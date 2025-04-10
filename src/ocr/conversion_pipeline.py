#!/usr/bin/env python3
"""
Art Book Conversion Pipeline

Coordinates the OCR image processing and text processing
to convert art book images to mdBook compatible markdown.
"""

import os
import logging
import json
from pathlib import Path
from typing import List, Dict, Optional
import argparse
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

from .image_processor import ImageProcessor
from .text_processor import TextProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ConversionPipeline:
    """
    Coordinates the entire conversion process from images to mdBook.
    """

    def __init__(self, config_path: str = None):
        """
        Initialize the conversion pipeline with configuration.
        
        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize processors
        self.image_processor = ImageProcessor(self.config)
        self.text_processor = TextProcessor(self.config)
        
        # Create output directories
        self.output_dir = Path(self.config.get("MDBOOK_OUTPUT_DIR", "./mdbook_output"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Book metadata
        self.book_title = self.config.get("BOOK_TITLE", "Art History Textbook")
        self.book_author = self.config.get("BOOK_AUTHOR", "Lucas Blanco")
        self.book_description = self.config.get("BOOK_DESCRIPTION", "")
        
        # Set up processing threads
        self.max_threads = int(self.config.get("OCR_THREADS", 4))
        
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """
        Load configuration from file or environment.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        config = {}
        
        # Default configuration
        config.update({
            "OCR_LANGUAGE": "eng",
            "OCR_DPI": 300,
            "OCR_THREADS": 4,
            "MDBOOK_OUTPUT_DIR": "./mdbook_output",
            "MD_OUTPUT_DIR": "./markdown_output",
            "BOOK_TITLE": "Art History Textbook",
            "BOOK_AUTHOR": "Lucas Blanco",
            "BOOK_DESCRIPTION": "Complete online textbook for ARH1000",
        })
        
        # Load from file if provided
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    file_config = json.load(f)
                    config.update(file_config)
                logger.info(f"Loaded configuration from {config_path}")
            except Exception as e:
                logger.error(f"Error loading configuration: {e}")
        
        # Load from environment (overrides file)
        for key in config.keys():
            env_value = os.environ.get(key)
            if env_value:
                config[key] = env_value
                
        return config
    
    def process_file(self, file_path: str) -> Dict:
        """
        Process a single file through the pipeline.
        
        Args:
            file_path: Path to the input file
            
        Returns:
            Processing result dictionary
        """
        try:
            # Process image to extract text
            raw_text, processed_image = self.image_processor.process_image_file(
                file_path, save_processed=True
            )
            
            # Process text to markdown
            markdown, md_path = self.text_processor.process_text(
                raw_text, Path(file_path).stem + ".md"
            )
            
            return {
                "input_file": file_path,
                "processed_image": processed_image,
                "markdown_file": md_path,
                "status": "success",
                "error": None,
            }
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return {
                "input_file": file_path,
                "processed_image": None,
                "markdown_file": None,
                "status": "error",
                "error": str(e),
            }
    
    def batch_process(self, input_dir: str, recursive: bool = False) -> List[Dict]:
        """
        Process all files in a directory.
        
        Args:
            input_dir: Directory containing input files
            recursive: Whether to search subdirectories
            
        Returns:
            List of processing result dictionaries
        """
        input_path = Path(input_dir)
        if not input_path.is_dir():
            raise ValueError(f"Not a valid directory: {input_dir}")
            
        logger.info(f"Starting batch processing from {input_dir}")
        start_time = time.time()
        
        # Collect all eligible files
        files_to_process = []
        pattern = "**/*" if recursive else "*"
        
        for file_path in input_path.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in self.image_processor.allowed_extensions:
                files_to_process.append(str(file_path))
                
        logger.info(f"Found {len(files_to_process)} files to process")
        
        # Process files in parallel
        results = []
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            future_to_file = {
                executor.submit(self.process_file, file_path): file_path
                for file_path in files_to_process
            }
            
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(f"Processed {file_path}: {result['status']}")
                except Exception as e:
                    logger.error(f"Error in worker processing {file_path}: {e}")
                    results.append({
                        "input_file": file_path,
                        "status": "error",
                        "error": str(e),
                    })
        
        elapsed_time = time.time() - start_time
        success_count = sum(1 for r in results if r["status"] == "success")
        logger.info(f"Batch processing complete. {success_count}/{len(results)} files processed successfully in {elapsed_time:.2f} seconds")
        
        return results
        
    def create_mdbook_structure(self, results: List[Dict]) -> str:
        """
        Create the mdBook directory structure and files.
        
        Args:
            results: List of processing results
            
        Returns:
            Path to the mdBook directory
        """
        # Create mdBook directory structure
        mdbook_dir = self.output_dir / "arh1000-textbook"
        src_dir = mdbook_dir / "src"
        
        mdbook_dir.mkdir(exist_ok=True)
        src_dir.mkdir(exist_ok=True)
        
        logger.info(f"Creating mdBook structure in {mdbook_dir}")
        
        # Create book.toml
        book_toml = f"""[book]
title = "{self.book_title}"
authors = ["{self.book_author}"]
description = "{self.book_description}"
language = "en"

[output.html]
additional-css = ["custom.css"]
additional-js = ["custom.js", "chat-integration.js"]
git-repository-url = "https://lucasblanco.com/ed/arh1000/fulltext"
edit-url-template = "https://lucasblanco.com/ed/arh1000/admin/edit/{{path}}"
"""
        
        with open(mdbook_dir / "book.toml", "w") as f:
            f.write(book_toml)
            
        # Create custom CSS
        custom_css = """/* Custom CSS for Art History Textbook */
:root {
    --sidebar-width: 300px;
    --page-padding: 15px;
    --content-max-width: 800px;
    --menu-bar-height: 50px;
    --primary-color: #5c8a9d;
    --secondary-color: #264b5d;
}

/* Improved readability */
.content {
    font-family: 'Merriweather', serif;
    line-height: 1.7;
    font-size: 16px;
}

/* Better heading styles */
.content h1, .content h2, .content h3 {
    font-family: 'Montserrat', sans-serif;
    margin-top: 1.5em;
    color: var(--secondary-color);
}

/* Image enhancements */
.content img {
    max-width: 100%;
    border-radius: 5px;
    box-shadow: 0 3px 8px rgba(0,0,0,0.15);
    margin: 1.5em 0;
}

/* Figure captions */
.content img + em {
    display: block;
    text-align: center;
    font-style: italic;
    color: #555;
    margin-top: -5px;
    font-size: 0.9em;
}

/* Chat interface container */
.chat-container {
    position: fixed;
    bottom: 20px;
    right: 20px;
    z-index: 1000;
}
"""
        
        with open(mdbook_dir / "custom.css", "w") as f:
            f.write(custom_css)
            
        # Create JavaScript for chat integration
        chat_js = """// Chat Integration Script
document.addEventListener('DOMContentLoaded', function() {
    // Create chat button
    const chatButton = document.createElement('button');
    chatButton.id = 'chat-button';
    chatButton.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24"><path fill="currentColor" d="M20,2H4A2,2 0 0,0 2,4V22L6,18H20A2,2 0 0,0 22,16V4A2,2 0 0,0 20,2M20,16H6L4,18V4H20"></path></svg>';
    chatButton.className = 'chat-button';
    
    // Create chat container
    const chatContainer = document.createElement('div');
    chatContainer.className = 'chat-container';
    chatContainer.appendChild(chatButton);
    
    // Create chat window (initially hidden)
    const chatWindow = document.createElement('div');
    chatWindow.className = 'chat-window hidden';
    chatWindow.innerHTML = `
        <div class="chat-header">
            <h3>Art History Assistant</h3>
            <button class="close-chat">×</button>
        </div>
        <div class="chat-messages"></div>
        <div class="chat-input">
            <textarea placeholder="Ask about this page..."></textarea>
            <button class="send-message">Send</button>
        </div>
    `;
    chatContainer.appendChild(chatWindow);
    
    // Add to page
    document.body.appendChild(chatContainer);
    
    // Style elements
    const style = document.createElement('style');
    style.textContent = `
        .chat-button {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: var(--primary-color);
            color: white;
            border: none;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
        }
        .chat-window {
            position: fixed;
            bottom: 80px;
            right: 20px;
            width: 350px;
            height: 500px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 5px 25px rgba(0,0,0,0.2);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            transition: all 0.3s ease;
        }
        .chat-window.hidden {
            opacity: 0;
            transform: translateY(20px);
            pointer-events: none;
        }
        .chat-header {
            padding: 15px;
            background: var(--primary-color);
            color: white;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .chat-header h3 {
            margin: 0;
            font-size: 16px;
        }
        .close-chat {
            background: none;
            border: none;
            color: white;
            font-size: 24px;
            cursor: pointer;
        }
        .chat-messages {
            flex: 1;
            padding: 15px;
            overflow-y: auto;
        }
        .chat-input {
            padding: 15px;
            border-top: 1px solid #eee;
            display: flex;
        }
        .chat-input textarea {
            flex: 1;
            border: 1px solid #ddd;
            border-radius: 20px;
            padding: 10px 15px;
            font-family: inherit;
            resize: none;
            height: 40px;
            outline: none;
        }
        .send-message {
            background: var(--primary-color);
            color: white;
            border: none;
            border-radius: 20px;
            padding: 0 15px;
            margin-left: 10px;
            cursor: pointer;
        }
    `;
    document.head.appendChild(style);
    
    // Add event listeners
    chatButton.addEventListener('click', function() {
        chatWindow.classList.toggle('hidden');
    });
    
    document.querySelector('.close-chat').addEventListener('click', function() {
        chatWindow.classList.add('hidden');
    });
    
    // Function to be implemented: Connect with Fast Agent API
    function initializeFastAgent() {
        // This will be implemented when Fast Agent integration is ready
        console.log('Fast Agent integration will be initialized here');
    }
    
    // Initialize when page is fully loaded
    window.addEventListener('load', initializeFastAgent);
});
"""
        
        with open(mdbook_dir / "chat-integration.js", "w") as f:
            f.write(chat_js)
            
        # Copy markdown files to src directory
        chapter_files = []
        for result in results:
            if result["status"] == "success" and result["markdown_file"]:
                md_path = Path(result["markdown_file"])
                if md_path.exists():
                    # Copy to src directory with clean numbered filename
                    original_name = md_path.stem
                    new_filename = f"chapter_{len(chapter_files) + 1:02d}_{original_name}.md"
                    new_path = src_dir / new_filename
                    
                    with open(md_path, 'r', encoding='utf-8') as source_file:
                        content = source_file.read()
                        
                    with open(new_path, 'w', encoding='utf-8') as dest_file:
                        dest_file.write(content)
                        
                    chapter_files.append(new_path)
                    logger.info(f"Copied {md_path} to {new_path}")
        
        # Create SUMMARY.md
        summary_content = "# Summary\n\n"
        summary_content += f"[Introduction]({chapter_files[0].name if chapter_files else 'README.md'})\n\n"
        
        # Add chapters to summary
        for chapter_path in chapter_files:
            chapter_name = chapter_path.stem.replace("chapter_", "").replace("_", " ").title()
            chapter_name = re.sub(r'^[0-9]+ ', '', chapter_name)
            summary_content += f"- [{chapter_name}]({chapter_path.name})\n"
            
        # Add placeholder for further content
        summary_content += "\n[Glossary](glossary.md)\n"
        summary_content += "[References](references.md)\n"
        
        with open(src_dir / "SUMMARY.md", "w") as f:
            f.write(summary_content)
            
        # Create basic README.md if not present
        if not (src_dir / "README.md").exists():
            with open(src_dir / "README.md", "w") as f:
                f.write(f"# {self.book_title}\n\n")
                f.write(f"{self.book_description}\n\n")
                f.write("Welcome to the online edition of this art history textbook. ")
                f.write("Use the navigation panel on the left to browse chapters.\n\n")
                f.write("For any questions, you can use the chat assistant available on each page.\n")
                
        # Create placeholder files
        for placeholder in ["glossary.md", "references.md"]:
            with open(src_dir / placeholder, "w") as f:
                title = placeholder.replace(".md", "").title()
                f.write(f"# {title}\n\n")
                f.write("This section is under development.\n")
        
        return str(mdbook_dir)


def main():
    """
    Main function to run the conversion pipeline.
    """
    parser = argparse.ArgumentParser(description="Art Book Conversion Pipeline")
    parser.add_argument("input_dir", help="Directory containing book images")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--recursive", action="store_true", help="Search subdirectories")
    args = parser.parse_args()
    
    try:
        # Initialize the pipeline
        pipeline = ConversionPipeline(args.config)
        
        # Process files
        results = pipeline.batch_process(args.input_dir, args.recursive)
        
        # Create mdBook structure
        mdbook_path = pipeline.create_mdbook_structure(results)
        
        logger.info(f"Conversion complete. mdBook created at {mdbook_path}")
        logger.info(f"To build the book, navigate to {mdbook_path} and run 'mdbook build'")
        
        # Summary statistics
        success_count = sum(1 for r in results if r["status"] == "success")
        logger.info(f"Processed {len(results)} files with {success_count} successes and {len(results) - success_count} failures")
        
    except Exception as e:
        logger.error(f"Error in conversion pipeline: {e}")
        return 1
        
    return 0


if __name__ == "__main__":
    exit(main())
