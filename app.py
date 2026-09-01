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
GREEN, GOLD, INK = "#005A36", "#C5A059", "#212529"

STARTERS = [
    "How many leave days can I carry over?",
    "I'm travelling to Dubai — what's my meal budget?",
    "My laptop was stolen, what do I do?",
    "Can I use ChatGPT for a work document?",
]


# ------------------------------------------------------------------ page

st.set_page_config(
    page_title="BIF Handbook Assistant",
    page_icon="📗",
    layout="centered",
)

st.markdown(
    f"""
    <style>
      h1 {{
        color: {GREEN} !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em;
        border-bottom: 3px solid {GOLD};
        padding-bottom: 10px;
      }}
      [data-testid="stChatMessage"] {{
        border: 1px solid #E0E5E1;
        border-radius: 10px;
      }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("BIF Handbook Assistant")
st.caption("Bader Investment Fund · fictional test data · every answer cites its policy section")


# ------------------------------------------------------------------ handbook index

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
    """Split the handbook into {section number: (document code, text)}."""
    docs, sections, current = {}, {}, None

    for line in text.splitlines():
        line = line.strip()

        header = re.match(r"^([A-Z]{2,4}-\d{2})\s+(.+?)\s*\(updated", line)
        if header:
            current = header.group(1)
            docs[current] = tidy(header.group(2))
            continue

        body = re.match(r"^(\d+\.\d+)\s+(.+)$", line)
        if body and current:
            sections[body.group(1)] = (current, body.group(2).strip())

    return docs, sections


DOCS, SECTIONS = build_index(POLICIES)


def cited_sections(answer):
    """Pull [HR-02 2.2, 2.5] out of an answer and look the sections up."""
    found = []
    for doc, nums in re.findall(r"\[([A-Z]{2,4}-\d{2})\s*([0-9.,\s]*)\]", answer):
        for n in re.findall(r"\d+\.\d+", nums):
            if n in SECTIONS:
                found.append((doc, n, SECTIONS[n][1]))
    return found


def show_sources(answer):
    """Render a collapsed 'read the policy' panel under an answer."""
    for doc, n, text in cited_sections(answer):
        title = DOCS.get(doc, doc)
        with st.expander(f"📄  {title} · §{n}"):
            st.markdown(f"**{doc} §{n}**")
            st.write(text)


# ------------------------------------------------------------------ brain

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
    """Yield the reply piece by piece, so it types itself onto the screen."""
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


# ------------------------------------------------------------------ sidebar

with st.sidebar:
    st.subheader("About")
    st.write(
        "This handbook is **entirely fictional**. Bader Investment Fund "
        "does not exist and none of these policies are real."
    )
    st.write(f"Handbook: **{len(POLICIES):,}** characters · **{len(SECTIONS)}** sections")
    st.write(f"Model: `{MODEL}`")

    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.caption(
        "The assistant only sees the handbook text. It has no access to any "
        "real system, file or record."
    )


# ------------------------------------------------------------------ state

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending" not in st.session_state:
    st.session_state.pending = None


# ------------------------------------------------------------------ starters

if not st.session_state.messages:
    st.write("")
    st.markdown("**Try one of these**")
    cols = st.columns(2)
    for i, q in enumerate(STARTERS):
        if cols[i % 2].button(q, key=f"starter_{i}", use_container_width=True):
            st.session_state.pending = q
            st.rerun()
    st.write("")


# ------------------------------------------------------------------ history

for m in st.session_state.messages:
    with st.chat_message(m["role"], avatar="📗" if m["role"] == "assistant" else None):
        st.markdown(m["content"])
        if m["role"] == "assistant":
            show_sources(m["content"])


# ------------------------------------------------------------------ turn

typed = st.chat_input("Ask about leave, expenses, IT, security...")

question = typed or st.session_state.pending
st.session_state.pending = None

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant", avatar="📗"):
        answer = st.write_stream(stream_answer(st.session_state.messages))
        show_sources(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
