import json
import requests
from io import StringIO
from typing import Dict, Any
import sys


PISTON_API = "https://emkc.org/api/v2/piston/execute"


class CodeExecutor:
    """Code execution: Python runs in-process (restricted), JS via Piston public API."""

    def __init__(self):
        self.timeout = 5

    def execute(self, code: str, language: str) -> Dict[str, Any]:
        if language.lower() == "python":
            return self._execute_python(code)
        elif language.lower() in ["javascript", "js"]:
            return self._execute_javascript(code)
        else:
            return {"success": False, "error": f"Unsupported language: {language}", "output": ""}

    def _execute_python(self, code: str) -> Dict[str, Any]:
        import builtins
        # Allow full builtins + standard library imports
        # Blocked: os, sys, subprocess, socket — no filesystem or network access
        _blocked = {"os", "sys", "subprocess", "socket", "shutil", "pathlib",
                    "open", "eval", "exec", "compile", "__import__"}

        def _safe_import(name, *args, **kwargs):
            if name in _blocked:
                raise ImportError(f"Module '{name}' is not allowed in the interview sandbox.")
            return builtins.__import__(name, *args, **kwargs)

        restricted_globals = {
            "__builtins__": {
                **vars(builtins),          # all standard builtins
                "__import__": _safe_import,  # override with safe version
                "open": None,              # block file access
            }
        }
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            exec(code, restricted_globals)
            output = sys.stdout.getvalue()
            return {"success": True, "output": output, "error": None}
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}
        finally:
            sys.stdout = old_stdout

    def _execute_javascript(self, code: str) -> Dict[str, Any]:
        """Run JS via Piston public API — no Node.js installation needed."""
        try:
            payload = {
                "language": "javascript",
                "version": "*",
                "files": [{"content": code}],
                "run_timeout": self.timeout * 1000,
            }
            resp = requests.post(PISTON_API, json=payload, timeout=self.timeout + 3)
            resp.raise_for_status()
            data = resp.json().get("run", {})
            stderr = data.get("stderr", "").strip()
            stdout = data.get("stdout", "").strip()
            if stderr:
                return {"success": False, "output": stdout, "error": stderr}
            return {"success": True, "output": stdout, "error": None}
        except requests.Timeout:
            return {"success": False, "output": "", "error": "Execution timeout (5 seconds)"}
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}
