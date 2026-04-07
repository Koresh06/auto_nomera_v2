class SlotError(Exception):
    pass


class SlotAlreadyHeld(SlotError):
    """Слот уже удерживается другим пользователем."""

    pass


class SlotAlreadyBooked(SlotError):
    """Слот уже занят (подтверждён)."""

    pass


class SlotHoldExpired(SlotError):
    """HOLD истёк (например, при попытке подтвердить оплату)."""

    pass
