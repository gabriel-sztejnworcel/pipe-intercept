import asyncio
import logging
from http_parser.pyparser import HttpParser


HTTP_PROXY_PORT = 9999


class ProxyException(Exception):
    pass


async def proxy_server_handler(server_reader, server_writer):
    try:
        req = await server_reader.read(65536)
        host, port = handle_connect_request(req)

        client_reader, client_writer = await asyncio.open_connection(host, port)
        server_writer.write(b'HTTP/1.1 200 OK\r\n\r\n')
        await server_writer.drain()

        asyncio.create_task(forward_data(server_reader, client_writer))
        asyncio.create_task(forward_data(client_reader, server_writer))

    except ProxyException as e:
        logging.warning(e)

    except Exception as e:
        pass


def handle_connect_request(req: bytes):
    parser = HttpParser()
    parsed_len = parser.execute(req, len(req))

    if parsed_len != len(req):
        raise ProxyException(f'Invalid request: {req}')

    method = parser.get_method()
    if method != 'CONNECT':
        raise ProxyException(f'Invalid request method: {method}')

    host = parser.get_headers()['HOST'] 
    host_split = host.split(':')

    if len(host_split) != 2:
        raise ProxyException(f'Invalid host: {host}')

    host = host_split[0]
    port = host_split[1]
    return host, port


async def forward_data(reader, writer):
    try:
        while not reader.at_eof():
            msg = await reader.read(65536)
            msg = msg.replace(b'zerothis', b'00000000')
            writer.write(msg)
            await writer.drain()

    except:
        pass

    writer.close()


async def main():
    server = await asyncio.start_server(proxy_server_handler, '127.0.0.1', HTTP_PROXY_PORT)
    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())
