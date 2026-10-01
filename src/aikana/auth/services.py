"""Session-based admin login, logout and admin check, per ./auth.sdd."""

import hmac


class AuthService:
    def __init__(self, admin_password: str) -> None:
        self.admin_password = admin_password

    def login(self, session: dict, password: str) -> bool:
        if not self.admin_password or not hmac.compare_digest(password, self.admin_password):
            return False
        session["admin"] = True
        return True

    def logout(self, session: dict) -> None:
        session.pop("admin", None)

    def is_admin(self, session: dict) -> bool:
        return bool(session.get("admin"))

