import type { Factor } from '../types'

/**
 * What moves the forecast: one row per factor, label on top and a bar growing
 * right (adds games, blue) or left (costs games, red) from the center line.
 * Signs and values are printed, so color is never the only cue.
 */
export default function FactorChart({ factors }: { factors: Factor[] }) {
  const reach = Math.max(1, ...factors.map((f) => Math.abs(f.games))) * 1.15
  return (
    <div>
      <div className="mb-3 flex gap-5 text-xs text-muted">
        <span className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-sm bg-up" /> Adds games
        </span>
        <span className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-sm bg-down" /> Costs games
        </span>
      </div>
      <ul className="space-y-3.5">
        {factors.map((f) => {
          const width = `${(Math.abs(f.games) / reach) * 50}%`
          const up = f.games >= 0
          return (
            <li key={f.label}>
              <div className="flex items-baseline justify-between gap-3 text-sm">
                <span className="text-ink">
                  {f.label} <span className="text-muted">· {f.value}</span>
                </span>
                <span className={`tabular shrink-0 font-semibold ${up ? 'text-up' : 'text-down'}`}>
                  {up ? '+' : '−'}
                  {Math.abs(f.games).toFixed(1)}
                </span>
              </div>
              <div className="relative mt-1.5 h-2.5 rounded-full bg-surface-2">
                <div className="absolute inset-y-[-3px] left-1/2 w-px bg-line" />
                <div
                  className={`absolute inset-y-0 ${up ? 'left-1/2 rounded-r-full bg-up' : 'right-1/2 rounded-l-full bg-down'}`}
                  style={{ width }}
                />
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
