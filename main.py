prom_name = f"{name} (Арт. {articul}) для авто"
            ET.SubElement(offer, "name").text = prom_name
            
            # Передаємо вже прораховану ціну
            ET.SubElement(offer, "price").text = prom_price
            ET.SubElement(offer, "currencyId").text = "UAH"
            ET.SubElement(offer, "categoryId").text = cat_id
            
            final_image = download_and_process_image(image_url) if image_url else ""
            if final_image:
                ET.SubElement(offer, "picture").text = final_image
                
            prom_desc = f"""
            <p><strong>Шукаєте надійні автотовари?</strong> {name} — це ідеальний вибір для вашого автомобіля.</p>
            <p><strong>Основні переваги:</strong></p>
            <ul>
                <li>Офіційна якість від виробника</li>
                <li>Артикул товару: {articul}</li>
                <li>Гарантія сумісності та надійності</li>
            </ul>
            <p>Замовляйте просто зараз! Доставка по всій Україні в найкоротші терміни.</p>
            """
            ET.SubElement(offer, "description").text = prom_desc
            ET.SubElement(offer, "vendor").text = row.get('Бренд', row.get('brand', 'АвтоГранд'))
            ET.SubElement(offer, "keywords").text = f"{name}, автотовари, запчастини, купити {name}"

        xml_output = ET.tostring(yml_catalog, encoding="utf-8")
        return Response(xml_output, mimetype="application/xml")

    except Exception as e:
        return f"Помилка обробки файлу: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
