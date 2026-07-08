// App shell is built in BL-FE-04 (sidebar + routing). This placeholder confirms
// the scaffold + token foundation renders.
export default function App() {
  return (
    <div style={{ padding: 32, maxWidth: 640 }}>
      <div
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: 32,
          height: 32,
          borderRadius: 8,
          background: 'var(--accent)',
          color: '#fff',
          fontWeight: 700,
        }}
      >
        R
      </div>
      <h1 style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.02em', marginTop: 16 }}>
        HR Recruited
      </h1>
      <p style={{ color: 'var(--text-muted)', marginTop: 6 }}>
        Frontend scaffold ready — React + TypeScript + Vite, design tokens loaded.
      </p>
    </div>
  )
}
