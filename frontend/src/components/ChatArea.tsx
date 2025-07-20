
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ChatMessage } from "./ChatMessage";
import { JobCard } from "./JobCard";
import { 
  Send, 
  Paperclip, 
  Mic,
  Image as ImageIcon,
  Sparkles,
  Loader2
} from "lucide-react";

interface Message {
  id: number;
  content: string;
  isUser: boolean;
  timestamp: Date;
}

interface ChatAreaProps {
  messages: Message[];
  isLoading: boolean;
  onSendMessage: (message: string) => void;
}

export const ChatArea = ({ messages, isLoading, onSendMessage }: ChatAreaProps) => {
  const [message, setMessage] = useState("");

  const handleSendMessage = () => {
    if (!message.trim() || isLoading) return;
    
    onSendMessage(message);
    setMessage("");
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-background">
      {/* Chat Messages Area */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {messages.length === 1 ? (
          /* Empty State - Gemini Style */
          <div className="h-full flex flex-col items-center justify-center max-w-2xl mx-auto">
            <div className="mb-8 text-center">
              <div className="w-16 h-16 bg-gradient-primary rounded-full flex items-center justify-center mb-4 mx-auto">
                <Sparkles className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-2xl font-medium text-foreground mb-2">
                Hello, how can I help you today?
              </h2>
              <p className="text-muted-foreground">
                Ask me about jobs, news, or anything else you'd like to know.
              </p>
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto space-y-6">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
            
            {/* Loading indicator */}
            {isLoading && (
              <div className="flex items-start space-x-4">
                <div className="w-8 h-8 bg-gradient-primary rounded-full flex items-center justify-center flex-shrink-0">
                  <Sparkles className="w-4 h-4 text-white" />
                </div>
                <div className="bg-card border border-border rounded-lg p-4 max-w-2xl">
                  <div className="flex items-center space-x-2 text-muted-foreground">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Thinking...</span>
                  </div>
                </div>
              </div>
            )}
            
            {/* Sample Job Results - Only show if conversation is longer and contains job-related content */}
            {messages.length > 2 && messages.some(msg => 
              msg.content.toLowerCase().includes('job') || 
              msg.content.toLowerCase().includes('✅ job scraping completed')
            ) && (
              <div className="space-y-4">
                <h3 className="text-lg font-medium text-foreground">Job Opportunities</h3>
                <div className="grid gap-4">
                  <JobCard 
                    title="Senior Frontend Developer"
                    company="TechCorp"
                    location="San Francisco, CA"
                    salary="$120,000 - $160,000"
                    description="We're looking for an experienced frontend developer to join our growing team..."
                    tags={["React", "TypeScript", "Remote"]}
                  />
                  <JobCard 
                    title="Product Manager"
                    company="StartupX"
                    location="New York, NY"
                    salary="$100,000 - $140,000"
                    description="Join us as we build the next generation of productivity tools..."
                    tags={["Product", "Strategy", "SaaS"]}
                  />
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Chat Input - Gemini Style */}
      <div className="border-t border-border bg-card px-6 py-4">
        <div className="max-w-3xl mx-auto">
          <div className="relative flex items-center bg-background border border-border rounded-full shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center pl-4 space-x-2">
              <Button variant="ghost" size="sm" className="h-8 w-8 p-0 hover:bg-warm-100">
                <Paperclip className="w-4 h-4" />
              </Button>
              <Button variant="ghost" size="sm" className="h-8 w-8 p-0 hover:bg-warm-100">
                <ImageIcon className="w-4 h-4" />
              </Button>
            </div>
            
            <Input
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask me anything..."
              disabled={isLoading}
              className="flex-1 border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 px-4 py-3 text-base"
            />
            
            <div className="flex items-center pr-2 space-x-1">
              <Button variant="ghost" size="sm" className="h-8 w-8 p-0 hover:bg-warm-100">
                <Mic className="w-4 h-4" />
              </Button>
              <Button 
                onClick={handleSendMessage}
                disabled={!message.trim() || isLoading}
                size="sm" 
                className="h-8 w-8 p-0 bg-gradient-primary hover:opacity-90 disabled:opacity-50"
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 text-white animate-spin" />
                ) : (
                  <Send className="w-4 h-4 text-white" />
                )}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
