#!/bin/bash
# =========================================================
# ARH1000 Art History Textbook Setup Script
# This script is a specialized implementation for the
# ARH1000 Art History course, building on the base
# art-textbook-setup.sh script with course-specific settings.
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
ARH_CONFIG_FILE="$BASE_DIR/config/.arh1000-config"
BASE_SCRIPT="$SCRIPT_DIR/art-textbook-setup.sh"
LOG_FILE="$BASE_DIR/arh1000-textbook-setup.log"

# --- Function: Display banner ---
show_banner() {
    clear
    echo -e "${BOLD}${BLUE}=======================================================${NC}"
    echo -e "${BOLD}${BLUE}       ARH1000 Art History Textbook Setup         ${NC}"
    echo -e "${BOLD}${BLUE}=======================================================${NC}"
    echo -e "${CYAN}This specialized script will:${NC}"
    echo -e "${CYAN}- Set up the ARH1000 Art History textbook digital conversion${NC}"
    echo -e "${CYAN}- Apply course-specific AI enhancements${NC}"
    echo -e "${CYAN}- Configure optimal settings for art history content${NC}"
    echo -e "${CYAN}- Prepare for Canvas LMS integration for ARH1000${NC}"
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

# --- Function: Check that base script exists ---
check_base_script() {
    if [ ! -f "$BASE_SCRIPT" ]; then
        echo -e "${RED}Error: Base script not found at $BASE_SCRIPT${NC}"
        exit 1
    fi
    
    log_message "INFO" "Base script verified at $BASE_SCRIPT"
}

# --- Function: Configure ARH1000 specific settings ---
configure_arh1000_settings() {
    echo -e "${CYAN}Configuring ARH1000-specific settings...${NC}"
    
    # Create or update ARH1000 config file
    echo "ARH1000_VERSION=1.0" > "$ARH_CONFIG_FILE"
    echo "ARH1000_COURSE_NAME=\"Introduction to Art History\"" >> "$ARH_CONFIG_FILE"
    echo "ARH1000_TEMPLATE_ID=arh1000_template" >> "$ARH_CONFIG_FILE"
    echo "ARH1000_GLOSSARY_ENABLED=true" >> "$ARH_CONFIG_FILE"
    echo "ARH1000_AI_ENHANCEMENT_LEVEL=advanced" >> "$ARH_CONFIG_FILE"
    echo "ARH1000_IMAGE_ANALYSIS_ENABLED=true" >> "$ARH_CONFIG_FILE"
    echo "ARH1000_ART_PERIOD_DETECTION=true" >> "$ARH_CONFIG_FILE"
    echo "ARH1000_STYLE_ANALYSIS=true" >> "$ARH_CONFIG_FILE"
    
    # Create Python AI enhancement script specifically for ARH1000
    cat > "$BASE_DIR/scripts/arh1000_ai_enhancements.py" << 'EOF'
#!/usr/bin/env python3
"""
ARH1000-specific AI Enhancements

This script applies specialized AI enhancements for Art History content,
focusing on art period detection, style analysis, and artist attribution.
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.warning("sentence-transformers not available, will use basic enhancements")
    TRANSFORMERS_AVAILABLE = False

class ARH1000Enhancer:
    """Specialized enhancer for ARH1000 Art History content."""
    
    def __init__(self, book_dir):
        self.book_dir = Path(book_dir)
        self.src_dir = self.book_dir / "src"
        self.glossary_terms = {}
        self.art_periods = {
            "Prehistoric": ["cave painting", "petroglyphs", "megaliths"],
            "Ancient Egyptian": ["hieroglyphics", "pharaoh", "pyramid", "sphinx"],
            "Ancient Greek": ["acropolis", "parthenon", "column", "pottery", "sculpture"],
            "Roman": ["pantheon", "colosseum", "forum", "mosaic", "fresco"],
            "Byzantine": ["icon", "mosaic", "hagia sophia", "dome"],
            "Medieval": ["illuminated manuscript", "gothic", "cathedral", "romanesque"],
            "Renaissance": ["perspective", "sfumato", "humanism", "da vinci", "michelangelo"],
            "Baroque": ["dramatic", "chiaroscuro", "bernini", "caravaggio", "rubens"],
            "Neoclassical": ["symmetry", "mythology", "david", "ingres"],
            "Romanticism": ["emotion", "nature", "delacroix", "turner", "friedrich"],
            "Impressionism": ["light", "monet", "renoir", "plein air", "brushwork"],
            "Post-Impressionism": ["cezanne", "van gogh", "gauguin", "seurat"],
            "Cubism": ["picasso", "braque", "geometric", "multiple perspectives"],
            "Surrealism": ["dali", "magritte", "unconscious", "dream"],
            "Abstract Expressionism": ["pollock", "de kooning", "rothko", "gesture"],
            "Pop Art": ["warhol", "lichtenstein", "consumerism", "mass culture"],
            "Contemporary": ["installation", "digital", "conceptual", "multimedia"]
        }
        
        # Initialize AI models if available
        if TRANSFORMERS_AVAILABLE:
            try:
                # Use try-except in case the specific model isn't available
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Loaded sentence transformer model")
            except Exception as e:
                logger.error(f"Error loading model: {e}")
                self.model = None
        else:
            self.model = None
    
    def process_book(self):
        """Process the entire book and apply ARH1000 enhancements."""
        if not self.src_dir.exists():
            logger.error(f"Source directory not found: {self.src_dir}")
            return False
            
        logger.info("Starting ARH1000-specific enhancements")
        
        # Step 1: Extract art terms and create glossary
        self.extract_art_terms()
        
        # Step 2: Detect art periods in each chapter
        self.detect_art_periods()
        
        # Step 3: Create specialized cross-references
        self.create_cross_references()
        
        # Step 4: Generate art period timeline
        self.generate_timeline()
        
        # Step 5: Create and update summary.md with art history context
        self.create_summary()
        
        logger.info("ARH1000 enhancements completed")
        return True
        
    def extract_art_terms(self):
        """Extract specialized art history terms and create a glossary."""
        logger.info("Extracting art history terms")
        
        # Custom art history terms for detection
        art_terms = {
            "chiaroscuro": "A technique using strong contrasts between light and dark",
            "sfumato": "A technique for softening transitions between colors",
            "contrapposto": "A pose where the figure's weight rests on one leg",
            "trompe l'oeil": "Visual illusion in art used to trick the eye",
            "impasto": "A technique using thick application of paint",
            "foreshortening": "A technique to create the illusion of projection or extension in space",
            "iconography": "The study of visual imagery and symbolism in art",
            "vanitas": "A still life with symbols of death and change",
            "tenebrism": "A dramatic illumination style with dark backgrounds",
            "pointillism": "A technique using small, distinct dots of color"
        }
        
        # Process markdown files to find these terms
        md_files = list(self.src_dir.glob("**/*.md"))
        for md_file in md_files:
            try:
                with open(md_file, 'r') as f:
                    content = f.read()
                    
                for term, definition in art_terms.items():
                    if re.search(r'\b' + term + r'\b', content, re.IGNORECASE):
                        self.glossary_terms[term] = definition
                        
            except Exception as e:
                logger.error(f"Error processing file {md_file}: {e}")
        
        # Create glossary.md
        self.create_glossary()
        logger.info(f"Extracted {len(self.glossary_terms)} art history terms")
        
    def create_glossary(self):
        """Create a glossary of art history terms."""
        glossary_path = self.src_dir / "glossary.md"
        
        try:
            with open(glossary_path, 'w') as f:
                f.write("# Art History Glossary\n\n")
                f.write("This glossary provides definitions for key art history terms used throughout this textbook.\n\n")
                
                # Sort terms alphabetically
                sorted_terms = sorted(self.glossary_terms.items())
                
                for term, definition in sorted_terms:
                    f.write(f"## {term.capitalize()}\n\n")
                    f.write(f"{definition}\n\n")
                    
            logger.info(f"Created glossary at {glossary_path}")
        except Exception as e:
            logger.error(f"Error creating glossary: {e}")
            
    def detect_art_periods(self):
        """Detect art periods mentioned in each chapter."""
        logger.info("Detecting art periods in chapters")
        
        # Track detected periods by chapter
        chapter_periods = {}
        
        md_files = list(self.src_dir.glob("chapter*.md"))
        for md_file in md_files:
            chapter_name = md_file.stem
            chapter_periods[chapter_name] = set()
            
            try:
                with open(md_file, 'r') as f:
                    content = f.read().lower()
                    
                # Check for period keywords
                for period, keywords in self.art_periods.items():
                    for keyword in keywords:
                        if keyword.lower() in content:
                            chapter_periods[chapter_name].add(period)
                            
                    # Also check for the period name itself
                    if period.lower() in content:
                        chapter_periods[chapter_name].add(period)
                        
            except Exception as e:
                logger.error(f"Error processing file {md_file}: {e}")
                
        # Save period metadata
        self.save_period_metadata(chapter_periods)
        
    def save_period_metadata(self, chapter_periods):
        """Save detected art period metadata."""
        metadata_dir = self.book_dir / "metadata"
        metadata_dir.mkdir(exist_ok=True)
        
        try:
            period_path = metadata_dir / "art_periods.json"
            with open(period_path, 'w') as f:
                # Convert sets to lists for JSON serialization
                serializable_data = {
                    chapter: list(periods) 
                    for chapter, periods in chapter_periods.items()
                }
                json.dump(serializable_data, f, indent=2)
                
            logger.info(f"Saved art period metadata to {period_path}")
        except Exception as e:
            logger.error(f"Error saving period metadata: {e}")
            
    def create_cross_references(self):
        """Create specialized cross-references between related art concepts."""
        logger.info("Creating art history cross-references")
        
        # Define related concept groups
        concept_groups = {
            "painting_techniques": ["fresco", "oil", "tempera", "watercolor", "acrylic"],
            "architectural_elements": ["column", "arch", "dome", "vault", "buttress"],
            "sculpture_methods": ["carving", "casting", "modeling", "assemblage"],
            "art_movements": ["impressionism", "cubism", "surrealism", "expressionism"]
        }
        
        # Process each markdown file to add cross-references
        md_files = list(self.src_dir.glob("chapter*.md"))
        for md_file in md_files:
            try:
                with open(md_file, 'r') as f:
                    content = f.read()
                
                # For each concept group, add cross-references
                for group_name, concepts in concept_groups.items():
                    for concept in concepts:
                        pattern = r'\b' + concept + r'\b(?![^[]*\])'  # Don't match within links
                        if re.search(pattern, content, re.IGNORECASE):
                            # Find related concepts in this group
                            related = [c for c in concepts if c != concept]
                            
                            # Create cross-reference text
                            if related:
                                ref_text = f"\n\n> **Related concepts:** {', '.join(related)}\n"
                                # Add the cross-reference only once
                                if ref_text not in content:
                                    content += ref_text
                
                # Save updated content
                with open(md_file, 'w') as f:
                    f.write(content)
                    
            except Exception as e:
                logger.error(f"Error adding cross-references to {md_file}: {e}")
                
        logger.info("Cross-references created")
        
    def generate_timeline(self):
        """Generate an art history timeline."""
        logger.info("Generating art history timeline")
        
        timeline_path = self.src_dir / "timeline.md"
        
        try:
            with open(timeline_path, 'w') as f:
                f.write("# Art History Timeline\n\n")
                f.write("This timeline provides an overview of major art periods covered in this textbook.\n\n")
                
                # Art periods with approximate dates
                timeline_data = [
                    ("Prehistoric Art", "30,000 BCE - 2,500 BCE"),
                    ("Ancient Egyptian Art", "3,100 BCE - 30 BCE"),
                    ("Ancient Greek Art", "800 BCE - 31 BCE"),
                    ("Roman Art", "500 BCE - 476 CE"),
                    ("Byzantine Art", "330 CE - 1453 CE"),
                    ("Medieval Art", "500 CE - 1400 CE"),
                    ("Renaissance", "1400 CE - 1600 CE"),
                    ("Baroque", "1600 CE - 1750 CE"),
                    ("Neoclassicism", "1750 CE - 1850 CE"),
                    ("Romanticism", "1800 CE - 1850 CE"),
                    ("Impressionism", "1860 CE - 1900 CE"),
                    ("Post-Impressionism", "1886 CE - 1905 CE"),
                    ("Modernism", "1900 CE - 1970 CE"),
                    ("Contemporary Art", "1970 CE - Present")
                ]
                
                f.write("| Period | Time Range |\n")
                f.write("|--------|------------|\n")
                
                for period, date_range in timeline_data:
                    f.write(f"| {period} | {date_range} |\n")
                    
                f.write("\n## Major Movements in Modern Art\n\n")
                
                modern_movements = [
                    ("Fauvism", "1905 - 1910", "Characterized by bold colors and wild brushwork"),
                    ("Cubism", "1907 - 1914", "Breaking subjects into geometric shapes from multiple viewpoints"),
                    ("Futurism", "1909 - 1944", "Celebrating technology, speed, youth and violence"),
                    ("Dada", "1916 - 1924", "Anti-art movement born from disgust with WWI"),
                    ("Surrealism", "1924 - 1966", "Exploring the unconscious mind and dreams"),
                    ("Abstract Expressionism", "1946 - 1960", "Emotional, spontaneous abstract painting"),
                    ("Pop Art", "1955 - 1975", "Inspired by popular culture and mass media"),
                    ("Minimalism", "1960 - 1975", "Extreme simplification of form"),
                    ("Conceptual Art", "1965 - Present", "Ideas take precedence over traditional aesthetics")
                ]
                
                f.write("| Movement | Period | Description |\n")
                f.write("|----------|--------|-------------|\n")
                
                for movement, period, description in modern_movements:
                    f.write(f"| {movement} | {period} | {description} |\n")
                    
            logger.info(f"Created timeline at {timeline_path}")
        except Exception as e:
            logger.error(f"Error creating timeline: {e}")
            
    def create_summary(self):
        """Create a summary with art history context."""
        logger.info("Creating ARH1000 summary")
        
        summary_path = self.src_dir / "summary.md"
        
        try:
            # Create or update summary
            with open(summary_path, 'w') as f:
                f.write("# Summary\n\n")
                f.write("## Introduction to Art History (ARH1000)\n\n")
                f.write("This textbook provides a comprehensive introduction to art history, covering major periods, styles, techniques, and influential artists throughout human history.\n\n")
                
                f.write("## Course Objectives\n\n")
                f.write("- Develop visual literacy and critical thinking skills for analyzing works of art\n")
                f.write("- Understand the historical and cultural contexts of art production\n")
                f.write("- Identify major art periods, movements, and their defining characteristics\n")
                f.write("- Recognize significant artists and their contributions to art history\n")
                f.write("- Apply appropriate terminology and methodologies for describing and interpreting art\n\n")
                
                f.write("## Book Structure\n\n")
                f.write("This textbook is organized chronologically, moving from prehistoric art through contemporary practices. Each chapter explores key works, artists, and historical contexts.\n\n")
                
                # Add links to key sections
                f.write("## Key Resources\n\n")
                f.write("- [Art History Timeline](timeline.md)\n")
                f.write("- [Art History Glossary](glossary.md)\n")
                
            logger.info(f"Created ARH1000 summary at {summary_path}")
        except Exception as e:
            logger.error(f"Error creating summary: {e}")

def main():
    parser = argparse.ArgumentParser(description="ARH1000-specific AI enhancements")
    parser.add_argument("--book-dir", required=True, help="Path to book directory")
    
    args = parser.parse_args()
    
    enhancer = ARH1000Enhancer(args.book_dir)
    success = enhancer.process_book()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
EOF

    # Make the script executable
    chmod +x "$BASE_DIR/scripts/arh1000_ai_enhancements.py"
    
    log_message "INFO" "ARH1000-specific settings configured"
    log_message "INFO" "Created specialized AI enhancement script for ARH1000"
}

# --- Function: Run the base script with ARH1000 settings ---
run_with_arh1000_settings() {
    echo -e "${CYAN}Running base script with ARH1000 settings...${NC}"
    
    # Create a temporary environment file for ARH1000 default settings
    TMP_ENV_FILE=$(mktemp)
    
    cat > "$TMP_ENV_FILE" << EOF
# ARH1000-specific environment settings
BOOK_TITLE="Introduction to Art History"
BOOK_AUTHOR="ARH1000 Course Team"
BOOK_DESCRIPTION="A comprehensive introduction to the study of art history across major periods and cultures."
DEFAULT_OCR_LANGUAGE="eng"
AI_ENHANCEMENT_LEVEL="advanced"
ENABLE_GLOSSARY=true
ENABLE_TIMELINE=true
ENABLE_IMAGE_ANALYSIS=true
USE_ARH1000_TEMPLATE=true
EOF

    # Run the base script with the ARH1000 settings
    source "$BASE_SCRIPT" --env-file "$TMP_ENV_FILE" --arh1000-mode
    
    # Clean up
    rm -f "$TMP_ENV_FILE"
    
    log_message "INFO" "Base script execution completed"
}

# --- Function: Apply ARH1000-specific AI enhancements ---
apply_arh1000_enhancements() {
    echo -e "${CYAN}Applying ARH1000-specific AI enhancements...${NC}"
    
    # Get book directory from config
    BOOK_DIR=""
    if [ -f "$ARH_CONFIG_FILE" ]; then
        source "$ARH_CONFIG_FILE"
        if [ -n "$BOOK_DIR" ]; then
            # Run the specialized Python enhancement script
            python3 "$BASE_DIR/scripts/arh1000_ai_enhancements.py" --book-dir "$BOOK_DIR"
            
            log_message "INFO" "Applied ARH1000-specific AI enhancements"
        else
            log_message "ERROR" "Book directory not found in configuration"
        fi
    else
        log_message "ERROR" "ARH1000 configuration file not found"
    fi
}

# --- Function: Configure Canvas LMS for ARH1000 ---
configure_arh1000_canvas() {
    echo -e "${CYAN}Configuring Canvas LMS for ARH1000...${NC}"
    
    # Create specialized Canvas module structure for ARH1000
    cat > "$BASE_DIR/scripts/arh1000_canvas_structure.json" << 'EOF'
{
  "module_name": "ARH1000: Introduction to Art History",
  "items": [
    {
      "title": "Course Overview and Timeline",
      "type": "Page",
      "content_path": "summary.md"
    },
    {
      "title": "Art History Timeline",
      "type": "Page",
      "content_path": "timeline.md"
    },
    {
      "title": "Art History Glossary",
      "type": "Page",
      "content_path": "glossary.md" 
    },
    {
      "title": "Weekly Reading Assignments",
      "type": "SubHeader"
    }
  ],
  "quizzes": [
    {
      "title": "Art History Concepts Quiz",
      "questions": 10,
      "points": 20
    },
    {
      "title": "Art Period Recognition",
      "questions": 15,
      "points": 30
    }
  ]
}
EOF

    log_message "INFO" "Created Canvas LMS structure for ARH1000"
    
    # Prompt for ARH1000-specific Canvas settings
    echo -e "${YELLOW}Please enter ARH1000-specific Canvas settings:${NC}"
    
    read -p "ARH1000 Canvas Course ID: " ARH1000_COURSE_ID
    echo "ARH1000_COURSE_ID=\"$ARH1000_COURSE_ID\"" >> "$ARH_CONFIG_FILE"
    
    read -p "ARH1000 Canvas Module Name [ARH1000: Introduction to Art History]: " ARH1000_MODULE_NAME
    ARH1000_MODULE_NAME=${ARH1000_MODULE_NAME:-"ARH1000: Introduction to Art History"}
    echo "ARH1000_MODULE_NAME=\"$ARH1000_MODULE_NAME\"" >> "$ARH_CONFIG_FILE"
    
    log_message "INFO" "ARH1000 Canvas LMS configuration completed"
}

# --- Main function ---
main() {
    # Create or truncate log file
    echo "ARH1000 Art History Textbook Setup - Log started at $(date)" > "$LOG_FILE"
    
    # Display welcome banner
    show_banner
    
    # Step 1: Check that base script exists
    check_base_script
    
    # Step 2: Configure ARH1000-specific settings
    configure_arh1000_settings
    
    # Step 3: Ask if user wants to proceed with setup
    echo -e "${CYAN}The ARH1000-specific settings have been configured.${NC}"
    echo -e "${CYAN}Would you like to proceed with the textbook setup?${NC}"
    echo ""
    
    read -p "Proceed with setup? (y/n) [y]: " proceed
    proceed=${proceed:-y}
    
    if [[ $proceed == "y" || $proceed == "Y" ]]; then
        # Step 4: Run the base script with ARH1000 settings
        run_with_arh1000_settings
        
        # Step 5: Apply ARH1000-specific AI enhancements
        apply_arh1000_enhancements
        
        # Step 6: Configure Canvas LMS for ARH1000
        configure_arh1000_canvas
        
        # Step 7: Final message
        echo -e "${BOLD}${GREEN}=======================================================${NC}"
        echo -e "${BOLD}${GREEN}     ARH1000 Textbook Setup Complete!                 ${NC}"
        echo -e "${BOLD}${GREEN}=======================================================${NC}"
        echo -e "${CYAN}Your ARH1000 textbook has been set up with specialized${NC}"
        echo -e "${CYAN}art history enhancements and Canvas LMS integration.${NC}"
        echo -e "${CYAN}For support or feedback, please contact the Art Education Platform team.${NC}"
        echo -e "${BOLD}${GREEN}=======================================================${NC}"
    else
        echo -e "${YELLOW}Setup canceled. You can run this script again at any time.${NC}"
    fi
}

# Call the main function to start the script
main
