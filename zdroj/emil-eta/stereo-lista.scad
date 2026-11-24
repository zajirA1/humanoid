// Emil ETA V3 – společné sedlo pro dvě USB kamery Yahboom AHB015.
// Jednotky mm. Zadní plochou dolů na podložku. Kamerové hlavy stáhnout
// na čtyřech samostatných sedlech pásky šířky 2,5–3,5 mm přes oba konce.
// Středy pro tovární sponu, kloub a kabel zůstávají otevřené.
// Po dotažení zajistit ostření, změřit obě optické osy a stereo kalibrovat.
$fn = 64;
roztec = 110;
sklon = 20;

// Tiskové osy u,v,w: doprava při pohledu zepředu, vzhůru, od stěžně vpřed.
// V simulaci [X,Y,Z] = [-61+w,402+v,-u].
// Soustava sedla [u,d,h]: boční, ve směru pohledu, kolmo vzhůru.
module sedlove_osy() {
    multmatrix([[1,0,0,0], [0,-sin(sklon),cos(sklon),9],
                [0,cos(sklon),sin(sklon),10], [0,0,0,1]]) children();
}

module zaoblena_deska(u0,u1,v0,v1,w0,w1,r) {
    hull() for (u=[u0+r,u1-r],v=[v0+r,v1-r])
        translate([u,v,w0]) cylinder(h=w1-w0,r=r);
}

module podpera(u) {
    // Zadní pevná opora, spojující každé sedlo přímo s výztuhou.
    hull() {
        translate([u-6,11,0]) cube([12,14,5.6]);
        sedlove_osy() translate([u-6,-4,0]) cube([12,3.5,17]);
    }
    // Uložení na dvě vnitřní roviny; čelo hlavy i mikrofon jsou volné.
    sedlove_osy() {
        translate([u-6,-4,-3]) cube([12,32,3]);
        translate([u-6,-4,-2.5]) cube([12,4,31]);
    }
}

module stereo_lista() {
    difference() {
        union() {
            zaoblena_deska(-103,103,10,27,0,6,4);
            zaoblena_deska(-24,24,-7,27,0,7,4);
            for (stred=[-roztec/2,roztec/2], k=[-31,31]) podpera(stred+k);
        }
        // Průchozí M4 pro dva šrouby s podložkou a maticí v držáku tabletu.
        for (u=[-13,13]) translate([u,0,-1]) cylinder(h=10,d=4.5);
        // Pásky projdou dnem a horní částí zadního sedla mimo výztuhu.
        for (stred=[-roztec/2,roztec/2], k=[-31,31])
            sedlove_osy() {
                translate([stred+k-2.4,23.4,-4.0]) cube([4.8,2.2,6]);
                translate([stred+k-2.4,-6,24.3]) cube([4.8,8,2.2]);
            }
        // Párové štěrbiny pro odlehčení obou USB kabelů za příčkou.
        for (strana=[-1,1], vzdalenost=[65,72])
            translate([strana*vzdalenost-1.15,15,-1]) cube([2.3,5.4,9]);
    }
}

stereo_lista();
