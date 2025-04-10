#!/bin/bash
# Production Deployment Script for Art Education Platform
# This script handles secure deployment to production environments
# It employs security best practices like input validation and least privilege

set -e  # Exit on any error

# Configuration
APP_NAME="art-education-platform"
LOG_FILE="deployment.log"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_DIR="backups/$TIMESTAMP"

# Load environment variables
if [ -f "./config/.env" ]; then
    echo "Loading environment variables from .env file"
    export $(grep -v '^#' ./config/.env | xargs)
else
    echo "ERROR: .env file not found in config directory"
    echo "Please create one from the .env.example template"
    exit 1
fi

# Function to validate required environment variables
validate_env_vars() {
    local required_vars=("SECRET_KEY" "SITE_URL" "UPLOAD_DIR" "TEMPLATES_DIR" 
                         "STATIC_DIR" "DATA_DIR" "INSTANCES_DIR" "DEPLOYMENTS_DIR")
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        echo "ERROR: Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        echo "Please update your .env file with these variables"
        exit 1
    fi
}

# Function to create backup
create_backup() {
    echo "Creating backup in $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
    
    # Backup critical files and directories
    if [ -d "instance" ]; then
        cp -r instance "$BACKUP_DIR"
    fi
    
    if [ -d "$DATA_DIR" ]; then
        cp -r "$DATA_DIR" "$BACKUP_DIR"
    fi
    
    if [ -d "$INSTANCES_DIR" ]; then
        cp -r "$INSTANCES_DIR" "$BACKUP_DIR"
    fi
    
    echo "Backup created successfully"
}

# Function to update dependencies
update_dependencies() {
    echo "Updating dependencies"
    
    # Check if we're in a virtual environment
    if [ -z "$VIRTUAL_ENV" ]; then
        echo "WARNING: Not running in a virtual environment"
        read -p "Do you want to continue? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # Update pip itself
    pip install --upgrade pip
    
    # Install/upgrade dependencies
    pip install -r requirements.txt
    
    echo "Dependencies updated successfully"
}

# Function to check for security vulnerabilities
check_security() {
    echo "Checking for security vulnerabilities"
    
    # Check Python dependencies
    if command -v safety &> /dev/null; then
        echo "Running safety check on dependencies"
        safety check -r requirements.txt
    else
        echo "Installing safety for dependency checking"
        pip install safety
        safety check -r requirements.txt
    fi
    
    # Run static analysis
    if command -v bandit &> /dev/null; then
        echo "Running Bandit for static security analysis"
        bandit -r ./src -f txt -o security_report.txt
    else
        echo "Installing Bandit for static security analysis"
        pip install bandit
        bandit -r ./src -f txt -o security_report.txt
    fi
    
    echo "Security checks completed"
}

# Function to build frontend assets
build_frontend() {
    echo "Building frontend assets"
    
    if [ -f "package.json" ]; then
        npm ci  # Use clean install for production
        npm run build
    else
        echo "No package.json found, skipping frontend build"
    fi
    
    echo "Frontend build completed"
}

# Function to set up database
setup_database() {
    echo "Setting up database"
    
    # Run database migrations or setup script
    python -m src.db.setup
    
    echo "Database setup completed"
}

# Function to optimize for production
optimize_for_production() {
    echo "Optimizing for production"
    
    # Compile Python files for better performance
    python -m compileall src
    
    # Set proper permissions
    find ./src -type f -name "*.py" -exec chmod 644 {} \;
    find ./scripts -type f -name "*.sh" -exec chmod 755 {} \;
    
    echo "Optimization completed"
}

# Function to deploy the application
deploy() {
    echo "Deploying application to production"
    
    # Create necessary directories
    for dir in "$UPLOAD_DIR" "$TEMPLATES_DIR" "$STATIC_DIR" "$DATA_DIR" \
               "$INSTANCES_DIR" "$DEPLOYMENTS_DIR"; do
        mkdir -p "$dir"
        echo "Created directory: $dir"
    done
    
    # Deploy application
    if [ -n "$WSGI_PATH" ]; then
        echo "Configuring WSGI..."
        cp wsgi.py "$WSGI_PATH"
        
        # Restart web server based on what's configured
        if [ -n "$WEB_SERVER" ]; then
            case "$WEB_SERVER" in
                "apache")
                    echo "Restarting Apache..."
                    sudo systemctl restart apache2
                    ;;
                "nginx")
                    echo "Restarting Nginx..."
                    sudo systemctl restart nginx
                    ;;
                *)
                    echo "Unknown web server: $WEB_SERVER"
                    echo "Please restart your web server manually"
                    ;;
            esac
        fi
    fi
    
    echo "Deployment completed successfully"
}

# Function to run post-deployment checks
post_deployment_check() {
    echo "Running post-deployment checks"
    
    # Wait for server to start
    sleep 5
    
    # Check if API is responding
    if [ -n "$SITE_URL" ]; then
        if command -v curl &> /dev/null; then
            echo "Checking API health at $SITE_URL/api/health"
            curl -s -o /dev/null -w "%{http_code}" "$SITE_URL/api/health" | grep 200
            if [ $? -eq 0 ]; then
                echo "API is healthy"
            else
                echo "WARNING: API is not responding correctly"
            fi
        else
            echo "curl not found, skipping API health check"
        fi
    fi
    
    echo "Post-deployment checks completed"
}

# Main execution
main() {
    echo "Starting deployment process for $APP_NAME at $TIMESTAMP"
    echo "Logging deployment to $LOG_FILE"
    
    # Validate environment
    validate_env_vars
    
    # Perform deployment steps
    create_backup
    update_dependencies
    check_security
    build_frontend
    setup_database
    optimize_for_production
    deploy
    post_deployment_check
    
    echo "Deployment process completed successfully"
}

# Execute main function and log output
main | tee -a "$LOG_FILE"
