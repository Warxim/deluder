import threading

from deluder.common import *
from deluder.interceptor import MessageInterceptor

from deluder.interceptors.proxifier.strategy import * 
from deluder.interceptors.proxifier.connection import DEFAULT_CONNECTION_ID, Connection
from deluder.interceptors.proxifier.server import Server


class ProxifierMessageInterceptor(MessageInterceptor):
    """
    Proxifier interceptor allows sending Deluder messages through TCP proxies using multiple strategies
    """
    server: Server
    connections: Dict[str, Connection]
    lock: threading.Lock

    @classmethod
    def default_config(cls) -> dict:
        return {
            'proxyHost': '127.0.0.1',
            'proxyPort': 8888,
            'serverHost': '127.0.0.1',
            'serverPort': 25500,
            'strategy': 'length',
            'strategies': {
                'buffer': {
                    'bufferSize': 65536,
                },
                'suffix': {
                    'bufferSize': 65536,
                    'value': '[D_END]',
                },
                'length': {
                },
            },
            'autoCloseConnections': True,
            'multipleConnections': True,
        }

    def init(self):
        self.server = Server(
            server_host=self.config['serverHost'],
            server_port=self.config['serverPort'],
            proxy_host=self.config['proxyHost'],
            proxy_port=self.config['proxyPort'],
            strategy=ProxifierStrategyType(self.config['strategy']),
            strategy_config=self.config['strategies'].get(self.config['strategy'], {}),
            logger=self.logger
        )
        self.server.start()
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
        if hasattr(self, 'server'):
            self.server.stop()
    
    def _extract_connection_id(self, message: Message) -> str:
        if self.config['multipleConnections'] == True:
            return message.metadata.get(MetadataType.CONNECTION_ID, DEFAULT_CONNECTION_ID) 
        return DEFAULT_CONNECTION_ID

    def _get_connection(self, message: Message) -> Connection:
        with self.lock:
            # Determine connection identifier
            connection_id = self._extract_connection_id(message)

            # Get connection or create a new one if it does not exist
            connection = self.connections.get(connection_id)
            if connection is None:
                connection = self.server.connect()
                connection.set_info(connection_id)
                connection.start()
                self.connections[connection_id] = connection

            return connection
    
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
            
            self.logger.info('Connection %s is being closed due to received close event.', connection.id)
            
            connection.stop()

