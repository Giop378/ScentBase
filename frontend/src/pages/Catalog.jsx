import { ChevronLeft, ChevronRight, Filter, RotateCcw, Search, SlidersHorizontal } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useLocation, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import PerfumeCard from '../components/PerfumeCard'
import { EmptyState, ErrorState, Loading } from '../components/UI'
import { createReferenceMaps, enrichPerfume } from '../utils/display'

const defaults = { name: '', brand: '', gender: '', year_min: '', year_max: '', rating_min: '', rating_max: '', votes_min: '', note: '', accord: '', perfumer: '', sort_by: 'rating', sort_order: 'desc' }
const PAGE_SIZE = 12

export default function Catalog() {
  const [searchParams, setSearchParams] = useSearchParams()
  const location = useLocation()
  const [draft, setDraft] = useState(() => ({ ...defaults, ...Object.fromEntries(searchParams.entries()) }))
  const [filters, setFilters] = useState(() => ({ ...defaults, ...Object.fromEntries(searchParams.entries()) }))
  const [page, setPage] = useState(1)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [filterOpen, setFilterOpen] = useState(false)

  useEffect(() => {
    let cancelled = false

    Promise.all([
      api.perfumes({ ...filters, limit: PAGE_SIZE, skip: (page - 1) * PAGE_SIZE }),
      api.catalogReferences(),
    ])
      .then(([data, references]) => {
        if (!cancelled) {
          const maps = createReferenceMaps(references)
          setResult({ ...data, items: data.items.map((item) => enrichPerfume(item, maps)) })
          setError(null)
        }
      })
      .catch((currentError) => {
        if (!cancelled) setError(currentError)
      })

    return () => {
      cancelled = true
    }
  }, [filters, page])

  const submit = (event) => {
    event.preventDefault()
    const clean = Object.fromEntries(Object.entries(draft).filter(([, value]) => value !== ''))
    setResult(null)
    setError(null)
    setSearchParams(clean)
    setFilters({ ...defaults, ...clean })
    setPage(1)
    setFilterOpen(false)
  }

  const reset = () => {
    setResult(null)
    setError(null)
    setDraft(defaults)
    setFilters(defaults)
    setSearchParams({})
    setPage(1)
  }

  const changeSort = (key, value) => {
    const next = { ...draft, [key]: value }
    setResult(null)
    setError(null)
    setDraft(next)
    setFilters(next)
    setPage(1)
  }

  const retry = () => {
    setResult(null)
    setError(null)
    setFilters({ ...filters })
  }

  const totalPages = Math.max(Math.ceil((result?.total || 0) / PAGE_SIZE), 1)

  return <div className="page page-wide">
    {location.state?.notice && <div className="notice success-notice" role="status">{location.state.notice}</div>}
    <div className="page-title-row"><div><span className="kicker">24.000+ fragranze</span><h1>Catalogo</h1><p>Combina liberamente i criteri per trovare il profumo che cerchi.</p></div><button className="button secondary mobile-filter" onClick={() => setFilterOpen(!filterOpen)}><SlidersHorizontal size={17} /> Filtri</button></div>
    <div className="catalog-layout">
      <aside className={filterOpen ? 'filters-panel open' : 'filters-panel'}><form onSubmit={submit}>
        <div className="filter-heading"><h2><Filter size={18} /> Filtri</h2><button type="button" onClick={reset}><RotateCcw size={15} /> Azzera</button></div>
        <Field label="Nome"><input value={draft.name} onChange={e => setDraft({ ...draft, name: e.target.value })} placeholder="es. Vanilla" /></Field>
        <Field label="Brand"><input value={draft.brand} onChange={e => setDraft({ ...draft, brand: e.target.value })} placeholder="es. Dior" /></Field>
        <Field label="Genere"><select value={draft.gender} onChange={e => setDraft({ ...draft, gender: e.target.value })}><option value="">Tutti</option><option value="women">Donna</option><option value="men">Uomo</option><option value="unisex">Unisex</option></select></Field>
        <div className="field-pair"><Field label="Anno da"><input type="number" value={draft.year_min} onChange={e => setDraft({ ...draft, year_min: e.target.value })} /></Field><Field label="a"><input type="number" value={draft.year_max} onChange={e => setDraft({ ...draft, year_max: e.target.value })} /></Field></div>
        <div className="field-pair"><Field label="Rating da"><input type="number" step="0.1" min="0" max="5" value={draft.rating_min} onChange={e => setDraft({ ...draft, rating_min: e.target.value })} /></Field><Field label="a"><input type="number" step="0.1" min="0" max="5" value={draft.rating_max} onChange={e => setDraft({ ...draft, rating_max: e.target.value })} /></Field></div>
        <Field label="Voti minimi"><input type="number" min="0" value={draft.votes_min} onChange={e => setDraft({ ...draft, votes_min: e.target.value })} /></Field>
        <Field label="Nota"><input value={draft.note} onChange={e => setDraft({ ...draft, note: e.target.value })} placeholder="es. Bergamot" /></Field>
        <Field label="Accordo"><input value={draft.accord} onChange={e => setDraft({ ...draft, accord: e.target.value })} placeholder="es. Woody" /></Field>
        <Field label="Profumiere"><input value={draft.perfumer} onChange={e => setDraft({ ...draft, perfumer: e.target.value })} /></Field>
        <button className="button primary full" type="submit"><Search size={17} /> Applica filtri</button>
      </form></aside>

      <section className="catalog-results">
        <div className="results-toolbar"><div><strong>{result?.total?.toLocaleString('it-IT') || '—'}</strong><span> risultati</span></div><div className="sort-controls"><select value={draft.sort_by} onChange={e => changeSort('sort_by', e.target.value)}><option value="rating">Rating</option><option value="votes">Voti</option><option value="name">Nome</option><option value="year">Anno</option></select><select value={draft.sort_order} onChange={e => changeSort('sort_order', e.target.value)}><option value="desc">Decrescente</option><option value="asc">Crescente</option></select></div></div>
        {error ? <ErrorState error={error} onRetry={retry} /> : !result ? <Loading label="Cerchiamo nel catalogo" /> : result.items.length === 0 ? <EmptyState /> : <div className="perfume-grid">{result.items.map(p => <PerfumeCard key={p._id} perfume={p} />)}</div>}
        {result?.total > PAGE_SIZE && <div className="pagination"><button disabled={page === 1} onClick={() => { setResult(null); setPage(p => p - 1) }}><ChevronLeft /> Precedente</button><span>Pagina <strong>{page}</strong> di {totalPages}</span><button disabled={page === totalPages} onClick={() => { setResult(null); setPage(p => p + 1) }}>Successiva <ChevronRight /></button></div>}
      </section>
    </div>
  </div>
}

function Field({ label, children }) { return <label className="form-field"><span>{label}</span>{children}</label> }
