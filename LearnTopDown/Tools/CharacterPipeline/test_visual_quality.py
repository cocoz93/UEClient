"""Regressions for visual failures previously accepted by screenshot-only review."""
import copy
import unittest
from visual_quality import check_quality, PHASES

class VisualQualityTests(unittest.TestCase):
 def setUp(self):
    self.profile={'character_id':'sparrow','presentation_contract':{'quality_gate':dict(expected_cloth_count=[1],cloth_limits={'max_above_head_cm':30,'p95_above_head_cm':10,'max_radius_cm':130},forbidden_effects=['P_ReleaseArrow'],minimum_seconds={})}}
    row=dict(cloth_suspended=False,cloth_disabled=False,cloth_lod=0,cloth_lod_has_data=True,casting=True,cloth=[dict(vertices=432,max_above_head_cm=-8,p95_above_head_cm=-10,max_radius_cm=50)],effects=[])
    samples=[dict(copy.deepcopy(row),time=i/30) for i in range(20)]
    samples[-1]['casting']=False
    self.report=dict(suite='character_visual_quality',passed=True,protected_files_match=True,fixed_simulation_fps=30,character_id='sparrow',map='/Game/TopDown/Lvl_TopDown',cases=[])
    for name in ['locomotion','primary','skill_Q','skill_W','skill_E','skill_R']:
        data=dict(quality_samples=copy.deepcopy(samples),captured_phases=list(PHASES),target_health_before_after=[100,80])
        if name=='skill_E':
            data['target_health_before_after']=[100,100]
            for s in data['quality_samples']:s['casting']=False
        self.report['cases'].append(dict(name=name,data=data))
 def test_complete_timeline_passes(self):
    self.assertTrue(check_quality(self.profile,self.report)['passed'])
 def test_cape_above_head_is_rejected(self):
    self.report['cases'][0]['data']['quality_samples'][5]['cloth'][0]['max_above_head_cm']=130
    with self.assertRaises(ValueError):check_quality(self.profile,self.report)
 def test_missing_midcast_frames_are_rejected(self):
    del self.report['cases'][2]['data']['quality_samples'][4:10]
    with self.assertRaises(ValueError):check_quality(self.profile,self.report)
 def test_camera_plane_is_rejected(self):
    self.report['cases'][2]['data']['quality_samples'][5]['effects']=[dict(active=True,particles=1,template='/Game/P_ReleaseArrow')]
    with self.assertRaises(ValueError):check_quality(self.profile,self.report)
 def test_placeholder_renderer_is_rejected(self):
    self.report['cases'][2]['data']['quality_samples'][5]['effects']=[dict(active=True,particles=1,template='/Game/FX',render_emitters=[dict(particles=1,materials=['/Engine/WorldGridMaterial'])])]
    with self.assertRaises(ValueError):check_quality(self.profile,self.report)
 def test_disabling_cloth_is_rejected(self):
    self.report['cases'][0]['data']['quality_samples'][5]['cloth_suspended']=True
    with self.assertRaises(ValueError):check_quality(self.profile,self.report)
 def test_truncated_tail_is_rejected(self):
    self.profile['presentation_contract']['quality_gate']['minimum_seconds']['skill_Q']=4.0
    with self.assertRaises(ValueError):check_quality(self.profile,self.report)
 def test_legitimate_no_cloth_lod_is_allowed(self):
    row=self.report['cases'][0]['data']['quality_samples'][5]
    row.update(cloth=[],cloth_lod=3,cloth_lod_has_data=False)
    self.assertTrue(check_quality(self.profile,self.report)['passed'])
 def test_missing_particles_at_cloth_lod_is_rejected(self):
    self.report['cases'][0]['data']['quality_samples'][5]['cloth']=[]
    with self.assertRaises(ValueError):check_quality(self.profile,self.report)
 def test_light_only_emitter_material_is_not_a_surface(self):
    self.report['cases'][2]['data']['quality_samples'][5]['effects']=[dict(active=True,particles=1,template='/Game/Light',render_emitters=[dict(particles=1,renders_surface=False,materials=['/Engine/WorldGridMaterial'])])]
    self.assertTrue(check_quality(self.profile,self.report)['passed'])
 def test_unexpired_tail_is_rejected(self):
    self.report['cases'][2]['data']['quality_samples'][-1]['effects']=[dict(active=True,particles=1,template='/Game/FX')]
    with self.assertRaises(ValueError):check_quality(self.profile,self.report)
 def test_blocked_cast_cannot_prove_successful_presentation(self):
    self.report['cases'][-1]['data']['target_health_before_after']=[100,100]
    with self.assertRaises(ValueError):check_quality(self.profile,self.report)
 def test_missing_skill_phase_is_rejected(self):
    self.report['cases'][2]['data']['captured_phases'].remove('action')
    with self.assertRaises(ValueError):check_quality(self.profile,self.report)

if __name__=='__main__':unittest.main()
