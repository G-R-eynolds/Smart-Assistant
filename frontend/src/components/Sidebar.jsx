import React, { useState } from 'react';
import { PlusCircle, Menu, Calendar, Users, User, Settings, ChevronDown, ChevronRight, MessageSquare } from 'lucide-react';

const Sidebar = ({ userName = "Alex Morgan", conversationHistory = [] }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
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

  return (
    <div className={`bg-white/90 backdrop-blur-md border-r border-gray-200/50 transition-all duration-300 ${
      isCollapsed ? 'w-16' : 'w-80'
    } flex flex-col h-full shadow-lg`}>
      
      {/* Header */}
      <div className="p-4 border-b border-gray-200/50">
        <div className="flex items-center justify-between">
          {!isCollapsed && (
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">SA</span>
              </div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                Smart Assistant
              </h1>
            </div>
          )}
          <button 
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <Menu size={20} className="text-gray-600" />
          </button>
        </div>
      </div>

      {/* New Conversation Button */}
      <div className="p-4">
        <button className={`w-full bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-xl py-3 px-4 
          hover:from-indigo-600 hover:to-purple-700 transition-all duration-200 shadow-md hover:shadow-lg
          ${isCollapsed ? 'px-2' : ''}`}>
          <div className="flex items-center justify-center space-x-2">
            <PlusCircle size={20} />
            {!isCollapsed && <span className="font-medium">New Conversation</span>}
          </div>
        </button>
      </div>

      {/* Content Sections */}
      <div className="flex-grow overflow-y-auto">
        {!isCollapsed && (
          <>
            {/* Daily Digest Section */}
            <div className="px-4 pb-4">
              <button 
                onClick={() => toggleSection('digest')}
                className="w-full flex items-center justify-between py-2 text-left"
              >
                <div className="flex items-center space-x-2">
                  <Calendar size={18} className="text-indigo-500" />
                  <span className="font-medium text-gray-700">Daily Digest</span>
                </div>
                {expandedSections.digest ? 
                  <ChevronDown size={16} className="text-gray-400" /> : 
                  <ChevronRight size={16} className="text-gray-400" />
                }
              </button>
              
              {expandedSections.digest && (
                <div className="mt-2 space-y-2 ml-6">
                  <div className="p-3 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border-l-4 border-indigo-400">
                    <p className="text-sm font-medium text-gray-800">Today's Job Market</p>
                    <p className="text-xs text-gray-600 mt-1">15 new opportunities in your field</p>
                  </div>
                  <div className="p-3 bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg border-l-4 border-green-400">
                    <p className="text-sm font-medium text-gray-800">News Summary</p>
                    <p className="text-xs text-gray-600 mt-1">Key updates in tech industry</p>
                  </div>
                </div>
              )}
            </div>

            {/* Recent Conversations */}
            <div className="px-4 pb-4">
              <button 
                onClick={() => toggleSection('conversations')}
                className="w-full flex items-center justify-between py-2 text-left"
              >
                <div className="flex items-center space-x-2">
                  <MessageSquare size={18} className="text-purple-500" />
                  <span className="font-medium text-gray-700">Recent Chats</span>
                </div>
                {expandedSections.conversations ? 
                  <ChevronDown size={16} className="text-gray-400" /> : 
                  <ChevronRight size={16} className="text-gray-400" />
                }
              </button>
              
              {expandedSections.conversations && (
                <div className="mt-2 space-y-1 ml-6">
                  {conversationHistory.length > 0 ? (
                    conversationHistory.slice(0, 8).map((conversation) => (
                      <div 
                        key={conversation.id} 
                        className="p-3 hover:bg-gray-50 rounded-lg cursor-pointer transition-colors group"
                      >
                        <p className="text-sm font-medium text-gray-800 truncate group-hover:text-indigo-600">
                          {conversation.title}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">{conversation.timestamp}</p>
                      </div>
                    ))
                  ) : (
                    <div className="p-3 text-center">
                      <p className="text-sm text-gray-500">No recent conversations</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* User Profile */}
      <div className="p-4 border-t border-gray-200/50">
        {!isCollapsed ? (
          <div className="flex items-center space-x-3 p-3 hover:bg-gray-50 rounded-lg cursor-pointer transition-colors">
            <div className="w-10 h-10 bg-gradient-to-r from-indigo-400 to-purple-500 rounded-full flex items-center justify-center">
              <User size={20} className="text-white" />
            </div>
            <div className="flex-grow">
              <p className="font-medium text-gray-800">{userName}</p>
              <p className="text-sm text-gray-500">Free Plan</p>
            </div>
            <Settings size={18} className="text-gray-400 hover:text-gray-600" />
          </div>
        ) : (
          <div className="flex justify-center">
            <div className="w-10 h-10 bg-gradient-to-r from-indigo-400 to-purple-500 rounded-full flex items-center justify-center cursor-pointer">
              <User size={20} className="text-white" />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Sidebar;
