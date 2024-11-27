from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Получаем значение по ключу из словаря"""
    return dictionary.get(key)
