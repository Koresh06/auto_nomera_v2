"""
Coverage for src/application/use_cases/user/* — previously entirely untested.
"""

from decimal import Decimal

import pytest

from src.application.dtos.user import UpdateUserDTO
from src.application.exceptions.user import (
    UserAlreadyExistsException,
    UserNotFoundException,
)
from src.application.use_cases.user.admin_adjust_balance import (
    AdminAdjustBalanceCommand,
    AdminAdjustBalanceUseCase,
)
from src.application.use_cases.user.get_admin import GetAdminsCommand, GetAdminsUseCase
from src.application.use_cases.user.get_by_id import GetByIdRequest, GetByIdUserUseCase
from src.application.use_cases.user.get_by_tg_id import (
    GetByTgIdUserUseCase,
    GetTgIdRequest,
)
from src.application.use_cases.user.manage_admin import (
    AdminAction,
    ManageAdminCommand,
    ManageAdminUseCase,
)
from src.application.use_cases.user.register import (
    RegisterUserUseCase,
    UserRegisterRequest,
)
from src.application.use_cases.user.set_block import (
    BlockAction,
    SetUserBlockCommand,
    SetUserBlockUseCase,
)
from src.application.use_cases.user.top_up_balance import (
    TopUpBalanceRequest,
    TopUpBalanceUseCase,
)
from src.application.use_cases.user.update import UpdateUserRequest, UpdateUserUseCase
from src.domain.entities.region import Region
from src.domain.entities.user import User
from src.domain.enums.region import RegionStatus
from src.domain.enums.role import UserRole
from src.domain.exceptions.region import RegionDisabledError
from src.domain.exceptions.user import InsufficientBalance
from src.domain.services.region.region_guard import RegionGuard
from src.domain.value_objects.region_metadata import RegionMetadata
from src.domain.value_objects.region_settings import RegionSettings
from src.domain.value_objects.timezone_name import TimezoneName


class FakeUserRepo:
    def __init__(self, users: list[User] | None = None) -> None:
        self._by_id = {u.id: u for u in (users or [])}
        self._by_tg = {u.tg_id: u for u in (users or [])}
        self.added: list[User] = []
        self.saved: list[User] = []
        self.updated: list[tuple[int, UpdateUserDTO]] = []

    async def add(self, user: User) -> User:
        self.added.append(user)
        self._by_id[user.id] = user
        self._by_tg[user.tg_id] = user
        return user

    async def get_by_id_for_update(self, user_id):

        return await self.get_by_id(user_id)

    async def get_by_id(self, user_id: int) -> User | None:
        return self._by_id.get(user_id)

    async def get_by_tg_id(self, tg_id: int) -> User | None:
        return self._by_tg.get(tg_id)

    async def save(self, user: User) -> None:
        self.saved.append(user)
        self._by_id[user.id] = user

    async def update(self, tg_id: int, data: UpdateUserDTO) -> User:
        self.updated.append((tg_id, data))
        return self._by_tg[tg_id]

    async def get_by_role(self, role: UserRole) -> list[User]:
        return [u for u in self._by_id.values() if u.role == role]


class FakeRegionRepo:
    def __init__(self, region: Region | None) -> None:
        self._region = region

    async def get_by_id(self, region_id: int) -> Region | None:
        if self._region and self._region.id == region_id:
            return self._region
        return None


class FakeBlockCache:
    def __init__(self) -> None:
        self.flags: dict[int, tuple[bool, bool]] = {}

    async def get_flags(self, tg_id: int):
        return self.flags.get(tg_id)

    async def set_flags(
        self, tg_id: int, *, is_blocked: bool, is_payment_blocked: bool
    ) -> None:
        self.flags[tg_id] = (is_blocked, is_payment_blocked)

    async def invalidate(self, tg_id: int) -> None:
        self.flags.pop(tg_id, None)


class FakeTransactionManager:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


def make_user(**overrides) -> User:
    defaults = dict(
        id=1,
        tg_id=1001,
        role=UserRole.USER,
        phone=None,
        region_id=1,
        balance=Decimal("100"),
    )
    defaults.update(overrides)
    return User(**defaults)


def make_region(status: RegionStatus = RegionStatus.ACTIVE) -> Region:
    return Region(
        id=1,
        title="Test",
        timezone=TimezoneName("Europe/Moscow"),
        channel_id=-100123,
        channel_username="testchannel",
        status=status,
        metadata=RegionMetadata(),
        settings=RegionSettings(),
    )


# ---------- AdminAdjustBalanceUseCase ----------


