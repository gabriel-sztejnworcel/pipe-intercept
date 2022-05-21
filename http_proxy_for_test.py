import asyncio
import logging
from http_parser.pyparser import HttpParser


HTTP_PROXY_PORT = 9999


async def proxy_server_handler(server_reader, server_writer):
    try:
        req = await server_reader.read(65536)
        host, port = handle_connect_request(req)
        logging.info(f'Received CONNECT request to {host}:{port}')

        client_reader, client_writer = await asyncio.open_connection(host, port)
        logging.info('Connected')

        server_to_client_task = asyncio.create_task(forward_data(server_reader, client_writer))
        client_to_server_task = asyncio.create_task(forward_data(client_reader, server_writer))

        await server_to_client_task
        await client_to_server_task

    except Exception as e:
        logging.error(e)


def handle_connect_request(req: bytes):
    parser = HttpParser()
    parsed_len = parser.execute(req, len(req))

    if parsed_len != len(req):
        raise Exception('Invalid request')

    method = parser.get_method()
    if method != 'CONNECT':
        raise Exception('Invalid request')

    host = parser.get_headers()['HOST'] 
    host_split = host.split(':')

    if len(host_split) != 2:
        raise Exception('Invalid request')

    host = host_split[0]
    port = host_split[1]
    return host, port


async def forward_data(reader, writer):
    logging.info('forward_data')
    while True:
        msg = await reader.read(65536)
        logging.info(f'got data: {msg}')
        writer.write(msg)
        await writer.drain()


async def main():
    server = await asyncio.start_server(proxy_server_handler, '127.0.0.1', HTTP_PROXY_PORT)
    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())
