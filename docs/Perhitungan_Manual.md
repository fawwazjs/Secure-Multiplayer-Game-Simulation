# Perhitungan Manual — Parameter Referensi p=23

Dokumen ini memuat perhitungan manual lengkap untuk parameter contoh yang
diminta pada spesifikasi tugas:

- Diffie-Hellman: `p = 23`, `g = 5`, `a = 6`, `b = 15`
- ElGamal: `p = 23`, `g = 5`, `x = 6`, `m = 12`, `k = 3`

Seluruh nilai dihitung ulang oleh program melalui
`source_code/reference_demo.py`. Keluaran aktual skrip tersebut disalin pada
bagian akhir dokumen. Parameter kecil ini **hanya untuk pembelajaran** dan
tidak aman untuk penggunaan nyata.

> Catatan penting tentang aplikasi live: aplikasi web pada `source_code/`
> membangkitkan safe prime 16-bit (Mode Demo) atau 128-bit (Mode Aman) agar
> setiap sesi memiliki parameter baru, dan memakai varian integrasi
> `m' = (m + K) mod p`. Contoh `p=23` di dokumen ini adalah verifikasi
> referensi terpisah untuk memenuhi contoh perhitungan pada spesifikasi.
> Varian integrasi juga dihitung pada bagian 5 agar perbedaan nilai `c2`
> tidak menimbulkan kebingungan.

---

## 1. Pemeriksaan Parameter

Nilai yang dipakai:

```text
p = 23
q = (p - 1) / 2 = 11
g = 5
```

Pemeriksaan:

1. `p = 23` adalah bilangan prima.
2. `q = 11` adalah bilangan prima, sehingga `p = 2q + 1 = 2(11) + 1 = 23`
   adalah **safe prime**.
3. Generator harus memenuhi `g^2 mod p ≠ 1` dan `g^q mod p ≠ 1`:

```text
g^2 mod p = 5^2 mod 23 = 25 mod 23 = 2  (≠ 1)
g^q mod p = 5^11 mod 23 = 22             (≠ 1)
```

Karena kedua syarat terpenuhi, `g = 5` adalah generator (akar primitif)
modulo 23 dan ordernya adalah `p - 1 = 22`.

---

## 2. Diffie-Hellman

### 2.1 Parameter publik

```text
p = 23, g = 5
```

Kedua nilai boleh diketahui oleh Alice, Bob, dan penyadap.

### 2.2 Kunci privat

```text
a = 6   (privat Alice)
b = 15  (privat Bob)
```

Kunci privat tidak dikirim melalui jaringan.

### 2.3 Kunci publik Alice

```text
A = g^a mod p
A = 5^6 mod 23
```

Perhitungan dengan square-and-multiply:

```text
5^1  mod 23 = 5
5^2  mod 23 = 25 mod 23 = 2
5^4  mod 23 = 2^2 = 4
5^6  mod 23 = 5^4 · 5^2 mod 23 = 4 · 2 = 8
```

Jadi:

```text
A = 8
```

### 2.4 Kunci publik Bob

```text
B = g^b mod p
B = 5^15 mod 23 = 19
```

Verifikasi bertahap:

```text
5^1  = 5
5^2  = 25 mod 23 = 2
5^4  = 2^2 = 4
5^8  = 4^2 = 16
5^15 = 5^8 · 5^4 · 5^2 · 5^1 mod 23
     = 16 · 4 · 2 · 5 mod 23
     = 640 mod 23
     = 19
```

Jadi:

```text
B = 19
```

### 2.5 Rahasia bersama dari sisi Alice

```text
K_A = B^a mod p
K_A = 19^6 mod 23
```

Perhitungan:

```text
19^2 = 361 mod 23 = 16
19^4 = 16^2 = 256 mod 23 = 3
19^6 = 19^4 · 19^2 mod 23 = 3 · 16 = 48 mod 23 = 2
```

Jadi:

```text
K_A = 2
```

### 2.6 Rahasia bersama dari sisi Bob

```text
K_B = A^b mod p
K_B = 8^15 mod 23
```

Perhitungan:

```text
8^1  = 8
8^2  = 64 mod 23 = 18
8^4  = 18^2 = 324 mod 23 = 2
8^8  = 2^2 = 4
8^15 = 8^8 · 8^4 · 8^2 · 8^1 mod 23
     = 4 · 2 · 18 · 8 mod 23
     = 1152 mod 23
     = 2
```

