#!/usr/bin/env python3
"""Fisch desktop app (Tkinter) for searching and comparing rods.

Suggested architecture implemented:
- Indexer: refresh online data into a local JSON index.
- Local data: load condensed index for fast search/filter.
- UI: compare rods in a desktop interface.
"""

from __future__ import annotations

import re
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any, Callable

from rod_compare import DEFAULT_URL
from wiki_index import DEFAULT_INDEX_FILE, load_index, refresh_index

DISPLAY_COLUMNS = [
    "name",
    "lure_speed",
    "luck",
    "control",
    "resilience",
    "max_kg",
    "price",
    "stage",
    "level_requirement",
    "durability",
    "disturbance",
    "hunt_focus",
    "passive",
    "location",
    "source",
]

COLUMN_TITLES = {
    "name": "Rod",
    "lure_speed": "Lure",
    "luck": "Luck",
    "control": "Control",
    "resilience": "Resilience",
    "max_kg": "Max Kg",
    "price": "Price",
    "stage": "Stage",
    "level_requirement": "Level Req",
    "durability": "Durability",
    "disturbance": "Disturbance",
    "hunt_focus": "Hunt Focus",
    "passive": "Passive",
    "location": "Location",
    "source": "Source",
}

COMPARE_STATS = ["lure_speed", "luck", "control", "resilience", "max_kg", "price"]

LOCATION_AVERAGES = {
    "Mineshaft": {"avg_gold": 210.00, "avg_xp": 55.5},
    "Calm Zone": {"avg_gold": 450.00, "avg_xp": 120.0},
    "Meteorite Crater": {"avg_gold": 1200.00, "avg_xp": 450.0},
    "The Black Market": {"avg_gold": 900.50, "avg_xp": 300.0},
    "Frigid Cavern": {"avg_gold": 580.00, "avg_xp": 190.5},
    "Overgrowth Caves": {"avg_gold": 1350.75, "avg_xp": 550.0},
    "The Abyss": {"avg_gold": 3900.00, "avg_xp": 1800.0},
    "Statue of Sovereignty": {"avg_gold": 850.00, "avg_xp": 280.5},
    "Tidefall Ruins": {"avg_gold": 5800.00, "avg_xp": 2400.0},
    "The Grotto": {"avg_gold": 3400.50, "avg_xp": 1450.0},
    "Sovereign's Reach": {"avg_gold": 4100.00, "avg_xp": 1700.5},
    "Great Reef": {"avg_gold": 1100.00, "avg_xp": 410.0},
    "Moosewood": {"avg_gold": 120.50, "avg_xp": 35.0},
    "Roslit Bay": {"avg_gold": 315.20, "avg_xp": 85.5},
    "Snowcap Island": {"avg_gold": 410.75, "avg_xp": 105.0},
    "Terrapin Island": {"avg_gold": 550.00, "avg_xp": 140.5},
    "Mushgrove Swamp": {"avg_gold": 620.30, "avg_xp": 155.0},
    "Ocean": {"avg_gold": 400.00, "avg_xp": 95.0},
    "Boreal Pines": {"avg_gold": 850.00, "avg_xp": 320.0},
    "Forsaken Shores": {"avg_gold": 1150.25, "avg_xp": 420.0},
    "Sunstone Island": {"avg_gold": 1450.75, "avg_xp": 850.5},
    "Volcanic Vents": {"avg_gold": 1850.75, "avg_xp": 780.0},
    "Desolate Deep": {"avg_gold": 2100.50, "avg_xp": 950.0},
    "Vertigo": {"avg_gold": 2300.00, "avg_xp": 1050.0},
    "Castaway Cliffs": {"avg_gold": 3200.50, "avg_xp": 1350.0},
    "The Depths": {"avg_gold": 3600.00, "avg_xp": 1600.5},
    "Luminescent Cavern": {"avg_gold": 4200.75, "avg_xp": 2600.0},
    "Scoria's Reach": {"avg_gold": 4800.00, "avg_xp": 1950.5},
    "Tidefall": {"avg_gold": 5500.50, "avg_xp": 2100.0},
    "Apollo's Song of Light": {"avg_gold": 6500.00, "avg_xp": 2900.5},
    "Ancient Isle": {"avg_gold": 1750.00, "avg_xp": 700.0},
    "Cursed Isle": {"avg_gold": 2800.50, "avg_xp": 1250.0},
    "Ancient Archives": {"avg_gold": 3100.00, "avg_xp": 1400.0},
    "Lost Jungle": {"avg_gold": 3800.25, "avg_xp": 1750.5},
    "Toxic Grove": {"avg_gold": 4100.00, "avg_xp": 1850.0},
    "Atlantis": {"avg_gold": 5100.50, "avg_xp": 2350.0},
    "Crystal Cove": {"avg_gold": 6200.00, "avg_xp": 2750.0},
    "Moosewood Docks": {"avg_gold": 110.00, "avg_xp": 30.0},
    "Moosewood Pond": {"avg_gold": 135.50, "avg_xp": 40.5},
    "The Arch": {"avg_gold": 150.00, "avg_xp": 45.0},
    "Roslit Volcano": {"avg_gold": 1950.00, "avg_xp": 810.0},
    "Roslit Coral Reef": {"avg_gold": 380.00, "avg_xp": 110.5},
    "Roslit Deep": {"avg_gold": 450.50, "avg_xp": 135.0},
    "Snowcap Cave": {"avg_gold": 475.00, "avg_xp": 125.0},
    "Frozen Lake": {"avg_gold": 440.00, "avg_xp": 115.5},
    "Glacier Edge": {"avg_gold": 490.50, "avg_xp": 140.0},
    "Swamp Depths": {"avg_gold": 680.00, "avg_xp": 180.0},
    "Glowing Mushroom Area": {"avg_gold": 710.25, "avg_xp": 205.5},
    "The Rot": {"avg_gold": 800.00, "avg_xp": 240.0},
    "Boreal River": {"avg_gold": 880.50, "avg_xp": 335.0},
    "Boreal Waterfall": {"avg_gold": 950.00, "avg_xp": 375.5},
    "Open Ocean": {"avg_gold": 350.00, "avg_xp": 85.0},
    "Shallow Waters": {"avg_gold": 280.00, "avg_xp": 65.0},
    "Deep Ocean": {"avg_gold": 650.50, "avg_xp": 190.0},
    "Shipwreck": {"avg_gold": 950.00, "avg_xp": 280.5},
    "Sunstone Cavern": {"avg_gold": 1550.00, "avg_xp": 900.0},
    "Desolate Pocket": {"avg_gold": 2250.00, "avg_xp": 1050.0},
    "Brine Pool": {"avg_gold": 2600.00, "avg_xp": 1150.5},
    "Abyssal Trench": {"avg_gold": 2900.50, "avg_xp": 1280.0},
    "The Drop": {"avg_gold": 2100.00, "avg_xp": 980.0},
    "Vertigo Pit": {"avg_gold": 2450.50, "avg_xp": 1120.5},
    "Distortion Zone": {"avg_gold": 2650.00, "avg_xp": 1200.0},
    "The Labyrinth": {"avg_gold": 3750.00, "avg_xp": 1680.0},
    "Whispering Caves": {"avg_gold": 3900.25, "avg_xp": 1750.5},
    "The Core": {"avg_gold": 4150.00, "avg_xp": 1900.0},
    "Keeper's Altar": {"avg_gold": 1600.00, "avg_xp": 880.0},
    "Coral Bastion": {"avg_gold": 4300.50, "avg_xp": 1850.0},
    "Cryogenic Canal": {"avg_gold": 4500.00, "avg_xp": 1980.5},
    "Cultist Lair": {"avg_gold": 3200.00, "avg_xp": 1450.0},
    "Everturn Forest": {"avg_gold": 1850.00, "avg_xp": 720.5},
    "Glacial Grotto": {"avg_gold": 1350.00, "avg_xp": 480.0},
    "Nectar Den": {"avg_gold": 1800.00, "avg_xp": 650.5},
    "Veil of Forsaken": {"avg_gold": 1250.00, "avg_xp": 450.0},
    "Olympian Fissure": {"avg_gold": 7200.00, "avg_xp": 3200.0},
    "Crimson Cavern": {"avg_gold": 4650.50, "avg_xp": 2150.0},
    "Grand Reef": {"avg_gold": 1200.50, "avg_xp": 480.0},
    "Living Garden": {"avg_gold": 2200.00, "avg_xp": 950.0},
    "Northern Expedition": {"avg_gold": 3100.50, "avg_xp": 1400.0},
    "Mariana's Veil": {"avg_gold": 4500.00, "avg_xp": 2100.5},
    "Bellona's Frenzy of War": {"avg_gold": 5800.75, "avg_xp": 2850.0},
    "Easter Cove": {"avg_gold": 950.00, "avg_xp": 350.0},
    "Carrot Garden": {"avg_gold": 800.00, "avg_xp": 8500.0},
    "The Sanctum": {"avg_gold": 2400.50, "avg_xp": 1250.0},
    "Crowned Ruins": {"avg_gold": 5200.00, "avg_xp": 2200.0},
    "Collapsed Ruins": {"avg_gold": 4100.25, "avg_xp": 1850.0},
    "Snowburrow": {"avg_gold": 650.00, "avg_xp": 210.5},
    "Scoria Reach Mine": {"avg_gold": 4900.00, "avg_xp": 2100.0},
    "Chasm Mineshaft": {"avg_gold": 3800.50, "avg_xp": 1600.0},
    "Northern Expedition Summit": {"avg_gold": 4400.00, "avg_xp": 1950.0},
    "Poseidon Trail Room": {"avg_gold": 6100.25, "avg_xp": 2750.5},
    "Blue Moon Bunker": {"avg_gold": 7500.00, "avg_xp": 3500.0},
    "Music Venue (Crystal Cove)": {"avg_gold": 6400.50, "avg_xp": 2800.0},
    "The Underworld": {"avg_gold": 6900.00, "avg_xp": 3100.5},
}

