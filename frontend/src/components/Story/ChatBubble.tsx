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
  // Only strip lines that are purely JSON objects (prevent raw JSON leaks)
  return text
    .split('\n')
    .filter(line => !/^\{"type"\s*:\s*"(?:narrative|question|observation|done|ending)"/.test(line.trim()))
    .join('\n')
    .trim();
}

export default function ChatBubble({ role, content, isStreaming, isQuestion, imageUrl, isEnding }: ChatBubbleProps) {
  const cls = [
    'chat-bubble',
    `chat-bubble-${role}`,
    isQuestion ? 'chat-bubble-question' : '',
    isStreaming ? 'chat-bubble-streaming' : '',
    isEnding ? 'chat-bubble-ending' : '',
  ]
    .filter(Boolean)
    .join(' ');

  const displayContent = sanitizeContent(content);

  if (!displayContent && !imageUrl) return null;

  return (
    <div className={cls}>
      <div className="chat-bubble-avatar">
        {role === 'ai' ? '🎬' : '🧒'}
      </div>
      <div className="chat-bubble-content">
        {displayContent && (
          <p className="chat-bubble-text">
            {displayContent}
            {isStreaming && <span className="cursor-blink">|</span>}
            {isEnding && <span className="ending-badge">🎉 故事完结</span>}
          </p>
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
    </div>
  );
}
