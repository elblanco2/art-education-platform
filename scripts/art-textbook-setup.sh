#!/bin/bash
# =========================================================
# Art Education Platform - Textbook Setup Script
# This script guides professors through the process of
# converting JPG textbook pages to an mdBook website
# with AI enhancements and deployment options.
# =========================================================

# --- Color and formatting definitions ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# --- Global variables ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$BASE_DIR/config/.art-textbook-config"
LOG_FILE="$BASE_DIR/art-textbook-setup.log"
ENV_FILE="$BASE_DIR/config/.env"
ENV_EXAMPLE="$BASE_DIR/config/.env.example"
PYTHON_MIN_VERSION="3.8"
TESSERACT_MIN_VERSION="4.1.0"
BOOK_ID=""

# --- Function: Display banner ---
show_banner() {
    clear
    echo -e "${BOLD}${BLUE}=======================================================${NC}"
    echo -e "${BOLD}${BLUE}       Art Education Platform - Textbook Setup         ${NC}"
    echo -e "${BOLD}${BLUE}=======================================================${NC}"
    echo -e "${CYAN}This script will guide you through the process of:${NC}"
    echo -e "${CYAN}- Converting textbook JPG pages to digital format${NC}"
    echo -e "${CYAN}- Enhancing content with AI (using local models)${NC}"
    echo -e "${CYAN}- Creating a franchise template${NC}"
    echo -e "${CYAN}- Deploying to your domain or Canvas LMS${NC}"
    echo -e "${BOLD}${BLUE}=======================================================${NC}"
    echo ""
}

# --- Function: Log messages ---
log_message() {
    local level=$1
    local message=$2
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
    
    case $level in
        "INFO") echo -e "${GREEN}$message${NC}" ;;
        "WARN") echo -e "${YELLOW}$message${NC}" ;;
        "ERROR") echo -e "${RED}$message${NC}" ;;
        *) echo -e "$message" ;;
    esac
}

# --- Function: Check Python ---
check_python() {
    if command -v python3 &>/dev/null; then
        local version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')
        log_message "INFO" "Found Python version $version"
        
        if python3 -c "import sys; exit(0) if sys.version_info >= (${PYTHON_MIN_VERSION//./, }) else exit(1)" &>/dev/null; then
            return 0
        else
            log_message "ERROR" "Python version must be at least $PYTHON_MIN_VERSION"
            exit 1
        fi
    else
        log_message "ERROR" "Python 3 not found. Please install Python $PYTHON_MIN_VERSION or newer."
        exit 1
    fi
}

# --- Function: Check Tesseract ---
check_tesseract() {
    if command -v tesseract &>/dev/null; then
        local version=$(tesseract --version 2>&1 | head -n 1 | awk '{print $2}')
        log_message "INFO" "Found Tesseract OCR version $version"
        
        # Check if using Tesseract 5.x for new features
        if [[ "$version" =~ ^5 ]]; then
            log_message "INFO" "Using Tesseract 5.x with improved OCR engine"
            OCR_ENGINE_MODE="--oem 2"  # LSTM only for v5.x
        else
            log_message "INFO" "Using Tesseract 4.x compatibility mode"
            OCR_ENGINE_MODE="--oem 1"  # Neural nets (LSTM) + legacy Tesseract
        fi
        
        return 0
    else
        log_message "ERROR" "Tesseract OCR not found. This is required for image processing."
        log_message "INFO" "Please install Tesseract OCR:"
        log_message "INFO" "  - macOS: brew install tesseract"
        log_message "INFO" "  - Ubuntu/Debian: sudo apt-get install tesseract-ocr"
        log_message "INFO" "  - CentOS/RHEL: sudo yum install tesseract"
        log_message "INFO" "  - Windows: https://github.com/UB-Mannheim/tesseract/wiki"
        exit 1
    fi
}

# --- Function: Check Git ---
check_git() {
    if command -v git &>/dev/null; then
        local version=$(git --version | awk '{print $3}')
        log_message "INFO" "Found Git version $version"
        return 0
    else
        log_message "ERROR" "Git not found. This is required for source control and deployment."
        log_message "INFO" "Please install Git:"
        log_message "INFO" "  - macOS: brew install git"
        log_message "INFO" "  - Ubuntu/Debian: sudo apt-get install git"
        log_message "INFO" "  - CentOS/RHEL: sudo yum install git"
        log_message "INFO" "  - Windows: https://git-scm.com/download/win"
        exit 1
    fi
}

