# BMad-Compliant Automation Design

## Critical Principle

**DO NOT bypass BMad's workflow. Let agents work as designed with full context.**

BMad is a sophisticated, file-based system with built-in safety mechanisms. Our automation must ORCHESTRATE BMad agents, not replace their functionality.

---

## How BMad Actually Works (File-Based Workflow)

### 1. Core Configuration (`core-config.yaml`)
```yaml
devStoryLocation: docs/stories        # Where story files go
devLoadAlwaysFiles:                    # Dev always loads these
  - docs/architecture/coding-standards.md
  - docs/architecture/tech-stack.md
  - docs/architecture/source-tree.md
architecture:
  architectureSharded: true
  architectureShardedLocation: docs/architecture
prd:
  prdSharded: true
  prdShardedLocation: docs/prd
```

### 2. Agent File Loading (By Design)

**SM Agent (`create-next-story` task)**:
- Loads: `.bmad-core/core-config.yaml`
- Loads: `docs/prd/{epic-files}` (sharded PRD)
- Loads: `docs/architecture/` (multiple files based on story type):
  - For ALL stories: `tech-stack.md`, `unified-project-structure.md`, `coding-standards.md`, `testing-strategy.md`
  - For Backend: `data-models.md`, `database-schema.md`, `backend-architecture.md`, `rest-api-spec.md`
  - For Frontend: `frontend-architecture.md`, `components.md`, `core-workflows.md`
  - For Full-Stack: Both Backend + Frontend files
- Reads: Previous story files in `docs/stories/`
- **Creates**: `docs/stories/{epic}.{story}.story.md` with FULL context

**PO Agent (`validate-next-story` task)**:
- Loads: `.bmad-core/core-config.yaml`
- Loads: `docs/stories/{epic}.{story}.story.md` (created by SM)
- Loads: `.bmad-core/checklists/po-master-checklist.md` (~16k chars)
- Loads: `.bmad-core/templates/story-tmpl.yaml` (for validation)
- Loads: `docs/prd/` (for requirement validation)
- Loads: `docs/architecture/` (for technical validation)
- **Updates**: Story file with validation status and decision

**Dev Agent (`*develop-story` command)**:
- Loads: `.bmad-core/core-config.yaml`
- Loads: `devLoadAlwaysFiles` (coding standards, tech stack, source tree)
- Loads: `docs/stories/{epic}.{story}.story.md` (has ALL context from SM)
- **DOES NOT** load PRD/architecture (story already has extracted context)
- **Updates**: Story file checkboxes, File List, Debug Log, Completion Notes

**QA Agent (`*test-story` command)**:
- Loads: `.bmad-core/core-config.yaml`
- Loads: `docs/stories/{epic}.{story}.story.md`
- Tests against acceptance criteria in story
- **Updates**: Story file with test results

---

## Context Window Management Strategy

### The Challenge
- Agent window: 200,000 tokens
- Full architecture docs: ~50k-100k tokens
- Story file: ~5k-20k tokens
- Checklists: ~10k-20k tokens
- Code being written: variable (10k-50k tokens)
- **Total possible**: 75k-190k tokens per agent

### The Solution: Context Clearing Between Iterations

**NOT between stages** (SM→PO→Dev→QA) but **between STORIES**:

```
Story 1.1: SM → PO → Dev → QA (context accumulates)
↓ CLEAR CONTEXT ↓
Story 1.2: SM → PO → Dev → QA (fresh start)
↓ CLEAR CONTEXT ↓
Story 1.3: SM → PO → Dev → QA (fresh start)
```

**Why this works**:
1. Each agent loads what it needs fresh
2. Story files contain distilled context (not full docs)
3. Dev doesn't re-load architecture (SM already extracted to story)
4. Between stories, we start fresh

### How to Clear Context