Jadi:

```text
K_B = 2
```

### 2.7 Verifikasi

```text
K_A = K_B = 2
```

Pertukaran kunci berhasil karena kedua sisi memperoleh nilai yang sama.
Rahasia bersama `K = 2` tidak pernah dikirim melalui jaringan.

---

## 3. ElGamal Murni (Contoh m=12, k=3)

Bagian ini adalah contoh ElGamal **tanpa topeng DH**, sesuai contoh pada
spesifikasi. Nilai ini yang menghasilkan ciphertext `(c1, c2) = (10, 3)`.

### 3.1 Pembentukan kunci publik

Kunci privat penerima:

```text
x = 6
```

Kunci publik:

```text
y = g^x mod p
y = 5^6 mod 23
```

Karena `5^6 mod 23 = 8` (lihat perhitungan DH di atas), maka:

```text
y = 8
```

Pasangan kunci ElGamal:

```text
Kunci publik : (p, g, y) = (23, 5, 8)
Kunci privat : x = 6
```

Catatan: pasangan kunci ElGamal ini **terpisah** dari kunci privat
Diffie-Hellman. Nilai `x = 6` kebetulan sama dengan `a = 6` hanya karena
contoh akademik menggunakan angka kecil yang sama; secara konseptual
keduanya adalah kunci yang berbeda dan tidak boleh dianggap dapat
dipertukarkan.

### 3.2 Pemilihan bilangan acak k

```text
k = 3
```

Syarat ElGamal: `1 ≤ k ≤ p - 2`, yaitu `1 ≤ k ≤ 21`. Untuk contoh ini juga
dipenuhi `FPB(k, p-1) = FPB(3, 22) = 1`. Mode deterministik dengan `k=3`
hanya untuk reproduksibilitas dan pengujian.

### 3.3 Ciphertext pertama

```text
c1 = g^k mod p
c1 = 5^3 mod 23
c1 = 125 mod 23
c1 = 10
```

### 3.4 Ciphertext kedua

Hitung dahulu:

```text
y^k mod p = 8^3 mod 23
         = 512 mod 23
         = 6
```

Kemudian:

```text
c2 = m · y^k mod p
c2 = 12 · 6 mod 23
c2 = 72 mod 23
c2 = 3
```

Ciphertext:

```text
C = (c1, c2) = (10, 3)
```

### 3.5 Dekripsi

Server menghitung:

```text
s = c1^x mod p
s = 10^6 mod 23
```

Perhitungan bertahap:

```text
10^2 = 100 mod 23 = 8
10^4 = 8^2 = 64 mod 23 = 18
10^6 = 10^4 · 10^2 mod 23 = 18 · 8 = 144 mod 23 = 6
```

Jadi:

```text
s = 6
```

### 3.6 Invers modular

Cari `s^-1 mod 23`, yaitu bilangan `u` sehingga:

```text
6 · u ≡ 1 (mod 23)
```

Extended Euclidean algorithm:

```text
23 = 3 · 6 + 5
 6 = 1 · 5 + 1
 5 = 5 · 1 + 0
```

Substitusi balik:

```text
1 = 6 - 1 · 5
  = 6 - 1 · (23 - 3 · 6)
  = 4 · 6 - 1 · 23
```

Maka koefisien untuk 6 adalah 4:

```text
s^-1 mod 23 = 4
```

Verifikasi:

```text
6 · 4 = 24 ≡ 1 (mod 23)
```

### 3.7 Pemulihan pesan

```text
m = c2 · s^-1 mod p
m = 3 · 4 mod 23
m = 12
```

Hasil dekripsi sama dengan pesan awal:

```text
m' = 12 = m
```

---

## 4. Ringkasan Nilai Referensi

