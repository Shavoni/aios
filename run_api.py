"""Run the AIOS API server."""

import uvicorn

from packages.api import app
from packages.api.config import Settings

if __name__ == "__main__":
    settings = Settings()
    uvicorn.run(
        "packages.api:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
