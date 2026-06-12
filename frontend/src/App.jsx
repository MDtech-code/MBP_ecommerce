
import './App.css'
import { useEffect, useState } from "react";
function App() {
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetch("http://localhost:8000/api")
      .then((res) => res.json())
      .then((data) => setMessage(data.message))
      .catch((err) => console.error("Error fetching API:", err));
  }, []);
  return (
    <>
       <div>
      <h1>React Frontend  MD </h1>
      <p>Backend says: {message|| 'no record found '}</p>
    </div>
    </>
  )
}

export default App
