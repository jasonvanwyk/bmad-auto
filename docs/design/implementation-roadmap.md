# BMad Automation Implementation Roadmap

## Executive Summary

We've completed comprehensive design for a **LangGraph-based orchestrator** that automates BMad agent workflows while maintaining full compliance with BMad's methodology.

### Key Design Documents

1. **LANGGRAPH_ORCHESTRATOR_DESIGN.md** - State machine architecture for agent coordination
2. **CLAUDE_CODE_INVOCATION_GUIDE.md** - How to spawn and control Claude Code instances
3. **TMUX_SESSION_MANAGEMENT_DESIGN.md** - Session isolation and context clearing
4. **FILE_BASED_COMMUNICATION_PROTOCOL.md** - Agent completion detection via file monitoring

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  LangGraph Orchestrator (Master Process)                    │
│  - State machine: SM → PO → Dev → QA                       │
│  - File monitoring for completion detection                 │
│  - Checkpoint management for resume capability              │
└────────────┬────────────────────────────────────────────────┘
             │
             │ spawns
             ↓
┌─────────────────────────────────────────────────────────────┐
│  Tmux Session Manager                                        │
│  - Creates isolated tmux sessions per agent                 │
│  - Injects commands: /sm *create, /po *validate, etc.      │
│  - Context cleared on session kill                          │
└────────────┬────────────────────────────────────────────────┘
             │
             │ runs in each session
             ↓
┌─────────────────────────────────────────────────────────────┐
│  Claude Code Instances (in tmux)                            │
│  - Loads BMad agents via slash commands                     │
│  - Executes tasks: *create, *validate, *develop-story, etc │
│  - Full context: architecture docs, checklists, PRD         │
│  - Updates story files in docs/stories/                     │
└────────────┬────────────────────────────────────────────────┘
             │
             │ writes to
             ↓
┌─────────────────────────────────────────────────────────────┐
│  File System (Communication Layer)                          │
│  - Story files: docs/stories/{epic}.{story}.story.md       │
│  - Checkpoint files: .bmad-checkpoint-{epic}.yaml          │
│  - Orchestrator monitors for changes                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Foundation (MVP) ✅ DESIGNED

**Goal**: Basic orchestrator that can process a single story

**Components**:
1. TmuxAgentManager - Spawn and manage tmux sessions
2. StoryFileMonitor - Detect file changes
3. Basic LangGraph state machine - SM → PO → Dev → QA
4. Simple file-based completion detection

**Deliverables**:
- `src/tmux_manager.py` - Tmux session management
- `src/file_monitor.py` - File monitoring and parsing
- `src/orchestrator.py` - Basic LangGraph workflow
- Test script that processes single story

**Success Criteria**:
- ✅ Can spawn tmux session with Claude Code
- ✅ Can send `/sm` and `*create` commands
- ✅ Can detect story file creation
- ✅ Can kill session (context cleared)

**Estimated Time**: 4-6 hours

---

### Phase 2: Full Agent Pipeline ⬜ NEXT

**Goal**: Complete SM → PO → Dev → QA workflow

**Components**:
1. PO validation detection
2. Dev implementation monitoring
3. QA test result detection
4. State transitions based on outcomes

**Deliverables**:
- Enhanced orchestrator with all 4 agent stages
- PO decision routing (APPROVED/BLOCKED)
- Dev file modification tracking
- QA pass/fail detection

**Success Criteria**:
- ✅ Story goes through all 4 stages automatically
- ✅ PO blocking stops progression
- ✅ Dev files are tracked
- ✅ QA results recorded
- ✅ Complete story file with all sections

**Estimated Time**: 6-8 hours

---

### Phase 3: Epic Processing ⬜ PENDING

**Goal**: Process entire epic with multiple stories

**Components**:
1. Epic file loading (stories.yaml)
2. Story iteration logic
3. Checkpoint management
4. Resume capability
5. Failure handling

**Deliverables**:
- `src/checkpoint_manager.py` - Checkpoint persistence
- Epic processing loop in orchestrator
- Resume from checkpoint capability
- Failure recovery logic

**Success Criteria**:
- ✅ Can process multiple stories sequentially
- ✅ Checkpoints saved after each story
- ✅ Can resume from last completed story
- ✅ Failed stories logged and skipped

**Estimated Time**: 4-6 hours

---

### Phase 4: Robustness & Error Handling ⬜ PENDING

**Goal**: Production-ready automation with comprehensive error handling

**Components**:
1. Timeout management per agent
2. Session recovery on crashes
3. Human escalation system
4. Detailed logging
5. Progress reporting

**Deliverables**:
- Timeout handling for each agent stage
- Session health checks
- Automatic retry logic (configurable)
- Human escalation triggers
- Rich console output with progress bars

