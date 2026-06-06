from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RegionMetadata:
    tg_group_url: str | None = None
    vk_group_url: str | None = None
    max_channel_url: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("tg_group_url", "vk_group_url", "max_channel_url"):
            value = getattr(self, field_name)
            if value is not None and not value.strip():
                object.__setattr__(self, field_name, None)

    @property
    def has_any(self) -> bool:
        return any([self.tg_group_url, self.vk_group_url, self.max_channel_url])