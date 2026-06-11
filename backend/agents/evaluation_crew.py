"""
EvaluationCrew
--------------
Orchestrates the full 7-dimension candidate evaluation:

  Behavioural panel (CrewAI sequential):
    1. Prompting Skills Analyst       (Groq)
    2. Problem Understanding Analyst  (Mistral codestral)
    3. Debugging Behavior Analyst     (Cohere)
    4. Production Thinking Analyst    (Groq)
    5. Report Generator               (Mistral codestral)

  Deep analysis (parallel, thread-based):
    6. CodeReviewAgent  — two-pass: automated tests + LLM static analysis
    7. ChatAnalysisAgent — 6-dimension AI collaboration quality score

Final report merges all 7 sources into a single EvaluationReport.
"""

from crewai import Agent, Task, Crew, Process
import os
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor
from crewai import LLM
from typing import Dict, Any, List
from typing import Any, ClassVar
from pydantic import BaseModel, Field
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

from backend.agents.code_review_agent import CodeReviewAgent, CodeReviewResult
from backend.agents.chat_analysis_agent import ChatAnalysisAgent, ChatAnalysisResult


def _llm_pydantic_schema(cls, handler: GetCoreSchemaHandler):
    return core_schema.no_info_plain_serializer(
        lambda v: v.model if hasattr(v, "model") else str(v)
    )

LLM.__get_pydantic_core_schema__ = classmethod(_llm_pydantic_schema)


# ── LLM routing ──────────────────────────────────────────────────────────────
LLM_ASSIGNMENTS = {
    "prompting":   "groq/llama-3.3-70b-versatile",
    "problem":     "mistral/codestral-latest",
    "debugging":   "cohere_chat/command-a-03-2025",
    "production":  "groq/llama-3.3-70b-versatile",
    "report":      "mistral/codestral-latest",
}

LLM_USE_CASES = {
    "groq/llama-3.3-70b-versatile": "Fast multi-turn reasoning — prompting clarity & production thinking.",
    "mistral/codestral-latest":     "Code-native model — problem understanding, code review & report synthesis.",
    "cohere_chat/command-a-03-2025": "Instruction-following precision — debugging analysis & concise summaries.",
}


# ── Pydantic models ───────────────────────────────────────────────────────────
class AgentSummary(BaseModel):
    agent_role: str
    llm: Any
    llm_use_case: str
    score: float = Field(..., ge=0, le=100)
    summary: str

    model_config: ClassVar = {
        "arbitrary_types_allowed": True,
        "json_encoders": {LLM: lambda v: v.model if hasattr(v, "model") else str(v)},
    }


class ScoreBreakdown(BaseModel):
    # Behavioural panel
    prompting_skill: float       = Field(..., ge=0, le=100)
    problem_understanding: float = Field(..., ge=0, le=100)
    iteration_refinement: float  = Field(..., ge=0, le=100)
    debugging_behavior: float    = Field(..., ge=0, le=100)
    production_thinking: float   = Field(..., ge=0, le=100)
    # Deep analysis
    code_quality: float          = Field(..., ge=0, le=100)
    chat_collaboration: float    = Field(..., ge=0, le=100)
    overall: float               = Field(..., ge=0, le=100)


class CodeReviewSummary(BaseModel):
    task_title: str
    language: str
    tests_passed: int
    tests_total: int
    correctness_score: float
    edge_case_score: float
    quality_score: float
    production_score: float
    overall_code_score: float
    correctness_notes: List[str]
    quality_notes: List[str]
    production_notes: List[str]
    llm_summary: str
    final_code_snippet: str


class ChatCollaborationSummary(BaseModel):
    total_prompts: int
    avg_prompt_length: float
    prompt_clarity: float
    context_loading: float
    iterative_refinement: float
    understanding_depth: float
    token_efficiency: float
    ai_as_tool_score: float
    overall_chat_score: float
    best_prompt: str
    weakest_prompt: str
    turning_point: str
    coaching_tip: str
    summary: str


