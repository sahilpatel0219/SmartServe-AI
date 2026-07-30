import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';

import { assistant as assistantApi } from '../api/endpoints';
import { useToast } from '../context/ToastContext';
import { Loading, PageHeader, UploadPrompt } from '../components/ui';

export default function Assistant() {
  const { toast } = useToast();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const scrollRef = useRef(null);

  const statusQuery = useQuery({ queryKey: ['assistant', 'status'], queryFn: assistantApi.status });

  const chatMutation = useMutation({
    mutationFn: assistantApi.chat,
    onSuccess: (result, question) => {
      setMessages((m) => [
        ...m,
        { role: 'assistant', text: result.reply, chips: result.chips, intent: result.intent, question },
      ]);
    },
    onError: (err) => {
      setMessages((m) => [...m, { role: 'assistant', text: err.message, isError: true }]);
    },
  });

  const feedbackMutation = useMutation({
    mutationFn: assistantApi.feedback,
    onSuccess: () => toast.success('Thanks — that helps improve the answers.'),
  });

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, chatMutation.isPending]);

  const ask = (question) => {
    const text = question.trim();
    if (!text || chatMutation.isPending) return;
    setMessages((m) => [...m, { role: 'user', text }]);
    setInput('');
    chatMutation.mutate(text);
  };

  if (statusQuery.isLoading) return <Loading rows={3} />;

  const status = statusQuery.data;

  return (
    <>
      <PageHeader
        title="AI Assistant"
        subtitle={
          status?.llm_enabled
            ? 'Ask about your business in plain language. Every number comes from your own data.'
            : 'Running in deterministic mode — answers come straight from your data, no LLM key configured.'
        }
      />

      {!status?.has_data ? (
        <UploadPrompt
          title="Nothing to Ask About Yet"
          desc="The assistant answers from your uploaded data only — it never invents figures. Upload your sales history to get started."
        />
      ) : (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            height: 'calc(100vh - var(--topbar-height) - 220px)',
            minHeight: 460,
            maxWidth: 720,
            margin: '0 auto',
            overflow: 'hidden',
            // Same surface as the sidebar/topbar. In dark theme this is a
            // distinct near-black different from the page background; in
            // light theme --bg-elev-1 and --bg-elev-2 are both white, so this
            // is a no-op there — the request to match dark-theme only holds.
            background: 'var(--bg-elev-1)',
            border: '1px solid var(--glass-border)',
            borderRadius: 'var(--r-lg)',
            boxShadow: 'var(--shadow-2)',
          }}
        >
          {/* Header strip — gives the panel a clear top edge against the page */}
          <div
            className="flex items-center gap-2"
            style={{
              padding: 'var(--space-3) var(--space-6)',
              borderBottom: '1px solid var(--hairline)',
              background: 'var(--brand-tint)',
            }}
          >
            <i className="bi bi-stars" style={{ color: 'var(--brand)' }} />
            <span className="fw-semi text-sm">SmartServe Assistant</span>
            <span
              className="badge badge-success"
              style={{ marginLeft: 'auto' }}
            >
              <i className="bi bi-circle-fill" style={{ fontSize: 6 }} /> Online
            </span>
          </div>

          {/* Message stream */}
          <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: 'var(--space-6)' }}>
            {!messages.length && (
              <div className="text-center" style={{ padding: 'var(--space-8) 0 var(--space-4)' }}>
                <div
                  style={{
                    width: 64, height: 64, borderRadius: '50%', margin: '0 auto var(--space-4)',
                    background: 'linear-gradient(135deg, var(--brand), var(--brand-hover))',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '1.6rem', color: '#fff', boxShadow: 'var(--shadow-glow)',
                  }}
                >
                  <i className="bi bi-stars" />
                </div>
                <h3 className="empty-title" style={{ marginBottom: 4 }}>Ask me about your business</h3>
                <p className="text-sm text-muted mb-0">Answers are computed from your uploaded data — nothing is guessed.</p>
              </div>
            )}

            {messages.map((msg, i) => (
              <Message
                key={i}
                msg={msg}
                onFeedback={(rating) =>
                  feedbackMutation.mutate({ rating, question: msg.question || '', answer: msg.text })
                }
                onChipClick={ask}
              />
            ))}

            {chatMutation.isPending && (
              <div className="flex gap-3 items-center text-sm text-muted" style={{ padding: 'var(--space-3) 0' }}>
                <Avatar role="assistant" />
                <span className="spinner" /> Working through your data…
              </div>
            )}
          </div>

          {/* Persistent suggestion bar — stays visible across the whole session, not just before the first question */}
          {status.starter_chips?.length > 0 && (
            <div
              className="flex gap-2 flex-wrap"
              style={{ padding: 'var(--space-3) var(--space-6)', borderTop: '1px solid var(--hairline)' }}
            >
              {status.starter_chips.map((chip) => (
                <button
                  key={chip}
                  type="button"
                  className="btn btn-sm btn-outline btn-pill"
                  onClick={() => ask(chip)}
                  disabled={chatMutation.isPending}
                >
                  <i className="bi bi-lightning-charge" /> {chip}
                </button>
              ))}
            </div>
          )}

          {/* Composer */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              ask(input);
            }}
            className="flex gap-2"
            style={{ padding: 'var(--space-4) var(--space-6)', borderTop: '1px solid var(--hairline)' }}
          >
            <input
              className="form-control"
              placeholder="e.g. What was my revenue last week?"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={chatMutation.isPending}
              autoFocus
            />
            <button type="submit" className="btn btn-primary" disabled={chatMutation.isPending || !input.trim()}>
              <i className="bi bi-send" />
            </button>
          </form>
        </div>
      )}
    </>
  );
}

