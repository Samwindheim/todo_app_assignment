from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# Create FastAPI app instance
app = FastAPI()

# --- Pydantic Models for Data Validation ---

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    completed: bool = False

class TaskCreate(TaskBase):
    pass # Inherits all fields from TaskBase

class Task(TaskBase):
    id: int

# --- In-Memory "Database" ---

# Sample in-memory "database" for tasks
# We'll replace this with a proper database connection later
tasks_db: List[Task] = [
    Task(id=1, title="Groceries", description="Bananas, Bread", completed=False),
    Task(id=2, title="Laundry", description="Shirts, Socks", completed=False),
]

# Helper to get next ID (simple increment)
_next_id = 3

def get_next_id():
    global _next_id
    current_id = _next_id
    _next_id += 1
    return current_id

# --- API Endpoints ---

@app.get("/api/tasks", response_model=List[Task])
async def get_tasks():
    """
    Retrieve a list of all tasks.
    """
    return tasks_db

@app.post("/api/tasks", response_model=Task, status_code=201)
async def create_task(task_in: TaskCreate):
    """
    Create a new task.
    """
    new_id = get_next_id()
    new_task = Task(id=new_id, **task_in.model_dump())
    tasks_db.append(new_task)
    return new_task

# Add a simple root endpoint for testing
@app.get("/")
async def read_root():
    return {"message": "Todo App Backend is running!"}