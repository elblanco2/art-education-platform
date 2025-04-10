#!/usr/bin/env python3
"""
Franchise Deployment Manager

Handles the secure deployment of professor-created textbook instances
to hosting platforms, including both lucasblanco.com hosting and options 
for self-hosting or Canvas direct integration.
"""

import os
import logging
import json
import subprocess
import shutil
import re
import uuid
import time
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
import threading
import tempfile
import requests
from urllib.parse import urlparse

# Configure logging with secure practices
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class DeploymentManager:
    """
    Manages deployment of franchise instances to various hosting options.
    Focuses on security and ease of use for professors.
    """

    def __init__(self, config: Dict = None):
        """
        Initialize deployment manager with configuration.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        
        # Setup directories
        self.instances_dir = Path(self.config.get("INSTANCES_DIR", "./instances"))
        self.deployments_dir = Path(self.config.get("DEPLOYMENTS_DIR", "./deployments"))
        self.deployments_dir.mkdir(parents=True, exist_ok=True)
        
        # Hosting configuration
        self.default_domain = self.config.get("DEFAULT_DOMAIN", "lucasblanco.com/ed")
        
        # Dictionary to track deployment processes
        self.active_deployments = {}
        
        # Deployment options
        self.deployment_options = {
            "hosted": {
                "name": "Managed Hosting",
                "description": "Host on our secure platform",
                "features": ["Simple setup", "Managed updates", "Built-in CDN", "Canvas integration"],
                "pricing": self.config.get("HOSTED_PRICE", 4.99)
            },
            "self_hosted": {
                "name": "Self Hosting",
                "description": "Deploy to your own hosting",
                "features": ["Full control", "Custom domain", "Advanced customization"],
                "pricing": 0
            },
            "canvas_direct": {
                "name": "Canvas Direct",
                "description": "Deploy directly to Canvas LMS",
                "features": ["Deep Canvas integration", "Automatic enrollment"],
                "pricing": self.config.get("CANVAS_DIRECT_PRICE", 2.99)
            }
        }
        
        # Load deployment registry
        self.registry_path = self.deployments_dir / "registry.json"
        self.deployments = self._load_registry()
        
    def _load_registry(self) -> Dict:
        """
        Load the deployment registry from file.
        
        Returns:
            Dictionary of registered deployments
        """
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading deployment registry: {e}")
                return {}
        else:
            return {}
            
    def _save_registry(self):
        """
        Save the deployment registry to file.
        """
        try:
            with open(self.registry_path, 'w') as f:
                json.dump(self.deployments, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving deployment registry: {e}")
            
    def get_deployment_options(self) -> Dict:
        """
        Get available deployment options.
        
        Returns:
            Dictionary of deployment options
        """
        return {
            "status": "success",
            "options": self.deployment_options
        }
        
    def validate_subdomain(self, subdomain: str) -> Dict:
        """
        Validate a requested subdomain.
        
        Args:
            subdomain: Requested subdomain
            
        Returns:
            Validation result
        """
        # Sanitize subdomain for security
        subdomain = re.sub(r'[^a-zA-Z0-9-]', '', subdomain).lower()
        
        # Check length
        if len(subdomain) < 3 or len(subdomain) > 30:
            return {
                "status": "error",
                "message": "Subdomain must be between 3 and 30 characters",
                "valid": False
            }
            
        # Check for reserved names
        reserved = ["www", "admin", "api", "app", "test", "demo", "beta"]
        if subdomain in reserved:
            return {
                "status": "error",
                "message": "This subdomain is reserved",
                "valid": False
            }
            
        # Check for existing deployments with this subdomain
        for deployment_id, deployment in self.deployments.items():
            if deployment.get("subdomain") == subdomain:
                return {
                    "status": "error",
                    "message": "This subdomain is already in use",
                    "valid": False
                }
                
        return {
            "status": "success",
            "message": "Subdomain is available",
            "valid": True,
            "sanitized": subdomain
        }
        
    def _sanitize_custom_domain(self, domain: str) -> str:
        """
        Sanitize a custom domain for security.
        
        Args:
            domain: Custom domain string
            
        Returns:
            Sanitized domain
        """
        # Basic domain sanitization
        domain = domain.strip().lower()
        
        # Remove protocol if present
        if "://" in domain:
            domain = domain.split("://", 1)[1]
            
        # Remove path if present
        domain = domain.split("/", 1)[0]
        
        # Remove potential script injection
        domain = re.sub(r'[<>\'";]', '', domain)
        
        return domain
        
    def deploy_instance(self, instance_id: str, deployment_type: str,
                       subdomain: str = None, custom_domain: str = None) -> Dict:
        """
        Deploy an instance to hosting.
        
        Args:
            instance_id: Instance identifier
            deployment_type: Type of deployment
            subdomain: Optional subdomain for hosted option
            custom_domain: Optional custom domain
            
        Returns:
            Deployment result
        """
        # Validate deployment type
        if deployment_type not in self.deployment_options:
            return {
                "status": "error",
                "message": f"Invalid deployment type: {deployment_type}"
            }
            
        # Check if instance exists
        instance_dir = self.instances_dir / instance_id
        meta_path = instance_dir / "instance.json"
        
        if not instance_dir.exists() or not meta_path.exists():
            return {
                "status": "error",
                "message": "Instance not found"
            }
            
        try:
            # Load instance metadata
            with open(meta_path, 'r') as f:
                instance_meta = json.load(f)
                
            # Generate deployment ID
            deployment_id = str(uuid.uuid4())
            
            # Deploy based on type
            result = None
            if deployment_type == "hosted":
                result = self._deploy_hosted(
                    instance_id=instance_id, 
                    instance_meta=instance_meta,
                    deployment_id=deployment_id,
                    subdomain=subdomain
                )
            elif deployment_type == "self_hosted":
                result = self._deploy_self_hosted(
                    instance_id=instance_id,
                    instance_meta=instance_meta,
                    deployment_id=deployment_id,
                    custom_domain=custom_domain
                )
            elif deployment_type == "canvas_direct":
                result = self._deploy_canvas_direct(
                    instance_id=instance_id,
                    instance_meta=instance_meta,
                    deployment_id=deployment_id
                )
                
            if not result or result.get("status") != "success":
                return result or {
                    "status": "error",
                    "message": "Deployment failed"
                }
                
            # Update instance metadata
            instance_meta["published"] = True
            instance_meta["url"] = result.get("url", "")
            instance_meta["modified"] = datetime.datetime.now().isoformat()
            
            # Save updated instance metadata
            with open(meta_path, 'w') as f:
                json.dump(instance_meta, f, indent=2)
                
            # Add to deployment registry
            self.deployments[deployment_id] = {
                "id": deployment_id,
                "instance_id": instance_id,
                "type": deployment_type,
                "url": result.get("url", ""),
                "created": datetime.datetime.now().isoformat(),
                "status": "active"
            }
            
            self._save_registry()
            
            return {
                "status": "success",
                "deployment_id": deployment_id,
                "url": result.get("url", ""),
                "message": "Deployment successful"
            }
            
        except Exception as e:
            logger.error(f"Error deploying instance: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
            
    def _deploy_hosted(self, instance_id: str, instance_meta: Dict, 
                      deployment_id: str, subdomain: str = None) -> Dict:
        """
        Deploy to hosted platform.
        
        Args:
            instance_id: Instance identifier
            instance_meta: Instance metadata
            deployment_id: Deployment identifier
            subdomain: Optional subdomain
            
        Returns:
            Deployment result
        """
        # Validate subdomain
        if not subdomain:
            # Generate from instance name
            name_based = re.sub(r'[^a-zA-Z0-9-]', '', instance_meta["name"].lower())
            subdomain = f"{name_based}-{str(uuid.uuid4())[:8]}"
        
        validation = self.validate_subdomain(subdomain)
        if not validation.get("valid", False):
            return {
                "status": "error",
                "message": validation.get("message", "Invalid subdomain")
            }
            
        # Use validated subdomain
        subdomain = validation.get("sanitized", subdomain)
        
        # Create deployment directory
        deploy_dir = self.deployments_dir / deployment_id
        deploy_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy instance files to deployment directory
        instance_dir = self.instances_dir / instance_id
        
        try:
            # Use shutil.copytree for full directory copy
            # Exclude certain files (like instance.json)
            for item in instance_dir.iterdir():
                if item.name != "instance.json":
                    if item.is_dir():
                        shutil.copytree(item, deploy_dir / item.name)
                    else:
                        shutil.copy2(item, deploy_dir / item.name)
                        
            # Create deployment metadata
            deploy_meta = {
                "id": deployment_id,
                "instance_id": instance_id,
                "instance_name": instance_meta["name"],
                "subdomain": subdomain,
                "url": f"https://{self.default_domain}/{subdomain}",
                "created": datetime.datetime.now().isoformat(),
                "status": "active",
                "type": "hosted"
            }
            
            # Save deployment metadata
            with open(deploy_dir / "deployment.json", 'w') as f:
                json.dump(deploy_meta, f, indent=2)
                
            # In a real implementation, this would trigger the actual deployment
            # For now, simulate with a success message
            
            return {
                "status": "success",
                "url": deploy_meta["url"],
                "subdomain": subdomain,
                "message": "Deployment initiated successfully"
            }
            
        except Exception as e:
            logger.error(f"Error in hosted deployment: {e}")
            # Cleanup on failure
            if deploy_dir.exists():
                shutil.rmtree(deploy_dir)
            return {"status": "error", "message": str(e)}
            
    def _deploy_self_hosted(self, instance_id: str, instance_meta: Dict, 
                           deployment_id: str, custom_domain: str = None) -> Dict:
        """
        Prepare for self-hosted deployment.
        
        Args:
            instance_id: Instance identifier
            instance_meta: Instance metadata
            deployment_id: Deployment identifier
            custom_domain: Optional custom domain
            
        Returns:
            Deployment package info
        """
        # Sanitize custom domain
        domain = "your-domain.com"
        if custom_domain:
            domain = self._sanitize_custom_domain(custom_domain)
        
        # Create deployment directory
        deploy_dir = self.deployments_dir / deployment_id
        deploy_dir.mkdir(parents=True, exist_ok=True)
        
        # Create deployment package
        package_path = deploy_dir / "package.zip"
        
        try:
            # Copy instance files to temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Copy instance files
                instance_dir = self.instances_dir / instance_id
                for item in instance_dir.iterdir():
                    if item.name != "instance.json":
                        if item.is_dir():
                            shutil.copytree(item, temp_path / item.name)
                        else:
                            shutil.copy2(item, temp_path / item.name)
                            
                # Add deployment-specific files
                # In a real implementation, this would include:
                # - README with setup instructions
                # - Web server configuration files
                # - Any necessary scripts
                
                # Create README file
                readme_path = temp_path / "README.md"
                with open(readme_path, 'w') as f:
                    f.write(f"""# {instance_meta["name"]} - Self-Hosted Deployment

