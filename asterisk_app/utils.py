import phonenumbers
from django.core.exceptions import ValidationError

def validate_phone_number(number):
    try:
        parsed = phonenumbers.parse(number, "RU")
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except Exception as e:
        raise ValidationError(f"Invalid phone number: {number}")