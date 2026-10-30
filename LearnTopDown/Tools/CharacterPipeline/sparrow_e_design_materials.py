"""Owned real geometry/materials for E1 feather bow, E2 sweep and E3 arc arrows.

Default E assets are not changed.  Existing import/material authoring patterns
are reused; the native skill owns actual single/sector/five-arrow damage.
"""
import hashlib
import json
import math
from pathlib import Path
import runpy

import unreal

ROOT = '/Game/TopDown/Characters/Sparrow/Materials/EDesign20261027'
MESH_ROOT = '/Game/TopDown/Characters/Sparrow/FX/EDesign20261027'
FLOW = '/Game/ParagonSparrow/FX/Textures/Tile/Energy/Plasma/T_Sparrow_Poster_Tendrils_v2_Seamless'
ART = '/Game/TopDown/Characters/Sparrow/FX/FDesign20261027/T_FDesignGoldenFlow'
BOW_ART = MESH_ROOT + '/T_E7CelestialBow'
PLUME_ART = MESH_ROOT + '/T_E8FeatherBow'


def _bow_art():
    source = Path(__file__).resolve().parent / 'ArtSources/Craft20261027/E7-celestial-bow.png'
    assert source.is_file(), 'E7 authored transparent bow is required: ' + str(source)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    texture = unreal.load_asset(BOW_ART)
    reused = bool(texture and unreal.EditorAssetLibrary.get_metadata_tag(texture, 'E7ImageHash') == digest)
    if not reused:
        task = unreal.AssetImportTask()
        for key, value in {'filename': str(source), 'destination_path': MESH_ROOT,
                           'destination_name': 'T_E7CelestialBow', 'automated': True,
                           'replace_existing': True, 'save': False}.items():
            task.set_editor_property(key, value)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        texture = unreal.load_asset(BOW_ART)
    assert isinstance(texture, unreal.Texture2D), BOW_ART
    previous_never_stream = texture.get_editor_property('never_stream')
    texture.set_editor_property('srgb', True)
    texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_BC7)
    texture.set_editor_property('compression_no_alpha', False)
    # This hero appears for about half a second on a newly spawned component.
    # Keep this single small texture resident instead of streaming coarse mips
    # during the opening. The source image and material intensity are unchanged.
    texture.set_editor_property('never_stream', True)
    stretch = getattr(unreal.TexturePowerOfTwoSetting, 'STRETCH_TO_POWER_OF_TWO', None)
    if stretch is not None:
        texture.set_editor_property('power_of_two_mode', stretch)
    texture.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
    texture.set_editor_property('filter', unreal.TextureFilter.TF_TRILINEAR)
    texture.set_editor_property('address_x', unreal.TextureAddress.TA_CLAMP)
    texture.set_editor_property('address_y', unreal.TextureAddress.TA_CLAMP)
    unreal.EditorAssetLibrary.set_metadata_tag(texture, 'E7ImageHash', digest)
    assert unreal.EditorAssetLibrary.save_loaded_asset(texture, False), BOW_ART
    return texture, {'path': BOW_ART, 'source': str(source), 'hash': digest, 'reused': reused,
                     'channels': 'linear-decoded RGB surface, authored A coverage; no luminance alpha key',
                     'srgb': True, 'mips': 'UE stretch-to-POT, trilinear; all mips resident',
                     'previous_never_stream': previous_never_stream,
                     'never_stream': texture.get_editor_property('never_stream'),
                     'lod_bias': texture.get_editor_property('lod_bias'),
                     'max_texture_size': texture.get_editor_property('max_texture_size'),
                     'grip_uv': [.5, .585], 'tip_uv': [[.091, .189], [.909, .189]],
                     'source_dimensions': [1881, 836]}


def _plume_art():
    """Import the shared E8/D6 authored feather image without changing E7."""
    source = Path(__file__).resolve().parent / 'ArtSources/Plume20261028/FeatherBow.png'
    assert source.is_file(), str(source)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    texture = unreal.load_asset(PLUME_ART)
    reused = bool(texture and unreal.EditorAssetLibrary.get_metadata_tag(texture, 'E8ImageHash') == digest)
    if not reused:
        task = unreal.AssetImportTask()
        for key, value in {'filename': str(source), 'destination_path': MESH_ROOT,
                           'destination_name': 'T_E8FeatherBow', 'automated': True,
                           'replace_existing': True, 'save': False}.items():
            task.set_editor_property(key, value)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        texture = unreal.load_asset(PLUME_ART)
    assert isinstance(texture, unreal.Texture2D), PLUME_ART
    for key, value in {'srgb': True, 'compression_settings': unreal.TextureCompressionSettings.TC_BC7,
                       'compression_no_alpha': False, 'never_stream': True,
                       'mip_gen_settings': unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP,
                       'filter': unreal.TextureFilter.TF_TRILINEAR,
                       'address_x': unreal.TextureAddress.TA_CLAMP,
                       'address_y': unreal.TextureAddress.TA_CLAMP}.items():
        texture.set_editor_property(key, value)
    stretch = getattr(unreal.TexturePowerOfTwoSetting, 'STRETCH_TO_POWER_OF_TWO', None)
    if stretch is not None:
        texture.set_editor_property('power_of_two_mode', stretch)
    unreal.EditorAssetLibrary.set_metadata_tag(texture, 'E8ImageHash', digest)
    assert unreal.EditorAssetLibrary.save_loaded_asset(texture, False), PLUME_ART
    return texture, {'path': PLUME_ART, 'source': str(source), 'hash': digest, 'reused': reused,
                     'source_dimensions': [2079, 756], 'grip_uv': [.5, .735],
                     'tip_uv': [[.073, .035], [.927, .035]], 'never_stream': True,
                     'mapping': 'image up is draw-back (-attack X); arrow flight remains +attack X'}

COMMON = r'''
float u=saturate(UV.x),v=saturate(UV.y);
float raw=Texture2DSample(Flow,FlowSampler,UV*float2(1.3,2.1)+float2(-Age*.21,Index*.17)).r;
float n=pow(saturate(raw),.45);
float fine=pow(saturate(Texture2DSample(Flow,FlowSampler,UV*float2(3.,4.)+float2(Age*.37,Index*.29)).g),.45);
float3 amber=float3(1.10,.40,.045), gold=float3(2.7,1.55,.39),white=float3(4.7,3.5,1.55);
float3 rgb=0.; float alpha=0.;
'''

LIMB = COMMON + r'''
float edge=pow(abs(v-.5)*2.,7.)*smoothstep(.28,.63,n);
float ridge=pow(saturate(cos(v*12.56637+u*3.+n*2.)),6.);
float flowing=exp(-pow((u-frac(Age*.9+Index*.12))/.11,2.));
float reveal=1.-smoothstep(Open-.045,Open+.035,u);
rgb=amber*(.38+n*.36)+gold*(ridge*.35+flowing*.43)+white*edge*.14;
alpha=(.62+n*.23+edge*.10)*reveal;
return float4(rgb*(1.+Pulse*.85),alpha*Envelope);
'''

