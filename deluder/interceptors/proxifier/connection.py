import logging
import threading
import socket

from deluder.common import *

from deluder.utils import try_close
from deluder.interceptors.proxifier.strategy import * 


DEFAULT_CONNECTION_ID = 'default'


class Connection:
    """
    Proxifier connection is a connection to the Proxifier server through configured proxy
    (all messages are sent to the server through the proxy and the received message is then used as a result)
    """
    id: str
    client_sock: socket.socket
    server_sock: socket.socket
    lock: threading.Lock
    strategy: ProxifierStrategy

    def __init__(
            self, 
            client_sock: socket.socket, 
            server_sock: socket.socket,
            strategy: ProxifierStrategy,
            logger: logging.Logger
    ):
        self.client_sock = client_sock
        self.server_sock = server_sock
        self.strategy = strategy
        self.logger = logger
        self.lock = threading.Lock()
    
    def start(self):
        self.logger.info('Connection %s started.', self.id)
    
    def stop(self):
        try_close(self.server_sock)
        try_close(self.client_sock)
        self.logger.info('Connection %s stopped.', self.id)

    def c2s(self, data: bytes) -> bytes:
       """
       Sends the data from the client to the server and then receives the data on the server side and returns them back
       (by that, letting the data be intercepted in the proxy, which is between the client and the server)
       """
       return self._send_recv(data, self.client_sock, self.server_sock)
    
    def s2c(self, data: bytes) -> bytes:
       """
       Sends the data from the server to the client and then receives the data on the client side and returns them back
       (by that, letting the data be intercepted in the proxy, which is between the server and the client)
       """
       return self._send_recv(data, self.server_sock, self.client_sock)
    
    def set_info(self, id: str):
        self.id = id

    def _send_recv(self, data: bytes, sending_sock: socket.socket, receiving_sock: socket.socket) -> bytes:
        with self.lock:
            try:
                return self.strategy.send_recv(data, sending_sock, receiving_sock)
            except Exception as e:
                self.logger.error(e.args)
        return bytes()
