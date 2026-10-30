#include "GideonSkillComponent.h"

#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/DecalComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/OverlapResult.h"
#include "Components/SplineMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "Camera/PlayerCameraManager.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "KwangTrainingDummy.h"
#include "NavigationSystem.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "TimerManager.h"
#include "TopDownCombatCharacter.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	TAutoConsoleVariable<int32> CVarGideonIgnoreCooldowns(
		TEXT("Gideon.Skills.IgnoreCooldowns"), 1,
		TEXT("Testing: 1 (default) lets Gideon skills ignore cooldowns. Set 0 to restore cooldowns."));
	// F 번개 시안(10-19): 1~4 녹스 단색(「녹스 푸른·노란 번개, 망각의 지팡이 초록, 데스레이」), 5~8 녹스 경로 + 파라곤 재료
	// (「톤이 다르다 — 파라곤 에셋 재조립」). 8번으로 정했고(gideon-21st-c-20261019-011506/F_파라곤시안표.png),
	// 「다시 바꿀 수도 있으니 지우지 말고 둬」(10-19)로 나머지도 남긴다 — 콘솔 Gideon.Skills.FStyle 1~8로 바로 볼 수 있다.
	// 8은 「그림을 떼다 붙인 것 같다, 톤도 안 맞다」(10-19) → 녹스 녹화(사용자 C:/Users/USER/Videos/Captures/녹스푸른번개.mp4)를 재서 만든 9가 기본.
	// 9 다음 「원본을 써먹어볼까?」 시안 F1(gideon-rf-drafts-20261019-185647/F_원본번개_시안.mp4) → 「일단 F1로 가자」(10-19)로 10이 기본.
	// 10-20 「한 명 타겟이 잘 안 느껴짐 — 집중되는 이펙트 + 권장한 것 다 취합」 → 11(모았다가 한 방). 같은 날 시안 11~15
	// (gideon-35th-fdraft-20261020-113151/F_시안표.png)에서 「F14로 해줘」 → 14(작은 블랙홀이 접히며 터짐)가 기본.
	TAutoConsoleVariable<int32> CVarGideonFStyle(TEXT("Gideon.Skills.FStyle"), 14,
		TEXT("Draft for F: 1 blue Lightning, 2 yellow Energy Bolt, 3 green bolt (Staff of Oblivion), 4 Death Ray (Nox flat), ")
		TEXT("5 Paragon beams on the Nox path, 6 = 5 + purple discharge strip, 7 Paragon bolt-material strips, 8 = 7 main strip + 5 side beams, ")
		TEXT("9 soft-glow strips matched to the Nox recording, 10 Kwang ultimate lightning (red swirl hidden) striking the target every 0.5s, ")
		TEXT("11 one target: 1s of purple light gathering on it with a spinning ring at its feet, then one bolt for the whole damage, ")
		TEXT("12 = 11 with a Prime Helix gather and Kwang light strike + stasis shockwave, 13 = 12 gather with a 1.2x Kwang bolt + Dekker sky-beam burst, ")
		TEXT("14 (default) a small black hole on the target swallowing spiralling light then collapsing into a shockwave, 15 three 1x bolts in a row on one spot."));
	// A 자리에 넣을 새 스킬 러프 시안(10-20 「A 빼고 새 스킬 — 시안 몇 개 러프하게라도 만들어서 보여 줘」). 0 = 지금 A(Burden).
	// 1차 표(gideon-41st-anew-*)에서 「A1·A4는 별로, A2·A3는 두고 시안 더」 → 1·4를 빼고 5~7을 더했다.
	// 10-20 「A스킬 그대로던데」: 콘솔을 안 쳐도 A가 광선이 되게 기본을 7로. 원래 Burden은 0.
	// 같은 날 「저렇게 자기 맘대로 쏘는 게 아니라 타겟팅 지정해서 계속 쏘는 거」 → 8(찍은 대상에 광선을 붙잡음)이 기본.
	// 8은 10-21 한 발 광선 → 도우미(평타마다 한 발 광선을 쏴 주는 빛 구슬)로 바뀌었다(ExecuteNewSkillDraft case 8).
	TAutoConsoleVariable<int32> CVarGideonANew(TEXT("Gideon.Skills.ANew"), 8,
		TEXT("Rough draft for a new skill on A: 0 current Burden, ")
		TEXT("2 orbiting stars (3 stars circle Gideon for 4s and hit what they touch), 3 chain star (a bolt hops between up to 3 enemies), ")
		TEXT("5 split comet (bursts on the first enemy into 8 star shards), 6 pulling star (drags the struck enemy to Gideon on a tether), ")
		TEXT("7 sweeping beam (a purple beam sweeps across the front), 8 (default) helper orb (floats by Gideon and fires a thin beam on every basic attack). ")
		TEXT("1 and 4 were dropped."));
	// D 바닥 자국 시안(10-20 「방향은 맞는데 바닥 이펙트가 좀 아쉬움 — 시안 좀」). 시안표 gideon-36th-dmark-20261020-122359에서
	// 「D4로 가자」 → 4가 기본. 2·3(룬·별 무늬)은 안 보이거나 원판으로 뭉개져 표에서 뺐다.
	TAutoConsoleVariable<int32> CVarGideonDMark(TEXT("Gideon.Skills.DMark"), 4,
		TEXT("Draft for the D ground mark: 0 dark purple scorch, 1 glowing scorch (bright purple rim), 2 rune pattern, 3 star pattern, ")
		TEXT("4 (default) = 0 with embers drifting up from each mark."));
	// D 보강 시안(10-20 「진짜 딱 2% 정도 아쉬운데 이펙트 더 보강할 수는 없을까」). 새 물체 없이 있는 것(꼬리·부딪힘·큰 유성)만 키운다.
	TAutoConsoleVariable<int32> CVarGideonDBoost(TEXT("Gideon.Skills.DBoost"), 0,
		TEXT("Draft for strengthening D: 0 (default) as now, 1 each impact pops a flash and flings sparks, 2 the trail sheds twinkling star dust, ")
		TEXT("3 the last big meteor lands harder (bigger burst, flash, a ring of sparks along the floor), 4 = 1 + 2 + 3."));
	// V 블랙홀 일렁이는 빛 시안(10-19 「마법진은 거대한데 블랙홀 공 하나라 썰렁 — R1 일렁거리는 빛을 지속시키면」).
	// 시안표 gideon-26th-vglow-20261019-222006/V_일렁빛시안표.png에서 2번(「적용해줘」 10-19)이 기본.
	// 10-20 「일렁임이 블랙홀로 빨려 드는 느낌」 시도(일렁임 줄이기·효과 기준 좌표 사본·빨려 드는 빛 점·빛 점 소용돌이 시안 5)는
	// 「V는 그냥 롤백」(10-20)으로 모두 뺐다. 일렁임은 크기 조절을 안 받는 이펙트였다(gideon-36th-vsplit-*). 블랙홀이 열릴 때 번개는 남김.
	TAutoConsoleVariable<int32> CVarGideonVGlow(TEXT("Gideon.Skills.VGlow"), 2,
		TEXT("Draft for the V glow: 0 none, 1 purple shimmer (Prime Helix shockwave) 0.45x slowed from 0.15s, 2 = 1 at 0.6x, ")
		TEXT("3 = 1 slowed from 0.25s, 4 = 1 starting 0.8s after the black hole opens."));
	// E 포털 이펙트의 정면 축과 액터 앞축(X)의 차이. 렌더로 정한다.
	constexpr float TornSpacePortalYawOffset = 0.0f;
	// W 룬 글자 고리 반지름 ÷ 균열 반경. 바깥 테두리 겹원(반경 그대로) 안쪽에 들어가게 줄인다.
	constexpr float RiftRuneGlyphFraction = 0.8f;
	// W 가운데 삼각 마법진 반지름 ÷ 균열 반경, 마법진 층이 도는 기준 속도(도/초).
	constexpr float RiftRuneCenterFraction = 0.5f;
	constexpr float RiftRuneSpinDegrees = 12.0f;
	// W 룬 원판(점선 고리 자리, 「점선 마법진 아쉽고 심심」 10-18 → 시안 1번 선택) 크기(반경 대비)와 진하기 배수.
	// 진하기: 0.25배로 바깥 고리와 밝기를 맞췄으나(gideon-18th-f-20261018-181538) 「전이 더 낫다」(10-18)로 1.4배로 되돌림.
	constexpr float RiftRuneDenseFraction = 0.62f;
	constexpr float RiftRuneDenseOpacity = 1.4f;
	// 룬 원판은 두께가 거의 없어 바닥 가까이선 재질의 깊이 페이드로 안 보인다(gideon-17th-20261018-171004 w1·w2). 이만큼 띄운다.
	constexpr float RiftRuneDenseLift = 25.0f;
	// W 마법진이 줄어들며 사라지는 시간.
	constexpr float RiftRuneFadeSeconds = 0.25f;
	// E로 건너간 뒤 두 포털을 열어 두었다가 함께 닫기까지의 시간.
	constexpr float TornSpaceExitLinger = 0.5f;
	// E 포털을 지우기 전에 닫힘 이펙트와 겹쳐 두는 시간.
	constexpr float TornSpaceCloseOverlap = 0.15f;
	// V가 끝날 때 블랙홀이 한 점으로 접히는 시간과 접힌 끝 크기. 마법진도 같은 시간에 가운데로 빨려 들어간다(10-18 「폭발 말고 다 빨려 들어가듯」).
	constexpr float BlackHoleShrinkSeconds = 0.6f;
	constexpr float BlackHoleShrinkScale = 0.05f;
	// V: 마법진 반경·진하기, 마법진이 깔린 뒤 블랙홀이 열리기까지(10-18 「마법진 이후에 스킬이」).
	// V: 시작에 까는 봉인 마법진(P_Gideon_Ultimate_Cast — 「그전께 훨씬 좋았는데」 10-18, gideon-12th-v0 v_drafts 맨 위 줄) 배율,
	// 마법진이 다 펼쳐진 뒤 블랙홀이 열리기까지(마법진은 약 0.6초에 다 서고 1.3초쯤 사라진다 — 같은 사진).
	constexpr float BlackHoleSealScale = 0.8f;
	// 10-20 「V는 한 1/3 정도 더 키울 수 있나」 → 4/3 → 「너무 과한가? 니 생각은?」 비교표 gideon-49th-vsize-*(4/3은 마법진이 화면 밖으로 잘리고
	// 마지막 폭발이 화면 2/3를 덮음) → 「니 권장대로」 1.15. 마법진·블랙홀(높이 포함)·일렁이는 빛·번개·마지막 폭발·빛 점·범위(BlackHoleRadius)에 모두 곱한다.
	constexpr float BlackHoleSize = 1.15f;
	// 10-20 「V는 시전 시간을 좀 길게」 → 0.7 → 1.4초(누른 뒤 블랙홀까지 1.2 → 1.9초). 마법진은 그동안 BlackHoleSealSlow 배속으로 펼쳐져
	// 블랙홀이 열릴 때 예전과 같은 장면(다 펼쳐진 직후)이 되고, 열리면 제 속도로 돌아간다.
	constexpr float BlackHoleIntroSeconds = 1.4f;
	constexpr float BlackHoleSealSlow = 0.7f / BlackHoleIntroSeconds;
	// 블랙홀이 열린 뒤에도 마법진을 남겨 두는 시간(그 전에 스스로 사라지면 효과 쪽이 먼저 끝난다).
	constexpr float BlackHoleSealLinger = 1.0f;
	// V 일렁이는 빛 시안(CVarGideonVGlow 1~4): 배율, 터진 뒤 느리게 바꾸는 시점, 블랙홀이 열린 뒤 띄우기까지.
	// 원래 0.5초 안에 사라지는 한 번 터짐(R 시안 R1)이라 일렁이는 구간에서 재생을 느리게 해 블랙홀 동안 끈다. 접히기 시작하면 원래 속도로 돌려 같이 사라진다.
	struct FBlackHoleGlowDraft
	{
		float Scale;
		float SlowAfter;
		float Delay;
	};
	constexpr FBlackHoleGlowDraft BlackHoleGlowDrafts[4] = { { 0.45f, 0.15f, 0.0f }, { 0.6f, 0.15f, 0.0f }, { 0.45f, 0.25f, 0.0f }, { 0.45f, 0.15f, 0.8f } };
	constexpr float BlackHoleGlowDilation = 0.06f;
	// 소용돌이로 빨려 드는 빛 점이 도는 빠르기(도/초). F 14 작은 블랙홀에 쓴다.
	constexpr float SpiralDotSwirl = 150.0f;
	// 블랙홀이 열릴 때부터 접히기 직전까지 내리치는 번개: 간격·첫 가운데 번개 배율(나머지는 0.55~0.8배, 마법진 안 아무 자리).
	// 처음엔 0.15초 간격 세 번이었으나 「터지기 직전까지 계속 — 위압감 있게」(10-20)로 끝까지 0.3초마다(약 10번).
	// 같은 날 「번개가 가운데 집중되게」 → 내리치는 자리를 마법진 반경의 0.15~0.8배 → 0~BlackHoleBoltSpread배, 크기 0.55~0.8 → 0.7~1배.
	// 10-21 「번개 이펙트(터질 때 말고) 너무 과한 것 같은데 2~30% 정도만 줄여」 → 크기 2.5 → 1.875배(25% 줄임). 마지막 폭발 번개(BlackHoleFinalBoltScale)는 그대로.
	constexpr float BlackHoleBoltGap = 0.3f;
	constexpr float BlackHoleBoltSpread = 0.2f;
	constexpr float BlackHoleBoltScale = 1.875f;
	// W 마법진 진하기(1 = 원본).
	constexpr float RiftRuneOpacity = 0.5f;
	// W 운석이 떨어진 자리의 폭발 배율(수정 깨지는 충돌 대신 폭발, 10-18). 10-19 「70% 정도로」 1.2 → 0.84.
	constexpr float RiftBlastScale = 0.84f;
	// F Void Ray: 유지 시간·피해 횟수·사거리·선 폭.
	constexpr float RaySeconds = 2.0f;
	constexpr int32 RayTicks = 10;
	constexpr float RayRange = 1200.0f;
	constexpr float RayWidth = 70.0f;
	// F 10: 원본 번개를 내리치는 간격(시안 F1과 같음).
	constexpr float OriginalBoltInterval = 0.5f;
	// 「좀 잘 보이게」(10-19): 1배는 줄기가 가늘고 맞는 자리 빛이 작아 2배로(짐작, 촬영으로 확인).
	constexpr float OriginalBoltScale = 2.0f;
	// F 10이 커서 둘레에서 꽂을 적을 찾는 반경(10-20 「한 명한테 집중」, 임시값).
	constexpr float BoltLockRadius = 300.0f;
	// F 11: 고정한 적에게 FocusChargeSeconds 동안 보라 빛이 모여들고 발밑 고리가 돈 뒤 번개 한 번(1배 — 2배는 바닥에 넓게 퍼져 범위기처럼 보였다)과
	// 몸 섬광으로 피해 10번어치를 한꺼번에 준다. 시전은 찍은 직후(FocusMoveAfter)에 끝난다(10-21 전엔 번개 뒤 0.35초).
	// 10-20 「스킬 지속시간(이펙트 보여주는 시간) 2배」 → 1 → 2초.
	constexpr float FocusChargeSeconds = 2.0f;
	// F 동작(10-20 「F 애니메이션 너무 어색한데 딴 거 없어?」 → 「손 내미는 거 위주로」 → 시안표 gideon-49th-fanim-* 「F는 1번으로」):
	// 평타 1타(Primary_Attack_A_Medium)로 손을 뻗어 찍는다. 처음엔 손 뻗은 순간(0.173초)에 멈춰 2초 버텼으나 10-21 「몸이 멈춰 있는 게 어색해」로
	// 1타를 끝까지 틀어 모으는 동안은 서 있다가 터질 때 평타 2타로 다시 내지르게 했고, 「시전하고 멈춰 있는 게 아쉬움」 →
	// 「F는 바로 움직일 수 있게 하자」(10-21)로 찍은 뒤 FocusMoveAfter에 시전을 끝낸다(ExecuteFocusBolt가 불리는 0.35초 기준 —
	// 손 뻗기 0.173초 + 평타처럼 잠깐 그 자세). 모이고 터지는 건 그대로 대상에서.
	constexpr float FocusMoveAfter = 0.05f;
	// A 광선 굵기(10-20 「더 얇게」 → 굵기 시안 gideon-50th-athin-*(0.65·0.43·0.26배) → 「제일 얇은 것보다 더 얇게」): 띠 굵기 70 × 0.15 ≈ 10cm,
	// 양 끝 빛덩이 0.4배, 흰 심 날카로움 10 → 2. 흰 심은 띠 폭의 1 − 0.5^(1/날카로움)만 밝아 가늘게 하면 1픽셀 아래로 내려가 점선처럼
	// 끊기므로(A 광선 9 교훈, 계단 현상 방지 꺼짐) 날카로움을 같이 낮춰 흰 심을 약 3cm로 둔다(10cm × 29%).
	constexpr float LockBeamWidth = 0.15f;
	constexpr float LockBeamFlare = 0.4f;
	constexpr float LockBeamCoreSharpness = 2.0f;
	// 같은 날 「이펙트가 너무 밋밋해졌다」 → 번개 1 → 2배(고정·고리가 생겨 넓어도 한 명으로 읽힌다) + 몸에 W 폭발(RiftBlast) +
	// 모이는 점·고리·튀는 점을 늘리고 키움.
	constexpr float FocusBoltScale = 2.0f;
	constexpr float FocusFlashScale = 2.5f;
	constexpr float FocusBlastScale = 0.6f;
	// 모여드는 빛 점: 껍질 반경·한 번(0.05초)에 몇 개·수명(가운데에 닿으며 사라짐)·크기(cm).
	constexpr float FocusGatherRadius = 190.0f;
	constexpr int32 FocusGatherPerStep = 6;
	// F 14 몸 둘레를 돌며 빨려 드는 점(「벚꽃처럼 흔들리며 도는 거 두 배쯤」 10-20 → 6 → 12개/0.05초).
	constexpr int32 FocusSpiralPerStep = 12;
	// 그 점들이 둘레를 돌다 끝에 몰아서 빨려 드는 정도(반지름 1 − t^이 값 — 클수록 터지기 직전에 한꺼번에 모인다).
	// 10-20 「모이는 게 좀 더 확실하게 보였으면」 → 6 → 9(끝까지 더 넓게 돌다가 더 짧게 몰려듦) + 도는 반경 190 → 260·점 크기 24 → 36.
	// 같은 날 「불빛의 크기를 절반으로」 → 빛 점 크기(도는 점 36 → 18, 모이는·튀는 점 24 → 12, 발밑 고리 20 → 10)를 모두 반으로.
	constexpr float FocusSpiralPull = 9.0f;
	constexpr float FocusSpiralRadius = 260.0f;
	constexpr float FocusSpiralSize = 18.0f;
	constexpr float FocusGatherLife = 0.3f;
	constexpr float FocusGatherSize = 12.0f;
	// 발밑 고리: 반경·점 수·도는 빠르기(도/초)·점 수명·크기. 남은 점이 작아지며 꼬리처럼 끌린다.
	// 10-20 「발밑에 불빛 모이는 거 원 더 작게」 → 95 → 60.
	constexpr float FocusRingRadius = 60.0f;
	constexpr int32 FocusRingDots = 20;
	constexpr float FocusRingSpin = 240.0f;
	constexpr float FocusRingLife = 0.4f;
	constexpr float FocusRingSize = 10.0f;
	// 번개 순간 몸에서 바깥으로 튀는 빛 점 수·빠르기.
	constexpr int32 FocusBurstDots = 40;
	constexpr float FocusBurstSpeed = 650.0f;
	// F 15 연속 낙뢰 간격, F 14 대상 몸에 띄우는 작은 블랙홀 배율.
	// 10-20 「F는 이펙트 약간만 더 줄이고」 → F 14의 블랙홀·충격파·폭발을 0.8배(F14Shrink). 블랙홀 0.22 → 0.176.
	constexpr float FocusStrikeGap = 0.12f;
	constexpr float F14Shrink = 0.8f;
	// 10-20 「반딧불 같은 게 주변을 빙글거리며 도는 게 아니라 오브젝트로 모였다가 한 번에 쾅 하고 폭발」 → F 14: 도는 점(FocusSpiral*) 대신
	// 껍질(반경 FocusInflowRadius)에서 곧장 물체로 날아가 닿으며 사라지는 점(한 번에 몇 개·수명·크기), 물체(작은 블랙홀)는 모으는 동안
	// FocusGrowFrom배에서 원래 크기로 커지고, 터질 때 섬광·폭발 F14Burst배·튀는 점 FocusBurstDots → F14BurstDots개·빠르기 F14BurstSpeed.
	constexpr float FocusInflowRadius = 260.0f;
	constexpr int32 FocusInflowPerStep = 10;
	constexpr float FocusInflowLifeMin = 0.45f;
	constexpr float FocusInflowLifeMax = 0.75f;
	constexpr float FocusInflowSize = 18.0f;
	constexpr float FocusGrowFrom = 0.4f;
	constexpr float F14Burst = 1.3f;
	constexpr int32 F14BurstDots = 70;
	constexpr float F14BurstSpeed = 900.0f;
	constexpr float FocusVoidScale = 0.22f * F14Shrink;
	// F 11~15 시안 한 벌의 그림(ExecuteFocusBolt). 기본값 = 11. 이펙트는 시안마다 함수 안에서 채운다.
	struct FFocusLook
	{
		UParticleSystem* Charge = nullptr;
		float ChargeScale = 1.0f;
		float ChargeAt = 0.0f;
		bool bStraightDots = true;
		bool bSpiralDots = false;
		// 둘레에서 곧장 물체로 빨려 드는 점(FocusInflow*)·모으는 동안 물체가 커짐(FocusGrowFrom → 1).
		bool bInflowDots = false;
		bool bGrowCharge = false;
		bool bRing = true;
		bool bCollapseCharge = false;
		UParticleSystem* Bolt = nullptr;
		float BoltScale = FocusBoltScale;
		float BoltAt = FocusChargeSeconds;
		int32 Strikes = 1;
		UParticleSystem* Flash = nullptr;
		float FlashScale = FocusFlashScale;
		UParticleSystem* Blast = nullptr;
		float BlastScale = FocusBlastScale;
		int32 BurstDots = FocusBurstDots;
		float BurstSpeed = FocusBurstSpeed;
	};
	// 둥근 빛 점(D 유성 꼬리·F 11) 색·밝기. 재질은 F 시안 9의 카메라를 향한 둥근 빛 판(M_NoxSpark).
	const FColor GlowDotColor(200, 130, 255);
	constexpr float GlowDotIntensity = 4.0f;
	// F 녹스 번개(10-19): 녹스 클라가 번개를 긋는 방식을 옮겼다(Nox_Origin/third_party/opennox-src/src/legacy/client__draw__lightning.c,
	// 색은 GAME3_1.c nox_xxx_prepareLightningEffects_4BAB30, 데스레이는 spell_death_ray.go clientFXDeathRay).
	// 녹스: 두 끝 사이를 반씩 나누며 가운데를 화면 가로·세로로 따로 흔든다. 흔들 폭 = 줄 길이 512px 이상이면 100px, 아니면 15 + 길이×85/512,
	// 단계마다 10/16배. 단계 수는 길이로 5~8(조각 2^(단계-1)). 파랑·초록 = 흐린 곁가지 둘(굵기 3px·옅게) + 빛무리(12px) 두른 본줄기(1px 흰 심),
	// 노랑 = 곁가지 없이 굵기가 출렁이는 본줄기 하나(남은 수명 값으로 굵기를 정함). 매 화면 새로 그린다.
	// 녹스 1px ≈ 이 게임 4cm로 잡았다(녹스 640폭 화면 ↔ 이 쿼터뷰 화면 대비 짐작 — 화면에서 맞출 것). 조각은 32개로 줄였다(녹스 128).
	constexpr float NoxPixel = 4.0f;
	constexpr int32 NoxMaxDepth = 6;
	constexpr float NoxRefreshSeconds = 0.05f;
	// 줄 굵기(cm)·밝기: 흰 심, 빛무리, 곁가지, 불티. 빛무리 45·0.35는 굵은 관처럼 보였고 불티 3은 하얗게 넘쳤다(gideon-20th-20261019-002041).
	constexpr float NoxCoreWidth = 6.0f;
	constexpr float NoxCoreIntensity = 3.0f;
	constexpr float NoxGlowWidth = 30.0f;
	constexpr float NoxGlowIntensity = 0.12f;
	constexpr float NoxSideWidth = 10.0f;
	constexpr float NoxSideIntensity = 0.5f;
	constexpr float NoxSparkIntensity = 1.2f;
	// 노랑 심 굵기 출렁임: 최소·최대·한 번 줄어드는 시간. 6~30은 밧줄처럼 굵었다(같은 촬영).
	constexpr float NoxPulseMin = 4.0f;
	constexpr float NoxPulseMax = 16.0f;
	constexpr float NoxPulseSeconds = 0.3f;
	// 두 끝에 튀는 불티(녹스 BlueSpark·YellowSpark·GreenSpark): 한 번에 몇 개, 수명, 흩어지는 빠르기, 크기.
	constexpr int32 NoxEndSparks = 3;
	constexpr float NoxEndSparkLife = 0.25f;
	constexpr float NoxEndSparkSpeed = 250.0f;
	constexpr float NoxEndSparkSize = 7.0f;
	// 데스레이: 시전자→목표 일직선에 보라 불티를 녹스 2px마다 깔고, 불티는 0.67~1.33초(녹스 20~40화면) 위아래로 흔들리며 사라진다.
	// 녹스에선 한 번 쏘는 주문이라 F 동안 이 간격으로 다시 쏜다.
	constexpr float DeathRayInterval = 0.3f;
	constexpr float DeathRaySparkSize = 9.0f;
	constexpr float DeathRayLifeMin = 0.67f;
	constexpr float DeathRayLifeMax = 1.33f;
	constexpr float DeathRayDrift = 60.0f;
	constexpr float DeathRayLift = 15.0f;
	// 두 손 사이에서 앞으로 띄울 거리.
	constexpr float RayHandAhead = 15.0f;
	// 파라곤 시안(5~7, 「녹스 느낌을 목표로 파라곤 에셋을 다시 조립」 10-19): 녹스 경로는 그대로 두고 그리기만 파라곤 것으로.
	// 띠에 입혀 쓸 만한 파라곤 재질은 콰앙 번개(3번)·방전(6번)뿐이었다(재질 8개 촬영 gideon-21st-mats-b-20261019-010709).
	// 조각 수(콰앙 광선은 한 조각이 입자 하나라 줄인다), 다시 긋는 간격, 광선 하나가 보이는 시간(0.12초쯤 차오르고 0.5초 전에 진다 —
	// gideon-bolt-cands-20261018-174553), 본줄기·곁가지 광선 배율, 방전 띠·번개 띠 굵기, 손·맞은 자리 불꽃 간격·배율.
	constexpr int32 NoxParagonDepth = 4;
	constexpr int32 NoxParagonEvery = 2;
	constexpr float NoxBeamSeconds = 0.3f;
	constexpr float NoxBeamMainScale = 1.6f;
	constexpr float NoxBeamSideScale = 0.9f;
	constexpr float NoxDischargeWidth = 40.0f;
	constexpr float NoxBoltStripWidth = 14.0f;
	constexpr float NoxBoltStripSideWidth = 7.0f;
	constexpr int32 NoxParagonSparkEvery = 3;
	constexpr float NoxParagonArcScale = 0.6f;
	constexpr float NoxParagonFlashScale = 0.8f;
	// 시안 9(녹화 대조, 10-19): 녹스 녹화 b_009(1280×960)를 잼 — 흰 심 굵기 가운데값 1px(상위 10% 3px), 심 + 파란 빛무리 7px(14px),
	// 줄 길이 303px에 옆으로 벌어진 폭 114px(0.38배), 둘레에 작은 파란 불티. 이 게임 화면 1px ≈ 1.2cm(번개 600cm ≈ 500px)로 옮긴다.
	// 띠 너비(재질이 가운데 밝고 가장자리로 꺼지므로 보이는 굵기보다 넓게), 심 날카로움(클수록 가는 심), 세기.
	constexpr float NoxSoftMainWidth = 40.0f;
	constexpr float NoxSoftBloomWidth = 110.0f;
	constexpr float NoxSoftSideWidth = 18.0f;
	// 1차(날카로움 8, 불티 9cm·흰색, 두 끝 빛덩이 45·60) 녹화 대조: 심이 녹스보다 굵고 불티는 흰 점, 두 끝 빛덩이는 안 보임
	// (gideon-22nd-20261019-090517/F_9번_녹스대조.png) → 심을 가늘게, 불티를 크고 파랗게, 빛덩이를 크게(작은 것 하나를 겹쳐 가운데를 밝게).
	constexpr float NoxSoftCoreSharpness = 14.0f;
	constexpr float NoxSoftCoreIntensity = 4.0f;
	constexpr float NoxSoftGlowIntensity = 0.8f;
	constexpr float NoxSoftBloomIntensity = 0.12f;
	constexpr float NoxSoftSideIntensity = 0.9f;
	// 둘레 불티: 한 번 그을 때 몇 개, 줄에서 벗어나는 거리(흔들 폭 대비), 크기·수명, 두 끝 빛덩이 크기.
	constexpr int32 NoxSoftSparkles = 7;
	constexpr float NoxSoftSparkleOffset = 0.4f;
	constexpr float NoxSoftSparkleSize = 18.0f;
	constexpr float NoxSoftSparkleLife = 0.35f;
	constexpr float NoxSoftHandFlare = 90.0f;
	constexpr float NoxSoftTargetFlare = 120.0f;
	constexpr float NoxSoftFlareCore = 0.35f;
	// V 끝: 접힌 블랙홀을 하얀 섬광 → 푸른 충격 고리가 차례로 지운다(「다 포기하기 힘든 이펙트, 겹치지 말고 섞어」 10-18,
	// 시안 표 gideon-19th-b-20261018-220602/V_폭발시안표.png). 배율과 섬광에서 각각 터지기까지.
	// 사이에 있던 콰앙 보라 돔·번개는 뺐다(「V는 빼줘, 번개는 다른 스킬로」 10-19).
	// 같은 날 「폭발이 한 번 두 번 이런데 한 번으로 합쳐」 → 섬광과 고리를 같이 터뜨린다(고리 0.5초 뒤 → 0초).
	// 10-20 「마지막 폭발 훨씬 더 극적이고 강력하게」 → 섬광 1.5 → 2.2, 고리 0.8 → 1.2 + 늦게 퍼지는 둘째 고리·가운데 번개·보라 충격파 구·W 폭발·빛 점.
	constexpr float BlackHoleFlashScale = 2.2f;
	constexpr float BlackHoleRingScale = 1.2f;
	constexpr float BlackHoleSecondRingDelay = 0.18f;
	constexpr float BlackHoleSecondRingScale = 1.8f;
	constexpr float BlackHoleFinalBoltScale = 4.0f;
	constexpr float BlackHoleFinalShockScale = 2.2f;
	constexpr float BlackHoleFinalBlastScale = 2.0f;
	constexpr int32 BlackHoleFinalDots = 60;
	// W 색(보라). 재질 사본의 Tint 값에 곱한다(gideon_fade_assets.py).
	const FLinearColor RiftRuneTint(0.75f, 0.42f, 1.0f, 1.0f);
	// Q 운석: 「그냥 돌이 떨어지는 지점에 마법진을」(10-18) — 하늘 포털 자리 맞추기(화면 위로 잘림·목표 너머)를 그만두고
	// 포털(마법진)을 조준점 바닥에 눕혀 깐다. 운석은 목표 너머 하늘에서 비스듬히 그 안으로 떨어진다: 시작 높이·너머 거리,
	// 바닥 포털 배율·띄움.
	constexpr float BlastMeteorHeight = 1500.0f;
	constexpr float BlastMeteorBeyond = 450.0f;
	// 포털은 0.4초 남짓 열렸다 닫혀(gideon-19th-qcircle-20261018-220648) 0.71초 뒤 떨어지는 운석보다 먼저 사라졌다 → 재생을 늦춰
	// 떨어질 때까지 열어 둔다. 크기는 1배면 폭발(반경 220)보다 한참 작았다(gideon-19th-a-20261018-215241 q).
	// 10-19 운석이 0.5초 늦게 출발해 닿기까지 1.21초 → 0.45배(약 0.9초)로는 모자라 0.3배(약 1.3초)로(짐작, 촬영으로 확인).
	// 같은 날 「Q 왜 이렇게 느려졌지? 다시 빠르게」 → 0.5초 대기를 빼고 0.45배로 되돌림.
	constexpr float BlastPortalScale = 2.0f;
	constexpr float BlastPortalLift = 5.0f;
	constexpr float BlastPortalSlow = 0.45f;
	constexpr float BlastMeteorSpeed = 2200.0f;
	// W·E: 마법진이 다 생긴 뒤 시전·폭발까지 기다리는 시간(「마법진 생긴 이후에 0.5초 정도 딜레이」 10-19, Q는 같은 날 「다시 빠르게」로 뺌).
	constexpr float CircleLeadSeconds = 0.5f;
	// S: 포털 수, 몸 중심에서 포털까지 거리, 이웃 포털 사이 각도, 높이.
	constexpr int32 VolleyPortalCount = 3;
	constexpr float VolleyPortalDistance = 110.0f;
	constexpr float VolleyPortalSpreadDegrees = 50.0f;
	constexpr float VolleyPortalHeight = 30.0f;
	// S: 발 수(포털마다 두 발), 발 간격. 너무 가까이 찍으면 줄들이 몸 앞에서 엇갈리므로 모으는 점을 이만큼은 띄운다.
	constexpr int32 VolleyShots = 6;
	constexpr float VolleyShotInterval = 0.08f;
	// E Star Line(포털 줄 + 바닥 포털 표시로 확정, 10-18): 포털 수·간격·사이 시간·폭발 반경.
	// 폭발은 마지막 포털이 열린 뒤 CircleLeadSeconds부터, 열린 순서(가까운 쪽부터)대로 같은 간격으로(10-19).
	constexpr int32 LinePortals = 5;
	constexpr float LinePortalSpacing = 180.0f;
	constexpr float LinePortalInterval = 0.08f;
	constexpr float LinePortalRadius = 130.0f;
	// E 폭발 배율, 마지막 칸 배수.
	constexpr float LineImpactScale = 0.45f;
	constexpr float LineFinishScale = 1.5f;
	// R 고리 방패(「R은 빼는 게 나으려나 — 다른 스킬들이랑 결이」 10-18 → 감옥 대신 시안): 몸 앞에 보라 포털(E 포털)을 방패로 세워
	// 앞쪽 적을 밀쳐낸다. 지금은 3번을 때리는 적이 없고 캐릭터에 피해를 받는 곳도 없어 피해를 줄이는 효과는 넣지 않았다.
	// 10-19 「공 모양 이펙트 생기고 즉시 이동 가능, 시전하고 거의 즉시 튕겨나게」 → 버티지 않고 포털이 생긴 뒤 WardSeconds에 밀쳐내고
	// 시전도 그 직후 끝낸다(예전 1.6초 버팀). 포털이 생긴 뒤 밀쳐내기까지, 방패 위치(몸 앞 거리·몸 중심 위 높이)·배율,
	// 밀쳐내는 범위(몸에서)·정면 좌우 각도·거리·걸리는 시간·나눠 옮기는 횟수, 터짐 배율.
	// 10-19 터짐을 Muriel 거품 터짐으로(「뭔가 튕겨내는 느낌」 → 시안 R3, gideon-rf-drafts-20261019-185647/R_시안표.png).
	// 같은 날 「밀리는 것도, 이펙트도 너무 과해 — 1/4 수준으로」 → 미는 거리 350 → 87.5, 거품 0.8 → 0.2배.
	constexpr float WardSeconds = 0.12f;
	constexpr float WardAhead = 90.0f;
	constexpr float WardHeight = 20.0f;
	constexpr float WardScale = 1.1f;
	constexpr float WardPushRadius = 380.0f;
	constexpr float WardPushArc = 75.0f;
	// 10-20 「적을 지금보다 3~4배는 더 밀어줘」 → 87.5의 3.5배.
	constexpr float WardPushDistance = 306.0f;
	constexpr float WardPushSeconds = 0.25f;
	constexpr int32 WardPushSteps = 10;
	constexpr float WardPopScale = 0.2f;
	// 거품 터짐의 주황 첫 장면을 숨기는 시간(R 시안 표에서 터진 뒤 0.04초 주황 → 0.11초엔 흰 고리).
	constexpr float WardPopHideSeconds = 0.08f;
	// 거품 터짐 횟수·간격·한 번에 앞으로 나아가는 거리(10-20 「폭발 3번」).
	constexpr int32 WardPops = 3;
	constexpr float WardPopGap = 0.12f;
	constexpr float WardPopStride = 45.0f;
	// 시전자 반동(뒤로 50 밀림, 10-19)은 「밀려나는 건 롤백해줘」(10-20)로 뺐다.
	// D 유성(「유성같이 떨어지고 바닥이나 오브젝트랑 부딪히면 폭발, 디테일 신경써서」 10-18): 작은 유성 수·간격, 떨어지는 자리 흩음 반경과
	// 서로 띄울 거리, 마지막 큰 유성(가운데·기절)까지의 추가 대기. 후보 단독 촬영 gideon-19th-movers-20261018-213101 · bursts-20261018-213139.
	// 10-20 「두 배는 더 많이 날아오게」 → 6개·0.14초 간격을 12개·0.07초로(쏟아지는 시간 0.84초는 그대로). 같은 넓이에 두 배를 흩으므로
	// 띄울 거리는 1/√2(120 → 85).
	constexpr int32 StarSmallCount = 12;
	constexpr float StarInterval = 0.07f;
	constexpr float StarSpread = 300.0f;
	constexpr float StarMinGap = 85.0f;
	constexpr int32 StarSpotTries = 200;
	// 10-20 「지속시간 2배로」 → 같은 간격으로 위 한 바퀴(12개·0.84초)를 두 번(24개·1.68초). 총 피해도 두 배.
	// 같은 날 다시 「지속시간 두 배」 → 2 → 4바퀴(48개·3.36초). 총 피해도 다시 두 배.
	constexpr int32 StarRounds = 4;
	constexpr float StarBigDelay = 0.2f;
	// 비스듬히 떨어지는 길이·연직에서 기운 각도, 화면 가로 대비 깊이 쪽으로 튼 각도(화면 오른쪽 위 → 왼쪽 아래로 긋는다),
	// 유성마다 방향 흔듦, 속도, 부딪힘 판정 반지름. 처음(카메라 반대쪽에서 카메라 쪽으로 38°)은 화면에서 거의 세로로만 떨어져
	// 유성 같지 않았다(gideon-19th-d-20261018-220814).
	constexpr float StarFallLength = 1700.0f;
	constexpr float StarFallTilt = 50.0f;
	constexpr float StarFallDepthAngle = 35.0f;
	// 10-20 「날아오는 궤적 일정하게」 → 흔듦 12° → 0(모든 유성이 같은 각도로 나란히 떨어진다).
	constexpr float StarFallJitter = 0.0f;
	constexpr float StarSpeed = 2600.0f;
	constexpr float StarCollisionRadius = 30.0f;
	constexpr float StarCollisionHeight = 350.0f;
	// 피해 반경(작은·큰), 피해 배수(스킬 피해 대비), 기절 시간, 그림 배율(유성·작은 빛 폭발·큰 빛 폭발). 흙먼지(Dekker)는 회색 얼룩이
	// 바닥에 오래 남아 뺐다(같은 촬영).
	constexpr float StarSmallRadius = 140.0f;
	constexpr float SkyRadius = 250.0f;
	constexpr float StarSmallDamage = 0.15f;
	constexpr float StarBigDamage = 0.6f;
	constexpr float SkyStunSeconds = 1.2f;
	// 10-20 「머리에서 꼬리로 갈 때 줄어들게」 → 평타 탄(꼬리 굵기가 고르다)은 머리로만 작게 쓰고(2.2 → 1.3), 지나간 길에 빛 점을
	// StarTailSpacing마다 남겨 수명 동안 줄인다(머리 굵고 꼬리 끝 가늘게). 꼬리 길이 ≈ 빠르기 2600 × 수명.
	// 같은 날 「거친 느낌이 너무 없어졌다 — 재질 느낌 다시 살려」 → 평타 탄을 원래 2.2배로 되돌리고 빛 점은 45 → 30으로 줄여 탄 무늬 밑에 깔리게.
	constexpr float StarTrailScale = 2.2f;
	constexpr float StarTailSpacing = 10.0f;
	constexpr float StarTailLife = 0.2f;
	constexpr float StarTailSize = 30.0f;
	// 10-20 「바닥에 부딪혔을 때 흔적이 남고 스킬 다 끝나면 자연스럽게 사라지게」: 부딪힌 바닥에 그을음 데칼(M_Gideon_StarScorch, gideon_scorch_material.py).
	// 크기(반지름 — 작은·큰), 투사 깊이, 마지막 큰 유성 뒤 남겨 두는 시간·사라지는 시간, 큰 유성이 안 떨어질 때 스스로 사라지기까지.
	constexpr float StarScorchSize = 75.0f;
	constexpr float StarBigScorchSize = 160.0f;
	constexpr float StarScorchDepth = 60.0f;
	constexpr float StarScorchHold = 0.6f;
	constexpr float StarScorchFade = 1.4f;
	constexpr float StarScorchFallback = 6.0f;
	// D 시안 4 불씨: 자국 하나당 개수·크기.
	constexpr int32 StarEmberCount = 8;
	constexpr float StarEmberSize = 16.0f;
	// D 보강 시안(Gideon.Skills.DBoost) — 모두 꼬리와 같은 둥근 빛 점(AddGlowDot)이다.
	//  1 부딪힘: 터지는 자리에 잠깐 큰 섬광 점 + 위·옆으로 튀는 불티(큰 유성은 1.5배 크기·두 배 개수).
	//  2 꼬리: 지나간 길에서 별가루가 옆으로 흩어지며 천천히 사그라든다(StarDustSpacing마다 하나).
	//  3 큰 유성: 터짐 배율 3 → 4.2, 큰 섬광 점, 바닥을 따라 둥글게 퍼지는 불티 고리.
	// 1차 시안표(gideon-47th-dboost-*)에서 「넷 다 뭔 차인지 모르겠다 — 알아볼 수 있게」 → 섬광 110 → 220·0.12 → 0.18초, 불티 8 → 14개·11 → 16,
	// 별가루 55 → 25cm마다·10 → 16, 큰 유성 터짐 4.2 → 5·섬광 280 → 450·고리 18 → 32개(크기 14 → 22), 큰 그을음 160 → 220.
	constexpr float StarBoostFlash = 220.0f;
	constexpr float StarBoostFlashLife = 0.18f;
	constexpr int32 StarBoostSparks = 14;
	constexpr float StarBoostSparkSize = 16.0f;
	constexpr float StarDustSpacing = 25.0f;
	constexpr float StarDustSize = 16.0f;
	constexpr float StarFinaleImpactScale = 5.0f;
	constexpr float StarFinaleFlash = 450.0f;
	constexpr int32 StarFinaleRing = 32;
	constexpr float StarFinaleScorchSize = 220.0f;
	// D 거친 꼬리(10-21 「D는 이펙트를 좀 더 거칠게」 → 시안 gideon-55th-drough-* 「D는 3으로 가자 — 티 나는 것 같아」): 꼬리 점을 옆으로 흔드는 폭,
	// 떨어져 나가는 부스러기 간격·크기. 안 고른 시안 = 1 부딪힐 때마다 돌 조각(Q 운석 바닥 터짐에서 돌만 남긴 사본
	// P_Gideon_RMB_HitWorld_RockOnly — 에셋은 남김, 쓰는 곳 없음) · 2 부딪힐 때마다 화면 흔들림 · 4 셋 다.
	constexpr float StarRaggedJitter = 9.0f;
	constexpr float StarRaggedSpacing = 35.0f;
	constexpr float StarRaggedFleck = 11.0f;

	// DBoost 값을 켜는 것들의 묶음으로(1 부딪힘 · 2 꼬리 · 4 큰 유성). 4 = 셋 다.
	int32 GetStarBoost()
	{
		switch (CVarGideonDBoost.GetValueOnGameThread())
		{
		case 1:
			return 1;
		case 2:
			return 2;
		case 3:
			return 4;
		case 4:
			return 1 | 2 | 4;
		default:
			return 0;
		}
	}
	// A 시안 7 빛줄기(10-20): 모으기·차오르기·접히기 시간, 굵기, 넓은 번짐 배율, 바닥 자국 간격·크기·남는 시간·사라짐, 판 길이 방향(U) 뒤집기.
	constexpr float SweepCharge = 0.15f;
	constexpr float SweepGrow = 0.06f;
	constexpr float SweepCollapse = 0.1f;
	constexpr float SweepBeamWidth = 70.0f;
	constexpr float SweepBloomScale = 3.2f;
	constexpr float SweepScorchGap = 45.0f;
	constexpr float SweepScorchSize = 50.0f;
	constexpr float SweepScorchHold = 0.4f;
	constexpr float SweepScorchFade = 1.0f;
	// 엔진 기본 판의 U는 X −50에서 0, +50에서 1(Tools/CharacterPipeline/plane_uv_dump.py) — 띠의 X가 손→끝이라 뒤집지 않는다.
	constexpr float SweepBeamFlipU = 0.0f;
	constexpr float StarSmallImpactScale = 2.0f;
	constexpr float StarBigImpactScale = 3.0f;
	constexpr float VolleyMinFocusDistance = 500.0f;
	// A 탄 빠르기와 혜성 그림의 몸통 길이(출발점 뒤로 달고 생기는 길이). 몸통 길이는 700px 화면(약 3cm/px)에서 혜성 몸통 끝과
	// 출발점 사이를 잰 어림값(±40)이다(gideon-37th-alook-* a_035). 10-20 몸 뒤 마법진 시도 넷은 「A 엉망이구나, 롤백」으로 뺐다.
	constexpr float BurdenCometTail = 190.0f;
	constexpr float BurdenSpeed = 2200.0f;
	// S 대상 고르기(A 도우미가 쏠 대상도): 커서 아래에 대상이 안 잡히면 커서 둘레 이 반경 안에서 가장 가까운 대상(10-20 「오브젝트 타겟형」).
	constexpr float TargetPickRadius = 150.0f;
	// A 도우미 광선(바로 앞까지 A였던 한 발 광선 — 10-21 「녹스 데스 레이처럼 광선을 딱 한 발만 팡 하고 쏘는 느낌」):
	// 쏜 뒤 그대로 있는 시간·가늘어지며 사라지는 시간, 처음 터지는 동안(굵기 DeathRayFlashWidth배·양 끝 빛덩이 DeathRayFlare).
	constexpr float DeathRayHold = 0.06f;
	constexpr float DeathRayFade = 0.24f;
	constexpr float DeathRayFlashSeconds = 0.05f;
	constexpr float DeathRayFlashWidth = 1.6f;
	constexpr float DeathRayFlare = 1.0f;
	// A 부르는 동작: 평타 1타(Primary_Attack_A_Medium)를 한 번 틀고 오른손이 가장 뒤에서 가장 앞까지의 90%에 닿는 0.18초에 도우미가 손에서 나온다
	// (앞 = 메시 +Y). 한 발 광선 때 동작 시안(gideon-53rd-adraft-*)에서 「A는 2가 제일 나은 듯」 → 평타 3타(Primary_Attack_C_Medium)였으나
	// 「쏠 때 동작은 좋은데 굳이 점프했다가 쏴야 해?」(10-21) — 3타는 골반이 0.07초에 10cm 웅크렸다(98.7 → 88.2) 0.33초까지 16cm 솟는다(발은 바닥
	// 그대로 — 측정 gideon-55th-ajump-*). 같은 한 손 뻗기 중 웅크림이 없는 1타(골반 103.5 → 105.6, 2타는 6cm 웅크림)로 바꿨다. F 찍는 동작과 같다.
	// 안 고른 후보 = Burden_slow(0.33) · PortalBlast_Start(0.18, 손에 고리를 듦) · Cast(0.12) · RMB_Intro(0.25)(gideon-53rd-ahand-*),
	// 그 전 = 두 손 모으기 Torn_Space_intro → 0.48초에 쏘고 Torn_Space_Outro로 내림.
	// 「세게」 시안(Gideon.Skills.AFx — 쏠 때 손·맞은 자리 빛 + 화면 흔들림 + 충격파 고리)은 답을 받기 전에 도우미로 바뀌어 평타마다 쏘기엔 과해 뺐다.
	constexpr float HelperSummonAt = 0.18f;
	// A 도우미(10-21 「A를 누르면 캐릭터를 도와주는 오브젝트가 나와서 공격할 때마다 지금 A를 써 주는」): 머무는 시간, 손에서 자리까지 날아가는 시간,
	// 화면 기준 자리(오른쪽·안쪽·위, cm), 위아래 일렁임(폭·빠르기·이 빠르기(cm/초) 이상 걸으면 멈춤), 따라붙는 빠르기(1/초),
	// 구슬을 가는 쪽으로 돌리는 최소 빠르기(cm/초)·돌리는 빠르기, 구슬 그림(평타 탄) 배율, 평타 뒤 쏘기까지, 한 발 피해(A 피해 배수),
	// 대상 찾는 사거리. 수치는 모두 임시값이다.
	// 같은 날 「A 지속시간 한 3~4배로」 → 8 → 30초(3.75배) → 「1분으로 늘려 그냥」 → 60초. 쿨은 「도우미 + 4초」로 맞춰 64초(Define).
	constexpr float HelperSeconds = 60.0f;
	constexpr float HelperFlyIn = 0.3f;
	constexpr float HelperRight = 70.0f;
	constexpr float HelperBack = 25.0f;
	constexpr float HelperUp = 115.0f;
	constexpr float HelperBob = 8.0f;
	constexpr float HelperBobHz = 0.8f;
	constexpr float HelperBobStopSpeed = 150.0f;
	constexpr float HelperFollow = 12.0f;
	constexpr float HelperTurnSpeed = 80.0f;
	constexpr float HelperTurnRate = 10.0f;
	constexpr float HelperOrbScale = 1.2f;
	constexpr float HelperShotDelay = 0.06f;
	constexpr float HelperShotDamage = 1.0f;
	constexpr float HelperRange = 1300.0f;
	// 10-21 「스킬로 타격할 때도 이펙트 나가면서 공격하는 게 좋지 않겠어?」 → 스킬이 맞힌 대상에게도 쏜다(HelperAssist). 여러 번 맞히는
	// 스킬(D 유성 48개·V 0.5초마다)이 쏟아내지 않게 이 간격에 한 번만.
	constexpr float HelperAssistGap = 0.35f;
	const TCHAR* const AnimationRoot =TEXT("/Game/ParagonGideon/Characters/Heroes/Gideon/Animations/");
	const TCHAR* const EffectRoot = TEXT("/Game/ParagonGideon/FX/Particles/Gideon/Abilities/");
	const TCHAR* const DekkerEffectRoot = TEXT("/Game/ParagonDekker/FX/Particles/Abilities/");
	const TCHAR* const KwangEffectRoot = TEXT("/Game/ParagonKwang/FX/Particles/Abilities/");
	const TCHAR* const MurielEffectRoot = TEXT("/Game/ParagonMuriel/FX/Particles/Abilities/");

	UParticleSystem* LoadEffect(const TCHAR* Folder, const TCHAR* Name, const TCHAR* Root = EffectRoot)
	{
		const FString Path = FString::Printf(TEXT("%s%s/FX/%s.%s"), Root, Folder, Name, Name);
		ConstructorHelpers::FObjectFinder<UParticleSystem> Finder(*Path);
		return Finder.Object;
	}

	UAnimSequence* LoadAnimation(const TCHAR* Name)
	{
		const FString Path = FString::Printf(TEXT("%s%s.%s"), AnimationRoot, Name, Name);
		ConstructorHelpers::FObjectFinder<UAnimSequence> Finder(*Path);
		return Finder.Object;
	}

	// 반투명 재질은 Opacity가 불투명도와 밝기에 함께 곱해져 사실상 제곱으로 옅어지고, 가산 재질(가운데 바닥 빛)은 밝기에만
	// 곱해진다. 같은 값을 주면 가운데만 진해 보이므로(사용자 지적 10-18) 가산 재질엔 제곱을 준다.
	float RiftRuneSlotOpacity(const UMaterialInterface* Material, float Opacity)
	{
		return Material && Material->GetBlendMode() == BLEND_Additive ? Opacity * Opacity : Opacity;
	}

	bool IsCombatTarget(const AActor* Actor, const AActor* Owner)
	{
		return IsValid(Actor) && Actor != Owner && (Actor->IsA<APawn>() || Actor->IsA<AKwangTrainingDummy>());
	}

	void SetStatus(AActor* Target, FName Status, float Seconds)
	{
		if (AKwangTrainingDummy* Dummy = Cast<AKwangTrainingDummy>(Target))
		{
			Dummy->SetCombatStatus(Status, Seconds);
		}
	}
}

