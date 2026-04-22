from pathlib import Path

from rod_compare import (
    WikiTableParser,
    choose_rod_table,
    extract_passive_from_rod_page,
    enrich_passives_online,
    load_rods_from_local_html,
    map_header_indices,
    parse_number,
    parse_rods_from_html,
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

    selected = choose_rod_table(parser.tables)
    assert selected is not None
    headers, rows = selected

    idx = map_header_indices(headers)
    rods = [row_to_rod(row, idx) for row in rows]
    rods = [r for r in rods if r is not None]

    assert len(rods) == 2
    assert rods[0].name == "Training Rod"
    assert rods[0].lure_speed == 10.0
    assert rods[1].price == 50000.0
    assert rods[1].passive == "Tentacle Hit"


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
        return "No passive"

    monkeypatch.setattr("rod_compare.fetch_rod_page_passive", fake_fetch)
    enrich_passives_online(rods, "https://fischipedia.org/wiki/Fishing_Rods")

    assert rods[0].passive == "No passive"
