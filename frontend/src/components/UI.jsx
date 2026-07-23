import { AlertCircle, LoaderCircle, Star } from 'lucide-react'
import { formatDisplayName, getAccordColor, isDarkColor } from '../utils/display'

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

export function AccordDots({ accords = [] }) {
  return <div className="accord-dots" aria-label="Accordi principali">{accords.slice(0, 5).map((accord, index) => <span key={accord._id || index} style={{ background: getAccordColor(accord) }} title={formatDisplayName(accord.name || accord._id)} />)}</div>
}

export function AccordBadges({ accords = [], limit = 3 }) {
  const visible = accords.slice(0, limit)
  return <div className="accord-badges" aria-label="Accordi principali">
    {visible.map((accord, index) => {
      const color = getAccordColor(accord)
      return <span
        key={accord._id || index}
        className="accord-badge"
        style={{ '--accord-color': color, '--accord-text': isDarkColor(color) ? '#fff' : '#2b211c' }}
      >
        <i />{formatDisplayName(accord.name || accord._id)}
      </span>
    })}
    {accords.length > limit && <span className="accord-more">+{accords.length - limit}</span>}
  </div>
}
