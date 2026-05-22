#!/bin/bash

# Set UTF-8 encoding
export LANG=en_US.UTF-8

echo "========================================"
echo "  Auto Install Script (macOS & Linux)"
echo "========================================"
echo

# ============================================
# Project Configuration (modify according to your project)
# ============================================
PROJECT_NAME="NeonRace"
GITHUB_USER="PizzaDark"
GITHUB_REPO="$PROJECT_NAME"
REPO_URL="https://github.com/$GITHUB_USER/$GITHUB_REPO.git"
REPO_ZIP_URL="https://github.com/$GITHUB_USER/$GITHUB_REPO/archive/refs/heads/main.zip"
REPO_DIR="$PROJECT_NAME"

# ============================================
# Step 1: Check Python 3.10+ Environment
# ============================================
echo "[1/5] Checking Python environment..."

if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "[Error] Python environment not detected!"
    echo
    echo "Please download and install Python 3.10 or higher: https://www.python.org/downloads/"
    echo
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
PYTHON_MAJOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info[0])')
PYTHON_MINOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info[1])')

echo "Detected Python version: $PYTHON_VERSION"

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]; }; then
    echo "[Error] Python version is too low! Current version: $PYTHON_VERSION, requires 3.10 or higher"
    echo "Please download version 3.10 or above: https://www.python.org/downloads/"
    exit 1
fi

echo "[✓] Python version acceptable (requires 3.10+)"
echo

# ============================================
# Step 2: Check Git Environment
# ============================================
echo "[2/5] Checking Git environment..."
if ! command -v git &>/dev/null; then
    echo "[Hint] Git environment not detected"
    echo
    echo "Attempting to download project archive..."
    if command -v curl &>/dev/null && command -v unzip &>/dev/null; then
        curl -L -o project.zip "$REPO_ZIP_URL"
        if [ $? -ne 0 ]; then
            echo "[Error] Download failed!"
            exit 1
        fi
        unzip -q project.zip
        
        if [ -d "${PROJECT_NAME}-main" ]; then
            mv "${PROJECT_NAME}-main" "$PROJECT_NAME"
        elif [ -d "${PROJECT_NAME}-master" ]; then
            mv "${PROJECT_NAME}-master" "$PROJECT_NAME"
        fi
        
        rm project.zip
        cd "$PROJECT_NAME" || exit 1
    else
        echo "[Error] curl or unzip not detected, please install Git, curl, and unzip, or download manually: ${REPO_ZIP_URL}"
        exit 1
    fi
else
    echo "[✓] Git environment looks good"
    echo
    
    CURRENT_DIR=$(basename "$PWD")
    if [ "$CURRENT_DIR" == "$PROJECT_NAME" ] || [ -d ".git" ] || [ -f "main.py" ]; then
        echo "[Hint] Currently in project directory, skipping clone step"
    else
        echo "Cloning repository..."
        git clone "$REPO_URL"
        if [ $? -ne 0 ]; then
            echo "[Error] Clone failed! Attempting to download ZIP archive using curl..."
            if command -v curl &>/dev/null && command -v unzip &>/dev/null; then
                curl -L -o project.zip "$REPO_ZIP_URL"
                unzip -q project.zip
                if [ -d "${PROJECT_NAME}-main" ]; then
                    mv "${PROJECT_NAME}-main" "$PROJECT_NAME"
                fi
                rm project.zip
            else
                echo "[Error] Clone failed and curl/unzip not found. Please download manually."
                exit 1
            fi
        fi
        cd "$PROJECT_NAME" || exit 1
    fi
fi
echo

# ============================================
# Step 3: Create Virtual Environment
# ============================================
echo "[3/5] Checking/Creating virtual environment..."
if [ -d ".venv" ]; then
    echo "[Hint] Existing virtual environment detected"
else
    echo "Creating virtual environment..."
    $PYTHON_CMD -m venv .venv
    if [ $? -ne 0 ]; then
        echo "[Error] Failed to create virtual environment! Probably missing python3-venv module."
        echo "On Ubuntu/Debian, you can install it with: sudo apt install python3-venv"
        exit 1
    fi
    echo "[✓] Virtual environment created successfully"
fi
echo

# ============================================
# Step 4: Activate Virtual Environment
# ============================================
echo "[4/5] Activating virtual environment..."
source .venv/bin/activate
if [ $? -ne 0 ]; then
    echo "[Error] Failed to activate virtual environment!"
    exit 1
fi
echo "[✓] Virtual environment activated"
echo

# ============================================
# Step 5: Install Dependencies
# ============================================
echo "[5/5] Installing/Updating dependencies..."
if [ ! -f "requirements.txt" ]; then
    echo "[Warning] requirements.txt not found!"
    echo "Will attempt to run the program directly..."
    echo
else
    echo "Installing dependencies using Aliyun mirror, please wait..."
    pip install pip -i https://mirrors.aliyun.com/pypi/simple/ >/dev/null 2>&1
    pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
    if [ $? -ne 0 ]; then
        echo "[Error] Failed to install dependencies!"
        echo
        echo "You can try running manually:"
        echo "pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/"
        echo
        exit 1
    fi
    echo "[✓] Dependencies installed successfully"
    echo
fi

# ============================================
# Run main program
# ============================================
echo "========================================"
echo "  Environment ready, launching program..."
echo "========================================"
echo

if [ ! -f "main.py" ]; then
    echo "[Error] main.py not found!"
    echo
    echo "Ensure you are running this script in the correct project directory."
    echo
    exit 1
fi

python main.py

# Post-execution process
echo
echo "========================================"
echo "  Program exited"
echo "========================================"
