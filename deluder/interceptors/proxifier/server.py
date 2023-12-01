import logging
import threading
import concurrent.futures
import socket

from deluder.common import *
from deluder.utils import try_close

from deluder.interceptors.proxifier.strategy import * 
from deluder.interceptors.proxifier.connection import Connection


class Server:
    """
    Proxifier server, which starts server sockets and allows creation of connections to it through proxy
    """
    server_sock: socket.socket
    lock: threading.Lock

    def __init__(
            self,
            server_host: str, 
            server_port: int,
            proxy_host: str, 
            proxy_port: int,
            strategy: ProxifierStrategyType, 
            strategy_config: dict,
            logger: logging.Logger
    ):
        self.server_host = server_host
        self.server_port = server_port
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.strategy = strategy
        self.strategy_config = strategy_config
        self.logger = logger

    def start(self):
        """
        Starts the server and listens for new connections
        """
        self.lock = threading.Lock()
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        server_address = (self.server_host, self.server_port)
        self.logger.info('Running server on %s:%d.', self.server_host, self.server_port)
        self.server_sock.bind(server_address)
        self.server_sock.listen(1)
    
    def stop(self):
        """
        Stops the server
        """
        try_close(self.server_sock)

    def connect(self) -> Connection:
        """
        Creates new connection to the server through the configured proxy
        """
        with self.lock:
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
            server_connection = executor.submit(self._server_accept)
            client_sock = executor.submit(self._client_connect)
            return Connection(
                client_sock=client_sock.result(), 
                server_sock=server_connection.result(),
                strategy=create_strategy(self.strategy, self.strategy_config),
                logger=self.logger
            )
    
    def _server_accept(self):
        self.logger.debug('Accepting connections on %s:%d.', self.server_host, self.server_port)
        server_client_connection, _ = self.server_sock.accept()
        return server_client_connection

    def _client_connect(self):
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (self.proxy_host, self.proxy_port)
        self.logger.debug('Connecting through proxy on %s:%d.', self.proxy_host, self.proxy_port)
        client_sock.connect(server_address)
        return client_sock
