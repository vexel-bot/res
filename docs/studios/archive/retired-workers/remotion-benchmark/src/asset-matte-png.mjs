// Bound decoded allocation before bundling or opening Chromium. Full PNG
// decoding remains the browser's responsibility. Check dimensions and the
// pre-IDAT chunk sequence; animated PNG is not a static matte input.
export function validateMattePngHeader(bytes,mime,previousPixels=0){
  if(mime!=='image/png'||bytes.length<33||!bytes.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10]))||
    bytes.readUInt32BE(8)!==13||bytes.toString('ascii',12,16)!=='IHDR'){
    throw new Error('hybrid_asset_matte_png_required');
  }
  const width=bytes.readUInt32BE(16),height=bytes.readUInt32BE(20),pixels=width*height;
  const totalPixels=previousPixels+pixels;
  if(!Number.isSafeInteger(previousPixels)||previousPixels<0||width<1||height<1||pixels>16777216||totalPixels>33554432){
    throw new Error('hybrid_asset_matte_decode_pixel_limit');
  }
  let offset=33;
  while(offset<bytes.length){
    if(offset+12>bytes.length)throw new Error('hybrid_asset_matte_png_required');
    const length=bytes.readUInt32BE(offset),type=bytes.toString('ascii',offset+4,offset+8);
    if(type==='acTL')throw new Error('hybrid_asset_matte_animated_png_pending');
    if(type==='IDAT'||type==='IEND')break;
    const end=offset+12+length;
    if(end>bytes.length)throw new Error('hybrid_asset_matte_png_required');
    offset=end;
  }
  return {width,height,pixels,totalPixels};
}
