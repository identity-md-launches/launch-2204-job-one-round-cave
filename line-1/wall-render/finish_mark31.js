'use strict';
// Transfer only generated earth-pigment masks onto previously unpainted rock.
const fs=require('node:fs'), crypto=require('node:crypto');
const {decodePNG,encodePNG,preview}=require('./finish_wall.js');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const original=fs.readFileSync('artifacts/line-1/wall.png');
const previous=JSON.parse(fs.readFileSync('dist/line-1/30.json','utf8'));
if(previous.image!=='https://api.imd.fun/artifacts/'+hash(original)) throw Error('ancestor digest mismatch');
const ancestor=decodePNG('artifacts/line-1/wall.png');
const donor=decodePNG('artifacts/line-1/wall-v13.png');
const result={...ancestor,pixels:Buffer.from(ancestor.pixels)};
if(ancestor.width!==1254||ancestor.height!==1254||donor.width!==1024||donor.height!==1024) throw Error('unexpected dimensions');
// Crop excludes both unsolicited donor frogs. Ancestral Pepes remain untouched.
const bounds=[320,205,470,320], source=[120,240,830,820];
for(let y=bounds[1];y<bounds[3];y++) for(let x=bounds[0];x<bounds[2];x++) {
  const coverage={black:0,red:0,ochre:0};
  for(const dy of [.125,.375,.625,.875]) for(const dx of [.125,.375,.625,.875]) {
    const sx=Math.floor(source[0]+(x-bounds[0]+dx)/(bounds[2]-bounds[0])*(source[2]-source[0]));
    const sy=Math.floor(source[1]+(y-bounds[1]+dy)/(bounds[3]-bounds[1])*(source[3]-source[1]));
    const at=(sy*donor.width+sx)*donor.channels;
    const [r,g,b]=donor.pixels.subarray(at,at+3);
    if(Math.max(r,g,b)<105) coverage.black+=1/16;
    else if(r>g*1.45 && r>b*1.75 && g<140) coverage.red+=1/16;
    else if(r>g*1.18 && g>b*1.6 && r>120) coverage.ochre+=1/16;
  }
  const at=(y*result.width+x)*result.channels;
  const grain=.65+.35*ancestor.pixels[at]/255;
  for(const [kind,color,strength] of [['black',[39,29,18],.86],['red',[136,53,24],.84],['ochre',[174,114,30],.8]]) {
    const alpha=coverage[kind]*strength*grain;
    for(let c=0;c<3;c++) result.pixels[at+c]=Math.round(result.pixels[at+c]*(1-alpha)+color[c]*alpha);
  }
}
let changed=0, outside=true;
for(let y=0;y<result.height;y++) for(let x=0;x<result.width;x++) {
  const at=(y*result.width+x)*result.channels;
  if(!result.pixels.subarray(at,at+result.channels).equals(ancestor.pixels.subarray(at,at+ancestor.channels))) {
    changed++;
    if(!(x>=bounds[0]&&x<bounds[2]&&y>=bounds[1]&&y<bounds[3])) outside=false;
  }
}
if(!outside||changed<100) throw Error('failed preservation/empty mark');
const png=encodePNG(result), jpg=preview(result);
if(jpg.length>100000) throw Error('preview exceeds 100 KB');
fs.writeFileSync('artifacts/line-1/wall-v13.png',png);
fs.writeFileSync('artifacts/line-1/wall.png',png);
fs.writeFileSync('dist/line-1/31.jpg',jpg);
const report={bounds,source,changed_pixels:changed,all_pixels_outside_identical:outside,
  ancestor_sha256:hash(original),wall_sha256:hash(png),width:result.width,height:result.height,
  format:'PNG RGB8',png_bytes:png.length,preview:{width:512,height:512,format:'JPEG',bytes:jpg.length},
  generator:'installed mcp image generate; only earth pigment masks transferred',
  donor_note:'Unsolicited green donor frogs and all donor background were excluded. No donor hand or foot was transferred.'};
fs.writeFileSync('line-1/mark-process-31.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));
