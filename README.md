## quiz_scraper

A simple Playwright-based scraper that visits a Daypo-like quiz page, extracts the current question and its answer options, and stores them in a local SQLite database.

### Install

- Install dependencies:

```bash
pip install playwright
```

- Install Playwright browsers:

```bash
playwright install
```

### Run

```bash
python main.py
```

You will be prompted to paste the quiz URL.

### Database

- The script creates a local SQLite database file named `cuestionarios.db` in the project directory.
- It contains two tables: `preguntas` and `respuestas`.
  - `preguntas`: stores each question text.
  - `respuestas`: stores each answer option linked to its question and whether it is correct.

### How correctness is detected

- Each answer row has an associated canvas (`vaiX`).
- The script calls `.toDataURL()` on those canvases and compares the data URL to a provided reference image string.
- If they match, the answer is marked as correct.

### User Interface (MCP Server)

This project includes a Model Context Protocol (MCP) server that allows LLMs to interact with the scraper and the database.

#### Installation

1. Install all dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install
   ```

#### Usage with Claude Desktop

Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "daypo-scraper": {
      "command": "python",
      "args": ["/path/to/quiz_scraper/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/path/to/quiz_scraper"
      }
    }
  }
}
```

#### Available Tools

- `scrape_daypo`: Scrapes a quiz given its URL or ID.
- `list_scraped_quizzes`: Shows a list of quizzes already in the database.
- `get_quiz_content`: Retrieves questions and answers for a specific quiz ID.
