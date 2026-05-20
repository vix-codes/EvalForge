import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/layout/Layout'
import { Overview } from './pages/Overview'
import { EvalRuns } from './pages/EvalRuns'
import { RunDetail } from './pages/RunDetail'
import { Datasets } from './pages/Datasets'
import { Analytics } from './pages/Analytics'
import { ModelComparison } from './pages/ModelComparison'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Overview />} />
          <Route path="/evals" element={<EvalRuns />} />
          <Route path="/evals/:id" element={<RunDetail />} />
          <Route path="/datasets" element={<Datasets />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/models" element={<ModelComparison />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
