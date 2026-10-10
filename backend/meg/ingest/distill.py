"""Keep the shortest verified route through a successful agent trace."""

from __future__ import annotations

from meg.models import EventType, TraceEvent


def distill(events: list[TraceEvent]) -> list[TraceEvent]:
    """Remove failed commands and abandoned branch work before final verification.

    The final exit-zero command is the verification point.  We retain reads/searches
    that establish context, then retain only actions after the last failing command
    before verification, plus the verifier itself.  This deliberately favors a
    short repeatable procedure over a full debugging transcript.
    """
    successful = [index for index, event in enumerate(events)
                  if event.type is EventType.COMMAND and event.exit_code == 0]
    if not successful:
        return []
    verified_at = successful[-1]
    relevant = events[: verified_at + 1]
    last_failure = max((index for index, event in enumerate(relevant)
                        if event.type is EventType.COMMAND and event.exit_code not in (None, 0)), default=-1)
    context = [event for event in relevant[:last_failure] if event.type in (EventType.READ, EventType.SEARCH)]
    solution = [event for event in relevant[last_failure + 1:] if event.exit_code in (None, 0)]
    return context + solution
