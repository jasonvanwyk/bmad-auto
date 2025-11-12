# BMad Automation - Design Documentation

This directory contains the complete architectural design for the BMad Automation System.

## Overview

The BMad Automation System is a LangGraph-based orchestrator that automates the BMad Method's agent workflow (SM → PO → Dev → QA) while maintaining full compliance with BMad's design principles.

## Design Documents

### Core Architecture

1. **[architecture.md](./architecture.md)** (Coming soon)
   - System overview
   - High-level component diagram
   - Data flow
   - Integration points

### Component Specifications

2. **[orchestrator.md](./orchestrator.md)**
   - LangGraph state machine design
   - Node implementations (spawn_sm, spawn_po, spawn_dev, spawn_qa)
   - State transitions and routing
   - Error handling flows
   - **Status**: ✅ Complete

3. **[tmux-sessions.md](./tmux-sessions.md)**
   - Tmux session management
   - TmuxAgentManager class specification
   - Session lifecycle and cleanup
   - Context clearing mechanism
   - **Status**: ✅ Complete

4. **[file-communication.md](./file-communication.md)**
   - File-based communication protocol
   - StoryFileMonitor class specification
   - Completion detection strategies
   - Checkpoint management
   - **Status**: ✅ Complete

5. **[claude-code-cli.md](./claude-code-cli.md)**
   - Claude Code CLI capabilities
   - BMad agent invocation via slash commands
   - Session spawning techniques
   - Command injection methods
   - **Status**: ✅ Complete

### Implementation Guide

6. **[implementation-roadmap.md](./implementation-roadmap.md)**
   - 5-phase implementation plan
   - Phase 1 (MVP): Single story processing
   - Phase 2: Full agent pipeline
   - Phase 3: Epic processing with checkpoints
   - Phase 4: Robustness & error handling
   - Phase 5: Advanced features
   - **Status**: ✅ Complete

## Key Architectural Decisions

### 1. File-Based Communication
**Decision**: Use file system monitoring instead of stdout parsing

**Rationale**:
- BMad agents naturally update story files
- File changes are atomic and persistent
- Easier to debug and inspect
- Full audit trail in git

### 2. Tmux for Session Isolation
**Decision**: Run each agent in isolated tmux session

**Rationale**:
- Fresh Claude Code instance per agent
- Context automatically cleared on session kill
- Can attach to sessions for live monitoring
- Process isolation prevents state leakage

### 3. LangGraph for Orchestration
**Decision**: Use LangGraph state machine for workflow control

**Rationale**:
- Explicit state transitions
- Built-in error handling and routing
- Visualizable workflow
- Easy to extend with new nodes/edges

### 4. BMad Compliance
**Decision**: Invoke BMad agents via slash commands, not custom prompts

**Rationale**:
- Agents load full context (architecture docs, checklists, tasks)
- Anti-hallucination verification works as designed
- PO master checklist executed properly
- Story files created/updated as intended

## Design Principles

1. **Respect BMad's Design**
   - Don't bypass BMad's workflows
   - Let agents load full context
   - Use story files as designed

2. **Context Safety**
   - Fresh session per agent
   - No context accumulation
   - Token limits respected

3. **Debuggability**
   - File-based communication is inspectable
   - Can attach to tmux sessions anytime
   - Full logging of operations

4. **Resilience**
   - Checkpoint/resume capability
   - Timeout handling
   - Human escalation for blockers

5. **Testability**
   - Each component unit-testable
   - Integration tests for workflows
   - Mock file system for testing

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│  LangGraph Orchestrator (Master Process)                │
│  ┌─────────────────────────────────────────────────┐   │
│  │ State: StoryState                               │   │
│  │ - story_id, current_stage, po_decision, etc.   │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────┐   ┌─────────┐   ┌──────────┐   ┌──────┐ │
│  │spawn_sm │→→→│spawn_po │→→→│spawn_dev │→→→│spawn_│ │
│  │         │   │         │   │          │   │  qa  │ │
│  └────┬────┘   └────┬────┘   └────┬─────┘   └──┬───┘ │
└───────┼─────────────┼──────────────┼─────────────┼─────┘
        ↓             ↓              ↓             ↓
┌───────────────────────────────────────────────────────┐
│  TmuxAgentManager                                     │
│  - Creates isolated sessions                          │
│  - Injects commands: /sm *create, /po *validate, etc.│
│  - Monitors session health                            │
└───────┬───────────────┬──────────────┬────────────┬───┘
        ↓               ↓              ↓            ↓
  ┌──────────┐    ┌──────────┐  ┌──────────┐  ┌────────┐
  │bmad-sm   │    │bmad-po   │  │bmad-dev  │  │bmad-qa │
  │  1-1     │    │  1-1     │  │  1-1     │  │  1-1   │
  └────┬─────┘    └────┬─────┘  └────┬─────┘  └───┬────┘
       │               │             │            │
       ↓               ↓             ↓            ↓
  ┌────────────────────────────────────────────────────┐
  │  Claude Code Instances                             │
  │  - Loads BMad agents via slash commands            │
  │  - Full context: architecture docs, checklists     │
  │  - Updates story files                             │
  └────────┬───────────────────────────────────────────┘
           ↓
  ┌────────────────────────────────────────────────────┐
  │  File System (Communication Layer)                 │
  │  - docs/stories/{epic}.{story}.story.md            │
  │  - .bmad-checkpoint-{epic}.yaml                    │
  └────────┬───────────────────────────────────────────┘
           ↓
  ┌────────────────────────────────────────────────────┐
  │  StoryFileMonitor                                  │
  │  - Detects file changes                            │
  │  - Parses status (PO decision, QA results, etc.)   │
  │  - Notifies orchestrator of completion             │
  └────────────────────────────────────────────────────┘
```

## Getting Started

1. Read [implementation-roadmap.md](./implementation-roadmap.md) for implementation phases
2. Review [orchestrator.md](./orchestrator.md) for state machine design
3. Study [tmux-sessions.md](./tmux-sessions.md) for session management
4. Understand [file-communication.md](./file-communication.md) for monitoring
5. Check [claude-code-cli.md](./claude-code-cli.md) for CLI invocation

## Status

- **Design Phase**: ✅ Complete
- **Implementation Phase**: Phase 1 (MVP) ready to begin
- **Testing Phase**: Not started
- **Production Deployment**: Not started

## Related Documents

- **Learning Journey**: See `docs/archive/learning-journey/` for design evolution
- **Obsolete Code**: See `docs/archive/obsolete-code/` for previous implementation attempts

---

**Last Updated**: 2024-11-12
**Version**: 1.0 (Complete Design)
**Status**: Ready for Implementation
