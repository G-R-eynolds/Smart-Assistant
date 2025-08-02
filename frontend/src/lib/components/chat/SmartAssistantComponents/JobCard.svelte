<!--
	JobCard.svelte
	
	Individual Job Display Component for Smart Assistant
	
	Features:
	- Clean job information display with company, title, location
	- Relevance score visualization with color coding
	- AI insights expansion with match reasoning
	- Action buttons for save, apply, and view details
	- Status indicators and employment type badges
	- Responsive design with hover interactions
-->

<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { slide, scale } from 'svelte/transition';
	
	// Icon imports
	import { 
		MapPin, 
		Building, 
		Clock, 
		DollarSign, 
		ExternalLink, 
		Bookmark, 
		BookmarkCheck,
		ChevronDown,
		ChevronUp,
		Brain,
		Star,
		Users,
		Calendar
	} from 'lucide-svelte';
	
	// Store imports
	import type { SmartAssistantJob } from '$lib/stores/smartAssistant';
	
	// Props
	export let job: SmartAssistantJob;
	
	// Local state
	let showDetails: boolean = false;
	let isHovering: boolean = false;
	
	// Event dispatcher for parent communication
	const dispatch = createEventDispatcher<{
		save: { jobId: string };
		apply: { job: SmartAssistantJob };
		details: { job: SmartAssistantJob };
	}>();
	
	// Computed properties
	$: relevanceColor = getRelevanceColor(job.relevance_score);
	$: relevancePercentage = Math.round(job.relevance_score * 100);
	$: employmentTypeBadge = getEmploymentTypeBadge(job.employment_type);
	$: experienceLevelBadge = getExperienceLevelBadge(job.experience_level);
	$: salaryDisplay = getSalaryDisplay(job.salary_min, job.salary_max);
	$: timeAgo = getTimeAgo(job.discovered_at);
	
	// Helper functions
	function getRelevanceColor(score: number): string {
		if (score >= 0.8) return 'text-green-600 bg-green-50 border-green-200';
		if (score >= 0.6) return 'text-blue-600 bg-blue-50 border-blue-200';
		if (score >= 0.4) return 'text-yellow-600 bg-yellow-50 border-yellow-200';
		return 'text-red-600 bg-red-50 border-red-200';
	}
	
	function getEmploymentTypeBadge(type: string): { text: string; color: string } {
		const badges = {
			'full-time': { text: 'Full Time', color: 'bg-blue-100 text-blue-800' },
			'part-time': { text: 'Part Time', color: 'bg-purple-100 text-purple-800' },
			'contract': { text: 'Contract', color: 'bg-orange-100 text-orange-800' },
			'remote': { text: 'Remote', color: 'bg-green-100 text-green-800' },
			'internship': { text: 'Internship', color: 'bg-indigo-100 text-indigo-800' }
		};
		return badges[type] || { text: type, color: 'bg-gray-100 text-gray-800' };
	}
	
	function getExperienceLevelBadge(level: string): { text: string; color: string } {
		const badges = {
			'entry': { text: 'Entry', color: 'bg-green-100 text-green-700' },
			'mid': { text: 'Mid-Level', color: 'bg-blue-100 text-blue-700' },
			'senior': { text: 'Senior', color: 'bg-purple-100 text-purple-700' },
			'executive': { text: 'Executive', color: 'bg-gray-100 text-gray-700' }
		};
		return badges[level] || { text: level, color: 'bg-gray-100 text-gray-700' };
	}
	
	function getSalaryDisplay(min?: number, max?: number): string {
		if (!min && !max) return '';
		if (min && max) return `$${(min / 1000).toFixed(0)}k - $${(max / 1000).toFixed(0)}k`;
		if (min) return `$${(min / 1000).toFixed(0)}k+`;
		if (max) return `Up to $${(max / 1000).toFixed(0)}k`;
		return '';
	}
	
	function getTimeAgo(dateString: string): string {
		const now = new Date();
		const past = new Date(dateString);
		const diffMs = now.getTime() - past.getTime();
		const diffMins = Math.floor(diffMs / (1000 * 60));
		const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
		const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
		
		if (diffMins < 60) return `${diffMins}m ago`;
		if (diffHours < 24) return `${diffHours}h ago`;
		return `${diffDays}d ago`;
	}
	
	// Event handlers
	function handleSave() {
		dispatch('save', { jobId: job.id });
	}
	
	function handleApply() {
		dispatch('apply', { job });
	}
	
	function handleDetails() {
		showDetails = !showDetails;
		dispatch('details', { job });
	}
	
	function handleCardClick(event: MouseEvent) {
		// Don't toggle details if clicking on action buttons
		if ((event.target as Element).closest('.job-actions')) {
			return;
		}
		showDetails = !showDetails;
	}
</script>

<div 
	class="job-card {job.status}"
	class:hovering={isHovering}
	on:mouseenter={() => isHovering = true}
	on:mouseleave={() => isHovering = false}
	on:click={handleCardClick}
	role="button"
	tabindex="0"
	on:keydown={(e) => e.key === 'Enter' && handleCardClick(e)}
	transition:scale={{ duration: 200 }}
