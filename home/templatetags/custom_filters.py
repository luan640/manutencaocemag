from django import template
from datetime import date

register = template.Library()

@register.filter
def days_since(value):
    """Calcula o número de dias desde uma data passada."""
    if not value:
        return ""  # Retorna vazio se não houver data
    delta = date.today() - value.date()  # Calcula a diferença em dias
    if delta.days == 1:
        return "há 1 dia"
    return f"há {delta.days} dias"