FEATHER = COMMON + r'''
float edge=pow(abs(v-.5)*2.,10.)*smoothstep(.38,.70,n);
float spine=exp(-pow((v-.5-(n-.4)*.10)/.13,2.));
float barb=pow(saturate(cos(u*28.-abs(v-.5)*12.+n*2.5)),6.)*(1.-edge);
float ragged=smoothstep(.16,.49,n+.18*sin(u*14.+v*9.));
float reveal=1.-smoothstep(Open-.04,Open+.04,u);
rgb=amber*(.45+n*.45)+gold*(barb*.48+spine*.38)+white*edge*.15;
alpha=(.54*ragged+edge*.20+spine*.30+barb*.26)*reveal;
return float4(rgb*(1.+Pulse*.75),saturate(alpha)*Envelope);
'''

SWEEP = COMMON + r'''
float end=smoothstep(0.,.035,u)*(1.-smoothstep(.88,1.,u));
float center=.50+(n-.4)*.16+sin(u*8.-Age*10.)*.055;
float body=exp(-pow((v-center)/.31,2.))*(.35+.65*n);
float blade=exp(-pow((v-center-.13)/(.045+fine*.025),2.))*smoothstep(.19,.55,n);
float fibers=pow(saturate(cos(v*27.+u*9.-Age*11.+n*4.)),6.)*body;
float breakup=smoothstep(.08,.43,n+.12*sin(u*21.-Age*15.));
rgb=amber*(.5+n*.7)+gold*fibers*.6+white*blade*.70;
alpha=saturate(body*.73*breakup+blade*.80+fibers*.28)*end;
alpha*=1.-smoothstep(Open-.02,Open+.10,u);
return float4(rgb,alpha*Envelope);
'''

STRAND = r'''
float u=saturate(UV.x),v=abs(UV.y-.5)*2.;
if(TrailMode>.5) {
 // These planes are consecutive pieces of one real flight path. End-fading
 // each piece creates black seams and turns the curved wake into a dashed rail.
 float core=exp(-pow(v/.48,2.)),edge=exp(-pow(v/.90,2.));
 float3 color=lerp(float3(1.8,.75,.10),float3(3.0,2.2,.80),core*.65);
 return float4(color,saturate(core*.86+edge*.12)*Envelope);
}
float center=exp(-pow(v/lerp(.24,.52,Trail),2.)),body=exp(-pow(v/.76,2.));
float end=smoothstep(.0,.06,u)*(1.-smoothstep(.92,1.,u));
return float4(float3(3.8,2.6,.95)*center+float3(1.4,.53,.08)*body*.40,
             saturate(center*.85+body*.25)*end*Envelope);
'''

ARROW = COMMON + r'''
// Rightmost UV point is the actual tip.  All flight filaments trail behind it.
float y=abs(v-.5);
float shaft=exp(-pow(y/.017,2.))*smoothstep(.03,.16,u)*(1.-smoothstep(.91,.985,u));
float tip=saturate((.985-u)/.15);
float chevron=1.-smoothstep(.011,.025,abs(y-tip*.23));
chevron*=smoothstep(.78,.84,u)*(1.-smoothstep(.975,.99,u));
float body=(1.-smoothstep(.0,.02,y-tip*.23))*smoothstep(.81,.86,u)*(1.-smoothstep(.975,.99,u));
float fibers=0.;
for(int j=0;j<3;j++) {
 float offset=sin(u*(8.+j*3.)+j*2.3)*(.009+(.9-u)*.065);
 fibers+=exp(-pow((v-.5-offset)/.010,2.))*smoothstep(.04,.20,u)*(1.-smoothstep(.74,.88,u))*(.30+n*.50);
}
rgb=white*(shaft*.90+chevron*.68)+gold*(body*.23+fibers*.48);
alpha=saturate(shaft+chevron*.8+body*.48+fibers*.55);
return float4(rgb,alpha*Envelope);
'''


RECURVE_FRAME = COMMON + r'''
float detail=step(1.5,UV.y);
v=detail>.5 ? saturate(UV.y-2.) : v;
float side=saturate(dot(normalize(Normal),normalize(float3(.25,-.40,.87)))*.5+.5);
float ridge=pow(saturate(cos(v*12.56637+u*3.)),9.)*smoothstep(.25,.70,n);
float surge=exp(-pow((u-frac(Age*.95+Index*.19))/.095,2.));
float reveal=1.-smoothstep(Open-.035,Open+.04,u);
float3 dark=float3(.035,.010,.002),face=float3(.24,.085,.012);
rgb=lerp(dark,face,side)+gold*(ridge*.075+surge*ridge*.18)+white*ridge*surge*.08;
rgb=lerp(rgb,float3(.48,.19,.033)+gold*(ridge*.16+surge*.14),detail);
return float4(rgb*(1.+Pulse*.45),(.88+n*.10)*reveal*Envelope);
'''

RECURVE_SAIL = COMMON + r'''
if(UV.y>3.5) {
 float edgeV=UV.y-4.;
 float taper=smoothstep(.0,.07,u)*(1.-smoothstep(.60,1.,u));
 float core=exp(-pow((edgeV-.5-(n-.4)*.12)/.22,2.));
 float3 color=float3(1.9,.72,.08)+float3(3.2,2.5,1.0)*core*.36;
 return float4(color*(1.+Pulse*.90),core*taper*Envelope*(.55+.35*n));
}
if(UV.y>1.5) {
 float membraneV=saturate(UV.y-2.);
 float4 flow=Texture2DSample(Art,ArtSampler,float2(u*.78-Age*.32,membraneV));
 float light=pow(saturate(dot(flow.rgb,float3(.30,.59,.11))*1.8),.72);
 float pockets=smoothstep(.12,.38,n+.10*sin(u*19.+membraneV*9.));
 float margin=smoothstep(.0,.08,membraneV)*(1.-smoothstep(.92,1.,membraneV));
 float ends=smoothstep(.04,.13,u)*(1.-smoothstep(.91,1.,u));
 float vein=exp(-pow((membraneV-(.48+.18*sin(u*10.-Age*2.)))/.055,2.))*smoothstep(.26,.56,n);
 float3 color=lerp(float3(.23,.065,.009),float3(1.15,.51,.095),light)+float3(3.2,2.4,.9)*vein*.30;
 float coverage=(flow.a*(.18+light*.36)*pockets+vein*.15)*margin*ends;
 return float4(color*(1.+Pulse*1.20),coverage*Envelope*(1.-smoothstep(Open-.03,Open+.055,u)));
}
float2 flowUV=float2(u*.76-Age*.37+Index*.13,v);
float4 art=Texture2DSample(Art,ArtSampler,flowUV);
float luminance=dot(art.rgb,float3(.30,.59,.11));
float middle=pow(saturate(luminance*1.9),.75);
float hot=smoothstep(.38,.82,luminance);
float crossFade=smoothstep(.0,.07,v)*(1.-smoothstep(.90,1.,v));
float erosion=smoothstep(.19,.52,n+middle*.22);
float reveal=1.-smoothstep(Open-.035,Open+.055,u);
float lengthFade=smoothstep(.0,.045,u)*(1.-smoothstep(.94,1.,u));
float vein=exp(-pow((v-(.52+.16*sin(u*9.-Age*2.1)))/.055,2.))*smoothstep(.22,.48,n);
float opening=1.-smoothstep(.17,.38,sin(u*17.+Index)*sin(v*9.+u*5.));
rgb=lerp(float3(.25,.065,.006),float3(1.6,.62,.075),middle)+float3(3.4,2.6,1.0)*(hot*.32+vein*.30);
alpha=saturate(art.a*(.32+middle*.64)*erosion*opening+vein*.58)*crossFade*lengthFade*reveal;
return float4(rgb*(1.+Pulse*1.10),alpha*Envelope);
'''

