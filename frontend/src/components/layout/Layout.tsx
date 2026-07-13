import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'

export function Layout() {
  return (
    <div className="flex min-h-screen" style={{ background: '#06060f' }}>
      <Sidebar />
      <main className="flex-1 ml-56 p-7 overflow-auto animate-fade-in">
        <Outlet />
      </main>
    </div>
  )
}