UGideonSkillComponent::UGideonSkillComponent()
{
	// Burden 줄이 이어진 동안만 매 프레임 두 끝을 옮긴다(ApplyBurden이 켜고, 마지막 줄이 끊기면 끈다).
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.bStartWithTickEnabled = false;

	const auto Define = [this](EGideonSkill Skill, const TCHAR* Name, const TCHAR* Animation, UParticleSystem* Cast,
		float Damage, float Cooldown, float Range, float ActionTime, float RecoveryTime)
	{
		FGideonSkillDefinition& Definition = Skills.Add(Skill);
		Definition.Name = Name;
		Definition.Animation = LoadAnimation(Animation);
		Definition.CastEffect = Cast;
		Definition.Damage = Damage;
		Definition.Cooldown = Cooldown;
		Definition.Range = Range;
		Definition.ActionTime = ActionTime;
		Definition.RecoveryTime = RecoveryTime;
	};
	// 피해·쿨타임·사거리 중 Cosmic Rift 쿨 6초만 원작 위키 값이고 나머지는 임시값이다.
	// Q는 하늘에서 떨어지는 운석이라 바닥 지점을 찍는다(사거리 = 찍을 수 있는 거리).
	Define(EGideonSkill::PortalBlast, TEXT("Portal Blast"), TEXT("RMB_Cast"),
		LoadEffect(TEXT("ProjectileMeteor"), TEXT("P_Gideon_RMB_CastPortal")), 35.0f, 4.0f, 1200.0f, 0.35f, 0.35f);
	// 원본 동작은 0.2초에 두 팔을 들어 1.0초까지 버티고 1.7초까지 내린다. 팔을 들 때 마법진을 열고, 팔을 내리기 시작하면 풀어 준다.
	Define(EGideonSkill::CosmicRift, TEXT("Cosmic Rift"), TEXT("CosmicRift"),
		LoadEffect(TEXT("Meteor"), TEXT("P_Meteor_Cast")), 15.0f, 6.0f, 1200.0f, 0.20f, 0.80f);
	Skills[EGideonSkill::CosmicRift].bFinishAnimation = true;
	Define(EGideonSkill::TornSpace, TEXT("Torn Space"), TEXT("Torn_Space"),
		LoadEffect(TEXT("Portal"), TEXT("P_Portal_Cast")), 0.0f, 10.0f, 1200.0f, 0.50f, 0.30f);
	Define(EGideonSkill::BlackHole, TEXT("Black Hole"), TEXT("Blackhole_Start"),
		LoadEffect(TEXT("Ultimate"), TEXT("P_Ultimate_Cast")), 8.0f, 40.0f, 1000.0f, 0.50f, 0.0f);
	// 원작 Burden은 투사체로 맞힌 적과 줄로 이어진다(시전 사거리 1300, 쿨 6초 — 2017-09 위키). 기본 `Burden` 동작은 팔을 머리 위로
	// 휘돌려 버티는 자세라 앞으로 던지는 모양이 아니다. 오른손을 앞으로 내던지는 `Burden_slow`의 0.33초에 쏜다.
	Define(EGideonSkill::Burden, TEXT("Burden"), TEXT("Burden_slow"),
		LoadEffect(TEXT("Burden"), TEXT("P_Burden_Cast")), 15.0f, 64.0f, 1300.0f, 0.33f, 0.30f);
	// 10-21 A 자리가 도우미(HelperSeconds 8초)로 바뀌며 쿨 6 → 12초(임시 — 6이면 도우미가 끊기지 않고 늘 떠 있다), 도우미 30초가 되며 34초,
	// 60초가 되며 64초.
	Skills[EGideonSkill::Burden].bFinishAnimation = true;
	// 팩에 있으나 원작 스킬에 안 쓰인 `portal_blast_medium`(1.33초) 동작. 피해는 한 발 값(임시), 마지막 발은 시전 +0.7초.
	Define(EGideonSkill::PortalVolley, TEXT("Portal Volley"), TEXT("portal_blast_medium"), nullptr, 12.0f, 6.0f, 1400.0f, 0.30f, 0.50f);
	Skills[EGideonSkill::PortalVolley].bFinishAnimation = true;
	// Dekker 효과로 만든 셋. 동작은 Gideon 팩에서 원작 스킬에 안 쓰인 것을 빌린다. 수치는 모두 임시값이다.
	Define(EGideonSkill::StarLine, TEXT("Star Line"), TEXT("portal_blast_fast"), nullptr, 18.0f, 7.0f, LinePortals * LinePortalSpacing, 0.30f, 0.35f);
	Skills[EGideonSkill::StarLine].bFinishAnimation = true;
	// R 고리 방패: 고리를 들어 올리는 `PortalBlast_Loop`(F 동작 시안 4번 — 「카메라를 들고 있다」던 그 고리). 밀쳐낸 직후(+0.05초) 시전을 끝내
	// 바로 움직일 수 있다(10-19). 밀쳐내기는 시전 중일 때만 돌므로 시전 끝을 그보다 뒤에 둔다(30fps 한 틱 0.033초보다 넉넉히).
	// 같은 날 「팔 뻗어서 시전하는 걸로」 → 오른손을 앞으로 내뻗는 `Cast`(손이 가장 앞으로 나가는 때 0.13초 — 공이 생기는 0.15초와 맞음,
	// 후보 손 위치 측정 gideon-28th-ranims-*).
	Define(EGideonSkill::StarCage, TEXT("Ring Ward"), TEXT("Cast"), nullptr, 20.0f, 10.0f, 1000.0f, 0.15f, WardSeconds + 0.05f);
	// D는 「어색하다」(10-18)로 평타 2타 동작(오른손을 앞으로 휘두름, 발사 0.17초)으로 바꿈.
	Define(EGideonSkill::SkyLance, TEXT("Star Fall"), TEXT("Primary_Attack_B_Medium"), nullptr, 45.0f, 9.0f, 1100.0f, 0.20f, 0.45f);
	// F: 손을 모으는 `Torn_Space_intro` → 두 손을 모아 앞으로 뻗은 `Torn_Space_TargetingPose`를 번개 동안 되풀이 → 끝에 `Torn_Space_Outro`로
	// 내린다(「애니메이션 좀 더 자연스럽게」 10-18 — 자세만 되풀이하면 시작·끝이 뚝 끊겼다). 겨누는 자세(`RMB_Targeting_Pose`)는 양팔을
	// 옆으로 벌려 어색했다(동작 시안 표 gideon-19th-b-20261018-220602 5번 선택).
	// 10-20 F 동작 시안(gideon-40th-fa1-*/F_동작시안표.png)에서 「F 자세는 F3으로」 → 고리를 앞에 받쳐 들고 두 팔을 벌려 버티는 `Burden_Loop`.
	// 들어가는 동작은 같은 묶음의 `Burden_Start`, 끝 동작은 없이 시전이 끝날 때 섞어 내린다(Torn_Space_Outro는 다른 자세에서 내려오는 동작이라).
	// 같은 날 「손 내미는 거 위주로」 → 「F는 1번으로」(gideon-49th-fanim-*): 평타 1타로 손을 뻗어 찍고 바로 움직인다
	// (FocusMoveAfter — 10-21 손 뻗은 채 멈춰 버티던 것, 서서 모으다 2타로 다시 내지르던 것을 뺌). Burden_Loop는 옛 F 시안(1~10)만 쓴다.
	Define(EGideonSkill::VoidRay, TEXT("Void Ray"), TEXT("Primary_Attack_A_Medium"), nullptr, 8.0f, 8.0f, RayRange, 0.35f, RaySeconds + 0.1f);
	RayHold = LoadAnimation(TEXT("Burden_Loop"));
	RayOutro = nullptr;
	// A 시안 7 빛줄기(10-20 「광선 느낌으로 — 디테일·이펙트 신경」): 두 손을 모아 앞으로 뻗어 쏘고(옛 F 광선 동작), 끝에 내린다.
	SweepIntro = LoadAnimation(TEXT("Torn_Space_intro"));
	SweepHold = LoadAnimation(TEXT("Torn_Space_TargetingPose"));
	SweepOutro = LoadAnimation(TEXT("Torn_Space_Outro"));
	RayShotAnim = LoadAnimation(TEXT("Primary_Attack_A_Medium"));
	Skills[EGideonSkill::SkyLance].bFinishAnimation = true;

	PrimaryProjectile = LoadEffect(TEXT("Primary"), TEXT("P_Gideon_Primary_Projectile"));
	PrimaryMuzzle = LoadEffect(TEXT("Primary"), TEXT("P_Gideon_Primary_MuzzleFlash"));
	PrimaryHitCharacter = LoadEffect(TEXT("Primary"), TEXT("P_Gideon_Primary_HitCharacter"));
	PrimaryHitWorld = LoadEffect(TEXT("Primary"), TEXT("P_Gideon_Primary_HitWorld"));
	PrimaryNoHit = LoadEffect(TEXT("Primary"), TEXT("P_Gideon_Primary_NoHit"));
	BlastPortal = LoadEffect(TEXT("ProjectileMeteor"), TEXT("P_Gideon_RMB_Portal"));
	BlastProjectile = LoadEffect(TEXT("ProjectileMeteor"), TEXT("P_Gideon_RMB_Proj"));
	BlastHitWorld = LoadEffect(TEXT("ProjectileMeteor"), TEXT("P_Gideon_RMB_HitWorld"));
	BlastExplosion = LoadEffect(TEXT("ProjectileMeteor"), TEXT("P_Gideon_RMB_NoHitExplosion"));
	RiftPortal = LoadEffect(TEXT("Meteor"), TEXT("P_Gideon_Meteor_Portal"));
	ConstructorHelpers::FObjectFinder<UStaticMesh> RuneOuter(TEXT("/Game/ParagonGideon/FX/Meshes/Heroes/Gideon/SM_Rune_Ring_Outer.SM_Rune_Ring_Outer"));
	RiftRuneOuter = RuneOuter.Object;
	// 안쪽 겹원 모형 사본에서 원 바깥 삼각형 조각을 잘라 낸 것(Tools/CharacterPipeline/gideon_rune_shards.py). 경계가 곧 원이다.
	ConstructorHelpers::FObjectFinder<UStaticMesh> RuneBorder(TEXT("/Game/TopDown/Characters/Gideon/FX/SM_Rune_Ring_Inner_NoShards.SM_Rune_Ring_Inner_NoShards"));
	RiftRuneBorder = RuneBorder.Object;
	ConstructorHelpers::FObjectFinder<UStaticMesh> RuneCenter(TEXT("/Game/ParagonGideon/FX/Meshes/Heroes/Gideon/SM_Ult_Runes_Inner.SM_Ult_Runes_Inner"));
	RiftRuneCenter = RuneCenter.Object;
	// W 룬·삼각이 빽빽한 원판(점선 고리 자리, gideon-meshes-20261018-164004).
	ConstructorHelpers::FObjectFinder<UStaticMesh> RuneDense(TEXT("/Game/ParagonGideon/FX/Meshes/Heroes/Gideon/SM_Circle_Curved_Edge.SM_Circle_Curved_Edge"));
	RiftRuneDense = RuneDense.Object;
	// 룬 재질은 투명도 값이 없어, Opacity 값을 더한 사본을 원본 이름으로 찾아 끼운다(gideon_fade_assets.py).
	for (const TCHAR* Name : { TEXT("M_Star_Runes_Ring_VertColorFade"), TEXT("M_Star_Runes_Ring"), TEXT("M_Star_Runes_Big"), TEXT("M_Floor_Burst") })
	{
		ConstructorHelpers::FObjectFinder<UMaterialInterface> Faded(
			*FString::Printf(TEXT("/Game/TopDown/Characters/Gideon/FX/%s_Fade.%s_Fade"), Name, Name));
		if (Faded.Succeeded())
		{
			RiftRuneFadeMaterials.Add(Name, Faded.Object);
		}
	}
	RiftImpact = LoadEffect(TEXT("Meteor"), TEXT("P_Gideon_MeteorBigImpact"));
	PortalEntrance = LoadEffect(TEXT("Portal"), TEXT("P_Portal_Entrance"));
	PortalExit = LoadEffect(TEXT("Portal"), TEXT("P_Portal_Exit"));
	PortalEntranceClose = LoadEffect(TEXT("Portal"), TEXT("P_Portal_Entrance_Close"));
	PortalExitClose = LoadEffect(TEXT("Portal"), TEXT("P_Portal_Exit_Close"));
	TeleportEnter = LoadEffect(TEXT("Portal"), TEXT("P_Portal_Teleport_Enter"));
	TeleportExit = LoadEffect(TEXT("Portal"), TEXT("P_Portal_Teleport_Exit"));
	BlackHole = LoadEffect(TEXT("Ultimate"), TEXT("P_Gideon_Ultimate"));
	BlackHoleCancelled = LoadEffect(TEXT("Ultimate"), TEXT("P_Gideon_Ultimate_Cancelled"));
	BurdenProjectile = LoadEffect(TEXT("Burden"), TEXT("P_Gideon_Burden_Projectile"));
	BurdenMuzzle = LoadEffect(TEXT("Burden"), TEXT("P_Gideon_Burden_MuzzleFlash"));
	BurdenHitCharacter = LoadEffect(TEXT("Burden"), TEXT("P_Gideon_Burden_HitCharacter"));
	BurdenNoHit = LoadEffect(TEXT("Burden"), TEXT("P_Gideon_Burden_NoHit"));
	BurdenDot = LoadEffect(TEXT("Burden"), TEXT("P_Gideon_Burden_DoT"));
	BurdenDotEnd = LoadEffect(TEXT("Burden"), TEXT("P_Gideon_Burden_DoT2_End"));
	// 직접 만든 사본(Tools/CharacterPipeline/gideon_portal_hide.py 등).
	const auto LoadOwnEffect = [](const TCHAR* Name) -> UParticleSystem*
	{
		ConstructorHelpers::FObjectFinder<UParticleSystem> Finder(*FString::Printf(TEXT("/Game/TopDown/Characters/Gideon/FX/%s.%s"), Name, Name));
		return Finder.Object;
	};
	SkyPortal = LoadOwnEffect(TEXT("P_Gideon_RMB_Portal_NoStreak"));
	SealCircle = LoadEffect(TEXT("Ultimate"), TEXT("P_Gideon_Ultimate_Cast"));
	AnnihilateFlash = LoadEffect(TEXT("SlowBomb"), TEXT("P_Dekker_SlowBomb_Explosion"), DekkerEffectRoot);
	// F 녹스 번개: 줄 조각 = 원통, 불티 = 공, 재질 = 빛만 내는 가산 재질(Tools/CharacterPipeline/gideon_noxbolt_material.py).
	ConstructorHelpers::FObjectFinder<UStaticMesh> NoxCylinder(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	NoxSegmentMesh = NoxCylinder.Object;
	ConstructorHelpers::FObjectFinder<UStaticMesh> NoxSphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	NoxSparkMesh = NoxSphere.Object;
	ConstructorHelpers::FObjectFinder<UMaterialInterface> NoxMaterial(TEXT("/Game/TopDown/Characters/Gideon/FX/M_NoxBolt.M_NoxBolt"));
	NoxBoltMaterial = NoxMaterial.Object;
	// 파라곤 시안: 콰앙 번개 광선·전기 불꽃, 띠(판) 모형, 인스턴스 메시용 사본 재질 둘(Tools/CharacterPipeline/gideon_paragon_mat_copies.py).
	RayBolt = LoadEffect(TEXT("LightStrike"), TEXT("P_LightStrike_Beams"), KwangEffectRoot);
	RayArc = LoadEffect(TEXT("LightStrike"), TEXT("P_LightStrikeImpact"), KwangEffectRoot);
	ConstructorHelpers::FObjectFinder<UStaticMesh> NoxPlane(TEXT("/Engine/BasicShapes/Plane.Plane"));
	NoxStripMesh = NoxPlane.Object;
	ConstructorHelpers::FObjectFinder<UMaterialInterface> Discharge(
		TEXT("/Game/TopDown/Characters/Gideon/FX/ParagonISM/M_Kwang_Electric_Discharge_ISM.M_Kwang_Electric_Discharge_ISM"));
	NoxDischargeMaterial = Discharge.Object;
	ConstructorHelpers::FObjectFinder<UMaterialInterface> BoltStrip(
		TEXT("/Game/TopDown/Characters/Gideon/FX/ParagonISM/M_Kwang_Lightning_Bolt_Master_ISM.M_Kwang_Lightning_Bolt_Master_ISM"));
	NoxBoltStripMaterial = BoltStrip.Object;
	// 시안 9: 가운데 밝고 가장자리로 부드럽게 꺼지는 띠·둥근 불티(Tools/CharacterPipeline/gideon_noxglow_material.py).
	ConstructorHelpers::FObjectFinder<UMaterialInterface> GlowStrip(TEXT("/Game/TopDown/Characters/Gideon/FX/M_NoxGlowStrip.M_NoxGlowStrip"));
	NoxGlowStripMaterial = GlowStrip.Object;
	ConstructorHelpers::FObjectFinder<UMaterialInterface> SoftSpark(TEXT("/Game/TopDown/Characters/Gideon/FX/M_NoxSpark.M_NoxSpark"));
	NoxSoftSparkMaterial = SoftSpark.Object;
	// D 유성 = 평타 보라 빛 탄을 키운 것(밝고 가는 줄기가 날아가는 방향으로 늘어진다, gideon-19th-movers-20261018-213101 05).
	// W 운석 꼬리는 비스듬히 옮기면 세로 기둥으로, Q 운석은 돌덩이·돌 파편으로 보여(「밝은 작은 유성 같은 느낌이었는데」 10-18) 바꿈.
	// 터짐은 평타 명중 빛(작은 것)·V 섬광(큰 것)으로 돌 파편 없이. 기절 표시는 Dekker 것.
	StarTrail = LoadEffect(TEXT("Primary"), TEXT("P_Gideon_Primary_Projectile"));
	// V 끝 둘째 터짐: 무지개 고리를 숨긴 Dekker 큰 폭발(푸른 충격 고리).
	AnnihilateRing = LoadOwnEffect(TEXT("P_Dekker_SkyBeam_BigBlast_NoHalo"));
	// R 밀쳐낼 때 공이 깨지듯 터지는 거품.
	WardPop = LoadEffect(TEXT("ConsGround"), TEXT("P_ConsGround_Bubble_Pop"), MurielEffectRoot);
	// W 운석비·폭발: 「마법진 위에 폭발인데 왜 돌이 쪼개지는 이펙트가 들어가지」(10-19) → 돌 조각 가닥을 숨긴 사본(gideon_portal_hide.py).
	// 운석비는 보라 돌 조각 2가닥, 폭발(Q 운석 바닥 충돌)은 운석이 쪼개지는 조각 7가닥 + 보라 돌 조각 1가닥(gideon-28th-wdump-*). Q는 원본 그대로.
	RiftShower = LoadOwnEffect(TEXT("P_Gideon_Meteor_Shower_NoRock"));
	RiftBlast = LoadOwnEffect(TEXT("P_Gideon_RMB_HitWorld_NoRock"));
	// F 10: 콰앙 궁극기 번개에서 붉은 회오리 가닥(ParticleModuleRequired_7)만 숨긴 사본(gideon_portal_hide.py, 「저 벌건색 없앨 수 없나」).
	OriginalBolt = LoadOwnEffect(TEXT("P_Kwang_Ult_Lightning_NoRed"));
	// V 일렁이는 빛 시안: Prime Helix 충격파(R 시안 R1).
	BlackHoleGlow = LoadEffect(TEXT("SpecialAttack2"), TEXT("P_PH_Shockwave_V2"), TEXT("/Game/ParagonMinions/FX/Particles/Minions/Prime_Helix/Abilities/"));
	SkyStunned = LoadEffect(TEXT("SkyBeam"), TEXT("P_Dekker_SkyBeam_Stunned"), DekkerEffectRoot);
	ConstructorHelpers::FObjectFinder<UMaterialInterface> Scorch(TEXT("/Game/TopDown/Characters/Gideon/FX/M_Gideon_StarScorch.M_Gideon_StarScorch"));
	StarScorchMaterial = Scorch.Object;
	ConstructorHelpers::FObjectFinder<UMaterialInterface> Rune(TEXT("/Game/TopDown/Characters/Gideon/FX/M_Gideon_StarRune.M_Gideon_StarRune"));
	StarRuneMaterial = Rune.Object;
	ConstructorHelpers::FObjectFinder<UMaterialInterface> Astro(TEXT("/Game/TopDown/Characters/Gideon/FX/M_Gideon_StarAstro.M_Gideon_StarAstro"));
	StarAstroMaterial = Astro.Object;
	FocusGather = LoadEffect(TEXT("SpecialAttack1"), TEXT("P_Prime_Mortar_Chargeup"), TEXT("/Game/ParagonMinions/FX/Particles/Minions/Prime_Helix/Abilities/"));
	FocusLightStrike = LoadEffect(TEXT("LightStrike"), TEXT("P_Kwang_LightStrike_Burst"), KwangEffectRoot);
	FocusShockwave = LoadEffect(TEXT("StasisBomb"), TEXT("P_Dekker_StasisBomb_Shockwave"), DekkerEffectRoot);
	FocusStarBurst = LoadEffect(TEXT("SkyBeam"), TEXT("P_Dekker_SkyBeam_FirstBlast"), DekkerEffectRoot);
	// A 시안 7 빛줄기 띠: 흰 심 + 보라 빛무리 + 길이 방향으로 흐르는 에너지 가닥(Tools/CharacterPipeline/gideon_sweep_beam_material.py).
	ConstructorHelpers::FObjectFinder<UMaterialInterface> SweepBeam(TEXT("/Game/TopDown/Characters/Gideon/FX/M_Gideon_SweepBeam.M_Gideon_SweepBeam"));
	SweepBeamMaterial = SweepBeam.Object;
	ConstructorHelpers::FObjectFinder<UStaticMesh> TetherMesh(TEXT("/Game/ParagonGideon/FX/Meshes/Heroes/Gideon/SM_Burden_Spline.SM_Burden_Spline"));
	BurdenTetherMesh = TetherMesh.Object;
}

void UGideonSkillComponent::BeginPlay()
{
	Super::BeginPlay();
	Character = Cast<ATopDownCombatCharacter>(GetOwner());
	USkeletalMeshComponent* Mesh = Character.IsValid() ? Character->GetMesh() : nullptr;
	bEnabled = Mesh && Mesh->GetSkeletalMeshAsset();
	for (const TPair<EGideonSkill, FGideonSkillDefinition>& Pair : Skills)
	{
		const UAnimSequence* Animation = Pair.Value.Animation;
		// 시전 시점 조정의 근거로 원본 길이를 남긴다.
		UE_LOG(LogTemp, Display, TEXT("GIDEON_ANIM skill=%s anim=%s length=%.3f skeleton_match=%d"),
			*Pair.Value.Name.ToString(), *GetNameSafe(Animation), Animation ? Animation->GetPlayLength() : 0.0f,
			Animation && Mesh && Animation->GetSkeleton() == Mesh->GetSkeletalMeshAsset()->GetSkeleton());
	}
}

const FGideonSkillDefinition* UGideonSkillComponent::FindSkill(int32 Slot) const
{
	return Slot >= 0 && Slot < SlotCount ? Skills.Find(static_cast<EGideonSkill>(Slot)) : nullptr;
}

FText UGideonSkillComponent::GetSkillDisplayName(int32 Slot) const
{
	const FGideonSkillDefinition* Skill = FindSkill(Slot);
	return Skill ? FText::FromName(Skill->Name) : FText::GetEmpty();
}

FText UGideonSkillComponent::GetSkillStatusText(int32 Slot) const
{
	if (bCasting && Slot == ActiveSlot && ActiveSkill == EGideonSkill::BlackHole && GetWorld() && BlackHoleEnd > 0.0)
	{
		return FText::FromString(FString::Printf(TEXT("%.1fs"), FMath::Max(0.0, BlackHoleEnd - GetWorld()->GetTimeSeconds())));
	}
	// A 도우미가 떠 있는 동안 남은 시간.
	if (Slot == static_cast<int32>(EGideonSkill::Burden) && HelperOrb.IsValid() && GetWorld())
	{
		return FText::FromString(FString::Printf(TEXT("%.1fs"), FMath::Max(0.0, HelperEnd - GetWorld()->GetTimeSeconds())));
	}
	return FText::GetEmpty();
}

float UGideonSkillComponent::GetSlotCooldownRemaining(int32 Slot) const
{
	const double* End = FindSkill(Slot) ? CooldownEnds.Find(static_cast<EGideonSkill>(Slot)) : nullptr;
	return End && GetWorld() && !IgnoresCooldowns() ? FMath::Max(0.0f, static_cast<float>(*End - GetWorld()->GetTimeSeconds())) : 0.0f;
}

FString UGideonSkillComponent::GetInputFeedback() const
{
	return GetWorld() && GetWorld()->GetTimeSeconds() < FeedbackDeadline ? Feedback : FString();
}

bool UGideonSkillComponent::IgnoresCooldowns() const
{
	return CVarGideonIgnoreCooldowns.GetValueOnGameThread() != 0;
}

bool UGideonSkillComponent::RejectInput(const TCHAR* Reason)
{
	Feedback = Reason;
	FeedbackDeadline = GetWorld() ? GetWorld()->GetTimeSeconds() + 1.25 : 0.0;
	UE_LOG(LogTemp, Display, TEXT("GIDEON_SKILL rejected=%s"), Reason);
	return false;
}

bool UGideonSkillComponent::TryUseSkillSlot(int32 Slot, const FVector& AimLocation, AActor* Target)
{
	const FGideonSkillDefinition* Skill = FindSkill(Slot);
	if (!Skill)
	{
		return RejectInput(TEXT("Unavailable"));
	}
	if (!bEnabled || !GetWorld() || !Character.IsValid() || !Character->GetCharacterMovement() ||
		Character->GetCharacterMovement()->MovementMode != MOVE_Walking || AimLocation.ContainsNaN())
	{
		return RejectInput(TEXT("Unavailable"));
	}
	if (bCasting)
	{
		return RejectInput(TEXT("Casting"));
	}
	if (GetSlotCooldownRemaining(Slot) > 0.0f)
	{
		return RejectInput(TEXT("Cooldown"));
	}
	const EGideonSkill Kind = static_cast<EGideonSkill>(Slot);
	FVector Aim = AimLocation;
	switch (Kind)
	{
	case EGideonSkill::PortalBlast:
	case EGideonSkill::CosmicRift:
	case EGideonSkill::BlackHole:
	case EGideonSkill::SkyLance:
		if (!ClampGroundTarget(AimLocation, Skill->Range, false, Aim))
		{
			return RejectInput(TEXT("Invalid ground"));
		}
		break;
	case EGideonSkill::TornSpace:
		// 순간이동 끝점은 실제로 서 있을 수 있는 내비 위여야 한다.
		if (!ClampGroundTarget(AimLocation, Skill->Range, true, Aim))
		{
			return RejectInput(TEXT("No walkable destination"));
		}
		break;
	case EGideonSkill::Burden:
	case EGideonSkill::PortalVolley:
	case EGideonSkill::StarLine:
	case EGideonSkill::StarCage:
	case EGideonSkill::VoidRay:
		// S는 찍은 대상에만 쓴다(「오브젝트 타겟형, 논타겟으로 못 쓰게」 10-20 — A 시안 8도 그랬다가 10-21 도우미로 바뀜). 대상이 없거나 사거리 밖이면 쓰지 않는다.
		ActiveTarget.Reset();
		if (RequiresTarget(Kind))
		{
			AActor* Picked = PickSkillTarget(Target, AimLocation);
			if (!Picked)
			{
				return RejectInput(TEXT("No target"));
			}
			if (FVector::Dist2D(Picked->GetActorLocation(), Character->GetActorLocation()) > Skill->Range)
			{
				return RejectInput(TEXT("Out of range"));
			}
			ActiveTarget = Picked;
			Aim = Picked->GetActorLocation();
		}
		if ((Aim - Character->GetActorLocation()).GetSafeNormal2D().IsNearlyZero())
		{
			return RejectInput(TEXT("Choose a direction"));
		}
		// F 11~15는 한 명을 고정하는 스킬이라 커서 둘레·조준선에 대상이 없으면 쓸 수 없다(「타겟팅으로, 오브젝트가 없으면 못 쓰게」 10-20).
		if (Kind == EGideonSkill::VoidRay && CVarGideonFStyle.GetValueOnGameThread() >= 11)
		{
			const FVector Feet = GetFeetLocation();
			const FVector Direction = (Aim - Character->GetActorLocation()).GetSafeNormal2D();
			const FVector Cursor = Feet + (FVector(Aim.X, Aim.Y, Feet.Z) - Feet).GetClampedToMaxSize(RayRange);
			if (!FindFocusTarget(Cursor, Feet, Feet + Direction * RayRange))
			{
				return RejectInput(TEXT("No target"));
			}
		}
		break;
	}
	return BeginCast(Kind, Aim);
}

FVector UGideonSkillComponent::GetFeetLocation() const
{
	return Character.IsValid() ? Character->GetActorLocation() -
		FVector(0.0f, 0.0f, Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()) : FVector::ZeroVector;
}

bool UGideonSkillComponent::ClampGroundTarget(const FVector& Aim, float Range, bool bRequireNavigation, FVector& Result) const
{
	if (!Character.IsValid() || !GetWorld())
	{
		return false;
	}
	const FVector Feet = GetFeetLocation();
	FVector Offset = Aim - Feet;
	Offset.Z = 0.0f;
	if (Offset.SizeSquared() > FMath::Square(Range))
	{
		Offset = Offset.GetSafeNormal() * Range;
	}
	const FVector Column = Feet + Offset;
	FCollisionQueryParams Query(SCENE_QUERY_STAT(GideonGround), false, Character.Get());
	FCollisionObjectQueryParams Objects(ECC_WorldStatic);
	FHitResult Hit;
	// 높이가 다른 바닥을 고른 경우에도 그 열의 실제 지면을 쓴다.
	if (!GetWorld()->LineTraceSingleByObjectType(Hit, FVector(Column.X, Column.Y, Aim.Z + 500.0f),
		FVector(Column.X, Column.Y, Aim.Z - 1000.0f), Objects, Query))
	{
		return false;
	}
	Result = Hit.ImpactPoint;
	if (!bRequireNavigation)
	{
		return true;
	}
	UNavigationSystemV1* Navigation = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
	FNavLocation Projected;
	if (!Navigation || !Navigation->ProjectPointToNavigation(Result, Projected, FVector(100.0f, 100.0f, 250.0f),
		&Character->GetNavAgentPropertiesRef()))
	{
		return false;
	}
	Result = Projected.Location;
	return true;
}

bool UGideonSkillComponent::BeginCast(EGideonSkill Skill, const FVector& Aim)
{
	const FGideonSkillDefinition& Definition = Skills[Skill];
	USkeletalMeshComponent* Mesh = Character->GetMesh();
	UAnimInstance* AnimInstance = Mesh ? Mesh->GetAnimInstance() : nullptr;
	if (!AnimInstance)
	{
		return RejectInput(TEXT("Unavailable"));
	}
	Character->CancelBasicAttackForSkill();
	if (AController* Controller = Character->GetController())
	{
		Controller->StopMovement();
	}
	Character->GetCharacterMovement()->StopMovementImmediately();
	const FVector Direction = (Aim - Character->GetActorLocation()).GetSafeNormal2D();
	if (!Direction.IsNearlyZero())
	{
		Character->SetActorRotation(FRotator(0.0f, Direction.Rotation().Yaw, 0.0f));
	}

	bCasting = true;
	++CastGeneration;
	ActiveSkill = Skill;
	ActiveSlot = static_cast<int32>(Skill);
	ActiveAim = Aim;
	bSavedOrientRotation = Character->GetCharacterMovement()->bOrientRotationToMovement;
	Character->GetCharacterMovement()->bOrientRotationToMovement = false;
	CastAnimInstance = AnimInstance;
	SavedRootMotionMode = AnimInstance->RootMotionMode;
	// 제자리 시전이다. Torn Space의 이동도 원본 루트 모션이 아니라 순간이동으로 처리한다.
	AnimInstance->SetRootMotionMode(ERootMotionMode::IgnoreRootMotion);
	ActiveMontage = nullptr;
	UAnimSequence* Animation = Definition.Animation;
	// A 시안 7 빛줄기는 한 손으로 던지는 A 동작 대신 두 손을 모으는 동작으로 시작한다(모은 손 사이에서 빛줄기가 나간다).
	const int32 ADraft = CVarGideonANew.GetValueOnGameThread();
	float ActionTime = Definition.ActionTime;
	if (Skill == EGideonSkill::Burden && ADraft == 7 && SweepIntro)
	{
		Animation = SweepIntro;
	}
	// A 도우미(8)는 평타 1타를 한 번 틀고, 손이 거의 다 나간 때(HelperSummonAt)에 손에서 도우미가 나온다.
	if (Skill == EGideonSkill::Burden && ADraft == 8 && RayShotAnim)
	{
		Animation = RayShotAnim;
		ActionTime = HelperSummonAt;
	}
	// R 고리 방패는 10-19부터 버티지 않으므로(바로 밀쳐내고 끝) 고리 든 자세를 되풀이하지 않는다. 모든 시전이 한 번 재생이다.
	// F도 10-21 「몸이 멈춰 있는 게 어색해」로 손 뻗은 순간에 멈춰 버티던 것을 뺐다(찍고 바로 움직인다 — FocusMoveAfter).
	if (Animation && Animation->GetSkeleton() == Mesh->GetSkeletalMeshAsset()->GetSkeleton())
	{
		ActiveMontage = UAnimMontage::CreateSlotAnimationAsDynamicMontage(Animation, CastSlot, 0.08f, 0.15f, 1.0f, 1);
		if (ActiveMontage)
		{
			AnimInstance->Montage_Play(ActiveMontage, 1.0f);
		}
	}
	if (Definition.CastEffect)
	{
		UGameplayStatics::SpawnEmitterAttached(Definition.CastEffect, Mesh, NAME_None, FVector::ZeroVector,
			FRotator::ZeroRotator, EAttachLocation::KeepRelativeOffset, true);
	}
	if (Skill == EGideonSkill::TornSpace)
	{
		// 원작처럼 양 끝 포털을 먼저 열고, 시전 동작이 끝날 즈음 건너간다.
		const FVector Lift(0.0f, 0.0f, TornSpacePortalHeight);
		// 두 포털 모두 건너가는 방향을 보게 돌린다(방향을 안 주면 어디로 쓰든 같은 쪽을 본다).
		const FVector Travel = (Aim - GetFeetLocation()).GetSafeNormal2D();
		const FRotator Facing(0.0f, (Travel.IsNearlyZero() ? Character->GetActorForwardVector() : Travel).Rotation().Yaw
			+ TornSpacePortalYawOffset, 0.0f);
		EntrancePortal = SpawnOwnedEffect(PortalEntrance, GetFeetLocation() + Lift, Facing);
		ExitPortal = SpawnOwnedEffect(PortalExit, Aim + Lift, Facing);
	}
	StartCooldown(Skill);
	UE_LOG(LogTemp, Display, TEXT("GIDEON_SKILL cast=%s slot=%d aim=%s montage=%d"), *Definition.Name.ToString(),
		ActiveSlot, *Aim.ToCompactString(), ActiveMontage != nullptr);

	FTimerManager& Timers = GetWorld()->GetTimerManager();
	Timers.SetTimer(ActionTimer, FTimerDelegate::CreateUObject(this, &UGideonSkillComponent::ExecuteAction, CastGeneration),
		FMath::Max(ActionTime, 0.01f), false);
	if (Skill != EGideonSkill::BlackHole)
	{
		// Black Hole은 유지 시간이 끝날 때 스스로 시전을 끝낸다.
		Timers.SetTimer(RecoveryTimer, this, &UGideonSkillComponent::FinishCast,
			Definition.ActionTime + Definition.RecoveryTime, false);
	}
	return true;
}

void UGideonSkillComponent::StartCooldown(EGideonSkill Skill)
{
	CooldownEnds.Add(Skill, GetWorld()->GetTimeSeconds() + Skills[Skill].Cooldown);
}

void UGideonSkillComponent::ExecuteAction(uint32 Generation)
{
	if (!bCasting || Generation != CastGeneration || !Character.IsValid())
	{
		return;
	}
	const FGideonSkillDefinition& Definition = Skills[ActiveSkill];
	UE_LOG(LogTemp, Display, TEXT("GIDEON_SKILL action=%s"), *Definition.Name.ToString());
	switch (ActiveSkill)
	{
	case EGideonSkill::PortalBlast:
		ExecutePortalBlast();
		break;
	case EGideonSkill::CosmicRift:
		ExecuteCosmicRift();
		break;
	case EGideonSkill::TornSpace:
		ExecuteTornSpace();
		break;
	case EGideonSkill::BlackHole:
		ExecuteBlackHole();
		break;
	case EGideonSkill::Burden:
	{
		// 새 스킬 러프 시안(Gideon.Skills.ANew 2·3·5·6·7·8)이 켜져 있으면 그걸 쓴다. 뺀 1·4나 없는 번호는 지금 A로.
		const int32 Draft = CVarGideonANew.GetValueOnGameThread();
		if (Draft == 2 || Draft == 3 || (Draft >= 5 && Draft <= 8))
		{
			ExecuteNewSkillDraft(Draft);
			break;
		}
		// 10-20 마법진 시도(몸 뒤·등 뒤 고리·발밑·혜성 몸통 자리)는 「A 엉망이구나, 롤백」으로 모두 뺐다. 원래대로 오른손(Muzzle_01)에서 쏜다.
		if (BurdenMuzzle)
		{
			UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), BurdenMuzzle, GetSocketLocation(TEXT("Muzzle_01")));
		}
		// 혜성 그림은 출발점 뒤로 약 BurdenCometTail 긴 몸통을 달고 생겨, 손에서 쏴도 몸통이 캐릭터 뒤에서 먼저 보였다
		// (gideon-37th-alook-* a_035 — 「뒤에서 불쑥」의 정체). 몸통 끝이 손에 닿을 때까지 그림을 숨겨 손에서부터 나가게 한다
		// (「A 롤백하고 오브젝트를 손에서부터 나가게」 10-20). 판정은 손에서부터 그대로다.
		if (AGideonProjectile* Comet = LaunchProjectile(EGideonProjectileKind::Burden, TEXT("Muzzle_01"), ActiveAim, BurdenSpeed, Definition.Range,
			Definition.Damage, BurdenProjectile, BurdenHitCharacter, nullptr, BurdenNoHit))
		{
			Comet->HideTrailFor(BurdenCometTail / BurdenSpeed);
		}
		break;
	}
	case EGideonSkill::PortalVolley:
		ExecutePortalVolley();
		break;
	case EGideonSkill::StarLine:
		ExecuteStarLine();
		break;
	case EGideonSkill::StarCage:
		ExecuteRingWard();
		break;
	case EGideonSkill::SkyLance:
		ExecuteSkyLance();
		break;
	case EGideonSkill::VoidRay:
		ExecuteVoidRay();
		break;
	}
}

