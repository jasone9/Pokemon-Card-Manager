import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import tkinter as tk
import unittest
from unittest.mock import Mock, patch
from urllib.error import URLError

from pokemon_card_manager import control, model, view


def saved_card(name, identifier):
    return {
        "name": name, "set": "Base Set", "rarity": "Common",
        "market": 1.0, "tcgPlayerId": identifier, "imageUrl": None,
    }


class ViewBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        model.init_database(self.temporary.name)
        self.app = view.PokemonCardManager.__new__(view.PokemonCardManager)
        self.app.root = Mock()
        self.app.last_card = None
        self.app.photo = None
        self.app.entry = Mock()
        self.app.save_button = Mock()
        self.app.image_label = Mock()
        self.app.card_labels = {field: Mock() for field in ("Name", "Set", "Type", "Rarity", "Market")}
        self.app.filter_field = Mock()
        self.app.filter_field.get.return_value = "Name"
        self.app.filter_text = Mock()
        self.app.filter_text.get.return_value = ""
        self.app.collection_tree = Mock()
        self.app.collection_tree.get_children.return_value = ()
        self.app.total_value = Mock()
        self.app.show_page = Mock()

    def tearDown(self):
        model.close_database()
        self.temporary.cleanup()

    def test_filtered_deletion_removes_the_original_record(self):
        model.collection[:] = [saved_card("Pikachu", "1"), saved_card("Blastoise", "2"), saved_card("Pichu", "3")]
        self.app.filter_text.get.return_value = "blastoise"
        self.app.refresh_collection_view()
        self.assertEqual(self.app.collection_tree.insert.call_args.kwargs["iid"], "1")
        self.app.collection_tree.selection.return_value = ("1",)
        self.app.remove_selected()
        self.assertEqual([r["name"] for r in model.collection], ["Pikachu", "Pichu"])
        model.load_collection()
        self.assertEqual([r["name"] for r in model.collection], ["Pikachu", "Pichu"])

    def test_multiple_selection_does_not_shift_remaining_indices(self):
        model.collection[:] = [saved_card("Pikachu", "1"), saved_card("Blastoise", "2"), saved_card("Pichu", "3")]
        self.app.collection_tree.selection.return_value = ("0", "2")
        self.app.remove_selected()
        self.assertEqual([r["name"] for r in model.collection], ["Blastoise"])

    def test_remove_failure_restores_the_visible_collection(self):
        model.collection[:] = [saved_card("Pikachu", "1")]
        self.app.collection_tree.selection.return_value = ("0",)
        with patch.object(model, "persist_collection", side_effect=PermissionError("read only")), patch.object(view.messagebox, "showerror") as error:
            self.app.remove_selected()
        self.assertEqual([r["name"] for r in model.collection], ["Pikachu"])
        error.assert_called_once()
        self.app.collection_tree.delete.assert_not_called()

    def test_save_failure_does_not_add_a_card_or_navigate_away(self):
        self.app.last_card = {"name": "Pikachu", "prices": {"market": 1}}
        with patch.object(model, "persist_collection", side_effect=PermissionError("read only")), patch.object(view.messagebox, "showerror") as error:
            self.app.save_current_card()
        self.assertEqual(model.collection, [])
        self.app.show_page.assert_not_called()
        self.app.entry.delete.assert_not_called()
        error.assert_called_once()

    def test_failed_new_search_cannot_save_a_stale_previous_card(self):
        self.app.entry.get.return_value = "not found"
        for result in (None, control.CardLookupError("offline")):
            with self.subTest(result=result):
                self.app.last_card = {"name": "Previous result"}
                with patch.object(control, "get_card_info") as lookup, patch.object(view.messagebox, "showerror"), patch.object(view.messagebox, "showinfo"):
                    if isinstance(result, Exception):
                        lookup.side_effect = result
                    else:
                        lookup.return_value = result
                    self.app.search_card()
                self.assertIsNone(self.app.last_card)
                self.app.save_button.configure.assert_called_with(state="disabled")
                self.app.save_current_card()
                self.assertEqual(model.collection, [])

    def test_unknown_and_zero_prices_replace_previous_search_price(self):
        self.app.entry.get.return_value = "Pikachu"
        with patch.object(control, "get_card_info") as lookup, patch.object(self.app, "_load_card_image"):
            for price, expected in ((5.52, "Market: $5.52"), (None, "Market: Unavailable"), (0, "Market: $0.00")):
                lookup.return_value = {"name": "Pikachu", "prices": {"market": price}}
                self.app.search_card()
                self.app.card_labels["Market"].configure.assert_called_with(text=expected)
                self.app.save_button.configure.assert_called_with(state="normal")

    def test_successful_save_survives_reload(self):
        self.app.last_card = {"name": "Pikachu", "tcgPlayerId": "1", "prices": {"market": 0}}
        self.app.save_current_card()
        self.app.show_page.assert_called_once_with(0)
        self.assertIsNone(self.app.last_card)
        model.load_collection()
        self.assertEqual(model.collection[0]["name"], "Pikachu")
        self.assertEqual(model.collection[0]["market"], 0)

    def test_image_download_failure_does_not_block_saving_the_card(self):
        self.app.entry.get.return_value = "Pikachu"
        card = {"name": "Pikachu", "imageUrl": "https://example.invalid/card.jpg"}
        with patch.object(control, "get_card_info", return_value=card), patch.object(view, "urlopen", side_effect=URLError("offline")):
            self.app.search_card()
        self.app.image_label.configure.assert_called_with(image="", text="Image unavailable")
        self.app.save_button.configure.assert_called_with(state="normal")
        self.app.save_current_card()
        model.load_collection()
        self.assertEqual(model.collection[0]["name"], "Pikachu")
        self.assertIsNone(model.collection[0]["market"])


class LaunchTests(unittest.TestCase):
    def test_import_from_another_directory_has_no_gui_storage_or_network_side_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(__file__).resolve().parents[1]
            environment = {**os.environ, "PYTHONPATH": str(root), "POKEMON_CARD_MANAGER_DATA_DIR": str(Path(directory) / "data")}
            result = subprocess.run(
                [sys.executable, "-c", "from unittest.mock import patch\nwith patch('tkinter.Tk', side_effect=AssertionError('GUI on import')), patch('urllib.request.urlopen', side_effect=AssertionError('network on import')):\n    import pokemon_card_manager.view\n"],
                cwd=directory, env=environment, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((Path(directory) / "data").exists())

    def test_module_entrypoint_calls_the_gui_main_function(self):
        with patch.object(view, "main") as main:
            runpy.run_module("pokemon_card_manager", run_name="__main__")
        main.assert_called_once_with()

    def test_closing_the_window_closes_storage_and_tolerates_an_already_destroyed_root(self):
        root = Mock()
        root.destroy.side_effect = [None, tk.TclError("application has been destroyed")]
        root.mainloop.side_effect = lambda: root.destroy()
        with patch.object(view.tk, "Tk", return_value=root), patch.object(view, "PokemonCardManager"), patch.object(model, "init_database"), patch.object(model, "load_collection"), patch.object(model, "load_users"), patch.object(model, "close_database") as close:
            view.main()
        close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
