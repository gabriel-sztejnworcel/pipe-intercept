import argparse


PIPE_PREFIX = '\\\\.\\pipe\\'


class Config:
    ws_server_port: int
    http_proxy_port: int
    pipe_name: str
    pipe_fullpath: str


def parse_cmd_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--pipe-name', required=True, help='The name of the pipe to be intercepted')

    parser.add_argument(
        '--ws-port',
        required=False,
        help='An available port number for the internal WebSocket server (if not specified, a random port will be used)',
        default=0,
        type=int)

    parser.add_argument(
        '--http-proxy-port',
        required=False,
        help='The port number of the HTTP proxy (if not specified, the default is 8080)',
        default=8080,
        type=int)

    parser.add_argument(
        '--log-level',
        required=False,
        choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'],
        help='Log level (if not specified, the default is INFO)',
        default='INFO')

    args = parser.parse_args()
    return args


def init_config():
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
