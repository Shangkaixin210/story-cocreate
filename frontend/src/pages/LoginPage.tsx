import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { login, register } from '../api/endpoints';
import { ApiError } from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import Button from '../components/Shared/Button';
import './LoginPage.css';

export default function LoginPage() {
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const { login: authLogin } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    if (!username.trim() || !password.trim()) {
      setError('请填写用户名和密码哦~');
      return;
    }
    setLoading(true);
    try {
      const result = isRegister
        ? await register(username.trim(), password.trim(), displayName.trim() || undefined)
        : await login(username.trim(), password.trim());
      if (result.show_onboarding) {
        sessionStorage.setItem('ai_bole_show_onboarding', 'true');
      } else {
        sessionStorage.removeItem('ai_bole_show_onboarding');
      }
      authLogin(result.token, result.user);
      navigate('/');
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('网络出问题了，再试试吧！');
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card animate-pop-in">
        <div className="login-header">
          <span className="login-icon">🌟</span>
          <h1>AI 伯乐</h1>
          <p className="login-subtitle">故事共创 · 发现你的语言天赋</p>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <div className="login-field">
            <label>用户名</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="输入你的用户名"
              maxLength={20}
            />
          </div>

          {isRegister && (
            <div className="login-field">
              <label>显示名称（可选）</label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="让大家怎么称呼你？"
                maxLength={20}
              />
            </div>
          )}

          <div className="login-field">
            <label>密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="输入密码"
              maxLength={50}
            />
          </div>

          {error && <p className="login-error">😅 {error}</p>}

          <Button type="submit" variant="primary" size="lg" disabled={loading}>
            {loading ? '请稍候...' : isRegister ? '✨ 注册并开始' : '🚀 登录'}
          </Button>
        </form>

        <p className="login-toggle">
          {isRegister ? '已经有账号了？' : '还没有账号？'}
          <button onClick={() => { setIsRegister(!isRegister); setError(''); }}>
            {isRegister ? '去登录' : '注册一个'}
          </button>
        </p>
      </div>
    </div>
  );
}
