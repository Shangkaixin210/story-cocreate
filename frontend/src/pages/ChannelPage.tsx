import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { apiFetch } from '../api/client';
import './ChannelPage.css';

export default function ChannelPage() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const [selected, setSelected] = useState<string>(user?.age_group || '');
  const [saving, setSaving] = useState(false);

  async function handleConfirm() {
    if (!selected || !user) return;
    setSaving(true);
    try {
      await apiFetch(`/auth/me/channel?age_group=${selected}`, { method: 'PATCH' });
      setUser({ ...user, age_group: selected });
      navigate('/');
    } catch {
      // fallback: save anyway and continue
      setUser({ ...user, age_group: selected });
      navigate('/');
    }
  }

  return (
    <div className="channel-page">
      <div className="channel-card animate-pop-in">
        <span className="channel-hero-emoji">🎯</span>
        <h1 className="channel-hero-title">选择你的故事通道</h1>
        <p className="channel-hero-desc">
          我们会根据你的年龄，匹配最适合的故事风格、词汇难度和互动方式
        </p>

        <div className="channel-options">
          <button
            className={`channel-option ${selected === '4-7' ? 'selected young' : ''}`}
            onClick={() => setSelected('4-7')}
          >
            <span className="channel-option-emoji">🧒</span>
            <span className="channel-option-label">幼儿通道</span>
            <span className="channel-option-age">4 - 7 岁</span>
            <span className="channel-option-desc">
              口语互动 · 画面引导 · 简单选择<br />
              用颜色和声音描绘世界
            </span>
          </button>

          <button
            className={`channel-option ${selected === '8-12' ? 'selected older' : ''}`}
            onClick={() => setSelected('8-12')}
          >
            <span className="channel-option-emoji">🧑</span>
            <span className="channel-option-label">学龄通道</span>
            <span className="channel-option-age">8 - 12 岁</span>
            <span className="channel-option-desc">
              完整叙事 · 角色创作 · 深度思考<br />
              用修辞和逻辑搭建故事世界
            </span>
          </button>
        </div>

        <button
          className="channel-confirm-btn"
          disabled={!selected || saving}
          onClick={handleConfirm}
        >
          {saving ? '保存中...' : '✨ 确认，进入故事世界'}
        </button>

        <p className="channel-hint">首次登录只需选择一次，之后可从顶部年龄标签主动修改</p>
      </div>
    </div>
  );
}
