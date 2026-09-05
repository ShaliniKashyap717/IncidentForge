export interface Incident {
  id: string;
  title: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  affected_services: string[];
  status: string;
}

export interface InvestigationSummary {
  investigation_id: string;
  incident_id: string;
  incident_title: string;
  status: string;
  stage: string;
  progress: number;
  error: string | null;
  evidence_count: number;
  findings_count: number;
  recommendations_count: number;
  active_agents: string[];
  completed_agents: string[];
  pending_tasks: string[];
  completed_tasks: string[];
}

export interface InvestigationListResponse {
  investigations: InvestigationSummary[];
}

export interface FullInvestigationState {
  incident: Incident;
  status: string;
  stage: string;
  progress: number;
  error: string | null;
  investigation_started_at: string;
  evidence: Evidence[];
  findings: Finding[];
  hypotheses: Hypothesis[];
  recommendations: Recommendation[];
  active_agents: string[];
  completed_agents: string[];
  pending_tasks: string[];
  completed_tasks: string[];
  timeline: TimelineEvent[];
}

export interface Evidence {
  id?: string;
  type: 'metric' | 'log' | 'trace' | 'code' | 'deployment' | 'database';
  source: string;
  description: string;
  relevance: number;
  timestamp?: string | null;
}

export interface Finding {
  agent: string;
  summary: string;
  hypothesis: string;
  confidence: number;
  evidence: Evidence[];
  next_actions: string[];
}

export interface Hypothesis {
  description: string;
  confidence: number;
  supporting_evidence: Evidence[];
  contradicting_evidence: Evidence[];
  status: string;
}

export interface Recommendation {
  action: string;
  rationale: string;
  risk: string;
  confidence: number;
  requires_approval: boolean;
  status: 'pending' | 'approved' | 'rejected';
}

export interface TimelineEvent {
  timestamp: string;
  type: string;
  description: string;
  agent?: string | null;
}

export interface ScenarioListResponse {
  scenarios: string[];
}

export interface ScenarioResponse {
  name: string;
  incident: Incident;
  logs: LogEntry[];
  metrics: any;
  traces: any;
  deployments: any;
  commits: any;
}

export interface LogEntry {
  timestamp: string;
  severity: string;
  service: string;
  message: string;
}

export interface StreamEvent {
  type: 'state' | 'event' | 'complete';
  data: any;
}