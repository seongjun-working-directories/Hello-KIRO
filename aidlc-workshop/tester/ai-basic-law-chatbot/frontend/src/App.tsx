import ChatWindow from './components/ChatWindow'
import AdminDashboard from './pages/AdminDashboard'

export default function App() {
  const isAdmin = window.location.pathname.startsWith('/admin/logs')
  return isAdmin ? <AdminDashboard /> : <ChatWindow />
}