async def test_admin_adjust_balance_positive_tops_up():
    user = make_user(balance=Decimal("100"))
    tx = FakeTransactionManager()
    use_case = AdminAdjustBalanceUseCase(
        user_repo=FakeUserRepo([user]), transaction_manager=tx
    )

    dto = await use_case(AdminAdjustBalanceCommand(user_id=1, amount=Decimal("50")))

    assert dto.balance == Decimal("150")
    assert tx.commits == 1


async def test_admin_adjust_balance_negative_charges():
    user = make_user(balance=Decimal("100"))
    use_case = AdminAdjustBalanceUseCase(
        user_repo=FakeUserRepo([user]), transaction_manager=FakeTransactionManager()
    )

    dto = await use_case(AdminAdjustBalanceCommand(user_id=1, amount=Decimal("-30")))

    assert dto.balance == Decimal("70")


async def test_admin_adjust_balance_zero_raises():
    use_case = AdminAdjustBalanceUseCase(
        user_repo=FakeUserRepo([make_user()]),
        transaction_manager=FakeTransactionManager(),
    )

    with pytest.raises(ValueError):
        await use_case(AdminAdjustBalanceCommand(user_id=1, amount=Decimal("0")))


async def test_admin_adjust_balance_negative_exceeding_balance_raises():
    user = make_user(balance=Decimal("10"))
    use_case = AdminAdjustBalanceUseCase(
        user_repo=FakeUserRepo([user]), transaction_manager=FakeTransactionManager()
    )

    with pytest.raises(InsufficientBalance):
        await use_case(AdminAdjustBalanceCommand(user_id=1, amount=Decimal("-50")))


async def test_admin_adjust_balance_unknown_user_raises():
    use_case = AdminAdjustBalanceUseCase(
        user_repo=FakeUserRepo([]), transaction_manager=FakeTransactionManager()
    )

    with pytest.raises(UserNotFoundException):
        await use_case(AdminAdjustBalanceCommand(user_id=999, amount=Decimal("10")))


# ---------- GetAdminsUseCase ----------


async def test_get_admins_returns_only_admins():
    admin = make_user(id=1, tg_id=1, role=UserRole.ADMIN)
    regular = make_user(id=2, tg_id=2, role=UserRole.USER)
    use_case = GetAdminsUseCase(user_repo=FakeUserRepo([admin, regular]))

    result = await use_case(GetAdminsCommand())

    assert len(result) == 1
    assert result[0].id == 1


# ---------- GetByIdUserUseCase / GetByTgIdUserUseCase ----------


async def test_get_by_id_raises_for_unknown_user():
    use_case = GetByIdUserUseCase(user_repo=FakeUserRepo([]))
    with pytest.raises(UserNotFoundException):
        await use_case(GetByIdRequest(user_id=1))


async def test_get_by_id_returns_dto():
    use_case = GetByIdUserUseCase(user_repo=FakeUserRepo([make_user()]))
    dto = await use_case(GetByIdRequest(user_id=1))
    assert dto.id == 1


async def test_get_by_tg_id_raises_for_unknown_user():
    use_case = GetByTgIdUserUseCase(user_repo=FakeUserRepo([]))
    with pytest.raises(UserNotFoundException):
        await use_case(GetTgIdRequest(tg_id=1001))


async def test_get_by_tg_id_returns_dto():
    use_case = GetByTgIdUserUseCase(user_repo=FakeUserRepo([make_user()]))
    dto = await use_case(GetTgIdRequest(tg_id=1001))
    assert dto.tg_id == 1001


# ---------- ManageAdminUseCase ----------


async def test_manage_admin_promote():
    user = make_user(role=UserRole.USER)
    use_case = ManageAdminUseCase(
        user_repo=FakeUserRepo([user]), transaction_manager=FakeTransactionManager()
    )

    dto = await use_case(ManageAdminCommand(user_id=1, action=AdminAction.PROMOTE))

    assert dto.role == UserRole.ADMIN


async def test_manage_admin_revoke():
    user = make_user(role=UserRole.ADMIN)
    use_case = ManageAdminUseCase(
        user_repo=FakeUserRepo([user]), transaction_manager=FakeTransactionManager()
    )

    dto = await use_case(ManageAdminCommand(user_id=1, action=AdminAction.REVOKE))

    assert dto.role == UserRole.USER


async def test_manage_admin_unknown_user_raises():
    use_case = ManageAdminUseCase(
        user_repo=FakeUserRepo([]), transaction_manager=FakeTransactionManager()
    )
    with pytest.raises(UserNotFoundException):
        await use_case(ManageAdminCommand(user_id=1, action=AdminAction.PROMOTE))


