import json
from pathlib import Path

import fcl
import numpy as np
import trimesh


PROJECT = Path(__file__).resolve().parents[1]
SCAN_PATH = PROJECT / "references" / "dualsense-scan" / "Controller_HQ2.3mf"
BODY_PATH = PROJECT / "f1_dual_controller_stand_body.stl"


def collision_object(mesh):
    model = fcl.BVHModel()
    model.beginModel(len(mesh.faces), len(mesh.vertices))
    model.addSubModel(np.asarray(mesh.vertices), np.asarray(mesh.faces))
    model.endModel()
    return fcl.CollisionObject(model)


def load_geometry(face_count=20000):
    body = trimesh.load_mesh(BODY_PATH)
    cradle = body.slice_plane([0, 0, 145], [0, 0, 1], cap=False)
    cradle.apply_translation([0, 0, -162])
    scan = trimesh.load_mesh(SCAN_PATH)
    if face_count is not None:
        scan = scan.simplify_quadric_decimation(face_count=face_count)
    return body, cradle, scan


def pose_matrix(pitch_degrees, fore_aft, height, lateral=0):
    transform = trimesh.transformations.rotation_matrix(
        np.deg2rad(-pitch_degrees), [1, 0, 0]
    )
    transform[:3, 3] = [lateral, fore_aft, height]
    return transform


def set_pose(collision_mesh, transform):
    collision_mesh.setTransform(fcl.Transform(transform[:3, :3], transform[:3, 3]))


def contact_region(point):
    lateral, fore_aft, height = point
    if abs(lateral) >= 44 and -42 <= fore_aft <= -28:
        return "decorative horn (not a support)"
    if fore_aft >= -4.1:
        return "rear shell or backbone"
    if 17 <= abs(lateral) <= 27 and fore_aft >= -13 and height >= 12:
        return "inner guide"
    if 27 <= abs(lateral) <= 39 and height >= 10:
        return "side cheek"
    if fore_aft <= -46:
        return "front lip"
    return "floor or root"


def drop_to_contact(cradle, scan, pitch_degrees, fore_aft, lateral=0):
    cradle_object = collision_object(cradle)
    scan_object = collision_object(scan)
    rotation = pose_matrix(pitch_degrees, 0, 0)[:3, :3]
    lowest = (scan.vertices @ rotation.T)[:, 2].min()
    high = float(cradle.bounds[1, 2] - lowest + 3)
    request = fcl.CollisionRequest()

    def collides(height):
        set_pose(scan_object, pose_matrix(pitch_degrees, fore_aft, height, lateral))
        return bool(fcl.collide(cradle_object, scan_object, request, fcl.CollisionResult()))

    assert not collides(high)
    low = high - 1
    while low > -80 and not collides(low):
        high, low = low, low - 1
    if low <= -80:
        return None
    for iteration in range(14):
        middle = (low + high) / 2
        if collides(middle):
            low = middle
        else:
            high = middle

    set_pose(scan_object, pose_matrix(pitch_degrees, fore_aft, low - 0.02, lateral))
    result = fcl.CollisionResult()
    fcl.collide(
        cradle_object,
        scan_object,
        fcl.CollisionRequest(num_max_contacts=64, enable_contact=True),
        result,
    )
    contacts = np.array([contact.pos for contact in result.contacts])
    regions = sorted({contact_region(point) for point in contacts})
    return {
        "pitch_degrees": pitch_degrees,
        "fore_aft_mm": fore_aft,
        "lateral_mm": lateral,
        "height_above_cradle_datum_mm": high,
        "contact_regions": regions,
        "contact_bounds_mm": [contacts.min(axis=0).tolist(), contacts.max(axis=0).tolist()],
        "contacts_mm": contacts.tolist(),
        "transform": pose_matrix(pitch_degrees, fore_aft, high, lateral).tolist(),
    }


