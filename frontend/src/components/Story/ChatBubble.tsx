import { useState, useCallback } from 'react';
import { useTTS } from '../../hooks/useTTS';
import WordLookup from './WordLookup';
import './ChatBubble.css';

interface ChatBubbleProps {
  role: 'ai' | 'child';
  content: string;
  isStreaming?: boolean;
  isQuestion?: boolean;
  imageUrl?: string;
  isEnding?: boolean;
}

function sanitizeContent(text: string): string {
  return text
    .split('\n')
    .filter(line => !/^\{"type"\s*:\s*"(?:narrative|question|observation|done|ending)"/.test(line.trim()))
    .join('\n')
    .trim();
}

interface LookupState {
  text: string;
  x: number;
  y: number;
}

export default function ChatBubble({ role, content, isStreaming, isQuestion, imageUrl, isEnding }: ChatBubbleProps) {
  const { speak, stop, speaking } = useTTS();
  const [lookup, setLookup] = useState<LookupState | null>(null);

  const cls = [
    'chat-bubble',
    `chat-bubble-${role}`,
    isQuestion ? 'chat-bubble-question' : '',
    isStreaming ? 'chat-bubble-streaming' : '',
    isEnding ? 'chat-bubble-ending' : '',
  ].filter(Boolean).join(' ');

  const displayContent = sanitizeContent(content);

  const handleTextSelect = useCallback(() => {
    const selection = window.getSelection();
    const selectedText = selection?.toString().trim();
    if (selectedText && selectedText.length >= 1 && selectedText.length <= 20) {
      const range = selection?.getRangeAt(0);
      if (range) {
        const rect = range.getBoundingClientRect();
        setLookup({
          text: selectedText,
          x: rect.left + rect.width / 2,
          y: rect.top,
        });
      }
    }
  }, []);

  const handleTTS = () => {
    if (speaking) {
      stop();
    } else {
      speak(content);
    }
  };

  if (!content && !imageUrl) return null;

  return (
    <div className={cls}>
      <div className="chat-bubble-avatar">
        {role === 'ai' ? '🎬' : '🧒'}
      </div>
      <div className="chat-bubble-content">
        {displayContent && (
          <p className="chat-bubble-text" onMouseUp={handleTextSelect}>
            {displayContent}
            {isStreaming && <span className="cursor-blink">|</span>}
            {isEnding && <span className="ending-badge">🎉 故事完结</span>}
          </p>
        )}

        {/* TTS button for AI messages */}
        {role === 'ai' && content && !isStreaming && (
          <button
            className={`tts-btn ${speaking ? 'tts-btn-active' : ''}`}
            onClick={handleTTS}
            title={speaking ? '停止朗读' : '朗读这段故事'}
          >
            {speaking ? '⏹ 停止' : '🔊 朗读'}
          </button>
        )}

        {imageUrl && (
          <div className="chat-bubble-image">
            <img
              src={imageUrl}
              alt="故事插图"
              loading="lazy"
              style={{ minHeight: 100, background: '#f0f0f0' }}
            />
            <span className="chat-bubble-image-label">🖼️ AI 生成的插图</span>
          </div>
        )}
      </div>

      {/* Word lookup popup */}
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
