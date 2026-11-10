import csv
import xml.etree.ElementTree as ET
import random
import requests
from datetime import datetime
from flask import Flask, Response

app = Flask(__name__)

CSV_URL = "https://ag-opt.com.ua"

# Словар для унікалізації назв та пошукових слів
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
    """Генерація унікальних назв, описів та тегів для Prom."""
    # Очищення базової назви
    clean_name = name.strip()
    
    # 1. Унікалізація назви
    prefix = random.choice(PREFIXES)
    adj = random.choice(ADJECTIVES)
    # Зразок: "Надійний Фільтр масляний для авто (Арт. 12345)"
    unique_name = f"{prefix} {clean_name} {adj} (Арт. {product_id})"
    
    # 2. Автоматична генерація ключових слів для пошуку на Prom
    words = [w.lower().strip(",.?!()\"") for w in clean_name.split() if len(w) > 3]
    base_keywords = [clean_name.lower(), "автотовари", "запчастини", "аксесуари для авто"]
    base_keywords.extend(words)
    # Залишаємо унікальні ключові слова через кому
    keywords_str = ", ".join(list(dict.fromkeys(base_keywords))[:15])
    
    # 3. Перефразування опису за допомогою рандомізованих блоків
    intro_options = [
        "Пропонуємо вашій увазі високоякісну позицію для вашого автомобіля.",
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
        clean_desc = f"Товар {clean_name} для обслуговування та покращення авто."

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
        response = requests.get(CSV_URL, timeout=30)
        response.raise_for_status()
        
        # Виправлення можливих проблем із кодуванням файлу постачальника
        response.encoding = 'utf-8'
        lines = response.text.splitlines()
        reader = csv.DictReader(lines, delimiter=";")

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
            # Читання ID та захист від зсуву колонок
            product_id = row.get("id") or row.get("ID") or row.get("\ufeffid")
            if not product_id:
                continue

            try:
                raw_price = row.get("price") or row.get("Price") or "0"
                price_opt = float(raw_price.replace(",", ".").strip())
            except ValueError:
                price_opt = 0.0

            if price_opt <= 0:
                continue

            margin_percent = calculate_margin(price_opt)
            price_retail = round(price_opt * (1 + margin_percent), 2)

            avail_status = row.get("available") or row.get("Available") or "true"
            is_available = "true" if avail_status.lower() in ["true", "1", "yes", "в наявності"] else "false"

            raw_name = row.get("name") or row.get("Name") or "Автотовар"
            raw_desc = row.get("description") or row.get("Description") or ""

            # Запуск модуля унікалізації контенту
            u_name, u_desc, u_keywords = unique_product_data(raw_name, product_id, raw_desc)

            offer = ET.SubElement(offers, "offer", id=str(product_id), available=is_available)
            ET.SubElement(offer, "name").text = u_name
            ET.SubElement(offer, "price").text = str(price_retail)
            ET.SubElement(offer, "currencyId").text = "UAH"
            ET.SubElement(offer, "categoryId").text = "7090"
            ET.SubElement(offer, "description").text = f"<![CDATA[{u_desc}]]>"
            
            # Додаємо ключові слова спеціально для пошукових алгоритмів Prom
            ET.SubElement(offer, "keywords").text = u_keywords

        xml_string = ET.tostring(yml_catalog, encoding="utf-8", method="xml")
        xml_declaration = b'<?xml version="1.0" encoding="UTF-8"?>\n'

        return Response(xml_declaration + xml_string, mimetype="text/xml")

    except Exception as e:
        return Response(f"Помилка генерації: {str(e)}", status=500, mimetype="text/plain")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
