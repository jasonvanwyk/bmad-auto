# Claude Code CLI Invocation Guide

## Discovery: BMad Agents Are Slash Commands

After researching the Claude Code CLI and examining the BMad project structure, I've discovered how BMad agents work:

**BMad agents are Claude Code slash commands** stored in `.claude/commands/BMad/agents/`

### BMad Project Structure
```
project/
├── .claude/
│   └── commands/
│       └── BMad/
│           ├── agents/
│           │   ├── sm.md      # /sm command
│           │   ├── po.md      # /po command
│           │   ├── dev.md     # /dev command
│           │   └── qa.md      # /qa command
│           └── tasks/
│               ├── create-next-story.md    # *create task
│               ├── validate-next-story.md  # *validate task
│               ├── develop-story.md        # *develop-story task
│               └── test-story.md           # *test task
└── .bmad-core/
    ├── core-config.yaml
    ├── agents/          # Referenced by slash commands
    ├── tasks/           # Referenced by slash commands
    └── checklists/      # Loaded by agents as needed
```

### How BMad Agents Work in Interactive Mode

**Normal Claude Code Usage:**
```bash
$ claude
> /sm           # Loads SM agent persona
> *create       # Executes create-next-story task
> exit
```

**Agent Activation Process:**
1. User types `/sm` → Claude loads `.claude/commands/BMad/agents/sm.md`
2. SM persona activates, loads `.bmad-core/core-config.yaml`
3. User types `*create` → SM loads `.bmad-core/tasks/create-next-story.md`
4. SM executes task, loading architecture docs, epic files, creates story

---

## Claude Code CLI Capabilities

```bash
claude --version
# 2.0.37 (Claude Code)
```

### Key CLI Options for Automation

```bash
# Interactive Mode (default)
claude                                    # Start interactive session
claude --continue                         # Continue last conversation
claude --resume [sessionId]              # Resume specific session

# Print Mode (non-interactive)
claude --print "your prompt"             # Print response and exit
claude --print --output-format json      # JSON output
claude --print --output-format stream-json  # Streaming JSON

# Session Management
claude --session-id <uuid>               # Use specific session ID
claude --fork-session --resume <id>      # Fork existing session

# System Prompts
claude --system-prompt "prompt"          # Replace system prompt
claude --append-system-prompt "prompt"   # Append to system prompt

# Settings
claude --settings <file-or-json>         # Load settings
claude --setting-sources user,project    # Specify setting sources

# Tools and Permissions
claude --tools "Bash,Edit,Read"          # Specify available tools
claude --permission-mode bypassPermissions  # Bypass permissions (sandbox only)
claude --dangerously-skip-permissions    # Skip all permission checks

# Input/Output Formats
claude --input-format stream-json        # Streaming input
claude --output-format stream-json       # Streaming output
claude --replay-user-messages            # Echo user messages back
```

---

## Strategy for Invoking BMad Agents

### Option 1: Interactive Mode with Tmux (RECOMMENDED)

**Pros:**
- ✅ Slash commands work natively
- ✅ Can monitor session in real-time
- ✅ Full agent activation with all features
- ✅ Context and session state maintained

**Cons:**
- ❌ Need to parse tmux pane output to detect completion
- ❌ More complex session management

