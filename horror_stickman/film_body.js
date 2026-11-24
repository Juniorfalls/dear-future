// ===== FOG RIDGE 2D FILM =====
// Expects `const SCENES = {...}` with {dur, cuts, shots:[{slug,kind,title,focus}], events:[...]}
// painted for the stickman engine. One world: an interior lamp room and the
// exterior cliff, with every shot a camera on one of them.

const MARA={skin:'#E9C6A0',cloth:'#5C6672',hood:'#3A4552',hand:'#E9C6A0',face:'#14121B',leg:'#232A38',shoe:'#10131A',finger:'#14121B',hair:'#241C24',coat:true};
const CAPT={skin:'#D9B58C',cloth:'#26344A',hood:'#1A2536',hand:'#D9B58C',face:'#14121B',leg:'#1D2633',shoe:'#0E1117',finger:'#14121B',hat:true};
const SHAD={skin:'#161A24',cloth:'#11151D',hood:'#080A10',hand:'#161A24',face:'#05070B',leg:'#080A10',shoe:'#05070B',finger:'#05070B',coat:true};
const CUTS=SCENES.cuts, LAST=CUTS[CUTS.length-1];
const stOf=s=>CUTS[s]/30, enOf=s=>CUTS[s+1]/30;

function coldSky(x,t,storm){
  let g=x.createLinearGradient(0,-420,0,760);
  g.addColorStop(0,'#070b13');
  g.addColorStop(.42,'#111a27');
  g.addColorStop(.72,'#223041');
  g.addColorStop(.88,'#334154');
  g.addColorStop(1,'#101822');
  x.fillStyle=g;x.fillRect(-1000,-700,4200,2200);
  // long cloud slabs, drifting; no sparkle or bokeh
  for(let i=0;i<7;i++){
    const y=-80+i*105+Math.sin(t*.10+i*1.7)*10;
    g=x.createLinearGradient(0,y-60,0,y+70);
    g.addColorStop(0,'rgba(8,12,20,0)');
    g.addColorStop(.48,`rgba(${38+i*3},${48+i*3},${62+i*3},${.09+.025*storm})`);
    g.addColorStop(1,'rgba(8,12,20,0)');
    x.fillStyle=g;x.fillRect(-900,y-60,3800,140);
  }
  if(storm>.8){
    g=x.createLinearGradient(0,120,0,680);
    g.addColorStop(0,'rgba(160,188,205,.10)');
    g.addColorStop(1,'rgba(160,188,205,0)');
    x.fillStyle=g;x.fillRect(-900,120,3800,560);
  }
}

function coldSea(x,t,storm){
  let g=x.createLinearGradient(0,620,0,1010);
  g.addColorStop(0,'#16222c');g.addColorStop(.35,'#0b141c');g.addColorStop(1,'#060a10');
  x.fillStyle=g;x.fillRect(-900,620,3800,520);
  x.lineCap='round';
  for(let i=0;i<17;i++){
    const y=642+i*23,amp=4+i*.8;
    x.strokeStyle=`rgba(${80+i*2},${105+i*2},${122+i*2},${.06+.025*storm})`;
    x.lineWidth=2+i*.14;x.beginPath();
    for(let px=-700;px<3000;px+=42)x.lineTo(px,y+Math.sin(px*.011+t*(.5+i*.03)+i)*amp);
    x.stroke();
  }
}

function fogBands(x,t,a,base=500){
  for(let i=0;i<5;i++){
    const y=base+i*86+Math.sin(t*.16+i*1.4)*13;
    const g=x.createLinearGradient(0,y-76,0,y+82);
    g.addColorStop(0,'rgba(170,190,202,0)');
    g.addColorStop(.46,`rgba(170,190,202,${a*(.55+.45*Math.sin(t*.27+i*1.9))})`);
    g.addColorStop(1,'rgba(170,190,202,0)');
    x.fillStyle=g;x.fillRect(-900,y-76,3800,160);
  }
}

