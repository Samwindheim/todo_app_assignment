import databases
import sqlalchemy
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional # Removed Dict, Any as they might not be needed anymore
import os # To construct database path safely

# --- Database Configuration ---

# Define the path for the SQLite database file relative to this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE_PATH = os.path.join(BASE_DIR, 'todo.db')

# Async URL for the 'databases' library
DATABASE_URL = f"sqlite+aiosqlite:///{DB_FILE_PATH}"

# Sync URL for SQLAlchemy engine (for table creation)
SYNC_DATABASE_URL = f"sqlite:///{DB_FILE_PATH}"

# Create a Database instance for async operations
database = databases.Database(DATABASE_URL)

# SQLAlchemy metadata object
metadata = sqlalchemy.MetaData()

# Define the 'tasks' table structure using SQLAlchemy Core
tasks_table = sqlalchemy.Table(
    "tasks",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("title", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("description", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("completed", sqlalchemy.Boolean, default=False),
)

# Create a synchronous engine ONLY for creating the table
sync_engine = sqlalchemy.create_engine(SYNC_DATABASE_URL)

# --- Pydantic Models for Data Validation ---

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    completed: bool = False

class TaskCreate(TaskBase):
    pass # Inherits all fields from TaskBase

class TaskUpdate(TaskBase): # Model for PUT requests
    pass # Inherits all fields from TaskBase

class Task(TaskBase):
    id: int

# --- FastAPI Application ---

app = FastAPI()

# --- Event Handlers for Database Connection ---

@app.on_event("startup")
async def startup():
    # Create the database table using the synchronous engine
    try:
        print(f"Attempting to create tables in database at: {DB_FILE_PATH}")
        metadata.create_all(bind=sync_engine) # USE SYNC ENGINE HERE
        print("Database tables checked/created successfully.")
    except Exception as e:
        print(f"Error creating database tables: {e}")
        # Decide if you want the app to fail startup or continue
        # raise e # Uncomment to stop app if table creation fails

    # Connect to the database using the async 'databases' instance
    try:
        await database.connect()
        print("Database connection established.")
    except Exception as e:
        print(f"Error connecting to database: {e}")
        # Handle connection error (e.g., raise to stop app)
        raise e

@app.on_event("shutdown")
async def shutdown():
    # Disconnect from the database
    try:
        await database.disconnect()
        print("Database connection closed.")
    except Exception as e:
        print(f"Error disconnecting from database: {e}")

# --- API Endpoints (Modified for Database) ---

@app.get("/api/tasks", response_model=List[Task])
async def get_tasks():
    """
    Retrieve a list of all tasks from the database.
    """
    query = tasks_table.select()
    return await database.fetch_all(query)

@app.post("/api/tasks", response_model=Task, status_code=201)
async def create_task(task_in: TaskCreate):
    """
    Create a new task in the database.
    """
    query = tasks_table.insert().values(
        title=task_in.title,
        description=task_in.description,
        completed=task_in.completed
    )
    # Execute the insert query and get the ID of the new row
    last_record_id = await database.execute(query)
    # Return the created task including the generated ID
    return Task(id=last_record_id, **task_in.model_dump())

@app.put("/api/tasks/{task_id}", response_model=Task)
async def update_task(task_id: int, task_in: TaskUpdate):
    """
    Update an existing task in the database by ID.
    """
    query = (
        tasks_table.update()
        .where(tasks_table.c.id == task_id)
        .values(
            title=task_in.title,
            description=task_in.description,
            completed=task_in.completed
        )
    )
    # Execute the update query
    result = await database.execute(query)

    # Check if any row was updated
    if result == 0:
         check_query = tasks_table.select().where(tasks_table.c.id == task_id)
         updated_task = await database.fetch_one(check_query)
         if updated_task is None:
             raise HTTPException(status_code=404, detail="Task not found")
         return updated_task

    # Fetch the updated task data to return
    fetch_query = tasks_table.select().where(tasks_table.c.id == task_id)
    updated_task_data = await database.fetch_one(fetch_query)
    if updated_task_data is None:
         raise HTTPException(status_code=404, detail="Task not found after update attempt")

    # Ensure the returned data conforms to the Pydantic model
    # The fetch_one result is a RowProxy, which behaves like a dict/namedtuple
    # Pydantic can usually handle this directly if field names match
    return updated_task_data

@app.delete("/api/tasks/{task_id}", status_code=204)
async def delete_task(task_id: int):
    """
    Delete a task from the database by ID.
    """
    query = tasks_table.delete().where(tasks_table.c.id == task_id)
    # Execute the delete query
    result = await database.execute(query)

    # Check if any row was deleted
    if result == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # No content to return for 204
    return

# Add a simple root endpoint for testing
@app.get("/")
async def read_root():
    return {"message": "Todo App Backend is running with SQLite persistence!"}
