import hashlib
import json
from pathlib import Path

import fcl
import numpy as np
import trimesh
from scipy.spatial import ConvexHull

from analysis.cradle_fit import PROJECT, SCAN_PATH, collision_object, pose_matrix, set_pose


CRADLE_LEVELS = [52, 162]
REMOVAL_STEPS = [[0, 0, 5], [0, -70, 0], [0, 0, 30]]
PATH_CLEARANCE = 0.4


def surface_distance(first, second):
    result = fcl.DistanceResult()
    distance = fcl.distance(
        first, second, fcl.DistanceRequest(enable_nearest_points=True), result
    )
    return float(distance), np.asarray(result.nearest_points).tolist()


def trace_translation(moving, fixed, start, displacement):
    length = float(np.linalg.norm(displacement))
    direction = np.asarray(displacement) / length
    travelled = 0.0
    minimum = float("inf")
    samples = 0
    while True:
        transform = start.copy()
        transform[:3, 3] += direction * travelled
        set_pose(moving, transform)
        gap = min(surface_distance(obstacle, moving)[0] for obstacle in fixed)
        if gap <= PATH_CLEARANCE:
            raise AssertionError(f"Removal path blocked at {travelled:.3f} mm: {gap:.4f} mm")
        minimum = min(minimum, gap)
        samples += 1
        if travelled >= length:
            break
        assert samples < 2000, "Removal-path check did not converge"
        travelled = min(length, travelled + min(5.0, (gap-PATH_CLEARANCE) * 0.8))
    return {"minimum_sampled_clearance_mm": minimum, "samples": samples}


def pad_surface_errors(scan, specification, pad_path):
    center = np.asarray(specification["center"])
    size = np.asarray(specification["size"])
    lateral = np.arange(center[0] - size[0] / 2 + 0.05, center[0] + size[0] / 2, 0.25)
    fore_aft = np.arange(center[1] - size[1] / 2 + 0.05, center[1] + size[1] / 2, 0.25)
    origins = np.array([[horizontal, depth, -100.0] for depth in fore_aft for horizontal in lateral])
    directions = np.tile([0.0, 0.0, 1.0], (len(origins), 1))
    locations, ray_indices, triangle_indices = scan.ray.intersects_location(
        origins, directions, multiple_hits=False
    )
    controller_heights = np.full(len(origins), np.nan)
    controller_heights[ray_indices] = locations[:, 2]
    pad = trimesh.load_mesh(pad_path)
    locations, ray_indices, triangle_indices = pad.ray.intersects_location(origins, directions)
    pad_heights = np.full(len(origins), -np.inf)
    np.maximum.at(pad_heights, ray_indices, locations[:, 2])
    assert np.isfinite(controller_heights).all() and np.isfinite(pad_heights).all()
    errors = pad_heights - controller_heights
    return {
        "sample_count": len(origins),
        "maximum_above_scan_mm": float(errors.max()),
        "maximum_below_scan_mm": float(-errors.min()),
        "rms_error_mm": float(np.sqrt(np.mean(errors**2))),
    }


