import win32file, win32pipe
import websockets
import websocket
import asyncio
import threading
import argparse


class Options:
    ws_server_port: int
    http_proxy_port: int
    pipe_name: str

options = Options()


def pipe_data_available(pipe) -> bool:
    (_, avail, _) = win32pipe.PeekNamedPipe(pipe, 0)
    return avail > 0


def create_pipe_server(pipe_name: str):
    return win32pipe.CreateNamedPipe(
        pipe_name,
        win32pipe.PIPE_ACCESS_DUPLEX,
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
        0,
        None
    )


def on_message(ws_client_conn, msg, pipe):
    try:
        win32file.WriteFile(pipe, msg)

    except Exception as e:
        print(e)
        ws_client_conn.close()
        win32file.CloseHandle(pipe)


def on_open(ws_client_conn, pipe):
    def run():
        try:
            while True:
                if pipe_data_available(pipe):
                    (_, msg) = win32file.ReadFile(pipe, 65536)
                    ws_client_conn.send(msg, websocket.ABNF.OPCODE_BINARY)

        except Exception as e:
            print(e)
            ws_client_conn.close()
            win32file.CloseHandle(pipe)

    threading.Thread(target=run).start()


def ws_client_connect_and_handle(pipe):
    try:
        ws_client_conn = websocket.WebSocketApp(
                f'ws://127.0.0.1:{options.ws_server_port}',
                on_open=lambda ws_client_conn : on_open(ws_client_conn, pipe),
                on_message=lambda ws_client_conn, msg : on_message(ws_client_conn, msg, pipe))

        ws_client_conn.run_forever(
            proxy_type='http',
            http_proxy_host='127.0.0.1',
            http_proxy_port=options.http_proxy_port,
            http_no_proxy=['dummyhost'])
    
    except Exception as e:
        print(e)
        ws_client_conn.close()
        win32file.CloseHandle(pipe)


def pipe_server_loop():
    try:
        while True:
            pipe = create_pipe_server(options.pipe_name)
            win32pipe.ConnectNamedPipe(pipe, None)

            threading.Thread(target=ws_client_connect_and_handle, args=(pipe,)).start()

            # wait for an available pipe server before moving on to the next iteration
            # to avoid race condition where the ws client can connect to our next
            # pipe server
            win32pipe.WaitNamedPipe(options.pipe_name, win32pipe.NMPWAIT_WAIT_FOREVER)
    
    except Exception as e:
        print(e)


async def ws_server_to_pipe_client(ws_server_conn, pipe):
    try:
        while True:
            msg = await ws_server_conn.recv()
            win32file.WriteFile(pipe, msg)
    
    except Exception as e:
        print(e)
        await ws_server_conn.close()
        win32file.CloseHandle(pipe)


def pipe_client_to_ws_server(ws_server_conn, pipe, loop):
    try:
        while True:
            if pipe_data_available(pipe):
                (_, msg) = win32file.ReadFile(pipe, 65536)
                asyncio.run_coroutine_threadsafe(ws_server_conn.send(msg), loop)
    
    except Exception as e:
        print(e)
        asyncio.run_coroutine_threadsafe(ws_server_conn.close(), loop)
        win32file.CloseHandle(pipe)


async def ws_server_handler(ws):
    pipe = create_pipe_client(options.pipe_name)

    ws_to_pipe_task = asyncio.create_task(ws_server_to_pipe_client(ws, pipe))
    pipe_to_ws_coro = asyncio.to_thread(
        pipe_client_to_ws_server, ws, pipe, asyncio.get_running_loop())

    await pipe_to_ws_coro
    await ws_to_pipe_task


async def main():
    try:
        pipe_server_coro = asyncio.to_thread(pipe_server_loop)
        async with websockets.serve(ws_server_handler, "", options.ws_server_port):
            await pipe_server_coro
            await asyncio.Future()
    
    except Exception as e:
        print(e)


def parse_cmd_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pipe-name', required=True)
    parser.add_argument('--ws-port', required=True)
    parser.add_argument('--http-proxy-port', required=True)
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = parse_cmd_args()
    options.ws_server_port = args.ws_port
    options.http_proxy_port = args.http_proxy_port
    options.pipe_name = args.pipe_name
    asyncio.run(main())
