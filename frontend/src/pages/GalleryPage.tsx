import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listStories, deleteStory, updateStory, type Story } from '../api/endpoints';
import StoryCard from '../components/Gallery/StoryCard';
import StoryReader from '../components/Gallery/StoryReader';
import Modal from '../components/Shared/Modal';
import Button from '../components/Shared/Button';
import Loading from '../components/Shared/Loading';
import './GalleryPage.css';

export default function GalleryPage() {
  const [stories, setStories] = useState<Story[]>([]);
  const [loading, setLoading] = useState(true);
  const [readingStory, setReadingStory] = useState<Story | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadStories();
  }, []);

  async function loadStories() {
    try {
      const data = await listStories();
      setStories(data);
    } catch {
      // silently handle
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(story: Story, e: React.MouseEvent) {
    e.stopPropagation();
    if (!confirm('确定要删除这个故事吗？')) return;
    await deleteStory(story.id);
    setStories((prev) => prev.filter((s) => s.id !== story.id));
    if (readingStory?.id === story.id) setReadingStory(null);
  }

  async function handleRename(story: Story) {
    const newTitle = prompt('给你的故事取个名字吧：', story.title || story.theme || '');
    if (newTitle && newTitle.trim()) {
      await updateStory(story.id, { title: newTitle.trim() });
      loadStories();
    }
  }

  function handleContinueStory(story: Story) {
    navigate(`/play/${story.id}`);
  }

  if (loading) return <Loading text="加载故事画廊..." />;

  const activeStories = stories.filter((s) => s.status === 'active');
  const completedStories = stories.filter((s) => s.status === 'completed');

  return (
    <div className="gallery-page page">
      <div className="gallery-header">
        <h1>📚 我的故事画廊</h1>
        <Button variant="primary" onClick={() => navigate('/characters')}>
          ✨ 创作新故事
        </Button>
      </div>

      {stories.length === 0 ? (
        <div className="gallery-empty">
          <span className="gallery-empty-emoji">📖</span>
          <h2>还没有故事</h2>
          <p>去创作你的第一个故事吧！</p>
          <Button variant="primary" size="lg" onClick={() => navigate('/characters')}>
            🚀 开始创作
          </Button>
        </div>
      ) : (
        <>
          {activeStories.length > 0 && (
            <div className="gallery-section">
              <h2 className="gallery-section-title">✍️ 进行中的故事</h2>
              <div className="gallery-grid">
                {activeStories.map((story) => (
                  <div key={story.id} className="gallery-story-wrapper">
                    <StoryCard story={story} onClick={handleContinueStory} />
                    <div className="gallery-story-actions">
                      <button
                        className="gallery-action-btn continue"
                        onClick={() => handleContinueStory(story)}
                      >
                        ▶ 继续创作
                      </button>
                      <button
                        className="gallery-action-btn delete"
                        onClick={(e) => handleDelete(story, e)}
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {completedStories.length > 0 && (
            <div className="gallery-section">
              <h2 className="gallery-section-title">📖 完成的故事</h2>
              <div className="gallery-grid">
                {completedStories.map((story) => (
                  <div key={story.id} className="gallery-story-wrapper">
                    <StoryCard story={story} onClick={() => setReadingStory(story)} />
                    <div className="gallery-story-actions">
                      <button className="gallery-action-btn read" onClick={() => setReadingStory(story)}>📖 阅读</button>
                      <button className="gallery-action-btn rename" onClick={() => handleRename(story)}>✏️ 改名</button>
                      <button className="gallery-action-btn talent" onClick={() => navigate(`/talent/${story.id}`)}>🧠 天赋画像</button>
                      <button
                        className="gallery-action-btn delete"
                        onClick={(e) => handleDelete(story, e)}
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Story reader modal */}
      <Modal
        open={!!readingStory}
        onClose={() => setReadingStory(null)}
        title={readingStory?.title || readingStory?.theme || '故事'}
      >
        {readingStory && <StoryReader storyId={readingStory.id} />}
      </Modal>
    </div>
  );
}
