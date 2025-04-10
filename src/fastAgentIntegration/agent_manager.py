#!/usr/bin/env python3
"""
Fast Agent Manager for Art Education Platform

Implements an optimized integration with Fast Agent that reduces API costs
through local vector embeddings, efficient caching, and retrieval-augmented
generation.

Security Measures:
- Input validation and sanitization
- Rate limiting to prevent abuse
- Output filtering for sensitive information
- Secure credential handling
- Proper error handling and logging
"""

import os
import json
import logging
import time
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
import uuid
from datetime import datetime
import threading
import queue

# Configure logging with secure practices
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("agent_manager.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import optional dependencies
try:
    from langchain.vectorstores import FAISS
    from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.document_loaders import DirectoryLoader
    LANGCHAIN_AVAILABLE = True
except ImportError:
    logger.warning("LangChain not available, some features will be limited")
    LANGCHAIN_AVAILABLE = False

try:
    import fast_agent
    FAST_AGENT_AVAILABLE = True
except ImportError:
    logger.warning("Fast Agent not available, will use fallback mechanisms")
    FAST_AGENT_AVAILABLE = False


class AgentManager:
    """
    Manages Fast Agent integration with security, optimization,
    and cost-saving features.
    """

    def __init__(self, config: Dict = None):
        """
        Initialize the Agent Manager with configuration.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self._sanitize_config()
        
        # Setup security and resource controls
        self.rate_limits = {
            'default': {'requests': 10, 'window': 60},  # 10 requests per minute
            'premium': {'requests': 30, 'window': 60},  # 30 requests per minute
        }
        self.request_history = {}
        self.request_lock = threading.Lock()
        
        # Vector database setup
        self.vector_db = None
        self.embeddings_model = None
        self.vector_db_path = Path(self.config.get("VECTOR_DB_PATH", "./vector_store"))
        
        # Response cache setup
        self.cache_dir = Path(self.config.get("CACHE_DIR", "./cache"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = int(self.config.get("CACHE_TTL", 86400))  # 24 hours default
        
        # Initialize components
        self._initialize_vector_store()
        self._initialize_agent()
        
        # Task queue for batch processing
        self.task_queue = queue.Queue()
        self.processing_thread = threading.Thread(target=self._process_batch_tasks, daemon=True)
        self.processing_thread.start()

    def _sanitize_config(self):
        """
        Sanitize configuration parameters to prevent injection attacks.
        """
        # Sanitize critical parameters that could be vulnerable
        for key in ["MODEL_PATH", "VECTOR_DB_PATH", "CACHE_DIR"]:
            if key in self.config:
                # Remove path traversal attempts
                sanitized_value = re.sub(r'\.\./', '', self.config[key])
                self.config[key] = sanitized_value
                
        # Validate numeric parameters
        for key in ["CONTEXT_SIZE", "MAX_TOKENS", "TEMPERATURE"]:
            if key in self.config:
                try:
                    self.config[key] = float(self.config[key])
                except (ValueError, TypeError):
                    # Set to safe defaults if invalid
                    defaults = {"CONTEXT_SIZE": 4096, "MAX_TOKENS": 1024, "TEMPERATURE": 0.7}
                    logger.warning(f"Invalid {key} value, using default: {defaults[key]}")
                    self.config[key] = defaults[key]
    
    def _initialize_vector_store(self):
        """
        Initialize the vector store for document retrieval.
        """
        if not LANGCHAIN_AVAILABLE:
            logger.warning("LangChain not available, Vector DB functionality disabled")
            return
            
        self.vector_db_path.mkdir(parents=True, exist_ok=True)
        embedding_model_name = self.config.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        
        try:
            logger.info(f"Initializing vector store with model {embedding_model_name}")
            self.embeddings_model = SentenceTransformerEmbeddings(model_name=embedding_model_name)
            
            # Check if vector store exists
            if (self.vector_db_path / "index.faiss").exists():
                self.vector_db = FAISS.load_local(
                    self.vector_db_path, 
                    self.embeddings_model
                )
                logger.info(f"Loaded existing vector store from {self.vector_db_path}")
            else:
                logger.info("No existing vector store found, will create when content is added")
        except Exception as e:
            logger.error(f"Error initializing vector store: {e}")
            self.embeddings_model = None
    
    def _initialize_agent(self):
        """
        Initialize the Fast Agent with appropriate security settings.
        """
        if not FAST_AGENT_AVAILABLE:
            logger.warning("Fast Agent not available, will use fallback mode")
            return
            
        try:
            # Safely get model parameters with defaults
            model_path = self.config.get("MODEL_PATH", "")
            model_type = self.config.get("MODEL_TYPE", "llama")
            context_size = int(self.config.get("CONTEXT_SIZE", 4096))
            max_tokens = int(self.config.get("MAX_TOKENS", 1024))
            temperature = float(self.config.get("TEMPERATURE", 0.7))
            
            # Validate model path exists if specified
            if model_path and not os.path.exists(model_path):
                logger.error(f"Model path not found: {model_path}")
                model_path = ""
                
            # Initialize Fast Agent with controlled parameters
            if model_path:
                logger.info(f"Initializing Fast Agent with local model: {model_path}")
                # This would be implementation-specific to Fast Agent
                # fast_agent.initialize(...)
            else:
                logger.info("Initializing Fast Agent with default settings")
                # Use default configuration
                # fast_agent.initialize(...)
                
        except Exception as e:
            logger.error(f"Error initializing Fast Agent: {e}")
    
    def index_document(self, document_path: str, metadata: Dict = None) -> bool:
        """
        Index a document into the vector store for retrieval.
        
        Args:
            document_path: Path to document file or directory
            metadata: Optional metadata about the document
            
        Returns:
            True if successful, False otherwise
        """
        if not LANGCHAIN_AVAILABLE or not self.embeddings_model:
            logger.error("Vector indexing not available - missing dependencies")
            return False
            
        try:
            # Validate the path
            path = Path(document_path)
            if not path.exists():
                logger.error(f"Document path does not exist: {path}")
                return False
                
            # Process based on whether it's a file or directory
            if path.is_file():
                documents = self._process_file(path, metadata)
            elif path.is_dir():
                # Load multiple files from directory with document loader
                loader = DirectoryLoader(document_path, glob="**/*.md")
                documents = loader.load()
                
                # Add metadata if provided
                if metadata:
                    for doc in documents:
                        doc.metadata.update(metadata)
            else:
                logger.error(f"Path is neither file nor directory: {path}")
                return False
                
            # Split text into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=100,
                length_function=len,
            )
            chunks = text_splitter.split_documents(documents)
            
            # Create or update vector store
            if self.vector_db is None:
                self.vector_db = FAISS.from_documents(chunks, self.embeddings_model)
                self.vector_db.save_local(self.vector_db_path)
                logger.info(f"Created new vector store at {self.vector_db_path}")
            else:
                self.vector_db.add_documents(chunks)
                self.vector_db.save_local(self.vector_db_path)
                logger.info(f"Updated vector store with {len(chunks)} chunks")
                
            return True
                
        except Exception as e:
            logger.error(f"Error indexing document: {e}")
            return False
    
    def _process_file(self, file_path: Path, metadata: Dict = None) -> List:
        """
        Process a single file for indexing.
        
        Args:
            file_path: Path to the file
            metadata: Optional metadata
            
        Returns:
            List of document objects
        """
        from langchain.document_loaders import TextLoader
        from langchain.schema import Document
        
        # Set up metadata with secure defaults
        meta = {
            "source": str(file_path),
            "filename": file_path.name,
            "created_at": datetime.now().isoformat(),
        }
        
        if metadata:
            meta.update(metadata)
            
        try:
            # Load the document based on file type
            if file_path.suffix.lower() == ".md":
                loader = TextLoader(str(file_path))
                documents = loader.load()
                
                # Update with our metadata
                for doc in documents:
                    doc.metadata.update(meta)
                    
                return documents
            else:
                # Basic handling for other text files
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                return [Document(page_content=content, metadata=meta)]
                
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return []
    
    def check_rate_limit(self, user_id: str, tier: str = "default") -> bool:
        """
        Check if a request is within rate limits.
        
        Args:
            user_id: User identifier
            tier: Service tier (default, premium)
            
        Returns:
            True if request is allowed, False if rate limited
        """
        with self.request_lock:
            # Get limit configuration for tier
            limits = self.rate_limits.get(tier, self.rate_limits["default"])
            max_requests = limits["requests"]
            window = limits["window"]
            
            # Get current time
            now = time.time()
            
            # Initialize or clean history
            if user_id not in self.request_history:
                self.request_history[user_id] = []
            else:
                # Remove entries outside the time window
                self.request_history[user_id] = [
                    timestamp for timestamp in self.request_history[user_id]
                    if now - timestamp < window
                ]
                
            # Check if under limit
            if len(self.request_history[user_id]) < max_requests:
                # Record this request
                self.request_history[user_id].append(now)
                return True
            else:
                logger.warning(f"Rate limit exceeded for user {user_id}")
                return False
    
    def get_from_cache(self, query: str, context: Dict) -> Optional[Dict]:
        """
        Try to retrieve a response from the cache.
        
        Args:
            query: User query
            context: Request context
            
        Returns:
            Cached response or None if not found/expired
        """
        # Create a cache key from query and relevant context
        context_str = json.dumps({k: v for k, v in context.items() if k in ["page", "section"]})
        cache_key = hashlib.md5((query + context_str).encode()).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
            
        try:
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
                
            # Check if cache is expired
            if time.time() - cached_data.get("timestamp", 0) > self.cache_ttl:
                logger.info(f"Cache expired for key {cache_key}")
                return None
                
            logger.info(f"Cache hit for query: {query[:30]}...")
            return cached_data.get("response")
            
        except Exception as e:
            logger.error(f"Error reading from cache: {e}")
            return None
    
    def save_to_cache(self, query: str, context: Dict, response: Dict):
        """
        Save a response to the cache.
        
        Args:
            query: User query
            context: Request context
            response: Response data to cache
        """
        # Create a cache key from query and relevant context
        context_str = json.dumps({k: v for k, v in context.items() if k in ["page", "section"]})
        cache_key = hashlib.md5((query + context_str).encode()).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            cache_data = {
                "query": query,
                "context": context,
                "response": response,
                "timestamp": time.time()
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
                
            logger.info(f"Saved response to cache: {cache_key}")
            
        except Exception as e:
            logger.error(f"Error saving to cache: {e}")
    
    def _retrieve_context(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Retrieve relevant context from the vector store.
        
        Args:
            query: User query
            top_k: Number of results to retrieve
            
        Returns:
            List of relevant document chunks with metadata
        """
        if not LANGCHAIN_AVAILABLE or not self.vector_db:
            logger.warning("Vector retrieval not available")
            return []
            
        try:
            docs = self.vector_db.similarity_search(query, k=top_k)
            
            # Format results
            results = []
            for doc in docs:
                results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata
                })
                
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return []
    
    def _process_batch_tasks(self):
        """
        Background thread to process non-time-sensitive batch tasks.
        """
        while True:
            try:
                task = self.task_queue.get()
                
                if task["type"] == "index":
                    self.index_document(task["path"], task.get("metadata"))
                elif task["type"] == "cache_cleanup":
                    self._clean_expired_cache()
                # Add other batch tasks as needed
                
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing batch task: {e}")
            
            # Sleep to prevent 100% CPU usage
            time.sleep(0.1)
            
    def _clean_expired_cache(self):
        """
        Clean expired entries from the cache.
        """
        try:
            now = time.time()
            count = 0
            
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, 'r') as f:
                        data = json.load(f)
                    
                    if now - data.get("timestamp", 0) > self.cache_ttl:
                        cache_file.unlink()
                        count += 1
                except Exception as e:
                    logger.error(f"Error processing cache file {cache_file}: {e}")
                    
            logger.info(f"Cleaned {count} expired cache entries")
            
        except Exception as e:
            logger.error(f"Error cleaning cache: {e}")
    
    def _sanitize_user_input(self, user_input: str) -> str:
        """
        Sanitize user input to prevent injection attacks.
        
        Args:
            user_input: Raw user input
            
        Returns:
            Sanitized user input
        """
        if not user_input:
            return ""
            
        # Remove potentially dangerous characters and patterns
        sanitized = re.sub(r'[^\w\s\.,\?\!]', ' ', user_input)
        
        # Normalize whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        # Limit input length
        max_length = int(self.config.get("MAX_INPUT_LENGTH", 1000))
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
            
        return sanitized
    
    def _filter_sensitive_output(self, output: str) -> str:
        """
        Filter sensitive information from output.
        
        Args:
            output: Raw output from model
            
        Returns:
            Filtered output
        """
        if not output:
            return ""
            
        # Filter patterns that might contain sensitive data
        patterns = [
            r'(?i)api[_\-\s]*key[_\-\s]*[:=]\s*[\w\d]{8,}',
            r'(?i)password[_\-\s]*[:=]\s*\S+',
            r'(?i)secret[_\-\s]*[:=]\s*\S+',
            r'(?i)token[_\-\s]*[:=]\s*\S+',
        ]
        
        filtered = output
        for pattern in patterns:
            filtered = re.sub(pattern, '[REDACTED]', filtered)
            
        return filtered
            
    def process_query(self, query: str, user_id: str, context: Dict = None) -> Dict:
        """
        Process a user query with RAG-enhanced responses.
        
        Args:
            query: User query
            user_id: User identifier
            context: Additional context (page, section, etc.)
            
        Returns:
            Response dictionary
        """
        # Set defaults
        context = context or {}
        tier = context.get("tier", "default")
        
        # Generate request ID for tracking
        request_id = str(uuid.uuid4())
        logger.info(f"Processing query {request_id} from user {user_id}")
        
        try:
            # Check rate limits
            if not self.check_rate_limit(user_id, tier):
                return {
                    "status": "error",
                    "error": "Rate limit exceeded. Please try again later.",
                    "request_id": request_id
                }
                
            # Sanitize user input
            sanitized_query = self._sanitize_user_input(query)
            if not sanitized_query:
                return {
                    "status": "error",
                    "error": "Invalid query. Please provide a valid question.",
                    "request_id": request_id
                }
                
            # Check cache
            cached_response = self.get_from_cache(sanitized_query, context)
            if cached_response:
                cached_response["cached"] = True
                cached_response["request_id"] = request_id
                return cached_response
                
            # Retrieve relevant context using vector store
            relevant_docs = self._retrieve_context(
                sanitized_query, 
                top_k=int(self.config.get("VECTOR_SIMILARITY_TOP_K", 5))
            )
            
            # Prepare prompt with retrieved context
            prompt = self._prepare_prompt(sanitized_query, relevant_docs, context)
            
            # Generate response using Fast Agent or fallback
            if FAST_AGENT_AVAILABLE:
                # Call Fast Agent implementation
                # response_text = fast_agent.generate(prompt, ...)
                # Using placeholder for now
                response_text = f"This is a simulated response to: {sanitized_query}"
            else:
                # Fallback response mechanism
                response_text = f"Fast Agent not available. Your query was: {sanitized_query}"
            
            # Filter sensitive information from response
            filtered_response = self._filter_sensitive_output(response_text)
            
            # Prepare final response
            response = {
                "status": "success",
                "query": sanitized_query,
                "response": filtered_response,
                "sources": [doc["metadata"].get("source", "") for doc in relevant_docs],
                "request_id": request_id,
                "cached": False
            }
            
            # Cache the response
            self.save_to_cache(sanitized_query, context, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing query {request_id}: {e}")
            return {
                "status": "error",
                "error": "An error occurred while processing your request.",
                "request_id": request_id
            }
    
    def _prepare_prompt(self, query: str, relevant_docs: List[Dict], context: Dict) -> str:
        """
        Prepare a prompt with retrieved context.
        
        Args:
            query: User query
            relevant_docs: Retrieved document chunks
            context: Additional context
            
        Returns:
            Formatted prompt string
        """
        # Build prompt with context from retrieved documents
        prompt_parts = [
            "You are an educational assistant specialized in art history.",
            "Use the following information to answer the question.",
            "\nRelevant information:"
        ]
        
        # Add retrieved content
        for i, doc in enumerate(relevant_docs):
            prompt_parts.append(f"\n[{i+1}] {doc['content']}")
            
        # Add page context if available
        if context.get("page"):
            prompt_parts.append(f"\nCurrent page: {context['page']}")
            
        # Add the query
        prompt_parts.append(f"\nQuestion: {query}")
        prompt_parts.append("\nAnswer:")
        
        return "\n".join(prompt_parts)
    
    def add_batch_task(self, task_type: str, **kwargs):
        """
        Add a task to the batch processing queue.
        
        Args:
            task_type: Type of task
            **kwargs: Task parameters
        """
        task = {"type": task_type, **kwargs}
        self.task_queue.put(task)
        logger.info(f"Added {task_type} task to batch queue")
        
    def generate_quiz(self, content_id: str, difficulty: str = "medium", 
                      question_count: int = 5) -> Dict:
        """
        Generate a quiz based on textbook content.
        
        Args:
            content_id: Content identifier (chapter, section)
            difficulty: Quiz difficulty (easy, medium, hard)
            question_count: Number of questions to generate
            
        Returns:
            Quiz data dictionary
        """
        # Validate and sanitize parameters
        difficulty = difficulty.lower()
        if difficulty not in ["easy", "medium", "hard"]:
            difficulty = "medium"
            
        question_count = min(max(1, question_count), 20)  # Limit between 1-20
        
        # Find content based on ID
        # This would need implementation specific to your content storage
        
        # Create a prompt for quiz generation
        prompt = f"""
        Generate a {difficulty} difficulty quiz with {question_count} questions about art history.
        The quiz should be related to {content_id}.
        Include multiple choice answers for each question with one correct answer.
        Format the response as a JSON array with questions, options, and correct answers.
        """
        
        # This would integrate with Fast Agent or other LLM
        # For now, return a placeholder
        quiz = {
            "questions": [
                {
                    "question": f"Sample question about {content_id}?",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "correct": 0
                }
            ] * question_count,
            "difficulty": difficulty,
            "content_id": content_id
        }
        
        return quiz
