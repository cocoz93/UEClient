"""PIE in the dark training room: key 4 -> Aurora, walk next to a dummy, then for every effect draft set its console value,
cast the skill at the dummy and capture a run of game frames (CharacterVisualQA.Capture <skill>_<value>_<frame>).
Drafts: first round (2026-10-19 「Q·E 이펙트 시안 여러 개」 · 「F 쏠 때 캐릭터 쪽에 이펙트」) compared QStyle·EStyle·FHand 0-3;
second round (「Q는 초승달 검기만 + 얼음 파편도 어울리게」 · 「E는 휘두르는 이펙트 자체가 아쉽다」) compares Aurora.FX.QHit 0-3 with the
crescent and the new Aurora.FX.EStyle swings 0-3. Frame times are seconds after the key press. Puts the defaults back at the end.
Saves no assets."""
import json
import math
import os
from pathlib import Path
import time
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
MAP = '/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom'
# (키, 콘솔 값 이름, 값들, 찍는 때들). Q는 0.3초에 베고, E는 0초부터 휘둘러 0.25초에 내려찍고, F는 0.5초에 던진다.
# 다섯째 판(「Q 흩날리는 이펙트 · S 3에 좀 더 투명하게」): 정한 모습만 한 번씩. 눈송이는 1.3초까지 남아 길게 찍는다.
# (키, 콘솔 값 이름 또는 None, 값들, 찍는 때들, 다음 시안 전 기다림). S 장판은 9초 남는다.
DRAFTS = [
    # 일곱째 판(10-19 오후 「Q 테두리 얇게 + 흩날리는 류 · E 원과 회오리 크기 맞추기 · R 동작 다르게 · A 뒤쪽 육각형」).
    # 갑옷(A)은 12초 남아 다른 시안을 가리므로 맨 끝에 찍는다.
    # (Q·E·A는 같은 판 첫 촬영 aurora-35th-drafts-20261019-152643.) R은 장판 이펙트가 몸을 덮어 동작이 안 보였다 → 빈 바닥에 깔고
    # 0.1초마다 찍어 움직이는 그림으로 본다.
    ('R', 'Aurora.FX.RChannel', (3, 4, 5, 6), tuple(round(0.1 * k, 2) for k in range(1, 27)), 2.5),
]
# 확인 판(「R은 추천대로 · A는 3·4쪽 더, 정중앙은 지워」): 콘솔 값을 건드리지 않고 기본값 그대로 R과 A를 찍는다.
DRAFTS = [
    ('R', None, (0,), tuple(round(0.2 * k, 2) for k in range(1, 14)), 2.5),
    ('A', None, (0,), (1.3, 2.0, 3.0), 0.5),
]
# 여덟째 판(10-19 저녁 「Q·S 공주 같다 → 여전사 느낌 · W 보강할 거 없나 · R 길게 + 손 뻗기 반복 + 계속 터짐 · A 육각형 투명하게」):
# W는 지금 그대로, Q는 지금(2)과 여전사풍 3·4, R은 새 기본(7, 4초), A는 새 투명도, S는 여전사풍 4와 지금(3).
# A 갑옷은 12초 남아 몸을 덮으므로 S 앞에서 끝날 때까지 기다리고, S 3의 반짝임은 9초 동안 이어 뜨므로 S 3을 맨 끝에 찍는다.
DRAFTS = [
    ('W', None, (0,), (0.05, 0.1, 0.15, 0.2, 0.3, 0.45, 0.7, 1.0), 1.0),
    ('Q', 'Aurora.FX.QBoost', (2, 3, 4), (0.35, 0.42, 0.5, 0.65, 0.85, 1.1), 2.0),
    ('R', None, (0,), tuple(round(0.2 * k, 2) for k in range(1, 24)), 2.0),
    ('A', None, (0,), (1.3, 2.0, 3.0), 12.5),
    ('S', 'Aurora.FX.SStyle', (4, 3), (0.55, 0.65, 0.8, 1.2, 2.5), 0.5),
]
# 확인 판(「Q, S 그렇게 가 보자 · W도 넣어 봐」): 콘솔 값을 건드리지 않고 새 기본값(Q 3 · S 4)과 W 맞은 자리 파편을 찍는다.
DRAFTS = [
    ('W', None, (0,), (0.05, 0.1, 0.15, 0.2, 0.3, 0.45, 0.7, 1.0), 1.0),
    ('Q', None, (0,), (0.35, 0.42, 0.5, 0.65, 0.85, 1.1), 2.0),
    ('S', None, (0,), (0.55, 0.65, 0.8, 1.2, 2.5), 0.5),
]
# 아홉째 판(10-19 밤 「R 애니 어색 — 다른 거 없나, 자연스럽게 · A 더 많이 옅게 · S 롤백하고 기존 원에 깨진 듯한 이펙트 ·
# D·F 방향은 괜찮은데 이펙트가 아쉽다, 시안」): R은 지금(7)·몸이 안 튀게(8)·칼로 얼음 깎기(9)를 0.1초마다(움직이는 그림용),
# D·F는 지금(0)과 시안 1~3, S는 되돌린 3과 고리가 깨진 6·7, 끝에 A(새 투명도, 12초 남음).
# F는 꽂히는 자리가 보이게 허수아비에서 550 떨어져 허수아비를 겨눈다(WALK_BACK). S 3·6·7은 반짝임이 9초 이어 떠서 사이를 9초 둔다.
DRAFTS = [
    ('R', 'Aurora.FX.RChannel', (7, 8, 9), tuple(round(0.1 * k, 2) for k in range(1, 45)), 2.0),
    ('D', 'Aurora.FX.DStyle', (0, 1, 2, 3), (0.3, 0.36, 0.42, 0.5, 0.6, 0.75, 0.95, 1.3), 1.5),
    ('F', 'Aurora.FX.FStyle', (0, 1, 2, 3), (0.55, 0.62, 0.7, 0.78, 0.9, 1.1, 1.4), 1.5),
    ('S', 'Aurora.FX.SStyle', (3, 6, 7), (0.55, 0.65, 0.75, 0.9, 1.3, 3.0), 9.0),
    ('A', None, (0,), (1.3, 2.0, 3.0), 0.5),
]
WALK_BACK = {'F': 550.0}
# 확인 판(「R9으로 칼 휘두를 때마다 캐릭터 쪽 이펙트 + 해당 지점 터짐 · D 2·3 중 하나 + 칼을 땅에 박는 동작 · F 적당히 · A 더 낮추고
# 옆 육각형을 뒤쪽으로 이어서」): 콘솔 값을 건드리지 않고 새 기본값(R 9 · D 3 · F 2)과 A를 찍는다. D는 칼이 꽂히기 전부터 찍는다.
DRAFTS = [
    ('R', None, (0,), tuple(round(0.1 * k, 2) for k in range(1, 45)), 2.0),
    ('D', None, (0,), (0.1, 0.2, 0.3, 0.36, 0.42, 0.5, 0.65, 0.8, 1.0), 1.5),
    ('F', None, (0,), (0.55, 0.62, 0.7, 0.78, 0.9, 1.1, 1.4), 1.5),
    ('A', None, (0,), (1.3, 2.0, 3.0), 0.5),
]
# 큰 틀 판(10-19 밤 「E는 E1로」): 전 기본(0 회오리 + 바닥 원)과 새 기본 4(칼 궤적 + 얼음 가둠)를 같은 때에 찍는다.
# 0.25초에 내려찍어 묶고 1.5초 묶은 뒤(1.75초) 깨진다. 금 가는 조각은 1.5초.
DRAFTS = [
    ('E', 'Aurora.FX.EStyle', (0, 4), (0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.55, 0.9, 1.5, 1.6, 1.75, 1.85, 2.0), 1.0),
]
# 칼 궤적을 정한 뒤 확인(움직이는 그림용): 0.05초마다 2.1초. 깨진 연기가 다음 시전을 가리지 않게 사이를 3초 둔다.
if os.environ.get('DRAFTS_E_FINE') == '1':
    DRAFTS = [('E', 'Aurora.FX.EStyle', (0, 4), tuple(round(0.05 * k, 2) for k in range(1, 43)), 3.0)]
# 이어서 E 4의 칼 궤적 고르기: 콘솔 값 이름을 묶음으로 주면 값도 같은 차례의 묶음이다(궤적 에셋 0~3 × 소켓 0 손 · 1 칼날).
if os.environ.get('DRAFTS_E_TRAIL') == '1':
    DRAFTS = [('E', ('Aurora.FX.ETrailSockets', 'Aurora.FX.ETrail'), tuple((s, t) for s in (0, 1) for t in range(4)),
               tuple(round(0.03 * k, 2) for k in range(1, 12)) + (0.45,), 1.0)]
# 큰 틀 판 2(10-19 밤 「Q 두 번 누르기 — 예 · R은 나」): Q는 새 기본 5 — 0은 Q1이 끝난 뒤(0.75초) 0.85초에 다시 눌러 Q2,
# 1은 Q1 도중 0.5초에 미리 눌러 Q1이 끝나는 순간 Q2. R은 허수아비를 장판 안에 두고(420 물러나 허수아비를 겨눔) 전(0) · 회오리(1).
# 여섯째 칸 = 시전 뒤 더 누를 키(초, 키).
if os.environ.get('DRAFTS_QR') == '1':
    DRAFTS = [
        ('Q', None, (0,), tuple(round(0.05 * k, 2) for k in range(1, 33)), 1.5, ((0.85, 'Q'),)),
        ('Q', None, (1,), tuple(round(0.05 * k, 2) for k in range(1, 33)), 1.5, ((0.5, 'Q'),)),
        ('R', 'Aurora.FX.RField', (0, 1), tuple(round(0.1 * k, 2) for k in range(1, 49)), 3.0),
    ]
    WALK_BACK = {'R': 420.0}
    AIM_AT_DUMMY = {'R'}
    # 첫 판은 장판 가운데가 허수아비 위라 끌어당길 거리가 0이었다 → 허수아비 옆 170을 겨눈다.
    AIM_SIDE = {'R': 170.0}
