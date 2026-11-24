// Emil on the ETA 5229 Master. All dimensions are in mm; Z is up for printing.
// Original geometry: Emil-V1.glb, nodes 68–72 (tray) and 99 (sample object).
// In the robot's original coordinates, the tray bottom centre is [0, 115, 97]
// (X forward, Y up, Z right). The upper surface of its floor is at Y = 121.
// Verify available space and retention on the actual platform before mounting.

part = "tray"; // [tray,ball,footprint]

tray_length = 98;
tray_width = 92;
tray_floor = 6;
tray_wall = 3;
tray_rim_height = 12;    // measured from the inside floor
ball_diameter = 32;

// Stock Waveshare Robot Arm for Pi base, excluding cables. The manufacturer's
// dimensioned photo gives the exterior envelope but does not locate screw holes.
// https://www.waveshare.com/img/devkit/accBoard/Robot-Arm-for-Pi/Robot-Arm-for-Pi-size.jpg
base_length = 149.6;
base_width = 80;
gauge_height = 2;
gauge_border = 5;

module collection_tray() {
    height = tray_floor + tray_rim_height;
    difference() {
        translate([-tray_length/2, -tray_width/2, 0])
            cube([tray_length, tray_width, height]);
        // Extend the cutter through the opening to avoid coincident top faces.
        translate([-tray_length/2 + tray_wall, -tray_width/2 + tray_wall, tray_floor])
            cube([tray_length - 2*tray_wall, tray_width - 2*tray_wall, tray_rim_height + 1]);
    }
}

module test_ball() {
    // Cross-sections meet the poles and equator exactly. The ball has the
    // simulator's full round profile and will need support for a one-piece print.
    radius = ball_diameter / 2;
    profile = [for (a = [-90:3:90])
        [abs(a) == 90 ? 0 : radius*cos(a), radius + radius*sin(a)]];
    rotate_extrude($fn=96) polygon(profile);
}

module stock_base_footprint() {
    // Lay the outside perimeter on the ETA platform to check available space.
    // Set length/width to measured values to regenerate the rectangular envelope.
    // The stock base has rounded corners; this gauge includes those corner boxes.
    difference() {
        translate([-base_length/2, -base_width/2, 0])
            cube([base_length, base_width, gauge_height]);
        translate([-base_length/2 + gauge_border, -base_width/2 + gauge_border, -1])
            cube([base_length - 2*gauge_border, base_width - 2*gauge_border, gauge_height + 2]);
    }
}

if (part == "tray") collection_tray();
else if (part == "ball") test_ball();
else if (part == "footprint") stock_base_footprint();
else assert(false, str("Unknown part: ", part));
