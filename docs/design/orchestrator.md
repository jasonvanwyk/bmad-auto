# LangGraph Orchestrator Architecture

## Vision: True BMad Automation

**Orchestrate BMad agents WITHOUT bypassing their design.**

### The Approach
```
LangGraph Orchestrator (Master Agent)
    ↓ spawns
tmux session → Claude Code instance → @sm *create
    ↓ writes
docs/stories/1.1.story.md
    ↓ orchestrator detects file
LangGraph transitions to next state
    ↓ spawns
tmux session → Claude Code instance → @po *validate
    ↓ updates
docs/stories/1.1.story.md (status: approved)
    ↓ orchestrator detects approval
LangGraph transitions
    ↓ spawns
tmux session → Claude Code instance → @dev *develop-story
    ↓ creates files, updates story
docs/git-workflow.md, story status: ready-for-review
    ↓ orchestrator detects completion
LangGraph transitions
    ↓ spawns
tmux session → Claude Code instance → @qa *test
    ↓ tests, updates story
story status: done, all tests passed
    ↓ orchestrator detects success
Story complete! → Next story
```

---

## Architecture Components

### 1. LangGraph State Machine (Orchestrator)

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal

class StoryState(TypedDict):
    """State for processing a single story."""
    epic_id: str
    story_id: str
    story_num: int
    current_stage: Literal["sm", "po", "dev", "qa", "complete", "failed"]
    story_file_path: str
    tmux_session_id: str
    po_decision: str
    dev_files_modified: list[str]
    qa_test_results: str
    retry_count: int
    error_message: str

# Define the graph
workflow = StateGraph(StoryState)

# Add nodes (each spawns Claude Code in tmux)
workflow.add_node("spawn_sm", spawn_sm_agent)
workflow.add_node("spawn_po", spawn_po_agent)
workflow.add_node("spawn_dev", spawn_dev_agent)
workflow.add_node("spawn_qa", spawn_qa_agent)
workflow.add_node("handle_failure", handle_failure)

# Add edges (state transitions)
workflow.add_edge("spawn_sm", "spawn_po")
workflow.add_conditional_edges(
    "spawn_po",
    route_po_decision,
    {
        "approved": "spawn_dev",
        "blocked": "handle_failure",
        "changes": "handle_failure"
    }
)
workflow.add_edge("spawn_dev", "spawn_qa")
workflow.add_conditional_edges(
    "spawn_qa",
    route_qa_results,
    {
        "passed": END,
        "failed": "handle_failure"
    }
)

# Set entry point
workflow.set_entry_point("spawn_sm")

# Compile
app = workflow.compile()
```

---

### 2. Tmux Session Management

```python
import libtmux
from pathlib import Path

class TmuxAgentManager:
    """
    Manages tmux sessions for isolated agent execution.
    Each agent runs in its own tmux session.
    """

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.server = libtmux.Server()
        self.sessions = {}

    def spawn_agent_session(
        self,
        agent: str,  # "sm", "po", "dev", "qa"
        story_id: str,
        command: str
    ) -> str:
        """
        Spawn Claude Code session for BMad agent.

        Args:
            agent: BMad agent type (sm/po/dev/qa)
            story_id: Story identifier (e.g., "1.1")
            command: BMad command to execute (e.g., "@sm *create")

        Returns:
            session_id: Tmux session identifier
        """
        session_name = f"bmad-{agent}-{story_id}"

        # Kill existing session if any
        if session_name in [s.name for s in self.server.sessions]:
            self.server.kill_session(session_name)

        # Create new session
        session = self.server.new_session(
            session_name=session_name,
            start_directory=str(self.project_path),
            window_name=f"{agent}-{story_id}"
        )

        # Get the window
        window = session.attached_window
        pane = window.attached_pane

        # CRITICAL: Clear context instruction
        context_clear_command = (
            "# IMPORTANT: Starting fresh context\n"
            "# Previous conversations are not relevant\n"
            f"# Agent: {agent}, Story: {story_id}\n"
        )

        # Start Claude Code in the tmux pane
        # Assuming `claude` CLI can be invoked headlessly
        pane.send_keys(f"cd {self.project_path}")
        pane.send_keys(context_clear_command)

        # Invoke Claude Code with BMad agent command
        # This might vary depending on how Claude Code CLI works
        # Option 1: Direct command (if supported)
        pane.send_keys(f"claude code --command '{command}'")

        # Option 2: Interactive mode with auto-send
        # pane.send_keys("claude code")
        # pane.send_keys(command)

        self.sessions[session_name] = {
            'session': session,
            'agent': agent,
            'story_id': story_id,
            'started_at': datetime.now()
        }

        return session_name

    def monitor_session_output(self, session_id: str) -> str:
        """
        Capture output from tmux session.
        Used to detect completion/errors.
        """
        if session_id not in self.sessions:
            return ""

        session = self.sessions[session_id]['session']
        window = session.attached_window
        pane = window.attached_pane

        # Capture pane content
        return pane.capture_pane()

    def kill_session(self, session_id: str):
        """Clean up tmux session."""
        if session_id in self.sessions:
            session = self.sessions[session_id]['session']
            self.server.kill_session(session.name)
            del self.sessions[session_id]