# --- Function: Check Python packages ---
check_python_packages() {
    log_message "INFO" "Checking required Python packages..."
    
    local required_packages=(
        "fastapi"
        "uvicorn"
        "pydantic"
        "python-multipart"
        "pytesseract"
        "Pillow"
        "sentence-transformers"
        "python-dotenv"
        "jwt"
        "requests"
    )
    
    # Check if pip is installed
    if ! command -v pip3 &>/dev/null; then
        log_message "ERROR" "pip3 not found. Please install pip for Python 3."
        exit 1
    fi
    
    # Check and install packages
    for package in "${required_packages[@]}"; do
        package_name=${package//-/_}
        if ! python3 -c "import ${package_name}" &>/dev/null 2>&1; then
            log_message "WARN" "Package $package not found. Installing..."
            if pip3 install "$package"; then
                log_message "INFO" "Successfully installed $package"
            else
                log_message "ERROR" "Failed to install $package"
                exit 1
            fi
        else
            log_message "INFO" "Package $package is already installed"
        fi
    done
}

# --- Function: Check all dependencies ---
check_dependencies() {
    log_message "INFO" "Checking dependencies..."
    
    # Check Python version
    check_python
    
    # Check Tesseract OCR
    check_tesseract
    
    # Check Git 
    check_git
    
    # Check/install Python packages
    check_python_packages
    
    log_message "INFO" "All dependencies satisfied!"
}

# --- Function: Generate random key ---
generate_random_key() {
    python3 -c "import secrets; print(secrets.token_hex(32))"
}

# --- Function: Create directories ---
create_directories() {
    log_message "INFO" "Creating necessary directories..."
    
    local directories=(
        "$BASE_DIR/uploads"
        "$BASE_DIR/templates"
        "$BASE_DIR/static"
        "$BASE_DIR/data"
        "$BASE_DIR/instances"
        "$BASE_DIR/deployments"
    )
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_message "INFO" "Created directory: $dir"
        else
            log_message "INFO" "Directory already exists: $dir"
        fi
    done
}

# --- Function: Prompt for environment variable ---
prompt_env_var() {
    local var_name=$1
    local prompt_text=$2
    local default_value=$3
    local current_value=""
    
    # Check if already in .env file
    if [ -f "$ENV_FILE" ]; then
        current_value=$(grep "^$var_name=" "$ENV_FILE" | cut -d= -f2-)
    fi
    
    # If empty, use default
    if [ -z "$current_value" ]; then
        current_value=$default_value
    fi
    
    # Prompt user
    if [ -n "$current_value" ]; then
        read -p "$prompt_text [$current_value]: " user_input
    else
        read -p "$prompt_text: " user_input
    fi
    
    # Use user input or current value
    local final_value="${user_input:-$current_value}"
    
    # Update .env file
    if [ -f "$ENV_FILE" ]; then
        if grep -q "^$var_name=" "$ENV_FILE"; then
            # Replace existing line
            sed -i.bak "s|^$var_name=.*|$var_name=$final_value|" "$ENV_FILE" && rm "$ENV_FILE.bak"
        else
            # Add new line
            echo "$var_name=$final_value" >> "$ENV_FILE"
        fi
    else
        # Create new file
        echo "$var_name=$final_value" > "$ENV_FILE"
    fi
}

# --- Function: Setup environment ---
setup_environment() {
    log_message "INFO" "Setting up environment configuration..."
    
    if [ ! -f "$ENV_FILE" ] && [ -f "$ENV_EXAMPLE" ]; then
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        log_message "INFO" "Created .env file from template"
    fi
    
    # Prompt for essential environment variables
    prompt_env_var "SECRET_KEY" "Enter a secret key for secure operations" "$(generate_random_key)"
    prompt_env_var "SITE_URL" "Enter the base URL for your deployment" "https://example.com/textbooks"
    prompt_env_var "USE_LOCAL_EMBEDDINGS" "Use local embeddings to avoid API costs? (true/false)" "true"
    prompt_env_var "EMBEDDING_MODEL" "Local embedding model to use" "all-MiniLM-L6-v2"
    prompt_env_var "OCR_ENGINE" "OCR engine to use" "tesseract"
    
    # Create necessary directories
    create_directories
    
    log_message "INFO" "Environment setup complete"
}

# --- Function: Prompt for value (generic) ---
prompt_value() {
    local var_name=$1
    local prompt_text=$2
    local default_value=$3
    local value=""
    
    # Show prompt with optional default
    if [ -n "$default_value" ]; then
        read -p "$prompt_text [$default_value]: " value
        value="${value:-$default_value}"
    else
        read -p "$prompt_text: " value
        
        # Validate non-empty input for required fields
        while [ -z "$value" ]; do
            echo -e "${YELLOW}This field is required. Please provide a value.${NC}"
            read -p "$prompt_text: " value
        done
    fi
    
    # Set global variable
    eval "$var_name=\"$value\""
    
    # Save to config
    echo "$var_name=$value" >> "$CONFIG_FILE.tmp"
}

# --- Function: Collect book metadata ---
collect_book_metadata() {
    log_message "INFO" "Collecting book information..."
    
    # Create a temporary config file
    [ -f "$CONFIG_FILE.tmp" ] && rm "$CONFIG_FILE.tmp"
    touch "$CONFIG_FILE.tmp"
    
    echo -e "${CYAN}Let's collect information about your textbook.${NC}"
    echo -e "${CYAN}This will be used for the mdBook generation and deployment.${NC}"
    echo ""
    
    # Generate a unique book ID
    BOOK_ID=$(python3 -c "import uuid; print(str(uuid.uuid4()))")
    echo "BOOK_ID=$BOOK_ID" >> "$CONFIG_FILE.tmp"
    
    # Prompt for book details
    prompt_value "BOOK_TITLE" "Enter the textbook title" ""
    prompt_value "BOOK_AUTHOR" "Enter the author name(s)" ""
    prompt_value "BOOK_DESCRIPTION" "Enter a brief description of the textbook" ""
    
    # Prompt for academic information
    echo ""
    echo -e "${CYAN}Let's add some academic context:${NC}"
    prompt_value "COURSE_CODE" "Enter the course code (e.g., ARH1000)" ""
    prompt_value "ACADEMIC_TERM" "Enter the academic term (e.g., Fall 2025)" "$(date +%Y)-$(date +%Y -d '+1 year')"
    
    # Move temporary config to final location
    mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"
    
    log_message "INFO" "Book metadata collected and saved to $CONFIG_FILE"
    
    # Summary display
    echo ""
    echo -e "${GREEN}Book Information Summary:${NC}"
    echo -e "${BOLD}Title:${NC} $BOOK_TITLE"
    echo -e "${BOLD}Author:${NC} $BOOK_AUTHOR"
    echo -e "${BOLD}Course:${NC} $COURSE_CODE"
    echo -e "${BOLD}Term:${NC} $ACADEMIC_TERM"
    echo -e "${BOLD}Book ID:${NC} $BOOK_ID"
    echo ""
}

# --- Function: Validate JPG directory ---
validate_jpg_directory() {
    local dir=$1
    
    # Check if directory exists
    if [ ! -d "$dir" ]; then
        log_message "ERROR" "Directory does not exist: $dir"
        return 1
    fi
    
    # Check for JPG files
    local jpg_count=$(find "$dir" -name "*.jpg" -o -name "*.jpeg" | wc -l)
    
    if [ "$jpg_count" -eq 0 ]; then
        log_message "ERROR" "No JPG files found in directory: $dir"
        return 1
    fi
    
    # Check naming convention
    local sequential_count=$(find "$dir" -name "page[0-9]*.jpg" -o -name "page[0-9]*.jpeg" | wc -l)
    
    if [ "$sequential_count" -lt "$jpg_count" ]; then
        log_message "WARN" "Some files don't follow the recommended naming convention (page001.jpg, page002.jpg, etc.)"
        log_message "WARN" "This may affect the ordering of content in the final book."
        
        # Ask if user wants to continue
        read -p "Do you want to continue anyway? (y/n): " continue_anyway
        if [[ ! $continue_anyway =~ ^[Yy]$ ]]; then
            log_message "INFO" "Please rename your files and try again."
            return 1
        fi
    fi
    
    # Basic image validation
    log_message "INFO" "Validating image files. This may take a moment..."
    
    local invalid_count=0
    for img in "$dir"/*.jpg "$dir"/*.jpeg; do
        # Skip if not a file
        [ -f "$img" ] || continue
        
        # Check if it's a valid JPG
        if ! file "$img" | grep -q "JPEG image data"; then
            log_message "ERROR" "Invalid JPEG file: $img"
            invalid_count=$((invalid_count + 1))
        fi
    done
    
    if [ "$invalid_count" -gt 0 ]; then
        log_message "ERROR" "Found $invalid_count invalid image file(s)."
        return 1
    fi
    
    log_message "INFO" "Found $jpg_count valid JPG files."
    return 0
}

# --- Function: Select JPG directory ---
select_jpg_directory() {
    log_message "INFO" "Selecting JPG directory..."
    
    echo -e "${CYAN}We need to locate the directory containing your textbook JPG files.${NC}"
    echo -e "${CYAN}Files should ideally be named in sequence (e.g., page001.jpg, page002.jpg, etc.)${NC}"
    echo ""
    
    local valid=false
    
    while [ "$valid" != "true" ]; do
        read -p "Enter the full path to your JPG directory: " JPG_DIR
        
        # Expand tilde in path
        JPG_DIR="${JPG_DIR/#\~/$HOME}"
        
        # Validate the directory
        if validate_jpg_directory "$JPG_DIR"; then
            valid=true
            echo "JPG_DIR=$JPG_DIR" >> "$CONFIG_FILE"
            log_message "INFO" "JPG directory selected: $JPG_DIR"
        else
            echo -e "${YELLOW}Please try again or press Ctrl+C to exit.${NC}"
        fi
    done
    
    # Count JPG files
    local jpg_count=$(find "$JPG_DIR" -name "*.jpg" -o -name "*.jpeg" | wc -l)
    echo -e "${GREEN}Selected directory with $jpg_count JPG files: $JPG_DIR${NC}"
    
    # Check if files exceed a reasonable limit
    if [ "$jpg_count" -gt 1000 ]; then
        log_message "WARN" "You have a large number of files ($jpg_count). Processing may take a while."
        echo -e "${YELLOW}You have a large number of files ($jpg_count). Processing may take a while.${NC}"
    fi
}

# --- Function: Configure OCR options ---
configure_ocr() {
    log_message "INFO" "Configuring OCR settings..."
    
    echo -e "${CYAN}Let's configure OCR (Optical Character Recognition) settings.${NC}"
    echo -e "${CYAN}These settings affect how text is extracted from your images.${NC}"
    echo ""
    
    # OCR engine selection - we use Tesseract by default to avoid API costs
    echo -e "${BOLD}OCR Engine:${NC}"
    echo -e "1) Tesseract (Local, free, good quality)"
    echo -e "2) Platform Default (Uses the platform's optimized settings)"
    
    local ocr_choice
    read -p "Select OCR engine [1]: " ocr_choice
    ocr_choice=${ocr_choice:-1}
    
    case $ocr_choice in
        1)
            OCR_ENGINE="tesseract"
            ;;
        2)
            OCR_ENGINE="platform_default"
            ;;
        *)
            log_message "WARN" "Invalid selection. Using Tesseract as default."
            OCR_ENGINE="tesseract"
            ;;
    esac
    
    echo "OCR_ENGINE=$OCR_ENGINE" >> "$CONFIG_FILE"
    
    # OCR language
    echo ""
    echo -e "${BOLD}OCR Language:${NC}"
    
    local available_langs=$(tesseract --list-langs 2>/dev/null | tail -n +2)
    
    echo "Available languages:"
    echo "$available_langs" | tr '\n' ' '
    echo ""
    
    read -p "Enter OCR language(s) [eng]: " OCR_LANG
    OCR_LANG=${OCR_LANG:-eng}
    echo "OCR_LANG=$OCR_LANG" >> "$CONFIG_FILE"
    
    # OCR quality settings
    echo ""
    echo -e "${BOLD}OCR Quality:${NC}"
    echo -e "1) Fast (Lower quality, faster processing)"
    echo -e "2) Balanced (Good quality, reasonable speed) - Recommended"
    echo -e "3) High Quality (Best quality, slower processing)"
    
    local quality_choice
    read -p "Select quality level [2]: " quality_choice
    quality_choice=${quality_choice:-2}
    
    case $quality_choice in
        1)
            OCR_QUALITY="fast"
            ;;
        2)
            OCR_QUALITY="balanced"
            ;;
        3)
            OCR_QUALITY="high"
            ;;
        *)
            log_message "WARN" "Invalid selection. Using Balanced as default."
            OCR_QUALITY="balanced"
            ;;
    esac
    
    echo "OCR_QUALITY=$OCR_QUALITY" >> "$CONFIG_FILE"
    
    # Image preprocessing options
    echo ""
    echo -e "${BOLD}Image Preprocessing:${NC}"
    echo -e "Select preprocessing options (improves OCR quality):"
    
    local preprocess_options=()
    
    # Ask about each option
    read -p "Apply deskew? (y/n) [y]: " choice
    choice=${choice:-y}
    [[ $choice =~ ^[Yy]$ ]] && preprocess_options+=("deskew")
    
    read -p "Apply contrast enhancement? (y/n) [y]: " choice
    choice=${choice:-y}
    [[ $choice =~ ^[Yy]$ ]] && preprocess_options+=("contrast")
    
    read -p "Apply noise reduction? (y/n) [y]: " choice
    choice=${choice:-y}
    [[ $choice =~ ^[Yy]$ ]] && preprocess_options+=("denoise")
    
    # Join array with commas
    PREPROCESS_OPTIONS=$(IFS=,; echo "${preprocess_options[*]}")
    echo "PREPROCESS_OPTIONS=$PREPROCESS_OPTIONS" >> "$CONFIG_FILE"
    
    log_message "INFO" "OCR settings configured"
    echo -e "${GREEN}OCR configuration complete!${NC}"
}

# --- Function: Process images with OCR ---
process_images() {
    log_message "INFO" "Starting image processing with OCR..."
    
    # Load config values
    source "$CONFIG_FILE"
    
    # Create output directories
    local ocr_output_dir="$BASE_DIR/data/$BOOK_ID/ocr"
    local md_output_dir="$BASE_DIR/data/$BOOK_ID/markdown"
    
    mkdir -p "$ocr_output_dir"
    mkdir -p "$md_output_dir"
    
    echo -e "${CYAN}Starting OCR processing of your images. This may take some time.${NC}"
    echo -e "${CYAN}Processing settings:${NC}"
    echo -e "- OCR Engine: ${BOLD}$OCR_ENGINE${NC}"
    echo -e "- OCR Language: ${BOLD}$OCR_LANG${NC}"
    echo -e "- Quality: ${BOLD}$OCR_QUALITY${NC}"
    echo -e "- Preprocessing: ${BOLD}$PREPROCESS_OPTIONS${NC}"
    echo -e "- Engine Mode: ${BOLD}$OCR_ENGINE_MODE${NC}"
    echo ""
    
    # Count total JPG files
    local total_files=$(find "$JPG_DIR" -name "*.jpg" -o -name "*.jpeg" | wc -l)
    local processed=0
    
    # Find all JPG files and sort them numerically if possible
    local files=()
    while IFS= read -r file; do
        files+=("$file")
    done < <(find "$JPG_DIR" -name "*.jpg" -o -name "*.jpeg" | sort -V)
    
    # Process each image
    for img in "${files[@]}"; do
        # Get filename without extension
        local filename=$(basename "$img")
        local name_no_ext="${filename%.*}"
        
        # Progress indicator
        processed=$((processed + 1))
        progress=$((processed * 100 / total_files))
        printf "Processing: [%-50s] %d%%\r" "$(printf '#%.0s' $(seq 1 $((progress / 2))))" "$progress"
        
        # OCR the image
        if [ "$OCR_ENGINE" = "tesseract" ]; then
            # Preprocess if needed using Python script
            if [ -n "$PREPROCESS_OPTIONS" ]; then
                python3 "$BASE_DIR/src/ocr/image_processor.py" --input "$img" --output "$ocr_output_dir/${name_no_ext}.txt" --preprocess "$PREPROCESS_OPTIONS" --lang "$OCR_LANG" --quality "$OCR_QUALITY" --engine-mode "$OCR_ENGINE_MODE"
            else
                # Direct tesseract if no preprocessing
                tesseract "$img" "$ocr_output_dir/${name_no_ext}" -l "$OCR_LANG" $OCR_ENGINE_MODE txt
            fi
        else
            # Use platform default OCR engine through Python wrapper
            python3 "$BASE_DIR/src/ocr/image_processor.py" --input "$img" --output "$ocr_output_dir/${name_no_ext}.txt" --engine "$OCR_ENGINE" --lang "$OCR_LANG" --quality "$OCR_QUALITY" --engine-mode "$OCR_ENGINE_MODE"
        fi
        
        # Convert OCR to markdown
        python3 "$BASE_DIR/src/ocr/text_processor.py" --input "$ocr_output_dir/${name_no_ext}.txt" --output "$md_output_dir/${name_no_ext}.md" --format "markdown" --clean
        
        log_message "INFO" "Processed $img"
    done
    
    # Clear progress line and show completion
    printf "\033[2K" # Clear line
    echo -e "${GREEN}OCR processing complete! Processed $total_files images.${NC}"
    
    # Save paths to config
    echo "OCR_OUTPUT_DIR=$ocr_output_dir" >> "$CONFIG_FILE"
    echo "MD_OUTPUT_DIR=$md_output_dir" >> "$CONFIG_FILE"
    
    log_message "INFO" "Image processing complete. OCR output at $ocr_output_dir, Markdown at $md_output_dir"
}

# --- Function: Generate mdBook ---
generate_mdbook() {
    log_message "INFO" "Generating mdBook from processed images..."
    
    # Load config values
    source "$CONFIG_FILE"
    
    # Create book directory
    local book_dir="$BASE_DIR/instances/$BOOK_ID"
    mkdir -p "$book_dir"
    
    echo -e "${CYAN}Creating mdBook structure...${NC}"
    
    # Check if mdbook is installed
    if ! command -v mdbook &>/dev/null; then
        log_message "WARN" "mdBook is not installed. Installing..."
        
        # Install mdbook using cargo if available
        if command -v cargo &>/dev/null; then
            cargo install mdbook
        else
            log_message "ERROR" "Cargo is not installed. Please install Rust and Cargo first."
            log_message "INFO" "Visit https://www.rust-lang.org/tools/install for installation instructions."
            exit 1
        fi
    fi
    
    # Initialize mdBook
    (cd "$book_dir" && mdbook init --title "$BOOK_TITLE" --ignore=none)
    
    # Prepare SUMMARY.md content
    echo "# Summary" > "$book_dir/src/SUMMARY.md"
    echo "" >> "$book_dir/src/SUMMARY.md"
    echo "- [Introduction](README.md)" >> "$book_dir/src/SUMMARY.md"
    
    # Create book README
    cat > "$book_dir/src/README.md" << EOF
# $BOOK_TITLE

By: $BOOK_AUTHOR

$BOOK_DESCRIPTION

*Course: $COURSE_CODE*  
*Term: $ACADEMIC_TERM*

This digital textbook was created using the Art Education Platform.
EOF
    
    # Copy all markdown files 
    echo -e "${CYAN}Copying content to mdBook...${NC}"
    
    # Find markdown files and sort them
    local md_files=()
    while IFS= read -r file; do
        md_files+=("$file")
    done < <(find "$MD_OUTPUT_DIR" -name "*.md" | sort -V)
    
    # Create chapters
    for md_file in "${md_files[@]}"; do
        # Get filename without extension
        local filename=$(basename "$md_file")
        local name_no_ext="${filename%.*}"
        
        # Create chapter number and title
        local chapter_num=$(echo "$name_no_ext" | grep -o '[0-9]\+' | sed 's/^0*//')
        local chapter_title="Chapter $chapter_num"
        
        # Copy content to mdBook
        cp "$md_file" "$book_dir/src/chapter_${chapter_num}.md"
        
        # Add to SUMMARY.md
        echo "- [$chapter_title](chapter_${chapter_num}.md)" >> "$book_dir/src/SUMMARY.md"
        
        log_message "INFO" "Added $chapter_title from $md_file"
    done
    
    # Create custom book.toml with additional settings
    cat > "$book_dir/book.toml" << EOF
[book]
authors = ["$BOOK_AUTHOR"]
language = "en"
multilingual = false
src = "src"
title = "$BOOK_TITLE"

[output.html]
default-theme = "light"
preferred-dark-theme = "navy"
git-repository-url = ""
edit-url-template = ""
additional-css = ["custom.css"]
additional-js = ["custom.js"]

[output.html.search]
enable = true
limit-results = 20
teaser-word-count = 30
use-boolean-and = true
boost-title = 2
boost-hierarchy = 1
boost-paragraph = 1
expand = true
heading-split-level = 3
EOF
    
    # Create custom CSS
    cat > "$book_dir/src/custom.css" << EOF
:root {
    --content-max-width: 1000px;
}
img {
    max-width: 100%;
    display: block;
    margin: 0 auto;
}
.chapter {
    line-height: 1.6;
}
EOF
    
    # Create custom JS for any interactive elements
    cat > "$book_dir/src/custom.js" << EOF
// Custom JavaScript for enhanced interactivity
document.addEventListener('DOMContentLoaded', function() {
    console.log('Art Education Platform mdBook loaded');
});
EOF
    
    # Build the book
    echo -e "${CYAN}Building mdBook...${NC}"
    (cd "$book_dir" && mdbook build)
    
    # Save book path to config
    echo "BOOK_DIR=$book_dir" >> "$CONFIG_FILE"
    
    log_message "INFO" "mdBook generation complete. Book available at $book_dir/book"
    echo -e "${GREEN}mdBook generation complete!${NC}"
    echo -e "${GREEN}Your book is available at: ${BOLD}$book_dir/book${NC}"
}

# --- Function: Apply AI enhancements ---
apply_ai_enhancements() {
    log_message "INFO" "Applying AI enhancements to the book..."
    
    # Load config values
    source "$CONFIG_FILE"
    
    echo -e "${CYAN}Applying AI enhancements to your textbook...${NC}"
    echo -e "${CYAN}This will improve the reading experience with:${NC}"
    echo -e "- Cross-references between chapters"
    echo -e "- Term definitions and glossary"
    echo -e "- Enhanced search capabilities"
    echo -e "- Improved navigation"
    echo ""
    
    # Check for Python dependencies (sentence-transformers)
    check_python_package "sentence-transformers" || {
        echo -e "${YELLOW}Installing sentence-transformers package...${NC}"
        python3 -m pip install sentence-transformers
    }
    
    # Check for sentence-transformers version
    local st_version=$(python3 -c "import pkg_resources; print(pkg_resources.get_distribution('sentence-transformers').version)")
    local is_v4_or_higher=false
    
    if [[ $(echo "$st_version" | cut -d. -f1) -ge 4 ]]; then
        is_v4_or_higher=true
        log_message "INFO" "Using sentence-transformers v4.0+ with new API"
    else
        log_message "INFO" "Using sentence-transformers v3.x compatibility mode"
    fi
    
    # Enhance the book with AI
    echo -e "${CYAN}Processing markdown files for enhancements...${NC}"
    
    # Create enhancement script with version check
    local temp_script=$(mktemp)
    cat <<EOF > "$temp_script"
import os
import sys
import glob
from pathlib import Path
import re
import json

try:
    from sentence_transformers import SentenceTransformer
    
    # Check for v4.0+ and adjust imports accordingly
    import pkg_resources
    st_version = pkg_resources.get_distribution('sentence-transformers').version
    major_version = int(st_version.split('.')[0])
    
    # Import appropriate modules based on version
    if major_version >= 4:
        from sentence_transformers import Embedder  # v4.0+ API
        using_v4 = True
    else:
        using_v4 = False
        
except ImportError:
    print("Error: sentence-transformers package not installed")
    sys.exit(1)

def extract_terms(md_files):
    """Extract important terms from markdown files"""
    terms = {}
    
    term_pattern = re.compile(r'\*\*(.*?)\*\*')
    
    for file_path in md_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Extract terms in bold
        matches = term_pattern.findall(content)
        
        for term in matches:
            if len(term) > 3:  # Ignore very short terms
                if term not in terms:
                    # Get the context (sentence containing the term)
                    context_pattern = re.compile(r'[^.!?]*\*\*' + re.escape(term) + r'\*\*[^.!?]*[.!?]')
                    context_matches = context_pattern.findall(content)
                    
                    if context_matches:
                        context = context_matches[0].strip()
                    else:
                        context = ""
                    
                    terms[term] = {
                        'definition': context,
                        'occurrences': [os.path.basename(file_path)],
                        'file_path': file_path
                    }
                else:
                    if os.path.basename(file_path) not in terms[term]['occurrences']:
                        terms[term]['occurrences'].append(os.path.basename(file_path))
    
    return terms

def create_embeddings(terms):
    """Create embeddings for terms using sentence-transformers"""
    print("Creating embeddings for glossary terms...")
    
    if using_v4:
        # Use v4.0+ API
        embedder = Embedder()
        term_texts = list(terms.keys())
        embeddings = embedder.embed(term_texts)
        
        # Add embeddings to terms dictionary
        for i, term in enumerate(term_texts):
            terms[term]['embedding'] = embeddings[i].tolist()
    else:
        # Use legacy API
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Process terms in batches to avoid memory issues
        batch_size = 32
        term_texts = list(terms.keys())
        
        for i in range(0, len(term_texts), batch_size):
            batch = term_texts[i:i+batch_size]
            embeddings = model.encode(batch)
            
            # Add embeddings to terms dictionary
            for j, term in enumerate(batch):
                terms[term]['embedding'] = embeddings[j].tolist()
    
    return terms

def create_cross_references(terms, md_files):
    """Create cross-references between markdown files"""
    print("Creating cross-references between chapters...")
    
    # For each file, find referenced terms and add links
    for file_path in md_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace terms with links to glossary
        for term, info in terms.items():
            # Don't replace terms in their own definition file
            if file_path != info['file_path']:
                # Create pattern that matches the term but not if it's already in a link
                pattern = r'(?<!\[)\*\*(' + re.escape(term) + r')\*\*(?!\])'
                replacement = f'**[{term}](glossary.md#{term.lower().replace(" ", "-")})**'
                content = re.sub(pattern, replacement, content)
        
        # Write updated content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

def create_glossary(terms, book_dir):
    """Create a glossary markdown file"""
    print("Creating glossary...")
    
    glossary_path = os.path.join(book_dir, 'src', 'glossary.md')
    
    with open(glossary_path, 'w', encoding='utf-8') as f:
        f.write("# Glossary\n\n")
        f.write("This glossary contains important terms used throughout the book.\n\n")
        
        # Sort terms alphabetically
        sorted_terms = sorted(terms.keys())
        
        for term in sorted_terms:
            info = terms[term]
            f.write(f"## {term}\n\n")
            f.write(f"{info['definition']}\n\n")
            
            if len(info['occurrences']) > 0:
                f.write("**Appears in:** ")
                
                # Create links to chapters
                chapter_links = []
                for occurrence in info['occurrences']:
                    chapter_name = os.path.splitext(occurrence)[0]
                    chapter_links.append(f"[{chapter_name}]({occurrence})")
                
                f.write(", ".join(chapter_links))
                f.write("\n\n")
        
        # Store terms data as JSON for search functionality
        terms_json = json.dumps(terms)
        terms_js_path = os.path.join(book_dir, 'src', 'terms.json')
        
        with open(terms_js_path, 'w', encoding='utf-8') as js_file:
            js_file.write(terms_json)

def update_summary(book_dir):
    """Update SUMMARY.md to include glossary"""
    summary_path = os.path.join(book_dir, 'src', 'SUMMARY.md')
    
    with open(summary_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add glossary if not already present
    if "- [Glossary](glossary.md)" not in content:
        # Find position to insert (before end of file or any appendix)
        lines = content.split('\n')
        insert_pos = len(lines)
        
        for i, line in enumerate(lines):
            if line.startswith("- [Appendix") or line.startswith("# Appendix"):
                insert_pos = i
                break
        
        # Insert glossary link
        lines.insert(insert_pos, "- [Glossary](glossary.md)")
        
        # Write updated content
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

def enhance_search(book_dir):
    """Enhance search functionality"""
    print("Enhancing search functionality...")
    
    # Check if book.js exists
    book_js_path = os.path.join(book_dir, 'src', 'book.js')
    
    # Create or update book.js
    with open(book_js_path, 'w', encoding='utf-8') as f:
        f.write("""// Advanced search functionality
window.addEventListener('load', function() {
    // Load terms data
    fetch('terms.json')
        .then(response => response.json())
        .then(terms => {
            // Add custom search function to enhance the built-in search
            window.enhancedSearch = function(searchTerm) {
                // Simple term matching for now
                const results = [];
                
                for (const term in terms) {
                    if (term.toLowerCase().includes(searchTerm.toLowerCase())) {
                        results.push({
                            term: term,
                            definition: terms[term].definition,
                            file: terms[term].file_path
                        });
                    }
                }
                
                return results;
            };
            
            // Add search box enhancement if search is present
            const searchInput = document.querySelector('.search-input');
            if (searchInput) {
                // Add enhanced results below the regular search
                const searchResults = document.querySelector('.search-results');
                if (searchResults) {
                    const enhancedResults = document.createElement('div');
                    enhancedResults.className = 'enhanced-search-results';
                    enhancedResults.style.marginTop = '20px';
                    enhancedResults.innerHTML = '<h3>Term Definitions</h3><div class="results-container"></div>';
                    searchResults.after(enhancedResults);
                    
                    // Hide initially
                    enhancedResults.style.display = 'none';
                    
                    // Add event listener for search input
                    searchInput.addEventListener('input', function(e) {
                        const searchTerm = e.target.value.trim();
                        
                        if (searchTerm.length > 2) {
                            const results = window.enhancedSearch(searchTerm);
                            const container = enhancedResults.querySelector('.results-container');
                            
                            if (results.length > 0) {
                                container.innerHTML = results.map(result => 
                                    `<div class="term-result">
                                        <a href="glossary.html#${result.term.toLowerCase().replace(/ /g, '-')}">
                                            <strong>${result.term}</strong>
                                        </a>
                                        <p>${result.definition.substring(0, 100)}...</p>
                                    </div>`
                                ).join('');
                                
                                enhancedResults.style.display = 'block';
                            } else {
                                enhancedResults.style.display = 'none';
                            }
                        } else {
                            enhancedResults.style.display = 'none';
                        }
                    });
                }
            }
        });
});
""")

def main():
    if len(sys.argv) < 3:
        print("Usage: python enhance_book.py <markdown_dir> <book_dir>")
        sys.exit(1)
    
    md_dir = sys.argv[1]
    book_dir = sys.argv[2]
    
    # Get all markdown files
    md_files = glob.glob(os.path.join(md_dir, "*.md"))
    
    if not md_files:
        print(f"No markdown files found in {md_dir}")
        sys.exit(1)
    
    print(f"Found {len(md_files)} markdown files")
    
    # Extract terms
    terms = extract_terms(md_files)
    print(f"Extracted {len(terms)} terms")
    
    # Create embeddings
    terms = create_embeddings(terms)
    
    # Copy markdown files to book src directory if not already there
    src_dir = os.path.join(book_dir, 'src')
    
    if md_dir != src_dir:
        for file_path in md_files:
            filename = os.path.basename(file_path)
            target_path = os.path.join(src_dir, filename)
            
            with open(file_path, 'r', encoding='utf-8') as src_file:
                with open(target_path, 'w', encoding='utf-8') as dst_file:
                    dst_file.write(src_file.read())
        
        # Update md_files list to point to copied files
        md_files = glob.glob(os.path.join(src_dir, "*.md"))
    
    # Create cross-references
    create_cross_references(terms, md_files)
    
    # Create glossary
    create_glossary(terms, book_dir)
    
    # Update SUMMARY.md
    update_summary(book_dir)
    
    # Enhance search
    enhance_search(book_dir)
    
    print("AI enhancements complete!")

if __name__ == "__main__":
    main()
EOF
    
    # Execute the enhancement script
    log_message "INFO" "Running AI enhancement script"
    python3 "$temp_script" "$MD_OUTPUT_DIR" "$BOOK_DIR"
    
    # Cleanup
    rm -f "$temp_script"
    
    echo -e "${GREEN}AI enhancements applied successfully!${NC}"
    log_message "INFO" "AI enhancements complete"
}

# --- Function: Preview book ---
preview_book() {
    log_message "INFO" "Previewing book locally..."
    
    # Load config values
    source "$CONFIG_FILE"
    
    # Start local server
    echo -e "${CYAN}Starting local preview server...${NC}"
    echo -e "${CYAN}Your book will be available at http://localhost:3000${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop the preview when done.${NC}"
    
    # Launch mdbook serve
    (cd "$BOOK_DIR" && mdbook serve --open)
}

# --- Function: Secure input for password ---
secure_password_input() {
    local prompt=$1
    local var_name=$2
    local password=""
    
    # Prompt for password securely (without echo)
    read -sp "$prompt: " password
    echo ""
    
    # Confirm password
    local confirm_password=""
    read -sp "Confirm $prompt: " confirm_password
    echo ""
    
    # Validate passwords match
    if [ "$password" != "$confirm_password" ]; then
        echo -e "${RED}Passwords do not match. Please try again.${NC}"
        secure_password_input "$prompt" "$var_name"
        return
    fi
    
    # Set the password to the variable name provided
    eval "$var_name='$password'"
}

# --- Function: Configure SSH deployment ---
configure_ssh_deployment() {
    log_message "INFO" "Configuring SSH deployment..."
    
    echo -e "${CYAN}Let's set up deployment to your own server via SSH.${NC}"
    echo -e "${CYAN}This will allow you to host the textbook on your own domain.${NC}"
    echo ""
    
    # Prompt for server information
    read -p "Enter the SSH hostname (e.g., example.com): " SSH_HOST
    read -p "Enter the SSH username: " SSH_USER
    read -p "Enter the SSH port [22]: " SSH_PORT
    SSH_PORT=${SSH_PORT:-22}
    
    # Determine SSH authentication method
    echo -e "${CYAN}SSH Authentication Method:${NC}"
    echo -e "1) SSH Key (More secure, recommended)"
    echo -e "2) Password (Less secure)"
    
    local auth_choice
    read -p "Select authentication method [1]: " auth_choice
    auth_choice=${auth_choice:-1}
    
    local ssh_auth_method=""
    local ssh_key_path=""
    
    case $auth_choice in
        1)
            ssh_auth_method="key"
            echo -e "${CYAN}Using SSH key authentication (recommended).${NC}"
            
            # Check for existing SSH keys
            if [ -f ~/.ssh/id_rsa.pub ]; then
                echo -e "${GREEN}Found existing SSH key at ~/.ssh/id_rsa.pub${NC}"
                ssh_key_path="~/.ssh/id_rsa"
            elif [ -f ~/.ssh/id_ed25519.pub ]; then
                echo -e "${GREEN}Found existing SSH key at ~/.ssh/id_ed25519.pub${NC}"
                ssh_key_path="~/.ssh/id_ed25519"
            else
                # Prompt to create a new key
                echo -e "${YELLOW}No SSH key found. Would you like to create one?${NC}"
                read -p "Create SSH key? (y/n) [y]: " create_key
                create_key=${create_key:-y}
                
                if [[ $create_key =~ ^[Yy]$ ]]; then
                    echo -e "${CYAN}Creating new SSH key...${NC}"
                    ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""
                    ssh_key_path="~/.ssh/id_ed25519"
                    
                    echo -e "${GREEN}Key created successfully!${NC}"
                    echo -e "${YELLOW}Important: You will need to add this public key to your server's authorized_keys file.${NC}"
                    echo -e "${YELLOW}Public key:${NC}"
                    cat ~/.ssh/id_ed25519.pub
                else
                    echo -e "${RED}SSH key authentication selected but no key will be created.${NC}"
                    echo -e "${RED}Please specify the path to your existing SSH private key.${NC}"
                    read -p "Enter path to SSH private key: " ssh_key_path
                fi
            fi
            ;;
        2)
            ssh_auth_method="password"
            echo -e "${YELLOW}Using password authentication (less secure).${NC}"
            echo -e "${YELLOW}Warning: Passwords may be visible in process listings and logs.${NC}"
            
            # Get password securely
            secure_password_input "Enter the SSH password" "SSH_PASS"
            ;;
        *)
            echo -e "${RED}Invalid selection. Using SSH key authentication as default.${NC}"
            ssh_auth_method="key"
            ssh_key_path="~/.ssh/id_rsa"
            ;;
    esac
    
    # Target directory
    read -p "Enter the target directory on the server: " SSH_DIR
    
    # Save deployment info to config (excluding sensitive data)
    echo "DEPLOY_METHOD=ssh" >> "$CONFIG_FILE"
    echo "SSH_HOST=$SSH_HOST" >> "$CONFIG_FILE"
    echo "SSH_USER=$SSH_USER" >> "$CONFIG_FILE"
    echo "SSH_PORT=$SSH_PORT" >> "$CONFIG_FILE"
    echo "SSH_DIR=$SSH_DIR" >> "$CONFIG_FILE"
    echo "SSH_AUTH_METHOD=$ssh_auth_method" >> "$CONFIG_FILE"
    
    if [ "$ssh_auth_method" = "key" ]; then
        echo "SSH_KEY_PATH=$ssh_key_path" >> "$CONFIG_FILE"
    fi
    
    # Validate SSH connection
    echo -e "${CYAN}Validating SSH connection...${NC}"
    
    local connection_success=false
    
    if [ "$ssh_auth_method" = "key" ]; then
        # Test connection with SSH key
        if ssh -i "${ssh_key_path/#\~/$HOME}" -o StrictHostKeyChecking=accept-new -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" "echo 'Connection successful'" &>/dev/null; then
            connection_success=true
        fi
    else
        # Test connection with password
        if command -v sshpass &>/dev/null; then
            if sshpass -f <(echo "$SSH_PASS") ssh -o StrictHostKeyChecking=accept-new -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" "echo 'Connection successful'" &>/dev/null; then
                connection_success=true
            fi
        else
            log_message "ERROR" "sshpass not found. Cannot validate connection with password."
            echo -e "${RED}sshpass not found. Cannot validate connection with password.${NC}"
            echo -e "${RED}Please install sshpass or use SSH key authentication.${NC}"
            
            # Securely remove the password file
            return 1
        fi
    fi
    
    if [ "$connection_success" = "true" ]; then
        echo -e "${GREEN}SSH connection successful!${NC}"
        
        # Create remote directory if it doesn't exist
        if [ "$ssh_auth_method" = "key" ]; then
            ssh -i "${ssh_key_path/#\~/$HOME}" -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" "mkdir -p \"$SSH_DIR\""
        else
            sshpass -f <(echo "$SSH_PASS") ssh -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" "mkdir -p \"$SSH_DIR\""
        fi
        
        log_message "INFO" "SSH deployment configured successfully"
        return 0
    else
        echo -e "${RED}SSH connection failed. Please check your credentials and try again.${NC}"
        log_message "ERROR" "SSH connection failed"
        return 1
    fi
}