def validate_revision(body_path=None, hard_path=None, check_pads=True):
    body_path = Path(body_path or PROJECT / "f1_dual_controller_stand_body.stl")
    hard_path = Path(hard_path or PROJECT / "analysis" / "revised_hard_assembly.stl")
    configuration = json.loads((PROJECT / "generated" / "seat_manifest.json").read_text())
    body = trimesh.load_mesh(body_path)
    hard = trimesh.load_mesh(hard_path)
    scan = trimesh.load_mesh(SCAN_PATH)
    assert body.is_watertight and len(body.split()) == 1
    ground = body.vertices[np.abs(body.vertices[:, 2]) < 0.00001]
    ground_hull = ConvexHull(ground[:, :2])
    for side in [-1, 1]:
        foot = body.vertices[(side * body.vertices[:, 0] > 40) & (body.vertices[:, 1] < -40)]
        assert abs(foot[:, 2].min()) < 0.00001

    hard_object = collision_object(hard)
    controllers = [collision_object(scan), collision_object(scan)]
    transforms = [
        pose_matrix(configuration["seat_controller_pitch"], configuration["seat_controller_y"],
                    level + configuration["seat_controller_height"])
        for level in CRADLE_LEVELS
    ]
    report = {
        "source_sha256": hashlib.sha256((PROJECT / "f1_dual_controller_stand.scad").read_bytes()).hexdigest(),
        "body_sha256": hashlib.sha256(body_path.read_bytes()).hexdigest(),
        "hard_assembly_sha256": hashlib.sha256(hard_path.read_bytes()).hexdigest(),
        "reference_sha256": hashlib.sha256(SCAN_PATH.read_bytes()).hexdigest(),
        "reference_triangles": len(scan.faces),
        "body_triangles": len(body.faces),
        "body_watertight": bool(body.is_watertight),
        "body_components": len(body.split()),
        "body_bounds_mm": body.bounds.tolist(),
        "ground_contact_hull_mm": ground[ground_hull.vertices].tolist(),
        "levels_mm": CRADLE_LEVELS,
        "removal_steps_mm": REMOVAL_STEPS,
        "removal_clearance_bound_mm": PATH_CLEARANCE,
        "seated": [],
        "removal_paths": [],
    }
    for controller, transform in zip(controllers, transforms):
        set_pose(controller, transform)
        gap, nearest = surface_distance(hard_object, controller)
        assert gap > 0.4, f"Insufficient rigid clearance: {gap}"
        report["seated"].append({"rigid_clearance_mm": gap, "nearest_points_mm": nearest})
    gap, nearest = surface_distance(*controllers)
    assert gap > 7.0, f"Insufficient controller separation: {gap}"
    report["controller_pair"] = {"clearance_mm": gap, "nearest_points_mm": nearest}

    for active_index in range(2):
        other_index = 1 - active_index
        set_pose(controllers[other_index], transforms[other_index])
        transform = transforms[active_index].copy()
        segments = []
        for displacement in REMOVAL_STEPS:
            segments.append(
                trace_translation(controllers[active_index], [hard_object, controllers[other_index]],
                                  transform, displacement)
            )
            transform[:3, 3] += displacement
        report["removal_paths"].append({"level_mm": CRADLE_LEVELS[active_index], "segments": segments})

    for side in [-1, 1]:
        horn_faces = np.flatnonzero(
            np.all(side * hard.triangles[:, :, 0] >= 33, axis=1)
            & np.all(hard.triangles[:, :, 1] >= 16.7, axis=1)
            & np.all(hard.triangles[:, :, 2] >= 165, axis=1)
        )
        horn = hard.submesh([horn_faces], append=True)
        set_pose(controllers[1], transforms[1])
        gap, nearest = surface_distance(collision_object(horn), controllers[1])
        report[f"rear_horn_{side}"] = {"clearance_mm": gap, "nearest_points_mm": nearest}
        assert gap > 5.0, f"Decorative horn too close: {gap}"

    if check_pads:
        scan.apply_transform(pose_matrix(configuration["seat_controller_pitch"],
                                        configuration["seat_controller_y"],
                                        configuration["seat_controller_height"]))
        report["pad_surface_errors"] = [
            pad_surface_errors(scan, specification, PROJECT / "generated" / f"seat_pad_{index}.stl")
            for index, specification in enumerate(configuration["pads"])
        ]
        for errors in report["pad_surface_errors"]:
            assert errors["maximum_above_scan_mm"] < 0.25, errors
            assert errors["maximum_below_scan_mm"] < 0.25, errors

    (PROJECT / "analysis" / "revision_validation.json").write_text(json.dumps(report, indent=2), encoding="ascii")
    print(json.dumps(report, indent=2), flush=True)
    return report


if __name__ == "__main__":
    validate_revision()