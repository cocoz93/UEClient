"""Two PIE-only wind additions over the restored pre-reforge A.

The native FeatherRing pair, short arrow, crackle and three hit flashes remain
visible. This module never changes the real projectile or production assets.
Run author(out), then sequence(rig) after applying the separately audited A
rollback. Only Previews/ATempest20261024 receives saved materials.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import runpy

import unreal


BASE = runpy.run_path(str(Path(__file__).with_name('sparrow_orbit_arsenal_studies.py')))
ROOT = '/Game/TopDown/Characters/Sparrow/Previews/ATempest20261024'
OPTIONS = ('AT1', 'AT2')
DESIGNS = {
    'AT1': {'label': '압축 나선류',
            'shape': '기존 회전부 뒤에서 좁아지는 반투명 나선면과 끊어진 백금 바람결',
            'precast': '활 앞에서 작은 나선이 빠르게 감기며 압축되고 발사 때 투사체로 이어짐'},
    'AT2': {'label': '갈라지는 태풍',
            'shape': '기존 회전부 바깥의 넓고 찢어진 바람층과 뒤로 흩어지는 짧은 풍편',
            'precast': '활 앞의 두 큰 바람날이 반대로 교차하고 발사 때 한 덩어리로 감겨 나감'},
}
FLOW = '/Game/ParagonSparrow/FX/Textures/Tile/Energy/Plasma/T_Sparrow_Poster_Tendrils_v2_Seamless'

SHADER = r'''
const float PI=3.14159265;
const int Variant=VARIANT_NUMBER;
float x=UV.x,y=(UV.y-.5)*2.;
float mask=smoothstep(.025,.20,x)*(1.-smoothstep(.84,.99,x));
float radius=lerp(.10,.66,pow(saturate(x),.72));
float grain=Texture2DSample(Flow,FlowSampler,UV*float2(2.3,2.9)+float2(-Age*.93,Age*.21)).r;
float detail=Texture2DSample(Flow,FlowSampler,UV*float2(5.8,4.2)+float2(Age*.62,-Age*.17)).g;
float intensity=0.,rim=0.,wisps=0.;
// Less than one spatial turn per ribbon; front-facing sectors break the
// uniform spring silhouette. Broad, eroded surfaces supply wind volume.
for(int i=0;i<4;i++) {
    if(Variant==1 && i==3)continue;
    float phase=x*(Variant==1?5.8:4.1)-Age*(Variant==1?10.5:8.0)+i*(Variant==1?2.0944:1.5708);
    phase+=sin(x*10.+i*2.7-Age*2.2)*.18;
    float nearSide=.5+.5*cos(phase);
    float path=sin(phase)*radius;
    path+=(grain-.5)*(Variant==1?.045:.11)*x;
    float width=Variant==1 ? .055+.095*nearSide : .11+.19*nearSide;
    width*=.72+.28*sin(x*11.+i*1.7-Age*1.8);
    float distance=abs(y-path);
    float inside=1.-smoothstep(width*.22,width,distance);
    float edge=exp(-abs(distance-width*.65)*(Variant==1?100.:70.));
    float cut=sin(x*23.+y*9.-Age*5.+i*3.1)*.19+sin(x*61.-y*16.+i)*.10;
    float flowValue=saturate(.16+grain*.60+detail*.35+cut);
    float broken=Variant==1 ? .48+flowValue*.52 : smoothstep(.23,.62,flowValue);
    float depth=smoothstep(.13,.72,nearSide)*(.35+.65*nearSide);
    intensity+=inside*broken*depth;
    rim+=edge*broken*depth*(Variant==1?.32:.19);
    wisps+=inside*flowValue*depth*.10;
}
// Torn, slanted streamlets emphasize forward travel instead of closed coils.
for(int j=0;j<5;j++) {
    float phase=x*4.8-Age*10.+j*1.2566;
    float path=sin(phase)*(radius+.07);
    float stream=exp(-abs(y-path)*140.);
    float dash=pow(saturate(sin(x*19.-Age*12.+j*2.)),5.);
    rim+=stream*dash*smoothstep(.1,.8,cos(phase))*.25;
}
float trailing=smoothstep(.09,.28,x);
float alpha=saturate((intensity*(Variant==1?.45:.54)+rim*.42+wisps)*mask*Strength*trailing);
float3 gold=float3(1.8,1.04,.23),white=float3(2.7,2.35,1.55);
float3 color=gold*(intensity*(.27+grain*.19)+wisps)+white*(rim+intensity*.09);
return float4(color,alpha);
'''


def write(out, name, value):
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out)/name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def hashes():
    project = Path(__file__).resolve().parents[2]
    paths = ['Source/LearnTopDown/SparrowAscension.cpp', 'Source/LearnTopDown/SparrowAscension.h',
             'Source/LearnTopDown/SparrowSkillComponentExtras.cpp',
             'Content/TopDown/Characters/Sparrow/Materials/M_SparrowGearFeather.uasset']
    return {p: hashlib.sha256((project/p).read_bytes()).hexdigest() for p in paths}


def author(out):
    before = hashes()
    lib = unreal.MaterialEditingLibrary
    texture = unreal.load_asset(FLOW)
    assert texture, FLOW
    assets = []
    for option in OPTIONS:
        path = ROOT+'/M_'+option
        material = unreal.load_asset(path)
        if material is None:
            folder, name = path.rsplit('/', 1)
            material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                name, folder, unreal.Material, unreal.MaterialFactoryNew())
        lib.delete_all_material_expressions(material)
        material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
        material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
        material.set_editor_property('two_sided', True)
        def node(kind, **props):
            result = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression'+kind))
            for key, value in props.items(): result.set_editor_property(key, value)
            return result
        shader = node('Custom', code=SHADER.replace('VARIANT_NUMBER', option[-1]),
                      output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
        sources = {'UV': node('TextureCoordinate'), 'Flow': node('TextureObject', texture=texture),
                   'Age': node('ScalarParameter', parameter_name='Age', default_value=.3),
                   'Strength': node('ScalarParameter', parameter_name='Strength', default_value=1.)}
        inputs = []
        for name in sources:
            item = unreal.CustomInput(); item.set_editor_property('input_name', name); inputs.append(item)
        shader.set_editor_property('inputs', inputs)
        for name, value in sources.items(): assert lib.connect_material_expressions(value, '', shader, name)
        for prop, rgba in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True,True,True,False)),
                           (unreal.MaterialProperty.MP_OPACITY, (False,False,False,True))):
            mask = node('ComponentMask', r=rgba[0], g=rgba[1], b=rgba[2], a=rgba[3])
            assert lib.connect_material_expressions(shader, '', mask, '')
            assert lib.connect_material_property(mask, '', prop)
        lib.recompile_material(material)
        assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
        assets.append(path)
    assert before == hashes(), 'author changed production A'
    result = {'passed': True, 'preview_materials': assets, 'production_changed': False, 'revision':2,
              'requires_restored_FeatherRing_pair': True, 'designs': DESIGNS}
    write(out, 'a-tempest-author.json', result)
    return result


class Study(BASE['Study']):
    def __init__(self, rig, option):
        super().__init__(rig, option)
        self.materials['tempest'] = unreal.load_asset(ROOT+'/M_'+option)
        assert self.materials['tempest']
        self.sheets = [self.plane('tempest', 'wind_'+str(i)) for i in range(3)]
        for row in self.sheets:
            row['actor'].set_life_span(8.)
        self.release = None
        self.native_rings = []
        self.last_spark = -100.
        self.started = self.now()

    def observe_arrow(self, arrow):
        self.arrow_actor = arrow
        self.release = self.now()-self.started
        self.native_rings = [c for c in arrow.get_components_by_class(unreal.StaticMeshComponent)
                             if c.get_name().startswith('FeatherRing')]
        self.rig['check'](len(self.native_rings) == 2,
                          'A tempest overlays the restored native pair, not the rejected Tsunami blades')
        for component in arrow.get_components_by_class(unreal.StaticMeshComponent):
            self.native_snapshot.append((component, tuple(component.get_material(i)
                                        for i in range(component.get_num_materials()))))
        self.forward = arrow.get_flight_direction()
        self.right = arrow.get_actor_right_vector()
        self.pulse('muzzle', ('Airglow', 'Sparks'), arrow.get_actor_location(),
                   unreal.MathLibrary.make_rot_from_x(self.forward), (.65,.65,.65), .22, 2.)
        self.events.append({'event': 'native_arrow_released', 'time': self.release})

    def surface(self, row, center, direction, length, width, age, strength, tilt=0.):
        camera = unreal.GameplayStatics.get_player_camera_manager(self.rig['world'](), 0).get_camera_location()
        normal = camera-center
        rotation = unreal.MathLibrary.make_rot_from_xz(direction, normal)
        if tilt:
            rotation = unreal.MathLibrary.compose_rotators(unreal.Rotator(roll=tilt), rotation)
        row['actor'].set_actor_location(center, False, True)
        row['actor'].set_actor_rotation(rotation, True)
        row['mesh'].set_world_scale3d(unreal.Vector(length/100., width/100., 1.))
        row['mid'].set_scalar_parameter_value('Age', age)
        row['mid'].set_scalar_parameter_value('Strength', strength)

    def update(self, elapsed):
        f = self.forward
        if self.release is None:
            origin = self.rig['skills']().get_arrow_origin()
            f = self.rig['pawn']().get_actor_forward_vector()
            self.forward = f
            progress = BASE['_smooth'](elapsed/.36)
            # Wind gathers in front of the real bow. It never draws a floor fog.
            center = origin+f*(35.+progress*25.)
            length, width = (100.+70.*progress, 90.+80.*progress)
            if self.option == 'AT2': length, width = 125.+65.*progress, 145.+100.*progress
            for index, row in enumerate(self.sheets):
                self.surface(row, center-f*index*16., f, length, width,
                             elapsed*1.15+index*.43, progress*(.90 if index == 0 else .25), index*67.)
        elif BASE['_valid'](self.arrow_actor):
            arrow = self.arrow_actor
            f = arrow.get_flight_direction()
            p = arrow.get_actor_location()+f*30.
            length = 180. if self.option == 'AT1' else 225.
            width = 170. if self.option == 'AT1' else 245.
            for index, row in enumerate(self.sheets):
                self.surface(row, p-f*(length*.38+index*12.), f, length, width,
                             elapsed+index*.43, 1.05 if index == 0 else .30, index*67.)
            if self.now()-self.last_spark >= (.22 if self.option == 'AT1' else .16):
                self.last_spark = self.now()
                phase = elapsed*12.
                radial = self.right*math.cos(phase)+self.up*math.sin(phase)
                q = p-f*55.+radial*(45. if self.option == 'AT1' else 70.)
                self.pulse('muzzle', ('Sparks',), q, unreal.MathLibrary.make_rot_from_x(f*-1.),
                           (.30,.30,.30), .22, 1.8)
        else:
            for row in self.sheets: row['mid'].set_scalar_parameter_value('Strength', 0.)
        self.tick()


def sequence(rig):
    before = hashes()
    options = [x.strip() for x in os.environ.get('SPARROW_A_TEMPEST', ','.join(OPTIONS)).split(',') if x.strip()]
    assert options and all(x in OPTIONS for x in options), options
    now = lambda: unreal.GameplayStatics.get_time_seconds(rig['world']())
    rows = []
    for option in options:
        rig['switch']('countess'); yield .2
        rig['switch']('sparrow'); yield .7
        rig['cmd']('CountessComboQA.FlushInput')
        prefix = 'ATempest_'+option
        rig['case'](prefix)
        targets = rig['layout']([(340,0),(600,0),(600,350)]); yield .2
        original_health = [rig['health'](t) for t in targets]
        study = Study(rig, option)
        started = now(); study.started = started
        seen = set(); frames = [.20,.36,.65,1.30,2.20,3.60]
        try:
            rig['use']('A', targets[0])
            rig['STATE']['video_clip'] = {'case':prefix, 'prefix':prefix+'_video',
                                         'cast_time':started, 'frame_times':[]}
            while now()-started < 4.4:
                for arrow in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowGearArrow):
                    if arrow.get_owner() == rig['pawn']() and arrow.get_path_name() not in seen:
                        seen.add(arrow.get_path_name()); study.observe_arrow(arrow)
                elapsed = now()-started
                study.update(elapsed)
                if frames and elapsed >= frames[0]:
                    rig['capture'](prefix+'_t'+str(round(frames.pop(0)*100)).zfill(3))
                yield 1/rig['FPS']
            rig['finish_video_clip']()
            damage = [a-rig['health'](t) for a,t in zip(original_health,targets)]
            rig['check'](len(seen) == 1, option+' preserves exactly one native A projectile')
            rig['check'](BASE['_valid'](study.arrow_actor) and study.arrow_actor.is_piercing()
                         and abs(study.arrow_actor.get_flight_speed()-160.) < .01,
                         option+' preserves 160 cm/s and piercing')
            rig['check'](all(abs(d-90.) < .03 for d in damage[:2]) and abs(damage[2]) < .03,
                         option+' preserves 90 once per lane target and lateral exclusion')
            rig['check'](all(c.is_visible() for c in study.native_rings), option+' keeps the native cutting pair visible')
            rig['recovered']()
            row = {'id':option, **DESIGNS[option], 'video_prefix':prefix+'_video', 'duration':4.4,
                   'installed':False, 'damage':damage, 'events':study.events,
                   'visual_review':'pending actual PIE frames'}
        finally:
            rig['finish_video_clip']()
            failures = study.close()
        rig['check'](not failures and not study.planes, option+' preserves native materials and removes all preview planes')
        rows.append(row)
        write(rig['OUT'], 'a-tempest-studies.json', {'passed':len(rows)==len(options), 'studies':rows,
              'production_changed':False, 'production_rollback_required':True})
    rig['check'](before == hashes(), 'A tempest previews preserve production A source and native material')
