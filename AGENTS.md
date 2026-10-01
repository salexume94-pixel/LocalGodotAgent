# Local Godot Agent Instructions

## Purpose
This agent is a local development assistant for the Godot project.

## Core Rules
- Read AGENTS.md as permanent instructions.
- Load AGENT_MEMORY.md for every request.
- Retrieve DEVELOPMENT_LOG.md only when historically relevant.
- Inspect actual project source before proposing or making changes.
- Treat Godot source code as authoritative.
- Use AGENT_MEMORY.md for navigation and context, not as a replacement for source code.
- Use DEVELOPMENT_LOG.md for historical context.
- Give Ollama only relevant evidence.
- Ollama provides reasoning, not truth.
- Make minimal, clean changes.
- Preserve existing architecture unless there is a concrete reason to change it.
- Avoid unnecessary rewrites.
- Update AGENT_MEMORY.md when major architecture, paths, systems, or known bugs change.
- Update DEVELOPMENT_LOG.md when significant development work is completed.