```

---

### 3. File Monitoring System

```python
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import yaml

class StoryFileMonitor(FileSystemEventHandler):
    """
    Monitors story files for changes.
    Orchestrator uses this to detect agent completion.
    """

    def __init__(self, story_file_path: Path, callback):
        self.story_file_path = story_file_path
        self.callback = callback
        self.last_modified = None

    def on_modified(self, event):
        """Called when story file is modified."""
        if event.src_path == str(self.story_file_path):
            # Read the file
            content = self.story_file_path.read_text()

            # Parse for status
            status = self.extract_status(content)

            # Notify orchestrator
            self.callback(status, content)

    def extract_status(self, content: str) -> dict:
        """
        Extract status information from story file.

        Story file format (Markdown with metadata):
        ---
        status: Draft | Ready for Review | Done
        ---

        Or look for specific sections:
        ## Status
        Ready for Review

        ## PO Decision
        APPROVED
        """
        # Parse YAML frontmatter if present
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 2:
                try:
                    metadata = yaml.safe_load(parts[1])
                    return metadata
                except:
                    pass

        # Fall back to section parsing
        status = {
            'status': None,
            'po_decision': None,
            'dev_files': [],
            'qa_results': None
        }

        lines = content.split('\n')
        current_section = None

        for line in lines:
            if line.startswith('## Status'):
                current_section = 'status'
            elif line.startswith('## PO Decision'):
                current_section = 'po_decision'
            elif line.startswith('## File List'):
                current_section = 'file_list'
            elif line.startswith('## Testing'):
                current_section = 'testing'
            elif current_section and line.strip():
                if current_section == 'status':
                    status['status'] = line.strip()
                elif current_section == 'po_decision':
                    if 'APPROVED' in line:
                        status['po_decision'] = 'APPROVED'
                    elif 'BLOCKED' in line:
                        status['po_decision'] = 'BLOCKED'
                elif current_section == 'file_list' and line.startswith('- '):
                    status['dev_files'].append(line[2:].strip())

        return status

async def wait_for_file_condition(
    file_path: Path,
    condition_check,
    timeout: int = 600
) -> bool:
    """
    Wait for file to meet a condition.

    Args:
        file_path: Path to monitor
        condition_check: Function(file_content) -> bool
        timeout: Max seconds to wait

    Returns:
        True if condition met, False if timeout
    """
    start_time = asyncio.get_event_loop().time()

    while (asyncio.get_event_loop().time() - start_time) < timeout:
        if file_path.exists():
            content = file_path.read_text()
            if condition_check(content):
                return True

        await asyncio.sleep(2)  # Check every 2 seconds

    return False
```

---

### 4. Agent Spawning Functions (LangGraph Nodes)

```python
async def spawn_sm_agent(state: StoryState) -> StoryState:
    """
    Spawn SM agent in tmux to create story file.

    SM will:
    - Load core-config.yaml
    - Load architecture docs
    - Load epic files
    - Create docs/stories/{epic}.{story}.story.md
    """
    print(f"→ SM: Creating story {state['story_id']}")

    tmux_mgr = TmuxAgentManager(project_path)

    # Spawn tmux session with SM agent
    session_id = tmux_mgr.spawn_agent_session(
        agent="sm",
        story_id=state['story_id'],
        command="@sm *create"
    )

    state['tmux_session_id'] = session_id
    state['current_stage'] = 'sm'

    # Wait for story file to be created
    story_file = project_path / f"docs/stories/{state['story_id']}.story.md"

    print(f"  Waiting for story file: {story_file}")

    success = await wait_for_file_condition(
        story_file,
        lambda content: len(content) > 1000,  # Substantial content
        timeout=600  # 10 minutes max
    )

    if success:
        print(f"  ✓ Story file created: {story_file}")
        state['story_file_path'] = str(story_file)
    else:
        print(f"  ✗ SM timed out or failed")
        state['current_stage'] = 'failed'
        state['error_message'] = 'SM failed to create story file'

    # Cleanup tmux session
    tmux_mgr.kill_session(session_id)

    return state


