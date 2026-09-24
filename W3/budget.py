"""budget.py: the guardrail that stops two agents looping forever.

This file is COMPLETE. You do not need to change it. Use it everywhere you
run a model in a loop. See ../cost-and-safety.md for why all three limits matter.
"""
import time


class Budget:
    """Enforces three independent stop conditions plus an optional goal stop.

    Usage:
        b = Budget(max_turns=12, max_tokens=4000, max_seconds=120)
        while not b.exhausted():
            reply = ...                 # call the model
            b.record(turns=1, tokens=reply.tokens)
            if goal_met: b.stop("goal_reached")
        print(b.stop_reason)            # which limit fired
    """

    def __init__(self, max_turns=10, max_tokens=4000, max_seconds=120):
        self.max_turns = max_turns
        self.max_tokens = max_tokens
        self.max_seconds = max_seconds
        self.turns = 0
        self.tokens = 0
        self._start = None
        self.stop_reason = None

    def start(self):
        self._start = time.monotonic()
        return self

    @property
    def elapsed(self):
        return 0.0 if self._start is None else time.monotonic() - self._start

    def record(self, turns=0, tokens=0):
        """Call once per completed turn with that turn's cost."""
        self.turns += turns
        self.tokens += tokens

    def stop(self, reason):
        """Force a stop for a domain reason (e.g. 'goal_reached')."""
        if self.stop_reason is None:
            self.stop_reason = reason

    def exhausted(self):
        """True when any limit is reached. Starts the clock on first call."""
        if self._start is None:
            self.start()
        if self.stop_reason is not None:
            return True
        if self.turns >= self.max_turns:
            self.stop("max_turns")
            return True
        if self.tokens >= self.max_tokens:
            self.stop("max_tokens")
            return True
        if self.elapsed >= self.max_seconds:
            self.stop("max_seconds")
            return True
        return False

    def summary(self):
        return {
            "stop_reason": self.stop_reason,
            "turns": self.turns,
            "tokens": self.tokens,
            "seconds": round(self.elapsed, 3),
            "limits": {
                "max_turns": self.max_turns,
                "max_tokens": self.max_tokens,
                "max_seconds": self.max_seconds,
            },
        }
