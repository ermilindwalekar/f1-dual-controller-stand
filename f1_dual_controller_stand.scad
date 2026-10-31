/*
  F1-INSPIRED DUAL PS5 CONTROLLER STAND — CLEAN-SHEET MODEL

  Visual basis: front, top, angled, loaded, cradle-detail, base-detail, and
  fitted-accent views in the supplied showcase. The showcase side view is
  intentionally ignored because the user identified it as inaccurate.

  Units: mm. OpenSCAD 2021.01+.
*/

// ---------- OUTPUT ----------
// "assembled", "body", "inserts", "inserts_base", "inserts_spine",
// "inserts_cradles", "exploded", "cradle_detail", "coupon_body",
// "coupon_insert", "pads", "cradle_test", "loaded"
render_mode = "assembled";
include <generated/seat_config.scad>

// ---------- OVERALL ENVELOPE ----------
overall_height = 210;
target_base_width = 140;
target_base_depth = 130;
base_sole_height = 1.2;
base_sole_rear_y = -52;

// ---------- CONTROLLER / CRADLE PARAMETERS ----------
cradle_pitch = 110;
cradle_levels = [162-cradle_pitch, 162];
tray_width = 72;
tray_depth = 56;
tray_thickness = 9;
tray_front_y = -50;
tray_rear_y = tray_front_y + tray_depth;
tray_pocket_depth = 1.6;
cradle_tip_span = 124;
cradle_tip_rise = 42;
side_cheek_height = 4;
controller_fit_allowance = 1.0;
show_inner_guides = false;
seat_pad_clearance = -0.10;

// Decorative horns stay behind the controller; only the central saddle supports it.
cradle_arm_front_y = 17;
cradle_arm_depth = 12;
cradle_arm_root_x = 34;
cradle_arm_stick_clear_x = 47;

// ---------- BACKBONE / FACEPLATE ----------
faceplate_text = "R1";           // generic racing plate, not team branding
show_faceplate_text = true;

// ---------- RED INSERT FIT ----------
insert_clearance = 0.22;         // per mating side; calibrate with coupon
insert_depth = 2.5;
insert_proud = 0.18;
detent_interference = 0.10;
detent_length = 4.0;

base_insert_open = 5.0;
base_insert_inner = 7.4;
spine_insert_open = 3.8;
spine_insert_inner = 5.8;
cradle_insert_open = 4.5;
cradle_insert_inner = 6.8;

$fn = $preview ? 28 : 56;

// ---------- VECTOR HELPERS ----------
function vadd(a,b) = [a[0]+b[0],a[1]+b[1],a[2]+b[2]];
function vsub(a,b) = [a[0]-b[0],a[1]-b[1],a[2]-b[2]];
function vmul(a,s) = [a[0]*s,a[1]*s,a[2]*s];
function vunit(a) = let(m=norm(a)) [a[0]/m,a[1]/m,a[2]/m];
function lerp(a,b,t) = vadd(a,vmul(vsub(b,a),t));

// Local X follows a feature, local Y is stripe width, local Z points out.
function feature_frame(p1,p2,outward_hint) =
    let(u=vunit(vsub(p2,p1)),
        w=vunit(cross(outward_hint,u)),
        n=vunit(cross(u,w)))
    [[u[0],w[0],n[0],p1[0]],
     [u[1],w[1],n[1],p1[1]],
     [u[2],w[2],n[2],p1[2]],
     [0,0,0,1]];

// ---------- SLIDING DOVETAIL + INTEGRAL DETENT ----------
module dovetail_channel_raw(length,open_w,inner_w,depth=insert_depth) {
    union() {
        rotate([0,90,0])
            linear_extrude(height=length,convexity=8)
                polygon([
                    [-0.28,-open_w/2],[-0.28,open_w/2],
                    [depth+0.10,inner_w/2],[depth+0.10,-inner_w/2]
                ]);

        // Long relief near the accessible end receives the integral bump.
        pocket_x=max(0,length-11);
        translate([pocket_x,inner_w/2-0.15,-depth+0.25])
            cube([9,insert_clearance+detent_interference+0.45,0.9]);
    }
}

module dovetail_insert_raw(length,open_w,inner_w,depth=insert_depth) {
    visible_w=open_w-2*insert_clearance;
    buried_w=inner_w-2*insert_clearance;
    union() {
        rotate([0,90,0])
            linear_extrude(height=length,convexity=8)
                polygon([
                    [-insert_proud,-visible_w/2],
                    [-insert_proud, visible_w/2],
                    [depth-insert_clearance, buried_w/2],
                    [depth-insert_clearance,-buried_w/2]
                ]);

