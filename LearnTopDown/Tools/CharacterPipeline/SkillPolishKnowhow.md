# 캐릭터·스킬 연출 노하우 — 2026-10-21 기록 점검

1번 암살자(Countess)·2번 궁수(Sparrow)의 작업과 기존 3번(Gideon)·4번(Aurora) 기록을 취합했다. 이번 점검은 문서·현재 소스·프로필·남아 있는 QA 결과의 대조이며, 새 빌드나 플레이 검증을 실행한 것은 아니다. 게임 코드·에셋·설정은 변경하지 않았다.

**설치된 구현, 비교 시안, 기능 검사 통과, 실제 화면 확인, 사용자 채택을 구분한다.** 아래 수치는 이 프로젝트의 출발점이며 다른 캐릭터에 그대로 적용하는 정답이 아니다. 작업 범위와 검증 비용은 [프로젝트 AGENTS.md](../../AGENTS.md), 병렬 작업은 [ParallelCharacterWork.md](ParallelCharacterWork.md)를 따른다. 사용자의 현재 요청이 과거 작업 습관보다 우선한다.

재개할 때는 §8 현재 설정 → §10 E 시안 상태 → §12 미확인점부터 읽는다. 외형 조정은 §7, 애니메이션/망토는 §9, 도구 문제는 §3~4만 추가로 찾아본다. 매 작업마다 모든 과거 기록을 다시 읽지 않는다.

## 0. 이번 점검에서 바로잡은 내용

| 기존 기록의 문제 | 이 문서에서 적용할 기준 |
|---|---|
| 사진 없이 로그만 보면 검증 완료로 읽힐 수 있었음 | 로그는 판정·타이밍·정리 증거다. 외형을 보지 않았으면 `화면 미확인`으로 보고한다. 사용자가 실제 화면 확인을 요청하면 해당 구간을 확인한다. |
| `Condition failed 15 / ensure 2`를 정상 기준처럼 고정 | 실행별로 수가 달랐던 기록도 있다. 메시지·발생 위치·호출 경로·영향으로 기존/신규를 구별하며, 개수 일치만으로 정상 처리하지 않는다. |
| 시안 선택 즉시 사진 삭제, 실패한 재질은 에셋째 삭제하도록 일반화 | 해당 작업에서 승인된 정리 범위만 적용한다. 미확정 시안·열어 둔 미리보기·공유 에셋을 자동 삭제하지 않는다. |
| 모든 스킬이 `UpperBody` 슬롯이라는 설명 | 캐릭터와 동작별 슬롯이 다르다. 1번은 `CountessFullBody`, 2번은 상·전신 혼합, 4번은 `AuroraFullBody` 등 실제 그래프를 확인한다. |
| LearnTopDown이 git 밖이라는 설명 | 이번 `git rev-parse`는 상위 `MMO_Zone` 저장소를 반환했고, 이 문서가 있는 도구 폴더는 미추적 상태였다. 저장소 밖과 미추적은 다르다. 커밋·push는 이번 요청에 포함되지 않는다. |
| 과거 README의 R 가속안, 궁수 색상표의 패시브 E, 망토 문서의 초기 바람식 | 현재 소스와 다르다. §8의 현재 기준과 §12의 오래된 문서 목록을 먼저 본다. |

기존 3·4번 사례는 해당 기록의 관측으로 남겼다. 이번에 원인을 재현하지 않은 항목을 UE 전체의 확정 법칙으로 확대하지 않는다.

## 1. 사용자와 주고받는 방식

- **캐릭터 호칭** — 1 암살자/Countess · 2 궁수/Sparrow · 3 Gideon · 4 Aurora. 사용자가 쓴 호칭이나 「1번 Q」로 보고하고, 코드 이름은 그대로 둔다.
- **보고는 한국어 · 결론 먼저 · 짧게** — 바꾼 것·이유·확인 범위만 말한다. 화면을 보지 않았다면 「구현/빌드 완료, 화면 확인 대기」로 구분한다.
- **승인된 방향은 실행까지 이어감** — 「그렇게 해줘」·「무인루프로 진행」을 다시 확인받지 않는다. 「가능한지 대답만」·「후보만」·「러프 시안」은 그 범위로 제한한다. 복잡한 새 로직의 계획 승인은 상위 AGENTS.md를 따르되, 이미 승인된 계획을 재승인받지 않는다.
  - 「~하는 게 어때?」도 문맥상 변경 요청이면 진행한다. 설명·의견 요청인지 불분명한 경우에는 후보를 제시하고, 명백한 의도를 기계적으로 되묻지 않는다.
  - 한 메시지의 여러 항목은 각각 요청·보류·시안·실제 반영을 구분한다.
- **매 수정마다 대량 촬영하지 않음** — 3·4번에서 사용자가 직접 게임 확인을 택한 작업 방식은 유지한다. 1·2번의 실제 화면 검증 요청이나 시각 문제 원인 진단까지 생략하는 규칙은 아니다. 색·크기만 바꿨으면 짧은 대표 구간으로 충분하다.
- **지목한 부분만** — 「투명하게」는 지목한 부위에만, 「보강」이라도 새 이펙트를 임의로 넣지 않음(4번에서 둘 다 반려)
- **모양 요청이 반복해서 빗나가면 해석을 먼저 맞춤** — 길이·두께·곡률·방향·질감 중 무엇을 바꿀지 기존 화면에 표시한다. 필요하면 참고 그림/장면을 요청하고, 같은 추측으로 대량 변주를 반복하지 않는다.
- **위치 지시(뒤쪽·옆쪽)가 애매하면 번호 그림 먼저** — 후보 자리에 번호를 찍은 그림을 보여 짚게 함
- **효과를 갈아 끼우면 「느낌」이 바뀜** — 사용자가 이미 본 느낌을 지키는 후보로 고르고, 바뀌면 보고에 한 줄(3번 D 「원래 밝은 작은 유성이었는데 왜 바뀌었지」)
- 커밋·push를 임의로 수행하지 않는다. 저장소와 추적 상태는 실제 경로에서 확인한다.

## 2. 시안 고르기

- **시안은 운영 구현과 구분** — 반복 비교가 필요하면 콘솔 번호를 쓰고, 기본값은 마지막으로 적용하기로 한 상태를 보존한다. 콘솔을 시전 때 읽는지 스폰 때 읽는지도 적는다. 1번 E A·D처럼 기존 PIE 시각 액터만 바꾸는 미리보기라면 새 네이티브 분기를 만들 필요가 없다.
- **비교는 같은 순간끼리 나란히** — 영상 + 대표 표 또는 기존의 시간 동기화 HTML을 재사용한다. 둘 다 새로 만들 필요는 없다.
  - 표: 가로 줄 하나 = 시안 하나, 왼쪽에 큰 번호 + 한 줄 설명, 위에 시각 — `draft_table.py`의 `table()`. 칸 구석에 작은 영문 라벨만 붙인 격자는 「어떻게 봐야 할지 너무 불친절」로 반려됨(10-18)
  - 영상: `draft_video.py <spec.json>` — 시안별 `<접두어>_<숫자>.png`를 같은 순번끼리 붙여 mp4 + 표 한 장(spec 항목은 파일 머리 주석)
- **골격(동작·시점)을 먼저 맞추고 조형만 바꿈** — 골격이 안 맞으면 조형 변주는 전부 헛수고
- **정리는 승인된 범위 안에서** — 3번은 사용자 요청에 따라 색인 + 시안마다 알아볼 그림 + 재생성 코드를 남긴 사례다. 이를 다른 캐릭터의 미확정 미리보기 삭제 권한으로 해석하지 않는다. 삭제 전 실제 절대 경로와 열린 페이지 의존성을 확인한다.
- 안 고른 시안 **코드** 삭제는 사용자에게 물음(3번 F 1~4는 「다시 바꿀 수도 있으니 지우지 말고 둬」)

## 3. 빌드·확인

- **빌드** — `"C:/Program Files/Epic Games/UE_5.8/Engine/Build/BatchFiles/Build.bat" LearnTopDownEditor Win64 Development -Project=<LearnTopDown.uproject 절대경로> -WaitMutex`
- **DLL 잠금 확인** — 실행 중인 에디터가 빌드 대상 DLL을 사용하는 경우 LNK1104가 날 수 있다. 강제 종료하지 않는다. 잠금 대상·실제 로드 모듈을 확인한 뒤 저장/종료가 필요한 경우에만 요청한다. 무기한 `Wait-Process`로 진행 보고를 막지 않는다.
- **별도 실행 경로** — `editor_task.py --debug-game`는 `UnrealEditor-Win64-DebugGame.exe`를 사용한다. 해당 DebugGame 타깃을 먼저 빌드하고 실제 로드 구성을 확인한다. 다른 DLL이어도 동일 에셋의 동시 저장과 GPU 경합까지 안전해지는 것은 아니다. 예전 모듈 접미사를 그대로 재사용하지 않는다.
- **빌드와 로드 구분** — 컴파일 줄의 유무만으로 최신/구버전을 단정하지 않는다. 증분 빌드·다른 작업자의 선행 빌드일 수 있다. `Binaries/Win64/UnrealEditor.modules`, 빌드 결과와 실행 로그/변경 동작을 함께 확인한다. 모듈 manifest만으로 이미 열린 에디터가 새 DLL을 쓴다고 판단하지 않는다.
- **로그의 용도** — 기존 진단 명령/로그로 발사 수·피해·타격 시각·취소·정리를 확인한다. 필요할 때만 최소 계측을 추가하며, 로그 정상은 외형 승인과 별개다.
- **오류 기준선** — 알려진 메시지는 원인·발생 단계·영향·이번 변경과의 관계를 기록한다. 같은 개수라도 다른 오류가 섞일 수 있고, 기존 ensure가 있다는 이유로 새 실패를 묻지 않는다.
- **시간대별 사진(시안용)** — 숨은 에디터 PIE에 키(`CountessInputQA.Key <키> Press|Release`)·마우스(`CountessComboQA.Mouse Move Left x y z`)를 콘솔로 넣고 정한 게임 시각에 찍음. 3번 정본 = `gideon_wra_sequence.py`
  - 환경 변수: `WRA_ONLY`(묶음 고르기) · `WRA_REPEAT=<묶음>:<콘솔값>:<번호들>`(같은 동작을 시안 번호별로 반복, 콘솔값 여럿은 `+`) · `WRA_<묶음>_TIMES`(찍을 시각) · `WRA_NO_SHOTS=1`(로그만)

## 4. 함정 — 실제로 당한 것

