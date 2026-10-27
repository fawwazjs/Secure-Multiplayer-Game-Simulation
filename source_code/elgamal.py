"""Implementasi ElGamal dari nol untuk pesan numerik.

Skema:
  Kunci privat x, kunci publik y = g^x mod p.
  Enkripsi pesan m (0 <= m < p):
      k acak dengan FPB(k, p-1) = 1
      c1 = g^k mod p
      c2 = m * y^k mod p
  Dekripsi:
      s = c1^x mod p
      m = c2 * s^(-1) mod p

Semua operasi memakai fungsi modular buatan sendiri pada mathutil.py.
"""

from __future__ import annotations

from mathutil import MathError, gcd, mod_exp, mod_inverse, random_between, random_coprime


class ElGamalError(ValueError):
    """Kesalahan pada proses ElGamal."""


def generate_keypair(p: int, g: int) -> dict[str, int]:
    """Bangkitkan kunci ElGamal server.

    x dipilih acak pada 2..p-2, lalu y = g^x mod p.
    """
    if p <= 5:
        raise ElGamalError("Modulus terlalu kecil untuk ElGamal.")
    x = random_between(2, p - 2)
    y = mod_exp(g, x, p)
    return {"x": x, "y": y}


def choose_k(p: int) -> int:
    """Pilih k acak dengan syarat FPB(k, p-1) = 1.

    Syarat ini menjamin s = c1^x = g^(kx) tidak bernilai nol, sehingga
    invers modularnya selalu ada saat dekripsi.
    """
    if p <= 5:
        raise ElGamalError("Modulus terlalu kecil untuk ElGamal.")
    return random_coprime(p - 1)


def encrypt(
    p: int,
    g: int,
    y: int,
    message: int,
    k: int | None = None,
) -> dict[str, int]:
    """Enkripsi pesan numerik dengan kunci publik server.

    Mengembalikan k, c1, c2, dan yk (y^k mod p) agar tahapan dapat
    ditampilkan pada antarmuka. ``k`` boleh diberikan untuk pengujian,
    tetapi harus memenuhi FPB(k, p-1) = 1.
    """
    if not (0 <= message < p):
        raise ElGamalError("Pesan harus memenuhi 0 <= m < p.")
    if not (1 < y < p):
        raise ElGamalError("Kunci publik y tidak valid.")

    if k is None:
        k = choose_k(p)
    else:
        if not (2 <= k <= p - 2) or gcd(k, p - 1) != 1:
            raise ElGamalError("k harus koprima dengan p-1 dan berada di 2..p-2.")

    c1 = mod_exp(g, k, p)
    yk = mod_exp(y, k, p)
    c2 = (message * yk) % p
    return {"k": k, "c1": c1, "c2": c2, "yk": yk}


def decrypt(p: int, x: int, c1: int, c2: int) -> dict[str, int | bool]:
    """Dekripsi ciphertext (c1, c2) dengan kunci privat server.

    s = c1^x mod p
    s_inv = s^(-1) mod p
    m = c2 * s_inv mod p
    """
    if not (1 <= c1 < p):
        raise ElGamalError("c1 harus berada pada 1..p-1 agar invers tersedia.")
    if not (0 <= c2 < p):
        raise ElGamalError("c2 harus berada pada 0..p-1.")
    if not (2 <= x <= p - 2):
        raise ElGamalError("Kunci privat x tidak valid.")

    try:
        s = mod_exp(c1, x, p)
        s_inv = mod_inverse(s, p)
    except MathError as exc:
        raise ElGamalError(str(exc)) from exc

    message = (c2 * s_inv) % p
    return {
        "s": s,
        "s_inv": s_inv,
        "message": message,
        "inverse_ok": (s * s_inv) % p == 1,
    }


def mask_message(message: int, shared_key: int, p: int) -> int:
    """Siapkan pesan bertopeng m' = (m + K) mod p."""
    if not (0 <= message < p):
        raise ElGamalError("Pesan asli harus memenuhi 0 <= m < p.")
    if not (0 <= shared_key < p):
        raise ElGamalError("Kunci bersama K harus berada pada 0..p-1.")
    return (message + shared_key) % p


def unmask_message(masked_message: int, shared_key: int, p: int) -> int:
    """Pulihkan pesan m = (m' - K) mod p setelah dekripsi ElGamal."""
    if not (0 <= masked_message < p):
        raise ElGamalError("Pesan bertopeng harus berada pada 0..p-1.")
    if not (0 <= shared_key < p):
        raise ElGamalError("Kunci bersama K harus berada pada 0..p-1.")
    return (masked_message - shared_key) % p


def tamper_c2(c2: int, p: int, delta: int) -> int:
    """Ubah ciphertext c2 di tengah jaringan: c2' = (c2 + delta) mod p.

    Perubahan sekecil apa pun pada c2 akan mengubah hasil dekripsi. Karena
    ElGamal polos tidak memiliki tag autentikasi, server tidak dapat
    membedakan ciphertext asli dan palsu hanya dari operasi matematika.
    """
    if not (0 <= c2 < p):
        raise ElGamalError("c2 harus berada pada 0..p-1.")
    if delta == 0:
        raise ElGamalError("Perubahan c2 tidak boleh nol.")
    return (c2 + delta) % p
