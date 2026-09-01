"""
BIF Handbook Assistant — a Streamlit chat app over a fictional employee handbook.

Run locally:   streamlit run app.py
Deployed:      share.streamlit.io, with GEMINI_API_KEY set in Secrets
"""

import re

import streamlit as st
from google import genai
from google.genai import types

from handbook_dummy_data import POLICIES

MODEL = "gemini-3.6-flash"
GREEN, GREEN_DARK, GOLD, INK = "#005A36", "#004429", "#C5A059", "#212529"

STARTERS = [
    "How many leave days can I carry over?",
    "I'm travelling to Dubai — what's my meal budget?",
    "My laptop was stolen, what do I do?",
    "Can I use ChatGPT for a work document?",
]


# ================================================================== page

st.set_page_config(
    page_title="BIF Handbook Assistant",
    page_icon="📗",
    layout="centered",
)

st.markdown(
    f"""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">

    <style>
      html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}

      .block-container {{ padding-top: 2rem; }}

      /* ---------- header band ---------- */
      .hero {{
        background: linear-gradient(135deg, {GREEN} 0%, {GREEN_DARK} 100%);
        border-bottom: 4px solid {GOLD};
        border-radius: 12px 12px 0 0;
        padding: 22px 26px;
        display: flex;
        align-items: center;
        gap: 16px;
        margin-bottom: 0;
      }}
      .hero-mark {{
        width: 46px; height: 46px; flex: none;
        border-radius: 8px;
        background: rgba(255,255,255,.14);
        border: 1px solid rgba(255,255,255,.28);
        display: flex; align-items: center; justify-content: center;
        color: #fff; font-weight: 700; font-size: 14px; letter-spacing: .02em;
      }}
      .hero-org {{
        color: {GOLD}; font-size: 11px; font-weight: 600;
        letter-spacing: .14em; text-transform: uppercase;
      }}
      .hero-title {{
        color: #fff; font-size: 24px; font-weight: 700;
        letter-spacing: -.02em; line-height: 1.2;
      }}

      /* ---------- stat strip ---------- */
      .stats {{
        background: #FFFFFF;
        border: 1px solid #E0E5E1;
        border-top: none;
        border-radius: 0 0 12px 12px;
        padding: 10px 26px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11.5px;
        letter-spacing: .04em;
        color: #6B7370;
        margin-bottom: 22px;
      }}
      .stats b {{ color: {GREEN}; font-weight: 500; }}

      /* ---------- chat bubbles ---------- */
      [data-testid="stChatMessage"] {{
        border: 1px solid #E0E5E1;
        border-radius: 12px;
        padding: 4px 8px;
        margin-bottom: 6px;
      }}

      /* ---------- citation chips ---------- */
      .chips {{ margin: 6px 0 2px; }}
      .chip {{
        display: inline-block;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
        letter-spacing: .03em;
        color: {GREEN};
        background: #E8F0EB;
        border: 1px solid #C8DCD0;
        border-radius: 999px;
        padding: 3px 10px;
        margin-right: 6px;
      }}

      /* ---------- buttons ---------- */
      .stButton button {{
        border: 1px solid #D6DCD8;
        background: #FFFFFF;
        color: {INK};
        font-weight: 500;
        text-align: left;
      }}
      .stButton button:hover {{
        border-color: {GREEN};
        color: {GREEN};
        background: #F2F7F4;
      }}

      /* ---------- sidebar ---------- */
      [data-testid="stSidebar"] h3 {{ color: {GREEN}; }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ================================================================== handbook index

SMALL = {"to", "and", "of", "the", "for"}
ACRONYMS = {"It": "IT", "Ai": "AI", "Bif": "BIF", "Hr": "HR"}


def tidy(title):
    """ANNUAL LEAVE & TIME OFF  ->  Annual Leave & Time Off"""
    words = []
    for i, w in enumerate(title.strip().title().split()):
        w = ACRONYMS.get(w, w)
        if i and w.lower() in SMALL:
            w = w.lower()
        words.append(w)
    return " ".join(words)


@st.cache_data
def build_index(text):
    """
    Split the handbook into:
      docs      {code: title}
      sections  {"2.2": (code, text)}
      by_doc    {code: [(number, text), ...]}
      extras    {code: [unnumbered lines]}     e.g. the HR-09 contact list
    """
    docs, sections, by_doc, extras = {}, {}, {}, {}
    current = None

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        header = re.match(r"^([A-Z]{2,4}-\d{2})\s+(.+?)\s*\(updated", line)
        if header:
            current = header.group(1)
            docs[current] = tidy(header.group(2))
            by_doc[current] = []
            extras[current] = []
            continue

        if not current:
            continue

        body = re.match(r"^(\d+\.\d+)\s+(.+)$", line)
        if body:
            num, content = body.group(1), body.group(2).strip()
            sections[num] = (current, content)
            by_doc[current].append((num, content))
        else:
            extras[current].append(line)

    return docs, sections, by_doc, extras


DOCS, SECTIONS, BY_DOC, EXTRAS = build_index(POLICIES)
TEAM_COUNT = sum(1 for line in EXTRAS.get("HR-09", []) if "extension" in line.lower())


# ================================================================== header

st.markdown(
    f"""
    <div class="hero">
      <div class="hero-mark">BIF</div>
      <div>
        <div class="hero-org">Bader Investment Fund</div>
        <div class="hero-title">Handbook Assistant</div>
      </div>
    </div>
    <div class="stats">
      <b>{len(DOCS)}</b> documents &nbsp;·&nbsp;
      <b>{len(SECTIONS)}</b> sections &nbsp;·&nbsp;
      <b>{TEAM_COUNT}</b> teams &nbsp;·&nbsp;
      fictional test data
    </div>
    """,
    unsafe_allow_html=True,
)


# ================================================================== citations

def split_citation(answer):
    """Separate the trailing [HR-02 2.2] from the answer body."""
    refs = []
    for doc, nums in re.findall(r"\[([A-Z]{2,4}-\d{2})\s*([0-9.,\s]*)\]", answer):
        found = re.findall(r"\d+\.\d+", nums)
        if found:
            refs += [(doc, n) for n in found]
        else:
            refs.append((doc, None))

    body = re.sub(r"\[([A-Z]{2,4}-\d{2})\s*([0-9.,\s]*)\]", "", answer).strip()
    return body, refs


def render_answer(answer):
    """Answer text, then citation chips, then a panel with the policy itself."""
    body, refs = split_citation(answer)
    st.markdown(body)

    if refs:
        chips = "".join(
            f'<span class="chip">{doc}{" §" + n if n else ""}</span>' for doc, n in refs
        )
        st.markdown(f'<div class="chips">{chips}</div>', unsafe_allow_html=True)

    for doc, n in refs:
        if n and n in SECTIONS:
            with st.expander(f"📄  {DOCS.get(doc, doc)} · §{n}"):
                st.write(SECTIONS[n][1])


# ================================================================== brain

SYSTEM = f"""You are the Bader Investment Fund handbook assistant.
You answer employee questions using ONLY the handbook at the end of this message.

How to answer:
- Lead with the direct answer in one short sentence. Add conditions only if they matter.
- Keep it under 60 words unless the question genuinely needs more.
- Give exact numbers, extensions and deadlines. Never round or approximate.
- End every answer with a citation on its own line, in exactly this format:  [HR-02 2.2]
  If you used more than one section:  [HR-02 2.2, 2.5]
- If the handbook does not cover the question, say so plainly, do not guess, and
  point them to the right team from HR-09.
- If the employee states something incorrect, correct them.
- Reply in the same language the employee wrote in.
- This is a conversation. Use what was said earlier to understand follow-up questions.

HANDBOOK:
{POLICIES}"""


@st.cache_resource
def get_client():
    key = st.secrets.get("GEMINI_API_KEY")
    return genai.Client(api_key=key) if key else None


client = get_client()

if client is None:
    st.error(
        "No API key found.\n\n"
        "**Deployed:** Manage app → Settings → Secrets → "
        "add `GEMINI_API_KEY = \"...\"`\n\n"
        "**Local:** create `.streamlit/secrets.toml` with the same line."
    )
    st.stop()


def stream_answer(messages):
    """Yield the reply piece by piece."""
    contents = [
        {
            "role": "user" if m["role"] == "user" else "model",
            "parts": [{"text": m["content"]}],
        }
        for m in messages
    ]

    try:
        stream = client.models.generate_content_stream(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM,
                temperature=0.2,
            ),
        )
        for chunk in stream:
            if chunk.text:
                yield chunk.text

    except Exception as e:
        yield f"\n\n⚠️ **{type(e).__name__}** — {e}"


# ================================================================== sidebar

with st.sidebar:
    st.markdown("### The handbook")
    st.caption("Read any policy directly.")

    for code, title in DOCS.items():
        with st.expander(f"{code} · {title}"):
            for num, text in BY_DOC.get(code, []):
                st.markdown(f"**§{num}** &nbsp; {text}")
            for line in EXTRAS.get(code, []):
                st.markdown(f"- {line}")

    st.divider()

    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.caption(
        f"Model `{MODEL}` · {len(POLICIES):,} characters. "
        "Entirely fictional — Bader Investment Fund does not exist."
    )


# ================================================================== state

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending" not in st.session_state:
    st.session_state.pending = None


# ================================================================== welcome

if not st.session_state.messages:
    with st.container(border=True):
        st.markdown("#### Ask about any BIF policy")
        st.caption(
            "Working hours, leave, expenses, travel, IT, security, and who to "
            "contact. Every answer quotes the section it came from — and says "
            "so plainly when the handbook does not cover your question."
        )
        st.write("")
        cols = st.columns(2)
        for i, q in enumerate(STARTERS):
            if cols[i % 2].button(q, key=f"starter_{i}", use_container_width=True):
                st.session_state.pending = q
                st.rerun()


# ================================================================== history

for m in st.session_state.messages:
    if m["role"] == "user":
        with st.chat_message("user"):
            st.markdown(m["content"])
    else:
        with st.chat_message("assistant", avatar="📗"):
            render_answer(m["content"])


# ================================================================== turn

typed = st.chat_input("Ask about leave, expenses, IT, security...")

question = typed or st.session_state.pending
st.session_state.pending = None

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant", avatar="📗"):
        slot = st.empty()
        answer = ""

        for piece in stream_answer(st.session_state.messages):
            answer += piece
            slot.markdown(answer + " ▌")

        slot.empty()
        render_answer(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
