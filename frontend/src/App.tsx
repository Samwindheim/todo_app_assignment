// ==============================================================================
// 1. IMPORTS & INTERFACES
// ==============================================================================
import { useState, useEffect, FormEvent } from 'react' // React hooks and types
import axios from 'axios' // For making HTTP requests to the backend API
import './App.css' // Basic styling

// Define the structure of a Task object, matching the backend's Task model
interface Task {
  id: number;
  title: string;
  description: string | null;
  completed: boolean;
  labels: string | null; // LLM-generated labels
}

// API Base URL (points to the FastAPI backend)
const API_URL = 'http://127.0.0.1:8000/api/tasks';

// ==============================================================================
// 2. MAIN APPLICATION COMPONENT
// ==============================================================================
function App() {
  // --- State Variables ---
  // useState hooks manage the component's data and trigger re-renders when data changes.

  // Holds the array of task objects fetched from the backend
  const [tasks, setTasks] = useState<Task[]>([]);
  // Stores any error message to display to the user (e.g., API connection issues)
  const [error, setError] = useState<string | null>(null);
  // Tracks the value of the input field for adding new tasks
  const [newTaskTitle, setNewTaskTitle] = useState<string>("");

  // State specifically for handling the inline editing feature:
  // Stores the ID of the task currently being edited (null if none)
  const [editingTaskId, setEditingTaskId] = useState<number | null>(null);
  // Stores the current text in the input field while editing a task title
  const [editedTaskTitle, setEditedTaskTitle] = useState<string>("");

  // ==============================================================================
  // 3. DATA FETCHING EFFECT
  // ==============================================================================

  // useEffect hook: Runs code after the component mounts (and potentially on updates).
  // Here, it fetches the initial list of tasks from the backend API.
  useEffect(() => {
    axios.get<Task[]>(API_URL)
      .then(response => {
        // Sort tasks on fetch: incomplete first, then newest first
        const sortedTasks = response.data.sort((a, b) => {
            if (a.completed === b.completed) {
                return b.id - a.id; // Newest first (higher ID) within the same status
            }
            return a.completed ? 1 : -1; // Incomplete tasks (false) come first
        });
        setTasks(sortedTasks); // Update the component's state with fetched tasks
        setError(null); // Clear any previous errors on successful fetch
      })
      .catch(err => {
        // Handle errors during the API call
        console.error("Error fetching tasks:", err);
        setError("Failed to fetch tasks. Is the backend running?");
      });
  }, []); // Empty dependency array `[]` means this effect runs only *once* when the component mounts.

  // ==============================================================================
  // 4. EVENT HANDLERS (User Actions)
  // ==============================================================================

  // --- Add Task --- Triggered by submitting the "Add Task" form.
  const handleAddTask = async (event: FormEvent) => {
    event.preventDefault(); // Prevent the default form submission (which causes a page reload)

    // Basic validation: prevent adding empty tasks
    if (!newTaskTitle.trim()) {
      setError("Task title cannot be empty.");
      return;
    }

    try {
      // Send a POST request to the backend API to create the new task
      const response = await axios.post<Task>(API_URL, {
        title: newTaskTitle, // Only title is needed; backend handles defaults and labels
      });

      // Update the local state immediately for a responsive UI:
      // Add the newly created task (from the response) to the beginning of the list
      // and re-sort to maintain the desired order.
      setTasks(prevTasks => {
          const updatedTasks = [response.data, ...prevTasks];
          return updatedTasks.sort((a, b) => {
              if (a.completed === b.completed) {
                  return b.id - a.id;
              }
              return a.completed ? 1 : -1;
          });
      });
      setNewTaskTitle(""); // Clear the input field
      setError(null); // Clear any errors
    } catch (err) {
      console.error("Error adding task:", err);
      setError("Failed to add task. Please try again.");
    }
  };

  // --- Toggle Task Completion --- Triggered by clicking a task's checkbox.
  const handleToggleComplete = async (taskToToggle: Task) => {
    // Prevent changing completion status while the task is being edited
    if (editingTaskId === taskToToggle.id) {
       return;
    }

    // Create the updated task data to send to the backend
    const updatedTaskData = {
        ...taskToToggle,
        completed: !taskToToggle.completed, // Invert the completed status
    };

    try {
      // Send a PUT request to update the task on the backend
      await axios.put(`${API_URL}/${taskToToggle.id}`, updatedTaskData);

      // Update the local state:
      // Map through existing tasks, replace the toggled one, and re-sort.
      setTasks(prevTasks => {
        const updatedTasks = prevTasks.map(task =>
          task.id === taskToToggle.id ? updatedTaskData : task
        );
        return updatedTasks.sort((a, b) => {
            if (a.completed === b.completed) {
                return b.id - a.id;
            }
            return a.completed ? 1 : -1;
        });
      });
      setError(null); // Clear errors
    } catch (err) {
      console.error("Error updating task status:", err);
      setError("Failed to update task status. Please try again.");
      // Note: UI doesn't automatically revert on error, shows message instead.
    }
  };

  // --- Delete Task --- Triggered by clicking the "Delete" button.
  const handleDeleteTask = async (taskIdToDelete: number) => {
    // Optional: Confirmation dialog (commented out)
    // if (!window.confirm("Are you sure?")) return;

    try {
      // Send a DELETE request to the backend API
      await axios.delete(`${API_URL}/${taskIdToDelete}`);

      // Update the local state:
      // Filter out the deleted task from the array.
      setTasks(prevTasks => prevTasks.filter(task => task.id !== taskIdToDelete));
      setError(null); // Clear errors
    } catch (err) {
      console.error("Error deleting task:", err);
      setError("Failed to delete task. Please try again.");
    }
  };

  // --- Start Editing Task --- Triggered by clicking an incomplete task's title or "Edit" button.
  const handleEditClick = (task: Task) => {
    setEditingTaskId(task.id); // Set which task is being edited
    setEditedTaskTitle(task.title); // Pre-fill the input with the current title
  };

  // --- Cancel Editing --- Triggered by clicking the "Cancel" button in edit mode.
  const handleCancelEdit = () => {
    setEditingTaskId(null); // Clear the editing task ID
    setEditedTaskTitle(""); // Clear the edit input field text
  };

  // --- Save Edited Task --- Triggered by clicking "Save" or pressing Enter in edit mode.
  const handleSaveEdit = async () => {
    if (editingTaskId === null) return; // Should not happen, but safety check

    // Basic validation for edited title
    if (!editedTaskTitle.trim()) {
        setError("Task title cannot be empty.");
        return;
    }

    // Find the original task data in the current state
    const originalTask = tasks.find(task => task.id === editingTaskId);
    if (!originalTask) {
        setError("Original task not found for editing."); // Defensive check
        setEditingTaskId(null); // Exit edit mode if task vanished
        return;
    }

    // Prepare the data payload for the PUT request.
    // Send the potentially updated title and all other *original* data.
    // The backend will handle label regeneration if the title changed.
    const updatedTaskData = {
        ...originalTask,
        title: editedTaskTitle.trim(), // Send the new title
        // labels: originalTask.labels // Send current labels; backend decides if they change
    };

    try {
      // Send PUT request. The response will contain the task data
      // potentially with updated labels from the backend.
      const response = await axios.put<Task>(`${API_URL}/${editingTaskId}`, updatedTaskData);
      const taskWithUpdatedLabels = response.data; // Task data returned by the API

      // Update local state using the data returned from the backend
      // (this ensures we have the latest labels)
      setTasks(prevTasks => {
        const updatedTasks = prevTasks.map(task =>
          task.id === editingTaskId ? taskWithUpdatedLabels : task // Replace with response data
        );
        // Re-sort the list
        return updatedTasks.sort((a, b) => {
            if (a.completed === b.completed) {
                return b.id - a.id;
            }
            return a.completed ? 1 : -1;
        });
      });
      setError(null); // Clear errors
      handleCancelEdit(); // Exit edit mode on success
    } catch (err) {
      console.error("Error updating task:", err);
      setError("Failed to update task. Please try again.");
      // Note: Does not exit edit mode on error, allowing user to retry.
    }
  };

  // ==============================================================================
  // 5. JSX RENDERING LOGIC
  // ==============================================================================
  return (
    <>
      <h1>Todo List</h1>

      {/* Display error message if the 'error' state is not null */}      
      {error && <p style={{ color: 'red' }}>{error}</p>}

      {/* --- Add Task Form --- */}      
      <form onSubmit={handleAddTask}>
        <input
          type="text"
          value={newTaskTitle} // Controlled input: value linked to state
          onChange={(e) => setNewTaskTitle(e.target.value)} // Update state on change
          placeholder="Enter new task title"
        />
        <button type="submit">Add Task</button>
      </form>

      {/* --- Task List --- */}      
      {/* Map over the 'tasks' state array to render each task as a list item */}      
      <ul>
        {tasks.map(task => (
          // Use task ID as the unique key for each list item (required by React)
          <li key={task.id} style={{ display: 'flex', alignItems: 'center', marginBottom: '10px', textDecoration: task.completed ? 'line-through' : 'none' }}>
            
            {/* CONDITIONAL RENDERING: Show edit UI or view UI */}            
            {editingTaskId === task.id ? (
              // --- Edit Mode UI --- (Shown only for the task being edited)
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <input
                  type="text"
                  value={editedTaskTitle} // Controlled input for editing
                  onChange={(e) => setEditedTaskTitle(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSaveEdit()} // Allow saving with Enter key
                  autoFocus // Automatically focus the input when it appears
                  style={{ marginRight: '10px' }}
                />
                <button onClick={handleSaveEdit} style={{ marginRight: '5px' }}>Save</button>
                <button onClick={handleCancelEdit}>Cancel</button>
              </div>

            ) : (
              // --- View Mode UI --- (Shown for tasks not being edited)
              <>
                {/* Checkbox for toggling completion */}                
                <input
                  type="checkbox"
                  checked={task.completed}
                  onChange={() => handleToggleComplete(task)}
                  style={{ marginRight: '10px' }}
                  // Disable checkbox if *any* task is currently being edited
                  disabled={editingTaskId !== null}
                />

                {/* Task Title (clickable to edit if not completed) */}                
                <span 
                   onClick={() => !task.completed && handleEditClick(task)} // Only allow editing incomplete tasks
                   style={{ cursor: task.completed ? 'default' : 'pointer', marginRight: '10px' }}
                 >
                   {task.title}
                </span>

                {/* Display Labels if they exist */}                
                {task.labels && (
                    <span style={{ fontSize: '0.8em', color: 'grey', marginLeft: 'auto', marginRight: '10px' }}>
                         [{task.labels}]
                    </span>
                )}

                {/* Container for buttons (Edit/Delete) */}                
                {/* Adjust left margin automatically if labels are not present */}                
                <div style={{ marginLeft: task.labels ? '0' : 'auto'}}>
                    {/* Edit Button (only show if task is not completed) */}                    
                    {!task.completed &&
                        <button
                            onClick={() => handleEditClick(task)}
                            style={{ marginLeft: '10px', cursor: 'pointer' }}
                            // Disable button if *any* task is currently being edited
                            disabled={editingTaskId !== null}
                        >
                            Edit
                        </button>
                    }
                    {/* Delete Button */}                    
                    <button
                        onClick={() => handleDeleteTask(task.id)}
                        style={{ marginLeft: '10px', cursor: 'pointer', color: 'red' }}
                        // Disable button if *any* task is currently being edited
                        disabled={editingTaskId !== null}
                    >
                        Delete
                    </button>
                </div>
              </>
            )}
          </li>
        ))}
      </ul>
    </>
  )
}

export default App