# 「Q는 차라리 얼음 검기를 두세 번 · E는 롤백」: 새 기본 Q 6(검기 셋)과 되돌린 E 0을 콘솔 값 없이 찍는다. Q는 셋째 검기까지 1.3초.
if os.environ.get('DRAFTS_Q6') == '1':
    DRAFTS = [
        ('Q', None, (0,), tuple(round(0.05 * k, 2) for k in range(1, 31)), 1.5),
        ('E', None, (0,), (0.1, 0.2, 0.3, 0.5, 0.9, 1.5, 1.8), 1.0),
    ]
# 「S 눈 모양 유지하면서 거친 느낌」: 새 기본 5(눈송이 균열)와 4(균열)를 같은 때에 찍는다.
if os.environ.get('DRAFTS_S_FLAKE') == '1':
    DRAFTS = [('S', 'Aurora.FX.SStyle', (5, 4), (0.55, 0.65, 0.8, 1.2, 2.5), 0.5)]
# S 그림 바탕(10-20 「S는 한번 그려봐」): 장판이 깔리기 전 빈 바닥과, 같은 자리에 지금 장판이 깔린 모습.
if os.environ.get('DRAFTS_S_PLATE') == '1':
    DRAFTS = [('S', None, (0,), (0.02, 3.0), 0.5)]
# S 마법진 모양 시안(10-20 「S는 모양 이게 최선인가? 시안 더 줘」): DRAFTS_S_SWAP = 시안 그림 PNG(쉼표). 시작 전에 /Game/AuroraDrafts로
# 가져오고(장판 그림과 같은 설정), S를 한 번 깔아 지금 그림을 찍은 뒤 깔린 장판의 그림(FlakeTexture)만 차례로 바꿔 끼워 찍는다
# (자리·카메라가 같다). 끝나면 Content/AuroraDrafts 폴더는 지운다.
SWAP_DRAFTS = [p for p in os.environ.get('DRAFTS_S_SWAP', '').split(',') if p]
SWAP_FOLDER = '/Game/AuroraDrafts'
# 이어서 「그 진하기를 절반 이하로」: DRAFTS_S_SCALE = 진하기 배율(선·퍼진 빛·별빛 불투명도에 곱함). 주면 지금 그림도 같은 배율로
# 바꿔 끼워 한 번 더 찍는다(재질 기본값 = aurora_frost_materials_build.py M_Aurora_SnowFloor).
# 불투명도 0.45배가 화면 선 대비로는 약 0.7배였다(선이 밝게 빛나 화면 밝기 곡선 위쪽에서 눌림) → 쉼표로 여러 배율을 주면 배율마다 한 벌씩 찍는다.
SWAP_SCALES = [float(s) for s in os.environ.get('DRAFTS_S_SCALE', '1').split(',')]
SWAP_SCALE = SWAP_SCALES[0]
SWAP_OPACITY = {'LineOpacity': 0.35, 'HaloOpacity': 0.04, 'GlintStrength': 0.25}
SWAP_CURRENT = '/Game/TopDown/Characters/Aurora/FX/T_Aurora_SnowCircle'
if SWAP_DRAFTS:
    DRAFTS = [('S', None, (0,), (1.5,), 0.0)]
# 10-20 저녁 시안 묶음(「S 다 아쉬운데 원인 파악해서 다시 · Q 검기 날리는 거 시안, 필요하면 조합 · V 바닥에 오브젝트 깔리는 거 말고」):
# DRAFTS_Q_R52 · DRAFTS_V_R52 · DRAFTS_S_R52 = 1인 것만 차례로. Q = Aurora.FX.QWave 0·1·2·4·7(검기 셋이 1.05초에 끝남),
# V = Aurora.FX.VLand 0~4(1.2초에 착지, 얼음은 1.2초 뒤 터짐), S = 아래 S_FEEL(콘솔 값 + 깔린 장판 재질 사본 값, 0.1초마다 움직이는 그림용).
EVENING = [k for k in ('Q', 'V', 'S') if os.environ.get(f'DRAFTS_{k}_R52') == '1']
if EVENING:
    DRAFTS = []
    if 'Q' in EVENING:
        # DRAFTS_Q_VALUES = 찍을 값만(쉼표) — 첫 판 뒤 2(Yin 채찍 잔상이 검기보다 멀리 앞서 날아가 따로 놂)를 빼고 1 + 4만 더 찍었다
        values = tuple(int(v) for v in os.environ.get('DRAFTS_Q_VALUES', '0,1,2,4,7').split(','))
        DRAFTS.append(('Q', 'Aurora.FX.QWave', values, tuple(round(0.2 + 0.05 * k, 2) for k in range(21)), 1.5))
    if 'V' in EVENING:
        DRAFTS.append(('V', 'Aurora.FX.VLand', (0, 1, 2, 3, 4), tuple(round(1.1 + 0.08 * k, 2) for k in range(22)), 2.0))
# S 느낌 시안(원인 후보마다 하나): 지금 · 돎(바깥 띠 20도/초, 안쪽 반대로 11도/초) · 번쩍+맥동(깔리는 순간 빛 3.5배에서 0.5초에
# 가라앉고 2초마다 ±35%) · 빛(장판 위 푸른 빛 + 선 둘레 푸른 번짐) · 셋 다. 빛이 있는 시안은 끝에 둔다(빛은 9초 남아 다음 시안에 비친다).
# 첫 판 뒤 고침: 선 화소가 거의 무채색(채도 중앙값 0.07, 평균 RGB 181·188·196)이라 빛 시안은 선 자체도 파랗게(WhiteColour) ·
# 돎은 원 밖을 지움(CircleMask — 원 밖 UV가 이웃 칸 그림을 비춰 호가 생겼다) · 번쩍·맥동은 재질이 불투명도 같이 올린다.
S_FLASH = (2.5, 1.8, 1.2, 0.7, 0.3, 0.0)
S_GLOW = {'HaloOpacity': 0.3, 'IceColour': (0.08, 0.35, 1.0), 'WhiteColour': (0.45, 0.75, 1.0)}
S_SPIN = {'SpinOuter': 0.35, 'SpinInner': -0.2, 'CircleMask': 1.0}
S_PULSE = {'PulseStrength': 0.35, 'GlowBoost': 'flash'}
S_FEEL = [('now', {}, {}), ('spin', {}, S_SPIN), ('pulse', {}, S_PULSE), ('light', {'Aurora.FX.SLight': 60}, S_GLOW),
          ('all', {'Aurora.FX.SLight': 60}, {**S_SPIN, **S_PULSE, **S_GLOW})] if 'S' in EVENING else []
S_FEEL_FRAMES = tuple(round(0.55 + 0.1 * k, 2) for k in range(25))
# 10-20 밤 시안 묶음(「Q 다 아쉽다, 시안 가자 · V 지금 나오는 오브젝트들을 빽빽하게 — 부하 많이 걸리려나, 추가 시안 더」):
# DRAFTS_Q_R53 · DRAFTS_V_R53 = 1인 것만. Q = Aurora.FX.QBlade 비트 0·1·2·4·7·13, V = Aurora.FX.VDense 0~4(찍는 때는 R52와 같다).
# Q는 허수아비가 없는 화면 가로 쪽(월드 방위 -45도)으로 쏜다 — 허수아비에 맞는 터짐이 검기를 덮었다(r52 Q 0).
NIGHT = [k for k in ('Q', 'V') if os.environ.get(f'DRAFTS_{k}_R53') == '1']
if NIGHT:
    DRAFTS = []
    if 'Q' in NIGHT:
        values = tuple(int(v) for v in os.environ.get('DRAFTS_Q_VALUES', '0,1,2,4,7,13').split(','))
        DRAFTS.append(('Q', 'Aurora.FX.QBlade', values, tuple(round(0.2 + 0.05 * k, 2) for k in range(21)), 1.5))
        AIM_YAW = {'Q': -45.0}
    if 'V' in NIGHT:
        DRAFTS.append(('V', 'Aurora.FX.VDense', (0, 1, 2, 3, 4), tuple(round(1.1 + 0.08 * k, 2) for k in range(22)), 2.0))
# 이어서(「Q 7번이 그나마 — 더 크게·굵게·빠르게·멀리·거칠게, 퀄리티도 · V 얼음 오브젝트 지우고 다른 이펙트」): DRAFTS_Q_R54 · DRAFTS_V_R54 = 1인 것만.
# Q = QBlade 7(지금 고른 것)·23(+ 큰 검기 16)·55(+ 잔상 줄기 32)·119(+ 파편 강화 64), V = VLand 0·5~8(충격파는 0.25초에 퍼져 0.05초마다).
LATE = [k for k in ('Q', 'V') if os.environ.get(f'DRAFTS_{k}_R54') == '1']
if LATE:
    DRAFTS = []
    if 'Q' in LATE:
        DRAFTS.append(('Q', 'Aurora.FX.QBlade', (7, 23, 55, 119), tuple(round(0.2 + 0.05 * k, 2) for k in range(21)), 1.5))
        AIM_YAW = {'Q': -45.0}
    if 'V' in LATE:
        DRAFTS.append(('V', 'Aurora.FX.VLand', (0, 5, 6, 7, 8), tuple(round(1.1 + 0.05 * k, 2) for k in range(34)), 2.0))
