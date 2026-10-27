# Secure Multiplayer Game Simulator

**Mata Kuliah:** Kriptografi (C)  
**Kelompok:** Kelompok 4

| Nama | NRP |
|---|---|
| Ahmad Wildan Fawwaz | 5027241001 |
| Dimas Satya Andhika | 5027241032 |
| Daniswara Fausta Novanto | 5027241050 |

**Dosen Pengampu:** Annisaa Sri Indrawanti, S.Kom., M.Kom.  
**Departemen:** Teknologi Informasi  
**Institusi:** Institut Teknologi Sepuluh Nopember

## Deskripsi

Secure Multiplayer Game Simulator adalah aplikasi web edukatif yang memperlihatkan bagaimana data aksi pemain dikirim ke server game melalui Diffie-Hellman dan ElGamal. Seluruh perhitungan kriptografi ditulis dari nol menggunakan Python standard library. Tidak ada pustaka kriptografi siap pakai, tidak ada framework frontend, dan tidak ada pemanggilan `eval()` untuk input pengguna.

Aplikasi memiliki dua jalur demonstrasi:

1. **Arena pertarungan p=23** — pemain memilih Serang, Gunakan Skill, atau Bertahan. Kode aksi dienkripsi dengan ElGamal memakai kunci publik server `(p=23, g=5, y=8)`, lalu server mendekripsi, memvalidasi kode, memetakan kode ke damage, dan memperbarui HP monster. Client tidak dapat menentukan damage sendiri.
2. **Laboratorium tahapan 0–7** — demonstrasi lengkap parameter publik, kunci ElGamal, Diffie-Hellman, penyamaran pesan `m' = (m + K) mod p`, enkripsi, dekripsi, panel Eve, dan serangan cheater. Mode Demo memakai safe prime 16 bit; Mode Aman memakai safe prime 128 bit.

Panel **Demonstrasi manual p=23** menampilkan nilai yang sama dengan contoh tugas:

```text
Diffie-Hellman : p=23, g=5, a=6, b=15
                 A=8, B=19, K_A=K_B=2
ElGamal        : p=23, g=5, x=6, y=8, m=12, k=3
                 c1=10, c2=3, s=6, s^-1=4, m'=12
```

## Fitur

- Arena pertarungan dengan HP pemain 100 dan HP monster 100.
- Tiga aksi server-authoritative: Serang (damage 25), Gunakan Skill (damage 30), Bertahan (damage 0, pulihkan 5 HP).
- Enkripsi ElGamal di sisi client, pengiriman ciphertext `(c1, c2)`, dekripsi di sisi server, dan validasi kode aksi.
- Mode `k` deterministik (`k=3`) untuk verifikasi manual dan mode `k` acak untuk simulasi normal.
- Tombol **Uji klaim damage 999** untuk membuktikan server mengabaikan damage dari client.
- Tombol **Uji ciphertext rusak** untuk menunjukkan penolakan ciphertext tidak valid tanpa mengubah HP.
- Panel Diffie-Hellman dan ElGamal dengan rumus, substitusi angka, dan trace square-and-multiply.
- Laboratorium tahapan 0–7 dengan tombol **Langkah Berikutnya** dan **Jalankan Semua**.
- Panel jaringan/Eve yang memisahkan data publik dan rahasia.
- Log komunikasi, riwayat aksi, dan panel validasi.
- Tema Obscura dengan font lokal; aplikasi dapat berjalan offline.
- 46 pengujian otomatis (`unittest`) untuk matematika, DH, ElGamal, arena, dan endpoint HTTP.

## Teknologi

| Bagian | Teknologi |
|---|---|
| Backend | Python 3.10+ standard library (`http.server`, `json`, `threading`, `os`) |
| Kriptografi | Implementasi sendiri: `mathutil.py`, `diffie_hellman.py`, `elgamal.py` |
| Frontend | HTML, CSS, dan JavaScript murni |
| Font | Jersey 10 dan Manrope, disimpan lokal di `source_code/static/fonts/` |
| Pengujian | `unittest` standard library |
| Dokumen | Markdown, DOCX, dan PDF |