**Success Criteria**:
- ✅ Handles agent timeouts gracefully
- ✅ Recovers from crashes
- ✅ Escalates unresolvable issues to human
- ✅ Clear logging for debugging
- ✅ Real-time progress visibility

**Estimated Time**: 6-8 hours

---

### Phase 5: Advanced Features ⬜ FUTURE

**Goal**: Enhanced capabilities for production use

**Components**:
1. Parallel story processing
2. MCP server integrations
3. Web UI for monitoring
4. Metrics and analytics
5. Configuration management

**Deliverables**:
- Parallel execution with resource limits
- MCP servers for git, files, processes
- Simple web UI to watch progress
- Performance metrics collection
- YAML-based configuration

**Success Criteria**:
- ✅ Can process 2-4 stories in parallel
- ✅ MCP servers provide enhanced capabilities
- ✅ Web UI shows real-time status
- ✅ Metrics tracked (time per stage, success rate, etc.)

**Estimated Time**: 12-16 hours

---

## Phase 1 Implementation Plan (MVP)

### Step 1: Project Setup (30 min)

```bash
cd ~/bmad-auto

# Create source structure
mkdir -p src tests

# Install dependencies
pip install langgraph libtmux watchdog pyyaml pytest

# Create requirements.txt
cat > requirements.txt << 'EOF'
langgraph>=0.1.0
libtmux>=0.21.0
watchdog>=3.0.0
pyyaml>=6.0
pytest>=7.4.0
EOF

# Initialize package
touch src/__init__.py
touch tests/__init__.py
```

### Step 2: Tmux Manager Implementation (2 hours)

**File**: `src/tmux_manager.py`

```python
"""
Tmux session management for BMad agents.
Based on: TMUX_SESSION_MANAGEMENT_DESIGN.md
"""
import libtmux
import time
from pathlib import Path
from typing import Optional, List
from datetime import datetime

class TmuxAgentManager:
    # ... implementation from design doc ...
    pass
```

**Test**: `tests/test_tmux_manager.py`

```python
"""
Test tmux manager functionality.
"""
import pytest
from pathlib import Path
from src.tmux_manager import TmuxAgentManager

def test_spawn_session():
    """Test session creation."""
    mgr = TmuxAgentManager(Path.cwd())
    session_id = mgr.spawn_agent_session(
        agent="sm",
        story_id="test-1",
        commands=None
    )
    assert session_id.startswith("bmad-sm")
    mgr.kill_session(session_id)

def test_send_commands():
    """Test command injection."""
    mgr = TmuxAgentManager(Path.cwd())
    session_id = mgr.spawn_agent_session("sm", "test-2")

    # Send test commands
    mgr.send_keys(session_id, "echo 'test'")
    time.sleep(1)

    # Capture output
    output = mgr.capture_pane_output(session_id)
    assert "test" in output

    mgr.kill_session(session_id)
```

### Step 3: File Monitor Implementation (2 hours)

**File**: `src/file_monitor.py`

```python
"""
File monitoring for agent completion detection.
Based on: FILE_BASED_COMMUNICATION_PROTOCOL.md
"""
import asyncio
from pathlib import Path
from typing import Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class StoryFileMonitor(FileSystemEventHandler):
    # ... implementation from design doc ...
    pass

async def wait_for_file_condition(
    file_path: Path,
    condition: Callable[[dict], bool],
    timeout: int = 600,
    check_interval: float = 2.0
) -> bool:
    # ... implementation from design doc ...
    pass
```

**Test**: `tests/test_file_monitor.py`

```python
"""
Test file monitoring functionality.
"""
import pytest
import asyncio
from pathlib import Path
from src.file_monitor import StoryFileMonitor, wait_for_file_condition

@pytest.mark.asyncio
async def test_wait_for_file_creation(tmp_path):
    """Test waiting for file creation."""
    test_file = tmp_path / "test.md"

    async def create_file_later():
        await asyncio.sleep(1)
        test_file.write_text("content")

    # Start creation task
    asyncio.create_task(create_file_later())

    # Wait for file
    success = await wait_for_file_condition(
        test_file,
        lambda s: s.get('exists', False),
        timeout=5
    )

    assert success
    assert test_file.exists()
```

### Step 4: Basic Orchestrator (2 hours)

**File**: `src/orchestrator.py`

