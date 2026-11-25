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


// ---------------- road / hitchhiker scenes ----------------
function asphalt(x,hzY=520,bottom=1080){
  const g=x.createLinearGradient(0,hzY,0,bottom);
  g.addColorStop(0,'#0a0d13');g.addColorStop(.55,'#0d1119');g.addColorStop(1,'#141a24');
  x.fillStyle=g;
  x.beginPath();x.moveTo(960-32,hzY);x.lineTo(960+32,hzY);
  x.lineTo(960+1500,bottom);x.lineTo(960-1500,bottom);x.closePath();x.fill();
}
function roadMarks(x,hzY=520,bottom=1080){
  x.fillStyle='rgba(188,196,186,.42)';
  for(let i=0;i<9;i++){
    const p0=i/9,p1=p0+.055;
    const y0=hzY+(bottom-hzY)*p0*p0, y1=hzY+(bottom-hzY)*p1*p1;
    const w0=2+10*p0*p0, w1=2+10*p1*p1;
    x.fillRect(960-w0/2,y0,w0,Math.max(2,y1-y0));
  }
  // edge lines
  for(const side of [-1,1]){
    x.strokeStyle='rgba(150,158,150,.28)';x.lineWidth=3;
    x.beginPath();x.moveTo(960+side*34,hzY);x.lineTo(960+side*620,bottom);x.stroke();
  }
}
function tailLights(x,t,hzY=520){
  for(let i=0;i<5;i++){
    const px=760+i*88+Math.sin(t*.7+i)*6, py=hzY-4+Math.abs(i-2)*9;
    const a=.18+.12*Math.sin(t*1.3+i);
    const g=x.createRadialGradient(px,py,1,px,py,16);
    g.addColorStop(0,`rgba(196,74,54,${a+.25})`);g.addColorStop(1,'rgba(196,74,54,0)');
    x.fillStyle=g;x.fillRect(px-18,py-18,36,36);
    x.fillStyle=`rgba(220,110,80,${a+.3})`;x.fillRect(px-3,py-2,6,4);
  }
}
function drawRoad(x,t,st,en,kind){
  asphalt(x);roadMarks(x);
  // headlight wash from the viewer's car
  let g=x.createRadialGradient(960,1040,40,960,1040,760);
  g.addColorStop(0,'rgba(214,198,160,.16)');g.addColorStop(1,'rgba(214,198,160,0)');
  x.fillStyle=g;x.fillRect(180,540,1560,540);
  // shoulder posts rushing by
  for(let i=0;i<7;i++){
    const p=((i*140+t*260)%980)/980;
    const y=540+p*p*540, scale=.4+p*1.5, side=i%2?-1:1;
    x.fillStyle='#0a0d12';x.fillRect(960+side*(140+scale*520),y-70*scale,7*scale,70*scale);
  }
  if(kind==='roadside_sign')drawSign(x,t,st,en);
  else tailLights(x,t);
}
function drawSign(x,t,st,en){
  x.fillStyle='#0b0e14';x.fillRect(1370,470,26,510);
  x.fillStyle='#0a0c11';x.fillRect(1300,860,180,24);
  // rusted board
  const g=x.createLinearGradient(1080,300,1600,560);
  g.addColorStop(0,'#2a2a26');g.addColorStop(.45,'#3a382f');g.addColorStop(1,'#22221d');
  x.fillStyle=g;x.fillRect(1080,300,520,250);
  x.strokeStyle='rgba(214,204,180,.55)';x.lineWidth=8;x.strokeRect(1100,320,480,210);
  // rust streaks
  x.fillStyle='rgba(96,58,34,.45)';
  for(let i=0;i<7;i++){const rx=1120+i*70;x.fillRect(rx,320,5,70+(i*37)%120);}
  // text
  x.save();x.translate(1340,392);x.rotate(-.02);
  x.font='bold 74px sans-serif';x.textAlign='center';x.fillStyle='#ddd4c0';
  x.fillText('DO NOT',0,0);
  x.font='bold 92px sans-serif';x.fillText('STOP',0,96);
  x.restore();
  // weak lamp catching the board
  const lg=x.createRadialGradient(1340,430,10,1340,430,360);
  lg.addColorStop(0,'rgba(200,190,160,.10)');lg.addColorStop(1,'rgba(200,190,160,0)');
  x.fillStyle=lg;x.fillRect(980,220,720,460);
}
function drawCabin(x,t,st,en,cam,variant){
  variant=variant||'';
  // glass and what is beyond it
  const g=x.createLinearGradient(0,120,0,760);
  g.addColorStop(0,'#0a1220');g.addColorStop(.6,'#0d1726');g.addColorStop(1,'#121a24');
  x.fillStyle=g;x.fillRect(300,110,1320,620);
  // distant headlights smeared by rain
  for(let i=0;i<4;i++){
    const px=700+i*150+Math.sin(t*.5+i)*8, py=560+Math.abs(i-1.5)*26;
    const rg=x.createRadialGradient(px,py,2,px,py,60);
    rg.addColorStop(0,'rgba(214,214,196,.30)');rg.addColorStop(1,'rgba(214,214,196,0)');
    x.fillStyle=rg;x.fillRect(px-70,py-70,140,140);
  }
  // rain on the windshield
  x.strokeStyle='rgba(168,190,214,.22)';x.lineWidth=2;
  for(let i=0;i<46;i++){
    const rx=310+((i*211+t*40)%1300), ry=120+((i*97+t*120)%600);
    x.beginPath();x.moveTo(rx,ry);x.lineTo(rx-6,ry+30);x.stroke();
  }
  // A-pillars and roof
  x.fillStyle='#05070b';
  x.beginPath();x.moveTo(150,80);x.lineTo(340,110);x.lineTo(320,760);x.lineTo(120,900);x.closePath();x.fill();
  x.beginPath();x.moveTo(1770,80);x.lineTo(1580,110);x.lineTo(1600,760);x.lineTo(1800,900);x.closePath();x.fill();
  x.fillRect(280,60,1360,80);
  // passenger presence
  const sp={x:1450,y:standY(1010,.74),s:.74,face:-1,breath:t*1.1,coat:true,flut:.5,time:t,hat:false,
    look:kf(t,[[st,-.5],[en,-.9]]),brow:-.5,sad:-.7,mouth:-.45,blink:0};
  actor(x,'shad',SHAD,sp,cam,'rgba(90,110,128,.25)',-1);

  // dashboard (drawn over the passenger: seated, not standing at the glass)
  const dg=x.createLinearGradient(0,700,0,1080);
  dg.addColorStop(0,'#0b0f16');dg.addColorStop(1,'#05070b');
  x.fillStyle=dg;
  x.beginPath();x.moveTo(160,760);x.lineTo(1760,760);x.lineTo(1920,1080);x.lineTo(0,1080);x.closePath();x.fill();
  x.fillStyle='#070a10';x.fillRect(160,742,1600,26);
  // instrument glow
  const ig=x.createRadialGradient(960,880,20,960,880,300);
  ig.addColorStop(0,'rgba(120,190,176,.16)');ig.addColorStop(1,'rgba(120,190,176,0)');
  x.fillStyle=ig;x.fillRect(620,620,680,420);
  // steering wheel
  x.save();x.translate(960,900);x.rotate(Math.sin(t*.6)*.03);
  x.strokeStyle='#0a0d14';x.lineWidth=34;x.beginPath();x.arc(0,0,190,0,Math.PI*2);x.stroke();
  x.strokeStyle='rgba(70,80,92,.55)';x.lineWidth=4;x.beginPath();x.arc(0,0,176,0,Math.PI*2);x.stroke();
  x.strokeStyle='#0a0d14';x.lineWidth=26;
  x.beginPath();x.moveTo(-176,0);x.lineTo(-40,0);x.stroke();
  x.beginPath();x.moveTo(176,0);x.lineTo(40,0);x.stroke();
  x.beginPath();x.moveTo(0,40);x.lineTo(0,176);x.stroke();
  x.fillStyle='#0c1017';x.beginPath();x.arc(0,0,44,0,Math.PI*2);x.fill();
  x.restore();

  // ---- director variants: dashboard radio / paint ----
  if(variant==='radio'){
    // radio faceplate on the dash
    x.fillStyle='#06090e';x.beginPath();x.roundRect(1120,812,380,152,12);x.fill();
    x.strokeStyle='rgba(120,140,150,.22)';x.lineWidth=2;x.strokeRect(1136,826,348,124);
    const gy=x.createLinearGradient(0,838,0,910);
    gy.addColorStop(0,'#0a2018');gy.addColorStop(1,'#06120e');
    x.fillStyle=gy;x.fillRect(1150,838,228,72);
    // static scanlines
    for(let i=0;i<7;i++){
      const a=.05+.10*Math.abs(Math.sin(t*2.3+i*1.7));
      x.fillStyle=`rgba(140,220,190,${a})`;
      x.fillRect(1152,842+((i*11+t*30)%68),224,2);
    }
    x.fillStyle='rgba(150,235,200,.85)';x.font='bold 34px monospace';x.textAlign='left';
    x.fillText('103.7',1158,888);
    x.fillStyle='rgba(150,235,200,.5)';x.font='18px monospace';x.fillText('AM',1310,884);
    // knobs
    for(const kx of [1400,1440]){
      x.fillStyle='#0a0e14';x.beginPath();x.arc(kx,862,14,0,Math.PI*2);x.fill();
      x.strokeStyle='rgba(160,180,190,.35)';x.lineWidth=2;x.beginPath();x.arc(kx,862,14,0,Math.PI*2);x.stroke();
      x.beginPath();x.moveTo(kx,862);x.lineTo(kx,850);x.stroke();
    }
    x.fillStyle='rgba(150,235,200,.18)';x.fillRect(1390,890,80,6);
    const rg=x.createRadialGradient(1264,874,10,1264,874,220);
    rg.addColorStop(0,'rgba(130,220,185,.13)');rg.addColorStop(1,'rgba(130,220,185,0)');
    x.fillStyle=rg;x.fillRect(1040,760,470,260);
  }
    // hands on the wheel
    for(const side of [-1,1]){
      const hx=960+side*176, hy=902;
      x.save();x.translate(hx,hy);x.rotate(side*.16);
      x.fillStyle='#8a6a4f';x.beginPath();x.roundRect(-26,-20,52,46,18);x.fill();
      x.fillStyle='#6f543e';
      for(let i=0;i<4;i++){x.beginPath();x.roundRect(-20+i*11,-4,9,28,4);x.fill();}
      x.fillStyle='#5d4634';x.beginPath();x.roundRect(side>0?16:-32,-8,16,32,8);x.fill();
      x.restore();
    }
  if(variant==='paint'){
    // glossy black paint climbing the dash and curling round the wheel
    x.save();
    x.strokeStyle='rgba(7,8,10,.94)';x.lineCap='round';
    const tendrils=[[700,1080,760,880,1010,930,1120,760],[1520,1080,1470,860,1240,900,1160,752],
                    [980,1080,1010,940,900,860,860,760]];
    for(let i=0;i<tendrils.length;i++){
      const [x0,y0,x1,y1,x2,y2,x3,y3]=tendrils[i];
      x.lineWidth=46-i*8;
      x.beginPath();x.moveTo(x0,y0);x.bezierCurveTo(x1,y1,x2,y2,x3,y3);x.stroke();
      x.strokeStyle='rgba(150,160,175,.20)';x.lineWidth=4;
      x.beginPath();x.moveTo(x0-6,y0);x.bezierCurveTo(x1-8,y1,x2-8,y2,x3-6,y3);x.stroke();
      x.strokeStyle='rgba(7,8,10,.94)';
    }
    // paint swallowing the wheel rim
    x.strokeStyle='rgba(7,8,10,.96)';x.lineWidth=30;
    x.beginPath();x.arc(960,900,190,Math.PI*.98,Math.PI*1.62);x.stroke();
    x.strokeStyle='rgba(7,8,10,.9)';x.lineWidth=22;
    x.beginPath();x.arc(960,900,190,Math.PI*1.72,Math.PI*2.2);x.stroke();
    // wet highlights and drips
    x.strokeStyle='rgba(165,175,190,.28)';x.lineWidth=3;
    x.beginPath();x.moveTo(900,900);x.bezierCurveTo(940,880,980,872,1010,858);x.stroke();
    x.fillStyle='rgba(7,8,10,.95)';
    for(const [dx,dy,r] of [[880,842,16],[1050,806,12],[1180,792,10],[770,900,13]]){
      x.beginPath();x.ellipse(dx,dy,r,r*1.5,0,0,Math.PI*2);x.fill();
    }
    x.restore();
  }
  // rear-view mirror
  x.fillStyle='#05070b';x.beginPath();x.roundRect(820,66,300,110,18);x.fill();
  x.fillStyle='#101722';x.beginPath();x.roundRect(836,80,268,82,12);x.fill();
  x.fillStyle='rgba(120,140,160,.18)';x.fillRect(850,96,240,10);
}
function drawMirror(x,t,st,en,cam){
  // dim cabin around the mirror
  let g=x.createLinearGradient(0,0,0,1080);
  g.addColorStop(0,'#05070c');g.addColorStop(1,'#0a0e15');
  x.fillStyle=g;x.fillRect(-400,-300,2800,1700);
  // housing
  x.fillStyle='#04060a';x.beginPath();x.roundRect(430,190,1060,540,34);x.fill();
  x.strokeStyle='rgba(90,100,110,.35)';x.lineWidth=6;x.beginPath();x.roundRect(444,204,1032,512,28);x.stroke();
  // reflection: road receding, cold and wrong
  const rg=x.createLinearGradient(0,230,0,690);
  rg.addColorStop(0,'#0c1420');rg.addColorStop(.6,'#0e1826');rg.addColorStop(1,'#081018');
  x.fillStyle=rg;x.fillRect(466,226,988,468);
  x.fillStyle='rgba(150,160,150,.30)';
  for(let i=0;i<6;i++){const p=i/6,y=300+p*p*380,w=2+8*p*p;x.fillRect(960-w/2,y,w,26);}
  // reflecting figure on the back seat: silhouette only
  const sp={x:1240,y:standY(610,.92),s:.92,face:-1,breath:t*.9,coat:true,flut:.35,time:t,hat:true,
    look:kf(t,[[st,-.6],[en,-.95]]),brow:-.55,sad:-.8,mouth:-.5,blink:0};
  actor(x,'shad',SHAD,sp,cam,'rgba(120,140,160,.30)',-1);
  // glass cracks
  x.strokeStyle='rgba(210,220,230,.35)';x.lineWidth=2;
  for(let i=0;i<3;i++){
    const cx=700+i*260, cy=300+((i*97)%240);
    x.beginPath();x.moveTo(cx,cy);x.lineTo(cx+70,cy+90);x.lineTo(cx+30,cy+180);x.stroke();
  }
  // glass glare sweep
  const gg=x.createLinearGradient(520,240,1400,660);
  gg.addColorStop(0,'rgba(180,200,220,0)');gg.addColorStop(.45,'rgba(180,200,220,.08)');gg.addColorStop(1,'rgba(180,200,220,0)');
  x.fillStyle=gg;x.fillRect(466,226,988,468);
}
function roadScene(t,cam,s,u,kind){
  const st=stOf(s),en=enOf(s);
  let x=layer('sky',cam,.30);
  let g=x.createLinearGradient(0,-100,0,1080);
  g.addColorStop(0,'#04060b');g.addColorStop(.5,'#08101b');g.addColorStop(1,'#121a26');
  x.fillStyle=g;x.fillRect(-500,-400,2900,1800);
  g=x.createRadialGradient(1450,250,20,1450,250,460);
  g.addColorStop(0,'rgba(150,176,206,.14)');g.addColorStop(1,'rgba(150,176,206,0)');
  x.fillStyle=g;x.fillRect(900,-250,1200,950);

  x=layer('far',cam,.55);
  x.fillStyle='#060910';
  for(let i=0;i<28;i++){
    const bx=-260+i*104, h=30+((i*53)%70);
    x.beginPath();x.moveTo(bx,540);x.lineTo(bx+22,540-h);x.lineTo(bx+46,540);x.closePath();x.fill();
  }
  x=layer('set',cam,1);
  if(kind==='rearview_mirror')drawMirror(x,t,st,en,cam);
  else if(kind==='car_interior')drawCabin(x,t,st,en,cam,SCENES.shots[s].variant||'');
  else drawRoad(x,t,st,en,kind);

  x=layer('act',cam);
  if(kind==='highway'){
    // the road has no visible traveller: only the storm
  }
  x=layer('rain',cam,1.12);rainSheet(x,t,.58);
  x=layer('fg',cam,1.2);
  let v=x.createLinearGradient(0,900,0,1080);
  v.addColorStop(0,'rgba(3,5,9,0)');v.addColorStop(1,'rgba(3,5,9,.85)');
  x.fillStyle=v;x.fillRect(-500,880,3000,300);
  comp([['sky',cam.b[0]],['far',cam.b[1]],['set',0],['act',0],['rain',0,.55],['fg',cam.b[2]]]);
}


