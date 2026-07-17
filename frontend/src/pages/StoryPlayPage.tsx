import { useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useSSE } from '../hooks/useSSE';
import { useStoryState, type ChatMessage } from '../contexts/StoryContext';
import { getStory, getStoryMessages, updateStory, type StoryMessage } from '../api/endpoints';
import ChatBubble from '../components/Story/ChatBubble';
import StoryInput from '../components/Story/StoryInput';
import StoryProgress from '../components/Story/StoryProgress';
import TypingIndicator from '../components/Story/TypingIndicator';
import Button from '../components/Shared/Button';
import Loading from '../components/Shared/Loading';
import './StoryPlayPage.css';

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
      }));
      dispatch({ type: 'RESTORE_MESSAGES', messages: chatMessages, turnNumber: story.turn_count });

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

  async function handleEndStory() {
    if (!id) return;
    await updateStory(id, { status: 'completed' });
    dispatch({ type: 'FINISH_TURN', turnNumber: state.turnNumber, isEnding: true });
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
      {/* Progress bar */}
      <div className="story-play-top">
        <Button variant="ghost" size="sm" onClick={() => navigate('/characters')}>
          ← 返回
        </Button>
        <StoryProgress turn={state.turnNumber} maxTurns={10} isEnding={state.isEnding} />
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
              <Button variant="primary" onClick={() => navigate(`/gallery`)}>
                📚 查看故事画廊
              </Button>
              <Button variant="secondary" onClick={() => navigate('/characters')}>
                🎭 再创作一个
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
            <button className="end-story-btn" onClick={handleEndStory}>
              🏁 给故事写一个结尾
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
