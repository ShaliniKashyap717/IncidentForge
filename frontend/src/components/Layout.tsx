import { NavLink } from 'react-router-dom';

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <aside style={{
        width: 200,
        backgroundColor: 'var(--color-bg-surface)',
        borderRight: '1px solid var(--color-border)',
        display: 'flex',
        flexDirection: 'column',
        padding: 'var(--spacing-lg) var(--spacing-md)',
      }}>
        <div style={{
          fontSize: '18px',
          fontWeight: 500,
          color: 'var(--color-accent-bronze)',
          marginBottom: 'var(--spacing-xl)',
          padding: 'var(--spacing-sm) 0',
          letterSpacing: '-0.01em',
        }}>
          IncidentForge
        </div>
        <nav style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-xs)' }}>
          <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            Dashboard
          </NavLink>
          <NavLink to="/new" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            New Investigation
          </NavLink>
        </nav>
      </aside>
      <main style={{ flex: 1, overflow: 'auto' }}>
        {children}
      </main>
    </div>
  );
}