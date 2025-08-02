<!--
	JobDiscoveryInterface.svelte
	
	Smart Assistant Job Discovery Interface Component
	
	Features:
	- Job search trigger button with natural language input
	- Loading states and progress indicators
	- Job results grid layout with relevance filtering
	- Integration with Smart Assistant pipeline and store
	- Visual feedback for search operations
-->

<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { slide } from 'svelte/transition';
	
	// Store imports
	import { 
		smartAssistant, 
		smartAssistantActions, 
		jobSearchResults, 
		qualifiedJobs,
		hasActiveProcesses,
		type SmartAssistantJob 
	} from '$lib/stores/smartAssistant';
	
	// Component imports
	import JobCard from './JobCard.svelte';
	
	// Icons and UI components  
	import { Search, Filter, RefreshCw, ExternalLink, MapPin } from 'lucide-svelte';
	
	// Props
	export let isVisible: boolean = false;
	export let onClose: () => void = () => {};
	
	// Local state
	let searchQuery: string = '';
	let isSearching: boolean = false;
	let searchTimeout: NodeJS.Timeout | null = null;
	let jobsContainer: HTMLElement;
	let showAdvancedFilters: boolean = false;
	
	// Advanced filter options
	let filters = {
		experience_level: 'all',
		employment_type: 'all',
		min_relevance: 0.5,
		location: '',
		company: '',
		salary_min: null as number | null
	};
	
	// Reactive statements
	$: filteredJobs = $jobSearchResults.filter((job: SmartAssistantJob) => {
		// Apply relevance filter
		if (job.relevance_score < filters.min_relevance) return false;
		
		// Apply experience level filter
		if (filters.experience_level !== 'all' && 
			job.experience_level !== filters.experience_level) return false;
		
		// Apply employment type filter
		if (filters.employment_type !== 'all' && 
			job.employment_type !== filters.employment_type) return false;
		
		// Apply location filter
		if (filters.location && 
			!job.location.toLowerCase().includes(filters.location.toLowerCase())) return false;
		
		// Apply company filter
		if (filters.company && 
			!job.company.toLowerCase().includes(filters.company.toLowerCase())) return false;
		
		// Apply salary filter
		if (filters.salary_min && job.salary_min && 
			job.salary_min < filters.salary_min) return false;
		
		return true;
	});
	
	$: jobStats = {
		total: $jobSearchResults.length,
		qualified: $qualifiedJobs.length,
		filtered: filteredJobs.length,
		saved: $jobSearchResults.filter((job: SmartAssistantJob) => job.status === 'saved').length
	};
	
	// Job search function
	async function handleJobSearch() {
		if (!searchQuery.trim()) {
			toast.error('Please enter a job search query');
			return;
		}
		
		isSearching = true;
		smartAssistantActions.startJobSearch({ query: searchQuery });
		
		try {
			// Call the Smart Assistant job discovery endpoint
			const response = await fetch('/api/v1/smart_assistant/job_discovery/run', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					message: searchQuery,
					user: { id: 'user' } // Basic user object for pipeline
				})
			});
			
			if (!response.ok) {
				throw new Error(`Pipeline call failed: ${response.status}`);
			}
			
			const result = await response.json();
			
			// Check if jobs were found in the response
			if (result.data && result.data.jobs) {
				const jobs = result.data.jobs.map((job: any, index: number) => ({
					id: `job_${Date.now()}_${index}`,
					title: job.title || 'Unknown Title',
					company: job.company || 'Unknown Company',
					location: job.location || 'Unknown Location',
					relevance_score: job.relevance_score || 0.5,
					ai_insights: job.ai_insights || {
						match_reasoning: 'Job discovered through Smart Assistant',
						skills_match: [],
						experience_match: false
					},
					status: 'discovered' as const,
					discovered_at: new Date().toISOString(),
					job_url: job.job_url || '#',
					description: job.description || 'No description available',
					employment_type: job.employment_type || 'full-time',
					experience_level: job.experience_level || 'mid',
					salary_min: job.salary_min,
					salary_max: job.salary_max
				}));
				
				smartAssistantActions.updateJobResults(jobs);
				
				toast.success(`Found ${jobs.length} job opportunities!`);
				
				// Scroll to results
				setTimeout(() => {
					if (jobsContainer) {
						jobsContainer.scrollIntoView({ behavior: 'smooth' });
					}
				}, 100);
			} else {
				toast.warning('No jobs found for your search criteria');
				smartAssistantActions.updateJobResults([]);
			}
			
		} catch (error) {
			console.error('Job search failed:', error);
			toast.error('Job search failed. Please try again.');
			smartAssistantActions.updateJobResults([]);
		} finally {
			isSearching = false;
		}
	}
	
	// Handle real-time search with debouncing
	function handleSearchInput() {
		if (searchTimeout) {
			clearTimeout(searchTimeout);
		}
		
		// Auto-search after 2 seconds of inactivity
		searchTimeout = setTimeout(() => {
			if (searchQuery.trim()) {
				handleJobSearch();
			}
		}, 2000);
	}
	
	// Clear filters
	function clearFilters() {
		filters = {
			experience_level: 'all',
			employment_type: 'all',
			min_relevance: 0.5,
			location: '',
			company: '',
			salary_min: null
		};
	}
	
	// Handle job actions
	function handleJobSave(event: CustomEvent<{ jobId: string }>) {
		smartAssistantActions.saveJob(event.detail.jobId);
		toast.success('Job saved to your collection!');
	}
	
	function handleJobApply(event: CustomEvent<{ job: SmartAssistantJob }>) {
		// Open job URL in new tab
		window.open(event.detail.job.job_url, '_blank');
		toast.info('Opening job application page...');
	}
	
	// Lifecycle
	onMount(() => {
		// Focus search input when component becomes visible
		if (isVisible) {
			setTimeout(() => {
				const searchInput = document.getElementById('job-search-input');
				if (searchInput) {
					searchInput.focus();
				}
			}, 100);
		}
	});
	
	// Clean up timeout on destroy
	function onDestroy() {
		if (searchTimeout) {
			clearTimeout(searchTimeout);
		}
	}
