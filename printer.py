import sqlite3

conn = sqlite3.connect("cuestionarios.db")
c = conn.cursor()

query = "SELECT * FROM preguntas LIMIT 250"
results = c.execute(query)
text = ""

for row in list(results):
    pregunta = row[1]
    text += f"{pregunta}\n"
    respuestas = c.execute("SELECT * FROM respuestas WHERE pregunta_id = ?", (row[0],))
    for respuesta in respuestas:
        text += f"{respuesta[2]} {'---Correcta' if respuesta[3] == 1 else ''}\n"
    text += "\n"

with open("cuestionarios.txt", "w") as f:
    f.write(text)

conn.close()
