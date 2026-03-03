import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";
import type { Message } from "../../types/message";

interface MessageListProps {
  messages: Message[];
}

const markdownComponents: Components = {
  code({ className, children, ...props }) {
    const isBlock = className?.startsWith("language-");
    if (isBlock) {
      return (
        <code
          className={className}
          style={{
            display: "block",
            fontFamily: "'DM Mono', 'Fira Code', 'Cascadia Code', monospace",
            fontSize: "0.8125rem",
            color: "var(--text-primary)",
          }}
          {...props}
        >
          {children}
        </code>
      );
    }
    return (
      <code
        style={{
          fontFamily: "'DM Mono', 'Fira Code', 'Cascadia Code', monospace",
          fontSize: "0.8125rem",
          background: "var(--bg-elevated)",
          border: "1px solid var(--border-default)",
          borderRadius: "4px",
          padding: "0.1em 0.35em",
          color: "var(--accent)",
        }}
        {...props}
      >
        {children}
      </code>
    );
  },
  pre({ children, ...props }) {
    return (
      <pre
        style={{
          background: "var(--bg-input)",
          border: "1px solid var(--border-default)",
          borderLeft: "3px solid var(--border-accent)",
          borderRadius: "6px",
          padding: "0.75rem 1rem",
          overflowX: "auto",
          margin: "0.5rem 0",
        }}
        {...props}
      >
        {children}
      </pre>
    );
  },
  a({ href, children, ...props }) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        style={{ color: "var(--accent)", textDecoration: "underline" }}
        {...props}
      >
        {children}
      </a>
    );
  },
  strong({ children, ...props }) {
    return (
      <strong style={{ color: "var(--text-primary)", fontWeight: 600 }} {...props}>
        {children}
      </strong>
    );
  },
  em({ children, ...props }) {
    return (
      <em style={{ color: "var(--text-secondary)", fontStyle: "italic" }} {...props}>
        {children}
      </em>
    );
  },
  h1({ children, ...props }) {
    return (
      <h1
        style={{
          fontSize: "1.05rem",
          fontWeight: 600,
          color: "var(--accent)",
          margin: "0.75rem 0 0.35rem",
          lineHeight: 1.3,
        }}
        {...props}
      >
        {children}
      </h1>
    );
  },
  h2({ children, ...props }) {
    return (
      <h2
        style={{
          fontSize: "0.975rem",
          fontWeight: 600,
          color: "var(--text-primary)",
          margin: "0.65rem 0 0.3rem",
          lineHeight: 1.3,
        }}
        {...props}
      >
        {children}
      </h2>
    );
  },
  h3({ children, ...props }) {
    return (
      <h3
        style={{
          fontSize: "0.9rem",
          fontWeight: 600,
          color: "var(--text-secondary)",
          margin: "0.5rem 0 0.25rem",
          lineHeight: 1.3,
        }}
        {...props}
      >
        {children}
      </h3>
    );
  },
  ul({ children, ...props }) {
    return (
      <ul
        style={{ margin: "0.4rem 0", paddingLeft: "1.4rem", lineHeight: 1.65 }}
        {...props}
      >
        {children}
      </ul>
    );
  },
  ol({ children, ...props }) {
    return (
      <ol
        style={{ margin: "0.4rem 0", paddingLeft: "1.4rem", lineHeight: 1.65 }}
        {...props}
      >
        {children}
      </ol>
    );
  },
  li({ children, ...props }) {
    return (
      <li style={{ marginBottom: "0.15rem" }} {...props}>
        {children}
      </li>
    );
  },
  blockquote({ children, ...props }) {
    return (
      <blockquote
        style={{
          borderLeft: "3px solid var(--accent)",
          paddingLeft: "0.75rem",
          margin: "0.5rem 0",
          color: "var(--text-secondary)",
          fontStyle: "italic",
        }}
        {...props}
      >
        {children}
      </blockquote>
    );
  },
  p({ children, ...props }) {
    return (
      <p style={{ margin: "0.3rem 0" }} {...props}>
        {children}
      </p>
    );
  },
  hr(props) {
    return (
      <hr
        style={{ border: "none", borderTop: "1px solid var(--border-default)", margin: "0.75rem 0" }}
        {...props}
      />
    );
  },
};

export function MessageList({ messages }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div
      style={{
        flex: 1,
        overflowY: "auto",
        padding: "1.25rem 1.25rem 0.5rem",
        display: "flex",
        flexDirection: "column",
        gap: "0.875rem",
      }}
    >
      {messages.length === 0 && (
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: "0.75rem",
            color: "var(--text-muted)",
            paddingTop: "4rem",
          }}
        >
          <img
            src="/istari-icon.png"
            alt=""
            style={{ width: "52px", height: "52px", borderRadius: "14px", opacity: 0.3 }}
          />
          <p style={{ fontSize: "0.875rem" }}>Ask me anything</p>
        </div>
      )}

      {messages.map((msg) => (
        <div
          key={msg.id}
          style={{
            display: "flex",
            flexDirection: msg.role === "user" ? "row-reverse" : "row",
            alignItems: "flex-end",
            gap: "0.5rem",
          }}
        >
          {/* Istari avatar sigil */}
          {msg.role === "assistant" && (
            <div
              style={{
                width: "24px",
                height: "24px",
                borderRadius: "6px",
                background: "var(--bg-elevated)",
                border: "1px solid var(--border-accent)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
                fontSize: "0.625rem",
                color: "var(--accent)",
              }}
            >
              ✦
            </div>
          )}

          {/* Message bubble */}
          <div
            style={{
              maxWidth: "78%",
              padding: "0.625rem 0.875rem",
              borderRadius: msg.role === "user" ? "14px 14px 4px 14px" : "4px 14px 14px 14px",
              background: msg.role === "user" ? "var(--bg-elevated)" : "var(--bg-surface)",
              border: `1px solid ${msg.role === "user" ? "var(--border-default)" : "var(--border-subtle)"}`,
              borderLeft: msg.role === "assistant" ? "2px solid var(--border-accent)" : undefined,
              fontSize: "0.875rem",
              lineHeight: 1.6,
              color: "var(--text-primary)",
              whiteSpace: msg.role === "user" ? "pre-wrap" : undefined,
              wordBreak: "break-word",
            }}
          >
            {msg.role === "assistant" ? (
              <div className="markdown-body">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={markdownComponents}
                >
                  {msg.content}
                </ReactMarkdown>
              </div>
            ) : (
              msg.content
            )}
          </div>
        </div>
      ))}

      <div ref={bottomRef} />
    </div>
  );
}
