"""Tkinter collection, card-search, and user pages from the original tracker."""

import io
import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk
from urllib.request import urlopen

from PIL import Image, ImageTk

from . import control, model, theme

STORAGE_ERRORS = (OSError, ValueError, sqlite3.Error)


class PokemonCardManager:
    def __init__(self, root):
        self.root = root
        self.last_card = None
        self.photo = None
        root.title("Pokemon Card Manager")
        root.geometry("1060x820")
        root.minsize(840, 700)
        self.style = theme.apply_theme(root)
        root.rowconfigure(1, weight=1)
        root.columnconfigure(0, weight=1)
        device = tk.Frame(root, background=theme.RED)
        device.grid(row=0, column=0, sticky="ew", padx=2, pady=(2, 0))
        device.columnconfigure(0, weight=1)
        theme.device_header(device).grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 14))
        tk.Frame(device, background=theme.INK, height=5).grid(row=1, column=0, sticky="ew")
        screen = tk.Frame(root, background=theme.WHITE, highlightbackground=theme.INK,
                          highlightcolor=theme.INK, highlightthickness=3)
        screen.grid(row=1, column=0, sticky="nsew", padx=24, pady=(18, 0))
        screen.rowconfigure(0, weight=1)
        screen.columnconfigure(0, weight=1)
        footer = tk.Frame(root, background=theme.RED_DARK)
        footer.grid(row=2, column=0, sticky="ew", padx=24, pady=(14, 18))
        tk.Label(footer, text="●  PERSONAL CARD ARCHIVE", foreground=theme.WHITE,
                 background=theme.RED_DARK, font=("TkDefaultFont", 9, "bold")).pack(side="left")
        tk.Label(footer, text="COLLECT  /  ORGANIZE  /  DISCOVER", foreground=theme.WHITE,
                 background=theme.RED_DARK, font=("TkDefaultFont", 9)).pack(side="right")
        self.filter_field = tk.StringVar(master=root, value="Name")
        self.filter_text = tk.StringVar(master=root, value="")
        self.pages = [ttk.Frame(screen, padding=24) for _ in range(3)]
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

    def _page_heading(self, page, number, title, subtitle):
        heading = ttk.Frame(page)
        heading.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 20))
        heading.columnconfigure(0, weight=1)
        ttk.Label(heading, text=number, style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(heading, text=title, style="Title.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 3))
        ttk.Label(heading, text=subtitle, style="Muted.TLabel").grid(row=2, column=0, sticky="w")
        actions = ttk.Frame(heading)
        actions.grid(row=0, column=1, rowspan=3, sticky="e", padx=(18, 0))
        return actions

    def _build_collection_page(self):
        page = self.pages[0]
        page.rowconfigure(2, weight=1)
        page.columnconfigure(0, weight=1)
        actions = self._page_heading(page, "01 / COLLECTION", "Your collection",
                                      "Keep your favorite finds in one place.")
        ttk.Button(actions, text="Users", style="Secondary.TButton",
                   command=lambda: self.show_page(2)).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="+ Add card", style="Primary.TButton",
                   command=lambda: self.show_page(1)).pack(side="left")
        filters = ttk.Frame(page, style="Well.TFrame", padding=12)
        filters.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 18))
        filters.columnconfigure(2, weight=1)
        ttk.Label(filters, text="FILTER BY", style="Well.TLabel").grid(row=0, column=0, padx=(0, 10))
        ttk.Combobox(
            filters, values=("Name", "Set", "Rarity"), textvariable=self.filter_field,
            state="readonly", width=10,
        ).grid(row=0, column=1, padx=(0, 8))
        filter_entry = ttk.Entry(filters, textvariable=self.filter_text, width=24)
        filter_entry.grid(row=0, column=2, sticky="ew", padx=(0, 8))
        filter_entry.bind("<Return>", self.refresh_collection_view)
        ttk.Button(filters, text="Filter", style="Primary.TButton",
                   command=self.refresh_collection_view).grid(row=0, column=3, padx=(0, 6))
        ttk.Button(filters, text="Clear", style="Secondary.TButton",
                   command=self.clear_collection_filter).grid(row=0, column=4)
        columns = ("Name", "Set", "Rarity", "Market Value")
        display = tk.Frame(page, background=theme.BORDER, borderwidth=1)
        display.grid(row=2, column=0, columnspan=2, sticky="nsew")
        display.rowconfigure(0, weight=1)
        display.columnconfigure(0, weight=1)
        self.collection_tree = ttk.Treeview(display, columns=columns, show="headings", selectmode="extended")
        for column in columns:
            anchor = "e" if column == "Market Value" else "w"
            self.collection_tree.heading(column, text=column, anchor=anchor)
            self.collection_tree.column(column, width=160, minwidth=100, anchor=anchor)
        self.collection_tree.column("Set", width=230)
        self.collection_tree.tag_configure("even", background=theme.WHITE)
        self.collection_tree.tag_configure("odd", background=theme.WELL)
        self.collection_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(display, orient="vertical", command=self.collection_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.collection_tree.configure(yscrollcommand=scrollbar.set)
        self.empty_label = ttk.Label(display, text="Your collection starts here.\nUse + Add card to save your first find.",
                                      anchor="center", style="Empty.TLabel")
        summary = ttk.Frame(page, style="Value.TFrame", padding=(16, 13))
        summary.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(18, 0))
        ttk.Button(summary, text="Remove selected", style="Danger.TButton",
                   command=self.remove_selected).pack(side="right", padx=(12, 0))
        ttk.Label(summary, text="SAVED MARKET VALUES", style="ValueMeta.TLabel").pack(anchor="w")
        self.total_value = ttk.Label(summary, style="Value.TLabel")
        self.total_value.pack(anchor="w", pady=(3, 0))

    def _build_add_page(self):
        page = self.pages[1]
        page.columnconfigure(0, weight=1)
        page.rowconfigure(2, weight=1)
        actions = self._page_heading(page, "02 / CARD LOOKUP", "Discover a card",
                                      "Search by name or TCGplayer ID.")
        ttk.Button(actions, text="Back", style="Secondary.TButton",
                   command=lambda: self.show_page(0)).pack(side="left", padx=(0, 8))
        self.save_button = ttk.Button(actions, text="Save to collection", style="Primary.TButton",
                                       command=self.save_current_card, state="disabled")
        self.save_button.pack(side="left")
        search = ttk.Frame(page, style="Well.TFrame", padding=12)
        search.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 18))
        search.columnconfigure(1, weight=1)
        ttk.Label(search, text="CARD NAME / ID", style="Well.TLabel").grid(row=0, column=0, padx=(0, 12))
        self.entry = ttk.Entry(search)
        self.entry.grid(row=0, column=1, sticky="ew")
        self.entry.bind("<Return>", self.search_card)
        ttk.Button(search, text="Search", style="Primary.TButton",
                   command=self.search_card).grid(row=0, column=2, padx=(10, 0))
        preview = ttk.Frame(page, style="Well.TFrame", padding=20)
        preview.grid(row=2, column=0, columnspan=2, sticky="nsew")
        preview.columnconfigure(0, weight=1)
        preview.columnconfigure(1, weight=1)
        preview.rowconfigure(0, weight=1)
        self.image_label = ttk.Label(preview, text="CARD PREVIEW", anchor="center", style="Preview.TLabel")
        self.image_label.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        details = ttk.Frame(preview, style="Well.TFrame", padding=(0, 12))
        details.grid(row=0, column=1, sticky="ew")
        ttk.Label(details, text="CARD DETAILS", style="Well.TLabel").pack(anchor="w", pady=(0, 14))
        self.card_labels = {}
        for field in ("Name", "Set", "Type", "Rarity", "Market"):
            style = "CardName.TLabel" if field == "Name" else "CardDetail.TLabel"
            if field == "Market":
                style = "CardPrice.TLabel"
            label = ttk.Label(details, style=style)
            label.pack(anchor="w", fill="x", pady=(4, 12) if field == "Market" else 3)
            self.card_labels[field] = label

    def _build_users_page(self):
        page = self.pages[2]
        page.rowconfigure(1, weight=1)
        page.columnconfigure(0, weight=1)
        actions = self._page_heading(page, "03 / COLLECTORS", "User management",
                                      "A shared directory of collector names.")
        ttk.Button(actions, text="Back to collection", style="Secondary.TButton",
                   command=lambda: self.show_page(0)).pack()
        display = ttk.Frame(page, style="Well.TFrame", padding=14)
        display.grid(row=1, column=0, columnspan=2, sticky="nsew")
        display.rowconfigure(1, weight=1)
        display.columnconfigure(0, weight=1)
        ttk.Label(display, text="REGISTERED COLLECTORS", style="Well.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.user_listbox = tk.Listbox(display, height=12, exportselection=False,
                                       background=theme.WHITE, foreground=theme.INK,
                                       selectbackground=theme.RED, selectforeground=theme.WHITE,
                                       highlightbackground=theme.BORDER, highlightcolor=theme.BLUE,
                                       highlightthickness=1, borderwidth=0, selectborderwidth=0,
                                       font=("TkDefaultFont", 12))
        self.user_listbox.grid(row=1, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(display, orient="vertical", command=self.user_listbox.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.user_listbox.configure(yscrollcommand=scrollbar.set)
        controls = ttk.Frame(page, style="Well.TFrame", padding=12)
        controls.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(18, 12))
        controls.columnconfigure(1, weight=1)
        ttk.Label(controls, text="USERNAME", style="Well.TLabel").grid(row=0, column=0, padx=(0, 10))
        self.new_user_entry = ttk.Entry(controls, width=24)
        self.new_user_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        self.new_user_entry.bind("<Return>", lambda event: self.add_user())
        ttk.Button(controls, text="Add user", style="Primary.TButton",
                   command=self.add_user).grid(row=0, column=2, padx=(0, 8))
        ttk.Button(controls, text="Remove selected", style="Danger.TButton",
                   command=self.remove_user).grid(row=0, column=3)
        self.total_users = ttk.Label(page, style="Muted.TLabel")
        self.total_users.grid(row=3, column=0, sticky="w", pady=(0, 4))

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
                    image.thumbnail((240, 280))
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
        records = model.filter_collection(self.filter_field.get(), self.filter_text.get())
        for index, record in records:
            price = model.market_value(record.get("market"))
            self.collection_tree.insert(
                "", "end", iid=str(index), values=(
                    record.get("name"), record.get("set"), record.get("rarity"),
                    f"${price:,.2f}" if price is not None else "-",
                ), tags=("odd" if index % 2 else "even",),
            )
        if hasattr(self, "empty_label"):
            if records:
                self.empty_label.place_forget()
            else:
                text = "No cards match this filter.\nTry another search or choose Clear."
                if not model.collection:
                    text = "Your collection starts here.\nUse + Add card to save your first find."
                self.empty_label.configure(text=text)
                self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
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
