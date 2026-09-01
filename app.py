"""
BIF Handbook Assistant — a Streamlit chat app over a fictional employee handbook.

Run locally:   streamlit run app.py
Deployed:      share.streamlit.io, with GEMINI_API_KEY set in Secrets
"""

import streamlit as st
from google import genai
from google.genai import types

from handbook_dummy_data import POLICIES

MODEL = "gemini-3.6-flash"
GREEN, GOLD, INK = "#005A36", "#C5A059", "#212529"


# ------------------------------------------------------------------ page

st.set_page_config(
    page_title="BIF Handbook Assistant",
    page_icon="📗",
    layout="centered",
)

st.markdown(
    f"""
    <style>
      .stApp {{ background-color: #F4F6F4; }}
      h1 {{
        color: {GREEN} !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em;
        border-bottom: 3px solid {GOLD};
        padding-bottom: 10px;
      }}
      [data-testid="stChatMessage"] {{
        background-color: #FFFFFF;
        border: 1px solid #E0E5E1;
        border-radius: 10px;
      }}
      [data-testid="stSidebar"] {{ background-color: #FFFFFF; }}
      .stButton button {{
        background-color: {GREEN};
        color: #FFFFFF;
        border: none;
      }}
      .stButton button:hover {{ background-color: #004429; color: #FFFFFF; }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("BIF Handbook Assistant")
st.caption("Bader Investment Fund · fictional test data · every answer cites its policy section")


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
    """Create the Gemini client once and reuse it."""
    key = st.secrets.get("GEMINI_API_KEY")
    if not key:
        return None
    return genai.Client(api_key=key)


client = get_client()

if client is None:
    st.error(
        "No API key found.\n\n"
        "**Deployed:** app settings → Secrets → add `GEMINI_API_KEY = \"...\"`\n\n"
        "**Local:** create `.streamlit/secrets.toml` with the same line."
    )
    st.stop()


def ask_gemini(messages):
    """Send the whole conversation to Gemini and return the reply text."""
    contents = [
        {
            "role": "user" if m["role"] == "user" else "model",
            "parts": [{"text": m["content"]}],
        }
        for m in messages
    ]

    reply = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM,
            temperature=0.2,
        ),
    )
    return reply.text


# ------------------------------------------------------------------ sidebar

with st.sidebar:
    st.subheader("About")
    st.write(
        "This handbook is **entirely fictional**. Bader Investment Fund "
        "does not exist and none of these policies are real."
    )
    st.write(f"Handbook loaded: **{len(POLICIES):,}** characters")
    st.write(f"Model: `{MODEL}`")

    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.caption(
        "The assistant only sees the handbook text. It has no access to any "
        "real system, file or record."
    )


# ------------------------------------------------------------------ chat

if "messages" not in st.session_state:
    st.session_state.messages = []

if not st.session_state.messages:
    st.info(
        "Try: *how many leave days can I carry over?* · "
        "*I'm travelling to Dubai, what's my meal budget?* · "
        "*my laptop was stolen* · *can I use ChatGPT for a work document?*"
    )

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])


question = st.chat_input("Ask about leave, expenses, IT, security...")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Reading the handbook..."):
            try:
                answer = ask_gemini(st.session_state.messages)
            except Exception as e:
                answer = f"⚠️ **{type(e).__name__}** — {e}"
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
