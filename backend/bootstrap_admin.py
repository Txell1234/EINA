"""Initialize DB tables and create admin@osint.local (Option A)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database import Base, engine
import models  # noqa: F401
from create_user import create_initial_user


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[OK] Base de dades inicialitzada")
    await create_initial_user()


if __name__ == "__main__":
    asyncio.run(main())
