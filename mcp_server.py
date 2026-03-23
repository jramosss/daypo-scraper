import os
import asyncio
from mcp.server.fastmcp import FastMCP
<<<<<<< HEAD
from main import scrape, buscar_daypos
=======
from main import scrape
>>>>>>> master
from database import Database
from constants import DB_NAME

# Get absolute path to the database
base_path = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base_path, DB_NAME)

# Initialize FastMCP server
mcp = FastMCP("Daypo Scraper")

@mcp.tool()
<<<<<<< HEAD
async def search_daypo(subject: str) -> list:
    """
    Searches Daypo for quizzes related to a subject.
    Returns matches that are relevant (e.g., Siglo 21, Parciales).

    Args:
        subject: The name of the subject to search for.
    """
    try:
        results = await buscar_daypos(subject)
        return results
    except Exception as e:
        import traceback
        return [{"error": f"Error searching Daypo: {str(e)}", "details": traceback.format_exc()}]

@mcp.tool()
async def scrape_daypo(url_or_id: str) -> str:
    """
    Scrapes a Daypo quiz based on a URL or a quiz ID.

    Args:
        url_or_id: The full URL (e.g., https://www.daypo.com/quiz-name.html)
                   or just the quiz ID/name (e.g., quiz-name).
    """
    url = url_or_id
=======
async def scrape_daypo(url_or_id: str) -> str:
    """
    Scrapes a Daypo quiz based on a URL or a quiz ID.
    
    Args:
        url_or_id: The full URL (e.g., https://www.daypo.com/quiz-name.html) 
                   or just the quiz ID/name (e.g., quiz-name).
    """
    url = url_or_id
    import os, getpass
    print(f"DEBUG: MCP Process - User: {getpass.getuser()}, CWD: {os.getcwd()}")
    
>>>>>>> master
    # If it's just an ID/slug, construct the URL
    if not url.startswith("http"):
        # Common pattern for Daypo URLs
        if not url.endswith(".html"):
            url = f"https://www.daypo.com/{url}.html"
        else:
            url = f"https://www.daypo.com/{url}"
<<<<<<< HEAD

    # Ensure it ends with #test to skip the landing page if possible
    if "#test" not in url:
        url += "#test"

=======
    
    # Ensure it ends with #test to skip the landing page if possible
    if "#test" not in url:
        url += "#test"
        
>>>>>>> master
    try:
        quiz_id = await scrape(url)
        return f"Successfully scraped quiz. Database ID: {quiz_id}. URL: {url}"
    except Exception as e:
        import traceback
        return f"Error scraping quiz: {str(e)}\n{traceback.format_exc()}"

@mcp.tool()
def list_scraped_quizzes() -> list:
    """
    Lists all quizzes that have been scraped and stored in the local database.
    """
    db = Database(db_path)
    quizzes = db.obtener_cuestionarios()
    # Format: (id, url, nombre, fecha_creacion)
    return [
        {
            "id": q[0],
            "url": q[1],
            "nombre": q[2],
            "fecha_creacion": q[3]
<<<<<<< HEAD
        }
=======
        } 
>>>>>>> master
        for q in quizzes
    ]

@mcp.tool()
def get_quiz_content(quiz_id: str) -> dict:
    """
    Retrieves the full content (questions and answers) of a previously scraped quiz.
<<<<<<< HEAD

=======
    
>>>>>>> master
    Args:
        quiz_id: The ID (name) of the quiz in the database.
    """
    db = Database(db_path)
    quiz = db.obtener_cuestionario_por_id(quiz_id)
    if not quiz:
        return {"error": f"Quiz with ID {quiz_id} not found."}
<<<<<<< HEAD

=======
    
>>>>>>> master
    preguntas = db.obtener_preguntas(quiz_id)
    result = {
        "id": quiz[0],
        "nombre": quiz[2],
        "url": quiz[1],
        "preguntas": []
    }
<<<<<<< HEAD

=======
    
>>>>>>> master
    for p in preguntas:
        p_id, _, p_texto = p
        respuestas = db.obtener_respuestas(p_id)
        result["preguntas"].append({
            "pregunta": p_texto,
            "respuestas": [
<<<<<<< HEAD
                {"texto": r[2], "correcta": bool(r[3])}
                for r in respuestas
            ]
        })

=======
                {"texto": r[2], "correcta": bool(r[3])} 
                for r in respuestas
            ]
        })
        
>>>>>>> master
    return result

if __name__ == "__main__":
    mcp.run()
