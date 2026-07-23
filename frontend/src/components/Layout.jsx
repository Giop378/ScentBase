import { BarChart3, Menu, Plus, Search, X } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { useState } from 'react'

const links = [
  { to: '/', label: 'Dashboard', icon: BarChart3 },
  { to: '/catalogo', label: 'Catalogo', icon: Search },
  { to: '/profumi/nuovo', label: 'Nuovo profumo', icon: Plus },
]

export default function Layout({ children }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="app-shell">
      <header className="site-header">
        <NavLink to="/" className="brand" onClick={() => setOpen(false)}>
          <span className="brand-mark"><span /></span>
          <span><strong>ScentBase</strong><small>Olfactory archive</small></span>
        </NavLink>
        <button className="icon-button menu-button" onClick={() => setOpen(!open)} aria-label="Apri navigazione">
          {open ? <X /> : <Menu />}
        </button>
        <nav className={open ? 'main-nav open' : 'main-nav'}>
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === '/'} onClick={() => setOpen(false)}>
              <Icon size={17} />{label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main>{children}</main>
      <footer className="site-footer"><span>ScentBase</span><span>MongoDB · FastAPI · React</span></footer>
    </div>
  )
}
