"""Implementasi pertukaran kunci Diffie-Hellman dari nol.

Pemain dan server sama-sama memilih eksponen rahasia. Keduanya hanya
mengirim nilai publik A atau B. Rahasia bersama K dihitung dari nilai publik
lawan dan eksponen rahasia sendiri, sehingga K tidak pernah melewati jaringan.
"""

from __future__ import annotations

from mathutil import MathError, mod_exp, random_between


class DHError(ValueError):
    """Kesalahan pada protokol Diffie-Hellman."""


def choose_private_exponent(p: int) -> int:
    """Pilih eksponen rahasia pada rentang 2..p-2.

    Rentang ini menghindari nilai trivial 0, 1, dan p-1 yang dapat membuat
    kunci publik bernilai 1 atau p-1.
    """
    if p <= 5:
        raise DHError("Modulus terlalu kecil untuk Diffie-Hellman.")
    return random_between(2, p - 2)


def public_value(g: int, private_value: int, p: int) -> int:
    """Hitung nilai publik A = g^a mod p atau B = g^b mod p."""
    if not (2 <= g <= p - 2):
        raise DHError("Generator g tidak valid.")
    if not (2 <= private_value <= p - 2):
        raise DHError("Eksponen rahasia di luar rentang yang diizinkan.")
    return mod_exp(g, private_value, p)


def shared_secret(peer_public: int, private_value: int, p: int) -> int:
    """Hitung K = (nilai publik lawan)^(rahasia sendiri) mod p."""
    if not (1 < peer_public < p):
        raise DHError("Nilai publik lawan berada di luar grup.")
    if not (2 <= private_value <= p - 2):
        raise DHError("Eksponen rahasia di luar rentang yang diizinkan.")
    return mod_exp(peer_public, private_value, p)


def player_start(p: int, g: int) -> dict[str, int]:
    """Langkah 2a: pemain memilih a dan menghitung A = g^a mod p."""
    a = choose_private_exponent(p)
    A = public_value(g, a, p)
    return {"a": a, "A": A}


def server_start(p: int, g: int) -> dict[str, int]:
    """Langkah 2b: server memilih b dan menghitung B = g^b mod p."""
    b = choose_private_exponent(p)
    B = public_value(g, b, p)
    return {"b": b, "B": B}


def compute_shared_keys(
    p: int,
    a: int,
    b: int,
    A: int,
    B: int,
) -> dict[str, object]:
    """Langkah 2c-2d: hitung K dari kedua sisi dan bandingkan.

    Pemain menghitung K_pemain = B^a mod p.
    Server menghitung K_server = A^b mod p.
    Secara matematis keduanya sama karena (g^b)^a = (g^a)^b = g^(ab).
    """
    K_player = shared_secret(B, a, p)
    K_server = shared_secret(A, b, p)
    return {
        "K_player": K_player,
        "K_server": K_server,
        "verified": K_player == K_server,
    }


def run_handshake(p: int, g: int) -> dict[str, int | bool]:
    """Jalankan satu pertukaran DH lengkap untuk kebutuhan pengujian."""
    player = player_start(p, g)
    server = server_start(p, g)
    keys = compute_shared_keys(p, player["a"], server["b"], player["A"], server["B"])
    return {
        "a": player["a"],
        "A": player["A"],
        "b": server["b"],
        "B": server["B"],
        "K_player": keys["K_player"],
        "K_server": keys["K_server"],
        "verified": keys["verified"],
    }


def validate_parameters(p: int, q: int, g: int) -> bool:
    """Validasi ringan parameter DH: p = 2q+1 dan 1 < g < p-2."""
    try:
        return (
            p == 2 * q + 1
            and p > 5
            and 2 <= g <= p - 2
            and mod_exp(g, q, p) != 1
            and mod_exp(g, 2, p) != 1
        )
    except MathError:
        return False
