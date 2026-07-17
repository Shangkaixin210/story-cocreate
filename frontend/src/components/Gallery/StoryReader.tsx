import { useEffect, useState } from 'react';
import { getStoryMessages, type StoryMessage } from '../../api/endpoints';
import Loading from '../Shared/Loading';
import './StoryReader.css';

interface StoryReaderProps {
  storyId: number;
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
      {messages.map((msg) => (
        <div key={msg.id} className={`reader-message reader-message-${msg.role}`}>
          <div className="reader-role-icon">
            {msg.role === 'ai' ? '🎬' : '🧒'}
          </div>
          <div className="reader-content">
            <p>{msg.content}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
