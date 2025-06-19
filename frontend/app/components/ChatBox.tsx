"use client";
import { useState, useRef, useEffect } from "react";
import { Textarea } from "./ui/textarea";
import { Button } from "./ui/button";
import { Send, Loader2, FileText, Clock } from "lucide-react";

interface Message {
  role: "user" | "bot";
  content: string;
  timestamp: Date;
  sources?: Array<{
    score: number;
    content: string;
    metadata: {
      file_name: string;
      file_type: string;
      chunk_index: number;
      page_number?: number;
    };
  }>;
}

interface ChatBoxProps {
  hasDocuments?: boolean;
}

export default function ChatBox({ hasDocuments = false }: ChatBoxProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const queryDocuments = async (query: string) => {
    try {
      const response = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: query,
          top_k: 5,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = `HTTP ${response.status}`;
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.detail || errorMessage;
        } catch {
          // If not JSON, use the text as is
          errorMessage = errorText || errorMessage;
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error("Query error:", error);
      throw error;
    }
  };

  const generateAIResponse = async (query: string, context: string) => {
    try {
      const response = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: query,
          context: context,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = `HTTP ${response.status}`;
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.detail || errorMessage;
        } catch {
          // If not JSON, use the text as is
          errorMessage = errorText || errorMessage;
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      return data.response;
    } catch (error) {
      console.error("AI response error:", error);
      throw error;
    }
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    const currentQuery = input;
    setInput("");
    setLoading(true);

    try {
      if (!hasDocuments) {
        // No documents uploaded, provide a helpful message
        setMessages([
          ...newMessages,
          {
            role: "bot",
            content:
              "Please upload some documents first so I can help answer questions about them.",
            timestamp: new Date(),
          },
        ]);
        return;
      }

      // First, query the documents to get relevant context
      const queryResult = await queryDocuments(currentQuery);

      if (queryResult.results.length === 0) {
        setMessages([
          ...newMessages,
          {
            role: "bot",
            content:
              "I couldn't find any relevant information in the uploaded documents to answer your question. Please try rephrasing your question or make sure your documents contain the information you're looking for.",
            timestamp: new Date(),
            sources: [],
          },
        ]);
        return;
      }

      // Prepare context from the top results
      const topSources = queryResult.results.slice(0, 3);
      const context = topSources
        .map((source: any, index: number) => {
          return `Document ${index + 1} (${source.metadata.file_name}${
            source.metadata.page_number
              ? `, Page ${source.metadata.page_number}`
              : ""
          }):\n${source.content}`;
        })
        .join("\n\n---\n\n");

      // Generate AI response using the context
      const aiResponse = await generateAIResponse(currentQuery, context);

      const botMessage: Message = {
        role: "bot",
        content: aiResponse,
        timestamp: new Date(),
        sources: queryResult.results,
      };

      setMessages([...newMessages, botMessage]);
    } catch (error) {
      console.error("Error:", error);
      let errorMessage =
        "Sorry, I encountered an error while processing your request. Please try again.";

      if (error instanceof Error) {
        const errorMsg = error.message.toLowerCase();

        if (
          errorMsg.includes("failed to fetch") ||
          errorMsg.includes("network")
        ) {
          errorMessage =
            "Unable to connect to the backend service. Please make sure the server is running on http://localhost:8000 and try again.";
        } else if (errorMsg.includes("openrouter api key")) {
          errorMessage =
            "The AI service is not properly configured. Please check that the OpenRouter API key is set in the environment variables.";
        } else if (errorMsg.includes("openrouter api error")) {
          errorMessage =
            "The AI service encountered an error. This might be due to API limits or configuration issues. Please try again later.";
        } else if (errorMsg.includes("timeout")) {
          errorMessage =
            "The AI service request timed out. Please try again with a shorter question.";
        } else if (errorMsg.includes("http 500")) {
          errorMessage =
            "The backend service encountered an internal error. Please check the server logs and try again.";
        } else if (errorMsg.includes("http 400")) {
          errorMessage =
            "Invalid request format. Please try rephrasing your question.";
        } else if (error.message && error.message !== `HTTP ${error.message}`) {
          // If we have a detailed error message from the backend, use it
          errorMessage = `Error: ${error.message}`;
        }
      }

      setMessages([
        ...newMessages,
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

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const formatScore = (score: number) => {
    return (score * 100).toFixed(1);
  };

  return (
    <div className="rounded-xl border border-gray-200 shadow-sm p-6 bg-white space-y-6">
      <div className="h-[400px] overflow-y-auto space-y-4 pr-2 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-gray-400 italic text-center">
            <div>
              {hasDocuments ? (
                <>
                  <FileText className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                  <p>Documents are ready! Ask me anything about them.</p>
                </>
              ) : (
                <>
                  <FileText className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                  <p>Upload documents to start chatting about them.</p>
                </>
              )}
            </div>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className="flex flex-col space-y-2">
              <div
                className={`max-w-[75%] px-4 py-2 rounded-lg text-sm whitespace-pre-wrap ${
                  msg.role === "user"
                    ? "ml-auto bg-blue-600 text-white rounded-br-none"
                    : "bg-gray-100 text-gray-800 rounded-bl-none"
                }`}
              >
                {msg.content}
              </div>

              {msg.sources && msg.sources.length > 0 && (
                <div className="max-w-[75%] space-y-2">
                  <div className="text-xs text-gray-500 font-medium">
                    Sources:
                  </div>
                  {msg.sources.slice(0, 3).map((source, sourceIdx) => (
                    <div
                      key={sourceIdx}
                      className="bg-gray-50 border border-gray-200 rounded-md p-3 text-xs"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <FileText className="h-3 w-3 text-gray-500" />
                          <span className="font-medium text-gray-700">
                            {source.metadata.file_name}
                          </span>
                        </div>
                        <span className="text-gray-500">
                          {formatScore(source.score)}% match
                        </span>
                      </div>
                      <div className="text-gray-600 line-clamp-2">
                        {source.content.substring(0, 100)}...
                      </div>
                      {source.metadata.page_number && (
                        <div className="text-gray-500 mt-1">
                          Page {source.metadata.page_number}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              <span
                className={`text-xs text-gray-400 mt-1 flex items-center gap-1 ${
                  msg.role === "user" ? "ml-auto" : "mr-auto"
                }`}
              >
                <Clock className="h-3 w-3" />
                {formatTime(msg.timestamp)}
              </span>
            </div>
          ))
        )}

        {loading && (
          <div className="flex items-center gap-2 text-gray-500 bg-gray-100 max-w-[75%] px-4 py-2 rounded-lg text-sm rounded-bl-none">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>Thinking...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="flex items-end gap-3">
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            hasDocuments
              ? "Ask something about your documents..."
              : "Upload documents first to start chatting..."
          }
          className="flex-grow resize-none min-h-[80px]"
          disabled={loading}
        />
        <Button
          onClick={handleSend}
          disabled={loading || !input.trim() || !hasDocuments}
          className="min-w-[80px] h-[42px] flex items-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Sending</span>
            </>
          ) : (
            <>
              <Send className="h-4 w-4" />
              <span>Send</span>
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
