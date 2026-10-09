"""Tools / integrasi API eksternal yang bisa dipanggil oleh LLM (function calling).

- get_weather            : Open-Meteo (gratis, tanpa API key)
- convert_currency       : open.er-api.com (gratis, tanpa API key)
- recommend_destinations : katalog lokal data/destinations.json

Docstring & type hint setiap fungsi dipakai Gemini SDK untuk membuat
deklarasi fungsi secara otomatis, jadi tulis dengan jelas.
"""

import json
from functools import lru_cache
from pathlib import Path

import requests

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "destinations.json"
TIMEOUT = 10

WEATHER_CODES = {
    0: "Cerah", 1: "Cerah berawan", 2: "Berawan sebagian", 3: "Berawan",
    45: "Berkabut", 48: "Kabut tebal", 51: "Gerimis ringan", 53: "Gerimis",
    55: "Gerimis lebat", 61: "Hujan ringan", 63: "Hujan sedang",
    65: "Hujan lebat", 80: "Hujan lokal ringan", 81: "Hujan lokal",
    82: "Hujan lokal lebat", 95: "Badai petir", 96: "Badai petir + es",
    99: "Badai petir hebat",
}


def get_weather(city: str) -> dict:
    """Ambil cuaca terkini dan prakiraan 3 hari untuk sebuah kota.

    Args:
        city: Nama kota, misalnya "Bandung" atau "Labuan Bajo".

    Returns:
        dict berisi lokasi, cuaca sekarang (suhu, kondisi, angin) dan
        prakiraan harian; atau dict {"error": ...} jika gagal.
    """
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "id", "format": "json"},
            timeout=TIMEOUT,
        ).json()
        if not geo.get("results"):
            return {"error": f"Kota '{city}' tidak ditemukan."}
        loc = geo["results"][0]

        wx = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": loc["latitude"],
                "longitude": loc["longitude"],
                "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "timezone": "auto",
                "forecast_days": 3,
            },
            timeout=TIMEOUT,
        ).json()
        cur, daily = wx["current"], wx["daily"]
        return {
            "lokasi": f"{loc['name']}, {loc.get('admin1', '')}, {loc.get('country', '')}".strip(", "),
            "sekarang": {
                "suhu_c": cur["temperature_2m"],
                "kelembapan_persen": cur["relative_humidity_2m"],
                "kondisi": WEATHER_CODES.get(cur["weather_code"], "Tidak diketahui"),
                "angin_kmh": cur["wind_speed_10m"],
            },
            "prakiraan": [
                {
                    "tanggal": daily["time"][i],
                    "kondisi": WEATHER_CODES.get(daily["weather_code"][i], "Tidak diketahui"),
                    "suhu_min_c": daily["temperature_2m_min"][i],
                    "suhu_max_c": daily["temperature_2m_max"][i],
                    "peluang_hujan_persen": daily["precipitation_probability_max"][i],
                }
                for i in range(len(daily["time"]))
            ],
            "sumber": "Open-Meteo",
        }
    except (requests.RequestException, KeyError, ValueError) as exc:
        return {"error": f"Gagal mengambil data cuaca: {exc.__class__.__name__}"}


def convert_currency(amount: float, from_currency: str, to_currency: str = "IDR") -> dict:
    """Konversi nominal uang dari satu mata uang ke mata uang lain dengan kurs terbaru.

    Args:
        amount: Jumlah uang yang akan dikonversi.
        from_currency: Kode mata uang asal (ISO 4217), misalnya "USD".
        to_currency: Kode mata uang tujuan (ISO 4217), default "IDR".

    Returns:
        dict berisi hasil konversi dan kurs; atau {"error": ...} jika gagal.
    """
    src, dst = from_currency.upper().strip(), to_currency.upper().strip()
    try:
        data = requests.get(f"https://open.er-api.com/v6/latest/{src}", timeout=TIMEOUT).json()
        if data.get("result") != "success":
            return {"error": f"Kode mata uang '{src}' tidak dikenali."}
        rate = data["rates"].get(dst)
        if rate is None:
            return {"error": f"Kode mata uang '{dst}' tidak dikenali."}
        return {
            "dari": f"{amount:,.2f} {src}",
            "ke": f"{amount * rate:,.2f} {dst}",
            "kurs": f"1 {src} = {rate:,.4f} {dst}",
            "update_terakhir": data.get("time_last_update_utc", "-"),
            "sumber": "ExchangeRate-API (open.er-api.com)",
        }
    except (requests.RequestException, KeyError, ValueError) as exc:
        return {"error": f"Gagal mengambil kurs: {exc.__class__.__name__}"}


@lru_cache(maxsize=1)
def _load_destinations() -> list[dict]:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def recommend_destinations(
    interest: str = "",
    max_budget_idr: int = 0,
    region: str = "",
    limit: int = 3,
) -> dict:
    """Rekomendasikan destinasi wisata Indonesia dari katalog berdasarkan minat & budget.

    Args:
        interest: Minat wisata, misalnya "alam", "pantai", "kuliner", "budaya", "gunung".
            Kosongkan jika tidak spesifik.
        max_budget_idr: Batas budget per orang per hari dalam Rupiah. 0 berarti tanpa batas.
        region: Provinsi/kota/area, misalnya "Bandung", "Bali", "Jawa Barat". Kosongkan jika bebas.
        limit: Jumlah maksimal rekomendasi (1-5).

    Returns:
        dict berisi daftar destinasi yang cocok, diurutkan dari skor tertinggi.
    """
    interest_l, region_l = interest.lower().strip(), region.lower().strip()
    limit = max(1, min(int(limit or 3), 5))
    scored = []
    for d in _load_destinations():
        if max_budget_idr and d["budget_per_hari_idr"] > max_budget_idr:
            continue
        place = f"{d['kota']} {d['provinsi']} {' '.join(d.get('alias_area', []))}".lower()
        if region_l and region_l not in place:
            continue
        score = d["rating"]
        if interest_l:
            if any(interest_l in tag or tag in interest_l for tag in d["kategori"]):
                score += 2
            elif interest_l in d["deskripsi"].lower():
                score += 1
            else:
                continue
        scored.append((score, d))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = [
        {
            "nama": d["nama"],
            "lokasi": f"{d['kota']}, {d['provinsi']}",
            "kategori": d["kategori"],
            "budget_per_hari_idr": d["budget_per_hari_idr"],
            "waktu_terbaik": d["waktu_terbaik"],
            "deskripsi": d["deskripsi"],
            "rating": d["rating"],
        }
        for _, d in scored[:limit]
    ]
    if not results:
        return {"hasil": [], "catatan": "Tidak ada destinasi di katalog yang cocok. Coba longgarkan filter."}
    return {"hasil": results, "jumlah": len(results)}


TOOLS = [get_weather, convert_currency, recommend_destinations]
