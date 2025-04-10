"""
Vector store management for art education content.
This module provides utilities for indexing and retrieving content from the vector database.
"""
import logging
import os
from typing import List, Dict, Any, Optional, Tuple

import pinecone
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class ArtContentVectorStore:
    """
    Vector store for art education content using Pinecone.
    This class provides methods for indexing art textbook content and retrieving
    relevant information for educational purposes.
    """
    
    def __init__(self,
                 embedding_model_name: str = "all-MiniLM-L6-v2",
                 pinecone_api_key: Optional[str] = None,
                 pinecone_environment: str = "us-west1-gcp",
                 pinecone_index_name: str = "art-education-vectors"):
        """
        Initialize the vector store with the specified configuration.
        
        Args:
            embedding_model_name: Name of the Sentence Transformer model for embeddings
            pinecone_api_key: Pinecone API key (if None, will look for PINECONE_API_KEY env var)
            pinecone_environment: Pinecone environment
            pinecone_index_name: Name of the Pinecone index to use
        """
        # Load embedding model
        self.embedding_model = SentenceTransformer(embedding_model_name)
        self.embedding_dimension = self.embedding_model.get_sentence_embedding_dimension()
        
        # Initialize Pinecone
        self._init_pinecone(
            api_key=pinecone_api_key or os.environ.get("PINECONE_API_KEY"),
            environment=pinecone_environment,
            index_name=pinecone_index_name
        )
    
    def _init_pinecone(self, api_key: str, environment: str, index_name: str):
        """Initialize Pinecone and connect to the specified index."""
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
        self.index_name = index_name
        logger.info(f"Connected to Pinecone index: {index_name}")
    
    def index_textbook_content(self, 
                              content_chunks: List[str], 
                              metadata_list: List[Dict[str, Any]],
                              namespace: str = "textbook"):
        """
        Index textbook content chunks in the vector store.
        
        Args:
            content_chunks: List of text chunks to index
            metadata_list: List of metadata dictionaries for each chunk
            namespace: Namespace to use for the vectors
        """
        if len(content_chunks) != len(metadata_list):
            raise ValueError("Number of content chunks and metadata entries must match")
        
        # Generate embeddings for all chunks
        embeddings = self.embedding_model.encode(content_chunks)
        
        # Prepare vectors for Pinecone
        vectors = []
        for i, (chunk, meta) in enumerate(zip(content_chunks, metadata_list)):
            # Include chunk text in metadata for easier retrieval
            meta_with_text = {**meta, "text": chunk}
            vector_id = f"{namespace}-{meta.get('id', i)}"
            vectors.append((vector_id, embeddings[i].tolist(), meta_with_text))
        
        # Upsert vectors in batches
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i+batch_size]
            self.index.upsert(vectors=batch, namespace=namespace)
        
        logger.info(f"Indexed {len(content_chunks)} content chunks in namespace '{namespace}'")
    
    def semantic_search(self, 
                       query: str, 
                       namespace: str = "textbook",
                       top_k: int = 5,
                       filter_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Perform semantic search on the vector store.
        
        Args:
            query: Search query
            namespace: Namespace to search in
            top_k: Number of results to return
            filter_params: Optional filter parameters for the search
            
        Returns:
            List of search results with metadata
        """
        # Generate embedding for the query
        query_embedding = self.embedding_model.encode(query)
        
        # Perform search
        search_results = self.index.query(
            vector=query_embedding.tolist(),
            top_k=top_k,
            namespace=namespace,
            filter=filter_params,
            include_metadata=True
        )
        
        # Format results
        results = []
        for match in search_results['matches']:
            results.append({
                'id': match['id'],
                'score': match['score'],
                'text': match['metadata'].get('text', ''),
                'metadata': {k: v for k, v in match['metadata'].items() if k != 'text'}
            })
        
        return results
    
    def retrieve_context(self, 
                        query: str, 
                        namespaces: List[str] = ["textbook"],
                        results_per_namespace: int = 3) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve context from multiple namespaces.
        
        Args:
            query: Search query
            namespaces: List of namespaces to search in
            results_per_namespace: Number of results to fetch from each namespace
            
        Returns:
            Dictionary of namespace to list of results
        """
        context = {}
        
        for namespace in namespaces:
            results = self.semantic_search(
                query=query,
                namespace=namespace,
                top_k=results_per_namespace
            )
            context[namespace] = results
        
        return context
    
    def index_art_analysis(self,
                          artwork_id: str,
                          analysis_text: str,
                          metadata: Dict[str, Any],
                          namespace: str = "art_analysis"):
        """
        Index an art analysis in the vector store.
        
        Args:
            artwork_id: Unique identifier for the artwork
            analysis_text: Text of the analysis
            metadata: Metadata for the analysis
            namespace: Namespace to store the analysis in
        """
        # Generate embedding for the analysis
        embedding = self.embedding_model.encode(analysis_text)
        
        # Add text to metadata
        meta_with_text = {**metadata, "text": analysis_text, "artwork_id": artwork_id}
        
        # Store in Pinecone
        self.index.upsert(
            vectors=[(artwork_id, embedding.tolist(), meta_with_text)],
            namespace=namespace
        )
        
        logger.info(f"Indexed analysis for artwork {artwork_id} in namespace '{namespace}'")
    
    def similar_artworks(self, 
                        artwork_id: str, 
                        namespace: str = "artworks",
                        top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Find similar artworks based on a reference artwork.
        
        Args:
            artwork_id: ID of the reference artwork
            namespace: Namespace to search in
            top_k: Number of similar artworks to find
            
        Returns:
            List of similar artworks with metadata
        """
        # Retrieve the vector for the reference artwork
        vector_response = self.index.fetch(ids=[artwork_id], namespace=namespace)
        
        if artwork_id not in vector_response.get('vectors', {}):
            raise ValueError(f"Artwork with ID {artwork_id} not found in namespace {namespace}")
        
        # Get the embedding
        artwork_vector = vector_response['vectors'][artwork_id]['values']
        
        # Search for similar artworks
        search_results = self.index.query(
            vector=artwork_vector,
            top_k=top_k + 1,  # +1 because the query artwork will be included
            namespace=namespace,
            include_metadata=True
        )
        
        # Filter out the query artwork and format results
        results = []
        for match in search_results['matches']:
            if match['id'] != artwork_id:  # Exclude the query artwork
                results.append({
                    'id': match['id'],
                    'score': match['score'],
                    'metadata': match['metadata']
                })
        
        return results[:top_k]  # Ensure we return only top_k results