function cliff(x,side){
  x.fillStyle='#05070c';
  x.beginPath();x.moveTo(-900,980);
  if(side<0){x.lineTo(-870,780);x.lineTo(-540,796);x.lineTo(-420,872);x.lineTo(-160,858);x.lineTo(40,910);x.lineTo(210,980)}
  else{x.lineTo(1080,980);x.lineTo(1150,890);x.lineTo(1320,846);x.lineTo(1540,862);x.lineTo(1740,824);x.lineTo(1970,856);x.lineTo(2160,790);x.lineTo(2420,824);x.lineTo(2640,980)}
  x.lineTo(3000,1080);x.lineTo(-1000,1080);x.closePath();x.fill();
  x.fillStyle='#0b0f16';
  x.beginPath();x.moveTo(1080,990);x.lineTo(1170,906);x.lineTo(1350,880);x.lineTo(1600,890);x.lineTo(1840,856);x.lineTo(2080,892);x.lineTo(2300,856);x.lineTo(2600,930);x.lineTo(2800,1080);x.lineTo(1000,1080);x.closePath();x.fill();
}

function farCliff(x,t){
  x.fillStyle='rgba(8,11,17,.92)';
  x.beginPath();x.moveTo(1940,760);x.lineTo(2040,698);x.lineTo(2180,724);x.lineTo(2320,676);x.lineTo(2460,718);x.lineTo(2620,780);x.lineTo(2620,960);x.lineTo(1900,960);x.closePath();x.fill();
  x.fillStyle='rgba(20,27,36,.45)';
  x.beginPath();x.moveTo(2000,742);x.lineTo(2100,706);x.lineTo(2230,734);x.lineTo(2370,698);x.lineTo(2500,740);x.lineTo(2500,820);x.lineTo(1980,820);x.closePath();x.fill();
  // ledge the watcher stands on, so the feet never float over the sea
  x.fillStyle='#080c13';x.beginPath();x.moveTo(1950,744);x.lineTo(1995,728);x.lineTo(2088,732);x.lineTo(2130,752);x.lineTo(2140,812);x.lineTo(1958,812);x.closePath();x.fill();
}

function lighthouse(x,t,beamA,fade){
  const bx=1500,by=928;
  x.fillStyle='#05070b';
  x.beginPath();x.moveTo(bx-170,by+40);x.lineTo(bx-120,by-66);x.lineTo(bx+110,by-74);x.lineTo(bx+182,by+46);x.closePath();x.fill();
  // tower: tapered, banded masonry
  x.fillStyle='#151b25';
  x.beginPath();x.moveTo(bx-96,by);x.lineTo(bx-60,386);x.lineTo(bx+60,386);x.lineTo(bx+96,by);x.closePath();x.fill();
  x.fillStyle='#202936';
  for(let i=0;i<6;i++){const y0=by-i*88;x.beginPath();x.moveTo(bx-94+i*6,y0);x.lineTo(bx+94-i*6,y0);x.lineTo(bx+91-i*6,y0-34);x.lineTo(bx-91+i*6,y0-34);x.closePath();x.fill()}
  x.fillStyle='rgba(9,13,20,.55)';
  x.beginPath();x.moveTo(bx-7,by);x.lineTo(bx-4,390);x.lineTo(bx+5,390);x.lineTo(bx+9,by);x.closePath();x.fill();
  // gallery
  x.fillStyle='#0a0e15';x.fillRect(bx-86,360,172,18);
  x.strokeStyle='#2b3542';x.lineWidth=4;
  for(let i=-3;i<=3;i++){x.beginPath();x.moveTo(bx+i*26,360);x.lineTo(bx+i*26,314);x.stroke()}
  x.beginPath();x.moveTo(bx-82,314);x.lineTo(bx+82,314);x.stroke();
  // lantern room
  x.fillStyle='#090d14';x.fillRect(bx-55,276,110,84);
  let g=x.createLinearGradient(bx-46,0,bx+46,0);
  g.addColorStop(0,'rgba(255,178,92,.18)');g.addColorStop(.5,'rgba(255,214,148,.92)');g.addColorStop(1,'rgba(255,178,92,.18)');
  x.fillStyle=g;x.fillRect(bx-43,286,86,64);
  x.fillStyle='#101620';
  for(const m of [-34,-12,12,34])x.fillRect(bx+m-2,286,4,64);
  x.fillStyle='#0a0e15';x.beginPath();x.moveTo(bx-65,278);x.lineTo(bx,232);x.lineTo(bx+65,278);x.closePath();x.fill();
  // faint warm halo (light source, not decoration)
  g=x.createRadialGradient(bx,318,10,bx,318,300);
  g.addColorStop(0,`rgba(255,196,120,${.24*fade})`);g.addColorStop(.45,`rgba(255,174,94,${.07*fade})`);g.addColorStop(1,'rgba(255,174,94,0)');
  x.fillStyle=g;x.fillRect(bx-320,0,640,640);
  if(fade>0.01){
    x.save();x.translate(bx,318);x.rotate(beamA);x.globalAlpha=fade;
    g=x.createLinearGradient(0,0,1700,0);
    g.addColorStop(0,'rgba(255,218,156,.42)');g.addColorStop(.45,'rgba(255,206,134,.13)');g.addColorStop(1,'rgba(255,206,134,0)');
    x.fillStyle=g;x.beginPath();x.moveTo(0,-21);x.lineTo(1700,-190);x.lineTo(1700,190);x.lineTo(0,21);x.closePath();x.fill();
    x.globalAlpha=fade*.35;
    g=x.createLinearGradient(0,0,-800,0);
    g.addColorStop(0,'rgba(255,206,134,.28)');g.addColorStop(1,'rgba(255,206,134,0)');
    x.fillStyle=g;x.beginPath();x.moveTo(0,-18);x.lineTo(-800,-130);x.lineTo(-800,130);x.lineTo(0,18);x.closePath();x.fill();
    x.restore();
  }
}

