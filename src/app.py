#!/usr/bin/env python3
"""
Art Education Platform - Main Application

This is the entry point for the Art Education Platform, integrating all components:
- OCR and image processing
- mdBook creation and management 
- Fast Agent AI integration
- Canvas LMS integration
- Franchise template system
- Web API

This application follows secure coding practices and provides 
a streamlined workflow for professors to create and deploy
their own art education textbooks.
"""

import os
import sys
import json
import logging
import logging.config
import argparse
from pathlib import Path
from typing import Dict, Optional, Any, Union
import uvicorn

# Set up base paths
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# Import components
from src.api.api_router import create_app
from src.ocr.conversion_pipeline import ConversionPipeline
from src.mdbook.mdbook_manager import MdBookManager
from src.fastAgentIntegration.agent_manager import AgentManager
from src.canvasIntegration.canvas_connector import CanvasConnector
from src.franchise.template_manager import TemplateManager
from src.franchise.deployment_manager import DeploymentManager


def configure_logging(config: Dict) -> None:
    """
    Configure application logging based on configuration.
    
    Args:
        config: Configuration dictionary
    """
    log_level = config.get("LOG_LEVEL", "INFO").upper()
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file = config.get("LOG_FILE")
    
    logging_config = {
        "version": 1,
        "formatters": {
            "default": {
                "format": log_format
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "level": log_level,
                "stream": "ext://sys.stdout"
            }
        },
        "root": {
            "level": log_level,
            "handlers": ["console"]
        }
    }
    
    # Add file handler if log file is specified
    if log_file:
        log_dir = Path(log_file).parent
        try:
            if not log_dir.exists():
                log_dir.mkdir(parents=True)
            
            logging_config["handlers"]["file"] = {
                "class": "logging.FileHandler",
                "formatter": "default",
                "level": log_level,
                "filename": log_file
            }
            logging_config["root"]["handlers"].append("file")
        except Exception as e:
            print(f"Error configuring file logging: {e}")
    
    # Apply configuration
    logging.config.dictConfig(logging_config)


def load_config(config_path: Optional[str] = None) -> Dict:
    """
    Load application configuration from a file or environment variables.
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        Configuration dictionary
    """
    config = {}
    
    # 1. Load environment variables
    env_vars = [
        "DEBUG", "LOG_LEVEL", "LOG_FILE", "HOST", "PORT", 
        "SECRET_KEY", "SITE_URL", "CANVAS_API_URL", "CANVAS_API_KEY",
        "ALLOWED_ORIGINS", "TOKEN_EXPIRE_MINUTES", "UPLOAD_DIR",
        "TEMPLATES_DIR", "STATIC_DIR", "DATA_DIR", "LTI_CONFIG_DIR",
        "INSTANCES_DIR", "DEPLOYMENTS_DIR", "DEFAULT_DOMAIN"
    ]
    
    for var in env_vars:
        if var in os.environ:
            config[var] = os.environ[var]
    
    # 2. Override with file configuration if provided
    if config_path:
        path = Path(config_path)
        
        if path.exists():
            try:
                with open(path, 'r') as f:
                    file_config = json.load(f)
                    config.update(file_config)
            except Exception as e:
                print(f"Error loading configuration file: {e}")
    
    # 3. Set default values for required config
    defaults = {
        "DEBUG": False,
        "LOG_LEVEL": "INFO",
        "HOST": "127.0.0.1",
        "PORT": 8000,
        "SITE_URL": "https://lucasblanco.com/ed/arh1000/fulltext",
        "ALLOWED_ORIGINS": ["*"],
        "TOKEN_EXPIRE_MINUTES": 60,
        "UPLOAD_DIR": str(BASE_DIR / "uploads"),
        "TEMPLATES_DIR": str(BASE_DIR / "templates"),
        "STATIC_DIR": str(BASE_DIR / "static"),
        "DATA_DIR": str(BASE_DIR / "data"),
        "INSTANCES_DIR": str(BASE_DIR / "instances"),
        "DEPLOYMENTS_DIR": str(BASE_DIR / "deployments"),
        "DEFAULT_DOMAIN": "lucasblanco.com/ed"
    }
    
    # Apply defaults for missing values
    for key, value in defaults.items():
        if key not in config:
            config[key] = value
    
    # Ensure critical directories exist
    for dir_key in ["UPLOAD_DIR", "TEMPLATES_DIR", "STATIC_DIR", "DATA_DIR"]:
        dir_path = Path(config[dir_key])
        if not dir_path.exists():
            try:
                dir_path.mkdir(parents=True)
            except Exception as e:
                print(f"Error creating directory {dir_key}: {e}")
    
    return config


def validate_config(config: Dict) -> bool:
    """
    Validate configuration for required values.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        True if valid, False otherwise
    """
    required_keys = [
        "HOST", "PORT", "SITE_URL", "UPLOAD_DIR", 
        "TEMPLATES_DIR", "STATIC_DIR", "DATA_DIR"
    ]
    
    missing_keys = [key for key in required_keys if key not in config]
    
    if missing_keys:
        print(f"Missing required configuration: {', '.join(missing_keys)}")
        return False
    
    # Validate security settings
    if "SECRET_KEY" not in config:
        print("WARNING: No SECRET_KEY provided. A temporary key will be generated.")
        print("For production use, please set a permanent SECRET_KEY.")
    
    # Validate API URLs
    if "CANVAS_API_URL" in config and not (
        config["CANVAS_API_URL"].startswith("http://") or 
        config["CANVAS_API_URL"].startswith("https://")
    ):
        print(f"Invalid CANVAS_API_URL: {config['CANVAS_API_URL']}")
        print("URL must start with http:// or https://")
        return False
    
    return True


def create_app_instance(config: Dict):
    """
    Create the FastAPI application instance.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        FastAPI application instance
    """
    # Create FastAPI application
    return create_app(config)


def run_server(app, config: Dict):
    """
    Run the web server.
    
    Args:
        app: FastAPI application instance
        config: Configuration dictionary
    """
    host = config.get("HOST", "127.0.0.1")
    port = int(config.get("PORT", 8000))
    log_level = config.get("LOG_LEVEL", "info").lower()
    
    print(f"Starting server at http://{host}:{port}")
    uvicorn.run(
        app, 
        host=host, 
        port=port,
        log_level=log_level
    )


def main():
    """
    Main entry point for the application.
    """
    parser = argparse.ArgumentParser(description="Art Education Platform")
    parser.add_argument(
        "--config", 
        help="Path to configuration file (JSON)"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug mode"
    )
    parser.add_argument(
        "--log-level", 
        choices=["debug", "info", "warning", "error", "critical"],
        help="Set logging level"
    )
    parser.add_argument(
        "--host", 
        help="Server host address"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        help="Server port number"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Override config with command-line arguments
    if args.debug:
        config["DEBUG"] = True
    if args.log_level:
        config["LOG_LEVEL"] = args.log_level.upper()
    if args.host:
        config["HOST"] = args.host
    if args.port:
        config["PORT"] = args.port
    
    # Validate configuration
    if not validate_config(config):
        sys.exit(1)
    
    # Configure logging
    configure_logging(config)
    
    # Create and run application
    app = create_app_instance(config)
    run_server(app, config)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
