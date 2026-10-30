// 87차 마감 재작업(2026-10-28 「E, D 빼고 다 아쉽다 — 이펙트·마감」) — 고르기 페이지(Saved/QA/CharacterPipeline/aurora-87th-page) 답:
// W 「있던 자리에 생기는 얼음 오브젝트 애니메이션만 다른 걸로, 가능하면 돌진하기 직전(팔을 뒤로 뺀) 느낌」 · Space 「2번」 · R 「R2」 ·
// Q 「Q-2에 결정 파열로」 · F 「F1」. 「바닥에 깔리는 얼음 오브젝트 남발 금지」에 맞춰 조합에 있던 남는 가시·고드름 잔해는 뺐다
// (사용자가 고른 R-2 감옥 고리만 둔다). 콘솔 값을 0으로 두면 그 전 모습.
#include "AuroraSkillComponent.h"

#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInterface.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "TimerManager.h"
#include "TopDownCombatCharacter.h"

namespace
{
	// 기본 2 → 1(92차 확대 aurora-92nd-finalQ: 2는 칼끝이 앞쪽 위로 들려 내지르는 중으로 보이고, 1이 칼 든 팔을 뒤로 늘어뜨려
	// 「돌진하기 직전(팔을 뒤로 뺀)」에 가장 가깝다)
	TAutoConsoleVariable<int32> CVarAuroraWPose(
		TEXT("Aurora.FX.WPose"), 1,
		TEXT("W leap: what stays behind where she leapt from. 0 the old ice statue, 1 an ice copy of her standing with the sword arm drawn back before a dash (default), 2 crouched low lunging with the sword raised, 3 holding the sword out aimed (dash aiming stance)."));
	TAutoConsoleVariable<int32> CVarAuroraSpaceLook(
		TEXT("Aurora.FX.SpaceLook"), 1,
		TEXT("Space dash: 0 the old white floor streak and trail, 1 ice fragments scattering along the path and a crystal burst with a flash where she stops (default)."));
	// 93차 「분신 주변 얼음 오브젝트는 좀 다른 이펙트 없나」 → 바닥 고드름 대신 2 냉기 회오리(기본) · 3 떠서 도는 얼음 결정, 1 = 그 전 고드름
	// 94차 「원형으로 도는 이펙트가 E랑 겹쳐서 아쉬운데 다른 시안 없나」 → 4 공중에 멈춘 얼음 파편(기본) · 5 대상이 얼음에 갇힘
	TAutoConsoleVariable<int32> CVarAuroraRPrison(
		TEXT("Aurora.FX.RPrison"), 4,
		TEXT("R flurry: what wraps the target from the start until the big blast after the last cut. 4 an ice burst round the target frozen in mid-air for the whole flurry, released flying out at the blast (default), 5 the target sealed in Aurora's own freezing ice, 2 Aurora's frost whirlwind held round the target, 3 a ring of deep-blue ice spears circling the target point first that all stab into it at the blast, 1 the old ring of icicles on the floor, 0 none."));
	TAutoConsoleVariable<int32> CVarAuroraQBurst(
		TEXT("Aurora.FX.QBurst"), 1,
		TEXT("Q frost slash: 1 a crystal burst once on every target it hits (default), 0 none."));
	// Q 검기 자체(10-28 「Q의 진짜 문제는 저 검기 자체」) — 93차 「정말 최종적으로 검기 스타일 여러 개 시안」으로 3~6을 더함 → 94차 「그림 톤·게임 톤과
	// 안 맞는다」로 팩 칼 궤적 7~9를 더해 8이 기본, 고르기 전까지
	TAutoConsoleVariable<int32> CVarAuroraQSlash(
		TEXT("Aurora.FX.QSlash"), 8,
		TEXT("Q sword wave itself: 0 the old painted crescent with ice cones on it, 1 a code-drawn sharp blade - a thin white-hot edge, cyan glow, speed streaks flowing along it, wearing away from the inside, 2 an ice crystal blade - faceted cells glinting, each going out on its own, 3 an energy crescent - a thick body streaming back from a white-hot edge like flame, with sparks (default), 4 three thin wind blades of different radii unfolding one after another with dragged wind marks, 5 a frost storm - no edge line, a swirling blue frost mist crescent with snowflakes, 6 a crescent of solid deep-blue glowing ice chunks on a thin glowing edge, (94th - the pack's own Aurora sword-trail look instead of drawn shapes) 7 a wide ribbon in the pack's mesh-trail material (brushed, streaming), 8 a thin glowing edge over that ribbon (default), 9 a thin ribbon in the pack's basic-attack trail material over that ribbon - all three with Aurora's basic-attack snowflakes, (95th - very thin) 10 a hairline glowing edge over a very thin brushed ribbon, 11 the hairline edge alone."));
	// F 덩어리 자체(10-28 「이것도 얼음 이펙트 자체가 아쉬운 거임」) → 93차 「이것도 너무 아쉬운데 얼음송곳 같은 걸로 바꾸면 어때?」로 3을 더해 기본
	TAutoConsoleVariable<int32> CVarAuroraFChunk(
		TEXT("Aurora.FX.FChunk"), 4,
		TEXT("F ice barrage chunks: 0 the old drawn gems and thin light streaks, 1 solid tumbling ice rocks that fly with Rampage's ice rock trail, 2 the same ice stretched into crystal spears pointing where they fly, with Aurora's leap trail, 3 faceted deep-blue icicles hovering point up, then drilling at their targets point first, spinning on their own axis, (94th) 4 copies of Aurora's own sword appearing behind her with her sword-summon flash, hovering point up, then flying point first (default), 5 the same swords in glowing ghost ice."));
	// A 게임 안 시안(87차 「A-1, A-2는 게임에 적용해서 시안 볼 수 있게 — 이렇게 봐서는 모르겠다」) — 기본 1, 고르기 전까지
	TAutoConsoleVariable<int32> CVarAuroraAPolish(
		TEXT("Aurora.FX.APolish"), 1,
		TEXT("A ice armor look: 0 the old frost ring and cracked shell, 1 ice spikes bursting out of her body and shattering at 0.8 s, then the shell (default), 2 four icicle plates rising round her that stay on her for the whole armor instead of the shell and shatter when it ends."));
	// S 새 방향(87차 「S는 다 아쉬움」) — 기본 1, 고르기 전까지
	// 94차 「바닥 시안 여러 개 · 아예 없애고 머리 위 얼음 왕관 같은 버프기로 바꾸는 건 어때」 → 3 왕관만이 기본
	TAutoConsoleVariable<int32> CVarAuroraSPolish(
		TEXT("Aurora.FX.SPolish"), 3,
		TEXT("S frost haste look: 0 the old snow rune circle with ice set round its rim, 1 a soft round frost floor and an icy aura on her body while she is fast (default), 2 the old rune circle floor with the same body aura, no rim ice, (94th) 3 no floor - a crown of ice crystals turning slowly above her head while she is fast, with the body aura (default), 4 the crown and the soft frost floor, 5 a floor cracking outward from her feet, 6 no floor - two frost shockwave rings when she casts."));
	// 덩어리 재질(90차 비교 aurora-90th-fskin): 0 분신 얼음은 납작한 하늘색 조각 · 1 메시에 원래 붙은 팩 얼음 재질은 면 그림자가 있어
	// 얼음 바위·결정으로 읽힌다 → 기본 1
	TAutoConsoleVariable<int32> CVarAuroraFChunkSkin(
		TEXT("Aurora.FX.FChunkSkin"), 1,
		TEXT("F solid chunks: 0 the glowing clone ice material, 1 the ice chunk mesh's own pack material (default)."));
	TAutoConsoleVariable<int32> CVarAuroraFBurst(
		TEXT("Aurora.FX.FBurst"), 1,
		TEXT("F ice barrage: 1 a big crystal burst where each chunk hits (default), 0 none."));
	// 93차 A 「시전 애니메이션 다른 거 없어?」 — 원작 동작 후보 촬영(aurora-93rd-acast)에서 고른 셋. 그 전에 반려된 것(Recall 칼 꽂기 ·
	// Ability_R_InPlace_V2 · Level_Start 칼 돌리기 · Ability_R_Targeting 한 자세)은 다시 쓰지 않음(Recall은 꽂기 전 칼 돌려 드는 구간만)
	TAutoConsoleVariable<int32> CVarAuroraAMotion(
		TEXT("Aurora.FX.AMotion"), 1,
		TEXT("A ice armor cast motion (94th: played slower, 0.5 s up and 0.3 s held): 1 she brings the sword up and holds it slanted over her head in a guard (Emote_Slice 0.47-0.87 s, default), 2 she spins the sword in her hand and lifts it level over her head (Recall 0.67-1.07 s), 3 she rises from a crouch with the sword pointed straight at the sky (Ability_R_InPlace 0.60-1.00 s), 0 the old left hand reaching up."));
	// 94차 「A는 좀 천천히」: 동작 시안의 드는 시간 · 버티는 시간(그 전 0.21 · 0.2초)
	constexpr float ArmorMotionRaise = 0.5f;
	constexpr float ArmorMotionHold = 0.3f;
	// 94차 「저 보호막도 시안 여러 개」
	TAutoConsoleVariable<int32> CVarAuroraAShell(
		TEXT("Aurora.FX.AShell"), 2,
		TEXT("A ice armor shell: 2 her whole body glazed in a thin glowing ice skin drawn over her (default), 3 Aurora's own decoy frost growing over her body and held there, 1 the cracked frost sphere round her, 0 none."));
	const TCHAR* const ArmorSkinPath = TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_ArmorSkin.M_Aurora_ArmorSkin");
	const TCHAR* const ArmorFrostPaths[] = {
		TEXT("/Game/ParagonAurora/FX/Particles/Abilities/Leap/FX/P_Aurora_Decoy_Frost_Torso.P_Aurora_Decoy_Frost_Torso"),
		TEXT("/Game/ParagonAurora/FX/Particles/Abilities/Leap/FX/P_Aurora_Decoy_Mesh_Attach.P_Aurora_Decoy_Mesh_Attach")};
	constexpr float ArmorSkinBrightness = 2.2f;
	constexpr float ArmorSkinRim = 2.0f;
	constexpr float ArmorFrostHoldAfter = 0.8f;
	constexpr float ArmorFrostDilation = 0.02f;
	// 94차 S 얼음 왕관: 결정 수 · 고리 반경 · 몸 가운데(캡슐)에서 고리까지 높이 · 긴/짧은 결정 길이 · 굵기 · 바깥으로 기운 각 · 도는 빠르기 ·
	// 생길 때 커지는 시간
	constexpr int32 CrownCount = 8;
	// 95차 「왕관 더 작게」: 반경 15 → 10 · 긴 결정 34 → 22 · 짧은 결정 20 → 13 · 굵기 8 → 5.5(약 2/3), 머리에 조금 더 가깝게 92 → 88
	constexpr float CrownRadius = 10.0f;
	constexpr float CrownLift = 88.0f;
	constexpr float CrownTall = 22.0f;
	constexpr float CrownShort = 13.0f;
	constexpr float CrownThick = 5.5f;
	constexpr float CrownTilt = 18.0f;
	constexpr float CrownSpin = 40.0f;
	constexpr float CrownForm = 0.25f;
	struct FArmorMotion
	{
		const TCHAR* Name;
		float Start;
		float Peak;
	};
	const FArmorMotion ArmorMotions[] = {
		{TEXT("Emote_Slice"), 0.47f, 0.87f},
		{TEXT("Recall"), 0.67f, 1.07f},
		{TEXT("Ability_R_InPlace"), 0.60f, 1.0f}};
	// 93차 D 「오브젝트 얼음 생기는 거 너무 별론데 아예 빼든가 다른 오브젝트 이펙트 줘 봐」 — 둘 다 넣고 2를 기본으로
	TAutoConsoleVariable<int32> CVarAuroraDShard(
		TEXT("Aurora.FX.DShard"), 2,
		TEXT("D (Cryoseism) landing and ice bursts: what replaces the glowing ice bits flung across the floor. 2 Rampage's big ice crystal burst with a ring of Aurora's shattering fragments, nothing left lying (default), 1 nothing (only the frost shockwave), 0 the old glowing ice bits."));

