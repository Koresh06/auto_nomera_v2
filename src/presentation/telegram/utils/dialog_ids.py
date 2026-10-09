"""Более уникальные id контекстов aiogram-dialog.

Библиотека генерирует id как ``int(time.time()) % 10**8 + randint(0, 99) * 10**8``:
всего 100 вариантов на секунду. Если два диалога одного пользователя
созданы в одну секунду и id совпали (1 из 100), второй контекст
перезаписывает первый — кнопки первого начинают падать с UnknownIntent
(«Произошла ошибка»). Берём 48 случайных бит (~2.8e14 вариантов): id
длиннее всего на 3 символа (callback_data укладывается в лимит 64 байта).
"""

import random

from aiogram_dialog.api.entities import stack as _stack


def _new_int_id() -> int:
    return random.getrandbits(48) or 1


def install() -> None:
    _stack.new_int_id = _new_int_id
