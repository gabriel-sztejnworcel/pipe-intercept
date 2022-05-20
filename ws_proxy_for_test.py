import websockets
import asyncio
import logging


WS_PROXY_PORT = 9999


async def ws_server_handler(ws_server, path):
    forward_path = f'ws://{ws_server.request_headers["Host"]}{path}'
    async with websockets.connect(forward_path) as ws_client:
        client_to_server_task = asyncio.create_task(client_to_server(ws_client, ws_server))
        server_to_client_task = asyncio.create_task(server_to_client(ws_client, ws_server))
        await client_to_server_task
        await server_to_client_task


async def client_to_server(ws_client, ws_server):
    async for msg in ws_client:
        await ws_server.send(msg)


async def server_to_client(ws_client, ws_server):
    async for msg in ws_server:
        await ws_client.send(msg)


async def main():
    try:
        async with websockets.serve(ws_server_handler, '127.0.0.1', WS_PROXY_PORT) as ws_server:
            await asyncio.Future()
    
    except Exception as e:
        logging.error(e)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())
