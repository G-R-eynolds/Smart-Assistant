
interface NewsDigestCardProps {
  title: string;
  summary: string;
  source: string;
  time: string;
  category?: string;
  thumbnail?: string;
}

export const NewsDigestCard = ({ 
  title, 
  summary, 
  source, 
  time, 
  category = "Technology",
  thumbnail = "/placeholder.svg"
}: NewsDigestCardProps) => {
  return (
    <div className="bg-card border border-border rounded-lg p-4 hover:shadow-md transition-all duration-200 hover:border-warm-300">
      <div className="flex gap-3">
        {/* Thumbnail */}
        <div className="flex-shrink-0">
          <img 
            src={thumbnail} 
            alt={title}
            className="w-16 h-16 rounded-lg object-cover bg-muted"
          />
        </div>
        
        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-2">
            <span className="px-2 py-1 bg-gradient-primary text-white text-xs rounded-full font-medium">
              {category}
            </span>
            <span className="text-xs text-muted-foreground">{time}</span>
          </div>
          
          <h4 className="font-medium text-sm text-foreground mb-2 line-clamp-2 leading-tight">
            {title}
          </h4>
          
          <p className="text-xs text-muted-foreground mb-2 line-clamp-2 leading-relaxed">
            {summary}
          </p>
          
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-warm-600">{source}</span>
            <button className="text-xs text-primary hover:text-warm-700 font-medium transition-colors">
              Read more
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
