import { useEffect, useRef, useCallback, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useSSE } from '../hooks/useSSE';
import { useStoryState, type ChatMessage } from '../contexts/StoryContext';
import { getStory, getStoryMessages, updateStory, type StoryMessage } from '../api/endpoints';
import ChatBubble from '../components/Story/ChatBubble';
import StoryInput from '../components/Story/StoryInput';
import TypingIndicator from '../components/Story/TypingIndicator';
import Button from '../components/Shared/Button';
import Loading from '../components/Shared/Loading';
import './StoryPlayPage.css';

function extractStoredImageUrl(message: StoryMessage): string | undefined {
  if (!message.ai_raw_response) return undefined;
  try {
    const raw = JSON.parse(message.ai_raw_response) as { image_urls?: unknown };
    if (!Array.isArray(raw.image_urls)) return undefined;
    return raw.image_urls.find((url): url is string => typeof url === 'string' && url.length > 0);
  } catch {
    return undefined;
  }
}

export default function StoryPlayPage() {
  const { storyId } = useParams<{ storyId: string }>();
  const navigate = useNavigate();
  const id = Number(storyId);
  const { state, dispatch } = useStoryState();
  const { startTurn } = useSSE();
  const chatEndRef = useRef<HTMLDivElement>(null);
  const loadingRef = useRef(false);
  const storyStartedRef = useRef(false);

  useEffect(() => {
    if (!id) return;
    loadStory();
    return () => {
      dispatch({ type: 'RESET' });
      storyStartedRef.current = false;
    };
  }, [id]);

  async function loadStory() {
    try {
      const story = await getStory(id);
      const msgs = await getStoryMessages(id);
      const chatMessages: ChatMessage[] = msgs.map((m: StoryMessage) => ({
        id: String(m.id),
        role: m.role as 'ai' | 'child',
        content: m.content,
        isQuestion: false,
        imageUrl: extractStoredImageUrl(m),
      }));
      dispatch({
        type: 'RESTORE_MESSAGES',
        messages: chatMessages,
        turnNumber: story.turn_count,
        isEnding: story.status === 'completed',
      });
      setStoryTitleState(story.title || '');

      // Auto-trigger first turn: if story has 0 turns, AI kicks off the story
      if (story.turn_count === 0 && !storyStartedRef.current) {
        storyStartedRef.current = true;
        // Small delay to let the UI render first
        setTimeout(() => {
          startStoryKickoff(id);
        }, 500);
      }
    } catch {
      navigate('/characters');
    }
  }

  const startStoryKickoff = useCallback(async (storyId: number) => {
    try {
      await startTurn(storyId, '');  // Empty input = AI initiates
    } catch {
      // Errors handled in useSSE
    }
  }, [startTurn]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [state.messages, state.isStreaming]);

  async function handleSend(text: string) {
    if (!id || state.isStreaming) return;
    try {
      await startTurn(id, text);
    } catch {
      // Errors handled in useSSE
    }
  }

  const [showEndModal, setShowEndModal] = useState(false);
  const [childEnding, setChildEnding] = useState('');
  const [storyTitle, setStoryTitleState] = useState('');

  async function handleAIEnding() {
    if (!id) return;
    setShowEndModal(false);
    // Keep the story active until the director has written and saved the ending.
    await startTurn(id, '请从刚才的情节继续，给这个故事写一个完整的大结局吧！', true);
  }

  async function handleChildEnding() {
    if (!id || !childEnding.trim()) return;
    // Send child's ending as final message, then mark complete
    dispatch({ type: 'ADD_CHILD_MESSAGE', content: childEnding.trim() });
    await updateStory(id, { status: 'completed' });
    dispatch({ type: 'FINISH_TURN', turnNumber: state.turnNumber + 1, isEnding: true });
    setShowEndModal(false);
    setChildEnding('');
  }

  if (state.storyId === null && state.messages.length === 0 && loadingRef.current === false) {
    if (id) {
      loadingRef.current = true;
      return <Loading text="加载故事中..." />;
    }
  }

  const showStartHint = state.messages.length === 0 && !state.isStreaming && state.turnNumber === 0;

  return (
    <div className="story-play-page">
      {/* Top bar */}
      <div className="story-play-top">
        <Button variant="ghost" size="sm" onClick={() => navigate('/characters')}>← 返回</Button>
        <input
          className="story-title-inline"
          value={storyTitle}
          onChange={(e) => setStoryTitleState(e.target.value)}
          onBlur={async () => { if (id && storyTitle.trim()) await updateStory(id, { title: storyTitle.trim() }); }}
          placeholder="未命名故事"
          maxLength={30}
        />
      </div>

      {/* Safety notice banner */}
      {state.safetyNotice && (
        <div className={`safety-banner safety-banner-${state.safetyNotice.level}`}>
          <span className="safety-banner-icon">🛡️</span>
          <span className="safety-banner-text">{state.safetyNotice.message}</span>
          <button className="safety-banner-close" onClick={() => dispatch({ type: 'DISMISS_SAFETY_NOTICE' })}>✕</button>
        </div>
      )}

      {/* Chat area */}
      <div className="story-chat-area">
        {showStartHint && (
          <div className="story-start-hint">
            <span className="story-start-emoji">🎬</span>
            <h2>故事导演正在准备...</h2>
            <p>马上为你呈现精彩的故事开场！</p>
          </div>
        )}

        {state.messages.map((msg) => (
          <ChatBubble
            key={msg.id}
            role={msg.role}
            content={msg.content}
            isStreaming={msg.isStreaming}
            isQuestion={msg.isQuestion}
            imageUrl={msg.imageUrl}
            isEnding={msg.isEnding}
          />
        ))}

        {state.isStreaming && <TypingIndicator />}

        <div ref={chatEndRef} />
      </div>

      {/* Input area */}
      <div className="story-play-bottom">
        {state.isEnding ? (
          <div className="story-ended-card">
            <span className="story-ended-emoji">🎉</span>
            <h3>故事创作完成！</h3>
            <p>太棒了！你们一起创造了一个精彩的故事~</p>
            <div className="story-ended-actions">
              <Button variant="primary" onClick={() => id && navigate(`/talent/${id}`)}>
                🧠 查看天赋画像
              </Button>
              <Button variant="secondary" onClick={() => navigate(`/gallery`)}>
                📚 故事画廊
              </Button>
            </div>
          </div>
        ) : (
          <StoryInput
            onSubmit={handleSend}
            disabled={state.isStreaming}
            placeholder="写下你的想法吧..."
          />
        )}

        {/* End story button */}
        {state.turnNumber >= 3 && !state.isEnding && !state.isStreaming && (
          <div className="story-end-action">
            <button className="end-story-btn" onClick={() => setShowEndModal(true)}>
              🏁 给故事写一个结尾
            </button>
          </div>
        )}

        {/* Ending choice modal */}
        {showEndModal && (
          <div className="end-modal-overlay" onClick={() => setShowEndModal(false)}>
            <div className="end-modal animate-pop-in" onClick={e => e.stopPropagation()}>
              <h3>🎬 故事结局</h3>
              <div className="end-options">
                <button className="end-option-btn" onClick={handleAIEnding}>
                  <span className="end-option-icon">🤖</span>
                  <span className="end-option-title">让故事导演写结局</span>
                  <span className="end-option-desc">AI根据剧情发展，给出一个温暖的结尾</span>
                </button>
                <div className="end-option-divider"><span>或者</span></div>
                <div className="end-option-child">
                  <span className="end-option-icon">✏️</span>
                  <span className="end-option-title">我来写结局</span>
                  <textarea
                    className="end-child-input"
                    value={childEnding}
                    onChange={e => setChildEnding(e.target.value)}
                    placeholder="在这里写下你的故事结局..."
                    rows={3}
                  />
                  <button
                    className="end-child-submit"
                    disabled={!childEnding.trim()}
                    onClick={handleChildEnding}
                  >
                    ✨ 提交我的结局
                  </button>
                </div>
              </div>
              <button className="end-modal-close" onClick={() => setShowEndModal(false)}>关闭</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
