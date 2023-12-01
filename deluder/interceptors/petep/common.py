from enum import Enum


class PetepDeluderMessageType(Enum):
    """
    Standard message types between Deluder and PETEP
    """
    CONNECTION_INFO = 1
    DATA_C2S = 2
    DATA_S2C = 3
