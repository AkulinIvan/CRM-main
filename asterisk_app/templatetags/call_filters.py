# asterisk_app/templatetags/call_filters.py
from django import template

register = template.Library()

@register.filter
def div(value, arg):
    """Делит значение на аргумент"""
    try:
        return int(value) / int(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0

@register.filter
def multiply(value, arg):
    """Умножает значение на аргумент"""
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def seconds_to_minutes(seconds):
    """Конвертирует секунды в минуты"""
    try:
        seconds = int(seconds)
        minutes = seconds // 60
        remainder = seconds % 60
        if remainder > 0:
            return f"{minutes} мин {remainder} сек"
        return f"{minutes} мин"
    except (ValueError, TypeError):
        return "0 сек"