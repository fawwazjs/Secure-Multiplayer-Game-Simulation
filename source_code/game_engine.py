"""Arena pertarungan pemain vs monster untuk demonstrasi akademik.

Modul ini melengkapi laboratorium tahapan dengan studi kasus yang diminta
pada tugas: pemain memilih aksi, aksi dienkripsi dengan ElGamal memakai
kunci publik server, server mendekripsi, memvalidasi kode aksi, lalu
memperbarui HP monster memakai aturan damage milik server.

Parameter yang dipakai sengaja kecil agar seluruh perhitungan dapat
diperiksa manual:

    p = 23, g = 5, x = 6, y = 8
    Diffie-Hellman: a = 6, b = 15, A = 8, B = 19, K = 2

Kunci ElGamal dan kunci Diffie-Hellman adalah dua pasangan yang terpisah.
Pada arena ini K tidak dipakai sebagai kunci privat ElGamal; K hanya
ditampilkan sebagai demonstrasi pertukaran kunci. Integrasi opsional
m' = (m + K) mod p pada laboratorium tahapan dijelaskan terpisah dan tidak
mengklaim bahwa DH otomatis menjadi kunci ElGamal.

Semua operasi kriptografi memakai mathutil.py dan elgamal.py buatan sendiri.
"""

from __future__ import annotations

import time
from typing import Any

import elgamal
from diffie_hellman import public_value, shared_secret
from mathutil import (
    MathError,
    gcd,
    mod_exp,
    mod_exp_trace,
    mod_inverse,
    mod_inverse_trace,
)

# Parameter demonstrasi yang sama dengan contoh pada laporan.
P = 23
G = 5
DH_A = 6
DH_B = 15
EG_X = 6
EG_Y = 8
DEMO_MESSAGE = 12
DEMO_K = 3

PLAYER_MAX_HP = 100
MONSTER_MAX_HP = 100

ACTIONS: dict[int, dict[str, Any]] = {
    1: {
        "code": 1,
        "id": "attack",
        "name": "Serang",
        "damage": 25,
        "monster_damage": 10,
        "heal": 0,
        "description": "Serangan pedang biasa. Damage 25; monster membalas 10.",
    },
    2: {
        "code": 2,
        "id": "skill",
        "name": "Gunakan Skill",
        "damage": 30,
        "monster_damage": 6,
        "heal": 0,
        "description": "Skill fokus. Damage 30; monster membalas 6.",
    },
    3: {
        "code": 3,
        "id": "defend",
        "name": "Bertahan",
        "damage": 0,
        "monster_damage": 0,
        "heal": 5,
        "description": "Bertahan: damage 0, serangan monster diblokir, pulihkan 5 HP.",
    },
}

ACTION_BY_ID = {action["id"]: action for action in ACTIONS.values()}


class GameError(ValueError):
    """Kesalahan aturan arena atau data yang tidak valid."""


def _now() -> str:
    return time.strftime("%H:%M:%S")


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def action_from_id(action_id: str) -> dict[str, Any]:
    """Kembalikan definisi aksi dari id teks attack/skill/defend."""
    if not isinstance(action_id, str) or action_id not in ACTION_BY_ID:
        raise GameError("Aksi tidak dikenal. Gunakan attack, skill, atau defend.")
    return ACTION_BY_ID[action_id]


def action_from_code(code: int) -> dict[str, Any]:
    """Kembalikan definisi aksi dari kode numerik 1..3."""
    if not _is_int(code) or code not in ACTIONS:
        raise GameError(f"Kode aksi {code!r} tidak dikenal.")
    return ACTIONS[code]


def actions_payload() -> list[dict[str, Any]]:
    """Daftar aksi yang boleh dipilih pemain (tanpa data rahasia)."""
    return [
        {
            "code": action["code"],
            "id": action["id"],
            "name": action["name"],
            "damage": action["damage"],
            "monster_damage": action["monster_damage"],
            "heal": action["heal"],
            "description": action["description"],
        }
        for action in ACTIONS.values()
    ]


