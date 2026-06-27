from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def style_agent(state: dict) -> dict:
    """
    Reviews PR diff for coding standards:
    - Naming conventions
    - Documentation and comments
    - Code structure and readability
    - DRY principles
    - Function/class size
    """
    prompt = f"""
    You are a senior software engineer reviewing code style and standards.

    PR Title: {state['pr_title']}
    PR Description: {state['pr_description']}

    Code Changes:
    {state['pr_diff']}

    Review strictly for style and standards:
    1. Naming conventions (variables, functions, classes)
    2. Missing or poor documentation/docstrings
    3. Code readability and clarity
    4. DRY violations (repeated code)
    5. Function or class complexity (too long, too many responsibilities)
    6. Proper error handling patterns

    For each issue:
    - Type: Naming / Documentation / Readability / DRY / Complexity / ErrorHandling
    - Location: file/line reference
    - Issue: what's wrong
    - Suggestion: how to improve

    Also mention what's done well.
    Be constructive and specific.
    """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
        temperature=0.3
    )

    state["style_issues"] = response.choices[0].message.content
    return state