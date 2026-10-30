"""Preview-only E art directions. Gameplay, native sources and installed FX stay intact."""
import json
import math
import os
import sys
import traceback
import types
from pathlib import Path

import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
sys.path[:0] = [str(ROOT / 'Tools/CharacterPipeline'), str(ROOT / 'Tools/CharacterPipeline/Suites')]
job = {'output': str(OUT), 'profile': str(ROOT / 'Tools/CharacterPipeline/Profiles/countess.json'),
       'fps': int(os.environ.get('SPARROW_QA_FPS', '60')),
       'baseline': str(OUT.parent / 'concept-baseline.json')}
(OUT / 'job.json').write_text(json.dumps(job), encoding='utf-8')
os.environ['CHARACTER_PIPELINE_JOB'] = str(OUT / 'job.json')
REFINED = os.environ.get('COUNTESS_E_CONCEPT_REFINED') == '1'
COMPARE = REFINED and os.environ.get('COUNTESS_E_CONCEPT_COMPARE') == '1'

SHADER = r'''
struct InkFX {
    float hash(float2 p) { return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453); }
    float noise(float2 p) {
        float2 i=floor(p), f=frac(p); f=f*f*(3-2*f);
        return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),
                    lerp(hash(i+float2(0,1)),hash(i+float2(1,1)),f.x),f.y);
    }
    float grain(float2 p) { return noise(p)*.6+noise(p*2.03+9)*.28+noise(p*4.1-3)*.12; }
};
InkFX F;
float age=Clock-SpawnTime;
if(age<0 || age>Duration) return float4(0,0,0,0);
float t=saturate(age/max(Duration,.001));
float2 p=UV*2-1;
float seed=Hit*7.31+Line*3.9;
float n=F.grain(p*float2(13,21)+seed);
float fine=F.noise(p*float2(61,43)+seed);
float3 color=0; float alpha=0;
float fade=smoothstep(0,.008,age)*pow(1-t,.65);

if(Style<.5) {
    // Ragged opaque ink, a torn crimson lip, and sparse steel glints.
    float taper=pow(saturate(1-abs(p.x)),.62);
    float wav=(F.noise(float2(p.x*19+seed,4))-.5)*.09;
    float d=abs(p.y-wav);
    float width=(.075+.17*n)*taper;
    float body=1-smoothstep(width,width+.045,d);
    float lip=(1-smoothstep(.018,.06,abs(d-width*.75)))*taper;
    float dry=smoothstep(.22,.50,n+.12)*body;
    float glint=lip*smoothstep(.72,.88,fine)*pow(1-t,3);
    color=lerp(float3(.018,.003,.009),float3(.22,.004,.020),n)*dry;
    color+=float3(1.1,.017,.055)*lip*(.3+.7*fine);
    color+=float3(1.2,.85,.82)*glint;
    alpha=saturate((dry*.94+lip*.65)*fade);
    // Broken short fibers along the incision, not a second continuous beam.
    float fiber=(1-smoothstep(.035,.08,abs(d-width-.08)))*taper*smoothstep(.62,.82,n);
    color+=float3(.58,.008,.023)*fiber;
    alpha=max(alpha,fiber*fade*.8);
} else if(Style<1.5) {
    // Three faceted shadow daggers converge on the victim from different sides.
    float arrival=saturate(t*2.5);
    float tip=lerp(.48,.015,arrival);
    for(int i=0;i<3;i++) {
        float a=i*2.0944+Hit*.61;
        float2 q=float2(dot(p,float2(cos(a),sin(a))),dot(p,float2(-sin(a),cos(a))));
        float along=q.x-tip;
        float lengthBlade=.60;
        float w=saturate(along/lengthBlade)*.28;
        float body=(1-smoothstep(w,w+.018,abs(q.y)))*step(0,along)*(1-smoothstep(lengthBlade*.72,lengthBlade,along));
        float edge=(1-smoothstep(.009,.028,abs(abs(q.y)-w)))*step(0,along)*(1-smoothstep(.42,.6,along));
        float facet=step(0,q.y)*body;
        color+=float3(.009,.004,.014)*body+float3(.24,.15,.20)*facet;
        color+=float3(.63,.045,.115)*edge*(.55+.45*n);
        alpha=max(alpha,(body+edge*.6)*fade);
    }
    float center=1-smoothstep(.01,.21,length(p*float2(1.1,.9)));
    float burst=smoothstep(.17,.30,t)*(1-smoothstep(.50,.92,t));
    color+=float3(.48,.006,.027)*center*burst*(.3+n);
    alpha=max(alpha,center*burst*.8);
} else if(Style<2.5) {
    // Compact torn impact, blood-red splinters, no cross or circular shock wave.
    float r=length(p*float2(.9,1.15));
    float flow=F.grain(p*5.5+float2(seed+t*1.4,seed-t*2.3));
    float detail=F.grain(p*18+float2(seed,seed-t*3));
    float cloud=(1-smoothstep(.13,.53,saturate(r-.19*sqrt(t))+(flow-.5)*.43));
    cloud*=smoothstep(.17,.58,flow+detail*.30)*pow(1-t,.75);
    float veins=smoothstep(.48,.72,flow)*cloud;
    color=lerp(float3(.012,.003,.010),float3(.32,.009,.037),veins)*cloud;
    color+=float3(.17,.035,.045)*cloud*smoothstep(.53,.68,detail)*pow(1-t,1.6);
    alpha=cloud*.93;
    for(int i=0;i<19;i++) {
        float a=F.hash(float2(i,Hit+8))*6.28318;
        float2 q=float2(dot(p,float2(cos(a),sin(a))),dot(p,float2(-sin(a),cos(a))));
        float speed=.35+F.hash(float2(i+11,Hit))*.45;
        float center=.13+sqrt(t)*speed;
        float len=.025+.07*F.hash(float2(i+4,Hit+13));
        float d=abs(q.x-center)/len;
        float w=(1-saturate(d))*(.015+.025*F.hash(float2(i+7,Hit+2)));
        float shard=(1-smoothstep(w,w+.010,abs(q.y)))*step(d,1);
        float hot=pow(1-t,2)*step(.65,F.hash(float2(i,7)));
        color+=shard*(float3(.52,.008,.031)+float3(.25,.07,.055)*hot);
        alpha=max(alpha,shard*pow(1-t,.6));
    }
    color*=.65+.6*n;
    alpha*=smoothstep(0,.008,age);
} else {
    // Short wounds remain between hits; all six erode together into shadow ash.
    float release=saturate((Clock-ReleaseTime)/.32);
    p.y+=release*(.18+.45*n);
    float taper=pow(saturate(1-abs(p.x)),.65);
    float d=abs(p.y+(n-.5)*.10);
    float lip=(1-smoothstep(.045,.095,d))*taper;
    float shadow=(1-smoothstep(.10,.29,d))*taper;
    float broken=smoothstep(.12,.50,n+(.8-release)*.25);
    float fresh=pow(saturate(1-age/.14),2);
    color=float3(.028,.001,.007)*shadow+float3(.85,.008,.035)*lip*(.55+.45*n);
    color+=float3(.6,.18,.16)*lip*fresh*fine;
    alpha=max(shadow*.82,lip)*broken*smoothstep(0,.01,age)*(1-release);
    color*=1-release*.7;
}
return float4(color*Energy,saturate(alpha));
'''

