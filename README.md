# Darwin

> *Naturalist for modern developers. Watches how you code with AI — then judges what makes you effective.*

**Live demo**: [darwin-eta.vercel.app](https://darwin-eta.vercel.app)

Darwin is an AI-augmented technical interview platform that evaluates **how a candidate codes with AI in the loop** — not just whether the final code compiles. It observes every prompt, revision, and debugging step, then runs a 4-agent CrewAI panel to score the behaviors that actually make someone effective with modern tools.

Curie reasons about molecules. Darwin reasons about how people code.

---

## Why Darwin

Darwin's real work was observation. Years watching finches adapt to their environments, documenting behavior, inferring which traits made species effective.

That is exactly what this tool does:

- Watches the candidate adapt to a coding challenge (prompting, debugging, iterating)
- Documents every behavioral signal
- Infers which traits mark an effective modern developer

Naturalist observer → behavioral evaluator.

---

## What it evaluates

Four dimensions, one specialised LLM agent each:

| Agent | LLM | Looks for |
|---|---|---|
| **Prompting Skills** | Groq Llama 3.3 70B | Multi-turn prompt clarity, context-loading, intent specification |
| **Production Thinking** | Groq Llama 3.3 70B | Error handling, edge cases, what "done" actually means |
| **Problem Understanding** | Mistral Phoenix 1.5 | Long-horizon breakdowns, edge-case reasoning |
| **Debugging Behavior** | Gemini 1.5 Pro | Error reactions, hypothesis quality, recovery patterns |

A fifth Mistral pass synthesises the per-dimension reports into a final session dossier.

### Why multi-provider routing
Splitting agents across Groq + Mistral + Gemini avoids any single token-budget ceiling AND matches each agent to the provider best suited for its role — fast multi-turn (Groq), long-horizon synthesis (Mistral), precise instruction-following (Gemini).

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Candidate UI (React + Monaco)                              │
│  ┌──────────────────┐    ┌────────────────────────────────┐ │
│  │  AI Chat Panel   │    │  Code Editor + Sandboxed Run   │ │
│  └────────┬─────────┘    └──────────┬─────────────────────┘ │
└───────────┼─────────────────────────┼───────────────────────┘
            │                         │
            ▼                         ▼
┌──────────────────────────────────────────────────────────────┐
│  FastAPI Backend                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  LangGraph Workflow — session state, task progression  │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Behavioral Logger — prompts, edits, runs, errors      │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  CrewAI 4-Agent Panel (multi-LLM routing)              │ │
│  │   Prompting · Production · Problem · Debugging         │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Stack |
|---|---|
| Backend | Python · FastAPI · LangGraph · CrewAI |
| Frontend | React · Monaco Editor · Tailwind |
| LLMs | Groq Llama 3.3 70B · Mistral Phoenix 1.5 · Gemini 1.5 Pro |
| Execution | Sandboxed Python / JavaScript runner |
| Deployment | Vercel (frontend) · Hugging Face Spaces (backend) |

---

## Project structure

```
Darwin/
├── backend/         FastAPI app — agents, services, LangGraph workflows
├── client/          React UI — Monaco editor + chat panel
├── space_backend/   Dockerfile shim for Hugging Face Spaces deployment
└── requirements.txt
```

---

## Quick start

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate         # Windows: venv\Scripts\activate
pip install -r ../requirements.txt
cp .env.example .env             # add GROQ_API_KEY, MISTRAL_API_KEY, GOOGLE_API_KEY
python main.py
```

### Frontend
```bash
cd client
npm install
npm run dev
```

---

## Status

- 3 interview tasks live
- Behavioral logging end-to-end
- 4-agent CrewAI panel scoring
- Multi-LLM routing across Groq, Mistral, Gemini
- Session report generation

---

## Author

**Sindhuja Sivaraman** · Senior Engineer, AI/ML — HTC Global Services
[Portfolio](https://coding-chemist.vercel.app) · [GitHub](https://github.com/coding-chemist)