# ---------------------------------------------------------------------------
# Demonstrasi p=23 untuk verifikasi manual
# ---------------------------------------------------------------------------


def _dh_steps(a: int, b: int, A: int, B: int, K_A: int, K_B: int) -> list[dict[str, str]]:
    return [
        {
            "index": "1",
            "title": "Parameter publik",
            "formula": "p = 23, g = 5",
            "substitution": "p = 23; g = 5",
            "result": "Kedua pihak mengetahui p dan g.",
        },
        {
            "index": "2",
            "title": "Kunci privat",
            "formula": "a = 6, b = 15",
            "substitution": f"a = {a}; b = {b}",
            "result": "Kunci privat tidak dikirim melalui jaringan.",
        },
        {
            "index": "3",
            "title": "Kunci publik Alice",
            "formula": "A = g^a mod p",
            "substitution": f"A = 5^{a} mod 23",
            "result": f"A = {A}",
        },
        {
            "index": "4",
            "title": "Kunci publik Bob",
            "formula": "B = g^b mod p",
            "substitution": f"B = 5^{b} mod 23",
            "result": f"B = {B}",
        },
        {
            "index": "5",
            "title": "Rahasia bersama Alice",
            "formula": "K_A = B^a mod p",
            "substitution": f"K_A = {B}^{a} mod 23",
            "result": f"K_A = {K_A}",
        },
        {
            "index": "6",
            "title": "Rahasia bersama Bob",
            "formula": "K_B = A^b mod p",
            "substitution": f"K_B = {A}^{b} mod 23",
            "result": f"K_B = {K_B}",
        },
        {
            "index": "7",
            "title": "Verifikasi",
            "formula": "K_A = K_B ?",
            "substitution": f"{K_A} = {K_B}",
            "result": "Pertukaran kunci berhasil" if K_A == K_B else "Pertukaran kunci gagal",
        },
    ]


def _elgamal_steps(
    message: int,
    k: int,
    c1: int,
    c2: int,
    yk: int,
    s: int,
    inverse: int,
    recovered: int,
) -> list[dict[str, str]]:
    return [
        {
            "index": "1",
            "title": "Kunci publik penerima",
            "formula": "y = g^x mod p",
            "substitution": "y = 5^6 mod 23",
            "result": f"y = {EG_Y}; kunci privat x = {EG_X}",
        },
        {
            "index": "2",
            "title": "Pilih bilangan acak k",
            "formula": "1 ≤ k ≤ p-2",
            "substitution": f"k = {k}",
            "result": f"k = {k} (mode deterministik untuk demonstrasi)",
        },
        {
            "index": "3",
            "title": "Ciphertext pertama",
            "formula": "c1 = g^k mod p",
            "substitution": f"c1 = 5^{k} mod 23",
            "result": f"c1 = {c1}",
        },
        {
            "index": "4",
            "title": "Ciphertext kedua",
            "formula": "c2 = m · y^k mod p",
            "substitution": f"c2 = {message} · {yk} mod 23",
            "result": f"c2 = {c2}; ciphertext C = ({c1}, {c2})",
        },
        {
            "index": "5",
            "title": "Dekripsi: rahasia sementara",
            "formula": "s = c1^x mod p",
            "substitution": f"s = {c1}^{EG_X} mod 23",
            "result": f"s = {s}",
        },
        {
            "index": "6",
            "title": "Dekripsi: invers modular",
            "formula": "s⁻¹ mod p",
            "substitution": f"{s} · {inverse} mod 23",
            "result": f"s⁻¹ = {inverse} karena ({s} × {inverse}) mod 23 = 1",
        },
        {
            "index": "7",
            "title": "Pesan hasil dekripsi",
            "formula": "m = c2 · s⁻¹ mod p",
            "substitution": f"m = {c2} · {inverse} mod 23",
            "result": f"m = {recovered}",
        },
    ]


