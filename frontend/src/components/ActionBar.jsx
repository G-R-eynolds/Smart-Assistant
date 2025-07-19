import React from 'react';
import { Save, Briefcase, Database } from 'lucide-react';

const ActionBar = ({ onSaveConversation, onScrapeJobs, onOpenAirtableDatabase }) => {
  return (
    <div className="flex items-center justify-between p-4 bg-white/80 backdrop-blur-sm border-b border-gray-200/50">
      <div className="flex items-center space-x-3">
        <button 
          onClick={onSaveConversation}
          className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-indigo-500 to-purple-600 
          text-white rounded-full hover:from-indigo-600 hover:to-purple-700 transition-all duration-200 
          shadow-md hover:shadow-lg transform hover:scale-105"
        >
          <Save size={18} />
          <span className="font-medium">Save Chat</span>
        </button>
        
        <button 
          onClick={onScrapeJobs}
          className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-blue-500 to-cyan-600 
          text-white rounded-full hover:from-blue-600 hover:to-cyan-700 transition-all duration-200 
          shadow-md hover:shadow-lg transform hover:scale-105"
        >
          <Briefcase size={18} />
          <span className="font-medium">Scrape Jobs</span>
        </button>
        
        <button 
          onClick={onOpenAirtableDatabase}
          className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-emerald-500 to-teal-600 
          text-white rounded-full hover:from-emerald-600 hover:to-teal-700 transition-all duration-200 
          shadow-md hover:shadow-lg transform hover:scale-105"
        >
          <Database size={18} />
          <span className="font-medium">Airtable DB</span>
        </button>
      </div>
      
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2 text-sm text-gray-600">
          <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
          <span>AI Assistant Active</span>
        </div>
      </div>
    </div>
  );
};

export default ActionBar;
