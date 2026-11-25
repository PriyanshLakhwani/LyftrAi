
import { useEffect, useState } from "react";
import "./App.css";

const API_URL = import.meta.env.VITE_API_URL;

const createSessionId = () =>
  `session_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;

const createConversation = () => ({
  id: createSessionId(),
  title: "New conversation",
  messages: [],
  createdAt: Date.now(),
});

function App() {
  const [conversations, setConversations] = useState(() => {
    try {
      const saved = localStorage.getItem("lyftr_conversations");
      return saved ? JSON.parse(saved) : [createConversation()];
    } catch {
      return [createConversation()];
    }
  });

  const [activeId, setActiveId] = useState(() => {
    try {
      const saved = localStorage.getItem("lyftr_active_id");
      return saved || null;
    } catch {
      return null;
    }
  });

  const [input, setInput] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [showSettings, setShowSettings] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    localStorage.setItem("lyftr_conversations", JSON.stringify(conversations));
  }, [conversations]);

  useEffect(() => {
    if (!conversations.length) {
      const newConversation = createConversation();
      setConversations([newConversation]);
      setActiveId(newConversation.id);
      return;
    }

    const validActiveId = conversations.some((c) => c.id === activeId);

    if (!validActiveId) {
      setActiveId(conversations[0].id);
    }
  }, [conversations, activeId]);

  useEffect(() => {
    if (activeId) {
      localStorage.setItem("lyftr_active_id", activeId);
    }
  }, [activeId]);

  const activeConversation = conversations.find(
    (conversation) => conversation.id === activeId
  );

  const messages = activeConversation?.messages || [];

  const updateConversation = (conversationId, updater) => {
    setConversations((previous) =>
      previous.map((conversation) =>
        conversation.id === conversationId
          ? updater(conversation)
          : conversation
      )
    );
  };

  const createNewChat = () => {
    const conversation = createConversation();
    setConversations((previous) => [conversation, ...previous]);
    setActiveId(conversation.id);
    setInput("");
    setError("");
  };

  const deleteConversation = (conversationId) => {
    const remaining = conversations.filter((c) => c.id !== conversationId);

    if (remaining.length === 0) {
      const newConversation = createConversation();
      setConversations([newConversation]);
      setActiveId(newConversation.id);
      return;
    }

    setConversations(remaining);

    if (activeId === conversationId) {
      setActiveId(remaining[0].id);
    }
  };

  const sendMessage = async () => {
    const text = input.trim();

    if (!text || loading || !activeConversation) return;

    setError("");
    setInput("");

    const userMessage = {
      role: "user",
      content: text,
    };

    const updatedMessages = [...messages, userMessage];

    updateConversation(activeConversation.id, (conversation) => ({
      ...conversation,
      title:
        conversation.messages.length === 0
          ? text.length > 32
            ? `${text.slice(0, 32)}...`
            : text
          : conversation.title,
      messages: updatedMessages,
    }));

    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: activeConversation.id,
          message: text,
          system_prompt: systemPrompt,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Something went wrong.");
      }

      const assistantMessage = {
        role: "assistant",
        content: data.reply,
        metadata: data.metadata || {},
      };

      updateConversation(activeConversation.id, (conversation) => ({
        ...conversation,
        messages: [...conversation.messages, assistantMessage],
      }));
    } catch (err) {
      setError(err.message || "Unable to connect to the server.");

      updateConversation(activeConversation.id, (conversation) => ({
        ...conversation,
        messages: conversation.messages.filter(
          (message, index) =>
            !(message.role === "user" && index === conversation.messages.length - 1)
        ),
      }));

      setInput(text);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="app-shell">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">✦</div>
          <span>Lyftr<span className="brand-ai">AI</span></span>
        </div>

        <button className="new-chat-button" onClick={createNewChat}>
          <span>＋</span> New chat
        </button>

        <div className="sidebar-section-title">YOUR CHATS</div>

        <div className="conversation-list">
          {conversations.map((conversation) => (
            <div
              key={conversation.id}
              className={`conversation-item ${
                activeId === conversation.id ? "active" : ""
              }`}
            >
              <button
                className="conversation-select"
                onClick={() => {
                  setActiveId(conversation.id);
                  setError("");
                }}
                title={conversation.title}
              >
                <span className="conversation-icon">◷</span>
                <span className="conversation-title">{conversation.title}</span>
              </button>

              <button
                className="delete-chat-button"
                onClick={() => deleteConversation(conversation.id)}
                title="Delete conversation"
                aria-label="Delete conversation"
              >
                ×
              </button>
            </div>
          ))}
        </div>

        <div className="sidebar-bottom">
          <button
            className={`settings-button ${showSettings ? "selected" : ""}`}
            onClick={() => setShowSettings((previous) => !previous)}
          >
            <span>⚙</span>
            <span>System prompt</span>
          </button>

          <div className="sidebar-profile">
            <div className="profile-avatar">L</div>
            <div className="profile-info">
              <div className="profile-name">Lyftr AI</div>
              <div className="profile-caption">Multi-provider AI assistant</div>
            </div>
            <div className="status-dot" />
          </div>
        </div>
      </aside>

      {/* Main Chat */}
      <main className="main-panel">
        <header className="topbar">
          <div className="topbar-left">
            <div className="mobile-brand">
              <div className="brand-icon">✦</div>
              <span>Lyftr<span className="brand-ai">AI</span></span>
            </div>
            <div className="chat-heading">
              <span className="heading-title">
                {activeConversation?.title || "New conversation"}
              </span>
              <span className="connection-status">
                <span className="status-dot" />
                AI ready
              </span>
            </div>
          </div>

          <button
            className="topbar-settings"
            onClick={() => setShowSettings((previous) => !previous)}
            title="System prompt settings"
          >
            ⚙
          </button>
        </header>

        {showSettings && (
          <div className="system-prompt-panel">
            <div className="system-prompt-header">
              <div>
                <strong>System prompt</strong>
                <p>Customize how the AI assistant responds.</p>
              </div>
              <button
                className="close-settings"
                onClick={() => setShowSettings(false)}
              >
                ×
              </button>
            </div>

            <textarea
              data-testid="system-prompt-input"
              className="system-prompt-input"
              placeholder="You are a helpful AI assistant..."
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              rows={3}
            />

            <div className="system-prompt-footer">
              <span>Applied to new messages</span>
              <button
                className="reset-prompt"
                onClick={() => setSystemPrompt("")}
              >
                Reset
              </button>
            </div>
          </div>
        )}

        <div className="messages-area">
          {messages.length === 0 ? (
            <div className="welcome-screen">
              <div className="welcome-symbol">✦</div>
              <div className="welcome-eyebrow">YOUR AI WORKSPACE</div>
              <h1>
                What can I help
                <br />
                <span>you with today?</span>
              </h1>
              <p className="welcome-description">
                Ask anything, explore ideas, or get help with your next task.
              </p>

              <div className="suggestion-grid">
                {[
                  {
                    icon: "✧",
                    title: "Explain something",
                    text: "Break down complex topics simply",
                    prompt: "Explain cloud computing in simple terms.",
                  },
                  {
                    icon: "⌘",
                    title: "Write something",
                    text: "Help me draft or improve content",
                    prompt: "Help me write a professional email.",
                  },
                  {
                    icon: "⌁",
                    title: "Brainstorm ideas",
                    text: "Explore new ideas and possibilities",
                    prompt: "Help me brainstorm some creative project ideas.",
                  },
                  {
                    icon: "⌖",
                    title: "Solve a problem",
                    text: "Think through a challenge with me",
                    prompt: "Help me solve a problem step by step.",
                  },
                ].map((suggestion) => (
                  <button
                    key={suggestion.title}
                    className="suggestion-card"
                    onClick={() => setInput(suggestion.prompt)}
                  >
                    <span className="suggestion-icon">{suggestion.icon}</span>
                    <span className="suggestion-title">{suggestion.title}</span>
                    <span className="suggestion-description">{suggestion.text}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="messages-container">
              {messages.map((message, index) => (
                <div
                  key={`${activeConversation.id}-${index}`}
                  className={`message-row ${message.role}`}
                >
                  {message.role === "assistant" && (
                    <div className="assistant-avatar">✦</div>
                  )}

                  <div className="message-content-wrapper">
                    <div
                      className={`message-bubble ${
                        message.role === "assistant" ? "assistant-bubble" : "user-bubble"
                      }`}
                      data-testid={
                        message.role === "assistant" ? "assistant-message" : undefined
                      }
                    >
                      <div className="message-text">{message.content}</div>
                    </div>

                    {message.role === "assistant" && message.metadata && (
                      <div className="metadata-container">
                        <div className="metadata-header">
                          <span className="metadata-label">RESPONSE DETAILS</span>
                          <span
                            className={`source-pill ${
                              message.metadata.resolution_source === "LLM_CACHE"
                                ? "cache-source"
                                : "live-source"
                            }`}
                            data-testid="meta-source"
                          >
                            {message.metadata.resolution_source === "LLM_CACHE"
                              ? "Cached"
                              : "Live"}
                          </span>
                        </div>

                        <div className="metadata-grid">
                          <div className="metadata-item">
                            <span className="metadata-key">MODEL</span>
                            <span data-testid="meta-model">
                              {message.metadata.model || "—"}
                            </span>
                          </div>

                          <div className="metadata-item">
                            <span className="metadata-key">LATENCY</span>
                            <span data-testid="meta-latency">
                              {message.metadata.latency_ms != null
                                ? `${message.metadata.latency_ms} ms`
                                : "—"}
                            </span>
                          </div>

                          <div className="metadata-item">
                            <span className="metadata-key">INPUT TOKENS</span>
                            <span data-testid="meta-input-tokens">
                              {message.metadata.input_tokens ?? "—"}
                            </span>
                          </div>

                          <div className="metadata-item">
                            <span className="metadata-key">OUTPUT TOKENS</span>
                            <span data-testid="meta-output-tokens">
                              {message.metadata.output_tokens ?? "—"}
                            </span>
                          </div>
                        </div>
                      </div>
                    )}

                    <span className="message-time">
                      {formatTime(Date.now())}
                    </span>
                  </div>
                </div>
              ))}

              {loading && (
                <div className="message-row assistant">
                  <div className="assistant-avatar">✦</div>
                  <div className="typing-bubble">
                    <span className="typing-dot" />
                    <span className="typing-dot" />
                    <span className="typing-dot" />
                    <span className="typing-label">Thinking...</span>
                  </div>
                </div>
              )}

              <div className="messages-bottom-spacer" />
            </div>
          )}
        </div>

        {error && (
          <div className="error-banner">
            <span>⚠</span>
            {error}
            <button onClick={() => setError("")}>×</button>
          </div>
        )}

        <div className="input-area">
          <div className="input-box">
            <textarea
              data-testid="chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Message Lyftr AI..."
              rows={1}
              disabled={loading}
            />

            <div className="input-bottom">
              <div className="input-hint">
                <span>↵</span> to send · Shift + ↵ for new line
              </div>

              <button
                data-testid="send-button"
                className={`send-button ${input.trim() && !loading ? "enabled" : ""}`}
                onClick={sendMessage}
                disabled={!input.trim() || loading}
                title="Send message"
              >
                {loading ? (
                  <span className="send-loading" />
                ) : (
                  <span>↑</span>
                )}
              </button>
            </div>
          </div>

          <p className="disclaimer">
            Lyftr AI can make mistakes. Verify important information.
          </p>
        </div>
      </main>
    </div>
  );
}

export default App;