# --- Function: Deploy via SSH ---
deploy_via_ssh() {
    log_message "INFO" "Deploying via SSH..."
    
    # Load config values
    source "$CONFIG_FILE"
    
    echo -e "${CYAN}Deploying your textbook via SSH to $SSH_HOST...${NC}"
    
    local deployment_success=false
    
    if [ "$SSH_AUTH_METHOD" = "key" ]; then
        # Deploy using SSH key
        echo -e "${CYAN}Deploying with SSH key authentication...${NC}"
        
        # Expand ~ in key path if present
        local expanded_key_path="${SSH_KEY_PATH/#\~/$HOME}"
        
        rsync -avz -e "ssh -i \"$expanded_key_path\" -p $SSH_PORT" "$BOOK_DIR/book/" "$SSH_USER@$SSH_HOST:$SSH_DIR/"
        if [ $? -eq 0 ]; then
            deployment_success=true
        fi
    else
        # Deploy using password
        echo -e "${CYAN}Deploying with password authentication...${NC}"
        
        # Prompt for password again for security
        secure_password_input "Enter your SSH password" "SSH_PASS"
        
        # Create a temporary password file for sshpass
        local temp_pass_file=$(mktemp)
        echo "$SSH_PASS" > "$temp_pass_file"
        
        # Deploy using rsync over SSH with password
        if command -v sshpass &>/dev/null; then
            sshpass -f "$temp_pass_file" rsync -avz -e "ssh -p $SSH_PORT" "$BOOK_DIR/book/" "$SSH_USER@$SSH_HOST:$SSH_DIR/"
            if [ $? -eq 0 ]; then
                deployment_success=true
            fi
        else
            log_message "ERROR" "sshpass not found. Cannot deploy with password."
            echo -e "${RED}sshpass not found. Cannot deploy with password.${NC}"
            echo -e "${RED}Please install sshpass or use SSH key authentication.${NC}"
        fi
        
        # Securely remove the password file
        shred -u "$temp_pass_file" 2>/dev/null || rm -f "$temp_pass_file"
    fi
    
    if [ "$deployment_success" = "true" ]; then
        echo -e "${GREEN}Deployment successful!${NC}"
        echo -e "${GREEN}Your textbook is now available at: http://$SSH_HOST/$SSH_DIR/${NC}"
        
        # Save deployment timestamp to config
        echo "LAST_DEPLOY=$(date +%s)" >> "$CONFIG_FILE"
        echo "DEPLOY_URL=http://$SSH_HOST/$SSH_DIR/" >> "$CONFIG_FILE"
        
        log_message "INFO" "SSH deployment complete"
    else
        echo -e "${RED}Deployment failed. Please check your connection and try again.${NC}"
        log_message "ERROR" "SSH deployment failed"
    fi
}

