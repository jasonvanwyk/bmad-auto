# Epic 1 Execution Plan: Foundation, DevOps, & Core Services

## Overview

This document details exactly what will happen when you run the BMad automation on Epic 1 for the Precept POS project.

## Token Safety

### Context Window Limits
- **Agent Context Window**: 200,000 tokens
- **Max Context Passed to Agent**: 50,000 tokens (25% of window)
- **Warning Threshold**: 40,000 tokens (80% of max)

### Token Management Strategy
1. **Fresh Context Per Agent**: Each agent starts with `--new-session` flag
2. **Lightweight Handoff**: Only minimal context passed between stages
3. **Auto-Truncation**: Summaries truncated to prevent bloat
4. **Token Display**: Real-time token counts shown during execution

### Typical Token Usage Per Stage
- **SM**: Story details from YAML (~500-2,000 tokens)
- **PO**: SM summary only (~100-500 tokens)
- **Dev**: PO decision + summary (~200-600 tokens)
- **QA**: File list + dev summary (~300-800 tokens)

**Maximum handoff context**: ~5,000 tokens per stage (well under 50k limit)

---

## Epic 1 Stories

### Story 1.0: Initialize Project Scaffolding
**Status**: completed
**Action**: Will likely be skipped (already done)

### Story 1.0.1: Initialize GitHub Repository
**Status**: completed
**Action**: Will likely be skipped (already done)

### Story 1.1: Define Git Branching Strategy
**Status**: in_progress
**Action**: Will be processed by automation

### Story 1.2: Set Up CI/CD Pipeline
**Status**: pending
**Action**: Will be processed by automation

**Total Stories to Process**: 2 active stories (1.1 and 1.2)

---

## Execution Flow for Each Story

### Story 1.1: Git Branching Strategy

#### Stage 1: SM (Scrum Master) - 5 minutes max
**What happens**:
1. Reads story from `docs/epics/epic-1/stories.yaml`
2. Reviews existing docs:
   - `docs/prd.md`
   - `docs/architecture.md`
   - Existing `docs/stories/1.1.git-branching-strategy.md` (if exists)
3. Creates detailed story breakdown with tasks
4. Outputs structured plan

**Estimated tokens**: ~2,000 tokens
**Expected output**: Story plan in `/tmp/sm_create-next-story_output.md`

#### Stage 2: PO (Product Owner) - 3 minutes max
**What happens**:
1. Receives ONLY SM's summary (~500 chars)
2. Reviews against PRD and architecture
3. Validates acceptance criteria are clear:
   - Branch naming conventions documented
   - PR requirements defined
   - Branch protection rules configured
   - Commit message conventions documented
   - docs/git-workflow.md created
4. **MUST OUTPUT**: `APPROVED`, `BLOCKED`, or `CHANGES REQUESTED`

**Estimated tokens**: ~500 tokens
**Expected output**: Decision + validation notes

**If APPROVED**: Continue to Dev
**If BLOCKED**: Stop, record blockers, skip Dev/QA
**If CHANGES**: Stop, wait for human intervention

#### Stage 3: Dev (Developer) - 15 minutes max
**What happens**:
1. Receives ONLY:
   - PO decision (`APPROVED`)
   - PO summary (~500 chars)
2. Creates/modifies files:
   - `docs/git-workflow.md` - Complete branching strategy documentation
   - May update `.github/PULL_REQUEST_TEMPLATE.md`
   - May configure branch protection (instructions in docs)
3. Tracks all file modifications
4. Commits changes to git

**Estimated tokens**: ~1,000 tokens
**Expected files created/modified**:
- `docs/git-workflow.md` (new)
- Possibly `.github/` config files

**Git operations**:
- Creates feature branch (e.g., `feature/story-1.1-git-workflow`)
- Commits changes
- Does NOT push (human approval first)

#### Stage 4: QA (Quality Assurance) - 10 minutes max
**What happens**:
1. Receives ONLY:
   - List of modified files (last 10 files)
   - Dev summary (~500 chars)