	// WPose 1~3 굳힐 시각: 1·2 = 원작 돌진(Ability_Q)에서 칼을 뒤로 뺀 순간(aurora-87th-wpose 0.28초 선 채 · 0.35초 웅크림),
	// 3 = 원작 돌진 겨누기 시작(Ability_Q_Targeting_Intro)에서 칼을 앞으로 겨눈 0.40초
	constexpr float DecoyPoseTimes[] = {0.28f, 0.35f, 0.40f};

	// Space-2 길 조각 · 도착 결정 파열 · 섬광 크기(조합 촬영 aurora-87th-combos Sp2 = 1.0 · 1.3 · 0.8), 도착 자리는 발 앞
	constexpr float SpaceFragmentScale = 1.0f;
	constexpr float SpaceArrivalBurst = 1.3f;
	constexpr float SpaceArrivalFlash = 0.8f;
	constexpr float SpaceArrivalAhead = 60.0f;
	// R-2 고드름 고리: 개수 · 반경 · 크기 · 터질 때 큰 폭발 · 고드름마다 부서짐(조합 R2 = 6 · 190 · 0.55 · 1.3)
	constexpr int32 PrisonCount = 6;
	constexpr float PrisonRadius = 190.0f;
	constexpr float PrisonScale = 0.55f;
	constexpr float PrisonBreakScale = 1.3f;
	constexpr float PrisonCrumbleScale = 0.8f;
	// 93차 RPrison 2 회오리 크기 · 붙잡는 때 · 붙잡은 빠르기(E 원본 회오리는 0.2초짜리 휘감기라 그대로면 시작 순간에만 보였다 — 첫 촬영
	// aurora-93rd-final → 다 휘감은 뒤 느리게 돌게 붙잡아 난무 내내 남긴다, 55차 E 둘레 결정과 같은 방법)
	constexpr float PrisonSwirlScale = 1.6f;
	constexpr float PrisonSwirlHoldAfter = 0.15f;
	constexpr float PrisonSwirlHoldDilation = 0.15f;
	// 3 얼음 창 고리: 개수 · 도는 반경(분신이 서는 140 바깥) · 높이 · 창 길이 · 굵기 · 초당 도는 각 · 커지는 시간 · 터질 때 가운데로 꽂히는
	// 시간 · 겨누는 높이(대상 몸통). 첫 촬영의 둥근 덩어리는 쿼터뷰에서 작은 흰 점으로만 보였다 → 짙푸른 얼음 창이 끝으로 대상을 겨눈 채 돈다
	constexpr int32 PrisonOrbCount = 8;
	constexpr float PrisonOrbRadius = 185.0f;
	constexpr float PrisonOrbHeight = 90.0f;
	constexpr float PrisonSpearLength = 90.0f;
	constexpr float PrisonSpearThick = 20.0f;
	constexpr float PrisonOrbTurn = 220.0f;
	constexpr float PrisonOrbForm = 0.2f;
	constexpr float PrisonOrbFlySeconds = 0.12f;
	constexpr float PrisonAimHeight = 70.0f;
	// 94차 4 멈춘 파편: 터짐 둘(분신 파편 · 람파지 결정)의 크기 · 높이 · 붙잡는 때(파편이 막 퍼진 순간) · 붙잡은 빠르기
	constexpr float PrisonFrozenShardScale = 1.2f;
	constexpr float PrisonFrozenBurstScale = 1.1f;
	constexpr float PrisonFrozenLift = 60.0f;
	constexpr float PrisonFrozenHoldAfter = 0.1f;
	constexpr float PrisonFrozenDilation = 0.02f;
	// 95차 「저 연기가 갑자기 생기는데 자연스럽게」: 처음 크기 비율 · 느리게 피는 빠르기 · 다 피는 시간(그동안 크기는 처음 → 1, 빠르기는
	// 느림 → 멈춤으로 부드럽게) — 0.1초 만에 다 핀 채 멈추던 것을 0.7초에 걸쳐 피어나게
	constexpr float PrisonGrowFrom = 0.35f;
	constexpr float PrisonGrowDilation = 0.35f;
	constexpr float PrisonGrowSeconds = 0.7f;
	// 94차 Q 팩 칼 궤적(QSlash 7~9): 리본 메시 둘(aurora_qribbon_art.py) · 팩 칼 궤적 재질 사본 둘(aurora_frost_materials_build.py qtrail —
	// Fade·Brightness를 더함) · 밝기(갤러리 aurora-94th-qgallery: 메시 꼬리 재질은 1이면 어두운 수련장에서 거의 안 보이고 3에서 결이 보였다,
	// 평타 칼 궤적 재질은 입자 색 없이 점가루처럼 흐려 더 세게) · 꼭대기를 따라가는 오로라 평타 눈송이
	const TCHAR* const QRibbonThinPath = TEXT("/Game/TopDown/Characters/Aurora/FX/Meshes/SM_Aurora_QRibbonThin.SM_Aurora_QRibbonThin");
	const TCHAR* const QRibbonWidePath = TEXT("/Game/TopDown/Characters/Aurora/FX/Meshes/SM_Aurora_QRibbonWide.SM_Aurora_QRibbonWide");
	const TCHAR* const QRibbonHairPath = TEXT("/Game/TopDown/Characters/Aurora/FX/Meshes/SM_Aurora_QRibbonHair.SM_Aurora_QRibbonHair");
	const TCHAR* const QTrailPrimaryPath = TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_QTrailPrimary.M_Aurora_QTrailPrimary");
	const TCHAR* const QTrailMeshPath = TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_QTrailMesh.M_Aurora_QTrailMesh");
	const TCHAR* const QTrailSnowPath =
		TEXT("/Game/ParagonAurora/FX/Particles/Abilities/Primary/FX/P_Aurora_Primary_Snowflakes.P_Aurora_Primary_Snowflakes");
	constexpr float QTrailMeshBrightness = 3.0f;
	constexpr float QTrailPrimaryBrightness = 6.0f;
	// 93차 D 착지 팩 결정 파열 크기 · 둘레 조각 개수 · 그 자리(착지 반경 비율) · 크기 · 얼린 대상마다 터질 때 크기
	constexpr float CryoSwapBurst = 1.8f;
	constexpr int32 CryoSwapFragments = 6;
	constexpr float CryoSwapFragmentReach = 0.45f;
	constexpr float CryoSwapFragmentScale = 0.8f;
	constexpr float CryoSwapEchoBurst = 0.9f;
	// F 입체 덩어리: 가장 긴 변 길이(1 바위 · 2 창의 굵기 쪽) · 창 길이 배율 · 커지는 시간 · 위아래 흔들림(cm · 초당 번) · 떠 있을 때 도는
	// 빠르기 · 날 때 도는 빠르기(바위만) · 매만지는 간격(초)
	// 90차 촬영에서 쿼터뷰로 작아 보여(바위 70 · 창 34) 30%쯤 키움
	constexpr float ChunkRockSize = 90.0f;
	constexpr float ChunkSpearSize = 44.0f;
	constexpr float ChunkSpearStretch = 4.0f;
	constexpr float ChunkMeshForm = 0.22f;
	constexpr float ChunkMeshBob = 6.0f;
	constexpr float ChunkMeshBobRate = 1.5f;
	constexpr float ChunkIdleSpin = 70.0f;
	constexpr float ChunkFlightSpin = 900.0f;
	constexpr float ChunkMeshTickSeconds = 1.0f / 60.0f;
	constexpr float ChunkThrowScale = 0.6f;
	constexpr float ChunkTrailScale = 1.0f;
	constexpr float ChunkFrostTrailThin = 0.35f;
	constexpr float ChunkFrostTrailSpear = 0.5f;
	// 93차 FChunk 3 얼음송곳: 메시(aurora_spear_art.py 각진 결정 창, 긴 축 +Z · 끝 +Z) · 재질(D 고드름 비 시안 1의 짙푸른 빛나는 얼음) ·
	// 길이 · 굵기(D 고드름 비에서 결정은 원뿔 굵기 16의 1.6배라야 바늘로 안 보였다) · 떠 있을 때·날 때 제 축으로 도는 빠르기 · 쏠 때 번쩍 크기
	const TCHAR* const IcicleMeshPath = TEXT("/Game/TopDown/Characters/Aurora/FX/Meshes/SM_Aurora_IceSpear.SM_Aurora_IceSpear");
	const TCHAR* const IcicleMaterialPath = TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_SpearIce.M_Aurora_SpearIce");
	// 93차 첫 촬영(aurora-93rd-final): 120 · 24는 쿼터뷰에서 바늘처럼 작게 보여 키움
	constexpr float IcicleLength = 160.0f;
	constexpr float IcicleThick = 32.0f;
	constexpr float IcicleIdleTwist = 90.0f;
	constexpr float IcicleDrillTwist = 1080.0f;
	constexpr float IcicleLaunchFlash = 0.6f;
	// 95차 F 「애니메이션 다른 거 없을까」 — 쏘는 순간(시전 0.5초)이 동작의 칼끝·손끝이 앞으로 나가는 때에 오게 빠르기를 맞춘다.
	// A(Emote_Slice 앞 · Recall · Ability_R_InPlace)·E·S·V(Cast)가 쓰는 구간은 피함
	TAutoConsoleVariable<int32> CVarAuroraFMotion(
		TEXT("Aurora.FX.FMotion"), 1,
		TEXT("F cast motion: 1 she raises the sword high and chops down as the swords fire (Primary_Attack_Slow_C, default), 2 she cuts down and thrusts her left hand forward commanding them (Emote_Slice 1.00-1.75 s), 3 she aims her sword at the target (Ability_Q_Targeting_Intro), 0 the old dash lunge (Ability_Q)."));
	struct FLanceMotion
	{
		const TCHAR* Name;
		float Start;
		// 쏘는 순간(시전 ActionTime)에 와야 할 동작 시각
		float Fire;
	};
	const FLanceMotion LanceMotions[] = {
		{TEXT("Primary_Attack_Slow_C"), 0.0f, 0.42f},
		{TEXT("Emote_Slice"), 1.0f, 1.75f},
		{TEXT("Ability_Q_Targeting_Intro"), 0.0f, 0.40f}};
	// 94차 F 4·5 얼음 검(「고드름 퀄리티가 왜 저래 — 캐릭터 톤이랑 어울렸으면」): 오로라 검 사본 크기(원래 칼 길이의 배) · 생길 때 팩 검 소환 번쩍
	// 첫 촬영(aurora-94th-rest) 1.4는 쿼터뷰에서 가는 막대로 작게 보여 키움 · 날 때 도약 꼬리(0.5는 화면을 가로지르는 흰 연기 줄로 오래 남음)는 가늘게
	constexpr float SwordScale = 1.8f;
	constexpr float SwordTrail = 0.2f;
	constexpr float SwordSpawnFlash = 0.7f;
	const TCHAR* const SwordSpawnPath = TEXT("/Game/ParagonAurora/FX/Particles/Aurora/P_Aurora_Sword_Spawn.P_Aurora_Sword_Spawn");