XP_ENCHANT_MULTIPLIERS = {
    "None": 1.0,
    "Clever (+15%)": 1.15,
    "Insight (+25%)": 1.25,
    "Wise (+35%)": 1.35,
}

MUTATION_MULTIPLIERS = {
    "shiny": 1.20,
    "sparkling": 1.55,
    "mythic": 2.25,
}

GOLD_ENCHANT_MULTIPLIERS = {
    "None": 1.0,
    "Greedy (+10%)": 1.10,
    "Prosperous (+20%)": 1.20,
    "Opulent (+35%)": 1.35,
}

MUTATION_PROFILES = {
    "None": [{"name": "No mutation", "chance": 1.0, "multiplier": 1.0}],
    "Balanced": [
        {"name": "No mutation", "chance": 0.65, "multiplier": 1.0},
        {"name": "Shiny", "chance": 0.20, "multiplier": 1.20},
        {"name": "Sparkling", "chance": 0.10, "multiplier": 1.55},
        {"name": "Mythic", "chance": 0.05, "multiplier": 2.25},
    ],
    "High-Risk": [
        {"name": "No mutation", "chance": 0.55, "multiplier": 1.0},
        {"name": "Shiny", "chance": 0.20, "multiplier": 1.20},
        {"name": "Sparkling", "chance": 0.15, "multiplier": 1.55},
        {"name": "Mythic", "chance": 0.10, "multiplier": 2.25},
    ],
}


class FischDesktopApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Fisch Rod Explorer")
        self.root.geometry("1250x760")
        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")

        self.index_path_var = tk.StringVar(value=str(Path(DEFAULT_INDEX_FILE).resolve()))
        self.wiki_url_var = tk.StringVar(value=DEFAULT_URL)
        self.search_var = tk.StringVar(value="")
        self.scan_passives_var = tk.BooleanVar(value=True)
        self.dark_mode_var = tk.BooleanVar(value=False)

        self.rods: list[dict[str, Any]] = []
        self.filtered_rods: list[dict[str, Any]] = []
        self.location_names = sorted(LOCATION_AVERAGES.keys())
        self._xp_rod_options = ["No xp bonus on rod"]
        self._gold_rod_options: list[str] = []

        self.xp_location_var = tk.StringVar(value=self.location_names[0] if self.location_names else "")
        self.xp_rod_var = tk.StringVar(value="No xp bonus on rod")
        self.xp_enchant_var = tk.StringVar(value="None")
        self.xp_result_var = tk.StringVar(value="Adjusted XP: -")

        self.gold_location_var = tk.StringVar(value=self.location_names[0] if self.location_names else "")
        self.gold_rod_var = tk.StringVar(value="")
        self.gold_enchant_var = tk.StringVar(value="None")
        self.gold_mutation_profile_var = tk.StringVar(value="Balanced")
        self.gold_result_var = tk.StringVar(value="Adjusted Gold: -")

        self.max_compare_slots = 6
        self.compare_choice_vars = [tk.StringVar(value="") for _ in range(self.max_compare_slots)]
        self.compare_combos: list[ttk.Combobox] = []
        self.compare_labels: list[ttk.Label] = []
        self.visible_compare_slots = 2
        self._default_passive_width = 200
        self._sort_state: dict[str, bool] = {}
        self._passive_popup: tk.Toplevel | None = None
        self._compare_all_names: list[str] = []
        self._xp_avg_sort_ascending = True
        self._gold_avg_sort_ascending = True

        self._build_ui()
        self.search_var.trace_add("write", lambda *_: self.apply_search_filter())

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True)

        rods_tab = ttk.Frame(notebook)
        xp_tab = ttk.Frame(notebook)
        gold_tab = ttk.Frame(notebook)
        notebook.add(rods_tab, text="Rods")
        notebook.add(xp_tab, text="XP")
        notebook.add(gold_tab, text="Gold")
        self._build_resource_tab(xp_tab, mode="xp")
        self._build_resource_tab(gold_tab, mode="gold")

        top = ttk.Frame(rods_tab, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Wiki URL:").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(top, textvariable=self.wiki_url_var, width=65).grid(row=0, column=1, sticky="we", padx=4, pady=4)

        ttk.Label(top, text="Index JSON:").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(top, textvariable=self.index_path_var, width=65).grid(row=1, column=1, sticky="we", padx=4, pady=4)

        ttk.Checkbutton(
            top,
            text="Scan individual rod pages for passives (online)",
            variable=self.scan_passives_var,
        ).grid(row=0, column=2, sticky="w", padx=6, pady=4)

        ttk.Button(top, text="Refresh Index From Wiki", command=self.refresh_from_wiki).grid(
            row=1, column=2, sticky="we", padx=6, pady=4
        )
        ttk.Button(top, text="Load Local Index", command=self.load_local_index).grid(
            row=1, column=3, sticky="we", padx=6, pady=4
        )
        self.dark_mode_button = ttk.Button(top, text="Enable Dark Mode", command=self.toggle_dark_mode)
        self.dark_mode_button.grid(row=2, column=3, sticky="we", padx=6, pady=4)

        top.columnconfigure(1, weight=1)

        middle = ttk.Frame(rods_tab, padding=(10, 0, 10, 10))
        middle.pack(fill="both", expand=True)

        search_row = ttk.Frame(middle)
        search_row.pack(fill="x", pady=(0, 8))
        ttk.Label(search_row, text="Search:").pack(side="left")
        ttk.Entry(search_row, textvariable=self.search_var, width=40).pack(side="left", padx=8)
        ttk.Label(search_row, text="(name, location, source, passive)").pack(side="left")

        self.tree = ttk.Treeview(middle, columns=DISPLAY_COLUMNS, show="headings", height=16)
        for col in DISPLAY_COLUMNS:
            sortable = col not in {"passive", "location", "source"}
            self.tree.heading(
                col,
                text=COLUMN_TITLES[col],
                command=(lambda c=col: self.sort_by_column(c)) if sortable else "",
            )
            width = 85
            if col == "name":
                width = 135
            elif col == "passive":
                width = self._default_passive_width
            elif col == "location":
                width = 110
            elif col == "durability":
                width = 150
            elif col == "hunt_focus":
                width = 130
            elif col == "source":
                width = 95
            self.tree.column(col, width=width, stretch=True, anchor="w")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Button-3>", self._on_tree_right_click)
        self.tree.bind("<ButtonRelease-1>", self._on_tree_left_click)
        self.tree.tag_configure("odd", background="#a4b4db", foreground="black")
        self.tree.tag_configure("even", background="white", foreground="black")
        self.tree.tag_configure("limited_location", foreground="red")

        scroll_y = ttk.Scrollbar(self.tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side="right", fill="y")

        compare_box = ttk.LabelFrame(rods_tab, text="Compare Rods", padding=10)
        compare_box.pack(fill="x", padx=10, pady=(0, 10))

        for i in range(self.max_compare_slots):
            label = ttk.Label(compare_box, text=f"Compare Slot {i + 1}:")
            label.grid(row=i, column=0, sticky="w", padx=4, pady=2)
            combo = ttk.Combobox(compare_box, textvariable=self.compare_choice_vars[i], width=45, state="normal")
            combo.grid(row=i, column=1, sticky="we", padx=4, pady=2)
            combo.bind("<KeyRelease>", lambda event, idx=i: self._filter_compare_options(idx))
            combo.bind("<<ComboboxSelected>>", lambda event, idx=i: self._finalize_compare_selection(idx))
            if i >= self.visible_compare_slots:
                combo.grid_remove()
                label.grid_remove()
            self.compare_labels.append(label)
            self.compare_combos.append(combo)

        controls_row = self.max_compare_slots
        ttk.Button(compare_box, text="Compare", command=self.compare_selected).grid(row=controls_row, column=0, padx=4, pady=6, sticky="w")
        ttk.Button(compare_box, text="Reset Slots", command=self.reset_compare_slots).grid(row=controls_row, column=1, padx=4, pady=6, sticky="w")

        self.compare_text = tk.Text(compare_box, height=12, wrap="word")
        self.compare_text.grid(row=controls_row + 1, column=0, columnspan=2, sticky="we", padx=4, pady=(8, 4))
        self.compare_text.tag_configure("best_stat", foreground="green")
        self.compare_text.tag_configure("overall_best", foreground="blue")
        self.compare_text.tag_configure("category", font=("TkDefaultFont", 9, "bold"))
        self.compare_text.tag_configure("rod_0", foreground="purple")
        self.compare_text.tag_configure("rod_1", foreground="orange")
        self.compare_text.tag_configure("rod_2", foreground="teal")
        self.compare_text.tag_configure("rod_3", foreground="brown")
        self.compare_text.tag_configure("rod_4", foreground="magenta")
        self.compare_text.tag_configure("rod_5", foreground="navy")

        compare_box.columnconfigure(1, weight=1)

        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Add to compare", command=self.add_selected_row_to_compare)
        self._apply_theme()

    def _build_resource_tab(self, parent: ttk.Frame, mode: str) -> None:
        container = ttk.Frame(parent, padding=10)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)

        table_frame = ttk.LabelFrame(container, text="Location Averages", padding=8)
        table_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        calculator_frame = ttk.LabelFrame(container, text="Calculator", padding=12)
        calculator_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        columns = ("location", "average")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=24)
        tree.heading("location", text="Location")
        if mode == "xp":
            tree.heading("average", text="Average XP ▲", command=lambda: self._sort_average_tree("xp"))
        else:
            tree.heading("average", text="Average Gold ▲", command=lambda: self._sort_average_tree("gold"))
        tree.column("location", width=230, stretch=True, anchor="w")
        tree.column("average", width=120, stretch=False, anchor="e")
        tree.pack(fill="both", expand=True)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        for location in self.location_names:
            avg_key = "avg_xp" if mode == "xp" else "avg_gold"
            avg_val = LOCATION_AVERAGES[location][avg_key]
            tree.insert("", "end", values=(location, f"{avg_val:,.2f}"))

        if mode == "xp":
            self.xp_locations_tree = tree
            self._build_xp_calculator(calculator_frame)
        else:
            self.gold_locations_tree = tree
            self._build_gold_calculator(calculator_frame)

    def _build_xp_calculator(self, frame: ttk.LabelFrame) -> None:
        ttk.Label(frame, text="Rod").grid(row=0, column=0, sticky="w", pady=4)
        self.xp_rod_combo = ttk.Combobox(frame, textvariable=self.xp_rod_var, values=self._xp_rod_options, state="normal", width=30)
        self.xp_rod_combo.grid(row=1, column=0, sticky="we", pady=(0, 8))
        ttk.Label(frame, text="Location").grid(row=0, column=1, sticky="w", padx=(12, 0), pady=4)
        self.xp_location_combo = ttk.Combobox(
            frame, textvariable=self.xp_location_var, values=self.location_names, state="normal", width=30
        )
        self.xp_location_combo.grid(row=1, column=1, sticky="we", padx=(12, 0), pady=(0, 8))

        ttk.Label(frame, text="Enchant").grid(row=2, column=0, sticky="w", pady=4)
        self.xp_enchant_combo = ttk.Combobox(
            frame, textvariable=self.xp_enchant_var, values=list(XP_ENCHANT_MULTIPLIERS.keys()), state="normal", width=30
        )
        self.xp_enchant_combo.grid(row=3, column=0, sticky="we", pady=(0, 8))
        ttk.Button(frame, text="Calculate XP", command=self.calculate_xp).grid(row=3, column=1, sticky="we", padx=(12, 0), pady=(0, 8))
        ttk.Label(frame, textvariable=self.xp_result_var, font=("TkDefaultFont", 10, "bold")).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )

        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        self.xp_location_combo.bind("<<ComboboxSelected>>", lambda *_: self.calculate_xp())
        self.xp_rod_combo.bind("<<ComboboxSelected>>", lambda *_: self.calculate_xp())
        self.xp_enchant_combo.bind("<<ComboboxSelected>>", lambda *_: self.calculate_xp())
        self._bind_filtering(self.xp_rod_combo, lambda: self._xp_rod_options, self.calculate_xp)
        self._bind_filtering(self.xp_location_combo, self.location_names, self.calculate_xp)
        self._bind_filtering(self.xp_enchant_combo, list(XP_ENCHANT_MULTIPLIERS.keys()), self.calculate_xp)
        self.calculate_xp()

    def _build_gold_calculator(self, frame: ttk.LabelFrame) -> None:
        ttk.Label(frame, text="Rod").grid(row=0, column=0, sticky="w", pady=4)
        self.gold_rod_combo = ttk.Combobox(
            frame, textvariable=self.gold_rod_var, values=self._gold_rod_options, state="normal", width=30
        )
        self.gold_rod_combo.grid(row=1, column=0, sticky="we", pady=(0, 8))
        ttk.Label(frame, text="Location").grid(row=0, column=1, sticky="w", padx=(12, 0), pady=4)
        self.gold_location_combo = ttk.Combobox(
            frame, textvariable=self.gold_location_var, values=self.location_names, state="normal", width=30
        )
        self.gold_location_combo.grid(row=1, column=1, sticky="we", padx=(12, 0), pady=(0, 8))

        ttk.Label(frame, text="Enchant").grid(row=2, column=0, sticky="w", pady=4)
        self.gold_enchant_combo = ttk.Combobox(
            frame,
            textvariable=self.gold_enchant_var,
            values=list(GOLD_ENCHANT_MULTIPLIERS.keys()),
            state="normal",
            width=30,
        )
        self.gold_enchant_combo.grid(row=3, column=0, sticky="we", pady=(0, 8))

        ttk.Label(frame, text="Mutation profile").grid(row=4, column=0, sticky="w", pady=4)
        self.gold_mutation_combo = ttk.Combobox(
            frame,
            textvariable=self.gold_mutation_profile_var,
            values=list(MUTATION_PROFILES.keys()),
            state="normal",
            width=30,
        )
        self.gold_mutation_combo.grid(row=5, column=0, sticky="we", pady=(0, 8))
        ttk.Button(frame, text="Calculate Gold", command=self.calculate_gold).grid(row=5, column=1, sticky="we", padx=(12, 0), pady=(0, 8))
        ttk.Label(frame, textvariable=self.gold_result_var, font=("TkDefaultFont", 10, "bold")).grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )

        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        self.gold_location_combo.bind("<<ComboboxSelected>>", lambda *_: self.calculate_gold())
        self.gold_rod_combo.bind("<<ComboboxSelected>>", lambda *_: self.calculate_gold())
        self.gold_enchant_combo.bind("<<ComboboxSelected>>", lambda *_: self.calculate_gold())
        self.gold_mutation_combo.bind("<<ComboboxSelected>>", lambda *_: self.calculate_gold())
        self._bind_filtering(self.gold_rod_combo, lambda: self._gold_rod_options, self.calculate_gold)
        self._bind_filtering(self.gold_location_combo, self.location_names, self.calculate_gold)
        self._bind_filtering(self.gold_enchant_combo, list(GOLD_ENCHANT_MULTIPLIERS.keys()), self.calculate_gold)
        self._bind_filtering(self.gold_mutation_combo, list(MUTATION_PROFILES.keys()), self.calculate_gold)
        self.calculate_gold()

    def refresh_from_wiki(self) -> None:
        try:
            rods = refresh_index(
                wiki_url=self.wiki_url_var.get().strip(),
                output_path=self.index_path_var.get().strip(),
                scan_passives=self.scan_passives_var.get(),
            )
        except Exception as exc:  # user-facing desktop message
            messagebox.showerror("Refresh failed", str(exc))
            return

        self.rods = rods
        self.apply_search_filter()
        messagebox.showinfo("Done", f"Indexed {len(self.rods)} rods to {self.index_path_var.get().strip()}")

    def load_local_index(self) -> None:
        try:
            self.rods = load_index(self.index_path_var.get().strip())
        except Exception as exc:
            messagebox.showerror("Load failed", str(exc))
            return
        self.apply_search_filter()

    def toggle_dark_mode(self) -> None:
        self.dark_mode_var.set(not self.dark_mode_var.get())
        self.dark_mode_button.configure(text="Disable Dark Mode" if self.dark_mode_var.get() else "Enable Dark Mode")
        self._apply_theme()

    def _apply_theme(self) -> None:
        self._hide_passive_popup()
        if self.dark_mode_var.get():
            charcoal = "#2b2b2b"
            light_text = "#f5f5f5"
            muted = "#3a3a3a"
            self.compare_text.configure(bg=charcoal, fg=light_text, insertbackground=light_text)
            self.tree.tag_configure("odd", background="#42507a", foreground="white")
            self.tree.tag_configure("even", background="#232323", foreground="white")
            self.style.configure("TFrame", background=charcoal)
            self.style.configure("TLabel", background=charcoal, foreground=light_text)
            self.style.configure("TLabelframe", background=charcoal, bordercolor="#42507a")
            self.style.configure("TLabelframe.Label", background=charcoal, foreground=light_text)
            self.style.configure("TButton", background=muted, foreground=light_text)
            self.style.map("TButton", background=[("active", "#4a4a4a")], foreground=[("active", light_text)])
            self.style.configure("TCheckbutton", background=charcoal, foreground=light_text)
            self.style.configure("TEntry", fieldbackground="#1f1f1f", foreground=light_text)
            self.style.configure("TCombobox", fieldbackground="#1f1f1f", foreground=light_text, background=muted)
            self.style.map("TCombobox", fieldbackground=[("readonly", "#1f1f1f")], foreground=[("readonly", light_text)])
            self.style.configure("Treeview", background="#232323", foreground=light_text, fieldbackground="#232323")
            self.style.configure("Treeview.Heading", background=muted, foreground=light_text)
            self.style.map("Treeview.Heading", background=[("active", "#42507a")], foreground=[("active", light_text)])
            self.root.option_add("*TCombobox*Listbox*Background", "#1f1f1f")
            self.root.option_add("*TCombobox*Listbox*Foreground", light_text)
            self.root.option_add("*TCombobox*Listbox*selectBackground", "#42507a")
            self.root.option_add("*TCombobox*Listbox*selectForeground", light_text)
            self.root.configure(bg=charcoal)
            self.context_menu.configure(background=charcoal, foreground=light_text, activebackground="#4a4a4a", activeforeground=light_text)
        else:
            self.compare_text.configure(bg="white", fg="black", insertbackground="black")
            self.tree.tag_configure("odd", background="#a4b4db", foreground="black")
            self.tree.tag_configure("even", background="white", foreground="black")
            self.style.configure("TFrame", background="SystemButtonFace")
            self.style.configure("TLabel", background="SystemButtonFace", foreground="black")
            self.style.configure("TLabelframe", background="SystemButtonFace")
            self.style.configure("TLabelframe.Label", background="SystemButtonFace", foreground="black")
            self.style.configure("TButton", background="SystemButtonFace", foreground="black")
            self.style.map("TButton", background=[("active", "#e6e6e6")], foreground=[("active", "black")])
            self.style.configure("TCheckbutton", background="SystemButtonFace", foreground="black")
            self.style.configure("TEntry", fieldbackground="white", foreground="black")
            self.style.configure("TCombobox", fieldbackground="white", foreground="black", background="SystemButtonFace")
            self.style.map("TCombobox", fieldbackground=[("readonly", "white")], foreground=[("readonly", "black")])
            self.style.configure("Treeview", background="white", foreground="black", fieldbackground="white")
            self.style.configure("Treeview.Heading", background="#e8e8e8", foreground="black")
            self.style.map("Treeview.Heading", background=[("active", "#a4b4db")], foreground=[("active", "black")])
            self.root.option_add("*TCombobox*Listbox*Background", "white")
            self.root.option_add("*TCombobox*Listbox*Foreground", "black")
            self.root.option_add("*TCombobox*Listbox*selectBackground", "#a4b4db")
            self.root.option_add("*TCombobox*Listbox*selectForeground", "black")
            self.root.configure(bg="SystemButtonFace")
            self.context_menu.configure(background="SystemButtonFace", foreground="black", activebackground="#d9d9d9", activeforeground="black")

    def apply_search_filter(self) -> None:
        q = self.search_var.get().strip().lower()
        if not q:
            self.filtered_rods = list(self.rods)
        else:
            self.filtered_rods = [
                rod
                for rod in self.rods
                if q in (rod.get("name") or "").lower()
                or q in (rod.get("location") or "").lower()
                or q in (rod.get("source") or "").lower()
                or q in (rod.get("stage") or "").lower()
                or q in (rod.get("level_requirement") or "").lower()
                or q in (rod.get("durability") or "").lower()
                or q in (rod.get("disturbance") or "").lower()
                or q in (rod.get("hunt_focus") or "").lower()
                or q in (rod.get("passive") or "").lower()
            ]

        self._render_tree()
        self._update_compare_choices()
        self._update_calculator_rod_choices()

    def _render_tree(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        for idx, rod in enumerate(self.filtered_rods):
            row = [self._display_cell(rod, col) for col in DISPLAY_COLUMNS]
            tags = ["odd" if idx % 2 == 0 else "even"]
            location = (rod.get("location") or "").lower()
            if "limited" in location:
                tags.append("limited_location")
            self.tree.insert("", "end", values=row, tags=tuple(tags))

    def sort_by_column(self, column: str) -> None:
        ascending = self._sort_state.get(column, True)
        self._sort_state[column] = not ascending

        def key_fn(rod: dict[str, Any]):
            value = rod.get(column)
            if isinstance(value, (int, float)):
                return (0, float(value))
            if isinstance(value, str):
                num = self._num(value)
                if num != 0.0 or value.strip() in {"0", "0.0"}:
                    return (0, num)
                return (1, value.lower())
            return (2, "")

        self.filtered_rods.sort(key=key_fn, reverse=not ascending)
        self._render_tree()

    def _filter_compare_options(self, index: int) -> None:
        query = self.compare_choice_vars[index].get().strip().lower()
        if not query:
            self.compare_combos[index]["values"] = self._compare_all_names
            return
        filtered = [name for name in self._compare_all_names if query in name.lower()]
        self.compare_combos[index]["values"] = filtered

    def _finalize_compare_selection(self, index: int) -> None:
        chosen = self.compare_choice_vars[index].get().strip()
        if chosen not in self._compare_all_names:
            self.compare_choice_vars[index].set("")
        self.compare_combos[index]["values"] = self._compare_all_names

    def _update_compare_choices(self) -> None:
        names = [rod.get("name", "") for rod in self.filtered_rods]
        self._compare_all_names = names[:]
        for combo in self.compare_combos:
            combo["values"] = names

        if not names:
            for var in self.compare_choice_vars:
                var.set("")
            return

        for i in range(self.visible_compare_slots):
            current = self.compare_choice_vars[i].get()
            if current not in names:
                self.compare_choice_vars[i].set("")

    def compare_selected(self) -> None:
        selected_names = [var.get() for var in self.compare_choice_vars[: self.visible_compare_slots] if var.get()]
        unique_names = []
        for name in selected_names:
            if name not in unique_names:
                unique_names.append(name)

        selected_rods = [self._find_rod(name) for name in unique_names]
        selected_rods = [rod for rod in selected_rods if rod is not None]
        if len(selected_rods) < 2:
            messagebox.showwarning("Missing selection", "Please select at least two rods to compare.")
            return

        names_csv = ", ".join(rod["name"] for rod in selected_rods)
        self.compare_text.delete("1.0", "end")
        self.compare_text.insert("end", f"Comparing: {names_csv}\n\n")

        score = {rod["name"]: 0 for rod in selected_rods}

        for stat in COMPARE_STATS:
            values = [
                (rod["name"], self._num(rod.get(stat)) + self._passive_stat_bonus(rod, stat))
                for rod in selected_rods
            ]
            best_value = max(v for _, v in values)
            winners = [name for name, value in values if value == best_value]
            for winner in winners:
                score[winner] += 1

            winner_text = "Tie" if len(winners) != 1 else winners[0]
            self.compare_text.insert("end", f"{COLUMN_TITLES[stat]}: ", ("category",))
            for idx, (_, value) in enumerate(values):
                rod_tag = f"rod_{idx % self.max_compare_slots}"
                self.compare_text.insert("end", f"{value:g}", (rod_tag,))
                if idx != len(values) - 1:
                    self.compare_text.insert("end", " | ")
            line_start = self.compare_text.index("end-1c")
            line = f" | Best: {winner_text}\n"
            self.compare_text.insert("end", line)

            if len(winners) == 1:
                offset = line.rfind(winner_text)
                if offset >= 0:
                    tag_start = f"{line_start}+{offset}c"
                    tag_end = f"{tag_start}+{len(winner_text)}c"
                    self.compare_text.tag_add("best_stat", tag_start, tag_end)

        best_score = max(score.values())
        overall = [name for name, val in score.items() if val == best_score]
        overall_text = ", ".join(overall)
        line_start = self.compare_text.index("end-1c")
        summary = f"\nOverall best: {overall_text} (wins: {best_score})\n"
        self.compare_text.insert("end", summary)
        offset = summary.rfind(overall_text)
        if offset >= 0:
            tag_start = f"{line_start}+{offset}c"
            tag_end = f"{tag_start}+{len(overall_text)}c"
            self.compare_text.tag_add("overall_best", tag_start, tag_end)

    def reset_compare_slots(self) -> None:
        self.visible_compare_slots = 2
        for i, combo in enumerate(self.compare_combos):
            label = self._get_compare_label_widget(i)
            if i < self.visible_compare_slots:
                combo.grid()
                label.grid()
            else:
                combo.grid_remove()
                label.grid_remove()
            if i >= self.visible_compare_slots:
                self.compare_choice_vars[i].set("")
        self._update_compare_choices()

    def _get_compare_label_widget(self, index: int):
        return self.compare_labels[index]

    def _on_tree_right_click(self, event) -> None:
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return
        self.tree.selection_set(row_id)
        self.context_menu.post(event.x_root, event.y_root)

    def _on_tree_left_click(self, event) -> None:
        column_id = self.tree.identify_column(event.x)
        if not column_id or column_id == "#0":
            self._hide_passive_popup()
            return
        column_index = int(column_id[1:]) - 1
        if column_index < 0 or column_index >= len(DISPLAY_COLUMNS):
            self._hide_passive_popup()
            return

        clicked_col = DISPLAY_COLUMNS[column_index]
        if clicked_col != "passive":
            self._hide_passive_popup()
            return

        row_id = self.tree.identify_row(event.y)
        if not row_id:
            self._hide_passive_popup()
            return
        values = self.tree.item(row_id, "values")
        if not values:
            self._hide_passive_popup()
            return
        passive_value = str(values[column_index]) if column_index < len(values) else ""
        if not passive_value or passive_value == "-":
            self._hide_passive_popup()
            return
        self._show_passive_popup(event.x_root, event.y_root, passive_value)

    def _show_passive_popup(self, x_root: int, y_root: int, text: str) -> None:
        self._hide_passive_popup()
        popup = tk.Toplevel(self.root)
        popup.wm_overrideredirect(True)
        popup.attributes("-topmost", True)
        bg = "#2b2b2b" if self.dark_mode_var.get() else "white"
        fg = "#f5f5f5" if self.dark_mode_var.get() else "black"
        border = "#42507a" if self.dark_mode_var.get() else "#a4b4db"
        popup.configure(bg=border)

        container = tk.Frame(popup, bg=bg, padx=8, pady=6)
        container.pack(padx=1, pady=1)
        label = tk.Label(
            container,
            text=text,
            bg=bg,
            fg=fg,
            justify="left",
            anchor="w",
            wraplength=640,
        )
        label.pack(fill="both", expand=True)
        popup.update_idletasks()
        popup.geometry(f"+{x_root + 10}+{y_root + 10}")
        popup.bind("<FocusOut>", lambda *_: self._hide_passive_popup())
        popup.bind("<Escape>", lambda *_: self._hide_passive_popup())
        popup.focus_force()
        self._passive_popup = popup

    def _hide_passive_popup(self) -> None:
        if self._passive_popup and self._passive_popup.winfo_exists():
            self._passive_popup.destroy()
        self._passive_popup = None

    def add_selected_row_to_compare(self) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0], "values")
        if not values:
            return
        rod_name = values[0]

        for i in range(self.visible_compare_slots):
            if self.compare_choice_vars[i].get() == rod_name:
                return

        target = None
        for i in range(self.visible_compare_slots):
            if not self.compare_choice_vars[i].get():
                target = i
                break
        if target is None:
            if self.visible_compare_slots < self.max_compare_slots:
                target = self.visible_compare_slots
                self.visible_compare_slots += 1
                self.compare_combos[target].grid()
                self._get_compare_label_widget(target).grid()
            else:
                target = self.max_compare_slots - 1

        self.compare_choice_vars[target].set(rod_name)

    def _find_rod(self, name: str) -> dict[str, Any] | None:
        for rod in self.rods:
            if rod.get("name") == name:
                return rod
        return None

    @staticmethod
    def _fmt(value: Any) -> str:
        if value is None or value == "":
            return "-"
        if isinstance(value, float) and value == float("inf"):
            return "inf."
        return str(value)

    def _display_cell(self, rod: dict[str, Any], col: str) -> str:
        if col == "price":
            price = rod.get("price")
            if price is None and "quest" in (rod.get("source") or "").lower():
                return "quest reward"
            if isinstance(price, (int, float)):
                if price >= 1_000_000:
                    mil = price / 1_000_000
                    return f"{mil:g} mil"
                return f"{int(price):,}"
        if col == "max_kg":
            max_kg = rod.get("max_kg")
            if isinstance(max_kg, (int, float)) and max_kg != float("inf"):
                return f"{int(max_kg):,}"
        return self._fmt(rod.get(col))

    @staticmethod
    def _num(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _bind_filtering(self, combo: ttk.Combobox, options: list[str] | Callable[[], list[str]], on_change) -> None:
        def resolve_options() -> list[str]:
            return options() if callable(options) else options

        def filter_values(*_) -> None:
            query = combo.get().strip().lower()
            all_options = resolve_options()
            values = all_options if not query else [opt for opt in all_options if query in opt.lower()]
            combo["values"] = values

        combo.bind("<KeyRelease>", filter_values)
        combo.bind("<FocusIn>", filter_values)
        combo.bind("<FocusOut>", lambda *_: on_change())

    def _sort_average_tree(self, mode: str) -> None:
        tree = self.xp_locations_tree if mode == "xp" else self.gold_locations_tree
        rows = []
        for item in tree.get_children():
            loc, avg = tree.item(item, "values")
            rows.append((loc, float(str(avg).replace(",", ""))))
        ascending = self._xp_avg_sort_ascending if mode == "xp" else self._gold_avg_sort_ascending
        rows.sort(key=lambda row: row[1], reverse=not ascending)
        for item in tree.get_children():
            tree.delete(item)
        for loc, avg in rows:
            tree.insert("", "end", values=(loc, f"{avg:,.2f}"))
        if mode == "xp":
            self._xp_avg_sort_ascending = not ascending
            arrow = "▲" if self._xp_avg_sort_ascending else "▼"
            tree.heading("average", text=f"Average XP {arrow}", command=lambda: self._sort_average_tree("xp"))
        else:
            self._gold_avg_sort_ascending = not ascending
            arrow = "▲" if self._gold_avg_sort_ascending else "▼"
            tree.heading("average", text=f"Average Gold {arrow}", command=lambda: self._sort_average_tree("gold"))

    def _expected_multiplier(self, profile_name: str) -> float:
        profile = MUTATION_PROFILES.get(profile_name, MUTATION_PROFILES["None"])
        return sum(entry["chance"] * entry["multiplier"] for entry in profile)

    def _extract_percent_bonus(self, text: str, keywords: list[str]) -> float:
        if not text:
            return 0.0
        total = 0.0
        lowered = text.lower()
        for keyword in keywords:
            patterns = [
                rf"([+-]?\d+(?:\.\d+)?)\s*%[^.]*{re.escape(keyword)}",
                rf"{re.escape(keyword)}[^.]*?([+-]?\d+(?:\.\d+)?)\s*%",
            ]
            for pattern in patterns:
                for match in re.finditer(pattern, lowered):
                    try:
                        total += float(match.group(1))
                    except ValueError:
                        continue
        return total

    def _extract_xp_multiplier_bonus(self, text: str) -> float:
        if not text:
            return 0.0
        total = 0.0
        lowered = text.lower()
        patterns = [
            r"([0-9]+(?:\.[0-9]+)?)x\s*(?:xp|exp|experience)",
            r"(?:xp|exp|experience)[^.]*?([0-9]+(?:\.[0-9]+)?)x",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, lowered):
                try:
                    mult = float(match.group(1))
                    if mult > 0:
                        total += (mult - 1.0) * 100.0
                except ValueError:
                    continue
        return total

    def _mutation_expected_multiplier_from_passive(self, text: str) -> float:
        if not text:
            return 1.0
        lowered = text.lower()
        weighted_bonus = 0.0
        total_chance = 0.0
        for mutation, multiplier in MUTATION_MULTIPLIERS.items():
            for match in re.finditer(rf"(\d+(?:\.\d+)?)\s*%[^.]*{re.escape(mutation)}", lowered):
                chance = float(match.group(1)) / 100.0
                if chance <= 0:
                    continue
                total_chance += chance
                weighted_bonus += chance * multiplier
        if total_chance <= 0:
            return 1.0
        residual = max(0.0, 1.0 - total_chance)
        return residual + weighted_bonus

    def _rod_xp_bonus_multiplier(self, rod_name: str) -> float:
        if rod_name == "No xp bonus on rod":
            return 1.0
        rod = self._find_rod(rod_name)
        if not rod:
            return 1.0
        passive = rod.get("passive") or ""
        bonus = self._extract_percent_bonus(passive, ["xp", "exp", "experience"])
        bonus += self._extract_xp_multiplier_bonus(passive)
        return 1.0 + (bonus / 100.0)

    def _rod_gold_bonus_multiplier(self, rod_name: str) -> float:
        if not rod_name:
            return 1.0
        rod = self._find_rod(rod_name)
        if not rod:
            return 1.0
        passive = rod.get("passive") or ""
        bonus = self._extract_percent_bonus(passive, ["sell value", "value", "gold", "coins", "cash", "c$"])
        mutation_bonus = self._mutation_expected_multiplier_from_passive(passive)
        return (1.0 + (bonus / 100.0)) * mutation_bonus

    def _update_calculator_rod_choices(self) -> None:
        names = sorted((rod.get("name") or "") for rod in self.rods if rod.get("name"))
        self._gold_rod_options = names
        xp_names = []
        for rod in self.rods:
            passive = (rod.get("passive") or "").lower()
            if "xp" in passive or "experience" in passive or "exp" in passive:
                if rod.get("name"):
                    xp_names.append(rod["name"])
        self._xp_rod_options = ["No xp bonus on rod", *sorted(set(xp_names))]

        if hasattr(self, "gold_rod_combo"):
            self.gold_rod_combo["values"] = self._gold_rod_options
            if self.gold_rod_var.get() not in self._gold_rod_options:
                self.gold_rod_var.set(self._gold_rod_options[0] if self._gold_rod_options else "")
        if hasattr(self, "xp_rod_combo"):
            self.xp_rod_combo["values"] = self._xp_rod_options
            if self.xp_rod_var.get() not in self._xp_rod_options:
                self.xp_rod_var.set("No xp bonus on rod")
        self.calculate_xp()
        self.calculate_gold()

    def calculate_xp(self) -> None:
        location = self.xp_location_var.get()
        base_xp = LOCATION_AVERAGES.get(location, {}).get("avg_xp", 0.0)
        enchant_multiplier = XP_ENCHANT_MULTIPLIERS.get(self.xp_enchant_var.get(), 1.0)
        rod_multiplier = self._rod_xp_bonus_multiplier(self.xp_rod_var.get())
        adjusted = base_xp * enchant_multiplier * rod_multiplier
        self.xp_result_var.set(
            f"Adjusted XP: {adjusted:,.2f}  (base {base_xp:,.2f} × rod {rod_multiplier:.3f} × enchant {enchant_multiplier:.3f})"
        )

    def calculate_gold(self) -> None:
        location = self.gold_location_var.get()
        base_gold = LOCATION_AVERAGES.get(location, {}).get("avg_gold", 0.0)
        enchant_multiplier = GOLD_ENCHANT_MULTIPLIERS.get(self.gold_enchant_var.get(), 1.0)
        rod_multiplier = self._rod_gold_bonus_multiplier(self.gold_rod_var.get())
        mutation_multiplier = self._expected_multiplier(self.gold_mutation_profile_var.get())
        adjusted = base_gold * enchant_multiplier * rod_multiplier * mutation_multiplier
        self.gold_result_var.set(
            "Adjusted Gold: "
            f"{adjusted:,.2f}  (base {base_gold:,.2f} × rod {rod_multiplier:.3f} × enchant {enchant_multiplier:.3f} × mutation EV {mutation_multiplier:.3f})"
        )

    def _passive_stat_bonus(self, rod: dict[str, Any], stat: str) -> float:
        passive = (rod.get("passive") or "").lower()
        if not passive:
            return 0.0
        keywords = {
            "lure_speed": ["lure speed", "lure"],
            "luck": ["luck"],
            "control": ["control"],
            "resilience": ["resilience"],
            "max_kg": [],
            "price": [],
        }
        total = 0.0
        for keyword in keywords.get(stat, []):
            patterns = [
                rf"([+-]\d+(?:\.\d+)?)\s*%?\s*{re.escape(keyword)}",
                rf"{re.escape(keyword)}\s*(?:by|to)?\s*([+-]\d+(?:\.\d+)?)",
            ]
            for pattern in patterns:
                for match in re.finditer(pattern, passive):
                    try:
                        total += float(match.group(1))
                    except (TypeError, ValueError):
                        continue
        return total


def main() -> None:
    root = tk.Tk()
    app = FischDesktopApp(root)
    default_index = Path(app.index_path_var.get())
    if default_index.exists():
        app.load_local_index()
    root.mainloop()


if __name__ == "__main__":
    main()