function Avatar({ role }) {
  return (
    <div
      style={{
        width: 34, height: 34, borderRadius: '50%', flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.95rem',
        background: role === 'user' ? 'var(--brand)' : 'var(--glass-bg)',
        color: role === 'user' ? '#fff' : 'var(--brand)',
        border: role === 'user' ? 'none' : '1px solid var(--glass-border)',
      }}
    >
      <i className={`bi ${role === 'user' ? 'bi-person-fill' : 'bi-stars'}`} />
    </div>
  );
}

function Message({ msg, onFeedback, onChipClick }) {
  const isUser = msg.role === 'user';

  return (
    <div style={{ padding: 'var(--space-2) 0' }}>
      <div className={`flex gap-3 ${isUser ? 'justify-end' : ''}`} style={{ alignItems: 'flex-end' }}>
        {!isUser && <Avatar role="assistant" />}
        <div
          style={{
            maxWidth: '74%',
            // Panel is now bg-elev-1 (matches the sidebar); bubbles use the
            // lighter bg-elev-2 so replies still stand out against it.
            background: isUser ? 'var(--brand)' : 'var(--bg-elev-2)',
            color: isUser ? '#fff' : 'var(--text-primary)',
            border: isUser ? 'none' : '1px solid var(--glass-border)',
            borderRadius: isUser ? 'var(--r-md) var(--r-md) 4px var(--r-md)' : 'var(--r-md) var(--r-md) var(--r-md) 4px',
            padding: 'var(--space-3) var(--space-4)',
            fontSize: 'var(--text-sm)',
            whiteSpace: 'pre-wrap',
            lineHeight: 1.6,
            boxShadow: isUser ? 'var(--inset-hi-brand)' : 'none',
          }}
        >
          {msg.text}
        </div>
        {isUser && <Avatar role="user" />}
      </div>

      {!isUser && !msg.isError && (
        <div className="flex gap-2 items-center mt-2" style={{ paddingLeft: 44 }}>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => onFeedback('up')} aria-label="Helpful">
            <i className="bi bi-hand-thumbs-up" />
          </button>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => onFeedback('down')} aria-label="Not helpful">
            <i className="bi bi-hand-thumbs-down" />
          </button>
          {msg.intent && <span className="text-xs text-faint">{msg.intent}</span>}
        </div>
      )}

      {!isUser && msg.chips?.length > 0 && (
        <div className="flex gap-2 flex-wrap mt-2" style={{ paddingLeft: 44 }}>
          {msg.chips.map((chip) => (
            <button key={chip} type="button" className="btn btn-sm btn-outline btn-pill" onClick={() => onChipClick(chip)}>
              {chip}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
