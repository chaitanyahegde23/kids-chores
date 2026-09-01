import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { ApiError, api, type Chore, type DayChore, type ParentDailyRecord, type ParentOverview, type Reward, type WeekRecord } from '../api/client'
import { WeekStrip } from './WeekStrip'

type Tab = 'overview' | 'history' | 'chores' | 'money' | 'rewards' | 'goal' | 'settings'

function ParentLogin({ onLogin }: { onLogin: () => void }) {
  const [pin, setPin] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    try {
      await api.parentLogin(pin)
      onLogin()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not unlock parent mode')
      setPin('')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="parent-login-shell">
      <a href="/" className="back-link">← Kid dashboard</a>
      <form className="pin-card" onSubmit={(event) => void submit(event)}>
        <div className="pin-icon">🔐</div>
        <span className="eyebrow">PARENT MODE</span>
        <h1>Enter your PIN</h1>
        <p>Use your four-digit parent PIN to manage chores and rewards.</p>
        <label htmlFor="parent-pin">4-digit PIN</label>
        <input
          id="parent-pin"
          inputMode="numeric"
          autoComplete="off"
          maxLength={4}
          pattern="[0-9]{4}"
          value={pin}
          onChange={(event) => setPin(event.target.value.replace(/\D/g, '').slice(0, 4))}
          autoFocus
          required
        />
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="primary-button" disabled={pin.length !== 4 || busy}>{busy ? 'Checking…' : 'Unlock'}</button>
      </form>
    </main>
  )
}

const recurrenceLabels: Record<Chore['recurrence_type'], string> = {
  daily: 'Daily',
  weekdays: 'Weekdays',
  weekends: 'Weekends',
  specific_days: 'Specific days',
}

const weekDays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const dayPartLabels: Record<Chore['day_part'], string> = {
  morning: 'Morning',
  after_school: 'After school',
  evening: 'Evening',
}

function formatChoreRewards(chore: Chore) {
  const rewards = []
  if (chore.points) rewards.push(`${chore.points} ⭐`)
  if (Number(chore.money_reward)) rewards.push(`$${Number(chore.money_reward).toFixed(2)}`)
  if (chore.xoxo_reward) rewards.push(`${chore.xoxo_reward} 🤗`)
  return rewards.join(' · ')
}

function formatDayRewards(chore: DayChore) {
  const rewards = []
  if (chore.points_awarded) rewards.push(`${chore.points_awarded} ⭐`)
  if (Number(chore.money_awarded)) rewards.push(`$${Number(chore.money_awarded).toFixed(2)}`)
  if (chore.xoxos_awarded) rewards.push(`${chore.xoxos_awarded} 🤗`)
  return rewards.join(' · ')
}

function formatAuditDelta(points: number, money: string, xoxos: number) {
  const rewards = []
  if (points) rewards.push(`${points > 0 ? '+' : ''}${points} ⭐`)
  if (Number(money)) rewards.push(`${Number(money) > 0 ? '+' : '-'}$${Math.abs(Number(money)).toFixed(2)}`)
  if (xoxos) rewards.push(`${xoxos > 0 ? '+' : ''}${xoxos} 🤗`)
  return rewards.join(' · ')
}

function HistoricalChoreRow({ chore, busy, onUpdate }: { chore: DayChore; busy: boolean; onUpdate: (chore: DayChore, reason: string) => Promise<void> }) {
  const [reason, setReason] = useState('')
  return (
    <article className={`history-chore-row ${chore.completed ? 'is-complete' : ''}`}>
      <span className="management-emoji">{chore.emoji}</span>
      <div><h3>{chore.name}</h3><p>{formatDayRewards(chore)} · {chore.skip_status === 'approved' ? 'Skipped with parent approval' : chore.completed ? 'Completed' : 'Not done'}</p></div>
      {chore.skip_status === 'approved' ? <strong>Skipped</strong> : <>
        <label>Reason<input aria-label={`Reason for ${chore.name}`} value={reason} maxLength={240} placeholder={chore.completed ? 'Why are you reopening it?' : 'Why are you backfilling it?'} onChange={(event) => setReason(event.target.value)} /></label>
        <button className={chore.completed ? 'danger-button' : 'approve-button'} disabled={busy || !reason.trim()} onClick={() => void onUpdate(chore, reason).then(() => setReason(''))}>{chore.completed ? 'Undo completion' : 'Mark complete'}</button>
      </>}
    </article>
  )
}