        // Printed wedge bump: ramps over the channel wall, then sits in the
        // relief pocket. The long strip supplies the small elastic deflection.
        bump_x=max(0,length-7);
        bump_y=buried_w/2-0.12;
        bump_z=-depth+insert_clearance+0.22;
        hull() {
            translate([bump_x,bump_y,bump_z]) cube([0.7,0.3,0.55]);
            translate([bump_x+detent_length,bump_y,bump_z])
                cube([0.7,insert_clearance+detent_interference+0.24,0.55]);
        }
    }
}

module feature_channel(p1,p2,outward,open_w,inner_w) {
    multmatrix(feature_frame(p1,p2,outward))
        dovetail_channel_raw(norm(vsub(p2,p1)),open_w,inner_w);
}

module feature_insert(p1,p2,outward,open_w,inner_w) {
    multmatrix(feature_frame(p1,p2,outward))
        dovetail_insert_raw(norm(vsub(p2,p1)),open_w,inner_w);
}

// ---------- FACETED STRUCTURAL HELPERS ----------
module aero_beam(p1,p2,width1,width2,height1,height2) {
    L=norm(vsub(p2,p1));
    slice=2;
    multmatrix(feature_frame(p1,p2,[0,0,1]))
        hull() {
            translate([0,-width1/2,-height1]) cube([slice,width1,height1]);
            translate([L-slice,-width2/2,-height2]) cube([slice,width2,height2]);
        }
}

module prism_x(width,yz_points) {
    translate([-width/2,0,0])
        rotate([0,90,0])
            linear_extrude(height=width,convexity=8)
                polygon([for(p=yz_points)[-p[1],p[0]]]);
}

// ---------- TWO-LEG V BASE ----------
function leg_root(side)=[side*11,46,36];
function leg_tip(side)=[side*58.5,-66.5,9];
function leg_u(side)=vunit(vsub(leg_tip(side),leg_root(side)));
function leg_w(side)=vunit(cross([0,0,1],leg_u(side)));
function base_accent_start(side)=
    vadd(lerp(leg_root(side),leg_tip(side),0.09),
         vmul(leg_w(side),side*6.0));
function base_accent_end(side)=
    vadd(lerp(leg_root(side),leg_tip(side),1.01),
         vmul(leg_w(side),side*5.2));

module base() {
    for(side=[-1,1]) {
        aero_beam(leg_root(side),leg_tip(side),30,25,36,9);
        linear_extrude(height=base_sole_height)
            projection(cut=false)
                intersection() {
                    aero_beam(leg_root(side),leg_tip(side),30,25,36,9);
                    translate([-target_base_width,-target_base_depth,-1])
                        cube([2*target_base_width,
                              target_base_depth+base_sole_rear_y,14]);
                }

        // Secondary upper chine creates the multi-faceted open-wheel look.
        w=leg_w(side);
        aero_beam(vadd(lerp(leg_root(side),leg_tip(side),0.05),
                       vmul(w,-side*3)),
                  vadd(lerp(leg_root(side),leg_tip(side),0.76),
                       vmul(w,-side*2)),
                  12,9,7,3);
    }

    // Short central keel visible in front/angled views; not a third long foot.
    prism_x(16,[[-34,0],[-28,16],[28,41],[43,23],[-2,5]]);
}

module base_channels() {
    for(side=[-1,1])
        feature_channel(base_accent_start(side),base_accent_end(side),
                        [0,0,1],base_insert_open,base_insert_inner);
}

module base_inserts_assembled() {
    for(side=[-1,1])
        feature_insert(lerp(base_accent_start(side),base_accent_end(side),0.025),
                       lerp(base_accent_start(side),base_accent_end(side),0.985),
                       [0,0,1],base_insert_open,base_insert_inner);
}

// ---------- LOFTED BACKBONE ----------
backbone_sections=[
    [0,  44,-3.0,43],
    [42, 39, 1.0,39],
    [70, 35, 4.8,35],
    [122,32, 6.2,34],
    [160,34, 7.4,34],
    [210,30, 9.3,35]
];

