import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiFetch, ApiError } from '../api/client';
import Button from '../components/Shared/Button';
import Loading from '../components/Shared/Loading';
import StoryReader from '../components/Gallery/StoryReader';
import Modal from '../components/Shared/Modal';
import './TalentPage.css';

interface TalentProfile {
  story_id: number; story_title: string; total_turns: number; age_group: string; completed: boolean;
  avg_vocabulary_semantic: number | null; avg_sentence_fluency: number | null;
  avg_narrative_completeness: number | null; avg_character_empathy: number | null;
  avg_creative_initiative: number | null; overall_score: number | null;
  vocab_trend: string; fluency_trend: string; narrative_trend: string; empathy_trend: string; initiative_trend: string;
  overall_level: string; level_label: string; level_description: string; talent_tags: string[];
  semantic_highlights: string[]; empathy_highlights: string[]; initiative_highlights: string[];
  total_words: number; avg_words_per_turn: number; strengths: string[]; suggestions: string[];
}

const DIMENSIONS = [
  { key: 'avg_vocabulary_semantic', label: '词汇语义', emoji: '📝', desc: '修饰词、情绪词、修辞敏感度' },
  { key: 'avg_sentence_fluency', label: '表达流畅', emoji: '💬', desc: '语句连贯性与逻辑顺序' },
  { key: 'avg_narrative_completeness', label: '叙事完整', emoji: '📖', desc: '起因-冲突-解决-结局结构' },
  { key: 'avg_character_empathy', label: '角色共情', emoji: '🎭', desc: '角色台词、心理、情绪独白' },
  { key: 'avg_creative_initiative', label: '创作主动', emoji: '🚀', desc: '自发新剧情与细节拓展' },
] as const;

function Bar({ label, emoji, score, trend, desc }: { label: string; emoji: string; score: number | null; trend: string; desc: string }) {
  const pct = score ? (score / 5) * 100 : 0;
  return (
    <div className="talent-bar">
      <div className="talent-bar-header">
        <span className="talent-bar-label">{emoji} {label}</span>
        <span className="talent-bar-score">{score ?? '-'}<small>/5</small></span>
        <span className="talent-bar-trend">{trend}</span>
      </div>
      <div className="talent-bar-track">
        <div className={`talent-bar-fill talent-fill-${score ? (score >= 4 ? 'high' : score >= 3 ? 'mid' : 'low') : 'low'}`} style={{ width: `${pct}%` }} />
      </div>
      <div className="talent-bar-desc">{desc}</div>
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

  if (loading) return <Loading text="正在分析语言天赋数据..." />;
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
          {(profile.overall_score ?? 0) >= 4 ? '🌟' : (profile.overall_score ?? 0) >= 3 ? '✨' : '🌱'}
        </span>
        <h1 className="talent-hero-level">{profile.level_label}</h1>
        <p className="talent-hero-desc">{profile.level_description}</p>
        <div className="talent-hero-meta">
          <span>《{profile.story_title}》</span>
          <span>·</span>
          <span>{profile.total_turns}轮对话</span>
          <span>·</span>
          <span>{profile.age_group}岁组</span>
        </div>
      </div>

      {/* Radar overview */}
      <div className="talent-radar animate-slide-up">
        <h2>🧠 语言智能五维画像</h2>
        <div className="talent-radar-grid">
          {DIMENSIONS.map((d) => {
            const score = (profile as any)[d.key] as number | null;
            return (
              <div key={d.key} className="talent-radar-item">
                <div className="talent-radar-ring">
                  <svg viewBox="0 0 80 80">
                    <circle cx="40" cy="40" r="34" fill="none" stroke="#eee" strokeWidth="6" />
                    <circle cx="40" cy="40" r="34" fill="none"
                      stroke={score && score >= 4 ? '#6BCB77' : score && score >= 3 ? '#FFD93D' : '#FF8C42'}
                      strokeWidth="6" strokeLinecap="round"
                      strokeDasharray={`${(score || 0) / 5 * 214} 214`}
                      transform="rotate(-90 40 40)" />
                  </svg>
                  <span className="talent-radar-num">{score ?? '?'}</span>
                </div>
                <span className="talent-radar-label">{d.emoji} {d.label}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Detail bars */}
      <div className="talent-scores animate-slide-up">
        <h2>📊 详细评估</h2>
        {DIMENSIONS.map((d) => {
          const score = (profile as any)[d.key] as number | null;
          const trendKey = d.key.replace('avg_', '') + '_trend';
          const trendMap: Record<string, string> = {
            avg_vocabulary_semantic: profile.vocab_trend,
            avg_sentence_fluency: profile.fluency_trend,
            avg_narrative_completeness: profile.narrative_trend,
            avg_character_empathy: profile.empathy_trend,
            avg_creative_initiative: profile.initiative_trend,
          };
          return <Bar key={d.key} label={d.label} emoji={d.emoji} score={score} trend={trendMap[d.key] || ''} desc={d.desc} />;
        })}
      </div>

      {/* Stats */}
      <div className="talent-stats animate-slide-up">
        <div className="talent-stat-card"><span className="talent-stat-num">{profile.total_words}</span><span className="talent-stat-label">总输出字数</span></div>
        <div className="talent-stat-card"><span className="talent-stat-num">{profile.avg_words_per_turn}</span><span className="talent-stat-label">每轮平均</span></div>
        <div className="talent-stat-card"><span className="talent-stat-num">{profile.total_turns}</span><span className="talent-stat-label">参与轮次</span></div>
      </div>

      {/* Tags */}
      {profile.talent_tags.length > 0 && (
        <div className="talent-tags animate-slide-up">
          <h2>🏷️ 天赋标签</h2>
          <div className="talent-tags-list">
            {profile.talent_tags.map((t) => <span key={t} className="talent-tag">{t}</span>)}
          </div>
        </div>
      )}

      {/* Highlights */}
      {(profile.semantic_highlights.length > 0 || profile.empathy_highlights.length > 0 || profile.initiative_highlights.length > 0) && (
        <div className="talent-highlights animate-slide-up">
          <h2>✏️ 精彩瞬间</h2>
          {profile.semantic_highlights.map((h, i) => <div key={`s-${i}`} className="talent-hl-item">📝 {h}</div>)}
          {profile.empathy_highlights.map((h, i) => <div key={`e-${i}`} className="talent-hl-item">🎭 {h}</div>)}
          {profile.initiative_highlights.map((h, i) => <div key={`i-${i}`} className="talent-hl-item">🚀 {h}</div>)}
        </div>
      )}

      {/* Feedback */}
      <div className="talent-feedback animate-slide-up">
        <div className="talent-fb-card strengths">
          <h2>👍 语言优势</h2>
          <ul>{profile.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
        <div className="talent-fb-card suggestions">
          <h2>💡 成长建议</h2>
          <ul>{profile.suggestions.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
      </div>

      <div className="talent-actions">
        <Button variant="secondary" onClick={() => setShowStory(true)}>📖 查看完整故事</Button>
        <Button variant="primary" onClick={() => navigate('/characters')}>🎭 再创作一个</Button>
      </div>

      <Modal open={showStory} onClose={() => setShowStory(false)} title={`📖 ${profile.story_title}`}>
        <StoryReader storyId={profile.story_id} />
      </Modal>
    </div>
  );
}
