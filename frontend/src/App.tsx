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
        setTasks(response.data);
        setError(null); // Clear any previous errors
      })
      .catch(err => {
        console.error("Error fetching tasks:", err);
        setError("Failed to fetch tasks. Is the backend running?");
        // Handle specific errors if needed (e.g., network error vs. server error)
      });
  }, []); // Empty dependency array means this runs once on mount

  // --- Function to handle adding a new task --- // Added this function
  const handleAddTask = async (event: FormEvent) => {
    event.preventDefault(); // Prevent page reload on form submit

    if (!newTaskTitle.trim()) {
      setError("Task title cannot be empty.");
      return; // Don't submit if title is empty
    }

    try {
      const response = await axios.post<Task>(API_URL, {
        title: newTaskTitle,
        // description and completed will use backend defaults
      });

      // Add the new task to the beginning of the list in the state
      setTasks(prevTasks => [response.data, ...prevTasks]);
      setNewTaskTitle(""); // Clear the input field
      setError(null); // Clear any previous errors
    } catch (err) {
      console.error("Error adding task:", err);
      setError("Failed to add task. Please try again.");
      // More specific error handling could be added here
    }
  };

  return (
    <>
      <h1>Todo List</h1>
      {error && <p style={{ color: 'red' }}>{error}</p>} {/* Display error message if any */}

      {/* --- Add Task Form --- */} {/* Added this form */}
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
          <li key={task.id}>
            {task.title} {task.completed ? "(Completed)" : ""}
            {/* We'll add buttons for edit/delete/complete later */}
          </li>
        ))}
      </ul>
    </>
  )
}

export default App