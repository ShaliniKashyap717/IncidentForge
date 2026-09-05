import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useScenarios } from '../hooks/useInvestigations';
import { api } from '../api/client';

export function NewInvestigation() {
  const navigate = useNavigate();
  const { scenarios, loading: scenariosLoading } = useScenarios();
  const [mode, setMode] = useState<'scenario' | 'manual'>('scenario');
  const [scenario, setScenario] = useState('');
  const [incident, setIncident] = useState({
    id: '',
    title: '',
    description: '',
    severity: 'high',
    affected_services: '',
  });
  const [context, setContext] = useState('');
  const [useLlm, setUseLlm] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setCreating(true);

    try {
      let payload: any = { use_llm: useLlm };

      if (mode === 'scenario') {
        if (!scenario) {
          setError('Please select a scenario');
          setCreating(false);
          return;
        }
        payload.scenario = scenario;
      } else {
        if (!incident.id || !incident.title) {
          setError('Incident ID and title are required');
          setCreating(false);
          return;
        }
        payload.incident = {
          ...incident,
          affected_services: incident.affected_services.split(',').map(s => s.trim()).filter(Boolean),
        };
        if (context.trim()) {
          try {
            payload.context = JSON.parse(context);
          } catch {
            setError('Context must be valid JSON');
            setCreating(false);
            return;
          }
        }
      }

      const response = await api.investigations.create(payload);
      navigate(`/investigations/${response.investigation_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create investigation');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="container" style={{ maxWidth: '800px' }}>
      <h1 className="page-title">New Investigation</h1>

      <form onSubmit={handleSubmit}>
        <div className="card" style={{ marginBottom: 'var(--spacing-md)' }}>
          <h3 style={{ marginBottom: 'var(--spacing-md)' }}>Investigation Mode</h3>
          <div style={{ display: 'flex', gap: 'var(--spacing-md)' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)', cursor: 'pointer' }}>
              <input
                type="radio"
                name="mode"
                value="scenario"
                checked={mode === 'scenario'}
                onChange={() => setMode('scenario')}
              />
              <strong>Scenario</strong> - Use a predefined scenario with telemetry data
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)', cursor: 'pointer' }}>
              <input
                type="radio"
                name="mode"
                value="manual"
                checked={mode === 'manual'}
                onChange={() => setMode('manual')}
              />
              <strong>Manual</strong> - Provide incident and context manually
            </label>
          </div>
        </div>

        {mode === 'scenario' && (
          <div className="card" style={{ marginBottom: 'var(--spacing-md)' }}>
            <h3 style={{ marginBottom: 'var(--spacing-md)' }}>Select Scenario</h3>
            <div className="form-group">
              <label className="form-label">Scenario</label>
              <select
                value={scenario}
                onChange={(e) => setScenario(e.target.value)}
                disabled={scenariosLoading}
              >
                <option value="">Select a scenario...</option>
                {scenariosLoading ? (
                  <option disabled>Loading...</option>
                ) : (
                  scenarios.map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))
                )}
              </select>
              {scenariosLoading && <small style={{ color: 'var(--color-text-secondary)' }}>Loading scenarios...</small>}
            </div>
          </div>
        )}

        {mode === 'manual' && (
          <div className="card" style={{ marginBottom: 'var(--spacing-md)' }}>
            <h3 style={{ marginBottom: 'var(--spacing-md)' }}>Incident Details</h3>
            <div style={{ display: 'grid', gap: 'var(--spacing-md)' }}>
              <div className="form-group">
                <label className="form-label">Incident ID</label>
                <input
                  type="text"
                  value={incident.id}
                  onChange={(e) => setIncident({ ...incident, id: e.target.value })}
                  placeholder="INC-2026-XXXX"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Title</label>
                <input
                  type="text"
                  value={incident.title}
                  onChange={(e) => setIncident({ ...incident, title: e.target.value })}
                  placeholder="Payment API latency spike"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Description</label>
                <textarea
                  value={incident.description}
                  onChange={(e) => setIncident({ ...incident, description: e.target.value })}
                  rows={3}
                  placeholder="Checkout requests to the payment service are intermittently taking 4-8s..."
                />
              </div>
              <div className="form-group">
                <label className="form-label">Severity</label>
                <select
                  value={incident.severity}
                  onChange={(e) => setIncident({ ...incident, severity: e.target.value })}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Affected Services (comma-separated)</label>
                <input
                  type="text"
                  value={incident.affected_services}
                  onChange={(e) => setIncident({ ...incident, affected_services: e.target.value })}
                  placeholder="payment-api, checkout-api, inventory-api"
                />
              </div>
            </div>
          </div>
        )}

        <div className="card" style={{ marginBottom: 'var(--spacing-md)' }}>
          <h3 style={{ marginBottom: 'var(--spacing-md)' }}>Advanced Options</h3>
          <div className="form-group">
            <label className="form-label">Context (JSON, optional)</label>
            <textarea
              value={context}
              onChange={(e) => setContext(e.target.value)}
              rows={6}
              placeholder='{"logs": [], "metrics": {}, "traces": {}, "deployments": {}, "commits": {}}'
              style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}
            />
          </div>
          <div className="form-group">
            <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={useLlm}
                onChange={(e) => setUseLlm(e.target.checked)}
              />
              Use LLM for coordination (requires GOOGLE_API_KEY)
            </label>
          </div>
        </div>

        {error && (
          <div className="card" style={{ borderColor: 'var(--color-error)', marginBottom: 'var(--spacing-md)' }}>
            <p style={{ color: 'var(--color-error)' }}>{error}</p>
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--spacing-md)' }}>
          <button type="button" className="btn btn-secondary" onClick={() => navigate('/')}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={creating}>
            {creating ? 'Creating...' : 'Start Investigation'}
          </button>
        </div>
      </form>
    </div>
  );
}