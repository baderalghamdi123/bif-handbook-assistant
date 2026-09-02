"""
BIF Handbook Assistant
A Streamlit chat interface over a fictional employee handbook.

Run locally:   streamlit run app.py
Deployed:      share.streamlit.io, with GEMINI_API_KEY set in Secrets
"""

import html
import re

import streamlit as st
from google import genai
from google.genai import types

from handbook_dummy_data import POLICIES

MODEL = "gemini-3.6-flash"

STARTERS = [
    ("Leave",    "How many leave days can I carry over?"),
    ("Travel",   "I'm travelling to Dubai — what's my meal budget?"),
    ("IT",       "My laptop was stolen, what do I do?"),
    ("Security", "Can I use ChatGPT for a work document?"),
]


# ================================================================== page

st.set_page_config(
    page_title="BIF Handbook Assistant",
    page_icon="📗",
    layout="centered",
    initial_sidebar_state="auto",
)


# ================================================================== design system
#
# Every colour, radius, shadow and typeface lives here as a CSS variable.
# The rest of the stylesheet only ever refers to these names.

TOKENS = """
:root {
  --green:      #005A36;
  --green-700:  #004C2D;
  --green-800:  #003D24;
  --green-050:  #EEF4F0;
  --green-100:  #DCE9E1;
  --green-200:  #C3D9CC;

  --gold:       #C5A059;
  --gold-050:   #FAF5EA;
  --gold-200:   #E8D6AE;

  --ink:        #212529;
  --ink-2:      #4E5A55;
  --ink-3:      #7C8883;
  --ink-4:      #A8B1AD;

  --paper:      #F5F7F5;
  --card:       #FFFFFF;
  --rule:       #E2E7E3;
  --rule-2:     #EDF1EE;

  --amber:      #8A5A12;
  --amber-050:  #FDF5E6;
  --amber-200:  #EFDFC0;

  --r-sm: 8px;  --r-md: 12px;  --r-lg: 16px;

  --sh-sm: 0 1px 2px rgba(20,40,30,.05);
  --sh-md: 0 4px 14px -6px rgba(20,40,30,.14), 0 1px 2px rgba(20,40,30,.05);

  --f-ui:      'DM Sans', system-ui, -apple-system, 'Segoe UI', sans-serif;
  --f-display: 'Newsreader', Georgia, 'Times New Roman', serif;
  --f-mono:    'IBM Plex Mono', ui-monospace, Menlo, Consolas, monospace;
  --f-ar:      'IBM Plex Sans Arabic', 'Segoe UI', Tahoma, sans-serif;
}
"""

