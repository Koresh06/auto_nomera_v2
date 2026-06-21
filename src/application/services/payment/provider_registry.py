from src.application.ports.payment.provider import PaymentProvider
from src.domain.enums.payment import PaymentMethod
from src.domain.exceptions.payment import PaymentProviderNotFoundException


class PaymentProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[PaymentMethod, PaymentProvider] = {}

    def register(self, method: PaymentMethod, provider: PaymentProvider) -> None:
        self._providers[method] = provider

    def get(self, method: PaymentMethod) -> PaymentProvider:
        provider = self._providers.get(method)
        if provider is None:
            raise PaymentProviderNotFoundException(method)
        return provider