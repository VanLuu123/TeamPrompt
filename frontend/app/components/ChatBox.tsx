"use client";
import { useState, useRef, useEffect } from "react";

interface Message {
  role: "user" | "bot";
  content: string;
  timestamp: Date;
  sources?: Array<{
    content: string;
    filename: string;
    score: number;
  }>;
}

interface QueryResult {
  content: string;
  filename: string;
  score: number;
}

interface ChatBoxProps {
  hasDocuments?: boolean;
}

export default function ChatBox({ hasDocuments = false }: ChatBoxProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const currentQuery = input;
    setInput("");
    setLoading(true);

    try {
      if (!hasDocuments) {
        setMessages((prev) => [
          ...prev,
          {
            role: "bot",
            content:
              "Please upload some documents first so I can help answer questions about them.",
            timestamp: new Date(),
          },
        ]);
        return;
      }

      // Query documents
      const queryResponse = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: currentQuery, top_k: 5 }),
      });

      if (!queryResponse.ok) {
        throw new Error(`Query failed: ${queryResponse.status}`);
      }

      const queryData = await queryResponse.json();

      if (!queryData.results || queryData.results.length === 0) {
        setMessages((prev) => [
          ...prev,
          {
            role: "bot",
            content:
              "I couldn't find any relevant information in your documents to answer that question.",
            timestamp: new Date(),
          },
        ]);
        return;
      }

      // Prepare context from top results
      const context = queryData.results
        .slice(0, 3)
        .map(
          (result: QueryResult, index: number) =>
            `Source ${index + 1} (${result.filename}):\n${result.content}`
        )
        .join("\n\n---\n\n");

      // Get AI response
      const chatResponse = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: currentQuery, context }),
      });

      if (!chatResponse.ok) {
        throw new Error(`Chat failed: ${chatResponse.status}`);
      }

      const chatData = await chatResponse.json();

      setMessages((prev) => [
        ...prev,
        {
          role: "bot",
          content: chatData.response,
          timestamp: new Date(),
          sources: queryData.results.slice(0, 3),
        },
      ]);
    } catch (error) {
      console.error("Chat error:", error);
      let errorMessage = "Sorry, something went wrong. Please try again.";

      if (error instanceof Error) {
        const msg = error.message.toLowerCase();
        if (msg.includes("failed to fetch") || msg.includes("network")) {
          errorMessage = "Can't connect to the server. Make sure it's running;";
        } else if (msg.includes("query failed")) {
          errorMessage = "Failed to search documents. Please try again.";
        } else if (msg.includes("chat failed")) {
          errorMessage =
            "AI service unavailable. Check your OpenRouter API key.";
        }
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "bot",
          content: errorMessage,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-[600px] border rounded-lg bg-white shadow-sm">
      {/* Header */}
      <div className="border-b p-4">
        <h3 className="font-semibold text-gray-800">Chat with Documents</h3>
        <p className="text-sm text-gray-500">
          {hasDocuments
            ? "Ask questions about your uploaded documents"
            : "Upload documents to get started"}
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-400">
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center">
                <svg
                  className="w-8 h-8"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                  />
                </svg>
              </div>
              <p>
                {hasDocuments
                  ? "Start a conversation!"
                  : "Upload documents first"}
              </p>
            </div>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${
                msg.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[80%] space-y-2 ${
                  msg.role === "user" ? "items-end" : "items-start"
                }`}
              >
                <div
                  className={`px-4 py-2 rounded-lg ${
                    msg.role === "user"
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-800"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>

                {msg.sources && msg.sources.length > 0 && (
                  <div className="space-y-1">
                    <p className="text-xs text-gray-500">Sources:</p>
                    {msg.sources.map((source, sidx) => (
                      <div
                        key={sidx}
                        className="bg-gray-50 border rounded p-2 text-xs"
                      >
                        <div className="flex justify-between items-center mb-1">
                          <span className="font-medium">{source.filename}</span>
                          <span className="text-gray-500">
                            {Math.round(source.score * 100)}%
                          </span>
                        </div>
                        <p className="text-gray-600 line-clamp-2">
                          {source.content.substring(0, 120)}...
                        </p>
                      </div>
                    ))}
                  </div>
                )}

                <p className="text-xs text-gray-400">
                  {msg.timestamp.toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </p>
              </div>
            </div>
          ))
        )}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg px-4 py-2 flex items-center space-x-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
              <span className="text-gray-600">Thinking...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t p-4">
        <div className="flex space-x-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              hasDocuments
                ? "Ask about your documents..."
                : "Upload documents first..."
            }
            className="flex-1 border rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 text-black"
            rows={2}
            disabled={loading || !hasDocuments}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim() || !hasDocuments}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              loading || !input.trim() || !hasDocuments
                ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                : "bg-blue-600 text-white hover:bg-blue-700"
            }`}
          >
            {loading ? (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            ) : (
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                />
              </svg>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
