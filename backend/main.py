import databases
import sqlalchemy
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import logging

# ==============================================================================
# 1. CONFIGURATION (Environment, Logging, OpenAI Client)
# ==============================================================================
from dotenv import load_dotenv
from openai import AsyncOpenAI, OpenAIError

# Load API keys and other settings from .env file into environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Setup basic logging to see informational messages and errors
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the asynchronous OpenAI client *only if* the API key is available.
# This allows the app to run without an API key (LLM features disabled).
aclient = None
if OPENAI_API_KEY:
    aclient = AsyncOpenAI(api_key=OPENAI_API_KEY)
    logger.info("OpenAI client initialized. LLM labeling enabled.")
else:
    logger.warning("OPENAI_API_KEY not found. LLM labeling disabled.")

# ==============================================================================
# 2. LLM HELPER FUNCTION (Smart Labeling Logic)
# ==============================================================================
async def get_labels_for_task(title: str, description: Optional[str]) -> Optional[str]:
    """
    Calls the OpenAI API to suggest relevant labels for a task.

    Args:
        title: The task title.
        description: The task description (optional).

    Returns:
        A comma-separated string of labels (e.g., "work, urgent") or None if
        no labels are suggested, the API key is missing, or an error occurs.
    """
    # Gracefully handle missing API key/client
    if not aclient:
        logger.warning("OpenAI client not available. Skipping label generation.")
        return None

    # Combine title and description for context
    combined_text = f"Title: {title}"
    if description:
        combined_text += f"\nDescription: {description}"

    # Define the instructions for the LLM
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
        logger.info(f"Requesting LLM labels for task: '{title[:50]}...'")
        # Make the asynchronous API call to OpenAI
        response = await aclient.chat.completions.create(
            model="gpt-3.5-turbo", # Using a cost-effective and capable model
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2, # Lower temperature for more predictable, less creative output
            max_tokens=20,   # Limit the length of the generated label string
            n=1,             # Request a single completion
            stop=None
        )

        suggested_labels = response.choices[0].message.content.strip()
        logger.info(f"Received labels: '{suggested_labels}' for task: '{title[:50]}...'")

        # Handle cases where the model explicitly says "None" or returns empty
        if suggested_labels.lower() == 'none' or not suggested_labels:
            return None

        # Clean up the labels (lowercase, remove extra spaces)
        cleaned_labels = ", ".join([label.strip().lower() for label in suggested_labels.split(',') if label.strip()])

        return cleaned_labels if cleaned_labels else None

    except OpenAIError as e:
        # Handle API-specific errors (e.g., connection, authentication)
        logger.error(f"OpenAI API error getting labels for task '{title[:50]}...': {e}")
        return None # Fallback: return None on API error
    except Exception as e:
        # Handle unexpected errors during the API call or processing
        logger.error(f"Unexpected error getting labels for task '{title[:50]}...': {e}")
        return None # Fallback: return None on other errors

# ==============================================================================
# 3. DATABASE CONFIGURATION (SQLite, SQLAlchemy, `databases`)
# ==============================================================================

# Define the base directory of the backend application
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Construct the full path to the SQLite database file
DB_FILE_PATH = os.path.join(BASE_DIR, 'todo.db')

# Database URL for `databases` library (async access)
# Format: sqlite+aiosqlite:///path/to/your/database.db
DATABASE_URL = f"sqlite+aiosqlite:///{DB_FILE_PATH}"

# Database URL for SQLAlchemy Core (used for initial table creation - synchronous)
# Format: sqlite:///path/to/your/database.db
SYNC_DATABASE_URL = f"sqlite:///{DB_FILE_PATH}"

# Instantiate the `databases` object for performing async database operations
database = databases.Database(DATABASE_URL)

# SQLAlchemy metadata container (holds table definitions)
metadata = sqlalchemy.MetaData()

# ==============================================================================
# 4. DATABASE SCHEMA DEFINITION (SQLAlchemy Table Object)
# ==============================================================================

# Define the structure of the 'tasks' table using SQLAlchemy Core syntax
tasks_table = sqlalchemy.Table(
    "tasks",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True), # Auto-incrementing primary key
    sqlalchemy.Column("title", sqlalchemy.String, nullable=False),  # Task title is required
    sqlalchemy.Column("description", sqlalchemy.String, nullable=True), # Optional description
    sqlalchemy.Column("completed", sqlalchemy.Boolean, default=False), # Defaults to not completed
    sqlalchemy.Column("labels", sqlalchemy.String, nullable=True),   # Optional comma-separated labels
)

# Create a synchronous SQLAlchemy engine ONLY for creating the table if it doesn't exist.
# This is done during application startup.
sync_engine = sqlalchemy.create_engine(SYNC_DATABASE_URL)

