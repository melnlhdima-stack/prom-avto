import csv
import xml.etree.ElementTree as ET
import random
import requests
from datetime import datetime
from flask import Flask, Response

app = Flask(__name__)

# Посилання на CSV-файл вашого постачальника
CSV_URL = "https://ag-opt.com.ua"

# Набори слів для автоматичної унікалізації назв і текстів
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
    
    # 3. Структурована рандомізована модель опису
    intro_options = [
        "Пропонуємо вашій увазі якісну позицію для вашого автомобіля.",
        "Оригінальна деталь та аксесуари, що забезпечать надійну роботу авто.",
        "Сучасне рішення для обслуговування транспортного засобу від перевіреного бренду."
    ]
    benefit_options = [
        "Виріб виготовлено з міцних матеріалів, стійких до зносу.",
        "Відповідає всім заводским стандартам якості та технічним вимогам.",
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

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def generate_feed(path):
    try:
        # Емуляція браузера Chrome для обходу блокувань постачальника
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(CSV_URL, headers=headers, timeout=30)
        response.raise_for_status()
        
        response.encoding = 'utf-8-sig'
        lines = response.text.splitlines()
        
        if not lines:
            return Response("Помилка: Файл постачальника порожній", status=400, mimetype="text/plain")

        # Автоматичне визначення розділювача за першим рядком
        delimiter = ";" if ";" in lines[0] else ","
        reader = csv.reader(lines, delimiter=delimiter)
        
        # Пропускаємо перший рядок із заголовками колонок
        next(reader, None)

        # Базовий каркас XML каталогу
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
            if not row or len(row) < 3:
                continue

            # Читання даних за порядковими номерами колонок (0 - ID, 1 - назва, 2 - ціна, 3 - опис)
            product_id = row[0].strip()
            raw_name = row[1].strip() if len(row) > 1 else "Автотовар"
            raw_price = row[2].strip() if len(row) > 2 else "0"
            raw_desc = row[3].strip() if len(row) > 3 else ""

            if not product_id:
                continue

            try:
                price_opt = float(raw_price.replace(",", ".").strip())
            except ValueError:
                price_opt = 0.0

            if price_opt <= 0:
                continue

            # Обчислення ціни з вашою націнкою
            margin_percent = calculate_margin(price_opt)
            price_retail = round(price_opt * (1 + margin_percent), 2)

            # Генерація унікальних даних
            u_name, u_desc, u_keywords = unique_product_data(raw_name, product_id, raw_desc)

            # Формування елемента товару
            offer = ET.SubElement(offers, "offer", id=str(product_id), available="true")
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
        return Response(f"Помилка сервера: {str(e)}", status=500, mimetype="text/plain")
