# File-Based Communication Protocol

## Overview

The orchestrator and BMad agents communicate through **file system changes**, not direct IPC. This approach is:

- ✅ **Reliable** - File changes are atomic and persistent
- ✅ **Debuggable** - Can inspect files manually at any point
- ✅ **BMad-compliant** - Agents naturally work with story files
- ✅ **Auditable** - Complete trail of changes in git

---

## Communication Model

```
Orchestrator                    BMad Agent (in tmux)
    |                                   |
    | 1. Spawn tmux session             |
    |---------------------------------->|
    |                                   | 2. Activate agent (/sm)
    |                                   | 3. Execute task (*create)
    |                                   | 4. Load architecture docs
    |                                   | 5. Create story file
    |                                   |    docs/stories/1.1.story.md
    | 6. Detect file creation           |
    |<----------------------------------|
    | 7. Parse story file               |
    | 8. Kill tmux session              |
    |---------------------------------->|
    |                                   | Session terminated
```

**Key insight**: Orchestrator **monitors files**, not stdout/stderr

---

## File Types

### 1. Story Files (Primary Communication Channel)

**Location**: `docs/stories/{epic}.{story}.story.md`

**Purpose**: Main artifact BMad agents create and update

**Lifecycle**:
1. **SM creates** story file with full context
2. **PO updates** with validation decision
3. **Dev updates** with implementation details, file list
4. **QA updates** with test results

**Example story file structure**:
```markdown
# Story 1.1: Git Branching Strategy

## Story
As a development team, we need a documented git workflow...

## Acceptance Criteria
- [ ] Branch naming conventions documented
- [ ] PR requirements defined
- [ ] Branch protection configured

## PO Decision
Status: APPROVED
Validated: 2024-11-12 10:30:00
Rationale: Story is clear, testable, aligns with architecture.

## Dev Agent Record
Status: Ready for Review
Files Modified: 2
Implementation Time: 15 minutes

## File List
- docs/git-workflow.md
- .github/PULL_REQUEST_TEMPLATE.md

## Testing / Validation
- [x] docs/git-workflow.md exists and has content
- [x] Branch naming conventions documented
- [x] PR requirements defined

## QA Results
Status: PASS
All acceptance criteria met.
Tests passed: 3/3
```

### 2. Checkpoint Files (Orchestrator State)

**Location**: `.bmad-checkpoint-{epic_id}.yaml`

**Purpose**: Track orchestrator progress for resume capability

**Example**:
```yaml
epic_id: epic-1
last_completed_story: "1.1"
stories_completed:
  - story_id: "1.1"
    status: completed
    po_decision: APPROVED
    qa_results: PASSED
    completed_at: "2024-11-12T10:45:00"
stories_failed:
  - story_id: "1.2"
    status: failed
    stage: po
    po_decision: BLOCKED
    reason: "Missing architecture details"
    failed_at: "2024-11-12T11:00:00"
```

### 3. Handoff Files (Inter-Agent Context - Optional)

**Location**: `.bmad-handoff-{story_id}.yaml`

**Purpose**: Minimal context between agent stages (if needed)

**Example**:
```yaml
story_id: "1.1"
story_file: "docs/stories/1.1.story.md"
sm_completed_at: "2024-11-12T10:30:00"
po_decision: "APPROVED"
po_completed_at: "2024-11-12T10:35:00"
dev_files_modified:
  - docs/git-workflow.md
  - .github/PULL_REQUEST_TEMPLATE.md
dev_completed_at: "2024-11-12T10:50:00"
```

**Note**: Handoff files are optional since story files contain all necessary context.

---

## File Monitoring System

### Watchdog-Based Implementation

