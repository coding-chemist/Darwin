from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import uuid

from .workflows.interview_graph import InterviewGraph
from .agents.evaluation_crew import EvaluationCrew
from .services.code_executor import CodeExecutor
from .services.session_manager import SessionManager

load_dotenv()

app = FastAPI(title="AI Pair-Programmer Interview Room")

# CORS middleware — ALLOWED_ORIGINS env var lets you add Vercel URL without code changes
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
_allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
session_manager = SessionManager()
code_executor = CodeExecutor()

# Pydantic models
class SessionCreate(BaseModel):
    candidate_name: str
    candidate_email: str

class ChatMessage(BaseModel):
    session_id: str
    message: str
    task_id: int
    is_error_message: bool = False   # True when auto-injected from a code execution error

class CodeExecution(BaseModel):
    session_id: str
    code: str
    language: str
    task_id: int

class SessionSubmit(BaseModel):
    session_id: str

@app.get("/")
async def root():
    return {"message": "AI Pair-Programmer Interview Room API"}

@app.post("/api/session/create")
async def create_session(session_data: SessionCreate):
    """Create a new interview session"""
    session_id = str(uuid.uuid4())
    
    session = {
        "session_id": session_id,
        "candidate_name": session_data.candidate_name,
        "candidate_email": session_data.candidate_email,
        "created_at": datetime.now().isoformat(),
        "tasks": [],
        "current_task": None,
        "chat_history": [],
        "code_executions": [],
        "behavioral_logs": {
            "prompts": [],
            "iterations": 0,
            "code_revisions": 0,
            "run_attempts": 0,
            "debugging_steps": [],
            "technical_vocabulary": []
        },
        "status": "active"
    }
    
    session_manager.save_session(session_id, session)
    
    return {
        "session_id": session_id,
        "message": "Session created successfully",
        "tasks": get_available_tasks()
    }

@app.get("/api/tasks")
async def get_tasks():
    """Get available interview tasks"""
    return {"tasks": get_available_tasks()}

