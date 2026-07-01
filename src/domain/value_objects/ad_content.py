from dataclasses import dataclass

from src.domain.value_objects.contacts import Contacts
from src.domain.value_objects.price import Price


@dataclass(frozen=True, slots=True)
class AdContent:
    plate_number: str | None
    city: str
    price: Price

    contacts: Contacts

    caption: str | None = None
    image_file_id: str | None = None