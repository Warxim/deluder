from copy import copy
from typing import Optional

from deluder.common import *
from deluder.log import logger


class MessageConverter:
    """
    Converter for converting Frida's dictionaries and bytes to common data classes used in Deluder
    to distinguish different intercepted messages.
    """
    @staticmethod
    def convert(message: dict, data: Optional[bytes]) -> Optional[Message]:
        """
        Converts message dictionary and data bytes to common message types
        (SendMessage, RecvMessage and CloseMessage)
        """
        if message['type'] != 'send':
            if data is None:
                logger.info('Message received %s', message)
            else:
                logger.info('Message received %s with data %s', message, data)
            return

        id = message['payload']['id']
        type = message['payload']['type']

        metadata = copy(message['payload'])
        metadata.pop('id')
        metadata.pop('type')

        if type == MessageType.SEND:
            return SendMessage(id, data, metadata)
        elif type == MessageType.RECV:
            return RecvMessage(id, data, metadata)
        elif type == MessageType.CLOSE:
            return CloseMessage(id, metadata)
        else:
            raise ValueError(f'Unsupported message type {type}!')
