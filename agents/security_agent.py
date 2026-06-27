from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def security_agent(state: dict) -> dict:
    """
    Scans PR diff for security vulnerabilities:
    - Hardcoded secrets/API keys
    - SQL injection risks
    - Unsafe dependencies
    - Authentication issues
    - Data exposure risks
    """
    prompt = f"""
    You are a security expert reviewing a pull request for vulnerabilities.

    PR Title: {state['pr_title']}
    PR Description: {state['pr_description']}

    Code Changes:
    {state['pr_diff']}

    Analyse strictly for security issues:
    1. Hardcoded secrets, API keys, passwords, tokens
    2. SQL injection or command injection vulnerabilities
    3. Unsafe input handling or missing validation
    4. Authentication or authorization issues
    5. Sensitive data exposure

    For each issue found:
    - Severity: CRITICAL / HIGH / MEDIUM / LOW
    - Location: which file/line
    - Description: what the issue is
    - Fix: how to resolve it

    If no issues found, explicitly state "No security issues detected."
    Be concise and specific.
    """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
        temperature=0.1  # low temperature for security — need precision
    )

    state["security_findings"] = response.choices[0].message.content
    return state