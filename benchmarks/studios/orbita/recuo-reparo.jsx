// Recorded native demonstration. Run on a copy of the 19.5 s ÓRBITA project.
var comp = app.project.item(1);
var screen = comp.layer("TELA (rig)");
var first = comp.layer("O futuro");
var second = comp.layer("cabe num curta.");
if (!screen || !first || !second) throw new Error("This demonstration expects the original ÓRBITA layers.");

function replaceKeys(property, entries, easeInfluence) {
    while (property.numKeys > 0) property.removeKey(property.numKeys);
    for (var k = 0; k < entries.length; k++) property.setValueAtTime(entries[k][0], entries[k][1]);
    if (easeInfluence === undefined) return;
    var ease = new KeyframeEase(0, easeInfluence);
    var values = typeof entries[0][1] === "number" ? [ease] : [ease, ease, ease];
    for (var index = 1; index <= property.numKeys; index++) {
        property.setTemporalEaseAtKey(index, values, values);
    }
}

// Make the opening drift lead into a less concentrated change of scale.
// Keep the spatial relationship and the established later screen-to-grid move.
replaceKeys(screen.transform.scale, [[0,[385,385,100]],[1.45,[372,372,100]],
    [3.25,[100,100,100]],[11.25,[100,100,100]],[12,[45,45,100]]], 33);
replaceKeys(screen.transform.position, [[0,[118,450,0]],[1.45,[118,450,0]],
    [3.25,[270,380,0]],[11.25,[270,380,0]],[12,[152,330,0]]], 33);

// Park the first title while the frame crosses its path. Bring the complete
// phrase back above the settled screen before the brand changes hierarchy.
replaceKeys(first.transform.opacity, [[.125,0],[.46,100],[1.40,100],[1.69,0],
    [2.91,0],[3.12,100],[3.94,100],[4.18,0]]);
replaceKeys(first.transform.position, [[0,[270,188,0]],[1.69,[270,188,0]],
    [2.88,[270,104,0]],[4.18,[270,104,0]]]);
replaceKeys(first.transform.scale, [[0,[100,100,100]],[1.69,[100,100,100]],
    [2.88,[66,66,100]],[4.18,[66,66,100]]]);
replaceKeys(second.transform.opacity, [[2.91,0],[3.12,100],[3.94,100],[4.18,0]]);
replaceKeys(second.transform.position, [[0,[270,174,0]],[4.18,[270,174,0]]]);

for (var i = 1; i <= comp.numLayers; i++) {
    var layer = comp.layer(i);
    var textGroup = layer.property("ADBE Text Properties");
    if (!textGroup) continue;
    var source = textGroup.property("ADBE Text Document");
    if (!source) continue;
    var doc = source.value;
    if (doc.font === "Inter-Black") {
        doc.font = "Inter-Bold";
        source.setValue(doc);
    }
}

var brand = comp.layer("ÓRBITA");
var glow = comp.layer("ÓRBITA 2");
replaceKeys(brand.transform.opacity, [[4.18,0],[4.47,70]]);
replaceKeys(glow.transform.opacity, [[4.22,0],[4.5,100]]);
var cta = comp.layer("CTA rig");
replaceKeys(cta.transform.scale, [[12.583333,[86,86,100]],[13.08,[100,100,100]]], 40);

// Keep the source WAV editable. Match the fade to the new end of the cut.
var soundtrack = null;
for (var j = 1; j <= comp.numLayers; j++) {
    var candidate = comp.layer(j);
    if (/\.wav$/i.test(candidate.name)) { soundtrack = candidate; break; }
}
if (!soundtrack) throw new Error("The original soundtrack must be present.");
var levels = soundtrack.property("ADBE Audio Group").property("ADBE Audio Levels");
replaceKeys(levels, [[0,[7,7]],[16.35,[7,7]],[16.85,[1,1]],
    [17.25,[-12,-12]],[17.58,[-36,-36]],[17.75,[-96,-96]]]);
comp.duration = 17.75;
soundtrack.outPoint = 17.75;
"ÓRBITA: 17.75 s, revised camera and type, native stereo gain and fade";
