import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Layout({ children }) {
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="app-shell">
      <header className="app-header">
        <Link to="/" className="brand">
          <span className="leaf" role="img" aria-label="leaf">
            🌳
          </span>
          Darukaa.Earth
        </Link>
        <nav>
          {isAuthenticated && (
            <>
              {user?.email && <span className="user-email">{user.email}</span>}
              <button className="btn btn-outline-light" onClick={handleLogout}>
                Logout
              </button>
            </>
          )}
        </nav>
      </header>
      <main className="app-main">{children}</main>
    </div>
  );
}
