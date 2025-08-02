/**
 * Smart Assistant Store for Open WebUI Integration
 * 
 * Manages state for Smart Assistant features including:
 * - Job discovery and search results
 * - Inbox management and email processing  
 * - Intelligence briefing generation
 * - Pipeline integration status
 */

import { writable, derived, type Writable } from 'svelte/store';

// ============================================================================
// Types and Interfaces
// ============================================================================

export interface SmartAssistantJob {
	id: string;
	title: string;
	company: string;
	location: string;
	relevance_score: number;
	ai_insights: {
		match_reasoning: string;
		skills_match: string[];
		experience_match: boolean;
	};
	status: 'discovered' | 'saved' | 'applied' | 'rejected';
	discovered_at: string;
	job_url: string;
	description: string;
	employment_type: string;
	experience_level: string;
	salary_min?: number;
	salary_max?: number;
}

export interface EmailSummary {
	id: string;
	sender: string;
	subject: string;
	urgency: 'low' | 'medium' | 'high';
	category: string;
	received_at: string;
	preview?: string;
}

export interface InboxProcessingResult {
	status: string;
	unread_count: number;
	total_emails: number;
	important_emails: EmailSummary[];
	categories: Record<string, number>;
	action_items: Array<{
		description: string;
		priority: 'low' | 'medium' | 'high';
		due_date: string;
	}>;
	processing_time_ms?: number;
}

export interface BriefingItem {
	title: string;
	source: string;
	category: string;
	summary: string;
	published_at: string;
	relevance: 'low' | 'medium' | 'high';
	url?: string;
}

export interface IntelligenceBriefing {
	status: string;
	generated_at: string;
	news_items: BriefingItem[];
	market_data: Record<string, any>;
	tech_trends: Array<{
		title: string;
		impact_score: number;
		summary: string;
	}>;
	career_insights: Array<{
		title: string;
		relevance: string;
		description: string;
	}>;
	key_takeaways: string[];
	generation_time_ms?: number;
}

export interface SmartAssistantConfig {
	enabled: boolean;
	microservice_url: string;
	job_discovery_enabled: boolean;
	inbox_management_enabled: boolean;
	intelligence_briefing_enabled: boolean;
	auto_save_jobs: boolean;
	notification_preferences: {
		job_alerts: boolean;
		email_notifications: boolean;
		briefing_updates: boolean;
	};
}

export interface SmartAssistantState {
	// Configuration
	config: SmartAssistantConfig;
	
	// Job Discovery
	jobs: SmartAssistantJob[];
	job_search_in_progress: boolean;
	last_job_search: string | null;
	job_search_params: Record<string, any>;
	
	// Inbox Management  
	inbox_result: InboxProcessingResult | null;
	inbox_processing: boolean;
	last_inbox_check: string | null;
	
	// Intelligence Briefing
	latest_briefing: IntelligenceBriefing | null;
	briefing_in_progress: boolean;
	last_briefing_generated: string | null;
	
	// Pipeline Status
	pipeline_status: {
		job_discovery_active: boolean;
		inbox_management_active: boolean;
		intelligence_briefing_active: boolean;
	};
	
	// UI State
	show_job_interface: boolean;
	show_inbox_interface: boolean;
	show_briefing_interface: boolean;
	active_command: string | null;
	command_suggestions: string[];
}

// ============================================================================
// Store Implementation  
// ============================================================================

// Default configuration
const defaultConfig: SmartAssistantConfig = {
	enabled: true,
	microservice_url: 'http://localhost:8001',
	job_discovery_enabled: true,
	inbox_management_enabled: true,
	intelligence_briefing_enabled: true,
	auto_save_jobs: false,
	notification_preferences: {
		job_alerts: true,
		email_notifications: true,
		briefing_updates: true
	}
};

// Default state
const defaultState: SmartAssistantState = {
	config: defaultConfig,
	
	jobs: [],
	job_search_in_progress: false,
	last_job_search: null,
	job_search_params: {},
	
	inbox_result: null,
	inbox_processing: false,
	last_inbox_check: null,
	
	latest_briefing: null,
	briefing_in_progress: false,
	last_briefing_generated: null,
	
	pipeline_status: {
		job_discovery_active: false,
		inbox_management_active: false,
		intelligence_briefing_active: false
	},
	
	show_job_interface: false,
	show_inbox_interface: false,
	show_briefing_interface: false,
	active_command: null,
	command_suggestions: []
};

