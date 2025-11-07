from typing import Literal


class PaperStateManager:
    """Very small state manager scaffold.

    Use this class to track paper processing state. Implement a proper state
    machine in later phases.
    """

    def __init__(self) -> None:
        self.state: Literal["new", "fetched", "metadata_ready", "downloaded"] = "new"

    def set_state(self, state: str) -> None:
        self.state = state  # naive acceptance; validate in real impl.
