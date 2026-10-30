"""A Pokédex-inspired red shell and readable, light display surfaces."""

import tkinter as tk
from tkinter import font as tkfont, ttk

RED = "#D92338"
RED_DARK = "#AE182B"
RED_LIGHT = "#FFF0F1"
WHITE = "#FFFFFF"
INK = "#232830"
MUTED = "#636C77"
BORDER = "#D5DAE0"
WELL = "#F2F4F6"
BLUE = "#249BD7"
GREEN = "#E9F2E4"
GREEN_INK = "#31563B"


def apply_theme(root):
    """Use a colorable ttk theme on Windows, macOS, and Linux."""
    style = ttk.Style(root)
    style.theme_use("clam" if "clam" in style.theme_names() else "default")
    family = tkfont.nametofont("TkDefaultFont", root=root).actual("family")
    base_font = (family, 10)
    root.configure(background=RED_DARK)
    root.option_add("*Font", base_font)
    root.option_add("*TCombobox*Listbox.background", WHITE)
    root.option_add("*TCombobox*Listbox.foreground", INK)
    root.option_add("*TCombobox*Listbox.selectBackground", RED)
    root.option_add("*TCombobox*Listbox.selectForeground", WHITE)

    style.configure(".", background=WHITE, foreground=INK, font=base_font)
    style.configure("TFrame", background=WHITE)
    style.configure("TLabel", background=WHITE, foreground=INK)
    style.configure("Well.TFrame", background=WELL)
    style.configure("Well.TLabel", background=WELL, foreground=MUTED)
    style.configure("Muted.TLabel", foreground=MUTED)
    style.configure("Section.TLabel", foreground=RED_DARK, font=(family, 9, "bold"))
    style.configure("Title.TLabel", font=(family, 23, "bold"))
    style.configure("DeviceTitle.TLabel", background=RED, foreground=WHITE,
                    font=(family, 26, "bold"))
    style.configure("DeviceMeta.TLabel", background=RED, foreground=WHITE,
                    font=(family, 9, "bold"))
    style.configure("Value.TFrame", background=GREEN)
    style.configure("Value.TLabel", background=GREEN, foreground=GREEN_INK,
                    font=(family, 17, "bold"))
    style.configure("ValueMeta.TLabel", background=GREEN, foreground=GREEN_INK,
                    font=(family, 9, "bold"))
    style.configure("CardName.TLabel", background=WELL, foreground=INK,
                    font=(family, 18, "bold"), wraplength=350)
    style.configure("CardDetail.TLabel", background=WELL, foreground=MUTED,
                    wraplength=350, padding=(0, 5))
    style.configure("CardPrice.TLabel", background=GREEN, foreground=GREEN_INK,
                    font=(family, 15, "bold"), padding=(12, 12))
    style.configure("Preview.TLabel", background="#E5E9ED", foreground=MUTED,
                    padding=14)
    style.configure("Empty.TLabel", background=WHITE, foreground=MUTED,
                    justify="center", padding=20)

    for name, background, foreground, border, active in (
        ("Primary.TButton", RED, WHITE, RED_DARK, RED_DARK),
        ("Secondary.TButton", WHITE, INK, BORDER, WELL),
        ("Danger.TButton", WHITE, RED_DARK, BORDER, RED_LIGHT),
    ):
        style.configure(name, background=background, foreground=foreground,
                        bordercolor=border, lightcolor=background, darkcolor=border,
                        focuscolor=BLUE, borderwidth=1, relief="flat",
                        padding=(15, 10), font=(family, 10, "bold"))
        style.map(name,
                  background=[("disabled", "#E3E6EA"), ("pressed", active),
                              ("active", active)],
                  foreground=[("disabled", "#626B76")],
                  bordercolor=[("focus", BLUE)])

    for name in ("TEntry", "TCombobox"):
        style.configure(name, fieldbackground=WHITE, background=WHITE,
                        foreground=INK, insertcolor=INK, bordercolor=BORDER,
                        lightcolor=BORDER, darkcolor=BORDER, borderwidth=1,
                        padding=(9, 8), selectbackground=RED, selectforeground=WHITE)
        style.map(name,
                  fieldbackground=[("disabled", WELL), ("readonly", WHITE)],
                  foreground=[("disabled", MUTED), ("readonly", INK)],
                  bordercolor=[("focus", BLUE)])
    style.configure("TCombobox", arrowcolor=RED_DARK)
    style.configure("Treeview", background=WHITE, fieldbackground=WHITE,
                    foreground=INK, rowheight=36, borderwidth=0, relief="flat")
    style.map("Treeview", background=[("selected", RED)],
              foreground=[("selected", WHITE)])
    style.configure("Treeview.Heading", background=INK, foreground=WHITE,
                    bordercolor=INK, lightcolor=INK, darkcolor=INK,
                    relief="flat", padding=(12, 11), font=(family, 10, "bold"))
    style.map("Treeview.Heading", background=[("active", RED_DARK)])
    style.configure("Vertical.TScrollbar", background=BORDER, troughcolor=WELL,
                    bordercolor=WELL, arrowcolor=INK, lightcolor=BORDER,
                    darkcolor=BORDER, borderwidth=0)
    style.map("Vertical.TScrollbar", background=[("active", "#B9C1CB")])
    return style


def device_header(parent):
    """Draw the reference's lens, indicator lights, and Poké Ball in Tk."""
    header = tk.Frame(parent, background=RED)
    header.columnconfigure(1, weight=1)
    lens = tk.Canvas(header, width=88, height=88, background=RED,
                     highlightthickness=0)
    lens.grid(row=0, column=0, rowspan=3, padx=(0, 18))
    lens.create_oval(3, 3, 81, 81, fill=INK, outline=INK)
    lens.create_oval(7, 7, 77, 77, fill=WHITE, outline=WHITE)
    lens.create_oval(13, 13, 71, 71, fill=BLUE, outline=INK, width=2)
    lens.create_oval(19, 17, 44, 42, fill="#91DCF7", outline="")
    lens.create_oval(25, 20, 36, 31, fill=WHITE, outline="")
    lights = tk.Canvas(header, width=100, height=19, background=RED,
                       highlightthickness=0)
    lights.grid(row=0, column=1, sticky="w")
    for x, color in ((0, "#F68A97"), (25, "#FFE388"), (50, "#91D7A7")):
        lights.create_oval(x + 1, 2, x + 12, 13, fill=color, outline=INK, width=1)
    ttk.Label(header, text="POKÉDEX", style="DeviceTitle.TLabel").grid(
        row=1, column=1, sticky="w")
    ttk.Label(header, text="C A R D   C O L L E C T I O N   M A N A G E R",
              style="DeviceMeta.TLabel").grid(row=2, column=1, sticky="w")
    ball = tk.Canvas(header, width=60, height=60, background=RED,
                     highlightthickness=0)
    ball.grid(row=0, column=2, rowspan=3, padx=(20, 2))
    ball.create_oval(4, 4, 56, 56, fill=WHITE, outline=INK, width=3)
    ball.create_arc(4, 4, 56, 56, start=0, extent=180, fill=RED_DARK,
                    outline=INK, width=3)
    ball.create_line(5, 30, 55, 30, fill=INK, width=4)
    ball.create_oval(20, 20, 40, 40, fill=WHITE, outline=INK, width=4)
    ball.create_oval(26, 26, 34, 34, fill=WELL, outline=BORDER)
    return header
