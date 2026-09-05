const API_BASE = '/api/v1';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

export const api = {
  scenarios: {
    list: () => fetchJson<{ scenarios: string[] }>('/scenarios'),
    get: (name: string) => fetchJson<any>(`/scenarios/${encodeURIComponent(name)}`),
  },

  investigations: {
    create: (data: {
      scenario?: string;
      incident?: any;
      context?: any;
      use_llm?: boolean;
    }) => fetchJson<any>('/investigations', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

    list: () => fetchJson<{ investigations: any[] }>('/investigations'),

    get: (id: string) => fetchJson<any>(`/investigations/${id}`),

    getState: (id: string) => fetchJson<any>(`/investigations/${id}/state`),

    getTimeline: (id: string) => fetchJson<{ timeline: any[] }>(`/investigations/${id}/timeline`),

    getEvidence: (id: string) => fetchJson<{ evidence: any[] }>(`/investigations/${id}/evidence`),

    getFindings: (id: string) => fetchJson<{ findings: any[] }>(`/investigations/${id}/findings`),

    getRecommendations: (id: string) => fetchJson<{ recommendations: any[] }>(`/investigations/${id}/recommendations`),

    approveRecommendation: (id: string, index: number, note?: string) =>
      fetchJson<any>(`/investigations/${id}/recommendations/${index}/approve`, {
        method: 'POST',
        body: JSON.stringify({ note }),
      }),

    rejectRecommendation: (id: string, index: number, note?: string) =>
      fetchJson<any>(`/investigations/${id}/recommendations/${index}/reject`, {
        method: 'POST',
        body: JSON.stringify({ note }),
      }),

    stream: (id: string): EventSource => {
      const url = `${API_BASE}/investigations/${id}/stream`;
      return new EventSource(url);
    },
  },
};