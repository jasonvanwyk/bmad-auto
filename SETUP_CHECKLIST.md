# BMad Automation Setup Checklist

Follow this checklist to set up your BMad automation environment step by step.

## Phase 1: Proxmox VM Setup ⚡

### Prerequisites
- [ ] Proxmox VE host available
- [ ] At least 8GB RAM free
- [ ] 50GB storage available
- [ ] Ubuntu 22.04 Server ISO downloaded

### VM Creation
- [ ] Run VM creation script:
  ```bash
  cd bmad-auto/scripts
  chmod +x create_bmad_test_vm.sh
  ./create_bmad_test_vm.sh
  ```
- [ ] Note VM ID (default: 500)
- [ ] Start VM: `qm start 500`
- [ ] Connect to console: `qm terminal 500`

### Ubuntu Installation
- [ ] Install Ubuntu 22.04 Server (minimal installation)
- [ ] Configure network (DHCP or static)
- [ ] Create initial user (can be 'ubuntu')
- [ ] Enable SSH server
- [ ] Complete installation and reboot

### Post-Installation
- [ ] Remove CD-ROM: `qm set 500 --ide2 none`
- [ ] Verify VM network: `qm guest cmd 500 network-get-interfaces`
- [ ] Note VM IP address: _______________
- [ ] Test SSH connection: `ssh ubuntu@<vm-ip>`

## Phase 2: VM Provisioning 🔧

### Run Provisioning Script
- [ ] SSH into VM as root/ubuntu
- [ ] Download provisioning script:
  ```bash
  wget https://raw.githubusercontent.com/yourusername/bmad-auto/main/scripts/provision_bmad_vm.sh
  # Or copy from local:
  scp scripts/provision_bmad_vm.sh root@<vm-ip>:/tmp/
  ```
- [ ] Run provisioning:
  ```bash
  sudo bash provision_bmad_vm.sh
  ```
- [ ] Note bmad-test user password: BmadTest123!

### Verify Installation
- [ ] System updated successfully
- [ ] Python 3.10+ installed: `python3 --version`
- [ ] Node.js installed: `node --version`
- [ ] Tmux installed: `tmux -V`
- [ ] BMad Method installed: `ls ~/.bmad-core`
- [ ] bmad-test user created

### Create Initial Snapshot
- [ ] On Proxmox host:
  ```bash
  qm snapshot 500 initial-setup --description "Clean BMad environment"
  ```

## Phase 3: Project Setup 📁

### SSH as bmad-test User
- [ ] SSH into VM:
  ```bash
  ssh bmad-test@<vm-ip>
  ```
- [ ] Activate environment:
  ```bash
  source ~/setup.sh
  ```

### Deploy Automation Scripts
- [ ] Clone repository:
  ```bash
  cd ~
  git clone https://github.com/yourusername/bmad-auto.git
  # Or copy from local
  ```
- [ ] Copy main script:
  ```bash
  cp bmad-auto/mvp_story_automation.py ~/automation/
  ```
- [ ] Copy configuration:
  ```bash
  cp bmad-auto/configs/bmad_automation_config.yaml ~/automation/configs/
  ```

### Install Python Dependencies
- [ ] Activate virtual environment:
  ```bash
  source ~/bmad-env/bin/activate
  ```
- [ ] Install requirements:
  ```bash
  cd ~/bmad-auto
  pip install libtmux rich click pyyaml
  ```

## Phase 4: Test Project Preparation 📝

### Verify Test Project
- [ ] Navigate to test project:
  ```bash
  cd ~/projects/test-project
  ```
- [ ] Check required files exist:
  - [ ] `docs/prd.md`
  - [ ] `docs/architecture.md`
  - [ ] `docs/epics/epic-1/stories.yaml`

### Customize Test Stories (Optional)
- [ ] Edit stories file:
  ```bash
  vim docs/epics/epic-1/stories.yaml
  ```
- [ ] Verify YAML syntax:
  ```bash
  python -c "import yaml; yaml.safe_load(open('docs/epics/epic-1/stories.yaml'))"
  ```

## Phase 5: First Test Run 🚀

### Pre-Test Snapshot
- [ ] On Proxmox host:
  ```bash
  cd bmad-auto/scripts
  ./snapshot_manager.sh pre-epic test-epic-1
  ```

### Dry Run Test
- [ ] In VM as bmad-test:
  ```bash
  cd ~/projects/test-project
  python ~/automation/mvp_story_automation.py \
    --project . \
    --epic epic-1 \
    --dry-run
  ```
- [ ] Verify output shows story processing
- [ ] Check no errors occurred

### Live Test (Single Story)
- [ ] Create another snapshot:
  ```bash
  # On Proxmox host
  ./snapshot_manager.sh checkpoint "Before live test"
  ```
- [ ] Modify stories.yaml to have only 1 story (temporarily)
- [ ] Run live test:
  ```bash
  python ~/automation/mvp_story_automation.py \
    --project . \
    --epic epic-1
  ```
- [ ] Monitor tmux session (in new terminal):
  ```bash
  tmux attach -t bmad-epic-epic-1
  ```

## Phase 6: Monitoring & Verification ✅

### During Execution
- [ ] Tmux session created successfully
- [ ] Can see story windows in tmux
- [ ] Progress displayed in terminal
- [ ] Checkpoint file created: `.bmad-checkpoint-epic-1.yaml`

### After Completion
- [ ] Summary statistics displayed
- [ ] Check logs:
  ```bash
  ls ~/automation/logs/
  ```
