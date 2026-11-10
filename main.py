import csv
import io
import requests
import xml.etree.ElementTree as ET
from flask import Flask, Response

app = Flask(__name__)

CSV_URL = "https://ag-opt.com.ua"

def calculate_markup(base_price):
    try:
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
        res.encoding = 'utf-8'
        if res.status_code != 200:
            return "Помилка завантаження даних", 500
            
        csv_data = csv.DictReader(io.StringIO(res.text))
        yml = ET.Element("yml_catalog", date="2026-11-10 12:00")
        shop = ET.SubElement(yml, "shop")
        
        ET.SubElement(shop, "name").text = "Магазин"
        ET.SubElement(shop, "company").text = "Компанія"
        ET.SubElement(shop, "url").text = "https://prom.ua"
        
        currencies = ET.SubElement(shop, "currencies")
        ET.SubElement(currencies, "currency", id="UAH", rate="1")
        
        categories = ET.SubElement(shop, "categories")
        offers = ET.SubElement(shop, "offers")
        added_cats = set()

        for row in csv_data:
            articul = row.get('Артикул', row.get('article', ''))
            name = row.get('Назва', row.get('name', ''))
            price_raw = row.get('Ціна', row.get('price', '0'))
            amount = row.get('Кількість', row.get('quantity', '0'))
            cat_name = row.get('Категорія', row.get('category', 'Автотовари'))
            img = row.get('Фото', row.get('image', ''))
            
            if not articul:
                continue
                
            prom_price = calculate_markup(price_raw)
            cat_id = str(hash(cat_name) % 10000)
            if cat_id not in added_cats:
                ET.SubElement(categories, "category", id=cat_id).text = cat_name
                added_cats.add(cat_id)
            
            avail = "true" if int(amount) > 0 else "false"
            offer = ET.SubElement(offers, "offer", id=articul, available=avail)
            
            ET.SubElement(offer, "name").text = f"{name} (Арт. {articul})"
            ET.SubElement(offer, "price").text = prom_price
            ET.SubElement(offer, "currencyId").text = "UAH"
            ET.SubElement(offer, "categoryId").text = cat_id
            if img:
                ET.SubElement(offer, "picture").text = img
                
            desc = f"<p><strong>Якісні автотовари!</strong> {name}. Артикул: {articul}. Доставка по Україні.</p>"
            ET.SubElement(offer, "description").text = desc

        return Response(ET.tostring(yml, encoding="utf-8"), mimetype="application/xml")
    except Exception as e:
        return f"Помилка: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
