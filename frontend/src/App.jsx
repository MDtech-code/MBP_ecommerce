
import { useState, useEffect } from 'react'
import { useApi } from './hooks/useApi'

import Badge  from '../components/Badge'
import Card from '../components/Card'
import SourceBadge from '../components/SourceBadge'
import PaginationControls from '../components/PaginationControls'









// ─── Main App ─────────────────────────────────────────

export default function App() {
  const { get, post } = useApi()
  const [books, setBooks] = useState(null)
  const [authors, setAuthors] = useState(null)
  const [logs, setLogs] = useState(null)
  const [health, setHealth] = useState(null)
  const [celery, setCelery] = useState(null)
  const [loading, setLoading] = useState({})
  const [newBook, setNewBook] = useState({ title: '', price: '', author: '' })
  const [activeTab, setActiveTab] = useState('books')
  const [createError, setCreateError] = useState(null)

  // pagination state per tab
  const [booksPage, setBooksPage] = useState(1)
  const [authorsPage, setAuthorsPage] = useState(1)
  const [logsPage, setLogsPage] = useState(1)

  const setLoad = (key, val) => setLoading(p => ({ ...p, [key]: val }))

  async function loadBooks(page = booksPage) {
    setLoad('books', true)
    const data = await get(`/api/integration/books/?page=${page}&page_size=10`)
    setBooks(data)
    setBooksPage(page)
    setLoad('books', false)
  }

  async function loadAuthors(page = authorsPage) {
    setLoad('authors', true)
    const data = await get(`/api/integration/authors/?page=${page}&page_size=10`)
    setAuthors(data)
    setAuthorsPage(page)
    setLoad('authors', false)
  }

  async function loadLogs(page = logsPage) {
    setLoad('logs', true)
    const data = await get(`/api/integration/logs/?page=${page}&page_size=20`)
    setLogs(data)
    setLogsPage(page)
    setLoad('logs', false)
  }

  async function loadHealth() {
    setLoad('health', true)
    const data = await get('/api/integration/health/')
    setHealth(data)
    setLoad('health', false)
  }

  async function testCelery() {
    setLoad('celery', true)
    const data = await get('/api/integration/test-celery/')
    setCelery(data)
    setLoad('celery', false)
  }
  
  async function triggerSentryError() {
  try {
    await get('/api/integration/sentry-test/')
  } catch (e) {
    console.log(e)
  }
  alert('Error triggered — check Sentry dashboard!')
}

  async function handleCreate(e) {
    e.preventDefault()
    setCreateError(null)
    const res = await post('/api/integration/books/create/', {
      title: newBook.title,
      price: parseFloat(newBook.price),
      author: parseInt(newBook.author)
    })
    if (!res.success) {
      setCreateError(res.errors)
      return
    }
    setNewBook({ title: '', price: '', author: '' })
    await loadBooks(1)   // reset to page 1 after create
    await loadLogs(1)
  }

  function handleTabClick(tab) {
    setActiveTab(tab)
    if (tab === 'books') loadBooks(1)
    if (tab === 'authors') loadAuthors(1)
    if (tab === 'logs') loadLogs(1)
    if (tab === 'health') loadHealth()
  }

  useEffect(() => {
    loadBooks(1)
    loadAuthors(1)
    loadLogs(1)
  }, [])

  const tabs = ['books', 'authors', 'logs', 'health', 'celery', 'sentry']

  return (
    <>
    
    <div className="min-h-screen bg-gray-50">

      {/* Navbar */}
      <nav className="navbar navbar-dark bg-dark px-4 mb-4">
        <span className="navbar-brand fw-bold">🔧 Integration Test Dashboard</span>
        <span className="text-secondary small">Django + DRF + Redis + Celery</span>
      </nav>

      <div className="container-fluid px-4">

        {/* Status Bar */}
        <div className="flex gap-3 mb-4 flex-wrap">
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

        {/* Tabs */}
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

        {/* ─── Books Tab ─── */}
        {activeTab === 'books' && (
          <div className="row">
            <div className="col-md-8">
              <Card title={
                <div className="flex justify-between items-center">
                  <span>📚 Books</span>
                  {books?.meta && <SourceBadge source={books.meta.source} />}
                </div>
              }>
                <button
                  className="btn btn-sm btn-outline-primary mb-3 w-fit inline-flex"
                  onClick={() => loadBooks(booksPage)}
                  disabled={loading.books}
                >
                  {loading.books ? 'Loading...' : '🔄 Reload'}
                </button>

                {books?.data?.length === 0 && (
                  <p className="text-muted">No books yet.</p>
                )}

                <div className="flex flex-col gap-2">
                  {books?.data?.map(book => (
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

                <PaginationControls
                  meta={books?.meta}
                  onPageChange={(page) => loadBooks(page)}
                />
              </Card>
            </div>

            <div className="col-md-4">
              <Card title="➕ Create Book">
                {createError && (
                  <div className="alert alert-danger py-2 small mb-3">
                    {typeof createError === 'object'
                      ? Object.entries(createError).map(([k, v]) => (
                        <div key={k}><strong>{k}:</strong> {v}</div>
                      ))
                      : createError
                    }
                  </div>
                )}
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

        {/* ─── Authors Tab ─── */}
        {activeTab === 'authors' && (
          <Card title={
            <div className="flex justify-between items-center">
              <span>👤 Authors</span>
              {authors?.meta && <SourceBadge source={authors.meta.source} />}
            </div>
          }>
            <button
              className="btn btn-sm btn-outline-primary mb-3 w-fit inline-flex"
              onClick={() => loadAuthors(authorsPage)}
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
                        <div key={b.id} className="text-sm text-gray-600">• {b.title}</div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <PaginationControls
              meta={authors?.meta}
              onPageChange={(page) => loadAuthors(page)}
            />
          </Card>
        )}

        {/* ─── Logs Tab ─── */}
        {activeTab === 'logs' && (
          <Card title={
            <div className="flex justify-between items-center">
              <span>📋 Activity Logs</span>
              {logs?.meta && <SourceBadge source={logs.meta.source} />}
            </div>
          }>
            <button
              className="btn btn-sm btn-outline-secondary mb-3 w-fit inline-flex"
              onClick={() => loadLogs(logsPage)}
              disabled={loading.logs}
            >
              {loading.logs ? 'Loading...' : '🔄 Reload'}
            </button>

            <div style={{ fontFamily: 'monospace', fontSize: '13px' }} className="flex flex-col gap-1">
              {logs?.data?.map(log => (
                <div key={log.id} className="bg-gray-900 text-green-400 rounded px-3 py-1">
                  <span className="text-gray-500 mr-2">{log.created_at}</span>
                  {log.message}
                </div>
              ))}
            </div>

            <PaginationControls
              meta={logs?.meta}
              onPageChange={(page) => loadLogs(page)}
            />
          </Card>
        )}

        {/* ─── Health Tab ─── */}
        {activeTab === 'health' && (
          <Card title="❤️ System Health">
            <button
              className="btn btn-success mb-3 w-fit inline-flex"
              onClick={loadHealth}
              disabled={loading.health}
            >
              {loading.health ? 'Checking...' : '🩺 Run Health Check'}
            </button>

            {health && (
              <div className="flex flex-col gap-3">
                {health.meta && (
                  <div className="mb-2">
                    <SourceBadge source={health.meta.source} />
                  </div>
                )}
                <div className="flex gap-3 flex-wrap">
                  {Object.entries(health.data || {}).map(([key, val]) => (
                    <div key={key}
                      className="bg-white border rounded-lg px-4 py-3 shadow-sm text-center"
                      style={{ minWidth: '120px' }}>
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

        {/* ─── Celery Tab ─── */}
        {activeTab === 'celery' && (
          <Card title="⚙️ Celery Task Test">
            <button
              className="btn btn-warning mb-3 w-fit inline-flex"
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

        {/* ─── Sentry Tab ─── */}
        {activeTab === 'sentry' && (
          <Card title="🚨 Sentry Error Monitoring">
            <p className="text-muted mb-3">
              Click to trigger a test error and verify Sentry captures it.
            </p>
            <button
              className="btn btn-danger w-fit inline-flex"
              onClick={triggerSentryError}
            >
              🔥 Trigger Test Error
            </button>
          </Card>
        )}

      </div>
    </div>
    </>
  )
}
