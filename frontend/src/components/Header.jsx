import React from 'react';
import { Save, Briefcase, Database, Loader2 } from 'lucide-react';

const Header = ({ 
  onSaveConversation, 
  onScrapeJobs, 
  onOpenAirtableDatabase, 
  isLoading = false 
}) => {
  return (
    <div className="flex items-center justify-between p-6 border-b border-gray-200 bg-white">
      <div className="flex items-center gap-3">
        <button 
          onClick={onSaveConversation}
          disabled={isLoading}
          className="btn btn-secondary"
        >
          <Save size={18} />
          Save Conversation
        </button>
        
        <button 
          onClick={onScrapeJobs}
          disabled={isLoading}
          className="btn btn-primary"
        >
          {isLoading ? (
            <Loader2 size={18} className="animate-spin" />
          ) : (
            <Briefcase size={18} />
          )}
          Scrape Jobs
        </button>
        
        <button 
          onClick={onOpenAirtableDatabase}
          disabled={isLoading}
          className="btn btn-secondary"
        >
          <Database size={18} />
          Airtable Database
        </button>
      </div>
      
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
          <span>AI Assistant Active</span>
        </div>
      </div>
    </div>
  );
};

export default Header;