from deluder.common import *
from deluder.log import create_logger


class MessageInterceptor:
    """
    Base class for message interceptors
    """
    def __init__(self, config: Dict[str, any]=dict()):
        full_config = self.default_config()
        full_config.update(config)
        self.config = full_config
        self.logger = create_logger(self.get_name())

    @classmethod
    def default_config(cls) -> dict:
        """
        Default interceptor configuration, which can be overriden in config.json file
        """
        return {}

    def get_name(self) -> str:
        """
        Obtains name of the interceptor
        """
        return self.__class__.__name__.replace('MessageInterceptor', '')

    def init(self):
        """
        Inititializes the interceptor when Deluder starts
        """
        pass

    def intercept(self, process: Process, message: Message):
        """
        Intercepts message from given process
        """
        pass

    def destroy(self):
        """
        Destroys the interceptor when Deluder stops
        """
        pass