REFINED_SHADER = SHADER.split('if(Style<.5)')[0] + r'''
// Use the existing Countess texture grain, but keep the cutting silhouette stable.
float tex=saturate(Noise*.65+n*.35);
float taper=pow(saturate(1-abs(p.x)),.72);
float aa=max(fwidth(p.y),.006);
if(Style<.5) {
    float center=(F.noise(float2(p.x*13+seed,7))-.5)*.014;
    float y=p.y-center;
    float d=abs(y);
    float width=(.052+.075*taper);
    float front=-1+2*saturate(age/.032);
    float reveal=1-smoothstep(front-.06,front+.02,p.x);
    float cut=(1-smoothstep(width,width+aa*2,d))*taper*reveal;
    float wash=(1-smoothstep(width*.8,width+.14*taper,d))*taper*reveal;
    float broken=smoothstep(.24,.65,tex);
    float edge=1-smoothstep(.018,.038+aa,abs(y-width*.55));
    edge*=taper*reveal*(.30+.70*broken);
    float filament=(1-smoothstep(.008,.019+aa,abs(y+width*.5)))*taper;
    filament*=smoothstep(.54,.73,tex)*reveal;
    float strikeFade=pow(saturate(1-age/.19),.72);
    float remnant=pow(1-t,.8)*smoothstep(.12,.43,tex-t*.22);
    color=float3(.013,.001,.005)*cut;
    color+=float3(.10,.002,.012)*wash*broken;
    color+=float3(.48,.005,.022)*cut*(.25+.75*tex)*strikeFade;
    color+=float3(1.10,.012,.045)*edge*(.35+.65*strikeFade);
    color+=float3(.39,.004,.020)*filament*strikeFade;
    // A small moving edge highlight; never a full-length white tube.
    float tip=(1-smoothstep(.025,.09,abs(p.x-front+.05)));
    tip*=(1-smoothstep(.012,.045,d))*taper*step(age,.035);
    color+=float3(1.35,.62,.55)*tip;
    alpha=saturate((cut*.90+wash*broken*.42+edge*.6)*remnant);
    for(int i=0;i<5;i++) {
        float r=F.hash(float2(i+6,Hit+Line*6));
        float2 origin=float2(lerp(-.65,.65,r),(i%2==0?1:-1)*.055);
        float move=saturate((age-.025)/.20);
        float2 q=p-origin-float2((r-.5)*.20,(i%2==0?1:-1)*(.10+.15*r))*move;
        float piece=(1-smoothstep(.5,1,length(q/float2(.025+.026*r,.010))));
        piece*=smoothstep(.015,.04,age)*pow(1-move,1.4);
        color+=float3(.55,.008,.025)*piece;
        alpha=max(alpha,piece*.8);
    }
    alpha*=smoothstep(0,.006,age);
} else {
    // The marks stay on the victim. Only their detached ash moves during expiry.
    float release=saturate((Clock-ReleaseTime)/.48);
    float y=p.y+(F.noise(float2(p.x*18+seed,3))-.5)*.018;
    float d=abs(y);
    float incision=(1-smoothstep(.022,.048+aa,d))*taper;
    float cavity=(1-smoothstep(.065,.11+aa,d))*taper;
    float stain=(1-smoothstep(.10,.24,d))*taper*smoothstep(.16,.70,tex);
    float lip=(1-smoothstep(.013,.032+aa,abs(d-.056)))*taper;
    float fresh=pow(saturate(1-age/.12),.8);
    float sweep=-1+2*saturate(age/.035);
    float reveal=1-smoothstep(sweep-.045,sweep+.02,p.x);
    float erosion=smoothstep(release*.95-.10,release*.95+.10,tex);
    float endPulse=(1-smoothstep(0,.13,release))*step(ReleaseTime,Clock);
    color=float3(.009,.001,.004)*cavity+float3(.055,.001,.008)*stain;
    color+=float3(.57,.006,.025)*lip*(.5+.5*tex)*(.65+fresh*.5+endPulse*.18);
    color+=float3(.85,.12,.10)*incision*fresh*(.3+.7*tex);
    color*=reveal*erosion*(1-release*.80);
    alpha=max(cavity*.92,lip*.9)+stain*.20;
    alpha*=reveal*erosion*(1-release)*smoothstep(0,.006,age);
    for(int i=0;i<7;i++) {
        float r=F.hash(float2(i+12,Hit+5));
        float2 origin=float2(lerp(-.78,.78,r),(r-.5)*.10);
        float2 drift=float2((r-.5)*.25,-(.24+.26*r))*release;
        float2 q=p-origin-drift;
        float piece=(1-smoothstep(.55,1,length(q/float2(.028,.014))));
        piece*=smoothstep(.02,.18,release)*pow(1-release,1.3);
        color+=lerp(float3(.28,.004,.014),float3(.008,.001,.003),release)*piece;
        alpha=max(alpha,piece*.8);
    }
}
return float4(color*Energy,saturate(alpha));
'''


