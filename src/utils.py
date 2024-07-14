def clean_price_string(price_str):
    return price_str.replace('$', '').replace('USD', '').replace('.', '').strip()


def get_currency_type(price_str):
    return 'USD' if 'USD' in price_str else 'ARS'


def clean_area_string(area_str):
    return area_str.replace('m²', '').strip()


def clean_expenses_string(expenses_str):
    return expenses_str.replace('$', '').replace('.', '').replace('Expensas', '').strip()


def safe_extract(element, selector, attribute=None):
    found = element.select_one(selector)
    if not found:
        return None
    if attribute:
        return found.get(attribute)
    return found.get_text(strip=True)
