"""Konfigurasi parameter kreatif JelajahBot.

Semua "parameter kreatif" chatbot dikumpulkan di sini supaya mudah diubah:
- PERSONAS      : gaya bahasa (santai / formal / pemandu lokal Sunda)
- CREATIVITY    : preset temperature & top_p model
- BASE_PROMPT   : batasan domain (wisata Indonesia)
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

APP_NAME = "JelajahBot"
APP_TAGLINE = "Asisten wisata Indonesia berbasis AI"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

# ---------------------------------------------------------------------------
# Domain pengetahuan: wisata Indonesia
# ---------------------------------------------------------------------------
BASE_PROMPT = """Kamu adalah {name}, asisten perjalanan (travel assistant) yang ahli
tentang destinasi wisata di Indonesia: alam, kuliner, budaya, transportasi,
estimasi biaya, dan tips perjalanan.

Aturan:
1. Fokus pada topik perjalanan & wisata. Jika pengguna bertanya di luar topik,
   jawab singkat lalu arahkan kembali ke topik perjalanan dengan sopan.
2. Gunakan tools yang tersedia bila relevan:
   - get_weather          -> cuaca terkini & prakiraan suatu kota
   - convert_currency     -> konversi mata uang dengan kurs terbaru
   - recommend_destinations -> rekomendasi destinasi dari katalog lokal
   Jangan mengarang data cuaca atau kurs; selalu panggil tool.
3. Jika membuat itinerary, susun per hari dengan perkiraan biaya dalam Rupiah.
4. Jawaban ringkas, terstruktur (gunakan poin/heading markdown bila perlu),
   maksimal ~250 kata kecuali pengguna minta detail.
5. Jika tidak yakin, katakan tidak yakin dan sarankan pengguna mengecek
   sumber resmi.

Gaya bahasa: {style}

Yang kamu ingat tentang pengguna ini (memory):
{memory}
"""

PERSONAS: dict[str, dict[str, str]] = {
    "Santai": {
        "emoji": "😎",
        "style": (
            "Santai dan akrab seperti teman jalan-jalan. Pakai sapaan 'kamu', "
            "boleh sedikit emoji, kalimat pendek dan hangat."
        ),
        "greeting": "Halo! Aku JelajahBot 😎 Mau liburan ke mana nih? Ceritain aja rencanamu.",
    },
    "Formal": {
        "emoji": "🧳",
        "style": (
            "Formal dan profesional seperti agen perjalanan. Pakai sapaan "
            "'Anda', bahasa baku, tanpa emoji, terstruktur rapi."
        ),
        "greeting": "Selamat datang di JelajahBot. Ada yang dapat saya bantu untuk rencana perjalanan Anda?",
    },
    "Pemandu Lokal (Sunda)": {
        "emoji": "🌋",
        "style": (
            "Seperti pemandu lokal asal Bandung yang ramah. Bahasa Indonesia "
            "santai dengan sisipan kata Sunda ringan (mangga, punten, hatur "
            "nuhun, atuh) dan cerita singkat tentang budaya setempat."
        ),
        "greeting": "Wilujeng sumping! Abdi JelajahBot, pemandu wisata. Mangga, mau jalan-jalan ka mana?",
    },
}

CREATIVITY: dict[str, dict[str, float]] = {
    "Presisi": {"temperature": 0.2, "top_p": 0.8},
    "Seimbang": {"temperature": 0.7, "top_p": 0.9},
    "Kreatif": {"temperature": 1.1, "top_p": 0.95},
}

DEFAULT_PERSONA = "Santai"
DEFAULT_CREATIVITY = "Seimbang"
MAX_OUTPUT_TOKENS = 1024

SUGGESTED_PROMPTS = [
    "Rekomendasi wisata alam murah dekat Bandung",
    "Gimana cuaca di Yogyakarta hari ini?",
    "Berapa 150 USD dalam Rupiah?",
    "Buatkan itinerary 3 hari ke Bali budget 3 juta",
]


def build_system_prompt(persona: str, memory_text: str) -> str:
    style = PERSONAS.get(persona, PERSONAS[DEFAULT_PERSONA])["style"]
    return BASE_PROMPT.format(name=APP_NAME, style=style, memory=memory_text or "(belum ada)")
