import type { ReactNode, TableHTMLAttributes } from 'react'

/* Thin wrapper applying the ui-table styling; use native thead/tbody/tr/th/td
   inside for full control (sorting, custom cells) per screen. */
export function Table({
  children,
  className = '',
  ...rest
}: { children: ReactNode } & TableHTMLAttributes<HTMLTableElement>) {
  return (
    <table className={`ui-table ${className}`.trim()} {...rest}>
      {children}
    </table>
  )
}