```python
"""
LangGraph-based orchestrator for BMad agents.
Based on: LANGGRAPH_ORCHESTRATOR_DESIGN.md
"""
from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal
from pathlib import Path
import asyncio

from .tmux_manager import TmuxAgentManager
from .file_monitor import wait_for_file_condition

class StoryState(TypedDict):
    """State for processing a single story."""
    story_id: str
    current_stage: Literal["sm", "po", "dev", "qa", "complete", "failed"]
    story_file_path: str
    tmux_session_id: str
    po_decision: str
    dev_files_modified: list
    qa_test_results: str
    error_message: str

class BMadOrchestrator:
    """Orchestrates BMad agent workflow using LangGraph."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.tmux_mgr = TmuxAgentManager(project_path)
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """Build LangGraph state machine."""
        workflow = StateGraph(StoryState)

        # Add nodes
        workflow.add_node("spawn_sm", self._spawn_sm_agent)
        # Add more nodes in Phase 2

        # Set entry
        workflow.set_entry_point("spawn_sm")

        return workflow.compile()

    async def _spawn_sm_agent(self, state: StoryState) -> StoryState:
        """Spawn SM agent to create story."""
        print(f"→ SM: Creating story {state['story_id']}")

        # Spawn tmux session
        session_id = self.tmux_mgr.spawn_agent_session(
            agent="sm",
            story_id=state['story_id'],
            commands=["/sm", "*create"]
        )

        state['tmux_session_id'] = session_id
        state['current_stage'] = 'sm'

        # Wait for story file
        story_file = self.project_path / f"docs/stories/{state['story_id']}.story.md"

        success = await wait_for_file_condition(
            story_file,
            lambda s: s.get('exists') and s.get('size', 0) > 1000,
            timeout=600
        )

        if success:
            print(f"✓ Story file created: {story_file}")
            state['story_file_path'] = str(story_file)
            state['current_stage'] = 'complete'  # Only SM for Phase 1
        else:
            print("✗ SM failed")
            state['current_stage'] = 'failed'
            state['error_message'] = 'SM timeout'

        # Cleanup
        self.tmux_mgr.kill_session(session_id)

        return state

    async def process_story(self, story_id: str) -> dict:
        """Process single story through workflow."""
        initial_state = StoryState(
            story_id=story_id,
            current_stage="sm",
            story_file_path="",
            tmux_session_id="",
            po_decision="",
            dev_files_modified=[],
            qa_test_results="",
            error_message=""
        )

        final_state = await self.workflow.ainvoke(initial_state)

        return {
            'success': final_state['current_stage'] == 'complete',
            'stage_reached': final_state['current_stage'],
            'story_file': final_state.get('story_file_path'),
            'error': final_state.get('error_message')
        }
```

### Step 5: Test Script (1 hour)

**File**: `test_mvp.py`

```python
"""
Test MVP orchestrator with single story.
"""
import asyncio
from pathlib import Path
from src.orchestrator import BMadOrchestrator

async def main():
    project_path = Path("~/projects/precept-pos-bmad-auto").expanduser()

    if not project_path.exists():
        print(f"✗ Project not found: {project_path}")
        return

    print("BMad Orchestrator MVP Test")
    print("="*60)
    print(f"Project: {project_path}")
    print()

    orchestrator = BMadOrchestrator(project_path)

    # Test with story 1.1
    story_id = "1.1"

    print(f"Processing story {story_id}...")
    print()

    result = await orchestrator.process_story(story_id)

    print()
    print("="*60)
    print("Result:")
    print(f"  Success: {result['success']}")
    print(f"  Stage reached: {result['stage_reached']}")
    print(f"  Story file: {result['story_file']}")
    if result['error']:
        print(f"  Error: {result['error']}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Testing Strategy

### Unit Tests

```bash
# Test tmux manager
pytest tests/test_tmux_manager.py -v

# Test file monitor
pytest tests/test_file_monitor.py -v

# Run all tests
pytest tests/ -v
```

### Integration Test

```bash
# Test with real BMad project
python test_mvp.py
```

### Manual Verification

```bash
# Watch tmux session in real-time
tmux ls
tmux attach -t bmad-sm-1-1

