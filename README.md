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

### Notes

- Dependencies used: Playwright (third-party), `sqlite3` (built-in), `asyncio` (built-in).
- The browser is launched in non-headless mode by default for visibility.
