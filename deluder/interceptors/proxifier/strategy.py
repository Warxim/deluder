import socket

from enum import Enum

from deluder.utils import recv_n


class ProxifierStrategyType(str, Enum):
    """
    Proxifing strategy
    """
    buffer = 'buffer'
    """Relies on buffer length"""
    suffix = 'suffix'
    """Relies on suffix appended at the end of each intercepted message"""
    length = 'length'
    """Relies on 4B length sent at the beginning of each intercepted message"""


class ProxifierStrategy:
    """
    Base class for Proxifier strategies
    """
    def __init__(self, config: dict):
        self.config = config

    def send_recv(self, data: bytes, sending_sock: socket.socket, receiving_sock: socket.socket, buffer_size: int) -> bytes:
        """
        Sends data through the sending_sock and receives them back using receiving_sock
        (by that, it lets the message be intercepted by the target proxy)
        """
        raise Exception('Not implemented!')


def create_strategy(strategy: ProxifierStrategyType, config: dict) -> ProxifierStrategy:
    """
    Creates strategy instance from type
    """
    if strategy == ProxifierStrategyType.buffer:
        return BufferStrategy(config)
    if strategy == ProxifierStrategyType.suffix:
        return SuffixStrategy(config)
    if strategy == ProxifierStrategyType.length:
        return LengthStrategy(config)


class BufferStrategy(ProxifierStrategy):
    """
    Buffer strategy relies on big enough buffer for sending/receiving the data
    """
    def send_recv(self, data: bytes, sending_sock: socket.socket, receiving_sock: socket.socket) -> bytes:
        buffer_size = self.config['bufferSize']
        sending_sock.sendall(data)
        data = receiving_sock.recv(buffer_size)
        if len(data) == 0:
            raise Exception('Connection lost, please restart deluder!')
        return data


class SuffixStrategy(ProxifierStrategy):
    """
    Suffix strategy relies on appended suffix at the end of each intercepted message
    """
    def send_recv(self, data: bytes, sending_sock: socket.socket, receiving_sock: socket.socket) -> bytes:
        suffix = self.config['value'].encode()
        buffer_size = self.config['bufferSize']
        sending_sock.sendall(data + suffix)
        total_data = bytearray()
        while True:
            data = receiving_sock.recv(buffer_size)
            if len(data) == 0:
                raise Exception('Connection lost, please restart deluder!')
            total_data.extend(data)
            if total_data.endswith(suffix):
                break
        return total_data[:-len(suffix)]


class LengthStrategy(ProxifierStrategy):
    """
    Length strategy relies on prepended 4B length at the beginning of each intercepted message
    """
    def send_recv(self, data: bytes, sending_sock: socket.socket, receiving_sock: socket.socket) -> bytes:
        payload = self.create_payload(data)
        sending_sock.sendall(payload)
        
        length_bytes = recv_n(receiving_sock, 4)
        length = int.from_bytes(length_bytes, 'big')
        data = recv_n(receiving_sock, length)
        return data

    def create_payload(self, data: bytes) -> bytes:
        payload = bytearray()
        length = len(data).to_bytes(4, byteorder='big')
        payload.extend(length)
        payload.extend(data)
        return payload
