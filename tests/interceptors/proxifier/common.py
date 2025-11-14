import socket

from tests.utils import generate_all_bytes
from concurrent.futures import ThreadPoolExecutor
from threading import Thread

from deluder.utils import try_close


TEST_DATA_INPUT = ['te[replace]st'.encode(), generate_all_bytes(), '[replace]warxim[replace]'.encode()]
TEST_DATA_OUTPUT = ['te[value]st'.encode(), generate_all_bytes(), '[value]warxim[value]'.encode()]


class SimpleProxy(Thread):
    def __init__(self, proxy_port, target_port, buffer_size, interceptor):
        Thread.__init__(self)
        self.proxy_port = proxy_port
        self.target_port = target_port
        self.buffer_size = buffer_size
        self.interceptor = interceptor
    
    def run(self):
        self.proxy_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.proxy_sock.settimeout(10)
        proxy_address = ('127.0.0.1', self.proxy_port)
        self.proxy_sock.bind(proxy_address)
        self.proxy_sock.listen(1)
        
        self.proxy_client_sock, _ = self.proxy_sock.accept()
        
        self.target_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.target_sock.settimeout(10)
        target_address = ('127.0.0.1', self.target_port)
        self.target_sock.connect(target_address)
            
        with ThreadPoolExecutor(max_workers=2) as executor:
            executor.submit(self._handle_client_to_proxy)
            executor.submit(self._handle_server_to_proxy)

    def _handle_client_to_proxy(self):
        while True:
            data = self.proxy_client_sock.recv(self.buffer_size)
            if not data:
                return
            data = self.interceptor(data)
            if not data:
                return
            self.target_sock.sendall(data)

    def _handle_server_to_proxy(self):
        while True:
            data = self.target_sock.recv(self.buffer_size)
            if not data:
                return
            data = self.interceptor(data)
            if not data:
                return
            self.proxy_client_sock.sendall(data)

    def stop(self):
        try_close(self.target_sock)
        try_close(self.proxy_sock)
        self.join()


def create_proxy(interceptor=None) -> SimpleProxy:
    interceptor = interceptor if interceptor is not None else data_inteceptor
    return SimpleProxy(proxy_port=18888, target_port=25500, buffer_size=1024, interceptor=interceptor)


def data_inteceptor(data: bytes) -> bytes:
    return data.replace(b'[replace]', b'[value]')


def create_config() -> dict:
    return {
        'proxyPort': 18888,
        'serverPort': 25500,
    }
