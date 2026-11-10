import csv
import io
import requests
import xml.etree.ElementTree as ET
from flask import Flask, Response

app = Flask(__name__)

CSV_URL = "https://ag-opt.com.ua"

def calculate_markup(base_price):
    try:
        # Очищаємо ціну від можливих пробілів та замін
        base_price = base_price.replace(',', '.').strip()
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
        res = requests.get(CSV_URL, timeout=30)
        if res.status_code != 200:
            return "Помилка завантаження даних", 500
            
        # Автоматично визначаємо кодування або пробуємо два найпопулярніших
        text_content = ""
        try:
            text_content = res.content.decode('utf-8')
        except UnicodeDecodeError:
            text_content = res.content.decode('cp1251')
            
        csv_data = csv.DictReader(io.StringIO(text_content))
        
        # Перевіряємо реальні назви колонок, які прийшли від постачальника
        fieldnames = csv_data.fieldnames if csv_data.fieldnames else []
        
        # Функція для гнучкого пошуку потрібної колонки
        def find_col(possible_names):
            for name in possible_names:
                for field in fieldnames:
                    if field.lower().strip() == name.lower().strip():
                        return field
            return None

        # Шукаємо відповідності колонок у постачальника AvtoGrand
        art_col = find_col(['Артикул', 'article', 'sku', 'id', 'код'])
        name_col = find_col(['Назва', 'name', 'title', 'товар'])
        price_col = find_col(['Ціна', 'price', 'cost', 'цена'])
        amount_col = find_col(['Кількість', 'quantity', 'amount', 'ostatok', 'кол-во', 'склад'])
        cat_col = find_col(['Категорія', 'category', 'группа', 'група'])
        img_col = find_col(['Фото', 'image', 'picture', 'photo', 'ссылка на фото'])

        yml = ET.Element("yml_catalog", date="2026-11-10 12:00")
        shop = ET.SubElement(yml, "shop")
        
        ET.SubElement(shop, "name").text = "Автомагазин"
        ET.SubElement(shop, "company").text = "Дропшипінг"
        ET.SubElement(shop, "url").text = "https://prom.ua"
        
        currencies = ET.SubElement(shop, "currencies")
        ET.SubElement(currencies, "currency", id="UAH", rate="1")
        
        categories = ET.SubElement(shop, "categories")
        offers = ET.SubElement(shop, "offers")
        added_cats = set()

        for row in csv_data:
            # Зчитуємо дані через визначені розумні колонки
            articul = row.get(art_col, '').strip() if art_col else ''
            name = row.get(name_col, '').strip() if name_col else ''
            price_raw = row.get(price_col, '0').strip() if price_col else '0'
            amount_raw = row.get(amount_col, '0').strip() if amount_col else '0'
            cat_name = row.get(cat_col, 'Автотовари').strip() if cat_col else 'Автотовари'
            img = row.get(img_col, '').strip() if img_col else ''
            
            if not articul or not name:
                continue
                
            prom_price = calculate_markup(price_raw)
            cat_id = str(hash(cat_name) % 10000)
            if cat_id not in added_cats:
                ET.SubElement(categories, "category", id=cat_id).text = cat_name
                added_cats.add(cat_id)
            
            # Перевіряємо кількість безпомилково
            try:
                avail_bool = int(amount_raw) > 0
            except:
                avail_bool = True if amount_raw and amount_raw.lower() not in ['0', 'нет', 'немає'] else False
                
            avail = "true" if avail_bool else "false"
            offer = ET.SubElement(offers, "offer", id=articul, available=avail)
            
            ET.SubElement(offer, "name").text = f"{name} (Арт. {articul})"
            ET.SubElement(offer, "price").text = prom_price
            ET.SubElement(offer, "currencyId").text = "UAH"
            ET.SubElement(offer, "categoryId").text = cat_id
            if img:
                ET.SubElement(offer, "picture").text = img
                
            desc = f"<p><strong>Якісні автотовари!</strong> {name}. Артикул для замовлення: {articul}. Доставка по Україні.</p>"
            ET.SubElement(offer, "description").text = desc

        return Response(ET.tostring(yml, encoding="utf-8"), mimetype="application/xml")
    except Exception as e:
        return f"Помилка: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

