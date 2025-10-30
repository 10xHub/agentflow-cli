"""
Thread name generation utilities for AI agent conversations.

This module provides the AIThreadNameGenerator class and helper function for generating
meaningful, varied, and human-friendly thread names for AI chat sessions using different
patterns and themes.

Classes:
    AIThreadNameGenerator: Generates thread names using adjective-noun, action-based,
    and compound patterns.

Functions:
    generate_dummy_thread_name: Convenience function for generating a thread name.
"""

import secrets
from abc import ABC, abstractmethod


class AIThreadNameGenerator:
    """
    Generates meaningful, varied thread names for AI conversations using different
    patterns and themes. Patterns include adjective-noun, action-based, and compound
    descriptive names.

    Example:
        >>> AIThreadNameGenerator().generate_name()
        'thoughtful-dialogue'
    """

    # Enhanced adjectives grouped by semantic meaning
    ADJECTIVES = [
        # Intellectual
        "thoughtful",
        "insightful",
        "analytical",
        "logical",
        "strategic",
        "methodical",
        "systematic",
        "comprehensive",
        "detailed",
        "precise",
        # Creative
        "creative",
        "imaginative",
        "innovative",
        "artistic",
        "expressive",
        "original",
        "inventive",
        "inspired",
        "visionary",
        "whimsical",
        # Emotional/Social
        "engaging",
        "collaborative",
        "meaningful",
        "productive",
        "harmonious",
        "enlightening",
        "empathetic",
        "supportive",
        "encouraging",
        "uplifting",
        # Dynamic
        "dynamic",
        "energetic",
        "vibrant",
        "lively",
        "spirited",
        "active",
        "flowing",
        "adaptive",
        "responsive",
        "interactive",
        # Quality-focused
        "focused",
        "dedicated",
        "thorough",
        "meticulous",
        "careful",
        "patient",
        "persistent",
        "resilient",
        "determined",
        "ambitious",
    ]

    # Enhanced nouns with more conversational context
    NOUNS = [
        # Conversation-related
        "dialogue",
        "conversation",
        "discussion",
        "exchange",
        "chat",
        "consultation",
        "session",
        "meeting",
        "interaction",
        "communication",
        # Journey/Process
        "journey",
        "exploration",
        "adventure",
        "quest",
        "voyage",
        "expedition",
        "discovery",
        "investigation",
        "research",
        "study",
        # Conceptual
        "insight",
        "vision",
        "perspective",
        "understanding",
        "wisdom",
        "knowledge",
        "learning",
        "growth",
        "development",
        "progress",
        # Solution-oriented
        "solution",
        "approach",
        "strategy",
        "method",
        "framework",
        "plan",
        "blueprint",
        "pathway",
        "route",
        "direction",
        # Creative/Abstract
        "canvas",
        "story",
        "narrative",
        "symphony",
        "composition",
        "creation",
        "masterpiece",
        "design",
        "pattern",
        "concept",
        # Collaborative
        "partnership",
        "collaboration",
        "alliance",
        "connection",
        "bond",
        "synergy",
        "harmony",
        "unity",
        "cooperation",
        "teamwork",
    ]

    # Action-based patterns for more dynamic names
    ACTION_PATTERNS = {
        "exploring": ["ideas", "concepts", "possibilities", "mysteries", "frontiers", "depths"],
        "building": ["solutions", "understanding", "connections", "frameworks", "bridges"],
        "discovering": ["insights", "patterns", "answers", "truths", "secrets", "wisdom"],
        "crafting": ["responses", "solutions", "stories", "strategies", "experiences"],
        "navigating": ["challenges", "questions", "complexities", "territories", "paths"],
        "unlocking": ["potential", "mysteries", "possibilities", "creativity", "knowledge"],
        "weaving": ["ideas", "stories", "connections", "patterns", "narratives"],
        "illuminating": ["concepts", "mysteries", "paths", "truths", "possibilities"],
    }

    # Descriptive compound patterns
    COMPOUND_PATTERNS = [
        ("deep", ["dive", "thought", "reflection", "analysis", "exploration"]),
        ("bright", ["spark", "idea", "insight", "moment", "flash"]),
        ("fresh", ["perspective", "approach", "start", "take", "view"]),
        ("open", ["dialogue", "discussion", "conversation", "exchange", "forum"]),
        ("creative", ["flow", "spark", "burst", "stream", "wave"]),
        ("mindful", ["moment", "pause", "reflection", "consideration", "thought"]),
        ("collaborative", ["effort", "venture", "journey", "exploration", "creation"]),
    ]

    def generate_simple_name(self, separator: str = "-") -> str:
        """
        Generate a simple adjective-noun combination for a thread name.

        Args:
            separator (str): String to separate words (default: "-").

        Returns:
            str: Name like "thoughtful-dialogue" or "creative-exploration".

        Example:
            >>> AIThreadNameGenerator().generate_simple_name()
            'creative-exploration'
        """
        adj = secrets.choice(self.ADJECTIVES)
        noun = secrets.choice(self.NOUNS)
        return f"{adj}{separator}{noun}"

    def generate_action_name(self, separator: str = "-") -> str:
        """
        Generate an action-based thread name for a more dynamic feel.

        Args:
            separator (str): String to separate words (default: "-").

        Returns:
            str: Name like "exploring-ideas" or "building-understanding".

        Example:
            >>> AIThreadNameGenerator().generate_action_name()
            'building-connections'
        """
        action = secrets.choice(list(self.ACTION_PATTERNS.keys()))
        target = secrets.choice(self.ACTION_PATTERNS[action])
        return f"{action}{separator}{target}"

    def generate_compound_name(self, separator: str = "-") -> str:
        """
        Generate a compound descriptive thread name.

        Args:
            separator (str): String to separate words (default: "-").

        Returns:
            str: Name like "deep-dive" or "bright-spark".

        Example:
            >>> AIThreadNameGenerator().generate_compound_name()
            'deep-reflection'
        """
        base, options = secrets.choice(self.COMPOUND_PATTERNS)
        complement = secrets.choice(options)
        return f"{base}{separator}{complement}"

    def generate_name(self, separator: str = "-") -> str:
        """
        Generate a meaningful thread name using random pattern selection.

        Args:
            separator (str): String to separate words (default: "-").

        Returns:
            str: A meaningful thread name from various patterns.

        Example:
            >>> AIThreadNameGenerator().generate_name()
            'engaging-discussion'
        """
        # Randomly choose between different naming patterns
        pattern = secrets.choice(["simple", "action", "compound"])

        if pattern == "simple":
            return self.generate_simple_name(separator)
        if pattern == "action":
            return self.generate_action_name(separator)
        # compound
        return self.generate_compound_name(separator)


class ThreadNameGenerator(ABC):
    """Deprecated class for generating thread names.

    Use AIThreadNameGenerator instead.
    """

    @abstractmethod
    async def generate_name(self, messages: list[str]) -> str:
        """Generate a thread name using the list of message text.

        Args:
            messages (list[str]): List of message text.

        Returns:
            str: A meaningful thread name.

        Example:
            >>> ThreadNameGenerator().generate_name()
            'insightful-conversation'
        """


class DummyThreadNameGenerator(ThreadNameGenerator):
    """Deprecated dummy thread name generator.

    Use AIThreadNameGenerator instead.
    """

    async def generate_name(self, messages: list[str]) -> str:
        """Generate a dummy thread name.

        Args:
            messages (list[str]): List of message text.

        Returns:
            str: A meaningful thread name.

        Example:
            >>> DummyThreadNameGenerator().generate_name()
            'thoughtful-dialogue'
        """
        generator = AIThreadNameGenerator()
        return generator.generate_name("-")