STYLES = """
/* ------------------------------------------------ base */
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stSidebar"] { font-family: var(--f-ui); }

[data-testid="stIconMaterial"],
span[data-testid="stIconMaterial"],
.material-symbols-rounded,
.material-symbols-outlined,
[class*="material-symbols"] {
  font-family: 'Material Symbols Rounded', 'Material Symbols Outlined' !important;
}
[data-testid="stAppViewContainer"] { background: var(--paper); }
[data-testid="stHeader"]      { background: transparent; }
[data-testid="stDecoration"]  { display: none; }
#MainMenu, footer             { visibility: hidden; }
.block-container { padding-top: 1.6rem; padding-bottom: 6rem; max-width: 820px; }

/* ------------------------------------------------ header */
.bif-header {
  position: relative; overflow: hidden;
  background: linear-gradient(160deg, var(--green) 0%, var(--green-800) 100%);
  border-radius: var(--r-lg) var(--r-lg) 0 0;
  padding: 26px 28px;
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
}
.bif-header::before {
  content: ""; position: absolute; inset: 0; pointer-events: none;
  background-image: repeating-linear-gradient(135deg, rgba(255,255,255,.035) 0 1px, transparent 1px 14px);
}
.bif-header::after {
  content: ""; position: absolute; right: -80px; top: -120px; width: 320px; height: 320px;
  border-radius: 50%; pointer-events: none;
  background: radial-gradient(closest-side, rgba(197,160,89,.22), transparent);
}
.bif-brand { display: flex; align-items: center; gap: 16px; position: relative; }
.bif-mark {
  width: 48px; height: 48px; border-radius: 10px; flex: none;
  background: rgba(255,255,255,.10); border: 1px solid rgba(255,255,255,.22);
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-weight: 700; font-size: 14px; letter-spacing: .06em;
}
.bif-org {
  color: var(--gold); font-size: 10.5px; font-weight: 600;
  letter-spacing: .16em; text-transform: uppercase; margin-bottom: 3px;
}
.bif-title {
  color: #fff; font-family: var(--f-display); font-size: 30px; font-weight: 500;
  letter-spacing: -.01em; line-height: 1.05;
}
.bif-status {
  position: relative; display: flex; align-items: center; gap: 8px;
  font-family: var(--f-mono); font-size: 11px; letter-spacing: .04em;
  color: rgba(255,255,255,.80); background: rgba(0,0,0,.18);
  border: 1px solid rgba(255,255,255,.14); border-radius: 999px;
  padding: 6px 12px; white-space: nowrap;
}
.bif-status .dot {
  width: 7px; height: 7px; border-radius: 50%; background: #7FD1A6;
  box-shadow: 0 0 0 3px rgba(127,209,166,.25);
}

.bif-strip {
  display: flex; align-items: center; gap: 18px; flex-wrap: wrap;
  background: var(--card); border: 1px solid var(--rule); border-top: 0;
  border-radius: 0 0 var(--r-lg) var(--r-lg);
  padding: 11px 28px; margin-bottom: 26px; box-shadow: var(--sh-sm);
  font-family: var(--f-mono); font-size: 11.5px; letter-spacing: .03em; color: var(--ink-3);
}
.bif-strip b { color: var(--green); font-weight: 500; }
.bif-strip i { width: 1px; height: 14px; background: var(--rule); display: inline-block; }
.bif-strip .tag {
  margin-left: auto; color: var(--amber); background: var(--amber-050);
  border: 1px solid var(--amber-200); border-radius: 999px; padding: 3px 10px;
  font-size: 10.5px; letter-spacing: .06em; text-transform: uppercase;
}

/* ------------------------------------------------ welcome card */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--card); border: 1px solid var(--rule) !important;
  border-radius: var(--r-lg) !important; box-shadow: var(--sh-md); padding: 8px 10px;
}
.welcome-h {
  font-family: var(--f-display); font-size: 26px; font-weight: 500;
  color: var(--ink); letter-spacing: -.01em; line-height: 1.15; margin: 2px 0 6px;
}
.welcome-p { color: var(--ink-2); font-size: 14.5px; line-height: 1.6; max-width: 58ch; margin: 0 0 16px; }
.starter-cat {
  font-family: var(--f-mono); font-size: 10.5px; letter-spacing: .12em;
  text-transform: uppercase; color: var(--ink-3); margin: 4px 0 6px 2px;
}

.stButton > button {
  width: 100%; text-align: left; justify-content: flex-start;
  background: var(--card); color: var(--ink);
  border: 1px solid var(--rule); border-radius: var(--r-md);
  padding: 14px 16px; min-height: 56px;
  font-weight: 500; font-size: 14px; line-height: 1.35;
  box-shadow: var(--sh-sm);
  transition: transform .12s ease, border-color .12s ease, box-shadow .12s ease, background .12s ease;
}
.stButton > button:hover {
  border-color: var(--green); color: var(--green); background: var(--green-050);
  transform: translateY(-1px); box-shadow: var(--sh-md);
}
.stButton > button:active { transform: translateY(0); }
.stButton > button:focus-visible { outline: 2px solid var(--green); outline-offset: 2px; }

/* ------------------------------------------------ chat */
[data-testid="stChatMessage"] {
  background: var(--card); border: 1px solid var(--rule); border-radius: var(--r-lg);
  padding: 16px 20px; margin-bottom: 10px; box-shadow: var(--sh-sm);
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
  background: var(--green-050); border-color: var(--green-100);
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarCustom"]) {
  border-left: 3px solid var(--gold);
}
[data-testid="stChatMessage"] p { font-size: 15px; line-height: 1.65; color: var(--ink); }
[data-testid="stChatMessageAvatarUser"] { background: var(--green) !important; color: #fff !important; }

.answer-rtl {
  direction: rtl; text-align: right; font-family: var(--f-ar);
  font-size: 16px; line-height: 1.9; color: var(--ink);
}

.chips { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0 4px; }
.chip {
  display: inline-flex; align-items: center; gap: 6px;
  font-family: var(--f-mono); font-size: 11px; letter-spacing: .03em;
  color: var(--green-700); background: var(--green-050);
  border: 1px solid var(--green-200); border-radius: 999px; padding: 4px 11px;
}
.chip::before { content: ""; width: 5px; height: 5px; border-radius: 50%; background: currentColor; opacity: .7; }
.chip.contact { color: var(--amber); background: var(--amber-050); border-color: var(--amber-200); }

/* ------------------------------------------------ source panel */
[data-testid="stExpander"] {
  border: 1px solid var(--rule) !important; border-radius: var(--r-md) !important;
  background: #FBFCFB; margin-top: 8px; overflow: hidden;
}
[data-testid="stExpander"] summary { padding: 10px 14px; }
[data-testid="stExpander"] summary:hover { background: var(--green-050); }
[data-testid="stAppViewContainer"] > .main [data-testid="stExpander"] summary p,
.block-container [data-testid="stExpander"] summary p {
  font-family: var(--f-mono) !important; font-size: 12px !important;
  letter-spacing: .03em; color: var(--green-700) !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary p {
  font-family: var(--f-mono) !important; font-size: 11.5px !important;
  letter-spacing: .02em; color: var(--ink-2) !important;
}
.src { padding: 4px 2px 6px; }
.src-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 8px; }
.src-code {
  font-family: var(--f-mono); font-size: 11px; letter-spacing: .05em; color: var(--green);
  background: var(--green-050); border: 1px solid var(--green-200); border-radius: 4px; padding: 2px 7px;
}
.src-title { font-size: 13px; font-weight: 600; color: var(--ink-2); }
.src-quote {
  margin: 0; padding: 10px 14px; border-left: 3px solid var(--gold);
  background: var(--gold-050); border-radius: 0 8px 8px 0;
  font-family: var(--f-display); font-size: 15.5px; line-height: 1.6; color: var(--ink);
}
.src-quote.rtl { direction: rtl; text-align: right; font-family: var(--f-ar); border-left: 0; border-right: 3px solid var(--gold); border-radius: 8px 0 0 8px; }

/* ------------------------------------------------ input */
[data-testid="stChatInput"] {
  background: var(--card); border: 1.5px solid var(--rule); border-radius: 14px; box-shadow: var(--sh-md);
}
[data-testid="stChatInput"]:focus-within {
  border-color: var(--green); box-shadow: 0 0 0 4px rgba(0,90,54,.10), var(--sh-md);
}
[data-testid="stChatInput"] textarea { font-family: var(--f-ui); font-size: 15px; }
[data-testid="stBottom"] > div { background: var(--paper); }

/* ------------------------------------------------ sidebar */
[data-testid="stSidebar"] { background: var(--card); border-right: 1px solid var(--rule); }
[data-testid="stSidebarContent"] { padding-top: 1.2rem; }
.sb-brand {
  display: flex; align-items: center; gap: 12px;
  padding: 4px 2px 16px; border-bottom: 1px solid var(--rule); margin-bottom: 16px;
}
.sb-mark {
  width: 36px; height: 36px; border-radius: 8px; background: var(--green); color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 12px; letter-spacing: .06em;
}
.sb-org  { font-size: 10px; font-weight: 600; letter-spacing: .14em; text-transform: uppercase; color: var(--gold); }
.sb-title { font-family: var(--f-display); font-size: 18px; color: var(--ink); line-height: 1.1; }
.sb-label {
  font-family: var(--f-mono); font-size: 10.5px; letter-spacing: .14em;
  text-transform: uppercase; color: var(--ink-3); margin: 6px 0 8px 2px;
}
.sb-meta { font-size: 12.5px; color: var(--ink-2); line-height: 1.7; margin-bottom: 8px; }
.sb-meta b { color: var(--ink); font-weight: 600; }
.sb-foot { font-size: 11.5px; color: var(--ink-4); line-height: 1.6; margin-top: 14px; }
[data-testid="stSidebar"] [data-testid="stExpander"] { background: var(--card); margin-top: 6px; }
.sec   { padding: 8px 0; border-bottom: 1px solid var(--rule-2); }
.sec:last-child { border-bottom: 0; }
.sec-n { font-family: var(--f-mono); font-size: 10.5px; color: var(--green); margin-right: 6px; }
.sec-t { font-size: 12.5px; color: var(--ink-2); line-height: 1.55; }
[data-testid="stSidebar"] .stButton > button {
  min-height: 40px; padding: 9px 14px; text-align: center; justify-content: center; font-size: 13px;
}

/* ------------------------------------------------ streaming */
.thinking { font-family: var(--f-mono); font-size: 12px; color: var(--ink-3); letter-spacing: .04em; }
.cursor {
  display: inline-block; width: 2px; height: 1em; background: var(--green);
  vertical-align: -2px; margin-left: 2px; animation: blink 1s steps(2) infinite;
}
@keyframes blink { 50% { opacity: 0; } }

/* ------------------------------------------------ footer */
.bif-foot {
  text-align: center; font-family: var(--f-mono); font-size: 11px;
  letter-spacing: .04em; color: var(--ink-4); margin-top: 28px;
}

@media (max-width: 640px) {
  .bif-header { padding: 20px; }
  .bif-title  { font-size: 24px; }
  .bif-status { display: none; }
  .bif-strip .tag { margin-left: 0; }
}
@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
}
"""

