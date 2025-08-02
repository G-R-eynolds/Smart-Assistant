<!--
	SmartAssistantSidebar.svelte
	
	Smart Assistant Control Sidebar
	
	Features:
	- Floating control panel for Quick Smart Assistant interface access
	- Toggle buttons for all Smart Assistant components
	- Status indicators for active components
	- Minimizable sidebar design
	- Real-time activity indicators
-->

<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { slide, fade } from 'svelte/transition';
	
	// Store imports
	import { 
		smartAssistant, 
		smartAssistantActions,
		isSmartAssistantEnabled
	} from '$lib/stores/smartAssistant';
	
	// Icon imports
	import { 
		Search, 
		Mail, 
		FileText, 
		ChevronLeft, 
		ChevronRight,
		Activity,
		Settings,
		Minimize2,
		Maximize2
	} from 'lucide-svelte';
	
	// Props
	export let isVisible: boolean = true;
	export let position: 'left' | 'right' = 'right';
	
	// Local state
	let isMinimized: boolean = false;
	let isCollapsed: boolean = false;
	
	// Event dispatcher
	const dispatch = createEventDispatcher<{
		toggleInterface: { interface: string; visible: boolean };
		settingsRequested: {};
	}>();
	
	// Reactive statements
	$: isJobActive = $smartAssistant.show_job_interface;
	$: isInboxActive = $smartAssistant.show_inbox_interface;
	$: isBriefingActive = $smartAssistant.show_briefing_interface;
	$: hasActiveInterface = isJobActive || isInboxActive || isBriefingActive;
	
	// Toggle functions
	function toggleJobInterface() {
		const newState = !isJobActive;
		smartAssistantActions.toggleInterface('job', newState);
		dispatch('toggleInterface', { interface: 'job', visible: newState });
	}
	
	function toggleInboxInterface() {
		const newState = !isInboxActive;
		smartAssistantActions.toggleInterface('inbox', newState);
		dispatch('toggleInterface', { interface: 'inbox', visible: newState });
	}
	
	function toggleBriefingInterface() {
		const newState = !isBriefingActive;
		smartAssistantActions.toggleInterface('briefing', newState);
		dispatch('toggleInterface', { interface: 'briefing', visible: newState });
	}
	
	function toggleMinimized() {
		isMinimized = !isMinimized;
	}
	
	function toggleCollapsed() {
		isCollapsed = !isCollapsed;
	}
	
	function openSettings() {
		dispatch('settingsRequested');
	}
</script>

