#!/usr/bin/env python3
"""
API Router

Core API router for the Art Education Platform, implementing secure
endpoints for OCR processing, mdBook creation, Canvas integration,
and franchise management.
"""

import os
import logging
import json
import time
import uuid
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Body, Query, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import jwt
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, validator

# Setup logging with security in mind
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import platform components
try:
    from ..ocr.conversion_pipeline import ConversionPipeline
    from ..mdbook.mdbook_manager import MdBookManager
    from ..fastAgentIntegration.agent_manager import AgentManager
    from ..canvasIntegration.canvas_connector import CanvasConnector
    from ..franchise.template_manager import TemplateManager
    from ..franchise.deployment_manager import DeploymentManager
except ImportError:
    # Alternative import style for direct execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
    from src.ocr.conversion_pipeline import ConversionPipeline
    from src.mdbook.mdbook_manager import MdBookManager
    from src.fastAgentIntegration.agent_manager import AgentManager
    from src.canvasIntegration.canvas_connector import CanvasConnector
    from src.franchise.template_manager import TemplateManager
    from src.franchise.deployment_manager import DeploymentManager


# Rate limiting settings
RATE_LIMIT = 100  # requests per minute
RATE_WINDOW = 60  # seconds


# Pydantic models for request/response validation
class TokenData(BaseModel):
    username: Optional[str] = None
    scopes: List[str] = []