// Main Smart Assistant store
export const smartAssistant: Writable<SmartAssistantState> = writable(defaultState);

// ============================================================================
// Derived Stores (Computed Values)
// ============================================================================

export const jobSearchResults = derived(
	smartAssistant,
	($smartAssistant: SmartAssistantState) => $smartAssistant.jobs
);

export const qualifiedJobs = derived(
	smartAssistant,
	($smartAssistant: SmartAssistantState) => $smartAssistant.jobs.filter((job: SmartAssistantJob) => job.relevance_score >= 0.7)
);

export const savedJobs = derived(
	smartAssistant,
	($smartAssistant: SmartAssistantState) => $smartAssistant.jobs.filter((job: SmartAssistantJob) => job.status === 'saved')
);

export const isSmartAssistantEnabled = derived(
	smartAssistant,
	($smartAssistant: SmartAssistantState) => $smartAssistant.config.enabled
);

export const hasActiveProcesses = derived(
	smartAssistant,
	($smartAssistant: SmartAssistantState) => $smartAssistant.job_search_in_progress || 
					   $smartAssistant.inbox_processing || 
					   $smartAssistant.briefing_in_progress
);

export const unreadEmailCount = derived(
	smartAssistant,
	($smartAssistant: SmartAssistantState) => $smartAssistant.inbox_result?.unread_count || 0
);

export const latestBriefingItems = derived(
	smartAssistant,
	($smartAssistant: SmartAssistantState) => $smartAssistant.latest_briefing?.news_items?.slice(0, 5) || []
);

// ============================================================================
// Smart Assistant Commands Detection
// ============================================================================

export const SMART_ASSISTANT_COMMANDS = {
	// Job Discovery Commands
	JOB_SEARCH: [
		'find jobs', 'search jobs', 'job search', 'look for jobs', 
		'discover jobs', 'job opportunities', 'scrape jobs', 'get jobs',
		'linkedin jobs', 'job hunt', 'career opportunities'
	],
	
	// Inbox Management Commands  
	EMAIL_CHECK: [
		'check email', 'check inbox', 'process inbox', 'email summary',
		'unread emails', 'important emails', 'inbox status'
	],
	
	// Intelligence Briefing Commands
	BRIEFING: [
		'daily briefing', 'intelligence briefing', 'generate briefing',
		'news summary', 'market update', 'tech trends', 'intelligence update'
	],
	
	// Job Management Commands
	JOB_SAVE: ['save job', 'bookmark job', 'add to airtable'],
	JOB_APPLY: ['apply to job', 'apply for position'],
	JOB_DETAILS: ['job details', 'more info', 'full description']
};

// ============================================================================
// Store Actions (Business Logic)
// ============================================================================

