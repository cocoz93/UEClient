"""Actual-world E/A studies plus four authored Sparrow mobility animations.

Only AnimSequence assets under Previews/Fresh20261022 are saved. E/A changes
are instance-local overlays driven by native arrows/hits. Mobility previews
move collisionless proxies, never the player, and are not installed abilities.
Run author(out) before PIE; sequence(rig) plugs into new_skills_probe unchanged.
"""
import json
import math
import os
from pathlib import Path
import runpy

import unreal


_PARTICLES = runpy.run_path(str(Path(__file__).with_name('sparrow_e_texture_studies.py')))
ParticleStudy, _valid = _PARTICLES['Study'], _PARTICLES['_valid']
_BOW = runpy.run_path(str(Path(__file__).with_name('sparrow_bow_audit.py')))
FOLDER = '/Game/TopDown/Characters/Sparrow/Previews/Fresh20261022'
ANIMS = '/Game/ParagonSparrow/Characters/Heroes/Sparrow/Animations/'
MESH = '/Game/ParagonSparrow/Characters/Heroes/Sparrow/Skins/Rogue/Meshes/Sparrow_Rogue'
ECHO = '/Game/TopDown/Characters/Sparrow/Materials/M_SparrowAscensionEcho'
PLASMA_TEXTURE = '/Game/ParagonSparrow/FX/Textures/Energy/T_Plasma_Wisps'
PLASMA_PREVIEW = FOLDER + '/M_SparrowFreshPlasma'
PLASMA_RELEASE = '/Game/TopDown/Characters/Sparrow/Materials/M_SparrowReleaseWisps'
OPTIONS = ('E7', 'E8', 'E9', 'A3', 'A4', 'A5', 'M6', 'M7', 'M8', 'M9')
DESIGNS = {
    'E7': {'label': '황금 깃불 쇄도', 'description': '넓게 갈라진 원본 화염편이 활에서 접혀 나가고 짧은 금빛 불꽃 몸체로 모이는 연사'},
    'E8': {'label': '백금 가속탄', 'description': '백금색 입자 흐름에 두 갈래 짧은 추진 불꽃, 미세한 불티가 빠르게 뒤로 흩어지는 연사'},
    'E9': {'label': '분쇄 파편탄', 'description': '원본 곡면 파편이 화살 주변 세 지점에 불규칙하게 붙고 명중에서 작은 파편 다발로 터지는 연사'},
    'A3': {'label': '절삭 불꽃 꼬리', 'description': '복원된 작은 톱날 뒤로 두 개의 굵은 불꽃 흐름과 지속적인 절삭 불티'},
    'A4': {'label': '나선 파편 꼬리', 'description': '톱날 후방의 금빛 곡면 파편이 엇갈린 두 나선을 이루고 명중에서 옆으로 찢어짐'},
    'A5': {'label': '백금 압축 분쇄', 'description': '짧고 응축된 백금 추진 몸체와 일정 간격의 금빛 파편; 접촉에는 세 번의 절삭 불티'},
    'M6': {'label': '전진 도약', 'description': '점프 준비·정점·착지 포즈를 재조합한 전방 340cm 도약', 'duration': .70, 'distance': 340., 'height': 58.},
    'M7': {'label': '측면 낮은 회피', 'description': '좌측 이동·점프 정점·정지를 보간한 낮은 측면 280cm 회피', 'duration': .60, 'distance': 280., 'height': 17.},
    'M8': {'label': '후방 도약', 'description': '정면을 유지하며 뒤로 270cm 물러나는 도약, 금빛 잔상 두 개', 'duration': .70, 'distance': 270., 'height': 48.},
    'M9': {'label': '빠른 백스텝', 'description': '후진 시작·후진·정지 포즈를 압축한 지면 220cm 이동', 'duration': .60, 'distance': 220., 'height': 0.},
}

# Each node is (normalized output time, authored native animation, source
# fraction). New clips blend local joint transforms between these key poses.
MOTION_KEYS = {
    'M6': ((0., 'Jump_Start_TravelMode', 0.), (.18, 'Jump_Start_TravelMode', 1.),
           (.48, 'Jump_Apex_TravelMode', .5), (.73, 'Jump_Land_TravelMode', .18),
           (1., 'Jump_Recovery_TravelMode', 1.)),
    'M7': ((0., 'Jog_Left_Start', 0.), (.22, 'Jog_Left_Start', .48),
           (.48, 'Jump_Apex_TravelMode', .25), (.72, 'Jog_Left_Stop', .3),
           (1., 'Jog_Left_Stop', 1.)),
    'M8': ((0., 'Jump_Start', 0.), (.20, 'Jump_Start', 1.),
           (.47, 'Jump_Apex', .38), (.74, 'Jump_Land', .22),
           (1., 'Jump_Recovery', 1.)),
    'M9': ((0., 'Jog_Bwd_Start', 0.), (.22, 'Jog_Bwd_Start', .65),
           (.50, 'Jog_Bwd', .30), (.74, 'Jog_Bwd_Stop', .18),
           (1., 'Jog_Bwd_Stop', 1.)),
}