@app.post("/api/chat")
async def chat(message: ChatMessage):
    """Handle AI chat interaction"""
    session = session_manager.get_session(message.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Initialize LangGraph workflow
    interview_graph = InterviewGraph()
    
    # Log the prompt
    session["behavioral_logs"]["prompts"].append({
        "message": message.message,
        "timestamp": datetime.now().isoformat(),
        "task_id": message.task_id
    })
    
    # Analyze technical vocabulary
    technical_terms = extract_technical_vocabulary(message.message)
    session["behavioral_logs"]["technical_vocabulary"].extend(technical_terms)
    
    # Get AI response
    response = await interview_graph.process_chat(
        message=message.message,
        session_id=message.session_id,
        task_id=message.task_id,
        chat_history=session.get("chat_history", []),
        is_error_message=message.is_error_message,
    )

    # Only log to prompts if it's a genuine candidate message, not an auto-injected error
    if message.is_error_message:
        # Remove the auto-appended prompt entry — errors aren't candidate prompts
        if session["behavioral_logs"]["prompts"]:
            session["behavioral_logs"]["prompts"].pop()

    # Update chat history
    session["chat_history"].append({
        "role": "user",
        "content": message.message,
        "timestamp": datetime.now().isoformat()
    })
    session["chat_history"].append({
        "role": "assistant",
        "content": response,
        "timestamp": datetime.now().isoformat()
    })
    
    session_manager.save_session(message.session_id, session)
    
    return {"response": response}

@app.post("/api/code/execute")
async def execute_code(execution: CodeExecution):
    """Execute code and return results"""
    session = session_manager.get_session(execution.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Increment run attempts
    session["behavioral_logs"]["run_attempts"] += 1
    
    # Execute code
    result = code_executor.execute(execution.code, execution.language)
    
    # Log execution
    session["code_executions"].append({
        "code": execution.code,
        "language": execution.language,
        "result": result,
        "timestamp": datetime.now().isoformat(),
        "task_id": execution.task_id
    })
    
    # Track code revisions
    if len(session["code_executions"]) > 1:
        session["behavioral_logs"]["code_revisions"] += 1
    
    # Detect debugging behavior
    if result.get("error") or "debug" in execution.code.lower() or "console.log" in execution.code or "print" in execution.code:
        session["behavioral_logs"]["debugging_steps"].append({
            "timestamp": datetime.now().isoformat(),
            "action": "code_execution_with_debugging",
            "details": result
        })
    
    session_manager.save_session(execution.session_id, session)
    
    return result

@app.post("/api/session/submit")
async def submit_session(submit: SessionSubmit):
    """Submit session for evaluation"""
    session = session_manager.get_session(submit.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Initialize evaluation crew
    evaluation_crew = EvaluationCrew()
    
    # Run evaluation
    evaluation_result = await evaluation_crew.evaluate_session(session)
    
    # Update session
    session["status"] = "completed"
    session["evaluation"] = json.loads(json.dumps(evaluation_result))
    session["completed_at"] = datetime.now().isoformat()
    
    session_manager.save_session(submit.session_id, session)
    
    return evaluation_result

@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Get session details"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session

def get_available_tasks():
    """
    3 intentionally underspecified tasks — candidates MUST use the AI panel
    to clarify requirements before coding. The AI knows the full spec and
    reveals it through conversation. Prompting score is now meaningful.
    """
    return [
        {
            "id": 1,
            "title": "Build an Event Logger",
            "difficulty": "Medium",
            "description": (
                "A backend service needs to log events from multiple sources. "
                "Build it. Ask the AI to clarify what the logger needs to do "
                "before you write a single line of code."
            ),
            "ai_full_spec": (
                "The logger must: (1) accept events as dicts with 'source', 'level' "
                "(INFO/WARN/ERROR), and 'message' fields; (2) filter by minimum level "
                "— only log events at or above the configured level; (3) support "
                "multiple output destinations — console and an in-memory buffer; "
                "(4) allow the buffer to be queried by source or level; "
                "(5) handle missing or malformed event fields gracefully without crashing."
            ),
            "hints": [
                "What fields does an event have?",
                "What log levels are supported and how do they rank?",
                "Where should logs be written — file, console, memory?",
                "What happens when a required field is missing?"
            ]
        },
        {
            "id": 2,
            "title": "Design a Rate Limiter",
            "difficulty": "Hard",
            "description": (
                "An API needs to limit how often clients can make requests. "
                "Build a rate limiter. The requirements are intentionally vague — "
                "use the AI to discover them before writing code."
            ),
            "ai_full_spec": (
                "The rate limiter must: (1) use a sliding window algorithm — not fixed window; "
                "(2) track requests per client_id; (3) allow configurable limit (requests) "
                "and window (seconds) at instantiation; (4) return True if request is allowed, "
                "False if denied; (5) expose a method to get remaining quota for a client; "
                "(6) automatically clean up expired entries to avoid memory leaks."
            ),
            "hints": [
                "What algorithm — fixed window, sliding window, token bucket?",
                "Per user, per IP, or global?",
                "What should happen when the limit is hit — error or queue?",
                "How do you handle the window expiry?"
            ]
        },
        {
            "id": 3,
            "title": "Implement a Task Queue",
            "difficulty": "Hard",
            "description": (
                "A system needs to process background jobs asynchronously. "
                "Build a task queue. Don't assume anything — ask the AI what "
                "the queue needs to support before you start coding."
            ),
            "ai_full_spec": (
                "The task queue must: (1) support priority levels (HIGH/NORMAL/LOW) — "
                "higher priority tasks run first; (2) allow workers to claim a task "
                "atomically so no two workers run the same task; (3) support task "
                "status: PENDING, RUNNING, DONE, FAILED; (4) automatically requeue "
                "a RUNNING task if it hasn't completed within a configurable timeout; "
                "(5) expose a stats() method returning counts per status."
            ),
            "hints": [
                "Should tasks have priorities?",
                "What happens if a worker crashes mid-task?",
                "How many workers can run simultaneously?",
                "What task statuses do you need to track?"
            ]
        }
    ]

def extract_technical_vocabulary(text: str) -> List[str]:
    """Extract technical terms from text"""
    technical_keywords = [
        "async", "await", "promise", "callback", "function", "class",
        "array", "object", "string", "number", "boolean", "null",
        "undefined", "map", "filter", "reduce", "foreach", "loop",
        "if", "else", "switch", "case", "try", "catch", "finally",
        "api", "fetch", "request", "response", "error", "exception",
        "cache", "ttl", "timeout", "interval", "data", "structure",
        "algorithm", "complexity", "performance", "optimization"
    ]
    
    text_lower = text.lower()
    found_terms = [term for term in technical_keywords if term in text_lower]
    return found_terms

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
