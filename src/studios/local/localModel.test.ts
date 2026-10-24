import test from 'node:test';
import assert from 'node:assert/strict';
import { valueAt, newLayer, duplicateLayer, containsPoint, localScenes, localRecoveryMatchesProject, mergeAgentTasks } from './localModel';
import type { AgentTask } from './localApi';

test('a stale task-history read cannot replace a completed plan with a running task or erase its receipt', () => {
    const base = {id:'one',documentId:'doc',documentRevision:1,role:'image',provider:'clicko.local-tools',createdAt:'2026-10-22T12:00:00Z'};
    const running:AgentTask = {...base,status:'running'};
    const completed:AgentTask = {...base,status:'succeeded',appliedRevision:2,result:{commands:[],rationale:'Done',state:'planned',inference:'none'}};
    assert.deepEqual(mergeAgentTasks([completed],[running]),[completed]);
    assert.deepEqual(mergeAgentTasks([completed],[{...completed,appliedRevision:null}]),[completed]);
    assert.deepEqual(mergeAgentTasks([running],[completed]),[completed]);
    assert.deepEqual(mergeAgentTasks([completed],[]),[completed]);
});

test('an explicit KLIC project link cannot recover the draft or pending write of another project', () => {
    assert.equal(localRecoveryMatchesProject('project-b', 'project-a'), false);
    assert.equal(localRecoveryMatchesProject('project-b', undefined), false);
    assert.equal(localRecoveryMatchesProject('project-b', 'project-b'), true);
    assert.equal(localRecoveryMatchesProject(null, 'project-a'), true);
});
test('local preview clamps keyframes and matches the smooth renderer curves', () => {
    const keys = [{ property: 'x' as const, frame: 0, value: -100 }, { property: 'x' as const, frame: 24, value: 0, easing: 'ease-out' as const }];
    assert.equal(valueAt(keys, 'x', 1, -2), -100);
    assert.equal(valueAt(keys, 'x', 1, 12), -12.5);
    assert.equal(valueAt(keys, 'x', 1, 40), 0);
    assert.equal(valueAt(keys, 'y', 30, 12), 30);
    const smooth = [{ property: 'opacity' as const, frame: 0, value: 0 }, { property: 'opacity' as const, frame: 10, value: 1, easing: 'ease-in-out' as const }];
    assert.equal(valueAt(smooth, 'opacity', 1, 5), .5);
    assert.equal(valueAt(smooth, 'opacity', 1, 2), .10400000000000002);
});
test('duplicate is independent and preserves original animations, with bounded layer count', () => {
    const layer=newLayer('text',640,360,360);
    layer.properties.keyframes=[{property:'x',frame:0,value:0}];
    const copy=duplicateLayer(layer,[layer]);
    assert.notEqual(copy.id,layer.id);
    copy.properties.keyframes![0].value=12;
    assert.equal(layer.properties.keyframes[0].value,0);
    assert.throws(()=>duplicateLayer({...layer,locked:true},[layer]),/Desbloqueie/);
    assert.throws(()=>duplicateLayer(layer,Array(24).fill(layer)),/24/);
});
test('preview selection inverts rotation and scale rather than selecting the old bounding box', () => {
    const layer=newLayer('shape',640,360,360);
    Object.assign(layer,{x:100,y:100,width:200,height:40,rotation:90});
    assert.equal(containsPoint(layer,0,200,200),true);
    assert.equal(containsPoint(layer,0,110,120),false);
});
test('scene navigation tolerates corrupted legacy drafts without throwing or duplicate keys', () => {
    assert.deepEqual(localScenes(null),[]);
    assert.deepEqual(localScenes({localProduction:{scenes:{invalid:true}}}),[]);
    const scene={id:'one',title:'Cena',startFrame:0,durationFrames:120};
    assert.deepEqual(localScenes({localProduction:{scenes:[null,scene,scene,{...scene,id:'bad',durationFrames:-1}]}}),[scene]);
});
