"""Navigation context tracker — tracks elder's progress through multi-step tasks."""

import logging
from typing import Optional

from app.models.navigator import NavigationContext, ScreenAnalysis

logger = logging.getLogger(__name__)


class NavigationTracker:
    """Tracks an elder's progress through a navigator or assist task."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.context = NavigationContext()
        self.history: list[ScreenAnalysis] = []

    def set_task(self, task_description: str, estimated_steps: list[str] = None):
        """Set the current task and optional estimated steps."""
        self.context.task = task_description
        self.context.steps_remaining = estimated_steps or []
        self.context.steps_completed = []
        self.context.task_completed = False
        self.context.stuck_count = 0

    def update(self, analysis: ScreenAnalysis) -> NavigationContext:
        """Update context based on a new screen analysis."""
        self.history.append(analysis)
        self.context.screens_analyzed += 1

        # Update current screen info
        self.context.current_app = analysis.app_name
        self.context.current_screen = analysis.screen_description

        # Detect stuck state
        if analysis.is_same_as_previous:
            self.context.stuck_count += 1
        else:
            self.context.stuck_count = 0

        # Check if a step was completed (screen changed and we had remaining steps)
        if not analysis.is_same_as_previous and self.context.steps_remaining:
            completed_step = self.context.steps_remaining.pop(0)
            self.context.steps_completed.append(completed_step)

            # Check task completion
            if not self.context.steps_remaining:
                self.context.task_completed = True

        return self.context

    def get_encouragement(self) -> Optional[str]:
        """Get contextual encouragement message based on current state."""
        if self.context.task_completed:
            return "You did it! That wasn't so hard, was it?"

        if self.context.stuck_count >= 3:
            return "No worries, let me try explaining that differently."

        if self.context.stuck_count >= 5:
            return "We can try again next time if you'd like. You're doing great for trying!"

        if len(self.context.steps_completed) == 1:
            return "Great job! One step done."

        if len(self.context.steps_completed) > 1:
            remaining = len(self.context.steps_remaining)
            if remaining > 0:
                return f"You're doing wonderful! Just {remaining} more step{'s' if remaining > 1 else ''} to go."

        return None

    def to_dict(self) -> dict:
        """Serialize context for storage."""
        return self.context.model_dump()
