"""Exercise the real themed widgets under a desktop display or CI's Xvfb."""

import os
import sys
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from pokemon_card_manager import control, model, view


class DesktopTests(unittest.TestCase):
    def setUp(self):
        if not os.environ.get("DISPLAY") and sys.platform not in ("win32", "darwin"):
            self.skipTest("A desktop display is required; CI runs this test under Xvfb.")
        self.root = tk.Tk()
        self.addCleanup(self.root.destroy)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        model.init_database(self.directory.name)
        self.addCleanup(model.close_database)
        self.app = view.PokemonCardManager(self.root)
        self.root.update()

    def test_themed_app_can_save_filter_remove_and_manage_users(self):
        self.app.show_page(2)
        self.app.new_user_entry.insert(0, "Ash")
        self.app.add_user()
        self.assertEqual(self.app.user_listbox.get(0), "Ash")
        for name, identifier in (("Pikachu", "88086"), ("Blastoise", "88087")):
            with self.subTest(card=name):
                self.app.show_page(1)
                self.app.entry.insert(0, name)
                with patch.object(control, "get_card_info", return_value={
                    "name": name, "tcgPlayerId": identifier,
                    "setName": "Base Set", "rarity": "Common",
                    "prices": {"market": 5.52},
                }):
                    self.app.search_card()
                self.root.update()
                self.assertFalse(self.app.save_button.instate(["disabled"]))
                self.app.save_button.invoke()
        self.root.update()
        self.assertEqual(len(self.app.collection_tree.get_children()), 2)
        self.assertFalse(self.app.empty_label.winfo_ismapped())
        self.app.filter_text.set("Blastoise")
        self.app.refresh_collection_view()
        self.assertEqual(self.app.collection_tree.get_children(), ("1",))
        self.app.collection_tree.selection_set("1")
        self.app.remove_selected()
        self.app.clear_collection_filter()
        self.assertEqual(self.app.collection_tree.get_children(), ("0",))
        self.assertEqual(self.app.total_value.cget("text"), "Total Value: $5.52")
        model.load_collection()
        self.assertEqual([card["name"] for card in model.collection], ["Pikachu"])
        self.app.show_page(2)
        self.app.user_listbox.selection_set(0)
        self.app.remove_user()
        self.assertEqual(self.app.user_listbox.size(), 0)

    def test_primary_controls_fit_at_the_minimum_window_size(self):
        self.root.geometry("840x700")
        for page, widgets in (
            (0, (self.app.collection_tree, self.app.total_value)),
            (1, (self.app.entry, self.app.save_button)),
            (2, (self.app.new_user_entry, self.app.user_listbox)),
        ):
            with self.subTest(page=page):
                self.app.show_page(page)
                self.root.update()
                for widget in widgets:
                    left = widget.winfo_rootx() - self.root.winfo_rootx()
                    top = widget.winfo_rooty() - self.root.winfo_rooty()
                    self.assertGreaterEqual(left, 0)
                    self.assertGreaterEqual(top, 0)
                    self.assertLessEqual(left + widget.winfo_width(), self.root.winfo_width())
                    self.assertLessEqual(top + widget.winfo_height(), self.root.winfo_height())


if __name__ == "__main__":
    unittest.main()
