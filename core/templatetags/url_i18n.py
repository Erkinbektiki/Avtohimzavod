# core/templatetags/url_i18n.py
from django import template
from django.urls import translate_url

register = template.Library()

@register.simple_tag(takes_context=True)
def alt_url(context, lang_code: str):
    """
    Вернёт абсолютный URL текущей страницы с нужным языковым префиксом.
    Пример: {% alt_url 'en' %}
    """
    request = context["request"]
    return translate_url(request.build_absolute_uri(), lang_code)