class EvaluationReport(BaseModel):
    agent_summaries: List[AgentSummary]
    scores: ScoreBreakdown
    overall_summary: str
    hiring_recommendation: str
    llm_recommendations: Dict[str, str]
    code_review: CodeReviewSummary
    chat_collaboration: ChatCollaborationSummary


# ── Main crew ─────────────────────────────────────────────────────────────────
class EvaluationCrew:

    def __init__(self):
        groq_key    = os.getenv("GROQ_API_KEY")
        mistral_key = os.getenv("MISTRAL_API_KEY")
        cohere_key  = os.getenv("COHERE_API_KEY")

        if not groq_key:
            raise ValueError("GROQ_API_KEY environment variable is not set")

        # Propagate to env so litellm can pick them up
        os.environ["GROQ_API_KEY"]    = groq_key
        os.environ.setdefault("LITELLM_PROXY_SERVER_NOT_RUNNING", "true")
        if mistral_key:
            os.environ["MISTRAL_API_KEY"] = mistral_key
        if cohere_key:
            os.environ["COHERE_API_KEY"] = cohere_key

        def build_llm(model: str) -> LLM:
            if model.startswith("groq/"):
                return LLM(model=model, api_key=groq_key)
            if model.startswith("mistral/"):
                return LLM(model=model, api_key=mistral_key)
            if model.startswith("cohere_chat/"):
                return LLM(model=model, api_key=cohere_key)
            raise ValueError(f"Unknown model family: {model}")

        self.prompting_llm  = build_llm(LLM_ASSIGNMENTS["prompting"])
        self.problem_llm    = build_llm(LLM_ASSIGNMENTS["problem"])
        self.debugging_llm  = build_llm(LLM_ASSIGNMENTS["debugging"])
        self.production_llm = build_llm(LLM_ASSIGNMENTS["production"])
        self.report_llm     = build_llm(LLM_ASSIGNMENTS["report"])

        self.prompting_analyst      = self._create_prompting_analyst()
        self.problem_solver_analyst = self._create_problem_solver_analyst()
        self.debugging_analyst      = self._create_debugging_analyst()
        self.production_analyst     = self._create_production_analyst()
        self.report_generator       = self._create_report_generator()
        self.analysts = [
            self.prompting_analyst,
            self.problem_solver_analyst,
            self.debugging_analyst,
            self.production_analyst,
        ]
        self.llm_use_cases = LLM_USE_CASES

        # Deep analysis agents — lazy init so a failure here doesn't kill the crew
        try:
            self.code_reviewer = CodeReviewAgent()
        except Exception as e:
            import logging
            logging.error(f"CodeReviewAgent init failed: {e}")
            self.code_reviewer = None

        try:
            self.chat_analyser = ChatAnalysisAgent()
        except Exception as e:
            import logging
            logging.error(f"ChatAnalysisAgent init failed: {e}")
            self.chat_analyser = None

    # ── CrewAI agent factories ────────────────────────────────────────────────

    def _create_prompting_analyst(self) -> Agent:
        return Agent(
            role="Prompting Skills Analyst",
            goal="Evaluate the candidate's ability to communicate effectively with AI",
            backstory="Expert in AI interaction and prompt engineering. Assesses how candidates formulate requests, provide context, and iterate on prompts.",
            verbose=True, allow_delegation=False, llm=self.prompting_llm,
        )

    def _create_problem_solver_analyst(self) -> Agent:
        return Agent(
            role="Problem Understanding Analyst",
            goal="Assess the candidate's ability to understand and break down problems",
            backstory="Expert in software engineering problem-solving. Evaluates systematic thinking, clarifying questions, and edge-case awareness.",
            verbose=True, allow_delegation=False, llm=self.problem_llm,
        )

    def _create_debugging_analyst(self) -> Agent:
        return Agent(
            role="Debugging Behavior Analyst",
            goal="Evaluate the candidate's debugging and testing approach",
            backstory="Expert in debugging and QA. Assesses error identification, testing strategies, and systematic troubleshooting.",
            verbose=True, allow_delegation=False, llm=self.debugging_llm,
        )

    def _create_production_analyst(self) -> Agent:
        return Agent(
            role="Production Thinking Analyst",
            goal="Assess the candidate's consideration of real-world engineering concerns",
            backstory="Expert in production software engineering. Evaluates performance awareness, error handling, scalability thinking, and code maintainability.",
            verbose=True, allow_delegation=False, llm=self.production_llm,
        )

    def _create_report_generator(self) -> Agent:
        return Agent(
            role="Technical Interview Report Generator",
            goal="Synthesize all evaluations into a comprehensive hiring recommendation",
            backstory="Senior technical recruiter and engineering manager. Combines analyst insights into actionable reports with specific evidence.",
            verbose=True, allow_delegation=False, llm=self.report_llm,
        )

    # ── Main entry point ──────────────────────────────────────────────────────

    async def evaluate_session(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all 3 evaluation tracks in parallel:
          - CrewAI behavioural panel (5 agents)
          - CodeReviewAgent (2-pass)
          - ChatAnalysisAgent (6-dimension)
        Then merge results into a single EvaluationReport.
        """
        session_summary = self._prepare_session_summary(session)
        loop = asyncio.get_event_loop()

        with ThreadPoolExecutor(max_workers=3) as pool:
            crew_future = loop.run_in_executor(pool, self._run_crew, session_summary)

            code_future = (
                loop.run_in_executor(pool, self.code_reviewer.review, session)
                if self.code_reviewer else asyncio.get_event_loop().run_in_executor(None, self._empty_code_review)
            )
            chat_future = (
                loop.run_in_executor(pool, self.chat_analyser.analyse, session)
                if self.chat_analyser else asyncio.get_event_loop().run_in_executor(None, self._empty_chat_result)
            )

            crew_result, code_result, chat_result = await asyncio.gather(
                crew_future, code_future, chat_future
            )

        return self._build_report(crew_result, code_result, chat_result, session)

    def _run_crew(self, session_summary: str) -> Dict[str, Any]:
        """
        Runs the 5-agent CrewAI panel synchronously (called in thread).
        Returns a dict with the final crew result AND individual task summaries
        captured directly from task.output — no text parsing needed.
        """
        prompting_task = Task(
            description=f"""{session_summary}

You are the PROMPTING SKILLS ANALYST. Your job is ONLY to evaluate how the candidate writes prompts to the AI.
Do NOT evaluate code quality, debugging, or problem understanding — those are other analysts' jobs.

Look specifically at the CHAT HISTORY and PROMPTS sections above. Ask yourself:
- Did the candidate write clear, specific prompts or vague requests?
- Did they provide enough context before asking?
- Did each follow-up build on the previous response or just repeat?
- Did they use precise technical vocabulary?
- Did they extract real value from each AI exchange?

Your summary MUST reference specific prompts from the chat history above. Do not copy answers from other analysts.

Return ONLY a JSON object: {{"score": <0-100>, "summary": "<under 200 chars, cite specific prompts>"}}""",
            agent=self.prompting_analyst,
            expected_output='JSON: {"score": int, "summary": str}',
        )

        problem_task = Task(
            description=f"""{session_summary}

You are the PROBLEM UNDERSTANDING ANALYST. Your job is ONLY to evaluate how deeply the candidate understood the problem.
Do NOT evaluate prompting style or debugging — those are other analysts' jobs.

Look specifically at what the candidate asked and how they approached the problem. Ask yourself:
- Did they understand the requirements from the start or did they misinterpret them?
- Did they break the problem into steps before coding?
- Did they ask clarifying questions about edge cases or constraints?
- Did their approach show systematic thinking?

Your summary MUST reference the candidate's actual approach from the session above. Do not copy answers from other analysts.

Return ONLY a JSON object: {{"score": <0-100>, "summary": "<under 200 chars, cite their approach>"}}""",
            agent=self.problem_solver_analyst,
            expected_output='JSON: {"score": int, "summary": str}',
        )

        debugging_task = Task(
            description=f"""{session_summary}

You are the DEBUGGING BEHAVIOR ANALYST. Your job is ONLY to evaluate how the candidate handled errors and failures.
Do NOT evaluate prompting style or problem understanding — those are other analysts' jobs.

Look specifically at the CODE EXECUTIONS section above. Ask yourself:
- When their code failed (ERROR executions), how did they respond?
- Did they use systematic debugging or random guessing?
- Did they use print/logging techniques?
- How many attempts did it take to fix each error?

Your summary MUST reference specific code execution results from the session. Do not copy answers from other analysts.

Return ONLY a JSON object: {{"score": <0-100>, "summary": "<under 200 chars, cite specific errors>"}}""",
            agent=self.debugging_analyst,
            expected_output='JSON: {"score": int, "summary": str}',
        )

        production_task = Task(
            description=f"""{session_summary}

You are the PRODUCTION THINKING ANALYST. Your job is ONLY to evaluate whether the candidate thought beyond the happy path.
Do NOT evaluate prompting style or debugging steps — those are other analysts' jobs.

Look at the candidate's questions and code. Ask yourself:
- Did they ask about edge cases, error handling, or production concerns?
- Did they consider performance or scalability?
- Did their code show awareness of real-world usage?
- Did they think about maintainability?

Your summary MUST reference specific evidence from the session. Do not copy answers from other analysts.

Return ONLY a JSON object: {{"score": <0-100>, "summary": "<under 200 chars, cite specific evidence>"}}""",
            agent=self.production_analyst,
            expected_output='JSON: {"score": int, "summary": str}',
        )

        report_task = Task(
            description=f"""{session_summary}

You have received scores from 4 analysts. Synthesize a final report.

Return ONLY a JSON object:
{{
  "overall_summary": "<3-4 sentences, max 400 chars>",
  "recommendation": "<Strong Hire | Hire | Maybe | No Hire>"
}}""",
            agent=self.report_generator,
            expected_output='JSON: {"overall_summary": str, "recommendation": str}',
            context=[prompting_task, problem_task, debugging_task, production_task],
        )

        # Run each analyst in its own isolated single-task crew.
        # This prevents sequential context bleeding where later agents
        # copy-paste the first agent's output because they see it in context.
        import json as _j

        def _run_isolated(agent: Agent, task: Task) -> tuple:
            """Run one agent in its own crew, return (raw_result_str, summary_str)."""
            solo_crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=True)
            result = solo_crew.kickoff()
            raw = re.sub(r"```(?:json)?|```", "", str(result)).strip()
            try:
                obj = _j.loads(raw)
                return raw, str(obj.get("summary", "")).strip()
            except Exception:
                m = re.search(r'"summary"\s*:\s*"((?:[^"\\]|\\.)*)"', raw)
                summary = m.group(1).replace("\\n", " ").strip() if m else raw[:200]
                return raw, summary

        prompting_raw,  prompting_summary  = _run_isolated(self.prompting_analyst,      prompting_task)
        problem_raw,    problem_summary    = _run_isolated(self.problem_solver_analyst,  problem_task)
        debugging_raw,  debugging_summary  = _run_isolated(self.debugging_analyst,       debugging_task)
        production_raw, production_summary = _run_isolated(self.production_analyst,      production_task)

        # Report task needs all 4 analyst outputs as context — run last
        report_task_final = Task(
            description=f"""{session_summary}

Analyst findings:
- Prompting: {prompting_raw[:400]}
- Problem Understanding: {problem_raw[:400]}
- Debugging: {debugging_raw[:400]}
- Production Thinking: {production_raw[:400]}

Synthesize a final report. Return ONLY a JSON object:
{{
  "overall_summary": "<3-4 sentences, max 400 chars>",
  "recommendation": "<Strong Hire | Hire | Maybe | No Hire>"
}}""",
            agent=self.report_generator,
            expected_output='JSON: {"overall_summary": str, "recommendation": str}',
        )
        report_crew = Crew(agents=[self.report_generator], tasks=[report_task_final], process=Process.sequential, verbose=True)
        crew_result = report_crew.kickoff()

        return {
            "crew_result": crew_result,
            "summaries": {
                "prompting":  prompting_summary,
                "problem":    problem_summary,
                "debugging":  debugging_summary,
                "production": production_summary,
            },
        }

    # ── Report assembly ───────────────────────────────────────────────────────

    def _build_report(
        self,
        crew_result: Any,
        code_result: CodeReviewResult,
        chat_result: ChatAnalysisResult,
        session: Dict[str, Any],
    ) -> Dict[str, Any]:

        # Unpack crew dict returned by _run_crew
        agent_texts  = crew_result.get("summaries", {})
        result_text  = str(crew_result.get("crew_result", ""))

        # Behavioural scores from crew
        b_scores = self._extract_behavioural_scores(result_text, session)

        # Unified score breakdown — 7 dimensions
        scores = ScoreBreakdown(
            prompting_skill=b_scores["prompting_skill"],
            problem_understanding=b_scores["problem_understanding"],
            iteration_refinement=b_scores["iteration_refinement"],
            debugging_behavior=b_scores["debugging_behavior"],
            production_thinking=b_scores["production_thinking"],
            code_quality=self._clamp(code_result.overall_code_score),
            chat_collaboration=self._clamp(chat_result.overall_chat_score),
            overall=self._compute_overall(b_scores, code_result, chat_result),
        )

        agent_summaries = self._build_agent_summaries(scores, session, chat_result, agent_texts, code_result)
        overall_summary = self._extract_overall_summary(result_text, session)
        recommendation  = self._derive_recommendation(scores.overall)

        code_summary = CodeReviewSummary(
            task_title=code_result.task_title,
            language=code_result.language,
            tests_passed=code_result.tests_passed,
            tests_total=code_result.tests_total,
            correctness_score=code_result.correctness.score,
            edge_case_score=code_result.edge_cases.score,
            quality_score=code_result.code_quality.score,
            production_score=code_result.production_readiness.score,
            overall_code_score=code_result.overall_code_score,
            correctness_notes=code_result.correctness.notes,
            quality_notes=code_result.code_quality.notes,
            production_notes=code_result.production_readiness.notes,
            llm_summary=code_result.llm_summary,
            final_code_snippet=code_result.final_code_snippet,
        )

        chat_summary = ChatCollaborationSummary(
            total_prompts=chat_result.total_prompts,
            avg_prompt_length=chat_result.avg_prompt_length,
            prompt_clarity=chat_result.prompt_clarity,
            context_loading=chat_result.context_loading,
            iterative_refinement=chat_result.iterative_refinement,
            understanding_depth=chat_result.understanding_depth,
            token_efficiency=chat_result.token_efficiency,
            ai_as_tool_score=chat_result.ai_as_tool_score,
            overall_chat_score=chat_result.overall_chat_score,
            best_prompt=chat_result.best_prompt,
            weakest_prompt=chat_result.weakest_prompt,
            turning_point=chat_result.turning_point,
            coaching_tip=chat_result.coaching_tip,
            summary=chat_result.summary,
        )

        report = EvaluationReport(
            agent_summaries=agent_summaries,
            scores=scores,
            overall_summary=overall_summary,
            hiring_recommendation=recommendation,
            llm_recommendations=self.llm_use_cases,
            code_review=code_summary,
            chat_collaboration=chat_summary,
        )
        return report.model_dump(mode="json")

    # ── Score helpers ─────────────────────────────────────────────────────────

    def _compute_overall(
        self, b: Dict, cr: CodeReviewResult, chat: ChatAnalysisResult
    ) -> float:
        return self._clamp(round(
            b["prompting_skill"]       * 0.10
            + b["problem_understanding"] * 0.10
            + b["iteration_refinement"]  * 0.10
            + b["debugging_behavior"]    * 0.10
            + b["production_thinking"]   * 0.10
            + cr.overall_code_score      * 0.30   # code is the core signal
            + chat.overall_chat_score    * 0.20,  # AI collaboration matters
            1,
        ))

    def _extract_behavioural_scores(self, text: str, session: Dict) -> Dict[str, float]:
        logs = session.get("behavioral_logs", {})
        prompts    = len(logs.get("prompts", []))
        runs       = logs.get("run_attempts", 0)
        revisions  = logs.get("code_revisions", 0)
        dbg_steps  = len(logs.get("debugging_steps", []))
        tech_terms = len(set(logs.get("technical_vocabulary", [])))
        iterations = revisions + logs.get("iterations", 0)

        # Heuristic baseline (will be overridden by parsed LLM scores)
        heuristics = {
            "prompting_skill":       self._clamp(45 + prompts * 2.5),
            "problem_understanding": self._clamp(50 + runs * 3.2),
            "iteration_refinement":  self._clamp(35 + iterations * 7),
            "debugging_behavior":    self._clamp(40 + dbg_steps * 9),
            "production_thinking":   self._clamp(30 + tech_terms * 3),
        }

        # Override with LLM-extracted scores where available
        patterns = {
            "prompting_skill":       r"prompting skill[s]?.*?([0-9]{1,3})",
            "problem_understanding": r"problem understanding.*?([0-9]{1,3})",
            "iteration_refinement":  r"iteration.*?([0-9]{1,3})",
            "debugging_behavior":    r"debugging behavior.*?([0-9]{1,3})",
            "production_thinking":   r"production thinking.*?([0-9]{1,3})",
        }
        for key, pattern in patterns.items():
            m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if m:
                heuristics[key] = self._clamp(float(m.group(1)))

        # Try JSON "score" extraction
        json_scores = re.findall(r'"score"\s*:\s*([0-9]{1,3})', text)
        if len(json_scores) >= 5:
            keys = ["prompting_skill", "problem_understanding",
                    "debugging_behavior", "production_thinking"]
            for i, k in enumerate(keys):
                if i < len(json_scores):
                    heuristics[k] = self._clamp(float(json_scores[i]))

        return heuristics

    def _build_agent_summaries(
        self,
        scores: ScoreBreakdown,
        session: Dict,
        chat: ChatAnalysisResult,
        agent_texts: Dict[str, str],
        code_result: CodeReviewResult,
    ) -> List[AgentSummary]:
        logs = session.get("behavioral_logs", {})

        def _s(key: str, fallback: str) -> str:
            """Return LLM summary if non-empty, else fallback."""
            return agent_texts.get(key, "").strip() or fallback

        return [
            AgentSummary(
                agent_role="Prompting Skills Analyst",
                llm=LLM_ASSIGNMENTS["prompting"],
                llm_use_case=self.llm_use_cases[LLM_ASSIGNMENTS["prompting"]],
                score=scores.prompting_skill,
                summary=_s("prompting",
                    f"{len(logs.get('prompts',[]))} prompts sent; avg {chat.avg_prompt_length:.0f} chars each."),
            ),
            AgentSummary(
                agent_role="Problem Understanding Analyst",
                llm=LLM_ASSIGNMENTS["problem"],
                llm_use_case=self.llm_use_cases[LLM_ASSIGNMENTS["problem"]],
                score=scores.problem_understanding,
                summary=_s("problem",
                    f"{logs.get('run_attempts',0)} code runs, {logs.get('code_revisions',0)} revisions observed."),
            ),
            AgentSummary(
                agent_role="Debugging Behavior Analyst",
                llm=LLM_ASSIGNMENTS["debugging"],
                llm_use_case=self.llm_use_cases[LLM_ASSIGNMENTS["debugging"]],
                score=scores.debugging_behavior,
                summary=_s("debugging",
                    f"{len(logs.get('debugging_steps',[]))} debugging steps detected."),
            ),
            AgentSummary(
                agent_role="Production Thinking Analyst",
                llm=LLM_ASSIGNMENTS["production"],
                llm_use_case=self.llm_use_cases[LLM_ASSIGNMENTS["production"]],
                score=scores.production_thinking,
                summary=_s("production",
                    f"{len(set(logs.get('technical_vocabulary',[])))} distinct technical terms used."),
            ),
            AgentSummary(
                agent_role="Code Review Agent (Mistral codestral)",
                llm=LLM_ASSIGNMENTS["problem"],
                llm_use_case="Automated test execution + LLM static analysis of submitted code.",
                score=scores.code_quality,
                summary=code_result.llm_summary or f"Code scored {scores.code_quality:.1f}/100.",
            ),
            AgentSummary(
                agent_role="Chat Collaboration Analyst (Groq Llama 3.3)",
                llm=LLM_ASSIGNMENTS["prompting"],
                llm_use_case="6-dimension AI collaboration quality analysis across the full conversation.",
                score=scores.chat_collaboration,
                summary=chat.summary[:300] if chat.summary else f"Chat collaboration scored {scores.chat_collaboration:.1f}/100.",
            ),
        ]

    def _extract_overall_summary(self, text: str, session: Dict) -> str:
        import json as _json
        try:
            m = re.search(r'\{[^{}]*"overall_summary"[^{}]*\}', text, re.DOTALL)
            if m:
                obj = _json.loads(m.group(0))
                s = obj.get("overall_summary", "")
                if s:
                    runs = session.get("behavioral_logs", {}).get("run_attempts", 0)
                    return f"{s.strip()} ({runs} code runs executed.)"
        except Exception:
            pass
        cleaned = re.sub(r'```(?:json)?|```', '', text).strip()[:450]
        return cleaned or "Evaluation complete. See dimension scores for detail."

    def _derive_recommendation(self, overall: float) -> str:
        if overall >= 85: return "Strong Hire"
        if overall >= 70: return "Hire"
        if overall >= 55: return "Maybe"
        return "No Hire"

    def _clamp(self, v: float) -> float:
        try:
            return max(0.0, min(100.0, float(v)))
        except (TypeError, ValueError):
            return 0.0

    def _prepare_session_summary(self, session: Dict[str, Any]) -> str:
        logs = session.get("behavioral_logs", {})
        return f"""SESSION SUMMARY
Candidate : {session.get('candidate_name', 'Unknown')}
Duration  : {self._duration(session)}

BEHAVIOURAL METRICS:
- Prompts sent    : {len(logs.get('prompts', []))}
- Code executions : {logs.get('run_attempts', 0)}
- Code revisions  : {logs.get('code_revisions', 0)}
- Debugging steps : {len(logs.get('debugging_steps', []))}
- Technical terms : {len(set(logs.get('technical_vocabulary', [])))}

CHAT HISTORY:
{self._fmt_chat(session.get('chat_history', []))}

CODE EXECUTIONS:
{self._fmt_executions(session.get('code_executions', []))}

PROMPTS:
{self._fmt_prompts(logs.get('prompts', []))}"""

    def _duration(self, session: Dict) -> str:
        from datetime import datetime
        try:
            s = datetime.fromisoformat(session["created_at"])
            e = datetime.fromisoformat(session["completed_at"])
            return str(e - s)
        except Exception:
            return "Unknown"

    def _fmt_chat(self, history: list) -> str:
        if not history: return "No chat history"
        return "\n".join(
            f"{i}. [{m['role'].upper()}]: {m['content'][:200]}"
            for i, m in enumerate(history[-20:], 1)
        )

    def _fmt_executions(self, execs: list) -> str:
        if not execs: return "No code executions"
        return "\n".join(
            f"{i}. [{'SUCCESS' if not e['result'].get('error') else 'ERROR'}] "
            f"{e['language']}: {e['code'][:100]}..."
            for i, e in enumerate(execs, 1)
        )

    def _fmt_prompts(self, prompts: list) -> str:
        if not prompts: return "No prompts"
        return "\n".join(f"{i}. {p['message'][:150]}" for i, p in enumerate(prompts, 1))

    def _empty_code_review(self):
        from backend.agents.code_review_agent import CodeReviewResult, DimensionScore
        return CodeReviewResult(
            task_id=1, task_title="N/A", language="unknown",
            correctness=DimensionScore(score=0), edge_cases=DimensionScore(score=0),
            code_quality=DimensionScore(score=0), production_readiness=DimensionScore(score=0),
            overall_code_score=0, llm_summary="Code review unavailable.",
        )

    def _empty_chat_result(self):
        from backend.agents.chat_analysis_agent import ChatAnalysisResult
        return ChatAnalysisResult(
            prompt_clarity=0, context_loading=0, iterative_refinement=0,
            understanding_depth=0, token_efficiency=0, ai_as_tool_score=0,
            overall_chat_score=0, summary="Chat analysis unavailable.",
        )
