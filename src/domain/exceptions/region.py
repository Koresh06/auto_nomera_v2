class RegionDomainError(Exception):
    pass


class InvalidTimezone(RegionDomainError):
    """Таймзона не соответствует формату"""
    pass


class InvalidChannelId(RegionDomainError):
    """ID канала не соответствует формату"""
    pass


class InvalidSlotTimes(RegionDomainError):
    """Время начала и конца слота не соответствуют формату"""
    pass


class InvalidDaysRange(RegionDomainError):
    """Время начала и конца слота не соответствуют формату"""
    pass


class InvalidSystemPaidSlotsCount(RegionDomainError):
    """Время начала и конца слота не соответствуют формату"""
    pass


class RegionNotFoundException(RegionDomainError):
    """Регион не найден"""
    pass

class RegionDisabledError(RegionDomainError):
    """Регион не активен"""
    pass