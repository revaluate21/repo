from __future__ import annotations

import asyncio

from orchestrator import parse_args, run


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
