from src.domain.services.ad.plate_validator import validate_plate


def validate_plate_sale(v: str) -> str:
    return validate_plate(v, allow_mask=False)


def validate_plate_buy(v: str) -> str:
    return validate_plate(v, allow_mask=True)
