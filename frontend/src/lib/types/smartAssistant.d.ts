// Missing type definitions for Smart Assistant components

declare module 'lucide-svelte' {
	export const Search: any;
	export const Filter: any;
	export const RefreshCw: any;
	export const ExternalLink: any;
	export const MapPin: any;
	export const Building: any;
	export const Clock: any;
	export const DollarSign: any;
	export const Bookmark: any;
	export const BookmarkCheck: any;
	export const ChevronDown: any;
	export const ChevronUp: any;
	export const Brain: any;
	export const Star: any;
	export const Users: any;
	export const Calendar: any;
	export const Zap: any;
	export const Mail: any;
	export const FileText: any;
	export const AlertCircle: any;
}

declare module 'svelte-sonner' {
	export const toast: {
		error: (message: string) => void;
		success: (message: string) => void;
		warning: (message: string) => void;
		info: (message: string) => void;
	};
}

// Extend Window interface for global types if needed
declare global {
	interface Window {
		smartAssistant?: any;
	}
}

export {};