def author():
    lib = unreal.MaterialEditingLibrary
    folder = '/Game/TopDown/Characters/Countess/FXConcepts'
    name = 'M_EConceptsAD_Refined_20261021' if REFINED else 'M_EConcepts_20261017'
    mat = unreal.load_asset(folder + '/' + name)
    if mat is None:
        mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    lib.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided', True)
    def node(kind, **props):
        expr = lib.create_material_expression(mat, getattr(unreal, 'MaterialExpression' + kind))
        for key, value in props.items():
            expr.set_editor_property(key, value)
        return expr
    shader = node('Custom', code=REFINED_SHADER if REFINED else SHADER, output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    inputs = ['UV', 'Clock', 'SpawnTime', 'Duration', 'Energy', 'Style', 'Hit', 'Line', 'ReleaseTime']
    if REFINED:
        inputs.append('Noise')
    pins = []
    for name in inputs:
        pin = unreal.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    shader.set_editor_property('inputs', pins)
    for name in inputs:
        if name == 'Noise':
            uv = node('TextureCoordinate', u_tiling=2.8, v_tiling=.7)
            texture = node('TextureSample', texture=unreal.load_asset('/Game/ParagonCountess/FX/Textures/Tile/Noise/T_TilingNoise12'))
            assert lib.connect_material_expressions(uv, '', texture, 'UVs')
            assert lib.connect_material_expressions(texture, 'R', shader, name)
            continue
        expr = node('TextureCoordinate') if name == 'UV' else node('Time') if name == 'Clock' else node('ScalarParameter', parameter_name=name, default_value=1 if name in ('Energy', 'Duration') else 0)
        assert lib.connect_material_expressions(expr, '', shader, name)
    for prop, rgba in [(unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True, True, True, False)),
                       (unreal.MaterialProperty.MP_OPACITY, (False, False, False, True))]:
        mask = node('ComponentMask', r=rgba[0], g=rgba[1], b=rgba[2], a=rgba[3])
        assert lib.connect_material_expressions(shader, '', mask, lib.get_material_expression_input_names(mask)[0])
        assert lib.connect_material_property(mask, '', prop)
    lib.recompile_material(mat)
    assert unreal.EditorAssetLibrary.save_loaded_asset(mat, False)
    (OUT / 'concept-material.json').write_text(json.dumps({'asset': mat.get_path_name(), 'preview_only': True, 'refined': REFINED}), encoding='utf-8')
    return mat


