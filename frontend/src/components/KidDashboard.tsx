import { useCallback, useEffect, useState } from 'react'
import { api, type DailyRecord, type Dashboard, type DayChore, type Weather, type WeekRecord } from '../api/client'
import { jokeForDate } from '../jokes'
import { WeekStrip } from './WeekStrip'

const dayParts = [
  { key: 'morning', label: 'Morning', emoji: '🌅' },
  { key: 'after_school', label: 'After School', emoji: '🎒' },
  { key: 'evening', label: 'Evening', emoji: '🌙' },
] as const

function choreRewardLabel(chore: DayChore) {
  const rewards = []
  if (chore.points_awarded) rewards.push(`+${chore.points_awarded} ⭐`)
  if (Number(chore.money_awarded)) rewards.push(`+$${Number(chore.money_awarded).toFixed(2)}`)
  if (chore.xoxos_awarded) rewards.push(`+${chore.xoxos_awarded} 🤗`)
  return rewards.join(' · ')
}

function readableDate(value: string) {
  return new Date(`${value}T12:00:00`).toLocaleDateString(undefined, {
    weekday: 'long',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function activityDate(value: string) {
  return new Date(value).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  })
}

function LoadingScreen() {
  return (
    <main className="center-screen" aria-live="polite">
      <div className="loading-mark">🏠</div>
      <p>Getting today ready…</p>
    </main>
  )
}

export function KidDashboard() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [weather, setWeather] = useState<Weather[]>([])
  const [weatherBusy, setWeatherBusy] = useState(true)
  const [weatherError, setWeatherError] = useState('')
  const [selectedDate, setSelectedDate] = useState('')
  const [historicalDay, setHistoricalDay] = useState<DailyRecord | null>(null)
  const [historyBusy, setHistoryBusy] = useState(false)
  const [week, setWeek] = useState<WeekRecord | null>(null)

  const load = useCallback(async () => {
    try {
      setDashboard(await api.dashboard())
      setError('')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load the dashboard')
    }
  }, [])

  useEffect(() => {
    let active = true
    void api.dashboard().then(
      (result) => {
        if (active) setDashboard(result)
      },
      (cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : 'Could not load the dashboard')
      },
    )
    return () => {
      active = false
    }
  }, [])

  const finishChore = async (id: string) => {
    setBusyId(id)
    try {
      const result = await api.completeChore(id)
      setNotice(result.message)
      await load()
      if (dashboard) setWeek(await api.week(dashboard.date))
      window.setTimeout(() => setNotice(''), 1800)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not complete the chore')
    } finally {
      setBusyId(null)
    }
  }

  const undoChore = async (id: string) => {
    setBusyId(id)
    try {
      await api.undoChore(id)
      setNotice('Task undone. Awards removed.')
      await load()
      if (dashboard) setWeek(await api.week(dashboard.date))
      window.setTimeout(() => setNotice(''), 1800)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not undo the chore')
    } finally {
      setBusyId(null)
    }
  }

  const requestSkip = async (id: string, name: string) => {
    setBusyId(id)
    try {
      await api.requestChoreSkip(id)
      setNotice(`${name} skip request sent to your parent.`)
      await load()
      if (dashboard) setWeek(await api.week(dashboard.date))
      window.setTimeout(() => setNotice(''), 2200)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not request the skip')
    } finally {
      setBusyId(null)
    }
  }

  const redeem = async (id: string, name: string) => {
    setBusyId(id)
    try {
      await api.requestReward(id)
      setNotice(`${name} sent to your parent! 🎉`)
      await load()
      window.setTimeout(() => setNotice(''), 2200)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not request the reward')
    } finally {
      setBusyId(null)
    }
  }

  const loadWeather = async () => {
    setWeatherBusy(true)
    try {
      setWeather(await api.weather())
      setWeatherError('')
    } catch {
      setWeatherError('Weather is temporarily unavailable')
    } finally {
      setWeatherBusy(false)
    }
  }

  useEffect(() => {
    let active = true
    void api.weather().then(
      (result) => {
        if (active) {
          setWeather(result)
          setWeatherError('')
          setWeatherBusy(false)
        }
      },
      () => {
        if (active) {
          setWeatherError('Weather is temporarily unavailable')
          setWeatherBusy(false)
        }
      },
    )
    return () => {
      active = false
    }
  }, [])

  const showDate = async (value: string) => {
    setSelectedDate(value)
    if (!dashboard) return
    if (value !== dashboard.date) setHistoricalDay(null)
    setHistoryBusy(true)
    try {
      const weekRequest = week && value >= week.start_date && value <= week.end_date
        ? Promise.resolve(week)
        : api.week(value)
      const [nextWeek, day] = await Promise.all([
        weekRequest,
        value === dashboard.date ? Promise.resolve(null) : api.day(value),
      ])
      setWeek(nextWeek)
      setHistoricalDay(day)
      setError('')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load this date')
    } finally {
      setHistoryBusy(false)
    }
  }

  useEffect(() => {
    if (!dashboard || week) return
    void api.week(dashboard.date).then(setWeek, (cause: unknown) => {
      setError(cause instanceof Error ? cause.message : 'Could not load this week')
    })
  }, [dashboard, week])

  if (!dashboard) {
    return error ? (
      <main className="center-screen error-state">
        <span>🛠️</span>
        <h1>We couldn’t load your chores</h1>
        <p>{error}</p>
        <button onClick={() => void load()}>Try again</button>
      </main>
    ) : (
      <LoadingScreen />
    )
  }

  const viewingDate = selectedDate || dashboard.date
  const viewingToday = viewingDate === dashboard.date
  const todayChores: DayChore[] = dashboard.chores.map((chore) => ({
    id: chore.id,
    name: chore.name,
    emoji: chore.emoji,
    day_part: chore.day_part,
    completed: chore.completed,
    points_awarded: chore.points,
    money_awarded: chore.money_reward,
    xoxos_awarded: chore.xoxo_reward,
    skip_status: chore.skip_status,
  }))
  const displayedDay = viewingToday
    ? { date: dashboard.date, chores: todayChores, completed_count: dashboard.completed_count, total_count: dashboard.total_count }
    : historicalDay
  const choreProgress = displayedDay?.total_count
    ? Math.round((displayedDay.completed_count / displayedDay.total_count) * 100)
    : 100
  const completedThisWeek = week?.days.reduce((total, day) => total + day.completed_count, 0) ?? 0
  const completedDaysThisWeek = week?.days.filter((day) => !day.future && day.total_count > 0 && day.completed_count === day.total_count).length ?? 0
  const currentWeek = Boolean(week && week.start_date <= dashboard.date && week.end_date >= dashboard.date)

  return (
    <main className="kid-shell">
      <header className="kid-header">
        <div>
          <span className="eyebrow">KIDS CHORES</span>
          <h1>{dashboard.greeting}</h1>
          <p>{dashboard.completed_count === dashboard.total_count ? 'You did it all today!' : 'Let’s make today awesome.'}</p>
        </div>
        <a className="parent-link" href="/parent" aria-label="Open parent dashboard">⚙️ Parent</a>
      </header>

      <aside className="joke-banner" aria-label="Joke of the day"><span>😄</span><div><strong>Joke of the day</strong><p>{jokeForDate(dashboard.date)}</p></div></aside>

      {notice && <div className="celebration" role="status">{notice}</div>}
      {error && <div className="inline-error" role="alert">{error}</div>}

      <section className="summary-grid" aria-label="Your totals">
        <article className="summary-card piggy-card">
          <div className="summary-icon">🐷</div>
          <div><span>Piggy Bank</span><strong>${Number(dashboard.piggy_bank_balance).toFixed(2)}</strong></div>
        </article>
        <article className="summary-card points-card">
          <div className="summary-icon">⭐</div>
          <div><span>Points</span><strong>{dashboard.points_balance.toLocaleString()}</strong></div>
        </article>
        <article className="summary-card xoxo-card">
          <div className="summary-icon">🤗</div>
          <div><span>XOXOs</span><strong>{dashboard.xoxo_balance.toLocaleString()}</strong></div>
        </article>
        <article className="summary-card streak-card">
          <div className="summary-icon">🔥</div>
          <div><span>Current streak</span><strong>{dashboard.streak_days} {dashboard.streak_days === 1 ? 'day' : 'days'}</strong></div>
        </article>
        {(['home', 'school'] as const).map((key) => {
          const place = weather.find((item) => item.key === key)
          const fallbackName = key === 'home' ? 'Home' : 'School'
          return <article className="summary-card weather-card" aria-label={`${place?.name ?? fallbackName} weather`} key={key}>
            <div className="summary-icon">{key === 'home' ? '🏠' : '🏫'}</div>
            <div className="weather-place">
              <span>{place?.name ?? fallbackName}</span>
              {place && <small>{place.location}</small>}
              {weatherBusy && <small>Checking weather…</small>}
              {!weatherBusy && weatherError && <button className="weather-button" onClick={() => void loadWeather()}>Try again</button>}
            </div>
            {place && <div className="weather-reading"><strong>{place.temperature}°</strong><small>{place.emoji} {place.label}</small><small>H {place.high}° · L {place.low}°</small></div>}
          </article>
        })}
      </section>

      {week && <section className="weekly-recap" aria-label="Weekly recap">
        <div className="recap-copy"><span>🏆</span><div><small>{currentWeek ? 'THIS WEEK SO FAR' : 'SELECTED WEEK'}</small><strong>{completedThisWeek ? `You finished ${completedThisWeek} ${completedThisWeek === 1 ? 'chore' : 'chores'}!` : 'A fresh week to begin!'}</strong></div></div>
        <div className="recap-stat"><strong>{completedThisWeek}</strong><span>chores done</span></div>
        <div className="recap-stat"><strong>{completedDaysThisWeek}</strong><span>all-done days</span></div>
      </section>}

      <div className="kid-content-grid">
        <section className="chores-panel" aria-labelledby="today-title">
          <div className="section-heading">
            <div><span className="eyebrow">{viewingToday ? 'YOUR MISSION' : 'YOUR HISTORY'}</span><h2 id="today-title">{viewingToday ? 'Today’s Chores' : readableDate(viewingDate)}</h2></div>
            {displayedDay && <div className="round-progress" style={{ '--progress': `${choreProgress * 3.6}deg` } as React.CSSProperties} aria-label={`${choreProgress}% complete`}><span>{displayedDay.completed_count}/{displayedDay.total_count}</span></div>}
          </div>
          <WeekStrip week={week} selectedDate={viewingDate} today={dashboard.date} busy={historyBusy} onSelect={(date) => void showDate(date)} />
          <div className="chore-groups">
            {historyBusy && <p className="empty-message">Loading this day…</p>}
            {!historyBusy && displayedDay?.chores.length === 0 && <p className="empty-message">No chores scheduled for this day.</p>}
            {!historyBusy && displayedDay && dayParts.map((part) => {
              const chores = displayedDay.chores.filter((chore) => (chore.day_part ?? 'after_school') === part.key)
              if (!chores.length) return null
              return <section className="day-part" aria-labelledby={`day-part-${part.key}`} key={part.key}>
                <h3 id={`day-part-${part.key}`}><span>{part.emoji}</span>{part.label}<small>{chores.filter((chore) => chore.completed).length}/{chores.filter((chore) => chore.skip_status !== 'approved').length}</small></h3>
                <div className="chore-list">{chores.map((chore) => (
                  <article className={`chore-card ${chore.completed ? 'is-complete' : ''} ${chore.skip_status === 'approved' ? 'is-skipped' : ''}`} key={chore.id}>
                    <span className="chore-emoji" aria-hidden="true">{chore.emoji}</span>
                    <div className="chore-copy"><h3>{chore.name}</h3><span>{chore.skip_status === 'rejected' ? 'Skip declined · ' : ''}{choreRewardLabel(chore)}</span></div>
                    <div className="chore-actions">
                      {!viewingToday ? <button className="done-button" disabled aria-label={chore.skip_status === 'approved' ? `${chore.name} was skipped` : chore.completed ? `${chore.name} completed` : `${chore.name} was not completed`}>{chore.skip_status === 'approved' ? 'Skipped' : chore.completed ? '✓ Done' : 'Not done'}</button>
                        : chore.completed ? <button className="done-button undo-button" disabled={busyId === chore.id} onClick={() => void undoChore(chore.id)} aria-label={`Undo ${chore.name}`}>{busyId === chore.id ? '…' : 'Undo'}</button>
                        : chore.skip_status === 'approved' ? <button className="done-button skipped-button" disabled aria-label={`${chore.name} skipped`}>Skipped</button>
                        : chore.skip_status === 'pending' ? <button className="done-button pending-skip-button" disabled aria-label={`Skip request for ${chore.name} awaiting parent approval`}>Waiting for parent</button>
                        : <>
                          <button className="done-button" disabled={busyId === chore.id} onClick={() => void finishChore(chore.id)} aria-label={`Mark ${chore.name} done`}>{busyId === chore.id ? '…' : 'Done'}</button>
                          {chore.skip_status !== 'rejected' && <button className="skip-button" disabled={busyId === chore.id} onClick={() => void requestSkip(chore.id, chore.name)} aria-label={`Request to skip ${chore.name}`}>Request skip</button>}
                        </>}
                    </div>
                  </article>
                ))}</div>
              </section>
            })}
          </div>
        </section>

        <aside className="kid-side-stack">
          {dashboard.savings_goal && (
            <section className="goal-card" aria-labelledby="goal-title">
              <div className="goal-top"><span>{dashboard.savings_goal.emoji}</span><div><small>SAVING FOR</small><h2 id="goal-title">{dashboard.savings_goal.name}</h2></div></div>
              <div className="goal-numbers"><strong>${Number(dashboard.savings_goal.current_amount).toFixed(0)}</strong><span>of ${Number(dashboard.savings_goal.target_amount).toFixed(0)}</span></div>
              <div className="progress-track"><div style={{ width: `${dashboard.savings_goal.progress_percent}%` }} /></div>
              <p>{dashboard.savings_goal.progress_percent}% there — keep going!</p>
            </section>
          )}
          <section className="points-activity-panel" aria-labelledby="points-activity-title" aria-label="Points activity">
            <div className="section-heading compact">
              <div><span className="eyebrow">YOUR POINTS</span><h2 id="points-activity-title">Why they changed</h2></div>
              <span className="activity-star" aria-hidden="true">⭐</span>
            </div>
            {dashboard.point_activity.length ? <div className="points-activity-list">
              {dashboard.point_activity.map((item) => <article className="points-activity-row" key={item.id}>
                <strong className={item.amount >= 0 ? 'points-added' : 'points-removed'}>{item.amount >= 0 ? '+' : ''}{item.amount}</strong>
                <div><p>{item.reason}</p><time dateTime={item.created_at}>{activityDate(item.created_at)}</time></div>
              </article>)}
            </div> : <p className="empty-message">Your point changes will appear here.</p>}
          </section>
          <section className="rewards-panel" aria-labelledby="rewards-title">
            <div className="section-heading compact"><div><span className="eyebrow">TREAT YOURSELF</span><h2 id="rewards-title">Rewards</h2></div>{dashboard.pending_reward_count > 0 && <span className="pending-pill">{dashboard.pending_reward_count} pending</span>}</div>
            <div className="reward-list">
              {dashboard.rewards.map((reward) => (
                <article className="reward-card" key={reward.id}>
                  <span className="reward-emoji">{reward.emoji}</span>
                  <div><h3>{reward.name}</h3><span>{reward.points_cost} ⭐</span></div>
                  <button disabled={busyId === reward.id} onClick={() => void redeem(reward.id, reward.name)}>Redeem</button>
                </article>
              ))}
            </div>
          </section>
        </aside>
      </div>
    </main>
  )
}
