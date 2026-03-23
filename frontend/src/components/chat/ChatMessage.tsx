import ReactMarkdown from 'react-markdown';
import type { ChatMessage as ChatMessageType } from '../../stores/chatStore';

interface Props {
  message: ChatMessageType;
}

export function ChatMessage({ message }: Props) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      <div
        className="max-w-[85%] rounded-2xl px-4 py-2.5 text-sm"
        style={
          isUser
            ? { background: '#2563eb', color: '#ffffff' }
            : {
                background: 'var(--bg-secondary)',
                border: '1px solid var(--color-border)',
                color: 'var(--text-primary)',
              }
        }
      >
        {isUser ? (
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        ) : (
          <div className="prose prose-sm max-w-none" style={{ color: 'inherit' }}>
            {message.content ? (
              <ReactMarkdown>{message.content}</ReactMarkdown>
            ) : null}
            {message.isStreaming && (
              <span className="inline-flex gap-1 ml-2 align-middle">
                {[0, 1, 2].map(i => (
                  <span
                    key={i}
                    className="w-1.5 h-1.5 rounded-full bg-current animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }}
                  />
                ))}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