2. Validates acceptance criteria:
   - ✓ docs/git-workflow.md exists and has content
   - ✓ Branch naming conventions documented
   - ✓ PR requirements defined
   - ✓ Commit conventions documented
3. May run basic validation tests
4. **MUST OUTPUT**: `PASS` or `FAIL` with test results

**Estimated tokens**: ~800 tokens
**Expected output**: Test report with PASS/FAIL per criterion

---

### Story 1.2: Set Up CI/CD Pipeline

#### Stage 1: SM - 5 minutes max
**What happens**:
1. Reads story 1.2 from YAML
2. Reviews architecture for CI/CD requirements
3. Creates detailed implementation plan
4. Breaks down into tasks

**Estimated tokens**: ~2,000 tokens

#### Stage 2: PO - 3 minutes max
**What happens**:
1. Receives SM summary
2. Validates against architecture:
   - GitHub Actions workflows specified
   - CI on PRs (lint, test, build)
   - Caching strategy defined
   - Test reporting configured
3. **MUST DECIDE**: APPROVED/BLOCKED/CHANGES

**Estimated tokens**: ~500 tokens

#### Stage 3: Dev - 15 minutes max
**What happens**:
1. Creates GitHub Actions workflows:
   - `.github/workflows/ci.yml` - Main CI pipeline
   - `.github/workflows/lint.yml` - Linting checks
   - `.github/workflows/test.yml` - Test runner
2. Configures for monorepo:
   - Turborepo integration
   - pnpm caching
   - Cargo workspace builds
3. Sets up branch protection requirements

**Estimated tokens**: ~1,000 tokens
**Expected files**:
- `.github/workflows/ci.yml` (new)
- `.github/workflows/lint.yml` (new)
- `.github/workflows/test.yml` (new)
- Documentation updates

#### Stage 4: QA - 10 minutes max
**What happens**:
1. Validates workflow files exist
2. Checks YAML syntax
3. Verifies required jobs present:
   - lint
   - test
   - build
4. Validates caching configured
5. May trigger test run

**Estimated tokens**: ~800 tokens

---

## Total Execution Estimates

### Time Estimates
- **Story 1.1**: ~33 minutes (5 + 3 + 15 + 10)
- **Story 1.2**: ~33 minutes (5 + 3 + 15 + 10)
- **Total**: ~66 minutes (~1 hour 6 minutes)

### Token Usage (Per Story)
- **SM**: ~2,000 tokens
- **PO**: ~500 tokens
- **Dev**: ~1,000 tokens
- **QA**: ~800 tokens
- **Total per story**: ~4,300 tokens

**Total for Epic 1**: ~8,600 tokens (4% of 200k limit) ✅ SAFE

---

## Validation Checkpoints

### After SM (Each Story)
- ✓ Story plan created
- ✓ Tasks clearly defined
- ✓ Acceptance criteria understood

### After PO (Each Story)
- ✓ PO explicitly APPROVED/BLOCKED/CHANGES
- ✓ If BLOCKED, blocker reasons recorded
- ✓ If APPROVED, dev can proceed

### After Dev (Each Story)
- ✓ Files actually created/modified
- ✓ Git branch created
- ✓ Changes committed locally
- ✓ File count matches expectations

### After QA (Each Story)
- ✓ Test results explicitly PASS or FAIL
- ✓ Each acceptance criterion tested
- ✓ Report generated

---

## Files That Will Be Created

### Story 1.1 Outputs
```
docs/git-workflow.md                    # Main deliverable
.github/PULL_REQUEST_TEMPLATE.md        # Possibly updated
```

### Story 1.2 Outputs
```
.github/workflows/ci.yml                # Main CI pipeline
.github/workflows/lint.yml              # Linting workflow
.github/workflows/test.yml              # Testing workflow
docs/ci-cd-setup.md                     # Documentation (possibly)
```

