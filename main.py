import asyncio
import base64
import sys
from typing import Any, Dict, List, Optional, Tuple

from playwright.async_api import Page, async_playwright

from constants import CONTESTAR_XPATH, NUMERO_DE_PREGUNTAS_XPATH, SIGUIENTE_XPATH
from database import Database


def same_image(b64_1: str, b64_2: str) -> bool:
    # Quitar el prefijo "data:image/png;base64," si lo tiene
    clean1 = b64_1.split(",")[-1]
    clean2 = b64_2.split(",")[-1]

    # Decodificar los bytes de cada imagen
    bytes1 = base64.b64decode(clean1)
    bytes2 = base64.b64decode(clean2)

    # Comparar los bytes directamente
    return bytes1 == bytes2


def extraer_nombre_cuestionario(url: str) -> str:
    """Extrae el nombre del cuestionario desde la URL"""
    return url.split("/")[-1].replace(".html", "").replace("#test", "")


async def obtener_numero_preguntas(page: Page) -> int:
    """Obtiene el número total de preguntas del cuestionario"""
    numero_de_preguntas_element = page.locator(f"xpath={NUMERO_DE_PREGUNTAS_XPATH}")
    numero_de_preguntas_text = await numero_de_preguntas_element.inner_text()
    numero_de_preguntas = numero_de_preguntas_text.split("/")[-1]
    return int(numero_de_preguntas)


async def click_posponer(page: Page) -> None:
    """Hace clic en el botón 'Posponer' si está disponible"""
    try:
        posponer = page.locator(f"xpath={CONTESTAR_XPATH}")
        if await posponer.count() > 0:
            await posponer.click()
    except Exception as e:
        import sys
        print(f"No se pudo hacer clic en Posponer: {e}", file=sys.stderr)


async def extraer_texto_pregunta(page: Page) -> str:
    """Extrae el texto de la pregunta actual"""
    pregunta_elem = page.locator("td[id^='pri']")
    if await pregunta_elem.count() > 0:
        return await pregunta_elem.inner_text()
    return "Pregunta desconocida"


def determinar_respuesta_correcta(data_url: str) -> int:
    """
    Determina si una respuesta es correcta basándose en el canvas

    Args:
        data_url: URL de datos del canvas

    Returns:
        1 si es correcta, 0 si no
    """
    # TODO: encontrar mejor manera de determinar si la imagen es el tick verde
    return 1 if len(data_url) > 400 else 0


async def extraer_respuestas_pregunta(page: Page) -> List[Dict[str, Any]]:
    """
    Extrae todas las respuestas de la pregunta actual

    Returns:
        Lista de diccionarios con 'texto' y 'correcta'
    """
    respuestas = []

    # Obtener todos los canvas de respuestas
    vai_canvases = await page.query_selector_all("canvas[id^='vai']")

    # Obtener los textos de las respuestas
    respuestas_td = await page.locator("#cuestiones1").locator("td.pr05").all_inner_texts()

    for idx, canvas in enumerate(vai_canvases):
        canvas_id = await canvas.get_attribute("id")
        data_url = await page.evaluate(f"document.getElementById('{canvas_id}').toDataURL()")

        # Obtener el texto de la respuesta
        texto = "Respuesta desconocida"
        if idx < len(respuestas_td):
            texto = respuestas_td[idx]

        # Determinar si es correcta
        es_correcta = determinar_respuesta_correcta(data_url)

        respuestas.append({
            'texto': texto.strip(),
            'correcta': es_correcta
        })

    return respuestas


async def avanzar_pregunta(page: Page) -> None:
    """Hace clic en el botón 'Siguiente' para avanzar a la siguiente pregunta"""
    siguiente = page.locator(f"xpath={SIGUIENTE_XPATH}")
    await siguiente.click()