**Option A: New Process Per Story** (RECOMMENDED)
```python
# Story 1.1
process_story("1.1")  # Starts new Python subprocess
# Process exits, memory cleared

# Story 1.2
process_story("1.2")  # New subprocess, fresh memory
```

**Option B: Explicit Claude Context Clearing** (If using Claude API)
```python
# After each story, create new session
session = new_claude_session()
session.clear_context()
```

**Option C: BMad CLI Process Isolation**
```python
# Each BMad agent call is a separate process already
subprocess.run(["bmad", "sm", ...])  # Fresh process
subprocess.run(["bmad", "po", ...])  # Fresh process
```

---

## BMad-Compliant Automation Architecture

### Command Structure

**BEFORE (Wrong - Bypasses BMad)**:
```python
# Minimal context YAML
context = {
    'story_id': 'story-1.1',
    'title': '...'
}
bmad sm --context /tmp/minimal.yaml --headless
```

**AFTER (Correct - BMad-Compliant)**:
```python
# Let BMad do its job
bmad sm --task create-next-story --headless

# BMad will:
# - Load core-config.yaml
# - Load architecture docs
# - Load epic files
# - Create complete story file
# - Follow create-next-story checklist
```

### Agent Invocation Pattern

```python
def run_sm_agent(project_path: Path, epic_id: str, story_num: int):
    """
    SM creates story file with full context.
    BMad loads everything it needs automatically.
    """
    # Change to project directory
    os.chdir(project_path)

    # Clear any existing Claude sessions (context clearing)
    clear_context_instruction = (
        "IMPORTANT: Start with fresh context. "
        "Clear any previous conversation history."
    )

    # Run BMad SM
    result = subprocess.run([
        "bmad", "sm",
        "--task", "create-next-story",
        "--headless",
        "--context-instruction", clear_context_instruction
    ], capture_output=True, text=True)

    # SM creates: docs/stories/{epic}.{story}.story.md
    story_file = project_path / f"docs/stories/{epic_id}.{story_num}.story.md"

    return story_file


def run_po_agent(project_path: Path, story_file: Path):
    """
    PO validates the story file SM created.
    BMad loads checklist and validates against architecture.
    """
    os.chdir(project_path)

    clear_context_instruction = (
        "IMPORTANT: Start with fresh context. "
        "Clear any previous conversation history."
    )

    result = subprocess.run([
        "bmad", "po",
        "--task", "validate-next-story",
        "--story-file", str(story_file),
        "--headless",
        "--context-instruction", clear_context_instruction
    ], capture_output=True, text=True)

    # PO updates story file with validation status
    # Parse output for decision (APPROVED/BLOCKED/CHANGES)

    return parse_po_decision(result.stdout)


def run_dev_agent(project_path: Path, story_file: Path):
    """
    Dev implements from story file.
    BMad loads devLoadAlwaysFiles + story (has all context).
    """
    os.chdir(project_path)

    clear_context_instruction = (
        "IMPORTANT: Start with fresh context. "
        "Clear any previous conversation history. "
        "Load only the story file and devLoadAlwaysFiles as configured."
    )

    result = subprocess.run([
        "bmad", "dev",
        "--develop-story",
        "--story-file", str(story_file),
        "--headless",
        "--context-instruction", clear_context_instruction
    ], capture_output=True, text=True)

    # Dev updates story file with implementation

    return parse_dev_results(result.stdout)


def run_qa_agent(project_path: Path, story_file: Path):
    """
    QA tests the implementation.
    BMad loads story file and tests against acceptance criteria.
    """
    os.chdir(project_path)

    clear_context_instruction = (
        "IMPORTANT: Start with fresh context. "
        "Clear any previous conversation history."
    )

    result = subprocess.run([
        "bmad", "qa",
        "--test-story",
        "--story-file", str(story_file),
        "--headless",
        "--context-instruction", clear_context_instruction
    ], capture_output=True, text=True)

    # QA updates story file with test results

    return parse_qa_results(result.stdout)
```

---

