import { useState, useEffect, FormEvent } from 'react' // Added FormEvent
import axios from 'axios'
import './App.css'

// Define an interface for the Task structure
interface Task {
  id: number;
  title: string;
  description: string | null;
  completed: boolean;
  labels: string | null; // Added labels field
}

function App() {
  // State to hold the list of tasks
  const [tasks, setTasks] = useState<Task[]>([]);
  // State to hold potential loading errors
  const [error, setError] = useState<string | null>(null);
  // State for the new task input field
  const [newTaskTitle, setNewTaskTitle] = useState<string>(""); // Added state for input

  // --- State for Editing Tasks ---
  const [editingTaskId, setEditingTaskId] = useState<number | null>(null);
  const [editedTaskTitle, setEditedTaskTitle] = useState<string>("");

  // API base URL (adjust if your backend runs elsewhere)
  const API_URL = 'http://127.0.0.1:8000/api/tasks';

  // useEffect hook to fetch tasks when the component mounts
  useEffect(() => {
    axios.get<Task[]>(API_URL)
      .then(response => {
        // Sort tasks: incomplete first, then by ID descending (newest first)
        const sortedTasks = response.data.sort((a, b) => {
            if (a.completed === b.completed) {
                return b.id - a.id; // Newest first within the same status
            }
            return a.completed ? 1 : -1; // Incomplete tasks first
        });
        setTasks(sortedTasks);
        setError(null); // Clear any previous errors
      })
      .catch(err => {
        console.error("Error fetching tasks:", err);
        setError("Failed to fetch tasks. Is the backend running?");
        // Handle specific errors if needed (e.g., network error vs. server error)
      });
  }, []); // Empty dependency array means this runs once on mount

  // --- Function to handle adding a new task ---
  const handleAddTask = async (event: FormEvent) => {
    event.preventDefault(); // Prevent page reload on form submit

    if (!newTaskTitle.trim()) {
      setError("Task title cannot be empty.");
      return; // Don't submit if title is empty
    }

    try {
      const response = await axios.post<Task>(API_URL, {
        title: newTaskTitle,
        // description and completed will use backend defaults (false)
      });

      // Add the new task to the state and re-sort
      setTasks(prevTasks => {
          const updatedTasks = [response.data, ...prevTasks];
          // Keep the same sorting logic as in useEffect
          return updatedTasks.sort((a, b) => {
              if (a.completed === b.completed) {
                  return b.id - a.id;
              }
              return a.completed ? 1 : -1;
          });
      });
      setNewTaskTitle(""); // Clear the input field
      setError(null); // Clear any previous errors
    } catch (err) {
      console.error("Error adding task:", err);
      setError("Failed to add task. Please try again.");
      // More specific error handling could be added here
    }
  };

  // --- Function to handle toggling task completion ---
  const handleToggleComplete = async (taskToToggle: Task) => {
    // --- Prevent toggling while editing the same task ---
    if (editingTaskId === taskToToggle.id) {
       return; // Or maybe show a small message
    }

    const updatedTaskData = {
        ...taskToToggle,
        completed: !taskToToggle.completed,
    };

    try {
      await axios.put(`${API_URL}/${taskToToggle.id}`, updatedTaskData);

      // Update the task in the state and re-sort
      setTasks(prevTasks => {
        const updatedTasks = prevTasks.map(task =>
          task.id === taskToToggle.id ? updatedTaskData : task
        );
        // Keep the same sorting logic
        return updatedTasks.sort((a, b) => {
            if (a.completed === b.completed) {
                return b.id - a.id;
            }
            return a.completed ? 1 : -1;
        });
      });
      setError(null); // Clear errors on success
    } catch (err) {
      console.error("Error updating task:", err);
      setError("Failed to update task status. Please try again.");
      // Optionally revert state change here if needed
    }
  };

  // --- Function to handle deleting a task ---
  const handleDeleteTask = async (taskIdToDelete: number) => {
    // Optional: Ask for confirmation before deleting
    // if (!window.confirm("Are you sure you want to delete this task?")) {
    //   return;
    // }

    try {
      await axios.delete(`${API_URL}/${taskIdToDelete}`);

      // Remove the task from the state
      setTasks(prevTasks => prevTasks.filter(task => task.id !== taskIdToDelete));
      setError(null); // Clear errors on success
    } catch (err) {
      console.error("Error deleting task:", err);
      setError("Failed to delete task. Please try again.");
      // No state reversion needed for delete, but error is shown
    }
  };

  // --- Functions for Editing Tasks ---
  const handleEditClick = (task: Task) => {
    setEditingTaskId(task.id);
    setEditedTaskTitle(task.title); // Pre-fill the input
    // Note: We are not editing labels directly in this simplified UI
  };

  const handleCancelEdit = () => {
    setEditingTaskId(null);
    setEditedTaskTitle("");
  };

  const handleSaveEdit = async () => {
    if (editingTaskId === null) return;

    if (!editedTaskTitle.trim()) {
        setError("Task title cannot be empty.");
        return; // Don't save if title is empty
    }

    const originalTask = tasks.find(task => task.id === editingTaskId);
    if (!originalTask) {
        setError("Original task not found for editing."); // Should not happen
        setEditingTaskId(null);
        return;
    }

    // Prepare data for PUT request
    // We send the *potentially* changed title. Backend will decide if labels need regenerating.
    const updatedTaskData = {
        ...originalTask,
        title: editedTaskTitle.trim(),
        // We don't send labels from the frontend during save edit,
        // backend handles regeneration based on title change.
        // If we wanted manual label override, we'd need state for editedLabels.
        labels: originalTask.labels // Send current labels back initially
    };

    try {
      // The PUT request will return the task potentially with *updated* labels from the backend
      const response = await axios.put<Task>(`${API_URL}/${editingTaskId}`, updatedTaskData);
      const taskWithUpdatedLabels = response.data;

      // Update the task in the state (using the response data)
      setTasks(prevTasks => {
        const updatedTasks = prevTasks.map(task =>
          task.id === editingTaskId ? taskWithUpdatedLabels : task // Use task returned from backend
        );
        // Keep the same sorting logic
        return updatedTasks.sort((a, b) => {
            if (a.completed === b.completed) {
                return b.id - a.id;
            }
            return a.completed ? 1 : -1;
        });
      });
      setError(null); // Clear errors on success
      handleCancelEdit(); // Exit edit mode
    } catch (err) {
      console.error("Error updating task:", err);
      setError("Failed to update task. Please try again.");
      // Optionally: Don't exit edit mode on error, let user retry?
    }
  };

  return (
    <>
      <h1>Todo List</h1>
      {error && <p style={{ color: 'red' }}>{error}</p>} {/* Display error message if any */}

      {/* --- Add Task Form --- */}
      <form onSubmit={handleAddTask}>
        <input
          type="text"
          value={newTaskTitle}
          onChange={(e) => setNewTaskTitle(e.target.value)}
          placeholder="Enter new task title"
        />
        <button type="submit">Add Task</button>
      </form>

      {/* --- Task List --- */}
      <ul>
        {tasks.map(task => (
          <li key={task.id} style={{ display: 'flex', alignItems: 'center', marginBottom: '10px', textDecoration: task.completed ? 'line-through' : 'none' }}>
            {editingTaskId === task.id ? (
              // --- Edit Mode --- //
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <input
                  type="text"
                  value={editedTaskTitle}
                  onChange={(e) => setEditedTaskTitle(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSaveEdit()} // Save on Enter
                  autoFocus // Focus the input when it appears
                  style={{ marginRight: '10px' }}
                />
                <button onClick={handleSaveEdit} style={{ marginRight: '5px' }}>Save</button>
                <button onClick={handleCancelEdit}>Cancel</button>
              </div>
            ) : (
              // --- View Mode --- //
              <>
                <input
                  type="checkbox"
                  checked={task.completed}
                  onChange={() => handleToggleComplete(task)}
                  style={{ marginRight: '10px' }}
                  disabled={editingTaskId !== null} // Disable checkbox if any task is being edited
                />
                <span onClick={() => !task.completed && handleEditClick(task)} style={{ cursor: task.completed ? 'default' : 'pointer', marginRight: '10px' }}>
                   {task.title}
                </span>
                {/* Display Labels */}
                {task.labels && (
                    <span style={{ fontSize: '0.8em', color: 'grey', marginLeft: 'auto', marginRight: '10px' }}>
                         [{task.labels}]
                    </span>
                )}
                <div style={{ marginLeft: task.labels ? '0' : 'auto'}}> {/* Adjust margin based on labels presence */} 
                    {/* Edit Button - only show if not completed */}
                    {!task.completed &&
                        <button
                            onClick={() => handleEditClick(task)}
                            style={{ marginLeft: '10px', cursor: 'pointer' }}
                            disabled={editingTaskId !== null} // Disable if any task is being edited
                        >
                            Edit
                        </button>
                    }
                    {/* Delete Button */}
                    <button
                        onClick={() => handleDeleteTask(task.id)}
                        style={{ marginLeft: '10px', cursor: 'pointer', color: 'red' }}
                        disabled={editingTaskId !== null} // Disable if any task is being edited
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