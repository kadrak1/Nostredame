/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import api from './api/client';

export interface GuestProfile {
  id: number;
  name: string;
  phone_masked: string;
  first_visit: string;
  total_bookings: number;
  total_orders: number;
}

interface GuestAuthState {
  guest: GuestProfile | null;
  isLoading: boolean;
  login: (phone: string) => Promise<{ name: string; is_new: boolean }>;
  logout: () => Promise<void>;
}

const GuestAuthContext = createContext<GuestAuthState | null>(null);

export function GuestAuthProvider({ children }: { children: ReactNode }) {
  const [guest, setGuest] = useState<GuestProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // On mount: restore session from httpOnly cookie
  useEffect(() => {
    api
      .get<GuestProfile>('/guest/me')
      .then((r) => setGuest(r.data))
      .catch(() => setGuest(null))
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (phone: string) => {
    const r = await api.post<{ guest_id: number; name: string; is_new: boolean }>(
      '/auth/guest',
      { phone },
    );
    // Fetch full profile to update context
    const profile = await api.get<GuestProfile>('/guest/me');
    setGuest(profile.data);
    return { name: r.data.name, is_new: r.data.is_new };
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/guest/logout');
    } catch {
      // ignore — cookie may already be gone
    }
    setGuest(null);
  }, []);

  const value = useMemo(
    () => ({ guest, isLoading, login, logout }),
    [guest, isLoading, login, logout],
  );

  return <GuestAuthContext.Provider value={value}>{children}</GuestAuthContext.Provider>;
}

export function useGuest(): GuestAuthState {
  const ctx = useContext(GuestAuthContext);
  if (!ctx) throw new Error('useGuest must be inside GuestAuthProvider');
  return ctx;
}
