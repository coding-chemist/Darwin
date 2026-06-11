from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
import os


# Full spec the AI knows but the candidate must discover through conversation
TASK_SPECS = {
    1: {
        "title": "Event Logger",
        "spec": (
            "Full spec (reveal piece by piece when candidate asks — never dump all at once):\n"
            "- Events are dicts with 'source' (str), 'level' (INFO/WARN/ERROR), 'message' (str)\n"
            "- Filter by minimum level: INFO < WARN < ERROR\n"
            "- Two output destinations: console print AND in-memory list buffer\n"
            "- Buffer queryable by source or level\n"
            "- Missing/malformed fields must be handled gracefully — no crashes\n"
            "- Thread safety is NOT required for this exercise"
        )
    },
    2: {
        "title": "Rate Limiter",
        "spec": (
            "Full spec (reveal piece by piece when candidate asks — never dump all at once):\n"
            "- Sliding window algorithm (not fixed window — clarify if they assume fixed)\n"
            "- Track per client_id (string key)\n"
            "- Configurable: limit (int, max requests) and window (int, seconds) at init\n"
            "- is_allowed(client_id) → True/False\n"
            "- get_remaining(client_id) → int (how many requests left in current window)\n"
            "- Auto-cleanup expired entries to avoid memory leaks"
        )
    },
    3: {
        "title": "Task Queue",
        "spec": (
            "Full spec (reveal piece by piece when candidate asks — never dump all at once):\n"
            "- Priority levels: HIGH=1, NORMAL=2, LOW=3 (lower number = higher priority)\n"
            "- claim_task() → returns highest-priority PENDING task atomically, marks it RUNNING\n"
            "- complete_task(task_id) and fail_task(task_id) update status\n"
            "- Statuses: PENDING, RUNNING, DONE, FAILED\n"
            "- Auto-requeue RUNNING tasks that exceed configurable timeout (back to PENDING)\n"
            "- stats() → dict with count per status"
        )
    }
}


class InterviewState(TypedDict):
    session_id: str
    message: str
    task_id: int
    chat_history: List[Dict[str, str]]
    ai_response: str
    context: Dict[str, Any]
    task_spec: str          # hidden spec the AI holds
    is_error_message: bool  # True when message is an auto-injected code error


class InterviewGraph:
    """LangGraph workflow — AI knows the hidden spec, reveals it through dialogue."""

    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            api_key=os.getenv("GROQ_API_KEY")
        )
        self.graph = self._create_graph()

    def _create_graph(self):
        workflow = StateGraph(InterviewState)
        workflow.add_node("generate_response", self._generate_response)
        workflow.add_node("validate_response", self._validate_response)
        workflow.set_entry_point("generate_response")
        workflow.add_edge("generate_response", "validate_response")
        workflow.add_edge("validate_response", END)
        return workflow.compile()

    async def _generate_response(self, state: InterviewState) -> InterviewState:
        task_spec  = state.get("task_spec", "")
        is_error   = state.get("is_error_message", False)

        history_str = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in state.get("chat_history", [])[-12:]
        ])

        if is_error:
            # Error feedback mode — be direct, help debug
            system_prompt = f"""You are an AI pair-programming assistant in a technical interview.
The candidate just ran their code and got an error. Help them debug it.

TASK HIDDEN SPEC (you know this — use it to guide, not to give away):
{task_spec}

Rules for error feedback:
- Read the error carefully and explain what it means in plain language
- Ask ONE guiding question to help them locate the cause
- Do NOT write the fix for them — ask them to try first
- If it's a simple syntax error, you may point to the line directly
- Keep your response concise — 3-5 sentences max

Recent conversation:
{history_str}"""
        else:
            # Normal chat mode — Socratic, spec-revealing
            system_prompt = f"""You are an AI pair-programming assistant in a technical interview.
Your role is to help the candidate discover the full requirements through conversation — not to hand them the spec upfront.

TASK HIDDEN SPEC (you hold this — reveal it gradually as they ask):
{task_spec}

How to reveal the spec:
- When they ask a specific question ("what fields does an event have?"), answer it directly
- When they ask vague questions ("what should I build?"), ask a clarifying question back
- Never dump the entire spec at once — make them work for each requirement
- After they've clarified enough to start coding, encourage them to begin

Coding guidance rules:
- Do NOT write complete solutions
- Do help with syntax errors, built-in functions, and debugging techniques
- When they hit an error, ask about their thought process before suggesting fixes
- Encourage them to think about edge cases and production concerns

Recent conversation:
{history_str}"""

        # Build messages directly — avoids LangChain treating {vars} in user
        # code (e.g. {r1}, {remaining}) as template variables (KeyError)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=state["message"]),
        ]
        result = await self.llm.ainvoke(messages)
        state["ai_response"] = result.content
        return state

    async def _validate_response(self, state: InterviewState) -> InterviewState:
        # No-op — validation kept for extensibility
        return state

    async def process_chat(
        self,
        message: str,
        session_id: str,
        task_id: int,
        chat_history: List[Dict],
        is_error_message: bool = False,
    ) -> str:
        task_info = TASK_SPECS.get(task_id, TASK_SPECS[1])

        initial_state = {
            "session_id": session_id,
            "message": message,
            "task_id": task_id,
            "chat_history": chat_history,
            "ai_response": "",
            "context": {},
            "task_spec": task_info["spec"],
            "is_error_message": is_error_message,
        }

        final_state = await self.graph.ainvoke(initial_state)
        return final_state["ai_response"]
