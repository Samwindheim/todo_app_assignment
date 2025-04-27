import databases
import sqlalchemy
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional # Removed Dict, Any as they might not be needed anymore
import os # To construct database path safely
import logging # Added for logging

# --- LLM & Environment Configuration ---
from dotenv import load_dotenv
from openai import AsyncOpenAI, OpenAIError # Added OpenAI imports

load_dotenv() # Load environment variables from .env file

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client (only if key is present)
aclient = None
if OPENAI_API_KEY:
    aclient = AsyncOpenAI(api_key=OPENAI_API_KEY)
    logger.info("OpenAI client initialized.")
else:
    logger.warning("OPENAI_API_KEY not found in environment variables. LLM features will be disabled.")

# --- LLM Helper Function ---
async def get_labels_for_task(title: str, description: Optional[str]) -> Optional[str]:
    """Calls OpenAI API to suggest labels for a task based on title and description."""
    if not aclient: # Check if client was initialized (API key present)
        logger.warning("OpenAI client not available. Skipping label generation.")
        return None

    combined_text = f"Title: {title}"
    if description:
        combined_text += f"\nDescription: {description}"

    # Basic Prompt Strategy
    system_prompt = "You are an assistant that suggests relevant labels for tasks."
    user_prompt = (
        f"Suggest 1-3 relevant labels for the following task. "
        f"Labels should be concise, lowercase words (e.g., 'work', 'urgent', 'shopping', 'bug', 'feature'). "
        f"Separate multiple labels with a comma and a space (e.g., 'personal, urgent'). "
        f"If no specific labels seem highly relevant, respond with 'None'."
        f"\n\nTask:\n{combined_text}"
        f"\n\nSuggested Labels:"
    )

    try:
        logger.info(f"Requesting labels for task: '{title[:50]}...' ")
        response = await aclient.chat.completions.create(
            model="gpt-3.5-turbo", # Or choose another suitable model like gpt-4o-mini
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2, # Lower temperature for more focused output
            max_tokens=20, # Limit response length
            n=1, # Get one response
            stop=None # No specific stop sequence needed
        )

        suggested_labels = response.choices[0].message.content.strip()
        logger.info(f"Received labels: '{suggested_labels}' for task: '{title[:50]}...' ")

        # Basic validation/cleanup
        if suggested_labels.lower() == 'none' or not suggested_labels:
            return None

        # Optional: Further sanitize labels (e.g., remove extra spaces, ensure lowercase)
        cleaned_labels = ", ".join([label.strip().lower() for label in suggested_labels.split(',') if label.strip()])

        return cleaned_labels if cleaned_labels else None

    except OpenAIError as e:
        logger.error(f"OpenAI API error while getting labels for task '{title[:50]}...': {e}")
        return None # Fallback: return None on API error
    except Exception as e:
        logger.error(f"Unexpected error while getting labels for task '{title[:50]}...': {e}")
        return None # Fallback: return None on other errors

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
    sqlalchemy.Column("labels", sqlalchemy.String, nullable=True),
)

# Create a synchronous engine ONLY for creating the table
sync_engine = sqlalchemy.create_engine(SYNC_DATABASE_URL)

# --- Pydantic Models for Data Validation ---

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    completed: bool = False
    labels: Optional[str] = None

class TaskCreate(TaskBase):
    # We will *not* accept labels directly on creation
    # Labels will be generated after creation
    title: str
    description: Optional[str] = None
    completed: bool = False

class TaskUpdate(TaskBase): # Model for PUT requests
    # We *will* accept labels during update, in case user wants to override
    title: str
    description: Optional[str] = None
    completed: bool = False
    labels: Optional[str] = None # Allow labels to be updated

class Task(TaskBase):
    id: int
    # Ensure labels is included in the final Task model returned by API
    labels: Optional[str] = None

# --- FastAPI Application ---

app = FastAPI()
# --- CORS Middleware Configuration ---

# Define allowed origins (your frontend URL)
origins = [
    "http://localhost:5173", # Vite default dev server
    "http://127.0.0.1:5173", # Sometimes accessed via IP
    # Add other origins if needed (e.g., deployed frontend URL)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # List of allowed origins
    allow_credentials=True, # Allow cookies (optional, but good practice)
    allow_methods=["*"],    # Allow all standard methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],    # Allow all headers
)

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
    Create a new task in the database and generate labels using LLM.
    """
    # 1. Insert the basic task data (without labels initially)
    insert_query = tasks_table.insert().values(
        title=task_in.title,
        description=task_in.description,
        completed=task_in.completed,
        labels=None # Explicitly set labels to None initially
    )
    last_record_id = await database.execute(insert_query)

    # 2. Attempt to get labels from LLM
    generated_labels = await get_labels_for_task(task_in.title, task_in.description)

    # 3. Update the task with labels if generated successfully
    if generated_labels:
        update_query = (
            tasks_table.update()
            .where(tasks_table.c.id == last_record_id)
            .values(labels=generated_labels)
        )
        await database.execute(update_query)

    # 4. Fetch the final task data (including potential labels) to return
    fetch_query = tasks_table.select().where(tasks_table.c.id == last_record_id)
    created_task = await database.fetch_one(fetch_query)

    if created_task is None:
        # This should ideally not happen if insert succeeded
        raise HTTPException(status_code=500, detail="Failed to retrieve task after creation")

    # Pydantic will validate the RowProxy object against the Task model
    return created_task

@app.put("/api/tasks/{task_id}", response_model=Task)
async def update_task(task_id: int, task_in: TaskUpdate):
    """
    Update an existing task in the database by ID.
    If title/description changes, regenerate labels using LLM.
    """
    # 1. Fetch the current task to check if text changed
    fetch_query = tasks_table.select().where(tasks_table.c.id == task_id)
    current_task = await database.fetch_one(fetch_query)

    if current_task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    # Determine if text content relevant for labeling has changed
    text_changed = (
        current_task["title"] != task_in.title or
        current_task["description"] != task_in.description
    )

    # 2. Generate new labels if text changed, otherwise use provided labels or keep old
    labels_to_set = current_task["labels"] # Default to keeping old labels
    if text_changed:
        logger.info(f"Task text changed for ID {task_id}. Regenerating labels...")
        generated_labels = await get_labels_for_task(task_in.title, task_in.description)
        if generated_labels is not None:
            labels_to_set = generated_labels
        # If LLM fails or returns None, we keep the old labels unless explicitly cleared by user
        elif task_in.labels is None:
             labels_to_set = None # Allow user to clear labels by passing null

    elif task_in.labels is not None:
         # Text didn't change, but user provided labels in the PUT request
         labels_to_set = task_in.labels
    # If text didn't change and user didn't provide labels, labels_to_set retains original value


    # 3. Update the task in the database with all new values
    update_query = (
        tasks_table.update()
        .where(tasks_table.c.id == task_id)
        .values(
            title=task_in.title,
            description=task_in.description,
            completed=task_in.completed,
            labels=labels_to_set # Set the determined labels
        )
    )
    result = await database.execute(update_query)

    # 4. Fetch the updated task data to return
    # Re-fetch necessary as the update query doesn't return the row
    updated_task_data = await database.fetch_one(fetch_query)
    if updated_task_data is None:
         # Should not happen if the task existed initially
         raise HTTPException(status_code=404, detail="Task not found after update attempt")

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
