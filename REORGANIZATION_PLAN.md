# Repository Reorganization Plan

## New Structure

```
bmad-auto/
├── README.md                          # ✅ Updated project overview
├── requirements.txt                   # ✅ Updated dependencies
├── .gitignore                         # ✅ Updated
│
├── docs/
│   ├── design/                        # 🎯 ACTIVE DESIGN DOCUMENTS
│   │   ├── README.md                  # Design overview
│   │   ├── architecture.md            # System architecture
│   │   ├── orchestrator.md            # LangGraph orchestrator
│   │   ├── tmux-sessions.md           # Session management
│   │   ├── file-communication.md      # File monitoring protocol
│   │   ├── claude-code-cli.md         # CLI invocation guide
│   │   └── implementation-roadmap.md  # Implementation phases
│   │
│   └── archive/                       # 📦 LEARNING JOURNEY & OBSOLETE
│       ├── learning-journey/          # Documents from design process
│       │   ├── bmad-auto-original.md
│       │   ├── reality-check.md
│       │   ├── bmad-compliant-design.md
│       │   ├── epic1-execution-plan.md
│       │   ├── context-management.md
│       │   ├── conversation-summary.md
│       │   └── setup-checklist.md
│       │
│       └── obsolete-code/             # Old implementation attempts
│           ├── mvp_story_automation.py
│           ├── context_manager.py
│           ├── hitl_interface.py
│           └── safety_wrapper.py
│
├── src/                               # 🚀 NEW IMPLEMENTATION
│   ├── __init__.py
│   ├── orchestrator.py                # LangGraph orchestrator (NEW)
│   ├── tmux_manager.py                # Tmux session management (NEW)
│   ├── file_monitor.py                # File monitoring & parsing (NEW)
│   └── checkpoint_manager.py          # Checkpoint persistence (Phase 3)
│
├── tests/                             # ✅ TEST SUITE
│   ├── __init__.py
│   ├── test_tmux_manager.py
│   ├── test_file_monitor.py
│   └── test_orchestrator.py
│
├── scripts/                           # 🔧 UTILITY SCRIPTS
│   ├── test_mvp.py                    # MVP integration test
│   ├── snapshot_manager.sh            # VM snapshot management
│   ├── provision_bmad_vm.sh           # VM provisioning
│   └── create_bmad_test_vm.sh         # VM creation
│
└── configs/                           # ⚙️ CONFIGURATION
    └── default.yaml                   # Default orchestrator config
```

## Rationale

### Active Documents (docs/design/)
- **Current architecture** - What we're building now
- **Implementation ready** - These are the specs for coding
- **Version controlled** - Part of the project

### Archive (docs/archive/)
- **Learning journey** - Shows our design evolution
- **Historical context** - Explains why we made certain decisions
- **Not deleted** - Valuable for understanding the thought process

### Clean src/
- **Fresh start** - Remove old implementation
- **Design-driven** - Build from specs in docs/design/
- **Testable** - Unit tests for each module

### Focused Configuration
- **Single config file** - No scattered YAML files
- **Environment-based** - Can override per environment
