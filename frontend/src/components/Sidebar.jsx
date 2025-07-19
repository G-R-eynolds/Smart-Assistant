import React, { useState } from 'react';
import { 
  Plus, 
  Calendar, 
  MessageSquare, 
  ChevronDown, 
  ChevronRight, 
  Search,
  User,
  Settings,
  ExternalLink,
  Clock
} from 'lucide-react';

const Sidebar = ({ onNewConversation, conversationHistory = [] }) => {
  const [expandedSections, setExpandedSections] = useState({
    digest: true,
    conversations: true
  });

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  // Mock daily digest data
  const dailyDigest = [
    {
      id: 1,
      title: "Tech Giants Announce New AI Collaboration",
      summary: "Major tech companies unveil partnership for responsible AI development...",
      category: "Technology",
      readTime: "3 min read",
      isNew: true
    },
    {
      id: 2,
      title: "Remote Work Trends for 2024 Revealed",
      summary: "New study shows 68% of companies plan to expand remote work options...",
      category: "Workplace",
      readTime: "5 min read",
      isNew: true
    },
    {
      id: 3,
      title: "New Development Framework Released",
      summary: "The framework promises 40% faster development cycles for web applications...",
      category: "Development",
      readTime: "4 min read",
      isNew: false
    }
  ];

  return (
    <div className="w-80 bg-gray-50 border-r border-gray-200 flex flex-col h-full">
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-semibold text-sm">SA</span>
          </div>
          <h1 className="text-xl font-semibold text-gray-900">Smart Assistant</h1>
        </div>
        
        {/* New Conversation Button */}
        <button 
          onClick={onNewConversation}
          className="btn btn-primary w-full"
        >
          <Plus size={18} />
          New Conversation
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {/* Daily Digest Section */}
        <div className="p-6 border-b border-gray-200">
          <button 
            onClick={() => toggleSection('digest')}
            className="w-full flex items-center justify-between mb-4 text-left"
          >
            <div className="flex items-center gap-2">
              <Calendar size={18} className="text-blue-600" />
              <span className="font-medium text-gray-900">Daily Digest</span>
            </div>
            {expandedSections.digest ? 
              <ChevronDown size={16} className="text-gray-400" /> : 
              <ChevronRight size={16} className="text-gray-400" />
            }
          </button>
          
          {expandedSections.digest && (
            <div className="space-y-3">
              {dailyDigest.map((article) => (
                <div 
                  key={article.id}
                  className="card card-hover p-4 cursor-pointer group"
                >
                  <div className="flex items-start justify-between mb-2">
                    <h4 className="font-medium text-gray-900 text-sm line-clamp-2 group-hover:text-blue-600 transition-colors">
                      {article.title}
                    </h4>
                    {article.isNew && (
                      <span className="badge badge-blue ml-2 flex-shrink-0">New</span>
                    )}
                  </div>
                  <p className="text-xs text-gray-600 line-clamp-2 mb-3">
                    {article.summary}
                  </p>
                  <div className="flex items-center justify-between text-xs text-gray-500">
                    <span className="badge badge-gray">{article.category}</span>
                    <div className="flex items-center gap-1">
                      <Clock size={12} />
                      <span>{article.readTime}</span>
                    </div>
                  </div>
                </div>
              ))}
              
              <button className="w-full text-sm text-blue-600 hover:text-blue-700 font-medium py-2 flex items-center justify-center gap-1">
                View All Articles
                <ExternalLink size={14} />
              </button>
            </div>
          )}
        </div>

        {/* Recent Conversations */}
        <div className="p-6">
          <button 
            onClick={() => toggleSection('conversations')}
            className="w-full flex items-center justify-between mb-4 text-left"
          >
            <div className="flex items-center gap-2">
              <MessageSquare size={18} className="text-blue-600" />
              <span className="font-medium text-gray-900">Recent Conversations</span>
            </div>
            {expandedSections.conversations ? 
              <ChevronDown size={16} className="text-gray-400" /> : 
              <ChevronRight size={16} className="text-gray-400" />
            }
          </button>
          
          {expandedSections.conversations && (
            <div className="space-y-2">
              {conversationHistory.length > 0 ? (
                conversationHistory.slice(0, 10).map((conversation) => (
                  <div 
                    key={conversation.id} 
                    className="p-3 hover:bg-gray-100 rounded-lg cursor-pointer transition-colors group"
                  >
                    <p className="font-medium text-gray-900 text-sm truncate group-hover:text-blue-600 transition-colors">
                      {conversation.title}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">{conversation.timestamp}</p>
                  </div>
                ))
              ) : (
                <div className="text-center py-8">
                  <MessageSquare size={32} className="text-gray-300 mx-auto mb-3" />
                  <p className="text-sm text-gray-500">No conversations yet</p>
                  <p className="text-xs text-gray-400 mt-1">Start chatting to see your history here</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* User Profile */}
      <div className="p-6 border-t border-gray-200">
        <div className="flex items-center gap-3 p-3 hover:bg-gray-100 rounded-lg cursor-pointer transition-colors group">
          <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
            <User size={20} className="text-blue-600" />
          </div>
          <div className="flex-1">
            <p className="font-medium text-gray-900 text-sm">Alex Morgan</p>
            <p className="text-xs text-gray-500">Free Plan</p>
          </div>
          <Settings size={18} className="text-gray-400 group-hover:text-gray-600 transition-colors" />
        </div>
      </div>
    </div>
  );
};

export default Sidebar;