import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';
import { ChatMessageList } from './ChatMessageList';
import { ChatInput } from './ChatInput';

export function ChatPanel() {
  const { isOpen, messages, suggestedQuestions, isStreaming, closeChat, sendMessage } =
    useChatStore();

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          key="chat-panel"
          initial={{ x: '100%' }}
          animate={{ x: 0 }}
          exit={{ x: '100%' }}
          transition={{ type: 'spring', damping: 28, stiffness: 280 }}
          className="fixed inset-y-0 right-0 w-full md:w-[40%] z-50 flex flex-col shadow-2xl"
          style={{
            background: 'var(--bg-card)',
            borderLeft: '1px solid var(--color-border)',
          }}
        >
          {/* Header */}
          <div
            className="flex items-center justify-between px-4 py-3 flex-shrink-0"
            style={{ borderBottom: '1px solid var(--color-border)' }}
          >
            <h2 className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
              AI Code Review Assistant
            </h2>
            <button
              onClick={closeChat}
              className="flex items-center justify-center w-7 h-7 rounded-md hover:opacity-70 transition-opacity"
              style={{ color: 'var(--text-secondary)' }}
              aria-label="Close chat"
            >
              <X size={16} />
            </button>
          </div>

          {/* Suggested questions — shown only when no messages yet */}
          {messages.length === 0 && suggestedQuestions.length > 0 && (
            <div
              className="px-4 py-3 flex flex-col gap-2 flex-shrink-0"
              style={{ borderBottom: '1px solid var(--color-border)' }}
            >
              <p className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                SUGGESTED QUESTIONS
              </p>
              <div className="flex flex-col gap-1.5">
                {suggestedQuestions.map(q => (
                  <button
                    key={q}
                    onClick={() => sendMessage(q)}
                    className="text-left text-xs px-3 py-2 rounded-lg hover:opacity-80 transition-opacity"
                    style={{
                      background: 'var(--bg-secondary)',
                      border: '1px solid var(--color-border)',
                      color: 'var(--text-primary)',
                    }}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Message list */}
          <ChatMessageList messages={messages} />

          {/* Input */}
          <div className="flex-shrink-0">
            <ChatInput onSend={sendMessage} disabled={isStreaming} />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
