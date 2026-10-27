"""Pengujian unit untuk Secure Multiplayer Game Simulator.

Jalankan dari folder source_code:
    python -m unittest discover -s tests -v

Catatan: ``pow(a, b, m)`` hanya dipakai di file pengujian ini sebagai
pembanding independen. Kode utama tidak memakai pemanggilan tersebut.
"""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import diffie_hellman as dh
import elgamal
from mathutil import (
    find_generator,
    gcd,
    generate_prime,
    generate_safe_prime,
    is_generator,
    is_prime,
    mod_exp,
    mod_inverse,
    random_below,
    random_between,
)


class MathUtilityTests(unittest.TestCase):
    """Uji fungsi aritmetika modular dasar."""

    def test_mod_exp_matches_builtin_pow(self):
        """mod_exp harus sama dengan pow(a, b, m) bawaan Python."""
        rng = random.Random(2026)
        for _ in range(80):
            base = rng.randrange(0, 10**12)
            exponent = rng.randrange(0, 5000)
            modulus = rng.randrange(2, 10**9)
            expected = pow(base, exponent, modulus)  # pembanding khusus test
            self.assertEqual(mod_exp(base, exponent, modulus), expected)

    def test_mod_exp_edge_cases(self):
        self.assertEqual(mod_exp(0, 0, 97), 1)
        self.assertEqual(mod_exp(0, 5, 97), 0)
        self.assertEqual(mod_exp(5, 0, 97), 1)
        self.assertEqual(mod_exp(5, 1, 97), 5)
        self.assertEqual(mod_exp(5, 2, 97), 25)

    def test_gcd(self):
        self.assertEqual(gcd(0, 9), 9)
        self.assertEqual(gcd(48, 18), 6)
        self.assertEqual(gcd(-48, 18), 6)
        self.assertEqual(gcd(17, 31), 1)

    def test_extended_gcd_identity(self):
        for a, b in [(240, 46), (17, 31), (0, 9), (-48, 18), (123456, 7890)]:
            g, x, y = __import__("mathutil").extended_gcd(a, b)
            self.assertEqual(a * x + b * y, g)
            self.assertEqual(g, gcd(a, b))

    def test_mod_inverse(self):
        rng = random.Random(7)
        for _ in range(80):
            modulus = rng.randrange(2, 100000)
            value = rng.randrange(1, modulus)
            if gcd(value, modulus) != 1:
                continue
            inverse = mod_inverse(value, modulus)
            self.assertEqual((value * inverse) % modulus, 1)
            self.assertTrue(0 <= inverse < modulus)

    def test_mod_inverse_rejects_non_coprime(self):
        with self.assertRaises(ValueError):
            mod_inverse(6, 9)

    def test_is_prime_known_values(self):
        primes = [2, 3, 5, 7, 11, 13, 97, 997, 7919, 104729, 2147483647]
        composites = [0, 1, 4, 6, 9, 15, 21, 25, 341, 561, 1105, 1729, 2047, 104730]
        for value in primes:
            self.assertTrue(is_prime(value), f"{value} seharusnya prima")
        for value in composites:
            self.assertFalse(is_prime(value), f"{value} seharusnya komposit")

    def test_is_prime_large(self):
        # 2^127 - 1 adalah bilangan prima Mersenne yang diketahui.
        self.assertTrue(is_prime((1 << 127) - 1))
        # 2^128 - 1 jelas komposit (habis dibagi 3, 5, 17, ...).
        self.assertFalse(is_prime((1 << 128) - 1))

    def test_generate_prime_size_and_primality(self):
        for bits in (8, 16, 32):
            prime = generate_prime(bits)
            self.assertEqual(prime.bit_length(), bits)
            self.assertTrue(is_prime(prime))

    def test_safe_prime_and_generator(self):
        for bits in (16, 64):
            p, q = generate_safe_prime(bits)
            self.assertEqual(p, 2 * q + 1)
            self.assertEqual(p.bit_length(), bits)
            self.assertTrue(is_prime(p))
            self.assertTrue(is_prime(q))
            g = find_generator(p, q)
            self.assertTrue(is_generator(g, p, q))

    def test_random_coprime(self):
        from mathutil import random_coprime

        for n in (12, 35, 97, 1000, 65536):
            for _ in range(10):
                value = random_coprime(n)
                self.assertEqual(gcd(value, n), 1)
                self.assertTrue(2 <= value <= n - 1)

    def test_random_below_range(self):
        for limit in (1, 2, 3, 10, 1000):
            for _ in range(20):
                value = random_below(limit)
                self.assertTrue(0 <= value < limit)
        for _ in range(20):
            value = random_between(5, 9)
            self.assertTrue(5 <= value <= 9)


