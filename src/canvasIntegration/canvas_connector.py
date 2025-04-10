#!/usr/bin/env python3
"""
Canvas LMS Connector

Handles secure integration with Canvas LMS through the Canvas API and LTI.
Provides functionality for authentication, course management, and content delivery.
"""

import os
import logging
import json
import time
import uuid
import re
import hmac
import hashlib
import base64
from typing import Dict, List, Optional, Tuple, Any, Union
from urllib.parse import urlencode, quote
import secrets
from datetime import datetime, timedelta
from pathlib import Path
import requests

# Configure logging with secure practices
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Try importing Canvas API library
try:
    from canvasapi import Canvas
    CANVASAPI_AVAILABLE = True
except ImportError:
    logger.warning("CanvasAPI library not available, some features will be limited")
    CANVASAPI_AVAILABLE = False

# Try importing pylti1p3 for LTI support
try:
    from pylti1p3.registration import Registration
    from pylti1p3.message_launch import MessageLaunch
    from pylti1p3.tool_config import ToolConfJsonFile
    LTI_AVAILABLE = True
except ImportError:
    logger.warning("pylti1p3 not available, LTI features will be limited")
    LTI_AVAILABLE = False


class CanvasConnector:
    """
    Manages secure connection and interaction with Canvas LMS.
    """

    def __init__(self, config: Dict = None):
        """
        Initialize Canvas connector with configuration.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self._sanitize_config()
        
        # Setup Canvas API connection if available
        self.canvas = None
        self.api_url = self.config.get("CANVAS_API_URL", "")
        self.api_key = self.config.get("CANVAS_API_KEY", "")
        
        if self.api_url and self.api_key and CANVASAPI_AVAILABLE:
            try:
                self.canvas = Canvas(self.api_url, self.api_key)
                logger.info(f"Initialized Canvas API connection to {self.api_url}")
            except Exception as e:
                logger.error(f"Failed to initialize Canvas API: {e}")
                
        # Setup LTI configuration
        self.lti_config_dir = Path(self.config.get("LTI_CONFIG_DIR", "./lti_config"))
        self.lti_config_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup secure data storage
        self.data_dir = Path(self.config.get("DATA_DIR", "./canvas_data"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Session management
        self.sessions = {}
        self.session_ttl = int(self.config.get("SESSION_TTL", 3600))  # 1 hour default
        
    def _sanitize_config(self):
        """
        Sanitize configuration values to prevent injection attacks.
        """
        # Sanitize URL
        if "CANVAS_API_URL" in self.config:
            url = self.config["CANVAS_API_URL"]
            # Ensure URL is properly formed
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            # Remove potential script injection
            url = re.sub(r'[<>\'";]', '', url)
            self.config["CANVAS_API_URL"] = url
            
        # Sanitize file paths to prevent traversal
        for key in ["LTI_CONFIG_DIR", "DATA_DIR"]:
            if key in self.config:
                path_value = re.sub(r'\.\./', '', self.config[key])
                self.config[key] = path_value
                
    def _generate_secure_token(self, length: int = 32) -> str:
        """
        Generate a cryptographically secure token.
        
        Args:
            length: Length of token in bytes
            
        Returns:
            Secure token string
        """
        return secrets.token_hex(length)
        
    def _encrypt_sensitive_data(self, data: str, key: Optional[str] = None) -> str:
        """
        Encrypt sensitive data for storage.
        
        Args:
            data: Data to encrypt
            key: Optional encryption key
            
        Returns:
            Encrypted data string
        """
        try:
            # Use provided key or generate one from config secret
            encryption_key = key or self.config.get("SECRET_KEY", "default_key")
            
            # Simple encryption using HMAC for demonstration
            # In production, use a proper encryption library like cryptography
            h = hmac.new(
                encryption_key.encode(), 
                data.encode(), 
                hashlib.sha256
            )
            return base64.b64encode(h.digest() + data.encode()).decode()
            
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            # Return an error indicator instead of the original data
            return ""
            
    def _decrypt_sensitive_data(self, encrypted_data: str, key: Optional[str] = None) -> str:
        """
        Decrypt sensitive data.
        
        Args:
            encrypted_data: Encrypted data string
            key: Optional decryption key
            
        Returns:
            Decrypted data string
        """
        try:
            # Use provided key or generate one from config secret
            encryption_key = key or self.config.get("SECRET_KEY", "default_key")
            
            # Simple decryption for demonstration
            # In production, use a proper encryption library
            decoded = base64.b64decode(encrypted_data.encode())
            return decoded[32:].decode()  # Skip HMAC digest
            
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            return ""
            
    def create_lti_config(self, title: str, description: str) -> Dict:
        """
        Create a new LTI tool configuration for Canvas.
        
        Args:
            title: Tool title
            description: Tool description
            
        Returns:
            LTI configuration dictionary
        """
        if not LTI_AVAILABLE:
            logger.error("LTI library not available")
            return {"status": "error", "message": "LTI support not available"}
            
        try:
            # Generate secure client ID and deployment ID
            client_id = f"lti-client-{self._generate_secure_token(16)}"
            deployment_id = f"deployment-{self._generate_secure_token(8)}"
            
            # Generate secure keys
            private_key = self._generate_secure_token(32)
            public_jwk = {
                "kty": "oct",
                "use": "sig",
                "alg": "HS256",
                "kid": self._generate_secure_token(8)
            }
            
            # Base URL from config
            base_url = self.config.get("SITE_URL", "https://lucasblanco.com/ed/arh1000/fulltext")
            
            # Create LTI config
            lti_config = {
                "title": title,
                "description": description,
                "oidc_initiation_url": f"{base_url}/lti/init",
                "target_link_uri": f"{base_url}/lti/launch",
                "scopes": [
                    "https://purl.imsglobal.org/spec/lti-ags/scope/lineitem",
                    "https://purl.imsglobal.org/spec/lti-ags/scope/result.readonly",
                    "https://purl.imsglobal.org/spec/lti-nrps/scope/contextmembership.readonly"
                ],
                "extensions": [
                    {
                        "platform": "canvas.instructure.com",
                        "settings": {
                            "platform": "canvas.instructure.com",
                            "text": title,
                            "icon_url": f"{base_url}/assets/icon.png",
                            "placements": [
                                {
                                    "text": title,
                                    "enabled": True,
                                    "placement": "course_navigation",
                                    "default": "disabled",
                                    "message_type": "LtiResourceLinkRequest"
                                },
                                {
                                    "text": "Art History Resource",
                                    "enabled": True,
                                    "placement": "link_selection",
                                    "message_type": "LtiDeepLinkingRequest"
                                }
                            ]
                        }
                    }
                ],
                "public_jwk": public_jwk,
                "client_id": client_id,
                "deployment_id": deployment_id
            }
            
            # Save configuration securely
            config_id = f"lti_config_{int(time.time())}"
            config_path = self.lti_config_dir / f"{config_id}.json"
            
            with open(config_path, 'w') as f:
                json.dump(lti_config, f, indent=2)
                
            # Store private key securely (in a real implementation, use a secure key store)
            private_config = {
                "config_id": config_id,
                "client_id": client_id,
                "private_key": private_key
            }
            
            private_path = self.lti_config_dir / f"{config_id}_private.json"
            with open(private_path, 'w') as f:
                json.dump(private_config, f, indent=2)
                
            logger.info(f"Created LTI configuration: {config_id}")
            
            # Return public configuration with limited info
            return {
                "status": "success",
                "config_id": config_id,
                "title": title,
                "client_id": client_id,
                "deployment_id": deployment_id,
                "xml_url": f"{base_url}/lti/config/{config_id}.xml",
                "json_url": f"{base_url}/lti/config/{config_id}.json"
            }
            
        except Exception as e:
            logger.error(f"Error creating LTI config: {e}")
            return {"status": "error", "message": str(e)}
            
    def process_lti_launch(self, request_data: Dict, config_id: str) -> Dict:
        """
        Process an LTI launch request.
        
        Args:
            request_data: LTI launch request data
            config_id: LTI configuration ID
            
        Returns:
            Processed launch data
        """
        if not LTI_AVAILABLE:
            logger.error("LTI library not available")
            return {"status": "error", "message": "LTI support not available"}
            
        try:
            # Load configuration
            config_path = self.lti_config_dir / f"{config_id}.json"
            private_path = self.lti_config_dir / f"{config_id}_private.json"
            
            if not config_path.exists() or not private_path.exists():
                logger.error(f"LTI configuration not found: {config_id}")
                return {"status": "error", "message": "Configuration not found"}
                
            with open(config_path, 'r') as f:
                lti_config = json.load(f)
                
            with open(private_path, 'r') as f:
                private_config = json.load(f)
                
            # Validate the LTI request
            # This would use pylti1p3 in a full implementation
            
            # Extract user information and context
            user_id = request_data.get("sub", "")
            context_id = request_data.get("context_id", "")
            roles = request_data.get("roles", [])
            
            # Create session
            session_id = self._generate_secure_token(16)
            self.sessions[session_id] = {
                "user_id": user_id,
                "context_id": context_id,
                "roles": roles,
                "timestamp": time.time()
            }
            
            # Return basic session info
            return {
                "status": "success",
                "session_id": session_id,
                "user_id": user_id,
                "is_instructor": any("Instructor" in role for role in roles),
                "context_id": context_id
            }
            
        except Exception as e:
            logger.error(f"Error processing LTI launch: {e}")
            return {"status": "error", "message": str(e)}
    
    def validate_session(self, session_id: str) -> Dict:
        """
        Validate an active session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session information if valid
        """
        if session_id not in self.sessions:
            return {"status": "error", "message": "Invalid session"}
            
        session = self.sessions[session_id]
        
        # Check if session is expired
        if time.time() - session["timestamp"] > self.session_ttl:
            del self.sessions[session_id]
            return {"status": "error", "message": "Session expired"}
            
        # Update timestamp
        session["timestamp"] = time.time()
        
        return {
            "status": "success",
            "user_id": session["user_id"],
            "context_id": session["context_id"],
            "roles": session["roles"]
        }
        
    def get_course_info(self, course_id: str) -> Dict:
        """
        Get information about a Canvas course.
        
        Args:
            course_id: Canvas course ID
            
        Returns:
            Course information dictionary
        """
        if not self.canvas:
            logger.error("Canvas API not initialized")
            return {"status": "error", "message": "Canvas API not initialized"}
            
        try:
            # Validate course ID (should be numeric)
            if not course_id.isdigit():
                return {"status": "error", "message": "Invalid course ID"}
                
            # Get course data from Canvas
            course = self.canvas.get_course(course_id)
            
            # Extract relevant information
            course_info = {
                "id": course.id,
                "name": course.name,
                "code": course.course_code,
                "start_date": getattr(course, "start_at", None),
                "end_date": getattr(course, "end_at", None),
                "url": f"{self.api_url}/courses/{course.id}"
            }
            
            return {
                "status": "success",
                "course": course_info
            }
            
        except Exception as e:
            logger.error(f"Error getting course info: {e}")
            return {"status": "error", "message": str(e)}
            
    def create_module(self, course_id: str, name: str, 
                      items: List[Dict] = None) -> Dict:
        """
        Create a module in a Canvas course with textbook content.
        
        Args:
            course_id: Canvas course ID
            name: Module name
            items: List of module items
            
        Returns:
            Module creation result
        """
        if not self.canvas:
            logger.error("Canvas API not initialized")
            return {"status": "error", "message": "Canvas API not initialized"}
            
        try:
            # Validate course ID
            if not course_id.isdigit():
                return {"status": "error", "message": "Invalid course ID"}
                
            # Get the course
            course = self.canvas.get_course(course_id)
            
            # Create the module
            module = course.create_module(module={"name": name})
            
            # Add items if provided
            created_items = []
            if items:
                for item in items:
                    # Validate item data
                    if "type" not in item or "title" not in item:
                        continue
                        
                    # Create module item
                    module_item = module.create_module_item(
                        module_item={
                            "title": item["title"],
                            "type": item["type"],
                            "content_id": item.get("content_id"),
                            "external_url": item.get("external_url"),
                            "new_tab": item.get("new_tab", False)
                        }
                    )
                    
                    created_items.append({
                        "id": module_item.id,
                        "title": module_item.title,
                        "type": module_item.type
                    })
            
            return {
                "status": "success",
                "module": {
                    "id": module.id,
                    "name": module.name,
                    "items": created_items
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating module: {e}")
            return {"status": "error", "message": str(e)}
            
    def send_grade(self, course_id: str, assignment_id: str, 
                   user_id: str, score: float, max_score: float = 100.0) -> Dict:
        """
        Submit a grade for a student in Canvas.
        
        Args:
            course_id: Canvas course ID
            assignment_id: Canvas assignment ID
            user_id: Canvas user ID
            score: User's score
            max_score: Maximum possible score
            
        Returns:
            Grade submission result
        """
        if not self.canvas:
            logger.error("Canvas API not initialized")
            return {"status": "error", "message": "Canvas API not initialized"}
            
        try:
            # Validate parameters
            if not course_id.isdigit() or not assignment_id.isdigit():
                return {"status": "error", "message": "Invalid course or assignment ID"}
                
            # Normalize score to percentage
            percentage = (score / max_score) * 100
            
            # Ensure percentage is within bounds
            percentage = max(0, min(percentage, 100))
            
            # Get the course and assignment
            course = self.canvas.get_course(course_id)
            assignment = course.get_assignment(assignment_id)
            
            # Submit the grade
            submission = assignment.get_submission(user_id)
            result = submission.edit(submission={"posted_grade": percentage})
            
            return {
                "status": "success",
                "submission": {
                    "id": result.id,
                    "score": result.score,
                    "grade": result.grade
                }
            }
            
        except Exception as e:
            logger.error(f"Error submitting grade: {e}")
            return {"status": "error", "message": str(e)}
            
    def import_textbook_to_course(self, course_id: str, book_id: str,
                                 module_name: str = "Art History Textbook") -> Dict:
        """
        Import textbook content into a Canvas course.
        
        Args:
            course_id: Canvas course ID
            book_id: Textbook identifier
            module_name: Name for the module
            
        Returns:
            Import result
        """
        if not self.canvas:
            logger.error("Canvas API not initialized")
            return {"status": "error", "message": "Canvas API not initialized"}
            
        try:
            # Get textbook structure (implementation would depend on your book storage)
            # This is a placeholder
            book_url = self.config.get("SITE_URL", "https://lucasblanco.com/ed/arh1000/fulltext")
            chapters = [
                {"title": "Introduction", "path": "introduction.html"},
                {"title": "Chapter 1", "path": "chapter_01.html"},
                {"title": "Chapter 2", "path": "chapter_02.html"}
            ]
            
            # Create module items from chapters
            items = []
            for chapter in chapters:
                items.append({
                    "title": chapter["title"],
                    "type": "ExternalUrl",
                    "external_url": f"{book_url}/{chapter['path']}",
                    "new_tab": True
                })
                
            # Create module with items
            result = self.create_module(course_id, module_name, items)
            
            return result
            
        except Exception as e:
            logger.error(f"Error importing textbook: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_course_users(self, course_id: str, role: str = None) -> Dict:
        """
        Get users enrolled in a Canvas course.
        
        Args:
            course_id: Canvas course ID
            role: Optional filter by role
            
        Returns:
            List of users
        """
        if not self.canvas:
            logger.error("Canvas API not initialized")
            return {"status": "error", "message": "Canvas API not initialized"}
            
        try:
            # Validate course ID
            if not course_id.isdigit():
                return {"status": "error", "message": "Invalid course ID"}
                
            # Get the course
            course = self.canvas.get_course(course_id)
            
            # Get users based on role
            if role:
                users = course.get_users(enrollment_type=[role])
            else:
                users = course.get_users()
                
            # Format user data
            user_list = []
            for user in users:
                user_list.append({
                    "id": user.id,
                    "name": user.name,
                    "email": getattr(user, "email", None),
                    "login_id": getattr(user, "login_id", None)
                })
                
            return {
                "status": "success",
                "users": user_list,
                "count": len(user_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting course users: {e}")
            return {"status": "error", "message": str(e)}
            
    def create_assignment(self, course_id: str, title: str, 
                         description: str, points: float = 100.0) -> Dict:
        """
        Create an assignment in a Canvas course.
        
        Args:
            course_id: Canvas course ID
            title: Assignment title
            description: Assignment description
            points: Points possible
            
        Returns:
            Assignment creation result
        """
        if not self.canvas:
            logger.error("Canvas API not initialized")
            return {"status": "error", "message": "Canvas API not initialized"}
            
        try:
            # Validate course ID
            if not course_id.isdigit():
                return {"status": "error", "message": "Invalid course ID"}
                
            # Get the course
            course = self.canvas.get_course(course_id)
            
            # Create assignment
            assignment = course.create_assignment({
                "name": title,
                "description": description,
                "points_possible": points,
                "submission_types": ["external_tool"],
                "external_tool_tag_attributes": {
                    "url": f"{self.config.get('SITE_URL')}/lti/assignment_launch",
                    "new_tab": True
                }
            })
            
            return {
                "status": "success",
                "assignment": {
                    "id": assignment.id,
                    "name": assignment.name,
                    "points_possible": assignment.points_possible,
                    "html_url": assignment.html_url
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating assignment: {e}")
            return {"status": "error", "message": str(e)}


def main():
    """
    Main function for testing Canvas integration.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Canvas LMS Connector")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--create-lti", action="store_true", help="Create LTI configuration")
    parser.add_argument("--title", default="Art History Textbook", help="Tool title")
    parser.add_argument("--description", default="Art History resource for Canvas", help="Tool description")
    
    args = parser.parse_args()
    
    # Load configuration
    config = {}
    if args.config and os.path.exists(args.config):
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
    
    # Initialize connector
    connector = CanvasConnector(config)
    
    # Process commands
    if args.create_lti:
        result = connector.create_lti_config(args.title, args.description)
        print(json.dumps(result, indent=2))
    
    return 0


if __name__ == "__main__":
    exit(main())
