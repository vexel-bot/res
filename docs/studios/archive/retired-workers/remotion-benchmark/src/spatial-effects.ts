/** Existing canonical spatial fields; never accept a caller-supplied CSS filter. */
export type EditorialShadow = {x:number; y:number; blur:number; color:string; opacity:number};

export const spatialFilter = (blur:number, shadow:EditorialShadow|null|undefined, target:string):string|undefined => {
  if (!Number.isFinite(blur) || blur < 0 || blur > 500) {
    throw new Error(`hybrid_spatial_blur_invalid:target=${target}`);
  }
  const filters:string[] = blur === 0 ? [] : [`blur(${blur}px)`];
  if (shadow !== undefined && shadow !== null) {
    if (typeof shadow !== 'object' || Array.isArray(shadow) ||
        Object.keys(shadow).some(key => !['x','y','blur','color','opacity'].includes(key)) ||
        !Number.isFinite(shadow.x) || Math.abs(shadow.x) > 100 ||
        !Number.isFinite(shadow.y) || Math.abs(shadow.y) > 100 ||
        !Number.isFinite(shadow.blur) || shadow.blur < 0 || shadow.blur > 100 ||
        !Number.isFinite(shadow.opacity) || shadow.opacity < 0 || shadow.opacity > 1 ||
        typeof shadow.color !== 'string' || !/^#[0-9a-fA-F]{6}$/.test(shadow.color)) {
      throw new Error(`hybrid_spatial_shadow_invalid:target=${target}`);
    }
    if (shadow.opacity !== 0) {
      const color = [1,3,5].map(index => Number.parseInt(shadow.color.slice(index,index+2),16));
      filters.push(`drop-shadow(${shadow.x}px ${shadow.y}px ${shadow.blur}px rgba(${color.join(',')},${shadow.opacity}))`);
    }
  }
  return filters.length ? filters.join(' ') : undefined;
};
