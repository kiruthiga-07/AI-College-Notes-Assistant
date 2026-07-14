import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import docx
import json
import re
import io

# ---------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------
st.set_page_config(
    page_title="AI College Notes Assistant",
    page_icon="📚",
    layout="wide",
)

# ---------------------------------------------------------
# API KEY SETUP (Streamlit secrets — never hardcode this)
# ---------------------------------------------------------
def get_api_key():
    # 1. Try Streamlit secrets (used on Streamlit Cloud + locally via .streamlit/secrets.toml)
    if "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"]
    return None

api_key = get_api_key()

with st.sidebar:
    st.title("📚 AI College Notes Assistant")
    st.caption("Upload notes → get summaries, ask questions, take quizzes.")

if not api_key:
    st.error(
        "This app isn't configured yet. The site owner needs to add "
        "`GEMINI_API_KEY` under Settings → Secrets on Streamlit Cloud."
    )
    st.stop()

try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-3.5-flash")
except Exception as e:
    st.error(f"Failed to configure Gemini: {e}")
    st.stop()

# ---------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------
if "notes_text" not in st.session_state:
    st.session_state.notes_text = ""
if "summary" not in st.session_state:
    st.session_state.summary = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "quiz" not in st.session_state:
    st.session_state.quiz = None
if "quiz_answers" not in st.session_state:
    st.session_state.quiz_answers = {}
if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False

# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
def extract_text_from_file(uploaded_file):
    """Extract raw text from an uploaded pdf, docx, or txt file."""
    name = uploaded_file.name.lower()
    data = uploaded_file.read()

    if name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        text = ""
        for page in reader.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"
        return text.strip()

    elif name.endswith(".docx"):
        doc = docx.Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs).strip()

    elif name.endswith(".txt"):
        return data.decode("utf-8", errors="ignore").strip()

    else:
        return ""


def call_gemini(prompt, temperature=0.4):
    """Single wrapper around the Gemini call with basic error handling."""
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(temperature=temperature),
        )
        return response.text
    except Exception as e:
        st.error(f"Gemini API error: {e}")
        return None


def generate_summary(text):
    prompt = f"""You are a helpful study assistant. Read the following college notes/material
and rewrite them as clear, simple, well-organized study notes.

Rules:
- Use headings and bullet points.
- Break down complex ideas into simple language, as if explaining to a student seeing the topic for the first time.
- Keep key definitions, formulas, and terms accurate — do not invent facts not present in the source.
- End with a short "Key Takeaways" section (3-5 bullet points).

SOURCE MATERIAL:
\"\"\"
{text[:15000]}
\"\"\"
"""
    return call_gemini(prompt)


def answer_question(question, context, history):
    history_str = ""
    for turn in history[-6:]:
        history_str += f"Student: {turn['q']}\nAssistant: {turn['a']}\n"

    prompt = f"""You are an AI tutor answering a student's question using ONLY the notes provided below.
If the answer isn't contained in the notes, say so honestly, then you may add general knowledge
clearly labeled as "(general knowledge, not from your notes)".

NOTES:
\"\"\"
{context[:15000]}
\"\"\"

CONVERSATION SO FAR:
{history_str}

New question: {question}

Answer clearly and concisely, using simple language.
"""
    return call_gemini(prompt)


