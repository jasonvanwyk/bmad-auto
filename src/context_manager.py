"""
context_manager.py - Lightweight context management for agent handoffs

Prevents context bloat while maintaining necessary continuity between agents.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class StoryHandoff:
    """
    Manages lightweight context handoffs between agents.
    Ensures context stays focused and doesn't bloat.
    """

    MAX_SUMMARY_LENGTH = 2000  # characters
    MAX_ACCEPTANCE_CRITERIA = 10  # items
    MAX_FILES_TRACKED = 20  # files

    def __init__(self, story_id: str, project_path: Path):
        self.story_id = story_id
        self.project_path = project_path
        self.handoff_file = project_path / f".bmad-handoff-{story_id}.yaml"
        self.data = self._initialize()

    def _initialize(self) -> Dict:
        """Initialize or load handoff data."""
        if self.handoff_file.exists():
            with open(self.handoff_file, 'r') as f:
                return yaml.safe_load(f) or {}

        return {
            'story_id': self.story_id,
            'created_at': datetime.now().isoformat(),
            'stages': {},
            'files_modified': [],
            'decisions': [],
            'blockers': []
        }

    def add_stage_summary(self, stage: str, summary: str, decision: Optional[str] = None):
        """
        Add a stage summary with automatic truncation.

        Args:
            stage: Agent stage (sm, po, dev, qa)
            summary: Brief summary of what was done (auto-truncated)
            decision: Explicit decision (APPROVED, BLOCKED, etc.)
        """
        # Truncate summary if too long
        if len(summary) > self.MAX_SUMMARY_LENGTH:
            summary = summary[:self.MAX_SUMMARY_LENGTH] + "... [truncated]"

        self.data['stages'][stage] = {
            'summary': summary,
            'decision': decision,
            'timestamp': datetime.now().isoformat()
        }

        if decision:
            self.data['decisions'].append({
                'stage': stage,
                'decision': decision,
                'timestamp': datetime.now().isoformat()
            })

        self._save()

    def add_file_modified(self, file_path: str, action: str = "modified"):
        """Track files modified, with limit to prevent bloat."""
        file_entry = {
            'path': file_path,
            'action': action,
            'timestamp': datetime.now().isoformat()
        }

        self.data['files_modified'].append(file_entry)

        # Keep only recent files if exceeding limit
        if len(self.data['files_modified']) > self.MAX_FILES_TRACKED:
            self.data['files_modified'] = self.data['files_modified'][-self.MAX_FILES_TRACKED:]

        self._save()

    def add_blocker(self, blocker: str, stage: str):
        """Add a blocker issue."""
        self.data['blockers'].append({
            'blocker': blocker,
            'stage': stage,
            'timestamp': datetime.now().isoformat()
        })
        self._save()

    def get_context_for_stage(self, stage: str) -> Dict:
        """
        Get minimal context needed for next stage.
        Returns only essential information to prevent bloat.
        """
        context = {
            'story_id': self.story_id,
            'previous_stages': {}
        }

        # Stage-specific context
        if stage == 'po':
            # PO needs SM's story definition
            if 'sm' in self.data['stages']:
                context['previous_stages']['sm'] = {
                    'summary': self.data['stages']['sm']['summary']
                }

        elif stage == 'dev':
            # Dev needs PO approval status and any guidance
            if 'po' in self.data['stages']:
                po_stage = self.data['stages']['po']
                context['previous_stages']['po'] = {
                    'decision': po_stage.get('decision'),
                    'summary': po_stage['summary'][:500]  # Truncated
                }

        elif stage == 'qa':
            # QA needs list of modified files and dev summary
            if 'dev' in self.data['stages']:
                context['previous_stages']['dev'] = {
                    'summary': self.data['stages']['dev']['summary'][:500]
                }
            context['files_modified'] = [
                f['path'] for f in self.data['files_modified'][-10:]  # Last 10 files only
            ]

        # Always include current blockers (if any)
        if self.data['blockers']:
            context['blockers'] = self.data['blockers'][-3:]  # Last 3 blockers only

        return context

    def validate_po_decision(self) -> tuple[bool, str]:
        """
        Validate that PO made an explicit decision.

        Returns:
            (is_valid, message)
        """
        if 'po' not in self.data['stages']:
            return False, "PO stage not completed"

        po_stage = self.data['stages']['po']
        decision = po_stage.get('decision', '').upper()

        if decision not in ['APPROVED', 'BLOCKED', 'CHANGES_REQUESTED']:
            return False, f"PO must explicitly APPROVE, BLOCK, or request CHANGES. Got: {decision or 'NO DECISION'}"

        if decision == 'BLOCKED' and not self.data['blockers']:
            return False, "PO BLOCKED but provided no blocker reasons"

        return True, decision

    def get_summary(self) -> str:
        """Get a brief summary of the handoff state."""
        stages_completed = list(self.data['stages'].keys())
        files_count = len(self.data['files_modified'])
        blockers_count = len(self.data['blockers'])

        summary = f"Story {self.story_id}:\n"
        summary += f"  Stages: {' → '.join(stages_completed)}\n"
        summary += f"  Files modified: {files_count}\n"

        if blockers_count > 0:
            summary += f"  ⚠ Blockers: {blockers_count}\n"

        # Show latest decision
        if self.data['decisions']:
            latest = self.data['decisions'][-1]
            summary += f"  Latest: {latest['stage'].upper()} - {latest['decision']}\n"

        return summary

    def _save(self):
        """Save handoff data to file."""
        with open(self.handoff_file, 'w') as f:
            yaml.dump(self.data, f, default_flow_style=False, sort_keys=False)

    def cleanup(self):
        """Remove handoff file after story completion."""
        if self.handoff_file.exists():
            self.handoff_file.unlink()


class AgentValidator:
    """Validates agent outputs to ensure quality and completeness."""

    @staticmethod
    def validate_po_output(output: str, handoff: StoryHandoff) -> tuple[bool, str]:
        """
        Strictly validate PO output for explicit approval/blocking.

        Returns:
            (is_valid, message)
        """
        output_upper = output.upper()

        # Check for explicit decision markers
        has_approved = 'APPROVED' in output_upper or 'APPROVE' in output_upper
        has_blocked = 'BLOCKED' in output_upper or 'BLOCK' in output_upper
        has_changes = 'CHANGES REQUESTED' in output_upper or 'CHANGE REQUEST' in output_upper

        if not (has_approved or has_blocked or has_changes):
            return False, "PO output must contain explicit APPROVED, BLOCKED, or CHANGES REQUESTED"

        # Check handoff file has decision
        is_valid, msg = handoff.validate_po_decision()
        if not is_valid:
            return False, f"PO handoff validation failed: {msg}"

        return True, "PO decision validated"

    @staticmethod
    def validate_dev_output(output: str, handoff: StoryHandoff) -> tuple[bool, str]:
        """
        Validate Dev output has actual file changes.

        Returns:
            (is_valid, message)
        """
        if not handoff.data['files_modified']:
            return False, "Dev completed but no files were modified"

        return True, f"Dev modified {len(handoff.data['files_modified'])} file(s)"

    @staticmethod
    def validate_qa_output(output: str, handoff: StoryHandoff) -> tuple[bool, str]:
        """
        Validate QA output has test results.

        Returns:
            (is_valid, message)
        """
        output_upper = output.upper()

        has_pass = 'PASS' in output_upper or 'SUCCESS' in output_upper
        has_fail = 'FAIL' in output_upper or 'ERROR' in output_upper

        if not (has_pass or has_fail):
            return False, "QA output must contain explicit PASS/FAIL test results"

        return True, "QA results validated"
