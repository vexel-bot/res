"""Historical Alight capability metadata. Execution was replaced by Craft."""

from ...domain.studios.motion_recipes import RECIPE_CAPABILITIES

NAME = "alight-motion.contextual-v1"


def required_capabilities(document):
    capabilities = {
        RECIPE_CAPABILITIES[recipe["technique"]]
        for recipe in document.composition.narrative.get("editorialV2", {}).get("motionRecipes", [])
    }
    for page in document.composition.pages:
        for layer in page.layers:
            if not layer.visible:
                continue
            capabilities.add("composition." + layer.kind)
            component = layer.properties.get("nativeComponent")
            if component:
                capabilities.add(f"native.{component['component']}.v{component['version']}")
            for effect in layer.properties.get("effects", []):
                capabilities.add("effect." + effect["kind"])
    return capabilities


def refresh_registration(settings, registry):
    registry.pop(NAME, None)
    return {"provider": NAME, "available": False, "blockers": ["editor_replaced_by_effectcraft"], "capabilities": []}
