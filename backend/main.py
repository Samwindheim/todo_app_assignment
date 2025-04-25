from fastapi import FastAPI
from typing import List, Dict, Any

# Create FastAPI app instance
app = FastAPI()

# Sample in-memory "database" for tasks
# We'll replace this with a proper database connection later
tasks_db: List[Dict[str, Any]] = [
    {"id": 1, "title": "Groceries", "description": "Bananas, Bread", "completed": False},
    {"id": 2, "title": "Laundry", "description": "Shirts, Socks", "completed": False},
]

@app.get("/api/tasks")
async def get_tasks() -> List[Dict[str, Any]]:
    """
    Retrieve a list of all tasks.
    """
    return tasks_db

# Add a simple root endpoint for testing
@app.get("/")
async def read_root():
    return {"message": "Todo App Backend is running!"}