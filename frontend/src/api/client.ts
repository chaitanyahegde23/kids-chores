export type Chore = {
  id: string
  name: string
  emoji: string
  points: number
  money_reward: string
  xoxo_reward: number
  recurrence_type: 'daily' | 'weekdays' | 'weekends' | 'specific_days'
  recurrence_days: number[] | null
  day_part: 'morning' | 'after_school' | 'evening'
  active: boolean
  completed: boolean
  skip_status: 'pending' | 'approved' | 'rejected' | null
}

export type Reward = {
  id: string
  name: string
  emoji: string
  points_cost: number
  active: boolean
}

export type RewardRequest = {
  id: string
  reward_id: string
  reward_name: string
  reward_emoji: string
  status: 'pending' | 'approved' | 'rejected'
  points_cost: number
  requested_at: string
  resolved_at: string | null
}

export type ChoreSkipRequest = {
  id: string
  chore_id: string
  chore_name: string
  chore_emoji: string
  skip_date: string
  status: 'pending' | 'approved' | 'rejected'
  requested_at: string
  resolved_at: string | null
}

export type SavingsGoal = {
  id: string
  name: string
  emoji: string
  target_amount: string
  current_amount: string
  progress_percent: number
}

export type PointActivity = {
  id: string
  amount: number
  reason: string
  created_at: string
}

export type Dashboard = {
  child_id: string
  child_name: string
  greeting: string
  date: string
  points_balance: number
  piggy_bank_balance: string
  xoxo_balance: number
  piggy_bank_interest_rate: string
  point_activity: PointActivity[]
  chores: Chore[]
  completed_count: number
  total_count: number
  rewards: Reward[]
  savings_goal: SavingsGoal | null
  streak_days: number
  pending_reward_count: number
}

export type DayChore = {
  id: string
  name: string
  emoji: string
  day_part: Chore['day_part']
  completed: boolean
  points_awarded: number
  money_awarded: string
  xoxos_awarded: number
  skip_status: 'pending' | 'approved' | 'rejected' | null
}

export type DailyRecord = {
  date: string
  completed_count: number
  total_count: number
  chores: DayChore[]
}

export type ChoreAudit = {
  id: string
  chore_id: string
  chore_name: string
  effective_date: string
  action: 'completed' | 'reopened'
  actor: 'kid' | 'parent' | 'system'
  points_delta: number
  money_delta: string
  xoxos_delta: number
  reason: string
  created_at: string
}

export type ParentDailyRecord = DailyRecord & { audit: ChoreAudit[] }

export type WeekRecord = {
  start_date: string
  end_date: string
  days: Array<{
    date: string
    completed_count: number
    total_count: number
    future: boolean
  }>
}

export type PointTransaction = {
  id: string
  amount: number
  reason: string
  source_type: string
  created_at: string
}

export type PiggyTransaction = {
  id: string
  amount: string
  reason: string
  created_at: string
}

export type XoxoTransaction = {
  id: string
  amount: number
  reason: string
  created_at: string
}

export type Weather = {
  key: 'home' | 'school'
  name: string
  location: string
  temperature: number
  high: number
  low: number
  weather_code: number
  label: string
  emoji: string
}

