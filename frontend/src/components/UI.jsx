import { AlertCircle, LoaderCircle, Star } from 'lucide-react'

export function Loading({ label = 'Caricamento in corso' }) {
  return <div className="state-card"><LoaderCircle className="spin" /><p>{label}</p></div>
}

export function ErrorState({ error, onRetry }) {
  return <div className="state-card error-state"><AlertCircle /><h3>Qualcosa non ha funzionato</h3><p>{error?.message || 'Errore inatteso'}</p>{onRetry && <button className="button secondary" onClick={onRetry}>Riprova</button>}</div>
}

export function EmptyState({ title = 'Nessun risultato', text = 'Prova a modificare i filtri applicati.' }) {
  return <div className="state-card"><div className="empty-orbit" /><h3>{title}</h3><p>{text}</p></div>
}

export function Rating({ value, votes }) {
  return <span className="rating"><Star size={15} fill="currentColor" />{value ?? '—'}{votes != null && <small>{Number(votes).toLocaleString('it-IT')} voti</small>}</span>
}

export function AccordDots({ accords = [], ids = [] }) {
  const source = accords.length ? accords : ids.map((id) => ({ _id: id }))
  return <div className="accord-dots" aria-label="Accordi principali">{source.slice(0, 5).map((accord, index) => <span key={accord._id || index} style={{ background: accord.hex_color || accord.color || fallbackColor(accord._id || String(index)) }} title={accord.name || accord._id} />)}</div>
}

function fallbackColor(seed = '') {
  const palette = ['#b56d5d', '#d6a767', '#7f8e6a', '#7b6b8d', '#a98c72', '#557d7a']
  return palette[[...seed].reduce((sum, c) => sum + c.charCodeAt(0), 0) % palette.length]
}
