import sys
from xtea import new, MODE_ECB, XTEACipher


_rounds: int = 64
_byte_order: str = sys.byteorder
_key: list[int] = None
_key_string: bytes = None
_xtea: XTEACipher = None

def setup(rounds: int = 64, byte_order: str = sys.byteorder, key_segment: list[int] = None):
    global _rounds, _byte_order, _key, _key_string, _xtea

    if len(key_segment) != 4:
        raise ValueError("Key must be 4 integers long.")

    _rounds = rounds
    _byte_order = byte_order


    _key = key_segment
    _key_string = b""
    for key_segment in _key:
        _key_string += key_segment.to_bytes(4, byteorder=_byte_order, signed=False)

    _xtea = new(_key_string, mode=MODE_ECB, rounds=_rounds, endian="<" if _byte_order == "little" else ">")
    print(f"Key set to {_key}.")

def pad_data(data: bytes, length: int = 8) -> bytes:
    """Pads the data to the specified length.

    Args:
        data (bytes): The data to pad.

    Returns:
        bytes: The padded data.
    """
    missing_bytes = (length - len(data) % length) % length

    return data + b"\x00" * missing_bytes

def decrypt(data: bytes) -> bytes:
    """Decrypts the given data using the XTEA algorithm.

    Args:
        data (bytes): The data to decrypt.

    Returns:
        bytes: The decrypted data.
    """
    decrypted_data = _xtea.decrypt(pad_data(data))

    return decrypted_data

def encrypt(data: bytes) -> bytes:
    """Encrypts the given data using the XTEA algorithm.

    Args:
        data (bytes): The data to encrypt.

    Returns:
        bytes: The encrypted data.
    """
    encrypted_data = _xtea.encrypt(pad_data(data))

    return encrypted_data

def is_ready() -> bool:
    """Checks if the XTEA cipher is set up.

    Returns:
        bool: True if the XTEA cipher is set up, False otherwise.
    """
    return _xtea is not None
