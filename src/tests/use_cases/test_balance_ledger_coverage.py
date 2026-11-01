"""Журнал полон, только если каждое изменение баланса его пишет: новое место
с user.charge()/top_up() без записи обесценило бы выручку молча. Поведение
каждого места проверяет integration/telegram/test_balance_ledger.py."""

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2] / "application"
_MUTATION = re.compile(r"\.(charge|top_up)\(")


def _mutating_files() -> dict[str, str]:
    return {
        path.name: text
        for path in ROOT.rglob("*.py")
        if _MUTATION.search(text := path.read_text())
    }


def test_known_call_sites_are_listed_here():
    """Упало — значит появилось новое место: добавьте запись в журнал и тест."""
    assert sorted(_mutating_files()) == [
        "admin_adjust_balance.py",
        "buy_pre_publication_service.py",
        "buy_publication_service.py",
        "confirm.py",
        "confirm_paid_slot_from_balance.py",
    ]


def test_every_call_site_writes_to_the_ledger():
    assert [n for n, t in _mutating_files().items() if "ledger.record(" not in t] == []
