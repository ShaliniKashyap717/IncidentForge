import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useInvestigation, useInvestigationState } from '../hooks/useInvestigations';
import { api } from '../api/client';

const STAGE_ORDER = ['initialized', 'queued', 'running', 'analyzing', 'recommending', 'completed', 'failed'];

function getStageIndex(stage: string) {
  return STAGE_ORDER.indexOf(stage);
}

function formatTime(timestamp: string) {
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return timestamp;
  }
}

function getStatusBadge(status: string) {
  const badges: Record<string, string> = {
    created: 'badge-created',
    queued: 'badge-queued',
    running: 'badge-running',
    analyzing: 'badge-analyzing',
    recommending: 'badge-recommending',
    completed: 'badge-completed',
    failed: 'badge-failed',
  };
  return badges[status] || '';
}

function CollapsibleSection({ title, expanded, onToggle, children }: { title: string; expanded: boolean; onToggle: () => void; children: React.ReactNode }) {
  return (
    <div style={{ border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
      <button
        style={{ width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 'var(--spacing-md)', background: 'var(--color-bg-tertiary)', border: 'none', color: 'inherit', fontSize: '16px', cursor: 'pointer' }}
        onClick={onToggle}
      >
        <span>{title}</span>
        <span>{expanded ? '▼' : '▶'}</span>
      </button>
      {expanded && <div style={{ padding: 'var(--spacing-md)' }}>{children}</div>}
    </div>
  );
}

export function InvestigationDetail() {
  const { investigationId } = useParams<{ investigationId: string }>();
  const navigate = useNavigate();
  const { investigation, loading, error, refetch } = useInvestigation(investigationId || null);
  const { state, loading: _stateLoading, refetch: refetchState } = useInvestigationState(investigationId || null);

  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    timeline: true,
    evidence: false,
    findings: false,
    hypotheses: false,
    recommendations: false,
  });

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const [_streamError, _setStreamError] = useState<string | null>(null);

  const handleApprove = async (index: number) => {
    const note = prompt('Approval note (optional):');
    try {
      await api.investigations.approveRecommendation(investigationId!, index, note || undefined);
      refetchState();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to approve');
    }
  };

  const handleReject = async (index: number) => {
    const note = prompt('Rejection note (optional):');
    try {
      await api.investigations.rejectRecommendation(investigationId!, index, note || undefined);
      refetchState();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to reject');
    }
  };

  if (!investigationId) {
    return <div className="container">Invalid investigation ID</div>;
  }

  if (loading) {
    return (
      <div className="container" style={{ textAlign: 'center', padding: 'var(--spacing-xl)' }}>
        Loading investigation...
      </div>
    );
  }

  if (error && !investigation) {
    return (
      <div className="container">
        <div className="card" style={{ borderColor: 'var(--color-error)' }}>
          <h2>Investigation Not Found</h2>
          <p>{error}</p>
          <button className="btn btn-primary" onClick={() => navigate('/')} style={{ marginTop: 'var(--spacing-md)' }}>
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const currentInvestigation = investigation!;
  const currentState = state || currentInvestigation as any;
  const currentStage = currentState.stage || 'initialized';

  return (
    <div className="container">
      <div className="page-header">
        <div>
          <h1 className="page-title">{currentInvestigation.incident_title}</h1>
          <div style={{ display: 'flex', gap: 'var(--spacing-md)', marginTop: 'var(--spacing-xs)', fontSize: '14px', color: 'var(--color-text-secondary)' }}>
            <span>ID: <code>{currentInvestigation.incident_id}</code></span>
            <span>Investigation: <code>{currentInvestigation.investigation_id.slice(0, 8)}...</code></span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 'var(--spacing-md)', alignItems: 'center' }}>
          <button className="btn btn-secondary" onClick={() => navigate('/')}>← Back</button>
          <button className="btn btn-secondary" onClick={() => { refetch(); }}>Refresh</button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 350px', gap: 'var(--spacing-lg)' }}>
        <div>
          {/* Stage Progress */}
          <div className="card" style={{ marginBottom: 'var(--spacing-md)' }}>
            <h3 style={{ marginBottom: 'var(--spacing-md)' }}>Investigation Progress</h3>
            <div className="stage-indicator">
              {STAGE_ORDER.map(stage => (
                <div
                  key={stage}
                  className={`stage-step ${stage === 'failed' && currentInvestigation.status === 'failed' ? 'failed' : getStageIndex(stage) < getStageIndex(currentStage) ? 'completed' : getStageIndex(stage) === getStageIndex(currentStage) ? 'active' : ''}`}
                >
                  <div className="stage-icon" style={{
                    backgroundColor: stage === 'failed' && currentInvestigation.status === 'failed' ? 'var(--color-error)' :
                                     getStageIndex(stage) < getStageIndex(currentStage) ? 'var(--color-success)' :
                                     getStageIndex(stage) === getStageIndex(currentStage) ? 'var(--color-accent)' : 'transparent',
                    border: stage === 'failed' && currentInvestigation.status === 'failed' ? '2px solid var(--color-error)' :
                            getStageIndex(stage) < getStageIndex(currentStage) ? '2px solid var(--color-success)' :
                            getStageIndex(stage) === getStageIndex(currentStage) ? '2px solid var(--color-accent)' : '2px solid var(--color-border)'
                  }}>
                    {getStageIndex(stage) < getStageIndex(currentStage) ? '✓' :
                     getStageIndex(stage) === getStageIndex(currentStage) ? '▶' :
                     stage === 'failed' && currentInvestigation.status === 'failed' ? '✗' : ''}
                  </div>
                  <span>{stage.charAt(0).toUpperCase() + stage.slice(1)}</span>
                </div>
              ))}
            </div>
            <div className="progress-bar" style={{ marginTop: 'var(--spacing-md)' }}>
              <div className="progress-fill" style={{ width: `${currentInvestigation.progress}%` }}></div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 'var(--spacing-xs)', fontSize: '12px', color: 'var(--color-text-secondary)' }}>
              <span>Status: <strong>{currentInvestigation.status}</strong></span>
              <span>Stage: <strong>{currentStage}</strong></span>
              <span>Progress: <strong>{currentInvestigation.progress.toFixed(0)}%</strong></span>
            </div>
          </div>

          {/* Timeline / Event Feed */}
          <div className="card" style={{ marginBottom: 'var(--spacing-md)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-md)' }}>
              <h3>
                <button
                  className="btn btn-secondary"
                  style={{ fontSize: '16px', padding: 0, background: 'none', border: 'none', color: 'inherit' }}
                  onClick={() => toggleSection('timeline')}
                >
                  📋 Timeline ({currentState.timeline?.length || 0})
                  {expandedSections.timeline ? ' ▼' : ' ▶'}
                </button>
              </h3>
              {_streamError && (
                <span className="badge badge-failed">SSE disconnected - polling fallback</span>
              )}
            </div>
            {expandedSections.timeline && (
              <div className="event-feed">
                {(() => {
                  const events = currentState.timeline?.slice().reverse() || [];
                  return events.map((event: any, idx: number) => (
                    <div key={idx} className="event-item">
                      <span className="event-time">{formatTime(event.timestamp)}</span>
                      <span className="event-type">{event.type}</span>
                      <span className="event-description">{event.description}</span>
                      {event.agent && <span className="event-agent">[{event.agent}]</span>}
                    </div>
                  ));
                })()}
              </div>
            )}
          </div>
        </div>

        <aside>
          {/* Status Card */}
          <div className="card" style={{ marginBottom: 'var(--spacing-md)', position: 'sticky', top: 'var(--spacing-lg)' }}>
            <h3 style={{ marginBottom: 'var(--spacing-md)' }}>Status</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-sm)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--color-text-secondary)' }}>Incident ID</span>
                <code>{currentInvestigation.incident_id}</code>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--color-text-secondary)' }}>Status</span>
                <span className={`badge ${getStatusBadge(currentInvestigation.status)}`}>{currentInvestigation.status}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--color-text-secondary)' }}>Stage</span>
                <span>{currentState.stage || 'initialized'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--color-text-secondary)' }}>Progress</span>
                <span>{currentInvestigation.progress.toFixed(0)}%</span>
              </div>
              <div className="progress-bar" style={{ marginTop: 'var(--spacing-xs)' }}>
                <div className="progress-fill" style={{ width: `${currentInvestigation.progress}%` }}></div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                <span style={{ color: 'var(--color-text-secondary)' }}>Evidence</span>
                <strong>{currentInvestigation.evidence_count}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                <span style={{ color: 'var(--color-text-secondary)' }}>Findings</span>
                <strong>{currentInvestigation.findings_count}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                <span style={{ color: 'var(--color-text-secondary)' }}>Hypotheses</span>
                <strong>{currentState.hypotheses_count || 0}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                <span style={{ color: 'var(--color-text-secondary)' }}>Recommendations</span>
                <strong>{currentInvestigation.recommendations_count}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                <span style={{ color: 'var(--color-text-secondary)' }}>Active Agents</span>
                <strong>{currentInvestigation.active_agents.length}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                <span style={{ color: 'var(--color-text-secondary)' }}>Completed Agents</span>
                <strong>{currentInvestigation.completed_agents.length}</strong>
              </div>
              {currentInvestigation.error && (
                <div style={{ marginTop: 'var(--spacing-md)', padding: 'var(--spacing-sm)', backgroundColor: 'rgba(248, 81, 73, 0.1)', border: '1px solid var(--color-error)', borderRadius: 'var(--radius-sm)', color: 'var(--color-error)', fontSize: '12px' }}>
                  Error: {currentInvestigation.error}
                </div>
              )}
            </div>
          </div>

          {/* Agents */}
          <div className="card" style={{ marginBottom: 'var(--spacing-md)' }}>
            <h3 style={{ marginBottom: 'var(--spacing-md)' }}>Agents</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-sm)' }}>
              {['Observability Agent', 'Repository Agent', 'Database Agent'].map(agent => {
                const isActive = currentInvestigation.active_agents.includes(agent);
                const isCompleted = currentInvestigation.completed_agents.includes(agent);
                return (
                  <div key={agent} style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--spacing-sm)',
                    padding: 'var(--spacing-sm)',
                    backgroundColor: isActive ? 'rgba(88, 166, 255, 0.1)' : isCompleted ? 'rgba(63, 185, 80, 0.1)' : 'transparent',
                    borderRadius: 'var(--radius-sm)',
                    border: isActive ? '1px solid var(--color-accent)' : isCompleted ? '1px solid var(--color-success)' : '1px solid var(--color-border)',
                  }}>
                    <span style={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      backgroundColor: isActive ? 'var(--color-accent)' : isCompleted ? 'var(--color-success)' : 'var(--color-border)',
                    }}></span>
                    <span style={{ flex: 1 }}>{agent}</span>
                    <span className={`badge ${isActive ? 'badge-running' : isCompleted ? 'badge-completed' : 'badge-pending'}`}>
                      {isActive ? 'Running' : isCompleted ? 'Done' : 'Pending'}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </aside>
      </div>

      {/* Collapsible Sections */}
      <div className="card" style={{ marginTop: 'var(--spacing-lg)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-md)' }}>
          <h2>Investigation Artifacts</h2>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)' }}>
          <CollapsibleSection
            title={`Evidence (${currentState.evidence.length})`}
            expanded={expandedSections.evidence}
            onToggle={() => toggleSection('evidence')}
          >
            <div style={{ maxHeight: '400px', overflow: 'auto' }}>
              {currentState.evidence.length === 0 ? (
                <div className="empty-state" style={{ padding: 'var(--spacing-lg)' }}>No evidence collected yet</div>
              ) : (
                <table className="table">
                  <thead>
                    <tr>
                      <th>Type</th>
                      <th>Source</th>
                      <th>Description</th>
                      <th>Relevance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {currentState.evidence.map((e: any, idx: number) => (
                      <tr key={idx}>
                        <td><span className={`badge badge-${e.type}`}>{e.type}</span></td>
                        <td><code>{e.source}</code></td>
                        <td>{e.description}</td>
                        <td>{(e.relevance * 100).toFixed(0)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </CollapsibleSection>

          <CollapsibleSection
            title={`Findings (${currentState.findings.length})`}
            expanded={expandedSections.findings}
            onToggle={() => toggleSection('findings')}
          >
            {currentState.findings.length === 0 ? (
              <div className="empty-state" style={{ padding: 'var(--spacing-lg)' }}>No findings yet</div>
            ) : (
              currentState.findings.map((f: any, idx: number) => (
                <div key={idx} style={{ borderBottom: '1px solid var(--color-border)', padding: 'var(--spacing-md)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--spacing-xs)' }}>
                    <strong>{f.agent}</strong>
                    <span className="badge badge-approved">Confidence: {(f.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <p style={{ marginBottom: 'var(--spacing-sm)' }}>{f.summary}</p>
                  <p style={{ fontStyle: 'italic', color: 'var(--color-text-secondary)', marginBottom: 'var(--spacing-sm)' }}>Hypothesis: {f.hypothesis}</p>
                  <small>Evidence: {f.evidence?.length || 0} items</small>
                </div>
              ))
            )}
          </CollapsibleSection>

          <CollapsibleSection
            title={`Hypotheses (${currentState.hypotheses.length})`}
            expanded={expandedSections.hypotheses}
            onToggle={() => toggleSection('hypotheses')}
          >
            {currentState.hypotheses.length === 0 ? (
              <div className="empty-state" style={{ padding: 'var(--spacing-lg)' }}>No hypotheses yet</div>
            ) : (
              currentState.hypotheses.map((h: any, idx: number) => (
                <div key={idx} style={{ borderBottom: '1px solid var(--color-border)', padding: 'var(--spacing-md)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--spacing-xs)' }}>
                    <strong>Hypothesis {idx + 1}</strong>
                    <span className="badge badge-approved">{(h.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <p style={{ marginBottom: 'var(--spacing-sm)' }}>{h.description}</p>
                  <small>Status: {h.status} | Supporting evidence: {h.supporting_evidence?.length || 0}</small>
                </div>
              ))
            )}
          </CollapsibleSection>

          <CollapsibleSection
            title={`Recommendations (${currentState.recommendations.length})`}
            expanded={expandedSections.recommendations}
            onToggle={() => toggleSection('recommendations')}
          >
            {currentState.recommendations.length === 0 ? (
              <div className="empty-state" style={{ padding: 'var(--spacing-lg)' }}>No recommendations yet</div>
            ) : (
              currentState.recommendations.map((r: any, idx: number) => (
                <div key={idx} style={{ borderBottom: '1px solid var(--color-border)', padding: 'var(--spacing-md)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--spacing-sm)' }}>
                    <strong style={{ flex: 1 }}>Recommendation {idx + 1}</strong>
                    <span className={`badge badge-${r.status}`}>{r.status}</span>
                  </div>
                  <p style={{ marginBottom: 'var(--spacing-xs)' }}><strong>Action:</strong> {r.action}</p>
                  <p style={{ marginBottom: 'var(--spacing-xs)', color: 'var(--color-text-secondary)' }}><strong>Rationale:</strong> {r.rationale}</p>
                  <p style={{ marginBottom: 'var(--spacing-xs)', color: 'var(--color-text-secondary)' }}><strong>Risk:</strong> {r.risk}</p>
                  <div style={{ display: 'flex', gap: 'var(--spacing-md)', fontSize: '12px', color: 'var(--color-text-secondary)', marginBottom: 'var(--spacing-md)' }}>
                    <span>Confidence: {(r.confidence * 100).toFixed(0)}%</span>
                    <span>Requires Approval: {r.requires_approval ? 'Yes' : 'No'}</span>
                  </div>
                  {r.requires_approval && r.status === 'pending' && (
                    <div style={{ display: 'flex', gap: 'var(--spacing-sm)' }}>
                      <button className="btn btn-primary" style={{ fontSize: '12px' }} onClick={() => handleApprove(idx)}>
                        Approve
                      </button>
                      <button className="btn btn-danger" style={{ fontSize: '12px' }} onClick={() => handleReject(idx)}>
                        Reject
                      </button>
                    </div>
                  )}
                </div>
              ))
            )}
          </CollapsibleSection>
        </div>
      </div>
    </div>
  );
}