RECURVE_CREST = COMMON + r'''
float face=saturate(dot(normalize(Normal),normalize(float3(.28,-.36,.9)))*.5+.5);
float seam=pow(saturate(cos(v*12.56637)),12.)*smoothstep(.3,.65,n);
float reveal=smoothstep(.32,.82,Open);
rgb=lerp(float3(.10,.025,.003),float3(.69,.28,.055),face)+float3(3.6,2.6,1.1)*seam*.20;
if(UV.y>1.5) {
 float facet=pow(face,3.);
 rgb=float3(.39,.11,.014)+float3(2.8,1.6,.40)*facet+float3(3.8,3.,1.6)*seam*.22;
}
return float4(rgb*(1.+Pulse*.38),reveal*Envelope*.95);
'''

PLASMA_TRAIL = r'''
// The phase is measured along the real flight path, not each mesh segment.
float distance=PathStart+saturate(UV.x)*PathLength;
float2 sampleUV=float2(distance/195.-Age*.62,UV.y);
float4 art=Texture2DSample(Art,ArtSampler,sampleUV);
float light=dot(art.rgb,float3(.30,.59,.11));
float y=UV.y-.5;
float n=pow(saturate(Texture2DSample(Flow,FlowSampler,float2(distance/143.-Age*.41,UV.y*1.4)).r),.45);
float curl=(n-.43)*.11;
float core=exp(-pow((y-curl)/.026,2.));
float broad=exp(-pow(y/.38,2.));
float mid=pow(saturate(light*1.8),.65);
float crest=smoothstep(.36,.78,light);
float3 rgb=lerp(float3(.58,.16,.016),float3(2.8,1.3,.21),mid)+float3(3.5,2.8,1.4)*(crest*.42+core*.32);
float alpha=saturate(art.a*(.30+mid*.72)*broad+core*.50);
return float4(rgb,alpha*Envelope);
'''

LIGHTNING_TRAIL = r'''
float distance=PathStart+saturate(UV.x)*PathLength;
float x=distance/82.;
float y=UV.y-.5;
float pulse=floor(Age*21.);
float a=floor(x*5.), f=frac(x*5.);
float h0=frac(sin((a+pulse*.17)*127.1)*43758.5453)-.5;
float h1=frac(sin((a+1.+pulse*.17)*127.1)*43758.5453)-.5;
float bolt=lerp(h0,h1,f)*.32;
float core=exp(-pow((y-bolt)/.045,2.));
float halo=exp(-pow((y-bolt)/.135,2.));
float b=frac(x*.9-Age*.9);
float branchY=bolt+sin(b*3.14159)*.29*(h0<0.?-1.:1.);
float branch=exp(-pow((y-branchY)/.022,2.))*smoothstep(.04,.13,b)*(1.-smoothstep(.50,.74,b));
float grainCell=floor(x*8.);
float grainY=(frac(sin(grainCell*91.7)*12454.7)-.5)*.84;
float grain=exp(-pow((y-grainY)/.038,2.))*pow(saturate(sin(frac(x*8.)*3.14159)),12.);
float3 rgb=float3(1.25,.52,.055)+float3(3.5,3.0,1.8)*saturate(core+branch)+float3(1.8,.9,.13)*grain;
return float4(rgb,saturate(core*.88+halo*.18+branch*.65+grain*.58)*Envelope);
'''

PLASMA_ARROW = COMMON + r'''
float x=saturate(UV.x), y=UV.y-.5;
float width=.025+pow(saturate(1.-x),.8)*.35;
float4 art=Texture2DSample(Art,ArtSampler,float2(x*.74-Age*.52,UV.y));
float luminance=dot(art.rgb,float3(.30,.59,.11));
float taper=1.-smoothstep(width*.55,width,abs(y));
float tail=smoothstep(.015,.13,x);
float blade=exp(-pow(y/.012,2.))*tail;
float tip=exp(-pow((x-.94)/.045,2.))*exp(-pow(y/.032,2.));
rgb=lerp(float3(.85,.26,.025),gold,pow(saturate(luminance*2.),.7))+white*(blade*.35+tip*.4);
alpha=saturate(art.a*taper*.86+blade*.7+tip*.7)*tail;
return float4(rgb,alpha*Envelope);
'''

LIGHTNING_ARROW = COMMON + r'''
float x=saturate(UV.x), y=UV.y-.5;
float axis=exp(-pow(y/.027,2.))*smoothstep(.02,.14,x);
float zig=sin(x*37.+floor(Age*25.)*.8)*(.98-x)*.12;
float bolt=exp(-pow((y-zig)/.022,2.))*smoothstep(.04,.16,x);
float fork=exp(-pow((abs(y)-(.98-x)*.31)/.012,2.))*smoothstep(.48,.78,x);
float broken=smoothstep(.21,.45,fine);
float headWidth=saturate((.99-x)/.23)*.22;
float head=(1.-smoothstep(headWidth-.008,headWidth+.010,abs(y)))*smoothstep(.735,.78,x)*(1.-smoothstep(.985,1.,x));
float headEdge=exp(-pow((abs(y)-headWidth)/.014,2.))*smoothstep(.75,.80,x)*(1.-smoothstep(.985,1.,x));
rgb=gold*.5+white*(axis*.7+bolt*.55+fork*.35+headEdge*.35)+float3(2.8,1.8,.60)*head*.28;
alpha=saturate(axis*.85+bolt*.7+fork*.6*broken+head*.76+headEdge*.60)*(1.-smoothstep(.985,1.,x));
return float4(rgb,alpha*Envelope);
'''


HELIOS_LIMB = COMMON + r'''
// A broad bevelled body carries the silhouette; emission is confined to its
// sharp borders and moving channels so the layered shape survives bloom.
float side=saturate(dot(normalize(Normal),normalize(float3(.35,-.50,.78)))*.5+.5);
float bevel=pow(abs(v-.5)*2.,8.);
float channel=exp(-pow((v-.36-.045*sin(u*14.))/.042,2.));
float stream=pow(saturate(sin(u*25.-Age*16.+Index*1.7)),6.);
float reveal=1.-smoothstep(Open-.10,Open+.08,u);
float panel=pow(saturate(sin(u*21.)),22.);
float3 body=lerp(float3(.035,.012,.003),float3(.39,.19,.044),pow(side,1.3));
rgb=body+float3(1.8,1.15,.34)*(bevel*.34+channel*.32)+float3(3.2,2.8,1.6)*channel*stream*.32;
rgb*=1.-panel*.24;
return float4(rgb*(1.+Pulse*.70),reveal*Envelope*.99);
'''