**Implementation:**
```python
import libtmux
from pathlib import Path

class ClaudeCodeTmuxManager:
    """Spawn Claude Code sessions in tmux for BMad agent execution."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.server = libtmux.Server()

    def spawn_sm_agent(self, story_id: str) -> str:
        """
        Spawn SM agent session to create story.

        Returns:
            session_name: Tmux session identifier
        """
        session_name = f"bmad-sm-{story_id}"

        # Create tmux session
        session = self.server.new_session(
            session_name=session_name,
            start_directory=str(self.project_path),
            window_name=f"sm-{story_id}"
        )

        window = session.attached_window
        pane = window.attached_pane

        # Start Claude Code in interactive mode
        pane.send_keys(f"cd {self.project_path}")
        pane.send_keys("claude")

        # Wait for Claude to be ready (poll for prompt)
        time.sleep(3)

        # Send slash command to activate SM agent
        pane.send_keys("/sm")

        # Wait for activation (SM greets and shows *help)
        time.sleep(5)

        # Send task command
        pane.send_keys("*create")

        return session_name

    def monitor_pane_output(self, session_name: str) -> str:
        """Capture output from tmux pane."""
        session = self.server.find_where({"session_name": session_name})
        if not session:
            return ""

        window = session.attached_window
        pane = window.attached_pane

        # Capture pane content (last N lines)
        return "\n".join(pane.cmd('capture-pane', '-p').stdout)

    def detect_story_file_created(self, session_name: str, story_id: str) -> bool:
        """
        Check if story file exists (SM completed).

        This is more reliable than parsing output.
        """
        story_file = self.project_path / f"docs/stories/{story_id}.story.md"
        return story_file.exists() and story_file.stat().st_size > 1000

    def kill_session(self, session_name: str):
        """Clean up tmux session."""
        session = self.server.find_where({"session_name": session_name})
        if session:
            session.kill_session()
```

**Usage:**
```python
manager = ClaudeCodeTmuxManager(Path("~/projects/precept-pos-bmad-auto"))

# Spawn SM agent
session_id = manager.spawn_sm_agent(story_id="1.1")

# Wait for story file creation (file-based detection)
while not manager.detect_story_file_created(session_id, "1.1"):
    time.sleep(5)

print("✓ SM created story file")
manager.kill_session(session_id)
```

---

### Option 2: Print Mode with Slash Command String (EXPERIMENTAL)

**Test if slash commands work in --print mode:**

```bash
cd ~/projects/precept-pos-bmad-auto
claude --print "/sm *create" --output-format json
```

**Pros:**
- ✅ Simpler execution model
- ✅ Direct capture of output
- ✅ No tmux complexity

**Cons:**
- ❌ May not support slash commands in print mode
- ❌ Less context/state management
- ❌ Agent activation might not work fully

**Implementation (if it works):**
```python
import subprocess
import json

def invoke_sm_agent_print_mode(project_path: Path, story_id: str) -> dict:
    """
    Invoke SM agent using --print mode.

    WARNING: Experimental - slash commands may not work in print mode.
    """
    cmd = [
        "claude",
        "--print",
        "/sm *create",  # Slash command + task
        "--output-format", "json",
        "--settings", json.dumps({
            "workingDirectory": str(project_path)
        })
    ]

    result = subprocess.run(
        cmd,
        cwd=project_path,
        capture_output=True,
        text=True,
        timeout=600
    )

    if result.returncode == 0:
        return json.loads(result.stdout)
    else:
        raise RuntimeError(f"SM agent failed: {result.stderr}")
```

---

### Option 3: Session-Based Invocation with Resume (HYBRID)

**Create a session, send commands, resume to check completion:**

```python
import subprocess
import uuid
from pathlib import Path

class ClaudeCodeSessionManager:
    """Manage Claude Code sessions via CLI."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.sessions = {}

    def create_session(self, agent: str, story_id: str) -> str:
        """
        Create new Claude session for agent.

        Returns:
            session_id: UUID of session
        """
        session_id = str(uuid.uuid4())

        # Start interactive session with specific ID
        # Note: This requires piping commands somehow
        # May need to use --input-format stream-json

        self.sessions[session_id] = {
            'agent': agent,
            'story_id': story_id,
            'started_at': time.time()
        }

        return session_id

    def send_command_to_session(self, session_id: str, command: str):
        """
        Send command to existing session.

        This is complex - may need MCP server or stdin pipe.
        """
        # This is where it gets tricky
        # Claude Code doesn't have built-in command sending to running sessions
        # Would need:
        # 1. MCP server that can control sessions
        # 2. Or tmux wrapping (Option 1)
        # 3. Or file-based communication
        pass
```

---

## Recommended Approach: Tmux + File Monitoring

After analyzing the options, **Option 1 (Tmux + Interactive Mode)** is most viable because:

