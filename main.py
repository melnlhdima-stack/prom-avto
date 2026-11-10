import csv
import io
import requests
from flask import Flask

app = Flask(__name__)

CSV_URL = "https://ag-opt.com.ua"

@app.route("/prom-feed")
def prom_feed():
    try:
        res = requests.get(CSV_URL, timeout=30)
        
        text_content = ""
        try:
            text_content = res.content.decode('utf-8')
        except UnicodeDecodeError:
            text_content = res.content.decode('cp1251')
            
        csv_data = csv.DictReader(io.StringIO(text_content))
        fieldnames = csv_data.fieldnames if csv_data.fieldnames else []
        
        # Показываем первые 2 строки для проверки данных
        sample_rows = []
        for i, row in enumerate(csv_data):
            if i < 2:
                sample_rows.append(str(dict(row)))
            else:
                break
                
        return f"<h1>Названия колонок у поставщика:</h1><p>{', '.join(fieldnames)}</p><h2>Пример товара:</h2><p>{'<br><br>'.join(sample_rows)}</p>"
    except Exception as e:
        return f"Ошибка: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