# ==============================================================================
# 5. PYDANTIC MODELS (API Data Validation & Serialization)
# ==============================================================================
# These models define the expected structure of data in API requests and responses.
# FastAPI uses them for automatic validation and serialization (converting to/from JSON).

class TaskBase(BaseModel):
    """Base model with common task fields."""
    title: str
    description: Optional[str] = None
    completed: bool = False
    labels: Optional[str] = None # Note: Labels are generally handled by backend logic

class TaskCreate(TaskBase):
    """Model used when creating a new task (input). Does not accept labels directly."""
    # Labels are omitted here because they will be generated by the LLM after creation.
    title: str
    description: Optional[str] = None
    completed: bool = False # Keep default

class TaskUpdate(TaskBase):
    """Model used when updating an existing task (input for PUT). Allows label override."""
    # All fields are included as they can potentially be updated.
    # Users can optionally provide labels here to manually override LLM suggestions.
    title: str
    description: Optional[str] = None
    completed: bool = False
    labels: Optional[str] = None

class Task(TaskBase):
    """Model representing a task as returned by the API (output). Includes the ID."""
    # This is the final shape of the task data sent back to the client.
    id: int
    # Ensure labels is part of the response model.
    labels: Optional[str] = None

# ==============================================================================
# 6. FASTAPI APPLICATION SETUP (App Instance, CORS Middleware)
# ==============================================================================

# Create the main FastAPI application instance
app = FastAPI()

# Configure Cross-Origin Resource Sharing (CORS)
# This allows the frontend (running on a different origin, e.g., localhost:5173)
# to make requests to this backend API (running on localhost:8000).
origins = [
    "http://localhost:5173", # Default Vite dev server address
    "http://127.0.0.1:5173",
    # Add production frontend URL here if deploying
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # Allow specific origins listed above
    allow_credentials=True,    # Allow cookies (not used here, but good practice)
    allow_methods=["*"],       # Allow all standard HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],       # Allow all request headers
)

# ==============================================================================
# 7. STARTUP/SHUTDOWN EVENTS (Database Connection Management)
# ==============================================================================

@app.on_event("startup")
async def startup():
    """Actions to perform when the FastAPI application starts."""
    # 1. Ensure the database table exists.
    #    Uses the synchronous engine as table creation is typically a one-off setup task.
    try:
        logger.info(f"Checking/Creating database table 'tasks' at: {DB_FILE_PATH}")
        metadata.create_all(bind=sync_engine) # Create table if it doesn't exist
        logger.info("Database table check/creation complete.")
    except Exception as e:
        logger.error(f"Error during database table creation: {e}")
        # Depending on severity, might want to raise exception to stop startup
        # raise e

    # 2. Connect to the database using the async 'databases' instance.
    #    This connection will be used for all API endpoint operations.
    try:
        await database.connect()
        logger.info("Async database connection established.")
    except Exception as e:
        logger.error(f"Error connecting to async database: {e}")
        # Stop the application if database connection fails on startup
        raise e

@app.on_event("shutdown")
async def shutdown():
    """Actions to perform when the FastAPI application shuts down."""
    # Disconnect the async database connection gracefully.
    try:
        await database.disconnect()
        logger.info("Async database connection closed.")
    except Exception as e:
        logger.error(f"Error disconnecting from async database: {e}")

# ==============================================================================
# 8. API ENDPOINTS (CRUD Operations & LLM Integration)
# ==============================================================================

# --- Read Tasks ---
@app.get("/api/tasks", response_model=List[Task])
async def get_tasks():
    """
    Retrieve a list of all tasks from the database.
    """
    logger.info("Received request to get all tasks.")
    query = tasks_table.select() # SQLAlchemy query to select all rows
    return await database.fetch_all(query) # Execute query asynchronously

# --- Create Task ---
@app.post("/api/tasks", response_model=Task, status_code=201)
async def create_task(task_in: TaskCreate):
    """
    Create a new task, generate labels using LLM, and store in the database.
    """
    logger.info(f"Received request to create task: '{task_in.title[:50]}...'")
    # 1. Insert basic task data (labels intentionally set to None initially)
    insert_query = tasks_table.insert().values(
        title=task_in.title,
        description=task_in.description,
        completed=task_in.completed,
        labels=None # Labels will be added in step 3 if generated
    )
    # Execute insert and get the ID of the newly created row
    last_record_id = await database.execute(insert_query)
    logger.info(f"Inserted task with ID: {last_record_id}")

    # 2. Attempt to get labels from the LLM helper function
    generated_labels = await get_labels_for_task(task_in.title, task_in.description)

    # 3. Update the task with labels if they were generated successfully
    if generated_labels:
        logger.info(f"Updating task ID {last_record_id} with labels: '{generated_labels}'")
        update_query = (
            tasks_table.update()
            .where(tasks_table.c.id == last_record_id)
            .values(labels=generated_labels)
        )
        await database.execute(update_query)
    else:
        logger.info(f"No labels generated or LLM disabled for task ID {last_record_id}.")

    # 4. Fetch the complete task data (including potential labels) to return
    #    Must fetch again to get the final state after potential update.
    fetch_query = tasks_table.select().where(tasks_table.c.id == last_record_id)
    created_task = await database.fetch_one(fetch_query)

    if created_task is None:
        logger.error(f"Failed to fetch task ID {last_record_id} after creation.")
        raise HTTPException(status_code=500, detail="Failed to retrieve task after creation")

    # FastAPI automatically validates the fetched data against the Task response model
    return created_task

