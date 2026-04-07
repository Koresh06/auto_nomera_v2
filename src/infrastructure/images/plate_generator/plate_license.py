from enum import StrEnum
import re
from typing import List, Optional
from abc import ABC, abstractmethod


class PlateTag(StrEnum):
    """Enumeration for license plate tags"""

    ROUND = "Круглые"
    MIRROR = "Зеркальные"
    FIRST_TEN = "ПерваяДесятка"
    SAME_LETTERS = "ОдинаковыеБуквы"
    SAME_DIGITS = "ОдинаковыеЦифры"


# Constants from your existing code
russian_number_letters = "АВЕКМНОРСТУХ"
english_number_letters = "ABEKMHOPCTYX"
number_letters = russian_number_letters + english_number_letters
russian_to_english = {
    russian_number_letters[i]: english_number_letters[i]
    for i in range(len(russian_number_letters))
}


class BaseLicensePlate(ABC):
    """Base class for all license plate types"""

    # Each subclass should define its own pattern
    PATTERN: re.Pattern = None

    def __init__(self, number: str):
        """
        Initialize license plate with preprocessing
        - Remove spaces
        - Convert Russian letters to English
        """
        # Remove spaces
        cleaned_number = number.replace(" ", "")

        # Convert Russian letters to English
        self.processed_number = "".join(
            russian_to_english.get(c, c) for c in cleaned_number.upper()
        )

        self.original_number = number

    @classmethod
    def matches(cls, number: str) -> bool:
        """Check if the number matches this plate type pattern"""
        if cls.PATTERN is None:
            return False
        # Remove spaces for pattern matching
        cleaned_number = number.replace(" ", "")
        return bool(re.fullmatch(cls.PATTERN, cleaned_number))

    @abstractmethod
    def get_main_part(self) -> str:
        """Get main part of the plate number"""
        raise NotImplementedError

    @abstractmethod
    def get_letters(self) -> str:
        """Get letters from the plate number"""
        raise NotImplementedError

    @abstractmethod
    def get_digits(self) -> str:
        """Get digits from the plate number (excluding region)"""
        raise NotImplementedError

    @abstractmethod
    def get_region_digits(self) -> str:
        """Get region digits"""
        raise NotImplementedError

    def __str__(self) -> str:
        return self.processed_number

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}<{self.original_number}>"

    def get_tags(self) -> List[PlateTag]:
        """Get list of tags for this license plate"""
        return get_plate_tags(self.get_letters(), self.get_digits())


class AutoLicensePlate(BaseLicensePlate):
    """License plate for cars (format: а999аа01)"""

    # Auto pattern: 1 letter/*, 3 digits/*, 2 letters/*, region 2-3 digits/*
    PATTERN = re.compile(
        rf"^[{number_letters}*][0-9*]{{3}}[{number_letters}*]{{2}}[0-9*]{{2,3}}$",
        flags=re.IGNORECASE,
    )

    def get_main_part(self) -> str:
        """Get main part of auto plate (positions 0, 1, 2, 3, 4, 5)"""
        return self.processed_number[:6]

    def get_letters(self) -> str:
        """Get letters from auto plate (positions 0, 4, 5)"""
        if len(self.processed_number) >= 6:
            return self.processed_number[0] + self.processed_number[4:6]
        return ""

    def get_digits(self) -> str:
        """Get digits from auto plate (positions 1, 2, 3)"""
        if len(self.processed_number) >= 4:
            return self.processed_number[1:4]
        return ""

    def get_region_digits(self) -> str:
        """Get region digits from auto plate"""
        return self.processed_number[6:]


class TrailerLicensePlate(BaseLicensePlate):
    """License plate for trailers (format: аа000001 or аа0000012)"""

    # 2 буквы + 4 цифры + 2–3 цифры региона
    PATTERN = re.compile(
        rf"^[{number_letters}*]{{2}}[0-9*]{{4}}[0-9*]{{2,3}}$", flags=re.IGNORECASE
    )

    def get_main_part(self) -> str:
        """2 буквы + 4 цифры"""
        return self.processed_number[:6]

    def get_letters(self) -> str:
        """2 буквы"""
        return self.processed_number[:2]

    def get_digits(self) -> str:
        """4 цифры основной части"""
        return self.processed_number[2:6]

    def get_region_digits(self) -> str:
        """2–3 цифры региона"""
        return self.processed_number[6:]


class MotoLicensePlate(BaseLicensePlate):
    """License plate for motorcycles (format: 9999аа01)"""

    # Moto pattern: 4 digits/*, 2 letters/*, 2 digits/*
    PATTERN = re.compile(
        rf"^[0-9*]{{4}}[{number_letters}*]{{2}}[0-9*]{{2,3}}$", flags=re.IGNORECASE
    )

    def get_main_part(self) -> str:
        """Get main part of moto plate (positions 0, 1, 2, 3)"""
        return self.processed_number[:6]

    def get_letters(self) -> str:
        """Get letters from moto plate (positions 4, 5)"""
        if len(self.processed_number) >= 6:
            return self.processed_number[4:6]
        return ""

    def get_digits(self) -> str:
        """Get digits from moto plate (positions 0, 1, 2, 3)"""
        if len(self.processed_number) >= 4:
            return self.processed_number[:4]
        return ""

    def get_region_digits(self) -> str:
        """Get region digits from moto plate"""
        return self.processed_number[6:]


def create_license_plate(number: str) -> Optional[BaseLicensePlate]:
    """
    Factory function to create appropriate license plate object
    based on pattern matching using class methods
    """
    # List of all license plate classes
    plate_classes = [AutoLicensePlate, TrailerLicensePlate, MotoLicensePlate]

    for plate_class in plate_classes:
        if plate_class.matches(number):
            return plate_class(number)


def get_plate_tags(letters: str, digits: str) -> List[PlateTag]:
    """
    Get list of tags for a license plate based on its characteristics
    """
    tags = []

    if not letters or not digits:
        return tags

    # Remove asterisks for tag analysis
    clean_letters = letters.replace("*", "")
    clean_digits = digits.replace("*", "")

    if not clean_letters or not clean_digits:
        return tags

    # Same letters (all letters are the same and valid in Latin alphabet)
    if len(clean_letters) > 1 and len(set(clean_letters)) == 1:
        if clean_letters[0] in english_number_letters:
            tags.append(PlateTag.SAME_LETTERS)

    if len(clean_digits) < 3:
        return tags

    # Round numbers (100, 200, 300, ..., 900)
    power = 10 ** (len(clean_digits) - 1)
    if any(int(clean_digits) == i * power for i in range(1, 10)):
        tags.append(PlateTag.ROUND)

    # First ten (001-009)
    if any(int(clean_digits) == i for i in range(1, 10)):
        tags.append(PlateTag.FIRST_TEN)

    # Same digits (111-999, all digits are the same)
    if len(set(clean_digits)) == 1 and clean_digits[0] != "0":
        tags.append(PlateTag.SAME_DIGITS)

    # Mirror numbers (palindromic digits and/or letters)
    def is_palindrome(s: str) -> bool:
        return s == s[::-1] and len(s) > 1

    # Check if digits are palindromic
    if is_palindrome(clean_digits):
        tags.append(PlateTag.MIRROR)

    return tags