# --- Function: Configure Canvas LMS integration ---
configure_canvas_lms() {
    log_message "INFO" "Configuring Canvas LMS integration..."
    
    echo -e "${CYAN}Let's set up deployment to Canvas LMS.${NC}"
    echo -e "${CYAN}This will allow you to publish the textbook directly to your Canvas course.${NC}"
    echo ""
    
    # Prompt for Canvas URL and API key
    read -p "Enter your Canvas LMS URL (e.g., canvas.instructure.com): " CANVAS_URL
    
    # Handle URL format
    if [[ ! $CANVAS_URL == http* ]]; then
        CANVAS_URL="https://$CANVAS_URL"
    fi
    
    # Secure API key input
    secure_api_key_input "Enter your Canvas API key" "CANVAS_API_KEY"
    
    # Check for Python keyring package
    local use_keyring=false
    if python3 -c "import keyring" &>/dev/null; then
        use_keyring=true
        log_message "INFO" "Using system keyring for secure API key storage"
        
        # Store API key in system keyring
        python3 - <<EOF
import keyring
keyring.set_password("art_textbook", "canvas_api", "$CANVAS_API_KEY")
EOF
    else
        log_message "INFO" "Keyring package not available, using memory-only storage for API key"
    fi
    
    # Get course list
    echo -e "${CYAN}Fetching your Canvas courses...${NC}"
    
    # Create temporary Python script for Canvas API
    local temp_script=$(mktemp)
    cat <<EOF > "$temp_script"
import requests
import sys
import json
import os
import keyring

canvas_url = "$CANVAS_URL"
# Get API key from keyring if available
try:
    import keyring
    api_key = keyring.get_password("art_textbook", "canvas_api")
    if not api_key:
        api_key = os.environ.get("CANVAS_API_KEY", "")
except ImportError:
    api_key = os.environ.get("CANVAS_API_KEY", "")

headers = {
    "Authorization": f"Bearer {api_key}"
}

def get_courses():
    """Get list of courses"""
    response = requests.get(f"{canvas_url}/api/v1/courses", headers=headers)
    
    if response.status_code == 200:
        courses = response.json()
        return courses
    else:
        print(f"Error: {response.status_code} - {response.text}")
        sys.exit(1)

def validate_connection():
    """Validate Canvas API connection"""
    try:
        response = requests.get(f"{canvas_url}/api/v1/users/self", headers=headers)
        
        if response.status_code == 200:
            user = response.json()
            print(f"Connected to Canvas as: {user.get('name', 'Unknown')}")
            return True
        else:
            print(f"Error connecting to Canvas: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Exception: {str(e)}")
        return False

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "validate"
    
    if action == "validate":
        success = validate_connection()
        sys.exit(0 if success else 1)
    elif action == "courses":
        courses = get_courses()
        print(json.dumps(courses))
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
EOF
    
    # Make API key available to script
    if [ "$use_keyring" = "false" ]; then
        export CANVAS_API_KEY
    fi
    
    # Validate connection
    echo -e "${CYAN}Validating Canvas LMS connection...${NC}"
    if python3 "$temp_script" validate; then
        echo -e "${GREEN}Connection to Canvas LMS successful!${NC}"
        
        # Get course list
        echo -e "${CYAN}Fetching course list...${NC}"
        COURSES_JSON=$(python3 "$temp_script" courses)
        
        # Parse and display courses
        python3 - <<EOF
import json
import sys

try:
    courses = json.loads('''$COURSES_JSON''')
    
    if len(courses) == 0:
        print("No courses found.")
        sys.exit(0)
    
    print("\nAvailable courses:")
    for i, course in enumerate(courses):
        if course.get('name'):
            print(f"{i+1}. {course.get('name')} (ID: {course.get('id')})")
except Exception as e:
    print(f"Error parsing courses: {str(e)}")
    sys.exit(1)
EOF
        
        # Prompt for course selection
        read -p "Enter the number of the course to deploy to: " COURSE_NUM
        
        # Validate and get course ID
        COURSE_ID=$(python3 - <<EOF
import json

try:
    courses = json.loads('''$COURSES_JSON''')
    course_num = int("$COURSE_NUM") - 1
    
    if 0 <= course_num < len(courses):
        print(courses[course_num]['id'])
    else:
        print("Invalid selection")
except Exception as e:
    print(f"Error: {str(e)}")
EOF
)
        
        if [[ "$COURSE_ID" == "Invalid selection" || "$COURSE_ID" == Error:* ]]; then
            echo -e "${RED}Invalid course selection. Please try again.${NC}"
            log_message "ERROR" "Invalid Canvas course selection"
            
            # Cleanup
            rm -f "$temp_script"
            return 1
        fi
        
        # Save Canvas configuration to config (excluding API key)
        echo "DEPLOY_METHOD=canvas" >> "$CONFIG_FILE"
        echo "CANVAS_URL=$CANVAS_URL" >> "$CONFIG_FILE"
        echo "CANVAS_COURSE_ID=$COURSE_ID" >> "$CONFIG_FILE"
        echo "CANVAS_USE_KEYRING=$use_keyring" >> "$CONFIG_FILE"
        
        log_message "INFO" "Canvas LMS integration configured successfully"
        
        # Cleanup
        rm -f "$temp_script"
        return 0
    else
        echo -e "${RED}Failed to connect to Canvas LMS. Please check your URL and API key.${NC}"
        log_message "ERROR" "Canvas LMS connection failed"
        
        # Cleanup
        rm -f "$temp_script"
        return 1
    fi
}

