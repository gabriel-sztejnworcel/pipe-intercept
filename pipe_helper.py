import win32file, win32pipe
import win32event, pywintypes


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


def pipe_write_async_await(pipe, data):
    overlapped = pywintypes.OVERLAPPED()
    overlapped.hEvent = win32event.CreateEvent(None, True, False, None)
    win32file.WriteFile(pipe, data, overlapped)
    win32event.WaitForSingleObject(overlapped.hEvent, win32event.INFINITE)
    win32file.CloseHandle(overlapped.hEvent)


def pipe_read_async_await(pipe, read_buf) -> bytes:
    overlapped = pywintypes.OVERLAPPED()
    overlapped.hEvent = win32event.CreateEvent(None, True, False, None)
    win32file.ReadFile(pipe, read_buf, overlapped)
    win32event.WaitForSingleObject(overlapped.hEvent, win32event.INFINITE)
    read_buf_len = win32pipe.GetOverlappedResult(pipe, overlapped, True)
    win32file.CloseHandle(overlapped.hEvent)
    return bytes(read_buf[:read_buf_len])
