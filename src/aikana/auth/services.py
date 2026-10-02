"""Session-based admin login, logout and admin check, per ./auth.sdd."""

import hmac


class AuthService:
    def __init__(self, AIKANA_PASSWD: str) -> None:
        self.AIKANA_PASSWD = AIKANA_PASSWD

    def login(self, session: dict, password: str) -> bool:
        if not self.AIKANA_PASSWD or not hmac.compare_digest(password, self.AIKANA_PASSWD):
            return False
        session["admin"] = True
        return True

    def logout(self, session: dict) -> None:
        session.pop("admin", None)

    def is_admin(self, session: dict) -> bool:
        return bool(session.get("admin"))

