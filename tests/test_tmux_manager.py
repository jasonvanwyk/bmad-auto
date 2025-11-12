"""
Unit tests for tmux_manager module.

Tests the TmuxAgentManager for spawning and managing tmux sessions.
"""

import pytest
import time
from pathlib import Path
from src.tmux_manager import TmuxAgentManager


@pytest.fixture
def test_project_dir(tmp_path):
    """Create a temporary project directory."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    return project_dir


def test_tmux_manager_init(test_project_dir):
    """Test TmuxAgentManager initialization."""
    mgr = TmuxAgentManager(test_project_dir)

    assert mgr.project_path == test_project_dir.resolve()
    assert mgr.server is not None
    assert len(mgr.sessions) == 0


def test_spawn_session_basic(test_project_dir):
    """Test spawning a basic tmux session."""
    mgr = TmuxAgentManager(test_project_dir)

    try:
        session_id = mgr.spawn_agent_session(
            agent="sm",
            story_id="test-1",
            commands=None,  # Don't send Claude commands in test
            wait_for_ready=1.0
        )

        # Verify session was created
        assert session_id.startswith("bmad-sm")
        assert session_id in mgr.sessions

        # Verify session exists in tmux
        assert mgr._session_exists(session_id)

    finally:
        # Cleanup
        mgr.kill_session(session_id)


def test_session_metadata(test_project_dir):
    """Test session metadata tracking."""
    mgr = TmuxAgentManager(test_project_dir)

    try:
        session_id = mgr.spawn_agent_session(
            agent="sm",
            story_id="1.1",
            commands=None,
            wait_for_ready=0.5
        )

        # Get session info
        info = mgr.get_session_info(session_id)

        assert info['agent'] == 'sm'
        assert info['story_id'] == '1.1'
        assert info['running_time'] >= 0
        assert info['session_exists'] is True

    finally:
        mgr.kill_session(session_id)


def test_send_keys(test_project_dir):
    """Test sending keys to session."""
    mgr = TmuxAgentManager(test_project_dir)

    try:
        session_id = mgr.spawn_agent_session(
            agent="sm",
            story_id="test-2",
            commands=None,
            wait_for_ready=0.5
        )

        # Send test command
        mgr.send_keys(session_id, "echo 'test'", wait=0.5)

        # Capture output
        output = mgr.capture_pane_output(session_id)

        # Should contain our echo command
        assert "echo 'test'" in output or "test" in output

    finally:
        mgr.kill_session(session_id)


def test_kill_session(test_project_dir):
    """Test killing a session."""
    mgr = TmuxAgentManager(test_project_dir)

    session_id = mgr.spawn_agent_session(
        agent="sm",
        story_id="test-3",
        commands=None,
        wait_for_ready=0.5
    )

    # Verify session exists
    assert session_id in mgr.sessions
    assert mgr._session_exists(session_id)

    # Kill session
    mgr.kill_session(session_id)

    # Verify session removed
    assert session_id not in mgr.sessions
    time.sleep(0.5)  # Give tmux time to cleanup
    assert not mgr._session_exists(session_id)


def test_kill_nonexistent_session(test_project_dir):
    """Test killing a session that doesn't exist."""
    mgr = TmuxAgentManager(test_project_dir)

    # Should not raise exception
    mgr.kill_session("nonexistent-session")


def test_list_sessions(test_project_dir):
    """Test listing active sessions."""
    mgr = TmuxAgentManager(test_project_dir)

    try:
        # Create multiple sessions
        session1 = mgr.spawn_agent_session("sm", "1.1", None, 0.5)
        session2 = mgr.spawn_agent_session("po", "1.1", None, 0.5)

        # List sessions
        sessions = mgr.list_sessions()

        assert len(sessions) == 2
        assert session1 in sessions
        assert session2 in sessions

    finally:
        mgr.kill_all_sessions()


def test_kill_all_sessions(test_project_dir):
    """Test killing all sessions."""
    mgr = TmuxAgentManager(test_project_dir)

    # Create multiple sessions
    mgr.spawn_agent_session("sm", "1.1", None, 0.5)
    mgr.spawn_agent_session("po", "1.1", None, 0.5)
    mgr.spawn_agent_session("dev", "1.1", None, 0.5)

    assert len(mgr.sessions) == 3

    # Kill all
    mgr.kill_all_sessions()

    assert len(mgr.sessions) == 0


def test_session_name_format(test_project_dir):
    """Test session naming convention."""
    mgr = TmuxAgentManager(test_project_dir)

    try:
        # Test various story IDs
        session1 = mgr.spawn_agent_session("sm", "1.1", None, 0.5)
        assert session1 == "bmad-sm-1-1"  # . replaced with -

        mgr.kill_session(session1)

        session2 = mgr.spawn_agent_session("po", "2.3.1", None, 0.5)
        assert session2 == "bmad-po-2-3-1"

        mgr.kill_session(session2)

    finally:
        mgr.kill_all_sessions()


def test_attach_instructions(test_project_dir):
    """Test getting attach instructions."""
    mgr = TmuxAgentManager(test_project_dir)

    try:
        session_id = mgr.spawn_agent_session("sm", "1.1", None, 0.5)

        instructions = mgr.attach_instructions(session_id)

        assert "tmux attach -t" in instructions
        assert session_id in instructions

    finally:
        mgr.kill_session(session_id)
