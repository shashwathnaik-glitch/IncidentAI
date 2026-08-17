/**
 * Auth Service for IncidentMind
 * Attempts to connect to existing auth API (/api/v1/auth/login).
 * If API is unreachable or returns 404, gracefully falls back to mock authentication
 * so both Employee and Admin roles can be fully tested.
 */

const API_BASE_URL = 'http://44.213.103.173:8000/api/v1';

// Demo fallback accounts for standalone local testing
const DEMO_USERS = [
  {
    id: 'usr_emp_001',
    email: 'employee@company.com',
    password: 'password123',
    name: 'Alex Rivera',
    title: 'L2 Support Engineer',
    role: 'employee',
    avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80'
  },
  {
    id: 'usr_emp_002',
    email: 'user@company.com',
    password: 'password123',
    name: 'Jordan Lee',
    title: 'DevOps Specialist',
    role: 'employee',
    avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80'
  },
  {
    id: 'usr_adm_001',
    email: 'admin@company.com',
    password: 'admin123',
    name: 'Sarah Chen',
    title: 'IT Administrator & Lead SRE',
    role: 'admin',
    avatar: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150&auto=format&fit=crop&q=80'
  }
];

export const authService = {
  /**
   * Authenticates user via API endpoint or fallback demo accounts
   * @param {string} email 
   * @param {string} password 
   * @param {string} expectedRole 'employee' | 'admin'
   * @returns {Promise<{user: object, token: string}>}
   */
  async login(email, password, expectedRole = null) {
    const cleanEmail = email.trim().toLowerCase();

    // 1. Try real API backend first if available
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: cleanEmail, password }),
      });

      if (response.ok) {
        const data = await response.json();
        const token = data.access_token || data.token || `jwt_${Date.now()}`;
        const role = data.role || expectedRole || 'employee';
        
        const user = {
          email: cleanEmail,
          role: role,
          name: data.name || cleanEmail.split('@')[0],
          token
        };

        this.setSession(user, token);
        return { user, token };
      } else if (response.status === 401 || response.status === 403) {
        throw new Error('Invalid email or password. Please check your credentials.');
      }
    } catch (err) {
      // If it's explicit credential rejection from real API, rethrow
      if (err.message.includes('Invalid email or password')) {
        throw err;
      }
      // Otherwise network failure / 404 -> Fallback to client-side auth mechanism
      console.warn('API endpoint unavailable. Falling back to local authentication mode.', err);
    }

    // 2. Fallback local authentication logic for demo/offline use
    await new Promise((resolve) => setTimeout(resolve, 600)); // Simulate realistic network delay

    const matchedUser = DEMO_USERS.find(
      (u) => u.email.toLowerCase() === cleanEmail && u.password === password
    );

    if (!matchedUser) {
      // Check if user exists with wrong password or doesn't exist
      const userExists = DEMO_USERS.some((u) => u.email.toLowerCase() === cleanEmail);
      if (userExists) {
        throw new Error('Incorrect password. Please try again.');
      } else {
        throw new Error(`No account found matching "${cleanEmail}". Use demo credentials below.`);
      }
    }

    // Verify role matches if expectedRole was specified
    if (expectedRole && matchedUser.role !== expectedRole) {
      throw new Error(
        `Role Mismatch: Account "${cleanEmail}" is registered as an ${matchedUser.role.toUpperCase()}, not an ${expectedRole.toUpperCase()}. Please switch tabs or log in with proper role credentials.`
      );
    }

    const mockToken = `mock_jwt_token_${matchedUser.id}_${Date.now()}`;
    const userSession = {
      id: matchedUser.id,
      email: matchedUser.email,
      name: matchedUser.name,
      title: matchedUser.title,
      role: matchedUser.role,
      avatar: matchedUser.avatar
    };

    this.setSession(userSession, mockToken);
    return { user: userSession, token: mockToken };
  },

  setSession(user, token) {
    localStorage.setItem('incidentmind_user', JSON.stringify(user));
    localStorage.setItem('incidentmind_token', token);
  },

  clearSession() {
    localStorage.removeItem('incidentmind_user');
    localStorage.removeItem('incidentmind_token');
  },

  getCurrentUser() {
    try {
      const stored = localStorage.getItem('incidentmind_user');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  },

  getToken() {
    return localStorage.getItem('incidentmind_token');
  },

  isAuthenticated() {
    return !!this.getToken() && !!this.getCurrentUser();
  },

  getDemoUsers() {
    return DEMO_USERS;
  }
};
