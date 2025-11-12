#!/bin/bash
#
# snapshot_manager.sh - Manage Proxmox VM snapshots for BMad automation
#
# Usage:
#   ./snapshot_manager.sh <action> [options]
#
# Actions:
#   create <name> <description>  - Create a new snapshot
#   list                         - List all snapshots
#   delete <name>                - Delete a snapshot
#   rollback <name>              - Rollback to a snapshot
#   auto-cleanup                 - Remove old snapshots (keep last N)
#   pre-epic <epic-id>           - Create pre-epic snapshot
#   post-story <story-id>        - Create post-story snapshot
#   checkpoint <description>     - Create manual checkpoint
#

set -euo pipefail

# Configuration
VM_ID=${BMAD_VM_ID:-500}
MAX_SNAPSHOTS=${MAX_KEEP:-10}
LOG_FILE="/var/log/bmad_snapshots.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check if running on Proxmox host
if ! command -v qm &> /dev/null; then
    echo -e "${RED}Error: This script must run on a Proxmox host.${NC}"
    exit 1
fi

# Logging function
log_action() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE" 2>/dev/null || true
    echo -e "${GREEN}$1${NC}"
}

# Create snapshot with timestamp
create_snapshot() {
    local name="$1"
    local desc="${2:-No description}"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local full_name="${name}_${timestamp}"

    echo -e "${BLUE}Creating snapshot: ${full_name}${NC}"
    echo "Description: $desc"

    if qm snapshot $VM_ID "$full_name" --description "$desc" 2>&1; then
        log_action "✓ Snapshot created: $full_name"
        echo "$full_name|$desc|$(date)" >> "${LOG_FILE}.history" 2>/dev/null || true
        return 0
    else
        echo -e "${RED}✗ Failed to create snapshot${NC}"
        return 1
    fi
}

# List all snapshots
list_snapshots() {
    echo -e "${BLUE}Snapshots for VM $VM_ID:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    qm listsnapshot $VM_ID 2>/dev/null || {
        echo -e "${RED}Failed to list snapshots${NC}"
        return 1
    }

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Count snapshots
    local count=$(qm listsnapshot $VM_ID 2>/dev/null | tail -n +2 | wc -l)
    echo -e "${GREEN}Total snapshots: $count${NC}"

    if [ $count -gt $MAX_SNAPSHOTS ]; then
        echo -e "${YELLOW}Warning: Exceeds maximum ($MAX_SNAPSHOTS). Consider cleanup.${NC}"
    fi
}

# Delete a snapshot
delete_snapshot() {
    local snap_name="$1"

    echo -e "${YELLOW}Deleting snapshot: $snap_name${NC}"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if qm delsnapshot $VM_ID "$snap_name" 2>&1; then
            log_action "✓ Snapshot deleted: $snap_name"
        else
            echo -e "${RED}✗ Failed to delete snapshot${NC}"
            return 1
        fi
    else
        echo "Cancelled."
    fi
}

# Rollback to snapshot
rollback_snapshot() {
    local snap_name="${1:-}"

    if [ -z "$snap_name" ]; then
        echo -e "${BLUE}Available snapshots:${NC}"
        list_snapshots
        echo
        read -p "Enter snapshot name to rollback to: " snap_name
    fi

    echo -e "${YELLOW}⚠ WARNING: Rollback to snapshot: $snap_name${NC}"
    echo "This will revert all changes made after this snapshot!"
    read -p "Are you sure? (yes/NO): " -r

    if [[ $REPLY == "yes" ]]; then
        # Check if VM is running
        if qm status $VM_ID | grep -q "running"; then
            echo "Stopping VM first..."
            qm stop $VM_ID
            sleep 5
        fi

        echo "Rolling back..."
        if qm rollback $VM_ID "$snap_name" 2>&1; then
            log_action "✓ Rolled back to: $snap_name"
            echo -e "${GREEN}Rollback complete!${NC}"

            read -p "Start VM now? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                qm start $VM_ID
                echo -e "${GREEN}VM started${NC}"
            fi
        else
            echo -e "${RED}✗ Rollback failed${NC}"
            return 1
        fi
    else
        echo "Rollback cancelled."
    fi
}

# Auto cleanup old snapshots
auto_cleanup() {
    echo -e "${BLUE}Auto-cleanup: Keeping last $MAX_SNAPSHOTS snapshots${NC}"

    local snapshots=$(qm listsnapshot $VM_ID 2>/dev/null | tail -n +2 | head -n -1)
    local count=$(echo "$snapshots" | wc -l)

    if [ $count -le $MAX_SNAPSHOTS ]; then
        echo "Current snapshots ($count) within limit. No cleanup needed."
        return 0
    fi

    local to_delete=$((count - MAX_SNAPSHOTS))
    echo -e "${YELLOW}Will delete $to_delete old snapshot(s)${NC}"

    # Get oldest snapshots
    echo "$snapshots" | head -n $to_delete | while read line; do
        local snap_name=$(echo "$line" | awk '{print $1}')
        echo "  Deleting: $snap_name"
        qm delsnapshot $VM_ID "$snap_name" 2>&1 || true
    done

    log_action "✓ Cleanup complete. Deleted $to_delete snapshot(s)"
}

