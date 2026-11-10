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
            
        # Беремо перші 1000 символів файлу, щоб побачити його структуру
        raw_sample = text_content[:1000]
        
        return f"<h1>Сирий початок файлу постачальника:</h1><pre>{raw_sample}</pre>"
    except Exception as e:
        return f"Помилка: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
