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
    "durability": "Durability",
    "disturbance": "Disturbance",
    "hunt_focus": "Hunt Focus",
    "passive": "Passive",
    "location": "Location",
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

        self.max_compare_slots = 6
        self.compare_choice_vars = [tk.StringVar(value="") for _ in range(self.max_compare_slots)]
        self.compare_combos: list[ttk.Combobox] = []
        self.compare_labels: list[ttk.Label] = []
        self.visible_compare_slots = 2

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

        self.tree = ttk.Treeview(middle, columns=DISPLAY_COLUMNS, show="headings", height=16)
        for col in DISPLAY_COLUMNS:
            self.tree.heading(col, text=COLUMN_TITLES[col])
            width = 85
            if col == "name":
                width = 135
            elif col == "passive":
                width = 200
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
        self.tree.tag_configure("odd", background="black", foreground="white")
        self.tree.tag_configure("even", background="white", foreground="black")
        self.tree.tag_configure("limited_location", foreground="red")

        scroll_y = ttk.Scrollbar(self.tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side="right", fill="y")

        compare_box = ttk.LabelFrame(self.root, text="Compare Rods", padding=10)
        compare_box.pack(fill="x", padx=10, pady=(0, 10))

        for i in range(self.max_compare_slots):
            label = ttk.Label(compare_box, text=f"Compare Slot {i + 1}:")
            label.grid(row=i, column=0, sticky="w", padx=4, pady=2)
            combo = ttk.Combobox(compare_box, textvariable=self.compare_choice_vars[i], width=45, state="readonly")
            combo.grid(row=i, column=1, sticky="we", padx=4, pady=2)
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
                or q in (rod.get("passive") or "").lower()
            ]

        self._render_tree()
        self._update_compare_choices()

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

    def _update_compare_choices(self) -> None:
        names = [rod.get("name", "") for rod in self.filtered_rods]
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
        self.compare_text.insert("end", "Passives:\n", ("category",))
        for idx, rod in enumerate(selected_rods):
            rod_tag = f"rod_{idx % self.max_compare_slots}"
            self.compare_text.insert("end", f"- {rod['name']}: ", (rod_tag,))
            self.compare_text.insert("end", f"{rod.get('passive') or '-'}\n")
        self.compare_text.insert("end", "\n")

        score = {rod["name"]: 0 for rod in selected_rods}

        for stat in COMPARE_STATS:
            values = [(rod["name"], self._num(rod.get(stat))) for rod in selected_rods]
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
            if rod.get("price") is None and "quest" in (rod.get("source") or "").lower():
                return "quest reward"
        return self._fmt(rod.get(col))

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