| Tahap | Rumus | Substitusi | Hasil |
|---|---|---|---|
| Kunci publik DH Alice | `A = g^a mod p` | `5^6 mod 23` | `8` |
| Kunci publik DH Bob | `B = g^b mod p` | `5^15 mod 23` | `19` |
| Rahasia Alice | `K_A = B^a mod p` | `19^6 mod 23` | `2` |
| Rahasia Bob | `K_B = A^b mod p` | `8^15 mod 23` | `2` |
| Kunci publik ElGamal | `y = g^x mod p` | `5^6 mod 23` | `8` |
| Ciphertext pertama | `c1 = g^k mod p` | `5^3 mod 23` | `10` |
| Faktor topeng | `y^k mod p` | `8^3 mod 23` | `6` |
| Ciphertext kedua | `c2 = m·y^k mod p` | `12·6 mod 23` | `3` |
| Shared secret dekripsi | `s = c1^x mod p` | `10^6 mod 23` | `6` |
| Invers modular | `s^-1 mod 23` | `6^-1 mod 23` | `4` |
| Pesan hasil dekripsi | `m = c2·s^-1 mod p` | `3·4 mod 23` | `12` |

---

## 5. Varian Integrasi yang Dipakai Aplikasi Live

Aplikasi web memakai lapisan tambahan:

```text
m' = (m + K) mod p
```

Dengan `m = 12` dan `K = 2`:

```text
m' = (12 + 2) mod 23 = 14
```

ElGamal kemudian mengenkripsi `m' = 14`:

```text
c1 = 5^3 mod 23 = 10
y^k mod p = 8^3 mod 23 = 6
c2 = 14 · 6 mod 23 = 84 mod 23 = 15
```

Dekripsi:

```text
s = 10^6 mod 23 = 6
s^-1 mod 23 = 4
m' = c2 · s^-1 mod 23 = 15 · 4 mod 23 = 60 mod 23 = 14
m  = (m' - K) mod 23 = (14 - 2) mod 23 = 12
```

Perbedaan yang harus dipahami:

| Varian | Pesan yang dienkripsi | `c2` |
|---|---|---|
| ElGamal murni (contoh spesifikasi) | `m = 12` | `3` |
| Integrasi aplikasi live | `m' = (m + K) = 14` | `15` |

Keduanya benar pada konteksnya masing-masing. Aplikasi live memakai varian
integrasi agar pesan terikat pada kunci sesi DH; contoh manual `p=23`
memakai ElGamal murni agar sesuai dengan nilai `c2 = 3` pada spesifikasi.

---

## 6. Keluaran Aktual `reference_demo.py`

Perintah:

```text
cd source_code
python reference_demo.py
```

Keluaran (ringkas, nilai aktual):

```text
[PARAMETER]
p                                  23
q = (p-1)/2                        11
p prima                            True
q prima (safe prime)               True
g = 5 generator                    True

[DIFFIE-HELLMAN]
A = g^a mod p                      5^6 mod 23 = 8
B = g^b mod p                      5^15 mod 23 = 19
K_A = B^a mod p                    19^6 mod 23 = 2
K_B = A^b mod p                    8^15 mod 23 = 2
K_A == K_B                         True

[ELGAMAL MURNI - SESUAI CONTOH SPESIFIKASI]
y = g^x mod p                      5^6 mod 23 = 8
k                                  3
c1 = g^k mod p                     5^3 mod 23 = 10
y^k mod p                          6
c2 = m*y^k mod p                   12*6 mod 23 = 3
s = c1^x mod p                     10^6 mod 23 = 6
s^-1 mod p                         6^-1 mod 23 = 4
cek s*s^-1 mod p                   1
m' = c2*s^-1 mod p                 12
m' == m                            True

[VARIAN INTEGRASI APLIKASI LIVE - m' = (m + K) mod p]
K sesi DH                          2
m' = (m + K) mod p                 14
c1                                 10
c2 = m'*y^k mod p                  15
dekripsi ElGamal m'                14
m = (m' - K) mod p                 12

SEMUA NILAI REFERENSI COCOK.
Catatan: parameter kecil ini hanya untuk pembelajaran, bukan produksi.
```

Skrip memakai `assert` untuk memastikan seluruh nilai di atas benar. Jika
salah satu nilai berubah karena bug, skrip akan berhenti dengan
`AssertionError`.

---

## 7. Catatan Keamanan

1. `p = 23` dapat dipecahkan dengan brute force dalam hitungan detik.
2. Diffie-Hellman polos tidak mengautentikasi pihak yang bertukar kunci dan
   rentan man-in-the-middle.
3. ElGamal polos tidak menjamin integritas; perubahan `c2` tetap dapat
   didekripsi menjadi pesan lain.
4. Nilai `k` tidak boleh dipakai ulang pada implementasi nyata.
5. Aplikasi ini adalah demonstrasi akademik, bukan sistem game produksi.