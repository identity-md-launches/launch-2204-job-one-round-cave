// Preserve every ancestral pixel except pigment from the generated new motif.
// Node built-ins only; reads/writes only the explicitly named workspace images.
const fs = require('fs');
const zlib = require('zlib');
const crypto = require('crypto');
function decode(data) {
  let pos=8, idat=[], width,height;
  while(pos<data.length){let n=data.readUInt32BE(pos), kind=data.toString('ascii',pos+4,pos+8), p=data.subarray(pos+8,pos+8+n);
    if(kind==='IHDR'){width=p.readUInt32BE(0);height=p.readUInt32BE(4);if(p[8]!==8||p[9]!==2||p[12]!==0)throw Error('RGB8 noninterlaced required');}
    if(kind==='IDAT')idat.push(p);pos+=n+12;}
  let raw=zlib.inflateSync(Buffer.concat(idat)), stride=width*3, pixels=Buffer.alloc(width*height*3);
  if(raw.length!==(stride+1)*height)throw Error('scanline size');
  for(let y=0;y<height;y++){let mode=raw[y*(stride+1)];for(let x=0;x<stride;x++){
    let k=y*stride+x,a=x>=3?pixels[k-3]:0,b=y?pixels[k-stride]:0,c=y&&x>=3?pixels[k-stride-3]:0,p=0;
    if(mode===1)p=a;else if(mode===2)p=b;else if(mode===3)p=Math.floor((a+b)/2);else if(mode===4){let v=a+b-c, da=Math.abs(v-a),db=Math.abs(v-b),dc=Math.abs(v-c);p=da<=db&&da<=dc?a:db<=dc?b:c;}else if(mode!==0)throw Error('filter');
    pixels[k]=(raw[y*(stride+1)+1+x]+p)&255;}}
  return {width,height,pixels};
}
function crc(data){let c=0xffffffff;for(let b of data){c^=b;for(let j=0;j<8;j++)c=(c>>>1)^((c&1)?0xedb88320:0);}return (c^0xffffffff)>>>0;}
function chunk(name,data){let kind=Buffer.from(name),out=Buffer.alloc(data.length+12);out.writeUInt32BE(data.length,0);kind.copy(out,4);data.copy(out,8);out.writeUInt32BE(crc(Buffer.concat([kind,data])),data.length+8);return out;}
function encode(img){let header=Buffer.alloc(13);header.writeUInt32BE(img.width,0);header.writeUInt32BE(img.height,4);header[8]=8;header[9]=2;
 let stride=img.width*3,raw=Buffer.alloc((stride+1)*img.height);for(let y=0;y<img.height;y++)img.pixels.copy(raw,y*(stride+1)+1,y*stride,(y+1)*stride);
 return Buffer.concat([Buffer.from('89504e470d0a1a0a','hex'),chunk('IHDR',header),chunk('IDAT',zlib.deflateSync(raw)),chunk('IEND',Buffer.alloc(0))]);}
const ancestor='artifacts/gathering/wall-v12.png', target='artifacts/gathering/wall-v13.png';
const before=fs.readFileSync(ancestor), donor=fs.readFileSync(target), a=decode(before), d=decode(donor);
if(crypto.createHash('sha256').update(donor).digest('hex')!=='d39bf8012341bf471337b298cc525e68f39d1f34e41e8474ce4dff5af50c5dfa')throw Error('Requires the original generated donor at the target path; refusing to repaint a finished wall.');
if(crypto.createHash('sha256').update(before).digest('hex')!=='d23d6bfc85792e4379a85c704705900c359e512d2b2f5efbeda287e014e665c6')throw Error('Ancestor mismatch');
const box=[692,1136,804,1218], crop=[260,340,712,668];
let changed=0;
for(let y=box[1];y<box[3];y++)for(let x=box[0];x<box[2];x++){
 const sx=Math.floor(crop[0]+(x-box[0])*(crop[2]-crop[0])/(box[2]-box[0]));
 const sy=Math.floor(crop[1]+(y-box[1])*(crop[3]-crop[1])/(box[3]-box[1]));
 const k=(y*a.width+x)*3,j=(sy*d.width+sx)*3;
 const r=d.pixels[j],g=d.pixels[j+1],b=d.pixels[j+2];
 if(Math.max(r,g,b)<100)continue;
 // Keep generated pigment's broken edges. Reduce saturation to earth pigment
 // and let the original rock texture remain visible through the new pigment.
 let pigment;
 if(r>150&&g>150&&b>130)pigment=[214,187,144];
 else if(r>g*1.45)pigment=[159,65,30];
 else if(r>130&&g>95&&b<100)pigment=[183,121,42];
 else continue;
 const alpha=.66;
 for(let c=0;c<3;c++)a.pixels[k+c]=Math.round(a.pixels[k+c]*(1-alpha)+pigment[c]*alpha);
 changed++;
}
if(changed<300)throw Error('missing generated pigment');
fs.writeFileSync(target,encode(a));
fs.writeFileSync('gathering/mark-process13.json',JSON.stringify({method:'Generated isolated chalk arcs and ochre dots; transferred only their pigment onto bare lower foreground, leaving ancestral pixels elsewhere exact.',image_tool:'mcp__image__generate_image',ancestor,ancestor_sha256:crypto.createHash('sha256').update(before).digest('hex'),generated_donor_sha256:crypto.createHash('sha256').update(donor).digest('hex'),donor_dimensions:[d.width,d.height],destination_box:box,donor_crop:crop,changed_pixels:changed,preservation:'Every decoded pixel outside the added pigment mask is identical to Gathering 12.'},null,2)+'\n');
console.log({width:a.width,height:a.height,changed});
