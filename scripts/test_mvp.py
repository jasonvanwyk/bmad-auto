#!/usr/bin/env python3
"""
BMad Orchestrator MVP Integration Test

Tests the Phase 1 implementation with a real BMad project.
Only tests SM agent (story creation).

Usage:
    python scripts/test_mvp.py [--project PATH] [--story-id ID]

Example:
    python scripts/test_mvp.py --project ~/projects/precept-pos-bmad-auto --story-id 1.1
"""

import asyncio
import sys
from pathlib import Path
import argparse

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestrator import BMadOrchestrator


def validate_project(project_path: Path) -> tuple[bool, str]:
    """
    Validate that project is a BMad project.

    Args:
        project_path: Path to project

    Returns:
        (is_valid, error_message)
    """
    if not project_path.exists():
        return False, f"Project path does not exist: {project_path}"

    if not project_path.is_dir():
        return False, f"Project path is not a directory: {project_path}"

    bmad_core = project_path / ".bmad-core"
    if not bmad_core.exists():
        return False, f"Not a BMad project (no .bmad-core/): {project_path}"

    core_config = bmad_core / "core-config.yaml"
    if not core_config.exists():
        return False, f"Missing core-config.yaml in .bmad-core/"

    docs_dir = project_path / "docs"
    if not docs_dir.exists():
        return False, f"Missing docs/ directory"

    return True, ""


async def main():
    """Run MVP integration test."""
    parser = argparse.ArgumentParser(
        description="Test BMad Orchestrator MVP (Phase 1 - SM only)"
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=Path.home() / "projects" / "precept-pos-bmad-auto",
        help="Path to BMad project (default: ~/projects/precept-pos-bmad-auto)"
    )
    parser.add_argument(
        "--story-id",
        type=str,
        default="1.1",
        help="Story ID to process (default: 1.1)"
    )

    args = parser.parse_args()

    print("╔═══════════════════════════════════════════════════════════╗")
    print("║     BMad Orchestrator MVP Test (Phase 1: SM Only)        ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # Validate project
    print(f"→ Validating project: {args.project}")
    is_valid, error = validate_project(args.project)

    if not is_valid:
        print(f"✗ Project validation failed:")
        print(f"  {error}")
        print()
        print("Please provide a valid BMad project path with --project")
        return 1

    print(f"  ✓ Valid BMad project")
    print()

    # Check if story file already exists
    story_file = args.project / f"docs/stories/{args.story_id}.story.md"
    if story_file.exists():
        print(f"⚠️  Warning: Story file already exists: {story_file}")
        print(f"  This test will wait for SM to update it.")
        print(f"  Consider deleting it first or using a different story ID.")
        print()

    # Initialize orchestrator
    print(f"→ Initializing orchestrator...")
    orchestrator = BMadOrchestrator(args.project)
    print(f"  ✓ Orchestrator initialized")
    print()

    # Process story
    print(f"→ Processing story {args.story_id}")
    print(f"  This will:")
    print(f"    1. Spawn tmux session: bmad-sm-{args.story_id.replace('.', '-')}")
    print(f"    2. Start Claude Code with /sm *create")
    print(f"    3. Wait for story file creation (max 10 minutes)")
    print(f"    4. Kill tmux session (context cleared)")
    print()
    print(f"  You can monitor in another terminal:")
    print(f"    tmux attach -t bmad-sm-{args.story_id.replace('.', '-')}")
    print()

    try:
        result = await orchestrator.process_story(args.story_id)

        # Print detailed result
        print()
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║                      TEST RESULT                          ║")
        print("╚═══════════════════════════════════════════════════════════╝")
        print()

        if result['success']:
            print("✓ SUCCESS: Story processing complete")
            print()
            print(f"Story File: {result['story_file']}")
            print()

            # Show file info
            if result['story_file']:
                story_path = Path(result['story_file'])
                if story_path.exists():
                    size = story_path.stat().st_size
                    print(f"File Size: {size:,} bytes")
                    print()
                    print("First 50 lines:")
                    print("-" * 60)
                    content = story_path.read_text()
                    lines = content.split('\n')[:50]
                    for line in lines:
                        print(line)
                    if len(content.split('\n')) > 50:
                        print("...")
                        print(f"(showing 50 of {len(content.split('\n'))} lines)")
                    print("-" * 60)
            print()
            print("✓ Phase 1 MVP test PASSED")
            return 0

        else:
            print("✗ FAILED: Story processing failed")
            print()
            print(f"Stage Reached: {result['stage_reached']}")
            print(f"Error: {result['error']}")
            print()
            print("✗ Phase 1 MVP test FAILED")
            return 1

    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        print("→ Cleaning up...")
        orchestrator.cleanup()
        return 130

    except Exception as e:
        print(f"\n\n✗ Unexpected error: {e}")
        print("→ Cleaning up...")
        orchestrator.cleanup()
        raise

    finally:
        # Ensure cleanup
        orchestrator.cleanup()


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        sys.exit(1)
