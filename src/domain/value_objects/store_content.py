from dataclasses import dataclass

from src.domain.value_objects.contacts import Contacts
from src.domain.value_objects.price import Price


@dataclass(frozen=True, slots=True)
class StoreItem:
    plate: str
    price: Price


@dataclass(frozen=True, slots=True)
class StoreContent:
    shop_name: str
    city: str
    contacts: Contacts

    items: tuple[StoreItem, ...]