	UStaticMesh* LoadIcicleMesh()
	{
		return TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(IcicleMeshPath)).LoadSynchronous();
	}

	// 메시 크기에서 길이·굵기를 맞춘 축마다 배율
	FVector SpearScale(const UStaticMesh* Mesh, float Length, float Thick)
	{
		const FVector Extent = Mesh ? Mesh->GetBounds().BoxExtent : FVector(50.0f);
		return FVector(Thick / FMath::Max(2.0f * Extent.X, 1.0f), Thick / FMath::Max(2.0f * Extent.Y, 1.0f),
			Length / FMath::Max(2.0f * Extent.Z, 1.0f));
	}

	FVector IcicleScale(const UStaticMesh* Mesh)
	{
		return SpearScale(Mesh, IcicleLength, IcicleThick);
	}
	// A-1 가시 크기(조합 0.55는 쿼터뷰에서 거의 안 보여 키움) · 부서지는 때 · 바닥 섬광 · 손 위 얼음 높이·크기
	constexpr float ArmorSpikeScale = 0.8f;
	constexpr float ArmorSpikeBreak = 0.8f;
	constexpr float ArmorFlashScale = 0.7f;
	constexpr float ArmorHandIceLift = 150.0f;
	constexpr float ArmorHandIceScale = 2.0f;
	// A-2 고드름 판: 개수 · 몸에서 떨어진 거리 · 크기 · 다 솟은 뒤 멈춰 세우는 때 · 멈춘 빠르기(E 둘레 결정과 같은 방법 — 55차)
	constexpr int32 ArmorPlateCount = 4;
	constexpr float ArmorPlateRadius = 70.0f;
	constexpr float ArmorPlateScale = 0.4f;
	constexpr float ArmorPlateHoldAfter = 1.3f;
	constexpr float ArmorPlateHoldDilation = 0.02f;
}

bool UAuroraSkillComponent::SpawnDecoyPose(const FVector& Feet, float Yaw)
{
	const int32 Pose = CVarAuroraWPose.GetValueOnGameThread();
	USkeletalMeshComponent* Body = Character.IsValid() ? Character->GetMesh() : nullptr;
	UAnimSequence* Anim = Pose == 3 ? DashAimIntroAnimation.Get() : ChargeLungeAnimation.Get();
	UMaterialInterface* Ice = Pose >= 1 && Pose <= 3 ? CloneIceMaterial.LoadSynchronous() : nullptr;
	if (!Ice || !Body || !Anim || !GetWorld())
	{
		return false;
	}
	// 캐릭터 메시 사본(F·R 분신과 같은 방식)을 그 자세로 굳힌다. 충돌·내비는 메시를 끼우기 전에 끈다(SpawnTimedMesh와 같은 까닭).
	USkeletalMeshComponent* Clone = NewObject<USkeletalMeshComponent>(Character.Get());
	Clone->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Clone->SetCanEverAffectNavigation(false);
	Clone->SetSkeletalMesh(Body->GetSkeletalMeshAsset());
	Clone->SetUsingAbsoluteLocation(true);
	Clone->SetUsingAbsoluteRotation(true);
	Clone->SetUsingAbsoluteScale(true);
	Clone->SetWorldScale3D(Body->GetComponentScale());
	Clone->SetWorldLocationAndRotation(Feet, FRotator(0.0f, Yaw + Body->GetRelativeRotation().Yaw, 0.0f));
	Clone->RegisterComponent();
	for (int32 Slot = 0; Slot < Clone->GetNumMaterials(); ++Slot)
	{
		Clone->SetMaterial(Slot, Ice);
	}
	Clone->SetAnimationMode(EAnimationMode::AnimationSingleNode);
	Clone->PlayAnimation(Anim, false);
	Clone->SetPosition(DecoyPoseTimes[Pose - 1], false);
	Clone->SetPlayRate(0.0f);
	DecoyClone = Clone;
	UE_LOG(LogTemp, Display, TEXT("AURORA_DECOY pose=%d anim=%s at=%.2f feet=%s"), Pose, *Anim->GetName(), DecoyPoseTimes[Pose - 1],
		*Feet.ToCompactString());
	return true;
}

int32 UAuroraSkillComponent::GetSpaceLook() const
{
	return CVarAuroraSpaceLook.GetValueOnGameThread();
}

void UAuroraSkillComponent::SpaceFragment(const FVector& Spot, const FVector& Direction)
{
	// 지나온 길(WallStep 간격)에 오로라 분신 조각이 흩날린다 — 바닥에 남는 것은 없다
	SpawnBurstLater(DecoyFragmentsFx, Spot + FVector(0.0f, 0.0f, 40.0f), SpaceFragmentScale, 0.0f, Direction.Rotation());
}

void UAuroraSkillComponent::SpaceArrival(const FVector& Feet, const FVector& Direction)
{
	const FVector Ahead = Feet + Direction * SpaceArrivalAhead;
	SpawnBurstLater(RockHitBurst, Ahead, SpaceArrivalBurst, 0.0f);
	SpawnBurstLater(CryoInitialBlast, Ahead, SpaceArrivalFlash, 0.0f);
	UE_LOG(LogTemp, Display, TEXT("AURORA_SPACE arrival at=%s"), *Ahead.ToCompactString());
}

