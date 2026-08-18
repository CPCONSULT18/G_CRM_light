"""Normalization helpers shared by importer, matcher, and views."""

import re

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\+?[0-9][0-9\s\-\./()]{5,}[0-9]")

# Legal-form markers stripped when comparing company names.
LEGAL_FORMS = re.compile(
    r"\b(gmbh|ag|kgaa|kg|ohg|gbr|& co\.?|und co\.?|ges\.?|mbh|ug|ltd|llc|inc|"
    r"e\.?k\.?|e\.?v\.?|limited|s\.?a\.?|s\.?r\.?l\.?|plc)\b",
    re.IGNORECASE,
)


def norm_email(email):
    if not email:
        return ""
    return email.strip().lower()


def base_domain(email_or_domain):
    """Extract registrable-ish base domain from an email or domain string."""
    s = (email_or_domain or "").strip().lower()
    if "@" in s:
        s = s.split("@")[-1]
    s = re.sub(r"^www\.", "", s)
    s = re.sub(r"^m\.", "", s)
    s = re.sub(r"^(https?://)?", "", s)
    s = s.rstrip("/").split("/")[0]
    return s


def norm_phone(phone, country_code="49"):
    """Convert a phone string to a comparable E.164-ish key.

    Keeps digits and a leading '+'. Removes spaces/dashes/braces. German
    national format (0XX...) gets country code prepended when it starts with 0.
    """
    if not phone:
        return ""
    p = phone.strip()
    if not p:
        return ""
    plus = p.startswith("+")
    digits = re.sub(r"\D", "", p)
    if not digits:
        return ""
    if plus:
        return "+" + digits
    if digits.startswith("00"):
        return "+" + digits[2:]
    if digits.startswith("0"):
        return "+" + str(country_code) + digits[1:]
    return digits


def norm_name(name):
    """Uppercase + strip legal forms + punctuation for fuzzy name compare."""
    if not name:
        return ""
    s = name.upper()
    s = LEGAL_FORMS.sub(" ", s)
    s = re.sub(r"[^A-Z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_contact_cell(cell):
    """Extract (name, email, phone) from a single 'Contact at Dealer' cell."""
    if not cell:
        return ("", "", "")
    raw = cell.strip()
    emails = re.findall(EMAIL_RE, raw)
    email = emails[0] if emails else ""

    phones = re.findall(PHONE_RE, raw)
    phone = phones[0].strip() if phones else ""

    # Remove email(s) and phone tokens to leave the name.
    rest = raw
    for e in emails:
        rest = rest.replace(e, " ")
    for p in phones:
        rest = rest.replace(p, " ")
    name = re.sub(r"\s+", " ", rest).strip(" ,;-|()/")
    return (name, email, phone)