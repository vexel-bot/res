"""One media API surface, reused by both authentication entrypoints."""

from .routers import (
    editing_resources,
    motion_gemini,
    product_evolution,
    studio_agents,
    studio_copy_workflow,
    studio_ad_materials,
    studio_department,
    studio_identity_library,
    studio_openrouter_media,
    studio_project_avatar,
    studio_project_narration,
    studio_video,
    studios,
)
from .config import get_settings


def include_studio_routes(app):
    for router in (
        studios.router,
        studio_copy_workflow.router,
        studio_ad_materials.router,
        studio_department.router,
        studio_video.router,
        studio_video.archive_router,
        studio_openrouter_media.router,
        studio_agents.router,
        motion_gemini.router,
        editing_resources.router,
        studio_identity_library.router,
        studio_project_narration.router,
        studio_project_avatar.router,
        product_evolution.router,
    ):
        app.include_router(router, prefix="/api/v1")
    if get_settings().studio_legacy_craft_enabled:
        from .routers import studio_craft

        app.include_router(studio_craft.router, prefix="/api/v1")
