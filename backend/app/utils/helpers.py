from datetime import UTC, datetime

ETH_EPOCH = 1724221


def utc_now() -> datetime:
    return datetime.now(UTC)


def gregorian_to_jdn(year: int, month: int, day: int) -> int:
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045


def ethiopian_to_jdn(year: int, month: int, day: int) -> int:
    if month < 1 or month > 13:
        raise ValueError("Ethiopian month must be between 1 and 13")
    max_day = 30 if month <= 12 else (6 if year % 4 == 3 else 5)
    if day < 1 or day > max_day:
        raise ValueError("Invalid day for Ethiopian month")
    return ETH_EPOCH - 1 + 365 * (year - 1) + (year - 1) // 4 + 30 * (month - 1) + day


def jdn_to_gregorian(jdn: int) -> tuple[int, int, int]:
    a = jdn + 32044
    b = (4 * a + 3) // 146097
    c = a - (146097 * b) // 4
    d = (4 * c + 3) // 1461
    e = c - (1461 * d) // 4
    m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1
    month = m + 3 - 12 * (m // 10)
    year = 100 * b + d - 4800 + m // 10
    return year, month, day


def jdn_to_ethiopian(jdn: int) -> tuple[int, int, int]:
    year = (4 * (jdn - ETH_EPOCH) + 1463) // 1461
    while ethiopian_to_jdn(year + 1, 1, 1) <= jdn:
        year += 1
    while ethiopian_to_jdn(year, 1, 1) > jdn:
        year -= 1

    day_of_year = jdn - ethiopian_to_jdn(year, 1, 1)
    month = day_of_year // 30 + 1
    day = day_of_year % 30 + 1
    return year, month, day


def gregorian_to_ethiopian(year: int, month: int, day: int) -> tuple[int, int, int]:
    return jdn_to_ethiopian(gregorian_to_jdn(year, month, day))


def ethiopian_to_gregorian(year: int, month: int, day: int) -> tuple[int, int, int]:
    return jdn_to_gregorian(ethiopian_to_jdn(year, month, day))
