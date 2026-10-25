// Shapes of the JSON written by `python -m next82.export` into public/data/.

export interface Accuracy {
  modelMae: number
  bestBaseline: string
  bestBaselineMae: number
  comebackHealthyMae: number
  testSeasons: [string, string]
}

export interface Meta {
  forecastSeason: string
  dataThrough: string
  previousSeason: string
  latestFinishedSeason: string
  rostersAsOf: string | null
  /** The forecast season is underway (games so far are available). */
  seasonStarted: boolean
  /** Date of the latest game counted in "so far" numbers. */
  soFarThrough: string | null
  generatedAt: string
  games: number
  setbackGames: number
  accuracy: Accuracy
}

export interface Team {
  abbr: string
  name: string
  /** Rostered players without a forecast (mostly rookies). */
  noForecast: string[]
}

export interface PlayerSummary {
  id: number
  name: string
  /** Lowercase, accent-free name for search. */
  search: string
  /** Current team, or null if not on a roster. */
  team: string | null
  lastTeam: string
  age: number
  games: number
  seasonGames: number
  /** Returning from a missed season: show ifHealthy + setbackChance instead of forecast. */
  comeback: boolean
  forecast: number
  ifHealthy: number | null
  setbackChance: number | null
  /** The number to display and sort by: ifHealthy for comebacks, forecast otherwise. */
  shown: number
  /** Minutes in the last season played; used to rank search suggestions. */
  recentMinutes: number
  /** Games played so far this season, and the player's current team's games so far. */
  playedSoFar: number | null
  teamGamesSoFar: number | null
}

export interface Factor {
  label: string
  value: string
  /** Effect on the forecast, in games. */
  games: number
}

export interface SeasonGames {
  season: string
  games: number
  seasonGames: number
  missed: boolean
}

export interface SimilarComeback {
  name: string
  seasonMissed: string
  age: number
  before: string
  comebackGames: number
}

export interface PlayerDetail extends PlayerSummary {
  teamName: string | null
  /** Average forecast the factors start from, in games. */
  factorBase: number
  factors: Factor[]
  history: SeasonGames[]
  similar: SimilarComeback[]
}

export interface Index {
  meta: Meta
  teams: Team[]
  players: PlayerSummary[]
}
