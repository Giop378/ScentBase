import { ArrowUpRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { AccordDots, Rating } from './UI'

export default function PerfumeCard({ perfume }) {
  const brand = perfume.brand?.name || perfume.brand_name || perfume.brand_id || 'Brand non disponibile'
  return (
    <article className="perfume-card">
      <div className="bottle-art" aria-hidden="true"><div className="bottle-cap" /><div className="bottle-body"><span>{perfume.name?.slice(0, 1)}</span></div></div>
      <div className="perfume-card-content">
        <div className="eyebrow-row"><span>{brand}</span><span>{perfume.gender || '—'}</span></div>
        <h3>{perfume.name}</h3>
        <div className="card-meta"><span>{perfume.year || 'Anno n.d.'}</span><Rating value={perfume.rating} votes={perfume.votes} /></div>
        <div className="card-bottom"><AccordDots accords={perfume.accords} ids={perfume.accord_ids} /><Link to={`/profumi/${encodeURIComponent(perfume._id)}`} aria-label={`Apri ${perfume.name}`}><ArrowUpRight /></Link></div>
      </div>
    </article>
  )
}
