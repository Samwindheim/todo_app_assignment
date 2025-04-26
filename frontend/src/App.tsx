import { useState, useEffect } from 'react'
import axios from 'axios' // Import axios
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

  return (
    <>
      <h1>Todo List</h1>
      {error && <p style={{ color: 'red' }}>{error}</p>} {/* Display error message if any */}
      <ul>
        {tasks.map(task => (
          <li key={task.id}>
            {task.title} {task.completed ? "(Completed)" : ""}
            {/* We'll add buttons for edit/delete/complete later */}
          </li>
        ))}
      </ul>
      {/* We'll add a form to add new tasks later */}
    </>
  )
}

export default App
