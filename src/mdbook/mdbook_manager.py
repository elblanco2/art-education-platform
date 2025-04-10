#!/usr/bin/env python3
"""
mdBook Manager

Manages mdBook instances, including configuration, customization,
build processes, and security measures.
"""

import os
import logging
import json
import subprocess
import shutil
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import tempfile
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class MdBookManager:
    """
    Manages mdBook instances for the art education platform.
    Includes security measures for safe operations.
    """

    def __init__(self, config: Dict = None):
        """
        Initialize the mdBook manager with configuration.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.validate_paths()
        
        # Check if mdbook is installed
        self.mdbook_installed = self._check_mdbook_installed()
        if not self.mdbook_installed:
            logger.warning("mdBook is not installed or not in PATH. Some functions will be limited.")
    
    def validate_paths(self):
        """
        Validate and sanitize paths in the configuration.
        Creates necessary directories.
        """
        # Ensure root directory exists
        root_dir = Path(self.config.get("ROOT_DIR", "./mdbooks"))
        root_dir.mkdir(parents=True, exist_ok=True)
        self.config["ROOT_DIR"] = str(root_dir)
        
        # Validate book paths
        if "BOOK_PATHS" in self.config:
            sanitized_paths = {}
            for book_id, path in self.config["BOOK_PATHS"].items():
                # Sanitize book ID to prevent path traversal
                safe_id = re.sub(r'[^a-zA-Z0-9_-]', '', book_id)
                
                # Ensure path is within root directory
                book_path = Path(path)
                if not str(book_path).startswith(str(root_dir)):
                    book_path = root_dir / safe_id
                
                sanitized_paths[safe_id] = str(book_path)
            self.config["BOOK_PATHS"] = sanitized_paths
    
    def _check_mdbook_installed(self) -> bool:
        """
        Check if mdbook is installed and available.
        
        Returns:
            True if mdbook is installed, False otherwise
        """
        try:
            result = subprocess.run(
                ["mdbook", "--version"], 
                capture_output=True, 
                text=True, 
                check=False
            )
            if result.returncode == 0:
                logger.info(f"mdBook is installed: {result.stdout.strip()}")
                return True
            else:
                logger.warning("mdBook command failed")
                return False
        except FileNotFoundError:
            logger.warning("mdBook is not installed")
            return False
            
    def create_book(self, book_id: str, title: str, author: str, description: str) -> str:
        """
        Create a new mdBook instance with secure defaults.
        
        Args:
            book_id: Unique identifier for the book
            title: Book title
            author: Book author
            description: Book description
            
        Returns:
            Path to the created book
        """
        # Sanitize book ID
        safe_id = re.sub(r'[^a-zA-Z0-9_-]', '', book_id)
        if safe_id != book_id:
            logger.warning(f"Book ID sanitized from '{book_id}' to '{safe_id}'")
            
        # Create book directory
        root_dir = Path(self.config.get("ROOT_DIR", "./mdbooks"))
        book_dir = root_dir / safe_id
        
        if book_dir.exists():
            logger.warning(f"Book directory already exists: {book_dir}")
            # Generate a unique name to avoid overwriting
            hash_suffix = hashlib.md5(str(book_dir).encode()).hexdigest()[:8]
            safe_id = f"{safe_id}_{hash_suffix}"
            book_dir = root_dir / safe_id
            logger.info(f"Using alternative directory: {book_dir}")
            
        book_dir.mkdir(parents=True, exist_ok=True)
        src_dir = book_dir / "src"
        src_dir.mkdir(exist_ok=True)
        
        # If mdbook is installed, use it to initialize
        if self.mdbook_installed:
            try:
                # Create a temporary directory to avoid output going to stdout
                with tempfile.TemporaryDirectory() as temp_dir:
                    subprocess.run(
                        ["mdbook", "init", "--force"],
                        cwd=str(book_dir),
                        capture_output=True,
                        check=True
                    )
                logger.info(f"Created mdBook at {book_dir} using mdbook command")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to create mdBook: {e}")
                logger.error(f"stdout: {e.stdout}, stderr: {e.stderr}")
                # Fall back to manual creation
                self._create_book_manually(book_dir, title, author, description)
        else:
            # Create book manually
            self._create_book_manually(book_dir, title, author, description)
            
        # Update config to track this book
        if "BOOK_PATHS" not in self.config:
            self.config["BOOK_PATHS"] = {}
        self.config["BOOK_PATHS"][safe_id] = str(book_dir)
        
        return str(book_dir)
        
    def _create_book_manually(self, book_dir: Path, title: str, author: str, description: str):
        """
        Create an mdBook structure manually when mdbook command is not available.
        
        Args:
            book_dir: Book directory path
            title: Book title
            author: Book author
            description: Book description
        """
        logger.info(f"Creating mdBook structure manually at {book_dir}")
        
        # Create src directory if not exists
        src_dir = book_dir / "src"
        src_dir.mkdir(exist_ok=True)
        
        # Create basic book.toml
        book_toml = f"""[book]
