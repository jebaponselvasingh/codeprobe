import { useState, useRef, type KeyboardEvent } from 'react';
import { SendHorizonal } from 'lucide-react';

interface Props {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled = false }: Props) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    const scrollHeight = el.scrollHeight;
    // Clamp between 1 row (~24px) and 4 rows (~96px)
    el.style.height = `${Math.min(scrollHeight, 96)}px`;
  };

  return (
    <div
      className="flex items-end gap-2 p-3"
      style={{ borderTop: '1px solid var(--color-border)' }}
    >
      <textarea
        ref={textareaRef}
        value={value}
        onChange={e => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        disabled={disabled}
        placeholder="Ask a question… (Enter to send, Shift+Enter for newline)"
        rows={1}
        className="flex-1 resize-none rounded-lg px-3 py-2 text-sm outline-none transition-colors"
        style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--color-border)',
          color: 'var(--text-primary)',
          minHeight: '36px',
          maxHeight: '96px',
          overflowY: 'auto',
          opacity: disabled ? 0.6 : 1,
        }}
      />
      <button
        onClick={handleSend}
        disabled={disabled || !value.trim()}
        className="flex-shrink-0 flex items-center justify-center w-9 h-9 rounded-lg transition-colors"
        style={{
          background: disabled || !value.trim() ? 'var(--bg-secondary)' : '#2563eb',
          color: disabled || !value.trim() ? 'var(--text-muted)' : '#ffffff',
          border: '1px solid var(--color-border)',
          cursor: disabled || !value.trim() ? 'not-allowed' : 'pointer',
        }}
      >
        <SendHorizonal size={16} />
      </button>
    </div>
  );
}