function ChoreForm({ chore, onSaved, onCancel }: { chore?: Chore; onSaved: () => void; onCancel?: () => void }) {
  const [recurrence, setRecurrence] = useState<Chore['recurrence_type']>(chore?.recurrence_type ?? 'daily')
  const [error, setError] = useState('')

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    const days = form.getAll('days').map(Number)
    const body = {
      name: String(form.get('name')),
      emoji: String(form.get('emoji')),
      points: Number(form.get('points')),
      money_reward: String(form.get('money_reward')),
      xoxo_reward: Number(form.get('xoxo_reward')),
      recurrence_type: recurrence,
      recurrence_days: recurrence === 'specific_days' ? days : null,
      day_part: String(form.get('day_part')) as Chore['day_part'],
      active: form.get('active') === 'on',
    }
    try {
      if (chore) await api.updateChore(chore.id, body)
      else await api.createChore(body)
      onSaved()
      if (!chore) formElement.reset()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not save chore')
    }
  }

  return (
    <form className="management-form" onSubmit={(event) => void submit(event)}>
      <div className="field small"><label>Emoji</label><input aria-label="Chore emoji" name="emoji" defaultValue={chore?.emoji ?? '✅'} maxLength={16} required /></div>
      <div className="field grow"><label>Chore name</label><input aria-label="Chore name" name="name" defaultValue={chore?.name} maxLength={120} required /></div>
      <div className="field small"><label>Points</label><input aria-label="Chore points" name="points" type="number" min="0" max="10000" defaultValue={chore?.points ?? 10} required /></div>
      <div className="field small"><label>Money</label><input aria-label="Chore money" name="money_reward" type="number" min="0" step="0.01" defaultValue={chore?.money_reward ?? '0.00'} required /></div>
      <div className="field small"><label>XOXOs</label><input aria-label="Chore XOXOs" name="xoxo_reward" type="number" min="0" max="10000" defaultValue={chore?.xoxo_reward ?? 0} required /></div>
      <div className="field"><label>Repeats</label><select value={recurrence} onChange={(event) => setRecurrence(event.target.value as Chore['recurrence_type'])}>{Object.entries(recurrenceLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>
      <div className="field"><label>Part of day</label><select aria-label="Chore part of day" name="day_part" defaultValue={chore?.day_part ?? 'after_school'}>{Object.entries(dayPartLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>
      {recurrence === 'specific_days' && <fieldset className="weekday-picker"><legend>Days</legend>{weekDays.map((day, index) => <label key={day}><input type="checkbox" name="days" value={index} defaultChecked={chore?.recurrence_days?.includes(index)} />{day}</label>)}</fieldset>}
      <label className="toggle-field"><input type="checkbox" name="active" defaultChecked={chore?.active ?? true} /> Active</label>
      {error && <p className="form-error">{error}</p>}
      <div className="form-actions"><button className="primary-button">{chore ? 'Save changes' : 'Add chore'}</button>{onCancel && <button type="button" className="text-button" onClick={onCancel}>Cancel</button>}</div>
    </form>
  )
}

function RewardForm({ reward, onSaved, onCancel }: { reward?: Reward; onSaved: () => void; onCancel?: () => void }) {
  const [error, setError] = useState('')
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    const body = { name: String(form.get('name')), emoji: String(form.get('emoji')), points_cost: Number(form.get('points_cost')), active: form.get('active') === 'on' }
    try {
      if (reward) await api.updateReward(reward.id, body)
      else await api.createReward(body)
      onSaved()
      if (!reward) formElement.reset()
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not save reward') }
  }
  return (
    <form className="management-form" onSubmit={(event) => void submit(event)}>
      <div className="field small"><label>Emoji</label><input name="emoji" defaultValue={reward?.emoji ?? '🎁'} maxLength={16} required /></div>
      <div className="field grow"><label>Reward name</label><input name="name" defaultValue={reward?.name} maxLength={120} required /></div>
      <div className="field"><label>Point cost</label><input name="points_cost" type="number" min="1" defaultValue={reward?.points_cost ?? 100} required /></div>
      <label className="toggle-field"><input type="checkbox" name="active" defaultChecked={reward?.active ?? true} /> Active</label>
      {error && <p className="form-error">{error}</p>}
      <div className="form-actions"><button className="primary-button">{reward ? 'Save changes' : 'Add reward'}</button>{onCancel && <button type="button" className="text-button" onClick={onCancel}>Cancel</button>}</div>
    </form>
  )
}

export function ParentDashboard() {
  const [overview, setOverview] = useState<ParentOverview | null>(null)
  const [authenticated, setAuthenticated] = useState<boolean | null>(null)
  const [tab, setTab] = useState<Tab>('overview')
  const [editingChore, setEditingChore] = useState<Chore | null>(null)
  const [editingReward, setEditingReward] = useState<Reward | null>(null)
  const [deletingChoreId, setDeletingChoreId] = useState<string | null>(null)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [historyDate, setHistoryDate] = useState('')
  const [parentDay, setParentDay] = useState<ParentDailyRecord | null>(null)
  const [historyBusy, setHistoryBusy] = useState(false)
  const [parentWeek, setParentWeek] = useState<WeekRecord | null>(null)

  const load = useCallback(async () => {
    try {
      setOverview(await api.parentOverview())
      setAuthenticated(true)
      setError('')
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) setAuthenticated(false)
      else setError(cause instanceof Error ? cause.message : 'Could not load parent mode')
    }
  }, [])

  useEffect(() => {
    let active = true
    void api.parentOverview().then(
      (result) => {
        if (!active) return
        setOverview(result)
        setAuthenticated(true)
      },
      (cause: unknown) => {
        if (!active) return
        if (cause instanceof ApiError && cause.status === 401) setAuthenticated(false)
        else setError(cause instanceof Error ? cause.message : 'Could not load parent mode')
      },
    )
    return () => {
      active = false
    }
  }, [])

  const run = async (action: () => Promise<unknown>, message: string) => {
    try {
      await action()
      setNotice(message)
      setError('')
      await load()
      window.setTimeout(() => setNotice(''), 2000)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Action failed') }
  }

  const loadHistory = async (day: string) => {
    setHistoryDate(day)
    setParentDay(null)
    setHistoryBusy(true)
    try {
      const weekRequest = parentWeek && day >= parentWeek.start_date && day <= parentWeek.end_date
        ? Promise.resolve(parentWeek)
        : api.week(day)
      const [record, nextWeek] = await Promise.all([api.parentDay(day), weekRequest])
      setParentDay(record)
      setParentWeek(nextWeek)
      setError('')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load chore history')
    } finally {
      setHistoryBusy(false)
    }
  }

  const updateHistory = async (chore: DayChore, reason: string) => {
    const day = historyDate || overview?.dashboard.date
    if (!day) return
    setHistoryBusy(true)
    try {
      setParentDay(await api.updateHistoricalChore(day, chore.id, !chore.completed, reason))
      setParentWeek(await api.week(day))
      setNotice(chore.completed ? 'Completion undone and awards reversed' : 'Completion backfilled')
      setError('')
      await load()
      window.setTimeout(() => setNotice(''), 2200)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not update this completion')
    } finally {
      setHistoryBusy(false)
    }
  }

  if (authenticated === null) return <main className="center-screen"><p>Opening parent mode…</p></main>
  if (!authenticated) return <ParentLogin onLogin={() => void load()} />
  if (!overview) return <main className="center-screen error-state"><h1>Parent dashboard unavailable</h1><p>{error}</p><button onClick={() => void load()}>Try again</button></main>

  const pending = overview.reward_requests.filter((request) => request.status === 'pending')
  const pendingSkips = overview.skip_requests.filter((request) => request.status === 'pending')
  const pendingRequestCount = pending.length + pendingSkips.length

  const submitAdjustment = async (event: FormEvent<HTMLFormElement>, kind: 'points' | 'piggy' | 'xoxo') => {
    event.preventDefault()
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    const rawAmount = String(form.get('amount'))
    const reason = String(form.get('reason'))
    const pointAmount = form.get('operation') === 'deduct'
      ? -Math.abs(Number(rawAmount))
      : Math.abs(Number(rawAmount))
    await run(
      () => kind === 'points' ? api.adjustPoints(pointAmount, reason) : kind === 'piggy' ? api.adjustPiggy(rawAmount, reason) : api.adjustXoxos(Number(rawAmount), reason),
      `${kind === 'points' ? 'Points' : kind === 'piggy' ? 'Piggy bank' : 'XOXOs'} updated`,
    )
    formElement.reset()
  }

  const quickAdd = (kind: 'points' | 'piggy' | 'xoxo', amount: number, label: string) => {
    const action = kind === 'points' ? api.adjustPoints(amount, `Quick add: ${label}`) : kind === 'piggy' ? api.adjustPiggy(amount.toFixed(2), `Quick add: ${label}`) : api.adjustXoxos(amount, `Quick add: ${label}`)
    void run(() => action, `${label} added`)
  }

  const submitPinChange = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const currentPin = String(form.get('current_pin'))
    const newPin = String(form.get('new_pin'))
    const confirmation = String(form.get('confirm_pin'))
    if (newPin !== confirmation) {
      setError('New PIN entries do not match')
      return
    }
    try {
      await api.changePin(currentPin, newPin)
      setAuthenticated(false)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not change PIN')
    }
  }

  return (
    <main className="parent-shell">
      <header className="parent-header">
        <div><span className="eyebrow">KIDS CHORES</span><h1>Parent dashboard</h1><p>Manage today without making it complicated.</p></div>
        <div className="header-actions"><a href="/" className="secondary-button" aria-label="Go to kid dashboard">← Kids</a><button className="text-button" onClick={() => void run(async () => { await api.parentLogout(); setAuthenticated(false) }, '')}>Lock</button></div>
      </header>
      <nav className="parent-tabs" aria-label="Parent sections">
        {(['overview', 'history', 'chores', 'money', 'rewards', 'goal', 'settings'] as Tab[]).map((item) => <button key={item} className={tab === item ? 'active' : ''} onClick={() => { setTab(item); if (item === 'history' && !parentDay) void loadHistory(historyDate || overview.dashboard.date) }}>{item === 'money' ? 'Balances' : item[0].toUpperCase() + item.slice(1)}{item === 'rewards' && pendingRequestCount > 0 ? ` (${pendingRequestCount})` : ''}</button>)}
      </nav>
      {notice && <div className="success-banner" role="status">✓ {notice}</div>}
      {error && <div className="inline-error" role="alert">{error}</div>}

      {tab === 'overview' && <section className="parent-section">
        <div className="admin-summary-grid">
          <article><span>Points</span><strong>{overview.dashboard.points_balance.toLocaleString()} ⭐</strong></article>
          <article><span>Piggy bank</span><strong>${Number(overview.dashboard.piggy_bank_balance).toFixed(2)}</strong></article>
          <article><span>XOXOs</span><strong>{overview.dashboard.xoxo_balance.toLocaleString()} 🤗</strong></article>
          <article><span>Today</span><strong>{overview.dashboard.completed_count} / {overview.dashboard.total_count}</strong></article>
          <article><span>Streak</span><strong>{overview.dashboard.streak_days} days 🔥</strong></article>
        </div>
        <div className="admin-grid">
          <article className="admin-card"><div className="card-heading"><h2>Today’s progress</h2><button className="text-button" onClick={() => setTab('chores')}>Manage</button></div>{overview.dashboard.chores.map((chore) => <div className="status-row" key={chore.id}><span>{chore.emoji} {chore.name}</span><strong className={chore.completed ? 'complete-text' : ''}>{chore.skip_status === 'approved' ? 'Skipped' : chore.skip_status === 'pending' ? 'Skip requested' : chore.completed ? 'Done' : 'Waiting'}</strong></div>)}</article>
          <article className="admin-card"><div className="card-heading"><h2>Pending approvals</h2><button className="text-button" onClick={() => setTab('rewards')}>Review</button></div>{pendingRequestCount === 0 ? <p className="empty-message">No requests waiting.</p> : <><p>{pendingSkips.length} chore skips · {pending.length} rewards</p>{pendingSkips.map((request) => <div className="status-row" key={request.id}><span>{request.chore_emoji} Skip {request.chore_name}</span><strong>{request.skip_date}</strong></div>)}</>}</article>
        </div>
      </section>}

      {tab === 'history' && <section className="parent-section">
        <div className="section-title"><div><span className="eyebrow">DAILY RECORDS</span><h2>Chore history</h2></div></div>
        <article className="admin-card">
          <WeekStrip week={parentWeek} selectedDate={historyDate || overview.dashboard.date} today={overview.dashboard.date} busy={historyBusy} onSelect={(date) => void loadHistory(date)} />
          <p className="history-help">Backfills and corrections update today’s balances and always create ledger and audit entries.</p>
          {historyBusy && !parentDay && <p className="empty-message">Loading this day…</p>}
          {parentDay && <><div className="history-summary"><strong>{parentDay.completed_count} of {parentDay.total_count} completed</strong><span>{parentDay.date}</span></div><div className="history-chore-list">{parentDay.chores.length === 0 ? <p className="empty-message">No chores scheduled for this day.</p> : parentDay.chores.map((chore) => <HistoricalChoreRow key={chore.id} chore={chore} busy={historyBusy} onUpdate={updateHistory} />)}</div></>}
        </article>
        <article className="admin-card"><h3>Audit trail</h3>{!parentDay || parentDay.audit.length === 0 ? <p className="empty-message">No completion changes recorded for this date.</p> : <div className="audit-list">{parentDay.audit.map((event) => <div key={event.id}><div><strong>{event.action === 'completed' ? 'Completed' : 'Reopened'} · {event.chore_name}</strong><span>{event.actor === 'kid' ? 'Kid' : event.actor === 'parent' ? 'Parent' : 'Imported'} · {new Date(event.created_at).toLocaleString()}</span></div><strong className={event.action === 'completed' ? 'positive' : 'negative'}>{formatAuditDelta(event.points_delta, event.money_delta, event.xoxos_delta)}</strong><p>{event.reason}</p></div>)}</div>}</article>
      </section>}

      {tab === 'chores' && <section className="parent-section"><div className="section-title"><div><span className="eyebrow">ROUTINES</span><h2>Manage chores</h2></div></div>
        <div className="admin-card"><h3>Add a chore</h3><ChoreForm onSaved={() => void load()} /></div>
        <div className="management-list">{overview.all_chores.map((chore) => editingChore?.id === chore.id ? <article className="admin-card" key={chore.id}><ChoreForm chore={chore} onSaved={() => { setEditingChore(null); void load() }} onCancel={() => setEditingChore(null)} /></article> : <article className={`management-row ${!chore.active ? 'muted' : ''}`} key={chore.id}><span className="management-emoji">{chore.emoji}</span><div><h3>{chore.name}</h3><p>{formatChoreRewards(chore)} · {dayPartLabels[chore.day_part]} · {recurrenceLabels[chore.recurrence_type]} · {chore.active ? 'Active' : 'Archived'}</p></div><div className="row-actions"><button className="secondary-button" onClick={() => setEditingChore(chore)}>Edit</button>{chore.active ? <button className="danger-button" onClick={() => void run(() => api.archiveChore(chore.id), 'Chore archived')}>Archive</button> : deletingChoreId === chore.id ? <><button className="danger-button" onClick={() => { setDeletingChoreId(null); void run(() => api.deleteChore(chore.id), 'Chore deleted') }}>Confirm delete</button><button className="text-button" onClick={() => setDeletingChoreId(null)}>Cancel</button></> : <button className="danger-button" onClick={() => setDeletingChoreId(chore.id)}>Delete</button>}</div></article>)}</div>
      </section>}

      {tab === 'money' && <section className="parent-section"><div className="section-title"><div><span className="eyebrow">BALANCES</span><h2>Points, money & XOXOs</h2></div></div><div className="admin-grid">
        <article className="admin-card"><h3>Adjust points</h3><p className="large-balance">{overview.dashboard.points_balance.toLocaleString()} ⭐</p><div className="quick-actions"><button onClick={() => quickAdd('points', 5, '5 points')}>+5</button><button onClick={() => quickAdd('points', 10, '10 points')}>+10</button><button onClick={() => quickAdd('points', 25, '25 points')}>+25</button></div><form className="stack-form" onSubmit={(event) => void submitAdjustment(event, 'points')}><label>Action<select name="operation" defaultValue="add"><option value="add">Add points</option><option value="deduct">Deduct points</option></select></label><label>Amount<input name="amount" type="number" min="1" placeholder="10" required /></label><label>Description<input name="reason" maxLength={240} placeholder="Did not do it the first time listening" required /></label><button className="primary-button">Save point adjustment</button></form><h4>Recent history</h4><div className="history-list">{overview.point_history.map((item) => <div key={item.id}><strong className={item.amount >= 0 ? 'positive' : 'negative'}>{item.amount > 0 ? '+' : ''}{item.amount}</strong><span>{item.reason}</span></div>)}</div></article>
        <article className="admin-card"><h3>Adjust piggy bank</h3><p className="large-balance">${Number(overview.dashboard.piggy_bank_balance).toFixed(2)}</p><div className="quick-actions"><button onClick={() => quickAdd('piggy', .25, 'Quarter')}>+25¢</button><button onClick={() => quickAdd('piggy', 1, 'One dollar')}>+$1</button><button onClick={() => quickAdd('piggy', 5, 'Five dollars')}>+$5</button></div><form className="stack-form" onSubmit={(event) => void submitAdjustment(event, 'piggy')}><label>Custom amount<input name="amount" type="number" step="0.01" placeholder="5.00 or -2.50" required /></label><label>Note<input name="reason" maxLength={240} placeholder="Weekly allowance" required /></label><button className="primary-button">Save money adjustment</button></form><h4>Recent history</h4><div className="history-list">{overview.piggy_bank_history.map((item) => <div key={item.id}><strong className={Number(item.amount) >= 0 ? 'positive' : 'negative'}>{Number(item.amount) > 0 ? '+' : ''}${Number(item.amount).toFixed(2)}</strong><span>{item.reason}</span></div>)}</div></article>
        <article className="admin-card"><h3>Add XOXOs</h3><p className="large-balance">{overview.dashboard.xoxo_balance.toLocaleString()} 🤗</p><div className="quick-actions"><button onClick={() => quickAdd('xoxo', 1, 'One XOXO')}>+1</button><button onClick={() => quickAdd('xoxo', 5, 'Five XOXOs')}>+5</button><button onClick={() => quickAdd('xoxo', 10, 'Ten XOXOs')}>+10</button></div><form className="stack-form" onSubmit={(event) => void submitAdjustment(event, 'xoxo')}><label>Custom amount<input name="amount" type="number" placeholder="3 or -1" required /></label><label>Reason<input name="reason" maxLength={240} placeholder="A big hug" required /></label><button className="primary-button">Save XOXOs</button></form><h4>Recent history</h4><div className="history-list">{overview.xoxo_history.map((item) => <div key={item.id}><strong className={item.amount >= 0 ? 'positive' : 'negative'}>{item.amount > 0 ? '+' : ''}{item.amount}</strong><span>{item.reason}</span></div>)}</div></article>
        <article className="admin-card"><h3>Bank interest</h3><p className="large-balance">{Number(overview.dashboard.piggy_bank_interest_rate).toFixed(2)}% annual</p><p>At this rate, today’s balance would be about <strong>${(Number(overview.dashboard.piggy_bank_balance) * Math.pow(1 + Number(overview.dashboard.piggy_bank_interest_rate) / 1200, 12)).toFixed(2)}</strong> after one year.</p><form className="stack-form" onSubmit={(event) => { event.preventDefault(); const form = new FormData(event.currentTarget); void run(() => api.setInterestRate(String(form.get('rate'))), 'Interest rate updated') }}><label>Annual interest rate<input name="rate" type="number" min="0" max="100" step="0.01" defaultValue={overview.dashboard.piggy_bank_interest_rate} required /></label><button className="primary-button">Save interest rate</button></form><button className="secondary-button interest-button" onClick={() => void run(api.applyInterest, 'One month of interest added')}>Apply one month’s interest</button><p className="help-text">Interest is added only when you tap this button, so every deposit has a visible ledger entry.</p></article>
      </div></section>}

      {tab === 'rewards' && <section className="parent-section"><div className="section-title"><div><span className="eyebrow">APPROVALS & MOTIVATION</span><h2>Requests & rewards</h2></div></div>
        <article className="admin-card"><h3>Pending chore skips</h3>{pendingSkips.length === 0 ? <p className="empty-message">No skip requests need approval.</p> : pendingSkips.map((request) => <div className="request-row" key={request.id}><div><span>{request.chore_emoji}</span><div><h4>Skip {request.chore_name}</h4><p>{request.skip_date}</p></div></div><div><button className="approve-button" onClick={() => void run(() => api.resolveChoreSkip(request.id, 'approve'), 'Chore skip approved')}>Approve</button><button className="danger-button" onClick={() => void run(() => api.resolveChoreSkip(request.id, 'reject'), 'Chore skip rejected')}>Reject</button></div></div>)}</article>
        <article className="admin-card"><h3>Pending reward requests</h3>{pending.length === 0 ? <p className="empty-message">No reward requests need approval.</p> : pending.map((request) => <div className="request-row" key={request.id}><div><span>{request.reward_emoji}</span><div><h4>{request.reward_name}</h4><p>{request.points_cost} points</p></div></div><div><button className="approve-button" onClick={() => void run(() => api.resolveReward(request.id, 'approve'), 'Reward approved')}>Approve</button><button className="danger-button" onClick={() => void run(() => api.resolveReward(request.id, 'reject'), 'Reward rejected')}>Reject</button></div></div>)}</article>
        <article className="admin-card"><h3>Add a reward</h3><RewardForm onSaved={() => void load()} /></article>
        <div className="management-list">{overview.all_rewards.map((reward) => editingReward?.id === reward.id ? <article className="admin-card" key={reward.id}><RewardForm reward={reward} onSaved={() => { setEditingReward(null); void load() }} onCancel={() => setEditingReward(null)} /></article> : <article className={`management-row ${!reward.active ? 'muted' : ''}`} key={reward.id}><span className="management-emoji">{reward.emoji}</span><div><h3>{reward.name}</h3><p>{reward.points_cost} points · {reward.active ? 'Active' : 'Inactive'}</p></div><div className="row-actions"><button className="secondary-button" onClick={() => setEditingReward(reward)}>Edit</button>{reward.active && <button className="danger-button" onClick={() => void run(() => api.archiveReward(reward.id), 'Reward archived')}>Archive</button>}</div></article>)}</div>
      </section>}

      {tab === 'goal' && <section className="parent-section"><div className="section-title"><div><span className="eyebrow">SAVING</span><h2>Savings goal</h2></div></div><article className="admin-card narrow-card"><form className="stack-form" onSubmit={(event) => { event.preventDefault(); const form = new FormData(event.currentTarget); void run(() => api.saveGoal({ emoji: String(form.get('emoji')), name: String(form.get('name')), target_amount: String(form.get('target')) }), 'Savings goal updated') }}><label>Emoji<input name="emoji" defaultValue={overview.dashboard.savings_goal?.emoji ?? '🎯'} maxLength={16} required /></label><label>Goal name<input name="name" defaultValue={overview.dashboard.savings_goal?.name ?? ''} placeholder="LEGO Set" required /></label><label>Target amount<input name="target" type="number" min="0.01" step="0.01" defaultValue={overview.dashboard.savings_goal?.target_amount ?? ''} required /></label><button className="primary-button">Save goal</button></form></article></section>}

      {tab === 'settings' && <section className="parent-section"><div className="section-title"><div><span className="eyebrow">SECURITY</span><h2>Parent settings</h2></div></div><article className="admin-card narrow-card"><h3>Change parent PIN</h3><p>Changing the PIN locks parent mode on this device. Sign in again with the new PIN.</p><form className="stack-form" onSubmit={(event) => void submitPinChange(event)}><label>Current PIN<input name="current_pin" type="password" inputMode="numeric" pattern="[0-9]{4}" maxLength={4} autoComplete="current-password" required /></label><label>New PIN<input name="new_pin" type="password" inputMode="numeric" pattern="[0-9]{4}" maxLength={4} autoComplete="new-password" required /></label><label>Confirm new PIN<input name="confirm_pin" type="password" inputMode="numeric" pattern="[0-9]{4}" maxLength={4} autoComplete="new-password" required /></label><button className="primary-button">Change PIN</button></form></article></section>}
    </main>
  )
}