module backbone() {
    n=len(backbone_sections);
    pts=[for(s=backbone_sections,k=[0:3])
        k==0?[-s[1]/2,s[2],s[0]]:
        k==1?[ s[1]/2,s[2],s[0]]:
        k==2?[ s[1]/2,s[3],s[0]]:
             [-s[1]/2,s[3],s[0]]];
    tri_a=[for(i=[0:n-2],j=[0:3])
        [i*4+j,i*4+(j+1)%4,(i+1)*4+(j+1)%4]];
    tri_b=[for(i=[0:n-2],j=[0:3])
        [i*4+j,(i+1)*4+(j+1)%4,(i+1)*4+j]];
    top=(n-1)*4;
    faces=concat([[3,2,1],[3,1,0]],tri_a,tri_b,
                 [[top,top+1,top+2],[top,top+2,top+3]]);
    polyhedron(points=pts,faces=faces,convexity=12);

    // Subtle central crease running into the base flare.
    hull() {
        translate([-3,-1.5,20]) cube([6,3,10]);
        translate([-2.2,7.2,198]) cube([4.4,2.2,7]);
    }
}

function spine_accent_start(side)=[side*11.5,0.8,25];
function spine_accent_end(side)=[side*11.5,9.5,210.5];

module spine_channels() {
    for(side=[-1,1])
        feature_channel(spine_accent_start(side),spine_accent_end(side),
                        [0,-1,0],spine_insert_open,spine_insert_inner);
}

module spine_inserts_assembled() {
    for(side=[-1,1])
        feature_insert(lerp(spine_accent_start(side),spine_accent_end(side),0.02),
                       lerp(spine_accent_start(side),spine_accent_end(side),0.985),
                       [0,-1,0],spine_insert_open,spine_insert_inner);
}

// ---------- FACEPLATE ----------
module faceplate() {
    plate_y=5.8;
    plate_z=119;
    translate([0,plate_y,plate_z]) rotate([90,0,0])
        linear_extrude(height=1.0)
            polygon([[-13,0],[13,0],[11,19],[-11,19]]);

    if(show_faceplate_text)
        translate([0,plate_y-1.05,plate_z+9.5]) rotate([90,0,0])
            linear_extrude(height=0.55)
                text(faceplate_text,size=7,halign="center",valign="center",
                     font="DejaVu Sans:style=Bold Italic");
}

// ---------- DETAILED HORIZONTAL BUCKET CRADLE ----------
module cradle_floor(z) {
    half=(tray_width+controller_fit_allowance)/2;
    difference() {
        union() {
            translate([0,0,z])
                linear_extrude(height=tray_thickness,scale=[0.95,0.97])
                    polygon([[-half,tray_front_y],[half,tray_front_y],
                             [half-1,tray_rear_y],[-half+1,tray_rear_y]]);

            // Front lip: deep central material plus a raised retaining edge.
            translate([0,tray_front_y+3,0]) rotate([90,0,0])
                linear_extrude(height=5)
                    polygon([[-half+1,z+4],[half-1,z+4],
                             [half-4,z+14],[-half+4,z+14]]);
        }

        // Drafted, open recess matching the angular controller-underbody seat.
        translate([0,0,z+tray_thickness-tray_pocket_depth])
            linear_extrude(height=tray_pocket_depth+0.45,
                           scale=[1.10,1.08],convexity=8)
                polygon([[-25,-39],[25,-39],[28,-31],[28,-13],
                         [21,-6],[-21,-6],[-28,-13],[-28,-31]]);
    }
}

module cradle_root(z) {
    // Horizontal collar and tapered rear shell visibly merge the bucket into
    // the central backbone without a long slanted underside support.
    translate([0,4,z-2])
        linear_extrude(height=13,scale=[0.94,0.96])
            polygon([[-31,-16],[31,-16],[28,15],[-28,15]]);

    translate([0,tray_rear_y+5,0]) rotate([90,0,0])
        linear_extrude(height=15,convexity=8)
            polygon([[-35,z+3],[35,z+3],[32,z+20],
                     [24,z+29],[-24,z+29],[-32,z+20]]);

    for(side=[-1,1])
        hull() {
            translate([side*27,tray_rear_y-2,z+10]) cube([8,4,13],center=true);
            translate([side*32,tray_rear_y-12,z+11]) cube([10,4,15],center=true);
        }
}

module cradle_side(side,z) {
    half=(tray_width+controller_fit_allowance)/2;
    tip=cradle_tip_span/2;

    profile=[
        [cradle_arm_root_x,z+5],[cradle_arm_root_x+9,z+5],
        [tip,z+cradle_tip_rise-10],[tip,z+cradle_tip_rise],
        [tip-8,z+cradle_tip_rise+1],
        [cradle_arm_stick_clear_x,z+16],[cradle_arm_root_x,z+12]
    ];
    translate([0,cradle_arm_front_y+cradle_arm_depth,0]) rotate([90,0,0])
        linear_extrude(height=cradle_arm_depth,convexity=8)
            polygon([for(p=profile)[side*p[0],p[1]]]);