# --- Update Task ---
@app.put("/api/tasks/{task_id}", response_model=Task)
async def update_task(task_id: int, task_in: TaskUpdate):
    """
    Update an existing task by ID. Regenerates labels if title/description change.
    Allows manual override of labels via the request body.
    """
    logger.info(f"Received request to update task ID: {task_id}")
    # 1. Fetch the current task data to compare changes
    fetch_query = tasks_table.select().where(tasks_table.c.id == task_id)
    current_task = await database.fetch_one(fetch_query)

    if current_task is None:
        logger.warning(f"Update failed: Task ID {task_id} not found.")
        raise HTTPException(status_code=404, detail="Task not found")

    # Convert RowProxy to dict for easier access (optional but can be clearer)
    # current_task_dict = dict(current_task) if current_task else {}

    # 2. Determine if labels need regeneration or if user provided override
    labels_to_set = current_task["labels"] # Default: keep existing labels

    # Check if text content relevant to labeling has changed
    text_changed = (
        current_task["title"] != task_in.title or
        current_task["description"] != task_in.description
    )

    if text_changed:
        logger.info(f"Task text changed for ID {task_id}. Requesting LLM labels...")
        generated_labels = await get_labels_for_task(task_in.title, task_in.description)
        # Use generated labels if successful, otherwise keep old ones unless user clears them
        if generated_labels is not None:
            labels_to_set = generated_labels
            logger.info(f"Using newly generated labels for task ID {task_id}: '{labels_to_set}'")
        elif task_in.labels is None: # User explicitly cleared labels while text changed
            labels_to_set = None
            logger.info(f"User cleared labels while text changed for task ID {task_id}.")
        else:
            logger.info(f"LLM label generation failed or skipped for task ID {task_id}, keeping old labels.")

    elif task_in.labels is not None:
         # Text didn't change, but user explicitly provided labels in the PUT request (manual override)
         labels_to_set = task_in.labels
         logger.info(f"User provided manual label override for task ID {task_id}: '{labels_to_set}'")
    # else: Text didn't change and user didn't provide labels -> keep original (labels_to_set holds original value)


    # 3. Update the task in the database with new values
    update_query = (
        tasks_table.update()
        .where(tasks_table.c.id == task_id)
        .values(
            title=task_in.title,
            description=task_in.description,
            completed=task_in.completed,
            labels=labels_to_set # Use the determined labels
        )
    )
    await database.execute(update_query)
    logger.info(f"Updated task ID {task_id} in database.")

    # 4. Fetch the updated task data to return the final state
    #    Must fetch again as `execute` doesn't return the updated row.
    updated_task_data = await database.fetch_one(fetch_query)
    if updated_task_data is None:
         # This is unlikely if the initial fetch succeeded, but check defensively.
         logger.error(f"Failed to fetch task ID {task_id} after update attempt.")
         raise HTTPException(status_code=404, detail="Task not found after update attempt")

    return updated_task_data

# --- Delete Task ---
@app.delete("/api/tasks/{task_id}", status_code=204)
async def delete_task(task_id: int):
    """
    Delete a task from the database by ID.
    """
    logger.info(f"Received request to delete task ID: {task_id}")
    query = tasks_table.delete().where(tasks_table.c.id == task_id)
    # Execute the delete query and get the number of rows affected
    result = await database.execute(query)

    # Check if a row was actually deleted (result > 0)
    if result == 0:
        logger.warning(f"Delete failed: Task ID {task_id} not found.")
        raise HTTPException(status_code=404, detail="Task not found")

    logger.info(f"Successfully deleted task ID: {task_id}")
    # Return None (FastAPI handles 204 No Content response)
    return

# --- Root Endpoint ---
@app.get("/")
async def read_root():
    """A simple root endpoint to confirm the backend is running."""
    return {"message": "Todo App Backend API is running!"}

# Note: Removed some redundant comments that just repeated the code.
# Added section headers and explanations focusing on purpose and flow.
