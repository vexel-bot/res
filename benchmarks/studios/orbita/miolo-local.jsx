var c = app.project.activeItem;
function layer(prefix) {
    for(var i=1;i<=c.numLayers;i++) if(c.layer(i).name.indexOf(prefix)===0) return c.layer(i);
    throw new Error("Missing layer "+prefix);
}
function transform(l,n) {return l.property("ADBE Transform Group").property(n);}
function place(l,a,b) {l.startTime=a;l.inPoint=a;l.outPoint=b;}
var encontro=c.layer(1), detalhe=c.layer(2), travessia=c.layer(3);
var gate=layer("Gate");
var names=["Travessia","Detalhe da máquina","Encontro"];
var takes=[travessia,detalhe,encontro], cuts=[5,7.2,8.6,11];
for(var j=0;j<3;j++){
    var l=takes[j]; l.name="Miolo · "+names[j];place(l,cuts[j],cuts[j+1]);
    transform(l,"ADBE Position").setValue([540,960]);
    transform(l,"ADBE Scale").setValue([200,200]);
    l.moveAfter(gate);
}
layer("6beec2ee").remove();
layer("1c8562d2").remove();
layer("5f32f89d").remove();
var plate=c.layers.addSolid([0.024,0.026,0.044],"Miolo · base da categoria",790,90,1,18);
place(plate,5.18,7.2);transform(plate,"ADBE Position").setValue([540,218]);
transform(plate,"ADBE Opacity").setValue(89);
var caption=c.layers.addText("Mostra de curtas de ficção científica");
var p=caption.property("ADBE Text Properties").property("ADBE Text Document"), d=p.value;
d.font="Space Grotesk"; d.fontSize=42; d.fillColor=[.94,.91,.85];
d.justification=ParagraphJustification.CENTER_JUSTIFY; p.setValue(d);
place(caption,5.18,7.2); transform(caption,"ADBE Position").setValue([540,234]);
var opacity=transform(caption,"ADBE Opacity");opacity.setValueAtTime(5.18,0);opacity.setValueAtTime(5.4,100);
// Shift the two internal accents only. The entrance, the pullback and the outro keep their audio.
for(var i=1;i<=c.numLayers;i++){
    var a=c.layer(i);
    if(a.name.indexOf("9ec88053")!==0) continue;
    var newTime=null;
    if(Math.abs(a.inPoint-6.73)<.03) newTime=6.96;
    if(Math.abs(a.inPoint-8.73)<.03) newTime=8.36;
    if(newTime===null) continue;
    place(a,newTime,newTime+.65);
    var levels=a.property("ADBE Audio Group").property("ADBE Audio Levels");
    for(var k=levels.numKeys;k>0;k--) levels.removeKey(k);
    levels.setValueAtTime(newTime,[-10,-10]);
}
"Miolo local · travessia, detalhe e encontro";
