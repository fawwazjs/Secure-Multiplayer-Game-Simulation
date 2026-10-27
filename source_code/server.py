"""Server HTTP untuk Secure Multiplayer Game Simulator.

Backend hanya memakai Python standard library:
  - http.server untuk server HTTP
  - json untuk pertukaran data
  - os/pathlib untuk file statis
  - threading untuk mengunci state sesi

Seluruh perhitungan kriptografi dilakukan oleh mathutil.py,
diffie_hellman.py, dan elgamal.py. Frontend hanya memanggil API dan
menampilkan hasil; frontend tidak menghitung kripto.
"""

from __future__ import annotations

import json
import mimetypes
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import diffie_hellman as dh
import elgamal
import game_engine as game
from mathutil import generate_safe_prime, find_generator

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

MODES = {
    "demo": {"bits": 16, "label": "Mode Demo (16 bit)"},
    "safe": {"bits": 128, "label": "Mode Aman (128 bit)"},
}

ACTION_LABELS = {
    1: "Serang",
    2: "Bertahan",
    3: "Heal",
}
MAX_SCORE = 1_000_000


class FlowError(RuntimeError):
    """Dipanggil ketika tahap belum siap atau sudah dijalankan."""


def _num(value: int | None) -> str | None:
    """Ubah bilangan kripto menjadi string agar aman di JavaScript."""
    return None if value is None else str(value)


def _fmt_action(code: int) -> str:
    return ACTION_LABELS.get(code, "Tidak dikenal")


def _message_label(data_type: str | None, value: int | None) -> str:
    """Bentuk label pesan yang ramah dibaca manusia."""
    if data_type is None or value is None:
        return "Belum ada pesan"
    if data_type == "action":
        label = _fmt_action(value)
        if label == "Tidak dikenal":
            return f"Aksi tidak dikenal (kode {value})"
        return f"Aksi: {label}"
    return f"Skor: {value}"


