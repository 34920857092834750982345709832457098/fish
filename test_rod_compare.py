from pathlib import Path

from rod_compare import (
    WikiTableParser,
    choose_rod_tables,
    extract_passive_from_rod_page,
    enrich_rod_details_online,
    fetch_rod_page_details,
    load_rods_from_local_html,
    map_header_indices,
    parse_number,
    parse_rods_from_html,
    parse_rods_from_wikitext,
    row_to_rod,
    Rod,
)


SAMPLE_HTML = """
<table>
  <tr>
    <th>Rod</th><th>Source</th><th>Lure Speed</th><th>Luck</th><th>Control</th><th>Resilience</th><th>Max Kg</th><th>Price</th><th>Passive</th>
  </tr>
  <tr>
    <td>Training Rod</td><td>Merchant</td><td>10%</td><td>5</td><td>0.15</td><td>8%</td><td>20,000</td><td>C$300</td><td>-</td>
  </tr>
  <tr>
    <td>Kraken Rod</td><td>Quest</td><td>70%</td><td>180</td><td>0.2</td><td>15%</td><td>100,000</td><td>C$50,000</td><td>Tentacle Hit</td>
  </tr>
</table>
"""


def test_parse_number():
    assert parse_number("70%") == 70.0
    assert parse_number("C$50,000") == 50000.0
    assert parse_number("-") is None


def test_extract_and_convert_rows():
    parser = WikiTableParser()
    parser.feed(SAMPLE_HTML)

    selected = choose_rod_tables(parser.tables)
    assert selected
    headers, rows = selected[0]

    idx = map_header_indices(headers)
    rods = [row_to_rod(row, idx) for row in rows]
    rods = [r for r in rods if r is not None]

    assert len(rods) == 2
    assert rods[0].name == "Training Rod"
    assert rods[0].lure_speed == 10.0
    assert rods[1].price == 50000.0
    assert rods[1].passive == "Tentacle Hit"


def test_split_price_from_source_when_price_column_missing():
    headers = ["Rod", "Source", "Luck"]
    idx = map_header_indices(headers)
    row = ["Mystic Rod", "Merlin - C$12,000", "35"]
    rod = row_to_rod(row, idx)
    assert rod is not None
    assert rod.price == 12000.0
    assert rod.source == "Merlin"


def test_parse_rods_from_html_helper():
    rods = parse_rods_from_html(SAMPLE_HTML)
    assert [r.name for r in rods] == ["Training Rod", "Kraken Rod"]


def test_load_rods_from_local_html(tmp_path: Path):
    html_file = tmp_path / "Fishing_Rods.html"
    html_file.write_text(SAMPLE_HTML, encoding="utf-8")
    rods = load_rods_from_local_html(str(html_file))
    assert rods[0].source == "Merchant"


def test_extract_passive_from_rod_page():
    html = """
    <table class="infobox">
      <tr><th>Passive</th><td><b>Tentacle Hit</b> (10% chance)</td></tr>
    </table>
    """
    assert extract_passive_from_rod_page(html) == "Tentacle Hit (10% chance)"


def test_enrich_passives_online_with_mock(monkeypatch):
    rods = [Rod(name="Training Rod", source="Merchant", passive="-")]

    def fake_fetch(name: str, base: str):
        assert name == "Training Rod"
        assert base == "https://fischipedia.org"
        return {"passive": "No passive", "stage": "Stage 3", "line_distance": "20m"}

    monkeypatch.setattr("rod_compare.fetch_rod_page_details", fake_fetch)
    enrich_rod_details_online(rods, "https://fischipedia.org/wiki/Fishing_Rods")

    assert rods[0].passive == "No passive"
    assert rods[0].stage == "Stage 3"
    assert rods[0].line_distance == "20m"


def test_parse_rods_from_wikitext():
    raw = """
    {| class=\"wikitable\"
    ! Rod !! Source !! Lure Speed !! Luck !! Control !! Resilience !! Max Kg !! Price !! Passive
    |-
    | Training Rod || Merchant || 10% || 5 || 0.15 || 8% || 20,000 || C$300 || -
    |-
    | Kraken Rod || Quest || 70% || 180 || 0.2 || 15% || 100,000 || C$50,000 || Tentacle Hit
    |}
    """
    rods = parse_rods_from_wikitext(raw)
    assert len(rods) == 2
    assert rods[1].name == "Kraken Rod"
    assert rods[1].passive == "Tentacle Hit"


def test_parse_rods_from_html_collects_multiple_tables():
    html = """
    <table>
      <tr><th>Rod</th><th>Source</th><th>Lure</th><th>Luck</th><th>Control</th><th>Resilience</th></tr>
      <tr><td>Rod A</td><td>Shop</td><td>10</td><td>5</td><td>1</td><td>1</td></tr>
    </table>
    <table>
      <tr><th>Rod</th><th>Source</th><th>Lure</th><th>Luck</th><th>Control</th><th>Resilience</th></tr>
      <tr><td>Rod B</td><td>Quest</td><td>12</td><td>7</td><td>1</td><td>1</td></tr>
    </table>
    """
    rods = parse_rods_from_html(html)
    assert {r.name for r in rods} == {"Rod A", "Rod B"}


def test_fetch_rod_page_details_extracts_many_fields(monkeypatch):
    html = """
    <table>
      <tr><th>Location</th><td>Brine Pool</td></tr>
      <tr><th>Source</th><td>Purchasing</td></tr>
      <tr><th>Price</th><td>15,000C$</td></tr>
      <tr><th>Stage</th><td>Stage 3</td></tr>
      <tr><th>Durability</th><td>200 (Lava, Noxious Fluid, Brine)</td></tr>
      <tr><th>Disturbance</th><td>+1</td></tr>
      <tr><th>Hunt Focus</th><td>Brine Storm +5</td></tr>
      <tr><th>Line Distance</th><td>20m</td></tr>
      <tr><th>Passive</th><td>50% chance for Brined (3.5×)</td></tr>
    </table>
    """

    class DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return html.encode("utf-8")

    monkeypatch.setattr("rod_compare.urlopen", lambda *args, **kwargs: DummyResponse())
    details = fetch_rod_page_details("Brine-Infused Rod", "https://fischipedia.org")

    assert details["location"] == "Brine Pool"
    assert details["source"] == "Purchasing"
    assert details["price"] == "15,000C$"
    assert details["stage"] == "Stage 3"
    assert details["durability"].startswith("200")
