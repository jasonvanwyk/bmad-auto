#!/bin/bash
#
# provision_bmad_vm.sh - Provision BMad automation test VM
#
# Run this script inside the VM after Ubuntu installation to set up
# the complete BMad automation testing environment.
#
# Usage: bash provision_bmad_vm.sh
#

set -euo pipefail

# Configuration
BMAD_USER="bmad-test"
BMAD_PASSWORD="BmadTest123!"
PYTHON_VERSION="3.10"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging
LOG_FILE="/var/log/bmad_provision.log"
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   BMad Automation Test Environment Setup       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (sudo bash provision_bmad_vm.sh)${NC}"
    exit 1
fi

# Update hostname
echo -e "${GREEN}[1/12] Setting hostname...${NC}"
hostnamectl set-hostname bmad-automation-test
echo "127.0.1.1 bmad-automation-test" >> /etc/hosts

# System update
echo -e "${GREEN}[2/12] Updating system packages...${NC}"
apt update && apt upgrade -y

# Install essential packages
echo -e "${GREEN}[3/12] Installing essential packages...${NC}"
apt install -y \
    build-essential \
    git \
    curl \
    wget \
    vim \
    htop \
    tree \
    jq \
    zip \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release

# Install Python and pip
echo -e "${GREEN}[4/12] Installing Python ${PYTHON_VERSION}...${NC}"
apt install -y \
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-venv \
    python${PYTHON_VERSION}-dev \
    python3-pip

# Install Node.js and npm
echo -e "${GREEN}[5/12] Installing Node.js and npm...${NC}"
curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -
apt install -y nodejs

# Install tmux
echo -e "${GREEN}[6/12] Installing tmux and dependencies...${NC}"
apt install -y tmux screen

# Install useful CLI tools
echo -e "${GREEN}[7/12] Installing CLI tools...${NC}"
apt install -y \
    ripgrep \
    fd-find \
    bat \
    fzf \
    ncdu \
    iftop \
    nethogs

# Create bmad-test user
echo -e "${GREEN}[8/12] Creating bmad-test user...${NC}"
if ! id -u $BMAD_USER >/dev/null 2>&1; then
    useradd -m -s /bin/bash $BMAD_USER
    echo "$BMAD_USER:$BMAD_PASSWORD" | chpasswd
    usermod -aG sudo $BMAD_USER
    echo "$BMAD_USER ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/bmad-test
    chmod 440 /etc/sudoers.d/bmad-test
    echo -e "${GREEN}  ✓ User created: $BMAD_USER / $BMAD_PASSWORD${NC}"
else
    echo -e "${YELLOW}  User $BMAD_USER already exists${NC}"
fi

# Setup Python environment for bmad-test user
echo -e "${GREEN}[9/12] Setting up Python environment...${NC}"
sudo -u $BMAD_USER bash <<EOF
cd /home/$BMAD_USER

# Create virtual environment
python3 -m venv bmad-env
source bmad-env/bin/activate

# Install Python packages
pip install --upgrade pip setuptools wheel
pip install \
    langchain \
    langchain-community \
    langgraph \
    libtmux \
    rich \
    click \
    prompt-toolkit \
    pyyaml \
    watchdog \
    asyncio \
    aiofiles \
    pytest \
    pytest-asyncio \
    black \
    ruff \
    ipython

echo -e "${GREEN}  ✓ Python environment configured${NC}"
EOF

# Install BMad Method
echo -e "${GREEN}[10/12] Installing BMad Method...${NC}"
sudo -u $BMAD_USER bash <<'EOF'
cd /home/$BMAD_USER

# Install BMad (latest alpha)
npx bmad-method@alpha install

# Verify installation
if [ -d ".bmad-core" ]; then
    echo -e "  ✓ BMad installed successfully"
    echo "  Version: $(cat .bmad-core/core-config.yaml | grep version || echo 'unknown')"
else
    echo -e "  ⚠ BMad installation may have issues"
fi
EOF

# Setup project structure
echo -e "${GREEN}[11/12] Creating project structure...${NC}"
sudo -u $BMAD_USER bash <<'EOF'
cd /home/$BMAD_USER