- **맵 불러온 직후 PIE** — 내비 준비 전에 월드를 복사하면 이동 검사가 무효가 될 수 있다. 시작/목표 투영과 완전 경로를 확인한다. `navigation_ready.py`의 좌표는 기존 필드용 `(0,0,212) → (0,650,125)`이므로 다른 맵에 그대로 쓰지 않는다.
- **PIE 게임 시간 ≠ 로그 시각** — 고정 스텝에서는 벽시계와 게임 시간이 다르며 캡처 지연도 생긴다. 파일 이름의 예정 시각보다 기록된 실제 게임 시각을 기준으로 비교한다. 샘플 PNG를 이어 만든 영상은 연속 녹화/성능 측정과 구분한다.
- **프레임 파일은 숫자로 정렬** — `<이름>_<숫자>.png`를 문자로 정렬하면 `_100`이 `_20` 앞에 옴
- **숨은 에디터 화면 크기가 바뀜** — 편집기 배치에 따라 원본 캡처가 700×330 등으로 달라진 이력이 있다. 필요하면 PIE의 `CharacterVisualQA.ViewportSize <폭> <높이>`로 비교 조건을 고정하고 요청/실제 크기와 PNG 크기를 확인한다(각 축 최대 2048). 공용 `EditorLayout.ini`를 수정하지 않는다. 확대 보기는 별도 표시하고 원본 쿼터뷰도 함께 제공한다.
- **런타임 메시 부품** — `NewObject<UStaticMeshComponent>` 뒤 충돌·내비 영향을 **먼저** 끄고 `SetStaticMesh`. 거꾸로면 내비 목록에 남아 지나간 길에 구멍, 캐릭터 이동이 멈춤. 진단 = `log LogNavigationDirtyArea VeryVerbose`
- **대상과 내비 장애물 구분** — `BlockAllDynamic` 허수아비 주변의 내비 구멍 때문에 접근이 거절된 사례가 있다. 공격 대상 자체와 경로 장애물을 구분하되, 월드 충돌·착지·높이·시야 검사를 통째로 없애지 않는다.
- **방출 종료와 소멸 구분** — `Deactivate` 뒤에도 기존 입자가 남을 수 있다. 자연 종료는 잔여 수명/페이드, 취소는 게임 판정 즉시 중단 후 필요한 시각 꼬리만 유지, 소유자 종료는 명시 정리로 구분한다. 원인 FX가 불명확하면 `fx_gallery.py` 같은 기존 도구로 개별 확인한다.
- **첫 사용 흐림** — 4번에서 스트리밍 저해상도 사례가 있었다. 해상도·스트리밍·AA·재질 컴파일을 먼저 구별한다. 작은 전용 핵심 텍스처의 `never_stream`은 후보이며, 모든 텍스처에 적용하면 메모리 비용이 늘어난다.
- **첫 사용 데칼 이상색** — 4번에서 작은 데칼로 사전 렌더한 대응 이력이 있다. 재질 컴파일/로딩을 먼저 확인하고, 프리워밍이 실제 실패를 숨기거나 일괄 필수가 되지 않게 한다.
- **공중 FX 잘림** — 약 650cm는 특정 카메라/뷰포트의 관측이다. 위치·FOV·종횡비가 바뀌면 달라지므로 `ProjectWorldLocationToScreen`과 실제 화면으로 결정한다.
- **저작할 에셋의 수명** — 4번의 생성자 하드 참조와 재질 재생성 경로에서 `!IsRooted`가 관측됐다. 프로젝트 소유 저작 에셋은 필요 시 `TSoftObjectPtr`와 지연 로드를 검토한다. 모든 `FObjectFinder`가 잘못된 것은 아니며, soft 참조도 이미 로드된 객체의 삭제/저장을 무조건 안전하게 만들지 않는다.
- **재질 그래프 재작성** — 4번에서 노드 누적·빈 입력으로 컴파일 실패한 이력이 있다. 연결 반환값·실제 노드/입력·최종 컴파일 결과를 확인한다. 전용 생성 에셋의 재생성이 필요하면 참조와 보존 범위를 먼저 확인하고, 공유/원본 재질을 자동 삭제하지 않는다. `Failed to compile Material`은 에셋 경로·시각으로 조사하며 중간 그래프 경고와 최종 실패를 구별한다.
- **상체/전신 슬롯** — 실제 AnimGraph의 합성 순서와 뼈 마스크를 본다. 4번의 숨은 메시 + leader pose는 종료 때 튀어 전신 슬롯으로 교체한 사례다. 이를 모든 캐릭터의 슬롯 교체 지시로 해석하지 않는다.
- **동작이 「어색」하면 뼈 위치를 시각별로 뽑음** — `gideon_hand_timing_dump.py`·`aurora_hand_timing_dump.py`. 3번 A의 「점프」는 실은 3타 동작의 10cm 웅크림 → 16cm 솟음이었음
- **1번 관측(원인·플레이 영향 미확인)** — 10-21 `Saved/Logs/LearnTopDown.log`에도 `LevelStart_Montage`의 Shinbi `Mudang/Animations/LevelStart` 및 `P_Mudang_LevelStart_Heart` 의존성 누락이 있다. Q/E의 결함이나 무해한 오류로 단정하지 않는다. 원본 팩을 임의 수정하지 말고 별도 자산 참조 조사 대상으로 남긴다.

## 5. 같이 쓰는 파일 — 3·4번 작업이 고친 자리

- [KwangPlayerController.cpp](../../Source/LearnTopDown/KwangPlayerController.cpp)의 `SetupInputComponent` — V·Space와 숫자 1/2/3/4 선택. `SwitchCharacter`와 이전 Pawn 정리까지 공통 영향 범위다.
- [CharacterSkillHUD.cpp](../../Source/LearnTopDown/CharacterSkillHUD.cpp)의 `PlacesLetterKeysOnLeftHud()` 사용부와 [CharacterSkillComponent.h](../../Source/LearnTopDown/CharacterSkillComponent.h) — 기본 false, 직업별 HUD 배치 확장. 고정 줄 번호보다 심볼을 찾는다.
- 파일 수정 시각만으로 다른 담당의 무변경을 보증하지 않는다. 수정 담당·범위와 실제 diff를 확인한다. `CountessInputQA`·`CountessComboQA`는 다른 직업도 빌려 쓰는 공통 진단 명령이다.
- **동시 작업** — 캐릭터별 소스/전용 에셋은 담당을 나누고 공통 소스·맵·프로필·빌드는 통합 담당이 조율한다. `render_lock.py`는 이를 사용하는 오프스크린 에디터끼리만 직렬화한다. UBT·사용자 에디터·외부 도구까지 잠그지 않는다.

## 6. 기록 위치

- 3번 차수별 기록 — [gideon-skills-progress.md](../../../../../MyDocs/claude-plans/gideon-skills-progress.md)
- 4번 — [aurora-skills-progress.md](../../../../../MyDocs/claude-plans/aurora-skills-progress.md)
- 1·2번 개별 작업 기록은 §12에 연결했다. 외부 기록은 프로젝트를 옮기면 경로를 다시 확인한다.

## 7. 1·2번에서 얻은 연출 조정 기준

| 사용자 표현 | 먼저 분리해서 조정할 것 | 피할 것 |
|---|---|---|
| 길다 / 두껍다 | 메시의 길이축·폭, 재질 알파 폭, 빛 번짐을 따로 조정 | 길이를 줄인 뒤 종횡비나 전체 스케일로 두께까지 달라지게 만들기 |
| 단색이고 쨍하다 | 넓은 흰 코어를 줄이고 기존 텍스처 결·검붉은 중간톤·작은 순간 강조를 유지 | 색상값만 붉게 바꾸고 넓은 단색 면을 그대로 두기 |
| 안개가 너무 짙다 | 방출량/버스트와 한 입자의 Opacity를 따로 확인 | 효과 반경을 줄여 밀도 요청에 답하기 |
| 외곽이 비어 보인다 | 외곽과 내부를 구분해 띠의 연결·짧은 잔상·빈 공간을 보완 | 중심 전체에 입자를 겹쳐 더 탁하게 만들기 |
| 더 빠르고 몰아친다 | 준비·이동·타격 간격·클립 속도·회복을 따로 정함 | 몽타주 전체 배속만 올려 팔 움직임과 피격 시점을 무너뜨리기 |
| 활 앞에 고정 | 활/캐릭터의 수평 yaw를 기준으로 배치 | 발사체의 위아래 조준 pitch에 원형 FX까지 기울이기 |
| 자연스럽게 사라진다 | 판정 종료와 시각 꼬리를 분리하고 위치를 유지한 채 알파/침식 처리 | 배우를 즉시 삭제하거나 잔상 전체가 둥둥 떠오르게 하기 |

- **쿼터뷰에서 보이는 차이를 먼저 설계한다.** 「크고 확실하게」는 길이·두께·화면 점유율·밝기 정점·노출 시간 중 어떤 차이를 만들지 정하는 요청이다. 전부 동시에 키우지 않는다. 근접 확대에서만 보이는 개선을 실제 플레이 개선이라고 보고하지 않는다.
- Q의 큰 반월/넓게 휜 궤적은 사용자가 거부했다. 원본 칼 소켓을 측정했어도 만들어진 곡면이 좋은 연출이라는 뜻은 아니다. 반대로 직선화한 연출을 실제 칼 궤적이라고 설명하지 않는다.
- 「기존 톤」은 색만이 아니라 텍스처 결·투명도·잔상·밝기 대비·소멸 방식까지 포함한다. 원본 팩을 직접 바꾸지 말고 프로젝트 소유 사본이나 transient 인스턴스에서 조절한다.
- 현재 `DefaultEngine.ini`의 `r.AntiAliasingMethod=0`이다. 얇은 선·고주파 노이즈는 실제 해상도에서 점멸/계단이 생기는지 본다. 이를 가리려고 비교 이미지만 리사이즈하거나 프로젝트 AA를 몰래 바꾸지 않는다.
- 방출량·수명·알파·컴포넌트 수를 올리면 겹침/비용도 달라진다. 새 Tick이 없다는 이유로 GPU 비용이 같다고 주장하지 않는다. 성능 수치는 별도 계측 없이는 확정하지 않는다.

## 8. 현재 구현에서 재사용할 설정 기준

**2026-10-21 소스·프로필 대조값을 기본으로, 궁수 행은 10-22 후속 작업까지 갱신했다.** 열린 사용자 에디터의 실제 로드값을 뜻하지 않는다. BP 저장값 → BeginPlay 이행/교체 → 콘솔값 읽기 → 실제 선택 에셋을 순서대로 추적한다. 표의 값만 설치기에 덮어쓰지 않는다.

| 항목 | 현재 기준 / 적용 시점 | 근거와 주의 |
|---|---|---|
| 필드·선택 | 기본 맵 `Lvl_DarkTrainingRoom`, 숫자 1/2/3/4 | `Config/DefaultEngine.ini`, `KwangPlayerController::SetupInputComponent`. 옛 F1/F2·개별 프로필 검사 맵과 구분. |
| 카메라 | 비교 기준 arm 2000, 회전 `(-50,45,0)`, FOV 55, lag 3 | `Profiles/sparrow.json` + 전환 시 카메라 복사. arm만 같다고 parity 판정하지 말고 offset·projection·실제 화면도 확인. |
| 연습 쿨타임 | `Countess.Skills.IgnoreCooldowns=1`, `Sparrow.Skills.IgnoreCooldowns=1` | 각 `IgnoresCooldowns()`에서 읽음. 스킬 정의의 8/6/8/20초는 지워진 것이 아니다. 정상 쿨타임 검사 때만 해당 실행에서 0으로 복원. |
| 암살자 Q | `QPresentation=3`, `QTone=1`, `QLengthScale=0.52`(0.35~1) | `SpawnBlinkDualSweep`: 현재 `M_CountessQOutwardWispy`가 있으면 이를 우선 사용, 없으면 Muted. 길이축만 조절하며 피해 사거리 850cm와 별개. |
| 암살자 W | `WPresentation=3`, `WPreview=0`, `WPlayRate=1.95`(0.5~2) | 현재 `P_CountessW_VeilRing`; 속도는 시전 때 고정. 기준 타격 0.55/회복 0.95초를 배속으로 나눠 약 0.282/0.487초. 피해 40·반경 240cm는 별개. |
| 암살자 E | 수련장 스폰 시 `EFlurry=1`; 본체 3 + 분신 3, 합계 6타·기본 총 피해 45 | `CreateFlurryMontages`, `PlayFlurryStrike`, `HitFlurryTarget`. 근접 210cm, 간격 `0.22/1.5 ≈ 0.1467초`, 복귀 약 1.1667초. 기존 평타 클립을 편집한 구현이지 새 전용 애니메이션 에셋은 아니다. |
| E 분신 종료 | 공격 정리 후 별도 외형이 약 0.45초 침식, 액터 수명 0.5초 | `RetireFlurryShadow`, `countess_e_shadow_material.py`. Q 분신 재질 사본에서 E 전용으로 작성, 분신 이동의 기준 스케일 8cm. Q 원본을 함께 바꾸지 않음. |
| 암살자 R | 원본 `Ability_Ultimate`, 0초부터 1배속, 준비 0.95 + 접근 0.5초, 타격 1.8 / 복귀 2.25초 | 최초 동작으로 롤백한 상태. 과거 0.2+0.2초 접근/1.5배속안을 재적용하지 않음. |
| 궁수 평타 | 스폰 시 `Attack.Natural=1`, `Attack.HeldAim=1`, `Attack.Speed=1.8`(0.5~2) | 10-22 요청으로 이전1.2의1.5배. 후속 요청으로 모션 완료 뒤 대기는 최대0.08/공속, 현재0.044초. transient 몽타주의 진입/종료 블렌드도 공속으로 나눔. `ASparrowCharacter::BeginPlay`, `CreateHeldAttackMontages`. 단클릭 완주와 원본 에셋 보존. 기본값 변경 후엔 다른 캐릭터로 갔다가 재선택해 스폰. |
| 궁수 Q | 자유 바닥 지점, 사거리1400/반경300cm, 4초8회/총40피해, 시각 밀도2.4배 | 10-22 `Ground` 타기팅. `UseSkill`에서 pawn을 제외한 바닥을 읽고 `StartHail`로 전달한다. 범위원 마지막0.4초 페이드/착탄 섬광. 실제 피해와 화살 입자 발생량을 구별. |
| 궁수 W | 준비 0.5초, 발사 0.62초, 복귀 2.25초 | 채택 A1 절개 고리2개. 스케일2.6/1.5에서 각0.55 확대, 보조 밝기0.5, 고리당0.14초·액터0.24초·축 섬광0.10초. `SparrowShotWave::Tick` 연출이며 투사체 두께2/피해35와 별개. |
| 궁수 A | 속도320cm/s, 범위1800cm, 반경70cm, 경로 표적당90피해 | A3 깃털환을 후속 요청으로 축소. `ASparrowGearArrow` 평면2개의 스케일1.6/1.08, 중심 금속1.35, 보조 밝기0.45, 기존540deg/s 회전과 관통 유지. |
| 궁수 E | 준비 0.12초, 6발, 간격 0.16초, 전체 동작 1.2초 | 기존 누적 피해 패시브 유지. 10-22부터 기본 Sparrow 황금/흰색 준비 리본·활 불꽃·화살·명중 FX를 연결한다. `RapidShotCount/Interval`, `FireRapidShot`. |
| 궁수 R | 능동 다발사격21발×3회=63발, 78도, 준비0.12/간격0.22/복귀0.94초 | `FireMultishotWave`와 `ASparrowArrow`의 회차별 공유 피격 집합. 속도2600/거리1800, 대상당20×3=60피해, 패시브 중첩 제외. 최종 잔상은 R만 교차 평면2개, 스케일1.8/.05와 Envelope0.8. 이전10초 평타 버프 기록은 과거 이력. |
| 궁수 S | 8초 황금 변신, 망토/끈/후드 제거, 기존 Serath 날개 | `SparrowAscension`에서 Rogue ID3/7/13의 모든 LOD를 숨기고16개 재질을 황금 MID로 변경. 종료 때 기존 재질/section 가시성을 복구. 디아블로식 교체 날개는 미확인. |
| 궁수 D | 10초 동행 분신2개, 평타·Q/W/E/R/A 각30% 복제 | 실제 발사 이벤트에서 호출. 자동 발사/재귀 분신/패시브 누적 제외. S는 외형/날개만 동기화, R 회차별 중복 피해 집합은 분신마다 별도. 소유자 종료 때 분신/남은 공격 정리. |
| 궁수 망토 | 스폰 시 Presentation 1, 목표 최대풍속 180cm/s(0~200), damping 0.08 / local 0.12 | `ConfigureSparrowRogueCape`, `UpdateCapeFlutter`. Rogue 전용이며 다른 천 모델의 권장값으로 복사하지 않음. |

