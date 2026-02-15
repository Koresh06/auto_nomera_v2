from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StoreItem:
    plate: str
    price_text: str


@dataclass(frozen=True, slots=True)
class StoreContent:
    shop_name: str
    city: str
    contacts: str

    items: tuple[StoreItem, ...]
