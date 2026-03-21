#!/usr/bin/env python3
"""Run the Quota Manager service."""

import os
import uvicorn

from app.core.logging_config import configure_logging

if __name__ == "__main__":
    configure_logging(os.getenv("LOG_LEVEL", "INFO"))
    port = int(os.getenv("PORT", "8002"))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("RELOAD", "false").lower() == "true",
    )
