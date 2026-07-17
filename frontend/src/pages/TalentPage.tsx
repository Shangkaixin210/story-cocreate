import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiFetch, ApiError } from '../api/client';
import { getStoryMessages } from '../api/endpoints';
import Button from '../components/Shared/Button';
import Loading from '../components/Shared/Loading';
import StoryReader from '../components/Gallery/StoryReader';
import Modal from '../components/Shared/Modal';
import './TalentPage.css';

interface TalentProfile {
  story_id: number;
  story_title: string;
  total_turns: number;
  completed: boolean;
  vocabulary_richness: number | null;
  descriptive_ability: number | null;
  story_structure: number | null;
  vocabulary_trend: string;
  descriptive_trend: string;
  structure_trend: string;
  overall_level: string;
  overall_score: number | null;
  creativity_flags: string[];
  dominant_flag: string;
  vocabulary_highlights: string[];
  descriptive_highlights: string[];
  total_words_by_child: number;
  avg_words_per_turn: number;
  strengths: string[];
  suggestions: string[];
  level_label: string;
  level_description: string;
}

const FLAG_LABELS: Record<string, string> = {
  unexpected_twist: '意外转折',
  rich_imagery: '丰富意象',
  emotional_depth: '情感深度',
  logical_consistency: '逻辑一致',
  humor: '幽默感',
};

function ScoreBar({ label, score, trend, emoji }: { label: string; score: number | null; trend: string; emoji: string }) {
  const pct = score ? (score / 5) * 100 : 0;
  return (
    <div className="talent-score-item">
      <div className="talent-score-header">
        <span className="talent-score-label">{emoji} {label}</span>
        <span className="talent-score-value">{score ?? '-'} / 5</span>
        <span className="talent-score-trend">{trend}</span>
      </div>
      <div className="talent-score-bar-track">
        <div
          className={`talent-score-bar-fill talent-score-bar-${score ? (score >= 4 ? 'high' : score >= 3 ? 'mid' : 'low') : 'low'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function TalentPage() {
  const { storyId } = useParams<{ storyId: string }>();
  const navigate = useNavigate();
  const [profile, setProfile] = useState<TalentProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showStory, setShowStory] = useState(false);

  useEffect(() => {
    if (!storyId) return;
    apiFetch<TalentProfile>(`/talents/${storyId}`)
      .then(setProfile)
      .catch((err) => setError(err instanceof ApiError ? err.message : '加载失败'))
      .finally(() => setLoading(false));
  }, [storyId]);

  if (loading) return <Loading text="分析天赋数据中..." />;
  if (error) return <div className="page talent-error">😅 {error}</div>;
  if (!profile) return <div className="page talent-error">找不到天赋数据</div>;

  return (
    <div className="page talent-page">
      <Button variant="ghost" size="sm" onClick={() => navigate('/gallery')} style={{ alignSelf: 'flex-start', marginBottom: 16 }}>
        ← 返回画廊
      </Button>

      {/* Hero */}
      <div className="talent-hero animate-fade-in">
        <span className="talent-hero-emoji">
          {profile.overall_score && profile.overall_score >= 4 ? '🌟' : profile.overall_score && profile.overall_score >= 3 ? '✨' : '🌱'}
        </span>
        <h1 className="talent-hero-level">{profile.level_label}</h1>
        <p className="talent-hero-desc">{profile.level_description}</p>
        <p className="talent-hero-story">故事《{profile.story_title}》· {profile.total_turns} 轮对话</p>
      </div>

      {/* Score cards */}
      <div className="talent-scores animate-slide-up">
        <h2>📊 语言能力维度</h2>
        <ScoreBar label="词汇丰富度" score={profile.vocabulary_richness} trend={profile.vocabulary_trend} emoji="📝" />
        <ScoreBar label="描述能力" score={profile.descriptive_ability} trend={profile.descriptive_trend} emoji="🎨" />
        <ScoreBar label="故事结构" score={profile.story_structure} trend={profile.structure_trend} emoji="📖" />
      </div>

      {/* Overall stats */}
      <div className="talent-stats animate-slide-up">
        <div className="talent-stat-card">
          <span className="talent-stat-num">{profile.total_words_by_child}</span>
          <span className="talent-stat-label">总输出字数</span>
        </div>
        <div className="talent-stat-card">
          <span className="talent-stat-num">{profile.avg_words_per_turn}</span>
          <span className="talent-stat-label">每轮平均字数</span>
        </div>
        <div className="talent-stat-card">
          <span className="talent-stat-num">{profile.total_turns}</span>
          <span className="talent-stat-label">参与轮次</span>
        </div>
      </div>

      {/* Creativity flags */}
      {profile.creativity_flags.length > 0 && (
        <div className="talent-flags animate-slide-up">
          <h2>💡 创造力亮点</h2>
          <div className="talent-flags-list">
            {profile.creativity_flags.map((flag) => (
              <span key={flag} className="talent-flag-tag">
                {FLAG_LABELS[flag] || flag}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Highlights */}
      {(profile.vocabulary_highlights.length > 0 || profile.descriptive_highlights.length > 0) && (
        <div className="talent-highlights animate-slide-up">
          <h2>✏️ 精彩瞬间</h2>
          {profile.descriptive_highlights.map((h, i) => (
            <div key={i} className="talent-highlight-item">"{h}"</div>
          ))}
          {profile.vocabulary_highlights.map((h, i) => (
            <div key={`v-${i}`} className="talent-highlight-item vocab-highlight">🌟 亮点词汇：{h}</div>
          ))}
        </div>
      )}

      {/* Strengths & suggestions */}
      <div className="talent-feedback animate-slide-up">
        <div className="talent-feedback-card strengths">
          <h2>👍 优势</h2>
          <ul>
            {profile.strengths.map((s, i) => <li key={i}>{s}</li>)}
          </ul>
        </div>
        <div className="talent-feedback-card suggestions">
          <h2>💬 成长建议</h2>
          <ul>
            {profile.suggestions.map((s, i) => <li key={i}>{s}</li>)}
          </ul>
        </div>
      </div>

      <div className="talent-actions">
        <Button variant="secondary" onClick={() => setShowStory(true)}>
          📖 查看完整故事
        </Button>
        <Button variant="primary" onClick={() => navigate('/characters')}>
          🎭 再创作一个故事
        </Button>
      </div>

      <Modal open={showStory} onClose={() => setShowStory(false)} title={`📖 ${profile.story_title}`}>
        <StoryReader storyId={profile.story_id} />
      </Modal>
    </div>
  );
}
