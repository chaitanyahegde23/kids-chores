import type { WeekRecord } from '../api/client'

function parseDate(value: string) {
  return new Date(`${value}T12:00:00`)
}

function toIsoDate(value: Date) {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function shiftDate(value: string, days: number) {
  const date = parseDate(value)
  date.setDate(date.getDate() + days)
  return toIsoDate(date)
}

function weekLabel(week: WeekRecord) {
  const start = parseDate(week.start_date)
  const end = parseDate(week.end_date)
  const startMonth = start.toLocaleDateString(undefined, { month: 'short' })
  const endMonth = end.toLocaleDateString(undefined, { month: 'short' })
  if (start.getMonth() === end.getMonth() && start.getFullYear() === end.getFullYear()) {
    return `${startMonth} ${start.getDate()}–${end.getDate()}, ${end.getFullYear()}`
  }
  return `${startMonth} ${start.getDate()} – ${endMonth} ${end.getDate()}, ${end.getFullYear()}`
}

export function WeekStrip({ week, selectedDate, today, busy, onSelect }: { week: WeekRecord | null; selectedDate: string; today: string; busy: boolean; onSelect: (date: string) => void }) {
  const shiftWeek = (offset: number) => {
    const shifted = shiftDate(selectedDate, offset)
    onSelect(shifted > today ? today : shifted)
  }

  return (
    <div className="week-browser" aria-label="Weekly chore history">
      <div className="week-browser-heading">
        <button className="week-arrow" aria-label="Previous week" disabled={busy} onClick={() => shiftWeek(-7)}>‹</button>
        <strong>{week ? weekLabel(week) : 'Loading week…'}</strong>
        <button className="week-arrow" aria-label="Next week" disabled={busy || !week || week.end_date >= today} onClick={() => shiftWeek(7)}>›</button>
      </div>
      <div className="week-days">
        {week?.days.map((day) => {
          const date = parseDate(day.date)
          const complete = day.total_count > 0 && day.completed_count === day.total_count
          const partial = day.completed_count > 0 && !complete
          const status = day.future ? 'Future' : day.total_count === 0 ? 'No chores' : complete ? 'All done' : partial ? `${day.completed_count} of ${day.total_count} done` : 'Not done'
          return (
            <button
              key={day.date}
              className={`week-day ${day.date === selectedDate ? 'is-selected' : ''} ${day.date === today ? 'is-today' : ''} ${complete ? 'is-complete' : ''} ${partial ? 'is-partial' : ''}`}
              disabled={day.future || busy}
              onClick={() => onSelect(day.date)}
              aria-label={`${date.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}: ${status}`}
              aria-pressed={day.date === selectedDate}
            >
              <span>{date.toLocaleDateString(undefined, { weekday: 'narrow' })}</span>
              <strong>{date.getDate()}</strong>
              <i aria-hidden="true">{complete ? '✓' : partial ? day.completed_count : ''}</i>
            </button>
          )
        })}
      </div>
      <div className="jump-date-row">
        <details className="jump-date">
          <summary>Go to date</summary>
          <label>Date and year<input aria-label="Jump to date and year" type="date" max={today} value={selectedDate} onChange={(event) => onSelect(event.target.value)} /></label>
        </details>
        {selectedDate !== today && <button className="text-button" onClick={() => onSelect(today)}>Back to today</button>}
      </div>
    </div>
  )
}
