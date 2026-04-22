#!/usr/bin/env python3
"""Fisch desktop app (Tkinter) for searching and comparing rods.

Suggested architecture implemented:
- Indexer: refresh online data into a local JSON index.
- Local data: load condensed index for fast search/filter.
- UI: compare rods in a desktop interface.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

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
    "durability",
    "disturbance",
    "hunt_focus",
    "line_distance",
    "passive",
    "location",
    "passive",
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
    "durability": "Durability",
    "disturbance": "Disturbance",
    "hunt_focus": "Hunt Focus",
    "line_distance": "Line Distance",
    "passive": "Passive",
    "location": "Location",
    "passive": "Passive",
    "source": "Source",
}

COMPARE_STATS = ["lure_speed", "luck", "control", "resilience", "max_kg", "price"]


class FischDesktopApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Fisch Rod Explorer")
        self.root.geometry("1250x760")

        self.index_path_var = tk.StringVar(value=str(Path(DEFAULT_INDEX_FILE).resolve()))
        self.wiki_url_var = tk.StringVar(value=DEFAULT_URL)
        self.search_var = tk.StringVar(value="")
        self.scan_passives_var = tk.BooleanVar(value=True)

        self.rods: list[dict[str, Any]] = []
        self.filtered_rods: list[dict[str, Any]] = []

        self.left_choice_var = tk.StringVar(value="")
        self.right_choice_var = tk.StringVar(value="")

        self._build_ui()
        self.search_var.trace_add("write", lambda *_: self.apply_search_filter())

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=10)
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

        top.columnconfigure(1, weight=1)

        middle = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        middle.pack(fill="both", expand=True)

        search_row = ttk.Frame(middle)
        search_row.pack(fill="x", pady=(0, 8))
        ttk.Label(search_row, text="Search:").pack(side="left")
        ttk.Entry(search_row, textvariable=self.search_var, width=40).pack(side="left", padx=8)
        ttk.Label(search_row, text="(name, location, source, passive)").pack(side="left")
        ttk.Label(search_row, text="(name, source, passive)").pack(side="left")

        self.tree = ttk.Treeview(middle, columns=DISPLAY_COLUMNS, show="headings", height=16)
        for col in DISPLAY_COLUMNS:
            self.tree.heading(col, text=COLUMN_TITLES[col])
            width = 120
            if col == "name":
                width = 180
            elif col == "passive":
                width = 260
            elif col == "location":
                width = 180
            elif col == "durability":
                width = 200
            elif col == "hunt_focus":
                width = 200
            elif col == "source":
                width = 180
            self.tree.column(col, width=width, stretch=True, anchor="w")
        self.tree.pack(fill="both", expand=True)

        scroll_y = ttk.Scrollbar(self.tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side="right", fill="y")

        compare_box = ttk.LabelFrame(self.root, text="Compare Rods", padding=10)
        compare_box.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Label(compare_box, text="Left Rod:").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.left_combo = ttk.Combobox(compare_box, textvariable=self.left_choice_var, width=35, state="readonly")
        self.left_combo.grid(row=0, column=1, sticky="w", padx=4, pady=4)

        ttk.Label(compare_box, text="Right Rod:").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        self.right_combo = ttk.Combobox(compare_box, textvariable=self.right_choice_var, width=35, state="readonly")
        self.right_combo.grid(row=0, column=3, sticky="w", padx=4, pady=4)

        ttk.Button(compare_box, text="Compare", command=self.compare_selected).grid(row=0, column=4, padx=8)

        self.compare_text = tk.Text(compare_box, height=9, wrap="word")
        self.compare_text.grid(row=1, column=0, columnspan=5, sticky="we", padx=4, pady=(8, 4))

        compare_box.columnconfigure(1, weight=1)
        compare_box.columnconfigure(3, weight=1)

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
                or q in (rod.get("durability") or "").lower()
                or q in (rod.get("disturbance") or "").lower()
                or q in (rod.get("hunt_focus") or "").lower()
                or q in (rod.get("line_distance") or "").lower()
                or q in (rod.get("source") or "").lower()
                or q in (rod.get("passive") or "").lower()
            ]

        self._render_tree()
        self._update_compare_choices()

    def _render_tree(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        for rod in self.filtered_rods:
            row = [self._fmt(rod.get(col)) for col in DISPLAY_COLUMNS]
            self.tree.insert("", "end", values=row)

    def _update_compare_choices(self) -> None:
        names = [rod.get("name", "") for rod in self.filtered_rods]
        self.left_combo["values"] = names
        self.right_combo["values"] = names

        if names:
            if self.left_choice_var.get() not in names:
                self.left_choice_var.set(names[0])
            if self.right_choice_var.get() not in names:
                self.right_choice_var.set(names[min(1, len(names) - 1)])
        else:
            self.left_choice_var.set("")
            self.right_choice_var.set("")

    def compare_selected(self) -> None:
        left = self._find_rod(self.left_choice_var.get())
        right = self._find_rod(self.right_choice_var.get())
        if not left or not right:
            messagebox.showwarning("Missing selection", "Please select two rods to compare.")
            return

        lines = [
            f"Comparing: {left['name']}  vs  {right['name']}",
            "",
            f"Passive (left):  {left.get('passive') or '-'}",
            f"Passive (right): {right.get('passive') or '-'}",
            "",
        ]

        for stat in COMPARE_STATS:
            lv = self._num(left.get(stat))
            rv = self._num(right.get(stat))
            delta = lv - rv
            if delta > 0:
                winner = left["name"]
            elif delta < 0:
                winner = right["name"]
            else:
                winner = "Tie"
            lines.append(f"{COLUMN_TITLES[stat]}: {lv:g} vs {rv:g}  | Δ={delta:+g} | Winner: {winner}")

        self.compare_text.delete("1.0", "end")
        self.compare_text.insert("1.0", "\n".join(lines))

    def _find_rod(self, name: str) -> dict[str, Any] | None:
        for rod in self.rods:
            if rod.get("name") == name:
                return rod
        return None

    @staticmethod
    def _fmt(value: Any) -> str:
        if value is None or value == "":
            return "-"
        return str(value)

    @staticmethod
    def _num(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0


def main() -> None:
    root = tk.Tk()
    app = FischDesktopApp(root)
    default_index = Path(app.index_path_var.get())
    if default_index.exists():
        app.load_local_index()
    root.mainloop()


if __name__ == "__main__":
    main()
