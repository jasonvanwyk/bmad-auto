#!/usr/bin/env python3
"""
mvp_story_automation.py - Minimal viable BMad story automation

Focuses only on the core development cycle:
SM draft → PO validate → Dev implement → QA test

Usage:
    python3 mvp_story_automation.py --project /path/to/project --epic epic-1

Author: BMad Automation Team
Version: 1.0.0
"""

import asyncio
import subprocess
import yaml
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import libtmux
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint


class StoryDevelopmentMVP:
    """
    Minimal automation for BMad story development cycle.
    Focuses ONLY on: SM draft → PO validate → Dev implement → QA test
    """

    def __init__(self, project_path: str, epic_id: str, vm_safe_mode: bool = True, dry_run: bool = False):
        """Initialize the story development automation."""
        self.project_path = Path(project_path).resolve()
        self.epic_id = epic_id
        self.vm_safe_mode = vm_safe_mode
        self.dry_run = dry_run
        self.console = Console()

        # Results tracking
        self.results = []
        self.start_time = None
        self.checkpoint_file = self.project_path / f".bmad-checkpoint-{epic_id}.yaml"

        # Safety: Verify we're in VM if safe mode enabled
        if self.vm_safe_mode:
            self.verify_vm_environment()

        # Verify planning phase is complete
        self.verify_planning_complete()

        # Load pre-sharded stories
        self.stories = self.load_stories()

        # Setup tmux for visibility
        self.tmux_server = None
        self.session = None
        if not dry_run:
            try:
                self.tmux_server = libtmux.Server()
            except:
                self.console.print("[yellow]⚠ Tmux not available. Continuing without session management.[/yellow]")

    def verify_vm_environment(self):
        """Ensure we're running in the test VM for safety."""
        try:
            hostname = subprocess.run(
                ['hostname'],
                capture_output=True,
                text=True,
                timeout=5
            ).stdout.strip()

            if 'bmad-automation-test' not in hostname.lower():
                self.console.print(Panel(
                    "[red]⚠️  Not running in test VM![/red]\n\n"
                    "For safety, please run in Proxmox VM 'bmad-automation-test'.\n"
                    "Override with --no-vm-check if you're absolutely sure.\n\n"
                    f"Current hostname: {hostname}",
                    title="Safety Check Failed",
                    style="red"
                ))

                if not click.confirm("Do you want to continue anyway?", default=False):
                    sys.exit(1)
        except Exception as e:
            self.console.print(f"[yellow]Could not verify VM environment: {e}[/yellow]")

    def verify_planning_complete(self):
        """Ensure planning artifacts exist before automation."""
        required_files = {
            "PRD": self.project_path / "docs" / "prd.md",
            "Architecture": self.project_path / "docs" / "architecture.md",
            "Epic Plan": self.project_path / "docs" / "epics" / self.epic_id / "stories.yaml"
        }

        missing = []
        for name, path in required_files.items():
            if not path.exists():
                missing.append(f"  • {name}: {path}")

        if missing:
            self.console.print(Panel(
                "[red]Planning phase incomplete![/red]\n\n"
                "Missing required artifacts:\n" + "\n".join(missing) + "\n\n"
                "Please complete the planning phase before running automation.",
                title="Prerequisites Check Failed",
                style="red"
            ))
            sys.exit(1)

        self.console.print("[green]✓[/green] Planning phase verified - all artifacts present")

    def load_stories(self) -> List[Dict]:
        """Load pre-sharded stories from epic plan."""
        epic_file = self.project_path / "docs" / "epics" / self.epic_id / "stories.yaml"

        try:
            with open(epic_file, 'r') as f:
                epic_data = yaml.safe_load(f)

            stories = epic_data.get('stories', [])

            if not stories:
                self.console.print(f"[red]No stories found in {epic_file}[/red]")
                sys.exit(1)

            self.console.print(f"[green]✓[/green] Loaded {len(stories)} stories from epic plan")
            return stories

        except Exception as e:
            self.console.print(f"[red]Error loading stories: {e}[/red]")
            sys.exit(1)

    def initialize_tmux_session(self):
        """Create tmux session for monitoring."""
        if not self.tmux_server or self.dry_run:
            return

        session_name = f"bmad-epic-{self.epic_id}"

        try:
            # Kill existing session if it exists
            existing = self.tmux_server.find_where({"session_name": session_name})
            if existing:
                existing.kill_session()
        except:
            pass

        try:
            self.session = self.tmux_server.new_session(
                session_name=session_name,
                window_name="orchestrator",
                start_directory=str(self.project_path)
            )
            self.console.print(f"[green]✓[/green] Created tmux session: {session_name}")
            self.console.print(f"  [dim]Attach with: tmux attach -t {session_name}[/dim]")
        except Exception as e:
            self.console.print(f"[yellow]Could not create tmux session: {e}[/yellow]")

    async def run_story_cycle(self, story: Dict, story_num: int, total: int) -> Dict:
        """Run single story through SM→PO→Dev→QA cycle."""
        story_id = story.get('id', f'story-{story_num}')
        story_title = story.get('title', 'Untitled Story')

        self.console.print(f"\n[cyan]═══ Story {story_num}/{total}: {story_id} ═══[/cyan]")
        self.console.print(f"[dim]{story_title}[/dim]\n")

        results = {
            'story_id': story_id,
            'title': story_title,
            'start_time': datetime.now().isoformat(),
            'stages': {},
            'success': False
        }

        # Create tmux window for this story
        if self.session and not self.dry_run:
            try:
                story_window = self.session.new_window(window_name=f"story-{story_id}")
            except:
                story_window = None

        # Stage 1: SM Draft
        self.console.print("[yellow]→ SM:[/yellow] Drafting story details...")
        sm_result = await self.execute_agent(
            agent='sm',
            task='create-next-story',
            context=story,
            timeout=300  # 5 minutes
        )
        results['stages']['sm'] = sm_result

        if not sm_result['success']:
            self.console.print(f"  [red]✗ SM failed: {sm_result.get('error', 'Unknown error')}[/red]")
            results['success'] = False
            return results

        self.console.print("  [green]✓ Story drafted[/green]")

        # Stage 2: PO Validation
        self.console.print("[yellow]→ PO:[/yellow] Validating story...")
        po_result = await self.execute_agent(
            agent='po',
            task='validate-next-story',
            context={'story_file': sm_result.get('output_file', story_id)},
            timeout=180  # 3 minutes
        )
        results['stages']['po'] = po_result

        if not po_result['success']:
            self.console.print(f"  [yellow]⚠ PO validation had issues[/yellow]")
            # Continue anyway for MVP
        else:
            self.console.print("  [green]✓ Story validated[/green]")

        # Stage 3: Dev Implementation
        self.console.print("[yellow]→ Dev:[/yellow] Implementing story...")
        dev_result = await self.execute_agent(
            agent='dev',
            task='develop-story',
            context={'story_file': sm_result.get('output_file', story_id)},
            timeout=900  # 15 minutes
        )
        results['stages']['dev'] = dev_result

        if not dev_result['success']:
            self.console.print(f"  [red]✗ Dev failed: {dev_result.get('error', 'Unknown error')}[/red]")
            results['success'] = False
            return results

        self.console.print("  [green]✓ Story implemented[/green]")

        # Stage 4: QA Testing
        self.console.print("[yellow]→ QA:[/yellow] Testing implementation...")
        qa_result = await self.execute_agent(
            agent='qa',
            task='test-story',
            context={'implementation_path': dev_result.get('output_path', '.')},
            timeout=600  # 10 minutes
        )
        results['stages']['qa'] = qa_result

        # Determine final status
        if qa_result['success']:
            self.console.print("  [green]✓ All tests passed![/green]")
            results['success'] = True
        else:
            self.console.print("  [yellow]⚠ QA found issues[/yellow]")
            # In full system, would retry Dev here
            results['success'] = False

        results['end_time'] = datetime.now().isoformat()
        return results

    async def execute_agent(self, agent: str, task: str, context: Dict, timeout: int) -> Dict:
        """Execute BMad agent with safety wrapper."""

        if self.dry_run:
            # Simulate execution in dry run mode
            await asyncio.sleep(1)
            return {
                'success': True,
                'dry_run': True,
                'agent': agent,
                'task': task,
                'output_file': f"/tmp/{agent}_{task}_output.md",
                'output_path': str(self.project_path)
            }

        # Prepare context file
        context_file = f"/tmp/bmad_{agent}_{task}_context.yaml"
        with open(context_file, 'w') as f:
            yaml.dump(context, f)

        # Build command
        cmd = f"bmad {agent} --task {task} --context {context_file} --headless"

        # Add safety wrapper if in VM
        if self.vm_safe_mode:
            cmd = f"timeout {timeout}s nice -n 10 {cmd}"

        try:
            # Execute command
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.project_path)
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout + 10  # Add buffer to timeout
            )

            success = process.returncode == 0

            # Parse output for file paths
            output_file = None
            output_path = str(self.project_path)

            if success and stdout:
                for line in stdout.decode().split('\n'):
                    if 'output:' in line.lower() or 'file:' in line.lower():
                        parts = line.split(':', 1)
                        if len(parts) > 1:
                            output_file = parts[1].strip()
                    if 'path:' in line.lower():
                        parts = line.split(':', 1)
                        if len(parts) > 1:
                            output_path = parts[1].strip()

            return {
                'success': success,
                'agent': agent,
                'task': task,
                'stdout': stdout.decode()[:5000] if stdout else "",
                'stderr': stderr.decode()[:2000] if stderr else "",
                'output_file': output_file,
                'output_path': output_path,
                'returncode': process.returncode
            }

        except asyncio.TimeoutExpired:
            return {
                'success': False,
                'agent': agent,
                'task': task,
                'error': f'Agent {agent} timed out after {timeout}s',
                'timeout': True
            }
        except Exception as e:
            return {
                'success': False,
                'agent': agent,
                'task': task,
                'error': str(e),
                'exception': True
            }

    def save_checkpoint(self):
        """Save progress checkpoint for recovery."""
        checkpoint = {
            'epic_id': self.epic_id,
            'timestamp': datetime.now().isoformat(),
            'completed_stories': len(self.results),
            'total_stories': len(self.stories),
            'results': self.results
        }

        try:
            with open(self.checkpoint_file, 'w') as f:
                yaml.dump(checkpoint, f, default_flow_style=False)
            self.console.print(f"[dim]  💾 Checkpoint saved[/dim]")
        except Exception as e:
            self.console.print(f"[yellow]Could not save checkpoint: {e}[/yellow]")

    def load_checkpoint(self) -> bool:
        """Load checkpoint if it exists."""
        if not self.checkpoint_file.exists():
            return False

        try:
            with open(self.checkpoint_file, 'r') as f:
                checkpoint = yaml.safe_load(f)

            if checkpoint['epic_id'] != self.epic_id:
                return False

            self.results = checkpoint.get('results', [])
            completed = checkpoint.get('completed_stories', 0)

            self.console.print(Panel(
                f"Found checkpoint with {completed} completed stories.\n"
                f"Last saved: {checkpoint['timestamp']}",
                title="Checkpoint Loaded",
                style="yellow"
            ))

            return click.confirm("Resume from checkpoint?", default=True)

        except Exception as e:
            self.console.print(f"[yellow]Could not load checkpoint: {e}[/yellow]")
            return False

    def print_summary(self):
        """Print execution summary with statistics."""
        if not self.results:
            return

        # Calculate statistics
        successful = sum(1 for r in self.results if r.get('success', False))
        failed = len(self.results) - successful
        success_rate = (successful / len(self.results) * 100) if self.results else 0

        # Create summary table
        table = Table(title=f"Epic {self.epic_id} Summary", show_header=True)
        table.add_column("Story", style="cyan")
        table.add_column("SM", style="yellow")
        table.add_column("PO", style="yellow")
        table.add_column("Dev", style="yellow")
        table.add_column("QA", style="yellow")
        table.add_column("Status", style="green")

        for result in self.results:
            story_id = result.get('story_id', 'unknown')
            stages = result.get('stages', {})

            # Status icons for each stage
            sm_status = "✓" if stages.get('sm', {}).get('success') else "✗"
            po_status = "✓" if stages.get('po', {}).get('success') else "⚠"
            dev_status = "✓" if stages.get('dev', {}).get('success') else "✗"
            qa_status = "✓" if stages.get('qa', {}).get('success') else "✗"

            overall = "[green]Complete[/green]" if result.get('success') else "[red]Failed[/red]"

            table.add_row(story_id, sm_status, po_status, dev_status, qa_status, overall)

        self.console.print("\n")
        self.console.print(table)

        # Print statistics panel
        duration = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        duration_min = duration / 60

        stats_text = f"""
[green]Stories Completed:[/green] {successful}
[red]Stories Failed:[/red] {failed}
[yellow]Success Rate:[/yellow] {success_rate:.1f}%
[cyan]Total Duration:[/cyan] {duration_min:.1f} minutes
[dim]Checkpoint saved to:[/dim] {self.checkpoint_file}
        """

        self.console.print(Panel(
            stats_text.strip(),
            title="[bold green]Execution Complete[/bold green]",
            style="green"
        ))

    async def run_epic(self):
        """Run all stories in the epic."""
        self.start_time = datetime.now()

        # Display startup banner
        self.console.print(Panel.fit(
            f"[bold cyan]BMad Epic Automation[/bold cyan]\n\n"
            f"Epic: {self.epic_id}\n"
            f"Stories: {len(self.stories)}\n"
            f"Mode: {'Dry Run' if self.dry_run else 'Live'}\n"
            f"VM Safety: {'Enabled' if self.vm_safe_mode else 'Disabled'}",
            style="cyan"
        ))

        # Check for checkpoint
        resume_from = 0
        if self.load_checkpoint():
            resume_from = len(self.results)
            self.console.print(f"[yellow]Resuming from story {resume_from + 1}[/yellow]\n")

        # Initialize tmux session
        self.initialize_tmux_session()

        # Process stories
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console
        ) as progress:

            epic_task = progress.add_task(
                f"[cyan]Processing epic {self.epic_id}",
                total=len(self.stories)
            )

            # Skip already completed stories if resuming
            if resume_from > 0:
                progress.update(epic_task, completed=resume_from)

            for i, story in enumerate(self.stories[resume_from:], start=resume_from + 1):
                progress.update(
                    epic_task,
                    description=f"[cyan]Story {i}/{len(self.stories)}: {story.get('title', 'Untitled')[:40]}..."
                )

                result = await self.run_story_cycle(story, i, len(self.stories))
                self.results.append(result)

                progress.advance(epic_task)

                # Save checkpoint after each story
                self.save_checkpoint()

                # Small delay between stories
                if i < len(self.stories):
                    await asyncio.sleep(2)

        # Print final summary
        self.print_summary()

        # Cleanup tmux session (optional)
        if self.session and not self.dry_run:
            self.console.print(f"\n[dim]Tmux session kept alive: tmux attach -t bmad-epic-{self.epic_id}[/dim]")

        return self.results


