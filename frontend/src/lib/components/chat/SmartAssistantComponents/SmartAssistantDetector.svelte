<!--
	SmartAssistantDetector.svelte
	
	Smart Assistant Command Detection Component
	
	This component analyzes user messages for Smart Assistant commands and
	triggers appropriate interfaces when detected. It integrates seamlessly
	with the existing Open WebUI chat system.
	
	Features:
	- Real-time command detection from user messages
	- Natural language processing for job search parameters
	- Smart trigger system with confidence scoring
	- Integration with existing chat message flow
	- Visual indicators for Smart Assistant activation
-->

<script lang="ts">
	import { onMount, createEventDispatcher } from 'svelte';
	import { fade, slide } from 'svelte/transition';
	
	// Store imports
	import { 
		smartAssistant, 
		smartAssistantActions,
		detectSmartAssistantCommand,
		SMART_ASSISTANT_COMMANDS,
		type SmartAssistantJob,
		callSmartAssistantAPI
	} from '$lib/stores/smartAssistant';
	
	// Icon imports
	import { Brain, Zap, Search, Mail, FileText, AlertCircle } from 'lucide-svelte';
	
	// Props
	export let message: string = '';
	export let onCommandDetected: (command: string, params: any) => void = () => {};
	export let autoTrigger: boolean = true;
	export let showVisualIndicator: boolean = true;
	
	// Local state
	let detectedCommand: string | null = null;
	let commandConfidence: number = 0;
	let extractedParams: Record<string, any> = {};
	let isProcessing: boolean = false;
	let showCommandPreview: boolean = false;
	let commandPreviewTimeout: NodeJS.Timeout | null = null;
	
	// Event dispatcher
	const dispatch = createEventDispatcher<{
		commandDetected: { command: string; params: any; confidence: number };
		jobSearchTriggered: { params: any };
		inboxCheckTriggered: {};
		briefingTriggered: {};
	}>();
	
	// Reactive statements
	$: if (message) {
		detectCommand(message);
	}
	
	$: commandIcon = getCommandIcon(detectedCommand);
	$: commandDisplayName = getCommandDisplayName(detectedCommand);
	$: shouldShowPreview = showVisualIndicator && detectedCommand && commandConfidence > 0.3;
	
	// Command detection function
	function detectCommand(text: string) {
		if (!text || text.length < 3) {
			resetDetection();
			return;
		}
		
		const detection = detectSmartAssistantCommand(text);
		
		detectedCommand = detection.type;
		commandConfidence = detection.confidence;
		extractedParams = detection.extractedParams || {};
		
		// Show preview for high-confidence commands
		if (detectedCommand && commandConfidence > 0.5) {
			showCommandPreview = true;
			
			// Clear existing timeout
			if (commandPreviewTimeout) {
				clearTimeout(commandPreviewTimeout);
			}
			
			// Auto-hide preview after 3 seconds
			commandPreviewTimeout = setTimeout(() => {
				showCommandPreview = false;
			}, 3000);
			
			// Dispatch event
			dispatch('commandDetected', {
				command: detectedCommand,
				params: extractedParams,
				confidence: commandConfidence
			});
			
			// Auto-trigger if enabled and confidence is high
			if (autoTrigger && commandConfidence > 0.7) {
				setTimeout(() => {
					triggerCommand(detectedCommand, extractedParams);
				}, 500);
			}
		}
	}
	
	// Reset detection state
	function resetDetection() {
		detectedCommand = null;
		commandConfidence = 0;
		extractedParams = {};
		showCommandPreview = false;
		
		if (commandPreviewTimeout) {
			clearTimeout(commandPreviewTimeout);
			commandPreviewTimeout = null;
		}
	}
	
	// Trigger detected command
	async function triggerCommand(command: string | null, params: Record<string, any>) {
		if (!command) return;
		
		isProcessing = true;
		
		try {
			switch (command) {
				case 'JOB_SEARCH':
					await handleJobSearch(params);
					break;
				case 'EMAIL_CHECK':
					await handleEmailCheck();
					break;
				case 'BRIEFING':
					await handleBriefing();
					break;
				default:
					console.log('Unknown command:', command);
			}
		} catch (error) {
			console.error('Command execution failed:', error);
		} finally {
			isProcessing = false;
		}
		
		// Notify parent component
		onCommandDetected(command, params);
	}
	
	// Command handlers
	async function handleJobSearch(params: Record<string, any>) {
		dispatch('jobSearchTriggered', { params });
		
		// Enhanced parameter extraction using Smart Assistant microservice
		try {
			const enhancedParams = await callSmartAssistantAPI('/extract-job-parameters', {
				query: message,
				context: {
					user_preferences: {},
					previous_searches: []
				}
			}, $smartAssistant.config);
			
			// Merge basic and enhanced parameters
			const finalParams = { ...params, ...enhancedParams };
			
			smartAssistantActions.startJobSearch(finalParams);
			
		} catch (error) {
			console.error('Enhanced parameter extraction failed:', error);
			// Fall back to basic parameters
			smartAssistantActions.startJobSearch(params);
		}
	}
	
	async function handleEmailCheck() {
		dispatch('inboxCheckTriggered', {});
		smartAssistantActions.startInboxProcessing();
		
		try {
			const inboxResult = await callSmartAssistantAPI('/process-inbox', {
				email_config: {
					// This would come from user settings
					provider: 'gmail',
					check_unread: true,
					categorize: true
				}
			}, $smartAssistant.config);
			
			smartAssistantActions.updateInboxResult(inboxResult);
			
		} catch (error) {
			console.error('Inbox processing failed:', error);
		}
	}
	
	async function handleBriefing() {
		dispatch('briefingTriggered', {});
		smartAssistantActions.startBriefingGeneration();
		
		try {
			const briefing = await callSmartAssistantAPI('/generate-briefing', {
				topics: ['technology', 'career', 'market'],
				personalization: {
					user_interests: [],
					career_focus: 'software_development'
				}
			}, $smartAssistant.config);
			
			smartAssistantActions.updateBriefing(briefing);
			
		} catch (error) {
			console.error('Briefing generation failed:', error);
		}
	}
	
	// Helper functions
	function getCommandIcon(command: string | null) {
		switch (command) {
			case 'JOB_SEARCH':
				return Search;
			case 'EMAIL_CHECK':
				return Mail;
			case 'BRIEFING':
				return FileText;
			default:
				return Brain;
		}
	}
	
	function getCommandDisplayName(command: string | null): string {
		switch (command) {
			case 'JOB_SEARCH':
				return 'Job Discovery';
			case 'EMAIL_CHECK':
				return 'Inbox Processing';
			case 'BRIEFING':
				return 'Intelligence Briefing';
			default:
				return 'Smart Assistant';
		}
	}
	
	function getConfidenceColor(confidence: number): string {
		if (confidence >= 0.8) return 'text-green-600 bg-green-50 border-green-200';
		if (confidence >= 0.6) return 'text-blue-600 bg-blue-50 border-blue-200';
		if (confidence >= 0.4) return 'text-yellow-600 bg-yellow-50 border-yellow-200';
		return 'text-red-600 bg-red-50 border-red-200';
	}
	
	// Manual trigger function (for testing or explicit calls)
	export function manualTrigger(command: string, params: Record<string, any> = {}) {
		triggerCommand(command, params);
	}
	
	// Get available commands for suggestions
	export function getAvailableCommands() {
		return Object.keys(SMART_ASSISTANT_COMMANDS);
	}
	
	// Lifecycle
	onMount(() => {
		return () => {
			if (commandPreviewTimeout) {
				clearTimeout(commandPreviewTimeout);
			}
		};
	});
