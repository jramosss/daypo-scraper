import sqlite3

conn = sqlite3.connect("cuestionarios.db")
c = conn.cursor()

query = "SELECT * FROM preguntas LIMIT 10"
results = c.execute(query)

for row in results:
    pregunta = row[1]
    print(pregunta)
    respuestas = c.execute("SELECT * FROM respuestas WHERE pregunta_id = ?", (row[0],))
    for respuesta in respuestas:
        print(respuesta[2], "---" "Correcta" if respuesta[3] == 1 else "")

conn.close()
