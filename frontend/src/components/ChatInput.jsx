import React from 'react';
import { Paperclip, Mic, Send, Sparkles } from 'lucide-react';

const ChatInput = ({ 
  value = '', 
  onChange, 
  onSubmit,
  placeholder = "Message your assistant..."
}) => {
  const handleInputChange = (e) => {
    if (onChange) {
      onChange(e.target.value);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (onSubmit && value.trim()) {
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

  return (
    <div className="p-6 bg-gradient-to-t from-white to-white/50 backdrop-blur-sm border-t border-gray-200/50">
      <div className="max-w-4xl mx-auto">
        {/* Suggestion Pills */}
        {!value && (
          <div className="flex flex-wrap justify-center gap-2 mb-4">
            <button className="px-3 py-1 bg-white/80 backdrop-blur-sm border border-gray-200 rounded-full text-sm text-gray-600 hover:bg-white hover:shadow-md transition-all duration-200">
              Find remote jobs
            </button>
            <button className="px-3 py-1 bg-white/80 backdrop-blur-sm border border-gray-200 rounded-full text-sm text-gray-600 hover:bg-white hover:shadow-md transition-all duration-200">
              Latest tech news
            </button>
            <button className="px-3 py-1 bg-white/80 backdrop-blur-sm border border-gray-200 rounded-full text-sm text-gray-600 hover:bg-white hover:shadow-md transition-all duration-200">
              Review my resume
            </button>
          </div>
        )}
        
        <form onSubmit={handleSubmit}>
          <div className="relative">
            <div className="flex items-center bg-white/90 backdrop-blur-md border border-gray-200/50 rounded-2xl shadow-lg hover:shadow-xl transition-all duration-200 overflow-hidden">
              {/* Paperclip Button */}
              <button 
                type="button"
                className="p-4 text-gray-500 hover:text-indigo-600 hover:bg-gray-50 transition-colors"
                onClick={handlePaperclipClick}
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
                className="flex-grow py-4 px-2 bg-transparent focus:outline-none text-gray-800 placeholder-gray-500"
              />
              
              <div className="flex items-center">
                {/* Microphone Button */}
                <button 
                  type="button"
                  className="p-4 text-gray-500 hover:text-indigo-600 hover:bg-gray-50 transition-colors"
                  onClick={handleMicrophoneClick}
                >
                  <Mic size={20} />
                </button>
                
                {/* Send Button */}
                <button 
                  type="submit"
                  className={`m-2 p-3 rounded-xl transition-all duration-200 ${
                    value.trim() 
                      ? 'bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-md hover:shadow-lg transform hover:scale-105' 
                      : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  }`}
                  disabled={!value.trim()}
                >
                  <Send size={20} />
                </button>
              </div>
            </div>
            
            {/* AI Enhancement Indicator */}
            {value && (
              <div className="absolute -top-8 left-4 flex items-center space-x-2 text-xs text-indigo-600">
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
