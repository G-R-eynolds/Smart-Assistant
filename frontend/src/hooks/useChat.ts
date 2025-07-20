import { useState, useCallback } from 'react';
import { apiService, QAPair } from '@/lib/api';

export interface Message {
  id: number;
  content: string;
  isUser: boolean;
  timestamp: Date;
}

export const useChat = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      content: "Hello! I'm your Smart Assistant. I can help you with job searches, provide news updates, and answer any questions you might have. What would you like to know today?",
      isUser: false,
      timestamp: new Date()
    }
  ]);
  
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(() => `session_${Date.now()}`);

  const sendMessage = useCallback(async (messageContent: string) => {
    if (!messageContent.trim() || isLoading) return;

    setIsLoading(true);

    // Add user message immediately
    const userMessage: Message = {
      id: Date.now(),
      content: messageContent,
      isUser: true,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);

    try {
      // Call backend API
      const response = await apiService.sendMessage(messageContent, sessionId);
      
      // Add assistant response
      const assistantMessage: Message = {
        id: Date.now() + 1,
        content: response.response,
        isUser: false,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
      
      // Add error message
      const errorMessage: Message = {
        id: Date.now() + 1,
        content: "Sorry, I encountered an error while processing your request. Please try again.",
        isUser: false,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, isLoading]);

  const saveConversation = useCallback(async () => {
    try {
      // Extract Q&A pairs from messages
      const conversations: QAPair[] = [];
      
      for (let i = 0; i < messages.length - 1; i++) {
        const current = messages[i];
        const next = messages[i + 1];
        
        if (current.isUser && !next.isUser) {
          conversations.push({
            question: current.content,
            answer: next.content
          });
        }
      }

      if (conversations.length === 0) {
        throw new Error('No conversations to save. Start chatting first!');
      }

      const response = await apiService.saveConversation(conversations);
      
      // Clear conversation and start fresh
      setMessages([{
        id: 1,
        content: "Hello! I'm your Smart Assistant. How can I help you today?",
        isUser: false,
        timestamp: new Date()
      }]);

      return response.message;
    } catch (error) {
      console.error('Failed to save conversation:', error);
      throw error;
    }
  }, [messages]);

  const runJobSearch = useCallback(async () => {
    try {
      setIsLoading(true);
      
      const response = await apiService.runJobSearch();
      
      // Add success message to chat
      const successMessage: Message = {
        id: Date.now(),
        content: `✅ Job scraping completed! Found ${response.total_found} jobs, saved ${response.saved_count} new ones. ${response.message}`,
        isUser: false,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, successMessage]);
      
      return response;
    } catch (error) {
      console.error('Failed to run job search:', error);
      
      // Add error message to chat
      const errorMessage: Message = {
        id: Date.now(),
        content: '❌ Failed to scrape jobs. Please check if the backend is running and try again.',
        isUser: false,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, errorMessage]);
      
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const clearSession = useCallback(async () => {
    try {
      await apiService.clearSession(sessionId);
      
      // Reset messages to initial state
      setMessages([{
        id: 1,
        content: "Hello! I'm your Smart Assistant. How can I help you today?",
        isUser: false,
        timestamp: new Date()
      }]);
    } catch (error) {
      console.error('Failed to clear session:', error);
      throw error;
    }
  }, [sessionId]);

  return {
    messages,
    isLoading,
    sendMessage,
    saveConversation,
    runJobSearch,
    clearSession,
    sessionId
  };
};
