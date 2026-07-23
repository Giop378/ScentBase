import { ArrowRight, Database, FlaskConical, Layers3, Sparkles, Tags } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import PerfumeCard from '../components/PerfumeCard'
import { ErrorState, Loading } from '../components/UI'

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  const load = () => {
    setError(null)
    setData(null)
    Promise.all([api.counts(), api.topPerfumes(4), api.brandStats(7), api.noteStats(8)])
      .then(([counts, top, brands, notes]) => setData({ counts, top: top.items, brands: brands.items, notes: notes.items }))
      .catch(setError)
  }

  useEffect(load, [])

  if (error) return <Page><ErrorState error={error} onRetry={load} /></Page>
  if (!data) return <Page><Loading label="Prepariamo la panoramica olfattiva" /></Page>

  const counts = data.counts?.collections || data.counts
  const maxNote = Math.max(...data.notes.map((item) => item.perfume_count || item.count || 1), 1)

  return <Page>
    <section className="hero">
      <div><span className="kicker">Archivio olfattivo digitale</span><h1>Esplora il linguaggio dei profumi.</h1><p>Un catalogo NoSQL di fragranze, note, accordi e profumieri, progettato per essere interrogato e analizzato.</p><div className="hero-actions"><Link className="button primary" to="/catalogo">Esplora il catalogo <ArrowRight size={17} /></Link><Link className="button ghost" to="/profumi/nuovo">Aggiungi un profumo</Link></div></div>
      <div className="hero-visual"><div className="halo halo-one" /><div className="halo halo-two" /><div className="hero-bottle"><div /><span>S</span></div></div>
    </section>

    <section className="stats-grid">
      <Stat icon={FlaskConical} label="Profumi" value={counts?.perfumes} />
      <Stat icon={Tags} label="Brand" value={counts?.brands} />
      <Stat icon={Sparkles} label="Note" value={counts?.notes} />
      <Stat icon={Layers3} label="Accordi" value={counts?.accords} />
      <Stat icon={Database} label="Profumieri" value={counts?.perfumers} />
    </section>

    <Section title="Fragranze in evidenza" subtitle="Le migliori valutazioni con almeno 100 voti" action={<Link to="/catalogo?sort_by=rating&sort_order=desc">Vedi catalogo <ArrowRight size={16} /></Link>}>
      <div className="perfume-grid compact">{data.top.map((item) => <PerfumeCard key={item._id} perfume={item} />)}</div>
    </Section>

    <div className="analytics-grid">
      <Section title="Brand più apprezzati" subtitle="Rating medio e ampiezza del catalogo"><div className="rank-list">{data.brands.map((item, i) => <div className="rank-row" key={item.brand_id || item._id || i}><span className="rank-number">{String(i + 1).padStart(2, '0')}</span><div><strong>{item.brand?.name || item.brand_name || item.name || item.brand_id}</strong><small>{item.perfume_count || item.count} profumi</small></div><b>{Number(item.average_rating || item.avg_rating || 0).toFixed(2)}</b></div>)}</div></Section>
      <Section title="Note più frequenti" subtitle="Presenza nel catalogo completo"><div className="bar-chart">{data.notes.map((item) => { const value = item.perfume_count || item.count || 0; return <div className="bar-row" key={item.note_id || item._id}><div><span>{item.note?.name || item.note_name || item.name || item.note_id}</span><b>{value.toLocaleString('it-IT')}</b></div><div className="bar-track"><span style={{ width: `${Math.max((value / maxNote) * 100, 3)}%` }} /></div></div> })}</div></Section>
    </div>
  </Page>
}

function Page({ children }) { return <div className="page page-wide">{children}</div> }
function Stat({ icon: Icon, label, value }) { return <article className="stat-card"><Icon /><div><strong>{Number(value || 0).toLocaleString('it-IT')}</strong><span>{label}</span></div></article> }
function Section({ title, subtitle, action, children }) { return <section className="section-block"><div className="section-heading"><div><span className="kicker">ScentBase insights</span><h2>{title}</h2><p>{subtitle}</p></div>{action}</div>{children}</section> }