Tidak ada Flask, Django, FastAPI, React, Vue, Angular, Bootstrap, Tailwind, atau pustaka kriptografi pihak ketiga pada aplikasi utama.

## Struktur Direktori

```text
Secure-Multiplayer-Game-Simulation/
├── source_code/
│   ├── mathutil.py              # aritmetika modular, primality, safe prime, trace
│   ├── diffie_hellman.py        # protokol DH
│   ├── elgamal.py               # key generation, enkripsi, dekripsi, mask, tamper
│   ├── game_engine.py           # arena, aturan damage, HP, demonstrasi p=23
│   ├── server.py                # HTTP server, API, state sesi dan arena
│   ├── reference_demo.py        # verifikasi nilai referensi p=23
│   ├── static/
│   │   ├── index.html
│   │   ├── css/style.css
│   │   ├── js/app.js            # kontrol laboratorium tahapan
│   │   ├── js/arena.js          # kontrol arena dan panel p=23
│   │   ├── js/pixels.js
│   │   └── fonts/
│   └── tests/
│       ├── test_crypto.py       # 21 test matematika, DH, ElGamal
│       └── test_arena.py        # 25 test arena dan endpoint HTTP
├── docs/
│   ├── Perhitungan_Manual.md    # perhitungan manual p=23
│   ├── Hasil_Pengujian.txt      # keluaran aktual unittest dan reference_demo
│   ├── build_report.py          # pembangun DOCX
│   ├── build_pdf.py             # pembangun PDF (opsional)
│   ├── diagram-alur.png
│   ├── diagram-tahapan.png
│   └── screenshots/
├── Laporan_Kelompok_4.md
├── Laporan_Kelompok_4.docx
├── Laporan_Kelompok_4.pdf
├── README.md
├── README.txt
├── requirements.txt
├── requirements-dev.txt
└── .gitignore
```

## Persyaratan

- Python 3.10 atau lebih baru (diuji dengan Python 3.13.7).
- Browser modern (Chrome, Edge, Firefox, atau Safari).
- Tidak ada dependensi pihak ketiga untuk menjalankan aplikasi atau pengujian.

## Cara Menjalankan

Dari root proyek:

```bash
cd source_code
python server.py
```

Buka:

```text
http://localhost:8000
```

Jika port 8000 sedang dipakai:

```bash
python server.py --port 8080
```

Server hanya mendengarkan `127.0.0.1` secara default. Aplikasi berjalan offline setelah file dimuat; font dan aset disimpan lokal.

## Cara Menjalankan Pengujian

Dari folder `source_code`:

```bash
python -m unittest discover -s tests -v
```

Hasil yang diharapkan: **46 test lulus**. Untuk memverifikasi contoh p=23 secara terpisah:

```bash
python reference_demo.py
```

Keluaran aktual terbaru disimpan di `docs/Hasil_Pengujian.txt`.

## Contoh Alur Penggunaan

### Arena

1. Buka halaman dan gulir ke bagian **Arena otoritatif**.
2. Pilih mode `k deterministik (3)` atau biarkan tidak dicentang untuk `k` acak.
3. Klik **Serang**. Client mengirim `C=(c1,c2)` ke server; server mendekripsi, memvalidasi, dan memperbarui HP.
4. Perhatikan pipeline Aksi → Enkripsi → Kirim → Dekripsi → HP monster, lalu cek panel **Aksi terakhir**.
5. Klik **Uji klaim damage 999** untuk melihat server tetap memakai damage 25.
6. Klik **Uji ciphertext rusak** untuk melihat penolakan tanpa perubahan HP.
7. Klik **Reset arena** untuk memulai pertarungan baru.

### Laboratorium Tahapan

1. Pilih **Mode Demo · 16 bit** atau **Mode Aman · 128 bit**.
2. Pilih jenis data **Kode Aksi** atau **Skor**.
3. Klik **Langkah Berikutnya** untuk menjalankan tahap 0–7 satu per satu, atau **Jalankan Semua**.
4. Baca kartu tahap, panel pemain/Eve/server, log, dan panel validasi.
5. Gunakan tombol **Cheater: ubah c2 di jalan** pada tahap 7 untuk melihat sifat malleable ElGamal.