HELIOS_FIRE = COMMON + r'''
float cross=abs(v-.5)*2.;
float4 flow=Texture2DSample(Art,ArtSampler,float2(u*1.25-Age*.72+Index*.17,v));
float light=pow(saturate(dot(flow.rgb,float3(.30,.59,.11))*2.5),.55);
float middle=exp(-pow((v-.48-(n-.45)*.12)/.32,2.));
float edge=smoothstep(.0,.13,u)*(1.-smoothstep(.76,1.,u))*(1.-smoothstep(.62,1.,cross));
float rip=pow(saturate(sin(u*32.-Age*19.+n*4.+v*8.)),8.);
float flame=smoothstep(.30,.68,n+light*.17);
float vein=exp(-pow((v-.46-.10*sin(u*14.-Age*4.))/.065,2.));
float reveal=1.-smoothstep(Open-.06,Open+.12,u);
rgb=lerp(float3(.18,.055,.008),float3(1.20,.64,.18),light)+float3(3.4,2.8,1.25)*(vein*.32+rip*.13);
alpha=(flow.a*(.18+light*.45)*flame+middle*.12+vein*.34)*edge*reveal;
return float4(rgb*(1.+Pulse*.65),saturate(alpha)*Envelope);
'''

HELIOS_INLAY = COMMON + r'''
float side=saturate(dot(normalize(Normal),normalize(float3(.3,-.5,.8)))*.5+.5);
float facets=pow(side,3.);
float rim=pow(abs(v-.5)*2.,7.);
float reveal=1.-smoothstep(Open-.10,Open+.10,u);
rgb=float3(.22,.07,.009)+float3(2.2,1.28,.32)*facets+float3(4.2,3.5,1.8)*rim*.36;
return float4(rgb*(1.+Pulse*.48),Envelope*reveal*.98);
'''

HELIOS_TRAIL = r'''
float distance=PathStart+saturate(UV.x)*PathLength;
float2 coord=float2(distance/240.-Age*.65,UV.y);
float n=pow(saturate(Texture2DSample(Flow,FlowSampler,coord*float2(1.8,1.4)).r),.45);
float v=UV.y-.5;
float core=exp(-pow(v/.035,2.));
float wake=exp(-pow((v-(n-.4)*.16)/.28,2.))*smoothstep(.14,.56,n);
float pulse=pow(saturate(sin(distance*.045-Age*21.+n*3.)),8.);
float edge=1.-smoothstep(.30,.5,abs(v));
return float4(float3(2.7,1.4,.25)*(.45+wake*.4)+float3(5.2,4.2,2.)*(core*.75+pulse*.18),
              saturate(core*.90+wake*.54)*edge*Envelope);
'''

HELIOS_ARROW = COMMON + r'''
float y=abs(v-.5),tip=saturate((.99-u)/.20);
float shaft=exp(-pow(y/.018,2.))*smoothstep(.0,.12,u)*(1.-smoothstep(.93,1.,u));
float head=(1.-smoothstep(tip*.24,tip*.24+.016,y))*smoothstep(.76,.82,u);
float blade=exp(-pow((y-tip*.24)/.014,2.))*smoothstep(.76,.82,u);
float stream=exp(-pow((v-.5-.03*sin(u*19.-Age*15.))/.09,2.))*smoothstep(.04,.18,u)*(1.-smoothstep(.72,.86,u));
return float4(float3(4.0,3.4,1.6)*(shaft*.75+blade*.5)+float3(1.5,.62,.06)*(head*.55+stream*.65),
              saturate(shaft+head*.76+blade*.8+stream*.55)*Envelope);
'''


REGALIA_BOW = r'''
// One authored hero silhouette. Keep the carved amber recesses, ivory ridges,
// and attached tip detail instead of washing the whole bow into yellow-white.
float side=abs(UV.x-.5)*2.;
float draw=Draw;
float2 bowUV=UV;
bowUV.y+=(side*side)*(.012*draw-.014*Pulse);
float4 art=Texture2DSample(BowArt,BowArtSampler,bowUV);
float l=dot(art.rgb,float3(.30,.59,.11));
float ridge=smoothstep(.38,.77,l);
float recess=smoothstep(.018,.095,l)*(1.-smoothstep(.22,.51,l));
float wave=pow(saturate(Texture2DSample(Flow,FlowSampler,float2(side*1.8-Age*.78,UV.y*2.5)).r),.58);
float fibers=pow(saturate(Texture2DSample(Flow,FlowSampler,float2(side*3.4-Age*1.3,UV.y*4.0)).g),.70);
float current=pow(wave,3.)*(.35+fibers*.65)*recess;
float sweep=exp(-pow((side-frac(Age*1.2))/.085,2.));
float reveal=1.-smoothstep(Open-.025,Open+.065,side);
float front=exp(-pow((side-Open)/.040,2.))*(1.-smoothstep(.88,1.,Open));
float3 gold=float3(2.6,1.22,.18),ivory=float3(2.7,2.20,1.23);
float3 rgb=art.rgb*.75+gold*(current*.30+sweep*ridge*.09)+ivory*(ridge*.05+front*.30);
rgb+=ivory*ridge*Pulse*.16;
float coverage=art.a*(.74+ridge*.10)*reveal;
return float4(rgb*(1.+Ascended*.09),coverage*Envelope);
'''

REGALIA_STRAND = r'''
float u=saturate(UV.x),v=abs(UV.y-.5)*2.;
float core=exp(-pow(v/.28,2.)),edge=exp(-pow(v/.68,2.));
float end=smoothstep(0.,.045,u)*(1.-smoothstep(.94,1.,u));
return float4(float3(2.5,1.94,.91)*core+float3(1.1,.42,.055)*edge*.27,
              saturate(core*.82+edge*.20)*end*Envelope);
'''

PLUME_BOW = r'''
// The attached feathers are the bow itself. Linear-decoded artwork supplies
// the gaps and barbs; moving light stays inside them instead of bleaching them.
float side=abs(UV.x-.5)*2.;
float4 art=Texture2DSample(BowArt,BowArtSampler,UV);
float l=dot(art.rgb,float3(.30,.59,.11));
float ridge=smoothstep(.42,.90,l);
float inset=smoothstep(.025,.10,l)*(1.-smoothstep(.23,.53,l));
float wave=Texture2DSample(Flow,FlowSampler,float2(side*2.7-Age*.91,UV.y*4.2)).r;
float detail=Texture2DSample(Flow,FlowSampler,float2(side*6.1-Age*1.45,UV.y*9.0)).g;
float flow=pow(saturate(wave),2.3)*(.24+.76*detail);
float sweep=exp(-pow((side-frac(Age*1.35))/.055,2.));
float reveal=1.-smoothstep(Open-.025,Open+.055,side);
float edge=exp(-pow((side-Open)/.028,2.))*(1.-smoothstep(.90,1.,Open));
float3 gold=float3(2.05,.96,.14),ivory=float3(2.30,1.91,1.08);
float3 rgb=art.rgb*.64+gold*(flow*inset*.27+sweep*inset*.12)
    +ivory*(ridge*.035+ridge*flow*.075+edge*.19+Pulse*ridge*.09);
float alpha=art.a*(.77+.09*ridge)*reveal*Envelope;
return float4(rgb*(1.+Ascended*.08),alpha);
'''

