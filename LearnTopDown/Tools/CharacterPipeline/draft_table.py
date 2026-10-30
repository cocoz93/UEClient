"""시안 비교표: 가로 줄 = 시안(왼쪽에 번호·설명), 세로 줄 = 시간(위에 표시), 칸 사이 구분선."""
import os
import sys
from PIL import Image, ImageDraw, ImageFont

FONT = 'C:/Windows/Fonts/malgunbd.ttf'
BG = (24, 24, 28)
LINE = (235, 235, 235)


def table(title, rows, times, crop, out, cell_w=520, label_w=300):
    """rows = [(번호 글자, 설명, 폴더, 파일 앞머리)], times = [(파일 꼬리, 머리 글자)], crop = (x0,y0,x1,y1) 비율."""
    first = Image.open(f'{rows[0][2]}/screenshots/{rows[0][3]}_{times[0][0]}.png')
    w, h = first.size
    box = (int(w * crop[0]), int(h * crop[1]), int(w * crop[2]), int(h * crop[3]))
    cell_h = int(cell_w * (box[3] - box[1]) / (box[2] - box[0]))
    title_h, head_h, gap = 64, 44, 4
    width = label_w + len(times) * (cell_w + gap) + gap
    height = title_h + head_h + len(rows) * (cell_h + gap) + gap
    sheet = Image.new('RGB', (width, height), BG)
    draw = ImageDraw.Draw(sheet)
    big, mid, small = ImageFont.truetype(FONT, 34), ImageFont.truetype(FONT, 26), ImageFont.truetype(FONT, 20)
    draw.text((16, 12), title, font=big, fill=(255, 255, 255))
    for column, (_, head) in enumerate(times):
        x = label_w + gap + column * (cell_w + gap)
        draw.text((x + 10, title_h + 8), head, font=mid, fill=(255, 220, 90))
    for row, (number, text, folder, prefix) in enumerate(rows):
        y = title_h + head_h + gap + row * (cell_h + gap)
        draw.line([(0, y - gap // 2 - 1), (width, y - gap // 2 - 1)], fill=LINE, width=3)
        draw.text((16, y + 16), number, font=big, fill=(255, 220, 90))
        lines, current = [], ''
        for word in text.split(' '):
            trial = (current + ' ' + word).strip()
            if draw.textlength(trial, font=small) > label_w - 32:
                lines.append(current)
                current = word
            else:
                current = trial
        lines.append(current)
        for index, line in enumerate(lines):
            draw.text((16, y + 64 + index * 28), line, font=small, fill=(230, 230, 230))
        for column, (suffix, _) in enumerate(times):
            x = label_w + gap + column * (cell_w + gap)
            cell = Image.open(f'{folder}/screenshots/{prefix}_{suffix}.png').convert('RGB').crop(box).resize((cell_w, cell_h))
            sheet.paste(cell, (x, y))
    for column in range(len(times) + 1):
        x = label_w + column * (cell_w + gap) + gap // 2 - 1
        draw.line([(x, title_h), (x, height)], fill=LINE, width=3)
    sheet.save(out)
    print(out, sheet.size)


def round17(base):
    w = base + '/gideon-17th-d-20261018-173403'
    table('W 마법진 시안 (가로 줄 하나 = 시안 하나)', [
        ('W 0번', '이전 그대로 (점선 고리 있음)', w, 'w0'),
        ('W 1번', '점선 고리 → 룬·삼각 원판 (빽빽)', w, 'w1'),
        ('W 2번', '1번 + 바깥 룬 띠 한 겹 더', w, 'w2'),
    ], [('030', '0.3초 (깔리자마자)'), ('100', '1.0초 (운석 떨어지는 중)')], (0.25, 0.0, 0.85, 0.6), w + '/W_시안표.png')
    r = base + '/gideon-17th-20261018-171004'
    table('V 마지막 시안 (가로 줄 하나 = 시안 하나)', [
        ('V 0번', '접히자마자 하얀 섬광', r, 'r0'),
        ('V 1번', '접힌 채 잠깐 멈춤 → 섬광 + 충격파', r, 'r1'),
    ], [('430', '4.30초'), ('450', '4.50초'), ('459', '4.59초'), ('470', '4.70초'), ('480', '4.80초'), ('500', '5.00초')],
        (0.45, 0.0, 1.0, 0.6), r + '/V_시안표.png', cell_w=330, label_w=260)
    table('F 광선 시안 (가로 줄 하나 = 시안 하나)', [
        ('F 0번', '이전 그대로 (팔 뻗은 채 멈춤)', r, 'ray0'),
        ('F 1번', '겨누는 자세 + 손끝 빛 + 굵은 광선', r, 'ray1'),
        ('F 2번', '손 앞 포털에서 광선', r, 'ray2'),
        ('F 3번', '보라 탄 연사 (광선 대신)', r, 'ray3'),
    ], [('045', '0.45초'), ('120', '1.2초'), ('200', '2.0초')], (0.2, 0.0, 0.8, 0.95), r + '/F_시안표.png', cell_w=420)


def round18(base):
    f = base + '/gideon-18th-g-20261018-181706'
    table('F 번개 시안 (가로 줄 하나 = 시안 하나)', [
        ('F 1번', '번개만 (녹스 번개처럼 지글지글)', f, 'ray1'),
        ('F 2번', '번개 + 가는 레이저 심', f, 'ray2'),
    ], [('080', '0.8초'), ('120', '1.2초'), ('160', '1.6초'), ('200', '2.0초')], (0.3, 0.0, 0.85, 0.7), f + '/F_번개시안표.png',
        cell_w=400, label_w=280)
    # 같은 고정점·같은 시각(운석 폭발 전 0.18초). 위 = 고르신 그대로(원판 1.4배), 아래 = 바깥 고리에 맞춘 지금(0.25배).
    table('W 1번 진하기 맞춤 (위 = 전, 아래 = 후)', [
        ('전', '원판 1.4배 — 안쪽만 하얗게 튐', base + '/gideon-18th-c-20261018-180743', 'w1.4'),
        ('후', '원판 0.25배 — 바깥 고리와 같은 진하기, 보라', base + '/gideon-18th-f-20261018-181538', 'w1'),
    ], [('018', '0.18초 (깔린 직후)')], (0.55, 0.0, 0.95, 0.55), base + '/gideon-18th-f-20261018-181538/W_전후.png', cell_w=640, label_w=300)



def round19(base):
    b = base + '/gideon-19th-b-20261018-220602'
    table('V 끝 폭발 시안 (가로 줄 하나 = 시안 하나)', [
        ('V 0번', '지금 그대로 (섬광 0.7배)', b, 'r0'),
        ('V 1번', '섬광 1.5배', b, 'r1'),
        ('V 2번', '섬광 1.5배 + 보라 돔·번개', b, 'r2'),
        ('V 3번', '섬광 1.5배 + 푸른 충격 고리', b, 'r3'),
    ], [('430', '4.30초'), ('445', '4.45초'), ('459', '4.59초'), ('480', '4.80초 (터짐)'), ('500', '5.00초')],
        (0.45, 0.0, 1.0, 0.75), b + '/V_폭발시안표.png', cell_w=330, label_w=260)
    rows = [('F 1번', '지금 — 양팔을 옆으로 벌림', 'RMB_Targeting_Pose'),
            ('F 2번', '몸을 낮추고 오른손을 아래로', 'Burden_aim_pose'),
            ('F 3번', '오른손을 앞으로 낮게', 'Burden_aim_pose2'),
            ('F 4번', '오른손을 대상 쪽으로 뻗고 원반을 듦 (추천)', 'PortalBlast_Loop'),
            ('F 5번', '두 손을 모아 앞으로 (추천)', 'Torn_Space_TargetingPose'),
            ('F 6번', '원반을 높이 들고 오른손을 앞으로', 'Burden_Loop'),
            ('F 7번', '평타 찌르기를 되풀이', 'Primary_Attack_A_Medium')]
    table('F 동작 시안 (가로 줄 하나 = 시안 하나, 캐릭터 확대)', [(n, d, b, 'ray' + a) for n, d, a in rows],
        [('045', '0.45초 (번개 시작)'), ('120', '1.2초 (붙잡는 중)')], (0.40, 0.22, 0.66, 0.75), b + '/F_동작시안표.png',
        cell_w=420, label_w=300)



def round19_check(base):
    # 고를 것 없이 확인만 하는 표(Q 바닥 마법진 · D 유성 · R 큰 원 = 벽).
    e = base + '/gideon-19th-e-20261018-221321'
    table('Q 떨어지는 자리 마법진 (확인용)', [
        ('Q 위쪽', '허수아비 조준', e, 'q'),
        ('Q 아래쪽', '시전자 뒤쪽 조준', e, 'q2'),
    ], [('040', '0.4초'), ('060', '0.6초'), ('080', '0.8초'), ('095', '0.95초'), ('105', '1.05초 (닿음)'), ('120', '1.2초')],
        (0.0, 0.0, 1.0, 1.0), e + '/Q_확인표.png', cell_w=330, label_w=200)
    table('D 유성 (확인용, 위 줄 → 아래 줄 순서)', [
        ('D ①', '작은 유성 6개', e, 'sky'),
    ], [('065', '0.65초'), ('075', '0.75초'), ('085', '0.85초'), ('095', '0.95초'), ('105', '1.05초')],
        (0.3, 0.0, 1.0, 0.85), e + '/D_확인표_1.png', cell_w=330, label_w=200)
    table('D 유성 (확인용, 이어서)', [
        ('D ②', '마지막 큰 유성(기절)', e, 'sky'),
    ], [('120', '1.2초'), ('135', '1.35초'), ('150', '1.5초'), ('170', '1.7초'), ('200', '2.0초')],
        (0.3, 0.0, 1.0, 0.85), e + '/D_확인표_2.png', cell_w=330, label_w=200)
    a = base + '/gideon-19th-a-20261018-215241'
    table('R 마법진 큰 원 = 감옥 벽 (확인용)', [
        ('R', '마법진 반지름 475 → 370', a, 'cage'),
    ], [('090', '0.9초'), ('120', '1.2초'), ('150', '1.5초 (벽 솟음)'), ('250', '2.5초')],
        (0.35, 0.0, 1.0, 0.75), a + '/R_확인표.png', cell_w=360, label_w=220)



def round19_final(base):
    # 확정분 확인(V 차례로 터짐 · F 5번 동작 + 번개 · D 밝은 유성).
    f = base + '/gideon-19th-f-20261018-224834'
    table('V 끝 — 섬광 → 보라 돔·번개 → 푸른 고리 (확인용)', [
        ('V', '차례로 터짐 (0.25초 간격)', f, 'r'),
    ], [('459', '4.59초 (접힘)'), ('475', '4.75초 (섬광)'), ('484', '4.84초'), ('500', '5.00초'), ('515', '5.15초'), ('540', '5.40초')],
        (0.45, 0.0, 1.0, 0.75), f + '/V_확인표.png', cell_w=320, label_w=200)
    table('F — 두 손 모아 앞으로 + 번개 (확인용)', [
        ('F', '5번 동작 · 번개 세 가닥', f, 'ray'),
    ], [('045', '0.45초'), ('080', '0.8초'), ('120', '1.2초'), ('160', '1.6초'), ('200', '2.0초')],
        (0.38, 0.0, 0.82, 0.75), f + '/F_확인표.png', cell_w=340, label_w=200)
    table('D 밝은 유성 (확인용, 위 줄 → 아래 줄)', [
        ('D ①', '작은 유성', f, 'sky'),
    ], [('065', '0.65초'), ('075', '0.75초'), ('085', '0.85초'), ('095', '0.95초'), ('105', '1.05초')],
        (0.3, 0.0, 1.0, 0.85), f + '/D_1.png', cell_w=330, label_w=200)
    table('D 밝은 유성 (이어서)', [
        ('D ②', '마지막 큰 유성(기절)', f, 'sky'),
    ], [('120', '1.2초'), ('135', '1.35초'), ('150', '1.5초'), ('170', '1.7초'), ('200', '2.0초')],
        (0.3, 0.0, 1.0, 0.85), f + '/D_2.png', cell_w=330, label_w=200)
    from PIL import Image
    top, bottom = Image.open(f + '/D_1.png'), Image.open(f + '/D_2.png')
    sheet = Image.new('RGB', (top.width, top.height + bottom.height), BG)
    sheet.paste(top, (0, 0))
    sheet.paste(bottom, (0, top.height))
    sheet.save(f + '/D_확인표.png')
    os.remove(f + '/D_1.png')
    os.remove(f + '/D_2.png')



def round19_ward(base):
    # R 고리 방패 시안 · F 동작 이어 붙이기(준비 → 붙잡기 → 마무리) 확인.
    i = base + '/gideon-19th-i-20261018-233255'
    table('R 고리 방패 (시안, 허수아비 앞 250에서)', [
        ('R', '방패 포털 → 닫으며 밀쳐냄', i, 'ward'),
    ], [('030', '0.3초'), ('080', '0.8초 (방패)'), ('150', '1.5초'), ('175', '1.75초 (닫힘)'), ('195', '1.95초'), ('250', '2.5초')],
        (0.15, 0.0, 0.9, 0.85), i + '/R_시안표.png', cell_w=320, label_w=220)
    table('F 다듬기 (손 모으기 → 붙잡기 → 내리기)', [
        ('F', '두 손 사이에서 첫 대상 몸으로', i, 'ray'),
    ], [('015', '0.15초'), ('045', '0.45초'), ('140', '1.4초'), ('240', '2.4초'), ('254', '2.55초'), ('275', '2.75초')],
        (0.15, 0.0, 0.9, 0.85), i + '/F_확인표.png', cell_w=320, label_w=220)



def round20(base):
    # F 녹스 번개 시안 넷(녹스 원본 클라 그리기를 옮김).
    c = base + '/gideon-20th-c-20261019-002333'
    table('F 녹스 번개 시안 (가로 줄 하나 = 시안 하나)', [
        ('F 1번', '파랑 번개 (라이트닝) — 곁가지 둘 + 본줄기', c, 'ray1'),
        ('F 2번', '노랑 에너지 볼트 — 굵기가 출렁이는 한 줄', c, 'ray2'),
        ('F 3번', '초록 번개 (망각의 지팡이) — 1번과 같은 꼴', c, 'ray3'),
        ('F 4번', '데스레이 — 보라 불티 일직선', c, 'ray4'),
    ], [('060', '0.6초'), ('100', '1.0초'), ('140', '1.4초'), ('190', '1.9초')], (0.36, 0.0, 0.86, 0.62), c + '/F_녹스시안표.png',
        cell_w=400, label_w=280)



def round21(base):
    # F 파라곤 재조립 시안(녹스 꺾임 경로 + 파라곤 재료).
    c = base + '/gideon-21st-c-20261019-011506'
    table('F 파라곤 재조립 시안 (가로 줄 하나 = 시안 하나)', [
        ('F 5번', '꺾인 조각마다 콰앙 번개 광선 (세 가닥)', c, 'ray5'),
        ('F 6번', '5번 + 보라 방전 무늬', c, 'ray6'),
        ('F 7번', '콰앙 번개 재질 띠 (밝은 줄 + 바닥 푸른빛)', c, 'ray7'),
        ('F 8번', '7번 본줄기 + 5번 광선 곁가지 둘', c, 'ray8'),
    ], [('060', '0.6초'), ('100', '1.0초'), ('140', '1.4초'), ('190', '1.9초')], (0.36, 0.0, 0.86, 0.62), c + '/F_파라곤시안표.png',
        cell_w=400, label_w=280)


if __name__ == '__main__':
    {'17': round17, '18': round18, '19': round19, '19c': round19_check, '19f': round19_final, '19w': round19_ward, '20': round20, '21': round21}[sys.argv[2] if len(sys.argv) > 2 else '18'](sys.argv[1])