# 이어서(「Q 23 기반으로 여러 시안 · V 8 기반으로 여러 시안 · S 거친 느낌이 없다, 방법 없나」): DRAFTS_R55 = Q·V·S 중 찍을 키(쉼표).
# Q = (QBlade, QBig) 23·31(원뿔 뺌)에 QBig 1·2·4·8·15, V = (VLand, VNova) 8에 VNova 1·2·4·8·15(얼음이 터지는 2.4초까지),
# S = SRough 0~3(0.1초마다 2.5초 — 돎·맥동이 보이게).
FINAL = [k for k in os.environ.get('DRAFTS_R55', '').split(',') if k]
if FINAL:
    DRAFTS = []
    if 'Q' in FINAL:
        DRAFTS.append(('Q', ('Aurora.FX.QBlade', 'Aurora.FX.QBig'), ((23, 0), (31, 0), (23, 1), (23, 2), (23, 4), (23, 8), (23, 15)),
                       tuple(round(0.2 + 0.05 * k, 2) for k in range(21)), 1.5))
        AIM_YAW = {'Q': -45.0}
    if 'V' in FINAL:
        DRAFTS.append(('V', ('Aurora.FX.VLand', 'Aurora.FX.VNova'), ((8, 0), (8, 1), (8, 2), (8, 4), (8, 8), (8, 15)),
                       tuple(round(1.1 + 0.05 * k, 2) for k in range(34)), 2.0))
    if 'S' in FINAL:
        DRAFTS.append(('S', 'Aurora.FX.SRough', (0, 1, 2, 3), tuple(round(0.55 + 0.1 * k, 2) for k in range(25)), 0.3))
# 이어서(「S 2가 그나마 괜찮긴 한데 — 한계야? 시안 더」): DRAFTS_R56=1 = (SStyle, SRough) 게임 기본 1에 SRough 2 바탕 2·6(잔 결)·
# 10(딱 끊김)·26(딱 끊김 + 큰 조각)·14(잔 결 + 딱 끊김) + 참고 (2, 2)(안에 서리 깔기 — R55까지 이 도구는 SStyle 3으로 찍어 안 서리 +
# 서리 터짐이 같이 나왔다). 찍는 때는 R55와 같다.
if os.environ.get('DRAFTS_R56') == '1':
    DRAFTS = [('S', ('Aurora.FX.SStyle', 'Aurora.FX.SRough'), ((1, 2), (1, 6), (1, 10), (1, 26), (1, 14), (2, 2)),
               tuple(round(0.55 + 0.1 * k, 2) for k in range(25)), 0.3)]
# 이어서(「Q 퀄리티가 너무 아쉬운데 뭐가 문제지 · R 러프하게라도 찍어서 보여 줄 수 있나」): DRAFTS_R57=1 = Q 기본(23)을 빈 바닥(월드 방위
# -45도)으로 0.03초마다 + R 러프 시안 Aurora.FX.RDraft 1~5(허수아비에서 420 물러나 허수아비를 겨눔). 4는 1.0초에 Q를 눌러 분신 검기까지.
# 3(칼날 폭풍)은 4.35초까지라 0.1초마다.
if os.environ.get('DRAFTS_R57') == '1':
    DRAFTS = [
        ('Q', None, (0,), tuple(round(0.2 + 0.03 * k, 2) for k in range(36)), 1.5),
        ('R', 'Aurora.FX.RDraft', (1,), tuple(round(0.05 * k, 2) for k in range(1, 31)), 1.5),
        ('R', 'Aurora.FX.RDraft', (2,), tuple(round(0.05 * k, 2) for k in range(1, 45)), 1.5),
        ('R', 'Aurora.FX.RDraft', (3,), tuple(round(0.1 * k, 2) for k in range(1, 50)), 1.0),
        ('R', 'Aurora.FX.RDraft', (4,), tuple(round(0.05 * k, 2) for k in range(1, 56)), 1.5, ((1.0, 'Q'),)),
        ('R', 'Aurora.FX.RDraft', (5,), tuple(round(0.05 * k, 2) for k in range(1, 35)), 1.5),
    ]
    AIM_YAW = {'Q': -45.0}
    WALK_BACK = {'R': 420.0}
    AIM_AT_DUMMY = {'R'}
    # DRAFTS_R57_PICK = 다시 찍을 R 시안 번호(쉼표) — 주면 Q는 빼고 그 R만
    if os.environ.get('DRAFTS_R57_PICK'):
        picked = [int(v) for v in os.environ['DRAFTS_R57_PICK'].split(',')]
        DRAFTS = [d for d in DRAFTS if d[0] == 'R' and d[2][0] in picked]
# 이어서(10-21 「Q 시안 만들어 줘 · 1은 별 모양 말고 눈 모양 어때?」): DRAFTS_R58=1 = Q 기본(23)에 Aurora.FX.QLook 0·1·2·3·4·8·15를
# R57과 같은 때에 + R 러프 시안 1(눈 결정 모양으로 바꾼 얼음 난무)
if os.environ.get('DRAFTS_R58') == '1':
    DRAFTS = [
        ('Q', 'Aurora.FX.QLook', (0, 1, 2, 3, 4, 8, 15), tuple(round(0.2 + 0.03 * k, 2) for k in range(36)), 1.5),
        ('R', 'Aurora.FX.RDraft', (1,), tuple(round(0.05 * k, 2) for k in range(1, 31)), 1.5),
    ]
    AIM_YAW = {'Q': -45.0}
    WALK_BACK = {'R': 420.0}
    AIM_AT_DUMMY = {'R'}
# 이어서(10-21 「지금 Q가 제일 낫다 — 다른 시안 · Q 빠르게 · R 1로, 눈 모양 이펙트 신경 + 순간이동 어색함 시안 · F는 분신 셋 돌격」):
# DRAFTS_R59=1 = Q 기본(23, 빨라진 0.2초)에 Aurora.FX.QFeel 0·1·2·4·7 + R(얼음 난무 기본)에 Aurora.FX.RBlink 0·1·2·4·8·5·15 +
# F 기본(분신 셋 돌격, 허수아비 반대쪽 빈 바닥). R은 R57처럼 420 물러나 허수아비를 겨눈다.
if os.environ.get('DRAFTS_R59') == '1':
    DRAFTS = [
        # QFeel 2(바닥 길)는 두 판 다 아니어서 C++에서 뺐다
        ('Q', 'Aurora.FX.QFeel', (0, 1, 4, 5), tuple(round(0.2 + 0.03 * k, 2) for k in range(32)), 1.5),
        ('F', None, (0,), tuple(round(0.4 + 0.04 * k, 2) for k in range(24)), 1.5),
        ('R', 'Aurora.FX.RBlink', (0, 1, 2, 4, 8, 5, 15), tuple(round(0.05 * k, 2) for k in range(1, 31)), 1.5),
    ]
    AIM_YAW = {'Q': -45.0, 'F': -45.0}
    WALK_BACK = {'R': 420.0}
    AIM_AT_DUMMY = {'R'}
# 이어서(10-21 「Q는 어쩌면 좋을까 — 검기 날리는 게 문제인가, 다른 추가 이펙트를 붙이는 건 어때 · F는 W 진행 중인 동작처럼」):
# DRAFTS_R60=1 = Q 기본에 Aurora.FX.QAdd 0·1·2·4·8·15 — 맞는 순간이 보이게 허수아비에서 420 물러나 허수아비를 겨눈다 + F 기본(분신 셋이
# W 돌진 자세로, 허수아비 반대쪽 빈 바닥 — 끝까지 나는 모습 확인용)
if os.environ.get('DRAFTS_R60') == '1':
    DRAFTS = [
        ('Q', 'Aurora.FX.QAdd', (0, 1, 2, 4, 8, 15), tuple(round(0.2 + 0.03 * k, 2) for k in range(36)), 1.5),
        ('F', None, (0,), tuple(round(0.4 + 0.04 * k, 2) for k in range(24)), 1.5),
    ]
    AIM_YAW = {'F': -45.0}
    WALK_BACK = {'Q': 420.0}
# 이어서(10-21 「Q는 칼 궤적만 — 뭐가 문제일까, 검기 이펙트 시안 여러 개 · 다 만들어서」): DRAFTS_R61=1 = Q 기본(23 + 칼 궤적)에
# Aurora.FX.QShape 0~4(골격 넷) — 검기 모양이 가려지지 않게 허수아비 없는 화면 가로 쪽(월드 방위 -45도)으로
if os.environ.get('DRAFTS_R61') == '1':
    DRAFTS = [('Q', 'Aurora.FX.QShape', (0, 1, 2, 3, 4), tuple(round(0.2 + 0.03 * k, 2) for k in range(36)), 1.5)]
    AIM_YAW = {'Q': -45.0}
# 이어서(「누운 초승달 형태가 좋은데 이펙트 시안을 더」): DRAFTS_R62=1 = Aurora.FX.QSkin 0·1·2·4·8·16 — R61과 같은 쪽·때
# (두 판은 공기 일그러짐 세기를 0.03~5로 같이 찍었는데 바닥이 그대로여서 C++에서 뺐다)
if os.environ.get('DRAFTS_R62') == '1':
    DRAFTS = [('Q', 'Aurora.FX.QSkin', (0, 1, 2, 4, 8, 16), tuple(round(0.2 + 0.03 * k, 2) for k in range(36)), 1.5)]
    AIM_YAW = {'Q': -45.0}
# 이어서(「얼음 모양 매나 새 같은 게 날아가는 거 어때? F는」): DRAFTS_R63=1 = Aurora.FX.FBird 0(분신)·1(그림 매)·2(결정 매) —
# 허수아비 없는 화면 가로 쪽으로 끝까지 날아 부서지는 데까지
if os.environ.get('DRAFTS_R63') == '1':
    DRAFTS = [('F', 'Aurora.FX.FBird', (0, 1, 2), tuple(round(0.4 + 0.03 * k, 2) for k in range(30)), 1.5)]
    AIM_YAW = {'F': -45.0}
