"""
File monitoring system for detecting BMad agent completion.

This module provides file-based communication between the orchestrator
and BMad agents running in tmux sessions. Agents update story files,
and the orchestrator monitors these changes to detect completion.

Based on: docs/design/file-communication.md
"""

import asyncio
from pathlib import Path
from typing import Callable, Optional, Dict
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
import time


class StoryFileMonitor(FileSystemEventHandler):
    """
    Monitors story file for changes indicating agent completion.

    BMad agents update story files in docs/stories/ as they work.
    This monitor detects those changes and extracts status information.

    Example:
        >>> monitor = StoryFileMonitor(
        ...     story_file=Path("docs/stories/1.1.story.md"),
        ...     on_change=lambda status: print(status)
        ... )
        >>> status = monitor.parse_story_file()
        >>> print(status['po_decision'])  # "APPROVED"
    """

    def __init__(
        self,
        story_file: Path,
        on_change: Optional[Callable[[dict], None]] = None
    ):
        """
        Initialize story file monitor.

        Args:
            story_file: Path to story file to monitor
            on_change: Optional callback when file changes (receives parsed status)
        """
        self.story_file = story_file
        self.on_change = on_change
        self.last_modified_time = 0

    def on_modified(self, event: FileModifiedEvent):
        """
        Called when file is modified.

        This is invoked by watchdog when the file system detects a change.
        """
        if event.src_path != str(self.story_file):
            return

        # Debounce (file might be written multiple times)
        if not self.story_file.exists():
            return

        current_time = self.story_file.stat().st_mtime
        if current_time == self.last_modified_time:
            return

        self.last_modified_time = current_time

        # Parse file and notify
        try:
            status = self.parse_story_file()
            if self.on_change:
                self.on_change(status)
        except Exception as e:
            print(f"  Warning: Error parsing story file: {e}")

    def parse_story_file(self) -> dict:
        """
        Extract status information from story file.

        Parses the story file to extract:
        - File existence and size
        - PO decision (APPROVED/BLOCKED/CHANGES)
        - Dev status (Ready for Review/In Progress/Done)
        - QA results (PASS/FAIL)
        - File list (files modified by Dev)

        Returns:
            Dictionary with status information:
            {
                'exists': bool,
                'size': int,
                'po_decision': str | None,
                'dev_status': str | None,
                'qa_results': str | None,
                'file_list': list[str]
            }
        """
        if not self.story_file.exists():
            return {
                'exists': False,
                'size': 0,
                'po_decision': None,
                'dev_status': None,
                'qa_results': None,
                'file_list': []
            }

        content = self.story_file.read_text()
        size = self.story_file.stat().st_size

        status = {
            'exists': True,
            'size': size,
            'po_decision': self._extract_po_decision(content),
            'dev_status': self._extract_dev_status(content),
            'qa_results': self._extract_qa_results(content),
            'file_list': self._extract_file_list(content)
        }

        return status

    def _extract_po_decision(self, content: str) -> Optional[str]:
        """
        Extract PO decision from story file.

        Looks for "## PO Decision" section and searches for:
        - APPROVED
        - BLOCKED
        - CHANGES (or CHANGES REQUESTED)

        Args:
            content: Story file content

        Returns:
            "APPROVED", "BLOCKED", "CHANGES", or None
        """
        lines = content.split('\n')
        in_po_section = False

        for line in lines:
            if '## PO Decision' in line:
                in_po_section = True
                continue

            if in_po_section:
                # Next section starts
                if line.startswith('##'):
                    break

                # Check for decision keywords
                upper_line = line.upper()
                if 'APPROVED' in upper_line:
                    return 'APPROVED'
                elif 'BLOCKED' in upper_line:
                    return 'BLOCKED'
                elif 'CHANGES' in upper_line:
                    return 'CHANGES'

        return None

    def _extract_dev_status(self, content: str) -> Optional[str]:
        """
        Extract Dev status from story file.

        Looks for status indicators:
        - "Ready for Review"
        - "In Progress"
        - "Done"

        Args:
            content: Story file content

        Returns:
            Status string or None
        """
        if 'Ready for Review' in content or 'ready-for-review' in content.lower():
            return 'Ready for Review'
        elif 'In Progress' in content:
            return 'In Progress'
        elif 'Status: Done' in content or 'status: done' in content.lower():
            return 'Done'

        return None

    def _extract_qa_results(self, content: str) -> Optional[str]:
        """
        Extract QA results from story file.

        Looks for QA test results:
        - PASS or "All tests passed"
        - FAIL or "Tests failed"

        Args:
            content: Story file content

        Returns:
            "PASS", "FAIL", or None
        """
        # Look for QA Results or Testing section
        if 'QA Results' in content or '## Testing' in content:
            upper_content = content.upper()
            if 'STATUS: PASS' in upper_content or 'ALL TESTS PASSED' in upper_content:
                return 'PASS'
            elif 'STATUS: FAIL' in upper_content or 'TESTS FAILED' in upper_content:
                return 'FAIL'

        return None

    def _extract_file_list(self, content: str) -> list[str]:
        """
        Extract list of files modified by Dev.

        Looks for "## File List" section and extracts markdown list items.

        Args:
            content: Story file content

        Returns:
            List of file paths
        """
        files = []
        lines = content.split('\n')
        in_file_list = False

        for line in lines:
            if '## File List' in line:
                in_file_list = True
                continue

            if in_file_list:
                # Next section starts
                if line.startswith('##'):
                    break

                # Extract markdown list item
                stripped = line.strip()
                if stripped.startswith('- '):
                    file_path = stripped[2:].strip()
                    if file_path:
                        files.append(file_path)

        return files


