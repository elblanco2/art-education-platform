#!/usr/bin/env python3
"""
Franchise Template Manager

Provides tools for professors to easily create their own textbook instances
with minimal technical requirements. Implements a sustainable revenue model
and user-friendly setup process.
"""

import os
import logging
import json
import shutil
import uuid
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
import time
import datetime
import threading
import zipfile
import tempfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class TemplateManager:
    """
    Manages textbook templates and franchise instances.
    """

    def __init__(self, config: Dict = None):
        """
        Initialize the template manager with configuration.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        
        # Setup directories
        self.templates_dir = Path(self.config.get("TEMPLATES_DIR", "./templates"))
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        self.instances_dir = Path(self.config.get("INSTANCES_DIR", "./instances"))
        self.instances_dir.mkdir(parents=True, exist_ok=True)
        
        self.uploads_dir = Path(self.config.get("UPLOADS_DIR", "./uploads"))
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        
        # Load template registry
        self.registry_path = self.templates_dir / "registry.json"
        self.templates = self._load_registry()
        
        # Load subscription plans
        self.plans = {
            "free": {
                "name": "Free",
                "price": 0,
                "features": ["Basic textbook conversion", "Standard theme", "Canvas integration"],
                "limits": {"books": 1, "pages": 100, "students": 50}
            },
            "basic": {
                "name": "Basic",
                "price": 4.99,
                "features": ["Advanced textbook conversion", "Custom theme", "Canvas integration", "Quiz generation"],
                "limits": {"books": 3, "pages": 500, "students": 200}
            },
            "premium": {
                "name": "Premium",
                "price": 9.99,
                "features": ["Advanced textbook conversion", "Custom theme", "Canvas integration", "Quiz generation", "Advanced analytics", "Priority support"],
                "limits": {"books": 10, "pages": 2000, "students": 1000}
            },
            "enterprise": {
                "name": "Enterprise",
                "price": 24.99,
                "features": ["All features", "Unlimited books", "Unlimited pages", "Unlimited students", "Dedicated support", "Custom integrations"],
                "limits": {"books": -1, "pages": -1, "students": -1}  # -1 means unlimited
            }
        }
        
    def _load_registry(self) -> Dict:
        """
        Load the template registry from file.
        
        Returns:
            Dictionary of registered templates
        """
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading template registry: {e}")
                return {}
        else:
            return {}
            
    def _save_registry(self):
        """
        Save the template registry to file.
        """
        try:
            with open(self.registry_path, 'w') as f:
                json.dump(self.templates, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving template registry: {e}")
            
    def create_template(self, name: str, description: str, author: str,
                       template_type: str = "textbook", files: Dict = None) -> Dict:
        """
        Create a new template for reuse.
        
        Args:
            name: Template name
            description: Template description
            author: Template author
            template_type: Type of template (textbook, course, etc.)
            files: Dictionary of files to include
            
        Returns:
            Template creation result
        """
        # Generate a unique ID for the template
        template_id = str(uuid.uuid4())
        
        # Create template directory
        template_dir = self.templates_dir / template_id
        template_dir.mkdir(parents=True, exist_ok=True)
        
        # Create template metadata
        template_meta = {
            "id": template_id,
            "name": name,
            "description": description,
            "author": author,
            "type": template_type,
            "created": datetime.datetime.now().isoformat(),
            "modified": datetime.datetime.now().isoformat(),
            "files": []
        }
        
        # Copy files if provided
        if files:
            for file_id, file_info in files.items():
                source_path = file_info.get("path")
                if source_path and os.path.exists(source_path):
                    # Create target path
                    rel_path = file_info.get("relative_path", "")
                    target_dir = template_dir / rel_path
                    target_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file
                    filename = os.path.basename(source_path)
                    target_path = target_dir / filename
                    shutil.copy2(source_path, target_path)
                    
                    # Add to metadata
                    template_meta["files"].append({
                        "id": file_id,
                        "name": filename,
                        "path": str(Path(rel_path) / filename),
                        "size": os.path.getsize(target_path),
                        "type": file_info.get("type", "unknown")
                    })
        
        # Save template metadata
        with open(template_dir / "template.json", 'w') as f:
            json.dump(template_meta, f, indent=2)
            
        # Add to registry
        self.templates[template_id] = {
            "id": template_id,
            "name": name,
            "description": description,
            "author": author,
            "type": template_type,
            "created": template_meta["created"],
            "modified": template_meta["modified"],
            "file_count": len(template_meta["files"])
        }
        
        self._save_registry()
        
        return {
            "status": "success",
            "template_id": template_id,
            "name": name
        }
        
    def get_templates(self, template_type: Optional[str] = None) -> List[Dict]:
        """
        Get list of available templates.
        
        Args:
            template_type: Optional filter by type
            
        Returns:
            List of template metadata
        """
        result = []
        
        for template_id, template in self.templates.items():
            if template_type is None or template.get("type") == template_type:
                result.append(template)
                
        return result
        
    def get_template_details(self, template_id: str) -> Dict:
        """
        Get detailed information about a template.
        
        Args:
            template_id: Template identifier
            
        Returns:
            Template details
        """
        if template_id not in self.templates:
            return {"status": "error", "message": "Template not found"}
            
        # Get template directory
        template_dir = self.templates_dir / template_id
        meta_path = template_dir / "template.json"
        
        if not meta_path.exists():
            return {"status": "error", "message": "Template metadata not found"}
            
        try:
            with open(meta_path, 'r') as f:
                template_meta = json.load(f)
                
            return {
                "status": "success",
                "template": template_meta
            }
            
        except Exception as e:
            logger.error(f"Error loading template metadata: {e}")
            return {"status": "error", "message": str(e)}
            
    def create_instance(self, template_id: str, name: str, owner: Dict,
                        subscription_plan: str = "free") -> Dict:
        """
        Create a new instance from a template.
        
        Args:
            template_id: Template to use
            name: Instance name
            owner: Owner information
            subscription_plan: Subscription plan
            
        Returns:
            Instance creation result
        """
        if template_id not in self.templates:
            return {"status": "error", "message": "Template not found"}
            
        # Validate subscription plan
        if subscription_plan not in self.plans:
            subscription_plan = "free"
            
        # Generate a unique ID for the instance
        instance_id = str(uuid.uuid4())
        
        # Create instance directory
        instance_dir = self.instances_dir / instance_id
        instance_dir.mkdir(parents=True, exist_ok=True)
        
        # Create src directory for content
        src_dir = instance_dir / "src"
        src_dir.mkdir(exist_ok=True)
        
        try:
            # Copy template files
            template_dir = self.templates_dir / template_id
            template_meta_path = template_dir / "template.json"
            
            if template_meta_path.exists():
                with open(template_meta_path, 'r') as f:
                    template_meta = json.load(f)
                    
                # Copy each file from template
                for file_info in template_meta.get("files", []):
                    source_path = template_dir / file_info["path"]
                    target_path = instance_dir / file_info["path"]
                    
                    # Create parent directories
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file
                    if source_path.exists():
                        shutil.copy2(source_path, target_path)
            
            # Create instance metadata
            instance_meta = {
                "id": instance_id,
                "name": name,
                "template_id": template_id,
                "template_name": self.templates[template_id]["name"],
                "owner": owner,
                "created": datetime.datetime.now().isoformat(),
                "modified": datetime.datetime.now().isoformat(),
                "subscription": {
                    "plan": subscription_plan,
                    "features": self.plans[subscription_plan]["features"],
                    "limits": self.plans[subscription_plan]["limits"],
                    "start_date": datetime.datetime.now().isoformat(),
                    "end_date": (datetime.datetime.now() + datetime.timedelta(days=30)).isoformat()
                },
                "published": False,
                "url": ""
            }
            
            # Save instance metadata
            with open(instance_dir / "instance.json", 'w') as f:
                json.dump(instance_meta, f, indent=2)
                
            return {
                "status": "success",
                "instance_id": instance_id,
                "name": name
            }
            
        except Exception as e:
            logger.error(f"Error creating instance: {e}")
            # Cleanup on failure
            if instance_dir.exists():
                shutil.rmtree(instance_dir)
            return {"status": "error", "message": str(e)}
            
    def get_instances(self, owner_id: Optional[str] = None) -> List[Dict]:
        """
        Get list of instances, optionally filtered by owner.
        
        Args:
            owner_id: Optional owner identifier
            
        Returns:
            List of instance metadata
        """
        result = []
        
        for instance_dir in self.instances_dir.iterdir():
            if not instance_dir.is_dir():
                continue
                
            meta_path = instance_dir / "instance.json"
            if not meta_path.exists():
                continue
                
            try:
                with open(meta_path, 'r') as f:
                    instance_meta = json.load(f)
                    
                # Filter by owner if specified
                if owner_id is None or instance_meta.get("owner", {}).get("id") == owner_id:
                    # Return simplified metadata
                    result.append({
                        "id": instance_meta["id"],
                        "name": instance_meta["name"],
                        "template_id": instance_meta["template_id"],
                        "template_name": instance_meta["template_name"],
                        "owner": instance_meta["owner"],
                        "created": instance_meta["created"],
                        "modified": instance_meta["modified"],
                        "subscription": instance_meta["subscription"]["plan"],
                        "published": instance_meta["published"],
                        "url": instance_meta["url"]
                    })
                    
            except Exception as e:
                logger.error(f"Error loading instance metadata: {e}")
                
        return result
        
    def get_instance_details(self, instance_id: str) -> Dict:
        """
        Get detailed information about an instance.
        
        Args:
            instance_id: Instance identifier
            
        Returns:
            Instance details
        """
        instance_dir = self.instances_dir / instance_id
        meta_path = instance_dir / "instance.json"
        
        if not instance_dir.exists() or not meta_path.exists():
            return {"status": "error", "message": "Instance not found"}
            
        try:
            with open(meta_path, 'r') as f:
                instance_meta = json.load(f)
                
            return {
                "status": "success",
                "instance": instance_meta
            }
            
        except Exception as e:
            logger.error(f"Error loading instance metadata: {e}")
            return {"status": "error", "message": str(e)}
            
    def process_upload(self, upload_id: str, file_type: str) -> Dict:
        """
        Process an uploaded file for conversion.
        
        Args:
            upload_id: Upload identifier
            file_type: Type of file (jpg, pdf, etc.)
            
        Returns:
            Processing result
        """
        upload_path = self.uploads_dir / upload_id
        
        if not upload_path.exists():
            return {"status": "error", "message": "Upload not found"}
            
        # Different processing based on file type
        if file_type == "jpg" or file_type == "image":
            return self._process_image_upload(upload_path)
        elif file_type == "pdf":
            return self._process_pdf_upload(upload_path)
        elif file_type == "zip":
            return self._process_zip_upload(upload_path)
        else:
            return {"status": "error", "message": f"Unsupported file type: {file_type}"}
            
    def _process_image_upload(self, upload_path: Path) -> Dict:
        """
        Process an uploaded image file.
        
        Args:
            upload_path: Path to uploaded file
            
        Returns:
            Processing result
        """
        # In a real implementation, this would call the OCR module
        # For now, return a placeholder result
        return {
            "status": "success",
            "message": f"Image processing initiated for {upload_path.name}",
            "processing_id": str(uuid.uuid4())
        }
        
    def _process_pdf_upload(self, upload_path: Path) -> Dict:
        """
        Process an uploaded PDF file.
        
        Args:
            upload_path: Path to uploaded file
            
        Returns:
            Processing result
        """
        # In a real implementation, this would convert the PDF
        # For now, return a placeholder result
        return {
            "status": "success",
            "message": f"PDF processing initiated for {upload_path.name}",
            "processing_id": str(uuid.uuid4())
        }
        
    def _process_zip_upload(self, upload_path: Path) -> Dict:
        """
        Process an uploaded ZIP file containing multiple files.
        
        Args:
            upload_path: Path to uploaded file
            
        Returns:
            Processing result
        """
        try:
            # Create temporary directory for extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract ZIP file
                with zipfile.ZipFile(upload_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                    
                # Count extracted files
                file_count = sum(1 for _ in Path(temp_dir).rglob('*') if _.is_file())
                
                # In a real implementation, process the extracted files
                # For now, return a placeholder result
                return {
                    "status": "success",
                    "message": f"Extracted {file_count} files from ZIP",
                    "processing_id": str(uuid.uuid4()),
                    "file_count": file_count
                }
                
        except Exception as e:
            logger.error(f"Error processing ZIP file: {e}")
            return {"status": "error", "message": str(e)}
            
    def update_subscription(self, instance_id: str, plan: str) -> Dict:
        """
        Update the subscription plan for an instance.
        
        Args:
            instance_id: Instance identifier
            plan: New subscription plan
            
        Returns:
            Update result
        """
        if plan not in self.plans:
            return {"status": "error", "message": f"Invalid subscription plan: {plan}"}
            
        instance_dir = self.instances_dir / instance_id
        meta_path = instance_dir / "instance.json"
        
        if not instance_dir.exists() or not meta_path.exists():
            return {"status": "error", "message": "Instance not found"}
            
        try:
            # Load current metadata
            with open(meta_path, 'r') as f:
                instance_meta = json.load(f)
                
            # Update subscription information
            instance_meta["subscription"] = {
                "plan": plan,
                "features": self.plans[plan]["features"],
                "limits": self.plans[plan]["limits"],
                "start_date": datetime.datetime.now().isoformat(),
                "end_date": (datetime.datetime.now() + datetime.timedelta(days=30)).isoformat()
            }
            
            instance_meta["modified"] = datetime.datetime.now().isoformat()
            
            # Save updated metadata
            with open(meta_path, 'w') as f:
                json.dump(instance_meta, f, indent=2)
                
            return {
                "status": "success",
                "instance_id": instance_id,
                "plan": plan
            }
            
        except Exception as e:
            logger.error(f"Error updating subscription: {e}")
            return {"status": "error", "message": str(e)}
            
    def get_subscription_plans(self) -> Dict:
        """
        Get available subscription plans.
        
        Returns:
            Dictionary of subscription plans
        """
        return {
            "status": "success",
            "plans": self.plans
        }


def main():
    """
    Main function for testing the template manager.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Franchise Template Manager")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--list-templates", action="store_true", help="List available templates")
    parser.add_argument("--list-instances", action="store_true", help="List instances")
    parser.add_argument("--list-plans", action="store_true", help="List subscription plans")
    
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
    manager = TemplateManager(config)
    
    # Process commands
    if args.list_templates:
        templates = manager.get_templates()
        print(json.dumps(templates, indent=2))
        
    if args.list_instances:
        instances = manager.get_instances()
        print(json.dumps(instances, indent=2))
        
    if args.list_plans:
        plans = manager.get_subscription_plans()
        print(json.dumps(plans, indent=2))
    
    return 0


if __name__ == "__main__":
    exit(main())
