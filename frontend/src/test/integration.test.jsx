// import { describe, it, expect, vi, beforeEach } from 'vitest'
// import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
// import App from '../App'

// const mockFetch = vi.fn()
// global.fetch = mockFetch

// function mockResponse(data) {
//   mockFetch.mockResolvedValueOnce({
//     json: async () => data
//   })
// }

// // mock all initial load calls — books + authors + logs
// function mockInitialLoad(booksData = { source: 'database', books: [] }) {
//   mockResponse(booksData)                              // getBooks
//   mockResponse({ data: [], pagination: {} })           // getAuthors
//   mockResponse({ data: [], pagination: {} })           // getLogs
// }

// describe('Integration App', () => {

//   beforeEach(() => {
//     mockFetch.mockClear()
//   })

//   it('renders navbar heading', async () => {
//     mockInitialLoad()
//     await act(async () => {
//       render(<App />)
//     })
//     expect(screen.getByText('🔧 Integration Test Dashboard')).toBeInTheDocument()
//   })

//   it('shows books tab by default', async () => {
//     mockInitialLoad()
//     await act(async () => {
//       render(<App />)
//     })
//     expect(screen.getByRole('button', { name: 'books' })).toHaveClass('active')
//   })

//   it('displays books from API response', async () => {
//     mockInitialLoad({
//       source: 'database',
//       books: [
//         { id: 1, title: 'Test Book', price: '100.00', author_name: 'Test Author' }
//       ]
//     })
//     await act(async () => {
//       render(<App />)
//     })
//     await waitFor(() => {
//       expect(screen.getByText('Test Book')).toBeInTheDocument()
//     })
//   })

//   it('shows database source badge on first load', async () => {
//     mockInitialLoad({ source: 'database', books: [] })
//     await act(async () => {
//       render(<App />)
//     })
//     await waitFor(() => {
//       expect(screen.getByText('🗄️ Database')).toBeInTheDocument()
//     })
//   })

//   it('shows redis source badge on cached response', async () => {
//     mockInitialLoad({ source: 'l2_redis', books: [] })
//     await act(async () => {
//       render(<App />)
//     })
//     await waitFor(() => {
//       expect(screen.getByText('⚡ L2 Redis')).toBeInTheDocument()
//     })
//   })

//   it('fires celery task on button click', async () => {
//     mockInitialLoad()
//     await act(async () => {
//       render(<App />)
//     })

//     fireEvent.click(screen.getByRole('button', { name: 'celery' }))
//     mockResponse({ task_id: 'abc-123', status: 'queued' })

//     await act(async () => {
//       fireEvent.click(screen.getByText('🚀 Fire Celery Task'))
//     })

//     await waitFor(() => {
//       expect(screen.getByText('abc-123')).toBeInTheDocument()
//     })
//   })

//   it('create book form has required fields', async () => {
//     mockInitialLoad()
//     await act(async () => {
//       render(<App />)
//     })
//     expect(screen.getByPlaceholderText('Book title')).toBeInTheDocument()
//     expect(screen.getByPlaceholderText('0.00')).toBeInTheDocument()
//     expect(screen.getByPlaceholderText('Author ID')).toBeInTheDocument()
//   })

// })
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import App from '../App'

// ─────────────────────────────────────────────
// Global Fetch Mock
// ─────────────────────────────────────────────

const mockFetch = vi.fn()
global.fetch = mockFetch

function mockResponse(data) {
  mockFetch.mockResolvedValueOnce({
    json: async () => data
  })
}

// helper to build paginated API response
function buildPaginatedResponse(data = [], source = 'database') {
  return {
    data,
    meta: {
      page: 1,
      total_pages: 1,
      total_items: data.length,
      source
    }
  }
}

// mock initial load calls — books + authors + logs
function mockInitialLoad(booksData = buildPaginatedResponse()) {
  mockResponse(booksData)                        // getBooks
  mockResponse(buildPaginatedResponse())        // getAuthors
  mockResponse(buildPaginatedResponse())        // getLogs
}

// ─────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────

describe('Integration App', () => {

  beforeEach(() => {
    mockFetch.mockClear()
  })

  it('renders navbar heading', async () => {
    mockInitialLoad()

    await act(async () => {
      render(<App />)
    })

    expect(
      screen.getByText('🔧 Integration Test Dashboard')
    ).toBeInTheDocument()
  })

  it('shows books tab by default', async () => {
    mockInitialLoad()

    await act(async () => {
      render(<App />)
    })

    expect(
      screen.getByRole('button', { name: 'books' })
    ).toHaveClass('active')
  })

  it('displays books from API response', async () => {
    mockInitialLoad(
      buildPaginatedResponse([
        {
          id: 1,
          title: 'Test Book',
          price: '100.00',
          author_name: 'Test Author'
        }
      ])
    )

    await act(async () => {
      render(<App />)
    })

    await waitFor(() => {
      expect(screen.getByText('Test Book')).toBeInTheDocument()
    })
  })

  it('shows database source badge on first load', async () => {
    mockInitialLoad(
      buildPaginatedResponse([], 'database')
    )

    await act(async () => {
      render(<App />)
    })

    await waitFor(() => {
      expect(screen.getByText('🗄️ Database')).toBeInTheDocument()
    })
  })

  it('shows redis source badge on cached response', async () => {
    mockInitialLoad(
      buildPaginatedResponse([], 'l2_redis')
    )

    await act(async () => {
      render(<App />)
    })

    await waitFor(() => {
      expect(screen.getByText('⚡ L2 Redis')).toBeInTheDocument()
    })
  })

  it('fires celery task on button click', async () => {
    mockInitialLoad()

    await act(async () => {
      render(<App />)
    })

    // switch to celery tab
    fireEvent.click(screen.getByRole('button', { name: 'celery' }))

    // mock celery API BEFORE clicking trigger
    mockResponse({ task_id: 'abc-123', status: 'queued' })

    await act(async () => {
      fireEvent.click(screen.getByText('🚀 Fire Celery Task'))
    })

    await waitFor(() => {
      expect(screen.getByText('abc-123')).toBeInTheDocument()
    })
  })

  it('create book form has required fields', async () => {
    mockInitialLoad()

    await act(async () => {
      render(<App />)
    })

    expect(screen.getByPlaceholderText('Book title')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('0.00')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Author ID')).toBeInTheDocument()
  })

})