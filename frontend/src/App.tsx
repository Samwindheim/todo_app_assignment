import { useState, useEffect, FormEvent } from 'react' // Added FormEvent
import axios from 'axios'
import './App.css'

// Define an interface for the Task structure
interface Task {
  id: number;
  title: string;
  description: string | null;
  completed: boolean;
}

function App() {
  // State to hold the list of tasks
  const [tasks, setTasks] = useState<Task[]>([]);
  // State to hold potential loading errors
  const [error, setError] = useState<string | null>(null);
  // State for the new task input field
  const [newTaskTitle, setNewTaskTitle] = useState<string>(""); // Added state for input

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
          <li key={task.id} style={{ textDecoration: task.completed ? 'line-through' : 'none' }}>
             <input
                type="checkbox"
                checked={task.completed}
                onChange={() => handleToggleComplete(task)}
                style={{ marginRight: '10px' }} // Add some spacing
             />
            {task.title}
            {/* Add Delete Button */}
            <button
                onClick={() => handleDeleteTask(task.id)}
                style={{ marginLeft: '10px', cursor: 'pointer', color: 'red' }} // Basic styling
            >
                Delete
            </button>
            {/* We'll add buttons for edit later */}
          </li>
        ))}
      </ul>
    </>
  )
}

export default App