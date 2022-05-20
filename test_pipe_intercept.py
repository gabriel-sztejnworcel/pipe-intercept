import pipe_helper
import uuid
import win32file
import subprocess
import time


HTTP_PROXY_PORT = 9999


def create_pipe_client_server(pipe_name):
    pipe_fullpath = f'\\\\.\\pipe\\{pipe_name}'
    pipe_server = pipe_helper.create_pipe_server(pipe_fullpath)
    event = pipe_helper.pipe_wait_for_client_async_nowait(pipe_server)
    pipe_client = pipe_helper.create_pipe_client(pipe_fullpath)
    pipe_helper.wait_and_close_event(event)
    return pipe_server, pipe_client


def test_pipe_write_read():
    pipe_name = str(uuid.uuid4())
    pipe_server, pipe_client = create_pipe_client_server(pipe_name)
    pipe_helper.pipe_write_async_await(pipe_client, b'hello')
    read_buf = win32file.AllocateReadBuffer(65536)
    msg = pipe_helper.pipe_read_async_await(pipe_server, read_buf)
    assert msg == b'hello'


def test_pipe_intercept_msg_unchanged():
    pipe_name = str(uuid.uuid4())

    pipe_intercept_process = subprocess.Popen(
        ['python', 'pipe_intercept.py', '--pipe-name', pipe_name, '--http-proxy-port', f'{HTTP_PROXY_PORT}', '--log-level', 'DEBUG'],
        creationflags=subprocess.CREATE_NEW_CONSOLE)

    time.sleep(10)
    
    ws_proxy_process = subprocess.Popen(['python', 'ws_proxy_for_test.py'], creationflags=subprocess.CREATE_NEW_CONSOLE)

    time.sleep(10)

    pipe_server, pipe_client = create_pipe_client_server(pipe_name)

    pipe_helper.pipe_write_async_await(pipe_client, b'hello')
    read_buf = win32file.AllocateReadBuffer(65536)
    msg = pipe_helper.pipe_read_async_await(pipe_server, read_buf)
    print(msg)

    pipe_intercept_process.wait()
    ws_proxy_process.wait()
