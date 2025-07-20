
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MapPin, DollarSign, Building, Clock, Bookmark } from "lucide-react";

interface JobCardProps {
  title: string;
  company: string;
  location: string;
  salary: string;
  description: string;
  tags: string[];
  postedTime?: string;
}

export const JobCard = ({ 
  title, 
  company, 
  location, 
  salary, 
  description, 
  tags,
  postedTime = "2 days ago"
}: JobCardProps) => {
  return (
    <div className="bg-card border border-border rounded-lg p-6 hover:shadow-lg transition-all duration-200 hover:border-warm-300 animate-fade-in">
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-foreground mb-1 hover:text-primary cursor-pointer transition-colors">
            {title}
          </h3>
          <div className="flex items-center text-muted-foreground text-sm space-x-4">
            <div className="flex items-center">
              <Building className="w-4 h-4 mr-1" />
              <span className="font-medium">{company}</span>
            </div>
            <div className="flex items-center">
              <MapPin className="w-4 h-4 mr-1" />
              <span>{location}</span>
            </div>
            <div className="flex items-center">
              <Clock className="w-4 h-4 mr-1" />
              <span>{postedTime}</span>
            </div>
          </div>
        </div>
        <Button variant="ghost" size="sm" className="hover:bg-warm-100">
          <Bookmark className="w-4 h-4" />
        </Button>
      </div>

      {/* Salary */}
      <div className="flex items-center mb-3">
        <DollarSign className="w-4 h-4 mr-1 text-warm-600" />
        <span className="font-semibold text-warm-700 text-lg">{salary}</span>
      </div>

      {/* Description */}
      <p className="text-muted-foreground text-sm mb-4 leading-relaxed">
        {description}
      </p>

      {/* Tags */}
      <div className="flex flex-wrap gap-2 mb-4">
        {tags.map((tag, index) => (
          <Badge 
            key={index} 
            variant="secondary" 
            className="bg-warm-100 text-warm-800 hover:bg-warm-200 transition-colors"
          >
            {tag}
          </Badge>
        ))}
      </div>

      {/* Actions */}
      <div className="flex space-x-3">
        <Button className="flex-1 bg-gradient-primary hover:opacity-90 text-white">
          Apply Now
        </Button>
        <Button variant="outline" className="border-warm-300 hover:bg-warm-50">
          Learn More
        </Button>
      </div>
    </div>
  );
};
