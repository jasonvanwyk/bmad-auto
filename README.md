# BMad Automation System

> Intelligent orchestration for the BMad Method development phase, automating the story cycle while preserving human creativity in planning.

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![BMad](https://img.shields.io/badge/BMad-v4.44.3-green)](https://github.com/bmad-code-org/BMAD-METHOD)
[![Status](https://img.shields.io/badge/status-MVP-yellow)](https://github.com/jasonvanwyk/bmad-auto)

## 🚀 Overview

BMad Automation revolutionizes the development workflow by automating the repetitive story development cycle (SM → PO → Dev → QA) while maintaining human control over strategic planning decisions. Run multiple stories in parallel, handle failures intelligently, and maintain full visibility through tmux sessions.

### Why BMad Automation?

The [BMad Method](https://github.com/bmad-code-org/BMAD-METHOD) provides a powerful framework for AI-driven development, but manually orchestrating multiple AI agents (Scrum Master, Product Owner, Developer, QA) through each story becomes repetitive and time-consuming. **BMad Automation solves this by:**

- **Eliminating repetitive agent interactions** - No more manually switching between SM, PO, Dev, and QA roles for each story
- **Maintaining consistent quality** - Automated validation ensures every story follows the same rigorous process
- **Scaling your workflow** - Process multiple stories in parallel instead of one at a time
- **Freeing you for high-value work** - Focus on architecture, planning, and creative problem-solving while automation handles the execution

You stay in control of the "what" (PRD, Architecture, Story planning) while automation handles the "how" (repetitive agent execution).

### Key Features

- **🔄 Automated Story Pipeline**: SM draft → PO validate → Dev implement → QA test
- **⚡ Parallel Execution**: Process multiple stories simultaneously with git worktrees
- **🛡️ VM Safety**: Complete isolation in Proxmox VM with snapshot/rollback
- **👁️ Full Visibility**: Real-time monitoring through tmux sessions
- **🤝 Human-in-the-Loop**: Intelligent escalation for critical decisions
- **💾 Checkpoint/Resume**: Never lose progress with automatic checkpointing
- **📊 Rich Dashboard**: Beautiful terminal UI with progress tracking

## 📋 Prerequisites

### On Proxmox Host
- Proxmox VE 7.0+
- At least 8GB RAM available for VM
- 50GB storage space
- Ubuntu 22.04 Server ISO

### In Development Environment
- Python 3.10+
- Node.js 18+ and npm
- BMad Method installed (`npx bmad-method@alpha install`)
- Completed planning phase:
  - PRD (`docs/prd.md`)
  - Architecture (`docs/architecture.md`)
  - Sharded stories (`docs/epics/<epic-id>/stories.yaml`)

## 🛠️ Installation

### Step 1: Create Proxmox VM

On your Proxmox host:

```bash
cd bmad-auto/scripts
chmod +x create_bmad_test_vm.sh
./create_bmad_test_vm.sh

# Follow prompts to install Ubuntu 22.04 Server
# After installation, remove CD-ROM:
qm set 500 --ide2 none
```

### Step 2: Provision VM

SSH into the VM and run:

```bash
wget https://raw.githubusercontent.com/jasonvanwyk/bmad-auto/main/scripts/provision_bmad_vm.sh
sudo bash provision_bmad_vm.sh
```

This installs:
- Python environment with all dependencies
- BMad Method framework
- Tmux configuration
- Safety constraints
- Test project template

### Step 3: Create Initial Snapshot

On Proxmox host:

```bash
qm snapshot 500 post-provision --description "Clean BMad environment ready for testing"
```

### Step 4: Deploy Automation Scripts

As `bmad-test` user in VM:

```bash
cd ~
git clone git@github.com:jasonvanwyk/bmad-auto.git
cd bmad-auto

# Install Python dependencies
source ~/bmad-env/bin/activate
pip install -r requirements.txt

# Copy automation script
cp mvp_story_automation.py ~/automation/
```

## 🚦 Quick Start

### 1. Prepare Your Project

```bash
# Create project structure
cd ~/projects/myproject
mkdir -p docs/epics/epic-1

# Create PRD and Architecture docs (if not existing)
# These should come from your planning phase

# Create story file
cat > docs/epics/epic-1/stories.yaml <<EOF
epic_id: epic-1
title: "User Management"
stories:
  - id: story-1
    title: "User Registration"
    acceptance_criteria:
      - User can register with email/password
      - Email validation implemented
EOF
```

### 2. Run Automation (Dry Run First)

```bash
# Activate environment
source ~/bmad-env/bin/activate

# Test with dry run
python ~/automation/mvp_story_automation.py \
  --project ~/projects/myproject \
  --epic epic-1 \
  --dry-run

# If successful, take snapshot
```

### 3. Run Live Automation

On Proxmox host, create pre-run snapshot:

```bash
./scripts/snapshot_manager.sh pre-epic epic-1
```

In VM:

```bash
# Run automation
python ~/automation/mvp_story_automation.py \
  --project ~/projects/myproject \
  --epic epic-1

# Monitor in another terminal
tmux attach -t bmad-epic-epic-1
```

### 4. Monitor Progress

```bash
# View tmux sessions
tmux ls

# Attach to session
tmux attach -t bmad-epic-epic-1

# Navigate windows
# Ctrl-b, w  - Window list
# Ctrl-b, n  - Next window
# Ctrl-b, p  - Previous window

# View logs
tail -f ~/automation/logs/epic-1.log
```

## 📁 Project Structure

```
bmad-auto/
├── README.md                    # This file
├── bmad-auto.md                 # Comprehensive documentation
├── requirements.txt             # Python dependencies
├── mvp_story_automation.py      # Main automation script
│
├── scripts/
│   ├── create_bmad_test_vm.sh  # Proxmox VM creation
│   ├── provision_bmad_vm.sh    # VM setup and configuration
│   ├── snapshot_manager.sh     # Snapshot management
│   └── safe_run.sh            # Safety wrapper
│
├── configs/
│   ├── bmad_automation_config.yaml  # Main configuration
│   └── epic_template.yaml           # Epic story template
│
├── src/
│   ├── tmux_manager.py         # Tmux session management
│   ├── safety_wrapper.py       # Command validation
│   ├── hitl_interface.py       # Human-in-the-loop
│   └── monitoring.py           # Dashboard and metrics
│
└── tests/
    ├── test_automation.py      # Unit tests
    └── test_safety.py          # Safety constraint tests
```

## ⚙️ Configuration

Edit `configs/bmad_automation_config.yaml`:

```yaml
automation:
  mode: supervised        # auto, supervised, manual
  parallel_stories: 3     # Stories to run in parallel
  max_retries: 3         # Retry attempts per stage

hitl:
  enabled: true
  escalation_thresholds:
    agent_timeout: 900   # 15 minutes
    confidence_minimum: 0.7
    qa_failure_max: 2

agents:
  models:
    sm: haiku
    dev: sonnet         # More capable for coding
    qa: haiku
```

## 🔒 Safety Features

### VM Isolation
- Runs in dedicated Proxmox VM
- Hostname verification (`bmad-automation-test`)
- Resource limits enforced
- Network isolation (optional)

### Command Sandboxing
- Dangerous commands blocked
- Protected system paths
- File operation limits
- Execution timeouts

### Snapshot Protection
- Pre-epic snapshots
- Story checkpoints
- Easy rollback on failure
- Automatic cleanup

## 🎯 Usage Examples

### Basic Epic Run
```bash
python mvp_story_automation.py --project ./myproject --epic epic-1
```

### Resume from Checkpoint
```bash
python mvp_story_automation.py --project ./myproject --epic epic-1 --resume
```

### Skip VM Safety Check (Dangerous!)
```bash
python mvp_story_automation.py --project ./myproject --epic epic-1 --no-vm-check
```

### Dry Run Testing
```bash
python mvp_story_automation.py --project ./myproject --epic epic-1 --dry-run
```

## 📊 Monitoring & Debugging

### View Real-time Dashboard
```python
# In separate terminal
python src/monitoring.py --epic epic-1
```

### Check Story Status
```bash
# View checkpoint file
cat .bmad-checkpoint-epic-1.yaml

# Check tmux windows
tmux list-windows -t bmad-epic-epic-1
```

### Emergency Stop
```bash
# In orchestrator tmux window
Ctrl-C

# Or kill all processes
pkill -f bmad_automation
```

## 🚨 Troubleshooting

### VM Issues

| Problem | Solution |
|---------|----------|
| Can't create VM | Check Proxmox storage space |
| VM won't start | Verify ISO path in script |
| Network issues | Check bridge configuration |

### Automation Issues

| Problem | Solution |
|---------|----------|
| Agent timeout | Increase timeout in config |
| Tmux not found | Install: `apt install tmux` |
| Import errors | Activate venv: `source ~/bmad-env/bin/activate` |
| Stories not found | Verify `docs/epics/<epic>/stories.yaml` exists |

### Recovery Procedures

```bash
# Rollback VM to previous state
qm rollback 500 <snapshot-name>

# Clean up stuck worktrees
git worktree prune
git worktree remove stories/story-* --force

# Reset automation state
rm .bmad-checkpoint-*.yaml
tmux kill-session -t bmad-epic-*
```

## 📈 Roadmap

### Phase 1: MVP ✅
- [x] Basic story automation
- [x] VM safety setup
- [x] Checkpoint/resume
- [x] Tmux integration

### Phase 2: Enhancement 🚧
- [ ] Parallel story execution
- [ ] HITL decision system
- [ ] Git worktree isolation
- [ ] Cost tracking

### Phase 3: Production 📅
- [ ] LangGraph orchestration
- [ ] MCP server communication
- [ ] CI/CD integration
- [ ] Web dashboard

### Phase 4: Scale 🚀
- [ ] Multi-epic processing
- [ ] Distributed execution
- [ ] ML-based optimization
- [ ] Cloud deployment

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone repository
git clone git@github.com:jasonvanwyk/bmad-auto.git
cd bmad-auto

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/
```

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

This project builds upon the excellent work of:

- **[BMad Method](https://github.com/bmad-code-org/BMAD-METHOD)** - The foundational AI-driven development framework that makes this automation possible. BMad Automation extends the BMad Method by automating the repetitive orchestration of its agent-based workflow.
- [LangGraph](https://github.com/langchain-ai/langgraph) - State machine orchestration
- [libtmux](https://github.com/tmux-python/libtmux) - Tmux automation
- [Rich](https://github.com/Textualize/rich) - Beautiful terminal UI

## 📞 Support

- 🐛 Issues: [GitHub Issues](https://github.com/jasonvanwyk/bmad-auto/issues)
- 📖 Docs: [Full Documentation](bmad-auto.md)
- 💬 Discussions: [GitHub Discussions](https://github.com/jasonvanwyk/bmad-auto/discussions)

## ⚡ Quick Commands Reference

```bash
# VM Management
qm start 500                    # Start VM
qm stop 500                     # Stop VM
qm snapshot 500 <name>          # Create snapshot
qm rollback 500 <name>          # Rollback to snapshot
qm terminal 500                 # Console access

# Automation Control
./run_epic.sh epic-1            # Helper script
tmux attach -t bmad-epic-epic-1 # Monitor execution
tmux kill-session -t bmad-*     # Stop all sessions

# Safety Checks
hostname                        # Verify VM environment
whoami                         # Should be: bmad-test
git worktree list              # Check active worktrees
```

---

**⚠️ Remember**: Always test in the VM first! Your main system will thank you. 🙏

*Built with ❤️ for the BMad community*