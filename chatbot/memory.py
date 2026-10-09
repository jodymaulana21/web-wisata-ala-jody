"""Memory jangka panjang sederhana berbasis file JSON.

Bot menyimpan fakta preferensi pengguna (nama, kota asal, budget, minat)
yang diekstrak dari percakapan, lalu menyuntikkannya ke system prompt
sehingga bot "ingat" walau aplikasi direstart.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

MEMORY_FILE = Path(__file__).resolve().parent.parent / "data" / "memory.json"

INTEREST_WORDS = [
    "pantai", "gunung", "alam", "kuliner", "budaya", "sejarah", "belanja",
    "museum", "danau", "air terjun", "snorkeling", "diving", "camping", "kota",
]

# Pola sederhana (rule-based) untuk ekstraksi fakta dari pesan pengguna
PATTERNS = {
    # Prefix tidak peka huruf besar/kecil, tapi nama/kota harus diawali huruf kapital
    "nama": re.compile(r"\b(?i:nama (?:saya|aku|gue|gw)(?: adalah)?|panggil (?:saya|aku))\s+([A-Z][a-zA-Z]+)"),
    "kota_asal": re.compile(
        r"\b(?i:saya|aku|gue|gw) (?i:dari|tinggal di|domisili(?: di)?)\s+([A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z]+)?)"
    ),
    "budget": re.compile(r"\bbudget(?:nya| saya| aku)?\s*(?:sekitar|maks(?:imal)?|cuma|hanya)?\s*(?:rp\.?\s*)?([\d.,]+\s*(?:rb|ribu|jt|juta|k)?)", re.I),
}


class Memory:
    def __init__(self, path: Path = MEMORY_FILE):
        self.path = path
        self.facts: dict[str, object] = self._load()

    def _load(self) -> dict:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.facts, ensure_ascii=False, indent=2), encoding="utf-8")

    def extract(self, message: str) -> list[str]:
        """Ekstrak fakta dari pesan pengguna. Mengembalikan daftar key yang berubah."""
        changed = []
        for key, pattern in PATTERNS.items():
            m = pattern.search(message)
            if m:
                value = m.group(1).strip().title() if key != "budget" else m.group(1).strip()
                if self.facts.get(key) != value:
                    self.facts[key] = value
                    changed.append(key)

        msg_l = message.lower()
        if re.search(r"\b(suka|senang|hobi|tertarik|pengen|ingin)\b", msg_l):
            found = [w for w in INTEREST_WORDS if w in msg_l]
            if found:
                interests = list(dict.fromkeys(list(self.facts.get("minat", [])) + found))
                if interests != self.facts.get("minat"):
                    self.facts["minat"] = interests
                    changed.append("minat")
        if changed:
            self.save()
        return changed

    def as_text(self) -> str:
        if not self.facts:
            return ""
        label = {"nama": "Nama", "kota_asal": "Kota asal", "budget": "Budget", "minat": "Minat"}
        lines = []
        for k, v in self.facts.items():
            v = ", ".join(v) if isinstance(v, list) else v
            lines.append(f"- {label.get(k, k)}: {v}")
        return "\n".join(lines)

    def clear(self) -> None:
        self.facts = {}
        if self.path.exists():
            self.path.unlink()