```python
import asyncio
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from typing import Callable, Optional
import yaml

class StoryFileMonitor(FileSystemEventHandler):
    """
    Monitors story file for changes indicating agent completion.
    """

    def __init__(
        self,
        story_file: Path,
        on_change: Callable[[dict], None]
    ):
        """
        Args:
            story_file: Path to story file to monitor
            on_change: Callback when file changes (receives parsed status)
        """
        self.story_file = story_file
        self.on_change = on_change
        self.last_modified_time = 0

    def on_modified(self, event: FileModifiedEvent):
        """Called when file is modified."""
        if event.src_path != str(self.story_file):
            return

        # Debounce (file might be written multiple times)
        current_time = self.story_file.stat().st_mtime
        if current_time == self.last_modified_time:
            return

        self.last_modified_time = current_time

        # Parse file and notify
        try:
            status = self.parse_story_file()
            self.on_change(status)
        except Exception as e:
            print(f"Error parsing story file: {e}")

    def parse_story_file(self) -> dict:
        """
        Extract status information from story file.

        Returns:
            dict with: {
                'exists': bool,
                'size': int,
                'po_decision': str | None,
                'dev_status': str | None,
                'qa_results': str | None,
                'file_list': list[str]
            }
        """
        if not self.story_file.exists():
            return {'exists': False}

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
        """Extract PO decision from story file."""
        # Look for "## PO Decision" section
        lines = content.split('\n')
        in_po_section = False

        for line in lines:
            if '## PO Decision' in line:
                in_po_section = True
                continue

            if in_po_section:
                if line.startswith('##'):  # Next section
                    break

                if 'Status: APPROVED' in line or 'APPROVED' in line:
                    return 'APPROVED'
                elif 'Status: BLOCKED' in line or 'BLOCKED' in line:
                    return 'BLOCKED'
                elif 'CHANGES' in line:
                    return 'CHANGES'

        return None

    def _extract_dev_status(self, content: str) -> Optional[str]:
        """Extract Dev status from story file."""
        if 'Status: Ready for Review' in content:
            return 'Ready for Review'
        elif 'Status: In Progress' in content:
            return 'In Progress'
        elif 'Status: Done' in content:
            return 'Done'

        return None

    def _extract_qa_results(self, content: str) -> Optional[str]:
        """Extract QA results from story file."""
        if 'QA Results' in content or '## Testing' in content:
            if 'Status: PASS' in content or 'All tests passed' in content:
                return 'PASS'
            elif 'Status: FAIL' in content or 'Tests failed' in content:
                return 'FAIL'

        return None

    def _extract_file_list(self, content: str) -> list[str]:
        """Extract list of files modified by Dev."""
        files = []
        lines = content.split('\n')
        in_file_list = False

        for line in lines:
            if '## File List' in line:
                in_file_list = True
                continue

            if in_file_list:
                if line.startswith('##'):  # Next section
                    break

                if line.strip().startswith('- '):
                    files.append(line.strip()[2:].strip())

        return files


async def wait_for_file_condition(
    file_path: Path,
    condition: Callable[[dict], bool],
    timeout: int = 600,
    check_interval: float = 2.0
) -> bool:
    """
    Wait for file to meet a condition.

    Args:
        file_path: Path to monitor
        condition: Function(status_dict) -> bool
        timeout: Max seconds to wait
        check_interval: Seconds between checks

    Returns:
        True if condition met, False if timeout

    Example:
        # Wait for file to exist and have content
        success = await wait_for_file_condition(
            story_file,
            lambda s: s.get('exists') and s.get('size', 0) > 1000,
            timeout=600
        )
    """
    start_time = asyncio.get_event_loop().time()

    monitor = StoryFileMonitor(file_path, lambda s: None)

    while (asyncio.get_event_loop().time() - start_time) < timeout:
        status = monitor.parse_story_file()

        if condition(status):
            return True

        await asyncio.sleep(check_interval)

    return False
```

---

## Stage-Specific Detection

### SM Stage: Wait for Story File Creation

```python
async def wait_for_sm_completion(story_file: Path, timeout: int = 600) -> bool:
    """
    Wait for SM to create story file with substantial content.

    Criteria:
    - File exists
    - Size > 1000 bytes
    - Has "## Acceptance Criteria" section
    - Has "## Tasks" section
    """
    def check_sm_done(status: dict) -> bool:
        if not status.get('exists'):
            return False

        if status.get('size', 0) < 1000:
            return False

        # Read content and verify required sections
        content = story_file.read_text()
        return all([
            '## Acceptance Criteria' in content,
            '## Tasks' in content or '## Subtasks' in content
        ])

    return await wait_for_file_condition(story_file, check_sm_done, timeout)
```

### PO Stage: Wait for Validation Decision

```python
async def wait_for_po_decision(story_file: Path, timeout: int = 300) -> str:
    """
    Wait for PO to update story file with decision.

    Returns:
        "APPROVED", "BLOCKED", "CHANGES", or "TIMEOUT"
    """
    def check_po_done(status: dict) -> bool:
        return status.get('po_decision') is not None

    success = await wait_for_file_condition(story_file, check_po_done, timeout)

    if not success:
        return "TIMEOUT"

    # Parse decision
    monitor = StoryFileMonitor(story_file, lambda s: None)
    status = monitor.parse_story_file()

    return status.get('po_decision', 'UNKNOWN')
```

### Dev Stage: Wait for Implementation