export type ParentOverview = {
  dashboard: Dashboard
  all_chores: Chore[]
  all_rewards: Reward[]
  reward_requests: RewardRequest[]
  skip_requests: ChoreSkipRequest[]
  point_history: PointTransaction[]
  piggy_bank_history: PiggyTransaction[]
  xoxo_history: XoxoTransaction[]
}

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api${path}`, {
    credentials: 'include',
    ...options,
    headers: options.body ? { 'Content-Type': 'application/json', ...options.headers } : options.headers,
  })
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new ApiError(response.status, payload?.detail ?? 'Something went wrong')
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const api = {
  dashboard: () => request<Dashboard>('/dashboard'),
  day: (date: string) => request<DailyRecord>(`/days/${date}`),
  week: (date: string) => request<WeekRecord>(`/weeks/${date}`),
  weather: () => request<Weather[]>('/weather'),
  completeChore: (id: string) =>
    request<{ message: string; points_balance: number; piggy_bank_balance: string; xoxo_balance: number }>(`/chores/${id}/complete`, { method: 'POST' }),
  undoChore: (id: string) => request<void>(`/chores/${id}/complete`, { method: 'DELETE' }),
  requestChoreSkip: (id: string) =>
    request<ChoreSkipRequest>(`/chores/${id}/skip-requests`, { method: 'POST' }),
  requestReward: (rewardId: string) =>
    request<RewardRequest>('/reward-requests', {
      method: 'POST',
      body: JSON.stringify({ reward_id: rewardId }),
    }),
  parentLogin: (pin: string) =>
    request<void>('/parent/login', { method: 'POST', body: JSON.stringify({ pin }) }),
  parentLogout: () => request<void>('/parent/logout', { method: 'POST' }),
  parentOverview: () => request<ParentOverview>('/parent/overview'),
  parentDay: (date: string) => request<ParentDailyRecord>(`/parent/days/${date}`),
  updateHistoricalChore: (date: string, choreId: string, completed: boolean, reason: string) =>
    request<ParentDailyRecord>(`/parent/days/${date}/chores/${choreId}`, {
      method: 'PUT',
      body: JSON.stringify({ completed, reason }),
    }),
  createChore: (body: object) =>
    request<Chore>('/parent/chores', { method: 'POST', body: JSON.stringify(body) }),
  updateChore: (id: string, body: object) =>
    request<Chore>(`/parent/chores/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  archiveChore: (id: string) => request<void>(`/parent/chores/${id}`, { method: 'DELETE' }),
  deleteChore: (id: string) => request<void>(`/parent/chores/${id}/permanent`, { method: 'DELETE' }),
  adjustPoints: (amount: number, reason: string) =>
    request<{ balance: number }>('/parent/points', {
      method: 'POST',
      body: JSON.stringify({ amount, reason }),
    }),
  adjustPiggy: (amount: string, reason: string) =>
    request<{ balance: string }>('/parent/piggy-bank', {
      method: 'POST',
      body: JSON.stringify({ amount, reason }),
    }),
  adjustXoxos: (amount: number, reason: string) =>
    request<{ balance: number }>('/parent/xoxos', {
      method: 'POST',
      body: JSON.stringify({ amount, reason }),
    }),
  setInterestRate: (annualRate: string) =>
    request<{ annual_rate: string; interest_earned: string; balance: string; projected_one_year: string }>('/parent/piggy-bank/interest-rate', {
      method: 'PUT',
      body: JSON.stringify({ annual_rate: annualRate }),
    }),
  applyInterest: () =>
    request<{ annual_rate: string; interest_earned: string; balance: string; projected_one_year: string }>('/parent/piggy-bank/apply-interest', { method: 'POST' }),
  changePin: (currentPin: string, newPin: string) =>
    request<void>('/parent/pin', {
      method: 'PUT',
      body: JSON.stringify({ current_pin: currentPin, new_pin: newPin }),
    }),
  createReward: (body: object) =>
    request<Reward>('/parent/rewards', { method: 'POST', body: JSON.stringify(body) }),
  updateReward: (id: string, body: object) =>
    request<Reward>(`/parent/rewards/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  archiveReward: (id: string) => request<void>(`/parent/rewards/${id}`, { method: 'DELETE' }),
  resolveChoreSkip: (id: string, action: 'approve' | 'reject') =>
    request<ChoreSkipRequest>(`/parent/chore-skip-requests/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ action }),
    }),
  resolveReward: (id: string, action: 'approve' | 'reject') =>
    request<RewardRequest>(`/parent/reward-requests/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ action }),
    }),
  saveGoal: (body: object) =>
    request<SavingsGoal>('/parent/savings-goal', { method: 'PUT', body: JSON.stringify(body) }),
}