void UAuroraSkillComponent::BeginRPrison(const FVector& Center, float BreakAfter, AActor* Target)
{
	PrisonTarget = Target;
	// 앞 감옥이 남아 있으면(재사용 대기 무시 시험) 터뜨리지 않고 치운다
	for (const TWeakObjectPtr<UParticleSystemComponent>& Old : PrisonRing)
	{
		if (UParticleSystemComponent* Ring = Old.Get())
		{
			OwnedEffects.Remove(Ring);
			Ring->DestroyComponent();
		}
	}
	PrisonRing.Reset();
	ClearPrisonOrbs();
	PrisonLook = CVarAuroraRPrison.GetValueOnGameThread();
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	PrisonCenter = Center;
	switch (PrisonLook)
	{
	case 1:
		for (int32 Index = 0; IcicleWallsFx && Index < PrisonCount; ++Index)
		{
			const float Angle = 360.0f * Index / PrisonCount;
			const FVector Spot = Center + FRotator(0.0f, Angle, 0.0f).Vector() * PrisonRadius;
			// 고드름 무더기는 바깥을 본다
			if (UParticleSystemComponent* Ring = SpawnOwnedEffect(IcicleWallsFx, Spot, FRotator(0.0f, Angle, 0.0f)))
			{
				Ring->SetWorldScale3D(FVector(PrisonScale));
				PrisonRing.Add(Ring);
			}
		}
		break;
	case 2:
	{
		// E 원본 냉기 회오리(P_Aurora_Freeze_Whrilwind)를 대상 발밑에 크게 — 분신이 베는 동안 대상을 감싼다
		const FAuroraSkillDefinition* Freeze = Skills.Find(EAuroraSkill::Hoarfrost);
		if (UParticleSystemComponent* Swirl = Freeze && Freeze->CastEffect ? SpawnOwnedEffect(Freeze->CastEffect, Center) : nullptr)
		{
			Swirl->SetWorldScale3D(FVector(PrisonSwirlScale));
			PrisonRing.Add(Swirl);
			const TWeakObjectPtr<UParticleSystemComponent> WeakSwirl = Swirl;
			World->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, [WeakSwirl]()
			{
				if (UParticleSystemComponent* Held = WeakSwirl.Get())
				{
					Held->CustomTimeDilation = PrisonSwirlHoldDilation;
				}
			}), PrisonSwirlHoldAfter, false);
		}
		break;
	}
	case 4:
	{
		// 분신 파편 · 람파지 얼음 결정 터짐이 막 퍼진 순간 거의 멈춰 세운다 — 터질 때 제 빠르기로 풀려 바깥으로 날아간다(BreakRPrison)
		const FVector Burst = Center + FVector(0.0f, 0.0f, PrisonFrozenLift);
		for (const TPair<UParticleSystem*, float>& Each : {TPair<UParticleSystem*, float>(DecoyExplode.Get(), PrisonFrozenShardScale),
			TPair<UParticleSystem*, float>(RockHitBurst.Get(), PrisonFrozenBurstScale)})
		{
			if (UParticleSystemComponent* Frozen = Each.Key ? SpawnOwnedEffect(Each.Key, Burst) : nullptr)
			{
				Frozen->SetWorldScale3D(FVector(Each.Value));
				PrisonRing.Add(Frozen);
			}
		}
		// 95차: 0.1초에 다 핀 채 멈춰 세우던 것(「갑자기 생긴다」) 대신 느리게 띄워 작게서 키우며 멈춰 간다(PrisonGrowTick)
		PrisonGrowBorn = World->GetTimeSeconds();
		World->GetTimerManager().SetTimer(PrisonGrowTimer, this, &UAuroraSkillComponent::PrisonGrowTick, 1.0f / 60.0f, true);
		PrisonGrowTick();
		break;
	}
	case 5:
		// 대상이 오로라 원본 빙결(D와 같은 얼음)에 갇힌다 — 터질 때 같이 깨진다(AttachTimedEffect가 그때 걷음)
		if (AActor* Sealed = PrisonTarget.Get())
		{
			AttachTimedEffect(CryoFrozen, Sealed, BreakAfter);
		}
		break;
	case 3:
	{
		// 창은 크기 0에 가깝게 띄워 두고 PrisonOrbTick이 키우며 돌린다(충돌·내비는 SpawnTimedMesh가 먼저 끈다) — F 얼음송곳과 같은 메시·재질
		UStaticMesh* Spear = LoadIcicleMesh();
		UMaterialInterface* SpearIce = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(IcicleMaterialPath)).LoadSynchronous();
		for (int32 Index = 0; Spear && Index < PrisonOrbCount; ++Index)
		{
			if (UStaticMeshComponent* Orb = SpawnTimedMesh(Spear, FTransform(FRotator::ZeroRotator, Center, FVector(0.001f)),
				BreakAfter + PrisonOrbFlySeconds + 1.0f))
			{
				for (int32 Slot = 0; SpearIce && Slot < Orb->GetNumMaterials(); ++Slot)
				{
					Orb->SetMaterial(Slot, SpearIce);
				}
				Orb->SetCastShadow(false);
				Orb->SetReceivesDecals(false);
				PrisonOrbs.Add(Orb);
			}
		}
		PrisonOrbBorn = World->GetTimeSeconds();
		PrisonOrbScatter = -1.0;
		if (!PrisonOrbs.IsEmpty())
		{
			World->GetTimerManager().SetTimer(PrisonOrbTimer, this, &UAuroraSkillComponent::PrisonOrbTick, ChunkMeshTickSeconds, true);
			PrisonOrbTick();
		}
		break;
	}
	default:
		return;
	}
	World->GetTimerManager().SetTimer(AddReleaseTimer(), this, &UAuroraSkillComponent::BreakRPrison, BreakAfter, false);
	UE_LOG(LogTemp, Display, TEXT("AURORA_RPRISON start look=%d rings=%d orbs=%d break=%.2f"), PrisonLook, PrisonRing.Num(), PrisonOrbs.Num(),
		BreakAfter);
}

void UAuroraSkillComponent::PrisonGrowTick()
{
	UWorld* World = GetWorld();
	const float Age = World ? static_cast<float>(World->GetTimeSeconds() - PrisonGrowBorn) : PrisonGrowSeconds;
	const float Alpha = FMath::Clamp(Age / PrisonGrowSeconds, 0.0f, 1.0f);
	const float Size = FMath::InterpEaseOut(PrisonGrowFrom, 1.0f, Alpha, 2.0f);
	const float Speed = FMath::InterpEaseIn(PrisonGrowDilation, PrisonFrozenDilation, Alpha, 2.0f);
	const float Scales[] = {PrisonFrozenShardScale, PrisonFrozenBurstScale};
	for (int32 Index = 0; Index < PrisonRing.Num(); ++Index)
	{
		if (UParticleSystemComponent* Growing = PrisonRing[Index].Get())
		{
			Growing->SetWorldScale3D(FVector(Scales[FMath::Min(Index, 1)] * Size));
			Growing->CustomTimeDilation = Speed;
		}
	}
	if (Alpha >= 1.0f || PrisonRing.IsEmpty() || PrisonLook != 4)
	{
		if (World)
		{
			World->GetTimerManager().ClearTimer(PrisonGrowTimer);
		}
	}
}

void UAuroraSkillComponent::PrisonOrbTick()
{
	UWorld* World = GetWorld();
	if (!World)
	{
		ClearPrisonOrbs();
		return;
	}
	const double Now = World->GetTimeSeconds();
	const float Age = static_cast<float>(Now - PrisonOrbBorn);
	const float Fly = PrisonOrbScatter < 0.0 ? 0.0f : static_cast<float>(Now - PrisonOrbScatter);
	if (Fly > PrisonOrbFlySeconds)
	{
		ClearPrisonOrbs();
		return;
	}
	const float Grow = FMath::InterpEaseOut(0.05f, 1.0f, FMath::Min(Age / PrisonOrbForm, 1.0f), 2.0f);
	// 터질 땐(Converge 0 → 1) 겨눈 채 가운데로 꽂혀 든다
	const float Converge = FMath::Clamp(Fly / PrisonOrbFlySeconds, 0.0f, 1.0f);
	const FVector Aim = PrisonCenter + FVector(0.0f, 0.0f, PrisonAimHeight);
	for (int32 Index = 0; Index < PrisonOrbs.Num(); ++Index)
	{
		UStaticMeshComponent* Orb = PrisonOrbs[Index].Get();
		if (!IsValid(Orb))
		{
			continue;
		}
		const float Angle = 360.0f * Index / PrisonOrbs.Num() + PrisonOrbTurn * Age;
		const float Bob = 12.0f * FMath::Sin(Age * 2.0f * PI * 1.2f + Index) * (1.0f - Converge);
		const FVector Ring = PrisonCenter + FRotator(0.0f, Angle, 0.0f).Vector() * PrisonOrbRadius + FVector(0.0f, 0.0f, PrisonOrbHeight + Bob);
		const FVector At = FMath::Lerp(Ring, Aim, Converge * 0.85f);
		// 끝(+Z)이 대상 몸통을 본다
		Orb->SetWorldLocationAndRotation(At, FRotationMatrix::MakeFromZ((Aim - At).GetSafeNormal()).ToQuat());
		Orb->SetWorldScale3D(SpearScale(Orb->GetStaticMesh(), PrisonSpearLength, PrisonSpearThick) * Grow);
	}
}

void UAuroraSkillComponent::ClearPrisonOrbs()
{
	for (const TWeakObjectPtr<UStaticMeshComponent>& Each : PrisonOrbs)
	{
		RemoveTimedMesh(Each.Get(), nullptr);
	}
	PrisonOrbs.Reset();
	PrisonOrbScatter = -1.0;
	if (GetWorld())
	{
		GetWorld()->GetTimerManager().ClearTimer(PrisonOrbTimer);
	}
}

