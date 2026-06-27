from gtts import gTTS
import io
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_voice_summary(report: dict) -> bytes:
    """
    Takes the review report and returns audio bytes
    of a spoken summary using Google TTS.

    Steps:
    1. Extract key findings from report
    2. Generate clean spoken summary via LLM
    3. Convert text to speech using gTTS
    4. Return audio as bytes for API response
    """

    # Step 1: Extract key findings
    executive_summary  = report.get("executive_summary", "")
    security_findings  = report.get("summary", {}).get("security_findings", "")
    impact_analysis    = report.get("summary", {}).get("impact_analysis", "")
    pr_title           = report.get("pr_title", "this pull request")
    agents_run         = report.get("agents_run", [])

    # Step 2: Generate spoken-friendly summary
    # Regular report text has markdown, bullets etc
    # Need clean natural language for TTS
    spoken_prompt = f"""
    Convert this code review report into a natural spoken summary.
    It will be read aloud so:
    - No bullet points or markdown
    - No special characters or symbols
    - Natural conversational sentences
    - Maximum 5 sentences total
    - Mention the most critical finding first

    PR Title: {pr_title}
    Executive Summary: {executive_summary}
    Security Findings (first 200 chars): {security_findings[:200]}
    Impact Analysis (first 200 chars): {impact_analysis[:200]}
    Agents that ran: {', '.join(agents_run)}

    Start with: "Code review complete for {pr_title}."
    """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": spoken_prompt}],
        max_tokens=300,
        temperature=0.3
    )

    spoken_text = response.choices[0].message.content.strip()
    print(f"Voice summary text: {spoken_text}")

    # Step 3: Convert text to speech
    audio_bytes = text_to_speech(spoken_text)

    return audio_bytes, spoken_text

def text_to_speech(text: str, 
                   language: str = "en",
                   slow: bool = False) -> bytes:
    """
    Converts text to speech using Google TTS.
    Returns audio as bytes.
    Free — uses Google Translate TTS API.
    """
    tts = gTTS(
        text=text,
        lang=language,
        slow=slow
    )

    # Save to bytes buffer instead of file
    audio_buffer = io.BytesIO()
    tts.write_to_fp(audio_buffer)
    audio_buffer.seek(0)

    return audio_buffer.read()

def answer_voice_query(query_text: str, 
                       report: dict) -> tuple:
    """
    Answers a specific developer voice question
    about the review report.

    e.g. "What are the security issues?"
         "Which files are impacted?"
         "What should I fix first?"

    Returns: (answer_text, audio_bytes)
    """
    # Build context from report
    context = f"""
    PR Title: {report.get('pr_title', '')}
    Executive Summary: {report.get('executive_summary', '')}
    Code Analysis: {report.get('summary', {}).get('code_analysis', '')[:500]}
    Security Findings: {report.get('summary', {}).get('security_findings', '')[:500]}
    Style Issues: {report.get('summary', {}).get('style_issues', '')[:300]}
    Impact Analysis: {report.get('summary', {}).get('impact_analysis', '')[:300]}
    """

    answer_prompt = f"""
    A developer asked this question about their code review:
    Question: {query_text}

    Based on this review report:
    {context}

    Answer in 2-3 natural sentences.
    No bullet points or markdown — will be spoken aloud.
    Be specific and actionable.
    """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": answer_prompt}],
        max_tokens=200,
        temperature=0.3
    )

    answer_text  = response.choices[0].message.content.strip()
    audio_bytes  = text_to_speech(answer_text)

    return answer_text, audio_bytes