function rainSheet(x,t,a=1,y0=-180,h=1500){
  drawRain(x,t,a,850,-250,y0,h);
}

function otsShoulder(x,t,side=1,warm=0){
  x.save();
  if(side>0)x.translate(1920,0),x.scale(-1,1);
  x.fillStyle='#04060a';
  x.beginPath();x.moveTo(-40,1120);
  x.quadraticCurveTo(-30,786,140,742);
  x.quadraticCurveTo(262,708,322,642);
  x.quadraticCurveTo(370,566,456,560);
  x.quadraticCurveTo(560,556,588,650);
  x.quadraticCurveTo(616,748,548,850);
  x.quadraticCurveTo(470,970,520,1120);
  x.closePath();x.fill();
  // rim on the shoulder, cold
  x.strokeStyle=warm>0?'rgba(238,178,118,.22)':'rgba(142,174,196,.20)';
  x.lineWidth=5;x.lineCap='round';
  x.beginPath();x.moveTo(320,640);x.quadraticCurveTo(368,568,452,560);x.stroke();
  x.restore();
}

// ---------------- interior lamp room ----------------
function roomWall(x,t,storm){
  let g=x.createLinearGradient(0,-160,0,940);
  g.addColorStop(0,'#0c111a');g.addColorStop(.58,'#161f2c');g.addColorStop(1,'#0b1017');
  x.fillStyle=g;x.fillRect(-500,-300,3200,1500);
  for(let i=0;i<28;i++){
    const px=-180+i*92;
    x.strokeStyle=`rgba(${52+i%3*4},${63+i%4*4},${78+i%5*3},.22)`;
    x.lineWidth=2;x.beginPath();x.moveTo(px,-200);x.lineTo(px,880);x.stroke();
  }
  // window: the storm outside
  const wx=1730,wy=238,ww=332,wh=424;
  x.save();x.beginPath();x.rect(wx,wy,ww,wh);x.clip();
  let q=x.createLinearGradient(0,wy,0,wy+wh);
  q.addColorStop(0,'#111a26');q.addColorStop(.62,'#2b3c4d');q.addColorStop(1,'#0c1520');
  x.fillStyle=q;x.fillRect(wx,wy,ww,wh);
  x.strokeStyle='rgba(120,150,168,.16)';x.lineWidth=3;
  for(let i=0;i<4;i++){const y=wy+250+i*38;x.beginPath();x.moveTo(wx,y);x.quadraticCurveTo(wx+ww*.5,y+16,wx+ww,y-4);x.stroke()}
  rainSheet(x,t,.55,wy-20,wh+60);
  const flash=storm>.7?Math.max(0,Math.sin(t*2.7)-.86)*6:0;
  if(flash>0.02){x.fillStyle=`rgba(190,210,225,${Math.min(.22,flash)})`;x.fillRect(wx,wy,ww,wh)}
  x.restore();
  x.strokeStyle='#0a0e15';x.lineWidth=18;x.strokeRect(wx-9,wy-9,ww+18,wh+18);
  x.strokeStyle='#394554';x.lineWidth=5;x.strokeRect(wx,wy,ww,wh);
  x.lineWidth=6;x.beginPath();x.moveTo(wx+ww/2,wy);x.lineTo(wx+ww/2,wy+wh);x.moveTo(wx,wy+wh*.52);x.lineTo(wx+ww,wy+wh*.52);x.stroke();
  // wall lamp
  const lx=612,ly=332;
  x.strokeStyle='#1e2836';x.lineWidth=8;x.beginPath();x.moveTo(lx-58,ly-30);x.lineTo(lx+4,ly-30);x.stroke();
  x.fillStyle='#202a38';x.beginPath();x.moveTo(lx-52,ly-30);x.lineTo(lx+40,ly-30);x.lineTo(lx+28,ly+34);x.lineTo(lx-38,ly+34);x.closePath();x.fill();
  g=x.createRadialGradient(lx,ly+20,4,lx,ly+20,250);
  g.addColorStop(0,'rgba(255,184,104,.32)');g.addColorStop(.42,'rgba(255,164,82,.09)');g.addColorStop(1,'rgba(255,164,82,0)');
  x.fillStyle=g;x.fillRect(lx-280,ly-220,560,560);
  x.fillStyle='rgba(255,214,152,.72)';x.fillRect(lx-29,ly+8,58,10);
  // shelf and a dead clock
  x.fillStyle='#1a2330';x.fillRect(330,470,210,15);
  x.fillStyle='#0d121a';x.beginPath();x.roundRect(376,412,52,58,8);x.fill();
  x.strokeStyle='#5d6c7c';x.lineWidth=2;x.beginPath();x.moveTo(402,470);x.lineTo(402,432);x.moveTo(402,470);x.lineTo(428,456);x.stroke();
}