    hull() {
        translate([side*29,6,z+6]) cube([10,12,8],center=true);
        translate([side*38,cradle_arm_front_y+6,z+6])
            cube([10,12,8],center=true);
    }

    cheek_x=side*(half-3.5);
    hull() {
        translate([cheek_x,tray_front_y+14,z+5])
            cube([10,4,side_cheek_height],center=true);
        translate([cheek_x,tray_rear_y-10,z+7])
            cube([10,4,side_cheek_height+4],center=true);
    }
}

module cradle_guides(z) {
    if(show_inner_guides)
        for(side=[-1,1])
            hull() {
                translate([side*21,tray_rear_y-11,z+9]) cube([8,8,4],center=true);
                translate([side*23,tray_rear_y-15,z+15]) cube([6,6,5],center=true);
            }
}

module seat_pad_pockets(z) {
    for(index=[0:len(seat_pad_centers)-1]) {
        center=seat_pad_centers[index];
        size=seat_pad_sizes[index];
        translate([center[0]-size[0]/2-seat_pad_clearance,
                   center[1]-size[1]/2-seat_pad_clearance,
                   z+seat_pad_bottoms[index]])
            cube([size[0]+2*seat_pad_clearance,
                  size[1]+2*seat_pad_clearance,50]);
    }
}

module seat_pads_assembled(z) {
    for(index=[0:len(seat_pad_centers)-1])
        translate([0,0,z])
            import(str("generated/seat_pad_",index,".stl"),convexity=8);
}

module seat_pads_layout() {
    for(tier=[0:len(cradle_levels)-1],index=[0:len(seat_pad_centers)-1]) {
        center=seat_pad_centers[index];
        translate([(index-1)*24-center[0],tier*24-center[1],
                   -seat_pad_bottoms[index]])
            import(str("generated/seat_pad_",index,".stl"),convexity=8);
    }
}

module cradle(z) {
    difference() {
        union() {
            cradle_floor(z);
            cradle_root(z);
            cradle_guides(z);
            for(side=[-1,1]) cradle_side(side,z);
            translate([0,0,z]) import("generated/central_seat.stl",convexity=10);
        }
        seat_pad_pockets(z);
        translate([-9,-47,z+tray_thickness]) cube([18,16,40]);
    }
}

function cradle_side_start(side,z)=
    [side*(cradle_arm_root_x+5),cradle_arm_front_y,z+8];
function cradle_side_end(side,z)=
    [side*(cradle_tip_span/2+0.4),cradle_arm_front_y,
     z+cradle_tip_rise+0.6];
function cradle_lip_start(z)=
    [-((tray_width+controller_fit_allowance)/2-3),tray_front_y-2,z+9];
function cradle_lip_end(z)=
    [ ((tray_width+controller_fit_allowance)/2-1),tray_front_y-2,z+9];

module cradle_channels(z) {
    for(side=[-1,1])
        feature_channel(cradle_side_start(side,z),cradle_side_end(side,z),
                        [0,-1,0],cradle_insert_open,cradle_insert_inner);
    feature_channel(cradle_lip_start(z),cradle_lip_end(z),
                    [0,-1,0],cradle_insert_open,cradle_insert_inner);
}

module cradle_inserts_assembled(z) {
    for(side=[-1,1])
        feature_insert(lerp(cradle_side_start(side,z),cradle_side_end(side,z),0.025),
                       lerp(cradle_side_start(side,z),cradle_side_end(side,z),0.98),
                       [0,-1,0],cradle_insert_open,cradle_insert_inner);
    feature_insert(lerp(cradle_lip_start(z),cradle_lip_end(z),0.02),
                   lerp(cradle_lip_start(z),cradle_lip_end(z),0.98),
                   [0,-1,0],cradle_insert_open,cradle_insert_inner);
}

// ---------- COMPLETE BLACK BODY ----------
module main_body() {
    difference() {
        union() {
            base();
            backbone();
            faceplate();
            for(z=cradle_levels) cradle(z);
        }
        base_channels();
        spine_channels();
        for(z=cradle_levels) cradle_channels(z);
    }
}

module all_inserts_assembled() {
    base_inserts_assembled();
    spine_inserts_assembled();
    for(z=cradle_levels) cradle_inserts_assembled(z);
}

