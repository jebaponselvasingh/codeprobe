import { useEffect, useRef } from 'react';
import type { ChatMessage as ChatMessageType } from '../../stores/chatStore';
import { ChatMessage } from './ChatMessage';

interface Props {
  messages: ChatMessageType[];
}

export function ChatMessageList({ messages }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages]);

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto px-4 py-3"
    >
      {messages.map(msg => (
        <ChatMessage key={msg.id} message={msg} />
      ))}
    </div>
  );
}
