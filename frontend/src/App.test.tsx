import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

const dashboard = {
  child_id: 'child-1',
  child_name: 'Kid',
  greeting: 'Good Morning! 👋',
  date: '2026-08-22',
  points_balance: 1250,
  piggy_bank_balance: '84.00',
  xoxo_balance: 7,
  piggy_bank_interest_rate: '4.00',
  point_activity: [
    { id: 'points-2', amount: -10, reason: 'Did not do it the first time listening', created_at: '2026-08-22T16:30:00Z' },
    { id: 'points-1', amount: 25, reason: 'Helped clean garage', created_at: '2026-08-21T16:30:00Z' },
  ],
  chores: [
    { id: 'chore-1', name: 'Make Bed', emoji: '🛏️', points: 10, money_reward: '0.25', xoxo_reward: 1, recurrence_type: 'daily', recurrence_days: null, day_part: 'morning', active: true, completed: false, skip_status: null },
  ],
  completed_count: 0,
  total_count: 1,
  rewards: [
    { id: 'reward-1', name: 'Ice cream', emoji: '🍦', points_cost: 150, active: true },
  ],
  savings_goal: { id: 'goal-1', name: 'LEGO Set', emoji: '🧱', target_amount: '120.00', current_amount: '84.00', progress_percent: 70 },
  streak_days: 6,
  pending_reward_count: 0,
}

const week = {
  start_date: '2026-08-16',
  end_date: '2026-08-22',
  days: [
    { date: '2026-08-16', completed_count: 1, total_count: 1, future: false },
    { date: '2026-08-17', completed_count: 1, total_count: 1, future: false },
    { date: '2026-08-18', completed_count: 0, total_count: 1, future: false },
    { date: '2026-08-19', completed_count: 0, total_count: 1, future: false },
    { date: '2026-08-20', completed_count: 0, total_count: 1, future: false },
    { date: '2026-08-21', completed_count: 0, total_count: 1, future: false },
    { date: '2026-08-22', completed_count: 0, total_count: 1, future: false },
  ],
}

const weather = [
  { key: 'home', name: 'Home', location: 'New York, New York', temperature: 77, high: 84, low: 61, weather_code: 1, label: 'Mostly clear', emoji: '🌤️' },
  { key: 'school', name: 'School', location: 'Brooklyn, New York', temperature: 74, high: 81, low: 59, weather_code: 2, label: 'Partly cloudy', emoji: '⛅' },
]