# --- Function: Deploy to Canvas LMS ---
deploy_to_canvas() {
    log_message "INFO" "Deploying to Canvas LMS..."
    
    # Load config values
    source "$CONFIG_FILE"
    
    echo -e "${CYAN}Preparing to deploy your textbook to Canvas LMS...${NC}"
    
    # Prompt for API key again for security
    read -p "Enter your Canvas API key: " CANVAS_API_KEY
    
    # First, we need to package the book for Canvas
    echo -e "${CYAN}Packaging the textbook for Canvas...${NC}"
    
    # Create a temporary directory for the Canvas package
    local canvas_package_dir="$BASE_DIR/deployments/canvas_$BOOK_ID"
    mkdir -p "$canvas_package_dir"
    
    # Copy the book to the package directory
    cp -r "$BOOK_DIR/book/"* "$canvas_package_dir/"
    
    # Create Canvas configuration files for LTI integration
    cat > "$canvas_package_dir/lti_config.xml" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<cartridge_basiclti_link xmlns="http://www.imsglobal.org/xsd/imslticc_v1p0"
    xmlns:blti = "http://www.imsglobal.org/xsd/imsbasiclti_v1p0"
    xmlns:lticm ="http://www.imsglobal.org/xsd/imslticm_v1p0"
    xmlns:lticp ="http://www.imsglobal.org/xsd/imslticp_v1p0"
    xmlns:xsi = "http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation = "http://www.imsglobal.org/xsd/imslticc_v1p0 http://www.imsglobal.org/xsd/lti/ltiv1p0/imslticc_v1p0.xsd
    http://www.imsglobal.org/xsd/imsbasiclti_v1p0 http://www.imsglobal.org/xsd/lti/ltiv1p0/imsbasiclti_v1p0.xsd
    http://www.imsglobal.org/xsd/imslticm_v1p0 http://www.imsglobal.org/xsd/lti/ltiv1p0/imslticm_v1p0.xsd
    http://www.imsglobal.org/xsd/imslticp_v1p0 http://www.imsglobal.org/xsd/lti/ltiv1p0/imslticp_v1p0.xsd">
    <blti:title>$BOOK_TITLE</blti:title>
    <blti:description>$BOOK_DESCRIPTION</blti:description>
    <blti:launch_url>$SITE_URL/$BOOK_ID/index.html</blti:launch_url>
</cartridge_basiclti_link>
EOF
    
    # Create Canvas module page content
    local module_content="<h1>$BOOK_TITLE</h1>
<p>By: $BOOK_AUTHOR</p>
<p>$BOOK_DESCRIPTION</p>
<p>Access your digital textbook below:</p>
<p><a class='btn btn-primary' href='$SITE_URL/$BOOK_ID/index.html' target='_blank'>Open Textbook</a></p>"
    
    # Create a temporary file with the module content
    local module_content_file="$canvas_package_dir/module_content.html"
    echo "$module_content" > "$module_content_file"
    
    # Now we need to create a module in Canvas and add the content
    echo -e "${CYAN}Creating Canvas module and page...${NC}"
    
    # Create a module
    local module_response=$(curl -s -X POST \
      -H "Authorization: Bearer $CANVAS_API_KEY" \
      -H "Content-Type: application/json" \
      -d "{\"module\":{\"name\":\"$BOOK_TITLE\"}}" \
      "$CANVAS_URL/api/v1/courses/$CANVAS_COURSE_ID/modules")
    
    # Extract module ID
    local module_id=$(echo "$module_response" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
    
    if [ -z "$module_id" ]; then
        echo -e "${RED}Failed to create Canvas module. Check your API key and permissions.${NC}"
        log_message "ERROR" "Failed to create Canvas module"
        return 1
    fi
    
    # Create a page
    local page_response=$(curl -s -X POST \
      -H "Authorization: Bearer $CANVAS_API_KEY" \
      -H "Content-Type: application/json" \
      -d "{\"wiki_page\":{\"title\":\"$BOOK_TITLE\",\"body\":$(echo "$module_content" | python3 -c "import json,sys; print(json.dumps(sys.stdin.read()))")}}" \
      "$CANVAS_URL/api/v1/courses/$CANVAS_COURSE_ID/pages")
    
    # Extract page URL
    local page_url=$(echo "$page_response" | grep -o '"url":"[^"]*"' | head -1 | cut -d'"' -f4)
    
    if [ -z "$page_url" ]; then
        echo -e "${RED}Failed to create Canvas page. Check your API key and permissions.${NC}"
        log_message "ERROR" "Failed to create Canvas page"
        return 1
    fi
    
    # Add the page to the module
    curl -s -X POST \
      -H "Authorization: Bearer $CANVAS_API_KEY" \
      -H "Content-Type: application/json" \
      -d "{\"module_item\":{\"title\":\"$BOOK_TITLE\",\"type\":\"Page\",\"page_url\":\"$page_url\"}}" \
      "$CANVAS_URL/api/v1/courses/$CANVAS_COURSE_ID/modules/$module_id/items" > /dev/null
    
    echo -e "${GREEN}Textbook successfully deployed to Canvas LMS!${NC}"
    echo -e "${GREEN}Your textbook is now available in course $CANVAS_COURSE_ID as module '$BOOK_TITLE'.${NC}"
    
    # Save deployment timestamp and URL to config
    echo "LAST_DEPLOY=$(date +%s)" >> "$CONFIG_FILE"
    echo "DEPLOY_URL=$CANVAS_URL/courses/$CANVAS_COURSE_ID/modules#module_$module_id" >> "$CONFIG_FILE"
    
    log_message "INFO" "Canvas LMS deployment complete"
}

# --- Function: Choose deployment method ---
choose_deployment() {
    log_message "INFO" "Selecting deployment method..."
    
    echo -e "${CYAN}Let's choose how to deploy your textbook.${NC}"
    echo -e "${BOLD}Deployment Options:${NC}"
    echo -e "1) Self-hosted via SSH (Your own server)"
    echo -e "2) Canvas LMS Integration"
    echo -e "3) Skip deployment for now"
    echo ""
    
    local deploy_choice
    read -p "Select deployment method [3]: " deploy_choice
    deploy_choice=${deploy_choice:-3}
    
    case $deploy_choice in
        1)
            if configure_ssh_deployment; then
                deploy_via_ssh
            else
                echo -e "${YELLOW}SSH deployment configuration failed. Skipping deployment.${NC}"
            fi
            ;;
        2)
            if configure_canvas_lms; then
                deploy_to_canvas
            else
                echo -e "${YELLOW}Canvas LMS configuration failed. Skipping deployment.${NC}"
            fi
            ;;
        3)
            echo -e "${YELLOW}Skipping deployment for now. You can deploy later by running this script again.${NC}"
            log_message "INFO" "Deployment skipped"
            ;;
        *)
            echo -e "${RED}Invalid choice. Skipping deployment.${NC}"
            log_message "ERROR" "Invalid deployment choice"
            ;;
    esac
}

