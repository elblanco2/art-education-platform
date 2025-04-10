"""
Art content enhancement service using local LLM.
This module provides services for enhancing art education content with AI capabilities.
"""
import logging
from typing import Dict, List, Any, Optional, Tuple

from .local_llm import LocalLLM
from .vector_store import ArtContentVectorStore

logger = logging.getLogger(__name__)

class ContentEnhancer:
    """
    Service for enhancing art education content using local LLM capabilities.
    This replaces OpenAI API usage with a local, cost-free implementation.
    """
    
    def __init__(self, 
                 llm: Optional[LocalLLM] = None,
                 vector_store: Optional[ArtContentVectorStore] = None):
        """
        Initialize the content enhancer service.
        
        Args:
            llm: Optional pre-configured LocalLLM instance
            vector_store: Optional pre-configured ArtContentVectorStore instance
        """
        self.llm = llm or LocalLLM()
        self.vector_store = vector_store or ArtContentVectorStore()
    
    def enhance_paragraph(self, 
                         paragraph: str, 
                         enhancement_type: str = "explanation",
                         context: Optional[Dict[str, Any]] = None) -> str:
        """
        Enhance a paragraph with additional content based on the specified type.
        
        Args:
            paragraph: The original paragraph text
            enhancement_type: Type of enhancement ("explanation", "historical_context", 
                              "analysis", "question")
            context: Optional additional context
            
        Returns:
            Enhanced content
        """
        prompts = {
            "explanation": f"""The following is a paragraph from an art textbook. 
Please provide a clear, accessible explanation that would help students understand the concepts:

Paragraph: "{paragraph}"

Explanation:""",
            
            "historical_context": f"""The following is a paragraph from an art textbook.
Please provide relevant historical context that would enrich the student's understanding:

Paragraph: "{paragraph}"

Historical Context:""",
            
            "analysis": f"""The following is a paragraph from an art textbook.
Please provide a brief analysis that highlights key points or techniques mentioned:

Paragraph: "{paragraph}"

Analysis:""",
            
            "question": f"""The following is a paragraph from an art textbook.
Please generate 2-3 thought-provoking discussion questions about this content:

Paragraph: "{paragraph}"

Discussion Questions:"""
        }
        
        if enhancement_type not in prompts:
            raise ValueError(f"Enhancement type '{enhancement_type}' not supported")
        
        prompt = prompts[enhancement_type]
        
        # If we have context, we should first do a semantic search to find relevant information
        if context:
            artwork_info = context.get("artwork", {})
            artist_info = context.get("artist", {})
            period_info = context.get("period", {})
            
            # Add context to the prompt
            additional_context = ""
            if artwork_info:
                additional_context += f"\nArtwork: {artwork_info.get('title', '')}"
                additional_context += f"\nYear: {artwork_info.get('year', '')}"
                additional_context += f"\nMedium: {artwork_info.get('medium', '')}"
            
            if artist_info:
                additional_context += f"\nArtist: {artist_info.get('name', '')}"
                additional_context += f"\nLifespan: {artist_info.get('lifespan', '')}"
            
            if period_info:
                additional_context += f"\nArt Period: {period_info.get('name', '')}"
                additional_context += f"\nCharacteristics: {period_info.get('characteristics', '')}"
            
            if additional_context:
                prompt = prompt.replace("Paragraph:", f"Additional Context:{additional_context}\n\nParagraph:")
        
        # Generate the enhancement
        enhanced_content = self.llm.generate_text(
            prompt=prompt,
            max_length=512,
            temperature=0.7
        )[0]
        
        return enhanced_content
    
    def generate_explanations(self, text: str, difficulty_level: str = "intermediate") -> Dict[str, str]:
        """
        Generate various explanations for art terms and concepts in the given text.
        
        Args:
            text: The art education text
            difficulty_level: Target difficulty level ("beginner", "intermediate", "advanced")
            
        Returns:
            Dictionary of terms to explanations
        """
        # First, extract key terms that need explanation
        extract_prompt = f"""The following is a text from an art education book.
Please identify 3-5 key terms or concepts that would benefit from further explanation
for a {difficulty_level} level student:

Text: "{text}"

Key Terms (comma-separated):"""
        
        terms_text = self.llm.generate_text(
            prompt=extract_prompt,
            max_length=100,
            temperature=0.3
        )[0]
        
        # Parse the comma-separated terms
        terms = [term.strip() for term in terms_text.split(',') if term.strip()]
        
        # Generate explanations for each term
        explanations = {}
        for term in terms:
            explain_prompt = f"""Please provide a clear, concise explanation of the art term or concept '{term}' 
suitable for a {difficulty_level} level art student. Explanation should be 2-3 sentences:"""
            
            explanation = self.llm.generate_text(
                prompt=explain_prompt,
                max_length=200,
                temperature=0.7
            )[0]
            
            explanations[term] = explanation
        
        return explanations
    
    def create_quiz_questions(self, 
                            content: str, 
                            num_questions: int = 3,
                            question_types: List[str] = ["multiple_choice", "true_false", "short_answer"]) -> List[Dict[str, Any]]:
        """
        Create quiz questions based on the provided content.
        
        Args:
            content: Educational content to generate questions for
            num_questions: Number of questions to generate
            question_types: Types of questions to generate
            
        Returns:
            List of question dictionaries
        """
        all_questions = []
        
        for _ in range(num_questions):
            # Randomly select a question type
            import random
            q_type = random.choice(question_types)
            
            if q_type == "multiple_choice":
                prompt = f"""Based on the following art education content, generate a multiple-choice question
with 4 options and indicate the correct answer:

Content: "{content}"

Question:
A)
B)
C)
D)
Correct Answer:"""
            
            elif q_type == "true_false":
                prompt = f"""Based on the following art education content, generate a true/false question
and indicate whether the statement is true or false:

Content: "{content}"

Statement:
Answer (True or False):"""
            
            else:  # short_answer
                prompt = f"""Based on the following art education content, generate a short-answer question:

Content: "{content}"

Question:
Sample Answer:"""
            
            # Generate the question
            question_text = self.llm.generate_text(
                prompt=prompt,
                max_length=300,
                temperature=0.7
            )[0]
            
            # Parse the generated question based on type
            question = {"type": q_type}
            
            if q_type == "multiple_choice":
                lines = [line.strip() for line in question_text.split('\n') if line.strip()]
                question["question"] = lines[0].replace("Question:", "").strip()
                options = []
                for i in range(1, 5):
                    if i < len(lines) and lines[i].startswith(("A)", "B)", "C)", "D)")):
                        options.append(lines[i][2:].strip())
                question["options"] = options
                
                # Get correct answer
                correct_line = next((line for line in lines if line.startswith("Correct Answer:")), "")
                correct = correct_line.replace("Correct Answer:", "").strip()
                # Convert A/B/C/D to index
                answer_map = {"A": 0, "B": 1, "C": 2, "D": 3}
                question["correct_answer"] = answer_map.get(correct, 0)
            
            elif q_type == "true_false":
                lines = [line.strip() for line in question_text.split('\n') if line.strip()]
                question["question"] = lines[0].replace("Statement:", "").strip()
                
                # Get correct answer
                answer_line = next((line for line in lines if line.startswith("Answer")), "")
                answer_text = answer_line.replace("Answer (True or False):", "").strip()
                question["correct_answer"] = answer_text.lower() == "true"
            
            else:  # short_answer
                lines = [line.strip() for line in question_text.split('\n') if line.strip()]
                question["question"] = lines[0].replace("Question:", "").strip()
                
                # Get sample answer
                answer_line = next((line for line in lines if line.startswith("Sample Answer:")), "")
                question["sample_answer"] = answer_line.replace("Sample Answer:", "").strip()
            
            all_questions.append(question)
        
        return all_questions
    
    def analyze_artwork(self, 
                      artwork_info: Dict[str, Any],
                      analysis_depth: str = "standard") -> Dict[str, str]:
        """
        Generate an analysis for an artwork.
        
        Args:
            artwork_info: Dictionary with artwork information
            analysis_depth: Depth of analysis ("brief", "standard", "detailed")
            
        Returns:
            Dictionary with different sections of analysis
        """
        # Extract artwork information
        title = artwork_info.get("title", "Untitled")
        artist = artwork_info.get("artist", "Unknown")
        year = artwork_info.get("year", "Unknown")
        medium = artwork_info.get("medium", "Unknown")
        dimensions = artwork_info.get("dimensions", "Unknown dimensions")
        location = artwork_info.get("location", "Unknown location")
        description = artwork_info.get("description", "")
        
        # Search for additional context in the vector store
        context_results = []
        if artist:
            # Search for information about the artist
            artist_results = self.vector_store.semantic_search(
                query=artist,
                namespace="artists",
                top_k=1
            )
            if artist_results:
                context_results.extend(artist_results)
        
        # Construct the base prompt
        artwork_info_text = f"""Title: {title}
Artist: {artist}
Year: {year}
Medium: {medium}
Dimensions: {dimensions}
Location: {location}
Description: {description}"""
        
        # Add any context information
        context_text = ""
        for result in context_results:
            context_text += f"\nContext Information: {result.get('text', '')}"
        
        # Define the analysis sections based on depth
        sections = ["formal_elements", "subject_matter", "historical_context"]
        
        if analysis_depth == "detailed":
            sections.extend(["symbolism", "interpretation", "significance", "techniques"])
        elif analysis_depth == "brief":
            sections = ["formal_elements", "subject_matter"]
        
        # Generate analysis for each section
        analysis = {}
        
        section_prompts = {
            "formal_elements": f"""Analyze the formal elements (line, color, composition, etc.) of the following artwork:

{artwork_info_text}
{context_text}

Formal Elements Analysis:""",
            
            "subject_matter": f"""Describe and analyze the subject matter of the following artwork:

{artwork_info_text}
{context_text}

Subject Matter Analysis:""",
            
            "historical_context": f"""Provide the historical context of the following artwork:

{artwork_info_text}
{context_text}

Historical Context:""",
            
            "symbolism": f"""Analyze the symbolism and iconography in the following artwork:

{artwork_info_text}
{context_text}

Symbolism Analysis:""",
            
            "interpretation": f"""Provide an interpretation of the meaning or message of the following artwork:

{artwork_info_text}
{context_text}

Interpretation:""",
            
            "significance": f"""Explain the significance and influence of the following artwork:

{artwork_info_text}
{context_text}

Significance:""",
            
            "techniques": f"""Analyze the techniques and methods used to create the following artwork:

{artwork_info_text}
{context_text}

Techniques Analysis:"""
        }
        
        for section in sections:
            if section in section_prompts:
                analysis[section] = self.llm.generate_text(
                    prompt=section_prompts[section],
                    max_length=300 if analysis_depth == "brief" else 500,
                    temperature=0.7
                )[0]
        
        return analysis
    
    def compare_artworks(self, 
                        artwork_ids: List[str],
                        comparison_aspects: List[str] = ["style", "technique", "theme", "influence"]) -> Dict[str, str]:
        """
        Generate a comparison analysis between multiple artworks.
        
        Args:
            artwork_ids: List of artwork IDs to compare
            comparison_aspects: Aspects to compare
            
        Returns:
            Dictionary with different sections of comparison
        """
        # Retrieve artwork information from the vector store
        artworks_info = []
        for artwork_id in artwork_ids:
            # Get artwork vector
            artwork_data = self.vector_store.index.fetch(
                ids=[artwork_id],
                namespace="artworks"
            )
            
            if artwork_id in artwork_data.get('vectors', {}):
                metadata = artwork_data['vectors'][artwork_id].get('metadata', {})
                artworks_info.append(metadata)
            else:
                logger.warning(f"Artwork with ID {artwork_id} not found in vector store")
        
        if len(artworks_info) < 2:
            raise ValueError("At least two valid artwork IDs are required for comparison")
        
        # Construct the comparison prompt
        artwork_descriptions = []
        for i, artwork in enumerate(artworks_info):
            description = f"""Artwork {i+1}:
Title: {artwork.get('title', 'Unknown')}
Artist: {artwork.get('artist', 'Unknown')}
Year: {artwork.get('year', 'Unknown')}
Medium: {artwork.get('medium', 'Unknown')}
Description: {artwork.get('description', '')}"""
            artwork_descriptions.append(description)
        
        artworks_text = "\n\n".join(artwork_descriptions)
        
        # Generate comparison for each aspect
        comparison = {}
        
        aspect_prompts = {
            "style": f"""Compare the artistic styles of the following artworks:

{artworks_text}

Style Comparison:""",
            
            "technique": f"""Compare the techniques used in the following artworks:

{artworks_text}

Technique Comparison:""",
            
            "theme": f"""Compare the themes and subject matter of the following artworks:

{artworks_text}

Theme Comparison:""",
            
            "influence": f"""Compare the historical influences and significance of the following artworks:

{artworks_text}

Influence Comparison:""",
            
            "composition": f"""Compare the composition and formal elements of the following artworks:

{artworks_text}

Composition Comparison:""",
            
            "context": f"""Compare the historical and cultural contexts of the following artworks:

{artworks_text}

Context Comparison:"""
        }
        
        for aspect in comparison_aspects:
            if aspect in aspect_prompts:
                comparison[aspect] = self.llm.generate_text(
                    prompt=aspect_prompts[aspect],
                    max_length=400,
                    temperature=0.7
                )[0]
        
        # Generate an overall comparison summary
        summary_prompt = f"""Provide a brief overall comparison summary of the following artworks:

{artworks_text}

Overall Comparison Summary:"""
        
        comparison["summary"] = self.llm.generate_text(
            prompt=summary_prompt,
            max_length=300,
            temperature=0.7
        )[0]
        
        return comparison
