import React from 'react';
import { Paperclip, Mic, Send, Sparkles } from 'lucide-react';

const ChatInput = ({ 
  value = '', 
  onChange, 
  onSubmit,
  disabled = false,
  placeholder = "Message your assistant..."
}) => {
  const handleInputChange = (e) => {
    if (onChange) {
      onChange(e.target.value);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (onSubmit && value.trim() && !disabled) {
      onSubmit(value);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handlePaperclipClick = () => {
    console.log('File attachment clicked');
  };

  const handleMicrophoneClick = () => {
    console.log('Voice input clicked');
  };

  // Suggestion pills data
  const suggestions = [
    "Find remote software engineering jobs",
    "What's in today's tech news?",
    "Help me improve my resume",
    "Search for Python developer positions"
  ];

  return (
    <div className="p-6 bg-white border-t border-gray-200">
      <div className="max-w-4xl mx-auto">
        {/* Suggestion Pills */}
        {!value && (
          <div className="flex flex-wrap justify-center gap-2 mb-4">
            {suggestions.map((suggestion, index) => (
              <button 
                key={index}
                onClick={() => onChange && onChange(suggestion)}
                className="px-3 py-1 bg-gray-50 border border-gray-200 rounded-full text-sm text-gray-600 hover:bg-gray-100 hover:border-gray-300 transition-all"
                disabled={disabled}
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}
        
        <form onSubmit={handleSubmit}>
          <div className="relative">
            <div className="flex items-center bg-white border border-gray-300 rounded-2xl shadow-sm hover:shadow-md transition-all focus-within:border-blue-500 focus-within:shadow-md overflow-hidden">
              {/* Paperclip Button */}
              <button 
                type="button"
                className="p-4 text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50"
                onClick={handlePaperclipClick}
                disabled={disabled}
              >
                <Paperclip size={20} />
              </button>
              
              {/* Text Input */}
              <input 
                type="text" 
                placeholder={placeholder}
                value={value}
                onChange={handleInputChange}
                onKeyPress={handleKeyPress}
                disabled={disabled}
                className="flex-1 py-4 px-2 bg-transparent focus:outline-none text-gray-900 placeholder-gray-500 disabled:opacity-50"
              />
              
              <div className="flex items-center">
                {/* Microphone Button */}
                <button 
                  type="button"
                  className="p-4 text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50"
                  onClick={handleMicrophoneClick}
                  disabled={disabled}
                >
                  <Mic size={20} />
                </button>
                
                {/* Send Button */}
                <button 
                  type="submit"
                  className={`m-2 p-3 rounded-xl transition-all ${
                    value.trim() && !disabled
                      ? 'bg-blue-600 hover:bg-blue-700 text-white shadow-sm hover:shadow-md transform hover:scale-105' 
                      : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  }`}
                  disabled={!value.trim() || disabled}
                >
                  <Send size={20} />
                </button>
              </div>
            </div>
            
            {/* AI Enhancement Indicator */}
            {value && (
              <div className="absolute -top-8 left-4 flex items-center gap-2 text-xs text-blue-600">
                <Sparkles size={14} className="animate-pulse" />
                <span>AI enhanced</span>
              </div>
            )}
          </div>
        </form>
        
        {/* Footer Info */}
        <div className="flex justify-center items-center mt-3 text-xs text-gray-500">
          <span>Press Enter to send • Shift+Enter for new line</span>
        </div>
      </div>
    </div>
  );
};

export default ChatInput;