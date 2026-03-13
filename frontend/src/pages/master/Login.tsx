import { useState, type FormEvent } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../auth';
import api from '../../api/client';

export default function MasterLogin() {
  const [login, setLogin] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const auth = useAuth();

  const rawFrom = (location.state as { from?: { pathname: string } })?.from?.pathname;
  const from = rawFrom?.startsWith('/') && !rawFrom.startsWith('//') ? rawFrom : '/master/orders';

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await api.post('/auth/login', { login, password });
      await auth.login();
      navigate(from, { replace: true });
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Неверный логин или пароль';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <form onSubmit={handleSubmit} className="login-form">
        <h1>Вход для кальянщика</h1>

        {error && <div className="error">{error}</div>}

        <label>
          Логин
          <input
            type="text"
            value={login}
            onChange={(e) => setLogin(e.target.value)}
            required
            autoComplete="username"
          />
        </label>

        <label>
          Пароль
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </label>

        <button type="submit" disabled={loading} className="btn btn-primary">
          {loading ? 'Вход...' : 'Войти'}
        </button>
      </form>
    </div>
  );
}
