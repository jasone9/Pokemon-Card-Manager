import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pokemon_card_manager import model


def card(name="Pikachu", card_id="88086", market=5.52):
    return {
        "name": name, "set": "Mysterious Treasures", "rarity": "Common",
        "market": market, "tcgPlayerId": card_id, "imageUrl": None,
    }


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        model.init_database(self.directory)

    def tearDown(self):
        model.close_database()
        self.temporary.cleanup()

    def test_collection_round_trip_preserves_duplicates_ids_and_missing_prices(self):
        records = [card(), card(), card("Unknown price", "2", None)]
        model.collection.extend(records)
        model.persist_collection()
        self.assertEqual(json.loads(model.COLLECTION_FILE.read_text()), records)
        rows = model.conn.execute(
            'SELECT name, "set", market, tcg_player_id, image_url FROM cards ORDER BY id'
        ).fetchall()
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0], ("Pikachu", "Mysterious Treasures", 5.52, "88086", None))
        self.assertIsNone(rows[2][2])
        model.close_database()
        model.init_database(self.directory)
        model.load_collection()
        self.assertEqual(model.collection, records)
        model.collection.pop(1)
        model.persist_collection()
        model.load_collection()
        self.assertEqual(len(model.collection), 2)
        self.assertEqual(model.conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0], 2)

    def test_missing_json_recovers_collection_from_sqlite(self):
        model.collection.append(card())
        model.persist_collection()
        model.COLLECTION_FILE.unlink()
        model.collection.clear()
        model.load_collection()
        self.assertEqual(model.collection, [card()])

    def test_original_example_json_can_be_imported(self):
        example = Path(__file__).resolve().parents[1] / "examples" / "collection.json"
        model.COLLECTION_FILE.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
        model.load_collection()
        self.assertEqual([r["name"] for r in model.collection], ["Pikachu", "Blastoise Spirit Link"])
        self.assertAlmostEqual(model.collection_total(), 5.63)
        self.assertEqual(model.conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0], 2)

    def test_invalid_json_does_not_overwrite_collection_or_database(self):
        model.collection.append(card())
        model.persist_collection()
        for contents in ("{", '{"name": "wrong shape"}', '["not a record"]'):
            with self.subTest(contents=contents):
                model.COLLECTION_FILE.write_text(contents, encoding="utf-8")
                with self.assertRaises(ValueError):
                    model.load_collection()
                self.assertEqual(model.collection, [card()])
                self.assertEqual(model.COLLECTION_FILE.read_text(), contents)
                self.assertEqual(model.conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0], 1)

    def test_failed_snapshot_write_rolls_back_sqlite(self):
        model.collection.append(card())
        model.persist_collection()
        model.collection.append(card("Blastoise", "2"))
        with patch.object(model, "_write_json", side_effect=PermissionError("read only")):
            with self.assertRaises(PermissionError):
                model.persist_collection()
        self.assertEqual(json.loads(model.COLLECTION_FILE.read_text()), [card()])
        self.assertEqual(model.conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0], 1)

    def test_failed_json_encoding_keeps_previous_snapshot(self):
        model.collection.append(card())
        model.persist_collection()
        model.collection.append(card("Invalid price", "3", float("nan")))
        with self.assertRaises(ValueError):
            model.persist_collection()
        self.assertEqual(json.loads(model.COLLECTION_FILE.read_text()), [card()])
        self.assertEqual(model.conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0], 1)
        self.assertEqual(list(self.directory.glob("*.tmp")), [])

    def test_data_directory_is_independent_of_working_directory(self):
        other = self.directory / "elsewhere"
        other.mkdir()
        target = self.directory / "configured-data"
        previous = Path.cwd()
        try:
            os.chdir(other)
            with patch.dict(os.environ, {"POKEMON_CARD_MANAGER_DATA_DIR": str(target)}):
                model.init_database()
                model.collection.append(card())
                model.persist_collection()
            self.assertTrue((target / "collection.json").is_file())
            self.assertFalse((other / "collection.json").exists())
        finally:
            os.chdir(previous)

    def test_default_storage_does_not_follow_the_working_directory(self):
        target = self.directory / "default-data"
        other = self.directory / "working-directory"
        other.mkdir()
        previous = Path.cwd()
        try:
            os.chdir(other)
            with patch.dict(os.environ, {}, clear=True), patch.object(model, "DEFAULT_DATA_DIR", target):
                model.init_database()
                model.collection.append(card())
                model.persist_collection()
            self.assertTrue((target / "collection.json").is_file())
            self.assertEqual(list(other.iterdir()), [])
        finally:
            os.chdir(previous)

    def test_users_are_validated_persisted_and_removed(self):
        self.assertFalse(model.add_user("  ")[0])
        self.assertTrue(model.add_user("  Alice  ")[0])
        self.assertFalse(model.add_user("Alice")[0])
        self.assertTrue(model.add_user("O'Brien")[0])
        self.assertEqual(model.get_user_count(), 2)
        model.close_database()
        model.init_database(self.directory)
        model.load_users()
        self.assertEqual([r["username"] for r in model.get_all_users()], ["Alice", "O'Brien"])
        self.assertTrue(model.remove_user("Alice")[0])
        self.assertFalse(model.remove_user("missing")[0])
        self.assertEqual(model.get_user_count(), 1)
        self.assertEqual(model.conn.execute("SELECT username FROM users").fetchall(), [("O'Brien",)])
        self.assertEqual(json.loads(model.USERS_FILE.read_text())[0]["username"], "O'Brien")
        model.get_all_users()[0]["username"] = "changed copy"
        self.assertEqual(model.get_all_users()[0]["username"], "O'Brien")

    def test_missing_json_recovers_users_from_sqlite(self):
        model.add_user("Alice")
        model.USERS_FILE.unlink()
        model.users.clear()
        model.load_users()
        self.assertEqual(model.get_all_users()[0]["username"], "Alice")

    def test_user_write_failures_do_not_change_saved_users(self):
        model.add_user("Alice")
        before = model.get_all_users()
        with patch.object(model, "_write_json", side_effect=PermissionError("read only")):
            self.assertFalse(model.add_user("Bob")[0])
            self.assertFalse(model.remove_user("Alice")[0])
        self.assertEqual(model.get_all_users(), before)
        self.assertEqual(json.loads(model.USERS_FILE.read_text()), before)
        self.assertEqual(model.conn.execute("SELECT username FROM users").fetchall(), [("Alice",)])


