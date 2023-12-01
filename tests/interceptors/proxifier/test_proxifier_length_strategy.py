from deluder.interceptors.proxifier.interceptor import ProxifierMessageInterceptor, ProxifierStrategyType
from deluder.common import RecvMessage, SendMessage

from tests.interceptors.proxifier.common import TEST_DATA_INPUT, TEST_DATA_OUTPUT, create_proxy, create_config, data_inteceptor


def test_proxifier_interceptor_length_strategy():
    interceptor = None
    proxy = None
    try:
        proxy = create_proxy(interceptor=data_inteceptor_with_length)
        proxy.start()

        config = create_config()
        config['strategy'] = ProxifierStrategyType.length.value
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


def data_inteceptor_with_length(data: bytes) -> bytes:
    new_data = data_inteceptor(data)
    length = len(new_data) - 4
    length_bytes = length.to_bytes(4, byteorder='big')
        
    payload = bytearray()
    payload.extend(length_bytes)
    payload.extend(new_data[4:])
    return payload
