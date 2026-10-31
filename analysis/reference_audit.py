import argparse
import json
from pathlib import Path

import matplotlib
import trimesh

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


def inspect_reference(mesh_path, image_path):
    mesh = trimesh.load_mesh(mesh_path)
    components = mesh.split(only_watertight=False) if len(mesh.faces) < 100000 else None
    summary = {
        "file": str(mesh_path),
        "units": mesh.units,
        "vertices": len(mesh.vertices),
        "triangles": len(mesh.faces),
        "bounds_raw_units": mesh.bounds.tolist(),
        "extents_raw_units": mesh.extents.tolist(),
        "watertight": bool(mesh.is_watertight),
        "consistent_winding": bool(mesh.is_winding_consistent),
        "connected_components": len(components) if components is not None else None,
        "largest_component_triangles": sorted(
            [len(component.faces) for component in components], reverse=True
        )[:10] if components is not None else None,
    }
    print(json.dumps(summary, indent=2), flush=True)

    if image_path is None:
        return

    display_mesh = mesh.copy()
    if len(display_mesh.faces) > 20000:
        display_mesh = display_mesh.simplify_quadric_decimation(face_count=20000)
    center = mesh.bounds.mean(axis=0)
    radius = mesh.extents.max() * 0.55
    figure = plt.figure(figsize=(12, 10))
    views = [(25, -60, "Oblique"), (90, -90, "XY"), (0, -90, "XZ"), (0, 0, "YZ")]
    for panel_index, (elevation, azimuth, title) in enumerate(views, start=1):
        axis = figure.add_subplot(2, 2, panel_index, projection="3d")
        axis.add_collection3d(
            Poly3DCollection(
                display_mesh.triangles,
                facecolors="#69aeb9",
                linewidths=0,
                shade=True,
            )
        )
        axis.set_xlim(center[0] - radius, center[0] + radius)
        axis.set_ylim(center[1] - radius, center[1] + radius)
        axis.set_zlim(center[2] - radius, center[2] + radius)
        axis.set_box_aspect((1, 1, 1))
        axis.set_proj_type("ortho")
        axis.view_init(elev=elevation, azim=azimuth)
        axis.set_title(title)
        axis.set_xlabel("X (raw units)")
        axis.set_ylabel("Y (raw units)")
        axis.set_zlabel("Z (raw units)")
    figure.suptitle(f"Actual mesh: {mesh_path.name}")
    figure.tight_layout()
    image_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(image_path, dpi=150)
    plt.close(figure)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mesh", type=Path)
    parser.add_argument("--image", type=Path)
    arguments = parser.parse_args()
    inspect_reference(arguments.mesh, arguments.image)