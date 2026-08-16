/**
 * Incident & AI Memory Service for IncidentMind
 * Interacts with backend REST API (/api/v1/incidents & /api/v1/ai)
 * Provides persistent local state fallback with realistic sample data
 * incorporating CockroachDB outcome-aware memory models (v1.1).
 */

const API_BASE_URL = '/api/v1';

function getAuthHeaders() {
  const token = localStorage.getItem('incidentmind_token');
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

function mapBackendIncidentToFrontend(inc) {
  if (!inc) return inc;
  const revSeverityMap = {
    P1: 'CRITICAL',
    P2: 'HIGH',
    P3: 'MEDIUM',
    P4: 'LOW'
  };
  return {
    ...inc,
    status: inc.status ? inc.status.toUpperCase() : inc.status,
    severity: revSeverityMap[inc.severity] || inc.severity
  };
}

// Initial sample incident database with solution attempt memory histories
const INITIAL_INCIDENTS = [
  {
    id: 'INC-9104',
    title: 'CockroachDB Connection Pool Exhaustion in Pod-B',
    description: 'Services reporting HTTP 500 errors during traffic spikes. Database connection pool max limits reached.',
    severity: 'CRITICAL',
    category: 'Database',
    logs: 'FATAL: sorry, too many clients already\n[psycopg2.OperationalError] connection to server at "cockroach-db-0.service" failed: FATAL: remaining connection slots reserved for non-replication superuser connections',
    status: 'investigating',
    reporter: 'Alex Rivera',
    createdAt: new Date(Date.now() - 25 * 60000).toISOString(),
    resolutionOutcome: 'In progress: AI recommended scaling connection pool to 500.',
    solutionAttempts: [
      {
        id: 'att_101',
        solutionText: 'Increase DB max_connections from 100 to 500 & restart pgBouncer pooler',
        outcome: 'success',
        executionDurationMs: 420,
        confidenceAtExecution: 0.96,
        failureReason: null,
        performedBy: 'Alex Rivera',
        createdAt: new Date(Date.now() - 15 * 60000).toISOString()
      },
      {
        id: 'att_102',
        solutionText: 'Restart application pod instance without clearing pool',
        outcome: 'failure',
        executionDurationMs: 180,
        confidenceAtExecution: 0.40,
        failureReason: 'Connections locked immediately after boot due to lingering auth cursors',
        performedBy: 'Automated Agent',
        createdAt: new Date(Date.now() - 22 * 60000).toISOString()
      },
      {
        id: 'att_103',
        solutionText: 'Scale reader replica nodes manually',
        outcome: 'partial',
        executionDurationMs: 850,
        confidenceAtExecution: 0.65,
        failureReason: 'Mitigated read load but write pool remained 100% saturated',
        performedBy: 'Jordan Lee',
        createdAt: new Date(Date.now() - 24 * 60000).toISOString()
      }
    ],
    aiRecommendation: {
      summary: 'Scale CockroachDB max_connections parameter and restart proxy pooler service.',
      rootCause: 'Connection leak caused by unclosed DB cursors in legacy auth middleware during burst spikes.',
      confidence: 96,
      similarityScore: 0.94,
      requiresApproval: true,
      suggestedFix: 'Execute pooler reconfiguration and flush idle connections.',
      pastAttempts: [
        { id: 'att_101', solutionText: 'Increase DB max_connections from 100 to 500 & restart pgBouncer pooler', outcome: 'success', count: 7, lastReason: null },
        { id: 'att_102', solutionText: 'Restart application pod instance without clearing pool', outcome: 'failure', count: 3, lastReason: 'Connections locked immediately after boot' },
        { id: 'att_103', solutionText: 'Scale replica nodes manually', outcome: 'partial', count: 1, lastReason: 'Mitigated read load but write pool remained saturated' }
      ]
    }
  },
  {
    id: 'INC-9098',
    title: 'High Latency Spikes on Authentication Endpoint (/api/v1/auth/login)',
    description: 'P99 response time increased from 120ms to 4.8s. Users experiencing login timeouts.',
    severity: 'HIGH',
    category: 'Backend API',
    logs: 'WARN [AuthService] Password hash verification took 4520ms for user@company.com\nINFO [Bcrypt] CPU thread saturation detected on core 2',
    status: 'open',
    reporter: 'Jordan Lee',
    createdAt: new Date(Date.now() - 110 * 60000).toISOString(),
    resolutionOutcome: 'Open: Pending bcrypt work factor adjustment.',
    solutionAttempts: [
      {
        id: 'att_201',
        solutionText: 'Lower password hash cost factor to 10 & deploy patch',
        outcome: 'success',
        executionDurationMs: 310,
        confidenceAtExecution: 0.91,
        failureReason: null,
        performedBy: 'Sarah Chen',
        createdAt: new Date(Date.now() - 90 * 60000).toISOString()
      },
      {
        id: 'att_202',
        solutionText: 'Restart CPU thread pool without config change',
        outcome: 'rejected',
        executionDurationMs: 0,
        confidenceAtExecution: 0.50,
        failureReason: 'Engineer rejected temporary patch',
        performedBy: 'Jordan Lee',
        createdAt: new Date(Date.now() - 105 * 60000).toISOString()
      }
    ],
    aiRecommendation: {
      summary: 'Adjust bcrypt work factor from 14 to 10 and enable Redis token caching.',
      rootCause: 'Excessive bcrypt cost factor causing CPU starvation on auth pods.',
      confidence: 91,
      similarityScore: 0.89,
      requiresApproval: false,
      suggestedFix: 'Update AuthConfig work_factor environment variable to 10.',
      pastAttempts: [
        { id: 'att_201', solutionText: 'Lower password hash cost factor to 10 & deploy patch', outcome: 'success', count: 12, lastReason: null },
        { id: 'att_202', solutionText: 'Restart CPU thread pool without config change', outcome: 'rejected', count: 2, lastReason: 'Engineer rejected temporary patch' }
      ]
    }
  },
  {
    id: 'INC-9082',
    title: 'Amazon Bedrock API Throttling Exception',
    description: 'LLM reasoning agent returning 429 Too Many Requests during automated incident analysis.',
    severity: 'MEDIUM',
    category: 'AI Service',
    logs: 'botocore.exceptions.ClientError: An error occurred (ThrottlingException) when calling the InvokeModel operation: Rate limit exceeded',
    status: 'resolved',
    reporter: 'Sarah Chen',
    createdAt: new Date(Date.now() - 340 * 60000).toISOString(),
    resolvedAt: new Date(Date.now() - 280 * 60000).toISOString(),
    resolutionOutcome: 'Resolved: Enabled tenacity retry wrapper with exponential backoff.',
    solutionAttempts: [
      {
        id: 'att_301',
        solutionText: 'Wrap boto3 call with exponential backoff jitter decorator',
        outcome: 'success',
        executionDurationMs: 150,
        confidenceAtExecution: 0.99,
        failureReason: null,
        performedBy: 'Sarah Chen',
        createdAt: new Date(Date.now() - 280 * 60000).toISOString()
      }
    ],
    aiRecommendation: {
      summary: 'Apply exponential backoff retry policy with jitter in boto3 client configuration.',
      rootCause: 'Concurrent agent queries exceeding default AWS Bedrock quota of 200 TPM.',
      confidence: 99,
      similarityScore: 0.98,
      requiresApproval: false,
      suggestedFix: 'Enable tenacity retry wrapper with exponential backoff on Bedrock invocation.',
      pastAttempts: [
        { id: 'att_301', solutionText: 'Wrap boto3 call with exponential backoff jitter decorator', outcome: 'success', count: 15, lastReason: null }
      ]
    }
  }
];

function getStoredIncidents() {
  try {
    const data = localStorage.getItem('incidentmind_incidents');
    const list = data ? JSON.parse(data) : INITIAL_INCIDENTS;
    return list.map(mapBackendIncidentToFrontend);
  } catch {
    return INITIAL_INCIDENTS.map(mapBackendIncidentToFrontend);
  }
}

function saveStoredIncidents(incidents) {
  try {
    const mapped = incidents.map(inc => ({
      ...inc,
      status: inc.status ? inc.status.toLowerCase() : inc.status
    }));
    localStorage.setItem('incidentmind_incidents', JSON.stringify(mapped));
  } catch (err) {
    console.error('Failed to persist incidents:', err);
  }
}

export const incidentService = {
  async getIncidents() {
    try {
      const response = await fetch(`${API_BASE_URL}/incidents`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const list = await response.json();
        return Array.isArray(list) ? list.map(mapBackendIncidentToFrontend) : list;
      }
    } catch {
      // fallback handled
    }
    return getStoredIncidents();
  },

  /**
   * Returns paginated incident list with status and search filtering
   */
  async getIncidentsPaginated(page = 1, limit = 5, statusFilter = 'ALL', searchQuery = '') {
    // Try backend API first with pagination params
    try {
      const queryParams = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString(),
        status: statusFilter === 'ALL' ? '' : statusFilter.toLowerCase(),
        search: searchQuery
      });
      const response = await fetch(`${API_BASE_URL}/incidents?${queryParams}`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        const rawItems = data.items || data.incidents || data;
        const items = Array.isArray(rawItems) ? rawItems.map(mapBackendIncidentToFrontend) : rawItems;
        return {
          incidents: items,
          total: data.total || data.length,
          page: data.page || page,
          limit: data.limit || limit,
          totalPages: data.totalPages || Math.ceil((data.total || data.length) / limit)
        };
      }
    } catch {
      // Fallback to client-side pagination
    }

    const all = getStoredIncidents();
    const filtered = all.filter(inc => {
      const matchesStatus = statusFilter === 'ALL' || inc.status === statusFilter;
      const matchesSearch = !searchQuery ||
        inc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        inc.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
        inc.id.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesStatus && matchesSearch;
    });

    const total = filtered.length;
    const totalPages = Math.ceil(total / limit) || 1;
    const validPage = Math.min(Math.max(1, page), totalPages);
    const startIndex = (validPage - 1) * limit;
    const paginatedItems = filtered.slice(startIndex, startIndex + limit);

    return {
      incidents: paginatedItems,
      total,
      page: validPage,
      limit,
      totalPages
    };
  },

  /**
   * Fetches single incident detail by ID including un-merged solution attempts history
   */
  async getIncidentById(incidentId) {
    if (!incidentId) return null;

    try {
      const response = await fetch(`${API_BASE_URL}/incidents/${incidentId}`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const inc = await response.json();
        const mappedInc = mapBackendIncidentToFrontend(inc);
        try {
          const attemptsRes = await fetch(`${API_BASE_URL}/incidents/${incidentId}/attempts`, {
            headers: getAuthHeaders()
          });
          if (attemptsRes.ok) {
            const rawAttempts = await attemptsRes.ok ? await attemptsRes.json() : [];
            mappedInc.solutionAttempts = Array.isArray(rawAttempts)
              ? rawAttempts.map(att => ({
                  id: att.id,
                  solutionText: att.solution_text,
                  outcome: att.outcome,
                  failureReason: att.failure_reason,
                  performedBy: att.performed_by,
                  executionDurationMs: att.execution_duration_ms,
                  confidenceAtExecution: att.confidence_at_execution,
                  rewardInfo: att.reward_info,
                  createdAt: att.created_at
                }))
              : [];
          } else {
            mappedInc.solutionAttempts = [];
          }
        } catch {
          mappedInc.solutionAttempts = [];
        }
        return mappedInc;
      }
    } catch {
      // fallback
    }

    const all = getStoredIncidents();
    const found = all.find(i => i.id.toLowerCase() === incidentId.toLowerCase());
    return found || null;
  },

  async submitAndAnalyzeIncident(incidentData, reporterName = 'Support Engineer') {
    const severityMap = {
      'CRITICAL': 'P1',
      'HIGH': 'P2',
      'MEDIUM': 'P3',
      'LOW': 'P4'
    };

    const payload = {
      title: incidentData.title.trim(),
      description: incidentData.description.trim(),
      severity: severityMap[incidentData.severity] || 'P2',
      category: incidentData.category || 'Database',
      logs: incidentData.logs ? incidentData.logs.trim() : null
    };

    let createdIncident = null;

    try {
      const response = await fetch(`${API_BASE_URL}/incidents`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        createdIncident = await response.json();
        createdIncident = mapBackendIncidentToFrontend(createdIncident);
      } else if (response.status === 400 || response.status === 422) {
        const errorData = await response.json();
        throw new Error(errorData.detail || errorData.message || 'Invalid incident payload.');
      }
    } catch (err) {
      if (err.message.includes('Invalid incident payload')) {
        throw err;
      }
      console.warn('Backend API /api/v1/incidents unreachable. Using memory store fallback.', err);
    }

    if (!createdIncident) {
      await new Promise(resolve => setTimeout(resolve, 700));

      const simulatedAI = this.generateSimulatedAIRecommendation(payload);
      createdIncident = {
        id: `INC-${Math.floor(1000 + Math.random() * 9000)}`,
        title: payload.title,
        description: payload.description,
        severity: payload.severity,
        category: payload.category,
        logs: payload.logs,
        status: 'investigating',
        reporter: reporterName,
        createdAt: new Date().toISOString(),
        resolutionOutcome: 'Investigating with AI memory analysis.',
        solutionAttempts: [],
        aiRecommendation: simulatedAI
      };

      const currentList = getStoredIncidents();
      saveStoredIncidents([createdIncident, ...currentList]);
    }

    return createdIncident;
  },

  async getAIRecommendation(incidentId, logs = '') {
    try {
      const response = await fetch(`${API_BASE_URL}/ai/analyze`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          incident_id: incidentId,
          error_logs: logs || 'No log trace associated.',
          environment: 'production'
        })
      });
      if (response.ok) {
        return await response.json();
      }
    } catch (err) {
      console.warn('Backend API /api/v1/ai/analyze unreachable.', err);
    }
    return null;
  },

  async approveResolution(incidentId, solutionText, outcome = 'success', feedbackReason = null, operatorName = 'Operator') {
    const list = getStoredIncidents();
    const index = list.findIndex(i => i.id === incidentId);

    if (index === -1) {
      throw new Error(`Incident ${incidentId} not found.`);
    }

    const incident = list[index];
    incident.status = outcome === 'success' ? 'resolved' : 'investigating';
    if (outcome === 'success') {
      incident.resolvedAt = new Date().toISOString();
      incident.resolutionOutcome = `Resolved by ${operatorName}: ${solutionText}`;
    }

    // CRITICAL RULE: Solution attempts are added as separate immutable records — never merged or overwritten
    if (!incident.solutionAttempts) {
      incident.solutionAttempts = [];
    }

    const newAttempt = {
      id: `att_${Date.now()}_${Math.floor(Math.random() * 1000)}`,
      solutionText: solutionText || (incident.aiRecommendation ? incident.aiRecommendation.suggestedFix : 'Manual fix execution'),
      outcome: outcome, // 'success' | 'failure' | 'partial' | 'rejected' | 'unknown'
      executionDurationMs: Math.floor(150 + Math.random() * 500),
      confidenceAtExecution: incident.aiRecommendation ? incident.aiRecommendation.confidence / 100 : 0.90,
      failureReason: feedbackReason,
      performedBy: operatorName,
      createdAt: new Date().toISOString()
    };

    incident.solutionAttempts.unshift(newAttempt);

    list[index] = incident;
    saveStoredIncidents(list);

    try {
      await fetch(`${API_BASE_URL}/ai/approve`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          incident_id: incidentId,
          solution_text: solutionText,
          outcome: outcome,
          failure_reason: feedbackReason
        })
      });
    } catch {
      // fallback
    }

    return incident;
  },

  async rejectResolution(incidentId, rejectionReason, operatorName = 'Operator') {
    return this.approveResolution(incidentId, 'AI Recommendation Rejected', 'rejected', rejectionReason, operatorName);
  },

  generateSimulatedAIRecommendation(incident) {
    const text = `${incident.title} ${incident.description} ${incident.logs || ''}`.toLowerCase();

    if (text.includes('database') || text.includes('connection') || text.includes('postgres') || text.includes('cockroach')) {
      return {
        summary: 'CockroachDB connection limit threshold exceeded. Scale pool size & clear idle queries.',
        rootCause: 'Connection saturation caused by unclosed transaction sessions.',
        confidence: 95,
        similarityScore: 0.92,
        requiresApproval: true,
        suggestedFix: 'ALTER RANGE CONSTRAINTS SET max_connections = 500; SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = "idle";',
        pastAttempts: [
          { id: 'sim_1', solutionText: 'Terminate idle backend connections and scale pool limit', outcome: 'success', count: 8, lastReason: null },
          { id: 'sim_2', solutionText: 'Hard reboot cluster node during active traffic', outcome: 'failure', count: 2, lastReason: 'Triggered cascading failover alert' }
        ]
      };
    } else {
      return {
        summary: 'Standard operational anomaly detected. Correlated with historical infrastructure patterns.',
        rootCause: 'Service response degradation due to transient network packet loss.',
        confidence: 85,
        similarityScore: 0.81,
        requiresApproval: false,
        suggestedFix: 'Flush DNS cache, verify ingress routing tables, and restart service pod.',
        pastAttempts: [
          { id: 'sim_5', solutionText: 'Flush ingress DNS routing table and restart pod', outcome: 'success', count: 4, lastReason: null }
        ]
      };
    }
  }
};
