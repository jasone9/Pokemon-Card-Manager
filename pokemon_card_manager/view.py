"""Tkinter collection, card-search, and user pages from the original tracker."""

import io
import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk
from urllib.request import urlopen

from PIL import Image, ImageTk

from . import control, model

STORAGE_ERRORS = (OSError, ValueError, sqlite3.Error)


class PokemonCardManager:
    def __init__(self, root):
        self.root = root
        self.last_card = None
        self.photo = None
        root.title("Pokemon Card Manager")
        root.geometry("1000x720")
        root.minsize(760, 560)
        root.rowconfigure(0, weight=1)
        root.columnconfigure(0, weight=1)
        self.filter_field = tk.StringVar(master=root, value="Name")
        self.filter_text = tk.StringVar(master=root, value="")
        self.pages = [ttk.Frame(root, padding=16) for _ in range(3)]
        for page in self.pages:
            page.grid(row=0, column=0, sticky="nsew")
        self._build_collection_page()
        self._build_add_page()
        self._build_users_page()
        self.refresh_collection_view()
        self.refresh_users_view()
        self.show_page(0)
        root.protocol("WM_DELETE_WINDOW", root.destroy)

    def show_page(self, index):
        self.pages[index].tkraise()

    def _build_collection_page(self):
        page = self.pages[0]
        page.rowconfigure(2, weight=1)
        page.columnconfigure(0, weight=1)
        heading = ttk.Frame(page)
        heading.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        ttk.Label(heading, text="Pokemon Card Manager", font=("Arial", 18, "bold")).pack(side="left")
        ttk.Button(heading, text="ADD CARD", command=lambda: self.show_page(1)).pack(side="right")
        ttk.Button(heading, text="USERS", command=lambda: self.show_page(2)).pack(side="right", padx=8)
        filters = ttk.Frame(page)
        filters.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 12))
        ttk.Label(filters, text="Filter:").pack(side="left", padx=(0, 8))
        ttk.Combobox(
            filters, values=("Name", "Set", "Rarity"), textvariable=self.filter_field,
            state="readonly", width=12,
        ).pack(side="left", padx=(0, 8))
        filter_entry = ttk.Entry(filters, textvariable=self.filter_text, width=24)
        filter_entry.pack(side="left", padx=(0, 8))
        filter_entry.bind("<Return>", self.refresh_collection_view)
        ttk.Button(filters, text="FILTER", command=self.refresh_collection_view).pack(side="left", padx=4)
        ttk.Button(filters, text="CLEAR", command=self.clear_collection_filter).pack(side="left")
        columns = ("Name", "Set", "Rarity", "Market Value")
        self.collection_tree = ttk.Treeview(page, columns=columns, show="headings", selectmode="extended")
        for column in columns:
            self.collection_tree.heading(column, text=column)
            self.collection_tree.column(column, width=160, minwidth=100)
        self.collection_tree.grid(row=2, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(page, orient="vertical", command=self.collection_tree.yview)
        scrollbar.grid(row=2, column=1, sticky="ns")
        self.collection_tree.configure(yscrollcommand=scrollbar.set)
        self.total_value = ttk.Label(page)
        self.total_value.grid(row=3, column=0, sticky="w", pady=12)
        ttk.Button(page, text="REMOVE SELECTED", command=self.remove_selected).grid(row=4, column=0, sticky="e")

    def _build_add_page(self):
        page = self.pages[1]
        page.columnconfigure(1, weight=1)
        ttk.Button(page, text="BACK", command=lambda: self.show_page(0)).grid(row=0, column=0, sticky="w")
        self.save_button = ttk.Button(page, text="SAVE TO COLLECTION", command=self.save_current_card, state="disabled")
        self.save_button.grid(row=0, column=2, sticky="e")
        ttk.Label(page, text="TCGplayer ID or Card Name:").grid(row=1, column=0, padx=(0, 10), pady=20)
        self.entry = ttk.Entry(page)
        self.entry.grid(row=1, column=1, sticky="ew", pady=20)
        self.entry.bind("<Return>", self.search_card)
        ttk.Button(page, text="SEARCH", command=self.search_card).grid(row=1, column=2, padx=(10, 0))
        self.image_label = ttk.Label(page, anchor="center")
        self.image_label.grid(row=2, column=0, columnspan=3, pady=10)
        self.card_labels = {}
        for row, field in enumerate(("Name", "Set", "Type", "Rarity", "Market"), start=3):
            label = ttk.Label(page)
            label.grid(row=row, column=0, columnspan=3, pady=3)
            self.card_labels[field] = label

    def _build_users_page(self):
        page = self.pages[2]
        page.rowconfigure(1, weight=1)
        page.columnconfigure(0, weight=1)
        ttk.Button(page, text="BACK", command=lambda: self.show_page(0)).grid(row=0, column=0, sticky="w")
        ttk.Label(page, text="User Management", font=("Arial", 16, "bold")).grid(row=0, column=1, pady=12)
        self.user_listbox = tk.Listbox(page, height=15, exportselection=False)
        self.user_listbox.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=12)
        scrollbar = ttk.Scrollbar(page, orient="vertical", command=self.user_listbox.yview)
        scrollbar.grid(row=1, column=2, sticky="ns", pady=12)
        self.user_listbox.configure(yscrollcommand=scrollbar.set)
        controls = ttk.Frame(page)
        controls.grid(row=2, column=0, columnspan=2, pady=12)
        ttk.Label(controls, text="Username:").pack(side="left", padx=5)
        self.new_user_entry = ttk.Entry(controls, width=24)
        self.new_user_entry.pack(side="left", padx=5)
        self.new_user_entry.bind("<Return>", lambda event: self.add_user())
        ttk.Button(controls, text="ADD USER", command=self.add_user).pack(side="left", padx=5)
        ttk.Button(controls, text="REMOVE SELECTED", command=self.remove_user).pack(side="left", padx=5)
        self.total_users = ttk.Label(page)
        self.total_users.grid(row=3, column=0, sticky="w", pady=12)

    def _clear_card_preview(self):
        self.last_card = None
        self.photo = None
        self.save_button.configure(state="disabled")
        self.image_label.configure(image="", text="")
        for label in self.card_labels.values():
            label.configure(text="")

    def search_card(self, event=None):
        self._clear_card_preview()
        query = self.entry.get().strip()
        if not query:
            messagebox.showwarning("Search", "Enter a card name or TCGplayer ID.", parent=self.root)
            return
        try:
            card = control.get_card_info(query)
        except control.CardLookupError as exc:
            messagebox.showerror("Card lookup", str(exc), parent=self.root)
            return
        if card is None:
            messagebox.showinfo("Card lookup", "No card found with that name or ID.", parent=self.root)
            return
        record = model.record_from_card(card)
        self.last_card = card
        price = model.market_value(record["market"])
        values = {
            "Name": record["name"], "Set": record["set"],
            "Type": card.get("cardType") or "Unknown", "Rarity": record["rarity"],
            "Market": f"${price:,.2f}" if price is not None else "Unavailable",
        }
        for field, value in values.items():
            self.card_labels[field].configure(text=f"{field}: {value}")
        self._load_card_image(record["imageUrl"])
        self.save_button.configure(state="normal")

    def _load_card_image(self, url):
        if url:
            try:
                with urlopen(url, timeout=control.HTTP_TIMEOUT) as response:
                    image = Image.open(io.BytesIO(response.read()))
                    image.thumbnail((280, 350))
                    self.photo = ImageTk.PhotoImage(image, master=self.root)
                self.image_label.configure(image=self.photo)
                return
            except (OSError, ValueError, tk.TclError):
                pass
        self.image_label.configure(image="", text="Image unavailable")

    def save_current_card(self):
        if self.last_card is None:
            return
        model.collection.append(model.record_from_card(self.last_card))
        try:
            model.persist_collection()
        except STORAGE_ERRORS as exc:
            model.collection.pop()
            messagebox.showerror("Save failed", str(exc), parent=self.root)
            return
        self.entry.delete(0, tk.END)
        self._clear_card_preview()
        self.refresh_collection_view()
        self.show_page(0)

    def refresh_collection_view(self, event=None):
        for row in self.collection_tree.get_children():
            self.collection_tree.delete(row)
        for index, record in model.filter_collection(self.filter_field.get(), self.filter_text.get()):
            price = model.market_value(record.get("market"))
            self.collection_tree.insert(
                "", "end", iid=str(index), values=(
                    record.get("name"), record.get("set"), record.get("rarity"),
                    f"${price:,.2f}" if price is not None else "-",
                ),
            )
        self.total_value.configure(text=f"Total Value: ${model.collection_total():,.2f}")

    def clear_collection_filter(self):
        self.filter_field.set("Name")
        self.filter_text.set("")
        self.refresh_collection_view()

    def remove_selected(self):
        selected = self.collection_tree.selection()
        if not selected:
            return
        previous = model.collection.copy()
        for index in sorted((int(item) for item in selected), reverse=True):
            model.collection.pop(index)
        try:
            model.persist_collection()
        except STORAGE_ERRORS as exc:
            model.collection[:] = previous
            messagebox.showerror("Remove failed", str(exc), parent=self.root)
            return
        self.refresh_collection_view()

    def add_user(self):
        success, message = model.add_user(self.new_user_entry.get())
        if success:
            self.new_user_entry.delete(0, tk.END)
            self.refresh_users_view()
        else:
            messagebox.showwarning("Users", message, parent=self.root)

    def remove_user(self):
        selected = self.user_listbox.curselection()
        if not selected:
            return
        success, message = model.remove_user(self.user_listbox.get(selected[0]))
        if success:
            self.refresh_users_view()
        else:
            messagebox.showerror("Users", message, parent=self.root)

    def refresh_users_view(self):
        self.user_listbox.delete(0, tk.END)
        for user in model.get_all_users():
            self.user_listbox.insert(tk.END, user["username"])
        self.total_users.configure(text=f"Total Users: {model.get_user_count()}")


def main():
    """Open storage and the window only when explicitly launched."""
    root = tk.Tk()
    try:
        model.init_database()
        model.load_collection()
        model.load_users()
        PokemonCardManager(root)
        root.mainloop()
    except STORAGE_ERRORS as exc:
        messagebox.showerror("Storage error", str(exc), parent=root)
    finally:
        model.close_database()
        try:
            root.destroy()
        except tk.TclError:
            pass  # The window may already have been closed by the user.