REGALIA_ARROW = r'''
float u=saturate(UV.x),y=abs(UV.y-.5);
float shaft=exp(-pow(y/.018,2.))*smoothstep(.05,.20,u)*(1.-smoothstep(.91,.99,u));
float headWidth=saturate((.99-u)/.24)*.16;
float head=(1.-smoothstep(headWidth,headWidth+.012,y))*smoothstep(.74,.79,u);
float bevel=exp(-pow((y-headWidth)/.008,2.))*smoothstep(.74,.80,u);
float inset=exp(-pow(y/.027,2.))*smoothstep(.77,.86,u);
float spine=shaft+bevel*.75+inset*.42;
float tail=exp(-pow(y/.065,2.))*smoothstep(.01,.11,u)*(1.-smoothstep(.40,.68,u));
float3 rgb=float3(2.95,2.35,1.18)*spine+float3(1.42,.64,.09)*(head*.52+tail*.34);
return float4(rgb,saturate(shaft+bevel*.80+head*.65+tail*.30)*Envelope);
'''

REGALIA_TRAIL = r'''
float distance=PathStart+saturate(UV.x)*PathLength;
float y=UV.y-.5;
float n=Texture2DSample(Flow,FlowSampler,float2(distance/170.-Age*.7,UV.y*1.6)).r;
float core=exp(-pow(y/.055,2.));
float filament=exp(-pow((abs(y)-.13-(n-.4)*.018)/.016,2.));
float end=1.-smoothstep(.40,.49,abs(y));
float3 rgb=float3(2.45,1.84,.74)*core+float3(1.3,.54,.065)*filament*.40;
return float4(rgb,saturate(core*.72+filament*.30)*end*Envelope);
'''


def _ensure_strand_usage(material, name):
    if name not in ('M_EStrand','M_E4Trail','M_E5Trail','M_E6Trail','M_E7Trail','M_E7Strand','M_E8Trail','M_E8Strand'):
        return False
    lib=unreal.MaterialEditingLibrary
    usage=unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES
    changed=not lib.has_material_usage(material,usage)
    lib.set_material_usage(material,usage)
    assert lib.has_material_usage(material,usage),'E strand requires instanced-static-mesh shader usage'
    return changed


def _material(name, code, texture, art, bow_art=None, folder=ROOT, spline=False):
    path=folder+'/'+name
    bow_signature=(bow_art.get_path_name()+unreal.EditorAssetLibrary.get_metadata_tag(bow_art,'E7ImageHash')+
                   unreal.EditorAssetLibrary.get_metadata_tag(bow_art,'E8ImageHash')) if 'BowArtSampler' in code else ''
    digest=hashlib.sha256((code+FLOW+(ART if 'ArtSampler' in code else '')+bow_signature).encode()).hexdigest()
    material=unreal.load_asset(path)
    if material and unreal.EditorAssetLibrary.get_metadata_tag(material,'EDesignHash')==digest:
        usage_fixed=_ensure_strand_usage(material,name)
        if spline:
            usage=unreal.MaterialUsage.MATUSAGE_SPLINE_MESH
            usage_fixed |= not unreal.MaterialEditingLibrary.has_material_usage(material,usage)
            unreal.MaterialEditingLibrary.set_material_usage(material,usage)
            assert unreal.MaterialEditingLibrary.has_material_usage(material,usage)
        if usage_fixed:
            unreal.MaterialEditingLibrary.recompile_material(material)
            assert unreal.EditorAssetLibrary.save_loaded_asset(material,False),path
        return material,{'path':path,'reused':True,'instanced_usage_fixed':usage_fixed}
    if material is None:
        material=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,unreal.Material,unreal.MaterialFactoryNew())
    assert material,path
    lib=unreal.MaterialEditingLibrary
    lib.delete_all_material_expressions(material)
    material.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided',True)
    def node(kind,**props):
        obj=lib.create_material_expression(material,getattr(unreal,'MaterialExpression'+kind))
        for key,value in props.items(): obj.set_editor_property(key,value)
        return obj
    shader=node('Custom',code=code,output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    sources={'UV':node('TextureCoordinate'),'Flow':node('TextureObject',texture=texture)}
    if 'ArtSampler' in code: sources['Art']=node('TextureObject',texture=art)
    if 'BowArtSampler' in code:
        assert bow_art, 'Authored bow material requires its owned RGBA texture'
        sources['BowArt']=node('TextureObject',texture=bow_art)
    if 'normalize(Normal)' in code: sources['Normal']=node('PixelNormalWS')
    if 'PathStart' in code:
        for index,(key,default) in enumerate((('PathStart',0.),('PathLength',1.))):
            instance=node('PerInstanceCustomData',data_index=index,const_default_value=default)
            interpolator=node('VertexInterpolator')
            assert lib.connect_material_expressions(instance,'',interpolator,'VS')
            sources[key]=interpolator
    for key,default in (('Age',0.),('Open',1.),('Envelope',1.),('Index',0.),('Pulse',0.),('Ascended',0.),('Trail',0.),('TrailMode',0.),('Draw',0.)):
        sources[key]=node('ScalarParameter',parameter_name=key,default_value=default)
    pins=[]
    for key in sources:
        pin=unreal.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
    shader.set_editor_property('inputs',pins)
    for key,source in sources.items(): assert lib.connect_material_expressions(source,'',shader,key),(name,key)
    for prop,channels in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR,(True,True,True,False)),(unreal.MaterialProperty.MP_OPACITY,(False,False,False,True))):
        mask=node('ComponentMask',r=channels[0],g=channels[1],b=channels[2],a=channels[3])
        assert lib.connect_material_expressions(shader,'',mask,'')
        assert lib.connect_material_property(mask,'',prop)
    _ensure_strand_usage(material,name)
    if spline:
        usage=unreal.MaterialUsage.MATUSAGE_SPLINE_MESH
        lib.set_material_usage(material,usage)
        assert lib.has_material_usage(material,usage),path
    lib.recompile_material(material)
    unreal.EditorAssetLibrary.set_metadata_tag(material,'EDesignHash',digest)
    assert unreal.EditorAssetLibrary.save_loaded_asset(material,False),path
    return material,{'path':path,'reused':False,'hash':digest}


