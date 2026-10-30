"""Transient B1/B2 effects around the unchanged native transformed Space.

No native timing, position, source asset, material or input edits. The existing
0.14s blink owns movement; visual remnants dissipate independently for 0.42s.
"""
import json
import math
import os
from pathlib import Path
import runpy
import unreal

BASE = runpy.run_path(str(Path(__file__).with_name('sparrow_orbit_arsenal_studies.py')))
BaseStudy, valid, clamp = BASE['Study'], BASE['_valid'], BASE['_clamp']
TAG = unreal.Name('SparrowBlinkFlowStudy')
DESIGNS = {
    'B1': '빛실 잔상: 출발의 작은 파열에서 도착으로 세 가닥의 금빛 결이 이어졌다가 가늘게 흩어진다.',
    'B2': '날갯결 산개: 날개의 양쪽에서 짧은 금빛 깃결이 갈라지고 도착점 주변으로 부드럽게 모인다.',
}


def author(out):
    return {'passed': True, 'assets_saved': False, 'production_changed': False, 'designs': DESIGNS}


class Study(BaseStudy):
    def __init__(self, rig, option):
        super().__init__(rig, option)
        self.start = rig['pawn']().get_actor_location()
        self.end = self.start + self.forward*480.
        self.committed = False
        self.fragments_emitted = False
        self.lines = [[self.plane('soft_line', 'flow') for _ in range(10)] for _ in range(3 if option == 'B1' else 6)]
        self.motes = [self.plane('soft_dot', 'spark') for _ in range(12)]
        for row in self.planes:
            row['actor'].set_editor_property('tags', [TAG])
        self.pulse('muzzle', ('Wisps', 'Sparks'), self.start, unreal.Rotator(), (1.05,.85,1.20), .32, 1.8)

    def update(self, age):
        point = self.rig['pawn']().get_actor_location()
        if not self.committed and (point-self.start).length() > 10.:
            self.committed = True
            self.end = point
            self.pulse('impact', ('Main Flames', 'Sparks'), self.end, unreal.Rotator(), (.90,.70,.95), .30, 1.9)
            if self.option == 'B2':
                self.pulse('shards', ('Flames2',), self.end, unreal.Rotator(), (.72,.72,.85), .32, 1.7)
        if self.option == 'B2' and self.committed and not self.fragments_emitted:
            self.fragments_emitted = True
            for i in range(4):
                u=(i+.3)/4.5
                p=self.start+(self.end-self.start)*u+self.right*((-1. if i%2 else 1.)*35.)+self.up*18.
                self.pulse('shards', ('Flames2',), p, unreal.MathLibrary.make_rot_from_x(self.forward),
                           (.70,.42,.58), .28, 2.1)
        fade = (1.-clamp((age-.08)/.34))**1.5
        head = clamp(age/.075)
        for strand, rows in enumerate(self.lines):
            for i, row in enumerate(rows):
                def p(u):
                    if self.option == 'B1':
                        return self.start+(self.end-self.start)*u+self.right*((strand-1.)*22.*math.sin(math.pi*u))+self.up*(8.+(strand-1.)*24.+28.*math.sin(math.pi*u))
                    side = -1. if strand<3 else 1.
                    j = strand%3
                    return self.start+(self.end-self.start)*u+self.right*(side*(30.+j*16.)*math.sin(math.pi*u))+self.up*(18.+j*21.+36.*math.sin(math.pi*u))
                u0, u1 = head*i/10., head*(i+1)/10.
                # Fade from departure first; the last trace belongs to arrival.
                weight = fade*(.30+.70*u1)
                if self.option == 'B2':
                    # Disconnected short feather strokes, never six parallel ropes.
                    u0 = clamp(i/10.+age*.36)
                    u1 = clamp(u0+.026)
                    weight *= (.65+.35*math.sin(i*1.7+strand)) if i%3==strand%3 else 0.
                self.soft_line(row, p(u0), p(u1), (15. if self.option=='B1' else 20.)*(.35+.65*math.sin(math.pi*u1)), weight*(1.45 if self.option=='B1' else 1.9))
        for i,row in enumerate(self.motes):
            u = i/11.
            direction = -1. if i%2 else 1.
            drift = max(0.,age-.04)*70.
            p = self.start+(self.end-self.start)*u+self.right*(direction*(10.+i%3*8.+drift))+self.up*(i%4*17.+drift*.5)
            self.soft_dot(row,p,5.+i%3*2.,fade*(.35+.12*(i%3)) if u<=head else 0.)
        self.tick()


def sequence(rig):
    options = os.environ.get('SPARROW_BLINK_FLOW_OPTIONS','B1,B2').split(',')
    report = {'passed':False, 'installed':False, 'native_changed':False, 'studies':[]}
    frame = 1./rig['FPS']
    for option in options:
        assert option in DESIGNS
        rig['switch']('countess'); yield .15
        rig['switch']('sparrow'); yield .6
        rig['case']('Blink_flow_'+option)
        rig['layout']([(700,350),(800,-400),(-500,500)])
        rig['key']('V'); yield 1.75
        pawn = rig['pawn']()
        mesh = pawn.get_editor_property('mesh')
        materials = [mesh.get_material(i) for i in range(mesh.get_num_materials())]
        wings = unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SparrowAscensionWings)
        rig['check'](len(wings)==1,'blink flow begins in actual V transformation')
        rig['aim'](offset=(550,0))
        rig['STATE']['video_clip'] = {'case':'Blink_flow_'+option, 'prefix':'Blink_flow_'+option+'_video', 'cast_time':unreal.GameplayStatics.get_time_seconds(rig['world']()), 'frame_times':[]}
        yield .30
        rig['key']('SpaceBar')
        yield frame
        actors = unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SparrowGoldRoll)
        rig['check'](len(actors)==1 and actors[0].is_teleporting(),'preview uses real transformed Space')
        study = Study(rig,option)
        initial = pawn.get_actor_location()
        captures = [.067,.133,.233,.4]
        positions=[]
        try:
            while study.now()-study.born < .8:
                age = study.now()-study.born
                study.update(age)
                positions.append((pawn.get_actor_location()-initial).length())
                if captures and age>=captures[0]:
                    rig['capture']('Blink_flow_'+option+'_t'+str(round(captures.pop(0)*1000)))
                yield frame
            rig['finish_video_clip']()
            rig['check'](study.committed and abs(positions[-1]-480.)<3.,'blink flow retains native480cm displacement')
            rig['check'](all(d<3. or abs(d-480.)<3. for d in positions),'effects do not interpolate native teleport position')
            rig['check'](mesh.is_visible() and materials==[mesh.get_material(i) for i in range(mesh.get_num_materials())],'blink flow preserves original transformed body materials')
            rig['check'](valid(wings[0]) and not rig['skills']().is_rolling() and not pawn.is_combat_busy(),'same wings and recovered movement after effects')
            rig['check'](study.peak_particles>0,'blink flow has visible live original particles')
            report['studies'].append({'id':option,'description':DESIGNS[option],'peak_particles':study.peak_particles,'positions':positions,'installed':False})
        finally:
            rig['finish_video_clip']()
            study.close()
        rig['check'](not rig['tagged'](str(TAG)) and not study.effects,'blink flow removes transient effect actors')
    report['passed']=True
    (Path(rig['OUT'])/'blink-flow-studies.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
