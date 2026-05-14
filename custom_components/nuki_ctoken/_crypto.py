"""Pure-Python XSalsa20-Poly1305 (NaCl SecretBox) — no native dependencies."""
from __future__ import annotations

import struct

_SIGMA = (0x61707865, 0x3320646e, 0x79622d32, 0x6b206574)


def _u32(x: int) -> int:
    return x & 0xFFFFFFFF


def _rot32(x: int, n: int) -> int:
    return _u32(x << n) | (x >> (32 - n))


def _qr(z: list[int], a: int, b: int, c: int, d: int) -> None:
    z[b] ^= _rot32(_u32(z[a] + z[d]), 7)
    z[c] ^= _rot32(_u32(z[b] + z[a]), 9)
    z[d] ^= _rot32(_u32(z[c] + z[b]), 13)
    z[a] ^= _rot32(_u32(z[d] + z[c]), 18)


def _salsa20_block(x: list[int]) -> bytes:
    z = list(x)
    for _ in range(10):
        _qr(z, 0, 4, 8, 12); _qr(z, 5, 9, 13, 1); _qr(z, 10, 14, 2, 6); _qr(z, 15, 3, 7, 11)
        _qr(z, 0, 1, 2, 3);  _qr(z, 5, 6, 7, 4);  _qr(z, 10, 11, 8, 9); _qr(z, 15, 12, 13, 14)
    return struct.pack("<16I", *[_u32(z[i] + x[i]) for i in range(16)])


def _hsalsa20(key32: bytes, nonce16: bytes) -> bytes:
    k = struct.unpack_from("<8I", key32)
    n = struct.unpack_from("<4I", nonce16)
    z: list[int] = [
        _SIGMA[0], k[0], k[1], k[2], k[3], _SIGMA[1],
        n[0], n[1], n[2], n[3],
        _SIGMA[2], k[4], k[5], k[6], k[7], _SIGMA[3],
    ]
    for _ in range(10):
        _qr(z, 0, 4, 8, 12); _qr(z, 5, 9, 13, 1); _qr(z, 10, 14, 2, 6); _qr(z, 15, 3, 7, 11)
        _qr(z, 0, 1, 2, 3);  _qr(z, 5, 6, 7, 4);  _qr(z, 10, 11, 8, 9); _qr(z, 15, 12, 13, 14)
    # HSalsa20: diagonal + input words, WITHOUT adding back initial state
    return struct.pack("<8I", z[0], z[5], z[10], z[15], z[6], z[7], z[8], z[9])


def _xsalsa20_keystream(key32: bytes, nonce24: bytes, length: int) -> bytes:
    subkey = _hsalsa20(key32, nonce24[:16])
    k = struct.unpack_from("<8I", subkey)
    n0, n1 = struct.unpack_from("<2I", nonce24[16:])
    out = bytearray()
    ctr = 0
    while len(out) < length:
        x: list[int] = [
            _SIGMA[0], k[0], k[1], k[2], k[3], _SIGMA[1],
            n0, n1, ctr & 0xFFFFFFFF, (ctr >> 32) & 0xFFFFFFFF,
            _SIGMA[2], k[4], k[5], k[6], k[7], _SIGMA[3],
        ]
        out += _salsa20_block(x)
        ctr += 1
    return bytes(out[:length])


def _poly1305(msg: bytes, key32: bytes) -> bytes:
    P = (1 << 130) - 5
    r = int.from_bytes(key32[:16], "little") & 0x0ffffffc0ffffffc0ffffffc0fffffff
    s = int.from_bytes(key32[16:], "little")
    acc = 0
    for i in range(0, len(msg), 16):
        chunk = msg[i : i + 16]
        n = (
            int.from_bytes(chunk + b"\x01", "little")
            if len(chunk) < 16
            else int.from_bytes(chunk, "little") + (1 << 128)
        )
        acc = r * (acc + n) % P
    return ((acc + s) & ((1 << 128) - 1)).to_bytes(16, "little")


def secretbox_encrypt(message: bytes, nonce24: bytes, key32: bytes) -> bytes:
    """XSalsa20-Poly1305 encrypt. Returns mac (16 B) + ciphertext."""
    stream = _xsalsa20_keystream(key32, nonce24, 32 + len(message))
    ciphertext = bytes(a ^ b for a, b in zip(message, stream[32:]))
    return _poly1305(ciphertext, stream[:32]) + ciphertext
