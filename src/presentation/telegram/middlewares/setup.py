from aiogram import Dispatcher
from dishka import AsyncContainer

from src.presentation.telegram.middlewares.block import BlockCheckMiddleware


def setup_middlewares(
    dp: Dispatcher,
    container: AsyncContainer,
) -> None:
    dp.update.outer_middleware(BlockCheckMiddleware())