# Create directory structure
mkdir -p projects
mkdir -p automation
mkdir -p automation/scripts
mkdir -p automation/configs
mkdir -p automation/logs
mkdir -p backups
mkdir -p .sandboxes

# Create README
cat > automation/README.md <<'README'
# BMad Automation Testing Environment

## Quick Start

1. Activate Python environment:
   ```
   source ~/bmad-env/bin/activate
   ```

2. Run automation:
   ```
   cd ~/projects/<your-project>
   python ~/automation/mvp_story_automation.py --project . --epic epic-1
   ```

3. Monitor with tmux:
   ```
   tmux attach -t bmad-epic-<epic-id>
   ```

## Safety Features

- VM isolation
- Resource limits enforced
- Snapshot capability
- Command sandboxing

## Directory Structure

- `~/projects/` - Test projects
- `~/automation/` - Automation scripts
- `~/automation/logs/` - Execution logs
- `~/backups/` - State backups
- `~/.sandboxes/` - Isolated execution environments

README

echo -e "  ✓ Project structure created"
EOF

# Configure Git
echo -e "${GREEN}[12/12] Configuring Git...${NC}"
sudo -u $BMAD_USER bash <<EOF
git config --global user.name "BMad Test Bot"
git config --global user.email "bmad-test@localhost"
git config --global init.defaultBranch main
git config --global core.editor vim
echo -e "  ✓ Git configured"
EOF

# Setup tmux configuration
sudo -u $BMAD_USER bash <<'EOF'
cat > /home/$BMAD_USER/.tmux.conf <<'TMUX'
# BMad Automation Tmux Configuration

# Enable mouse support
set -g mouse on

# Increase history
set -g history-limit 10000

# Better colors
set -g default-terminal "screen-256color"

# Status bar customization
set -g status-bg colour235
set -g status-fg colour136
set -g status-left '[#S] '
set -g status-right '%H:%M %d-%b-%y'
set -g status-left-length 20
set -g status-right-length 40

# Window notifications
setw -g monitor-activity on
set -g visual-activity on

# Pane border colors
set -g pane-border-style fg=colour235
set -g pane-active-border-style fg=colour136

# Easy reload config
bind r source-file ~/.tmux.conf \; display "Config reloaded!"

# Better pane splitting
bind | split-window -h
bind - split-window -v

# Pane switching with Alt+Arrow
bind -n M-Left select-pane -L
bind -n M-Right select-pane -R
bind -n M-Up select-pane -U
bind -n M-Down select-pane -D

# Logging
bind H pipe-pane -o "cat >> ~/automation/logs/tmux-#S-#W.log" \; display "Logging to ~/automation/logs/tmux-#S-#W.log"
TMUX
EOF

# Setup resource limits for safety
echo -e "${YELLOW}Configuring safety constraints...${NC}"

# User limits
cat > /etc/security/limits.d/bmad-test.conf <<'LIMITS'
# BMad test user resource limits
bmad-test soft nproc 200
bmad-test hard nproc 300
bmad-test soft nofile 2048
bmad-test hard nofile 4096
bmad-test soft memlock 2097152
bmad-test hard memlock 4194304
bmad-test soft cpu 60
bmad-test hard cpu 120
LIMITS

# Create safety wrapper script
sudo -u $BMAD_USER bash <<'EOF'
cat > /home/$BMAD_USER/automation/scripts/safe_run.sh <<'SAFE'
#!/bin/bash
#
# safe_run.sh - Safety wrapper for BMad automation
#
# Usage: safe_run.sh <command>
#

set -euo pipefail

# Safety limits
ulimit -t 3600      # CPU time: 1 hour
ulimit -v 4194304   # Virtual memory: 4GB
ulimit -f 1048576   # File size: 1GB
ulimit -u 100       # Max processes: 100

# Create sandbox
SANDBOX="/tmp/bmad_sandbox_$$"
mkdir -p "$SANDBOX"
cd "$SANDBOX"

# Log execution
echo "[$(date)] Executing in sandbox: $@" >> ~/automation/logs/safe_run.log

