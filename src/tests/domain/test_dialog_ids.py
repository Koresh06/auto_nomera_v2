from aiogram_dialog.api.entities import stack

from src.presentation.telegram.utils import dialog_ids


def test_ids_created_in_the_same_moment_do_not_collide(monkeypatch):
    monkeypatch.setattr(stack, "new_int_id", stack.new_int_id)  # откат после теста
    dialog_ids.install()

    ids = [stack.new_id() for _ in range(2000)]

    # 2000 id за доли секунды: у библиотечного генератора (100 вариантов
    # на секунду) здесь были бы десятки совпадений
    assert len(set(ids)) == len(ids)
    assert max(len(i) for i in ids) <= 9