def textbook_demo() -> dict[str, Any]:
    """Hitung contoh p=23 persis seperti pada laporan.

    Hasil yang diharapkan:
      DH: A=8, B=19, K_A=K_B=2
      ElGamal: y=8, c1=10, c2=3, s=6, s⁻¹=4, m'=12
    """
    A = public_value(G, DH_A, P)
    B = public_value(G, DH_B, P)
    K_A = shared_secret(B, DH_A, P)
    K_B = shared_secret(A, DH_B, P)

    y = mod_exp(G, EG_X, P)
    yk = mod_exp(y, DEMO_K, P)
    c1 = mod_exp(G, DEMO_K, P)
    c2 = (DEMO_MESSAGE * yk) % P
    s = mod_exp(c1, EG_X, P)
    inverse = mod_inverse(s, P)
    recovered = (c2 * inverse) % P

    return {
        "parameters": {"p": P, "g": G},
        "dh": {
            "a": DH_A,
            "b": DH_B,
            "A": A,
            "B": B,
            "K_A": K_A,
            "K_B": K_B,
            "verified": K_A == K_B,
            "steps": _dh_steps(DH_A, DH_B, A, B, K_A, K_B),
            "traces": {
                "A": mod_exp_trace(G, DH_A, P),
                "B": mod_exp_trace(G, DH_B, P),
                "K_A": mod_exp_trace(B, DH_A, P),
                "K_B": mod_exp_trace(A, DH_B, P),
            },
        },
        "elgamal": {
            "x": EG_X,
            "y": y,
            "message": DEMO_MESSAGE,
            "k": DEMO_K,
            "yk": yk,
            "c1": c1,
            "c2": c2,
            "s": s,
            "inverse": inverse,
            "recovered": recovered,
            "verified": recovered == DEMO_MESSAGE,
            "steps": _elgamal_steps(
                DEMO_MESSAGE, DEMO_K, c1, c2, yk, s, inverse, recovered
            ),
            "inverse_trace": mod_inverse_trace(s, P),
            "traces": {
                "c1": mod_exp_trace(G, DEMO_K, P),
                "yk": mod_exp_trace(y, DEMO_K, P),
                "s": mod_exp_trace(c1, EG_X, P),
            },
        },
        "note": (
            "Contoh ini memakai pasangan kunci yang terpisah. K = 2 dari "
            "Diffie-Hellman bukan kunci privat ElGamal x = 6 dan tidak dipakai "
            "untuk mendekripsi ciphertext pada arena."
        ),
    }


def textbook_elgamal(message: int = DEMO_MESSAGE, k: int = DEMO_K) -> dict[str, Any]:
    """Hitung ulang contoh ElGamal dengan m dan k yang dipilih pengguna.

    Nilai m harus 1..p-1. Nilai k harus 1..p-2 dan koprima dengan p-1 agar
    invers pada dekripsi selalu ada.
    """
    if not _is_int(message) or not (1 <= message <= P - 1):
        raise GameError(f"Pesan m harus bilangan bulat 1..{P - 1}.")
    if not _is_int(k) or not (1 <= k <= P - 2):
        raise GameError(f"k harus bilangan bulat 1..{P - 2}.")
    if gcd(k, P - 1) != 1:
        raise GameError(f"k harus koprima dengan p-1 = {P - 1}.")

    y = mod_exp(G, EG_X, P)
    yk = mod_exp(y, k, P)
    c1 = mod_exp(G, k, P)
    c2 = (message * yk) % P
    s = mod_exp(c1, EG_X, P)
    inverse = mod_inverse(s, P)
    recovered = (c2 * inverse) % P

    return {
        "parameters": {"p": P, "g": G, "y": y},
        "message": message,
        "k": k,
        "yk": yk,
        "c1": c1,
        "c2": c2,
        "s": s,
        "inverse": inverse,
        "recovered": recovered,
        "verified": recovered == message,
        "steps": _elgamal_steps(message, k, c1, c2, yk, s, inverse, recovered),
        "inverse_trace": mod_inverse_trace(s, P),
    }


# ---------------------------------------------------------------------------
# Arena
# ---------------------------------------------------------------------------


