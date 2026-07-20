import { useEffect, useState } from 'react';
import { getStoryMessages, type StoryMessage } from '../../api/endpoints';
import Loading from '../Shared/Loading';
import './StoryReader.css';

interface StoryReaderProps {
  storyId: number;
}

function extractImageUrls(msg: StoryMessage): string[] {
  if (!msg.ai_raw_response) return [];
  try {
    const raw = JSON.parse(msg.ai_raw_response);
    return raw.image_urls || [];
  } catch {
    return [];
  }
}

export default function StoryReader({ storyId }: StoryReaderProps) {
  const [messages, setMessages] = useState<StoryMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    setLoading(true);
    getStoryMessages(storyId)
      .then(setMessages)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [storyId]);

  if (loading) return <Loading text="加载故事中..." />;
  if (error) return <p className="reader-error">😅 {error}</p>;

  return (
    <div className="story-reader">
      {messages.map((msg) => {
        const imageUrls = msg.role === 'ai' ? extractImageUrls(msg) : [];
        return (
          <div key={msg.id} className={`reader-message reader-message-${msg.role}`}>
            <div className="reader-role-icon">
              {msg.role === 'ai' ? '🎬' : '🧒'}
            </div>
            <div className="reader-content">
              <p>{msg.content}</p>
              {imageUrls.map((url, i) => (
                <div key={i} className="reader-image">
                  <img src={url} alt={`故事插图 ${i + 1}`} loading="lazy" />
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
