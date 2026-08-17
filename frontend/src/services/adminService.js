/**
 * Admin Service for IncidentMind
 * Consumes existing backend administrative REST APIs (/api/v1/admin/dashboard & /api/v1/admin/users).
 * Provides resilient fallback metrics for standalone local testing.
 */

const API_BASE_URL = 'http://44.213.103.173:8000/api/v1';

function getAuthHeaders() {
  const token = localStorage.getItem('incidentmind_token');
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

const MOCK_ADMIN_METRICS = {
  activeIncidents: 3,
  resolvedIncidents: 142,
  totalUsers: 48,
  activeEmployees: 42,
  activeAdmins: 6,
  mttrReductionPercent: 68.4,
  aiRecommendationAccuracy: 96.4,
  vectorMemoriesCount: 1284,
  nodeClusterHealth: 'HEALTHY',
  
  // Solution effectiveness breakdown across all 5 outcome types
  solutionEffectiveness: {
    success: 184,
    failure: 24,
    partial: 12,
    rejected: 8,
    unknown: 4,
    totalAttempts: 232,
    successRate: 79.3
  },

  // Solution Leaderboard (Reward & Credit system)
  solutionLeaderboard: [
    { rank: 1, fixTitle: 'Scale CockroachDB max_connections & flush idle cursors', category: 'Database', successCount: 42, rewardPoints: 850, author: 'Alex Rivera' },
    { rank: 2, fixTitle: 'Lower bcrypt work factor to 10 with Redis token caching', category: 'Backend API', successCount: 38, rewardPoints: 760, author: 'Jordan Lee' },
    { rank: 3, fixTitle: 'Wrap boto3 Bedrock call with exponential backoff jitter', category: 'AI Service', successCount: 29, rewardPoints: 580, author: 'Sarah Chen' },
    { rank: 4, fixTitle: 'Flush ingress DNS routing table and restart pod', category: 'Infrastructure', successCount: 21, rewardPoints: 420, author: 'Taylor Vance' }
  ],

  // Employee usage metrics
  employeeUsage: [
    { name: 'Alex Rivera', email: 'employee@company.com', title: 'L2 Support Engineer', resolvedCount: 34, rewardPoints: 850, lastActive: '5m ago' },
    { name: 'Jordan Lee', email: 'user@company.com', title: 'DevOps Specialist', resolvedCount: 28, rewardPoints: 760, lastActive: '18m ago' },
    { name: 'Sarah Chen', email: 'admin@company.com', title: 'Lead SRE & Admin', resolvedCount: 45, rewardPoints: 980, lastActive: 'Now' },
    { name: 'Taylor Vance', email: 'taylor@company.com', title: 'Infrastructure Engineer', resolvedCount: 19, rewardPoints: 420, lastActive: '2h ago' }
  ],

  // Category distribution
  categoryDistribution: [
    { category: 'Database (CockroachDB)', count: 54, percent: 38 },
    { category: 'Backend API (FastAPI)', count: 42, percent: 30 },
    { category: 'AI Service (Bedrock)', count: 28, percent: 20 },
    { category: 'Infrastructure / Cloud', count: 18, percent: 12 }
  ]
};

const MOCK_USERS = [
  { id: 'usr_adm_001', name: 'Sarah Chen', email: 'admin@company.com', role: 'admin', title: 'Lead SRE & Admin', status: 'Active', joinedDate: '2025-11-10' },
  { id: 'usr_emp_001', name: 'Alex Rivera', email: 'employee@company.com', role: 'employee', title: 'L2 Support Engineer', status: 'Active', joinedDate: '2026-01-15' },
  { id: 'usr_emp_002', name: 'Jordan Lee', email: 'user@company.com', role: 'employee', title: 'DevOps Specialist', status: 'Active', joinedDate: '2026-02-01' },
  { id: 'usr_emp_003', name: 'Taylor Vance', email: 'taylor@company.com', role: 'employee', title: 'Infrastructure Engineer', status: 'Active', joinedDate: '2026-02-20' },
  { id: 'usr_adm_002', name: 'Marcus Brody', email: 'marcus@company.com', role: 'admin', title: 'IT Operations Manager', status: 'Active', joinedDate: '2025-12-05' }
];

export const adminService = {
  /**
   * Fetches administrative dashboard metrics
   */
  async getDashboardMetrics() {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/dashboard`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        const realMetrics = data.metrics || {};
        const realSolution = data.solution_analytics || {};
        const realStatus = data.system_status || {};
        
        return {
          activeIncidents: realMetrics.active_incidents ?? 0,
          resolvedIncidents: realMetrics.resolved_incidents ?? 0,
          totalUsers: data.user_counts_by_role ? (data.user_counts_by_role.employee + data.user_counts_by_role.admin) : 0,
          activeEmployees: data.user_counts_by_role ? data.user_counts_by_role.employee : 0,
          activeAdmins: data.user_counts_by_role ? data.user_counts_by_role.admin : 0,
          mttrReductionPercent: null,
          aiRecommendationAccuracy: null,
          vectorMemoriesCount: null,
          nodeClusterHealth: realStatus.database_connected ? 'HEALTHY' : 'DEGRADED',
          
          solutionEffectiveness: {
            success: realSolution.success_count ?? 0,
            failure: realSolution.failure_count ?? 0,
            partial: realSolution.partial_count ?? 0,
            rejected: realSolution.rejected_count ?? 0,
            unknown: realSolution.unknown_count ?? 0,
            totalAttempts: realSolution.total_solution_attempts ?? 0,
            successRate: realSolution.solution_success_rate_pct ?? 0.0
          },
          solutionLeaderboard: null,
          employeeUsage: null,
          categoryDistribution: null
        };
      }
    } catch (err) {
      console.warn('Backend API /api/v1/admin/dashboard offline. Using fallback metrics.', err);
    }
    return MOCK_ADMIN_METRICS;
  },

  /**
   * Fetches user list for RBAC management
   */
  async getUsers() {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/users`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        return await response.json();
      }
    } catch (err) {
      console.warn('Backend API /api/v1/admin/users offline. Using fallback user list.', err);
    }
    return MOCK_USERS;
  }
};