async def spawn_po_agent(state: StoryState) -> StoryState:
    """
    Spawn PO agent to validate story file.

    PO will:
    - Load core-config.yaml
    - Load story file
    - Load po-master-checklist.md
    - Validate against PRD/architecture
    - Update story file with decision
    """
    print(f"→ PO: Validating story {state['story_id']}")

    tmux_mgr = TmuxAgentManager(project_path)
    story_file = Path(state['story_file_path'])

    # Spawn tmux session with PO agent
    session_id = tmux_mgr.spawn_agent_session(
        agent="po",
        story_id=state['story_id'],
        command=f"@po *validate --story-file {story_file}"
    )

    state['tmux_session_id'] = session_id
    state['current_stage'] = 'po'

    # Wait for PO decision in story file
    print(f"  Waiting for PO decision...")

    def check_po_decision(content: str) -> bool:
        """Check if PO made a decision."""
        return any(word in content for word in ['APPROVED', 'BLOCKED', 'CHANGES'])

    success = await wait_for_file_condition(
        story_file,
        check_po_decision,
        timeout=300  # 5 minutes
    )

    if success:
        # Parse decision
        content = story_file.read_text()
        monitor = StoryFileMonitor(story_file, None)
        status = monitor.extract_status(content)

        decision = status.get('po_decision', 'UNKNOWN')
        print(f"  ✓ PO Decision: {decision}")

        state['po_decision'] = decision
    else:
        print(f"  ✗ PO timed out or failed")
        state['current_stage'] = 'failed'
        state['error_message'] = 'PO failed to validate story'

    # Cleanup tmux session
    tmux_mgr.kill_session(session_id)

    return state


async def spawn_dev_agent(state: StoryState) -> StoryState:
    """
    Spawn Dev agent to implement story.

    Dev will:
    - Load core-config.yaml
    - Load devLoadAlwaysFiles
    - Load story file
    - Implement tasks
    - Update story file with File List
    """
    print(f"→ Dev: Implementing story {state['story_id']}")

    tmux_mgr = TmuxAgentManager(project_path)
    story_file = Path(state['story_file_path'])

    # Spawn tmux session with Dev agent
    session_id = tmux_mgr.spawn_agent_session(
        agent="dev",
        story_id=state['story_id'],
        command=f"@dev *develop-story --story-file {story_file}"
    )

    state['tmux_session_id'] = session_id
    state['current_stage'] = 'dev'

    # Wait for Dev to mark story as ready
    print(f"  Waiting for implementation...")

    def check_dev_complete(content: str) -> bool:
        """Check if Dev marked story ready."""
        return 'Ready for Review' in content or 'status: Ready' in content

    success = await wait_for_file_condition(
        story_file,
        check_dev_complete,
        timeout=1800  # 30 minutes max
    )

    if success:
        # Parse modified files
        content = story_file.read_text()
        monitor = StoryFileMonitor(story_file, None)
        status = monitor.extract_status(content)

        files = status.get('dev_files', [])
        print(f"  ✓ Dev completed, modified {len(files)} files")

        state['dev_files_modified'] = files
    else:
        print(f"  ✗ Dev timed out or failed")
        state['current_stage'] = 'failed'
        state['error_message'] = 'Dev failed to implement story'

    # Cleanup tmux session
    tmux_mgr.kill_session(session_id)

    return state