## Token Monitoring Strategy

### Monitor But Don't Restrict

```python
class TokenMonitor:
    """
    Monitor token usage without restricting agent context.
    Warn when approaching limits, but let agents load what they need.
    """

    MAX_SAFE_TOKENS = 180000  # 90% of 200k window
    WARN_TOKENS = 150000      # 75% of window

    def estimate_context_size(self, story_file: Path) -> int:
        """Estimate what agent will load."""
        total = 0

        # Story file
        total += estimate_tokens(story_file.read_text())

        # Architecture docs (if SM/PO stage)
        arch_dir = story_file.parent.parent / "architecture"
        if arch_dir.exists():
            for arch_file in arch_dir.glob("*.md"):
                total += estimate_tokens(arch_file.read_text())

        # Checklists (if PO stage)
        # ... etc

        return total

    def check_before_agent(self, agent: str, story_file: Path):
        """Warn if context might be large, but don't block."""
        estimated = self.estimate_context_size(story_file)

        if estimated > self.MAX_SAFE_TOKENS:
            print(f"⚠️  WARNING: Estimated {estimated:,} tokens (90%+ of limit)")
            print(f"   Agent {agent} may hit context limit")
            print(f"   Consider: Reviewing architecture doc sizes")
        elif estimated > self.WARN_TOKENS:
            print(f"ℹ️  Info: Estimated {estimated:,} tokens (75% of limit)")
            print(f"   Still safe, but monitor for issues")
        else:
            print(f"✓ Estimated {estimated:,} tokens (safe)")
```

---

## Story File as Context Container

### How It Works

**SM creates story file with extracted context**:
```markdown
# Story 1.1: Git Branching Strategy

## Story
As a development team, I want a documented git workflow...

## Acceptance Criteria
- [ ] Branch naming conventions documented
- [ ] PR requirements defined
- [ ] Branch protection configured

## Dev Notes

### Relevant Architecture Extract
[Source: docs/architecture/coding-standards.md#git-workflow]
- Branch naming: feature/story-{num}-{slug}
- PR requires: 1 approval, CI passing
- Protected branches: main, develop

### Project Structure
[Source: docs/architecture/source-tree.md]
- Documentation goes in: docs/
- Git workflow docs: docs/git-workflow.md

### Technical Requirements
[Source: docs/architecture/tech-stack.md]
- GitHub Actions for CI/CD
- Branch protection via GitHub settings

## Tasks / Subtasks
- [ ] Create docs/git-workflow.md
  - [ ] Document branch naming conventions
  - [ ] Document PR process
  - [ ] Document merge strategies
- [ ] Configure branch protection rules
  - [ ] Set up main branch protection
  - [ ] Require PR approvals
  - [ ] Require CI status checks

## Dev Agent Record
<!-- Dev updates this section -->

## File List
<!-- Dev lists modified files here -->

## Testing / Validation
- Verify docs/git-workflow.md exists
- Check branch protection configured
- Validate documentation completeness
```

**Dev loads ONLY story file + devLoadAlwaysFiles**:
- Story has extracted architecture context
- No need to reload full architecture docs
- Dev knows exactly what to do
- Token usage stays reasonable

---

## Epic Processing Flow

