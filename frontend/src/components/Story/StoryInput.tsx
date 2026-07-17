import { useState, useRef, type FormEvent, type KeyboardEvent } from 'react';
import './StoryInput.css';

interface StoryInputProps {
  onSubmit: (text: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export default function StoryInput({
  onSubmit,
  disabled = false,
  placeholder = '写下你的想法吧...',
}: StoryInputProps) {
  const [text, setText] = useState('');
  const inputRef = useRef<HTMLTextAreaElement>(null);

  function handleSubmit(e?: FormEvent) {
    e?.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setText('');
    // Auto-resize reset
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  function handleInput() {
    const el = inputRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = Math.min(el.scrollHeight, 120) + 'px';
    }
  }

  return (
    <form className="story-input-wrapper" onSubmit={handleSubmit}>
      <div className="story-input-row">
        <textarea
          ref={inputRef}
          className="story-input-field"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
        />
        <button
          type="submit"
          className="story-input-send"
          disabled={disabled || !text.trim()}
          title="发送"
        >
          🚀
        </button>
      </div>
      <p className="story-input-hint">按 Enter 发送，Shift+Enter 换行</p>
    </form>
  );
}