def _selected():
    values = [s.strip() for s in os.environ.get('SPARROW_FRESH_OPTIONS', ','.join(OPTIONS)).split(',') if s.strip()]
    assert values and all(s in OPTIONS for s in values), values
    return values


def _write(out, name, report):
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out) / name).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


def _smooth(value):
    value = max(0., min(1., value))
    return value * value * (3. - 2. * value)


def _mix(a, b, alpha):
    return a * (1. - alpha) + b * alpha


def _rotation_mix(a, b, alpha):
    qa, qb = (a.x, a.y, a.z, a.w), (b.x, b.y, b.z, b.w)
    sign = -1. if sum(x*y for x, y in zip(qa, qb)) < 0. else 1.
    q = [x*(1.-alpha) + y*alpha*sign for x, y in zip(qa, qb)]
    length = math.sqrt(sum(x*x for x in q))
    assert length > .001
    return unreal.Quat(*(x/length for x in q))


def _author_plasma(path, tint, gain):
    """Preserve the original SubUV alpha silhouette and red-channel lighting.

    Read-only graph/PNG audit confirmed that A is the sparse flame silhouette,
    R is lighting, and B is 255 in 89.60 percent of the atlas. RGB/max is not an
    opacity source. Particle RGB is omitted only to permit neutral platinum.
    """
    assert path in (PLASMA_PREVIEW, PLASMA_RELEASE), path
    lib = unreal.MaterialEditingLibrary
    material = unreal.load_asset(path)
    if material is None:
        folder, name = path.rsplit('/', 1)
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    assert isinstance(material, unreal.Material), path
    lib.delete_all_material_expressions(material)
    for key,value in {'blend_mode':unreal.BlendMode.BLEND_TRANSLUCENT,
                      'shading_model':unreal.MaterialShadingModel.MSM_UNLIT,
                      'two_sided':True,'used_with_particle_sprites':True}.items():
        material.set_editor_property(key,value)
    def node(kind, **properties):
        item=lib.create_material_expression(material,getattr(unreal,'MaterialExpression'+kind))
        for key,value in properties.items():
            item.set_editor_property(key,value)
        return item
    def wire(a,b,pin,output=''):
        assert lib.connect_material_expressions(a,output,b,pin)
    custom=node('Custom',output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4,code='''
// Match the audited source graph: SubUV.A supplies shape, SubUV.R supplies
// internal lighting. No disc mask, RGB opacity, or opaque sprite background.
float detail = pow(saturate(TextureAlpha), 0.85);
float life = sqrt(saturate(ParticleAlpha));
float opacity = saturate(detail * life * OpacityGain);
float3 color = Tint.rgb * (0.35 + 1.10 * saturate(TextureRed));
return float4(color, opacity);
''')
    pins=[]
    for key in ('TextureRed','TextureAlpha','ParticleAlpha','Tint','OpacityGain'):
        pin=unreal.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
    custom.set_editor_property('inputs',pins)
    source=node('ParticleSubUV',texture=unreal.load_asset(PLASMA_TEXTURE))
    wire(source,custom,'TextureRed','R')
    wire(source,custom,'TextureAlpha','A')
    wire(node('ParticleColor'),custom,'ParticleAlpha','A')
    wire(node('VectorParameter',parameter_name='Tint',default_value=unreal.LinearColor(*tint,1.)),custom,'Tint')
    wire(node('ScalarParameter',parameter_name='OpacityGain',default_value=gain),custom,'OpacityGain')
    for prop,channels in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR,(True,True,True,False)),
                          (unreal.MaterialProperty.MP_OPACITY,(False,False,False,True))):
        mask=node('ComponentMask',r=channels[0],g=channels[1],b=channels[2],a=channels[3])
        wire(custom,mask,'')
        assert lib.connect_material_property(mask,'',prop)
    lib.recompile_material(material)
    assert unreal.EditorAssetLibrary.save_loaded_asset(material,False)
    return path


