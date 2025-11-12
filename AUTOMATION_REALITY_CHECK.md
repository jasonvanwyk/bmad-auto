# Automation vs BMad Reality Check

## Critical Discovery: BMad is IDE-Based, Not CLI-Based

After examining BMad's architecture, I've discovered a fundamental compatibility issue between full automation and BMad's design.

---

## How BMad Actually Works

### BMad is an IDE Integration
```
You in IDE → @sm → Claude loads SM agent persona + tasks → Executes interactively
             @po → Claude loads PO agent persona + checklist → Validates interactively
             @dev → Claude loads Dev agent persona + story → Implements interactively
             @qa → Claude loads QA agent persona + tests → Tests interactively
```

**NOT a CLI tool**: BMad has no `bmad` command-line interface. It's integrated into:
- Claude Code (via `.claude/` config)
- Windsurf/OpenCode (via `opencode.jsonc`)
- Cursor (via configuration)

### How Agents Are Invoked
```markdown
# In IDE chat:
@sm *create           # SM creates next story
@po *validate         # PO validates story draft
@dev *develop-story   # Dev implements story
@qa *test            # QA tests implementation
```

**Each @ mention**:
1. Loads agent persona from `.bmad-core/agents/{agent}.md`
2. Loads tasks from `.bmad-core/tasks/`
3. Loads checklists from `.bmad-core/checklists/`
4. Has full IDE context (can read/write files)
5. Interacts with YOU for decisions

---

## The Automation Dilemma

### What You Want (Ideal)
```
Run automation → SM drafts → PO validates → Dev implements → QA tests
                 (fully automated, high quality, BMad-compliant)
```

### What's Possible

#### Option 1: Semi-Automated (RECOMMENDED)
**Automation orchestrates, BMad executes, You approve**

```python
# Automation guides the workflow
for story in epic:
    print("→ Next: Run @sm *create in Claude Code")
    wait_for_user_approval()

    print("→ Next: Run @po *validate on story file")
    wait_for_user_approval()

    print("→ Next: Run @dev *develop-story")
    wait_for_user_approval()

    print("→ Next: Run @qa *test")
    wait_for_user_approval()
```

**Pros**:
✅ Uses BMad's full capabilities (checklists, tasks, validations)
✅ Full quality context (architecture docs, PRD, etc.)
✅ You approve each stage
✅ BMad's safety mechanisms intact

**Cons**:
❌ Not fully automated (requires your interaction)
❌ You need to manually @ mention each agent

#### Option 2: Custom Agent Prompts (What We Built)
**Full automation with custom prompts that mimic BMad**

```python
# Our automation loads files and prompts Claude directly
claude.send(
    role="SM",
    context=load_architecture_docs() + load_prd() + load_epic(),
    prompt="Create story file for {story_id}. Load all relevant docs as BMad SM would."
)
```

**Pros**:
✅ Fully automated
✅ Can load architecture docs ourselves
✅ Can implement quality context loading
✅ Context clearing between stories

**Cons**:
❌ Bypasses BMad's built-in checklists
❌ Bypasses BMad's task workflows
❌ We have to reimplement BMad's logic
❌ Loses BMad's safety mechanisms
❌ Not using BMad at all (just custom automation)

#### Option 3: Hybrid Approach (PRACTICAL)
**Automation handles document loading, agents work interactively**

```python
# Automation prepares context files for each agent
prepare_sm_context(story_id)  # Loads arch docs, epic, previous story
# → Outputs: /tmp/sm-context-{story}.md

# Then YOU run:
# @sm, here's your context: /tmp/sm-context-1.1.md
# Please create story file following create-next-story task

# Automation validates output
check_story_file_created()

# Repeat for PO, Dev, QA
```

**Pros**:
✅ Automation handles heavy lifting (file loading, context prep)
✅ BMad agents execute with full context
✅ You stay in control
✅ Maintains quality
✅ Uses BMad as designed

**Cons**:
❌ Still requires manual @ mentions
❌ Not fully hands-off

---

## The Real Question

**Do you want:**

