# hotel/templatetags/peso_filters.py

from django import template
from django.template.defaultfilters import floatformat
from django.contrib.humanize.templatetags.humanize import intcomma

register = template.Library()

from django import template

register = template.Library()

@register.filter
def peso(value):
    """Format a number as currency in PHP Peso."""
    try:
        return f"₱{value:,.2f}"
    except (ValueError, TypeError):
        return value