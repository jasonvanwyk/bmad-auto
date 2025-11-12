# Tmux Session Management for BMad Automation

## Overview

Tmux provides **session isolation** for BMad agents, ensuring:
- ✅ **Context clearing** - Each agent runs in fresh session
- ✅ **Parallel execution** - Multiple stories can run simultaneously
- ✅ **Live monitoring** - Attach to sessions to watch real-time
- ✅ **Process isolation** - Clean separation between agent invocations

---

## Architecture

### Session Hierarchy

```
tmux server
├── bmad-orchestrator (main control session)
├── bmad-sm-1.1 (SM working on story 1.1)
├── bmad-po-1.1 (PO validating story 1.1)
├── bmad-dev-1.1 (Dev implementing story 1.1)
├── bmad-qa-1.1 (QA testing story 1.1)
├── bmux-sm-1.2 (SM working on story 1.2)
└── ... (more stories)
```

**Each session:**
- Runs in project directory
- Has single window
- Contains one pane with Claude Code instance
- Is named `bmad-{agent}-{story_id}`

---

## TmuxAgentManager Implementation

```python
import libtmux
import time
import asyncio
from pathlib import Path
from typing import Optional, List
from datetime import datetime

class TmuxAgentManager:
    """
    Manages tmux sessions for isolated BMad agent execution.

    Features:
    - Session creation and cleanup
    - Command injection
    - Output monitoring
    - Session lifecycle management
    """

    def __init__(self, project_path: Path):
        """
        Initialize tmux manager.

        Args:
            project_path: Absolute path to BMad project
        """
        self.project_path = project_path.resolve()
        self.server = libtmux.Server()
        self.sessions = {}  # session_name -> metadata

    def spawn_agent_session(
        self,
        agent: str,
        story_id: str,
        commands: Optional[List[str]] = None,
        wait_for_ready: float = 5.0
    ) -> str:
        """
        Spawn new tmux session with Claude Code running BMad agent.

        Args:
            agent: BMad agent type (sm, po, dev, qa)
            story_id: Story identifier (e.g., "1.1")
            commands: Optional list of commands to send after activation
            wait_for_ready: Seconds to wait for Claude to initialize

        Returns:
            session_name: Tmux session identifier

        Example:
            session_id = mgr.spawn_agent_session(
                agent="sm",
                story_id="1.1",
                commands=["/sm", "*create"]
            )
        """
        session_name = f"bmad-{agent}-{story_id.replace('.', '-')}"

        # Kill existing session if present
        self._kill_session_by_name(session_name)

        # Create new session
        session = self.server.new_session(
            session_name=session_name,
            start_directory=str(self.project_path),
            window_name=f"{agent}-{story_id}",
            attach=False  # Don't attach (run in background)
        )

        # Get pane
        window = session.attached_window
        pane = window.attached_pane

        # Change to project directory (ensure we're in right place)
        pane.send_keys(f"cd {self.project_path}")
        time.sleep(0.5)

        # Start Claude Code in interactive mode
        pane.send_keys("claude")
        time.sleep(wait_for_ready)

        # Send commands if provided
        if commands:
            for cmd in commands:
                pane.send_keys(cmd)
                time.sleep(2)  # Wait between commands

        # Record session metadata
        self.sessions[session_name] = {
            'agent': agent,
            'story_id': story_id,
            'started_at': datetime.now(),
            'session_obj': session
        }

        return session_name

    def send_keys(self, session_name: str, keys: str, wait: float = 1.0):
        """
        Send keys to session pane.

        Args:
            session_name: Session identifier
            keys: Text to send
            wait: Seconds to wait after sending
        """
        if session_name not in self.sessions:
            raise ValueError(f"Session {session_name} not found")

        session = self.sessions[session_name]['session_obj']
        pane = session.attached_window.attached_pane
        pane.send_keys(keys)
        time.sleep(wait)

    def capture_pane_output(
        self,
        session_name: str,
        start_line: int = 0,
        end_line: Optional[int] = None
    ) -> str:
        """
        Capture output from session pane.

        Args:
            session_name: Session identifier
            start_line: Start line (0 = beginning of scrollback)
            end_line: End line (None = current line)

        Returns:
            Captured output as string
        """
        if session_name not in self.sessions:
            raise ValueError(f"Session {session_name} not found")

        session = self.sessions[session_name]['session_obj']
        pane = session.attached_window.attached_pane

        # Capture pane content
        if end_line:
            output = pane.cmd('capture-pane', '-p', '-S', str(start_line), '-E', str(end_line))
        else:
            output = pane.cmd('capture-pane', '-p', '-S', str(start_line))

        return output.stdout[0] if output.stdout else ""

    def get_session_info(self, session_name: str) -> dict:
        """Get metadata about session."""
        if session_name not in self.sessions:
            raise ValueError(f"Session {session_name} not found")

        meta = self.sessions[session_name]
        return {
            'agent': meta['agent'],
            'story_id': meta['story_id'],
            'started_at': meta['started_at'],
            'running_time': (datetime.now() - meta['started_at']).total_seconds(),
            'session_exists': self._session_exists(session_name)
        }

    def kill_session(self, session_name: str):
        """
        Kill tmux session and cleanup metadata.

        Args:
            session_name: Session identifier
        """
        if session_name in self.sessions:
            try:
                session = self.sessions[session_name]['session_obj']
                session.kill_session()
            except Exception as e:
                # Session might already be dead
                pass

            del self.sessions[session_name]

    def list_sessions(self) -> List[str]:
        """List all active BMad sessions."""
        return list(self.sessions.keys())

    def kill_all_sessions(self):
        """Kill all managed sessions (cleanup)."""
        for session_name in list(self.sessions.keys()):
            self.kill_session(session_name)

    def attach_instructions(self, session_name: str) -> str:
        """
        Get command to manually attach to session.

        Returns:
            tmux attach command
        """
        return f"tmux attach -t {session_name}"

    # Private methods

    def _kill_session_by_name(self, session_name: str):
        """Kill session by name (if exists)."""
        try:
            session = self.server.find_where({"session_name": session_name})
            if session:
                session.kill_session()
        except:
            pass

    def _session_exists(self, session_name: str) -> bool:
        """Check if session exists in tmux server."""
        return self.server.has_session(session_name)


# Async wrapper for awaitable operations
class AsyncTmuxAgentManager(TmuxAgentManager):
    """
    Async version of TmuxAgentManager for use with asyncio.
    """

    async def spawn_agent_session_async(
        self,
        agent: str,
        story_id: str,
        commands: Optional[List[str]] = None,
        wait_for_ready: float = 5.0
    ) -> str:
        """Async version of spawn_agent_session."""
        session_name = await asyncio.to_thread(
            self.spawn_agent_session,
            agent, story_id, commands, wait_for_ready
        )
        return session_name

    async def send_keys_async(self, session_name: str, keys: str, wait: float = 1.0):
        """Async version of send_keys."""
        await asyncio.to_thread(self.send_keys, session_name, keys, wait)

    async def capture_pane_output_async(
        self,
        session_name: str,
        start_line: int = 0,
        end_line: Optional[int] = None
    ) -> str:
        """Async version of capture_pane_output."""
        return await asyncio.to_thread(
            self.capture_pane_output,
            session_name, start_line, end_line
        )

    async def kill_session_async(self, session_name: str):
        """Async version of kill_session."""
        await asyncio.to_thread(self.kill_session, session_name)
```

