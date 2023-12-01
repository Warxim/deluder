import itertools
import socket


SPACE_BYTE = 46


def try_close(sock: socket.socket):
    """
    Tries to close the socket
    """
    try:
        if sock is not None:
            sock.close()
    except:
        pass


def recv_n(receiving_sock: socket.socket, n: int) -> bytes:
    """
    Receives exactly specified amount of bytes from the socket
    """
    remaining = n
    total_data = bytearray()
    while remaining != 0:
        data = receiving_sock.recv(remaining)
        if len(data) == 0:
            raise Exception('Connection lost, please restart deluder!')
        total_data.extend(data)
        remaining = n - len(total_data)
    return total_data


def format_bytes(data: bytes) -> str:
    """
    Formats given bytes to human readable format (hex table)
    """
    data = _replace_invisible_chars(data)

    text = ''
    line = '        '
    line += ' ' * 2
    line += ' '.join('{:2x}'.format(x).upper() for x in range(16))
    line += ' ' * 2
    line += ''.join('{:1x}'.format(x).upper() for x in range(16))
    text += line + '\n'

    part_index = 0
    for part in _partition(data, 16):
        line = ''.join('{:08x}'.format(part_index).upper())
        line += ' ' * 2
        line += _add_padding_to_line(' '.join('{:02x}'.format(x) for x in part), 47)
        line += ' ' * 2
        line += bytes(part).decode('latin1')
        text += line + '\n'
        part_index += 16

    return text


def _partition(array: bytes, size: int):
    for i in range(0, len(array), size):
        yield bytes(itertools.islice(array, i, i + size))


def _add_padding_to_line(line: str, length: int) -> str:
    padding = (length - len(line)) * ' ' 
    return line + padding


def _replace_invisible_chars(data: bytes) -> bytes:
    new_bytes = bytearray(data)
    for i in range(len(data)):
        if data[i] >= 0 and data[i] < 32:
            new_bytes[i] = SPACE_BYTE
    return new_bytes