# 이어서(「매는 훨씬 더 얇은 느낌 · 매 아니어도 여러 시안」 · 「E 얼음 5~10초 유지 · A 바닥 이펙트 말고 다른 것 · A 무늬 시안 · Q 두 개만 눕혀」):
# DRAFTS_R64=1 = F 1(그 전 매)·3~6 · Q 새 기본(눕힌 둘, 확인용) · E 둘레 결정이 8초 서 있는지 · A 발밑 이펙트 ACast 0~5와 무늬 APattern
# 0~5를 짝지어(보호막 12초가 다음 시안을 가려 갑옷 하나에 한 짝씩) — 맨 끝
if os.environ.get('DRAFTS_R64') == '1':
    DRAFTS = [('F', 'Aurora.FX.FBird', (1, 3, 4, 5, 6), tuple(round(0.4 + 0.03 * k, 2) for k in range(30)), 1.5),
              ('Q', None, (0,), tuple(round(0.2 + 0.04 * k, 2) for k in range(20)), 1.0),
              ('E', None, (0,), (0.6, 1.5, 3.0, 5.0, 7.0, 7.8, 8.6, 9.5), 1.0),
              ('A', ('Aurora.FX.ACast', 'Aurora.FX.APattern'), tuple((k, k) for k in range(6)),
               tuple(round(0.2 + 0.08 * k, 2) for k in range(16)) + (2.5, 4.0), 9.0)]
    AIM_YAW = {'F': -45.0, 'Q': -45.0}
# 이어서(10-25 「R 다른 휘두르는 애니메이션 없어? 지금도 어정쩡해 보이는데 · F는 매 한 마리만 일직선으로 날아가서 펑」):
# DRAFTS_R65=1 = R 잔상 동작 Aurora.FX.RSwing 0~7(R59처럼 420 물러나 허수아비를 겨눔, 잔상이 사라지는 1.8초까지) + F 새 기본(확인용)
if os.environ.get('DRAFTS_R65') == '1':
    DRAFTS = [('R', 'Aurora.FX.RSwing', tuple(range(8)), tuple(round(0.05 * k, 2) for k in range(1, 37)), 1.5),
              ('F', None, (0,), tuple(round(0.4 + 0.04 * k, 2) for k in range(24)), 1.5)]
    AIM_YAW = {'F': -45.0}
    WALK_BACK = {'R': 420.0}
    AIM_AT_DUMMY = {'R'}
# 이어서(10-25 「고드름 비 가자 — 하늘에서 얼음송곳들이 일정하게 대각선으로」): DRAFTS_R67=1 = D 고드름 비(Aurora.FX.DRain 1 기본),
# 허수아비에서 420 물러나 허수아비를 겨눔(원 가운데에 허수아비). 그 전 R66(범위 얼음송곳 DArea)은 지웠다.
if os.environ.get('DRAFTS_R67') == '1':
    DRAFTS = [('D', 'Aurora.FX.DRain', tuple(int(v) for v in os.environ.get('DRAFTS_D_VALUES', '1').split(',')), tuple(round(0.05 * k, 2) for k in range(1, 47)), 1.5)]
    WALK_BACK = {'D': 420.0}
    AIM_AT_DUMMY = {'D'}
# 이어서(10-25 59차 무인 — 「R 눈 1/2 + A 쓰면 분신도 보호막 · S 또렷하게 · D 퀄리티 · F 매 모양」): DRAFTS_R69=1 = S 새 기본(확인용) ·
# D 퀄리티 Aurora.FX.DLook 0·1·2·4·7 · F 매 Aurora.FX.FBird 3(지금 얇은 매)·7(꽉 찬 매)·8(날씬한 매) · 맨 끝에 A를 켜고 0.9초에 R(보호막이
# 난무 동안 숨는지, 눈꽃 1/2 확인용 — A 보호막 12초가 다른 시안을 가리지 않게 끝에)
if os.environ.get('DRAFTS_R69') == '1':
    DRAFTS = [('S', None, (0,), (0.6, 1.0, 2.0), 1.0),
              ('D', 'Aurora.FX.DLook', (0, 1, 2, 4, 7), tuple(round(0.05 * k, 2) for k in range(1, 47)), 1.5),
              ('F', 'Aurora.FX.FBird', (3, 7, 8), tuple(round(0.4 + 0.03 * k, 2) for k in range(30)), 1.5),
              ('A', None, (0,), tuple(round(0.9 + 0.05 * k, 2) for k in range(36)), 1.5, ((0.9, 'R'),))]
    AIM_YAW = {'F': -45.0}
    WALK_BACK = {'D': 420.0, 'A': 420.0}
    AIM_AT_DUMMY = {'D', 'A'}
# 이어서(10-26 70차 「A는 4번에서 손만 뻗는 동작만 · D 꽂히는 얼음 오브젝트 다른 거 · F 이펙트 보완」): DRAFTS_R70=1 = A 새 동작(확인용) ·
# D 창 모양 Aurora.FX.DSpear 0~4 · F 매 보완 Aurora.FX.FLook 0·1·2·4·8·15 — F는 허수아비에서 800 물러나 겨눠 멈춰 터지는 자리가 화면 안에
if os.environ.get('DRAFTS_R70') == '1':
    DRAFTS = [('A', None, (0,), tuple(round(0.04 * k, 2) for k in range(1, 31)), 1.5),
              ('D', 'Aurora.FX.DSpear', (0, 1, 2, 3, 4), tuple(round(0.05 * k, 2) for k in range(1, 47)), 1.5),
              ('F', 'Aurora.FX.FLook', tuple(int(v) for v in os.environ.get('DRAFTS_F_VALUES', '0,1,2,4,8,15').split(',')),
               tuple(round(0.4 + 0.03 * k, 2) for k in range(30)), 1.5)]
    WALK_BACK = {'D': 420.0, 'F': 800.0}
    AIM_AT_DUMMY = {'D', 'F'}
# 이어서(10-26 71차 「3D 매 — 디테일은 필요 없고 매라고 느끼기만」): DRAFTS_R71=1 = F 그림 매 8 · 입체 매 9(FLook은 게임 기본 12 = 느리게 + 몸 빛)
if os.environ.get('DRAFTS_R71') == '1':
    DRAFTS = [('F', 'Aurora.FX.FBird', (8, 9), tuple(round(0.4 + 0.03 * k, 2) for k in range(30)), 1.5)]
    WALK_BACK = {'F': 800.0}
    AIM_AT_DUMMY = {'F'}
# 이어서(10-26 72차 「매가 날아가는 쪽에 이펙트 시안 · D 니 권장대로 · 이펙트를 톤 맞춰서 새로 제작하는 건 불가능한가」): DRAFTS_R72=1 =
# F 나는 쪽 이펙트 Aurora.FX.FTrail 0·1·2·4·8(입체 매 · 느리게 + 몸 빛) · D 새 기본에 팩 결정 색 바꿔 끼우기 Aurora.FX.DTint 0·1·2
if os.environ.get('DRAFTS_R72') == '1':
    DRAFTS = [('F', 'Aurora.FX.FTrail', (0, 1, 2, 4, 8), tuple(round(0.4 + 0.03 * k, 2) for k in range(30)), 1.5),
              ('D', 'Aurora.FX.DTint', (0, 1, 2), tuple(round(0.05 * k, 2) for k in range(1, 41)), 1.5)]
    WALK_BACK = {'D': 420.0, 'F': 800.0}
    AIM_AT_DUMMY = {'D', 'F'}
# 이어서(같은 날 「입체 매로 일단 하되, 매가 소환되는 타이밍에 뭔가 이펙트가」): DRAFTS_R73=1 = F 등장 이펙트 Aurora.FX.FSummon 0~4 — 던지기 전부터
if os.environ.get('DRAFTS_R73') == '1':
    DRAFTS = [('F', 'Aurora.FX.FSummon', (0, 1, 2, 3, 4), tuple(round(0.3 + 0.03 * k, 2) for k in range(30)), 1.5)]
    WALK_BACK = {'F': 800.0}
    AIM_AT_DUMMY = {'F'}
# 이어서(같은 날 75차 「저 얼음 오브젝트 말고 다르게 표현할 방법은 없나」): DRAFTS_R75=1 = D 꽂힌 자리 Aurora.FX.DMark 0(결정) · 1(바닥 서리 자국)
if os.environ.get('DRAFTS_R75') == '1':
    DRAFTS = [('D', 'Aurora.FX.DMark', (0, 1), tuple(round(0.05 * k, 2) for k in range(1, 41)), 1.5)]
    WALK_BACK = {'D': 420.0}
    AIM_AT_DUMMY = {'D'}
# 이어서(같은 날 76차 「내가 준 레퍼런스 참고하지 말고 니가 자유롭게 시안 여러 개」): DRAFTS_R76=1 = D 지금(0) · 새 시안 Aurora.FX.DFresh 1~3,
# 빛줄기가 0.09초에 떨어져 0.04초마다 찍는다(움직이는 그림용)
if os.environ.get('DRAFTS_R76') == '1':
    DRAFTS = [('D', 'Aurora.FX.DFresh', (0, 1, 2, 3), tuple(round(0.04 * k, 2) for k in range(1, 51)), 1.5)]
    WALK_BACK = {'D': 420.0}
    AIM_AT_DUMMY = {'D'}
# 이어서(77차 「2, 3 괜찮은 것 같은데 퀄리티를 높이거나 다양한 방식으로 또 시안 여러 개」): DRAFTS_R77=1 = 다듬은 4·5 · 새 6·7·8
if os.environ.get('DRAFTS_R77') == '1':
    DRAFTS = [('D', 'Aurora.FX.DFresh', (4, 5, 6, 7, 8), tuple(round(0.04 * k, 2) for k in range(1, 51)), 1.5)]
    WALK_BACK = {'D': 420.0}
    AIM_AT_DUMMY = {'D'}
# 이어서(78차 「결계 아이디어를 S 마법진에 · 궁극기는 D로 빼고 V는 블리자드처럼 얼음송곳이 쏟아지는 광역기」): DRAFTS_R78=1 =
# V 눈보라 Aurora.FX.VStorm 1·2 · S 둘레 얼음(확인용) · D가 옛 궁극기로 나가는지(확인용)
if os.environ.get('DRAFTS_R78') == '1':
    DRAFTS = [('V', 'Aurora.FX.VStorm', (1, 2), tuple(round(0.1 * k, 2) for k in range(3, 49)), 1.5),
              ('S', 'Aurora.FX.SIce', (1,), (0.55, 0.6, 0.65, 0.7, 0.8, 0.95, 1.2, 2.0, 4.0), 1.0),
              ('D', None, (0,), (0.6, 1.0, 1.3, 1.6), 1.5)]
    WALK_BACK = {'V': 520.0}
    AIM_AT_DUMMY = {'V', 'D'}
