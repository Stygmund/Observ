#!/bin/bash
# Installation script for Deployment Paradigm

set -e

echo "=== Installing Deployment Paradigm ==="

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.10"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)"; then
    echo "❌ Python 3.10+ required (found $PYTHON_VERSION)"
    exit 1
fi

echo "✓ Python $PYTHON_VERSION"

# Create installation directory
INSTALL_DIR="/opt/deployment-paradigm"
echo "Creating installation directory: $INSTALL_DIR"
sudo mkdir -p "$INSTALL_DIR"

# Clone or copy files
if [ -d ".git" ]; then
    # Running from git repo
    echo "Copying files from current directory..."
    sudo cp deploy_paradigm.py "$INSTALL_DIR/"
    sudo cp -r templates "$INSTALL_DIR/"
else
    # Download from GitHub (future)
    echo "Downloading latest version..."
    REPO_URL="https://github.com/you/deployment-paradigm"
    sudo git clone "$REPO_URL" "$INSTALL_DIR"
fi

# Install dependencies
echo "Installing Python dependencies..."
sudo pip3 install click pyyaml requests

# Create symlink
echo "Creating symlink: /usr/local/bin/deploy-paradigm"
sudo ln -sf "$INSTALL_DIR/deploy_paradigm.py" /usr/local/bin/deploy-paradigm
sudo chmod +x /usr/local/bin/deploy-paradigm

# Create directories
echo "Creating deployment directories..."
sudo mkdir -p /var/repos
sudo mkdir -p /opt/deployments
sudo mkdir -p /var/log/deployments

# Set permissions
sudo chown -R $USER:$USER /opt/deployments
sudo chown -R $USER:$USER /var/repos
sudo chown -R $USER:$USER /var/log/deployments

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Next steps:"
echo "1. Setup an application:"
echo "   deploy-paradigm setup <app-name> <git-url>"
echo ""
echo "2. Or check help:"
echo "   deploy-paradigm --help"
