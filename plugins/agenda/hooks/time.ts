import type { Labels } from './labels'

const pad = (n: number): string => String(n).padStart(2, '0')

/** Minutes east of UTC from a trailing `±HH:MM` or `Z`; undefined when absent. */
export function parseOffset(text: string): number | undefined {
  if (/Z$/.test(text)) return 0
  const m = /([+-])(\d{2}):(\d{2})$/.exec(text)
  if (!m) return undefined
  const minutes = Number(m[2]) * 60 + Number(m[3])
  return m[1] === '-' ? -minutes : minutes
}

/** Local date and wall time of an instant at the given offset. */
export function localParts(nowMs: number, offsetMin: number): { date: string; time: string } {
  const d = new Date(nowMs + offsetMin * 60000)
  return {
    date: `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}`,
    time: `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`,
  }
}

/** `gio 29 ott` for a `YYYY-MM-DD` date. */
export function dayLabel(date: string, labels: Labels): string {
  const [y = 0, m = 1, d = 1] = date.split('-').map(Number)
  const weekday = new Date(Date.UTC(y, m - 1, d)).getUTCDay()
  return `${labels.days[weekday]} ${d} ${labels.months[m - 1]}`
}

/** `HH:MM` as written in an ISO string (already local). */
export function wallTime(iso: string): string {
  return iso.slice(11, 16)
}

/** Milliseconds from `nowMs` to the next full minute (60000 when already on it). */
export function msToNextMinute(nowMs: number): number {
  return 60000 - (nowMs % 60000)
}
