// Technical fixture, not an advertisement. Throws on unsupported configuration.
var c=app.project.activeItem;
while(c.numLayers)c.layer(1).remove();
c.duration=1;c.frameRate=30;c.width=640;c.height=640;
var bg=c.layers.addSolid([0.15,0.16,0.20],"proof-background",640,640,1,1);
function circle(name,x,y,col){
 var l=c.layers.addShape();l.name=name;
 var v=l.property("ADBE Root Vectors Group");
 var g=v.addProperty("ADBE Vector Group").property("ADBE Vectors Group");
 g.addProperty("ADBE Vector Shape - Ellipse").property("ADBE Vector Ellipse Size").setValue([70,70]);
 g.addProperty("ADBE Vector Graphic - Fill").property("ADBE Vector Fill Color").setValue(col);
 l.property("ADBE Transform Group").property("ADBE Position").setValue([x,y]);return l;
}
var a=circle("linear",100,180,[1,0.4,0.25]),b=circle("bezier",100,300,[0.6,0.5,1]);
function move(l,ease){var p=l.property("ADBE Transform Group").property("ADBE Position");
 var y=p.value[1];p.setValueAtTime(0,[100,y,0]);p.setValueAtTime(1,[540,y,0]);
 p.setSpatialAutoBezierAtKey(1,false);p.setSpatialAutoBezierAtKey(2,false);
 p.setSpatialTangentsAtKey(1,[0,0,0],[0,0,0]);p.setSpatialTangentsAtKey(2,[0,0,0],[0,0,0]);
 if(ease){p.setInterpolationTypeAtKey(1,KeyframeInterpolationType.BEZIER,KeyframeInterpolationType.BEZIER);
 p.setInterpolationTypeAtKey(2,KeyframeInterpolationType.BEZIER,KeyframeInterpolationType.BEZIER);
 p.setTemporalEaseAtKey(1,[new KeyframeEase(0,70)],[new KeyframeEase(0,70)]);
 p.setTemporalEaseAtKey(2,[new KeyframeEase(0,70)],[new KeyframeEase(0,70)]);}
}
move(a,false);move(b,true);
var line=c.layers.addShape();line.name="cubic-stroke";
line.property("ADBE Transform Group").property("ADBE Position").setValue([0,0]);
var v=line.property("ADBE Root Vectors Group");var g=v.addProperty("ADBE Vector Group").property("ADBE Vectors Group");
var s=new Shape();s.vertices=[[100,480],[540,480]];s.inTangents=[[0,0],[-130,100]];s.outTangents=[[130,-100],[0,0]];s.closed=false;
g.addProperty("ADBE Vector Shape - Group").property("ADBE Vector Shape").setValue(s);
var st=g.addProperty("ADBE Vector Graphic - Stroke");st.property("ADBE Vector Stroke Color").setValue([0.7,1,0.3]);
st.property("ADBE Vector Stroke Width").setValue(14);st.property("ADBE Vector Stroke Line Cap").setValue(2);
JSON.stringify({fixture:"native-motion-proof-v1",duration:c.duration,fps:c.frameRate,scope:"Curve, stroke, spatial/temporal interpolation; no claim of lighting, 3D or audio qualification"});
