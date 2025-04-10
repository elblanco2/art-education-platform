#!/usr/bin/env python3
"""
Art Book OCR Image Processor

This module handles the processing of art book images for OCR text extraction.
Implements secure file handling with validation and sanitization to prevent
security vulnerabilities.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import hashlib

import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
from pdf2image import convert_from_path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ImageProcessor:
    """
    Handles image preprocessing for optimal OCR results.
    Includes security measures for safe file handling.
    """

    def __init__(self, config: Dict):
        """
        Initialize the image processor with configuration.
        
        Args:
            config: Dictionary containing OCR configuration parameters
        """
        self.ocr_language = config.get("OCR_LANGUAGE", "eng")
        self.ocr_dpi = int(config.get("OCR_DPI", 300))
        self.allowed_extensions = {".jpg", ".jpeg", ".png", ".tiff", ".pdf"}
        self.output_dir = Path(config.get("OUTPUT_DIR", "./processed_images"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate tesseract installation
        try:
            pytesseract.get_tesseract_version()
            logger.info("Tesseract installed and working correctly")
        except Exception as e:
            logger.error(f"Tesseract not installed or not working: {e}")
            raise RuntimeError("Tesseract OCR must be installed and configured")

    def validate_file(self, file_path: str) -> bool:
        """
        Validate if a file is safe to process.
        
        Args:
            file_path: Path to the input file
            
        Returns:
            bool: True if file is valid, False otherwise
        """
        file_path = Path(file_path)
        
        # Check if file exists
        if not file_path.exists():
            logger.error(f"File does not exist: {file_path}")
            return False
            
        # Check file extension
        if file_path.suffix.lower() not in self.allowed_extensions:
            logger.error(f"Unsupported file extension: {file_path.suffix}")
            return False
            
        # Check file size (limit to 50MB for security)
        max_size = 50 * 1024 * 1024  # 50MB
        if file_path.stat().st_size > max_size:
            logger.error(f"File too large: {file_path}")
            return False
            
        return True
        
    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Enhance image for better OCR results.
        
        Args:
            image: PIL Image object
            
        Returns:
            Enhanced PIL Image object
        """
        # Convert to grayscale
        image = image.convert("L")
        
        # Increase contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        # Apply slight sharpening
        image = image.filter(ImageFilter.SHARPEN)
        
        # Binarization with threshold
        threshold = 200
        image = image.point(lambda p: 255 if p > threshold else 0)
        
        return image
        
    def convert_pdf_to_images(self, pdf_path: str) -> List[Image.Image]:
        """
        Convert PDF pages to images.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of PIL Image objects
        """
        if not self.validate_file(pdf_path):
            raise ValueError(f"Invalid PDF file: {pdf_path}")
            
        logger.info(f"Converting PDF to images: {pdf_path}")
        
        try:
            # Convert PDF to images
            return convert_from_path(
                pdf_path,
                dpi=self.ocr_dpi,
                fmt="jpeg",
                grayscale=True,
            )
        except Exception as e:
            logger.error(f"Error converting PDF to images: {e}")
            raise
            
    def process_image_file(self, image_path: str, save_processed: bool = False) -> Tuple[str, str]:
        """
        Process a single image file for OCR.
        
        Args:
            image_path: Path to image file
            save_processed: Whether to save the processed image
            
        Returns:
            Tuple of (raw_text, processed_image_path)
        """
        if not self.validate_file(image_path):
            raise ValueError(f"Invalid image file: {image_path}")
            
        logger.info(f"Processing image file: {image_path}")
        
        try:
            # Open and preprocess image
            with Image.open(image_path) as img:
                processed_img = self.preprocess_image(img)
                
                # Save processed image if requested
                processed_path = None
                if save_processed:
                    # Create a secure filename using hash
                    file_hash = hashlib.md5(image_path.encode()).hexdigest()[:10]
                    original_name = Path(image_path).stem
                    processed_path = self.output_dir / f"{original_name}_{file_hash}_processed.png"
                    processed_img.save(processed_path)
                    logger.info(f"Saved processed image to {processed_path}")
                
                # Perform OCR
                raw_text = pytesseract.image_to_string(
                    processed_img,
                    lang=self.ocr_language,
                    config="--psm 1"  # Automatic page segmentation with OSD
                )
                
                return raw_text, str(processed_path) if processed_path else ""
                
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            raise
            
    def batch_process(self, input_dir: str, recursive: bool = False) -> Dict[str, str]:
        """
        Process all valid images in a directory.
        
        Args:
            input_dir: Directory containing images
            recursive: Whether to search subdirectories
            
        Returns:
            Dictionary mapping image paths to extracted text
        """
        input_path = Path(input_dir)
        if not input_path.is_dir():
            raise ValueError(f"Not a valid directory: {input_dir}")
            
        logger.info(f"Batch processing images in {input_dir}")
        
        results = {}
        pattern = "**/*" if recursive else "*"
        
        for file_path in input_path.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in self.allowed_extensions:
                try:
                    text, _ = self.process_image_file(str(file_path))
                    results[str(file_path)] = text
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}")
                    results[str(file_path)] = f"ERROR: {str(e)}"
                    
        return results
