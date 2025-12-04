import json
import subprocess
from ollama import Client
import tempfile
import os
import re

client = Client(host="http://localhost:11434")

# ----------------- Agent 1: Analyzer Agent ------------------
def analyze_function(function_code: str):
    prompt = f"""
    You are a code analysis expert. Analyze the following function and extract:
    - purpose
    - input parameters & types
    - possible edge cases
    - failure conditions or error paths
    - expected output behavior

    Return as structured JSON.

    Function:
    {function_code}
    """

    response = client.chat(
        model="phi3",
        messages=[{"role": "user", "content": prompt}]
    )

    return response["message"]["content"]

# ----------------- Agent 2: Test Generator Agent ------------------
def generate_tests(function_code, analysis, framework="unittest"):
    prompt = f"""
    You are a senior Python test engineer.
    Using the following analysis and function code, generate high-quality {framework} tests.

    Requirements:
    - Include edge cases & negative cases
    - Use assert statements appropriately
    - Do not include explanations, only test code
    - Import the original function

    Function:
    {function_code}

    Analysis:
    {analysis}

    Output ONLY valid python code for tests.
    """

    response = client.chat(
        model="phi3",
        messages=[{"role": "user", "content": prompt}]
    )

    # Strip Markdown code fences
    test_code = response["message"]["content"].replace("```python", "").replace("```", "").strip()
    return test_code

# ----------------- Fix Imports ------------------
def fix_test_imports(test_code: str, function_file="code_under_test"):
    """
    Replace any LLM-generated 'from <module> import <func>' with the temp file module
    """
    test_code = re.sub(r"from\s+\w+\s+import\s+(\w+)", rf"from {function_file} import \1", test_code)
    return test_code

# ----------------- Agent 3: Test Validator Agent ------------------
def validate_tests(test_code: str, function_code: str):
    """
    Creates temp file, executes tests, and returns results.
    Windows-safe: sets cwd to tempdir.
    """
    # Strip any remaining Markdown fences
    test_code = test_code.replace("```python", "").replace("```", "").strip()
    test_code = fix_test_imports(test_code)

    with tempfile.TemporaryDirectory() as tempdir:
        func_path = os.path.join(tempdir, "code_under_test.py")
        test_path = os.path.join(tempdir, "test_generated.py")

        with open(func_path, "w") as f:
            f.write(function_code)

        with open(test_path, "w") as f:
            f.write(test_code)

        try:
            # Run unittest inside temp directory (Windows-safe)
            result = subprocess.run(
                ["python", "-m", "unittest", "test_generated.py"],
                cwd=tempdir,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout + result.stderr

        except Exception as e:
            return f"ERROR executing tests: {e}"

# ----------------- Main Execution Workflow ------------------
if __name__ == "__main__":

    # Example Python function to test
    function_code = """
def divide(a, b):
    if b == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    return a / b
"""

    print("🔍 Agent 1 analyzing function...")
    analysis = analyze_function(function_code)
    print("\nAnalysis Result:\n", analysis)

    print("\n🧪 Agent 2 generating tests...")
    tests = generate_tests(function_code, analysis)
    print("\nGenerated Test Code:\n", tests)

    print("\n⚙️ Agent 3 validating...")
    results = validate_tests(tests, function_code)
    print("\nValidation Results:\n", results)
