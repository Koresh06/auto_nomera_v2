from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class YooKassaReceiptItem:
    description: str
    quantity: Decimal
    unit_price: Decimal
    vat_code: int = 1  # 1 = без НДС (для самозанятого/УСН)
    payment_mode: str = "full_payment"
    payment_subject: str = "service"

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "quantity": f"{self.quantity:.2f}",
            "amount": {
                "value": f"{self.unit_price:.2f}",
                "currency": "RUB",
            },
            "vat_code": self.vat_code,
            "payment_mode": self.payment_mode,
            "payment_subject": self.payment_subject,
        }


@dataclass(frozen=True)
class YooKassaInvoiceRequest:
    amount: Decimal
    description: str
    return_url: str
    external_id: str
    user_id: int
    chat_id: int
    phone: str
    receipt_items: list[YooKassaReceiptItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "amount": {
                "value": f"{self.amount:.2f}",
                "currency": "RUB",
            },
            "confirmation": {
                "type": "redirect",
                "return_url": self.return_url,
            },
            "capture": True,
            "description": self.description,
            "metadata": {
                "user_id": self.user_id,
                "chat_id": self.chat_id,
                "external_id": self.external_id,
            },
            "receipt": {
                "customer": {
                    "phone": self.phone,
                },
                "items": [item.to_dict() for item in self.receipt_items],
            },
        }