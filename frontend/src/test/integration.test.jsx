// import { describe, it, expect, vi, beforeEach } from 'vitest'
// import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
// import App from '../App'

// // ✅ Mock axios client used inside useApi
// vi.mock('../api/client', () => {
//   return {
//     api: {
//       get: vi.fn(),
//       post: vi.fn(),
//       put: vi.fn(),
//       delete: vi.fn(),
//     }
//   }
// })

// import { api } from '../api/client'

// // ─────────────────────────────────────────────
// // Helpers
// // ─────────────────────────────────────────────

// function mockGetResponse(data) {
//   api.get.mockResolvedValueOnce({ data })
// }

// function mockPostResponse(data) {
//   api.post.mockResolvedValueOnce({ data })
// }

// function buildPaginatedResponse(data = [], source = 'database') {
//   return {
//     data,
//     meta: {
//       page: 1,
//       total_pages: 1,
//       total_items: data.length,
//       source
//     }
//   }
// }

// function mockInitialLoad(booksData = buildPaginatedResponse()) {
//   mockGetResponse(booksData)                 // getBooks
//   mockGetResponse(buildPaginatedResponse()) // getAuthors
//   mockGetResponse(buildPaginatedResponse()) // getLogs
// }

// // ─────────────────────────────────────────────
// // Tests
// // ─────────────────────────────────────────────

// describe('Integration App', () => {

//   beforeEach(() => {
//     vi.clearAllMocks()
//   })

//   it('renders navbar heading', async () => {
//     mockInitialLoad()

//     await act(async () => {
//       render(<App />)
//     })

//     expect(
//       screen.getByText('🔧 Integration Test Dashboard')
//     ).toBeInTheDocument()
//   })

//   it('shows books tab by default', async () => {
//     mockInitialLoad()

//     await act(async () => {
//       render(<App />)
//     })

//     expect(
//       screen.getByRole('button', { name: 'books' })
//     ).toHaveClass('active')
//   })

//   it('displays books from API response', async () => {
//     mockInitialLoad(
//       buildPaginatedResponse([
//         {
//           id: 1,
//           title: 'Test Book',
//           price: '100.00',
//           author_name: 'Test Author'
//         }
//       ])
//     )

//     await act(async () => {
//       render(<App />)
//     })

//     await waitFor(() => {
//       expect(screen.getByText('Test Book')).toBeInTheDocument()
//     })
//   })

//   it('shows database source badge on first load', async () => {
//     mockInitialLoad(
//       buildPaginatedResponse([], 'database')
//     )

//     await act(async () => {
//       render(<App />)
//     })

//     await waitFor(() => {
//       expect(screen.getByText('🗄️ Database')).toBeInTheDocument()
//     })
//   })

//   it('shows redis source badge on cached response', async () => {
//     mockInitialLoad(
//       buildPaginatedResponse([], 'l2_redis')
//     )

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

//     mockGetResponse({ task_id: 'abc-123', status: 'queued' })

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