- [ ] Verify checkpoint saved
- [ ] Tmux session still accessible

### Success Indicators
- [ ] ✅ Story completed (even if QA failed)
- [ ] ✅ No system errors or crashes
- [ ] ✅ Can access all outputs
- [ ] ✅ VM still responsive

## Phase 7: Full Epic Test 🎯

### Preparation
- [ ] Create snapshot:
  ```bash
  ./snapshot_manager.sh pre-epic full-epic-1
  ```
- [ ] Restore full stories.yaml (3+ stories)
- [ ] Clear previous checkpoint:
  ```bash
  rm .bmad-checkpoint-epic-1.yaml
  ```

### Run Full Epic
- [ ] Execute automation:
  ```bash
  python ~/automation/mvp_story_automation.py \
    --project . \
    --epic epic-1
  ```
- [ ] Monitor progress
- [ ] Watch for any escalations
- [ ] Let it run to completion

### Post-Run Analysis
- [ ] Review summary statistics
- [ ] Check success rate
- [ ] Examine any failures
- [ ] Review generated code (if any)

## Phase 8: Safety Verification 🛡️

### Test Safety Features
- [ ] Verify VM hostname check works:
  ```bash
  python ~/automation/mvp_story_automation.py \
    --project . --epic epic-1 --dry-run
  # Should show: "bmad-automation-test"
  ```
- [ ] Test checkpoint resume:
  ```bash
  # Interrupt a run with Ctrl-C
  # Then resume:
  python ~/automation/mvp_story_automation.py \
    --project . --epic epic-1 --resume
  ```

### Test Rollback
- [ ] On Proxmox host:
  ```bash
  ./snapshot_manager.sh list
  ./snapshot_manager.sh rollback
  # Select a snapshot
  ```
- [ ] Verify VM restored correctly

## Troubleshooting Checklist 🔧

If something goes wrong:

### VM Issues
- [ ] Check VM status: `qm status 500`
- [ ] Check VM logs: `qm terminal 500`
- [ ] Verify network: `ping <vm-ip>`
- [ ] Check resources: `qm config 500`

### Automation Issues
- [ ] Python environment active?
  ```bash
  which python
  # Should show: /home/bmad-test/bmad-env/bin/python
  ```
- [ ] BMad installed?
  ```bash
  ls ~/.bmad-core
  ```
- [ ] Required files exist?
  ```bash
  ls docs/prd.md docs/architecture.md
  ```
- [ ] YAML valid?
  ```bash
  python -c "import yaml; print(yaml.safe_load(open('docs/epics/epic-1/stories.yaml')))"
  ```

### Recovery Steps
- [ ] Kill stuck processes:
  ```bash
  pkill -f bmad_automation
  tmux kill-server
  ```
- [ ] Rollback VM:
  ```bash
  qm rollback 500 initial-setup
  ```
- [ ] Start fresh:
  ```bash
  rm -rf ~/projects/test-project/.bmad-checkpoint-*
  git worktree prune
  ```

## Success Criteria ✨

You're ready for production use when:

- [ ] ✅ Can run a 3-story epic successfully
- [ ] ✅ Checkpoint/resume works
- [ ] ✅ Tmux monitoring functional
- [ ] ✅ VM snapshots tested
- [ ] ✅ Safety checks pass
- [ ] ✅ Understand the logs and output

## Next Steps 🚀

Once basic setup is complete:

1. **Customize Configuration**
   - Edit `~/automation/configs/bmad_automation_config.yaml`
   - Adjust timeouts and retry limits
   - Configure agent models

2. **Test with Real Project**
   - Copy your actual project to VM
   - Ensure planning phase complete
   - Run automation on real stories

3. **Add Enhancements**
   - Enable parallel story execution
   - Configure HITL thresholds
   - Set up monitoring dashboard

4. **Production Deployment**
   - Create production VM
   - Implement backup strategy
   - Set up CI/CD integration

## Quick Reference 📚

### Essential Commands
```bash
# VM Management
qm start 500                        # Start VM
qm stop 500                         # Stop VM
qm snapshot 500 <name>              # Create snapshot
qm rollback 500 <name>              # Restore snapshot
qm terminal 500                     # Console access

# In VM
source ~/bmad-env/bin/activate      # Activate Python env
tmux attach -t bmad-epic-<id>       # Monitor execution
tail -f ~/automation/logs/*.log     # View logs

# Emergency
Ctrl-C                              # Stop automation
pkill -f bmad                       # Kill all BMad processes
tmux kill-server                    # Kill all tmux sessions
```

### File Locations
```
~/projects/test-project/            # Test project
~/automation/                       # Automation scripts
~/automation/logs/                  # Execution logs
~/automation/configs/               # Configuration
~/.bmad-core/                      # BMad installation
/tmp/bmad_sandbox_*/               # Temporary execution
```

## Completion Confirmation ☑️

### Final Checks
- [ ] All phases completed successfully
- [ ] Test epic ran without critical errors
- [ ] Understand how to monitor and control execution
- [ ] Know how to rollback if needed
- [ ] Documentation reviewed and understood

### Sign-off
- [ ] Date: _______________
- [ ] Tested by: _______________
- [ ] Environment ready for use

---

🎉 **Congratulations!** Your BMad automation environment is ready!

Remember: Always snapshot before major tests, and keep your VM isolated for safety.

For support, refer to the main [README](README.md) or [comprehensive documentation](bmad-auto.md).