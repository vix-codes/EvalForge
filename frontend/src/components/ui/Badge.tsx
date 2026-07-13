import { CheckCircle2, Clock, Loader2, XCircle, AlertTriangle, ShieldCheck, ShieldX } from 'lucide-react'

const STATUS_MAP: Record<string, { label: string; cls: string; icon: React.ReactNode }> = {
  completed: { label: 'Completed', cls: 'badge-green',  icon: <CheckCircle2 className="w-3 h-3" /> },
  running:   { label: 'Running',   cls: 'badge-blue',   icon: <Loader2 className="w-3 h-3 animate-spin" /> },
  pending:   { label: 'Pending',   cls: 'badge-yellow', icon: <Clock className="w-3 h-3" /> },
  failed:    { label: 'Failed',    cls: 'badge-red',    icon: <XCircle className="w-3 h-3" /> },
}

export function StatusBadge({ status }: { status: string }) {
  const s = STATUS_MAP[status] ?? { label: status, cls: 'badge-gray', icon: null }
  return (
    <span className={s.cls}>
      {s.icon}
      {s.label}
    </span>
  )
}

export function QualityGateBadge({ passed }: { passed: boolean | null | undefined }) {
  if (passed === null || passed === undefined) return <span className="badge-gray">—</span>
  return passed
    ? <span className="badge-green"><ShieldCheck className="w-3 h-3" /> Pass</span>
    : <span className="badge-red"><ShieldX className="w-3 h-3" /> Fail</span>
}

export function HallucinationBadge({ rate }: { rate: number | null | undefined }) {
  if (rate === null || rate === undefined) return <span className="badge-gray">—</span>
  if (rate === 0) return <span className="badge-green"><CheckCircle2 className="w-3 h-3" /> Clean</span>
  if (rate < 0.1) return <span className="badge-yellow"><AlertTriangle className="w-3 h-3" /> Low</span>
  return <span className="badge-red"><AlertTriangle className="w-3 h-3" /> High</span>
}