class DiffieHellmanTests(unittest.TestCase):
    """Uji pertukaran kunci Diffie-Hellman."""

    @classmethod
    def setUpClass(cls):
        cls.p, cls.q = generate_safe_prime(16)
        cls.g = find_generator(cls.p, cls.q)
        cls.safe_p, cls.safe_q = generate_safe_prime(128)
        cls.safe_g = find_generator(cls.safe_p, cls.safe_q)

    def test_shared_key_equal_100_random_trials(self):
        """K pemain harus sama dengan K server pada 100 percobaan acak."""
        for _ in range(100):
            result = dh.run_handshake(self.p, self.g)
            self.assertEqual(result["K_player"], result["K_server"])
            self.assertTrue(result["verified"])

    def test_shared_key_equal_safe_mode(self):
        for _ in range(10):
            result = dh.run_handshake(self.safe_p, self.safe_g)
            self.assertEqual(result["K_player"], result["K_server"])
            self.assertTrue(result["verified"])

    def test_public_values_are_in_group(self):
        for _ in range(20):
            player = dh.player_start(self.p, self.g)
            server = dh.server_start(self.p, self.g)
            self.assertTrue(1 < player["A"] < self.p)
            self.assertTrue(1 < server["B"] < self.p)


class ElGamalTests(unittest.TestCase):
    """Uji enkripsi, dekripsi, penyamaran, dan tamper."""

    @classmethod
    def setUpClass(cls):
        cls.params = []
        for bits in (16, 128):
            p, q = generate_safe_prime(bits)
            g = find_generator(p, q)
            cls.params.append((f"{bits}bit", p, q, g))

    def test_encrypt_decrypt_100_messages_both_modes(self):
        """100 pesan acak harus kembali utuh pada Mode Demo dan Mode Aman."""
        for label, p, _q, g in self.params:
            key = elgamal.generate_keypair(p, g)
            for _ in range(100):
                message = random_below(p)
                cipher = elgamal.encrypt(p, g, key["y"], message)
                plain = elgamal.decrypt(p, key["x"], cipher["c1"], cipher["c2"])
                self.assertEqual(plain["message"], message, label)
                self.assertTrue(plain["inverse_ok"], label)

    def test_k_is_coprime_with_p_minus_1(self):
        for _label, p, _q, g in self.params:
            key = elgamal.generate_keypair(p, g)
            for _ in range(20):
                cipher = elgamal.encrypt(p, g, key["y"], random_below(p))
                self.assertEqual(gcd(cipher["k"], p - 1), 1)
                self.assertTrue(1 < cipher["c1"] < p)

    def test_mask_and_unmask(self):
        for _label, p, _q, _g in self.params:
            key = random_below(p)
            for _ in range(50):
                message = random_below(p)
                masked = elgamal.mask_message(message, key, p)
                self.assertEqual(masked, (message + key) % p)
                self.assertEqual(elgamal.unmask_message(masked, key, p), message)

    def test_full_dependency_chain(self):
        """m -> m' -> ElGamal -> m' -> m harus konsisten."""
        for label, p, q, g in self.params:
            handshake = dh.run_handshake(p, g)
            keypair = elgamal.generate_keypair(p, g)
            for _ in range(50):
                message = random_below(p)
                masked = elgamal.mask_message(message, handshake["K_player"], p)
                cipher = elgamal.encrypt(p, g, keypair["y"], masked)
                opened = elgamal.decrypt(p, keypair["x"], cipher["c1"], cipher["c2"])
                recovered_masked = opened["message"]
                recovered = elgamal.unmask_message(
                    recovered_masked, handshake["K_server"], p
                )
                self.assertEqual(recovered, message, label)
                self.assertEqual(handshake["K_player"], handshake["K_server"], label)

    def test_tamper_changes_recovered_message(self):
        """Perubahan c2 harus menghasilkan plaintext berbeda dari m asli."""
        for label, p, _q, g in self.params:
            handshake = dh.run_handshake(p, g)
            keypair = elgamal.generate_keypair(p, g)
            checked = 0
            for _ in range(20):
                message = random_below(p)
                masked = elgamal.mask_message(message, handshake["K_player"], p)
                cipher = elgamal.encrypt(p, g, keypair["y"], masked)

                delta = random_between(1, p - 1)
                tampered_c2 = elgamal.tamper_c2(cipher["c2"], p, delta)
                opened = elgamal.decrypt(p, keypair["x"], cipher["c1"], tampered_c2)
                recovered = elgamal.unmask_message(
                    opened["message"], handshake["K_server"], p
                )

                self.assertNotEqual(recovered, message, label)
                checked += 1
            self.assertEqual(checked, 20)

    def test_tamper_endpoint_value_is_different(self):
        """Simulasi server harus memilih perubahan yang menghasilkan nilai berbeda."""
        p, q = generate_safe_prime(16)
        g = find_generator(p, q)
        handshake = dh.run_handshake(p, g)
        keypair = elgamal.generate_keypair(p, g)
        message = 1
        masked = elgamal.mask_message(message, handshake["K_player"], p)
        cipher = elgamal.encrypt(p, g, keypair["y"], masked)
        tampered_c2 = (cipher["c2"] + 1) % p
        opened = elgamal.decrypt(p, keypair["x"], cipher["c1"], tampered_c2)
        recovered = elgamal.unmask_message(opened["message"], handshake["K_server"], p)
        self.assertNotEqual(recovered, message)


if __name__ == "__main__":
    unittest.main(verbosity=2)