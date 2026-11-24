// ÓRBITA local revision of the paid EffectCraft composition, 1080 × 1920, 30 fps.
var comp = app.project.activeItem;
var cream = [0.94,0.91,0.85], ember = [1,0.357,0.141], dark = [0.023,0.027,0.047];
var D = 18;
function find(prefix) {
    for (var i=1; i<=comp.numLayers; i++) if (comp.layer(i).name.indexOf(prefix)===0) return comp.layer(i);
    throw new Error("Missing layer: " + prefix);
}
function prop(l, n) { return l.property("ADBE Transform Group").property(n); }
function clear(p) { for (var i=p.numKeys; i>0; i--) p.removeKey(i); }
function set(l,n,value) { var p=prop(l,n); clear(p); p.setValue(value); }
function keys(l,n,t,v) { var p=prop(l,n); clear(p); for(var i=0;i<t.length;i++) p.setValueAtTime(t[i],v[i]); }
function span(l,a,b,offset) { l.startTime=a-(offset||0); l.inPoint=a; l.outPoint=b; }
function plate(name,w,h,c,x,y,a,b) {
    var l=comp.layers.addSolid(c,name,w,h,1,D); span(l,a,b); set(l,"ADBE Position",[x,y]); return l;
}
function label(l, words, font, size, color, y, a, fade) {
    var p=l.property("ADBE Text Properties").property("ADBE Text Document"), d=p.value;
    d.text=words; d.font=font; d.fontSize=size; d.fillColor=color; d.tracking=0;
    d.justification=ParagraphJustification.CENTER_JUSTIFY; p.setValue(d);
    span(l,a,D); set(l,"ADBE Position",[540,y]);
    keys(l,"ADBE Opacity",[a,a+fade],[0,100]);
}
var planet=comp.layer(1), field=comp.layer(2);
field.name="Campo estelar · fundo original";
span(field,0,D); set(field,"ADBE Position",[540,960]);
field.moveAfter(find("Tira"));
planet.name="Planeta · motivo de abertura";
span(planet,0,4.7);
keys(planet,"ADBE Position",[0,0.8,3.25,4.7],[[540,964],[540,990],[540,1280],[540,1120]]);
keys(planet,"ADBE Scale",[0,0.8,3.25,4.7],[[64,64],[98,98],[78,78],[130,130]]);
keys(planet,"ADBE Opacity",[0,0.18,3.7,4.7],[0,100,100,0]);
planet.moveAfter(find("Tira")); planet.moveBefore(field);
var signature=find("ÓRBITA"), category=find("mostra de curtas"), cta=find("Confira a programação"), credit=find("Imagens: Tears of Steel");
label(signature,"ÓRBITA","Unbounded",155,cream,1050,12.15,0.36);
label(category,"mostra de curtas de ficção científica.","Space Grotesk",50,cream,1180,12.6,0.35);
label(cta,"Confira a programação.","Space Grotesk",58,dark,1439,13.4,0.32);
label(credit,"Tears of Steel · Blender Foundation","Space Grotesk",47,cream,1640,13.55,0.32);
var creditTerms=comp.layers.addText("Trechos editados · CC BY 3.0");
label(creditTerms,"Trechos editados · CC BY 3.0","Space Grotesk",43,cream,1700,13.55,0.32);
var openA=find("O futuro"), openB=find("cabe num curta");
label(openA,"O futuro","Unbounded",106,cream,500,.45,.42); openA.outPoint=3.85;
label(openB,"cabe num curta.","Unbounded",84,ember,622,1.04,.43); openB.outPoint=3.95;
var invitation=plate("Assinatura · convite laranja",770,112,ember,540,1417,13.4,D);
keys(invitation,"ADBE Opacity",[13.4,13.72],[0,100]); invitation.moveAfter(cta);
var line=plate("Assinatura · traço orbital",300,5,ember,540,1106,12.35,D);
keys(line,"ADBE Scale",[12.35,12.92],[[0,100],[100,100]]);

var oldFrame=find("Moldura");
var closingClip=comp.layer(oldFrame.index-1);
if (closingClip.name.indexOf("9e08e448")!==0) throw new Error("Unexpected closing footage: "+closingClip.name);
for(var i=comp.numLayers;i>0;i--) if(comp.layer(i).name.indexOf("FPerf")===0) comp.layer(i).remove();
oldFrame.remove();
// Keep the film geometry tied to one origin and scale. The video fits between the rails.
var t=[11,11.48,12.32], scales=[1.52,1.28,1], centers=[936,806,638];
function film(l,dx,dy,scale) {
    var positions=[], sizes=[];
    for(var j=0;j<t.length;j++){positions.push([540+dx*scales[j],centers[j]+dy*scales[j]]); sizes.push([scale*scales[j],scale*scales[j]]);}
    keys(l,"ADBE Position",t,positions); keys(l,"ADBE Scale",t,sizes);
}
var frame=plate("Assinatura · corpo da película",900,374,[0.125,0.078,0.061],540,638,11,D);
frame.moveAfter(closingClip); film(frame,0,0,100);
film(closingClip,0,0,132);
for(var r=0;r<2;r++) for(var j=0;j<13;j++) {
    var perf=plate("Assinatura · perfuração",24,12,[0.74,0.55,0.39],540,638,11,D);
    film(perf,-396+j*66,r?165:-165,100);
}
function gain(l,t,db) {
    var p=l.property("ADBE Audio Group").property("ADBE Audio Levels");
    clear(p); for(var i=0;i<t.length;i++) p.setValueAtTime(t[i],[db[i],db[i]]);
}
var music=find("91e68920"), hit=find("fa179bb5"), sweep=find("9ec88053"), resolve=find("92a35922");
gain(music,[0,0.65,4.65,5,5.4,10.8,12.5,16.65,18],[-45,-2,-2,-6,-2,-3,-4,-4,-55]);
span(hit,5,5.9); gain(hit,[5],[-6]);
span(resolve,12.18,13.78); gain(resolve,[12.18],[-5]);
// One lead-in, two cuts and one pullback. Quiet accents leave the score audible.
var offsets=[4.46,6.73,8.73,10.76], sw=0;
for(var j=1;j<=comp.numLayers;j++) {
    var a=comp.layer(j);
    if(a.name.indexOf("9ec88053")===0 && sw<offsets.length) {
        span(a,offsets[sw],offsets[sw]+0.65); gain(a,[offsets[sw]],[-10]); sw++;
    }
}
"ÓRBITA: película alinhada, identidade, crédito e som";
