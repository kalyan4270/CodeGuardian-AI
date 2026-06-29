<div align="center">

<img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
<img src="https://img.shields.io/badge/LangGraph-0.1.5-FF6B6B?style=for-the-badge" />
<img src="https://img.shields.io/badge/Neo4j-5.20-008CC1?style=for-the-badge&logo=neo4j&logoColor=white" />
<img src="https://img.shields.io/badge/Groq-LLaMA3-F55036?style=for-the-badge" />
<img src="https://img.shields.io/badge/Whisper-OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white" />

# 🛡️ CodeGuardian AI

### Multi-Agent Intelligent Code Review Platform

> An enterprise-grade AI platform that automatically reviews GitHub Pull Requests using
> specialized AI agents running in parallel — analyzing code quality, security vulnerabilities,
> style compliance, and dependency impact through a Neo4j knowledge graph.

[Features](#features) • [Architecture](#architecture) • [Agents](#agents) • [API](#api) • [Setup](#setup) • [Design](#design-patterns)

</div>

---

## 📌 Overview

CodeGuardian AI replaces manual code reviews with a coordinated system of specialized AI agents.
When a Pull Request is submitted, the platform:

1. Fetches the PR diff from GitHub API
2. Fires 4 specialized agents **simultaneously** using parallel execution
3. Queries a **Neo4j knowledge graph** to map dependency impact
4. Generates a comprehensive review report with voice summary
5. Allows developers to ask questions via **voice or text**

---

## ✨ Features

| Feature | Description |
|---|---|
| 🤖 Multi-Agent Review | 4 specialized agents run in parallel |
| 🕸️ Knowledge Graph | Neo4j dependency mapping across codebase |
| 🔒 Security Scanning | Detects hardcoded secrets, injection risks |
| 🎤 Voice Interface | Whisper STT + Google TTS for voice Q&A |
| ⚡ Parallel Execution | ThreadPoolExecutor for concurrent agents |
| 🔄 LLM Fallback | Automatic model fallback on rate limits |
| 📊 Impact Analysis | Downstream dependency risk assessment |
| 🏗️ Production Ready | Proper logging, config, error handling |

---

### System Architecture
## 🏗️ High-Level Design (HLD)

![HLD](https://github.com/user-attachments/assets/cb73da6f-9efa-4e88-9c63-a23ccb6bfe70)

> System architecture showing all components and data flow


### Data Flow

```
Developer Opens PR
       │
       ▼
POST /review ──► GitHub Service ──► Fetch PR Diff + Metadata
       │
       ▼
LangGraph Orchestrator
       │
       ├──────────────────────────────────────┐
       │                                      │
       ▼                                      ▼
ThreadPoolExecutor                      Neo4j Client
(4 agents parallel)                  (Knowledge Graph)
       │                                      │
       ├── Code Agent ──► Groq LLM           │
       ├── Security Agent ──► Groq LLM       │
       ├── Style Agent ──► Groq LLM          │
       └── Impact Agent ──► Neo4j Queries ───┘
                │
                ▼
         State Merge
         (by agent key)
                │
                ▼
       Report Generator ──► Groq LLM (Summary)
                │
                ▼
         Report Store
         (Thread-safe cache)
                │
                ▼
       JSON Response ──► Frontend
                │
                ▼
       Voice Summary ──► Google TTS ──► Audio Stream
```

---

## 🔬 Low-Level Design (LLD)

### Agent Architecture

```
┌─────────────────────────────────────────────────┐
│                  BaseAgent Pattern               │
│                                                 │
│  base.py                                        │
│  ┌─────────────────────────────────────────┐   │
│  │  build_pr_context(state) → str          │   │
│  │  ┌───────────────────────────────────┐  │   │
│  │  │  PR Title + Description + Diff    │  │   │
│  │  └───────────────────────────────────┘  │   │
│  │                                         │   │
│  │  run_review_agent(                      │   │
│  │    state,                               │   │
│  │    system_role,                         │   │
│  │    instructions,                        │   │
│  │    temperature,                         │   │
│  │    max_tokens                           │   │
│  │  ) → str                               │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
         │           │           │           │
         ▼           ▼           ▼           ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
   │   Code   │ │ Security │ │  Style   │ │  Impact  │
   │  Agent   │ │  Agent   │ │  Agent   │ │  Agent   │
   │          │ │          │ │          │ │          │
   │temp: 0.3 │ │temp: 0.1 │ │temp: 0.3 │ │Neo4j +  │
   │          │ │(precision│ │          │ │Groq LLM  │
   │Writes to:│ │needed)   │ │Writes to:│ │          │
   │code_     │ │Writes to:│ │style_    │ │Writes to:│
   │analysis  │ │security_ │ │issues    │ │impact_   │
   │          │ │findings  │ │          │ │analysis  │
   └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

### Orchestrator — State Machine Design

```
ReviewState (TypedDict)
┌─────────────────────────────┐
│ pr_diff:           str      │
│ pr_description:    str      │
│ pr_title:          str      │
│ repo_name:         str      │
│ pr_number:         int      │
│ code_analysis:     str      │  ◄── Written by Code Agent
│ security_findings: str      │  ◄── Written by Security Agent
│ style_issues:      str      │  ◄── Written by Style Agent
│ impact_analysis:   str      │  ◄── Written by Impact Agent
│ graph_metadata:    dict     │  ◄── Written by Impact Agent
│ final_report:      dict     │  ◄── Written by Report Generator
└─────────────────────────────┘

LangGraph Flow:
START
  │
  ▼
parallel_agents ──► Fires 4 agents via ThreadPoolExecutor
  │                 Each agent gets dict(state) copy
  │                 Results merged by _AGENT_OUTPUT_KEYS map
  │                 Prevents empty string overwrites
  ▼
report_generator ──► Generates executive summary via LLM
  │                  Assembles final_report dict
  ▼
END
```

### Neo4j Knowledge Graph Schema

```
Node Types:
┌─────────────┐    ┌─────────────┐    ┌──────────────┐
│ Repository  │    │    File     │    │ PullRequest  │
│             │    │             │    │              │
│ name: str   │    │ path: str   │    │ number: int  │
│ created_at  │    │ repo: str   │    │ title: str   │
│ last_seen   │    │ created_at  │    │ reviewed_at  │
└──────┬──────┘    └──────┬──────┘    └──────┬───────┘
       │                  │                  │
       │ CONTAINS         │ IMPORTS          │ CHANGED
       └──────────────────┘                  │
                                             ▼
Relationship Types:                    (links PR to
CONTAINS  → Repo contains File          changed files)
IMPORTS   → File imports File
CALLS     → File calls File
EXTENDS   → File extends File
HAS_PR    → Repo has PullRequest
CHANGED   → PR changed File

Query Example — Find Downstream Impact:
MATCH (f:File {path: $file_path})
      <-[:IMPORTS|CALLS|EXTENDS]-(dependent:File)
RETURN dependent.path AS impacted_file
```

### LLM Client — Fallback Chain Design

```
complete(prompt) called
         │
         ▼
   Primary Model
   llama-3.3-70b-versatile
         │
    429 Rate Limit?
    ┌────┴────┐
   YES       NO
    │         │
    ▼         ▼
Fallback    Return
  Model     Response
llama-3.1-
8b-instant
    │
 429 Again?
 ┌──┴──┐
YES    NO
 │      │
 ▼      ▼
Raise  Return
LLM    Response
Rate
Limit
Error
```

### Exception Hierarchy

```
CodeGuardianError (base)
├── GitHubAPIError
│   └── status_code, detail
├── ReviewNotFoundError
│   └── repo, pr_number
├── TranscriptionError
│   └── (voice input failures)
└── LLMRateLimitError
    └── models_tried, retry_after
```

### Project Structure

```
CodeGuardian-AI/
├── main.py                    # App factory + lifespan
├── api/
│   └── routes/
│       ├── health.py          # Health check endpoint
│       └── review.py          # All review endpoints
├── agents/
│   ├── base.py                # Shared agent utilities
│   ├── orchestrator.py        # LangGraph state machine
│   ├── code_agent.py          # Code quality analysis
│   ├── security_agent.py      # Security vulnerability scan
│   ├── style_agent.py         # Style and standards check
│   └── impact_agent.py        # Neo4j dependency analysis
├── core/
│   ├── config.py              # Frozen dataclass settings
│   ├── exceptions.py          # Custom exception hierarchy
│   ├── llm.py                 # Groq client + fallback chain
│   └── logging.py             # Structured logging setup
├── graph/
│   ├── neo4j_client.py        # Neo4j driver + queries
│   └── graph_builder.py       # Graph construction from diffs
├── multimodal/
│   ├── voice_input.py         # Whisper STT
│   └── voice_output.py        # Google TTS
├── services/
│   ├── github_service.py      # GitHub API integration
│   └── report_store.py        # Thread-safe report cache
├── models/
│   ├── schemas.py             # Pydantic request/response
│   └── state.py               # LangGraph ReviewState
└── reports/
    └── generator.py           # Report formatting
```

---

## 🤖 Agents

| Agent | Role | Temperature | Output Key |
|---|---|---|---|
| **Code Agent** | Detects bugs, logic errors, performance issues | 0.3 | `code_analysis` |
| **Security Agent** | Finds hardcoded secrets, injection risks, auth issues | 0.1 | `security_findings` |
| **Style Agent** | Checks naming, documentation, DRY violations | 0.3 | `style_issues` |
| **Impact Agent** | Queries Neo4j for downstream dependency risk | 0.3 | `impact_analysis` |

---


## 🔌 API Reference

### Review a Pull Request
```http
POST /review
Content-Type: application/json

{
  "repo_url": "https://github.com/owner/repo",
  "pr_number": 42
}
```

### Get Voice Summary
```http
GET /review/{owner}/{repo}/{pr_number}/voice-summary
→ Returns: audio/mpeg stream
```

### Ask Text Question
```http
POST /review/{owner}/{repo}/{pr_number}/query
Content-Type: application/x-www-form-urlencoded

question=What are the security issues?
```

### Ask Voice Question
```http
POST /review/{owner}/{repo}/{pr_number}/voice-query
Content-Type: multipart/form-data

audio_file: <wav/mp3 file>
→ Returns: audio/mpeg stream
```

### Health Check
```http
GET /health
→ Returns: { status, phase, features }
```

---

## ⚙️ Setup

### Prerequisites
```
Python 3.11+
Neo4j Aura account (free)
Groq API key (free)
GitHub Personal Access Token
```

### Installation

```bash
# Clone repository
git clone https://github.com/kalyan4270/CodeGuardian-AI.git
cd CodeGuardian-AI

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables

Create `.env` file:
```env
GROQ_API_KEY=your_groq_api_key
GITHUB_TOKEN=your_github_token
NEO4J_URI=neo4j+ssc://xxxxxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_FALLBACK_MODELS=llama-3.1-8b-instant
```

### Run

```bash
uvicorn main:app --reload
```

API docs available at: `http://localhost:8000/docs`

---

## 🧪 Testing

```bash
# Test LLM connection
python -c "from core.llm import complete; print(complete('Hello'))"

# Test Neo4j connection
python -c "from graph.neo4j_client import neo4j_client; print(neo4j_client.verify_connection())"

# Run API
uvicorn main:app --reload

# Test review endpoint
curl -X POST http://localhost:8000/review \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/owner/repo", "pr_number": 1}'
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **API Framework** | FastAPI 0.111 |
| **Agent Orchestration** | LangGraph 0.1.5 |
| **LLM Provider** | Groq (LLaMA3 70B + 8B fallback) |
| **Knowledge Graph** | Neo4j Aura 5.20 |
| **Voice Input** | OpenAI Whisper (local) |
| **Voice Output** | Google TTS (gTTS) |
| **Parallel Execution** | ThreadPoolExecutor |
| **HTTP Client** | HTTPX (async) |
| **Data Validation** | Pydantic v2 |
| **Configuration** | Frozen dataclass + python-dotenv |

---

## 🔮 Future Enhancements

- [ ] Redis for persistent report storage
- [ ] WebSocket for real-time agent progress
- [ ] Support for Java, JavaScript dependency parsing
- [ ] GitHub App integration for automatic PR triggering
- [ ] Docker containerization
- [ ] Kubernetes deployment manifests
- [ ] OpenTelemetry distributed tracing
- [ ] Fine-tuned models for code-specific analysis

---

## 👤 Author

**Chodabattula Yaswanth**
- GitHub: [@kalyan4270](https://github.com/kalyan4270)
- LinkedIn: [Yaswanth](https://linkedin.com/in/chodabattula-yaswanth-venkata-kalyan-702b9523a)
- Portfolio: [yaswanth-portfolio](https://yaswanth-portfolio-v4uc.vercel.app/)

---

<div align="center">
Built with LangGraph • Neo4j • Groq • FastAPI • Whisper
</div>
