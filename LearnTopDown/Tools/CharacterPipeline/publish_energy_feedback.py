"""Reuse the previous media encoder and gallery for this focused feedback pass."""
from pathlib import Path

PROJECT=Path(__file__).resolve().parents[2]
QA=PROJECT/'Saved/QA/CharacterPipeline'
ROOT=QA/'sparrow-energy-feedback-20261028'
source=(QA/'sparrow-polish-20261028/publish.py').read_text(encoding='utf-8')
source=source.replace("sparrow_polish_studies.py", "sparrow_energy_feedback.py")
source=source.replace("if run_name=='pilot-fixed30' and ident!='Q1_form':continue", "if run_name=='first30' and ident not in ('E4_normal','E4_form'):continue")
source=source.replace("'Q':('../sparrow-plume-20261028/Q8_form_refined60.webp','../sparrow-plume-20261028/Q8_form_refined60.mp4')", "'Q':('../sparrow-polish-20261028/Q1_form.webp','../sparrow-polish-20261028/Q1_form.mp4')")
source=source.replace("'A':('../sparrow-plume-adoption-20261028/A6_normal.webp','../sparrow-plume-adoption-20261028/A6_normal.mp4')", "'A':('../sparrow-polish-20261028/A_normal.webp','../sparrow-polish-20261028/A_normal.mp4')")
source=source.replace("'E':('../sparrow-plume-20261028/E8_normal_first60.webp','../sparrow-plume-20261028/E8_normal_first60.mp4')", "'E':('../sparrow-polish-20261028/E1_normal.webp','../sparrow-polish-20261028/E1_normal.mp4')")
source=source.replace("'S':('../sparrow-plume-20261028/S103_normal_refined60.webp','../sparrow-plume-20261028/S103_normal_refined60.mp4')", "'S':('../sparrow-polish-20261028/S1_normal.webp','../sparrow-polish-20261028/S1_normal.mp4')")
source=source.replace("'D':('../sparrow-plume-adoption-20261028/D7_normal.webp','../sparrow-plume-adoption-20261028/D7_normal.mp4')", "'D':('../sparrow-polish-20261028/D1_normal.webp','../sparrow-polish-20261028/D1_normal.mp4')")
source=source.replace("'F':('../sparrow-plume-20261028/F7_normal_first60.webp','../sparrow-plume-20261028/F7_normal_first60.mp4')", "'F':('../sparrow-polish-20261028/F2_normal.webp','../sparrow-polish-20261028/F2_normal.mp4')")
source=source.replace("W·A 적용본 / Q·E·S·D·F·Space 선택안", "E1·A 요청 반영 / Q·S·D·F·Space 새 방향 1안씩")
source=source.replace("order=['Q','W','E','A','S','D','F','B']", "order=['Q','E','A','S','D','F','B']")
start=source.index("const names={") if "const names={" in source else source.index("const names=")
end=source.index(";\nconst notes=",start)
source=source[:start]+"const names={Q:'변신 Q · 광핵 낙하',E:'E · E1 문양과 날카로운 깃활',A:'A · 타원 궤도 회전',S:'S · 불꽃의 압축과 파열',D:'D · 활에서 응축 후 분출',F:'F · 흡수와 장창 화살',B:'V Space · 짧은 쌍점 파열'}"+source[end:]
start=source.index('const notes=');end=source.index(';\nfunction render()',start)
source=source[:start]+"const notes={Q:'광핵 응축 → 한 번의 낙하 → 지면 폭발. 새 표현 시안이며 실제 피해 8회는 그대로입니다.',E:'선택한 E1 문양을 실제 발사 신호에 연결했습니다. 몸통은 가늘게, 중앙과 양끝은 뾰족하게 수정했습니다.',A:'두 갈래 화염이 같은 타원을 따라 공전합니다. 속도 160과 기존 판정은 유지했습니다.',S:'선을 더하는 대신 불꽃의 부피와 밝기가 중심으로 압축되고 짧게 터지는 방향입니다.',D:'실제 활 크기를 유지하며 위아래 불꽃이 발사점으로 모이고 짧게 분출합니다.',F:'흡수 흐름은 화살 조각으로 조립되지 않습니다. 마지막에 긴 축·넓은 화살촉·갈라진 화살깃이 펼쳐집니다.',B:'실제 출발·도착 지점에 약 0.18초의 짧은 파열. 이동거리와 조작 복귀는 그대로입니다.'}"+source[end:]
source=source.replace("if(!still&&G.baseline[key]&&mode==='normal'||!still&&key==='Q')", "if(!still&&G.baseline[key]&&(mode==='normal'||key==='Q'))")
source=source.replace("data={'clips':list(clips.values()),'designs':designs,'baseline':baseline}", """old_manifest=json.loads((ROOT.parent/'sparrow-polish-20261028/game-manifest.json').read_text(encoding='utf-8'))
old_ids={'Q':'Q1_form','E':'E1_normal','A':'A_normal','S':'S1_normal','D':'D1_normal','F':'F2_normal'}
baseline_stills={key:[{**s,'src':'../sparrow-polish-20261028/'+s['src']} for s in next(c for c in old_manifest['clips'] if c['id']==ident)['stills']] for key,ident in old_ids.items()}
data={'clips':list(clips.values()),'designs':designs,'baseline':baseline,'baseline_stills':baseline_stills}""")
source=source.replace("if(!still&&G.baseline[key]&&(mode==='normal'||key==='Q'))", "if(G.baseline[key]&&(mode==='normal'||key==='Q'))")
source=source.replace("let b=G.baseline[key];if(b)", "let b=G.baseline[key];let oldStills=G.baseline_stills[key]||[];let baselineImage=still&&oldStills.length?oldStills.reduce((a,b)=>Math.abs(b.time-t)<Math.abs(a.time-t)?b:a).src:slow?b[0].replace('.webp','_half.webp'):b[0];if(b)")
source=source.replace('src="${b[0]}"', 'src="${baselineImage}"')
source=source.replace("document.querySelector('#normal').disabled='QB'.includes(key)", "document.querySelector('#normal').disabled=!G.clips.some(c=>c.key===key&&c.mode==='normal');document.querySelector('#form').disabled=!G.clips.some(c=>c.key===key&&c.mode==='form')")
source=source.replace("if('QB'.includes(key))mode='form';history", "if('QB'.includes(key))mode='form';else if(!G.clips.some(c=>c.key===key&&c.mode===mode))mode='normal';history")
source=source.replace('<h3>${c.option} · ${c.label}', "<h3>${c.key==='E'?'E1 수정본':c.key==='B'?'Space':c.key} · ${c.label}")
(ROOT/'publish.py').write_text(source,encoding='utf-8')
print('Focused gallery encoder prepared')
