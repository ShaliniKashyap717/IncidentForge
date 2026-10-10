import { useState, useCallback, useRef, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useInvestigation, useInvestigationState } from '../hooks/useInvestigations';
import { useInvestigationStream } from '../hooks/useInvestigationStream';
import { api } from '../api/client';
import { FullInvestigationState, TimelineEvent } from '../types/api';

const STAGE_ORDER = ['queued', 'triage', 'observability', 'repository', 'database', 'correlation', 'synthesis', 'recommendation', 'completed', 'failed'];

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
    queued: 'badge-queued',
    running: 'badge-running',
    analyzing: 'badge-analyzing',
    synthesizing: 'badge-synthesizing',
    completed: 'badge-completed',
    failed: 'badge-failed',
  };
  return badges[status] || '';
}

function getStatusIndicator(status: string) {
  const indicators: Record<string, string> = {
    queued: 'status-indicator queued',
    running: 'status-indicator running',
    analyzing: 'status-indicator running',
    synthesizing: 'status-indicator running',
    completed: 'status-indicator completed',
    failed: 'status-indicator failed',
  };
  return indicators[status] || '';
}

function formatDuration(startedAt: string | null, completedAt: string | null) {
  if (!startedAt) return 'N/A';
  const start = new Date(startedAt).getTime();
  const end = completedAt ? new Date(completedAt).getTime() : Date.now();
  const diffMs = end - start;
  if (diffMs < 1000) return `${diffMs}ms`;
  return `${(diffMs / 1000).toFixed(1)}s`;
}

function getLeadingHypothesis(hypotheses: any[]) {
  if (!hypotheses.length) return null;
  return hypotheses.reduce((max, h) => h.confidence > max.confidence ? h : max, hypotheses[0]);
}

function getAgentStatusClass(agent: string, activeAgents: string[], completedAgents: string[]) {
  if (activeAgents.includes(agent)) return 'active';
  if (completedAgents.includes(agent)) return 'completed';
  return 'pending';
}

function getAgentStatusText(agent: string, activeAgents: string[], completedAgents: string[]) {
  if (activeAgents.includes(agent)) return 'Active';
  if (completedAgents.includes(agent)) return 'Completed';
  return 'Pending';
}