## Setup Instructions

1. Unzip this package to your web server directory
2. Configure your web server to serve the content
3. Update your domain settings to point to your server
4. Open the URL in your browser to verify the installation

For more detailed instructions, visit our support website.
""")
                
                # Create .htaccess for Apache (common hosting)
                htaccess_path = temp_path / ".htaccess"
                with open(htaccess_path, 'w') as f:
                    f.write("""RewriteEngine On
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^(.*)$ index.html [QSA,L]

# Security headers
Header set X-Content-Type-Options "nosniff"
Header set X-Frame-Options "SAMEORIGIN"
Header set X-XSS-Protection "1; mode=block"
Header set Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;"
""")
                
                # Create deployment info file
                deploy_info_path = temp_path / "deployment-info.json"
                with open(deploy_info_path, 'w') as f:
                    json.dump({
                        "id": deployment_id,
                        "instance_id": instance_id,
                        "instance_name": instance_meta["name"],
                        "type": "self_hosted",
                        "domain": domain,
                        "created": datetime.datetime.now().isoformat()
                    }, f, indent=2)
                    
                # Create ZIP package
                shutil.make_archive(
                    str(deploy_dir / "package"),
                    'zip',
                    temp_dir
                )
                
            # Create deployment metadata
            deploy_meta = {
                "id": deployment_id,
                "instance_id": instance_id,
                "instance_name": instance_meta["name"],
                "domain": domain,
                "url": f"https://{domain}",
                "package": f"package.zip",
                "created": datetime.datetime.now().isoformat(),
                "status": "ready",
                "type": "self_hosted"
            }
            
            # Save deployment metadata
            with open(deploy_dir / "deployment.json", 'w') as f:
                json.dump(deploy_meta, f, indent=2)
                
            return {
                "status": "success",
                "url": deploy_meta["url"],
                "package_url": f"/deployments/{deployment_id}/package.zip",
                "domain": domain,
                "message": "Deployment package created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error in self-hosted deployment: {e}")
            # Cleanup on failure
            if deploy_dir.exists():
                shutil.rmtree(deploy_dir)
            return {"status": "error", "message": str(e)}
            
    def _deploy_canvas_direct(self, instance_id: str, instance_meta: Dict, 
                             deployment_id: str) -> Dict:
        """
        Deploy directly to Canvas LMS.
        
        Args:
            instance_id: Instance identifier
            instance_meta: Instance metadata
            deployment_id: Deployment identifier
            
        Returns:
            Deployment result
        """
        # This would integrate with the Canvas LMS API
        # For now, return a placeholder result
        
        # Create deployment directory
        deploy_dir = self.deployments_dir / deployment_id
        deploy_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Create deployment metadata
            deploy_meta = {
                "id": deployment_id,
                "instance_id": instance_id,
                "instance_name": instance_meta["name"],
                "url": f"https://canvas.example.com/courses/123",
                "created": datetime.datetime.now().isoformat(),
                "status": "pending_configuration",
                "type": "canvas_direct"
            }
            
            # Save deployment metadata
            with open(deploy_dir / "deployment.json", 'w') as f:
                json.dump(deploy_meta, f, indent=2)
                
            return {
                "status": "success",
                "url": deploy_meta["url"],
                "message": "Canvas deployment initiated, configuration needed",
                "configuration_url": f"/deployments/{deployment_id}/canvas_config"
            }
            
        except Exception as e:
            logger.error(f"Error in Canvas deployment: {e}")
            # Cleanup on failure
            if deploy_dir.exists():
                shutil.rmtree(deploy_dir)
            return {"status": "error", "message": str(e)}
            
    def get_deployment_status(self, deployment_id: str) -> Dict:
        """
        Get status of a deployment.
        
        Args:
            deployment_id: Deployment identifier
            
        Returns:
            Deployment status
        """
        if deployment_id not in self.deployments:
            return {"status": "error", "message": "Deployment not found"}
            
        # Get deployment directory
        deploy_dir = self.deployments_dir / deployment_id
        meta_path = deploy_dir / "deployment.json"
        
        if not deploy_dir.exists() or not meta_path.exists():
            return {"status": "error", "message": "Deployment metadata not found"}
            
        try:
            with open(meta_path, 'r') as f:
                deploy_meta = json.load(f)
                
            return {
                "status": "success",
                "deployment": deploy_meta
            }
            
        except Exception as e:
            logger.error(f"Error loading deployment metadata: {e}")
            return {"status": "error", "message": str(e)}
            
    def get_deployments(self, instance_id: Optional[str] = None) -> List[Dict]:
        """
        Get list of deployments, optionally filtered by instance.
        
        Args:
            instance_id: Optional instance identifier
            
        Returns:
            List of deployment metadata
        """
        result = []
        
        for deployment_id, deployment in self.deployments.items():
            if instance_id is None or deployment.get("instance_id") == instance_id:
                result.append(deployment)
                
        return result
        
    def undeploy(self, deployment_id: str) -> Dict:
        """
        Remove a deployment.
        
        Args:
            deployment_id: Deployment identifier
            
        Returns:
            Undeployment result
        """
        if deployment_id not in self.deployments:
            return {"status": "error", "message": "Deployment not found"}
            
        # Get deployment directory
        deploy_dir = self.deployments_dir / deployment_id
        meta_path = deploy_dir / "deployment.json"
        
        if not deploy_dir.exists() or not meta_path.exists():
            return {"status": "error", "message": "Deployment metadata not found"}
            
        try:
            # Load deployment metadata
            with open(meta_path, 'r') as f:
                deploy_meta = json.load(f)
                
            # Remove from registry
            del self.deployments[deployment_id]
            self._save_registry()
            
            # Update instance if needed
            instance_id = deploy_meta.get("instance_id")
            instance_dir = self.instances_dir / instance_id
            instance_meta_path = instance_dir / "instance.json"
            
            if instance_dir.exists() and instance_meta_path.exists():
                try:
                    with open(instance_meta_path, 'r') as f:
                        instance_meta = json.load(f)
                        
                    # Update instance metadata
                    instance_meta["published"] = False
                    instance_meta["url"] = ""
                    instance_meta["modified"] = datetime.datetime.now().isoformat()
                    
                    with open(instance_meta_path, 'w') as f:
                        json.dump(instance_meta, f, indent=2)
                        
                except Exception as e:
                    logger.error(f"Error updating instance metadata: {e}")
            
            # Remove deployment directory
            shutil.rmtree(deploy_dir)
            
            return {
                "status": "success",
                "message": "Deployment removed successfully"
            }
            
        except Exception as e:
            logger.error(f"Error removing deployment: {e}")
            return {"status": "error", "message": str(e)}


def main():
    """
    Main function for testing the deployment manager.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Franchise Deployment Manager")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--list-options", action="store_true", help="List deployment options")
    parser.add_argument("--list-deployments", action="store_true", help="List deployments")
    parser.add_argument("--validate-subdomain", help="Validate a subdomain")
    
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
    manager = DeploymentManager(config)
    
    # Process commands
    if args.list_options:
        options = manager.get_deployment_options()
        print(json.dumps(options, indent=2))
        
    if args.list_deployments:
        deployments = manager.get_deployments()
        print(json.dumps(deployments, indent=2))
        
    if args.validate_subdomain:
        validation = manager.validate_subdomain(args.validate_subdomain)
        print(json.dumps(validation, indent=2))
    
    return 0


if __name__ == "__main__":
    exit(main())
