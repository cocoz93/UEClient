"""Specialize existing actual-input Q checks for tone and compact length."""
from pathlib import Path

tools=Path(__file__).resolve().parent
text=(tools/'countess_q_outward_compare.py').read_text(encoding='utf-8-sig')
text=text.replace('choice = 3 if enhanced else 2','choice = 3')
anchor="    rig.check(unreal.SystemLibrary.get_console_variable_int_value(CVAR) == choice,"
insertion="    unreal.SystemLibrary.execute_console_command(rig.world, 'Countess.Skills.QTone ' + ('1' if enhanced else '0'))\n    unreal.SystemLibrary.execute_console_command(rig.world, 'Countess.Skills.QLengthScale ' + ('0.52' if enhanced else '1'))\n"
assert text.count(anchor)==1
text=text.replace(anchor,insertion+anchor)
text=text.replace("('M_CountessQOutwardCut' if enhanced else 'M_CountessQDualSweep')", "'M_CountessQOutwardMuted'")
text=text.replace("('SM_CountessQOutwardCut' if enhanced else 'SM_CountessQDualSweep')", "'SM_CountessQOutwardCut'")
text=text.replace("'material':blade.get_material(0).get_editor_property('parent').get_path_name(),", "'material':blade.get_material(0).get_editor_property('parent').get_path_name(), 'tone_mix':blade.get_material(0).get_scalar_parameter_value('ToneMix'),")
anchor="        rig.check(bool(dual), 'the selected independent blade geometry is present')"
addition="\n        rig.check(all(abs(b['scale'][0]-(.52 if enhanced else 1))<.001 for b in dual), 'Q lateral blade scale matches the requested compact or previous full length')\n        rig.check(all(abs(b['tone_mix']-(1 if enhanced else 0))<.001 for a in accents for b in a['blades']), 'every Q visual layer uses the requested actual material tone parameter')"
assert text.count(anchor)==1
text=text.replace(anchor,anchor+addition)
text=text.replace("presentation_variants={'original':2, 'enhanced':3}","presentation_variants={'original':{'tone':0,'lateral_scale':1}, 'enhanced':{'tone':1,'lateral_scale':.52}}")
text=text.replace('Q outward cuts versus previous curved strips; E/gameplay settings preserved','Muted compact Q versus previous bright full length; original mesh, alpha, timing and E/gameplay settings preserved')
viewport_hook="""    def case_generator(self, factory):
        if not getattr(self, 'fixed_viewport_configured', False):
            unreal.SystemLibrary.execute_console_command(self.rig.world, 'CharacterVisualQA.ViewportSize 700 330')
            yield 2 / fps
            self.rig.snapshot()
            self.rig.check(self.rig.latest['viewport_size'] == [700, 330],
                           'actual native PIE viewport is fixed to 700 by 330 before the first capture')
            self.fixed_viewport_configured = True
            self.report['native_fixed_viewport_size'] = [700, 330]
        yield from TrainingRunner.case_generator(self, factory)
        self.rig.check(all(shot['width'] == 700 and shot['height'] == 330 for shot in self.report['screenshots']),
                       'every actual captured PNG keeps the fixed native 700 by 330 size')

"""
assert text.count('class ComparisonRunner(TrainingRunner):\n')==1
text=text.replace('class ComparisonRunner(TrainingRunner):\n','class ComparisonRunner(TrainingRunner):\n'+viewport_hook)
(tools/'countess_q_tone_compare.py').write_text(text,encoding='utf-8')

runner=(tools/'countess_q_outward_run.py').read_text(encoding='utf-8-sig')
runner=runner.replace('countess-q-outward-20261016','q-tone-cape-20261016')
runner=runner.replace("choices=('countess_q_outward_compare.py','countess_q_outward_motion.py'),default='countess_q_outward_compare.py'", "choices=('countess_q_tone_compare.py',),default='countess_q_tone_compare.py'")
(tools/'countess_q_tone_run.py').write_text(runner,encoding='utf-8')
review=(tools/'countess_q_outward_review.py').read_text(encoding='utf-8-sig')
review=review.replace('Previous curved Q','Previous bright full-length Q').replace('New outward cuts','Muted compact Q')
review=review.replace('Q-curve-vs-outward-sampled.gif','Q-tone-length-sampled.gif')
(tools/'countess_q_tone_review.py').write_text(review,encoding='utf-8')
print('Prepared real-input Q tone/length comparison, launcher, and source-hashed sheets.')
