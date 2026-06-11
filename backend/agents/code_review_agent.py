"""
CodeReviewAgent
---------------
Evaluates the candidate's submitted code against the actual task requirements.
Runs two passes:
  1. Automated test generation + execution via the existing CodeExecutor
  2. LLM static analysis (correctness, edge cases, code quality, production readiness)

Returns a structured CodeReviewResult with per-dimension scores and evidence.
"""

import os
import json
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from crewai import Agent, Task, Crew, Process, LLM

from backend.services.code_executor import CodeExecutor


# ── LLM for code review ──────────────────────────────────────────────────────
# Mistral codestral-latest: purpose-built code model, best fit for static analysis
CODE_REVIEW_LLM = "mistral/codestral-latest"


# ── Task catalogue (mirrors main.py get_available_tasks) ─────────────────────
TASK_CATALOGUE = {
    1: {
        "title": "String Manipulation API",
        "description": (
            "Build a function that takes a string and returns an object/dict with "
            "character frequency counts. Case-insensitive, ignore non-alphabetic characters."
        ),
        "test_cases": [
            {"input": '"Hello World!"', "expected_keys": ["h", "e", "l", "o", "w", "r", "d"]},
            {"input": '""',             "expected": {}},
            {"input": '"123!@#"',       "expected": {}},
            {"input": '"AaA"',          "expected": {"a": 3}},
        ],
        "python_test_harness": '''
import json

def run_tests(fn):
    results = []
    tests = [
        ("Hello World!", {"h":1,"e":1,"l":3,"o":2,"w":1,"r":1,"d":1}),
        ("",             {}),
        ("123!@#",       {}),
        ("AaA",          {"a":3}),
        ("  spaces  ",   {"s":2,"p":1,"a":1,"c":1,"e":2}),
    ]
    for inp, expected in tests:
        try:
            result = fn(inp)
            passed = dict(sorted(result.items())) == dict(sorted(expected.items()))
            results.append({"input": repr(inp), "expected": expected, "got": result, "passed": passed})
        except Exception as ex:
            results.append({"input": repr(inp), "expected": expected, "got": str(ex), "passed": False})
    return results
''',
    },
    2: {
        "title": "Async Data Processor",
        "description": (
            "Create an async function that fetches data from multiple URLs concurrently, "
            "handles errors gracefully, and returns a consolidated result."
        ),
        "test_cases": [],
        "python_test_harness": None,  # async task — static analysis only
    },
    3: {
        "title": "Cache System with TTL",
        "description": (
            "Implement an in-memory cache class with TTL support. "
            "Must support get, set, delete operations and auto-expire old entries."
        ),
        "test_cases": [],
        "python_test_harness": '''
import time, json

def run_tests(CacheClass):
    results = []

    # Basic set/get
    c = CacheClass()
    c.set("k", "v", 5000)
    results.append({"test": "set_get", "passed": c.get("k") == "v"})

    # Miss
    results.append({"test": "miss", "passed": c.get("missing") is None})

    # Delete
    c.set("d", "val", 5000)
    c.delete("d")
    results.append({"test": "delete", "passed": c.get("d") is None})

    return results
''',
    },
}


# ── Output models ─────────────────────────────────────────────────────────────
class DimensionScore(BaseModel):
    score: float = Field(..., ge=0, le=100)
    notes: List[str] = Field(default_factory=list)


class TestResult(BaseModel):
    test_input: str
    expected: Any
    actual: Any
    passed: bool


class CodeReviewResult(BaseModel):
    task_id: int
    task_title: str
    language: str
    correctness: DimensionScore
    edge_cases: DimensionScore
    code_quality: DimensionScore
    production_readiness: DimensionScore
    overall_code_score: float
    test_results: List[TestResult] = Field(default_factory=list)
    tests_passed: int = 0
    tests_total: int = 0
    llm_summary: str = ""
    final_code_snippet: str = ""


