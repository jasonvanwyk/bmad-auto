"""
Unit tests for file_monitor module.

Tests the StoryFileMonitor and helper functions for parsing
story files and detecting agent completion.
"""

import pytest
import asyncio
from pathlib import Path
from src.file_monitor import StoryFileMonitor, wait_for_file_condition


def test_parse_nonexistent_file(tmp_path):
    """Test parsing a file that doesn't exist."""
    story_file = tmp_path / "nonexistent.md"
    monitor = StoryFileMonitor(story_file)

    status = monitor.parse_story_file()

    assert status['exists'] is False
    assert status['size'] == 0
    assert status['po_decision'] is None


def test_parse_po_decision_approved(tmp_path):
    """Test extracting PO decision: APPROVED."""
    story_file = tmp_path / "story.md"
    story_file.write_text("""
# Story 1.1

## PO Decision
Status: APPROVED
Validated by PO on 2024-11-12

## Other Section
Some content
""")

    monitor = StoryFileMonitor(story_file)
    status = monitor.parse_story_file()

    assert status['exists'] is True
    assert status['po_decision'] == 'APPROVED'


def test_parse_po_decision_blocked(tmp_path):
    """Test extracting PO decision: BLOCKED."""
    story_file = tmp_path / "story.md"
    story_file.write_text("""
# Story 1.1

## PO Decision
Status: BLOCKED
Reason: Missing architecture details

## Other Section
""")

    monitor = StoryFileMonitor(story_file)
    status = monitor.parse_story_file()

    assert status['po_decision'] == 'BLOCKED'


def test_parse_dev_status(tmp_path):
    """Test extracting Dev status."""
    story_file = tmp_path / "story.md"
    story_file.write_text("""
# Story 1.1

## Dev Agent Record
Status: Ready for Review
Files modified: 2

## File List
- src/main.py
- tests/test_main.py
""")

    monitor = StoryFileMonitor(story_file)
    status = monitor.parse_story_file()

    assert status['dev_status'] == 'Ready for Review'
    assert len(status['file_list']) == 2
    assert 'src/main.py' in status['file_list']


def test_parse_qa_results_pass(tmp_path):
    """Test extracting QA results: PASS."""
    story_file = tmp_path / "story.md"
    story_file.write_text("""
# Story 1.1

## QA Results
Status: PASS
All tests passed
Tests run: 5/5
""")

    monitor = StoryFileMonitor(story_file)
    status = monitor.parse_story_file()

    assert status['qa_results'] == 'PASS'


def test_parse_file_list(tmp_path):
    """Test extracting file list."""
    story_file = tmp_path / "story.md"
    story_file.write_text("""
# Story 1.1

## File List
- src/components/Button.tsx
- src/components/Input.tsx
- tests/components/Button.test.tsx

## Other Section
Content
""")

    monitor = StoryFileMonitor(story_file)
    status = monitor.parse_story_file()

    assert len(status['file_list']) == 3
    assert 'src/components/Button.tsx' in status['file_list']
    assert 'tests/components/Button.test.tsx' in status['file_list']


@pytest.mark.asyncio
async def test_wait_for_file_condition_success(tmp_path):
    """Test waiting for file condition that succeeds."""
    test_file = tmp_path / "test.md"

    async def create_file_later():
        await asyncio.sleep(0.5)
        test_file.write_text("content")

    # Start file creation task
    asyncio.create_task(create_file_later())

    # Wait for file to exist
    success = await wait_for_file_condition(
        test_file,
        lambda s: s.get('exists', False),
        timeout=2,
        check_interval=0.1
    )

    assert success is True
    assert test_file.exists()


@pytest.mark.asyncio
async def test_wait_for_file_condition_timeout(tmp_path):
    """Test waiting for file condition that times out."""
    test_file = tmp_path / "never-created.md"

    # Wait for file that will never be created
    success = await wait_for_file_condition(
        test_file,
        lambda s: s.get('exists', False),
        timeout=0.5,
        check_interval=0.1
    )

    assert success is False


def test_parse_complex_story_file(tmp_path):
    """Test parsing a complete story file with all sections."""
    story_file = tmp_path / "story.md"
    story_file.write_text("""
# Story 1.1: Git Branching Strategy

## Story
As a development team, we need a documented git workflow...

## Acceptance Criteria
- [ ] Branch naming conventions documented
- [ ] PR requirements defined

## Tasks
- [ ] Create docs/git-workflow.md
- [ ] Configure branch protection

## PO Decision
Status: APPROVED
Validated: 2024-11-12 10:30:00

## Dev Agent Record
Status: Ready for Review
Implementation time: 15 minutes

## File List
- docs/git-workflow.md
- .github/PULL_REQUEST_TEMPLATE.md

## Testing / Validation
- [x] docs/git-workflow.md exists
- [x] Branch naming conventions documented

## QA Results
Status: PASS
All acceptance criteria met
Tests passed: 3/3
""")

    monitor = StoryFileMonitor(story_file)
    status = monitor.parse_story_file()

    # Verify all extracted information
    assert status['exists'] is True
    assert status['size'] > 0
    assert status['po_decision'] == 'APPROVED'
    assert status['dev_status'] == 'Ready for Review'
    assert status['qa_results'] == 'PASS'
    assert len(status['file_list']) == 2
    assert 'docs/git-workflow.md' in status['file_list']
