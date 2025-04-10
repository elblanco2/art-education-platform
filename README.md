# Art Education Platform with mdBook and AI Integration

## Project Overview
This platform provides an immersive educational experience by combining:
- Art textbook content converted to mdBook format
- AI assistance through both Fast Agent and Local LLM implementation
- Seamless Canvas LMS integration
- Franchise model for instructor adoption
- No external API costs through local model deployment

## Security Features
- Secure authentication through Canvas LMS integration
- Data encryption for sensitive information
- GDPR and FERPA compliant data handling
- Secure vector storage for retrieval-augmented generation
- Input validation and sanitization for all user inputs
- Rate limiting to prevent abuse and DDoS attacks
- Secure credential storage for deployment integrations
- JWT-based authentication for API endpoints
- HTTPS enforcement for all connections
- Least privilege principle applied throughout the codebase

## Directory Structure
- `src/` - Source code for the application components
  - `ocr/` - OCR processing for textbook conversion
  - `mdbook/` - mdBook configuration and customization
  - `ai/` - Local LLM implementation and content enhancer
  - `fastAgentIntegration/` - AI assistant integration
  - `canvasIntegration/` - Canvas LMS connectivity
  - `franchise/` - Franchise template system
  - `deployment/` - Deployment tools and integrations
  - `api/` - API endpoints and routing
  - `models/` - Data models
  - `services/` - Business logic and services
- `docs/` - Documentation for various user roles
- `tools/` - Utility scripts for conversion and management
- `config/` - Configuration files
- `scripts/` - Installation and deployment scripts
- `assets/` - Static assets like images, stylesheets, etc.

## Local LLM Implementation

This project uses a local Large Language Model (LLM) implementation instead of OpenAI API, eliminating API costs for students and faculty. Key features include:

- **Hugging Face Models**: Utilizes open-source models from Hugging Face
- **Pinecone Vector Database**: Stores and retrieves art-related content efficiently
- **Sentence Transformers**: Generates embeddings for semantic search
- **No API Costs**: All AI features run locally with no usage fees

### AI Components:

- `LocalLLM`: Core implementation of text generation capabilities
- `ArtContentVectorStore`: Vector database management for art education content
- `ContentEnhancer`: Services for enhancing textbook content with AI

## Getting Started

### Prerequisites
- Python 3.8 or higher
- Node.js 16+ (for frontend components)
- Tesseract OCR for image processing
- Git for version control
- CUDA-capable GPU (recommended for optimal performance)
- Canvas LMS access
- Required Python packages (see requirements.txt)

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/elblanco2/art-education-platform.git
   cd art-education-platform
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment:
   ```bash
   cp config/.env.example config/.env
   ```
   Edit the `.env` file with your specific configurations.

5. Download LLM models (one-time setup):
   ```bash
   python scripts/download_models.py
   ```

6. Run setup script:
   ```bash
   ./scripts/setup.sh
   ```

7. Start development server:
   ```bash
   ./scripts/dev.sh
   ```

## Configuration

Create a `.env` file based on the `.env.example` template with the following variables:

- `CANVAS_API_URL` - Your Canvas LMS API URL
- `CANVAS_API_KEY` - Your Canvas LMS API key
- `DATABASE_URL` - Database connection string
- `LLM_EMBEDDING_MODEL` - Sentence transformer model name
- `LLM_GENERATION_MODEL` - Text generation model name
- `PINECONE_API_KEY` - Pinecone API key for vector storage
- `PINECONE_ENVIRONMENT` - Pinecone environment
- `PINECONE_INDEX_NAME` - Pinecone index name
- `SITE_URL` - URL for the deployed application
- `SECURE_KEY` - Secret key for JWT token generation

## Deployment Options

### 1. Hosted Deployment (lucasblanco.com)
The platform is primarily hosted at `lucasblanco.com/ed/arh1000/fulltext`. To deploy your instance:

1. Create a franchise template from your textbook content
2. Configure your deployment settings in the admin dashboard
3. Submit for deployment review
4. Once approved, your instance will be available at your specified subdomain

### 2. Canvas LMS Direct Integration
For seamless integration with your Canvas LMS:

1. Generate an LTI configuration using the Canvas Connector
2. Install the LTI app in your Canvas instance
3. Configure the integration settings
4. Your students will have SSO access through Canvas

### 3. Self-Hosted Deployment
For institutions that prefer to host the platform themselves:

1. Set up a server with Python 3.8+ and required dependencies
2. Clone the repository and install requirements
3. Configure the environment variables
4. Set up a web server (Nginx/Apache) with WSGI
5. Run the deployment script:
   ```bash
   ./scripts/deploy_production.sh
   ```

### 4. HostBridge MCP Integration
For conversational deployment through Claude and other AI assistants:

1. Install the HostBridge MCP server:
   ```bash
   python src/deployment/hostbridge_integration.py --install
   ```

2. Configure your hosting provider credentials
3. Use Claude or another compatible AI assistant to deploy your instance through conversation

## Development

### Code Style
This project follows PEP 8 style guidelines for Python code.

### Testing
Run tests with:
```bash
pytest
```

## API Documentation
The platform provides a comprehensive API for integrating with other systems:

- API documentation is available at `/api/docs` when running the server
- OpenAPI specification is available at `/api/openapi.json`
- Authentication uses JWT tokens obtained through `/api/auth/token`

## Franchise Model
The platform uses a franchise model to allow professors to create and maintain their own instances:

1. Create a template from your content
2. Customize the look and feel
3. Choose deployment options
4. Select subscription plan
5. Publish to your students

## Security Considerations
- Do not commit sensitive data: API keys, passwords, tokens, or private credentials
- Use environment variables for all sensitive data
- Check for secrets before committing code
- Validate all user inputs to prevent injection attacks
- Always use HTTPS for all connections

## Contributing
Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License
This project is licensed under the MIT License - see the LICENSE file for details.

Copyright 2025 Lucas Blanco