W의 「발생량 약 77.1% + 내부 Opacity 0.40」은 [CountessWPreview.md](CountessWPreview.md)에 기록된 단계별 저작 이력이다. 현재 코드의 VeilRing 선택은 확인했지만 이번에 바이너리 내부 값을 다시 덤프한 것은 아니다. 원본 대비/직전 버전 대비 배율을 구분하고, 재실행은 현재 복사본에 누적 곱하지 말고 지정한 원본에서 다시 계산한다.

## 9. 애니메이션·망토 문제를 분리하는 방법

- 이동→정지의 어색함은 전환 블렌드뿐 아니라 이동/대기 포즈의 골반·머리·발 중심 차이를 본다. 궁수는 `idle_relaxed` 일부 구간에서 `Travel_Mode_Idle_BowDown` 사본으로 바꾼 이력이 있다. 블렌드만 늘려 큰 변위를 천천히 보이게 하는 것으로 해결했다고 판단하지 않는다.
- 실제 이동과 시선 문제는 Actor yaw·경로 완료·잔여 회전을 먼저 확인한다. `FinishStopHeading`은 정상 도착 후 작은 잔여 회전만 마무리하고, 새 이동/전투/컨트롤러 변경 때 해제한다.
- 연사 중 활을 내리는 문제는 준비→발사→회복→다음 발의 연결 문제다. 하체 이동 포즈 위 상체 슬롯과 held pose를 사용하되 단발·홀드 해제·R 종료의 복귀도 함께 확인한다. 단순 공속 증가는 대체가 아니다.
- 본체와 분신은 같은 동작을 초고속으로 재생하기보다 서로 엇갈리게 타격하게 해 총 밀도를 만든다. `HitFlurryTarget`의 6회 피해와 FX 선/입자 수를 혼동하지 않는다. 대상 소실·사거리/시야 이탈·취소·소유자 종료에는 공격 타이머와 판정을 먼저 정리한다.
- 망토의 폭주·몸 관통·뻣뻣함은 별개다. 몸 포즈/충돌체 → 관성·급회전 → 감쇠 → 바람 순으로 원인을 좁힌다. 천 시뮬레이션을 끈 것과 자연스럽게 만든 것은 다르다.
- 현재 `ConfigureSparrowCapeBodyCollisions`는 기존 몸 PhysicsAsset의 구/캡슐을 `AddClothCollisionSource`로 제공한다. `UpdateCapeFlutter`는 이동 속도를 0.25초 지수 보간하고, 이동 중 좌우 강제 바람 이동을 0으로 줄이며 풍속 진폭도 낮춘다. 초기 망토 문서의 대기용 바람식만 재적용하지 않는다.
- 현재 Rogue Legacy 바람의 환산 `100×25`와 반경 20cm/앞쪽 5cm는 해당 구현 조건이다. 소스 입력값을 천 입자의 실제 이동량이나 모든 엔진 버전의 단위로 해석하지 않는다.

## 10. 암살자 E A·D — 비교 시안으로만 보관

본체·분신 협공과 반대편 배치는 유지하고 FX만 비교한 것이다. **현재 설치된 E는 `M_CountessETargetCut`이며, A·D는 아직 기본 E로 반영하지 않았다.** 직선 참격 구현이 존재한다는 사실과 사용자가 그 외형을 채택했다는 뜻을 구별한다.

| 시안 | 재사용할 설계와 실험값 | 상태 |
|---|---|---|
| A: 짧은 검붉은 절개 | 외곽 형태는 안정적으로 두고 내부에 원본 노이즈 결. 전개 0.032초, 수명 0.25초, 두 번째 절개 지연 0.045초·강도 0.60. 선 길이 기준 172cm/마지막 두 타 198cm, 두 번째 선은 80%. | 실제 PIE 비교를 만든 값. 최종 미적 승인 대기. |
| D: 누적 상처 | 새 상처만 잠깐 강조하고 이전 상처는 어둡게 유지. 첫 타 +0.87초부터 0.48초 동안 제자리에서 침식하고 작은 파편만 이동. | 실제 PIE 비교를 만든 값. 최종 미적 승인 대기. |

- 생성/재현: [countess_e_concepts.py](countess_e_concepts.py), `COUNTESS_E_CONCEPT_REFINED=1`, 전후 비교는 `COUNTESS_E_CONCEPT_COMPARE=1`, 선택 시안은 `COUNTESS_E_CONCEPT_STYLES`. 새 전용 재질 `FXConcepts/M_EConceptsAD_Refined_20261021`을 사용한다.
- [비교 페이지](../../Saved/QA/CharacterPipeline/countess-E-AD-refined-20261021/E-AD-preview.html), [결과](../../Saved/QA/CharacterPipeline/countess-E-AD-refined-20261021/result.json). 현재 남아 있는 결과는 `passed=true`, `installed_skill_changed=false`, `native_build_performed=false`다. 원본 700×330 캡처를 사용했으므로 고해상도 최종 품질 검증과 구분한다.
- A 최종 비교 근거는 `field-a-final/e-concepts.json`, D는 `field/e-concepts.json`이다. A를 한 번 더 보강했으므로 이전 `field`의 A를 최종본으로 고르지 않는다. 확인한 피해 45·6타와 시각 만족도는 별도다.
- 일반화할 것은 「고정된 짧은 형태 + 내부 질감 + 타격별 강약 + 짧은 잔상」의 분리다. 시안의 모든 수치를 다른 스킬의 기본값으로 승격하지 않는다.

## 11. 검증 비용과 다음 세션 인계

1. 실제 소스/에셋과 마지막 승인 상태를 먼저 확인하고, 변경 축을 한 문장으로 정한다. 미확정이면 소수 시안으로 방향부터 고른다.
2. 국소 시각값은 관련 구간만 확인한다. 애니메이션·타이머·입력·판정 변경은 타격/발사·취소·복귀까지, 프레임 의존성이 있을 때만 30/60fps로 넓힌다. 문서 수정에는 게임 빌드가 필요 없다.
3. 기존 도구와 PIE를 재사용한다. 전체 회귀·원본 전체 해시·Game 타깃 빌드는 통합/보존 위험에 맞춰 수행한다. 같은 검사를 새 변경·실패 근거 없이 반복하지 않는다.
4. 다음 담당에게 `현재 적용본 / 사용자 채택 여부 / 보류·폐기안 / 수정 파일·에셋 / 마지막 검사 조건·결과 / 미확인점 / 다음 한 가지`만 넘긴다. 원본 에셋 이름과 가공 사본 이름을 함께 적는다.
5. QA 폴더가 남아 있는지 확인한다. 사라진 결과의 `passed` 기록이나 오래된 해시를 현재 검증으로 재사용하지 않는다. 비용 절감률은 계측 없이 숫자로 단정하지 않는다.

## 12. 근거 파일과 남겨 둔 확인 사항

| 파일 | 읽는 용도 / 현재와의 차이 |
|---|---|
| [CountessSkillComponent.cpp](../../Source/LearnTopDown/CountessSkillComponent.cpp), [Profiles/countess.json](Profiles/countess.json) | Q/W/E/R 실제 선택·타이밍. 프로필 `quality_gate.reason`의 1.5배속 R 천 관측은 과거 조건이며 현재 R 재검증 증거가 아니다. |
| [SparrowSkillComponent.cpp](../../Source/LearnTopDown/SparrowSkillComponent.cpp), [SparrowCharacter.cpp](../../Source/LearnTopDown/SparrowCharacter.cpp), [SparrowShotWave.cpp](../../Source/LearnTopDown/SparrowShotWave.cpp), [Profiles/sparrow.json](Profiles/sparrow.json) | 능동 E, R 부채꼴, 평타 연결, 망토, 원형 FX의 현재 구현. |
| [CountessQPreview.md](CountessQPreview.md) | 원본 칼 소켓 측정/곡면→직선 변형 이력. 본문의 Muted가 현재 최종 재질이라는 설명은 Wispy 우선 경로보다 오래됨. |
| [CountessWPreview.md](CountessWPreview.md) | 밀도→외곽→연결→내부 알파를 분리한 이력. 일부 1.5배속 문구와 예전 QA 폴더는 현재 기본 1.95/증거 존재 여부와 구분. |
| [SparrowFXPalette.md](SparrowFXPalette.md) | 기본 FX 금색/연보라와 Rogue 진홍색 팩 조사. HDR 수치는 화면 RGB가 아님. 표의 E 패시브/FX 없음은 능동 속사 추가 전 기록. |
| [SparrowBasicAttack.md](SparrowBasicAttack.md), [SparrowStopPolish.md](SparrowStopPolish.md), [SparrowCapePresentation.md](SparrowCapePresentation.md) | 상·하체 분리/정지/바람의 초기 원인. HeldAim 후속, 이동 바람 보정과 몸 충돌원은 현재 소스에서 추가 확인. |
| [README.md](README.md), [TrainingRoom.md](TrainingRoom.md) | 초기 설치/전환/검증 도구 안내. README의 R 0.2+0.2초/1.5배속, 초기 idle 발췌와 E 무시전 자세 설명은 현재 구현에 그대로 적용하지 않음. 전체 검사 목록도 매 수정의 의무가 아님. |
| [editor_task.py](editor_task.py), [render_lock.py](render_lock.py), [navigation_ready.py](navigation_ready.py) | 에디터 실행/잠금 범위/맵별 내비 준비. DLL 최신성이나 모든 프로세스의 직렬화를 보증하는 도구가 아님. |

아래는 **문서 취합만으로 해결됐다고 볼 수 없는 항목**이다.

- **궁수 후드 보류와 코드 기본값:** 이 대화에서는 후드 추가 작업을 보류했지만 현재 `Sparrow.Appearance.IvoryHood` 기본값은 1이고, `BeginPlay`에 원본 후드 재질을 전용 사본으로 바꾸는 경로가 있다. 「보류 = 코드 미적용」으로 기록하지 않는다. 이번에는 설정을 바꾸지 않았으며, 후드 작업 재개 시 실제 재질과 원하는 기준을 먼저 맞춘다.
- **LevelStart 의존성 누락:** §4의 기존 로드 오류는 별도 조사 대상이다. 이번에는 원인 수정·플레이 영향 판정을 하지 않았다.
- **문서의 검사 성공과 원본 동작:** `presentation_contract`의 원작 행동 검증은 여전히 `unverified`다. 에셋 이름·기능 통과·사용자 선택을 원작 게임 재현의 근거로 대체하지 않는다.
- 다른 문서/프로필의 과거 문장을 이번에 일괄 수정하지 않았다. 위 표로 충돌을 표시했으며, 해당 설치기나 검사를 다시 쓸 때 현재 소스와 적용 범위를 맞춘다.