// ---------- FLAT PRINT LAYOUTS ----------
module raw_insert_at(x,y,length,open_w,inner_w,rotation=90) {
    translate([x,y,insert_depth-insert_clearance])
        rotate([0,0,rotation])
            dovetail_insert_raw(length,open_w,inner_w);
}

module base_inserts_layout() {
    L=norm(vsub(base_accent_end(1),base_accent_start(1)))*0.96;
    raw_insert_at(-8,-L/2,L,base_insert_open,base_insert_inner);
    raw_insert_at( 8,-L/2,L,base_insert_open,base_insert_inner);
}

module spine_inserts_layout() {
    L=norm(vsub(spine_accent_end(1),spine_accent_start(1)))*0.965;
    raw_insert_at(-8,-L/2,L,spine_insert_open,spine_insert_inner);
    raw_insert_at( 8,-L/2,L,spine_insert_open,spine_insert_inner);
}

module cradle_inserts_layout() {
    sideL=norm(vsub(cradle_side_end(1,0),cradle_side_start(1,0)))*0.955;
    lipL=norm(vsub(cradle_lip_end(0),cradle_lip_start(0)))*0.96;
    // Four side arms, two front lips.
    for(i=[0:3]) raw_insert_at(-32+i*14,-sideL/2,sideL,
                               cradle_insert_open,cradle_insert_inner);
    for(i=[0:1]) raw_insert_at(26+i*14,-lipL/2,lipL,
                               cradle_insert_open,cradle_insert_inner);
}

module all_inserts_layout() {
    translate([-48,0,0]) spine_inserts_layout();
    translate([-18,0,0]) base_inserts_layout();
    translate([48,0,0]) cradle_inserts_layout();
}

// ---------- FIT COUPON ----------
module coupon_body() {
    difference() {
        translate([-17,-24,0]) cube([34,48,8]);
        feature_channel([0,-19,8],[0,25,8],[0,0,1],
                        base_insert_open,base_insert_inner);
    }
}

module coupon_insert() {
    raw_insert_at(0,-21,42,base_insert_open,base_insert_inner);
}

// ---------- OUTPUT SELECTOR ----------
if(render_mode=="assembled" || render_mode=="loaded") {
    color([0.025,0.028,0.032]) render(convexity=12) main_body();
    color([0.86,0.01,0.015]) all_inserts_assembled();
    color([0.25,0.27,0.28])
        for(z=cradle_levels) seat_pads_assembled(z);
    if(render_mode=="loaded")
        color([0.75,0.78,0.80])
            for(z=cradle_levels)
                translate([0,seat_controller_y,z+seat_controller_height])
                    rotate([-seat_controller_pitch,0,0])
                        import("generated/controller_preview.stl",convexity=12);
} else if(render_mode=="body") {
    main_body();
} else if(render_mode=="hard_assembly") {
    main_body();
    all_inserts_assembled();
} else if(render_mode=="inserts") {
    all_inserts_layout();
} else if(render_mode=="inserts_base") {
    base_inserts_layout();
} else if(render_mode=="inserts_spine") {
    spine_inserts_layout();
} else if(render_mode=="inserts_cradles") {
    cradle_inserts_layout();
} else if(render_mode=="exploded") {
    color([0.025,0.028,0.032]) render(convexity=12) main_body();
    color([0.86,0.01,0.015]) {
        translate([0,0,10]) base_inserts_assembled();
        translate([0,-10,0]) spine_inserts_assembled();
        for(z=cradle_levels)
            translate([0,-12,0]) cradle_inserts_assembled(z);
    }
    color([0.25,0.27,0.28])
        for(z=cradle_levels) translate([0,0,14]) seat_pads_assembled(z);
} else if(render_mode=="cradle_detail") {
    z=cradle_levels[0];
    translate([0,0,-z]) {
        color([0.12,0.13,0.15]) render(convexity=12)
            difference() { cradle(z); cradle_channels(z); }
        color([0.86,0.01,0.015]) cradle_inserts_assembled(z);
        color([0.25,0.27,0.28]) seat_pads_assembled(z);
    }
} else if(render_mode=="pads") {
    seat_pads_layout();
} else if(render_mode=="cradle_test") {
    translate([0,0,2])
        difference() { cradle(0); cradle_channels(0); }
} else if(render_mode=="coupon_body") {
    coupon_body();
} else if(render_mode=="coupon_insert") {
    coupon_insert();
} else {
    assert(false,str("Unknown render_mode: ",render_mode));
}
