import { NavLink } from 'react-router-dom'
import {
  Activity,
  BarChart3,
  Database,
  GitBranch,
  LayoutDashboard,
  List,
  Zap,
} from 'lucide-react'
import { clsx } from 'clsx'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Overview', end: true },
  { to: '/evals', icon: List, label: 'Eval Runs' },
  { to: '/datasets', icon: Database, label: 'Datasets' },
  { to: '/analytics', icon: BarChart3, label: 'Analytics' },
  { to: '/models', icon: Zap, label: 'Model Compare' },
]

export function Sidebar() {
  return (
    <aside className="w-56 h-screen flex flex-col fixed left-0 top-0 z-40"
      style={{ background: 'linear-gradient(180deg, #09091a 0%, #06060f 100%)', borderRight: '1px solid rgba(255,255,255,0.06)' }}>

      {/* Logo */}
      <div className="p-5 border-b border-white/5">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
            <Activity className="w-4 h-4 text-white" />
          </div>
          <div>
            <div className="font-bold text-white tracking-tight text-sm">EvalForge</div>
            <div className="text-[10px] text-slate-500 font-mono">LLM Eval Platform</div>
          </div>
        </div>
      </div>

      {/* Live indicator */}
      <div className="px-5 py-2.5 border-b border-white/5">
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span className="pulse-dot" />
          <span>Live monitoring</span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 flex flex-col gap-0.5 pt-3">
        {navItems.map(({ to, icon: Icon, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 group relative',
                isActive
                  ? 'bg-indigo-500/10 text-indigo-400'
                  : 'text-slate-500 hover:text-slate-200 hover:bg-white/5'
              )
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-indigo-400 rounded-r-full" />
                )}
                <Icon className={clsx('w-4 h-4 transition-colors', isActive ? 'text-indigo-400' : 'text-slate-600 group-hover:text-slate-400')} />
                <span className="font-medium">{label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-white/5">
        <div className="flex items-center gap-2 text-xs text-slate-600">
          <GitBranch className="w-3 h-3" />
          <span className="font-mono">v1.0.0</span>
        </div>
      </div>
    </aside>
  )
}
