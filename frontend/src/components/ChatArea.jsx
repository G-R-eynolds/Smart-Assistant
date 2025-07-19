import React, { useEffect, useRef } from 'react';
import ChatMessage from './ChatMessage';
import { Loader2 } from 'lucide-react';

const ChatArea = ({ chatHistory, isLoading }) => {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatHistory]);

  return (
    <div className="flex-1 overflow-y-auto bg-gray-25">
      <div className="max-w-4xl mx-auto p-6">
        {/* Welcome Section */}
        {chatHistory.length <= 1 && (
          <div className="text-center mb-12 animate-fade-in">
            <h1 className="text-3xl font-bold text-gray-900 mb-4">
              Smart Assistant
            </h1>
            <p className="text-lg text-gray-600 mb-8 max-w-2xl mx-auto">
              Ask me anything about job searching, news, or how I can help you today.
            </p>
            
            {/* Quick Action Pills */}
            <div className="flex flex-wrap justify-center gap-3">
              <button className="px-4 py-2 bg-white border border-gray-200 rounded-full text-sm text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-all shadow-sm">
                Search for jobs
              </button>
              <button className="px-4 py-2 bg-white border border-gray-200 rounded-full text-sm text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-all shadow-sm">
                Read news digest
              </button>
              <button className="px-4 py-2 bg-white border border-gray-200 rounded-full text-sm text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-all shadow-sm">
                Resume help
              </button>
            </div>
          </div>
        )}
        
        {/* Messages */}
        <div className="space-y-6">
          {chatHistory.map((message, index) => (
            <ChatMessage 
              key={index} 
              message={{
                sender: message.sender === 'ai' ? 'assistant' : message.sender,
                text: message.text
              }} 
            />
          ))}
          
          {/* Loading indicator */}
          {isLoading && (
            <div className="flex items-start gap-4 animate-fade-in">
              <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                <Loader2 size={20} className="text-blue-600 animate-spin" />
              </div>
              <div className="card p-4 max-w-2xl">
                <div className="flex items-center gap-2 text-gray-600">
                  <span>Thinking</span>
                  <div className="flex gap-1">
                    <div className="w-1 h-1 bg-gray-400 rounded-full animate-pulse"></div>
                    <div className="w-1 h-1 bg-gray-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                    <div className="w-1 h-1 bg-gray-400 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
        
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};

export default ChatArea;