void UAuroraSkillComponent::BreakRPrison()
{
	if (GetWorld())
	{
		GetWorld()->GetTimerManager().ClearTimer(PrisonGrowTimer);
	}
	// 5(대상 빙결)는 붙인 이펙트를 AttachTimedEffect가 걷으니 여기 남은 것이 없어도 큰 터짐은 낸다
	if (PrisonRing.IsEmpty() && PrisonOrbs.IsEmpty() && PrisonLook != 5)
	{
		return;
	}
	int32 Broken = 0;
	for (const TWeakObjectPtr<UParticleSystemComponent>& Each : PrisonRing)
	{
		UParticleSystemComponent* Ring = Each.Get();
		if (!Ring)
		{
			continue;
		}
		++Broken;
		if (PrisonLook == 2 || PrisonLook == 4)
		{
			// 회오리는 새로 뿜는 것만 멈추고 남은 입자는 흩어지게 둔다
			ReleaseOwnedEffect(Ring);
			continue;
		}
		SpawnBurstLater(FreezeSegmentCrumble, Ring->GetComponentLocation(), PrisonCrumbleScale, 0.0f);
		OwnedEffects.Remove(Ring);
		Ring->DestroyComponent();
	}
	PrisonRing.Reset();
	if (!PrisonOrbs.IsEmpty() && GetWorld())
	{
		// 돌던 창은 한꺼번에 가운데로 꽂힌다(PrisonOrbTick이 PrisonOrbFlySeconds 동안 날리고 치운다) — 가운데 큰 터짐은 아래에서 같이
		Broken += PrisonOrbs.Num();
		PrisonOrbScatter = GetWorld()->GetTimeSeconds();
	}
	SpawnBurstLater(CryoExplode, PrisonCenter, PrisonBreakScale, 0.0f);
	UE_LOG(LogTemp, Display, TEXT("AURORA_RPRISON break rings=%d at=%s"), Broken, *PrisonCenter.ToCompactString());
}

bool UAuroraSkillComponent::UseQBurst() const
{
	return CVarAuroraQBurst.GetValueOnGameThread() != 0;
}

int32 UAuroraSkillComponent::GetQSlash() const
{
	return CVarAuroraQSlash.GetValueOnGameThread();
}

UStaticMesh* UAuroraSkillComponent::LoadQRibbon(bool bThin) const
{
	return TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(bThin ? QRibbonThinPath : QRibbonWidePath)).LoadSynchronous();
}

UMaterialInterface* UAuroraSkillComponent::LoadQTrailMaterial(bool bPrimary) const
{
	return TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(bPrimary ? QTrailPrimaryPath : QTrailMeshPath)).LoadSynchronous();
}

float UAuroraSkillComponent::GetQTrailBrightness(bool bPrimary) const
{
	return bPrimary ? QTrailPrimaryBrightness : QTrailMeshBrightness;
}

UStaticMesh* UAuroraSkillComponent::LoadQRibbonHair() const
{
	return TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(QRibbonHairPath)).LoadSynchronous();
}

UParticleSystem* UAuroraSkillComponent::LoadQTrailSnow() const
{
	return TSoftObjectPtr<UParticleSystem>(FSoftObjectPath(QTrailSnowPath)).LoadSynchronous();
}

bool UAuroraSkillComponent::UseFBurst() const
{
	return CVarAuroraFBurst.GetValueOnGameThread() != 0;
}

void UAuroraSkillComponent::PolishHitBurst(const FVector& Where, float Scale)
{
	SpawnBurstLater(RockHitBurst, Where, Scale, 0.0f);
}

void UAuroraSkillComponent::SpawnCryoShards(const FVector& Center, int32 Count, bool bHeavy, float Reach, bool bEcho)
{
	switch (CVarAuroraDShard.GetValueOnGameThread())
	{
	case 0:
		SpawnIceBurst(Center, Count, bHeavy, Reach);
		break;
	case 2:
		// 바닥에 남는 조각 대신 그 자리에서 크게 터지고 끝나는 팩 효과 — 착지엔 가운데 결정 파열 + 둘레에서 바깥을 보고 흩어지는 분신 조각,
		// 얼린 대상마다 터질 땐 작은 결정 파열만
		SpawnBurstLater(RockHitBurst, Center, bEcho ? CryoSwapEchoBurst : CryoSwapBurst, 0.0f);
		for (int32 Index = 0; !bEcho && Index < CryoSwapFragments; ++Index)
		{
			const FRotator Out(0.0f, 360.0f * Index / CryoSwapFragments, 0.0f);
			SpawnBurstLater(DecoyFragmentsFx, Center + Out.Vector() * Reach * CryoSwapFragmentReach + FVector(0.0f, 0.0f, 40.0f),
				CryoSwapFragmentScale, 0.0f, Out);
		}
		break;
	default:
		break;
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_DSHARD look=%d echo=%d"), CVarAuroraDShard.GetValueOnGameThread(), bEcho);
}

int32 UAuroraSkillComponent::GetAPolish() const
{
	return CVarAuroraAPolish.GetValueOnGameThread();
}

void UAuroraSkillComponent::SpawnArmorPolish(int32 Look)
{
	if (!Character.IsValid() || !GetWorld())
	{
		return;
	}
	const FVector Feet = GetFeetLocation();
	SpawnBurstLater(CryoInitialBlast, Feet, ArmorFlashScale, 0.0f);
	if (Look == 1)
	{
		// A-1: 몸에서 가시가 확 솟았다가 부서져 흩어진다(그 뒤엔 보호막 껍질만)
		UParticleSystemComponent* Spikes = SpawnOwnedEffect(DecoyFrostFx, Feet, FRotator(0.0f, Character->GetActorRotation().Yaw, 0.0f));
		if (Spikes)
		{
			Spikes->SetWorldScale3D(FVector(ArmorSpikeScale));
		}
		SpawnBurstLater(HandIceFx, Feet + FVector(0.0f, 0.0f, ArmorHandIceLift), ArmorHandIceScale, 0.0f);
		const TWeakObjectPtr<UParticleSystemComponent> WeakSpikes = Spikes;
		GetWorld()->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, [this, WeakSpikes, Feet]()
		{
			if (UParticleSystemComponent* Done = WeakSpikes.Get())
			{
				OwnedEffects.Remove(Done);
				Done->DestroyComponent();
			}
			SpawnBurstLater(FreezeSegmentCrumble, Feet, 1.0f, 0.0f);
			SpawnBurstLater(DecoyExplode, Feet + FVector(0.0f, 0.0f, 60.0f), 0.6f, 0.0f);
		}), ArmorSpikeBreak, false);
		UE_LOG(LogTemp, Display, TEXT("AURORA_APOLISH look=1 spikes=%d"), Spikes != nullptr);
		return;
	}
	// A-2: 몸 둘레 가까이 고드름 판이 솟아 몸에 붙어 따라다닌다 — 다 솟으면 거의 멈춰 세워 켜진 동안 남긴다
	EndArmorPolish();
	USceneComponent* Root = Character->GetRootComponent();
	const float Down = Feet.Z - Character->GetActorLocation().Z;
	for (int32 Index = 0; Root && IcicleWallsFx && Index < ArmorPlateCount; ++Index)
	{
		const float Angle = 45.0f + 360.0f * Index / ArmorPlateCount;
		const FVector Offset = FRotator(0.0f, Angle, 0.0f).Vector() * ArmorPlateRadius + FVector(0.0f, 0.0f, Down);
		UParticleSystemComponent* Plate = UGameplayStatics::SpawnEmitterAttached(IcicleWallsFx, Root, NAME_None, Offset,
			FRotator(0.0f, Angle, 0.0f), FVector(ArmorPlateScale), EAttachLocation::KeepRelativeOffset, false);
		if (Plate)
		{
			OwnedEffects.Add(Plate);
			ArmorPlates.Add(Plate);
		}
	}
	SpawnBurstLater(FreezeRooted, Feet, 1.0f, 0.0f);
	GetWorld()->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, [this]()
	{
		for (const TWeakObjectPtr<UParticleSystemComponent>& Each : ArmorPlates)
		{
			if (UParticleSystemComponent* Plate = Each.Get())
			{
				Plate->CustomTimeDilation = ArmorPlateHoldDilation;
			}
		}
	}), ArmorPlateHoldAfter, false);
	UE_LOG(LogTemp, Display, TEXT("AURORA_APOLISH look=2 plates=%d"), ArmorPlates.Num());
}

bool UAuroraSkillComponent::PlayArmorMotion()
{
	const int32 Motion = CVarAuroraAMotion.GetValueOnGameThread();
	USkeletalMeshComponent* Body = Character.IsValid() ? Character->GetMesh() : nullptr;
	if (Motion < 1 || Motion > static_cast<int32>(UE_ARRAY_COUNT(ArmorMotions)) || !Body || !GetWorld())
	{
		return false;
	}
	const FArmorMotion& Pick = ArmorMotions[Motion - 1];
	UAnimSequence* Anim = TSoftObjectPtr<UAnimSequence>(FSoftObjectPath(FString::Printf(
		TEXT("/Game/ParagonAurora/Characters/Heroes/Aurora/Animations/%s.%s"), Pick.Name, Pick.Name))).LoadSynchronous();
	if (!Anim)
	{
		return false;
	}
	// 시작 자세에서 다 든 자세(Peak)까지를 시전 시간(보호막이 생기는 때 — ApplyArmorTiming이 늘려 둔 값)에 맞춘다
	const float Raise = Skills[EAuroraSkill::IceArmor].ActionTime;
	const float Rate = (Pick.Peak - Pick.Start) / Raise;
	PlayFullBody(Anim, Rate, Pick.Start, 1, ArmorReachBlendIn);
	const TWeakObjectPtr<UAnimMontage> Montage = ActiveMontage;
	const TWeakObjectPtr<USkeletalMeshComponent> WeakBody = Body;
	GetWorld()->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, [Montage, WeakBody]()
	{
		// 다 든 자세에서 멈춰 세운다 — 회복(ArmorHoldSeconds)이 끝나며 FinishCast가 섞어 내린다
		UAnimInstance* Instance = WeakBody.IsValid() ? WeakBody->GetAnimInstance() : nullptr;
		if (Instance && Montage.IsValid() && Instance->Montage_IsPlaying(Montage.Get()))
		{
			Instance->Montage_SetPlayRate(Montage.Get(), 0.0f);
		}
	}), Raise, false);
	UE_LOG(LogTemp, Display, TEXT("AURORA_AMOTION motion=%d anim=%s from=%.2f to=%.2f rate=%.2f"), Motion, Pick.Name, Pick.Start, Pick.Peak, Rate);
	return true;
}

