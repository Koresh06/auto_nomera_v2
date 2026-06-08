from dataclasses import dataclass, replace

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

    def with_image(self, image_file_id: str) -> "AdContent":
        return replace(self, image_file_id=image_file_id)
