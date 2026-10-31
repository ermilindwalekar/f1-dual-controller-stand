# DualSense Central-Cradle Fit Assessment

Date: 2026-10-31

## Revised Design Status

The stand and released STLs have now been revised. The geometric interference
and noncoplanar-foot issues found in the initial assessment are corrected for
the reference controller. Physical no-rocking behaviour still requires a printed
prototype with the intended TPU contact pads and the actual controller.

The revision uses a 30-degree recline, floor datums of 52 and 162 mm, a 110 mm
tier pitch, a scan-contoured central saddle, three TPU pads per controller,
lower cheeks and rear-mounted decorative horns. The body stays 210 mm tall.
The controller's grips remain outside the cradle; the horns are not supports.

Full-resolution checks of the exported rigid body plus fitted red accents found:

| Check | Result |
| --- | --- |
| Seated controller to rigid stand | Minimum 0.614 mm clearance |
| Controller to controller | Minimum 15.239 mm clearance |
| Exposed rear horn surfaces to scan | Minimum 9.114 mm clearance |
| Removal with the other controller present | Clear with a conservative 0.4 mm clearance bound |
| Pad top versus scanned underside | Maximum sampled vertical mismatch 0.147 mm |
| Both front foot soles | Z = 0, matching the central contacts |
| Exported body | One watertight component, 13,930 triangles |

The checked path is a 5 mm vertical lift, a 70 mm forward pull, then a 30 mm
lift, at the seating angle. Python-FCL uses the complete 1,980,421-triangle scan.
Distance-based steps are smaller than the available gap minus 0.4 mm, bounding
rigid-surface clearance between samples for this translation-only path. TPU pads
are excluded from rigid collision obstacles; their intentional shell contact is
checked separately by underside ray sampling on a 0.25 mm grid. This does not
simulate pad compression or friction.

The pads have flat bases and shaped tops, with 0.10 mm per-side friction
interference in the pockets. They must be flexible and fully seated. Their
separated contact patches are intended to prevent rigid central-point pivoting,
but no gravity-settling or contact-force simulation has been performed.

Files: [revision_validation.json](revision_validation.json),
[export_manifest.json](export_manifest.json),
[loaded preview](../f1_dual_controller_stand_loaded.png), and
[cradle close-up](../f1_dual_controller_stand_cradle_detail.png).

Print the [cradle test](../controller_cradle_fit_test.stl) and three of the
[TPU pads](../f1_dual_controller_stand_tpu_pads.stl) first. Secure the test cradle
at least 40 mm above the desk so its overhanging grips do not touch the desk.
Check all three contacts, rocking, pad retention, full stick/trigger travel,
and removal. On the completed stand, check loaded desk stability and cable pull.
The full static scan does not cover stick deflection, grip covers, DualSense
Edge, real mass distribution, printer tolerances, material strength or creep.

## Reproducing the Revision

From the project directory with the configured analysis environment:

```powershell
& ..\.venv-cad-audit\Scripts\python.exe -m analysis.build_seat
& ..\.venv-cad-audit\Scripts\python.exe -m analysis.export_revision
& ..\.venv-cad-audit\Scripts\python.exe -m analysis.validate_revision
```

The export script preserves the previous released body as
[baseline_body.stl](baseline_body.stl). Current reports include input hashes.
The remaining sections below record the original diagnosis, not the current fit.

## Initial Diagnosis (Before Revision)

The original stand had confirmed interference at a representative central-bottom
seating target. Its horns and cheeks caught the controller before it reached the
intended seat. It was not a validated, non-rocking design.

## Intended Seating

- Only the controller's central lower section rests inside the bucket, similar
  to the original PS5 charging dock.
- Both grip handles overhang outside the bucket and may extend below its floor.
- The horns are decorative and must clear the controller, including its sticks.
- Stable support must come from the central seat and appropriate locating
  surfaces, not from a horn or an accidental high contact.

The original source called the horns "grip-support wings". That description
conflicted with the clarified intent and has been corrected.

## Reference