void UGideonSkillComponent::ExecuteVoidRay()
{
	// 조준 방향으로 번개를 붙잡는다(「레이저 발사 같은 느낌, 녹스 번개처럼」 10-18). 벽에 닿으면 거기서 끊긴다.
	const FVector Muzzle = GetRayHands();
	const FVector Direction = (ActiveAim - Character->GetActorLocation()).GetSafeNormal2D();
	const FVector Feet = GetFeetLocation();
	FVector End = Feet + Direction * RayRange;
	FHitResult Wall;
	FCollisionQueryParams Query(SCENE_QUERY_STAT(GideonVoidRay), false, Character.Get());
	if (GetWorld()->LineTraceSingleByObjectType(Wall, Muzzle, Muzzle + Direction * RayRange, FCollisionObjectQueryParams(ECC_WorldStatic), Query))
	{
		End = FVector(Wall.ImpactPoint.X, Wall.ImpactPoint.Y, Feet.Z);
	}
	const FVector Strike = End + FVector(0.0f, 0.0f, 40.0f);
	// 10: 대상이 없으면 사거리 끝(화면 밖일 수 있음) 대신 커서 자리(사거리 안으로 줄임)에 떨어진다(「F 커서 자리에 떨어지게」 10-19).
	const FVector Cursor = Feet + (FVector(ActiveAim.X, ActiveAim.Y, Feet.Z) - Feet).GetClampedToMaxSize(RayRange);
	NoxStyle = FMath::Clamp(CVarGideonFStyle.GetValueOnGameThread(), 1, 15);
	if (NoxStyle >= 11)
	{
		UE_LOG(LogTemp, Display, TEXT("GIDEON_VARIANT skill=F style=%d"), NoxStyle);
		ExecuteFocusBolt(Feet, End, Cursor, NoxStyle);
		return;
	}
	// 손을 모으는 동작이 끝나면 뻗은 자세를 번개 동안 되풀이하고, 끝에 손을 내린다(시작·끝이 뚝 끊기지 않게).
	PlayCastMontage(RayHold, 100, true);
	After(RaySeconds, [this, Generation = CastGeneration]()
	{
		if (bCasting && Generation == CastGeneration)
		{
			PlayCastMontage(RayOutro, 1, false);
		}
	});
	// 녹스 번개: 두 손 사이에서 줄 위 첫 대상의 몸(없으면 사거리 끝)까지 매번 새로 긋는다. 쏠 때마다 손 위치와 대상을 다시 읽는다.
	if (NoxStyle != 10)
	{
		PrepareNoxLayers(NoxStyle);
	}
	UE_LOG(LogTemp, Display, TEXT("GIDEON_VARIANT skill=F style=%d"), NoxStyle);
	// 10: 시전 때 커서에 가장 가까운 적 하나(없으면 조준선 첫 대상)를 정해 번개 동안 그 적만 따라가며 꽂고 피해도 그 적에게만 준다
	// (「한 명한테 집중해서 꽂히는 방식」 10-20). 줄 위 첫 대상을 매번 다시 고르면 커서가 적에서 조금만 벗어나도 바닥에 떨어졌다.
	const bool bFocus = NoxStyle == 10;
	TWeakObjectPtr<AActor> Locked;
	if (bFocus)
	{
		Locked = FindFocusTarget(Cursor, Feet, End);
		UE_LOG(LogTemp, Display, TEXT("GIDEON_BOLT lock=%s"), Locked.IsValid() ? *Locked->GetName() : TEXT("none"));
	}
	int32 Frame = 0;
	for (float Start = 0.0f; Start < RaySeconds; Start += NoxRefreshSeconds)
	{
		After(Start + 0.01f, [this, Feet, End, Strike, Cursor, Locked, Start, Index = Frame++, Generation = CastGeneration]()
		{
			if (!bCasting || Generation != CastGeneration)
			{
				return;
			}
			// 10: 손→대상 줄기 없이 콰앙 궁극기 번개를 정해 둔 적(없거나 사라지면 커서 자리) 바닥에 내리친다.
			if (NoxStyle == 10)
			{
				if (OriginalBolt && Index % FMath::Max(FMath::RoundToInt(OriginalBoltInterval / NoxRefreshSeconds), 1) == 0)
				{
					const AActor* Focus = Locked.Get();
					const FVector Ground = Focus ? FVector(Focus->GetActorLocation().X, Focus->GetActorLocation().Y, Feet.Z) : Cursor;
					UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), OriginalBolt, Ground, FRotator::ZeroRotator, FVector(OriginalBoltScale));
					UE_LOG(LogTemp, Display, TEXT("GIDEON_BOLT at=%s target=%s"), *Ground.ToCompactString(), Focus ? *Focus->GetName() : TEXT("none"));
				}
				return;
			}
			const FVector From = GetRayHands();
			const AActor* Target = FindRayTarget(Feet, End);
			const FVector To = Target ? Target->GetActorLocation() : Strike;
			if (NoxStyle == 4)
			{
				if (Index % FMath::Max(FMath::RoundToInt(DeathRayInterval / NoxRefreshSeconds), 1) == 0)
				{
					EmitDeathRay(From, To);
				}
				return;
			}
			if (NoxStyle == 9)
			{
				DrawNoxBolt(From, To, 0.0f);
				return;
			}
			if (NoxStyle >= 5)
			{
				if (Index % NoxParagonEvery == 0)
				{
					DrawNoxBolt(From, To, 0.0f);
				}
				if (Index % NoxParagonSparkEvery == 0)
				{
					if (RayArc)
					{
						UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), RayArc, To, FRotator::ZeroRotator, FVector(NoxParagonArcScale));
					}
					if (PrimaryMuzzle)
					{
						UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), PrimaryMuzzle, From, (To - From).Rotation(), FVector(NoxParagonFlashScale));
					}
				}
				return;
			}
			DrawNoxBolt(From, To, FMath::Fmod(Start, NoxPulseSeconds) / NoxPulseSeconds);
			AddNoxSparks(From, NoxEndSparks);
			AddNoxSparks(To, NoxEndSparks);
		});
	}
	After(RaySeconds + 0.02f, [this]() { ClearNoxBolt(); });
	// 피해는 번개가 꽂히는 한 대상에게만(10은 정해 둔 적, 나머지는 줄 위 첫 대상).
	for (int32 Tick = 0; Tick < RayTicks; ++Tick)
	{
		After(Tick * RaySeconds / RayTicks + 0.01f, [this, Feet, End, Direction, bFocus, Locked]()
		{
			AActor* Target = bFocus ? Locked.Get() : FindRayTarget(Feet, End);
			if (!Target)
			{
				UE_LOG(LogTemp, Display, TEXT("GIDEON_RAY tick target=none"));
				return;
			}
			if (Target->CanBeDamaged())
			{
				FHitResult Hit(Target, nullptr, Target->GetActorLocation(), -Direction);
				UGameplayStatics::ApplyPointDamage(Target, Skills[EGideonSkill::VoidRay].Damage, Direction, Hit,
					Character.IsValid() ? Character->GetController() : nullptr, GetOwner(), nullptr);
			}
			UE_LOG(LogTemp, Display, TEXT("GIDEON_RAY tick target=%s"), *Target->GetName());
		});
	}
	UE_LOG(LogTemp, Display, TEXT("GIDEON_RAY from=%s to=%s"), *Feet.ToCompactString(), *End.ToCompactString());
}

