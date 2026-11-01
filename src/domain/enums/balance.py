from enum import Enum


class BalanceTransactionKind(str, Enum):
    TOPUP = "topup"  # пополнение внешним платежом
    COMPENSATION = "compensation"  # возврат на баланс внешнего платежа
    ADMIN_CREDIT = "admin_credit"  # начисление админом
    ADMIN_DEBIT = "admin_debit"  # списание админом
    SLOT_PURCHASE = "slot_purchase"  # покупка платного слота с баланса
    SERVICE_PURCHASE = "service_purchase"  # покупка услуги с баланса
    PRE_PUBLICATION_PURCHASE = "pre_publication_purchase"  # подписка с баланса
