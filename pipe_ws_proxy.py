import pipe_helper
import win32file, win32pipe, win32event
import pywintypes, winerror
import websockets
import websocket
import asyncio
import threading
import argparse
import logging


PIPE_PREFIX = '\\\\.\\pipe\\'


class Config:
    ws_server_port: int
    http_proxy_port: int
    pipe_name: str
    pipe_fullpath: str


def on_message(ws_client_conn, msg, pipe):
    try:
        pipe_helper.pipe_write_async_await(pipe, msg)

    except Exception as e:
        if e.winerror != winerror.ERROR_BROKEN_PIPE:
            logging.error(e)

        ws_client_conn.close()
        win32file.CloseHandle(pipe)


def on_open(ws_client_conn, pipe):
    def run():
        try:
            read_buf = win32file.AllocateReadBuffer(65536)
            while True:
                msg = pipe_helper.pipe_read_async_await(pipe, read_buf)
                ws_client_conn.send(msg, websocket.ABNF.OPCODE_BINARY)

        except Exception as e:
            if e.winerror != winerror.ERROR_BROKEN_PIPE:
                logging.error(e)

            ws_client_conn.close()
            win32file.CloseHandle(pipe)

    threading.Thread(target=run).start()


def ws_client_connect_and_handle(pipe):
    try:
        ws_client_conn = websocket.WebSocketApp(
                f'ws://127.0.0.1:{Config.ws_server_port}/pipe/{Config.pipe_name}',
                on_open=lambda ws_client_conn : on_open(ws_client_conn, pipe),
                on_message=lambda ws_client_conn, msg : on_message(ws_client_conn, msg, pipe))

        ws_client_conn.run_forever(
            proxy_type='http',
            http_proxy_host='127.0.0.1',
            http_proxy_port=Config.http_proxy_port,
            http_no_proxy=['dummyhost'])
    
    except Exception as e:
        if e.winerror != winerror.ERROR_BROKEN_PIPE:
            logging.error(e)

        ws_client_conn.close()
        win32file.CloseHandle(pipe)


def pipe_server_loop():
    try:
        pipe = pipe_helper.create_pipe_server(Config.pipe_fullpath)
        while True:
            overlapped = pywintypes.OVERLAPPED()
            overlapped.hEvent = win32event.CreateEvent(None, True, False, None)
            win32pipe.ConnectNamedPipe(pipe, overlapped)
            win32event.WaitForSingleObject(overlapped.hEvent, win32event.INFINITE)
            win32file.CloseHandle(overlapped.hEvent)

            # wait for an available pipe server before moving on to the next iteration
            # to avoid race condition where the ws client can connect to our next
            # pipe server
            win32pipe.WaitNamedPipe(Config.pipe_fullpath, win32pipe.NMPWAIT_WAIT_FOREVER)

            pipe_next = pipe_helper.create_pipe_server(Config.pipe_fullpath)
            threading.Thread(target=ws_client_connect_and_handle, args=(pipe,)).start()
            pipe = pipe_next
    
    except Exception as e:
        if e.winerror != winerror.ERROR_BROKEN_PIPE:
            logging.error(e)


async def ws_server_to_pipe_client(ws_server_conn, pipe):
    try:
        while True:
            msg = await ws_server_conn.recv()
            pipe_helper.pipe_write_async_await(pipe, msg)
    
    except Exception as e:
        if e.winerror != winerror.ERROR_BROKEN_PIPE:
            logging.error(e)

        await ws_server_conn.close()
        win32file.CloseHandle(pipe)


def pipe_client_to_ws_server(ws_server_conn, pipe, loop):
    try:
        read_buf = win32file.AllocateReadBuffer(65536)
        while True:
            msg = pipe_helper.pipe_read_async_await(pipe, read_buf)
            asyncio.run_coroutine_threadsafe(ws_server_conn.send(msg), loop)
    
    except Exception as e:
        if e.winerror != winerror.ERROR_BROKEN_PIPE:
            logging.error(e)
            
        asyncio.run_coroutine_threadsafe(ws_server_conn.close(), loop)
        win32file.CloseHandle(pipe)


async def ws_server_handler(ws):
    pipe = pipe_helper.create_pipe_client(Config.pipe_fullpath)

    ws_to_pipe_task = asyncio.create_task(ws_server_to_pipe_client(ws, pipe))
    pipe_to_ws_coro = asyncio.to_thread(
        pipe_client_to_ws_server, ws, pipe, asyncio.get_running_loop())

    await pipe_to_ws_coro
    await ws_to_pipe_task


async def main():
    try:
        pipe_server_coro = asyncio.to_thread(pipe_server_loop)
        async with websockets.serve(ws_server_handler, '', Config.ws_server_port):
            await pipe_server_coro
            await asyncio.Future()
    
    except Exception as e:
        if e.winerror != winerror.ERROR_BROKEN_PIPE:
            logging.error(e)


def parse_cmd_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pipe-name', required=True)
    parser.add_argument('--ws-port', required=True)
    parser.add_argument('--http-proxy-port', required=True)

    parser.add_argument(
        '--log-level',
        required=False,
        choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'],
        default='INFO')

    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = parse_cmd_args()

    Config.ws_server_port = args.ws_port
    Config.http_proxy_port = args.http_proxy_port
    Config.log_level = args.log_level

    if args.pipe_name.startswith(PIPE_PREFIX):
        Config.pipe_fullpath = args.pipe_name
        Config.pipe_name = Config.pipe_fullpath[len(PIPE_PREFIX):]
    else:
        Config.pipe_name = args.pipe_name
        Config.pipe_fullpath = PIPE_PREFIX + Config.pipe_name

    logging.basicConfig(level=logging.getLevelName(Config.log_level))
    asyncio.run(main())