1. **Slash commands work natively** - `/sm`, `/po`, `/dev`, `/qa` activate properly
2. **Full agent features** - All BMad workflows, checklists, file loading work
3. **Session isolation** - Each tmux session is independent (context clearing!)
4. **File-based completion detection** - More reliable than parsing output

### Architecture

```python
# Orchestrator spawns agent in tmux
session_id = tmux_mgr.spawn_agent(
    agent="sm",
    story_id="1.1",
    commands=["/sm", "*create"]
)

# Monitor file system instead of parsing output
story_file = project_path / f"docs/stories/1.1.story.md"

# Poll until file exists and has content
while not (story_file.exists() and story_file.stat().st_size > 1000):
    await asyncio.sleep(5)

print("✓ SM completed - story file created")

# Parse story file for metadata
with open(story_file) as f:
    content = f.read()
    # Extract status, PO decision, etc.

# Kill tmux session (context cleared)
tmux_mgr.kill_session(session_id)
```

---

## Enhanced Tmux Manager with Command Sequencing

```python
class EnhancedTmuxManager:
    """
    Enhanced tmux manager that can send multiple commands sequentially.
    """

    def spawn_agent_with_commands(
        self,
        agent: str,
        story_id: str,
        commands: list[str],
        wait_between: float = 3.0
    ) -> str:
        """
        Spawn agent and send multiple commands.

        Args:
            agent: BMad agent (sm, po, dev, qa)
            story_id: Story identifier
            commands: List of commands to send (e.g., ["/sm", "*create"])
            wait_between: Seconds to wait between commands

        Returns:
            session_name
        """
        session_name = f"bmad-{agent}-{story_id}"

        session = self.server.new_session(
            session_name=session_name,
            start_directory=str(self.project_path),
            window_name=f"{agent}-{story_id}"
        )

        window = session.attached_window
        pane = window.attached_pane

        # Start Claude Code
        pane.send_keys(f"cd {self.project_path}")
        pane.send_keys("claude")

        # Wait for Claude to initialize
        time.sleep(5)

        # Send commands sequentially
        for cmd in commands:
            pane.send_keys(cmd)
            time.sleep(wait_between)

        return session_name

    def attach_to_session(self, session_name: str):
        """
        Attach to session for manual inspection.

        Usage:
            # In another terminal:
            tmux attach -t bmad-sm-1.1
        """
        print(f"To attach: tmux attach -t {session_name}")
```

---

## File-Based Completion Detection

**More reliable than parsing tmux output:**

```python
async def wait_for_story_file(
    story_file: Path,
    timeout: int = 600,
    check_interval: int = 5
) -> bool:
    """
    Wait for story file to be created and have substantial content.

    Args:
        story_file: Path to expected story file
        timeout: Max seconds to wait
        check_interval: Seconds between checks

    Returns:
        True if file created, False if timeout
    """
    start_time = time.time()

    while (time.time() - start_time) < timeout:
        if story_file.exists():
            size = story_file.stat().st_size
            if size > 1000:  # Substantial content
                # Additional check: has required sections
                content = story_file.read_text()
                if "## Acceptance Criteria" in content and "## Tasks" in content:
                    return True

        await asyncio.sleep(check_interval)

    return False


async def wait_for_po_decision(
    story_file: Path,
    timeout: int = 300
) -> str:
    """
    Wait for PO to update story file with decision.

    Returns:
        "APPROVED", "BLOCKED", or "CHANGES"
    """
    start_time = time.time()

    while (time.time() - start_time) < timeout:
        if story_file.exists():
            content = story_file.read_text()

            # Look for PO Decision section
            if "## PO Decision" in content:
                if "APPROVED" in content:
                    return "APPROVED"
                elif "BLOCKED" in content:
                    return "BLOCKED"
                elif "CHANGES" in content:
                    return "CHANGES"

        await asyncio.sleep(5)

    return "TIMEOUT"
```

---

## MCP Server for Enhanced Control (Future)

**Potential MCP server capabilities:**

