import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { AccordBadges, Rating } from './UI'
import { formatDisplayName, formatGender, getAccordColor } from '../utils/display'

export default function PerfumeCard({ perfume }) {
  const brand = formatDisplayName(perfume.brand?.name || perfume.brand_name || perfume.brand_id)
  const name = formatDisplayName(perfume.name)
  const accords = perfume.accords || []
  const primaryColor = getAccordColor(accords[0], '#B98A72')
  const secondaryColor = getAccordColor(accords[1], '#D6B7A3')
  const cardStyle = {
    '--primary-accord': primaryColor,
    '--secondary-accord': secondaryColor,
  }

  return (
    <article className="perfume-card" style={cardStyle}>
      <div className="bottle-art" aria-hidden="true">
        <div className="bottle-glow" />
        <div className="bottle-cap" />
        <div className="bottle-body">
          <div className="bottle-liquid" />
          <span>{name.slice(0, 1).toLocaleUpperCase('it-IT')}</span>
        </div>
      </div>
      <div className="perfume-card-content">
        <div className="eyebrow-row">
          <span className="brand-name">{brand}</span>
          <span className="gender-badge">{formatGender(perfume.gender)}</span>
        </div>
        <h3 title={name}>{name}</h3>
        <div className="card-meta">
          <span>{perfume.year || 'Anno n.d.'}</span>
          <Rating value={perfume.rating} votes={perfume.votes} />
        </div>
        <AccordBadges accords={accords} />
        <Link className="details-link" to={`/profumi/${encodeURIComponent(perfume._id)}`} aria-label={`Apri ${name}`}>
          Dettagli <ArrowRight size={16} />
        </Link>
      </div>
    </article>
  )
}