---

## Session Lifecycle

### 1. Session Creation

```python
tmux_mgr = TmuxAgentManager(Path("~/projects/precept-pos-bmad-auto"))

# Create SM session
session_id = tmux_mgr.spawn_agent_session(
    agent="sm",
    story_id="1.1",
    commands=["/sm", "*create"],
    wait_for_ready=5.0
)

# Session is now running in background
print(f"Session created: {session_id}")
print(f"To watch: {tmux_mgr.attach_instructions(session_id)}")
```

### 2. Session Monitoring

```python
# Get session info
info = tmux_mgr.get_session_info(session_id)
print(f"Agent: {info['agent']}")
print(f"Story: {info['story_id']}")
print(f"Running time: {info['running_time']}s")

# Capture recent output
output = tmux_mgr.capture_pane_output(session_id, start_line=-50)
print(output)
```

### 3. Session Cleanup

```python
# Kill specific session
tmux_mgr.kill_session(session_id)

# Or kill all sessions (end of epic)
tmux_mgr.kill_all_sessions()
```

---

## Advanced Features

### Parallel Story Processing

```python
async def process_multiple_stories_parallel(story_ids: List[str]):
    """
    Process multiple stories in parallel using separate tmux sessions.
    """
    tmux_mgr = AsyncTmuxAgentManager(project_path)

    # Spawn all SM sessions
    tasks = []
    for story_id in story_ids:
        task = asyncio.create_task(
            process_single_story(tmux_mgr, story_id)
        )
        tasks.append(task)

    # Wait for all to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return results


async def process_single_story(
    tmux_mgr: AsyncTmuxAgentManager,
    story_id: str
):
    """Process single story through all stages."""
    # SM stage
    sm_session = await tmux_mgr.spawn_agent_session_async(
        agent="sm",
        story_id=story_id,
        commands=["/sm", "*create"]
    )

    # Wait for completion (file-based)
    story_file = project_path / f"docs/stories/{story_id}.story.md"
    await wait_for_file(story_file)

    await tmux_mgr.kill_session_async(sm_session)

    # Continue with PO, Dev, QA...
```