title = "{title}"
authors = ["{author}"]
description = "{description}"
language = "en"

[output.html]
additional-css = ["custom.css"]
additional-js = ["custom.js", "chat-integration.js"]
"""
        
        with open(book_dir / "book.toml", "w") as f:
            f.write(book_toml)
            
        # Create SUMMARY.md
        summary = "# Summary\n\n[Introduction](README.md)\n"
        with open(src_dir / "SUMMARY.md", "w") as f:
            f.write(summary)
            
        # Create README.md
        readme = f"# {title}\n\n{description}\n"
        with open(src_dir / "README.md", "w") as f:
            f.write(readme)
            
        # Create empty CSS file
        with open(book_dir / "custom.css", "w") as f:
            f.write("/* Custom styles for the book */\n")
            
        logger.info(f"Created basic mdBook structure at {book_dir}")
    
    def build_book(self, book_id: str, output_dir: Optional[str] = None) -> Tuple[bool, str]:
        """
        Build an mdBook to generate HTML output.
        
        Args:
            book_id: Book identifier
            output_dir: Optional custom output directory
            
        Returns:
            Tuple of (success, output_path)
        """
        # Sanitize book ID and verify it exists in our config
        safe_id = re.sub(r'[^a-zA-Z0-9_-]', '', book_id)
        if "BOOK_PATHS" not in self.config or safe_id not in self.config["BOOK_PATHS"]:
            logger.error(f"Book ID not found: {safe_id}")
            return False, ""
            
        book_dir = Path(self.config["BOOK_PATHS"][safe_id])
        if not book_dir.exists():
            logger.error(f"Book directory does not exist: {book_dir}")
            return False, ""
            
        # Set output directory
        if output_dir:
            # Sanitize output directory - must be within our root dir for security
            output_path = Path(output_dir)
            root_dir = Path(self.config.get("ROOT_DIR", "./mdbooks"))
            if not str(output_path).startswith(str(root_dir)):
                output_path = root_dir / "build" / safe_id
                logger.warning(f"Output directory outside of root, using: {output_path}")
        else:
            # Default output directory
            output_path = book_dir / "book"
            
        # Create output directory
        output_path.mkdir(parents=True, exist_ok=True)
        
        # If mdbook is installed, use it to build
        if self.mdbook_installed:
            try:
                # Build the book
                build_result = subprocess.run(
                    ["mdbook", "build", "--dest-dir", str(output_path)],
                    cwd=str(book_dir),
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if build_result.returncode == 0:
                    logger.info(f"Successfully built book to {output_path}")
                    return True, str(output_path)
                else:
                    logger.error(f"Failed to build book: {build_result.stderr}")
                    return False, ""
            except Exception as e:
                logger.error(f"Error building book: {e}")
                return False, ""
        else:
            # If mdbook is not installed, we can't build the book
            logger.error("Cannot build book - mdbook is not installed")
            return False, ""
    
    def update_theme(self, book_id: str, theme_options: Dict) -> bool:
        """
        Update the theme for an mdBook.
        
        Args:
            book_id: Book identifier
            theme_options: Dictionary of theme options
            
        Returns:
            True if successful, False otherwise
        """
        # Sanitize book ID and verify it exists
        safe_id = re.sub(r'[^a-zA-Z0-9_-]', '', book_id)
        if "BOOK_PATHS" not in self.config or safe_id not in self.config["BOOK_PATHS"]:
            logger.error(f"Book ID not found: {safe_id}")
            return False
            
        book_dir = Path(self.config["BOOK_PATHS"][safe_id])
        if not book_dir.exists():
            logger.error(f"Book directory does not exist: {book_dir}")
            return False
            
        # Update book.toml with theme options
        book_toml_path = book_dir / "book.toml"
        if not book_toml_path.exists():
            logger.error(f"book.toml not found at {book_toml_path}")
            return False
            
        try:
            # Read existing content
            with open(book_toml_path, 'r') as f:
                content = f.read()
                
            # Parse and modify content (using simple string manipulation to avoid dependencies)
            output_html_section = False
            new_lines = []
            added_theme_options = False
            
            for line in content.split('\n'):
                if line.strip() == "[output.html]":
                    output_html_section = True
                    new_lines.append(line)
                    
                    # Add theme options
                    for key, value in theme_options.items():
                        # Sanitize key to prevent injection
                        safe_key = re.sub(r'[^a-zA-Z0-9_-]', '', key)
                        if isinstance(value, str):
                            new_lines.append(f'{safe_key} = "{value}"')
                        else:
                            new_lines.append(f'{safe_key} = {value}')
                    added_theme_options = True
                elif line.strip().startswith('[') and line.strip().endswith(']'):
                    output_html_section = False
                    new_lines.append(line)
                elif output_html_section and any(line.strip().startswith(f"{key} =") for key in theme_options):
                    # Skip existing options that we're replacing
                    continue
                else:
                    new_lines.append(line)
                    
            # If [output.html] section not found, add it
            if not added_theme_options:
                new_lines.append("\n[output.html]")
                for key, value in theme_options.items():
                    safe_key = re.sub(r'[^a-zA-Z0-9_-]', '', key)
                    if isinstance(value, str):
                        new_lines.append(f'{safe_key} = "{value}"')
                    else:
                        new_lines.append(f'{safe_key} = {value}')
                        
            # Write updated content
            with open(book_toml_path, 'w') as f:
                f.write('\n'.join(new_lines))
                
            logger.info(f"Updated theme options for {book_id}")
            return True
                
        except Exception as e:
            logger.error(f"Error updating theme: {e}")
            return False
    
    def update_css(self, book_id: str, css_content: str) -> bool:
        """
        Update custom CSS for an mdBook.
        
        Args:
            book_id: Book identifier
            css_content: CSS content to write
            
        Returns:
            True if successful, False otherwise
        """
        # Sanitize book ID and verify it exists
        safe_id = re.sub(r'[^a-zA-Z0-9_-]', '', book_id)
        if "BOOK_PATHS" not in self.config or safe_id not in self.config["BOOK_PATHS"]:
            logger.error(f"Book ID not found: {safe_id}")
            return False
            
        book_dir = Path(self.config["BOOK_PATHS"][safe_id])
        if not book_dir.exists():
            logger.error(f"Book directory does not exist: {book_dir}")
            return False
            
        # Write CSS file
        try:
            # Validate CSS content (basic check)
            if not css_content.strip():
                logger.warning("Empty CSS content provided")
                
            # Write to custom.css
            css_path = book_dir / "custom.css"
            with open(css_path, 'w') as f:
                f.write(css_content)
                
            logger.info(f"Updated custom CSS for {book_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating CSS: {e}")
            return False
            
    def update_javascript(self, book_id: str, js_file: str, js_content: str) -> bool:
        """
        Update or add a JavaScript file for an mdBook.
        
        Args:
            book_id: Book identifier
            js_file: JavaScript filename (without path)
            js_content: JavaScript content
            
        Returns:
            True if successful, False otherwise
        """
        # Sanitize book ID and verify it exists
        safe_id = re.sub(r'[^a-zA-Z0-9_-]', '', book_id)
        if "BOOK_PATHS" not in self.config or safe_id not in self.config["BOOK_PATHS"]:
            logger.error(f"Book ID not found: {safe_id}")
            return False
            
        book_dir = Path(self.config["BOOK_PATHS"][safe_id])
        if not book_dir.exists():
            logger.error(f"Book directory does not exist: {book_dir}")
            return False
            
        # Sanitize JS filename (restrict to .js files for security)
        safe_filename = re.sub(r'[^a-zA-Z0-9_-]', '', Path(js_file).stem) + ".js"
        
        # Write JavaScript file
        try:
            js_path = book_dir / safe_filename
            
            # Update book.toml to include this JS file if not already included
            book_toml_path = book_dir / "book.toml"
            if book_toml_path.exists():
                with open(book_toml_path, 'r') as f:
                    content = f.read()
                    
                # Check if JS file is already in additional-js
                js_pattern = rf'additional-js\s*=\s*\[(.*?)\]'
                match = re.search(js_pattern, content, re.DOTALL)
                
                if match:
                    js_list = match.group(1)
                    if safe_filename not in js_list:
                        # Add file to the list
                        updated_list = js_list.rstrip().rstrip('"').rstrip(",") + f', "{safe_filename}"'
                        updated_content = content.replace(match.group(0), f'additional-js = [{updated_list}]')
                        
                        with open(book_toml_path, 'w') as f:
                            f.write(updated_content)
                else:
                    # If no additional-js found, add it to [output.html] section
                    html_section = "[output.html]"
                    if html_section in content:
                        updated_content = content.replace(
                            html_section,
                            f'{html_section}\nadditional-js = ["{safe_filename}"]'
                        )
                        with open(book_toml_path, 'w') as f:
                            f.write(updated_content)
            
            # Write JavaScript content
            with open(js_path, 'w') as f:
                f.write(js_content)
                
            logger.info(f"Updated JavaScript file {safe_filename} for {book_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating JavaScript: {e}")
            return False
            
    def add_chapter(self, book_id: str, chapter_title: str, content: str, position: int = -1) -> bool:
        """
        Add a new chapter to the book.
        
        Args:
            book_id: Book identifier
            chapter_title: Chapter title
            content: Chapter content in Markdown
            position: Position in the summary (-1 for end)
            
        Returns:
            True if successful, False otherwise
        """
        # Sanitize book ID and verify it exists
        safe_id = re.sub(r'[^a-zA-Z0-9_-]', '', book_id)
        if "BOOK_PATHS" not in self.config or safe_id not in self.config["BOOK_PATHS"]:
            logger.error(f"Book ID not found: {safe_id}")
            return False
            
        book_dir = Path(self.config["BOOK_PATHS"][safe_id])
        src_dir = book_dir / "src"
        if not src_dir.exists():
            logger.error(f"Source directory does not exist: {src_dir}")
            return False
            
        # Create safe filename from title
        safe_filename = re.sub(r'[^a-zA-Z0-9_-]', '_', chapter_title.lower()) + ".md"
        
        try:
            # Write chapter content
            chapter_path = src_dir / safe_filename
            with open(chapter_path, 'w') as f:
                f.write(f"# {chapter_title}\n\n{content}")
                
            # Update SUMMARY.md
            summary_path = src_dir / "SUMMARY.md"
            if summary_path.exists():
                with open(summary_path, 'r') as f:
                    summary_lines = f.readlines()
                    
                # Find where to insert the new chapter
                chapter_entry = f"- [{chapter_title}]({safe_filename})\n"
                
                if position < 0 or position >= len(summary_lines):
                    # Add to end, before any appendix items
                    appendix_markers = ["[Appendix]", "[Glossary]", "[References]"]
                    appendix_pos = len(summary_lines)
                    
                    for i, line in enumerate(summary_lines):
                        if any(marker in line for marker in appendix_markers):
                            appendix_pos = i
                            break
                            
                    summary_lines.insert(appendix_pos, chapter_entry)
                else:
                    # Insert at specified position
                    summary_lines.insert(position, chapter_entry)
                    
                # Write updated summary
                with open(summary_path, 'w') as f:
                    f.writelines(summary_lines)
                    
            else:
                # Create a new summary if it doesn't exist
                with open(summary_path, 'w') as f:
                    f.write("# Summary\n\n[Introduction](README.md)\n\n")
                    f.write(chapter_entry)
                    
            logger.info(f"Added chapter '{chapter_title}' to {book_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding chapter: {e}")
            return False
    
    def export_book(self, book_id: str, format_type: str = "html") -> Tuple[bool, str]:
        """
        Export the book in various formats.
        
        Args:
            book_id: Book identifier
            format_type: Export format (html, pdf, epub)
            
        Returns:
            Tuple of (success, output_path)
        """
        # Sanitize and validate inputs
        safe_id = re.sub(r'[^a-zA-Z0-9_-]', '', book_id)
        format_type = format_type.lower()
        
        if format_type not in ["html", "pdf", "epub"]:
            logger.error(f"Unsupported export format: {format_type}")
            return False, ""
            
        if "BOOK_PATHS" not in self.config or safe_id not in self.config["BOOK_PATHS"]:
            logger.error(f"Book ID not found: {safe_id}")
            return False, ""
            
        book_dir = Path(self.config["BOOK_PATHS"][safe_id])
        if not book_dir.exists():
            logger.error(f"Book directory does not exist: {book_dir}")
            return False, ""
            
        # Create export directory
        export_dir = book_dir / "exports"
        export_dir.mkdir(exist_ok=True)
        
        # Process based on format type
        if format_type == "html":
            success, path = self.build_book(book_id, str(export_dir / "html"))
            return success, path
            
        elif format_type in ["pdf", "epub"]:
            # Check if mdbook is installed with required renderer
            if not self.mdbook_installed:
                logger.error(f"Cannot export to {format_type} - mdbook not installed")
                return False, ""
                
            # Check for required renderer
            try:
                cmd = ["mdbook", format_type, "--version"]
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                
                if result.returncode != 0:
                    logger.error(f"mdbook-{format_type} not installed: {result.stderr}")
                    return False, ""
                    
                # Export the book
                output_file = export_dir / f"{safe_id}.{format_type}"
                export_cmd = ["mdbook", format_type, str(book_dir), "-d", str(output_file)]
                
                export_result = subprocess.run(
                    export_cmd,
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if export_result.returncode == 0:
                    logger.info(f"Exported {format_type} to {output_file}")
                    return True, str(output_file)
                else:
                    logger.error(f"Failed to export {format_type}: {export_result.stderr}")
                    return False, ""
                    
            except Exception as e:
                logger.error(f"Error exporting to {format_type}: {e}")
                return False, ""
                
        return False, ""


def main():
    """
    Main function for testing the mdBook manager.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="mdBook Manager")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--create", help="Create a new book with specified ID")
    parser.add_argument("--title", default="Art History Textbook", help="Book title")
    parser.add_argument("--author", default="Lucas Blanco", help="Book author")
    parser.add_argument("--description", default="Art History Textbook", help="Book description")
    parser.add_argument("--build", help="Build a book with specified ID")
    parser.add_argument("--export", help="Export a book with specified ID")
    parser.add_argument("--format", default="html", help="Export format (html, pdf, epub)")
    
    args = parser.parse_args()
    
    # Load configuration
    config = {}
    if args.config and os.path.exists(args.config):
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
    
    # Initialize manager
    manager = MdBookManager(config)
    
    # Process commands
    if args.create:
        book_path = manager.create_book(args.create, args.title, args.author, args.description)
        print(f"Created book at: {book_path}")
        
    if args.build:
        success, output_path = manager.build_book(args.build)
        if success:
            print(f"Built book at: {output_path}")
        else:
            print("Failed to build book")
            
    if args.export:
        success, output_path = manager.export_book(args.export, args.format)
        if success:
            print(f"Exported book to: {output_path}")
        else:
            print(f"Failed to export book to {args.format}")
    
    return 0


if __name__ == "__main__":
    exit(main())
