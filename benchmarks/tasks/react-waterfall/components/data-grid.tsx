import { schedule } from '@/lib/heavy-grid-engine'

export function DataGrid({ rows }: { rows: unknown[] }) {
  return <div>{schedule(rows).length}</div>
}
