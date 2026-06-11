"""
ChatAnalysisAgent
-----------------
Evaluates the quality of the candidate's AI collaboration — not just counts.

Dimensions scored:
  1. Prompt Clarity       — how well they specified intent, context, constraints
  2. Context Loading      — did they give the AI what it needed to help them?
  3. Iterative Refinement — did they build on responses or repeat the same ask?
  4. Understanding Depth  — do their questions reveal they understand the problem?
  5. Token Efficiency     — did they extract real value per exchange vs vague asks?
  6. AI as Tool vs Crutch — did they use AI to accelerate thinking or replace it?

Also surfaces: best prompt, weakest prompt, turning-point moment in the conversation.
"""

import os
import json
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from crewai import Agent, Task, Crew, Process, LLM


# ── LLM assignment ─────────────────────────────────────────────────────────
# Groq llama-3.3-70b: fast, strong at conversational analysis and multi-turn reasoning
CHAT_ANALYSIS_LLM = "groq/llama-3.3-70b-versatile"


# ── Output models ─────────────────────────────────────────────────────────────
class PromptPattern(BaseModel):
    prompt_text: str
    strength: str        # "strong" | "weak" | "neutral"
    reason: str


class ChatAnalysisResult(BaseModel):
    prompt_clarity: float = Field(..., ge=0, le=100)
    context_loading: float = Field(..., ge=0, le=100)
    iterative_refinement: float = Field(..., ge=0, le=100)
    understanding_depth: float = Field(..., ge=0, le=100)
    token_efficiency: float = Field(..., ge=0, le=100)
    ai_as_tool_score: float = Field(..., ge=0, le=100)
    overall_chat_score: float = Field(..., ge=0, le=100)

    total_prompts: int = 0
    total_ai_responses: int = 0
    avg_prompt_length: float = 0.0
    notable_patterns: List[PromptPattern] = Field(default_factory=list)

    best_prompt: str = ""
    weakest_prompt: str = ""
    turning_point: str = ""
    summary: str = ""
    coaching_tip: str = ""     # one thing they should do differently