# Run with timeout
timeout --preserve-status 2h "$@"
EXIT_CODE=$?

# Cleanup
cd /
rm -rf "$SANDBOX"

exit $EXIT_CODE
SAFE

chmod +x /home/$BMAD_USER/automation/scripts/safe_run.sh
EOF

# Create quick setup script
cat > /home/$BMAD_USER/setup.sh <<'SETUP'
#!/bin/bash
# Quick environment setup
source ~/bmad-env/bin/activate
export PATH="$HOME/automation/scripts:$PATH"
echo "BMad environment activated!"
echo "Python: $(which python)"
echo "BMad: $(which bmad || echo 'not in PATH')"
SETUP
chmod +x /home/$BMAD_USER/setup.sh

# Create test project template
echo -e "${GREEN}Creating test project template...${NC}"
sudo -u $BMAD_USER bash <<'EOF'
cd /home/$BMAD_USER/projects

# Create sample project
mkdir -p test-project/docs/epics/epic-1
mkdir -p test-project/src
mkdir -p test-project/tests

# Create sample PRD
cat > test-project/docs/prd.md <<'PRD'
# Product Requirements Document

## Project: Test Application

### Overview
A simple test application for BMad automation testing.

### Features
1. User authentication
2. User profiles
3. Basic CRUD operations

PRD

# Create sample architecture
cat > test-project/docs/architecture.md <<'ARCH'
# Architecture Document

## Tech Stack
- Backend: Python/FastAPI
- Database: PostgreSQL
- Frontend: React

## Components
1. API Server
2. Database Layer
3. Authentication Service

ARCH

# Create sample stories
cat > test-project/docs/epics/epic-1/stories.yaml <<'STORIES'
epic_id: epic-1
title: "User Management System"
description: "Basic user management functionality"

stories:
  - id: story-1
    title: "User Registration"
    description: "Allow users to create new accounts"
    acceptance_criteria:
      - User can register with email and password
      - Email must be validated
      - Password must meet security requirements
      - Confirmation email is sent
    technical_notes: "Use bcrypt for password hashing, implement rate limiting"

  - id: story-2
    title: "User Login"
    description: "Allow users to authenticate"
    acceptance_criteria:
      - User can login with email/password
      - Session token is generated on success
      - Failed attempts are rate limited
      - Remember me option available
    technical_notes: "Use JWT tokens, 15 minute timeout"

  - id: story-3
    title: "Password Reset"
    description: "Allow users to reset forgotten passwords"
    acceptance_criteria:
      - User can request password reset via email
      - Reset link expires after 1 hour
      - User can set new password
      - Old sessions are invalidated
    technical_notes: "Generate secure random tokens"
STORIES

echo -e "  ✓ Test project template created"
EOF

# Final summary
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          Provisioning Complete!                ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}System Information:${NC}"
echo "  Hostname: $(hostname)"
echo "  IP Address: $(hostname -I | awk '{print $1}')"
echo "  Python: $(python3 --version)"
echo "  Node.js: $(node --version)"
echo "  User: $BMAD_USER / $BMAD_PASSWORD"
echo ""
echo -e "${BLUE}Quick Start:${NC}"
echo "  1. SSH into VM:"
echo "     ssh $BMAD_USER@$(hostname -I | awk '{print $1}')"
echo ""
echo "  2. Activate environment:"
echo "     source ~/setup.sh"
echo ""
echo "  3. Test automation:"
echo "     cd ~/projects/test-project"
echo "     python ~/automation/mvp_story_automation.py --project . --epic epic-1 --dry-run"
echo ""
echo -e "${YELLOW}Safety Features:${NC}"
echo "  ✓ Resource limits configured"
echo "  ✓ Isolated user environment"
echo "  ✓ Sandbox execution available"
echo "  ✓ Ready for snapshot"
echo ""
echo -e "${GREEN}Next step: Create a VM snapshot before testing${NC}"
echo "  On Proxmox host: qm snapshot 500 post-provision"
echo ""
echo -e "${GREEN}Log file: $LOG_FILE${NC}"