void UGideonSkillComponent::PrepareNoxLayers(int32 Style)
{
	// 층: 0 흰 심, 1 빛무리, 2·3 곁가지, 4 불티. 처음 한 번 만들고 시안마다 색만 바꾼다.
	if (NoxLayers.IsEmpty() && GetOwner() && NoxSegmentMesh && NoxSparkMesh && NoxBoltMaterial)
	{
		for (int32 Layer = 0; Layer < 5; ++Layer)
		{
			UInstancedStaticMeshComponent* Mesh = NewObject<UInstancedStaticMeshComponent>(GetOwner());
			Mesh->SetStaticMesh(Layer == 4 ? NoxSparkMesh.Get() : NoxSegmentMesh.Get());
			Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			Mesh->SetCastShadow(false);
			Mesh->SetMobility(EComponentMobility::Movable);
			Mesh->SetUsingAbsoluteLocation(true);
			Mesh->SetUsingAbsoluteRotation(true);
			Mesh->SetUsingAbsoluteScale(true);
			Mesh->SetWorldTransform(FTransform::Identity);
			Mesh->SetMaterial(0, UMaterialInstanceDynamic::Create(NoxBoltMaterial, Mesh));
			Mesh->RegisterComponent();
			NoxLayers.Add(Mesh);
		}
	}
	// 녹스 색(sRGB): 파랑 = 심 흰·빛무리 128,128,255·곁가지 128,128,255 / 64,64,255·불티 200,200,255,
	// 노랑 = 심 흰·빛무리 255,255,0, 초록 = 심 40,225,40·빛무리 150,220,150·곁가지 30,160,30 / 60,140,60, 데스레이 불티 보라(VioletSpark, 색 짐작).
	const FColor Colors[4][5] = {
		{ FColor(255, 255, 255), FColor(128, 128, 255), FColor(128, 128, 255), FColor(64, 64, 255), FColor(200, 200, 255) },
		{ FColor(255, 255, 255), FColor(255, 255, 0), FColor(255, 255, 0), FColor(255, 255, 0), FColor(255, 255, 120) },
		{ FColor(40, 225, 40), FColor(150, 220, 150), FColor(30, 160, 30), FColor(60, 140, 60), FColor(120, 255, 120) },
		{ FColor(255, 255, 255), FColor(190, 100, 255), FColor(190, 100, 255), FColor(190, 100, 255), FColor(190, 100, 255) } };
	const float Intensities[5] = { NoxCoreIntensity, NoxGlowIntensity, NoxSideIntensity, NoxSideIntensity, NoxSparkIntensity };
	// 줄 조각 층(0~3): 녹스 시안(1~4)은 원통 + 녹스 빛 재질, 6은 본줄기 층에 방전 재질 띠, 7은 콰앙 번개 재질 띠(본줄기·곁가지).
	bNoxStrips = Style >= 6 && NoxStripMesh;
	// 8은 7의 본줄기 띠 + 5의 곁가지 광선. 9는 부드러운 빛 띠(본줄기·넓은 번짐·곁가지 둘) + 카메라를 향한 둥근 불티.
	bNoxSoftSparks = Style == 9 && NoxGlowStripMaterial && NoxSoftSparkMaterial;
	for (int32 Layer = 0; Layer < FMath::Min(NoxLayers.Num(), 4); ++Layer)
	{
		UMaterialInterface* Material = Style == 6 ? NoxDischargeMaterial.Get() : Style == 9 ? NoxGlowStripMaterial.Get() :
			Style >= 7 ? NoxBoltStripMaterial.Get() : NoxBoltMaterial.Get();
		NoxLayers[Layer]->SetStaticMesh(bNoxStrips ? NoxStripMesh.Get() : NoxSegmentMesh.Get());
		NoxLayers[Layer]->SetMaterial(0, UMaterialInstanceDynamic::Create(Material ? Material : NoxBoltMaterial.Get(), NoxLayers[Layer]));
	}
	if (NoxLayers.Num() >= 5)
	{
		NoxLayers[4]->SetStaticMesh(bNoxSoftSparks ? NoxStripMesh.Get() : NoxSparkMesh.Get());
		NoxLayers[4]->SetMaterial(0, UMaterialInstanceDynamic::Create(bNoxSoftSparks ? NoxSoftSparkMaterial.Get() : NoxBoltMaterial.Get(), NoxLayers[4]));
	}
	if (Style == 9)
	{
		// 녹스 파랑: 심 흰·빛무리 128,128,255. 곁가지는 흰 심 없이 파랑만, 불티는 200,200,255.
		const FLinearColor Blue = FLinearColor::FromSRGBColor(FColor(128, 128, 255));
		const FLinearColor White(1.0f, 1.0f, 1.0f, 1.0f);
		const struct { FLinearColor Core; float CoreIntensity; float Sharpness; float GlowIntensity; } Strips[4] = {
			{ White, NoxSoftCoreIntensity, NoxSoftCoreSharpness, NoxSoftGlowIntensity },
			{ Blue, 0.0f, 1.0f, NoxSoftBloomIntensity },
			{ Blue, NoxSoftSideIntensity, 3.0f, NoxSoftSideIntensity * 0.3f },
			{ Blue, NoxSoftSideIntensity, 3.0f, NoxSoftSideIntensity * 0.3f } };
		for (int32 Layer = 0; Layer < FMath::Min(NoxLayers.Num(), 4); ++Layer)
		{
			if (UMaterialInstanceDynamic* Dynamic = Cast<UMaterialInstanceDynamic>(NoxLayers[Layer]->GetMaterial(0)))
			{
				Dynamic->SetVectorParameterValue(TEXT("CoreColor"), Strips[Layer].Core);
				Dynamic->SetScalarParameterValue(TEXT("CoreIntensity"), Strips[Layer].CoreIntensity);
				Dynamic->SetScalarParameterValue(TEXT("CoreSharpness"), Strips[Layer].Sharpness);
				Dynamic->SetVectorParameterValue(TEXT("GlowColor"), Blue);
				Dynamic->SetScalarParameterValue(TEXT("GlowIntensity"), Strips[Layer].GlowIntensity);
			}
		}
		if (NoxLayers.Num() >= 5)
		{
			if (UMaterialInstanceDynamic* Dynamic = Cast<UMaterialInstanceDynamic>(NoxLayers[4]->GetMaterial(0)))
			{
				Dynamic->SetVectorParameterValue(TEXT("Color"), FLinearColor::FromSRGBColor(FColor(150, 150, 255)));
				Dynamic->SetScalarParameterValue(TEXT("Intensity"), 3.0f);
			}
		}
		return;
	}
	for (int32 Layer = 0; Layer < NoxLayers.Num(); ++Layer)
	{
		if (UMaterialInstanceDynamic* Dynamic = Cast<UMaterialInstanceDynamic>(NoxLayers[Layer]->GetMaterial(0)))
		{
			Dynamic->SetVectorParameterValue(TEXT("Color"), FLinearColor::FromSRGBColor(Colors[FMath::Min(Style, 4) - 1][Layer]));
			Dynamic->SetScalarParameterValue(TEXT("Intensity"), Intensities[Layer]);
		}
	}
}

void UGideonSkillComponent::DrawNoxBolt(const FVector& From, const FVector& To, float PulsePhase)
{
	if (NoxLayers.Num() < 5)
	{
		return;
	}
	// 녹스는 화면에 긋는다 — 흔들기를 카메라의 가로·세로 축으로 한다(쿼터뷰에서 녹스와 같은 모양으로 보이게).
	FRotator View(-50.0f, 45.0f, 0.0f);
	if (const APlayerController* Viewer = Character.IsValid() ? Cast<APlayerController>(Character->GetController()) : nullptr)
	{
		if (Viewer->PlayerCameraManager)
		{
			View = Viewer->PlayerCameraManager->GetCameraRotation();
		}
	}
	const FRotationMatrix Axes(View);
	const FVector Right = Axes.GetUnitAxis(EAxis::Y);
	const FVector Up = Axes.GetUnitAxis(EAxis::Z);
	const float Length = FVector::Dist(From, To) / NoxPixel;
	const float Amplitude = (Length >= 512.0f ? 100.0f : 15.0f + Length * 85.0f / 512.0f) * NoxPixel;
	const int32 Steps = Length >= 256.0f ? 8 : Length >= 128.0f ? 7 : Length >= 64.0f ? 6 : 5;
	// 광선을 조각마다 하나씩 쓰는 시안(5·6)만 조각을 줄이고, 띠(7·8)는 녹스와 같이 잘게.
	const int32 Depth = FMath::Min(Steps, NoxStyle == 5 || NoxStyle == 6 ? NoxParagonDepth : NoxMaxDepth);
	const auto Strand = [&](TArray<FVector>& Points)
	{
		Points.Reset();
		Points.Add(From);
		// 단계 Level(1부터)의 가운데 흔들기 = ±Amplitude × (10/16)^Level, 가로·세로 따로. Depth 단계에서 멈춰 조각을 남긴다.
		TFunction<void(const FVector&, const FVector&, int32)> Split = [&](const FVector& A, const FVector& B, int32 Level)
		{
			if (Level >= Depth)
			{
				Points.Add(B);
				return;
			}
			const float Scale = Amplitude * FMath::Pow(10.0f / 16.0f, static_cast<float>(Level));
			const FVector Mid = (A + B) * 0.5f + Right * FMath::FRandRange(-Scale, Scale) + Up * FMath::FRandRange(-Scale, Scale);
			Split(A, Mid, Level + 1);
			Split(Mid, B, Level + 1);
		};
		Split(From, To, 1);
	};
	const FVector Toward = -Axes.GetUnitAxis(EAxis::X);
	const bool bStrips = bNoxStrips;
	const auto Lay = [Toward, bStrips](const TArray<FVector>& Points, float Width, TArray<FTransform>& Out)
	{
		for (int32 Index = 1; Index < Points.Num(); ++Index)
		{
			const FVector Segment = Points[Index] - Points[Index - 1];
			const float Size = Segment.Size();
			if (Size < KINDA_SMALL_NUMBER)
			{
				continue;
			}
			const FVector Middle = (Points[Index] + Points[Index - 1]) * 0.5f;
			if (bStrips)
			{
				// 엔진 기본 판 = 100×100(X·Y), 면이 Z. 길이를 X로, 면을 카메라 쪽으로 돌린다(U = 길이, V = 굵기).
				Out.Add(FTransform(FRotationMatrix::MakeFromXZ(Segment / Size, Toward).Rotator(), Middle, FVector(Size / 100.0f, Width / 100.0f, 1.0f)));
				continue;
			}
			// 엔진 기본 원통 = 높이 100(축 Z)·반지름 50.
			Out.Add(FTransform(FRotationMatrix::MakeFromZ(Segment / Size).Rotator(), Middle, FVector(Width / 100.0f, Width / 100.0f, Size / 100.0f)));
		}
	};
	TArray<FVector> Points;
	TArray<FVector> SidePointsA;
	TArray<FVector> SidePointsB;
	TArray<FTransform> Core, Glow, SideA, SideB;
	Strand(Points);
	if (NoxStyle != 2)
	{
		Strand(SidePointsA);
		Strand(SidePointsB);
	}
	if (NoxStyle == 9)
	{
		// 녹화 대조판: 본줄기(흰 심 + 파란 빛무리), 같은 줄의 넓고 옅은 번짐, 흰 심 없는 파란 곁가지 둘.
		Lay(Points, NoxSoftMainWidth, Core);
		Lay(Points, NoxSoftBloomWidth, Glow);
		Lay(SidePointsA, NoxSoftSideWidth, SideA);
		Lay(SidePointsB, NoxSoftSideWidth, SideB);
		// 둘레 불티는 본줄기 근처 아무 데나, 두 끝엔 짧게 남는 빛덩이.
		const double Now = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0;
		for (int32 Index = 0; Index < NoxSoftSparkles && Points.Num() > 1; ++Index)
		{
			FNoxSpark& Spark = NoxSparks.AddDefaulted_GetRef();
			Spark.Location = Points[FMath::RandRange(1, Points.Num() - 1)] +
				(Right * FMath::FRandRange(-1.0f, 1.0f) + Up * FMath::FRandRange(-1.0f, 1.0f)) * Amplitude * NoxSoftSparkleOffset;
			Spark.Velocity = FMath::VRand() * 40.0f;
			Spark.Born = Now;
			Spark.Life = NoxSoftSparkleLife * FMath::FRandRange(0.6f, 1.0f);
			Spark.Size = NoxSoftSparkleSize * FMath::FRandRange(0.6f, 1.3f);
		}
		for (int32 Side = 0; Side < 2; ++Side)
		{
			for (const float Fraction : { 1.0f, NoxSoftFlareCore })
			{
				FNoxSpark& Flare = NoxSparks.AddDefaulted_GetRef();
				Flare.Location = Side == 0 ? From : To;
				Flare.Born = Now;
				Flare.Life = NoxRefreshSeconds * 1.6f;
				Flare.Size = (Side == 0 ? NoxSoftHandFlare : NoxSoftTargetFlare) * Fraction;
			}
		}
		RefreshTickEnabled();
	}
	else if (NoxStyle >= 5)
	{
		// 파라곤 시안: 5·6은 꺾인 조각마다 콰앙 번개 광선, 6은 본줄기 아래 방전 띠, 7은 콰앙 번개 재질 띠.
		const auto Beams = [this](const TArray<FVector>& Strip, float Scale)
		{
			for (int32 Index = 1; Index < Strip.Num(); ++Index)
			{
				if (UParticleSystemComponent* Bolt = SpawnTimedEffect(RayBolt, Strip[Index - 1], (Strip[Index] - Strip[Index - 1]).Rotation(), Scale,
					NoxBeamSeconds))
				{
					Bolt->SetBeamSourcePoint(0, Strip[Index - 1], 0);
					Bolt->SetBeamTargetPoint(0, Strip[Index], 0);
				}
			}
		};
		if (NoxStyle <= 6)
		{
			Beams(Points, NoxBeamMainScale);
			Beams(SidePointsA, NoxBeamSideScale);
			Beams(SidePointsB, NoxBeamSideScale);
		}
		if (NoxStyle == 6)
		{
			Lay(Points, NoxDischargeWidth, Core);
		}
		if (NoxStyle == 7)
		{
			Lay(Points, NoxBoltStripWidth, Core);
			Lay(SidePointsA, NoxBoltStripSideWidth, SideA);
			Lay(SidePointsB, NoxBoltStripSideWidth, SideB);
		}
		if (NoxStyle == 8)
		{
			// 곁가지 광선은 조각을 줄여(입자 수) 다시 그린다.
			Lay(Points, NoxBoltStripSideWidth + 3.0f, Core);
			TArray<FVector> Coarse;
			for (int32 Side = 0; Side < 2; ++Side)
			{
				Coarse.Reset();
				const int32 Stride = 1 << FMath::Max(NoxMaxDepth - NoxParagonDepth, 0);
				const TArray<FVector>& Source = Side == 0 ? SidePointsA : SidePointsB;
				for (int32 Index = 0; Index < Source.Num(); Index += Stride)
				{
					Coarse.Add(Source[Index]);
				}
				Coarse.Add(Source.Last());
				Beams(Coarse, NoxBeamMainScale);
			}
		}
	}
	else
	{
		// 노랑은 심 굵기가 줄었다 늘었다 한다(녹스는 남은 수명 값으로 굵기를 정한다). 파랑·초록은 1px 심.
		const float CoreWidth = NoxStyle == 2 ? FMath::Lerp(NoxPulseMax, NoxPulseMin, PulsePhase) : NoxCoreWidth;
		Lay(Points, CoreWidth, Core);
		Lay(Points, NoxGlowWidth + (NoxStyle == 2 ? CoreWidth : 0.0f), Glow);
		if (NoxStyle != 2)
		{
			Lay(SidePointsA, NoxSideWidth, SideA);
			Lay(SidePointsB, NoxSideWidth, SideB);
		}
	}
	TArray<FTransform>* Sets[4] = { &Core, &Glow, &SideA, &SideB };
	for (int32 Layer = 0; Layer < 4; ++Layer)
	{
		NoxLayers[Layer]->ClearInstances();
		NoxLayers[Layer]->AddInstances(*Sets[Layer], false, true);
	}
}

void UGideonSkillComponent::AddNoxSparks(const FVector& At, int32 Count)
{
	const double Now = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0;
	for (int32 Index = 0; Index < Count; ++Index)
	{
		FNoxSpark& Spark = NoxSparks.AddDefaulted_GetRef();
		Spark.Location = At;
		Spark.Velocity = FMath::VRand() * NoxEndSparkSpeed;
		Spark.Born = Now;
		Spark.Life = NoxEndSparkLife;
		Spark.Size = NoxEndSparkSize;
	}
	RefreshTickEnabled();
}

void UGideonSkillComponent::EmitDeathRay(const FVector& From, const FVector& To)
{
	// 녹스 데스레이: 일직선에 녹스 2px마다 보라 불티, 높이·위아래 흔들림·수명은 불티마다 따로.
	const double Now = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0;
	const float Length = FVector::Dist(From, To);
	const int32 Count = FMath::Max(FMath::RoundToInt(Length / (2.0f * NoxPixel)), 1);
	for (int32 Index = 0; Index <= Count; ++Index)
	{
		FNoxSpark& Spark = NoxSparks.AddDefaulted_GetRef();
		Spark.Location = FMath::Lerp(From, To, static_cast<float>(Index) / Count) + FVector(0.0f, 0.0f, FMath::FRandRange(-DeathRayLift, DeathRayLift));
		Spark.Velocity = FVector(0.0f, 0.0f, FMath::FRandRange(-DeathRayDrift, DeathRayDrift));
		Spark.Born = Now;
		Spark.Life = FMath::FRandRange(DeathRayLifeMin, DeathRayLifeMax);
		Spark.Size = DeathRaySparkSize;
	}
	RefreshTickEnabled();
	UE_LOG(LogTemp, Display, TEXT("GIDEON_DEATHRAY sparks=%d"), Count + 1);
}

void UGideonSkillComponent::UpdateNoxSparks(float DeltaTime)
{
	if (NoxSparks.IsEmpty() || NoxLayers.Num() < 5 || !GetWorld())
	{
		return;
	}
	// 불티는 수명 동안 날아가며 작아진다. 시안 9는 둥근 빛 판을 카메라 쪽으로 돌린다.
	const double Now = GetWorld()->GetTimeSeconds();
	TArray<FTransform> Transforms;
	FRotator Facing = FRotator::ZeroRotator;
	if (bNoxSoftSparks)
	{
		FRotator View(-50.0f, 45.0f, 0.0f);
		if (const APlayerController* Viewer = Character.IsValid() ? Cast<APlayerController>(Character->GetController()) : nullptr)
		{
			if (Viewer->PlayerCameraManager)
			{
				View = Viewer->PlayerCameraManager->GetCameraRotation();
			}
		}
		Facing = FRotationMatrix::MakeFromZ(-View.Vector()).Rotator();
	}
	for (int32 Index = NoxSparks.Num() - 1; Index >= 0; --Index)
	{
		FNoxSpark& Spark = NoxSparks[Index];
		const float Age = static_cast<float>(Now - Spark.Born);
		if (Age >= Spark.Life)
		{
			NoxSparks.RemoveAtSwap(Index);
			continue;
		}
		Spark.Location += Spark.Velocity * DeltaTime;
		// 엔진 기본 공 = 지름 100, 판 = 100×100.
		const float Size = Spark.Size / 100.0f * (1.0f - Age / Spark.Life);
		Transforms.Add(FTransform(Facing, Spark.Location, bNoxSoftSparks ? FVector(Size, Size, 1.0f) : FVector(Size)));
	}
	NoxLayers[4]->ClearInstances();
	NoxLayers[4]->AddInstances(Transforms, false, true);
	if (NoxSparks.IsEmpty())
	{
		RefreshTickEnabled();
	}
}

void UGideonSkillComponent::ClearNoxBolt()
{
	for (int32 Layer = 0; Layer < FMath::Min(NoxLayers.Num(), 4); ++Layer)
	{
		NoxLayers[Layer]->ClearInstances();
	}
}

FVector UGideonSkillComponent::GetRayHands() const
{
	// 두 손을 모아 앞으로 뻗는 자세라 번개는 두 손 사이 조금 앞에서 나간다.
	const FVector Forward = Character.IsValid() ? Character->GetActorForwardVector() : FVector::ForwardVector;
	return (GetSocketLocation(TEXT("hand_l")) + GetSocketLocation(TEXT("hand_r"))) * 0.5f + Forward * RayHandAhead;
}

AActor* UGideonSkillComponent::FindRayTarget(const FVector& From, const FVector& To) const
{
	// 줄(폭 RayWidth) 안에서 시전자에게 가장 가까운 대상.
	TArray<AActor*> Candidates;
	GatherTargets((From + To) * 0.5f, FVector::Dist2D(From, To) * 0.5f + RayWidth, Candidates);
	const FVector FlatTo(To.X, To.Y, From.Z);
	const FVector Along = (FlatTo - From).GetSafeNormal();
	AActor* Best = nullptr;
	float BestDistance = TNumericLimits<float>::Max();
	for (AActor* Candidate : Candidates)
	{
		const FVector Flat(Candidate->GetActorLocation().X, Candidate->GetActorLocation().Y, From.Z);
		const float Distance = FVector::DotProduct(Flat - From, Along);
		if (Distance >= 0.0f && Distance < BestDistance && FMath::PointDistToSegment(Flat, From, FlatTo) <= RayWidth)
		{
			Best = Candidate;
			BestDistance = Distance;
		}
	}
	return Best;
}

AActor* UGideonSkillComponent::FindFocusTarget(const FVector& Cursor, const FVector& Feet, const FVector& End) const
{
	// 커서 둘레(BoltLockRadius)에서 커서에 가장 가까운 대상, 없으면 조준선 첫 대상(F 10·11).
	TArray<AActor*> Near;
	GatherTargets(Cursor, BoltLockRadius, Near);
	AActor* Locked = nullptr;
	float Best = TNumericLimits<float>::Max();
	for (AActor* Candidate : Near)
	{
		const float Distance = FVector::DistSquared2D(Candidate->GetActorLocation(), Cursor);
		if (Distance < Best)
		{
			Best = Distance;
			Locked = Candidate;
		}
	}
	return Locked ? Locked : FindRayTarget(Feet, End);
}

ECharacterSkillTargeting UGideonSkillComponent::GetSkillTargeting(int32 Slot) const
{
	return Slot >= 0 && Slot < SlotCount && RequiresTarget(static_cast<EGideonSkill>(Slot)) ? ECharacterSkillTargeting::Actor
		: ECharacterSkillTargeting::Direction;
}

bool UGideonSkillComponent::IsSkillTargetValid(int32 Slot, const AActor* Target, const AActor* Caster) const
{
	// 기본 규칙(Pawn만)과 달리 수련장 허수아비도 대상으로 친다(오로라와 같다).
	return IsCombatTarget(Target, Caster) && Target->CanBeDamaged();
}

bool UGideonSkillComponent::RequiresTarget(EGideonSkill Skill) const
{
	// A 시안 8은 대상을 찍는 광선이었다가 10-21 도우미(자기 자신에게 쓰는 버프)로 바뀌어 대상이 필요 없다.
	return Skill == EGideonSkill::PortalVolley;
}

AActor* UGideonSkillComponent::PickSkillTarget(AActor* Hovered, const FVector& Cursor) const
{
	// 입력이 커서 아래에서 고른 대상이 우선이다. 발밑 바닥을 찍었을 때를 위해 커서 둘레(TargetPickRadius)에서 가장 가까운 것까지 본다.
	if (IsSkillTargetValid(0, Hovered, GetOwner()))
	{
		return Hovered;
	}
	TArray<AActor*> Near;
	GatherTargets(Cursor, TargetPickRadius, Near);
	AActor* Best = nullptr;
	float BestDistance = TNumericLimits<float>::Max();
	for (AActor* Candidate : Near)
	{
		const float Distance = FVector::DistSquared2D(Candidate->GetActorLocation(), Cursor);
		if (Candidate->CanBeDamaged() && Distance < BestDistance)
		{
			Best = Candidate;
			BestDistance = Distance;
		}
	}
	return Best;
}