// ---------------- abandoned hallway / the other silhouette ----------------
function hallStick(x,cx,footY,h,opt){
  opt=opt||{};
  const col=opt.color||'#e9e6da', hr=h*.072, headY=footY-h+hr;
  x.save();
  if(opt.solid){x.shadowColor='rgba(222,216,198,.32)';x.shadowBlur=opt.rim||12;}
  if(opt.flatten){x.translate(cx,footY);x.scale(opt.flatten,1);x.translate(-cx,-footY);}
  x.strokeStyle=col;x.lineCap='round';x.lineJoin='round';x.lineWidth=Math.max(4,h*.03);
  const lean=opt.lean||0, shY=headY+hr+h*.03, hipY=footY-h*.44;
  x.beginPath();x.moveTo(cx,shY);x.lineTo(cx+lean*h*.10,hipY);x.stroke();
  x.beginPath();x.moveTo(cx+lean*h*.10,hipY);x.lineTo(cx-h*.10+ (opt.stride||0),footY);x.stroke();
  x.beginPath();x.moveTo(cx+lean*h*.10,hipY);x.lineTo(cx+h*.12-(opt.stride||0),footY);x.stroke();
  const armA=opt.armA===undefined?.5:opt.armA, armB=opt.armB===undefined?.5:opt.armB;
  x.beginPath();x.moveTo(cx,shY+h*.02);
  x.lineTo(cx-h*.20-armA*h*.08, shY+h*.26-armA*h*.10);x.stroke();
  x.beginPath();x.moveTo(cx,shY+h*.02);
  x.lineTo(cx+h*.20+armB*h*.08, shY+h*.26-armB*h*.10);x.stroke();
  x.beginPath();x.arc(cx+(opt.headX||0),headY+(opt.headY||0),hr,0,Math.PI*2);
  if(opt.solid){x.fillStyle=col;x.fill();}
  else{x.strokeStyle=col;x.lineWidth=Math.max(3,h*.020);x.stroke();}
  if(opt.eyes){
    x.fillStyle='rgba(238,244,255,.92)';
    x.beginPath();x.arc(cx+(opt.headX||0)-hr*.28,headY-hr*.05,hr*.10,0,Math.PI*2);x.fill();
    x.beginPath();x.arc(cx+(opt.headX||0)+hr*.28,headY-hr*.05,hr*.10,0,Math.PI*2);x.fill();
  }
  x.restore();
}
function hallFlash(x,cx,cy,dir,on){
  if(on<=0)return;
  x.save();
  x.strokeStyle='rgba(210,214,206,.55)';x.lineWidth=5;
  x.beginPath();x.moveTo(cx,cy);x.lineTo(cx+dir*26,cy-6);x.stroke();
  const g=x.createLinearGradient(cx,cy,cx+dir*620,cy+70);
  g.addColorStop(0,`rgba(246,240,214,${.20*on})`);g.addColorStop(1,'rgba(246,240,214,0)');
  x.fillStyle=g;x.beginPath();x.moveTo(cx+dir*16,cy-6);x.lineTo(cx+dir*680,cy-150);x.lineTo(cx+dir*680,cy+260);x.closePath();x.fill();
  x.fillStyle=`rgba(255,252,232,${.8*on})`;x.beginPath();x.arc(cx+dir*20,cy-8,6,0,Math.PI*2);x.fill();
  x.restore();
}
function hallwaySet(x,t,kind,lit){
  // wall and floor, high-contrast charcoal
  let g=x.createLinearGradient(0,0,0,700);
  g.addColorStop(0,'#0a0b0e');g.addColorStop(.52,'#15171b');g.addColorStop(1,'#07080a');
  x.fillStyle=g;x.fillRect(-400,-300,2800,980);
  // charcoal bloom and paper scars
  for(let i=0;i<90;i++){
    const a1=Math.sin(i*91.7)*43758.5453, a2=Math.sin(i*47.3)*24634.6345;
    const bx=(a1-Math.floor(a1))*1920, by=(a2-Math.floor(a2))*660;
    const r=12+((i*37)%70), al=.012+.028*Math.abs(Math.sin(i*1.7));
    x.fillStyle=`rgba(214,212,200,${al})`;x.beginPath();x.arc(bx,by,r,0,Math.PI*2);x.fill();
  }
  // peeling wallpaper strips
  for(let i=0;i<14;i++){
    const wx=-200+i*160, a=.03+.05*Math.sin(i*2.1);
    x.fillStyle=`rgba(210,205,190,${a})`;x.fillRect(wx,80,70+(i%3)*26,520);
    x.fillStyle='rgba(10,11,14,.35)';x.fillRect(wx+70,80,10,520);
  }
  // baseboard
  x.fillStyle='#080a0e';x.fillRect(-400,620,2800,46);
  x.fillStyle='rgba(190,185,170,.08)';x.fillRect(-400,618,2800,5);
  // floor
  g=x.createLinearGradient(0,660,0,1080);
  g.addColorStop(0,'#0a0b0d');g.addColorStop(.55,'#121316');g.addColorStop(1,'#060708');
  x.fillStyle=g;x.fillRect(-400,660,2800,460);
  x.strokeStyle='rgba(150,146,132,.10)';x.lineWidth=3;
  for(let i=0;i<10;i++){x.beginPath();x.moveTo(-300+i*240,660);x.lineTo(-700+i*340,1080);x.stroke();}
  // boarded window
  x.fillStyle='#05070b';x.fillRect(260,120,300,380);
  x.strokeStyle='rgba(150,148,140,.16)';x.lineWidth=10;x.strokeRect(260,120,300,380);
  for(let i=0;i<4;i++){
    x.save();x.translate(410,310+i*86);x.rotate(-.12+(i%2)*.18);
    x.fillStyle='#1c1b18';x.fillRect(-170,-18,340,36);
    x.fillStyle='rgba(210,205,190,.10)';x.fillRect(-170,-18,340,4);
    x.restore();
  }
  // moonlight shaft
  if(lit){
    const a=kind==='hallway_dark'?.05:.115;
    g=x.createLinearGradient(420,180,1000,980);
    g.addColorStop(0,`rgba(224,232,244,${a*1.6})`);g.addColorStop(.6,`rgba(214,226,240,${a})`);g.addColorStop(1,'rgba(214,226,240,0)');
    x.fillStyle=g;x.beginPath();x.moveTo(300,150);x.lineTo(560,150);x.lineTo(1240,1010);x.lineTo(760,1010);x.closePath();x.fill();
    // pool on the floor
    g=x.createRadialGradient(980,960,20,980,960,330);
    g.addColorStop(0,`rgba(220,230,242,${a*2.2})`);g.addColorStop(1,'rgba(220,230,242,0)');
    x.fillStyle=g;x.fillRect(600,720,900,360);
  }
  // dust motes in the beam
  for(let i=0;i<42;i++){
    const px=520+((i*137+t*9)%720), py=240+((i*89+t*16)%700);
    const a=.05+.12*Math.abs(Math.sin(t*.7+i));
    x.fillStyle=`rgba(226,232,240,${a})`;x.beginPath();x.arc(px,py,1.4+(i%3),0,Math.PI*2);x.fill();
  }
  // dark doorway at the end of the hall
  x.fillStyle='#030407';x.fillRect(1520,250,240,410);
  x.fillStyle='rgba(120,128,140,.10)';x.fillRect(1512,244,256,8);
}
function hallScene(t,cam,s,u,kind){
  const st=stOf(s),en=enOf(s);
  const lit = true;
  let x=layer('sky',cam,.12);
  x.fillStyle='#07080c';x.fillRect(-400,-300,2800,1700);
  x=layer('far',cam,.35);
  hallwaySet(x,t,kind,lit);
  x=layer('set',cam);
  // floor shadow patch and actors are drawn in act layer below
  x=layer('act',cam);
  if(kind==='hallway_moonlight'){
    // long wall shadow, Leo in the beam
    x.save();x.globalAlpha=.55;
    hallStick(x,1120,770,430,{color:'#000',solid:true,flatten:1.25,lean:.5,stride:.1,armA:.2,armB:.2});
    x.restore();
    const walk=kf(t,[[st,-.10],[en,.10]]);
    hallStick(x,760+u*40,940,420,{lean:.55,stride:walk,armA:.2,armB:.6,headX:4});
    hallFlash(x,700+u*40,700,.55,.6+.25*Math.sin(t*9));
  }
  if(kind==='shadow_detach'){
    const turn=kf(t,[[st,.0],[st+1.2,.9],[en,.9]]);
    hallStick(x,700,940,420,{lean:.35+turn*.45,stride:.25,armA:.35,armB:.45,headX:turn*6});
    hallFlash(x,760,706,.6,.55);
    // shadow on the wall lags, then its head snaps back at 60% of the shot
    const lag=u<.62?1:0;
    x.save();x.globalAlpha=.9;
    hallStick(x,1080,790,470,{color:'#000',solid:true,flatten:1.18,lean:.2,stride:.06,
      armA:.2+lag*.5,armB:.2+lag*.35,headX:lag*46,headY:lag*6});
    x.restore();
  }
  const n=s+1;
  if(kind==='shadow_rise'){
    // flashlight dies, Leo backs to the wall, the flat shadow stands up
    hallStick(x,1210,950,420,{lean:-.32,stride:.05,armA:.45,armB:.65,headX:-4});
    hallFlash(x,1150,712,-.55,Math.max(0,.8*(1-u/.32)));
    x.fillStyle='rgba(214,226,242,.09)';
    x.beginPath();x.moveTo(640,150);x.lineTo(940,150);x.lineTo(1300,980);x.lineTo(760,980);x.closePath();x.fill();
    const rise=Math.min(1,Math.max(0,(u-.26)/.55));
    if(rise<=0.02){
      x.save();x.translate(860,965);x.scale(1.6,.24);
      hallStick(x,0,0,440,{color:'#000',solid:true,lean:.1,stride:.4,armA:.4,armB:.3});
      x.restore();
    }else{
      x.save();x.globalAlpha=.6+.4*rise;
      x.translate(880,970);x.scale(1,.30+.70*rise);x.translate(-880,-970);
      hallStick(x,880,970,450,{color:'#000',solid:true,lean:-.05,stride:.25,armA:.2+rise*.5,armB:.2+rise*.4});
      x.restore();
    }
  }
  if(kind==='shadow_twist'){
    x.fillStyle='rgba(214,226,242,.10)';
    x.beginPath();x.moveTo(640,150);x.lineTo(930,150);x.lineTo(1290,980);x.lineTo(750,980);x.closePath();x.fill();
    hallStick(x,760,950,430,{lean:0,stride:.05,armA:.3,armB:.3,eyes:true});
    hallFlash(x,720,712,.45,.2);
    x.fillStyle='rgba(228,236,250,.16)';
    x.beginPath();x.ellipse(1080,962,340,64,0,0,Math.PI*2);x.fill();
    x.save();x.globalAlpha=.92;x.translate(1080,986);x.scale(1.8,.20);
    const claw=.25+.75*Math.abs(Math.sin(t*7));
    hallStick(x,0,0,440,{color:'#000',solid:true,lean:.15,stride:.3,armA:claw,armB:1.0,headX:8});
    x.restore();
    // hard cut to black
    const cut=seg(u,.90,1); if(cut>0){x.fillStyle=`rgba(0,0,0,${cut})`;x.fillRect(-400,-300,2800,1700);}
  }
  if(kind==='shadow_merge'){
    // moon pool from a cracked ceiling
    x.fillStyle='rgba(210,224,240,.10)';
    x.beginPath();x.moveTo(620,140);x.lineTo(930,140);x.lineTo(1280,980);x.lineTo(740,980);x.closePath();x.fill();
    if(n===10){
      // flat shadow lying in front of Leo, wrong way round
      x.save();x.globalAlpha=.85;x.translate(860,950);x.scale(1.7,.26);
      hallStick(x,0,0,440,{color:'#000',solid:true,lean:.1,stride:.45,armA:.4,armB:.2});
      x.restore();
      hallStick(x,1240,950,420,{lean:-.3,stride:.1,armA:.55,armB:.7,headX:-4});
      hallFlash(x,1180,712,-.6,.35);
    }else if(n===11){
      // it peels up off the boards, full height by the end of the beat
      const rise=Math.min(1,Math.max(0,(u-.10)/.80));
      x.save();x.globalAlpha=.55+.35*rise;
      x.translate(880,960);x.scale(1,.35+.65*rise);x.translate(-880,-960);
      hallStick(x,880,960,440,{color:'#000',solid:true,lean:-.05,stride:.3,armA:.2+rise*.5,armB:.2+rise*.45});
      x.restore();
      hallStick(x,1260,950,420,{lean:-.2,stride:.1,armA:.5,armB:.6,headX:-3});
    }else if(n===12){
      // eyeless figure inches from him; Leo shields his face
      hallStick(x,860,960,450,{color:'#000',solid:true,lean:.15,stride:.2,armA:.65,armB:.55});
      hallStick(x,1160,950,420,{lean:.35,stride:.05,armA:1.1,armB:1.1,headX:6});
      x.save();x.globalAlpha=.9;x.fillStyle='rgba(0,0,0,.55)';
      x.beginPath();x.ellipse(1010,650,120,170,0,0,Math.PI*2);x.fill();x.restore();
    }else{
      // n===13: the merge, then Leo alone and whole
      if(u<.42){
        const k=u/.42;
        hallStick(x,860+160*k,960,450,{color:'#000',solid:true,lean:.1,stride:.2,armA:.6,armB:.55});
        hallStick(x,1160-140*k,950,420,{lean:.1,stride:.05,armA:.7,armB:.7,headX:4});
      }else if(u<.62){
        // black impact: two silhouettes occupying the same space
        x.save();x.globalAlpha=.92;x.fillStyle='#000';
        x.beginPath();x.ellipse(1040,700,190,280,0,0,Math.PI*2);x.fill();x.restore();
        hallStick(x,1040,950,430,{color:'#000',solid:true,lean:.05,stride:.1,armA:.8,armB:.8});
      }else{
        hallStick(x,1080,950,420,{lean:.05,stride:.1,armA:.55,armB:.5});
      }
    }
  }
  if(kind==='hallway_dark'){
    const isFinal = n===14;
    if(!isFinal){
      const dying = u>.55?.22:.8;
      hallStick(x,900+u*40,950,420,{lean:.2,stride:.1,armA:.2,armB:.7,headX:2});
      hallFlash(x,840,712,.65,dying*(.75+.2*Math.sin(t*13)));
    }else{
      // the twist: white pinprick eyes on Leo, flat copy clawing in the beam
      hallStick(x,780,950,430,{lean:0,stride:.05,armA:.3,armB:.3,eyes:true});
      hallFlash(x,720,712,.55,.25);
      x.fillStyle='rgba(228,236,250,.16)';
      x.beginPath();x.ellipse(1050,960,340,64,0,0,Math.PI*2);x.fill();
      x.save();x.globalAlpha=.92;x.translate(1050,985);x.scale(1.8,.20);
      const claw=.25+.75*Math.abs(Math.sin(t*7));
      hallStick(x,0,0,440,{color:'#000',solid:true,lean:.15,stride:.3,armA:claw,armB:1.0,headX:8});
      x.restore();
    }
    const vg=x.createRadialGradient(960,600,100,960,600,1050);
    vg.addColorStop(0,'rgba(0,0,0,0)');vg.addColorStop(1,'rgba(0,0,0,.62)');
    x.fillStyle=vg;x.fillRect(-400,-300,2800,1700);
  }
  x=layer('fg',cam,1.12);
  x.fillStyle=`rgba(200,215,235,${.034+.028*Math.sin(t*2.4)+.008*Math.sin(t*8.1)})`;
  x.fillRect(-400,-300,2800,1700);
  const fx=((t*24)%2600)-400;
  const fg2=x.createRadialGradient(fx,500,40,fx,500,700);
  fg2.addColorStop(0,'rgba(190,205,225,.05)');fg2.addColorStop(1,'rgba(190,205,225,0)');
  x.fillStyle=fg2;x.fillRect(-400,-300,2800,1700);
  const fr=Math.floor(t*30);
  for(let i=0;i<170;i++){
    const a=Math.sin(i*127.1+fr*311.7)*43758.5453, b=Math.sin(i*269.5+fr*183.3)*43758.5453;
    const rx=(a-Math.floor(a))*1920, ry=(b-Math.floor(b))*1080;
    x.fillStyle=`rgba(228,236,250,${.03+.05*Math.abs(Math.sin(i+fr*.7))})`;
    x.fillRect(rx,ry,2,2);
  }
  const v=x.createLinearGradient(0,0,0,1080);
  v.addColorStop(0,'rgba(0,0,0,.55)');v.addColorStop(.45,'rgba(0,0,0,0)');v.addColorStop(1,'rgba(0,0,0,.65)');
  x.fillStyle=v;x.fillRect(-400,-300,2800,1700);
  x.fillStyle='#000';x.fillRect(-400,-300,2800,356);x.fillRect(-400,1024,2800,356);
  comp([['sky',cam.b[0]],['far',cam.b[1]],['set',0],['act',0],['fg',cam.b[2]]]);
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
  end:{x:1220,y:548,z:.78,push:.04,dx:50,dy:-3,b:[3,.8,0]},
  highway:{x:960,y:548,z:.86,push:.07,dx:0,dy:-2,b:[3,1.0,0]},
  car_interior:{x:960,y:560,z:1.04,push:.05,dx:0,dy:0,b:[4,0,0]},
  rearview_mirror:{x:960,y:520,z:1.30,push:.10,dx:0,dy:0,b:[4,0,0]},
  roadside_sign:{x:1200,y:540,z:.94,push:.06,dx:26,dy:-2,b:[3,1.0,0]},
  hallway_moonlight:{x:1000,y:560,z:1.00,push:.05,dx:14,dy:-2,b:[3,1,0]},
  shadow_detach:{x:980,y:560,z:1.10,push:.07,dx:8,dy:-1,b:[3,1,0]},
  shadow_merge:{x:1000,y:580,z:1.02,push:.08,dx:4,dy:-2,b:[3,1,0]},
  hallway_dark:{x:980,y:560,z:1.14,push:.06,dx:10,dy:-2,b:[3,1,0]},
  shadow_rise:{x:1000,y:560,z:1.04,push:.06,dx:8,dy:-2,b:[3,1,0]},
  shadow_twist:{x:1000,y:560,z:1.02,push:.06,dx:6,dy:-2,b:[3,1,0]}
};

