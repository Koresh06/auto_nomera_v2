from dataclasses import fields

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dtos.user import UpdateUserDTO
from src.application.exceptions.user import UserNotFoundException
from src.domain.entities.user import User
from src.application.ports.user.user_repo import UserRepository
from src.infrastructure.database.models import UserModel


class SQLAlchemyUserRepo(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> User:
        user_model = UserModel.from_entity(user)
        self._session.add(user_model)
        await self._session.flush()
        await self._session.refresh(user_model)
        return user_model.to_entity()

    async def get_by_id(self, user_id: int) -> User | None:
        query = select(UserModel).where(UserModel.id == user_id)
        result = await self._session.execute(query)
        user_model = result.scalar_one_or_none()
        return user_model.to_entity() if user_model else None

    async def get_by_tg_id(self, tg_id: int) -> User | None:
        query = select(UserModel).where(UserModel.tg_id == tg_id)
        result = await self._session.execute(query)
        user_model = result.scalar_one_or_none()
        return user_model.to_entity() if user_model else None

    async def save(self, user: User) -> None:
        query = select(UserModel).where(UserModel.id == user.id)
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()
        if model is None:
            raise UserNotFoundException(user.id)
        UserModel._update_model(model, user)
        await self._session.flush()

    async def update(self, tg_id: int, data: UpdateUserDTO) -> User:
        query = select(UserModel).where(UserModel.tg_id == tg_id)
        result = await self._session.execute(query)
        user_model = result.scalar_one_or_none()
        if user_model is None:
            raise UserNotFoundException(tg_id)
    
        for field in fields(data):
            value = getattr(data, field.name)
            if value is not None and hasattr(user_model, field.name):
                setattr(user_model, field.name, value)
    
        await self._session.merge(user_model)
        await self._session.flush()
        return user_model.to_entity()