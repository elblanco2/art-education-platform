"""
Local LLM implementation using Hugging Face models and Pinecone for vector storage.
This module provides a cost-free alternative to OpenAI's API for educational purposes.
"""
import os
import logging
from typing import List, Dict, Any, Optional, Union

import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from sentence_transformers import SentenceTransformer
import pinecone

logger = logging.getLogger(__name__)

class LocalLLM:
    """
    A local LLM implementation that uses Hugging Face models and Pinecone for vector storage.
    This allows for text generation and semantic search without external API costs.
    """
    
    def __init__(self, 
                 embedding_model_name: str = "all-MiniLM-L6-v2",
                 generation_model_name: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
                 pinecone_api_key: Optional[str] = None,
                 pinecone_environment: str = "us-west1-gcp",
                 pinecone_index_name: str = "art-education-vectors",
                 device: str = None):
        """
        Initialize the local LLM with specified models and Pinecone configuration.
        
        Args:
            embedding_model_name: Name of the Sentence Transformer model for embeddings
            generation_model_name: Name of the Hugging Face model for text generation
            pinecone_api_key: Pinecone API key (if None, will look for PINECONE_API_KEY env var)
            pinecone_environment: Pinecone environment
            pinecone_index_name: Name of the Pinecone index to use
            device: Device to run models on ('cuda', 'cpu', or None for auto-detection)
        """
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {self.device}")
        
        # Load embedding model
        logger.info(f"Loading embedding model: {embedding_model_name}")
        self.embedding_model = SentenceTransformer(embedding_model_name, device=self.device)
        self.embedding_dimension = self.embedding_model.get_sentence_embedding_dimension()
        
        # Load generation model
        logger.info(f"Loading generation model: {generation_model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(generation_model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            generation_model_name,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            low_cpu_mem_usage=True
        )
        self.model.to(self.device)
        
        # Set up text generation pipeline
        self.generator = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            device=0 if self.device == "cuda" else -1
        )
        
        # Initialize Pinecone for vector storage
        self._setup_pinecone(
            api_key=pinecone_api_key or os.environ.get("PINECONE_API_KEY"),
            environment=pinecone_environment,
            index_name=pinecone_index_name
        )
    
    def _setup_pinecone(self, api_key: str, environment: str, index_name: str):
        """Initialize Pinecone and create index if it doesn't exist."""
        if not api_key:
            raise ValueError("Pinecone API key not provided and PINECONE_API_KEY env var not set")
        
        # Initialize Pinecone
        pinecone.init(api_key=api_key, environment=environment)
        
        # Check if index exists, create it if it doesn't
        if index_name not in pinecone.list_indexes():
            logger.info(f"Creating Pinecone index: {index_name}")
            pinecone.create_index(
                name=index_name,
                dimension=self.embedding_dimension,
                metric="cosine"
            )
        
        # Connect to the index
        self.index = pinecone.Index(index_name)
        logger.info(f"Connected to Pinecone index: {index_name}")
    
    def generate_text(self, 
                     prompt: str, 
                     max_length: int = 512, 
                     temperature: float = 0.7,
                     num_return_sequences: int = 1) -> List[str]:
        """
        Generate text based on a prompt using the local model.
        
        Args:
            prompt: Input text prompt
            max_length: Maximum length of generated text
            temperature: Temperature for text generation (higher = more creative)
            num_return_sequences: Number of different sequences to generate
            
        Returns:
            List of generated text sequences
        """
        logger.info(f"Generating text with prompt: {prompt[:50]}...")
        
        outputs = self.generator(
            prompt,
            max_length=max_length,
            temperature=temperature,
            num_return_sequences=num_return_sequences,
            pad_token_id=self.tokenizer.eos_token_id
        )
        
        # Extract generated text from outputs
        generated_texts = [output['generated_text'] for output in outputs]
        
        # Remove the original prompt from the generated text
        results = [text[len(prompt):].strip() for text in generated_texts]
        
        return results
    
    def get_embeddings(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        Generate embeddings for one or more texts.
        
        Args:
            texts: Single text string or list of text strings
            
        Returns:
            Array of embeddings
        """
        if isinstance(texts, str):
            texts = [texts]
        
        embeddings = self.embedding_model.encode(texts)
        return embeddings
    
    def store_documents(self, texts: List[str], metadata: List[Dict[str, Any]] = None):
        """
        Store documents in Pinecone with their embeddings.
        
        Args:
            texts: List of document texts
            metadata: Optional list of metadata dicts for each document
        """
        if metadata is None:
            metadata = [{} for _ in texts]
        
        if len(texts) != len(metadata):
            raise ValueError("Number of texts and metadata entries must match")
        
        # Generate embeddings for all texts
        embeddings = self.get_embeddings(texts)
        
        # Prepare vectors for Pinecone
        vectors = []
        for i, (text, meta) in enumerate(zip(texts, metadata)):
            # Add the text to metadata for retrieval
            meta_with_text = {**meta, "text": text}
            vectors.append((str(i), embeddings[i].tolist(), meta_with_text))
        
        # Upsert to Pinecone in batches of 100
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i+batch_size]
            self.index.upsert(vectors=batch)
        
        logger.info(f"Stored {len(texts)} documents in Pinecone")
    
    def semantic_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Perform semantic search using Pinecone.
        
        Args:
            query: The search query
            top_k: Number of results to return
            
        Returns:
            List of search results with scores and metadata
        """
        # Generate embedding for the query
        query_embedding = self.get_embeddings(query)
        
        # Search Pinecone
        results = self.index.query(
            vector=query_embedding.tolist(),
            top_k=top_k,
            include_metadata=True
        )
        
        # Format results
        formatted_results = []
        for match in results['matches']:
            formatted_results.append({
                'score': match['score'],
                'text': match['metadata'].get('text', ''),
                'metadata': {k: v for k, v in match['metadata'].items() if k != 'text'}
            })
        
        return formatted_results
    
    def generate_with_context(self, 
                             query: str, 
                             max_length: int = 512,
                             temperature: float = 0.7,
                             context_results: int = 3) -> str:
        """
        Generate text with context from the knowledge base.
        
        Args:
            query: User query
            max_length: Maximum length of generated text
            temperature: Temperature for text generation
            context_results: Number of context documents to retrieve
            
        Returns:
            Generated text
        """
        # Get relevant context from Pinecone
        context_docs = self.semantic_search(query, top_k=context_results)
        
        # Create a prompt with the context
        context_text = "\n\n".join([doc['text'] for doc in context_docs])
        prompt = f"""Context information:
{context_text}

Based on the above context, please answer the following question:
{query}

Answer:"""
        
        # Generate response
        response = self.generate_text(
            prompt=prompt,
            max_length=max_length,
            temperature=temperature
        )[0]
        
        return response
