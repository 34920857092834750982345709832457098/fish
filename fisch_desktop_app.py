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

        self.max_compare_slots = 6
        self.compare_choice_vars = [tk.StringVar(value="") for _ in range(self.max_compare_slots)]
        self.compare_combos: list[ttk.Combobox] = []
        self.compare_labels: list[ttk.Label] = []
        self.visible_compare_slots = 2
        self._default_passive_width = 200
        self._sort_state: dict[str, bool] = {}
        self._passive_popup: tk.Toplevel | None = None
        self._compare_all_names: list[str] = []

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

        ttk.Label(xp_tab, text="XP tab coming next.").pack(anchor="center", pady=20)
        ttk.Label(gold_tab, text="Gold tab coming next.").pack(anchor="center", pady=20)

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
