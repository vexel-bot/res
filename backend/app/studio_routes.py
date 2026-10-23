"""One media API surface, reused by both authentication entrypoints."""

from .routers import editing_resources, studio_agents, studio_craft, studio_department, studio_video, studios


def include_studio_routes(app):
    for router in (
        studios.router,
        studio_craft.router,
        studio_department.router,
        studio_video.router,
        studio_agents.router,
        editing_resources.router,
    ):
        app.include_router(router, prefix="/api/v1")
