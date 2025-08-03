#!/bin/bash

# Smart Assistant Pipeline Test Script
# Quick and easy testing of the job scraping pipeline

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE} $1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if Python environment is set up
check_environment() {
    print_header "Checking Environment"
    
    # Check Python
    if command -v python3 &> /dev/null; then
        print_success "Python3 found: $(python3 --version)"
    else
        print_error "Python3 not found. Please install Python 3.9+"
        exit 1
    fi
    
    # Check if we're in the right directory
    if [ ! -f "test_pipeline.py" ]; then
        print_error "test_pipeline.py not found. Please run this script from the backend directory."
        exit 1
    fi
    
    # Check .env file
    if [ -f ".env" ]; then
        print_success ".env file found"
    else
        print_warning ".env file not found. Use: cp .env.template .env"
    fi
    
    # Check CV file
    if [ -f "data/cv/cv.pdf" ]; then
        print_success "CV file found"
    else
        print_warning "CV file not found. Upload with: python upload_cv.py /path/to/cv.pdf"
    fi
}

# Show usage
show_usage() {
    echo "Smart Assistant Pipeline Test Script"
    echo "====================================="
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  setup           - Setup environment and install dependencies"
    echo "  quick           - Run quick connectivity tests"
    echo "  cv              - Test CV system"
    echo "  config          - Test configuration"
    echo "  search <query>  - Search for jobs"
    echo "  cover <query>   - Generate cover letter"
    echo "  pipeline <query>- Run full pipeline"
    echo "  demo            - Run demo pipeline"
    echo "  help            - Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 quick"
    echo "  $0 search \"software engineer\""
    echo "  $0 pipeline \"python developer\""
    echo "  $0 demo"
}

# Setup environment
setup_environment() {
    print_header "Setting Up Environment"
    
    # Install dependencies
    print_info "Installing Python dependencies..."
    pip install pyairtable aiohttp structlog PyPDF2
    
    # Copy .env template if needed
    if [ ! -f ".env" ]; then
        cp .env.template .env
        print_success "Created .env file from template"
        print_warning "Please edit .env file and add your API keys"
    fi
    
    # Create CV directory
    mkdir -p data/cv
    print_success "CV directory created"
    
    print_success "Environment setup complete!"
    echo ""
    print_info "Next steps:"
    echo "  1. Edit .env file with your API keys"
    echo "  2. Upload CV: python upload_cv.py /path/to/cv.pdf"
    echo "  3. Run tests: $0 quick"
}

# Run specific test commands
run_quick_test() {
    print_header "Quick Test"
    python quick_test.py
}

run_cv_test() {
    print_header "CV System Test"
    python test_pipeline.py cv-info
}

run_config_test() {
    print_header "Configuration Test"
    python test_pipeline.py config
}

run_search_test() {
    local query="${1:-software engineer}"
    print_header "Job Search Test"
    print_info "Searching for: $query"
    python test_pipeline.py search "$query" --max-results 3
}

run_cover_letter_test() {
    local query="${1:-software engineer}"
    print_header "Cover Letter Test"
    print_info "Generating cover letter for: $query"
    python test_pipeline.py cover-letter "$query"
}

run_pipeline_test() {
    local query="${1:-python developer}"
    print_header "Full Pipeline Test"
    print_info "Running pipeline for: $query"
    python test_pipeline.py full-pipeline "$query" --max-results 2 --cover-letters
}

run_demo() {
    print_header "Demo Pipeline"
    print_info "Running demo with multiple test scenarios..."
    
    echo ""
    print_info "1. Testing configuration..."
    python test_pipeline.py config
    
    echo ""
    print_info "2. Testing CV system..."
    python test_pipeline.py cv-info
    
    echo ""
    print_info "3. Searching for jobs..."
    python test_pipeline.py search "software engineer" --max-results 2
    
    echo ""
    print_info "4. Testing cover letter generation..."
    python test_pipeline.py cover-letter "python developer"
    
    print_success "Demo completed!"
}

# Main script logic
main() {
    case "${1:-help}" in
        "setup")
            check_environment
            setup_environment
            ;;
        "quick")
            check_environment
            run_quick_test
            ;;
        "cv")
            check_environment
            run_cv_test
            ;;
        "config")
            check_environment
            run_config_test
            ;;
        "search")
            check_environment
            run_search_test "$2"
            ;;
        "cover")
            check_environment
            run_cover_letter_test "$2"
            ;;
        "pipeline")
            check_environment
            run_pipeline_test "$2"
            ;;
        "demo")
            check_environment
            run_demo
            ;;
        "help"|*)
            show_usage
            ;;
    esac
}

# Run main function with all arguments
main "$@"