def _geometry(kind):
    vertices,uvs,faces=[],[],[]
    def grid(fn,steps=40,sides=8,closed=False,uvfn=None):
        base=len(vertices)
        for i in range(steps+1):
            u=i/steps
            for j in range(sides if closed else sides+1):
                v=j/sides
                vertices.append(fn(u,v));uvs.append(uvfn(u,v) if uvfn else (u,v))
        count=sides if closed else sides+1
        for i in range(steps):
            for j in range(sides):
                a=base+i*count+j+1;b=base+i*count+(j+1)%count+1
                faces.extend(((a,b,b+count),(a,b+count,a+count)))
    def limb(t):
        return 26.*math.sin(t*math.pi)-25.*t*t,146.*t,math.sin(t*math.pi)*4.
    def recurve(t,side):
        length=196. if side>0 else 179.
        x=-(72. if side>0 else 64.)*math.sin(t*math.pi)+(20. if side>0 else 17.)*t*t
        if side<0: x+=8.*math.sin(t*math.tau)
        return x,side*length*t,math.sin(t*math.tau)*(10. if side>0 else -13.)
    def helios(t):
        return 62.*math.sin(t*math.pi)-15.*t*t,207.*t,math.sin(t*math.pi)*9.
    if kind=='regalia_bow':
        # Generated orthographic RGBA artwork is the only large bow surface.
        # U spans the world side axis; image top is the attack-forward axis.
        # The grip at image (.50,.585) maps to the live bow socket. A shallow
        # 3 cm camber keeps the surface above, rather than below, that plane.
        def fn(u,v):
            return (.585-v)*480.*836./1881.*1.25,(u-.5)*480.,math.sin(u*math.pi)*math.sin(v*math.pi)*3.
        grid(fn,32,16)
    elif kind=='plume_bow':
        # Correct E7's reversed grip/tip direction. The image's upper tips point
        # toward the drawing hand (-X); the projectile always leaves toward +X.
        def fn(u,v):
            return (v-.735)*480.*756./2079.*.90,(u-.5)*480.,math.sin(u*math.pi)*math.sin(v*math.pi)*2.
        grid(fn,40,20)
    elif kind=='helios_limb':
        # A real faceted bow, with separated shell plates rather than repeated
        # thin wires. Four-sided bevels retain a readable dark/gold contrast.
        for layer in range(3):
            lo=(.0,.24,.56)[layer];hi=(.53,.80,1.)[layer]
            def fn(u,v,layer=layer,lo=lo,hi=hi):
                t=lo+(hi-lo)*u;p=helios(t)
                width=(13.+layer*2.)*math.sin(u*math.pi)**.5+.9
                depth=4.5*math.sin(u*math.pi)+.35
                angle=v*math.tau+math.pi*.25
                return p[0]+layer*8.+math.cos(angle)*width,p[1]+math.sin(angle)*width*.22,p[2]+math.sin(angle)*depth+layer*2.2
            grid(fn,40,4,True)
        # Inside-facing blade at the grip grounds the two large limbs.
        def guard(u,v):
            a=v*math.tau;w=(2.+13.*math.sin(u*math.pi))*(1.-u*.8)
            return 8.+43.*u+math.cos(a)*w,24.*u+math.sin(a)*w*.3,math.sin(a)*w*.7
        grid(guard,24,4,True)
    elif kind=='helios_fire':
        # The visible silhouette is the recurved bow, not two full wings.
        # One restrained veil follows its inner edge; only the physical tips
        # carry short attached flow. Large parallel feather tongues are removed.
        for strand in range(1):
            def fn(u,v,strand=strand):
                t=.10+u*.86;p=helios(t)
                sweep=9.*math.sin(u*math.pi)**.75
                x=p[0]+3.+sweep+math.sin(u*7.+strand)*2.
                y=p[1]+u*u*4.
                z=p[2]+math.sin(u*math.pi)*8.
                width=12.*math.sin(u*math.pi)**.65+.1
                return x+(v-.5)*width*2.,y,z+(v-.5)*width*.38
            grid(fn,56,8)
        # Attached tip plume travels outward, never floating ahead of the bow.
        for plume in range(2):
            p=helios(.88+plume*.075)
            def fn(u,v,p=p,plume=plume):
                width=(5.-plume)*math.sin(u*math.pi)**.65+.1
                return p[0]-math.sin(u*math.pi)*9.+u*18.+(v-.5)*width*2.,p[1]+u*(28.-plume*4.),p[2]+plume*4.+math.sin(u*math.pi)*8.
            grid(fn,32,6)
    elif kind=='helios_inlay':
        for index,t in enumerate((.16,.38,.61,.81)):
            p=helios(t)
            def fn(u,v,p=p,index=index):
                w=(5.+index*.8)*math.sin(u*math.pi)+.1
                return p[0]+12.+math.cos(v*math.tau)*w,p[1]+(u-.5)*(24.+index*4.),p[2]+8.+math.sin(v*math.tau)*w
            grid(fn,16,4,True)
    elif kind=='helios_contact':
        def fn(u,v):
            angle=-.8+u*2.5;radius=18.+u*110.
            w=(4.+25.*math.sin(u*math.pi))*(1.-u*.8)
            return -u*42.+math.sin(u*math.pi)*21.,math.cos(angle)*radius+(v-.5)*w*2.,math.sin(angle)*radius+math.sin(v*math.pi)*w*.4
        grid(fn,48,8)
    elif kind=='recurve_frame':
        for side in (-1,1):
            def fn(u,v,side=side):
                p=recurve(u,side);a=recurve(max(0.,u-.001),side);b=recurve(min(1.,u+.001),side)
                dx,dy=b[0]-a[0],b[1]-a[1];length=max(.001,math.hypot(dx,dy))
                width=(4.5+4.0*math.sin(u*math.pi))*(1.-u*.75)
                across=math.cos(v*math.tau)*width
                return p[0]+dy/length*across,p[1]-dx/length*across,p[2]+math.sin(v*math.tau)*width*.65
            grid(fn,64,8,True)
            for index,t in enumerate((.16,.29,.43,.57,.71,.84)):
                for direction in (-1,1):
                    start=recurve(t,side);end=recurve(min(.96,t+.075),side)
                    def fn(u,v,start=start,end=end,t=t,side=side,direction=direction):
                        span=(18.+22.*math.sin(t*math.pi))*u
                        if direction<0: span=(18.+22.*math.sin(t*math.pi))*(1.-u)
                        p=[start[i]+(end[i]-start[i])*u for i in range(3)]
                        p[0]+=span;p[2]+=math.sin(u*math.pi)*5.
                        radius=1.10+math.sin(u*math.pi)*.50
                        return p[0]+math.cos(v*math.tau)*radius,p[1],p[2]+math.sin(v*math.tau)*radius
                    grid(fn,12,4,True,lambda u,v:(u,v+2.))
    elif kind=='recurve_sails':
        for side in (-1,1):
            for layer in range(2):
                def fn(u,v,side=side,layer=layer):
                    p=recurve(u,side)
                    width=(20.+25.*math.sin(u*math.pi))*(.12+.88*math.sin(u*math.pi)**.6)
                    # Two separated ribs with a physical opening between them.
                    # The previous full-width layers overlapped into a solid
                    # yellow plate at the normal gameplay camera distance.
                    across=v*(.30 if layer==0 else .25)+(0. if layer==0 else .69)
                    across+=(.035 if layer==0 else -.035)*math.sin(u*math.pi*2.)
                    x=p[0]+(across*.95-.08)*width
                    y=p[1]+side*math.sin(v*math.pi)*10.*math.sin(u*math.pi)
                    z=p[2]+(1. if layer==0 else -1.)*(3.+math.sin(v*math.pi)*7.)*math.sin(u*math.pi)
                    return x,y,z
                grid(fn,56,8)
            def membrane(u,v,side=side):
                p=recurve(u,side)
                width=(20.+25.*math.sin(u*math.pi))*(.12+.88*math.sin(u*math.pi)**.6)
                return p[0]+(v*.95-.08)*width,p[1],p[2]-4.-math.sin(v*math.pi)*5.*math.sin(u*math.pi)
            grid(membrane,56,10,False,lambda u,v:(u,v+2.))
            for index in range(2):
                p=recurve(.84+index*.07,side)
                def glow(u,v,p=p,side=side,index=index):
                    x=p[0]+32.*u-26.*math.sin(u*math.pi)*(.8+index*.2)
                    y=p[1]+side*(38.+index*8.)*u
                    z=p[2]+math.sin(u*math.pi)*12.+index*5.
                    width=3.0+2.5*math.sin(u*math.pi)
                    return x+(v-.5)*width,y,z+math.sin(v*math.pi)*2.
                grid(glow,24,4,False,lambda u,v:(u,v+4.))
    elif kind=='recurve_crests':
        for side in (-1,1):
            for index,t in enumerate((.30,.66,.91)):
                p=recurve(t,side)
                size=(24.,35.,29.)[index]*(1. if side>0 else .88)
                def fn(u,v,p=p,side=side,size=size):
                    # A closed faceted spur with depth; its moving light sits on
                    # real faces instead of another repeated feather card.
                    thickness=(2.5+5.*math.sin(u*math.pi))*(1.-u*.92)
                    return p[0]-size*u+math.cos(v*math.tau)*thickness*.35,p[1]+side*size*u*.6+math.cos(v*math.tau)*thickness,p[2]+math.sin(v*math.tau)*thickness*.85+u*5.
                grid(fn,12,4,True)
            for fork in (-1,1):
                p=recurve(.955,side)
                def fn(u,v,p=p,side=side,fork=fork):
                    thickness=(1.7+2.2*math.sin(u*math.pi))*(1.-u*.91)
                    return p[0]+u*24.+fork*math.sin(u*math.pi)*7.+math.cos(v*math.tau)*thickness,p[1]+side*u*22.,p[2]+fork*u*8.+math.sin(v*math.tau)*thickness*.60
                grid(fn,14,4,True)
            for t in (.26,.53,.79):
                p=recurve(t,side);p=(p[0]+12.,p[1],p[2]+4.)
                base=len(vertices)
                points=((0,0,4.5),(0,0,-4.5),(4.,0,0),(0,9.,0),(-4.,0,0),(0,-9.,0))
                for index,q in enumerate(points):
                    vertices.append(tuple(p[a]+q[a] for a in range(3)));uvs.append((index/6.,2.+index/6.))
                for f in ((0,2,3),(0,3,4),(0,4,5),(0,5,2),(1,3,2),(1,4,3),(1,5,4),(1,2,5)):
                    faces.append(tuple(base+i+1 for i in f))
    elif kind=='limb':
        def fn(u,v):
            p=limb(u);w=(3.8+3.0*math.sin(u*math.pi))*(1.-u*.78)
            return p[0]+math.cos(v*math.tau)*w,p[1],p[2]+math.sin(v*math.tau)*w*.42
        grid(fn,48,8,True)
    elif kind=='feather':
        roots=(.14,.23,.35,.44,.57,.67,.77,.89)
        lengths=(52.,69.,58.,83.,70.,96.,79.,104.)
        for index in range(8):
            root=limb(roots[index])
            length=lengths[index]
            def fn(u,v,root=root,index=index,length=length):
                x=root[0]-length*(.68*u+.32*u*u)
                y=root[1]+u*(35.+index*4.)+math.sin(u*math.pi)*11.
                z=root[2]+math.sin(u*math.pi)*(4.+index%3*3.)
                width=(10.5-index*.47)*max(.025,math.sin(math.pi*u)**.75)
                return x+(v-.5)*width*.8,y+(v-.5)*width*2.,z+math.sin(v*math.pi)*width*.16
            grid(fn,24,4)
    elif kind=='sweep':
        def fn(u,v):
            # Bow-rooted asymmetric blade, not a constant-radius target ring.
            p0,p1,p2=(12.,-28.),(180.,-320.),(510.,110.)
            x=(1.-u)**2*p0[0]+2.*(1.-u)*u*p1[0]+u*u*p2[0]
            y=(1.-u)**2*p0[1]+2.*(1.-u)*u*p1[1]+u*u*p2[1]
            tx=2.*(1.-u)*(p1[0]-p0[0])+2.*u*(p2[0]-p1[0])
            ty=2.*(1.-u)*(p1[1]-p0[1])+2.*u*(p2[1]-p1[1])
            size=max(.01,math.hypot(tx,ty))
            width=4.+62.*math.sin(u*math.pi)**.8*(.55+u*.45)
            side=(v-.5)*width*2.
            return x-ty/size*side,y+tx/size*side,math.sin(u*math.pi)*17.+(v-.5)*12.
        grid(fn,48,8)
    else: raise ValueError(kind)
    return vertices,uvs,faces


