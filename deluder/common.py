import enum
import frida

from dataclasses import dataclass, field
from typing import List, Dict, Optional


VERSION = "1.0"


@dataclass
class Process:
    """
    Process descriptor
    """
    pid: int
    session: frida.core.Session = None
    script: Optional[frida.core.Script] = None
    
    def __hash__(self):
        return hash(self.pid)


class MessageType(str, enum.Enum):
    """
    Type of message sent from Frida script to Deluder process
    """
    ERROR = 'error'
    SEND = 's'
    RECV = 'r'
    CLOSE = 'c'


class MetadataType(str, enum.Enum):
    """
    Standard metadata dictionary keys sent from Frida script to Deluder process
    """
    SOCKET = 's'
    PROTOCOL = 'p'
    CONNECTION_ID = 'ci'
    CONNECTION_SOURCE_IP = 'csi'
    CONNECTION_SOURCE_PORT = 'csp'
    CONNECTION_SOURCE_PATH = 'cspa'
    CONNECTION_DESTINATION_IP = 'cdi'
    CONNECTION_DESTINATION_PORT = 'cdp'
    CONNECTION_DESTINATION_PATH = 'cdpa'
    MODULE = 'm'


@dataclass
class Message:
    """
    Base class for all Deluder message types
    """
    id: str
    type: MessageType
    metadata: Dict[str, any]


@dataclass
class DataMessage(Message):
    """
    Base class for Deluder data message types
    """
    data: bytes


@dataclass
class SendMessage(DataMessage):
    """
    Message intercepted in send/encrypt library functions (representing communication from the client to the server)
    """
    def __init__(self, id: str, data: bytes, metadata: Dict[str, any]):
        super().__init__(id=id, type=MessageType.SEND, data=data, metadata=metadata)


@dataclass
class RecvMessage(DataMessage):
    """
    Message intercepted in recv/decrypt library functions (representing communication from the server to the client)
    """
    def __init__(self, id: str, data: bytes, metadata: Dict[str, any]):
        super().__init__(id=id, type=MessageType.RECV, data=data, metadata=metadata)


@dataclass
class CloseMessage(Message):
    """
    Message intercepted in close/shutdown library functions (representing closing of the connection)
    """
    def __init__(self, id: str, metadata: Dict[str, any]):
        super().__init__(id=id, type=MessageType.CLOSE, metadata=metadata)


class DeluderException(Exception):
    """
    Common Deluder exception used across the Deluder components
    """
    def __init__(self, message: str) -> None:
        self.message = message


@dataclass
class DeluderScriptConfig:
    """
    Deluder configuration for a single script
    """
    type: str
    config: Dict[str, any] = field(default_factory=dict)


@dataclass
class DeluderInterceptorConfig:
    """
    Deluder configuration for a single interceptor
    """
    type: str
    config: Dict[str, any] = field(default_factory=dict)


@dataclass
class DeluderConfig:
    """
    Deluder configuration 
    """
    debug: bool
    ignore_child_processes: bool
    scripts: List[DeluderScriptConfig]
    interceptors: List[DeluderInterceptorConfig]


def create_default_config() -> DeluderConfig:
    """
    Provides default configuration, which is used, when no other configuration is provided by the user
    """
    return DeluderConfig(
        debug=False,
        ignore_child_processes=False,
        scripts=[
            DeluderScriptConfig('winsock'),
            DeluderScriptConfig('openssl'),
            DeluderScriptConfig('schannel'),
        ],
        interceptors=[
            DeluderInterceptorConfig('log')
        ],
    )
