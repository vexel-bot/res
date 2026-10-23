"""Aggregate real job measurements; financial estimates are not provider invoices."""

from sqlalchemy import func, select

from ...models import LibraryAsset, StudioGenerationJob


def metrics(db, workspace_id, user_id):
    def jobs(actor=None):
        fields = [
            func.coalesce(func.sum(StudioGenerationJob.result_payload[name].as_float()), 0)
            for name in ("processingSeconds", "outputVideoSeconds", "generatedVideoSeconds", "estimatedCostUsd")
        ]
        query = select(*fields).where(StudioGenerationJob.workspace_id == workspace_id)
        if actor:
            query = query.where(StudioGenerationJob.requested_by == actor)
        values = db.execute(query).one()
        return dict(
            zip(
                ("processingSeconds", "outputVideoSeconds", "generatedVideoSeconds", "estimatedCostUsd"),
                map(float, values),
                strict=True,
            )
        )

    size = db.scalar(
        select(func.coalesce(func.sum(LibraryAsset.size_bytes), 0)).where(
            LibraryAsset.workspace_id == workspace_id, LibraryAsset.lifecycle_status == "active"
        )
    )
    return {
        "workspace": {**jobs(), "storedBytes": int(size)},
        "currentUser": jobs(user_id),
        "commercialVideoPolicy": "generated_scenes_only",
        "costCurrency": "USD",
        "providerReportedCostUsd": None,
        "invoiceReconciliation": "not_connected",
    }
