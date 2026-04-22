from pathlib import Path

from rod_compare import Rod
from wiki_index import load_index, normalize_rods, refresh_index, save_index


def test_normalize_rods_sorted_by_name():
    rods = [Rod(name="B Rod", source="A"), Rod(name="A Rod", source="B")]
    normalized = normalize_rods(rods)
    assert [r["name"] for r in normalized] == ["A Rod", "B Rod"]


def test_save_and_load_index(tmp_path: Path):
    rods = [Rod(name="Training Rod", source="Merchant", luck=5)]
    out = tmp_path / "idx.json"
    save_index(rods, str(out))
    loaded = load_index(str(out))
    assert loaded[0]["name"] == "Training Rod"
    assert loaded[0]["luck"] == 5


def test_refresh_index_uses_fetch_and_enrich(monkeypatch, tmp_path: Path):
    calls = {"fetch": 0, "enrich": 0}

    def fake_fetch(url: str):
        calls["fetch"] += 1
        return [Rod(name="A Rod", source="Shop", passive="-")]

    def fake_enrich(rods, url: str):
        calls["enrich"] += 1
        rods[0].passive = "Speed burst"

    monkeypatch.setattr("wiki_index.fetch_rods", fake_fetch)
    monkeypatch.setattr("wiki_index.enrich_rod_details_online", fake_enrich)
    monkeypatch.setattr("wiki_index.enrich_passives_online", fake_enrich)

    out = tmp_path / "idx.json"
    result = refresh_index("https://fischipedia.org/wiki/Fishing_Rods", str(out), scan_passives=True)

    assert calls == {"fetch": 1, "enrich": 1}
    assert out.exists()
    assert result[0]["passive"] == "Speed burst"
