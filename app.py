"""Ngalalana - Pemandu Wisata Tatar Sunda ala Jody Maulana (UI Streamlit).

Jalankan:  streamlit run app.py
"""
import json

import streamlit as st

from chatbot import config
from chatbot.llm import DemoEngine, get_engine
from chatbot.memory import Memory

BOT_AVATAR = "🎋"
USER_AVATAR = "🙂"
TOOL_LABEL = {
    "get_weather": "🌦️ Cek cuaca (Open-Meteo)",
    "convert_currency": "💱 Konversi kurs (ExchangeRate-API)",
    "recommend_destinations": "📍 Rekomendasi wisata Sunda (katalog Kang Jody)",
}

st.set_page_config(page_title=f"{config.APP_NAME} · Wisata Sunda", page_icon=BOT_AVATAR, layout="centered")

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@600;800&display=swap');
      .hero {position: relative; overflow: hidden; padding: 1.3rem 1.4rem 1.1rem; border-radius: 16px;
             margin-bottom: .9rem; color: #fdf8ec;
             background:
               repeating-linear-gradient(135deg, rgba(255,255,255,.05) 0 10px, transparent 10px 20px),
               linear-gradient(120deg, #1f4d2b 0%, #2f6b3a 45%, #7a5a1f 100%);}
      .hero::after {content: "🎋"; position: absolute; right: 14px; top: 6px; font-size: 4.2rem; opacity: .22;}
      .hero h1 {margin: 0; font-family: 'Fraunces', serif; font-weight: 800; font-size: 2rem;
                color: #fdf8ec; letter-spacing: .3px;}
      .hero .tag {margin: .15rem 0 0; font-size: 1rem; opacity: .95;}
      .hero .motto {margin: .35rem 0 0; font-size: .82rem; font-style: italic; opacity: .8;}
      .badge {display:inline-block; padding:2px 10px; border-radius:999px; font-size:.75rem;
              background: rgba(253,248,236,.18); margin-top:.6rem; margin-right:.3rem;}
      .author {text-align:center; font-size:.8rem; color:#6b6248; margin-top: 1.4rem;}
      .author b {color:#2f6b3a;}
      section[data-testid="stSidebar"] h2 {font-family: 'Fraunces', serif;}
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
    st.header("⚙️ Setelan Ngalalana")
    persona = st.radio(
        "Gaya basa (gaya bahasa)",
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
    st.subheader("🧠 Émut (Memory)")
    mem_text = memory.as_text()
    if mem_text:
        st.markdown(mem_text)
    else:
        st.caption("Teu acan aya. Coba: “Nama saya Jody, aku dari Bandung, suka curug dan kuliner.”")
    col1, col2 = st.columns(2)
    if col1.button("Hapus memory", use_container_width=True):
        memory.clear()
        st.rerun()
    if col2.button("Obrolan anyar", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.caption(f"Engine: **{engine.name}**" + (f" · `{config.GEMINI_MODEL}`" if not isinstance(engine, DemoEngine) else ""))
    if isinstance(engine, DemoEngine):
        st.info("Mode demo aktif. Isi `GEMINI_API_KEY` di `.env` untuk memakai LLM.", icon="💡")
    st.caption(f"Dirancang ku **{config.APP_AUTHOR}** · Bandung")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="hero">
      <h1>{config.APP_NAME}</h1>
      <p class="tag">{config.APP_TAGLINE}</p>
      <p class="motto">“{config.APP_MOTTO}”</p>
      <span class="badge">{config.PERSONAS[persona]['emoji']} {persona}</span>
      <span class="badge">🎛️ {creativity}</span>
      <span class="badge">🤖 {engine.name}</span>
    </div>
    """,
    unsafe_allow_html=True,
)


def render_tools(tools: list) -> None:
    for call in tools:
        with st.expander(TOOL_LABEL.get(call["tool"], call["tool"]), expanded=False):
            st.caption("Argumen: " + json.dumps(call["args"], ensure_ascii=False))
            st.json(call["result"], expanded=False)


# Riwayat chat
if not st.session_state.messages:
    with st.chat_message("assistant", avatar=BOT_AVATAR):
        st.markdown(config.PERSONAS[persona]["greeting"])
    st.caption("Mangga cobian salah sahiji:")
    cols = st.columns(2)
    for i, sp in enumerate(config.SUGGESTED_PROMPTS):
        if cols[i % 2].button(sp, key=f"sp{i}", use_container_width=True):
            st.session_state.pending = sp
            st.rerun()

for m in st.session_state.messages:
    with st.chat_message(m["role"], avatar=BOT_AVATAR if m["role"] == "assistant" else USER_AVATAR):
        st.markdown(m["content"])
        if m.get("tools"):
            render_tools(m["tools"])

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------
user_msg = st.chat_input("Tanyakeun wisata Sunda, cuaca, kurs, atanapi itinerary...")
if not user_msg and st.session_state.get("pending"):
    user_msg = st.session_state.pop("pending")

if user_msg:
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(user_msg)
    changed = memory.extract(user_msg)

    with st.chat_message("assistant", avatar=BOT_AVATAR):
        with st.spinner("Sakedap, nuju mikir..."):
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
                text, tools = f"⚠️ Punten, aya kasalahan nalika ngahubungi model: `{exc}`", []
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

st.markdown(
    f'<div class="author">🎋 <b>{config.APP_NAME}</b> — dijieun ku {config.APP_AUTHOR} · '
    "Tugas Proyek Chatbot AI</div>",
    unsafe_allow_html=True,
)
