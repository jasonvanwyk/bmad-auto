"""
LangGraph-based orchestrator for BMad agent workflow.

This module provides the BMadOrchestrator class that uses LangGraph
to manage the SM → PO → Dev → QA workflow, spawning agents in tmux
sessions and monitoring story files for completion.

Based on: docs/design/orchestrator.md
"""

from typing import TypedDict, Literal
from pathlib import Path
import asyncio

from langgraph.graph import StateGraph, END

from .tmux_manager import TmuxAgentManager
from .file_monitor import wait_for_sm_completion


class StoryState(TypedDict):
    """
    State for processing a single story.

    This state is passed between LangGraph nodes and tracks
    the current stage of story processing.
    """
    story_id: str
    current_stage: Literal["sm", "po", "dev", "qa", "complete", "failed"]
    story_file_path: str
    tmux_session_id: str
    po_decision: str
    dev_files_modified: list
    qa_test_results: str
    error_message: str


class BMadOrchestrator:
    """
    Orchestrates BMad agent workflow using LangGraph.

    Manages the complete story lifecycle:
    1. SM creates story file
    2. PO validates story (Phase 2)
    3. Dev implements story (Phase 2)
    4. QA tests implementation (Phase 2)

    For Phase 1 (MVP), only SM stage is implemented.

    Example:
        >>> orchestrator = BMadOrchestrator(Path("~/projects/myproject"))
        >>> result = await orchestrator.process_story("1.1")
        >>> if result['success']:
        ...     print(f"Story complete: {result['story_file']}")
    """

    def __init__(self, project_path: Path):
        """
        Initialize orchestrator.

        Args:
            project_path: Absolute path to BMad project directory
        """
        self.project_path = project_path.resolve()
        self.tmux_mgr = TmuxAgentManager(project_path)
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """
        Build LangGraph state machine.

        For Phase 1 (MVP): Only SM node implemented.
        Phase 2 will add PO, Dev, QA nodes.

        Returns:
            Compiled LangGraph workflow
        """
        workflow = StateGraph(StoryState)

        # Add nodes
        workflow.add_node("spawn_sm", self._spawn_sm_agent)

        # Phase 2: Add more nodes
        # workflow.add_node("spawn_po", self._spawn_po_agent)
        # workflow.add_node("spawn_dev", self._spawn_dev_agent)
        # workflow.add_node("spawn_qa", self._spawn_qa_agent)

        # Set entry point
        workflow.set_entry_point("spawn_sm")

        # For Phase 1: SM goes directly to END
        workflow.add_edge("spawn_sm", END)

        # Phase 2: Add conditional edges
        # workflow.add_conditional_edges(
        #     "spawn_po",
        #     self._route_po_decision,
        #     {
        #         "approved": "spawn_dev",
        #         "blocked": END,
        #         "changes": END
        #     }
        # )

        return workflow.compile()

    async def _spawn_sm_agent(self, state: StoryState) -> StoryState:
        """
        Spawn SM agent in tmux to create story file.

        SM agent:
        1. Is spawned in isolated tmux session
        2. Loads BMad SM persona via /sm slash command
        3. Executes *create task
        4. Loads full architecture docs and epic files
        5. Creates comprehensive story file

        Args:
            state: Current story state

        Returns:
            Updated state with story_file_path or error
        """
        print(f"\n→ SM: Creating story {state['story_id']}")
        print(f"  Project: {self.project_path}")

        # Spawn tmux session with SM agent
        try:
            session_id = self.tmux_mgr.spawn_agent_session(
                agent="sm",
                story_id=state['story_id'],
                commands=["/sm", "*create"],
                wait_for_ready=5.0
            )

            state['tmux_session_id'] = session_id
            state['current_stage'] = 'sm'

        except Exception as e:
            print(f"  ✗ Failed to spawn SM session: {e}")
            state['current_stage'] = 'failed'
            state['error_message'] = f'Failed to spawn SM session: {e}'
            return state

        # Wait for story file creation (file-based detection)
        story_file = self.project_path / f"docs/stories/{state['story_id']}.story.md"
        print(f"  Waiting for story file: {story_file}")
        print(f"  Timeout: 10 minutes")

        try:
            success = await wait_for_sm_completion(story_file, timeout=600)

            if success:
                print(f"  ✓ Story file created: {story_file}")
                print(f"    Size: {story_file.stat().st_size} bytes")
                state['story_file_path'] = str(story_file)
                state['current_stage'] = 'complete'  # Phase 1: SM only
            else:
                print(f"  ✗ SM timed out (no story file created)")
                state['current_stage'] = 'failed'
                state['error_message'] = 'SM timeout: Story file not created within 10 minutes'

        except Exception as e:
            print(f"  ✗ Error waiting for story file: {e}")
            state['current_stage'] = 'failed'
            state['error_message'] = f'Error monitoring story file: {e}'

        # Cleanup tmux session (context cleared)
        print(f"  Cleaning up tmux session...")
        try:
            self.tmux_mgr.kill_session(session_id)
            print(f"  ✓ Context cleared (session killed)")
        except Exception as e:
            print(f"  Warning: Failed to kill session: {e}")

        return state

    async def process_story(self, story_id: str) -> dict:
        """
        Process single story through workflow.

        For Phase 1 (MVP): Only SM stage is processed.

        Args:
            story_id: Story identifier (e.g., "1.1")

        Returns:
            Dictionary with result:
            {
                'success': bool,
                'stage_reached': str,
                'story_file': str | None,
                'error': str | None
            }

        Example:
            >>> result = await orchestrator.process_story("1.1")
            >>> if result['success']:
            ...     print(f"Story file: {result['story_file']}")
            >>> else:
            ...     print(f"Failed at {result['stage_reached']}: {result['error']}")
        """
        print(f"\n{'='*60}")
        print(f"Processing Story {story_id}")
        print(f"{'='*60}")

        # Initialize state
        initial_state = StoryState(
            story_id=story_id,
            current_stage="sm",
            story_file_path="",
            tmux_session_id="",
            po_decision="",
            dev_files_modified=[],
            qa_test_results="",
            error_message=""
        )

        # Run through LangGraph workflow
        try:
            final_state = await self.workflow.ainvoke(initial_state)
        except Exception as e:
            print(f"\n✗ Workflow error: {e}")
            return {
                'success': False,
                'stage_reached': 'workflow_error',
                'story_file': None,
                'error': str(e)
            }

        # Build result
        success = final_state['current_stage'] == 'complete'
        result = {
            'success': success,
            'stage_reached': final_state['current_stage'],
            'story_file': final_state.get('story_file_path'),
            'error': final_state.get('error_message')
        }

        # Print summary
        print(f"\n{'='*60}")
        if success:
            print(f"✓ Story {story_id} COMPLETE")
            print(f"  Story file: {result['story_file']}")
        else:
            print(f"✗ Story {story_id} FAILED")
            print(f"  Stage: {result['stage_reached']}")
            print(f"  Error: {result['error']}")
        print(f"{'='*60}\n")

        return result

    def cleanup(self):
        """
        Cleanup all resources.

        Kills all managed tmux sessions.
        Call this on shutdown or error to ensure clean state.
        """
        print("\n→ Cleaning up orchestrator...")
        self.tmux_mgr.kill_all_sessions()
        print("  ✓ Cleanup complete")


# Phase 2: Additional node implementations will go here
# async def _spawn_po_agent(self, state: StoryState) -> StoryState:
#     ...
#
# async def _spawn_dev_agent(self, state: StoryState) -> StoryState:
#     ...
#
# async def _spawn_qa_agent(self, state: StoryState) -> StoryState:
#     ...
#
# def _route_po_decision(self, state: StoryState) -> str:
#     ...