describe('Kids Chores app', () => {
  afterEach(cleanup)

  beforeEach(() => {
    window.history.replaceState({}, '', '/')
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input)
      if (path.endsWith('/dashboard')) {
        return new Response(JSON.stringify(dashboard), { status: 200, headers: { 'Content-Type': 'application/json' } })
      }
      if (path.endsWith('/weather')) return new Response(JSON.stringify(weather), { status: 200, headers: { 'Content-Type': 'application/json' } })
      if (path.includes('/weeks/')) return new Response(JSON.stringify(week), { status: 200, headers: { 'Content-Type': 'application/json' } })
      if (path.endsWith('/chores/chore-1/skip-requests')) return new Response(JSON.stringify({ id: 'skip-1', status: 'pending' }), { status: 201, headers: { 'Content-Type': 'application/json' } })
      if (path.includes('/complete')) {
        return new Response(JSON.stringify({ message: 'Great job! +10 ⭐', points_balance: 1260 }), { status: 200, headers: { 'Content-Type': 'application/json' } })
      }
      throw new Error(`Unexpected request: ${path}`)
    }))
  })

  it('renders the tablet kid dashboard with core information', async () => {
    render(<App />)

    expect(await screen.findByRole('heading', { name: 'Good Morning! 👋' })).toBeInTheDocument()
    expect(screen.getByText('$84.00')).toBeInTheDocument()
    expect(screen.getByText('1,250')).toBeInTheDocument()
    expect(screen.getByText('7')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Make Bed' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 3, name: /Morning/ })).toBeInTheDocument()
    expect(screen.getByText('+10 ⭐ · +$0.25 · +1 🤗')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'LEGO Set' })).toBeInTheDocument()
    expect(screen.getByText('6 days')).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: /Sunday, August 16, 2026: All done/ })).toBeInTheDocument()
    expect(await screen.findByText('Home')).toBeInTheDocument()
    expect(screen.getByText('School')).toBeInTheDocument()
    expect(await screen.findByRole('article', { name: 'Home weather' })).toHaveTextContent('77°')
    expect(screen.getByRole('article', { name: 'School weather' })).toHaveTextContent('74°')
    expect(screen.getByLabelText('Joke of the day')).toHaveTextContent(/Joke of the day/)
    expect(screen.getByLabelText('Weekly recap')).toHaveTextContent(/2\s*chores done/)
    expect(screen.getByLabelText('Points activity')).toHaveTextContent('-10Did not do it the first time listening')
    expect(screen.getByLabelText('Points activity')).toHaveTextContent('+25Helped clean garage')
  })

  it('completes a chore and shows positive feedback', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(await screen.findByRole('button', { name: 'Mark Make Bed done' }))

    expect(await screen.findByRole('status')).toHaveTextContent('Great job! +10 ⭐')
    await waitFor(() => expect(fetch).toHaveBeenCalledWith('/api/chores/chore-1/complete', expect.objectContaining({ method: 'POST' })))
  })

  it('lets a kid request parent approval to skip a chore', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(await screen.findByRole('button', { name: 'Request to skip Make Bed' }))

    expect(await screen.findByRole('status')).toHaveTextContent('Make Bed skip request sent to your parent.')
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(
      '/api/chores/chore-1/skip-requests',
      expect.objectContaining({ method: 'POST' }),
    ))
  })
  it('lets a kid undo a completed chore', async () => {
    const user = userEvent.setup()
    const completedDashboard = {
      ...dashboard,
      chores: dashboard.chores.map((chore) => ({ ...chore, completed: true })),
      completed_count: 1,
    }
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, options?: RequestInit) => {
      const path = String(input)
      if (path.endsWith('/dashboard')) return new Response(JSON.stringify(completedDashboard), { status: 200, headers: { 'Content-Type': 'application/json' } })
      if (path.endsWith('/weather')) return new Response(JSON.stringify(weather), { status: 200, headers: { 'Content-Type': 'application/json' } })
      if (path.includes('/weeks/')) return new Response(JSON.stringify(week), { status: 200, headers: { 'Content-Type': 'application/json' } })
      if (path.endsWith('/chores/chore-1/complete') && options?.method === 'DELETE') return new Response(null, { status: 204 })
      throw new Error(`Unexpected request: ${path}`)
    }))
    render(<App />)

    await user.click(await screen.findByRole('button', { name: 'Undo Make Bed' }))

    expect(await screen.findByRole('status')).toHaveTextContent('Task undone. Awards removed.')
    await waitFor(() => expect(fetch).toHaveBeenCalledWith('/api/chores/chore-1/complete', expect.objectContaining({ method: 'DELETE' })))
  })

  it('lets a kid browse a previous year without editing it', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input)
      if (path.endsWith('/dashboard')) return new Response(JSON.stringify(dashboard), { status: 200, headers: { 'Content-Type': 'application/json' } })
      if (path.endsWith('/weeks/2026-08-22')) return new Response(JSON.stringify(week), { status: 200, headers: { 'Content-Type': 'application/json' } })
      if (path.endsWith('/weeks/2025-12-31')) return new Response(JSON.stringify({
        start_date: '2025-12-28',
        end_date: '2026-01-03',
        days: [
          { date: '2025-12-28', completed_count: 0, total_count: 1, future: false },
          { date: '2025-12-29', completed_count: 0, total_count: 1, future: false },
          { date: '2025-12-30', completed_count: 0, total_count: 1, future: false },
          { date: '2025-12-31', completed_count: 0, total_count: 1, future: false },
          { date: '2026-01-01', completed_count: 0, total_count: 1, future: false },
          { date: '2026-01-02', completed_count: 0, total_count: 1, future: false },
          { date: '2026-01-03', completed_count: 0, total_count: 1, future: false },
        ],
      }), { status: 200, headers: { 'Content-Type': 'application/json' } })
      if (path.endsWith('/days/2025-12-31')) return new Response(JSON.stringify({
        date: '2025-12-31',
        completed_count: 0,
        total_count: 1,
        chores: [{ id: 'old-chore', name: 'Read a book', emoji: '📚', completed: false, points_awarded: 5, money_awarded: '0.00', xoxos_awarded: 0 }],
      }), { status: 200, headers: { 'Content-Type': 'application/json' } })
      throw new Error(`Unexpected request: ${path}`)
    }))
    const user = userEvent.setup()
    render(<App />)
    await user.click(await screen.findByText('Go to date'))
    const dateInput = screen.getByLabelText('Jump to date and year')

    fireEvent.change(dateInput, { target: { value: '2025-12-31' } })

    expect(await screen.findByRole('heading', { name: 'Read a book' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Read a book was not completed' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Back to today' })).toBeInTheDocument()
  })

  it('shows the parent PIN screen at the parent route', async () => {
    window.history.replaceState({}, '', '/parent')
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ detail: 'Parent PIN required' }), { status: 401, headers: { 'Content-Type': 'application/json' } })))

    render(<App />)

    expect(await screen.findByRole('heading', { name: 'Enter your PIN' })).toBeInTheDocument()
    expect(screen.getByLabelText('4-digit PIN')).toHaveAttribute('inputmode', 'numeric')
  })

  it('adds a chore without showing a false error after the save succeeds', async () => {
    window.history.replaceState({}, '', '/parent')
    const overview = {
      dashboard,
      all_chores: dashboard.chores,
      all_rewards: dashboard.rewards,
      reward_requests: [],
      skip_requests: [],
      point_history: [],
      piggy_bank_history: [],
      xoxo_history: [],
    }
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, options?: RequestInit) => {
      const path = String(input)
      if (path.endsWith('/parent/overview')) return new Response(JSON.stringify(overview), { status: 200, headers: { 'Content-Type': 'application/json' } })
      if (path.endsWith(`/weeks/${dashboard.date}`)) return new Response(JSON.stringify(week), { status: 200, headers: { 'Content-Type': 'application/json' } })
      if (path.endsWith('/parent/chores') && options?.method === 'POST') {
        return new Response(JSON.stringify({ ...dashboard.chores[0], id: 'chore-2', name: 'Water plants' }), { status: 201, headers: { 'Content-Type': 'application/json' } })
      }
      throw new Error(`Unexpected request: ${path}`)
    }))
    const user = userEvent.setup()
    render(<App />)
    await user.click(await screen.findByRole('button', { name: 'Chores' }))
    expect(screen.getByRole('link', { name: 'Go to kid dashboard' })).toHaveAttribute('href', '/')
    await user.clear(screen.getByRole('textbox', { name: 'Chore name' }))
    await user.type(screen.getByRole('textbox', { name: 'Chore name' }), 'Water plants')
    await user.clear(screen.getByRole('spinbutton', { name: 'Chore money' }))
    await user.type(screen.getByRole('spinbutton', { name: 'Chore money' }), '0.5')

    await user.click(screen.getByRole('button', { name: 'Add chore' }))

    await waitFor(() => expect(fetch).toHaveBeenCalledWith('/api/parent/chores', expect.objectContaining({ method: 'POST' })))
    const createCall = vi.mocked(fetch).mock.calls.find(([path, options]) => String(path).endsWith('/parent/chores') && options?.method === 'POST')
    expect(JSON.parse(String(createCall?.[1]?.body))).toMatchObject({ points: 10, money_reward: '0.5', xoxo_reward: 0 })
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Chore name' })).toHaveValue('')
  })

  it('makes point deductions explicit and sends a negative ledger amount', async () => {
    window.history.replaceState({}, '', '/parent')
    const overview = {
      dashboard,
      all_chores: dashboard.chores,
      all_rewards: dashboard.rewards,
      reward_requests: [],
      skip_requests: [],
      point_history: [],
      piggy_bank_history: [],
      xoxo_history: [],
    }
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, options?: RequestInit) => {
      const path = String(input)
      if (path.endsWith('/parent/overview')) return new Response(JSON.stringify(overview), { status: 200, headers: { 'Content-Type': 'application/json' } })
      if (path.endsWith('/parent/points') && options?.method === 'POST') return new Response(JSON.stringify({ balance: 1240 }), { status: 200, headers: { 'Content-Type': 'application/json' } })
      throw new Error(`Unexpected request: ${path}`)
    }))
    const user = userEvent.setup()
    render(<App />)
    await user.click(await screen.findByRole('button', { name: 'Balances' }))
    await user.selectOptions(screen.getByLabelText('Action'), 'deduct')
    await user.type(screen.getByLabelText('Amount'), '10')
    await user.type(screen.getByLabelText('Description'), 'Did not do it the first time listening')

    await user.click(screen.getByRole('button', { name: 'Save point adjustment' }))

    await waitFor(() => {
      const call = vi.mocked(fetch).mock.calls.find(([path, options]) => String(path).endsWith('/parent/points') && options?.method === 'POST')
      expect(JSON.parse(String(call?.[1]?.body))).toEqual({ amount: -10, reason: 'Did not do it the first time listening' })
    })
  })

  it('lets a parent approve a chore skip request', async () => {
    window.history.replaceState({}, '', '/parent')
    const overview = {
      dashboard: {
        ...dashboard,
        chores: dashboard.chores.map((chore) => ({ ...chore, skip_status: 'pending' })),
      },
      all_chores: dashboard.chores,
      all_rewards: dashboard.rewards,
      reward_requests: [],
      skip_requests: [{
        id: 'skip-1',
        chore_id: 'chore-1',
        chore_name: 'Make Bed',
        chore_emoji: '🛏️',
        skip_date: dashboard.date,
        status: 'pending',
        requested_at: '2026-08-22T10:00:00Z',
        resolved_at: null,
      }],
      point_history: [],
      piggy_bank_history: [],
      xoxo_history: [],
    }
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, options?: RequestInit) => {
      const path = String(input)
      if (path.endsWith('/parent/overview')) return new Response(JSON.stringify(overview), { status: 200, headers: { 'Content-Type': 'application/json' } })
      if (path.endsWith('/parent/chore-skip-requests/skip-1') && options?.method === 'PATCH') return new Response(JSON.stringify({ ...overview.skip_requests[0], status: 'approved' }), { status: 200, headers: { 'Content-Type': 'application/json' } })
      throw new Error(`Unexpected request: ${path}`)
    }))
    const user = userEvent.setup()
    render(<App />)

    await user.click(await screen.findByRole('button', { name: 'Rewards (1)' }))
    await user.click(screen.getByRole('button', { name: 'Approve' }))

    await waitFor(() => {
      const call = vi.mocked(fetch).mock.calls.find(([path, options]) => String(path).endsWith('/parent/chore-skip-requests/skip-1') && options?.method === 'PATCH')
      expect(JSON.parse(String(call?.[1]?.body))).toEqual({ action: 'approve' })
    })
  })
  it('lets a parent backfill a historical chore with a reason', async () => {
    window.history.replaceState({}, '', '/parent')
    const overview = { dashboard, all_chores: dashboard.chores, all_rewards: dashboard.rewards, reward_requests: [], skip_requests: [], point_history: [], piggy_bank_history: [], xoxo_history: [] }
    const day = {
      date: dashboard.date,
      completed_count: 0,
      total_count: 1,
      chores: [{ id: 'chore-1', name: 'Make Bed', emoji: '🛏️', completed: false, points_awarded: 10, money_awarded: '0.25', xoxos_awarded: 1 }],
      audit: [],
    }
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, options?: RequestInit) => {
      const path = String(input)
      if (path.endsWith('/parent/overview')) return new Response(JSON.stringify(overview), { status: 200, headers: { 'Content-Type': 'application/json' } })
      if (path.endsWith(`/weeks/${dashboard.date}`)) return new Response(JSON.stringify(week), { status: 200, headers: { 'Content-Type': 'application/json' } })
      if (path.endsWith(`/parent/days/${dashboard.date}`) && !options?.method) return new Response(JSON.stringify(day), { status: 200, headers: { 'Content-Type': 'application/json' } })
      if (path.includes(`/parent/days/${dashboard.date}/chores/chore-1`) && options?.method === 'PUT') return new Response(JSON.stringify({ ...day, completed_count: 1, chores: [{ ...day.chores[0], completed: true }] }), { status: 200, headers: { 'Content-Type': 'application/json' } })
      throw new Error(`Unexpected request: ${path}`)
    }))
    const user = userEvent.setup()
    render(<App />)
    await user.click(await screen.findByRole('button', { name: 'History' }))
    await user.type(await screen.findByLabelText('Reason for Make Bed'), 'Paper chart showed it was done')

    await user.click(screen.getByRole('button', { name: 'Mark complete' }))

    await waitFor(() => {
      const call = vi.mocked(fetch).mock.calls.find(([path, options]) => String(path).includes('/chores/chore-1') && options?.method === 'PUT')
      expect(JSON.parse(String(call?.[1]?.body))).toEqual({ completed: true, reason: 'Paper chart showed it was done' })
    })
  })
})
