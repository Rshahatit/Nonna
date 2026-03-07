"""Services package. Routes storage backend based on USE_LOCAL_STORAGE env var."""

import os

if os.environ.get("USE_LOCAL_STORAGE", "").lower() in ("true", "1", "yes"):
    from app.services import local_storage as firestore
else:
    from app.services import firestore  # type: ignore[no-redef]
