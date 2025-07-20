
import { Button } from "@/components/ui/button";
import { 
  Save, 
  Database, 
  Search, 
  Settings,
  Sparkles,
  Loader2
} from "lucide-react";

interface TopNavigationProps {
  onSaveConversation: () => void;
  onJobSearch: () => void;
  onOpenJobDatabase: () => void;
  isLoading?: boolean;
}

export const TopNavigation = ({ 
  onSaveConversation, 
  onJobSearch, 
  onOpenJobDatabase,
  isLoading = false 
}: TopNavigationProps) => {
  return (
    <header className="h-14 bg-card border-b border-border flex items-center justify-between px-6">
      {/* Left Section - Logo and Title */}
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-gradient-primary rounded-lg flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gradient-primary">
              Smart Assistant
            </h1>
          </div>
        </div>
      </div>

      {/* Right Section - Action Buttons */}
      <div className="flex items-center space-x-2">
        <Button 
          variant="outline" 
          size="sm" 
          className="h-8 border-warm-300 hover:bg-warm-100"
          onClick={onSaveConversation}
          disabled={isLoading}
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Save className="w-4 h-4 mr-2" />
          )}
          Save Conversation
        </Button>
        
        <Button 
          variant="outline" 
          size="sm" 
          className="h-8 border-warm-300 hover:bg-warm-100"
          onClick={onJobSearch}
          disabled={isLoading}
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Search className="w-4 h-4 mr-2" />
          )}
          Scrape Jobs
        </Button>
        
        <Button 
          variant="outline" 
          size="sm" 
          className="h-8 border-warm-300 hover:bg-warm-100"
          onClick={onOpenJobDatabase}
        >
          <Database className="w-4 h-4 mr-2" />
          Job Database
        </Button>
        
        <div className="w-px h-6 bg-border mx-2" />
        
        <Button variant="ghost" size="sm" className="h-8 w-8 p-0 hover:bg-warm-100">
          <Settings className="w-4 h-4" />
        </Button>
      </div>
    </header>
  );
};
