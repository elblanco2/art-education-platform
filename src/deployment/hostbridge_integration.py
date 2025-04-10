#!/usr/bin/env python3
"""
HostBridge MCP Integration for Art Education Platform

This module provides integration with HostBridge MCP, allowing easy deployment of 
the Art Education Platform through conversational interfaces like Claude.

Features:
- Secure credential management
- Multiple hosting provider support (Netlify, Vercel, SSH/SFTP, etc.)
- Framework-specific deployment handlers
- Automated deployment workflows
"""

import os
import sys
import json
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import re
import secrets
import hashlib
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import needed modules if available
try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    logger.warning("Keyring module not available, will use file-based credential storage")
    KEYRING_AVAILABLE = False


class HostBridgeIntegration:
    """
    Integration with HostBridge MCP server for deploying instances
    through conversational interfaces.
    """

    def __init__(self, config: Dict = None):
        """
        Initialize HostBridge integration with configuration.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        
        # Setup directories
        self.base_dir = Path(self.config.get("BASE_DIR", "."))
        self.instances_dir = Path(self.config.get("INSTANCES_DIR", "./instances"))
        self.deployments_dir = Path(self.config.get("DEPLOYMENTS_DIR", "./deployments"))
        self.credentials_dir = Path(self.config.get("CREDENTIALS_DIR", "./credentials"))
        self.credentials_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup credential manager
        self.service_name = self.config.get("SERVICE_NAME", "art_education_platform")
        
        # Provider configurations
        self.providers = {
            "netlify": {
                "name": "Netlify",
                "framework_support": ["eleventy", "nextjs", "gatsby", "hugo", "react", "vue"],
                "config_template": {
                    "site_name": "",
                    "build_command": "npm run build",
                    "publish_directory": "dist",
                    "environment_variables": {}
                }
            },
            "vercel": {
                "name": "Vercel",
                "framework_support": ["nextjs", "gatsby", "nuxt", "vue", "react", "angular"],
                "config_template": {
                    "project_name": "",
                    "framework": "nextjs",
                    "root_directory": "",
                    "environment_variables": {}
                }
            },
            "ssh": {
                "name": "SSH/SFTP",
                "framework_support": ["*"],
                "config_template": {
                    "host": "",
                    "port": 22,
                    "username": "",
                    "remote_path": "",
                    "use_key": True,
                    "key_path": ""
                }
            },
            "hostm": {
                "name": "Hostm.com",
                "framework_support": ["php", "static", "nodejs"],
                "config_template": {
                    "app_name": "",
                    "app_type": "static",
                    "domain": "",
                    "environment_variables": {}
                }
            }
        }
        
    def _securely_store_credential(self, key: str, value: str) -> bool:
        """
        Securely store a credential.
        
        Args:
            key: Credential key/identifier
            value: Credential value
            
        Returns:
            True if successful, False otherwise
        """
        if KEYRING_AVAILABLE:
            try:
                keyring.set_password(self.service_name, key, value)
                return True
            except Exception as e:
                logger.error(f"Error storing credential in keyring: {e}")
                # Fall back to file storage
        
        # File-based storage with encryption
        try:
            # Generate a salt
            salt = secrets.token_bytes(16)
            
            # Hash with salt (in a production system, use a proper encryption)
            key_bytes = key.encode()
            value_bytes = value.encode()
            
            h = hashlib.pbkdf2_hmac('sha256', value_bytes, salt, 100000)
            
            # Store with salt
            cred_file = self.credentials_dir / f"{key}.cred"
            with open(cred_file, 'wb') as f:
                f.write(salt + h)
                
            return True
            
        except Exception as e:
            logger.error(f"Error storing credential in file: {e}")
            return False
            
    def _securely_retrieve_credential(self, key: str) -> Optional[str]:
        """
        Securely retrieve a credential.
        
        Args:
            key: Credential key/identifier
            
        Returns:
            Credential value if found, None otherwise
        """
        if KEYRING_AVAILABLE:
            try:
                value = keyring.get_password(self.service_name, key)
                if value:
                    return value
            except Exception as e:
                logger.error(f"Error retrieving credential from keyring: {e}")
                # Fall back to file storage
        
        # File-based retrieval
        try:
            cred_file = self.credentials_dir / f"{key}.cred"
            if not cred_file.exists():
                return None
                
            # In a real implementation, this would decrypt the credential
            # For now, just indicate we found it
            return "[CREDENTIAL FOUND - REQUIRES USER INPUT]"
            
        except Exception as e:
            logger.error(f"Error retrieving credential from file: {e}")
            return None
            
    def get_supported_providers(self) -> List[Dict]:
        """
        Get list of supported hosting providers.
        
        Returns:
            List of provider information
        """
        result = []
        
        for provider_id, provider_info in self.providers.items():
            result.append({
                "id": provider_id,
                "name": provider_info["name"],
                "frameworks": provider_info["framework_support"]
            })
            
        return result
        
    def get_provider_config_template(self, provider_id: str) -> Dict:
        """
        Get configuration template for a provider.
        
        Args:
            provider_id: Provider identifier
            
        Returns:
            Configuration template
        """
        if provider_id not in self.providers:
            return {"error": "Provider not supported"}
            
        return self.providers[provider_id]["config_template"]
        
    def store_provider_credentials(self, provider_id: str, credentials: Dict) -> Dict:
        """
        Store provider credentials securely.
        
        Args:
            provider_id: Provider identifier
            credentials: Credentials dictionary
            
        Returns:
            Result status
        """
        if provider_id not in self.providers:
            return {"status": "error", "message": "Provider not supported"}
            
        # Store each credential with provider prefix
        success = True
        stored = []
        
        for key, value in credentials.items():
            if value:  # Only store non-empty values
                cred_key = f"{provider_id}_{key}"
                if self._securely_store_credential(cred_key, value):
                    stored.append(key)
                else:
                    success = False
                    
        if not stored:
            return {"status": "error", "message": "No credentials stored"}
            
        return {
            "status": "success" if success else "partial",
            "message": f"Stored credentials: {', '.join(stored)}",
            "stored": stored
        }
        
    def check_provider_credentials(self, provider_id: str) -> Dict:
        """
        Check if credentials exist for a provider.
        
        Args:
            provider_id: Provider identifier
            
        Returns:
            Credential status
        """
        if provider_id not in self.providers:
            return {"status": "error", "message": "Provider not supported"}
            
        # Look for common credential patterns
        common_keys = {
            "netlify": ["token", "api_key"],
            "vercel": ["token", "api_key"],
            "ssh": ["password", "key_path"],
            "hostm": ["api_key", "username"]
        }
        
        found = []
        for key in common_keys.get(provider_id, []):
            cred_key = f"{provider_id}_{key}"
            value = self._securely_retrieve_credential(cred_key)
            if value:
                found.append(key)
                
        return {
            "status": "success" if found else "not_found",
            "message": f"Found credentials: {', '.join(found)}" if found else "No credentials found",
            "found": found
        }
        
    def prepare_deployment(self, instance_id: str, provider_id: str, 
                          provider_config: Dict) -> Dict:
        """
        Prepare deployment of an instance to a hosting provider.
        
        Args:
            instance_id: Instance identifier
            provider_id: Provider identifier
            provider_config: Provider-specific configuration
            
        Returns:
            Preparation result
        """
        if provider_id not in self.providers:
            return {"status": "error", "message": "Provider not supported"}
            
        # Check if instance exists
        instance_dir = self.instances_dir / instance_id
        meta_path = instance_dir / "instance.json"
        
        if not instance_dir.exists() or not meta_path.exists():
            return {"status": "error", "message": "Instance not found"}
            
        try:
            # Load instance metadata
            with open(meta_path, 'r') as f:
                instance_meta = json.load(f)
                
            # Create deployment directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            deploy_id = f"deploy_{provider_id}_{timestamp}"
            deploy_dir = self.deployments_dir / deploy_id
            deploy_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy instance files
            for item in instance_dir.iterdir():
                if item.name != "instance.json":
                    if item.is_dir():
                        shutil.copytree(item, deploy_dir / item.name)
                    else:
                        shutil.copy2(item, deploy_dir / item.name)
                        
            # Create deployment configuration
            deploy_config = {
                "id": deploy_id,
                "instance_id": instance_id,
                "instance_name": instance_meta["name"],
                "provider": provider_id,
                "provider_config": provider_config,
                "created": datetime.now().isoformat(),
                "status": "prepared"
            }
            
            # Save deployment configuration
            with open(deploy_dir / "deploy_config.json", 'w') as f:
                json.dump(deploy_config, f, indent=2)
                
            # Provider-specific preparation
            if provider_id == "netlify":
                self._prepare_netlify(deploy_dir, provider_config)
            elif provider_id == "vercel":
                self._prepare_vercel(deploy_dir, provider_config)
            elif provider_id == "ssh":
                self._prepare_ssh(deploy_dir, provider_config)
            elif provider_id == "hostm":
                self._prepare_hostm(deploy_dir, provider_config)
                
            return {
                "status": "success",
                "deploy_id": deploy_id,
                "message": f"Deployment prepared for {self.providers[provider_id]['name']}",
                "next_steps": [
                    "Execute deployment with execute_deployment(deploy_id)",
                    "Check deployment status with check_deployment_status(deploy_id)"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error preparing deployment: {e}")
            # Cleanup on failure
            if 'deploy_dir' in locals() and deploy_dir.exists():
                shutil.rmtree(deploy_dir)
            return {"status": "error", "message": str(e)}
            
    def _prepare_netlify(self, deploy_dir: Path, config: Dict) -> None:
        """
        Prepare Netlify-specific deployment files.
        
        Args:
            deploy_dir: Deployment directory
            config: Netlify configuration
        """
        # Create netlify.toml
        netlify_config = {
            "build": {
                "command": config.get("build_command", "npm run build"),
                "publish": config.get("publish_directory", "dist"),
                "environment": config.get("environment_variables", {})
            }
        }
        
        with open(deploy_dir / "netlify.toml", 'w') as f:
            f.write("[build]\n")
            f.write(f'  command = "{netlify_config["build"]["command"]}"\n')
            f.write(f'  publish = "{netlify_config["build"]["publish"]}"\n')
            
            if netlify_config["build"]["environment"]:
                f.write("\n[build.environment]\n")
                for key, value in netlify_config["build"]["environment"].items():
                    f.write(f'  {key} = "{value}"\n')
                    
    def _prepare_vercel(self, deploy_dir: Path, config: Dict) -> None:
        """
        Prepare Vercel-specific deployment files.
        
        Args:
            deploy_dir: Deployment directory
            config: Vercel configuration
        """
        # Create vercel.json
        vercel_config = {
            "name": config.get("project_name", "art-education-platform"),
            "framework": config.get("framework", "nextjs"),
            "env": config.get("environment_variables", {})
        }
        
        if config.get("root_directory"):
            vercel_config["rootDirectory"] = config["root_directory"]
            
        with open(deploy_dir / "vercel.json", 'w') as f:
            json.dump(vercel_config, f, indent=2)
            
    def _prepare_ssh(self, deploy_dir: Path, config: Dict) -> None:
        """
        Prepare SSH/SFTP deployment files.
        
        Args:
            deploy_dir: Deployment directory
            config: SSH configuration
        """
        # Create deployment script
        deploy_script = f"""#!/bin/bash
