import os

from typing import Set


SCRIPTS_PATH = os.path.realpath(os.path.dirname(__file__)) + os.path.sep
COMMON_SCRIPTS = {'common.js', 'config.js'}


def _get_available_scripts() -> Set[str]:
    scripts = set()
    for path in os.listdir(SCRIPTS_PATH):
        if path in COMMON_SCRIPTS or not path.endswith('.js'):
            continue
        scripts.add(path.replace('.js', ''))
    return scripts


AVAILABLE_SCRIPTS = frozenset(_get_available_scripts())
"""
Contains all available scripts, which can be loaded to Deluder
"""

SCRIPTS_DEFAULT_CONFIGS = {
    'winsock': {
        'libs': ["ws2_32.dll", "wsock32.dll"],
        'send': True,
        'sendto': True,
        'recv': True,
        'recvfrom': True,
        'WSASend': True,
        'WSASendTo': True,
        'WSARecv': True,
        'WSARecvFrom': True,
        'shutdown': True,
        'closesocket': True,
    },
    'libc': {
        'libs': ["libc.so"],
        'send': True,
        'sendto': True,
        'recv': True,
        'recvfrom': True,
        'shutdown': True,
        'close': True,
    },
    'openssl': {
        'libs': ["libssl", "openssl", "ssleay", "libeay", "libcrypto"],
        'SSL_write': True,
        'SSL_write_ex': True,
        'SSL_read': True,
        'SSL_read_ex': True,
        'SSL_shutdown': True,
    },
    'gnutls': {
        'libs': ["gnutls"],
        'gnutls_record_send': True,
        'gnutls_record_recv': True,
        'gnutls_bye': True,
    },
    'schannel': {
        'libs': ["Secur32.dll"],
        'EncryptMessage': True,
        'DecryptMessage': True,
    }
}
"""
Contains default values of configurations for all available scripts, which can be loaded to Deluder
"""