## 13. 신규 D 재설계에서 확인한 원본 FX 연결

- **메시만 꺼내면 원본 모습이 보장되지 않는다.** Countess Wing의 Wipe 마스크는 `saturate(3*On-2*u) * (1-saturate(3*Off-2*u))`이다. 원본 DP 기본 `(0,1,1,1)`은 전체 투명이고 표시값은 `(1,0,1,1)`이다. `ParticleColor`, `DynamicParameter`, VertexColor/WPO와 원본 MI의 유효값을 함께 확인한다. 같은 DP라도 실제 저장된 출력이 4개인 에셋과 6개인 에셋이 있어 런타임 출력 배열을 읽는다.
- **위치 생성형 PSC를 부착만 하면 따라가지 않을 수 있다.** UE `UGameplayStatics::InternalSpawnEmitterAtLocation`은 위치·회전·크기를 절대 좌표로 만든다. D의 실제 사례에서는 `AttachToComponent` 뒤 `SetAbsolute(false,false,false)`와 명시적 상대 변환이 필요했다. 시전자 자리에 남은 파티클을 단순 수명/밀도 문제로 판단하지 않는다.
- **원본 전체 FX를 실제 LOD와 카메라에서 먼저 확인한다.** 이번 D는 사본 `P_CountessNightTideBody`의 local-space와 반복/잔여 수명만 전용으로 조정해 이동 본체로 삼았다. 원본 전체 구성의 품질과 정적 메시 단독 모양은 다르다. Slate 콜백 안의 에셋 복제/컴파일은 콜백을 다시 실행시킬 수 있으므로 재진입을 막는다.
- 근거는 [D 검토 결과](../../Saved/QA/CharacterPipeline/countess-D-rebuild-20261021/result.json)와 `countess_tide_materials.py`, `CountessExtraTide.cpp`다. 이는 대표 D의 구현 근거이며, 8개 품질 완료나 사용자의 미적 채택을 뜻하지 않는다.

- **Cascade 내부 플래그는 Python 읽기/쓰기 가능 여부를 따로 확인한다.** A/F 원본에 포함된 `ParticleModuleLocationBoneSocket.bEnabled`는 UE 5.8 Python에서 보호 속성이다. 전용 사본 5개 이름만 허용하는 `CountessFXQA.DisableExtraBoneSources`를 기존 `CountessFXAutomation.cpp`에 추가해 실제 엔진 타입으로 처리한다. 임의 SET 명령이나 텍스트 export에서 해당 값이 없다는 이유로 비활성화를 단정하지 않는다. 이 도구는 에디터 전용이며 원본 팩을 저장하지 않는다.

## 14. E 원본 참격·Serath 날개·궁수 분신 연결

- Countess XSlash의 실제 벡터 이름은 `ColorA/B/C`다. 설명상의 `Color01`을 가정하지 않고 `GetAllVectorParameterInfo`의 이름/association/index로 읽기 성공 여부와 MID 적용 후 값을 확인한다. 파티클의 실제 MeshMaterial override에도 MID가 들어갔는지 별도로 확인한다. HDR 원본의 peak는 최대50으로, 단순 RGB 압축만으로는 주황색 과노출이 남았다. E 전용 `Countess.Skills.EInkGain` .02/.06/.12를 같은 실제 카메라에서 비교해 기본 .06을 택했다. 원본 파티클·재질은 저장하지 않는다.
- Sparrow Rogue 후드는 `M14_CloakHood`, material ID13이다. Serath wing은 `M12_WingSplines`/`M13_WingMembrane`, IDs12/13이고 기본 WingAlpha0이라 표시값이 필요하다. 원본 Holy 팔레트의 청색·보라도 실제로 있으므로 황금 변신용 MID만 보정했다. 일부 낮은 LOD에는 spline 섹션이 없어 별도 wing 컴포넌트는 LOD0(ForcedLOD1)로 유지한다. `Idle_Wings`는 접힌 자세였고 펼친 유지에는 `Idle_Pose_Wings`를 사용했다.
- 천 섹션이 있는 Sparrow 분신은 `used_with_skeletal_mesh`만으로 충분하지 않았다. 전용 재질에 `used_with_clothing=True`를 저장해야 망토의 회색 기본 재질 fallback이 사라진다. 분신 천 시뮬레이션을 끄는 것과 셰이더의 clothing usage는 별개다. 최종 실제 전체 망토 색과 로그를 함께 확인한다.
- 관통 검사 fixture는 바닥 높이도 기록한다. 수련장 X1050 부근의 Ground가 Z621여서 대상 중심이 Z711로 배치된 사례가 있었다. 같은 높이 대상 관통은 X450/X750(Z90)으로 검증하고 벽 차단은 별도 fixture로 검사했다. 서로 다른 높이와 실제 벽 충돌을 투사체 관통 실패로 단정하지 않는다.
- 근거: [QWER 결과](../../Saved/QA/CharacterPipeline/qwer-rework-20261021/result.json), [추가 스킬 결과](../../Saved/QA/CharacterPipeline/ascension-skills-20261021/result.json). 실제 표본 확인과 사용자의 미적 채택은 별도다.

## 15. 궁수 자유 조준·다발사격·스킬 복제

아래63발/180cm 궤적은 §18 당시 이력이다. 현재 R과 질감 보강은 다음 §16을 따른다.

- 범위기에서 적을 지정하지 않아도 되려면 입력 컨트롤러의 타기팅도 확인한다. `Ground` 분기는 pawn을 제외한 커서 바닥을 읽어야 근처 적 중심으로 좌표가 다시 스냅되지 않는다. 기존 enum 뒤에 값을 추가해 저장된 기존 값의 의미를 보존했다.
- 화살63발을 모두 피해63회로 계산하지 않는다. `FireMultishotWave`는 회차별 표적 집합을 화살끼리 공유해 대상당20피해만 인정한다. 분신은 별도 집합과0.3배 피해를 쓰고 패시브 중첩을 기록하지 않는다. 패시브 허용 여부를 W 외형 판정에 재사용하면 분신 평타/E가 W처럼 보이므로, `bPiercing && bPassesWorld && !bUltimate`로 발사 종류를 구분한다.
- 입자 수를 늘린 뒤 실제 카메라에서 방향성이 사라지는지 본다. 첫 R은 기존 궁극기 꼬리가 겹쳐 번개줄처럼 보였고, 최종 R만 길이180cm/폭5cm 교차 평면으로 바꿔 화살 진행 방향을 드러냈다. W/E/평타의 궤적에는 적용하지 않았다.
- 후드와 망토는 같은 section이 아니다. Rogue는 끈3/망토7/후드13을 LOD별로 처리하고, 모든 재질과 기존 section 가시성을 저장해 종료 때 복원한다. S+D에서는 분신도 소유자 가시성과 실제 날개 포즈를 동기화한다.
- E 시안은 `sparrow_e_variants.py`의 임시 PIE 덮어쓰기이며 운영 기본값이 아니다. `Previews/E20261022` 재질3개와 실제0.20/0.53초 프레임을 남겼다. E1 열린 곡선/E2 깃털 별빛/E3 축 섬광 중 E3를 추천했지만 사용자 채택 전 자동 설치하지 않는다.
- 근거: [궁수 재작업 결과](../../Saved/QA/CharacterPipeline/sparrow-arsenal-20261022/result.json). 60fps127개 검사는 최종 R 잔상 조정 전, 30fps65개는 조정 후다. 최종 화면은 R=`verify30`, 나머지=`verify60`를 사용한다.

## 16. 비어 보이는 FX 보강 · 짧은 화살 군집

- **숫자와 길이를 따로 설계한다.** R은63개 긴 선보다186개 작은 화살이 사용자 의도에 맞았다. 31×6회/.10초, 꼬리30–55cm/폭1.5–2cm, 촉 .45–.60, 시각 위치0–35cm 분산이 현재 값이다. 판정 위치는 그대로 두고 시각 메시만 분산한다. 피해는 화살 수가 아니라 회차별 공유 표적 집합으로10×6=60을 유지한다. 애니메이션까지6회 반복하면 팔 동작이 지나치게 빨라지므로 기존3회 모션을 유지했다.
- **궤적과 질감을 대체 관계로 만들지 않는다.** E의 PrimaryTrail을 Wisps로 교체한 첫 결과는 여전히 비어 보였다. 원본 진행 궤적에 별도 PSC를 추가하고 폭1.5, Wisps80–110cm/alpha.5/45/s로 실제 카메라에서 보강했다. 원본 muzzle의 flare·GPU·광원 전체를 화살마다 복제하지 않는다. 선택한 emitter는 NativeDump로 이름·활성 LOD·수명·색·뼈 의존성을 먼저 확인한다.
- **runtime 복제본의 배포 목록과 색 분포를 확인한다.** transient 파티클 사본만 수정하고 `IsIn(Runtime)`으로 소유권을 확인한다. emitter 필터 후 `UpdateModuleLists()`를 재구성한다. 기존 baked 분포를 수정할 때 새로운 FRawDistribution/비베이크 분포를 넣어 이전 LUT가 남지 않게 한다. 원본 `GetEmitterName()`은 현재 엔진에서 non-const다.
- **원본 이벤트 체인을 유지한다.** Q의 Falling/FallingLingerArrows 충돌이 Hit/Impact/Light/Sparks를 구동하므로 전체 emitter를 임의 증폭/삭제하지 않는다. 현재 밀도3.2/scale.78, 전용 지면 질감은 원본 `T_TilingClouds_01`을 이용한 `M_SparrowHailAtmosphere`다. 저작 중 연결 미완성 경고와 최종 저장본의 새 에디터 컴파일 결과를 구별한다.
- **밀도가 높은 장면의 착탄은 따로 제한한다.** R+D가 벽에 닿을 때 작은 화살에 큰 파열을 각각 붙이면 과노출이 생겼다. R 벽 착탄만 명중 scale의 .22배/수명 .18초로 축소했다. 적 명중과 판정에는 적용하지 않는다. S/D 전환도 원본 Burst 전체 대신 plasma/flame shard만 추려 윤곽을 가리지 않게 한다.
- **검사 fixture의 상태를 명시한다.** 훈련 표적의 HP 초기화는 Sparrow의 대상별 Relentless 중첩을 지우지 않는다. E6발 피해 검사는 시작 중첩을 읽어 `10*(1+min(stack+i,10)*.0175)`를6회 합산한다. 영상 프레임은 실제 timestamp를 사용하고, fps가 달라도 대표 프레임의 시전 경과 시간이 같게 맞춘다.
- 근거: [현재 결과](../../Saved/QA/CharacterPipeline/sparrow-volume-20261022/result.json), `sparrow_volume_polish.py`, `sparrow_fx_depth_audit.py`. R 최종은 `verify-r-final`, W/E/A 등은 `visual-final-2`. 현재 스킨은 Rogue이며 날개 형태도 기존 Serath를 유지한다.

## 17. 과한 지면 효과 제거 · 짧은 후딜 · 외형 시안 분리

- 사용자 반려 후 Q 구름 평면은 생성·갱신·정리 경로까지 제거했다. 낙하만3.2→2.56으로 줄이며 이벤트 착탄과 피해 횟수를 유지한다. §16의 Q 안개/3.2는 과거값이다.
- W의 발사 모션과 행동 잠금은 별개다. 발사 .62초를 유지하고 RecoveryTime .72/종료 blend .06으로 줄였다. 저장 BP 이전값 이행과 실제 이동 입력·중단을 함께 확인했다.30/60fps 발사 후 잠금 .10초가 현재 근거다.
- 이름만 다른 FX3안을 성공으로 취급하지 않는다. E첫3안은 실제 쿼터뷰에서 공통 궤적/착탄광에 가려져 비슷했다. E1 긴 궤적 숨김, E2 곡면 파편 확대, E3 재질×입자색 역보정으로 분리했다. 미리보기마다 실제6발을 관측하고 두 PSC에 변경12회가 도달했는지 확인한다. 원본 템플릿을 바꾸지 않는다.
- 몸통/장비 섹션 이름만으로 부분 외형을 추정하지 않는다. Rogue 갑옷령은 발목 장식이 남았다. Raven의 연속된 상반신을 보존하고 새 시안 재질에 `WorldPos.z-CutBaseZ` 높이 fade를 적용해 실제 화면에서 하체 제거를 확인했다. 무기 슬롯은 별도 원래 Echo 재질로 유지한다.
- 시안 루프는 FPS에 맞춰 샘플 수를 환산하고, 연속 시전은 이전 Recovery 이후 실행한다. S복원은 시전시각+8초가 아니라 실제 발동 이후 잔여 시간을 따른다. UE5.8 Python PSC 종료는 `deactivate()`이며 `deactivate_system()`은 노출되지 않았다.
- 근거: `sparrow-feedback-20261022/result.json`, `sparrow_form_studies.py`, `sparrow_e_texture_studies.py`. A1의 불티를 추가해도 기존 밝은 중심이 지배적이므로 완성된 분쇄감이라고 과장하지 않는다. S/D 미적 승인과 E/A/D시안 채택은 별도다.