def _uv_range(mesh):
    # Editor-only readback, after import/build and before PIE. The shared OBJ
    # helper deliberately keeps OBJ UV convention; only this design encodes
    # material bands outside 0..1 and therefore needs an explicit check.
    vertices,indices,normals,uvs,tangents=unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh,0,0)
    assert uvs,'E1 imported mesh returned no UV coordinates: '+mesh.get_path_name()
    return {'count':len(uvs),'min_u':min(p.x for p in uvs),'max_u':max(p.x for p in uvs),
            'min_v':min(p.y for p in uvs),'max_v':max(p.y for p in uvs),
            'membrane_detail_vertices':sum(1 for p in uvs if 1.5<p.y<3.5),
            'tip_flow_vertices':sum(1 for p in uvs if p.y>3.5),
            'negative_v_vertices':sum(1 for p in uvs if p.y<-.01)}


def _mesh(output,material,name,kind):
    path=MESH_ROOT+'/'+name
    vertices,uvs,faces=_geometry(kind)
    recurve=kind.startswith('recurve_')
    authored_bow=kind in ('regalia_bow','plume_bow')
    intended_uvs=list(uvs)
    if recurve:
        # FbxStaticMeshImport.cpp (UE 5.8), lines 758/927: imported V = 1 - V.
        # Without compensation, authored bands 2..3 and 4..5 become negative,
        # bypass their shader branch, and hit the basic sail's zero edge mask.
        # Keep the shared importer and every non-E1 mesh unchanged.
        uvs=[(u,1.-v) for u,v in uvs]
    elif authored_bow:
        # The RGBA artwork also has a directional top/bottom: keep its tips
        # pointing forward after OBJ/FBX import instead of flipping the bow.
        uvs=[(u,1.-v) for u,v in uvs]
    digest=hashlib.sha256(repr((vertices,uvs,faces)).encode()).hexdigest()
    mesh=unreal.load_asset(path)
    before_uv=_uv_range(mesh) if mesh and (recurve or authored_bow) else None
    if mesh and unreal.EditorAssetLibrary.get_metadata_tag(mesh,'EDesignMesh')==digest:
        row={'path':path,'reused':True,'triangles':mesh.get_num_triangles(0)}
    else:
        sizes=[max(p[a] for p in vertices)-min(p[a] for p in vertices) for a in range(3)]
        bounds=(sizes[0],sizes[1]-.1,sizes[1]+.1,sizes[2]-.1,sizes[2]+.1)
        importer=runpy.run_path(str(Path(__file__).with_name('countess_ruin_surface.py')))['_import_mesh']
        row=importer(output,material,path,vertices,uvs,faces,'EDesignMesh',digest,bounds,len(faces)-8,48)
        source=Path(row['source_obj']).resolve()
        assert source.parent==output.resolve() and source.name==name+'.obj'
        source.unlink();row['source_obj_removed']=True
        mesh=unreal.load_asset(path)
    if recurve or authored_bow:
        after_uv=_uv_range(mesh)
        expected={'min_u':min(p[0] for p in intended_uvs),'max_u':max(p[0] for p in intended_uvs),
                  'min_v':min(p[1] for p in intended_uvs),'max_v':max(p[1] for p in intended_uvs)}
        passed=all(abs(after_uv[key]-value)<.01 for key,value in expected.items()) and after_uv['negative_v_vertices']==0
        audit={'path':path,'before':before_uv,'after':after_uv,'expected':expected,'passed':passed,
               'reason':('Authored image-space top/bottom preserved through FBX V flip' if authored_bow else
                         'E1-only precompensation of FBX V flip; shader branch IDs remain 2..3 and 4..5')}
        (output/(name+'-uv-audit.json')).write_text(json.dumps(audit,indent=2),encoding='utf-8')
        assert passed,'E1 imported UV differs from shader bands: '+json.dumps(audit)
        row['uv_audit']=audit
    return row