def sweep():
    body, cradle, scan = load_geometry()
    results = []
    for pitch in [0, 15, 30, 45, 60, 75, 90]:
        for fore_aft in [-50, -40, -30, -20, -10]:
            result = drop_to_contact(cradle, scan, pitch, fore_aft)
            if result is not None:
                results.append(result)
                print(
                    pitch,
                    fore_aft,
                    round(result["height_above_cradle_datum_mm"], 3),
                    result["contact_regions"],
                    np.round(result["contact_bounds_mm"], 2).tolist(),
                    flush=True,
                )
    output = PROJECT / "analysis" / "contact_sweep.json"
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


def closest_surfaces(first_mesh, second_mesh, transform=None):
    first_object = collision_object(first_mesh)
    second_object = collision_object(second_mesh)
    if transform is not None:
        set_pose(second_object, transform)
    result = fcl.DistanceResult()
    distance = fcl.distance(
        first_object,
        second_object,
        fcl.DistanceRequest(enable_nearest_points=True),
        result,
    )
    return {
        "distance_mm": float(distance),
        "nearest_points_mm": np.asarray(result.nearest_points).tolist(),
    }


def render_pose(cradle, scan, result, image_path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    display_scan = scan.simplify_quadric_decimation(face_count=18000)
    display_scan.apply_transform(np.asarray(result["transform"]))
    bounds = np.array([cradle.bounds, display_scan.bounds])
    minimum = bounds[:, 0].min(axis=0)
    maximum = bounds[:, 1].max(axis=0)
    center = (minimum + maximum) / 2
    radius = max(maximum - minimum) * 0.53
    figure = plt.figure(figsize=(16, 6))
    for panel_index, (elevation, azimuth, title) in enumerate(
        [(18, -65, "Oblique"), (0, -90, "Front"), (0, 0, "Side")], start=1
    ):
        axis = figure.add_subplot(1, 3, panel_index, projection="3d")
        for mesh, color in [(cradle, "#52585d"), (display_scan, "#69aeb9")]:
            axis.add_collection3d(
                Poly3DCollection(mesh.triangles, facecolors=color, linewidths=0, shade=True)
            )
        axis.set_xlim(center[0] - radius, center[0] + radius)
        axis.set_ylim(center[1] - radius, center[1] + radius)
        axis.set_zlim(center[2] - radius, center[2] + radius)
        axis.set_box_aspect((1, 1, 1))
        axis.set_proj_type("ortho")
        axis.view_init(elev=elevation, azim=azimuth)
        axis.set_axis_off()
        axis.set_title(title)
    figure.suptitle(
        f"{result.get('test_label', 'First-contact test')}: {result['pitch_degrees']} deg recline, "
        f"Y = {result['fore_aft_mm']} mm (not an equilibrium simulation)"
    )
    figure.tight_layout()
    figure.savefig(image_path, dpi=150)
    plt.close(figure)


def verify_full_resolution():
    body, cradle, scan = load_geometry(face_count=None)
    central_faces = np.flatnonzero(np.max(np.abs(cradle.triangles[:, :, 0]), axis=1) <= 40)
    central_cradle = cradle.submesh([central_faces], append=True)
    verified = []
    for pitch, fore_aft in [(0, -30), (60, -30), (0, -10), (90, -30)]:
        result = drop_to_contact(cradle, scan, pitch, fore_aft)
        transform = np.asarray(result["transform"])
        result["central_cradle_clearance"] = closest_surfaces(central_cradle, scan, transform)
        lower = scan.copy()
        lower.apply_transform(transform)
        upper_transform = transform.copy()
        upper_transform[2, 3] += 90
        result["controller_pair_clearance"] = closest_surfaces(lower, scan, upper_transform)
        verified.append(result)
        print(json.dumps({key: value for key, value in result.items() if key != "contacts_mm"}), flush=True)
        if pitch in [0, 60] and fore_aft == -30:
            render_pose(cradle, scan, result, PROJECT / "analysis" / f"fit_pose_{pitch}deg.png")
    output = PROJECT / "analysis" / "full_resolution_checks.json"
    output.write_text(json.dumps(verified, indent=2), encoding="utf-8")
    return verified


def collision_check(first_mesh, second_mesh, transform=None):
    first_object = collision_object(first_mesh)
    second_object = collision_object(second_mesh)
    if transform is not None:
        set_pose(second_object, transform)
    result = fcl.CollisionResult()
    count = fcl.collide(
        first_object,
        second_object,
        fcl.CollisionRequest(num_max_contacts=64, enable_contact=True),
        result,
    )
    return {
        "surface_collision": bool(count),
        "contact_points_mm": [np.asarray(contact.pos).tolist() for contact in result.contacts],
    }


def central_bucket(cradle):
    bucket = cradle
    for origin, normal in [
        ([-28, 0, 0], [1, 0, 0]),
        ([28, 0, 0], [-1, 0, 0]),
        ([0, -46, 0], [0, 1, 0]),
        ([0, 2, 0], [0, -1, 0]),
        ([0, 0, 30], [0, 0, -1]),
    ]:
        bucket = bucket.slice_plane(origin, normal, cap=False)
    return bucket


def verify_central_seating(poses=None, face_count=20000, render=False):
    if poses is None:
        poses = [(0, -30), (0, -10), (15, -20)]
    body, cradle, scan = load_geometry(face_count=face_count)
    bucket = central_bucket(cradle)
    results = []
    for pitch, fore_aft in poses:
        result = drop_to_contact(bucket, scan, pitch, fore_aft)
        if result is None:
            continue
        result["test_label"] = "Central underside seating target"
        result["reference_triangles"] = len(scan.faces)
        transform = np.asarray(result["transform"])
        lifted_transform = transform.copy()
        lifted_transform[2, 3] += 0.1
        interference = collision_check(cradle, scan, lifted_transform)
        interference["sampled_regions"] = sorted(
            {contact_region(point) for point in interference["contact_points_mm"]}
        )
        result["whole_cradle_at_target_plus_0_1mm"] = interference
        result["grips_allowed_outside_bucket"] = True
        results.append(result)
        print(
            json.dumps(
                {
                    "pitch_degrees": pitch,
                    "fore_aft_mm": fore_aft,
                    "center_seating_height_mm": result["height_above_cradle_datum_mm"],
                    "center_contact_regions": result["contact_regions"],
                    "center_contact_bounds_mm": result["contact_bounds_mm"],
                    "interference_with_whole_cradle": interference["surface_collision"],
                    "sampled_interference_regions": interference["sampled_regions"],
                }
            ),
            flush=True,
        )
        if render:
            render_pose(
                cradle,
                scan,
                result,
                PROJECT / "analysis" / f"central_seat_{pitch}deg_y{fore_aft}.png",
            )
    suffix = "full" if face_count is None else "preliminary"
    (PROJECT / "analysis" / f"central_seating_{suffix}.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    return results


def verify_forward_pose():
    body, cradle, scan = load_geometry(face_count=None)
    central_faces = np.flatnonzero(np.max(np.abs(cradle.triangles[:, :, 0]), axis=1) <= 40)
    central_cradle = cradle.submesh([central_faces], append=True)
    upper_tier = body.slice_plane([0, 0, 155], [0, 0, 1], cap=False)
    result = drop_to_contact(cradle, scan, 75, -50)
    transform = np.asarray(result["transform"])
    result["central_cradle_clearance"] = closest_surfaces(central_cradle, scan, transform)
    lower_transform = transform.copy()
    lower_transform[2, 3] += 72.1
    result["lower_pose_with_0_1mm_lift"] = collision_check(body, scan, lower_transform)
    result["upper_tier_clearance_with_0_1mm_lift"] = closest_surfaces(upper_tier, scan, lower_transform)
    positioned_scan = scan.copy()
    positioned_scan.apply_transform(transform)
    upper_transform = transform.copy()
    upper_transform[2, 3] += 90
    result["controller_pair_clearance"] = closest_surfaces(positioned_scan, scan, upper_transform)
    result["controller_bounds_relative_to_cradle_mm"] = positioned_scan.bounds.tolist()
    render_pose(cradle, scan, result, PROJECT / "analysis" / "fit_pose_forward_75deg.png")
    (PROJECT / "analysis" / "forward_pose_check.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in result.items() if key != "contacts_mm"}), flush=True)
    return result


if __name__ == "__main__":
    sweep()