import './App.css'
import { useState,useEffect } from 'react'

function App() {
  const [result, setResult] = useState(null)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)

  const testCelery = async () => {
    const res = await fetch('/api/test-celery/')
    const data = await res.json()
    setResult(data)
  }

  async function load() {
    setLoading(true)
    const res = await fetch("/api/integration/books/")
    const json = await res.json()
    setData(json)
    setLoading(false)
  }


  async function create() {
    const res = await fetch("/api/integration/books/create/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: "React Created Book " + Date.now(), // unique title each time
        price: 500,
        author: 1
      })
    })
    const json = await res.json()
    console.log("Created:", json)
    await load()  // ← refresh list after create, cache is invalidated on backend
  }

   // ← auto load on page open
  useEffect(() => {
    const fetchBooks = async () => {
      await load()
    }

    fetchBooks()
  }, [])

  return (
    <>
    <h1>line add during local running </h1>
      <div>
        <button onClick={testCelery}>Test Celery</button>
        {result && <pre>{JSON.stringify(result, null, 2)}</pre>}
      </div>
      <hr />
     
      <div>
        <h1>Redis + Celery Integration Test</h1>
        <button onClick={load} disabled={loading}>
          {loading ? "Loading..." : "Reload Books"}
        </button>
        <button onClick={create}>Create Book</button>
        {data && (
          <>
            <p>Source: <strong>{data.source}</strong></p>
            <pre>{JSON.stringify(data.books, null, 2)}</pre>
          </>
        )}
      </div>
    </>
  )
}

export default App