# ---------- RegisterUserUseCase ----------


async def test_register_user_creates_new_user():
    region = make_region()
    repo = FakeUserRepo([])
    use_case = RegisterUserUseCase(
        region_guard=RegionGuard(FakeRegionRepo(region)),
        user_repo=repo,
        transaction_manager=FakeTransactionManager(),
    )

    await use_case(
        UserRegisterRequest(tg_id=1001, region_id=1, username="ivan", full_name="Ivan")
    )

    assert len(repo.added) == 1
    assert repo.added[0].tg_id == 1001


async def test_register_user_raises_if_already_exists():
    region = make_region()
    existing = make_user()
    use_case = RegisterUserUseCase(
        region_guard=RegionGuard(FakeRegionRepo(region)),
        user_repo=FakeUserRepo([existing]),
        transaction_manager=FakeTransactionManager(),
    )

    with pytest.raises(UserAlreadyExistsException):
        await use_case(
            UserRegisterRequest(
                tg_id=existing.tg_id, region_id=1, username=None, full_name=None
            )
        )


async def test_register_user_raises_if_region_disabled():
    region = make_region(status=RegionStatus.DISABLED)
    use_case = RegisterUserUseCase(
        region_guard=RegionGuard(FakeRegionRepo(region)),
        user_repo=FakeUserRepo([]),
        transaction_manager=FakeTransactionManager(),
    )

    with pytest.raises(RegionDisabledError):
        await use_case(
            UserRegisterRequest(tg_id=1001, region_id=1, username=None, full_name=None)
        )


# ---------- SetUserBlockUseCase ----------


async def test_set_user_block_blocks_user_and_updates_cache():
    user = make_user()
    cache = FakeBlockCache()
    use_case = SetUserBlockUseCase(
        user_repo=FakeUserRepo([user]),
        block_cache=cache,
        transaction_manager=FakeTransactionManager(),
    )

    dto = await use_case(SetUserBlockCommand(user_id=1, action=BlockAction.BLOCK_USER))

    assert dto.is_blocked is True
    assert cache.flags[user.tg_id] == (True, False)


async def test_set_user_block_unblock_payments():
    user = make_user()
    user.block_payments()
    use_case = SetUserBlockUseCase(
        user_repo=FakeUserRepo([user]),
        block_cache=FakeBlockCache(),
        transaction_manager=FakeTransactionManager(),
    )

    dto = await use_case(
        SetUserBlockCommand(user_id=1, action=BlockAction.UNBLOCK_PAYMENTS)
    )

    assert dto.is_payment_blocked is False


# ---------- TopUpBalanceUseCase ----------


async def test_top_up_balance_increases_balance():
    user = make_user(balance=Decimal("10"))
    tx = FakeTransactionManager()
    use_case = TopUpBalanceUseCase(
        user_repo=FakeUserRepo([user]), transaction_manager=tx
    )

    await use_case(TopUpBalanceRequest(user_id=1, amount=Decimal("90")))

    assert user.balance == Decimal("100")
    assert tx.commits == 1


async def test_top_up_balance_rejects_non_positive_amount():
    use_case = TopUpBalanceUseCase(
        user_repo=FakeUserRepo([make_user()]),
        transaction_manager=FakeTransactionManager(),
    )

    with pytest.raises(ValueError):
        await use_case(TopUpBalanceRequest(user_id=1, amount=Decimal("0")))


async def test_top_up_balance_unknown_user_raises():
    use_case = TopUpBalanceUseCase(
        user_repo=FakeUserRepo([]), transaction_manager=FakeTransactionManager()
    )

    with pytest.raises(UserNotFoundException):
        await use_case(TopUpBalanceRequest(user_id=1, amount=Decimal("10")))


# ---------- UpdateUserUseCase ----------


async def test_update_user_calls_repo_update():
    user = make_user()
    repo = FakeUserRepo([user])
    use_case = UpdateUserUseCase(
        user_repo=repo, transaction_manager=FakeTransactionManager()
    )

    data = UpdateUserDTO(full_name="New Name")
    await use_case(UpdateUserRequest(tg_id=user.tg_id, data=data))

    assert repo.updated == [(user.tg_id, data)]


async def test_update_user_unknown_user_raises():
    use_case = UpdateUserUseCase(
        user_repo=FakeUserRepo([]), transaction_manager=FakeTransactionManager()
    )

    with pytest.raises(UserNotFoundException):
        await use_case(UpdateUserRequest(tg_id=1001, data=UpdateUserDTO()))
