import test_helper
import pipe_helper
import uuid
import win32file
import threading
import os


def test_pipe_write_read():
    pipe_name = str(uuid.uuid4())
    pipe_server, pipe_client = test_helper.create_pipe_client_server(pipe_name)
    pipe_helper.pipe_write_async_await(pipe_client, b'hello')
    read_buf = win32file.AllocateReadBuffer(65536)
    msg = pipe_helper.pipe_read_async_await(pipe_server, read_buf)
    assert msg == b'hello'


def test_pipe_intercept_msg_unchanged():
    ws_proxy = test_helper.WebSocketProxy(9999)
    ws_proxy_thread = threading.Thread(target=ws_proxy.run)
    ws_proxy_thread.start()
    pipe_name = str(uuid.uuid4())
    os.symlink(f'start python pipe_intercept.py --pipe-name {pipe_name} --http-proxy-port 9999')
    while True:
        pass