function consoleSet(x,t,lit){
  // tall radio console; the cabinet front is drawn after the actor so the
  // keeper stands behind it and her lower body is hidden.
  x.fillStyle='#10161f';x.fillRect(1016,420,528,30);
  x.fillStyle='#1a2330';x.fillRect(1016,450,528,12);
  // console body and radio sit on the top
  x.fillStyle='#0b1018';x.beginPath();x.roundRect(1212,330,236,90,10);x.fill();
  x.fillStyle='#222d3c';x.beginPath();x.roundRect(1220,338,220,74,8);x.fill();
  x.fillStyle='#0c1119';x.beginPath();x.roundRect(1232,348,132,52,6);x.fill();
  // speaker slots
  x.strokeStyle='rgba(120,138,154,.22)';x.lineWidth=3;
  for(let i=0;i<5;i++){x.beginPath();x.moveTo(1242,356+i*9);x.lineTo(1354,356+i*9);x.stroke()}
  // dials
  x.fillStyle='#151d28';x.beginPath();x.roundRect(1288,404,88,20,6);x.fill();
  x.fillStyle='#2c3949';x.beginPath();x.roundRect(1368,346,52,16,5);x.fill();
  x.fillStyle='#8b98a7';x.fillRect(1390,350,4,8);
  // green signal lamp
  const pulse=lit>0?(.55+.45*Math.abs(Math.sin(t*3.1))):0;
  if(pulse>0.01){
    let g=x.createRadialGradient(1332,388,1,1332,388,54);
    g.addColorStop(0,`rgba(92,255,172,${.38*pulse})`);g.addColorStop(.4,`rgba(72,238,152,${.10*pulse})`);g.addColorStop(1,'rgba(72,238,152,0)');
    x.fillStyle=g;x.fillRect(1278,334,108,108);
  }
  x.fillStyle=lit>0?`rgba(108,255,178,${.55+.35*pulse})`:'rgba(34,48,44,.7)';
  x.beginPath();x.roundRect(1326,384,13,9,3);x.fill();
  // tuning knob the keeper's hand rests on
  x.fillStyle='#42536a';x.beginPath();x.roundRect(1340,392,22,20,7);x.fill();
  x.fillStyle='#9fb0c0';x.beginPath();x.roundRect(1348,396,6,12,3);x.fill();
  x.strokeStyle='rgba(150,182,202,.30)';x.lineWidth=2;x.beginPath();x.moveTo(1341,393);x.lineTo(1361,411);x.stroke();
  // small needle dial
  x.strokeStyle='rgba(196,210,220,.35)';x.lineWidth=2;
  x.beginPath();x.moveTo(1382,374);x.lineTo(1408,362+Math.sin(t*.9)*10);x.stroke();
  // microphone on the top
  x.strokeStyle='#1c2634';x.lineWidth=8;x.beginPath();x.moveTo(1140,420);x.lineTo(1148,374);x.stroke();
  x.fillStyle='#202b3a';x.beginPath();x.roundRect(1124,336,42,38,14);x.fill();
  x.fillStyle='#0b0f16';x.beginPath();x.roundRect(1132,342,26,24,10);x.fill();
}

