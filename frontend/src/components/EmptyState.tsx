import { Icon, type IconName } from './Icon'

// Honest empty/loading/error placeholder — shown when a real endpoint returns
// nothing (or hasn't loaded / failed). Never fabricates data.
export function EmptyState({
  icon = 'list',
  title,
  hint,
}: {
  icon?: IconName
  title: string
  hint?: string
}) {
  return (
    <div className="empty-state">
      <span className="es-ic">
        <Icon name={icon} size={22} />
      </span>
      <div className="es-tt">{title}</div>
      {hint && <div className="es-hint">{hint}</div>}
    </div>
  )
}