{#if isVisible && $isSmartAssistantEnabled}
	<div 
		class="smart-assistant-sidebar {position}" 
		class:minimized={isMinimized}
		class:collapsed={isCollapsed}
		transition:slide={{ axis: 'x', duration: 300 }}
	>
		
		<!-- Header -->
		<div class="sidebar-header">
			{#if !isCollapsed}
				<div class="header-content" transition:fade={{ duration: 200 }}>
					<div class="header-title">
						<Activity class="w-4 h-4 text-blue-500" />
						<span>Smart Assistant</span>
						{#if hasActiveInterface}
							<div class="activity-indicator"></div>
						{/if}
					</div>
					
					<div class="header-controls">
						<button 
							class="control-btn"
							on:click={toggleMinimized}
							title={isMinimized ? 'Maximize' : 'Minimize'}
						>
							{#if isMinimized}
								<Maximize2 class="w-3 h-3" />
							{:else}
								<Minimize2 class="w-3 h-3" />
							{/if}
						</button>
					</div>
				</div>
			{/if}
			
			<button 
				class="collapse-btn"
				on:click={toggleCollapsed}
				title={isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
			>
				{#if isCollapsed}
					{#if position === 'right'}
						<ChevronLeft class="w-4 h-4" />
					{:else}
						<ChevronRight class="w-4 h-4" />
					{/if}
				{:else}
					{#if position === 'right'}
						<ChevronRight class="w-4 h-4" />
					{:else}
						<ChevronLeft class="w-4 h-4" />
					{/if}
				{/if}
			</button>
		</div>
		
		<!-- Interface Controls -->
		{#if !isCollapsed && !isMinimized}
			<div class="sidebar-content" transition:slide={{ duration: 300 }}>
				
				<!-- Job Discovery Control -->
				<div class="interface-control">
					<button 
						class="interface-btn"
						class:active={isJobActive}
						on:click={toggleJobInterface}
						title="Job Discovery Interface"
					>
						<div class="btn-icon">
							<Search class="w-4 h-4" />
							{#if isJobActive}
								<div class="active-dot"></div>
							{/if}
						</div>
						<div class="btn-content">
							<span class="btn-label">Job Search</span>
							<span class="btn-description">Find and analyze job opportunities</span>
						</div>
					</button>
				</div>
				
				<!-- Inbox Management Control -->
				<div class="interface-control">
					<button 
						class="interface-btn"
						class:active={isInboxActive}
						on:click={toggleInboxInterface}
						title="Inbox Management Interface"
					>
						<div class="btn-icon">
							<Mail class="w-4 h-4" />
							{#if isInboxActive}
								<div class="active-dot"></div>
							{/if}
						</div>
						<div class="btn-content">
							<span class="btn-label">Email Inbox</span>
							<span class="btn-description">Manage and categorize emails</span>
						</div>
					</button>
				</div>
				
				<!-- Intelligence Briefing Control -->
				<div class="interface-control">
					<button 
						class="interface-btn"
						class:active={isBriefingActive}
						on:click={toggleBriefingInterface}
						title="Intelligence Briefing Interface"
					>
						<div class="btn-icon">
							<FileText class="w-4 h-4" />
							{#if isBriefingActive}
								<div class="active-dot"></div>
							{/if}
						</div>
						<div class="btn-content">
							<span class="btn-label">Daily Briefing</span>
							<span class="btn-description">Intelligence and trend updates</span>
						</div>
					</button>
				</div>
				
				<!-- Divider -->
				<div class="sidebar-divider"></div>
				
				<!-- Settings Control -->
				<div class="interface-control">
					<button 
						class="interface-btn settings"
						on:click={openSettings}
						title="Smart Assistant Settings"
					>
						<div class="btn-icon">
							<Settings class="w-4 h-4" />
						</div>
						<div class="btn-content">
							<span class="btn-label">Settings</span>
							<span class="btn-description">Configure Smart Assistant</span>
						</div>
					</button>
				</div>
			</div>
		{:else if isCollapsed}
			<!-- Collapsed Mode - Icon Only -->
			<div class="collapsed-content" transition:fade={{ duration: 200 }}>
				<button 
					class="collapsed-btn"
					class:active={isJobActive}
					on:click={toggleJobInterface}
					title="Job Discovery Interface"
				>
					<Search class="w-4 h-4" />
					{#if isJobActive}
						<div class="active-dot"></div>
					{/if}
				</button>
				
				<button 
					class="collapsed-btn"
					class:active={isInboxActive}
					on:click={toggleInboxInterface}
					title="Inbox Management Interface"
				>
					<Mail class="w-4 h-4" />
					{#if isInboxActive}
						<div class="active-dot"></div>
					{/if}
				</button>
				
				<button 
					class="collapsed-btn"
					class:active={isBriefingActive}
					on:click={toggleBriefingInterface}
					title="Intelligence Briefing Interface"
				>
					<FileText class="w-4 h-4" />
					{#if isBriefingActive}
						<div class="active-dot"></div>
					{/if}
				</button>
				
				<div class="collapsed-divider"></div>
				
				<button 
					class="collapsed-btn settings"
					on:click={openSettings}
					title="Smart Assistant Settings"
				>
					<Settings class="w-4 h-4" />
				</button>
			</div>
		{/if}
	</div>
{/if}

<style>
	.smart-assistant-sidebar {
		position: fixed;
		top: 50%;
		transform: translateY(-50%);
		z-index: 1000;
		background: white;
		border-radius: 12px;
		box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
		border: 1px solid #e5e7eb;
		min-width: 280px;
		max-width: 320px;
		overflow: hidden;
		transition: all 0.3s ease;
	}
	
	.smart-assistant-sidebar.right {
		right: 1rem;
	}
	
	.smart-assistant-sidebar.left {
		left: 1rem;
	}
	
	.smart-assistant-sidebar.minimized {
		max-height: 60px;
	}
	
	.smart-assistant-sidebar.collapsed {
		min-width: 60px;
		max-width: 60px;
	}
	
	/* Header */
	.sidebar-header {
		background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
		color: white;
		padding: 1rem;
		display: flex;
		align-items: center;
		justify-content: space-between;
	}
	
	.header-content {
		display: flex;
		align-items: center;
		justify-content: space-between;
		width: 100%;
		margin-right: 0.5rem;
	}
	
	.header-title {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-weight: 600;
		font-size: 0.875rem;
	}
	
	.activity-indicator {
		width: 8px;
		height: 8px;
		background: #10b981;
		border-radius: 50%;
		animation: pulse 2s infinite;
	}
	
	@keyframes pulse {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.5; }
	}
	
	.header-controls {
		display: flex;
		gap: 0.25rem;
	}
	
	.control-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 1.5rem;
		height: 1.5rem;
		background: rgba(255, 255, 255, 0.2);
		border: none;
		border-radius: 4px;
		color: white;
		cursor: pointer;
		transition: background-color 0.2s;
	}
	
	.control-btn:hover {
		background: rgba(255, 255, 255, 0.3);
	}
	
	.collapse-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 2rem;
		height: 2rem;
		background: rgba(255, 255, 255, 0.2);
		border: none;
		border-radius: 6px;
		color: white;
		cursor: pointer;
		transition: background-color 0.2s;
	}
	
	.collapse-btn:hover {
		background: rgba(255, 255, 255, 0.3);
	}
	
	/* Content */
	.sidebar-content {
		padding: 1rem;
		max-height: 400px;
		overflow-y: auto;
	}
	
	.interface-control {
		margin-bottom: 0.5rem;
	}
	
	.interface-btn {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		width: 100%;
		padding: 0.75rem;
		background: #f9fafb;
		border: 1px solid #e5e7eb;
		border-radius: 8px;
		cursor: pointer;
		transition: all 0.2s;
		text-align: left;
	}
	
	.interface-btn:hover {
		background: #f3f4f6;
		border-color: #d1d5db;
	}
	
	.interface-btn.active {
		background: #e0e7ff;
		border-color: #6366f1;
		color: #1e40af;
	}
	
	.interface-btn.settings {
		background: #f8fafc;
	}
	
	.interface-btn.settings:hover {
		background: #f1f5f9;
	}
	
	.btn-icon {
		position: relative;
		display: flex;
		align-items: center;
		justify-content: center;
		width: 2rem;
		height: 2rem;
		background: white;
		border-radius: 6px;
		border: 1px solid #e5e7eb;
		color: #6b7280;
		flex-shrink: 0;
	}
	
	.interface-btn.active .btn-icon {
		background: #6366f1;
		color: white;
		border-color: #6366f1;
	}
	
	.active-dot {
		position: absolute;
		top: -2px;
		right: -2px;
		width: 8px;
		height: 8px;
		background: #10b981;
		border: 2px solid white;
		border-radius: 50%;
	}
	
	.btn-content {
		flex: 1;
		min-width: 0;
	}
	
	.btn-label {
		display: block;
		font-weight: 500;
		font-size: 0.875rem;
		color: #111827;
		margin-bottom: 0.125rem;
	}
	
	.interface-btn.active .btn-label {
		color: #1e40af;
	}
	
	.btn-description {
		display: block;
		font-size: 0.75rem;
		color: #6b7280;
		line-height: 1.3;
	}
	
	.interface-btn.active .btn-description {
		color: #3730a3;
	}
	
	.sidebar-divider {
		height: 1px;
		background: #e5e7eb;
		margin: 0.75rem 0;
	}
	
	/* Collapsed Mode */
	.collapsed-content {
		display: flex;
		flex-direction: column;
		padding: 0.5rem;
		gap: 0.5rem;
	}
	
	.collapsed-btn {
		position: relative;
		display: flex;
		align-items: center;
		justify-content: center;
		width: 2.5rem;
		height: 2.5rem;
		background: #f9fafb;
		border: 1px solid #e5e7eb;
		border-radius: 8px;
		cursor: pointer;
		transition: all 0.2s;
		color: #6b7280;
	}
	
	.collapsed-btn:hover {
		background: #f3f4f6;
		border-color: #d1d5db;
	}
	
	.collapsed-btn.active {
		background: #e0e7ff;
		border-color: #6366f1;
		color: #1e40af;
	}
	
	.collapsed-btn.settings {
		background: #f8fafc;
	}
	
	.collapsed-btn.settings:hover {
		background: #f1f5f9;
	}
	
	.collapsed-divider {
		height: 1px;
		background: #e5e7eb;
		margin: 0.25rem 0;
	}
	
	/* Responsive Design */
	@media (max-width: 768px) {
		.smart-assistant-sidebar {
			position: fixed;
			bottom: 1rem;
			top: auto;
			left: 1rem;
			right: 1rem;
			transform: none;
			min-width: auto;
			max-width: none;
		}
		
		.smart-assistant-sidebar.collapsed {
			min-width: auto;
			max-width: none;
		}
		
		.collapsed-content {
			flex-direction: row;
			justify-content: center;
		}
		
		.sidebar-content {
			max-height: 300px;
		}
	}
	
	/* Scrollbar Styling */
	.sidebar-content::-webkit-scrollbar {
		width: 4px;
	}
	
	.sidebar-content::-webkit-scrollbar-track {
		background: #f1f1f1;
		border-radius: 2px;
	}
	
	.sidebar-content::-webkit-scrollbar-thumb {
		background: #c1c1c1;
		border-radius: 2px;
	}
	
	.sidebar-content::-webkit-scrollbar-thumb:hover {
		background: #a1a1a1;
	}
</style>