## 18. 가로 활 자세 · 단색 몸 · 실제 shader 오류 확인

- 활을 눕힌 자세는 투사체 회전이 아니다. Sparrow 원본 `R_Ability_Fast_Fire`에 가로 발사 자세가 있다. 발사 전 실제 `bow_shaft_top_03-bow_shaft_bott_03` 축의 수직 비율은.08–.09, 기존 Primary는 거의1이었다. 원본 복제/본 억지 회전 없이 A의 몽타주 참조와 시점만 바꿨다.
- 단색 에너지 몸을 원할 때 피부 텍스처에 색을 곱하는 방식은 장비 질감을 남긴다. 새 opaque/unlit 재질로 본체 실루엣을 유지하고 약한 윤곽 명암만 둔다. 원본 재질/망토 section을 저장해40초 후 복원한다. 큰 날개 전개는 등장.8초에만 두고 지속 중 화면을 덮지 않는다.
- HLSL `line`은 예약어다. Python의 재질 저장 성공과 C++ 빌드 성공은 shader 성공을 보장하지 않는다. 이번 A/E6의 회색 평면은 사용 플래그가 아니라 그 변수명의 컴파일 실패였으며 `strand`/`spineMask`로 고쳤다. 새 재질을 다시 저장한 후 실제 최종 화면을 확인하고, 옛 에셋 로딩 중 경고와 최종 상태를 구분한다.
- Echo 재질의 Visibility는 단순 opacity가 아니라 noise dissolve도 제어한다. 잔상에.2를 주면 실루엣 전체가 사라진다. 금빛 이동 시안은1/.92/.84/.76으로 형태를 남기고 위치·시간을 엇갈려 잔상을 보였다.
- 원본 질감을 모두 숨기고 얇은 수학적 선만 얹으면 서로 구분되더라도 밀도와 재질감은 나빠질 수 있다. E4–6은 진행 PSC 질감을 되살리고 도형 세기를 낮춰 보완했다. 시안 구분도와 최종 품질은 별개다.
- 근거: `sparrow-reforge-20261022/result.json`, `sparrow_a_sidecast.py`, `sparrow_s_silhouette.py`, `sparrow_ew_studies.py`, `sparrow_mobility_studies.py`. 이동 후보는 맞는 원본 모델에서 확인했으며 Sparrow 리타게팅이나 실제 회피 스킬 설치를 뜻하지 않는다.


## 19. 이동 클릭 보관 · 분신 대형 · SubUV 실제 채널

- 후딜 중 `MoveToCursor` 조기반환은 영구busy와 구분한다. 실제 짧은 우클릭→해제→후딜종료뒤 이동을 검사하고, 유효내비목표 하나를 pawn별보관한다. 행동이풀려도 root-motion blend가 `IsPathFollowingAllowed`를 한 프레임 막을 수 있으므로 둘다기다린다. 새공격/성공한스킬/flush/전환은예약을폐기한다.
- LeaderPose분신의 위치대형까지 본체조준yaw로매번회전시키면 원주이동이튀어보인다. 대형yaw는실제이동방향으로천천히회전시키고 몸/활yaw는본체자세와맞춘다. 본체평행이동과대형offset보간을분리해야발미끄러짐이늘지않는다. 천시뮬을끄면굳은망토가남으며, `BindClothToLeaderPoseComponent`는본체cloth를localspace로바꾸는부작용이있어이번에는분신천섹션을숨겼다.
- `T_Plasma_Wisps`의RGB를opacity로추측하지않는다. 원본실제그래프는SubUV.A가형태/R이내부명암이다. B는대부분최댓값이라maxRGB마스크는가득찬판/구슬을만든다. 단순radialfalloff는모서리만가리고불꽃결을복원하지못한다. `plasma-audit/plasma-readonly-audit.json`과읽기전용export로채널을확인한후새재질에A/R을연결했다.
- 새회피시안은다른캐릭터도너그대로재생과구분한다. 같은Sparrow165본의준비/정점/착지/후진포즈를새AnimSequence로보간했으나, 충돌/벽/무적/입력은별도실제스킬작업이다.
- 근거: `sparrow-finish-20261022/result.json`, `sparrow_movement_stress.py`, `sparrow_forms_repair.py`, `sparrow_fresh_studies.py`. 실패run은보존하고최종영상별출처는delivery-clips.json을따른다.


## 20. 에너지 날개의 주층 · 원본 불꽃 침식 · 고정 원점 시전 인계

- 얇고 매끈한 수학 코어가 밝으면 불꽃 texture를 곁들여도 철사로 보인다. 실제 쿼터뷰4px 폭에서1px미만 코어만 남던 S를 반려했다. 전용 리본폭/중간 굵기/끝갈라짐을 늘리고 코어를 texture로 끊으며 황금sheath를 주층으로 바꿨다. 메시 형태·불꽃 알파·내부명암·흐름을 각각 확인한다.
- SubUV.A/R을 맞춰도 원본의 수명별 침식을 빼면 구름처럼 뭉칠 수 있다. E7 새 재질은 pow(A,.85)*sqrt(ParticleAlpha)*1.5로 낮은alpha를 증폭했다. 실제 원본 graph는 A*ParticleAlpha에서 RelativeTime 기반 임계치를 뺀다. E7 주층만 원본 transientMID로 되돌려 침식을 복원했다. 공유재질·원본팩을 덮어쓰지 않는다. 원본 Wisps의 실제 emitter slot5와 단일RapidFlow slot0 적용을 get_material로 기록했다.
- 생성된 같은 프레임에 visible을 요구하지 않는다. S는 ConfigureVisual에서 숨기고 첫Tick에 Envelope를 올린다. component수/초기visible/실제wait/최종visible을 기록하고 짧은한도만 기다린다. 영구숨김은 여전히 실패한다. C++ getter 이름이 있어도 UFUNCTION 없으면 Python API가 아니다. get_wing_mesh/get_slot_cooldown_remaining 오류를 엔진노출 component조회/실제키 쿨타임검사로 바꿨다.
- W 분신 인계는 피해를 복사하는 새 공격이 아니라 원래 예정된 한 발의 소유권 이전이다. 발사여부/남은시간/애니메이션시각/조준을 FinishSkill 전에 캡처하고, 원래타이머를 해제한뒤 분신타이머 하나만 둔다. 이미 발사한 W는 재생만하고 추가피해를 만들지 않는다. 분신은 SceneRoot를 출발점에 고정하고 skeletal child만 원본 상대변환을 따른다.
- 백스텝은 기존 행동을 정리한 뒤 root-motion/회전 상태를 저장해야 한다. 종료/벽충돌/몽타주중단/소유자종료 모두 같은복원 경로를 쓴다. 30/60fps에서 미발사/이미발사 W를 분리하고, 새우클릭 이동까지 확인한다.
- 근거: `sparrow-partner-20261023/result.json`, `sparrow_energy_partner.py`, `sparrow_e_refinement.py`, `sparrow_backstep_review.py`. 새에셋저작 뒤 Space1회거부는 원인미확정이며 단독/같은순서새세션은 정상. 정상재실행만으로 원인을 만들어내지 않는다.


## 21. 황금 날개 참조 · 붙는 그림자 · 섬광 이관 · 급후퇴

- 디아블로 황금날개를 이름/기억만으로 가는 갈고리선으로 만들지 않는다. 공식 Wings of Valor GIF의 실제 프레임에서 넓은 빛의 화염띠, 밝은 등쪽 뿌리, 흐릿하게 침식되는 끝을 확인했다. §20의14곡선/fork 형태는 이후 사용자에게 반려된 이력이다. 현재는6개 넓은띠/물리fork0이며 원작 동일 외형 인증은 아니다.
- 곡면2장과 여러띠가 겹치면 개별 alpha가 낮아도 HDR 전체가 흰색으로 찬다. 실제쿼터뷰에서 주색/실루엣을 보고 alpha와 gold/whitehot을 분리한다. r2는alpha*.72, 본체gold(1.85,.70,.015), whitehot은뿌리와작은열점으로만 제한했다.
- 섀도우 파트너를 몸에 붙은 그림자로 요청하면 독립궁수 대형 보간은 부적합하다.45cm뒤/같은회전·포즈를 즉시 따르고, 공유dissolve재질을 억지로낮추는대신 전용반투명 단색재질을 쓴다. 기존10초/30%/무날개 복제는 유지한다.
- R 섬광 제거는 표적착탄뿐 아니라 world착탄·발사muzzle까지 확인한다. 기존 target축소만으로 큰 wall파열이 남았다. target/world의실제 emitter명을Sparks로제한하고 fallback을없앴다. A3파열은별도소유actor/독립타이머로 추가피해없이 재생하며 projectile종료와owner종료를 구분한다.
- 급후퇴는 실제이동과애니메이션을함께줄인다. 이동.16초/몽타주.20초와급출발감속을 쓰되, 이미준비한W의남은발사시간은배속에곱하지않는다. 원점분신에한발만인계하고본체이동완료후에도남은원래발사를독립적으로진행한다.
- 실제 화면에서 E후류를 과하게 쌓으면 흐린 덩어리가 된다. E10은익궁실루엣만확실히남기고 큰반복Wisps를제거/실조회한원본침식재질MID/폭1.05로정리했다. E11의흰구름도반려하고 gold코어/좁은6핀분출로바꿨다. 서로다른조형이실제로읽히는지같은.30/.57초프레임을대조한다.
- 저작동반세션의nav투영실패와새게임세션정상은분리기록한다. projected=false까지확정해도타일재빌드가원인이라고추정확정하지않는다. 에디터world nav완료는 PIE world의모든목적지투영증거가아니다. 안전검사를빼서검사를통과시키지않는다.
- 근거: `sparrow-gold-revision-20261023/result.json`, `sparrow_energy_partner.py`, `sparrow_backstep_review.py`, `sparrow_r_finish_review.py`, `sparrow_e_refinement.py`. 적용본과미채택E시안을구분한다.

- 첫시전선명도는코드분기와분리한다. E10/E11순서를반대로실행하자먼저시전한안의후류만흐리고두번째시전은선명했다. 이를재질수정효과로잘못확정하지않고, 두최종영상은동일한후속시전조건으로맞췄다. 실제스트리밍mip/렌더계측은안했으므로원인명은미확정이다.


## 22. 원래 형태와 새 질감의 분리 · 완성된 파티클 체인 보존

- “형태는 롤백, 질감만 변경”은 기존 skeletal mesh·펼침/유지 애니메이션·spline 슬롯을 복구하고 membrane의 원래 opacity/WPO 그래프를 새 전용 재질에 그대로 복제하는 것으로 처리한다. 새 곡면띠의 윤곽을 원형 복구라고 부르지 않는다.
- 원본 Aura 같은 mesh particle은 RequiredModule.Material만 복사하면 부족하다. `ParticleModuleMeshMaterial`의 실제 override와 DynamicParameter/RandX/RandY/Refraction/Param4, ParticleColor·원래 erosion 수명을 함께 보존한다. 새 평면에 비슷한색을 입힌 결과를 원본 재질의 질감과 동등하다고 판단하지 않는다.
- A의 비어 보임/둔한 인상은 입자 수 부족만이 원인이 아니다. 중심 Airglow가 회전 날을 덮는 실제 프레임을 확인하고, 중심크기.70→.24와 두번째 날 강도.32→.46을 별도로 조절했다. 이미 inherited UltimateTrail에 있는 mesh층을 중복 추가하지 않는다.
- R에서 큰 섬광 제거는 큰Flare·LightsOnly/광원층만 제외하는 것이다. Main Flames/Wisps/Sparks/선형파열을 모두 제거하면 요청보다 과한 변경이다. 활 앞 발광도 별개로 판단한다.
- 초단기 잔상은 실제 충돌 sweep이 통과한 진행률에서만 포즈를 기록한다. 출발점의 실제 W인계분신과 이동 중 피해없는3개 pose snapshot은 기능이 다르다. 포즈는 고정하고 opacity만짧게감쇠해분신이달려오는모습을피한다.
- 동일Tick의MID파라미터갱신 직후 screenshot요청은 직전렌더프레임을 잡을 수 있다. D공격윤곽은2프레임 뒤 원본영상에서 확인해 대표이미지를고른다. 선명도문제를재질밝기부족으로즉시단정하지않는다.
- 이 묶음의 적용/시안 구분과 실제 근거는 `SessionHandoff-20261021.md` §25 및 `Saved/QA/CharacterPipeline/sparrow-texture-restore-20261023`에 둔다.


