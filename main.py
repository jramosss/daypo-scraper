import asyncio
import base64
import sqlite3
from time import sleep

from playwright.async_api import async_playwright

# Constante de referencia (canvas "correcto")
CORRECT_IMG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEUAAABFCAYAAAAcjSspAAAC50lEQVR4AezYzU4UQRQF4DOjS4nxBXwCF8bfFYobN+qzmKhrE/fGxBfgKXTlwiVGR/4CK7Yk7GBHAmRmuKc6MMNw6TDddauozu1QPc2dUFX9caamu/vw7ZKAo1wiARzFURQBpeRJcRRFQCl5UhxFEVBKnhRHUQSUkifFURQBpeRJcRRFQCl1NynKyV635CiKVLdQfuOOco5zl7qDMsArLGAXA3zGFlrhdAcF+CCRuCvtC47wXV4b/3QDhSkB3p4rDPHt/LjBQTdQqpRUp9/DMp5hu/ql2b58lMgpIWP5KJFTUj6KQUrKRzFISdkoRikpG8UoJeWiGKakXBTDlBSAwinONOOUcLQSr1N4j8O5AxGuXqFsZaEkSAmNykIxXksIwhYPZRP32KFZm03JLbS6E66bZxyUDTzAMdbxH4uw2y6uJQ/b3QnXTbM9CkFO8FMGuY+RvFrAJEyJnAfaowyxIB1Vj/96cmwDkywlci4RUB5hRXrhU699dojYMGtYwvRTNcO1RMYJP+2Twm40mHGkj9IQHzlEaLwuMVxLwhiyi4MiHWEWBvJRIsxfvODbjVqGlHCe8VDYmwbTxw80hRkh6VrCU2CLi8IeCTPEZI1hYprAMCVjvGOXoSVYS8I4souPIp3iOVbQFiZTSjh9GxT23AYmY0o4dTsU9l7BzP9RypgSTtsWhSPMC5M5JZyyPQpHOYMZo7rAq1t8M6eE002DwpEIM5JvpTqYf1hCpm8cTG3pUDjoVTCrqC7w+nmuSzi16ZYWhSNrMCO5wBvgPW5ASjjF9CgclTB9vBGEyRoDfOVboSW6xwljKbs8KJzIY/zBRZjbLIeW8Oo1jDezy4fCiUzD9LAjyfkljx6WkeBOGDVbXhRObALzEk/xGof4xHLOlh+FZ0+YJ9jjIRZxEF4z7m4GSkYAbWhHUVQcxVEUAaV07aQof9vZkqMo/1pHcRRFQCl5UhxFEVBKnhRHUQSUkifFURQBpXQKAAD//7oMqq0AAAAGSURBVAMA9UPBi92NAsUAAAAASUVORK5CYII="
CONTESTAR_XPATH = "/html/body/div[2]/div[3]/div[3]/table/tbody/tr/td[9]/table/tbody/tr/td[2]/div"
SIGUIENTE_XPATH = "/html/body/div[2]/div[3]/div[3]/table/tbody/tr/td[9]/table/tbody/tr/td[2]/div"
NUMERO_DE_PREGUNTAS_XPATH = "/html/body/div[2]/div[3]/div[1]/table/tbody/tr/td[2]/table/tbody/tr/td[2]"
TABLE_XPATH = """//*[@id="cuestiones1"]/table"""

# Inicializa la base de datos
def init_db():
    conn = sqlite3.connect("cuestionarios.db")
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS preguntas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        texto TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS respuestas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pregunta_id INTEGER,
        texto TEXT,
        correcta INTEGER,
        FOREIGN KEY (pregunta_id) REFERENCES preguntas(id)
    )
    """)
    conn.commit()
    conn.close()



def same_image(b64_1: str, b64_2: str) -> bool:
    # Quitar el prefijo "data:image/png;base64," si lo tiene
    clean1 = b64_1.split(",")[-1]
    clean2 = b64_2.split(",")[-1]

    # Decodificar los bytes de cada imagen
    bytes1 = base64.b64decode(clean1)
    bytes2 = base64.b64decode(clean2)

    # Comparar los bytes directamente
    return bytes1 == bytes2

async def scrape(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(url)

        numero_de_preguntas_element = page.locator(f"xpath={NUMERO_DE_PREGUNTAS_XPATH}")
        numero_de_preguntas_text = await numero_de_preguntas_element.inner_text()
        numero_de_preguntas = numero_de_preguntas_text.split("/")[-1]

        # Listas para acumular datos
        preguntas_data = []
        respuestas_data = []

        for i in range(int(numero_de_preguntas)):
            # Clic en "Posponer"
            try:
                posponer = page.locator(f"xpath={CONTESTAR_XPATH}")
                if await posponer.count() > 0:
                    await posponer.click()
            except Exception as e:
                print(f"No se pudo hacer clic en Posponer: {e}")

            # Obtener texto de la pregunta
            pregunta_elem = page.locator("td[id^='pri']")
            pregunta_texto = await pregunta_elem.inner_text() if await pregunta_elem.count() > 0 else "Pregunta desconocida"

            preguntas_data.append(pregunta_texto)
            pregunta_idx = len(preguntas_data) - 1

            # Iterar sobre los canvas "vaiX"
            vai_canvases = await page.query_selector_all("canvas[id^='vai']")

            # Debug: ver cuántos td.pr05 hay
            respuestas_td = await page.locator("td[id='cuestiones1']").locator("td.pr05").all_inner_texts()

            for idx, canvas in enumerate(vai_canvases):
                canvas_id = await canvas.get_attribute("id")
                data_url = await page.evaluate(f"document.getElementById('{canvas_id}').toDataURL()")

                texto = "Respuesta desconocida"
                if idx < len(respuestas_td):
                    texto = respuestas_td[idx]

                # encontrar mejor manera de determinar si la imagen es el tick verde
                es_correcta = 1 if len(data_url) > 400 else 0

                respuestas_data.append({
                    'pregunta_idx': pregunta_idx,
                    'texto': texto.strip(),
                    'correcta': es_correcta
                })

            siguiente = page.locator(f"xpath={SIGUIENTE_XPATH}")

            await siguiente.click()


        # Guardar todo en la base de datos
        conn = sqlite3.connect("cuestionarios.db")
        c = conn.cursor()

        # Insertar todas las preguntas
        c.executemany("INSERT INTO preguntas (texto) VALUES (?)",
                      [(p,) for p in preguntas_data])

        # Obtener los IDs de las preguntas insertadas
        pregunta_ids = [row[0] for row in c.execute(
            "SELECT id FROM preguntas ORDER BY id DESC LIMIT ?",
            (len(preguntas_data),)
        ).fetchall()][::-1]

        # Insertar todas las respuestas con los IDs correctos
        respuestas_to_insert = [
            (pregunta_ids[r['pregunta_idx']], r['texto'], r['correcta'])
            for r in respuestas_data
        ]
        c.executemany(
            "INSERT INTO respuestas (pregunta_id, texto, correcta) VALUES (?, ?, ?)",
            respuestas_to_insert
        )

        conn.commit()
        conn.close()
        await browser.close()

if __name__ == "__main__":
    init_db()
    # url = input("Ingrese la URL del cuestionario: ").strip()
    url = "https://www.daypo.com/ng-principios-economia-primer-parcial.html#test"
    asyncio.run(scrape(url))