# 이어서(79차 「범위 두 배 · 누가 봐도 궁극기로 보이게 화려하게 · 맵 전체에 눈보라」): DRAFTS_R79=1 = V Aurora.FX.VStorm 1(화면 어둡게) · 2(안 어둡게),
# 마지막 거대 결정(4.25초) 뒤까지
if os.environ.get('DRAFTS_R79') == '1':
    DRAFTS = [('V', 'Aurora.FX.VStorm', (1, 2), tuple(round(0.1 * k, 2) for k in range(3, 60)), 1.5)]
    WALK_BACK = {'V': 520.0}
    AIM_AT_DUMMY = {'V'}
# 이어서(81차 「어둡게 하자 · 얼음송곳 좀 더 날카롭게, 이펙트 다듬어」): DRAFTS_R81=1 = V 기본(1)만 — 내 확인용
if os.environ.get('DRAFTS_R81') == '1':
    DRAFTS = [('V', 'Aurora.FX.VStorm', (1,), tuple(round(0.1 * k, 2) for k in range(3, 48)), 1.5)]
    WALK_BACK = {'V': 520.0}
    AIM_AT_DUMMY = {'V'}
# 이어서(84차 「매 날리기 빼고 2번 캐릭터 F를 얼음 빛깔로 넣어 봐」): DRAFTS_R84=1 = F 얼음 결정 사격(Aurora.FX.FShot 1) — 모이는 0~0.5초 · 나가는 0.5초 뒤
if os.environ.get('DRAFTS_R84') == '1':
    DRAFTS = [('F', 'Aurora.FX.FShot', (1,), tuple(round(0.04 * k, 2) for k in range(1, 31)), 1.5)]
    WALK_BACK = {'F': 800.0}
    AIM_AT_DUMMY = {'F'}
# 이어서(85차 「전혀 2번 캐릭터의 F 스킬 느낌이 아닌데」): DRAFTS_R85=1 = 원본을 본다 — DRAFTS_CHARACTER=Two로 Sparrow F(Crystal Shot).
# 같은 묶음을 기본(Four)으로 돌리면 오로라 F(0 = 매가 아니라 FShot을 안 건드림 — 게임 기본 1)
if os.environ.get('DRAFTS_R85') == '1':
    DRAFTS = [('F', None, (0,), tuple(round(0.04 * k, 2) for k in range(1, 36)), 1.5)]
    WALK_BACK = {'F': 800.0}
    AIM_AT_DUMMY = {'F'}
# 이어서(86차 「캐릭터 뒤쪽에 얼음 덩어리들이 각자 덩어리를 만들고 여러 명을 타겟팅」): DRAFTS_R86=1 = F 얼음 덩어리 일제 사격 —
# 허수아비 여럿이 1100 안에 들도록 600만 물러남, 다섯 발이 다 꽂힐 때까지
if os.environ.get('DRAFTS_R86') == '1':
    DRAFTS = [('F', None, (0,), tuple(round(0.04 * k, 2) for k in range(1, 38)), 1.5)]
    WALK_BACK = {'F': 600.0}
    AIM_AT_DUMMY = {'F'}
# 87차(10-28 「E, D 빼고 다 아쉽다 — 이펙트·마감」): DRAFTS_R87=1 = 마감 재작업 전 지금 모습 기준 — 콘솔 값을 건드리지 않고
# 바꿀 스킬 여덟을 차례로. 키마다 그 사거리에 맞게 다시 걸어 선다(Space는 허수아비를 지나 끝까지 돌진하므로 그 뒤 자리가 바뀐다).
# S 장판은 9초 남아 A를 덮으므로 다 꺼질 때까지 기다린다.
if os.environ.get('DRAFTS_R87') == '1':
    DRAFTS = [('Q', None, (0,), tuple(round(0.2 + 0.04 * k, 2) for k in range(21)), 1.5),
              ('W', None, (0,), tuple(round(0.05 * k, 2) for k in range(1, 26)), 1.5),
              ('SpaceBar', None, (0,), tuple(round(0.05 * k, 2) for k in range(1, 25)), 1.5),
              ('R', None, (0,), tuple(round(0.1 * k, 2) for k in range(1, 47)), 2.0),
              ('F', None, (0,), tuple(round(0.04 * k, 2) for k in range(1, 38)), 1.5),
              ('V', None, (0,), tuple(round(0.1 * k, 2) for k in range(1, 51)), 2.5),
              ('S', None, (0,), (0.55, 0.6, 0.7, 0.8, 1.0, 1.3, 2.0, 4.0), 9.5),
              ('A', None, (0,), tuple(round(0.04 * k, 2) for k in range(1, 31)) + (2.0, 4.0), 0.5)]
    WALK_BACK = {'Q': 170.0, 'W': 600.0, 'SpaceBar': 300.0, 'R': 420.0, 'F': 600.0, 'V': 520.0, 'S': 170.0, 'A': 170.0}
    AIM_AT_DUMMY = {'R', 'F', 'V'}
# 88차(87차 답 반영 확인): DRAFTS_R88=1 = W 남는 분신 자세 시안 1~3(분신은 1.5초 남음) · Q 결정 파열 · Space-2 · R-2 감옥 · F 결정 파열
if os.environ.get('DRAFTS_R88') == '1':
    DRAFTS = [('Q', None, (0,), tuple(round(0.2 + 0.04 * k, 2) for k in range(21)), 1.5),
              ('W', 'Aurora.FX.WPose', (1, 2, 3), tuple(round(0.1 * k, 2) for k in range(1, 17)), 1.5),
              ('SpaceBar', None, (0,), tuple(round(0.05 * k, 2) for k in range(1, 31)), 1.5),
              ('R', None, (0,), tuple(round(0.1 * k, 2) for k in range(1, 27)), 2.0),
              ('F', None, (0,), tuple(round(0.04 * k, 2) for k in range(1, 46)), 1.5)]
    WALK_BACK = {'Q': 170.0, 'W': 600.0, 'SpaceBar': 300.0, 'R': 420.0, 'F': 600.0}
    AIM_AT_DUMMY = {'R', 'F'}
# 92차(87차 마감 재작업 통합 — 결과 한 판): DRAFTS_R92=1 = 바꾼 여덟을 기본값 먼저 + 콘솔 시안. 값이 많아 두 번에 나눠 찍는다
# (DRAFTS_ONLY=Q,W,SpaceBar,R,F · DRAFTS_ONLY=S,A)
if os.environ.get('DRAFTS_R92') == '1':
    DRAFTS = [('Q', 'Aurora.FX.QSlash', (1, 2), tuple(round(0.2 + 0.03 * k, 2) for k in range(24)), 1.5),
              ('W', 'Aurora.FX.WPose', (2, 1, 3), tuple(round(0.1 * k, 2) for k in range(1, 17)), 1.5),
              ('SpaceBar', None, (0,), tuple(round(0.05 * k, 2) for k in range(1, 31)), 1.5),
              ('R', None, (0,), tuple(round(0.1 * k, 2) for k in range(1, 27)), 2.0),
              ('F', 'Aurora.FX.FChunk', (1, 2), tuple(round(0.04 * k, 2) for k in range(1, 38)), 1.5),
              ('S', 'Aurora.FX.SPolish', (1, 2), (0.3, 0.55, 0.7, 0.9, 1.3, 2.0, 4.0), 9.5),
              ('A', 'Aurora.FX.APolish', (1, 2), tuple(round(0.1 * k, 2) for k in range(1, 16)) + (2.5, 6.0, 12.3), 1.0)]
    AIM_YAW = {'Q': -45.0}
    WALK_BACK = {'Q': 420.0, 'W': 600.0, 'SpaceBar': 300.0, 'R': 420.0, 'F': 600.0, 'S': 170.0, 'A': 170.0}
    AIM_AT_DUMMY = {'R', 'F'}
    REWALK = {'W'}
# 95차(94차 답 — Q 아주 얇게 · R 연기 자연스럽게 · S 왕관 작게 · F 동작 시안 · V 시안 더): DRAFTS_R95=1
if os.environ.get('DRAFTS_R95') == '1':
    DRAFTS = [('Q', 'Aurora.FX.QSlash', (10, 11, 8), tuple(round(0.2 + 0.03 * k, 2) for k in range(24)), 1.5),
              ('R', 'Aurora.FX.RPrison', (4,), tuple(round(0.05 * k, 2) for k in range(1, 31)), 2.0),
              ('F', 'Aurora.FX.FMotion', (1, 2, 3, 0), tuple(round(0.04 * k, 2) for k in range(1, 31)), 1.5),
              ('V', 'Aurora.FX.VLook', (4, 5, 6), tuple(round(0.1 * k, 2) for k in range(1, 51)), 2.5),
              ('S', 'Aurora.FX.SPolish', (3,), (0.3, 0.55, 0.7, 0.9, 1.3, 2.0, 4.0), 9.5)]
    AIM_YAW = {'Q': -45.0}
    WALK_BACK = {'Q': 420.0, 'R': 420.0, 'F': 600.0, 'V': 520.0, 'S': 170.0}
    AIM_AT_DUMMY = {'R', 'F', 'V'}