### System Files (Per Story)
```
.bmad-handoff-story-1.1.yaml            # Temporary (cleaned up after success)
.bmad-handoff-story-1.2.yaml            # Temporary (cleaned up after success)
.bmad-checkpoint-epic-1.yaml            # Persists for resume capability
```

---

## Failure Scenarios

### If PO Blocks Story 1.1
- **Action**: Execution stops for story 1.1
- **Dev/QA skipped**: Yes
- **Story 1.2**: Still attempted (independent)
- **Human Action Needed**: Review PO blocker reasons, address issues, re-run

### If Dev Fails Story 1.1
- **Action**: Execution stops for story 1.1
- **QA skipped**: Yes
- **Story 1.2**: Still attempted
- **Human Action Needed**: Review dev errors, may need manual intervention

### If QA Fails Story 1.1
- **Action**: Story marked as failed
- **Story 1.2**: Still attempted
- **Human Action Needed**: Review QA test results, fix issues, re-run

---

## Rollback Plan

### If Automation Goes Wrong
1. **VM Snapshot Ready**: `pre-epic-1-live` snapshot available
2. **Rollback Command** (from Proxmox host):
   ```bash
   qm rollback 500 pre-epic-1-live
   ```
3. **Local Git Reset** (if needed):
   ```bash
   git reset --hard HEAD
   git clean -fd
   ```

### If Stories Partially Complete
- **Resume capability**: Checkpoint file allows resuming from last successful story
- **Re-run with** `--resume` flag:
  ```bash
  python mvp_story_automation.py \
    --project ~/projects/precept-pos-bmad-auto \
    --epic epic-1 \
    --resume
  ```

---

## Monitoring During Execution

### Tmux Session
```bash
# Attach to watch real-time progress
tmux attach -t bmad-epic-epic-1

# Windows will show:
# - Window 0: Orchestrator (main progress)
# - Window 1: Story 1.1 execution
# - Window 2: Story 1.2 execution
```

### Console Output Shows
```
→ SM: Drafting story details...
  Context size: ~2,000 tokens
  ✓ Story drafted

→ PO: Validating story...
  Context size: ~500 tokens
  ✓ Story validated - Decision: PO decision validated

→ Dev: Implementing story...
  Context size: ~1,000 tokens
  ✓ Dev modified 2 file(s)
  ✓ Story implemented

→ QA: Testing implementation...
  Context size: ~800 tokens
  ✓ All tests passed!
```

---

## Success Criteria

### Epic 1 Considered Complete When:
1. ✅ Story 1.1: Git workflow documented, QA passed
2. ✅ Story 1.2: CI/CD pipelines created, QA passed
3. ✅ All files committed to git (local branches)
4. ✅ No validation errors
5. ✅ Checkpoint saved successfully

### You Will Have:
- Complete git workflow documentation
- GitHub Actions CI/CD pipelines
- Local feature branches ready for PR creation
- Full audit trail in checkpoint file

---

## Human Review Required After Execution

### Review Files Created
```bash
cd ~/projects/precept-pos-bmad-auto
git status
git diff main
```

### Review Each Story Output
```bash
cat docs/git-workflow.md
cat .github/workflows/ci.yml
```

### Decision Points
1. **Are the files correct?** Review for quality
2. **Ready to push?** Or need manual adjustments
3. **Create PRs?** One PR per story or combined

---

## Command to Execute

```bash
cd ~/bmad-auto
source ~/bmad-env/bin/activate

python mvp_story_automation.py \
  --project ~/projects/precept-pos-bmad-auto \
  --epic epic-1
```

**Monitor in another terminal**:
```bash
tmux attach -t bmad-epic-epic-1
```

---

## Safety Guarantees

✅ **Token limits enforced**: Max 50k tokens per agent (25% of 200k window)
✅ **Context clearing**: Fresh session each agent run
✅ **Strict validation**: PO must explicitly approve
✅ **File tracking**: All modifications logged
✅ **Rollback ready**: VM snapshot available
✅ **Resume capability**: Can continue from failures
✅ **No auto-push**: Changes stay local for review

**Ready to execute when you are!**
