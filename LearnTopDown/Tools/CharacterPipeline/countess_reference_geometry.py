"""Reference-shaped Countess solids, curved blades and torn energy surfaces.

Only project-owned Reference20261024 packages are saved. The source texture
packages and the existing gameplay/component assets are never modified.
"""
import hashlib
import json
import math
import runpy
from pathlib import Path

import unreal


ROOT = '/Game/TopDown/Characters/Countess/Reference20261024'
NOISE = '/Game/ParagonCountess/FX/Textures/Tile/Noise/T_Inky_Smoke_Tile'
INK = '/Game/ParagonCountess/FX/Textures/FluidPatterns/T_InkSmoky_M'
VERSION = '2'


def _surface(name, veil=False, hand=False):
    path = ROOT + '/' + name
    material = unreal.load_asset(path)
    if material is None:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, ROOT, unreal.Material, unreal.MaterialFactoryNew())
    if unreal.EditorAssetLibrary.get_metadata_tag(material, 'CountessReferenceVersion') == VERSION:
        return material
    lib = unreal.MaterialEditingLibrary
    lib.delete_all_material_expressions(material)
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT if veil or hand else unreal.BlendMode.BLEND_MASKED)
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT if veil or hand else unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    material.set_editor_property('two_sided', True)
    material.set_editor_property('opacity_mask_clip_value', .22)

    def node(kind, **props):
        item = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression' + kind))
        for key, value in props.items():
            item.set_editor_property(key, value)
        return item

    def wire(source, channel, target, pin):
        if not lib.connect_material_expressions(source, channel, target, pin):
            raise RuntimeError('Cannot connect Countess reference material: ' + pin)

    uv = node('TextureCoordinate')
    time = node('Time')
    samples = []
    for tex_path, speed in ((NOISE, (.08, -.35)), (INK, (-.06, .19))):
        texture = unreal.load_asset(tex_path)
        if texture is None:
            raise RuntimeError('Missing source texture: ' + tex_path)
        pan = node('Panner', speed_x=speed[0], speed_y=speed[1])
        wire(uv, '', pan, 'Coordinate')
        sample = node('TextureSample', texture=texture)
        wire(pan, '', sample, 'UVs')
        samples.append(sample)
    values = [(uv, '', 'UV'), (time, '', 'Time'), (samples[0], 'R', 'Noise'),
              (samples[1], 'R', 'Ink'),
              (node('Fresnel', exponent=1., base_reflect_fraction=0.), '', 'Facing')]
    for key, default in (('RuinErode', 0.), ('RuinPulse', 0.), ('RuinEnergy', 1.),
                         ('RuinProfile', 1.), ('CloneOpacity', 1.), ('ReferenceAge', 0.)):
        values.append((node('ScalarParameter', parameter_name=key, default_value=default), '', key))

    def custom(code, output):
        result = node('Custom', code=code, output_type=output)
        pins = []
        for source, channel, key in values:
            pin = unreal.CustomInput()
            pin.set_editor_property('input_name', key)
            pins.append(pin)
        result.set_editor_property('inputs', pins)
        for source, channel, key in values:
            wire(source, channel, result, key)
        return result

    common = '''
float n=pow(saturate((Noise-.0075)/.5766),.62);
float ink=pow(saturate((Ink-.0009)/.3131),.38);
float grain=saturate(n*.58+ink*.42);
float vein=pow(saturate(1-abs(n-ink*.67-.12)*19),2.4)*smoothstep(.24,.60,grain);
float edge=1-smoothstep(.012,.07,min(UV.y,1-UV.y));
float ends=smoothstep(0,.06,UV.x)*smoothstep(0,.10,1-UV.x);
'''
    if hand:
        emission = common + '''
float rim=pow(saturate(Facing),3.2);
float fade=1-saturate(RuinErode);
return (float3(.005,.00015,.0008)+float3(.52,.003,.018)*(vein*.32+rim*.38+grain*grain*.07))
 * RuinEnergy * (.8+.2*saturate(RuinPulse))*sqrt(fade);
'''
        alpha = common + '''
float patches=smoothstep(.23,.63,grain);
float erosion=1-smoothstep(grain*.55+.10,grain*.55+.48,saturate(RuinErode));
return CloneOpacity*(.16+.57*patches)*erosion;
'''
    elif veil:
        emission = common + '''
float heat=smoothstep(.46,.83,grain);
return (float3(.004,.0002,.0007)*(1-heat)+float3(1.25,.011,.023)*(heat*.22+vein*.15))
 * RuinEnergy * (.65+.35*saturate(RuinPulse));
'''
        alpha = common + '''
float torn=smoothstep(.14+.45*saturate(RuinErode),.55,grain);
float boundary=smoothstep(0,.12,UV.y)*smoothstep(0,.10,1-UV.y);
return saturate(torn*boundary*ends*CloneOpacity*.95);
'''
    else:
        emission = common + '''
float blade=step(1.5,RuinProfile);
float crater=1-step(.5,RuinProfile);
float edgeLight=edge*ends*(blade+.13*crater*pow(grain,3))*(.55+.45*ink);
return (float3(1.9,.014,.030)*(vein*.42+edgeLight*.80)
 +float3(2.2,.055,.028)*saturate(RuinPulse)*(vein*.35+edgeLight*.22))*RuinEnergy;
'''
        alpha = common + '''
float erosion=saturate((.25+.55*grain+.20*(1-UV.x)-saturate(RuinErode))*10);
float crater=1-step(.5,RuinProfile);
float brokenRim=saturate((grain-.26*smoothstep(.50,.92,UV.y))*9);
return erosion*lerp(1,brokenRim,crater)*saturate(CloneOpacity*4);
'''
        base = custom(common + 'return lerp(float3(.008,.005,.007),float3(.039,.016,.023),grain*grain);', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        lib.connect_material_property(base, '', unreal.MaterialProperty.MP_BASE_COLOR)
        lib.connect_material_property(node('Constant', r=.93), '', unreal.MaterialProperty.MP_ROUGHNESS)
        lib.connect_material_property(node('Constant', r=0.), '', unreal.MaterialProperty.MP_METALLIC)
        lib.connect_material_property(node('Constant', r=.10), '', unreal.MaterialProperty.MP_SPECULAR)
    lib.connect_material_property(custom(emission, unreal.CustomMaterialOutputType.CMOT_FLOAT3), '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.connect_material_property(custom(alpha, unreal.CustomMaterialOutputType.CMOT_FLOAT1), '',
                                  unreal.MaterialProperty.MP_OPACITY if veil or hand else unreal.MaterialProperty.MP_OPACITY_MASK)
    errors = [str(e) for e in (lib.recompile_material(material) or [])]
    if errors:
        raise RuntimeError('Countess reference shader failed: ' + repr(errors))
    unreal.EditorAssetLibrary.set_metadata_tag(material, 'CountessReferenceVersion', VERSION)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError('Cannot save reference material ' + path)
    return material


class Geometry:
    def __init__(self):
        self.vertices, self.uvs, self.faces = [], [], []

    def grid(self, rows):
        base = len(self.vertices) + 1
        width = len(rows[0])
        for row in rows:
            for pos, uv in row:
                self.vertices.append(pos)
                self.uvs.append(uv)
        for i in range(len(rows)-1):
            for j in range(width-1):
                a = base + i*width+j
                self.faces.extend(((a, a+1, a+width+1), (a, a+width+1, a+width)))

    def tube(self, points, radii, sides=10):
        rows = []
        for i, ((x, y, z), (ry, rz)) in enumerate(zip(points, radii)):
            rows.append([((x, y+math.cos(j*math.tau/sides)*ry, z+math.sin(j*math.tau/sides)*rz),
                          (i/(len(points)-1), j/sides)) for j in range(sides+1)])
        self.grid(rows)


def _hand():
    g = Geometry()
    # A broad, flattened palm and four independent knuckles give the summon a
    # recognisable attacker, rather than three unrelated floating slash curves.
    g.tube([(-48, 0, -2), (-30, 0, 0), (-8, 0, 4), (16, 0, 2), (34, 0, -2)],
           [(7, 6), (18, 9), (34, 15), (40, 18), (33, 10)], 16)
    for i, side in enumerate((-31, -11, 12, 32)):
        reach = (89, 113, 108, 83)[i]
        points, radii = [], []
        for k in range(17):
            t = k/16
            points.append((23+reach*t, side*(1+.34*t), 4+27*math.sin(t*math.pi*.9)-63*t*t*t))
            radius = (9.1 if i in (1, 2) else 7.7)*(1-t)**.83*(1+.09*math.sin(t*math.pi*4))+.14
            radii.append((radius, radius*.88))
        g.tube(points, radii)
    # The thumb branches below the wrist and curls back toward the palm.
    points = [(-17+81*t/16, -33-43*math.sin(t/16*math.pi*.62), -3-28*(t/16)**2) for t in range(17)]
    g.tube(points, [(10.5*(1-k/16)**.7+.12, 8.8*(1-k/16)**.7+.12) for k in range(17)])
    return g


def _cup():
    g = Geometry()
    rows = []
    for ring in range(9):
        t = ring/8
        row = []
        for i in range(65):
            a = i/64*math.tau
            chipped = (math.sin((i%64)*12.9898+3.7)*43758.5453)%1
            r = (9+91*t)*(1+.03*math.sin(7*a)+(.11*chipped-.055)*t*t)
            lip = max(0, (t-.48)/.52)**1.7
            z = -2+lip*(13+17*chipped+4*math.sin(a*5+.7))
            row.append(((r*math.cos(a), r*math.sin(a), z), (i/64, t)))
        rows.append(row)
    g.grid(rows)
    return g


def _arc(degrees=284):
    g = Geometry()
    rows = []
    for i in range(49):
        t=i/48
        a=(-degrees*.5+degrees*t)*math.pi/180
        taper=max(.012, math.sin(math.pi*t)**.72)
        row=[]
        for j in range(7):
            v=j/6
            r=86+(v-.5)*42*taper
            z=14*math.sin(a*1.3)+(1-abs(v-.5)*2)*10*taper
            row.append(((r*math.cos(a), r*math.sin(a), z), (t,v)))
        rows.append(row)
    g.grid(rows)
    return g


def _shroud():
    g = Geometry()
    rows=[]
    for i in range(33):
        t=i/32
        angle=t*math.tau
        row=[]
        for j in range(17):
            h=j/16
            radius=(22+63*math.sin(h*math.pi))*(1+.07*math.sin(angle*7+h*9))
            row.append(((radius*math.cos(angle),radius*math.sin(angle),h*190), (t,h)))
        rows.append(row)
    g.grid(rows)
    return g


def _save_mesh(output, material, name, geometry):
    path=ROOT+'/'+name
    mesh=unreal.load_asset(path)
    if mesh is not None and unreal.EditorAssetLibrary.get_metadata_tag(mesh,'CountessReferenceGeometry')==VERSION:
        return {'path':path,'reused':True,'triangles':mesh.get_num_triangles(0)}
    size=[max(v[a] for v in geometry.vertices)-min(v[a] for v in geometry.vertices) for a in range(3)]
    bounds=(size[0],size[1]-.2,size[1]+.2,size[2]-.2,size[2]+.2)
    importer=runpy.run_path(str(Path(__file__).with_name('countess_ruin_surface.py')))['_import_mesh']
    return importer(output,material,path,geometry.vertices,geometry.uvs,geometry.faces,
                    'CountessReferenceGeometry',VERSION,bounds,len(geometry.faces)-4,32)


def author(output):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    source_files=[Path(unreal.Paths.project_content_dir())/(p.removeprefix('/Game/')+'.uasset') for p in (NOISE,INK)]
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
    solid=_surface('M_CountessReferenceSolid')
    veil=_surface('M_CountessReferenceVeil',True)
    hand=_surface('M_CountessDemonicHand',hand=True)
    meshes=[_save_mesh(output,hand,'SM_CountessDemonicHand',_hand()),
            _save_mesh(output,solid,'SM_CountessRuptureCup',_cup()),
            _save_mesh(output,solid,'SM_CountessBladeVortex',_arc()),
            _save_mesh(output,solid,'SM_CountessStormCleave',_arc(160)),
            _save_mesh(output,veil,'SM_CountessDemonShroud',_shroud())]
    unchanged=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==v for p,v in before.items())
    if not unchanged:
        raise RuntimeError('Source texture package unexpectedly changed')
    result={'passed':True,'version':VERSION,'source_hash_unchanged':unchanged,'meshes':meshes,
            'materials':[solid.get_path_name(),veil.get_path_name(),hand.get_path_name()],
            'scope':'owned visual geometry only; no gameplay, animation or source-pack changes'}
    (output/'countess-reference-geometry.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
