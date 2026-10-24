import test from 'node:test';
import assert from 'node:assert/strict';
import { bindHologramInteraction } from './hologramInteraction';

test('mouse/touch field stays local, preserves scroll, rejects drag clicks but retains keyboard/tap activation', () => {
  class Target extends EventTarget { getBoundingClientRect() { return {left:0,top:0,width:200,height:200}; } }
  const target = new Target(), control = bindHologramInteraction(target as unknown as HTMLElement, () => {});
  const send = (type:string, pointerType:string, x:number, y:number) => {
    const event = new Event(type,{bubbles:true,cancelable:true});
    Object.assign(event,{pointerType,clientX:x,clientY:y,isPrimary:true}); target.dispatchEvent(event); return event;
  };
  send('pointerenter','mouse',80,100); assert.ok(control.pointer.active);
  assert.ok(Math.abs(control.pointer.x + .2) < .001);
  send('pointerdown','mouse',80,100); send('pointermove','mouse',140,100); send('pointerup','mouse',140,100);
  const dragClick = new Event('click',{cancelable:true}); Object.assign(dragClick,{detail:1}); target.dispatchEvent(dragClick);
  assert.equal(dragClick.defaultPrevented,true);
  const keyboard = new Event('click',{cancelable:true}); Object.assign(keyboard,{detail:0}); target.dispatchEvent(keyboard);
  assert.equal(keyboard.defaultPrevented,false);
  send('pointerleave','mouse',140,100); assert.equal(control.pointer.active,false);
  const touch = send('pointerdown','touch',100,100); const scroll = send('pointermove','touch',102,150);
  assert.equal(touch.defaultPrevented,false); assert.equal(scroll.defaultPrevented,false);
  send('pointercancel','touch',102,150); assert.equal(control.pointer.active,false);
  send('pointerdown','touch',100,100); send('pointerup','touch',100,100);
  const tap = new Event('click',{cancelable:true}); Object.assign(tap,{detail:1}); target.dispatchEvent(tap);
  assert.equal(tap.defaultPrevented,false);
  control.dispose(); send('pointermove','mouse',160,100); assert.equal(control.pointer.active,false);
});

test('miniature click mode never reacts to hover or dragging and preserves the existing click action',()=>{
  class Target extends EventTarget {getBoundingClientRect(){return {left:0,top:0,width:60,height:60};}}
  const target=new Target();let bursts=0,wakes=0;
  const control=bindHologramInteraction(target as unknown as HTMLElement,()=>{wakes++;},{mode:'click',onPress:pointer=>{
    bursts++;assert.equal(pointer.active,false);assert.equal(pointer.vx,0);assert.equal(pointer.vy,0);
  }});
  const send=(type:string,pointerType='mouse')=>{
    const event=new Event(type,{cancelable:true});Object.assign(event,{pointerType,clientX:35,clientY:30,isPrimary:true});target.dispatchEvent(event);return event;
  };
  send('pointerenter');send('pointermove');assert.equal(control.pointer.active,false);assert.equal(wakes,0);assert.equal(bursts,0);
  send('pointerdown');send('pointermove');assert.equal(control.pointer.active,false);assert.equal(bursts,0);
  send('pointerup');const click=new Event('click',{cancelable:true});Object.assign(click,{detail:1,clientX:35,clientY:30});target.dispatchEvent(click);
  assert.equal(click.defaultPrevented,false);assert.equal(bursts,1);
  send('pointerenter','touch');send('pointerdown','touch');const scroll=send('pointermove','touch');send('pointercancel','touch');
  assert.equal(scroll.defaultPrevented,false);assert.equal(control.pointer.active,false);assert.equal(bursts,1);
  const keyboard=new Event('click',{cancelable:true});Object.assign(keyboard,{detail:0});target.dispatchEvent(keyboard);
  assert.equal(keyboard.defaultPrevented,false);assert.equal(bursts,2);
  control.dispose();target.dispatchEvent(click);assert.equal(bursts,2);
});

test('interaction mode changes clear the force field without rebuilding the canvas or blocking clicks',()=>{
  class Target extends EventTarget {getBoundingClientRect(){return {left:0,top:0,width:200,height:200};}}
  const target=new Target(),control=bindHologramInteraction(target as unknown as HTMLElement,()=>{});
  const move=new Event('pointermove');Object.assign(move,{pointerType:'mouse',clientX:90,clientY:100,isPrimary:true});
  target.dispatchEvent(move);assert.equal(control.pointer.active,true);
  control.setMode('click');assert.equal(control.pointer.active,false);
  target.dispatchEvent(move);assert.equal(control.pointer.active,false);
  control.setMode('full');target.dispatchEvent(move);assert.equal(control.pointer.active,true);
  control.dispose();
});
