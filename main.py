import asyncio
import base64
from typing import Any, Dict, List

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
        print(f"No se pudo hacer clic en Posponer: {e}")


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
    respuestas_td = await page.locator("td[id='cuestiones1']").locator("td.pr05").all_inner_texts()

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


async def extraer_datos_cuestionario(page: Page, numero_preguntas: int) -> tuple[List[str], List[Dict[str, Any]]]:
    """
    Extrae todos los datos del cuestionario (preguntas y respuestas)

    Returns:
        Tupla con (lista de textos de preguntas, lista de respuestas con pregunta_idx)
    """
    preguntas_data = []
    respuestas_data = []

    for i in range(numero_preguntas):
        # Hacer clic en posponer si es necesario
        await click_posponer(page)

        # Extraer la pregunta
        pregunta_texto = await extraer_texto_pregunta(page)
        preguntas_data.append(pregunta_texto)
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


def guardar_cuestionario(db: Database, cuestionario_id: int,
                         preguntas_data: List[str], respuestas_data: List[Dict[str, Any]]) -> None:
    """
    Guarda el cuestionario completo en la base de datos

    Args:
        db: Instancia de Database
        cuestionario_id: ID del cuestionario
        preguntas_data: Lista de textos de preguntas
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
    db = Database()

    # Crear el cuestionario en la base de datos
    nombre_cuestionario = extraer_nombre_cuestionario(url)
    cuestionario_id = db.crear_cuestionario(url, nombre_cuestionario)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
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

    print(f"Cuestionario guardado con ID: {cuestionario_id}")

if __name__ == "__main__":
    # url = input("Ingrese la URL del cuestionario: ").strip()
    url = "https://www.daypo.com/ng-principios-economia-primer-parcial.html#test"
    asyncio.run(scrape(url))
