"""Verifikasi contoh parameter p=23 yang diminta pada spesifikasi tugas.

Skrip ini memakai modul kriptografi proyek (mathutil, diffie_hellman,
elgamal) dan memeriksa nilai-nilai referensi:

  Diffie-Hellman : p=23, g=5, a=6, b=15
                   A=8, B=19, K_A=K_B=2
  ElGamal        : p=23, g=5, x=6, y=8, m=12, k=3
                   c1=10, c2=3, s=6, s^-1=4, m'=12

Skrip juga menunjukkan varian integrasi yang dipakai aplikasi live:
m' = (m + K) mod p. Varian ini sengaja dibedakan agar nilai c2=3 dari
contoh ElGamal murni tidak tertukar dengan c2=15 pada varian bertopeng.

Jalankan dari folder source_code:
    python reference_demo.py
"""

from __future__ import annotations

from diffie_hellman import public_value, shared_secret
from elgamal import decrypt, encrypt, mask_message, unmask_message
from mathutil import is_generator, is_prime, mod_exp, mod_exp_trace, mod_inverse

P = 23
G = 5
A_PRIVATE = 6
B_PRIVATE = 15
X = 6
M = 12
K = 3


def line(label: str, value: object) -> None:
    print(f"{label:<34} {value}")


def main() -> None:
    print("=" * 68)
    print("VERIFIKASI REFERENSI p=23 — SECURE MULTIPLAYER GAME SIMULATOR")
    print("=" * 68)

    q = (P - 1) // 2
    print("\n[PARAMETER]")
    line("p", P)
    line("q = (p-1)/2", q)
    line("p prima", is_prime(P))
    line("q prima (safe prime)", is_prime(q))
    line("g = 5 generator", is_generator(G, P, q))

    print("\n[DIFFIE-HELLMAN]")
    public_a = public_value(G, A_PRIVATE, P)
    public_b = public_value(G, B_PRIVATE, P)
    shared_a = shared_secret(public_b, A_PRIVATE, P)
    shared_b = shared_secret(public_a, B_PRIVATE, P)
    line("A = g^a mod p", f"5^{A_PRIVATE} mod {P} = {public_a}")
    line("B = g^b mod p", f"5^{B_PRIVATE} mod {P} = {public_b}")
    line("K_A = B^a mod p", f"{public_b}^{A_PRIVATE} mod {P} = {shared_a}")
    line("K_B = A^b mod p", f"{public_a}^{B_PRIVATE} mod {P} = {shared_b}")
    line("K_A == K_B", shared_a == shared_b and shared_a == 2)
    assert (public_a, public_b, shared_a, shared_b) == (8, 19, 2, 2)

    print("\n[SQUARE-AND-MULTIPLY A = 5^6 mod 23]")
    trace = mod_exp_trace(5, 6, 23)
    print("i | bit | faktor | sebelum | sesudah | dikali")
    for step in trace["steps"]:
        print(
            f"{step['bit_index']} | {step['bit']:>3} | {step['factor']:>6} | "
            f"{step['result_before']:>7} | {step['result_after']:>7} | "
            f"{'ya' if step['multiplied'] else 'tidak'}"
        )
    line("hasil", trace["result"])
    assert trace["result"] == 8

    print("\n[ELGAMAL MURNI — SESUAI CONTOH SPESIFIKASI]")
    y = mod_exp(G, X, P)
    line("y = g^x mod p", f"5^{X} mod {P} = {y}")
    encrypted = encrypt(P, G, y, M, K)
    line("k", K)
    line("c1 = g^k mod p", f"5^{K} mod {P} = {encrypted['c1']}")
    line("y^k mod p", encrypted["yk"])
    line("c2 = m*y^k mod p", f"{M}*{encrypted['yk']} mod {P} = {encrypted['c2']}")
    decrypted = decrypt(P, X, encrypted["c1"], encrypted["c2"])
    line("s = c1^x mod p", f"{encrypted['c1']}^{X} mod {P} = {decrypted['s']}")
    line("s^-1 mod p", f"{decrypted['s']}^-1 mod {P} = {decrypted['s_inv']}")
    line("cek s*s^-1 mod p", (decrypted["s"] * decrypted["s_inv"]) % P)
    line("m' = c2*s^-1 mod p", decrypted["message"])
    line("m' == m", decrypted["message"] == M)
    assert encrypted["c1"] == 10
    assert encrypted["c2"] == 3
    assert decrypted["s"] == 6
    assert decrypted["s_inv"] == 4
    assert decrypted["message"] == 12
    assert mod_inverse(6, 23) == 4

    print("\n[VARIAN INTEGRASI APLIKASI LIVE — m' = (m + K) mod p]")
    masked = mask_message(M, shared_a, P)
    encrypted_masked = encrypt(P, G, y, masked, K)
    decrypted_masked = decrypt(P, X, encrypted_masked["c1"], encrypted_masked["c2"])
    restored = unmask_message(decrypted_masked["message"], shared_a, P)
    line("K sesi DH", shared_a)
    line("m' = (m + K) mod p", masked)
    line("c1", encrypted_masked["c1"])
    line("c2 = m'*y^k mod p", encrypted_masked["c2"])
    line("dekripsi ElGamal m'", decrypted_masked["message"])
    line("m = (m' - K) mod p", restored)
    assert masked == 14
    assert encrypted_masked["c2"] == 15
    assert decrypted_masked["message"] == 14
    assert restored == 12

    print("\nSEMUA NILAI REFERENSI COCOK.")
    print("Catatan: parameter kecil ini hanya untuk pembelajaran, bukan produksi.")


if __name__ == "__main__":
    main()