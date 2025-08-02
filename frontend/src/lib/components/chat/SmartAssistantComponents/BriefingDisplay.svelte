<!--
	BriefingDisplay.svelte
	
	Smart Assistant Intelligence Briefing Display Component
	
	Features:
	- Daily intelligence briefing presentation with expandable sections
	- News categorization (market, technology, career insights)
	- Bookmark and sharing functionality for briefing items
	- Visual indicators for news importance and recency
	- Personalized insights based on user profile
	- Source attribution and credibility scoring
-->

<script lang="ts">
	import { onMount, createEventDispatcher } from 'svelte';
	import { slide, fade } from 'svelte/transition';
	import { toast } from 'svelte-sonner';
	
	// Store imports
	import { 
		smartAssistant, 
		smartAssistantActions,
		latestBriefingItems,
		type BriefingItem,
		type IntelligenceBriefing
	} from '$lib/stores/smartAssistant';
	
	// Icon imports
	import { 
		FileText, 
		TrendingUp, 
		Star, 
		ExternalLink, 
		Bookmark,
		BookmarkCheck,
		Share,
		ChevronDown,
		ChevronUp,
		Globe,
		Briefcase,
		Code,
		Calendar,
		Clock,
		RefreshCw,
		Filter,
		Search
	} from 'lucide-svelte';
	
	// Props
	export let isVisible: boolean = false;
	export let onClose: () => void = () => {};
	
	// Local state
	let selectedCategory: string = 'all';
	let selectedRelevance: string = 'all';
	let expandedSections: Set<string> = new Set(['news', 'trends']);
	let bookmarkedItems: Set<string> = new Set();
	let briefingContainer: HTMLElement;
	let searchQuery: string = '';
	
	// Event dispatcher
	const dispatch = createEventDispatcher<{
		itemBookmarked: { item: BriefingItem };
		itemShared: { item: BriefingItem };
		sourceClicked: { url: string };
	}>();
	
	// Reactive statements
	$: briefing = $smartAssistant.latest_briefing;
	$: isGenerating = $smartAssistant.briefing_in_progress;
	$: filteredNewsItems = filterNewsItems(briefing?.news_items || [], searchQuery, selectedCategory, selectedRelevance);
	$: briefingAge = briefing ? getBriefingAge(briefing.generated_at) : null;
	
	// Filter news items
	function filterNewsItems(items: BriefingItem[], query: string, category: string, relevance: string): BriefingItem[] {
		return items.filter(item => {
			// Search filter
			if (query && !item.title.toLowerCase().includes(query.toLowerCase()) && 
				!item.summary.toLowerCase().includes(query.toLowerCase())) {
				return false;
			}
			
			// Category filter
			if (category !== 'all' && item.category !== category) {
				return false;
			}
			
			// Relevance filter
			if (relevance !== 'all' && item.relevance !== relevance) {
				return false;
			}
			
			return true;
		});
	}
	
	// Generate briefing function
	async function generateBriefing() {
		smartAssistantActions.startBriefingGeneration();
		
		try {
			// Call the intelligence briefing pipeline
			const response = await fetch('/api/v1/smart_assistant/briefing/generate', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					message: 'Generate my daily intelligence briefing',
					user: { id: 'user' }
				})
			});
			
			if (!response.ok) {
				throw new Error(`Briefing generation failed: ${response.status}`);
			}
			
			const result = await response.json();
			
			if (result.data) {
				smartAssistantActions.updateBriefing(result.data);
				toast.success('Intelligence briefing generated successfully!');
				
				// Auto-expand key sections
				expandedSections.add('news');
				expandedSections.add('trends');
				expandedSections = expandedSections;
			} else {
				toast.warning('No briefing data received');
			}
			
		} catch (error) {
			console.error('Briefing generation failed:', error);
			toast.error('Failed to generate briefing. Please try again.');
		}
	}
	
	// Section toggle function
	function toggleSection(sectionId: string) {
		if (expandedSections.has(sectionId)) {
			expandedSections.delete(sectionId);
		} else {
			expandedSections.add(sectionId);
		}
		expandedSections = expandedSections;
	}
	
	// Bookmark item
	function toggleBookmark(item: BriefingItem) {
		if (bookmarkedItems.has(item.title)) {
			bookmarkedItems.delete(item.title);
			toast.info('Bookmark removed');
		} else {
			bookmarkedItems.add(item.title);
			toast.success('Item bookmarked');
		}
		bookmarkedItems = bookmarkedItems;
		dispatch('itemBookmarked', { item });
	}
	
	// Share item
	function shareItem(item: BriefingItem) {
		if (navigator.share) {
			navigator.share({
				title: item.title,
				text: item.summary,
				url: item.url
			});
		} else {
			// Fallback to copying URL
			navigator.clipboard.writeText(item.url || item.title);
			toast.success('Item details copied to clipboard');
		}
		dispatch('itemShared', { item });
	}
	
	// Open source link
	function openSource(item: BriefingItem) {
		if (item.url) {
			window.open(item.url, '_blank', 'noopener,noreferrer');
			dispatch('sourceClicked', { url: item.url });
		}
	}
	
	// Helper functions
	function getRelevanceColor(relevance: string): string {
		switch (relevance) {
			case 'high': return 'text-red-600 bg-red-50 border-red-200';
			case 'medium': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
			case 'low': return 'text-green-600 bg-green-50 border-green-200';
			default: return 'text-gray-600 bg-gray-50 border-gray-200';
		}
	}
	
	function getCategoryIcon(category: string) {
		switch (category.toLowerCase()) {
			case 'market': return TrendingUp;
			case 'technology': return Code;
			case 'career': return Briefcase;
			case 'business': return Globe;
			default: return FileText;
		}
	}
	
	function getBriefingAge(dateString: string): string {
		const now = new Date();
		const past = new Date(dateString);
		const diffMs = now.getTime() - past.getTime();
		const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
		const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
		
		if (diffHours < 1) return 'Just generated';
		if (diffHours < 24) return `${diffHours}h ago`;
		return `${diffDays}d ago`;
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
		// Auto-generate briefing if none exists and component is visible
		if (isVisible && !briefing) {
			generateBriefing();
		}
	});
