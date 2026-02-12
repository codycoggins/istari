"""Gmail digest job — runs at 8am and 2pm daily."""


async def run_gmail_digest() -> None:
    """Scan Gmail, produce actionable digest, queue as notification."""
    raise NotImplementedError
