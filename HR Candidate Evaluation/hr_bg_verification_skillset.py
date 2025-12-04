import psycopg2
from fastapi import FastAPI, UploadFile, File, Form
from ollama import Client
import PyPDF2
import io
import json
import os
import uuid

app = FastAPI()
client = Client()

UPLOAD_FOLDER = "./uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- DB Connection ---
conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="Password@123",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

# --- Create Tables ---
cursor.execute("CREATE SCHEMA IF NOT EXISTS hr;")

cursor.execute("""
CREATE TABLE IF NOT EXISTS hr.candidates (
    candidate_id SERIAL PRIMARY KEY,
    full_name TEXT,
    email TEXT,
    resume_file_name TEXT,
    created_at TIMESTAMP DEFAULT NOW()
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS hr.job_descriptions (
    jd_id SERIAL PRIMARY KEY,
    jd_title TEXT,
    jd_file_name TEXT,
    created_at TIMESTAMP DEFAULT NOW()
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS hr.candidate_skills (
    candidate_id INT REFERENCES hr.candidates(candidate_id),
    skill_json JSONB,
    bg_verification_json JSONB,
    created_at TIMESTAMP DEFAULT NOW()
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS hr.jd_skills (
    jd_id INT REFERENCES hr.job_descriptions(jd_id),
    skill_json JSONB,
    created_at TIMESTAMP DEFAULT NOW()
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS hr.candidate_evaluation (
    eval_id SERIAL PRIMARY KEY,
    candidate_id INT REFERENCES hr.candidates(candidate_id),
    jd_id INT REFERENCES hr.job_descriptions(jd_id),
    skill_match_json JSONB,
    created_at TIMESTAMP DEFAULT NOW()
)
""")

conn.commit()

# --- Helper Functions ---
def extract_text_from_pdf(pdf_bytes):
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
    text = ""
    for page in pdf_reader.pages:
        text += (page.extract_text() or "") + "\n"
    return text

def safe_parse_json(text: str):
    """Try to parse JSON, fallback to raw text."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text.strip()}

# --- API: Upload Candidate Resume ---
@app.post("/upload_candidate_resume")
async def upload_candidate_resume(
    file: UploadFile = File(...),
    candidate_name: str = Form(...),
    email: str = Form(...)
):
    file_bytes = await file.read()
    file_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_FOLDER, file_name)
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    candidate_text = extract_text_from_pdf(file_bytes)

    # LLM: Extract candidate skills
    skill_prompt = f"""
Extract skills from resume.
Return strictly JSON with key 'skills' as a list.
No explanations.
Candidate Resume:\n{candidate_text}
"""
    skill_res = client.chat(model="phi3", messages=[{"role": "user", "content": skill_prompt}])
    skill_json = safe_parse_json(skill_res["message"]["content"])

    # LLM: Background verification
    bg_prompt = f"""
Perform background verification.
Return strictly JSON with keys: status, risk_score, education_verified, employment_verified, identity_verified, remarks.
No explanations.
Candidate Resume:\n{candidate_text}
"""
    bg_res = client.chat(model="phi3", messages=[{"role": "user", "content": bg_prompt}])
    bg_json = safe_parse_json(bg_res["message"]["content"])

    # Insert candidate
    cursor.execute(
        "INSERT INTO hr.candidates (full_name, email, resume_file_name) VALUES (%s, %s, %s) RETURNING candidate_id",
        (candidate_name, email, file_name)
    )
    candidate_id = cursor.fetchone()[0]
    conn.commit()

    cursor.execute(
        "INSERT INTO hr.candidate_skills (candidate_id, skill_json, bg_verification_json) VALUES (%s, %s, %s)",
        (candidate_id, json.dumps(skill_json), json.dumps(bg_json))
    )
    conn.commit()

    return {"candidate_id": candidate_id, "file_name": file_name, "skills": skill_json, "bg_verification": bg_json}

# --- API: Upload Job Description ---
@app.post("/upload_job_description")
async def upload_job_description(
    file: UploadFile = File(...),
    jd_title: str = Form(...)
):
    file_bytes = await file.read()
    file_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_FOLDER, file_name)
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    jd_text = extract_text_from_pdf(file_bytes)

    # LLM: Extract JD skills
    jd_skill_prompt = f"""
Extract required skills from Job Description.
Return strictly JSON with key 'skills' as a list.
No explanations.
Job Description:\n{jd_text}
"""
    jd_skill_res = client.chat(model="phi3", messages=[{"role": "user", "content": jd_skill_prompt}])
    jd_skill_json = safe_parse_json(jd_skill_res["message"]["content"])

    cursor.execute(
        "INSERT INTO hr.job_descriptions (jd_title, jd_file_name) VALUES (%s, %s) RETURNING jd_id",
        (jd_title, file_name)
    )
    jd_id = cursor.fetchone()[0]
    conn.commit()

    cursor.execute(
        "INSERT INTO hr.jd_skills (jd_id, skill_json) VALUES (%s, %s)",
        (jd_id, json.dumps(jd_skill_json))
    )
    conn.commit()

    return {"jd_id": jd_id, "file_name": file_name, "skills": jd_skill_json}

# --- API: Evaluate Candidate against Job Description ---
@app.post("/evaluate_candidate")
async def evaluate_candidate(candidate_id: int = Form(...), jd_id: int = Form(...)):
    cursor.execute("SELECT skill_json FROM hr.candidate_skills WHERE candidate_id=%s", (candidate_id,))
    candidate_skill_json = cursor.fetchone()[0]

    cursor.execute("SELECT skill_json FROM hr.jd_skills WHERE jd_id=%s", (jd_id,))
    jd_skill_json = cursor.fetchone()[0]

    # No json.loads() needed, the JSONB field returns dict
    candidate_skills = set(candidate_skill_json.get("skills", []))
    jd_skills = set(jd_skill_json.get("skills", []))

    matched_skills = list(candidate_skills & jd_skills)
    missing_skills = list(jd_skills - candidate_skills)
    match_percentage = int(len(matched_skills)/len(jd_skills)*100) if jd_skills else 0

    evaluation_json = {
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "match_percentage": match_percentage
    }

    cursor.execute(
        "INSERT INTO hr.candidate_evaluation (candidate_id, jd_id, skill_match_json) VALUES (%s, %s, %s)",
        (candidate_id, jd_id, json.dumps(evaluation_json))
    )
    conn.commit()

    return {"candidate_id": candidate_id, "jd_id": jd_id, "evaluation": evaluation_json}
