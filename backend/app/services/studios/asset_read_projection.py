"""Small read views of existing assets; never partially hydrated ORM identities."""
import json
from types import SimpleNamespace

from sqlalchemy import func, select

from ...models import LibraryAsset

ASSET_FIELDS = (
    "id", "workspace_id", "title", "asset_type", "tags", "campaign_id", "content_id", "url",
    "storage_key", "storage_backend", "media_type", "size_bytes", "checksum_sha256", "lifecycle_status",
    "created_at", "updated_at",
)


def project_assets(db, statement, metadata_paths):
    # Existing in-memory metadata (including untracked nested mutations) wins
    # under the prior reader. Other dialects retain their original ORM path.
    if not hasattr(db, "get_bind") or db.get_bind().dialect.name != "sqlite":
        return None
    if any(isinstance(item, LibraryAsset) for item in db.identity_map.values()):
        return None
    ancestors = sorted({path[:length] for path in metadata_paths for length in range(1, len(path))})
    columns = [getattr(LibraryAsset, name).label(name) for name in ASSET_FIELDS]
    columns.append(func.json_type(LibraryAsset.object_metadata))
    for path in ancestors:
        columns.append(func.json_type(LibraryAsset.object_metadata, "$." + ".".join(path)))
    for path in metadata_paths:
        json_path = "$." + ".".join(path)
        # One full path avoids constructing/quoting large parent JSON objects
        # when a small nested receipt/direction is the only requested value.
        columns.extend([func.json_extract(LibraryAsset.object_metadata, json_path),
                        func.json_type(LibraryAsset.object_metadata, json_path)])
    rows = db.execute(statement.with_only_columns(*columns, maintain_column_froms=True)).all()
    first_type = len(ASSET_FIELDS)
    # Preserve prior handling/errors for malformed containers, rather than
    # substituting a valid-looking metadata object for an invalid stored one.
    if any(row[first_type] != "object" or any(
        value not in {None, "object"} for value in row[first_type + 1:first_type + 1 + len(ancestors)]
    ) for row in rows):
        return None
    views = []
    for row in rows:
        metadata = {}
        offset = first_type + 1 + len(ancestors)
        for index, path in enumerate(metadata_paths):
            value, kind = row[offset + index * 2:offset + index * 2 + 2]
            if kind is None:
                continue  # Missing differs from a present JSON null.
            if kind == "integer" and not isinstance(value, int) or kind == "real" and value == 0:
                # SQLite extraction can lose oversized integer precision or the
                # sign of zero. The original JSON reader preserves both.
                return None
            if kind in {"true", "false"}:
                value = kind == "true"
            elif kind in {"object", "array"}:
                value = json.loads(value)
            container = metadata
            for key in path[:-1]:
                container = container.setdefault(key, {})
            container[path[-1]] = value
        values = dict(zip(ASSET_FIELDS, row[:first_type], strict=True))
        views.append(SimpleNamespace(**values, object_metadata=metadata))
    return views


def project_asset(db, asset_id, metadata_paths):
    rows = project_assets(db, select(LibraryAsset).where(LibraryAsset.id == asset_id), metadata_paths)
    if rows is None:
        return db.get(LibraryAsset, asset_id)
    return rows[0] if rows else None