### A) Full Automation (No BMad)
- Custom agent prompts
- We load docs ourselves
- No checklists/tasks
- Faster but less validated
- **This is what our current automation does**

### B) BMad-Compliant Semi-Automation (Recommended)
- Automation guides workflow
- You run @ mentions in Claude Code
- BMad's full quality checks
- Interactive but thorough
- **This respects BMad's design**

### C) Hybrid (Best of Both)
- Automation prepares contexts
- You invoke BMad agents with prepared context
- Gets quality AND efficiency
- **Requires some manual steps**

---

## My Honest Recommendation

**For Epic 1 (Foundation stories)**: Option B or C

**Why?**
1. Foundation is CRITICAL - needs BMad's validation
2. Git workflow, CI/CD setup must be right
3. BMad's checklists catch issues we'd miss
4. Only 4 stories - manual @ mentions are manageable

**For Later Epics (Feature stories)**: Could use Option A
1. Foundation is solid
2. Repetitive feature work
3. Full automation saves time
4. Less critical if minor issues

---

## Specific Recommendations for Epic 1

### Story 1.1: Git Branching Strategy

**Manual BMad Workflow** (20-30 min total):
```
1. You: @sm *create
   - SM loads architecture, creates story file
   - You review story file

2. You: @po *validate
   - PO loads checklist, validates story
   - You review PO decision

3. You: @dev *develop-story
   - Dev implements git workflow docs
   - You review output

4. You: @qa *test
   - QA validates implementation
   - You review test results
```

**With Automation Helper** (We provide):
```python
# Script tells you exactly what to do next
python bmad_workflow_guide.py --project precept-pos --epic epic-1

# Output:
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Story 1.1: Git Branching Strategy
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# STEP 1: Create Story
# In Claude Code, run: @sm *create
# Expected output: docs/stories/1.1.git-branching-strategy.md
#
# [Press Enter when done]
#
# STEP 2: Validate Story
# In Claude Code, run: @po *validate
# PO will load po-master-checklist and validate
# Expected: PO explicitly APPROVES story
#
# [Press Enter when done]
#
# STEP 3: Implement Story
# In Claude Code, run: @dev *develop-story
# Dev will create docs/git-workflow.md
#
# [Press Enter when done]
#
# STEP 4: Test Implementation
# In Claude Code, run: @qa *test
# QA will validate against acceptance criteria
#
# [Press Enter when done]
#
# ✓ Story 1.1 Complete!
# Next: Story 1.2 (CI/CD Pipeline)
```

---

## What I Can Build For You

### Option 1: Workflow Guide (Recommended for Epic 1)
```python
# Interactive guide that tells you what to do
python bmad_workflow_guide.py
# Tracks progress, validates outputs, guides you through BMad workflow
```

### Option 2: Full Custom Automation (For later epics)
```python
# What we already built - bypasses BMad
python mvp_story_automation.py --epic epic-2
# Fully automated but doesn't use BMad's checklists
```

### Option 3: Context Preparer (Hybrid)
```python
# Prepares context files for each BMad agent
python bmad_context_prep.py --story 1.1 --agent sm
# Outputs: context file you give to @sm
```

---

## Recommendation for Right Now

Given that:
1. You have Epic 1 ready (foundation stories)
2. These are CRITICAL setup stories
3. BMad's validation is valuable here
4. Only 4 stories total

**I recommend**:

**Use BMad manually for Epic 1 with our workflow guide**

1. I'll create an interactive guide script
2. It tells you exactly what @ mention to run
3. It validates outputs between stages
4. You get BMad's full quality checks
5. Takes ~1-2 hours for all 4 stories

**Then for Epic 2+**: We can discuss full automation

---

## The Question

**Which approach do you want for Epic 1?**

A) **Workflow Guide** - I build interactive guide, you run @ mentions manually
B) **Full Automation** - Use our existing system, bypass BMad
C) **Hybrid** - I prep contexts, you run BMad agents with them
D) **Something else** - Tell me what you're thinking

**For Epic 1's foundation stories, I strongly lean toward Option A** - it's the right balance of automation (guiding) and quality (BMad's validation).

What do you think?
