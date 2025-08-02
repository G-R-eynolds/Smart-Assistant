<!--
	InboxInterface.svelte
	
	Smart Assistant Inbox Management Interface Component
	
	Features:
	- Email categorization and priority display
	- Unread email count and important email highlights
	- Email preview with action buttons (reply, archive, delete)
	- Email search and filtering capabilities
	- Real-time inbox processing with loading states
	- Integration with Smart Assistant email processing pipeline
-->

<script lang="ts">
	import { onMount, createEventDispatcher } from 'svelte';
	import { slide, fade } from 'svelte/transition';
	import { toast } from 'svelte-sonner';
	
	// Store imports
	import { 
		smartAssistant, 
		smartAssistantActions,
		unreadEmailCount,
		type EmailSummary,
		type InboxProcessingResult
	} from '$lib/stores/smartAssistant';
	
	// Icon imports
	import { 
		Mail, 
		MailOpen, 
		Search, 
		Filter, 
		RefreshCw, 
		AlertCircle,
		Archive,
		Trash2,
		Reply,
		Star,
		Clock,
		User,
		Tag,
		ExternalLink
	} from 'lucide-svelte';
	
	// Props
	export let isVisible: boolean = false;
	export let onClose: () => void = () => {};
	
	// Local state
	let searchQuery: string = '';
	let selectedCategory: string = 'all';
	let selectedPriority: string = 'all';
	let showFilters: boolean = false;
	let selectedEmails: Set<string> = new Set();
	let emailsContainer: HTMLElement;
	
	// Event dispatcher
	const dispatch = createEventDispatcher<{
		emailAction: { action: string; emailId: string };
		bulkAction: { action: string; emailIds: string[] };
	}>();
	
	// Reactive statements
	$: inboxResult = $smartAssistant.inbox_result;
	$: isProcessing = $smartAssistant.inbox_processing;
	$: filteredEmails = filterEmails(inboxResult?.important_emails || [], searchQuery, selectedCategory, selectedPriority);
	$: emailCategories = inboxResult?.categories || {};
	$: unreadCount = $unreadEmailCount;
	
	// Filter emails based on search and filters
	function filterEmails(emails: EmailSummary[], query: string, category: string, priority: string): EmailSummary[] {
		return emails.filter(email => {
			// Search filter
			if (query && !email.subject.toLowerCase().includes(query.toLowerCase()) && 
				!email.sender.toLowerCase().includes(query.toLowerCase())) {
				return false;
			}
			
			// Category filter
			if (category !== 'all' && email.category !== category) {
				return false;
			}
			
			// Priority filter
			if (priority !== 'all' && email.urgency !== priority) {
				return false;
			}
			
			return true;
		});
	}
	
	// Inbox processing function
	async function processInbox() {
		smartAssistantActions.startInboxProcessing();
		
		try {
			// Call the inbox processing pipeline
			const response = await fetch('/api/v1/smart_assistant/inbox/process', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					message: 'Process my inbox and show important emails',
					user: { id: 'user' }
				})
			});
			
			if (!response.ok) {
				throw new Error(`Inbox processing failed: ${response.status}`);
			}
			
			const result = await response.json();
			
			if (result.data) {
				smartAssistantActions.updateInboxResult(result.data);
				toast.success(`Processed inbox: ${result.data.unread_count} unread emails`);
			} else {
				toast.warning('No inbox data received');
			}
			
		} catch (error) {
			console.error('Inbox processing failed:', error);
			toast.error('Failed to process inbox. Please try again.');
		}
	}
	
	// Email action handlers
	function handleEmailAction(action: string, emailId: string) {
		dispatch('emailAction', { action, emailId });
		
		switch (action) {
			case 'reply':
				toast.info('Opening reply composer...');
				break;
			case 'archive':
				toast.success('Email archived');
				break;
			case 'delete':
				toast.success('Email deleted');
				break;
			case 'star':
				toast.success('Email starred');
				break;
		}
	}
	
	function handleBulkAction(action: string) {
		const emailIds = Array.from(selectedEmails);
		if (emailIds.length === 0) {
			toast.warning('No emails selected');
			return;
		}
		
		dispatch('bulkAction', { action, emailIds });
		
		switch (action) {
			case 'archive':
				toast.success(`${emailIds.length} emails archived`);
				break;
			case 'delete':
				toast.success(`${emailIds.length} emails deleted`);
				break;
			case 'mark_read':
				toast.success(`${emailIds.length} emails marked as read`);
				break;
		}
		
		selectedEmails.clear();
		selectedEmails = selectedEmails;
	}
	
	// Email selection handlers
	function toggleEmailSelection(emailId: string) {
		if (selectedEmails.has(emailId)) {
			selectedEmails.delete(emailId);
		} else {
			selectedEmails.add(emailId);
		}
		selectedEmails = selectedEmails;
	}
	
	function selectAllEmails() {
		if (selectedEmails.size === filteredEmails.length) {
			selectedEmails.clear();
		} else {
			filteredEmails.forEach(email => selectedEmails.add(email.id));
		}
		selectedEmails = selectedEmails;
	}
	
	// Helper functions
	function getPriorityColor(urgency: string): string {
		switch (urgency) {
			case 'high': return 'text-red-600 bg-red-50 border-red-200';
			case 'medium': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
			case 'low': return 'text-green-600 bg-green-50 border-green-200';
			default: return 'text-gray-600 bg-gray-50 border-gray-200';
		}
	}
	
	function getCategoryIcon(category: string) {
		switch (category.toLowerCase()) {
			case 'work': return User;
			case 'personal': return Mail;
			case 'promotions': return Tag;
			case 'updates': return RefreshCw;
			default: return Mail;
		}
	}
	
	function getTimeAgo(dateString: string): string {
		const now = new Date();
		const past = new Date(dateString);
		const diffMs = now.getTime() - past.getTime();
		const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
		const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
		
		if (diffHours < 24) return `${diffHours}h ago`;
		return `${diffDays}d ago`;
	}
	
	// Lifecycle
	onMount(() => {
		// Auto-process inbox when component becomes visible
		if (isVisible && !inboxResult) {
			processInbox();
		}
	});