### Session Recovery

```python
class SessionRecoveryManager:
    """
    Handles session crashes and recovery.
    """

    def __init__(self, tmux_mgr: TmuxAgentManager):
        self.tmux_mgr = tmux_mgr
        self.recovery_log = []

    def check_session_health(self, session_name: str) -> bool:
        """
        Check if session is still alive and responsive.

        Returns:
            True if healthy, False if dead/unresponsive
        """
        try:
            info = self.tmux_mgr.get_session_info(session_name)
            return info['session_exists']
        except:
            return False

    async def recover_session(
        self,
        session_name: str,
        agent: str,
        story_id: str,
        commands: List[str]
    ):
        """
        Attempt to recover crashed session.

        Strategy:
        1. Kill dead session
        2. Create new session with same parameters
        3. Log recovery attempt
        """
        print(f"⚠️  Session {session_name} crashed, attempting recovery...")

        # Kill dead session
        self.tmux_mgr.kill_session(session_name)

        # Spawn new session
        new_session = self.tmux_mgr.spawn_agent_session(
            agent=agent,
            story_id=story_id,
            commands=commands
        )

        self.recovery_log.append({
            'original_session': session_name,
            'new_session': new_session,
            'timestamp': datetime.now(),
            'agent': agent,
            'story_id': story_id
        })

        return new_session
```

### Live Output Streaming

```python
async def stream_session_output(
    tmux_mgr: TmuxAgentManager,
    session_name: str,
    callback
):
    """
    Stream session output in real-time.

    Args:
        tmux_mgr: Tmux manager
        session_name: Session to monitor
        callback: Function to call with new output lines
    """
    last_line_count = 0

    while True:
        output = tmux_mgr.capture_pane_output(session_name)
        lines = output.split('\n')

        # Get new lines since last check
        new_lines = lines[last_line_count:]
        last_line_count = len(lines)

        # Process new lines
        for line in new_lines:
            await callback(line)

        await asyncio.sleep(1)
```

---

## Integration with Orchestrator

### LangGraph Node Implementation

```python
from langgraph.graph import StateGraph

async def spawn_sm_node(state: StoryState) -> StoryState:
    """
    LangGraph node that spawns SM agent in tmux.
    """
    tmux_mgr = AsyncTmuxAgentManager(project_path)

    print(f"→ SM: Creating story {state['story_id']}")

    # Spawn tmux session
    session_id = await tmux_mgr.spawn_agent_session_async(
        agent="sm",
        story_id=state['story_id'],
        commands=["/sm", "*create"]
    )

    state['tmux_session_id'] = session_id
    state['current_stage'] = 'sm'

    # Wait for story file (file-based detection)
    story_file = project_path / f"docs/stories/{state['story_id']}.story.md"

    success = await wait_for_file(
        story_file,
        condition=lambda c: len(c) > 1000,
        timeout=600
    )

    if success:
        print(f"✓ Story file created")
        state['story_file_path'] = str(story_file)
    else:
        print(f"✗ SM timed out")
        state['current_stage'] = 'failed'
        state['error_message'] = 'SM failed to create story'

    # Cleanup session
    await tmux_mgr.kill_session_async(session_id)

    return state
```