</script>

<!-- Command Detection Indicator -->
{#if shouldShowPreview && showCommandPreview}
	<div 
		class="smart-assistant-indicator"
		transition:slide={{ duration: 200 }}
	>
		<div class="indicator-content">
			<div class="indicator-icon">
				<svelte:component this={commandIcon} class="w-4 h-4" />
			</div>
			
			<div class="indicator-text">
				<span class="command-name">{commandDisplayName}</span>
				<span class="command-description">detected</span>
			</div>
			
			<div class="confidence-badge {getConfidenceColor(commandConfidence)}">
				{Math.round(commandConfidence * 100)}%
			</div>
			
			{#if autoTrigger && commandConfidence > 0.7}
				<div class="auto-trigger-indicator">
					<Zap class="w-3 h-3" />
					<span>Auto-triggering...</span>
				</div>
			{:else if commandConfidence > 0.5}
				<button 
					class="trigger-button"
					on:click={() => triggerCommand(detectedCommand, extractedParams)}
					disabled={isProcessing}
				>
					{#if isProcessing}
						<div class="spinner"></div>
					{:else}
						<Zap class="w-3 h-3" />
					{/if}
					Trigger
				</button>
			{/if}
		</div>
		
		<!-- Extracted Parameters Preview -->
		{#if Object.keys(extractedParams).length > 0}
			<div class="parameters-preview">
				<div class="parameters-title">Detected Parameters:</div>
				<div class="parameters-list">
					{#each Object.entries(extractedParams) as [key, value]}
						<span class="parameter-item">
							<strong>{key}:</strong> {Array.isArray(value) ? value.join(', ') : value}
						</span>
					{/each}
				</div>
			</div>
		{/if}
	</div>
{/if}

<!-- Processing Indicator -->
{#if isProcessing}
	<div class="processing-indicator" transition:fade={{ duration: 200 }}>
		<div class="processing-content">
			<div class="spinner-large"></div>
			<span>Processing {commandDisplayName}...</span>
		</div>
	</div>
{/if}

<style>
	.smart-assistant-indicator {
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
		border-radius: 12px;
		padding: 1rem;
		margin: 0.5rem 0;
		box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
		border: 1px solid rgba(255, 255, 255, 0.2);
	}
	
	.indicator-content {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-bottom: 0.5rem;
	}
	
	.indicator-icon {
		background: rgba(255, 255, 255, 0.2);
		border-radius: 50%;
		padding: 0.5rem;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	
	.indicator-text {
		flex: 1;
		display: flex;
		flex-direction: column;
	}
	
	.command-name {
		font-weight: 600;
		font-size: 0.875rem;
	}
	
	.command-description {
		font-size: 0.75rem;
		opacity: 0.9;
	}
	
	.confidence-badge {
		padding: 0.25rem 0.5rem;
		border-radius: 12px;
		font-size: 0.75rem;
		font-weight: 600;
		border: 1px solid;
		background: white;
	}
	
	.auto-trigger-indicator {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		font-size: 0.75rem;
		opacity: 0.9;
		animation: pulse 1.5s ease-in-out infinite;
	}
	
	.trigger-button {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		background: rgba(255, 255, 255, 0.2);
		border: 1px solid rgba(255, 255, 255, 0.3);
		border-radius: 6px;
		color: white;
		padding: 0.5rem 0.75rem;
		font-size: 0.75rem;
		cursor: pointer;
		transition: all 0.2s;
	}
	
	.trigger-button:hover:not(:disabled) {
		background: rgba(255, 255, 255, 0.3);
		border-color: rgba(255, 255, 255, 0.5);
	}
	
	.trigger-button:disabled {
		opacity: 0.7;
		cursor: not-allowed;
	}
	
	.parameters-preview {
		border-top: 1px solid rgba(255, 255, 255, 0.2);
		padding-top: 0.75rem;
		margin-top: 0.75rem;
	}
	
	.parameters-title {
		font-size: 0.75rem;
		opacity: 0.9;
		margin-bottom: 0.5rem;
	}
	
	.parameters-list {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}
	
	.parameter-item {
		background: rgba(255, 255, 255, 0.15);
		border-radius: 12px;
		padding: 0.25rem 0.5rem;
		font-size: 0.75rem;
	}
	
	.processing-indicator {
		background: rgba(59, 130, 246, 0.1);
		border: 1px solid rgba(59, 130, 246, 0.2);
		border-radius: 8px;
		padding: 1rem;
		margin: 0.5rem 0;
	}
	
	.processing-content {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.75rem;
		color: #3b82f6;
		font-size: 0.875rem;
	}
	
	.spinner {
		width: 12px;
		height: 12px;
		border: 2px solid rgba(255, 255, 255, 0.3);
		border-top: 2px solid white;
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}
	
	.spinner-large {
		width: 20px;
		height: 20px;
		border: 2px solid rgba(59, 130, 246, 0.3);
		border-top: 2px solid #3b82f6;
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}
	
	@keyframes spin {
		0% { transform: rotate(0deg); }
		100% { transform: rotate(360deg); }
	}
	
	@keyframes pulse {
		0%, 100% { opacity: 0.9; }
		50% { opacity: 0.6; }
	}
	
	/* Responsive Design */
	@media (max-width: 768px) {
		.smart-assistant-indicator {
			padding: 0.75rem;
		}
		
		.indicator-content {
			gap: 0.5rem;
		}
		
		.parameters-list {
			flex-direction: column;
			gap: 0.25rem;
		}
		
		.parameter-item {
			align-self: flex-start;
		}
	}
</style>
