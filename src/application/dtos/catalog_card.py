from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogCardDTO:
    plate: str
    city: str
    price: str
    contacts: str
    image_file_id: str | None
    is_urgent: bool
    pub_time: str | None  # для pre-publication
    ad_type_display: str
    ad_text: str
    owner_tg_id: int | None = None
    owner_link: str | None = None
    services_line: str | None = None