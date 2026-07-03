from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from src.domain.entities.base import Entity
from src.domain.enums.role import UserRole
from src.domain.exceptions.user import InsufficientBalance, InvalidTelegramId, EmptyUsername


@dataclass(kw_only=True)
class User(Entity):
    tg_id: int
    username: str | None = None
    full_name: str | None = None
    role: UserRole = UserRole.USER
    phone: str | None
    region_id: int
    balance: Decimal = Decimal("0.00")
    is_blocked: bool = False
    is_payment_blocked: bool = False
    pre_publication_expires_at: datetime | None = None

    @property
    def has_pre_publication(self) -> bool:
        if self.pre_publication_expires_at is None:
            return False
        return self.pre_publication_expires_at > datetime.now(timezone.utc)

    def activate_pre_publication(self, days: int = 30) -> None:
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        base = self.pre_publication_expires_at
        if base is None or base <= now:
            base = now
        self.pre_publication_expires_at = base + timedelta(days)
        self.touch()

    @classmethod
    def register(
        cls,
        *,
        tg_id: int,
        region_id: int,
        username: str | None = None,
        full_name: str | None = None,
        phone: str | None = None,
    ) -> "User":
        if tg_id <= 0:
            raise InvalidTelegramId(tg_id)

        if username is not None and not username.strip():
            raise EmptyUsername()

        user = cls(
            tg_id=tg_id,
            username=username,
            full_name=full_name,
            phone=phone,
            region_id=region_id,
        )
        return user

    def promote_to_admin(self) -> None:
        self.role = UserRole.ADMIN
        self.touch()

    def revoke_admin(self) -> None:
        self.role = UserRole.USER
        self.touch()

    def block(self) -> None:
        self.is_blocked = True
        self.touch()

    def unblock(self) -> None:
        self.is_blocked = False
        self.touch()

    def block_payments(self) -> None:
        self.is_payment_blocked = True
        self.touch()

    def unblock_payments(self) -> None:
        self.is_payment_blocked = False
        self.touch()

    def change_region(self, region_id: int) -> None:
        self.region_id = region_id
        self.touch()

    def top_up(self, amount: Decimal) -> None:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        self.balance += amount
        self.touch()
    
    def charge(self, amount: Decimal) -> None:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if self.balance < amount:
            raise InsufficientBalance
        self.balance -= amount
        self.touch()

