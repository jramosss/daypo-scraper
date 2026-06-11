import os
import sqlite3
from typing import Dict, List, Optional, Tuple

from constants import DB_NAME

# Calculate the absolute path to the database
# This ensures that no matter from where the script is called, it always uses the correct DB
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ABS_DB_PATH = os.path.join(BASE_DIR, DB_NAME)


class Database:
    """Wrapper para operaciones de base de datos"""

    def __init__(self, db_name: str = ABS_DB_PATH):
        self.db_name = db_name
        self.init_db()
    def get_connection(self) -> sqlite3.Connection:
        """Obtiene una conexión a la base de datos"""
        print(f"DEBUG: Attempting to connect to database at: {self.db_name}")
        try:
            conn = sqlite3.connect(self.db_name)
            conn.execute("PRAGMA foreign_keys = ON")  # Habilitar claves foráneas
            return conn
        except sqlite3.OperationalError as e:
            raise sqlite3.OperationalError(f"{str(e)} (path: {self.db_name})")

    def init_db(self):
        """Inicializa las tablas de la base de datos"""
        conn = self.get_connection()
        c = conn.cursor()

        # Crear tabla cuestionarios
        c.execute("""
        CREATE TABLE IF NOT EXISTS cuestionarios (
            id TEXT PRIMARY KEY,
            url TEXT,
            nombre TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Crear tabla preguntas (con relación a cuestionarios)
        c.execute("""
        CREATE TABLE IF NOT EXISTS preguntas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cuestionario_id TEXT,
            texto TEXT,
            imagen TEXT,
            FOREIGN KEY (cuestionario_id) REFERENCES cuestionarios(id) ON DELETE CASCADE
        )
        """)

        # Migración: Agregar columna imagen a la tabla preguntas si no existe
        try:
            c.execute("ALTER TABLE preguntas ADD COLUMN imagen TEXT")
        except sqlite3.OperationalError:
            pass

        # Crear tabla respuestas (con relación a preguntas)
        c.execute("""
        CREATE TABLE IF NOT EXISTS respuestas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pregunta_id INTEGER,
            texto TEXT,
            correcta INTEGER,
            FOREIGN KEY (pregunta_id) REFERENCES preguntas(id) ON DELETE CASCADE
        )
        """)

        conn.commit()
        conn.close()

    def crear_cuestionario(self, url: str, nombre: str) -> str:
        """
        Crea un nuevo cuestionario y retorna su ID (el nombre)

        Args:
            url: URL del cuestionario
            nombre: Nombre del cuestionario (usado como ID)

        Returns:
            ID del cuestionario creado (el nombre)
        """
        conn = self.get_connection()
        c = conn.cursor()

        try:
            c.execute(
                "INSERT INTO cuestionarios (id, url, nombre) VALUES (?, ?, ?)",
                (nombre, url, nombre)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            # Si ya existe, podríamos actualizarlo o simplemente devolver el nombre
            pass
        finally:
            conn.close()

        return nombre

    def insertar_pregunta(self, cuestionario_id: str, texto: str, imagen: Optional[str] = None) -> int:
        """
        Inserta una pregunta y retorna su ID

        Args:
            cuestionario_id: ID del cuestionario al que pertenece
            texto: Texto de la pregunta
            imagen: Ruta de la imagen asociada (opcional)

        Returns:
            ID de la pregunta insertada
        """
        conn = self.get_connection()
        c = conn.cursor()

        c.execute(
            "INSERT INTO preguntas (cuestionario_id, texto, imagen) VALUES (?, ?, ?)",
            (cuestionario_id, texto, imagen)
        )

        pregunta_id = c.lastrowid
        conn.commit()
        conn.close()

        return pregunta_id

    def insertar_preguntas_batch(self, cuestionario_id: str, preguntas: List[Tuple[str, Optional[str]]]) -> List[int]:
        """
        Inserta múltiples preguntas y retorna sus IDs

        Args:
            cuestionario_id: ID del cuestionario al que pertenecen
            preguntas: Lista de tuplas (texto, imagen)

        Returns:
            Lista de IDs de las preguntas insertadas
        """
        conn = self.get_connection()
        c = conn.cursor()

        # Obtener el máximo ID antes de insertar para este cuestionario
        max_id_before = c.execute(
            "SELECT COALESCE(MAX(id), 0) FROM preguntas WHERE cuestionario_id = ?",
            (cuestionario_id,)
        ).fetchone()[0]

        c.executemany(
            "INSERT INTO preguntas (cuestionario_id, texto, imagen) VALUES (?, ?, ?)",
            [(cuestionario_id, p[0], p[1]) for p in preguntas]
        )

        # Obtener los IDs insertados (deben ser consecutivos desde max_id_before + 1)
        pregunta_ids = [row[0] for row in c.execute(
            "SELECT id FROM preguntas WHERE cuestionario_id = ? AND id > ? ORDER BY id ASC",
            (cuestionario_id, max_id_before)
        ).fetchall()]

        conn.commit()
        conn.close()

        return pregunta_ids

    def insertar_respuesta(self, pregunta_id: int, texto: str, correcta: int) -> int:
        """
        Inserta una respuesta y retorna su ID

        Args:
            pregunta_id: ID de la pregunta a la que pertenece
            texto: Texto de la respuesta
            correcta: 1 si es correcta, 0 si no

        Returns:
            ID de la respuesta insertada
        """
        conn = self.get_connection()
        c = conn.cursor()

        c.execute(
            "INSERT INTO respuestas (pregunta_id, texto, correcta) VALUES (?, ?, ?)",
            (pregunta_id, texto, correcta)
        )

        respuesta_id = c.lastrowid
        conn.commit()
        conn.close()

        return respuesta_id

    def insertar_respuestas_batch(self, respuestas: List[Tuple[int, str, int]]):
        """
        Inserta múltiples respuestas

        Args:
            respuestas: Lista de tuplas (pregunta_id, texto, correcta)
        """
        conn = self.get_connection()
        c = conn.cursor()

        c.executemany(
            "INSERT INTO respuestas (pregunta_id, texto, correcta) VALUES (?, ?, ?)",
            respuestas
        )

        conn.commit()
        conn.close()

    def obtener_preguntas(self, cuestionario_id: Optional[str] = None, limit: Optional[int] = None) -> List[Tuple]:
        """
        Obtiene preguntas de la base de datos

        Args:
            cuestionario_id: ID del cuestionario (opcional, si no se especifica trae todas)
            limit: Límite de resultados (opcional)

        Returns:
            Lista de tuplas (id, cuestionario_id, texto)
        """
        conn = self.get_connection()
        c = conn.cursor()

        if cuestionario_id:
            query = "SELECT * FROM preguntas WHERE cuestionario_id = ?"
            params = (cuestionario_id,)
        else:
            query = "SELECT * FROM preguntas"
            params = ()

        if limit:
            query += f" LIMIT {limit}"

        results = c.execute(query, params).fetchall()
        conn.close()

        return results

    def obtener_respuestas(self, pregunta_id: int) -> List[Tuple]:
        """
        Obtiene las respuestas de una pregunta

        Args:
            pregunta_id: ID de la pregunta

        Returns:
            Lista de tuplas (id, pregunta_id, texto, correcta)
        """
        conn = self.get_connection()
        c = conn.cursor()

        results = c.execute(
            "SELECT * FROM respuestas WHERE pregunta_id = ?",
            (pregunta_id,)
        ).fetchall()

        conn.close()

        return results

    def obtener_cuestionarios(self) -> List[Tuple]:
        """
        Obtiene todos los cuestionarios

        Returns:
            Lista de tuplas (id, url, nombre, fecha_creacion)
        """
        conn = self.get_connection()
        c = conn.cursor()

        results = c.execute("SELECT * FROM cuestionarios ORDER BY fecha_creacion DESC").fetchall()
        conn.close()

        return results

    def obtener_cuestionario_por_id(self, cuestionario_id: str) -> Optional[Tuple]:
        """
        Obtiene un cuestionario por su ID (nombre)

        Args:
            cuestionario_id: ID (nombre) del cuestionario

        Returns:
            Tupla (id, url, nombre, fecha_creacion) o None si no existe
        """
        conn = self.get_connection()
        c = conn.cursor()

        result = c.execute(
            "SELECT * FROM cuestionarios WHERE id = ?",
            (cuestionario_id,)
        ).fetchone()

        conn.close()

        return result