async def extraer_datos_cuestionario(page: Page, numero_preguntas: int) -> tuple[List[Tuple[str, Optional[str]]], List[Dict[str, Any]]]:
    """
    Extrae todos los datos del cuestionario (preguntas y respuestas)

    Returns:
        Tupla con (lista de tuplas (texto, imagen) de preguntas, lista de respuestas con pregunta_idx)
    """
    preguntas_data = []
    respuestas_data = []

    for i in range(numero_preguntas):
        # Hacer clic en posponer si es necesario
        await click_posponer(page)

        # Extraer la pregunta
        pregunta_texto = await extraer_texto_pregunta(page)
        
        # Buscar si existe una imagen representada como canvas dentro del contenedor principal
        # que no sea parte de las respuestas
        imagen_path = None
        main_label = page.locator("xpath=/html/body/div[2]/div[3]/div[2]")
        if await main_label.count() > 0:
            all_canvases = await main_label.locator("canvas").all()
            for canvas in all_canvases:
                canvas_id = await canvas.get_attribute("id") or ""
                # Comprobar si está fuera de #cuestiones1
                is_in_cuestiones = await canvas.evaluate(
                    "canvas => !!canvas.closest('#cuestiones1')"
                )
                if not is_in_cuestiones and not canvas_id.startswith("vai") and not canvas_id.startswith("op"):
                    # Es una imagen de la pregunta!
                    try:
                        import os
                        import base64
                        
                        # Esperar a que el canvas esté dibujado (no vacío)
                        # Comprobar si hay algún píxel no transparente (alpha != 0)
                        for _ in range(20):
                            is_blank = await canvas.evaluate("""canvas => {
                                const ctx = canvas.getContext('2d');
                                if (!ctx) return true;
                                const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
                                for (let i = 3; i < data.length; i += 4) {
                                    if (data[i] !== 0) {
                                        return false; // Tiene contenido
                                    }
                                }
                                return true; // Totalmente transparente
                            }""")
                            if not is_blank:
                                break
                            await page.wait_for_timeout(50)
                        
                        # Obtener data URL del canvas
                        data_url = await canvas.evaluate("canvas => canvas.toDataURL()")
                        if "," in data_url:
                            # Formato: data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...
                            header, base64_data = data_url.split(",", 1)
                            image_bytes = base64.b64decode(base64_data)
                            
                            # Crear directorio images si no existe
                            base_dir = os.path.dirname(os.path.abspath(__file__))
                            images_dir = os.path.join(base_dir, "images")
                            os.makedirs(images_dir, exist_ok=True)
                            
                            # Generar un nombre de archivo único para esta pregunta
                            nombre_cuestionario = extraer_nombre_cuestionario(page.url)
                            filename = f"{nombre_cuestionario}_{i}.png"
                            filepath = os.path.join(images_dir, filename)
                            
                            # Escribir la imagen a disco
                            with open(filepath, "wb") as f:
                                f.write(image_bytes)
                                
                            # Guardar la ruta relativa (e.g. 'images/nombre_0.png')
                            imagen_path = f"images/{filename}"
                            print(f"Imagen de pregunta guardada en: {imagen_path}")
                    except Exception as e:
                        import sys
                        print(f"Error al guardar imagen de pregunta: {e}", file=sys.stderr)
                    break # Asumimos una imagen por pregunta

        preguntas_data.append((pregunta_texto, imagen_path))
        pregunta_idx = len(preguntas_data) - 1

        # Extraer las respuestas
        respuestas = await extraer_respuestas_pregunta(page)

        # Agregar el índice de pregunta a cada respuesta
        for respuesta in respuestas:
            respuestas_data.append({
                'pregunta_idx': pregunta_idx,
                'texto': respuesta['texto'],
                'correcta': respuesta['correcta']
            })

        # Avanzar a la siguiente pregunta (excepto en la última)
        if i < numero_preguntas - 1:
            await avanzar_pregunta(page)

    return preguntas_data, respuestas_data


def guardar_cuestionario(db: Database, cuestionario_id: str,
                         preguntas_data: List[Tuple[str, Optional[str]]], respuestas_data: List[Dict[str, Any]]) -> None:
    """
    Guarda el cuestionario completo en la base de datos

    Args:
        db: Instancia de Database
        cuestionario_id: ID del cuestionario
        preguntas_data: Lista de tuplas (texto, imagen) de preguntas
        respuestas_data: Lista de respuestas con pregunta_idx
    """
    # Insertar todas las preguntas
    pregunta_ids = db.insertar_preguntas_batch(cuestionario_id, preguntas_data)

    # Preparar las respuestas para inserción
    respuestas_to_insert = [
        (pregunta_ids[r['pregunta_idx']], r['texto'], r['correcta'])
        for r in respuestas_data
    ]

    # Insertar todas las respuestas
    db.insertar_respuestas_batch(respuestas_to_insert)


