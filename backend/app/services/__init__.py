"""Services package. Routes storage backend based on USE_LOCAL_STORAGE env var."""

import os
import sys

if os.environ.get("USE_LOCAL_STORAGE", "").lower() in ("true", "1", "yes"):
    from app.services import local_storage as firestore
    from app.services import local_storage_families as firestore_families

    # Register the local modules under the real module names so that direct
    # imports like `from app.services.firestore import get_db` also resolve
    # to the in-memory implementations.
    sys.modules["app.services.firestore"] = local_storage  # type: ignore[assignment]
    sys.modules["app.services.firestore_families"] = local_storage_families  # type: ignore[assignment]
else:
    from app.services import firestore  # type: ignore[no-redef]
    from app.services import firestore_families  # type: ignore[no-redef]
