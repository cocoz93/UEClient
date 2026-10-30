"""Derive a separate W rim comparison while retaining the prior QA tools."""
from pathlib import Path

p=Path(__file__).resolve().parent
s=(p/'countess_w_compare.py').read_text(encoding='utf-8')
for old,new in (
    ('str(int(enhanced))','str(2 if enhanced else 1)'),
    ('== int(enhanced)','== (2 if enhanced else 1)'),
    ("'CountessW_Dense' in e['template']", "'CountessW_' in e['template']"),
    ("('P_CountessW_DenseRing', 'P_CountessW_DenseTrails', 'P_CountessW_DenseHit')", "('P_CountessW_RimRing', 'P_CountessW_DenseTrails', 'P_CountessW_DenseHit')"),
    ("not any('CountessW_Dense' in n for n in names)", "any('P_CountessW_DenseRing' in n for n in names) and not any('P_CountessW_RimRing' in n for n in names)"),
    ('countess_w_textured_density','countess_w_textured_outer_front'),
    ('W density, original material contrast and visual persistence only','W expanding outer-front texture and thickness only')):
    assert old in s,old
    s=s.replace(old,new)
(p/'countess_w_rim_compare.py').write_text(s,encoding='utf-8')
s=(p/'countess_w_run.py').read_text(encoding='utf-8').replace("'countess_w_compare.py'","'countess_w_rim_compare.py'")
(p/'countess_w_rim_run.py').write_text(s,encoding='utf-8')
s=(p/'countess_w_review.py').read_text(encoding='utf-8').replace("('Previous W', 'Denser original-texture W')", "('Previous dense W', 'Textured outer-front W')")
(p/'countess_w_rim_review.py').write_text(s,encoding='utf-8')