class CollectionLogicTests(unittest.TestCase):
    def tearDown(self):
        model.collection.clear()

    def test_api_record_normalizes_sets_and_optional_prices(self):
        for set_fields in ({"setName": "Base Set"}, {"set": {"name": "Base Set"}}, {"set": "Base Set"}):
            with self.subTest(set_fields=set_fields):
                record = model.record_from_card({"name": "Pikachu", **set_fields, "prices": {"market": 0}})
                self.assertEqual(record["set"], "Base Set")
                self.assertEqual(record["market"], 0)
        for prices in (None, [], "unavailable", {}):
            with self.subTest(prices=prices):
                record = model.record_from_card({"prices": prices})
                self.assertEqual(record["name"], "Unknown")
                self.assertEqual(record["set"], "Unknown Set")
                self.assertIsNone(record["market"])

    def test_filters_are_case_insensitive_and_preserve_source_indices(self):
        model.collection[:] = [card(), {**card("Blastoise", "2"), "rarity": "Rare"}, card("Pichu", "3")]
        self.assertEqual([i for i, _ in model.filter_collection("Name", " BLAST ")], [1])
        self.assertEqual([i for i, _ in model.filter_collection("Rarity", "rare")], [1])
        self.assertEqual([i for i, _ in model.filter_collection("Set", "TREASURES")], [0, 1, 2])
        self.assertEqual(len(model.filter_collection("Name", "")), 3)
        self.assertEqual(model.filter_collection("Name", "not present"), [])
        with self.assertRaises(ValueError):
            model.filter_collection("unsupported", "")

    def test_total_handles_zero_numeric_strings_and_unavailable_prices(self):
        values = [0, "5.52", 0.11, None, "unknown", float("nan"), float("inf"), True]
        model.collection[:] = [card(market=value) for value in values]
        self.assertAlmostEqual(model.collection_total(), 5.63)


if __name__ == "__main__":
    unittest.main()
