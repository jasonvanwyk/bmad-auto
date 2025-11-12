"""
Tmux session management for BMad agent isolation.

This module provides the TmuxAgentManager class for spawning and managing
isolated tmux sessions where Claude Code instances run BMad agents.

Based on: docs/design/tmux-sessions.md
"""

import libtmux
import time
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime


class TmuxAgentManager:
    """
    Manages tmux sessions for isolated BMad agent execution.

    Each agent runs in its own tmux session, ensuring:
    - Context isolation (fresh Claude Code instance)
    - Process separation
    - Live monitoring capability
    - Clean session lifecycle

    Example:
        >>> mgr = TmuxAgentManager(Path("~/projects/myproject"))
        >>> session_id = mgr.spawn_agent_session(
        ...     agent="sm",
        ...     story_id="1.1",
        ...     commands=["/sm", "*create"]
        ... )
        >>> # Wait for agent to complete...
        >>> mgr.kill_session(session_id)
    """

    def __init__(self, project_path: Path):
        """
        Initialize tmux manager.

        Args:
            project_path: Absolute path to BMad project directory
        """
        self.project_path = project_path.resolve()
        self.server = libtmux.Server()
        self.sessions: Dict[str, dict] = {}  # session_name -> metadata

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
            commands: Optional list of commands to send after Claude starts
            wait_for_ready: Seconds to wait for Claude to initialize

        Returns:
            session_name: Tmux session identifier

        Example:
            >>> session_id = mgr.spawn_agent_session(
            ...     agent="sm",
            ...     story_id="1.1",
            ...     commands=["/sm", "*create"]
            ... )
        """
        # Create session name: bmad-sm-1-1 (replace . with -)
        session_name = f"bmad-{agent}-{story_id.replace('.', '-')}"

        # Kill existing session if present
        self._kill_session_by_name(session_name)

        # Create new tmux session
        session = self.server.new_session(
            session_name=session_name,
            start_directory=str(self.project_path),
            window_name=f"{agent}-{story_id}",
            attach=False  # Don't attach (run in background)
        )

        # Get pane
        window = session.active_window
        pane = window.active_pane

        # Change to project directory (ensure correct location)
        pane.send_keys(f"cd {self.project_path}")
        time.sleep(0.5)

        # Start Claude Code in interactive mode
        print(f"  Starting Claude Code in session {session_name}...")
        pane.send_keys("claude")
        time.sleep(wait_for_ready)

        # Send commands if provided
        if commands:
            for i, cmd in enumerate(commands):
                print(f"  Sending command: {cmd}")
                pane.send_keys(cmd)
                # Wait longer after agent activation command
                wait_time = 3.0 if i == 0 else 2.0
                time.sleep(wait_time)

        # Record session metadata
        self.sessions[session_name] = {
            'agent': agent,
            'story_id': story_id,
            'started_at': datetime.now(),
            'session_obj': session,
            'commands_sent': commands or []
        }

        print(f"  ✓ Session spawned: {session_name}")
        print(f"    To monitor: tmux attach -t {session_name}")

        return session_name

    def send_keys(self, session_name: str, keys: str, wait: float = 1.0):
        """
        Send keys to session pane.

        Args:
            session_name: Session identifier
            keys: Text to send (will be sent as keystrokes)
            wait: Seconds to wait after sending

        Raises:
            ValueError: If session not found
        """
        if session_name not in self.sessions:
            raise ValueError(f"Session {session_name} not found")

        session = self.sessions[session_name]['session_obj']
        pane = session.active_window.active_pane
        pane.send_keys(keys)
        time.sleep(wait)

    def capture_pane_output(
        self,
        session_name: str,
        start_line: int = -50,
        end_line: Optional[int] = None
    ) -> str:
        """
        Capture output from session pane.

        Args:
            session_name: Session identifier
            start_line: Start line (negative = from end, 0 = beginning)
            end_line: End line (None = current line)

        Returns:
            Captured output as string

        Raises:
            ValueError: If session not found
        """
        if session_name not in self.sessions:
            raise ValueError(f"Session {session_name} not found")

        session = self.sessions[session_name]['session_obj']
        pane = session.active_window.active_pane

        # Capture pane content
        try:
            if end_line:
                output = pane.cmd('capture-pane', '-p', '-S', str(start_line), '-E', str(end_line))
            else:
                output = pane.cmd('capture-pane', '-p', '-S', str(start_line))

            return output.stdout[0] if output.stdout else ""
        except Exception as e:
            print(f"Warning: Failed to capture pane output: {e}")
            return ""

    def get_session_info(self, session_name: str) -> dict:
        """
        Get metadata about session.

        Args:
            session_name: Session identifier

        Returns:
            Dictionary with session metadata

        Raises:
            ValueError: If session not found
        """
        if session_name not in self.sessions:
            raise ValueError(f"Session {session_name} not found")

        meta = self.sessions[session_name]
        running_time = (datetime.now() - meta['started_at']).total_seconds()

        return {
            'agent': meta['agent'],
            'story_id': meta['story_id'],
            'started_at': meta['started_at'],
            'running_time': running_time,
            'commands_sent': meta['commands_sent'],
            'session_exists': self._session_exists(session_name)
        }

    def kill_session(self, session_name: str):
        """
        Kill tmux session and cleanup metadata.

        This clears the context for the agent by terminating the
        Claude Code instance and destroying the tmux session.

        Args:
            session_name: Session identifier
        """
        if session_name in self.sessions:
            try:
                session = self.sessions[session_name]['session_obj']
                session.kill()
                print(f"  ✓ Session killed: {session_name}")
            except Exception as e:
                print(f"  Warning: Error killing session {session_name}: {e}")
            finally:
                # Always remove from tracking
                del self.sessions[session_name]

    def list_sessions(self) -> List[str]:
        """
        List all active BMad sessions managed by this instance.

        Returns:
            List of session names
        """
        return list(self.sessions.keys())

    def kill_all_sessions(self):
        """
        Kill all managed sessions (cleanup).

        Useful for cleanup after epic processing or on error.
        """
        session_names = list(self.sessions.keys())
        for session_name in session_names:
            self.kill_session(session_name)
        print(f"  ✓ All sessions killed ({len(session_names)} sessions)")

    def attach_instructions(self, session_name: str) -> str:
        """
        Get command to manually attach to session.

        Args:
            session_name: Session identifier

        Returns:
            tmux attach command string
        """
        return f"tmux attach -t {session_name}"

    # Private methods

    def _kill_session_by_name(self, session_name: str):
        """Kill session by name (if exists)."""
        try:
            # Get all sessions and find by name
            for session in self.server.sessions:
                if session.name == session_name:
                    session.kill()
                    break
        except Exception:
            pass  # Session doesn't exist or already dead

    def _session_exists(self, session_name: str) -> bool:
        """Check if session exists in tmux server."""
        return self.server.has_session(session_name)


class AsyncTmuxAgentManager(TmuxAgentManager):
    """
    Async version of TmuxAgentManager for use with asyncio.

    All methods that involve I/O or delays are wrapped to run in
    a thread pool, making them awaitable.

    Example:
        >>> import asyncio
        >>> mgr = AsyncTmuxAgentManager(Path("~/projects/myproject"))
        >>> session_id = await mgr.spawn_agent_session_async(
        ...     agent="sm",
        ...     story_id="1.1",
        ...     commands=["/sm", "*create"]
        ... )
    """

    async def spawn_agent_session_async(
        self,
        agent: str,
        story_id: str,
        commands: Optional[List[str]] = None,
        wait_for_ready: float = 5.0
    ) -> str:
        """Async version of spawn_agent_session."""
        import asyncio
        return await asyncio.to_thread(
            self.spawn_agent_session,
            agent, story_id, commands, wait_for_ready
        )

    async def send_keys_async(self, session_name: str, keys: str, wait: float = 1.0):
        """Async version of send_keys."""
        import asyncio
        await asyncio.to_thread(self.send_keys, session_name, keys, wait)

    async def capture_pane_output_async(
        self,
        session_name: str,
        start_line: int = -50,
        end_line: Optional[int] = None
    ) -> str:
        """Async version of capture_pane_output."""
        import asyncio
        return await asyncio.to_thread(
            self.capture_pane_output,
            session_name, start_line, end_line
        )

    async def kill_session_async(self, session_name: str):
        """Async version of kill_session."""
        import asyncio
        await asyncio.to_thread(self.kill_session, session_name)

    async def kill_all_sessions_async(self):
        """Async version of kill_all_sessions."""
        import asyncio
        await asyncio.to_thread(self.kill_all_sessions)
