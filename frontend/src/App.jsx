import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Catalog from './pages/Catalog'
import PerfumeDetail from './pages/PerfumeDetail'
import PerfumeForm from './pages/PerfumeForm'
import NotFound from './pages/NotFound'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/catalogo" element={<Catalog />} />
        <Route path="/profumi/nuovo" element={<PerfumeForm />} />
        <Route path="/profumi/:id/modifica" element={<PerfumeForm />} />
        <Route path="/profumi/:id" element={<PerfumeDetail />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Layout>
  )
}