def audit_plasma(out):
    """Export the unmodified flipbook and exact source graph connections."""
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    texture=unreal.load_asset(PLASMA_TEXTURE)
    task=unreal.AssetExportTask()
    task.object=texture;task.filename=str(out/'T_Plasma_Wisps.png')
    task.automated=True;task.prompt=False;task.replace_identical=True
    task.exporter=unreal.TextureExporterPNG()
    exported=unreal.Exporter.run_asset_export_task(task)
    assert exported,task.filename
    lib=unreal.MaterialEditingLibrary
    rows=[]
    for path in ('/Game/ParagonSparrow/FX/Materials/Energy/Plasma/M_Plasma_v5_Flipbook2',
                 _PARTICLES['WHITE_WISPS'],
                 '/Game/ParagonSparrow/FX/Materials/Heroes/Sparrow/Abilities/M_ShockwaveFlameSparrow'):
        material=unreal.load_asset(path);assert material,path
        row={'material':path,'blend_mode':str(material.get_editor_property('blend_mode')),'properties':{},'nodes':[]}
        for name,prop in (('opacity',unreal.MaterialProperty.MP_OPACITY),('emissive',unreal.MaterialProperty.MP_EMISSIVE_COLOR)):
            source=lib.get_material_property_input_node(material,prop)
            row['properties'][name]={'node':source.get_name() if source else None,
                                     'output':lib.get_material_property_input_node_output_name(material,prop)}
        for node in lib.get_material_expressions(material):
            item={'name':node.get_name(),'class':node.get_class().get_name(),'inputs':[]}
            for source in lib.get_inputs_for_material_expression(material,node):
                if source:
                    item['inputs'].append({'source':source.get_name(),
                        'output':str(lib.get_input_node_output_name_for_material_expression(node,source))})
            for field in ('parameter_name','default_value','texture','const_a','const_b','const_exponent','const_base'):
                try:
                    value=node.get_editor_property(field)
                    item[field]=value.get_path_name() if isinstance(value,unreal.Object) else str(value)
                except Exception:
                    pass
            row['nodes'].append(item)
        rows.append(row)
    report={'passed':True,'read_only':True,'source_assets_saved':False,
            'texture':{'export':task.filename,'srgb':texture.get_editor_property('srgb'),
                       'compression':str(texture.get_editor_property('compression_settings'))},'graphs':rows}
    _write(out,'plasma-readonly-audit.json',report)
    return report


def author_fx(out):
    """Only the new study material; does not regenerate motion clips."""
    source=unreal.load_asset('/Game/ParagonSparrow/FX/Materials/Energy/Plasma/M_Plasma_v5_Flipbook2')
    white=unreal.load_asset(_PARTICLES['WHITE_WISPS'])
    lib=unreal.MaterialEditingLibrary
    actual=[]
    for material in (source,white):
        assert material
        textures=[asset.get_path_name() for asset in lib.get_material_used_textures(material)]
        assert any(PLASMA_TEXTURE in texture for texture in textures),textures
        actual.append({'material':material.get_path_name(),'textures':textures,
                       'scalar_defaults':{str(n):lib.get_material_default_scalar_parameter_value(material,n)
                                          for n in lib.get_scalar_parameter_names(material)}})
    result={'passed':True,'saved_preview_material':_author_plasma(PLASMA_PREVIEW,(2.8,1.85,.35),1.35),
            'source_material_audit':actual,'source_assets_saved':False,'motion_clips_regenerated':False,
            'native_wisps_source':{'subimages':[8,8],'muzzle_initial_alpha':.1,
                                  'muzzle_initial_rgb':[4.,2.68,.04],
                                  'rapid_flow_initial_alpha':.5},
            'revision':3,
            'mask_basis':'Read-only source graph: opacity=SubUV.A; red is lighting; blue is mostly full, never use RGB max as opacity',
            'radial_or_geometric_opacity_mask':False,
            'white_color':'Direct Tint bypasses inherited gold ParticleColor RGB; alpha retains particle lifetime'}
    _write(out,'fresh-fx-author.json',result)
    return result


def author_release(out):
    """Explicitly authorized gold material for the parent's Q/W/R release PSC."""
    result={'passed':True,'saved_material':_author_plasma(PLASMA_RELEASE,(2.5,1.72,.38),1.0),
            'source_texture_read_only':PLASMA_TEXTURE,'source_assets_saved':False,
            'requires_subimages':[8,8],'rgb_particle_color_ignored':True,
            'particle_lifetime_alpha_preserved':True,'revision':3,
            'opacity_channel':'original SubUV A, no RGB max or radial fill'}
    _write(out,'release-wisps-author.json',result)
    return result