try:
    for command in ('r.Streaming.PoolSize 512', 'r.Shadow.Virtual.MaxPhysicalPages 1024'):
        unreal.SystemLibrary.execute_console_command(None, command)
    MATERIAL = author()
    ORIGINAL_MATERIAL = unreal.load_asset('/Game/TopDown/Characters/Countess/FXConcepts/M_EConcepts_20261017') if COMPARE else MATERIAL
    if ORIGINAL_MATERIAL is None:
        raise RuntimeError('The original concept material is unavailable')
except Exception:
    (OUT / 'author-error.txt').write_text(traceback.format_exc(), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
    raise

from context import fps
from training_room_verify import TrainingRunner, select
from countess_w_speed_compare import settle_switch, statue
from sparrow_runtime import valid

NAMES = ['ink', 'daggers', 'rupture', 'wounds']


def concept(style, refined=None):
    refined = REFINED if refined is None else refined
    def run(rig):
        yield from select(rig, 'countess')
        unreal.SystemLibrary.execute_console_command(rig.world, 'Countess.Skills.IgnoreCooldowns 1')
        rig.check(rig.component.is_flurry_prototype_enabled(), 'existing body and shadow E is active')
        target = statue(rig, 0, 145)
        rig.aim_target(target)
        rig.runner.preview_style = style
        rig.runner.preview_refined = refined
        rig.runner.cut_count = 0
        rig.runner.seen = set()
        rig.runner.first_cut_time = None
        rig.runner.preview_actors = []
        yield .2
        start = rig.now
        yield from rig.skill_key('E', target.get_actor_location())
        frames, shadow_seen = [], False
        capture_at = .05
        while rig.now - start < 1.85:
            if not shadow_seen:
                shadow_seen = any(a.actor_has_tag('CountessEFlurryShadow') for a in unreal.GameplayStatics.get_all_actors_of_class(rig.world, unreal.Actor))
            if rig.now - start >= capture_at:
                frames.append({'elapsed': rig.now - start, 'health': rig.health(target)})
                rig.snapshot()
                label = NAMES[style] + ('-refined' if refined else '-rough') if COMPARE else NAMES[style]
                yield rig.capture('E-' + label + '-' + str(len(frames) - 1).zfill(2))
                capture_at += .05
            else:
                yield 1 / fps
        rig.check(rig.runner.cut_count == 6, 'all six real hit FX were replaced by the selected preview')
        rig.check(rig.health(target) == 55, 'preview preserves six hits and total damage 45')
        rig.check(shadow_seen, 'existing animated shadow still accompanies the caster')
        rig.check(not any(valid(a) for a in rig.runner.preview_actors), 'preview surfaces naturally expire')
        rig.assert_recovered()
        rig.data.update(style=NAMES[style], refined=refined, preview_only=True, frames=frames, camera='approved_gameplay_quarter_view', damage=45, hits=6)
        rig.runner.preview_style = None
    return run


class ConceptRunner(TrainingRunner):
    def __init__(self):
        super().__init__()
        self.cases = [('E_concept_' + name, concept(i)) for i, name in enumerate(NAMES)]
        requested = os.environ.get('COUNTESS_E_CONCEPT_STYLES')
        if requested:
            self.cases = [c for i, c in enumerate(self.cases) if str(i) in requested.split(',')]
        elif REFINED:
            self.cases = [('E_concept_' + NAMES[i], concept(i)) for i in (0, 3)]
        if COMPARE:
            self.cases = [('E_concept_' + NAMES[i] + suffix, concept(i, refined))
                          for i in (0, 3) for suffix, refined in (('_rough', False), ('_refined', True))]
        self.report_name = 'e-concepts.json'
        self.report.update(suite='E_effect_concept_comparison', installed_skill_changed=False, temporary_pie_material_override=True)
        self.preview_style = None
        self.seen = set()
        self.cut_count = 0

    def case_generator(self, factory):
        self.rig.switch = types.MethodType(settle_switch, self.rig)
        yield from super().case_generator(factory)

    def update_preview(self):
        if self.preview_style is None or self.rig is None:
            return
        style = self.preview_style
        refined = self.preview_refined
        for actor in unreal.GameplayStatics.get_all_actors_of_class(self.rig.world, unreal.Actor):
            if not actor.actor_has_tag('CountessETargetCuts') or actor.get_path_name() in self.seen:
                continue
            self.seen.add(actor.get_path_name())
            hit = self.cut_count
            self.cut_count += 1
            self.preview_actors.append(actor)
            meshes = actor.get_components_by_class(unreal.StaticMeshComponent)
            spawn = meshes[0].get_material(0).get_scalar_parameter_value('SpawnTime')
            if self.first_cut_time is None:
                self.first_cut_time = spawn
            release = self.first_cut_time + (.87 if refined else .84)
            duration = [.17, .19, .29, release + .32 - spawn][style]
            if refined:
                duration = .25 if style == 0 else release + .48 - spawn
            actor.set_life_span(duration + .09)
            for line, mesh in enumerate(meshes):
                if line == 1 and style in (1, 2, 3):
                    mesh.set_visibility(False, False)
                    continue
                dynamic = mesh.create_dynamic_material_instance(0, MATERIAL if refined or not COMPARE else ORIGINAL_MATERIAL)
                for key, value in {'SpawnTime': spawn + (line * (.045 if refined else .025)), 'Duration': duration, 'Energy': 1.0 if line == 0 else (.60 if refined else .65),
                                   'Style': style, 'Hit': hit, 'Line': line, 'ReleaseTime': release}.items():
                    dynamic.set_scalar_parameter_value(key, value)
                if style == 0:
                    if refined:
                        length = (1.72 if hit < 4 else 1.98) * (1.0 if line == 0 else .80)
                        mesh.set_relative_scale3d(unreal.Vector(length, .80, 1))
                    else:
                        mesh.set_relative_scale3d(unreal.Vector(1.65 if hit < 4 else 1.95, .90, 1))
                elif style == 1:
                    mesh.set_relative_scale3d(unreal.Vector(2.15, 2.15, 1))
                    mesh.set_relative_rotation(unreal.Rotator(), False, False)
                    mesh.set_relative_location(unreal.Vector(0, 0, 0), False, False)
                elif style == 2:
                    size = 1.90 if hit < 4 else 2.20
                    mesh.set_relative_scale3d(unreal.Vector(size, size, 1))
                    mesh.set_relative_rotation(unreal.Rotator(yaw=hit * 31), False, False)
                    mesh.set_relative_location(unreal.Vector((hit % 2 * 2 - 1) * 10, (hit % 3 - 1) * 10, 0), False, False)
                else:
                    if refined:
                        mesh.set_relative_scale3d(unreal.Vector(.76 + (hit % 3) * .06, .80, 1))
                        mesh.set_relative_rotation(unreal.Rotator(yaw=[-48, 42, -37, 51, -44, 39][hit]), False, False)
                        mesh.set_relative_location(unreal.Vector([-10, 11, -12, 10, -8, 9][hit], [-16, -11, 1, 6, 18, 23][hit], hit * .15), False, False)
                    else:
                        mesh.set_relative_scale3d(unreal.Vector(.78 + (hit % 3) * .08, .60, 1))
                        mesh.set_relative_rotation(unreal.Rotator(yaw=[-50, -30, 48, 66, -8, 12][hit]), False, False)
                        mesh.set_relative_location(unreal.Vector([0, 9, -10, 6, -6, 4][hit], [-17, 15, 8, -9, 0, 20][hit], hit * .15), False, False)

    def tick(self, delta):
        try:
            self.update_preview()
        except Exception as error:
            self.finish(error)
            return
        super().tick(delta)


runtime = ConceptRunner()
runtime.start()
