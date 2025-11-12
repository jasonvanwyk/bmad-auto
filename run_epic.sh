#!/bin/bash
#
# run_epic.sh - Simple wrapper to run BMad epic automation
#
# Usage: ./run_epic.sh <epic-id> [options]
#

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
PYTHON_ENV="${PYTHON_ENV:-$HOME/bmad-env}"
AUTOMATION_SCRIPT="${AUTOMATION_SCRIPT:-$HOME/automation/mvp_story_automation.py}"
VM_CHECK="${VM_CHECK:-true}"

# Help function
show_help() {
    cat << EOF
BMad Epic Automation Runner

Usage: $0 <epic-id> [options]

Arguments:
    epic-id         The ID of the epic to process

Options:
    --project DIR   Project directory (default: current directory)
    --dry-run       Run in dry-run mode (no actual execution)
    --no-vm-check   Skip VM safety check
    --resume        Resume from checkpoint
    --help          Show this help message

Environment Variables:
    PROJECT_DIR     Project directory (default: pwd)
    PYTHON_ENV      Python virtual environment path
    AUTOMATION_SCRIPT Path to automation script

Examples:
    $0 epic-1                    # Run epic-1 in current directory
    $0 epic-1 --dry-run          # Dry run test
    $0 epic-1 --project /path    # Specify project path
    $0 epic-1 --resume           # Resume from checkpoint

EOF
}

# Parse arguments
if [ $# -eq 0 ] || [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_help
    exit 0
fi

EPIC_ID="$1"
shift

# Default options
DRY_RUN=""
RESUME=""
NO_VM_CHECK=""

# Parse options
while [[ $# -gt 0 ]]; do
    case "$1" in
        --project)
            PROJECT_DIR="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN="--dry-run"
            shift
            ;;
        --no-vm-check)
            NO_VM_CHECK="--no-vm-check"
            VM_CHECK="false"
            shift
            ;;
        --resume)
            RESUME="--resume"
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Header
echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     BMad Epic Automation Runner        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Validate environment
echo -e "${GREEN}Checking environment...${NC}"

# Check if in VM (if required)
if [ "$VM_CHECK" = "true" ]; then
    HOSTNAME=$(hostname)
    if [[ ! "$HOSTNAME" == *"bmad-automation-test"* ]]; then
        echo -e "${YELLOW}⚠ Warning: Not running in test VM${NC}"
        echo "Hostname: $HOSTNAME"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Aborted."
            exit 1
        fi
        NO_VM_CHECK="--no-vm-check"
    else
        echo -e "${GREEN}✓ Running in test VM${NC}"
    fi
fi

# Check Python environment
if [ -d "$PYTHON_ENV" ]; then
    echo -e "${GREEN}✓ Python environment found${NC}"
    source "$PYTHON_ENV/bin/activate"
else
    echo -e "${RED}✗ Python environment not found at: $PYTHON_ENV${NC}"
    exit 1
fi

# Check automation script
if [ ! -f "$AUTOMATION_SCRIPT" ]; then
    echo -e "${YELLOW}Automation script not found at: $AUTOMATION_SCRIPT${NC}"
    echo "Looking for alternative location..."

    # Try local directory
    if [ -f "./mvp_story_automation.py" ]; then
        AUTOMATION_SCRIPT="./mvp_story_automation.py"
        echo -e "${GREEN}✓ Found script in current directory${NC}"
    else
        echo -e "${RED}✗ Script not found${NC}"
        exit 1
    fi
fi

# Check project directory
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}✗ Project directory not found: $PROJECT_DIR${NC}"
    exit 1
fi

# Check required files
echo -e "${GREEN}Checking project structure...${NC}"

REQUIRED_FILES=(
    "$PROJECT_DIR/docs/prd.md"
    "$PROJECT_DIR/docs/architecture.md"
    "$PROJECT_DIR/docs/epics/$EPIC_ID/stories.yaml"
)

ALL_PRESENT=true
for FILE in "${REQUIRED_FILES[@]}"; do
    if [ -f "$FILE" ]; then
        echo -e "  ${GREEN}✓${NC} $(basename "$FILE")"
    else
        echo -e "  ${RED}✗${NC} $(basename "$FILE") - NOT FOUND"
        ALL_PRESENT=false
    fi
done

if [ "$ALL_PRESENT" = false ]; then
    echo -e "${RED}Missing required files. Complete planning phase first.${NC}"
    exit 1
fi

# Show configuration
echo ""
echo -e "${BLUE}Configuration:${NC}"
echo "  Epic ID:     $EPIC_ID"
echo "  Project:     $PROJECT_DIR"
echo "  Python:      $(which python)"
echo "  Dry Run:     $([ -n "$DRY_RUN" ] && echo "Yes" || echo "No")"
echo "  Resume:      $([ -n "$RESUME" ] && echo "Yes" || echo "No")"
echo "  VM Check:    $VM_CHECK"
echo ""

# Confirm execution
if [ -z "$DRY_RUN" ]; then
    read -p "Ready to start automation. Continue? (Y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        echo "Aborted."
        exit 0
    fi
fi

# Create pre-execution snapshot (if on Proxmox host)
if command -v qm &> /dev/null && [ "$VM_CHECK" = "true" ]; then
    echo -e "${GREEN}Creating pre-execution snapshot...${NC}"
    SNAPSHOT_NAME="pre_epic_${EPIC_ID}_$(date +%Y%m%d_%H%M%S)"
    qm snapshot 500 "$SNAPSHOT_NAME" --description "Before epic $EPIC_ID execution" || true
fi

# Run automation
echo ""
echo -e "${GREEN}Starting automation...${NC}"
echo "════════════════════════════════════════"

# Build command
CMD="python $AUTOMATION_SCRIPT"
CMD="$CMD --project $PROJECT_DIR"
CMD="$CMD --epic $EPIC_ID"

if [ -n "$DRY_RUN" ]; then
    CMD="$CMD --dry-run"
fi

if [ -n "$RESUME" ]; then
    CMD="$CMD --resume"
fi

if [ -n "$NO_VM_CHECK" ]; then
    CMD="$CMD --no-vm-check"
fi

echo "Executing: $CMD"
echo ""

# Execute with error handling
set +e
$CMD
EXIT_CODE=$?
set -e

# Handle exit code
echo ""
echo "════════════════════════════════════════"

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ Automation completed successfully!${NC}"

    # Show tmux attach command
    echo ""
    echo "View in tmux:"
    echo "  tmux attach -t bmad-epic-$EPIC_ID"

elif [ $EXIT_CODE -eq 130 ]; then
    echo -e "${YELLOW}⚠ Automation interrupted (Ctrl+C)${NC}"
    echo "Checkpoint saved. Resume with:"
    echo "  $0 $EPIC_ID --resume"

else
    echo -e "${RED}✗ Automation failed with exit code: $EXIT_CODE${NC}"

    # Suggest rollback
    if command -v qm &> /dev/null && [ "$VM_CHECK" = "true" ]; then
        echo ""
        echo "To rollback VM to previous state:"
        echo "  qm rollback 500 <snapshot-name>"
    fi
fi

# Cleanup Python environment
deactivate 2>/dev/null || true

exit $EXIT_CODE