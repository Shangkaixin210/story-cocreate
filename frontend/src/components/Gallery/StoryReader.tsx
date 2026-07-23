import { useEffect, useState } from 'react';
import { getStoryMessages, type StoryMessage } from '../../api/endpoints';
import Loading from '../Shared/Loading';
import PinyinText from '../Story/PinyinText';
import './StoryReader.css';

interface StoryReaderProps {
  storyId: number;
}

function extractFirstImageUrl(msg: StoryMessage): string | undefined {
  if (!msg.ai_raw_response) return undefined;
  try {
    const raw = JSON.parse(msg.ai_raw_response) as { image_urls?: unknown };
    if (!Array.isArray(raw.image_urls)) return undefined;
    return raw.image_urls.find(
      (url): url is string => typeof url === 'string' && url.trim().length > 0,
    );
  } catch {
    return undefined;
  }
}

export default function StoryReader({ storyId }: StoryReaderProps) {
  const [messages, setMessages] = useState<StoryMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showPinyin, setShowPinyin] = useState(false);
  const [fontSize, setFontSize] = useState<'s' | 'm' | 'l'>('m');

  useEffect(() => {
    setLoading(true);
    getStoryMessages(storyId)
      .then(setMessages)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [storyId]);

  if (loading) return <Loading text="加载故事中..." />;
  if (error) return <p className="reader-error">😅 {error}</p>;

  const displayedImages = new Set<string>();

  return (
    <div className={`story-reader ${showPinyin ? 'story-reader-pinyin' : ''} reader-fs-${fontSize}`}>
      <div className="reader-toolbar">
        <span className="reader-toolbar-label">字号</span>
        <div className="fontsize-toggle">
          <button className={`fs-btn ${fontSize==='s'?'fs-active':''}`} onClick={()=>setFontSize('s')}>小</button>
          <button className={`fs-btn ${fontSize==='m'?'fs-active':''}`} onClick={()=>setFontSize('m')}>中</button>
          <button className={`fs-btn ${fontSize==='l'?'fs-active':''}`} onClick={()=>setFontSize('l')}>大</button>
        </div>
        <span className="reader-toolbar-label">拼音</span>
        <button type="button" className={`reader-pinyin-toggle ${showPinyin?'active':''}`} onClick={()=>setShowPinyin(c=>!c)} aria-pressed={showPinyin}>{showPinyin?'关闭':'开启'}</button>
      </div>

      <div className="reader-message-list">
        {messages.map((msg) => {
          const candidateUrl = msg.role === 'ai' ? extractFirstImageUrl(msg) : undefined;
          const imageUrl = candidateUrl && !displayedImages.has(candidateUrl) ? candidateUrl : undefined;
          if (imageUrl) displayedImages.add(imageUrl);
          return (
            <div key={msg.id} className={`reader-message reader-message-${msg.role}`}>
              <div className="reader-role-icon">
                {msg.role === 'ai' ? '🎬' : '🧒'}
              </div>
              <div className="reader-content">
                <p>
                  <PinyinText text={msg.content} enabled={showPinyin && msg.role === 'ai'} />
                </p>
                {imageUrl && (
                  <figure className="reader-image">
                    <img src={imageUrl} alt="与这段故事对应的插图" loading="lazy" />
                  </figure>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
