// A different brief: a warm library opening its doors, followed by the name.
// This scene is deliberately a different spatial transition, without a zoom.
var comp = app.project.activeItem;
comp.duration = 6;
var ink = [.055,.08,.10], warm = [.96,.78,.46], wood = [.32,.17,.09];
function solid(name, width, height, color, x, y) {
    var layer = comp.layers.addSolid(color, name, width, height, 1, 6);
    layer.transform.position.setValue([x,y,0]);
    return layer;
}
function text(value, size, x, y) {
    var layer = comp.layers.addText(value);
    var source = layer.property("ADBE Text Properties").property("ADBE Text Document");
    var doc = source.value;
    doc.font = "Inter-Bold";
    doc.fontSize = size;
    doc.fillColor = [.99,.94,.82];
    doc.justification = ParagraphJustification.CENTER_JUSTIFY;
    source.setValue(doc);
    layer.transform.position.setValue([x,y,0]);
    return layer;
}
function travel(layer, x0, x1) {
    var p = layer.transform.position;
    p.setValueAtTime(.625,[x0,440,0]);
    p.setValueAtTime(2.125,[x1,440,0]);
    var ease = new KeyframeEase(0,36);
    p.setTemporalEaseAtKey(1,[ease,ease,ease],[ease,ease,ease]);
    p.setTemporalEaseAtKey(2,[ease,ease,ease],[ease,ease,ease]);
}
solid("Sala",540,960,ink,270,480);
solid("Luz da biblioteca",405,490,warm,270,442);
solid("Parede do fundo",364,435,[.15,.20,.19],270,442);
for (var row=0;row<3;row++) {
    var y=321+row*102;
    solid("Prateleira "+row,316,11,wood,270,y+35);
    for(var i=0;i<12;i++) {
        var color=[[.87,.36,.18],[.92,.67,.26],[.53,.71,.64],[.76,.53,.42]][(i+row)%4];
        var height=32+(i*9+row*11)%38;
        solid("Livro "+row+"-"+i,16,height,color,138+i*24,y+29-height/2);
    }
}
travel(solid("Porta esquerda",210,512,wood,165,440),165,-62);
travel(solid("Porta direita",210,512,wood,375,440),375,602);
travel(solid("Friso esquerdo",14,512,warm,263,440),263,36);
travel(solid("Friso direito",14,512,warm,277,440),277,504);
var title = text("CASA LUME",61,270,440);
var caption = text("Biblioteca de bairro",28,270,775);
var call = text("Venha conhecer",27,270,824);
// Seed defect: the name sits in the doorway while the friezes move across it.
title.inPoint=.95;
caption.inPoint=2.4;
call.inPoint=3.25;
"CASA LUME · semente do exercício de transferência";
