# BUKU PANDUAN LENGKAP & MATERI PRESENTASI LISAN
## Proyek: Secure Multiplayer Game Simulator
**Mata Kuliah:** Kriptografi (C) — Kelompok 4  
**Anggota:**  
1. Ahmad Wildan Fawwaz (5027241001)  
2. Dimas Satya Andhika (5027241032)  
3. Daniswara Fausta Novanto (5027241050)  
**Dosen Pengampu:** Annisaa Sri Indrawanti, S.Kom., M.Kom.  
**Departemen:** Teknologi Informasi, FTEIC — Institut Teknologi Sepuluh Nopember (2026)

---

> ### CATATAN KHUSUS UNTUK PRESENTASI TANPA PERANGKAT ELEKTRONIK (ORAL ONLY)
> Dokumen ini dirancang khusus sebagai **panduan penguasaan materi mutlak**. Karena kamu akan berbicara langsung di hadapan dosen dan teman sekelas tanpa bantuan proyektor, slide PPT, maupun laptop:
> 1. **Struktur Berpikir yang Runtut:** Materi di bawah ini disusun dari narasi cerita masalah (latar belakang), solusi arsitektural, bedah algoritma, penurunan rumus angka demi angka, hingga mitigasi serangan.
> 2. **Analogi Verbal yang Kuat:** Dilengkapi analogi dunia nyata agar audiens langsung terbayang tanpa melihat diagram visual.
> 3. **Angka Kunci yang Wajib Dihafal:** Disertai "jembatan keledai" untuk angka-angka referensi ($p=23, g=5, a=6, b=15, A=8, B=19, K=2, x=6, y=8, k=3, c_1=10, c_2=3$).
> 4. **Script & Defense Q&A:** Memuat naskah pidato lisan menit per menit serta antisipasi pertanyaan kritis dosen penguji.

---

