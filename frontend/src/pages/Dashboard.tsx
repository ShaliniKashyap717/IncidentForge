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

  if (loading) {
    return (
      <div className="container">
        <div style={{ textAlign: 'center', padding: 'var(--spacing-xl)' }}>Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container">
        <div className="card" style={{ borderColor: 'var(--color-error)' }}>
          <h3 style={{ color: 'var(--color-error)' }}>Error loading investigations</h3>
          <p>{error}</p>
          <button className="btn btn-primary" onClick={refetch} style={{ marginTop: 'var(--spacing-md)' }}>
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
        <button className="btn btn-primary" onClick={refetch}>Refresh</button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--spacing-md)', marginBottom: 'var(--spacing-xl)' }}>
        <div className="card">
          <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', textTransform: 'uppercase', marginBottom: 'var(--spacing-xs)' }}>Total</div>
          <div style={{ fontSize: '32px', fontWeight: '700' }}>{investigations.length}</div>
        </div>
        <div className="card">
          <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', textTransform: 'uppercase', marginBottom: 'var(--spacing-xs)' }}>Running</div>
          <div style={{ fontSize: '32px', fontWeight: '700', color: 'var(--color-accent)' }}>{running}</div>
        </div>
        <div className="card">
          <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', textTransform: 'uppercase', marginBottom: 'var(--spacing-xs)' }}>Completed</div>
          <div style={{ fontSize: '32px', fontWeight: '700', color: 'var(--color-success)' }}>{completed}</div>
        </div>
        <div className="card">
          <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', textTransform: 'uppercase', marginBottom: 'var(--spacing-xs)' }}>Failed</div>
          <div style={{ fontSize: '32px', fontWeight: '700', color: 'var(--color-error)' }}>{failed}</div>
        </div>
      </div>

      <div className="card">
        <h2 style={{ marginBottom: 'var(--spacing-md)', fontSize: '18px' }}>Recent Investigations</h2>
        {investigations.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📭</div>
            <p>No investigations yet</p>
            <a href="/new" className="btn btn-primary" style={{ marginTop: 'var(--spacing-md)' }}>Start New Investigation</a>
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Incident</th>
                <th>Status</th>
                <th>Stage</th>
                <th>Progress</th>
                <th>Agents</th>
                <th>Created</th>
                <th>Duration</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {investigations.slice().sort((a, b) => {
                return b.investigation_id.localeCompare(a.investigation_id);
              }).map((inv: InvestigationSummary) => (
                <tr key={inv.investigation_id} style={{ cursor: 'pointer' }}>
                  <td><code>{inv.investigation_id.slice(0, 8)}...</code></td>
                  <td>
                    <strong>{inv.incident_title}</strong>
                    <br />
                    <small style={{ color: 'var(--color-text-secondary)' }}>{inv.incident_id}</small>
                  </td>
                  <td><span className={`badge ${getStatusBadge(inv.status)}`}>{inv.status}</span></td>
                  <td>{inv.stage}</td>
                  <td>
                    <div className="progress-bar">
                      <div className="progress-fill" style={{ width: `${inv.progress}%` }}></div>
                    </div>
                    <small>{inv.progress.toFixed(0)}%</small>
                  </td>
                  <td>{inv.completed_agents.length} / {inv.completed_agents.length + inv.active_agents.length}</td>
                  <td>{inv.created_at ? formatDistanceToNow(new Date(inv.created_at), { addSuffix: true }) : 'N/A'}</td>
                  <td>
                    {inv.completed_at && inv.started_at 
                      ? `${((new Date(inv.completed_at).getTime() - new Date(inv.started_at).getTime()) / 1000).toFixed(1)}s`
                      : inv.started_at
                        ? `${((Date.now() - new Date(inv.started_at).getTime()) / 1000).toFixed(1)}s (running)`
                        : 'N/A'}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <a href={`/investigations/${inv.investigation_id}`} className="btn btn-secondary" style={{ fontSize: '12px', padding: '4px 8px' }}>
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