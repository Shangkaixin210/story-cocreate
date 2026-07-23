import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { apiFetch, ApiError } from '../api/client';
import StoryReader from '../components/Gallery/StoryReader';
import Button from '../components/Shared/Button';
import Loading from '../components/Shared/Loading';
import Modal from '../components/Shared/Modal';
import './TalentPage.css';

interface Dimension {
  key: string;
  label: string;
  score: number;
  max_score: number;
}

interface ReportSection {
  score?: number;
  base_score?: number;
  progress_bonus?: number;
  final_score?: number;
  level: string;
  level_label: string;
  dimensions: Dimension[];
}

interface TalentProfile {
  story_id: number;
  story_title: string;
  total_turns: number;
  age_group: string;
  completed: boolean;
  language: ReportSection;
  empathy: ReportSection;
  imagination: ReportSection;
  growth_memory: {
    has_history: boolean;
    compared_story_count: number;
    baseline_index: number | null;
    current_index: number;
    change: number;
    progress_bonus: number;
    summary: string;
  };
  highlights: string[];
  total_words: number;
  avg_words_per_turn: number;
  strengths: string[];
  suggestions: string[];
}

function ScoreSection({
  title,
  subtitle,
  section,
  language = false,
}: {
  title: string;
  subtitle: string;
  section: ReportSection;
  language?: boolean;
}) {
  const total = language ? section.final_score ?? 0 : section.score ?? 0;
  return (
    <section className={`talent-section talent-section-${section.level}`}>
      <div className="talent-section-heading">
        <div>
          <p className="talent-kicker">{subtitle}</p>
          <h2>{title}</h2>
          <span className="talent-level">{section.level_label}</span>
        </div>
        <div className="talent-total">
          <strong>{total}</strong>
          <span>{language ? '/ 100 + 进步分' : '/ 100'}</span>
        </div>
      </div>

      {language && (
        <div className="language-score-breakdown">
          <span>基础评分 <b>{section.base_score}</b>/100</span>
          <span>成长加分 <b>+{section.progress_bonus}</b>/10</span>
        </div>
      )}

      <div className="talent-dimensions">
        {section.dimensions.map((dimension) => (
          <div className="talent-dimension" key={dimension.key}>
            <div className="talent-dimension-label">
              <span>{dimension.label}</span>
              <b>{dimension.score}/{dimension.max_score}</b>
            </div>
            <div className="talent-track">
              <span style={{ width: `${Math.min(100, dimension.score / dimension.max_score * 100)}%` }} />
            </div>
          </div>
        ))}
      </div>
    </section>
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
      .catch((err) => setError(err instanceof ApiError ? err.message : '报告加载失败'))
      .finally(() => setLoading(false));
  }, [storyId]);

  if (loading) return <Loading text="正在生成标准化天赋报告..." />;
  if (error) return <div className="page talent-error">{error}</div>;
  if (!profile) return <div className="page talent-error">暂时没有可用的天赋数据</div>;

  return (
    <div className="page talent-page">
      <Button variant="ghost" size="sm" onClick={() => navigate('/gallery')}>
        返回故事画廊
      </Button>

      <header className="talent-hero">
        <p className="talent-kicker">AI 伯乐 · 标准化成长报告</p>
        <h1>{profile.story_title}</h1>
        <div className="talent-meta">
          <span>{profile.age_group} 岁通道</span>
          <span>{profile.total_turns} 次有效表达</span>
          <span>{profile.total_words} 字</span>
        </div>
      </header>

      <ScoreSection
        title="语言智能"
        subtitle=""
        section={profile.language}
        language
      />

      <div className="talent-secondary-grid">
        <ScoreSection
          title="共情与人际智能"
          subtitle=""
          section={profile.empathy}
        />
        <ScoreSection
          title="想象与空间智能"
          subtitle=""
          section={profile.imagination}
        />
      </div>

      {profile.highlights.length > 0 && (
        <section className="talent-card">
          <h2>精彩创作瞬间</h2>
          <div className="talent-quotes">
            {profile.highlights.map((quote, index) => <blockquote key={index}>“{quote}”</blockquote>)}
          </div>
        </section>
      )}

      <div className="talent-feedback">
        <section className="talent-card">
          <h2>能力亮点</h2>
          <ul>{profile.strengths.map((item, index) => <li key={index}>{item}</li>)}</ul>
        </section>
        <section className="talent-card">
          <h2>下一步建议</h2>
          <ul>{profile.suggestions.map((item, index) => <li key={index}>{item}</li>)}</ul>
        </section>
      </div>

      <div className="talent-actions">
        <Button variant="secondary" onClick={() => setShowStory(true)}>阅读完整故事</Button>
        <Button variant="primary" onClick={() => navigate('/characters')}>继续创作</Button>
      </div>

      <Modal open={showStory} onClose={() => setShowStory(false)} title={profile.story_title}>
        <StoryReader storyId={profile.story_id} />
      </Modal>
    </div>
  );
}
