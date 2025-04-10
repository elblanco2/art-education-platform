#!/usr/bin/env python3
"""
Text Processor for Art Book OCR Output

This module handles the cleaning, structuring, and conversion of OCR output
to properly formatted Markdown content for mdBook.
"""

import re
import logging
import unicodedata
from typing import List, Dict, Tuple, Optional
import html
from pathlib import Path
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class TextProcessor:
    """
    Processes OCR text output and converts it to structured Markdown.
    """

    def __init__(self, config: Dict = None):
        """
        Initialize the text processor with configuration.
        
        Args:
            config: Dictionary containing text processing configuration
        """
        self.config = config or {}
        self.output_dir = Path(self.config.get("MD_OUTPUT_DIR", "./markdown_output"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Common OCR errors and their corrections
        self.common_errors = {
            # Typography fixes
            "''": '"',
            "``": '"',
            "—": "-",
            "–": "-",
            # Common OCR errors
            "rn": "m",
            "cl": "d",
            "I-l": "H",
            # Add more based on specific OCR issues...
        }

    def sanitize_text(self, text: str) -> str:
        """
        Sanitize raw OCR text by removing control characters,
        normalizing whitespace, and escaping HTML.
        
        Args:
            text: Raw OCR text
            
        Returns:
            Sanitized text
        """
        if not text:
            return ""
            
        # Remove control characters
        text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C")
        
        # HTML escape to prevent injection
        text = html.escape(text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'^\s+|\s+$', '', text, flags=re.MULTILINE)
        
        # Fix common OCR errors
        for error, correction in self.common_errors.items():
            text = text.replace(error, correction)
            
        return text
        
    def extract_structure(self, text: str) -> Dict:
        """
        Extract structural elements from text.
        
        Args:
            text: Sanitized OCR text
            
        Returns:
            Dictionary with identified structural elements
        """
        # Initialize structure dictionary
        structure = {
            "title": "",
            "headings": [],
            "paragraphs": [],
            "chapters": [],
            "figures": [],
            "tables": [],
        }
        
        # Extract potential title (first line that looks like a title)
        lines = text.split('\n')
        if lines and len(lines[0]) < 100:  # Title usually short
            structure["title"] = lines[0].strip()
            lines = lines[1:]  # Remove title from content
        
        # Extract headings (lines that are shorter and possibly all caps)
        current_chapter = None
        current_section = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Potential heading detection
            if (len(line) < 80 and (line.isupper() or 
                re.match(r'^[0-9]+\..*$', line) or 
                re.match(r'^Chapter [0-9]+.*$', line, re.IGNORECASE))):
                
                # Save current section if exists
                if current_section:
                    if current_chapter:
                        structure["chapters"].append({
                            "heading": current_chapter,
                            "content": '\n\n'.join(current_section)
                        })
                    else:
                        structure["paragraphs"].extend(current_section)
                    current_section = []
                
                structure["headings"].append(line)
                current_chapter = line
            else:
                current_section.append(line)
        
        # Add the last section
        if current_section:
            if current_chapter:
                structure["chapters"].append({
                    "heading": current_chapter,
                    "content": '\n\n'.join(current_section)
                })
            else:
                structure["paragraphs"].extend(current_section)
        
        # Extract potential figure captions
        figure_pattern = r'(?:Figure|Fig\.)\s+[0-9]+[.:]\s*(.*?)(?:\.|$)'
        structure["figures"] = re.findall(figure_pattern, text, re.IGNORECASE)
        
        # Extract potential table captions
        table_pattern = r'(?:Table)\s+[0-9]+[.:]\s*(.*?)(?:\.|$)'
        structure["tables"] = re.findall(table_pattern, text, re.IGNORECASE)
        
        return structure
        
    def convert_to_markdown(self, structure: Dict) -> str:
        """
        Convert extracted structure to Markdown format.
        
        Args:
            structure: Dictionary with structural elements
            
        Returns:
            Formatted Markdown text
        """
        markdown = []
        
        # Add title
        if structure["title"]:
            markdown.append(f"# {structure['title']}\n")
        
        # Process chapters
        for chapter in structure["chapters"]:
            heading = chapter["heading"]
            content = chapter["content"]
            
            # Determine heading level by context
            if re.match(r'^Chapter', heading, re.IGNORECASE):
                markdown.append(f"## {heading}\n")
            elif re.match(r'^[0-9]+\.', heading):
                markdown.append(f"### {heading}\n")
            elif heading.isupper():
                markdown.append(f"### {heading.title()}\n")
            else:
                markdown.append(f"### {heading}\n")
                
            # Add content paragraphs
            markdown.append(content)
            markdown.append("\n")
        
        # Process any leftover paragraphs
        if structure["paragraphs"]:
            markdown.append("\n".join(structure["paragraphs"]))
        
        # Create a clean markdown text
        md_text = "\n\n".join(markdown)
        
        # Format figures
        md_text = re.sub(
            r'(Figure|Fig\.)\s+([0-9]+)[.:]\s*(.*?)(?:\.|$)', 
            r'**Figure \2:** \3', 
            md_text, 
            flags=re.IGNORECASE
        )
        
        # Format tables
        md_text = re.sub(
            r'(Table)\s+([0-9]+)[.:]\s*(.*?)(?:\.|$)', 
            r'**Table \2:** \3', 
            md_text, 
            flags=re.IGNORECASE
        )
        
        return md_text
    
    def process_text(self, text: str, filename: str = None) -> Tuple[str, str]:
        """
        Process OCR text: sanitize, extract structure, convert to markdown.
        
        Args:
            text: Raw OCR text
            filename: Filename to use for output
            
        Returns:
            Tuple of (markdown_text, output_path)
        """
        logger.info(f"Processing text{'for ' + filename if filename else ''}")
        
        # Sanitize the text
        clean_text = self.sanitize_text(text)
        
        # Extract structure
        structure = self.extract_structure(clean_text)
        
        # Convert to markdown
        markdown = self.convert_to_markdown(structure)
        
        # Save to file if filename provided
        output_path = None
        if filename:
            # Create safe filename
            safe_filename = re.sub(r'[^\w\-\.]', '_', filename)
            if not safe_filename.endswith('.md'):
                safe_filename += '.md'
                
            output_path = self.output_dir / safe_filename
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown)
            logger.info(f"Saved markdown to {output_path}")
        
        return markdown, str(output_path) if output_path else ""
    
    def batch_process(self, text_dict: Dict[str, str]) -> Dict[str, str]:
        """
        Process multiple text entries and convert to markdown.
        
        Args:
            text_dict: Dictionary mapping filenames to OCR text
            
        Returns:
            Dictionary mapping filenames to output paths
        """
        results = {}
        
        for filename, text in text_dict.items():
            try:
                basename = Path(filename).stem
                _, output_path = self.process_text(text, f"{basename}.md")
                results[filename] = output_path
            except Exception as e:
                logger.error(f"Failed to process {filename}: {e}")
                results[filename] = f"ERROR: {str(e)}"
                
        return results
