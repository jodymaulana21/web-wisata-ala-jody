"""Engine percakapan.

- GeminiEngine : memakai LLM Google Gemini + function calling otomatis
                 ke tools (cuaca, kurs, rekomendasi).
- DemoEngine   : fallback rule-based tanpa API key, agar aplikasi tetap
                 bisa dicoba. Tetap memakai tools/API eksternal yang sama.
"""
from __future__ import annotations

import functools
import re
from dataclasses import dataclass, field

from . import config
from .tools import TOOLS, convert_currency, get_weather, recommend_destinations


@dataclass
class BotReply:
    text: str
    tool_calls: list[dict] = field(default_factory=list)


def _tracked(func, log: list):
    """Bungkus tool agar setiap pemanggilan tercatat (untuk ditampilkan di UI)."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        log.append({"tool": func.__name__, "args": kwargs or list(args), "result": result})
        return result

    return wrapper


# ---------------------------------------------------------------------------
# Gemini (LLM)
# ---------------------------------------------------------------------------
class GeminiEngine:
    name = "Gemini"

    def __init__(self, api_key: str, model: str):
        # import di sini agar DemoEngine tetap jalan tanpa paket google-genai
        from google import genai
        from google.genai import types

        self._types = types
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def reply(self, history: list[dict], user_msg: str, persona: str, creativity: str, memory_text: str) -> BotReply:
        t = self._types
        log: list[dict] = []
        params = config.CREATIVITY[creativity]

        contents = [
            t.Content(role="user" if m["role"] == "user" else "model", parts=[t.Part(text=m["content"])])
            for m in history
        ]
        contents.append(t.Content(role="user", parts=[t.Part(text=user_msg)]))

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=t.GenerateContentConfig(
                system_instruction=config.build_system_prompt(persona, memory_text),
                temperature=params["temperature"],
                top_p=params["top_p"],
                max_output_tokens=config.MAX_OUTPUT_TOKENS,
                tools=[_tracked(fn, log) for fn in TOOLS],
            ),
        )
        return BotReply(text=response.text or "(Maaf, tidak ada jawaban dari model.)", tool_calls=log)


# ---------------------------------------------------------------------------
# Demo (tanpa API key)
# ---------------------------------------------------------------------------
CURRENCY_RE = re.compile(r"([\d.,]+)\s*(usd|sgd|myr|eur|jpy|aud|krw|gbp|cny|sar|dollar|dolar|ringgit|euro|yen)", re.I)
CURRENCY_ALIAS = {"dollar": "USD", "dolar": "USD", "ringgit": "MYR", "euro": "EUR", "yen": "JPY"}
KNOWN_CITIES = [
    "Bandung Barat", "Bandung", "Lembang", "Ciwidey", "Pangalengan", "Garut", "Tasikmalaya", "Bogor",
    "Puncak", "Sukabumi", "Cianjur", "Sumedang", "Kuningan", "Cirebon", "Pangandaran", "Purwakarta",
    "Subang", "Majalengka", "Banten", "Serang", "Pandeglang", "Lebak", "Depok", "Bekasi",
]
INTERESTS = [
    "kebun teh", "curug", "air terjun", "pantai", "gunung", "kawah", "danau", "situ", "alam",
    "kuliner", "budaya", "sejarah", "keluarga", "petualangan",
]


def _rupiah(n: float) -> str:
    return "Rp" + f"{n:,.0f}".replace(",", ".")


def _parse_budget(text: str) -> int:
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(jt|juta|rb|ribu|k)\b", text, re.I)
    if not m:
        return 0
    n = float(m.group(1).replace(",", "."))
    return int(n * (1_000_000 if m.group(2).lower() in ("jt", "juta") else 1_000))


class DemoEngine:
    name = "Demo (tanpa LLM)"

    def reply(self, history, user_msg, persona, creativity, memory_text) -> BotReply:
        msg = user_msg.lower()
        log: list[dict] = []
        city = next((c for c in KNOWN_CITIES if c.lower() in msg), "")
        formal = persona == "Formal"
        sunda = persona.startswith("Kang Jody")
        you = "Anda" if formal else "kamu"

        if "cuaca" in msg or "hujan" in msg:
            target = city or "Bandung"
            res = _tracked(get_weather, log)(city=target)
            if "error" in res:
                text = f"Maaf, data cuaca belum bisa diambil ({res['error']})."
            else:
                c = res["sekarang"]
                lines = [f"**Cuaca di {res['lokasi']}** saat ini: {c['kondisi']}, {c['suhu_c']}°C, "
                         f"kelembapan {c['kelembapan_persen']}%, angin {c['angin_kmh']} km/j.", "", "Prakiraan:"]
                lines += [f"- {d['tanggal']}: {d['kondisi']}, {d['suhu_min_c']}–{d['suhu_max_c']}°C, "
                          f"peluang hujan {d['peluang_hujan_persen']}%" for d in res["prakiraan"]]
                text = "\n".join(lines)
        elif (m := CURRENCY_RE.search(user_msg)):
            amount = float(m.group(1).replace(".", "").replace(",", "."))
            code = CURRENCY_ALIAS.get(m.group(2).lower(), m.group(2).upper())
            res = _tracked(convert_currency, log)(amount=amount, from_currency=code, to_currency="IDR")
            text = (f"Maaf, kurs belum bisa diambil ({res['error']})." if "error" in res else
                    f"**{res['dari']} ≈ {res['ke']}**\n\nKurs: {res['kurs']}  \nUpdate: {res['update_terakhir']}")
        elif any(k in msg for k in ("rekomendasi", "rekomen", "wisata", "liburan", "destinasi", "itinerary")):
            interest = next((i for i in INTERESTS if i in msg), "")
            budget = _parse_budget(msg)
            days = int(d.group(1)) if (d := re.search(r"(\d+)\s*hari", msg)) else 0
            per_day = budget // days if (budget and days) else budget
            res = _tracked(recommend_destinations, log)(
                interest=interest, max_budget_idr=per_day, region=city, limit=3)
            if not res["hasil"]:
                text = res["catatan"]
            else:
                intro = "Berikut rekomendasi destinasi untuk Anda:" if formal else \
                    ("Mangga, ieu rekomendasi ti abdi:" if sunda else "Nih rekomendasi wisata Sunda buat kamu 👇")
                lines = [intro, ""]
                for i, r in enumerate(res["hasil"], 1):
                    lines.append(f"**{i}. {r['nama']}** ({r['lokasi']}) — ⭐ {r['rating']}  \n"
                                 f"{r['deskripsi']}  \nBudget ±{_rupiah(r['budget_per_hari_idr'])}/hari · "
                                 f"Waktu terbaik: {r['waktu_terbaik']}\n")
                if days:
                    lines.append("\n_Catatan: itinerary detail per hari tersedia penuh di mode Gemini (LLM)._")
                text = "\n".join(lines)
        elif re.search(r"\b(halo|hai|hi|pagi|siang|sore|malam|assalamualaikum)\b", msg):
            text = config.PERSONAS[persona]["greeting"]
        elif re.search(r"\b(kumaha damang|damang)\b", msg):
            text = "Pangestu, damang abdi mah! 😄 Mangga, bade ngalalana ka mana?"
        else:
            text = (f"Saat ini Ngalalana berjalan di **mode demo** (tanpa API key), jadi {you} bisa mencoba: "
                    "cek cuaca kota, konversi mata uang, atau minta rekomendasi wisata Tatar Sunda. "
                    "Isi `GEMINI_API_KEY` di file `.env` untuk percakapan bebas penuh dengan LLM.")
        if sunda and log:
            text += "\n\n_Catetan Kang Jody: tong hilap mawa jaket, hawa Bandung mah tiris! Hatur nuhun_ 🙏"
        return BotReply(text=text, tool_calls=log)


def get_engine():
    """Pilih engine: Gemini jika API key tersedia, selain itu DemoEngine."""
    if config.GEMINI_API_KEY:
        try:
            return GeminiEngine(config.GEMINI_API_KEY, config.GEMINI_MODEL)
        except ImportError:
            pass
    return DemoEngine()
