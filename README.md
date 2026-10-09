# 🎋 Ngalalana — Pemandu Wisata Tatar Sunda ala Jody Maulana

**Ngalalana** (bahasa Sunda: *berkelana*) adalah chatbot pemandu wisata yang memakai LLM **Google Gemini**
untuk memahami bahasa alami dan memberi jawaban seputar wisata **Tatar Sunda (Jawa Barat & Banten)**:
rekomendasi destinasi, itinerary plus kuliner Sunda, cuaca, dan konversi mata uang — dengan gaya
"Kang Jody", pemandu lokal urang Bandung.

> Dibuat oleh **Jody Maulana, S.Kom.** untuk tugas proyek chatbot AI.

## ✨ Use Case & Parameter Kreatif

| Parameter | Implementasi |
|---|---|
| **Use case** | Pemandu wisata khusus Tatar Sunda (Jawa Barat & Banten) |
| **Model AI** | Google Gemini (`gemini-2.5-flash`, bisa diganti via `.env`) dengan *function calling* |
| **Gaya bahasa** | 3 persona: 🎋 Kang Jody (Indonesia + sisipan Sunda, default) · 😎 Santai · 🧳 Formal |
| **Kreativitas** | Preset `temperature` & `top_p`: Presisi (0.2) · Seimbang (0.7) · Kreatif (1.1) |
| **Domain** | System prompt membatasi topik ke wisata Sunda, wajib menyelipkan kuliner Sunda & "Catetan Kang Jody" |
| **Integrasi API eksternal** | 🌦️ Open-Meteo (cuaca + prakiraan 3 hari) · 💱 ExchangeRate-API (kurs terbaru) — keduanya gratis tanpa API key |
| **Rekomendasi** | Katalog 24 destinasi Sunda (Ciwidey, Lembang, Garut, Ciletuh, Kampung Naga, Baduy, dll.) (`data/destinations.json`) difilter berdasarkan minat, budget, dan wilayah |
| **Memory** | Bot mengingat nama, kota asal, budget, dan minat pengguna (disimpan di `data/memory.json`) lalu menyuntikkannya ke system prompt |
| **Transparansi** | Setiap pemanggilan tool tampil di UI (argumen + hasil JSON) |
| **Mode demo** | Tanpa API key, aplikasi tetap jalan dengan engine rule-based yang memakai tools yang sama |

## 🏗️ Arsitektur

```
Pengguna ──► Streamlit UI (app.py)
                │  persona, kreativitas, riwayat chat
                ▼
          chatbot/llm.py ──► Gemini API (LLM)
                │                 │ function calling otomatis
                │                 ▼
                │          chatbot/tools.py ──► Open-Meteo / ExchangeRate-API / katalog lokal
                ▼
          chatbot/memory.py ◄──► data/memory.json
```

## 📁 Struktur Proyek

```
jelajahbot/   (aplikasi: Ngalalana)
├── app.py                  # UI Streamlit
├── chatbot/
│   ├── config.py           # persona, preset kreativitas, system prompt
│   ├── llm.py              # GeminiEngine + DemoEngine
│   ├── tools.py            # cuaca, kurs, rekomendasi (function calling)
│   └── memory.py           # memory jangka panjang (JSON)
├── data/destinations.json  # katalog destinasi
├── tests/test_chatbot.py   # unit test (API di-mock)
├── docs/screenshots/       # screenshot UI untuk laporan
├── .vscode/                # konfigurasi VS Code (run, debug, test, ekstensi)
├── .streamlit/config.toml  # tema UI
├── requirements.txt
└── .env.example
```

## 🚀 Cara Menjalankan

**Prasyarat:** Python 3.10+ dan VS Code.

1. Buka folder di VS Code (`File → Open Folder` atau buka `jelajahbot.code-workspace`). Install ekstensi
   yang direkomendasikan saat diminta.
2. Buat virtual environment & install dependency — `Terminal → Run Task → Setup: buat venv & install dependency`,
   atau manual:
   ```bash
   python -m venv .venv
   # Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Salin `.env.example` menjadi `.env`, lalu isi `GEMINI_API_KEY` (gratis di
   [Google AI Studio](https://aistudio.google.com/apikey)).
4. Jalankan: tekan **F5** (pilih *Jalankan JelajahBot*) atau:
   ```bash
   streamlit run app.py
   ```
   Buka http://localhost:8501.
5. Test: `pytest -v` atau `Run Task → Test: pytest`.

> Di Windows, jika VS Code tidak menemukan interpreter, pilih `Python: Select Interpreter → .venv`.

## 💬 Contoh Pertanyaan

- "Nama saya Jody, aku dari Bandung, suka curug dan kuliner" → memory tersimpan
- "Rekomendasi wisata alam murah di Bandung" → tool rekomendasi
- "Kumaha cuaca di Lembang ayeuna?" → API Open-Meteo
- "Wisata budaya Sunda di Garut" → tool rekomendasi
- "Itinerary 2 hari ke Ciwidey budget 1 juta" → LLM + rekomendasi + kuliner

## 🖼️ Screenshot

| Tampilan awal | Rekomendasi + tool | Cuaca | Persona Formal |
|---|---|---|---|
| ![](docs/screenshots/01-home.png) | ![](docs/screenshots/02-rekomendasi.png) | ![](docs/screenshots/03-api.png) | ![](docs/screenshots/04-formal.png) |

## 🛠️ Teknologi

Python · Streamlit · Google Gemini (`google-genai`) · Open-Meteo API · ExchangeRate-API · pytest