</script>

{#if isVisible}
	<div class="smart-assistant-inbox-interface" transition:slide={{ duration: 300 }}>
		
		<!-- Header Section -->
		<div class="inbox-interface-header">
			<div class="header-content">
				<div class="header-title">
					<Mail class="w-5 h-5 text-blue-500" />
					<h2>Smart Inbox Management</h2>
					{#if unreadCount > 0}
						<span class="unread-badge">{unreadCount}</span>
					{/if}
				</div>
				<button 
					class="close-button"
					on:click={onClose}
					title="Close Inbox Interface"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>
			
			<!-- Inbox Stats -->
			{#if inboxResult}
				<div class="inbox-stats">
					<div class="stat-item">
						<span class="stat-number">{inboxResult.total_emails}</span>
						<span class="stat-label">Total</span>
					</div>
					<div class="stat-item">
						<span class="stat-number">{inboxResult.unread_count}</span>
						<span class="stat-label">Unread</span>
					</div>
					<div class="stat-item">
						<span class="stat-number">{filteredEmails.length}</span>
						<span class="stat-label">Important</span>
					</div>
					<div class="stat-item">
						<span class="stat-number">{inboxResult.action_items?.length || 0}</span>
						<span class="stat-label">Actions</span>
					</div>
				</div>
			{/if}
		</div>
		
		<!-- Controls Section -->
		<div class="inbox-controls">
			<div class="primary-controls">
				<button
					class="process-button"
					on:click={processInbox}
					disabled={isProcessing}
				>
					{#if isProcessing}
						<RefreshCw class="w-4 h-4 animate-spin" />
					{:else}
						<RefreshCw class="w-4 h-4" />
					{/if}
					{isProcessing ? 'Processing...' : 'Refresh Inbox'}
				</button>
				
				<!-- Bulk Actions -->
				{#if selectedEmails.size > 0}
					<div class="bulk-actions">
						<span class="selected-count">{selectedEmails.size} selected</span>
						<button class="bulk-action-btn" on:click={() => handleBulkAction('archive')}>
							<Archive class="w-4 h-4" />
							Archive
						</button>
						<button class="bulk-action-btn" on:click={() => handleBulkAction('delete')}>
							<Trash2 class="w-4 h-4" />
							Delete
						</button>
						<button class="bulk-action-btn" on:click={() => handleBulkAction('mark_read')}>
							<MailOpen class="w-4 h-4" />
							Mark Read
						</button>
					</div>
				{/if}
			</div>
			
			<!-- Search and Filters -->
			<div class="search-section">
				<div class="search-input-container">
					<Search class="search-icon" />
					<input
						type="text"
						bind:value={searchQuery}
						placeholder="Search emails by subject or sender..."
						class="search-input"
					/>
					<button
						class="filters-toggle"
						on:click={() => showFilters = !showFilters}
					>
						<Filter class="w-4 h-4" />
						Filters
					</button>
				</div>
				
				{#if showFilters}
					<div class="filters-panel" transition:slide={{ duration: 200 }}>
						<div class="filter-group">
							<label for="category-select">Category</label>
							<select id="category-select" bind:value={selectedCategory}>
								<option value="all">All Categories</option>
								{#each Object.keys(emailCategories) as category}
									<option value={category}>{category} ({emailCategories[category]})</option>
								{/each}
							</select>
						</div>
						
						<div class="filter-group">
							<label for="priority-select">Priority</label>
							<select id="priority-select" bind:value={selectedPriority}>
								<option value="all">All Priorities</option>
								<option value="high">High Priority</option>
								<option value="medium">Medium Priority</option>
								<option value="low">Low Priority</option>
							</select>
						</div>
					</div>
				{/if}
			</div>
		</div>
		
		<!-- Loading State -->
		{#if isProcessing}
			<div class="loading-section">
				<div class="loading-spinner">
					<RefreshCw class="w-8 h-8 animate-spin text-blue-500" />
				</div>
				<p class="loading-text">Processing your inbox...</p>
			</div>
		{/if}
		
		<!-- Email List -->
		{#if filteredEmails.length > 0}
			<div class="emails-container" bind:this={emailsContainer}>
				<div class="emails-header">
					<div class="select-all-container">
						<input
							type="checkbox"
							checked={selectedEmails.size === filteredEmails.length && filteredEmails.length > 0}
							on:change={selectAllEmails}
						/>
						<span>Select All ({filteredEmails.length})</span>
					</div>
				</div>
				
				<div class="emails-list">
					{#each filteredEmails as email (email.id)}
						<div class="email-item" class:selected={selectedEmails.has(email.id)}>
							<div class="email-checkbox">
								<input
									type="checkbox"
									checked={selectedEmails.has(email.id)}
									on:change={() => toggleEmailSelection(email.id)}
								/>
							</div>
							
							<div class="email-content">
								<div class="email-header">
									<div class="email-sender">
										<User class="w-4 h-4" />
										{email.sender}
									</div>
									<div class="email-meta">
										<span class="email-time">
											<Clock class="w-3 h-3" />
											{getTimeAgo(email.received_at)}
										</span>
										<span class="priority-badge {getPriorityColor(email.urgency)}">
											{email.urgency}
										</span>
									</div>
								</div>
								
								<div class="email-subject">{email.subject}</div>
								
								{#if email.preview}
									<div class="email-preview">{email.preview}</div>
								{/if}
								
								<div class="email-footer">
									<div class="email-category">
										<svelte:component this={getCategoryIcon(email.category)} class="w-3 h-3" />
										{email.category}
									</div>
									
									<div class="email-actions">
										<button 
											class="action-btn"
											on:click={() => handleEmailAction('reply', email.id)}
											title="Reply"
										>
											<Reply class="w-4 h-4" />
										</button>
										<button 
											class="action-btn"
											on:click={() => handleEmailAction('star', email.id)}
											title="Star"
										>
											<Star class="w-4 h-4" />
										</button>
										<button 
											class="action-btn"
											on:click={() => handleEmailAction('archive', email.id)}
											title="Archive"
										>
											<Archive class="w-4 h-4" />
										</button>
										<button 
											class="action-btn delete"
											on:click={() => handleEmailAction('delete', email.id)}
											title="Delete"
										>
											<Trash2 class="w-4 h-4" />
										</button>
									</div>
								</div>
							</div>
						</div>
					{/each}
				</div>
			</div>
		{:else if !isProcessing && inboxResult}
			<div class="empty-state">
				<Mail class="w-16 h-16 text-gray-400 mb-4" />
				<h3>No emails match your criteria</h3>
				<p>Try adjusting your search or filter settings.</p>
			</div>
		{:else if !isProcessing}
			<div class="empty-state">
				<Mail class="w-16 h-16 text-gray-400 mb-4" />
				<h3>Ready to process your inbox</h3>
				<p>Click "Refresh Inbox" to analyze your emails with Smart Assistant.</p>
			</div>
		{/if}
		
		<!-- Action Items -->
		{#if inboxResult?.action_items && inboxResult.action_items.length > 0}
			<div class="action-items-section">
				<h3>
					<AlertCircle class="w-4 h-4" />
					Action Items ({inboxResult.action_items.length})
				</h3>
				<div class="action-items-list">
					{#each inboxResult.action_items as item}
						<div class="action-item {item.priority}">
							<div class="action-description">{item.description}</div>
							<div class="action-due">Due: {new Date(item.due_date).toLocaleDateString()}</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}
	</div>
{/if}

<style>
	.smart-assistant-inbox-interface {
		background: white;
		border-radius: 12px;
		box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
		margin: 1rem 0;
		overflow: hidden;
		border: 1px solid #e5e7eb;
	}
	
	/* Header Styles */
	.inbox-interface-header {
		background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
		color: white;
		padding: 1.5rem;
	}
	
	.header-content {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
	}
	
	.header-title {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}
	
	.header-title h2 {
		font-size: 1.5rem;
		font-weight: 600;
		margin: 0;
	}
	
	.unread-badge {
		background: rgba(255, 255, 255, 0.2);
		color: white;
		padding: 0.25rem 0.5rem;
		border-radius: 12px;
		font-size: 0.75rem;
		font-weight: 600;
	}
	
	.close-button {
		background: rgba(255, 255, 255, 0.2);
		border: none;
		border-radius: 6px;
		color: white;
		cursor: pointer;
		padding: 0.5rem;
		transition: background-color 0.2s;
	}
	
	.close-button:hover {
		background: rgba(255, 255, 255, 0.3);
	}
	
	.inbox-stats {
		display: flex;
		gap: 2rem;
	}
	
	.stat-item {
		text-align: center;
	}
	
	.stat-number {
		display: block;
		font-size: 1.5rem;
		font-weight: 700;
	}
	
	.stat-label {
		font-size: 0.875rem;
		opacity: 0.9;
	}
	
	/* Controls Styles */
	.inbox-controls {
		padding: 1.5rem;
		background: #f9fafb;
		border-bottom: 1px solid #e5e7eb;
	}
	
	.primary-controls {
		display: flex;
		align-items: center;
		gap: 1rem;
		margin-bottom: 1rem;
	}
	
	.process-button {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		background: #3b82f6;
		color: white;
		border: none;
		border-radius: 6px;
		padding: 0.75rem 1rem;
		font-weight: 500;
		cursor: pointer;
		transition: background-color 0.2s;
	}
	
	.process-button:hover:not(:disabled) {
		background: #2563eb;
	}
	
	.process-button:disabled {
		background: #9ca3af;
		cursor: not-allowed;
	}
	
	.bulk-actions {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 1rem;
		background: #dbeafe;
		border-radius: 6px;
	}
	
	.selected-count {
		font-size: 0.875rem;
		color: #1d4ed8;
		margin-right: 0.5rem;
	}
	
	.bulk-action-btn {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		background: white;
		border: 1px solid #d1d5db;
		border-radius: 4px;
		padding: 0.25rem 0.5rem;
		font-size: 0.75rem;
		cursor: pointer;
		transition: all 0.2s;
	}
	
	.bulk-action-btn:hover {
		background: #f3f4f6;
	}
	
	/* Search and Filter Styles */
	.search-input-container {
		display: flex;
		align-items: center;
		background: white;
		border: 2px solid #e5e7eb;
		border-radius: 8px;
		padding: 0.75rem;
		transition: border-color 0.2s;
	}
	
	.search-input-container:focus-within {
		border-color: #3b82f6;
	}
	
	.search-icon {
		width: 1.25rem;
		height: 1.25rem;
		color: #6b7280;
		margin-right: 0.75rem;
	}
	
	.search-input {
		flex: 1;
		border: none;
		outline: none;
		font-size: 1rem;
		background: transparent;
	}
	
	.filters-toggle {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		background: #f3f4f6;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		padding: 0.5rem 1rem;
		cursor: pointer;
		font-size: 0.875rem;
		transition: all 0.2s;
	}
	
	.filters-toggle:hover {
		background: #e5e7eb;
	}
	
	.filters-panel {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1rem;
		margin-top: 1rem;
		padding: 1rem;
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 8px;
	}
	
	.filter-group {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}
	
	.filter-group label {
		font-size: 0.875rem;
		font-weight: 500;
		color: #374151;
	}
	
	.filter-group select {
		padding: 0.5rem;
		border: 1px solid #d1d5db;
		border-radius: 4px;
		font-size: 0.875rem;
	}
	
	/* Loading Styles */
	.loading-section {
		padding: 3rem;
		text-align: center;
	}
	
	.loading-spinner {
		margin-bottom: 1rem;
	}
	
	.loading-text {
		font-size: 1.125rem;
		color: #374151;
	}
	
	/* Email List Styles */
	.emails-container {
		padding: 1.5rem;
	}
	
	.emails-header {
		margin-bottom: 1rem;
		padding-bottom: 0.5rem;
		border-bottom: 1px solid #e5e7eb;
	}
	
	.select-all-container {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.875rem;
		color: #6b7280;
	}
	
	.emails-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}
	
	.email-item {
		display: flex;
		gap: 1rem;
		padding: 1rem;
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 8px;
		transition: all 0.2s;
	}
	
	.email-item:hover {
		border-color: #3b82f6;
		box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
	}
	
	.email-item.selected {
		background: #f0f9ff;
		border-color: #3b82f6;
	}
	
	.email-checkbox {
		display: flex;
		align-items: flex-start;
		padding-top: 0.25rem;
	}
	
	.email-content {
		flex: 1;
	}
	
	.email-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 0.5rem;
	}
	
	.email-sender {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-weight: 600;
		color: #111827;
	}
	
	.email-meta {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}
	
	.email-time {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		font-size: 0.75rem;
		color: #6b7280;
	}
	
	.priority-badge {
		padding: 0.25rem 0.5rem;
		border-radius: 12px;
		font-size: 0.625rem;
		font-weight: 600;
		text-transform: uppercase;
		border: 1px solid;
	}
	
	.email-subject {
		font-size: 1rem;
		font-weight: 500;
		color: #111827;
		margin-bottom: 0.5rem;
	}
	
	.email-preview {
		font-size: 0.875rem;
		color: #6b7280;
		line-height: 1.4;
		margin-bottom: 0.75rem;
	}
	
	.email-footer {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}
	
	.email-category {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		font-size: 0.75rem;
		color: #6b7280;
	}
	
	.email-actions {
		display: flex;
		gap: 0.5rem;
	}
	
	.action-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 2rem;
		height: 2rem;
		background: #f3f4f6;
		border: 1px solid #d1d5db;
		border-radius: 4px;
		cursor: pointer;
		transition: all 0.2s;
		color: #6b7280;
	}
	
	.action-btn:hover {
		background: #e5e7eb;
		color: #374151;
	}
	
	.action-btn.delete:hover {
		background: #fee2e2;
		color: #dc2626;
		border-color: #fecaca;
	}
	
	/* Action Items */
	.action-items-section {
		padding: 1.5rem;
		background: #fffbeb;
		border-top: 1px solid #fbbf24;
	}
	
	.action-items-section h3 {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		color: #92400e;
		margin-bottom: 1rem;
	}
	
	.action-items-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}
	
	.action-item {
		padding: 0.75rem;
		background: white;
		border-radius: 6px;
		border-left: 4px solid #fbbf24;
	}
	
	.action-item.high {
		border-left-color: #dc2626;
	}
	
	.action-item.medium {
		border-left-color: #ea580c;
	}
	
	.action-item.low {
		border-left-color: #65a30d;
	}
	
	.action-description {
		font-weight: 500;
		color: #111827;
		margin-bottom: 0.25rem;
	}
	
	.action-due {
		font-size: 0.75rem;
		color: #6b7280;
	}
	
	/* Empty States */
	.empty-state {
		padding: 3rem;
		text-align: center;
		color: #6b7280;
	}
	
	.empty-state h3 {
		font-size: 1.25rem;
		color: #374151;
		margin-bottom: 0.5rem;
	}
	
	/* Responsive Design */
	@media (max-width: 768px) {
		.inbox-stats {
			gap: 1rem;
		}
		
		.filters-panel {
			grid-template-columns: 1fr;
		}
		
		.email-header {
			flex-direction: column;
			gap: 0.5rem;
		}
		
		.email-meta {
			align-self: flex-start;
		}
		
		.email-actions {
			gap: 0.25rem;
		}
		
		.action-btn {
			width: 1.75rem;
			height: 1.75rem;
		}
	}
</style>
