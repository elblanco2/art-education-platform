# Art Education Platform

A platform for converting art textbooks to digital format with AI enhancements and Canvas LMS integration.

## Overview

This project aims to digitize art education materials and enhance them with AI capabilities, making them more accessible and interactive for students and educators. The platform integrates with Canvas LMS to provide a seamless educational experience.

## Features

- Digital conversion of art textbooks
- AI-enhanced content and interactions
- Canvas LMS integration
- Interactive learning experiences
- Customizable content for educators

## Project Structure

```
chatbook/
├── README.md          # Project documentation
├── requirements.txt   # Python dependencies
├── scripts/           # Setup and deployment scripts
├── src/               # Source code for the application
├── config/            # Configuration files
└── .gitignore         # Git ignore rules
```

## Getting Started

### Prerequisites

- Python 3.8+
- FastAPI
- Canvas LMS access
- Required Python packages (see requirements.txt)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/elblanco2/art-education-platform.git
   cd art-education-platform
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```
   cp config/.env.example config/.env
   # Edit config/.env with your own credentials
   ```

5. Run the application:
   ```
   python src/main.py
   ```

## Configuration

Create a `.env` file based on the `.env.example` template with the following variables:

- `CANVAS_API_URL` - Your Canvas LMS API URL
- `CANVAS_API_KEY` - Your Canvas LMS API key
- `DATABASE_URL` - Database connection string
- `AI_SERVICE_KEY` - API key for AI service (if applicable)

## Development

### Code Style

This project follows PEP 8 style guidelines for Python code.

### Testing

Run tests with:
```
pytest
```

## Deployment

Deployment instructions will be provided in the `/scripts/deploy.sh` file.

## Security Considerations

- Do not commit sensitive data: API keys, passwords, tokens, or private credentials
- Use environment variables for all sensitive data
- Check for secrets before committing code
- Validate all user inputs for security

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