async def spawn_qa_agent(state: StoryState) -> StoryState:
    """
    Spawn QA agent to test implementation.

    QA will:
    - Load core-config.yaml
    - Load story file
    - Test against acceptance criteria
    - Update story file with results
    """
    print(f"→ QA: Testing story {state['story_id']}")

    tmux_mgr = TmuxAgentManager(project_path)
    story_file = Path(state['story_file_path'])

    # Spawn tmux session with QA agent
    session_id = tmux_mgr.spawn_agent_session(
        agent="qa",
        story_id=state['story_id'],
        command=f"@qa *test --story-file {story_file}"
    )

    state['tmux_session_id'] = session_id
    state['current_stage'] = 'qa'

    # Wait for QA results
    print(f"  Waiting for test results...")

    def check_qa_complete(content: str) -> bool:
        """Check if QA completed tests."""
        return ('PASS' in content or 'FAIL' in content) and 'status: Done' in content

    success = await wait_for_file_condition(
        story_file,
        check_qa_complete,
        timeout=900  # 15 minutes max
    )

    if success:
        content = story_file.read_text()

        if 'PASS' in content:
            print(f"  ✓ QA: All tests passed")
            state['qa_test_results'] = 'PASSED'
            state['current_stage'] = 'complete'
        else:
            print(f"  ✗ QA: Tests failed")
            state['qa_test_results'] = 'FAILED'
            state['current_stage'] = 'failed'
    else:
        print(f"  ✗ QA timed out or failed")
        state['current_stage'] = 'failed'
        state['error_message'] = 'QA failed to test story'

    # Cleanup tmux session
    tmux_mgr.kill_session(session_id)

    return state
```

---

### 5. Routing Functions (State Transitions)

```python
def route_po_decision(state: StoryState) -> str:
    """Route based on PO decision."""
    decision = state.get('po_decision', '').upper()

    if decision == 'APPROVED':
        return "approved"
    elif decision == 'BLOCKED':
        return "blocked"
    else:
        return "changes"


def route_qa_results(state: StoryState) -> str:
    """Route based on QA results."""
    results = state.get('qa_test_results', '').upper()

    if results == 'PASSED':
        return "passed"
    else:
        return "failed"


async def handle_failure(state: StoryState) -> StoryState:
    """
    Handle story failure.
    Log the failure, potentially escalate to human.
    """
    print(f"✗ Story {state['story_id']} failed at stage {state['current_stage']}")
    print(f"  Error: {state.get('error_message', 'Unknown error')}")

    # Log to file
    failure_log = project_path / f".bmad-failures-{state['epic_id']}.log"
    with open(failure_log, 'a') as f:
        f.write(f"\n--- Story {state['story_id']} ---\n")
        f.write(f"Stage: {state['current_stage']}\n")
        f.write(f"Error: {state.get('error_message')}\n")
        f.write(f"PO Decision: {state.get('po_decision')}\n")
        f.write(f"QA Results: {state.get('qa_test_results')}\n")

    # Could escalate to human here
    # Or implement retry logic

    return state
```

---

### 6. MCP Server Integrations

```python
# MCP servers provide specialized capabilities

# File Monitoring MCP
mcp_file_monitor = MCPServer(
    name="file-monitor",
    capabilities=["watch", "notify", "parse"]
)

# Git Operations MCP
mcp_git = MCPServer(
    name="git-operations",
    capabilities=["commit", "branch", "diff", "status"]
)

# Process Management MCP
mcp_process = MCPServer(
    name="process-manager",
    capabilities=["spawn", "kill", "monitor"]
)

# Integration example:
async def spawn_agent_with_mcp(agent: str, story_id: str):
    """Spawn agent using MCP process manager."""
    result = await mcp_process.call(
        "spawn_claude_code",
        {
            "agent": agent,
            "command": f"@{agent} *create",
            "working_dir": str(project_path)
        }
    )
    return result['process_id']