# 94차(93차 답 — Q 「그림 톤·게임 톤과 안 맞음」 · R·A·S·F·V 시안 더): DRAFTS_R94=1. DRAFTS_R94_Q = 찍을 QSlash 값(쉼표)
if os.environ.get('DRAFTS_R94') == '1':
    DRAFTS = [('Q', 'Aurora.FX.QSlash', tuple(int(v) for v in os.environ.get('DRAFTS_R94_Q', '7,8,9').split(',')),
               tuple(round(0.2 + 0.03 * k, 2) for k in range(24)), 1.5)]
    AIM_YAW = {'Q': -45.0}
    WALK_BACK = {'Q': 420.0}
    # DRAFTS_R94_REST=1 = 나머지 — R 감옥 4·5·3 · F 검 4·5 · V 2·3·1 · S 3~6 · A(동작, 보호막) 짝 셋(갑옷 12초라 맨 끝, 값마다 끝날 때까지)
    if os.environ.get('DRAFTS_R94_REST') == '1':
        DRAFTS = [('R', 'Aurora.FX.RPrison', (4, 5, 3), tuple(round(0.1 * k, 2) for k in range(1, 27)), 2.0),
                  ('F', 'Aurora.FX.FChunk', (4, 5), tuple(round(0.04 * k, 2) for k in range(1, 38)), 1.5),
                  ('V', 'Aurora.FX.VLook', (2, 3, 1), tuple(round(0.1 * k, 2) for k in range(1, 51)), 2.5),
                  ('S', 'Aurora.FX.SPolish', (3, 4, 5, 6), (0.3, 0.55, 0.7, 0.9, 1.3, 2.0, 4.0), 9.5),
                  ('A', ('Aurora.FX.AMotion', 'Aurora.FX.AShell'), ((1, 2), (2, 3), (3, 1)),
                   tuple(round(0.05 * k, 2) for k in range(1, 18)) + (1.2, 2.0, 4.0), 12.5)]
        WALK_BACK = {'R': 420.0, 'F': 600.0, 'V': 520.0, 'S': 170.0, 'A': 170.0}
        AIM_AT_DUMMY = {'R', 'F', 'V'}
# 93차(92차 결과 답 — Q 검기 최종 시안 3~6 · R 분신 거리 + 감옥 회오리/떠서 도는 결정 · D 조각 대신 · F 얼음송곳 · S 옅게 · A 시전 동작):
# DRAFTS_R93=1. A는 갑옷이 12초 남아 몸을 덮으므로 맨 끝에 값마다 다 끝날 때까지 기다리고, S 장판(9초)은 그 앞에
if os.environ.get('DRAFTS_R93') == '1':
    DRAFTS = [('Q', 'Aurora.FX.QSlash', (3, 4, 5, 6), tuple(round(0.2 + 0.03 * k, 2) for k in range(24)), 1.5),
              ('R', 'Aurora.FX.RPrison', (2, 3), tuple(round(0.1 * k, 2) for k in range(1, 27)), 2.0),
              ('D', 'Aurora.FX.DShard', (2, 1, 0), tuple(round(0.1 * k, 2) for k in range(1, 36)), 1.5),
              ('F', 'Aurora.FX.FChunk', (3,), tuple(round(0.04 * k, 2) for k in range(1, 38)), 1.5),
              ('S', None, (0,), (0.3, 0.55, 0.7, 0.9, 1.3, 2.0, 4.0), 9.5),
              ('A', 'Aurora.FX.AMotion', (1, 2, 3, 0), tuple(round(0.04 * k, 2) for k in range(1, 16)) + (0.8, 1.2), 12.5)]
    AIM_YAW = {'Q': -45.0}
    WALK_BACK = {'Q': 420.0, 'R': 420.0, 'F': 600.0, 'S': 170.0, 'A': 170.0}
    AIM_AT_DUMMY = {'R', 'F'}
# 91차(A·S 게임 안 시안): DRAFTS_R91=1 = Aurora.FX.SPolish 0·1·2(장판 9초) → Aurora.FX.APolish 0·1·2(갑옷 12초 — 끝나 판이 부서지는
# 것까지 다음 값 전에)
if os.environ.get('DRAFTS_R91') == '1':
    DRAFTS = [('S', 'Aurora.FX.SPolish', (0, 1, 2), (0.3, 0.55, 0.7, 0.9, 1.3, 2.0, 4.0, 8.0), 9.5),
              ('A', 'Aurora.FX.APolish', (0, 1, 2), tuple(round(0.1 * k, 2) for k in range(1, 16)) + (2.5, 6.0, 11.0, 12.3), 1.0)]
    WALK_BACK = {'S': 170.0, 'A': 170.0}
# 90차(F 덩어리 자체 재작업): DRAFTS_R90=1 = Aurora.FX.FChunk 0 그 전 · 1 얼음 바위 · 2 결정 창 — 허수아비 여럿을 겨눠(86차와 같은 자리)
if os.environ.get('DRAFTS_R90') == '1':
    DRAFTS = [('F', 'Aurora.FX.FChunk', (0, 1, 2), tuple(round(0.04 * k, 2) for k in range(1, 38)), 1.5)]
    # DRAFTS_F_SKIN=1 = 덩어리 재질 비교(분신 얼음 0 · 팩 재질 1, 둘 다 FChunk 1)
    if os.environ.get('DRAFTS_F_SKIN') == '1':
        DRAFTS = [('F', ('Aurora.FX.FChunk', 'Aurora.FX.FChunkSkin'), ((1, 0), (1, 1), (2, 1)), tuple(round(0.04 * k, 2) for k in range(1, 38)), 1.5)]
    WALK_BACK = {'F': 600.0}
    AIM_AT_DUMMY = {'F'}
# 89차(Q 검기 자체 재작업): DRAFTS_R89=1 = Aurora.FX.QSlash 0 그 전 · 1 날 선 검기 · 2 결정 검기를 같은 자리·방향(화면 가로)에서
if os.environ.get('DRAFTS_R89') == '1':
    DRAFTS = [('Q', 'Aurora.FX.QSlash', (0, 1, 2), tuple(round(0.2 + 0.03 * k, 2) for k in range(24)), 1.5)]
    AIM_YAW = {'Q': -45.0}
    WALK_BACK = {'Q': 420.0}
# W 사거리 확인(59차 「W 사거리 2배 이상」 700 → 1500): DRAFTS_W_FAR=1 = 허수아비에서 1200 물러나 W(그 전 사거리면 Out of range)
if os.environ.get('DRAFTS_W_FAR') == '1':
    DRAFTS = [('W', None, (0,), (0.3, 0.6, 0.9), 1.5)]
    WALK_BACK = {'W': 1200.0}
    AIM_AT_DUMMY = {'W'}
# V 부하 재기(같은 날 「너무 부하가 많이 걸릴려나?」): DRAFTS_V_PERF = 잴 VDense 값(쉼표). 값마다 PERF_REPEAT번 번갈아 쏘고, 찍지 않고
# 장면마다 실제로 걸린 시간을 적는다(-UseFixedTimeStep이라 게임 시간은 장면마다 1/60초씩 가고, 실제 시간이 곧 한 장면 계산·그리기 비용).
# 구간 = 쏘기 전 1초(기준) · 결정이 다 선 1.4~2.3초 · 부서지는 2.4~2.9초. 결정 수는 1.6초에 월드 설정 액터 밑 Freeze_Segment 부품을 센다.
PERF_VALUES = [int(v) for v in os.environ.get('DRAFTS_V_PERF', '').split(',') if v]
PERF_REPEAT = 3
if PERF_VALUES:
    DRAFTS = []
# F 나는 꼬리 시안(10-20 「날아갈 때가 밋밋 — 시안 줘 봐」): Aurora.FX.FFlight 0~3. 0.5초에 던져 1400cm를 약 0.6초에 난다 —
# 허수아비가 없는 화면 가로 쪽(월드 방위 -45도)으로 던져 끝까지 날게 하고 0.04초마다 찍는다(움직이는 그림용).
if os.environ.get('DRAFTS_F_FLIGHT') == '1':
    DRAFTS = [('F', 'Aurora.FX.FFlight', (0, 1, 2, 3), tuple(round(0.48 + 0.04 * k, 2) for k in range(20)), 1.5)]
    AIM_YAW = {'F': -45.0}
# R 손 다시 뻗기 확인(시전 1.5~3.2초를 0.05초마다): 다시 뻗는 때는 시전 1.75 · 2.45 · 3.15 · 3.85초
if os.environ.get('DRAFTS_R_FINE') == '1':
    DRAFTS = [('R', None, (0,), tuple(round(1.5 + 0.05 * k, 2) for k in range(35)), 2.0)]
# DRAFTS_ONLY = 찍을 키만(쉼표, 예: W) — 빌드 전 바이너리로 바뀌지 않은 스킬만 먼저 볼 때
if os.environ.get('DRAFTS_ONLY'):
    DRAFTS = [d for d in DRAFTS if d[0] in os.environ['DRAFTS_ONLY'].split(',')]
DEFAULTS = {'Aurora.FX.QStyle': 1, 'Aurora.FX.QHit': 3, 'Aurora.FX.QBoost': 3, 'Aurora.FX.SStyle': 3, 'Aurora.FX.EStyle': 4, 'Aurora.FX.ETrail': 0, 'Aurora.FX.ETrailSockets': 1,
            'Aurora.FX.ERing': 1, 'Aurora.FX.FHand': 1, 'Aurora.FX.RChannel': 9, 'Aurora.FX.DStyle': 3, 'Aurora.FX.FStyle': 2}
# 키 → 그 시안들 앞에서 허수아비로부터 물러설 거리(없으면 처음 자리 170 그대로)
WALK_BACK = globals().get('WALK_BACK', {})
# 빈 바닥 대신 허수아비를 겨눌 키(R은 원래 빈 바닥에 깐다) · 그때 허수아비 옆으로 비킬 거리
AIM_AT_DUMMY = globals().get('AIM_AT_DUMMY', set())
AIM_SIDE = globals().get('AIM_SIDE', {})
# 허수아비와 상관없이 이 월드 방위(도)로 700 앞을 겨눌 키
AIM_YAW = globals().get('AIM_YAW', {})
REWALK = globals().get('REWALK', set())
DEFAULTS.update({'Aurora.FX.QStyle': 6, 'Aurora.FX.RField': 1, 'Aurora.FX.EStyle': 0, 'Aurora.FX.QBlade': 0, 'Aurora.FX.VDense': 0,
                 'Aurora.FX.VLand': 0, 'Aurora.FX.QBig': 0, 'Aurora.FX.VNova': 0, 'Aurora.FX.SRough': 0})
