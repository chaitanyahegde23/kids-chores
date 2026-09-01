import { KidDashboard } from './components/KidDashboard'
import { ParentDashboard } from './components/ParentDashboard'

export default function App() {
  return window.location.pathname.startsWith('/parent') ? <ParentDashboard /> : <KidDashboard />
}
