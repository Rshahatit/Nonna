"""Navigator engine — screen analysis and instruction generation via Gemini multimodal."""

import base64
import json
import logging
from typing import Optional

from google import genai
from google.genai import types

from app.config import get_settings
from app.models.navigator import ScreenAnalysis, NavigationContext

logger = logging.getLogger(__name__)

SCREEN_ANALYSIS_PROMPT = """Analyze this screenshot of an elder's device screen. Respond in JSON with these fields:
{
  "app_name": "name of the app or page visible (e.g., 'Safari', 'Home Screen', 'Settings')",
  "screen_description": "brief plain-language description of what's on screen",
  "ui_elements": ["list of visible interactive elements described by color, position, and label"],
  "suggested_action": "what the user should do next based on the current task context",
  "instruction_text": "elder-friendly instruction using positional language (e.g., 'Tap the blue button near the bottom that says Allow')",
  "is_same_as_previous": false
}

Rules:
- Describe UI elements by visual appearance: color, shape, position on screen
- NEVER use technical jargon (no 'URL bar', 'hamburger menu', 'modal', 'toggle', 'CTA')
- Instructions should be phrased as questions when possible: "Do you see a blue button that says Allow?"
- If the screen looks the same as described in the previous analysis context, set is_same_as_previous to true
- Keep instruction_text to ONE action only — never give multiple steps at once
"""


class NavigatorEngine:
    """Analyzes screenshots and generates elder-friendly navigation instructions."""

    def __init__(self):
        settings = get_settings()
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_model
        self._previous_description: Optional[str] = None

    async def analyze_screenshot(
        self,
        screenshot_base64: str,
        task_context: Optional[str] = None,
        navigation_context: Optional[NavigationContext] = None,
    ) -> ScreenAnalysis:
        """Analyze a screenshot and generate an elder-friendly instruction."""
        try:
            image_bytes = base64.b64decode(screenshot_base64)

            context_parts = [SCREEN_ANALYSIS_PROMPT]

            if task_context:
                context_parts.append(f"\nCurrent task: {task_context}")

            if navigation_context:
                if navigation_context.steps_completed:
                    context_parts.append(
                        f"\nSteps already completed: {', '.join(navigation_context.steps_completed)}"
                    )
                if navigation_context.steps_remaining:
                    context_parts.append(
                        f"\nSteps remaining: {', '.join(navigation_context.steps_remaining)}"
                    )

            if self._previous_description:
                context_parts.append(
                    f"\nPrevious screen was: {self._previous_description}"
                )

            prompt_text = "\n".join(context_parts)

            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=[
                    types.Content(
                        parts=[
                            types.Part(text=prompt_text),
                            types.Part(
                                inline_data=types.Blob(
                                    data=image_bytes,
                                    mime_type="image/jpeg",
                                )
                            ),
                        ]
                    )
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )

            result_text = response.text.strip()
            # Parse JSON response
            data = json.loads(result_text)
            analysis = ScreenAnalysis(**data)

            # Store for next comparison
            self._previous_description = analysis.screen_description

            return analysis

        except Exception as e:
            logger.error(f"Screenshot analysis failed: {e}")
            return ScreenAnalysis(
                screen_description="Could not analyze the screen",
                instruction_text="Can you describe what you see on your screen?",
            )
