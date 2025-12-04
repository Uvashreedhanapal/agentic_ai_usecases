# agentic_ai_usecases

**1.HR Candidate Evaluation**
This usecase is a FastAPI-based system for managing candidate resumes, job descriptions, and evaluating candidates against job requirements using an LLM (phi3 model via Ollama). It extracts skills from resumes and job descriptions, performs background verification, and calculates skill match percentages automatically. The data is stored in PostgreSQL.
  **Tech Stack**
  Python 3.12+
  FastAPI – REST API framework
  PostgreSQL – Relational database
  PyPDF2 – PDF parsing library
  Ollama API (phi3 model) – LLM for skill extraction and background verification
  UUID & JSON – For unique file naming and flexible JSON storage
  Psycopg2 – PostgreSQL connector