class ArenaSession:
    """State satu pertarungan pemain vs monster."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Kembalikan pertarungan ke kondisi awal; kunci server tetap."""
        self.player_hp = PLAYER_MAX_HP
        self.monster_hp = MONSTER_MAX_HP
        self.turn = 0
        self.status = "active"  # active | victory | defeat
        self.message = "Pertarungan dimulai. Pilih aksi pemain."
        self.history: list[dict[str, Any]] = []
        self.logs: list[dict[str, Any]] = []
        self._log_seq = 0
        self.last_encryption: dict[str, Any] | None = None
        self.last_transaction: dict[str, Any] | None = None
        self.stats = {
            "actions_processed": 0,
            "rejected": 0,
            "damage_dealt": 0,
            "encryptions": 0,
        }
        self._log("SYSTEM", "BOOT", "Arena dimuat dengan parameter p=23, g=5, x=6, y=8.", "info")
        self._log(
            "SERVER",
            "KEYGEN",
            "Kunci ElGamal server siap. Kunci privat x tetap di server.",
            "ok",
        )

    def _log(self, actor: str, tag: str, message: str, tone: str = "info") -> None:
        self._log_seq += 1
        self.logs.append(
            {
                "seq": self._log_seq,
                "time": _now(),
                "actor": actor,
                "tag": tag,
                "message": message,
                "tone": tone,
            }
        )
        if len(self.logs) > 120:
            self.logs = self.logs[-120:]

    def validation(self) -> dict[str, Any]:
        transaction = self.last_transaction
        accepted = bool(transaction and transaction.get("status") == "accepted")
        rejected = bool(transaction and transaction.get("status") == "rejected")
        return {
            "dh_verified": self.dh["verified"],
            "dh_shared": self.dh["K_A"],
            "encryption_ok": self.last_encryption is not None,
            "decryption_ok": accepted,
            "message_match": transaction.get("message_match") if accepted else (False if rejected else None),
            "last_original": transaction.get("original_action") if accepted else None,
            "last_decrypted": transaction.get("decrypted_action") if accepted else None,
            "last_error": transaction.get("error") if rejected else None,
            "server_authority": True,
        }

    def state(self) -> dict[str, Any]:
        return {
            "game": {
                "player_hp": self.player_hp,
                "player_max_hp": PLAYER_MAX_HP,
                "monster_hp": self.monster_hp,
                "monster_max_hp": MONSTER_MAX_HP,
                "turn": self.turn,
                "status": self.status,
                "message": self.message,
                "victory": self.status == "victory",
                "defeat": self.status == "defeat",
                "history": list(self.history),
            },
            "keys": {
                "public": {"p": P, "g": G, "y": EG_Y},
                "private_demo": {"x": EG_X},
                "formula": "y = 5^6 mod 23 = 8",
            },
            "dh": self.dh,
            "actions": actions_payload(),
            "logs": self.logs[-60:],
            "stats": dict(self.stats),
            "last_encryption": self.last_encryption,
            "last_transaction": self.last_transaction,
            "validation": self.validation(),
            "params": {"p": P, "g": G},
            "warning": (
                "Parameter p=23 hanya untuk pembelajaran. Kunci privat "
                "ditampilkan pada mode demo lokal dan tidak boleh dipublikasikan."
            ),
        }

    def encrypt_action(self, action_id: str, mode: str = "deterministic") -> dict[str, Any]:
        """Sisi client: enkripsi kode aksi dengan kunci publik server."""
        action = action_from_id(action_id)
        if mode not in {"deterministic", "random"}:
            raise GameError("Mode enkripsi harus 'deterministic' atau 'random'.")

        k = DEMO_K if mode == "deterministic" else elgamal.choose_k(P)
        encrypted = elgamal.encrypt(P, G, EG_Y, action["code"], k)
        self.last_encryption = {
            "timestamp": _now(),
            "action": action,
            "plaintext": {
                "code": action["code"],
                "action": action["id"],
                "name": action["name"],
            },
            "mode": mode,
            "ciphertext": {"c1": encrypted["c1"], "c2": encrypted["c2"]},
            "encryption": encrypted,
        }
        self.stats["encryptions"] += 1
        self._log(
            "CLIENT",
            "ENCRYPT",
            (
                f"Aksi '{action['name']}' (m={action['code']}) dienkripsi "
                f"dengan kunci publik y={EG_Y} -> C=({encrypted['c1']}, {encrypted['c2']}), "
                f"mode={mode}."
            ),
            "info",
        )
        return self.last_encryption

    def submit(
        self,
        c1: int,
        c2: int,
        claimed_action: str | None = None,
        claimed_damage: int | None = None,
    ) -> dict[str, Any]:
        """Sisi server: dekripsi, validasi, dan terapkan aksi."""
        ciphertext = {"c1": c1, "c2": c2}
        self._log("CLIENT", "SEND", f"Ciphertext C=({c1}, {c2}) dikirim ke server.", "info")

        try:
            if not _is_int(c1) or not _is_int(c2):
                raise GameError("c1 dan c2 harus bilangan bulat.")
            decrypted = elgamal.decrypt(P, EG_X, c1, c2)
            if not decrypted["inverse_ok"]:
                raise GameError("Invers modular hasil dekripsi tidak valid.")
            code = decrypted["message"]
            action = action_from_code(code)
        except (GameError, MathError, elgamal.ElGamalError) as exc:
            message = f"Dekripsi/validasi gagal: {exc}"
            self.stats["rejected"] += 1
            self.last_transaction = {
                "status": "rejected",
                "stage": "decrypt",
                "error": message,
                "ciphertext": ciphertext,
                "claimed_action": claimed_action,
                "claimed_damage": claimed_damage,
                "timestamp": _now(),
            }
            self._log("SERVER", "REJECT", message, "bad")
            raise GameError(message) from exc

        self._log(
            "SERVER",
            "DECRYPT",
            f"Server mendekripsi C=({c1}, {c2}) -> m'={code} ({action['name']}).",
            "ok",
        )

        original_action = None
        message_match: bool | None = None
        last = self.last_encryption
        if last and last["ciphertext"] == ciphertext:
            original_action = last["plaintext"]
            message_match = original_action["code"] == code
            self._log(
                "SERVER",
                "COMPARE",
                f"Pesan asli m={original_action['code']} vs hasil dekripsi m'={code} -> "
                + ("cocok." if message_match else "tidak cocok."),
                "ok" if message_match else "bad",
            )

        self._log(
            "SERVER",
            "VALIDATE",
            (
                f"Kode aksi {code} valid. Server memakai aturan damage sendiri "
                f"({action['damage']} damage), bukan nilai dari client."
            ),
            "ok",
        )

        try:
            result = self.apply_action(code, claimed_damage=claimed_damage)
        except GameError as exc:
            message = f"Aksi tidak dapat diterapkan: {exc}"
            self.stats["rejected"] += 1
            self.last_transaction = {
                "status": "rejected",
                "stage": "game",
                "error": message,
                "ciphertext": ciphertext,
                "decrypted_code": code,
                "decrypted_action": action,
                "claimed_action": claimed_action,
                "claimed_damage": claimed_damage,
                "timestamp": _now(),
            }
            self._log("SERVER", "REJECT", message, "bad")
            raise GameError(message) from exc

        self.stats["actions_processed"] += 1
        self.stats["damage_dealt"] += result["damage_dealt"]
        if claimed_damage is not None:
            self._log(
                "SERVER",
                "AUTHORITY",
                (
                    f"Klaim damage dari client ({claimed_damage}) diabaikan; "
                    f"server memakai damage {result['damage_dealt']}."
                ),
                "warn",
            )
        self._log(
            "SERVER",
            "HP",
            (
                f"HP monster {result['monster_hp_before']} -> {result['monster_hp_after']}; "
                f"HP pemain {result['player_hp_before']} -> {result['player_hp_after']}."
            ),
            "ok" if result["status"] == "active" else "warn",
        )
        if result["victory"]:
            self._log("GAME", "VICTORY", "Monster kalah, HP mencapai 0.", "ok")
        elif result["defeat"]:
            self._log("GAME", "DEFEAT", "Pemain kalah, HP mencapai 0.", "bad")

        transaction = {
            "status": "accepted",
            "stage": "complete",
            "timestamp": _now(),
            "ciphertext": ciphertext,
            "decrypted_code": code,
            "decrypted_action": {
                "code": action["code"],
                "id": action["id"],
                "name": action["name"],
                "damage": action["damage"],
            },
            "original_action": original_action,
            "message_match": message_match,
            "claimed_action": claimed_action,
            "claimed_damage": claimed_damage,
            "claimed_damage_ignored": claimed_damage is not None,
            "result": result,
        }
        self.last_transaction = transaction
        return transaction

    def apply_action(
        self,
        action_code: int,
        claimed_damage: int | None = None,
    ) -> dict[str, Any]:
        """Terapkan aksi yang sudah didekripsi dan divalidasi server."""
        if self.status != "active":
            raise GameError("Pertarungan sudah selesai. Reset arena untuk bermain lagi.")
        if claimed_damage is not None and not _is_int(claimed_damage):
            raise GameError("Klaim damage harus bilangan bulat bila dikirim.")

        action = action_from_code(action_code)
        damage = int(action["damage"])
        monster_damage = int(action["monster_damage"])
        heal = int(action["heal"])

        monster_hp_before = self.monster_hp
        player_hp_before = self.player_hp

        self.monster_hp = max(0, self.monster_hp - damage)

        healed = 0
        if self.monster_hp == 0:
            self.status = "victory"
            self.message = "Monster dikalahkan. Pertarungan selesai."
        else:
            if heal:
                new_hp = min(PLAYER_MAX_HP, self.player_hp + heal)
                healed = new_hp - self.player_hp
                self.player_hp = new_hp
            if monster_damage:
                self.player_hp = max(0, self.player_hp - monster_damage)
            if self.player_hp == 0:
                self.status = "defeat"
                self.message = "Pemain kehabisan HP. Pertarungan selesai."
            else:
                self.message = (
                    f"{action['name']}: {damage} damage ke monster; "
                    f"monster membalas {monster_damage} damage."
                )
                if healed:
                    self.message = (
                        f"{action['name']}: bertahan dan memulihkan {healed} HP."
                    )

        self.turn += 1
        result = {
            "action": action,
            "damage_dealt": damage,
            "monster_hp_before": monster_hp_before,
            "monster_hp_after": self.monster_hp,
            "player_hp_before": player_hp_before,
            "player_hp_after": self.player_hp,
            "monster_retaliation": 0 if self.monster_hp == 0 else monster_damage,
            "healed": healed,
            "turn": self.turn,
            "status": self.status,
            "message": self.message,
            "claimed_damage": claimed_damage,
            "claimed_damage_ignored": claimed_damage is not None,
            "victory": self.status == "victory",
            "defeat": self.status == "defeat",
        }

        self.history.append(
            {
                "turn": self.turn,
                "action": action["id"],
                "action_name": action["name"],
                "damage_dealt": damage,
                "monster_hp_after": self.monster_hp,
                "player_hp_after": self.player_hp,
                "claimed_damage": claimed_damage,
                "status": self.status,
            }
        )
        return result

    @property
    def dh(self) -> dict[str, Any]:
        """Nilai DH tetap untuk panel demonstrasi (tidak dipakai ElGamal)."""
        A = public_value(G, DH_A, P)
        B = public_value(G, DH_B, P)
        K_A = shared_secret(B, DH_A, P)
        K_B = shared_secret(A, DH_B, P)
        return {
            "p": P,
            "g": G,
            "a": DH_A,
            "b": DH_B,
            "A": A,
            "B": B,
            "K_A": K_A,
            "K_B": K_B,
            "verified": K_A == K_B,
        }


__all__ = [
    "P",
    "G",
    "DH_A",
    "DH_B",
    "EG_X",
    "EG_Y",
    "DEMO_MESSAGE",
    "DEMO_K",
    "PLAYER_MAX_HP",
    "MONSTER_MAX_HP",
    "ACTIONS",
    "ACTION_BY_ID",
    "GameError",
    "action_from_id",
    "action_from_code",
    "actions_payload",
    "textbook_demo",
    "textbook_elgamal",
    "ArenaSession",
]