void UGideonSkillComponent::ExecuteNewSkillDraft(int32 Draft)
{
	// A 자리 새 스킬 러프 시안(10-20). 모양만 보이려는 것이라 수치·그림 모두 임시값이고, 피해는 A 피해를 나눠 쓴다.
	// 1차 표(gideon-41st-anew-*)에서 「A1·A4는 별로」 → 1 중력장(V 장판과 닮음)·4 고리 투척은 뺐다.
	//  2 별 궤도: 4초 동안 평타 보라 탄 셋이 몸 둘레를 돌며 닿는 적을 때림(같은 적은 0.5초에 한 번)
	//  3 연쇄 별탄: 커서 둘레 적에게 혜성을 던지고, 맞은 적에서 가장 가까운 적으로 두 번 더 튐(튈 때마다 피해 0.8배)
	//  5 분열 혜성: 혜성이 길 위 첫 적(없으면 커서 자리)에서 터지며 별 조각 여덟이 사방으로 흩어짐(조각마다 피해 0.35배)
	//  6 끌어오는 별: 혜성에 맞은 적을 A 줄로 묶어 몸 앞까지 끌어옴(피해는 혜성 한 번)
	//  7 빛줄기 휩쓸기: 몸 앞에서 뻗은 보라 빛줄기가 앞쪽을 한쪽 끝에서 반대쪽 끝으로 쓸며 닿는 적을 한 번씩 때림
	//  8 대상 고정 광선: 찍은 적 하나에 광선을 2초 붙잡고 0.2초마다 때림(그림은 시안 7 빛줄기)
	constexpr float OrbitSeconds = 4.0f;
	constexpr float OrbitRadius = 160.0f;
	constexpr float OrbitSpin = 300.0f;
	constexpr float OrbitHitRadius = 70.0f;
	// 500은 수련장 허수아비 사이보다 짧아 한 번도 안 튐(gideon-41st-anew-* `chain targets=1`) → 900.
	constexpr float ChainHop = 900.0f;
	constexpr float ChainSpeed = 2200.0f;
	constexpr int32 SplitShards = 8;
	constexpr float SplitReach = 450.0f;
	constexpr float SplitSpeed = 1500.0f;
	constexpr float PullSeconds = 0.4f;
	constexpr float PullStop = 180.0f;
	constexpr float SweepSeconds = 0.8f;
	constexpr float SweepArc = 55.0f;
	// 750은 수련장 허수아비(약 850 앞)에 못 닿음(gideon-42nd-anew-* `sweep hits=0`) → 900. 43차에 두 손 모은 자세로 바꾸며 뿌리가
	// 몸 앞 70 → 22로 당겨져 몸에서 닿는 거리가 970 → 922(로그 reach), 맞던 허수아비 하나를 놓침 → 950(몸에서 약 972).
	constexpr float SweepLength = 950.0f;
	constexpr float SweepWidth = 60.0f;
	if (!Character.IsValid() || !GetWorld())
	{
		return;
	}
	const FGideonSkillDefinition& Definition = Skills[EGideonSkill::Burden];
	const float Damage = Definition.Damage;
	FTimerManager& Timers = GetWorld()->GetTimerManager();
	Timers.ClearTimer(ADraftTimer);
	const FVector Feet = GetFeetLocation();
	const FVector Direction = (ActiveAim - Character->GetActorLocation()).GetSafeNormal2D();
	UE_LOG(LogTemp, Display, TEXT("GIDEON_ANEW draft=%d"), Draft);
	const auto Hit = [this](AActor* Target, float Amount, const FVector& From)
	{
		if (!IsValid(Target) || !Target->CanBeDamaged() || !Character.IsValid())
		{
			return;
		}
		const FVector Away = (Target->GetActorLocation() - From).GetSafeNormal2D();
		FHitResult Result(Target, nullptr, Target->GetActorLocation(), -Away);
		UGameplayStatics::ApplyPointDamage(Target, Amount, Away, Result, Character->GetController(), GetOwner(), nullptr);
		if (PrimaryHitCharacter)
		{
			UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), PrimaryHitCharacter, Target->GetActorLocation(), Away.Rotation(), FVector(1.5f));
		}
	};
	switch (Draft)
	{
	case 2:
	{
		struct FOrbit
		{
			TArray<TWeakObjectPtr<UParticleSystemComponent>> Stars;
			TMap<const AActor*, double> LastHit;
			double Start = 0.0;
		};
		const TSharedRef<FOrbit> State = MakeShared<FOrbit>();
		State->Start = GetWorld()->GetTimeSeconds();
		for (int32 Index = 0; Index < 3 && StarTrail; ++Index)
		{
			if (UParticleSystemComponent* Star = SpawnOwnedEffect(StarTrail, Character->GetActorLocation()))
			{
				Star->SetWorldScale3D(FVector(1.6f));
				State->Stars.Add(Star);
			}
		}
		Timers.SetTimer(ADraftTimer, FTimerDelegate::CreateWeakLambda(this, [this, State, Damage, Hit]()
		{
			const double Now = GetWorld()->GetTimeSeconds();
			const float Age = static_cast<float>(Now - State->Start);
			if (Age > OrbitSeconds || !Character.IsValid())
			{
				for (const TWeakObjectPtr<UParticleSystemComponent>& Star : State->Stars)
				{
					ReleaseOwnedEffect(Star.Get());
				}
				GetWorld()->GetTimerManager().ClearTimer(ADraftTimer);
				return;
			}
			const FVector Center = Character->GetActorLocation() + FVector(0.0f, 0.0f, 10.0f);
			for (int32 Index = 0; Index < State->Stars.Num(); ++Index)
			{
				UParticleSystemComponent* Star = State->Stars[Index].Get();
				if (!Star)
				{
					continue;
				}
				const float Angle = FMath::DegreesToRadians(Age * OrbitSpin + Index * 120.0f);
				const FVector At = Center + FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.0f) * OrbitRadius;
				Star->SetWorldLocationAndRotation(At, FVector(-FMath::Sin(Angle), FMath::Cos(Angle), 0.0f).Rotation());
				TArray<AActor*> Targets;
				GatherTargets(At, OrbitHitRadius, Targets);
				for (AActor* Target : Targets)
				{
					const double* Last = State->LastHit.Find(Target);
					if (!Last || Now - *Last >= 0.5)
					{
						State->LastHit.Add(Target, Now);
						Hit(Target, Damage * 0.3f, Center);
						UE_LOG(LogTemp, Display, TEXT("GIDEON_ANEW orbit hit=%s"), *Target->GetName());
					}
				}
			}
		}), 0.02f, true);
		break;
	}
	case 3:
	{
		const FVector Cursor = Feet + (FVector(ActiveAim.X, ActiveAim.Y, Feet.Z) - Feet).GetClampedToMaxSize(Definition.Range);
		TArray<AActor*> Chain;
		if (AActor* First = FindFocusTarget(Cursor, Feet, Feet + Direction * Definition.Range))
		{
			Chain.Add(First);
		}
		while (!Chain.IsEmpty() && Chain.Num() < 3)
		{
			TArray<AActor*> Near;
			GatherTargets(Chain.Last()->GetActorLocation(), ChainHop, Near);
			AActor* Next = nullptr;
			float Best = TNumericLimits<float>::Max();
			for (AActor* Candidate : Near)
			{
				const float Distance = FVector::DistSquared2D(Candidate->GetActorLocation(), Chain.Last()->GetActorLocation());
				if (!Chain.Contains(Candidate) && Distance < Best)
				{
					Best = Distance;
					Next = Candidate;
				}
			}
			if (!Next)
			{
				break;
			}
			Chain.Add(Next);
		}
		UE_LOG(LogTemp, Display, TEXT("GIDEON_ANEW chain targets=%d"), Chain.Num());
		if (Chain.IsEmpty())
		{
			LaunchProjectile(EGideonProjectileKind::Primary, TEXT("Muzzle_01"), ActiveAim, ChainSpeed, Definition.Range, Damage,
				BurdenProjectile, BurdenHitCharacter, nullptr, BurdenNoHit);
			break;
		}
		// 앞 대상의 몸 안에서 쏘면 그 대상에 다시 맞으므로 다음 대상 쪽으로 몸 밖까지 내밀어 출발한다.
		FVector From = GetSocketLocation(TEXT("Muzzle_01"));
		float Delay = 0.0f;
		float Scale = 1.0f;
		for (AActor* Target : Chain)
		{
			const FVector To = Target->GetActorLocation();
			const float Distance = FVector::Dist2D(From, To);
			After(Delay + 0.01f, [this, From, To, Distance, Amount = Damage * Scale]()
			{
				LaunchProjectileFrom(EGideonProjectileKind::Primary, From, To, ChainSpeed, Distance + 150.0f, Amount,
					BurdenProjectile, BurdenHitCharacter, nullptr, nullptr);
			});
			Delay += Distance / ChainSpeed;
			Scale *= 0.8f;
			From = To;
			if (Target != Chain.Last())
			{
				const AActor* Next = Chain[Chain.IndexOfByKey(Target) + 1];
				From += (Next->GetActorLocation() - To).GetSafeNormal2D() * 90.0f;
			}
		}
		break;
	}
	case 5:
	{
		const FVector Hand = GetSocketLocation(TEXT("Muzzle_01"));
		const FVector Cursor = Feet + (FVector(ActiveAim.X, ActiveAim.Y, Feet.Z) - Feet).GetClampedToMaxSize(Definition.Range);
		// 혜성 길 위에 적이 있으면 그 적에서, 없으면 커서 자리에서 터진다.
		const AActor* First = FindRayTarget(Feet, Cursor);
		const FVector Burst = First ? First->GetActorLocation() : FVector(Cursor.X, Cursor.Y, Character->GetActorLocation().Z);
		const FVector Travel = (Burst - Hand).GetSafeNormal2D();
		const float Distance = FVector::Dist2D(Hand, Burst);
		LaunchProjectileFrom(EGideonProjectileKind::Primary, Hand, Burst, ChainSpeed, First ? Distance + 150.0f : Distance, Damage,
			BurdenProjectile, BurdenHitCharacter, nullptr, nullptr);
		After(Distance / ChainSpeed, [this, Burst, Travel, Damage]()
		{
			if (RiftBlast)
			{
				UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), RiftBlast, Burst, FRotator::ZeroRotator, FVector(0.45f));
			}
			int32 Launched = 0;
			for (int32 Index = 0; Index < SplitShards; ++Index)
			{
				const FVector Out = Travel.RotateAngleAxis(360.0f * Index / SplitShards, FVector::UpVector);
				// 터진 적의 몸 안에서 출발하면 그 적에 다시 맞으므로 몸 밖에서 출발한다(연쇄 별탄과 같은 까닭).
				const FVector From = Burst + Out * 90.0f;
				if (LaunchProjectileFrom(EGideonProjectileKind::Primary, From, From + Out * SplitReach, SplitSpeed, SplitReach, Damage * 0.35f,
					StarTrail, PrimaryHitCharacter, PrimaryHitWorld, PrimaryNoHit))
				{
					++Launched;
				}
			}
			UE_LOG(LogTemp, Display, TEXT("GIDEON_ANEW split at=%s shards=%d"), *Burst.ToCompactString(), Launched);
		});
		break;
	}
	case 6:
	{
		const FVector Hand = GetSocketLocation(TEXT("Muzzle_01"));
		const FVector Cursor = Feet + (FVector(ActiveAim.X, ActiveAim.Y, Feet.Z) - Feet).GetClampedToMaxSize(Definition.Range);
		AActor* Target = FindFocusTarget(Cursor, Feet, Feet + Direction * Definition.Range);
		// 이미 몸 앞에 붙어 있으면 끌 게 없으니 혜성만 맞힌다.
		if (!Target || FVector::Dist2D(Target->GetActorLocation(), Character->GetActorLocation()) <= PullStop + 20.0f)
		{
			LaunchProjectile(EGideonProjectileKind::Primary, TEXT("Muzzle_01"), ActiveAim, ChainSpeed, Definition.Range, Damage,
				BurdenProjectile, BurdenHitCharacter, nullptr, BurdenNoHit);
			UE_LOG(LogTemp, Display, TEXT("GIDEON_ANEW pull target=none"));
			break;
		}
		const float Distance = FVector::Dist2D(Hand, Target->GetActorLocation());
		LaunchProjectileFrom(EGideonProjectileKind::Primary, Hand, Target->GetActorLocation(), ChainSpeed, Distance + 150.0f, Damage,
			BurdenProjectile, BurdenHitCharacter, nullptr, nullptr);
		After(Distance / ChainSpeed, [this, Weak = TWeakObjectPtr<AActor>(Target)]()
		{
			AActor* Live = Weak.Get();
			if (!Live || !Character.IsValid() || !GetWorld())
			{
				return;
			}
			struct FPull
			{
				TWeakObjectPtr<AActor> Target;
				TWeakObjectPtr<USplineMeshComponent> Tether;
				FVector Start = FVector::ZeroVector;
				double Born = 0.0;
			};
			const TSharedRef<FPull> State = MakeShared<FPull>();
			State->Target = Live;
			State->Tether = SpawnBurdenTether();
			State->Start = Live->GetActorLocation();
			State->Born = GetWorld()->GetTimeSeconds();
			SetStatus(Live, TEXT("SLOW"), 1.0f);
			// 수련장 허수아비는 블랙홀·R처럼 잠시 뒤 제자리로 돌린다(RestoreBlackHoleTargets).
			if (!BlackHolePendingRestore.ContainsByPredicate([Live](const FBlackHoleTarget& Entry) { return Entry.Actor.Get() == Live; }))
			{
				FBlackHoleTarget& Entry = BlackHolePendingRestore.AddDefaulted_GetRef();
				Entry.Actor = Live;
				Entry.Origin = State->Start;
			}
			GetWorld()->GetTimerManager().SetTimer(ADraftTimer, FTimerDelegate::CreateWeakLambda(this, [this, State]()
			{
				AActor* Pulled = State->Target.Get();
				USplineMeshComponent* Tether = State->Tether.Get();
				const float Progress = FMath::Min(static_cast<float>(GetWorld()->GetTimeSeconds() - State->Born) / PullSeconds, 1.0f);
				if (Pulled && Character.IsValid())
				{
					const FVector Body = Character->GetActorLocation();
					FVector Stop = Body + (State->Start - Body).GetSafeNormal2D() * PullStop;
					Stop.Z = State->Start.Z;
					// 처음엔 천천히, 끝으로 갈수록 빨리 끌려온다. 캡슐은 쓸기 이동이 바닥에 걸리므로 R 밀기처럼 순간 이동으로 옮긴다.
					Pulled->SetActorLocation(FMath::Lerp(State->Start, Stop, Progress * Progress), false, nullptr, ETeleportType::TeleportPhysics);
					if (Tether)
					{
						const FVector Hand = GetSocketLocation(TEXT("Muzzle_01"));
						const FVector To = Pulled->GetActorLocation();
						Tether->SetStartAndEnd(Hand, To - Hand, To, To - Hand, true);
					}
				}
				if (Progress >= 1.0f || !Pulled || !Character.IsValid())
				{
					if (Tether)
					{
						Tether->DestroyComponent();
					}
					if (Pulled && BurdenHitCharacter)
					{
						UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), BurdenHitCharacter, Pulled->GetActorLocation());
					}
					UE_LOG(LogTemp, Display, TEXT("GIDEON_ANEW pull done target=%s moved=%.0f"), *GetNameSafe(Pulled),
						Pulled ? FVector::Dist2D(State->Start, Pulled->GetActorLocation()) : 0.0f);
					FTimerManager& Manager = GetWorld()->GetTimerManager();
					Manager.SetTimer(BlackHoleRestoreTimer, this, &UGideonSkillComponent::RestoreBlackHoleTargets, BlackHoleRestoreDelay, false);
					// 도는 중인 타이머를 지우면 이 람다가 그 자리에서 지워지므로 맨 끝에(휩쓸기와 같은 까닭).
					Manager.ClearTimer(ADraftTimer);
				}
			}), 0.02f, true);
		});
		break;
	}
	case 7:
	{
		// 10-20 「A7 느낌 괜찮은데 광선 느낌으로 — 디테일·이펙트 신경」: 빛 점 줄(구슬 꿴 줄로 보임) → 띠 광선(M_Gideon_SweepBeam).
		//  모으기(SweepCharge): 모은 두 손으로 보라 점이 소용돌이쳐 빨려 들고 손 빛덩이가 커진다
		//  쏘기: 손 섬광·불티와 함께 굵기가 빠르게 차오르고, 몸이 빛줄기를 따라 돌며 ±SweepArc를 쓴다. 굵기는 잘게 떨린다
		//  끝: 손에서 비스듬히 내려 바닥에 닿은 끝이 불티를 튀기고, 빛나는 그을음 자국을 호로 남긴다(다 쓴 뒤 함께 사그라짐).
		//      벽(바닥이 아닌 고정 물체)에 막히면 벽에서 끊긴다
		//  맞음: 적마다 한 번 피해 + 섬광 + 불티. 다 쓸면 굵기가 접히고 손 섬광과 함께 손을 내린다
		struct FSweep
		{
			TSet<const AActor*> Struck;
			FVector LastScorch = FVector(TNumericLimits<float>::Max());
			float Yaw = 0.0f;
			float Floor = 0.0f;
			double Start = 0.0;
			double LastBurst = 0.0;
			uint32 Generation = 0;
			int32 WallTicks = 0;
			int32 Ticks = 0;
			float Reach = 0.0f;
			bool bFired = false;
		};
		const TSharedRef<FSweep> State = MakeShared<FSweep>();
		State->Start = GetWorld()->GetTimeSeconds();
		State->Yaw = Direction.Rotation().Yaw;
		State->Floor = Feet.Z;
		State->Generation = CastGeneration;
		// 다 쓸 때까지 시전을 붙잡고(움직이면 몸 돌림과 싸운다), 두 손을 앞으로 모은 자세를 그동안 되풀이한다.
		Timers.SetTimer(RecoveryTimer, this, &UGideonSkillComponent::FinishCast, SweepCharge + SweepSeconds + 0.05f, false);
		PlayCastMontage(SweepHold, 100, true);
		const FVector ChargeAt = GetRayHands();
		for (int32 Index = 0; Index < 18; ++Index)
		{
			const FVector Offset = FMath::VRand() * FMath::FRandRange(70.0f, 120.0f);
			AddSpiralDot(ChargeAt, Offset, 540.0f, SweepCharge * FMath::FRandRange(0.8f, 1.0f), FMath::FRandRange(14.0f, 22.0f), 3.0f);
		}
		Timers.SetTimer(ADraftTimer, FTimerDelegate::CreateWeakLambda(this, [this, State, Damage, Hit]()
		{
			const double Now = GetWorld()->GetTimeSeconds();
			const float Age = static_cast<float>(Now - State->Start);
			// 다른 시전으로 끊기면(세대가 바뀜) 바로 접는다.
			const bool bCancelled = !Character.IsValid() || CastGeneration != State->Generation;
			const FVector Hands = Character.IsValid() ? GetRayHands() : FVector::ZeroVector;
			if (Age < SweepCharge && !bCancelled)
			{
				DrawSweepBeam(Hands, Hands, 0.0f, Age / SweepCharge);
				return;
			}
			const float Shot = Age - SweepCharge;
			if (Shot >= SweepSeconds || bCancelled)
			{
				ClearSweepBeam();
				if (Character.IsValid())
				{
					if (PrimaryMuzzle)
					{
						UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), PrimaryMuzzle, Hands, Character->GetActorRotation(), FVector(1.2f));
					}
					for (int32 Index = 0; Index < 10; ++Index)
					{
						AddGlowDot(Hands, FMath::VRand() * FMath::FRandRange(120.0f, 220.0f), FMath::FRandRange(0.2f, 0.4f), FMath::FRandRange(10.0f, 16.0f));
					}
					if (!bCancelled)
					{
						PlayCastMontage(SweepOutro, 1, false);
					}
				}
				UE_LOG(LogTemp, Display, TEXT("GIDEON_ANEW sweep hits=%d cancelled=%d ticks=%d wall_ticks=%d reach=%.0f"), State->Struck.Num(),
					bCancelled ? 1 : 0, State->Ticks, State->WallTicks, State->Reach);
				// 도는 중인 타이머를 지우면 이 람다(붙잡은 값 포함)가 그 자리에서 지워진다(TimerManager.cpp ETimerStatus::Executing) — 지우기는 맨 끝에.
				GetWorld()->GetTimerManager().ClearTimer(ADraftTimer);
				return;
			}
			// 양 끝에서 느리고 가운데에서 가장 빠르게. 몸이 빛줄기를 따라 돌아 뿌리가 모은 손에 붙어 있다.
			const float Eased = 0.5f - 0.5f * FMath::Cos(Shot / SweepSeconds * PI);
			const float Yaw = State->Yaw + (2.0f * Eased - 1.0f) * SweepArc;
			const FVector Along = FRotator(0.0f, Yaw, 0.0f).Vector();
			Character->SetActorRotation(FRotator(0.0f, Yaw, 0.0f));
			const FVector From = GetRayHands();
			const FVector Body = Character->GetActorLocation();
			++State->Ticks;
			if (!State->bFired)
			{
				State->bFired = true;
				if (PrimaryMuzzle)
				{
					UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), PrimaryMuzzle, From, Along.Rotation(), FVector(2.0f));
				}
				for (int32 Index = 0; Index < 14; ++Index)
				{
					AddGlowDot(From, FMath::VRand() * FMath::FRandRange(150.0f, 320.0f), FMath::FRandRange(0.2f, 0.4f), FMath::FRandRange(10.0f, 18.0f));
				}
			}
			// 길이는 손에서 잰다(몸 중심에서 재면 손 앞 거리만큼 짧아져 맞던 허수아비 하나를 놓쳤다, gideon-43rd-check-* hits 2 → 1).
			FVector To(From.X + Along.X * SweepLength, From.Y + Along.Y * SweepLength, State->Floor + 10.0f);
			bool bWall = false;
			FHitResult Block;
			FCollisionQueryParams Query(SCENE_QUERY_STAT(GideonSweepBeam), false, Character.Get());
			if (GetWorld()->LineTraceSingleByObjectType(Block, From, To, FCollisionObjectQueryParams(ECC_WorldStatic), Query) && Block.ImpactNormal.Z < 0.7f)
			{
				To = Block.ImpactPoint;
				bWall = true;
				++State->WallTicks;
			}
			State->Reach = FMath::Max(State->Reach, static_cast<float>(FVector::Dist2D(Body, To)));
			// 쏠 때 빠르게 차오르고(SweepGrow), 끝에 접히고(SweepCollapse), 그사이엔 잘게 떨린다.
			const float Grow = FMath::Min(Shot / SweepGrow, 1.0f);
			const float Collapse = FMath::Min((SweepSeconds - Shot) / SweepCollapse, 1.0f);
			const float Width = SweepBeamWidth * (1.0f - FMath::Square(1.0f - Grow)) * Collapse * (1.0f + 0.08f * FMath::Sin(Shot * 2.0f * PI * 11.0f));
			DrawSweepBeam(From, To, Width, Collapse);
			for (int32 Index = 0; Index < 3; ++Index)
			{
				const FVector Spray = (FMath::VRand() + FVector(0.0f, 0.0f, 1.2f)).GetSafeNormal() * FMath::FRandRange(150.0f, 380.0f);
				AddGlowDot(To, Spray, FMath::FRandRange(0.25f, 0.45f), FMath::FRandRange(9.0f, 16.0f));
			}
			if (Now - State->LastBurst >= 0.1 && PrimaryHitWorld)
			{
				UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), PrimaryHitWorld, To, FRotator::ZeroRotator, FVector(0.7f));
				State->LastBurst = Now;
			}
			if (!bWall)
			{
				const FVector Ground(To.X, To.Y, State->Floor);
				AddGlowDot(Ground + FVector(0.0f, 0.0f, 6.0f), FVector::ZeroVector, 0.5f, 34.0f);
				if (FVector::Dist2D(Ground, State->LastScorch) >= SweepScorchGap)
				{
					State->LastScorch = Ground;
					// D 바닥 자국 1번처럼 테두리가 보라로 빛나는 그을음. 다 쓴 뒤 SweepScorchHold에 한꺼번에 사그라든다.
					if (UDecalComponent* Scorch = StarScorchMaterial ? UGameplayStatics::SpawnDecalAtLocation(GetWorld(), StarScorchMaterial,
						FVector(60.0f, SweepScorchSize, SweepScorchSize), Ground, FRotator(-90.0f, FMath::FRandRange(0.0f, 360.0f), 0.0f)) : nullptr)
					{
						const float Hold = SweepSeconds - Shot + SweepScorchHold;
						Scorch->SetFadeScreenSize(0.0f);
						Scorch->SetFadeOut(Hold, SweepScorchFade, false);
						Scorch->SetLifeSpan(Hold + SweepScorchFade + 0.1f);
						if (UMaterialInstanceDynamic* Dynamic = Scorch->CreateDynamicMaterialInstance())
						{
							Dynamic->SetScalarParameterValue(TEXT("GlowIntensity"), 7.0f);
							Dynamic->SetScalarParameterValue(TEXT("GlowSharpness"), 1.5f);
							Dynamic->SetScalarParameterValue(TEXT("Opacity"), 0.7f);
						}
					}
					for (int32 Index = 0; Index < 2; ++Index)
					{
						AddGlowDot(Ground + FVector(FMath::FRandRange(-20.0f, 20.0f), FMath::FRandRange(-20.0f, 20.0f), 5.0f),
							FVector(FMath::FRandRange(-10.0f, 10.0f), FMath::FRandRange(-10.0f, 10.0f), FMath::FRandRange(25.0f, 60.0f)),
							FMath::FRandRange(0.8f, 1.4f), 12.0f);
					}
				}
			}
			const FVector Root(From.X, From.Y, Body.Z);
			const FVector Tip(To.X, To.Y, Body.Z);
			TArray<AActor*> Targets;
			GatherTargets((Root + Tip) * 0.5f, FVector::Dist2D(Root, Tip) * 0.5f + SweepWidth, Targets);
			for (AActor* Target : Targets)
			{
				const FVector At = Target->GetActorLocation();
				if (!State->Struck.Contains(Target) && FMath::PointDistToSegment(FVector(At.X, At.Y, Body.Z), Root, Tip) <= SweepWidth)
				{
					State->Struck.Add(Target);
					Hit(Target, Damage, Root);
					for (int32 Index = 0; Index < 10; ++Index)
					{
						AddGlowDot(At, FMath::VRand() * FMath::FRandRange(180.0f, 360.0f), FMath::FRandRange(0.2f, 0.4f), FMath::FRandRange(10.0f, 16.0f));
					}
				}
			}
		}), 0.016f, true);
		break;
	}
	case 8:
	{
		// 10-21 「A 너무 짧아서 아쉬움 — 따로 버프 스킬로 빼고, A를 누르면 캐릭터를 도와주는 오브젝트 같은 게 하나 나와서 공격할 때마다
		//  우리가 지금 쓰는 A를 사용해 주는 느낌」: 평타 1타로 손을 내지르면(HelperSummonAt) 손에서 빛 구슬(도우미)이 튀어나와 어깨 위에 떠서
		//  HelperSeconds 동안 따라다니고, 평타를 쏠 때마다 한 발 광선(바로 앞까지의 A — HelperShoot)을 쏴 준다. 시전은 부른 직후 끝나 바로 움직인다.
		//  바로 앞까지의 A = 대상을 찍어 모았다 쏘는 한 발 광선(10-21 「녹스 데스 레이처럼 딱 한 발만 팡」), 그 전 = 2초 붙잡는 광선(10-20).
		//  번개를 섞은 시안 1~12(Gideon.Skills.ABeam)는 「번개 빔 다 별로」 → 「광선으로」(10-20)로 지웠다(gideon-skills-progress.md 45~56차).
		SummonHelper();
		Timers.SetTimer(RecoveryTimer, this, &UGideonSkillComponent::FinishCast, 0.05f, false);
		break;
	}
	default:
		break;
	}
}

void UGideonSkillComponent::SummonHelper()
{
	// 손에서 튀어나와 HelperFlyIn 동안 어깨 위 자리로 날아간다. 떠 있는 동안 다시 부르면 남은 시간만 새로 채운다.
	const double Now = GetWorld()->GetTimeSeconds();
	const FVector Hand = GetSocketLocation(TEXT("Muzzle_01"));
	HelperEnd = Now + HelperSeconds;
	if (!HelperOrb.IsValid())
	{
		if (UParticleSystemComponent* Orb = SpawnOwnedEffect(PrimaryProjectile, Hand))
		{
			Orb->SetWorldScale3D(FVector(HelperOrbScale));
			HelperOrb = Orb;
		}
		HelperFrom = Hand;
		HelperAt = Hand;
		HelperStart = Now;
		HelperShots = 0;
		HelperHits = 0;
	}
	if (PrimaryMuzzle)
	{
		UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), PrimaryMuzzle, Hand, Character->GetActorRotation(), FVector(1.5f));
	}
	for (int32 Index = 0; Index < 16; ++Index)
	{
		AddGlowDot(Hand, FMath::VRand() * FMath::FRandRange(120.0f, 280.0f), FMath::FRandRange(0.2f, 0.4f), FMath::FRandRange(8.0f, 14.0f));
	}
	HelperLastTick = Now;
	GetWorld()->GetTimerManager().SetTimer(HelperTimer, this, &UGideonSkillComponent::UpdateHelper, 0.016f, true);
	UE_LOG(LogTemp, Display, TEXT("GIDEON_HELPER summon seconds=%.1f"), HelperSeconds);
}

void UGideonSkillComponent::UpdateHelper()
{
	UParticleSystemComponent* Orb = HelperOrb.Get();
	const double Now = GetWorld()->GetTimeSeconds();
	if (!Character.IsValid() || !Orb || Now >= HelperEnd)
	{
		// 시간이 다 되면 구슬 자리에서 작게 터지며 흩어진다(꼬리는 뿜기만 멈춰 사그라들게).
		if (Orb)
		{
			if (PrimaryHitWorld)
			{
				UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), PrimaryHitWorld, HelperAt, FRotator::ZeroRotator, FVector(0.7f));
			}
			for (int32 Index = 0; Index < 14; ++Index)
			{
				AddGlowDot(HelperAt, FMath::VRand() * FMath::FRandRange(120.0f, 260.0f), FMath::FRandRange(0.2f, 0.4f), FMath::FRandRange(8.0f, 14.0f));
			}
			ReleaseOwnedEffect(Orb);
		}
		HelperOrb.Reset();
		UE_LOG(LogTemp, Display, TEXT("GIDEON_HELPER end shots=%d hits=%d"), HelperShots, HelperHits);
		GetWorld()->GetTimerManager().ClearTimer(HelperTimer);
		return;
	}
	const float DeltaTime = FMath::Clamp(static_cast<float>(Now - HelperLastTick), 0.0f, 0.1f);
	HelperLastTick = Now;
	const float Age = static_cast<float>(Now - HelperStart);
	// 자리 = 화면 기준(카메라의 오른쪽·안쪽) 머리 오른쪽 위. 날아온 뒤에는 조금 늦게 따라붙어(HelperFollow) 몸에 박혀 있지 않게 보인다.
	// 처음엔 캐릭터가 보는 쪽 기준이라 돌아설 때마다 구슬이 몸을 빙 돌아 반대편으로 휘돌았다(10-21 「움직일 때 궤적이 좀 이상하게
	// 움직이는 것 같은데」). 위아래 일렁임은 서 있을 때만 — 걸을 때도 일렁이면 꼬리가 물결처럼 그려졌다.
	FVector ScreenRight = Character->GetActorRightVector();
	FVector ScreenIn = -Character->GetActorForwardVector();
	if (const APlayerController* Viewer = Cast<APlayerController>(Character->GetController()))
	{
		if (Viewer->PlayerCameraManager)
		{
			const FRotationMatrix View(FRotator(0.0f, Viewer->PlayerCameraManager->GetCameraRotation().Yaw, 0.0f));
			ScreenRight = View.GetUnitAxis(EAxis::Y);
			ScreenIn = View.GetUnitAxis(EAxis::X);
		}
	}
	const float Still = 1.0f - FMath::Clamp(static_cast<float>(Character->GetVelocity().Size2D()) / HelperBobStopSpeed, 0.0f, 1.0f);
	const FVector Home = Character->GetActorLocation() + ScreenRight * HelperRight + ScreenIn * HelperBack +
		FVector(0.0f, 0.0f, HelperUp + HelperBob * Still * FMath::Sin(Age * 2.0f * PI * HelperBobHz));
	const FVector Previous = HelperAt;
	HelperAt = Age < HelperFlyIn ? FMath::Lerp(HelperFrom, Home, 1.0f - FMath::Square(1.0f - Age / HelperFlyIn)) :
		FMath::Lerp(HelperAt, Home, 1.0f - FMath::Exp(-HelperFollow * DeltaTime));
	// 구슬 그림(평타 탄)은 앞축으로 날아가는 모양이라 가는 쪽으로 천천히 돌려 꼬리가 지나온 쪽으로 늘어지게 한다(D 유성과 같이).
	// 처음엔 돌리지 않아 꼬리가 늘 한쪽(월드 축)으로 뻗었다. 거의 멈춰 있으면 마지막 방향 그대로.
	const FVector Move = HelperAt - Previous;
	if (DeltaTime > 0.0f && Move.Size() > HelperTurnSpeed * DeltaTime)
	{
		Orb->SetWorldRotation(FMath::RInterpTo(Orb->GetComponentRotation(), Move.Rotation(), DeltaTime, HelperTurnRate));
	}
	Orb->SetWorldLocation(HelperAt);
	// 구슬 둘레에 작은 빛 점이 잠깐씩 맺혔다 사라진다.
	if (FMath::FRand() < 0.5f)
	{
		AddGlowDot(HelperAt + FMath::VRand() * FMath::FRandRange(10.0f, 30.0f), FMath::VRand() * 20.0f, FMath::FRandRange(0.25f, 0.45f),
			FMath::FRandRange(6.0f, 10.0f));
	}
}

void UGideonSkillComponent::HelperAssist(AActor* Target)
{
	if (!HelperOrb.IsValid() || !IsValid(Target) || !GetWorld())
	{
		return;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	if (Now - HelperLastAssist < HelperAssistGap)
	{
		return;
	}
	HelperLastAssist = Now;
	After(HelperShotDelay, [this, Weak = TWeakObjectPtr<AActor>(Target), At = Target->GetActorLocation()]()
	{
		HelperShoot(At, Weak.Get());
	});
}

void UGideonSkillComponent::HelperShoot(const FVector& Aim, AActor* Preferred)
{
	UParticleSystemComponent* Orb = HelperOrb.Get();
	if (!Orb || !Character.IsValid() || !GetWorld())
	{
		return;
	}
	// 쏠 대상: 스킬이 맞힌 대상(Preferred), 아니면 커서 아래·둘레(PickSkillTarget), 없으면 몸 → 커서 방향 줄 위 첫 대상(FindRayTarget).
	// 모두 사거리(HelperRange) 안. 대상이 없으면 커서 바닥(사거리까지)에 꽂는다. 벽이 가리면 벽에서 끊기고 안 맞는다.
	const FVector From = Orb->GetComponentLocation();
	const FVector Body = Character->GetActorLocation();
	const FVector Flat = (FVector(Aim.X, Aim.Y, Body.Z) - Body).GetSafeNormal2D();
	const FVector Direction = Flat.IsNearlyZero() ? Character->GetActorForwardVector() : Flat;
	AActor* Target = IsValid(Preferred) && Preferred->CanBeDamaged() ? Preferred : PickSkillTarget(nullptr, Aim);
	if (!Target || FVector::Dist2D(Target->GetActorLocation(), Body) > HelperRange)
	{
		Target = FindRayTarget(Body, Body + Direction * HelperRange);
	}
	FVector To = Target ? Target->GetActorLocation() : FVector(Body.X, Body.Y, Aim.Z) + Direction * FMath::Min(FVector::Dist2D(Aim, Body), HelperRange);
	bool bWall = false;
	FHitResult Block;
	FCollisionQueryParams Query(SCENE_QUERY_STAT(GideonHelperRay), false, Character.Get());
	if (GetWorld()->LineTraceSingleByObjectType(Block, From, To, FCollisionObjectQueryParams(ECC_WorldStatic), Query) && Block.ImpactNormal.Z < 0.7f)
	{
		To = Block.ImpactPoint;
		bWall = true;
	}
	const FVector Dir = (To - From).GetSafeNormal();
	// 구슬: 평타 총구 섬광 + 불티. 닿은 자리: 평타 바닥 터짐 + 위로 튀는 불티(맞으면 평타 명중 섬광도).
	if (PrimaryMuzzle)
	{
		UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), PrimaryMuzzle, From, Dir.Rotation(), FVector(1.2f));
	}
	for (int32 Index = 0; Index < 8; ++Index)
	{
		AddGlowDot(From, FMath::VRand() * FMath::FRandRange(120.0f, 260.0f), FMath::FRandRange(0.15f, 0.3f), FMath::FRandRange(8.0f, 14.0f));
	}
	if (PrimaryHitWorld)
	{
		UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), PrimaryHitWorld, To, FRotator::ZeroRotator, FVector(0.8f));
	}
	for (int32 Index = 0; Index < 12; ++Index)
	{
		const FVector Spray = (FMath::VRand() + FVector(0.0f, 0.0f, 1.2f)).GetSafeNormal() * FMath::FRandRange(200.0f, 420.0f);
		AddGlowDot(To, Spray, FMath::FRandRange(0.25f, 0.4f), FMath::FRandRange(9.0f, 14.0f));
	}
	const bool bHit = Target && !bWall && Target->CanBeDamaged();
	const float Damage = Skills[EGideonSkill::Burden].Damage * HelperShotDamage;
	if (bHit)
	{
		const FVector Away = Dir.GetSafeNormal2D();
		FHitResult Result(Target, nullptr, To, -Away);
		UGameplayStatics::ApplyPointDamage(Target, Damage, Away, Result, Character->GetController(), GetOwner(), nullptr);
		if (PrimaryHitCharacter)
		{
			UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), PrimaryHitCharacter, To, (-Dir).Rotation(), FVector(1.0f));
		}
		++HelperHits;
	}
	++HelperShots;
	UE_LOG(LogTemp, Display, TEXT("GIDEON_HELPER shot=%d from=%s target=%s hit=%d wall=%d damage=%.0f"), HelperShots,
		Preferred ? TEXT("skill") : TEXT("basic"), Target ? *Target->GetName() : TEXT("none"), bHit, bWall, bHit ? Damage : 0.0f);
	// 광선: 처음엔 굵고 양 끝이 크게 터졌다가(Flash) 잠깐 그대로 있고, 가늘어지며(Fade) 사라진다. 쏘는 끝은 따라다니는 구슬에 붙는다.
	// 새로 쏘면 앞 광선의 타이머를 덮어 바로 갈아 끼운다(빛줄기 층이 하나뿐이다).
	const double Start = GetWorld()->GetTimeSeconds();
	const auto Draw = [this, Start, From, To]()
	{
		const float Shot = static_cast<float>(GetWorld()->GetTimeSeconds() - Start);
		const float Flash = FMath::Clamp(1.0f - Shot / DeathRayFlashSeconds, 0.0f, 1.0f);
		const float Fade = FMath::Clamp((Shot - DeathRayHold) / DeathRayFade, 0.0f, 1.0f);
		const float Width = SweepBeamWidth * LockBeamWidth * FMath::Lerp(1.0f, DeathRayFlashWidth, Flash) * FMath::Square(1.0f - Fade);
		const FVector Origin = HelperOrb.IsValid() ? HelperOrb->GetComponentLocation() : From;
		DrawSweepBeam(Origin, To, Width, FMath::Lerp(LockBeamFlare, DeathRayFlare, Flash) * (1.0f - Fade), LockBeamCoreSharpness);
		return Shot >= DeathRayHold + DeathRayFade;
	};
	Draw();
	GetWorld()->GetTimerManager().SetTimer(ADraftTimer, FTimerDelegate::CreateWeakLambda(this, [this, Draw]()
	{
		if (Draw())
		{
			ClearSweepBeam();
			// 도는 중인 타이머를 지우면 이 람다(붙잡은 값 포함)가 그 자리에서 지워진다(TimerManager.cpp ETimerStatus::Executing) — 지우기는 맨 끝에.
			GetWorld()->GetTimerManager().ClearTimer(ADraftTimer);
		}
	}), 0.016f, true);
}

void UGideonSkillComponent::DrawSweepBeam(const FVector& From, const FVector& To, float Width, float Flare, float CoreSharpness)
{
	// 층: 0 흰 심 + 보라 빛무리 + 흐르는 가닥, 1 같은 재질의 넓고 옅은 번짐, 2 양 끝 빛덩이(둥근 불티 재질). 처음 쓸 때 만든다.
	if (SweepLayers.IsEmpty() && GetOwner() && NoxStripMesh && SweepBeamMaterial && NoxSoftSparkMaterial)
	{
		for (int32 Layer = 0; Layer < 3; ++Layer)
		{
			UInstancedStaticMeshComponent* Mesh = NewObject<UInstancedStaticMeshComponent>(GetOwner());
			Mesh->SetStaticMesh(NoxStripMesh);
			Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			Mesh->SetCastShadow(false);
			Mesh->SetMobility(EComponentMobility::Movable);
			Mesh->SetUsingAbsoluteLocation(true);
			Mesh->SetUsingAbsoluteRotation(true);
			Mesh->SetUsingAbsoluteScale(true);
			Mesh->SetWorldTransform(FTransform::Identity);
			UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(Layer < 2 ? SweepBeamMaterial.Get() : NoxSoftSparkMaterial.Get(), Mesh);
			if (Layer < 2)
			{
				Material->SetScalarParameterValue(TEXT("FlipU"), SweepBeamFlipU);
			}
			if (Layer == 1)
			{
				// 번짐은 흰 심·가는 실 없이 옅은 보라와 느슨한 가닥만, 무늬는 굵기에 맞춰 덜 되풀이한다.
				Material->SetScalarParameterValue(TEXT("CoreIntensity"), 0.0f);
				Material->SetScalarParameterValue(TEXT("GlowIntensity"), 0.7f);
				Material->SetScalarParameterValue(TEXT("GlowSoftness"), 2.5f);
				Material->SetScalarParameterValue(TEXT("StrandIntensity"), 0.8f);
				Material->SetScalarParameterValue(TEXT("FilamentIntensity"), 0.0f);
				Material->SetScalarParameterValue(TEXT("FlowTiling"), 1.5f);
				Material->SetScalarParameterValue(TEXT("Wobble"), 0.12f);
				Material->SetScalarParameterValue(TEXT("TipFade"), 0.25f);
			}
			if (Layer == 2)
			{
				Material->SetVectorParameterValue(TEXT("Color"), FLinearColor::FromSRGBColor(FColor(235, 205, 255)));
				Material->SetScalarParameterValue(TEXT("Intensity"), 5.0f);
			}
			Mesh->SetMaterial(0, Material);
			Mesh->RegisterComponent();
			SweepLayers.Add(Mesh);
		}
	}
	if (SweepLayers.Num() < 3)
	{
		return;
	}
	if (UMaterialInstanceDynamic* CoreMaterial = Cast<UMaterialInstanceDynamic>(SweepLayers[0]->GetMaterial(0)))
	{
		CoreMaterial->SetScalarParameterValue(TEXT("CoreSharpness"), CoreSharpness);
	}
	FRotator View(-50.0f, 45.0f, 0.0f);
	if (const APlayerController* Viewer = Character.IsValid() ? Cast<APlayerController>(Character->GetController()) : nullptr)
	{
		if (Viewer->PlayerCameraManager)
		{
			View = Viewer->PlayerCameraManager->GetCameraRotation();
		}
	}
	const FVector Toward = -View.Vector();
	TArray<FTransform> Core;
	TArray<FTransform> Bloom;
	const FVector Segment = To - From;
	const float Length = Segment.Size();
	if (Length > 1.0f && Width > 0.5f)
	{
		// 엔진 기본 판 = 100×100(X·Y), 면이 Z. 길이를 X로, 면을 카메라 쪽으로 돌린다(DrawNoxBolt와 같다).
		const FRotator Facing = FRotationMatrix::MakeFromXZ(Segment / Length, Toward).Rotator();
		const FVector Middle = (From + To) * 0.5f;
		Core.Add(FTransform(Facing, Middle, FVector(Length / 100.0f, Width / 100.0f, 1.0f)));
		Bloom.Add(FTransform(Facing, Middle, FVector(Length / 100.0f, Width * SweepBloomScale / 100.0f, 1.0f)));
	}
	// 손 빛덩이(크고 옅은 것 + 작고 진한 것 겹침)와 끝 빛덩이. 크기가 잘게 흔들려 깜빡인다.
	TArray<FTransform> Flares;
	const FRotator FlareFacing = FRotationMatrix::MakeFromZ(Toward).Rotator();
	const auto AddFlare = [&Flares, &FlareFacing](const FVector& At, float Size)
	{
		const float Scale = Size * FMath::FRandRange(0.9f, 1.1f) / 100.0f;
		Flares.Add(FTransform(FlareFacing, At, FVector(Scale, Scale, 1.0f)));
	};
	if (Flare > 0.0f)
	{
		AddFlare(From, 150.0f * Flare);
		AddFlare(From, 60.0f * Flare);
		if (Length > 1.0f)
		{
			AddFlare(To, 120.0f * Flare);
			AddFlare(To, 45.0f * Flare);
		}
	}
	const TArray<FTransform>* Sets[3] = { &Core, &Bloom, &Flares };
	for (int32 Layer = 0; Layer < 3; ++Layer)
	{
		SweepLayers[Layer]->ClearInstances();
		SweepLayers[Layer]->AddInstances(*Sets[Layer], false, true);
	}
}

void UGideonSkillComponent::ClearSweepBeam()
{
	for (UInstancedStaticMeshComponent* Layer : SweepLayers)
	{
		if (Layer)
		{
			Layer->ClearInstances();
		}
	}
}

