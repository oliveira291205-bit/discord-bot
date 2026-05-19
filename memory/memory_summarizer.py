from __future__ import annotations

from collections import Counter

from .memory_types import Memory


def summarize_memories(memories: list[Memory], *, limit: int = 700) -> str:
    if not memories:
        return "Nada salvo ainda."

    by_type = Counter(memory.memory_type for memory in memories)
    tags = Counter(tag for memory in memories for tag in memory.tags)
    important = sorted(memories, key=lambda item: (item.importance, item.updated_at), reverse=True)[:8]
    lines = [
        f"Total: {len(memories)} memorias.",
        "Tipos: " + ", ".join(f"{kind}={count}" for kind, count in by_type.most_common(6)),
    ]
    if tags:
        lines.append("Tags principais: " + ", ".join(tag for tag, _ in tags.most_common(8)))
    lines.append("Mais importantes:")
    lines.extend(f"- {memory.content[:180]}" for memory in important)
    text = "\n".join(lines)
    return text[:limit].rstrip()
