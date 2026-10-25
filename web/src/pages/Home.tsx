import { useMemo } from 'react'
import { useSearchParams } from 'react-router'
import Leaderboard from '../components/Leaderboard'
import SearchBox from '../components/SearchBox'
import { baselineText, shortDate } from '../data'
import type { Index } from '../types'

export default function Home({ index }: { index: Index }) {
  const { meta, teams, players } = index
  const [params, setParams] = useSearchParams()
  const teamAbbr = params.get('team')?.toUpperCase() ?? ''
  const team = teams.find((t) => t.abbr === teamAbbr)
  const rows = useMemo(() => (team ? players.filter((p) => p.team === team.abbr) : players), [players, team])

  return (
    <>
      <section className="pt-10 pb-8 sm:pt-16">
        <p className="text-sm font-semibold tracking-widest text-accent uppercase">
          {meta.forecastSeason} season forecasts
          {meta.seasonStarted && <span className="ml-2 text-muted">· season underway</span>}
        </p>
        <h1 className="mt-2 font-display text-5xl leading-[0.95] font-extrabold tracking-tight uppercase sm:text-7xl">
          How many games
          <br />
          will they play?
        </h1>
        <p className="mt-4 max-w-xl text-muted">
          A machine-learning forecast of games played for every NBA player this season, made before opening night, with
          the reasons behind each number.
          {meta.seasonStarted && meta.soFarThrough && (
            <> Games so far are updated through {shortDate(meta.soFarThrough)}.</>
          )}
        </p>
        <div className="mt-8 max-w-2xl">
          <SearchBox players={players} autoFocus />
        </div>
        <dl className="mt-8 grid max-w-2xl gap-px overflow-hidden rounded-xl border border-line bg-line sm:grid-cols-3">
          <Stat value={players.length.toString()} label="players forecast" />
          <Stat
            value={meta.accuracy.modelMae.toFixed(1)}
            unit="games"
            label="our average miss"
            note={`Half our forecasts land within ${Math.round(meta.accuracy.modelMedianError)} games`}
            accent
          />
          <Stat
            value={meta.accuracy.bestBaselineMae.toFixed(1)}
            unit="games"
            label={`average miss ${baselineText(meta.accuracy.bestBaseline)}`}
          />
        </dl>
      </section>

      <section className="pb-16">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <h2 className="font-display text-3xl font-bold uppercase">{team ? team.name : 'All players'}</h2>
          <label className="flex items-center gap-2 text-sm text-muted">
            Team
            <select
              value={team?.abbr ?? ''}
              onChange={(e) => setParams(e.target.value ? { team: e.target.value } : {})}
              className="rounded-lg border border-line bg-surface px-3 py-2 text-ink outline-none focus:border-accent"
            >
              <option value="">All teams</option>
              {teams.map((t) => (
                <option key={t.abbr} value={t.abbr}>
                  {t.name}
                </option>
              ))}
            </select>
          </label>
        </div>
        <Leaderboard
          key={team?.abbr ?? 'all'}
          players={rows}
          dataThrough={meta.dataThrough}
          forecastSeason={meta.forecastSeason}
          seasonStarted={meta.seasonStarted}
          showTeam={!team}
        />
        {team && team.noForecast.length > 0 && (
          <p className="mt-3 text-sm text-faint">
            No forecast yet: {team.noForecast.join(', ')}. Forecasts need NBA games in {meta.previousSeason} or{' '}
            {meta.dataThrough}, so rookies aren't included.
          </p>
        )}
      </section>
    </>
  )
}

function Stat({ value, unit, label, note, accent = false }: { value: string; unit?: string; label: string; note?: string; accent?: boolean }) {
  return (
    <div className="flex flex-col bg-surface px-4 py-4">
      <dd className="flex items-baseline gap-1.5">
        <span className={`tabular font-display text-3xl font-bold ${accent ? 'text-accent' : ''}`}>{value}</span>
        {unit && <span className="text-sm text-muted">{unit}</span>}
      </dd>
      <dt className="order-last mt-0.5 text-sm text-ink">{label}</dt>
      {note && <dd className="order-last mt-1 text-xs text-faint">{note}</dd>}
    </div>
  )
}