```python
# Future: MCP server for Claude Code control
class ClaudeCodeMCPServer:
    """
    MCP server that provides control over Claude Code sessions.

    Capabilities:
    - spawn_session(agent, commands)
    - send_command(session_id, command)
    - get_session_status(session_id)
    - kill_session(session_id)
    """

    async def spawn_session(self, agent: str, commands: list[str]) -> str:
        """Spawn Claude Code session with commands."""
        # Implementation would integrate with Claude Code internals
        pass

    async def monitor_session(self, session_id: str) -> dict:
        """Get session status and output."""
        pass
```

---

## Complete Workflow Example

```python
async def process_story_with_bmad(story_id: str, project_path: Path):
    """
    Process single story through BMad agents using tmux + file monitoring.
    """
    tmux_mgr = EnhancedTmuxManager(project_path)
    story_file = project_path / f"docs/stories/{story_id}.story.md"

    print(f"\n{'='*60}")
    print(f"Story {story_id}")
    print(f"{'='*60}\n")

    # Stage 1: SM creates story
    print("→ SM: Creating story...")
    sm_session = tmux_mgr.spawn_agent_with_commands(
        agent="sm",
        story_id=story_id,
        commands=["/sm", "*create"]
    )

    # Wait for story file
    success = await wait_for_story_file(story_file, timeout=600)
    if not success:
        print("✗ SM failed to create story file")
        tmux_mgr.kill_session(sm_session)
        return

    print(f"✓ Story file created: {story_file}")
    tmux_mgr.kill_session(sm_session)

    # Stage 2: PO validates story
    print("→ PO: Validating story...")
    po_session = tmux_mgr.spawn_agent_with_commands(
        agent="po",
        story_id=story_id,
        commands=["/po", f"*validate {story_file}"]
    )

    # Wait for PO decision
    decision = await wait_for_po_decision(story_file, timeout=300)
    print(f"✓ PO Decision: {decision}")
    tmux_mgr.kill_session(po_session)

    if decision != "APPROVED":
        print(f"⊘ Story blocked by PO, skipping Dev/QA")
        return

    # Stage 3: Dev implements
    print("→ Dev: Implementing story...")
    dev_session = tmux_mgr.spawn_agent_with_commands(
        agent="dev",
        story_id=story_id,
        commands=["/dev", f"*develop-story {story_file}"]
    )

    # Wait for dev to mark ready
    success = await wait_for_status_change(story_file, "Ready for Review", timeout=1800)
    if success:
        print("✓ Dev completed implementation")
    else:
        print("✗ Dev failed or timed out")

    tmux_mgr.kill_session(dev_session)

    # Stage 4: QA tests
    print("→ QA: Testing implementation...")
    qa_session = tmux_mgr.spawn_agent_with_commands(
        agent="qa",
        story_id=story_id,
        commands=["/qa", f"*test {story_file}"]
    )

    # Wait for QA results
    success = await wait_for_test_results(story_file, timeout=900)
    if success:
        print("✓ QA: All tests passed")
    else:
        print("✗ QA: Tests failed")

    tmux_mgr.kill_session(qa_session)

    print(f"\n✓ Story {story_id} complete!\n")
```

---

## Key Insights

1. **BMad agents = Claude Code slash commands** stored in `.claude/commands/BMad/agents/`
2. **Tmux + interactive mode** is the most reliable invocation method
3. **File-based detection** is more reliable than parsing output
4. **Context clearing** happens automatically (new tmux session = fresh Claude instance)
5. **Full BMad compliance** achieved (agents load all their files/checklists/tasks)

---

## Next Steps

1. ✅ Research Claude Code CLI - **COMPLETE**
2. ✅ Understand BMad slash command structure - **COMPLETE**
3. ⬜ Implement EnhancedTmuxManager prototype
4. ⬜ Test with single story (SM only)
5. ⬜ Add PO, Dev, QA stages
6. ⬜ Integrate with LangGraph orchestrator
7. ⬜ Build file monitoring system
8. ⬜ Test full epic processing

**The architecture is now clear and implementable!**
