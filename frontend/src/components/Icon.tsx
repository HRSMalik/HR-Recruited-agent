import type { CSSProperties, ReactNode } from 'react'

/* One SVG icon set (Lucide-style), uniform stroke — never emoji. */
const ICONS: Record<string, ReactNode> = {
  home: <><path d="M3 10.5 12 3l9 7.5" /><path d="M5 9.5V21h14V9.5" /></>,
  briefcase: <><rect x="3" y="7" width="18" height="13" rx="2" /><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></>,
  list: <path d="M4 6h16M4 12h16M4 18h10" />,
  users: <><circle cx="9" cy="8" r="3.2" /><path d="M3.5 20a5.5 5.5 0 0 1 11 0" /><path d="M17 5.5a3 3 0 0 1 0 5.8M20.5 20a5 5 0 0 0-3.5-4.8" /></>,
  interviews: <path d="M12 3v18M4 8l8-5 8 5M4 8v9l8 4 8-4V8" />,
  calendar: <><rect x="3" y="4.5" width="18" height="16" rx="2" /><path d="M3 9h18M8 2.5v4M16 2.5v4" /></>,
  video: <><rect x="3" y="6" width="13" height="12" rx="2" /><path d="M16 10l5-3v10l-5-3" /></>,
  clock: <><circle cx="12" cy="12" r="8.5" /><path d="M12 8v4l2.5 1.5" /></>,
  search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-3-3" /></>,
  plus: <path d="M12 5v14M5 12h14" />,
  check: <path d="M5 13l4 4L19 7" />,
  x: <path d="M18 6 6 18M6 6l12 12" />,
  chevronRight: <path d="m9 6 6 6-6 6" />,
  chevronDown: <path d="m6 9 6 6 6-6" />,
  chevronLeft: <path d="m15 6-6 6 6 6" />,
  flag: <path d="M5 21V4h11l-2 4 2 4H5" />,
  rerank: <><path d="M4 4v6h6M20 20v-6h-6" /><path d="M20 10a8 8 0 0 0-14-4M4 14a8 8 0 0 0 14 4" /></>,
  grip: <><circle cx="9" cy="7" r="1" /><circle cx="9" cy="12" r="1" /><circle cx="9" cy="17" r="1" /><circle cx="15" cy="7" r="1" /><circle cx="15" cy="12" r="1" /><circle cx="15" cy="17" r="1" /></>,
  more: <><circle cx="12" cy="12" r="1" /><circle cx="19" cy="12" r="1" /><circle cx="5" cy="12" r="1" /></>,
  alert: <><circle cx="12" cy="12" r="9" /><path d="M12 8v4M12 16h.01" /></>,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" /></>,
  trendingUp: <path d="M6 15l6-6 6 6" />,
  barChart: <><path d="M4 19V5M4 19h16" /><path d="M8 16v-4M13 16V8M18 16v-6" /></>,
  mic: <><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" /></>,
  captions: <><rect x="3" y="5" width="18" height="14" rx="2" /><path d="M7 11h3M8 14h6M14 11h3" /></>,
  leave: <><path d="M14 4h5v16h-5" /><path d="M10 12H3M7 8l-4 4 4 4" /></>,
  user: <><circle cx="12" cy="8.5" r="4" /><path d="M4 20a8 8 0 0 1 16 0" /></>,
  sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>,
  moon: <path d="M20 14.5A8 8 0 0 1 9.5 4 7 7 0 1 0 20 14.5Z" />,
}

export type IconName = keyof typeof ICONS

export function Icon({
  name,
  size = 18,
  className,
  style,
  label,
}: {
  name: IconName
  size?: number
  className?: string
  style?: CSSProperties
  label?: string
}) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      role={label ? 'img' : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      style={style}
    >
      {ICONS[name]}
    </svg>
  )
}
