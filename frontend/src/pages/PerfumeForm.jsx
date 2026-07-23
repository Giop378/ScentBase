import { ArrowLeft, Check, Plus, Save, Search, X } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { ErrorState, Loading } from '../components/UI'
import { formatDisplayName, getAccordColor } from '../utils/display'

const empty = {
  name: '',
  brand_id: '',
  gender: 'unisex',
  rating: '',
  votes: '',
  year: '',
  top_note_ids: [],
  middle_note_ids: [],
  base_note_ids: [],
  accord_ids: [],
  perfumer_ids: [],
  source_url: '',
}

const arrayFields = ['top_note_ids', 'middle_note_ids', 'base_note_ids', 'accord_ids', 'perfumer_ids']

function normalizeSearch(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLocaleLowerCase('it-IT')
    .replace(/[-_]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function optionLabel(option) {
  return formatDisplayName(option?.name || option?._id)
}

export default function PerfumeForm() {
  const { id } = useParams()
  const edit = Boolean(id)
  const navigate = useNavigate()
  const [form, setForm] = useState(empty)
  const [references, setReferences] = useState(null)
  const [brandSearch, setBrandSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [fieldErrors, setFieldErrors] = useState({})
  const [requestKey, setRequestKey] = useState(0)

  if (loading && !references) {
    Promise.all([
      api.catalogReferences(),
      edit ? api.perfume(id) : Promise.resolve(null),
    ])
      .then(([referenceData, perfume]) => {
        setReferences(referenceData)
        if (perfume) {
          const normalized = { ...empty, ...perfume }
          arrayFields.forEach((field) => { normalized[field] = perfume[field] || [] })
          normalized.rating ??= ''
          normalized.votes ??= ''
          normalized.year ??= ''
          normalized.source_url ??= ''
          setForm(normalized)
          const brand = (referenceData.brands || []).find((item) => item._id === perfume.brand_id)
          setBrandSearch(brand ? optionLabel(brand) : '')
        }
        setError(null)
      })
      .catch(setError)
      .finally(() => setLoading(false))
  }

  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }))

  const validate = () => {
    const next = {}
    if (!form.name.trim()) next.name = 'Il nome è obbligatorio.'
    if (!form.brand_id) next.brand_id = 'Seleziona un brand esistente.'
    if (form.rating !== '' && (+form.rating < 0 || +form.rating > 5)) next.rating = 'Il rating deve essere tra 0 e 5.'
    if (form.votes !== '' && (!Number.isInteger(+form.votes) || +form.votes < 0)) next.votes = 'I voti devono essere un numero intero non negativo.'
    if (form.year !== '' && (!Number.isInteger(+form.year) || +form.year < 0 || +form.year > 2100)) next.year = 'Inserisci un anno valido.'
    setFieldErrors(next)
    return Object.keys(next).length === 0
  }

  const submit = async (event) => {
    event.preventDefault()
    if (!validate()) return
    setSaving(true)
    setError(null)
    const payload = {
      name: form.name,
      brand_id: form.brand_id,
      gender: form.gender,
      rating: form.rating === '' ? null : Number(form.rating),
      votes: form.votes === '' ? null : Number(form.votes),
      year: form.year === '' ? null : Number(form.year),
      source_url: form.source_url.trim() || null,
      top_note_ids: form.top_note_ids,
      middle_note_ids: form.middle_note_ids,
      base_note_ids: form.base_note_ids,
      accord_ids: form.accord_ids,
      perfumer_ids: form.perfumer_ids,
    }
    try {
      const saved = edit ? await api.updatePerfume(id, payload) : await api.createPerfume(payload)
      navigate(`/profumi/${encodeURIComponent(saved._id)}`, {
        state: { notice: edit ? 'Profumo modificato correttamente.' : 'Profumo creato correttamente.' },
      })
    } catch (currentError) {
      setError(currentError)
    } finally {
      setSaving(false)
    }
  }

  const retry = () => {
    setLoading(true)
    setReferences(null)
    setError(null)
    setRequestKey((value) => value + 1)
  }

  void requestKey

  if (loading) return <div className="page"><Loading label="Prepariamo il modulo" /></div>
  if (error && !references) return <div className="page"><ErrorState error={error} onRetry={retry} /></div>

  const setBrandQuery = (value) => {
    setBrandSearch(value)
    const normalizedValue = normalizeSearch(value)
    const exact = (references.brands || []).find((option) => normalizeSearch(optionLabel(option)) === normalizedValue)
    update('brand_id', exact?._id || '')
  }

  return <div className="page form-page">
    <Link className="back-link" to={edit ? `/profumi/${encodeURIComponent(id)}` : '/catalogo'}><ArrowLeft size={16} /> Indietro</Link>
    <div className="page-title-row"><div><span className="kicker">Operazione CRUD</span><h1>{edit ? 'Modifica profumo' : 'Nuovo profumo'}</h1><p>Inserisci i dati leggibili: gli identificativi MongoDB vengono gestiti automaticamente.</p></div></div>
    {error && <ErrorState error={error} />}
    <form className="editor-form" onSubmit={submit}>
      <section>
        <h2>Informazioni principali</h2>
        <p className="form-help">I campi contrassegnati con * sono obbligatori. Tutti gli altri possono essere lasciati vuoti.</p>
        <div className="form-grid">
          <Field label="Nome *" error={fieldErrors.name} hint="Nome leggibile della fragranza.">
            <input value={form.name} onChange={(event) => update('name', event.target.value)} placeholder="Es. ScentBase Aurora" />
          </Field>
          <Field label="Brand *" error={fieldErrors.brand_id} hint="Scrivi anche solo una parte del nome e seleziona il risultato.">
            <SingleReferencePicker
              options={references.brands || []}
              value={brandSearch}
              onChange={setBrandQuery}
              onSelect={(option) => { setBrandSearch(optionLabel(option)); update('brand_id', option._id) }}
              placeholder="Cerca un brand, es. Dior"
            />
          </Field>
          <Field label="Genere">
            <select value={form.gender} onChange={(event) => update('gender', event.target.value)}><option value="unisex">Unisex</option><option value="women">Donna</option><option value="men">Uomo</option></select>
          </Field>
          <Field label="Anno" error={fieldErrors.year} hint="Opzionale, tra 0 e 2100.">
            <input type="number" min="0" max="2100" value={form.year} onChange={(event) => update('year', event.target.value)} placeholder="Es. 2026" />
          </Field>
          <Field label="Rating" error={fieldErrors.rating} hint="Opzionale, da 0 a 5.">
            <input type="number" step="0.1" min="0" max="5" value={form.rating} onChange={(event) => update('rating', event.target.value)} placeholder="Es. 4.2" />
          </Field>
          <Field label="Voti" error={fieldErrors.votes} hint="Opzionale, numero intero non negativo.">
            <input type="number" min="0" step="1" value={form.votes} onChange={(event) => update('votes', event.target.value)} placeholder="Es. 125" />
          </Field>
          <Field label="Source URL" wide hint="Opzionale. Deve essere un URL completo e univoco se inserito.">
            <input type="url" value={form.source_url} onChange={(event) => update('source_url', event.target.value)} placeholder="https://example.com/profumo" />
          </Field>
        </div>
      </section>

      <section>
        <h2>Profilo olfattivo</h2>
        <p className="form-help">Cerca i valori per nome e selezionali. Note, accordi e profumieri sono tutti opzionali.</p>
        <div className="form-grid">
          <Field label="Note di testa" wide hint="Opzionale. Puoi selezionare più note.">
            <MultiReferencePicker options={references.notes || []} value={form.top_note_ids} onChange={(value) => update('top_note_ids', value)} placeholder="Cerca una nota di testa, es. Bergamot" />
          </Field>
          <Field label="Note di cuore" wide hint="Opzionale. Puoi selezionare più note.">
            <MultiReferencePicker options={references.notes || []} value={form.middle_note_ids} onChange={(value) => update('middle_note_ids', value)} placeholder="Cerca una nota di cuore, es. Jasmine" />
          </Field>
          <Field label="Note di fondo" wide hint="Opzionale. Puoi selezionare più note.">
            <MultiReferencePicker options={references.notes || []} value={form.base_note_ids} onChange={(value) => update('base_note_ids', value)} placeholder="Cerca una nota di fondo, es. Vanilla" />
          </Field>
          <Field label="Accordi" wide hint="Opzionale. I colori associati provengono da color_hex.">
            <MultiReferencePicker options={references.accords || []} value={form.accord_ids} onChange={(value) => update('accord_ids', value)} placeholder="Cerca un accordo, es. Woody" colored />
          </Field>
          <Field label="Profumieri" wide hint="Opzionale. Il profumo può essere salvato anche senza profumiere.">
            <MultiReferencePicker options={references.perfumers || []} value={form.perfumer_ids} onChange={(value) => update('perfumer_ids', value)} placeholder="Cerca un profumiere, es. Alberto Morillas" />
          </Field>
        </div>
      </section>
      <div className="form-actions"><button className="button primary" disabled={saving}><Save size={17} />{saving ? 'Salvataggio…' : edit ? 'Salva modifiche' : 'Crea profumo'}</button></div>
    </form>
  </div>
}