async def wait_for_file_condition(
    file_path: Path,
    condition: Callable[[dict], bool],
    timeout: int = 600,
    check_interval: float = 2.0
) -> bool:
    """
    Wait for file to meet a condition.

    Polls the file periodically and checks if it meets the specified condition.
    Used to wait for agents to complete by monitoring story file changes.

    Args:
        file_path: Path to file to monitor
        condition: Function(status_dict) -> bool that checks if condition met
        timeout: Maximum seconds to wait
        check_interval: Seconds between checks

    Returns:
        True if condition met before timeout, False otherwise

    Example:
        >>> # Wait for file to exist and have content
        >>> success = await wait_for_file_condition(
        ...     Path("docs/stories/1.1.story.md"),
        ...     lambda s: s.get('exists') and s.get('size', 0) > 1000,
        ...     timeout=600
        ... )
    """
    start_time = asyncio.get_event_loop().time()
    monitor = StoryFileMonitor(file_path, None)

    while (asyncio.get_event_loop().time() - start_time) < timeout:
        status = monitor.parse_story_file()

        if condition(status):
            return True

        await asyncio.sleep(check_interval)

    return False


async def wait_for_sm_completion(story_file: Path, timeout: int = 600) -> bool:
    """
    Wait for SM to create story file with substantial content.

    SM agent is considered complete when:
    - File exists
    - Size > 1000 bytes (substantial content)
    - Has "## Acceptance Criteria" section
    - Has "## Tasks" or "## Subtasks" section

    Args:
        story_file: Path to story file
        timeout: Maximum seconds to wait

    Returns:
        True if SM completed, False if timeout
    """
    def check_sm_done(status: dict) -> bool:
        if not status.get('exists'):
            return False

        if status.get('size', 0) < 1000:
            return False

        # Read content and verify required sections
        try:
            content = story_file.read_text()
            has_criteria = '## Acceptance Criteria' in content
            has_tasks = ('## Tasks' in content or '## Subtasks' in content)
            return has_criteria and has_tasks
        except Exception:
            return False

    return await wait_for_file_condition(story_file, check_sm_done, timeout)


async def wait_for_po_decision(story_file: Path, timeout: int = 300) -> str:
    """
    Wait for PO to update story file with decision.

    PO agent is considered complete when story file contains
    a PO decision (APPROVED, BLOCKED, or CHANGES).

    Args:
        story_file: Path to story file
        timeout: Maximum seconds to wait

    Returns:
        "APPROVED", "BLOCKED", "CHANGES", or "TIMEOUT"
    """
    def check_po_done(status: dict) -> bool:
        return status.get('po_decision') is not None

    success = await wait_for_file_condition(story_file, check_po_done, timeout)

    if not success:
        return "TIMEOUT"

    # Parse decision
    monitor = StoryFileMonitor(story_file, None)
    status = monitor.parse_story_file()

    return status.get('po_decision', 'UNKNOWN')


async def wait_for_dev_completion(story_file: Path, timeout: int = 1800) -> dict:
    """
    Wait for Dev to complete implementation.

    Dev agent is considered complete when story file status is
    "Ready for Review" or "Done".

    Args:
        story_file: Path to story file
        timeout: Maximum seconds to wait (30 minutes default)

    Returns:
        Dictionary with:
        {
            'success': bool,
            'status': str,
            'files_modified': list[str]
        }
    """
    def check_dev_done(status: dict) -> bool:
        dev_status = status.get('dev_status')
        return dev_status in ['Ready for Review', 'Done']

    success = await wait_for_file_condition(story_file, check_dev_done, timeout)

    if not success:
        return {
            'success': False,
            'status': 'TIMEOUT',
            'files_modified': []
        }

    # Parse implementation details
    monitor = StoryFileMonitor(story_file, None)
    status = monitor.parse_story_file()

    return {
        'success': True,
        'status': status.get('dev_status'),
        'files_modified': status.get('file_list', [])
    }


async def wait_for_qa_completion(story_file: Path, timeout: int = 900) -> dict:
    """
    Wait for QA to complete tests.

    QA agent is considered complete when story file contains
    test results (PASS or FAIL).

    Args:
        story_file: Path to story file
        timeout: Maximum seconds to wait (15 minutes default)

    Returns:
        Dictionary with:
        {
            'success': bool,
            'results': str  # "PASS", "FAIL", or "TIMEOUT"
        }
    """
    def check_qa_done(status: dict) -> bool:
        return status.get('qa_results') is not None

    success = await wait_for_file_condition(story_file, check_qa_done, timeout)

    if not success:
        return {'success': False, 'results': 'TIMEOUT'}

    # Parse test results
    monitor = StoryFileMonitor(story_file, None)
    status = monitor.parse_story_file()

    qa_results = status.get('qa_results', 'UNKNOWN')

    return {
        'success': qa_results == 'PASS',
        'results': qa_results
    }
