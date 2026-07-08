import type { SelectHTMLAttributes } from 'react'
import { useId } from 'react'

export type Option = { value: string; label: string }

export function Select({
  label,
  error,
  options,
  className = '',
  ...rest
}: { label?: string; error?: string; options: Option[] } & SelectHTMLAttributes<HTMLSelectElement>) {
  const id = useId()
  return (
    <div className="ui-field">
      {label && (
        <label className="ui-label" htmlFor={id}>
          {label}
        </label>
      )}
      <select
        id={id}
        className={`ui-select ${error ? 'ui-input--error' : ''} ${className}`.trim()}
        aria-invalid={error ? true : undefined}
        {...rest}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {error && <span className="ui-error">{error}</span>}
    </div>
  )
}
