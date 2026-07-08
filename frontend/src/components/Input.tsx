import type { InputHTMLAttributes, TextareaHTMLAttributes } from 'react'
import { useId } from 'react'

export function Input({
  label,
  error,
  className = '',
  ...rest
}: { label?: string; error?: string } & InputHTMLAttributes<HTMLInputElement>) {
  const id = useId()
  return (
    <div className="ui-field">
      {label && (
        <label className="ui-label" htmlFor={id}>
          {label}
        </label>
      )}
      <input
        id={id}
        className={`ui-input ${error ? 'ui-input--error' : ''} ${className}`.trim()}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-err` : undefined}
        {...rest}
      />
      {error && (
        <span id={`${id}-err`} className="ui-error">
          {error}
        </span>
      )}
    </div>
  )
}

export function TextArea({
  label,
  error,
  className = '',
  ...rest
}: { label?: string; error?: string } & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const id = useId()
  return (
    <div className="ui-field">
      {label && (
        <label className="ui-label" htmlFor={id}>
          {label}
        </label>
      )}
      <textarea
        id={id}
        className={`ui-textarea ${error ? 'ui-input--error' : ''} ${className}`.trim()}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-err` : undefined}
        {...rest}
      />
      {error && (
        <span id={`${id}-err`} className="ui-error">
          {error}
        </span>
      )}
    </div>
  )
}
