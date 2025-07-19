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
    <div className="p-6 bg-gradient-warm border-t border-beige-200">
      <div className="chat-area-desktop max-w-4xl mx-auto">
        {/* Suggestion Pills */}
        {!value && (
          <div className="flex flex-wrap justify-center gap-2 mb-4">
            {suggestions.map((suggestion, index) => (
              <button 
                key={index}
                onClick={() => onChange && onChange(suggestion)}
                className="px-3 py-1 bg-white border border-beige-200 rounded-full text-sm text-warm-gray-600 hover:bg-beige-50 hover:border-sandy-300 transition-all shadow-sm"
                disabled={disabled}
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}
        
        <form onSubmit={handleSubmit}>
          <div className="relative">
            <div className="flex items-center bg-white border border-beige-300 rounded-2xl shadow-md hover:shadow-lg transition-all focus-within:border-sandy-400 focus-within:shadow-lg overflow-hidden">
              {/* Paperclip Button */}
              <button 
                type="button"
                className="p-4 text-warm-gray-400 hover:text-sandy-600 transition-colors disabled:opacity-50"
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
                className="flex-1 py-4 px-2 bg-transparent focus:outline-none text-warm-gray-900 placeholder-warm-gray-400 disabled:opacity-50"
              />
              
              <div className="flex items-center">
                {/* Microphone Button */}
                <button 
                  type="button"
                  className="p-4 text-warm-gray-400 hover:text-sandy-600 transition-colors disabled:opacity-50"
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
                      ? 'gradient-sandy hover:shadow-md text-warm-gray-900 shadow-sm transform hover:scale-105 font-medium' 
                      : 'bg-beige-100 text-warm-gray-400 cursor-not-allowed'
                  }`}
                  disabled={!value.trim() || disabled}
                >
                  <Send size={20} />
                </button>
              </div>
            </div>
            
            {/* AI Enhancement Indicator */}
            {value && (
              <div className="absolute -top-8 left-4 flex items-center gap-2 text-xs text-sandy-600">
                <Sparkles size={14} className="animate-pulse" />
                <span>AI enhanced</span>
              </div>
            )}
          </div>
        </form>
        
        {/* Footer Info */}
        <div className="flex justify-center items-center mt-3 text-xs text-warm-gray-500">
          <span>Press Enter to send • Shift+Enter for new line</span>
        </div>
      </div>
    </div>
  );
};

export default ChatInput;