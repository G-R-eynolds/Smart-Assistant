import { TopNavigation } from "@/components/TopNavigation";
import { Sidebar } from "@/components/Sidebar";
import { ChatArea } from "@/components/ChatArea";
import { useChat } from "@/hooks/useChat";
import { useToast } from "@/hooks/use-toast";

const Index = () => {
  const { 
    messages, 
    isLoading, 
    sendMessage, 
    saveConversation, 
    runJobSearch, 
    clearSession 
  } = useChat();
  
  const { toast } = useToast();

  const handleSaveConversation = async () => {
    try {
      const message = await saveConversation();
      toast({
        title: "Success!",
        description: message,
      });
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to save conversation",
        variant: "destructive",
      });
    }
  };

  const handleJobSearch = async () => {
    try {
      await runJobSearch();
      toast({
        title: "Job Search Complete",
        description: "Check the chat for results",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to run job search",
        variant: "destructive",
      });
    }
  };

  const handleOpenJobDatabase = () => {
    // Open Airtable in new tab
    window.open('https://airtable.com', '_blank');
  };

  const handleNewConversation = async () => {
    try {
      await clearSession();
      toast({
        title: "New Conversation",
        description: "Started a fresh conversation",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to start new conversation",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <TopNavigation 
        onSaveConversation={handleSaveConversation}
        onRunJobSearch={handleJobSearch}
        onAccessDatabase={handleOpenJobDatabase}
        isSaving={isLoading}
        isJobSearching={isLoading}
      />
      <div className="flex h-[calc(100vh-3.5rem)]">
        <Sidebar 
          messages={messages}
          onNewConversation={handleNewConversation}
          onClearSession={clearSession}
        />
        <ChatArea 
          messages={messages}
          isLoading={isLoading}
          onSendMessage={sendMessage}
        />
      </div>
    </div>
  );
};

export default Index;
