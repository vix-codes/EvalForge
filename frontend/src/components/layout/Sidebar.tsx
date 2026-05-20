import { NavLink } from 'react-router-dom'
import {
  Activity,
  BarChart3,
  Database,
  GitBranch,
  Home,
  List,
  Zap,
} from 'lucide-react'
import { clsx } from 'clsx'

const navItems = [
  { to: '/', icon: Home, label: 'Overview', end: true },
  { to: '/evals', icon: List, label: 'Eval Runs' },
  { to: '/datasets', icon: Database, label: 'Datasets' },
  { to: '/analytics', icon: BarChart3, label: 'Analytics' },
  { to: '/models', icon: Zap, label: 'Model Compare' },
]

export function Sidebar() {
  return (
    <aside className="w-56 h-screen bg-bg-secondary border-r border-bg-border flex flex-col fixed left-0 top-0">
      <div className="p-4 border-b border-bg-border">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-accent-blue" />
          <span className="font-bold text-text-primary tracking-tight">EvalForge</span>
        </div>
        <p className="text-xs text-text-muted mt-0.5">LLM Eval Platform</p>
      </div>

      <nav className="flex-1 p-3 flex flex-col gap-1">
        {navItems.map(({ to, icon: Icon, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-all',
                isActive
                  ? 'bg-accent-blue/10 text-accent-blue border border-accent-blue/20'
                  : 'text-text-secondary hover:text-text-primary hover:bg-bg-card'
              )
            }
          >
            <Icon className="w-4 h-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="p-3 border-t border-bg-border">
        <div className="text-xs text-text-muted">
          <GitBranch className="w-3 h-3 inline mr-1" />
          v1.0.0
        </div>
      </div>
    </aside>
  )
}
