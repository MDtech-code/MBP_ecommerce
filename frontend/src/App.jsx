/* eslint-disable react-hooks/exhaustive-deps */

import { useState,useEffect} from 'react'
import './App.css'

const API = {
  testCelery: () => fetch('/api/test-celery/').then(r => r.json()),
  getBooks: () => fetch('/api/integration/books/').then(r => r.json()),
  getAuthors: () => fetch('/api/integration/authors/').then(r => r.json()),
  getLogs: () => fetch('/api/integration/logs/').then(r => r.json()),
  getHealth: () => fetch('/api/integration/health/').then(r => r.json()),
  createBook: (data) => fetch('/api/integration/books/create/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }).then(r => r.json()),
}

function Badge({ text, variant = 'primary' }) {
  return (
    <span className={`badge bg-${variant} me-1`}>{text}</span>
  )
}

function Card({ title, children, className = '' }) {
  return (
    <div className={`card shadow-sm mb-4 ${className}`}>
      <div className="card-header fw-bold">{title}</div>
      <div className="card-body">{children}</div>
    </div>
  )
}

function SourceBadge({ source }) {
  const config = {
    l1_memory: { color: 'bg-warning text-dark', icon: '⚡⚡', label: 'L1 Memory' },
    l2_redis:  { color: 'bg-success', icon: '⚡', label: 'L2 Redis' },
    database:  { color: 'bg-primary', icon: '🗄️', label: 'Database' },
  }
  const s = config[source] || config.database
  return (
    <span className={`badge ${s.color}`}>
      {s.icon} {s.label}
    </span>
  )
}

export default function App() {
  const [books, setBooks] = useState(null)
  const [authors, setAuthors] = useState(null)
  const [logs, setLogs] = useState(null)
  const [health, setHealth] = useState(null)
  const [celery, setCelery] = useState(null)
  const [loading, setLoading] = useState({})
  const [newBook, setNewBook] = useState({ title: '', price: '', author: '' })
  const [activeTab, setActiveTab] = useState('books')

  const setLoad = (key, val) => setLoading(p => ({ ...p, [key]: val }))

  async function loadBooks() {
    setLoad('books', true)
    const data = await API.getBooks()
    setBooks(data)
    setLoad('books', false)
  }

  async function loadAuthors() {
    setLoad('authors', true)
    const data = await API.getAuthors()
    setAuthors(data)
    setLoad('authors', false)
  }

  async function loadLogs() {
    setLoad('logs', true)
    const data = await API.getLogs()
    setLogs(data)
    setLoad('logs', false)
  }

  async function loadHealth() {
    setLoad('health', true)
    const data = await API.getHealth()
    setHealth(data)
    setLoad('health', false)
  }

  async function testCelery() {
    setLoad('celery', true)
    const data = await API.testCelery()
    setCelery(data)
    setLoad('celery', false)
  }

  async function handleCreate(e) {
    e.preventDefault()
    await API.createBook({
      title: newBook.title,
      price: parseFloat(newBook.price),
      author: parseInt(newBook.author)
    })
    setNewBook({ title: '', price: '', author: '' })
    await loadBooks()
    await loadLogs()
  }
console.log('authors:', authors)
console.log('logs:', logs)


// function handleTabClick(tab) {
//   setActiveTab(tab)
//   if (tab === 'authors') loadAuthors()
//   if (tab === 'logs') loadLogs()
//   if (tab === 'health') return
//   if (tab === 'celery') return
// }
function handleTabClick(tab) {
  setActiveTab(tab)
  if (tab === 'books') loadBooks()
  if (tab === 'authors') loadAuthors()
  if (tab === 'logs') loadLogs()
  if (tab === 'health') loadHealth()
}

 // auto load on mount
  useEffect(() => {
    loadBooks()
    loadAuthors()
    loadLogs()
  }, [])


  const tabs = ['books', 'authors', 'logs', 'health', 'celery','sentry']

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navbar — Bootstrap */}
      <nav className="navbar navbar-dark bg-dark px-4 mb-6">
        <span className="navbar-brand fw-bold">
          🔧 Integration Test Dashboard
        </span>
        <span className="text-secondary small">
          Django + DRF + Redis + Celery
        </span>
      </nav>

      <div className="container-fluid px-4">

        {/* Status Bar — Tailwind */}
        <div className="flex gap-3 mb-6 flex-wrap">
          {[
            { label: 'Django', color: 'bg-green-500' },
            { label: 'PostgreSQL', color: 'bg-blue-500' },
            { label: 'Redis', color: books ? 'bg-green-500' : 'bg-gray-400' },
            { label: 'Celery', color: celery ? 'bg-green-500' : 'bg-gray-400' },
          ].map(s => (
            <div key={s.label} className="flex items-center gap-2 bg-white rounded-full px-3 py-1 shadow-sm text-sm">
              <span className={`w-2 h-2 rounded-full ${s.color}`}></span>
              {s.label}
            </div>
          ))}
        </div>

        {/* Tabs — Bootstrap */}
        <ul className="nav nav-tabs mb-4">
          {tabs.map(tab => (
            <li className="nav-item" key={tab}>
              <button
                className={`nav-link text-capitalize ${activeTab === tab ? 'active' : ''}`}
                onClick={() => handleTabClick(tab)}
              >
                {tab}
              </button>
            </li>
          ))}
        </ul>

        {/* Books Tab */}
        {activeTab === 'books' && (
          <div className="row">
            <div className="col-md-8">
              <Card title={
                <div className="flex justify-between items-center">
                  <span>📚 Books</span>
                  {books && <SourceBadge source={books.source} />}
                </div>
              }>
                <button
                  className="btn btn-sm btn-outline-primary mb-3"
                  onClick={loadBooks}
                  disabled={loading.books}
                >
                  {loading.books ? 'Loading...' : '🔄 Reload'}
                </button>

                {books?.books?.length === 0 && (
                  <p className="text-muted">No books yet.</p>
                )}

                <div className="flex flex-col gap-2">
                  {books?.books?.map(book => (
                    <div key={book.id}
                      className="flex justify-between items-center bg-gray-50 rounded-lg px-3 py-2 border">
                      <div>
                        <div className="fw-semibold">{book.title}</div>
                        <small className="text-muted">by {book.author_name}</small>
                      </div>
                      <Badge text={`Rs. ${book.price}`} variant="success" />
                    </div>
                  ))}
                </div>
              </Card>
            </div>

            <div className="col-md-4">
              <Card title="➕ Create Book">
                {/* Pure CSS form */}
                <form onSubmit={handleCreate} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div>
                    <label className="form-label small fw-semibold">Title</label>
                    <input
                      className="form-control form-control-sm"
                      placeholder="Book title"
                      value={newBook.title}
                      onChange={e => setNewBook(p => ({ ...p, title: e.target.value }))}
                      required
                    />
                  </div>
                  <div>
                    <label className="form-label small fw-semibold">Price</label>
                    <input
                      className="form-control form-control-sm"
                      type="number"
                      placeholder="0.00"
                      value={newBook.price}
                      onChange={e => setNewBook(p => ({ ...p, price: e.target.value }))}
                      required
                    />
                  </div>
                  <div>
                    <label className="form-label small fw-semibold">Author ID</label>
                    <input
                      className="form-control form-control-sm"
                      type="number"
                      placeholder="Author ID"
                      value={newBook.author}
                      onChange={e => setNewBook(p => ({ ...p, author: e.target.value }))}
                      required
                    />
                  </div>
                  <button type="submit" className="btn btn-primary btn-sm w-100">
                    Create Book
                  </button>
                </form>
              </Card>
            </div>
          </div>
        )}

        {/* Authors Tab */}
        {activeTab === 'authors' && (
          <Card title="👤 Authors">
            <button
              className="btn btn-sm btn-outline-primary mb-3"
              onClick={loadAuthors}
              disabled={loading.authors}
            >
              {loading.authors ? 'Loading...' : '🔄 Reload'}
            </button>
            <div className="row g-3">
              {authors?.data?.map(author => (
                <div key={author.id} className="col-md-4">
                  <div className="bg-white rounded-xl shadow-sm p-4 border">
                    <div className="fw-bold text-lg">{author.name}</div>
                    <div className="text-muted small mb-2">{author.email}</div>
                    <Badge text={`${author.total_books} books`} variant="info" />
                    <div className="mt-2 flex flex-col gap-1">
                      {author.books?.map(b => (
                        <div key={b.id} className="text-sm text-gray-600">
                          • {b.title}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Logs Tab */}
        {activeTab === 'logs' && (
          <Card title="📋 Activity Logs">
            <button
              className="btn btn-sm btn-outline-secondary mb-3"
              onClick={loadLogs}
              disabled={loading.logs}
            >
              {loading.logs ? 'Loading...' : '🔄 Load Logs'}
            </button>
            <div style={{ fontFamily: 'monospace', fontSize: '13px' }}
              className="flex flex-col gap-1">
              {logs?.data?.map(log => (
                <div key={log.id}
                  className="bg-gray-900 text-green-400 rounded px-3 py-1">
                  <span className="text-gray-500 mr-2">{log.created_at}</span>
                  {log.message}
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Health Tab */}
        {activeTab === 'health' && (
          <Card title="❤️ System Health">
            <button
              className="btn btn-success mb-3"
              onClick={loadHealth}
              disabled={loading.health}
            >
              {loading.health ? 'Checking...' : '🩺 Run Health Check'}
            </button>
            {health && (
              <div className="flex flex-col gap-3">
                <div className="flex gap-3 flex-wrap">
                  {Object.entries(health.data || health).map(([key, val]) => (
                    <div key={key}
                      className="bg-white border rounded-lg px-4 py-3 shadow-sm text-center min-w-32">
                      <div className="text-xs text-gray-500 uppercase tracking-wide">{key}</div>
                      <div className="fw-semibold text-green-600 text-sm mt-1">
                        {typeof val === 'string' ? val : '✓'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Card>

        )}

        {/* Celery Tab */}
        {activeTab === 'celery' && (
          <Card title="⚙️ Celery Task Test">
            <button
              className="btn btn-warning mb-3"
              onClick={testCelery}
              disabled={loading.celery}
            >
              {loading.celery ? 'Dispatching...' : '🚀 Fire Celery Task'}
            </button>
            {celery && (
              <div className="bg-gray-900 text-yellow-300 rounded-lg p-4"
                style={{ fontFamily: 'monospace' }}>
                <div>Task ID: <span className="text-white">{celery.task_id}</span></div>
                <div>Status: <span className="text-green-400">{celery.status}</span></div>
              </div>
            )}
          </Card>

        )}
        {/* sentry Tab */}
        {activeTab === 'sentry' && (
  <Card title="🚨 Sentry Error Monitoring">
    <p className="text-muted mb-3">
      Click the button to trigger a test error. 
      Check your Sentry dashboard to confirm it's captured.
    </p>
    <button
      className="btn btn-danger"
      onClick={async () => {
        try {
          await fetch('/api/integration/sentry-test/')
        } catch(e) {
          console.log(e)
        }
        alert('Error triggered — check Sentry dashboard!')
      }}
    >
      🔥 Trigger Test Error
    </button>
  </Card>
)}


      </div>
    </div>
  )
}

// import './App.css'
// import { useState,useEffect } from 'react'

// function App() {
//   const [result, setResult] = useState(null)
//   const [data, setData] = useState(null)
//   const [loading, setLoading] = useState(false)

//   const testCelery = async () => {
//     const res = await fetch('/api/test-celery/')
//     const data = await res.json()
//     setResult(data)
//   }

//   async function load() {
//     setLoading(true)
//     const res = await fetch("/api/integration/books/")
//     const json = await res.json()
//     setData(json)
//     setLoading(false)
//   }


//   async function create() {
//     const res = await fetch("/api/integration/books/create/", {
//       method: "POST",
//       headers: { "Content-Type": "application/json" },
//       body: JSON.stringify({
//         title: "React Created Book " + Date.now(), // unique title each time
//         price: 500,
//         author: 1
//       })
//     })
//     const json = await res.json()
//     console.log("Created:", json)
//     await load()  // ← refresh list after create, cache is invalidated on backend
//   }

//    // ← auto load on page open
//   useEffect(() => {
//     const fetchBooks = async () => {
//       await load()
//     }

//     fetchBooks()
//   }, [])

//   return (
//     <>
//     <h1>line add during local running </h1>
//       <div>
//         <button onClick={testCelery}>Test Celery</button>
//         {result && <pre>{JSON.stringify(result, null, 2)}</pre>}
//       </div>
//       <hr />
     
//       <div>
//         <h1>Redis + Celery Integration Test</h1>
//         <button onClick={load} disabled={loading}>
//           {loading ? "Loading..." : "Reload Books"}
//         </button>
//         <button onClick={create}>Create Book</button>
//         {data && (
//           <>
//             <p>Source: <strong>{data.source}</strong></p>
//             <pre>{JSON.stringify(data.books, null, 2)}</pre>
//           </>
//         )}
//       </div>
//     </>
//   )
// }

// export default App