---

## Testing and Debugging

### Manual Session Inspection

```bash
# List all tmux sessions
tmux ls

# Attach to specific session to watch
tmux attach -t bmad-sm-1-1

# Detach from session (keep it running)
# Press: Ctrl+b, then d

# Kill specific session
tmux kill-session -t bmad-sm-1-1
```

### Debug Mode

```python
class DebugTmuxAgentManager(TmuxAgentManager):
    """
    Debug version that logs all operations.
    """

    def __init__(self, project_path: Path, log_file: Path):
        super().__init__(project_path)
        self.log_file = log_file

    def spawn_agent_session(self, agent: str, story_id: str, commands=None, wait_for_ready=5.0):
        """Spawn with logging."""
        self._log(f"SPAWN: agent={agent}, story={story_id}, commands={commands}")

        session_name = super().spawn_agent_session(agent, story_id, commands, wait_for_ready)

        self._log(f"SPAWNED: session={session_name}")
        return session_name

    def kill_session(self, session_name: str):
        """Kill with logging."""
        self._log(f"KILL: session={session_name}")
        super().kill_session(session_name)

    def _log(self, message: str):
        """Write to log file."""
        timestamp = datetime.now().isoformat()
        with open(self.log_file, 'a') as f:
            f.write(f"[{timestamp}] {message}\n")
```

---

## Best Practices

### 1. Session Naming Convention

```python
# Format: bmad-{agent}-{story_id}
"bmad-sm-1-1"      # SM working on story 1.1
"bmad-po-1-2"      # PO validating story 1.2
"bmad-dev-2-3"     # Dev implementing story 2.3
```

### 2. Context Clearing

```python
# Each session is independent
# No shared state between sessions
# Context automatically cleared when session killed

# Pattern:
session = tmux_mgr.spawn_agent_session(...)
# ... do work ...
tmux_mgr.kill_session(session)  # ← Context cleared
```

### 3. Timeout Management

```python
# Set reasonable timeouts per stage
TIMEOUTS = {
    'sm': 600,    # 10 minutes
    'po': 300,    # 5 minutes
    'dev': 1800,  # 30 minutes
    'qa': 900     # 15 minutes
}

# Monitor session runtime
info = tmux_mgr.get_session_info(session_id)
if info['running_time'] > TIMEOUTS[info['agent']]:
    print(f"⚠️  Timeout exceeded, killing session")
    tmux_mgr.kill_session(session_id)
```

### 4. Error Handling

```python
try:
    session_id = tmux_mgr.spawn_agent_session(agent="sm", story_id="1.1")
    # ... wait for completion ...
except Exception as e:
    print(f"✗ Session failed: {e}")
finally:
    # Always cleanup
    tmux_mgr.kill_session(session_id)
```

---

## Performance Considerations

### Memory Usage

- Each tmux session: ~50MB
- Each Claude Code instance: ~500MB-1GB
- **Max parallel sessions**: 4-8 (depending on VM resources)

### CPU Usage

- Claude Code is CPU-intensive during code generation
- Recommend: 1-2 parallel stories max on 4-core VM
- Monitor with `htop` while running

### Session Cleanup

```python
# Periodic cleanup of orphaned sessions
def cleanup_orphaned_sessions(tmux_mgr: TmuxAgentManager):
    """
    Find and kill sessions older than threshold.
    """
    MAX_AGE_SECONDS = 3600  # 1 hour

    for session_name in tmux_mgr.list_sessions():
        info = tmux_mgr.get_session_info(session_name)
        if info['running_time'] > MAX_AGE_SECONDS:
            print(f"⚠️  Cleaning up old session: {session_name}")
            tmux_mgr.kill_session(session_name)
```

---

## Next Steps

1. ✅ Design tmux session management - **COMPLETE**
2. ⬜ Implement TmuxAgentManager prototype
3. ⬜ Test session creation and command injection
4. ⬜ Test with single BMad agent (SM)
5. ⬜ Integrate with file monitoring system
6. ⬜ Add to LangGraph orchestrator

**Tmux architecture is now fully designed!**
