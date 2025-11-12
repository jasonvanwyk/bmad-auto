# Context Management & Validation

## Overview

Critical improvements to prevent context bloat, hallucinations, and ensure quality control in automated agent workflows.

## Key Problems Solved

### 1. Context Bloat & Hallucinations
**Problem**: Agents accumulate context across iterations, leading to:
- Memory/token overload
- Hallucinations from stale context
- Agents going off-track

**Solution**:
- Each agent runs with `--new-session` flag
- Fresh context for every agent execution
- No accumulation between stories or stages

### 2. Lightweight Context Continuity
**Problem**: Need to pass information between agents without bloating context

**Solution**: `StoryHandoff` class
- Manages minimal, focused context passing
- Max summary length: 2000 characters
- Max files tracked: 20
- Auto-truncation prevents bloat
- Cleans up after story completion

### 3. Ambiguous PO Approvals
**Problem**: PO agent often doesn't explicitly approve/block stories

**Solution**: `AgentValidator` with strict validation
- PO **MUST** output: `APPROVED`, `BLOCKED`, or `CHANGES REQUESTED`
- No more "continue anyway" - execution stops if PO is ambiguous
- Validates handoff file has decision recorded

### 4. Quality Control
**Problem**: No validation that agents actually did their work

**Solution**: Output validation for all agents
- **SM**: Validates story was drafted
- **PO**: Validates explicit decision + reasoning if blocked
- **Dev**: Validates files were actually modified/created
- **QA**: Validates test results (PASS/FAIL) are present

## Architecture

### StoryHandoff Class

```python
class StoryHandoff:
    """Manages lightweight context between agent stages"""

    # Limits to prevent bloat
    MAX_SUMMARY_LENGTH = 2000
    MAX_ACCEPTANCE_CRITERIA = 10
    MAX_FILES_TRACKED = 20

    # Methods
    add_stage_summary(stage, summary, decision)
    add_file_modified(file_path, action)
    add_blocker(blocker, stage)
    get_context_for_stage(stage)  # Returns minimal context
    validate_po_decision()
    cleanup()  # Remove after success
```

### AgentValidator Class

```python
class AgentValidator:
    """Validates agent outputs"""

    @staticmethod
    def validate_po_output(output, handoff)

    @staticmethod
    def validate_dev_output(output, handoff)

    @staticmethod
    def validate_qa_output(output, handoff)
```

## Handoff File Structure

```yaml
story_id: story-1.1
created_at: 2025-11-12T10:30:00
stages:
  sm:
    summary: "Story drafted with acceptance criteria"
    decision: null
    timestamp: 2025-11-12T10:30:05
  po:
    summary: "Reviewed story, all criteria clear"
    decision: "APPROVED"
    timestamp: 2025-11-12T10:31:15
  dev:
    summary: "Implemented git workflow documentation"
    decision: null
    timestamp: 2025-11-12T10:45:20
files_modified:
  - path: docs/git-workflow.md
    action: created
    timestamp: 2025-11-12T10:45:18
decisions:
  - stage: po
    decision: APPROVED
    timestamp: 2025-11-12T10:31:15
blockers: []
```

## Context Passing Flow

### Stage 1: SM → PO
**SM receives**: Full story from stories.yaml
**PO receives**: Only SM's summary (truncated to 500 chars)

### Stage 2: PO → Dev
**Dev receives**:
- PO decision (APPROVED/BLOCKED/CHANGES)
- PO summary (truncated to 500 chars)
- No full SM context

### Stage 3: Dev → QA
**QA receives**:
- Dev summary (truncated to 500 chars)
- Last 10 modified files only
- No PO or SM context

### Stage 4: Story Complete
- Handoff file cleaned up
- Only checkpoint remains for resume capability

## Validation Flow

```
Agent Execution
    ↓
Extract: summary, decision, files
    ↓
Update handoff file
    ↓
Validate output
    ↓
 ✓ Pass → Continue
 ✗ Fail → STOP (no "continue anyway")
```

## PO Validation Enforcement

### Before (Broken)
```python
if not po_result['success']:
    print("⚠ PO validation had issues")
    # Continue anyway for MVP  ← DANGEROUS!
```

### After (Fixed)
```python
if not po_result['success']:
    print("✗ PO validation failed")
    return results  ← STOP EXECUTION

# Strict validation
is_valid, msg = AgentValidator.validate_po_output(output, handoff)
if not is_valid:
    print(f"✗ PO VALIDATION ERROR: {msg}")
    print("⚠ PO must explicitly APPROVE, BLOCK, or request CHANGES")
    return results  ← STOP EXECUTION
```

## Benefits

1. **Prevents Context Bloat**
   - Agents can't accumulate stale context
   - Fresh start every execution
   - Predictable token usage

2. **Maintains Continuity**
   - Essential context passed via handoff
   - Auto-truncation prevents growth
   - Summaries stay focused

3. **Enforces Quality**
   - PO can't be ambiguous
   - Dev must create/modify files
   - QA must have test results
   - No silent failures

4. **Debugging Support**
   - Handoff files show decision trail
   - Track which files were modified
   - See exactly where failures occur
   - Clean state after success

## Usage

The system is transparent - no changes needed to run commands:

```bash
# All context management happens automatically
python mvp_story_automation.py --project ./myproject --epic epic-1
```

## Files

- `src/context_manager.py` - StoryHandoff and AgentValidator classes
- `mvp_story_automation.py` - Integrated throughout automation flow

## Testing

Dry run shows validation in action:

```bash
python mvp_story_automation.py --project ./test --epic epic-1 --dry-run
```

Output shows:
- ✓ PO decision validated
- ✓ Dev modified X file(s)
- ✓ QA results validated

## Future Enhancements

- [ ] Configurable max sizes via config file
- [ ] Handoff file retention for debugging (optional)
- [ ] Summary quality scoring
- [ ] Auto-escalation on repeated PO blocks
- [ ] Context usage metrics/reporting