const INT_KINDS=new Set(['opening','console','radio_insert','speaks','hand','final']);
const ROAD_KINDS=new Set(['highway','car_interior','rearview_mirror','roadside_sign']);
const HALL_KINDS=new Set(['hallway_moonlight','shadow_detach','shadow_merge','hallway_dark','shadow_rise','shadow_twist']);

FILM={dur:SCENES.dur,cuts:SCENES.cuts,fadeIn:.7,fadeOut:.9,
  cam(s,u,t){
    const k=SCENES.shots[s].kind,c=CAMS[k]||CAMS.console;
    let x=c.x+(c.dx||0)*u,y=c.y+(c.dy||0)*u,z=c.z*(1+(c.push||0)*u);
    if(k==='storm'){x+=Math.sin(t*1.6)*2.4;y+=Math.cos(t*1.25)*1.7}
    if(k.indexOf('hallway_')===0||k.indexOf('shadow_')===0){x+=Math.sin(t*1.3)*6;y+=Math.cos(t*1.55)*4}
    return {x,y,z,b:c.b};
  },
  draw(t,cam,s,u){
    const k=SCENES.shots[s].kind;
    if(HALL_KINDS.has(k))hallScene(t,cam,s,u,k);
    else if(ROAD_KINDS.has(k))roadScene(t,cam,s,u,k);
    else if(INT_KINDS.has(k))interior(t,cam,s,u,k);else exterior(t,cam,s,u,k);
    for(const c of (SCENES.captions||[])){
      if(t<c.t0||t>c.t1)continue;
      const a=Math.min(1,Math.min((t-c.t0)/.18,(c.t1-t)/.18));
      ctx.save();ctx.globalAlpha=Math.max(0,a);
      ctx.font='600 46px "Helvetica Neue", Arial, sans-serif';ctx.textAlign='center';
      ctx.lineJoin='round';ctx.lineWidth=9;ctx.strokeStyle='rgba(6,7,9,.92)';
      ctx.strokeText(c.text,960,958);
      ctx.fillStyle='#f4ecd8';ctx.fillText(c.text,960,958);
      ctx.restore();
    }
  },
  warm(t){return .04},
  plants(){return {}}
};

for(const e of (SCENES.events||[]))say(e.t,e.k);