# --- Function: Display completion summary ---
display_summary() {
    log_message "INFO" "Displaying summary..."
    
    # Load config values
    source "$CONFIG_FILE"
    
    echo -e "${BOLD}${GREEN}=============================================${NC}"
    echo -e "${BOLD}${GREEN}     Art Textbook Setup Complete!           ${NC}"
    echo -e "${BOLD}${GREEN}=============================================${NC}"
    echo ""
    echo -e "${BOLD}Textbook Information:${NC}"
    echo -e "- Title: ${CYAN}$BOOK_TITLE${NC}"
    echo -e "- Author: ${CYAN}$BOOK_AUTHOR${NC}"
    echo -e "- ID: ${CYAN}$BOOK_ID${NC}"
    echo ""
    echo -e "${BOLD}Local Access:${NC}"
    echo -e "- Book Directory: ${CYAN}$BOOK_DIR${NC}"
    echo -e "- HTML Output: ${CYAN}$BOOK_DIR/book/${NC}"
    echo ""
    
    if [ -n "$DEPLOY_METHOD" ]; then
        echo -e "${BOLD}Deployment:${NC}"
        echo -e "- Method: ${CYAN}$DEPLOY_METHOD${NC}"
        if [ -n "$DEPLOY_URL" ]; then
            echo -e "- URL: ${CYAN}$DEPLOY_URL${NC}"
        fi
        echo ""
    fi
    
    echo -e "${BOLD}Next Steps:${NC}"
    echo -e "1. Preview your textbook with 'cd $BOOK_DIR && mdbook serve --open'"
    echo -e "2. Make manual edits to content in ${CYAN}$BOOK_DIR/src/${NC}"
    echo -e "3. Rebuild with 'cd $BOOK_DIR && mdbook build'"
    
    if [ "$DEPLOY_METHOD" = "ssh" ]; then
        echo -e "4. Redeploy changes with this script or manually with:"
        echo -e "   rsync -avz -e 'ssh -p $SSH_PORT' '$BOOK_DIR/book/' '$SSH_USER@$SSH_HOST:$SSH_DIR/'"
    elif [ "$DEPLOY_METHOD" = "canvas" ]; then
        echo -e "4. Update your Canvas module with the latest content"
    fi
    
    echo ""
    echo -e "${BOLD}${GREEN}=============================================${NC}"
    echo -e "${BOLD}${GREEN}     Thank you for using this platform!      ${NC}"
    echo -e "${BOLD}${GREEN}=============================================${NC}"
    
    log_message "INFO" "Setup complete! Summary displayed."
}