### Demonstrasi Manual p=23

Panel di samping Arena menampilkan langkah DH dan ElGamal yang dihitung ulang oleh Python. Nilai `c1=10`, `c2=3`, `s=6`, `s⁻¹=4`, dan `m′=12` dapat dibandingkan dengan `docs/Perhitungan_Manual.md`.

## Parameter Demonstrasi

| Parameter | Nilai | Keterangan |
|---|---|---|
| p | 23 | modulus prima untuk arena dan contoh manual |
| g | 5 | generator/akar primitif modulo 23 |
| a, b | 6, 15 | kunci privat DH pemain/server |
| A, B | 8, 19 | kunci publik DH |
| K | 2 | rahasia bersama DH; tidak dipakai sebagai kunci privat ElGamal pada arena |
| x | 6 | kunci privat ElGamal server |
| y | 8 | kunci publik ElGamal |
| m | 1, 2, 3 | kode aksi arena |
| k | 3 atau acak | nonce ElGamal; mode deterministik untuk verifikasi |
| p Mode Demo | safe prime 16 bit | untuk laboratorium tahapan |
| p Mode Aman | safe prime 128 bit | demonstrasi parameter besar, bukan produksi |

## Keamanan dan Batasan

Proyek ini **bukan sistem game produksi**.

- `p=23` dan safe prime 16 bit hanya untuk pembelajaran dan mudah dipecahkan dengan brute force.
- Mode Aman 128 bit masih jauh di bawah parameter produksi.
- Diffie-Hellman polos tidak mengautentikasi pihak yang bertukar kunci dan rentan man-in-the-middle.
- ElGamal polos tidak menjamin integritas, autentikasi pengirim, atau perlindungan replay; ciphertext bersifat malleable.
- Validasi kode aksi di server bukan pengganti MAC, tanda tangan digital, atau AEAD.
- Mode deterministik `k=3` tidak boleh dipakai pada ElGamal nyata; `k` harus acak, rahasia, dan tidak boleh dipakai ulang.
- Client dan server berjalan di satu proses lokal. Pemisahan kunci bersifat konseptual; panel demo sengaja menampilkan kunci privat untuk pembelajaran.
- Implementasi Python tidak constant-time dan belum diaudit.
- Aplikasi tidak memakai TLS, autentikasi pemain, rate limiting, atau penyimpanan state persisten.

Untuk sistem nyata, gunakan TLS 1.3, pustaka kriptografi yang diaudit, parameter produksi, autentikasi kunci, integritas pesan, dan perlindungan replay.

## Dokumentasi

- `Laporan_Kelompok_4.pdf` — laporan akademik lengkap (PDF).
- `Laporan_Kelompok_4.docx` — laporan versi Word.
- `Laporan_Kelompok_4.md` — sumber laporan Markdown.
- `docs/Perhitungan_Manual.md` — perhitungan manual p=23 dan varian integrasi.
- `docs/Hasil_Pengujian.txt` — keluaran aktual pengujian.
- `docs/screenshots/` — tangkapan layar aplikasi.

## Catatan tentang Client dan Server

Aplikasi berjalan sebagai satu server lokal agar mudah didemonstrasikan. Namun, batas konseptual tetap dijaga:

- Endpoint `/api/arena/encrypt` mewakili client yang hanya memakai kunci publik server.
- Endpoint `/api/arena/submit` mewakili server yang memegang kunci privat dan aturan damage.
- Endpoint `/api/state` dan panel laboratorium menampilkan kunci privat hanya untuk mode demonstrasi lokal.
- Diffie-Hellman dan ElGamal memiliki pasangan kunci yang berbeda. Pada arena, K tidak dipakai sebagai kunci privat ElGamal; pada laboratorium tahapan, K dipakai sebagai topeng pesan dan integrasi tersebut dijelaskan terpisah.

Semua data pemain dalam simulasi bersifat fiktif.