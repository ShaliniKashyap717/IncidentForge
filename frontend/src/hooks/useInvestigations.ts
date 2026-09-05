import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { InvestigationSummary, FullInvestigationState } from '../types/api';

export function useInvestigations() {
  const [investigations, setInvestigations] = useState<InvestigationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchInvestigations = useCallback(async () => {
    try {
      const response = await api.investigations.list();
      setInvestigations(response.investigations);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load investigations');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchInvestigations();
  }, [fetchInvestigations]);

  return { investigations, loading, error, refetch: fetchInvestigations };
}

export function useInvestigation(id: string | null) {
  const [investigation, setInvestigation] = useState<InvestigationSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchInvestigation = useCallback(async () => {
    if (!id) return;
    try {
      const data = await api.investigations.get(id);
      setInvestigation(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load investigation');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchInvestigation();
  }, [fetchInvestigation]);

  return { investigation, loading, error, refetch: fetchInvestigation };
}

export function useInvestigationState(id: string | null) {
  const [state, setState] = useState<FullInvestigationState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchState = useCallback(async () => {
    if (!id) return;
    try {
      const data = await api.investigations.getState(id);
      setState(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load investigation state');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchState();
  }, [fetchState]);

  return { state, loading, error, refetch: fetchState };
}

export function useScenarios() {
  const [scenarios, setScenarios] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchScenarios = useCallback(async () => {
    try {
      const response = await api.scenarios.list();
      setScenarios(response.scenarios);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load scenarios');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchScenarios();
  }, [fetchScenarios]);

  return { scenarios, loading, error, refetch: fetchScenarios };
}