class GameSession:
    """State satu sesi demonstrasi yang disimpan di memori server."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.mode: str | None = None
        self.bits: int = 0
        self.p: int | None = None
        self.q: int | None = None
        self.g: int | None = None
        self.setup_seconds: float = 0.0

        self.x: int | None = None
        self.y: int | None = None

        self.a: int | None = None
        self.A: int | None = None
        self.b: int | None = None
        self.B: int | None = None
        self.K_player: int | None = None
        self.K_server: int | None = None
        self.K_verified: bool = False

        self.data_type: str | None = None
        self.action: int | None = None
        self.score: int | None = None
        self.m: int | None = None
        self.m_prime: int | None = None

        self.k: int | None = None
        self.yk: int | None = None
        self.c1: int | None = None
        self.c2: int | None = None

        self.s: int | None = None
        self.s_inv: int | None = None
        self.m_prime_recovered: int | None = None
        self.m_recovered: int | None = None
        self.decrypt_valid: bool = False

        self.tamper: dict[str, object] | None = None

        self.step: int = -1
        self.logs: list[dict[str, object]] = []
        self.packets: list[dict[str, object]] = []
        self.log_seq: int = 0
        self.packet_seq: int = 0

    # ------------------------------------------------------------------
    # Utilitas log dan paket
    # ------------------------------------------------------------------

    def log(self, stage: int | str, kind: str, message: str) -> None:
        self.log_seq += 1
        self.logs.append(
            {
                "seq": self.log_seq,
                "stage": str(stage),
                "kind": kind,
                "message": message,
            }
        )

    def add_packet(
        self,
        stage: int,
        sender: str,
        receiver: str,
        packet_type: str,
        fields: list[dict[str, str]],
        note: str,
        status: str = "delivered",
    ) -> None:
        self.packet_seq += 1
        self.packets.append(
            {
                "seq": self.packet_seq,
                "stage": stage,
                "from": sender,
                "to": receiver,
                "type": packet_type,
                "status": status,
                "fields": fields,
                "note": note,
            }
        )

    # ------------------------------------------------------------------
    # Tahap 0 - parameter publik
    # ------------------------------------------------------------------

    def setup(self, mode: str) -> dict[str, object]:
        if mode not in MODES:
            raise ValueError("Mode harus 'demo' atau 'safe'.")
        self.reset()
        self.mode = mode
        bits = MODES[mode]["bits"]
        self.bits = bits

        started = time.perf_counter()
        p, q = generate_safe_prime(bits)
        g = find_generator(p, q)
        self.p, self.q, self.g = p, q, g
        self.setup_seconds = time.perf_counter() - started
        self.step = 0

        self.log(0, "ok", f"Parameter publik dibuat: p {bits} bit, q {bits - 1} bit, generator g ditemukan.")
        stage = {
            "number": 0,
            "key": "setup",
            "title": "Tahap 0 — Parameter Publik",
            "blocks": [
                {
                    "label": "0. Pembangkitan safe prime dan generator",
                    "formula": "p = 2q + 1, dengan p dan q prima; g ∈ [2, p-2]",
                    "substitution": (
                        f"p = {p} (safe prime, {p.bit_length()} bit)\n"
                        f"q = {q} (prima, {q.bit_length()} bit)\n"
                        f"verifikasi: 2·q + 1 = {2 * q + 1} = p\n"
                        f"g = {g}; periksa g² mod p = {_mod_text(g, 2, p)} ≠ 1 "
                        f"dan g^q mod p = {_mod_text(g, q, p)} ≠ 1"
                    ),
                    "result": "Parameter publik siap dibagikan melalui jaringan.",
                    "tone": "success",
                }
            ],
            "summary": f"p = {p} · q = {q} · g = {g}",
            "note": (
                f"Parameter dibuat dalam {MODES[mode]['label']}. Safe prime berarti p = 2q + 1 "
                "sehingga grup perkalian modulo p memiliki subgrup besar berorder prima q. "
                f"Waktu pembangkitan: {self.setup_seconds * 1000:.1f} ms."
            ),
            "values": {"p": _num(p), "q": _num(q), "g": _num(g), "bits": bits},
        }
        return {"ok": True, "stage": stage, "view": self.view()}

    # ------------------------------------------------------------------
    # Tahap 1 - kunci ElGamal server
    # ------------------------------------------------------------------

    def generate_key(self) -> dict[str, object]:
        self._require(self.p is not None, "Jalankan Tahap 0 terlebih dahulu.")
        self._require(self.y is None, "Kunci ElGamal sudah dibuat. Reset untuk mengulang.")
        assert self.p is not None and self.g is not None

        keypair = elgamal.generate_keypair(self.p, self.g)
        self.x, self.y = keypair["x"], keypair["y"]
        self.step = max(self.step, 1)
        self.log(1, "ok", "Server membuat kunci ElGamal: x rahasia dan y publik.")
        stage = {
            "number": 1,
            "key": "keygen",
            "title": "Tahap 1 — Pembangkitan Kunci ElGamal Server",
            "blocks": [
                {
                    "label": "1a. Pilih kunci privat x",
                    "formula": "x ∈ [2, p-2], x rahasia",
                    "substitution": f"x = {self.x}",
                    "result": "x hanya disimpan di panel server.",
                },
                {
                    "label": "1b. Hitung kunci publik y",
                    "formula": "y = g^x mod p",
                    "substitution": f"y = {self.g}^{self.x} mod {self.p} = {self.y}",
                    "result": f"Kunci publik server: y = {self.y}",
                    "tone": "success",
                },
            ],
            "summary": f"y = {self.y}",
            "note": "y boleh diketahui semua pihak, termasuk Eve. x tetap rahasia server.",
            "values": {"x": _num(self.x), "y": _num(self.y)},
        }
        return {"ok": True, "stage": stage, "view": self.view()}

    # ------------------------------------------------------------------
    # Tahap 2 - Diffie-Hellman
    # ------------------------------------------------------------------

    def dh_start(self) -> dict[str, object]:
        self._require(self.p is not None and self.g is not None, "Jalankan Tahap 0 terlebih dahulu.")
        self._require(self.A is None, "Nilai A sudah dibuat. Reset untuk mengulang.")
        assert self.p is not None and self.g is not None

        player = dh.player_start(self.p, self.g)
        self.a, self.A = player["a"], player["A"]
        self.step = max(self.step, 2)
        self.add_packet(
            2,
            "PEMAIN",
            "SERVER",
            "DH-1 · kunci publik pemain",
            [{"label": "A", "value": str(self.A)}],
            "A = g^a mod p. Eve dapat membaca A, tetapi tidak dapat memperoleh a.",
        )
        self.log(2, "info", "Tahap 2a: pemain mengirim nilai publik A.")
        return {"ok": True, "stage": self._dh_stage(), "view": self.view()}

    def dh_finish(self) -> dict[str, object]:
        self._require(self.A is not None, "Jalankan Tahap 2a terlebih dahulu.")
        self._require(self.B is None, "Nilai B sudah dibuat. Reset untuk mengulang.")
        assert self.p is not None and self.a is not None and self.A is not None

        server = dh.server_start(self.p, self.g)
        self.b, self.B = server["b"], server["B"]
        keys = dh.compute_shared_keys(self.p, self.a, self.b, self.A, self.B)
        self.K_player = int(keys["K_player"])
        self.K_server = int(keys["K_server"])
        self.K_verified = bool(keys["verified"])
        self.step = max(self.step, 3)

        self.add_packet(
            2,
            "SERVER",
            "PEMAIN",
            "DH-2 · kunci publik server",
            [{"label": "B", "value": str(self.B)}],
            "B = g^b mod p. Setelah A dan B bertukar, kedua pihak menghitung K.",
        )
        self.log(2, "ok", "Tahap 2c: K pemain dan K server dihitung dan dibandingkan.")
        if self.K_verified:
            self.log(2, "ok", "Tahap 2d: verifikasi berhasil — K pemain = K server.")
        else:
            self.log(2, "danger", "Tahap 2d: verifikasi gagal — kunci tidak sama.")
        return {"ok": True, "stage": self._dh_stage(), "view": self.view()}

    def _dh_stage(self) -> dict[str, object]:
        assert self.p is not None and self.g is not None
        blocks: list[dict[str, object]] = []
        if self.a is not None and self.A is not None:
            blocks.append(
                {
                    "label": "2a. Pemain memilih a dan mengirim A",
                    "formula": "a ∈ [2, p-2] (rahasia) ; A = g^a mod p",
                    "substitution": f"a = {self.a}\nA = {self.g}^{self.a} mod {self.p} = {self.A}",
                    "result": f"Pemain → Server: A = {self.A}",
                }
            )
        if self.b is not None and self.B is not None:
            blocks.append(
                {
                    "label": "2b. Server memilih b dan mengirim B",
                    "formula": "b ∈ [2, p-2] (rahasia) ; B = g^b mod p",
                    "substitution": f"b = {self.b}\nB = {self.g}^{self.b} mod {self.p} = {self.B}",
                    "result": f"Server → Pemain: B = {self.B}",
                }
            )
        if self.K_player is not None and self.K_server is not None:
            blocks.append(
                {
                    "label": "2c. Kedua pihak menghitung K",
                    "formula": "K_pemain = B^a mod p ; K_server = A^b mod p",
                    "substitution": (
                        f"K_pemain = {self.B}^{self.a} mod {self.p} = {self.K_player}\n"
                        f"K_server = {self.A}^{self.b} mod {self.p} = {self.K_server}"
                    ),
                    "result": (
                        f"K_pemain = {self.K_player}\nK_server = {self.K_server}"
                    ),
                    "tone": "success" if self.K_verified else "danger",
                }
            )
            blocks.append(
                {
                    "label": "2d. Pemeriksaan otomatis",
                    "formula": "K_pemain == K_server ?",
                    "substitution": f"{self.K_player} == {self.K_server}",
                    "result": (
                        "SAMA — kunci sesi berhasil disepakati (indikator hijau)."
                        if self.K_verified
                        else "TIDAK SAMA — periksa parameter."
                    ),
                    "tone": "success" if self.K_verified else "danger",
                }
            )
        summary = "Menunggu pertukaran kunci."
        if self.K_verified:
            summary = f"K = {self.K_player} (terverifikasi sama di kedua sisi)"
        return {
            "number": 2,
            "key": "dh",
            "title": "Tahap 2 — Diffie-Hellman",
            "blocks": blocks,
            "summary": summary,
            "note": (
                "K tidak pernah dikirim. Eve hanya melihat A dan B. "
                "Untuk mendapat K, Eve harus menyelesaikan logaritma diskret a atau b."
            ),
            "values": {
                "a": _num(self.a),
                "A": _num(self.A),
                "b": _num(self.b),
                "B": _num(self.B),
                "K_player": _num(self.K_player),
                "K_server": _num(self.K_server),
                "verified": self.K_verified,
            },
        }

    # ------------------------------------------------------------------
    # Tahap 3 - penyamaran pesan
    # ------------------------------------------------------------------

    def prepare_message(self, payload: dict[str, object]) -> dict[str, object]:
        self._require(self.K_verified, "Selesaikan Diffie-Hellman sampai K terverifikasi.")
        self._require(self.m is None, "Pesan sudah disiapkan. Reset untuk mengirim pesan baru.")
        assert self.p is not None and self.K_player is not None

        data_type = str(payload.get("data_type", "")).strip()
        if data_type not in ("action", "score"):
            raise ValueError("Jenis data harus 'action' atau 'score'.")

        if data_type == "action":
            raw_action = payload.get("action", 1)
            if isinstance(raw_action, bool):
                raise ValueError("Kode aksi harus berupa bilangan bulat.")
            if isinstance(raw_action, float) and not raw_action.is_integer():
                raise ValueError("Kode aksi harus berupa bilangan bulat.")
            try:
                action = int(raw_action)
            except (TypeError, ValueError) as exc:
                raise ValueError("Kode aksi harus berupa bilangan bulat.") from exc
            if action not in ACTION_LABELS:
                raise ValueError("Kode aksi hanya boleh 1 (Serang), 2 (Bertahan), atau 3 (Heal).")
            message = action
            self.action = action
            self.score = None
        else:
            raw_score = payload.get("score", 0)
            if isinstance(raw_score, bool):
                raise ValueError("Skor harus berupa bilangan bulat.")
            if isinstance(raw_score, float) and not raw_score.is_integer():
                raise ValueError("Skor harus berupa bilangan bulat tanpa pecahan.")
            try:
                score = int(raw_score)
            except (TypeError, ValueError) as exc:
                raise ValueError("Skor harus berupa bilangan bulat.") from exc
            if score < 0:
                raise ValueError("Skor tidak boleh negatif.")
            if score > MAX_SCORE:
                raise ValueError(f"Skor melebihi batas aplikasi {MAX_SCORE}.")
            message = score
            self.score = score
            self.action = None

        if not (0 <= message < self.p):
            raise ValueError(
                f"Pesan m = {message} harus memenuhi 0 ≤ m < p = {self.p}. "
                "Pilih nilai yang lebih kecil atau gunakan Mode Aman."
            )

        self.data_type = data_type
        self.m = message
        self.m_prime = elgamal.mask_message(message, self.K_player, self.p)
        self.step = max(self.step, 4)
        self.log(3, "info", f"Tahap 3: pesan {message} disamarkan dengan K menjadi m'.")

        stage = {
            "number": 3,
            "key": "mask",
            "title": "Tahap 3 — Penyamaran Pesan dengan Kunci Sesi",
            "blocks": [
                {
                    "label": "3a. Pesan asli pemain",
                    "formula": "0 ≤ m < p",
                    "substitution": f"m = {message} → {_message_label(data_type, message)}",
                    "result": f"Pesan asli: {_message_label(data_type, message)}",
                },
                {
                    "label": "3b. Samarkan dengan K hasil Diffie-Hellman",
                    "formula": "m' = (m + K) mod p",
                    "substitution": (
                        f"m' = ({message} + {self.K_player}) mod {self.p} = {self.m_prime}"
                    ),
                    "result": f"Pesan bertopeng: m' = {self.m_prime}",
                    "tone": "success",
                },
            ],
            "summary": f"m = {message} → m' = {self.m_prime}",
            "note": (
                "m' inilah yang akan dienkripsi ElGamal. Tanpa K, Eve tidak dapat "
                "memulihkan m walau ia berhasil memecahkan ElGamal."
            ),
            "values": {
                "m": _num(self.m),
                "m_prime": _num(self.m_prime),
                "K": _num(self.K_player),
                "data_type": data_type,
                "label": _message_label(data_type, message),
            },
        }
        return {"ok": True, "stage": stage, "view": self.view()}

    # ------------------------------------------------------------------
    # Tahap 4 - enkripsi ElGamal
    # ------------------------------------------------------------------

    def encrypt_message(self) -> dict[str, object]:
        self._require(self.m_prime is not None, "Siapkan pesan pada Tahap 3 terlebih dahulu.")
        self._require(self.c1 is None, "Pesan sudah dienkripsi. Reset untuk mengulang.")
        assert self.p is not None and self.g is not None and self.y is not None
        assert self.m_prime is not None

        result = elgamal.encrypt(self.p, self.g, self.y, self.m_prime)
        self.k = result["k"]
        self.c1 = result["c1"]
        self.c2 = result["c2"]
        self.yk = result["yk"]
        self.step = max(self.step, 5)

        self.add_packet(
            4,
            "PEMAIN",
            "SERVER",
            "ELGAMAL · ciphertext",
            [
                {"label": "c1", "value": str(self.c1)},
                {"label": "c2", "value": str(self.c2)},
            ],
            "ElGamal mengirim dua bilangan. Eave tidak dapat memisahkan m' dari c1 dan c2.",
        )
        self.log(4, "info", "Tahap 4: ciphertext ElGamal (c1, c2) dikirim ke server.")

        stage = {
            "number": 4,
            "key": "encrypt",
            "title": "Tahap 4 — Enkripsi ElGamal oleh Pemain",
            "blocks": [
                {
                    "label": "4a. Pilih nonce k",
                    "formula": "2 ≤ k ≤ p-2 ; FPB(k, p-1) = 1",
                    "substitution": f"k = {self.k}\nFPB({self.k}, {self.p - 1}) = 1",
                    "result": f"Nonce sesi: k = {self.k} (rahasia pemain, dipakai sekali).",
                },
                {
                    "label": "4b. Hitung c1",
                    "formula": "c1 = g^k mod p",
                    "substitution": f"c1 = {self.g}^{self.k} mod {self.p} = {self.c1}",
                    "result": f"c1 = {self.c1}",
                },
                {
                    "label": "4c. Hitung c2",
                    "formula": "c2 = m' · y^k mod p",
                    "substitution": (
                        f"y^k mod p = {self.y}^{self.k} mod {self.p} = {self.yk}\n"
                        f"c2 = ({self.m_prime} · {self.yk}) mod {self.p} = {self.c2}"
                    ),
                    "result": f"c2 = {self.c2}",
                    "tone": "success",
                },
            ],
            "summary": f"(c1, c2) = ({self.c1}, {self.c2})",
            "note": "Kedua bilangan ini yang melintasi jaringan dan dapat disadap Eve.",
            "values": {
                "k": _num(self.k),
                "c1": _num(self.c1),
                "c2": _num(self.c2),
                "yk": _num(self.yk),
            },
        }
        return {"ok": True, "stage": stage, "view": self.view()}

    # ------------------------------------------------------------------
    # Tahap 5 - dekripsi server
    # ------------------------------------------------------------------

    def decrypt_message(self) -> dict[str, object]:
        self._require(self.c1 is not None and self.c2 is not None, "Enkripsi pesan terlebih dahulu.")
        self._require(self.m_recovered is None, "Pesan sudah didekripsi. Reset untuk mengulang.")
        assert self.p is not None and self.x is not None and self.c1 is not None
        assert self.c2 is not None and self.m_prime is not None and self.K_server is not None

        result = elgamal.decrypt(self.p, self.x, self.c1, self.c2)
        self.s = int(result["s"])
        self.s_inv = int(result["s_inv"])
        self.m_prime_recovered = int(result["message"])
        self.m_recovered = elgamal.unmask_message(self.m_prime_recovered, self.K_server, self.p)
        self.decrypt_valid = self.m_recovered == self.m
        self.step = max(self.step, 6)

        label = _message_label(self.data_type, self.m_recovered)
        if self.decrypt_valid:
            self.log(5, "ok", f"Tahap 5: server memulihkan pesan '{label}'.")
        else:
            self.log(5, "danger", "Tahap 5: pesan hasil dekripsi tidak cocok dengan aslinya.")

        stage = {
            "number": 5,
            "key": "decrypt",
            "title": "Tahap 5 — Dekripsi ElGamal oleh Server",
            "blocks": [
                {
                    "label": "5a. Dekripsi ElGamal",
                    "formula": "s = c1^x mod p ; m' = c2 · s^-1 mod p",
                    "substitution": (
                        f"s = {self.c1}^{self.x} mod {self.p} = {self.s}\n"
                        f"s^-1 mod p = {self.s_inv}  (cek s·s^-1 mod p = 1)\n"
                        f"m' = {self.c2} · {self.s_inv} mod {self.p} = {self.m_prime_recovered}"
                    ),
                    "result": f"Pesan bertopeng diterima: m' = {self.m_prime_recovered}",
                },
                {
                    "label": "5b. Lepas topeng dengan K",
                    "formula": "m = (m' - K) mod p",
                    "substitution": (
                        f"m = ({self.m_prime_recovered} - {self.K_server}) mod {self.p} = {self.m_recovered}"
                    ),
                    "result": f"Data diterima server: {label}",
                    "tone": "success" if self.decrypt_valid else "danger",
                },
            ],
            "summary": label,
            "note": (
                "Server memakai x untuk membuka ElGamal, lalu K hasil DH untuk melepas "
                "topeng. Kedua rahasia harus benar agar m pulih."
            ),
            "values": {
                "s": _num(self.s),
                "s_inv": _num(self.s_inv),
                "m_prime": _num(self.m_prime_recovered),
                "m": _num(self.m_recovered),
                "label": label,
                "valid": self.decrypt_valid,
            },
        }
        return {"ok": True, "stage": stage, "view": self.view()}

    # ------------------------------------------------------------------
    # Tahap 6 - panel Eve
    # ------------------------------------------------------------------

    def eve_stage(self) -> dict[str, object]:
        self._require(self.p is not None, "Jalankan Tahap 0 terlebih dahulu.")
        self._require(self.m_recovered is not None, "Selesaikan dekripsi pada Tahap 5 terlebih dahulu.")
        self.step = max(self.step, 7)
        self.log(6, "warn", "Tahap 6: Eve memeriksa data publik yang berhasil disadap.")

        visible = self._eve_visible()
        hidden = self._eve_hidden()
        stage = {
            "number": 6,
            "key": "eve",
            "title": "Tahap 6 — Panel Penyadap (Eve)",
            "type": "eve",
            "visible": visible,
            "hidden": hidden,
            "blocks": [
                {
                    "label": "6a. Yang bisa dilihat Eve",
                    "formula": "p, q, g, y, A, B, c1, c2",
                    "substitution": "Semua nilai ini melintasi jaringan atau dipublikasikan.",
                    "result": "Eve dapat menyalin seluruh paket, tetapi tidak memperoleh kunci.",
                },
                {
                    "label": "6b. Yang tidak bisa dilihat Eve",
                    "formula": "a, b, x, k, K, m",
                    "substitution": "Nilai-nilai ini tidak pernah dikirim atau hanya ada di sisi masing-masing peran.",
                    "result": "Eve harus memecahkan logaritma diskret untuk menebak a, b, atau x.",
                    "tone": "danger",
                },
            ],
            "summary": "Eve hanya melihat data publik; kerahasiaan bergantung pada sulitnya logaritma diskret.",
            "note": (
                "Dari y = g^x mod p, Eve harus mencari x. Dari A = g^a mod p, Eve harus "
                "mencari a. Pada Mode Demo 16 bit, pencarian seperti ini masih mungkin "
                "dilakukan dengan brute force; pada Mode Aman 128 bit, jauh lebih mahal."
            ),
            "values": {},
        }
        return {"ok": True, "stage": stage, "view": self.view()}

    # ------------------------------------------------------------------
    # Tahap 7 - serangan cheater
    # ------------------------------------------------------------------

    def tamper_ciphertext(self) -> dict[str, object]:
        self._require(self.c2 is not None and self.m_recovered is not None, "Selesaikan Tahap 5 terlebih dahulu.")
        self._require(self.tamper is None, "Serangan sudah dijalankan. Reset untuk mengulang.")
        assert self.p is not None and self.x is not None and self.c1 is not None
        assert self.c2 is not None and self.K_server is not None and self.m is not None

        # Eve tidak tahu K atau m. Ia hanya mengubah c2. Simulator memilih
        # perubahan yang menghasilkan nilai berbeda agar skenario mudah diamati.
        original_c2 = self.c2
        tampered = original_c2
        tampered_plain = self.m_recovered
        delta_used = 0
        for _ in range(64):
            delta = (int.from_bytes(os.urandom(2), "big") % (self.p - 1)) + 1
            candidate_c2 = (original_c2 + delta) % self.p
            candidate = elgamal.decrypt(self.p, self.x, self.c1, candidate_c2)
            candidate_masked = int(candidate["message"])
            candidate_plain = elgamal.unmask_message(candidate_masked, self.K_server, self.p)
            if candidate_plain != self.m:
                tampered = candidate_c2
                tampered_plain = candidate_plain
                delta_used = delta
                break

        if tampered_plain == self.m:
            tampered = (original_c2 + 1) % self.p
            candidate = elgamal.decrypt(self.p, self.x, self.c1, tampered)
            tampered_plain = elgamal.unmask_message(int(candidate["message"]), self.K_server, self.p)
            delta_used = 1

        # m' hasil dekripsi langsung dihitung ulang agar jelas.
        candidate = elgamal.decrypt(self.p, self.x, self.c1, tampered)
        tampered_masked = int(candidate["message"])

        range_valid = self._valid_domain(tampered_plain)
        integrity_ok = tampered_plain == self.m
        suspicious = not integrity_ok

        original_label = _message_label(self.data_type, self.m)
        tampered_label = _message_label(self.data_type, tampered_plain)

        self.tamper = {
            "original_c2": original_c2,
            "tampered_c2": tampered,
            "delta": delta_used,
            "m_prime": tampered_masked,
            "m": tampered_plain,
            "original_m": self.m,
            "original_label": original_label,
            "label": tampered_label,
            "range_valid": range_valid,
            "integrity_ok": integrity_ok,
            "suspicious": suspicious,
        }
        self.step = max(self.step, 8)

        self.add_packet(
            7,
            "EVE",
            "SERVER",
            "PAKET DIUBAH · serangan cheater",
            [
                {"label": "c1", "value": str(self.c1)},
                {"label": "c2 (asli)", "value": str(original_c2)},
                {"label": "c2 (diubah)", "value": str(tampered)},
            ],
            "Eve mengubah c2 di jalan. Server tetap mendekripsi karena tidak ada tag integritas.",
            status="tampered",
        )
        self.log(7, "danger", f"Tahap 7: c2 diubah; server menerima nilai berbeda ({tampered_plain}).")
        if not range_valid:
            self.log(7, "warn", "Hasil berada di luar domain pesan yang valid.")
        else:
            self.log(7, "warn", "Hasil masih berada di domain, tetapi berbeda dari nilai asli — malleability.")

        stage = {
            "number": 7,
            "key": "tamper",
            "title": "Tahap 7 — Skenario Serangan Cheater",
            "type": "tamper",
            "blocks": [
                {
                    "label": "7a. Eve mengubah ciphertext",
                    "formula": "c2' = (c2 + Δ) mod p",
                    "substitution": (
                        f"c2 asli = {original_c2}\n"
                        f"Δ = {delta_used}\n"
                        f"c2' = ({original_c2} + {delta_used}) mod {self.p} = {tampered}"
                    ),
                    "result": f"Paket diubah: c2 → {tampered}",
                    "tone": "danger",
                },
                {
                    "label": "7b. Server mendekripsi paket palsu",
                    "formula": "s = c1^x mod p ; m' = c2'·s^-1 mod p ; m = (m' - K) mod p",
                    "substitution": (
                        f"m' hasil dekripsi = {tampered_masked}\n"
                        f"m hasil pelepasan topeng = {tampered_plain}\n"
                        f"pesan asli yang seharusnya = {self.m}"
                    ),
                    "result": f"Server menampilkan: {tampered_label}",
                    "tone": "danger",
                },
                {
                    "label": "7c. Status validasi",
                    "formula": "cek domain pesan dan perbandingan integritas",
                    "substitution": (
                        f"valid secara domain: {'ya' if range_valid else 'tidak'}\n"
                        f"cocok dengan nilai asli: {'ya' if integrity_ok else 'tidak'}"
                    ),
                    "result": (
                        "MENCURIGAKAN — pesan berubah di jaringan."
                        if suspicious
                        else "Tidak ada perubahan terdeteksi."
                    ),
                    "tone": "danger" if suspicious else "success",
                },
            ],
            "tamper": {
                "original_c2": str(original_c2),
                "tampered_c2": str(tampered),
                "delta": str(delta_used),
                "m_prime": str(tampered_masked),
                "m": str(tampered_plain),
                "original_m": str(self.m),
                "original_label": original_label,
                "label": tampered_label,
                "range_valid": range_valid,
                "integrity_ok": integrity_ok,
                "suspicious": suspicious,
            },
            "summary": (
                f"Server menerima '{tampered_label}' (asli: '{original_label}'). "
                "Status: MENCURIGAKAN."
            ),
            "note": (
                "ElGamal polos bersifat malleable: perubahan pada c2 menghasilkan perubahan "
                "pada plaintext tanpa error. Deteksi pada simulator ini memakai validasi domain "
                "dan perbandingan dengan nilai asli yang disimpan; server nyata tanpa tanda "
                "tangan digital/MAC tidak memiliki cara kriptografis untuk mengetahuinya."
            ),
            "values": {
                "original_c2": str(original_c2),
                "tampered_c2": str(tampered),
                "delta": str(delta_used),
                "m_prime": str(tampered_masked),
                "m": str(tampered_plain),
                "original_m": str(self.m),
                "range_valid": range_valid,
                "integrity_ok": integrity_ok,
                "suspicious": suspicious,
            },
        }
        return {"ok": True, "stage": stage, "view": self.view()}

    def _valid_domain(self, value: int) -> bool:
        if self.data_type == "action":
            return value in ACTION_LABELS
        return 0 <= value <= MAX_SCORE

    # ------------------------------------------------------------------
    # Tampilan state untuk frontend
    # ------------------------------------------------------------------

    def _eve_visible(self) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []

        def add(key: str, label: str, value: int | None, note: str = "") -> None:
            if value is not None:
                rows.append({"key": key, "label": label, "value": str(value), "note": note})

        add("p", "p (modulus publik)", self.p, "safe prime")
        add("q", "q (faktor prima)", self.q, "p = 2q + 1")
        add("g", "g (generator)", self.g, "dipakai bersama")
        add("y", "y (kunci publik server)", self.y, "y = g^x mod p")
        add("A", "A (kunci publik pemain)", self.A, "A = g^a mod p")
        add("B", "B (kunci publik server)", self.B, "B = g^b mod p")
        add("c1", "c1 (ciphertext)", self.c1, "c1 = g^k mod p")
        add("c2", "c2 (ciphertext)", self.c2, "c2 = m'·y^k mod p")
        if self.tamper:
            rows.append(
                {
                    "key": "c2_tampered",
                    "label": "c2 setelah diubah",
                    "value": str(self.tamper["tampered_c2"]),
                    "note": "terlihat di jaringan",
                }
            )
        return rows

    @staticmethod
    def _eve_hidden() -> list[dict[str, str]]:
        return [
            {"key": "a", "label": "a", "note": "rahasia pemain (DH)"},
            {"key": "b", "label": "b", "note": "rahasia server (DH)"},
            {"key": "x", "label": "x", "note": "kunci privat ElGamal server"},
            {"key": "k", "label": "k", "note": "nonce enkripsi pemain"},
            {"key": "K", "label": "K", "note": "kunci sesi hasil DH"},
            {"key": "m", "label": "m", "note": "pesan asli"},
            {"key": "mprime", "label": "m'", "note": "pesan bertopeng"},
        ]

    def _role_view(self) -> dict[str, object]:
        def rows(items: list[tuple[str, str, int | None, str]]) -> list[dict[str, str]]:
            return [
                {"key": key, "label": label, "value": str(value), "note": note}
                for key, label, value, note in items
                if value is not None
            ]

        player_public = rows(
            [
                ("p", "p", self.p, "parameter publik"),
                ("q", "q", self.q, "parameter publik"),
                ("g", "g", self.g, "generator"),
                ("y", "y server", self.y, "kunci publik ElGamal"),
                ("B", "B server", self.B, "diterima dari server"),
            ]
        )
        player_secret = rows(
            [
                ("a", "a", self.a, "eksponen rahasia pemain"),
                ("K", "K", self.K_player, "kunci sesi hasil DH"),
                ("m", "m", self.m, "pesan asli"),
                ("mprime", "m'", self.m_prime, "pesan bertopeng"),
                ("k", "k", self.k, "nonce ElGamal"),
            ]
        )
        player_sent = rows(
            [
                ("A", "A", self.A, "dikirim ke server"),
                ("c1", "c1", self.c1, "ciphertext"),
                ("c2", "c2", self.c2, "ciphertext"),
            ]
        )

        server_public = rows(
            [
                ("p", "p", self.p, "parameter publik"),
                ("q", "q", self.q, "parameter publik"),
                ("g", "g", self.g, "generator"),
                ("y", "y", self.y, "kunci publik sendiri"),
                ("A", "A pemain", self.A, "diterima dari pemain"),
                ("B", "B", self.B, "dikirim ke pemain"),
            ]
        )
        server_secret = rows(
            [
                ("x", "x", self.x, "kunci privat ElGamal"),
                ("b", "b", self.b, "eksponen rahasia server"),
                ("K", "K", self.K_server, "kunci sesi hasil DH"),
                ("s", "s", self.s, "c1^x mod p"),
                ("sinv", "s^-1", self.s_inv, "invers modular s"),
                ("mprime", "m' diterima", self.m_prime_recovered, "hasil dekripsi"),
                ("m", "m diterima", self.m_recovered, "hasil akhir"),
            ]
        )
        server_received = rows(
            [
                ("c1", "c1", self.c1, "ciphertext diterima"),
                ("c2", "c2", self.c2, "ciphertext diterima"),
            ]
        )

        return {
            "player": {
                "name": "PEMAIN",
                "subtitle": "Klien game",
                "public": player_public,
                "secret": player_secret,
                "sent": player_sent,
            },
            "server": {
                "name": "SERVER",
                "subtitle": "Game authority",
                "public": server_public,
                "secret": server_secret,
                "received": server_received,
            },
            "eve": {
                "name": "EVE",
                "subtitle": "Penyadap jaringan",
                "visible": self._eve_visible(),
                "hidden": self._eve_hidden(),
            },
        }

    def view(self) -> dict[str, object]:
        mode_label = MODES[self.mode]["label"] if self.mode else None
        return {
            "has_session": self.p is not None,
            "mode": self.mode,
            "mode_label": mode_label,
            "bits": self.bits,
            "step": self.step,
            "params": (
                {"p": str(self.p), "q": str(self.q), "g": str(self.g)}
                if self.p is not None
                else None
            ),
            "dh": {
                "A": _num(self.A),
                "B": _num(self.B),
                "verified": self.K_verified,
            },
            "elgamal": {"y": _num(self.y)},
            "message": {
                "data_type": self.data_type,
                "m": _num(self.m),
                "m_prime": _num(self.m_prime),
                "label": _message_label(self.data_type, self.m),
            },
            "cipher": {"c1": _num(self.c1), "c2": _num(self.c2)},
            "decryption": {
                "m": _num(self.m_recovered),
                "label": _message_label(self.data_type, self.m_recovered),
                "valid": self.decrypt_valid,
            },
            "tamper": None if self.tamper is None else {
                "m": str(self.tamper["m"]),
                "label": str(self.tamper["label"]),
                "suspicious": bool(self.tamper["suspicious"]),
                "range_valid": bool(self.tamper["range_valid"]),
            },
            "packets": self.packets,
            "logs": self.logs,
            "roles": self._role_view(),
        }

    def state_only(self) -> dict[str, object]:
        return {"ok": True, "view": self.view()}

    @staticmethod
    def _require(condition: bool, message: str) -> None:
        if not condition:
            raise FlowError(message)


def _mod_text(base: int, exp: int, mod: int) -> int:
    """Nilai mod_exp untuk teks tahap (bukan perhitungan frontend)."""
    from mathutil import mod_exp

    return mod_exp(base, exp, mod)


SESSION = GameSession()
SESSION_LOCK = threading.RLock()

# Arena pertarungan memakai parameter p=23 dan pasangan kunci terpisah.
ARENA = game.ArenaSession()
ARENA_LOCK = threading.RLock()


def _is_int(value: object) -> bool:
    """True hanya untuk int, bukan bool."""
    return isinstance(value, int) and not isinstance(value, bool)


class ApiHandler(BaseHTTPRequestHandler):
    """Handler HTTP untuk file statis dan endpoint JSON."""

    server_version = "SecureGameSim/1.0"
    protocol_version = "HTTP/1.1"

    # ------------------------------------------------------------------
    # Util HTTP
    # ------------------------------------------------------------------

    def log_message(self, fmt: str, *args: object) -> None:  # noqa: A003
        # Akses request tidak perlu membanjiri terminal; error tetap dicetak.
        if args and str(args[0]).startswith(("4", "5")):
            super().log_message(fmt, *args)

    def _send_bytes(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_json(self, payload: dict[str, object], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_bytes(body, "application/json; charset=utf-8", status)

    def _error(self, message: str, status: int = 400) -> None:
        with SESSION_LOCK:
            view = SESSION.view()
        self._send_json({"ok": False, "error": message, "view": view}, status)

    def _read_json(self) -> dict[str, object]:
        length_header = self.headers.get("Content-Length")
        try:
            length = int(length_header or "0")
        except ValueError as exc:
            raise ValueError("Content-Length tidak valid.") from exc
        if length > 1_000_000:
            raise ValueError("Body terlalu besar.")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Body harus berupa JSON yang valid.") from exc
        if not isinstance(data, dict):
            raise ValueError("Body JSON harus berupa objek.")
        return data

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/state":
            with SESSION_LOCK:
                self._send_json(SESSION.state_only())
            return
        if path == "/api/eve":
            try:
                with SESSION_LOCK:
                    payload = SESSION.eve_stage()
                    payload.pop("view", None)
                    payload["progress"] = {"step": SESSION.step}
                    payload["logs"] = SESSION.logs
                    payload["packets"] = SESSION.packets
                    payload["eve"] = {
                        "visible": SESSION._eve_visible(),
                        "hidden": SESSION._eve_hidden(),
                    }
                self._send_json(payload)
            except FlowError as exc:
                self._error(str(exc), 409)
            except Exception as exc:  # pragma: no cover - jalur darurat
                self._error(f"Terjadi kesalahan server: {exc}", 500)
            return
        if path == "/api/health":
            self._send_json({"ok": True, "service": "secure-multiplayer-game-simulator"})
            return
        if path == "/api/arena/state":
            with ARENA_LOCK:
                self._send_json({"ok": True, "arena": ARENA.state()})
            return
        if path == "/api/textbook":
            self._send_json({"ok": True, "textbook": game.textbook_demo()})
            return
        if path.startswith("/api/"):
            self._error("Endpoint tidak ditemukan.", 404)
            return
        self._serve_static(path)

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    def _handle_arena_post(self, path: str) -> None:
        """Tangani endpoint arena dan demonstrasi p=23."""
        try:
            if path == "/api/arena/reset":
                # Baca body lebih dulu agar koneksi keep-alive tidak
                # meninggalkan sisa "{}" untuk request berikutnya.
                self._read_json()
                with ARENA_LOCK:
                    ARENA.reset()
                    self._send_json({"ok": True, "arena": ARENA.state()})
                return

            payload = self._read_json()
            with ARENA_LOCK:
                if path == "/api/arena/encrypt":
                    action_id = payload.get("action")
                    mode = payload.get("mode", "deterministic")
                    if not isinstance(action_id, str):
                        raise game.GameError(
                            "Field 'action' wajib berupa string (attack/skill/defend)."
                        )
                    if not isinstance(mode, str):
                        raise game.GameError("Field 'mode' harus berupa string.")
                    encryption = ARENA.encrypt_action(action_id, mode)
                    result = {
                        "ok": True,
                        "encryption": encryption,
                        "arena": ARENA.state(),
                    }
                elif path == "/api/arena/submit":
                    ciphertext = payload.get("ciphertext")
                    if not isinstance(ciphertext, dict):
                        raise game.GameError(
                            "Field 'ciphertext' wajib berupa objek {c1, c2}."
                        )
                    c1 = ciphertext.get("c1")
                    c2 = ciphertext.get("c2")
                    if not _is_int(c1) or not _is_int(c2):
                        raise game.GameError("c1 dan c2 harus bilangan bulat.")
                    damage = payload.get("damage")
                    if damage is not None and not _is_int(damage):
                        raise game.GameError(
                            "Field 'damage' harus bilangan bulat bila dikirim."
                        )
                    claimed_action = payload.get("action")
                    if claimed_action is not None and not isinstance(claimed_action, str):
                        raise game.GameError(
                            "Field 'action' harus berupa string bila dikirim."
                        )
                    transaction = ARENA.submit(
                        c1,
                        c2,
                        claimed_action=claimed_action,
                        claimed_damage=damage,
                    )
                    result = {
                        "ok": True,
                        "transaction": transaction,
                        "arena": ARENA.state(),
                    }
                elif path == "/api/textbook/elgamal":
                    message = payload.get("m", game.DEMO_MESSAGE)
                    k_value = payload.get("k", game.DEMO_K)
                    if not _is_int(message):
                        raise game.GameError("Field 'm' harus bilangan bulat.")
                    if not _is_int(k_value):
                        raise game.GameError("Field 'k' harus bilangan bulat.")
                    result = {
                        "ok": True,
                        "demo": game.textbook_elgamal(message, k_value),
                    }
                else:
                    raise game.GameError("Endpoint tidak ditemukan.")
            self._send_json(result)
        except (game.GameError, ValueError) as exc:
            with ARENA_LOCK:
                arena_state = ARENA.state()
            self._send_json(
                {"ok": False, "error": str(exc), "arena": arena_state}, 400
            )
        except Exception as exc:  # pragma: no cover - jalur darurat
            with ARENA_LOCK:
                arena_state = ARENA.state()
            self._send_json(
                {
                    "ok": False,
                    "error": f"Terjadi kesalahan server: {exc}",
                    "arena": arena_state,
                },
                500,
            )

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path

        # Endpoint arena memakai state dan kunci yang terpisah dari SESSION.
        if path in {
            "/api/arena/encrypt",
            "/api/arena/submit",
            "/api/arena/reset",
            "/api/textbook/elgamal",
        }:
            self._handle_arena_post(path)
            return

        routes: dict[str, str] = {
            "/api/setup": "setup",
            "/api/elgamal/key": "keygen",
            "/api/keygen": "keygen",
            "/api/dh/start": "dh_start",
            "/api/dh/finish": "dh_finish",
            "/api/send": "prepare_message",
            "/api/encrypt": "encrypt_message",
            "/api/decrypt": "decrypt_message",
            "/api/tamper": "tamper_ciphertext",
            "/api/reset": "reset",
        }
        action = routes.get(path)
        if action is None:
            self._error("Endpoint tidak ditemukan.", 404)
            return

        try:
            payload = self._read_json()
            with SESSION_LOCK:
                if action == "setup":
                    result = SESSION.setup(str(payload.get("mode", "")).strip())
                elif action == "reset":
                    SESSION.reset()
                    result = SESSION.state_only()
                elif action == "prepare_message":
                    result = SESSION.prepare_message(payload)
                elif action == "keygen":
                    result = SESSION.generate_key()
                elif action == "dh_start":
                    result = SESSION.dh_start()
                elif action == "dh_finish":
                    result = SESSION.dh_finish()
                elif action == "encrypt_message":
                    result = SESSION.encrypt_message()
                elif action == "decrypt_message":
                    result = SESSION.decrypt_message()
                elif action == "tamper_ciphertext":
                    result = SESSION.tamper_ciphertext()
                else:  # pragma: no cover - tidak mungkin terjadi
                    raise ValueError("Aksi tidak dikenal.")
            self._send_json(result)
        except FlowError as exc:
            self._error(str(exc), 409)
        except ValueError as exc:
            self._error(str(exc), 400)
        except Exception as exc:  # pragma: no cover - jalur darurat
            self._error(f"Terjadi kesalahan server: {exc}", 500)

    # ------------------------------------------------------------------
    # File statis
    # ------------------------------------------------------------------

    def _serve_static(self, path: str) -> None:
        if path in ("/", "/index.html"):
            relative = "index.html"
        elif path.startswith("/static/"):
            relative = path[len("/static/"):]
        else:
            self._error("Halaman tidak ditemukan.", 404)
            return

        target = (STATIC_DIR / relative).resolve()
        try:
            target.relative_to(STATIC_DIR.resolve())
        except ValueError:
            self._error("Akses file ditolak.", 403)
            return

        if not target.is_file():
            self._error("File tidak ditemukan.", 404)
            return

        content_type, _ = mimetypes.guess_type(str(target))
        if target.suffix == ".js":
            content_type = "text/javascript"
        elif target.suffix == ".css":
            content_type = "text/css"
        elif target.suffix == ".ttf":
            content_type = "font/ttf"
        elif target.suffix == ".html":
            content_type = "text/html"
        content_type = (content_type or "application/octet-stream") + (
            "; charset=utf-8" if content_type and content_type.startswith(("text/", "application/json", "image/svg")) else ""
        )
        try:
            body = target.read_bytes()
        except OSError:
            self._error("Gagal membaca file.", 500)
            return
        self._send_bytes(body, content_type)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Secure Multiplayer Game Simulator")
    parser.add_argument("--host", default="127.0.0.1", help="Host (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port (default 8000)")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), ApiHandler)
    print("=" * 66)
    print("  Secure Multiplayer Game Simulator")
    print("  Kriptografi (C) - Kelompok 4")
    print(f"  Server berjalan di http://localhost:{args.port}")
    print("  Tekan Ctrl+C untuk berhenti.")
    print("=" * 66)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer dihentikan.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