```python
async def process_epic(project_path: Path, epic_id: str):
    """
    Process an entire epic, clearing context between stories.
    """
    # Load epic to find stories
    stories = load_epic_stories(project_path, epic_id)

    for story_num, story_info in enumerate(stories, start=1):
        print(f"\n{'='*60}")
        print(f"Story {epic_id}.{story_num}: {story_info['title']}")
        print(f"{'='*60}\n")

        # ===== CONTEXT CLEARING POINT =====
        # Each story starts fresh
        if story_num > 1:
            print("🔄 Clearing context between stories...")
            await asyncio.sleep(2)  # Brief pause for process cleanup

        # Monitor estimated token usage
        monitor = TokenMonitor()

        # Stage 1: SM creates story file
        print("→ SM: Creating story file with full context...")
        monitor.check_before_agent("SM", project_path)

        story_file = await run_sm_agent(project_path, epic_id, story_num)

        if not story_file.exists():
            print(f"✗ SM failed to create story file")
            continue

        print(f"✓ Story file created: {story_file}")

        # Stage 2: PO validates story file
        print("→ PO: Validating story with checklist...")
        monitor.check_before_agent("PO", story_file)

        po_decision = await run_po_agent(project_path, story_file)

        if po_decision != "APPROVED":
            print(f"✗ PO Decision: {po_decision}")
            if po_decision == "BLOCKED":
                print("  Story blocked, skipping Dev/QA")
                continue

        print(f"✓ PO Decision: {po_decision}")

        # Stage 3: Dev implements
        print("→ Dev: Implementing story...")
        monitor.check_before_agent("Dev", story_file)

        dev_result = await run_dev_agent(project_path, story_file)

        if not dev_result['success']:
            print(f"✗ Dev failed: {dev_result['error']}")
            continue

        print(f"✓ Dev completed, modified {dev_result['files_count']} files")

        # Stage 4: QA tests
        print("→ QA: Testing implementation...")
        monitor.check_before_agent("QA", story_file)

        qa_result = await run_qa_agent(project_path, story_file)

        if qa_result['status'] == 'PASS':
            print(f"✓ QA: All tests passed")
        else:
            print(f"✗ QA: Tests failed - {qa_result['failures']}")

        # ===== STORY COMPLETE =====
        # Context will be cleared before next story
```

---

## Key Differences from Previous Approach

### OLD (Minimal Context - WRONG)
```python
# Bypassed BMad workflow
context = {'story_id': 'x', 'title': 'y'}
bmad sm --context /tmp/minimal.yaml

# Result:
# - No architecture docs loaded
# - No checklist execution
# - No story file creation
# - Agents hallucinate
```

### NEW (BMad-Compliant - CORRECT)
```python
# Let BMad work as designed
bmad sm --task create-next-story

# Result:
# - SM loads core-config.yaml
# - SM loads architecture docs (50k-100k tokens)
# - SM loads epic files
# - SM creates complete story file
# - SM follows create-next-story checklist
# - Story has all context Dev needs
```

---

## Benefits of BMad-Compliant Approach

### 1. Quality Context
✅ Agents get FULL architecture context
✅ Checklists executed as designed
✅ Story files have extracted, relevant context
✅ Anti-hallucination verification works

### 2. Safety Mechanisms
✅ PO master checklist validation
✅ Template compliance checking
✅ Source citation requirements
✅ Anti-hallucination verification

### 3. Proper File Workflow
✅ Story files created in `docs/stories/`
✅ Dev updates story file (not random outputs)
✅ File List tracking works
✅ Debug logs properly linked

### 4. Token Management
✅ Context cleared between stories
✅ Story files contain distilled context
✅ Dev doesn't reload full architecture
✅ Warnings when approaching limits

---

## Implementation Checklist

- [ ] Remove minimal context YAML passing
- [ ] Call BMad agents with proper task names
- [ ] Pass story file paths between agents
- [ ] Add context clearing instructions to each agent call
- [ ] Implement token estimation and warnings
- [ ] Let agents load architecture docs as designed
- [ ] Parse story files for agent decisions
- [ ] Update story files instead of creating temp files
- [ ] Use BMad's file-based workflow
- [ ] Trust BMad's built-in safety mechanisms

---

## Next Steps

1. Rewrite automation to be BMad-compliant
2. Test with Epic 1 Story 1.1
3. Verify story file created correctly
4. Verify PO checklist executed
5. Verify Dev loads devLoadAlwaysFiles
6. Monitor token usage
7. Validate context clearing between stories

---

**CRITICAL: We are orchestrating BMad, not replacing it.**
