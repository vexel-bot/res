export const hologramVertexShader = `
precision highp float;
attribute vec3 aPosition;
attribute float aSeed;
attribute float aSize;
attribute vec3 aOffset;
uniform float uTime;
uniform float uPixelRatio;
uniform float uAspect;
uniform vec3 uVoice;
uniform vec2 uSpectrum;
varying float vOpacity;
varying float vFront;
varying float vPulse;
void main() {
  vec3 p = aPosition;
  float longitude = atan(p.z, p.x);
  float radius = length(p);
  float equator = 1.0 - p.y * p.y;
  float wave = .014 * sin(longitude * 3.0 + p.y * 8.0 - uTime * .5)
    + .007 * sin(longitude * 5.0 - uTime * .31 + aSeed * 3.0);
  float listenWave = sin((1.0 - abs(p.y)) * 19.0 - uTime * (2.2 + uSpectrum.x)) * uVoice.x * (.003 + uVoice.z * .022);
  float vibration = sin(uTime * 113.097 + aSeed * 6.283) * uVoice.x * uVoice.z * .0018 * (.4 + uSpectrum.y);
  float speaking = uVoice.y * uVoice.z;
  float resonantWave = wave * (1.0 - .35 * speaking) + sin(radius * 12.0 - uTime * 4.3 + longitude * 2.0) * speaking * .00735 * equator;
  float breath = 1.0 + .03 * sin(uTime * 1.4);
  p.xz *= breath + resonantWave * (1.0 + .4 * speaking) + listenWave + vibration;
  p.y = p.y * breath + (.016 * sin(longitude * 2.0 + uTime * .27 + p.y * 5.0) + listenWave * .3) * equator;
  float angle = uTime * .025 + .03 * sin(uTime * .17);
  p = vec3(cos(angle)*p.x + sin(angle)*p.z, p.y, -sin(angle)*p.x + cos(angle)*p.z);
  float tilt = -.14 + .055 * sin(uTime * .23);
  p = vec3(p.x, cos(tilt)*p.y - sin(tilt)*p.z, sin(tilt)*p.y + cos(tilt)*p.z);
  float roll = .04 * sin(uTime * .19);
  p.xy = vec2(cos(roll)*p.x - sin(roll)*p.y, sin(roll)*p.x + cos(roll)*p.y);
  // CPU spring displacement is relative to this continuously updated rest pose.
  p += aOffset;
  float perspective = 2.65 / (3.7 - p.z);
  gl_Position = vec4(p.x * perspective / uAspect, p.y * perspective, 0.0, 1.0);
  vFront = clamp((p.z + 1.1) / 2.2, 0.0, 1.0);
  gl_PointSize = clamp(aSize * (.85 + .15 * vFront) + uVoice.y * uVoice.z * .14, .6, 1.4 + uVoice.y * uVoice.z * .1) * uPixelRatio;
  vOpacity = mix(.20 + .15 * aSeed, .85 + .13 * aSeed, smoothstep(-.2, .7, p.z));
  vPulse = .985 + .015 * sin(uTime * 1.4 - radius * 4.0) + .02 * uVoice.z;
}`;

export const hologramFragmentShader = `
precision mediump float;
uniform vec3 uColor;
uniform float uShade;
uniform float uOpacity;
uniform float uGlow;
varying float vOpacity;
varying float vFront;
varying float vPulse;
void main() {
  float distance = length(gl_PointCoord - vec2(.5)) * 2.0;
  if (distance > 1.0) discard;
  float core = 1.0 - smoothstep(.72, 1.0, distance);
  float halo = exp(-distance * distance * 4.0) * uGlow;
  vec3 rear = vec3(45.0, 115.0, 195.0) / 255.0;
  vec3 sky = mix(vec3(165.0, 215.0, 255.0), vec3(180.0, 225.0, 255.0), vFront) / 255.0;
  vec3 color = mix(rear, uColor, smoothstep(.05, .55, vFront));
  color = mix(color, sky, smoothstep(.65, 1.0, vFront) * .78);
  gl_FragColor = vec4(min(vec3(1.0), color * uShade * vPulse), min(.98, vOpacity * uOpacity * (core + halo)));
}`;
