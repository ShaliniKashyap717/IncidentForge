import { useInvestigations } from '../hooks/useInvestigations';
import { formatDistanceToNow } from 'date-fns';
import { InvestigationSummary } from '../types/api';

export function Dashboard() {
  const { investigations, loading, error, refetch } = useInvestigations();

  const running = investigations.filter(i => i.status === 'running' || i.status === 'queued' || i.status === 'analyzing' || i.status === 'synthesizing').length;
  const completed = investigations.filter(i => i.status === 'completed').length;
  const failed = investigations.filter(i => i.status === 'failed').length;

  const getStatusBadge = (status: string) => {
    const badges: Record<string, string> = {
      queued: 'badge-queued',
      running: 'badge-running',
      analyzing: 'badge-analyzing',
      synthesizing: 'badge-synthesizing',
      completed: 'badge-completed',
      failed: 'badge-failed',
    };
    return badges[status] || '';
  };

  const getStatusIndicator = (status: string) => {
    const indicators: Record<string, string> = {
      queued: 'status-indicator queued',
      running: 'status-indicator running',
      analyzing: 'status-indicator running',
      synthesizing: 'status-indicator running',
      completed: 'status-indicator completed',
      failed: 'status-indicator failed',
    };
    return indicators[status] || '';
  };

  const formatDuration = (startedAt: string | null, completedAt: string | null) => {
    if (!startedAt) return 'N/A';
    const start = new Date(startedAt).getTime();
    const end = completedAt ? new Date(completedAt).getTime() : Date.now();
    const diffMs = end - start;
    if (diffMs < 1000) return `${diffMs}ms`;
    return `${(diffMs / 1000).toFixed(1)}s`;
  };

  if (loading) {
    return (
      <div className="container">
        <div style={{ textAlign: 'center', padding: 'var(--spacing-xl)', color: 'var(--color-text-muted)' }}>Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container">
        <div className="error-banner">
          <strong>Error loading investigations</strong>
          <p style={{ marginTop: 'var(--spacing-xs)' }}>{error}</p>
          <button className="btn btn-secondary" onClick={refetch} style={{ marginTop: 'var(--spacing-md)' }}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <button className="btn btn-secondary" onClick={refetch}>Refresh</button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 'var(--spacing-md)', marginBottom: 'var(--spacing-xl)' }}>
        <div className="card" style={{ padding: 'var(--spacing-lg) var(--spacing-md)' }}>
          <div style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)', marginBottom: 'var(--spacing-xs)' }}>Total</div>
          <div style={{ fontSize: '28px', fontWeight: 400, letterSpacing: '-0.02em' }}>{investigations.length}</div>
        </div>
        <div className="card" style={{ padding: 'var(--spacing-lg) var(--spacing-md)' }}>
          <div style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)', marginBottom: 'var(--spacing-xs)' }}>Running</div>
          <div style={{ fontSize: '28px', fontWeight: 400, letterSpacing: '-0.02em', color: 'var(--color-accent-olive)' }}>{running}</div>
        </div>
        <div className="card" style={{ padding: 'var(--spacing-lg) var(--spacing-md)' }}>
          <div style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)', marginBottom: 'var(--spacing-xs)' }}>Completed</div>
          <div style={{ fontSize: '28px', fontWeight: 400, letterSpacing: '-0.02em', color: 'var(--color-accent-green)' }}>{completed}</div>
        </div>
        <div className="card" style={{ padding: 'var(--spacing-lg) var(--spacing-md)' }}>
          <div style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)', marginBottom: 'var(--spacing-xs)' }}>Failed</div>
          <div style={{ fontSize: '28px', fontWeight: 400, letterSpacing: '-0.02em', color: 'var(--color-accent-red)' }}>{failed}</div>
        </div>
      </div>

      <div className="card">
        <div className="section-header">
          <h2 className="section-title">Recent Investigations</h2>
          <span className="section-count">{investigations.length} total</span>
        </div>
        {investigations.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">∅</div>
            <p>No investigations yet</p>
            <a href="/new" className="btn btn-primary" style={{ marginTop: 'var(--spacing-md)', display: 'inline-block' }}>Start New Investigation</a>
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th style={{ width: '80px' }}>ID</th>
                <th>Incident</th>
                <th style={{ width: '110px' }}>Status</th>
                <th style={{ width: '110px' }}>Stage</th>
                <th style={{ width: '100px' }}>Progress</th>
                <th style={{ width: '80px' }}>Agents</th>
                <th style={{ width: '140px' }}>Created</th>
                <th style={{ width: '100px' }}>Duration</th>
                <th style={{ width: '60px' }}></th>
              </tr>
            </thead>
            <tbody>
              {investigations.slice().sort((a, b) => {
                return b.investigation_id.localeCompare(a.investigation_id);
              }).map((inv: InvestigationSummary) => (
                <tr key={inv.investigation_id} style={{ cursor: 'pointer' }}>
                  <td><code>{inv.investigation_id.slice(0, 8)}…</code></td>
                  <td>
                    <strong>{inv.incident_title}</strong>
                    <br />
                    <small style={{ color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>{inv.incident_id}</small>
                  </td>
                  <td>
                    <span className={`badge ${getStatusBadge(inv.status)}`}>{inv.status}</span>
                    <span className={` ${getStatusIndicator(inv.status)}`} style={{ marginLeft: 'var(--spacing-sm)' }}></span>
                  </td>
                  <td><code>{inv.stage}</code></td>
                  <td>
                    <div className="progress-bar" style={{ minWidth: '80px' }}>
                      <div className="progress-fill" style={{ width: `${inv.progress}%` }}></div>
                    </div>
                    <small style={{ color: 'var(--color-text-muted)' }}>{inv.progress.toFixed(0)}%</small>
                  </td>
                  <td><code>{inv.completed_agents.length} / {inv.completed_agents.length + inv.active_agents.length}</code></td>
                  <td style={{ color: 'var(--color-text-secondary)' }}>{inv.created_at ? formatDistanceToNow(new Date(inv.created_at), { addSuffix: true }) : 'N/A'}</td>
                  <td><code>{inv.completed_at && inv.started_at ? formatDuration(inv.started_at, inv.completed_at) : inv.started_at ? formatDuration(inv.started_at, null) + ' (running)' : 'N/A'}</code></td>
                  <td style={{ textAlign: 'right' }}>
                    <a href={`/investigations/${inv.investigation_id}`} className="btn btn-secondary" style={{ fontSize: '12px', padding: 'var(--spacing-xs) var(--spacing-sm)' }}>
                      View
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}