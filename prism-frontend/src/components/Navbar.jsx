import { Link, useNavigate } from 'react-router-dom';
import { LogOut, LayoutDashboard } from 'lucide-react';
import './Navbar.css';

export default function Navbar({ showLogout = false }) {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    navigate('/login');
  };

  return (
    <nav className="navbar" id="main-navbar">
      <Link to={showLogout ? '/dashboard' : '/'} className="navbar-logo">
        <div className="navbar-logo-icon">P</div>
        <span className="navbar-logo-text">
          PR<span className="logo-accent">ism</span>
        </span>
      </Link>

      <div className="navbar-actions">
        {showLogout ? (
          <>
            <Link to="/dashboard" className="navbar-link">
              <LayoutDashboard size={16} />
              Dashboard
            </Link>
            <button onClick={handleLogout} className="btn-ghost navbar-logout" id="logout-btn">
              <LogOut size={16} />
              Sign Out
            </button>
          </>
        ) : (
          <Link to="/login" className="btn-secondary" id="signin-btn">
            Sign In
          </Link>
        )}
      </div>
    </nav>
  );
}
