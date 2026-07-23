import { useCallback, useState } from 'react';
import { useTTS } from '../../hooks/useTTS';
import PinyinText from './PinyinText';
import WordLookup from './WordLookup';
import './ChatBubble.css';

interface ChatBubbleProps {
  role: 'ai' | 'child' | 'fairy';
  content: string;
  isStreaming?: boolean;
  isQuestion?: boolean;
  imageUrl?: string;
  isEnding?: boolean;
  showPinyin?: boolean;
  fontSize?: 's' | 'm' | 'l';
}

function sanitizeContent(text: string): string {
  return text
    .split('\n')
    .filter((line) => !/^\{"type"\s*:\s*"(?:narrative|question|observation|done|ending)"/.test(line.trim()))
    .join('\n')
    .trim();
}

interface LookupState {
  text: string;
  x: number;
  y: number;
}

function FairyStar() {
  return (
    <svg className="story-fairy-star" viewBox="0 0 64 64" aria-label="故事精灵">
      <path d="M32 5l7.5 15.2 16.8 2.4-12.1 11.8 2.9 16.7L32 43.2 16.9 51l2.9-16.7L7.7 22.6l16.8-2.4L32 5z" />
      <circle cx="25" cy="29" r="2.2" />
      <circle cx="39" cy="29" r="2.2" />
      <path className="story-fairy-smile" d="M25 35c4 4 10 4 14 0" />
    </svg>
  );
}

export default function ChatBubble({
  role,
  content,
  isStreaming,
  isQuestion,
  imageUrl,
  isEnding,
  showPinyin,
  fontSize,
}: ChatBubbleProps) {
  const { speak, stop, speaking } = useTTS();
  const [lookup, setLookup] = useState<LookupState | null>(null);
  const cls = [
    'chat-bubble',
    `chat-bubble-${role}`,
    isQuestion ? 'chat-bubble-question' : '',
    isStreaming ? 'chat-bubble-streaming' : '',
    isEnding ? 'chat-bubble-ending' : '',
    fontSize ? `chat-fs-${fontSize}` : '',
  ].filter(Boolean).join(' ');
  const displayContent = sanitizeContent(content);

  const handleTextSelect = useCallback(() => {
    const selection = window.getSelection();
    const selectedText = selection?.toString().trim();
    if (!selectedText || selectedText.length > 20) return;
    const range = selection?.getRangeAt(0);
    if (!range) return;
    const rect = range.getBoundingClientRect();
    setLookup({ text: selectedText, x: rect.left + rect.width / 2, y: rect.top });
  }, []);

  const handleTTS = () => speaking ? stop() : speak(content);
  if (!content && !imageUrl) return null;

  return (
    <div className={cls}>
      <div className="chat-bubble-avatar">
        {role === 'fairy' ? <FairyStar /> : role === 'ai' ? '🎬' : '🧒'}
      </div>
      <div className="chat-bubble-content">
        {role === 'fairy' && <span className="story-fairy-name">故事精灵</span>}
        {displayContent && (
          <p className="chat-bubble-text" onMouseUp={handleTextSelect}>
            <PinyinText text={displayContent} enabled={(role === 'ai' || role === 'fairy') && Boolean(showPinyin)} />
            {isStreaming && <span className="cursor-blink">|</span>}
            {isEnding && <span className="ending-badge">故事完结</span>}
          </p>
        )}

        {role === 'ai' && content && !isStreaming && (
          <button
            className={`tts-btn ${speaking ? 'tts-btn-active' : ''}`}
            onClick={handleTTS}
            title={speaking ? '停止朗读' : '朗读这段故事'}
          >
            {speaking ? '停止' : '朗读'}
          </button>
        )}

        {imageUrl && (
          <div className="chat-bubble-image">
            <img src={imageUrl} alt="故事插图" loading="lazy" style={{ minHeight: 100, background: '#f0f0f0' }} />
            <span className="chat-bubble-image-label">AI 生成的插图</span>
          </div>
        )}
      </div>

      {lookup && (
        <WordLookup
          selectedText={lookup.text}
          position={{ x: lookup.x, y: lookup.y }}
          onClose={() => setLookup(null)}
        />
      )}
    </div>
  );
}