## 23. 강렬함을 가리는 중복 잔광 · 평면 날의 명암 · 부드러운 변신

- W구름이남으면새부품을계속줄이기전에발사경로전체의중복을확인한다. 이번에는PrimaryMuzzle와R용BowGlow가각각Wisps를재생했다. W전용MuzzleGlow/Airglow/Sparks/작은MuzzleFlare 한 번으로분리하고R경로는보존했다. 관통체의길이·폭/팽창대비/잔상수명은따로조절한다.
- 넓은평면날에고른고HDR노란색을쓰면금속날이아닌플라스틱도형처럼읽힌다. A6/A7초안을반려하고어두운청동면/금색bevel/흰razor를좁게분리했다. 실제쿼터뷰의대표프레임에서면과끝의명암을확인한다.
- 원본MeshCoronaLarge의.55초수명은긴느린투사체의계속되는본체가아니다. A8처럼긴비행에서는원본수명·DP침식을보존하며.30초간격으로교대생성해최대2개만겹친다. 시안종료에모든임시PSC를회수한다.
- S의부드러움은전체시전만늘려서끝내지않는다. 저장BP정의의Action/Recovery·montage진입/복귀blend·날개PlayRate와Idle전환타이머·진입opacity를같은의도로연결한다. S0.9→1.35초/.16-.24blend/Unfold.8배/.55fade를실제시전중우클릭큐의이동복귀까지30/60fps짧게검사했다.40초변신과원본형태·복구는유지한다.
- 근거: `sparrow-fire-forge-20261023/visual30`, `final30`, `smooth60` 및 handoff §26. 첫시각반려와최종촬영출처를구분하고미적채택을자동완료로기록하지않는다.


## 24. 표면 무늬와 불꽃 자체의 구분 · 혼합 시안의 핵 가독성

- 막alpha를94~100%고정하고emissive만흘리면표면위에덧댄인상이남는다. 고정gold spline까지같은root상대Fire장으로직접침식하고원본alpha는지원mask로만썼다. 별도입장plasma/flame를없애고원본mesh/WPO/전개를보존했다. 이것은원본팩을수정하지않고전용2재질에서처리한다.
- sourceAura의MeshCoronaLarge는LOD0만켜져있다. 자동LOD와카메라거리를고려해야하지만이번A9는강제LOD0만으로희미한핵의원인이확정되지않았다. 명확한근거없이LOD가원인이었다고보고하지않는다. 최종A9는기존회전날표면에흐르는질감의핵을직접통합하고원본Flames2짧은꼬리만붙였다. 실제이미지에서핵과외곽날이함께읽히는지확인한다.
- W의얇은느낌복구는메시폭뿐아니라Aura횡폭·보조가닥까지함께복구하되사용자가유지한발사효과는보존한다.
- 근거: handoff §27 및 `sparrow-native-flame-20261023`의최종·반려촬영출처.

## 25. 영상은 메타데이터와 실제 화면 출력을 구분한다

- IAB에서 H.264 MP4는 readyState4·오류0·시간 증가에도 검은 화면이 나왔다. 같은 캡처의 VP9/WebM·yuv420p에서는 실제 화면이 출력됐다. 현재 미리보기는 WebM 우선, MP4 보존용/대체 소스다. `play()` 거부도 화면에 알린다.
- 재생 완료 확인은 실제 화면과 시간 진행을 함께 본다. 인코딩/전체 디코딩 통과나 브라우저 메타데이터만으로 대체하지 않는다.
- 사용자 요청에 따라 전달 확인이 끝난 연속 PNG는 대표 프레임·명시 참조 파일만 남기고 바로 정리한다. 삭제 전 허용 루트·파일 종류·길이를 확인하고, 삭제 뒤 잔여와 확보 바이트를 기록한다. 보존 영상·대표 이미지·로그·QA JSON·게임 적용 파일·원본 에셋은 유지한다. 정리 뒤에는 전체 원시 프레임이 남아 있다고 보고하지 않는다.
- 근거: handoff §28 및 최신 QA의 `cleanup-result.json`.

## 26. 원본 레이어의 시간 분리 · 표면 밀도와 일렁임

- W 착탄은 입자를 무작정 늘리기보다 작은 핵(.055~.075초), 금빛 메시 화염의 두 짧은 burst, 후속 선형 파편으로 시간을 나눈다. 원본 MeshMaterial/DP/flipbook 체인은 transient 복제본에 보존하고 R/평타가 공유하는 소스는 수정하지 않는다. 얇은 비행체와 착탄 볼륨은 별도다.
- `HasImpactLightModules`는 표적/벽 효과를 모두 검사한다. 벽을 통과하는 W에서 사용하지 않는 기존 PrimaryWorldHit의 광원을 새 표적효과의 결함으로 판정하지 않는다. 실제 사용 경로와 검사 범위를 맞춘다.
- S 밀도는 Fire coverage와 threshold를 조절하고, 일렁임은 큰 흐름/잔물결 UV와 작은 root-anchored WPO로 나눈다. 원본 WPO를 새 노드 입력으로 연결하고 저작 marker로 중복 누적을 막는다. 현재 변형 폭은 뒤축1.6cm/상하.6cm이며 원본 형상과 접합부를 실제 화면에서 확인했다.
- 감속 시안은 실제 느려진 명중까지 관찰 시간을 늘린다. A160cm/s에서 기존3초보다 긴3.6초로 실제90피해·관통을 확인했다. 기존 검사 통과를 외형 채택으로 해석하지 않는다.
- 근거: handoff §29 및 `sparrow-impact-flow-20261023`.

## 27. 다른 리그의 구르기를 황금 실루엣으로 사용하기

- 잠깐 보이는 단색 대역이면 원래 메시와 일치하는 구르기 리그를 함께 사용해 리타게팅을 생략할 수 있다. 이번 Quaternius Roll은 실제 원본 샘플을 보존한 GLB와 매칭 마네킹을 설치했다. 파일명 조사/공식 뷰어 확인/다운로드 후 실제 재생은 서로 다른 증거로 기록한다. 라이선스와 출처를 소스 옆에 보존한다.
- 게임 이동은 기존 capsule sweep/nav를 유지하고 대역은 충돌 없이 owner XY를 따른다. 원본 root motion으로 이중 이동시키지 않는다. .16초처럼 매우 짧으면 클립 시간은 이동 진행률로 직접 맞추며, 원래 Sparrow 출발점 분신과 이동 중 구르기 잔상의 메시/역할을 분리한다.
- 본체 숨김은 child propagation 없이 처리하고, 별도 actor인 S 날개는 이전 hidden 상태를 저장해 복구한다. 정상 종료뿐 아니라 충돌/owner 종료도 같은 복원 경로를 탄다. 구르기 후 같은 S actor/재질/section과 새 이동 입력까지 확인한다.
- W 인계 검증은 준비 중1발과 발사 후0발을 나눈다. 시각 대역 교체가 고정 분신의 socket/포즈/지연 타이머에 영향을 주지 않도록 기존 Sparrow clone을 유지한다. 실제 피해35와 발사 수를 함께 본다.
- C++ header 멤버라도 Python reflection에 노출됐다고 추정하지 않는다. CurrentAsset은 editor property 조회가 실패해 읽기 전용 native getter로 실제 바인딩을 검사했다. 엔진 GetCurrentAsset의 const 제약도 현재 헤더로 확인한다. 실패 run은 그대로 두고 최종 검증을 별도로 만든다.
- 근거: handoff §31, `quaternius_roll_import.py`, `SparrowBackstepEcho.cpp`, `sparrow_backstep_review.py`, `sparrow-gold-roll-20261023/result.json`. 최종30/60fps 통과 뒤 빌드·실제 영상4개·브라우저 화면 확인을 끝냈고, 번호형 캡처417개는 대표27장만 남기고 정리했다.

## 28. 기존 이동기 복원과 새 이동기 슬롯 분리

- 기존 키의 구르기만 롤백하면 원점 분신/W 타이머까지 지우지 않는다. Space는 기존 actor에서 대역/몸숨김만 제거하고 잔상 메시를 본체로 되돌렸다. 긴 F는 별도 `ASparrowGoldRoll`/쿨다운으로 분리해 Space의 발사 인계 소유권에 영향을 주지 않게 했다.
- 빈칸을 채울 때 새 키를 임의로 추가하기 전에 기존 컨트롤러 slot11=F와 HUD의 display-name 기준을 확인한다. 독립 actor가 움직이면 몽타주용 bCasting만으로는 입력/평타/이동 잠금을 표현할 수 없으므로 공통 IsCasting과 활성 슬롯·취소·owner 종료를 함께 연결한다.
- 원본1.47초를 그대로 보이게 하면 .16초 배속과 달리 원본 시간 .20/.65/1.10초의 포즈와 종료를 직접 비교할 수 있다. 실제 이동은 capsule sweep/안전 목적지로 소유하고, 시각용 대역의 root motion과 분리한다. 충돌/중도Destroy에서도 원래 가시성/S 날개/root-motion/회전을 복원한다.
- 검증 범위는 새 F 전체 기능30fps와 관련 pose/S 복구60fps, 롤백한 Space의 기존 관련 case로 나눴다. 영상은 `SPARROW_MOBILITY_VIDEO_CASES`로 전달할 case만 녹화해 불필요한 원시 프레임을 줄였다. 근거: handoff §32 및 `sparrow-roll-split-20261023/result.json`.


## 29. 대역 전방 축 · 입력 수락 시점 · 시안 파티클 활성화

- 다른 리그의 전방은 이름으로 추정하지 않는다. Quaternius glTF의 foot→ball/+Z와 엔진 ConvertVec3(X,Z,Y)를 대조해 UE+Y임을 확인하고 capsule+X에 yaw-90을 적용했다. 네 방향 이동과 실제 대역 yaw를 함께 검사한다. 도약·회전·착지의 포즈시간과 capsule 이동곡선은 분리하되 종료 후 미끄러짐을 측정한다.
- 시전 중 이동 예약이 사라지는 현상은 영구 이동잠금과 구분한다. 실제 입력 순서 W→우클릭 예약→거절된 좌클릭에서 큐 손실을 재현했다. 공격 수락 전에 큐를 지우지 않고, held-attack 재시도에서 수락될 때도 같은 규칙으로 이동 의도를 대체한다. 새 우클릭이 되는지와 예약 자체가 살아 있는지를 따로 본다.
- 자동화 Key 명령은 키를 큐에 넣는다. 같은 Python 콜백에서 즉시 재질을 검사하면 실제 입력 처리 전 상태다. 한 실제 tick 뒤 casting/active slot/바뀐 재질 슬롯/처리시각을 기록한다. native getter가 UFUNCTION이 아니면 Python 노출을 가정하지 않는다. Wings 수명은 공개된 Actor.get_life_span으로 확인했다.
- 실제 게임의 즉시 활 변색은 원래 bow-only 슬롯명을 조회한 뒤 그 슬롯만 바꾼다. 변신 같은 다른 효과가 중간에 복원하면 현재 복원 기준을 갱신하며, 종료시 자기 MID가 여전히 적용돼 있을 때만 원래 재질을 돌린다. R 취소와 변신 중첩을 실제로 확인한다.
- 시안 PSC의 set_editor_property는 재등록을 유발할 수 있다. bAutoActivate=false로 만든 효과에 Activate 뒤 component_tags/generate_overlap_events를 설정하면 활성입자0/active=false가 됐다. 속성을 전부 설정한 뒤 Activate하고, 마지막에 SetEmitterEnable 마스크를 적용한다. 생성 카운트만으로 화면 표시를 통과시키지 말고 실제 활성입자와 화면을 확인한다. component LOD만 강제한 시도는 이 문제를 해결하지 못했으며 LOD0에서도 inactive였다는 기록을 남겼다.
- 시안 파티클이 안 보이면 먼저 활성화와 렌더되는 emitter를 확인한다. 안 보이는 상태에서 크기/밀도만 올리면 원인을 가린다. 날개 생성 시점과 실제로 펴지는 시점을 구분하고 후자에 짧은 효과의 최고점을 맞춘다. 비교 시안이 실제 운영 키에 설치됐다는 표현은 하지 않는다.
- 근거: handoff §33, sparrow-vault-arsenal-20261023/result.json, entries-active30/V1_entry_120.json 및 entry-firstlod30/V1_entry_120.json. 최종 시안은 entries-final30, D는 sentry-active30이다.


## 30. 대역과 본체 연결 / 고정 분신의 실제 공속 / 렌더 근거 시안 보강