void UGideonSkillComponent::ExecuteFocusBolt(const FVector& Feet, const FVector& End, const FVector& Cursor, int32 Style)
{
	// F 11~15: 고정한 적(없으면 커서 자리)에 FocusChargeSeconds 동안 힘을 모은 뒤 한 방. 손으로 찍고 바로 움직인다(FocusMoveAfter).
	// 시안(10-20 「전체적으로 퀄리티 아쉬움 — 신경 써서 시안 여러 개」)마다 모으는 그림·터지는 그림만 다르다(후보 단독 촬영 gideon-35th-ffx-*).
	//  11 보라 점이 곧게 모임 + 발밑 고리 → 콰앙 궁극기 번개 2배 + 평타 명중 섬광 + W 폭발(바로 앞까지 쓰던 것)
	//  12 Prime Helix 보라 모음 + 고리 → 콰앙 빛 강타(빛 알이 서고 한 점에 꽂히는 번개, 넓게 안 퍼짐) + Dekker 정지폭탄 충격파
	//  13 Prime Helix 보라 모음 + 고리 → 콰앙 궁극기 번개 1.2배(덜 퍼지게) + Dekker 하늘 빔 첫 터짐(흰 별빛) + 튀는 점
	//  14 대상 몸에 작은 블랙홀 + 소용돌이로 빨려 드는 점 → 블랙홀이 접히며 정지폭탄 충격파 + W 폭발(번개 없음, 기디언 결)
	//  15 고리 + 보라 점 모음 → 콰앙 궁극기 번개 1배를 FocusStrikeGap 간격 세 번 한 자리에(피해도 셋으로 나눔)
	FFocusLook Look;
	Look.Bolt = OriginalBolt;
	Look.Flash = PrimaryHitCharacter;
	Look.Blast = RiftBlast;
	switch (Style)
	{
	case 12:
		Look.Blast = nullptr;
		Look.Charge = FocusGather;
		Look.ChargeScale = 1.3f;
		Look.ChargeAt = FocusChargeSeconds - 0.6f;
		Look.bStraightDots = false;
		// 빛 강타는 띄우고 약 0.45초 뒤에 번개가 꽂힌다(단독 촬영 0.15초 빛 알 → 0.5초 번개).
		Look.Bolt = FocusLightStrike;
		Look.BoltScale = 0.45f;
		Look.BoltAt = FocusChargeSeconds - 0.45f;
		Look.Flash = FocusShockwave;
		Look.FlashScale = 0.55f;
		Look.BurstDots = 20;
		break;
	case 13:
		Look.Blast = nullptr;
		Look.Charge = FocusGather;
		Look.ChargeScale = 1.3f;
		Look.ChargeAt = FocusChargeSeconds - 0.6f;
		Look.Bolt = OriginalBolt;
		Look.BoltScale = 1.2f;
		Look.Flash = FocusStarBurst;
		Look.FlashScale = 0.5f;
		break;
	case 14:
		Look.Charge = BlackHole;
		Look.ChargeScale = FocusVoidScale;
		Look.bStraightDots = false;
		Look.bInflowDots = true;
		Look.bGrowCharge = true;
		Look.bCollapseCharge = true;
		Look.Bolt = nullptr;
		Look.Flash = FocusShockwave;
		Look.FlashScale = 0.7f * F14Shrink * F14Burst;
		Look.Blast = RiftBlast;
		Look.BlastScale = FocusBlastScale * F14Shrink * F14Burst;
		Look.BurstDots = F14BurstDots;
		Look.BurstSpeed = F14BurstSpeed;
		break;
	case 15:
		Look.BoltScale = 1.0f;
		Look.Strikes = 3;
		Look.Blast = nullptr;
		Look.BurstDots = 16;
		break;
	default:
		break;
	}
	const TWeakObjectPtr<AActor> Locked = FindFocusTarget(Cursor, Feet, End);
	UE_LOG(LogTemp, Display, TEXT("GIDEON_FOCUS style=%d lock=%s"), Style, Locked.IsValid() ? *Locked->GetName() : TEXT("none"));
	// 10-21 「F는 바로 움직일 수 있게 하자」: 찍는 동작(BeginCast의 평타 1타, 손 뻗기 0.173초)을 내지른 직후 시전을 끝내 바로 움직이고,
	// 모였다가 터지는 건 시전과 따로 끝까지 간다(아래 타이머들은 시전 세대가 아니라 캐릭터가 살아 있는지만 본다 — 캐릭터를 바꾸면
	// 캐릭터째 지워져 함께 멈춘다). 그 전엔 2초 동안 서서 모으고 터질 때 평타 2타로 다시 내질렀다(52차).
	GetWorld()->GetTimerManager().SetTimer(RecoveryTimer, this, &UGideonSkillComponent::FinishCast, FocusMoveAfter, false);
	// 대상의 몸 가운데와 발밑(대상이 움직이면 따라간다). 대상이 없거나 사라지면 커서 자리.
	const auto Spots = [Locked, Cursor](FVector& Body, FVector& Floor)
	{
		if (const AActor* Focus = Locked.Get())
		{
			Body = Focus->GetActorLocation();
			Floor = Body - FVector(0.0f, 0.0f, Focus->GetSimpleCollisionHalfHeight());
			return;
		}
		Floor = Cursor;
		Body = Cursor + FVector(0.0f, 0.0f, 90.0f);
	};
	// 모으는 이펙트는 몸 가운데에 띄워 아래 0.05초마다 대상을 따라 옮긴다.
	const TSharedRef<TWeakObjectPtr<UParticleSystemComponent>> Charge = MakeShared<TWeakObjectPtr<UParticleSystemComponent>>();
	if (Look.Charge)
	{
		After(Look.ChargeAt, [this, Spots, Look, Charge]()
		{
			if (!Character.IsValid())
			{
				return;
			}
			FVector Body;
			FVector Floor;
			Spots(Body, Floor);
			if (UParticleSystemComponent* Effect = SpawnOwnedEffect(Look.Charge, Body))
			{
				Effect->SetWorldScale3D(FVector(Look.ChargeScale));
				*Charge = Effect;
			}
		});
	}
	for (float Start = 0.0f; Start < FocusChargeSeconds; Start += NoxRefreshSeconds)
	{
		After(Start + 0.01f, [this, Spots, Look, Charge, Start]()
		{
			if (!Character.IsValid())
			{
				return;
			}
			FVector Body;
			FVector Floor;
			Spots(Body, Floor);
			if (UParticleSystemComponent* Effect = Charge->Get())
			{
				Effect->SetWorldLocation(Body);
				if (Look.bGrowCharge)
				{
					Effect->SetWorldScale3D(FVector(Look.ChargeScale * FMath::Lerp(FocusGrowFrom, 1.0f, Start / FocusChargeSeconds)));
				}
			}
			// F 14(FocusInflow* 설명): 껍질에서 곧장 물체로 날아가 닿으며 사라진다. 터지기 전에 닿도록 수명을 남은 시간 안으로 자른다.
			const float Left = FocusChargeSeconds - Start;
			for (int32 Index = 0; Look.bInflowDots && Left > 0.15f && Index < FocusInflowPerStep; ++Index)
			{
				FVector Out = FMath::VRand();
				Out.Z *= 0.5f;
				const FVector From = Body + Out.GetSafeNormal() * FocusInflowRadius * FMath::FRandRange(0.75f, 1.0f);
				const float Life = FMath::Min(FMath::FRandRange(FocusInflowLifeMin, FocusInflowLifeMax), Left);
				AddGlowDot(From, (Body - From) / Life, Life, FocusInflowSize);
			}
			// 옆·위 껍질에서 몸 가운데로 곧게 모여들며 작아진다.
			for (int32 Index = 0; Look.bStraightDots && Index < FocusGatherPerStep; ++Index)
			{
				FVector Out = FMath::VRand();
				Out.Z = FMath::Abs(Out.Z) * 0.8f;
				const FVector From = Body + Out.GetSafeNormal() * FocusGatherRadius;
				AddGlowDot(From, (Body - From) / FocusGatherLife, FocusGatherLife, FocusGatherSize);
			}
			// 둘레를 돌다가 터지기 직전에 한꺼번에 가운데(작은 블랙홀)로 모인다(블랙홀 시안 — 「주변 도는 이펙트들, 터지기 직전에
			// 오브젝트로 모이게」 10-20). 언제 띄웠든 수명을 터지는 때까지로 맞추고, 반지름을 (1 − t^FocusSpiralPull)로 줄여 끝에 몰아서 빨려 들게 한다.
			const float UntilStrike = FMath::Max(FocusChargeSeconds - Start, 0.15f);
			for (int32 Index = 0; Look.bSpiralDots && Index < FocusSpiralPerStep; ++Index)
			{
				const float Angle = FMath::FRandRange(0.0f, 2.0f * PI);
				const float Radius = FocusSpiralRadius * FMath::FRandRange(0.7f, 1.0f);
				const FVector Offset(FMath::Cos(Angle) * Radius, FMath::Sin(Angle) * Radius, FMath::FRandRange(-60.0f, 60.0f));
				AddSpiralDot(Body, Offset, SpiralDotSwirl * 1.5f, UntilStrike, FocusSpiralSize, FocusSpiralPull);
			}
			const float Spin = Start * FocusRingSpin;
			for (int32 Index = 0; Look.bRing && Index < FocusRingDots; ++Index)
			{
				const float Angle = FMath::DegreesToRadians(Spin + 360.0f * Index / FocusRingDots);
				AddGlowDot(Floor + FVector(FMath::Cos(Angle) * FocusRingRadius, FMath::Sin(Angle) * FocusRingRadius, 5.0f),
					FVector::ZeroVector, FocusRingLife, FocusRingSize);
			}
		});
	}
	// 미리 띄워야 제때 꽂히는 번개(빛 강타)는 꽂힐 시점에 맞춰 앞당겨 띄운다.
	if (Look.Bolt && Look.BoltAt < FocusChargeSeconds)
	{
		After(Look.BoltAt, [this, Spots, Look]()
		{
			if (!Character.IsValid())
			{
				return;
			}
			FVector Body;
			FVector Floor;
			Spots(Body, Floor);
			UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), Look.Bolt, Floor, FRotator::ZeroRotator, FVector(Look.BoltScale));
		});
	}
	for (int32 Strike = 0; Strike < Look.Strikes; ++Strike)
	{
		After(FocusChargeSeconds + Strike * FocusStrikeGap, [this, Spots, Locked, Look, Charge, Strike]()
		{
			if (!Character.IsValid())
			{
				return;
			}
			FVector Body;
			FVector Floor;
			Spots(Body, Floor);
			if (Strike == 0)
			{
				// 모은 것을 거둔다 — 블랙홀은 0.15초 동안 한 점으로 접어 지우고, 나머지는 뿜기만 멈춘다.
				if (UParticleSystemComponent* Effect = Charge->Get())
				{
					if (Look.bCollapseCharge)
					{
						OwnedEffects.Remove(Effect);
						for (int32 Step = 1; Step <= 3; ++Step)
						{
							After(Step * 0.05f, [Weak = TWeakObjectPtr<UParticleSystemComponent>(Effect), Scale = Look.ChargeScale * (1.0f - Step / 3.0f)]()
							{
								if (UParticleSystemComponent* Live = Weak.Get())
								{
									if (Scale <= 0.0f)
									{
										Live->DestroyComponent();
										return;
									}
									Live->SetWorldScale3D(FVector(Scale));
								}
							});
						}
					}
					else
					{
						ReleaseOwnedEffect(Effect);
					}
				}
			}
			if (Look.Bolt && Look.BoltAt >= FocusChargeSeconds)
			{
				UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), Look.Bolt, Floor, FRotator::ZeroRotator, FVector(Look.BoltScale));
			}
			if (Look.Flash)
			{
				UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), Look.Flash, Body, FRotator::ZeroRotator, FVector(Look.FlashScale));
			}
			if (Look.Blast)
			{
				UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), Look.Blast, Body, FRotator::ZeroRotator, FVector(Look.BlastScale));
			}
			for (int32 Index = 0; Index < Look.BurstDots; ++Index)
			{
				AddGlowDot(Body, FMath::VRand() * Look.BurstSpeed, FocusGatherLife, FocusGatherSize * 1.5f);
			}
			// 피해 10번(RayTicks)어치를 터지는 횟수로 나눠 준다.
			const float Damage = Skills[EGideonSkill::VoidRay].Damage * RayTicks / Look.Strikes;
			AActor* Focus = Locked.Get();
			if (Focus && Focus->CanBeDamaged() && Character.IsValid())
			{
				const FVector Direction = (Body - Character->GetActorLocation()).GetSafeNormal2D();
				FHitResult Hit(Focus, nullptr, Body, -Direction);
				UGameplayStatics::ApplyPointDamage(Focus, Damage, Direction, Hit, Character->GetController(), GetOwner(), nullptr);
				HelperAssist(Focus);
			}
			UE_LOG(LogTemp, Display, TEXT("GIDEON_FOCUS strike=%d target=%s damage=%.0f"), Strike, Focus ? *Focus->GetName() : TEXT("none"),
				Focus ? Damage : 0.0f);
		});
	}
}

UGideonSkillComponent::FGlowDot* UGideonSkillComponent::AddGlowDot(const FVector& At, const FVector& Velocity, float Life, float Size, float Age)
{
	// 카메라를 향한 둥근 빛 판 층은 처음 쓸 때 만든다(F 녹스 층과 따로).
	if (!GlowDotLayer && GetOwner() && NoxStripMesh && NoxSoftSparkMaterial)
	{
		GlowDotLayer = NewObject<UInstancedStaticMeshComponent>(GetOwner());
		GlowDotLayer->SetStaticMesh(NoxStripMesh);
		GlowDotLayer->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		GlowDotLayer->SetCastShadow(false);
		GlowDotLayer->SetMobility(EComponentMobility::Movable);
		GlowDotLayer->SetUsingAbsoluteLocation(true);
		GlowDotLayer->SetUsingAbsoluteRotation(true);
		GlowDotLayer->SetUsingAbsoluteScale(true);
		GlowDotLayer->SetWorldTransform(FTransform::Identity);
		UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(NoxSoftSparkMaterial, GlowDotLayer);
		Material->SetVectorParameterValue(TEXT("Color"), FLinearColor::FromSRGBColor(GlowDotColor));
		Material->SetScalarParameterValue(TEXT("Intensity"), GlowDotIntensity);
		GlowDotLayer->SetMaterial(0, Material);
		GlowDotLayer->RegisterComponent();
	}
	if (!GlowDotLayer)
	{
		return nullptr;
	}
	const bool bWasEmpty = GlowDots.IsEmpty();
	FGlowDot& Dot = GlowDots.AddDefaulted_GetRef();
	Dot.Location = At;
	Dot.Velocity = Velocity;
	Dot.Born = (GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0) - Age;
	Dot.Life = Life;
	Dot.Size = Size;
	if (bWasEmpty)
	{
		RefreshTickEnabled();
	}
	return &Dot;
}

void UGideonSkillComponent::AddSpiralDot(const FVector& Center, const FVector& Offset, float Swirl, float Life, float Size, float Pull)
{
	if (FGlowDot* Dot = AddGlowDot(Center + Offset, FVector::ZeroVector, Life, Size))
	{
		Dot->Center = Center;
		Dot->Offset = Offset;
		Dot->Swirl = Swirl;
		Dot->Pull = Pull;
	}
}

void UGideonSkillComponent::UpdateGlowDots(float DeltaTime)
{
	if (GlowDots.IsEmpty() || !GlowDotLayer || !GetWorld())
	{
		return;
	}
	// 수명 동안 날아가며 작아진다. 판은 카메라 쪽으로 돌린다.
	FRotator View(-50.0f, 45.0f, 0.0f);
	if (const APlayerController* Viewer = Character.IsValid() ? Cast<APlayerController>(Character->GetController()) : nullptr)
	{
		if (Viewer->PlayerCameraManager)
		{
			View = Viewer->PlayerCameraManager->GetCameraRotation();
		}
	}
	const FRotator Facing = FRotationMatrix::MakeFromZ(-View.Vector()).Rotator();
	const double Now = GetWorld()->GetTimeSeconds();
	TArray<FTransform> Transforms;
	Transforms.Reserve(GlowDots.Num());
	for (int32 Index = GlowDots.Num() - 1; Index >= 0; --Index)
	{
		FGlowDot& Dot = GlowDots[Index];
		const float Age = static_cast<float>(Now - Dot.Born);
		if (Age >= Dot.Life)
		{
			GlowDots.RemoveAtSwap(Index);
			continue;
		}
		const float Progress = Age / Dot.Life;
		// 소용돌이 점은 반지름이 (1 − t^Pull)로 줄어 처음엔 둘레를 돌다가 끝으로 갈수록 빨리 가운데로 빨려 들고, 크기도 같은 비율로 준다
		// (Pull이 클수록 끝에 한꺼번에 모인다). 나머지 점은 날아가며 수명 동안 고르게 작아진다.
		float Shrink = 1.0f - Progress;
		if (Dot.Swirl != 0.0f)
		{
			Shrink = 1.0f - FMath::Pow(Progress, Dot.Pull);
			Dot.Location = Dot.Center + Dot.Offset.RotateAngleAxis(Dot.Swirl * Age, FVector::UpVector) * Shrink;
		}
		else
		{
			Dot.Location += Dot.Velocity * DeltaTime;
		}
		// 엔진 기본 판 = 100×100.
		const float Size = Dot.Size / 100.0f * Shrink;
		Transforms.Add(FTransform(Facing, Dot.Location, FVector(Size, Size, 1.0f)));
	}
	GlowDotLayer->ClearInstances();
	GlowDotLayer->AddInstances(Transforms, false, true);
	if (GlowDots.IsEmpty())
	{
		RefreshTickEnabled();
	}
}

void UGideonSkillComponent::PlayCastMontage(UAnimSequence* Animation, int32 Loops, bool bKeepAsActive)
{
	UAnimInstance* AnimInstance = CastAnimInstance.Get();
	if (!Animation || !AnimInstance)
	{
		return;
	}
	if (UAnimMontage* Montage = UAnimMontage::CreateSlotAnimationAsDynamicMontage(Animation, CastSlot, 0.2f, 0.25f, 1.0f, Loops))
	{
		AnimInstance->Montage_Play(Montage, 1.0f);
		// 붙잡는 자세는 시전이 끝날 때 FinishCast가 내리게 하고, 마무리 동작은 시전이 끝나도 끝까지 둔다.
		if (bKeepAsActive)
		{
			ActiveMontage = Montage;
		}
	}
}

void UGideonSkillComponent::After(float Seconds, TFunction<void()> Callback)
{
	if (!GetWorld())
	{
		return;
	}
	FTimerHandle Handle;
	GetWorld()->GetTimerManager().SetTimer(Handle, FTimerDelegate::CreateWeakLambda(this,
		[Callback = MoveTemp(Callback)]() { Callback(); }), FMath::Max(Seconds, 0.01f), false);
}

UParticleSystemComponent* UGideonSkillComponent::SpawnTimedEffect(UParticleSystem* Effect, const FVector& Location,
	const FRotator& Rotation, float Scale, float Seconds)
{
	UParticleSystemComponent* Component = SpawnOwnedEffect(Effect, Location, Rotation);
	if (!Component)
	{
		return nullptr;
	}
	Component->SetWorldScale3D(FVector(Scale));
	// Dekker 바닥·벽 효과는 반복 재생이라 스스로 안 꺼진다(gideon-new3-20261018-001554). 정해진 시간 뒤 지운다.
	After(Seconds, [this, Weak = TWeakObjectPtr<UParticleSystemComponent>(Component)]()
	{
		if (UParticleSystemComponent* Live = Weak.Get())
		{
			OwnedEffects.Remove(Live);
			Live->DestroyComponent();
		}
	});
	return Component;
}

int32 UGideonSkillComponent::ApplyLineDamage(const FVector& Start, const FVector& End, float Width, float Damage, FName Status,
	float StatusSeconds)
{
	TArray<AActor*> Candidates;
	GatherTargets((Start + End) * 0.5f, FVector::Dist2D(Start, End) * 0.5f + Width, Candidates);
	AController* Instigator = Character.IsValid() ? Character->GetController() : nullptr;
	const FVector FlatEnd(End.X, End.Y, Start.Z);
	int32 Hits = 0;
	for (AActor* Target : Candidates)
	{
		const FVector Flat(Target->GetActorLocation().X, Target->GetActorLocation().Y, Start.Z);
		if (FMath::PointDistToSegment(Flat, Start, FlatEnd) > Width)
		{
			continue;
		}
		if (Target->CanBeDamaged() && Damage > 0.0f)
		{
			const FVector Push = (FlatEnd - Start).GetSafeNormal2D();
			FHitResult Hit(Target, nullptr, Target->GetActorLocation(), Push);
			UGameplayStatics::ApplyPointDamage(Target, Damage, Push, Hit, Instigator, GetOwner(), nullptr);
			// A 도우미가 떠 있으면 맞은 대상에게도 한 발(간격 제한이 있어 줄 위 여럿이어도 한 번).
			HelperAssist(Target);
		}
		if (!Status.IsNone())
		{
			SetStatus(Target, Status, StatusSeconds);
		}
		++Hits;
	}
	UE_LOG(LogTemp, Display, TEXT("GIDEON_LINEDAMAGE from=%s to=%s width=%.0f damage=%.0f hits=%d"), *Start.ToCompactString(),
		*End.ToCompactString(), Width, Damage, Hits);
	return Hits;
}

void UGideonSkillComponent::ExecuteStarLine()
{
	LineDirection = (ActiveAim - Character->GetActorLocation()).GetSafeNormal2D();
	LineStart = GetFeetLocation();
	StarLinePortals();
}

void UGideonSkillComponent::StarLinePortals()
{
	// 조준 방향으로 바닥에 작은 포털이 줄지어 열리고, 포털마다 운석 조각이 터진다(Gideon 보라 효과).
	// 표시는 W처럼 바닥에 깐 포털(시안 넷 중 사용자 선택 10-18, gideon-14th-20261018-144228/e_mark_drafts.png).
	// 포털은 차례로 열고, 마지막 포털이 열린 뒤 CircleLeadSeconds부터 열린 순서(가까운 쪽부터)대로 터진다(「마법진이 단계적으로 생성 후에,
	// 0.5초 정도 있다가 터졌으면」 → 「시전된 순서대로, 가까운 순서대로 폭발」 10-19). 포털은 제 차례에 터질 때까지 남는다.
	// 예전에는 포털마다 열리고 LinePortalDrop 뒤 따로 터졌고, 그다음엔 다섯 개가 한꺼번에 터졌다.
	const float Burst = (LinePortals - 1) * LinePortalInterval + CircleLeadSeconds;
	for (int32 Index = 0; Index < LinePortals; ++Index)
	{
		const FVector Ground = LineStart + LineDirection * (LinePortalSpacing * (Index + 1));
		const float Open = Index * LinePortalInterval;
		const float Explode = Burst + Index * LinePortalInterval;
		After(Open + 0.01f, [this, Ground, Life = Explode - Open + 0.1f]()
		{
			SpawnTimedEffect(RiftPortal, Ground + FVector(0.0f, 0.0f, 5.0f), FRotator(0.0f, 0.0f, 180.0f), 0.3f, Life);
		});
		After(Explode + 0.01f, [this, Ground, Index]()
		{
			// 마지막 칸은 크게 터뜨려 마무리한다(「2% 아쉽다」 10-18 — 다섯 번이 같은 크기라 끝이 흐지부지). 화면 흔들림은 빼 달라고 함.
			const bool bLast = Index == LinePortals - 1;
			if (RiftImpact)
			{
				UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), RiftImpact, Ground, FRotator::ZeroRotator,
					FVector(LineImpactScale * (bLast ? LineFinishScale : 1.0f)));
			}
			const int32 Hits = ApplyAreaDamage(Ground, LinePortalRadius, Skills[EGideonSkill::StarLine].Damage);
			UE_LOG(LogTemp, Display, TEXT("GIDEON_LINE portal=%d hits=%d"), Index, Hits);
		});
	}
}

void UGideonSkillComponent::ExecuteRingWard()
{
	WardForward = (ActiveAim - Character->GetActorLocation()).GetSafeNormal2D();
	if (WardForward.IsNearlyZero())
	{
		WardForward = Character->GetActorForwardVector().GetSafeNormal2D();
	}
	CloseTornSpacePortal(WardPortal.Get(), nullptr);
	const FVector Location = Character->GetActorLocation() + WardForward * WardAhead + FVector(0.0f, 0.0f, WardHeight);
	WardPortal = SpawnOwnedEffect(PortalEntrance, Location, FRotator(0.0f, WardForward.Rotation().Yaw + TornSpacePortalYawOffset, 0.0f));
	if (UParticleSystemComponent* Portal = WardPortal.Get())
	{
		Portal->SetWorldScale3D(FVector(WardScale));
	}
	After(WardSeconds, [this, Generation = CastGeneration]()
	{
		if (bCasting && Generation == CastGeneration)
		{
			ReleaseRingWard();
		}
	});
	UE_LOG(LogTemp, Display, TEXT("GIDEON_WARD up at=%s"), *Location.ToCompactString());
}

void UGideonSkillComponent::ReleaseRingWard()
{
	// 방패를 닫으며 앞쪽(정면 좌우 WardPushArc) 적을 몸에서 바깥으로 밀쳐내고 피해를 준다.
	UParticleSystemComponent* Portal = WardPortal.Get();
	const FVector Origin = Character->GetActorLocation();
	const FVector Burst = Portal ? Portal->GetComponentLocation() : Origin + WardForward * WardAhead;
	// 공은 닫힘 이펙트 없이 거두고 그 자리에서 거품이 깨지듯 터진다(시안 R3).
	CloseTornSpacePortal(Portal, nullptr);
	WardPortal.Reset();
	// 방패 자리에서 보라 빛이 터진다. 보라 돔(V 끝)은 하늘에서 번개 기둥이 내리쳐 밀쳐내는 느낌이 안 났다(gideon-19th-h-20261018-233012 ward_175).
	// 10-20 「R 좋은데 폭발 3번 하는 건」 → 거품 터짐을 WardPopGap 간격으로 세 번, 앞으로 WardPopStride씩 나아가며 조금씩 크게(밀기·피해는 한 번).
	for (int32 Pulse = 0; Pulse < WardPops && WardPop; ++Pulse)
	{
		After(Pulse * WardPopGap, [this, At = Burst + WardForward * (WardPopStride * Pulse), Scale = WardPopScale * (1.0f + 0.25f * Pulse)]()
		{
			// 거품 터짐 첫 장면은 주황 덩어리로 보여(gideon-28th-batch-20261019-233601 ward1_021, 밀쳐낸 다음 프레임) 그동안 숨겼다가 보인다.
			if (UParticleSystemComponent* Pop = UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), WardPop, At, FRotator::ZeroRotator, FVector(Scale)))
			{
				Pop->SetVisibility(false);
				After(WardPopHideSeconds, [Weak = TWeakObjectPtr<UParticleSystemComponent>(Pop)]()
				{
					if (UParticleSystemComponent* Live = Weak.Get())
					{
						Live->SetVisibility(true);
					}
				});
			}
		});
	}
	TArray<AActor*> Targets;
	GatherTargets(Origin, WardPushRadius, Targets);
	const float MinDot = FMath::Cos(FMath::DegreesToRadians(WardPushArc));
	int32 Pushed = 0;
	for (AActor* Target : Targets)
	{
		const FVector Away = (Target->GetActorLocation() - Origin).GetSafeNormal2D();
		if (FVector::DotProduct(Away, WardForward) < MinDot)
		{
			continue;
		}
		if (Target->CanBeDamaged())
		{
			FHitResult Hit(Target, nullptr, Target->GetActorLocation(), -Away);
			UGameplayStatics::ApplyPointDamage(Target, Skills[EGideonSkill::StarCage].Damage, Away, Hit, Character->GetController(), GetOwner(), nullptr);
			HelperAssist(Target);
		}
		if (PrimaryHitCharacter)
		{
			UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), PrimaryHitCharacter, Target->GetActorLocation(), Away.Rotation(), FVector(1.5f));
		}
		// 수련장 허수아비는 블랙홀처럼 잠시 뒤 제자리로 돌린다(RestoreBlackHoleTargets).
		if (!BlackHolePendingRestore.ContainsByPredicate([Target](const FBlackHoleTarget& Entry) { return Entry.Actor.Get() == Target; }))
		{
			FBlackHoleTarget& Entry = BlackHolePendingRestore.AddDefaulted_GetRef();
			Entry.Actor = Target;
			Entry.Origin = Target->GetActorLocation();
		}
		const FVector Step = Away * (WardPushDistance / WardPushSteps);
		for (int32 Index = 1; Index <= WardPushSteps; ++Index)
		{
			After(Index * WardPushSeconds / WardPushSteps, [Weak = TWeakObjectPtr<AActor>(Target), Step]()
			{
				if (AActor* Live = Weak.Get())
				{
					// 바닥에 닿은 캡슐은 쓸기 이동이 첫 접촉에서 막히므로 순간 이동으로 민다(블랙홀과 같은 까닭).
					Live->SetActorLocation(Live->GetActorLocation() + Step, false, nullptr, ETeleportType::TeleportPhysics);
				}
			});
		}
		++Pushed;
	}
	if (Pushed > 0 && GetWorld())
	{
		GetWorld()->GetTimerManager().SetTimer(BlackHoleRestoreTimer, this, &UGideonSkillComponent::RestoreBlackHoleTargets,
			WardPushSeconds + BlackHoleRestoreDelay, false);
	}
	UE_LOG(LogTemp, Display, TEXT("GIDEON_WARD release pushed=%d"), Pushed);
}

void UGideonSkillComponent::ExecuteSkyLance()
{
	// 조준점 둘레에 작은 유성이 차례로, 마지막에 가운데로 큰 유성(기절)이 떨어진다. 떨어지는 자리는 서로 띄워 고르게 흩는다.
	const FVector Center = ActiveAim;
	// 바퀴마다 따로 띄워 흩는다. 다른 바퀴와는 0.84초 떨어져 떨어지므로 자리가 겹쳐도 된다(24개를 한꺼번에 85씩 띄우면 반경 300에 다 안 들어간다).
	TArray<FVector> Spots;
	for (int32 Round = 0; Round < StarRounds; ++Round)
	{
		const int32 First = Spots.Num();
		for (int32 Try = 0; Spots.Num() - First < StarSmallCount && Try < StarSpotTries; ++Try)
		{
			const FVector Spot = Center + FVector(FMath::FRandRange(-1.0f, 1.0f), FMath::FRandRange(-1.0f, 1.0f), 0.0f) * StarSpread;
			bool bCrowded = false;
			for (int32 Other = First; Other < Spots.Num() && !bCrowded; ++Other)
			{
				bCrowded = FVector::Dist2D(Spot, Spots[Other]) < StarMinGap;
			}
			if (FVector::Dist2D(Spot, Center) <= StarSpread && FVector::Dist2D(Spot, Center) >= StarMinGap && !bCrowded)
			{
				Spots.Add(Spot);
			}
		}
	}
	const float Damage = Skills[EGideonSkill::SkyLance].Damage;
	for (int32 Index = 0; Index < Spots.Num(); ++Index)
	{
		After(Index * StarInterval + 0.01f, [this, Spot = Spots[Index], Damage]()
		{
			LaunchStarMeteor(Spot, Damage * StarSmallDamage, StarSmallRadius, 1.0f, false);
		});
	}
	After(Spots.Num() * StarInterval + StarBigDelay, [this, Center, Damage]()
	{
		LaunchStarMeteor(Center, Damage * StarBigDamage, SkyRadius, 1.6f, true);
	});
	UE_LOG(LogTemp, Display, TEXT("GIDEON_SKY cast center=%s small=%d"), *Center.ToCompactString(), Spots.Num());
}

void UGideonSkillComponent::LaunchStarMeteor(const FVector& Target, float Damage, float Radius, float Scale, bool bStun)
{
	// 화면 오른쪽 위 하늘에서 왼쪽 아래로 비스듬히 긋는 유성. 유성마다 방향을 조금씩 흔든다.
	FRotator View(0.0f, Character->GetActorRotation().Yaw, 0.0f);
	if (const APlayerController* Viewer = Cast<APlayerController>(Character->GetController()))
	{
		if (Viewer->PlayerCameraManager)
		{
			View = FRotator(0.0f, Viewer->PlayerCameraManager->GetCameraRotation().Yaw, 0.0f);
		}
	}
	// 화면 왼쪽(카메라 오른쪽의 반대)으로 가다가 깊이 쪽으로 조금 튼다(카메라 쪽 = 화면 아래).
	const FVector ScreenLeft = -FRotationMatrix(View).GetUnitAxis(EAxis::Y);
	const FVector Horizontal = ScreenLeft.RotateAngleAxis(-StarFallDepthAngle + FMath::FRandRange(-StarFallJitter, StarFallJitter), FVector::UpVector);
	const float Tilt = FMath::DegreesToRadians(StarFallTilt);
	const FVector Fall = (Horizontal * FMath::Sin(Tilt) - FVector::UpVector * FMath::Cos(Tilt)).GetSafeNormal();
	// 흩은 자리마다 바닥 높이를 다시 찾는다(조준점이 허수아비 몸에 걸려 공중일 수 있다). 못 찾으면 시전자 발 높이.
	FVector Floor(Target.X, Target.Y, GetFeetLocation().Z);
	FHitResult Down;
	FCollisionQueryParams DownQuery(SCENE_QUERY_STAT(GideonStarFloor), false, Character.Get());
	if (GetWorld()->LineTraceSingleByObjectType(Down, Target + FVector(0.0f, 0.0f, 300.0f), Target - FVector(0.0f, 0.0f, 1000.0f),
		FCollisionObjectQueryParams(ECC_WorldStatic), DownQuery))
	{
		Floor = Down.ImpactPoint;
	}
	FStarMeteor& Meteor = StarMeteors.AddDefaulted_GetRef();
	Meteor.Location = Floor - Fall * StarFallLength;
	Meteor.Velocity = Fall * StarSpeed;
	Meteor.Ground = Floor.Z;
	Meteor.Damage = Damage;
	Meteor.Radius = Radius;
	Meteor.Scale = Scale;
	Meteor.bStun = bStun;
	if (UParticleSystemComponent* Trail = SpawnOwnedEffect(StarTrail, Meteor.Location, Fall.Rotation()))
	{
		Trail->SetWorldScale3D(FVector(StarTrailScale * Scale));
		Meteor.Effect = Trail;
	}
	RefreshTickEnabled();
}

