// Emil ETA 5229 / V3.1. Souřadnice sestavy v mm: x vpřed, y vlevo, z vzhůru.
// Z=0 je horní plocha talíře. Přepínač part dodá STL v orientaci pro tisk.
// Návrhové hodnoty původní sestavy ověř na fyzickém robotu před lepením.
part = "talir"; // [talir,stojan,pojistka-tabletu,prichytka-ramene]
$fn = 96;
deck_r = 164;
deck_t = 7;

module rect(x1,x2,y1,y2,z1,z2) {
    translate([x1,y1,z1]) cube([x2-x1,y2-y1,z2-z1]);
}
module rounded2(x1,x2,y1,y2,r=3) {
    hull() for(x=[x1+r,x2-r],y=[y1+r,y2-r]) translate([x,y]) circle(r=r,$fn=32);
}
module slot2(x1,y1,x2,y2,d) {
    hull() for(p=[[x1,y1],[x2,y2]]) translate(p) circle(d=d,$fn=32);
}
module deck_outline() {
    intersection() {
        circle(r=deck_r,$fn=256);
        union() {
            difference(){circle(r=deck_r,$fn=256); circle(r=deck_r-11,$fn=256);}
            // Paprsky propojují střed, obruč i jednotlivé montážní plochy.
            for(a=[0:45:315]) rotate(a) translate([-2,-6]) square([deck_r+2,12]);
            circle(r=44);
            rounded2(36,148,-102,63,9); // tovární deska Waveshare, objímky a dorazy
            rounded2(-52,52,-145,-48,7); // miska
            rounded2(-92,-37,-49,49,7);  // příruba stojanu
            for(a=[40,-40]) rotate(a) translate([-110,-7]) square([112,14]);
        }
    }
}
module deck() {
  difference() {
    translate([0,0,-deck_t]) linear_extrude(deck_t) deck_outline();
    translate([0,0,-deck_t-1]) linear_extrude(deck_t+2) union() {
      // Čtyři příchytky sevřou volné hrany tovární desky bez vrtání Waveshare.
      for(p=[[44,37],[44,-33],[138,37],[138,-69]])
        slot2(p[0],p[1]-4,p[0],p[1]+4,4.5);
      // Dva dorazové sloupky Ø8 s otvory M4 pro konce tovární desky.
      slot2(73,57,73,61,4.5); slot2(77,-101,77,-97,4.5);
      for(x=[-79,-48],y=[-32,32]) translate([x,y]) circle(d=4.6,$fn=32);
      // Pásky 4,8 mm vedou pod miskou a obtáčejí její boční stěny.
      for(x=[-24,24],y=[-51.5,-142.5]) slot2(x-3,y,x+3,y,2.8);
      // Dvojice průvleků na kabelový pásek. Vedení držet nad optickou rovinou.
      for(y=[12,22]) slot2(-105,y,-100,y,3.5);
    }
  }
}

module xhole(x1,x2,y,z,d) {
    translate([x1,y,z]) rotate([0,90,0]) cylinder(d=d,h=x2-x1,$fn=32);
}
module tablet_stand() {
    // Redmi Pad Pro bez pouzdra 280 x 181,85 x 7,52 mm v poloze na šířku.
    // Tělo tabletu v x=-59,76..-52,24, y=±140, z=77..258,85.
    difference() {
      union() {
        rect(-86,-40,-40,40,0,8);                      // příruba čtyř šroubů M4
        // Zadní rovina x=-86 je zároveň tiskovou plochou. Podélná žebra
        // pokračují nad horní hranu displeje až k držáku stereokamer.
        rect(-86,-78,-23,23,0,295);
        for(y=[-19,12]) rect(-85,-69,y,y+7,0,295);
        for(y=[-24,18]) hull() {
            rect(-84,-42,y,y+6,7,9);
            rect(-84,-67,y,y+6,48,50);
        }
        // Otevřená spodní kolébka a koncové dorazy; horní třmen lze sundat.
        rect(-86,-46,-146,146,71,77);
        for(y=[-146,141.5]) rect(-86,-46,y,y+4.5,75,82);
        for(y=[-100,72]) rect(-51.2,-46.5,y,y+28,76,85);
        for(y=[-90,58]) rect(-86,-60.8,y,y+32,76,92);
        rect(-86,-70,-76,76,245,260);                // otvory pro horní třmen
        rect(-86,-61,-24,24,278,295);                 // stereo příruba, x=-61
      }
      for(x=[-79,-48],y=[-32,32])
        translate([x,y,-1]) cylinder(d=4.6,h=10,$fn=32);
      for(y=[-32,32]) xhole(-88,-68,y,252,4.5);
      for(y=[-13,13]) xhole(-88,-59,y,287,4.5);
    }
}
module tablet_catch() {
    // M4 matice zapuštěné zepředu. Šrouby se dotahují zezadu mimo displej.
    difference() {
      union() {
        rect(-70,-61.4,-74,74,246,262);
        for(y=[-74,52]) {
          rect(-70,-47.5,y,y+22,260.2,265.3);
          rect(-51,-47.5,y,y+22,252.5,265.3);
        }
      }
      for(y=[-32,32]) {
        xhole(-72,-60,y,252,4.5);
        translate([-65,y,252]) rotate([0,90,0]) cylinder(d=8.35,$fn=6,h=4.5);
      }
    }
}
module arm_clamp() {
    // Plochý horní povrch dolů na tiskové podložce. 4 kusy kolem levé
    // a pravé hrany originální kovové desky; pod špičku pružná podložka.
    difference() {
        union() {
            translate([0,0,9.8]) linear_extrude(4.6) rounded2(-11,12,-7,7,2);
            rect(-11,-6,-6,6,0,10.8);
        }
        translate([0,0,8]) linear_extrude(8) slot2(-2,0,2,0,4.5);
    }
}
if(part=="talir") rotate([180,0,0]) deck();
else if(part=="stojan") multmatrix([[0,1,0,0],[0,0,1,0],[1,0,0,86],[0,0,0,1]]) tablet_stand();
else if(part=="pojistka-tabletu") multmatrix([[0,1,0,0],[0,0,1,-246],[1,0,0,70],[0,0,0,1]]) tablet_catch();
else if(part=="prichytka-ramene") translate([0,0,14.4]) rotate([180,0,0]) arm_clamp();
else assert(false,str("Neznámý díl ",part));
