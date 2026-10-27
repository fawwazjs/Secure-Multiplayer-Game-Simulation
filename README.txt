SECURE MULTIPLAYER GAME SIMULATOR
Mata Kuliah: Kriptografi (C)
Kelompok 4

Anggota:
1. Ahmad Wildan Fawwaz - 5027241001
2. Dimas Satya Andhika - 5027241032
3. Daniswara Fausta Novanto - 5027241050

Dosen Pengampu: Annisaa Sri Indrawanti, S.Kom., M.Kom.
Departemen Teknologi Informasi
Institut Teknologi Sepuluh Nopember


CARA MENJALANKAN
----------------
1. Pastikan Python 3.10 atau lebih baru sudah terpasang.
2. Buka terminal di folder ini.
3. Masuk ke folder source_code:

       cd source_code

4. Jalankan server:

       python server.py

5. Buka browser ke:

       http://localhost:8000

Tidak perlu memasang dependensi apa pun. Aplikasi berjalan offline.
Jika port 8000 sedang dipakai, gunakan port lain:

       python server.py --port 8080


CARA MENJALANKAN PENGUJIAN
--------------------------
Dari folder source_code:

       python -m unittest discover -s tests -v

Hasil terbaru: 46 test lulus (21 test matematika/DH/ElGamal + 25 test
arena dan endpoint HTTP).

Verifikasi nilai referensi p=23:

       python reference_demo.py

Keluaran aktual: docs/Hasil_Pengujian.txt


FITUR APLIKASI
--------------
Arena pertarungan p=23:
- Pemain melawan Cipher Slime; HP pemain 100 dan HP monster 100.
- Aksi: Serang (damage 25), Gunakan Skill (damage 30), Bertahan
  (damage 0, pulihkan 5 HP).
- Kode aksi 1/2/3 dienkripsi ElGamal dengan kunci publik server
  (p=23, g=5, y=8). Server memegang kunci privat x=6.
- Server memetakan kode aksi ke damage; klaim damage dari client
  diabaikan.
- Tombol Uji klaim damage 999 dan Uji ciphertext rusak.
- Panel demonstrasi manual p=23: A=8, B=19, K=2, y=8, c1=10, c2=3,
  s=6, s^-1=4, m'=12.
- Log komunikasi, riwayat aksi, dan validasi.

Laboratorium tahapan 0-7:
- Parameter publik, kunci ElGamal, Diffie-Hellman, penyamaran pesan,
  enkripsi, dekripsi, panel Eve, dan serangan cheater.
- Mode Demo (safe prime 16 bit) dan Mode Aman (safe prime 128 bit).
- Tombol Langkah Berikutnya, Jalankan Semua, Reset, dan Cheater.

Antarmuka:
- Tema Obscura dengan font lokal, responsif untuk layar kecil.
- Tidak memakai framework frontend atau pustaka kriptografi.


STRUKTUR FILE
-------------
source_code/
  mathutil.py          aritmetika modular, primality, safe prime,
                       generator, bilangan acak, trace
  diffie_hellman.py    protokol pertukaran kunci DH
  elgamal.py           key generation, enkripsi, dekripsi, mask, tamper
  game_engine.py       arena, aturan damage, HP, demonstrasi p=23
  server.py            HTTP server, API JSON, state sesi/arena, statis
  reference_demo.py    verifikasi nilai referensi p=23
  static/index.html    antarmuka satu halaman
  static/css/style.css tema dan layout responsif
  static/js/app.js     kontrol tahapan dan rendering laboratorium
  static/js/arena.js   kontrol arena dan panel p=23
  static/js/pixels.js  sprite piksel lokal
  static/fonts/        font lokal (Jersey 10 dan Manrope)
  tests/test_crypto.py pengujian matematika, DH, ElGamal
  tests/test_arena.py  pengujian arena dan endpoint HTTP

docs/
  Perhitungan_Manual.md  perhitungan manual p=23
  Hasil_Pengujian.txt    keluaran aktual pengujian
  build_report.py        pembangun DOCX
  build_pdf.py           pembangun PDF (opsional)
  diagram-*.png          diagram laporan
  screenshots/           tangkapan layar

Laporan_Kelompok_4.docx  laporan utama (Word)
Laporan_Kelompok_4.pdf   laporan versi PDF
Laporan_Kelompok_4.md    laporan versi Markdown
requirements.txt         catatan dependensi (standard library)
requirements-dev.txt     dependensi opsional untuk membangun laporan
README.md                dokumentasi lengkap
README.txt               panduan singkat ini


ENDPOINT API
------------
POST /api/setup             membuat p, q, g dan mereset sesi
POST /api/elgamal/key       membuat kunci ElGamal x, y
POST /api/dh/start          memilih a dan menghitung A
POST /api/dh/finish         memilih b, menghitung B, K pemain/server
POST /api/send              memvalidasi m dan menghitung m'
POST /api/encrypt           memilih k dan menghitung c1, c2
POST /api/decrypt           menghitung s, s^-1, m', dan m
GET  /api/eve               data publik yang terlihat Eve
POST /api/tamper            mengubah c2 dan mendekripsi hasilnya
POST /api/reset             mereset state sesi laboratorium
GET  /api/state             state sesi saat ini
GET  /api/health            pemeriksaan kesehatan server

GET  /api/arena/state       state arena, HP, kunci, log, validasi
POST /api/arena/encrypt     enkripsi kode aksi dengan kunci publik
POST /api/arena/submit      dekripsi, validasi, perbarui HP
POST /api/arena/reset       reset HP dan turn arena
GET  /api/textbook          contoh perhitungan p=23
POST /api/textbook/elgamal  hitung ulang contoh ElGamal


CATATAN KEAMANAN
----------------
- p=23 dan safe prime 16 bit hanya untuk pembelajaran, bukan produksi.
- Mode Aman 128 bit masih di bawah parameter produksi.
- DH polos tidak mengautentikasi pihak yang bertukar kunci (rentan MITM).
- ElGamal polos tidak menjamin integritas/autentikasi dan bersifat
  malleable; validasi kode aksi bukan pengganti MAC/tanda tangan.
- Mode deterministik k=3 hanya untuk reproduksibilitas; pada ElGamal
  nyata k harus acak dan tidak boleh dipakai ulang.
- Client dan server berjalan di satu proses lokal; pemisahan kunci
  bersifat konseptual dan panel demo sengaja menampilkan kunci privat.
- Aplikasi tidak memakai TLS, autentikasi pemain, atau rate limiting.

Semua data pemain bersifat fiktif. Gunakan hanya untuk demonstrasi
akademik.