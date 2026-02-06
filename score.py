import streamlit as st
from groq import Groq
from dotenv import load_dotenv
import os
import re

# ---------- LOAD API KEY ----------
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    st.error("Groq API key not found in .env")
    st.stop()

client = Groq(api_key=api_key)

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="Exam Answer Evaluator",
    page_icon="📘",
    layout="wide"
)

# ---------- HEADER ----------
st.markdown("""
<h1 style='text-align:center;'>📘 AI-Based Exam Evaluation System</h1>
<p style='text-align:center;color:gray;'>
Upload Answer Key & Student Answers to auto-evaluate
</p>
<hr>
""", unsafe_allow_html=True)

# ---------- SIDEBAR ----------
with st.sidebar:
    st.header("📂 Upload Files")
    st.info("""
    🔹 Upload **2 TXT files only**
    - Answer Key → filename must contain **answer**
    - Student Answers → filename must contain **student**
    """)
    uploaded_files = st.file_uploader(
        "Select files",
        type=["txt"],
        accept_multiple_files=True
    )

    evaluate_btn = st.button("📊 Start Evaluation", use_container_width=True)

# ---------- FUNCTIONS ----------
def extract_answer_key(text):
    pattern = r"Q(\d+)\s*\((\d+)\s*marks\):(.*?)(?=Q\d+|\Z)"
    answers = {}
    for qno, marks, block in re.findall(pattern, text, re.S):
        lines = block.strip().split("\n")
        answers[qno] = {
            "question": lines[0].strip(),
            "answer": " ".join(lines[1:]).strip(),
            "marks": int(marks)
        }
    return answers


def extract_students(text):
    questions = {}
    q_blocks = re.findall(r"Q(\d+):(.*?)(?=Q\d+|\Z)", text, re.S)
    for qno, block in q_blocks:
        students = {}
        for i in range(1, 4):
            match = re.search(
                rf"Student {i}:(.*?)(Student {i+1}:|\Z)",
                block,
                re.S
            )
            students[f"Student {i}"] = match.group(1).strip() if match else ""
        questions[qno] = students
    return questions


def evaluate(question, correct, student, max_marks):
    prompt = f"""
You are a strict university examiner.

Question: {question}
Correct Answer: {correct}
Student Answer: {student}

Respond ONLY in this format:
Marks: X/{max_marks}
Verdict: Correct or Partially Correct or Wrong
Reason: one line
"""
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content.strip()

# ---------- MAIN LOGIC ----------
if uploaded_files and evaluate_btn:

    if len(uploaded_files) != 2:
        st.error("❌ Please upload exactly **2 files**")
        st.stop()

    ak_file = next((f for f in uploaded_files if "answer" in f.name.lower()), None)
    st_file = next((f for f in uploaded_files if "student" in f.name.lower()), None)

    if not ak_file or not st_file:
        st.error("❌ Filenames must contain **answer** and **student**")
        st.stop()

    answer_key_text = ak_file.read().decode("utf-8")
    student_text = st_file.read().decode("utf-8")

    with st.spinner("🧠 Evaluating answers... Please wait"):
        answer_key = extract_answer_key(answer_key_text)
        student_answers = extract_students(student_text)

        scores = {f"Student {i}": 0 for i in range(1, 4)}
        max_total = sum(v["marks"] for v in answer_key.values())

        st.success("✅ Evaluation Completed")

        # ---------- STUDENT TABS ----------
        tabs = st.tabs(["👨‍🎓 Student 1", "👩‍🎓 Student 2", "👨‍🎓 Student 3"])

        for idx, student in enumerate(scores.keys()):
            with tabs[idx]:
                st.subheader(f"{student} Performance")

                for qno, data in answer_key.items():
                    ans = student_answers.get(qno, {}).get(student, "")
                    result = evaluate(
                        data["question"],
                        data["answer"],
                        ans,
                        data["marks"]
                    )

                    mark_match = re.search(r"Marks:\s*(\d+)", result)
                    marks = int(mark_match.group(1)) if mark_match else 0
                    scores[student] += marks

                    with st.expander(f"📘 Question {qno} ({data['marks']} marks)"):
                        st.markdown(f"**Question:** {data['question']}")
                        st.markdown(f"**Student Answer:** {ans}")
                        st.code(result)

                st.metric(
                    label="Total Score",
                    value=f"{scores[student]} / {max_total}"
                )

        # ---------- SUMMARY ----------
        st.markdown("---")
        st.subheader("🎯 Final Score Summary")

        col1, col2, col3 = st.columns(3)
        cols = [col1, col2, col3]

        for i, (student, score) in enumerate(scores.items()):
            cols[i].success(f"**{student}**\n\n{score} / {max_total}")