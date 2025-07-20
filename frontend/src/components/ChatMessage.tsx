
import { format } from "date-fns";

interface ChatMessageProps {
  message: {
    id: number;
    content: string;
    isUser: boolean;
    timestamp: Date;
  };
}

export const ChatMessage = ({ message }: ChatMessageProps) => {
  return (
    <div className={`flex ${message.isUser ? 'justify-end' : 'justify-start'} mb-6`}>
      <div className={`max-w-[80%] ${message.isUser ? 'order-2' : 'order-1'}`}>
        {!message.isUser && (
          <div className="flex items-center mb-2">
            <div className="w-6 h-6 bg-gradient-primary rounded-full flex items-center justify-center mr-2">
              <span className="text-xs text-white font-medium">AI</span>
            </div>
            <span className="text-sm text-muted-foreground">
              Smart Assistant
            </span>
          </div>
        )}
        
        <div
          className={`rounded-2xl px-4 py-3 ${
            message.isUser
              ? 'bg-gradient-primary text-white ml-auto'
              : 'bg-card border border-border text-foreground'
          }`}
        >
          <p className="text-sm leading-relaxed whitespace-pre-wrap">
            {message.content}
          </p>
        </div>
        
        <div className={`mt-1 ${message.isUser ? 'text-right' : 'text-left'}`}>
          <span className="text-xs text-muted-foreground">
            {format(message.timestamp, 'HH:mm')}
          </span>
        </div>
      </div>
    </div>
  );
};
