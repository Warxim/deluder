from typing import Optional

from deluder.common import *
from deluder.interceptor import MessageInterceptor
from deluder.converter import MessageConverter
from deluder.log import logger


class MessageRouter:
    """
    Router lets messages go through interceptors and routes them back to the originating process script.
    """
    def __init__(self, interceptors: List[MessageInterceptor]):
        self.interceptors = interceptors

    def route(self, process: Process, message: dict, data: Optional[bytes]):
        """
        Routes given message and data through interceptors and back to the originating script.
        """
        message = MessageConverter.convert(message, data)
        if not message:
            return
        
        for interceptor in self.interceptors:
            try:
                interceptor.intercept(process, message)
            except Exception as e:
                logger.error('Intercept in %s failed!', interceptor.get_name(), exc_info=e)

        if isinstance(message, DataMessage):
            response = self._create_data_message_response(message)
            process.script.post(response)
        elif isinstance(message, CloseMessage):
            pass # No action needed
        else:
            raise ValueError(f'Unsupported message {message}!')

    @staticmethod
    def _create_data_message_response(message: DataMessage):
        return {
            'type': message.id,
            'id': message.id,
            'data': list(message.data),
            'metadata': message.metadata,
        }
