import { ArrowLeft, Save } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { ErrorState, Loading } from '../components/UI'

const empty = { name: '', brand_id: '', gender: 'unisex', rating: '', votes: '', year: '', top_note_ids: '', middle_note_ids: '', base_note_ids: '', accord_ids: '', perfumer_ids: '', source_url: '' }
const arrayFields = ['top_note_ids', 'middle_note_ids', 'base_note_ids', 'accord_ids', 'perfumer_ids']
const splitIds = (value) => value.split(',').map(v => v.trim()).filter(Boolean)

export default function PerfumeForm() {
  const { id } = useParams()
  const edit = Boolean(id)
  const navigate = useNavigate()
  const [form, setForm] = useState(empty)
  const [loading, setLoading] = useState(edit)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [fieldErrors, setFieldErrors] = useState({})

  useEffect(() => {
    if (!edit) return
    api.perfume(id).then(data => {
      const normalized = { ...empty, ...data }
      arrayFields.forEach(field => { normalized[field] = (data[field] || []).join(', ') })
      normalized.rating ??= ''
      normalized.votes ??= ''
      normalized.year ??= ''
      normalized.source_url ??= ''
      setForm(normalized)
    }).catch(setError).finally(() => setLoading(false))
  }, [edit, id])

  const update = (key, value) => setForm(current => ({ ...current, [key]: value }))

  const validate = () => {
    const next = {}
    if (!form.name.trim()) next.name = 'Il nome è obbligatorio.'
    if (!form.brand_id.trim()) next.brand_id = 'Il brand_id è obbligatorio.'
    if (form.rating !== '' && (+form.rating < 0 || +form.rating > 5)) next.rating = 'Il rating deve essere tra 0 e 5.'
    setFieldErrors(next)
    return Object.keys(next).length === 0
  }

  const submit = async (event) => {
    event.preventDefault()
    if (!validate()) return
    setSaving(true)
    setError(null)
    const payload = {
      name: form.name.trim(),
      brand_id: form.brand_id.trim(),
      gender: form.gender,
      rating: form.rating === '' ? null : Number(form.rating),
      votes: form.votes === '' ? null : Number(form.votes),
      year: form.year === '' ? null : Number(form.year),
      source_url: form.source_url.trim() || null,
    }
    arrayFields.forEach(field => { payload[field] = splitIds(form[field]) })
    try {
      const saved = edit ? await api.updatePerfume(id, payload) : await api.createPerfume(payload)
      navigate(`/profumi/${encodeURIComponent(saved._id)}`)
    } catch (currentError) {
      setError(currentError)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="page"><Loading label="Caricamento del profumo" /></div>

  return <div className="page form-page">
    <Link className="back-link" to={edit ? `/profumi/${encodeURIComponent(id)}` : '/catalogo'}><ArrowLeft size={16} /> Indietro</Link>
    <div className="page-title-row"><div><span className="kicker">Operazione CRUD</span><h1>{edit ? 'Modifica profumo' : 'Nuovo profumo'}</h1><p>I riferimenti alle collection collegate devono essere inseriti tramite i rispettivi identificativi.</p></div></div>
    {error && <ErrorState error={error} />}
    <form className="editor-form" onSubmit={submit}>
      <section><h2>Informazioni principali</h2><div className="form-grid"><Field label="Nome *" error={fieldErrors.name}><input value={form.name} onChange={e => update('name', e.target.value)} /></Field><Field label="Brand ID *" error={fieldErrors.brand_id}><input value={form.brand_id} onChange={e => update('brand_id', e.target.value)} placeholder="brand_example" /></Field><Field label="Genere"><select value={form.gender} onChange={e => update('gender', e.target.value)}><option value="unisex">Unisex</option><option value="women">Donna</option><option value="men">Uomo</option></select></Field><Field label="Anno"><input type="number" min="0" max="2100" value={form.year} onChange={e => update('year', e.target.value)} /></Field><Field label="Rating" error={fieldErrors.rating}><input type="number" step="0.1" min="0" max="5" value={form.rating} onChange={e => update('rating', e.target.value)} /></Field><Field label="Voti"><input type="number" min="0" value={form.votes} onChange={e => update('votes', e.target.value)} /></Field><Field label="Source URL" wide><input type="url" value={form.source_url} onChange={e => update('source_url', e.target.value)} placeholder="https://..." /></Field></div></section>
      <section><h2>Profilo olfattivo</h2><p className="form-help">Separare più identificativi con una virgola. Il backend verificherà l’esistenza dei riferimenti.</p><div className="form-grid"><Field label="Note di testa" wide><textarea rows="3" value={form.top_note_ids} onChange={e => update('top_note_ids', e.target.value)} placeholder="note_bergamot, note_lemon" /></Field><Field label="Note di cuore" wide><textarea rows="3" value={form.middle_note_ids} onChange={e => update('middle_note_ids', e.target.value)} /></Field><Field label="Note di fondo" wide><textarea rows="3" value={form.base_note_ids} onChange={e => update('base_note_ids', e.target.value)} /></Field><Field label="Accordi" wide><textarea rows="3" value={form.accord_ids} onChange={e => update('accord_ids', e.target.value)} /></Field><Field label="Profumieri" wide><textarea rows="3" value={form.perfumer_ids} onChange={e => update('perfumer_ids', e.target.value)} /></Field></div></section>
      <div className="form-actions"><button className="button primary" disabled={saving}><Save size={17} />{saving ? 'Salvataggio…' : edit ? 'Salva modifiche' : 'Crea profumo'}</button></div>
    </form>
  </div>
}

function Field({ label, error, wide, children }) {
  return <label className={`form-field ${wide ? 'wide' : ''}`}><span>{label}</span>{children}{error && <small className="field-error">{error}</small>}</label>
}