function SingleReferencePicker({ options, value, onChange, onSelect, placeholder }) {
  const [open, setOpen] = useState(false)
  const query = normalizeSearch(value)
  const matches = options
    .filter((option) => !query || normalizeSearch(optionLabel(option)).includes(query))
    .slice(0, 10)

  return <div className="reference-picker single-picker">
    <div className="picker-input"><Search size={16} /><input value={value} onChange={(event) => { onChange(event.target.value); setOpen(true) }} onFocus={() => setOpen(true)} onBlur={() => window.setTimeout(() => setOpen(false), 120)} placeholder={placeholder} autoComplete="off" />{value && <button type="button" aria-label="Svuota brand" onMouseDown={(event) => event.preventDefault()} onClick={() => onChange('')}><X size={15} /></button>}</div>
    {open && matches.length > 0 && <div className="picker-menu">{matches.map((option) => <button type="button" key={option._id} onMouseDown={(event) => event.preventDefault()} onClick={() => { onSelect(option); setOpen(false) }}><span>{optionLabel(option)}</span><Check size={14} /></button>)}</div>}
    {open && value && matches.length === 0 && <div className="picker-menu empty-picker">Nessun risultato.</div>}
  </div>
}

function MultiReferencePicker({ options, value, onChange, placeholder, colored = false }) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const optionMap = new Map(options.map((option) => [option._id, option]))
  const selected = value.map((id) => optionMap.get(id)).filter(Boolean)
  const normalizedQuery = normalizeSearch(query)
  const matches = options
    .filter((option) => !value.includes(option._id))
    .filter((option) => !normalizedQuery || normalizeSearch(optionLabel(option)).includes(normalizedQuery))
    .slice(0, 10)

  const add = (option) => {
    onChange([...value, option._id])
    setQuery('')
    setOpen(false)
  }

  const remove = (id) => onChange(value.filter((item) => item !== id))

  return <div className="reference-picker multi-picker">
    {selected.length > 0 && <div className="selected-references">{selected.map((option) => <span key={option._id} style={colored ? { '--selected-color': getAccordColor(option) } : undefined}>{colored && <i />} {optionLabel(option)}<button type="button" aria-label={`Rimuovi ${optionLabel(option)}`} onClick={() => remove(option._id)}><X size={13} /></button></span>)}</div>}
    <div className="picker-input"><Search size={16} /><input value={query} onChange={(event) => { setQuery(event.target.value); setOpen(true) }} onFocus={() => setOpen(true)} onBlur={() => window.setTimeout(() => setOpen(false), 120)} onKeyDown={(event) => { if (event.key === 'Enter' && matches[0]) { event.preventDefault(); add(matches[0]) } }} placeholder={placeholder} autoComplete="off" /><Plus size={15} /></div>
    {open && matches.length > 0 && <div className="picker-menu">{matches.map((option) => <button type="button" key={option._id} onMouseDown={(event) => event.preventDefault()} onClick={() => add(option)}><span>{colored && <i style={{ background: getAccordColor(option) }} />}{optionLabel(option)}</span><Plus size={14} /></button>)}</div>}
    {open && query && matches.length === 0 && <div className="picker-menu empty-picker">Nessun risultato.</div>}
  </div>
}

function Field({ label, error, hint, wide, children }) {
  return <label className={`form-field ${wide ? 'wide' : ''}`}><span>{label}</span>{children}{hint && <small className="field-hint">{hint}</small>}{error && <small className="field-error">{error}</small>}</label>
}