>
	<!-- Job Header -->
	<div class="job-header">
		<div class="job-title-section">
			<h3 class="job-title">{job.title}</h3>
			<div class="job-meta">
				<span class="company">
					<Building class="w-4 h-4" />
					{job.company}
				</span>
				<span class="location">
					<MapPin class="w-4 h-4" />
					{job.location}
				</span>
				<span class="time-ago">
					<Clock class="w-4 h-4" />
					{timeAgo}
				</span>
			</div>
		</div>
		
		<!-- Relevance Score -->
		<div class="relevance-score {relevanceColor}">
			<Star class="w-4 h-4" />
			<span class="score-text">{relevancePercentage}%</span>
		</div>
	</div>
	
	<!-- Job Badges -->
	<div class="job-badges">
		<span class="badge {employmentTypeBadge.color}">
			{employmentTypeBadge.text}
		</span>
		<span class="badge {experienceLevelBadge.color}">
			{experienceLevelBadge.text}
		</span>
		{#if salaryDisplay}
			<span class="badge salary-badge">
				<DollarSign class="w-3 h-3" />
				{salaryDisplay}
			</span>
		{/if}
	</div>
	
	<!-- Job Description Preview -->
	<div class="job-description">
		<p>{job.description.slice(0, 150)}{job.description.length > 150 ? '...' : ''}</p>
	</div>
	
	<!-- AI Insights Preview -->
	{#if job.ai_insights.match_reasoning}
		<div class="ai-insights-preview">
			<Brain class="w-4 h-4 text-purple-500" />
			<span class="insights-text">
				{job.ai_insights.match_reasoning.slice(0, 80)}...
			</span>
		</div>
	{/if}
	
	<!-- Job Actions -->
	<div class="job-actions">
		<button 
			class="action-button save-button"
			class:saved={job.status === 'saved'}
			on:click|stopPropagation={handleSave}
			title={job.status === 'saved' ? 'Job saved' : 'Save job'}
		>
			{#if job.status === 'saved'}
				<BookmarkCheck class="w-4 h-4" />
				Saved
			{:else}
				<Bookmark class="w-4 h-4" />
				Save
			{/if}
		</button>
		
		<button 
			class="action-button apply-button"
			on:click|stopPropagation={handleApply}
			title="Apply for this job"
		>
			<ExternalLink class="w-4 h-4" />
			Apply
		</button>
		
		<button 
			class="action-button details-button"
			on:click|stopPropagation={handleDetails}
			title="View full details"
		>
			{#if showDetails}
				<ChevronUp class="w-4 h-4" />
				Less
			{:else}
				<ChevronDown class="w-4 h-4" />
				More
			{/if}
		</button>
	</div>
	
	<!-- Expanded Details -->
	{#if showDetails}
		<div class="job-details" transition:slide={{ duration: 300 }}>
			
			<!-- Full Description -->
			<div class="detail-section">
				<h4>Job Description</h4>
				<p class="full-description">{job.description}</p>
			</div>
			
			<!-- AI Insights -->
			{#if job.ai_insights}
				<div class="detail-section ai-insights">
					<h4>
						<Brain class="w-4 h-4" />
						AI Analysis
					</h4>
					
					{#if job.ai_insights.match_reasoning}
						<div class="insight-item">
							<strong>Match Reasoning:</strong>
							<p>{job.ai_insights.match_reasoning}</p>
						</div>
					{/if}
					
					{#if job.ai_insights.skills_match && job.ai_insights.skills_match.length > 0}
						<div class="insight-item">
							<strong>Skills Match:</strong>
							<div class="skills-list">
								{#each job.ai_insights.skills_match as skill}
									<span class="skill-tag">{skill}</span>
								{/each}
							</div>
						</div>
					{/if}
					
					<div class="insight-item">
						<strong>Experience Match:</strong>
						<span class="experience-match" class:positive={job.ai_insights.experience_match}>
							{job.ai_insights.experience_match ? 'Yes' : 'Partial'}
						</span>
					</div>
				</div>
			{/if}
			
			<!-- Job Details -->
			<div class="detail-section job-info">
				<h4>Additional Information</h4>
				<div class="info-grid">
					<div class="info-item">
						<Users class="w-4 h-4" />
						<span>Employment Type: {job.employment_type}</span>
					</div>
					<div class="info-item">
						<Calendar class="w-4 h-4" />
						<span>Experience Level: {job.experience_level}</span>
					</div>
					{#if job.job_url && job.job_url !== '#'}
						<div class="info-item">
							<ExternalLink class="w-4 h-4" />
							<a href={job.job_url} target="_blank" rel="noopener noreferrer">
								View Original Posting
							</a>
						</div>
					{/if}
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
	.job-card {
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 12px;
		padding: 1.5rem;
		cursor: pointer;
		transition: all 0.2s ease;
		position: relative;
		overflow: hidden;
	}
	
	.job-card:hover {
		border-color: #3b82f6;
		box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
		transform: translateY(-2px);
	}
	
	.job-card.saved {
		border-color: #10b981;
		background: linear-gradient(to right, #ecfdf5, #ffffff);
	}
	
	.job-card.applied {
		border-color: #8b5cf6;
		background: linear-gradient(to right, #f3e8ff, #ffffff);
	}
	
	/* Job Header */
	.job-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 1rem;
	}
	
	.job-title-section {
		flex: 1;
	}
	
	.job-title {
		font-size: 1.125rem;
		font-weight: 600;
		color: #111827;
		margin: 0 0 0.5rem 0;
		line-height: 1.4;
	}
	
	.job-meta {
		display: flex;
		flex-wrap: wrap;
		gap: 1rem;
		font-size: 0.875rem;
		color: #6b7280;
	}
	
	.job-meta > span {
		display: flex;
		align-items: center;
		gap: 0.25rem;
	}
	
	.company {
		font-weight: 500;
		color: #374151;
	}
	
	/* Relevance Score */
	.relevance-score {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.5rem 0.75rem;
		border-radius: 20px;
		font-size: 0.875rem;
		font-weight: 600;
		border: 1px solid;
		white-space: nowrap;
	}
	
	/* Job Badges */
	.job-badges {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		margin-bottom: 1rem;
	}
	
	.badge {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.25rem 0.75rem;
		border-radius: 12px;
		font-size: 0.75rem;
		font-weight: 500;
	}
	
	.salary-badge {
		background: #f3f4f6;
		color: #374151;
	}
	
	/* Job Description */
	.job-description {
		margin-bottom: 1rem;
	}
	
	.job-description p {
		color: #4b5563;
		line-height: 1.5;
		margin: 0;
	}
	
	/* AI Insights Preview */
	.ai-insights-preview {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem;
		background: #faf5ff;
		border: 1px solid #e9d5ff;
		border-radius: 8px;
		margin-bottom: 1rem;
	}
	
	.insights-text {
		font-size: 0.875rem;
		color: #7c3aed;
		font-style: italic;
	}
	
	/* Job Actions */
	.job-actions {
		display: flex;
		gap: 0.75rem;
		margin-top: 1rem;
	}
	
	.action-button {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 1rem;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		background: white;
		color: #374151;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.2s;
		flex: 1;
		justify-content: center;
	}
	
	.action-button:hover {
		background: #f9fafb;
		border-color: #9ca3af;
	}
	
	.save-button.saved {
		background: #ecfdf5;
		border-color: #10b981;
		color: #047857;
	}
	
	.apply-button {
		background: #3b82f6;
		border-color: #3b82f6;
		color: white;
	}
	
	.apply-button:hover {
		background: #2563eb;
		border-color: #2563eb;
	}
	
	.details-button {
		flex: 0 0 auto;
		min-width: 80px;
	}
	
	/* Job Details (Expanded) */
	.job-details {
		margin-top: 1.5rem;
		padding-top: 1.5rem;
		border-top: 1px solid #e5e7eb;
	}
	
	.detail-section {
		margin-bottom: 1.5rem;
	}
	
	.detail-section h4 {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 1rem;
		font-weight: 600;
		color: #111827;
		margin: 0 0 0.75rem 0;
	}
	
	.full-description {
		color: #4b5563;
		line-height: 1.6;
		margin: 0;
	}
	
	/* AI Insights Details */
	.ai-insights {
		background: #faf5ff;
		border: 1px solid #e9d5ff;
		border-radius: 8px;
		padding: 1rem;
	}
	
	.insight-item {
		margin-bottom: 1rem;
	}
	
	.insight-item:last-child {
		margin-bottom: 0;
	}
	
	.insight-item strong {
		color: #7c3aed;
		display: block;
		margin-bottom: 0.25rem;
	}
	
	.insight-item p {
		color: #4b5563;
		margin: 0;
	}
	
	.skills-list {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		margin-top: 0.5rem;
	}
	
	.skill-tag {
		background: #ddd6fe;
		color: #5b21b6;
		padding: 0.25rem 0.5rem;
		border-radius: 12px;
		font-size: 0.75rem;
		font-weight: 500;
	}
	
	.experience-match {
		color: #dc2626;
		font-weight: 500;
	}
	
	.experience-match.positive {
		color: #059669;
	}
	
	/* Job Info Grid */
	.info-grid {
		display: grid;
		gap: 0.75rem;
	}
	
	.info-item {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		color: #4b5563;
		font-size: 0.875rem;
	}
	
	.info-item a {
		color: #3b82f6;
		text-decoration: none;
	}
	
	.info-item a:hover {
		text-decoration: underline;
	}
	
	/* Responsive Design */
	@media (max-width: 768px) {
		.job-card {
			padding: 1rem;
		}
		
		.job-header {
			flex-direction: column;
			gap: 1rem;
		}
		
		.relevance-score {
			align-self: flex-start;
		}
		
		.job-meta {
			gap: 0.75rem;
		}
		
		.action-button {
			padding: 0.75rem 0.5rem;
			font-size: 0.8125rem;
		}
		
		.details-button {
			min-width: 70px;
		}
	}
</style>
