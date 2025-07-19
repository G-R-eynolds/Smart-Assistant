import React, { useState } from 'react';
import axios from 'axios';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import ChatArea from './components/ChatArea';
import ChatInput from './components/ChatInput';

function App() {
  // State for current user input
  const [currentInput, setCurrentInput] = useState('');
  
  // State for chat history - array of objects with 'sender' and 'text' fields
  const [chatHistory, setChatHistory] = useState([
    {
      sender: 'ai',
      text: 'Hello! I\'m your Smart Assistant. I can help you search for jobs, provide daily news updates, or answer any questions you might have. What would you like to do today?'
    }
  ]);

  // Session ID for conversation continuity
  const [sessionId] = useState(() => 'session_' + Date.now());

  // Loading state
  const [isLoading, setIsLoading] = useState(false);

  // Async function to handle sending messages
  const handleSend = async (userMessage) => {
    try {
      setIsLoading(true);
      
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
    } finally {
      setIsLoading(false);
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
          text: 'Hello! I\'m your Smart Assistant. I can help you search for jobs, provide daily news updates, or answer any questions you might have. What would you like to do today?'
        }
      ]);
      
    } catch (error) {
      console.error('Error saving conversation:', error);
      alert('Failed to save conversation. Please try again.');
    }
  };

  // Handle job scraping
  const handleScrapeJobs = async () => {
    try {
      setIsLoading(true);
      
      // Add system message about starting job search
      const systemMessage = { 
        sender: 'ai', 
        text: 'Starting job search... This may take a few moments while I scrape and analyze job postings.' 
      };
      setChatHistory(prev => [...prev, systemMessage]);

      const response = await axios.post('http://127.0.0.1:8000/api/jobs/run-search');
      
      // Add results message
      const resultsMessage = { 
        sender: 'ai', 
        text: response.data.message 
      };
      setChatHistory(prev => [...prev, resultsMessage]);
      
    } catch (error) {
      console.error('Error scraping jobs:', error);
      const errorMessage = { 
        sender: 'ai', 
        text: 'Sorry, I encountered an error while searching for jobs. Please try again.' 
      };
      setChatHistory(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle new conversation
  const handleNewConversation = () => {
    setChatHistory([
      {
        sender: 'ai',
        text: 'Hello! I\'m your Smart Assistant. I can help you search for jobs, provide daily news updates, or answer any questions you might have. What would you like to do today?'
      }
    ]);
    setCurrentInput('');
  };

  return (
    <div className="min-h-screen bg-gray-25">
      <div className="flex h-screen">
        {/* Sidebar */}
        <Sidebar 
          onNewConversation={handleNewConversation}
          conversationHistory={chatHistory
            .filter(message => message.sender === 'user')
            .map((message, index) => ({
              id: index + 1,
              title: message.text.length > 40 ? message.text.substring(0, 40) + '...' : message.text,
              timestamp: 'Today',
              preview: message.text
            }))
          }
        />
        
        {/* Main Content */}
        <div className="flex-1 flex flex-col bg-white">
          {/* Header */}
          <Header 
            onSaveConversation={handleSaveConversation}
            onScrapeJobs={handleScrapeJobs}
            onOpenAirtableDatabase={() => window.open('https://airtable.com', '_blank')}
            isLoading={isLoading}
          />
          
          {/* Chat Area */}
          <ChatArea 
            chatHistory={chatHistory}
            isLoading={isLoading}
          />
          
          {/* Chat Input */}
          <ChatInput 
            value={currentInput}
            onChange={setCurrentInput}
            onSubmit={(userMessage) => {
              handleSend(userMessage);
              setCurrentInput('');
            }}
            disabled={isLoading}
          />
        </div>
      </div>
    </div>
  );
}

export default App;