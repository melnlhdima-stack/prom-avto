import csv
import xml.etree.ElementTree as ET
import random
import requests
from datetime import datetime
from flask import Flask, Response

app = Flask(__name__)

CSV_URL = "https://ag-opt.com.ua"

PREFIXES = ["Купити", "Якісний", "Надійний", "Оригінальний", "Професійний", "Автомобільний"]
ADJECTIVES = ["для авто", "високої якості", "в машину", "преміум класу", "для ремонту"]

def calculate_margin(price_opt):
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
    clean_name = str(name).strip()
    prefix = random.choice(PREFIXES)
    adj = random.choice(ADJECTIVES)
    unique_name = f"{prefix} {clean_name} {adj} (Арт. {product_id})"
    
    words = [w.lower().strip(",.?!()\"") for w in clean_name.split() if len(w) > 3]
    base_keywords = [clean_name.lower(), "автотовари", "запчастини", "аксесуари для авто"]
    base_keywords.extend(words)
    keywords_str = ", ".join(list(dict.fromkeys(base_keywords))[:15])
    
    intro = random.choice([
        "Пропонуємо вашій увазі якісну позицію для вашого автомобіля.",
        "Оригінальна деталь та аксесуари, що забезпечать надійну роботу авто.",
        "Сучасне рішення для обслуговування транспортного засобу."
    ])
    benefit = random.choice([
        "Виріб виготовлено з міцних матеріалів, стійких до зносу.",
        "Відповідає всім стандартам якості та технічним вимогам.",
        "Легко встановлюється та має тривалий термін експлуатації."
    ])
    delivery = random.choice([
        "Швидка доставка Новою Поштою та Укрпоштою по всій Україні.",
        "Відправка в день замовлення. Гарантія якості від постачальника."
    ])
    
    clean_desc = str(raw_description).replace("<p>", "").replace("</p>", "").replace("<strong>", "").replace("</strong>", "").strip()
    if not clean_desc or len(clean_desc) < 10:
        clean_desc = f"Товар {clean_name} призначений для якісного обслуговування вашого авто."

    unique_description = (
        f"<p><strong>{unique_name}</strong> — {intro}<br><br>"
        f"{clean_desc}<br><br>"
        f"<strong>Основні переваги:</strong> {benefit}<br>"
        f"<strong>Доставка:</strong> {delivery}</p>"
    )
    return unique_name, unique_description, keywords_str

@app.route("/")
@app.route("/prom-feed")
def generate_feed():
    try:
        response = requests.get(CSV_URL, timeout=30)
        response.raise_for_status()
        
        response.encoding = 'utf-8-sig'
        raw_text = response.text.strip()
        
        # Автоматическое определение разделителя (точка с запятой или запятая)
        delimiter = ";" if raw_text.count(";") > raw_text.count(",") else ","
        
        lines = raw_text.splitlines()
        if not lines:
            return Response("Помилка: Порожній файл від постачальника", mimetype="text/plain", status=400)
            
        reader = csv.reader(lines, delimiter=delimiter)
        headers = [h.strip().lower().replace("\ufeff", "") for h in next(reader)]
        
        # Индексы колонок (поиск по ключевым словам)
        id_idx, name_idx, price_idx, desc_idx, avail_idx = -1, -1, -1, -1, -1
        
        for i, h in enumerate(headers):
            if h in ["id", "id товара", "код", "артикул", "код_товара"]: id_idx = i
            elif h in ["name", "название", "найменування", "назва", "товар"]: name_idx = i
            elif h in ["price", "цена", "ціна", "price_opt"]: price_idx = i
            elif h in ["description", "описание", "опис"]: desc_idx = i
            elif h in ["available", "наличие", "наявність", "status"]: avail_idx = i

        # Если по именам не нашлось, берем жесткие дефолтные позиции (1-я колонка ID, 2-я Название, 3-я Цена)
        if id_idx == -1: id_idx = 0
        if name_idx == -1: name_idx = 1 if len(headers) > 1 else 0
        if price_idx == -1: price_idx = 2 if len(headers) > 2 else 0

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
            if not row or len(row) <= max(id_idx, name_idx, price_idx):
                continue
                
            product_id = str(row[id_idx]).strip()
            if not product_id or product_id.lower() in ["id", "код", "артикул"]:
                continue

            raw_price = row[price_idx]
            try:
                price_opt = float(str(raw_price).replace(",", ".").strip())
            except ValueError:
                price_opt = 0.0

            if price_opt <= 0:
                continue

            margin_percent = calculate_margin(price_opt)
            price_retail = round(price_opt * (1 + margin_percent), 2)

            raw_avail = row[avail_idx] if (avail_idx != -1 and avail_idx < len(row)) else "true"
            is_available = "true" if str(raw_avail).lower() in ["true", "1", "yes", "в наявності", "есть", "в наличии", ""] else "false"

            raw_name = row[name_idx] if name_idx < len(row) else "Автотовар"
            raw_desc = row[desc_idx] if (desc_idx != -1 and desc_idx < len(row)) else ""

            u_name, u_desc, u_keywords = unique_product_data(raw_name, product_id, raw_desc)

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