export const smartAssistantActions = {
	
	// Configuration Actions
	updateConfig: (newConfig: Partial<SmartAssistantConfig>) => {
		smartAssistant.update((state: SmartAssistantState) => ({
			...state,
			config: { ...state.config, ...newConfig }
		}));
	},
	
	// Job Discovery Actions
	startJobSearch: (searchParams: Record<string, any>) => {
		smartAssistant.update((state: SmartAssistantState) => ({
			...state,
			job_search_in_progress: true,
			job_search_params: searchParams,
			show_job_interface: true
		}));
	},
	
	updateJobResults: (jobs: SmartAssistantJob[]) => {
		smartAssistant.update((state: SmartAssistantState) => ({
			...state,
			jobs,
			job_search_in_progress: false,
			last_job_search: new Date().toISOString()
		}));
	},
	
	saveJob: (jobId: string) => {
		smartAssistant.update((state: SmartAssistantState) => ({
			...state,
			jobs: state.jobs.map((job: SmartAssistantJob) => 
				job.id === jobId ? { ...job, status: 'saved' } : job
			)
		}));
	},
	
	// Inbox Management Actions
	startInboxProcessing: () => {
		smartAssistant.update((state: SmartAssistantState) => ({
			...state,
			inbox_processing: true,
			show_inbox_interface: true
		}));
	},
	
	updateInboxResult: (result: InboxProcessingResult) => {
		smartAssistant.update((state: SmartAssistantState) => ({
			...state,
			inbox_result: result,
			inbox_processing: false,
			last_inbox_check: new Date().toISOString()
		}));
	},
	
	// Intelligence Briefing Actions
	startBriefingGeneration: () => {
		smartAssistant.update((state: SmartAssistantState) => ({
			...state,
			briefing_in_progress: true,
			show_briefing_interface: true
		}));
	},
	
	updateBriefing: (briefing: IntelligenceBriefing) => {
		smartAssistant.update((state: SmartAssistantState) => ({
			...state,
			latest_briefing: briefing,
			briefing_in_progress: false,
			last_briefing_generated: new Date().toISOString()
		}));
	},
	
	// UI State Actions
	setActiveCommand: (command: string | null) => {
		smartAssistant.update((state: SmartAssistantState) => ({
			...state,
			active_command: command
		}));
	},
	
	toggleInterface: (interfaceType: 'job' | 'inbox' | 'briefing', show?: boolean) => {
		smartAssistant.update((state: SmartAssistantState) => {
			const newState = { ...state };
			
			switch (interfaceType) {
				case 'job':
					newState.show_job_interface = show ?? !state.show_job_interface;
					break;
				case 'inbox':
					newState.show_inbox_interface = show ?? !state.show_inbox_interface;
					break;
				case 'briefing':
					newState.show_briefing_interface = show ?? !state.show_briefing_interface;
					break;
			}
			
			return newState;
		});
	},
	
	// Reset Actions
	resetJobSearch: () => {
		smartAssistant.update((state: SmartAssistantState) => ({
			...state,
			jobs: [],
			job_search_in_progress: false,
			job_search_params: {},
			show_job_interface: false
		}));
	},
	
	resetAll: () => {
		smartAssistant.set(defaultState);
	}
};

// ============================================================================
// Command Detection Utilities
// ============================================================================

export function detectSmartAssistantCommand(message: string): {
	type: keyof typeof SMART_ASSISTANT_COMMANDS | null;
	confidence: number;
	extractedParams?: Record<string, any>;
} {
	const messageLower = message.toLowerCase();
	
	// Check each command type
	for (const commandType in SMART_ASSISTANT_COMMANDS) {
		const triggers = SMART_ASSISTANT_COMMANDS[commandType as keyof typeof SMART_ASSISTANT_COMMANDS];
		for (let i = 0; i < triggers.length; i++) {
			const trigger = triggers[i];
			if (messageLower.indexOf(trigger) !== -1) {
				return {
					type: commandType as keyof typeof SMART_ASSISTANT_COMMANDS,
					confidence: trigger.length / message.length, // Simple confidence score
					extractedParams: extractParametersFromMessage(message, commandType)
				};
			}
		}
	}
	
	return { type: null, confidence: 0 };
}

function extractParametersFromMessage(message: string, commandType: string): Record<string, any> {
	const params: Record<string, any> = {};
	const messageLower = message.toLowerCase();
	
	// Basic parameter extraction (can be enhanced with Gemini AI)
	if (commandType === 'JOB_SEARCH') {
		// Extract location
		const locationMatch = messageLower.match(/(?:in|at|near)\s+([a-z\s,]+?)(?:\s|$)/);
		if (locationMatch) {
			params.location = locationMatch[1].trim();
		}
		
		// Extract job titles/keywords
		const jobKeywords = ['developer', 'engineer', 'manager', 'analyst', 'designer'];
		params.keywords = jobKeywords.filter(keyword => messageLower.indexOf(keyword) !== -1);
		
		// Extract experience level
		if (messageLower.indexOf('senior') !== -1) params.experience_level = 'senior';
		if (messageLower.indexOf('junior') !== -1) params.experience_level = 'junior';
		if (messageLower.indexOf('entry') !== -1) params.experience_level = 'entry';
	}
	
	return params;
}

// ============================================================================
// API Integration Utilities
// ============================================================================

export function callSmartAssistantAPI(
	endpoint: string, 
	payload: any,
	config: SmartAssistantConfig
): any {
	return fetch(`${config.microservice_url}/api/v1${endpoint}`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
		},
		body: JSON.stringify(payload)
	}).then(response => {
		if (!response.ok) {
			throw new Error(`API call failed: ${response.status} ${response.statusText}`);
		}
		return response.json();
	}).catch(error => {
		console.error('Smart Assistant API call failed:', error);
		throw error;
	});
}
