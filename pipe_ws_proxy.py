import win32file, win32pipe, pywintypes, win32event
import websockets
import websocket
import asyncio
import threading
import argparse
import logging


PIPE_PREFIX = '\\\\.\\pipe\\'


class Options:
    ws_server_port: int
    http_proxy_port: int
    pipe_name: str
    pipe_fullpath: str


def create_pipe_server(pipe_name: str):
    return win32pipe.CreateNamedPipe(
        pipe_name,
        win32pipe.PIPE_ACCESS_DUPLEX | win32file.FILE_FLAG_OVERLAPPED,
        win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE,
        win32pipe.PIPE_UNLIMITED_INSTANCES,
        65536,
        65536,
        0,
        None
    )


def create_pipe_client(pipe_name: str):
    return win32file.CreateFile(
        pipe_name,
        win32file.GENERIC_READ | win32file.GENERIC_WRITE,
        0,
        None,
        win32file.OPEN_EXISTING,
        win32file.FILE_FLAG_OVERLAPPED,
        None
    )


def on_message(ws_client_conn, msg, pipe):
    try:
        overlapped = pywintypes.OVERLAPPED()
        overlapped.hEvent = win32event.CreateEvent(None, True, False, None)
        win32file.WriteFile(pipe, msg, overlapped)
        win32event.WaitForSingleObject(overlapped.hEvent, win32event.INFINITE)
        # get overlapped result?
        win32file.CloseHandle(overlapped.hEvent)

    except Exception as e:
        logging.error(e)
        ws_client_conn.close()
        win32file.CloseHandle(pipe)


def on_open(ws_client_conn, pipe):
    def run():
        try:
            while True:
                overlapped = pywintypes.OVERLAPPED()
                overlapped.hEvent = win32event.CreateEvent(None, True, False, None)
                read_buf = win32file.AllocateReadBuffer(65536)
                win32file.ReadFile(pipe, read_buf, overlapped)
                win32event.WaitForSingleObject(overlapped.hEvent, win32event.INFINITE)
                read_buf_len = win32pipe.GetOverlappedResult(pipe, overlapped, True)
                msg = bytes(read_buf[:read_buf_len])
                win32file.CloseHandle(overlapped.hEvent)
                ws_client_conn.send(msg, websocket.ABNF.OPCODE_BINARY)

        except Exception as e:
            logging.error(e)
            ws_client_conn.close()
            win32file.CloseHandle(pipe)

    threading.Thread(target=run).start()


def ws_client_connect_and_handle(pipe):
    try:
        print(options.pipe_name)
        ws_client_conn = websocket.WebSocketApp(
                f'ws://127.0.0.1:{options.ws_server_port}/pipe/{options.pipe_name}',
                on_open=lambda ws_client_conn : on_open(ws_client_conn, pipe),
                on_message=lambda ws_client_conn, msg : on_message(ws_client_conn, msg, pipe))

        ws_client_conn.run_forever(
            proxy_type='http',
            http_proxy_host='127.0.0.1',
            http_proxy_port=options.http_proxy_port,
            http_no_proxy=['dummyhost'])
    
    except Exception as e:
        logging.error(e)
        ws_client_conn.close()
        win32file.CloseHandle(pipe)


def pipe_server_loop():
    try:
        pipe = create_pipe_server(options.pipe_fullpath)
        while True:
            overlapped = pywintypes.OVERLAPPED()
            overlapped.hEvent = win32event.CreateEvent(None, True, False, None)
            win32pipe.ConnectNamedPipe(pipe, overlapped)
            win32event.WaitForSingleObject(overlapped.hEvent, win32event.INFINITE)
            # get overlapped result?
            win32file.CloseHandle(overlapped.hEvent)

            # wait for an available pipe server before moving on to the next iteration
            # to avoid race condition where the ws client can connect to our next
            # pipe server
            win32pipe.WaitNamedPipe(options.pipe_fullpath, win32pipe.NMPWAIT_WAIT_FOREVER)

            pipe_next = create_pipe_server(options.pipe_fullpath)
            threading.Thread(target=ws_client_connect_and_handle, args=(pipe,)).start()
            pipe = pipe_next
    
    except Exception as e:
        logging.error(e)


async def ws_server_to_pipe_client(ws_server_conn, pipe):
    try:
        while True:
            msg = await ws_server_conn.recv()
            overlapped = pywintypes.OVERLAPPED()
            overlapped.hEvent = win32event.CreateEvent(None, True, False, None)
            win32file.WriteFile(pipe, msg, overlapped)
            win32event.WaitForSingleObject(overlapped.hEvent, win32event.INFINITE)
            # get overlapped result?
            win32file.CloseHandle(overlapped.hEvent)
    
    except Exception as e:
        logging.error(e)
        await ws_server_conn.close()
        win32file.CloseHandle(pipe)


def pipe_client_to_ws_server(ws_server_conn, pipe, loop):
    try:
        while True:
            overlapped = pywintypes.OVERLAPPED()
            overlapped.hEvent = win32event.CreateEvent(None, True, False, None)
            read_buf = win32file.AllocateReadBuffer(65536)
            win32file.ReadFile(pipe, read_buf, overlapped)
            win32event.WaitForSingleObject(overlapped.hEvent, win32event.INFINITE)
            read_buf_len = win32pipe.GetOverlappedResult(pipe, overlapped, True)
            msg = bytes(read_buf[:read_buf_len])
            win32file.CloseHandle(overlapped.hEvent)
            asyncio.run_coroutine_threadsafe(ws_server_conn.send(msg), loop)
    
    except Exception as e:
        logging.error(e)
        asyncio.run_coroutine_threadsafe(ws_server_conn.close(), loop)
        win32file.CloseHandle(pipe)


async def ws_server_handler(ws):
    pipe = create_pipe_client(options.pipe_fullpath)

    ws_to_pipe_task = asyncio.create_task(ws_server_to_pipe_client(ws, pipe))
    pipe_to_ws_coro = asyncio.to_thread(
        pipe_client_to_ws_server, ws, pipe, asyncio.get_running_loop())

    await pipe_to_ws_coro
    await ws_to_pipe_task


async def main():
    try:
        pipe_server_coro = asyncio.to_thread(pipe_server_loop)
        async with websockets.serve(ws_server_handler, '', options.ws_server_port):
            await pipe_server_coro
            await asyncio.Future()
    
    except Exception as e:
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

    options = Options()
    options.ws_server_port = args.ws_port
    options.http_proxy_port = args.http_proxy_port
    options.log_level = args.log_level

    if args.pipe_name.startswith(PIPE_PREFIX):
        options.pipe_fullpath = args.pipe_name
        options.pipe_name = options.pipe_fullpath[len(PIPE_PREFIX):]
    else:
        options.pipe_name = args.pipe_name
        options.pipe_fullpath = PIPE_PREFIX + options.pipe_name

    logging.basicConfig(level=logging.getLevelName(options.log_level))
    asyncio.run(main())
