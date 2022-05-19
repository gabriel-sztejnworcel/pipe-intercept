import pipe_helper
import websockets
import asyncio


def create_pipe_client_server(pipe_name):
    pipe_fullpath = f'\\\\.\\pipe\\{pipe_name}'
    pipe_server = pipe_helper.create_pipe_server(pipe_fullpath)
    event = pipe_helper.pipe_wait_for_client_async_nowait(pipe_server)
    pipe_client = pipe_helper.create_pipe_client(pipe_fullpath)
    pipe_helper.wait_and_close_event(event)
    return pipe_server, pipe_client


class WebSocketProxy:
    def __init__(self, port: int, intercept_func = None):
        self.port = port
        self.intercept_func = intercept_func

    def run(self):
        ws_server = websockets.serve(self.connection_handler, '127.0.0.1', self.port)
        asyncio.get_event_loop().run_until_complete(ws_server)
        asyncio.get_event_loop().run_forever()

    async def connection_handler(self, ws_server, path):
        forward_path = f'ws://{ws_server.request_headers["Host"]}{path}'
        async with websockets.connect(forward_path) as ws_client:
            client_to_server_task = asyncio.create_task(self.client_to_server(ws_client, ws_server))
            server_to_client_task = asyncio.create_task(self.server_to_client(ws_client, ws_server))
            await client_to_server_task
            await server_to_client_task

    async def client_to_server(self, ws_client, ws_server):
        async for msg in ws_client:
            if self.intercept_func is not None:
                msg = self.intercept_func(msg)
            await ws_server.send(msg)

    async def server_to_client(self, ws_client, ws_server):
        async for msg in ws_server:
            if self.intercept_func is not None:
                msg = self.intercept_func(msg)
            await ws_client.send(msg)