```python
async def wait_for_dev_completion(story_file: Path, timeout: int = 1800) -> dict:
    """
    Wait for Dev to complete implementation.

    Returns:
        dict with: {
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
    monitor = StoryFileMonitor(story_file, lambda s: None)
    status = monitor.parse_story_file()

    return {
        'success': True,
        'status': status.get('dev_status'),
        'files_modified': status.get('file_list', [])
    }
```

### QA Stage: Wait for Test Results

```python
async def wait_for_qa_completion(story_file: Path, timeout: int = 900) -> dict:
    """
    Wait for QA to complete tests.

    Returns:
        dict with: {
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
    monitor = StoryFileMonitor(story_file, lambda s: None)
    status = monitor.parse_story_file()

    qa_results = status.get('qa_results', 'UNKNOWN')

    return {
        'success': qa_results == 'PASS',
        'results': qa_results
    }
```

---

## Checkpoint Management

### Checkpoint File Handler

```python
from datetime import datetime
from pathlib import Path
import yaml

class CheckpointManager:
    """
    Manages checkpoint files for resume capability.
    """

    def __init__(self, epic_id: str, project_path: Path):
        self.epic_id = epic_id
        self.project_path = project_path
        self.checkpoint_file = project_path / f".bmad-checkpoint-{epic_id}.yaml"

    def load_checkpoint(self) -> dict:
        """Load existing checkpoint or create new."""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file) as f:
                return yaml.safe_load(f)
        else:
            return {
                'epic_id': self.epic_id,
                'last_completed_story': None,
                'stories_completed': [],
                'stories_failed': [],
                'started_at': datetime.now().isoformat()
            }

    def save_checkpoint(self, checkpoint: dict):
        """Save checkpoint to file."""
        checkpoint['updated_at'] = datetime.now().isoformat()

        with open(self.checkpoint_file, 'w') as f:
            yaml.safe_dump(checkpoint, f, default_flow_style=False)

    def mark_story_completed(
        self,
        story_id: str,
        po_decision: str,
        qa_results: str,
        files_modified: list[str]
    ):
        """Mark story as completed in checkpoint."""
        checkpoint = self.load_checkpoint()

        checkpoint['last_completed_story'] = story_id
        checkpoint['stories_completed'].append({
            'story_id': story_id,
            'status': 'completed',
            'po_decision': po_decision,
            'qa_results': qa_results,
            'files_modified': files_modified,
            'completed_at': datetime.now().isoformat()
        })

        self.save_checkpoint(checkpoint)

    def mark_story_failed(
        self,
        story_id: str,
        stage: str,
        reason: str
    ):
        """Mark story as failed in checkpoint."""
        checkpoint = self.load_checkpoint()

        checkpoint['stories_failed'].append({
            'story_id': story_id,
            'status': 'failed',
            'stage': stage,
            'reason': reason,
            'failed_at': datetime.now().isoformat()
        })

        self.save_checkpoint(checkpoint)

    def should_skip_story(self, story_id: str) -> bool:
        """Check if story already completed."""
        checkpoint = self.load_checkpoint()

        completed_ids = [s['story_id'] for s in checkpoint['stories_completed']]
        return story_id in completed_ids

    def get_resume_point(self) -> Optional[str]:
        """Get story to resume from (first incomplete story)."""
        checkpoint = self.load_checkpoint()
        return checkpoint.get('last_completed_story')
```

### Usage with Orchestrator

```python
async def process_epic_with_checkpoints(epic_id: str, project_path: Path):
    """Process epic with checkpoint/resume capability."""
    checkpoint_mgr = CheckpointManager(epic_id, project_path)

    # Load stories
    stories = load_epic_stories(epic_id, project_path)

    for story in stories:
        story_id = story['id']

        # Skip completed stories
        if checkpoint_mgr.should_skip_story(story_id):
            print(f"⊘ Story {story_id}: Already completed, skipping")
            continue

        print(f"\n→ Processing story {story_id}")

        try:
            # Process story through all stages
            result = await process_story(story_id, project_path)

            if result['success']:
                # Mark completed
                checkpoint_mgr.mark_story_completed(
                    story_id=story_id,
                    po_decision=result['po_decision'],
                    qa_results=result['qa_results'],
                    files_modified=result['files_modified']
                )
                print(f"✓ Story {story_id} completed")
            else:
                # Mark failed
                checkpoint_mgr.mark_story_failed(
                    story_id=story_id,
                    stage=result['failed_stage'],
                    reason=result['error_message']
                )
                print(f"✗ Story {story_id} failed at {result['failed_stage']}")

        except Exception as e:
            # Exception occurred
            checkpoint_mgr.mark_story_failed(
                story_id=story_id,
                stage='unknown',
                reason=str(e)
            )
            print(f"✗ Story {story_id} exception: {e}")
```

---

