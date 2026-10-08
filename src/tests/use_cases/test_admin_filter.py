"""
Regression test for AUD-18: AdminFilter compared `user.role in UserRole.ADMIN`
instead of `==`. UserRole is a str Enum, so `in` performs substring matching
on the string value, not an enum comparison. It happened to work today only
because "user" isn't a substring of "admin" and vice versa — fragile, and a
future role whose value is a substring of "admin" (or contains it) would
silently get the wrong authorization result.
"""

from unittest.mock import AsyncMock


from src.application.dtos.user import UserDTO
from src.application.exceptions.user import UserNotFoundException
from src.domain.enums.role import UserRole
from src.presentation.telegram.features.admin.modules.menu.filter import AdminFilter


def make_user_dto(role: UserRole) -> UserDTO:
    return UserDTO(
        id=1,
        tg_id=1,
        username=None,
        full_name=None,
        role=role,
        phone=None,
        region_id=1,
        balance=0,
        is_blocked=False,
        is_payment_blocked=False,
        pre_publication_expires_at=None,
    )


async def test_admin_filter_true_for_bootstrap_admin():
    admin_filter = AdminFilter(admin_ids=[555])

    result = await admin_filter.is_admin(555, mediator=AsyncMock())

    assert result is True


async def test_admin_filter_true_for_db_admin_role():
    admin_filter = AdminFilter(admin_ids=[])
    mediator = AsyncMock()
    mediator.handle.return_value = make_user_dto(UserRole.ADMIN)

    result = await admin_filter.is_admin(1, mediator=mediator)

    assert result is True


async def test_admin_filter_false_for_regular_user():
    admin_filter = AdminFilter(admin_ids=[])
    mediator = AsyncMock()
    mediator.handle.return_value = make_user_dto(UserRole.USER)

    result = await admin_filter.is_admin(1, mediator=mediator)

    assert result is False


async def test_admin_filter_false_for_unknown_user():
    admin_filter = AdminFilter(admin_ids=[])
    mediator = AsyncMock()
    mediator.handle.side_effect = UserNotFoundException(1)

    result = await admin_filter.is_admin(1, mediator=mediator)

    assert result is False
