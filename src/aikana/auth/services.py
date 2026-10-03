"""Session-based admin login, logout and admin check, per ./auth.sdd."""

import hmac
import time
from collections.abc import Callable


class AuthService:
    def __init__(
        self,
        admin_password: str,
        max_attempts: int = 5,
        cooldown_seconds: float = 60.0,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self.admin_password = admin_password
        self.max_attempts = max_attempts
        self.cooldown_seconds = cooldown_seconds
        self._now = now
        self._failures = 0
        self._locked_until = 0.0

    def login(self, session: dict, password: str) -> bool:
        if self._now() < self._locked_until:
            return False
        if not self.admin_password or not hmac.compare_digest(password, self.admin_password):
            self._register_failure()
            return False
        self._failures = 0
        session["admin"] = True
        return True

    def logout(self, session: dict) -> None:
        session.pop("admin", None)

    def is_admin(self, session: dict) -> bool:
        return bool(session.get("admin"))

    def _register_failure(self) -> None:
        """Count a failed attempt; reaching the limit locks login for the cooldown, bounding online brute force."""
        self._failures += 1
        if self._failures >= self.max_attempts:
            self._locked_until = self._now() + self.cooldown_seconds
            self._failures = 0

