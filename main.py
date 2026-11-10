import csv
import io
import requests
import xml.etree.ElementTree as ET
from flask import Flask, Response

app = Flask(__name__)

CSV_URL = "https://drive.google.com/file/d/1Fnxfh6gsHI9tC15q_uPt3Wg1RaO33T20/view?usp=sharing"

def calculate_markup(base_price):
    try:
        base_price = base_price.replace(',', '.').replace(' ', '').strip()
        price = float(base_price)
    except (ValueError, TypeError):
        return "0"
    if price <= 0:
        return "0"
    if price <= 100:
        markup = 1.00
    elif price <= 250:
        markup = 0.80
    elif price <= 500:
        markup = 0.60
    elif price <= 750:
        markup = 0.50
    elif price <= 1000:
        markup = 0.37
    elif price <= 1500:
        markup = 0.32
    elif price <= 2000:
        markup = 0.29
    elif price <= 4000:
        markup = 0.25
    elif price <= 6000:
        markup = 0.20
    elif price <= 10000:
        markup = 0.18
    else:
        markup = 0.15
    return str(round(price + (price * markup)))

@app.route("/prom-feed")
def prom_feed():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res = requests.get(CSV_URL, headers=headers, timeout=30)
        if res.status_code != 200:
            return "Помилка завантаження даних", 500
            
        text_content = ""
        try:
            text_content = res.content.decode('utf-8')
        except UnicodeDecodeError:
            text_content = res.content.decode('cp1251', errors='ignore')

        # Визначаємо розділювач таблиці
        delimiter = ';' if ';' in text_content.split('\n')[0] else ','
        csv_data = csv.DictReader(io.StringIO(text_content), delimiter=delimiter)
        
        fieldnames = csv_data.fieldnames if csv_data.fieldnames else []
        
        def find_col(possible_names):
            for name in possible_names:
                for field in fieldnames:
                    if field.lower().strip() == name.lower().strip():
                        return field
            return None

        # Шукаємо назви колонок постачальника AvtoGrand
        art_col = find_col(['Артикул', 'article', 'sku', 'id', 'код'])
        name_col = find_col(['Назва', 'name', 'title', 'товар', 'наименование'])
        price_col = find_col(['Ціна', 'price', 'cost', 'цена', 'розница'])
        amount_col = find_col(['Кількість', 'quantity', 'amount', 'ostatok', 'кол-во', 'наличие'])
        cat_col = find_col(['Категорія', 'category', 'группа', 'група'])
        img_col = find_col(['Фото', 'image', 'picture', 'photo', 'ссылка на фото'])

        # СТВОРЮЄМО ОФІЦІЙНУ СТРУКТУРУ YML ДЛЯ ПРОМУ
        yml_catalog = ET.Element("yml_catalog", date="2026-11-10 14:00")
        shop = ET.SubElement(yml_catalog, "shop")
        
        ET.SubElement(shop, "name").text = "Автомагазин"
        ET.SubElement(shop, "company").text = "Дропшипінг Компанія"
        ET.SubElement(shop, "url").text = "https://prom.ua"
        
        currencies = ET.SubElement(shop, "currencies")
        ET.SubElement(currencies, "currency", id="UAH", rate="1")
        
        categories = ET.SubElement(shop, "categories")
        offers = ET.SubElement(shop, "offers")
        
        added_cats = set()

        for row in csv_data:
            # Спроби дістати артикул та назву, якщо автоматичний пошук збився
            articul = row.get(art_col, '').strip() if art_col else ''
            if not articul and fieldnames:
                articul = row.get(fieldnames[0], '').strip() # беремо першу колонку як ID
                
            name = row.get(name_col, '').strip() if name_col else ''
            if not name and len(fieldnames) > 1:
                name = row.get(fieldnames[1], '').strip() # беремо другу колонку як назву

            price_raw = row.get(price_col, '0').strip() if price_col else '0'
            amount_raw = row.get(amount_col, '0').strip() if amount_col else '0'
            cat_name = row.get(cat_col, 'Автотовари').strip() if cat_col else 'Автотовари'
            img = row.get(img_col, '').strip() if img_col else ''
            
            if not articul or not name or name.lower() in ['назва', 'name', 'наименование']:
                continue
                
            prom_price = calculate_markup(price_raw)
            
            # Генеруємо унікальний ID категорії
            cat_id = str(abs(hash(cat_name)) % 10000)
            if cat_id not in added_cats:
                ET.SubElement(categories, "category", id=cat_id).text = cat_name
                added_cats.add(cat_id)
            
            # Логіка наявності
            try:
                avail_bool = float(amount_raw.replace('>', '').replace('<', '')) > 0
            except:
                avail_bool = True if amount_raw and amount_raw.lower() not in ['0', 'нет', 'немає'] else False
                
            avail = "true" if avail_bool else "false"
            
            # Створюємо товар суворо за стандартами Прому
            offer = ET.SubElement(offers, "offer", id=articul, available=avail)
            ET.SubElement(offer, "name").text = f"{name} (Арт. {articul})"
            ET.SubElement(offer, "price").text = prom_price
            ET.SubElement(offer, "currencyId").text = "UAH"
            ET.SubElement(offer, "categoryId").text = cat_id
            
            if img:
                ET.SubElement(offer, "picture").text = img
                
            desc = f"<p><strong>Якісні автотовари!</strong> {name}. Артикул для замовлення: {articul}. Доставка по Україні в найкоротші терміни.</p>"
            ET.SubElement(offer, "description").text = desc

        # Загортаємо все в XML декларацію
        xml_str = ET.tostring(yml_catalog, encoding="utf-8")
        xml_output = b'<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
        
        return Response(xml_output, mimetype="application/xml")
    except Exception as e:
        return f"Помилка: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