def generate_quiz(text, num_questions=5):
    prompt = f"""Create a multiple-choice quiz with exactly {num_questions} questions based on the notes below.

Return ONLY valid JSON (no markdown fences, no extra commentary) in exactly this format:
{{
  "questions": [
    {{
      "question": "...",
      "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
      "correct_answer": "A",
      "explanation": "..."
    }}
  ]
}}

NOTES:
\"\"\"
{text[:15000]}
\"\"\"
"""
    raw = call_gemini(prompt, temperature=0.5)
    if not raw:
        return None

    cleaned = re.sub(r"^```json|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to salvage JSON embedded in extra text
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        st.error("Couldn't parse the quiz. Try generating it again.")
        return None


# ---------------------------------------------------------
# SIDEBAR: FILE UPLOAD
# ---------------------------------------------------------
with st.sidebar:
    st.divider()
    st.subheader("1. Upload your notes")
    uploaded_file = st.file_uploader(
        "PDF, DOCX, or TXT", type=["pdf", "docx", "txt"]
    )

    if uploaded_file is not None:
        if st.button("Process file", use_container_width=True):
            with st.spinner("Extracting text..."):
                text = extract_text_from_file(uploaded_file)
            if not text:
                st.error(
                    "Couldn't extract any text. If this is a scanned/image-based PDF, "
                    "text extraction won't work — try a text-based PDF or DOCX/TXT."
                )
            else:
                st.session_state.notes_text = text
                st.session_state.summary = ""
                st.session_state.chat_history = []
                st.session_state.quiz = None
                st.session_state.quiz_submitted = False
                st.success(f"Extracted {len(text)} characters.")

    if st.session_state.notes_text:
        st.caption(f"✅ Notes loaded ({len(st.session_state.notes_text)} chars)")
        if st.button("Clear notes", use_container_width=True):
            st.session_state.notes_text = ""
            st.session_state.summary = ""
            st.session_state.chat_history = []
            st.session_state.quiz = None
            st.rerun()

# ---------------------------------------------------------
# MAIN AREA: TABS
# ---------------------------------------------------------
st.title("AI College Notes Assistant")

if not st.session_state.notes_text:
    st.info("Upload a document from the sidebar to get started.")
    st.stop()

tab1, tab2, tab3 = st.tabs(["📝 Simple Notes", "💬 Ask Questions", "🧠 Quiz"])

# --- TAB 1: SUMMARY ---
with tab1:
    st.subheader("Simplified Notes")
    if st.button("Generate simple notes"):
        with st.spinner("Generating notes..."):
            summary = generate_summary(st.session_state.notes_text)
        if summary:
            st.session_state.summary = summary

    if st.session_state.summary:
        st.markdown(st.session_state.summary)
        st.download_button(
            "Download notes as .txt",
            st.session_state.summary,
            file_name="simple_notes.txt",
        )
    else:
        st.caption("Click the button above to generate simplified notes from your upload.")

# --- TAB 2: CHAT ---
with tab2:
    st.subheader("Ask about your notes")

    for turn in st.session_state.chat_history:
        with st.chat_message("user"):
            st.write(turn["q"])
        with st.chat_message("assistant"):
            st.write(turn["a"])

    question = st.chat_input("Ask a question about your notes...")
    if question:
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                answer = answer_question(
                    question, st.session_state.notes_text, st.session_state.chat_history
                )
            if answer:
                st.write(answer)
                st.session_state.chat_history.append({"q": question, "a": answer})

    if st.session_state.chat_history and st.button("Clear chat"):
        st.session_state.chat_history = []
        st.rerun()

# --- TAB 3: QUIZ ---
with tab3:
    st.subheader("Test yourself")

    col1, col2 = st.columns([1, 1])
    with col1:
        num_q = st.slider("Number of questions", 3, 10, 5)
    with col2:
        st.write("")
        st.write("")
        if st.button("Generate new quiz"):
            with st.spinner("Building your quiz..."):
                quiz = generate_quiz(st.session_state.notes_text, num_q)
            if quiz and "questions" in quiz:
                st.session_state.quiz = quiz
                st.session_state.quiz_answers = {}
                st.session_state.quiz_submitted = False

    if st.session_state.quiz:
        questions = st.session_state.quiz["questions"]

        with st.form("quiz_form"):
            for i, q in enumerate(questions):
                st.markdown(f"**Q{i+1}. {q['question']}**")
                options = q["options"]
                labels = [f"{k}. {v}" for k, v in options.items()]
                choice = st.radio(
                    f"quiz_q_{i}",
                    options=list(options.keys()),
                    format_func=lambda k, opts=options: f"{k}. {opts[k]}",
                    key=f"radio_{i}",
                    label_visibility="collapsed",
                )
                st.session_state.quiz_answers[i] = choice
                st.divider()

            submitted = st.form_submit_button("Submit quiz")
            if submitted:
                st.session_state.quiz_submitted = True

        if st.session_state.quiz_submitted:
            score = 0
            for i, q in enumerate(questions):
                user_ans = st.session_state.quiz_answers.get(i)
                correct = q["correct_answer"]
                is_correct = user_ans == correct
                score += int(is_correct)

                if is_correct:
                    st.success(f"Q{i+1}: Correct! ({correct}. {q['options'][correct]})")
                else:
                    st.error(
                        f"Q{i+1}: You picked {user_ans}. "
                        f"Correct answer: {correct}. {q['options'][correct]}"
                    )
                st.caption(f"💡 {q['explanation']}")

            st.metric("Your score", f"{score} / {len(questions)}")
    else:
        st.caption("Click **Generate new quiz** to create questions from your notes.")
