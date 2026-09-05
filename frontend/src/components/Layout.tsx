import { NavLink } from 'react-router-dom';

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <aside style={{
        width: 240,
        backgroundColor: 'var(--color-bg-secondary)',
        borderRight: '1px solid var(--color-border)',
        display: 'flex',
        flexDirection: 'column',
        padding: 'var(--spacing-md)',
      }}>
        <div style={{
          fontSize: '20px',
          fontWeight: 700,
          color: 'var(--color-accent)',
          marginBottom: 'var(--spacing-xl)',
          padding: 'var(--spacing-sm) 0',
        }}>
          IncidentForge
        </div>
        <nav style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-xs)' }}>
          <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <span>📋</span> Dashboard
          </NavLink>
          <NavLink to="/new" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <span>🚀</span> New Investigation
          </NavLink>
        </nav>
      </aside>
      <main style={{ flex: 1, overflow: 'auto' }}>
        {children}
      </main>
    </div>
  );
}