from pathlib import Path


def load_file(path: str) -> bytes:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"{path} does not exist")
    return path.read_bytes()


def generate_all_bytes() -> bytes:
    byte_array = []
    byte = 0x00
    while byte != 0xFF:
        byte_array.append(byte)
        byte += 0x01
    byte_array.append(byte)
    return bytes(byte_array)
