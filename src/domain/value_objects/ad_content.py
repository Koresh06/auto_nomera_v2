from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AdContent:
    plate_number: str | None      # None для STORE
    city: str
    price_text: str               # "Договорная" или "100 000 руб."

    contacts: str                 # уже готовая строка: "@user, +7..."

    caption: str | None = None
    image_file_id: str | None = None


