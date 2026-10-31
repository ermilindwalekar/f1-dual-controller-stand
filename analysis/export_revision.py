import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import trimesh

from analysis.cradle_fit import PROJECT


EXPORTS = [
    ("body", "f1_dual_controller_stand_body.stl", 1),
    ("pads", "f1_dual_controller_stand_tpu_pads.stl", 6),
    ("cradle_test", "controller_cradle_fit_test.stl", 1),
    ("inserts", "f1_dual_controller_stand_red_inserts.stl", 10),
    ("inserts_base", "f1_dual_controller_stand_red_base_inserts.stl", 2),
    ("inserts_spine", "f1_dual_controller_stand_red_spine_inserts.stl", 2),
    ("inserts_cradles", "f1_dual_controller_stand_red_cradle_inserts.stl", 6),
]


def export_revision(openscad):
    source = PROJECT / "f1_dual_controller_stand.scad"
    baseline = PROJECT / "analysis" / "baseline_body.stl"
    current_body = PROJECT / "f1_dual_controller_stand_body.stl"
    if current_body.exists() and not baseline.exists():
        shutil.copy2(current_body, baseline)
    results = []
    for mode, filename, expected_components in EXPORTS:
        output = PROJECT / filename
        result = subprocess.run(
            [str(openscad), "-o", str(output), "-D", f'render_mode="{mode}"', str(source)],
            capture_output=True, text=True, timeout=180, cwd=PROJECT,
        )
        if result.returncode or "ERROR:" in result.stderr:
            raise RuntimeError(result.stderr)
        mesh = trimesh.load_mesh(output)
        components = mesh.split(only_watertight=False)
        assert mesh.is_watertight and mesh.is_winding_consistent, filename
        assert len(components) == expected_components, (filename, len(components))
        assert all(abs(component.bounds[0, 2]) < 0.001 for component in components), filename
        record = {
            "file": filename,
            "mode": mode,
            "triangles": len(mesh.faces),
            "components": len(components),
            "bounds_mm": mesh.bounds.tolist(),
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        }
        results.append(record)
        print(f"{filename}: {len(components)} component(s), watertight, all on Z=0", flush=True)
    hard_output = PROJECT / "analysis" / "revised_hard_assembly.stl"
    result = subprocess.run(
        [str(openscad), "-o", str(hard_output), "-D", 'render_mode="hard_assembly"', str(source)],
        capture_output=True, text=True, timeout=180, cwd=PROJECT,
    )
    if result.returncode or "ERROR:" in result.stderr:
        raise RuntimeError(result.stderr)
    manifest = {
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "hard_assembly_sha256": hashlib.sha256(hard_output.read_bytes()).hexdigest(),
        "exports": results,
    }
    (PROJECT / "analysis" / "export_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="ascii")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--openscad", type=Path, default=PROJECT.parent / ".tools" / "openscad-2021.01" / "openscad.com")
    arguments = parser.parse_args()
    export_revision(arguments.openscad)