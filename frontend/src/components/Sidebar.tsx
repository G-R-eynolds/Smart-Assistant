
import { NewsDigestCard } from "./NewsDigestCard";
import { Calendar, TrendingUp, Globe } from "lucide-react";

interface Message {
  id: number;
  content: string;
  isUser: boolean;
  timestamp: Date;
}

interface SidebarProps {
  messages: Message[];
  onNewConversation: () => void;
  onClearSession: () => void;
}

export const Sidebar = ({ messages, onNewConversation, onClearSession }: SidebarProps) => {
  const newsItems = [
    {
      title: "AI Revolution: New Breakthrough in Machine Learning Models",
      summary: "Researchers announce significant improvements in natural language processing capabilities...",
      source: "TechNews",
      time: "2 hours ago",
      category: "AI & Tech",
      thumbnail: "/placeholder.svg"
    },
    {
      title: "Remote Work Trends: Companies Adapt to Hybrid Models",
      summary: "Latest survey shows 73% of companies planning to maintain flexible work arrangements...",
      source: "WorkLife",
      time: "4 hours ago",
      category: "Business",
      thumbnail: "/placeholder.svg"
    },
    {
      title: "Startup Funding Reaches New Heights in Q4",
      summary: "Venture capital investments show strong growth across technology sectors...",
      source: "StartupDaily",
      time: "6 hours ago",
      category: "Finance",
      thumbnail: "/placeholder.svg"
    },
    {
      title: "Green Technology: Solar Energy Costs Drop by 25%",
      summary: "New manufacturing processes make renewable energy more accessible worldwide...",
      source: "EcoTech",
      time: "8 hours ago",
      category: "Environment",
      thumbnail: "/placeholder.svg"
    }
  ];

  return (
    <aside className="w-80 bg-card border-r border-border h-full flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-border">
        <div className="flex items-center space-x-2 mb-4">
          <div className="w-8 h-8 bg-gradient-warm rounded-lg flex items-center justify-center">
            <TrendingUp className="w-5 h-5 text-white" />
          </div>
          <h2 className="text-lg font-semibold text-foreground">Daily Digest</h2>
        </div>
        
        <div className="flex items-center text-sm text-muted-foreground">
          <Calendar className="w-4 h-4 mr-2" />
          <span>{new Date().toLocaleDateString('en-US', { 
            weekday: 'long', 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
          })}</span>
        </div>
      </div>

      {/* News Feed */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-4">
          {newsItems.map((item, index) => (
            <NewsDigestCard
              key={index}
              title={item.title}
              summary={item.summary}
              source={item.source}
              time={item.time}
              category={item.category}
              thumbnail={item.thumbnail}
            />
          ))}
        </div>
      </div>

      {/* Previous Chats */}
      <div className="p-4 border-t border-border">
        <div className="flex items-center space-x-2 mb-3">
          <div className="w-6 h-6 bg-gradient-warm rounded-md flex items-center justify-center">
            <Calendar className="w-4 h-4 text-white" />
          </div>
          <h3 className="text-sm font-medium text-foreground">Previous Chats</h3>
        </div>
        
        <div className="space-y-2">
          {messages.length > 1 ? [
            `Current conversation: ${messages.length - 1} messages`,
            "Job search strategy discussion",
            "Resume optimization tips", 
            "Interview preparation guide",
            "Salary negotiation advice"
          ].map((chat, index) => (
            <div 
              key={index}
              className={`p-2 rounded-lg cursor-pointer transition-colors ${
                index === 0 ? "bg-accent/50 hover:bg-accent" : "bg-muted/50 hover:bg-muted"
              }`}
              onClick={index === 0 ? onNewConversation : undefined}
            >
              <p className="text-xs text-muted-foreground truncate">{chat}</p>
            </div>
          )) : [
            "Job search strategy discussion",
            "Resume optimization tips", 
            "Interview preparation guide",
            "Salary negotiation advice"
          ].map((chat, index) => (
            <div 
              key={index}
              className="p-2 rounded-lg bg-muted/50 hover:bg-muted cursor-pointer transition-colors"
            >
              <p className="text-xs text-muted-foreground truncate">{chat}</p>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
};