export function InvestigationDetail() {
  const { investigationId } = useParams<{ investigationId: string }>();
  const navigate = useNavigate();
  const { investigation, loading, error, refetch } = useInvestigation(investigationId || null);
  const { state, loading: stateLoading, refetch: refetchState } = useInvestigationState(investigationId || null);

  const [activeTab, setActiveTab] = useState<'overview' | 'evidence' | 'findings' | 'hypotheses' | 'recommendations' | 'timeline'>('overview');
  const [streamError, setStreamError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const hasReceivedInitialState = useRef(false);

  const handleSSEEvent = useCallback((_: TimelineEvent) => {
    // Events are handled via state updates
  }, []);

  const handleSSEStateChange = useCallback((_: FullInvestigationState) => {
    if (!hasReceivedInitialState.current) {
      hasReceivedInitialState.current = true;
    }
  }, []);

  const handleSSEComplete = useCallback((_: FullInvestigationState) => {
    refetchState();
  }, [refetchState]);

  const handleSSEError = useCallback((err: Error) => {
    setStreamError(err.message);
    setConnected(false);
  }, []);

  useInvestigationStream({
    investigationId: investigationId || null,
    onEvent: handleSSEEvent,
    onStateChange: handleSSEStateChange,
    onComplete: handleSSEComplete,
    onError: handleSSEError,
  });

  // Track connection status
  useEffect(() => {
    const stateManager = state || investigation;
    if (stateManager) {
      const status = stateManager.status;
      setConnected(status !== 'completed' && status !== 'failed');
    }
  }, [state, investigation]);

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

  if (loading || stateLoading) {
    return (
      <div className="container" style={{ textAlign: 'center', padding: 'var(--spacing-xl)', color: 'var(--color-text-muted)' }}>
        Loading investigation…
      </div>
    );
  }

  if (error && !investigation) {
    return (
      <div className="container">
        <div className="error-banner">
          <strong>Investigation Not Found</strong>
          <p style={{ marginTop: 'var(--spacing-xs)' }}>{error}</p>
          <button className="btn btn-secondary" onClick={() => navigate('/')} style={{ marginTop: 'var(--spacing-md)' }}>
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const currentInvestigation = investigation!;
  const currentState = state || currentInvestigation as any;
  const currentStage = currentState.stage || 'queued';
  const isComplete = currentInvestigation.status === 'completed' || currentInvestigation.status === 'failed';
  const leadingHypothesis = getLeadingHypothesis(currentState.hypotheses || []);

  return (
    <div className="container">
      <div className="page-header">
        <div>
          <h1 className="page-title">
            {currentInvestigation.incident_title}
            <small>Investigation {currentInvestigation.investigation_id.slice(0, 8)}…</small>
          </h1>
          <div style={{ display: 'flex', gap: 'var(--spacing-lg)', marginTop: 'var(--spacing-xs)', fontSize: '13px', color: 'var(--color-text-secondary)' }}>
            <span>Incident: <code>{currentInvestigation.incident_id}</code></span>
            <span className={getStatusIndicator(currentInvestigation.status)}>
              {currentInvestigation.status.charAt(0).toUpperCase() + currentInvestigation.status.slice(1)}
            </span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 'var(--spacing-sm)', alignItems: 'center' }}>
          <button className="btn btn-secondary" onClick={() => navigate('/')}>← Back</button>
          <button className="btn btn-secondary" onClick={() => { refetch(); refetchState(); }}>Refresh</button>
        </div>
      </div>

      {/* Stage Progress Bar */}
      <div className="card" style={{ marginBottom: 'var(--spacing-lg)' }}>
        <div className="stage-indicator">
          {STAGE_ORDER.map(stage => {
            const idx = getStageIndex(stage);
            const currentIdx = getStageIndex(currentStage);
            let className = 'stage-step';
            if (stage === 'failed' && currentInvestigation.status === 'failed') className += ' failed';
            else if (idx < currentIdx) className += ' completed';
            else if (idx === currentIdx && !isComplete) className += ' active';
            return (
              <div key={stage} className={className}>
                <div className="stage-icon" style={{
                  backgroundColor: stage === 'failed' && currentInvestigation.status === 'failed' ? 'var(--color-accent-red)' :
                                   idx < currentIdx ? 'var(--color-accent-green)' :
                                   idx === currentIdx && !isComplete ? 'var(--color-accent-bronze)' : 'transparent',
                  borderColor: stage === 'failed' && currentInvestigation.status === 'failed' ? 'var(--color-accent-red)' :
                               idx < currentIdx ? 'var(--color-accent-green)' :
                               idx === currentIdx && !isComplete ? 'var(--color-accent-bronze)' : 'var(--color-border)',
                }}>
                  {idx < currentIdx ? '✓' :
                   idx === currentIdx && !isComplete ? '▸' :
                   stage === 'failed' && currentInvestigation.status === 'failed' ? '✕' : ''}
                </div>
                <span>{stage.charAt(0).toUpperCase() + stage.slice(1)}</span>
              </div>
            );
          })}
        </div>
        <div className="progress-bar" style={{ marginTop: 'var(--spacing-md)' }}>
          <div className="progress-fill" style={{ width: `${currentInvestigation.progress}%` }}></div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 'var(--spacing-sm)', fontSize: '12px', color: 'var(--color-text-muted)' }}>
          <span>Status: <strong>{currentInvestigation.status}</strong></span>
          <span>Stage: <strong>{currentStage}</strong></span>
          <span>Progress: <strong>{currentInvestigation.progress.toFixed(0)}%</strong></span>
          <span>Duration: <strong>{formatDuration(currentInvestigation.started_at, currentInvestigation.completed_at)}</strong></span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 'var(--spacing-lg)' }}>
        <div>
          {/* Main Content Tabs */}
          <div className="tabs" role="tablist">
            <button role="tab" className={`tab ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')} aria-selected={activeTab === 'overview'}>Overview</button>
            <button role="tab" className={`tab ${activeTab === 'evidence' ? 'active' : ''}`} onClick={() => setActiveTab('evidence')} aria-selected={activeTab === 'evidence'}>Evidence <span className="section-count">({currentState.evidence?.length || 0})</span></button>
            <button role="tab" className={`tab ${activeTab === 'findings' ? 'active' : ''}`} onClick={() => setActiveTab('findings')} aria-selected={activeTab === 'findings'}>Findings <span className="section-count">({currentState.findings?.length || 0})</span></button>
            <button role="tab" className={`tab ${activeTab === 'hypotheses' ? 'active' : ''}`} onClick={() => setActiveTab('hypotheses')} aria-selected={activeTab === 'hypotheses'}>Hypotheses <span className="section-count">({currentState.hypotheses?.length || 0})</span></button>
            <button role="tab" className={`tab ${activeTab === 'recommendations' ? 'active' : ''}`} onClick={() => setActiveTab('recommendations')} aria-selected={activeTab === 'recommendations'}>Recommendations <span className="section-count">({currentState.recommendations?.length || 0})</span></button>
            <button role="tab" className={`tab ${activeTab === 'timeline' ? 'active' : ''}`} onClick={() => setActiveTab('timeline')} aria-selected={activeTab === 'timeline'}>Timeline <span className="section-count">({currentState.timeline?.length || 0})</span></button>
          </div>

          {activeTab === 'overview' && (
            <div className="panel active">
              {/* Incident Summary */}
              <div className="incident-summary">
                <strong>Description:</strong> {currentInvestigation.incident_description || 'No description available.'}
                {currentInvestigation.incident_affected_services && currentInvestigation.incident_affected_services.length > 0 && (
                  <>
                    <br /><br />
                    <strong>Affected Services:</strong> {currentInvestigation.incident_affected_services.join(', ')}
                  </>
                )}
                {currentInvestigation.incident_severity && (
                  <>
                    <br /><br />
                    <strong>Severity:</strong> <code>{currentInvestigation.incident_severity}</code>
                  </>
                )}
              </div>

              {/* Leading Hypothesis */}
              {leadingHypothesis && (
                <div className="leading-hypothesis">
                  <div className="hypothesis-label">Leading Hypothesis</div>
                  <div className="hypothesis-text">{leadingHypothesis.description}</div>
                  <div className="hypothesis-confidence">
                    Confidence: <strong>{(leadingHypothesis.confidence * 100).toFixed(0)}%</strong>
                    {leadingHypothesis.supporting_evidence?.length && (
                      <> · Supported by {leadingHypothesis.supporting_evidence.length} evidence item(s)</>
                    )}
                    {leadingHypothesis.contradicting_evidence?.length && (
                      <> · {leadingHypothesis.contradicting_evidence.length} contradicting</>
                    )}
                  </div>
                </div>
              )}

              {/* Quick Stats */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 'var(--spacing-md)', marginTop: 'var(--spacing-lg)' }}>
                <div className="card" style={{ padding: 'var(--spacing-md)' }}>
                  <div style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)', marginBottom: 'var(--spacing-xs)' }}>Evidence Collected</div>
                  <div style={{ fontSize: '24px', fontWeight: 400 }}>{currentState.evidence?.length || 0}</div>
                </div>
                <div className="card" style={{ padding: 'var(--spacing-md)' }}>
                  <div style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)', marginBottom: 'var(--spacing-xs)' }}>Findings</div>
                  <div style={{ fontSize: '24px', fontWeight: 400 }}>{currentState.findings?.length || 0}</div>
                </div>
                <div className="card" style={{ padding: 'var(--spacing-md)' }}>
                  <div style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)', marginBottom: 'var(--spacing-xs)' }}>Hypotheses</div>
                  <div style={{ fontSize: '24px', fontWeight: 400 }}>{currentState.hypotheses?.length || 0}</div>
                </div>
                <div className="card" style={{ padding: 'var(--spacing-md)' }}>
                  <div style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-muted)', marginBottom: 'var(--spacing-xs)' }}>Recommendations</div>
                  <div style={{ fontSize: '24px', fontWeight: 400 }}>{currentState.recommendations?.length || 0}</div>
                </div>
              </div>

              {/* Next Steps */}
              {currentState.recommendations?.length && (
                <div style={{ marginTop: 'var(--spacing-lg)' }}>
                  <h3 style={{ fontSize: '15px', fontWeight: 500, marginBottom: 'var(--spacing-md)' }}>Recommended Next Steps</h3>
                  {currentState.recommendations.map((r: any, idx: number) => (
                    <div key={idx} className="recommendation-card">
                      <header>
                        <span className="recommendation-title">Recommendation {idx + 1}</span>
                        <span className={`badge badge-${r.status}`}>{r.status}</span>
                      </header>
                      <div className="recommendation-action"><strong>Action:</strong> {r.action}</div>
                      <div className="recommendation-rationale"><strong>Rationale:</strong> {r.rationale}</div>
                      <div className="recommendation-risk"><strong>Risk:</strong> {r.risk}</div>
                      <div className="recommendation-meta">
                        <span>Confidence: {(r.confidence * 100).toFixed(0)}%</span>
                        <span>Approval: {r.requires_approval ? 'Required' : 'Not required'}</span>
                      </div>
                      {r.requires_approval && r.status === 'pending' && (
                        <div className="recommendation-actions">
                          <button className="btn btn-primary" style={{ fontSize: '12px' }} onClick={() => handleApprove(idx)}>Approve</button>
                          <button className="btn btn-danger" style={{ fontSize: '12px' }} onClick={() => handleReject(idx)}>Reject</button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'evidence' && (
            <div className="panel active">
              {currentState.evidence?.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-state-icon">∅</div>
                  <p>No evidence collected yet</p>
                </div>
              ) : (
                <table className="evidence-table">
                  <thead>
                    <tr>
                      <th style={{ width: '90px' }}>Type</th>
                      <th style={{ width: '120px' }}>Source</th>
                      <th>Description</th>
                      <th style={{ width: '80px' }}>Relevance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {currentState.evidence.map((e: any, idx: number) => (
                      <tr key={idx}>
                        <td className="evidence-type"><span className={`badge badge-type-${e.type}`}>{e.type}</span></td>
                        <td className="evidence-source"><code>{e.source}</code></td>
                        <td className="evidence-description">{e.description}</td>
                        <td className="evidence-relevance">{(e.relevance * 100).toFixed(0)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {activeTab === 'findings' && (
            <div className="panel active">
              {currentState.findings?.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-state-icon">∅</div>
                  <p>No findings yet</p>
                </div>
              ) : (
                currentState.findings.map((f: any, idx: number) => (
                  <div key={idx} className="finding-card">
                    <header>
                      <span className="finding-agent">{f.agent}</span>
                      <span className="finding-confidence">Confidence: {(f.confidence * 100).toFixed(0)}%</span>
                    </header>
                    <div className="finding-summary">{f.summary}</div>
                    <div className="finding-hypothesis">Hypothesis: {f.hypothesis}</div>
                    <div className="finding-meta">Evidence items: {f.evidence?.length || 0} · Next actions: {f.next_actions?.length || 0}</div>
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === 'hypotheses' && (
            <div className="panel active">
              {currentState.hypotheses?.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-state-icon">∅</div>
                  <p>No hypotheses yet</p>
                </div>
              ) : (
                currentState.hypotheses.map((h: any, idx: number) => (
                  <div key={idx} className="hypothesis-card">
                    <header>
                      <span className="hypothesis-title">Hypothesis {idx + 1}</span>
                      <span className="hypothesis-confidence">{(h.confidence * 100).toFixed(0)}%</span>
                    </header>
                    <div className="hypothesis-description">{h.description}</div>
                    <div className="hypothesis-meta">
                      Status: {h.status} · Supporting: {h.supporting_evidence?.length || 0} · Contradicting: {h.contradicting_evidence?.length || 0}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === 'recommendations' && (
            <div className="panel active">
              {currentState.recommendations?.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-state-icon">∅</div>
                  <p>No recommendations yet</p>
                </div>
              ) : (
                currentState.recommendations.map((r: any, idx: number) => (
                  <div key={idx} className="recommendation-card">
                    <header>
                      <span className="recommendation-title">Recommendation {idx + 1}</span>
                      <span className={`badge badge-${r.status}`}>{r.status}</span>
                    </header>
                    <div className="recommendation-action"><strong>Action:</strong> {r.action}</div>
                    <div className="recommendation-rationale"><strong>Rationale:</strong> {r.rationale}</div>
                    <div className="recommendation-risk"><strong>Risk:</strong> {r.risk}</div>
                    <div className="recommendation-meta">
                      <span>Confidence: {(r.confidence * 100).toFixed(0)}%</span>
                      <span>Approval: {r.requires_approval ? 'Required' : 'Not required'}</span>
                    </div>
                    {r.requires_approval && r.status === 'pending' && (
                      <div className="recommendation-actions">
                        <button className="btn btn-primary" style={{ fontSize: '12px' }} onClick={() => handleApprove(idx)}>Approve</button>
                        <button className="btn btn-danger" style={{ fontSize: '12px' }} onClick={() => handleReject(idx)}>Reject</button>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === 'timeline' && (
            <div className="panel active">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-md)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)' }}>
                  <span className={`connection-status ${connected ? 'connected' : 'disconnected'}`}>
                    {connected ? 'Live' : 'Disconnected'}
                  </span>
                  {streamError && <span className="badge badge-failed">SSE Error</span>}
                </div>
              </div>
              <div className="event-feed">
                {(currentState.timeline || []).slice().reverse().map((event: any, idx: number) => (
                  <div key={idx} className="event-item">
                    <span className="event-time">{formatTime(event.timestamp)}</span>
                    <span className="event-type">{event.type.replace(/_/g, ' ')}</span>
                    <span className="event-description">{event.description}</span>
                    {event.agent && <span className="event-agent">{event.agent}</span>}
                  </div>
                ))}
                {(currentState.timeline || []).length === 0 && (
                  <div className="empty-state" style={{ padding: 'var(--spacing-xl)' }}>
                    <div className="empty-state-icon">∅</div>
                    <p>No timeline events yet</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <aside>
          {/* Status Panel */}
          <div className="card" style={{ marginBottom: 'var(--spacing-md)', position: 'sticky', top: 'var(--spacing-lg)' }}>
            <h3 style={{ marginBottom: 'var(--spacing-md)', fontSize: '15px', fontWeight: 500 }}>Status</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-sm)' }}>
              <div className="key-value"><span className="key">Incident ID</span><span className="value"><code>{currentInvestigation.incident_id}</code></span></div>
              <div className="key-value"><span className="key">Status</span><span className="value"><span className={`badge ${getStatusBadge(currentInvestigation.status)}`}>{currentInvestigation.status}</span></span></div>
              <div className="key-value"><span className="key">Stage</span><span className="value"><code>{currentStage}</code></span></div>
              <div className="key-value"><span className="key">Progress</span><span className="value">{currentInvestigation.progress.toFixed(0)}%</span></div>
              <div style={{ marginTop: 'var(--spacing-xs)' }}>
                <div className="progress-bar"><div className="progress-fill" style={{ width: `${currentInvestigation.progress}%` }}></div></div>
              </div>
              <div className="key-value"><span className="key">Created</span><span className="value">{currentInvestigation.created_at ? formatTime(currentInvestigation.created_at) : 'N/A'}</span></div>
              <div className="key-value"><span className="key">Started</span><span className="value">{currentInvestigation.started_at ? formatTime(currentInvestigation.started_at) : 'N/A'}</span></div>
              <div className="key-value"><span className="key">Completed</span><span className="value">{currentInvestigation.completed_at ? formatTime(currentInvestigation.completed_at) : 'N/A'}</span></div>
              <div className="key-value"><span className="key">Duration</span><span className="value">{formatDuration(currentInvestigation.started_at, currentInvestigation.completed_at)}</span></div>
              <div className="divider"></div>
              <div className="key-value"><span className="key">Evidence</span><span className="value"><strong>{currentInvestigation.evidence_count}</strong></span></div>
              <div className="key-value"><span className="key">Findings</span><span className="value"><strong>{currentInvestigation.findings_count}</strong></span></div>
              <div className="key-value"><span className="key">Hypotheses</span><span className="value"><strong>{currentState.hypotheses?.length || 0}</strong></span></div>
              <div className="key-value"><span className="key">Recommendations</span><span className="value"><strong>{currentInvestigation.recommendations_count}</strong></span></div>
              <div className="divider"></div>
              {currentInvestigation.error && (
                <div className="error-banner" style={{ marginTop: 'var(--spacing-sm)' }}>
                  Error: {currentInvestigation.error}
                </div>
              )}
            </div>
          </div>

          {/* Agents Panel */}
          <div className="card" style={{ position: 'sticky', top: 'calc(var(--spacing-lg) + 320px)' }}>
            <h3 style={{ marginBottom: 'var(--spacing-md)', fontSize: '15px', fontWeight: 500 }}>Agents</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-sm)' }}>
              {currentState.selected_agents?.length > 0 ? (
                currentState.selected_agents.map((agent: string) => (
                  <div key={agent} className={`agent-card ${getAgentStatusClass(agent, currentInvestigation.active_agents, currentInvestigation.completed_agents)}`}>
                    <span className="agent-dot"></span>
                    <span className="agent-name">{agent}</span>
                    <span className="agent-status">{getAgentStatusText(agent, currentInvestigation.active_agents, currentInvestigation.completed_agents)}</span>
                  </div>
                ))
              ) : (
                ['Observability Agent', 'Repository Agent', 'Database Agent'].map(agent => {
                  const isSelected = currentInvestigation.active_agents.includes(agent) || currentInvestigation.completed_agents.includes(agent);
                  return (
                    <div key={agent} className={`agent-card ${getAgentStatusClass(agent, currentInvestigation.active_agents, currentInvestigation.completed_agents)}`} style={{ opacity: isSelected ? 1 : 0.5 }}>
                      <span className="agent-dot"></span>
                      <span className="agent-name">{agent}</span>
                      <span className="agent-status">{getAgentStatusText(agent, currentInvestigation.active_agents, currentInvestigation.completed_agents)}</span>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}