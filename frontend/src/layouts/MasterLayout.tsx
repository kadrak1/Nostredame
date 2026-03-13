import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';

const NAV_ITEMS = [
  { to: '/master/orders', label: 'Очередь' },
  { to: '/master/history', label: 'История' },
  { to: '/master/recommendations', label: 'Рекомендации' },
];

export default function MasterLayout() {
  const { logout, user } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate('/master/login');
  }

  return (
    <div className="master-layout">
      <header className="master-header">
        <div className="master-header-brand">
          <span className="master-header-title">HookahBook</span>
          <span className="master-header-subtitle">Панель кальянщика</span>
        </div>

        <nav className="master-tabs">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `master-tab${isActive ? ' active' : ''}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="master-header-actions">
          {user && <span className="master-username">{user.display_name}</span>}
          <button onClick={handleLogout} className="btn-logout">
            Выйти
          </button>
        </div>
      </header>

      <main className="master-main">
        <Outlet />
      </main>
    </div>
  );
}
