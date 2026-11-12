// EffectCraft, 540 x 960, 24 fps. Each source remains an independent layer.
var comp = app.project.activeItem;
comp.duration = 18;
var ink = [.029,.045,.065], cream = [.975,.958,.888], acid = [.82,.98,.46];
var clips = [
    ["Cidade", 0, 2.25, 1.015, 1.055, 429],
    ["Rosto", 2.25, 4.50, 1.015, 1.04, 480],
    ["Laboratório", 4.50, 6.25, 1.015, 1.04, 480],
    ["Hologramas", 6.25, 8.0, 1.015, 1.05, 429],
    ["Máquina", 8.0, 9.5, 1.015, 1.055, 480],
    ["Torre", 9.5, 11.0, 1.015, 1.04, 433],
    ["Travessia", 11.0, 13.5, 1.015, 1.045, 432]
];
if (comp.numLayers !== clips.length + 3) throw new Error("Expected seven shots, two audio stems and the base solid");
var video = [];
for(var i=0;i<clips.length;i++) video.push(comp.layer(comp.numLayers-1-i));
var bed = comp.layer(2), hits = comp.layer(1);
bed.name="SOM · pulsação harmônica"; hits.name="SOM · cortes e assinatura";
function windowAt(l,a,b) { l.inPoint=a; l.outPoint=b; return l; }
function v(x,y) { return [x,y,0]; }
function move(l,x,y) { l.transform.position.setValue(v(x,y)); }
function scale(l,t,f) { l.transform.scale.setValueAtTime(t,[f*100,f*100,100]); }
function opacity(l,t,o) { l.transform.opacity.setValueAtTime(t,o); }
function rect(n,w,h,c,x,y,a,b) {
    var l = comp.layers.addSolid(c,n,w,h,1,18);
    move(l,x,y); return windowAt(l,a,b);
}
function label(s,size,x,y,a,b,colour,center) {
    var l=comp.layers.addText(s);
    var p=l.property("ADBE Text Properties").property("ADBE Text Document");
    var d=p.value; d.font="Inter-Bold"; d.fontSize=size; d.fillColor=colour;
    d.justification=center ? ParagraphJustification.CENTER_JUSTIFY : ParagraphJustification.LEFT_JUSTIFY;
    p.setValue(d); move(l,x,y); return windowAt(l,a,b);
}
function fadeIn(l,a,b) { opacity(l,a,0); opacity(l,b,100); }
var background=rect("Fundo de projeção",540,960,ink,270,480,0,18);
background.moveToEnd();
for(var j=0;j<clips.length;j++) {
    var a=clips[j], l=video[j];
    l.name=a[0]; l.startTime=a[1]; windowAt(l,a[1],a[2]); move(l,270,a[5]);
    scale(l,a[1],a[3]); scale(l,a[2],a[4]);
}

// Black plates over the shots keep the text detached from moving edges.
rect("Base da abertura",540,340,ink,270,772,0,2.25);
rect("Risco da projeção",70,3,acid,72,688,0,2.25);
label("O futuro cabe",52,38,759,.125,2.25,cream,false);
label("num curta.",71,38,837,.333,2.25,acid,false);
rect("Placa de categoria",540,92,ink,270,98,2.25,6.25);
rect("Marcador de categoria",4,45,acid,38,98,2.25,6.25);
label("MOSTRA DE CURTAS",25,53,95,2.25,6.25,cream,false);
label("DE FICÇÃO CIENTÍFICA",20,53,124,2.25,6.25,acid,false);
rect("Máscara inferior · filme",540,248,ink,270,848,6.25,13.5);
rect("Régua · filme",464,2,[.30,.38,.30],270,728,6.25,13.5);
label("ÓRBITA",57,38,831,6.25,13.5,cream,false);
rect("Acima da projeção",540,135,ink,270,67.5,6.25,13.5);
rect("Limite da tela",464,2,[.30,.38,.30],270,135,6.25,13.5);
var shutter=rect("Obturador",540,960,ink,270,480,13.333,13.5);
opacity(shutter,13.333,0); opacity(shutter,13.5,100);

// The last beat resolves to a clean slate. Only the rule moves after the CTA.
rect("Cartela final",540,960,ink,270,480,13.5,18);
rect("Campo da assinatura",462,425,[.051,.076,.094],270,462,13.5,18);
rect("Linha de assinatura",387,2,[.36,.46,.34],270,323,13.5,18);
var brand=label("ÓRBITA",104,270,442,13.5,18,cream,true);
fadeIn(brand,13.5,13.75);
label("Mostra de curtas",31,270,509,13.75,18,cream,true);
label("de ficção científica",31,270,548,13.75,18,cream,true);
var cta=rect("Bloco de convite",389,68,acid,270,633,14.333,18);
fadeIn(cta,14.333,14.5);
label("Confira a programação",29,270,644,14.5,18,ink,true);
label("Imagens: Tears of Steel · Blender Foundation",13,270,833,13.75,18,cream,true);
label("Trechos editados · CC BY 3.0",13,270,854,13.75,18,cream,true);
"ÓRBITA · sete planos, duas pistas e assinatura";
