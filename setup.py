#!/usr/bin/env python3
"""
Setup script for Contract AI Copilot development environment
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors"""
    print(f">> {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"OK {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"FAIL {description} failed: {e.stderr}")
        return False


def check_requirements():
    """Check if required tools are installed"""
    print(">> Checking requirements...")
    
    requirements = {
        "python": "python --version",
        "node": "node --version", 
        "npm": "npm --version",
        "docker": "docker --version",
        "docker-compose": "docker-compose --version"
    }
    
    missing = []
    for tool, command in requirements.items():
        if not run_command(command, f"Checking {tool}"):
            missing.append(tool)
    
    if missing:
        print(f"FAIL Missing requirements: {', '.join(missing)}")
        print("Please install the missing tools before continuing.")
        return False
    
    print("OK All requirements satisfied")
    return True


def setup_backend():
    """Setup Python backend environment"""
    print(">> Setting up Python backend...")
    
    # Create virtual environment
    if not os.path.exists("venv"):
        if not run_command("python -m venv venv", "Creating virtual environment"):
            return False
    
    # Determine activation script based on OS
    if os.name == 'nt':  # Windows
        activate_script = "venv\\Scripts\\activate"
        pip_command = "venv\\Scripts\\pip"
    else:  # Unix/Linux/MacOS
        activate_script = "source venv/bin/activate"
        pip_command = "venv/bin/pip"
    
    # Install requirements
    if not run_command(f"{pip_command} install -r backend/requirements.txt", "Installing Python dependencies"):
        return False
    
    print("OK Backend setup completed")
    return True


def setup_frontend():
    """Setup Node.js frontend environment"""
    print(">> Setting up React frontend...")
    
    # Change to frontend directory
    original_dir = os.getcwd()
    os.chdir("frontend")
    
    try:
        # Install npm dependencies
        if not run_command("npm install", "Installing Node.js dependencies"):
            return False
        
        print("OK Frontend setup completed")
        return True
    finally:
        os.chdir(original_dir)


def setup_environment_file():
    """Create environment file from example"""
    print(">> Setting up environment configuration...")
    
    env_example = "env.example"
    env_file = ".env"
    
    if not os.path.exists(env_file):
        if os.path.exists(env_example):
            shutil.copy(env_example, env_file)
            print(f"OK Created {env_file} from {env_example}")
            print("WARN  Please edit .env file with your actual configuration values")
        else:
            print(f"FAIL {env_example} not found")
            return False
    else:
        print(f"OK {env_file} already exists")
    
    return True


def create_directories():
    """Create necessary directories"""
    print(">> Creating necessary directories...")
    
    directories = [
        "logs",
        "data/uploads",
        "data/sample_contracts",
        "data/test_data"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"OK Created directory: {directory}")
    
    return True


def main():
    """Main setup function"""
    print(">> Contract AI Copilot - Development Environment Setup")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists("backend") or not os.path.exists("frontend"):
        print("FAIL Please run this script from the project root directory")
        print("   Expected structure: contract-ai-copilot/")
        print("   With subdirectories: backend/, frontend/, data/, docs/")
        sys.exit(1)
    
    # Run setup steps
    steps = [
        ("Checking requirements", check_requirements),
        ("Creating directories", create_directories),
        ("Setting up environment file", setup_environment_file),
        ("Setting up backend", setup_backend),
        ("Setting up frontend", setup_frontend)
    ]
    
    for step_name, step_function in steps:
        print(f"\n>> {step_name}")
        print("-" * 40)
        if not step_function():
            print(f"\nFAIL Setup failed at: {step_name}")
            sys.exit(1)
    
    print("\n>> Setup completed successfully!")
    print("\n>> Next steps:")
    print("1. Edit .env file with your configuration")
    print("2. Start the development environment:")
    print("   docker-compose -f docker-compose.dev.yml up -d")
    print("3. Or start individual services:")
    print("   Backend: cd backend && python -m uvicorn app.main:app --reload")
    print("   Frontend: cd frontend && npm start")
    print("\n>> Documentation:")
    print("- README.md - Project overview")
    print("- DEVELOPMENT_PLAN.md - Detailed development plan")
    print("- docs/ - Additional documentation")


if __name__ == "__main__":
    main()