# Inspect story file
cat ~/projects/precept-pos-bmad-auto/docs/stories/1.1.story.md
```

---

## Phase 1 Success Criteria

- [x] ✅ Design completed for all components
- [ ] ⬜ TmuxAgentManager implemented and tested
- [ ] ⬜ StoryFileMonitor implemented and tested
- [ ] ⬜ Basic orchestrator processes single story
- [ ] ⬜ SM agent creates story file successfully
- [ ] ⬜ Context clearing verified (session killed)
- [ ] ⬜ File-based detection works reliably

---

## Next Steps

### Immediate (Today)

1. ✅ Complete design phase - **DONE**
2. ⬜ Set up project structure
3. ⬜ Implement TmuxAgentManager
4. ⬜ Implement StoryFileMonitor
5. ⬜ Test individual components

### Short Term (This Week)

1. ⬜ Implement basic orchestrator
2. ⬜ Test with single story (SM only)
3. ⬜ Add PO, Dev, QA stages
4. ⬜ Test complete workflow

### Medium Term (Next Week)

1. ⬜ Add epic processing
2. ⬜ Implement checkpoints
3. ⬜ Add error handling
4. ⬜ Test with Epic 1

### Long Term (Future)

1. ⬜ Parallel processing
2. ⬜ MCP servers
3. ⬜ Web UI
4. ⬜ Production deployment

---

## Dependencies

### Python Packages

```txt
langgraph>=0.1.0       # State machine orchestration
libtmux>=0.21.0        # Tmux session management
watchdog>=3.0.0        # File system monitoring
pyyaml>=6.0            # YAML parsing
pytest>=7.4.0          # Testing framework
asyncio                # Async operations (built-in)
```

### System Requirements

- Python 3.10+
- tmux installed (`sudo apt install tmux`)
- Claude Code CLI installed (`claude --version`)
- BMad project configured (`.bmad-core/` present)

### Environment

- Proxmox VM: ID 500, Ubuntu 24.04.2
- Static IP: 192.168.85.155
- Virtual environment: `~/bmad-env`
- Automation repo: `~/bmad-auto`
- Test project: `~/projects/precept-pos-bmad-auto`

---

## Risk Mitigation

### Risk 1: Claude Code CLI Limitations

**Risk**: Slash commands may not work as expected via CLI

**Mitigation**:
- Test early with simple commands
- Have fallback to stdin piping
- Consider MCP server integration

### Risk 2: File Monitoring Reliability

**Risk**: File changes might not be detected promptly

**Mitigation**:
- Polling fallback if watchdog fails
- Configurable check intervals
- Timeout mechanisms

### Risk 3: Context Window Exceeded

**Risk**: Agents might exceed 200k token limit

**Mitigation**:
- Fresh session per agent (context cleared)
- Monitor token usage (if API available)
- Timeout agents running too long

### Risk 4: Session Crashes

**Risk**: Tmux sessions or Claude instances crash

**Mitigation**:
- Session health checks
- Automatic retry logic
- Human escalation system
- Checkpoint/resume capability

---

## Monitoring and Observability

### Logs

```
logs/
├── orchestrator.log         # Main orchestrator log
├── tmux-sessions.log        # Tmux session lifecycle
├── file-monitor.log         # File change events
└── agents/
    ├── sm-1.1.log          # SM agent output
    ├── po-1.1.log          # PO agent output
    └── ...
```

### Real-Time Monitoring

```bash
# Watch orchestrator progress
tail -f logs/orchestrator.log

# Attach to live session
tmux attach -t bmad-sm-1-1

# Monitor file changes
watch -n 2 'ls -lh ~/projects/precept-pos-bmad-auto/docs/stories/'
```

### Progress Dashboard (Phase 5)

- Web UI showing epic progress
- Story pipeline visualization
- Agent status indicators
- Failure alerts

---

## Documentation Structure

```
bmad-auto/
├── README.md                                  # Project overview
├── IMPLEMENTATION_ROADMAP.md                  # This file
├── LANGGRAPH_ORCHESTRATOR_DESIGN.md          # Architecture
├── CLAUDE_CODE_INVOCATION_GUIDE.md           # CLI usage
├── TMUX_SESSION_MANAGEMENT_DESIGN.md         # Session management
├── FILE_BASED_COMMUNICATION_PROTOCOL.md      # File monitoring
├── BMAD_COMPLIANT_DESIGN.md                  # Original BMad analysis
├── AUTOMATION_REALITY_CHECK.md               # Design iterations
├── EPIC1_EXECUTION_PLAN.md                   # Original plan
├── src/
│   ├── __init__.py
│   ├── orchestrator.py                        # Main orchestrator
│   ├── tmux_manager.py                        # Tmux management
│   ├── file_monitor.py                        # File monitoring
│   └── checkpoint_manager.py                  # Checkpoints (Phase 3)
├── tests/
│   ├── __init__.py
│   ├── test_tmux_manager.py
│   ├── test_file_monitor.py
│   └── test_orchestrator.py
└── test_mvp.py                                # MVP integration test
```

---

## Conclusion

We have completed comprehensive design for a production-ready BMad automation system that:

- ✅ **Respects BMad's design** - Uses agents as intended with full context
- ✅ **Fully automated** - LangGraph orchestrates entire workflow
- ✅ **Context safe** - Fresh tmux sessions prevent context bloat
- ✅ **Debuggable** - File-based communication is inspectable
- ✅ **Resilient** - Checkpoints, timeouts, error handling
- ✅ **Scalable** - Can process epics with many stories

**The architecture is sound. Time to build it!**

---

## Ready to Implement

All design work is complete. Phase 1 implementation can begin immediately with clear specifications, test strategy, and success criteria.

**Estimated time to working MVP: 6-8 hours of focused development.**

Let's build this! 🚀
