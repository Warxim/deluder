import json
import pytest
import socket 

from threading import Thread

from deluder.common import MetadataType, RecvMessage, SendMessage

from deluder.utils import recv_n, try_close
from deluder.interceptors.petep.interceptor import PetepDeluderMessageType, PetepMessageInterceptor

from tests.interceptors.proxifier.common import TEST_DATA_INPUT, TEST_DATA_OUTPUT, data_inteceptor


class PetepProxy(Thread):
    petep_port: int
    server_socket: socket.socket

    def __init__(
            self, 
            petep_port: int,
            interceptor
    ):
        Thread.__init__(self)
        self.petep_port = petep_port
        self.interceptor = interceptor
    
    def run(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.settimeout(10)
        petep_address = ('127.0.0.1', self.petep_port)
        self.server_socket.bind(petep_address)
        self.server_socket.listen(1)
        
        self.client_socket, _ = self.server_socket.accept()
        
        try:
            while True:
                type_byte = recv_n(self.client_socket, 1)
                length_bytes = recv_n(self.client_socket, 4)
                length = int.from_bytes(length_bytes, 'big')
                data = recv_n(self.client_socket, length)

                if type_byte[0] in {PetepDeluderMessageType.DATA_C2S.value, PetepDeluderMessageType.DATA_S2C.value}:
                    data = self.interceptor(data)
                    payload = self._create_payload(type_byte[0], data)
                    self.client_socket.sendall(payload)
                elif type_byte[0] == PetepDeluderMessageType.CONNECTION_INFO.value:
                    self.last_connection_info = json.loads(data) 
        except:
            pass

    def stop(self):
        try_close(self.server_socket)
        try_close(self.client_socket)
        self.join()

    def _create_payload(self, type: int, data: bytes) -> bytes:
        length = len(data)
        length_bytes = length.to_bytes(4, byteorder='big')
            
        payload = bytearray()
        payload.append(type)
        payload.extend(length_bytes)
        payload.extend(data)
        return payload


@pytest.mark.parametrize("metadata,expected_id,expected_name", [
    ({}, 'default', 'Deluder Connection'),
    ({MetadataType.CONNECTION_ID: 'test-connection-1'}, 'test-connection-1', 'test-connection-1'),
    ({MetadataType.CONNECTION_ID: 'test-1', 
      MetadataType.CONNECTION_DESTINATION_IP: '127.0.0.1',
      MetadataType.CONNECTION_DESTINATION_PORT: 1255}, 'test-1', '?<->:1255'),
    ({MetadataType.CONNECTION_ID: 'test-1', 
      MetadataType.CONNECTION_SOURCE_IP: '127.0.0.1',
      MetadataType.CONNECTION_SOURCE_PORT: 55680, 
      MetadataType.CONNECTION_DESTINATION_IP: '127.0.0.1',
      MetadataType.MODULE: 'winsock',
      MetadataType.PROTOCOL: 'tcp6',
      MetadataType.CONNECTION_DESTINATION_PORT: 1255}, 'test-1', ':55680<->:1255 (winsock/tcp6)'),
])
def test_petep_interceptor(metadata, expected_id, expected_name):
    interceptor = None
    proxy = None
    try:
        proxy = PetepProxy(petep_port=18888, interceptor=data_inteceptor)
        proxy.start()

        config = {
            'petepPort': 18888,
        }
        interceptor = PetepMessageInterceptor(config)
        interceptor.init()

        for i in range(len(TEST_DATA_INPUT)):
            message = SendMessage('id-1', TEST_DATA_INPUT[i], metadata)
            interceptor.intercept(None, message)
            assert message.data == TEST_DATA_OUTPUT[i]

        for i in range(len(TEST_DATA_INPUT)):
            message = RecvMessage('id-1', TEST_DATA_INPUT[i], metadata)
            interceptor.intercept(None, message)
            assert message.data == TEST_DATA_OUTPUT[i]
        
        assert proxy.last_connection_info['id'] == expected_id
        assert proxy.last_connection_info['name'] == expected_name
    finally:
        if interceptor:
            interceptor.destroy()
        
        if proxy:
            proxy.stop()

