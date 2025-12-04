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


**2.ai-unit-test-generator**
Multi-Agent AI-powered Python unit test generator using Ollama phi3 model.
Analyzer Agent analyzes a Python function and extracts its purpose, inputs, edge cases, failure conditions, and expected output.
Test Generator Agent generates high-quality unit tests (using unittest) based on the analysis.
Test Validator Agent executes the generated tests and provides the results


**Tech Stack**
Python 3.12+
Ollama phi3 model
