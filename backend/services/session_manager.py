from typing import Dict, Any, Optional


class SessionManager:
    """In-memory session store — works on HF Spaces (no persistent disk needed)."""

    def __init__(self, sessions_dir: str = "sessions"):
        # sessions_dir param kept for API compatibility but ignored
        self._store: Dict[str, Any] = {}

    def save_session(self, session_id: str, session_data: Dict[str, Any]) -> None:
        self._store[session_id] = session_data

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        if session_id in self._store:
            del self._store[session_id]
            return True
        return False

    def list_sessions(self) -> list:
        return list(self._store.keys())
