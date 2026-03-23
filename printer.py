from database import Database


def main():

    entrada = input("Ingrese el id del cuestionario").strip()
    cuestionario_id = entrada

    db = Database()

    # Obtener todas las preguntas para el cuestionario dado
    preguntas = db.obtener_preguntas(cuestionario_id)

    text = ""
    for i, pregunta_row in enumerate(preguntas):
        pregunta_id, cuestionario_id_row, pregunta_texto = pregunta_row
        text += f"{i + 1}. {pregunta_texto}\n"

        respuestas = db.obtener_respuestas(pregunta_id)
        for respuesta_row in respuestas:
            respuesta_id, pregunta_id_resp, texto, correcta = respuesta_row
            correct_mark = " ---Correcta" if correcta == 1 else ""
            text += f"{texto}{correct_mark}\n"
        text += "\n"

    out_name = f"cuestionario_{cuestionario_id}.txt"
    with open(out_name, "w") as f:
        f.write(text)

    print(f"Archivo generado: {out_name}")


if __name__ == "__main__":
    main()