## Communication Flow Example

### Complete Story Processing

```python
async def process_story_complete_example(story_id: str, project_path: Path):
    """
    Complete example of file-based communication for one story.
    """
    tmux_mgr = AsyncTmuxAgentManager(project_path)
    story_file = project_path / f"docs/stories/{story_id}.story.md"

    print(f"{'='*60}")
    print(f"Story {story_id}")
    print(f"{'='*60}\n")

    # ===== SM Stage =====
    print("→ SM: Creating story file...")

    sm_session = await tmux_mgr.spawn_agent_session_async(
        agent="sm",
        story_id=story_id,
        commands=["/sm", "*create"]
    )

    # Wait for story file creation (FILE-BASED)
    sm_success = await wait_for_sm_completion(story_file, timeout=600)

    if not sm_success:
        print("✗ SM failed to create story")
        await tmux_mgr.kill_session_async(sm_session)
        return {'success': False, 'failed_stage': 'sm'}

    print(f"✓ Story file created: {story_file}")
    await tmux_mgr.kill_session_async(sm_session)

    # ===== PO Stage =====
    print("→ PO: Validating story...")

    po_session = await tmux_mgr.spawn_agent_session_async(
        agent="po",
        story_id=story_id,
        commands=["/po", f"*validate"]
    )

    # Wait for PO decision (FILE-BASED)
    po_decision = await wait_for_po_decision(story_file, timeout=300)

    print(f"✓ PO Decision: {po_decision}")
    await tmux_mgr.kill_session_async(po_session)

    if po_decision != "APPROVED":
        print(f"⊘ Story blocked by PO")
        return {
            'success': False,
            'failed_stage': 'po',
            'po_decision': po_decision
        }

    # ===== Dev Stage =====
    print("→ Dev: Implementing story...")

    dev_session = await tmux_mgr.spawn_agent_session_async(
        agent="dev",
        story_id=story_id,
        commands=["/dev", f"*develop-story"]
    )

    # Wait for dev completion (FILE-BASED)
    dev_result = await wait_for_dev_completion(story_file, timeout=1800)

    if not dev_result['success']:
        print("✗ Dev failed or timed out")
        await tmux_mgr.kill_session_async(dev_session)
        return {
            'success': False,
            'failed_stage': 'dev',
            'po_decision': po_decision
        }

    print(f"✓ Dev completed, modified {len(dev_result['files_modified'])} files")
    await tmux_mgr.kill_session_async(dev_session)

    # ===== QA Stage =====
    print("→ QA: Testing implementation...")

    qa_session = await tmux_mgr.spawn_agent_session_async(
        agent="qa",
        story_id=story_id,
        commands=["/qa", f"*test"]
    )

    # Wait for QA results (FILE-BASED)
    qa_result = await wait_for_qa_completion(story_file, timeout=900)

    print(f"✓ QA Results: {qa_result['results']}")
    await tmux_mgr.kill_session_async(qa_session)

    # ===== Complete =====
    if qa_result['success']:
        print(f"\n✓ Story {story_id} COMPLETE!")
        return {
            'success': True,
            'po_decision': po_decision,
            'qa_results': qa_result['results'],
            'files_modified': dev_result['files_modified']
        }
    else:
        print(f"\n✗ Story {story_id} failed QA")
        return {
            'success': False,
            'failed_stage': 'qa',
            'po_decision': po_decision,
            'qa_results': qa_result['results']
        }
```

---

## Benefits of File-Based Communication

### 1. Reliability
- File operations are atomic
- No lost messages (unlike pipes/sockets)
- Persistent across crashes

### 2. Debuggability
```bash
# Inspect story file anytime
cat docs/stories/1.1.story.md

# Check what PO decided
grep "## PO Decision" docs/stories/1.1.story.md

# See files Dev modified
grep -A 10 "## File List" docs/stories/1.1.story.md
```

### 3. Auditability
```bash
# Full history in git
git log docs/stories/1.1.story.md

# See exactly when PO approved
git blame docs/stories/1.1.story.md | grep "APPROVED"
```

### 4. BMad Compliance
- Agents naturally update story files
- No special IPC needed
- Works exactly as BMad designed

### 5. Human Inspection
- Can check progress anytime
- Can manually edit if needed
- Can see exactly what agents did

---

## Next Steps

1. ✅ Design file-based communication protocol - **COMPLETE**
2. ⬜ Implement StoryFileMonitor class
3. ⬜ Test file monitoring with sample story file
4. ⬜ Implement CheckpointManager
5. ⬜ Integrate with LangGraph orchestrator
6. ⬜ Test complete story processing flow

**File communication protocol is fully designed!**
