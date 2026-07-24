import { Link } from 'react-router-dom'

export default function NotFound() {
  return <div className="page"><div className="state-card"><span className="kicker">404</span><h1>Pagina non trovata</h1><p>La risorsa richiesta non esiste o è stata rimossa.</p><Link className="button primary" to="/">Torna alla dashboard</Link></div></div>
}
