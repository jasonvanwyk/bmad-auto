# BMad Automation System - Vision & Implementation Plan

## Executive Summary

This document outlines a comprehensive automation system for the BMad Method, specifically targeting the repetitive development phase of software projects. The system automates the Story Writing → Validation → Development → QA cycle while preserving human control over strategic planning decisions.

## Table of Contents

1. [Vision & Problem Statement](#vision--problem-statement)
2. [System Architecture](#system-architecture)
3. [Implementation Strategy](#implementation-strategy)
4. [Safety & Testing Environment](#safety--testing-environment)
5. [MVP Implementation](#mvp-implementation)
6. [Roadmap](#roadmap)
7. [Quick Start Guide](#quick-start-guide)

---

## Vision & Problem Statement

### Current Pain Points
- **Manual Sequential Execution**: Running SM → PO → Dev → QA agents one at a time is tedious
- **Context Switching**: Constantly monitoring and triggering next agent in sequence
- **No Parallelization**: Stories processed one at a time despite independence
- **Lack of Visibility**: No unified view of epic progress across multiple stories

### The Solution
An intelligent orchestration layer that automates the BMad development phase while maintaining human oversight for critical decisions. The system focuses exclusively on the repetitive development cycles, respecting that strategic planning requires human vision and creativity.

### Key Principles
1. **Automate the Mechanical, Preserve the Creative**: Planning stays human-driven, execution becomes automated
2. **Safety First**: All testing in isolated VM environments with snapshot/rollback capability
3. **Human-in-the-Loop**: Intelligent escalation for anomalies and critical decisions
4. **Progressive Enhancement**: Start simple (MVP), add sophistication gradually
5. **Observable & Auditable**: Full visibility through tmux sessions and comprehensive logging

---

## System Architecture

### Scope Definition

```yaml
# HUMAN-DRIVEN (Not Automated)
Planning Phase:
  - Project Brief (Vision & Goals)
  - PRD Creation (Requirements)
  - Architecture Design (Technical Decisions)
  - Epic Planning & Story Sharding
  Output: → Sharded story files ready for development

# AUTOMATED (Our System)
Development Phase:
  For each story (1 to N):
    - SM: Draft detailed story specifications
    - PO: Validate story alignment
    - Dev: Implement code and tests
    - QA: Verify implementation
    - Loop: Handle failures with retry logic
  Output: → Tested code ready for merge
```

### Core Components

#### 1. Master Orchestrator (LangGraph-based)
- Manages story state transitions
- Coordinates agent execution
- Handles parallel story processing
- Implements retry and failure recovery logic

#### 2. Tmux Session Manager
- Provides persistent execution environment
- Visual monitoring of parallel agent execution
- Session recovery after disconnection
- Organized window/pane structure per story

#### 3. Human-in-the-Loop (HITL) System
- Intelligent escalation triggers
- Multi-channel notifications (terminal, desktop, sound)
- Interactive decision interface
- Learning from past decisions

#### 4. Safety Wrapper
- Command validation and sandboxing
- Resource limits (CPU, memory, disk)
- Protected path enforcement
- Dangerous operation blocking

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Proxmox VM Environment                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Master Orchestrator                     │    │
│  │         (LangGraph State Machine)                   │    │
│  └──────────────────┬───────────────────────────────────┘    │
│                     │                                        │
│  ┌──────────────────┴───────────────────────────────────┐   │
│  │                                                       │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │   │
│  │  │ Tmux Session │  │ HITL System  │  │  Safety    │ │   │
│  │  │   Manager    │  │              │  │  Wrapper   │ │   │
│  │  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘ │   │
│  │         │                  │                 │        │   │
│  └─────────┼──────────────────┼─────────────────┼────────┘   │
│            │                  │                 │            │
│  ┌─────────▼──────────────────▼─────────────────▼────────┐   │
│  │                  Agent Execution Layer                 │   │
│  ├────────────────────────────────────────────────────────┤   │
│  │                                                        │   │
│  │  Story 1 Worktree    Story 2 Worktree    Story N ...  │   │
│  │  ┌─────────────┐     ┌─────────────┐    ┌──────────┐ │   │
│  │  │ SM → PO →   │     │ SM → PO →   │    │ SM → PO  │ │   │
│  │  │ Dev → QA    │     │ Dev → QA    │    │ Dev → QA │ │   │
│  │  └─────────────┘     └─────────────┘    └──────────┘ │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

---

## Implementation Strategy

### Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Orchestration | LangGraph | State machine for complex agent flows |
| Agent Framework | BMad Method | Existing agent definitions and workflows |
| Session Management | Tmux + libtmux | Persistent, observable execution |
| VM Platform | Proxmox | Enterprise virtualization with snapshot support |
| Language | Python 3.10+ | Rich ecosystem, async support |
| UI/Dashboard | Rich + Click | Terminal-based for SSH compatibility |
| Version Control | Git Worktrees | Parallel story development |
| Communication | MCP (future) | Standardized agent communication |

### Git Worktree Strategy

```bash
project/
├── main/                     # Protected main branch
├── epic-1-orchestrator/      # Orchestrator's workspace
└── stories/
    ├── story-1-dev/         # Isolated development
    ├── story-2-dev/         # Parallel story work
    └── story-3-qa/          # Story in QA phase
```

### State Management

```python
# Story State Definition
class StoryState(TypedDict):
    story_id: str
    epic_id: str
    status: Literal['pending', 'drafting', 'validating',
                   'developing', 'testing', 'complete', 'failed']
    current_agent: str
    worktree_path: Optional[str]
    attempts: int
    confidence: float
    human_interventions: List[Dict]
    execution_log: List[Dict]
```

---

## Safety & Testing Environment

### Proxmox VM Configuration

```bash
# VM Specifications
VM_ID: 500
VM_NAME: bmad-automation-test
Resources:
  - CPU: 4 cores
  - RAM: 8GB
  - Disk: 50GB
  - Network: Isolated VLAN (optional)

# Safety Features
- Snapshot before each test run
- Resource limits enforced
- Isolated user (bmad-test)
- Command sandboxing
- Protected system paths
```

### VM Provisioning Script

```bash
#!/bin/bash
# Core installations
apt update && apt upgrade -y
apt install -y python3-pip nodejs npm tmux git

# Python environment
python3 -m venv /opt/bmad-env
source /opt/bmad-env/bin/activate
pip install langgraph langchain libtmux rich click pyyaml

# BMad installation
npx bmad-method@alpha install

# Safety user
useradd -m -s /bin/bash bmad-test
# ... [full script in implementation]
```

### Safety Constraints

```python
class SafetyConstraints:
    BLOCKED_COMMANDS = [
        r'rm\s+-rf\s+/',       # No root deletion
        r':()\{:|:&\};:',      # No fork bombs
        r'curl.*\|.*sh',       # No curl to shell
    ]

    PROTECTED_PATHS = [
        '/etc', '/boot', '/sys', '/proc'
    ]

    RESOURCE_LIMITS = {
        'cpu_seconds': 300,
        'memory_mb': 1024,
        'disk_mb': 500
    }
```

---

## MVP Implementation

### Minimal Viable Product - Story Development Focus

```python
#!/usr/bin/env python3
"""
mvp_story_automation.py - Minimal BMad story automation
Focuses only on: SM → PO → Dev → QA cycle
"""

import asyncio
from pathlib import Path
import yaml
import libtmux
from rich.console import Console

class StoryDevelopmentMVP:
    def __init__(self, project_path: str, epic_id: str):
        self.project_path = Path(project_path)
        self.epic_id = epic_id
        self.console = Console()

        # Verify prerequisites
        self.verify_planning_complete()
        self.stories = self.load_stories()

    def verify_planning_complete(self):
        """Ensure planning artifacts exist"""
        required = [
            self.project_path / "docs/prd.md",
            self.project_path / "docs/architecture.md",
            self.project_path / f"docs/epics/{self.epic_id}/stories.yaml"
        ]
        for file in required:
            if not file.exists():
                raise ValueError(f"Missing: {file}")

    async def run_story_cycle(self, story: Dict):
        """Execute single story through development cycle"""
        story_id = story['id']

        # SM Draft
        sm_result = await self.execute_agent('sm', 'create-next-story', story)
        if not sm_result['success']:
            return sm_result

        # PO Validation
        po_result = await self.execute_agent('po', 'validate-story',
                                            sm_result['output_file'])

        # Dev Implementation
        dev_result = await self.execute_agent('dev', 'implement-story',
                                             sm_result['output_file'])

        # QA Testing
        qa_result = await self.execute_agent('qa', 'test-story',
                                            dev_result['output_path'])

        return {
            'story_id': story_id,
            'success': qa_result['success'],
            'stages': {
                'sm': sm_result,
                'po': po_result,
                'dev': dev_result,
                'qa': qa_result
            }
        }
```

### Expected Project Structure

```
test-project/
├── docs/
│   ├── prd.md                    # Human-created
│   ├── architecture.md           # Human-created
│   └── epics/
│       └── epic-1/
│           └── stories.yaml      # Human-created (sharded stories)
├── src/                          # Dev agent writes here
├── tests/                        # QA agent writes here
└── .bmad-config.yaml            # BMad configuration
```

### Sample Stories File

```yaml
# docs/epics/epic-1/stories.yaml
epic_id: epic-1
title: "User Authentication System"
stories:
  - id: story-1
    title: "User Registration"
    acceptance_criteria:
      - User can register with email/password
      - Email validation is performed
      - Password meets security requirements
    technical_notes: "Use bcrypt for password hashing"

  - id: story-2
    title: "User Login"
    acceptance_criteria:
      - User can login with credentials
      - Session token is generated
      - Failed attempts are rate-limited
```

---

## Human-in-the-Loop Integration

### Escalation Triggers

```python
class InterventionType(Enum):
    AGENT_STUCK = "agent_stuck"          # Can't proceed
    QA_FAILURE = "qa_failure"           # Multiple failures
    ANOMALY_DETECTED = "anomaly"        # Unexpected output
    LOW_CONFIDENCE = "low_confidence"   # Agent uncertainty
    TIMEOUT = "timeout"                 # Execution timeout
    COST_THRESHOLD = "cost"            # API cost limit

# Escalation Rules
ESCALATION_RULES = {
    'max_retries': 3,
    'qa_failure_threshold': 2,
    'confidence_threshold': 0.7,
    'timeout_seconds': 900,
    'cost_limit_dollars': 10.0,
    'anomaly_keywords': ['error', 'failed', 'unclear', 'ambiguous']
}
```

### Decision Interface

```python
async def request_human_decision(intervention_type, context):
    """Interactive CLI for human decisions"""

    # Display context
    console.print(Panel(
        f"🚨 Human Decision Required\n"
        f"Type: {intervention_type}\n"
        f"Story: {context['story_id']}\n"
        f"Agent: {context['agent']}\n"
        f"Issue: {context['error']}"
    ))

    # Suggest actions
    suggestions = generate_suggestions(intervention_type, context)
    for i, suggestion in enumerate(suggestions, 1):
        console.print(f"{i}. {suggestion}")

    # Get decision
    choice = Prompt.ask("Your decision",
                       choices=['1', '2', '3', 'custom', 'skip'])

    return process_decision(choice, suggestions)
```

---

## Roadmap

### Phase 1: Foundation (Week 1)
- [x] Design system architecture
- [x] Define scope and constraints
- [ ] Setup Proxmox VM
- [ ] Install dependencies
- [ ] Create MVP script
- [ ] Test with single story

### Phase 2: Core Features (Week 2)
- [ ] Implement tmux session management
- [ ] Add basic HITL for errors
- [ ] Create checkpoint/resume capability
- [ ] Add parallel story execution (2-3 stories)
- [ ] Implement retry logic

### Phase 3: Enhancement (Week 3)
- [ ] Integrate LangGraph orchestration
- [ ] Add git worktree isolation
- [ ] Implement monitoring dashboard
- [ ] Create comprehensive logging
- [ ] Add cost tracking

### Phase 4: Production (Week 4)
- [ ] Add MCP server communication
- [ ] Implement CI/CD integration
- [ ] Create operational documentation
- [ ] Setup automated testing
- [ ] Performance optimization

### Future Enhancements
- [ ] Web UI dashboard (FastAPI + HTMX)
- [ ] Slack/Discord notifications
- [ ] Multi-epic orchestration
- [ ] A/B testing different agent strategies
- [ ] ML-based decision learning

---

## Quick Start Guide

### 1. Create Proxmox VM

```bash
# On Proxmox host
qm create 500 \
  --name bmad-automation-test \
  --memory 8192 \
  --cores 4 \
  --net0 virtio,bridge=vmbr0 \
  --scsi0 local-lvm:50

# Install Ubuntu 22.04
# Run provisioning script after installation
```

### 2. Provision VM

```bash
# SSH into VM
ssh root@<vm-ip>

# Download and run provisioning
wget https://your-repo/provision_bmad_vm.sh
bash provision_bmad_vm.sh

# Create snapshot
qm snapshot 500 initial_setup
```

### 3. Prepare Test Project

```bash
# As bmad-test user
su - bmad-test
cd ~/projects

# Clone or create test project
git clone <your-test-project>
cd test-project

# Verify planning phase complete
ls -la docs/epics/epic-1/stories.yaml
```

### 4. Run MVP

```bash
# Take pre-test snapshot (from Proxmox)
qm snapshot 500 pre_mvp_test

# Run automation (in VM)
python3 ~/automation/mvp_story_automation.py \
  --project . \
  --epic epic-1 \
  --vm-check

# Monitor in tmux
tmux attach -t epic-epic-1
```

### 5. Monitor & Control

```bash
# View all tmux sessions
tmux ls

# Attach to specific story
tmux attach -t epic-epic-1
# Navigate: Ctrl-b, w (window list)
#          Ctrl-b, n/p (next/previous)

# Check logs
tail -f ~/logs/epic-1.log

# Emergency stop
Ctrl-C in orchestrator window
```

### 6. Rollback if Needed

```bash
# List snapshots (from Proxmox)
qm listsnapshot 500

# Rollback to snapshot
qm rollback 500 pre_mvp_test
```

---

## Configuration Files

### bmad_automation_config.yaml

```yaml
automation:
  mode: supervised  # auto, supervised, manual
  parallel_stories: 3
  max_retries: 3

tmux:
  session_prefix: bmad-epic
  keep_alive_on_error: true

hitl:
  notification_channels: [terminal, desktop]
  escalation_thresholds:
    agent_timeout: 900
    confidence_minimum: 0.7
    qa_failure_max: 2

agents:
  models:
    sm: haiku
    po: haiku
    dev: sonnet
    qa: haiku

safety:
  vm_check: true
  command_validation: true
  resource_limits: true
  snapshot_on_start: true
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Story Success Rate | >80% | QA pass on first attempt |
| Human Interventions | <20% | Interventions per story |
| Time per Story | <30 min | End-to-end cycle time |
| Parallel Efficiency | >2.5x | vs. sequential execution |
| Cost per Story | <$0.50 | API usage costs |

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Agent timeout | Increase timeout in config, check VM resources |
| Git conflicts | Ensure worktree isolation, check branch strategy |
| QA loops | Review test criteria, add retry limits |
| Tmux disconnection | Use `tmux attach` to reconnect |
| VM performance | Increase CPU/RAM allocation |

### Emergency Procedures

```bash
# Stop all automation
pkill -f bmad_automation

# Kill tmux session
tmux kill-session -t epic-<id>

# Rollback VM
qm rollback 500 <snapshot>

# Clean up worktrees
git worktree prune
```

---

## Conclusion

This BMad automation system represents a practical solution to the tedium of sequential agent execution while maintaining the human creativity and oversight essential for successful software development. By focusing exclusively on the mechanical development phase and implementing robust safety measures, we create a system that is both powerful and safe to experiment with.

The key insight is recognizing that not all phases of development benefit equally from automation. Strategic planning requires human vision, but the implementation cycle follows predictable patterns perfect for automation. This system respects that distinction while dramatically improving developer productivity.

---

## Appendix

### A. Full Code Examples
[Complete implementation files available in repository]

### B. BMad Agent Reference
[Links to BMad documentation and agent specifications]

### C. Proxmox Commands Reference
[Common Proxmox CLI commands for VM management]

### D. Git Worktree Commands
[Reference for git worktree operations]

---

*Document Version: 1.0*
*Last Updated: November 2024*
*Author: BMad Automation Team*