# DAFTAR ISI BESAR
1. [BAB I: GAMBARAN UMUM & LATAR BELAKANG PROYEK](#bab-i-gambaran-umum--latar-belakang-proyek)
2. [BAB II: TUJUAN & MANFAAT PROYEK](#bab-ii-tujuan--manfaat-proyek)
3. [BAB III: ARSITEKTUR & ALUR KERJA SISTEM (WORKFLOW)](#bab-iii-arsitektur--alur-kerja-sistem-workflow)
4. [BAB IV: CARA KERJA KRIPTOGRAFI PADA PROYEK (DH & ELGAMAL)](#bab-iv-cara-kerja-kriptografi-pada-proyek-dh--elgamal)
5. [BAB V: RUMUSAN MATEMATIKA & PERHITUNGAN MANUAL LENGKAP (p=23)](#bab-v-rumusan-matematika--perhitungan-manual-lengkap-p23)
6. [BAB VI: SKENARIO SERANGAN, KEAMANAN, & BATASAN SISTEM](#bab-vi-skenario-serangan-keamanan--batasan-sistem)
7. [BAB VII: PANDUAN PRESENTASI LISAN DI DEPAN KELAS (SPEECH PLAYBOOK)](#bab-vii-panduan-presentasi-lisan-di-depan-kelas-speech-playbook)
8. [BAB VIII: TANYA JAWAB KRITIS DOSEN (DEFENSE Q&A GUIDE)](#bab-viii-tanya-jawab-kritis-dosen-defense-qa-guide)

---

# BAB I: GAMBARAN UMUM & LATAR BELAKANG PROYEK

### 1. Apa Itu Secure Multiplayer Game Simulator?
**Secure Multiplayer Game Simulator** adalah sebuah aplikasi simulasi komunikasi jaringan game online berbasis web yang mendemonstrasikan secara transparan bagaimana data aksi pemain diamankan saat melintasi jaringan publik menggunakan dua protokol kriptografi klasik berbasis masalah logaritma diskret (*Discrete Logarithm Problem* / DLP), yaitu:
1. **Diffie-Hellman Key Exchange (DH)** — untuk menyepakati kunci rahasia bersama (*session key* $K$) melalui kanal terbuka tanpa mengirimkan kunci tersebut.
2. **ElGamal Public-Key Cryptosystem** — untuk mengenkripsi aksi permainan menggunakan kunci publik penerima (*asymmetric encryption*).

### 2. Latar Belakang Masalah di Dunia Nyata (The Real-World Game Problem)
Bayangkan sebuah game online multiplayer seperti Mobile Legends, Genshin Impact, atau Valorant. Ketika pemain menekan tombol **"Serang"**:
- **Celah Jaringan Terbuka:** Paket data dikirim melalui kabel LAN, Wi-Fi publik di kafe, router ISP, hingga internet publik. Di tengah jalur ini, ada aktor ketiga (disebut **Eve**) yang dapat menyadap (*packet sniffing*) atau bahkan mencegat dan memanipulasi paket (*packet tampering / Man-in-the-Middle*).
- **Ancaman Cheating (Manipulasi Client):** Jika game dirancang secara naif, di mana HP monster dikurangi langsung oleh laptop pemain, seorang *cheater* bisa menggunakan software seperti *Cheat Engine* atau *packet injector* untuk mengirim data: `"Saya menyerang dengan damage 999999"`, sehingga monster langsung mati dalam satu detik.
- **Masalah Privasi Aksi:** Dalam game strategi real-time atau game kartu, lawan tidak boleh tahu aksi atau jurus rahasia apa yang sedang disiapkan pemain sebelum server mengeksekusinya.

### 3. Solusi Kami: Filosofi Desain Proyek
Untuk menyelesaikan masalah di atas, proyek ini menggabungkan dua pilar:
1. **Arsitektur Server-Authoritative (Server adalah Hakim Mutlak):**  
   Pemain **TIDAK PERNAH** diizinkan mengirim nilai *damage*. Pemain hanya boleh mengirim **"Niat/Kode Aksi"** (misalnya kode $1$ untuk Serang, $2$ untuk Skill, $3$ untuk Bertahan). Server-lah yang mendekripsi kode tersebut, memvalidasi apakah kode tersebut sah ($1, 2,$ atau $3$), lalu server yang menentukan berapa damage yang dihasilkan berdasarkan aturan internal server.
2. **Kriptografi Murni Tanpa Library (From Scratch):**  
   Seluruh fungsi matematika—mulai dari algoritma pencarian FPB (*Euclidean*), invers modular (*Extended Euclidean*), eksponensiasi modular (*Square-and-Multiply*), hingga uji bilangan prima (*Miller-Rabin*)—**ditulis sendiri 100% dari nol** menggunakan pustaka standar Python (`mathutil.py`, `diffie_hellman.py`, `elgamal.py`). Tidak ada library kriptografi siap pakai seperti `pycryptodome`, `cryptography`, maupun `OpenSSL`. Tujuannya agar setiap langkah aritmetika dapat diaudit, diverifikasi, dan dibuktikan secara matematis.

---

# BAB II: TUJUAN & MANFAAT PROYEK

### 1. Tujuan Proyek
1. **Implementasi Algoritma Asli:** Membuktikan bahwa algoritma Diffie-Hellman dan ElGamal dapat diimplementasikan dari dasar matematika murni tanpa bergantung pada *black-box library*.
2. **Visualisasi Transparan End-to-End:** Menampilkan setiap tahap perubahan data: dari plaintext angka $\to$ penyamaran $\to$ ciphertext pasangan $(c_1, c_2) \to$ transit jaringan $\to$ dekripsi $\to$ invers modular $\to$ eksekusi state game.
3. **Pembuktian Model Server-Authoritative:** Menunjukkan secara interaktif bahwa meskipun pemain jahat mencoba menyisipkan manipulasi data (seperti payload `damage: 999`), server game tetap aman karena hanya memercayai hasil dekripsi kode aksinya sendiri.
4. **Demonstrasi Kerentanan Malleability & MITM:** Menunjukkan batasan teoritis ElGamal polos (tanpa *Message Authentication Code* / MAC) di mana ciphertext dapat dimanipulasi di jalan (*malleability*), serta perlunya tanda tangan digital / sertifikat untuk mencegah *Man-in-the-Middle* pada Diffie-Hellman.

### 2. Manfaat Akademis & Praktis
- **Bagi Mahasiswa/Audiens:** Menjembatani teori abstrak perkuliahan kriptografi (teorema sisa, grup siklik, Fermat Little Theorem, Extended Euclid) ke dalam implementasi sistem nyata yang interaktif (game online).
- **Bagi Praktisi Game Security:** Memberikan pemahaman arsitektur baku industri bahwa keamanan game tidak boleh hanya bertumpu pada client side validation, melainkan wajib menerapkan enkripsi transport dan validasi otoritas server.

---

# BAB III: ARSITEKTUR & ALUR KERJA SISTEM (WORKFLOW)

Proyek ini memiliki **2 Jalur Demonstrasi Utama** di dalam aplikasi:

```
                          ARSITEKTUR UTAMA SISTEM
                          
   [ JALUR 1: ARENA PERTARUNGAN ]           [ JALUR 2: LABORATORIUM 8 TAHAPAN ]
   - Modulus p = 23 (Kecil/Manual)         - Mode Demo: Safe Prime 16-bit
   - Pemain vs Monster                     - Mode Aman: Safe Prime 128-bit
   - ElGamal Murni (Kunci Server)          - Integrasi DH + ElGamal: m' = (m + K) mod p
   - Simulasi Gameplay Otoritatif          - Bedah Langkah 0 sampai 7 + Panel Eve
```

---

### A. Tiga Aktor Utama dalam Sistem
Untuk mempermudah penjelasan ke audiens, bagi sistem ke dalam **3 entitas**:
1. **Pemain (Client / Alice):**  
   Pihak yang ingin berinteraksi dengan game. Memiliki kunci privat DH sendiri ($a$), memilih aksi permainan ($m$), membangkitkan nonce acak ($k$), dan mengenkripsi data sebelum dikirim.
2. **Jaringan Publik & Eve (Adversary / Penyadap):**  
   Saluran transmisi yang tidak aman. Eve berada di tengah-tengah. Eve dapat melihat semua parameter publik ($p, g, y, A, B$) dan paket ciphertext $(c_1, c_2)$ yang melintas. Namun, Eve **tidak memiliki akses** ke kunci privat $a, b, x$ maupun kunci rahasia bersama $K$.
3. **Server Game (Authority / Bob):**  
   Pemegang kebenaran mutlak permainan. Memiliki kunci privat DH ($b$) dan kunci privat ElGamal ($x$). Server mendekripsi pesan, mengekstrak niat aksi pemain, menghitung damage, dan memperbarui status darah (HP) monster.

---

### B. Alur Kerja Jalur 1: Arena Pertarungan ($p=23$)
Jalur ini adalah simulasi game pertarungan interaktif (HP Pemain = 100, HP Monster = 100):

```
+---------------+                +----------------+                +---------------+
| PEMAIN/CLIENT |                | JARINGAN / EVE |                |  SERVER GAME  |
+---------------+                +----------------+                +---------------+
       |                                 |                                 |
       | 1. Pilih Aksi (Misal: Serang)   |                                 |
       |    Kode m = 1                   |                                 |
       |                                 |                                 |
       | 2. Enkripsi ElGamal             |                                 |
       |    Nonce k = 3 (atau acak)      |                                 |
       |    c1 = g^k mod p = 10          |                                 |
       |    c2 = m * y^k mod p = 6       |                                 |
       |                                 |                                 |
       | 3. Kirim Paket JSON ----------->| 4. Eve menyadap:                |
       |    { ciphertext: {c1, c2},      |    Hanya melihat c1=10, c2=6    |
       |      damage_palsu: 999 }        |    (Eve tidak tahu isinya m=1)  |
       |                                 |-------------------------------->|
       |                                 |                                 | 5. Dekripsi:
       |                                 |                                 |    s = c1^x mod p = 6
       |                                 |                                 |    s^-1 = 4
       |                                 |                                 |    m = c2 * s^-1 = 1
       |                                 |                                 |
       |                                 |                                 | 6. Server Mengabaikan
       |                                 |                                 |    damage_palsu: 999!
       |                                 |                                 |
       |                                 |                                 | 7. Evaluasi Tabel:
       |                                 |                                 |    m=1 -> Damage = 25
       |                                 |                                 |    HP Monster: 100-25=75
       |                                 |                                 |    Monster balas: 10
       |                                 |                                 |    HP Pemain: 100-10=90
       |<------------------------------------------------------------------|
       | 8. Terima Status Baru: HP Monster 75, HP Pemain 90                |
```

#### Tabel Aturan Aksi di Server:
| Kode ($m$) | Nama Aksi | Damage ke Monster | Balasan Monster ke Pemain | Efek Spesial |
|:---:|:---|:---:|:---:|:---|
| **$1$** | **Serang (Attack)** | **25 HP** | 10 HP | Serangan tebasan pedang dasar |
| **$2$** | **Skill** | **30 HP** | 6 HP | Serangan sihir terfokus |
| **$3$** | **Bertahan (Defend)** | **0 HP** | 0 HP (kebal) | Memulihkan HP pemain +5 |

---

### C. Alur Kerja Jalur 2: Laboratorium 8 Tahapan (Step-by-Step 0–7)
Pada laboratorium ini, audiens dapat melihat langkah demi langkah pembentukan kriptografi secara granular:
- **Tahap 0 — Parameter Publik:** Pembentukan safe prime $p = 2q + 1$ dan pencarian generator $g$.
- **Tahap 1 — Kunci ElGamal Server:** Server membangkitkan private key $x$, lalu menghitung public key $y = g^x \pmod p$.
- **Tahap 2 — Pertukaran Kunci Diffie-Hellman:**
  - 2a: Pemain memilih eksponen privat $a$, menghitung publik $A = g^a \pmod p$.
  - 2b: Server memilih eksponen privat $b$, menghitung publik $B = g^b \pmod p$.
  - 2c: Pertukaran nilai publik $A$ dan $B$ di jaringan.
  - 2d: Perhitungan shared secret $K$: Pemain hitung $K_A = B^a \pmod p$, server hitung $K_B = A^b \pmod p$. Diverifikasi bahwa $K_A = K_B = K$.
- **Tahap 3 — Penyamaran Pesan (Masking):**  
  Sebelum dienkripsi ElGamal, pesan $m$ disamarkan dengan shared key $K$:  
  $$m' = (m + K) \pmod p$$
- **Tahap 4 — Enkripsi ElGamal:**  
  Pemain memilih nonce acak $k$, menghitung ciphertext $c_1 = g^k \pmod p$ dan $c_2 = m' \cdot y^k \pmod p$.
- **Tahap 5 — Dekripsi & Pelepasan Topeng oleh Server:**  
  Server menghitung shared factor $s = c_1^x \pmod p$, mencari invers modular $s^{-1} \pmod p$, mendekripsi ElGamal $m' = c_2 \cdot s^{-1} \pmod p$, lalu melepas topeng:  
  $$m = (m' - K) \pmod p$$
- **Tahap 6 — Audit Panel Eve:**  
  Membandingkan data yang bocor di jaringan publik vs data rahasia yang tetap aman di memori pemain dan server.
- **Tahap 7 — Eksperimen Cheater (Tampering/Malleability):**  
  Eve memodifikasi ciphertext $c_2$ menjadi $c_2'$. Ditunjukkan bagaimana plaintext yang didekripsi server menjadi korup/acak dan ditolak oleh validasi server.

---

# BAB IV: CARA KERJA KRIPTOGRAFI PADA PROYEK (DH & ELGAMAL)

### 1. Mengapa Kita Butuh Dua Algoritma Sekaligus?
Pertanyaan paling umum dari dosen atau audiens: *"Kenapa harus pakai Diffie-Hellman DAN ElGamal? Bukankah ElGamal sendiri sudah bisa mengenkripsi pesan?"*

**Jawaban Fundamental:**
- **Diffie-Hellman (DH):** Berfungsi untuk **Key Agreement** (kesepakatan kunci simetris sesi). DH sangat efisien untuk menyepakati sebuah rahasia bersama ($K$) antara dua pihak yang belum pernah bertemu sebelumnya, tanpa perlu mempercayakan kunci tersebut ke pihak ketiga.
- **ElGamal:** Berfungsi untuk **Public-Key Encryption** (enkripsi asimetris). Mengizinkan siapa pun yang memegang kunci publik server ($y$) untuk mengirim pesan rahasia yang hanya bisa dibuka oleh server (pemilik $x$).
- **Kolaborasi Keduanya (Defense-in-Depth):**  
  Pada laboratorium tahapan, kami menerapkan konsep *lapisan keamanan ganda*. Pesan disamarkan dulu dengan kunci sesi DH: $m' = (m + K) \pmod p$, lalu $m'$ dienkripsi ElGamal.  
  Artinya: Untuk membuka pesan asli $m$, penyerang harus memecahkan **DUA rahasia yang berbeda**:
  1. Kunci privat ElGamal milik server ($x$) untuk mendapatkan $m'$.
  2. Kunci sesi hasil Diffie-Hellman ($K$) untuk membuka topeng $m'$ menjadi $m$.

---

### 2. KLARIFIKASI PENTING: Pemisahan Kunci (Poin Kritis untuk Dosen)
> [!IMPORTANT]
> **Hati-hati jangan sampai salah ucap di depan dosen:**  
> Kunci sesi Diffie-Hellman ($K$) **BUKAN** kunci privat ElGamal ($x$)!  
> - Nilai $x$ adalah kunci privat permanen/jangka panjang milik server ElGamal.
> - Nilai $K$ adalah rahasia bersama sesi yang dibangkitkan dari pertukaran eksponen $a$ dan $b$.
> Pada contoh angka akademis $p=23$, kebetulan nilai $a=6$ dan $x=6$ sama-sama bernilai $6$ semata-mata karena keterbatasan ruang angka kecil untuk contoh buku teks. Namun di dalam kode dan arsitektur program, variabel keduanya dipisahkan secara ketat!

---

# BAB V: RUMUSAN MATEMATIKA & PERHITUNGAN MANUAL LENGKAP (p=23)

Bagian ini adalah **jantung presentasi**. Hafalkan angka-angka berikut karena kamu akan menjelaskannya secara lisan atau menuliskannya di papan tulis dengan percaya diri.

### 1. Fondasi Parameter Awal
- **Modulus Prima ($p$):** $p = 23$.
- **Safe Prime Property:** Bilangan prima $p$ disebut *safe prime* jika $p = 2q + 1$ di mana $q$ juga bilangan prima (*Sophie Germain prime*).  
  $$q = \frac{p - 1}{2} = \frac{23 - 1}{2} = 11$$  
  Karena $11$ adalah bilangan prima, maka $p=23$ adalah safe prime yang sah.
- **Generator ($g$):** $g = 5$.  
  Syarat $g$ adalah akar primitif (generator) dari grup $\mathbb{Z}_{23}^*$:
  1. $g^2 \not\equiv 1 \pmod{23} \implies 5^2 = 25 \equiv 2 \pmod{23} \neq 1$ (Terpenuhi).
  2. $g^q \not\equiv 1 \pmod{23} \implies 5^{11} \pmod{23} = 22 \equiv -1 \pmod{23} \neq 1$ (Terpenuhi).  
  Maka order dari $g=5$ adalah $p - 1 = 22$. Artinya, $5^k \pmod{23}$ akan menghasilkan seluruh elemen grup dari $1$ sampai $22$.

---

### 2. Perhitungan Diffie-Hellman Langkah demi Langkah

```
Parameter Bersama (Publik): p = 23, g = 5
Kunci Privat Pemain (Alice) : a = 6  (Rahasia pemain)
Kunci Privat Server (Bob)    : b = 15 (Rahasia server)
```

#### Langkah A: Pemain Menghitung Kunci Publik ($A$)
$$A = g^a \pmod p = 5^6 \pmod{23}$$
*Perhitungan Cepat (Square-and-Multiply):*
- $5^1 \equiv 5 \pmod{23}$
- $5^2 = 25 \equiv 2 \pmod{23}$
- $5^4 = (5^2)^2 = 2^2 = 4 \pmod{23}$
- $5^6 = 5^4 \cdot 5^2 = 4 \cdot 2 = 8 \pmod{23}$  
$$\mathbf{A = 8}$$
*(Pemain mengirim $A=8$ ke Server melalui jaringan)*

#### Langkah B: Server Menghitung Kunci Publik ($B$)
$$B = g^b \pmod p = 5^{15} \pmod{23}$$
*Perhitungan Cepat (Representasi Biner $15 = 8 + 4 + 2 + 1$):*
- $5^1 \equiv 5 \pmod{23}$
- $5^2 \equiv 2 \pmod{23}$
- $5^4 \equiv 4 \pmod{23}$
- $5^8 = 4^2 = 16 \pmod{23}$
- $5^{15} = 5^8 \cdot 5^4 \cdot 5^2 \cdot 5^1 = 16 \cdot 4 \cdot 2 \cdot 5 = 640 \pmod{23}$  
  $$640 = 23 \times 27 + 19 \implies 640 \pmod{23} = 19$$  
$$\mathbf{B = 19}$$
*(Server mengirim $B=19$ ke Pemain melalui jaringan)*

#### Langkah C: Pemain Menghitung Kunci Rahasia Bersama ($K_A$)
Pemain menggunakan kunci publik server $B=19$ dan kunci privatnya sendiri $a=6$:
$$K_A = B^a \pmod p = 19^6 \pmod{23}$$
*Perhitungan:*
- $19 \equiv -4 \pmod{23}$ *(trik angka negatif untuk mempermudah lisan!)*
- $19^2 \equiv (-4)^2 = 16 \pmod{23}$
- $19^4 \equiv 16^2 = 256 = (23 \times 11 + 3) \equiv 3 \pmod{23}$
- $19^6 = 19^4 \cdot 19^2 \equiv 3 \cdot 16 = 48 \pmod{23}$  
  $$48 = 23 \times 2 + 2 \implies 48 \pmod{23} = 2$$  
$$\mathbf{K_A = 2}$$

#### Langkah D: Server Menghitung Kunci Rahasia Bersama ($K_B$)
Server menggunakan kunci publik pemain $A=8$ dan kunci privatnya sendiri $b=15$:
$$K_B = A^b \pmod p = 8^{15} \pmod{23}$$
*Perhitungan:*
- $8^1 = 8$
- $8^2 = 64 = (23 \times 2 + 18) \equiv 18 \equiv -5 \pmod{23}$
- $8^4 = (-5)^2 = 25 \equiv 2 \pmod{23}$
- $8^8 = 2^2 = 4 \pmod{23}$
- $8^{15} = 8^8 \cdot 8^4 \cdot 8^2 \cdot 8^1 = 4 \cdot 2 \cdot 18 \cdot 8 = 1152 \pmod{23}$  
  $$1152 = 23 \times 50 + 2 \implies 1152 \pmod{23} = 2$$  
$$\mathbf{K_B = 2}$$

#### Kesimpulan Diffie-Hellman:
$$\mathbf{K_A = K_B = K = 2}$$
Kedua belah pihak telah menyepakati angka **$2$** sebagai kunci rahasia sesi mereka, tanpa ada satu pun angka $2$ yang pernah dikirim melalui jaringan!

---

### 3. Perhitungan ElGamal Murni (Contoh Spesifikasi: $m=12, k=3$)

Sekarang kita masuk ke skema enkripsi ElGamal:
- Parameter publik: $p = 23, g = 5$.
- Kunci privat server: $x = 6$.
- Kunci publik server ($y$):
  $$y = g^x \pmod p = 5^6 \pmod{23} = 8$$
  Maka pasangan kunci server adalah:
  - **Kunci Publik Server:** $(p, g, y) = (23, 5, 8)$
  - **Kunci Privat Server:** $x = 6$

#### Skenario Enkripsi di Sisi Pemain (Client)
Pemain ingin mengirim pesan rahasia: **$m = 12$**.  
Pemain memilih bilangan acak (*nonce*) $k = 3$ (syarat: $\text{FPB}(k, p-1) = \text{FPB}(3, 22) = 1$).

1. **Menghitung Ciphertext Pertama ($c_1$):**
   $$c_1 = g^k \pmod p = 5^3 \pmod{23} = 125 \pmod{23}$$
   $$125 = 23 \times 5 + 10 \implies \mathbf{c_1 = 10}$$
2. **Menghitung Masking Factor ($y^k$):**
   $$y^k \pmod p = 8^3 \pmod{23} = 512 \pmod{23}$$
   $$512 = 23 \times 22 + 6 \implies y^k \equiv 6 \pmod{23}$$
3. **Menghitung Ciphertext Kedua ($c_2$):**
   $$c_2 = m \cdot y^k \pmod p = 12 \cdot 6 \pmod{23} = 72 \pmod{23}$$
   $$72 = 23 \times 3 + 3 \implies \mathbf{c_2 = 3}$$

Maka paket Ciphertext yang dikirim ke server adalah pasangan:
$$\mathbf{C = (c_1, c_2) = (10, 3)}$$

---

#### Skenario Dekripsi di Sisi Server
Server menerima pasangan $C = (c_1, c_2) = (10, 3)$ dari jaringan. Server menggunakan kunci privatnya $x = 6$:

1. **Menghitung Shared Secret ($s$):**
   $$s = c_1^x \pmod p = 10^6 \pmod{23}$$
   *Perhitungan modular:*
   - $10^1 \equiv 10 \pmod{23}$
   - $10^2 = 100 \equiv 8 \pmod{23}$
   - $10^4 = 8^2 = 64 \equiv 18 \pmod{23}$
   - $10^6 = 10^4 \cdot 10^2 = 18 \cdot 8 = 144 \pmod{23}$  
     $$144 = 23 \times 6 + 6 \implies \mathbf{s = 6}$$

2. **Mencari Invers Modular ($s^{-1} \pmod{23}$):**
   Server harus mencari nilai bilangan bulat $u$ sehingga:
   $$6 \cdot u \equiv 1 \pmod{23}$$
   *Extended Euclidean Algorithm antara 23 dan 6:*
   - $23 = 3 \times 6 + 5$
   - $6 = 1 \times 5 + 1$
   - $5 = 5 \times 1 + 0$  
   *Substitusi Balik (Mencari 1):*
   $$1 = 6 - 1 \times 5$$
   $$1 = 6 - 1 \times (23 - 3 \times 6)$$
   $$1 = 4 \times 6 - 1 \times 23$$
   Dalam aritmetika modulo 23, suku $-1 \times 23$ bernilai $0$, sehingga:
   $$4 \times 6 \equiv 1 \pmod{23}$$
   Maka invers modular dari $6$ modulo $23$ adalah:
   $$\mathbf{s^{-1} = 4}$$  
   *(Uji cek: $6 \times 4 = 24 = 23 \times 1 + 1 \equiv 1 \pmod{23}$ — TERBUKTI BENAR!)*

3. **Memulihkan Pesan Asli ($m$):**
   $$m = c_2 \cdot s^{-1} \pmod p$$
   $$m = 3 \cdot 4 \pmod{23} = 12 \pmod{23}$$
   $$\mathbf{m = 12}$$
**Pesan berhasil dipulihkan secara sempurna menjadi $12$!**

---

### 4. Perhitungan Varian Integrasi (Laboratorium Tahap 3–5)
Di laboratorium interaktif, sistem menambahkan pengikatan kunci sesi DH ($K=2$):
1. **Penyamaran Pesan (Masking):**  
   $$m' = (m + K) \pmod p = (12 + 2) \pmod{23} = 14$$
2. **Enkripsi ElGamal terhadap $m'=14$:**
   - $c_1 = g^k \pmod p = 5^3 \pmod{23} = \mathbf{10}$
   - $c_2 = m' \cdot y^k \pmod p = 14 \cdot 6 \pmod{23} = 84 \pmod{23} = \mathbf{15}$  
     *(Perhatikan: jika ElGamal murni menghasilkan $c_2=3$, maka pada integrasi menghasilkan $c_2=15$)*
3. **Dekripsi oleh Server:**
   - $s = c_1^x \pmod p = 10^6 \pmod{23} = 6 \implies s^{-1} = 4$
   - $m' = c_2 \cdot s^{-1} \pmod p = 15 \cdot 4 \pmod{23} = 60 \pmod{23} = \mathbf{14}$
4. **Pelepasan Topeng (Unmasking):**  
   $$m = (m' - K) \pmod p = (14 - 2) \pmod{23} = \mathbf{12}$$
Hasil akhir kembali ke pesan awal $m = 12$.

---

### 5. Tabel Rangkuman Nilai Kunci Manual ($p=23$)
| Parameter / Notasi | Definisi | Rumus Matematis | Nilai Hasil |
|:---|:---|:---|:---:|
| $p$ | Modulus Prima (Safe Prime) | $p = 2q + 1$ | **23** |
| $q$ | Sophie Germain Prime | $(p-1)/2$ | **11** |
| $g$ | Generator / Akar Primitif | $g^2 \neq 1, g^q \neq 1 \pmod p$ | **5** |
| $a$ | Kunci Privat DH Pemain | Acak privat | **6** |
| $b$ | Kunci Privat DH Server | Acak privat | **15** |
| $A$ | Kunci Publik DH Pemain | $g^a \pmod p = 5^6 \pmod{23}$ | **8** |
| $B$ | Kunci Publik DH Server | $g^b \pmod p = 5^{15} \pmod{23}$ | **19** |
| $K$ | Shared Secret DH | $B^a = A^b \pmod p = 19^6 \pmod{23}$ | **2** |
| $x$ | Kunci Privat ElGamal Server | Rahasia server | **6** |
| $y$ | Kunci Publik ElGamal Server | $g^x \pmod p = 5^6 \pmod{23}$ | **8** |
| $k$ | Nonce Ephemeral Pemain | Acak, $\text{FPB}(k, p-1)=1$ | **3** |
| $m$ | Plaintext Pesan / Aksi | Pesan asli | **12** (atau 1, 2, 3) |
| $c_1$ | Ciphertext ElGamal Bagian 1 | $g^k \pmod p = 5^3 \pmod{23}$ | **10** |
| $c_2$ | Ciphertext ElGamal Bagian 2 | $m \cdot y^k \pmod p = 12 \cdot 6 \pmod{23}$ | **3** |
| $s$ | Shared Secret Dekripsi | $c_1^x \pmod p = 10^6 \pmod{23}$ | **6** |
| $s^{-1}$ | Invers Modular dari $s$ | $6 \cdot s^{-1} \equiv 1 \pmod{23}$ | **4** |
| $m_{dekripsi}$ | Plaintext Pulih | $c_2 \cdot s^{-1} \pmod{23} = 3 \cdot 4 \pmod{23}$ | **12** |

---

# BAB VI: SKENARIO SERANGAN, KEAMANAN, & BATASAN SISTEM

Dalam presentasi, dosen sering kali ingin melihat apakah mahasiswa memahami batasan keamanan dari sistem yang dibangun. Berikut adalah skenario serangan dan pembuktiannya di proyek ini:

### 1. Skenario Serangan 1: Cheater Mengirim Payload "Damage: 999"
- **Percobaan Serangan:** Seorang pemain memodifikasi file JavaScript atau menggunakan proxy lokal untuk mengirim paket HTTP POST ke endpoint `/api/arena/submit` dengan data:
  ```json
  {
    "ciphertext": { "c1": 10, "c2": 6 },
    "action": "attack",
    "damage": 999
  }
  ```
- **Hasil di Server:** Server **mengabaikan sepenuhnya** field `damage: 999`. Server mendekripsi ciphertext $(10, 6) \implies$ menghasilkan kode aksi $m=1$ (Serang). Berdasarkan tabel otoritatif di memori server, kode $1$ menghasilkan damage tetap sebesar **25 HP**. HP monster hanya berkurang 25 (dari 100 menjadi 75).
- **Pelajaran Keamanan:** Inilah esensi **Server-Authoritative Architecture**. Client hanya mengirim niat (*intention*), sedangkan *state mutation* mutlak dikuasai oleh server.

---

### 2. Skenario Serangan 2: Pengiriman Ciphertext Rusak / Acak
- **Percobaan Serangan:** Eve atau penyerang mencoba mengirim ciphertext palsu, misalnya $c_1 = 25$ (di luar rentang modulo) atau nilai acak yang saat didekripsi menghasilkan angka $m = 99$.
- **Hasil di Server:**  
  1. Validasi struktur: $c_1$ dan $c_2$ wajib berada pada rentang $1 \le c_1, c_2 \le p-1$.
  2. Validasi semantik: Setelah didekripsi, nilai aksi harus memenuhi $m \in \{1, 2, 3\}$. Nilai $99$ tidak ada dalam kamus aksi permainan.
  3. Server menolak paket (*Transaction Rejected*), memunculkan log peringatan, dan **darah (HP) monster maupun pemain sama sekali tidak berubah**.

---

### 3. Skenario Serangan 3: Sifat Malleable pada ElGamal (Tahap 7)
- **Kelemahan Teoretis ElGamal Polos:** ElGamal bersifat *malleable* (dapat dibentuk/diubah bentuknya) karena tidak memiliki tag integritas atau tanda tangan digital.
- **Cara Kerja:** Jika Eve mencegat $(c_1, c_2)$ di tengah jalan, Eve dapat mengalikan atau menambahkan skalar $\delta$ ke $c_2$ menjadi $c_2' = (c_2 + \delta) \pmod p$.
- **Akibat:** Ketika server mendekripsi:
  $$m' = c_2' \cdot s^{-1} = (c_2 + \delta) \cdot s^{-1} = m + \delta \cdot s^{-1} \pmod p$$
  Plaintext yang diterima server berubah menjadi angka yang sama sekali berbeda tanpa disadari oleh algoritma ElGamal!
- **Solusi Industri:** Di dunia nyata, enkripsi asimetris tidak boleh berdiri sendiri; harus digabungkan dengan **HMAC** (*Hash-based Message Authentication Code*) atau skema **AEAD** (*Authenticated Encryption with Associated Data*) untuk menjamin *Integrity* dan *Authenticity*.

---

### 4. Skenario Serangan 4: Man-in-the-Middle (MITM) pada Diffie-Hellman Polos
- **Kelemahan Teoretis DH Polos:** Diffie-Hellman polos tidak melakukan autentikasi identitas pengirim.
- **Skenario:** Eve bisa duduk di tengah jaringan. Saat Pemain mengirim $A$, Eve mencegat $A$ dan mengirim kunci palsunya $E_1$ ke Server. Saat Server membalas dengan $B$, Eve mencegat $B$ dan mengirim kunci palsunya $E_2$ ke Pemain.
- **Akibat:** Eve membentuk dua sesi terpisah (satu dengan pemain, satu dengan server). Eve bisa membaca dan memanipulasi seluruh percakapan tanpa terdeteksi!
- **Solusi Industri:** Penggunaan sertifikat digital X.509 dan Public Key Infrastructure (PKI) seperti yang diterapkan pada protokol **TLS 1.3**.

---

### 5. Batasan Sistem dan Kejujuran Akademis
Beri tahu audiens secara lugas:
1. **Ukuran Kunci:** $p=23$ dan safe prime 16-bit hanya untuk kemudahan demonstrasi visual dan perhitungan manual. Dalam standar industri (NIST), ukuran modulus prima minimal adalah **2048-bit hingga 3072-bit**, atau beralih ke *Elliptic Curve Cryptography* (ECC) seperti X25519 (256-bit).
2. **Side-Channel Attack:** Implementasi Python standar tidak dirancang *constant-time*, sehingga rentan terhadap analisis waktu eksekusi (*timing attacks*).
3. **Ketiadaan TLS & Session Token:** Sistem ini adalah simulator konseptual lokal, bukan pengganti stack keamanan web produksi.

---

# BAB VII: PANDUAN PRESENTASI LISAN DI DEPAN KELAS (SPEECH PLAYBOOK)

Gunakan struktur presentasi 5–7 menit berikut. Kamu bisa membagi peran jika presentasi bertiga, atau membawakannya sendiri secara mengalir:

```
+-------------------------------------------------------------------------------+
|               STRUKTUR ALUR PRESENTASI LISAN (TOTAL: ~6 MENIT)                |
+-------------------------------------------------------------------------------+
| 1. PEMBUKAAN & HOOK MASALAH (1 Menit)      -> Analogi Cheat Engine & Game     |
| 2. SOLUSI & ARSITEKTUR KAMI (1 Menit)     -> Server-Authoritative & 2 Skema   |
| 3. DEMONSTRASI MATEMATIKA (2.5 Menit)     -> Bedah Angka p=23 (DH & ElGamal)  |
| 4. SERANGAN & KEAMANAN (1 Menit)          -> Uji Tamper 999 & Malleability    |
| 5. KESIMPULAN & CLOSING (0.5 Menit)       -> Insight Kriptografi & Penutup    |
+-------------------------------------------------------------------------------+
```

---

### Naskah Lisan Menit per Menit (Speech Script)

#### Menit 1:00 — Pembukaan & Hook Masalah
> *"Selamat pagi/siang Bu Annisaa dan rekan-rekan semua. Kami dari Kelompok 4 hari ini membawakan proyek bertajuk **Secure Multiplayer Game Simulator**.*  
>  
> *Pernahkah teman-teman bermain game online dan tiba-tiba bertemu lawan yang memakai cheat 'one-hit kill'? Atau bagaimana jika ada hacker di jaringan Wi-Fi publik yang bisa membaca jurus apa yang akan kita keluarkan sebelum kita menyerang?*  
>  
> *Di sinilah letak masalah nyata dalam rekayasa jaringan game: **Kerahasiaan data** di jaringan publik dan **Integritas aturan permainan**. Proyek kami menjawab tantangan ini dengan menggabungkan dua algoritma kriptografi klasik: **Diffie-Hellman** dan **ElGamal**, yang kami bangun murni 100% dari nol menggunakan Python tanpa library kriptografi pihak ketiga."*

#### Menit 2:00 — Arsitektur & Filosofi Sistem
> *"Sistem kami dibangun di atas prinsip **Server-Authoritative**. Artinya apa? Pemain tidak pernah diizinkan mengirim instruksi 'Monster berkurang 100 HP'. Pemain hanya mengirimkan kode niat aksinya: 1 untuk Serang, 2 untuk Skill, dan 3 untuk Bertahan.*  
>  
> *Sebelum kode ini dikirim lewat internet yang penuh bahaya, kode aksi dienkripsi menggunakan kunci publik server lewat algoritma **ElGamal**. Di saat yang sama, untuk skenario laboratorium bertahap, pemain dan server menyepakati kunci sesi rahasia menggunakan **Diffie-Hellman** untuk memberikan lapisan penyamaran kedua.*  
>  
> *Seorang penyadap bernama Eve yang duduk di tengah jaringan hanya melihat angka acak $c_1$ dan $c_2$. Ia tidak bisa membaca aksinya, dan ia tidak bisa memalsukan damage-nya."*

#### Menit 3:00 s.d 4:30 — Inti Matematika & Bedah Angka ($p=23$)
*(Jika ada papan tulis, kamu bisa menuliskan ringkasan angka berikut sambil berbicara)*
> *"Mari kita buktikan secara matematis menggunakan parameter referensi tugas kami dengan modulus bilangan prima $p = 23$ dan generator $g = 5$.*  
>  
> *Pertama, **Diffie-Hellman**:*  
> *Pemain memilih kunci privat $a = 6$, menghasilkan kunci publik $A = 5^6 \pmod{23} = 8$.*  
> *Server memilih kunci privat $b = 15$, menghasilkan kunci publik $B = 5^{15} \pmod{23} = 19$.*  
> *Ketika mereka bertukar $A=8$ dan $B=19$ di jaringan terbuka, Pemain menghitung $19^6 \pmod{23} = 2$, dan Server menghitung $8^{15} \pmod{23} = 2$. Mereka berdua berhasil menyepakati kunci rahasia bersama bernilai **$K = 2$** tanpa Eve mengetahuinya.*  
>  
> *Kedua, **Enkripsi ElGamal**:*  
> *Server memiliki kunci privat $x = 6$ dan mempublikasikan kunci publik $y = 5^6 \pmod{23} = 8$.*  
> *Misalkan pemain mengirim kode aksi atau pesan $m = 12$ dengan nilai acak $k = 3$.*  
> *Pemain menghitung dua komponen ciphertext:*  
> *$c_1 = 5^3 \pmod{23} = 125 \pmod{23} = 10$.*  
> *$c_2 = 12 \times (8^3 \pmod{23}) \pmod{23} = 12 \times 6 = 72 \pmod{23} = 3$.*  
> *Ciphertext $(10, 3)$ dikirim ke server.*  
>  
> *Di sisi Server, bagaimana cara membukanya?*  
> *Server menghitung faktor rahasia $s = 10^6 \pmod{23} = 6$.*  
> *Lalu dengan Algoritma Euclidean Diperluas, server mencari invers modular dari 6 modulo 23, yaitu bilangan yang jika dikalikan 6 menghasilkan sisa 1. Angka tersebut adalah **$4$**, karena $6 \times 4 = 24 \equiv 1 \pmod{23}$.*  
> *Terakhir, server memulihkan pesan: $m = c_2 \times s^{-1} = 3 \times 4 = 12 \pmod{23}$. Tepat kembali ke angka 12!"*

#### Menit 5:30 — Uji Serangan & Ketahanan
> *"Lalu apa yang terjadi jika ada cheater yang mencoba curang?*  
> *Pada simulator kami, ada tombol uji **Klaim Damage 999**. Cheater memodifikasi JSON payload dan menyisipkan `damage: 999`. Namun server kami hanya mengekstrak isi ciphertext $c_1, c_2$. Karena hasil dekripsinya adalah kode 1 (Serang biasa), server tetap memotong HP monster sebesar 25 poin, bukan 999. Cheater gagal total.*  
>  
> *Kami juga menguji serangan ciphertext rusak. Jika paket diubah di jalan oleh Eve, server mendeteksi bahwa kode hasil dekripsi tidak valid dan menolak transaksi tanpa mengubah state permainan sedikit pun."*

#### Menit 6:00 — Penutup & Kesimpulan
> *"Sebagai kesimpulan, proyek ini membuktikan bahwa keamanan aplikasi bukan hanya soal memasang rumus kriptografi di atas kertas, melainkan bagaimana menyatukan arsitektur sistem yang tepat—yaitu **Server-Authoritative**—dengan pondasi matematika yang kokoh.*  
>  
> *Sekian presentasi dari Kelompok 4. Kami siap menerima pertanyaan atau tanggapan dari Bu Annisaa dan rekan-rekan. Terima kasih."*

---

# BAB VIII: TANYA JAWAB KRITIS DOSEN (DEFENSE Q&A GUIDE)

Hafalkan 6 pertanyaan paling sering ditanyakan dosen penguji kriptografi berikut ini beserta jawaban taktisnya:

### Q1: "Kenapa memilih $p=23$ dan $g=5$? Bagaimana memastikan $g=5$ benar-benar generator?"
**Jawaban Tangkas:**  
> *"Kami memilih $p=23$ karena 23 adalah safe prime, yaitu $p = 2q + 1$ dengan $q=11$ yang juga bilangan prima. Keuntungannya, subgrup modulo 23 hanya berukuran 1, 2, 11, dan 22.  
> Untuk membuktikan $g=5$ adalah generator, kami memeriksa dua syarat:  
> 1. $5^2 \pmod{23} = 25 \equiv 2 \neq 1$.  
> 2. $5^{11} \pmod{23} = 22 \neq 1$.  
> Karena pangkat 2 dan pangkat $q$ tidak ada yang menghasilkan 1, maka order dari 5 pasti penuh sebesar $p-1 = 22$, sehingga 5 adalah akar primitif atau generator sah dari $\mathbb{Z}_{23}^*$."*

---

### Q2: "Apakah kunci $K$ hasil Diffie-Hellman itu digunakan sebagai kunci privat ElGamal?"
**Jawaban Tangkas (Wajib Tegas!):**  
> *"Tidak, Bu. Itu adalah dua kunci yang terpisah secara konseptual dan implementasi. Kunci privat ElGamal ($x$) adalah milik permanen server untuk menerima pesan asimetris. Sedangkan $K$ adalah rahasia bersama hasil negosiasi sesi.  
> Pada laboratorium tahapan, $K$ kami gunakan sebagai layer penyamaran tambahan: $m' = (m + K) \pmod p$, baru kemudian $m'$ dienkripsi ElGamal. Kebetulan pada contoh akademis buku teks $a=6$ dan $x=6$, tetapi dalam arsitektur kode kami, keduanya adalah variabel independen."*

---

### Q3: "Mengapa ElGamal membutuhkan bilangan acak $k$ (nonce)? Apa bahayanya jika $k$ dipakai berulang kali?"
**Jawaban Tangkas:**  
> *"Nilai $k$ berfungsi sebagai faktor pengacak agar ElGamal bersifat probabilistik. Jika kita mengenkripsi pesan yang sama dua kali dengan $k$ yang berbeda, ciphertext $(c_1, c_2)$ yang dihasilkan akan berbeda total, sehingga penyadap tidak bisa menebak pola pesan.  
> Jika $k$ digunakan berulang kali pada dua pesan berbeda $m_1$ dan $m_2$, maka rasio ciphertext keduanya akan bocor:  
> $\frac{c_{2,1}}{c_{2,2}} \equiv \frac{m_1}{m_2} \pmod p$.  
> Penyerang dapat dengan mudah mengetahui korelasi pesan atau bahkan membongkar plaintext jika salah satu pesan diketahui."*

---

### Q4: "Bagaimana cara server mencari invers modular dari 6 modulo 23 secara manual tanpa membagi langsung?"
**Jawaban Tangkas:**  
> *"Dalam aritmetika modular tidak ada operasi pembagian langsung, melainkan perkalian dengan invers modular. Kami menggunakan **Extended Euclidean Algorithm** untuk mencari kombinasi linear Bézout: $a \cdot x + p \cdot y = 1$.  
> Dari pembagian berulang: $23 = 3(6) + 5$, lalu $6 = 1(5) + 1$.  
> Saat disubstitusi balik: $1 = 6 - 1(23 - 3(6)) = 4(6) - 1(23)$.  
> Dalam modulo 23, suku kelipatan 23 menjadi 0, sehingga tersisa $4 \times 6 \equiv 1 \pmod{23}$. Maka invers dari 6 adalah **4**."*

---

### Q5: "Apa kelemahan utama dari protokol Diffie-Hellman dan ElGamal yang kalian buat ini jika diterapkan di internet nyata?"
**Jawaban Tangkas (Menunjukkan Wawasan Industri):**  
> *"Ada dua kelemahan utama, Bu:  
> 1. **Ketiadaan Autentikasi pada DH:** DH polos rentan terhadap serangan Man-in-the-Middle karena Alice tidak bisa memastikan apakah nilai $B$ benar-benar dari Server atau dari Eve. Di industri, ini diselesaikan dengan sertifikat digital TLS / PKI.  
> 2. **Sifat Malleable pada ElGamal Polos:** ElGamal tidak memiliki integritas bawaan. Penyerang bisa memodifikasi $c_2$ di jalan dan server akan mendekripsi plaintext yang korup tanpa memicu error autentikasi. Di industri, ini harus dipadukan dengan MAC (seperti HMAC) atau skema Authenticated Encryption (AEAD)."*

---

### Q6: "Kenapa program kalian tidak memakai library seperti Cryptography atau PyCryptodome?"
**Jawaban Tangkas:**  
> *"Tujuan utama proyek ini adalah edukasi dan transparansi audit matematis. Jika kami menggunakan library siap pakai, proses kalkulasi seperti square-and-multiply, extended euclidean, dan pemisahan subgrup menjadi 'black box' yang tersembunyi. Dengan menulis dari nol menggunakan standard library Python, kami dapat menampilkan jejak substitusi angka secara detail di setiap tahap untuk diverifikasi dengan perhitungan tangan."*

---

# KESIMPULAN AKHIR UNTUK KAMU SEBAGAI PEMBICARA
Kunci sukses presentasi tanpa alat elektronik adalah **ketenangan, kontak mata, dan kejelasan alur logika**. Jangan menghafal kalimat kata per kata, melainkan pahami **rantai logikanya**:
$$\text{Masalah Cheat/Sniffing} \longrightarrow \text{Arsitektur Otoritatif Server} \longrightarrow \text{Kunci Sesi DH } (K=2) \longrightarrow \text{Enkripsi ElGamal } (c_1=10, c_2=3) \longrightarrow \text{Dekripsi Invers Euclid } (s^{-1}=4) \longrightarrow \text{Validasi HP Server}$$

Jika kamu memegang alur di atas dan mengingat angka-angka kuncinya, presentasimu akan terdengar sangat menguasai materi, percaya diri, dan profesional di hadapan dosen penguji!

