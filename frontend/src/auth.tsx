/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import api from './api/client';

export interface UserInfo {
  id: number;
  venue_id: number;
  role: string;
  display_name: string;
}

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: UserInfo | null;
  login: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState<UserInfo | null>(null);
  const logoutRef = useRef<(() => Promise<void>) | undefined>(undefined);

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout');
    } catch {
      // ignore — cookies may already be gone
    }
    setIsAuthenticated(false);
    setUser(null);
  }, []);

  // Keep ref in sync for use in interceptor (avoids stale closure)
  useEffect(() => {
    logoutRef.current = logout;
  }, [logout]);

  // On mount: check session + set up 401 interceptor with auto-refresh.
  // Concurrent 401s are queued — only one refresh request is made.
  useEffect(() => {
    api
      .get<UserInfo>('/auth/me')
      .then((r) => { setIsAuthenticated(true); setUser(r.data); })
      .catch(() => { setIsAuthenticated(false); setUser(null); })
      .finally(() => setIsLoading(false));

    let isRefreshing = false;
    let refreshQueue: Array<(ok: boolean) => void> = [];

    const interceptorId = api.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        // Don't intercept auth endpoints themselves
        const url = originalRequest?.url ?? '';
        if (url.includes('/auth/login') || url.includes('/auth/refresh') || url.includes('/auth/logout')) {
          return Promise.reject(error);
        }

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          if (isRefreshing) {
            // Queue concurrent 401 requests — wait for the single refresh
            return new Promise((resolve, reject) => {
              refreshQueue.push((ok) =>
                ok ? resolve(api(originalRequest)) : reject(error),
              );
            });
          }

          isRefreshing = true;
          try {
            await api.post('/auth/refresh');
            isRefreshing = false;
            refreshQueue.forEach((cb) => cb(true));
            refreshQueue = [];
            return api(originalRequest);
          } catch {
            isRefreshing = false;
            refreshQueue.forEach((cb) => cb(false));
            refreshQueue = [];
            logoutRef.current?.();
            return Promise.reject(error);
          }
        }

        return Promise.reject(error);
      },
    );

    return () => {
      api.interceptors.response.eject(interceptorId);
    };
  }, []);

  const login = useCallback(async () => {
    try {
      const r = await api.get<UserInfo>('/auth/me');
      setUser(r.data);
      setIsAuthenticated(true);
    } catch {
      setIsAuthenticated(false);
      setUser(null);
    }
  }, []);

  const value = useMemo(
    () => ({ isAuthenticated, isLoading, user, login, logout }),
    [isAuthenticated, isLoading, user, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be inside AuthProvider');
  return ctx;
}

export function PrivateRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <div className="loading">Загрузка...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/admin/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}

const MASTER_ROLES = new Set(['hookah_master', 'admin', 'owner']);

export function MasterRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading, user } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <div className="loading">Загрузка...</div>;
  }

  if (!isAuthenticated || !user || !MASTER_ROLES.has(user.role)) {
    return <Navigate to="/master/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
