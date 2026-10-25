import { useId, useMemo, useState } from 'react'
import { useNavigate } from 'react-router'
import { searchPlayers } from '../data'
import type { PlayerSummary } from '../types'

interface Props {
  players: PlayerSummary[]
  size?: 'large' | 'compact'
  autoFocus?: boolean
}

/** Player search with autocomplete. Arrow keys move, Enter opens, Escape closes. */
export default function SearchBox({ players, size = 'large', autoFocus = false }: Props) {
  const navigate = useNavigate()
  const listId = useId()
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const results = useMemo(() => searchPlayers(players, query), [players, query])
  const showList = open && query.trim() !== ''

  function choose(p: PlayerSummary) {
    setQuery('')
    setOpen(false)
    navigate(`/player/${p.id}`)
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setOpen(true)
      setActive((i) => Math.min(i + 1, results.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((i) => Math.max(i - 1, 0))
    } else if (e.key === 'Enter' && results[active]) {
      e.preventDefault()
      choose(results[active])
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  const large = size === 'large'
  return (
    <div className="relative w-full">
      <svg
        aria-hidden
        viewBox="0 0 20 20"
        className={`pointer-events-none absolute top-1/2 -translate-y-1/2 text-faint ${large ? 'left-5 size-5' : 'left-3 size-4'}`}
      >
        <path
          fill="currentColor"
          d="M8.5 3a5.5 5.5 0 0 1 4.38 8.83l3.65 3.64a.75.75 0 1 1-1.06 1.06l-3.64-3.65A5.5 5.5 0 1 1 8.5 3Zm0 1.5a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z"
        />
      </svg>
      <input
        role="combobox"
        aria-expanded={showList}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={showList && results[active] ? `${listId}-${active}` : undefined}
        aria-label="Search a player"
        // Only on larger screens: on phones it would pop up the keyboard on page load.
        autoFocus={autoFocus && window.matchMedia('(min-width: 640px)').matches}
        value={query}
        placeholder={large ? 'Search any player' : 'Search player'}
        onChange={(e) => {
          setQuery(e.target.value)
          setActive(0)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 120)}
        onKeyDown={onKeyDown}
        className={`w-full rounded-xl border border-line bg-surface text-ink placeholder:text-faint outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/30 ${
          large ? 'py-4 pr-5 pl-13 text-lg' : 'py-2 pr-3 pl-9 text-sm'
        }`}
      />
      {showList && (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-20 mt-2 w-full overflow-hidden rounded-xl border border-line bg-surface-2 shadow-2xl shadow-black/50"
        >
          {results.length === 0 && <li className="px-4 py-3 text-sm text-muted">No players found</li>}
          {results.map((p, i) => (
            <li
              key={p.id}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === active}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => choose(p)}
              onMouseEnter={() => setActive(i)}
              className={`flex cursor-pointer items-center justify-between gap-3 px-4 py-2.5 ${i === active ? 'bg-line' : ''}`}
            >
              <span className="truncate">
                <span className="font-medium">{p.name}</span>
                <span className="ml-2 text-sm text-faint">{p.team ?? 'No team'}</span>
              </span>
              <span className="tabular shrink-0 text-sm text-muted">
                {Math.round(p.shown)} {p.comeback ? 'if healthy' : 'games'}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
