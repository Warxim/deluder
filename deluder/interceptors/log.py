from deluder.common import *
from deluder.interceptor import MessageInterceptor
from deluder.utils import format_bytes


class LogMessageInterceptor(MessageInterceptor):
    """
    Basic logging interceptor, which logs messages into standard output in human readable hex table format
    """
    def intercept(self, process: Process, message: Message):
        if isinstance(message, DataMessage):
            self.logger.info(f'Message [pid={process.pid}] - {message.type.name}: {message.metadata}\n{format_bytes(message.data)}')
        else:
            self.logger.info(f'Message [pid={process.pid}] - {message.type.name}: {message.metadata}')
