import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Loader2, AlertCircle } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { ScrollArea } from "./ui/scroll-area";
import { useLanguage } from "@/contexts/LanguageContext";
import { useBackendHealth } from "@/hooks/useBackendHealth";
import { getBackendUrl } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

const ChatPanel = () => {
  const { t } = useLanguage();
  const { isHealthy } = useBackendHealth();
  
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "assistant",
      content: t("readyToProcess") as string,
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [hasError, setHasError] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Update initial message when language changes
  useEffect(() => {
    setMessages([
      {
        id: "1",
        role: "assistant",
        content: t("readyToProcess") as string,
        timestamp: new Date(),
      },
    ]);
  }, [t]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Clear error when backend comes back online
  useEffect(() => {
    if (isHealthy && hasError) {
      console.log("Backend is back online, clearing chat error...");
      setHasError(false);
    }
  }, [isHealthy, hasError]);

  const clearChat = () => {
    setMessages([
      {
        id: "1",
        role: "assistant",
        content: t("readyToProcess") as string,
        timestamp: new Date(),
      },
    ]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    // Check backend health before submitting
    if (!isHealthy) {
      console.error("Cannot submit message: Backend is not available");
      setHasError(true);
      return;
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const currentInput = input.trim();
    setInput("");
    setIsLoading(true);
    setHasError(false);

    try {
      const response = await fetch(getBackendUrl("/api/v1/chat"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: currentInput }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      // Use the backend's markdown-formatted message directly
      const responseMessage = data.message;

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: responseMessage,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setIsLoading(false);
    } catch (error) {
      console.error("Error processing message:", error);
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Sorry, I encountered an error connecting to the server. Please try again.",
        timestamp: new Date(),
      };
      
      setMessages((prev) => [...prev, errorMessage]);
      setHasError(true);
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full glass-card rounded-lg overflow-hidden relative">
      {/* Header with Clear Button */}
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-border/50">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-foreground/60" />
          <span className="font-mono text-xs tracking-wider uppercase text-muted-foreground">
            {t("ingestionAgent") as string}
          </span>
        </div>
        <button
          onClick={clearChat}
          className="flex items-center gap-1 px-2 py-1 rounded-md bg-secondary hover:bg-secondary/80 transition-colors text-muted-foreground hover:text-foreground text-xs"
          title="Clear chat history"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M3 6h18" />
            <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
            <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
          </svg>
          Clear
        </button>
      </div>

      {/* Error Overlay */}
      {hasError && (
        <div className="absolute inset-0 flex items-center justify-center bg-background/80 backdrop-blur-sm rounded-lg z-50">
          <div className="flex flex-col items-center gap-3 text-center px-6">
            <div className="w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center">
              <AlertCircle className="w-6 h-6 text-destructive" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground mb-1">Connection error</h3>
              <p className="text-xs text-muted-foreground">Unable to process request</p>
            </div>
          </div>
        </div>
      )}

      {/* Messages Area */}
      <ScrollArea className="flex-1 p-3" ref={scrollRef}>
        <div className="space-y-3">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex gap-2 ${
                message.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              {message.role === "assistant" && (
                <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-1">
                  <Bot className="w-3.5 h-3.5 text-primary" />
                </div>
              )}
              <div
                className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                  message.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-foreground"
                }`}
              >
                {message.role === "assistant" ? (
                  <div className="prose prose-sm dark:prose-invert max-w-none [&_code]:bg-primary/10 [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_code]:text-xs [&_code]:font-mono [&_code]:border [&_code]:border-primary/20 [&_code]:relative [&_code]:group [&_pre]:bg-primary/10 [&_pre]:p-2 [&_pre]:rounded [&_pre]:border [&_pre]:border-primary/20 [&_h2]:text-base [&_h2]:font-semibold [&_h2]:mt-2 [&_h2]:mb-1 [&_h3]:text-sm [&_h3]:font-semibold [&_p]:my-1 [&_p]:leading-relaxed [&_strong]:font-semibold [&_em]:italic [&_em]:text-muted-foreground">
                    <ReactMarkdown
                      components={{
                        code: ({ children, ...props }: any) => {
                          const text = String(children).replace(/\n$/, '');
                          const handleCopy = () => {
                            navigator.clipboard.writeText(text);
                            // Simple toast notification
                            const toast = document.createElement('div');
                            toast.className = 'fixed bottom-4 right-4 bg-primary text-primary-foreground px-4 py-2 rounded-lg shadow-lg z-50 animate-in fade-in slide-in-from-bottom-2';
                            toast.textContent = 'Copied to clipboard!';
                            document.body.appendChild(toast);
                            setTimeout(() => {
                              toast.classList.add('animate-out', 'fade-out', 'slide-out-to-bottom-2');
                              setTimeout(() => document.body.removeChild(toast), 200);
                            }, 2000);
                          };
                          
                          return (
                            <code className="inline-flex items-center gap-1 group" {...props}>
                              <span>{text}</span>
                              <button
                                onClick={handleCopy}
                                className="opacity-0 group-hover:opacity-100 transition-opacity ml-1 p-0.5 hover:bg-primary/20 rounded"
                                title="Copy to clipboard"
                              >
                                <svg
                                  xmlns="http://www.w3.org/2000/svg"
                                  width="12"
                                  height="12"
                                  viewBox="0 0 24 24"
                                  fill="none"
                                  stroke="currentColor"
                                  strokeWidth="2"
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                >
                                  <rect width="14" height="14" x="8" y="8" rx="2" ry="2" />
                                  <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
                                </svg>
                              </button>
                            </code>
                          );
                        },
                      }}
                    >
                      {message.content}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <p>{message.content}</p>
                )}
              </div>
              {message.role === "user" && (
                <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center flex-shrink-0 mt-1">
                  <User className="w-3.5 h-3.5 text-primary-foreground" />
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="flex gap-2">
              <div className="w-5 h-5 rounded bg-secondary flex items-center justify-center">
                <Bot className="w-3 h-3 animate-pulse text-muted-foreground" />
              </div>
              <div className="bg-secondary rounded-md px-3 py-2">
                <Loader2 className="w-3 h-3 animate-spin text-muted-foreground" />
              </div>
            </div>
          )}
          
          {/* Scroll anchor */}
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-2 border-t border-border/50">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={t("addCompany") as string}
            className="h-8 text-xs bg-secondary/50 border-border/50"
            disabled={isLoading}
          />
          <Button type="submit" size="icon" className="h-8 w-8 flex-shrink-0" disabled={!input.trim() || isLoading}>
            <Send className="w-3.5 h-3.5" />
          </Button>
        </div>
      </form>
    </div>
  );
};

export default ChatPanel;
