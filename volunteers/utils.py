import re


PHONE_COUNTRY_CHOICES = [
    ("+33", "+33 France"),
    ("+32", "+32 Belgique"),
    ("+41", "+41 Suisse"),
    ("+39", "+39 Italie"),
    ("+34", "+34 Espagne"),
    ("+44", "+44 Royaume-Uni"),
    ("+49", "+49 Allemagne"),
    ("+1", "+1 USA/Canada"),
]


def generate_short_name(first_name: str) -> str:
    if not first_name:
        return ""
    parts = re.split(r"[-\s']+", first_name.strip())
    parts = [part for part in parts if part]
    if not parts:
        return ""
    initials = "-".join(part[0].upper() for part in parts)
    return f"{initials}."


def split_phone(phone: str) -> tuple[str, str]:
    if not phone:
        return "+33", ""
    value = phone.strip()
    if value.startswith("+"):
        pieces = value.split()
        if len(pieces) >= 2:
            country = pieces[0]
            number = "".join(pieces[1:]).strip()
            return country, number
    return "+33", value.replace(" ", "")


def normalize_phone_number(number: str) -> str:
    return re.sub(r"\s+", "", number or "")


def format_phone(country: str, number: str) -> str:
    country = (country or "+33").strip()
    number = normalize_phone_number(number)
    return f"{country} {number}".strip()
