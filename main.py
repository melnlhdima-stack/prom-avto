import csv
import xml.etree.ElementTree as ET
import random
import requests
from datetime import datetime
from flask import Flask, Response

app = Flask(__name__)

CSV_URL = "https://ag-opt.com.ua"

# Словники для автоматичної унікалізації назв
PREFIXES = ["Купити", "Якісний", "Надійний", "Оригінальний", "Професійний", "Автомобільний"]
ADJECTIVES = ["для авто", "високої якості", "в машину", "преміум класу", "для ремонту"]

def calculate_margin(price_opt):
    """Розрахунок роздрібної ціни за вашою сіткою націнок."""
    if price_opt <= 100: return 1.00
    elif price_opt <= 250: return 0.80
    elif price_opt <= 500: return 0.60
    elif price_opt <= 750: return 0.50
    elif price_opt <= 1000: return 0.37
    elif price_opt <= 1500: return 0.32
    elif price_opt <= 2000: return 0.29
    elif price_opt <= 4000: return 0.25
    elif price_opt <= 6000: return 0.20
    elif price_opt <= 10000: return 0.18
    else: return 0.15

def unique_product_data(name, product_id, raw_description):
    """Генерація унікальних назв, описів та тегів пошуку."""
    clean_name = name.strip()
    
    # 1. Створення унікального тайтлу
    prefix = random.choice(PREFIXES)
    adj = random.choice(ADJECTIVES)
    unique_name = f"{prefix} {clean_name} {adj} (Арт. {product_id})"
    
    # 2. Ключові слова для пошуку всередині Prom
    words = [w.lower().strip(",.?!()\"") for w in clean_name.split() if len(w) > 3]
    base_keywords = [clean_name.lower(), "автотовари", "запчастини", "аксесуари для авто"]
    base_keywords.extend(words)
    keywords_str = ", ".join(list(dict.fromkeys(base_keywords))[:15])
    
    # 3. Нова структура опису (рандомізована)
    intro_options = [
        "Пропонуємо вашій увазі якісну позицію для вашого автомобіля.",
        "Оригінальна деталь та аксесуари, що забезпечать надійну роботу авто.",
        "Сучасне рішення для обслуговування транспортного засобу від перевіреного бренду."
    ]
    benefit_options = [
        "Виріб виготовлено з міцних матеріалів, стійких до зносу.",
        "Відповідає всім заводським стандартам якості та технічним вимогам.",
        "Легко встановлюється та має тривалий термін експлуатації."
    ]
    delivery_options = [
        "Швидка доставка Новою Поштою та Укрпоштою по всій Україні.",
        "Відправка в день замовлення. Гарантія якості від постачальника.",
        "Надійне пакування перед відправленням для безпечного транспортування."
    ]
    
    clean_desc = raw_description.replace("<p>", "").replace("</p>", "").replace("<strong>", "").replace("</strong>", "").strip()
    if not clean_desc or len(clean_desc) < 10:
        clean_desc = f"Товар {clean_name} призначений для якісного обслуговування та покращення вашого авто."

    unique_description = (
        f"<p><strong>{unique_name}</strong> — "
        f"{random.choice(intro_options)}<br><br>"
        f"{clean_desc}<br><br>"
        f"<strong>Основні переваги:</strong> {random.choice(benefit_options)}<br>"
        f"<strong>Доставка:</strong> {random.choice(delivery_options)}</p>"
    )
    
    return unique_name, unique_description, keywords_str

@app.route("/prom-feed")
def generate_feed():
    try:
        # Завантажуємо файл постачальника
        response = requests.get(CSV_URL, timeout=30)
        response.raise_for_status()
        
        # Обробка кодування (зокрема UTF-8 з невидимими символами BOM)
        response.encoding = 'utf-8-sig'
        lines = response.text.splitlines()
        reader = csv.DictReader(lines, delimiter=";")

        # Створення XML структури
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        yml_catalog = ET.Element("yml_catalog", date=current_time)
        shop = ET.SubElement(yml_catalog, "shop")

        ET.SubElement(shop, "name").text = "Автомагазин"
        ET.SubElement(shop, "company").text = "Дропшипінг Компанія"
        ET.SubElement(shop, "url").text = "https://prom.ua"

        currencies = ET.SubElement(shop, "currencies")
        ET.SubElement(currencies, "currency", id="UAH", rate="1")

        categories = ET.SubElement(shop, "categories")
        ET.SubElement(categories, "category", id="7090").text = "Автотовари"

        offers = ET.SubElement(shop, "offers")

        for row in reader:
            # Очищення ключів рядка від пробілів для точного пошуку колонок
            row_clean = {str(k).strip().lower(): v for k, v in row.items() if k is not None}

            # Розумний пошук ID колонки
            product_id = (
                row_clean.get("id") or 
                row_clean.get("id товара") or 
                row_clean.get("код") or 
                row_clean.get("артикул") or 
                row_clean.get("код_товара")
            )
            if not product_id:
                continue

            # Розумний пошук ціни
            raw_price = (
                row_clean.get("price") or 
                row_clean.get("цена") or 
                row_clean.get("ціна") or 
                "0"
            )
            try:
                price_opt = float(str(raw_price).replace(",", ".").strip())
            except ValueError:
                price_opt = 0.0

            if price_opt <= 0:
                continue

            # Обчислення нової ціни з унікальною націнкою
            margin_percent = calculate_margin(price_opt)
            price_retail = round(price_opt * (1 + margin_percent), 2)

            # Визначення статусу наявності
            raw_avail = row_clean.get("available") or row_clean.get("наличие") or row_clean.get("наявність") or "true"
            is_available = "true" if str(raw_avail).lower() in ["true", "1", "yes", "в наявності", "есть", "в наличии"] else "false"

            # Пошук назви та опису
            raw_name = row_clean.get("name") or row_clean.get("название") or row_clean.get("найменування") or row_clean.get("назва") or "Автотовар"
            raw_desc = row_clean.get("description") or row_clean.get("описание") or row_clean.get("опис") or ""

            # Унікалізація
            u_name, u_desc, u_keywords = unique_product_data(raw_name, product_id, raw_desc)

            # Запис у фід
            offer = ET.SubElement(offers, "offer", id=str(product_id), available=is_available)
            ET.SubElement(offer, "name").text = u_name
            ET.SubElement(offer, "price").text = str(price_retail)
            ET.SubElement(offer, "currencyId").text = "UAH"
            ET.SubElement(offer, "categoryId").text = "7090"
            ET.SubElement(offer, "description").text = f"<![CDATA[{u_desc}]]>"
            ET.SubElement(offer, "keywords").text = u_keywords

        xml_string = ET.tostring(yml_catalog, encoding="utf-8", method="xml")
        xml_declaration = b'<?xml version="1.0" encoding="UTF-8"?>\n'

        return Response(xml_declaration + xml_string, mimetype="text/xml")

    except Exception as e:
        return Response(f"Помилка генерації фіду: {str(e)}", status=500, mimetype="text/plain")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
