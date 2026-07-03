from enum import Enum


class MailingType(str, Enum):
    TO_ALL = "all"
    TO_REGION = "region"
    TO_ALL_REGIONS = "all_regions"

    def label(self) -> str:
        match self:
            case MailingType.TO_ALL:
                return "🧍 Всем пользователям"
            case MailingType.TO_REGION:
                return "🌍 По выбранному региону"
            case MailingType.TO_ALL_REGIONS:
                return "📢 Во все каналы"
            case _:
                return self.value