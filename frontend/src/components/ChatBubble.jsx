import { useState, useRef, useEffect, useCallback } from 'react';
import { Bot, X, Send, Loader2, Trash2 } from 'lucide-react';
import { sendChatMessage } from '../api/client';

/**
 * Floating AI chat bubble.
 * - Collapsed: pulsing circle icon at bottom-right.
 * - Expanded: full chat panel with message history + input.
 */
export default function ChatBubble() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [convId, setConvId] = useState(null);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input when panel opens
  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 100);
  }, [open]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || sending) return;

    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setInput('');
    setSending(true);

    try {
      const res = await sendChatMessage(text, convId);
      setConvId(res.conversation_id);
      setMessages((prev) => [...prev, { role: 'assistant', content: res.reply }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Error: ${err.message}` },
      ]);
    } finally {
      setSending(false);
    }
  }, [input, sending, convId]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClear = () => {
    setMessages([]);
    setConvId(null);
  };

  return (
    <>
      {/* ── Chat Panel ── */}
      {open && (
        <div
          className="fixed inset-x-0 bottom-0 z-50 flex flex-col bg-zinc-950 border-t border-zinc-800 shadow-2xl"
          style={{
            height: 'min(75dvh, 600px)',
            paddingBottom: 'env(safe-area-inset-bottom)',
          }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800 shrink-0">
            <div className="flex items-center gap-2">
              <Bot size={18} className="text-sky-400" />
              <span className="text-sm font-bold text-zinc-200">AI Coach</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleClear}
                className="text-zinc-500 active:text-zinc-300 cursor-pointer p-1"
                title="New conversation"
              >
                <Trash2 size={16} />
              </button>
              <button
                onClick={() => setOpen(false)}
                className="text-zinc-500 active:text-zinc-300 cursor-pointer p-1"
              >
                <X size={18} />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
            {messages.length === 0 && (
              <div className="text-center text-zinc-600 text-xs py-12">
                Ask me anything about your training, nutrition, or progress.
              </div>
            )}
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed whitespace-pre-wrap ${
                    msg.role === 'user'
                      ? 'bg-sky-500 text-black rounded-br-md'
                      : 'bg-zinc-800 text-zinc-200 rounded-bl-md'
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}
            {sending && (
              <div className="flex justify-start">
                <div className="bg-zinc-800 rounded-2xl rounded-bl-md px-4 py-3">
                  <Loader2 size={16} className="animate-spin text-zinc-400" />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="px-3 pb-3 pt-1 shrink-0">
            <div className="flex items-end gap-2 bg-zinc-900 border border-zinc-700 rounded-xl px-3 py-2 focus-within:border-sky-500 transition-colors">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Message your AI coach…"
                rows={1}
                className="flex-1 bg-transparent text-sm text-zinc-200 placeholder-zinc-600 resize-none focus:outline-none max-h-24"
                style={{ minHeight: '1.5rem' }}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || sending}
                className="shrink-0 p-1.5 rounded-lg bg-sky-500 text-black disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed active:opacity-80 transition-opacity"
              >
                <Send size={16} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Floating Bubble ── */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed z-50 w-14 h-14 rounded-full bg-gradient-to-br from-sky-400 to-indigo-500 text-white shadow-lg shadow-sky-500/40 flex items-center justify-center cursor-pointer active:scale-90 transition-transform animate-pulse hover:animate-none"
          style={{
            bottom: 'calc(1.25rem + env(safe-area-inset-bottom))',
            right: '1.25rem',
          }}
        >
          <Bot size={26} />
        </button>
      )}
    </>
  );
}
