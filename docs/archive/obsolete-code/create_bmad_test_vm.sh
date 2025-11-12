#!/bin/bash
#
# create_bmad_test_vm.sh - Create Proxmox VM for BMad automation testing
#
# Usage: ./create_bmad_test_vm.sh [VM_ID]
#
# This script creates a Proxmox VM specifically configured for
# safe BMad automation testing with proper isolation and resource limits.
#

set -euo pipefail

# Configuration
VM_ID=${1:-500}
VM_NAME="bmad-automation-test"
VM_CORES=4
VM_RAM=8192  # 8GB RAM
VM_DISK=50   # 50GB disk
VM_BRIDGE="vmbr0"
STORAGE="local-lvm"
ISO_PATH="local:iso/ubuntu-22.04.3-live-server-amd64.iso"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}BMad Automation Test VM Creator${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if running on Proxmox host
if ! command -v qm &> /dev/null; then
    echo -e "${RED}Error: 'qm' command not found. This script must run on a Proxmox host.${NC}"
    exit 1
fi

# Check if VM already exists
if qm status $VM_ID &> /dev/null; then
    echo -e "${YELLOW}VM $VM_ID already exists.${NC}"
    read -p "Do you want to destroy it and recreate? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Stopping and destroying VM $VM_ID..."
        qm stop $VM_ID 2>/dev/null || true
        sleep 2
        qm destroy $VM_ID
    else
        echo "Exiting without changes."
        exit 0
    fi
fi

# Create the VM
echo -e "${GREEN}Creating VM $VM_ID ($VM_NAME)...${NC}"

qm create $VM_ID \
  --name $VM_NAME \
  --memory $VM_RAM \
  --cores $VM_CORES \
  --sockets 1 \
  --cpu host \
  --net0 virtio,bridge=$VM_BRIDGE \
  --scsihw virtio-scsi-pci \
  --scsi0 ${STORAGE}:${VM_DISK} \
  --ide2 ${ISO_PATH},media=cdrom \
  --boot order=scsi0 \
  --agent enabled=1 \
  --ostype l26 \
  --description "BMad Automation Testing VM - Isolated environment for safe AI agent testing"

echo -e "${GREEN}✓ VM created successfully${NC}"

# Set additional features
echo "Configuring VM settings..."

# Enable QEMU Guest Agent
qm set $VM_ID --agent enabled=1,fstrim_cloned_disks=1

# Set CPU type for better performance
qm set $VM_ID --cpu host

# Enable protection to prevent accidental deletion
qm set $VM_ID --protection 1

# Disable autostart (manual control)
qm set $VM_ID --onboot 0

# Set resource limits to prevent runaway processes
qm set $VM_ID \
  --cpulimit $VM_CORES \
  --cpuunits 1000

# Create initial snapshot before OS installation
echo -e "${GREEN}Creating pre-install snapshot...${NC}"
qm snapshot $VM_ID pre-install --description "Clean VM before OS installation"

# Display VM configuration
echo ""
echo -e "${GREEN}VM Configuration:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
qm config $VM_ID | grep -E "name:|cores:|memory:|scsi0:|net0:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Start instructions
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}VM created successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Start the VM:        qm start $VM_ID"
echo "2. Open console:        qm terminal $VM_ID"
echo "   Or use web UI:       https://<proxmox-host>:8006"
echo "3. Install Ubuntu 22.04 Server"
echo "4. After installation:"
echo "   a. Remove CD-ROM:    qm set $VM_ID --ide2 none"
echo "   b. Reboot VM:        qm reboot $VM_ID"
echo "   c. Run provisioning: ./provision_bmad_vm.sh"
echo ""
echo "To connect via SSH after OS installation:"
echo "  ssh root@\$(qm guest cmd $VM_ID network-get-interfaces | grep -A1 '\"name\":\"eth0\"' | grep ip-address | cut -d'\"' -f4)"
echo ""
echo -e "${YELLOW}Safety Note: This VM has protection enabled to prevent accidental deletion.${NC}"
echo -e "${YELLOW}To remove protection: qm set $VM_ID --protection 0${NC}"

# Optional: Start the VM automatically
read -p "Do you want to start the VM now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting VM..."
    qm start $VM_ID
    echo -e "${GREEN}VM started. Please proceed with OS installation.${NC}"
    echo "Console access: qm terminal $VM_ID"
else
    echo "VM created but not started. Start with: qm start $VM_ID"
fi

echo ""
echo -e "${GREEN}Script completed successfully!${NC}"