</script>

{#if isVisible}
	<div class="smart-assistant-job-interface" transition:slide={{ duration: 300 }}>
		
		<!-- Header Section -->
		<div class="job-interface-header">
			<div class="header-content">
				<div class="header-title">
					<Search class="w-5 h-5 text-blue-500" />
					<h2>Smart Job Discovery</h2>
				</div>
				<button 
					class="close-button"
					on:click={onClose}
					title="Close Job Interface"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>
			
			<!-- Job Stats -->
			{#if jobStats.total > 0}
				<div class="job-stats">
					<div class="stat-item">
						<span class="stat-number">{jobStats.total}</span>
						<span class="stat-label">Total Jobs</span>
					</div>
					<div class="stat-item">
						<span class="stat-number">{jobStats.qualified}</span>
						<span class="stat-label">Qualified</span>
					</div>
					<div class="stat-item">
						<span class="stat-number">{jobStats.filtered}</span>
						<span class="stat-label">Filtered</span>
					</div>
					<div class="stat-item">
						<span class="stat-number">{jobStats.saved}</span>
						<span class="stat-label">Saved</span>
					</div>
				</div>
			{/if}
		</div>
		
		<!-- Search Section -->
		<div class="search-section">
			<div class="search-input-container">
				<Search class="search-icon" />
				<input
					id="job-search-input"
					type="text"
					bind:value={searchQuery}
					on:input={handleSearchInput}
					on:keydown={(e) => e.key === 'Enter' && handleJobSearch()}
					placeholder="Describe your ideal job (e.g., 'Senior Python developer in San Francisco')"
					class="search-input"
					disabled={isSearching || $hasActiveProcesses}
				/>
				<button
					class="search-button"
					on:click={handleJobSearch}
					disabled={isSearching || $hasActiveProcesses || !searchQuery.trim()}
				>
					{#if isSearching || $hasActiveProcesses}
						<RefreshCw class="w-4 h-4 animate-spin" />
					{:else}
						Search
					{/if}
				</button>
			</div>
			
			<!-- Advanced Filters Toggle -->
			<div class="filters-section">
				<button
					class="filters-toggle"
					on:click={() => showAdvancedFilters = !showAdvancedFilters}
				>
					<Filter class="w-4 h-4" />
					Filters {filteredJobs.length !== $jobSearchResults.length ? `(${filteredJobs.length})` : ''}
				</button>
				
				{#if showAdvancedFilters}
					<div class="advanced-filters" transition:slide={{ duration: 200 }}>
						<div class="filter-row">
							<div class="filter-group">
								<label for="experience-level-select">Experience Level</label>
								<select id="experience-level-select" bind:value={filters.experience_level}>
									<option value="all">All Levels</option>
									<option value="entry">Entry Level</option>
									<option value="mid">Mid Level</option>
									<option value="senior">Senior Level</option>
									<option value="executive">Executive</option>
								</select>
							</div>
							
							<div class="filter-group">
								<label for="employment-type-select">Employment Type</label>
								<select id="employment-type-select" bind:value={filters.employment_type}>
									<option value="all">All Types</option>
									<option value="full-time">Full Time</option>
									<option value="part-time">Part Time</option>
									<option value="contract">Contract</option>
									<option value="remote">Remote</option>
								</select>
							</div>
							
							<div class="filter-group">
								<label for="min-relevance-range">Min Relevance</label>
								<input 
									id="min-relevance-range"
									type="range" 
									bind:value={filters.min_relevance}
									min="0" 
									max="1" 
									step="0.1"
									class="relevance-slider"
								/>
								<span class="relevance-value">{Math.round(filters.min_relevance * 100)}%</span>
							</div>
						</div>
						
						<div class="filter-row">
							<div class="filter-group">
								<label for="location-input">Location</label>
								<input 
									id="location-input"
									type="text" 
									bind:value={filters.location}
									placeholder="City, State"
									class="filter-input"
								/>
							</div>
							
							<div class="filter-group">
								<label for="company-input">Company</label>
								<input 
									id="company-input"
									type="text" 
									bind:value={filters.company}
									placeholder="Company name"
									class="filter-input"
								/>
							</div>
							
							<div class="filter-group">
								<label for="salary-min-input">Min Salary ($)</label>
								<input 
									id="salary-min-input"
									type="number" 
									bind:value={filters.salary_min}
									placeholder="50000"
									class="filter-input"
								/>
							</div>
						</div>
						
						<div class="filter-actions">
							<button class="clear-filters-btn" on:click={clearFilters}>
								Clear Filters
							</button>
						</div>
					</div>
				{/if}
			</div>
		</div>
		
		<!-- Loading State -->
		{#if isSearching || $hasActiveProcesses}
			<div class="loading-section">
				<div class="loading-spinner">
					<RefreshCw class="w-8 h-8 animate-spin text-blue-500" />
				</div>
				<p class="loading-text">Discovering opportunities with Smart Assistant...</p>
				<div class="loading-steps">
					<div class="step active">Analyzing your request</div>
					<div class="step active">Searching job databases</div>
					<div class="step">Calculating relevance scores</div>
				</div>
			</div>
		{/if}
		
		<!-- Job Results -->
		{#if filteredJobs.length > 0}
			<div class="jobs-container" bind:this={jobsContainer}>
				<div class="jobs-header">
					<h3>Job Opportunities ({filteredJobs.length})</h3>
					<div class="view-options">
						<!-- Future: Grid/List view toggle -->
					</div>
				</div>
				
				<div class="jobs-grid">
					{#each filteredJobs as job (job.id)}
						<JobCard 
							{job}
							on:save={handleJobSave}
							on:apply={handleJobApply}
						/>
					{/each}
				</div>
			</div>
		{:else if $jobSearchResults.length > 0 && filteredJobs.length === 0}
			<div class="no-results">
				<Filter class="w-12 h-12 text-gray-400 mb-4" />
				<h3>No jobs match your filters</h3>
				<p>Try adjusting your filter criteria to see more results.</p>
				<button class="clear-filters-btn" on:click={clearFilters}>
					Clear All Filters
				</button>
			</div>
		{:else if !isSearching && !$hasActiveProcesses}
			<div class="empty-state">
				<Search class="w-16 h-16 text-gray-400 mb-4" />
				<h3>Ready to discover your next opportunity?</h3>
				<p>Use natural language to describe what you're looking for:</p>
				<div class="example-searches">
					<button class="example-search" on:click={() => { searchQuery = 'Senior software engineer in San Francisco'; handleJobSearch(); }}>
						"Senior software engineer in San Francisco"
					</button>
					<button class="example-search" on:click={() => { searchQuery = 'Remote Python developer position'; handleJobSearch(); }}>
						"Remote Python developer position"
					</button>
					<button class="example-search" on:click={() => { searchQuery = 'Data scientist role at startup'; handleJobSearch(); }}>
						"Data scientist role at startup"
					</button>
				</div>
			</div>
		{/if}
	</div>
{/if}

<style>
	.smart-assistant-job-interface {
		background: white;
		border-radius: 12px;
		box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
		margin: 1rem 0;
		overflow: hidden;
		border: 1px solid #e5e7eb;
	}
	
	/* Header Styles */
	.job-interface-header {
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
		padding: 1.5rem;
	}
	
	.header-content {
		display: flex;
		justify-content: between;
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
	
	.job-stats {
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
	
	/* Search Styles */
	.search-section {
		padding: 1.5rem;
		background: #f9fafb;
		border-bottom: 1px solid #e5e7eb;
	}
	
	.search-input-container {
		display: flex;
		align-items: center;
		background: white;
		border: 2px solid #e5e7eb;
		border-radius: 8px;
		padding: 0.75rem;
		margin-bottom: 1rem;
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
	
	.search-input::placeholder {
		color: #9ca3af;
	}
	
	.search-button {
		background: #3b82f6;
		color: white;
		border: none;
		border-radius: 6px;
		padding: 0.5rem 1rem;
		font-weight: 500;
		cursor: pointer;
		transition: background-color 0.2s;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}
	
	.search-button:hover:not(:disabled) {
		background: #2563eb;
	}
	
	.search-button:disabled {
		background: #9ca3af;
		cursor: not-allowed;
	}
	
	/* Filter Styles */
	.filters-section {
		display: flex;
		flex-direction: column;
	}
	
	.filters-toggle {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		background: white;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		padding: 0.5rem 1rem;
		cursor: pointer;
		font-size: 0.875rem;
		transition: all 0.2s;
		align-self: flex-start;
	}
	
	.filters-toggle:hover {
		background: #f3f4f6;
	}
	
	.advanced-filters {
		margin-top: 1rem;
		padding: 1rem;
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 8px;
	}
	
	.filter-row {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: 1rem;
		margin-bottom: 1rem;
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
	
	.filter-group select,
	.filter-input {
		padding: 0.5rem;
		border: 1px solid #d1d5db;
		border-radius: 4px;
		font-size: 0.875rem;
	}
	
	.relevance-slider {
		width: 100%;
	}
	
	.relevance-value {
		font-size: 0.75rem;
		color: #6b7280;
		align-self: center;
	}
	
	.filter-actions {
		display: flex;
		justify-content: flex-end;
	}
	
	.clear-filters-btn {
		background: #f3f4f6;
		color: #374151;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		padding: 0.5rem 1rem;
		cursor: pointer;
		font-size: 0.875rem;
		transition: background-color 0.2s;
	}
	
	.clear-filters-btn:hover {
		background: #e5e7eb;
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
		background: #dbeafe;
		color: #1d4ed8;
	}
	
	/* Jobs Grid */
	.jobs-container {
		padding: 1.5rem;
	}
	
	.jobs-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1.5rem;
	}
	
	.jobs-header h3 {
		font-size: 1.25rem;
		font-weight: 600;
		color: #111827;
		margin: 0;
	}
	
	.jobs-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
		gap: 1.5rem;
	}
	
	/* Empty States */
	.empty-state,
	.no-results {
		padding: 3rem;
		text-align: center;
		color: #6b7280;
	}
	
	.empty-state h3,
	.no-results h3 {
		font-size: 1.25rem;
		color: #374151;
		margin-bottom: 0.5rem;
	}
	
	.example-searches {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		margin-top: 1.5rem;
		max-width: 400px;
		margin-left: auto;
		margin-right: auto;
	}
	
	.example-search {
		background: #f3f4f6;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		padding: 0.75rem;
		cursor: pointer;
		text-align: left;
		transition: all 0.2s;
		font-size: 0.875rem;
	}
	
	.example-search:hover {
		background: #e5e7eb;
		border-color: #9ca3af;
	}
	
	/* Responsive Design */
	@media (max-width: 768px) {
		.job-stats {
			gap: 1rem;
		}
		
		.filter-row {
			grid-template-columns: 1fr;
		}
		
		.jobs-grid {
			grid-template-columns: 1fr;
		}
		
		.example-searches {
			max-width: 100%;
		}
	}
</style>
