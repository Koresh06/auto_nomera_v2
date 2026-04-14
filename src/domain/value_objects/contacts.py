from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Contacts:
    username: str | None = None
    phone: str | None = None

    @property
    def display(self) -> str:
        parts = []
        if self.username:
            parts.append(f"@{self.username.lstrip('@')}")
        if self.phone:
            parts.append(f"<code>{self.phone}</code>")
        return ", ".join(parts) if parts else ""

    @classmethod
    def from_user(cls, username: str | None, phone: str | None) -> "Contacts":
        return cls(username=username, phone=phone)