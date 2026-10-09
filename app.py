"""JelajahBot - UI chatbot berbasis Streamlit.

Jalankan:  streamlit run app.py
"""
import json

import streamlit as st

from chatbot import config
from chatbot.llm import DemoEngine, get_engine
from chatbot.memory import Memory

TOOL_LABEL = {
    "get_weather": "🌦️ Cek cuaca (Open-Meteo)",
    "convert_currency": "💱 Konversi kurs (ExchangeRate-API)",
    "recommend_destinations": "📍 Rekomendasi destinasi (katalog lokal)",
}

st.set_page_config(page_title=config.APP_NAME, page_icon="🧭", layout="centered")

st.markdown(
    """
    <style>
      .hero {padding: 1.1rem 1.3rem; border-radius: 14px; margin-bottom: .8rem;
             background: linear-gradient(120deg, #0f766e 0%, #155e75 60%, #1e3a8a 100%); color: #fff;}
      .hero h1 {margin: 0; font-size: 1.7rem; color: #fff;}
      .hero p {margin: .2rem 0 0; opacity: .9;}
      .badge {display:inline-block; padding:2px 10px; border-radius:999px; font-size:.75rem;
              background: rgba(255,255,255,.18); margin-top:.5rem; margin-right:.3rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
if "engine" not in st.session_state:
    st.session_state.engine = get_engine()
if "memory" not in st.session_state:
    st.session_state.memory = Memory()
if "messages" not in st.session_state:
    st.session_state.messages = []  # list[{"role","content","tools"}]

engine = st.session_state.engine
memory: Memory = st.session_state.memory

# ---------------------------------------------------------------------------
# Sidebar: parameter kreatif
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Pengaturan Bot")
    persona = st.radio(
        "Gaya bahasa",
        list(config.PERSONAS),
        index=list(config.PERSONAS).index(config.DEFAULT_PERSONA),
        format_func=lambda p: f"{config.PERSONAS[p]['emoji']} {p}",
    )
    creativity = st.select_slider(
        "Tingkat kreativitas",
        options=list(config.CREATIVITY),
        value=config.DEFAULT_CREATIVITY,
        help="Mengatur temperature & top_p model.",
    )
    p = config.CREATIVITY[creativity]
    st.caption(f"temperature = {p['temperature']} · top_p = {p['top_p']}")

    st.divider()
    st.subheader("🧠 Memory")
    mem_text = memory.as_text()
    if mem_text:
        st.markdown(mem_text)
    else:
        st.caption("Belum ada. Coba: “Nama saya Jody, aku dari Bandung, suka wisata alam.”")
    col1, col2 = st.columns(2)
    if col1.button("Hapus memory", use_container_width=True):
        memory.clear()
        st.rerun()
    if col2.button("Chat baru", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.caption(f"Engine: **{engine.name}**" + (f" · `{config.GEMINI_MODEL}`" if not isinstance(engine, DemoEngine) else ""))
    if isinstance(engine, DemoEngine):
        st.info("Mode demo aktif. Isi `GEMINI_API_KEY` di `.env` untuk memakai LLM.", icon="💡")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="hero">
      <h1>🧭 {config.APP_NAME}</h1>
      <p>{config.APP_TAGLINE} — cuaca, kurs, rekomendasi & itinerary.</p>
      <span class="badge">{config.PERSONAS[persona]['emoji']} {persona}</span>
      <span class="badge">🎛️ {creativity}</span>
      <span class="badge">🤖 {engine.name}</span>
    </div>
    """,
    unsafe_allow_html=True,
)


def render_tools(tools: list[dict]) -> None:
    for call in tools:
        with st.expander(TOOL_LABEL.get(call["tool"], call["tool"]), expanded=False):
            st.caption("Argumen: " + json.dumps(call["args"], ensure_ascii=False))
            st.json(call["result"], expanded=False)


# Riwayat chat
if not st.session_state.messages:
    with st.chat_message("assistant", avatar="🧭"):
        st.markdown(config.PERSONAS[persona]["greeting"])
    st.caption("Coba salah satu:")
    cols = st.columns(2)
    for i, sp in enumerate(config.SUGGESTED_PROMPTS):
        if cols[i % 2].button(sp, key=f"sp{i}", use_container_width=True):
            st.session_state.pending = sp
            st.rerun()

for m in st.session_state.messages:
    with st.chat_message(m["role"], avatar="🧭" if m["role"] == "assistant" else "🙂"):
        st.markdown(m["content"])
        if m.get("tools"):
            render_tools(m["tools"])

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------
user_msg = st.chat_input("Tanya soal liburan, cuaca, kurs, atau minta itinerary...")
if not user_msg and st.session_state.get("pending"):
    user_msg = st.session_state.pop("pending")

if user_msg:
    with st.chat_message("user", avatar="🙂"):
        st.markdown(user_msg)
    changed = memory.extract(user_msg)

    with st.chat_message("assistant", avatar="🧭"):
        with st.spinner("Sedang berpikir..."):
            try:
                reply = engine.reply(
                    history=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                    user_msg=user_msg,
                    persona=persona,
                    creativity=creativity,
                    memory_text=memory.as_text(),
                )
                text, tools = reply.text, reply.tool_calls
            except Exception as exc:  # error API, kuota, jaringan, dll.
                text, tools = f"⚠️ Terjadi kesalahan saat menghubungi model: `{exc}`", []
        st.markdown(text)
        render_tools(tools)
        if changed:
            st.toast("Memory diperbarui: " + ", ".join(changed), icon="🧠")

    st.session_state.messages += [
        {"role": "user", "content": user_msg},
        {"role": "assistant", "content": text, "tools": tools},
    ]
    if changed:
        st.rerun()