# ── Agent ─────────────────────────────────────────────────────────────────────
class ChatAnalysisAgent:
    """
    Analyses the full chat + code execution history to score AI collaboration quality.
    Goes beyond counting messages — reads actual prompt text and response patterns.
    """

    def __init__(self):
        self.llm = LLM(
            model=CHAT_ANALYSIS_LLM,
            api_key=os.getenv("GROQ_API_KEY"),
        )
        self._agent = Agent(
            role="AI Collaboration Analyst",
            goal=(
                "Evaluate how effectively the candidate used AI assistance during the interview. "
                "Score the quality of their prompts, their ability to iterate, and whether they "
                "used AI as a thinking tool or as a shortcut."
            ),
            backstory=(
                "You are an expert in human-AI interaction and have reviewed thousands of "
                "developer sessions. You can tell from a chat history whether someone understands "
                "how to leverage AI effectively — precise context-setting, iterative refinement, "
                "reading responses critically, and knowing when to push back."
            ),
            verbose=False,
            allow_delegation=False,
            llm=self.llm,
        )

    # ── public API ────────────────────────────────────────────────────────────

    def analyse(self, session: Dict[str, Any]) -> ChatAnalysisResult:
        """Full synchronous analysis — call from a thread executor."""
        chat_history = session.get("chat_history", [])
        code_executions = session.get("code_executions", [])
        behavioral_logs = session.get("behavioral_logs", {})

        # Basic metrics
        user_messages = [m for m in chat_history if m.get("role") == "user"]
        ai_messages   = [m for m in chat_history if m.get("role") == "assistant"]
        total_prompts = len(user_messages)
        avg_len = (
            sum(len(m.get("content", "")) for m in user_messages) / total_prompts
            if total_prompts > 0 else 0.0
        )

        if total_prompts == 0:
            # No chat at all — candidate didn't use AI
            return ChatAnalysisResult(
                prompt_clarity=0, context_loading=0, iterative_refinement=0,
                understanding_depth=0, token_efficiency=0, ai_as_tool_score=0,
                overall_chat_score=0,
                total_prompts=0, total_ai_responses=len(ai_messages),
                avg_prompt_length=0,
                summary="Candidate did not use the AI assistant during the session.",
                coaching_tip="Engage with the AI to discuss your approach, ask clarifying questions, and iterate on solutions.",
            )

        # LLM analysis pass
        llm_result = self._llm_analyse(
            chat_history, code_executions, behavioral_logs, total_prompts, avg_len
        )

        # Weighted overall
        overall = round(
            llm_result["prompt_clarity"]       * 0.20
            + llm_result["context_loading"]    * 0.20
            + llm_result["iterative_refinement"] * 0.20
            + llm_result["understanding_depth"] * 0.20
            + llm_result["token_efficiency"]    * 0.10
            + llm_result["ai_as_tool_score"]    * 0.10,
            1,
        )

        patterns = [
            PromptPattern(
                prompt_text=p.get("text", "")[:200],
                strength=p.get("strength", "neutral"),
                reason=p.get("reason", ""),
            )
            for p in llm_result.get("notable_patterns", [])
        ]

        return ChatAnalysisResult(
            prompt_clarity=llm_result["prompt_clarity"],
            context_loading=llm_result["context_loading"],
            iterative_refinement=llm_result["iterative_refinement"],
            understanding_depth=llm_result["understanding_depth"],
            token_efficiency=llm_result["token_efficiency"],
            ai_as_tool_score=llm_result["ai_as_tool_score"],
            overall_chat_score=overall,
            total_prompts=total_prompts,
            total_ai_responses=len(ai_messages),
            avg_prompt_length=round(avg_len, 1),
            notable_patterns=patterns,
            best_prompt=llm_result.get("best_prompt", ""),
            weakest_prompt=llm_result.get("weakest_prompt", ""),
            turning_point=llm_result.get("turning_point", ""),
            summary=llm_result.get("summary", ""),
            coaching_tip=llm_result.get("coaching_tip", ""),
        )

    # ── LLM pass ──────────────────────────────────────────────────────────────

    def _llm_analyse(
        self,
        chat_history: List[Dict],
        code_executions: List[Dict],
        behavioral_logs: Dict,
        total_prompts: int,
        avg_len: float,
    ) -> Dict[str, Any]:

        # Format chat for the prompt
        formatted_chat = self._format_chat(chat_history)
        formatted_code = self._format_code_timeline(code_executions)

        prompt = f"""You are evaluating a developer's AI collaboration quality in a technical interview.

QUANTITATIVE SIGNALS:
- Total prompts sent: {total_prompts}
- Avg prompt length (chars): {avg_len:.0f}
- Code executions: {behavioral_logs.get('run_attempts', 0)}
- Code revisions: {behavioral_logs.get('code_revisions', 0)}
- Debugging steps detected: {len(behavioral_logs.get('debugging_steps', []))}

FULL CONVERSATION:
{formatted_chat}

CODE EXECUTION TIMELINE:
{formatted_code}

Score each dimension 0-100. Be critical — a score above 80 means genuinely impressive AI collaboration.

Scoring guide:
- prompt_clarity: How precisely did they specify intent, constraints, and expected output?
- context_loading: Did they give the AI enough context (task requirements, what they already tried)?
- iterative_refinement: Did each follow-up build on the previous response, or did they repeat/give up?
- understanding_depth: Do their questions reveal they understood the problem deeply, not just surface-level?
- token_efficiency: Did they extract high value per exchange vs. vague asks that got vague answers?
- ai_as_tool_score: Did they use AI to accelerate their own thinking (high score) or to get answers without thinking (low score)?

Return ONLY valid JSON — no markdown, no explanation outside the JSON:
{{
  "prompt_clarity": <int>,
  "context_loading": <int>,
  "iterative_refinement": <int>,
  "understanding_depth": <int>,
  "token_efficiency": <int>,
  "ai_as_tool_score": <int>,
  "notable_patterns": [
    {{"text": "<verbatim prompt excerpt>", "strength": "strong|weak|neutral", "reason": "<why>"}}
  ],
  "best_prompt": "<verbatim best prompt, full text>",
  "weakest_prompt": "<verbatim weakest prompt, full text>",
  "turning_point": "<describe the moment the candidate's approach shifted, if any>",
  "summary": "<3-4 sentence verdict on their AI collaboration quality>",
  "coaching_tip": "<single most impactful thing they should do differently>"
}}"""

        task = Task(
            description=prompt,
            agent=self._agent,
            expected_output="JSON object with chat analysis scores and patterns",
        )
        crew = Crew(agents=[self._agent], tasks=[task], process=Process.sequential, verbose=False)
        result = crew.kickoff()
        return self._parse_json(str(result))

    # ── helpers ───────────────────────────────────────────────────────────────

    def _format_chat(self, chat_history: List[Dict]) -> str:
        if not chat_history:
            return "(no conversation)"
        lines = []
        for i, msg in enumerate(chat_history, 1):
            role = msg.get("role", "?").upper()
            content = msg.get("content", "")[:400]
            lines.append(f"[{i}] {role}: {content}")
        return "\n".join(lines)

    def _format_code_timeline(self, executions: List[Dict]) -> str:
        if not executions:
            return "(no code executions)"
        lines = []
        for i, exe in enumerate(executions, 1):
            status = "SUCCESS" if exe.get("result", {}).get("success") else "ERROR"
            lang = exe.get("language", "?")
            code_preview = exe.get("code", "")[:150].replace("\n", " ")
            error = exe.get("result", {}).get("error", "")
            line = f"[{i}] {status} ({lang}): {code_preview}"
            if error:
                line += f" | ERROR: {str(error)[:100]}"
            lines.append(line)
        return "\n".join(lines)

    def _parse_json(self, text: str) -> Dict[str, Any]:
        text = re.sub(r"```(?:json)?", "", text).strip()
        try:
            return json.loads(text)
        except Exception:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
        return {
            "prompt_clarity": 40, "context_loading": 40,
            "iterative_refinement": 40, "understanding_depth": 40,
            "token_efficiency": 40, "ai_as_tool_score": 40,
            "notable_patterns": [], "best_prompt": "", "weakest_prompt": "",
            "turning_point": "", "summary": "Could not parse chat analysis.",
            "coaching_tip": "",
        }