st.html(
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?'
    'family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700'
    '&family=Newsreader:opsz,wght@6..72,400;6..72,500'
    '&family=IBM+Plex+Mono:wght@400;500'
    '&family=IBM+Plex+Sans+Arabic:wght@400;500&display=swap" rel="stylesheet">'
    f"<style>{TOKENS}{STYLES}</style>"
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
TEAM_COUNT = sum(1 for line in EXTRAS.get("HR-09", []) if ", extension" in line.lower())


# ================================================================== text helpers

ARABIC = re.compile(r"[\u0600-\u06FF]")


def is_arabic(text):
    return bool(ARABIC.search(text))


def render_text(text):
    """Markdown for Latin text; a right-to-left block for Arabic."""
    if is_arabic(text):
        safe = html.escape(text).replace("\n", "<br>")
        st.html(f'<div class="answer-rtl">{safe}</div>')
    else:
        st.markdown(text)


CITE = re.compile(r"\[([A-Z]{2,4}-\d{2})\s*([0-9.,\s]*)\]")


def split_citation(answer):
    """Pull the trailing [HR-02 2.2] (or [HR-09]) out of an answer."""
    refs = []
    for doc, nums in CITE.findall(answer):
        found = re.findall(r"\d+\.\d+", nums)
        refs += [(doc, n) for n in found] if found else [(doc, None)]
    body = CITE.sub("", answer).strip()
    return body, refs


def render_answer(answer):
    """Answer body → citation chips → a source panel quoting the policy."""
    body, refs = split_citation(answer)
    render_text(body)

    if refs:
        chips = []
        for doc, n in refs:
            if n:
                chips.append(f'<span class="chip">{doc} §{n}</span>')
            else:
                chips.append(f'<span class="chip contact">{doc} · contact</span>')
        st.html(f'<div class="chips">{"".join(chips)}</div>')

    for doc, n in refs:
        if n and n in SECTIONS:
            title = DOCS.get(doc, doc)
            text = SECTIONS[n][1]
            rtl = " rtl" if is_arabic(text) else ""
            with st.expander(f"Read the policy  ·  {title} §{n}"):
                st.html(
                    f'<div class="src">'
                    f'  <div class="src-head">'
                    f'    <span class="src-code">{doc} §{n}</span>'
                    f'    <span class="src-title">{html.escape(title)}</span>'
                    f'  </div>'
                    f'  <blockquote class="src-quote{rtl}">{html.escape(text)}</blockquote>'
                    f'</div>'
                )


# ================================================================== brain

SYSTEM = f"""You are the Bader Investment Fund handbook assistant.
You answer employee questions using ONLY the handbook at the end of this message.

How to answer:
- Lead with the direct answer in one short sentence. Add conditions only if they matter.
- Keep it under 60 words unless the question genuinely needs more.
- Give exact numbers, extensions and deadlines. Never round or approximate.
- End every answer with a citation on its own line, in exactly this format:  [HR-02 2.2]
  If you used more than one section:  [HR-02 2.2, 2.5]
  If you are pointing the employee to a team instead:  [HR-09]
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


def stream_answer(client, messages):
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


# ================================================================== state

if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending" not in st.session_state:
    st.session_state.pending = None


# ================================================================== sidebar

with st.sidebar:
    st.html(
        '<div class="sb-brand">'
        '  <div class="sb-mark">BIF</div>'
        '  <div><div class="sb-org">Bader Investment Fund</div>'
        '       <div class="sb-title">Policy Portal</div></div>'
        '</div>'
    )

    st.html('<div class="sb-label">Browse the handbook</div>')

    for code, title in DOCS.items():
        with st.expander(f"{code}  ·  {title}"):
            rows = []
            for num, text in BY_DOC.get(code, []):
                rows.append(
                    f'<div class="sec"><span class="sec-n">§{num}</span>'
                    f'<span class="sec-t">{html.escape(text)}</span></div>'
                )
            for line in EXTRAS.get(code, []):
                rows.append(f'<div class="sec"><span class="sec-t">{html.escape(line)}</span></div>')
            st.html("".join(rows))

    st.html('<div class="sb-label" style="margin-top:18px">Session</div>')

    turns = sum(1 for m in st.session_state.messages if m["role"] == "user")
    st.html(
        f'<div class="sb-meta">'
        f'<b>{turns}</b> question{"s" if turns != 1 else ""} this session<br>'
        f'Model <b>{MODEL}</b><br>'
        f'Handbook <b>{len(POLICIES):,}</b> characters'
        f'</div>'
    )

    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.html(
        '<div class="sb-foot">Entirely fictional. Bader Investment Fund does not exist '
        'and none of these policies are real. The assistant sees only this handbook text — '
        'no real system, file or record.</div>'
    )


# ================================================================== header

st.html(
    f"""
    <div class="bif-header">
      <div class="bif-brand">
        <div class="bif-mark">BIF</div>
        <div>
          <div class="bif-org">Bader Investment Fund</div>
          <div class="bif-title">Handbook Assistant</div>
        </div>
      </div>
      <div class="bif-status"><span class="dot"></span>Connected · {MODEL}</div>
    </div>
    <div class="bif-strip">
      <span><b>{len(DOCS)}</b> documents</span><i></i>
      <span><b>{len(SECTIONS)}</b> sections</span><i></i>
      <span><b>{TEAM_COUNT}</b> teams</span>
      <span class="tag">Fictional test data</span>
    </div>
    """
)


# ================================================================== api key guard

client = get_client()

if client is None:
    st.error(
        "**No API key found.**\n\n"
        "Deployed: Manage app → Settings → Secrets → add `GEMINI_API_KEY = \"...\"`\n\n"
        "Local: create `.streamlit/secrets.toml` with the same line."
    )
    st.stop()


# ================================================================== welcome

if not st.session_state.messages:
    with st.container(border=True):
        st.html(
            '<div class="welcome-h">What do you need to know?</div>'
            '<p class="welcome-p">Ask about working hours, leave, expenses, travel, IT, '
            'security, or who to contact. Every answer cites the section it came from — '
            'and says so plainly when the handbook does not cover your question.</p>'
        )
        cols = st.columns(2)
        for i, (cat, q) in enumerate(STARTERS):
            with cols[i % 2]:
                st.html(f'<div class="starter-cat">{cat}</div>')
                if st.button(q, key=f"starter_{i}", use_container_width=True):
                    st.session_state.pending = q
                    st.rerun()


# ================================================================== history

for i, m in enumerate(st.session_state.messages):
    if m["role"] == "user":
        with st.chat_message("user"):
            render_text(m["content"])
    else:
        with st.chat_message("assistant", avatar="📗"):
            render_answer(m["content"])
            st.feedback("thumbs", key=f"fb_{i}")


# ================================================================== turn

typed = st.chat_input("Ask about leave, expenses, IT, security…")

question = typed or st.session_state.pending
st.session_state.pending = None

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        render_text(question)

    with st.chat_message("assistant", avatar="📗"):
        slot = st.empty()
        slot.html('<div class="thinking">Reading the handbook…</div>')

        answer = ""
        for piece in stream_answer(client, st.session_state.messages):
            answer += piece
            slot.markdown(answer + '<span class="cursor"></span>', unsafe_allow_html=True)

        slot.empty()
        render_answer(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.rerun()


st.html(
    '<div class="bif-foot">Fictional test data · Bader Investment Fund does not exist · '
    'Built as a learning project</div>'
)