async def scrape(url: str) -> None:
    """
    Función principal que realiza el scraping completo de un cuestionario

    Args:
        url: URL del cuestionario a scrapear
    """
    try:
        db = Database()

        # Crear el cuestionario en la base de datos
        nombre_cuestionario = extraer_nombre_cuestionario(url)
        cuestionario_id = db.crear_cuestionario(url, nombre_cuestionario)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url)

            # Obtener el número de preguntas
            numero_preguntas = await obtener_numero_preguntas(page)

            # Extraer todos los datos del cuestionario
            preguntas_data, respuestas_data = await extraer_datos_cuestionario(page, numero_preguntas)

            # Cerrar el navegador
            await browser.close()

        # Guardar en la base de datos
        guardar_cuestionario(db, cuestionario_id, preguntas_data, respuestas_data)

        print(f"Cuestionario guardado con ID: {cuestionario_id}", file=sys.stderr)
        return cuestionario_id
    except Exception as e:
        print(f"Error in scrape(): {type(e).__name__}: {str(e)}", file=sys.stderr)
        raise e

async def buscar_daypos(termino: str) -> List[Dict[str, str]]:
    """
    Busca cuestionarios en Daypo relacionados con el término proporcionado.
    Filtra y prioriza los resultados según las preferencias del usuario.
    """
    import urllib.parse
    termino_encoded = urllib.parse.quote_plus(termino)
    search_url = f"https://www.daypo.com/buscar.php?t={termino_encoded}&c=0&o=1"

    resultados_finales = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(search_url)

        # Esperar a que los resultados se carguen
        await page.wait_for_selector("a.h.w", timeout=10000)

        # Obtener todos los elementos de resultado
        result_elements = await page.query_selector_all("a.h.w")

        for element in result_elements:
            href = await element.get_attribute("href")
            # Convertir URL relativa a absoluta si es necesario
            if href and not href.startswith("http"):
                href = f"https://www.daypo.com/{href}"

            # Extraer título y descripción
            title_elem = await element.query_selector("div.tu.fwb")
            desc_elem = await element.query_selector("div.fs08.mt3x")

            title = await title_elem.inner_text() if title_elem else ""
            description = await desc_elem.inner_text() if desc_elem else ""

            result = {
                "url": href,
                "titulo": title.strip(),
                "descripcion": description.strip()
            }

            # Aplicar filtros y preferencias
            texto_completo = (title + " " + description).lower()

            # Prioridad: Siglo 21
            tiene_siglo_21 = "siglo 21" in texto_completo

            # Criterio general: Primer parcial o segundo parcial
            es_parcial = "primer parcial" in texto_completo or "segundo parcial" in texto_completo or "1er parcial" in texto_completo or "2do parcial" in texto_completo or "1 parcial" in texto_completo or "2 parcial" in texto_completo

            if tiene_siglo_21 or es_parcial:
                # Si cumple alguna, lo añadimos. Podemos marcar la prioridad.
                result["prioridad"] = tiene_siglo_21
                resultados_finales.append(result)

        await browser.close()

    # Ordenar: primero los que tienen Siglo 21
    resultados_finales.sort(key=lambda x: x.get("prioridad", False), reverse=True)

    return resultados_finales

if __name__ == "__main__":
    import sys
    if len(sys.argv) <= 1:
        print("Uso: python main.py <URL_DEL_CUESTIONARIO o ID_DEL_CUESTIONARIO> o use --search <termino>")
        sys.exit(1)

    if sys.argv[1] == "--search" and len(sys.argv) > 2:
        termino = " ".join(sys.argv[2:])
        results = asyncio.run(buscar_daypos(termino))
        for r in results:
            prefix = "[SIGLO 21] " if r.get("prioridad") else ""
            print(f"{prefix}{r['titulo']} - {r['url']}")
        sys.exit(0)

    url_or_id = sys.argv[1].strip()
    # Si no es una URL (no empieza con http), construimos la URL a partir del ID
    if not url_or_id.startswith("http"):
        # Si no tiene .html, lo añadimos
        if not url_or_id.endswith(".html"):
            url = f"https://www.daypo.com/{url_or_id}.html"
        else:
            url = f"https://www.daypo.com/{url_or_id}"
    else:
        url = url_or_id

    if not url.endswith("#test"):
        url += "#test"

    asyncio.run(scrape(url))