- 원본 리그 대역을 끝에서 bool로 교체하면 착지가 끊겨 보인다. 대역 opacity를 먼저 낮추면서 본체 자세의 금빛 overlay를 드러내고 실제 몸을 종료 전에 돌려준다. 원본 재질 전체를 바꾸지 않고 소유 전용 translucent MID의 Visibility만 제어하면 종료·취소 복원 범위가 작다. F는 실제 source mesh 재질/section을 보존한다.
- LeaderPose는 뼈 자세를 공유하지만 source cloth의 시뮬레이션 정점을 그대로 그리지 않는다. 첫 착지 화면의 뻣뻣한 금빛 망토판을 확인한 뒤 overlay에서만 이름으로 Cloak/Straps/Hood를 제외했다. 본체 cloth sim-space를 강제로 바꾸는 우회는 피했다. 나머지 overlay section은 source 상태를 따르고 source 자체가 유지되는지 QA한다.
- 회전 잔상은 생성 시 뼈·월드transform을 UPoseableMesh에 고정한다. 매 tick 소유자를 따라가게 하면 잔상이 아닌 붙어 있는 분신이 된다. 생성 시각/고정 위치·뼈/opacity 감소/종료 정리를 실제30·60fps에서 본다. 날개도 별도 actor visibility 계수로 연결하고 종료에1로 복구한다.
- 이동큐 테스트는 클릭 ray의 지면 hit뿐 아니라 navigation projection과 실제 Queued 이벤트까지 확인한다. NoNavProjection으로 처음부터 예약되지 않은 입력을 큐 소실 버그로 기록하지 않는다. 이번 fixture는 시작 화면에서 투영되는 가까운 좌표를 선택하고 처리된 목표를 기록한다.
- 설치형 D의 공속은 고정 숫자 복사 대신 본체 실제 Primary montage 길이/(PlayRate*RateScale)+ComboRestartCooldown에서 읽는다. 애니메이션과 발사시각을 같은 주기로 맞추고, 이전 skill echo callback은 중복 피해를 만들지 않도록 분리한다. 표적0·시야·기본피해비율·설치위치 고정·수명·준비취소/전환 정리를 별도로 확인한다. 날개/변신 cloth hide를 분신에 복사하지 않는다.
- V 날개 크기를 줄이면 mesh scale과 anchor 역이동을 함께 조정해야 등에 붙는 위치가 유지된다. 펼침 animation과 visual envelope를 같은1.75배로 맞추고 V2 입자 지연도 같은 계수로 맞춘다. 원본 pack을 수정하지 않는 transient emitter-filtered duplicate를 사용하고 모든 속성을 설정한 뒤 Activate한다.
- 시안은 particle 수가 살아 있어도 형태가 약할 수 있다. A12/N3는 첫 실제 캡처를 본 뒤 곡선으로 연결된 후류와 둥근 핵으로 보강해 재촬영했다. existing NoxGlowStrip/NoxSpark를 금빛 MID로 재사용하되 원래 asset은 유지한다. 시각용 비교 조각을 실제 반사 투사체나 회복 기능으로 설명하지 않는다.
- 근거: handoff §34, sparrow-vault-v2-sentries-20261023/result.json. 기존 실패 run 상태를 유지하고 성공한 case만 좁게 재사용한다. 최종12영상 WebM/MP4 전체 디코딩·IAB 재생 후 번호형 임시PNG1,882개를 제거, 대표57장과 이름 있는 캡처/검증 기록을 보존했다.


## 31. 실제 결박 복구 · 방어막과 native 충돌 순서 · 최종 근거 교체

- AI 결박에서 PauseMove 뒤 StopMovementImmediately를 호출하면 UNavMovementComponent→StopActiveMovement→OnUnableToMove로 실제 요청이 Abort된다. 이동모드만 되돌려도 원래 경로는 복구되지 않는다. StopMovementKeepPathing으로 정지하고 원래 bStopMovementAbortPaths/tick 상태를 보존하며, 만료·취소·owner 종료에 같은 request가 아직 Paused일 때만 Resume한다. QA는 mode 값뿐 아니라 request ID·tick·실제 정지/재개 변위로 확인한다.
- 투사체보다 먼저 Tick하는 방어막이 예측 구간에서 탄을 삭제하면 더 가까운 벽·표적을 건너뛸 수 있다. 지원 native projectile의 실제 Start/End와 guard 교차 분율을 구하고, 기존 정렬 Sweep Hit.Time 사이에 차단을 처리한다. 앞선 비관통 명중/벽/굴절이 끝낸 경로는 반격하지 않는다. 약참조·같은 world·EndPlay 제거 registry로 매틱 모든 actor 스캔을 피한다.
- 차단 근거는 가짜 입자 소멸이 아니다. 실제 Launch/Sweep의 무방어 native hit1, 방어 후0, 발사자 반격12피해, 본인/뒤쪽 통과를 비교한다. 같은 프레임 벽 선행 검사는 native WorldHit와 이동거리153cm, block0/counter0으로 기존 충돌 경로 보존을 확인했다.
- 자동화 Key/use는 입력 큐이므로 최소 한 실제 tick 뒤 활성 슬롯·쿨다운을 읽는다. AI fixture는 실제 navigation projection을 통과한 시작/목표 좌표를 사용한다. 입력 대기 누락·Nav fixture 실패와 운영 코드의 요청 Abort를 서로 다른 실패로 기록한다.
- 후속 수정으로 대체된 검사는 전 run 통과 개수를 그대로 더하지 않는다. 이번 timing60은 구르기/Countess1184만, concepts-first30은 A14의9개만 재사용하고 S/F는 sanctuary-final30의59개/final60의40개로 교체했다. 실패 run은 실패 상태로 남긴다. 비교용 D 오브젝트를 실제 피해/AI/운영 키 적용이라고 설명하지 않는다.
- 근거: handoff §35, sparrow-sanctuary-arsenal-20261023/result.json 및 sanctuary-final30/sanctuary-native-review.json. 실제 S65/F108 화면·빌드·18영상 전체 디코딩·IAB 실제 출력/시간진행/오류0·확대/반속/단일재생을 확인했다. 확인 뒤 번호형PNG2,539개/4,787,585,016바이트만 삭제하고 대표83장과 이름 있는 캡처/미디어/기록을 보존했다. cleanup-result.json에서 예정 잔여0·보존누락0을 확인하고 완료 상태로 갱신했다.


## 32. Countess 실제 형상 조사 · 곡면 분할 · 세계 효과와 행동 수명 분리

- 메시 이름만으로 가시/검격의 체적을 보장하지 않는다. Aurora Spike Single/Single2는 실제 bounds Z≈0/16삼각형 리본이며 원래 재질의 WPO에 의존했다. 이를 단순 MID로 덮은 첫 화면은 직사각형이었다. bounds/내보낸 geometry/원래 opacity·WPO를 먼저 확인한다. 실제 입체 fragment의 뾰족한 끝도 local -X임을 조사해 방향을 맞췄다.
- 원래 shadow의 상수색×Fresnel만 넓은 면에 쓰면 검은 도형처럼 보인다. 원본 opacity/dissolve는 유지하되 실제 Countess ink/noise를3D 투영해 이동시키고, 검붉은 면 변화·좁은 crack filament·붉은 edge를 나눈다. 전용 소유 재질에 버전 marker를 두어 반복 저작의 노드 중복을 막고 원본 hash를 확인한다. 밝기만 올리는 것으로 질감 문제를 해결하지 않는다.
- spline은 없는 세로 정점을 만들어 주지 않는다.10삼각형 wedge를 휘어도 큰 삼각형 면이 남았다. 기존 SM_Spline_Claw는384삼각형이지만 조사 결과3방향 T형 리본이라 평행3검격의 실루엣과 달랐다. 최종은 소유32분할/256삼각형의 가늘고 양끝이 좁은 blade를 검증된 OBJ import 경로로 만들고 spline usage 재질을 적용했다. 최종 실제 화면에서 세 곡선을 확인했다.
- 시전 행동 잠금, 설치된 세계 효과, 아직 남은 commit 예약,24초 변신은 수명이 다르다. V 후퇴는 원점 field를 보존하고 준비 중이면 남은 delay만 한 번 인계한다. S 재질은 보통 시전 종료로 복구하지 않는다. owner 전환/종료에는 모든 field·예약피해·변신을 정리하며 material 복원은 소유권을 확인한다. 입력 회복은 bool뿐 아니라 실제 새 이동과 mesh offset/root motion/회전으로 검사한다.
- Python enum 이름을 C++ 표기에서 추정하지 않는다. WORLD_DYNAMIC 미노출 때문에 첫 boundary run은 시작 단계에서 실패했다. CollisionChannel 항목은 노출 이름을 조회·정규화하고 응답 타입은 실제 CollisionResponseType을 사용한다. 키 명령은 큐에 들어가므로 처리 tick 전에 casting/material을 단정하지 않는다.
- 화면상의 커서 ray는 의도한 벽 뒤 좌표 대신 벽 앞을 hit할 수 있다. 차단 자체는 명시한 뒤쪽 point의 공개 TryUseSkillSlot으로 검사하고, 동일 WorldDynamic 벽의 Visibility Ignore 뒤 실제 키로 정상 발동·피해를 확인한다. R/A/D/V는 실제 키의 Block/Ignore 대조를 유지한다. 피해가 없다는 결과 하나만으로 벽 차단을 입증하지 않는다.
- 이전 Space 안전/nav 거부의 원인은 확정되지 않았다. 같은 순서 S→F→Space의30/60fps 통과는 최종 동작 근거이며 ‘nav 버그를 고쳤다’는 근거가 아니다. 실패 JSON을 덮어쓰지 말고 확인된 QA enum/target 가정 오류와 미확정 원인을 분리한다.
- 기능 통과와 시각 수용은 별도다. baseline30 gameplay120이 통과해도 직사각형 화면은 반려했고, refined30 전체148이 통과해도 E/R/D의 검은 도형은 다시 보강했다. 마지막 gameplay60fps308 뒤 형상/재질만 바꿔 E/R/D30fps62개를 확인하고 변경 없는 A/S/V/F/Space5영상을 재사용했다. 실패·대체 run의 숫자를 한 번의 전체 성공처럼 합치지 않는다.
- 근거: handoff §36, countess-inferno-20261023/result.json, form-move-boundary30/countess-ruin-asset-inspect.json 및 geometry JSON, ruin-final30/countess-ruin-surface.json. 최종8영상 전체 디코딩·브라우저와 번호형PNG1,429개/2,584,444,089바이트 정리는 완료했다. 마지막 V 암전 보강은25검사와 최고점/마지막0130의 정상 밝기 복귀 화면으로 확인하고 V만 교체 인코딩했다. 나머지7개 미디어 hash를 유지했으며 새 V의 브라우저 검증은 별도 JSON으로 남겼다. 큰 검증 묶음을 반복하지 않고 변경된 V의 실제 화면과 복구를 확인했다. 대표 번호형66장·최종347보존파일의 누락0과 삭제예정 잔여0을 검증했다.


## 33. Space 모드별 시간축 · 실제 순간이동 · 시안 차이와 저장 경계