class UserBase(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    disabled: Optional[bool] = None


class UserIn(UserBase):
    password: str


class User(UserBase):
    id: str
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class OcrRequest(BaseModel):
    file_path: str = Field(..., description="Path to image file for OCR")
    language: Optional[str] = Field("eng", description="OCR language")
    output_format: Optional[str] = Field("markdown", description="Output format")


class MdBookRequest(BaseModel):
    book_id: Optional[str] = Field(None, description="Book ID for existing book")
    title: str = Field(..., description="Book title")
    author: str = Field(..., description="Book author")
    description: Optional[str] = Field("", description="Book description")
    source_dir: Optional[str] = Field(None, description="Source directory with markdown files")


class CanvasIntegrationRequest(BaseModel):
    course_id: str = Field(..., description="Canvas course ID")
    book_id: str = Field(..., description="mdBook ID to integrate")
    module_name: Optional[str] = Field("Art History Textbook", description="Module name in Canvas")


class TemplateCreateRequest(BaseModel):
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    author: str = Field(..., description="Template author")
    template_type: Optional[str] = Field("textbook", description="Template type")
    files: Optional[Dict] = Field({}, description="Files to include")


class InstanceCreateRequest(BaseModel):
    template_id: str = Field(..., description="Template ID to use")
    name: str = Field(..., description="Instance name")
    subscription_plan: Optional[str] = Field("free", description="Subscription plan")


class DeploymentRequest(BaseModel):
    instance_id: str = Field(..., description="Instance ID to deploy")
    deployment_type: str = Field(..., description="Type of deployment")
    subdomain: Optional[str] = Field(None, description="Subdomain for hosted option")
    custom_domain: Optional[str] = Field(None, description="Custom domain for self-hosted")


# API Router class
class ApiRouter:
    """
    Core API router handling all endpoints for the Art Education Platform.
    """

    def __init__(self, config: Dict = None):
        """
        Initialize API router with configuration.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        
        # Setup FastAPI app
        self.app = FastAPI(
            title="Art Education Platform API",
            description="API for Art History Textbook Conversion and Integration",
            version="1.0.0",
            docs_url="/api/docs",
            redoc_url="/api/redoc",
            openapi_url="/api/openapi.json"
        )
        
        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.get("ALLOWED_ORIGINS", ["*"]),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Setup security
        self.secret_key = self.config.get("SECRET_KEY", "")
        if not self.secret_key:
            self.secret_key = str(uuid.uuid4())
            logger.warning("No SECRET_KEY provided, using generated key")
            
        self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
        self.token_expire_minutes = int(self.config.get("TOKEN_EXPIRE_MINUTES", 60))
        
        # Setup component managers
        self.conversion_pipeline = ConversionPipeline(self.config)
        self.mdbook_manager = MdBookManager(self.config)
        self.agent_manager = AgentManager(self.config)
        self.canvas_connector = CanvasConnector(self.config)
        self.template_manager = TemplateManager(self.config)
        self.deployment_manager = DeploymentManager(self.config)
        
        # Setup template directory
        self.templates_dir = Path(self.config.get("TEMPLATES_DIR", "./templates"))
        self.templates = Jinja2Templates(directory=str(self.templates_dir))
        
        # Setup static files
        self.static_dir = Path(self.config.get("STATIC_DIR", "./static"))
        self.app.mount("/static", StaticFiles(directory=str(self.static_dir)), name="static")
        
        # Rate limiting
        self.request_counts = {}
        
        # Create API routes
        self._create_routes()
        
    def _create_routes(self):
        """Create all API routes."""
        # Authentication routes
        @self.app.post("/api/auth/token", response_model=TokenResponse)
        async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
            return await self._login_handler(form_data)
        
        # Rate limiting middleware
        @self.app.middleware("http")
        async def rate_limit_middleware(request: Request, call_next):
            return await self._rate_limit_middleware(request, call_next)
        
        # OCR routes
        @self.app.post("/api/ocr/process", response_model=Dict)
        async def process_image(
            request: OcrRequest, 
            token: str = Depends(self.oauth2_scheme)
        ):
            user = await self._get_current_user(token)
            return await self._process_ocr(request, user)
        
        @self.app.post("/api/ocr/upload", response_model=Dict)
        async def upload_image(
            file: UploadFile = File(...),
            token: str = Depends(self.oauth2_scheme)
        ):
            user = await self._get_current_user(token)
            return await self._upload_file(file, user)
        
        # mdBook routes
        @self.app.post("/api/mdbook/create", response_model=Dict)
        async def create_book(
            request: MdBookRequest,
            token: str = Depends(self.oauth2_scheme)
        ):
            user = await self._get_current_user(token)
            return await self._create_mdbook(request, user)
        
        @self.app.get("/api/mdbook/{book_id}", response_model=Dict)
        async def get_book(
            book_id: str,
            token: str = Depends(self.oauth2_scheme)
        ):
            user = await self._get_current_user(token)
            return await self._get_mdbook(book_id, user)
        
        @self.app.post("/api/mdbook/{book_id}/build", response_model=Dict)
        async def build_book(
            book_id: str,
            token: str = Depends(self.oauth2_scheme)
        ):
            user = await self._get_current_user(token)
            return await self._build_mdbook(book_id, user)
        
        # Fast Agent routes
        @self.app.post("/api/agent/query", response_model=Dict)
        async def query_agent(
            query: str = Body(..., embed=True),
            book_id: str = Body(..., embed=True),
            token: str = Depends(self.oauth2_scheme)
        ):
            user = await self._get_current_user(token)
            return await self._query_agent(query, book_id, user)
        
        # Canvas integration routes
        @self.app.post("/api/canvas/integrate", response_model=Dict)
        async def integrate_with_canvas(
            request: CanvasIntegrationRequest,
            token: str = Depends(self.oauth2_scheme)
        ):
            user = await self._get_current_user(token)
            return await self._integrate_canvas(request, user)
        
        @self.app.post("/api/canvas/lti/config", response_model=Dict)
        async def create_lti_config(
            title: str = Body(..., embed=True),
            description: str = Body(..., embed=True),
            token: str = Depends(self.oauth2_scheme)
        ):
            user = await self._get_current_user(token)
            return await self._create_lti_config(title, description, user)
        
        # Franchise template routes
        @self.app.get("/api/templates", response_model=List[Dict])
        async def list_templates(
            template_type: Optional[str] = None,
            token: str = Depends(self.oauth2_scheme)
        ):
            user = await self._get_current_user(token)
            return self.template_manager.get_templates(template_type)
        
        @self.app.post("/api/templates/create", response_model=Dict)
        async def create_template(
            request: TemplateCreateRequest,
            token: str = Depends(self.oauth2_scheme)
        ):
            user = await self._get_current_user(token)
            return self.template_manager.create_template(
                name=request.name,
                description=request.description,
                author=request.author,
                template_type=request.template_type,
                files=request.files
            )
        
        @self.app.get("/api/templates/{template_id}", response_model=Dict)
        async def get_template(
            template_id: str,
            token: str = Depends(self.oauth2_scheme)
        ):
            user = await self._get_current_user(token)
            return self.template_manager.get_template_details(template_id)
        
        # Instance routes
        @self.app.post("/api/instances/create", response_model=Dict)
        async def create_instance(
            request: InstanceCreateRequest,
            token: str = Depends(self.oauth2_scheme)
        ):
            user = await self._get_current_user(token)
            owner_info = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "name": user.full_name
            }
            return self.template_manager.create_instance(
                template_id=request.template_id,
                name=request.name,
                owner=owner_info,
                subscription_plan=request.subscription_plan
            )
        
        @self.app.get("/api/instances", response_model=List[Dict])
        async def list_instances(
            token: str = Depends(self.oauth2_scheme)
        ):
            user = await self._get_current_user(token)
            return self.template_manager.get_instances(user.id)
        
        @self.app.get("/api/instances/{instance_id}", response_model=Dict)
        async def get_instance(
            instance_id: str,
            token: str = Depends(self.oauth2_scheme)
        ):
            user = await self._get_current_user(token)
            return self.template_manager.get_instance_details(instance_id)
        
        # Deployment routes
        @self.app.post("/api/deploy", response_model=Dict)
        async def deploy_instance(
            request: DeploymentRequest,
            token: str = Depends(self.oauth2_scheme)
        ):
            user = await self._get_current_user(token)
            return self.deployment_manager.deploy_instance(
                instance_id=request.instance_id,
                deployment_type=request.deployment_type,
                subdomain=request.subdomain,
                custom_domain=request.custom_domain
            )
        
        @self.app.get("/api/deployments", response_model=List[Dict])
        async def list_deployments(
            instance_id: Optional[str] = None,
            token: str = Depends(self.oauth2_scheme)
        ):
            user = await self._get_current_user(token)
            return self.deployment_manager.get_deployments(instance_id)
        
        @self.app.get("/api/deployment/options", response_model=Dict)
        async def get_deployment_options(
            token: str = Depends(self.oauth2_scheme)
        ):
            user = await self._get_current_user(token)
            return self.deployment_manager.get_deployment_options()
        
        @self.app.post("/api/deployment/validate-subdomain", response_model=Dict)
        async def validate_subdomain(
            subdomain: str = Body(..., embed=True),
            token: str = Depends(self.oauth2_scheme)
        ):
            user = await self._get_current_user(token)
            return self.deployment_manager.validate_subdomain(subdomain)
        
        # Main page
        @self.app.get("/", response_class=HTMLResponse)
        async def root(request: Request):
            return self.templates.TemplateResponse(
                "index.html", {"request": request, "title": "Art Education Platform"}
            )
            
    async def _rate_limit_middleware(self, request: Request, call_next):
        """
        Rate limiting middleware to prevent abuse.
        
        Args:
            request: FastAPI request
            call_next: Next middleware function
            
        Returns:
            Response
        """
        client_ip = request.client.host
        current_time = time.time()
        
        # Clean old entries
        self.request_counts = {
            ip: (count, timestamp) 
            for ip, (count, timestamp) in self.request_counts.items()
            if current_time - timestamp < RATE_WINDOW
        }
        
        # Check current client
        if client_ip in self.request_counts:
            count, timestamp = self.request_counts[client_ip]
            # If within time window, increment
            if current_time - timestamp < RATE_WINDOW:
                count += 1
                if count > RATE_LIMIT:
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={"detail": "Rate limit exceeded"}
                    )
            else:
                # New window
                count = 1
                
            self.request_counts[client_ip] = (count, current_time)
        else:
            # First request
            self.request_counts[client_ip] = (1, current_time)
            
        return await call_next(request)
        
    async def _login_handler(self, form_data: OAuth2PasswordRequestForm):
        """
        Handle user login and token generation.
        
        Args:
            form_data: Login form data
            
        Returns:
            Access token response
        """
        # In a real implementation, this would validate against a database
        # For now, accept any login for demonstration
        user_id = str(uuid.uuid4())
        
        # Create access token
        access_token_expires = timedelta(minutes=self.token_expire_minutes)
        access_token = self._create_access_token(
            data={"sub": form_data.username, "id": user_id},
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": self.token_expire_minutes * 60
        }
        
    def _create_access_token(self, data: Dict, expires_delta: timedelta = None) -> str:
        """
        Create JWT access token.
        
        Args:
            data: Token data
            expires_delta: Optional expiration time
            
        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
            
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm="HS256")
        
        return encoded_jwt
        
    async def _get_current_user(self, token: str) -> User:
        """
        Get current user from JWT token.
        
        Args:
            token: JWT token
            
        Returns:
            User object
            
        Raises:
            HTTPException: If token is invalid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            username = payload.get("sub")
            user_id = payload.get("id")
            
            if username is None or user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
                
            token_data = TokenData(username=username)
            
            # In a real implementation, this would fetch user from database
            # For now, create a user object from token data
            user = User(
                id=user_id,
                username=username,
                email=f"{username}@example.com",
                full_name=username.title(),
                disabled=False,
                created_at=datetime.utcnow().isoformat()
            )
            
            return user
            
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
    async def _process_ocr(self, request: OcrRequest, user: User) -> Dict:
        """
        Process OCR request.
        
        Args:
            request: OCR request
            user: Current user
            
        Returns:
            OCR processing result
        """
        try:
            # Validate and sanitize file path
            file_path = Path(request.file_path)
            if not file_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found"
                )
                
            # Process OCR
            result = self.conversion_pipeline.process_image(
                image_path=str(file_path),
                language=request.language,
                output_format=request.output_format
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing OCR: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
            
    async def _upload_file(self, file: UploadFile, user: User) -> Dict:
        """
        Handle file upload.
        
        Args:
            file: Uploaded file
            user: Current user
            
        Returns:
            Upload result
        """
        try:
            # Generate unique filename
            file_id = str(uuid.uuid4())
            filename = f"{file_id}_{file.filename}"
            
            # Determine upload directory
            upload_dir = Path(self.config.get("UPLOAD_DIR", "./uploads"))
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            # Save file
            file_path = upload_dir / filename
            with open(file_path, "wb") as buffer:
                buffer.write(await file.read())
                
            return {
                "status": "success",
                "file_id": file_id,
                "filename": file.filename,
                "path": str(file_path),
                "size": os.path.getsize(file_path)
            }
            
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
            
    async def _create_mdbook(self, request: MdBookRequest, user: User) -> Dict:
        """
        Create or update mdBook.
        
        Args:
            request: mdBook request
            user: Current user
            
        Returns:
            mdBook creation result
        """
        try:
            # Check if updating existing book
            if request.book_id:
                # Update existing book
                result = self.mdbook_manager.update_book(
                    book_id=request.book_id,
                    title=request.title,
                    author=request.author,
                    description=request.description
                )
            else:
                # Create new book
                result = self.mdbook_manager.create_book(
                    title=request.title,
                    author=request.author,
                    description=request.description
                )
                
            # Import source directory if provided
            if request.source_dir and result.get("status") == "success":
                book_id = result.get("book_id")
                source_dir = Path(request.source_dir)
                
                if source_dir.exists() and source_dir.is_dir():
                    import_result = self.mdbook_manager.import_markdown_directory(
                        book_id=book_id,
                        source_dir=str(source_dir)
                    )
                    
                    # Merge results
                    result.update({
                        "import_status": import_result.get("status"),
                        "import_message": import_result.get("message"),
                        "files_imported": import_result.get("files_imported", 0)
                    })
                    
            return result
            
        except Exception as e:
            logger.error(f"Error creating mdBook: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
            
    async def _get_mdbook(self, book_id: str, user: User) -> Dict:
        """
        Get mdBook details.
        
        Args:
            book_id: mdBook identifier
            user: Current user
            
        Returns:
            mdBook details
        """
        try:
            result = self.mdbook_manager.get_book_details(book_id)
            
            if result.get("status") != "success":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result.get("message", "Book not found")
                )
                
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting mdBook: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
            
    async def _build_mdbook(self, book_id: str, user: User) -> Dict:
        """
        Build mdBook.
        
        Args:
            book_id: mdBook identifier
            user: Current user
            
        Returns:
            Build result
        """
        try:
            result = self.mdbook_manager.build_book(book_id)
            
            if result.get("status") != "success":
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.get("message", "Build failed")
                )
                
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error building mdBook: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
            
    async def _query_agent(self, query: str, book_id: str, user: User) -> Dict:
        """
        Query Fast Agent for a book.
        
        Args:
            query: User query
            book_id: mdBook identifier
            user: Current user
            
        Returns:
            Agent response
        """
        try:
            # Validate book existence
            book_details = self.mdbook_manager.get_book_details(book_id)
            if book_details.get("status") != "success":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Book not found"
                )
                
            # Query agent
            result = self.agent_manager.query(
                query=query,
                book_id=book_id,
                user_id=user.id
            )
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error querying agent: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
            
    async def _integrate_canvas(self, request: CanvasIntegrationRequest, user: User) -> Dict:
        """
        Integrate mdBook with Canvas LMS.
        
        Args:
            request: Canvas integration request
            user: Current user
            
        Returns:
            Integration result
        """
        try:
            # Validate book existence
            book_details = self.mdbook_manager.get_book_details(request.book_id)
            if book_details.get("status") != "success":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Book not found"
                )
                
            # Integrate with Canvas
            result = self.canvas_connector.import_textbook_to_course(
                course_id=request.course_id,
                book_id=request.book_id,
                module_name=request.module_name
            )
            
            if result.get("status") != "success":
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.get("message", "Integration failed")
                )
                
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error integrating with Canvas: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
            
    async def _create_lti_config(self, title: str, description: str, user: User) -> Dict:
        """
        Create LTI configuration for Canvas.
        
        Args:
            title: Tool title
            description: Tool description
            user: Current user
            
        Returns:
            LTI configuration
        """
        try:
            result = self.canvas_connector.create_lti_config(
                title=title,
                description=description
            )
            
            if result.get("status") != "success":
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.get("message", "LTI configuration failed")
                )
                
            return result
            
        except Exception as e:
            logger.error(f"Error creating LTI configuration: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )


def create_app(config: Dict = None) -> FastAPI:
    """
    Create FastAPI application with all routes.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        FastAPI application
    """
    router = ApiRouter(config)
    return router.app


def main():
    """
    Main function for running the API directly.
    """
    import uvicorn
    import argparse
    
    parser = argparse.ArgumentParser(description="Art Education Platform API")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--host", default="127.0.0.1", help="Host address")
    parser.add_argument("--port", type=int, default=8000, help="Port number")
    
    args = parser.parse_args()
    
    # Load configuration
    config = {}
    if args.config and os.path.exists(args.config):
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
    
    # Create app
    app = create_app(config)
    
    # Run server
    uvicorn.run(
        app, 
        host=args.host, 
        port=args.port,
        log_level=config.get("LOG_LEVEL", "info").lower()
    )
    
    return 0


if __name__ == "__main__":
    exit(main())
