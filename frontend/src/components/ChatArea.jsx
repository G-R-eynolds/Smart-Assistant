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
    <div className="flex-1 overflow-y-auto bg-sandy-50">
      <div className="chat-area-desktop max-w-4xl mx-auto p-8">
        {/* Welcome Section */}
        {chatHistory.length <= 1 && (
          <div className="text-center mb-12 animate-fade-in">
            <div className="w-16 h-16 gradient-sandy rounded-2xl flex items-center justify-center shadow-lg mx-auto mb-6">
              <span className="text-warm-gray-900 font-bold text-2xl">SA</span>
            </div>
            <h1 className="text-3xl font-bold text-warm-gray-900 mb-4">
              Smart Assistant
            </h1>
            <p className="text-lg text-warm-gray-600 mb-8 max-w-2xl mx-auto">
              Ask me anything about job searching, news, or how I can help you today.
            </p>
            
            {/* Quick Action Pills */}
            <div className="flex flex-wrap justify-center gap-3">
              <button className="px-4 py-2 bg-white border border-beige-200 rounded-full text-sm text-warm-gray-700 hover:bg-beige-50 hover:border-sandy-300 transition-all shadow-sm">
                Search for jobs
              </button>
              <button className="px-4 py-2 bg-white border border-beige-200 rounded-full text-sm text-warm-gray-700 hover:bg-beige-50 hover:border-sandy-300 transition-all shadow-sm">
                Read news digest
              </button>
              <button className="px-4 py-2 bg-white border border-beige-200 rounded-full text-sm text-warm-gray-700 hover:bg-beige-50 hover:border-sandy-300 transition-all shadow-sm">
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
              <div className="w-10 h-10 rounded-full bg-sandy-100 flex items-center justify-center flex-shrink-0">
                <Loader2 size={20} className="text-sandy-600 animate-spin" />
              </div>
              <div className="card p-4 max-w-2xl">
                <div className="flex items-center gap-2 text-warm-gray-600">
                  <span>Thinking</span>
                  <div className="flex gap-1">
                    <div className="w-1 h-1 bg-sandy-400 rounded-full animate-pulse"></div>
                    <div className="w-1 h-1 bg-sandy-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                    <div className="w-1 h-1 bg-sandy-400 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
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