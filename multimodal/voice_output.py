from __future__ import annotations

import io
from typing import Any

from core.llm import complete


def text_to_speech(text: str, language: str = "en", slow: bool = False) -> bytes:
    from gtts import gTTS

    buffer = io.BytesIO()
    gTTS(text=text, lang=language, slow=slow).write_to_fp(buffer)
    buffer.seek(0)
    return buffer.read()


def generate_voice_summary(report: dict[str, Any]) -> tuple[bytes, str]:
    executive_summary = report.get("executive_summary", "")
    summary = report.get("summary", {})
    security_findings = summary.get("security_findings", "")
    impact_analysis = summary.get("impact_analysis", "")
    pr_title = report.get("pr_title", "this pull request")
    agents_run = report.get("agents_run", [])

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

    spoken_text = complete(spoken_prompt, max_tokens=300, temperature=0.3)
    return text_to_speech(spoken_text), spoken_text


def answer_voice_query(query_text: str, report: dict[str, Any]) -> tuple[str, bytes]:
    summary = report.get("summary", {})
    context = f"""
PR Title: {report.get('pr_title', '')}
Executive Summary: {report.get('executive_summary', '')}
Code Analysis: {summary.get('code_analysis', '')[:500]}
Security Findings: {summary.get('security_findings', '')[:500]}
Style Issues: {summary.get('style_issues', '')[:300]}
Impact Analysis: {summary.get('impact_analysis', '')[:300]}
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

    answer_text = complete(answer_prompt, max_tokens=200, temperature=0.3)
    return answer_text, text_to_speech(answer_text)
