from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RegionMetadata:
    data: dict

    def get_str(self, key: str) -> str | None:
        v = self.data.get(key)
        return v if isinstance(v, str) and v.strip() else None

    @property
    def tg_group_url(self) -> str | None:
        return self.get_str("tg_group_url")

    @property
    def vk_group_url(self) -> str | None:
        return self.get_str("vk_group_url")

    @property
    def max_channel_url(self) -> str | None:
        return self.get_str("max_channel_url")
