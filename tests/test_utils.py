from tests.utils import generate_all_bytes, load_file
from deluder.utils import format_bytes


def test_format_bytes():
    expected_text = load_file("tests/data/utils_format_bytes.txt").decode("latin1")
    all_bytes = generate_all_bytes()
    actual_text = format_bytes(all_bytes)

    assert actual_text == expected_text.replace("\r", "")
