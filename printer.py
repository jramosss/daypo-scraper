from database import Database

db = Database()

# Obtener todas las preguntas (opcionalmente puedes filtrar por cuestionario_id)
preguntas = db.obtener_preguntas(limit=250)

text = ""

for pregunta_row in preguntas:
    pregunta_id, cuestionario_id, pregunta_texto = pregunta_row
    text += f"{pregunta_texto}\n"

    respuestas = db.obtener_respuestas(pregunta_id)
    for respuesta_row in respuestas:
        respuesta_id, pregunta_id_resp, texto, correcta = respuesta_row
        text += f"{texto} {'---Correcta' if correcta == 1 else ''}\n"
    text += "\n"

with open("cuestionarios.txt", "w") as f:
    f.write(text)
