# Authorized move workflow

Use ordinary agent file tools; the bundled helper only previews and copies.

1. Inventory selected ordinary files. Record original relative path, proposed destination, size and SHA256. Preserve project folders, document companions and linked assets as units.
2. Check the user's requested scope and current file state. Resolve naming conflicts by preserving both, with a clear suffix or unchanged subpath. Do not overwrite an existing destination.
3. Apply only authorized moves. Record each successful source/destination mapping immediately. Stop applying that group if a source changes, becomes a symlink, is unreadable or belongs to an active application.
4. Verify source absence and destination bytes for completed moves; preserve partial results and report unfinished operations. Keep the ledger as the rollback guide. Rolling back also requires checking collisions and current contents.

For files actively edited by another application or a cloud sync client, postpone that group instead of claiming a stable snapshot. A move ledger is evidence of paths, not approval to delete originals or destination copies later.
