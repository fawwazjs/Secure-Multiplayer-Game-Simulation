"""Fungsi matematika dasar untuk demonstrasi Diffie-Hellman dan ElGamal.

Seluruh fungsi pada modul ini ditulis dari nol dan hanya memakai Python
standard library. Tidak ada pustaka kriptografi, pustaka matematika pihak
ketiga, maupun pemanggilan pemangkatan modular bawaan Python.

Semua bilangan besar diperlakukan sebagai ``int`` bawaan Python. Bilangan
acak diambil dari ``os.urandom`` melalui penolakan (rejection sampling) agar
sebarannya seragam tanpa memakai modul pembangkit rahasia tingkat tinggi.
"""

from __future__ import annotations

import os

# Basis Miller-Rabin. Untuk bilangan 128 bit, 12 basis memberikan peluang
# salah deteksi yang sangat kecil untuk keperluan demonstrasi. Untuk produksi
# kriptografi, jumlah putaran dan ukuran modulus harus jauh lebih besar.
MILLER_RABIN_BASES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)


class MathError(ValueError):
    """Kesalahan parameter pada fungsi matematika."""


def _ensure_int(value: int, name: str) -> int:
    """Pastikan nilai berupa bilangan bulat (bool tidak dianggap int)."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise MathError(f"{name} harus berupa bilangan bulat.")
    return value


def gcd(a: int, b: int) -> int:
    """Hitung FPB(a, b) dengan algoritma Euclidean.

    Langkah: selama b bukan nol, ganti (a, b) dengan (b, a mod b).
    Hasil selalu tidak negatif.
    """
    a = abs(_ensure_int(a, "a"))
    b = abs(_ensure_int(b, "b"))
    while b != 0:
        a, b = b, a % b
    return a


def extended_gcd(a: int, b: int) -> tuple[int, int, int]:
    """Kembalikan (g, x, y) sehingga a*x + b*y = g = FPB(a, b).

    Algoritma extended Euclidean versi iteratif, ditulis eksplisit agar
    mudah diaudit dan ditampilkan pada laporan.
    """
    a = _ensure_int(a, "a")
    b = _ensure_int(b, "b")

    old_r, r = a, b
    old_s, s = 1, 0
    old_t, t = 0, 1

    while r != 0:
        quotient = old_r // r
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s
        old_t, t = t, old_t - quotient * t

    return old_r, old_s, old_t


def mod_inverse(a: int, m: int) -> int:
    """Hitung invers modular a^-1 mod m memakai extended Euclid.

    Syarat: m > 1 dan FPB(a, m) = 1. Hasil berada pada rentang 0..m-1.
    """
    a = _ensure_int(a, "a")
    m = _ensure_int(m, "m")
    if m <= 1:
        raise MathError("Modulus harus lebih besar dari 1.")

    normalized = a % m
    if normalized == 0:
        raise MathError("Nol tidak memiliki invers modular.")

    g, x, _ = extended_gcd(normalized, m)
    if g != 1:
        raise MathError(
            f"Invers tidak ada karena FPB({normalized}, {m}) = {g}."
        )
    return x % m


def mod_exp(base: int, exponent: int, modulus: int) -> int:
    """Hitung base^exponent mod modulus dengan square-and-multiply.

    Algoritma membaca bit eksponen dari yang paling rendah. Setiap langkah
    mengkuadratkan faktor dan mengalikannya ke hasil bila bit bernilai 1.
    Kompleksitas O(log exponent) perkalian modular.
    """
    base = _ensure_int(base, "base")
    exponent = _ensure_int(exponent, "exponent")
    modulus = _ensure_int(modulus, "modulus")

    if modulus <= 1:
        raise MathError("Modulus harus lebih besar dari 1.")
    if exponent < 0:
        raise MathError("Eksponen harus tidak negatif.")

    result = 1
    factor = base % modulus
    remaining = exponent

    while remaining > 0:
        if remaining & 1:                  # bit eksponen sedang aktif
            result = (result * factor) % modulus
        factor = (factor * factor) % modulus  # siapkan pangkat berikutnya
        remaining >>= 1                    # geser ke bit berikutnya

    return result


def _is_small_prime(n: int) -> bool:
    """Uji cepat untuk bilangan kecil dengan pembagian trial division."""
    if n < 2:
        return False
    divisor = 2
    while divisor * divisor <= n:
        if n % divisor == 0:
            return False
        divisor += 1 if divisor == 2 else 2
    return True


# Daftar prima kecil untuk menyaring kandidat sebelum Miller-Rabin.
SMALL_PRIMES = tuple(n for n in range(2, 2000) if _is_small_prime(n))


def is_prime(n: int) -> bool:
    """Uji keprimaan dengan trial division kecil + Miller-Rabin.

    Untuk n < 2000^2, lolosnya trial division sudah cukup untuk menyatakan
    prima. Untuk n yang lebih besar, dilakukan uji Miller-Rabin dengan
    beberapa basis. Ini adalah uji probabilistik, bukan bukti formal.
    """
    n = _ensure_int(n, "n")

    if n < 2:
        return False
    if n in SMALL_PRIMES:
        return True
    for prime in SMALL_PRIMES:
        if n % prime == 0:
            return False
    if n < 2000 * 2000:
        return True

    # Tulis n - 1 = d * 2^s dengan d ganjil.
    d = n - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1

    for base in MILLER_RABIN_BASES:
        if base % n == 0:
            continue
        x = mod_exp(base, d, n)
        if x == 1 or x == n - 1:
            continue

        # Ulangi pengkuadratan sampai s-1 kali.
        for _ in range(s - 1):
            x = (x * x) % n
            if x == n - 1:
                break
        else:
            return False

    return True


def random_bits(bits: int) -> int:
    """Ambil bilangan acak non-negatif dengan tepat ``bits`` bit acak."""
    bits = _ensure_int(bits, "bits")
    if bits <= 0:
        raise MathError("Jumlah bit harus positif.")
    byte_count = (bits + 7) // 8
    raw = int.from_bytes(os.urandom(byte_count), "big")
    return raw & ((1 << bits) - 1)


def random_below(limit: int) -> int:
    """Ambil bilangan acak seragam pada rentang 0 <= x < limit."""
    limit = _ensure_int(limit, "limit")
    if limit <= 0:
        raise MathError("Batas harus positif.")

    bit_count = limit.bit_length()
    while True:
        candidate = random_bits(bit_count)
        if candidate < limit:              # rejection sampling: tolak bias modulo
            return candidate


def random_between(low: int, high: int) -> int:
    """Ambil bilangan acak seragam pada rentang tertutup low..high."""
    low = _ensure_int(low, "low")
    high = _ensure_int(high, "high")
    if low > high:
        raise MathError("Batas bawah tidak boleh melebihi batas atas.")
    return low + random_below(high - low + 1)


def random_coprime(n: int) -> int:
    """Ambil bilangan acak pada 2..n-1 yang koprima dengan n.

    Dipakai untuk memilih k pada ElGamal dengan syarat FPB(k, p-1) = 1.
    """
    n = _ensure_int(n, "n")
    if n <= 2:
        raise MathError("n harus lebih besar dari 2.")

    while True:
        candidate = random_between(2, n - 1)
        if gcd(candidate, n) == 1:
            return candidate


def generate_prime(bits: int) -> int:
    """Bangkitkan bilangan prima acak dengan ukuran tepat ``bits`` bit.

    Kandidat selalu ganjil dan bit teratas diset sehingga ukurannya tepat.
    Kandidat diuji dengan is_prime sebelum dikembalikan.
    """
    bits = _ensure_int(bits, "bits")
    if bits < 2:
        raise MathError("Ukuran prima minimal 2 bit.")

    top_bit = 1 << (bits - 1)
    while True:
        candidate = top_bit | random_below(top_bit) | 1
        if is_prime(candidate):
            return candidate


def generate_safe_prime(bits: int) -> tuple[int, int]:
    """Bangkitkan safe prime p = 2q + 1 dengan p dan q sama-sama prima.

    Mengembalikan pasangan (p, q). Ukuran p tepat ``bits`` bit, sedangkan q
    berukuran ``bits - 1`` bit. Safe prime dipakai agar grup modulo p hanya
    mempunyai subgrup besar berorder prima q.
    """
    bits = _ensure_int(bits, "bits")
    if bits < 3:
        raise MathError("Safe prime minimal 3 bit.")

    top_bit = 1 << (bits - 2)              # q memiliki bits-1 bit
    while True:
        # q kandidat: ganjil dan bit teratasnya diset.
        q = top_bit | random_below(top_bit) | 1
        p = 2 * q + 1
        if p.bit_length() != bits:
            continue

        # Penyaringan murah: jika q atau p habis dibagi prima kecil, lewati.
        rejected = False
        for prime in SMALL_PRIMES[1:]:
            if q % prime == 0 or p % prime == 0:
                rejected = True
                break
        if rejected:
            continue

        if is_prime(q) and is_prime(p):
            return p, q


def find_generator(p: int, q: int) -> int:
    """Cari generator g untuk grup modulo p = 2q + 1.

    Syarat generator penuh:
      - g^2 mod p != 1  (bukan elemen order 1 atau 2)
      - g^q mod p != 1  (bukan elemen order q)
    Dengan p safe prime, lolosnya kedua syarat berarti order(g) = 2q.
    """
    p = _ensure_int(p, "p")
    q = _ensure_int(q, "q")
    if p <= 5 or p != 2 * q + 1:
        raise MathError("p harus berbentuk 2q + 1.")
    if not is_prime(p) or not is_prime(q):
        raise MathError("p dan q harus prima.")

    while True:
        candidate = random_between(2, p - 2)
        if mod_exp(candidate, 2, p) == 1:
            continue
        if mod_exp(candidate, q, p) == 1:
            continue
        return candidate


def is_generator(g: int, p: int, q: int) -> bool:
    """Periksa apakah g memenuhi syarat generator untuk p = 2q + 1."""
    if not (2 <= g <= p - 2):
        return False
    return (
        mod_exp(g, 2, p) != 1
        and mod_exp(g, q, p) != 1
    )


def mod_exp_trace(base: int, exponent: int, modulus: int) -> dict[str, object]:
    """Square-and-multiply beserta tabel langkah untuk ditampilkan.

    Fungsi ini memakai algoritma yang sama dengan :func:`mod_exp`, tetapi
    merekam bit, faktor, hasil sebelum, dan hasil sesudah setiap langkah.
    Cocok untuk demonstrasi manual parameter kecil.
    """
    base = _ensure_int(base, "base")
    exponent = _ensure_int(exponent, "exponent")
    modulus = _ensure_int(modulus, "modulus")
    if modulus <= 1:
        raise MathError("Modulus harus lebih besar dari 1.")
    if exponent < 0:
        raise MathError("Eksponen harus tidak negatif.")

    result = 1
    factor = base % modulus
    remaining = exponent
    steps: list[dict[str, int | bool]] = []
    bit_index = 0

    while remaining > 0:
        bit = remaining & 1
        before = result
        multiplied = False
        if bit:
            result = (result * factor) % modulus
            multiplied = True
        steps.append(
            {
                "bit_index": bit_index,
                "bit": bit,
                "factor": factor,
                "result_before": before,
                "result_after": result,
                "multiplied": multiplied,
            }
        )
        factor = (factor * factor) % modulus
        remaining >>= 1
        bit_index += 1

    return {
        "base": base,
        "exponent": exponent,
        "modulus": modulus,
        "binary": format(exponent, "b"),
        "steps": steps,
        "result": result,
    }


def mod_inverse_trace(value: int, modulus: int) -> dict[str, object]:
    """Extended Euclidean beserta tabel langkah dan hasil invers.

    Selain koefisien Bezout, fungsi mengembalikan pemeriksaan
    ``(value * inverse) mod modulus == 1`` agar hasil dapat diverifikasi
    langsung pada antarmuka.
    """
    value = _ensure_int(value, "value")
    modulus = _ensure_int(modulus, "modulus")
    if modulus <= 1:
        raise MathError("Modulus harus lebih besar dari 1.")

    normalized = value % modulus
    if normalized == 0:
        raise MathError("Nol tidak memiliki invers modular.")

    old_r, r = normalized, modulus
    old_s, s = 1, 0
    old_t, t = 0, 1
    steps: list[dict[str, int]] = []

    while r != 0:
        quotient = old_r // r
        remainder = old_r - quotient * r
        steps.append(
            {
                "dividend": old_r,
                "divisor": r,
                "quotient": quotient,
                "remainder": remainder,
            }
        )
        old_r, r = r, remainder
        old_s, s = s, old_s - quotient * s
        old_t, t = t, old_t - quotient * t

    if old_r != 1:
        raise MathError(
            f"Invers tidak ada karena FPB({normalized}, {modulus}) = {old_r}."
        )

    inverse = old_s % modulus
    check = (normalized * inverse) % modulus
    if check != 1:
        raise MathError("Verifikasi invers gagal.")

    return {
        "value": value,
        "normalized_value": normalized,
        "modulus": modulus,
        "gcd": old_r,
        "coefficient_a": old_s,
        "coefficient_b": old_t,
        "steps": steps,
        "inverse": inverse,
        "check": check,
        "check_expression": (
            f"({normalized} x {inverse}) mod {modulus} = {check}"
        ),
    }