def author(out):
    """Author dedicated motion clips; audit source FX and backward candidates."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    if os.environ.get('SPARROW_FRESH_AUDIT_ONLY') == '1':
        return audit_plasma(out)
    author_fx(out)
    release = author_release(out)
    if os.environ.get('SPARROW_FRESH_FX_ONLY') == '1':
        return {'passed': release['passed'], 'motion_clips_regenerated': False}
    selected = _selected()
    fx_report = _PARTICLES['author'](out)
    mesh = unreal.load_asset(MESH)
    assert isinstance(mesh, unreal.SkeletalMesh), MESH
    skeleton = mesh.get_editor_property('skeleton')
    component = unreal.new_object(unreal.SkeletalMeshComponent)
    component.set_skeletal_mesh_asset(mesh)
    bones = [str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
    options = unreal.AnimPoseEvaluationOptions()
    sources, cached, clips = {}, {}, []
    for name in sorted({node[1] for key in selected if key in MOTION_KEYS for node in MOTION_KEYS[key]}):
        asset = unreal.load_asset(ANIMS + name)
        assert isinstance(asset, unreal.AnimSequence), name
        assert asset.get_editor_property('skeleton') == skeleton, name
        sources[name] = asset
    for key in selected:
        if key not in MOTION_KEYS:
            continue
        nodes = MOTION_KEYS[key]
        for _, name, fraction in nodes:
            cache_key = (name, fraction)
            if cache_key not in cached:
                asset = sources[name]
                pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(asset, asset.get_play_length()*fraction, options)
                cached[cache_key] = {bone: unreal.AnimPoseExtensions.get_bone_pose(pose, bone, unreal.AnimPoseSpaces.LOCAL)
                                     for bone in bones}
        name = 'AS_Sparrow_' + key + '_MobilityStudy'
        path = FOLDER + '/' + name
        clip = unreal.load_asset(path)
        if clip is None:
            factory = unreal.AnimSequenceFactory()
            factory.set_editor_property('target_skeleton', skeleton)
            factory.set_editor_property('preview_skeletal_mesh', mesh)
            clip = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, FOLDER, unreal.AnimSequence, factory)
        assert isinstance(clip, unreal.AnimSequence), path
        assert clip.get_path_name().startswith(FOLDER + '/'), clip.get_path_name()
        controller = clip.get_editor_property('controller')
        assert controller, 'AnimationDataController must be exposed before authoring'
        frame_count = round(DESIGNS[key]['duration'] * 30)
        controller.open_bracket('Author isolated Sparrow movement study', False)
        try:
            controller.remove_all_bone_tracks(False)
            controller.set_frame_rate(unreal.FrameRate(30, 1), False)
            controller.set_number_of_frames(unreal.FrameNumber(frame_count), False)
            for bone in bones:
                positions, rotations, scales = [], [], []
                for index in range(frame_count + 1):
                    phase = index / frame_count
                    segment = next((i for i in range(len(nodes)-1) if phase <= nodes[i+1][0]), len(nodes)-2)
                    left, right = nodes[segment], nodes[segment+1]
                    alpha = _smooth((phase-left[0]) / (right[0]-left[0]))
                    a, b = cached[(left[1], left[2])][bone], cached[(right[1], right[2])][bone]
                    position = _mix(a.translation, b.translation, alpha)
                    # Preserve joints while keeping displacement separate and reviewable.
                    if bone.lower() == 'root':
                        position = unreal.Vector(0., 0., 0.)
                    positions.append(position)
                    rotations.append(_rotation_mix(a.rotation, b.rotation, alpha))
                    scales.append(_mix(a.scale3d, b.scale3d, alpha))
                assert controller.add_bone_curve(bone, False), bone
                assert controller.set_bone_track_keys(bone, positions, rotations, scales, False), bone
        finally:
            controller.close_bracket(False)
        clip.set_editor_property('enable_root_motion', False)
        clip.set_editor_property('force_root_lock', True)
        assert unreal.EditorAssetLibrary.save_loaded_asset(clip, False)
        clips.append({'id': key, 'asset': path, 'duration': clip.get_play_length(), 'keys_per_track': frame_count+1,
                      'joint_tracks': len(bones), 'sources': [list(node) for node in nodes],
                      'new_pose_blended_animation': True, 'retargeted': False})
    candidates = []
    for path, role in (
        (ANIMS+'Jog_Bwd_Start', 'Native backward anticipation; directly usable skeleton'),
        (ANIMS+'Jog_Bwd_Stop', 'Native backward recovery; directly usable skeleton'),
        (ANIMS+'Knock_Bwd', 'Native hit reaction, not an authored dodge'),
        ('/Game/ParagonAurora/Characters/Heroes/Aurora/Animations/Ability_RMB_Bwd', 'Dedicated other-hero backward ability candidate'),
        ('/Game/ParagonAurora/Characters/Heroes/Aurora/Animations/Ability_RMB_BwdLeft', 'Other-hero backward-left ability candidate'),
        ('/Game/ParagonAurora/Characters/Heroes/Aurora/Animations/Ability_RMB_BwdRight', 'Other-hero backward-right ability candidate'),
        ('/Game/Characters/Mannequins/Anims/Unarmed/Jump/MM_Dash', 'Other-skeleton dash candidate')):
        asset = unreal.load_asset(path)
        assert isinstance(asset, unreal.AnimSequence), path
        candidates.append({'path': path, 'role': role, 'duration': asset.get_play_length(),
                           'same_skeleton_as_sparrow': asset.get_editor_property('skeleton') == skeleton})
    result = {'passed': True, 'preview_only': True, 'saved_motion_clips': clips, 'backward_candidates': candidates,
              'effect_sources_verified': fx_report['passed'], 'source_assets_saved': False,
              'production_defaults_changed': False, 'retargeting_performed': False,
              'movement_collision_or_input_installed': False, 'designs': {key: DESIGNS[key] for key in selected}}
    _write(out, 'fresh-author.json', result)
    return result


class Study(ParticleStudy):
    """Short textured additions, no giant additive plane or floor atmosphere."""
    def __init__(self, rig, option):
        super().__init__(rig, option)
        self.arrows, self.hidden, self.followers, self.pending = [], {}, [], []
        self.last_muzzle = -99.
        self.rotation = rig['pawn']().get_actor_rotation()
        self.rotation.pitch, self.rotation.roll = 0., 0.
        self.forward = rig['pawn']().get_actor_forward_vector()
        self.right = unreal.Vector(-self.forward.y, self.forward.x, 0.)
        material=unreal.load_asset(PLASMA_PREVIEW)
        assert material,'Run author_fx before these revised studies'
        self.white = unreal.MaterialLibrary.create_dynamic_material_instance(rig['world'](),material)
        self.gold = unreal.MaterialLibrary.create_dynamic_material_instance(rig['world'](),material)
        assert self.white and self.gold
        self.white.set_vector_parameter_value('Tint',unreal.LinearColor(3.6,3.5,2.8,1.))
        self.white.set_scalar_parameter_value('OpacityGain',1.8)
        self.gold.set_vector_parameter_value('Tint',unreal.LinearColor(3.2,2.05,.38,1.))
        self.gold.set_scalar_parameter_value('OpacityGain',1.5)
        self.mids.extend((self.white,self.gold))

    def hide(self, component):
        path = component.get_path_name()
        if path not in self.hidden:
            self.hidden[path] = (component, component.is_visible())
        component.set_visibility(False)

    def pulse(self, key, names, position, rotation, scale, seconds, speed=1., white=False):
        fx = super().pulse(key, names, position, rotation, scale, seconds, speed)
        if names == ('Wisps',) and self.option != 'E9':
            # Slot order belongs to the original template, not to the enabled subset.
            slot = _PARTICLES['EMITTERS'][key].index('Wisps')
            fx.set_material(slot, self.white if white else self.gold)
        return fx

    def shard(self, position, scale=.28, life=.25, speed=2.):
        return self.pulse('shards', ('Flames2',), position,
                          unreal.MathLibrary.make_rot_from_z(self.forward), (scale, scale, scale*1.35), life, speed)

    def arrow(self, arrow):
        e = self.option.startswith('E')
        row = {'arrow': arrow, 'born': self.now(), 'next_emit': 0., 'serial': len(self.arrows)}
        self.arrows.append(row)
        for fx in arrow.get_components_by_class(unreal.ParticleSystemComponent):
            name = fx.get_name()
            if not e and name == 'CondensedCore':
                self.snapshots.append((fx,fx.is_visible(),fx.get_editor_property('relative_scale3d'),
                                       fx.get_editor_property('custom_time_dilation'),fx.get_material(0)))
                fx.set_relative_scale3d(unreal.Vector(.36,.36,.36))
            if e and name in ('ArrowTrail', 'RapidArrowFlow'):
                self.snapshots.append((fx, fx.is_visible(), fx.get_editor_property('relative_scale3d'),
                                       fx.get_editor_property('custom_time_dilation'), fx.get_material(0)))
                if name == 'ArrowTrail':
                    fx.set_world_scale3d(unreal.Vector(1., .65, .65))
                else:
                    width=1.30 if self.option=='E7' else 1.65 if self.option=='E8' else 1.25
                    fx.set_world_scale3d(unreal.Vector(1.,width,width))
                    if self.option == 'E7':
                        fx.set_material(0,self.gold)
                    if self.option == 'E8':
                        fx.set_material(0, self.white)
                        fx.set_editor_property('custom_time_dilation', 1.1)
        origin = self.rig['skills']().get_arrow_origin()
        if self.option in ('E7', 'A3'):
            for side in (-1., 1.):
                self.shard(origin+self.right*(24.*side), .37 if e else .5, .24, 2.)
            self.pulse('muzzle', ('Wisps',), origin, self.rotation, (1.8,1.05,1.05), .20, 1.6)
        elif self.option in ('E8', 'A5'):
            self.pulse('muzzle', ('Wisps',), origin, self.rotation, (2.2,.90,.90), .22, 2., True)
            self.pulse('muzzle', ('Sparks',), origin, self.rotation, (1.4,.8,.8), .23, 2.)
        else:
            for offset in (-36., 0., 36.):
                self.shard(origin+self.right*offset+unreal.Vector(0,0,abs(offset)*.3), .32, .30, 2.2)
        self.last_muzzle = self.now()

    def hit(self, target, direction):
        point = target.get_actor_location()
        e = self.option.startswith('E')
        scale = .70 if e else 1.05
        self.pulse('impact', ('Sparks', 'SparkTrailHeads'), point, self.rotation, (scale,scale,scale), .32, 1.8)
        if self.option in ('E7', 'A3'):
            for side in (-1., 1.):
                self.shard(point+self.right*(18.*side), .24 if e else .40, .28, 1.8)
        elif self.option in ('E8', 'A5'):
            self.pulse('impact', ('Wisps',), point, self.rotation, (.85,.65,.65) if e else (1.1,.8,.8), .24, 2.2, True)
        else:
            for i in range(3 if e else 5):
                phase = i*2.39996
                position = point+self.right*(math.cos(phase)*32.)+unreal.Vector(0,0,math.sin(phase)*27.)
                self.shard(position, .20 if e else .28, .30, 2.2)
        if not e:
            for i in range(1, 4):
                self.pending.append((self.now()+i*.065, point+self.forward*(i*7.)+self.right*((1 if i%2 else -1)*18.)))

    def update(self, started):
        now = self.now()
        # Native ground/muzzle circles are suppressed only while this study is
        # running. Projectile texture and native hit feedback remain intact.
        if self.option.startswith('E'):
            for cls in (unreal.SparrowShotWave, unreal.SparrowBowFeedback):
                for actor in unreal.GameplayStatics.get_all_actors_of_class(self.rig['world'](), cls):
                    if actor.get_owner() == self.rig['pawn']():
                        actor.set_actor_hidden_in_game(True)
        for row in self.arrows:
            arrow = row['arrow']
            if not _valid(arrow) or now < row['next_emit']:
                continue
            e = self.option.startswith('E')
            period = .075 if e else .11
            row['next_emit'] = now+period
            age = now-row['born']
            position = arrow.get_actor_location()
            if self.option in ('E7', 'A3'):
                for side in (-1., 1.):
                    point = position-self.forward*(35. if e else 65.)+self.right*(side*(17. if e else 32.))
                    self.pulse('muzzle', ('Wisps',), point, self.rotation,
                               (1.05,.75,.75) if e else (2.1,1.25,1.25), .25 if e else .42, 1.4)
                if not e:
                    self.pulse('muzzle',('Wisps',),position-self.forward*130.,self.rotation,(1.45,.92,.92),.40,1.45)
                    self.pulse('muzzle', ('Sparks',), position, self.rotation, (.6,.65,.65), .25, 2.)
            elif self.option in ('E8', 'A5'):
                point = position-self.forward*(28. if e else 68.)
                self.pulse('muzzle', ('Wisps',), point, self.rotation,
                           (1.35,1.05,1.05) if e else (2.45,1.45,1.45), .25 if e else .40, 1.35, True)
                if not e:
                    self.pulse('muzzle',('Wisps',),position-self.forward*135.,self.rotation,(1.25,.85,.85),.32,1.6,True)
                self.pulse('muzzle', ('Sparks',), point, self.rotation, (.65,.55,.55), .24, 2.4)
                if not e and int(age/.11)%3 == 0:
                    self.shard(position-self.forward*38., .22, .25, 2.2)
            else:
                count = 3 if e else 3
                for i in range(count):
                    phase = age*(17. if e else 9.)+i*math.tau/count+row['serial']*.7
                    radius = 25. if e else 46.
                    point = position-self.forward*(24.+i*(14. if e else 46.))+self.right*(math.cos(phase)*radius)+unreal.Vector(0,0,math.sin(phase)*radius)
                    self.shard(point, .20 if e else .36, .27 if e else .44, 2.0)
        for due, position in self.pending[:]:
            if now >= due:
                self.pending.remove((due, position))
                self.pulse('impact', ('Sparks',), position, self.rotation, (.58,.58,.58), .28, 1.8)
        self.tick()

    def close(self):
        for component, visible in self.hidden.values():
            if _valid(component):
                component.set_visibility(visible)
        for cls in (unreal.SparrowShotWave, unreal.SparrowBowFeedback):
            for actor in unreal.GameplayStatics.get_all_actors_of_class(self.rig['world'](), cls):
                if actor.get_owner() == self.rig['pawn']():
                    actor.set_actor_hidden_in_game(False)
        self.pending.clear()
        return super().close()


def _clip(rig, name):
    if os.environ.get('NEW_SKILLS_VIDEO', '1') == '1':
        rig['STATE']['video_clip'] = {'case': name, 'prefix': name+'_video',
            'cast_time': unreal.GameplayStatics.get_time_seconds(rig['world']()), 'frame_times': []}


def _effects(rig, options):
    rows = []
    now = lambda: unreal.GameplayStatics.get_time_seconds(rig['world']())
    for option in options:
        if option.startswith('M'):
            continue
        rig['switch']('countess')
        yield .10
        rig['switch']('sparrow')
        yield .55
        rig['case']('fresh_'+option)
        e = option.startswith('E')
        targets = rig['layout']([(750 if e else 470, 0), (750, 350), (750, -350)])
        yield .20
        target = targets[0]
        initial = previous = rig['health'](target)
        stacks = rig['skills']().get_relentless_stacks(target)
        expected = sum(10.*(1.+min(stacks+i,10)*.0175) for i in range(6)) if e else 90.
        study, seen, hits = Study(rig, option), set(), []
        started = now()
        try:
            rig['use']('E' if e else 'A', target)
            _clip(rig, option)
            capture_times = [.30, .58] if e else [.72, 1.15, 1.9]
            while now()-started < (1.5 if e else 2.8):
                elapsed = now()-started
                for arrow in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowArrow):
                    path = arrow.get_path_name()
                    if arrow.get_owner() == rig['pawn']() and path not in seen:
                        seen.add(path)
                        study.arrow(arrow)
                health = rig['health'](target)
                if health < previous-.01:
                    study.hit(target, study.forward)
                    hits.append({'elapsed': elapsed, 'damage': previous-health})
                    if not e:
                        capture_times.append(elapsed+.10)
                previous = health
                study.update(started)
                if capture_times and elapsed >= capture_times[0]:
                    rig['capture'](option+'_at_'+str(round(capture_times.pop(0)*100)))
                yield 1/rig['FPS']
            rig['finish_video_clip']()
            actual = initial-rig['health'](target)
            rig['check'](len(seen) == (6 if e else 1), option+' observes native arrow count')
            rig['check'](abs(actual-expected) < .03, option+' preserves native damage')
            rig['recovered']()
            rows.append({'id': option, **DESIGNS[option], 'native_arrows': len(seen), 'hits': hits,
                         'actual_damage': actual, 'expected_damage': expected,
                         'temporary_particles_created': study.created,
                         'peak_active_particles': study.peak_particles, 'production_installed': False})
        finally:
            rig['finish_video_clip']()
            study.close()
        yield .15
    _write(rig['OUT'], 'fresh-fx-studies.json', {'passed': True, 'studies': rows,
           'new_damage_sources': False, 'assets_saved_in_PIE': False, 'production_defaults_changed': False,
           'visual_acceptance': 'pending actual capture review'})


def _proxy(rig, original, ghost=False):
    actor = _BOW['spawn_preview'](rig['world'](), rig['cmd'])
    mesh = actor.get_editor_property('skeletal_mesh_component')
    mesh.set_skeletal_mesh_asset(original.get_editor_property('skeletal_mesh_asset'))
    mesh.set_editor_property('disable_cloth_simulation', True)
    mesh.set_forced_lod(1)
    mesh.set_cast_shadow(False)
    mesh.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    # A separate animation instance makes each ghost preserve an older joint pose.
    mesh.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    if ghost:
        material = unreal.load_asset(ECHO)
        assert material
        mid = mesh.create_dynamic_material_instance(0, material)
        mid.set_scalar_parameter_value('Visibility', .9)
        mid.set_vector_parameter_value('BodyTint', unreal.LinearColor(1.1,.73,.18,1.))
        for slot in range(mesh.get_num_materials()):
            mesh.set_material(slot, mid)
        for lod in range(5):
            for slot in (3,7,13):
                mesh.show_material_section(slot, -1, False, lod)
    return actor, mesh


def _movement_transform(start, forward, right, key, phase):
    design = DESIGNS[key]
    travel = _smooth((phase-.10)/.68)
    direction = right * -1. if key == 'M7' else forward * (-1. if key in ('M8','M9') else 1.)
    height = design['height'] * math.sin(math.pi*_smooth((phase-.12)/.64))
    location = start.translation + direction*(design['distance']*travel)+unreal.Vector(0,0,height)
    rotation = start.rotation.rotator()
    envelope = math.sin(math.pi*travel)
    # Small component tilt complements the native changing joints; no fake rigid roll.
    rotation.roll += (13. if key == 'M6' else -11. if key == 'M8' else -6. if key == 'M9' else 0.)*envelope
    rotation.pitch += (-18. if key == 'M7' else 0.)*envelope
    return location, rotation


def _movements(rig, options):
    selected = [key for key in options if key.startswith('M')]
    if not selected:
        return
    rig['switch']('sparrow')
    yield .60
    rows = []
    for key in selected:
        rig['case']('fresh_'+key)
        rig['layout']([(800,300),(800,-350),(-650,400)])
        yield .20
        pawn = rig['pawn']()
        original = pawn.get_editor_property('mesh')
        original_visible = original.is_visible()
        player_start = pawn.get_actor_location()
        start = original.get_world_transform()
        forward = pawn.get_actor_forward_vector()
        right = unreal.Vector(-forward.y,forward.x,0.)
        clip = unreal.load_asset(FOLDER+'/AS_Sparrow_'+key+'_MobilityStudy')
        assert isinstance(clip,unreal.AnimSequence), key+' requires author before PIE'
        proxies = []
        try:
            for index in range(3):
                actor, mesh = _proxy(rig, original, index > 0)
                proxies.append((actor,mesh))
                actor.set_actor_transform(start,False,True)
                mesh.play_animation(clip,False)
                mesh.set_play_rate(0.)
                mesh.set_visibility(index == 0,False)
            original.set_visibility(False,False)
            _clip(rig,key)
            duration = DESIGNS[key]['duration']
            count = round(rig['FPS']*(duration+.22))
            bone_samples = []
            for frame in range(count):
                elapsed = frame/rig['FPS']
                for index,(actor,mesh) in enumerate(proxies):
                    delayed = elapsed-index*.050
                    phase = max(0.,min(1.,delayed/duration))
                    visible = index == 0 or (0.12 < delayed < duration*.87)
                    mesh.set_visibility(visible,False)
                    mesh.set_position(phase*clip.get_play_length(),False)
                    location,rotation = _movement_transform(start,forward,right,key,phase)
                    actor.set_actor_location_and_rotation(location,rotation,False,True)
                if frame in (round(rig['FPS']*.18),round(rig['FPS']*.38),round(rig['FPS']*.60)):
                    rig['capture'](key+'_at_'+str(frame))
                    mesh=proxies[0][1]
                    sample={}
                    local_sample={}
                    for bone in ('pelvis','foot_l','foot_r','hand_l','hand_r'):
                        if mesh.get_bone_index(bone)>=0:
                            p=mesh.get_socket_location(bone)
                            sample[bone]=[p.x,p.y,p.z]
                            p=mesh.get_socket_transform(bone,unreal.RelativeTransformSpace.RTS_COMPONENT).translation
                            local_sample[bone]=[p.x,p.y,p.z]
                    bone_samples.append({'seconds':elapsed,'world_bones':sample,'component_bones':local_sample})
                yield 1/rig['FPS']
            rig['finish_video_clip']()
            delta=pawn.get_actor_location()-player_start
            rig['check'](delta.length()<.01,key+' preview leaves live player position intact')
            joint_motion=max((math.sqrt(sum((a-b)**2 for a,b in zip(
                first['component_bones'][bone],last['component_bones'][bone])))
                for first in bone_samples for last in bone_samples
                for bone in set(first['component_bones']) & set(last['component_bones'])),default=0.)
            rig['check'](joint_motion>2.,key+' changes actual local joint poses, beyond actor translation')
            rows.append({'id':key,**DESIGNS[key],'new_animation_asset':clip.get_path_name(),
                         'joint_pose_samples':bone_samples,'max_sampled_joint_motion_cm':joint_motion,
                         'new_pose_blended_animation':True,
                         'player_displaced':False,'collision_tested':False,'installed_ability':False,
                         'anatomical_roll':False})
        finally:
            rig['finish_video_clip']()
            original.set_visibility(original_visible,False)
            for actor,_ in proxies:
                if _valid(actor):
                    actor.destroy_actor()
        rig['check'](original.is_visible()==original_visible,key+' restores original mesh visibility')
        yield .15
    remaining=[a for a in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SkeletalMeshActor)
               if a.actor_has_tag('SparrowBowAuditPreview')]
    rig['check'](not remaining,'all authored mobility preview actors removed')
    _write(rig['OUT'],'fresh-mobility-studies.json',{'passed':True,'studies':rows,
            'assets_saved_in_PIE':False,'movement_installed':False,
            'visual_acceptance':'pending actual capture review'})


def sequence(rig):
    options = _selected()
    yield from _effects(rig,options)
    yield from _movements(rig,options)
