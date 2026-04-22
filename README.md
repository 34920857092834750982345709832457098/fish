# Fisch Rod Comparator

Small Python CLI program that reads the rod table from the Fisch wiki and compares rod stats.

## Desktop app (Option B)

A Tkinter desktop UI is included in `fisch_desktop_app.py` using the suggested architecture:

1. **Indexer layer** (`wiki_index.py`): refresh wiki data and save condensed JSON index (`rods_index.json`).
2. **Local data layer**: load/search/filter cached index quickly.
3. **Compare UI layer**: pick two rods and compare stat deltas in-app.

Run it:

```powershell
py -3 fisch_desktop_app.py
```

or

```bash
python fisch_desktop_app.py
```

Desktop compare tips:
- Starts with 2 compare slots.
- Right-click a rod row and choose **Add to compare** to add more rods (third slot appears when needed).
- In comparison output, best-per-stat is highlighted in green and overall best is highlighted in blue.

## Windows 11 quick start

Open **PowerShell** in the folder where you saved these files, then run:

```powershell
py -3 rod_compare.py --help
```

Run a comparison:

```powershell
py -3 rod_compare.py --top 10 --sort luck
```

## Run

```bash
python rod_compare.py --top 10 --sort luck
```

Compare specific rods:

```bash
python rod_compare.py --rods "Training Rod" "Kraken Rod" --sort resilience
```

JSON output:

```bash
python rod_compare.py --top 5 --json
```

Scan each rod page for passives (online-only enrichment):

```bash
python rod_compare.py --scan-passives --top 10 --sort luck
```

With `--scan-passives`, the script also scans each rod page for detailed factors (location, source, price, stage, durability, disturbance, hunt focus, line distance, passive).

Use a local HTML file (no network request):

```bash
python rod_compare.py --input-html Fishing_Rods.html --top 10 --sort luck
```

## Notes

- The script scrapes the table from `https://fischipedia.org/wiki/Fishing_Rods` by default.
- If direct HTML table parsing fails, the script attempts a MediaWiki raw-text fallback (`?action=raw`).
- Add `--scan-passives` to fetch each rod's individual wiki page and enrich passive descriptions.
- Individual rod pages are discovered by replacing spaces with `_` in the rod name (e.g., `Brine-Infused Rod` -> `/wiki/Brine-Infused_Rod`).
- If network access to the site is blocked, save the page as HTML in your browser and pass the file via `--input-html`.
- `--scan-passives` is online-only and cannot be combined with `--input-html`.
- Source, location, and price are parsed into separate fields/columns when possible, and missing factors display as `-`.
- If network access to the site is blocked, save the page as HTML in your browser and pass the file via `--input-html`.
- `--scan-passives` is online-only and cannot be combined with `--input-html`.
- If the page structure changes, header matching may need updates in `rod_compare.py`.
- Desktop index data is saved to `rods_index.json` by default.