```

---

### 7. Epic Processing Loop

```python
async def process_epic(epic_id: str, project_path: Path):
    """
    Process entire epic using LangGraph orchestrator.

    Each story goes through: SM → PO → Dev → QA
    Context cleared between stories (new tmux sessions).
    """
    # Load epic stories
    epic_file = project_path / f"docs/epics/{epic_id}/stories.yaml"
    with open(epic_file) as f:
        epic_data = yaml.safe_load(f)

    stories = epic_data['stories']

    print(f"\n{'='*60}")
    print(f"Epic {epic_id}: {epic_data['title']}")
    print(f"Stories: {len(stories)}")
    print(f"{'='*60}\n")

    results = []

    for story_num, story_info in enumerate(stories, start=1):
        story_id = story_info['id']

        # Skip completed stories
        if story_info.get('status') == 'completed':
            print(f"⊘ Story {story_id}: Already completed, skipping")
            continue

        print(f"\n{'─'*60}")
        print(f"Story {story_num}/{len(stories)}: {story_id}")
        print(f"Title: {story_info['title']}")
        print(f"{'─'*60}\n")

        # Initialize state
        initial_state = StoryState(
            epic_id=epic_id,
            story_id=story_id,
            story_num=story_num,
            current_stage="sm",
            story_file_path="",
            tmux_session_id="",
            po_decision="",
            dev_files_modified=[],
            qa_test_results="",
            retry_count=0,
            error_message=""
        )

        # Run through LangGraph workflow
        final_state = await app.ainvoke(initial_state)

        # Record result
        results.append({
            'story_id': story_id,
            'success': final_state['current_stage'] == 'complete',
            'stage_reached': final_state['current_stage'],
            'po_decision': final_state.get('po_decision'),
            'files_modified': final_state.get('dev_files_modified', []),
            'qa_results': final_state.get('qa_test_results')
        })

        if final_state['current_stage'] == 'complete':
            print(f"\n✓ Story {story_id} completed successfully!")
        else:
            print(f"\n✗ Story {story_id} failed at {final_state['current_stage']}")

        # Brief pause between stories
        await asyncio.sleep(2)

    # Print epic summary
    print(f"\n\n{'='*60}")
    print(f"Epic {epic_id} Summary")
    print(f"{'='*60}")

    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    print(f"✓ Completed: {len(successful)}/{len(results)}")
    print(f"✗ Failed: {len(failed)}/{len(results)}")

    if failed:
        print(f"\nFailed stories:")
        for r in failed:
            print(f"  - {r['story_id']}: Failed at {r['stage_reached']}")

    return results
```

---

## Key Advantages

### 1. BMad-Compliant
✅ Each agent spawned properly (@sm, @po, @dev, @qa)
✅ Agents load their full configurations
✅ Architecture docs loaded (50-100k tokens!)
✅ Checklists executed (PO master checklist)
✅ Tasks followed exactly
✅ Anti-hallucination verification works

### 2. Fully Automated
✅ LangGraph orchestrates the entire flow
✅ File monitoring triggers transitions
✅ No manual intervention needed
✅ Handles failures gracefully

### 3. Context Clearing
✅ Each tmux session is isolated
✅ Fresh Claude Code instance per agent
✅ No context accumulation
✅ Each agent starts with clean state

### 4. Visibility & Debugging
✅ Tmux sessions can be attached to watch real-time
✅ File-based communication is debuggable
✅ Story files show complete audit trail
✅ Can pause/resume/inspect at any point

### 5. VM Safety
✅ Runs in isolated Proxmox VM
✅ Snapshots before/after epic
✅ Rollback capability
✅ Safe testing environment

---

## Implementation Phases

### Phase 1: Basic Orchestrator (MVP)
- [ ] LangGraph state machine
- [ ] Tmux session spawning
- [ ] File monitoring
- [ ] SM → PO → Dev → QA flow
- [ ] Single story processing

### Phase 2: Claude Code Integration
- [ ] Figure out Claude Code CLI invocation
- [ ] Auto-send @ mentions to sessions
- [ ] Capture output properly
- [ ] Handle interactive prompts

### Phase 3: Robustness
- [ ] Failure handling
- [ ] Retry logic
- [ ] Timeout management
- [ ] Human escalation

### Phase 4: MCP Servers
- [ ] File monitoring MCP
- [ ] Git operations MCP
- [ ] Process management MCP
- [ ] Enhanced capabilities

---

## Next Steps

1. Research Claude Code CLI capabilities
2. Test tmux + Claude Code integration
3. Build basic LangGraph orchestrator
4. Test with single story
5. Expand to full epic

This architecture gives you:
- **Full BMad compliance** (agents work as designed)
- **Full automation** (orchestrator handles flow)
- **Full quality** (architecture docs, checklists, tasks)
- **Full visibility** (tmux monitoring)
- **Full safety** (VM isolation, context clearing)

Perfect alignment with your original vision!