void UAuroraSkillComponent::ApplyArmorTiming()
{
	const int32 Motion = CVarAuroraAMotion.GetValueOnGameThread();
	const bool bDraft = Motion >= 1 && Motion <= static_cast<int32>(UE_ARRAY_COUNT(ArmorMotions));
	FAuroraSkillDefinition& Armor = Skills[EAuroraSkill::IceArmor];
	Armor.ActionTime = bDraft ? ArmorMotionRaise : ArmorRaiseSeconds;
	Armor.RecoveryTime = bDraft ? ArmorMotionHold : ArmorHoldSeconds;
}

int32 UAuroraSkillComponent::GetAShell() const
{
	return CVarAuroraAShell.GetValueOnGameThread();
}

void UAuroraSkillComponent::BeginArmorSkin()
{
	EndArmorSkin();
	const int32 Look = GetAShell();
	USkeletalMeshComponent* Body = Character.IsValid() ? Character->GetMesh() : nullptr;
	if (!Body || !GetWorld())
	{
		return;
	}
	if (Look == 2)
	{
		// 몸 위에 같은 몸을 한 번 더, 가장자리만 빛나는 얇은 얼음으로 겹쳐 그린다(겹 재질 — 보호막 구 없이 몸이 얼음 막에 덮임)
		if (UMaterialInterface* Skin = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(ArmorSkinPath)).LoadSynchronous())
		{
			// 첫 촬영(aurora-94th-rest): 재질 기본값(밝기 1.4 · 테 3)은 쿼터뷰에서 살짝 희어지는 정도라 더 세게, 테를 넓게
			UMaterialInstanceDynamic* Glaze = UMaterialInstanceDynamic::Create(Skin, Body);
			Glaze->SetScalarParameterValue(TEXT("Brightness"), ArmorSkinBrightness);
			Glaze->SetScalarParameterValue(TEXT("RimPower"), ArmorSkinRim);
			Body->SetOverlayMaterial(Glaze);
			bArmorSkin = true;
		}
	}
	else if (Look == 3)
	{
		// 오로라 분신(W)의 몸 서리 둘을 몸 메시에 붙여 다 자라면 거의 멈춰 세운다(55차 E 둘레 결정 · A-2 고드름 판과 같은 방법)
		TArray<TWeakObjectPtr<UParticleSystemComponent>> Grown;
		for (const TCHAR* Path : ArmorFrostPaths)
		{
			UParticleSystem* Fx = TSoftObjectPtr<UParticleSystem>(FSoftObjectPath(Path)).LoadSynchronous();
			if (UParticleSystemComponent* Frost = Fx ? UGameplayStatics::SpawnEmitterAttached(Fx, Body, NAME_None) : nullptr)
			{
				Frost->SetActorParameter(TEXT("VertSurfaceActor"), Character.Get());
				OwnedEffects.Add(Frost);
				ArmorPlates.Add(Frost);
				Grown.Add(Frost);
			}
		}
		GetWorld()->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, [Grown]()
		{
			for (const TWeakObjectPtr<UParticleSystemComponent>& Each : Grown)
			{
				if (UParticleSystemComponent* Held = Each.Get())
				{
					Held->CustomTimeDilation = ArmorFrostDilation;
				}
			}
		}), ArmorFrostHoldAfter, false);
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_ASHELL look=%d skin=%d plates=%d"), Look, bArmorSkin, ArmorPlates.Num());
}

void UAuroraSkillComponent::EndArmorSkin()
{
	if (!bArmorSkin)
	{
		return;
	}
	bArmorSkin = false;
	if (USkeletalMeshComponent* Body = Character.IsValid() ? Character->GetMesh() : nullptr)
	{
		Body->SetOverlayMaterial(nullptr);
		// 얼음 막이 깨져 흩어진다
		SpawnBurstLater(DecoyExplode, Body->GetComponentLocation() + FVector(0.0f, 0.0f, 90.0f), 0.5f, 0.0f);
	}
}

void UAuroraSkillComponent::EndArmorPolish()
{
	for (const TWeakObjectPtr<UParticleSystemComponent>& Each : ArmorPlates)
	{
		if (UParticleSystemComponent* Plate = Each.Get())
		{
			SpawnBurstLater(FreezeSegmentCrumble, Plate->GetComponentLocation(), 0.6f, 0.0f);
			OwnedEffects.Remove(Plate);
			Plate->DestroyComponent();
		}
	}
	ArmorPlates.Reset();
}

int32 UAuroraSkillComponent::GetSPolish() const
{
	return CVarAuroraSPolish.GetValueOnGameThread();
}