# 10-20 밤 게임 기본값(「Q는 23 · V는 8에 VNova 8 빼고 다」) + S는 게임 기본 1(10-20 오후 39차부터) — 위 3이 남아 S 시안에 안 서리와
# 서리 터짐(37차에 뺀 것)이 같이 찍혔다
DEFAULTS.update({'Aurora.FX.QBlade': 23, 'Aurora.FX.VLand': 8, 'Aurora.FX.VNova': 7, 'Aurora.FX.SStyle': 1, 'Aurora.FX.SRough': 10,
                 'Aurora.FX.RDraft': 1, 'Aurora.FX.QFeel': 0, 'Aurora.FX.RBlink': 15, 'Aurora.FX.FClone': 1, 'Aurora.FX.QAdd': 1, 'Aurora.FX.QShape': 0,
                 'Aurora.FX.QSkin': 1, 'Aurora.FX.QTilt': 40, 'Aurora.FX.FBird': 0, 'Aurora.FX.QFlat': 1, 'Aurora.FX.EWallSeconds': 8,
                 'Aurora.FX.ACast': 0, 'Aurora.FX.APattern': 0})
# 10-25 게임 기본값(A 고리 + 금 · S 가운데 눈꽃 없음 · F 얇은 매 한 마리 · R 잔상 동작 지금)
DEFAULTS.update({'Aurora.FX.ACast': 2, 'Aurora.FX.APattern': 2, 'Aurora.FX.SInner': 0, 'Aurora.FX.FBird': 3, 'Aurora.FX.RSwing': 6,
                 'Aurora.FX.DRain': 1, 'Aurora.FX.DLook': 0, 'Aurora.FX.SRough': 0})
# 10-25 59차 뒤 게임 기본값(D 다 같이 부서짐 · F 날씬한 매)
DEFAULTS.update({'Aurora.FX.DLook': 4, 'Aurora.FX.FBird': 8})
state = {'phase': 'load', 'wall': time.monotonic(), 'step': 0, 'until': 0.0, 'log': []}


def command(world, text):
    unreal.SystemLibrary.execute_console_command(world, text)


def key(world, name):
    command(world, f'CountessInputQA.Key {name} Press')
    command(world, f'CountessInputQA.Key {name} Release')


def target_point(world, pawn):
    dummies = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.KwangTrainingDummy)
    here = pawn.get_actor_location()
    nearest = min(dummies, key=lambda d: (d.get_actor_location() - here).length())
    location = nearest.get_actor_location()
    return unreal.Vector(location.x, location.y, location.z - 90)


def import_swap_drafts():
    # 장판 그림 가져오기(aurora_frost_materials_build.import_drawn과 같은 설정 — 마스크 압축 · sRGB 끔 · 통째로 올림)
    tasks = []
    for source in SWAP_DRAFTS:
        task = unreal.AssetImportTask()
        task.filename = source
        task.destination_path = SWAP_FOLDER
        task.destination_name = Path(source).stem
        task.automated = True
        task.replace_existing = True
        task.save = True
        tasks.append(task)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    for source in SWAP_DRAFTS:
        texture = unreal.load_asset(f'{SWAP_FOLDER}/{Path(source).stem}')
        if texture is None:
            raise RuntimeError('draft import failed: ' + source)
        texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS)
        texture.set_editor_property('srgb', False)
        texture.set_editor_property('never_stream', True)
        unreal.EditorAssetLibrary.save_loaded_asset(texture, False)


def swap_circle(path, scale=None):
    # 깔린 S 장판(엔진이 바닥 데칼을 월드 설정 액터 밑에 만든다)의 그림만 바꾼다
    scale = SWAP_SCALE if scale is None else scale

    def run(world, pawn):
        texture = unreal.load_asset(path)
        swapped = 0
        for owner in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.WorldSettings):
            for decal in owner.get_components_by_class(unreal.DecalComponent):
                material = decal.get_decal_material()
                if isinstance(material, unreal.MaterialInstanceDynamic) and material.get_editor_property('parent') \
                        and material.get_editor_property('parent').get_name() == 'M_Aurora_SnowFloor':
                    material.set_texture_parameter_value('FlakeTexture', texture)
                    for name, value in SWAP_OPACITY.items():
                        material.set_scalar_parameter_value(name, value * scale)
                    swapped += 1
        state['log'].append({'swap': path, 'loaded': texture is not None, 'decals': swapped, 'scale': scale})
    return run


def set_floor(params):
    # 깔린 S 장판 재질 사본 값만 바꾼다(swap_circle과 같은 데칼 찾기). 'flash'는 S_FLASH 차례로 따로 건다.
    def run(world, pawn):
        changed = 0
        for owner in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.WorldSettings):
            for decal in owner.get_components_by_class(unreal.DecalComponent):
                material = decal.get_decal_material()
                if isinstance(material, unreal.MaterialInstanceDynamic) and material.get_editor_property('parent') \
                        and material.get_editor_property('parent').get_name() == 'M_Aurora_SnowFloor':
                    for name, value in params.items():
                        if isinstance(value, tuple):
                            material.set_vector_parameter_value(name, unreal.LinearColor(value[0], value[1], value[2], 1.0))
                        elif not isinstance(value, str):
                            material.set_scalar_parameter_value(name, float(value))
                    changed += 1
        state['log'].append({'floor': {k: v for k, v in params.items() if not isinstance(v, str)}, 'decals': changed})
    return run


def perf_window(label):
    # 장면 시간 재기 구간을 연다(label) · 닫는다(None) — tick()이 열린 구간에 장면마다 실제 걸린 시간을 쌓는다
    def run(world, pawn):
        state['perf'] = label
    return run


def count_crystals(tag):
    def run(world, pawn):
        crystals = effects = 0
        for owner in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.WorldSettings):
            for component in owner.get_components_by_class(unreal.ParticleSystemComponent):
                effects += 1
                template = component.get_editor_property('template')
                if template and template.get_name() == 'P_Aurora_Freeze_Segment':
                    crystals += 1
        state.setdefault('crystals', {})[tag] = {'crystals': crystals, 'effects': effects}
    return run