# --- Main function ---
main() {
    # Create or truncate log file
    echo "Art Education Platform Setup - Log started at $(date)" > "$LOG_FILE"
    
    # Display welcome banner
    show_banner
    
    # Get the script state if exists
    local script_state=0
    if [ -f "$CONFIG_FILE" ] && grep -q "SCRIPT_STATE=" "$CONFIG_FILE"; then
        script_state=$(grep "SCRIPT_STATE=" "$CONFIG_FILE" | cut -d= -f2)
    fi
    
    # Execute steps based on state
    case $script_state in
        0)
            # Step 1: Check dependencies
            check_dependencies
            
            # Step 2: Setup environment
            setup_environment
            
            # Save state
            echo "SCRIPT_STATE=1" >> "$CONFIG_FILE"
            
            # Prompt to continue
            echo ""
            read -p "Press Enter to continue to book metadata collection..." 
            main
            ;;
        1)
            # Step 3: Collect book metadata
            collect_book_metadata
            
            # Step 4: Select JPG directory
            select_jpg_directory
            
            # Step 5: Configure OCR
            configure_ocr
            
            # Save state
            echo "SCRIPT_STATE=2" >> "$CONFIG_FILE"
            
            # Prompt to continue
            echo ""
            read -p "Press Enter to continue to image processing..." 
            main
            ;;
        2)
            # Step 6: Process images
            process_images
            
            # Step 7: Generate mdBook
            generate_mdbook
            
            # Step 8: Apply AI enhancements
            apply_ai_enhancements
            
            # Save state
            echo "SCRIPT_STATE=3" >> "$CONFIG_FILE"
            
            # Prompt to continue
            echo ""
            read -p "Press Enter to continue to deployment options..." 
            main
            ;;
        3)
            # Step 9: Preview the book
            preview_book
            
            # Step 10: Choose deployment
            choose_deployment
            
            # Step 11: Display summary
            display_summary
            
            # Mark as complete
            echo "SCRIPT_STATE=4" >> "$CONFIG_FILE"
            echo "SETUP_COMPLETE=true" >> "$CONFIG_FILE"
            echo "COMPLETION_DATE=$(date +'%Y-%m-%d %H:%M:%S')" >> "$CONFIG_FILE"
            ;;
        4)
            # Already completed, ask what to do
            echo -e "${CYAN}The setup process has already been completed.${NC}"
            echo -e "${CYAN}What would you like to do?${NC}"
            echo -e "1) Preview the book"
            echo -e "2) Deploy to a new location"
            echo -e "3) View summary"
            echo -e "4) Start over (new book)"
            echo ""
            
            local choice
            read -p "Select an option [3]: " choice
            choice=${choice:-3}
            
            case $choice in
                1)
                    preview_book
                    ;;
                2)
                    choose_deployment
                    ;;
                3)
                    display_summary
                    ;;
                4)
                    echo -e "${YELLOW}Starting over with a new book setup...${NC}"
                    rm -f "$CONFIG_FILE"
                    main
                    ;;
                *)
                    echo -e "${RED}Invalid choice.${NC}"
                    ;;
            esac
            ;;
        *)
            # Unknown state, start over
            echo -e "${YELLOW}Unknown script state. Starting from the beginning...${NC}"
            rm -f "$CONFIG_FILE"
            main
            ;;
    esac
}

# Call the main function to start the script
main
