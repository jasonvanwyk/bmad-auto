#!/usr/bin/env python3
"""
hitl_interface.py - Human-in-the-Loop interface for BMad automation

Provides intelligent escalation, notification, and decision-making interface
for handling anomalies and critical decisions during automation.
"""

import asyncio
import json
import subprocess
import platform
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from pathlib import Path
import re

import click
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.layout import Layout
from rich.live import Live
from rich import print as rprint


class InterventionType(Enum):
    """Types of human interventions"""
    AGENT_STUCK = "agent_stuck"           # Agent can't proceed
    QA_FAILURE = "qa_failure"            # Repeated QA failures
    VALIDATION_CONFLICT = "validation"    # PO/Architect disagree
    ANOMALY_DETECTED = "anomaly"         # Unexpected output
    RESOURCE_LIMIT = "resource"          # Cost/time threshold
    MERGE_CONFLICT = "merge_conflict"    # Git conflicts
    CRITICAL_DECISION = "critical"       # Architecture choices
    AMBIGUOUS_REQUIREMENT = "ambiguous"  # Unclear story req
    LOW_CONFIDENCE = "confidence"        # Agent uncertainty
    TIMEOUT = "timeout"                  # Execution timeout


class NotificationLevel(Enum):
    """Notification urgency levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class HumanDecision:
    """Represents a decision request from the system"""

    def __init__(self,
                 decision_id: str,
                 intervention_type: InterventionType,
                 context: Dict,
                 level: NotificationLevel = NotificationLevel.WARNING):
        """Initialize decision request

        Args:
            decision_id: Unique identifier
            intervention_type: Type of intervention needed
            context: Decision context and details
            level: Urgency level
        """
        self.decision_id = decision_id
        self.type = intervention_type
        self.context = context
        self.level = level
        self.options = []
        self.timestamp = datetime.now()
        self.resolved = False
        self.resolution = None
        self.response_time = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "decision_id": self.decision_id,
            "type": self.type.value,
            "level": self.level.value,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "resolved": self.resolved,
            "resolution": self.resolution,
            "response_time": self.response_time
        }


class HITLCoordinator:
    """Coordinates human-in-the-loop interventions"""

    def __init__(self,
                 epic_id: str,
                 config: Dict = None,
                 notification_callback: Callable = None):
        """Initialize HITL coordinator

        Args:
            epic_id: Epic identifier
            config: Configuration dictionary
            notification_callback: Optional callback for notifications
        """
        self.epic_id = epic_id
        self.config = config or self._default_config()
        self.notification_callback = notification_callback

        self.console = Console()
        self.pending_decisions = asyncio.Queue()
        self.decision_history = []
        self.escalation_rules = self._setup_escalation_rules()
        self.notification_channels = self._setup_notification_channels()

    def _default_config(self) -> Dict:
        """Get default HITL configuration"""
        return {
            "enabled": True,
            "notification_channels": ["terminal"],
            "escalation_thresholds": {
                "agent_timeout": 900,
                "confidence_minimum": 0.7,
                "qa_failure_max": 2,
                "cost_limit": 10.0,
                "anomaly_keywords": ["error", "failed", "unclear"]
            },
            "decision_timeout": 300,
            "auto_suggestions": True,
            "learn_from_decisions": True
        }

    def _setup_escalation_rules(self) -> Dict:
        """Setup escalation rules from configuration"""
        thresholds = self.config.get("escalation_thresholds", {})
        return {
            "max_retries": 3,
            "agent_timeout": thresholds.get("agent_timeout", 900),
            "qa_failure_threshold": thresholds.get("qa_failure_max", 2),
            "confidence_threshold": thresholds.get("confidence_minimum", 0.7),
            "cost_threshold": thresholds.get("cost_limit", 10.0),
            "anomaly_keywords": thresholds.get("anomaly_keywords", [])
        }

    def _setup_notification_channels(self) -> Dict:
        """Setup notification channels"""
        channels = {}

        for channel in self.config.get("notification_channels", ["terminal"]):
            if channel == "terminal":
                channels[channel] = self.notify_terminal
            elif channel == "desktop":
                channels[channel] = self.notify_desktop
            elif channel == "sound":
                channels[channel] = self.play_alert_sound

        return channels

    async def check_escalation_needed(self,
                                     agent: str,
                                     output: str,
                                     context: Dict) -> Optional[InterventionType]:
        """Check if human intervention is needed

        Args:
            agent: Agent name
            output: Agent output
            context: Execution context

        Returns:
            InterventionType if escalation needed, None otherwise
        """
        # Check for explicit escalation requests
        escalation_phrases = [
            "need human", "requires decision", "unclear requirement",
            "multiple options", "breaking change", "cannot proceed",
            "ambiguous", "conflict detected"
        ]

        for phrase in escalation_phrases:
            if phrase.lower() in output.lower():
                return InterventionType.CRITICAL_DECISION

        # Check confidence scores
        confidence_match = re.search(r'confidence:\s*([\d.]+)', output, re.IGNORECASE)
        if confidence_match:
            confidence = float(confidence_match.group(1))
            if confidence < self.escalation_rules["confidence_threshold"]:
                return InterventionType.LOW_CONFIDENCE

        # Check for QA failures
        if agent == "qa" and "failed" in output.lower():
            failure_count = context.get("qa_failures", 0) + 1
            if failure_count >= self.escalation_rules["qa_failure_threshold"]:
                return InterventionType.QA_FAILURE

        # Check for anomaly keywords
        for keyword in self.escalation_rules["anomaly_keywords"]:
            if keyword.lower() in output.lower():
                return InterventionType.ANOMALY_DETECTED

        # Check for timeout
        execution_time = context.get("execution_time", 0)
        if execution_time > self.escalation_rules["agent_timeout"]:
            return InterventionType.TIMEOUT

        return None

    async def request_human_decision(self,
                                    intervention_type: InterventionType,
                                    story_id: str,
                                    agent: str,
                                    context: Dict,
                                    suggested_actions: List[str]) -> Dict:
        """Request human intervention for critical decision

        Args:
            intervention_type: Type of intervention
            story_id: Story identifier
            agent: Agent name
            context: Decision context
            suggested_actions: List of suggested actions

        Returns:
            Decision result dictionary
        """
        decision = HumanDecision(
            decision_id=f"{story_id}-{agent}-{datetime.now().timestamp()}",
            intervention_type=intervention_type,
            context={
                "epic_id": self.epic_id,
                "story_id": story_id,
                "agent": agent,
                "details": context,
                "suggested_actions": suggested_actions
            },
            level=self._determine_notification_level(intervention_type)
        )

        # Send notifications
        await self.notify_human(decision)

        # Add to queue
        await self.pending_decisions.put(decision)

        # Display decision interface
        resolution = await self.display_decision_interface(decision)
        decision.resolution = resolution
        decision.resolved = True
        decision.response_time = (datetime.now() - decision.timestamp).seconds

        # Log decision
        self.decision_history.append(decision)

        return resolution

    def _determine_notification_level(self, intervention_type: InterventionType) -> NotificationLevel:
        """Determine notification level based on intervention type"""
        critical_types = [
            InterventionType.MERGE_CONFLICT,
            InterventionType.CRITICAL_DECISION,
            InterventionType.RESOURCE_LIMIT
        ]

        if intervention_type in critical_types:
            return NotificationLevel.CRITICAL
        elif intervention_type == InterventionType.TIMEOUT:
            return NotificationLevel.EMERGENCY
        else:
            return NotificationLevel.WARNING

    async def notify_human(self, decision: HumanDecision):
        """Send notifications through configured channels

        Args:
            decision: Decision request
        """
        for channel_name, channel_func in self.notification_channels.items():
            try:
                await channel_func(decision)
            except Exception as e:
                print(f"Notification failed for {channel_name}: {e}")

        # Call custom callback if provided
        if self.notification_callback:
            self.notification_callback(decision)

    async def notify_terminal(self, decision: HumanDecision):
        """Terminal notification with visual alert

        Args:
            decision: Decision request
        """
        # Terminal bell
        print("\a", end="", flush=True)

        # Color based on level
        colors = {
            NotificationLevel.INFO: "blue",
            NotificationLevel.WARNING: "yellow",
            NotificationLevel.CRITICAL: "red",
            NotificationLevel.EMERGENCY: "bold red on white"
        }

        color = colors.get(decision.level, "yellow")

        # Display notification
        self.console.print("\n" + "="*80)
        self.console.print(Panel(
            f"[{color}]HUMAN DECISION REQUIRED[/{color}]\n\n"
            f"Type: {decision.type.value}\n"
            f"Story: {decision.context.get('story_id', 'Unknown')}\n"
            f"Agent: {decision.context.get('agent', 'Unknown')}\n"
            f"Level: {decision.level.value}",
            title=f"[{color}]Intervention Request[/{color}]",
            style=color,
            expand=True
        ))
        self.console.print("="*80 + "\n")

    async def notify_desktop(self, decision: HumanDecision):
        """Desktop notification for Linux/Mac/Windows

        Args:
            decision: Decision request
        """
        title = f"BMad {decision.level.value.upper()}"
        message = (f"Decision needed for {decision.context.get('story_id', 'story')}\n"
                  f"Type: {decision.type.value}")

        system = platform.system()

        try:
            if system == "Linux":
                subprocess.run([
                    "notify-send",
                    title,
                    message,
                    "-u", "critical" if decision.level in [NotificationLevel.CRITICAL, NotificationLevel.EMERGENCY] else "normal",
                    "-t", "0" if decision.level == NotificationLevel.EMERGENCY else "10000"
                ], check=False)

            elif system == "Darwin":  # macOS
                subprocess.run([
                    "osascript", "-e",
                    f'display notification "{message}" with title "{title}" sound name "Ping"'
                ], check=False)

            elif system == "Windows":
                # Windows 10 toast notification (requires win10toast)
                try:
                    from win10toast import ToastNotifier
                    toaster = ToastNotifier()
                    toaster.show_toast(title, message, duration=10, threaded=True)
                except ImportError:
                    print("Windows notifications require 'win10toast' package")

        except Exception as e:
            print(f"Desktop notification failed: {e}")

    async def play_alert_sound(self, decision: HumanDecision):
        """Play alert sound based on urgency

        Args:
            decision: Decision request
        """
        # This is a placeholder - actual implementation would play sound files
        # For terminal beep, we already do print("\a")
        pass

    async def display_decision_interface(self, decision: HumanDecision) -> Dict:
        """Interactive CLI for decision making

        Args:
            decision: Decision request

        Returns:
            Resolution dictionary
        """
        self.console.clear()

        # Create layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=5)
        )

        # Header
        header_text = f"[bold cyan]BMad Automation - Human Decision Required[/bold cyan]"
        layout["header"].update(Panel(header_text, style="cyan"))

        # Body - split into context and details
        layout["body"].split_row(
            Layout(name="context"),
            Layout(name="details")
        )

        # Context panel
        context_table = Table(show_header=False, box=None)
        context_table.add_column("Key", style="yellow")
        context_table.add_column("Value", style="white")

        context_table.add_row("Decision ID", decision.decision_id[:20] + "...")
        context_table.add_row("Epic", decision.context.get("epic_id", "Unknown"))
        context_table.add_row("Story", decision.context.get("story_id", "Unknown"))
        context_table.add_row("Agent", decision.context.get("agent", "Unknown"))
        context_table.add_row("Type", decision.type.value)
        context_table.add_row("Level", decision.level.value)
        context_table.add_row("Time", decision.timestamp.strftime("%H:%M:%S"))

        layout["body"]["context"].update(Panel(context_table, title="Context"))

        # Details panel
        details = decision.context.get("details", {})
        details_text = ""

        if "error" in details:
            details_text = f"[red]Error:[/red]\n{details['error'][:500]}"
        elif "output" in details:
            details_text = f"[green]Output:[/green]\n{details['output'][:500]}"
        else:
            details_text = json.dumps(details, indent=2)[:500]

        layout["body"]["details"].update(Panel(details_text, title="Details"))

        # Footer - suggested actions
        suggestions = decision.context.get("suggested_actions", [])
        footer_text = "[yellow]Suggested Actions:[/yellow]\n"
        for i, action in enumerate(suggestions[:5], 1):
            footer_text += f"{i}. {action}\n"

        layout["footer"].update(Panel(footer_text, title="Suggestions"))

        # Display layout
        self.console.print(layout)

        # Get user input
        return await self._get_user_decision(decision, suggestions)

    async def _get_user_decision(self,
                                decision: HumanDecision,
                                suggestions: List[str]) -> Dict:
        """Get user's decision

        Args:
            decision: Decision request
            suggestions: List of suggested actions

        Returns:
            Resolution dictionary
        """
        self.console.print("\n[bold cyan]Available Options:[/bold cyan]")
        self.console.print("  1-5: Select suggested action")
        self.console.print("  r:   Retry the operation")
        self.console.print("  s:   Skip this story")
        self.console.print("  c:   Enter custom command")
        self.console.print("  v:   View more details")
        self.console.print("  e:   Escalate to team")
        self.console.print("  a:   Abort epic")
        self.console.print("")

        choice = Prompt.ask(
            "[bold]Your decision",
            choices=["1", "2", "3", "4", "5", "r", "s", "c", "v", "e", "a"],
            default="r"
        )

        # Process choice
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(suggestions):
                return {
                    "action": "execute",
                    "command": suggestions[idx],
                    "reason": "Selected suggested action"
                }

        elif choice == "r":
            return {
                "action": "retry",
                "command": None,
                "reason": "Human requested retry"
            }

        elif choice == "s":
            return {
                "action": "skip",
                "command": None,
                "reason": "Human decided to skip story"
            }

        elif choice == "c":
            custom_command = Prompt.ask("[bold]Enter custom command")
            return {
                "action": "custom",
                "command": custom_command,
                "reason": "Human provided custom command"
            }

        elif choice == "v":
            # Show more details and recurse
            self._show_full_details(decision)
            return await self._get_user_decision(decision, suggestions)

        elif choice == "e":
            return {
                "action": "escalate",
                "command": None,
                "reason": "Human escalated to team"
            }

        elif choice == "a":
            if Confirm.ask("[bold red]Are you sure you want to abort the epic?"):
                return {
                    "action": "abort",
                    "command": None,
                    "reason": "Human aborted epic"
                }
            else:
                return await self._get_user_decision(decision, suggestions)

        return {
            "action": "retry",
            "command": None,
            "reason": "Invalid choice - defaulting to retry"
        }

    def _show_full_details(self, decision: HumanDecision):
        """Show full decision details

        Args:
            decision: Decision request
        """
        self.console.clear()
        self.console.print(Panel(
            json.dumps(decision.to_dict(), indent=2, default=str),
            title="Full Decision Details",
            expand=True
        ))
        input("\nPress Enter to continue...")

    def generate_suggested_actions(self,
                                  intervention_type: InterventionType,
                                  context: Dict) -> List[str]:
        """Generate context-aware suggested actions

        Args:
            intervention_type: Type of intervention
            context: Decision context

        Returns:
            List of suggested actions
        """
        suggestions = []
        agent = context.get("agent", "")
        story_id = context.get("story_id", "")

        if intervention_type == InterventionType.TIMEOUT:
            suggestions.extend([
                f"Restart {agent} with increased timeout",
                "Simplify story requirements",
                "Skip story and continue",
                "Check system resources"
            ])

        elif intervention_type == InterventionType.LOW_CONFIDENCE:
            suggestions.extend([
                "Provide clarification for requirements",
                f"Manually review {agent} output",
                "Escalate to subject matter expert",
                "Retry with different model"
            ])

        elif intervention_type == InterventionType.QA_FAILURE:
            suggestions.extend([
                "Review failing tests",
                "Modify acceptance criteria",
                "Debug with developer agent",
                "Skip QA for now"
            ])

        elif intervention_type == InterventionType.MERGE_CONFLICT:
            suggestions.extend([
                "Manually resolve conflicts",
                "Use incoming changes",
                "Use current changes",
                "Rebase and retry"
            ])

        else:
            # Generic suggestions
            suggestions.extend([
                f"Retry {agent} agent",
                "Skip to next phase",
                "Manually complete phase",
                "Abort story"
            ])

        return suggestions[:5]  # Return top 5 suggestions

    def get_decision_history_summary(self) -> Dict:
        """Get summary of decision history

        Returns:
            Summary dictionary
        """
        if not self.decision_history:
            return {"total_decisions": 0}

        total = len(self.decision_history)
        by_type = {}
        by_resolution = {}
        avg_response_time = 0

        for decision in self.decision_history:
            # Count by type
            type_key = decision.type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1

            # Count by resolution
            if decision.resolution:
                action = decision.resolution.get("action", "unknown")
                by_resolution[action] = by_resolution.get(action, 0) + 1

            # Add response time
            if decision.response_time:
                avg_response_time += decision.response_time

        avg_response_time = avg_response_time / total if total > 0 else 0

        return {
            "total_decisions": total,
            "by_type": by_type,
            "by_resolution": by_resolution,
            "avg_response_time_seconds": avg_response_time,
            "escalation_rate": total / max(1, context.get("total_stories", 1))
        }


# CLI interface for testing
if __name__ == "__main__":
    async def test_hitl():
        """Test HITL interface"""
        print("Testing HITL Interface\n" + "="*50)

        # Create coordinator
        coordinator = HITLCoordinator("test-epic-1")

        # Test escalation check
        print("Testing escalation detection:")
        output = "Error: Cannot proceed with unclear requirements"
        intervention = await coordinator.check_escalation_needed(
            "dev", output, {"story_id": "story-1"}
        )
        print(f"  Detected: {intervention.value if intervention else 'None'}")

        # Test decision request
        print("\nTesting decision request:")
        resolution = await coordinator.request_human_decision(
            InterventionType.CRITICAL_DECISION,
            "story-1",
            "dev",
            {"error": "Ambiguous requirement for user authentication"},
            [
                "Use JWT tokens for authentication",
                "Use session-based authentication",
                "Implement OAuth 2.0",
                "Skip authentication for MVP"
            ]
        )
        print(f"\nResolution: {resolution}")

        # Get summary
        summary = coordinator.get_decision_history_summary()
        print(f"\nDecision Summary: {json.dumps(summary, indent=2)}")

    # Run test
    asyncio.run(test_hitl())