# CLI Interface
@click.command()
@click.option('--project', '-p', required=True, help='Path to project directory')
@click.option('--epic', '-e', required=True, help='Epic ID to process')
@click.option('--vm-check/--no-vm-check', default=True, help='Enforce VM safety check')
@click.option('--dry-run', is_flag=True, help='Simulate execution without running agents')
@click.option('--resume', is_flag=True, help='Resume from checkpoint if available')
def main(project, epic, vm_check, dry_run, resume):
    """
    BMad Story Development Automation MVP

    Automates the story development cycle:
    SM draft → PO validate → Dev implement → QA test

    Examples:

        # Run epic with VM safety check
        python mvp_story_automation.py --project ./myproject --epic epic-1

        # Run without VM check (careful!)
        python mvp_story_automation.py --project ./myproject --epic epic-1 --no-vm-check

        # Dry run to test setup
        python mvp_story_automation.py --project ./myproject --epic epic-1 --dry-run

        # Resume from checkpoint
        python mvp_story_automation.py --project ./myproject --epic epic-1 --resume
    """

    try:
        automation = StoryDevelopmentMVP(
            project_path=project,
            epic_id=epic,
            vm_safe_mode=vm_check,
            dry_run=dry_run
        )

        # Run the epic
        asyncio.run(automation.run_epic())

    except KeyboardInterrupt:
        print("\n\n[yellow]Automation interrupted by user[/yellow]")
        print("[dim]Checkpoint saved for resume[/dim]")
        sys.exit(1)
    except Exception as e:
        print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()