def author(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    texture=unreal.load_asset(FLOW);assert texture,FLOW
    art=unreal.load_asset(ART);assert art,ART
    bow_art,bow_art_row=_bow_art()
    materials={};rows=[]
    for name,code in (('M_ELimb',LIMB),('M_EFeather',FEATHER),('M_ESweep',SWEEP),('M_EStrand',STRAND),('M_E1Arrow',ARROW),('M_E3Arrow',ARROW),
                      ('M_ERecurveFrame',RECURVE_FRAME),('M_ERecurveSails',RECURVE_SAIL),('M_ERecurveCrests',RECURVE_CREST),
                      ('M_E4Trail',PLASMA_TRAIL),('M_E5Trail',LIGHTNING_TRAIL),('M_E4Arrow',PLASMA_ARROW),('M_E5Arrow',LIGHTNING_ARROW),
                      ('M_EHeliosLimb',HELIOS_LIMB),('M_EHeliosFire',HELIOS_FIRE),('M_EHeliosInlay',HELIOS_INLAY),('M_E6Arrow',HELIOS_ARROW),('M_E6Trail',HELIOS_TRAIL),
                      ('M_ERegaliaBow',REGALIA_BOW),('M_E7Arrow',REGALIA_ARROW),('M_E7Trail',REGALIA_TRAIL),('M_E7Strand',REGALIA_STRAND)):
        materials[name],row=_material(name,code,texture,art,bow_art);rows.append(row)
    meshes=[_mesh(output,materials[mat],name,kind) for name,mat,kind in (
        ('SM_ELimb','M_ELimb','limb'),('SM_EFeatherLimb','M_EFeather','feather'),('SM_ESweep','M_ESweep','sweep'),
        ('SM_ERecurveFrame','M_ERecurveFrame','recurve_frame'),('SM_ERecurveSails','M_ERecurveSails','recurve_sails'),('SM_ERecurveCrests','M_ERecurveCrests','recurve_crests'),
        ('SM_EHeliosLimb','M_EHeliosLimb','helios_limb'),('SM_EHeliosFire','M_EHeliosFire','helios_fire'),
        ('SM_EHeliosInlay','M_EHeliosInlay','helios_inlay'),('SM_EHeliosContact','M_EHeliosFire','helios_contact'),
        ('SM_ERegaliaBow','M_ERegaliaBow','regalia_bow'))]
    result={'passed':True,'materials':rows,'meshes':meshes,'images':[bow_art_row],'selector':'Sparrow.EDesign.Style','default':6,
            'styles':{'1':'asymmetric 3D recurved bow, broad flowing sails and faceted crests; one real arrow',
                      '2':'compact physical bow + close sector sweep',
                      '3':'five actual converging arrows; clean thin golden-white wakes',
                      '4':'same actual five arrows and curves; broad irregular plasma-fire wakes',
                      '5':'same actual five arrows and curves; branching lightning and shattering grains',
                      '6':'articulated broad solar bow, separate flowing tongues and faceted inlay, single impulse release',
                      '7':'socket-following horizontal authored hero bow, carved ivory/gold silhouette, flowing inlays and single impulse'},
            'source_assets_changed':False,'visual_acceptance':'pending actual game render'}
    (output/'e-design-author.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result


def author_plume(output):
    """E8-only author entry; retained E1-E7 and their textures stay untouched."""
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    texture=unreal.load_asset(FLOW);assert texture,FLOW
    art=unreal.load_asset(ART);assert art,ART
    plume,image_row=_plume_art()
    materials={};rows=[]
    for name,code in (('M_EFeatherBow',PLUME_BOW),('M_E8Arrow',REGALIA_ARROW),
                      ('M_E8Trail',REGALIA_TRAIL),('M_E8Strand',REGALIA_STRAND)):
        materials[name],row=_material(name,code,texture,art,plume);rows.append(row)
    mesh=_mesh(output,materials['M_EFeatherBow'],'SM_EFeatherBow','plume_bow')
    # The C++ string endpoints use these same source points. A reversal cannot
    # silently be reintroduced by rotating the texture or flipping imported V.
    depth=480.*756./2079.*.90
    tip_x=(.035-.735)*depth
    axis_audit={'attack_axis':'+X','grip_uv':[.5,.735],'grip_x':0.,
                'tip_uv':[[.073,.035],[.927,.035]],'tip_x':tip_x,
                'tip_y':[-.427*480.,.427*480.], 'nock_x_rest':-122.,'nock_x_drawn':-166.,
                'passed':-166.<-122.<tip_x<0.}
    assert axis_audit['passed'],axis_audit
    result={'passed':True,'materials':rows,'meshes':[mesh],'images':[image_row],
            'selector':'Sparrow.EDesign.Style 8','axis_audit':axis_audit,
            'source_assets_changed':False,'visual_acceptance':'pending actual game render'}
    (output/'e8-plume-author.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