void UGideonSkillComponent::UpdateStarMeteors(float DeltaTime)
{
	if (StarMeteors.IsEmpty() || !GetWorld())
	{
		return;
	}
	// 허수아비·캐릭터에 먼저 닿으면 거기서, 아니면 떨어질 바닥 높이에서 터진다(시전자 제외).
	// 벽(고정 물체)은 보지 않는다 — 맵 가장자리에 쓰면 비스듬히 날아오는 길이 벽을 지나 벽에 부딪혀 터졌다(「벽에 부딪히는 경우 못 막아?」 10-20).
	FCollisionQueryParams Query(SCENE_QUERY_STAT(GideonStarMeteor), false, Character.Get());
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	Objects.AddObjectTypesToQuery(ECC_Pawn);
	for (int32 Index = StarMeteors.Num() - 1; Index >= 0; --Index)
	{
		FStarMeteor& Meteor = StarMeteors[Index];
		const FVector Next = Meteor.Location + Meteor.Velocity * DeltaTime;
		// 하늘 높은 곳은 방 벽·천장 윗부분을 지나므로 바닥 가까이(사람 키 두 배쯤)에 내려와서야 부딪힘을 본다.
		FHitResult Hit;
		const bool bHit = Next.Z <= Meteor.Ground + StarCollisionHeight && GetWorld()->SweepSingleByObjectType(Hit, Meteor.Location, Next,
			FQuat::Identity, Objects, FCollisionShape::MakeSphere(StarCollisionRadius), Query);
		if (bHit || Next.Z <= Meteor.Ground)
		{
			const FVector Point = bHit ? Hit.ImpactPoint : FMath::LinePlaneIntersection(Meteor.Location, Next, FVector(0.0f, 0.0f, Meteor.Ground), FVector::UpVector);
			const FStarMeteor Done = Meteor;
			StarMeteors.RemoveAt(Index);
			ExplodeStarMeteor(Done, Point, bHit ? Hit.GetActor() : nullptr);
			continue;
		}
		// 지나간 길에 빛 점을 촘촘히 남긴다. 점은 수명 동안 작아지므로 머리는 굵고 꼬리 끝으로 갈수록 가늘다.
		// 이번 틱 사이의 점은 앞쪽일수록 늦게 지나간 것이라 나이를 그만큼 덜 준다.
		// 거친 꼬리(StarRagged*): 점을 옆으로 흔들고 크기를 들쭉날쭉하게, 지나간 길에서 부스러기가 떨어져 나간다.
		const int32 Dots = FMath::Max(FMath::CeilToInt(FVector::Dist(Meteor.Location, Next) / StarTailSpacing), 1);
		for (int32 Dot = 1; Dot <= Dots; ++Dot)
		{
			const float Along = static_cast<float>(Dot) / Dots;
			const FVector Shake = FMath::VRand() * StarRaggedJitter * Meteor.Scale * FMath::FRand();
			AddGlowDot(FMath::Lerp(Meteor.Location, Next, Along) + Shake, FVector::ZeroVector, StarTailLife,
				StarTailSize * Meteor.Scale * FMath::FRandRange(0.55f, 1.35f), (1.0f - Along) * DeltaTime);
		}
		const float FleckShare = FVector::Dist(Meteor.Location, Next) / StarRaggedSpacing;
		const int32 Flecks = FMath::FloorToInt(FleckShare) + (FMath::FRand() < FMath::Frac(FleckShare) ? 1 : 0);
		for (int32 Fleck = 0; Fleck < Flecks; ++Fleck)
		{
			const FVector Out = (FMath::VRand() - Meteor.Velocity.GetSafeNormal() * 0.5f).GetSafeNormal();
			AddGlowDot(FMath::Lerp(Meteor.Location, Next, FMath::FRand()), Out * FMath::FRandRange(150.0f, 380.0f),
				FMath::FRandRange(0.2f, 0.45f), StarRaggedFleck * Meteor.Scale * FMath::FRandRange(0.6f, 1.3f));
		}
		// D 보강 2: 지나간 길에서 별가루가 옆으로 흩어지며 사그라든다. 이번 틱에 지나간 길이 ÷ StarDustSpacing개(남는 몫은 확률로).
		if (GetStarBoost() & 2)
		{
			const float Expected = FVector::Dist(Meteor.Location, Next) / StarDustSpacing;
			const int32 Count = FMath::FloorToInt(Expected) + (FMath::FRand() < FMath::Frac(Expected) ? 1 : 0);
			for (int32 Dust = 0; Dust < Count; ++Dust)
			{
				AddGlowDot(FMath::Lerp(Meteor.Location, Next, FMath::FRand()), FMath::VRand() * FMath::FRandRange(40.0f, 120.0f),
					FMath::FRandRange(0.5f, 0.9f), StarDustSize * Meteor.Scale * FMath::FRandRange(0.7f, 1.2f));
			}
		}
		Meteor.Location = Next;
		if (UParticleSystemComponent* Trail = Meteor.Effect.Get())
		{
			Trail->SetWorldLocation(Next);
		}
	}
	if (StarMeteors.IsEmpty())
	{
		RefreshTickEnabled();
	}
}

void UGideonSkillComponent::ExplodeStarMeteor(const FStarMeteor& Meteor, const FVector& Point, AActor* Struck)
{
	// 꼬리는 새로 뿜기만 멈춰 남은 불꽃이 사그라들게 둔다.
	ReleaseOwnedEffect(Meteor.Effect.Get());
	const int32 Boost = GetStarBoost();
	const bool bFinale = Meteor.bStun && (Boost & 4);
	if (PrimaryHitWorld)
	{
		UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), PrimaryHitWorld, Point, FRotator::ZeroRotator,
			FVector(bFinale ? StarFinaleImpactScale : Meteor.bStun ? StarBigImpactScale : StarSmallImpactScale));
	}
	// 큰 유성의 V 섬광(Dekker SlowBomb 폭발 — 공기가 펑 퍼지는 모양)은 「마지막에 펑 하는 이펙트(공기 느낌) 꺼줘」(10-20)로 뺐다.
	// 피해·기절은 바닥 기준(허수아비 몸에 부딪혀도 발밑 둘레).
	const FVector Floor(Point.X, Point.Y, Meteor.Ground);
	// D 보강(GetStarBoost). 큰 섬광 점은 카메라를 향한 판이라 바닥 가까이 두면 아래쪽이 바닥에 잘려 네모나게 보였다(gideon-48th-dboost-* sky4 42번째)
	// → 카메라 쪽으로 반지름만큼 당긴다(판의 아래 끝은 가운데보다 반지름 × cos 50° 낮고, 당기면 반지름 × sin 50° 높아진다).
	FVector Toward = -FRotator(-50.0f, 45.0f, 0.0f).Vector();
	if (const APlayerController* Viewer = Character.IsValid() ? Cast<APlayerController>(Character->GetController()) : nullptr)
	{
		if (Viewer->PlayerCameraManager)
		{
			Toward = -Viewer->PlayerCameraManager->GetCameraRotation().Vector();
		}
	}
	if (Boost & 1)
	{
		const float Big = Meteor.bStun ? 1.5f : 1.0f;
		const float Flash = StarBoostFlash * (Meteor.bStun ? 1.8f : 1.0f);
		AddGlowDot(Point + Toward * (Flash * 0.5f), FVector::ZeroVector, StarBoostFlashLife, Flash);
		for (int32 Index = 0; Index < StarBoostSparks * (Meteor.bStun ? 2 : 1); ++Index)
		{
			const FVector Out = FVector(FMath::FRandRange(-1.0f, 1.0f), FMath::FRandRange(-1.0f, 1.0f), FMath::FRandRange(0.4f, 1.0f)).GetSafeNormal();
			AddGlowDot(Point + FVector(0.0f, 0.0f, 10.0f), Out * FMath::FRandRange(350.0f, 700.0f), FMath::FRandRange(0.35f, 0.6f),
				StarBoostSparkSize * Big * FMath::FRandRange(0.8f, 1.2f));
		}
	}
	if (bFinale)
	{
		AddGlowDot(Floor + Toward * (StarFinaleFlash * 0.5f), FVector::ZeroVector, 0.25f, StarFinaleFlash);
		for (int32 Index = 0; Index < StarFinaleRing; ++Index)
		{
			const float Angle = FMath::DegreesToRadians(360.0f * Index / StarFinaleRing + FMath::FRandRange(-6.0f, 6.0f));
			const FVector Out = FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.12f).GetSafeNormal();
			AddGlowDot(Floor + FVector(0.0f, 0.0f, 15.0f), Out * FMath::FRandRange(600.0f, 900.0f), FMath::FRandRange(0.5f, 0.7f),
				22.0f * FMath::FRandRange(0.85f, 1.15f));
		}
	}
	// 부딪힌 바닥에 그을음 자국을 남긴다. 마지막 큰 유성이 떨어지면 모두 잠깐 뒤 함께 서서히 사라진다.
	// 큰 유성이 안 떨어지는 경우(시전이 끊김)를 위해 띄울 때도 늦은 사라짐을 걸어 둔다.
	// 시안(Gideon.Skills.DMark): 0 그을음 · 1 테두리가 밝게 빛나는 그을음 · 2 룬 무늬 · 3 별 무늬 · 4 = 0 + 피어오르는 불씨.
	const int32 Mark = FMath::Clamp(CVarGideonDMark.GetValueOnGameThread(), 0, 4);
	UMaterialInterface* MarkMaterial = Mark == 2 ? StarRuneMaterial.Get() : Mark == 3 ? StarAstroMaterial.Get() : StarScorchMaterial.Get();
	const float Size = bFinale ? StarFinaleScorchSize : Meteor.bStun ? StarBigScorchSize : StarScorchSize;
	if (MarkMaterial)
	{
		if (UDecalComponent* Scorch = UGameplayStatics::SpawnDecalAtLocation(GetWorld(), MarkMaterial,
			FVector(StarScorchDepth, Size, Size), Floor, FRotator(-90.0f, FMath::FRandRange(0.0f, 360.0f), 0.0f)))
		{
			Scorch->SetFadeScreenSize(0.0f);
			Scorch->SetFadeOut(StarScorchFallback, StarScorchFade, false);
			Scorch->SetLifeSpan(StarScorchFallback + StarScorchFade + 0.1f);
			if (Mark == 1)
			{
				if (UMaterialInstanceDynamic* Dynamic = Scorch->CreateDynamicMaterialInstance())
				{
					Dynamic->SetScalarParameterValue(TEXT("GlowIntensity"), 7.0f);
					Dynamic->SetScalarParameterValue(TEXT("GlowSharpness"), 1.5f);
					Dynamic->SetScalarParameterValue(TEXT("Opacity"), 0.7f);
				}
			}
			StarScorches.Add(Scorch);
		}
	}
	if (Mark == 4)
	{
		// 자국 위에서 천천히 피어오르며 사그라드는 불씨.
		for (int32 Index = 0; Index < StarEmberCount; ++Index)
		{
			const FVector Start = Floor + FVector(FMath::FRandRange(-1.0f, 1.0f), FMath::FRandRange(-1.0f, 1.0f), 0.0f) * Size * 0.6f +
				FVector(0.0f, 0.0f, 5.0f);
			AddGlowDot(Start, FVector(FMath::FRandRange(-10.0f, 10.0f), FMath::FRandRange(-10.0f, 10.0f), FMath::FRandRange(25.0f, 60.0f)),
				FMath::FRandRange(1.2f, 2.4f), StarEmberSize * (Meteor.bStun ? 1.5f : 1.0f));
		}
	}
	if (Meteor.bStun)
	{
		for (const TWeakObjectPtr<UDecalComponent>& Weak : StarScorches)
		{
			if (UDecalComponent* Scorch = Weak.Get())
			{
				Scorch->SetFadeOut(StarScorchHold, StarScorchFade, false);
				Scorch->SetLifeSpan(StarScorchHold + StarScorchFade + 0.1f);
			}
		}
		StarScorches.Reset();
	}
	if (Meteor.bStun && SkyStunned)
	{
		TArray<AActor*> Targets;
		GatherTargets(Floor, Meteor.Radius, Targets);
		for (AActor* Target : Targets)
		{
			UGameplayStatics::SpawnEmitterAttached(SkyStunned, Target->GetRootComponent(), NAME_None,
				FVector(0.0f, 0.0f, 100.0f), FRotator::ZeroRotator, EAttachLocation::KeepRelativeOffset, true);
		}
	}
	const int32 Hits = ApplyAreaDamage(Floor, Meteor.Radius, Meteor.Damage, Meteor.bStun ? FName(TEXT("STUN")) : NAME_None, SkyStunSeconds);
	UE_LOG(LogTemp, Display, TEXT("GIDEON_SKY impact=%s struck=%s big=%d hits=%d"), *Floor.ToCompactString(),
		Struck ? *Struck->GetName() : TEXT("ground"), Meteor.bStun ? 1 : 0, Hits);
}

void UGideonSkillComponent::ExecutePortalBlast()
{
	// 사용자 요청(10-17)으로 원작의 앞으로 쏘는 운석 대신 운석을 조준점에 비스듬히 떨어뜨린다. 포털(마법진)은 떨어지는 자리 바닥에 깐다
	// (「그냥 돌이 떨어지는 지점에 마법진을」 10-18). 운석은 목표 너머(시전자 ↔ 목표 ↔ 운석 시작) 높은 하늘에서 온다.
	const FVector Forward = (ActiveAim - Character->GetActorLocation()).GetSafeNormal2D();
	const FVector Start = ActiveAim + Forward * BlastMeteorBeyond + FVector(0.0f, 0.0f, BlastMeteorHeight);
	const FRotator Fall = (ActiveAim - Start).Rotation();
	if (UParticleSystem* Circle = SkyPortal ? SkyPortal.Get() : BlastPortal.Get())
	{
		// 하늘에서 바닥을 보던 포털(pitch -90)을 뒤집어 위를 보게 눕힌다. 원본의 앞축 줄기는 숨긴 사본(gideon_portal_hide.py).
		if (UParticleSystemComponent* Portal = UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), Circle,
			ActiveAim + FVector(0.0f, 0.0f, BlastPortalLift), FRotator(90.0f, Fall.Yaw, 0.0f), FVector(BlastPortalScale)))
		{
			Portal->CustomTimeDilation = BlastPortalSlow;
		}
	}
	// 운석은 마법진과 함께 바로 출발한다(10-19 마법진 뒤 0.5초 대기 → 같은 날 「다시 빠르게」로 뺌).
	FBlastMeteor& Meteor = BlastMeteors.AddDefaulted_GetRef();
	Meteor.Effect = SpawnOwnedEffect(BlastProjectile, Start, Fall);
	Meteor.Start = Start;
	Meteor.End = ActiveAim;
	Meteor.StartTime = GetWorld()->GetTimeSeconds();
	Meteor.Duration = FVector::Dist(Start, ActiveAim) / BlastMeteorSpeed;
	RefreshTickEnabled();
	UE_LOG(LogTemp, Display, TEXT("GIDEON_METEOR start=%s end=%s fall=%.2fs"), *Start.ToCompactString(),
		*ActiveAim.ToCompactString(), Meteor.Duration);
}

void UGideonSkillComponent::UpdateBlastMeteors()
{
	if (BlastMeteors.IsEmpty() || !GetWorld())
	{
		return;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	for (int32 Index = BlastMeteors.Num() - 1; Index >= 0; --Index)
	{
		const FBlastMeteor& Meteor = BlastMeteors[Index];
		const float Alpha = FMath::Clamp(static_cast<float>((Now - Meteor.StartTime) / FMath::Max(Meteor.Duration, 0.01f)), 0.0f, 1.0f);
		UParticleSystemComponent* Effect = Meteor.Effect.Get();
		if (Effect)
		{
			Effect->SetWorldLocation(FMath::Lerp(Meteor.Start, Meteor.End, Alpha));
		}
		if (Alpha >= 1.0f)
		{
			ReleaseOwnedEffect(Effect);
			ExplodeBlastMeteor(Meteor.End);
			BlastMeteors.RemoveAt(Index);
		}
	}
	if (BlastMeteors.IsEmpty())
	{
		RefreshTickEnabled();
	}
}

void UGideonSkillComponent::ExplodeBlastMeteor(const FVector& Location)
{
	if (BlastHitWorld)
	{
		UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), BlastHitWorld, Location);
	}
	if (BlastExplosion)
	{
		UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), BlastExplosion, Location);
	}
	const int32 Hits = ApplyAreaDamage(Location, PortalBlastSplashRadius, Skills[EGideonSkill::PortalBlast].Damage);
	UE_LOG(LogTemp, Display, TEXT("GIDEON_METEOR impact=%s hits=%d"), *Location.ToCompactString(), Hits);
}

void UGideonSkillComponent::ExecutePortalVolley()
{
	// 조준 방향 앞에 작은 포털 셋을 부채꼴로 열고, 세 포털 모두 조준점 한 곳을 겨누게 한다.
	const FVector Center = Character->GetActorLocation();
	const FVector Direction = (ActiveAim - Center).GetSafeNormal2D();
	const FGideonSkillDefinition& Definition = Skills[EGideonSkill::PortalVolley];
	const float Distance = FMath::Clamp(FVector::Dist2D(ActiveAim, Center), VolleyMinFocusDistance, Definition.Range);
	VolleyFocus = Center + Direction * Distance;
	// 10-20부터 대상 지정: 모으는 점은 찍은 대상의 몸이고, 발마다 그때 대상 자리로 다시 겨눈다(FirePortalVolleyShot).
	if (const AActor* Focus = ActiveTarget.Get())
	{
		VolleyFocus = Focus->GetActorLocation();
	}
	VolleyPortals.Reset();
	for (int32 Index = 0; Index < VolleyPortalCount; ++Index)
	{
		const float Angle = VolleyPortalSpreadDegrees * (Index - (VolleyPortalCount - 1) * 0.5f);
		const FVector Portal = Center + Direction.RotateAngleAxis(Angle, FVector::UpVector) * VolleyPortalDistance +
			FVector(0.0f, 0.0f, VolleyPortalHeight);
		VolleyPortals.Add(Portal);
		if (BlastPortal)
		{
			UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), BlastPortal, Portal, (VolleyFocus - Portal).GetSafeNormal2D().Rotation(),
				FVector(0.6f));
		}
	}
	VolleyShot = 0;
	FirePortalVolleyShot();
	GetWorld()->GetTimerManager().SetTimer(VolleyTimer, this, &UGideonSkillComponent::FirePortalVolleyShot, VolleyShotInterval, true);
}

void UGideonSkillComponent::FirePortalVolleyShot()
{
	if (!Character.IsValid() || !GetWorld() || VolleyPortals.IsEmpty() || VolleyShot >= VolleyShots)
	{
		if (GetWorld())
		{
			GetWorld()->GetTimerManager().ClearTimer(VolleyTimer);
		}
		return;
	}
	// 왼쪽·가운데·오른쪽 포털을 차례로 돌며 쏜다. 사거리는 모으는 점을 조금 지나칠 만큼만. 대상이 움직였으면 지금 자리로 겨눈다.
	if (const AActor* Focus = ActiveTarget.Get())
	{
		VolleyFocus = Focus->GetActorLocation();
	}
	const FVector Portal = VolleyPortals[VolleyShot % VolleyPortals.Num()];
	const FGideonSkillDefinition& Definition = Skills[EGideonSkill::PortalVolley];
	if (PrimaryMuzzle)
	{
		UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), PrimaryMuzzle, Portal, (VolleyFocus - Portal).GetSafeNormal2D().Rotation());
	}
	// 사거리가 모으는 점 바로 너머에서 끝나 「빗나감」 효과(PrimaryNoHit)가 조준점 자리에서 터져 맞은 것처럼 보였다
	// (「안 맞았는데도 맞은 이펙트」 10-19) → 빗나가면 효과 없이 사라진다. 적·벽에 맞을 때만 터진다.
	LaunchProjectileFrom(EGideonProjectileKind::Primary, Portal, VolleyFocus, BasicAttackSpeed,
		FVector::Dist2D(Portal, VolleyFocus) + 200.0f, Definition.Damage, PrimaryProjectile, PrimaryHitCharacter, PrimaryHitWorld,
		nullptr);
	UE_LOG(LogTemp, Display, TEXT("GIDEON_VOLLEY shot=%d portal=%d focus=%s"), VolleyShot, VolleyShot % VolleyPortals.Num(),
		*VolleyFocus.ToCompactString());
	// S 탄은 평타 탄과 같은 투사체라 맞는 자리에서 가를 수 없어, 쏠 때 찍어 둔 대상에게 도우미도 쏜다(간격 제한).
	HelperAssist(ActiveTarget.Get());
	if (++VolleyShot >= VolleyShots)
	{
		GetWorld()->GetTimerManager().ClearTimer(VolleyTimer);
	}
}

void UGideonSkillComponent::FinishCast()
{
	if (!bCasting)
	{
		return;
	}
	bCasting = false;
	++CastGeneration;
	UE_LOG(LogTemp, Display, TEXT("GIDEON_SKILL finished=%s"), *Skills[ActiveSkill].Name.ToString());
	if (GetWorld())
	{
		GetWorld()->GetTimerManager().ClearTimer(ActionTimer);
		GetWorld()->GetTimerManager().ClearTimer(RecoveryTimer);
	}
	if (CastAnimInstance.IsValid())
	{
		if (ActiveMontage && !Skills[ActiveSkill].bFinishAnimation)
		{
			CastAnimInstance->Montage_Stop(0.15f, ActiveMontage);
		}
		CastAnimInstance->SetRootMotionMode(SavedRootMotionMode);
	}
	if (Character.IsValid() && Character->GetCharacterMovement())
	{
		Character->GetCharacterMovement()->bOrientRotationToMovement = bSavedOrientRotation;
	}
	CastAnimInstance.Reset();
	ActiveMontage = nullptr;
	ActiveSlot = INDEX_NONE;
	BlackHoleEnd = 0.0;
}

void UGideonSkillComponent::CancelSkill()
{
	if (!bCasting)
	{
		return;
	}
	UE_LOG(LogTemp, Display, TEXT("GIDEON_SKILL cancelled=%s"), *Skills[ActiveSkill].Name.ToString());
	if (ActiveSkill == EGideonSkill::BlackHole)
	{
		EndBlackHole(true);
	}
	if (ActiveSkill == EGideonSkill::TornSpace)
	{
		CloseTornSpacePortal(EntrancePortal.Get(), PortalEntranceClose);
		CloseTornSpacePortal(ExitPortal.Get(), PortalExitClose);
	}
	if (ActiveSkill == EGideonSkill::PortalVolley && GetWorld())
	{
		GetWorld()->GetTimerManager().ClearTimer(VolleyTimer);
	}
	if (ActiveSkill == EGideonSkill::StarCage)
	{
		CloseTornSpacePortal(WardPortal.Get(), PortalEntranceClose);
		WardPortal.Reset();
	}
	if (ActiveSkill == EGideonSkill::VoidRay)
	{
		ClearNoxBolt();
	}
	FinishCast();
}

FVector UGideonSkillComponent::GetSocketLocation(FName Socket) const
{
	const USkeletalMeshComponent* Mesh = Character.IsValid() ? Character->GetMesh() : nullptr;
	if (Mesh && Mesh->DoesSocketExist(Socket))
	{
		return Mesh->GetSocketLocation(Socket);
	}
	return Character.IsValid() ? Character->GetActorLocation() + Character->GetActorForwardVector() * 60.0f : FVector::ZeroVector;
}

AGideonProjectile* UGideonSkillComponent::LaunchProjectile(EGideonProjectileKind Kind, FName Socket, const FVector& Aim,
	float Speed, float Range, float Damage, UParticleSystem* Trail, UParticleSystem* HitCharacter,
	UParticleSystem* HitWorld, UParticleSystem* NoHit)
{
	if (!Character.IsValid() || !GetWorld())
	{
		return nullptr;
	}
	return LaunchProjectileFrom(Kind, GetSocketLocation(Socket), Aim, Speed, Range, Damage, Trail, HitCharacter, HitWorld, NoHit);
}

AGideonProjectile* UGideonSkillComponent::LaunchProjectileFrom(EGideonProjectileKind Kind, FVector Origin, const FVector& Aim,
	float Speed, float Range, float Damage, UParticleSystem* Trail, UParticleSystem* HitCharacter,
	UParticleSystem* HitWorld, UParticleSystem* NoHit)
{
	if (!Character.IsValid() || !GetWorld())
	{
		return nullptr;
	}
	// 손을 높이 드는 시전(Burden 등)에서도 허수아비·캐릭터 캡슐 높이 안으로 날도록 몸 중심 근처로 높이를 묶는다.
	const float Center = Character->GetActorLocation().Z;
	Origin.Z = FMath::Clamp(Origin.Z, Center - 40.0f, Center + 40.0f);
	FVector Direction = (Aim - Origin).GetSafeNormal2D();
	if (Direction.IsNearlyZero())
	{
		Direction = Character->GetActorForwardVector().GetSafeNormal2D();
	}
	// 쿼터뷰 바닥 조준이라 위 높이 그대로 수평으로 날린다.
	FActorSpawnParameters Parameters;
	Parameters.Owner = Character.Get();
	Parameters.Instigator = Character.Get();
	Parameters.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	AGideonProjectile* Projectile = GetWorld()->SpawnActor<AGideonProjectile>(Origin, Direction.Rotation(), Parameters);
	if (Projectile)
	{
		Projectile->Launch(Kind, Direction, Speed, Range, Damage, Trail, HitCharacter, HitWorld, NoHit);
		OwnedProjectiles.Add(Projectile);
	}
	return Projectile;
}

bool UGideonSkillComponent::FireBasicAttack(const FVector& AimLocation, int32 ComboStep)
{
	if (!bEnabled || !Character.IsValid())
	{
		return false;
	}
	const FName Socket = *FString::Printf(TEXT("Muzzle_0%d"), FMath::Clamp(ComboStep, 0, 2) + 1);
	// 손에서 커서 자리로 모아 쏜다(멀리 있는 적을 맞히려면 모여야 한다 — 몸 방향과 나란히 쏘면 손이 옆으로 떨어진 만큼 비켜 간다,
	// gideon-regress-20261019-161912). 다만 손은 몸에서 옆·앞으로 떨어져 있어 몸 가까이 찍은 바닥을 손에서 겨누면 크게 옆으로 꺾인다
	// (「바닥에 쏘면 이상한 곳으로 튄다」 10-19) → 손 방향이 몸→커서 방향과 BasicAttackMaxSkew 넘게 어긋나면 몸 방향으로 쏜다.
	// 몸 반경 안을 찍으면 캐릭터가 보는 쪽.
	const FVector Body = Character->GetActorLocation();
	const FVector Hand = GetSocketLocation(Socket);
	const FVector BodyDirection = FVector::Dist2D(AimLocation, Body) < BasicAttackMinAim ?
		Character->GetActorForwardVector().GetSafeNormal2D() : (AimLocation - Body).GetSafeNormal2D();
	FVector Direction = (AimLocation - Hand).GetSafeNormal2D();
	if (Direction.IsNearlyZero() || FVector::DotProduct(Direction, BodyDirection) < FMath::Cos(FMath::DegreesToRadians(BasicAttackMaxSkew)))
	{
		Direction = BodyDirection;
	}
	if (PrimaryMuzzle)
	{
		UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), PrimaryMuzzle, Hand, Direction.Rotation());
	}
	UE_LOG(LogTemp, Display, TEXT("GIDEON_BASIC step=%d socket=%s aim=%s hand=%s yaw=%.1f body_yaw=%.1f hand_yaw=%.1f"), ComboStep,
		*Socket.ToString(), *AimLocation.ToCompactString(), *Hand.ToCompactString(), Direction.Rotation().Yaw, BodyDirection.Rotation().Yaw,
		(AimLocation - Hand).GetSafeNormal2D().Rotation().Yaw);
	// A 도우미가 떠 있으면 평타마다 한 발 광선을 쏴 준다(HelperShotDelay 뒤 — 평타와 한 박자 어긋나 둘 다 보이게).
	if (HelperOrb.IsValid())
	{
		After(HelperShotDelay, [this, AimLocation]() { HelperShoot(AimLocation); });
	}
	return LaunchProjectile(EGideonProjectileKind::Primary, Socket, Hand + Direction * BasicAttackRange, BasicAttackSpeed,
		BasicAttackRange, BasicAttackDamage, PrimaryProjectile, PrimaryHitCharacter, PrimaryHitWorld, PrimaryNoHit) != nullptr;
}

void UGideonSkillComponent::HandleProjectileStopped(EGideonProjectileKind Kind, const FVector& Location, AActor* Target)
{
	switch (Kind)
	{
	case EGideonProjectileKind::PortalBlast:
		ExplodeBlastMeteor(Location);
		break;
	case EGideonProjectileKind::Burden:
		if (IsCombatTarget(Target, GetOwner()))
		{
			ApplyBurden(Target);
		}
		break;
	case EGideonProjectileKind::Primary:
		break;
	}
}

UParticleSystemComponent* UGideonSkillComponent::SpawnOwnedEffect(UParticleSystem* Effect, const FVector& Location, const FRotator& Rotation)
{
	if (!Effect || !GetWorld())
	{
		return nullptr;
	}
	UParticleSystemComponent* Component = UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), Effect, Location, Rotation,
		FVector(1.0f), false);
	if (Component)
	{
		OwnedEffects.Add(Component);
	}
	return Component;
}

void UGideonSkillComponent::ReleaseOwnedEffect(UParticleSystemComponent* Effect)
{
	if (!IsValid(Effect))
	{
		return;
	}
	OwnedEffects.Remove(Effect);
	// 반복 입자는 새로 뿜는 것만 멈추고, 남은 입자가 사라지면 스스로 정리한다.
	Effect->bAutoDestroy = true;
	Effect->DeactivateSystem();
}

void UGideonSkillComponent::GatherTargets(const FVector& Center, float Radius, TArray<AActor*>& Out) const
{
	if (!GetWorld())
	{
		return;
	}
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_Pawn);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	FCollisionQueryParams Query(SCENE_QUERY_STAT(GideonArea), false, GetOwner());
	TArray<FOverlapResult> Overlaps;
	// 높이 차가 있는 경사로에서도 맞도록 납작한 원기둥 대신 높은 캡슐로 찾는다.
	GetWorld()->OverlapMultiByObjectType(Overlaps, Center + FVector(0.0f, 0.0f, 90.0f), FQuat::Identity, Objects,
		FCollisionShape::MakeCapsule(Radius, Radius + 150.0f), Query);
	for (const FOverlapResult& Overlap : Overlaps)
	{
		AActor* Actor = Overlap.GetActor();
		if (IsCombatTarget(Actor, GetOwner()) && FVector::DistSquared2D(Actor->GetActorLocation(), Center) <=
			FMath::Square(Radius + 40.0f))
		{
			Out.AddUnique(Actor);
		}
	}
}

int32 UGideonSkillComponent::ApplyAreaDamage(const FVector& Center, float Radius, float Damage, FName Status, float StatusSeconds)
{
	TArray<AActor*> Targets;
	GatherTargets(Center, Radius, Targets);
	AController* Instigator = Character.IsValid() ? Character->GetController() : nullptr;
	for (AActor* Target : Targets)
	{
		if (Target->CanBeDamaged() && Damage > 0.0f)
		{
			FHitResult Hit(Target, nullptr, Target->GetActorLocation(), (Target->GetActorLocation() - Center).GetSafeNormal2D());
			UGameplayStatics::ApplyPointDamage(Target, Damage, (Target->GetActorLocation() - Center).GetSafeNormal2D(), Hit,
				Instigator, GetOwner(), nullptr);
		}
		if (!Status.IsNone())
		{
			SetStatus(Target, Status, StatusSeconds);
		}
	}
	UE_LOG(LogTemp, Display, TEXT("GIDEON_AREA center=%s radius=%.0f damage=%.0f hits=%d"),
		*Center.ToCompactString(), Radius, Damage, Targets.Num());
	// A 도우미가 떠 있으면 맞은 대상(첫째)에게도 한 발.
	if (Damage > 0.0f && !Targets.IsEmpty())
	{
		HelperAssist(Targets[0]);
	}
	return Targets.Num();
}

void UGideonSkillComponent::ExecuteCosmicRift()
{
	// 룬 원은 포털이 열릴 때 0.3초만 보이고, 그 뒤 커지는 보라 고리는 꺼도 3초 넘게 남아 겹친다.
	// 그래서 운석마다 앞 포털을 바로 지우고 새로 열어 룬 원만 이어 보이게 한다.
	const auto ClosePortal = [this]()
	{
		if (UParticleSystemComponent* Portal = RiftPortalEffect.Get())
		{
			OwnedEffects.Remove(Portal);
			Portal->DestroyComponent();
		}
	};
	// 바닥 포털은 가운데에 보라 빛을 덧칠해 마법진 가운데만 진해 보였다(사용자 「가운데 찐하고 바깥 연함」 10-18) → 열지 않는다.
	// 룬 마법진이 떨어질 자리를 대신 보여 준다.
	const auto OpenPortal = [ClosePortal]()
	{
		ClosePortal();
	};
	// 쿨타임을 무시하는 시험에서 균열이 겹치면 앞 균열의 포털·운석비를 먼저 닫는다.
	ClosePortal();
	ReleaseOwnedEffect(RiftShowerEffect.Get());
	RiftCenter = ActiveAim;
	// 원본은 포털을 하늘에 띄우지만 쿼터뷰에서는 화면 위로 잘린다. 같은 룬 원을 뒤집어 목표 바닥에 깔아
	// 떨어질 자리를 먼저 보여 주고, 운석은 한 박자 뒤부터 떨어진다.
	OpenPortal();
	ShowRiftRunes(RiftCenter, RiftRadius, RiftRuneOpacity);
	RiftRuneFadeLength = RiftRuneFadeSeconds;
	RiftWave = -1;
	const auto Wave = [this, OpenPortal, ClosePortal]()
	{
		if (++RiftWave < RiftWaves)
		{
			OpenPortal();
			CosmicRiftWave(RiftWave);
			return;
		}
		GetWorld()->GetTimerManager().ClearTimer(RiftTimer);
		ClosePortal();
		// 마법진은 바로 지우지 않고 줄어들며 사라지게 한다(UpdateRiftRuneFade).
		RiftRuneFadeStart = GetWorld()->GetTimeSeconds();
		RefreshTickEnabled();
		ReleaseOwnedEffect(RiftShowerEffect.Get());
	};
	// 마법진만 먼저 깔고 CircleLeadSeconds 뒤에 운석비를 시작한다(「마법진 생긴 이후에 0.5초 딜레이 이후에 마법 시전」 10-19).
	// 같은 타이머 손잡이를 써서 쿨타임을 무시한 겹쳐 쓰기에서도 앞 균열의 대기·운석비가 함께 지워진다.
	GetWorld()->GetTimerManager().SetTimer(RiftTimer, FTimerDelegate::CreateWeakLambda(this, [this, Wave]()
	{
		RiftShowerEffect = SpawnOwnedEffect(RiftShower, RiftCenter);
		Wave();
		GetWorld()->GetTimerManager().SetTimer(RiftTimer, FTimerDelegate::CreateWeakLambda(this, Wave), RiftWaveInterval, true);
	}), CircleLeadSeconds, false);
}

