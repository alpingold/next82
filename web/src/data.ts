import { useEffect, useState } from 'react'
import type { Index, PlayerDetail, PlayerSummary } from './types'

let indexPromise: Promise<Index> | null = null

/** The index (meta, teams, player summaries), fetched once and shared. */
export function useIndex(): Index | null {
  const [index, setIndex] = useState<Index | null>(null)
  useEffect(() => {
    indexPromise ??= fetch('/data/index.json').then((r) => r.json())
    indexPromise.then(setIndex)
  }, [])
  return index
}

/** One player's details. `undefined` while loading, `null` if not found. */
export function usePlayer(id: number): PlayerDetail | null | undefined {
  // Results are stored with the id they belong to, so switching players shows
  // "loading" straight away instead of the previous player's data.
  const [loaded, setLoaded] = useState<{ id: number; player: PlayerDetail | null } | null>(null)
  useEffect(() => {
    let current = true
    fetch(`/data/players/${id}.json`)
      .then((r) => (r.ok ? r.json() : null))
      .catch(() => null)
      .then((player) => current && setLoaded({ id, player }))
    return () => {
      current = false
    }
  }, [id])
  return loaded?.id === id ? loaded.player : undefined
}

/** Lowercase, accent-free text so "jokic" matches "Jokić". */
export function plain(text: string): string {
  return text.normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase()
}

/**
 * Players matching a search, most likely first: names with a word starting with
 * the query ("james" -> LeBron James, James Harden), then names containing it
 * anywhere. Within each group, players with more recent minutes (better known)
 * come first.
 */
export function searchPlayers(players: PlayerSummary[], query: string, limit = 8): PlayerSummary[] {
  const q = plain(query.trim())
  if (!q) return []
  const scored: [number, PlayerSummary][] = []
  for (const p of players) {
    const wordStart = p.search.startsWith(q) || p.search.split(' ').some((w) => w.startsWith(q))
    const tier = wordStart ? 0 : p.search.includes(q) ? 1 : -1
    if (tier >= 0) scored.push([tier, p])
  }
  scored.sort((a, b) => a[0] - b[0] || b[1].recentMinutes - a[1].recentMinutes)
  return scored.slice(0, limit).map(([, p]) => p)
}

/** Start year of the latest finished regular season (finished from May 1). */
export function latestFinishedSeason(today = new Date()): string {
  const start = today.getMonth() >= 4 ? today.getFullYear() - 1 : today.getFullYear() - 2
  return `${start}-${String(start + 1).slice(-2)}`
}

export function playedText(games: number, seasonGames: number): string {
  return `${games} of ${seasonGames}${games > seasonGames ? ' (traded)' : ''}`
}
