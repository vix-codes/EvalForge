import { clsx } from 'clsx'

interface BadgeProps {
  label: string
  variant?: 'green' | 'red' | 'yellow' | 'blue' | 'purple' | 'gray'
}

const variantMap: Record<string, string> = {
  green: 'badge-green',
  red: 'badge-red',
  yellow: 'badge-yellow',
  blue: 'badge-blue',
  purple: 'badge-purple',
  gray: 'badge-gray',
}

export function Badge({ label, variant = 'gray' }: BadgeProps) {
  return <span className={clsx('badge', variantMap[variant])}>{label}</span>
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; variant: BadgeProps['variant'] }> = {
    completed: { label: 'Completed', variant: 'green' },
    running: { label: 'Running', variant: 'blue' },
    pending: { label: 'Pending', variant: 'yellow' },
    failed: { label: 'Failed', variant: 'red' },
  }
  const cfg = map[status] ?? { label: status, variant: 'gray' }
  return <Badge label={cfg.label} variant={cfg.variant} />
}

export function QualityGateBadge({ passed }: { passed: boolean | null }) {
  if (passed === null) return <Badge label="N/A" variant="gray" />
  return passed ? <Badge label="PASS" variant="green" /> : <Badge label="FAIL" variant="red" />
}

export function PassBadge({ passed }: { passed: boolean }) {
  return passed ? <Badge label="Pass" variant="green" /> : <Badge label="Fail" variant="red" />
}