void UAuroraSkillComponent::SetHasteAura(bool bOn)
{
	for (const TWeakObjectPtr<UParticleSystemComponent>& Each : HasteAura)
	{
		ReleaseOwnedEffect(Each.Get());
	}
	HasteAura.Reset();
	ClearHasteCrown();
	USkeletalMeshComponent* Body = Character.IsValid() ? Character->GetMesh() : nullptr;
	if (!bOn || GetSPolish() == 0 || !Body)
	{
		return;
	}
	if (GetSPolish() == 3 || GetSPolish() == 4)
	{
		SpawnHasteCrown();
	}
	// 몸 메시에 붙여야 몸 겉에서 뿜는다(단독 촬영 aurora-87th-catalog에선 둘 다 거의 빈 화면)
	for (UParticleSystem* Fx : {EnrageLoopFx.Get(), EnrageSparksFx.Get()})
	{
		if (UParticleSystemComponent* Aura = Fx ? UGameplayStatics::SpawnEmitterAttached(Fx, Body, NAME_None) : nullptr)
		{
			OwnedEffects.Add(Aura);
			HasteAura.Add(Aura);
		}
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_SPOLISH aura=%d"), HasteAura.Num());
}

void UAuroraSkillComponent::SpawnHasteCrown()
{
	USceneComponent* Root = Character.IsValid() ? Character->GetRootComponent() : nullptr;
	UStaticMesh* Gem = LoadIcicleMesh();
	UMaterialInterface* Ice = CloneIceMaterial.LoadSynchronous();
	if (!Root || !Gem || !GetWorld())
	{
		return;
	}
	// 몸(캡슐 가운데) 위 CrownLift에 도는 받침 — 몸을 따라가되 돌기는 HasteCrownTick이 따로(몸이 돌 때 같이 휙 돌지 않게)
	USceneComponent* Pivot = NewObject<USceneComponent>(Character.Get());
	Pivot->SetupAttachment(Root);
	Pivot->SetUsingAbsoluteRotation(true);
	Pivot->SetRelativeLocation(FVector(0.0f, 0.0f, CrownLift));
	Pivot->RegisterComponent();
	HasteCrownPivot = Pivot;
	for (int32 Index = 0; Index < CrownCount; ++Index)
	{
		const FVector Out = FRotator(0.0f, 360.0f * Index / CrownCount, 0.0f).Vector();
		const float Length = Index % 2 == 0 ? CrownTall : CrownShort;
		const FVector Axis = (FVector::UpVector + Out * FMath::Tan(FMath::DegreesToRadians(CrownTilt))).GetSafeNormal();
		UStaticMeshComponent* Crystal = NewObject<UStaticMeshComponent>(Character.Get());
		// 충돌·내비는 메시를 끼우기 전에 끈다(SpawnTimedMesh와 같은 까닭)
		Crystal->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Crystal->SetCanEverAffectNavigation(false);
		Crystal->SetStaticMesh(Gem);
		Crystal->SetCastShadow(false);
		for (int32 Slot = 0; Ice && Slot < Crystal->GetNumMaterials(); ++Slot)
		{
			Crystal->SetMaterial(Slot, Ice);
		}
		Crystal->SetupAttachment(Pivot);
		// 메시 가운데가 원점이라 밑동이 고리에 오게 길이 절반만큼 축 따라 올린다
		Crystal->SetRelativeLocationAndRotation(Out * CrownRadius + Axis * Length * 0.5f, FRotationMatrix::MakeFromZ(Axis).Rotator());
		Crystal->SetRelativeScale3D(SpearScale(Gem, Length, CrownThick) * 0.01f);
		Crystal->RegisterComponent();
		HasteCrown.Add(Crystal);
	}
	HasteCrownBorn = GetWorld()->GetTimeSeconds();
	SpawnBurstLater(HandIceFx, Pivot->GetComponentLocation(), 0.8f, 0.0f);
	GetWorld()->GetTimerManager().SetTimer(HasteCrownTimer, this, &UAuroraSkillComponent::HasteCrownTick, 1.0f / 30.0f, true);
	UE_LOG(LogTemp, Display, TEXT("AURORA_SCROWN gems=%d"), HasteCrown.Num());
}

void UAuroraSkillComponent::HasteCrownTick()
{
	USceneComponent* Pivot = HasteCrownPivot.Get();
	if (!Pivot || !GetWorld())
	{
		ClearHasteCrown();
		return;
	}
	const float Age = static_cast<float>(GetWorld()->GetTimeSeconds() - HasteCrownBorn);
	Pivot->SetWorldRotation(FRotator(0.0f, CrownSpin * Age, 0.0f));
	const float Grow = FMath::InterpEaseOut(0.01f, 1.0f, FMath::Clamp(Age / CrownForm, 0.0f, 1.0f), 2.0f);
	UStaticMesh* Gem = nullptr;
	for (int32 Index = 0; Index < HasteCrown.Num(); ++Index)
	{
		if (UStaticMeshComponent* Crystal = HasteCrown[Index].Get())
		{
			Gem = Crystal->GetStaticMesh();
			Crystal->SetRelativeScale3D(SpearScale(Gem, Index % 2 == 0 ? CrownTall : CrownShort, CrownThick) * Grow);
		}
	}
}

void UAuroraSkillComponent::ClearHasteCrown()
{
	if (GetWorld())
	{
		GetWorld()->GetTimerManager().ClearTimer(HasteCrownTimer);
	}
	if (USceneComponent* Pivot = HasteCrownPivot.Get())
	{
		SpawnBurstLater(DecoyFragmentsFx, Pivot->GetComponentLocation(), 0.4f, 0.0f);
	}
	for (const TWeakObjectPtr<UStaticMeshComponent>& Each : HasteCrown)
	{
		if (UStaticMeshComponent* Crystal = Each.Get())
		{
			Crystal->DestroyComponent();
		}
	}
	HasteCrown.Reset();
	if (USceneComponent* Pivot = HasteCrownPivot.Get())
	{
		Pivot->DestroyComponent();
	}
	HasteCrownPivot.Reset();
}

bool UAuroraSkillComponent::PlayLanceMotion()
{
	const int32 Motion = CVarAuroraFMotion.GetValueOnGameThread();
	if (Motion < 1 || Motion > static_cast<int32>(UE_ARRAY_COUNT(LanceMotions)))
	{
		return false;
	}
	const FLanceMotion& Pick = LanceMotions[Motion - 1];
	UAnimSequence* Anim = TSoftObjectPtr<UAnimSequence>(FSoftObjectPath(FString::Printf(
		TEXT("/Game/ParagonAurora/Characters/Heroes/Aurora/Animations/%s.%s"), Pick.Name, Pick.Name))).LoadSynchronous();
	if (!Anim)
	{
		return false;
	}
	const float Rate = (Pick.Fire - Pick.Start) / FMath::Max(Skills[EAuroraSkill::IceLance].ActionTime, 0.05f);
	PlayFullBody(Anim, Rate, Pick.Start);
	UE_LOG(LogTemp, Display, TEXT("AURORA_FMOTION motion=%d anim=%s from=%.2f fire=%.2f rate=%.2f"), Motion, Pick.Name, Pick.Start, Pick.Fire, Rate);
	return true;
}

int32 UAuroraSkillComponent::GetFChunk() const
{
	return CVarAuroraFChunk.GetValueOnGameThread();
}

void UAuroraSkillComponent::SpawnChunkMesh(int32 Index, const FVector& Spot, float Appear, float Life, float Phase)
{
	const int32 Look = GetFChunk();
	// 90차 첫 촬영(aurora-90th-fchunk): 스스로 빛나는 얼음(GlowIce)은 납작한 하늘색 덩어리로 보였다 → W 분신에서 밝게 읽힌 분신 얼음 재질
	UMaterialInterface* Ice = CVarAuroraFChunkSkin.GetValueOnGameThread() == 1 ? nullptr : CloneIceMaterial.LoadSynchronous();
	// 93차 3 얼음송곳은 각진 결정 창 메시에 짙푸른 빛나는 얼음 · 94차 4·5 검은 같은 메시를 숨겨 나르는 몸으로
	const bool bSword = Look == 4 || Look == 5;
	UStaticMesh* Shape = Look >= 3 ? LoadIcicleMesh() : IceChunkMesh.Get();
	if (Look == 3)
	{
		Ice = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(IcicleMaterialPath)).LoadSynchronous();
	}
	if (Look <= 0 || !Shape || !GetWorld())
	{
		return;
	}
	if (ChunkMeshes.Num() <= Index)
	{
		ChunkMeshes.SetNum(Index + 1);
	}
	// 메시는 크기 0에 가깝게 숨겨 두었다가 생길 차례(Appear)부터 ChunkMeshTick이 키운다. 충돌·내비는 SpawnTimedMesh가 먼저 끈다.
	UStaticMeshComponent* Mesh = SpawnTimedMesh(Shape, FTransform(FRotator::ZeroRotator, Spot, FVector(0.001f)), Appear + Life + 2.0f);
	if (!Mesh)
	{
		return;
	}
	for (int32 Slot = 0; Ice && Slot < Mesh->GetNumMaterials(); ++Slot)
	{
		Mesh->SetMaterial(Slot, Ice);
	}
	Mesh->SetCastShadow(false);
	Mesh->SetReceivesDecals(false);
	const FVector Extent = Shape->GetBounds().BoxExtent;
	const float Longest = FMath::Max(2.0f * Extent.GetMax(), 1.0f);
	FAuroraChunkMesh& Chunk = ChunkMeshes[Index];
	Chunk.Mesh = Mesh;
	Chunk.Trail.Reset();
	const double Now = GetWorld()->GetTimeSeconds();
	Chunk.Born = Now + Appear;
	Chunk.FiredAt = -1.0;
	Chunk.Deadline = Now + Appear + Life + 0.3;
	Chunk.Spot = Spot;
	Chunk.Phase = Phase;
	Chunk.SpinAxis = FVector(FMath::FRandRange(-1.0f, 1.0f), FMath::FRandRange(-1.0f, 1.0f), FMath::FRandRange(0.3f, 1.0f)).GetSafeNormal();
	Chunk.Scale = (Look == 2 ? ChunkSpearSize : ChunkRockSize) / Longest;
	Chunk.Sword.Reset();
	USkeletalMeshComponent* Body = Character.IsValid() ? Character->GetMesh() : nullptr;
	if (bSword && Body)
	{
		Mesh->SetVisibility(false);
		// 지금 몸 자세를 그대로 굳힌 캐릭터 메시 사본에서 칼 칸만 보이게 하고, 칼 가운데가 나르는 몸의 원점 · 칼끝 쪽이 +Z에 오게 붙인다
		UPoseableMeshComponent* Sword = NewObject<UPoseableMeshComponent>(Character.Get());
		Sword->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Sword->SetCanEverAffectNavigation(false);
		Sword->SetSkinnedAssetAndUpdate(Body->GetSkeletalMeshAsset());
		Sword->SetCastShadow(false);
		Sword->SetupAttachment(Mesh);
		Sword->RegisterComponent();
		Sword->CopyPoseFromSkeletalComponent(Body);
		UMaterialInstanceDynamic* Hidden = nullptr;
		if (UMaterialInterface* Clone = CloneIceMaterial.LoadSynchronous())
		{
			Hidden = UMaterialInstanceDynamic::Create(Clone, Sword);
			Hidden->SetScalarParameterValue(TEXT("Fade"), 0.0f);
		}
		const TArray<FName> Slots = Body->GetMaterialSlotNames();
		int32 Blade = INDEX_NONE;
		for (int32 Slot = 0; Slot < Body->GetNumMaterials(); ++Slot)
		{
			const UMaterialInterface* Own = Body->GetMaterial(Slot);
			const bool bBlade = (Slots.IsValidIndex(Slot) && Slots[Slot].ToString().Contains(TEXT("Sword"))) ||
				(Own && Own->GetName().Contains(TEXT("Sword")));
			if (bBlade)
			{
				Blade = Slot;
				if (Look == 5)
				{
					Sword->SetMaterial(Slot, CloneIceMaterial.LoadSynchronous());
				}
				continue;
			}
			Sword->SetMaterial(Slot, Hidden);
		}
		// 칼 칸 재질에 칼 말고 다른 부품도 들어 있다(첫 촬영 — 검마다 아래쪽에 작은 조각이 따라 보임) → 칼을 쥔 뼈까지 가는 줄기에서
		// 갈라져 나간 가지(다리·왼팔·머리·옷자락)는 뿌리째 숨긴다(칼 쪽 가지는 남김)
		const FName Grip = Body->GetSocketBoneName(TEXT("Sword_Base"));
		TSet<FName> Chain;
		for (FName Bone = Grip; Bone != NAME_None; Bone = Body->GetParentBone(Bone))
		{
			Chain.Add(Bone);
		}
		int32 HiddenBranches = 0;
		for (int32 BoneIndex = 0; BoneIndex < Sword->GetNumBones(); ++BoneIndex)
		{
			const FName Bone = Sword->GetBoneName(BoneIndex);
			const FName Parent = Sword->GetParentBone(Bone);
			if (!Chain.Contains(Bone) && Chain.Contains(Parent) && Parent != Grip)
			{
				Sword->HideBoneByName(Bone, PBO_None);
				++HiddenBranches;
			}
		}
		const FVector Base = Body->GetSocketTransform(TEXT("Sword_Base"), RTS_Component).GetLocation();
		const FVector Tip = Body->GetSocketTransform(TEXT("Sword_Tip"), RTS_Component).GetLocation();
		const FQuat Along = FRotationMatrix::MakeFromZ((Tip - Base).GetSafeNormal()).ToQuat();
		const FQuat Undo = Along.Inverse();
		Sword->SetRelativeTransform(FTransform(Undo, -Undo.RotateVector((Base + Tip) * 0.5f * SwordScale), FVector(SwordScale)));
		Chunk.Sword = Sword;
		SpawnBurstLater(TSoftObjectPtr<UParticleSystem>(FSoftObjectPath(SwordSpawnPath)).LoadSynchronous(), Spot, SwordSpawnFlash, Appear);
		if (Index == 0)
		{
			UE_LOG(LogTemp, Display, TEXT("AURORA_FSWORD look=%d blade=%d slots=%d length=%.1f grip=%s chain=%d hidden=%d"), Look, Blade,
				Body->GetNumMaterials(), FVector::Dist(Base, Tip), *Grip.ToString(), Chain.Num(), HiddenBranches);
		}
	}
	if (!GetWorld()->GetTimerManager().IsTimerActive(ChunkMeshTimer))
	{
		GetWorld()->GetTimerManager().SetTimer(ChunkMeshTimer, this, &UAuroraSkillComponent::ChunkMeshTick, ChunkMeshTickSeconds, true);
	}
	if (Index == 0)
	{
		UE_LOG(LogTemp, Display, TEXT("AURORA_CHUNKMESH look=%d mesh=%s extent=%s scale=%.3f"), Look, *Shape->GetName(),
			*Extent.ToCompactString(), Chunk.Scale);
	}
}

