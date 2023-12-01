import logging
import threading

from deluder.interceptor import MessageInterceptor
from deluder.common import *

from deluder.interceptors.petep.common import *
from deluder.interceptors.petep.connection import *


class PetepMessageInterceptor(MessageInterceptor):
    """
    PETEP Message Interceptor adds support for integration between Deluder and PETEP.
    Integration uses simple custom protocol of the following format:
    [1B type][4B length][payload]
    in order to let PETEP intercept the Deluder messages in a convenient way.
    """
    connections: Dict[str, PetepConnection]
    lock: threading.Lock

    @classmethod
    def default_config(cls) -> dict:
        return {
            'petepHost': '127.0.0.1',
            'petepPort': 8008,
            'autoCloseConnections': True,
            'multipleConnections': True,
        }

    def init(self):
        self.connections = {}
        self.lock = threading.Lock()

    def intercept(self, process: Process, message: Message):
        if isinstance(message, SendMessage):
            message.data = self._get_connection(message).c2s(message.data)
        elif isinstance(message, RecvMessage):
            message.data = self._get_connection(message).s2c(message.data)
        elif isinstance(message, CloseMessage):
            self._handle_connection_close_message(message)

    def destroy(self):
        if hasattr(self, 'connections'):
            for connection in self.connections.values():
                connection.stop()

    def _get_connection(self, message: Message) -> PetepConnection:
        with self.lock:
            # Determine connection identifier
            connection_id = self._extract_connection_id(message)

            # Get connection or create a new one if it does not exist
            connection = self.connections.get(connection_id)
            if connection is None:
                info = self._extract_connection_info(message, connection_id)
                connection = PetepConnection(
                    petep_host=self.config['petepHost'],
                    petep_port=self.config['petepPort'],
                    info=info,
                    logger=self.logger
                )
                self.connections[connection_id] = connection
                connection.start()

            return connection
    
    def _extract_connection_id(self, message: Message) -> str:
        if self.config['multipleConnections'] == True:
            return message.metadata.get(MetadataType.CONNECTION_ID, DEFAULT_CONNECTION_ID) 
        return DEFAULT_CONNECTION_ID
    
    def _extract_connection_info(self, message: Message, connection_id: str) -> str:
        if connection_id == DEFAULT_CONNECTION_ID:
            return ConnectionInfo(
                id=connection_id
            )
        return ConnectionInfo(
            id=connection_id,
            protocol=message.metadata.get(MetadataType.PROTOCOL),
            socket=message.metadata.get(MetadataType.SOCKET),
            module=message.metadata.get(MetadataType.MODULE),
            source_ip=message.metadata.get(MetadataType.CONNECTION_SOURCE_IP),
            source_port=message.metadata.get(MetadataType.CONNECTION_SOURCE_PORT),
            source_path=message.metadata.get(MetadataType.CONNECTION_SOURCE_PATH),
            destination_ip=message.metadata.get(MetadataType.CONNECTION_DESTINATION_IP),
            destination_port=message.metadata.get(MetadataType.CONNECTION_DESTINATION_PORT),
            destination_path=message.metadata.get(MetadataType.CONNECTION_DESTINATION_PATH)
        )

    
    def _handle_connection_close_message(self, message: Message):
        if self.config['autoCloseConnections'] is False:
            return # Automatic closing of connection is disabled
        
        with self.lock:
            # Determine connection identifier
            connection_id = self._extract_connection_id(message)

            if connection_id is None or connection_id == DEFAULT_CONNECTION_ID:
                return # Do not close default connection
            
            connection = self.connections.pop(connection_id, None)
            if connection is None:
                return # Connection already
            
            self.logger.info('Connection %s (%s) is being closed due to received close event.', connection.info.id, connection.info.get_name())
            
            connection.stop()