void UGideonSkillComponent::ShowRiftRunes(const FVector& Center, float Radius, float Opacity)
{
	HideRiftRunes();
	if (!GetOwner() || !RiftRuneOuter)
	{
		return;
	}
	// 테두리 겹원(Border)을 균열 반경(피해 범위)에 맞춰 깔고, 룬 글자 고리는 그 안쪽에 둔다.
	// 룬 글자 고리와 안쪽 겹원은 한 벌로 만들어져 있어 같은 배율을 쓴다.
	const FVector Extent = RiftRuneOuter->GetBounds().BoxExtent;
	const float Scale = Radius * RiftRuneGlyphFraction / FMath::Max(Extent.GetMax(), 1.0f);
	const float BorderExtent = RiftRuneBorder ? RiftRuneBorder->GetBounds().BoxExtent.GetMax() : 0.0f;
	const float BorderScale = Radius / FMath::Max(BorderExtent, 1.0f);
	const float CenterExtent = RiftRuneCenter ? RiftRuneCenter->GetBounds().BoxExtent.GetMax() : 0.0f;
	const float CenterScale = Radius * RiftRuneCenterFraction / FMath::Max(CenterExtent, 1.0f);
	// 룬 고리 모형은 모두 YZ 면에 선 고리(두께 축 X)라 앞축을 위로 세워 눕히고, 가운데 삼각 마법진은 원래 누운 모형(두께 축 Z)이다.
	const FRotator Standing(90.0f, 0.0f, 0.0f);
	// 층마다 진하기 배수: 층을 하나씩 켜 바닥 대비 밝기를 잰 값(무채색 화소만, gideon-wlayers-20261018-155200)이
	// 가운데 삼각 약 25 · 안쪽 겹원·룬 글자 약 11 · 테두리 약 6이라 가운데만 진했다(사용자 지적 10-18 두 번). 밝기는 진하기의
	// 제곱으로 변하므로 배수 = √(목표 ÷ 잰 값). 1차 뒤 선 밝기(띠별 상위 5%)가 안 44~60 · 바깥 20~26이라 같은 셈으로 2차 조정(gideon-wlayers2-20261018-155400).
	// 점선 고리 자리는 룬 원판(「점선 마법진 아쉽고 심심」 10-18 → 시안 1번 선택).
	const float DenseScale = RiftRuneDense ? Radius * RiftRuneDenseFraction / FMath::Max(RiftRuneDense->GetBounds().BoxExtent.GetMax(), 1.0f) : 1.0f;
	const struct { UStaticMesh* Mesh; float Scale; FRotator Rotation; float Spin; float OpacityScale; } Layers[] = {
		{ RiftRuneOuter.Get(), Scale, Standing, -RiftRuneSpinDegrees, 0.74f },
		{ RiftRuneDense.Get(), DenseScale, FRotator::ZeroRotator, -RiftRuneSpinDegrees, RiftRuneDenseOpacity },
		{ RiftRuneBorder.Get(), BorderScale, Standing, RiftRuneSpinDegrees * 0.5f, 1.5f },
		{ RiftRuneCenter.Get(), CenterScale, FRotator::ZeroRotator, RiftRuneSpinDegrees * 1.5f, 0.5f } };
	for (const auto& Layer : Layers)
	{
		UStaticMesh* Mesh = Layer.Mesh;
		if (!Mesh)
		{
			continue;
		}
		const float Lift = Mesh == RiftRuneDense ? RiftRuneDenseLift : 3.0f;
		UStaticMeshComponent* Rune = SpawnRuneMesh(Mesh, Center + FVector(0.0f, 0.0f, Lift), Layer.Rotation, Layer.Scale,
			Opacity * Layer.OpacityScale, RiftRuneTint);
		RiftRunes.Add(Rune);
		RiftRuneScales.Add(Layer.Scale);
		RiftRuneSpins.Add(Layer.Spin);
	}
	RefreshTickEnabled();
	UE_LOG(LogTemp, Display, TEXT("GIDEON_RUNES shown=%d extent=%s border_extent=%.1f scale=%.2f border=%.2f"), RiftRunes.Num(),
		*Extent.ToCompactString(), BorderExtent, Scale, BorderScale);
}

UStaticMeshComponent* UGideonSkillComponent::SpawnRuneMesh(UStaticMesh* Mesh, const FVector& Location, const FRotator& Rotation,
	float Scale, float Opacity, const FLinearColor& Tint)
{
	// 캐릭터에 붙이지 않고 월드 좌표에 둔다(캐릭터가 움직여도 그 자리에 남는다).
	UStaticMeshComponent* Rune = NewObject<UStaticMeshComponent>(GetOwner());
	Rune->SetStaticMesh(Mesh);
	Rune->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Rune->SetCastShadow(false);
	Rune->SetWorldLocationAndRotation(Location, Rotation);
	Rune->SetWorldScale3D(FVector(Scale));
	// 마법진을 연하게(사용자 요청 10-18): 칸마다 Opacity 사본으로 바꿔 낮춘다.
	for (int32 Slot = 0; Slot < Mesh->GetStaticMaterials().Num(); ++Slot)
	{
		const UMaterialInterface* Original = Mesh->GetMaterial(Slot);
		const TObjectPtr<UMaterialInterface>* Faded = Original ? RiftRuneFadeMaterials.Find(Original->GetFName()) : nullptr;
		if (Faded && *Faded)
		{
			if (UMaterialInstanceDynamic* Dynamic = UMaterialInstanceDynamic::Create(*Faded, Rune))
			{
				Dynamic->SetScalarParameterValue(TEXT("Opacity"), RiftRuneSlotOpacity(Dynamic, Opacity));
				Dynamic->SetVectorParameterValue(TEXT("Tint"), Tint);
				Rune->SetMaterial(Slot, Dynamic);
			}
		}
	}
	Rune->RegisterComponent();
	return Rune;
}

void UGideonSkillComponent::HideRiftRunes()
{
	for (UStaticMeshComponent* Rune : RiftRunes)
	{
		if (IsValid(Rune))
		{
			Rune->DestroyComponent();
		}
	}
	RiftRunes.Reset();
	RiftRuneScales.Reset();
	RiftRuneSpins.Reset();
	RiftRuneFadeStart = -1.0;
	RefreshTickEnabled();
}

void UGideonSkillComponent::UpdateRiftRuneSpin(float DeltaTime)
{
	for (int32 Index = 0; Index < RiftRunes.Num(); ++Index)
	{
		if (IsValid(RiftRunes[Index]))
		{
			// 세워 눕힌 모형도 있어 자기 축이 아니라 세계의 위 축으로 돌린다.
			RiftRunes[Index]->AddWorldRotation(FQuat(FVector::UpVector, FMath::DegreesToRadians(RiftRuneSpins[Index] * DeltaTime)));
		}
	}
}

void UGideonSkillComponent::UpdateRiftRuneFade()
{
	if (RiftRuneFadeStart < 0.0 || !GetWorld())
	{
		return;
	}
	const float Alpha = FMath::Clamp(static_cast<float>((GetWorld()->GetTimeSeconds() - RiftRuneFadeStart) /
		FMath::Max(RiftRuneFadeLength, 0.01f)), 0.0f, 1.0f);
	if (Alpha >= 1.0f)
	{
		HideRiftRunes();
		return;
	}
	// 처음엔 천천히, 끝엔 빠르게 가운데로 줄인다.
	const float Scale = 1.0f - Alpha * Alpha;
	for (int32 Index = 0; Index < RiftRunes.Num(); ++Index)
	{
		if (IsValid(RiftRunes[Index]))
		{
			RiftRunes[Index]->SetWorldScale3D(FVector(RiftRuneScales[Index] * Scale));
		}
	}
}

void UGideonSkillComponent::RefreshTickEnabled()
{
	SetComponentTickEnabled(!BurdenTargets.IsEmpty() || !RiftRunes.IsEmpty() || BlackHoleEffect.IsValid() ||
		!BlastMeteors.IsEmpty() || !StarMeteors.IsEmpty() || !NoxSparks.IsEmpty() || !GlowDots.IsEmpty());
}

void UGideonSkillComponent::CosmicRiftWave(int32 WaveIndex)
{
	// 운석 낙하 지점은 반경 안에서 고르게 돌려 가며 보여 주고, 피해는 반경 전체에 같은 값으로 준다.
	const float Angle = WaveIndex * 2.39996f;
	const FVector Impact = RiftCenter + FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.0f) * RiftRadius * 0.45f;
	// 원본 충돌(수정이 깨지는 모양) 대신 폭발로(사용자 요청 10-18). 후보 단독 촬영 gideon-wexpl-20261018-142652.
	if (RiftBlast)
	{
		UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), RiftBlast, Impact, FRotator::ZeroRotator, FVector(RiftBlastScale));
	}
	ApplyAreaDamage(RiftCenter, RiftRadius, Skills[EGideonSkill::CosmicRift].Damage);
}

void UGideonSkillComponent::ExecuteTornSpace()
{
	const FVector From = Character->GetActorLocation();
	const float HalfHeight = Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	const FVector To = ActiveAim + FVector(0.0f, 0.0f, HalfHeight);
	if (TeleportEnter)
	{
		UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), TeleportEnter, From);
	}
	const bool bMoved = Character->TeleportTo(To, Character->GetActorRotation(), false, true);
	if (TeleportExit)
	{
		UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), TeleportExit, Character->GetActorLocation());
	}
	// 건너간 뒤 잠깐 두 포털을 열어 두었다가 같은 순간에 함께 닫는다.
	// 다음 E가 새 포털을 열어도 섞이지 않게 이번 포털을 따로 붙잡는다.
	const TWeakObjectPtr<UParticleSystemComponent> Entrance = EntrancePortal;
	const TWeakObjectPtr<UParticleSystemComponent> Exit = ExitPortal;
	EntrancePortal.Reset();
	ExitPortal.Reset();
	FTimerHandle CloseTimer;
	GetWorld()->GetTimerManager().SetTimer(CloseTimer, FTimerDelegate::CreateWeakLambda(this, [this, Entrance, Exit]()
	{
		CloseTornSpacePortal(Entrance.Get(), PortalEntranceClose);
		CloseTornSpacePortal(Exit.Get(), PortalExitClose);
	}), TornSpaceExitLinger, false);
	UE_LOG(LogTemp, Display, TEXT("GIDEON_TELEPORT moved=%d from=%s to=%s actual=%s"), bMoved,
		*From.ToCompactString(), *To.ToCompactString(), *Character->GetActorLocation().ToCompactString());
}

void UGideonSkillComponent::CloseTornSpacePortal(UParticleSystemComponent* Portal, UParticleSystem* CloseEffect)
{
	if (!IsValid(Portal))
	{
		return;
	}
	if (CloseEffect)
	{
		UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), CloseEffect, Portal->GetComponentLocation(), Portal->GetComponentRotation());
	}
	// 들어간 쪽 포털은 끄기만 하면 세로 빛줄기 입자가 3초 넘게 남는다(gideon-e-20261017-230153) → 지운다.
	// 단 닫힘 이펙트가 차오르기 전에 지우면 한 장면 비므로(gideon-e2-20261017-230640 e_095) 잠깐 겹쳐 둔다.
	OwnedEffects.Remove(Portal);
	FTimerHandle DestroyTimer;
	GetWorld()->GetTimerManager().SetTimer(DestroyTimer, FTimerDelegate::CreateWeakLambda(Portal, [Portal]()
	{
		Portal->DestroyComponent();
	}), TornSpaceCloseOverlap, false);
}

void UGideonSkillComponent::UpdateBlackHoleShrink()
{
	UParticleSystemComponent* Effect = BlackHoleEffect.Get();
	if (!Effect || BlackHoleEnd <= 0.0 || !GetWorld())
	{
		return;
	}
	// 끝나기 직전에 블랙홀을 한 점으로 빨려 들어가듯 접는다(터뜨리지 않는다 — 「폭발 말고 다 빨려 들어가듯」 10-18).
	const float Left = static_cast<float>(BlackHoleEnd - GetWorld()->GetTimeSeconds());
	if (Left > BlackHoleShrinkSeconds)
	{
		return;
	}
	const float Alpha = 1.0f - FMath::Clamp(Left / BlackHoleShrinkSeconds, 0.0f, 1.0f);
	Effect->SetWorldScale3D(FVector(FMath::Lerp(1.0f, BlackHoleShrinkScale, Alpha * Alpha) * BlackHoleSize));
	// 일렁이는 빛(V 시안)은 접히기 시작하면 원래 속도로 돌려 남은 구간을 마저 재생하며 같이 사라지게 한다.
	if (UParticleSystemComponent* Glow = BlackHoleGlowEffect.Get())
	{
		Glow->CustomTimeDilation = 1.0f;
	}
}

void UGideonSkillComponent::ExecuteBlackHole()
{
	// 앞 블랙홀의 허수아비가 아직 돌아가기 전이면 먼저 돌려야 새 원래 자리가 끌린 자리로 잘못 잡히지 않는다.
	GetWorld()->GetTimerManager().ClearTimer(BlackHoleRestoreTimer);
	if (!BlackHolePendingRestore.IsEmpty())
	{
		RestoreBlackHoleTargets();
	}
	BlackHoleCenter = ActiveAim;
	BlackHoleEnd = GetWorld()->GetTimeSeconds() + BlackHoleIntroSeconds + BlackHoleSeconds;
	// 봉인 마법진이 먼저 펼쳐지고, 그 위에 블랙홀이 열린다(사용자 요청 10-18). 끌기·피해도 블랙홀이 열릴 때부터.
	BlackHoleSealEffect = SpawnTimedEffect(SealCircle, BlackHoleCenter + FVector(0.0f, 0.0f, 5.0f), FRotator::ZeroRotator,
		BlackHoleSealScale * BlackHoleSize, BlackHoleIntroSeconds + BlackHoleSealLinger);
	if (UParticleSystemComponent* Seal = BlackHoleSealEffect.Get())
	{
		Seal->CustomTimeDilation = BlackHoleSealSlow;
	}
	// 원본 시전 동작(3.83초)이 곧 채널 전체다: 0.5초에 웅크려 모으고, 두 팔을 머리 위로 끌어올린 뒤 3.3초에 앞으로 내민다.
	// 남은 동작이 유지 시간과 함께 끝나도록 재생 속도만 맞춘다.
	if (CastAnimInstance.IsValid() && ActiveMontage)
	{
		const float Remaining = ActiveMontage->GetPlayLength() - CastAnimInstance->Montage_GetPosition(ActiveMontage);
		if (Remaining > 0.1f)
		{
			CastAnimInstance->Montage_SetPlayRate(ActiveMontage, Remaining / (BlackHoleIntroSeconds + BlackHoleSeconds));
		}
	}
	GetWorld()->GetTimerManager().SetTimer(BlackHoleIntroTimer, FTimerDelegate::CreateWeakLambda(this, [this]()
	{
		if (UParticleSystemComponent* Seal = BlackHoleSealEffect.Get())
		{
			Seal->CustomTimeDilation = 1.0f;
		}
		BlackHoleEffect = SpawnOwnedEffect(BlackHole, BlackHoleCenter + FVector(0.0f, 0.0f, 120.0f * BlackHoleSize));
		if (UParticleSystemComponent* Hole = BlackHoleEffect.Get())
		{
			Hole->SetWorldScale3D(FVector(BlackHoleSize));
		}
		RefreshTickEnabled();
		TArray<AActor*> Targets;
		GatherTargets(BlackHoleCenter, BlackHoleRadius * BlackHoleSize, Targets);
		BlackHoleTargets.Reset();
		for (AActor* Target : Targets)
		{
			BlackHoleTargets.Add({Target, Target->GetActorLocation()});
		}
		BlackHoleTick();
		GetWorld()->GetTimerManager().SetTimer(BlackHoleTimer, this, &UGideonSkillComponent::BlackHoleTick, BlackHoleTickSeconds, true);
		StartBlackHoleGlow();
		// 마법진이 다 펼쳐지고 블랙홀이 열리는 순간 번개가 내리친다 — F에서 빠진 콰앙 궁극기 번개(「번개 이펙트 아까우니 V 시전할 때
		// 마법진 이후로 번개 치는 이펙트로」 10-20). 가운데 한 번 크게, 이어서 블랙홀이 접히기 직전까지 마법진 안 아무 자리에 계속
		// (「터지기 직전까지 계속 번개 치는 이펙트 반복 — 위압감 있게」 10-20).
		const int32 Bolts = OriginalBolt ? FMath::FloorToInt((BlackHoleSeconds - BlackHoleShrinkSeconds) / BlackHoleBoltGap) + 1 : 0;
		for (int32 Bolt = 0; Bolt < Bolts; ++Bolt)
		{
			After(Bolt * BlackHoleBoltGap, [this, Bolt, Generation = CastGeneration]()
			{
				if (Generation != CastGeneration || !BlackHoleEffect.IsValid() ||
					GetWorld()->GetTimeSeconds() > BlackHoleEnd - BlackHoleShrinkSeconds)
				{
					return;
				}
				const float Angle = FMath::FRandRange(0.0f, 2.0f * PI);
				const FVector At = BlackHoleCenter + (Bolt == 0 ? FVector::ZeroVector :
					FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.0f) * BlackHoleRadius * BlackHoleSize * FMath::FRandRange(0.0f, BlackHoleBoltSpread));
				UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), OriginalBolt, At, FRotator::ZeroRotator,
					FVector((Bolt == 0 ? BlackHoleBoltScale : BlackHoleBoltScale * FMath::FRandRange(0.7f, 1.0f)) * BlackHoleSize));
			});
		}
		UE_LOG(LogTemp, Display, TEXT("GIDEON_BLACKHOLE start center=%s targets=%d"), *BlackHoleCenter.ToCompactString(),
			BlackHoleTargets.Num());
	}), BlackHoleIntroSeconds, false);
}

void UGideonSkillComponent::StartBlackHoleGlow()
{
	const int32 Draft = FMath::Clamp(CVarGideonVGlow.GetValueOnGameThread(), 0, 4);
	UE_LOG(LogTemp, Display, TEXT("GIDEON_VARIANT skill=V glow=%d"), Draft);
	if (Draft == 0 || !BlackHoleGlow)
	{
		return;
	}
	const FBlackHoleGlowDraft& Glow = BlackHoleGlowDrafts[Draft - 1];
	After(Glow.Delay, [this, Glow, Generation = CastGeneration]()
	{
		// 늦게 띄우는 시안은 그 사이 블랙홀이 끊겼으면 띄우지 않는다.
		if (Generation != CastGeneration || !BlackHoleEffect.IsValid())
		{
			return;
		}
		UParticleSystemComponent* Effect = SpawnOwnedEffect(BlackHoleGlow, BlackHoleCenter + FVector(0.0f, 0.0f, 5.0f));
		if (!Effect)
		{
			return;
		}
		Effect->SetWorldScale3D(FVector(Glow.Scale * BlackHoleSize));
		BlackHoleGlowEffect = Effect;
		After(Glow.SlowAfter, [Weak = TWeakObjectPtr<UParticleSystemComponent>(Effect)]()
		{
			if (UParticleSystemComponent* Live = Weak.Get())
			{
				Live->CustomTimeDilation = BlackHoleGlowDilation;
			}
		});
	});
}

void UGideonSkillComponent::BlackHoleTick()
{
	if (!GetWorld())
	{
		return;
	}
	if (GetWorld()->GetTimeSeconds() >= BlackHoleEnd - KINDA_SMALL_NUMBER)
	{
		EndBlackHole(false);
		FinishCast();
		return;
	}
	ApplyAreaDamage(BlackHoleCenter, BlackHoleRadius * BlackHoleSize, Skills[EGideonSkill::BlackHole].Damage, TEXT("STUN"),
		BlackHoleTickSeconds + 0.15f);
	for (const FBlackHoleTarget& Entry : BlackHoleTargets)
	{
		AActor* Target = Entry.Actor.Get();
		if (!IsValid(Target))
		{
			continue;
		}
		FVector ToCenter = BlackHoleCenter - Target->GetActorLocation();
		ToCenter.Z = 0.0f;
		const float Step = FMath::Min(BlackHolePullSpeed * BlackHoleTickSeconds, FMath::Max(ToCenter.Size() - 60.0f, 0.0f));
		if (Step > 0.0f)
		{
			// 바닥에 닿은 캡슐은 쓸기 이동이 첫 접촉에서 막히므로 순간 이동으로 당긴다.
			Target->SetActorLocation(Target->GetActorLocation() + ToCenter.GetSafeNormal() * Step, false, nullptr, ETeleportType::TeleportPhysics);
		}
	}
}

void UGideonSkillComponent::EndBlackHole(bool bCancelled)
{
	if (GetWorld())
	{
		GetWorld()->GetTimerManager().ClearTimer(BlackHoleTimer);
		GetWorld()->GetTimerManager().ClearTimer(BlackHoleIntroTimer);
	}
	// 블랙홀이 열리기 전에 끊기면 펼쳐지던 봉인 마법진도 거둔다.
	if (bCancelled)
	{
		ReleaseOwnedEffect(BlackHoleSealEffect.Get());
	}
	// 일렁이는 빛(V 시안)은 원래 속도로 돌려 남은 입자가 사라지면 스스로 정리되게 한다.
	if (UParticleSystemComponent* Glow = BlackHoleGlowEffect.Get())
	{
		Glow->CustomTimeDilation = 1.0f;
		ReleaseOwnedEffect(Glow);
	}
	BlackHoleGlowEffect.Reset();
	// 원작이 끝까지 버텼을 때 어떻게 닫히는지는 자료가 없다. 끝까지 버티면 한 점으로 접힌(UpdateBlackHoleShrink) 블랙홀을 그대로 지운다
	// (「폭발 말고 다 빨려 들어가듯」 10-18 — 터뜨리지 않는다).
	if (!bCancelled && BlackHoleEffect.IsValid())
	{
		UParticleSystemComponent* Effect = BlackHoleEffect.Get();
		const FVector Point = Effect->GetComponentLocation();
		// 한 점으로 접힌 블랙홀을 하얀 섬광과 푸른 충격 고리가 한 번에 터지며 지운다.
		// 10-20 「마지막 폭발이 훨씬 더 극적이고 강력하게」 → 섬광·고리를 키우고, 가운데 큰 번개 + 보라 충격파 구(정지폭탄) + W 폭발을 겹치고,
		// 고리를 한 번 더 크게 늦게 퍼뜨리고(두 겹 충격파), 빛 점을 사방으로 터뜨린다.
		OwnedEffects.Remove(Effect);
		Effect->DestroyComponent();
		const FVector Floor(Point.X, Point.Y, BlackHoleCenter.Z);
		if (AnnihilateFlash)
		{
			UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), AnnihilateFlash, Point, FRotator::ZeroRotator, FVector(BlackHoleFlashScale * BlackHoleSize));
		}
		if (AnnihilateRing)
		{
			UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), AnnihilateRing, Point, FRotator::ZeroRotator, FVector(BlackHoleRingScale * BlackHoleSize));
			After(BlackHoleSecondRingDelay, [this, Floor]()
			{
				UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), AnnihilateRing, Floor, FRotator::ZeroRotator,
					FVector(BlackHoleSecondRingScale * BlackHoleSize));
			});
		}
		if (OriginalBolt)
		{
			UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), OriginalBolt, Floor, FRotator::ZeroRotator, FVector(BlackHoleFinalBoltScale * BlackHoleSize));
		}
		if (FocusShockwave)
		{
			UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), FocusShockwave, Point, FRotator::ZeroRotator, FVector(BlackHoleFinalShockScale * BlackHoleSize));
		}
		if (RiftBlast)
		{
			UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), RiftBlast, Floor, FRotator::ZeroRotator, FVector(BlackHoleFinalBlastScale * BlackHoleSize));
		}
		for (int32 Index = 0; Index < BlackHoleFinalDots; ++Index)
		{
			FVector Out = FMath::VRand();
			Out.Z = FMath::Abs(Out.Z) * 0.5f;
			AddGlowDot(Point, Out.GetSafeNormal() * FMath::FRandRange(600.0f, 1400.0f) * BlackHoleSize, 0.6f, 40.0f * BlackHoleSize);
		}
	}
	// 도중에 끊기면 원래 크기라 팩의 닫힘 이펙트로 오므린다.
	else if (BlackHoleEffect.IsValid())
	{
		if (BlackHoleCancelled)
		{
			// 닫힘 이펙트는 원래 크기의 블랙홀이 오므라드는 모양이라, 줄어든 블랙홀 크기에 맞춰야 다시 커져 보이지 않는다.
			UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), BlackHoleCancelled, BlackHoleEffect->GetComponentLocation(),
				FRotator::ZeroRotator, BlackHoleEffect->GetComponentScale());
		}
		// 닫힘 이펙트는 0.2초쯤 지나야 차오르므로 그동안 블랙홀을 남겨 둬야 중간에 빈 화면이 안 생긴다.
		FTimerHandle CloseHandle;
		GetWorld()->GetTimerManager().SetTimer(CloseHandle, FTimerDelegate::CreateWeakLambda(this,
			[this, Effect = BlackHoleEffect]() { ReleaseOwnedEffect(Effect.Get()); }), BlackHoleCloseOverlap, false);
	}
	BlackHoleEffect.Reset();
	RefreshTickEnabled();
	UE_LOG(LogTemp, Display, TEXT("GIDEON_BLACKHOLE end cancelled=%d targets=%d"), bCancelled, BlackHoleTargets.Num());
	BlackHolePendingRestore.Append(BlackHoleTargets);
	BlackHoleTargets.Reset();
	if (GetWorld() && !BlackHolePendingRestore.IsEmpty())
	{
		GetWorld()->GetTimerManager().SetTimer(BlackHoleRestoreTimer, this, &UGideonSkillComponent::RestoreBlackHoleTargets,
			BlackHoleRestoreDelay, false);
	}
}

void UGideonSkillComponent::RestoreBlackHoleTargets()
{
	// 수련장 배치를 지키려고 끌려간 허수아비만 원래 자리로 돌린다. 실제 적(캐릭터)은 끌린 자리에 남는다.
	int32 Restored = 0;
	for (const FBlackHoleTarget& Entry : BlackHolePendingRestore)
	{
		if (AKwangTrainingDummy* Dummy = Cast<AKwangTrainingDummy>(Entry.Actor.Get()))
		{
			Dummy->SetActorLocation(Entry.Origin);
			++Restored;
		}
	}
	UE_LOG(LogTemp, Display, TEXT("GIDEON_BLACKHOLE restored=%d"), Restored);
	BlackHolePendingRestore.Reset();
}

void UGideonSkillComponent::ApplyBurden(AActor* Target)
{
	FBurdenTarget* Existing = BurdenTargets.FindByPredicate([Target](const FBurdenTarget& Entry) { return Entry.Actor.Get() == Target; });
	if (!Existing)
	{
		FBurdenTarget& Entry = BurdenTargets.AddDefaulted_GetRef();
		Entry.Actor = Target;
		if (BurdenDot)
		{
			UParticleSystemComponent* Effect = UGameplayStatics::SpawnEmitterAttached(BurdenDot, Target->GetRootComponent(),
				NAME_None, FVector::ZeroVector, FRotator::ZeroRotator, EAttachLocation::KeepRelativeOffset, false);
			Entry.Effect = Effect;
			if (Effect)
			{
				Effect->SetRelativeScale3D(FVector(BurdenDotScale));
				OwnedEffects.Add(Effect);
			}
		}
		Entry.Tether = SpawnBurdenTether();
		Existing = &Entry;
	}
	// 다시 맞으면 남은 지속 피해를 처음부터 다시 센다.
	Existing->TicksLeft = BurdenTicks;
	SetStatus(Target, TEXT("SLOW"), BurdenTickSeconds + 0.15f);
	FTimerManager& Timers = GetWorld()->GetTimerManager();
	Timers.SetTimer(Existing->Timer,
		FTimerDelegate::CreateUObject(this, &UGideonSkillComponent::BurdenTick, TWeakObjectPtr<AActor>(Target)),
		BurdenTickSeconds, true);
	RefreshTickEnabled();
	UpdateBurdenTethers();
	UE_LOG(LogTemp, Display, TEXT("GIDEON_BURDEN applied target=%s ticks=%d tether=%d"), *GetNameSafe(Target), BurdenTicks,
		Existing->Tether.IsValid());
}

bool UGideonSkillComponent::IsBurdenTetherBroken(const AActor* Target) const
{
	if (!Character.IsValid() || !IsValid(Target) || !GetWorld())
	{
		return true;
	}
	const FVector From = Character->GetActorLocation();
	const FVector To = Target->GetActorLocation();
	if (FVector::Dist2D(From, To) > BurdenTetherRange)
	{
		return true;
	}
	// 시야는 벽·기둥 같은 고정 물체만 가린다.
	FHitResult Hit;
	FCollisionQueryParams Query(SCENE_QUERY_STAT(GideonBurdenSight), false, Character.Get());
	Query.AddIgnoredActor(Target);
	return GetWorld()->LineTraceSingleByObjectType(Hit, From, To, FCollisionObjectQueryParams(ECC_WorldStatic), Query);
}

void UGideonSkillComponent::BurdenTick(TWeakObjectPtr<AActor> Target)
{
	const int32 Index = BurdenTargets.IndexOfByPredicate([&Target](const FBurdenTarget& Entry) { return Entry.Actor == Target; });
	if (Index == INDEX_NONE)
	{
		return;
	}
	AActor* Actor = Target.Get();
	if (IsBurdenTetherBroken(Actor))
	{
		EndBurden(Index, IsValid(Actor) ? TEXT("broken") : TEXT("gone"));
		return;
	}
	if (Actor->CanBeDamaged())
	{
		UGameplayStatics::ApplyDamage(Actor, BurdenTickDamage, Character.IsValid() ? Character->GetController() : nullptr,
			GetOwner(), nullptr);
	}
	// 감속은 줄이 이어진 동안만 건다. 끊기면 다음 갱신이 없어 곧 풀린다.
	SetStatus(Actor, TEXT("SLOW"), BurdenTickSeconds + 0.15f);
	if (--BurdenTargets[Index].TicksLeft <= 0)
	{
		EndBurden(Index, TEXT("expired"));
	}
}

void UGideonSkillComponent::EndBurden(int32 Index, const TCHAR* Reason)
{
	FBurdenTarget& Entry = BurdenTargets[Index];
	AActor* Actor = Entry.Actor.Get();
	if (GetWorld())
	{
		GetWorld()->GetTimerManager().ClearTimer(Entry.Timer);
		if (BurdenDotEnd && IsValid(Actor))
		{
			UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), BurdenDotEnd, Actor->GetActorLocation());
		}
	}
	ReleaseOwnedEffect(Entry.Effect.Get());
	if (USplineMeshComponent* Tether = Entry.Tether.Get())
	{
		Tether->DestroyComponent();
	}
	UE_LOG(LogTemp, Display, TEXT("GIDEON_BURDEN end target=%s reason=%s ticks_left=%d"), *GetNameSafe(Actor), Reason,
		Entry.TicksLeft);
	BurdenTargets.RemoveAt(Index);
	RefreshTickEnabled();
}

USplineMeshComponent* UGideonSkillComponent::SpawnBurdenTether()
{
	if (!BurdenTetherMesh || !GetOwner())
	{
		return nullptr;
	}
	// 캐릭터에 붙이지 않고 월드 원점에 둬서 두 끝 좌표를 월드 좌표 그대로 넣는다.
	USplineMeshComponent* Tether = NewObject<USplineMeshComponent>(GetOwner());
	Tether->SetMobility(EComponentMobility::Movable);
	Tether->SetStaticMesh(BurdenTetherMesh);
	Tether->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Tether->SetCastShadow(false);
	// 모형의 가장 긴 축을 줄 방향으로 쓴다.
	const FVector Extent = BurdenTetherMesh->GetBounds().BoxExtent;
	Tether->SetForwardAxis(Extent.X >= Extent.Y && Extent.X >= Extent.Z ? ESplineMeshAxis::X
		: (Extent.Y >= Extent.Z ? ESplineMeshAxis::Y : ESplineMeshAxis::Z), false);
	Tether->SetWorldTransform(FTransform::Identity);
	Tether->RegisterComponent();
	UE_LOG(LogTemp, Display, TEXT("GIDEON_BURDEN tether extent=%s"), *Extent.ToCompactString());
	return Tether;
}

void UGideonSkillComponent::UpdateBurdenTethers()
{
	const FVector Hand = GetSocketLocation(TEXT("Muzzle_01"));
	for (const FBurdenTarget& Entry : BurdenTargets)
	{
		USplineMeshComponent* Tether = Entry.Tether.Get();
		const AActor* Actor = Entry.Actor.Get();
		if (!Tether || !IsValid(Actor))
		{
			continue;
		}
		const FVector Target = Actor->GetActorLocation();
		const FVector Tangent = Target - Hand;
		Tether->SetStartAndEnd(Hand, Tangent, Target, Tangent, true);
	}
}

void UGideonSkillComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	UpdateBurdenTethers();
	UpdateRiftRuneSpin(DeltaTime);
	UpdateRiftRuneFade();
	UpdateBlackHoleShrink();
	UpdateBlastMeteors();
	UpdateStarMeteors(DeltaTime);
	UpdateNoxSparks(DeltaTime);
	UpdateGlowDots(DeltaTime);
}

void UGideonSkillComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	CancelSkill();
	if (GetWorld())
	{
		FTimerManager& Timers = GetWorld()->GetTimerManager();
		Timers.ClearTimer(ActionTimer);
		Timers.ClearTimer(RecoveryTimer);
		Timers.ClearTimer(RiftTimer);
		Timers.ClearTimer(BlackHoleTimer);
		Timers.ClearTimer(VolleyTimer);
		Timers.ClearTimer(SkyTimer);
		// A 도우미 구슬은 아래 OwnedEffects와 함께 지워진다.
		Timers.ClearTimer(HelperTimer);
		for (FBurdenTarget& Entry : BurdenTargets)
		{
			Timers.ClearTimer(Entry.Timer);
		}
	}
	if (!BlackHoleTargets.IsEmpty())
	{
		EndBlackHole(true);
	}
	// 캐릭터를 바꾸면 기다리던 허수아비 복귀 타이머가 같이 사라지므로 지금 돌린다.
	if (GetWorld())
	{
		GetWorld()->GetTimerManager().ClearTimer(BlackHoleRestoreTimer);
	}
	if (!BlackHolePendingRestore.IsEmpty())
	{
		RestoreBlackHoleTargets();
	}
	for (const TWeakObjectPtr<AGideonProjectile>& Projectile : OwnedProjectiles)
	{
		if (Projectile.IsValid())
		{
			Projectile->Destroy();
		}
	}
	for (UParticleSystemComponent* Effect : OwnedEffects)
	{
		if (IsValid(Effect))
		{
			Effect->DestroyComponent();
		}
	}
	OwnedProjectiles.Reset();
	OwnedEffects.Reset();
	for (const FBurdenTarget& Entry : BurdenTargets)
	{
		if (USplineMeshComponent* Tether = Entry.Tether.Get())
		{
			Tether->DestroyComponent();
		}
	}
	BurdenTargets.Reset();
	HideRiftRunes();
	bEnabled = false;
	Super::EndPlay(EndPlayReason);
}