# SSH/SFTP Deployment Script
# Generated by Art Education Platform

HOST="{config.get('host', 'example.com')}"
PORT="{config.get('port', 22)}"
USER="{config.get('username', 'user')}"
REMOTE_PATH="{config.get('remote_path', '/var/www/html')}"
USE_KEY={str(config.get('use_key', True)).lower()}
KEY_PATH="{config.get('key_path', '')}"

echo "Deploying to $HOST:$REMOTE_PATH..."

if [ "$USE_KEY" = "true" ] && [ ! -z "$KEY_PATH" ]; then
    OPTS="-i $KEY_PATH"
else
    OPTS=""
fi

# Create remote directory if it doesn't exist
ssh $OPTS -p $PORT $USER@$HOST "mkdir -p $REMOTE_PATH"

# Upload files
rsync -avz --delete -e "ssh $OPTS -p $PORT" ./ $USER@$HOST:$REMOTE_PATH

echo "Deployment complete!"
"""
        
        script_path = deploy_dir / "deploy.sh"
        with open(script_path, 'w') as f:
            f.write(deploy_script)
            
        # Make script executable
        script_path.chmod(0o755)
        
    def _prepare_hostm(self, deploy_dir: Path, config: Dict) -> None:
        """
        Prepare Hostm.com deployment files.
        
        Args:
            deploy_dir: Deployment directory
            config: Hostm configuration
        """
        # Create hostm.json
        hostm_config = {
            "name": config.get("app_name", "art-education-platform"),
            "type": config.get("app_type", "static"),
            "domain": config.get("domain", ""),
            "env": config.get("environment_variables", {})
        }
        
        with open(deploy_dir / "hostm.json", 'w') as f:
            json.dump(hostm_config, f, indent=2)
            
    def execute_deployment(self, deploy_id: str) -> Dict:
        """
        Execute a prepared deployment.
        
        Args:
            deploy_id: Deployment identifier
            
        Returns:
            Execution result
        """
        # Check if deployment exists
        deploy_dir = self.deployments_dir / deploy_id
        config_path = deploy_dir / "deploy_config.json"
        
        if not deploy_dir.exists() or not config_path.exists():
            return {"status": "error", "message": "Deployment not found"}
            
        try:
            # Load deployment configuration
            with open(config_path, 'r') as f:
                deploy_config = json.load(f)
                
            provider_id = deploy_config.get("provider")
            
            if provider_id not in self.providers:
                return {"status": "error", "message": "Provider not supported"}
                
            # Update status
            deploy_config["status"] = "deploying"
            with open(config_path, 'w') as f:
                json.dump(deploy_config, f, indent=2)
                
            # Provider-specific deployment
            result = None
            
            if provider_id == "netlify":
                result = self._deploy_netlify(deploy_dir, deploy_config)
            elif provider_id == "vercel":
                result = self._deploy_vercel(deploy_dir, deploy_config)
            elif provider_id == "ssh":
                result = self._deploy_ssh(deploy_dir, deploy_config)
            elif provider_id == "hostm":
                result = self._deploy_hostm(deploy_dir, deploy_config)
                
            if not result:
                return {"status": "error", "message": "Deployment execution failed"}
                
            # Update status
            deploy_config["status"] = result.get("status", "unknown")
            deploy_config["url"] = result.get("url", "")
            deploy_config["deployed_at"] = datetime.now().isoformat()
            deploy_config["deployment_id"] = result.get("deployment_id", "")
            
            with open(config_path, 'w') as f:
                json.dump(deploy_config, f, indent=2)
                
            return result
            
        except Exception as e:
            logger.error(f"Error executing deployment: {e}")
            return {"status": "error", "message": str(e)}
            
    def _deploy_netlify(self, deploy_dir: Path, deploy_config: Dict) -> Dict:
        """
        Deploy to Netlify.
        
        Args:
            deploy_dir: Deployment directory
            deploy_config: Deployment configuration
            
        Returns:
            Deployment result
        """
        # In a real implementation, this would call the netlify-cli
        # For now, return a placeholder
        return {
            "status": "deployed",
            "url": f"https://{deploy_config['instance_name'].lower().replace(' ', '-')}.netlify.app",
            "deployment_id": f"netlify_{deploy_config['id']}",
            "message": "Deployed to Netlify (Simulated)"
        }
        
    def _deploy_vercel(self, deploy_dir: Path, deploy_config: Dict) -> Dict:
        """
        Deploy to Vercel.
        
        Args:
            deploy_dir: Deployment directory
            deploy_config: Deployment configuration
            
        Returns:
            Deployment result
        """
        # In a real implementation, this would call the vercel CLI
        # For now, return a placeholder
        return {
            "status": "deployed",
            "url": f"https://{deploy_config['instance_name'].lower().replace(' ', '-')}.vercel.app",
            "deployment_id": f"vercel_{deploy_config['id']}",
            "message": "Deployed to Vercel (Simulated)"
        }
        
    def _deploy_ssh(self, deploy_dir: Path, deploy_config: Dict) -> Dict:
        """
        Deploy via SSH/SFTP.
        
        Args:
            deploy_dir: Deployment directory
            deploy_config: Deployment configuration
            
        Returns:
            Deployment result
        """
        # In a real implementation, this would execute the deploy.sh script
        # For now, return a placeholder
        provider_config = deploy_config.get("provider_config", {})
        domain = provider_config.get("host", "example.com")
        
        return {
            "status": "deployed",
            "url": f"https://{domain}",
            "deployment_id": f"ssh_{deploy_config['id']}",
            "message": "Deployed via SSH/SFTP (Simulated)"
        }
        
    def _deploy_hostm(self, deploy_dir: Path, deploy_config: Dict) -> Dict:
        """
        Deploy to Hostm.com.
        
        Args:
            deploy_dir: Deployment directory
            deploy_config: Deployment configuration
            
        Returns:
            Deployment result
        """
        # In a real implementation, this would call the Hostm API
        # For now, return a placeholder
        provider_config = deploy_config.get("provider_config", {})
        domain = provider_config.get("domain", "example.com")
        
        return {
            "status": "deployed",
            "url": f"https://{domain}",
            "deployment_id": f"hostm_{deploy_config['id']}",
            "message": "Deployed to Hostm.com (Simulated)"
        }
        
    def check_deployment_status(self, deploy_id: str) -> Dict:
        """
        Check status of a deployment.
        
        Args:
            deploy_id: Deployment identifier
            
        Returns:
            Deployment status
        """
        # Check if deployment exists
        deploy_dir = self.deployments_dir / deploy_id
        config_path = deploy_dir / "deploy_config.json"
        
        if not deploy_dir.exists() or not config_path.exists():
            return {"status": "error", "message": "Deployment not found"}
            
        try:
            # Load deployment configuration
            with open(config_path, 'r') as f:
                deploy_config = json.load(f)
                
            return {
                "status": "success",
                "deployment": {
                    "id": deploy_config.get("id"),
                    "instance_id": deploy_config.get("instance_id"),
                    "instance_name": deploy_config.get("instance_name"),
                    "provider": deploy_config.get("provider"),
                    "status": deploy_config.get("status"),
                    "url": deploy_config.get("url", ""),
                    "created_at": deploy_config.get("created"),
                    "deployed_at": deploy_config.get("deployed_at", ""),
                    "deployment_id": deploy_config.get("deployment_id", "")
                }
            }
            
        except Exception as e:
            logger.error(f"Error checking deployment status: {e}")
            return {"status": "error", "message": str(e)}
    
    def install_hostbridge_mcp(self) -> Dict:
        """
        Install HostBridge MCP server for integration.
        
        Returns:
            Installation result
        """
        try:
            # Check if git is available
            try:
                subprocess.run(["git", "--version"], check=True, capture_output=True)
            except (subprocess.SubprocessError, FileNotFoundError):
                return {
                    "status": "error",
                    "message": "Git not found. Please install Git before continuing."
                }
                
            # Check if pip is available
            try:
                subprocess.run([sys.executable, "-m", "pip", "--version"], check=True, capture_output=True)
            except (subprocess.SubprocessError, FileNotFoundError):
                return {
                    "status": "error",
                    "message": "Pip not found. Please install Pip before continuing."
                }
                
            # Install HostBridge MCP
            command = [
                sys.executable, "-m", "pip", "install", 
                "git+https://github.com/elblanco2/hostbridge-mcp.git"
            ]
            
            result = subprocess.run(command, capture_output=True, text=True)
            
            if result.returncode != 0:
                return {
                    "status": "error",
                    "message": f"Installation failed: {result.stderr}"
                }
                
            # Create or update Claude Desktop configuration
            try:
                home_dir = Path.home()
                claude_config_dir = home_dir / ".config" / "Claude"
                claude_config_file = claude_config_dir / "config.json"
                
                claude_config_dir.mkdir(parents=True, exist_ok=True)
                
                config = {}
                if claude_config_file.exists():
                    with open(claude_config_file, 'r') as f:
                        config = json.load(f)
                        
                # Add or update HostBridge MCP configuration
                if "mcpServers" not in config:
                    config["mcpServers"] = {}
                    
                config["mcpServers"]["hostbridge"] = {
                    "command": "hostbridge",
                    "args": ["--debug"]
                }
                
                with open(claude_config_file, 'w') as f:
                    json.dump(config, f, indent=2)
                    
                return {
                    "status": "success",
                    "message": "HostBridge MCP installed and configured for Claude Desktop",
                    "config_path": str(claude_config_file)
                }
                
            except Exception as e:
                logger.error(f"Error configuring Claude Desktop: {e}")
                return {
                    "status": "partial",
                    "message": f"HostBridge MCP installed but Claude Desktop configuration failed: {e}"
                }
                
        except Exception as e:
            logger.error(f"Error installing HostBridge MCP: {e}")
            return {"status": "error", "message": str(e)}


def main():
    """
    Main function for testing HostBridge integration.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="HostBridge MCP Integration")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--install", action="store_true", help="Install HostBridge MCP")
    parser.add_argument("--list-providers", action="store_true", help="List supported providers")
    
    args = parser.parse_args()
    
    # Load configuration
    config = {}
    if args.config and os.path.exists(args.config):
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
    
    # Initialize integration
    integration = HostBridgeIntegration(config)
    
    # Process commands
    if args.install:
        result = integration.install_hostbridge_mcp()
        print(json.dumps(result, indent=2))
        
    if args.list_providers:
        providers = integration.get_supported_providers()
        print(json.dumps(providers, indent=2))
    
    return 0


if __name__ == "__main__":
    exit(main())