void UAuroraSkillComponent::FireChunkMesh(int32 Index, const FVector& Goal, float Flight)
{
	if (!ChunkMeshes.IsValidIndex(Index) || !GetWorld())
	{
		return;
	}
	FAuroraChunkMesh& Chunk = ChunkMeshes[Index];
	UStaticMeshComponent* Mesh = Chunk.Mesh.Get();
	if (!IsValid(Mesh))
	{
		return;
	}
	Chunk.FiredAt = GetWorld()->GetTimeSeconds();
	Chunk.Flight = FMath::Max(Flight, 0.02f);
	Chunk.From = Mesh->GetComponentLocation();
	Chunk.Goal = Goal;
	const int32 Look = GetFChunk();
	// 1 바위: Rampage 얼음 바위 던지기 터짐 + 나는 바위 꼬리 · 2 창 · 3 송곳: 오로라 도약 꼬리
	if (Look == 1)
	{
		SpawnBurstLater(RockThrowFx, Chunk.From, ChunkThrowScale, 0.0f, (Goal - Chunk.From).Rotation());
	}
	else if (Look >= 3)
	{
		// 3 얼음송곳 · 4·5 검: 떠나는 자리에 작은 번쩍(R 순간이동과 같은 것)
		SpawnBurstLater(LanceFlash, Chunk.From, IcicleLaunchFlash, 0.0f, (Goal - Chunk.From).Rotation());
	}
	// 90차 첫 촬영: 바위 꼬리(Rock_Flying)는 옅은 회색 먼지뿐 · 도약 꼬리(Leap_Trail) 1.0은 두꺼운 흰 연기 줄 → 1은 먼지 + 가는 서리 꼬리,
	// 2·3은 서리 꼬리만 가늘게
	UParticleSystem* const Trails[2] = {Look == 1 ? RockFlyingFx.Get() : nullptr, LeapTrail.Get()};
	const float TrailScales[2] = {ChunkTrailScale, Look == 1 ? ChunkFrostTrailThin : Look >= 4 ? SwordTrail : ChunkFrostTrailSpear};
	for (int32 Kind = 0; Kind < 2; ++Kind)
	{
		if (!Trails[Kind])
		{
			continue;
		}
		UParticleSystemComponent* Trail = UGameplayStatics::SpawnEmitterAttached(Trails[Kind], Mesh, NAME_None, FVector::ZeroVector,
			FRotator::ZeroRotator, FVector(TrailScales[Kind]), EAttachLocation::KeepRelativeOffset, false);
		if (Trail)
		{
			// 메시 배율을 물려받지 않게(메시에 붙인 입자는 메시 배율을 따른다 — 70차 함정)
			Trail->SetUsingAbsoluteScale(true);
			Trail->SetWorldScale3D(FVector(TrailScales[Kind]));
			OwnedEffects.Add(Trail);
			// 닿을 때 정리할 꼬리는 마지막 것 하나만 들고, 먼지 꼬리는 날아가는 시간 뒤에 놓는다
			if (Kind == 0)
			{
				ReleaseLater(Trail, Chunk.Flight);
			}
			else
			{
				Chunk.Trail = Trail;
			}
		}
	}
}

void UAuroraSkillComponent::ChunkMeshTick()
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	const double Now = World->GetTimeSeconds();
	const int32 Look = GetFChunk();
	bool bAny = false;
	for (FAuroraChunkMesh& Chunk : ChunkMeshes)
	{
		UStaticMeshComponent* Mesh = Chunk.Mesh.Get();
		if (!IsValid(Mesh))
		{
			continue;
		}
		const float Age = static_cast<float>(Now - Chunk.Born);
		if (Chunk.FiredAt < 0.0)
		{
			if (Now > Chunk.Deadline)
			{
				// 쏘지 못하고 끊겼다(시전 취소) — 조용히 치운다
				if (USceneComponent* Sword = Chunk.Sword.Get())
				{
					Sword->DestroyComponent();
				}
				RemoveTimedMesh(Mesh, nullptr);
				Chunk.Mesh.Reset();
				continue;
			}
			bAny = true;
			const float Grow = Age <= 0.0f ? 0.001f : FMath::InterpEaseOut(0.15f, 1.0f, FMath::Min(Age / ChunkMeshForm, 1.0f), 2.0f);
			const FVector Bob(0.0f, 0.0f, ChunkMeshBob * FMath::Sin(Chunk.Phase + Age * 2.0f * PI * ChunkMeshBobRate));
			Mesh->SetWorldLocation(Chunk.Spot + Bob);
			const FQuat Spin(Chunk.SpinAxis, FMath::DegreesToRadians(ChunkIdleSpin * FMath::Max(Age, 0.0f)) + Chunk.Phase);
			if (Look == 4 || Look == 5)
			{
				// 검은 끝이 위로 서서 아주 천천히 돈다(나르는 몸은 숨김 · 검 사본은 붙어 같이 커진다)
				Mesh->SetWorldRotation(FQuat(FVector::UpVector, Chunk.Phase + FMath::DegreesToRadians(30.0f * FMath::Max(Age, 0.0f))));
				Mesh->SetWorldScale3D(FVector(Grow));
			}
			else if (Look == 3)
			{
				// 송곳은 끝이 위로 서서 제 축으로 천천히 돈다 — 쏘는 순간 나는 쪽으로 돌린다
				Mesh->SetWorldRotation(FQuat(FVector::UpVector, Chunk.Phase + FMath::DegreesToRadians(IcicleIdleTwist * FMath::Max(Age, 0.0f))));
				Mesh->SetWorldScale3D(IcicleScale(Mesh->GetStaticMesh()) * Grow);
			}
			else if (Look == 2)
			{
				// 창은 떠 있을 때도 끝이 위로 — 쏘는 순간 나는 쪽으로 돌린다
				Mesh->SetWorldRotation(FRotator(90.0f, 0.0f, 0.0f).Quaternion() * FQuat(FVector::XAxisVector, Chunk.Phase));
				Mesh->SetWorldScale3D(FVector(ChunkSpearStretch, 1.0f, 1.0f) * Chunk.Scale * Grow);
			}
			else
			{
				Mesh->SetWorldRotation(Spin);
				Mesh->SetWorldScale3D(FVector(Chunk.Scale * Grow));
			}
			continue;
		}
		const float Alpha = static_cast<float>((Now - Chunk.FiredAt) / Chunk.Flight);
		if (Alpha >= 1.0f)
		{
			// 닿았다 — 메시는 사라지고 꼬리는 남은 입자만 마저 흘러가게(맞은 자리 터짐은 ExecuteChunkVolley가 같은 때 띄운다)
			ReleaseOwnedEffect(Chunk.Trail.Get());
			Chunk.Trail.Reset();
			if (USceneComponent* Sword = Chunk.Sword.Get())
			{
				Sword->DestroyComponent();
			}
			RemoveTimedMesh(Mesh, nullptr);
			Chunk.Mesh.Reset();
			continue;
		}
		bAny = true;
		const FVector Axis = (Chunk.Goal - Chunk.From).GetSafeNormal();
		Mesh->SetWorldLocation(FMath::Lerp(Chunk.From, Chunk.Goal, Alpha));
		if (Look == 4 || Look == 5)
		{
			// 칼끝(+Z)이 나는 쪽을 본다
			Mesh->SetWorldRotation(FRotationMatrix::MakeFromZ(Axis).ToQuat());
			Mesh->SetWorldScale3D(FVector::OneVector);
		}
		else if (Look == 3)
		{
			// 끝(+Z)이 나는 쪽을 보고 송곳처럼 제 축으로 빠르게 돈다
			const float Seconds = static_cast<float>(Now - Chunk.FiredAt);
			Mesh->SetWorldRotation(FRotationMatrix::MakeFromZ(Axis).ToQuat() *
				FQuat(FVector::UpVector, Chunk.Phase + FMath::DegreesToRadians(IcicleDrillTwist * Seconds)));
			Mesh->SetWorldScale3D(IcicleScale(Mesh->GetStaticMesh()));
		}
		else if (Look == 2)
		{
			Mesh->SetWorldRotation(Axis.Rotation());
			Mesh->SetWorldScale3D(FVector(ChunkSpearStretch, 1.0f, 1.0f) * Chunk.Scale);
		}
		else
		{
			const float Seconds = static_cast<float>(Now - Chunk.FiredAt);
			Mesh->SetWorldRotation(FQuat(Chunk.SpinAxis, FMath::DegreesToRadians(ChunkFlightSpin * Seconds) + Chunk.Phase));
		}
	}
	if (!bAny)
	{
		ChunkMeshes.Reset();
		World->GetTimerManager().ClearTimer(ChunkMeshTimer);
	}
}

void UAuroraSkillComponent::ClearChunkMeshes()
{
	for (FAuroraChunkMesh& Chunk : ChunkMeshes)
	{
		ReleaseOwnedEffect(Chunk.Trail.Get());
		if (USceneComponent* Sword = Chunk.Sword.Get())
		{
			Sword->DestroyComponent();
		}
		RemoveTimedMesh(Chunk.Mesh.Get(), nullptr);
	}
	ChunkMeshes.Reset();
	if (GetWorld())
	{
		GetWorld()->GetTimerManager().ClearTimer(ChunkMeshTimer);
	}
}
