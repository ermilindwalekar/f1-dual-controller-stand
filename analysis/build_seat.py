import json

import numpy as np
import trimesh

from analysis.cradle_fit import PROJECT, SCAN_PATH, pose_matrix


PITCH = 30
FORE_AFT = -28
REFERENCE_HEIGHT = 32
HARD_CLEARANCE = 1.25
PAD_SURFACE_OFFSET = 0.10
PAD_MIN_THICKNESS = 2.0
PAD_SPECS = [
    {"center": [-16, -42], "size": [10, 8]},
    {"center": [16, -42], "size": [10, 8]},
    {"center": [0, -22], "size": [14, 10]},
]


def sample_underside(scan, lateral, fore_aft):
    origins = np.array(
        [[horizontal, depth, -100.0] for depth in fore_aft for horizontal in lateral]
    )
    directions = np.tile([0.0, 0.0, 1.0], (len(origins), 1))
    locations, ray_indices, triangle_indices = scan.ray.intersects_location(
        origins, directions, multiple_hits=False
    )
    heights = np.full(len(origins), np.nan)
    heights[ray_indices] = locations[:, 2]
    if not np.isfinite(heights).all():
        raise ValueError("The selected support area extends beyond the scanned shell")
    return heights.reshape(len(fore_aft), len(lateral))


def heightfield_solid(lateral, fore_aft, heights, bottom):
    top = np.array(
        [
            [horizontal, depth, heights[depth_index, horizontal_index]]
            for depth_index, depth in enumerate(fore_aft)
            for horizontal_index, horizontal in enumerate(lateral)
        ]
    )
    assert top[:, 2].min() > bottom
    underside = top.copy()
    underside[:, 2] = bottom
    vertex_count = len(top)
    row_length = len(lateral)
    faces = []
    for row_index in range(len(fore_aft) - 1):
        for column_index in range(row_length - 1):
            vertex = row_index * row_length + column_index
            corners = [vertex, vertex + 1, vertex + row_length + 1, vertex + row_length]
            for triangle in [corners[:3], [corners[0], corners[2], corners[3]]]:
                faces.append(triangle)
                faces.append([index + vertex_count for index in reversed(triangle)])
    perimeter = (
        list(range(row_length))
        + [row * row_length + row_length - 1 for row in range(1, len(fore_aft))]
        + list(range(vertex_count - 2, vertex_count - row_length - 1, -1))
        + [row * row_length for row in range(len(fore_aft) - 2, 0, -1)]
    )
    for edge_index, current in enumerate(perimeter):
        following = perimeter[(edge_index + 1) % len(perimeter)]
        faces.extend(
            [
                [current + vertex_count, following + vertex_count, following],
                [current + vertex_count, following, current],
            ]
        )
    mesh = trimesh.Trimesh(vertices=np.vstack([top, underside]), faces=faces)
    assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0
    return mesh


def build_seat():
    destination = PROJECT / "generated"
    destination.mkdir(exist_ok=True)
    scan = trimesh.load_mesh(SCAN_PATH)
    preview = scan.simplify_quadric_decimation(face_count=40000)
    preview.export(destination / "controller_preview.stl")
    scan.apply_transform(pose_matrix(PITCH, FORE_AFT, REFERENCE_HEIGHT))
    lateral = np.arange(-26.0, 26.01, 1.0)
    fore_aft = np.arange(-47.0, -14.99, 1.0)
    heights = sample_underside(scan, lateral, fore_aft)
    seat = heightfield_solid(lateral, fore_aft, heights - HARD_CLEARANCE, 3.0)
    seat.export(destination / "central_seat.stl")

    pads = []
    for pad_index, specification in enumerate(PAD_SPECS):
        center = np.asarray(specification["center"])
        size = np.asarray(specification["size"])
        lateral = np.arange(center[0] - size[0] / 2, center[0] + size[0] / 2 + 0.01, 0.5)
        fore_aft = np.arange(center[1] - size[1] / 2, center[1] + size[1] / 2 + 0.01, 0.5)
        heights = sample_underside(scan, lateral, fore_aft) - PAD_SURFACE_OFFSET
        bottom = float(heights.min() - PAD_MIN_THICKNESS)
        pad = heightfield_solid(lateral, fore_aft, heights, bottom)
        pad.export(destination / f"seat_pad_{pad_index}.stl")
        pads.append({**specification, "bottom": bottom, "triangles": len(pad.faces)})

    configuration = {
        "seat_controller_pitch": PITCH,
        "seat_controller_y": FORE_AFT,
        "seat_controller_height": REFERENCE_HEIGHT - PAD_SURFACE_OFFSET,
        "seat_hard_clearance": HARD_CLEARANCE,
        "seat_pad_centers": [pad["center"] for pad in pads],
        "seat_pad_sizes": [pad["size"] for pad in pads],
        "seat_pad_bottoms": [pad["bottom"] for pad in pads],
    }
    (destination / "seat_config.scad").write_text(
        "\n".join(f"{name} = {json.dumps(value)};" for name, value in configuration.items()) + "\n",
        encoding="ascii",
    )
    manifest = {
        **configuration,
        "reference": str(SCAN_PATH.relative_to(PROJECT)),
        "reference_triangles": len(scan.faces),
        "preview_triangles": len(preview.faces),
        "body_surface_gap_mm": HARD_CLEARANCE,
        "seat_triangles": len(seat.faces),
        "pads": pads,
    }
    (destination / "seat_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="ascii"
    )
    print(json.dumps(manifest, indent=2), flush=True)
    return manifest


if __name__ == "__main__":
    build_seat()