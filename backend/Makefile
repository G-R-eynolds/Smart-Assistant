# Smart Assistant Pipeline Testing Makefile
# 
# Quick commands to test the job scraping pipeline

.PHONY: help install test quick-test cv-test config-test search cover-letter full-pipeline clean

help:	## Show this help message
	@echo "Smart Assistant Pipeline Testing"
	@echo "================================"
	@echo ""
	@echo "Available commands:"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ { printf "  %-18s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo ""
	@echo "Examples:"
	@echo "  make quick-test                    # Run basic connectivity tests"
	@echo "  make search QUERY='python dev'     # Search for Python developer jobs"
	@echo "  make full-pipeline QUERY='SWE'     # Run complete pipeline"

install:	## Install required Python packages
	pip install pyairtable aiohttp structlog PyPDF2

quick-test:	## Run quick connectivity and configuration tests
	python quick_test.py

test:	## Show all available test commands
	python test_pipeline.py --help

cv-test:	## Test CV system (file upload and text extraction)
	python test_pipeline.py cv-info

config-test:	## Test all service configurations
	python test_pipeline.py config

# Search with optional parameters
QUERY ?= "software engineer"
LOCATION ?= 
MAX_RESULTS ?= 5

search:	## Search for jobs (use QUERY="job title" LOCATION="city" MAX_RESULTS=N)
	@if [ -z "$(LOCATION)" ]; then \
		python test_pipeline.py search "$(QUERY)" --max-results $(MAX_RESULTS); \
	else \
		python test_pipeline.py search "$(QUERY)" --location "$(LOCATION)" --max-results $(MAX_RESULTS); \
	fi

cover-letter:	## Generate cover letter for first job found (use QUERY="job title")
	python test_pipeline.py cover-letter "$(QUERY)"

# Full pipeline with optional flags
SAVE ?= false
COVER_LETTERS ?= false

full-pipeline:	## Run complete pipeline (use QUERY="job" SAVE=true COVER_LETTERS=true)
	@cmd="python test_pipeline.py full-pipeline \"$(QUERY)\""; \
	if [ "$(SAVE)" = "true" ]; then cmd="$$cmd --save"; fi; \
	if [ "$(COVER_LETTERS)" = "true" ]; then cmd="$$cmd --cover-letters"; fi; \
	if [ -n "$(LOCATION)" ]; then cmd="$$cmd --location \"$(LOCATION)\""; fi; \
	if [ "$(MAX_RESULTS)" != "5" ]; then cmd="$$cmd --max-results $(MAX_RESULTS)"; fi; \
	echo "Running: $$cmd"; \
	eval $$cmd

# Environment setup
setup-env:	## Copy .env template and show setup instructions
	@if [ ! -f .env ]; then \
		cp .env.template .env; \
		echo "✅ Created .env file from template"; \
		echo ""; \
		echo "📝 Next steps:"; \
		echo "  1. Edit .env file and add your API keys"; \
		echo "  2. Upload your CV: make upload-cv CV=/path/to/cv.pdf"; \
		echo "  3. Run tests: make quick-test"; \
	else \
		echo "⚠️  .env file already exists"; \
	fi

# CV upload helper
CV ?= 
upload-cv:	## Upload CV file (use CV=/path/to/cv.pdf)
	@if [ -z "$(CV)" ]; then \
		echo "❌ Please specify CV file: make upload-cv CV=/path/to/cv.pdf"; \
	else \
		python upload_cv.py "$(CV)"; \
	fi

# Development helpers
start-server:	## Start the backend server
	python -m app.main

check-logs:	## Show recent server logs (if running in background)
	tail -f app.log 2>/dev/null || echo "No log file found"

clean:	## Clean up temporary files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	echo "✅ Cleaned up Python cache files"

# Status check
status:	## Show current pipeline status
	@echo "Smart Assistant Pipeline Status"
	@echo "==============================="
	@echo ""
	@if [ -f .env ]; then echo "✅ Environment file exists"; else echo "❌ Environment file missing"; fi
	@if [ -f data/cv/cv.pdf ]; then echo "✅ CV file uploaded"; else echo "❌ CV file missing"; fi
	@echo ""
	@echo "Run 'make quick-test' for detailed status"

# Demo commands
demo-search:	## Demo: Search for software engineer jobs
	make search QUERY="software engineer" LOCATION="remote" MAX_RESULTS=3

demo-full:	## Demo: Full pipeline with cover letters
	make full-pipeline QUERY="python developer" COVER_LETTERS=true MAX_RESULTS=2

demo-save:	## Demo: Full pipeline with Airtable save
	make full-pipeline QUERY="data scientist" SAVE=true COVER_LETTERS=true MAX_RESULTS=2
