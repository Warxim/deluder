from deluder.interceptors.debug import DebugMessageInterceptor
from deluder.interceptors.proxifier.interceptor import ProxifierMessageInterceptor
from deluder.interceptors.petep.interceptor import PetepMessageInterceptor
from deluder.interceptors.log import LogMessageInterceptor


INTERCEPTORS_REGISTRY = {
    'petep': PetepMessageInterceptor,
    'proxifier': ProxifierMessageInterceptor,
    'log': LogMessageInterceptor,
}
"""
Contains all available interceptors, which can be loaded to Deluder mapped by their code
"""

AVAILABLE_INTERCEPTORS = frozenset(INTERCEPTORS_REGISTRY.keys())
"""
Contains codes of all available interceptors, which can be loaded to Deluder
"""
