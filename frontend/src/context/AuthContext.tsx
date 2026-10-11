'use client';
import React, { createContext, useContext, useState, useEffect } from 'react';

export type UserRole = 'super_admin' | 'city_officer' | 'field_inspector' | 'public_viewer';

export interface UserProfile {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  department?: string;
  is_active: boolean;
}

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  role: UserRole;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => void;
  switchDemoRole: (role: UserRole) => Promise<void>;
  hasRole: (allowedRoles: UserRole[]) => boolean;
}

const GUEST_USER: UserProfile = {
  id: 0,
  email: 'public@aervia.in',
  full_name: 'Public Viewer',
  role: 'public_viewer',
  department: 'Public Citizen',
  is_active: true,
};

const DEMO_CREDENTIALS: Record<UserRole, { email: string; pass: string }> = {
  super_admin: { email: 'admin@aervia.gov.in', pass: 'Admin123!' },
  city_officer: { email: 'officer@ghmc.gov.in', pass: 'Officer123!' },
  field_inspector: { email: 'inspector@ghmc.gov.in', pass: 'Inspector123!' },
  public_viewer: { email: 'public@aervia.in', pass: 'Public123!' },
};

const AuthContext = createContext<AuthContextType>({
  user: GUEST_USER,
  token: null,
  role: 'public_viewer',
  isAuthenticated: false,
  isLoading: false,
  error: null,
  login: async () => false,
  logout: () => {},
  switchDemoRole: async () => {},
  hasRole: () => false,
});

import { apiUrl } from '@/utils/api';

const API_BASE = {
  toString() {
    return apiUrl('');
  }
};

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(GUEST_USER);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Restore stored session on mount
  useEffect(() => {
    try {
      const storedToken = localStorage.getItem('aervia_auth_token');
      const storedUser = localStorage.getItem('aervia_auth_user');
      if (storedToken && storedUser) {
        setToken(storedToken);
        setUser(JSON.parse(storedUser));
      } else {
        setUser(GUEST_USER);
      }
    } catch {
      setUser(GUEST_USER);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const login = async (email: string, password: string): Promise<boolean> => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        setError(data.detail || 'Authentication failed. Please verify credentials.');
        setIsLoading(false);
        return false;
      }

      const data = await resp.json();
      setToken(data.access_token);
      setUser(data.user);
      localStorage.setItem('aervia_auth_token', data.access_token);
      localStorage.setItem('aervia_auth_user', JSON.stringify(data.user));
      setIsLoading(false);
      return true;
    } catch (e: any) {
      setError(e.message || 'Network error connecting to auth server.');
      setIsLoading(false);
      return false;
    }
  };

  const logout = () => {
    setToken(null);
    setUser(GUEST_USER);
    setError(null);
    try {
      localStorage.removeItem('aervia_auth_token');
      localStorage.removeItem('aervia_auth_user');
    } catch {}
  };

  const switchDemoRole = async (targetRole: UserRole) => {
    const creds = DEMO_CREDENTIALS[targetRole];
    if (creds) {
      await login(creds.email, creds.pass);
    }
  };

  const hasRole = (allowedRoles: UserRole[]): boolean => {
    if (!user) return false;
    if (user.role === 'super_admin') return true;
    return allowedRoles.includes(user.role);
  };

  const role: UserRole = user?.role || 'public_viewer';
  const isAuthenticated = !!token && role !== 'public_viewer';

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        role,
        isAuthenticated,
        isLoading,
        error,
        login,
        logout,
        switchDemoRole,
        hasRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
