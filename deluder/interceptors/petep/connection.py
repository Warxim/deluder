import json
import logging
import socket
import threading

from deluder.common import *
from deluder.utils import recv_n, try_close

from deluder.interceptors.petep.common import *


DEFAULT_CONNECTION_ID = 'default'


@dataclass
class ConnectionInfo:
    """
    Information about the Deluder connection, which is sent to PETEP
    """
    id: str
    socket: Optional[int] = None
    protocol: Optional[str] = None
    source_ip: Optional[str] = None
    source_port: Optional[int] = None
    source_path: Optional[str] = None
    destination_ip: Optional[str] = None
    destination_port: Optional[int] = None
    destination_path: Optional[str] = None
    module: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps({
            'id': self.id,
            'socket': self.socket,
            'protocol': self.protocol,
            'name': self.get_name(),
            'sourceIp': self.source_ip,
            'sourcePort': self.source_port,
            'sourcePath': self.source_path,
            'destinationIp': self.destination_ip,
            'destinationPort': self.destination_port,
            'destinationPath': self.destination_path,
            'module': self.module
        })

    @staticmethod
    def get_address(ip, port, path) -> Optional[str]:
        if ip is not None:
            if port is not None:
                if ip == '127.0.0.1':
                    return  f':{port}'
                return f'{ip}:{port}'
            else:
                return str(ip)
        if path is not None:
            return str(path)
        return None
    
    def get_source(self) -> Optional[str]:
        return self.get_address(self.source_ip, self.source_port, self.source_path)
    
    def get_destination(self) -> Optional[str]:
        return self.get_address(self.destination_ip, self.destination_port, self.destination_path)

    def get_name_suffix(self) -> str:
        suffix = ''
        if self.id == DEFAULT_CONNECTION_ID:
            return suffix
        if self.module is not None:
            suffix += self.module
        if self.protocol is not None:
            suffix += f'/{self.protocol}'
        if suffix == '':
            return suffix
        return f' ({suffix})'

    def get_name(self) -> str:
        if self.id == DEFAULT_CONNECTION_ID:
            return 'Deluder Connection'
        
        source = self.get_source()
        destination = self.get_destination()

        if not source and not destination:
            return self.id + self.get_name_suffix()

        if source is None:
            source = '?'
        if destination is None:
            destination = '?'

        return f'{source}<->{destination}{self.get_name_suffix()}'


class PetepConnection:
    """
    Connection to PETEP (PETEP is the server and Deluder is the client).
    Each connection to PETEP represents a connection in Deluder (if not configured otherwise).
    """
    petep_host: str
    petep_port: int
    socket: socket.socket
    logger: logging.Logger
    lock: threading.Lock

    def __init__(
            self,
            petep_host: str, 
            petep_port: int,
            info: ConnectionInfo,
            logger: logging.Logger
    ):
        self.petep_host = petep_host
        self.petep_port = petep_port
        self.info = info
        self.logger = logger

    def start(self):
        """
        Starts the connection to the PETEP and sends info about the connection
        """
        self.logger.info('Connection %s (%s) started.', self.info.id, self.info.get_name())
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        petep_address = (self.petep_host, self.petep_port)
        self.socket.connect(petep_address)
        self.logger.debug('Connection %s (%s) connected to PETEP on %s:%d.', self.info.id, self.info.get_name(), self.petep_host, self.petep_port)
        self._send_connection_info(self.info)
    
    def stop(self):
        """
        Stops the connection to the PETEP
        """
        try_close(self.socket)

    def c2s(self, data: bytes) -> bytes:
        """
        Sends client->server data to PETEP for interception
        """
        return self._send_recv(PetepDeluderMessageType.DATA_C2S, data)

    def s2c(self, data: bytes) -> bytes:
        """
        Sends server->client data to PETEP for interception
        """
        return self._send_recv(PetepDeluderMessageType.DATA_S2C, data)
    
    def _send_recv(self, type: PetepDeluderMessageType, data: bytes) -> bytes:
        payload = self._create_payload(type, data)
        self.socket.sendall(payload)
        
        type_byte = recv_n(self.socket, 1)
        length_bytes = recv_n(self.socket, 4)
        length = int.from_bytes(length_bytes, 'big')
        data = recv_n(self.socket, length)
        return data
        
    def _send_connection_info(self, info: ConnectionInfo):
        payload = self._create_payload(PetepDeluderMessageType.CONNECTION_INFO, info.to_json().encode())
        self.socket.sendall(payload)

    def _create_payload(self, type: PetepDeluderMessageType, data: bytes) -> bytes:
        payload = bytearray()
        payload.append(type.value)
        length = len(data).to_bytes(4, byteorder='big')
        payload.extend(length)
        payload.extend(data)
        return payload
