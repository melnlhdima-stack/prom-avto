import xml.etree.ElementTree as ET
import random
import requests
from datetime import datetime
from flask import Flask, Response

app = Flask(__name__)

# Ссылка на нового XML-поставщика (UADRON)
XML_URL = "https://uadron.com/products_feed.xml?hash_tag=281dd6d99f9dd4625d3c5e6ffe15f88d&sales_notes=&product_ids=&label_ids=&exclude_fields=&html_description=0&yandex_cpa=&process_presence_sure=&languages=uk%2Cru&extra_fields=quantityInStock&group_ids=109739798%2C138629015%2C153923291&nested_group_ids=109739798%2C138629015%2C153923291"

# Базы синонимов для автоматической уникализации контента
PREFIXES = ["Купити", "Якісний", "Надійний", "Оригінальний", "Професійний", "Інноваційний"]
ADJECTIVES = ["для авто", "високої якості", "преміум класу", "для майстерень", "перевірений"]

def calculate_margin(price_opt):
    """Расчет розничной цены по вашей сетке наценок."""
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
    """Генерация уникальных заголовков, описаний и ключевых слов."""
    clean_name = name.strip()
    
    # 1. Изменение названия
    prefix = random.choice(PREFIXES)
    adj = random.choice(ADJECTIVES)
    unique_name = f"{prefix} {clean_name} {adj} (Арт. {product_id})"
    
    # 2. Ключевые слова для поисковой оптимизации внутри Пром
    words = [w.lower().strip(",.?!()\"'") for w in clean_name.split() if len(w) > 3]
    base_keywords = [clean_name.lower(), "автотовари", "запчастини", "аксесуари"]
    base_keywords.extend(words)
    keywords_str = ", ".join(list(dict.fromkeys(base_keywords))[:15])
    
    # 3. Шаблонизатор для уникального описания
    intro_options = [
        "Пропонуємо вашій увазі якісну позицію для вашого автомобіля чи обладнання.",
        "Оригінальний товар, що забезпечить надійну роботу вашої техніки.",
        "Сучасне та надійне рішення від перевіреного бренду за вигідною ціною."
    ]
    benefit_options = [
        "Виріб виготовлено з міцних та зносостійких матеріалів.",
        "Повністю відповідає заводським стандартам якості та технічним нормам.",
        "Має тривалий термін експлуатації та легко встановлюється."
    ]
    delivery_options = [
        "Швидка доставка Новою Поштою та Укрпоштою по всій Україні.",
        "Відправка в день замовлення. Офіційна гарантія якості від виробника.",
        "Надійне пакування товару перед відправленням для безпечного транспортування."
    ]
    
    clean_desc = (raw_description or "").replace("<p>", "").replace("</p>", "").replace("<strong>", "").replace("</strong>", "").strip()
    if not clean_desc or len(clean_desc) < 10:
        clean_desc = f"Товар {clean_name} створений для професійного використання та обслуговування."

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
        # Скачиваем оригинальный XML от uadron
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(XML_URL, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Парсим полученное дерево XML
        root_src = ET.fromstring(response.content)
        
        # Создаем основу нового XML-каталога
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        yml_catalog = ET.Element("yml_catalog", date=current_time)
        shop = ET.SubElement(yml_catalog, "shop")
        
        # Копируем базовую информацию (можно переименовать под себя)
        ET.SubElement(shop, "name").text = "Автомагазин"
        ET.SubElement(shop, "company").text = "Дропшипінг Компанія"
        ET.SubElement(shop, "url").text = "https://prom.ua"
        
        # Валюта
        currencies = ET.SubElement(shop, "currencies")
        ET.SubElement(currencies, "currency", id="UAH", rate="1")
        
        # Копируем оригинальные категории
        categories_new = ET.SubElement(shop, "categories")
        categories_src = root_src.find(".//categories")
        if categories_src is not None:
            for cat in categories_src.findall("category"):
                cat_id = cat.get("id")
                parent_id = cat.get("parentId")
                attribs = {"id": cat_id}
                if parent_id:
                    attribs["parentId"] = parent_id
                ET.SubElement(categories_new, "category", **attribs).text = cat.text
        else:
            ET.SubElement(categories_new, "category", id="7090").text = "Автотовари"

        offers_new = ET.SubElement(shop, "offers")
        
        # Ищем все товары в исходном файле
        offers_src = root_src.findall(".//offer")
        for offer in offers_src:
            product_id = offer.get("id")
            available = offer.get("available", "true")
            
            # Извлекаем оригинальное имя, описание и цену
            name_el = offer.find("name")
            price_el = offer.find("price")
            desc_el = offer.find("description")
            cat_id_el = offer.find("categoryId")
            
            raw_name = name_el.text if name_el is not None else "Автотовар"
            raw_desc = desc_el.text if desc_el is not None else ""
            cat_id = cat_id_el.text if cat_id_el is not None else "7090"
            
            try:
                price_opt = float(price_el.text.strip()) if price_el is not None else 0.0
            except (ValueError, AttributeError):
                price_opt = 0.0
                
            if price_opt <= 0:
                continue
                
            # Считаем новую цену с наценкой
            margin = calculate_margin(price_opt)
            price_retail = round(price_opt * (1 + margin), 2)
            
            # Уникализируем данные
            u_name, u_desc, u_keywords = unique_product_data(raw_name, product_id, raw_desc)
            
            # Формируем новый элемент товара
            new_offer = ET.SubElement(offers_new, "offer", id=str(product_id), available=available)
            ET.SubElement(new_offer, "name").text = u_name
            ET.SubElement(new_offer, "price").text = str(price_retail)
            ET.SubElement(new_offer, "currencyId").text = "UAH"
            ET.SubElement(new_offer, "categoryId").text = str(cat_id)
            ET.SubElement(new_offer, "description").text = f"<![CDATA[{u_desc}]]>"
            ET.SubElement(new_offer, "keywords").text = u_keywords
            
            # Копируем картинки, если они есть
            for img in offer.findall("picture"):
                if img.text:
                    ET.SubElement(new_offer, "picture").text = img.text
                    
            # Копируем параметры/характеристики, если они есть
            for param in offer.findall("param"):
                attribs = {"name": param.get("name")}
                if param.get("unit"):
                    attribs["unit"] = param.get("unit")
                ET.SubElement(new_offer, "param", **attribs).text = param.text

        xml_string = ET.tostring(yml_catalog, encoding="utf-8", method="xml")
        xml_declaration = b'<?xml version="1.0" encoding="UTF-8"?>\n'
        
        return Response(xml_declaration + xml_string, mimetype="text/xml")
        
    except Exception as e:
        return Response(f"Помилка генерації XML: {str(e)}", status=500, mimetype="text/plain")
