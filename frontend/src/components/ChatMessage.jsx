import React from 'react';
import { Bot, User } from 'lucide-react';

const ChatMessage = ({ message }) => {
  const { sender, text } = message;

  if (sender === 'assistant') {
    return (
      <div className="flex items-start gap-4 animate-fade-in">
        <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
          <Bot size={20} className="text-blue-600" />
        </div>
        <div className="card p-4 max-w-2xl">
          <div className="prose prose-sm max-w-none">
            {text.split('\n').map((line, index) => (
              <p key={index} className="text-gray-800 leading-relaxed mb-2 last:mb-0">
                {line}
              </p>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (sender === 'user') {
    return (
      <div className="flex items-start justify-end gap-4 animate-fade-in">
        <div className="bg-blue-600 rounded-2xl rounded-tr-lg p-4 max-w-2xl shadow-sm">
          <div className="prose prose-sm max-w-none">
            {text.split('\n').map((line, index) => (
              <p key={index} className="text-white leading-relaxed mb-2 last:mb-0">
                {line}
              </p>
            ))}
          </div>
        </div>
        <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0">
          <User size={20} className="text-gray-600" />
        </div>
      </div>
    );
  }

  return null;
};

export default ChatMessage;