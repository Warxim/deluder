from deluder.interceptors.proxifier.interceptor import ProxifierMessageInterceptor, ProxifierStrategyType
from deluder.common import RecvMessage, SendMessage

from tests.interceptors.proxifier.common import TEST_DATA_INPUT, TEST_DATA_OUTPUT, create_proxy, create_config


def test_proxifier_interceptor_buffer_strategy():
    interceptor = None
    proxy = None
    try:
        proxy = create_proxy()
        proxy.start()

        config = create_config()
        config['strategy'] = ProxifierStrategyType.buffer.value
        config['strategies'] = {
            'buffer': {
                'bufferSize': 1024
            }
        }
        interceptor = ProxifierMessageInterceptor(config)
        interceptor.init()

        for i in range(len(TEST_DATA_INPUT)):
            message = SendMessage('id-1', TEST_DATA_INPUT[i], {})
            interceptor.intercept(None, message)
            assert message.data == TEST_DATA_OUTPUT[i]

        for i in range(len(TEST_DATA_INPUT)):
            message = RecvMessage('id-1', TEST_DATA_INPUT[i], {})
            interceptor.intercept(None, message)
            assert message.data == TEST_DATA_OUTPUT[i]
    finally:
        if interceptor:
            interceptor.destroy()
        
        if proxy:
            proxy.stop()
