import bpy
from mathutils import Vector

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 6
scene.frame_start, scene.frame_end = 1, 24

bpy.ops.mesh.primitive_uv_sphere_add(radius=0.9, location=(0, 0, 0.55))
sphere = bpy.context.object
sphere.name = 'Collider'
sphere.modifiers.new('Collision', 'COLLISION')
for polygon in sphere.data.polygons:
    polygon.use_smooth = True
green = bpy.data.materials.new('Jade')
green.diffuse_color = (0.08, 0.52, 0.29, 1)
sphere.data.materials.append(green)

bpy.ops.mesh.primitive_grid_add(x_subdivisions=20, y_subdivisions=20, size=3, location=(0, 0, 2.2))
cloth = bpy.context.object
cloth.name = 'Suspended cloth'
cloth_modifier = cloth.modifiers.new('Cloth', 'CLOTH')
cloth_modifier.settings.quality = 5
cloth_modifier.point_cache.frame_start = 1
cloth_modifier.point_cache.frame_end = 24
cloth.modifiers.new('Thickness', 'SOLIDIFY').thickness = 0.012
gold = bpy.data.materials.new('Orange silk')
gold.diffuse_color = (0.85, 0.19, 0.035, 1)
cloth.data.materials.append(gold)

bpy.ops.object.camera_add(location=(4.5, -5.6, 3.6))
camera = bpy.context.object
scene.camera = camera
camera.data.lens = 43
def aim(position):
    camera.location = position
    camera.rotation_euler = (Vector((0, 0, 1.25)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
for frame, position in ((1, (4.5, -5.6, 3.6)), (24, (2.6, -6.2, 2.9))):
    aim(position)
    camera.keyframe_insert(data_path='location', frame=frame)
    camera.keyframe_insert(data_path='rotation_euler', frame=frame)
bpy.ops.object.light_add(type='AREA', location=(2, -4, 6))
light = bpy.context.object
light.data.energy = 1050
light.data.shape = 'DISK'
light.data.size = 4
light.rotation_euler = (-light.location).to_track_quat('-Z', 'Y').to_euler()

scene.frame_set(1)
with bpy.context.temp_override(point_cache=cloth_modifier.point_cache):
    bpy.ops.ptcache.bake(bake=True)
