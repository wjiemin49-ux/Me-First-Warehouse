import random

import bpy


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def make_metal_material(name):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (
        random.random(),
        random.random(),
        random.random(),
        1.0,
    )
    bsdf.inputs["Metallic"].default_value = 1.0
    bsdf.inputs["Roughness"].default_value = random.uniform(0.1, 0.6)
    return material


def main():
    clear_scene()

    bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
    plane = bpy.context.active_object
    plane.name = "Ground"

    for i in range(100):
        size = random.uniform(0.2, 1.0)
        x = random.uniform(-5 + size / 2, 5 - size / 2)
        y = random.uniform(-5 + size / 2, 5 - size / 2)
        z = size / 2

        bpy.ops.mesh.primitive_cube_add(size=size, location=(x, y, z))
        cube = bpy.context.active_object
        cube.name = f"Cube_{i:03d}"

        material = make_metal_material(f"Metal_{i:03d}")
        cube.data.materials.append(material)


if __name__ == "__main__":
    main()