[PlayStation DualSense controller 3D scan](https://grabcad.com/library/playstation-dualsense-controller-3d-scan-1)
by Benjamin Gonzalez, uploaded 2025-12-29. The author describes a Creality
Raptor X scan with correct units, with reduced accuracy behind the joysticks.

The unscaled scan is in millimetres and measures approximately
159.380 x 60.963 x 108.704 mm in its native axes. It has 1,980,421 triangles,
consistent winding, and an open surface. It is not a manufacturer-certified
tolerance model, and its volume is not a valid estimate of the real mass
distribution. The earlier download from `ps5-controller-13` contains only the
PS-logo button and was rejected as a controller reference.

## Baseline Method and Results

The initial audit used the original body STL and Python-FCL triangle-surface collision
checks. The upper cradle is translated to a local floor datum of Z = 0.
A diagnostic central region, X = -28 to +28 mm, Y = -46 to +2 mm, Z <= 30 mm,
is used to establish a central seating target without catching the overhanging
grips on the horns. This clipping changes only the test fixture, not the stand.
The candidate is then checked against the complete, unclipped cradle.

At a representative 15-degree rearward recline:

- Native scan transform: rotate -15 degrees about X, then translate by
  [0, -20, 29.7386814] mm relative to the cradle datum.
- The central underside reaches the recessed floor at Z = 7.4 mm, with the
  grips outside. This is a target position, not a feasible final assembly.
- The original full-resolution scan intersects the decorative horns, even
  after lifting it 0.1 mm to avoid counting the intended floor contact.
- Two copies in this pose, separated vertically by the existing 90 mm tier
  pitch, intersect each other. This finding is pose-specific; it does not
  establish a required new pitch for a different seating angle.
- The lower controller does not intersect the upper stand region cropped at
  global Z >= 145 mm in this pose. That does not clear the local horn conflict
  or certify an insertion/removal path.

The preliminary 20,000-triangle sweep tested reclines of -15, 0, 15, 30, 45,
and 60 degrees, with native-scan Y translations of -40, -30, -20, -10, and
0 mm. Of these 30 targets, 28 intersect the full cradle. The two clear targets
rest on the rear shell's upper edge instead of seating in the bucket. This is
a finite diagnostic sweep, not proof that no conceivable placement exists.

See [the central-seat overlay](central_seat_15deg_y-20.png),
[full-resolution target data](central_seating_full.json), and
[preliminary sweep data](central_seating_preliminary.json).
The older `contact_sweep.json` and `full_resolution_checks.json` describe
first-contact tests against the entire cradle; horn contact in those files
does not represent acceptable seating.

## Baseline Stability Risks

Collision-free placement would not alone prove resistance to rocking. This
audit has not simulated gravity settling, friction, compliance, print variation,
or the controller's actual centre of gravity. No physical fit test has been
performed. Full stick deflection and grip covers remain unverified. The revision
adds a specific checked removal path, but no physical extraction test. Existing
insert-fit coupons test decorative inserts, not controllers.

Separately, the original stand's front feet had minimum Z = 0.212233 mm while
the central structure reaches Z = 0. Its initial ground-contact hull is at most
44 mm wide, despite the approximately 140 mm outer width. Those feet were not
coplanar in CAD; the revision adds flat front soles at Z = 0.

## Original Recommendations

1. Establish the final central-bottom seating angle and fore/aft position using
   the scan, while leaving both grips outside.
2. Relieve or reposition the horns and conflicting cheeks around that position,
   preserving clearance for the sticks throughout placement and removal.
3. Shape the central seat or use separated compliant contact pads and a backstop
   to prevent pivoting on a small central contact; keep loads on the plastic shell.
4. Recheck both occupied tiers together at the selected angle before changing
   pitch, and make the intended desk-contact feet coplanar.
5. Print a cradle-only prototype and check the actual controller for alternating
   contacts and rocking before printing the complete stand.

Use the revision commands above for the current model. Historical JSON results
are retained as evidence of the original issue, not as verification of revised
source. Any future geometry change requires fresh exports and checks.