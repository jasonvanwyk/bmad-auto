# BMad Automation System

> **LangGraph-based orchestrator for the BMad Method**, automating the story development cycle (SM → PO → Dev → QA) while maintaining full BMad compliance.

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![BMad](https://img.shields.io/badge/BMad-v4.44.3-green)](https://github.com/bmad-code-org/BMAD-METHOD)
[![Status](https://img.shields.io/badge/status-Design%20Complete-green)](https://github.com/jasonvanwyk/bmad-auto)

---

## 🎯 What Is This?

BMad Automation is an intelligent orchestrator that automates the repetitive agent workflow of the [BMad Method](https://github.com/bmad-code-org/BMAD-METHOD) - specifically the story development cycle where you manually invoke @sm, @po, @dev, and @qa agents for each story.

**The Problem**: Manually running `/sm *create`, `/po *validate`, `/dev *develop-story`, `/qa *test` for every story is time-consuming and repetitive.

**The Solution**: Let LangGraph orchestrate the workflow. You focus on planning (PRD, Architecture, Epics), automation handles execution.

---

## 🚀 Key Features

- **✅ BMad Compliant** - Agents load full context (architecture docs, checklists, tasks)
- **🔄 Full Automation** - SM → PO → Dev → QA pipeline runs autonomously
- **🔒 Context Safe** - Fresh Claude Code instance per agent (no context bloat)
- **🎭 Session Isolation** - Each agent runs in isolated tmux session
- **📁 File-Based** - Monitors story files for completion (not stdout parsing)
- **💾 Checkpoint/Resume** - Never lose progress
- **🛡️ VM Safe** - Runs in Proxmox VM with snapshot/rollback
- **👁️ Live Monitoring** - Attach to tmux sessions to watch agents work

---

## 📐 Architecture

```
LangGraph Orchestrator
    ↓ spawns
Tmux Sessions (bmad-sm-1.1, bmad-po-1.1, etc.)
    ↓ runs
Claude Code with BMad agents (/sm *create, /po *validate, etc.)
    ↓ writes
Story Files (docs/stories/1.1.story.md)
    ↓ monitors
File System (orchestrator detects changes)
```

**See**: [docs/design/](./docs/design/) for complete architecture documentation

---

## 📋 Prerequisites

- **System**: Ubuntu 24.04 LTS (recommended: Proxmox VM)
- **Python**: 3.10+
- **Claude Code**: Installed and configured (`claude --version`)
- **BMad Method**: Project with `.bmad-core/` configuration
- **Planning Complete**: PRD, Architecture, and Epic files ready

---

## 🛠️ Installation

### 1. Clone Repository

```bash
cd ~
git clone https://github.com/jasonvanwyk/bmad-auto.git
cd bmad-auto
```

### 2. Set Up Environment

```bash
# Create virtual environment
python3 -m venv ~/bmad-env
source ~/bmad-env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Verify Setup

```bash
# Check Claude Code
claude --version

# Check tmux
tmux -V

# Check BMad project exists
ls ~/projects/your-project/.bmad-core/
```

---

## 🚦 Quick Start

### Run Single Story (MVP)

```bash
source ~/bmad-env/bin/activate
cd ~/bmad-auto

# Test with single story
python scripts/test_mvp.py
```

### Monitor Execution

```bash
# In another terminal
tmux ls                          # List sessions
tmux attach -t bmad-sm-1-1       # Watch SM agent
# Ctrl-b, d to detach
```

### Check Results

```bash
# View created story file
cat ~/projects/your-project/docs/stories/1.1.story.md

# View checkpoint
cat ~/projects/your-project/.bmad-checkpoint-epic-1.yaml
```

---

## 📁 Project Structure

```
bmad-auto/
├── README.md                         # This file
├── requirements.txt                  # Python dependencies
├── .gitignore                        # Git ignore rules
│
├── docs/
│   ├── design/                       # 🎯 ACTIVE DESIGN DOCUMENTS
│   │   ├── README.md                 # Design overview
│   │   ├── orchestrator.md           # LangGraph state machine
│   │   ├── tmux-sessions.md          # Session management
│   │   ├── file-communication.md     # File monitoring protocol
│   │   ├── claude-code-cli.md        # CLI invocation guide
│   │   └── implementation-roadmap.md # Implementation phases
│   │
│   └── archive/                      # 📦 LEARNING JOURNEY & OBSOLETE
│       ├── learning-journey/         # Design evolution documents
│       └── obsolete-code/            # Previous implementation attempts
│
├── src/                              # 🚀 NEW IMPLEMENTATION
│   ├── __init__.py
│   ├── orchestrator.py               # LangGraph orchestrator (Phase 1)
│   ├── tmux_manager.py               # Tmux session management (Phase 1)
│   ├── file_monitor.py               # File monitoring & parsing (Phase 1)
│   └── checkpoint_manager.py         # Checkpoint persistence (Phase 3)
│
├── tests/                            # ✅ TEST SUITE
│   ├── __init__.py
│   ├── test_tmux_manager.py
│   ├── test_file_monitor.py
│   └── test_orchestrator.py
│
├── scripts/                          # 🔧 UTILITY SCRIPTS
│   ├── test_mvp.py                   # MVP integration test
│   └── snapshot_manager.sh           # VM snapshot management
│
└── configs/                          # ⚙️ CONFIGURATION
    └── default.yaml                  # Default orchestrator config
```

---

## 📖 Documentation

### Design Documents

- **[Architecture Overview](./docs/design/README.md)** - Start here
- **[Orchestrator Design](./docs/design/orchestrator.md)** - LangGraph state machine
- **[Session Management](./docs/design/tmux-sessions.md)** - Tmux isolation
- **[File Communication](./docs/design/file-communication.md)** - Monitoring protocol
- **[Claude Code CLI](./docs/design/claude-code-cli.md)** - Invocation guide
- **[Implementation Roadmap](./docs/design/implementation-roadmap.md)** - 5-phase plan

### Learning Journey

- **[Original Vision](./docs/archive/learning-journey/bmad-auto-original.md)** - Initial concept
- **[Reality Check](./docs/archive/learning-journey/reality-check.md)** - BMad is IDE-based discovery
- **[BMad Compliant Design](./docs/archive/learning-journey/bmad-compliant-design.md)** - How BMad actually works

---

## 🏗️ Implementation Status

### Phase 1: MVP (In Progress)
- [x] ✅ Design complete
- [x] ✅ Architecture documented
- [ ] ⬜ TmuxAgentManager implemented
- [ ] ⬜ StoryFileMonitor implemented
- [ ] ⬜ Basic orchestrator (SM only)
- [ ] ⬜ Single story processing working

### Phase 2: Full Pipeline (Planned)
- [ ] ⬜ PO validation
- [ ] ⬜ Dev implementation
- [ ] ⬜ QA testing
- [ ] ⬜ Complete SM → PO → Dev → QA flow

### Phase 3: Epic Processing (Planned)
- [ ] ⬜ Epic file loading
- [ ] ⬜ Checkpoint management
- [ ] ⬜ Resume capability
- [ ] ⬜ Multi-story processing

### Phase 4: Robustness (Planned)
- [ ] ⬜ Timeout handling
- [ ] ⬜ Session recovery
- [ ] ⬜ Human escalation
- [ ] ⬜ Comprehensive logging

### Phase 5: Advanced Features (Future)
- [ ] ⬜ Parallel story processing
- [ ] ⬜ MCP server integrations
- [ ] ⬜ Web UI monitoring
- [ ] ⬜ Metrics & analytics

**See**: [Implementation Roadmap](./docs/design/implementation-roadmap.md) for detailed plan

---

## 🔒 Safety Features

### VM Isolation
- Runs in dedicated Proxmox VM (recommended)
- Snapshot before every epic run
- Easy rollback on failure

### Context Safety
- Fresh tmux session per agent
- No context accumulation
- Respects 200k token limit

### BMad Compliance
- Agents load full architecture docs
- Checklists executed as designed
- Anti-hallucination verification works
- Story files created/updated properly

---

## 🎯 Usage Examples

### Process Single Story

```python
from src.orchestrator import BMadOrchestrator
from pathlib import Path

orchestrator = BMadOrchestrator(Path("~/projects/myproject"))
result = await orchestrator.process_story("1.1")

if result['success']:
    print(f"✓ Story complete: {result['story_file']}")
else:
    print(f"✗ Failed at {result['stage_reached']}: {result['error']}")
```

### Monitor Live Session

```bash
# List all BMad sessions
tmux ls | grep bmad-

# Attach to specific agent
tmux attach -t bmad-sm-1-1

# Watch story file changes
watch -n 2 'cat docs/stories/1.1.story.md | tail -20'
```

### Resume from Checkpoint

```python
# After failure or interruption
orchestrator = BMadOrchestrator(project_path)
result = await orchestrator.process_epic(
    epic_id="epic-1",
    resume=True  # Skips completed stories
)
```

---

## 🚨 Troubleshooting

### Claude Code Not Found

```bash
# Check installation
which claude
claude --version

# If not found, install from https://claude.ai/download
```

### Tmux Sessions Not Creating

```bash
# Check tmux
tmux -V

# Install if missing
sudo apt install tmux

# Test session creation
tmux new-session -d -s test-session
tmux ls
tmux kill-session -t test-session
```

### Story File Not Detected

```bash
# Check file exists
ls -lh ~/projects/your-project/docs/stories/

# Check file size (should be > 1KB)
du -h ~/projects/your-project/docs/stories/1.1.story.md

# View file content
cat ~/projects/your-project/docs/stories/1.1.story.md
```

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone and install
git clone https://github.com/jasonvanwyk/bmad-auto.git
cd bmad-auto
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Format code
black src/ tests/
ruff check src/ tests/
```

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

This project builds upon:

- **[BMad Method](https://github.com/bmad-code-org/BMAD-METHOD)** - The foundational framework
- **[LangGraph](https://github.com/langchain-ai/langgraph)** - State machine orchestration
- **[libtmux](https://github.com/tmux-python/libtmux)** - Tmux automation
- **[Watchdog](https://github.com/gorakhargosh/watchdog)** - File monitoring

---

## 📞 Support

- 🐛 **Issues**: [GitHub Issues](https://github.com/jasonvanwyk/bmad-auto/issues)
- 📖 **Documentation**: [docs/design/](./docs/design/)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/jasonvanwyk/bmad-auto/discussions)

---

**Status**: Design Complete ✅ | Implementation Phase 1 In Progress 🚧

*Built with ❤️ to automate the BMad Method workflow*
