import pipe_helper
import config_handler
import win32file, win32pipe
import pywintypes, winerror
import websockets
import websocket
import asyncio
import threading
import logging


def ws_client_on_message(ws_client_conn, msg, pipe):
    try:
        pipe_helper.pipe_write_async_await(pipe, msg)

    except Exception as e:
        log_error(e)
        ws_client_conn.close()
        pipe_helper.close_handle_ignore_error(pipe)


def ws_client_on_open(ws_client_conn, pipe):
    def run():
        try:
            read_buf = win32file.AllocateReadBuffer(65536)
            while True:
                msg = pipe_helper.pipe_read_async_await(pipe, read_buf)
                ws_client_conn.send(msg, websocket.ABNF.OPCODE_BINARY)

        except Exception as e:
            log_error(e)
            ws_client_conn.close()
            pipe_helper.close_handle_ignore_error(pipe)

    threading.Thread(target=run).start()


def ws_client_connect_and_handle(pipe):
    try:
        ws_client_conn = websocket.WebSocketApp(
                f'ws://127.0.0.1:{config_handler.Config.ws_server_port}/pipe/{config_handler.Config.pipe_name}',
                on_open=lambda ws_client_conn : ws_client_on_open(ws_client_conn, pipe),
                on_message=lambda ws_client_conn, msg : ws_client_on_message(ws_client_conn, msg, pipe))

        ws_client_conn.run_forever(
            proxy_type='http',
            http_proxy_host='127.0.0.1',
            http_proxy_port=config_handler.Config.http_proxy_port,
            http_no_proxy=['dummyhost'])
    
    except Exception as e:
        log_error(e)
        ws_client_conn.close()
        pipe_helper.close_handle_ignore_error(pipe)


def pipe_server_loop():
    try:
        pipe = pipe_helper.create_pipe_server(config_handler.Config.pipe_fullpath)
        while True:
            pipe_helper.pipe_wait_for_client_async_await(pipe)

            # wait for an available pipe server before moving on to the next iteration
            # to avoid race condition where the ws client can connect to our next pipe server
            win32pipe.WaitNamedPipe(config_handler.Config.pipe_fullpath, win32pipe.NMPWAIT_WAIT_FOREVER)

            pipe_next = pipe_helper.create_pipe_server(config_handler.Config.pipe_fullpath)
            threading.Thread(target=ws_client_connect_and_handle, args=(pipe,)).start()
            pipe = pipe_next
    
    except Exception as e:
        log_error(e)


async def ws_server_to_pipe_client(ws_server_conn, pipe):
    try:
        while True:
            msg = await ws_server_conn.recv()
            pipe_helper.pipe_write_async_await(pipe, msg)
    
    except Exception as e:
        log_error(e)
        await ws_server_conn.close()
        pipe_helper.close_handle_ignore_error(pipe)


def pipe_client_to_ws_server(ws_server_conn, pipe, loop):
    try:
        read_buf = win32file.AllocateReadBuffer(65536)
        while True:
            msg = pipe_helper.pipe_read_async_await(pipe, read_buf)
            asyncio.run_coroutine_threadsafe(ws_server_conn.send(msg), loop)
    
    except Exception as e:
        log_error(e)
        asyncio.run_coroutine_threadsafe(ws_server_conn.close(), loop)
        pipe_helper.close_handle_ignore_error(pipe)


async def ws_server_handler(ws_server_conn, path):
    if path == f'/pipe/{config_handler.Config.pipe_name}':
        pipe = pipe_helper.create_pipe_client(config_handler.Config.pipe_fullpath)

        ws_to_pipe_task = asyncio.create_task(ws_server_to_pipe_client(ws_server_conn, pipe))
        pipe_to_ws_coro = asyncio.to_thread(
            pipe_client_to_ws_server, ws_server_conn, pipe, asyncio.get_running_loop())

        await pipe_to_ws_coro
        await ws_to_pipe_task


def log_error(e):
    skip_log = False
    if isinstance(e, websockets.exceptions.ConnectionClosedOK):
        skip_log = True
    elif isinstance(e, pywintypes.error) and e.winerror == winerror.ERROR_BROKEN_PIPE:
        skip_log = True
    if not skip_log:
        logging.error(e)


async def main():
    try:
        pipe_server_coro = asyncio.to_thread(pipe_server_loop)
        async with websockets.serve(ws_server_handler, '127.0.0.1', config_handler.Config.ws_server_port, compression=None) as ws_server:
            if config_handler.Config.ws_server_port == 0:
                # 0 means listen on a random port, we neet to get it for the WebSocket client
                config_handler.Config.ws_server_port = ws_server.server.sockets[0].getsockname()[1]
            await pipe_server_coro
    
    except Exception as e:
        log_error(e)


if __name__ == '__main__':
    config_handler.init_config()
    logging.basicConfig(level=logging.getLevelName(config_handler.Config.log_level))
    asyncio.run(main())
