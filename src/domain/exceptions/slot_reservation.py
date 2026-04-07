class SlotReservationError(Exception):
    pass


class SlotAlreadyBooked(SlotReservationError):
    """Слот уже подтверждён и занят."""

    pass


class SlotAlreadyHeld(SlotReservationError):
    """Слот удерживается другим пользователем."""

    pass


class SlotHoldNotFound(SlotReservationError):
    """Нет активного HOLD (например, истёк TTL)."""

    pass


class SlotHoldOwnerMismatch(SlotReservationError):
    """HOLD есть, но принадлежит другому owner/ad."""

    pass
