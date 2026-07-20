import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import './Header.css';

export default function Header() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate('/login');
  }

  return (
    <header className="app-header">
      <Link to="/" className="header-logo">
        <span className="logo-icon">🌟</span>
        <span className="logo-text">AI 伯乐 · 故事共创</span>
      </Link>
      {user && (
        <div className="header-user">
          <span className="header-greeting">你好，{user.display_name || user.username}</span>
          <button className="header-channel" onClick={() => navigate('/channel')}>
            {user.age_group === '4-7' ? '🧒 4-7岁' : '🧑 8-12岁'}
          </button>
          <button className="header-logout" onClick={handleLogout}>
            退出
          </button>
        </div>
      )}
    </header>
  );
}
