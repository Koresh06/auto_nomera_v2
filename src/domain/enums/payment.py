from enum import Enum


class PaymentPurpose(str, Enum):
    BALANCE_TOPUP = "balance_topup"        # просто пополнение баланса
    PUBLICATION_SERVICE = "publication_service"  # покупка услуги к публикации
    PRE_PUBLICATION = "pre_publication"    # подписка
    SLOT = "slot"                          # платный слот


class PaymentMethod(Enum):
    MANUAL_CARD = "manual_card"            # вручную
    CRYPTO = "crypto"                      # криптовалюта
    TELEGRAM_STARS = "telegram_stars"      # покупка звезд
    YOOKASSA = "yookassa"                  # покупка через yookassa


class PaymentStatus(Enum):
    PENDING = "pending"                    # ожидает оплаты
    WAITING_CONFIRMATION = "waiting_confirmation"  # ожидает подтверждения
    PAID = "paid"                          # оплачено
    FAILED = "failed"                      # не оплачено
    EXPIRED = "expired"                    # просрочено