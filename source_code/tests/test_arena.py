"""Pengujian arena pertarungan dan demonstrasi manual p=23.

Jalankan dari folder source_code:
    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import game_engine as game
import server
from mathutil import mod_exp


def _encrypt(arena: game.ArenaSession, action: str, mode: str = "deterministic") -> dict:
    return arena.encrypt_action(action, mode)


class TextbookTests(unittest.TestCase):
    """Nilai harus persis sama dengan perhitungan manual pada laporan."""

    def test_diffie_hellman_values(self):
        demo = game.textbook_demo()["dh"]
        self.assertEqual(demo["A"], 8)
        self.assertEqual(demo["B"], 19)
        self.assertEqual(demo["K_A"], 2)
        self.assertEqual(demo["K_B"], 2)
        self.assertTrue(demo["verified"])

    def test_elgamal_values(self):
        demo = game.textbook_demo()["elgamal"]
        self.assertEqual(demo["y"], 8)
        self.assertEqual(demo["c1"], 10)
        self.assertEqual(demo["c2"], 3)
        self.assertEqual(demo["s"], 6)
        self.assertEqual(demo["inverse"], 4)
        self.assertEqual(demo["recovered"], 12)
        self.assertTrue(demo["verified"])

    def test_inverse_trace(self):
        trace = game.textbook_demo()["elgamal"]["inverse_trace"]
        self.assertEqual(trace["inverse"], 4)
        self.assertEqual(trace["check"], 1)
        self.assertTrue(trace["steps"])

    def test_textbook_elgamal_other_inputs(self):
        for message in (1, 2, 3, 7, 12, 22):
            for k in (3, 5, 7, 13, 21):
                demo = game.textbook_elgamal(message, k)
                self.assertEqual(demo["recovered"], message)
                self.assertTrue(demo["verified"])
                self.assertEqual(demo["c2"], (message * demo["yk"]) % 23)

    def test_textbook_rejects_invalid_inputs(self):
        with self.assertRaises(game.GameError):
            game.textbook_elgamal(0, 3)
        with self.assertRaises(game.GameError):
            game.textbook_elgamal(23, 3)
        with self.assertRaises(game.GameError):
            game.textbook_elgamal(12, 2)  # FPB(2, 22) != 1
        with self.assertRaises(game.GameError):
            game.textbook_elgamal(12, 22)


class ArenaTests(unittest.TestCase):
    def setUp(self):
        self.arena = game.ArenaSession()

    def submit(self, action: str, damage=None):
        encrypted = _encrypt(self.arena, action)
        return self.arena.submit(
            encrypted["ciphertext"]["c1"],
            encrypted["ciphertext"]["c2"],
            claimed_damage=damage,
        )

    def test_initial_state(self):
        snapshot = self.arena.state()["game"]
        self.assertEqual(snapshot["player_hp"], 100)
        self.assertEqual(snapshot["monster_hp"], 100)
        self.assertEqual(snapshot["turn"], 0)
        self.assertEqual(snapshot["status"], "active")

    def test_attack_mapping_and_retaliation(self):
        result = self.submit("attack")["result"]
        self.assertEqual(result["damage_dealt"], 25)
        self.assertEqual(result["monster_hp_after"], 75)
        self.assertEqual(result["player_hp_after"], 90)
        self.assertEqual(result["turn"], 1)

    def test_skill_mapping_and_retaliation(self):
        result = self.submit("skill")["result"]
        self.assertEqual(result["damage_dealt"], 30)
        self.assertEqual(result["monster_hp_after"], 70)
        self.assertEqual(result["player_hp_after"], 94)

    def test_defend_blocks_and_heals(self):
        self.arena.player_hp = 50
        result = self.submit("defend")["result"]
        self.assertEqual(result["damage_dealt"], 0)
        self.assertEqual(result["monster_hp_after"], 100)
        self.assertEqual(result["player_hp_after"], 55)
        self.assertEqual(result["monster_retaliation"], 0)

    def test_monster_hp_never_negative_and_victory(self):
        self.arena.monster_hp = 10
        result = self.submit("skill")["result"]
        self.assertEqual(result["monster_hp_after"], 0)
        self.assertTrue(result["victory"])
        self.assertEqual(result["monster_retaliation"], 0)
        self.arena.reset()
        self.arena.monster_hp = 1
        self.assertEqual(self.submit("attack")["result"]["monster_hp_after"], 0)

    def test_cannot_act_after_game_over(self):
        for _ in range(4):
            self.submit("attack")
        with self.assertRaises(game.GameError):
            self.submit("attack")

    def test_claimed_damage_is_ignored(self):
        transaction = self.submit("attack", damage=999)
        self.assertTrue(transaction["claimed_damage_ignored"])
        self.assertEqual(transaction["result"]["damage_dealt"], 25)
        self.assertEqual(transaction["result"]["monster_hp_after"], 75)

    def test_invalid_ciphertext_is_rejected_without_hp_change(self):
        with self.assertRaises(game.GameError):
            self.arena.submit(0, 3)
        snapshot = self.arena.state()
        self.assertEqual(snapshot["game"]["monster_hp"], 100)
        self.assertEqual(snapshot["last_transaction"]["status"], "rejected")
        self.assertFalse(snapshot["validation"]["decryption_ok"])

    def test_roundtrip_for_all_action_codes(self):
        for action in ("attack", "skill", "defend"):
            self.arena.reset()
            encrypted = _encrypt(self.arena, action)
            self.assertEqual(encrypted["ciphertext"]["c1"], 10)
            self.assertEqual(
                encrypted["ciphertext"]["c2"],
                game.ACTIONS[game.ACTION_BY_ID[action]["code"]]["code"] * 6 % 23,
            )
            transaction = self.arena.submit(
                encrypted["ciphertext"]["c1"], encrypted["ciphertext"]["c2"]
            )
            self.assertEqual(transaction["decrypted_code"], game.ACTION_BY_ID[action]["code"])

    def test_random_k_roundtrip(self):
        encrypted = _encrypt(self.arena, "attack", "random")
        self.assertTrue(1 < encrypted["encryption"]["k"] < 23)
        transaction = self.arena.submit(
            encrypted["ciphertext"]["c1"], encrypted["ciphertext"]["c2"]
        )
        self.assertEqual(transaction["decrypted_code"], 1)

    def test_invalid_action_id_and_mode(self):
        with self.assertRaises(game.GameError):
            self.arena.encrypt_action("heal", "deterministic")
        with self.assertRaises(game.GameError):
            self.arena.encrypt_action("attack", "super")


class ApiTests(unittest.TestCase):
    """Uji endpoint HTTP dengan server sungguhan pada port acak."""

    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.ApiHandler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=5)

    def setUp(self):
        server.ARENA.reset()

    def request(self, method: str, path: str, body=None):
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=10) as response:
                return response.status, response.read()
        except HTTPError as error:
            return error.code, error.read()

    def json_request(self, method: str, path: str, body=None):
        status, raw = self.request(method, path, body)
        return status, json.loads(raw.decode("utf-8"))

    def test_homepage_contains_arena_and_textbook(self):
        status, raw = self.request("GET", "/")
        self.assertEqual(status, 200)
        text = raw.decode("utf-8")
        self.assertIn("Arena otoritatif", text)
        self.assertIn("Studi kasus pertarungan", text)
        self.assertIn("Diffie-Hellman", text)
        self.assertIn("ElGamal", text)
        self.assertIn("Kelompok 4", text)

    def test_arena_state(self):
        status, data = self.json_request("GET", "/api/arena/state")
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertEqual(data["arena"]["game"]["monster_hp"], 100)
        self.assertEqual(data["arena"]["keys"]["public"]["y"], 8)
        self.assertTrue(data["arena"]["validation"]["dh_verified"])

    def test_textbook_endpoint(self):
        status, data = self.json_request("GET", "/api/textbook")
        self.assertEqual(status, 200)
        self.assertEqual(data["textbook"]["dh"]["K_A"], 2)
        self.assertEqual(data["textbook"]["elgamal"]["c1"], 10)
        self.assertEqual(data["textbook"]["elgamal"]["c2"], 3)
        self.assertEqual(data["textbook"]["elgamal"]["recovered"], 12)

    def test_end_to_end_attack(self):
        status, encrypted = self.json_request(
            "POST", "/api/arena/encrypt", {"action": "attack", "mode": "deterministic"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(encrypted["encryption"]["ciphertext"], {"c1": 10, "c2": 6})
        status, submitted = self.json_request(
            "POST",
            "/api/arena/submit",
            {"ciphertext": encrypted["encryption"]["ciphertext"], "action": "attack"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(submitted["transaction"]["decrypted_code"], 1)
        self.assertTrue(submitted["transaction"]["message_match"])
        self.assertEqual(submitted["arena"]["game"]["monster_hp"], 75)
        self.assertEqual(submitted["arena"]["game"]["player_hp"], 90)

    def test_claim_damage_is_ignored_by_server(self):
        _, encrypted = self.json_request(
            "POST", "/api/arena/encrypt", {"action": "attack", "mode": "deterministic"}
        )
        status, submitted = self.json_request(
            "POST",
            "/api/arena/submit",
            {"ciphertext": encrypted["encryption"]["ciphertext"], "damage": 999},
        )
        self.assertEqual(status, 200)
        self.assertTrue(submitted["transaction"]["claimed_damage_ignored"])
        self.assertEqual(submitted["transaction"]["result"]["damage_dealt"], 25)
        self.assertEqual(submitted["arena"]["game"]["monster_hp"], 75)

    def test_invalid_ciphertext_returns_400_and_keeps_hp(self):
        status, data = self.json_request(
            "POST", "/api/arena/submit", {"ciphertext": {"c1": 0, "c2": 3}}
        )
        self.assertEqual(status, 400)
        self.assertFalse(data["ok"])
        self.assertIn("arena", data)
        self.assertEqual(data["arena"]["game"]["monster_hp"], 100)
        self.assertEqual(data["arena"]["last_transaction"]["status"], "rejected")

    def test_invalid_action_and_body(self):
        status, data = self.json_request(
            "POST", "/api/arena/encrypt", {"action": "heal", "mode": "deterministic"}
        )
        self.assertEqual(status, 400)
        self.assertIn("Aksi tidak dikenal", data["error"])

        status, data = self.json_request("POST", "/api/arena/encrypt", ["bukan", "objek"])
        self.assertEqual(status, 400)
        self.assertIn("objek", data["error"].lower())

    def test_arena_reset(self):
        _, encrypted = self.json_request(
            "POST", "/api/arena/encrypt", {"action": "attack", "mode": "deterministic"}
        )
        self.json_request(
            "POST",
            "/api/arena/submit",
            {"ciphertext": encrypted["encryption"]["ciphertext"]},
        )
        status, data = self.json_request("POST", "/api/arena/reset", {})
        self.assertEqual(status, 200)
        self.assertEqual(data["arena"]["game"]["monster_hp"], 100)
        self.assertEqual(data["arena"]["game"]["turn"], 0)

    def test_unknown_endpoint_is_404(self):
        status, data = self.json_request("GET", "/api/tidak-ada")
        self.assertEqual(status, 404)
        self.assertFalse(data["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)