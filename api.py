from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from main import scrape
from database import Database
import uvicorn

app = FastAPI(title="Daypo Quiz Scraper API")
db = Database()

class ScrapeRequest(BaseModel):
    url: str

@app.post("/scrape")
async def handle_scrape(request: ScrapeRequest):
    """
    Scrapea un cuestionario a partir de una URL
    """
    url = request.url
    if not url.endswith("#test"):
        url += "#test"
    
    try:
        cuestionario_id = await scrape(url)
        return {"success": True, "cuestionario_id": cuestionario_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/quiz/{quiz_id}", response_class=PlainTextResponse)
async def get_quiz_text(quiz_id: str):
    """
    Obtiene un cuestionario de la base de datos y lo retorna en texto plano (formato printer)
    """
    # Obtener todas las preguntas para el cuestionario dado
    preguntas = db.obtener_preguntas(quiz_id)
    
    if not preguntas:
        raise HTTPException(status_code=404, detail="Cuestionario no encontrado")

    text = f"--- CUESTIONARIO: {quiz_id} ---\n\n"
    for i, pregunta_row in enumerate(preguntas):
        # El formato de la fila es (id, cuestionario_id, texto) según database.py
        pregunta_id, _, pregunta_texto = pregunta_row
        text += f"{i + 1}. {pregunta_texto}\n"

        respuestas = db.obtener_respuestas(pregunta_id)
        for respuesta_row in respuestas:
            # El formato es (id, pregunta_id, texto, correcta)
            _, _, texto, correcta = respuesta_row
            correct_mark = " ---Correcta" if correcta == 1 else ""
            text += f"{texto}{correct_mark}\n"
        text += "\n"

    return text

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