- 구르기 가속은 포즈만 배속하지 않는다. presentation phase1.05초에 같은2.625배 시간을 적용해 이동·잔상·착지까지 실제.40초에 맞췄다. QA의 F_idle_t055처럼 예전 이름의055는 phase 기준이며 실제 경과는.55/2.625다. 입력은 SpaceBar/active18이고 현재 운영에 없는 legacy M9 분기는 실행하지 않는다.
- 변신 순간이동은 빠른 선형 이동과 구분한다. 발동 시 V 유효 여부로 모드를 고정하고, blink는 real-time Age .035초 뒤 단 한 번의 swept SetActorLocation/TeleportPhysics를 수행한다. 구르기용 배속 phase를 blink .14초에 다시 곱하지 않는다. 실제 실행은30/60fps 프레임 경계에서 일어난다. 사전 안전 지면/nav와 commit-time sweep을 유지하고 벽·취소·공유 쿨다운·이동 예약을 함께 본다.
- 변신 중 이동의 복원은 첫 모습의 복사만으로 끝내지 않는다. 살아 있는 같은 wing actor의 hidden/visibility 상태를 보존하고, 이동 중 변신 만료 또는 캐릭터 전환이 있어도 만료된 외형을 되살리지 않는다. 몸 재질/section·root motion/회전과 실제 이동 복귀를 비교한다. 출발 잔상은 현재 본체 포즈를 고정하고 blink 경로에 Roll 대역을 깔지 않는다.
- 시안 차이가 약하면 같은 효과의 색·크기만 미세 조정하기보다 긴 직선/단계 광침/열리는 후광처럼 실루엣과 발사 후 시간 구조를 분리한다. 첫 화면에서 W2 광침은 구별됐지만 W1의 원래 발사 고리가 남았고 W3 arc는 너무 얇았다. refined30 실제 화면에서 W1 고리 제거와 W3 층별 arc 대비가 읽히는 것을 확인했다. native distance/speed로 발사 원점과 age를 복원하면 키 입력 지연과 첫 관찰 프레임을 섞지 않는다. 원래 ShotWave::Tick이 컴포넌트 visibility를 매프레임 덮으므로 해당 방식으로 숨긴 첫 화면에도 AirWave0/1 고리가 남았다. 보강안은 actor HiddenInGame을 별도 저장·복구해 native 컴포넌트 visibility와 분리한다. 실제 숨김 결과는 refined30에서 확인했다.
- 기존 helper를 runpy로 재사용해 검증된 카메라 방향 strip, collision-free 임시 plane, 속성 설정→Activate→emitter mask 순서를 유지한다. 추가 시각 광침을 실제 발수/피해로 설명하지 않고 기존 native 착탄의 활성 surface emitter를 확인한다. 생성 수나 helper AST 통과는 실제 렌더/미적 수용 근거가 아니다.
- V 비교는 소유 preview6재질만 저장하고 운영2표면은 그대로 둔 채 시안 중 슬롯만 임시 교체한다. 원본 hash·두 슬롯 복구·임시 actor 정리를 현재 실행 결과로 검증해야 한다. W/S는 asset save가 없는 범위다. ‘시안 미적용’과 ‘선택용 preview 에셋 저장’은 함께 성립하므로 구분해서 보고한다.
- 현재 근거: handoff §37, sparrow-signature-20261023/result.json. 이동기 mobility30의812/mobility60의593 및 실제 대표 화면·3빌드가 통과했다. concepts-first30 전체79검사는 S1 live particles0에서 실패했다. V2의13검사/실제 영상만 재사용하고 수정8개는 refined30의94검사와 실제 화면 비교를 통과했다.11영상 전체 디코딩·브라우저 실제 재생·정리도 완료했다. 번호형PNG1,598개/3,010,321,892바이트만 삭제하고 대표51장·총229파일 누락0 및33미디어 hash 불변을 확인했다. 삭제예정 잔여0/실패0이다. 기능 완료 기록과 미적 채택을 구분하며, 사용자의 새 Countess 전면 품질 반려는 기존 §36의 기능·빌드 사실을 지우지 않고 현재 진행 중인 countess-quality-20261023 작업으로 잇는다.


## 34. Countess 품질 재반려 대응 · 실제 renderer 감사 · 표면과 소멸 분리

- 기능 통과·컴파일 성공·전달 완료는 사용자의 외형 반려를 무효화하지 않는다. 같은 카메라 실제 장면에서 검은 몸체/좁은 날/접촉 파열/동작 주체를 따로 보고 실패한 판·점무늬·공허한 외곽을 기록한다. countess-quality-20261023/visual-review.md에는 첫 보강에서 A/S가 너무 약해져 다시 반려된 이력도 남겼다.
- mesh 이름·삼각형 수만으로 입체감을 판단하지 않는다. E의 원본 crater는 둥근 구멍, 첫 owned fracture는 방사형 부채처럼 읽혔다. 최종7개 짧은 비정형 rock은 상면 중심을 비틀고 아래를 매립해 바닥과 연결했다. actor 몸체용 lit 표면과 clone 소멸용 alpha/WPO는 별도로 소유한다. 수명 끝의 tip/noise 침식을 쓰되 source pack graph는 보존한다.
- PSC is_active와 실제 살아 있는 입자·renderer는 다르다. get_num_active_particles와 SparrowQA.State의 template/LOD/render_emitters/materials를 함께 기록한다. S의 첫 약한 화면은 nullptr가 아니라 캡처 사이에 낀 짧은 burst였다. V의 남은 점띠도 WaterMasked 교체로 해결되지 않았으며 실제 BlackSparks/RedSparks672~1008개/layer가 주원인이었다.6layer에서 두 emitter를 매 Activate 뒤 꺼 연기·SpiralArm448입자와 중앙 사건을 남겼다.
- 소유 visual actor만 감사하지 않는다. R/D/S 점판은 actor용 복제 burst를 정리해도 남았다. 세계 전체 receipt에서 별도로 살아 있던 원본 p_CountessUltImpact677입자를 확인했고 공통 ApplyPointDamage 후 SpawnOwnedEffect 경로를 찾았다. source를 수정하지 않고 해당 PSC에서8개 방해층을 끈 뒤 실제 화면과6층 renderer를 확인했다. 생성 개수 감소만으로 성능 향상을 확정하지 않는다.
- 실제 칼 AnimTrail이2~3샘플이고 보간이 꺼지면 빠른 회전에서 ㄱ자로 꺾인다. A/V는 unrelated Q 정적 궤적 보강판을 제거하고 private source trail의 PreviousTangentRecalculation과 Distance12cm/Tangent10도/Width8cm 보간으로 실제 소켓 궤적을 살렸다. body포즈·피해·공전 타이밍은 보존했다.
- 지속 변신 표면과 이동 잔상은 사용 플래그/수명이 다르다. F/Space의 회색 머리는 새 material의 Clothing usage 누락으로 실제 로그에서 확인됐다. S 본체는 lit/mask1/WPO0, 두 mantle만 찢어진 mask/약3.4cm normal ripple을 쓰며24초 만료에 원래 재질·section을 복원한다. 원본 shader 이름만으로 dither가 원인이라고 단정하지 않는다.
- Unreal Python ObjectIterator(unreal.Object)에는 class도 포함되어 item.get_path_name()가 static 호출 오류를 낼 수 있다. 기존 SystemLibrary.get_path_name(item)을 사용한다. ParticleModuleMeshMaterial의 snake_case mesh_materials는 이 환경에서 미노출이므로 실제 반사명 MeshMaterials를 사용한다. Public EditAnywhere 확인은 Python alias 존재의 증거가 아니다. OBJ export는 main 외 _Internal/_UV1 sidecar가 생길 수 있어 정확한 파일명도 정리한다.
- 원본 source/수용된 V PP hash를 전후 비교한다. 광량 전체를 누르는 암전 대신 매프레임 field의 화면 좌표와 부드러운 타원 feather로 중앙을 보존하고, EndPlay에서 PP component를 제거한다. 실제 최종0130 정상 밝기와60fps owner 전환/연속사용을 함께 확인했다.
- 최종 근거: handoff §38, countess-quality-20261023/result.json. Q/F/Space52개 재사용 + impact-final30 전체121 + recovery-final60 전체164다. 실제9영상/18스트림 전체 디코딩·브라우저9개 재생·확대/반속 통과. 임시번호PNG2,136개와OBJ sidecar2개 총3,787,870,037bytes를 정리하고99대표·358보존파일 누락0/미디어27파일hash변경0을 확인했다. 전체 원시프레임은 남지 않는다.

## 35. 실제 레퍼런스 형상 · 침식 표면 · 새 사격 경로 검증

- 레퍼런스의 시각 주체를 먼저 확인한다. Sparrow D 7:05의 붉은 큰 중앙 물체는 적/표적이고 새 소환물이 아니다. 실제 공격은 가느다란 황금 관통선과 작은 별타격이다. A1:42는 앞 chapter 끝이며 애로우해일 표기가 나오는1:47.5~1:49가 실제 파동이다. Shorts seeking은30fps, 일부 일반영상은60fps여서 프레임전진 수를 동일하게 잡으면 다른 장면을 찍는다.
- 메시가 존재한다고 면이 읽히는 것은 아니다. Countess RuptureCup 중심이 지면 아래 들어가면 테두리만 남고, 이를 높이기만 하면 검은 컵/벽이 된다. 중심/상승질감은 유지하면서 외곽 높이와 opacity/침식을 별도로 조절한다. D 손은 lit 광택보다 소유 unlit 반투명 잉크 재질이 유령손을 명확히 표현했다. A/V처럼 곡면이 겹치는 경우 검은 면을 지우지 말고 독립 흐름 재질의 내부/날/침식을 나눠 본다.
- Sparrow A의 spline 단면이 얇으면 실제 쿼터뷰에서 큰 C선만 남는다. 반경을 키우기보다 기존 반경 안에서 단면과 짧은 후류를 보강한다. S의 짧은 팬사격에는 활 앞 압축핵이 선과 화살을 한 번의 방출로 묶어 준다. 이때 전체화면 flash/대형 원형층은 불필요하다.
- UE MaterialEditingLibrary의 TextureSample 좌표 입력 이름은 이번5.8 환경에서 UVs다. 연결 결과 bool을 확인한다. material 안의 모든 Custom 노드를 이름으로 세면 연결되지 않은 보존 노드까지 잡힌다. 기존 재질 수정은 실제 Emissive/Opacity/WPO 출력에서 연결 그래프를 거슬러 올라가 대상을 선택한다.
- Python 호출 가능 여부는 C++ public 여부와 다르다. CancelSkill/GetSlotCooldownRemaining은 이번 클래스에서 UFUNCTION이 아니므로 Python 메서드가 없다. 기존 SparrowSanctuaryQA.Cancel을 사용하고, 쿨다운은 실제 같은키 재입력의 거절+GetInputFeedback=Cooldown으로 검증했다. 새 테스트를 위해 게임 API를 불필요하게 노출하지 않는다.
- 새S는 프레임마다 age threshold를 while로 통과시키고 파동마다 shared hit set을 갖는다.27발이 모두 같은 적에 중복 피해를 주지 않으며 파동간 피해는 독립이다. 취소 전 future wave 제거/owner전환/벽/쿨다운·V변신뒤Space·실제평타/이동 복귀를 짧은 실제입력으로 확인한다. 관련없는 통과 suite는 반복하지 않는다.
- 최종 영상은 WebM우선/MP4대체로 실제 브라우저 재생을 확인하고 그 뒤 번호형 원시PNG만 정확한 목록으로 지운다. manifest가 가리키는 numbered poster도 보존 목록에 추가해야 한다. 폴더 재귀 삭제 대신 최종 절대 경로·파일형식·reparse 여부를 확인하고 LiteralPath로 삭제한다.


## 36. 같은 형상 보정의 한계 · 독립 반려와 시각 재질 사용 플래그

- 컵처럼 읽히는 외벽을 높이/투명도로만 낮춰도 같은 구조 인상이 남는다. E/R에서 컵 생성을 제거한 뒤 E는 중앙의 열린 상승면, R은 서로 다른 높이/짧은 파열과 순차 소멸로 사건을 구분했다. 첫 E의 밝고 균일한 5곡선도 꽃잎처럼 보여 반려했고, 짧은 3검격과 비대칭 중앙 crest로 교체했다. 단순 광량·반경 확대는 채택 기준이 아니다.
- 분신의 큰 검격만 밝히면 몸보다 띠가 주체가 된다. A/V는 분신의 연속된 어두운 몸과 좁은 능선을 먼저 살리고, 짧은164도 침식 절삭면을 연결했다. 쿼터뷰에서 Pitch19/38/57+Roll24는 검격이 옆면으로 보이는 시점이 있었다. 경사12~24와 서로 다른 교차 경로로 해결했고 전체 폭풍/암전 확대는 하지 않았다.
- 새 skeletal 재질도 Clothing usage가 별도로 필요하다. pass2 V 회색 머리는 실제 `M_CountessStrikeShadow missing usage flag Clothing!` 로그로 확인했다. 전용 재질에 두 usage를 저장/조회해 검증하고 같은 화면을 재촬영했다. 표면·메시 버전은 분리해 사용 플래그 수정으로 이미 채택한 절삭면을 재저작하지 않는다.
- 재질 그래프 재구성 중 잠시 생긴 missing-input 경고와 저장된 shader의 런타임 실패를 구분한다. 저작의 연결 bool/최종 recompile 결과를 확인하고, 저작을 재실행하지 않은 마지막 실제 게임에서 material compile/usage 경고가 없어야 한다.
- 독립 검토는 기능 통과를 따라 채택하지 않는다. pass1 기능102통과 뒤 E/A/V는 외형 반려, pass2는 V 머리 문제만 보류, pass3에서 E/A/V를 채택했다. Q/F/Space는 역할에 맞는 가독성이 있어 수정하지 않았다. 실제 기준은 `countess-quality-gate-20261024/review-criteria.md`와 단계별 audit에 있고 사용자 최종 취향 승인을 대신하지 않는다.
- 근거: handoff §40, 최종6영상/12스트림 및 browser-verification.json, recovery60 54검사, cleanup-result.json. 영상 검증 후 번호형PNG1090개 약1.87GB를 정리했고 최종 미디어/대표/검증 근거는 보존했다.
