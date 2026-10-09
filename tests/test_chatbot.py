"""Unit test JelajahBot (tanpa jaringan: API eksternal di-mock)."""
from unittest.mock import MagicMock, patch

from chatbot import config
from chatbot.llm import DemoEngine, _parse_budget
from chatbot.memory import Memory
from chatbot.tools import convert_currency, get_weather, recommend_destinations


# --- Rekomendasi -----------------------------------------------------------
def test_recommend_filters_region_and_interest():
    res = recommend_destinations(interest="alam", region="Bandung", limit=5)
    assert res["hasil"]
    for r in res["hasil"]:
        assert "Jawa Barat" in r["lokasi"]


def test_recommend_respects_budget():
    res = recommend_destinations(max_budget_idr=150_000, limit=5)
    assert all(r["budget_per_hari_idr"] <= 150_000 for r in res["hasil"])


def test_recommend_no_match():
    res = recommend_destinations(interest="ski salju", region="Bandung")
    assert res["hasil"] == []


# --- Kurs (mock) -----------------------------------------------------------
@patch("chatbot.tools.requests.get")
def test_convert_currency(mock_get):
    mock_get.return_value = MagicMock(json=lambda: {
        "result": "success", "rates": {"IDR": 16000.0}, "time_last_update_utc": "x"})
    res = convert_currency(10, "usd")
    assert res["ke"] == "160,000.00 IDR"


# --- Cuaca (mock) ----------------------------------------------------------
@patch("chatbot.tools.requests.get")
def test_get_weather_city_not_found(mock_get):
    mock_get.return_value = MagicMock(json=lambda: {})
    assert "error" in get_weather("Kota Antah Berantah")


# --- Memory ----------------------------------------------------------------
def test_memory_extracts_facts(tmp_path):
    mem = Memory(tmp_path / "m.json")
    changed = mem.extract("Halo, nama saya Jody, aku dari Bandung dan suka pantai dan kuliner")
    assert set(changed) >= {"nama", "kota_asal", "minat"}
    assert mem.facts["nama"] == "Jody"
    assert Memory(tmp_path / "m.json").facts["kota_asal"] == "Bandung"  # tersimpan ke file


# --- Demo engine & util ----------------------------------------------------
def test_parse_budget():
    assert _parse_budget("budget 3 juta") == 3_000_000
    assert _parse_budget("maks 500rb") == 500_000


def test_demo_engine_recommendation_uses_tool():
    reply = DemoEngine().reply([], "rekomendasi wisata alam di Bandung", "Santai", "Seimbang", "")
    assert reply.tool_calls and reply.tool_calls[0]["tool"] == "recommend_destinations"


def test_system_prompt_contains_style_and_memory():
    prompt = config.build_system_prompt("Formal", "- Nama: Jody")
    assert "Formal" in prompt or "baku" in prompt
    assert "Jody" in prompt
