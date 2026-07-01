from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Price:
    value: int

    @staticmethod
    def format(value: int) -> str:
        if value == 0:
            return "Договорная"
        return f"{value:,} руб.".replace(",", " ")

    @property
    def display(self) -> str:
        return self.format(self.value)