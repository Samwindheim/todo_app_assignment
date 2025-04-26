# Todo/Task-List App Assignment

This project is a simple Todo/Task-List application built according to the specifications in `instructions.txt`. It features a Python FastAPI backend with SQLite persistence and a React frontend built with Vite and TypeScript.

## Tech Stack

- **Backend:** Python, FastAPI, Uvicorn, SQLAlchemy (Core), databases (for async), aiosqlite
- **Frontend:** React, TypeScript, Vite, Axios, CSS
- **Database:** SQLite

## Features

### Core Features (Implemented)

- View all tasks
- Add new tasks
- Mark tasks as complete/incomplete
- Edit existing tasks
- Delete tasks
- Tasks persist in a local SQLite database (`backend/todo.db`).

### LLM Feature (Planned)

- One of the following will be implemented:
  - Natural-language → Task
  - Smart labeling
  - Bulk summariser
- _Design details (prompt strategy, error handling, fallbacks) will be added here once the feature is implemented._

## Setup and Running Locally

### Prerequisites

- Python 3.8+ and pip
- Node.js and npm (or yarn)

### Backend Setup

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```
2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate # On Windows use `venv\Scripts\activate`
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Run the FastAPI server:**
    ```bash
    uvicorn main:app --reload
    ```
    The backend API will be available at `http://127.0.0.1:8000`.
    The SQLite database file (`todo.db`) will be created automatically in the `backend` directory if it doesn't exist.

### Frontend Setup

1.  **Navigate to the frontend directory (from the project root):**
    ```bash
    cd frontend
    ```
2.  **Install dependencies:**
    ```bash
    npm install
    # or if you use yarn: yarn install
    ```
3.  **Run the React development server:**
    ```bash
    npm run dev
    # or if you use yarn: yarn dev
    ```
    The frontend application will be available at `http://localhost:5173` (or another port if 5173 is busy).

### Running the App

Once both the backend and frontend servers are running, open your web browser and navigate to the frontend URL (e.g., `http://localhost:5173`). The app should connect to the backend API automatically.

## Project Structure

```
. (project root)
├── backend/
│   ├── main.py         # FastAPI application logic, API endpoints
│   ├── requirements.txt # Backend Python dependencies
│   ├── todo.db         # SQLite database file (auto-generated, ignored by git)
│   ├── .gitignore      # Backend-specific git ignores
│   └── venv/           # Virtual environment (ignored by git)
├── frontend/
│   ├── src/
│   │   ├── App.tsx     # Main React application component
│   │   ├── App.css     # Basic styling
│   │   └── ...         # Other React components/assets
│   ├── index.html      # HTML entry point
│   ├── package.json    # Frontend dependencies and scripts
│   ├── tsconfig.json   # TypeScript configuration
│   ├── vite.config.ts  # Vite configuration
│   └── .gitignore      # Frontend-specific git ignores (e.g., node_modules)
├── .gitignore          # Root git ignores
├── instructions.txt    # Project requirements
└── README.md           # This file
```

## Design Choices (Initial)

- **Backend Framework:** FastAPI was chosen for its speed, automatic documentation generation (Swagger UI at `/docs`), and excellent Pydantic integration for data validation.
- **Database:** SQLite was used for simplicity and local persistence as per requirements, avoiding the need for a separate database server setup. SQLAlchemy Core provides a schema definition layer, while the `databases` library enables async database access compatible with FastAPI.
- **Frontend Framework:** React with TypeScript (via Vite) was chosen for building a dynamic user interface with type safety.
- **API Communication:** Axios is used in the frontend for making HTTP requests to the backend API.
- **CORS:** Middleware is configured in FastAPI to allow requests from the frontend development server origin.

## Testing

- No automated tests have been implemented yet.
- _Details on how to run tests will be added here if/when they are created._
