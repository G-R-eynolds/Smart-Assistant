import React, { useState } from 'react';
import axios from 'axios';
import Sidebar from './components/Sidebar';
import ActionBar from './components/ActionBar';
import ChatInput from './components/ChatInput';
import ChatMessage from './components/ChatMessage';

function App() {
  // State for current user input
  const [currentInput, setCurrentInput] = useState('');
  
  // State for chat history - array of objects with 'sender' and 'text' fields
  const [chatHistory, setChatHistory] = useState([
    {
      sender: 'ai',
      text: 'Hello! I\'m your Smart Assistant. How can I help you today?'
    }
  ]);

  // Session ID for conversation continuity
  const [sessionId] = useState(() => 'session_' + Date.now());

  // Async function to handle sending messages
  const handleSend = async (userMessage) => {
    try {
      // First add the user's message to chat history
      const userMessageObj = { sender: 'user', text: userMessage };
      setChatHistory(prev => [...prev, userMessageObj]);

      // Make POST request to backend API
      const response = await axios.post('http://127.0.0.1:8000/api/chat', {
        message: userMessage,
        session_id: sessionId
      });

      // Add AI's response to chat history
      const aiResponse = { sender: 'ai', text: response.data.response };
      setChatHistory(prev => [...prev, aiResponse]);

    } catch (error) {
      // Log the error and add error message to chat history
      console.error('Error sending message to API:', error);
      const errorMessage = { 
        sender: 'ai', 
        text: 'Sorry, I encountered an error while processing your request. Please try again.' 
      };
      setChatHistory(prev => [...prev, errorMessage]);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (currentInput.trim()) {
      // Call the handleSend function with the current input
      handleSend(currentInput);
      
      // Clear input
      setCurrentInput('');
    }
  };

  // Async function to handle saving conversation
  const handleSaveConversation = async () => {
    try {
      // Format chat history into Q&A pairs
      const conversations = [];
      
      // Process chat history in pairs (user question, AI answer)
      for (let i = 0; i < chatHistory.length - 1; i++) {
        const currentMessage = chatHistory[i];
        const nextMessage = chatHistory[i + 1];
        
        // If current is user and next is AI, create a Q&A pair
        if (currentMessage.sender === 'user' && nextMessage.sender === 'ai') {
          conversations.push({
            question: currentMessage.text,
            answer: nextMessage.text
          });
        }
      }
      
      // Only proceed if we have conversations to save
      if (conversations.length === 0) {
        alert('No conversations to save yet. Start chatting first!');
        return;
      }

      // Send to backend API
      const response = await axios.post('http://127.0.0.1:8000/api/ingest-conversation', {
        conversations: conversations
      });

      // Handle successful response
      alert(`Success! ${response.data.message}`);
      
      // Clear chat history and start fresh
      setChatHistory([
        {
          sender: 'ai',
          text: 'Hello! I\'m your Smart Assistant. How can I help you today?'
        }
      ]);
      
    } catch (error) {
      console.error('Error saving conversation:', error);
      alert('Failed to save conversation. Please try again.');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50">
      <div className="flex h-screen">
        {/* Sidebar */}
        <Sidebar 
          userName="Alex Morgan"
          conversationHistory={chatHistory
            .filter(message => message.sender === 'user')
            .map((message, index) => ({
              id: index + 1,
              title: message.text.length > 30 ? message.text.substring(0, 30) + '...' : message.text,
              timestamp: 'Today'
            }))
          }
        />
        
        {/* Main Content */}
        <div id="main-content" className="flex-grow flex flex-col h-full bg-white/70 backdrop-blur-sm">
          {/* Action Bar */}
          <ActionBar 
            onSaveConversation={handleSaveConversation}
            onScrapeJobs={() => console.log('Scrape jobs clicked')}
            onOpenAirtableDatabase={() => console.log('Airtable database clicked')}
          />
          
          {/* Chat Area */}
          <div id="chat-area" className="flex-grow overflow-y-auto p-6 bg-gradient-to-b from-transparent to-white/20">
            <div className="max-w-4xl mx-auto">
              {/* Welcome Message */}
              <div className="mb-8 text-center">
                <h1 className="text-3xl font-bold text-gray-800 mb-4">Smart Assistant</h1>
                <p className="text-gray-600 text-lg mb-6">Ask me anything about job searching, news, or how I can help you today.</p>
                
                {/* Quick Action Pills */}
                {chatHistory.length <= 1 && (
                  <div className="flex flex-wrap justify-center gap-3 mb-8">
                    <button className="px-4 py-2 bg-white/80 backdrop-blur-sm border border-gray-200 rounded-full text-sm text-gray-700 hover:bg-white hover:shadow-md transition-all duration-200">
                      Search for jobs
                    </button>
                    <button className="px-4 py-2 bg-white/80 backdrop-blur-sm border border-gray-200 rounded-full text-sm text-gray-700 hover:bg-white hover:shadow-md transition-all duration-200">
                      Read news digest
                    </button>
                    <button className="px-4 py-2 bg-white/80 backdrop-blur-sm border border-gray-200 rounded-full text-sm text-gray-700 hover:bg-white hover:shadow-md transition-all duration-200">
                      Resume help
                    </button>
                  </div>
                )}
              </div>
              
              {/* Conversation Thread */}
              <div id="conversation-thread" className="space-y-6">
                {chatHistory.map((message, index) => (
                  <ChatMessage 
                    key={index} 
                    message={{
                      sender: message.sender === 'ai' ? 'assistant' : message.sender,
                      text: message.text
                    }} 
                  />
                ))}
              </div>
            </div>
          </div>
          
          {/* Chat Input */}
          <ChatInput 
            value={currentInput}
            onChange={setCurrentInput}
            onSubmit={(userMessage) => {
              handleSend(userMessage);
              setCurrentInput('');
            }}
          />
        </div>
      </div>
    </div>
  );
}

export default App;