# ── Agent ─────────────────────────────────────────────────────────────────────
class CodeReviewAgent:
    """
    Two-pass code reviewer.
    Pass 1: automated test execution against known test cases (Python only).
    Pass 2: LLM static analysis for quality dimensions the tests can't catch.
    """

    def __init__(self):
        self.executor = CodeExecutor()
        self.llm = LLM(
            model=CODE_REVIEW_LLM,
            api_key=os.getenv("MISTRAL_API_KEY"),
        )
        self._agent = Agent(
            role="Senior Code Reviewer",
            goal=(
                "Evaluate submitted interview code for correctness, edge-case coverage, "
                "code quality, and production readiness. Be specific — cite actual lines."
            ),
            backstory=(
                "You are a staff engineer with 12 years of code review experience at "
                "top-tier product companies. You care about correctness first, then clarity, "
                "then production concerns. You are direct and specific — no vague praise."
            ),
            verbose=False,
            allow_delegation=False,
            llm=self.llm,
        )

    # ── public API ────────────────────────────────────────────────────────────

    def review(self, session: Dict[str, Any]) -> CodeReviewResult:
        """Full synchronous review — call from a thread executor."""
        code, language, task_id = self._extract_final_submission(session)
        task_info = TASK_CATALOGUE.get(task_id, TASK_CATALOGUE[1])

        # Pass 1: automated tests (Python only)
        test_results, passed, total = self._run_tests(code, language, task_id, task_info)

        # Pass 2: LLM static analysis
        llm_result = self._llm_review(code, language, task_info, test_results, passed, total)

        overall = round(
            (llm_result["correctness"] * 0.35)
            + (llm_result["edge_cases"] * 0.20)
            + (llm_result["code_quality"] * 0.25)
            + (llm_result["production_readiness"] * 0.20),
            1,
        )

        return CodeReviewResult(
            task_id=task_id,
            task_title=task_info["title"],
            language=language,
            correctness=DimensionScore(
                score=llm_result["correctness"],
                notes=llm_result.get("correctness_notes", []),
            ),
            edge_cases=DimensionScore(
                score=llm_result["edge_cases"],
                notes=llm_result.get("edge_case_notes", []),
            ),
            code_quality=DimensionScore(
                score=llm_result["code_quality"],
                notes=llm_result.get("quality_notes", []),
            ),
            production_readiness=DimensionScore(
                score=llm_result["production_readiness"],
                notes=llm_result.get("production_notes", []),
            ),
            overall_code_score=overall,
            test_results=test_results,
            tests_passed=passed,
            tests_total=total,
            llm_summary=llm_result.get("summary", ""),
            final_code_snippet=code[:800],
        )

    # ── Pass 1: automated testing ─────────────────────────────────────────────

    def _extract_final_submission(self, session: Dict[str, Any]):
        """Return (code, language, task_id) from the last successful execution."""
        executions = session.get("code_executions", [])
        if not executions:
            return ("# no code submitted", "python", 1)

        # Prefer last successful execution
        for exe in reversed(executions):
            if exe.get("result", {}).get("success"):
                return (
                    exe["code"],
                    exe.get("language", "python"),
                    exe.get("task_id", 1),
                )

        # Fall back to last execution even if it errored
        last = executions[-1]
        return (last["code"], last.get("language", "python"), last.get("task_id", 1))

    def _run_tests(self, code: str, language: str, task_id: int, task_info: Dict):
        """Run automated test harness against candidate code. Returns (results, passed, total)."""
        harness = task_info.get("python_test_harness")
        if not harness or language.lower() != "python":
            return [], 0, 0

        # Inject harness + candidate code + runner
        runner = f"""
{harness}

# ── Candidate submission ──
{code}

# ── Auto-detect callable ──
import inspect
candidates = [(n, o) for n, o in list(locals().items()) + list(globals().items())
              if callable(o) and not n.startswith('_') and n not in ('run_tests',)]

results = []
if candidates:
    name, fn = candidates[-1]
    try:
        results = run_tests(fn)
    except Exception as e:
        results = [{{"error": str(e)}}]

import json
print(json.dumps(results))
"""
        raw = self.executor.execute(runner, "python")
        if not raw.get("success"):
            return [], 0, 0

        try:
            raw_results = json.loads(raw["output"].strip().split("\n")[-1])
        except Exception:
            return [], 0, 0

        test_results = []
        passed = 0
        for r in raw_results:
            if "error" in r:
                continue
            tr = TestResult(
                test_input=str(r.get("input", "")),
                expected=r.get("expected"),
                actual=r.get("got"),
                passed=bool(r.get("passed", False)),
            )
            test_results.append(tr)
            if tr.passed:
                passed += 1

        return test_results, passed, len(test_results)

    # ── Pass 2: LLM static analysis ───────────────────────────────────────────

    def _llm_review(
        self,
        code: str,
        language: str,
        task_info: Dict,
        test_results: List[TestResult],
        passed: int,
        total: int,
    ) -> Dict[str, Any]:

        test_summary = (
            f"{passed}/{total} automated tests passed."
            if total > 0
            else "No automated tests available for this language/task."
        )
        failed_cases = [
            f"  input={t.test_input}, expected={t.expected}, got={t.actual}"
            for t in test_results if not t.passed
        ]
        failed_str = "\n".join(failed_cases) if failed_cases else "  (none)"

        prompt = f"""You are reviewing a technical interview submission.

TASK: {task_info['title']}
REQUIREMENTS: {task_info['description']}
LANGUAGE: {language}

AUTOMATED TEST RESULTS: {test_summary}
FAILED CASES:
{failed_str}

SUBMITTED CODE:
```{language}
{code}
```

Score each dimension 0-100 and list specific notes (cite actual code where relevant).

Return ONLY valid JSON — no markdown fences, no explanation outside JSON:
{{
  "correctness": <int>,
  "correctness_notes": ["<specific issue or praise>", ...],
  "edge_cases": <int>,
  "edge_case_notes": ["<what is missing or handled well>", ...],
  "code_quality": <int>,
  "quality_notes": ["<naming, structure, DRY, type hints, readability>", ...],
  "production_readiness": <int>,
  "production_notes": ["<error handling, logging, performance, maintainability>", ...],
  "summary": "<2-3 sentence overall verdict>"
}}"""

        task = Task(
            description=prompt,
            agent=self._agent,
            expected_output="JSON object with scores and notes for each dimension",
        )
        crew = Crew(agents=[self._agent], tasks=[task], process=Process.sequential, verbose=False)
        result = crew.kickoff()
        return self._parse_json(str(result))

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from LLM output robustly."""
        # Strip markdown fences if present
        text = re.sub(r"```(?:json)?", "", text).strip()
        try:
            return json.loads(text)
        except Exception:
            # Try to find the first { ... } block
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
        return {
            "correctness": 50, "correctness_notes": [],
            "edge_cases": 50, "edge_case_notes": [],
            "code_quality": 50, "quality_notes": [],
            "production_readiness": 50, "production_notes": [],
            "summary": "Could not parse LLM review output.",
        }
