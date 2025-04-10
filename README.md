# Art Education Platform with mdBook and Fast Agent

## Project Overview
This platform provides an immersive educational experience by combining:
- Art textbook content converted to mdBook format
- AI assistance through Fast Agent with optimization for educational contexts
- Seamless Canvas LMS integration
- Franchise model for instructor adoption

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
  - `fastAgentIntegration/` - AI assistant integration
  - `canvasIntegration/` - Canvas LMS connectivity
  - `franchise/` - Franchise template system
  - `deployment/` - Deployment tools and integrations
  - `api/` - API endpoints and routing
- `docs/` - Documentation for various user roles
- `tools/` - Utility scripts for conversion and management
- `config/` - Configuration files
- `scripts/` - Installation and deployment scripts
- `assets/` - Static assets like images, stylesheets, etc.

## Getting Started

### Prerequisites
- Python 3.8 or higher
- Node.js 16+ (for frontend components)
- Tesseract OCR for image processing
- Git for version control

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/art-education-platform.git
   cd art-education-platform
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment:
   ```bash
   cp config/.env.example config/.env
   ```
   Edit the `.env` file with your specific configurations.

4. Run setup script:
   ```bash
   ./scripts/setup.sh
   ```

5. Start development server:
   ```bash
   ./scripts/dev.sh
   ```

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

## Contributing
Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License
Copyright 2025 Lucas Blanco
