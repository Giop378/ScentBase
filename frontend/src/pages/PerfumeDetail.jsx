import { ArrowLeft, Edit3, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import PerfumeCard from '../components/PerfumeCard'
import { AccordBadges, AccordDots, ErrorState, Loading, Rating } from '../components/UI'
import { createReferenceMaps, enrichPerfume, formatDisplayName, formatGender, getAccordColor } from '../utils/display'

export default function PerfumeDetail() {
  const { id } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const [requestKey, setRequestKey] = useState(0)
  const [data, setData] = useState(null)
  const [similar, setSimilar] = useState([])
  const [error, setError] = useState(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    let cancelled = false

    Promise.all([api.details(id), api.similar(id, 4), api.catalogReferences()])
      .then(([detail, sim, references]) => {
        if (!cancelled) {
          const maps = createReferenceMaps(references)
          setData(enrichPerfume(detail, maps))
          setSimilar((sim.items || []).map((item) => enrichPerfume(item, maps)))
          setError(null)
        }
      })
      .catch((currentError) => {
        if (!cancelled) setError(currentError)
      })

    return () => {
      cancelled = true
    }
  }, [id, requestKey])

  const retry = () => {
    setData(null)
    setSimilar([])
    setError(null)
    setRequestKey((value) => value + 1)
  }

  const remove = async () => {
    if (!window.confirm(`Eliminare definitivamente “${formatDisplayName(data.name)}”?`)) return
    setDeleting(true)
    try {
      await api.deletePerfume(id)
      navigate('/catalogo', { state: { notice: 'Profumo eliminato correttamente.' } })
    } catch (currentError) {
      setError(currentError)
      setDeleting(false)
    }
  }

  if (error) return <div className="page"><ErrorState error={error} onRetry={retry} /></div>
  if (!data) return <div className="page"><Loading label="Ricostruiamo il profilo olfattivo" /></div>

  const brand = formatDisplayName(data.brand?.name || data.brand_id)
  const name = formatDisplayName(data.name)
  const primaryColor = getAccordColor(data.accords?.[0], '#B98A72')
  const secondaryColor = getAccordColor(data.accords?.[1], '#D6B7A3')

  return <div className="page page-wide detail-page">
    {location.state?.notice && <div className="notice success-notice" role="status">{location.state.notice}</div>}
    <Link className="back-link" to="/catalogo"><ArrowLeft size={16} /> Torna al catalogo</Link>
    <section className="detail-hero" style={{ '--primary-accord': primaryColor, '--secondary-accord': secondaryColor }}>
      <div className="detail-bottle"><div className="bottle-art large"><div className="bottle-glow" /><div className="bottle-cap" /><div className="bottle-body"><div className="bottle-liquid" /><span>{name.slice(0, 1)}</span></div></div><AccordDots accords={data.accords} /></div>
      <div className="detail-copy"><span className="kicker">{brand}</span><h1>{name}</h1><div className="detail-meta"><Rating value={data.rating} votes={data.votes} /><span>{formatGender(data.gender)}</span><span>{data.year || 'Anno n.d.'}</span></div>{data.description && <p className="lead">{data.description}</p>}<div className="detail-actions"><Link className="button primary" to={`/profumi/${encodeURIComponent(id)}/modifica`}><Edit3 size={17} /> Modifica</Link><button className="button danger" disabled={deleting} onClick={remove}><Trash2 size={17} /> {deleting ? 'Eliminazione…' : 'Elimina'}</button></div></div>
    </section>

    <section className="olfactory-grid"><NoteGroup title="Note di testa" subtitle="L'apertura" items={data.top_notes} ids={data.top_note_ids} /><NoteGroup title="Note di cuore" subtitle="Il carattere" items={data.middle_notes} ids={data.middle_note_ids} /><NoteGroup title="Note di fondo" subtitle="La persistenza" items={data.base_notes} ids={data.base_note_ids} /></section>

    <div className="detail-info-grid">
      <section className="info-panel"><span className="kicker">Accordi principali</span><h2>Firma olfattiva</h2><AccordBadges accords={data.accords || []} limit={12} /></section>
      <section className="info-panel"><span className="kicker">Nasi creatori</span><h2>Profumieri</h2><div className="tag-cloud">{(data.perfumers || []).length ? data.perfumers.map(p => <span key={p._id}>{formatDisplayName(p.name)}</span>) : <p>Non disponibili.</p>}</div></section>
    </div>

    {similar.length > 0 && <section className="section-block"><div className="section-heading"><div><span className="kicker">Jaccard similarity</span><h2>Profumi simili</h2><p>Selezionati attraverso note e accordi condivisi.</p></div></div><div className="perfume-grid compact">{similar.map(p => <PerfumeCard key={p._id} perfume={p} />)}</div></section>}
  </div>
}

function NoteGroup({ title, subtitle, items = [], ids = [] }) {
  const source = items.length ? items : ids.map(id => ({ _id: id, name: id }))
  return <section className="note-panel"><small>{subtitle}</small><h2>{title}</h2><div className="tag-cloud">{source.length ? source.map(n => <span key={n._id}>{formatDisplayName(n.name)}</span>) : <p>Non disponibili.</p>}</div></section>
}
