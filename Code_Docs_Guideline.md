# Code Documentation Guideline

This guideline outlines the recommended practices for documenting Python code to make the most out of the `@pdoc` tool.

## General Principles

1. **Clarity**: Documentation should be clear, concise, and easy to understand.
2. **Consistency**: Follow a consistent style and format throughout the codebase.
3. **Completeness**: Ensure that all relevant information is included in the documentation.

## Documenting Python Code
```py
"""
Dog module
"""

class Dog:
    """🐕"""
    name: str
    """The name of our dog."""
    friends: list["Dog"]
    """The friends of our dog."""

    def __init__(self, name: str):
        """Make a Dog without any friends (yet)."""
        self.name = name
        self.friends = []

    def bark(self, loud: bool = True):
        """*woof*"""
```