function drawMic(x,hp,scale){
  // hand-held mic from the actor's hand toward the mouth
  const mx=hp[0],my=hp[1];
  x.save();x.translate(mx,my);x.rotate(-.42);
  x.fillStyle='#1c2532';x.beginPath();x.roundRect(-12,-58,24,84,10);x.fill();
  x.fillStyle='#344252';x.beginPath();x.roundRect(-16,-68,32,30,12);x.fill();
  x.fillStyle='rgba(150,166,180,.35)';x.fillRect(-9,-62,4,18);x.restore();
}

function handInsert(x,t){
  const shake=Math.sin(t*22)*2.1+Math.sin(t*7.3)*1.4;
  // forearm entering from the right
  x.save();x.strokeStyle='#C89E7D';x.lineCap='round';x.lineWidth=58;
  x.beginPath();x.moveTo(1540,500);x.lineTo(1394+shake,414+shake*.4);x.stroke();
  x.strokeStyle='#E2B994';x.lineWidth=46;
  x.beginPath();x.moveTo(1520,492);x.lineTo(1396+shake,416+shake*.4);x.stroke();
  // fist around the knob
  x.fillStyle='#E9C6A0';x.beginPath();x.roundRect(1336+shake,374+shake*.5,60,44,18);x.fill();
  x.strokeStyle='#14121B';x.lineWidth=3;
  for(let i=0;i<4;i++){x.beginPath();x.moveTo(1346+i*12+shake,384+shake*.5);x.lineTo(1348+i*12+shake,406+shake*.5);x.stroke()}
  x.fillStyle='rgba(70,44,34,.35)';x.beginPath();x.roundRect(1344+shake,408+shake*.5,46,10,5);x.fill();
  x.restore();
}