</script>

{#if isVisible}
	<div class="smart-assistant-briefing-interface" transition:slide={{ duration: 300 }}>
		
		<!-- Header Section -->
		<div class="briefing-interface-header">
			<div class="header-content">
				<div class="header-title">
					<FileText class="w-5 h-5 text-blue-500" />
					<h2>Intelligence Briefing</h2>
					{#if briefingAge}
						<span class="briefing-age">{briefingAge}</span>
					{/if}
				</div>
				<button 
					class="close-button"
					on:click={onClose}
					title="Close Briefing Interface"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>
			
			<!-- Briefing Stats -->
			{#if briefing}
				<div class="briefing-stats">
					<div class="stat-item">
						<span class="stat-number">{briefing.news_items?.length || 0}</span>
						<span class="stat-label">News Items</span>
					</div>
					<div class="stat-item">
						<span class="stat-number">{briefing.tech_trends?.length || 0}</span>
						<span class="stat-label">Tech Trends</span>
					</div>
					<div class="stat-item">
						<span class="stat-number">{briefing.career_insights?.length || 0}</span>
						<span class="stat-label">Career Insights</span>
					</div>
					<div class="stat-item">
						<span class="stat-number">{briefing.key_takeaways?.length || 0}</span>
						<span class="stat-label">Key Takeaways</span>
					</div>
				</div>
			{/if}
		</div>
		
		<!-- Controls Section -->
		<div class="briefing-controls">
			<div class="primary-controls">
				<button
					class="generate-button"
					on:click={generateBriefing}
					disabled={isGenerating}
				>
					{#if isGenerating}
						<RefreshCw class="w-4 h-4 animate-spin" />
					{:else}
						<RefreshCw class="w-4 h-4" />
					{/if}
					{isGenerating ? 'Generating...' : 'Refresh Briefing'}
				</button>
				
				{#if briefing?.generation_time_ms}
					<span class="generation-time">
						<Clock class="w-3 h-3" />
						Generated in {briefing.generation_time_ms}ms
					</span>
				{/if}
			</div>
			
			<!-- Search and Filters -->
			{#if briefing?.news_items && briefing.news_items.length > 0}
				<div class="search-section">
					<div class="search-input-container">
						<Search class="search-icon" />
						<input
							type="text"
							bind:value={searchQuery}
							placeholder="Search briefing items..."
							class="search-input"
						/>
					</div>
					
					<div class="filters">
						<select bind:value={selectedCategory}>
							<option value="all">All Categories</option>
							<option value="market">Market</option>
							<option value="technology">Technology</option>
							<option value="career">Career</option>
							<option value="business">Business</option>
						</select>
						
						<select bind:value={selectedRelevance}>
							<option value="all">All Relevance</option>
							<option value="high">High</option>
							<option value="medium">Medium</option>
							<option value="low">Low</option>
						</select>
					</div>
				</div>
			{/if}
		</div>
		
		<!-- Loading State -->
		{#if isGenerating}
			<div class="loading-section">
				<div class="loading-spinner">
					<RefreshCw class="w-8 h-8 animate-spin text-blue-500" />
				</div>
				<p class="loading-text">Generating your personalized intelligence briefing...</p>
				<div class="loading-steps">
					<div class="step active">Analyzing market trends</div>
					<div class="step active">Processing tech news</div>
					<div class="step">Generating insights</div>
				</div>
			</div>
		{/if}
		
		<!-- Briefing Content -->
		{#if briefing}
			<div class="briefing-content" bind:this={briefingContainer}>
				
				<!-- Key Takeaways Section -->
				{#if briefing.key_takeaways && briefing.key_takeaways.length > 0}
					<div class="briefing-section key-takeaways">
						<button 
							class="section-header"
							on:click={() => toggleSection('takeaways')}
						>
							<Star class="w-4 h-4" />
							<h3>Key Takeaways ({briefing.key_takeaways.length})</h3>
							{#if expandedSections.has('takeaways')}
								<ChevronUp class="w-4 h-4" />
							{:else}
								<ChevronDown class="w-4 h-4" />
							{/if}
						</button>
						
						{#if expandedSections.has('takeaways')}
							<div class="section-content" transition:slide={{ duration: 300 }}>
								<div class="takeaways-list">
									{#each briefing.key_takeaways as takeaway, index}
										<div class="takeaway-item">
											<div class="takeaway-number">{index + 1}</div>
											<div class="takeaway-text">{takeaway}</div>
										</div>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				{/if}
				
				<!-- News Items Section -->
				{#if filteredNewsItems.length > 0}
					<div class="briefing-section news-items">
						<button 
							class="section-header"
							on:click={() => toggleSection('news')}
						>
							<Globe class="w-4 h-4" />
							<h3>News & Updates ({filteredNewsItems.length})</h3>
							{#if expandedSections.has('news')}
								<ChevronUp class="w-4 h-4" />
							{:else}
								<ChevronDown class="w-4 h-4" />
							{/if}
						</button>
						
						{#if expandedSections.has('news')}
							<div class="section-content" transition:slide={{ duration: 300 }}>
								<div class="news-grid">
									{#each filteredNewsItems as item}
										<div class="news-item">
											<div class="news-header">
												<div class="news-meta">
													<svelte:component this={getCategoryIcon(item.category)} class="w-4 h-4" />
													<span class="news-category">{item.category}</span>
													<span class="news-time">
														<Clock class="w-3 h-3" />
														{getTimeAgo(item.published_at)}
													</span>
												</div>
												<div class="relevance-badge {getRelevanceColor(item.relevance)}">
													{item.relevance}
												</div>
											</div>
											
											<h4 class="news-title">{item.title}</h4>
											<p class="news-summary">{item.summary}</p>
											
											<div class="news-footer">
												<div class="news-source">
													<span>Source: {item.source}</span>
												</div>
												
												<div class="news-actions">
													<button 
														class="action-btn bookmark"
														class:bookmarked={bookmarkedItems.has(item.title)}
														on:click={() => toggleBookmark(item)}
														title="Bookmark"
													>
														{#if bookmarkedItems.has(item.title)}
															<BookmarkCheck class="w-4 h-4" />
														{:else}
															<Bookmark class="w-4 h-4" />
														{/if}
													</button>
													<button 
														class="action-btn"
														on:click={() => shareItem(item)}
														title="Share"
													>
														<Share class="w-4 h-4" />
													</button>
													{#if item.url}
														<button 
															class="action-btn"
															on:click={() => openSource(item)}
															title="Open Source"
														>
															<ExternalLink class="w-4 h-4" />
														</button>
													{/if}
												</div>
											</div>
										</div>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				{/if}
				
				<!-- Tech Trends Section -->
				{#if briefing.tech_trends && briefing.tech_trends.length > 0}
					<div class="briefing-section tech-trends">
						<button 
							class="section-header"
							on:click={() => toggleSection('trends')}
						>
							<Code class="w-4 h-4" />
							<h3>Technology Trends ({briefing.tech_trends.length})</h3>
							{#if expandedSections.has('trends')}
								<ChevronUp class="w-4 h-4" />
							{:else}
								<ChevronDown class="w-4 h-4" />
							{/if}
						</button>
						
						{#if expandedSections.has('trends')}
							<div class="section-content" transition:slide={{ duration: 300 }}>
								<div class="trends-list">
									{#each briefing.tech_trends as trend}
										<div class="trend-item">
											<div class="trend-header">
												<h5>{trend.title}</h5>
												<div class="impact-score">
													Impact: {trend.impact_score}/10
												</div>
											</div>
											<p class="trend-summary">{trend.summary}</p>
										</div>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				{/if}
				
				<!-- Career Insights Section -->
				{#if briefing.career_insights && briefing.career_insights.length > 0}
					<div class="briefing-section career-insights">
						<button 
							class="section-header"
							on:click={() => toggleSection('career')}
						>
							<Briefcase class="w-4 h-4" />
							<h3>Career Insights ({briefing.career_insights.length})</h3>
							{#if expandedSections.has('career')}
								<ChevronUp class="w-4 h-4" />
							{:else}
								<ChevronDown class="w-4 h-4" />
							{/if}
						</button>
						
						{#if expandedSections.has('career')}
							<div class="section-content" transition:slide={{ duration: 300 }}>
								<div class="career-list">
									{#each briefing.career_insights as insight}
										<div class="career-item">
											<div class="career-header">
												<h5>{insight.title}</h5>
												<span class="career-relevance">{insight.relevance}</span>
											</div>
											<p class="career-description">{insight.description}</p>
										</div>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				{/if}
				
				<!-- Market Data Section -->
				{#if briefing.market_data && Object.keys(briefing.market_data).length > 0}
					<div class="briefing-section market-data">
						<button 
							class="section-header"
							on:click={() => toggleSection('market')}
						>
							<TrendingUp class="w-4 h-4" />
							<h3>Market Data</h3>
							{#if expandedSections.has('market')}
								<ChevronUp class="w-4 h-4" />
							{:else}
								<ChevronDown class="w-4 h-4" />
							{/if}
						</button>
						
						{#if expandedSections.has('market')}
							<div class="section-content" transition:slide={{ duration: 300 }}>
								<div class="market-grid">
									{#each Object.entries(briefing.market_data) as [key, value]}
										<div class="market-item">
											<div class="market-key">{key}</div>
											<div class="market-value">{value}</div>
										</div>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				{/if}
			</div>
		{:else if !isGenerating}
			<div class="empty-state">
				<FileText class="w-16 h-16 text-gray-400 mb-4" />
				<h3>Ready to generate your briefing</h3>
				<p>Click "Refresh Briefing" to get your personalized intelligence update.</p>
			</div>
		{/if}
	</div>
{/if}

<style>
	.smart-assistant-briefing-interface {
		background: white;
		border-radius: 12px;
		box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
		margin: 1rem 0;
		overflow: hidden;
		border: 1px solid #e5e7eb;
	}
	
	/* Header Styles */
	.briefing-interface-header {
		background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
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
	
	.briefing-age {
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
	
	.briefing-stats {
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
	.briefing-controls {
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
	
	.generate-button {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		background: #6366f1;
		color: white;
		border: none;
		border-radius: 6px;
		padding: 0.75rem 1rem;
		font-weight: 500;
		cursor: pointer;
		transition: background-color 0.2s;
	}
	
	.generate-button:hover:not(:disabled) {
		background: #4f46e5;
	}
	
	.generate-button:disabled {
		background: #9ca3af;
		cursor: not-allowed;
	}
	
	.generation-time {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		font-size: 0.75rem;
		color: #6b7280;
	}
	
	.search-section {
		display: flex;
		gap: 1rem;
		align-items: center;
	}
	
	.search-input-container {
		display: flex;
		align-items: center;
		background: white;
		border: 2px solid #e5e7eb;
		border-radius: 8px;
		padding: 0.5rem;
		flex: 1;
		max-width: 300px;
	}
	
	.search-icon {
		width: 1rem;
		height: 1rem;
		color: #6b7280;
		margin-right: 0.5rem;
	}
	
	.search-input {
		flex: 1;
		border: none;
		outline: none;
		font-size: 0.875rem;
		background: transparent;
	}
	
	.filters {
		display: flex;
		gap: 0.5rem;
	}
	
	.filters select {
		padding: 0.5rem;
		border: 1px solid #d1d5db;
		border-radius: 4px;
		font-size: 0.875rem;
		background: white;
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
		margin-bottom: 1.5rem;
	}
	
	.loading-steps {
		display: flex;
		justify-content: center;
		gap: 1rem;
	}
	
	.step {
		padding: 0.5rem 1rem;
		background: #f3f4f6;
		color: #6b7280;
		border-radius: 20px;
		font-size: 0.875rem;
		transition: all 0.3s;
	}
	
	.step.active {
		background: #e0e7ff;
		color: #3730a3;
	}
	
	/* Briefing Content */
	.briefing-content {
		padding: 1.5rem;
	}
	
	.briefing-section {
		margin-bottom: 1.5rem;
		border: 1px solid #e5e7eb;
		border-radius: 8px;
		overflow: hidden;
	}
	
	.section-header {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		width: 100%;
		padding: 1rem 1.5rem;
		background: #f9fafb;
		border: none;
		cursor: pointer;
		transition: background-color 0.2s;
	}
	
	.section-header:hover {
		background: #f3f4f6;
	}
	
	.section-header h3 {
		flex: 1;
		text-align: left;
		font-size: 1.125rem;
		font-weight: 600;
		color: #111827;
		margin: 0;
	}
	
	.section-content {
		padding: 1.5rem;
	}
	
	/* Key Takeaways */
	.takeaways-list {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}
	
	.takeaway-item {
		display: flex;
		gap: 1rem;
		align-items: flex-start;
	}
	
	.takeaway-number {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 2rem;
		height: 2rem;
		background: #6366f1;
		color: white;
		border-radius: 50%;
		font-weight: 600;
		flex-shrink: 0;
	}
	
	.takeaway-text {
		flex: 1;
		line-height: 1.6;
		color: #374151;
	}
	
	/* News Items */
	.news-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
		gap: 1.5rem;
	}
	
	.news-item {
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 8px;
		padding: 1.25rem;
		transition: all 0.2s;
	}
	
	.news-item:hover {
		border-color: #6366f1;
		box-shadow: 0 2px 8px rgba(99, 102, 241, 0.1);
	}
	
	.news-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 0.75rem;
	}
	
	.news-meta {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.75rem;
		color: #6b7280;
	}
	
	.news-category {
		font-weight: 500;
		text-transform: capitalize;
	}
	
	.news-time {
		display: flex;
		align-items: center;
		gap: 0.25rem;
	}
	
	.relevance-badge {
		padding: 0.25rem 0.5rem;
		border-radius: 12px;
		font-size: 0.625rem;
		font-weight: 600;
		text-transform: uppercase;
		border: 1px solid;
	}
	
	.news-title {
		font-size: 1rem;
		font-weight: 600;
		color: #111827;
		margin: 0 0 0.75rem 0;
		line-height: 1.4;
	}
	
	.news-summary {
		color: #4b5563;
		line-height: 1.5;
		margin: 0 0 1rem 0;
		font-size: 0.875rem;
	}
	
	.news-footer {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}
	
	.news-source {
		font-size: 0.75rem;
		color: #6b7280;
	}
	
	.news-actions {
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
	
	.action-btn.bookmark.bookmarked {
		background: #dbeafe;
		color: #1d4ed8;
		border-color: #3b82f6;
	}
	
	/* Tech Trends */
	.trends-list, .career-list {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}
	
	.trend-item, .career-item {
		padding: 1rem;
		background: #f8fafc;
		border-radius: 6px;
		border-left: 4px solid #6366f1;
	}
	
	.trend-header, .career-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.5rem;
	}
	
	.trend-header h5, .career-header h5 {
		font-weight: 600;
		color: #111827;
		margin: 0;
	}
	
	.impact-score {
		background: #6366f1;
		color: white;
		padding: 0.25rem 0.5rem;
		border-radius: 12px;
		font-size: 0.75rem;
		font-weight: 600;
	}
	
	.career-relevance {
		background: #f3f4f6;
		color: #374151;
		padding: 0.25rem 0.5rem;
		border-radius: 12px;
		font-size: 0.75rem;
		font-weight: 500;
	}
	
	.trend-summary, .career-description {
		color: #4b5563;
		line-height: 1.5;
		margin: 0;
		font-size: 0.875rem;
	}
	
	/* Market Data */
	.market-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: 1rem;
	}
	
	.market-item {
		padding: 1rem;
		background: #f0fdf4;
		border-radius: 6px;
		border-left: 4px solid #22c55e;
	}
	
	.market-key {
		font-weight: 600;
		color: #111827;
		margin-bottom: 0.25rem;
	}
	
	.market-value {
		color: #15803d;
		font-size: 1.125rem;
		font-weight: 600;
	}
	
	/* Empty State */
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
		.briefing-stats {
			gap: 1rem;
		}
		
		.search-section {
			flex-direction: column;
			gap: 0.5rem;
			align-items: stretch;
		}
		
		.search-input-container {
			max-width: none;
		}
		
		.news-grid {
			grid-template-columns: 1fr;
		}
		
		.market-grid {
			grid-template-columns: 1fr;
		}
		
		.takeaway-item {
			gap: 0.75rem;
		}
		
		.takeaway-number {
			width: 1.5rem;
			height: 1.5rem;
			font-size: 0.875rem;
		}
	}
</style>
