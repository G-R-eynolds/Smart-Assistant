import React from 'react';
import { Bot, User } from 'lucide-react';

const ChatMessage = ({ message }) => {
  const { sender, text } = message;

  if (sender === 'assistant') {
    return (
      <div className="flex items-start space-x-4 mb-6">
        <div className="w-10 h-10 rounded-full bg-gradient-to-r from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0 shadow-md">
          <Bot size={20} className="text-white" />
        </div>
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl rounded-tl-md p-4 shadow-md border border-gray-200/50 max-w-3xl">
          <p className="text-gray-800 leading-relaxed">{text}</p>
        </div>
      </div>
    );
  }

  if (sender === 'user') {
    return (
      <div className="flex items-start justify-end space-x-4 mb-6">
        <div className="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-2xl rounded-tr-md p-4 max-w-3xl shadow-md">
          <p className="text-white leading-relaxed">{text}</p>
        </div>
        <div className="w-10 h-10 rounded-full bg-gradient-to-r from-gray-400 to-gray-500 flex items-center justify-center flex-shrink-0 shadow-md">
          <User size={20} className="text-white" />
        </div>
      </div>
    );
  }

  return null;
};

export default ChatMessage;