function interior(t,cam,s,u,kind){
  const st=stOf(s),en=enOf(s),storm=kind==='storm'?1:.62;
  let x=layer('wall',cam,.82);roomWall(x,t,storm);
  x=layer('set',cam);consoleSet(x,t,kind==='opening'?1:(kind==='console'||kind==='final'?1:0));
  if(kind==='radio_insert'){
    // close insert: radio panel only; a raking light sweeps the face so the
    // static insert still has motion between cuts.
    let g=x.createLinearGradient(1120,250,1560,500);
    g.addColorStop(0,'rgba(150,180,200,.07)');g.addColorStop(.55,'rgba(150,180,200,0)');g.addColorStop(1,'rgba(0,0,0,.25)');
    x.fillStyle=g;x.fillRect(980,240,620,360);
    const sx=1110+260*(1+Math.sin(t*.72));
    g=x.createLinearGradient(sx-70,250,sx+70,520);
    g.addColorStop(0,'rgba(176,206,224,0)');g.addColorStop(.5,'rgba(176,206,224,.16)');g.addColorStop(1,'rgba(176,206,224,0)');
    x.save();x.globalCompositeOperation='screen';x.fillStyle=g;x.fillRect(1120,240,500,380);
    x.fillStyle='rgba(64,88,108,.20)';x.fillRect(1200,326,260,100);x.restore();
    x.strokeStyle='rgba(158,192,212,.24)';x.lineWidth=3;x.strokeRect(1220,338,220,74);
    x.fillStyle='rgba(132,196,170,.055)';
    const sy=336+56*(1+Math.sin(t*.9+1.3));x.fillRect(1232,sy,132,2);
  }
  x=layer('act',cam);
  if(kind==='hand')handInsert(x,t);
  if(kind!=='radio_insert'&&kind!=='hand'){
    const p={x:1450,y:standY(920,.82),s:.82,face:-1,breath:t*1.85,
      look:kf(t,[[st,.20],[st+.7,.56],[en,.12]]),lookY:kf(t,[[st,.26],[st+.8,.10],[en,.22]]),
      brow:kf(t,[[st,.16],[st+.9,.50],[en,.72]]),sad:.42,tilt:.045,
      blink:blinkAt(t,[st+.8,st+2.4,en-1.0]),
      mouth:kind==='speaks'?talk(t,st+.15,en-.15):kf(t,[[st,.10],[st+1,.18],[en,.10]]),
      hands:{},tuck:{l:true},showH:{l:true}};
    if(kind==='speaks'){
      p.hands.r=[38,-94];p.hands.l=[-110,212];p.tuck={};p.showH={r:true};
      p.sad=.62;p.brow=.62;p.lookY=.06;
      const q=actor(x,'mara',MARA,p,cam,'rgba(255,198,148,.92)',1);
      drawMic(x,h2w(q,'r'),p.s);
      contact('hand-mic',h2w(q,'r'),[p.x+p._h.r[0]*p.s,p.y+p._h.r[1]*p.s]);
    }else{
      p.hands.l=w2l(p,[1350,402]);
      actor(x,'mara',MARA,p,cam,'rgba(255,198,148,.92)',1);
      contact('hand-radio',h2w(p,'l'),[1350,402]);
    }
  }
  // foreground console cabinet and haze
  x=layer('fg',cam,1.04);
  if(kind!=='radio_insert'&&kind!=='hand'){
    x.fillStyle='#0b1017';x.fillRect(1016,450,528,390);
    x.fillStyle='#131b26';x.fillRect(1016,450,528,10);
    x.fillStyle='#080c12';x.fillRect(1044,470,476,330);
    x.fillStyle='#0a0e15';x.fillRect(1008,420,544,30);
  }
  let g=x.createLinearGradient(0,1000,0,1080);g.addColorStop(0,'rgba(4,6,10,0)');g.addColorStop(1,'rgba(4,6,10,.75)');
  x.fillStyle=g;x.fillRect(-300,980,2600,160);
  comp([['wall',cam.b[0]],['set',cam.b[1]],['act',0],['fg',cam.b[2]]]);
}