def perf_summary():
    summary = {}
    for label, deltas in state.get('frames', {}).items():
        ms = sorted(d * 1000.0 for d in deltas)
        summary[label] = {'frames': len(ms), 'mean': round(sum(ms) / len(ms), 2), 'p50': round(ms[len(ms) // 2], 2),
                          'p95': round(ms[min(len(ms) - 1, int(len(ms) * 0.95))], 2), 'max': round(ms[-1], 2)} if ms else {'frames': 0}
    return summary


def build_steps():
    def switch(world, pawn):
        # DRAFTS_CHARACTER = 바꿀 캐릭터 숫자 키(기본 Four = 오로라, 10-26 85차 Sparrow F 원본 촬영은 Two)
        key(world, os.environ.get('DRAFTS_CHARACTER', 'Four'))

    def walk_to(distance):
        def run(world, pawn):
            point = target_point(world, pawn)
            here = pawn.get_actor_location()
            back = unreal.Vector(here.x - point.x, here.y - point.y, 0)
            back = back * (1.0 / max(back.length(), 1.0))
            goal = point + back * distance
            command(world, f'CountessComboQA.Mouse Press Right {goal.x} {goal.y} {goal.z}')
            command(world, f'CountessComboQA.Mouse Release Right {goal.x} {goal.y} {goal.z}')
        return run

    walk_near = walk_to(170)

    def reset(world, pawn):
        for dummy in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.KwangTrainingDummy):
            dummy.reset_dummy()

    def cast(key_name, name, value):
        def run(world, pawn):
            if isinstance(name, tuple):
                for each_name, each_value in zip(name, value):
                    command(world, f'{each_name} {each_value}')
            elif name:
                command(world, f'{name} {value}')
            reset(world, pawn)
            point = target_point(world, pawn)
            if key_name in AIM_YAW:
                here = pawn.get_actor_location()
                yaw = math.radians(AIM_YAW[key_name])
                point = unreal.Vector(here.x + 700.0 * math.cos(yaw), here.y + 700.0 * math.sin(yaw), point.z)
            elif (key_name == 'F' and key_name not in WALK_BACK) or (key_name == 'R' and key_name not in AIM_AT_DUMMY):
                # F는 허수아비 반대쪽 빈 바닥으로 던진다 — 가까이서 맞히면 꽂히는 폭발이 손 쪽 이펙트를 덮는다(첫 촬영).
                # R(장판)도 같은 까닭으로 빈 바닥에 깐다(10-19 오후 동작 시안).
                here = pawn.get_actor_location()
                away = unreal.Vector(here.x - point.x, here.y - point.y, 0)
                away = away * (700.0 / max(away.length(), 1.0))
                point = unreal.Vector(here.x + away.x, here.y + away.y, point.z)
            elif key_name == 'SpaceBar':
                # 돌진(10-21부터 Space — 그 전 시안 목록의 'W'는 돌진이었다)은 허수아비를 지나 450 끝까지 돌진하게 허수아비 너머를 겨눈다
                # (허수아비 발밑을 겨누면 170만 간다).
                here = pawn.get_actor_location()
                ahead = unreal.Vector(point.x - here.x, point.y - here.y, 0)
                ahead = ahead * (450.0 / max(ahead.length(), 1.0))
                point = unreal.Vector(here.x + ahead.x, here.y + ahead.y, point.z)
            if key_name in AIM_SIDE:
                here = pawn.get_actor_location()
                toward = unreal.Vector(point.x - here.x, point.y - here.y, 0)
                toward = toward * (1.0 / max(toward.length(), 1.0))
                point = unreal.Vector(point.x - toward.y * AIM_SIDE[key_name], point.y + toward.x * AIM_SIDE[key_name], point.z)
            command(world, f'CountessComboQA.Mouse Move Left {point.x} {point.y} {point.z}')
            key(world, key_name)
            state['cast_time'] = unreal.GameplayStatics.get_time_seconds(world)
            state['log'].append({'cast': key_name, 'value': value, 'time': round(unreal.GameplayStatics.get_time_seconds(world), 3),
                                 'pawn': [round(v, 1) for v in (pawn.get_actor_location().x, pawn.get_actor_location().y)],
                                 'aim': [round(point.x, 1), round(point.y, 1)]})
        return run

    def capture(label):
        # 한 장 찍는 동안에도 게임 시간이 몇 장면 흘러(고정 장면 시간) 찍는 때가 목록의 때보다 점점 늦어진다(10-19 밤 R 회오리 —
        # 「1.9초」 그림이 실제로는 4.5초 뒤 터진 뒤였다) → 시전 뒤 실제 게임 시각을 같이 적는다(shots).
        def run(world, pawn):
            state.setdefault('shots', {})[label] = round(unreal.GameplayStatics.get_time_seconds(world) - state.get('cast_time', 0.0), 3)
            command(world, f'CharacterVisualQA.Capture {label}')
        return run

    steps = [(0.0, switch), (0.8, walk_near), (3.5, lambda world, pawn: None)]
    warm = os.environ.get('DRAFTS_WARM') == '1'
    walked = set()
    for key_name, name, values, frames, tail, *rest in DRAFTS:
        presses = rest[0] if rest else ()
        if key_name in WALK_BACK and key_name not in walked:
            walked.add(key_name)
            steps.append((0.0, walk_to(WALK_BACK[key_name])))
            steps.append((2.5, lambda world, pawn: None))
        for value_index, value in enumerate(values):
            # REWALK = 값마다 다시 걸어 설 키(92차 — W 분신 자세는 도약한 뒤 그 자리에서 또 쓰면 분신이 몸과 겹쳐 안 보였다)
            if key_name in REWALK and value_index > 0:
                steps.append((0.0, walk_to(WALK_BACK.get(key_name, 170.0))))
                steps.append((2.5, lambda world, pawn: None))
            if warm:
                # DRAFTS_WARM=1: 한 번 먼저 쏘고(안 찍음) 다시 쏴서 찍는다 — 첫 사용 때만 생기는 장면(Q 시안 0.30초 초록 사각형)을 가린다
                steps.append((0.6, cast(key_name, name, value)))
                steps.append((1.6, lambda world, pawn: None))
            steps.append((0.6, cast(key_name, name, value)))
            previous = 0.0
            label = '-'.join(str(v) for v in value) if isinstance(value, tuple) else value
            events = [(moment, capture(f'{key_name.lower()}_{label}_{index}')) for index, moment in enumerate(frames)]
            events += [(moment, lambda world, pawn, k=pressed: key(world, k)) for moment, pressed in presses]
            for moment, action in sorted(events, key=lambda e: e[0]):
                steps.append((moment - previous, action))
                previous = moment
            # 다음 시안 전에 남은 이펙트가 사라지게 기다린다
            steps.append((tail, lambda world, pawn: None))
    swaps = [f'{SWAP_FOLDER}/{Path(source).stem}' for source in SWAP_DRAFTS]
    if SWAP_DRAFTS and SWAP_SCALES != [1.0]:
        swaps.insert(0, SWAP_CURRENT)
    for scale in SWAP_SCALES if SWAP_DRAFTS else ():
        for path in swaps:
            # 장판은 9초 남는다 — 배율 셋 × 그림 다섯도 그 안에 끝나게 0.2초씩
            steps.append((0.2, swap_circle(path, scale)))
            suffix = f'_x{round(scale * 100)}' if len(SWAP_SCALES) > 1 else ''
            steps.append((0.2, capture(f's_{path.rsplit("/", 1)[-1]}{suffix}')))
    for label, cvars, params in S_FEEL:
        for name, value in cvars.items():
            steps.append((0.0, lambda world, pawn, n=name, v=value: command(world, f'{n} {v}')))
        steps.append((0.6, cast('S', None, label)))
        # 장판은 0.5초에 깔린다 — 그 직후 값을 넣는다
        events = [(0.52, set_floor(params))]
        if params.get('GlowBoost') == 'flash':
            events += [(round(0.52 + 0.1 * k, 2), set_floor({'GlowBoost': v})) for k, v in enumerate(S_FLASH)]
        events += [(moment, capture(f's_{label}_{index}')) for index, moment in enumerate(S_FEEL_FRAMES)]
        previous = 0.0
        for moment, action in sorted(events, key=lambda e: e[0]):
            steps.append((moment - previous, action))
            previous = moment
        steps.append((0.3, lambda world, pawn: None))
        for name in cvars:
            steps.append((0.0, lambda world, pawn, n=name: command(world, f'{n} 0')))
    for round_index in range(PERF_REPEAT if PERF_VALUES else 0):
        for value in PERF_VALUES:
            tag = f'{value}_{round_index}'
            steps.append((0.0, perf_window(f'idle_{tag}')))
            steps.append((1.0, perf_window(None)))
            steps.append((0.0, cast('V', 'Aurora.FX.VDense', value)))
            events = [(1.4, perf_window(f'alive_{tag}')), (1.6, count_crystals(tag)), (2.3, perf_window(None)),
                      (2.4, perf_window(f'crumble_{tag}')), (2.9, perf_window(None))]
            previous = 0.0
            for moment, action in events:
                steps.append((moment - previous, action))
                previous = moment
            steps.append((2.0, lambda world, pawn: None))
    for name, value in DEFAULTS.items():
        steps.append((0.0, lambda world, pawn, n=name, v=value: command(world, f'{n} {v}')))
    return steps


STEPS = build_steps()


def finish(error=None):
    unreal.unregister_slate_post_tick_callback(handle)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    (qa / 'aurora-fx-drafts.json').write_text(json.dumps({'passed': error is None, 'error': str(error) if error else None,
        'drafts': [[k, n, list(v), list(f), t, *rest] for k, n, v, f, t, *rest in DRAFTS], 'log': state['log'],
        'shots': state.get('shots', {}), 'perf': perf_summary(), 'crystals': state.get('crystals', {})}, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()


def tick(delta):
    try:
        if time.monotonic() - state['wall'] > 700:
            raise TimeoutError('Aurora FX drafts timed out')
        if state['phase'] == 'load':
            # 가져오기가 도는 동안 이 콜백이 다시 불린다(첫 판: 가져오기 안에서 가져오기·맵 불러오기가 겹쳐 돎) → 단계부터 바꾼다
            state['phase'] = 'loading'
            if SWAP_DRAFTS:
                import_swap_drafts()
            unreal.EditorLoadingAndSavingUtils.load_map(MAP)
            state['phase'] = 'navwait'
            return
        if state['phase'] == 'loading':
            return
        if state['phase'] == 'navwait':
            # 불러온 직후 내비메시를 만드는 중이면 PIE 사본에 내비가 없다(걸어가지 못한다). 시작점이 내비에 투영될 때까지 기다린다
            # (aurora_skill_probe.py와 같은 방식 — 첫 판은 빌드 중만 보고 넘어가 캐릭터가 제자리에서 허공에 시전했다).
            editor_world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
            if time.monotonic() - state['wall'] < 2 or unreal.NavigationSystemV1.is_navigation_being_built(editor_world):
                return
            start = unreal.GameplayStatics.get_all_actors_of_class(editor_world, unreal.PlayerStart)[0].get_actor_location()
            projected = unreal.NavigationSystemV1.project_point_to_navigation(editor_world, start - unreal.Vector(0, 0, 90),
                None, None, unreal.Vector(100, 100, 250))
            if projected is None and time.monotonic() - state['wall'] < 90:
                return
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
            state['phase'] = 'run'
            return
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        # 장면 시간(위 DRAFTS_V_PERF): 이 콜백은 장면마다 한 번 — 지난 콜백부터 지금까지가 한 장면에 실제로 걸린 시간
        real = time.perf_counter()
        if state.get('perf') and 'last_real' in state:
            state.setdefault('frames', {}).setdefault(state['perf'], []).append(real - state['last_real'])
        state['last_real'] = real
        pawn = unreal.GameplayStatics.get_player_character(world, 0) if world else None
        # 내비 빌드는 시작 전에만 기다린다 — R 회오리가 허수아비를 끌어당기면 내비가 다시 만들어지는데, 그동안 촬영이 멈춰
        # 장면 사이에 2.5초가 비었다(aurora-41st-qrfinal).
        if not pawn or ('configured' not in state and unreal.NavigationSystemV1.is_navigation_being_built(world)):
            return
        now = unreal.GameplayStatics.get_time_seconds(world)
        if state['step'] == 0 and now < 4:
            return
        if state['step'] == 0 and 'configured' not in state:
            command(world, 'CharacterPipeline.OutputDirectory "' + qa.as_posix() + '"')
            command(world, 'Aurora.Skills.IgnoreCooldowns 1')
            # 촬영 크기는 에디터 창 배치(모든 프로젝트가 같이 쓰는 EditorLayout.ini)를 따라 바뀐다 — 10-20 오후 사용자 에디터가 배치를
            # 저장한 뒤 1521×631 → 700×330으로 줄었다. 그 전 크기로 고정한다.
            command(world, 'CharacterVisualQA.ViewportSize 1521 631')
            # 사용자 에디터와 같이 떠 그래픽 메모리가 모자라면 화면 왼쪽 위에 「Video memory has been exhausted」가 찍혀 시안 그림을 가렸다
            # (10-20 밤 aurora-53rd·55th). 글씨만 끈다(SceneRendering.cpp r.DemotedLocalMemoryWarning) — 메모리 부족 자체는 그대로다.
            command(world, 'r.DemotedLocalMemoryWarning 0')
            state['configured'] = True
        if now < state['until']:
            return
        if state['step'] >= len(STEPS):
            finish()
            return
        wait, action = STEPS[state['step']]
        if state.get('waited') != state['step']:
            state['waited'] = state['step']
            state['until'] = now + wait
            if wait > 0:
                return
        action(world, unreal.GameplayStatics.get_player_character(world, 0))
        state['step'] += 1
    except Exception:
        unreal.log_error(traceback.format_exc())
        finish(traceback.format_exc())


handle = unreal.register_slate_post_tick_callback(tick)
