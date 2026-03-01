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

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  login: () => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const logoutRef = useRef<() => Promise<void>>();

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout');
    } catch {
      // ignore — cookies may already be gone
    }
    setIsAuthenticated(false);
  }, []);

  // Keep ref in sync for use in interceptor (avoids stale closure)
  logoutRef.current = logout;

  // On mount: check session + set up 401 interceptor with auto-refresh
  useEffect(() => {
    api
      .get('/auth/me')
      .then(() => setIsAuthenticated(true))
      .catch(() => setIsAuthenticated(false))
      .finally(() => setIsLoading(false));

    // Interceptor: on 401, try to refresh once; if that also fails, auto-logout.
    // Concurrent 401s are queued — only one refresh request is made.
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

  const login = useCallback(() => {
    setIsAuthenticated(true);
  }, []);

  const value = useMemo(
    () => ({ isAuthenticated, isLoading, login, logout }),
    [isAuthenticated, isLoading, login, logout],
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
