"""Specialize the existing real PIE Q contract for old curve versus new cuts."""
from pathlib import Path

tools = Path(__file__).resolve().parent
text = (tools/'countess_q_dual_compare.py').read_text(encoding='utf-8-sig')
text = text.replace("choice = 1 if enhanced == 'legacy' else (2 if enhanced else 0)", "choice = 3 if enhanced else 2")
text = text.replace("bool(accents) == enhanced", "bool(accents)")
text = text.replace("all('M_CountessQDualSweep' in b['material'] and 'NO_COLLISION' in b['collision']", "all(('M_CountessQOutwardCut' if enhanced else 'M_CountessQDualSweep') in b['material'] and 'NO_COLLISION' in b['collision']")
text = text.replace("if 'SM_CountessQDualSweep' in b['mesh']", "if ('SM_CountessQOutwardCut' if enhanced else 'SM_CountessQDualSweep') in b['mesh']")
text = text.replace("bool(dual)==enhanced", "bool(dual)")
text = text.replace("measured dual Q sweep presentation only; E/gameplay settings preserved", "Q outward cuts versus previous curved strips; E/gameplay settings preserved")
text = text.replace("'the visible blade geometry comes from the measured left and right weapon socket paths'", "'the selected independent blade geometry is present'")
text = text.replace("'only enhanced Q creates its large measured dual-sword sweeps'", "'both controlled variants create their selected Q visuals'")
(tools/'countess_q_outward_compare.py').write_text(text, encoding='utf-8')
motion = (tools/'countess_q_dual_motion.py').read_text(encoding='utf-8-sig')
motion = motion.replace('from countess_q_dual_compare import', 'from countess_q_outward_compare import')
motion = motion.replace("('Q_motion_legacy', motion('legacy')), ", '')
motion = motion.replace('SM_CountessQDualSweep', 'SM_CountessQOutwardCut')
motion = motion.replace('countess_q_dual_motion', 'countess_q_outward_motion')
(tools/'countess_q_outward_motion.py').write_text(motion, encoding='utf-8')
print('Prepared comparison and motion checks for variants 2 and 3.')
