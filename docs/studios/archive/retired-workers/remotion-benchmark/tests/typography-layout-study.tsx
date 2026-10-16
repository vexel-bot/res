import React, {useEffect, useState} from 'react';
import {Composition, cancelRender, continueRender, delayRender, registerRoot, staticFile} from 'remotion';
import {measureTypography, type LayoutPolicy} from '../src/typography-layout';

const policy:LayoutPolicy={schemaVersion:'studio.typography-layout-policy.v1',policy:'dom.units-fit.v1',
  fitMode:'wrap_shrink',minFontSizePx:320*16/300,maxMeasureSteps:18,maxLayoutUnits:2000,tolerancePx:.5,fontQuantizationPx:1/64};
function Study(){
  const [handle]=useState(()=>delayRender('real-final-font-layout-study'));
  useEffect(()=>{
    (async()=>{
      const font=new FontFace('StudyBoundArial',`url(${staticFile('study.ttf')})`,{weight:'400'});
      const boldFont=new FontFace('StudyBoundArial',`url(${staticFile('study-bold.ttf')})`,{weight:'700'});
      await Promise.all([font.load(),boldFont.load()]);document.fonts.add(font);document.fonts.add(boldFont);
      await document.fonts.ready;
      const results:any[]=[];
      const expect=(value:boolean,message:string)=>{if(!value)throw new Error(message);};
      function source(text:string,unit:'word'|'character',style:Record<string,string>={}){
        const el=document.createElement('div');
        Object.assign(el.style,{fontFamily:'StudyBoundArial',fontWeight:'400',fontSize:'42px',lineHeight:'1.2',
          letterSpacing:'0px',whiteSpace:'pre-wrap',textAlign:'left',width:'275px',height:'220px',...style});
        // Units are explicitly supplied fixture data. No alternate Unicode
        // segmentation is used as proof of the canonical compiler.
        const pieces=unit==='word'?text.split(/(\s+)/u):text==='AC\u0327A\u0303O'?['A','C\u0327','A\u0303','O']:Array.from(text);
        let index=0;
        for(const piece of pieces){
          if(/^\s*$/u.test(piece)){el.append(document.createTextNode(piece));continue;}
          const span=document.createElement('span');span.textContent=piece;span.dataset.typographyUnit=String(index++);
          Object.assign(span.style,{display:'inline-block',opacity:'0.3',transform:'translateY(7px)'});el.append(span);
        }
        document.body.appendChild(el);return el;
      }
      function run(id:string,text:string,unit:'word'|'character',width:number,height:number,style:Record<string,string>={},
        check:(result:ReturnType<typeof measureTypography>)=>void=()=>{}){
        const el=source(text,unit,style);let parent:HTMLElement|undefined;
        if(id==='transformed'){
          parent=document.createElement('div');parent.style.transform='rotate(25deg) scale(1.6)';
          document.body.append(parent);parent.append(el);
        }
        try{
          const result=measureTypography(el,width,height,42,policy,'study-digest-'+id,'checksum_bound_asset');
          expect(result.fits&&result.fontSizePx>=policy.minFontSizePx,'fit/floor: '+id);check(result);
          results.push({id,status:'passed',result});return result;
        }finally{el.remove();parent?.remove();}
      }
      const text='Uma palavra inteira precisa de espaço para leitura clara';
      const wrapped=run('wrap',text,'word',275,220,{},r=>{
        expect(r.lines.length>=3,'wrapping missing');expect(r.fontSizePx>=30,'full paragraph was shrunk into one line');
        expect(r.units.every(u=>!u.text.includes(' ')),'word split');
      });
      const transformed=run('transformed',text,'word',275,220);
      expect(JSON.stringify(wrapped.units)===JSON.stringify(transformed.units),'parent transform contaminated local layout');
      run('unicode','AC\u0327A\u0303O','character',275,100,{},r=>{
        expect(r.units.length===4&&r.units[2].text==='A\u0303','accent units broken');
        expect(r.units.every(u=>u.ink.height>0&&u.baselinePx>0),'final font ink/baseline missing');
      });
      run('blank-lines','A\n\nB','word',275,220,{},r=>expect(r.contentHeightPx>140,'blank line height omitted'));
      run('shrink','palavra inteira','word',150,45,{},r=>expect(r.fontSizePx<42,'height/width shrink not applied'));
      const normal=run('weight-400','palavra inteira','word',275,100);
      const bold=run('weight-700','palavra inteira','word',275,100,{fontWeight:'700'});
      expect(bold.units[0].layout.width>normal.units[0].layout.width,'weight not reflected in DOM metrics');
      const spaced=run('spacing','palavra inteira','word',275,100,{letterSpacing:'2px'});
      expect(spaced.units[0].layout.width>normal.units[0].layout.width+5,'spacing not reflected in metrics');
      const centered=run('center','palavra','word',275,100,{textAlign:'center'});
      expect(centered.units[0].layout.x>50,'text alignment ignored');
      for(const [id,text,requested,override,expected] of [
        ['overflow','W'.repeat(100),42,{},'does_not_fit_at_reading_floor'],
        ['below-floor','Texto',8,{},'below_reading_floor'],
        ['policy','Texto',42,{maxMeasureSteps:200},'layout_policy_invalid'],
        ['unit-limit','A'.repeat(2001),42,{},'layout_unit_limit'],
      ] as const){
        const el=source(text,id==='unit-limit'?'character':'word');
        try{
          let rejected='';try{measureTypography(el,100,80,requested,{...policy,...override},'negative-'+id,'checksum_bound_asset');}
          catch(error){rejected=String(error);}
          expect(rejected.includes(expected),'negative not rejected: '+id);
          results.push({id,status:'passed',expectedRejection:rejected});
        }finally{el.remove();}
      }
      console.log('RES_TEXT_LAYOUT_STUDY:'+JSON.stringify({scope:'actual_Chromium_final_font_DOM_and_Canvas',
        humanReview:'pending',cases:results,passed:results.length}));
      continueRender(handle);
    })().catch(cancelRender);
  },[handle]);
  return <div style={{position:'absolute',inset:0,background:'#101820',color:'white'}}>Final-font DOM study</div>;
}
registerRoot(()=> <Composition id="TextLayoutStudy" component={Study} width={320} height={320} fps={30} durationInFrames={1}/>);
