import re

from src.application.dtos.region import RegionDTO

MOSCOW_CODES = {77, 97, 99, 50, 90}
SPB_CODES = {78, 98, 47}


def extract_region_codes(region: RegionDTO) -> list[int]:
    codes: list[str] = []
    if region.channel_username:
        codes += re.findall(r"\d+", region.channel_username)

    if region.title:
        match = re.match(r"^((?:\|\d+)+\|)", region.title.strip())
        if match:
            prefix = match.group(1)
            codes += re.findall(r"\d+", prefix)

    return [int(c) for c in codes]


def region_sort_key(region: RegionDTO) -> tuple[int, int]:
    codes = extract_region_codes(region)
    codes_set = set(codes)

    if codes_set & MOSCOW_CODES:
        return (0, 0)
    if codes_set & SPB_CODES:
        return (1, 0)
    if codes:
        return (2, min(codes))
    return (3, 999)


def sort_regions(regions: list[RegionDTO]) -> list[RegionDTO]:
    return sorted(regions, key=region_sort_key)
