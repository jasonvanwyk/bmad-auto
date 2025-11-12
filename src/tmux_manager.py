#!/usr/bin/env python3
"""
tmux_manager.py - Tmux session management for BMad automation

Provides session creation, window management, pane control, and monitoring
for parallel agent execution with full visibility.
"""

import libtmux
import subprocess
import json
import time
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum


class TmuxLayoutType(Enum):
    """Available tmux layout types"""
    TILED = "tiled"
    EVEN_HORIZONTAL = "even-horizontal"
    EVEN_VERTICAL = "even-vertical"
    MAIN_HORIZONTAL = "main-horizontal"
    MAIN_VERTICAL = "main-vertical"


class BmadTmuxManager:
    """Manages tmux sessions for BMad epic automation"""

    def __init__(self, epic_id: str, config: Dict = None):
        """Initialize tmux manager

        Args:
            epic_id: Epic identifier
            config: Optional configuration dictionary
        """
        self.epic_id = epic_id
        self.session_name = f"bmad-epic-{epic_id}"
        self.config = config or self._default_config()

        self.server = libtmux.Server()
        self.session = None
        self.windows = {}
        self.panes = {}
        self.creation_time = None

    def _default_config(self) -> Dict:
        """Get default configuration"""
        return {
            "window_layout": TmuxLayoutType.TILED.value,
            "enable_logging": True,
            "log_dir": Path.home() / "automation" / "logs",
            "keep_alive": True,
            "auto_attach": False,
            "mouse_support": True,
            "status_interval": 1,
        }

    def initialize_epic_session(self, working_dir: str = None) -> bool:
        """Create main tmux session structure

        Args:
            working_dir: Working directory for the session

        Returns:
            True if session created successfully
        """
        working_dir = working_dir or str(Path.cwd())

        # Kill existing session if it exists
        try:
            existing = self.server.find_where({"session_name": self.session_name})
            if existing:
                print(f"Killing existing session: {self.session_name}")
                existing.kill_session()
                time.sleep(1)  # Give it time to clean up
        except:
            pass

        try:
            # Create new session
            self.session = self.server.new_session(
                session_name=self.session_name,
                window_name="orchestrator",
                start_directory=working_dir
            )

            self.creation_time = datetime.now()

            # Configure session
            self._configure_session()

            # Create default windows
            self._create_default_windows()

            print(f"✓ Created tmux session: {self.session_name}")
            print(f"  Attach with: tmux attach -t {self.session_name}")

            return True

        except Exception as e:
            print(f"✗ Failed to create tmux session: {e}")
            return False

    def _configure_session(self):
        """Configure tmux session settings"""
        if not self.session:
            return

        # Enable mouse support
        if self.config.get("mouse_support"):
            self.session.set_option("mouse", "on")

        # Set status bar
        self.session.set_option("status", "on")
        self.session.set_option("status-position", "top")
        self.session.set_option("status-interval", self.config.get("status_interval", 1))

        # Set colors
        self.session.set_option("status-bg", "colour235")
        self.session.set_option("status-fg", "colour136")

        # Custom status line
        status_left = f"#[fg=green]Epic: {self.epic_id} "
        status_right = "#[fg=yellow]%H:%M:%S #[fg=cyan]| #(echo $USER)@#H"

        self.session.set_option("status-left", status_left)
        self.session.set_option("status-right", status_right)
        self.session.set_option("status-left-length", "30")
        self.session.set_option("status-right-length", "60")

    def _create_default_windows(self):
        """Create default window structure"""
        if not self.session:
            return

        # Orchestrator window (already created as first window)
        orchestrator_window = self.session.windows[0]
        orchestrator_window.rename_window("orchestrator")
        self.windows["orchestrator"] = orchestrator_window

        # Monitoring window
        monitoring_window = self.session.new_window(
            window_name="monitoring",
            start_directory=str(Path.cwd())
        )
        self.windows["monitoring"] = monitoring_window

        # Logs window
        logs_window = self.session.new_window(
            window_name="logs",
            start_directory=str(self.config.get("log_dir", "."))
        )
        self.windows["logs"] = logs_window

        # HITL (Human-in-the-loop) window
        hitl_window = self.session.new_window(
            window_name="hitl",
            start_directory=str(Path.cwd())
        )
        self.windows["hitl"] = hitl_window

    def create_story_window(self, story_id: str, layout: str = None) -> Optional[Any]:
        """Create dedicated window for story execution

        Args:
            story_id: Story identifier
            layout: Optional layout type

        Returns:
            Window object if created successfully
        """
        if not self.session:
            return None

        window_name = f"story-{story_id}"

        # Check if window already exists
        if window_name in self.windows:
            return self.windows[window_name]

        try:
            # Create story window
            story_window = self.session.new_window(
                window_name=window_name,
                start_directory=str(Path.cwd())
            )

            # Create 4 panes for each agent phase (2x2 grid)
            self._create_story_panes(story_window, story_id)

            # Apply layout
            layout = layout or self.config.get("window_layout", "tiled")
            story_window.select_layout(layout)

            self.windows[window_name] = story_window

            # Enable logging if configured
            if self.config.get("enable_logging"):
                self._enable_pane_logging(story_window, story_id)

            return story_window

        except Exception as e:
            print(f"Failed to create story window: {e}")
            return None

    def _create_story_panes(self, window: Any, story_id: str):
        """Create panes for story agents

        Args:
            window: Tmux window object
            story_id: Story identifier
        """
        # Start with one pane
        base_pane = window.panes[0]

        # Split to create 4 panes (2x2 grid)
        # Split vertically first
        right_pane = base_pane.split_window(vertical=True, percent=50)

        # Split each pane horizontally
        bottom_left = base_pane.split_window(vertical=False, percent=50)
        bottom_right = right_pane.split_window(vertical=False, percent=50)

        # Now we have 4 panes
        panes = window.panes

        # Assign panes to agents and set titles
        agents = ["sm-draft", "po-validate", "dev-implement", "qa-test"]
        colors = ["green", "yellow", "cyan", "magenta"]

        for idx, (pane, agent, color) in enumerate(zip(panes, agents, colors)):
            # Store pane reference
            self.panes[f"{story_id}_{agent}"] = pane

            # Send initial message to pane
            pane.send_keys(f"echo -e '\\033[1;{30 + idx}m=== {agent.upper()} PANE ==\\033[0m'")
            pane.send_keys(f"echo 'Story: {story_id}'")
            pane.send_keys(f"echo 'Ready for agent execution...'")

    def execute_agent_in_pane(self, story_id: str, agent: str, command: str) -> bool:
        """Execute BMad agent in dedicated pane

        Args:
            story_id: Story identifier
            agent: Agent name (sm, po, dev, qa)
            command: Command to execute

        Returns:
            True if command sent successfully
        """
        # Get or create story window
        window = self.windows.get(f"story-{story_id}")
        if not window:
            window = self.create_story_window(story_id)

        # Map agent to pane index
        pane_mapping = {
            "sm": 0,
            "po": 1,
            "dev": 2,
            "qa": 3
        }

        pane_idx = pane_mapping.get(agent, 0)

        try:
            pane = window.panes[pane_idx]

            # Clear pane
            pane.send_keys("C-c", suppress_history=True)  # Kill any running process
            time.sleep(0.5)
            pane.send_keys("clear")

            # Send execution header
            pane.send_keys(f"echo '════════════════════════════════════'")
            pane.send_keys(f"echo 'Executing: {agent.upper()} for {story_id}'")
            pane.send_keys(f"echo 'Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}'")
            pane.send_keys(f"echo '════════════════════════════════════'")
            pane.send_keys("")

            # Execute command
            pane.send_keys(command)

            return True

        except Exception as e:
            print(f"Failed to execute in pane: {e}")
            return False

    def capture_pane_output(self, story_id: str, agent: str, lines: int = -1) -> str:
        """Capture output from agent pane

        Args:
            story_id: Story identifier
            agent: Agent name
            lines: Number of lines to capture (-1 for all)

        Returns:
            Captured output text
        """
        window = self.windows.get(f"story-{story_id}")
        if not window:
            return ""

        pane_mapping = {"sm": 0, "po": 1, "dev": 2, "qa": 3}
        pane_idx = pane_mapping.get(agent, 0)

        try:
            pane = window.panes[pane_idx]

            # Capture pane content
            if lines == -1:
                output = pane.cmd("capture-pane", "-p").stdout
            else:
                output = pane.cmd("capture-pane", "-p", f"-S -{lines}").stdout

            return "\n".join(output) if output else ""

        except Exception as e:
            print(f"Failed to capture pane output: {e}")
            return ""

    def _enable_pane_logging(self, window: Any, story_id: str):
        """Enable logging for all panes in window

        Args:
            window: Tmux window object
            story_id: Story identifier
        """
        log_dir = self.config.get("log_dir", Path.home() / "automation" / "logs")
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        agents = ["sm", "po", "dev", "qa"]

        for idx, agent in enumerate(agents):
            try:
                pane = window.panes[idx]
                log_file = log_dir / f"tmux-{self.epic_id}-{story_id}-{agent}.log"

                # Start logging
                pane.cmd("pipe-pane", f"-o 'cat >> {log_file}'")

            except Exception as e:
                print(f"Failed to enable logging for {agent}: {e}")

    def send_to_orchestrator(self, message: str):
        """Send message to orchestrator window

        Args:
            message: Message to send
        """
        orchestrator = self.windows.get("orchestrator")
        if orchestrator and orchestrator.panes:
            orchestrator.panes[0].send_keys(message)

    def send_to_monitoring(self, message: str):
        """Send message to monitoring window

        Args:
            message: Message to send
        """
        monitoring = self.windows.get("monitoring")
        if monitoring and monitoring.panes:
            monitoring.panes[0].send_keys(message)

    def attach_to_session(self) -> bool:
        """Attach to tmux session

        Returns:
            True if attach command executed
        """
        try:
            subprocess.run(["tmux", "attach-session", "-t", self.session_name])
            return True
        except Exception as e:
            print(f"Failed to attach to session: {e}")
            return False

    def create_session_checkpoint(self) -> Dict[str, Any]:
        """Save session state for recovery

        Returns:
            Checkpoint dictionary
        """
        checkpoint = {
            "epic_id": self.epic_id,
            "session_name": self.session_name,
            "creation_time": self.creation_time.isoformat() if self.creation_time else None,
            "windows": list(self.windows.keys()),
            "active_stories": [],
            "timestamp": datetime.now().isoformat()
        }

        # Extract active stories
        for window_name in self.windows.keys():
            if window_name.startswith("story-"):
                story_id = window_name.replace("story-", "")
                checkpoint["active_stories"].append(story_id)

        # Save to file
        checkpoint_file = Path.home() / ".bmad-sessions" / f"{self.session_name}.checkpoint"
        checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint, f, indent=2)

        return checkpoint

    def recover_from_checkpoint(self, checkpoint_file: str) -> bool:
        """Restore session from checkpoint after crash

        Args:
            checkpoint_file: Path to checkpoint file

        Returns:
            True if recovery successful
        """
        try:
            with open(checkpoint_file) as f:
                checkpoint = json.load(f)

            # Try to reconnect to existing session
            try:
                self.session = self.server.find_where(
                    {"session_name": checkpoint["session_name"]}
                )
                print(f"✓ Reconnected to existing session: {checkpoint['session_name']}")

                # Rebuild window references
                for window in self.session.windows:
                    self.windows[window.name] = window

                return True

            except:
                print(f"Session not found. Recreating from checkpoint...")

                # Recreate session
                self.initialize_epic_session()

                # Recreate story windows
                for story_id in checkpoint.get("active_stories", []):
                    self.create_story_window(story_id)

                print(f"✓ Session recreated from checkpoint")
                return True

        except Exception as e:
            print(f"Failed to recover from checkpoint: {e}")
            return False

    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information

        Returns:
            Session information dictionary
        """
        if not self.session:
            return {"status": "not_connected"}

        info = {
            "status": "connected",
            "session_name": self.session_name,
            "epic_id": self.epic_id,
            "creation_time": self.creation_time.isoformat() if self.creation_time else None,
            "windows": {},
            "statistics": {}
        }

        # Get window information
        for name, window in self.windows.items():
            info["windows"][name] = {
                "id": window.id if hasattr(window, 'id') else None,
                "panes": len(window.panes) if hasattr(window, 'panes') else 0
            }

        # Calculate statistics
        info["statistics"] = {
            "total_windows": len(self.windows),
            "story_windows": sum(1 for w in self.windows if w.startswith("story-")),
            "uptime_minutes": (
                (datetime.now() - self.creation_time).seconds / 60
                if self.creation_time else 0
            )
        }

        return info

    def kill_session(self) -> bool:
        """Kill the tmux session

        Returns:
            True if session killed successfully
        """
        try:
            if self.session:
                self.session.kill_session()
                print(f"✓ Killed session: {self.session_name}")

            self.session = None
            self.windows = {}
            self.panes = {}

            return True

        except Exception as e:
            print(f"Failed to kill session: {e}")
            return False

    def list_all_sessions(self) -> List[str]:
        """List all BMad tmux sessions

        Returns:
            List of session names
        """
        try:
            sessions = self.server.list_sessions()
            bmad_sessions = [
                s.get("session_name", "") for s in sessions
                if s.get("session_name", "").startswith("bmad-")
            ]
            return bmad_sessions

        except:
            return []


# CLI interface for testing
if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="BMad Tmux Manager CLI")
    parser.add_argument("action", choices=["create", "attach", "info", "kill", "list"],
                       help="Action to perform")
    parser.add_argument("--epic", help="Epic ID")
    parser.add_argument("--story", help="Story ID")
    parser.add_argument("--agent", help="Agent name (sm, po, dev, qa)")
    parser.add_argument("--command", help="Command to execute")

    args = parser.parse_args()

    if args.action == "list":
        manager = BmadTmuxManager("dummy")
        sessions = manager.list_all_sessions()
        print("BMad Tmux Sessions:")
        for session in sessions:
            print(f"  - {session}")

    elif args.action == "create":
        if not args.epic:
            print("Error: --epic required")
            sys.exit(1)

        manager = BmadTmuxManager(args.epic)
        if manager.initialize_epic_session():
            print("Session created successfully")
            manager.create_session_checkpoint()

    elif args.action == "attach":
        if not args.epic:
            print("Error: --epic required")
            sys.exit(1)

        manager = BmadTmuxManager(args.epic)
        manager.attach_to_session()

    elif args.action == "info":
        if not args.epic:
            print("Error: --epic required")
            sys.exit(1)

        manager = BmadTmuxManager(args.epic)
        info = manager.get_session_info()
        print(json.dumps(info, indent=2))

    elif args.action == "kill":
        if not args.epic:
            print("Error: --epic required")
            sys.exit(1)

        manager = BmadTmuxManager(args.epic)
        manager.kill_session()