// ---------------- exterior ----------------
function exterior(t,cam,s,u,kind){
  const st=stOf(s),en=enOf(s);
  const storm=kind==='storm'?1:.55;
  const beamA=(-1.55+t*.42)%(Math.PI*2);
  const beamFade=kind==='end'?kf(t,[[st,.9],[en,.15]]):1;
  let x=layer('sky',cam,.32);coldSky(x,t,storm);
  x=layer('far',cam,.55);coldSea(x,t,storm);farCliff(x,t);fogBands(x,t,.05,520);
  x=layer('set',cam);cliff(x,-1);lighthouse(x,t,beamA,beamFade);fogBands(x,t,.06,660);
  if(kind==='storm'){
    // no figure here: the shot is the tower and the weather
  }
  if(kind==='fog'||kind==='whisper'||kind==='captain'){
    x=layer('act',cam);
    if(kind==='captain'){
      const cp={x:1730,y:standY(800,.52),s:.52,face:-1,breath:t*1.4,hat:true,
        look:kf(t,[[st,-.3],[en,-.55]]),lookY:.55,tilt:.16,brow:-.3,sad:-.45,mouth:-.3,blink:blinkAt(t,[st+1.7])};
      actor(x,'captain',CAPT,cp,cam,'rgba(146,176,198,.45)',-1);
      const sp={x:1930,y:standY(800,.58),s:.58,face:-1,breath:t*1.2,coat:true,flut:.7,time:t,hat:true,
        look:kf(t,[[st,-.2],[en,-.5]]),brow:-.6,sad:-.8,mouth:-.5};
      actor(x,'shad',SHAD,sp,cam,'rgba(120,150,174,.30)',-1);
    }else{
      const sp={x:kind==='whisper'?1790:2020,y:standY(kind==='whisper'?770:760,kind==='whisper'?.60:.48),s:kind==='whisper'?.60:.48,
        face:-1,breath:t*1.25,coat:true,flut:.75,time:t,hat:true,
        look:kf(t,[[st,-.2],[en,-.55]]),brow:-.65,sad:-.8,mouth:-.5,blink:0};
      actor(x,'shad',SHAD,sp,cam,'rgba(118,148,172,.34)',-1);
    }
    x=layer('ots',cam,1.32);otsShoulder(x,t,-1,kind==='captain'?1:0);
  }else{
    x=layer('act',cam);
    x=layer('ots',cam,1.32);
  }
  if(kind==='end'){
    x=layer('act',cam);
    const p={x:1120,y:standY(912,.64),s:.64,face:1,breath:t*1.7,coat:true,flut:kf(t,[[st,.3],[en,.9]]),time:t,
      look:kf(t,[[st,.35],[en,-.15]]),lookY:kf(t,[[st,.1],[en,.3]]),brow:.6,sad:.72,mouth:.08,
      blink:blinkAt(t,[st+1.3,en-.8]),tilt:-.03};
    actor(x,'mara',MARA,p,cam,'rgba(255,198,148,.42)',1);
  }
  x=layer('rain',cam,1.15);rainSheet(x,t,kind==='storm'?.92:.55);
  x=layer('fg',cam,1.2);
  let g=x.createLinearGradient(0,930,0,1080);g.addColorStop(0,'rgba(3,5,9,0)');g.addColorStop(1,'rgba(3,5,9,.9)');
  x.fillStyle=g;x.fillRect(-400,900,3000,260);
  comp([['sky',cam.b[0]],['far',cam.b[1]],['set',0],['act',0],['ots',6,.96],['rain',0,.5],['fg',cam.b[2]]]);
}

const CAMS={
  opening:{x:1250,y:520,z:1.03,push:.06,dx:26,dy:-4,b:[4,1.4,0]},
  console:{x:1400,y:420,z:1.62,push:.08,dx:10,dy:-3,b:[9,4,0]},
  fog:{x:1260,y:548,z:1.00,push:.05,dx:34,dy:-2,b:[4,1.3,0]},
  radio_insert:{x:1331,y:384,z:2.95,push:.23,dx:24,dy:-10,b:[15,0,0]},
  storm:{x:1120,y:540,z:.82,push:.06,dx:22,dy:-5,b:[3,.9,0]},
  speaks:{x:1428,y:420,z:1.74,push:.10,dx:8,dy:-3,b:[10,5,0]},
  whisper:{x:1340,y:552,z:1.02,push:.05,dx:28,dy:-2,b:[4,1.2,0]},
  beam:{x:1460,y:410,z:1.18,push:.14,dx:-22,dy:6,b:[8,4,0]},
  hand:{x:1332,y:400,z:3.10,push:.05,dx:10,dy:-3,b:[16,0,0]},
  captain:{x:1390,y:624,z:1.14,push:.06,dx:18,dy:-2,b:[5,1.6,0]},
  final:{x:1428,y:418,z:1.78,push:.11,dx:6,dy:-2,b:[10,5,0]},
  end:{x:1220,y:548,z:.78,push:.04,dx:50,dy:-3,b:[3,.8,0]}
};

const INT_KINDS=new Set(['opening','console','radio_insert','speaks','hand','final']);

FILM={dur:SCENES.dur,cuts:SCENES.cuts,fadeIn:.7,fadeOut:.9,
  cam(s,u,t){
    const k=SCENES.shots[s].kind,c=CAMS[k]||CAMS.console;
    let x=c.x+(c.dx||0)*u,y=c.y+(c.dy||0)*u,z=c.z*(1+(c.push||0)*u);
    if(k==='storm'){x+=Math.sin(t*1.6)*2.4;y+=Math.cos(t*1.25)*1.7}
    return {x,y,z,b:c.b};
  },
  draw(t,cam,s,u){
    const k=SCENES.shots[s].kind;
    if(INT_KINDS.has(k))interior(t,cam,s,u,k);else exterior(t,cam,s,u,k);
  },
  warm(t){return .04},
  plants(){return {}}
};

for(const e of (SCENES.events||[]))say(e.t,e.k);
