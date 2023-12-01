from deluder.common import *
from deluder.interceptor import MessageInterceptor


class DebugMessageInterceptor(MessageInterceptor):
    """
    Debugging interceptor, which logs the whole message as is to the standard output
    """
    def intercept(self, process: Process, message: Message):
        self.logger.debug(f'Message [pid={process.pid}]: {message}')
