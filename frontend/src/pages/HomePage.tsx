import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import Button from '../components/Shared/Button';
import './HomePage.css';

export default function HomePage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="home-page">
      <div className="home-hero">
        <span className="home-emoji animate-float">🌟</span>
        <h1 className="home-title animate-fade-in">
          欢迎来到<br />故事共创世界！
        </h1>
        <p className="home-subtitle animate-slide-up">
          {user ? `你好，${user.display_name || user.username}！` : '和故事导演一起，创造属于你的精彩故事吧~'}
        </p>
      </div>

      <div className="home-actions animate-slide-up">
        <Button variant="primary" size="lg" onClick={() => navigate('/characters')}>
          🎭 选择角色，开始冒险
        </Button>
        <Button variant="secondary" size="lg" onClick={() => navigate('/gallery')}>
          📚 看看我的故事
        </Button>
      </div>

      <div className="home-features">
        <div className="home-feature">
          <span>🎬</span>
          <h3>AI 故事导演</h3>
          <p>专业的故事导演陪你一起创作</p>
        </div>
        <div className="home-feature">
          <span>🎨</span>
          <h3>自由创作</h3>
          <p>你想怎么编就怎么编，没有标准答案</p>
        </div>
        <div className="home-feature">
          <span>📖</span>
          <h3>专属故事书</h3>
          <p>每个故事都会被保存，成为你的专属故事书</p>
        </div>
      </div>
    </div>
  );
}
