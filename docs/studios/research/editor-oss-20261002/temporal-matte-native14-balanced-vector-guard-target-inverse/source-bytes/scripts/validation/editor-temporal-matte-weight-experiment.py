"""Run one source-frozen API experiment and restore the pending production gate.

This candidate is not a production qualification. No thresholds or probes change.
The complete original bytes are retained before mutation and restored in finally.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "docs/studios/research/editor-oss-20261002"
MODE = sys.argv[1] if len(sys.argv) > 1 else "composition-opacity"
assert MODE in {"composition-opacity", "filter-opacity", "direct-root", "nested-opacity", "nested-composition-opacity",
               "svg-arithmetic-tree", "balanced-plus-lighter", "balanced-composition-opacity",
               "factored-plus-lighter", "factored-balanced-opacity", "padded-mask-viewport",
               "balanced-padded-mask-viewport", "balanced-inverted-padded-rect", "balanced-mask-guard-band",
               "balanced-padded-vector-guard-band", "factored-balanced-padded-vector-guard-band",
               "balanced-padded-vector-guard-band-padded-filter", "balanced-vector-guard-composite-inverse",
               "balanced-vector-guard-target-inverse"}
tag = os.environ.get("TEMPORAL_MATTE_EXPERIMENT_TAG", MODE)
assert tag.replace("-", "").replace("_", "").isalnum()
OUT = DIRECTORY / ("temporal-matte-native14-" + tag)
assert not OUT.exists(), "Do not overwrite an experimental phase"
baseline = json.loads((DIRECTORY / "temporal-matte-native13-current-sources.json").read_text(encoding="utf-8"))
ignored_capture = {"backend/tests/temporal_matte_kernel_diagnostic.py"} if os.environ.get(
    "TEMPORAL_MATTE_MANIFEST_CAPTURE") else set()
assert all(name in ignored_capture or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
           for name, digest in baseline["sources"].items()), "Native13 baseline source drift"
OUT.mkdir()
names = ["workers/remotion-benchmark/src/temporal-exposure.tsx",
         "backend/app/domain/studios/temporal_exposure.py", "backend/app/providers/studios/remotion_render.py",
         "workers/remotion-benchmark/src/asset-matte.tsx"]
original = {name: (ROOT / name).read_bytes() for name in names}
candidate = dict(original)
if MODE in {"factored-plus-lighter", "factored-balanced-opacity", "factored-balanced-padded-vector-guard-band"}:
    old = b"""  return <div data-temporal-exposure={JSON.stringify(diagnostic)}
    style={{position:'absolute',inset:0,zIndex,isolation:'isolate'}}>
    {nodes.map((node,index)=><div key={index} style={{position:'absolute',inset:0,
      mixBlendMode:'plus-lighter',filter:`opacity(${1/frames.length})`}}>{node}</div>)}
  </div>;"""
    new = b"""  const roots=nodes.map(node=>{
    if(!React.isValidElement<Record<string,any>>(node))return null;
    if(typeof node.type==='string')return {element:node,wrapped:false};
    if(componentInputs(node)?.tag==='asset_matte_v1'&&
      React.isValidElement<Record<string,any>>(node.props.children)&&typeof node.props.children.type==='string'){
      return {element:node.props.children,wrapped:true};
    }
    return null;
  });
  const sharedOpacity=roots[0]?.element.props.style?.opacity;
  const factored=typeof sharedOpacity==='number'&&Number.isFinite(sharedOpacity)&&sharedOpacity>=0&&sharedOpacity<=1&&
    roots.every(root=>root!==null&&root.element.props.style?.opacity===sharedOpacity&&
      (root.element.props.style?.mixBlendMode??'normal')==='normal');
  const samplesToComposite=factored?nodes.map((node,index)=>{
    const root=roots[index]!;
    const opaque=React.cloneElement(root.element,{style:{...root.element.props.style,opacity:1}});
    return root.wrapped?React.cloneElement(node as React.ReactElement<any>,{children:opaque}):opaque;
  }):nodes;
  return <div data-temporal-exposure={JSON.stringify(diagnostic)}
    data-experimental-opacity-factored={factored?sharedOpacity:undefined}
    style={{position:'absolute',inset:0,zIndex,isolation:'isolate',opacity:factored?sharedOpacity:1}}>
    {samplesToComposite.map((node,index)=><div key={index} style={{position:'absolute',inset:0,
      mixBlendMode:'plus-lighter',filter:`opacity(${1/frames.length})`}}>{node}</div>)}
  </div>;"""
    assert candidate[names[0]].count(old) == 1
    if MODE in {"factored-balanced-opacity", "factored-balanced-padded-vector-guard-band"}:
        flat = b"""    {samplesToComposite.map((node,index)=><div key={index} style={{position:'absolute',inset:0,
      mixBlendMode:'plus-lighter',filter:`opacity(${1/frames.length})`}}>{node}</div>)}"""
        tree = b"""    {(() => {
      const average=(items:React.ReactNode[]):React.ReactNode=>{
        if(items.length===1)return items[0];
        const cut=Math.floor(items.length/2),left=items.slice(0,cut),right=items.slice(cut);
        return <div style={{position:'absolute',inset:0,isolation:'isolate'}}>
          <div style={{position:'absolute',inset:0,mixBlendMode:'plus-lighter',opacity:left.length/items.length}}>
            {average(left)}
          </div>
          <div style={{position:'absolute',inset:0,mixBlendMode:'plus-lighter',opacity:right.length/items.length}}>
            {average(right)}
          </div>
        </div>;
      };
      return average(samplesToComposite);
    })()}"""
        assert new.count(flat) == 1
        new = new.replace(flat, tree)
    candidate[names[0]] = candidate[names[0]].replace(old, new)
elif MODE in {"balanced-plus-lighter", "balanced-composition-opacity", "balanced-padded-mask-viewport",
              "balanced-inverted-padded-rect", "balanced-mask-guard-band", "balanced-padded-vector-guard-band",
              "balanced-padded-vector-guard-band-padded-filter", "balanced-vector-guard-composite-inverse",
              "balanced-vector-guard-target-inverse"}:
    old = b"""    {nodes.map((node,index)=><div key={index} style={{position:'absolute',inset:0,
      mixBlendMode:'plus-lighter',filter:`opacity(${1/frames.length})`}}>{node}</div>)}"""
    new = b"""    {(() => {
      const average=(items:React.ReactNode[]):React.ReactNode=>{
        if(items.length===1)return items[0];
        const cut=Math.floor(items.length/2),left=items.slice(0,cut),right=items.slice(cut);
        return <div style={{position:'absolute',inset:0,isolation:'isolate'}}>
          <div style={{position:'absolute',inset:0,mixBlendMode:'plus-lighter',filter:`opacity(${left.length/items.length})`}}>
            {average(left)}
          </div>
          <div style={{position:'absolute',inset:0,mixBlendMode:'plus-lighter',filter:`opacity(${right.length/items.length})`}}>
            {average(right)}
          </div>
        </div>;
      };
      return average(nodes);
    })()}"""
    assert candidate[names[0]].count(old) == 1
    if MODE in {"balanced-composition-opacity", "balanced-padded-mask-viewport", "balanced-inverted-padded-rect",
                "balanced-mask-guard-band", "balanced-padded-vector-guard-band", "balanced-padded-vector-guard-band-padded-filter",
                "balanced-vector-guard-composite-inverse", "balanced-vector-guard-target-inverse"}:
        new = new.replace(b"filter:`opacity(${left.length/items.length})`", b"opacity:left.length/items.length")
        new = new.replace(b"filter:`opacity(${right.length/items.length})`", b"opacity:right.length/items.length")
    candidate[names[0]] = candidate[names[0]].replace(old, new)
elif MODE == "svg-arithmetic-tree":
    # Chromium candidate: average full-strength samples in a balanced SVG
    # filter tree. This retains the typed sample times and equal final weights.
    # It is experimental and does not rename the production composition policy.
    old = b"""  return <div data-temporal-exposure={JSON.stringify(diagnostic)}
    style={{position:'absolute',inset:0,zIndex,isolation:'isolate'}}>
    {nodes.map((node,index)=><div key={index} style={{position:'absolute',inset:0,
      mixBlendMode:'plus-lighter',filter:`opacity(${1/frames.length})`}}>{node}</div>)}
  </div>;"""
    new = b"""  const primitives:React.ReactNode[]=[];
  let branches=nodes.map((_,index)=>({name:'sample-'+index,count:1}));
  let serial=0;
  while(branches.length>1){
    const next:typeof branches=[];
    for(let index=0;index<branches.length;index+=2){
      const a=branches[index],b=branches[index+1];
      if(!b){next.push(a);continue;}
      const name='average-'+serial++,count=a.count+b.count;
      primitives.push(<feComposite key={name} in={a.name} in2={b.name} operator="arithmetic"
        k1={0} k2={a.count/count} k3={b.count/count} k4={0} result={name}/>);
      next.push({name,count});
    }
    branches=next;
  }
  const unique='exposure-'+zIndex+'-'+frame.toString().replace('.','-');
  return <div data-temporal-exposure={JSON.stringify(diagnostic)}
    data-experimental-compositing="svg_arithmetic_balanced_tree"
    style={{position:'absolute',inset:0,zIndex,isolation:'isolate'}}>
    <svg width="100%" height="100%" style={{position:'absolute',inset:0,overflow:'visible'}}>
      <defs>
        {nodes.map((node,index)=><g id={unique+'-sample-'+index} key={index}>
          <foreignObject x={0} y={0} width="100%" height="100%">
            <div style={{position:'absolute',inset:0}}>{node}</div>
          </foreignObject>
        </g>)}
        <filter id={unique+'-filter'} filterUnits="userSpaceOnUse" primitiveUnits="userSpaceOnUse"
          x={0} y={0} width="100%" height="100%" colorInterpolationFilters="sRGB">
          {nodes.map((_,index)=><feImage key={index} href={'#'+unique+'-sample-'+index}
            x={0} y={0} width="100%" height="100%" preserveAspectRatio="none" result={'sample-'+index}/>)}
          {primitives}
        </filter>
      </defs>
      <rect x={0} y={0} width="100%" height="100%" fill="transparent" filter={'url(#'+unique+'-filter)'}/>
    </svg>
  </div>;"""
    assert candidate[names[0]].count(old) == 1
    candidate[names[0]] = candidate[names[0]].replace(old, new)
elif MODE == "composition-opacity":
    token = b"filter:`opacity(${1/frames.length})`"
    assert candidate[names[0]].count(token) == 1
    candidate[names[0]] = candidate[names[0]].replace(token, b"opacity:1/frames.length")
elif MODE == "direct-root":
    old = b"""  return <div data-temporal-exposure={JSON.stringify(diagnostic)}
    style={{position:'absolute',inset:0,zIndex,isolation:'isolate'}}>
    {nodes.map((node,index)=><div key={index} style={{position:'absolute',inset:0,
      mixBlendMode:'plus-lighter',filter:`opacity(${1/frames.length})`}}>{node}</div>)}
  </div>;"""
    new = b"""  const weighted=(node:React.ReactNode,index:number)=>
    React.isValidElement<Record<string,any>>(node)&&typeof node.type==='string'
      ? React.cloneElement(node,{key:index,style:{...node.props.style,mixBlendMode:'plus-lighter',opacity:1/frames.length}})
      : <div key={index} style={{position:'absolute',inset:0,mixBlendMode:'plus-lighter',filter:`opacity(${1/frames.length})`}}>{node}</div>;
  return <div data-temporal-exposure={JSON.stringify(diagnostic)}
    style={{position:'absolute',inset:0,zIndex,isolation:'isolate'}}>
    {nodes.map(weighted)}
  </div>;"""
    assert candidate[names[0]].count(old) == 1
    candidate[names[0]] = candidate[names[0]].replace(old, new)
elif MODE == "nested-opacity":
    old = b"""    {nodes.map((node,index)=><div key={index} style={{position:'absolute',inset:0,
      mixBlendMode:'plus-lighter',filter:`opacity(${1/frames.length})`}}>{node}</div>)}"""
    new = b"""    {nodes.map((node,index)=><div key={index} style={{position:'absolute',inset:0,mixBlendMode:'plus-lighter'}}>
      <div style={{position:'absolute',inset:0,filter:`opacity(${1/frames.length})`}}>{node}</div>
    </div>)}"""
    assert candidate[names[0]].count(old) == 1
    candidate[names[0]] = candidate[names[0]].replace(old, new)
elif MODE == "nested-composition-opacity":
    old = b"""    {nodes.map((node,index)=><div key={index} style={{position:'absolute',inset:0,
      mixBlendMode:'plus-lighter',filter:`opacity(${1/frames.length})`}}>{node}</div>)}"""
    new = b"""    {nodes.map((node,index)=><div key={index} style={{position:'absolute',inset:0,mixBlendMode:'plus-lighter'}}>
      <div style={{position:'absolute',inset:0,opacity:1/frames.length}}>{node}</div>
    </div>)}"""
    assert candidate[names[0]].count(old) == 1
    candidate[names[0]] = candidate[names[0]].replace(old, new)
if MODE in {"padded-mask-viewport", "balanced-padded-mask-viewport", "balanced-padded-vector-guard-band",
            "factored-balanced-padded-vector-guard-band", "balanced-padded-vector-guard-band-padded-filter",
            "balanced-vector-guard-composite-inverse", "balanced-vector-guard-target-inverse"}:
    matte = candidate[names[3]]
    substitutions = [
        (b"const id='asset-matte-'+unique,filter='asset-matte-filter-'+unique;",
         b"const id='asset-matte-'+unique,filter='asset-matte-filter-'+unique,clip='asset-matte-clip-'+unique;"),
        (b"      <defs>\n", b"      <defs>\n        <clipPath id={clip} clipPathUnits=\"userSpaceOnUse\">\n"
         b"          <rect x={0} y={0} width={width} height={height}/>\n        </clipPath>\n"),
        (b'maskContentUnits="userSpaceOnUse" x={0} y={0} width={width} height={height}',
         b'maskContentUnits="userSpaceOnUse" x={-width} y={-height} width={width*3} height={height*3}'),
        (b"          {/* The mask region clips to the target. Its white background must\n"
         b"              cover that region, without adding a coincident AA silhouette. */}\n",
         b"          {/* Keep viewport rounding away from the target edge. One vector\n"
         b"              clip retains the authored target footprint for both modes. */}\n"
         b"          <g clipPath={`url(#${clip})`}>\n"),
        (b"            filter={spec.invert?`url(#${filter})`:undefined}/>\n        </mask>",
         b"            filter={spec.invert?`url(#${filter})`:undefined}/>\n          </g>\n        </mask>"),
    ]
    for before, after in substitutions:
        assert matte.count(before) == 1
        matte = matte.replace(before, after)
    if MODE in {"balanced-padded-vector-guard-band", "factored-balanced-padded-vector-guard-band",
                "balanced-padded-vector-guard-band-padded-filter", "balanced-vector-guard-composite-inverse",
                "balanced-vector-guard-target-inverse"}:
        before = b"maskImage:`url(#${id})`,maskMode:'match-source',maskRepeat:'no-repeat'"
        assert matte.count(before) == 1
        matte = matte.replace(before, before + b",maskClip:'no-clip',outline:'2px solid transparent',outlineOffset:0")
    if MODE == "balanced-padded-vector-guard-band-padded-filter":
        before = b'<filter id={filter} x="0%" y="0%" width="100%" height="100%"'
        assert matte.count(before) == 1
        matte = matte.replace(before, b'<filter id={filter} x="-50%" y="-50%" width="200%" height="200%"')
    if MODE == "balanced-vector-guard-composite-inverse":
        changes = [
            (b"maskType:spec.invert?'luminance':spec.mode", b"maskType:spec.mode"),
            (b'{spec.invert?<rect x={-width} y={-height} width={width*3} height={height*3} fill="white"/>:null}', b'{null}'),
            (b"filter={spec.invert?`url(#${filter})`:undefined}", b"filter={undefined}"),
            (b"maskImage:`url(#${id})`,maskMode:'match-source',maskRepeat:'no-repeat'",
             b"maskImage:spec.invert?`linear-gradient(#fff,#fff),url(#${id})`:`url(#${id})`,"
             b"maskMode:'match-source',maskComposite:spec.invert?'subtract':'add',maskRepeat:'no-repeat'"),
        ]
        for before, after in changes:
            assert matte.count(before) == 1
            matte = matte.replace(before, after)
    if MODE == "balanced-vector-guard-target-inverse":
        start = matte.index(b"        {spec.invert?<filter")
        end = matte.index(b"        </filter>:null}", start) + len(b"        </filter>:null}")
        replacement = b"""        {spec.invert?<filter id={filter} filterUnits="userSpaceOnUse" primitiveUnits="userSpaceOnUse"
          x={-width} y={-height} width={width*3} height={height*3} colorInterpolationFilters="sRGB">
          {spec.mode==='luminance'?<>
            <feColorMatrix in="SourceGraphic" type="luminanceToAlpha" result="luminance"/>
            <feComposite in="luminance" in2="SourceAlpha" operator="in" result="coverage"/>
          </>:null}
          <feColorMatrix in={spec.mode==='luminance'?'coverage':'SourceGraphic'} type="matrix"
            x={-width} y={-height} width={width*3} height={height*3}
            values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 -1 1"/>
        </filter>:null}"""
        matte = matte[:start] + replacement + matte[end:]
        changes = [
            (b"maskType:spec.invert?'luminance':spec.mode", b"maskType:spec.invert?'alpha':spec.mode"),
            (b'{spec.invert?<rect x={-width} y={-height} width={width*3} height={height*3} fill="white"/>:null}', b'{null}'),
            (b'          <g clipPath={`url(#${clip})`}>',
             b'          <g clipPath={`url(#${clip})`}>\n            <g filter={spec.invert?`url(#${filter})`:undefined}>'),
            (b"            filter={spec.invert?`url(#${filter})`:undefined}/>\n          </g>",
             b"            filter={undefined}/>\n            </g>\n          </g>"),
        ]
        for before, after in changes:
            assert matte.count(before) == 1
            matte = matte.replace(before, after)
    candidate[names[3]] = matte
elif MODE == "balanced-inverted-padded-rect":
    matte = candidate[names[3]]
    substitutions = [
        (b'maskContentUnits="userSpaceOnUse" x={0} y={0} width={width} height={height}',
         b'maskContentUnits="userSpaceOnUse" x={spec.invert?-width:0} y={spec.invert?-height:0} '
         b'width={spec.invert?width*3:width} height={spec.invert?height*3:height}'),
        (b'<rect x={-width} y={-height} width={width*3} height={height*3} fill="white"/>',
         b'<rect x={0} y={0} width={width} height={height} fill="white"/>'),
        (b"          {/* The mask region clips to the target. Its white background must\n"
         b"              cover that region, without adding a coincident AA silhouette. */}",
         b"          {/* The inverse's painted white rect defines its target footprint;\n"
         b"              the padded mask viewport does not cut off its edge coverage. */}"),
    ]
    for before, after in substitutions:
        assert matte.count(before) == 1
        matte = matte.replace(before, after)
    candidate[names[3]] = matte
elif MODE == "balanced-mask-guard-band":
    before = b"maskImage:`url(#${id})`,maskMode:'match-source',maskRepeat:'no-repeat'"
    after = before + b",maskClip:'no-clip',outline:'2px solid transparent',outlineOffset:0"
    assert candidate[names[3]].count(before) == 1
    candidate[names[3]] = candidate[names[3]].replace(before, after)
gate = candidate[names[1]]
start = gate.index(b"                # Effective draw-time mapping is implemented")
end = gate.index(b"    if any(layer.properties.get(\"recipeTemporalBlur\")", start)
candidate[names[1]] = gate[:start] + gate[end:]
assert candidate[names[2]].count(b"4.0.527-native.13") == 2
candidate[names[2]] = candidate[names[2]].replace(b"4.0.527-native.13", b"4.0.527-native.14")
for name, raw in original.items():
    target = OUT / "original-bytes" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
for name, raw in candidate.items():
    target = OUT / "candidate-bytes" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
result = None
try:
    for name, raw in candidate.items():
        (ROOT / name).write_bytes(raw)
    plugin = "scripts/validation/editor_temporal_matte_failure_evidence.py"
    frozen_names = sorted(set(baseline["sources"]) | {str(Path(__file__).relative_to(ROOT)).replace("\\", "/"), plugin})
    frozen = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in frozen_names}
    for name in frozen_names:
        snapshot = OUT / "source-bytes" / name
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_bytes((ROOT / name).read_bytes())
    (OUT / "sources.json").write_text(json.dumps({"scope": "temporary_actual_API_admission_experiment",
        "providerVersion": "4.0.527-native.14", "weightImplementation": MODE,
        "productionAdmissionAfterExperiment": "pending", "sources": frozen}, indent=2), encoding="utf-8")
    environment = dict(os.environ, TEMPORAL_MATTE_EVIDENCE_DIR=str(OUT), TEMPORAL_MATTE_MANIFEST_CAPTURE="rig-external-alpha-normal")
    environment["PYTHONPATH"] = str(ROOT / "scripts/validation") + os.pathsep + environment.get("PYTHONPATH", "")
    environment.pop("TEMPORAL_MATTE_BASELINE", None)
    cases = ["child-external-alpha-True", "rig-external-alpha-False", "rig-external-luminance-True"]
    if os.environ.get("TEMPORAL_MATTE_FULL_MATRIX") == "1":
        cases = ["control-external-alpha-False", "child-external-alpha-False", "child-external-alpha-True",
                 "rig-external-alpha-False", "rig-external-luminance-True", "child-common-alpha-False",
                 "rig-common-luminance-False"]
    command = [sys.executable, "-m", "pytest", "-p", "editor_temporal_matte_failure_evidence",
        *["tests/temporal_matte_kernel_diagnostic.py::test_temporal_matte_actual_api_pixels[" + case + "]"
          for case in cases], "-q", "--tb=short", "--junitxml=" + str(OUT / "tests.xml")]
    result = subprocess.run(command, cwd=ROOT / "backend", env=environment, check=False)
    assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
               for name, digest in frozen.items()), "Source drift during experiment"
finally:
    conflicts = [name for name in names if (ROOT / name).read_bytes() != candidate[name]]
    for name, raw in original.items():
        if name not in conflicts:
            (ROOT / name).write_bytes(raw)
    restored = not conflicts and all((ROOT / name).read_bytes() == raw for name, raw in original.items())
    (OUT / "run.json").write_text(json.dumps({"exitCode": result.returncode if result else None,
        "originalBytesRestored": restored, "conflictingConcurrentEdits": conflicts,
        "productionProviderAfterExperiment": "4.0.527-native.13" if restored else "inspect_conflicts",
        "productionCombinedAdmission": "pending" if restored else "inspect_conflicts"}, indent=2), encoding="utf-8")
    assert restored, "Inspect concurrent edits; do not overwrite them"
sys.exit(result.returncode)
