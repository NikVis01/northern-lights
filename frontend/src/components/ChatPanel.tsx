import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Loader2, AlertCircle } from "lucide-react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { ScrollArea } from "./ui/scroll-area";
import { useLanguage } from "@/contexts/LanguageContext";
import { useBackendHealth } from "@/hooks/useBackendHealth";

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

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Clear error when backend comes back online
  useEffect(() => {
    if (isHealthy && hasError) {
      console.log("Backend is back online, clearing chat error...");
      setHasError(false);
    }
  }, [isHealthy, hasError]);

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

    // TODO: Replace with actual API call
    // For now, simulating potential errors
    setTimeout(() => {
      try {
        const responses = [
          t("queuing", { input: currentInput }),
          t("foundEntity") as string,
          t("ingestionComplete") as string,
        ];

        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: responses[Math.floor(Math.random() * responses.length)],
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMessage]);
        setIsLoading(false);
      } catch (error) {
        console.error("Error processing message:", error);
        setHasError(true);
        setIsLoading(false);
      }
    }, 1200);
  };

  return (
    <div className="flex flex-col h-full glass-card rounded-lg overflow-hidden relative">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2.5 border-b border-border/50">
        <div className="w-2 h-2 rounded-full bg-foreground/60" />
        <span className="font-mono text-xs tracking-wider uppercase text-muted-foreground">
          {t("ingestionAgent") as string}
        </span>
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

      {/* Messages */}
      <ScrollArea className="flex-1 p-3" ref={scrollRef}>
        <div className="space-y-3">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex gap-2 ${message.role === "user" ? "flex-row-reverse" : ""}`}
            >
              <div className={`w-5 h-5 rounded flex items-center justify-center flex-shrink-0 mt-0.5 ${message.role === "assistant" ? "bg-secondary" : "bg-foreground/10"}`}>
                {message.role === "assistant" ? (
                  <Bot className="w-3 h-3 text-muted-foreground" />
                ) : (
                  <User className="w-3 h-3 text-foreground/70" />
                )}
              </div>
              <div className={`max-w-[85%] rounded-md px-3 py-2 text-xs ${message.role === "assistant" ? "bg-secondary text-foreground" : "bg-foreground text-background"}`}>
                <p className="leading-relaxed">{message.content}</p>
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex gap-2">
              <div className="w-5 h-5 rounded bg-secondary flex items-center justify-center">
                <Bot className="w-3 h-3 text-muted-foreground" />
              </div>
              <div className="bg-secondary rounded-md px-3 py-2">
                <Loader2 className="w-3 h-3 animate-spin text-muted-foreground" />
              </div>
            </div>
          )}
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