# Create pre-epic snapshot
pre_epic_snapshot() {
    local epic_id="$1"
    create_snapshot "pre_epic_${epic_id}" "Before starting epic $epic_id"
    auto_cleanup
}

# Create post-story snapshot
post_story_snapshot() {
    local story_id="$1"
    create_snapshot "story_complete_${story_id}" "After completing story $story_id"

    # Less aggressive cleanup for story snapshots
    local story_count=$(qm listsnapshot $VM_ID 2>/dev/null | grep -c "story_complete" || true)
    if [ $story_count -gt 5 ]; then
        echo -e "${YELLOW}Note: Multiple story snapshots exist. Consider cleanup.${NC}"
    fi
}

# Create checkpoint
checkpoint_snapshot() {
    local desc="${1:-Manual checkpoint}"
    create_snapshot "checkpoint" "$desc"
    auto_cleanup
}

# Show snapshot history
show_history() {
    if [ -f "${LOG_FILE}.history" ]; then
        echo -e "${BLUE}Snapshot History:${NC}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        tail -20 "${LOG_FILE}.history" | while IFS='|' read name desc date; do
            echo -e "${GREEN}$name${NC}"
            echo "  Description: $desc"
            echo "  Date: $date"
            echo ""
        done
    else
        echo "No history file found."
    fi
}

# Interactive mode
interactive_mode() {
    while true; do
        echo ""
        echo -e "${BLUE}BMad VM Snapshot Manager${NC}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "1) List snapshots"
        echo "2) Create snapshot"
        echo "3) Delete snapshot"
        echo "4) Rollback to snapshot"
        echo "5) Auto-cleanup"
        echo "6) Show history"
        echo "q) Quit"
        echo ""
        read -p "Select action: " choice

        case $choice in
            1) list_snapshots ;;
            2)
                read -p "Snapshot name: " name
                read -p "Description: " desc
                create_snapshot "$name" "$desc"
                ;;
            3)
                list_snapshots
                read -p "Snapshot to delete: " name
                delete_snapshot "$name"
                ;;
            4) rollback_snapshot ;;
            5) auto_cleanup ;;
            6) show_history ;;
            q|Q) break ;;
            *) echo "Invalid option" ;;
        esac
    done
}

# Main execution
case "${1:-}" in
    create)
        if [ $# -lt 2 ]; then
            echo "Usage: $0 create <name> [description]"
            exit 1
        fi
        create_snapshot "$2" "${3:-No description}"
        ;;

    list)
        list_snapshots
        ;;

    delete)
        if [ $# -lt 2 ]; then
            echo "Usage: $0 delete <snapshot-name>"
            exit 1
        fi
        delete_snapshot "$2"
        ;;

    rollback)
        rollback_snapshot "${2:-}"
        ;;

    auto-cleanup)
        auto_cleanup
        ;;

    pre-epic)
        if [ $# -lt 2 ]; then
            echo "Usage: $0 pre-epic <epic-id>"
            exit 1
        fi
        pre_epic_snapshot "$2"
        ;;

    post-story)
        if [ $# -lt 2 ]; then
            echo "Usage: $0 post-story <story-id>"
            exit 1
        fi
        post_story_snapshot "$2"
        ;;

    checkpoint)
        checkpoint_snapshot "${2:-Manual checkpoint}"
        ;;

    history)
        show_history
        ;;

    interactive|i)
        interactive_mode
        ;;

    *)
        echo -e "${BLUE}BMad VM Snapshot Manager${NC}"
        echo ""
        echo "Usage: $0 <action> [options]"
        echo ""
        echo "Actions:"
        echo "  create <name> [desc]  - Create a new snapshot"
        echo "  list                  - List all snapshots"
        echo "  delete <name>         - Delete a snapshot"
        echo "  rollback [name]       - Rollback to a snapshot"
        echo "  auto-cleanup          - Remove old snapshots"
        echo "  pre-epic <id>         - Snapshot before epic"
        echo "  post-story <id>       - Snapshot after story"
        echo "  checkpoint [desc]     - Create manual checkpoint"
        echo "  history               - Show snapshot history"
        echo "  interactive           - Interactive mode"
        echo ""
        echo "Environment Variables:"
        echo "  BMAD_VM_ID   - VM ID (default: 500)"
        echo "  MAX_KEEP     - Max snapshots to keep (default: 10)"
        echo ""
        echo "Examples:"
        echo "  $0 create test_snapshot \"Before testing\""
        echo "  $0 pre-epic epic-1"
        echo "  $0 rollback"
        echo "  $0 interactive"
        ;;
esac