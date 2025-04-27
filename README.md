# Todo/Task-List App Assignment

This project is a simple Todo/Task-List application featuring a Python FastAPI backend with SQLite persistence and a React+TypeScript frontend.

It fulfills the core requirements (add, edit, delete, mark-as-done tasks) and includes an LLM feature for automatic task labeling.

## Features

- **Core:** Add, edit, delete, and toggle completion status for tasks.
- **Persistence:** Tasks are saved locally in an SQLite database (`backend/todo.db`).
- **LLM - Smart Labeling:** When tasks are created or their text content is updated, the OpenAI API (`gpt-3.5-turbo`) is called to suggest 1-3 relevant labels (e.g., `[work, urgent]`). These are displayed in the UI.

## Setup and Running

### Prerequisites

- Python 3.8+
- Node.js & npm
- Make
- An OpenAI API Key

### Instructions

1.  **Clone the repository.**
2.  **Set up API Key:**
    - Copy the example environment file: `cp backend/.env.example backend/.env`
    - Edit `backend/.env` and add your `OPENAI_API_KEY`.
3.  **Install dependencies and set up environment:**
    ```bash
    make setup
    ```
4.  **Run the application (Backend + Frontend):**
    ```bash
    make run
    ```
    - Backend runs at `http://127.0.0.1:8000`.
    - Frontend runs at `http://localhost:5173` (or next available port).
    - Open the frontend URL in your browser.
    - Press `Ctrl+C` to stop.

### Other Useful Commands

- `make install`: Reinstall/update dependencies if `requirements.txt` or `package.json` changes (assumes venv exists).
- `make run-backend`: Run only the backend server.
- `make run-frontend`: Run only the frontend server.
- `make clean`: Remove virtual environment, `node_modules`, database file, and other generated files.
- `make help`: Display all available commands.

## LLM Integration Details

- **Model:** `gpt-3.5-turbo` (via `openai` library).
- **Prompt Strategy:** The LLM is asked to suggest 1-3 concise, lowercase, comma-separated labels based on the task title/description, or return `None`.
- **Error Handling/Fallback:** If the API key is missing or the API call fails (e.g., network error, rate limit), the backend logs an error and proceeds without labels. The main application functionality is unaffected.

## Testing

Unit tests are included for the backend LLM logic (`get_labels_for_task`).

1.  **Prerequisites:** Ensure development dependencies are installed via `make setup` or `make install`.
2.  **Run tests:** Execute from the project root directory:
    ```bash
    pytest
    ```
    - Tests are located in `backend/tests/`.
    - The tests mock the OpenAI API call to verify success and failure scenarios for label generation.
    - Ensure the backend virtual environment (`backend/venv/bin/activate`) is active if running `pytest` manually outside of Make.

# Design Decisions & Trade-offs

- **Backend (FastAPI):** Chosen for its modern async capabilities (good fit for I/O-bound tasks like API calls and DB operations), speed, automatic OpenAPI documentation (`/docs`), and built-in data validation with Pydantic. \_Trade-off: Smaller ecosystem compared to Flask/Django.
- **Frontend (React + TypeScript + Vite):** React provides a robust component model for UIs. TypeScript adds static typing for better maintainability and catching errors early. Vite offers a fast development experience. \_Trade-off: Can involve a slightly steeper learning curve.
- **Database (SQLite):** Used for simplicity and local persistence as per requirements (no external DB setup needed). `SQLAlchemy` Core + `databases` library provide async access. \_Trade-off: Potential limitations if schema evolution becomes complex.
- **LLM Integration (OpenAI Library):** The official `openai` library was used directly for simplicity in making single API calls for labeling. \_Trade-off: For more complex LLM workflows (chaining calls, agents), a framework like LangChain might offer more structure but adds complexity/dependencies.
- **LLM Error Handling:** Implemented a fallback where the app continues to function (returning tasks without labels) if the OpenAI API call fails.
- **Development Workflow (Makefile):** A `Makefile` provides reproducible, one-command setup (`make setup`) and run (`make run`) commands, improving developer experience.
- **API Key Management (`.env`):** Standard `python-dotenv` approach used to keep secrets out of version control.
