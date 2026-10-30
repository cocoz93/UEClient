#include "AuroraSkillComponent.h"

#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "AuroraCharacter.h"
#include "Components/CapsuleComponent.h"
#include "Components/DecalComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/Texture.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/OverlapResult.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/RootMotionSource.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "KwangTrainingDummy.h"
#include "Materials/Material.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "NavigationSystem.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "TimerManager.h"
#include "TopDownCombatCharacter.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	TAutoConsoleVariable<int32> CVarAuroraIgnoreCooldowns(
		TEXT("Aurora.Skills.IgnoreCooldowns"), 1,
		TEXT("Testing: 1 (default) lets Aurora skills ignore cooldowns. Set 0 to restore cooldowns."));

	// 시안 고르기용(2026-10-18). 사용자 선택 = W 1(얼음 파편) · R 3(합본) · 평타 눈송이 끔. 다른 번호는 비교용으로 남긴다.
	TAutoConsoleVariable<int32> CVarAuroraChargeTrail(
		TEXT("Aurora.FX.WTrail"), 1,
		TEXT("Glacial Charge path: 0 icicle walls, 1 ice shards burst, 2 frost puffs, 3 no path (body frost + arrival shock)."));
	TAutoConsoleVariable<int32> CVarAuroraCryoStyle(
		TEXT("Aurora.FX.RStyle"), 3,
		TEXT("Cryoseism: 0 original, 1 ice waves spreading, 2 charge glow while leaping + shards when the ice breaks, 3 both."));

	// 기본 2(2026-10-18 사용자 「임팩트 있고 절도 있게」 승인): 칼을 내지른 원작 돌진 자세로 빠르게 가서 미끄러지지 않고 멈춘다.
	TAutoConsoleVariable<int32> CVarAuroraChargeRun(
		TEXT("Aurora.FX.WRun"), 2,
		TEXT("Glacial Charge body: 0 original jog + slide stop, 1 same jog played fast + slide stop, 2 original charge lunge (Ability_Q, sword forward) + hard stop."));
	TAutoConsoleVariable<int32> CVarAuroraChargeFront(
		TEXT("Aurora.FX.WFront"), 4,
		TEXT("Glacial Charge front ice: 0 one flare attached to the body, 1 flare re-fired every 0.09s, 2 ice shards kicked ahead, 3 both, 4 none (spiky flare removed, 2026-10-18 request)."));
	// 진단용: 화면 위쪽 구름의 출처를 가리려고 R 착지 이펙트를 골라 끈다(비트 합). 1 InitialBlast · 2 결정 물결 ·
	// 64 얼은 대상에 붙이는 Frozen · 128 시전 이펙트. 하늘 눈구름은 언 바닥(Frozen_Ground_Water_Ultimate)으로 밝혀져 언 바닥째 뺐다.
	TAutoConsoleVariable<int32> CVarAuroraCryoSkip(
		TEXT("Aurora.FX.RSkip"), 0,
		TEXT("Diagnosis: bitmask of Cryoseism effects to skip (1 blast, 2 waves, 64 frozen on targets, 128 cast effects)."));
	TAutoConsoleVariable<int32> CVarAuroraSlashGround(
		TEXT("Aurora.FX.QGround"), 3,
		TEXT("Frost Slash floor along the arc: 0 small ice crystals, 1 white+ice frost marks (decal), 2 ice cracks (decal), 3 white snow cover (decal)."));
	// 기본 6(10-19 오후 「R 애니 어색, 다르게 조합」 → 시안 4~6 중 추천 6 「추천대로 가자」): 원본 동작 하나를 끊지 않고 틀어 두 동작
	// 사이의 툭 끊김이 없다. 그 전 기본 3(가리킨 뒤 무릎·칼 꽂기)은 A와 같은 동작이었다.
	// 같은 날 저녁 「지속시간 늘리고, 손 뻗은 애니메이션 반복하고 이펙트 계속 터지는 거」 → 7이 기본. 버티기가 4초로 늘어 6은 끝 무렵
	// 동작이 먼저 끝난다(6은 2초 버티기 기준).
	// 밤 「R 애니 어색하다 — 다른 거 없나, 아니면 자연스럽게」: 8 = 7을 몸이 튀지 않게 고친 것 · 9 = 다른 동작(칼로 얼음 깎기).
	// → 「R9으로, 칼 휘두를 때마다 캐릭터 쪽에 이펙트가 있고 휘두를 때 해당 지점이 터지는 방식」으로 9가 기본.
	TAutoConsoleVariable<int32> CVarAuroraFieldChannel(
		TEXT("Aurora.FX.RChannel"), 9,
		TEXT("Frost Field channel pose: 0 sword raised straight up (Ability_R_Targeting), 1 sword aimed forward (Ability_Q_Targeting), 2 pointing swing (Cast) twice, 3 kneel with the sword planted (Recall channel), 4 point then reach the free hand out (Emote_Slice), 5 point then slash and reach out, 6 raise, slash and reach out in one motion from the cast, 7 = 6 then thrust the hand out again and again with a big burst each time, 8 = 6 then the reached hand eases back and pushes out again without the body jumping, 9 carve ice with the sword (Emote_Ice_Sculpture): each fast stroke sweeps a sword wave and frost off Aurora towards the field and bursts the aimed spot (default)."));
	// 10-19 시안(사용자 「Q·E 이펙트 시안 여러 개」 · 「F 쏠 때 캐릭터 쪽에 이펙트」). Q는 「1번 초승달 검기만」으로 1이 기본.
	// 10-19 밤 「QER 다 아쉽다」 → 큰 틀 Q1·Q2를 「둘 다 스킬로」 + 「Q 두 번 누르기 — 예」로 5(QBoost·QHit·QGround는 1~3용).
	// 이어서 「Q는 차라리 얼음 검기를 날리는 거, 두세 번 정도, 이펙트 신경 좀. 지금 건 너무 별로」 → 6이 기본.
	TAutoConsoleVariable<int32> CVarAuroraSlashStyle(
		TEXT("Aurora.FX.QStyle"), 6,
		TEXT("Frost Slash look: 0 ice shards + floor marks (QGround), 1 crescent sword wave sweeping across the floor, 2 two rows of ice crystals bursting up along the fan, 3 frost wind sweeping the fan + ice chunks, 4 unused, 5 a crescent wave leaving the blade and flying forward (Q1) + pressing Q again within 1.5s after it cuts an X twice in the air (Q2), 6 three slashes each flinging an ice crescent wave (ice shards along its edge, ice bits falling off it, default)."));
	// R 장판에서 칼질마다 일어나는 일(10-19 밤 큰 틀 「R은 나 — 얼음 파편 회오리」): 0 가운데가 터짐(R9까지) · 1 얼음 파편 회오리.
	TAutoConsoleVariable<int32> CVarAuroraFieldVortex(
		TEXT("Aurora.FX.RField"), 1,
		TEXT("Frost Field: 0 the aimed spot bursts on each stroke (R9), 1 an ice shard whirlwind over the field that spins faster and wider on each stroke, pulls enemies in and slams down at the end (default)."));
	// 맞은 자리는 「3으로」(10-19).
	TAutoConsoleVariable<int32> CVarAuroraSlashHit(
		TEXT("Aurora.FX.QHit"), 3,
		TEXT("Frost Slash hit on each enemy: 0 ice shards (Aurora melee impact), 1 white flash along the slash, 2 snow burst, 3 frost sparkles sprayed along the slash (default)."));
	// Q 보강: 잔상·서리 바람·반짝임 시안은 「다 별로」로 빼고 「흩날리는 이펙트」(눈송이)만 남겼다(10-19).
	// 같은 날 오후 「이상하다, 테두리 더 얇게 + 흩날리는 류로」: 1은 눈송이가 게임 화면에서 점으로만 보여 2(눈가루 + 큰 눈송이)를 기본으로.
	// 같이 찍은 3(2 + 날 따라 냉기 안개 Rampage Ice_Enrage_End)은 점박이 공·청록 덩어리가 떠 보여 뺐다(aurora-35th-drafts).
	// 저녁 「너무 공주 같은 느낌, 여전사 같은 느낌이 났으면」: 3·4는 떠다니는 눈송이 대신 무겁게 튀는 얼음 파편(3은 칼이 바닥을 벤 자국까지)
	// → 「Q, S 그렇게 가 보자」로 3이 기본.
	TAutoConsoleVariable<int32> CVarAuroraSlashBoost(
		TEXT("Aurora.FX.QBoost"), 3,
		TEXT("Frost Slash crescent extra: 0 none, 1 small snowflakes fluttering off the blade, 2 fine snow dust streaming off the blade + bigger flakes, 3 heavy ice shards flung off the blade + a cut scar on the floor (default), 4 ice shards only."));
	// S는 「3(2 + 반짝임)에 좀 더 투명하게」(10-19). 저녁 「Q랑 마찬가지로 여전사 같은 장판기」 → 4 = 갈라지는 얼음 균열 장판,
	// 이어서 「그래도 눈 모양 유지하면서 거친 느낌」 → 5 = 눈송이 짜임을 균열 선으로.
	// 밤 「S는 그냥 롤백하고, 기존 원에 깨진 듯한 이펙트 추가하는 거 가능한?」 → 기본 3으로 되돌리고, 3의 고리가 깨진 시안 6·7(고르기 대기).
	// 10-20 「펑펑 얼음 터지는 이펙트는 없애 줘」 → 기본 2(3에서 장판 안에 0.4초마다 솟던 얼음 분출 P_Aurora_Sculpture_Thrust만 뺀 것).
	// 이어서 「왜 이렇게 아쉽지」 분석(문양이 원판 전체의 뿌연 막에 묻힘) → 기본 1(안에 서리를 깔지 않음).
	TAutoConsoleVariable<int32> CVarAuroraHasteStyle(
		TEXT("Aurora.FX.SStyle"), 1,
		TEXT("Frost Haste floor: 0 clean lines, 1 lines worn by frost (default), 2 worn lines + frosted ground inside, 3 = 2 + frost sparkles rising inside, 4 thick ice cracks splitting out from the feet inside a broken ice rim + ice chunks bursting, 5 = 4 with the cracks laid out as a snowflake, 6 = 3 with thin glowing cracks breaking its rings from the front round both sides, 7 = 3 with thick dark cracks breaking its rings + ice chips bursting along them."));
	// D·F 시안(10-19 밤). 「D 2·3 괜찮다, 이 중에 하나로」 → 3 · 「F 1·2·3 차이를 모르겠다, 적당히 골라서」 → 2(1의 바닥 줄은 레이저 선처럼 보였다).
	TAutoConsoleVariable<int32> CVarAuroraSpikeStyle(
		TEXT("Aurora.FX.DStyle"), 3,
		TEXT("Ice Rupture extra: 0 ice rocks only, 1 ice spikes punching up out of the floor at each rock and sinking back, 2 the floor cracked along the line, 3 both (default)."));
	TAutoConsoleVariable<int32> CVarAuroraLanceStyle(
		TEXT("Aurora.FX.FStyle"), 2,
		TEXT("Ice Lance extra: 0 none, 1 a white frost streak on the floor under each blade as it flies, 2 the floor cracked in a star where a blade strikes + ice shards flung on (default), 3 both."));
	// 10-20 시안(「S 다 아쉬운데 뭐가 문제지 · Q 검기 날리는 거 시안 · V 바닥에 오브젝트 깔리는 거 말고」). 고르기 전까지 0(지금 그대로).
	// S는 밤에 「라」(돎 + 번쩍·맥동 + 빛·색)로 정해 빛 60이 기본.
	TAutoConsoleVariable<float> CVarAuroraHasteLight(
		TEXT("Aurora.FX.SLight"), 60.0f,
		TEXT("Frost Haste: a blue point light over the floor, in candelas (60 default, 0 = none)."));
	TAutoConsoleVariable<int32> CVarAuroraSlashWave(
		TEXT("Aurora.FX.QWave"), 0,
		TEXT("Ice wave draft bitmask: 1 the Yin wind ribbon mesh rides with each wave, 2 the Yin whip afterimage trails its tip + Yin wind wings at the sword, 4 two fainter crescents follow behind (layered wave). 0 = none (default)."));
	// 10-20 밤 「V는 8 + 얼음 터질 때 한 번 더(VNova 8) 빼고 다」로 8이 기본(얼음 결정 물결은 안 깔림).
	TAutoConsoleVariable<int32> CVarAuroraCryoLand(
		TEXT("Aurora.FX.VLand"), 8,
		TEXT("Cryoseism landing draft: 0 ice crystal waves, 1 radial floor cracks, 2 snowflake-shaped cracks, 3 ice spears falling onto the frozen and around, 4 the floor frosting over, 5 two glowing frost shockwave rings sweeping out + a blue flash, 6 glowing ice shards flung out all round, 7 = 5 + 6, 8 = 7 + a brief hit stop on landing (default)."));
	// 10-20 밤 시안(「Q 다 아쉽다, 시안 가자 · V 지금 나오는 오브젝트들을 빽빽하게, 추가 시안 더」) → 「Q는 23」으로 23이 기본.
	TAutoConsoleVariable<int32> CVarAuroraSlashBlade(
		TEXT("Aurora.FX.QBlade"), 23,
		TEXT("Ice wave draft bitmask: 1 a thick glowing crescent body instead of the dark blue one, 2 the ice cones along the edge glow instead of grey stone, 4 a blue light follows each wave, 8 no ice cones, 16 a bigger, thicker, faster wave flying further (700) with a torn brush-stroke body, 32 four afterimages streaming behind it, 64 more and bigger glowing ice bits flung off it. 23 = 1 + 2 + 4 + 16 (default), 0 = none."));
	// 이어서 「Q 23 기반으로 여러 시안 · V 8 기반으로 여러 시안 · S 거친 느낌이 없다」(헤더 QContrastIce · CryoNovaFastSeconds · HasteRoughGrit 설명).
	// Q는 23 그대로(QBig 0), V는 8 빼고 다(VNova 7).
	TAutoConsoleVariable<int32> CVarAuroraSlashBig(
		TEXT("Aurora.FX.QBig"), 0,
		TEXT("Big ice wave draft bitmask (with QBlade 16): 1 torn rougher, 2 white edge + deep blue body, 4 shatters into glowing shards where it ends, 8 the third wave 1.35x wider with a hit stop. 0 = none (default)."));
	// 10-21 「사선으로 가는 건 확실히 사선으로」(헤더 QWaveRoll 설명): 화면에서 기운 각(도). 0이면 그 전처럼 나는 쪽 축으로 QWaveRoll만.
	TAutoConsoleVariable<float> CVarAuroraSlashTilt(
		TEXT("Aurora.FX.QTilt"), 40.0f,
		TEXT("Ice wave tilt on screen in degrees, turned round the camera's view so '/' and '\\' read clearly whichever way she aims (40 default). 0 = the old slight roll round the flight line."));
	// 10-21 「Q는 미치겠네 — 그냥 올곧게 일직선으로(바닥이랑 마주보게) 만들어서 두 개만 쏘는 건 어때」(헤더 QFlatVolley 설명).
	// 0이면 그 전 셋(기울임 QTilt).
	TAutoConsoleVariable<int32> CVarAuroraSlashFlat(
		TEXT("Aurora.FX.QFlat"), 1,
		TEXT("Ice wave volley: 1 two waves lying flat, face to the floor, no tilt (default), 0 the three slanted waves before."));
	// 10-21 「시안 중에선 지금 Q가 제일 낫다 — 다른 시안 줄 수 있어?」(헤더 QFeelUnfoldSeconds 설명) — 고르기 전까지 0.
	TAutoConsoleVariable<int32> CVarAuroraSlashFeel(
		TEXT("Aurora.FX.QFeel"), 0,
		TEXT("Big ice wave draft bitmask (with QBlade 16, on top of the current look): 1 it unfolds from the sword with a flash where it leaves, 4 its torn strokes animate - forming, rippling, then tearing apart. 0 = none (default)."));
	TAutoConsoleVariable<int32> CVarAuroraCryoNova(
		TEXT("Aurora.FX.VNova"), 7,
		TEXT("Cryoseism shockwave draft bitmask (with VLand 5-8): 1 rougher torn rings, 2 three faster rings, 4 bigger shards flung higher, 8 a second small shockwave + shards at each frozen target when the ice bursts. 7 = 1 + 2 + 4 (default), 0 = none."));
	// S는 「2가 그나마 낫다, 시안 더」로 2 바탕 시안을 더함(헤더 HasteFineGrit 설명) → 「니 권장대로」 10(2 + 딱 끊김)이 기본.
	// 10-25 「흐리멍덩하게 말고 좀 또렷하게」 → 0(선을 큰 조각으로 갉아 지워 군데군데 빈 선이 흐릿해 보였다. 그림의 흔들림·끊김은 남음).
	TAutoConsoleVariable<int32> CVarAuroraHasteRough(
		TEXT("Aurora.FX.SRough"), 0,
		TEXT("Frost Haste rough draft bitmask: 1 the circle picture shaken, frayed and broken much harder, 2 frost gnawing the lines in big patches, 4 a second, fine frost grain gnawing the lines too, 8 the gnawed edges cut hard instead of fading, 16 bigger gnawed-out chunks (with 2). 4 and 8 use the rough floor material. 10 = 2 + 8, 0 = none (default)."));
	// 10-25 「S도 이펙트가 아쉬운데 — 그냥 내부 큰 눈 문양을 없애는 방식은 어때」로 0이 기본(SRough 1의 거친 그림보다 먼저 본다).
	TAutoConsoleVariable<int32> CVarAuroraHasteInner(
		TEXT("Aurora.FX.SInner"), 0,
		TEXT("Frost Haste circle: 0 rings, hexagon and border crystals only - no big snowflake inside (default), 1 the big snowflake in the middle as before."));
	TAutoConsoleVariable<int32> CVarAuroraCryoDense(
		TEXT("Aurora.FX.VDense"), 0,
		TEXT("Cryoseism crystals draft: 0 three rings, 33 crystals (default), 1 five rings, 98 crystals touching, 2 = 1 scattered in place, size and heading, 3 = 1 + small crystals between the rings, 4 four rings, 54 crystals + the floor frosting over between them."));
	// 10-21 「F는 얼음덩어리 씌우지 말고 분신 세 개를 돌격시키는 게 좋을 것 같아」(헤더 LanceClonePoseFrom 설명)로 1이 기본.
	TAutoConsoleVariable<int32> CVarAuroraLanceClone(
		TEXT("Aurora.FX.FClone"), 1,
		TEXT("Ice Lance: 0 three thrown ice blades, 1 three ice clones charging out along the same paths instead (default)."));
	// F 나는 꼬리 시안(10-20 「날아갈 때가 밋밋한 것 같은데 — 시안 줘 봐」) → 「부스러기 + 잔상으로」 3.
	TAutoConsoleVariable<int32> CVarAuroraLanceFlight(
		TEXT("Aurora.FX.FFlight"), 3,
		TEXT("Ice Lance flight trail: 0 the leap trail only, 1 + ice crumbs dropping off behind each blade, 2 + afterimages of the blade thinning away behind it, 3 = 1 + 2 (default)."));
	// E는 「휘두르는 이펙트 자체가 아쉽다」로 회오리(0)를 대신할 휘두름 시안 셋. 묶기·깨짐은 시안과 상관없이 같다.
	// 10-19 밤 「QER 다 아쉽다」 → 큰 틀 고르기에서 E1(회전 베기 + 얼음 가둠) = 4. 4만 묶인 대상을 얼음 석상으로 바꾼다.
	// 이어서 「E는 그냥 롤백해 줘」 → 0(회오리 + 바닥 원형 검기 ERing)으로 되돌렸다. 4는 비교용으로 남긴다.
	TAutoConsoleVariable<int32> CVarAuroraFreezeStyle(
		TEXT("Aurora.FX.EStyle"), 0,
		TEXT("Hoarfrost swing: 0 blue whirlwind (pack, default), 1 full-circle sword wave spinning round, 2 frost spiral spinning out, 3 cyan cold swirl (Rampage ice cast glow), 4 sword trail following the spinning blade + rooted targets turned to ice with an ice lump at their feet that shatters."));
	// 10-21 「E는 얼음 오브젝트가 생기고 나서 한 5~10초 정도 유지 — 몬스터가 못 오게 만드는 느낌」(헤더 HoarfrostWallStep 설명): 둘레 결정이
	// 서 있는 시간(초). 묶기(1.5초)와 따로 — 보이기만 하고 길은 안 막는다.
	TAutoConsoleVariable<float> CVarAuroraFreezeWall(
		TEXT("Aurora.FX.EWallSeconds"), 8.0f,
		TEXT("Seconds the Hoarfrost ring of ice crystals stands before it crumbles (8 default; it only looks like a wall - enemies still walk through)."));
	// 「지금 기본값(회오리) 유지에 바닥에 원형 검기 추가」(10-19): 휘두름 시안과 따로 원형 검기를 같이 깐다(시안 1은 이미 원형 검기라 겹치지 않음).
	// E 4의 칼 궤적 고르기(10-19 밤): 손 소켓(FX_Trail_R, 40cm) 사이로는 어느 궤적이든 짧고 흐려 거의 안 보였다(aurora-40th-e1).
	// 칼날 밑동~끝(89cm) 사이로 그리면 Aurora 평타 궤적이 넓은 흰 칼바람이 된다 → 0 + 칼날(aurora-40th-trail). Rampage 분노(2)는
	// 더 밝지만 가는 파란 선이 여러 겹 남아 마법처럼 보였고, Kwang(3)은 갈색 판이었다.
	TAutoConsoleVariable<int32> CVarAuroraSwordTrail(
		TEXT("Aurora.FX.ETrail"), 0,
		TEXT("Hoarfrost 4 sword trail: 0 Aurora primary trail, 1 Rampage ice melee trail, 2 Rampage ice melee trail (enraged), 3 Kwang primary trail."));
	TAutoConsoleVariable<int32> CVarAuroraSwordTrailSockets(
		TEXT("Aurora.FX.ETrailSockets"), 1,
		TEXT("Hoarfrost 4 sword trail drawn between: 0 FX_Trail_R_01 and FX_Trail_R_02 (hand, 40cm), 1 Sword_Base and Sword_Tip (blade, default)."));
	TAutoConsoleVariable<int32> CVarAuroraFreezeRing(
		TEXT("Aurora.FX.ERing"), 1,
		TEXT("Hoarfrost: 1 also lays the full-circle sword wave on the floor under the swing (default), 0 swing effect only."));
	TAutoConsoleVariable<int32> CVarAuroraLanceHand(
		TEXT("Aurora.FX.FHand"), 1,
		TEXT("Ice Lance throw effect in front of Aurora: 0 none, 1 blue flash, 2 ice fragments, 3 cyan frost smoke."));
	TAutoConsoleVariable<int32> CVarAuroraMeleeSnow(
		TEXT("Aurora.FX.MeleeSnow"), 0,
		TEXT("Basic attack: 1 spawns the snowflake puff in front of Aurora on every swing, 0 hides it."));

	const TCHAR* const AnimationRoot = TEXT("/Game/ParagonAurora/Characters/Heroes/Aurora/Animations/");
	const TCHAR* const RampageIceRoot = TEXT("/Game/ParagonRampage/FX/Particles/Rampage_v001_IceBlue/FX/");
	const TCHAR* const EffectRoot = TEXT("/Game/ParagonAurora/FX/Particles/Abilities/");

	UParticleSystem* LoadEffect(const TCHAR* Folder, const TCHAR* Name)
	{
		const FString Path = FString::Printf(TEXT("%s%s/FX/%s.%s"), EffectRoot, Folder, Name, Name);
		ConstructorHelpers::FObjectFinder<UParticleSystem> Finder(*Path);
		return Finder.Object;
	}

	// 같은 Paragon의 Rampage 얼음판(파란 얼음) 이펙트. Aurora 팩만으로는 큰 폭발·파편이 모자라 빌려 쓴다.
	UParticleSystem* LoadRampageIce(const TCHAR* Name)
	{
		const FString Path = FString::Printf(TEXT("%s%s.%s"), RampageIceRoot, Name, Name);
		ConstructorHelpers::FObjectFinder<UParticleSystem> Finder(*Path);
		return Finder.Object;
	}

	UAnimSequence* LoadAnimation(const TCHAR* Name)
	{
		const FString Path = FString::Printf(TEXT("%s%s.%s"), AnimationRoot, Name, Name);
		ConstructorHelpers::FObjectFinder<UAnimSequence> Finder(*Path);
		return Finder.Object;
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

UAuroraSkillComponent::UAuroraSkillComponent()
{
	PrimaryComponentTick.bCanEverTick = false;

	const auto Define = [this](EAuroraSkill Skill, const TCHAR* Name, const TCHAR* Animation, UParticleSystem* Cast,
		float Damage, float Cooldown, float Range, float ActionTime, float RecoveryTime)
	{
		FAuroraSkillDefinition& Definition = Skills.Add(Skill);
		Definition.Name = Name;
		Definition.Animation = LoadAnimation(Animation);
		Definition.CastEffect = Cast;
		Definition.Damage = Damage;
		Definition.Cooldown = Cooldown;
		Definition.Range = Range;
		Definition.ActionTime = ActionTime;
		Definition.RecoveryTime = RecoveryTime;
	};
	// 시점은 원본 동작의 골반 높이 기준(aurora-assets 덤프), 피해·쿨타임·사거리는 카운테스·스패로우·Gideon 규모 임시값이다.
	// Frozen Simulacrum의 Damage는 남겨 둔 얼음 분신이 부서질 때의 피해다(원작은 미끼, 폭발 피해는 이 프로젝트의 임시 규칙).
	// 회복 0.6초 = 착지(0.65초) 직후 바로 움직인다. 원본 동작의 일어서는 구간(0.73~1.45초)은 건너뛴다(2026-10-18 후딜 단축).
	// 사거리(대상까지) 700 → 1500(10-25 「W 사거리를 2배 이상으로」). 날아가는 시간(0.5초)은 그대로라 멀수록 빠르게 날아간다.
	Define(EAuroraSkill::FrozenSimulacrum, TEXT("Frozen Simulacrum"), TEXT("Ability_RMB_Fwd"), nullptr,
		30.0f, 10.0f, 1500.0f, 0.15f, 0.6f);
	// Glacial Charge의 회복 시간은 돌진 거리로 정해진다(돌진 시간 + 멈춰 있는 시간 GetChargeStopSeconds).
	// 사거리 900 → 450(사용자 「이동거리 절반」 2026-10-18). 출발은 시전 0.10초 → ChargeWindupSeconds(10-20 「너무 즉발」).
	Define(EAuroraSkill::GlacialCharge, TEXT("Glacial Charge"), TEXT("Jog_Fwd_Ability_Q"), LoadEffect(TEXT("Dash"), TEXT("P_Aurora_Dash_WarmUp")),
		20.0f, 9.0f, 450.0f, ChargeWindupSeconds, 0.0f);
	// Hoarfrost의 Range는 사거리가 아니라 제자리 빙결 반경이다.
	Define(EAuroraSkill::Hoarfrost, TEXT("Hoarfrost"), TEXT("Ability_E_V2"), LoadEffect(TEXT("Freeze"), TEXT("P_Aurora_Freeze_Whrilwind")),
		25.0f, 8.0f, 380.0f, 0.25f, 1.05f);
	// Cryoseism의 Range는 제자리 얼림 반경, Damage는 얼음이 터질 때의 피해다(처음 얼릴 때는 CryoInitialDamage).
	// 서리 검기(Q): 크게 원을 그려 내려 베는 동작(Primary_Attack_Slow_B, 칼이 내려오는 0.3초)에 앞쪽 부채꼴을 벤다. Range = 베는 거리.
	Define(EAuroraSkill::FrostSlash, TEXT("Frost Slash"), TEXT("Primary_Attack_Slow_B"), nullptr,
		30.0f, 6.0f, 420.0f, 0.30f, 0.45f);
	// 냉기 장판(R): 칼로 가리킨 자리(Cast)에 장판을 깔고, 칼을 들어 올린 자세(Ability_R_Targeting)로 FieldChannelSeconds 동안
	// 버티며 얼음 창을 내리꽂는다(2026-10-18 채널링으로 바뀜). Range = 시전 거리, Damage = 끝까지 버텼을 때 얼리는 피해.
	Define(EAuroraSkill::FrostField, TEXT("Frost Field"), TEXT("Cast"), nullptr,
		20.0f, 16.0f, 800.0f, 0.35f, FieldChannelSeconds + 0.05f);
	// 얼음 갑옷(A): 왼손을 하늘로 뻗는 동작(Emote_Ice_Sculpture 첫 구간)으로 ArmorRaiseSeconds 동안 손을 들어 올리고, 다 올라간 순간
	// 얼음 보호막을 두른다. 피해 없음, 받는 피해 감소. 버프 전용 동작은 팩에 없다(원작에 자기 강화 스킬이 없음) —
	// 10-25 「A는 4번에서 그냥 손만 뻗는 동작만 써 줄 수 있겠나? 자연스럽게」.
	// 그 전(10-20 「간단하고 짧은 동작 중에 괜찮은 거 없나 → A는 니 추천대로」): 칼을 하늘로 곧게 치켜든 자세(Ability_R_Targeting).
	// 그 전(10-20 오후): 원작 등장 동작 Level_Start에서 오른손을 들어 올렸다가 칼을 한 바퀴 휘둘러 내려 잡는 구간 — 「아쉽다」.
	// 그보다 전(10-18): 칼을 몸 앞에 세워 머리 위로 들었다가 땅에 꽂고 무릎 꿇는 동작(Recall 앞 1.6초를 1.3배, 꽂히는 원본 1.45초에 보호막).
	// 그보다 전 동작 Ability_R_InPlace_V2는 「어색하다」, 앞 0.9초만 쓴 Recall은 「짤린 느낌」이었다.
	Define(EAuroraSkill::IceArmor, TEXT("Ice Armor"), TEXT("Emote_Ice_Sculpture"), nullptr,
		0.0f, 16.0f, 0.0f, ArmorRaiseSeconds, ArmorHoldSeconds);
	Skills[EAuroraSkill::IceArmor].PlayRate = ArmorReachRate;
	// 서리 가속(S): 돌며 칼을 들어 올리는 동작(Ability_E 앞 0.9초)에 발밑에 하얀 서리 장판을 깐다. Range = 장판 반경.
	Define(EAuroraSkill::FrostHaste, TEXT("Frost Haste"), TEXT("Ability_E"), nullptr,
		0.0f, 18.0f, HasteRadius, 0.5f, 0.4f);
	// 얼음 파열(D, 2026-10-18 다시 짬): 앞으로 얼음 바위가 차례로 터진다. Range = 줄 길이(시작 거리 포함).
	// 동작은 10-19 밤 「칼을 땅에 박는 걸로」: 회전 베기(Primary_Attack_Fast_D) → 칼을 땅에 꽂는 Recall의 칼을 든 SpikePlantStart초부터
	// SpikePlantRate배(칼끝이 바닥에 닿는 원본 1.40초 = 0.225초, aurora-39th-plant — 1.5배일 땐 0.30초). 그 순간 SpikePlantHitStopSeconds
	// 멈칫한다(ExecuteIceSpikes). 칼끝이 바닥에 머무는 동작은 이것뿐이다(10-18의 A와 같은 원본, A는 처음부터 1.3배로 길게 들었다 꽂고
	// 무릎을 꿇었다).
	// 10-20 「살짝 점프했다가 내리꽂는 걸로」에 원작 도약(Ability_RMB_Fwd, 공중제비 뒤 내려찍기 — 살짝만 뛰는 동작은 팩에 없다)으로
	// 바꿨다가 「그냥 되돌려줘」로 되돌렸다.
	// 10-26 「궁극기를 일반 스킬로 빼고」로 D 자리는 옛 궁극기(Cryoseism)에 내주고, 고드름 비의 생각은 V 눈보라로 옮겼다(그 전 D는
	// Aurora.FX.VStorm 0으로만 남음 — 줄 길이·피해는 SpikeLineLength·SpikeLineDamage).
	// 눈보라(V): 칼로 가리키는 동작(Cast — R의 시작 동작이던 것, 칼이 앞을 가리키는 0.35초)에 겨눈 자리로 눈보라를 부르고 바로
	// 움직인다. 버티는 동작이 팩에 없어(Gideon의 Blackhole_Start 같은 것) 서서 버티지 않는다 — 10-26 「애니메이션이 있냐 없냐가 중요」.
	// Range = 시전 거리, Damage = 결정 하나가 꽂힐 때 피해(쏟아지는 수는 AuroraSkillComponentDFresh.cpp BlizzardSpikeCount).
	Define(EAuroraSkill::Blizzard, TEXT("Blizzard"), TEXT("Cast"), nullptr,
		2.0f, 40.0f, 900.0f, 0.35f, 0.35f);
	// 얼음 창: 얼음 칼날 LanceCount개를 부채꼴로 던져 처음 맞은 대상에 Damage, 주위에 LanceSplashDamage(대상마다 한 번).
	// Range = 최대 비행 거리.
	// 동작은 원작 돌진 동작(Ability_Q) — 머리 위로 들었다가 0.5초에 칼을 앞으로 뻗으며 던진다(2026-10-18 교체).
	// 10-26 「매 날리기 빼고」 → 「캐릭터 뒤쪽에 얼음 덩어리들이 각자 덩어리를 만들고 여러 명을 타겟팅해서 공격」(Aurora.FX.FShot 1,
	// AuroraSkillComponentDFresh.cpp): 칼을 드는 동안 뒤 머리 위에 덩어리 다섯이 생기고 뻗는 0.5초부터 차례로 겨눈 자리에 가까운 적들에게 —
	// Damage = 덩어리 하나(한 명에게 다 꽂히면 다섯 배), Range = 겨누는 반경. 쿨 · 사거리는 2번 F(Crystal Shot) 것(그 전 매 40 · 7 · 1400 —
	// FShot 0의 매도 이 값을 쓴다). 이름도 바꿈(그 전 Ice Lance).
	Define(EAuroraSkill::IceLance, TEXT("Ice Barrage"), TEXT("Ability_Q"), nullptr,
		30.0f, 12.0f, 1100.0f, 0.50f, 0.40f);
	// 10-26 궁극기(V) → D 일반 스킬: 쿨타임 40 → 그 전 D와 같은 8초(나머지 그대로)
	Define(EAuroraSkill::Cryoseism, TEXT("Cryoseism"), TEXT("Ability_R"), LoadEffect(TEXT("Ultimate"), TEXT("P_Aurora_Ultimate_Warmup")),
		40.0f, 8.0f, 500.0f, 1.20f, 0.80f);

	MeleeImpact = LoadEffect(TEXT("Primary"), TEXT("P_Aurora_Melee_SucessfulImpact"));
	MeleeSnowflakes = LoadEffect(TEXT("Primary"), TEXT("P_Aurora_Primary_Snowflakes"));
	FreezeSegment = LoadEffect(TEXT("Freeze"), TEXT("P_Aurora_Freeze_Segment"));
	FreezeSegmentCrumble = LoadEffect(TEXT("Freeze"), TEXT("P_Aurora_Freeze_Segment_Crumble"));
	FreezeRooted = LoadEffect(TEXT("Freeze"), TEXT("P_Aurora_Freeze_Rooted"));
	SwordTrails.Add(LoadEffect(TEXT("Primary"), TEXT("P_Aurora_Primary_Trail")));
	SwordTrails.Add(LoadRampageIce(TEXT("P_Rampage_Ice_MeleeTrails_Regular")));
	SwordTrails.Add(LoadRampageIce(TEXT("P_Rampage_Ice_MeleeTrails_Enraged")));
	{
		static ConstructorHelpers::FObjectFinder<UParticleSystem> KwangTrail(
			TEXT("/Game/ParagonKwang/FX/Particles/Abilities/Primary/FX/P_Kwang_Primary_Trail_R.P_Kwang_Primary_Trail_R"));
		SwordTrails.Add(KwangTrail.Object);
	}
	{
		static ConstructorHelpers::FObjectFinder<UStaticMesh> Chunk(TEXT("/Game/ParagonAurora/FX/Meshes/Ice/SM_Ice_Chunk.SM_Ice_Chunk"));
		IceChunkMesh = Chunk.Object;
		static ConstructorHelpers::FObjectFinder<UParticleSystem> Chip(
			TEXT("/Game/ParagonAurora/FX/Particles/Aurora/P_Aurora_Sculpture_Chip.P_Aurora_Sculpture_Chip"));
		SculptureChip = Chip.Object;
	}
	ChargeStopAnimation = LoadAnimation(TEXT("Ability_Q_Stop"));
	ChargeLungeAnimation = LoadAnimation(TEXT("Ability_Q"));
	FieldChannelAnimation = LoadAnimation(TEXT("Ability_R_Targeting"));
	FieldAimAnimation = LoadAnimation(TEXT("Ability_Q_Targeting"));
	FieldReachAnimation = LoadAnimation(TEXT("Emote_Slice"));
	FieldCarveAnimation = LoadAnimation(TEXT("Emote_Ice_Sculpture"));
	FieldKneelAnimation = LoadAnimation(TEXT("Recall"));
	CrossFirstAnimation = LoadAnimation(TEXT("Primary_Attack_Fast_C"));
	CrossSecondAnimation = LoadAnimation(TEXT("Primary_Attack_Fast_B"));
	DashFlare = LoadEffect(TEXT("Dash"), TEXT("P_Aurora_Dash_Flare"));
	DashBodyFrost = LoadEffect(TEXT("Dash"), TEXT("P_Aurora_Dash_Frost_BodyDecals"));
	WallBase = LoadEffect(TEXT("Dash"), TEXT("P_Aurora_Wall_Base"));
	WallTop = LoadEffect(TEXT("Dash"), TEXT("P_Aurora_Wall_Top"));
	WallBaseDestroy = LoadEffect(TEXT("Dash"), TEXT("P_Aurora_Wall_Base_Destroy"));
	WallTopDestroy = LoadEffect(TEXT("Dash"), TEXT("P_Aurora_e_Wall_Top_Destroy"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Icicles(TEXT("/Game/ParagonAurora/FX/Meshes/Aurora/SM_Icicle_Wall_01.SM_Icicle_Wall_01"));
	IcicleWall = Icicles.Object;
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Statue(TEXT("/Game/ParagonAurora/FX/Meshes/Aurora/SM_Aurora_Decoy.SM_Aurora_Decoy"));
	DecoyStatue = Statue.Object;
	DecoySpawn = LoadEffect(TEXT("Leap"), TEXT("P_Aurora_Decoy_Spawn"));
	DecoyExplode = LoadEffect(TEXT("Leap"), TEXT("P_Aurora_Decoy_Explode_Fragments"));
	DecoyCrumble = LoadEffect(TEXT("Leap"), TEXT("P_Aurora_Decoy_Crumble_Fall"));
	// 87차(AuroraSkillComponentPolish.cpp): 단독 촬영 aurora-87th-catalog에서 보이고 얼음색인 것만
	RockHitBurst = LoadRampageIce(TEXT("P_Rampage_Ice_Rock_HitCharacter"));
	RockThrowFx = LoadRampageIce(TEXT("P_Rampage_Ice_Rock_Throw"));
	EnrageLoopFx = LoadRampageIce(TEXT("P_Rampage_Ice_Enrage_Looping"));
	EnrageSparksFx = LoadRampageIce(TEXT("P_Rampage_Ice_Elemental_Enraged_Sparks_Local"));
	RockFlyingFx = LoadRampageIce(TEXT("P_Rampage_Ice_Rock_Flying"));
	DecoyFragmentsFx = LoadEffect(TEXT("Leap"), TEXT("P_Aurora_Decoy_Fragments"));
	{
		static ConstructorHelpers::FObjectFinder<UParticleSystem> RecallIcicles(
			TEXT("/Game/ParagonAurora/FX/Particles/Aurora/P_Aurora_Recall_Icicle_Walls.P_Aurora_Recall_Icicle_Walls"));
		IcicleWallsFx = RecallIcicles.Object;
	}
	DashAimIntroAnimation = LoadAnimation(TEXT("Ability_Q_Targeting_Intro"));
	DecoyFrostFx = LoadEffect(TEXT("Leap"), TEXT("P_Aurora_Decoy_Frost"));
	{
		static ConstructorHelpers::FObjectFinder<UParticleSystem> HandIce(
			TEXT("/Game/ParagonAurora/FX/Particles/Aurora/P_Aurora_Recall_HandIce.P_Aurora_Recall_HandIce"));
		HandIceFx = HandIce.Object;
	}
	LeapTrail = LoadEffect(TEXT("Leap"), TEXT("P_Aurora_Leap_Trail"));
	CryoInitialBlast = LoadEffect(TEXT("Ultimate"), TEXT("P_Aurora_Ultimate_InitialBlast"));
	CryoFrozen = LoadEffect(TEXT("Ultimate"), TEXT("P_Aurora_Ultimate_Frozen"));
	CryoExplode = LoadEffect(TEXT("Ultimate"), TEXT("P_Aurora_Ultimate_Explode"));
	CryoSlowed = LoadEffect(TEXT("Ultimate"), TEXT("P_Aurora_Ultimate_Slowed"));
	{
		// 감정 표현(눈사람 걷어차기)용 이펙트라 Abilities 밖 폴더에 있다.
		static ConstructorHelpers::FObjectFinder<UParticleSystem> Kicked(
			TEXT("/Game/ParagonAurora/FX/Particles/Aurora/P_Aurora_SnowMinion_Kicked.P_Aurora_SnowMinion_Kicked"));
		PrisonBurstEffect = Kicked.Object;
		static ConstructorHelpers::FObjectFinder<UParticleSystem> Thrust(
			TEXT("/Game/ParagonAurora/FX/Particles/Aurora/P_Aurora_Sculpture_Thrust.P_Aurora_Sculpture_Thrust"));
		SlashSparkles = Thrust.Object;
	}
	LanceTrail = LoadEffect(TEXT("Leap"), TEXT("P_Aurora_Leap_Trail"));
	IceShock = LoadRampageIce(TEXT("P_Rampage_Lunge_ImpactBlue"));
	IceShockBig = LoadRampageIce(TEXT("P_Rampage_Lunge_ImpactBlueEnraged"));
	IceShards = LoadRampageIce(TEXT("P_Rampage_Ice_Rock_HitWorld"));
	IceChargeGlow = LoadRampageIce(TEXT("P_Rampage_Ice_Enrage_Cast"));
	IceFrostPuff = LoadRampageIce(TEXT("P_Rampage_Ice_Enrage_End"));
	IceChunks = LoadRampageIce(TEXT("P_Rampage_Ice_Rock_Cancel"));
	LanceFlash = LoadEffect(TEXT("Dash"), TEXT("P_Aurora_Dash_WarmUp"));
	{
		// 얼음 갑옷 보호막. 재질은 Tools/CharacterPipeline/aurora_shell_material_build.py가 만든다(Paragon 보호막 재질은
		// 속이 검거나 어두운 바닥에서 안 보였다).
		static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
		ShellMesh = Sphere.Object;
		static ConstructorHelpers::FObjectFinder<UStaticMesh> Cone(TEXT("/Engine/BasicShapes/Cone.Cone"));
		BladeMesh = Cone.Object;
		static ConstructorHelpers::FObjectFinder<UStaticMesh> Plane(TEXT("/Engine/BasicShapes/Plane.Plane"));
		PlaneMesh = Plane.Object;
		// 쓸 때 불러온다(Sparrow 재질과 같은 방식). 생성자에서 붙잡으면 에디터가 켜질 때부터 잡혀 있어 만드는 도구가 고치지 못한다.
		// 10-18 밤 디아블로 3 얼음 갑옷 느낌(둥근 구 + 육각 얼음판)으로 바꿨고, 10-19 육각판이 벌집처럼 붙어 1/5쯤 덮는 모양으로
		// 정했다(aurora_frost_materials_build.py build_armor_honey). 전 재질 M_Aurora_ArmorShell은 남겨 둔다.
		ShellMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_IceArmor.M_Aurora_IceArmor")));
		// S 장판은 눈송이 모양(10-18 밤 「원보다는 눈 모양」, 10-20부터 같은 재질에 그림만 눈 마법진 T_Aurora_SnowCircle), Q 시안 1 자국은 둥근 서리.
		HasteFloorMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_SnowFloor.M_Aurora_SnowFloor")));
		FrostTrailMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_FrostFloor.M_Aurora_FrostFloor")));
		CrackFloorMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_IceCrack.M_Aurora_IceCrack")));
		SnowCoverMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_SnowCover.M_Aurora_SnowCover")));
		SlashArcMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_SlashArc.M_Aurora_SlashArc")));
		FrostSweepMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_FrostSweep.M_Aurora_FrostSweep")));
		SpinRingMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_SpinRing.M_Aurora_SpinRing")));
		SpinFrostMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_SpinFrost.M_Aurora_SpinFrost")));
		DashStreakMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_DashStreak.M_Aurora_DashStreak")));
		FlakeMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_FlakeSprite.M_Aurora_FlakeSprite")));
		SlashScarMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_SlashScar.M_Aurora_SlashScar")));
		HasteCrackMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_HasteCrack.M_Aurora_HasteCrack")));
		HasteFlakeCrackMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_HasteFlakeCrack.M_Aurora_HasteFlakeCrack")));
		HasteRimCrackMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_RimCrack.M_Aurora_RimCrack")));
		HasteRimShatterMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_RimShatter.M_Aurora_RimShatter")));
		RuptureCrackMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_RuptureCrack.M_Aurora_RuptureCrack")));
		LanceImpactCrackMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_ImpactCrack.M_Aurora_ImpactCrack")));
		WaveBladeMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_WaveBlade.M_Aurora_WaveBlade")));
		CutMarkMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_CutMark.M_Aurora_CutMark")));
		WaveBladeBrightMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_WaveBladeBright.M_Aurora_WaveBladeBright")));
		GlowIceMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_GlowIce.M_Aurora_GlowIce")));
		WaveBladeRoughMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_WaveBladeRough.M_Aurora_WaveBladeRough")));
		NovaRingMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_NovaRing.M_Aurora_NovaRing")));
		WaveBladeRougherMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_WaveBladeRougher.M_Aurora_WaveBladeRougher")));
		NovaRingRoughMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_NovaRingRough.M_Aurora_NovaRingRough")));
		SnowCircleRoughTexture = TSoftObjectPtr<UTexture>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/T_Aurora_SnowCircleRough.T_Aurora_SnowCircleRough")));
		SnowCircleRingTexture = TSoftObjectPtr<UTexture>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/T_Aurora_SnowCircleRing.T_Aurora_SnowCircleRing")));
		HasteFloorRoughMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_SnowFloorRough.M_Aurora_SnowFloorRough")));
		WaveBladeFlipMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_WaveBladeFlip.M_Aurora_WaveBladeFlip")));
		WaveBladeSkinMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_WaveBladeSkin.M_Aurora_WaveBladeSkin")));
		CloneIceMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_CloneIce.M_Aurora_CloneIce")));
		QSlashForgeMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_QSlashForge.M_Aurora_QSlashForge")));
		FlakeArmMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_FlakeArm.M_Aurora_FlakeArm")));
		YinWindSpline = TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(
			TEXT("/Game/ParagonYin/FX/Meshes/Heroes/Yin/Abilities/SM_WindSpline_WhipCrack.SM_WindSpline_WhipCrack")));
		YinAfterimage = TSoftObjectPtr<UParticleSystem>(FSoftObjectPath(
			TEXT("/Game/ParagonYin/FX/Particles/Yin/Abilities/WhipCrack/FX/p_WhipCrack_Afterimages.p_WhipCrack_Afterimages")));
		YinKickOff = TSoftObjectPtr<UParticleSystem>(FSoftObjectPath(
			TEXT("/Game/ParagonYin/FX/Particles/Yin/Abilities/LashKick/FX/p_Lash_KickOff.p_Lash_KickOff")));
	}
}

void UAuroraSkillComponent::BeginPlay()
{
	Super::BeginPlay();
	Character = Cast<ATopDownCombatCharacter>(GetOwner());
	USkeletalMeshComponent* Mesh = Character.IsValid() ? Character->GetMesh() : nullptr;
	bEnabled = Mesh && Mesh->GetSkeletalMeshAsset() && Mesh->GetAnimInstance();
	if (bEnabled)
	{
		// 스킬 동작은 애니 BP 사본의 전신 슬롯(AuroraFullBody)에 몽타주로 재생한다. 이동은 루트 모션 소스(돌진·도약)가 맡으므로
		// 원본 동작의 루트 이동은 늘 무시한다(평타도 같은 규칙).
		Mesh->GetAnimInstance()->SetRootMotionMode(ERootMotionMode::IgnoreRootMotion);
	}
	// 얼음 창(F) 칼날은 얼음 분신 석상의 재질을 쓴다(게임에서 얼음으로 보이는 것이 확인된 재질).
	BladeMaterial = DecoyStatue ? DecoyStatue->GetMaterial(0) : nullptr;
	// 바닥 데칼·보호막 재질은 시전 순간에 처음 불러오지 않게 캐릭터가 나올 때 미리 불러 둔다(첫 시전 때 디스크 읽기로 멈칫하지 않게).
	// 생성자가 아니라 플레이 중에만 붙잡으므로 재질 만드는 도구와 부딪히지 않는다.
	for (const TSoftObjectPtr<UMaterialInterface>* Soft : {&ShellMaterial, &HasteFloorMaterial, &FrostTrailMaterial, &CrackFloorMaterial,
		&SnowCoverMaterial, &SlashArcMaterial, &FrostSweepMaterial, &SpinRingMaterial, &SpinFrostMaterial, &DashStreakMaterial,
		&FlakeMaterial, &SlashScarMaterial, &HasteCrackMaterial, &HasteFlakeCrackMaterial, &HasteRimCrackMaterial, &HasteRimShatterMaterial,
		&RuptureCrackMaterial, &LanceImpactCrackMaterial, &WaveBladeMaterial, &CutMarkMaterial})
	{
		if (UMaterialInterface* Material = Soft->LoadSynchronous())
		{
			PreloadedMaterials.Add(Material);
		}
	}
	// 데칼 재질을 처음 그리는 한 장면은 엔진이 그 재질의 그리기 준비(PSO)를 마칠 때까지 기본 재질(초록 사각형)로 비친다
	// (10-19 Q 시안: 첫 시전 0.30초에만 초록, 두 번째 시전은 깨끗 — 재질 미리 불러오기·사본 먼저 만들기·나타남 0 고치기로는 안 없어짐).
	// → 캐릭터가 나올 때 데칼 재질마다 1cm짜리를 발밑에 잠깐 깔아 그 첫 장면을 안 보이는 크기에서 치른다.
	const FVector Feet = GetFeetLocation();
	for (UMaterialInterface* Material : PreloadedMaterials)
	{
		if (Material && Material->GetMaterial() && Material->GetMaterial()->MaterialDomain == MD_DeferredDecal)
		{
			if (UDecalComponent* Warm = UGameplayStatics::SpawnDecalAtLocation(GetWorld(), Material, FVector(FloorDecalDepth, 1.0f, 1.0f),
				Feet, FRotator(-90.0f, 0.0f, 0.0f), 0.5f))
			{
				// 화면에서 너무 작다고 빼 버리면 그리지 않아 준비도 안 된다.
				Warm->SetFadeScreenSize(0.0f);
			}
		}
	}
	if (IcicleWall)
	{
		// 메시마다 크기·축이 달라 실제 경계 상자로 높이를 맞추고, 긴 축을 돌진 방향에 둔다.
		const FBoxSphereBounds Bounds = IcicleWall->GetBounds();
		const FVector Extent = Bounds.BoxExtent;
		WallScale = FMath::Clamp(ChargeWallHeight / FMath::Max(2.0f * Extent.Z, 1.0f), 0.2f, 3.0f);
		WallYawOffset = Extent.X >= Extent.Y ? 0.0f : 90.0f;
		WallStep = FMath::Max(2.0f * FMath::Max(Extent.X, Extent.Y) * WallScale * 0.9f, 60.0f);
		WallLift = (Extent.Z - Bounds.Origin.Z) * WallScale;
		UE_LOG(LogTemp, Display, TEXT("AURORA_WALL mesh=%s extent=%s origin=%s scale=%.2f step=%.0f yaw=%.0f lift=%.0f"),
			*IcicleWall->GetName(), *Extent.ToCompactString(), *Bounds.Origin.ToCompactString(), WallScale, WallStep, WallYawOffset, WallLift);
	}
	for (const TPair<EAuroraSkill, FAuroraSkillDefinition>& Pair : Skills)
	{
		const UAnimSequence* Animation = Pair.Value.Animation;
		UE_LOG(LogTemp, Display, TEXT("AURORA_ANIM skill=%s anim=%s length=%.3f skeleton_match=%d"),
			*Pair.Value.Name.ToString(), *GetNameSafe(Animation), Animation ? Animation->GetPlayLength() : 0.0f,
			Animation && Mesh && Animation->GetSkeleton() == Mesh->GetSkeletalMeshAsset()->GetSkeleton());
	}
}

const FAuroraSkillDefinition* UAuroraSkillComponent::FindSkill(int32 Slot) const
{
	return Slot >= 0 && Slot < SlotCount ? Skills.Find(static_cast<EAuroraSkill>(Slot)) : nullptr;
}

FText UAuroraSkillComponent::GetSkillDisplayName(int32 Slot) const
{
	const FAuroraSkillDefinition* Skill = FindSkill(Slot);
	return Skill ? FText::FromName(Skill->Name) : FText::GetEmpty();
}

ECharacterSkillTargeting UAuroraSkillComponent::GetSkillTargeting(int32 Slot) const
{
	// 도약(W)만 대상 지정(헤더 LeapAboveHead 설명), 나머지는 방향·지점 지정이다(대상을 고르던 얼음 감옥은 2026-10-18 얼음 갑옷으로 바뀌었다).
	return Slot == static_cast<int32>(EAuroraSkill::FrozenSimulacrum) ? ECharacterSkillTargeting::Actor : ECharacterSkillTargeting::Direction;
}

bool UAuroraSkillComponent::IsSkillTargetValid(int32 Slot, const AActor* Target, const AActor* Caster) const
{
	// 기본 규칙(Pawn만)과 달리 수련장 허수아비도 대상으로 친다.
	return IsCombatTarget(Target, Caster) && Target->CanBeDamaged();
}

float UAuroraSkillComponent::GetSlotCooldownRemaining(int32 Slot) const
{
	// Q2를 받는 동안 Q는 재사용 대기와 상관없이 쓸 수 있다.
	if (Slot == static_cast<int32>(EAuroraSkill::FrostSlash) && GetWorld() && GetWorld()->GetTimeSeconds() < CrossWindowEnds)
	{
		return 0.0f;
	}
	const double* End = FindSkill(Slot) ? CooldownEnds.Find(static_cast<EAuroraSkill>(Slot)) : nullptr;
	return End && GetWorld() && !IgnoresCooldowns() ? FMath::Max(0.0f, static_cast<float>(*End - GetWorld()->GetTimeSeconds())) : 0.0f;
}

FString UAuroraSkillComponent::GetInputFeedback() const
{
	return GetWorld() && GetWorld()->GetTimeSeconds() < FeedbackDeadline ? Feedback : FString();
}

bool UAuroraSkillComponent::IgnoresCooldowns() const
{
	return CVarAuroraIgnoreCooldowns.GetValueOnGameThread() != 0;
}

bool UAuroraSkillComponent::RejectInput(const TCHAR* Reason)
{
	Feedback = Reason;
	FeedbackDeadline = GetWorld() ? GetWorld()->GetTimeSeconds() + 1.25 : 0.0;
	UE_LOG(LogTemp, Display, TEXT("AURORA_SKILL rejected=%s"), Reason);
	return false;
}

bool UAuroraSkillComponent::TryUseSkillSlot(int32 Slot, const FVector& AimLocation, AActor* Target)
{
	const FAuroraSkillDefinition* Skill = FindSkill(Slot);
	if (!Skill || !bEnabled || !GetWorld() || !Character.IsValid() || !Character->GetCharacterMovement() ||
		Character->GetCharacterMovement()->MovementMode != MOVE_Walking || AimLocation.ContainsNaN())
	{
		return RejectInput(TEXT("Unavailable"));
	}
	if (bCasting && ActiveSkill == EAuroraSkill::FrostField && IsFieldChannelling())
	{
		// 냉기 장판 채널링 중 다른 스킬 키를 누르면 채널링을 끊고 그 스킬을 바로 쓴다.
		CancelFrostChannel(TEXT("skill"));
	}
	const bool bCrossStyle = CVarAuroraSlashStyle.GetValueOnGameThread() == 5;
	if (bCrossStyle && bCasting && ActiveSkill == EAuroraSkill::FrostSlash && !bCrossCast && Slot == static_cast<int32>(EAuroraSkill::FrostSlash))
	{
		// Q1이 끝나기 전에 Q를 다시 누르면 받아 두었다가 Q1이 끝나는 순간 Q2를 벤다(FinishCast).
		bCrossQueued = true;
		CrossAim = AimLocation;
		UE_LOG(LogTemp, Display, TEXT("AURORA_CROSS queued"));
		return true;
	}
	if (bCasting)
	{
		return RejectInput(TEXT("Casting"));
	}
	if (bCrossStyle && Slot == static_cast<int32>(EAuroraSkill::FrostSlash) && GetWorld()->GetTimeSeconds() < CrossWindowEnds)
	{
		return BeginFrostCross(AimLocation);
	}
	if (GetSlotCooldownRemaining(Slot) > 0.0f)
	{
		return RejectInput(TEXT("Cooldown"));
	}
	const EAuroraSkill Kind = static_cast<EAuroraSkill>(Slot);
	switch (Kind)
	{
	case EAuroraSkill::GlacialCharge:
	{
		// 끝점은 시전 때 정한다(벽·낭떠러지 앞에서 멈춤). 짧으면 돌진하지 않는다.
		FVector End;
		if (!PlanGlacialCharge(AimLocation, End))
		{
			return RejectInput(TEXT("No room to charge"));
		}
		ChargeEnd = End;
		ChargeSeconds = FVector::Dist2D(Character->GetActorLocation(), End) / ChargeSpeed;
		break;
	}
	case EAuroraSkill::FrozenSimulacrum:
	{
		// 대상 바로 앞(떠난 쪽)에 내려선다(헤더 LeapAboveHead 설명). 착지점은 실제로 설 수 있는 내비 위여야 한다.
		if (!IsSkillTargetValid(Slot, Target, Character.Get()))
		{
			return RejectInput(TEXT("No target"));
		}
		if (FVector::Dist2D(GetFeetLocation(), Target->GetActorLocation()) > Skill->Range)
		{
			return RejectInput(TEXT("Out of range"));
		}
		float Radius = 0.0f;
		float HalfHeight = 0.0f;
		Target->GetSimpleCollisionCylinder(Radius, HalfHeight);
		FVector Toward = (Target->GetActorLocation() - Character->GetActorLocation()).GetSafeNormal2D();
		if (Toward.IsNearlyZero())
		{
			Toward = Character->GetActorForwardVector().GetSafeNormal2D();
		}
		const FVector TargetFeet = Target->GetActorLocation() - FVector(0.0f, 0.0f, HalfHeight);
		const float Gap = Radius + Character->GetCapsuleComponent()->GetScaledCapsuleRadius() + LeapLandGap;
		FVector Landing;
		if (!ClampGroundTarget(TargetFeet - Toward * Gap, Skill->Range, true, Landing))
		{
			return RejectInput(TEXT("No walkable destination"));
		}
		LeapTarget = Landing + FVector(0.0f, 0.0f, Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
		LeapTargetActor = Target;
		break;
	}
	case EAuroraSkill::FrostField:
	{
		// R 새 스킬 러프 시안(Aurora.FX.RDraft, AuroraSkillComponentRDrafts.cpp)이 켜져 있으면 지금 R 대신 그 시안을 쓴다
		if (const int32 Draft = GetRDraft(); Draft != 0)
		{
			return BeginRDraft(Draft, AimLocation);
		}
		// 장판 자리는 시전 거리 안 바닥으로 당긴다(내비가 없어도 된다).
		FVector Spot;
		if (!ClampGroundTarget(AimLocation, Skill->Range, false, Spot))
		{
			return RejectInput(TEXT("No ground"));
		}
		FieldCenter = Spot;
		break;
	}
	case EAuroraSkill::FrostSlash:
	case EAuroraSkill::IceArmor:
	case EAuroraSkill::Hoarfrost:
	case EAuroraSkill::Cryoseism:
	case EAuroraSkill::FrostHaste:
	case EAuroraSkill::Blizzard:
	case EAuroraSkill::IceLance:
		break;
	}
	return BeginCast(Kind, AimLocation);
}

FVector UAuroraSkillComponent::GetFeetLocation() const
{
	return Character.IsValid() ? Character->GetActorLocation() -
		FVector(0.0f, 0.0f, Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()) : FVector::ZeroVector;
}

bool UAuroraSkillComponent::ClampGroundTarget(const FVector& Aim, float Range, bool bRequireNavigation, FVector& Result) const
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
	FCollisionQueryParams Query(SCENE_QUERY_STAT(AuroraGround), false, Character.Get());
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

bool UAuroraSkillComponent::BeginCast(EAuroraSkill Skill, const FVector& Aim)
{
	if (Skill == EAuroraSkill::IceArmor)
	{
		ApplyArmorTiming();
	}
	const FAuroraSkillDefinition& Definition = Skills[Skill];
	USkeletalMeshComponent* Mesh = Character->GetMesh();
	if (!Mesh || !Mesh->GetAnimInstance())
	{
		return RejectInput(TEXT("Unavailable"));
	}
	PrepareCast(Skill, Aim);
	if (Skill == EAuroraSkill::GlacialCharge && CVarAuroraChargeRun.GetValueOnGameThread() == 2 && ChargeLungeAnimation)
	{
		// 시안 2: 원작 돌진 동작(Ability_Q). 10-20부터 처음(칼을 들어 올리는 준비)부터 재생한다 — 전엔 내지르며 몸을 숙인 구간부터.
		PlayFullBody(ChargeLungeAnimation, ChargeLungeRate, ChargeLungeStart);
	}
	else if (Skill == EAuroraSkill::GlacialCharge && CVarAuroraChargeRun.GetValueOnGameThread() == 1)
	{
		// 시안 1: 같은 달리기 동작을 빠르게 돌린다(돌진이 0.45초 남짓이라 원래 속도로는 한 걸음도 다 못 뛴다).
		PlayFullBody(Definition.Animation, ChargeRunFastRate);
	}
	else if (Skill == EAuroraSkill::IceArmor)
	{
		// A: 왼손을 하늘로 뻗는 첫 구간만 — 끝(ArmorReachEnd)은 회복이 끝나며 FinishCast가 섞어 내린다.
		// 골반 자리는 섞이기 전 자세에서 잡는다.
		BeginArmorPoseLock();
		// 93차 「A는 시전 애니메이션 다른 거 없어?」 동작 시안(Aurora.FX.AMotion, AuroraSkillComponentPolish.cpp) — 0이면 그 전 손 뻗기
		if (!PlayArmorMotion())
		{
			PlayFullBody(Definition.Animation, Definition.PlayRate, 0.0f, 1, ArmorReachBlendIn);
		}
	}
	else if (Skill == EAuroraSkill::FrostField && CVarAuroraFieldChannel.GetValueOnGameThread() == 9)
	{
		// R 시안 9: 칼로 얼음을 깎는 동작을 시전부터 버티기 끝까지 끊지 않고 튼다.
		PlayFullBody(FieldCarveAnimation);
	}
	else if (Skill == EAuroraSkill::FrostField && CVarAuroraFieldChannel.GetValueOnGameThread() >= 6)
	{
		// R 시안 6~8: 가리키는 Cast 대신 칼을 들어 긋고 손을 뻗는 동작을 시전부터 버티기 끝까지 끊지 않고 튼다(ExecuteFrostField는 그대로 둔다).
		// 7은 버티는 동안 손을 다시 뻗는 동작을 FrostFieldTick이 겹쳐 틀고, 8은 같은 동작의 시각을 FrostFieldTick이 앞뒤로 옮긴다.
		PlayFullBody(FieldReachAnimation, 1.0f, FieldSliceOpenStart);
	}
	else if (Skill == EAuroraSkill::IceLance && PlayLanceMotion())
	{
		// 95차 F 동작 시안(Aurora.FX.FMotion, AuroraSkillComponentPolish.cpp)
	}
	else
	{
		PlayFullBody(Definition.Animation, Definition.PlayRate);
	}
	const bool bSkipCryoCast = Skill == EAuroraSkill::Cryoseism && (CVarAuroraCryoSkip.GetValueOnGameThread() & 128);
	// E 휘두름 시안(Aurora.FX.EStyle) 1~3은 팩 회오리 대신 휘두르는 동안(시전 0초 ~ 내려찍는 0.25초) 제 이펙트를 띄운다.
	const int32 FreezeStyle = Skill == EAuroraSkill::Hoarfrost ? CVarAuroraFreezeStyle.GetValueOnGameThread() : 0;
	// 4(E1)는 바닥 무늬 없이 칼 궤적만 쓴다.
	if (Skill == EAuroraSkill::Hoarfrost && FreezeStyle != 1 && FreezeStyle != 4 && CVarAuroraFreezeRing.GetValueOnGameThread() != 0)
	{
		// 회오리와 같은 크기로 보이게 키운다(HoarfrostRingScale).
		SweepFloorDecal(SpinRingMaterial.LoadSynchronous(), GetFeetLocation(), Character->GetActorForwardVector(),
			Definition.Range * HoarfrostRingScale, HoarfrostSpinSeconds, Definition.ActionTime);
	}
	switch (FreezeStyle)
	{
	case 0:
		break;
	case 2:
		// 서리 소용돌이: 감겨 나가는 서리 줄기가 한 바퀴 휩쓸며 드러나고, 남아 있는 동안 계속 돌며 사라진다.
		if (UDecalComponent* Spiral = SweepFloorDecal(SpinFrostMaterial.LoadSynchronous(), GetFeetLocation(), Character->GetActorForwardVector(),
			Definition.Range, HoarfrostSpinSeconds, Definition.ActionTime))
		{
			TWeakObjectPtr<UDecalComponent> Weak = Spiral;
			const int32 Steps = FMath::CeilToInt(HoarfrostSpinSeconds * 30.0f);
			for (int32 Step = 1; Step <= Steps; ++Step)
			{
				GetWorld()->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, [Weak]()
				{
					if (UDecalComponent* Decal = Weak.Get())
					{
						Decal->AddWorldRotation(FRotator(0.0f, HoarfrostSpinDegreesPerSecond / 30.0f, 0.0f));
					}
				}), Step / 30.0f, false);
			}
		}
		break;
	case 3:
		// 청록 냉기 소용돌이(Rampage 얼음판 시전 빛): 발밑에서 냉기가 돌며 모인다.
		SpawnBurstLater(IceChargeGlow, GetFeetLocation(), HoarfrostGlowScale, 0.0f);
		break;
	case 4:
		// 칼 궤적: 도는 칼을 따라 허리 높이에 고리가 그려진다.
		BeginSwordTrail(HoarfrostTrailSeconds);
		break;
	default:
		// 원형 검기: 몸을 한 바퀴 도는 칼날 빛이 앞에서부터 시계 방향으로 휩쓸며 드러났다 사라진다.
		SweepFloorDecal(SpinRingMaterial.LoadSynchronous(), GetFeetLocation(), Character->GetActorForwardVector(), Definition.Range,
			HoarfrostSpinSeconds, Definition.ActionTime);
		break;
	}
	if (Definition.CastEffect && !bSkipCryoCast && FreezeStyle == 0)
	{
		UParticleSystemComponent* CastComponent = UGameplayStatics::SpawnEmitterAttached(Definition.CastEffect, Mesh, NAME_None,
			FVector::ZeroVector, FRotator::ZeroRotator, EAttachLocation::KeepRelativeOffset, true);
		if (Skill == EAuroraSkill::Hoarfrost)
		{
			// E 회오리는 띠가 사라질 때 남은 얼음 조각도 같이 지운다(혼자 떠다니지 않게).
			DestroyEffectLater(CastComponent, HoarfrostSwirlSeconds);
		}
		if (Skill == EAuroraSkill::Cryoseism && CastComponent)
		{
			CastComponent->SetRelativeScale3D(FVector(CryoEffectScale));
		}
	}
	if (Skill == EAuroraSkill::Cryoseism && CVarAuroraCryoStyle.GetValueOnGameThread() >= 2 && !bSkipCryoCast)
	{
		// R 시안 2·3: 뛰어오르는 동안 발밑에 청록 냉기가 돌며 모인다(약 0.5~1.0초에 가장 밝음, 착지 1.2초).
		SpawnBurstLater(IceChargeGlow, GetFeetLocation(), CryoChargeGlowScale * CryoEffectScale, 0.0f);
	}
	if (Skill == EAuroraSkill::FrozenSimulacrum)
	{
		// 원작처럼 떠난 자리에 얼음 분신을 남긴다. 도약 전에 세워야 시전 자세 그대로 남는다.
		SpawnDecoy();
	}
	if (Skill == EAuroraSkill::IceLance)
	{
		// F 얼음 덩어리 일제 사격: 칼을 드는 동안 뒤 머리 위에 덩어리가 생긴다(그 전 매 날리기면 아무것도 안 함)
		BeginChunkVolley();
	}
	StartCooldown(Skill);
	UE_LOG(LogTemp, Display, TEXT("AURORA_SKILL cast=%s slot=%d aim=%s montage=%d"), *Definition.Name.ToString(),
		ActiveSlot, *Aim.ToCompactString(), ActiveMontage && Mesh->GetAnimInstance()->Montage_IsPlaying(ActiveMontage));

	FTimerManager& Timers = GetWorld()->GetTimerManager();
	// Q1(QStyle 5)·얼음 검기(6)는 칼끝이 앞을 지나는 순간(QWaveLaunch)에 검기를 떠나보낸다. 5는 끝나는 때가 그대로다.
	const int32 SlashStyle = Skill == EAuroraSkill::FrostSlash ? CVarAuroraSlashStyle.GetValueOnGameThread() : 0;
	const float ActionTime = SlashStyle == 5 || SlashStyle == 6 ? QWaveLaunch : Definition.ActionTime;
	Timers.SetTimer(ActionTimer, FTimerDelegate::CreateUObject(this, &UAuroraSkillComponent::ExecuteAction, CastGeneration),
		FMath::Max(ActionTime, 0.01f), false);
	const float Recovery = Skill == EAuroraSkill::GlacialCharge ? ChargeSeconds + GetChargeStopSeconds() : Definition.RecoveryTime;
	// 눕힌 두 번(Aurora.FX.QFlat 1, 헤더 QFlatVolley 설명)은 Fast_C 「\」까지만
	const bool bFlatVolley = SlashStyle == 6 && CVarAuroraSlashFlat.GetValueOnGameThread() != 0;
	Timers.SetTimer(RecoveryTimer, this, &UAuroraSkillComponent::FinishCast,
		SlashStyle == 6 ? (bFlatVolley ? QFlatVolleyEnd : QVolleyEnd) : Definition.ActionTime + Recovery, false);
	if (SlashStyle == 6)
	{
		// 얼음 검기 세 번: Slow_B 「/」 → Fast_C 「\」 → Fast_B 「/」(Q2와 같은 이음 — 앞 동작 끝 자세가 다음 시작 자세와 같다).
		// 첫 검기는 ExecuteFrostSlash가, 둘째·셋째는 칼마다 여기서 건 예약이 띄운다.
		const int32 Volley = bFlatVolley ? QFlatVolley : UE_ARRAY_COUNT(QVolleyLaunch);
		const uint32 Generation = CastGeneration;
		const auto Switch = [this, Generation](UAnimSequence* Next)
		{
			return FTimerDelegate::CreateWeakLambda(this, [this, Generation, Next]()
			{
				if (bCasting && Generation == CastGeneration)
				{
					PlayFullBody(Next);
				}
			});
		};
		Timers.SetTimer(AddReleaseTimer(), Switch(CrossFirstAnimation), QVolleySwitchFirst, false);
		if (!bFlatVolley)
		{
			Timers.SetTimer(AddReleaseTimer(), Switch(CrossSecondAnimation), QVolleySwitchSecond, false);
		}
		for (int32 Index = 1; Index < Volley; ++Index)
		{
			Timers.SetTimer(AddReleaseTimer(), FTimerDelegate::CreateUObject(this, &UAuroraSkillComponent::LaunchIceWave, Generation, Index),
				QVolleyLaunch[Index], false);
		}
		OnQAddCast();
	}
	return true;
}

void UAuroraSkillComponent::PrepareCast(EAuroraSkill Skill, const FVector& Aim)
{
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
	bCrossCast = false;
	bCrossQueued = false;
	CrossWindowEnds = 0.0;
	bSavedOrientRotation = Character->GetCharacterMovement()->bOrientRotationToMovement;
	Character->GetCharacterMovement()->bOrientRotationToMovement = false;
}

void UAuroraSkillComponent::StartCooldown(EAuroraSkill Skill)
{
	CooldownEnds.Add(Skill, GetWorld()->GetTimeSeconds() + Skills[Skill].Cooldown);
}

void UAuroraSkillComponent::ExecuteAction(uint32 Generation)
{
	if (!bCasting || Generation != CastGeneration || !Character.IsValid())
	{
		return;
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_SKILL action=%s"), *Skills[ActiveSkill].Name.ToString());
	switch (ActiveSkill)
	{
	case EAuroraSkill::Hoarfrost:
		ExecuteHoarfrost();
		break;
	case EAuroraSkill::GlacialCharge:
		ExecuteGlacialCharge();
		break;
	case EAuroraSkill::FrozenSimulacrum:
		ExecuteLeap();
		break;
	case EAuroraSkill::Cryoseism:
		ExecuteCryoseism();
		break;
	case EAuroraSkill::FrostSlash:
		ExecuteFrostSlash();
		break;
	case EAuroraSkill::FrostField:
		ExecuteFrostField();
		break;
	case EAuroraSkill::IceArmor:
		ExecuteIceArmor();
		break;
	case EAuroraSkill::FrostHaste:
		ExecuteFrostHaste();
		break;
	case EAuroraSkill::Blizzard:
		ExecuteBlizzard();
		break;
	case EAuroraSkill::IceLance:
		ExecuteIceLance();
		break;
	}
}

void UAuroraSkillComponent::ExecuteFrostHaste()
{
	// 발밑에 흰색과 얼음색이 섞인 서리 장판(바닥 데칼 M_Aurora_FrostFloor, 가장자리에 얇은 밝은 고리)을 깔고, 안에 있는 동안
	// 평타·이동이 빨라진다. 10-18 밤 「오브젝트 빼고 바닥만」으로 하얀 빛(Passive_Attack)과 둘레 눈꽃 결정 12개를 뺐다.
	HasteCenter = GetFeetLocation();
	HasteEndsAt = GetWorld()->GetTimeSeconds() + HasteSeconds;
	for (const TWeakObjectPtr<UDecalComponent>& Old : {HasteFloor, HasteRim})
	{
		if (UDecalComponent* Decal = Old.Get())
		{
			Decal->DestroyComponent();
		}
	}
	// 시안(Aurora.FX.SStyle, 10-19 「너무 깔끔해 게임풍과 안 어울린다」): 0 깔끔한 선(그 전) · 1 선이 서리 무늬로 닳음 ·
	// 2 닳은 선 + 마법진 안에 서리 낀 바닥 · 3 = 2 + 장판 안에서 서리 반짝임이 계속 피어오름 · 6·7 = 3 + 고리가 깨짐(아래)
	const int32 Style = CVarAuroraHasteStyle.GetValueOnGameThread();
	// 87차 S 새 방향 1(Aurora.FX.SPolish 1): 흰 선 마법진 대신 은은한 둥근 서리 바닥(Q 자국과 같은 M_Aurora_FrostFloor)
	const int32 SLook = GetSPolish();
	// 94차 「바닥에 깔리는 거 시안 여러 개 · 아예 없애고 머리 위 얼음 왕관 버프기로」: 3 왕관만(바닥 없음) · 4 왕관 + 은은한 서리 바닥 ·
	// 5 금 가는 바닥 · 6 바닥 없이 시전 때 서리 충격파 둘만 — 왕관은 SetHasteAura
	if (SLook == 3 || SLook == 6)
	{
		if (SLook == 6)
		{
			UMaterialInterface* Ring = NovaRingRoughMaterial.LoadSynchronous();
			SpawnFrostNova(HasteCenter, HasteRadius * 0.7f, 2, 0.5f, Ring ? Ring : NovaRingMaterial.LoadSynchronous());
		}
	}
	else if (SLook == 1 || SLook == 4)
	{
		// 91차 촬영(aurora-91st-as): 재질 기본값(채움 0.42 · 무늬 3배)은 반경 900을 통째로 하얗게 덮었다 → 채움을 옅게, 무늬를 잘게,
		// 가장자리 고리는 조금 세게
		// 93차 「이건 너무 밝잖아. 투명도 좀 많이 올려봐」: 채움 0.18 → 0.04 · 밝기 0.4 → 0.2 · 고리 0.75 → 0.12
		// (첫 촬영 aurora-93rd-final에서 1/3로는 테두리 흰 고리가 아직 밝았다)
		UMaterialInterface* Frost = FrostTrailMaterial.LoadSynchronous();
		UMaterialInstanceDynamic* Soft = Frost ? UMaterialInstanceDynamic::Create(Frost, this) : nullptr;
		if (Soft)
		{
			Soft->SetScalarParameterValue(TEXT("FillOpacity"), 0.04f);
			Soft->SetScalarParameterValue(TEXT("PatternFloor"), 0.1f);
			Soft->SetScalarParameterValue(TEXT("PatternTiling"), 9.0f);
			Soft->SetScalarParameterValue(TEXT("Brightness"), 0.2f);
			Soft->SetScalarParameterValue(TEXT("RingOpacity"), 0.12f);
		}
		HasteFloor = SpawnFloorDecal(Soft ? Soft : Frost, HasteCenter, HasteRadius, HasteSeconds, HasteFloorFadeIn, HasteFloorFadeOut);
	}
	else if (Style == 4 || Style == 5 || SLook == 5)
	{
		// 여전사풍(10-19 저녁): 발밑에서 바깥으로 굵은 얼음 균열이 갈라져 나가고(그림 B = 가운데에서 잰 거리) 둘레는 깨진 얼음 테두리.
		// 5는 균열이 눈송이 짜임(여섯 팔 + 가지). 갈라지는 순간 발밑에서 얼음 덩어리가 튄다.
		UMaterialInterface* Cracks = Style == 5 ? HasteFlakeCrackMaterial.LoadSynchronous() : HasteCrackMaterial.LoadSynchronous();
		HasteFloor = SweepFloorDecal(Cracks, HasteCenter, Character->GetActorForwardVector(), HasteRadius,
			HasteSeconds, HasteCrackSweepSeconds, -1.0f, HasteFloorFadeOut);
		SpawnBurstLater(IceShards, HasteCenter, HasteCrackChunkScale, 0.0f);
	}
	else
	{
		// 거친 시안(Aurora.FX.SRough) 4·8은 갉음 값이 더 있는 거친 장판 재질(없으면 그 전 재질)
		const int32 Rough = CVarAuroraHasteRough.GetValueOnGameThread();
		UMaterialInterface* Floor = (Rough & (4 | 8)) ? HasteFloorRoughMaterial.LoadSynchronous() : nullptr;
		if (!Floor)
		{
			Floor = HasteFloorMaterial.LoadSynchronous();
		}
		if (Floor && Style != 0)
		{
			UMaterialInstanceDynamic* Dynamic = UMaterialInstanceDynamic::Create(Floor, this);
			Dynamic->SetScalarParameterValue(TEXT("Grit"), HasteGrit);
			Dynamic->SetScalarParameterValue(TEXT("FrostFill"), Style >= 2 ? HasteFrostFill : 0.0f);
			// 10-20 「바깥 고리부터 그려지듯 나타나게」(S 아쉬운 까닭 넷째 — 깔린 뒤 내내 움직임 없는 그림): 바깥에서 안쪽으로
			// HasteRevealSeconds 동안 드러난다(재질 Reveal, 가운데에서 잰 거리 순서).
			Dynamic->SetScalarParameterValue(TEXT("Reveal"), 0.0f);
			RampReveal(Dynamic, HasteRevealSeconds, 16);
			// 10-20 밤 「라」(헤더 HasteSpinOuter 설명): 바깥 띠·안쪽 무늬가 반대로 돌고(원 밖은 지움) · 2초마다 오르내리고 · 선이 푸른
			// 얼음빛 · 시안보다 옅게. 깔리는 순간 번쩍(빛 배율 HasteFlash를 차례로 내림 — 재질이 불투명도도 같이 올린다).
			Dynamic->SetScalarParameterValue(TEXT("SpinOuter"), HasteSpinOuter);
			Dynamic->SetScalarParameterValue(TEXT("SpinInner"), HasteSpinInner);
			Dynamic->SetScalarParameterValue(TEXT("CircleMask"), 1.0f);
			Dynamic->SetScalarParameterValue(TEXT("PulseStrength"), HastePulseStrength);
			Dynamic->SetVectorParameterValue(TEXT("IceColour"), HasteIceColour);
			Dynamic->SetVectorParameterValue(TEXT("WhiteColour"), HasteWhiteColour);
			Dynamic->SetScalarParameterValue(TEXT("LineOpacity"), HasteLineOpacity);
			Dynamic->SetScalarParameterValue(TEXT("HaloOpacity"), HasteHaloOpacity);
			Dynamic->SetScalarParameterValue(TEXT("GlintStrength"), HasteGlintStrength);
			// 거친 시안(Aurora.FX.SRough, 헤더 HasteRoughGrit · HasteFineGrit 설명): 1 크게 흔들고 갉고 끊은 그림 · 2 서리 무늬가 선을 굵게 갉음 ·
			// 4 잔 서리 무늬로 한 겹 더 갉음 · 8 갉힌 경계를 칼로 끊듯 · 16 갉혀 나간 조각을 크게
			if (Rough & 1)
			{
				if (UTexture* Picture = SnowCircleRoughTexture.LoadSynchronous())
				{
					Dynamic->SetTextureParameterValue(TEXT("FlakeTexture"), Picture);
				}
			}
			// 가운데 큰 눈꽃 없음(Aurora.FX.SInner 0) — 거친 그림(SRough 1)보다 먼저
			if (CVarAuroraHasteInner.GetValueOnGameThread() == 0)
			{
				if (UTexture* Picture = SnowCircleRingTexture.LoadSynchronous())
				{
					Dynamic->SetTextureParameterValue(TEXT("FlakeTexture"), Picture);
				}
			}
			if (Rough & 2)
			{
				Dynamic->SetScalarParameterValue(TEXT("Grit"), HasteRoughGrit);
				Dynamic->SetScalarParameterValue(TEXT("GritTiling"), HasteRoughGritTiling);
			}
			if (Rough & 4)
			{
				Dynamic->SetScalarParameterValue(TEXT("GritFine"), HasteFineGrit);
				Dynamic->SetScalarParameterValue(TEXT("GritFineTiling"), HasteFineGritTiling);
			}
			if (Rough & 8)
			{
				Dynamic->SetScalarParameterValue(TEXT("Grit"), HasteHardGrit);
				Dynamic->SetScalarParameterValue(TEXT("GritCut"), HasteHardGritCut);
				Dynamic->SetScalarParameterValue(TEXT("GritGain"), HasteHardGritGain);
			}
			if (Rough & 16)
			{
				Dynamic->SetScalarParameterValue(TEXT("GritTiling"), HasteBigChunkTiling);
			}
			Dynamic->SetScalarParameterValue(TEXT("GlowBoost"), HasteFlash[0]);
			const TWeakObjectPtr<UMaterialInstanceDynamic> Weak = Dynamic;
			for (int32 Step = 1; Step < UE_ARRAY_COUNT(HasteFlash); ++Step)
			{
				const float Boost = HasteFlash[Step];
				GetWorld()->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, [Weak, Boost]()
				{
					if (UMaterialInstanceDynamic* Instance = Weak.Get())
					{
						Instance->SetScalarParameterValue(TEXT("GlowBoost"), Boost);
					}
				}), HasteFlashStep * Step, false);
			}
			Floor = Dynamic;
		}
		HasteFloor = SpawnFloorDecal(Floor, HasteCenter, HasteRadius, HasteSeconds, HasteFloorFadeIn, HasteFloorFadeOut);
	}
	if (const float Light = CVarAuroraHasteLight.GetValueOnGameThread(); Light > 0.0f)
	{
		SpawnHasteLight(Light);
	}
	// 10-26 「얼음 결계 — 원 바깥선에 얼음이 박히는 아이디어를 S 마법진에」(Aurora.FX.SIce, AuroraSkillComponentDFresh.cpp).
	// 87차 S 새 방향(SPolish 1·2)은 「바닥에 깔리는 얼음 오브젝트 남발 금지」로 뺀다 — 대신 시전 순간 몸에서 냉기가 터진다
	if (SLook == 0)
	{
		HasteRimIce(HasteCenter, Character->GetActorForwardVector().GetSafeNormal2D());
	}
	else if (Character->GetMesh())
	{
		UGameplayStatics::SpawnEmitterAttached(IceChargeGlow, Character->GetMesh(), NAME_None);
	}
	if (Style == 6 || Style == 7)
	{
		// 10-19 밤 「기존 원에 깨진 듯한 이펙트」: 3의 두 고리 자리 금(그림 B = 앞에서 잰 각도)이 앞에서부터 양옆으로 깨져 나가 뒤에서
		// 만나고, 장판과 같이 남았다 사라진다. 6 = 가늘게 빛나는 금 · 7 = 굵게 파인 금 + 고리 둘레에서 얼음 조각이 차례로 튐.
		const FVector Forward = Character->GetActorForwardVector().GetSafeNormal2D();
		HasteRim = SweepFloorDecal(Style == 6 ? HasteRimCrackMaterial.LoadSynchronous() : HasteRimShatterMaterial.LoadSynchronous(), HasteCenter,
			Forward, HasteRadius, HasteSeconds, HasteRimSweepSeconds, -1.0f, HasteFloorFadeOut);
		if (UDecalComponent* Rim = HasteRim.Get())
		{
			// 장판 위에 그린다
			Rim->SetSortOrder(1);
		}
		if (Style == 7)
		{
			for (int32 Index = 0; Index < HasteRimChunkCount; ++Index)
			{
				// 앞에서 잰 각도만큼 늦게(깨짐이 그 자리를 지날 때) 고리(반경 0.95) 위에서 튄다
				const float Angle = (Index + 0.5f) / HasteRimChunkCount * 360.0f - 180.0f;
				const FVector Spot = HasteCenter + Forward.RotateAngleAxis(Angle, FVector::UpVector) * HasteRadius * 0.95f;
				SpawnBurstLater(IceShards, Spot, HasteRimChunkScale, HasteRimSweepSeconds * FMath::Abs(Angle) / 180.0f / 1.1f);
			}
		}
	}
	if (Style == 3 || Style == 6 || Style == 7)
	{
		const int32 Count = FMath::FloorToInt(HasteSeconds / HasteSparkleInterval);
		for (int32 Index = 0; Index < Count; ++Index)
		{
			const float Angle = FMath::FRandRange(0.0f, 2.0f * PI);
			const float Reach = HasteRadius * 0.85f * FMath::Sqrt(FMath::FRand());
			const FVector Spot = HasteCenter + FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.0f) * Reach;
			// 반짝임 이펙트는 앞(X)으로 뿜으므로 위로 세운다.
			SpawnBurstLater(SlashSparkles, Spot, 0.8f, HasteFloorFadeIn + HasteSparkleInterval * Index,
				FRotator(90.0f, FMath::FRandRange(0.0f, 360.0f), 0.0f));
		}
	}
	SpawnBurstLater(IceShock, HasteCenter, 0.6f, 0.0f);
	GetWorld()->GetTimerManager().SetTimer(HasteTimer, this, &UAuroraSkillComponent::FrostHasteTick, HasteCheckInterval, true);
	FrostHasteTick();
	UE_LOG(LogTemp, Display, TEXT("AURORA_HASTE start at=%s radius=%.0f"), *HasteCenter.ToCompactString(), HasteRadius);
}

void UAuroraSkillComponent::FrostHasteTick()
{
	if (!GetWorld() || !Character.IsValid())
	{
		return;
	}
	if (GetWorld()->GetTimeSeconds() >= HasteEndsAt)
	{
		GetWorld()->GetTimerManager().ClearTimer(HasteTimer);
		SetHaste(false);
		UE_LOG(LogTemp, Display, TEXT("AURORA_HASTE end"));
		return;
	}
	// 장판 안(반경 + 몸 반지름)에 서 있을 때만 빨라진다. 지금은 자신만(파티원·아군이 수련장에 없다).
	SetHaste(FVector::Dist2D(Character->GetActorLocation(), HasteCenter) <= HasteRadius + Character->GetSimpleCollisionRadius());
}

void UAuroraSkillComponent::SetHaste(bool bOn)
{
	if (bOn == bHasteApplied || !Character.IsValid())
	{
		return;
	}
	bHasteApplied = bOn;
	if (AAuroraCharacter* Aurora = Cast<AAuroraCharacter>(Character.Get()))
	{
		Aurora->SetSpeedScale(bOn ? HasteScale : 1.0f, bOn ? HasteScale : 1.0f);
	}
	// 87차 S 새 방향: 빨라진 동안 몸 오라(SPolish 0이면 아무것도 안 함)
	SetHasteAura(bOn);
	UE_LOG(LogTemp, Display, TEXT("AURORA_HASTE %s walk=%.0f"), bOn ? TEXT("on") : TEXT("off"),
		Character->GetCharacterMovement() ? Character->GetCharacterMovement()->MaxWalkSpeed : 0.0f);
}

void UAuroraSkillComponent::SpawnHasteLight(float Intensity)
{
	if (!Character.IsValid() || !GetWorld())
	{
		return;
	}
	if (UPointLightComponent* Old = HasteLight.Get())
	{
		Old->DestroyComponent();
	}
	// 캐릭터 것이지만 붙이지 않아 장판 자리에 머문다. 장판과 같이 들어오고(HasteFloorFadeIn) 같이 사라진다(HasteFloorFadeOut).
	UPointLightComponent* Light = NewObject<UPointLightComponent>(Character.Get());
	Light->SetMobility(EComponentMobility::Movable);
	Light->RegisterComponent();
	Light->SetWorldLocation(HasteCenter + FVector(0.0f, 0.0f, HasteLightHeight));
	Light->SetIntensityUnits(ELightUnits::Candelas);
	Light->SetIntensity(0.0f);
	Light->SetLightColor(HasteLightColour);
	Light->SetAttenuationRadius(HasteRadius * HasteLightReach);
	Light->SetCastShadows(false);
	HasteLight = Light;
	const TWeakObjectPtr<UPointLightComponent> Weak = Light;
	constexpr int32 Steps = 8;
	for (int32 Step = 1; Step <= Steps; ++Step)
	{
		const float In = Intensity * Step / Steps;
		const float Out = Intensity * (Steps - Step) / Steps;
		GetWorld()->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, [Weak, In]()
		{
			if (Weak.IsValid())
			{
				Weak->SetIntensity(In);
			}
		}), HasteFloorFadeIn * Step / Steps, false);
		const bool bLast = Step == Steps;
		GetWorld()->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, [Weak, Out, bLast]()
		{
			if (!Weak.IsValid())
			{
				return;
			}
			Weak->SetIntensity(Out);
			if (bLast)
			{
				Weak->DestroyComponent();
			}
		}), HasteSeconds - HasteFloorFadeOut + HasteFloorFadeOut * Step / Steps, false);
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_HASTE light=%.0f"), Intensity);
}

void UAuroraSkillComponent::ExecuteIceSpikes()
{
	// 칼끝이 바닥에 닿는 순간 몸이 멈칫한다(10-20 「이렇게 해 봐」). 바닥 터짐은 그대로 나간다.
	BeginHitStop(nullptr, SpikePlantHitStopSeconds);
	// 꽂은 뒤엔 제 빠르기로 무릎을 꿇으며 얼음 줄이 솟는 동안 버틴다(「꽂고 나서 좀 더 기다리는 듯한 느낌」).
	USkeletalMeshComponent* Body = Character->GetMesh();
	if (UAnimInstance* Anim = Body ? Body->GetAnimInstance() : nullptr; Anim && ActiveMontage)
	{
		Anim->Montage_SetPlayRate(ActiveMontage, SpikePlantHoldRate);
	}
	// 고드름 비(Aurora.FX.DRain, 헤더 GetDRain 설명)면 한 줄 대신 겨눈 자리에 하늘에서
	if (GetDRain() != 0)
	{
		ExecuteIcicleRain();
		return;
	}
	// 앞으로 얼음 조각이 차례로 솟는다. 벽(고정 물체)에서 줄이 끊긴다.
	SpikeDirection = (ActiveAim - Character->GetActorLocation()).GetSafeNormal2D();
	if (SpikeDirection.IsNearlyZero())
	{
		SpikeDirection = Character->GetActorForwardVector().GetSafeNormal2D();
	}
	SpikeOrigin = GetFeetLocation();
	SpikeLength = SpikeLineLength;
	FCollisionQueryParams Query(SCENE_QUERY_STAT(AuroraSpikes), false, Character.Get());
	FHitResult Wall;
	const FVector Waist = Character->GetActorLocation();
	if (GetWorld()->SweepSingleByObjectType(Wall, Waist, Waist + SpikeDirection * SpikeLength, FQuat::Identity,
		FCollisionObjectQueryParams(ECC_WorldStatic), FCollisionShape::MakeSphere(40.0f), Query))
	{
		SpikeLength = Wall.Distance;
	}
	SpikeIndex = 0;
	SpikeHits.Reset();
	SpikeStyle = CVarAuroraSpikeStyle.GetValueOnGameThread();
	if ((SpikeStyle == 2 || SpikeStyle == 3) && SpikeLength > 1.0f)
	{
		// 시안 2·3: 줄 길이만 한 정사각형 데칼(그림 아래 = 발밑, 위 = 줄 끝)이 바위가 터져 나가는 빠르기로 앞쪽까지 갈라져 드러난다
		// (그림 B가 1.1에 닿는 시간 = 줄 길이 × 바위 간격 시간 / 바위 사이 거리 × 1.1).
		const float Sweep = SpikeLength * SpikeInterval / SpikeSpacing * 1.1f;
		SweepFloorDecal(RuptureCrackMaterial.LoadSynchronous(), SpikeOrigin + SpikeDirection * SpikeLength * 0.5f, SpikeDirection,
			SpikeLength * 0.5f, RuptureCrackSeconds, Sweep, -1.0f, RuptureCrackFadeOut);
	}
	IceSpikeStep();
	GetWorld()->GetTimerManager().SetTimer(SpikeTimer, this, &UAuroraSkillComponent::IceSpikeStep, SpikeInterval, true);
}

void UAuroraSkillComponent::IceSpikeStep()
{
	if (!GetWorld())
	{
		return;
	}
	const float Along = SpikeStart + SpikeSpacing * SpikeIndex;
	if (SpikeIndex >= SpikeCount || Along > SpikeLength)
	{
		GetWorld()->GetTimerManager().ClearTimer(SpikeTimer);
		// 줄 끝에서 한 번 더 터뜨린다.
		const FVector End = SpikeOrigin + SpikeDirection * FMath::Min(SpikeStart + SpikeSpacing * (SpikeIndex - 1) + 60.0f, SpikeLength);
		if (SpikeIndex > 0)
		{
			// 끝에서 파란 충격파로 마무리한다.
			SpawnBurstLater(IceShock, End, 0.8f, 0.0f);
		}
		UE_LOG(LogTemp, Display, TEXT("AURORA_SPIKES end segments=%d length=%.0f hits=%d"), SpikeIndex, SpikeLength, SpikeHits.Num());
		return;
	}
	const FVector Spot = SpikeOrigin + SpikeDirection * Along;
	// 얼음 바위가 바닥에서 터져 오른다(Rampage 얼음판 Ice_Rock_HitWorld). Q·W 파편보다 조금 크게(0.55).
	SpawnBurstLater(IceShards, Spot, 0.55f, 0.0f, SpikeDirection.Rotation());
	if (SpikeStyle == 1 || SpikeStyle == 3)
	{
		SpawnRuptureSpikes(Spot, SpikeDirection);
	}
	TArray<AActor*> Targets;
	GatherTargets(Spot, SpikeHitRadius, Targets);
	AController* Instigator = Character.IsValid() ? Character->GetController() : nullptr;
	for (AActor* Target : Targets)
	{
		if (SpikeHits.Contains(Target))
		{
			continue;
		}
		SpikeHits.Add(Target);
		if (Target->CanBeDamaged())
		{
			FHitResult Hit(Target, nullptr, Target->GetActorLocation(), SpikeDirection);
			UGameplayStatics::ApplyPointDamage(Target, SpikeLineDamage, SpikeDirection, Hit, Instigator, GetOwner(), nullptr);
		}
		SetStatus(Target, TEXT("SLOW"), SpikeSlowSeconds);
	}
	++SpikeIndex;
}

void UAuroraSkillComponent::ExecuteIceLance()
{
	// F 얼음 덩어리 일제 사격(Aurora.FX.FShot 1)이면 그쪽이 맡는다
	if (ExecuteChunkVolley())
	{
		return;
	}
	FVector Aim = (ActiveAim - Character->GetActorLocation()).GetSafeNormal2D();
	if (Aim.IsNearlyZero())
	{
		Aim = Character->GetActorForwardVector().GetSafeNormal2D();
	}
	// 앞서 던진 창이 아직 날고 있으면(쿨타임 무시 시험) 그 자리에서 부순다.
	for (int32 Index = Lances.Num() - 1; Index >= 0; --Index)
	{
		const UStaticMeshComponent* Old = Lances[Index].Mesh.Get();
		StopIceLance(Index, nullptr, Old ? Old->GetComponentLocation() : Character->GetActorLocation());
	}
	LanceHitTargets.Reset();
	// 몸 중심 높이에서 수평으로 던진다. 10-18 밤 「뾰족한 검 모양」으로 바꿨다: 엔진 원뿔을 얇고 납작하게 늘려 꼭짓점(+Z)을 나는 쪽,
	// 넓은 면(X)을 옆으로 눕혀 위에서 보면 끝이 뾰족한 얼음 칼날로 보이게 하고, 얼음 분신 석상과 같은 재질을 입힌다.
	// 전엔 분신 파편(Frag_05)을 키워 썼는데 휘어진 조각이라 「뭐 날리는 것 같다」였다.
	// 10-19 「세 방향으로 쏘는 거」: 겨눈 방향을 가운데로 LanceSpreadDegrees씩 벌려 LanceCount개를 같이 던진다.
	const FVector Extent = BladeMesh ? BladeMesh->GetBounds().BoxExtent : FVector(50.0f);
	const FVector Scale(LanceBladeWidth / FMath::Max(2.0f * Extent.X, 1.0f), LanceBladeThickness / FMath::Max(2.0f * Extent.Y, 1.0f),
		LanceBladeLength / FMath::Max(2.0f * Extent.Z, 1.0f));
	// 분신 돌격(Aurora.FX.FClone, 헤더 LanceClonePoseFrom 설명): 칼날은 숨겨 나는 길·맞힘 판정만 쓰고 그 아래 바닥을 얼음 분신이 돌진한다
	// 얼음 새 시안(Aurora.FX.FBird, 헤더 LanceBirdHeight 설명)이 0이 아니면 분신 대신 새가 난다
	const bool bBirds = GetFBird() != 0;
	const bool bClones = CVarAuroraLanceClone.GetValueOnGameThread() != 0 && !bBirds;
	// 새는 한 마리만 겨눈 쪽으로 곧게(10-25 「매 한 마리만 일직선으로 날아가서 펑 터지는」)
	const int32 Count = bBirds ? 1 : LanceCount;
	// 매 퀄리티 시안 4(Aurora.FX.FLook): 매가 느리게 난다 — 수명·한 장면 걸음도 같이
	LanceSpeedScale = bBirds && (GetFLook() & 4) ? LanceBirdSlowRate : 1.0f;
	for (int32 Index = 0; Index < Count; ++Index)
	{
		FAuroraLance Lance;
		Lance.Direction = Aim.RotateAngleAxis((Index - (Count - 1) * 0.5f) * LanceSpreadDegrees, FVector::UpVector);
		const FVector Origin = Character->GetActorLocation() + Lance.Direction * (LanceTailAhead + LanceBladeLength * 0.5f) + FVector(0.0f, 0.0f, 10.0f);
		const FVector Right(-Lance.Direction.Y, Lance.Direction.X, 0.0f);
		const FRotator Facing = FRotationMatrix::MakeFromZX(Lance.Direction, Right).Rotator();
		UStaticMeshComponent* Mesh = SpawnTimedMesh(BladeMesh, FTransform(Facing, Origin, Scale),
			Skills[EAuroraSkill::IceLance].Range / (LanceSpeed * LanceSpeedScale) + 1.0f);
		if (!Mesh)
		{
			continue;
		}
		if (BladeMaterial)
		{
			Mesh->SetMaterial(0, BladeMaterial);
		}
		if (LanceTrail)
		{
			if (UParticleSystemComponent* Trail = UGameplayStatics::SpawnEmitterAttached(LanceTrail, Mesh, NAME_None,
				FVector::ZeroVector, FRotator::ZeroRotator, EAttachLocation::KeepRelativeOffset, false))
			{
				OwnedEffects.Add(Trail);
				Lance.Trail = Trail;
			}
		}
		Lance.Mesh = Mesh;
		LanceFloorZ = GetFeetLocation().Z;
		if (bClones)
		{
			Mesh->SetVisibility(false);
			Lance.Clone = SpawnLanceClone(Lance.Direction, Origin);
		}
		else if (bBirds)
		{
			Mesh->SetVisibility(false);
			SpawnLanceBird(Lance, Origin, Index);
		}
		Lances.Add(Lance);
	}
	LanceStyle = CVarAuroraLanceStyle.GetValueOnGameThread();
	LanceFlight = CVarAuroraLanceFlight.GetValueOnGameThread();
	// 매 나는 쪽 이펙트 시안 8(Aurora.FX.FTrail): 창 꼬리 시안 1(얼음 부스러기)을 매에도
	if (bBirds && (GetFTrail() & 8))
	{
		LanceFlight |= 1;
	}
	for (FAuroraLance& Lance : Lances)
	{
		Lance.NextTrail = Lance.NextShed = GetWorld()->GetTimeSeconds();
	}
	if (LanceStyle == 1 || LanceStyle == 3)
	{
		// 시안 1·3: 칼날마다 아래 바닥에 흰 서리 줄이 칼날이 나는 빠르기로 앞쪽까지 드러난다. 길이는 날아가다 멈출 자리를 던질 때
		// 미리 쓸어 정한다(IceLanceTick과 같은 대상·반경).
		FCollisionObjectQueryParams Objects;
		Objects.AddObjectTypesToQuery(ECC_Pawn);
		Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
		Objects.AddObjectTypesToQuery(ECC_WorldStatic);
		FCollisionQueryParams Query(SCENE_QUERY_STAT(AuroraLanceStreak), false, Character.Get());
		const FVector Feet = GetFeetLocation();
		for (const FAuroraLance& Lance : Lances)
		{
			const UStaticMeshComponent* Mesh = Lance.Mesh.Get();
			if (!Mesh)
			{
				continue;
			}
			const FVector From = Mesh->GetComponentLocation();
			float Length = Skills[EAuroraSkill::IceLance].Range;
			FHitResult Hit;
			if (GetWorld()->SweepSingleByObjectType(Hit, From, From + Lance.Direction * Length, FQuat::Identity, Objects,
				FCollisionShape::MakeSphere(LanceHitRadius), Query))
			{
				Length = Hit.Distance;
			}
			const FVector Start(From.X, From.Y, Feet.Z);
			SweepFloorDecal(DashStreakMaterial.LoadSynchronous(), Start + Lance.Direction * Length * 0.5f, Lance.Direction,
				Length * 0.5f + DashStreakMargin, LanceStreakSeconds, FMath::Max(Length / LanceSpeed, 0.05f), LanceStreakHalfWidth);
		}
	}
	// 던지는 순간 칼날이 떠나는 캐릭터 앞에 이펙트(Aurora.FX.FHand, 10-19 「F 쏠 때 캐릭터 쪽에 뭔가 이펙트」)
	const FVector Release = Character->GetActorLocation() + Aim * 70.0f + FVector(0.0f, 0.0f, 10.0f);
	const int32 Hand = CVarAuroraLanceHand.GetValueOnGameThread();
	switch (Hand)
	{
	case 0:
		break;
	case 2:
		SpawnBurstLater(IceChunks, Release, 0.4f, 0.0f, Aim.Rotation());
		break;
	case 3:
		SpawnBurstLater(IceFrostPuff, Release, 0.7f, 0.0f);
		break;
	default:
		SpawnBurstLater(LanceFlash, Release, 1.2f, 0.0f, Aim.Rotation());
		break;
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_LANCE blade count=%d spread=%.0f hand=%d extent=%s scale=%s material=%s"), Lances.Num(),
		LanceSpreadDegrees, Hand, *Extent.ToCompactString(), *Scale.ToCompactString(), *GetNameSafe(BladeMaterial));
	GetWorld()->GetTimerManager().SetTimer(LanceTimer, this, &UAuroraSkillComponent::IceLanceTick, 1.0f / 60.0f, true);
}

void UAuroraSkillComponent::IceLanceTick()
{
	if (!GetWorld())
	{
		return;
	}
	const float Step = LanceSpeed * LanceSpeedScale / 60.0f;
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_Pawn);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	Objects.AddObjectTypesToQuery(ECC_WorldStatic);
	FCollisionQueryParams Query(SCENE_QUERY_STAT(AuroraLance), false, Character.Get());
	// 뒤에서부터 돈다(멈춘 창은 배열에서 빠진다).
	for (int32 Index = Lances.Num() - 1; Index >= 0; --Index)
	{
		UStaticMeshComponent* Mesh = Lances[Index].Mesh.Get();
		if (!IsValid(Mesh))
		{
			ReleaseOwnedEffect(Lances[Index].Trail.Get());
			if (USkeletalMeshComponent* Clone = Lances[Index].Clone.Get())
			{
				Clone->DestroyComponent();
			}
			EndLanceBird(Lances[Index], false);
			Lances.RemoveAt(Index);
			continue;
		}
		const FVector From = Mesh->GetComponentLocation();
		const FVector To = From + Lances[Index].Direction * Step;
		FHitResult Hit;
		if (GetWorld()->SweepSingleByObjectType(Hit, From, To, FQuat::Identity, Objects, FCollisionShape::MakeSphere(LanceHitRadius), Query))
		{
			AActor* Target = Hit.GetActor();
			StopIceLance(Index, IsCombatTarget(Target, GetOwner()) ? Target : nullptr, Hit.Location);
			continue;
		}
		Mesh->SetWorldLocation(To);
		if (USkeletalMeshComponent* Clone = Lances[Index].Clone.Get())
		{
			Clone->SetWorldLocation(FVector(To.X, To.Y, LanceFloorZ));
			// W가 닿은 자세(칼을 앞으로 뻗은 채)에서 멈춰 미끄러져 간다
			UAnimSingleNodeInstance* Pose = Clone->GetSingleNodeInstance();
			if (Pose && Pose->IsPlaying() && Pose->GetCurrentTime() >= LanceClonePoseHold)
			{
				Pose->SetPosition(LanceClonePoseHold, false);
				Pose->SetPlaying(false);
			}
		}
		Lances[Index].Travel += Step;
		const double Now = GetWorld()->GetTimeSeconds();
		LanceBirdTick(Lances[Index], To, Now);
		if (LanceFlight != 0)
		{
			TrailLance(Lances[Index], Mesh, Now);
		}
		if (Lances[Index].Travel >= Skills[EAuroraSkill::IceLance].Range)
		{
			StopIceLance(Index, nullptr, To);
		}
	}
	// 시안 2 잔상: 두께는 끝까지, 길이는 절반까지 줄어들며 사라진다(창이 멈춘 뒤에도 마저 줄어든다).
	const double Now = GetWorld()->GetTimeSeconds();
	for (int32 Index = LanceGhosts.Num() - 1; Index >= 0; --Index)
	{
		const FAuroraLanceGhost& Ghost = LanceGhosts[Index];
		UStaticMeshComponent* Mesh = Ghost.Mesh.Get();
		const float Age = static_cast<float>(Now - Ghost.Born) / (Ghost.Seconds > 0.0f ? Ghost.Seconds : LanceGhostSeconds);
		if (!IsValid(Mesh) || Age >= 1.0f)
		{
			if (IsValid(Mesh))
			{
				RemoveTimedMesh(Mesh, nullptr);
			}
			LanceGhosts.RemoveAtSwap(Index);
			continue;
		}
		Mesh->SetWorldScale3D(Ghost.Scale * FVector(1.0f - Age, 1.0f - Age, 1.0f - 0.5f * Age).ComponentMax(FVector(0.001f)));
	}
	if (Lances.IsEmpty() && LanceGhosts.IsEmpty())
	{
		GetWorld()->GetTimerManager().ClearTimer(LanceTimer);
	}
}

void UAuroraSkillComponent::TrailLance(FAuroraLance& Lance, const UStaticMeshComponent* Mesh, double Now)
{
	// 창 꼬리(나는 쪽 반대 끝)
	const FVector Tail = Mesh->GetComponentLocation() - Lance.Direction * LanceBladeLength * 0.5f;
	const bool bCrumbs = LanceFlight == 1 || LanceFlight == 3;
	// 분신 돌격은 칼날을 숨겨 칼날 잔상은 남기지 않는다
	const bool bGhosts = (LanceFlight == 2 || LanceFlight == 3) && !Lance.Clone.IsValid() && Lance.Bird == 0;
	if (bCrumbs && Now >= Lance.NextShed)
	{
		// 얼음 부스러기: Q 얼음 검기 날과 같은 방식 — 뒤로 떨어져 바닥에 닿아 미끄러지다 멈춘다(ShardTick).
		Lance.NextShed = Now + LanceShedSeconds;
		for (int32 Bit = 0; Bit < LanceShedCount; ++Bit)
		{
			FAuroraShard Shard;
			Shard.FloorZ = LanceFloorZ + 3.0f;
			Shard.Start = Tail + FMath::VRand() * 6.0f;
			Shard.Velocity = -Lance.Direction * FMath::FRandRange(60.0f, 160.0f) + FMath::VRand() * 60.0f + FVector(0.0f, 0.0f, 40.0f);
			Shard.Born = Now;
			Shard.Life = FMath::FRandRange(0.45f, 0.8f);
			const float Bitsize = FMath::FRandRange(4.0f, 8.0f) * LanceShedSize;
			Shard.Size = FVector(Bitsize, Bitsize * 0.6f, FMath::FRandRange(12.0f, 22.0f) * LanceShedSize);
			AddShard(Shard, Now);
		}
	}
	if (bGhosts && Now >= Lance.NextTrail)
	{
		// 잔상: 지금 자리·자세 그대로 같은 칼날을 하나 남기고 IceLanceTick이 줄여 지운다.
		Lance.NextTrail = Now + LanceGhostInterval;
		UStaticMeshComponent* Ghost = SpawnTimedMesh(BladeMesh, Mesh->GetComponentTransform(), LanceGhostSeconds + 0.1f);
		if (Ghost)
		{
			if (BladeMaterial)
			{
				Ghost->SetMaterial(0, BladeMaterial);
			}
			Ghost->SetCastShadow(false);
			LanceGhosts.Add({Ghost, Now, Mesh->GetComponentScale()});
		}
	}
}

USkeletalMeshComponent* UAuroraSkillComponent::SpawnLanceClone(const FVector& Direction, const FVector& Where)
{
	USkeletalMeshComponent* Body = Character.IsValid() ? Character->GetMesh() : nullptr;
	if (!Body || !GetWorld())
	{
		return nullptr;
	}
	// 붙이지 않은 캐릭터 메시 사본 — 혼자 W 돌진 동작을 틀고(닿는 자세에서 IceLanceTick이 멈춘다), 자리는 IceLanceTick이 숨긴 칼날 아래
	// 바닥으로 옮긴다.
	// 충돌·내비는 메시를 끼우기 전에 끈다(SpawnTimedMesh와 같은 까닭).
	USkeletalMeshComponent* Clone = NewObject<USkeletalMeshComponent>(Character.Get());
	Clone->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Clone->SetCanEverAffectNavigation(false);
	Clone->SetSkeletalMesh(Body->GetSkeletalMeshAsset());
	Clone->SetUsingAbsoluteLocation(true);
	Clone->SetUsingAbsoluteRotation(true);
	Clone->SetUsingAbsoluteScale(true);
	Clone->SetWorldScale3D(Body->GetComponentScale());
	const FVector Feet(Where.X, Where.Y, GetFeetLocation().Z);
	Clone->SetWorldLocationAndRotation(Feet, FRotator(0.0f, Direction.Rotation().Yaw + Body->GetRelativeRotation().Yaw, 0.0f));
	Clone->RegisterComponent();
	if (UMaterialInterface* Ice = CloneIceMaterial.LoadSynchronous())
	{
		for (int32 Slot = 0; Slot < Clone->GetNumMaterials(); ++Slot)
		{
			Clone->SetMaterial(Slot, Ice);
		}
	}
	Clone->SetAnimationMode(EAnimationMode::AnimationSingleNode);
	if (ChargeLungeAnimation)
	{
		Clone->PlayAnimation(ChargeLungeAnimation, false);
		Clone->SetPosition(LanceClonePoseFrom, false);
	}
	// 분신이 생길 때 분신 등장 연기(DecoySpawn)는 셋이 겹쳐 몸을 덮는 흰 구름이 돼 뺐다(10-21 첫 촬영)
	return Clone;
}

void UAuroraSkillComponent::StopIceLance(int32 Index, AActor* HitTarget, const FVector& Where)
{
	const FAuroraLance Lance = Lances[Index];
	Lances.RemoveAt(Index);
	// 잔상(FFlight 2)이 남아 있으면 IceLanceTick이 마저 줄여 지우고 멈춘다.
	if (Lances.IsEmpty() && LanceGhosts.IsEmpty())
	{
		GetWorld()->GetTimerManager().ClearTimer(LanceTimer);
	}
	const FVector LanceDirection = Lance.Direction;
	ReleaseOwnedEffect(Lance.Trail.Get());
	RemoveTimedMesh(Lance.Mesh.Get(), nullptr);
	if (USkeletalMeshComponent* Clone = Lance.Clone.Get())
	{
		// 분신은 그 자리에서 얼음 조각으로 부서진다(터짐 이펙트는 아래 창과 같다)
		SpawnShatterShards(Clone->GetComponentLocation(), 150.0f, LanceCloneShards, 300.0f, 250.0f, 1.2f);
		Clone->DestroyComponent();
	}
	EndLanceBird(Lance, true);
	// 박힌 자리에서 창이 부서지며 얼음 연기가 퍼진다. 같은 대상에 이미 다른 창이 꽂혔으면(가까이서 셋이 한 대상에) 작은 파편만 —
	// 큰 폭발이 세 번 겹쳐 화면을 덮었다(10-19 F 시안 촬영).
	const bool bRepeatHit = IsValid(HitTarget) && LanceHitTargets.Contains(HitTarget);
	if (DecoyExplode)
	{
		UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), DecoyExplode, Where, FRotator::ZeroRotator,
			FVector((bRepeatHit ? 0.5f : 1.0f) * LanceImpactScale));
	}
	if (CryoExplode && !bRepeatHit)
	{
		UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), CryoExplode, Where, FRotator::ZeroRotator, FVector(LanceImpactScale));
	}
	if (PrisonBurstEffect && !bRepeatHit)
	{
		UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), PrisonBurstEffect, Where, FRotator::ZeroRotator, FVector(LanceImpactScale));
	}
	if ((LanceStyle == 2 || LanceStyle == 3) && !bRepeatHit)
	{
		// 시안 2·3: 꽂힌 자리 아래 바닥이 별 모양으로 갈라지고, 얼음 파편이 나던 쪽으로 튀었다 떨어진다.
		const float FloorZ = FindFloorZ(Where, GetFeetLocation().Z);
		if (UDecalComponent* Crack = SweepFloorDecal(LanceImpactCrackMaterial.LoadSynchronous(), FVector(Where.X, Where.Y, FloorZ), LanceDirection,
			LanceCrackRadius * LanceImpactScale, LanceCrackSeconds, LanceCrackSweepSeconds, -1.0f, LanceCrackFadeOut))
		{
			Crack->SetSortOrder(1);
		}
		SpawnImpactShards(Where, LanceDirection, FloorZ);
	}
	if (Lance.Bird != 0)
	{
		// 새는 멈춘 자리에서 펑 — 둘레 피해 반경(LanceSplashRadius)까지 서리 충격파 고리가 퍼진다(10-25 「펑 터지는 느낌」)
		UMaterialInterface* Ring = NovaRingRoughMaterial.LoadSynchronous();
		SpawnFrostNova(FVector(Where.X, Where.Y, FindFloorZ(Where, GetFeetLocation().Z)), LanceSplashRadius, 1, LanceBirdBurstSeconds,
			Ring ? Ring : NovaRingMaterial.LoadSynchronous());
	}
	// 한 번 던진 창 셋 중 먼저 닿은 쪽만 피해를 준다(바로 맞힘이든 둘레 파편이든 대상마다 한 번).
	bool bDamaged = false;
	if (IsValid(HitTarget) && HitTarget->CanBeDamaged() && !LanceHitTargets.Contains(HitTarget))
	{
		LanceHitTargets.Add(HitTarget);
		FHitResult Hit(HitTarget, nullptr, Where, -LanceDirection);
		UGameplayStatics::ApplyPointDamage(HitTarget, Skills[EAuroraSkill::IceLance].Damage, LanceDirection, Hit,
			Character.IsValid() ? Character->GetController() : nullptr, GetOwner(), nullptr);
		bDamaged = true;
	}
	TArray<AActor*> Splashed;
	GatherTargets(Where - FVector(0.0f, 0.0f, 90.0f), LanceSplashRadius, Splashed);
	Splashed.Remove(HitTarget);
	int32 SplashDamaged = 0;
	for (AActor* Other : Splashed)
	{
		if (Other->CanBeDamaged() && !LanceHitTargets.Contains(Other))
		{
			LanceHitTargets.Add(Other);
			FHitResult Hit(Other, nullptr, Other->GetActorLocation(), LanceDirection);
			UGameplayStatics::ApplyPointDamage(Other, LanceSplashDamage, LanceDirection, Hit,
				Character.IsValid() ? Character->GetController() : nullptr, GetOwner(), nullptr);
			++SplashDamaged;
		}
		SetStatus(Other, TEXT("SLOW"), LanceSlowSeconds);
	}
	if (IsValid(HitTarget))
	{
		SetStatus(HitTarget, TEXT("SLOW"), LanceSlowSeconds);
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_LANCE stop target=%s damaged=%d travel=%.0f splash=%d splash_damaged=%d at=%s"),
		*GetNameSafe(HitTarget), bDamaged, Lance.Travel, Splashed.Num(), SplashDamaged, *Where.ToCompactString());
}

void UAuroraSkillComponent::RecordFrozen(AActor* Target, float Seconds)
{
	if (IsValid(Target) && GetWorld())
	{
		FrozenUntil.Add(Target, GetWorld()->GetTimeSeconds() + Seconds);
	}
}

bool UAuroraSkillComponent::IsFrozen(const AActor* Target) const
{
	const double* Until = FrozenUntil.Find(const_cast<AActor*>(Target));
	return Until && GetWorld() && GetWorld()->GetTimeSeconds() < *Until;
}

void UAuroraSkillComponent::ExecuteFrostSlash()
{
	// 칼이 내려오는 순간 앞쪽 부채꼴을 베고, 칼 궤적을 따라 얼음 파편이 왼쪽에서 오른쪽으로 차례로 튄다.
	const FAuroraSkillDefinition& Definition = Skills[EAuroraSkill::FrostSlash];
	FVector Direction = (ActiveAim - Character->GetActorLocation()).GetSafeNormal2D();
	if (Direction.IsNearlyZero())
	{
		Direction = Character->GetActorForwardVector().GetSafeNormal2D();
	}
	const FVector Feet = GetFeetLocation();
	// 87차 Q-2 결정 파열은 한 번 시전에 대상마다 한 번(세 번 베어도 셋이 겹치지 않게)
	QBurstTargets.Reset();
	// 이펙트 시안(Aurora.FX.QStyle, 10-19 「Q 이펙트를 어쩌면 좋을까, 시안 여러 개」). 판정은 시안과 상관없이 아래에서 같다.
	const int32 Style = CVarAuroraSlashStyle.GetValueOnGameThread();
	if (Style == 6)
	{
		// 얼음 검기 세 번의 첫째(둘째·셋째는 BeginCast가 건 예약). 판정은 검기마다 LaunchIceWave가 한다.
		LaunchIceWave(CastGeneration, 0);
		return;
	}
	switch (Style)
	{
	case 5:
		// Q1: 칼에서 떠난 초승달 검기가 앞으로 날아간다. 아래 바닥 서리 줄(W 돌진 자국 그림)은 밝은 곧은 띠가 레이저처럼 보여
		// 뺐다(aurora-41st-qr — F 시안 1 바닥 줄과 같은 까닭).
		SpawnFlyingWave(Feet, Direction);
		break;
	case 1:
	{
		// 초승달 검기: 칼 궤적 모양의 빛이 왼쪽부터 휩쓸며 나타났다 사라진다(10-19 「초승달 검기만 남겨 봐」 — 눈 덮임 자국은 뺐다).
		SweepFloorDecal(SlashArcMaterial.LoadSynchronous(), Feet, Direction, Definition.Range, SlashWaveSeconds, SlashSweepSeconds);
		// 보강(Aurora.FX.QBoost, 10-19 「뭔가 흩날리는 이펙트」): 검기 날에서 작은 눈송이들이 바깥으로 날려 나가 흔들리며 사라진다.
		// 그 전 시안(잔상·서리 바람·날 따라 반짝임)은 「다 별로」로 뺐다.
		switch (CVarAuroraSlashBoost.GetValueOnGameThread())
		{
		case 0:
			break;
		case 1:
			SpawnSlashFlakes(Feet, Direction, Definition.Range, SlashFlakeCount, FVector2D(SlashFlakeMinSize, SlashFlakeMaxSize),
				FVector2D(0.6f, 0.82f), FVector2D(SlashFlakeMinLife, SlashFlakeMaxLife));
			break;
		case 3:
			// 여전사풍(10-19 저녁): 칼이 바닥을 베고 지나간 자국이 검기와 같은 순서로 패이고, 날에서 얼음 파편이 튄다.
			if (UMaterialInterface* Scar = SlashScarMaterial.LoadSynchronous())
			{
				SweepFloorDecal(Scar, Feet, Direction, Definition.Range, SlashScarSeconds, SlashSweepSeconds, -1.0f, SlashScarFadeOut);
			}
			SpawnSlashShards(Feet, Direction, Definition.Range);
			break;
		case 4:
			SpawnSlashShards(Feet, Direction, Definition.Range);
			break;
		default:
			// 2: 초승달 날(그림의 바깥 날 = 반경 0.78) 바로 위에서 눈가루가 칼이 지나가는 대로 떨어져 나가고, 큰 눈송이가 섞여 흩날린다.
			SpawnSlashFlakes(Feet, Direction, Definition.Range, SlashDustCount, FVector2D(SlashDustMinSize, SlashDustMaxSize),
				FVector2D(0.74f, 0.8f), FVector2D(SlashDustMinLife, SlashDustMaxLife));
			SpawnSlashFlakes(Feet, Direction, Definition.Range, SlashBigFlakeCount, FVector2D(SlashBigFlakeMinSize, SlashBigFlakeMaxSize),
				FVector2D(0.6f, 0.82f), FVector2D(SlashBigFlakeMinLife, SlashBigFlakeMaxLife));
			break;
		}
		break;
	}
	case 2:
		// 얼음 결정 부채: 안쪽·바깥쪽 두 줄의 얼음 결정이 왼쪽부터 솟았다 부서진다.
		for (int32 Row = 0; Row < 2; ++Row)
		{
			const int32 Count = Row == 0 ? SlashInnerCount : SlashOuterCount;
			const float Reach = Row == 0 ? SlashInnerReach : SlashOuterReach;
			const float Scale = Row == 0 ? SlashInnerScale : SlashOuterScale;
			for (int32 Index = 0; Index < Count; ++Index)
			{
				const float Alpha = static_cast<float>(Index) / (Count - 1);
				const FVector Along = Direction.RotateAngleAxis(FMath::Lerp(-FrostSlashHalfAngle, FrostSlashHalfAngle, Alpha), FVector::UpVector);
				const FVector Spot = Feet + Along * Definition.Range * Reach;
				GetWorld()->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, [this, Spot, Along, Scale]()
				{
					if (UParticleSystemComponent* Crystal = SpawnOwnedEffect(FreezeSegment, Spot, Along.Rotation()))
					{
						Crystal->SetWorldScale3D(FVector(Scale));
						ReleaseLater(Crystal, SlashCrystalSeconds + 0.2f, FreezeSegmentCrumble);
					}
				}), 0.01f + SlashRowSweepSeconds * Alpha, false);
			}
		}
		break;
	case 3:
		// 서리 바람: 부채꼴 서리 줄기가 왼쪽부터 휩쓸고, 궤적 세 곳에서 얼음 덩어리가 튄다.
		SweepFloorDecal(FrostSweepMaterial.LoadSynchronous(), Feet, Direction, Definition.Range, SlashWaveSeconds, SlashSweepSeconds);
		for (int32 Index = 0; Index < 3; ++Index)
		{
			const FVector Along = Direction.RotateAngleAxis(-40.0f + 40.0f * Index, FVector::UpVector);
			SpawnBurstLater(IceChunks, Feet + Along * Definition.Range * 0.65f, 0.45f, SlashSweepSeconds * (0.2f + 0.4f * Index), Along.Rotation());
		}
		break;
	default:
		for (int32 Index = 0; Index < 5; ++Index)
		{
			const FVector Along = Direction.RotateAngleAxis(-FrostSlashHalfAngle + FrostSlashHalfAngle * 0.5f * Index, FVector::UpVector);
			// 얼음 파편 크기 0.55 → 0.4(사용자 「조금만 더 작게」 2026-10-18)
			SpawnBurstLater(IceShards, Feet + Along * Definition.Range * 0.6f, 0.4f, 0.03f * Index, Along.Rotation());
		}
		SpawnSlashGround(Feet, Direction, Definition.Range);
		break;
	}
	if (Style == 5)
	{
		ScheduleWaveHits(Feet, Direction, 1.0f);
		return;
	}
	TArray<AActor*> Targets;
	GatherTargets(Feet, Definition.Range, Targets);
	const float MinDot = FMath::Cos(FMath::DegreesToRadians(FrostSlashHalfAngle));
	int32 Hits = 0;
	for (AActor* Target : Targets)
	{
		const FVector Offset = Target->GetActorLocation() - Character->GetActorLocation();
		if (FVector::DotProduct(Direction, Offset.GetSafeNormal2D()) >= MinDot)
		{
			StrikeFrostSlash(Target, Direction);
			++Hits;
		}
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_SLASH hits=%d style=%d"), Hits, Style);
}

void UAuroraSkillComponent::GetWaveFlight(int32 Blade, float& OutReach, float& OutSeconds) const
{
	const bool bBig = (Blade & 16) != 0;
	OutReach = bBig ? QBigReach : Skills[EAuroraSkill::FrostSlash].Range;
	OutSeconds = bBig ? QBigSeconds : QWaveSeconds;
}

void UAuroraSkillComponent::ScheduleWaveHits(const FVector& Feet, const FVector& Direction, float DamageScale, float Reach, float Seconds,
	float HitStop, float Roll)
{
	const FAuroraSkillDefinition& Definition = Skills[EAuroraSkill::FrostSlash];
	if (Reach <= 0.0f || Seconds <= 0.0f)
	{
		Reach = Definition.Range;
		Seconds = QWaveSeconds;
	}
	TArray<AActor*> Targets;
	GatherTargets(Feet, Reach, Targets);
	const float MinDot = FMath::Cos(FMath::DegreesToRadians(FrostSlashHalfAngle));
	// 검기가 대상에 닿는 때(떠난 자리에서 날아온 거리 ÷ 빠르기)에 맞는다.
	const float WaveSpeed = (Reach - QWaveStart) / Seconds;
	int32 Hits = 0;
	for (AActor* Target : Targets)
	{
		const FVector Offset = Target->GetActorLocation() - Feet;
		if (FVector::DotProduct(Direction, Offset.GetSafeNormal2D()) < MinDot)
		{
			continue;
		}
		++Hits;
		const float Delay = FMath::Max(Offset.Size2D() - QWaveStart, 0.0f) / WaveSpeed;
		if (Delay <= 0.0f)
		{
			StrikeFrostSlash(Target, Direction, DamageScale);
			OnQAddHit(Target, Direction, Roll);
			if (HitStop > 0.0f)
			{
				BeginHitStop(Target, HitStop);
			}
			continue;
		}
		TWeakObjectPtr<AActor> Weak = Target;
		GetWorld()->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, [this, Weak, Direction, DamageScale, HitStop, Roll]()
		{
			if (AActor* Actor = Weak.Get())
			{
				StrikeFrostSlash(Actor, Direction, DamageScale);
				OnQAddHit(Actor, Direction, Roll);
				if (HitStop > 0.0f)
				{
					BeginHitStop(Actor, HitStop);
				}
			}
		}), Delay, false);
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_SLASH hits=%d style=%d scale=%.2f hitstop=%.2f"), Hits, CVarAuroraSlashStyle.GetValueOnGameThread(),
		DamageScale, HitStop);
}

void UAuroraSkillComponent::LaunchIceWave(uint32 Generation, int32 Index)
{
	if (!bCasting || Generation != CastGeneration || !Character.IsValid() || !GetWorld())
	{
		return;
	}
	// 세 칼 모두 처음 겨눈 쪽으로 날린다. 「/」(왼쪽 아래 → 오른쪽 위)와 「\」가 번갈아 기운다.
	FVector Direction = (ActiveAim - Character->GetActorLocation()).GetSafeNormal2D();
	if (Direction.IsNearlyZero())
	{
		Direction = Character->GetActorForwardVector().GetSafeNormal2D();
	}
	const FVector Feet = GetFeetLocation();
	// 눕힌 두 번(Aurora.FX.QFlat 1, 헤더 QFlatVolley 설명): 기울이지 않는다(옆 기울기 0 — 화면 기울기 QTilt도 기운 쪽 부호를 곱해 0)
	const bool bFlat = CVarAuroraSlashFlat.GetValueOnGameThread() != 0;
	const int32 Volley = bFlat ? QFlatVolley : UE_ARRAY_COUNT(QVolleyLaunch);
	// 큰 검기 시안 QBig 8: 마지막 검기를 크게 + 맞는 순간 멈칫
	const int32 Blade = CVarAuroraSlashBlade.GetValueOnGameThread();
	const bool bFinisher = (Blade & 16) && (CVarAuroraSlashBig.GetValueOnGameThread() & 8) && Index == Volley - 1;
	const float Roll = Index == 1 ? -1.0f : 1.0f;
	SpawnFlyingWave(Feet, Direction, true, bFlat ? 0.0f : Roll, bFinisher ? QFinisherScale : 1.0f);
	OnQAddLaunch();
	// 큰 검기 시안(QBlade 16)은 멀리·빠르게 나는 만큼 맞는 거리·때도 같이
	float Reach = 0.0f;
	float Seconds = 0.0f;
	GetWaveFlight(Blade, Reach, Seconds);
	ScheduleWaveHits(Feet, Direction, bFlat ? QFlatVolleyDamage : QVolleyDamage[Index], Reach, Seconds, bFinisher ? QFinisherHitStop : 0.0f, Roll);
	UE_LOG(LogTemp, Display, TEXT("AURORA_VOLLEY wave=%d of=%d flat=%d"), Index, Volley, bFlat);
}

void UAuroraSkillComponent::StrikeFrostSlash(AActor* Target, const FVector& Direction, float DamageScale)
{
	if (!IsValid(Target) || !Character.IsValid())
	{
		return;
	}
	const FAuroraSkillDefinition& Definition = Skills[EAuroraSkill::FrostSlash];
	// 얼어 있는 적은 깨뜨려 피해 2배. 얼음은 그 자리에서 터지고 얼림은 풀린다.
	const bool bFrozen = IsFrozen(Target);
	if (Target->CanBeDamaged())
	{
		FHitResult Hit(Target, nullptr, Target->GetActorLocation(), -Direction);
		UGameplayStatics::ApplyPointDamage(Target, Definition.Damage * DamageScale * (bFrozen ? FrostSlashFrozenMultiplier : 1.0f), Direction,
			Hit, Character->GetController(), GetOwner(), nullptr);
	}
	SetStatus(Target, TEXT("SLOW"), FrostSlashSlowSeconds);
	// 맞은 자리 이펙트 시안(Aurora.FX.QHit, 10-19 「얼음 파편도 초승달 검기에 어울리는 이펙트로」). 검기가 지나가는 쪽(Along)을 본다.
	// 날아가는 검기(QStyle 5·6)는 검기가 나는 쪽으로 무거운 얼음 파편이 튄다(반짝이는 가볍다 — 큰 틀 진단). 6은 Aurora 평타의 얼음 타격도.
	const FVector Along(-Direction.Y, Direction.X, 0.0f);
	const int32 Style = CVarAuroraSlashStyle.GetValueOnGameThread();
	if (Style == 5 || Style == 6)
	{
		SpawnImpactShards(Target->GetActorLocation(), Direction, FindFloorZ(Target->GetActorLocation(), GetFeetLocation().Z));
		if (Style == 6)
		{
			SpawnBurstLater(MeleeImpact, Target->GetActorLocation(), 1.2f, 0.0f, (-Direction).Rotation());
		}
	}
	else
	{
		switch (CVarAuroraSlashHit.GetValueOnGameThread())
		{
		case 0:
			SpawnBurstLater(MeleeImpact, Target->GetActorLocation(), 1.0f, 0.0f, (-Direction).Rotation());
			break;
		case 2:
			SpawnBurstLater(PrisonBurstEffect, Target->GetActorLocation(), 0.8f, 0.0f);
			break;
		case 3:
			SpawnBurstLater(SlashSparkles, Target->GetActorLocation(), 1.0f, 0.0f, Along.Rotation());
			break;
		default:
			SpawnBurstLater(LanceFlash, Target->GetActorLocation(), 1.4f, 0.0f, Along.Rotation());
			break;
		}
	}
	// 87차 「Q-2에 결정 파열로」(Aurora.FX.QBurst) — 남는 고드름 무더기는 「바닥 얼음 오브젝트 남발 금지」로 뺐다
	if (UseQBurst() && !QBurstTargets.Contains(Target))
	{
		QBurstTargets.Add(Target);
		const FVector At = Target->GetActorLocation();
		PolishHitBurst(FVector(At.X, At.Y, FindFloorZ(At, GetFeetLocation().Z)), 1.0f);
	}
	if (bFrozen)
	{
		SpawnBurstLater(CryoExplode, Target->GetActorLocation(), 1.0f, 0.0f);
		FrozenUntil.Remove(Target);
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_SLASH strike=%s shattered=%d"), *Target->GetName(), bFrozen);
}

void UAuroraSkillComponent::SpawnFlyingWave(const FVector& Feet, const FVector& Direction, bool bIce, float Roll, float Scale)
{
	// 검기 시안(Aurora.FX.QBlade 비트, 10-20 밤 「Q 다 아쉽다」 — 헤더 QLightCandelas 설명의 까닭 셋): 1 몸통 전체가 빛나는 두꺼운 초승달 ·
	// 2 날 위 얼음 원뿔이 스스로 빛남 · 4 검기마다 푸른 빛이 따라가며 바닥·대상을 비춤 · 8 얼음 원뿔을 뺌
	// 이어서(「7번이 그나마 낫다 — 더 크게, 굵게, 빠르게, 더 멀리, 더 거친 느낌」, 헤더 QBigReach 설명): 16 큰 검기(뜯긴 결 그림) · 32 잔상 줄기 ·
	// 64 파편 강화
	const int32 Blade = bIce ? CVarAuroraSlashBlade.GetValueOnGameThread() : 0;
	const bool bBig = (Blade & 16) != 0;
	// 23 바탕 시안(Aurora.FX.QBig, 헤더 QContrastIce 설명): 1 더 거친 결 · 2 흰 날 + 짙푸른 몸통 · 4 끝에서 산산조각 · 8 마지막 검기 크게(Scale)
	const int32 Big = bBig ? CVarAuroraSlashBig.GetValueOnGameThread() : 0;
	UMaterialInterface* Bright = (Big & 1) ? WaveBladeRougherMaterial.LoadSynchronous() : nullptr;
	if (!Bright && bBig)
	{
		Bright = WaveBladeRoughMaterial.LoadSynchronous();
	}
	if (!Bright && (Blade & (1 | 16)))
	{
		Bright = WaveBladeBrightMaterial.LoadSynchronous();
	}
	// 시안(Aurora.FX.QFeel, 큰 검기에만, 헤더 QFeelUnfoldSeconds 설명): 1 칼에서 펼쳐짐 · 4 움직이는 그림(여덟 장 넘김 재질,
	// 없으면 그 전 재질)
	const int32 Feel = bBig ? CVarAuroraSlashFeel.GetValueOnGameThread() : 0;
	if (Feel & 4)
	{
		if (UMaterialInterface* Flip = WaveBladeFlipMaterial.LoadSynchronous())
		{
			Bright = Flip;
		}
	}
	UMaterialInterface* Material = Bright ? Bright : WaveBladeMaterial.LoadSynchronous();
	// 골격 시안(Aurora.FX.QShape, 큰 검기에만, 헤더 QShapeUprightRoll 설명): 3 가는 칼빛 = 처음 초승달 그림 · 4 얼음 고리 = 거친 충격파 고리 그림
	const int32 Shape = bBig ? GetQShape() : 0;
	if (Shape == 3)
	{
		Material = WaveBladeMaterial.LoadSynchronous();
	}
	else if (Shape == 4)
	{
		UMaterialInterface* Ring = NovaRingRoughMaterial.LoadSynchronous();
		Material = Ring ? Ring : NovaRingMaterial.LoadSynchronous();
	}
	// 이펙트 시안(Aurora.FX.QSkin, 누운 큰 검기에만, 헤더 QSkinAuraScale 설명): 2·4는 오로라 빛깔·흐르는 결 값이 있는 재질(없으면 그 전 재질).
	// 1 빛무리는 지금 큰 검기 재질 그대로 사본을 쓴다.
	UMaterialInterface* AuraSource = Material;
	const int32 Skin = bBig && Shape == 0 ? GetQSkin() : 0;
	if (Skin & (2 | 4))
	{
		if (UMaterialInterface* SkinMaterial = WaveBladeSkinMaterial.LoadSynchronous())
		{
			Material = SkinMaterial;
		}
	}
	// 87차 Q 검기 재작업(Aurora.FX.QSlash, AuroraSkillComponentPolish.cpp): 1 날 선 검기 · 2 결정 검기 — 셰이더로 그린 새 재질로 바꾸고
	// 빛무리 판·날 위 얼음 원뿔은 뺀다(10-28 「Q의 진짜 문제는 저 검기 자체」 — 덧붙인 것 말고 검기 자체로 보이게)
	const int32 Forge = GetQSlash();
	// 94차 7~9 팩 칼 궤적(「Q는 그림 톤·게임 톤과 안 맞는다」 — 수식 도형 대신 팩 오로라 칼 궤적 재질): 7 넓은 리본 + 메시 꼬리 재질 ·
	// 8 가는 날 선(Style 6) 아래에 7을 겹침 · 9 가는 리본 + 평타 칼 궤적 재질 아래에 7을 겹침(AuroraSkillComponentPolish.cpp LoadQ*)
	const bool bTrailPlane = Forge == 7 || Forge == 9;
	// 95차 「검기를 아주 얇게」: 10 머리카락 굵기 날 선(Style 7) 아래에 아주 가는 리본 한 겹 · 11 그 날 선만
	UMaterialInterface* ForgeMaterial = bTrailPlane ? LoadQTrailMaterial(Forge == 9) :
		Forge > 0 ? QSlashForgeMaterial.LoadSynchronous() : nullptr;
	if (ForgeMaterial)
	{
		Material = ForgeMaterial;
	}
	if (!PlaneMesh || !Material || !GetWorld())
	{
		return;
	}
	float Range = 0.0f;
	float Seconds = 0.0f;
	GetWaveFlight(Blade, Range, Seconds);
	const float Height = bBig ? QBigHeight : QWaveHeight;
	const float Life = Seconds * (Range + QWaveOvershoot - QWaveStart) / (Range - QWaveStart);
	// 리본은 판과 같은 짜임(가운데 원점 · ±50 · 나는 쪽 -Y)으로 만들어 BladeTick이 판처럼 옮기고 키운다
	UStaticMesh* WaveShape = bTrailPlane ? LoadQRibbon(Forge == 9) : PlaneMesh.Get();
	UStaticMeshComponent* Mesh = WaveShape ? SpawnTimedMesh(WaveShape, FTransform(FRotator::ZeroRotator, Feet, FVector(0.001f)), Life + 0.05f) : nullptr;
	if (!Mesh)
	{
		return;
	}
	UMaterialInstanceDynamic* Dynamic = UMaterialInstanceDynamic::Create(Material, Mesh);
	if (ForgeMaterial)
	{
		Dynamic->SetScalarParameterValue(TEXT("Style"), static_cast<float>(Forge == 8 ? 6 : Forge >= 10 ? 7 : Forge));
		if (bTrailPlane)
		{
			Dynamic->SetScalarParameterValue(TEXT("Brightness"), GetQTrailBrightness(Forge == 9));
		}
	}
	// 두꺼운 초승달(Bright)은 재질 기본값이 얼음빛이다
	if (bIce && !Bright)
	{
		// 얼음 검기는 하얀 빛 대신 푸른 얼음빛 날(5의 하얗게 빛나는 판은 「너무 별로」) — 빛은 날 가운데 선만 남기고 퍼진 빛을 줄인다.
		// 10-20 「검기는 푸른 계열로」: 가운데 선도 하늘색으로(전 값 0.78·0.92·1 × 밝기 2.3은 화면에서 하얗게 날아갔다), 몸통은 짙은 파랑을 더 드러낸다.
		Dynamic->SetVectorParameterValue(TEXT("IceColour"), FLinearColor(0.04f, 0.24f, 1.0f));
		Dynamic->SetVectorParameterValue(TEXT("WhiteColour"), FLinearColor(0.32f, 0.64f, 1.0f));
		Dynamic->SetScalarParameterValue(TEXT("Brightness"), 0.9f);
		Dynamic->SetScalarParameterValue(TEXT("LineGlow"), 1.1f);
		Dynamic->SetScalarParameterValue(TEXT("HaloOpacity"), 0.4f);
	}
	if (Big & 2)
	{
		Dynamic->SetVectorParameterValue(TEXT("IceColour"), QContrastIce);
		Dynamic->SetVectorParameterValue(TEXT("WhiteColour"), QContrastWhite);
		Dynamic->SetScalarParameterValue(TEXT("Brightness"), QContrastBrightness);
		Dynamic->SetScalarParameterValue(TEXT("LineGlow"), QContrastLineGlow);
	}
	if (Shape == 3)
	{
		// 가는 칼빛: 가운데 날 선을 희푸르게 세게, 둘레 번짐은 얼음빛으로 조금
		Dynamic->SetVectorParameterValue(TEXT("IceColour"), FLinearColor(0.08f, 0.4f, 1.0f));
		Dynamic->SetVectorParameterValue(TEXT("WhiteColour"), FLinearColor(0.8f, 0.94f, 1.0f));
		Dynamic->SetScalarParameterValue(TEXT("Brightness"), 1.3f);
		Dynamic->SetScalarParameterValue(TEXT("LineGlow"), 4.0f);
		Dynamic->SetScalarParameterValue(TEXT("HaloOpacity"), 0.55f);
	}
	if (Skin & 2)
	{
		Dynamic->SetScalarParameterValue(TEXT("AuroraMix"), 1.0f);
	}
	if (Skin & 4)
	{
		Dynamic->SetScalarParameterValue(TEXT("FlowStrength"), QSkinFlowStrength);
		Dynamic->SetScalarParameterValue(TEXT("FlowTiling"), QSkinFlowTiling);
	}
	if (Skin & (2 | 4))
	{
		// 날 빛 2.5 그대로면 몸통이 흰빛으로 꽉 차 빛깔·결이 묻혔다(첫 촬영)
		Dynamic->SetScalarParameterValue(TEXT("LineGlow"), QSkinToneGlow);
	}
	Mesh->SetMaterial(0, Dynamic);
	Mesh->SetCastShadow(false);
	Mesh->SetReceivesDecals(false);
	FAuroraWave Wave;
	Wave.Mesh = Mesh;
	Wave.Material = Dynamic;
	Wave.Feet = Feet;
	Wave.Direction = Direction;
	Wave.Born = GetWorld()->GetTimeSeconds();
	Wave.Roll = Roll;
	Wave.NextShed = Wave.Born + QIceShedSeconds;
	Wave.bIce = bIce;
	Wave.Reach = Range;
	Wave.Seconds = Seconds;
	Wave.StartWidth = (bIce ? (bBig ? QBigStartWidth : QIceWaveStartWidth) : QWaveStartWidth) * Scale;
	Wave.EndWidth = (bIce ? (bBig ? QBigEndWidth : QIceWaveEndWidth) : QWaveEndWidth) * Scale;
	Wave.Height = Height;
	Wave.bSmear = (Blade & 32) != 0;
	Wave.bHeavy = (Blade & 64) != 0;
	Wave.bShatter = (Big & 4) != 0;
	Wave.Feel = Feel;
	Wave.Shape = Shape;
	Wave.Skin = Skin;
	// 긴 잔광은 골격 3과 이펙트 시안 16이 같이 쓴다(가는 날 선 사본)
	Wave.bAfterglow = Shape == 3 || (Skin & 8) != 0;
	// 얼음 덩어리는 골격 2(크게, 그림 옅게)와 이펙트 시안 16(작게, 그림 그대로)이 같이 쓴다 · 93차 QSlash 6(얼음 덩어리 초승달)은 골격 2 크기로
	const bool bForgeChunks = ForgeMaterial && Forge == 6;
	const bool bChunks = (Shape == 2 || (Skin & 16) || bForgeChunks) && IceChunkMesh;
	Wave.ChunkSize = bChunks ? (Shape == 2 || bForgeChunks ? QShapeChunkSize : QSkinChunkSize) : 0.0f;
	if (Shape == 1)
	{
		// 골격 1: 카메라 반대쪽으로 기운 검기는 가는 줄로만 보였다(첫 촬영의 둘째 검기) — 셋 다 카메라 쪽으로 눕는 쪽으로 세운다
		if (const APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(GetWorld(), 0))
		{
			const FQuat Flat = FRotationMatrix::MakeFromYZ(-Direction, FVector::UpVector).ToQuat();
			const FVector Normal = (FQuat(Direction, FMath::DegreesToRadians(QShapeUprightRoll)) * Flat).GetAxisZ();
			Wave.Roll = FVector::DotProduct(Normal, Camera->GetCameraLocation() - Feet) >= 0.0f ? 1.0f : -1.0f;
		}
	}
	else if (Shape != 4 && CVarAuroraSlashTilt.GetValueOnGameThread() != 0.0f)
	{
		// 화면 기울기(헤더 QWaveRoll 설명): 카메라를 등지고 쏠 때 나는 쪽 축으로 기운 쪽과 같은 쪽으로 — 마주 보고 쏘면 화면에서 거꾸로
		// 도는 셈이라 부호를 뒤집는다(칼이 「/」면 검기도 「/」)
		if (const APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(GetWorld(), 0))
		{
			Wave.ViewAxis = Camera->GetCameraRotation().Vector();
			const float Sense = FVector::DotProduct(Direction, Wave.ViewAxis) >= 0.0f ? 1.0f : -1.0f;
			Wave.Tilt = CVarAuroraSlashTilt.GetValueOnGameThread() * Roll * Sense;
		}
	}
	if (bChunks)
	{
		// 골격 2: 날 자리마다 얼음 덩어리 — 가운데가 크고 양끝으로 작아지며, 덩어리마다 아무렇게나 돌려 박는다. 팩 얼음 재질은 흰 눈뭉치처럼
		// 보여(둘째 촬영) 스스로 빛나는 얼음(QBlade 2의 원뿔과 같은 것)을 입힌다.
		UMaterialInterface* ChunkGlow = GlowIceMaterial.LoadSynchronous();
		// 93차 QSlash 6: 첫 촬영(aurora-93rd-final)에서 빛나는 흰 얼음은 흰 블록 줄로 보였다 → F 얼음송곳과 같은 짙푸른 빛나는 얼음
		if (bForgeChunks)
		{
			if (UMaterialInterface* Deep = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
				TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_SpearIce.M_Aurora_SpearIce"))).LoadSynchronous())
			{
				ChunkGlow = Deep;
			}
		}
		const int32 ChunkCount = Shape == 2 || bForgeChunks ? QShapeChunkCount : QSkinChunkCount;
		for (int32 Index = 0; Index < ChunkCount; ++Index)
		{
			const float Alpha = static_cast<float>(Index) / (ChunkCount - 1);
			const float Angle = FMath::Lerp(-55.0f, 55.0f, Alpha) + FMath::FRandRange(-4.0f, 4.0f);
			const float Size = FMath::Lerp(0.5f, 1.0f, FMath::Cos(FMath::DegreesToRadians(Angle) * 1.4f)) * FMath::FRandRange(0.8f, 1.2f);
			if (UStaticMeshComponent* Chunk = SpawnTimedMesh(IceChunkMesh, FTransform(FRotator::ZeroRotator, Feet, FVector(0.001f)), Life + 0.05f))
			{
				for (int32 Slot = 0; ChunkGlow && Slot < Chunk->GetNumMaterials(); ++Slot)
				{
					Chunk->SetMaterial(Slot, ChunkGlow);
				}
				Chunk->SetCastShadow(false);
				Chunk->SetReceivesDecals(false);
				Wave.Crest.Add(Chunk);
				Wave.CrestShape.Add(FVector2D(Angle, Size));
				Wave.CrestSpin.Add(FRotator(FMath::FRandRange(0.0f, 360.0f), FMath::FRandRange(0.0f, 360.0f), FMath::FRandRange(0.0f, 360.0f)).Quaternion());
			}
		}
	}
	else if (Shape == 4 && BladeMesh)
	{
		// 골격 4: 고리 둘레에 같은 틈으로 톱니(빛나는 얼음 원뿔)
		UMaterialInterface* Glow = GlowIceMaterial.LoadSynchronous();
		for (int32 Index = 0; Index < QShapeRingTeeth; ++Index)
		{
			if (UStaticMeshComponent* Tooth = SpawnTimedMesh(BladeMesh, FTransform(FRotator::ZeroRotator, Feet, FVector(0.001f)), Life + 0.05f))
			{
				Tooth->SetMaterial(0, Glow ? Glow : BladeMaterial.Get());
				Tooth->SetCastShadow(false);
				Tooth->SetReceivesDecals(false);
				Wave.Crest.Add(Tooth);
				Wave.CrestShape.Add(FVector2D(360.0f * Index / QShapeRingTeeth, 1.0f));
			}
		}
	}
	else if (Shape != 3 && bIce && BladeMesh && !(Blade & 8) && !ForgeMaterial)
	{
		// 날을 따라 바깥으로 솟은 얼음 조각: 가운데가 길고 양끝으로 짧아지며, 각도·길이를 조금씩 흩어 들쭉날쭉하게.
		UMaterialInterface* CrestMaterial = (Blade & 2) ? GlowIceMaterial.LoadSynchronous() : nullptr;
		if (!CrestMaterial)
		{
			CrestMaterial = BladeMaterial;
		}
		const int32 CrestCount = Wave.bHeavy ? QBigCrestCount : QIceCrestCount;
		for (int32 Index = 0; Index < CrestCount; ++Index)
		{
			const float Alpha = static_cast<float>(Index) / (CrestCount - 1);
			const float Angle = FMath::Lerp(-55.0f, 55.0f, Alpha) + FMath::FRandRange(-6.0f, 6.0f);
			const float Length = FMath::Lerp(0.45f, 1.0f, FMath::Cos(FMath::DegreesToRadians(Angle) * 1.4f)) * FMath::FRandRange(0.75f, 1.25f);
			if (UStaticMeshComponent* Shard = SpawnTimedMesh(BladeMesh, FTransform(FRotator::ZeroRotator, Feet, FVector(0.001f)), Life + 0.05f))
			{
				if (CrestMaterial)
				{
					Shard->SetMaterial(0, CrestMaterial);
				}
				Shard->SetCastShadow(false);
				Shard->SetReceivesDecals(false);
				Wave.Crest.Add(Shard);
				Wave.CrestShape.Add(FVector2D(Angle, Length));
			}
		}
	}
	// 이펙트 시안 1 빛무리: 검기 판과 같이 움직이는 판 하나(자리·흐려짐은 BladeTick) — 같은 그림의 퍼진 빛만 짙은 파랑으로
	if ((Skin & 1) && AuraSource && !ForgeMaterial)
	{
		if (UStaticMeshComponent* AuraMesh = SpawnTimedMesh(PlaneMesh, FTransform(FRotator::ZeroRotator, Feet, FVector(0.001f)), Life + 0.05f))
		{
			UMaterialInstanceDynamic* AuraDynamic = UMaterialInstanceDynamic::Create(AuraSource, AuraMesh);
			AuraDynamic->SetVectorParameterValue(TEXT("IceColour"), FLinearColor(0.03f, 0.25f, 1.0f));
			AuraDynamic->SetVectorParameterValue(TEXT("WhiteColour"), FLinearColor(0.1f, 0.4f, 1.0f));
			AuraDynamic->SetScalarParameterValue(TEXT("Brightness"), 1.2f);
			AuraDynamic->SetScalarParameterValue(TEXT("LineGlow"), 0.0f);
			AuraDynamic->SetScalarParameterValue(TEXT("LineOpacity"), 0.0f);
			AuraDynamic->SetScalarParameterValue(TEXT("HaloOpacity"), QSkinAuraHalo);
			AuraMesh->SetMaterial(0, AuraDynamic);
			AuraMesh->SetCastShadow(false);
			AuraMesh->SetReceivesDecals(false);
			Wave.Aura = AuraMesh;
			Wave.AuraMaterial = AuraDynamic;
		}
	}
	// 94차 QSlash 8·9: 날 아래에 넓은 리본 + 메시 꼬리 재질 한 겹(빛무리 판 자리 — BladeTick이 같은 가운데·같은 크기로 옮긴다)
	if ((Forge == 8 || Forge == 9 || Forge == 10) && !Wave.Aura.IsValid())
	{
		UStaticMesh* Wide = Forge == 10 ? LoadQRibbonHair() : LoadQRibbon(false);
		UMaterialInterface* Smoke = LoadQTrailMaterial(false);
		if (UStaticMeshComponent* Layer = Wide && Smoke ?
			SpawnTimedMesh(Wide, FTransform(FRotator::ZeroRotator, Feet, FVector(0.001f)), Life + 0.05f) : nullptr)
		{
			UMaterialInstanceDynamic* LayerDynamic = UMaterialInstanceDynamic::Create(Smoke, Layer);
			LayerDynamic->SetScalarParameterValue(TEXT("Brightness"), GetQTrailBrightness(false));
			Layer->SetMaterial(0, LayerDynamic);
			Layer->SetCastShadow(false);
			Layer->SetReceivesDecals(false);
			Wave.Aura = Layer;
			Wave.AuraMaterial = LayerDynamic;
			Wave.AuraScale = 1.0f;
		}
	}
	if (Feel & 1)
	{
		// 시안 1: 칼을 떠나는 자리에 번쩍(F 던질 때 손 앞 이펙트와 같은 것, 작게)
		SpawnBurstLater(LanceFlash, Feet + Direction * QWaveStart + FVector(0.0f, 0.0f, Height), QFeelFlashScale, 0.0f, Direction.Rotation());
	}
	// 검기 시안(Aurora.FX.QWave 비트, 10-20 「Q도 시안 — 필요하면 조합해서」): 1 Yin 바람 줄기 메시를 같이 싣고 · 2 Yin 채찍 잔상이
	// 날 꼭대기를 따라가고 칼 앞에서 바람 날개가 터짐 · 4 같은 초승달 둘이 뒤에 겹쳐 따라옴. 자리·크기는 BladeTick이 검기와 같이 정한다.
	const int32 Extra = bIce ? CVarAuroraSlashWave.GetValueOnGameThread() : 0;
	const FVector Launch = Feet + Direction * QWaveStart + FVector(0.0f, 0.0f, Height);
	if (Extra & 1)
	{
		if (UStaticMesh* Ribbon = YinWindSpline.LoadSynchronous())
		{
			if (UStaticMeshComponent* SplineMesh = SpawnTimedMesh(Ribbon, FTransform(FRotator::ZeroRotator, Feet, FVector(0.001f)), Life + 0.05f))
			{
				SplineMesh->SetCastShadow(false);
				SplineMesh->SetReceivesDecals(false);
				Wave.Spline = SplineMesh;
			}
		}
	}
	if (Extra & 2)
	{
		if (UParticleSystem* Trail = YinAfterimage.LoadSynchronous())
		{
			if (UParticleSystemComponent* Afterimage = SpawnOwnedEffect(Trail, Launch, Direction.Rotation()))
			{
				Afterimage->SetWorldScale3D(FVector(QAfterimageScale));
				Wave.Afterimage = Afterimage;
			}
		}
		if (UParticleSystem* Wings = YinKickOff.LoadSynchronous())
		{
			SpawnBurstLater(Wings, Launch, QKickOffScale, 0.0f, Direction.Rotation());
		}
	}
	// 94차 QSlash 7~9: 꼭대기를 따라 오로라 평타의 눈송이(팩 원본)가 흩날린다 — 자리는 BladeTick이 Afterimage로 옮기고 끝날 때 놓는다
	if (Forge >= 7 && !Wave.Afterimage.IsValid())
	{
		if (UParticleSystem* Snow = LoadQTrailSnow())
		{
			Wave.Afterimage = SpawnOwnedEffect(Snow, Launch, Direction.Rotation());
		}
	}
	// 87차 날 선 검기(QSlash 1)는 같은 검기 둘이 뒤에 겹쳐 따라와 빠르게 벤 느낌(89차 촬영: 혼자서는 가늘고 느슨해 보였다)
	if ((Extra & 4) || Wave.bSmear || Wave.bAfterglow || (ForgeMaterial && Forge == 1))
	{
		// 잔상 줄기(QBlade 32)는 같은 검기를 더 촘촘히 더 많이 · 긴 잔광(골격 3 · 이펙트 시안 16)은 더 길게, 가는 날 선 그림으로
		const int32 EchoCount = Wave.bAfterglow ? QShapeTrailCount : Wave.bSmear ? QSmearCount : QEchoCount;
		UMaterialInterface* EchoSource = Wave.bAfterglow ? WaveBladeMaterial.LoadSynchronous() : Material;
		for (int32 Echo = 0; EchoSource && Echo < EchoCount; ++Echo)
		{
			UStaticMeshComponent* EchoMesh = SpawnTimedMesh(PlaneMesh, FTransform(FRotator::ZeroRotator, Feet, FVector(0.001f)), Life + 0.05f);
			if (!EchoMesh)
			{
				continue;
			}
			// 같은 재질 사본에 얼음빛 값을 그대로 옮긴다
			UMaterialInstanceDynamic* EchoDynamic = UMaterialInstanceDynamic::Create(EchoSource, EchoMesh);
			if (EchoSource == Material)
			{
				EchoDynamic->CopyParameterOverrides(Dynamic);
			}
			if (Wave.bAfterglow)
			{
				// 긴 잔광은 날 선만 푸르게 — 번짐까지 옮기면 스무 장이 겹쳐 흰 반달 판이 됐다(둘째 촬영)
				EchoDynamic->SetVectorParameterValue(TEXT("IceColour"), FLinearColor(0.05f, 0.3f, 1.0f));
				EchoDynamic->SetVectorParameterValue(TEXT("WhiteColour"), FLinearColor(0.45f, 0.75f, 1.0f));
				EchoDynamic->SetScalarParameterValue(TEXT("LineGlow"), 2.0f);
				EchoDynamic->SetScalarParameterValue(TEXT("HaloOpacity"), 0.05f);
			}
			EchoMesh->SetMaterial(0, EchoDynamic);
			EchoMesh->SetCastShadow(false);
			EchoMesh->SetReceivesDecals(false);
			Wave.Echoes.Add(EchoMesh);
			Wave.EchoMaterials.Add(EchoDynamic);
		}
	}
	if ((Blade & 4) && Character.IsValid())
	{
		// 붙이지 않은 점광 — 자리·세기(검기 흐려짐을 따름)는 BladeTick이 정하고, 검기가 끝날 때 지운다(S 빛과 같은 빛깔, 그림자 없음).
		UPointLightComponent* Light = NewObject<UPointLightComponent>(Character.Get());
		Light->SetMobility(EComponentMobility::Movable);
		Light->RegisterComponent();
		Light->SetWorldLocation(Launch);
		Light->SetIntensityUnits(ELightUnits::Candelas);
		Light->SetIntensity(0.0f);
		Light->SetLightColor(HasteLightColour);
		Light->SetAttenuationRadius(QLightReach);
		Light->SetCastShadows(false);
		Wave.Light = Light;
	}
	Waves.Add(Wave);
	if (!GetWorld()->GetTimerManager().IsTimerActive(BladeTimer))
	{
		GetWorld()->GetTimerManager().SetTimer(BladeTimer, this, &UAuroraSkillComponent::BladeTick, 1.0f / 60.0f, true);
	}
	BladeTick();
}

void UAuroraSkillComponent::BladeTick()
{
	if (!GetWorld())
	{
		return;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	const FVector ConeExtent = BladeMesh ? BladeMesh->GetBounds().BoxExtent : FVector(50.0f);
	const FVector ConeOrigin = BladeMesh ? BladeMesh->GetBounds().Origin : FVector::ZeroVector;
	for (int32 Index = Waves.Num() - 1; Index >= 0; --Index)
	{
		FAuroraWave& Wave = Waves[Index];
		UStaticMeshComponent* Mesh = Wave.Mesh.Get();
		// 나는 거리·빠르기는 검기마다(큰 검기 시안 QBlade 16은 더 멀리·빠르게)
		const float Range = Wave.Reach;
		const float Speed = (Range - QWaveStart) / Wave.Seconds;
		const float Age = static_cast<float>(Now - Wave.Born);
		const float Reach = QWaveStart + Speed * Age;
		if (!IsValid(Mesh) || Reach > Range + QWaveOvershoot)
		{
			for (const TWeakObjectPtr<UStaticMeshComponent>& Shard : Wave.Crest)
			{
				RemoveTimedMesh(Shard.Get(), nullptr);
			}
			for (const TWeakObjectPtr<UStaticMeshComponent>& Echo : Wave.Echoes)
			{
				RemoveTimedMesh(Echo.Get(), nullptr);
			}
			RemoveTimedMesh(Wave.Spline.Get(), nullptr);
			RemoveTimedMesh(Wave.Aura.Get(), nullptr);
			ReleaseOwnedEffect(Wave.Afterimage.Get());
			if (UPointLightComponent* Light = Wave.Light.Get())
			{
				Light->DestroyComponent();
			}
			if (Wave.bShatter && Wave.LastHalf > 0.0f)
			{
				// 시안 QBig 4: 다 날아간 자리(마지막 장면의 날)에서 빛나는 얼음 파편으로 깨져 앞·옆으로 흩어진다. 첫 판에 같이 띄운 냉기 충격
				// (IceShock)은 흰 연기 뭉치로 피어 뺐다.
				UMaterialInterface* Glow = GlowIceMaterial.LoadSynchronous();
				const FVector Up = Wave.LastRolled.GetAxisZ();
				for (int32 Bit = 0; Bit < QShatterCount; ++Bit)
				{
					const float Radians = FMath::DegreesToRadians(FMath::Lerp(-55.0f, 55.0f, (Bit + FMath::FRand()) / QShatterCount));
					const FVector Radial = Wave.LastRolled.RotateVector(FVector(FMath::Sin(Radians), -FMath::Cos(Radians), 0.0f));
					FAuroraShard Shard;
					Shard.FloorZ = Wave.Feet.Z + 3.0f;
					Shard.Start = Wave.LastCenter + Radial * QWaveArcReach * Wave.LastHalf;
					Shard.Velocity = Wave.Direction * FMath::FRandRange(250.0f, 650.0f) + Radial * FMath::FRandRange(80.0f, 220.0f) +
						Up * FMath::FRandRange(120.0f, 280.0f);
					Shard.Born = Now;
					Shard.Life = FMath::FRandRange(0.6f, 1.0f);
					const float Width = FMath::FRandRange(10.0f, 18.0f);
					Shard.Size = FVector(Width, Width * FMath::FRandRange(0.4f, 0.7f), FMath::FRandRange(30.0f, 55.0f));
					AddShard(Shard, Now, Glow);
				}
			}
			Waves.RemoveAtSwap(Index);
			continue;
		}
		// 폭은 멀어질수록 넓어지고, 끝 무렵(QWaveFadeFrom부터) 흐려진다. 그림 속 초승달 꼭대기(가운데에서 반지름의 0.78)가 Reach에 온다.
		const bool bIce = Wave.bIce;
		const float Grown = FMath::Clamp((Reach - QWaveStart) / (Range - QWaveStart), 0.0f, 1.0f);
		// 시안 QFeel 1: 처음 QFeelUnfoldSeconds 동안 칼에서 펴지듯 좁게 시작한다
		const float Unfold = (Wave.Feel & 1) ? FMath::Lerp(QFeelUnfoldFrom, 1.0f, FMath::Clamp(Age / QFeelUnfoldSeconds, 0.0f, 1.0f)) : 1.0f;
		// 골격 1 세운 검기는 서는 만큼 높아져 폭을 줄인다
		const float Width = FMath::Lerp(Wave.StartWidth, Wave.EndWidth, Grown) * Unfold * (Wave.Shape == 1 ? QShapeUprightScale : 1.0f);
		float Half = Width / QWaveArcWidth;
		const float FadeStart = Range * QWaveFadeFrom;
		const float FadeIn = FMath::Clamp(Age / 0.03f, 0.0f, 1.0f);
		const float Tail = Reach < FadeStart ? 1.0f : FMath::Clamp(1.0f - (Reach - FadeStart) / (Range + QWaveOvershoot - FadeStart), 0.0f, 1.0f);
		const float Fade = FadeIn * Tail;
		// 시안 QFeel 4: 생겨남(0·1) → 일렁임(2~4) → 흐려지는 구간에 찢겨 흩어짐(5~7)
		const bool bFlip = (Wave.Feel & 4) != 0;
		// 판의 그림 위쪽(-Y)이 나는 쪽을, 판 앞면(Z)이 위를 보게 눕히고, 나는 쪽을 축으로 옆으로 기울인다(올려 베는 칼 따라).
		const FQuat Flat = FRotationMatrix::MakeFromYZ(-Wave.Direction, FVector::UpVector).ToQuat();
		const float RollDegrees = Wave.Shape == 1 ? QShapeUprightRoll : QWaveRoll;
		FQuat Rolled = FQuat(Wave.Direction, FMath::DegreesToRadians(RollDegrees * Wave.Roll)) * Flat;
		// 골격 1: 날 끝(가운데에서 ±55도, 반지름 0.78)이 위아래로 sin(기운 각)만큼 벌어진다 — 아래 끝이 바닥을 스치게 띄운다
		float Height = Wave.Shape == 1 ?
			FMath::Max(Wave.Height, 0.82f * FMath::Sin(FMath::DegreesToRadians(QShapeUprightRoll)) * QWaveArcReach * Half + 5.0f) : Wave.Height;
		if (!Wave.ViewAxis.IsNearlyZero())
		{
			// 화면 기울기(헤더 QWaveRoll 설명): 카메라가 보는 축으로 돌린다. 날(가운데에서 ±55도)에서 가장 낮은 자리가 바닥 위 5cm에 오게 띄운다.
			Rolled = FQuat(Wave.ViewAxis, FMath::DegreesToRadians(Wave.Tilt)) * Flat;
			float Lowest = 0.0f;
			for (int32 Step = -5; Step <= 5; ++Step)
			{
				const float Radians = FMath::DegreesToRadians(11.0f * Step);
				Lowest = FMath::Min(Lowest, Rolled.RotateVector(FVector(FMath::Sin(Radians), -FMath::Cos(Radians), 0.0f)).Z * QWaveArcReach * Half);
			}
			Height = FMath::Max(Height, 5.0f - Lowest);
		}
		const FVector Apex = Wave.Feet + Wave.Direction * Reach + FVector(0.0f, 0.0f, Height);
		FVector Center = Apex - Wave.Direction * QWaveArcReach * Half;
		if (Wave.Shape == 4)
		{
			// 골격 4: 고리 바깥 날(판 반쪽의 0.9)의 앞이 나는 거리에 오고, 판 앞면 축으로 돈다
			const float RingRadius = 0.5f * FMath::Lerp(QShapeRingStart, QShapeRingEnd, Grown);
			Half = RingRadius / 0.9f;
			Rolled = FQuat(Wave.Direction, FMath::DegreesToRadians(QShapeRingTilt * Wave.Roll)) * Flat *
				FQuat(FVector::UpVector, FMath::DegreesToRadians(QShapeRingSpin * Age));
			Center = Apex - Wave.Direction * RingRadius;
		}
		Mesh->SetWorldLocationAndRotation(Center, Rolled);
		Mesh->SetWorldScale3D(FVector(2.0f * Half / 100.0f, 2.0f * Half / 100.0f, 1.0f));
		Wave.LastCenter = Center;
		Wave.LastRolled = Rolled;
		Wave.LastHalf = Half;
		// 이펙트 시안 1 빛무리: 같은 가운데에서 조금 크게(날 밖으로도 번지게), 바로 밑에
		if (UStaticMeshComponent* AuraMesh = Wave.Aura.Get())
		{
			const float AuraHalf = Half * (Wave.AuraScale > 0.0f ? Wave.AuraScale : QSkinAuraScale);
			AuraMesh->SetWorldLocationAndRotation(Center - Rolled.GetAxisZ() * 0.5f, Rolled);
			AuraMesh->SetWorldScale3D(FVector(2.0f * AuraHalf / 100.0f, 2.0f * AuraHalf / 100.0f, 1.0f));
			if (UMaterialInstanceDynamic* AuraDynamic = Wave.AuraMaterial.Get())
			{
				AuraDynamic->SetScalarParameterValue(TEXT("Fade"), Fade);
			}
		}
		if (UMaterialInstanceDynamic* Dynamic = Wave.Material.Get())
		{
			// 골격 2는 얼음 덩어리가 몸통이고 그림은 옅게 받친다
			Dynamic->SetScalarParameterValue(TEXT("Fade"), Fade * (Wave.Shape == 2 ? QShapeChunkPlaneFade : 1.0f));
			if (bFlip)
			{
				constexpr int32 Frames = QFeelFlipColumns * QFeelFlipRows;
				const int32 Frame = Age < 0.03f ? 0 : Age < 0.06f ? 1 : Tail >= 1.0f ? 2 + FMath::FloorToInt(Age * QFeelFlickerRate) % 3 :
					FMath::Min(5 + FMath::FloorToInt((1.0f - Tail) * 3.0f), Frames - 1);
				Dynamic->SetScalarParameterValue(TEXT("FrameU"), static_cast<float>(Frame % QFeelFlipColumns) / QFeelFlipColumns);
				Dynamic->SetScalarParameterValue(TEXT("FrameV"), static_cast<float>(Frame / QFeelFlipColumns) / QFeelFlipRows);
			}
		}
		// 검기 시안(QWave): 바람 줄기는 긴 축을 검기 폭에 맞춰 같은 자세로 · 채찍 잔상은 날 꼭대기 · 겹 초승달은 QEchoLag씩 뒤처져 조금 좁고
		// 흐리게(검기가 몸에서 떨어질 때까지는 안 보임)
		if (UStaticMeshComponent* SplineMesh = Wave.Spline.Get())
		{
			const FBoxSphereBounds Bounds = SplineMesh->GetStaticMesh()->GetBounds();
			const float SplineScale = Width * QSplineWidthScale / FMath::Max(2.0f * Bounds.BoxExtent.X, 1.0f) * FMath::Max(Fade, 0.05f);
			SplineMesh->SetWorldScale3D(FVector(SplineScale));
			SplineMesh->SetWorldLocationAndRotation(Center - Rolled.RotateVector(Bounds.Origin * SplineScale), Rolled);
		}
		if (UParticleSystemComponent* Afterimage = Wave.Afterimage.Get())
		{
			Afterimage->SetWorldLocation(Apex);
		}
		if (UPointLightComponent* Light = Wave.Light.Get())
		{
			// 초승달 몸통 위(꼭대기에서 반지름의 0.3만큼 뒤), 바닥 가까이
			Light->SetWorldLocation(FVector(Apex.X, Apex.Y, Wave.Feet.Z + QLightHeight) - Wave.Direction * 0.3f * Half);
			Light->SetIntensity(QLightCandelas * Fade);
		}
		for (int32 Echo = 0; Echo < Wave.Echoes.Num(); ++Echo)
		{
			UStaticMeshComponent* EchoMesh = Wave.Echoes[Echo].Get();
			if (!IsValid(EchoMesh))
			{
				continue;
			}
			// 잔상 줄기(QBlade 32)는 촘촘히(QSmearLag) 덜 좁아지며 차례로 흐려진다 · 골격 3 긴 잔광은 더 길게 거의 안 좁아지며 같은 배율씩 흐려짐
			const bool bAfterglow = Wave.bAfterglow;
			const float Lag = (bAfterglow ? QShapeTrailLag : Wave.bSmear ? QSmearLag : QEchoLag) * (Echo + 1);
			const float EchoHalf = Half * (1.0f - (bAfterglow ? QShapeTrailShrink : Wave.bSmear ? QSmearShrink : QEchoShrink) * (Echo + 1));
			const float EchoStrength = bAfterglow ? QShapeTrailFirst * FMath::Pow(QShapeTrailDecay, static_cast<float>(Echo)) :
				Wave.bSmear ? QSmearFade[Echo] : QEchoFade[Echo];
			const FVector EchoApex = Apex - Wave.Direction * Lag;
			EchoMesh->SetWorldLocationAndRotation(EchoApex - Wave.Direction * QWaveArcReach * EchoHalf, Rolled);
			EchoMesh->SetWorldScale3D(FVector(2.0f * EchoHalf / 100.0f, 2.0f * EchoHalf / 100.0f, 1.0f));
			if (UMaterialInstanceDynamic* EchoDynamic = Wave.EchoMaterials[Echo].Get())
			{
				const float Away = FMath::Clamp((Reach - Lag - QWaveStart * 0.5f) / 40.0f, 0.0f, 1.0f);
				EchoDynamic->SetScalarParameterValue(TEXT("Fade"), Fade * EchoStrength * Away);
			}
		}
		// 얼음 조각 날: 초승달(가운데에서 반지름 0.78)의 각 자리에서 나는 쪽 뒤로 눕혀(조금 바깥·위로) 날을 따라 끌리는 두꺼운 얼음 날을
		// 이룬다 — 바깥으로 곧게 세웠더니 가시 달린 고리로 보였다(aurora-42nd-q6). 크기는 검기 폭을 따라 커지고 흐려지는 동안 줄어든다.
		const float ArcRadius = QWaveArcReach * Half;
		const float Size = Width / 300.0f * FMath::Max(Fade, 0.05f);
		const FVector Normal = Rolled.GetAxisZ();
		for (int32 Crest = 0; Crest < Wave.Crest.Num(); ++Crest)
		{
			UStaticMeshComponent* Shard = Wave.Crest[Crest].Get();
			if (!IsValid(Shard))
			{
				continue;
			}
			const float Radians = FMath::DegreesToRadians(Wave.CrestShape[Crest].X);
			if (Wave.ChunkSize > 0.0f && IceChunkMesh && Wave.CrestSpin.IsValidIndex(Crest))
			{
				// 골격 2 · 이펙트 시안 32: 덩어리 가운데를 날 위에 두고 판과 같이 돌린 제 자세로
				const FBoxSphereBounds ChunkBounds = IceChunkMesh->GetBounds();
				const float ChunkScale = Wave.ChunkSize * Wave.CrestShape[Crest].Y * Size / FMath::Max(2.0f * ChunkBounds.BoxExtent.GetMax(), 1.0f);
				const FQuat ChunkFacing = Rolled * Wave.CrestSpin[Crest];
				const FVector OnEdge = Center + Rolled.RotateVector(FVector(FMath::Sin(Radians), -FMath::Cos(Radians), 0.0f)) * ArcRadius;
				Shard->SetWorldLocationAndRotation(OnEdge - ChunkFacing.RotateVector(ChunkBounds.Origin * ChunkScale), ChunkFacing);
				Shard->SetWorldScale3D(FVector(ChunkScale));
				continue;
			}
			if (Wave.Shape == 4)
			{
				// 골격 4: 고리 바깥 날(반쪽의 0.9) 위 같은 틈의 자리에서 도는 반대쪽(뒤)으로 누운 톱니 — 판과 같이 돈다
				const FVector Rim = Rolled.RotateVector(FVector(FMath::Cos(Radians), FMath::Sin(Radians), 0.0f));
				const FVector Behind = Rolled.RotateVector(FVector(FMath::Sin(Radians), -FMath::Cos(Radians), 0.0f));
				const FVector ToothTip = (Behind * 0.75f + Rim * 0.65f).GetSafeNormal();
				const float ToothLength = QShapeRingToothLength * FMath::Max(Fade, 0.05f);
				const FVector ToothScale(QShapeRingToothWidth * FMath::Max(Fade, 0.05f) / (2.0f * ConeExtent.X),
					QShapeRingToothWidth * 0.5f * FMath::Max(Fade, 0.05f) / (2.0f * ConeExtent.Y), ToothLength / (2.0f * ConeExtent.Z));
				const FQuat ToothFacing = FRotationMatrix::MakeFromZ(ToothTip).ToQuat();
				const FVector ToothMiddle = Center + Rim * 0.9f * Half + ToothTip * (ToothLength * 0.5f);
				Shard->SetWorldLocationAndRotation(ToothMiddle - ToothFacing.RotateVector(ConeOrigin * ToothScale), ToothFacing);
				Shard->SetWorldScale3D(ToothScale);
				continue;
			}
			const FVector Radial = Rolled.RotateVector(FVector(FMath::Sin(Radians), -FMath::Cos(Radians), 0.0f));
			const FVector Tip = (-Wave.Direction * 0.85f + Radial * 0.35f + Normal * 0.12f).GetSafeNormal();
			const float Length = QIceCrestLength * Wave.CrestShape[Crest].Y * Size;
			const FVector Scale(QIceCrestWidth * Size / (2.0f * ConeExtent.X), QIceCrestWidth * 0.6f * Size / (2.0f * ConeExtent.Y),
				Length / (2.0f * ConeExtent.Z));
			const FQuat Facing = FRotationMatrix::MakeFromZ(Tip).ToQuat();
			// 원뿔 밑동을 날 위에 두고 끝이 뒤를 본다(경계 가운데가 날에서 길이 절반만큼 뒤).
			const FVector Middle = Center + Radial * ArcRadius + Tip * (Length * 0.5f);
			Shard->SetWorldLocationAndRotation(Middle - Facing.RotateVector(ConeOrigin * Scale), Facing);
			Shard->SetWorldScale3D(Scale);
		}
		// 날에서 얼음 부스러기가 뒤로 떨어져 나간다(바닥에 닿아 미끄러지다 멈춤 — ShardTick).
		if (bIce && Now >= Wave.NextShed && Fade > 0.3f)
		{
			Wave.NextShed = Now + QIceShedSeconds;
			// 파편 강화(QBlade 64)는 더 많이·크게·빛나는 얼음으로, 옆으로도 더 튀게
			const int32 ShedCount = Wave.bHeavy ? QBigShedCount : 2;
			const float ShedSize = Wave.bHeavy ? QBigShedSize : 1.0f;
			for (int32 Bit = 0; Bit < ShedCount; ++Bit)
			{
				const float Radians = FMath::DegreesToRadians(FMath::FRandRange(-55.0f, 55.0f));
				FAuroraShard Shard;
				Shard.FloorZ = Wave.Feet.Z + 3.0f;
				Shard.Start = Center + Rolled.RotateVector(FVector(FMath::Sin(Radians), -FMath::Cos(Radians), 0.0f)) * ArcRadius;
				Shard.Velocity = -Wave.Direction * FMath::FRandRange(60.0f, 160.0f) + FMath::VRand() * 60.0f * ShedSize + FVector(0.0f, 0.0f, 40.0f);
				Shard.Born = Now;
				Shard.Life = FMath::FRandRange(0.45f, 0.8f);
				const float Bitsize = FMath::FRandRange(4.0f, 8.0f) * ShedSize;
				Shard.Size = FVector(Bitsize, Bitsize * 0.6f, FMath::FRandRange(12.0f, 22.0f) * ShedSize);
				AddShard(Shard, Now, Wave.bHeavy ? GlowIceMaterial.LoadSynchronous() : nullptr);
			}
		}
	}
	for (int32 Index = CutMarks.Num() - 1; Index >= 0; --Index)
	{
		const FAuroraCutMark& Mark = CutMarks[Index];
		UStaticMeshComponent* Mesh = Mark.Mesh.Get();
		// 깨지는 때가 앞으로 잡혀 있으면(R 얼음 난무의 잠깐 남는 칼 빛) 그때까지는 그대로
		const float Faded = Mark.ShatterAt > 0.0 ? FMath::Max(static_cast<float>(Now - Mark.ShatterAt) / CutMarkFadeSeconds, 0.0f) : 0.0f;
		if (!IsValid(Mesh) || Faded >= 1.0f)
		{
			if (IsValid(Mesh))
			{
				RemoveTimedMesh(Mesh, nullptr);
			}
			CutMarks.RemoveAtSwap(Index);
			continue;
		}
		if (UMaterialInstanceDynamic* Dynamic = Mark.Material.Get())
		{
			// 칼이 지나가는 대로 아래에서 위로 그어지고(B 순서), 깨질 때 밝게 번쩍였다가 빠르게 사라진다.
			Dynamic->SetScalarParameterValue(TEXT("Reveal"), FMath::Clamp(static_cast<float>(Now - Mark.Born) / CutMarkDrawSeconds, 0.0f, 1.0f) * 1.1f);
			Dynamic->SetScalarParameterValue(TEXT("Fade"), Mark.ShatterAt > 0.0 ? 1.0f - Faded : 1.0f);
		}
	}
	if (Waves.IsEmpty() && CutMarks.IsEmpty())
	{
		GetWorld()->GetTimerManager().ClearTimer(BladeTimer);
	}
}

bool UAuroraSkillComponent::BeginFrostCross(const FVector& Aim)
{
	USkeletalMeshComponent* Mesh = Character.IsValid() ? Character->GetMesh() : nullptr;
	if (!Mesh || !Mesh->GetAnimInstance() || !CrossFirstAnimation || !CrossSecondAnimation || !GetWorld())
	{
		return RejectInput(TEXT("Unavailable"));
	}
	PrepareCast(EAuroraSkill::FrostSlash, Aim);
	bCrossCast = true;
	// 첫 칼(Fast_C) → FrostCrossSwitch초에 둘째 칼(Fast_B). 둘 다 칼이 가장 빠른 때에 벤다.
	PlayFullBody(CrossFirstAnimation);
	const uint32 Generation = CastGeneration;
	FTimerManager& Timers = GetWorld()->GetTimerManager();
	Timers.SetTimer(ActionTimer, FTimerDelegate::CreateUObject(this, &UAuroraSkillComponent::FrostCrossCut, Generation, 0),
		FrostCrossFirstCut, false);
	Timers.SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, [this, Generation]()
	{
		if (bCasting && Generation == CastGeneration)
		{
			PlayFullBody(CrossSecondAnimation);
		}
	}), FrostCrossSwitch, false);
	Timers.SetTimer(AddReleaseTimer(), FTimerDelegate::CreateUObject(this, &UAuroraSkillComponent::FrostCrossCut, Generation, 1),
		FrostCrossSwitch + FrostCrossSecondCut, false);
	Timers.SetTimer(RecoveryTimer, this, &UAuroraSkillComponent::FinishCast, FrostCrossSwitch + FrostCrossSecondEnd, false);
	UE_LOG(LogTemp, Display, TEXT("AURORA_CROSS cast aim=%s"), *Aim.ToCompactString());
	return true;
}

void UAuroraSkillComponent::FrostCrossCut(uint32 Generation, int32 Cut)
{
	if (!bCasting || !bCrossCast || Generation != CastGeneration || !Character.IsValid() || !GetWorld())
	{
		return;
	}
	const FVector Forward = Character->GetActorForwardVector().GetSafeNormal2D();
	const FVector Feet = GetFeetLocation();
	const double Now = GetWorld()->GetTimeSeconds();
	// 칼자국: 몸 앞 공중에 카메라를 보고 그어진다. 첫 칼 「\」(화면 오른쪽 아래 → 왼쪽 위) · 둘째 칼 「/」(왼쪽 아래 → 오른쪽 위).
	UMaterialInterface* Material = CutMarkMaterial.LoadSynchronous();
	const APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(GetWorld(), 0);
	if (PlaneMesh && Material && Camera)
	{
		const FRotationMatrix View(Camera->GetCameraRotation());
		const FVector Facing = -View.GetUnitAxis(EAxis::X);
		const float Tilt = FMath::DegreesToRadians(Cut == 0 ? -CutMarkTilt : CutMarkTilt);
		const FVector Stroke = View.GetUnitAxis(EAxis::Z) * FMath::Cos(Tilt) + View.GetUnitAxis(EAxis::Y) * FMath::Sin(Tilt);
		// 판 앞면(Z)이 카메라를, 그림 위쪽(-Y)이 칼이 나가는 쪽을 본다.
		const FQuat Rotation = FRotationMatrix::MakeFromZY(Facing, -Stroke).ToQuat();
		const FVector Center = Feet + Forward * CutMarkAhead + FVector(0.0f, 0.0f, CutMarkHeight);
		if (UStaticMeshComponent* Mesh = SpawnTimedMesh(PlaneMesh, FTransform(Rotation, Center,
			FVector(2.0f * CutMarkHalfWidth / 100.0f, CutMarkLength / 100.0f, 1.0f)), 3.0f))
		{
			UMaterialInstanceDynamic* Dynamic = UMaterialInstanceDynamic::Create(Material, Mesh);
			Dynamic->SetScalarParameterValue(TEXT("Reveal"), 0.0f);
			Mesh->SetMaterial(0, Dynamic);
			Mesh->SetCastShadow(false);
			Mesh->SetReceivesDecals(false);
			CutMarks.Add({Mesh, Dynamic, Now, 0.0});
			if (!GetWorld()->GetTimerManager().IsTimerActive(BladeTimer))
			{
				GetWorld()->GetTimerManager().SetTimer(BladeTimer, this, &UAuroraSkillComponent::BladeTick, 1.0f / 60.0f, true);
			}
		}
	}
	TArray<AActor*> Targets;
	GatherTargets(Feet, FrostCrossRange, Targets);
	const float MinDot = FMath::Cos(FMath::DegreesToRadians(FrostCrossHalfAngle));
	int32 Hits = 0;
	for (AActor* Target : Targets)
	{
		const FVector Offset = Target->GetActorLocation() - Character->GetActorLocation();
		if (FVector::DotProduct(Forward, Offset.GetSafeNormal2D()) < MinDot)
		{
			continue;
		}
		// 둘째 칼은 얼어 있는 적을 깨뜨려 2배(서리 검기와 같은 규칙)이고 뒤로 밀어낸다.
		const bool bFrozen = Cut == 1 && IsFrozen(Target);
		const float Damage = (Cut == 0 ? FrostCrossFirstDamage : FrostCrossSecondDamage) * (bFrozen ? FrostSlashFrozenMultiplier : 1.0f);
		if (Target->CanBeDamaged())
		{
			FHitResult Hit(Target, nullptr, Target->GetActorLocation(), -Forward);
			UGameplayStatics::ApplyPointDamage(Target, Damage, Forward, Hit, Character->GetController(), GetOwner(), nullptr);
		}
		SetStatus(Target, TEXT("SLOW"), FrostSlashSlowSeconds);
		if (bFrozen)
		{
			SpawnBurstLater(CryoExplode, Target->GetActorLocation(), 1.0f, 0.0f);
			FrozenUntil.Remove(Target);
		}
		if (Cut == 1)
		{
			PushTarget(Target, Forward, FrostCrossPush);
		}
		++Hits;
	}
	if (Cut == 1)
	{
		GetWorld()->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateUObject(this,
			&UAuroraSkillComponent::ShatterCutMarks), CutMarkShatterDelay, false);
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_CROSS cut=%d hits=%d"), Cut, Hits);
}

void UAuroraSkillComponent::ShatterCutMarks()
{
	if (!GetWorld() || !Character.IsValid())
	{
		return;
	}
	// X가 만난 자리에서 얼음 파편이 앞쪽으로 튀고 두 칼자국이 번쩍이며 사라진다. 시전이 이미 끝났어도 깨진다.
	const double Now = GetWorld()->GetTimeSeconds();
	int32 Marks = 0;
	for (FAuroraCutMark& Mark : CutMarks)
	{
		if (Mark.ShatterAt == 0.0)
		{
			Mark.ShatterAt = Now;
			++Marks;
		}
	}
	const FVector Forward = Character->GetActorForwardVector().GetSafeNormal2D();
	const FVector Feet = GetFeetLocation();
	SpawnImpactShards(Feet + Forward * CutMarkAhead + FVector(0.0f, 0.0f, CutMarkHeight), Forward, Feet.Z);
	UE_LOG(LogTemp, Display, TEXT("AURORA_CROSS shatter marks=%d"), Marks);
}

void UAuroraSkillComponent::SpawnSlashGround(const FVector& Feet, const FVector& Direction, float Range)
{
	// 바로 앞에 터지던 짙은 파란 충격파(IceShock)는 사용자 요청으로 뺐다(2026-10-18).
	// 대신 칼 궤적을 따라 바닥에 무언가가 파편과 같은 순서로 깔린다(2026-10-18 「Q가 빈약해졌다」). 모양은 시안(Aurora.FX.QGround):
	// 0 작은 얼음 결정이 솟았다 부서짐 · 1 흰색+얼음색 서리 자국(바닥 데칼) · 2 얼음 균열(바닥 데칼) ·
	// 3 새하얀 눈 덮임(바닥 데칼, 기본 — 10-19 균열이 「거미줄 같다」)
	const int32 Ground = CVarAuroraSlashGround.GetValueOnGameThread();
	for (int32 Index = 0; Index < SlashCrystalCount; ++Index)
	{
		const float Angle = -FrostSlashHalfAngle + 2.0f * FrostSlashHalfAngle * Index / (SlashCrystalCount - 1);
		const FVector Along = Direction.RotateAngleAxis(Angle, FVector::UpVector);
		const FVector Spot = Feet + Along * Range * SlashCrystalReach;
		GetWorld()->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, [this, Spot, Along, Ground]()
		{
			if (Ground == 0)
			{
				if (UParticleSystemComponent* Crystal = SpawnOwnedEffect(FreezeSegment, Spot, Along.Rotation()))
				{
					Crystal->SetWorldScale3D(FVector(SlashCrystalScale));
					ReleaseLater(Crystal, SlashCrystalSeconds, FreezeSegmentCrumble);
				}
				return;
			}
			// 장판용 고리는 끄고 둥근 자국만 겹쳐 궤적을 그린다.
			UMaterialInterface* Trail = nullptr;
			switch (Ground)
			{
			case 1:
				Trail = FrostTrailMaterial.LoadSynchronous();
				break;
			case 2:
				Trail = CrackFloorMaterial.LoadSynchronous();
				break;
			default:
				Trail = SnowCoverMaterial.LoadSynchronous();
				break;
			}
			// 장판용 값(고리 끄기)을 넣은 재질 사본을 먼저 만들어 그 사본으로 띄운다.
			UMaterialInstanceDynamic* Dynamic = Trail ? UMaterialInstanceDynamic::Create(Trail, this) : nullptr;
			if (Dynamic)
			{
				Dynamic->SetScalarParameterValue(TEXT("RingOpacity"), 0.0f);
				Dynamic->SetScalarParameterValue(TEXT("EdgeSharp"), 3.0f);
			}
			if (UDecalComponent* Mark = SpawnFloorDecal(Dynamic, Spot, SlashTrailRadius, SlashTrailSeconds, 0.05f, SlashTrailSeconds * 0.6f))
			{
				// 같은 그림이 일곱 번 나란히 찍혀 보이지 않게 자국마다 바닥 위에서 아무렇게나 돌린다.
				Mark->AddWorldRotation(FRotator(0.0f, FMath::FRandRange(0.0f, 360.0f), 0.0f));
			}
		}), 0.01f + SlashCrystalInterval * Index, false);
	}
}

void UAuroraSkillComponent::SpawnSlashFlakes(const FVector& Feet, const FVector& Direction, float Range, int32 Count, FVector2D Size,
	FVector2D Reach, FVector2D Life)
{
	UMaterialInterface* Material = FlakeMaterial.LoadSynchronous();
	if (!PlaneMesh || !Material || !GetWorld())
	{
		return;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	for (int32 Index = 0; Index < Count; ++Index)
	{
		// 부채꼴 안 아무 데서나, 검기 날(바깥쪽)에서 떠나 바깥·칼이 지나가는 쪽(오른쪽으로 도는 방향)·위로 날린다.
		// 검기가 그 자리를 지날 때 나타난다(왼쪽이 먼저).
		const float Alpha = FMath::FRand();
		const FVector Along = Direction.RotateAngleAxis(FMath::Lerp(-FrostSlashHalfAngle, FrostSlashHalfAngle, Alpha), FVector::UpVector);
		const FVector Tangent = Along.RotateAngleAxis(90.0f, FVector::UpVector);
		FAuroraFlake Flake;
		Flake.Start = Feet + Along * Range * FMath::FRandRange(Reach.X, Reach.Y) + FVector(0.0f, 0.0f, FMath::FRandRange(25.0f, 80.0f));
		Flake.Velocity = Along * SlashFlakeOutSpeed * FMath::FRandRange(0.5f, 1.2f) + Tangent * SlashFlakeSweepSpeed * FMath::FRandRange(0.2f, 1.2f)
			+ FVector(0.0f, 0.0f, SlashFlakeUpSpeed * FMath::FRandRange(0.3f, 1.0f));
		const float SwayAngle = FMath::FRandRange(0.0f, 2.0f * PI);
		Flake.Sway = FVector(FMath::Cos(SwayAngle), FMath::Sin(SwayAngle), 0.0f);
		Flake.Born = Now + SlashSweepSeconds * Alpha;
		Flake.Life = FMath::FRandRange(Life.X, Life.Y);
		Flake.Size = FMath::FRandRange(Size.X, Size.Y);
		Flake.SwayRate = FMath::FRandRange(1.5f, 3.0f);
		Flake.SwayPhase = FMath::FRandRange(0.0f, 2.0f * PI);
		Flake.Spin = FMath::FRandRange(0.0f, 360.0f);
		Flake.SpinRate = FMath::FRandRange(-360.0f, 360.0f);
		UStaticMeshComponent* Mesh = SpawnTimedMesh(PlaneMesh, FTransform(FRotator::ZeroRotator, Flake.Start, FVector(0.001f)),
			static_cast<float>(Flake.Born - Now) + Flake.Life + 0.05f);
		if (!Mesh)
		{
			continue;
		}
		Mesh->SetMaterial(0, Material);
		Mesh->SetCastShadow(false);
		Flake.Mesh = Mesh;
		Flakes.Add(Flake);
	}
	if (!GetWorld()->GetTimerManager().IsTimerActive(FlakeTimer))
	{
		GetWorld()->GetTimerManager().SetTimer(FlakeTimer, this, &UAuroraSkillComponent::FlakeTick, 1.0f / 60.0f, true);
	}
	FlakeTick();
}

void UAuroraSkillComponent::FlakeTick()
{
	if (!GetWorld())
	{
		return;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	// 판 앞면이 게임 카메라를 보게 세운다(위에서 비스듬히 내려다보므로 바닥에 눕히면 얇게 보인다).
	FVector Facing = FVector::UpVector;
	if (const APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(GetWorld(), 0))
	{
		Facing = -Camera->GetCameraRotation().Vector();
	}
	const FQuat Face = FRotationMatrix::MakeFromZ(Facing).ToQuat();
	for (int32 Index = Flakes.Num() - 1; Index >= 0; --Index)
	{
		const FAuroraFlake& Flake = Flakes[Index];
		UStaticMeshComponent* Mesh = Flake.Mesh.Get();
		const float Age = static_cast<float>(Now - Flake.Born);
		// 메시는 SpawnTimedMesh가 사는 시간 뒤에 치운다.
		if (!IsValid(Mesh) || Age >= Flake.Life)
		{
			Flakes.RemoveAtSwap(Index);
			continue;
		}
		if (Age < 0.0f)
		{
			continue;
		}
		// 공기 저항으로 점점 느려지며 날아가다 천천히 떨어지고, 옆으로 하늘하늘 흔들린다.
		const float Drift = (1.0f - FMath::Exp(-SlashFlakeDrag * Age)) / SlashFlakeDrag;
		const FVector Position = Flake.Start + Flake.Velocity * Drift - FVector(0.0f, 0.0f, 0.5f * SlashFlakeGravity * Age * Age)
			+ Flake.Sway * FMath::Sin(2.0f * PI * Flake.SwayRate * Age + Flake.SwayPhase) * SlashFlakeFlutter;
		const float Grow = FMath::Clamp(Age / 0.08f, 0.0f, 1.0f);
		const float Shrink = FMath::Clamp((Flake.Life - Age) / (Flake.Life * 0.4f), 0.0f, 1.0f);
		const FQuat Spin(Facing, FMath::DegreesToRadians(Flake.Spin + Flake.SpinRate * Age));
		Mesh->SetWorldLocationAndRotation(Position, Spin * Face);
		Mesh->SetWorldScale3D(FVector(FMath::Max(Flake.Size / 100.0f * Grow * Shrink, 0.001f)));
	}
	if (Flakes.IsEmpty())
	{
		GetWorld()->GetTimerManager().ClearTimer(FlakeTimer);
	}
}

void UAuroraSkillComponent::SpawnSlashShards(const FVector& Feet, const FVector& Direction, float Range)
{
	if (!BladeMesh || !GetWorld())
	{
		return;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	for (int32 Index = 0; Index < SlashShardCount; ++Index)
	{
		// 검기 날(반경 0.7~0.8)에서 떠나 바깥·칼이 지나가는 쪽으로 세게 튀고 위로 짧게 솟는다. 검기가 그 자리를 지날 때 나타난다.
		const float Alpha = (Index + FMath::FRandRange(0.0f, 1.0f)) / SlashShardCount;
		const FVector Along = Direction.RotateAngleAxis(FMath::Lerp(-FrostSlashHalfAngle, FrostSlashHalfAngle, Alpha), FVector::UpVector);
		const FVector Tangent = Along.RotateAngleAxis(90.0f, FVector::UpVector);
		FAuroraShard Shard;
		Shard.FloorZ = Feet.Z + 3.0f;
		Shard.Start = Feet + Along * Range * FMath::FRandRange(0.7f, 0.8f) + FVector(0.0f, 0.0f, FMath::FRandRange(15.0f, 45.0f));
		Shard.Velocity = Along * SlashShardOutSpeed * FMath::FRandRange(0.5f, 1.2f) + Tangent * SlashShardSweepSpeed * FMath::FRandRange(0.3f, 1.2f)
			+ FVector(0.0f, 0.0f, SlashShardUpSpeed * FMath::FRandRange(0.4f, 1.0f));
		Shard.Born = Now + SlashSweepSeconds * Alpha;
		Shard.Life = FMath::FRandRange(SlashShardMinLife, SlashShardMaxLife);
		const float Width = FMath::FRandRange(SlashShardMinWidth, SlashShardMaxWidth);
		Shard.Size = FVector(Width, Width * FMath::FRandRange(0.4f, 0.7f), FMath::FRandRange(SlashShardMinLength, SlashShardMaxLength));
		AddShard(Shard, Now);
	}
	ShardTick();
}

void UAuroraSkillComponent::SpawnImpactShards(const FVector& Where, const FVector& Direction, float FloorZ)
{
	if (!BladeMesh || !GetWorld())
	{
		return;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	for (int32 Index = 0; Index < LanceShardCount; ++Index)
	{
		// 꽂힌 자리에서 나던 쪽 부채꼴(±LanceShardSpread도)로 튀고 위로 솟았다가 떨어져 미끄러진다. 크기는 Q 파편보다 조금 작게.
		const FVector Along = Direction.RotateAngleAxis(FMath::FRandRange(-LanceShardSpread, LanceShardSpread), FVector::UpVector);
		FAuroraShard Shard;
		Shard.FloorZ = FloorZ + 3.0f;
		Shard.Start = Where + FMath::VRand() * 10.0f;
		Shard.Velocity = (Along * LanceShardSpeed * FMath::FRandRange(0.4f, 1.2f) + FVector(0.0f, 0.0f, LanceShardUpSpeed * FMath::FRandRange(0.3f, 1.0f)))
			* LanceImpactScale;
		Shard.Born = Now;
		Shard.Life = FMath::FRandRange(SlashShardMinLife, SlashShardMaxLife);
		const float Width = FMath::FRandRange(SlashShardMinWidth, SlashShardMaxWidth) * 0.85f;
		Shard.Size = FVector(Width, Width * FMath::FRandRange(0.4f, 0.7f), FMath::FRandRange(SlashShardMinLength, SlashShardMaxLength) * 0.8f)
			* LanceImpactScale;
		AddShard(Shard, Now);
	}
	ShardTick();
}

void UAuroraSkillComponent::SpawnShatterShards(const FVector& Feet, float Height, int32 Count, float Speed, float UpSpeed, float SizeScale)
{
	if (!BladeMesh || !GetWorld())
	{
		return;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	for (int32 Index = 0; Index < Count; ++Index)
	{
		// 높이 곳곳에서 고르게 돌아가며 바깥으로 튀고 위로 솟았다가 떨어져 미끄러진다.
		const FVector Out = FVector::ForwardVector.RotateAngleAxis(360.0f * (Index + FMath::FRand()) / Count, FVector::UpVector);
		FAuroraShard Shard;
		Shard.FloorZ = Feet.Z + 3.0f;
		Shard.Start = Feet + Out * 15.0f + FVector(0.0f, 0.0f, Height * FMath::FRandRange(0.15f, 0.85f));
		Shard.Velocity = Out * Speed * FMath::FRandRange(0.5f, 1.2f) + FVector(0.0f, 0.0f, UpSpeed * FMath::FRandRange(0.3f, 1.0f));
		Shard.Born = Now;
		Shard.Life = FMath::FRandRange(SlashShardMinLife, SlashShardMaxLife);
		const float Width = FMath::FRandRange(SlashShardMinWidth, SlashShardMaxWidth) * SizeScale;
		Shard.Size = FVector(Width, Width * FMath::FRandRange(0.4f, 0.7f), FMath::FRandRange(SlashShardMinLength, SlashShardMaxLength) * SizeScale);
		AddShard(Shard, Now);
	}
	ShardTick();
}

void UAuroraSkillComponent::AddShard(FAuroraShard Shard, double Now, UMaterialInterface* Material)
{
	// 원뿔 끝(+Z)을 아무 쪽으로나 둔 채 아무 축으로나 빠르게 굴러간다.
	Shard.Facing = FRotator(FMath::FRandRange(-180.0f, 180.0f), FMath::FRandRange(0.0f, 360.0f), FMath::FRandRange(-180.0f, 180.0f)).Quaternion();
	Shard.SpinAxis = FMath::VRand();
	Shard.SpinRate = FMath::FRandRange(540.0f, 1080.0f) * (FMath::RandBool() ? 1.0f : -1.0f);
	const FVector Extent = BladeMesh->GetBounds().BoxExtent;
	const FVector Scale(Shard.Size.X / FMath::Max(2.0f * Extent.X, 1.0f), Shard.Size.Y / FMath::Max(2.0f * Extent.Y, 1.0f),
		Shard.Size.Z / FMath::Max(2.0f * Extent.Z, 1.0f));
	UStaticMeshComponent* Mesh = SpawnTimedMesh(BladeMesh, FTransform(Shard.Facing, Shard.Start, Scale * 0.001f),
		static_cast<float>(Shard.Born - Now) + Shard.Life + 0.05f);
	if (!Mesh)
	{
		return;
	}
	if (UMaterialInterface* Look = Material ? Material : BladeMaterial.Get())
	{
		Mesh->SetMaterial(0, Look);
	}
	Mesh->SetCastShadow(false);
	Shard.Mesh = Mesh;
	Shards.Add(Shard);
	if (!GetWorld()->GetTimerManager().IsTimerActive(ShardTimer))
	{
		GetWorld()->GetTimerManager().SetTimer(ShardTimer, this, &UAuroraSkillComponent::ShardTick, 1.0f / 60.0f, true);
	}
}

void UAuroraSkillComponent::SpawnRuptureSpikes(const FVector& Spot, const FVector& Direction)
{
	if (!BladeMesh || !GetWorld())
	{
		return;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	const FVector Right(-Direction.Y, Direction.X, 0.0f);
	for (int32 Index = 0; Index < RuptureSpikesPerStep; ++Index)
	{
		// 가운데 하나는 줄 위에서 높고 곧게, 나머지는 양옆에서 낮게 바깥·앞으로 기울어 솟는다.
		const bool bMiddle = Index == 0;
		const float Side = bMiddle ? FMath::FRandRange(-0.3f, 0.3f) : (Index % 2 == 1 ? 1.0f : -1.0f) * FMath::FRandRange(0.6f, 1.0f);
		const FVector Lean = Right * Side * (bMiddle ? 0.15f : FMath::FRandRange(0.35f, 0.6f)) + Direction * FMath::FRandRange(0.0f, 0.3f);
		const FVector Axis = (FVector::UpVector + Lean).GetSafeNormal();
		FAuroraRuptureSpike Spike;
		Spike.Base = Spot + Right * Side * RuptureSpikeSpread + Direction * FMath::FRandRange(-25.0f, 25.0f);
		Spike.Height = bMiddle ? FMath::FRandRange(RuptureSpikeMaxHeight * 0.75f, RuptureSpikeMaxHeight)
			: FMath::FRandRange(RuptureSpikeMinHeight, RuptureSpikeMinHeight * 1.5f);
		Spike.Width = Spike.Height * FMath::FRandRange(0.28f, 0.36f);
		// 원뿔 끝(+Z)이 솟는 축을 보고, 납작한 쪽은 아무 데나 돌린다(둥근 기둥이 아니라 얼음 결정처럼 보이게)
		Spike.Facing = FQuat(Axis, FMath::FRandRange(0.0f, 2.0f * PI)) * FRotationMatrix::MakeFromZX(Axis, Direction).ToQuat();
		Spike.Born = Now + FMath::FRandRange(0.0f, 0.03f);
		Spike.Life = RuptureSpikeSeconds * FMath::FRandRange(0.9f, 1.1f);
		UStaticMeshComponent* Mesh = SpawnTimedMesh(BladeMesh, FTransform(Spike.Facing, Spike.Base, FVector(0.001f)),
			static_cast<float>(Spike.Born - Now) + Spike.Life + 0.05f);
		if (!Mesh)
		{
			continue;
		}
		if (BladeMaterial)
		{
			Mesh->SetMaterial(0, BladeMaterial);
		}
		Mesh->SetCastShadow(false);
		// 바닥 데칼(D 시안 2·3 갈라진 자국)이 가시 표면에 비치지 않게
		Mesh->SetReceivesDecals(false);
		Spike.Mesh = Mesh;
		RuptureSpikes.Add(Spike);
	}
	if (!GetWorld()->GetTimerManager().IsTimerActive(RuptureSpikeTimer))
	{
		GetWorld()->GetTimerManager().SetTimer(RuptureSpikeTimer, this, &UAuroraSkillComponent::RuptureSpikeTick, 1.0f / 60.0f, true);
	}
	RuptureSpikeTick();
}

void UAuroraSkillComponent::RuptureSpikeTick()
{
	if (!GetWorld())
	{
		return;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	const FBoxSphereBounds Bounds = BladeMesh ? BladeMesh->GetBounds() : FBoxSphereBounds(FVector::ZeroVector, FVector(50.0f), 50.0f);
	for (int32 Index = RuptureSpikes.Num() - 1; Index >= 0; --Index)
	{
		const FAuroraRuptureSpike& Spike = RuptureSpikes[Index];
		UStaticMeshComponent* Mesh = Spike.Mesh.Get();
		const float Age = static_cast<float>(Now - Spike.Born);
		if (!IsValid(Mesh) || Age >= Spike.Life)
		{
			RuptureSpikes.RemoveAtSwap(Index);
			continue;
		}
		if (Age < 0.0f)
		{
			continue;
		}
		// 바닥 아래에 묻힌 채 축을 따라 밀려 올라온다(RuptureSpikeRiseSeconds에 끝까지, 처음이 빠름) → 끝 RuptureSpikeSinkSeconds 동안
		// 도로 들어간다. Out = 바닥 위로 나온 몫(0 = 끝이 바닥에 닿음, 1 = 밑동이 바닥).
		const float Rise = FMath::Clamp(Age / RuptureSpikeRiseSeconds, 0.0f, 1.0f);
		const float Sink = FMath::Clamp((Spike.Life - Age) / RuptureSpikeSinkSeconds, 0.0f, 1.0f);
		const float Out = (1.0f - FMath::Pow(1.0f - Rise, 3.0f)) * FMath::InterpEaseInOut(0.0f, 1.0f, Sink, 2.0f);
		const FVector Scale(Spike.Width / FMath::Max(2.0f * Bounds.BoxExtent.X, 1.0f), Spike.Width * 0.75f / FMath::Max(2.0f * Bounds.BoxExtent.Y, 1.0f),
			Spike.Height / FMath::Max(2.0f * Bounds.BoxExtent.Z, 1.0f));
		const FVector Axis = Spike.Facing.GetAxisZ();
		// 메시 경계 가운데(Bounds.Origin)가 원뿔 높이의 가운데다
		const FVector Centre = Spike.Base + Axis * Spike.Height * (Out - 0.5f) - Spike.Facing.RotateVector(Bounds.Origin * Scale);
		Mesh->SetWorldLocationAndRotation(Centre, Spike.Facing);
		Mesh->SetWorldScale3D(Out > 0.01f ? Scale : FVector(0.001f));
	}
	if (RuptureSpikes.IsEmpty())
	{
		GetWorld()->GetTimerManager().ClearTimer(RuptureSpikeTimer);
	}
}

float UAuroraSkillComponent::FindFloorZ(const FVector& From, float Fallback) const
{
	if (!GetWorld())
	{
		return Fallback;
	}
	FCollisionQueryParams Query(SCENE_QUERY_STAT(AuroraFloor), false, GetOwner());
	FHitResult Hit;
	return GetWorld()->LineTraceSingleByObjectType(Hit, From + FVector(0.0f, 0.0f, 50.0f), From - FVector(0.0f, 0.0f, 600.0f),
		FCollisionObjectQueryParams(ECC_WorldStatic), Query) ? Hit.ImpactPoint.Z : Fallback;
}

void UAuroraSkillComponent::ShardTick()
{
	if (!GetWorld())
	{
		return;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	for (int32 Index = Shards.Num() - 1; Index >= 0; --Index)
	{
		const FAuroraShard& Shard = Shards[Index];
		UStaticMeshComponent* Mesh = Shard.Mesh.Get();
		const float Age = static_cast<float>(Now - Shard.Born);
		if (!IsValid(Mesh) || Age >= Shard.Life)
		{
			Shards.RemoveAtSwap(Index);
			continue;
		}
		if (Age < 0.0f)
		{
			continue;
		}
		// 포물선으로 날다가 바닥(FloorZ)에 닿은 뒤로는 바닥 위를 미끄러지며 멈추고 구르기도 멈춘다.
		const float Rise = Shard.Start.Z - Shard.FloorZ;
		const float Land = (Shard.Velocity.Z + FMath::Sqrt(FMath::Square(Shard.Velocity.Z) + 2.0f * SlashShardGravity * FMath::Max(Rise, 0.0f)))
			/ SlashShardGravity;
		const float Flight = FMath::Min(Age, Land);
		const float Slide = FMath::Max(Age - Land, 0.0f);
		const FVector Flat(Shard.Velocity.X, Shard.Velocity.Y, 0.0f);
		FVector Position = Shard.Start + Flat * Flight + FVector(0.0f, 0.0f, Shard.Velocity.Z * Flight - 0.5f * SlashShardGravity * Flight * Flight);
		Position += Flat * 0.35f * (1.0f - FMath::Exp(-SlashShardSlideDrag * Slide)) / SlashShardSlideDrag;
		Position.Z = FMath::Max(Position.Z, Shard.FloorZ);
		const FQuat Tumble(Shard.SpinAxis, FMath::DegreesToRadians(Shard.SpinRate * Flight));
		// 금방 커지고, 끝 0.25초 동안 작아지며 사라진다.
		const float Grow = FMath::Clamp(Age / 0.05f, 0.0f, 1.0f);
		const float Shrink = FMath::Clamp((Shard.Life - Age) / 0.25f, 0.0f, 1.0f);
		const FVector Extent = BladeMesh ? BladeMesh->GetBounds().BoxExtent : FVector(50.0f);
		const FVector Scale(Shard.Size.X / FMath::Max(2.0f * Extent.X, 1.0f), Shard.Size.Y / FMath::Max(2.0f * Extent.Y, 1.0f),
			Shard.Size.Z / FMath::Max(2.0f * Extent.Z, 1.0f));
		Mesh->SetWorldLocationAndRotation(Position, Tumble * Shard.Facing);
		Mesh->SetWorldScale3D(Scale * FMath::Max(Grow * Shrink, 0.001f));
	}
	if (Shards.IsEmpty())
	{
		GetWorld()->GetTimerManager().ClearTimer(ShardTimer);
	}
}

UDecalComponent* UAuroraSkillComponent::SweepFloorDecal(UMaterialInterface* Material, const FVector& Center, const FVector& Facing,
	float Radius, float Seconds, float SweepSeconds, float Width, float FadeOut)
{
	// 값을 바꿀 재질 사본을 먼저 만들어 그 사본으로 데칼을 띄운다(첫 장면부터 Reveal 0으로 숨겨진 채 나온다).
	UMaterialInstanceDynamic* Dynamic = Material ? UMaterialInstanceDynamic::Create(Material, this) : nullptr;
	if (!Dynamic)
	{
		return nullptr;
	}
	// Reveal을 0에서 1.1까지 SweepSeconds 동안 여덟 번에 나눠 올린다(1을 조금 넘겨 끝자락까지 다 보이게).
	Dynamic->SetScalarParameterValue(TEXT("RevealInvert"), SweepRevealInvert);
	Dynamic->SetScalarParameterValue(TEXT("Reveal"), 0.0f);
	UDecalComponent* Decal = SpawnFloorDecal(Dynamic, Center, Radius, Seconds, 0.0f, FadeOut >= 0.0f ? FadeOut : Seconds * 0.5f, Width);
	if (!Decal)
	{
		return nullptr;
	}
	Decal->AddWorldRotation(FRotator(0.0f, Facing.Rotation().Yaw + SweepDecalYawOffset, 0.0f));
	RampReveal(Dynamic, SweepSeconds);
	return Decal;
}

void UAuroraSkillComponent::RampReveal(UMaterialInstanceDynamic* Dynamic, float SweepSeconds, int32 Steps)
{
	if (!Dynamic || !GetWorld())
	{
		return;
	}
	TWeakObjectPtr<UMaterialInstanceDynamic> Weak = Dynamic;
	for (int32 Step = 1; Step <= Steps; ++Step)
	{
		const float Alpha = static_cast<float>(Step) / Steps;
		GetWorld()->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, [Weak, Alpha]()
		{
			if (UMaterialInstanceDynamic* Instance = Weak.Get())
			{
				Instance->SetScalarParameterValue(TEXT("Reveal"), Alpha * 1.1f);
			}
		}), SweepSeconds * Alpha, false);
	}
}

void UAuroraSkillComponent::ExecuteFrostField()
{
	// 채널링(사용자 제안 승인 2026-10-18): 칼을 들어 올린 자세로 서 있는 동안 FieldBurstInterval마다 장판 안에 얼음 파편이
	// 튀고(안의 적 전부에 피해·감속), FieldChannelSeconds를 다 버티면 마지막에 얼린다. 움직이거나 다른 키를 누르면 끊긴다.
	FieldStartedAt = GetWorld()->GetTimeSeconds();
	FieldBurstsDone = 0;
	FieldNextGlowAt = FieldStartedAt;
	// 시안 7·8: 시전부터 이어 온 동작에서 손이 처음 다 뻗는 순간에도 터진다. 8은 손이 끝까지 나간 때(FieldPulseOut)부터 앞뒤로 오간다.
	// 시안 9: 칼질마다 터진다(동작 시각 FieldCarveBursts — 버티기는 동작 ActionTime초에 시작한다).
	FieldStyle = CVarAuroraFieldChannel.GetValueOnGameThread();
	const float ActionTime = Skills[EAuroraSkill::FrostField].ActionTime;
	const bool bThrusting = FieldStyle == 7 || FieldStyle == 8;
	FieldThrusts = 0;
	FieldThrustBurstAt = bThrusting ? FieldStartedAt + (FieldReachPeakTime - FieldSliceOpenStart) - ActionTime : 0.0;
	FieldNextThrustAt = FieldStyle == 7 ? FieldStartedAt + FieldThrustFirst : 0.0;
	FieldPulseStartedAt = FieldStyle == 8 ? FieldStartedAt + (FieldPulseOut - FieldSliceOpenStart) - ActionTime : 0.0;
	FieldCarveIndex = 0;
	FieldVisual = CVarAuroraFieldVortex.GetValueOnGameThread();
	FieldLastTick = FieldStartedAt;
	// 버티는 자세 시안(Aurora.FX.RChannel): 0 칼을 곧게 들어 올림 · 1 칼을 앞으로 겨눔 · 2 휘둘러 가리키는 동작(Cast)을 두 번 ·
	// 3 칼을 땅에 꽂고 무릎 꿇은 채 버팀(원작 귀환 채널링 Recall의 1.45초부터, 10-19 오후까지 기본 — 0~2는 「딴 거 없어?」로 바꿈) ·
	// 4~6 칼을 내리고 왼손을 앞으로 뻗어 버팀(Emote_Slice — 4 손이 나가는 곳부터 · 5 칼을 그어서 · 6 시전부터 한 동작, BeginCast가 튼다) ·
	// 7 = 6 + 버티는 동안 손을 거듭 뻗으며 크게 터짐(기본, FrostFieldTick) · 8 = 7을 몸이 튀지 않게 · 9 칼로 얼음 깎기(BeginCast가 튼다)
	switch (FieldStyle)
	{
	case 3:
		// Recall(10-20 A가 Level_Start로 바뀌어 같은 Recall을 쓰는 D 것을 쓰다가, 10-26 D가 옛 궁극기로 바뀌어 따로 불러 둔다)
		PlayFullBody(FieldKneelAnimation, 1.0f, FieldKneelStart);
		break;
	case 4:
		PlayFullBody(FieldReachAnimation, FieldReachRate, FieldReachStart);
		break;
	case 5:
		PlayFullBody(FieldReachAnimation, 1.0f, FieldSlashStart);
		break;
	case 6:
	case 7:
	case 8:
	case 9:
		break;
	case 1:
		PlayFullBody(FieldAimAnimation, 1.0f, 0.0f, FieldChannelLoops);
		break;
	case 2:
		if (UAnimSequence* Wave = Skills[EAuroraSkill::FrostField].Animation)
		{
			PlayFullBody(Wave, Wave->GetPlayLength() * 2.0f / FieldChannelSeconds, 0.0f, 2);
		}
		break;
	default:
		PlayFullBody(FieldChannelAnimation, 1.0f, 0.0f, FieldChannelLoops);
		break;
	}
	if (FieldVisual == 1)
	{
		// 회오리: 장판 바닥엔 옅은 서리 원을 깔고 그 위에 얼음 파편 기둥을 세운다(시작 충격파는 연기가 피어 뺀다).
		if (UDecalComponent* Floor = SpawnFloorDecal(FrostTrailMaterial.LoadSynchronous(), FieldCenter, FieldRadius, FieldChannelSeconds + 0.4f,
			0.25f, 0.4f))
		{
			if (UMaterialInstanceDynamic* Faint = Floor->CreateDynamicMaterialInstance())
			{
				Faint->SetScalarParameterValue(TEXT("FillOpacity"), VortexFloorFill);
				Faint->SetScalarParameterValue(TEXT("RingOpacity"), VortexFloorRing);
			}
		}
		SpawnVortex();
	}
	else
	{
		SpawnBurstLater(IceShock, FieldCenter, 0.7f, 0.0f);
	}
	// 1초에 60번 — 시안 8이 동작 시각을 매번 옮겨서(30번이면 팔이 30장면으로 끊겨 보인다). 나머지는 시각으로 세어 횟수와 상관없다.
	GetWorld()->GetTimerManager().SetTimer(FieldTimer, this, &UAuroraSkillComponent::FrostFieldTick, 1.0f / 60.0f, true);
	UE_LOG(LogTemp, Display, TEXT("AURORA_FIELD start at=%s bursts=%d seconds=%.1f"), *FieldCenter.ToCompactString(),
		FieldBurstCount, FieldChannelSeconds);
}

bool UAuroraSkillComponent::IsFieldChannelling() const
{
	return GetWorld() && GetWorld()->GetTimerManager().IsTimerActive(FieldTimer);
}

void UAuroraSkillComponent::CancelFrostChannel(const TCHAR* Reason)
{
	if (!IsFieldChannelling())
	{
		return;
	}
	GetWorld()->GetTimerManager().ClearTimer(FieldTimer);
	UE_LOG(LogTemp, Display, TEXT("AURORA_FIELD cancelled reason=%s bursts=%d"), Reason, FieldBurstsDone);
	if (FieldVisual == 1)
	{
		CollapseVortex(false);
	}
	if (bCasting && ActiveSkill == EAuroraSkill::FrostField)
	{
		FinishCast();
	}
}

void UAuroraSkillComponent::FrostFieldTick()
{
	if (!GetWorld() || !Character.IsValid())
	{
		return;
	}
	// 움직이거나(오른쪽 버튼) 평타(왼쪽 버튼)를 누르면 끊긴다. 다른 스킬 키는 TryUseSkillSlot에서 끊는다.
	// 공용 입력(KwangPlayerController)은 시전 중 이동을 그냥 버리므로 여기서 버튼 상태를 직접 본다.
	if (const APlayerController* Player = Cast<APlayerController>(Character->GetController()))
	{
		if (Player->IsInputKeyDown(EKeys::RightMouseButton) || Player->IsInputKeyDown(EKeys::LeftMouseButton))
		{
			CancelFrostChannel(TEXT("input"));
			return;
		}
	}
	const double Now = GetWorld()->GetTimeSeconds();
	// 회오리(RField 1)는 장판 안 적을 매 장면 가운데로 끌어당긴다.
	if (FieldVisual == 1)
	{
		PullIntoVortex(static_cast<float>(Now - FieldLastTick));
	}
	FieldLastTick = Now;
	// 냉기 빛은 약 1초에 사그라들어 1초마다 다시 깐다(회오리는 서리 원이 장판을 보여 준다).
	if (FieldVisual != 1 && Now >= FieldNextGlowAt)
	{
		FieldNextGlowAt = Now + 1.0;
		SpawnBurstLater(IceChargeGlow, FieldCenter, 1.6f, 0.0f);
	}
	// 시안 7: 손을 거둬들였다가 다시 뻗고(끝나기 FieldThrustPeak초 전까지만 새로 뻗는다), 손이 다 뻗은 순간 장판 안에서 크게 터진다.
	if (FieldNextThrustAt > 0.0 && Now >= FieldNextThrustAt)
	{
		FieldNextThrustAt = Now - FieldStartedAt + FieldThrustInterval + FieldThrustPeak < FieldChannelSeconds ? Now + FieldThrustInterval : 0.0;
		PlayFullBody(FieldReachAnimation, FieldThrustRate, FieldThrustStart, 1, FieldThrustBlendIn);
		FieldThrustBurstAt = Now + FieldThrustPeak;
		++FieldThrusts;
	}
	// 시안 8: 손이 끝까지 나간 뒤로는 몽타주를 멈춰 두고 동작 시각을 직접 옮긴다 — 한 번(FieldPulseBackSeconds + FieldPulseOutSeconds)에
	// 손을 FieldPulseBack 자세까지 부드럽게 거뒀다가 FieldPulseOut 자세로 빠르게 내밀고, 다 내민 순간 터진다. 버티기 끝까지 다 못 도는
	// 마지막 한 번은 하지 않고 내민 채 버틴다.
	USkeletalMeshComponent* BodyMesh = Character->GetMesh();
	UAnimInstance* Anim = BodyMesh ? BodyMesh->GetAnimInstance() : nullptr;
	if (FieldStyle == 8 && FieldPulseStartedAt > 0.0 && Now >= FieldPulseStartedAt && Anim && ActiveMontage)
	{
		const float Period = FieldPulseBackSeconds + FieldPulseOutSeconds;
		const float Elapsed = static_cast<float>(Now - FieldPulseStartedAt);
		const int32 Cycles = FMath::FloorToInt((FieldChannelSeconds - static_cast<float>(FieldPulseStartedAt - FieldStartedAt)) / Period);
		const int32 Cycle = FMath::FloorToInt(Elapsed / Period);
		const float Into = Elapsed - Cycle * Period;
		float Position = FieldPulseOut;
		if (Cycle < Cycles)
		{
			Position = Into < FieldPulseBackSeconds
				? FMath::Lerp(FieldPulseOut, FieldPulseBack, FMath::SmoothStep(0.0f, 1.0f, Into / FieldPulseBackSeconds))
				: FMath::Lerp(FieldPulseBack, FieldPulseOut, 1.0f - FMath::Square(1.0f - (Into - FieldPulseBackSeconds) / FieldPulseOutSeconds));
		}
		if (Anim->Montage_GetPlayRate(ActiveMontage) != 0.0f)
		{
			Anim->Montage_SetPlayRate(ActiveMontage, 0.0f);
		}
		Anim->Montage_SetPosition(ActiveMontage, Position);
		// 다 돈 횟수만큼 터진다(처음 손이 다 뻗을 때의 한 번은 FieldThrusts 0번째)
		if (FMath::Min(Cycle, Cycles) > FieldThrusts && FieldThrustBurstAt == 0.0)
		{
			++FieldThrusts;
			FieldThrustBurstAt = Now;
		}
	}
	// 시안 9: 다음 칼질 때를 걸어 둔다.
	if (FieldStyle == 9 && FieldThrustBurstAt == 0.0 && FieldCarveIndex < UE_ARRAY_COUNT(FieldCarveBursts))
	{
		FieldThrustBurstAt = FieldStartedAt + FieldCarveBursts[FieldCarveIndex++] - Skills[EAuroraSkill::FrostField].ActionTime;
		++FieldThrusts;
	}
	if (FieldThrustBurstAt > 0.0 && Now >= FieldThrustBurstAt)
	{
		FieldThrustBurstAt = 0.0;
		FVector Ground = FieldCenter;
		if (FieldStyle == 9)
		{
			// 시안 9(10-19 밤 「칼 휘두를 때마다 캐릭터 쪽에 이펙트가 있고 휘두를 때 해당 지점이 터지는 방식」): 칼질마다 발밑에서 장판 쪽으로
			// 초승달 검기가 휩쓸고 칼 쥔 손에서 서리가 장판 쪽으로 뿜어진 뒤(FieldCarveBurstDelay), 겨눈 자리(장판 가운데)가 크게 터진다.
			const FVector Feet = GetFeetLocation();
			FVector Toward = (FieldCenter - Feet).GetSafeNormal2D();
			if (Toward.IsNearlyZero())
			{
				Toward = Character->GetActorForwardVector().GetSafeNormal2D();
			}
			SweepFloorDecal(SlashArcMaterial.LoadSynchronous(), Feet, Toward, FieldCarveArcRadius, FieldCarveArcSeconds, SlashSweepSeconds);
			const USkeletalMeshComponent* Body = Character->GetMesh();
			SpawnBurstLater(SlashSparkles, Body ? Body->GetSocketLocation(TEXT("hand_r")) : Character->GetActorLocation(), FieldCarveSparkleScale,
				0.0f, Toward.Rotation());
			if (FieldVisual == 1)
			{
				// 회오리: 겨눈 자리가 터지는 대신 회오리가 한 단 빨라지고 굵어진다.
				GetWorld()->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateUObject(this,
					&UAuroraSkillComponent::VortexStageUp), FieldCarveBurstDelay, false);
			}
			else
			{
				SpawnBurstLater(IceShards, Ground, FieldCarveBurstScale, FieldCarveBurstDelay);
				SpawnBurstLater(IceShock, Ground, FieldCarveShockScale, FieldCarveBurstDelay);
			}
		}
		else if (FieldVisual == 1)
		{
			VortexStageUp();
		}
		else
		{
			// 안에 적이 있으면 그 발밑에서, 없으면 장판 안 아무 데서나 터진다(피해는 아래 파편 틱이 준다).
			TArray<AActor*> Inside;
			GatherTargets(FieldCenter, FieldRadius, Inside);
			if (!Inside.IsEmpty())
			{
				const AActor* Victim = Inside[FMath::RandRange(0, Inside.Num() - 1)];
				Ground = FVector(Victim->GetActorLocation().X, Victim->GetActorLocation().Y, FieldCenter.Z);
			}
			else
			{
				const float Angle = FMath::FRandRange(0.0f, 2.0f * PI);
				Ground += FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.0f) * FieldRadius * 0.6f * FMath::Sqrt(FMath::FRand());
			}
			SpawnBurstLater(IceShards, Ground, FieldThrustBurstScale, 0.0f);
			SpawnBurstLater(IceShock, Ground, FieldThrustShockScale, 0.0f);
		}
		UE_LOG(LogTemp, Display, TEXT("AURORA_FIELD thrust=%d at=%s"), FieldThrusts, *Ground.ToCompactString());
	}
	const int32 Due = FMath::Min(FMath::FloorToInt(static_cast<float>(Now - FieldStartedAt) / FieldBurstInterval) + 1, FieldBurstCount);
	while (FieldBurstsDone < Due)
	{
		++FieldBurstsDone;
		// 안에 적이 있으면 파편의 절반 남짓은 적 발밑에서 튀어 맞는 게 보이게 한다.
		TArray<AActor*> Inside;
		GatherTargets(FieldCenter, FieldRadius, Inside);
		FVector Ground;
		if (!Inside.IsEmpty() && FMath::FRand() < 0.6f)
		{
			AActor* Victim = Inside[FMath::RandRange(0, Inside.Num() - 1)];
			Ground = FVector(Victim->GetActorLocation().X, Victim->GetActorLocation().Y, FieldCenter.Z) +
				FVector(FMath::FRandRange(-40.0f, 40.0f), FMath::FRandRange(-40.0f, 40.0f), 0.0f);
		}
		else
		{
			const float Angle = FMath::FRandRange(0.0f, 2.0f * PI);
			const float Reach = FieldRadius * 0.85f * FMath::Sqrt(FMath::FRand());
			Ground = FieldCenter + FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.0f) * Reach;
		}
		// 파편이 튀는 순간 장판 안 전부에 피해·감속(회오리는 도는 파편이 그 몫이라 따로 튀지 않는다).
		if (FieldVisual != 1)
		{
			SpawnBurstLater(IceShards, Ground, FieldBurstScale, 0.0f);
		}
		ApplyAreaDamage(FieldCenter, FieldRadius, FieldTickDamage, TEXT("SLOW"), FieldTickSlowSeconds);
	}
	if (Now - FieldStartedAt < FieldChannelSeconds)
	{
		return;
	}
	GetWorld()->GetTimerManager().ClearTimer(FieldTimer);
	// 끝(다 버텼을 때만): 안의 적은 얼어붙는다.
	TArray<AActor*> Targets;
	ApplyAreaDamage(FieldCenter, FieldRadius, Skills[EAuroraSkill::FrostField].Damage, TEXT("STUN"), FieldFreezeSeconds, &Targets);
	for (AActor* Target : Targets)
	{
		AttachTimedEffect(CryoFrozen, Target, FieldFreezeSeconds);
	}
	// 둘레에 솟던 얼음 결정 8개는 사용자 요청으로 뺐다(2026-10-18 밤 「마지막에 바닥에 생기는 오브젝트」).
	if (FieldVisual == 1)
	{
		CollapseVortex(true);
	}
	else
	{
		SpawnBurstLater(IceShockBig, FieldCenter, 1.0f, 0.0f);
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_FIELD end frozen=%d thrusts=%d"), Targets.Num(), FieldThrusts);
}

void UAuroraSkillComponent::SpawnVortex()
{
	ClearVortex();
	VortexStage = 0;
	VortexStageAt = 0.0;
	VortexCollapseAt = 0.0;
	VortexPulled = 0.0f;
	VortexLastTick = GetWorld()->GetTimeSeconds();
	AddVortexShards(VortexBaseCount);
	GetWorld()->GetTimerManager().SetTimer(VortexTimer, this, &UAuroraSkillComponent::VortexTick, 1.0f / 60.0f, true);
	VortexTick();
	UE_LOG(LogTemp, Display, TEXT("AURORA_VORTEX start shards=%d"), VortexShards.Num());
}

void UAuroraSkillComponent::AddVortexShards(int32 Count)
{
	if (!BladeMesh || !GetWorld())
	{
		return;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	for (int32 Index = 0; Index < Count; ++Index)
	{
		UStaticMeshComponent* Mesh = SpawnTimedMesh(BladeMesh, FTransform(FRotator::ZeroRotator, FieldCenter, FVector(0.001f)),
			FieldChannelSeconds + 3.0f);
		if (!Mesh)
		{
			continue;
		}
		if (BladeMaterial)
		{
			Mesh->SetMaterial(0, BladeMaterial);
		}
		Mesh->SetCastShadow(false);
		Mesh->SetReceivesDecals(false);
		// 바닥에서 솟아(VortexTick이 나타난 뒤 0.25초 동안 높이를 키운다) 제 자리를 돈다. 안팎·높이가 고르게 퍼지게 무작위.
		FAuroraVortexShard Shard;
		Shard.Mesh = Mesh;
		Shard.Angle = FMath::FRandRange(0.0f, 360.0f);
		Shard.Reach = FMath::Sqrt(FMath::FRand());
		Shard.Rise = FMath::FRand();
		Shard.Pace = FMath::FRandRange(0.8f, 1.25f);
		const float Width = FMath::FRandRange(SlashShardMinWidth, SlashShardMaxWidth) * VortexShardScale;
		Shard.Size = FVector(Width, Width * FMath::FRandRange(0.4f, 0.7f),
			FMath::FRandRange(SlashShardMinLength, SlashShardMaxLength) * VortexShardScale);
		Shard.Born = Now;
		Shard.SpinRate = FMath::FRandRange(180.0f, 540.0f) * (FMath::RandBool() ? 1.0f : -1.0f);
		VortexShards.Add(Shard);
	}
}

void UAuroraSkillComponent::VortexStageUp()
{
	if (VortexShards.IsEmpty() || VortexCollapseAt > 0.0 || !GetWorld())
	{
		return;
	}
	VortexStage = FMath::Min(VortexStage + 1, VortexMaxStage);
	VortexStageAt = GetWorld()->GetTimeSeconds();
	AddVortexShards(VortexAddCount);
	// 칼질이 닿는 순간: 회오리 가운데에서 얼음 조각이 튄다(VortexTick이 기둥을 잠깐 부풀린다).
	SpawnBurstLater(SculptureChip, FieldCenter + FVector(0.0f, 0.0f, 70.0f), 1.3f, 0.0f);
	UE_LOG(LogTemp, Display, TEXT("AURORA_VORTEX stage=%d shards=%d"), VortexStage, VortexShards.Num());
}

void UAuroraSkillComponent::VortexTick()
{
	if (!GetWorld() || !BladeMesh)
	{
		return;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	const float Delta = static_cast<float>(Now - VortexLastTick);
	VortexLastTick = Now;
	// 내리꽂히기(Collapse 0 → 1): 기둥이 가운데로 오므라들며 바닥으로 내려오고 더 빨리 돈다. 다 내려오면 터지거나(끝까지 버팀) 흩어진다.
	const float Collapse = VortexCollapseAt > 0.0 ? FMath::Clamp(static_cast<float>(Now - VortexCollapseAt) / VortexCollapseSeconds, 0.0f, 1.0f) : 0.0f;
	if (Collapse >= 1.0f)
	{
		if (bVortexFull)
		{
			SpawnShatterShards(FieldCenter, 60.0f, VortexBurstCount, VortexBurstSpeed, VortexBurstUpSpeed, 1.2f);
			SpawnBurstLater(SculptureChip, FieldCenter + FVector(0.0f, 0.0f, 40.0f), 2.0f, 0.0f);
		}
		else
		{
			SpawnShatterShards(FieldCenter, 100.0f, VortexBurstCount / 2, VortexBurstSpeed * 0.5f, VortexBurstUpSpeed * 0.5f);
		}
		UE_LOG(LogTemp, Display, TEXT("AURORA_VORTEX burst full=%d stage=%d shards=%d pulled=%.0f"), bVortexFull, VortexStage,
			VortexShards.Num(), VortexPulled);
		ClearVortex();
		return;
	}
	const float Spin = (VortexSpinBase + VortexSpinStage * VortexStage) * (1.0f + Collapse);
	const float Outer = VortexOuterBase + VortexOuterStage * VortexStage;
	const float Height = VortexHeightBase + VortexHeightStage * VortexStage;
	const float Pulse = VortexStageAt > 0.0 ? 1.0f + VortexPulse * FMath::Exp(-static_cast<float>(Now - VortexStageAt) / VortexPulseSeconds) : 1.0f;
	const float Grow = 1.0f + VortexGrowStage * VortexStage;
	const FVector Extent = BladeMesh->GetBounds().BoxExtent;
	for (int32 Index = VortexShards.Num() - 1; Index >= 0; --Index)
	{
		FAuroraVortexShard& Shard = VortexShards[Index];
		UStaticMeshComponent* Mesh = Shard.Mesh.Get();
		if (!IsValid(Mesh))
		{
			VortexShards.RemoveAtSwap(Index);
			continue;
		}
		Shard.Angle += Spin * Shard.Pace * Delta;
		const float Age = static_cast<float>(Now - Shard.Born);
		const float Risen = FMath::Clamp(Age / 0.25f, 0.0f, 1.0f);
		// 깔때기: 위로 갈수록 넓다. 단이 오르면 넓어지고 높아지며 잠깐 부푼다.
		const float Radius = FMath::Lerp(VortexInnerRadius, Outer, Shard.Reach) * (0.55f + 0.45f * Shard.Rise) * Pulse * (1.0f - 0.7f * Collapse);
		const float Z = 15.0f + Shard.Rise * Risen * Height * (1.0f - Collapse);
		const float Radians = FMath::DegreesToRadians(Shard.Angle);
		const FVector Out(FMath::Cos(Radians), FMath::Sin(Radians), 0.0f);
		const FVector Tangent(-Out.Y, Out.X, 0.0f);
		// 원뿔 끝(+Z)이 도는 쪽으로 조금 들려 바람에 실려 가는 모양, 제 축으로 빙글빙글 돈다.
		const FVector Heading = (Tangent * 0.94f + FVector(0.0f, 0.0f, 0.34f)).GetSafeNormal();
		const FQuat Facing = FQuat(Heading, FMath::DegreesToRadians(Shard.SpinRate * Age)) * FRotationMatrix::MakeFromZ(Heading).ToQuat();
		Mesh->SetWorldLocationAndRotation(FieldCenter + Out * Radius + FVector(0.0f, 0.0f, Z), Facing);
		const float Shown = Grow * FMath::Max(Risen, 0.05f);
		Mesh->SetWorldScale3D(FVector(Shard.Size.X / (2.0f * Extent.X), Shard.Size.Y / (2.0f * Extent.Y), Shard.Size.Z / (2.0f * Extent.Z)) * Shown);
	}
}

void UAuroraSkillComponent::PullIntoVortex(float DeltaSeconds)
{
	if (DeltaSeconds <= 0.0f || VortexShards.IsEmpty() || !GetWorld())
	{
		return;
	}
	TArray<AActor*> Inside;
	GatherTargets(FieldCenter, FieldRadius, Inside);
	const float Speed = VortexPullBase + VortexPullStage * VortexStage;
	for (AActor* Target : Inside)
	{
		FVector Offset = FieldCenter - Target->GetActorLocation();
		Offset.Z = 0.0f;
		const float Distance = Offset.Size();
		if (Distance <= VortexPullStop)
		{
			continue;
		}
		const FVector Step = Offset / Distance * FMath::Min(Speed * DeltaSeconds, Distance - VortexPullStop);
		if (AKwangTrainingDummy* Dummy = Cast<AKwangTrainingDummy>(Target))
		{
			// 허수아비는 끝난 뒤 원래 자리로 돌린다(돌진 밀어내기와 같은 규칙 — 마지막으로 끌어당긴 2.5초 뒤).
			if (!ShovedTargets.ContainsByPredicate([Dummy](const FShovedTarget& Entry) { return Entry.Actor.Get() == Dummy; }))
			{
				ShovedTargets.Add({Dummy, Dummy->GetActorLocation()});
			}
			Dummy->SetActorLocation(Dummy->GetActorLocation() + Step, false, nullptr, ETeleportType::TeleportPhysics);
			GetWorld()->GetTimerManager().SetTimer(ShoveRestoreTimer, this, &UAuroraSkillComponent::RestoreShoved, 2.5f, false);
		}
		else
		{
			Target->AddActorWorldOffset(Step, true);
		}
		VortexPulled += Step.Size();
	}
}

void UAuroraSkillComponent::CollapseVortex(bool bFull)
{
	if (VortexShards.IsEmpty() || VortexCollapseAt > 0.0 || !GetWorld())
	{
		return;
	}
	bVortexFull = bFull;
	VortexCollapseAt = GetWorld()->GetTimeSeconds();
	UE_LOG(LogTemp, Display, TEXT("AURORA_VORTEX collapse full=%d"), bFull);
}

void UAuroraSkillComponent::ClearVortex()
{
	for (const FAuroraVortexShard& Shard : VortexShards)
	{
		RemoveTimedMesh(Shard.Mesh.Get(), nullptr);
	}
	VortexShards.Reset();
	VortexCollapseAt = 0.0;
	if (GetWorld())
	{
		GetWorld()->GetTimerManager().ClearTimer(VortexTimer);
	}
}

float UAuroraSkillComponent::GetIncomingDamageScale() const
{
	return GetWorld() && GetWorld()->GetTimeSeconds() < ArmorEndsAt ? ArmorDamageScale : 1.0f;
}

void UAuroraSkillComponent::ExecuteIceArmor()
{
	// 칼을 다 치켜들면(10-20 오후는 칼이 몸 앞을 지나면, 10-18~10-20은 땅에 꽂히면) 몸을 감싸는 얼음 보호막(육각 얼음판이 벌집처럼 군데군데 붙은 둥근 구)이 켜진다(사용자 요청 2026-10-18~19 —
	// 파란 충격파·얼음 껍질·서리 무늬는 뺐다).
	const double Now = GetWorld()->GetTimeSeconds();
	// 켜져 있는 중에 다시 쓰면(쿨타임 무시 시험) 다시 부풀지 않고 시간만 늘린다.
	ArmorStartedAt = ArmorShell.IsValid() ? Now - ArmorShellGrowSeconds : Now;
	ArmorEndsAt = Now + ArmorSeconds;
	// 87차 A-2(Aurora.FX.APolish 2)는 보호막 껍질 대신 몸에 붙은 고드름 판이 켜진 동안을 보여 준다
	const int32 PolishLook = GetAPolish();
	// 94차 보호막 시안(Aurora.FX.AShell): 둥근 구는 1에서만, 2·3은 BeginArmorSkin
	if (!ArmorShell.IsValid() && ShellMesh && Character->GetRootComponent() && PolishLook != 2 && GetAShell() == 1)
	{
		UStaticMeshComponent* Shell = NewObject<UStaticMeshComponent>(Character.Get());
		// 충돌·내비 영향은 메시보다 먼저 끈다(SpawnTimedMesh와 같은 까닭 — 거꾸로면 내비 목록에 올라가 내비에 구멍이 난다).
		Shell->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Shell->SetCanEverAffectNavigation(false);
		Shell->SetStaticMesh(ShellMesh);
		Shell->SetCastShadow(false);
		// 몸 중심(캡슐 가운데)보다 조금 위에 둬 발끝부터 머리 위까지 덮는다.
		Shell->SetupAttachment(Character->GetRootComponent());
		Shell->SetRelativeLocation(FVector(0.0f, 0.0f, ArmorShellLift));
		// 몸을 따라다니되 돌지는 않는다(10-19 「방향이 너무 일렁이지 않았으면」 — 전엔 몸이 돌 때마다 육각판이 같이 휙휙 돌았다).
		Shell->SetUsingAbsoluteRotation(true);
		Shell->SetWorldRotation(FRotator::ZeroRotator);
		// 색·육각 얼음판·서리는 재질 기본값 그대로(aurora_frost_materials_build.py). 무늬 시안은 Aurora.FX.APattern.
		if (UMaterialInterface* Material = GetArmorShellMaterial(Shell))
		{
			Shell->SetMaterial(0, Material);
		}
		Shell->SetRelativeScale3D(FVector(0.01f));
		Shell->RegisterComponent();
		OwnedMeshes.Add(Shell);
		ArmorShell = Shell;
	}
	// 켜질 때 발밑 이펙트 시안(Aurora.FX.ACast — 0이 지금의 작은 얼음 결정). 87차 A-1·A-2는 그 대신 SpawnArmorPolish
	if (PolishLook > 0)
	{
		SpawnArmorPolish(PolishLook);
	}
	else
	{
		SpawnArmorCast(GetFeetLocation());
	}
	BeginArmorSkin();
	GetWorld()->GetTimerManager().SetTimer(ArmorTimer, this, &UAuroraSkillComponent::IceArmorTick, 1.0f / 30.0f, true);
	IceArmorTick();
	UE_LOG(LogTemp, Display, TEXT("AURORA_ARMOR on seconds=%.1f scale=%.2f shell=%d"), ArmorSeconds, ArmorDamageScale, ArmorShell.IsValid());
}

void UAuroraSkillComponent::IceArmorTick()
{
	if (!GetWorld() || !Character.IsValid())
	{
		return;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	UStaticMeshComponent* Shell = ArmorShell.Get();
	if (Now >= ArmorEndsAt)
	{
		GetWorld()->GetTimerManager().ClearTimer(ArmorTimer);
		if (Shell)
		{
			// 오므라든 보호막이 잘게 깨지며 흩어진다.
			SpawnBurstLater(DecoyExplode, Shell->GetComponentLocation(), 0.5f, 0.0f);
			OwnedMeshes.Remove(Shell);
			Shell->DestroyComponent();
		}
		ArmorShell.Reset();
		EndArmorPolish();
		EndArmorSkin();
		UE_LOG(LogTemp, Display, TEXT("AURORA_ARMOR off"));
		return;
	}
	if (!Shell)
	{
		return;
	}
	// 켜질 때 빠르게 부풀고(ArmorShellGrowSeconds), 끝날 때 오므라든다. 켜진 동안 숨 쉬듯 커졌다 작아지던 것은 10-19
	// 「너무 일렁이지 않았으면」으로 뺐다.
	const float Age = static_cast<float>(Now - ArmorStartedAt);
	const float Left = static_cast<float>(ArmorEndsAt - Now);
	const float Grow = FMath::InterpEaseOut(0.0f, 1.0f, FMath::Clamp(Age / ArmorShellGrowSeconds, 0.0f, 1.0f), 2.0f);
	const float Fade = FMath::Clamp(Left / ArmorShellFadeSeconds, 0.0f, 1.0f);
	const float Size = FMath::Max(Grow * Fade, 0.01f);
	Shell->SetRelativeScale3D(FVector(ArmorShellDiameter / 100.0f * Size));
}

void UAuroraSkillComponent::SpawnDecoy()
{
	// 앞 분신이 남아 있으면(쿨타임 무시 시험) 먼저 부순다.
	if (DecoyMesh.IsValid() || DecoyClone.IsValid())
	{
		GetWorld()->GetTimerManager().ClearTimer(DecoyTimer);
		ExplodeDecoy();
	}
	const FVector Feet = GetFeetLocation();
	if (DecoySpawn)
	{
		UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), DecoySpawn, Feet, Character->GetActorRotation());
	}
	// 87차 「있던 자리에 생기는 얼음 오브젝트 애니메이션만 다른 걸로 — 돌진하기 직전(팔을 뒤로 뺀) 느낌」: 석상 대신 그 자세의 사본
	if (SpawnDecoyPose(Feet, Character->GetActorRotation().Yaw))
	{
		GetWorld()->GetTimerManager().SetTimer(DecoyTimer, this, &UAuroraSkillComponent::ExplodeDecoy, DecoySeconds, false);
		return;
	}
	// 분신 메시의 앞 축은 캐릭터 메시와 같다고 보고 같은 -90도 돌림을 준다(촬영 aurora_q로 확인할 것).
	const FRotator Facing(0.0f, Character->GetActorRotation().Yaw - 90.0f, 0.0f);
	// 석상만 남긴다. 발밑에 솟는 뾰족한 얼음(Decoy_Frost)은 사용자 요청으로 뺐다(2026-10-18).
	DecoyMesh = SpawnTimedMesh(DecoyStatue, FTransform(Facing, Feet), DecoySeconds + 1.0f);
	GetWorld()->GetTimerManager().SetTimer(DecoyTimer, this, &UAuroraSkillComponent::ExplodeDecoy, DecoySeconds, false);
	if (DecoyStatue)
	{
		UE_LOG(LogTemp, Display, TEXT("AURORA_DECOY spawn at=%s extent=%s"), *Feet.ToCompactString(),
			*DecoyStatue->GetBounds().BoxExtent.ToCompactString());
	}
}

void UAuroraSkillComponent::ExplodeDecoy()
{
	UStaticMeshComponent* Decoy = DecoyMesh.Get();
	USkeletalMeshComponent* Clone = DecoyClone.Get();
	if ((!IsValid(Decoy) && !IsValid(Clone)) || !GetWorld())
	{
		return;
	}
	const FVector Center = IsValid(Decoy) ? Decoy->GetComponentLocation() : Clone->GetComponentLocation();
	if (IsValid(Clone))
	{
		Clone->DestroyComponent();
	}
	DecoyClone.Reset();
	if (DecoyExplode)
	{
		UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), DecoyExplode, Center + FVector(0.0f, 0.0f, 90.0f));
	}
	if (DecoyCrumble)
	{
		UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), DecoyCrumble, Center);
	}
	RemoveTimedMesh(Decoy, nullptr);
	DecoyMesh.Reset();
	const int32 Hits = ApplyAreaDamage(Center, DecoyRadius, Skills[EAuroraSkill::FrozenSimulacrum].Damage, TEXT("SLOW"), DecoySlowSeconds);
	UE_LOG(LogTemp, Display, TEXT("AURORA_DECOY explode at=%s hits=%d"), *Center.ToCompactString(), Hits);
}

void UAuroraSkillComponent::ExecuteLeap()
{
	// 대상 머리 위에 나타났다가 바로 앞에 내려선다(헤더 LeapAboveHead 설명). 대상이 그새 사라졌으면 내려설 자리 위에 나타난다.
	UCharacterMovementComponent* Movement = Character->GetCharacterMovement();
	LeapStart = Character->GetActorLocation();
	const float HalfHeight = Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	FVector Head = LeapTarget + FVector(0.0f, 0.0f, HalfHeight);
	if (const AActor* Target = LeapTargetActor.Get())
	{
		float Radius = 0.0f;
		float TargetHalf = 0.0f;
		Target->GetSimpleCollisionCylinder(Radius, TargetHalf);
		Head = Target->GetActorLocation() + FVector(0.0f, 0.0f, TargetHalf);
	}
	LeapFrom = Head + FVector(0.0f, 0.0f, LeapAboveHead + HalfHeight);
	const FVector Facing = (Head - LeapTarget).GetSafeNormal2D();
	// 떨어지는 길은 장면마다 직접 옮긴다(LeapDropTick) — 날아가는 이동 방식으로 두어 중력·바닥 미끄러짐이 끼지 않게
	Movement->StopMovementImmediately();
	Movement->SetMovementMode(MOVE_Flying);
	Character->SetActorLocationAndRotation(LeapFrom, Facing.IsNearlyZero() ? Character->GetActorRotation() : Facing.Rotation(), false, nullptr,
		ETeleportType::TeleportPhysics);
	bLeaping = true;
	LeapDropAge = 0.0f;
	if (LeapTrail)
	{
		UParticleSystemComponent* Trail = UGameplayStatics::SpawnEmitterAttached(LeapTrail, Character->GetMesh(), NAME_None,
			FVector::ZeroVector, FRotator::ZeroRotator, EAttachLocation::KeepRelativeOffset, false);
		if (Trail)
		{
			OwnedEffects.Add(Trail);
			LeapTrailEffect = Trail;
		}
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_LEAP appear target=%s above=%s land=%s"), *GetNameSafe(LeapTargetActor.Get()),
		*LeapFrom.ToCompactString(), *LeapTarget.ToCompactString());
	LeapEndTimer = GetWorld()->GetTimerManager().SetTimerForNextTick(this, &UAuroraSkillComponent::LeapDropTick);
}

void UAuroraSkillComponent::LeapDropTick()
{
	LeapEndTimer.Invalidate();
	if (!bLeaping || !Character.IsValid() || !GetWorld())
	{
		return;
	}
	// 옆으로는 처음 빠르게(머리 위를 먼저 벗어나고), 아래로는 점점 빠르게(떨어지듯) — 몸이 대상 머리에 걸리지 않는다.
	// 캐릭터 시간으로 센다(역경직이 걸리면 같이 멈춘다).
	LeapDropAge += GetWorld()->GetDeltaSeconds() * Character->CustomTimeDilation;
	const float Alpha = FMath::Clamp(LeapDropAge / LeapSeconds, 0.0f, 1.0f);
	const float Out = 1.0f - FMath::Square(1.0f - Alpha);
	const float Down = FMath::Square(Alpha);
	Character->SetActorLocation(FVector(FMath::Lerp(LeapFrom.X, LeapTarget.X, Out), FMath::Lerp(LeapFrom.Y, LeapTarget.Y, Out),
		FMath::Lerp(LeapFrom.Z, LeapTarget.Z, Down)), false, nullptr, ETeleportType::TeleportPhysics);
	if (Alpha >= 1.0f)
	{
		EndLeap(false);
		return;
	}
	LeapEndTimer = GetWorld()->GetTimerManager().SetTimerForNextTick(this, &UAuroraSkillComponent::LeapDropTick);
}

void UAuroraSkillComponent::EndLeap(bool bCancelled)
{
	if (!bLeaping)
	{
		return;
	}
	bLeaping = false;
	if (GetWorld())
	{
		GetWorld()->GetTimerManager().ClearTimer(LeapEndTimer);
	}
	if (Character.IsValid() && Character->GetCharacterMovement())
	{
		// 내려선 자리(또는 끊긴 공중)에서 떨어져 걷기로 돌아온다
		Character->GetCharacterMovement()->SetMovementMode(MOVE_Falling);
	}
	ReleaseOwnedEffect(LeapTrailEffect.Get());
	LeapTrailEffect.Reset();
	// 착지 바닥 서리(P_Aurora_Frozen_Ground_Water_Leap)는 뺐다 — R의 언 바닥과 같은 계열로 하늘에 눈구름을 띄운다(2026-10-18 사용자 요청).
	UE_LOG(LogTemp, Display, TEXT("AURORA_LEAP end cancelled=%d from=%s target=%s actual=%s miss=%.0f mode=%d"), bCancelled,
		*LeapStart.ToCompactString(), *LeapTarget.ToCompactString(),
		Character.IsValid() ? *Character->GetActorLocation().ToCompactString() : TEXT("-"),
		Character.IsValid() ? FVector::Dist2D(Character->GetActorLocation(), LeapTarget) : -1.0f,
		Character.IsValid() && Character->GetCharacterMovement() ? static_cast<int32>(Character->GetCharacterMovement()->MovementMode.GetValue()) : -1);
}

void UAuroraSkillComponent::ExecuteCryoseism()
{
	// 착지(1.2초)에 둘레의 대상을 얼리고, 잠시 뒤 얼음이 터지며 그 주위까지 피해·감속을 퍼뜨린다(원작 소개 글 기준).
	const FAuroraSkillDefinition& Definition = Skills[EAuroraSkill::Cryoseism];
	const FVector Center = GetFeetLocation();
	const int32 Skip = CVarAuroraCryoSkip.GetValueOnGameThread();
	if (CryoInitialBlast && !(Skip & 1))
	{
		UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), CryoInitialBlast, Center, FRotator::ZeroRotator, FVector(CryoEffectScale));
	}
	// 「주변이 다 얼어붙는」 시안(Aurora.FX.RStyle). 1 = 얼음 결정이 안쪽부터 물결처럼 번짐, 2 = 도약 중 발밑 냉기 빛 + 얼음이 터질 때 파편, 3 = 둘 다.
	// 착지 시안(Aurora.FX.VLand, 10-20 「바닥에 오브젝트 깔리는 거 말고」)이 0이 아니면 얼음 결정 물결 대신 그 시안을 깐다.
	const int32 Style = CVarAuroraCryoStyle.GetValueOnGameThread();
	const int32 Land = CVarAuroraCryoLand.GetValueOnGameThread();
	// 결정 빽빽 시안(Aurora.FX.VDense) 4는 결정 사이 바닥을 VLand 4처럼 얼린다
	const int32 Dense = CVarAuroraCryoDense.GetValueOnGameThread();
	const FVector Forward = Character->GetActorForwardVector().GetSafeNormal2D();
	switch (Land == 0 && Dense == 4 ? 4 : Land)
	{
	case 1:
	case 2:
		// 착지 자리에서 바닥이 바깥으로 갈라져 나가고(S 시안 4·5의 균열 그림 — 그림 B = 가운데에서 잰 거리), 얼음이 터질 때 사라진다.
		SweepFloorDecal(Land == 1 ? HasteCrackMaterial.LoadSynchronous() : HasteFlakeCrackMaterial.LoadSynchronous(), Center, Forward,
			Definition.Range, CryoFreezeSeconds + HasteFloorFadeOut, CryoCrackSweepSeconds, -1.0f, HasteFloorFadeOut);
		break;
	case 4:
		// 바닥이 하얗게 얼어붙는다(R 장판과 같은 서리 바닥, 진하게).
		if (UMaterialInterface* Frost = FrostTrailMaterial.LoadSynchronous())
		{
			UMaterialInstanceDynamic* Dynamic = UMaterialInstanceDynamic::Create(Frost, this);
			Dynamic->SetScalarParameterValue(TEXT("FillOpacity"), CryoFrostFill);
			Dynamic->SetScalarParameterValue(TEXT("RingOpacity"), CryoFrostRing);
			SpawnFloorDecal(Dynamic, Center, Definition.Range, CryoFreezeSeconds + HasteFloorFadeOut, CryoFrostFadeIn, HasteFloorFadeOut);
		}
		break;
	case 5:
	case 6:
	case 7:
	case 8:
		// 10-20 밤 「얼음 오브젝트 지우고 다른 이펙트」(헤더 CryoNovaStart 설명): 5 서리 충격파 · 6 얼음 파편 폭발 · 7 둘 다 · 8 = 7 + 멈칫.
		// 8 바탕 시안(Aurora.FX.VNova, 헤더 CryoNovaFastSeconds 설명): 1 더 거친 고리 · 2 고리 셋 더 빠르게 · 4 파편 크고 높이 · 8 터질 때 한 번 더
		if (Land != 6)
		{
			const int32 Nova = CVarAuroraCryoNova.GetValueOnGameThread();
			UMaterialInterface* Ring = (Nova & 1) ? NovaRingRoughMaterial.LoadSynchronous() : nullptr;
			SpawnFrostNova(Center, Definition.Range * CryoNovaReach, (Nova & 2) ? 3 : 2, (Nova & 2) ? CryoNovaFastSeconds : CryoNovaSeconds,
				Ring ? Ring : NovaRingMaterial.LoadSynchronous());
		}
		if (Land != 5)
		{
			const bool bHeavy = (CVarAuroraCryoNova.GetValueOnGameThread() & 4) != 0;
			SpawnCryoShards(Center, bHeavy ? CryoHeavyShardCount : CryoBurstShardCount, bHeavy, Definition.Range, false);
		}
		if (Land == 8)
		{
			BeginHitStop(nullptr, CryoLandHitStopSeconds);
		}
		break;
	default:
		break;
	}
	if ((Style == 1 || Style == 3) && Land == 0 && !(Skip & 2))
	{
		SpawnCryoCrystals(Center, Definition.Range, Dense);
	}
	// 착지 때 결정과 함께 터지던 큰 충격파·서리 안개·파편 8개·언 바닥은 사용자 요청으로 뺐다(2026-10-18 「얼음 깔릴 때
	// 나오는 이펙트는 없애는 게」). 언 바닥(Frozen_Ground_Water_Ultimate)은 하늘에 눈구름을 띄워 그 전에 이미 꺼 두었다.
	TArray<AActor*> Targets;
	ApplyAreaDamage(Center, Definition.Range, CryoInitialDamage, TEXT("STUN"), CryoFreezeSeconds, &Targets);
	FrozenTargets.Reset();
	for (AActor* Target : Targets)
	{
		FrozenTargets.Add(Target);
		if (!(CVarAuroraCryoSkip.GetValueOnGameThread() & 64))
		{
			AttachTimedEffect(CryoFrozen, Target, CryoFreezeSeconds);
		}
	}
	if (Land == 3)
	{
		SpawnFallingSpears(Center, Targets);
	}
	GetWorld()->GetTimerManager().SetTimer(CryoTimer, this, &UAuroraSkillComponent::BurstFrozen, CryoFreezeSeconds, false);
	UE_LOG(LogTemp, Display, TEXT("AURORA_CRYO freeze=%d radius=%.0f land=%d"), Targets.Num(), Definition.Range, Land);
}

void UAuroraSkillComponent::SpawnCryoCrystals(const FVector& Center, float Range, int32 Dense)
{
	// 결정 하나 = 자리 · 방향(바깥으로 기운다) · 크기. 고리마다 늦춰 안쪽부터 물결처럼 서고, 얼음이 터질 때(CryoFreezeSeconds) 같이 부서진다.
	struct FCrystal
	{
		FVector Spot;
		FRotator Facing;
		float Scale;
	};
	TArray<TArray<FCrystal>> Rings;
	TArray<float> Delays;
	// Offset = 고리 안 첫 결정의 자리(결정 간격 단위) — 이웃 고리끼리 엇갈리게
	auto AddRing = [&](float Radius, int32 Count, float Scale, float Delay, float Offset, bool bScatter)
	{
		TArray<FCrystal>& Ring = Rings.AddDefaulted_GetRef();
		Delays.Add(Delay);
		for (int32 Index = 0; Index < Count; ++Index)
		{
			float Angle = 2.0f * PI * (Index + Offset) / Count;
			float Reach = Radius;
			float Size = Scale;
			float Turn = 0.0f;
			if (bScatter)
			{
				// 간격의 35%까지 흩고, 크기 0.6~1.35배, 방향 ±20도
				Angle += FMath::FRandRange(-0.35f, 0.35f) * 2.0f * PI / Count;
				Reach += FMath::FRandRange(-0.35f, 0.35f) * CryoDenseStep;
				Size *= FMath::FRandRange(0.6f, 1.35f);
				Turn = FMath::FRandRange(-20.0f, 20.0f);
			}
			const FVector Outward(FMath::Cos(Angle), FMath::Sin(Angle), 0.0f);
			Ring.Add({Center + Outward * Reach, Outward.Rotation() + FRotator(0.0f, Turn, 0.0f), Size});
		}
	};
	switch (Dense)
	{
	case 1:
	case 2:
	case 3:
		for (int32 Ring = 0; Ring < CryoDenseRings; ++Ring)
		{
			const float Alpha = static_cast<float>(Ring) / (CryoDenseRings - 1);
			const float Radius = CryoDenseFirst + CryoDenseStep * Ring;
			AddRing(Radius, FMath::RoundToInt(2.0f * PI * Radius / CryoDenseStep), FMath::Lerp(0.55f, 0.85f, Alpha),
				CryoDenseSpread * Alpha, 0.5f * Ring, Dense == 2);
			if (Dense == 3 && Ring + 1 < CryoDenseRings)
			{
				// 고리 사이(반 간격 바깥)에 작은 결정을 0.75배 간격으로, 안쪽 고리와 같이 선다
				const float Between = Radius + CryoDenseStep * 0.5f;
				AddRing(Between, FMath::RoundToInt(2.0f * PI * Between / (CryoDenseStep * 0.75f)), CryoDenseSmallScale,
					CryoDenseSpread * Alpha, 0.25f, false);
			}
		}
		break;
	case 4:
		for (int32 Ring = 0; Ring < 4; ++Ring)
		{
			const float Alpha = Ring / 3.0f;
			AddRing(Range * (Ring + 1) / 4.0f * 0.92f, 6 + 5 * Ring, FMath::Lerp(0.55f, 0.85f, Alpha), CryoDenseSpread * Alpha, 0.5f * Ring, false);
		}
		break;
	default:
		// 지금(10-18 RStyle 1): 고리 셋에 6·11·16개, 고리마다 CryoWaveInterval씩 늦게
		for (int32 Ring = 0; Ring < CryoWaveCount; ++Ring)
		{
			AddRing(Range * (Ring + 1) / CryoWaveCount * 0.92f, 6 + 5 * Ring, 0.55f + 0.15f * Ring, CryoWaveInterval * Ring, 0.5f * Ring, false);
		}
		break;
	}
	int32 Total = 0;
	for (int32 Ring = 0; Ring < Rings.Num(); ++Ring)
	{
		Total += Rings[Ring].Num();
		const float Delay = Delays[Ring];
		GetWorld()->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this,
			[this, Crystals = MoveTemp(Rings[Ring]), Delay]()
			{
				for (const FCrystal& Each : Crystals)
				{
					if (UParticleSystemComponent* Crystal = SpawnOwnedEffect(FreezeSegment, Each.Spot, Each.Facing))
					{
						Crystal->SetWorldScale3D(FVector(Each.Scale * CryoEffectScale));
						ReleaseLater(Crystal, FMath::Max(CryoFreezeSeconds - Delay, 0.1f), FreezeSegmentCrumble);
					}
				}
			}), FMath::Max(Delay, 0.01f), false);
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_CRYO crystals=%d rings=%d dense=%d"), Total, Rings.Num(), Dense);
}

void UAuroraSkillComponent::SpawnFrostNova(const FVector& Center, float Radius, int32 RingCount, float Seconds, UMaterialInterface* Material,
	float Strength)
{
	if (!PlaneMesh || !Material || !GetWorld() || !Character.IsValid())
	{
		return;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	const float Life = CryoNovaSecondDelay * (RingCount - 1) + Seconds * 0.6f + CryoNovaFade + 0.05f;
	for (int32 Ring = 0; Ring < RingCount; ++Ring)
	{
		// 바닥에 눕힌 판(앞면 위) — 크기·흐려짐은 NovaTick이 정한다. 그림의 고리 바깥 날은 판 반쪽의 0.9.
		UStaticMeshComponent* Mesh = SpawnTimedMesh(PlaneMesh, FTransform(FRotator::ZeroRotator, Center + FVector(0.0f, 0.0f, 4.0f), FVector(0.001f)), Life);
		if (!Mesh)
		{
			continue;
		}
		UMaterialInstanceDynamic* Dynamic = UMaterialInstanceDynamic::Create(Material, Mesh);
		Dynamic->SetScalarParameterValue(TEXT("Fade"), 0.0f);
		Mesh->SetMaterial(0, Dynamic);
		Mesh->SetCastShadow(false);
		Mesh->SetReceivesDecals(false);
		FAuroraNovaRing Nova;
		Nova.Mesh = Mesh;
		Nova.Material = Dynamic;
		// 뒤 고리일수록 늦게·작게·흐리게(셋째는 둘째보다 한 번 더)
		Nova.Born = Now + CryoNovaSecondDelay * Ring;
		Nova.MaxRadius = Radius * FMath::Pow(0.85f, static_cast<float>(Ring));
		Nova.Strength = Strength * FMath::Pow(CryoNovaSecondStrength, static_cast<float>(Ring));
		Nova.Seconds = Seconds;
		NovaRings.Add(Nova);
	}
	// 착지 자리 푸른 빛 번쩍(S 빛과 같은 빛깔, 붙이지 않음)
	if (UPointLightComponent* Old = NovaLight.Get())
	{
		Old->DestroyComponent();
	}
	UPointLightComponent* Light = NewObject<UPointLightComponent>(Character.Get());
	Light->SetMobility(EComponentMobility::Movable);
	Light->RegisterComponent();
	Light->SetWorldLocation(Center + FVector(0.0f, 0.0f, 100.0f));
	Light->SetIntensityUnits(ELightUnits::Candelas);
	Light->SetIntensity(CryoNovaLight);
	Light->SetLightColor(HasteLightColour);
	Light->SetAttenuationRadius(Radius * 1.35f);
	Light->SetCastShadows(false);
	NovaLight = Light;
	NovaLightBorn = Now;
	GetWorld()->GetTimerManager().SetTimer(NovaTimer, this, &UAuroraSkillComponent::NovaTick, 1.0f / 60.0f, true);
	NovaTick();
}

void UAuroraSkillComponent::NovaTick()
{
	if (!GetWorld())
	{
		return;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	for (int32 Index = NovaRings.Num() - 1; Index >= 0; --Index)
	{
		const FAuroraNovaRing& Nova = NovaRings[Index];
		UStaticMeshComponent* Mesh = Nova.Mesh.Get();
		const float Age = static_cast<float>(Now - Nova.Born);
		const float FadeFrom = Nova.Seconds * 0.6f;
		if (!IsValid(Mesh) || Age > FadeFrom + CryoNovaFade)
		{
			RemoveTimedMesh(Mesh, nullptr);
			NovaRings.RemoveAtSwap(Index);
			continue;
		}
		// 처음 빠르게 퍼지다 느려지고(1 - (1 - t)²), 다 퍼질 무렵(60%)부터 흐려진다
		const float Spread = FMath::Clamp(Age / Nova.Seconds, 0.0f, 1.0f);
		const float Radius = FMath::Lerp(CryoNovaStart, Nova.MaxRadius, 1.0f - FMath::Square(1.0f - Spread));
		const float Fade = Age < 0.0f ? 0.0f : Nova.Strength * FMath::Clamp(1.0f - (Age - FadeFrom) / CryoNovaFade, 0.0f, 1.0f);
		const float Half = Radius / 0.9f;
		Mesh->SetWorldScale3D(FVector(2.0f * Half / 100.0f, 2.0f * Half / 100.0f, 1.0f));
		if (UMaterialInstanceDynamic* Dynamic = Nova.Material.Get())
		{
			Dynamic->SetScalarParameterValue(TEXT("Fade"), Fade);
		}
	}
	if (UPointLightComponent* Light = NovaLight.Get())
	{
		const float Left = 1.0f - static_cast<float>(Now - NovaLightBorn) / CryoNovaLightSeconds;
		if (Left <= 0.0f)
		{
			Light->DestroyComponent();
		}
		else
		{
			Light->SetIntensity(CryoNovaLight * Left * Left);
		}
	}
	if (NovaRings.IsEmpty() && !NovaLight.IsValid())
	{
		GetWorld()->GetTimerManager().ClearTimer(NovaTimer);
	}
}

void UAuroraSkillComponent::SpawnIceBurst(const FVector& Center, int32 Count, bool bHeavy, float Reach)
{
	if (!BladeMesh || !GetWorld())
	{
		return;
	}
	// 빛나는 얼음 파편이 착지 자리에서 사방으로 낮게 튀어 바닥을 미끄러져 멈추고, 얼음이 터질 때(CryoFreezeSeconds) 작아지며 사라진다.
	// 빠르기 500~950 · 위로 150~350이면 착지 반경(500) 안 약 250~480cm에 멈춘다(중력 SlashShardGravity · 미끄럼 SlashShardSlideDrag) —
	// Reach가 다르면 빠르기를 그 비율로. bHeavy(시안 VNova 4) = 크기 1.6배 · 위로 350~650(더 높이 떴다 떨어짐) · 빠르기 0.8배(멀리 안 나감).
	UMaterialInterface* Glow = GlowIceMaterial.LoadSynchronous();
	const double Now = GetWorld()->GetTimeSeconds();
	const float Pace = Reach / 500.0f * (bHeavy ? 0.8f : 1.0f);
	const float Size = bHeavy ? 1.6f : 1.0f;
	for (int32 Index = 0; Index < Count; ++Index)
	{
		const FVector Out = FVector::ForwardVector.RotateAngleAxis(360.0f * (Index + FMath::FRand()) / Count, FVector::UpVector);
		FAuroraShard Shard;
		Shard.FloorZ = Center.Z + 3.0f;
		Shard.Start = Center + Out * 40.0f + FVector(0.0f, 0.0f, FMath::FRandRange(20.0f, 60.0f));
		Shard.Velocity = Out * FMath::FRandRange(500.0f, 950.0f) * Pace +
			FVector(0.0f, 0.0f, bHeavy ? FMath::FRandRange(350.0f, 650.0f) : FMath::FRandRange(150.0f, 350.0f));
		Shard.Born = Now;
		Shard.Life = CryoFreezeSeconds + FMath::FRandRange(0.0f, 0.15f);
		const float Width = FMath::FRandRange(10.0f, 18.0f) * Size;
		Shard.Size = FVector(Width, Width * FMath::FRandRange(0.4f, 0.7f), FMath::FRandRange(30.0f, 60.0f) * Size);
		AddShard(Shard, Now, Glow);
	}
	ShardTick();
	UE_LOG(LogTemp, Display, TEXT("AURORA_CRYO burst shards=%d heavy=%d"), Count, bHeavy);
}

void UAuroraSkillComponent::SpawnFallingSpears(const FVector& Center, const TArray<AActor*>& Targets)
{
	if (!BladeMesh || !GetWorld())
	{
		return;
	}
	// 꽂힐 자리: 얼린 대상 발밑마다 + 둘레 고르게. 조금씩 늦게, 바깥으로 살짝 기울여 내리꽂는다(끝이 아래).
	TArray<FVector> Spots;
	for (const AActor* Target : Targets)
	{
		if (IsValid(Target))
		{
			const FVector At = Target->GetActorLocation();
			Spots.Add(FVector(At.X, At.Y, FindFloorZ(At, Center.Z)));
		}
	}
	const float Range = Skills[EAuroraSkill::Cryoseism].Range;
	for (int32 Index = 0; Index < CryoSpearRingCount; ++Index)
	{
		const FVector Out = FVector::ForwardVector.RotateAngleAxis(360.0f * (Index + 0.5f) / CryoSpearRingCount, FVector::UpVector);
		const FVector At = Center + Out * Range * CryoSpearRingRadius;
		Spots.Add(FVector(At.X, At.Y, FindFloorZ(At, Center.Z)));
	}
	const double Now = GetWorld()->GetTimeSeconds();
	const FVector Extent = BladeMesh->GetBounds().BoxExtent;
	const FVector Scale(CryoSpearWidth / FMath::Max(2.0f * Extent.X, 1.0f), CryoSpearWidth / FMath::Max(2.0f * Extent.Y, 1.0f),
		CryoSpearLength / FMath::Max(2.0f * Extent.Z, 1.0f));
	for (const FVector& Spot : Spots)
	{
		const FVector Out = (Spot - Center).GetSafeNormal2D();
		const FVector Down = (FVector(0.0f, 0.0f, -1.0f) + Out * 0.25f).GetSafeNormal();
		FAuroraFallingSpear Spear;
		// 창 가운데가 바닥 위 길이 35%에 오게(끝 15%가 바닥에 박힘)
		Spear.To = Spot - Down * CryoSpearLength * 0.35f;
		Spear.From = Spear.To - Down * CryoSpearDrop;
		Spear.Born = Now + FMath::FRandRange(0.0f, 0.12f);
		UStaticMeshComponent* Mesh = SpawnTimedMesh(BladeMesh, FTransform(FRotationMatrix::MakeFromZ(Down).Rotator(), Spear.From, FVector(0.001f)),
			CryoFreezeSeconds + 0.5f);
		if (!Mesh)
		{
			continue;
		}
		if (BladeMaterial)
		{
			Mesh->SetMaterial(0, BladeMaterial);
		}
		Mesh->SetCastShadow(false);
		Mesh->SetReceivesDecals(false);
		Mesh->SetWorldScale3D(Scale);
		Mesh->SetVisibility(false);
		Spear.Mesh = Mesh;
		FallingSpears.Add(Spear);
	}
	GetWorld()->GetTimerManager().SetTimer(SpearTimer, this, &UAuroraSkillComponent::FallingSpearTick, 1.0f / 60.0f, true);
	FallingSpearTick();
	UE_LOG(LogTemp, Display, TEXT("AURORA_CRYO spears=%d"), FallingSpears.Num());
}

void UAuroraSkillComponent::FallingSpearTick()
{
	if (!GetWorld())
	{
		return;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	bool bFalling = false;
	for (FAuroraFallingSpear& Spear : FallingSpears)
	{
		UStaticMeshComponent* Mesh = Spear.Mesh.Get();
		if (!IsValid(Mesh) || Spear.bLanded)
		{
			continue;
		}
		const float Alpha = static_cast<float>(Now - Spear.Born) / CryoSpearSeconds;
		if (Alpha < 0.0f)
		{
			bFalling = true;
			continue;
		}
		Mesh->SetVisibility(true);
		if (Alpha < 1.0f)
		{
			// 점점 빨라지며 떨어진다
			Mesh->SetWorldLocation(FMath::Lerp(Spear.From, Spear.To, Alpha * Alpha));
			bFalling = true;
			continue;
		}
		// 꽂힘: 바닥이 별 모양으로 갈라지고(F 꽂힌 자리 그림) 얼음 파편이 튄다.
		Mesh->SetWorldLocation(Spear.To);
		Spear.bLanded = true;
		const FVector Floor = Spear.To + (Spear.To - Spear.From).GetSafeNormal() * CryoSpearLength * 0.35f;
		SweepFloorDecal(LanceImpactCrackMaterial.LoadSynchronous(), Floor, Character.IsValid() ? Character->GetActorForwardVector() : FVector::ForwardVector,
			LanceCrackRadius * LanceImpactScale, CryoFreezeSeconds, 0.08f, -1.0f, HasteFloorFadeOut);
		SpawnBurstLater(IceShards, Floor, 0.5f, 0.0f);
	}
	if (!bFalling)
	{
		GetWorld()->GetTimerManager().ClearTimer(SpearTimer);
	}
}

void UAuroraSkillComponent::ShatterFallingSpears()
{
	// 얼음이 터질 때 꽂힌 창도 같이 부서진다.
	for (const FAuroraFallingSpear& Spear : FallingSpears)
	{
		if (UStaticMeshComponent* Mesh = Spear.Mesh.Get(); IsValid(Mesh))
		{
			const FVector Floor = Spear.To + (Spear.To - Spear.From).GetSafeNormal() * CryoSpearLength * 0.35f;
			SpawnShatterShards(Floor, CryoSpearLength * 0.6f, 8, 300.0f, 260.0f, 0.8f);
			RemoveTimedMesh(Mesh, nullptr);
		}
	}
	FallingSpears.Reset();
	if (GetWorld())
	{
		GetWorld()->GetTimerManager().ClearTimer(SpearTimer);
	}
}

void UAuroraSkillComponent::BurstFrozen()
{
	int32 Bursts = 0;
	for (const TWeakObjectPtr<AActor>& Weak : FrozenTargets)
	{
		AActor* Target = Weak.Get();
		if (!IsValid(Target))
		{
			continue;
		}
		const FVector At = Target->GetActorLocation();
		if (CryoExplode)
		{
			UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), CryoExplode, At, FRotator::ZeroRotator, FVector(CryoEffectScale));
		}
		if (CVarAuroraCryoStyle.GetValueOnGameThread() >= 2)
		{
			SpawnBurstLater(IceShards, At - FVector(0.0f, 0.0f, 60.0f), CryoEffectScale, 0.0f);
		}
		// 착지 시안 5~8 + VNova 8: 터지는 얼음마다 작은 충격파(퍼지는 반경 = 터짐 피해 반경)와 파편이 한 번 더 — 착지의 짝
		const int32 Land = CVarAuroraCryoLand.GetValueOnGameThread();
		const int32 Nova = CVarAuroraCryoNova.GetValueOnGameThread();
		if (Land >= 5 && Land <= 8 && (Nova & 8))
		{
			const FVector Floor(At.X, At.Y, FindFloorZ(At, At.Z - 90.0f));
			UMaterialInterface* Ring = (Nova & 1) ? NovaRingRoughMaterial.LoadSynchronous() : nullptr;
			SpawnFrostNova(Floor, CryoBurstRadius * CryoNovaReach, (Nova & 2) ? 3 : 2, (Nova & 2) ? CryoNovaFastSeconds : CryoNovaSeconds,
				Ring ? Ring : NovaRingMaterial.LoadSynchronous());
			SpawnCryoShards(Floor, CryoEchoShardCount, (Nova & 4) != 0, CryoBurstRadius, true);
		}
		TArray<AActor*> Splashed;
		ApplyAreaDamage(At - FVector(0.0f, 0.0f, 90.0f), CryoBurstRadius, Skills[EAuroraSkill::Cryoseism].Damage, TEXT("SLOW"),
			CryoSlowSeconds, &Splashed);
		for (AActor* Other : Splashed)
		{
			AttachTimedEffect(CryoSlowed, Other, CryoSlowSeconds);
		}
		++Bursts;
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_CRYO burst=%d"), Bursts);
	FrozenTargets.Reset();
	ShatterFallingSpears();
}

bool UAuroraSkillComponent::PlanGlacialCharge(const FVector& Aim, FVector& OutEnd) const
{
	UNavigationSystemV1* Navigation = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
	if (!Navigation || !Character.IsValid())
	{
		return false;
	}
	FVector Direction = (Aim - Character->GetActorLocation()).GetSafeNormal2D();
	if (Direction.IsNearlyZero())
	{
		Direction = Character->GetActorForwardVector().GetSafeNormal2D();
	}
	const FVector Extent(100.0f, 100.0f, 250.0f);
	FNavLocation Start;
	if (!Navigation->ProjectPointToNavigation(GetFeetLocation(), Start, Extent, &Character->GetNavAgentPropertiesRef()))
	{
		return false;
	}
	// 내비 광선은 허수아비 자리도 구멍으로 보므로 쓰지 않는다. 벽(고정 물체)만 몸 크기 구로 쓸어 그 앞에서 멈추고,
	// 끝점 아래에 바닥이 없으면(가장자리) 한 걸음씩 물린다. 적은 밀쳐 내며 지나간다.
	const float HalfHeight = Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	const float Radius = Character->GetCapsuleComponent()->GetScaledCapsuleRadius();
	const FVector Waist = Character->GetActorLocation();
	float Distance = Skills[EAuroraSkill::GlacialCharge].Range;
	FCollisionQueryParams Query(SCENE_QUERY_STAT(AuroraCharge), false, Character.Get());
	FHitResult Wall;
	if (GetWorld()->SweepSingleByObjectType(Wall, Waist, Waist + Direction * Distance, FQuat::Identity,
		FCollisionObjectQueryParams(ECC_WorldStatic), FCollisionShape::MakeSphere(Radius), Query))
	{
		Distance = FMath::Max(Wall.Distance - 20.0f, 0.0f);
	}
	FNavLocation Projected;
	bool bFound = false;
	for (; Distance >= ChargeMinDistance; Distance -= 100.0f)
	{
		const FVector Column = Waist + Direction * Distance;
		FHitResult Floor;
		if (GetWorld()->LineTraceSingleByObjectType(Floor, Column, Column - FVector(0.0f, 0.0f, HalfHeight + 150.0f),
			FCollisionObjectQueryParams(ECC_WorldStatic), Query) &&
			Navigation->ProjectPointToNavigation(Floor.ImpactPoint, Projected, Extent, &Character->GetNavAgentPropertiesRef()))
		{
			bFound = true;
			break;
		}
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_CHARGE plan wall=%d distance=%.0f found=%d"), Wall.bBlockingHit, Distance, bFound);
	if (!bFound || FVector::Dist2D(Start.Location, Projected.Location) < ChargeMinDistance)
	{
		return false;
	}
	OutEnd = Projected.Location + FVector(0.0f, 0.0f, HalfHeight);
	return true;
}

void UAuroraSkillComponent::ExecuteGlacialCharge()
{
	UCharacterMovementComponent* Movement = Character->GetCharacterMovement();
	ChargeStart = Character->GetActorLocation();
	ChargeLast = ChargeStart;
	ChargeWallTravel = 0.0f;
	ChargeWalls = 0;
	ChargeHits.Reset();
	ChargeFrontClock = 0.0f;
	bChargeHitStopped = false;
	// 돌진 길을 따라 흰 검기 자국이 출발점부터 몸을 따라 드러났다 사라진다(10-19 「이펙트에 맞춰 땅에 흰색 이펙트 그려야 하지 않을까」).
	const FVector Path = FVector(ChargeEnd.X - ChargeStart.X, ChargeEnd.Y - ChargeStart.Y, 0.0f);
	// 87차 Space-2(Aurora.FX.SpaceLook 1)는 이 흰 줄을 뺀다 — 기준 촬영 aurora-87th-baseline에서 광선처럼 보였다
	if (Path.Size2D() > 1.0f && GetSpaceLook() == 0)
	{
		SweepFloorDecal(DashStreakMaterial.LoadSynchronous(), GetFeetLocation() + Path * 0.5f, Path.GetSafeNormal2D(),
			Path.Size2D() * 0.5f + DashStreakMargin, DashStreakSeconds, FMath::Max(ChargeSeconds, 0.05f), DashStreakHalfWidth);
	}
	if (DashFlare && CVarAuroraChargeFront.GetValueOnGameThread() == 0)
	{
		// 속도감 이펙트는 시작 자리에 두지 않고 몸에 붙여 돌진과 함께 움직인다.
		UParticleSystemComponent* Flare = UGameplayStatics::SpawnEmitterAttached(DashFlare, Character->GetRootComponent(), NAME_None,
			GetFeetLocation(), (ChargeEnd - ChargeStart).GetSafeNormal2D().Rotation(), EAttachLocation::KeepWorldPosition, false);
		if (Flare)
		{
			OwnedEffects.Add(Flare);
			ReleaseLater(Flare, ChargeSeconds + GetChargeStopSeconds());
		}
	}
	if (DashBodyFrost)
	{
		UParticleSystemComponent* Frost = UGameplayStatics::SpawnEmitterAttached(DashBodyFrost, Character->GetMesh(), NAME_None,
			FVector::ZeroVector, FRotator::ZeroRotator, EAttachLocation::KeepRelativeOffset, false);
		if (Frost)
		{
			OwnedEffects.Add(Frost);
			ChargeBodyEffect = Frost;
		}
	}
	// 엔진의 정해진 이동(루트 모션 소스)으로 끝점까지 간다. 벽·바닥 충돌은 이동 컴포넌트가 처리한다.
	TSharedPtr<FRootMotionSource_MoveToForce> Move = MakeShared<FRootMotionSource_MoveToForce>();
	Move->InstanceName = TEXT("AuroraGlacialCharge");
	Move->AccumulateMode = ERootMotionAccumulateMode::Override;
	Move->Priority = 500;
	Move->StartLocation = ChargeStart;
	Move->TargetLocation = ChargeEnd;
	Move->Duration = FMath::Max(ChargeSeconds, 0.05f);
	Move->bRestrictSpeedToExpected = true;
	Move->FinishVelocityParams.Mode = ERootMotionFinishVelocityMode::SetVelocity;
	Move->FinishVelocityParams.SetVelocity = FVector::ZeroVector;
	ChargeRootMotionId = Movement->ApplyRootMotionSource(Move);
	FTimerManager& Timers = GetWorld()->GetTimerManager();
	Timers.SetTimer(ChargeTimer, this, &UAuroraSkillComponent::GlacialChargeTick, 1.0f / 30.0f, true);
	Timers.SetTimer(ChargeEndTimer, FTimerDelegate::CreateUObject(this, &UAuroraSkillComponent::EndGlacialCharge, false),
		FMath::Max(ChargeSeconds, 0.05f), false);
	GlacialChargeTick();
}

void UAuroraSkillComponent::GlacialChargeTick()
{
	if (!Character.IsValid())
	{
		return;
	}
	const FAuroraSkillDefinition& Definition = Skills[EAuroraSkill::GlacialCharge];
	const FVector Now = Character->GetActorLocation();
	const FVector Direction = (ChargeEnd - ChargeStart).GetSafeNormal2D();
	// 앞으로 조금 미리 본다. 부딪히기 전에 옆으로 밀어내야 돌진이 막히지 않는다.
	TArray<AActor*> Targets;
	GatherTargets(GetFeetLocation() + Direction * 60.0f, ChargeHitRadius, Targets);
	AController* Instigator = Character->GetController();
	for (AActor* Target : Targets)
	{
		if (ChargeHits.Contains(Target))
		{
			continue;
		}
		ChargeHits.Add(Target);
		if (Target->CanBeDamaged())
		{
			FHitResult Hit(Target, nullptr, Target->GetActorLocation(), -Direction);
			UGameplayStatics::ApplyPointDamage(Target, Definition.Damage, Direction, Hit, Instigator, GetOwner(), nullptr);
		}
		SetStatus(Target, TEXT("SLOW"), ChargeSlowSeconds);
		// 맞은 자리에서 얼음 파편이 터진다(10-19 저녁 「W도 넣어 봐」 — 맞는 순간이 약했다). 밀어내기 전 자리, 돌진 방향으로.
		SpawnBurstLater(IceShards, FVector(Target->GetActorLocation().X, Target->GetActorLocation().Y, GetFeetLocation().Z),
			ChargeHitShardScale, 0.0f, Direction.Rotation());
		ShoveBack(Target, Direction);
		// 처음 맞힌 순간 잠깐 멈칫한다(사용자 승인 「W 한번 이렇게」 2026-10-18). 화면 흔들림은 「꺼줘」로 뺐다(같은 날 밤).
		if (!bChargeHitStopped)
		{
			bChargeHitStopped = true;
			BeginHitStop(Target, ChargeHitStopSeconds);
		}
	}
	// 앞쪽 얼음(시안 Aurora.FX.WFront 1~3): 몸에 붙인 한 번이 아니라 짧은 간격으로 새로 터뜨려 계속 부서지며 튀게 한다.
	const int32 Front = CVarAuroraChargeFront.GetValueOnGameThread();
	ChargeFrontClock -= 1.0f / 30.0f;
	if (Front != 0 && ChargeFrontClock <= 0.0f)
	{
		ChargeFrontClock = ChargeFrontInterval;
		const FVector Feet = GetFeetLocation();
		if (Front == 1 || Front == 3)
		{
			SpawnBurstLater(DashFlare, Feet + Direction * 40.0f, 0.8f, 0.0f, Direction.Rotation());
		}
		if (Front == 2 || Front == 3)
		{
			SpawnBurstLater(IceShards, Feet + Direction * 90.0f, 0.4f, 0.0f, Direction.Rotation());
		}
	}
	// 지나온 길에 자국을 메시 길이 간격으로 남긴다. 모양만이고 길을 막지는 않는다. 모양은 시안 번호(Aurora.FX.WTrail)로 고른다.
	ChargeWallTravel += FVector::Dist2D(ChargeLast, Now);
	ChargeLast = Now;
	const float HalfHeight = Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	const int32 Trail = CVarAuroraChargeTrail.GetValueOnGameThread();
	while (ChargeWallTravel >= WallStep)
	{
		ChargeWallTravel -= WallStep;
		const FVector Spot = Now - Direction * (ChargeWallTravel + 60.0f) - FVector(0.0f, 0.0f, HalfHeight);
		// 87차 Space-2가 켜져 있으면 WTrail 대신 얼음 조각(-1)
		switch (GetSpaceLook() != 0 ? -1 : Trail)
		{
		case -1:
			SpaceFragment(Spot, Direction);
			break;
		case 1:
			// 얼음 파편이 바닥에서 튄다.
			// 크기 0.5 → 0.35(사용자 「조금만 더 작게」 2026-10-18)
			SpawnBurstLater(IceShards, Spot, 0.35f, 0.0f, Direction.Rotation());
			break;
		case 2:
			// 서리 연기와 잔 얼음 조각이 피어오른다.
			SpawnBurstLater(DecoyExplode, Spot + FVector(0.0f, 0.0f, 40.0f), 0.6f, 0.0f);
			break;
		case 3:
			// 길에는 남기지 않는다(몸의 서리와 도착 충격파만).
			break;
		default:
		{
			ReleaseLater(SpawnOwnedEffect(WallBase, Spot, Direction.Rotation()), ChargeWallSeconds, WallBaseDestroy);
			const FRotator Rotation(0.0f, Direction.Rotation().Yaw + WallYawOffset, 0.0f);
			SpawnTimedMesh(IcicleWall, FTransform(Rotation, Spot + FVector(0.0f, 0.0f, WallLift), FVector(WallScale)),
				ChargeWallSeconds, WallTopDestroy);
			break;
		}
		}
		++ChargeWalls;
	}
}

void UAuroraSkillComponent::EndGlacialCharge(bool bCancelled)
{
	if (ChargeRootMotionId == 0)
	{
		return;
	}
	if (GetWorld())
	{
		GetWorld()->GetTimerManager().ClearTimer(ChargeTimer);
		GetWorld()->GetTimerManager().ClearTimer(ChargeEndTimer);
	}
	if (!bCancelled)
	{
		GlacialChargeTick();
	}
	if (Character.IsValid() && Character->GetCharacterMovement())
	{
		Character->GetCharacterMovement()->RemoveRootMotionSourceByID(ChargeRootMotionId);
		Character->GetCharacterMovement()->StopMovementImmediately();
	}
	ChargeRootMotionId = 0;
	EndHitStop();
	ReleaseOwnedEffect(ChargeBodyEffect.Get());
	ChargeBodyEffect.Reset();
	if (!bCancelled)
	{
		// 원작 돌진 자세(WRun 2)는 미끄러지지 않고 그 자리에 딱 서서 내지른 칼을 ChargeHoldSeconds 동안 버틴다.
		if (CVarAuroraChargeRun.GetValueOnGameThread() != 2)
		{
			// 미끄러져 멈추는 원본 동작. 일어서는 중간(0.55초)에 시전을 끝낸다.
			PlayFullBody(ChargeStopAnimation);
		}
		if (GetSpaceLook() != 0)
		{
			// 87차 Space-2: 도착 자리 결정 파열 + 섬광
			SpaceArrival(GetFeetLocation(), FVector(ChargeEnd.X - ChargeStart.X, ChargeEnd.Y - ChargeStart.Y, 0.0f).GetSafeNormal2D());
		}
		else if (CVarAuroraChargeTrail.GetValueOnGameThread() != 0)
		{
			// 새 시안(1~3)은 도착 지점에서 파란 충격파로 마무리한다.
			SpawnBurstLater(IceShock, GetFeetLocation(), 0.7f, 0.0f);
		}
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_CHARGE end cancelled=%d moved=%.0f planned=%.0f hits=%d walls=%d"), bCancelled,
		Character.IsValid() ? FVector::Dist2D(ChargeStart, Character->GetActorLocation()) : 0.0f,
		FVector::Dist2D(ChargeStart, ChargeEnd), ChargeHits.Num(), ChargeWalls);
}

float UAuroraSkillComponent::GetChargeStopSeconds() const
{
	return CVarAuroraChargeRun.GetValueOnGameThread() == 2 ? ChargeHoldSeconds : ChargeStopSeconds;
}

void UAuroraSkillComponent::BeginHitStop(AActor* Target, float Seconds)
{
	if (!Character.IsValid() || !GetWorld() || GetWorld()->GetTimerManager().IsTimerActive(HitStopTimer))
	{
		return;
	}
	// 몸·이동(루트 모션 소스)·동작은 캐릭터 시간으로 돌아 같이 멈춘다. 세상 시간으로 도는 끝 예약은 직접 멈췄다 푼다.
	Character->CustomTimeDilation = HitStopDilation;
	if (IsValid(Target))
	{
		Target->CustomTimeDilation = HitStopDilation;
		HitStopTarget = Target;
	}
	FTimerManager& Timers = GetWorld()->GetTimerManager();
	Timers.PauseTimer(ChargeEndTimer);
	Timers.PauseTimer(RecoveryTimer);
	Timers.SetTimer(HitStopTimer, this, &UAuroraSkillComponent::EndHitStop, Seconds, false);
	UE_LOG(LogTemp, Display, TEXT("AURORA_HITSTOP target=%s seconds=%.2f"), *GetNameSafe(Target), Seconds);
}

void UAuroraSkillComponent::EndHitStop()
{
	if (GetWorld())
	{
		FTimerManager& Timers = GetWorld()->GetTimerManager();
		Timers.ClearTimer(HitStopTimer);
		Timers.UnPauseTimer(ChargeEndTimer);
		Timers.UnPauseTimer(RecoveryTimer);
	}
	if (Character.IsValid())
	{
		Character->CustomTimeDilation = 1.0f;
	}
	if (AActor* Target = HitStopTarget.Get())
	{
		Target->CustomTimeDilation = 1.0f;
	}
	HitStopTarget.Reset();
}

void UAuroraSkillComponent::ShoveBack(AActor* Target, const FVector& PathDirection)
{
	if (!IsValid(Target) || !Character.IsValid())
	{
		return;
	}
	// 돌진 쪽으로 민다(헤더 ChargeShoveClearance 설명). 전엔 길의 어느 쪽에 있는지에 따라 옆으로 밀었다(부딪혀 돌진이 막히지 않게).
	float Radius = 0.0f;
	float HalfHeight = 0.0f;
	Target->GetSimpleCollisionCylinder(Radius, HalfHeight);
	const float Clearance = Radius + Character->GetCapsuleComponent()->GetScaledCapsuleRadius() + ChargeShoveClearance;
	const float Ahead = FVector::DotProduct(ChargeEnd - Target->GetActorLocation(), PathDirection);
	const float Distance = FMath::Max(ChargeShoveDistance, Ahead + Clearance);
	const float Seconds = FMath::Max(FVector::Dist2D(Character->GetActorLocation(), ChargeEnd) / ChargeSpeed, ChargeShoveMinSeconds);
	PushTarget(Target, PathDirection, Distance, Seconds);
	UE_LOG(LogTemp, Display, TEXT("AURORA_CHARGE shove target=%s back=%.0f seconds=%.2f"), *GetNameSafe(Target), Distance, Seconds);
}

void UAuroraSkillComponent::PushTarget(AActor* Target, const FVector& Direction, float Distance, float Seconds)
{
	if (!IsValid(Target) || Distance <= 0.0f || !GetWorld())
	{
		return;
	}
	if (AKwangTrainingDummy* Dummy = Cast<AKwangTrainingDummy>(Target))
	{
		// 수련장 배치를 지키려고 허수아비는 잠시 뒤 원래 자리로 돌린다(Gideon Black Hole과 같은 규칙).
		if (!ShovedTargets.ContainsByPredicate([Dummy](const FShovedTarget& Entry) { return Entry.Actor.Get() == Dummy; }))
		{
			ShovedTargets.Add({Dummy, Dummy->GetActorLocation()});
		}
		if (Seconds > 0.0f)
		{
			ShoveSlides.RemoveAll([Dummy](const FShoveSlide& Slide) { return Slide.Actor.Get() == Dummy; });
			ShoveSlides.Add({Dummy, Dummy->GetActorLocation(), Dummy->GetActorLocation() + Direction * Distance, Seconds, 0.0f});
			// 장면마다 한 번(1/60초 반복 타이머는 장면 둘에 한 번씩 몰아 움직여, 그 사이 돌진한 몸이 허수아비에 걸려 21cm 덜 갔다 —
			// aurora-63rd-move2 장면 기록)
			if (!GetWorld()->GetTimerManager().TimerExists(ShoveSlideTimer))
			{
				ShoveSlideTimer = GetWorld()->GetTimerManager().SetTimerForNextTick(this, &UAuroraSkillComponent::ShoveSlideTick);
			}
		}
		else
		{
			Dummy->SetActorLocation(Dummy->GetActorLocation() + Direction * Distance, false, nullptr, ETeleportType::TeleportPhysics);
		}
		GetWorld()->GetTimerManager().SetTimer(ShoveRestoreTimer, this, &UAuroraSkillComponent::RestoreShoved, 2.0f, false);
	}
	else if (ACharacter* Other = Cast<ACharacter>(Target))
	{
		Other->LaunchCharacter(Direction * Distance * 4.0f + FVector(0.0f, 0.0f, 150.0f), true, true);
	}
}

void UAuroraSkillComponent::ShoveSlideTick()
{
	ShoveSlideTimer.Invalidate();
	if (!GetWorld())
	{
		return;
	}
	const float Delta = GetWorld()->GetDeltaSeconds();
	for (int32 Index = ShoveSlides.Num() - 1; Index >= 0; --Index)
	{
		FShoveSlide& Slide = ShoveSlides[Index];
		AActor* Actor = Slide.Actor.Get();
		if (!Actor)
		{
			ShoveSlides.RemoveAtSwap(Index);
			continue;
		}
		// 대상 시간으로 센다 — 처음 맞힌 순간의 멈칫(BeginHitStop) 동안은 대상도 멈춘다
		Slide.Age += Delta * Actor->CustomTimeDilation;
		const float Alpha = FMath::Min(Slide.Age / Slide.Seconds, 1.0f);
		Actor->SetActorLocation(FMath::Lerp(Slide.From, Slide.To, 1.0f - FMath::Square(1.0f - Alpha)), false, nullptr, ETeleportType::TeleportPhysics);
		if (Alpha >= 1.0f)
		{
			ShoveSlides.RemoveAtSwap(Index);
		}
	}
	if (!ShoveSlides.IsEmpty())
	{
		ShoveSlideTimer = GetWorld()->GetTimerManager().SetTimerForNextTick(this, &UAuroraSkillComponent::ShoveSlideTick);
	}
}

void UAuroraSkillComponent::RestoreShoved()
{
	ShoveSlides.Reset();
	if (GetWorld())
	{
		GetWorld()->GetTimerManager().ClearTimer(ShoveSlideTimer);
	}
	for (const FShovedTarget& Entry : ShovedTargets)
	{
		if (AActor* Actor = Entry.Actor.Get())
		{
			Actor->SetActorLocation(Entry.Origin, false, nullptr, ETeleportType::TeleportPhysics);
		}
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_CHARGE restored=%d"), ShovedTargets.Num());
	ShovedTargets.Reset();
}

void UAuroraSkillComponent::ExecuteHoarfrost()
{
	// 내려찍은 자리에 얼음 고리를 세우고, 고리 안의 대상을 묶는다(허수아비는 STUN 글자로 보인다).
	const FAuroraSkillDefinition& Definition = Skills[EAuroraSkill::Hoarfrost];
	const FVector Center = GetFeetLocation();
	// 바닥 서리와 둘레의 얼음 고리는 사용자 요청으로 뺐다(2026-10-18).
	// 대신 원형으로 흩날리는 얼음 조각(회오리)을 띄운다.
	// 원래 속도의 회오리를 HoarfrostSwirlSeconds마다 반 바퀴 돌려 이어 띄워 묶는 시간(1.5초) 내내 빠르게 돌게 하고, 마지막 회오리는
	// 깨지는 마무리 순간에 지운다(깨지는 파편이 사라지는 순간을 가린다). 10-18 저녁에 절반 속도로 늦췄다가 「너무 부드럽다」로 되돌림.
	// 휘두름 시안(Aurora.FX.EStyle, 10-19 「휘두르는 이펙트 자체가 아쉽다」): 회오리는 0일 때만. 1~3은 시전 때(BeginCast) 제 이펙트를 띄운다.
	// (그 전 시안 — 고드름·냉기 연기·결정 소용돌이 — 은 「다른 게 문제가 아니다」로 뺐다.)
	const int32 Style = CVarAuroraFreezeStyle.GetValueOnGameThread();
	for (int32 Turn = 0; Style == 0 && Turn < HoarfrostSwirlTurns; ++Turn)
	{
		const FVector Spot = Center + FVector(0.0f, 0.0f, 30.0f);
		const FRotator Facing(0.0f, 180.0f * Turn, 0.0f);
		UParticleSystem* Swirl = Definition.CastEffect;
		const float Delay = 0.01f + HoarfrostSwirlSeconds * Turn;
		const float Life = Turn + 1 == HoarfrostSwirlTurns ? HoarfrostRootSeconds - Delay : HoarfrostSwirlSeconds;
		// 띠가 사라질 때 남은 얼음 조각까지 함께 지운다. 끄기만 하면 조각이 수명대로 떠 있는다.
		GetWorld()->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this,
			[this, Swirl, Spot, Facing, Life]()
			{
				if (UParticleSystemComponent* Component = SpawnOwnedEffect(Swirl, Spot, Facing))
				{
					Component->SetWorldScale3D(FVector(HoarfrostSwirlScale));
					DestroyEffectLater(Component, Life);
				}
			}), Delay, false);
	}
	// 둘레를 V 얼음 결정이 빈틈없이 두르고 Aurora.FX.EWallSeconds 뒤 부서진다(헤더 HoarfrostWallStep 설명)
	const float WallSeconds = FMath::Max(CVarAuroraFreezeWall.GetValueOnGameThread(), 0.1f);
	const int32 WallCount = FMath::CeilToInt(2.0f * PI * Definition.Range / HoarfrostWallStep);
	for (int32 Index = 0; Index < WallCount; ++Index)
	{
		const float Angle = 2.0f * PI * Index / WallCount;
		const FVector Outward(FMath::Cos(Angle), FMath::Sin(Angle), 0.0f);
		if (UParticleSystemComponent* Crystal = SpawnOwnedEffect(FreezeSegment, Center + Outward * Definition.Range, Outward.Rotation()))
		{
			Crystal->SetWorldScale3D(FVector(HoarfrostWallScale * CryoEffectScale));
			if (WallSeconds > HoarfrostWallHold)
			{
				TWeakObjectPtr<UParticleSystemComponent> Weak = Crystal;
				GetWorld()->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, [Weak]()
				{
					if (Weak.IsValid())
					{
						Weak->CustomTimeDilation = HoarfrostWallHoldDilation;
					}
				}), HoarfrostWallHold, false);
			}
			ReleaseLater(Crystal, WallSeconds, FreezeSegmentCrumble);
		}
	}
	TArray<AActor*> Targets;
	ApplyAreaDamage(Center, Definition.Range, Definition.Damage, TEXT("STUN"), HoarfrostRootSeconds, &Targets);
	TArray<TWeakObjectPtr<AActor>> Rooted;
	for (AActor* Target : Targets)
	{
		if (Style == 4)
		{
			EncaseTarget(Target, HoarfrostRootSeconds);
		}
		else
		{
			AttachTimedEffect(FreezeRooted, Target, HoarfrostRootSeconds);
		}
		Rooted.Add(Target);
	}
	// 마무리: 묶기가 풀리는 순간 묶인 적의 얼음이 깨지고 가운데서 작은 파란 충격파가 퍼진다(사용자 승인 2026-10-18).
	GetWorld()->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateUObject(this,
		&UAuroraSkillComponent::ShatterHoarfrost, Rooted, Center, Style != 4), HoarfrostRootSeconds, false);
	UE_LOG(LogTemp, Display, TEXT("AURORA_HOARFROST rooted=%d radius=%.0f style=%d wall=%d wallseconds=%.1f"), Targets.Num(), Definition.Range, Style,
		WallCount, WallSeconds);
}

void UAuroraSkillComponent::ShatterHoarfrost(TArray<TWeakObjectPtr<AActor>> Rooted, FVector Center, bool bCenterShock)
{
	// E 4는 시전 자리 충격파를 뺀다 — 깨짐은 대상 몸에서만 보이고, 이 충격파의 연기가 시전 자리에 크게 피었다(aurora-40th-efinal-220803).
	if (bCenterShock)
	{
		SpawnBurstLater(IceShock, Center, 0.55f, 0.0f);
	}
	int32 Shattered = 0;
	for (const TWeakObjectPtr<AActor>& Weak : Rooted)
	{
		if (AActor* Target = Weak.Get())
		{
			// E 시안 4: 묶는 동안 다시 맞아 늦춰진 대상은 나중 시전의 마무리가 깨뜨린다.
			const bool bWasEncased = Encased.ContainsByPredicate([Target](const FAuroraEncased& Record) { return Record.Target == Target; });
			if (bWasEncased && !ReleaseEncased(Target, false))
			{
				continue;
			}
			float Radius = 0.0f;
			float HalfHeight = 0.0f;
			Target->GetSimpleCollisionCylinder(Radius, HalfHeight);
			const FVector Feet = Target->GetActorLocation() - FVector(0.0f, 0.0f, HalfHeight);
			if (bWasEncased)
			{
				// E 4: 얼음 석상이 깨질 때는 무너지는 눈가루·분신 폭발(둘 다 연기가 크게 피어 가벼워 보였다, aurora-40th-efinal 두 번)
				// 대신 무거운 얼음 파편이 사방으로 튄다.
				SpawnShatterShards(Feet, 2.0f * HalfHeight, EncaseShardCount, EncaseShardSpeed, EncaseShardUpSpeed);
			}
			else
			{
				SpawnBurstLater(FreezeSegmentCrumble, Feet, 1.0f, 0.0f);
				SpawnBurstLater(DecoyExplode, Feet + FVector(0.0f, 0.0f, 40.0f), 0.6f, 0.0f);
			}
			++Shattered;
		}
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_HOARFROST shatter=%d"), Shattered);
}

void UAuroraSkillComponent::BeginSwordTrail(float Seconds)
{
	USkeletalMeshComponent* Mesh = Character.IsValid() ? Character->GetMesh() : nullptr;
	const int32 Pick = CVarAuroraSwordTrail.GetValueOnGameThread();
	UParticleSystem* Template = SwordTrails.IsValidIndex(Pick) ? SwordTrails[Pick].Get() : nullptr;
	if (!Template || !Mesh || !GetWorld())
	{
		return;
	}
	// 칼 궤적 입자(AnimTrail)는 붙은 메시의 소켓 둘 사이를 매 장면 이어 그린다. 칼을 쥔 쪽은 오른손(weapon 뼈가 hand_r 옆).
	const bool bBlade = CVarAuroraSwordTrailSockets.GetValueOnGameThread() != 0;
	const FName First(bBlade ? TEXT("Sword_Base") : TEXT("FX_Trail_R_01"));
	const FName Second(bBlade ? TEXT("Sword_Tip") : TEXT("FX_Trail_R_02"));
	UParticleSystemComponent* Trail = UGameplayStatics::SpawnEmitterAttached(Template, Mesh, NAME_None, FVector::ZeroVector,
		FRotator::ZeroRotator, EAttachLocation::KeepRelativeOffset, false);
	if (!Trail)
	{
		return;
	}
	OwnedEffects.Add(Trail);
	Trail->BeginTrails(First, Second, ETrailWidthMode_FromCentre, 1.0f);
	UE_LOG(LogTemp, Display, TEXT("AURORA_TRAIL template=%s sockets=%s:%d,%s:%d distance=%.0f seconds=%.2f"), *Template->GetName(),
		*First.ToString(), Mesh->DoesSocketExist(First), *Second.ToString(), Mesh->DoesSocketExist(Second),
		FVector::Dist(Mesh->GetSocketLocation(First), Mesh->GetSocketLocation(Second)), Seconds);
	TWeakObjectPtr<UParticleSystemComponent> Weak = Trail;
	GetWorld()->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, [Weak]()
	{
		if (UParticleSystemComponent* Component = Weak.Get())
		{
			Component->EndTrails();
		}
	}), Seconds, false);
	DestroyEffectLater(Trail, Seconds + HoarfrostTrailFadeSeconds);
}

void UAuroraSkillComponent::EncaseTarget(AActor* Target, float Seconds)
{
	if (!IsValid(Target) || !BladeMaterial || !GetWorld())
	{
		return;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	FAuroraEncased* Record = Encased.FindByPredicate([Target](const FAuroraEncased& Each) { return Each.Target == Target; });
	if (!Record)
	{
		// 몸 전체(메시마다 모든 칸)를 얼음 분신 석상 재질로 바꾼다. 글자(TextRender)·입자는 메시가 아니라 그대로다.
		Record = &Encased.AddDefaulted_GetRef();
		Record->Target = Target;
		TInlineComponentArray<UMeshComponent*> Meshes(Target);
		for (UMeshComponent* Mesh : Meshes)
		{
			if (!Mesh->IsVisible())
			{
				continue;
			}
			Record->Meshes.Add(Mesh);
			Record->SlotCounts.Add(Mesh->GetNumMaterials());
			for (int32 Slot = 0; Slot < Mesh->GetNumMaterials(); ++Slot)
			{
				Record->Originals.Add(Mesh->GetMaterial(Slot));
				Mesh->SetMaterial(Slot, BladeMaterial);
			}
		}
	}
	Record->EndsAt = Now + Seconds;

	// 발밑 얼음 덩어리: 대상 반경에 맞춘 크기로 바닥에 반쯤 묻혀 솟는다(EncaseGrowSeconds 동안 커짐).
	float Radius = 0.0f;
	float HalfHeight = 0.0f;
	Target->GetSimpleCollisionCylinder(Radius, HalfHeight);
	const FVector Feet = Target->GetActorLocation() - FVector(0.0f, 0.0f, HalfHeight);
	if (IceChunkMesh)
	{
		const FBoxSphereBounds Bounds = IceChunkMesh->GetBounds();
		const float Scale = Radius * EncaseChunkWidthScale / FMath::Max(2.0f * Bounds.BoxExtent.X, 1.0f);
		const FRotator Facing(0.0f, FMath::FRandRange(0.0f, 360.0f), 0.0f);
		// 메시 윗면(Origin.Z + Extent.Z)이 바닥에서 EncaseChunkTop 높이에 온다. 가운데는 대상 축에 맞춘다.
		const FVector Offset = Facing.RotateVector(FVector(Bounds.Origin.X, Bounds.Origin.Y, 0.0f)) * Scale;
		const FVector Where = Feet - Offset + FVector(0.0f, 0.0f, EncaseChunkTop - (Bounds.Origin.Z + Bounds.BoxExtent.Z) * Scale);
		if (UStaticMeshComponent* Chunk = SpawnTimedMesh(IceChunkMesh, FTransform(Facing, Where, FVector(Scale * 0.4f)), Seconds))
		{
			Chunk->SetReceivesDecals(false);
			TWeakObjectPtr<UStaticMeshComponent> Weak = Chunk;
			const int32 Steps = FMath::Max(FMath::CeilToInt(EncaseGrowSeconds * 60.0f), 1);
			for (int32 Step = 1; Step <= Steps; ++Step)
			{
				const float Grown = Scale * FMath::Lerp(0.4f, 1.0f, static_cast<float>(Step) / Steps);
				GetWorld()->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, [Weak, Grown]()
				{
					if (UStaticMeshComponent* Component = Weak.Get())
					{
						Component->SetWorldScale3D(FVector(Grown));
					}
				}), Step / 60.0f, false);
			}
		}
	}
	// 깨지기 직전 금이 가며 얼음 조각이 튄다.
	TWeakObjectPtr<AActor> WeakTarget = Target;
	const float Lift = HalfHeight;
	GetWorld()->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, [this, WeakTarget, Lift]()
	{
		AActor* Actor = WeakTarget.Get();
		const FAuroraEncased* Live = Actor ? Encased.FindByPredicate([Actor](const FAuroraEncased& Each) { return Each.Target == Actor; }) : nullptr;
		// 다시 맞아 늦춰졌으면 나중 예약이 튀긴다.
		if (Live && Live->EndsAt - GetWorld()->GetTimeSeconds() <= EncaseCrackLead + 0.05)
		{
			SpawnBurstLater(SculptureChip, Actor->GetActorLocation() + FVector(0.0f, 0.0f, Lift * 0.2f), 1.0f, 0.0f);
		}
	}), FMath::Max(Seconds - EncaseCrackLead, 0.01f), false);
	UE_LOG(LogTemp, Display, TEXT("AURORA_ENCASE target=%s meshes=%d slots=%d until=%.2f"), *Target->GetName(), Record->Meshes.Num(),
		Record->Originals.Num(), Record->EndsAt);
}

bool UAuroraSkillComponent::ReleaseEncased(AActor* Target, bool bForce)
{
	const int32 Index = Encased.IndexOfByPredicate([Target](const FAuroraEncased& Each) { return Each.Target == Target; });
	if (Index == INDEX_NONE)
	{
		return false;
	}
	FAuroraEncased& Record = Encased[Index];
	if (!bForce && GetWorld() && Record.EndsAt > GetWorld()->GetTimeSeconds() + 0.05)
	{
		return false;
	}
	int32 Next = 0;
	for (int32 MeshIndex = 0; MeshIndex < Record.Meshes.Num(); ++MeshIndex)
	{
		UMeshComponent* Mesh = Record.Meshes[MeshIndex].Get();
		for (int32 Slot = 0; Slot < Record.SlotCounts[MeshIndex] && Record.Originals.IsValidIndex(Next); ++Slot, ++Next)
		{
			if (Mesh)
			{
				Mesh->SetMaterial(Slot, Record.Originals[Next]);
			}
		}
	}
	Encased.RemoveAt(Index);
	return true;
}

void UAuroraSkillComponent::AttachTimedEffect(UParticleSystem* Effect, AActor* Target, float Seconds, UParticleSystem* EndEffect)
{
	if (!Effect || !IsValid(Target) || !Target->GetRootComponent())
	{
		return;
	}
	UParticleSystemComponent* Component = UGameplayStatics::SpawnEmitterAttached(Effect, Target->GetRootComponent(), NAME_None,
		FVector::ZeroVector, FRotator::ZeroRotator, EAttachLocation::KeepRelativeOffset, false);
	if (Component)
	{
		OwnedEffects.Add(Component);
		ReleaseLater(Component, Seconds, EndEffect);
	}
}

FTimerHandle& UAuroraSkillComponent::AddReleaseTimer()
{
	// 이미 끝난 예약은 비워 목록이 쌓이지 않게 한다.
	FTimerManager& Timers = GetWorld()->GetTimerManager();
	ReleaseTimers.RemoveAll([&Timers](const FTimerHandle& Handle) { return !Timers.TimerExists(Handle); });
	return ReleaseTimers.AddDefaulted_GetRef();
}

UStaticMeshComponent* UAuroraSkillComponent::SpawnTimedMesh(UStaticMesh* Mesh, const FTransform& Transform, float Seconds,
	UParticleSystem* EndEffect)
{
	if (!Mesh || !Character.IsValid() || !GetWorld())
	{
		return nullptr;
	}
	// 어디에도 붙이지 않아 세상 자리에 그대로 남는다.
	UStaticMeshComponent* Component = NewObject<UStaticMeshComponent>(Character.Get());
	// 충돌·내비 영향은 메시를 끼우기 전에 끈다 — SetStaticMesh가 그 순간의 설정(기본값은 충돌·내비 켜짐)으로 부품을 내비 목록에
	// 올리고, 등록 전이라 나중에 꺼도 빠지지 않는다. 그러면 움직이는 Q 검기 판·얼음 조각이 생길 때마다 둘레 내비가 다시 지어지며
	// 지나간 자리에 구멍이 남아 이동이 막혔다(10-20 「이동이 이상해졌다」, aurora-43rd-octlog).
	Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Component->SetCanEverAffectNavigation(false);
	Component->SetStaticMesh(Mesh);
	Component->SetMobility(EComponentMobility::Movable);
	Component->SetUsingAbsoluteLocation(true);
	Component->SetUsingAbsoluteRotation(true);
	Component->SetUsingAbsoluteScale(true);
	Component->SetWorldTransform(Transform);
	Component->RegisterComponent();
	OwnedMeshes.Add(Component);
	FTimerHandle& Handle = AddReleaseTimer();
	TWeakObjectPtr<UStaticMeshComponent> Weak = Component;
	GetWorld()->GetTimerManager().SetTimer(Handle, FTimerDelegate::CreateWeakLambda(this, [this, Weak, EndEffect]()
	{
		RemoveTimedMesh(Weak.Get(), EndEffect);
	}), Seconds, false);
	return Component;
}

void UAuroraSkillComponent::RemoveTimedMesh(UStaticMeshComponent* Component, UParticleSystem* EndEffect)
{
	if (!IsValid(Component))
	{
		return;
	}
	if (EndEffect && GetWorld())
	{
		UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), EndEffect, Component->GetComponentLocation(), Component->GetComponentRotation());
	}
	OwnedMeshes.Remove(Component);
	Component->DestroyComponent();
}

void UAuroraSkillComponent::ReleaseLater(UParticleSystemComponent* Effect, float Seconds, UParticleSystem* EndEffect)
{
	if (!IsValid(Effect) || !GetWorld())
	{
		return;
	}
	FTimerHandle& Handle = AddReleaseTimer();
	TWeakObjectPtr<UParticleSystemComponent> Weak = Effect;
	GetWorld()->GetTimerManager().SetTimer(Handle, FTimerDelegate::CreateWeakLambda(this, [this, Weak, EndEffect]()
	{
		if (Weak.IsValid() && EndEffect)
		{
			UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), EndEffect, Weak->GetComponentLocation(), Weak->GetComponentRotation());
		}
		ReleaseOwnedEffect(Weak.Get());
	}), Seconds, false);
}

void UAuroraSkillComponent::FinishCast()
{
	if (!bCasting)
	{
		return;
	}
	bCasting = false;
	++CastGeneration;
	if (GetWorld())
	{
		GetWorld()->GetTimerManager().ClearTimer(ActionTimer);
		GetWorld()->GetTimerManager().ClearTimer(RecoveryTimer);
	}
	StopFullBody();
	if (Character.IsValid() && Character->GetCharacterMovement())
	{
		Character->GetCharacterMovement()->bOrientRotationToMovement = bSavedOrientRotation;
	}
	ActiveSlot = INDEX_NONE;
	// Q1이 끝나면 Q2를 받기 시작한다. Q1 도중 눌러 둔 Q가 있으면 바로 벤다(Q1 끝 자세에서 Q2 첫 칼이 이어진다).
	const bool bWasWave = ActiveSkill == EAuroraSkill::FrostSlash && !bCrossCast && CVarAuroraSlashStyle.GetValueOnGameThread() == 5;
	const bool bQueued = bCrossQueued;
	bCrossCast = false;
	bCrossQueued = false;
	CrossWindowEnds = bWasWave && GetWorld() ? GetWorld()->GetTimeSeconds() + FrostCrossWindow : 0.0;
	if (bWasWave && bQueued && Character.IsValid())
	{
		BeginFrostCross(CrossAim);
	}
}

void UAuroraSkillComponent::CancelSkill()
{
	if (!bCasting)
	{
		return;
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_SKILL cancelled=%s"), *Skills[ActiveSkill].Name.ToString());
	if (GetWorld())
	{
		GetWorld()->GetTimerManager().ClearTimer(FieldTimer);
	}
	// 장판이 끊기면 회오리도 흩어진다(이미 내리꽂히는 중이면 그대로 둔다).
	CollapseVortex(false);
	EndGlacialCharge(true);
	EndLeap(true);
	FinishCast();
}

void UAuroraSkillComponent::PlayFullBody(UAnimSequence* Animation, float PlayRate, float StartTime, int32 LoopCount, float BlendIn)
{
	USkeletalMeshComponent* Mesh = Character.IsValid() ? Character->GetMesh() : nullptr;
	UAnimInstance* Anim = Mesh ? Mesh->GetAnimInstance() : nullptr;
	if (!Anim || !Animation || Animation->GetSkeleton() != Mesh->GetSkeletalMeshAsset()->GetSkeleton())
	{
		return;
	}
	// 같은 슬롯의 앞 몽타주(돌진 → 멈춤 동작)는 새 몽타주가 섞으며 넘겨받는다.
	// 배율은 재생할 때 한 번만 준다(1번 Countess와 같은 방식 — 만들 때도 주면 겹칠 수 있다).
	UAnimMontage* Montage = UAnimMontage::CreateSlotAnimationAsDynamicMontage(Animation, FullBodySlot, BlendIn,
		FullBodyBlendOut, 1.0f, FMath::Max(LoopCount, 1));
	if (!Montage)
	{
		return;
	}
	Anim->SetRootMotionMode(ERootMotionMode::IgnoreRootMotion);
	if (Anim->Montage_Play(Montage, PlayRate, EMontagePlayReturnType::Duration, StartTime) > 0.0f)
	{
		ActiveMontage = Montage;
	}
}

void UAuroraSkillComponent::BeginArmorPoseLock()
{
	USkeletalMeshComponent* Mesh = Character.IsValid() ? Character->GetMesh() : nullptr;
	if (!Mesh || !GetWorld())
	{
		return;
	}
	if (!bArmorPoseLocked)
	{
		ArmorMeshBase = Mesh->GetRelativeLocation();
	}
	bArmorPoseLocked = true;
	ArmorPelvisRest = Mesh->GetBoneLocation(ArmorPelvisBone, EBoneSpaces::ComponentSpace);
	// 94차 A 동작 시안은 시전·버팀이 길다(ApplyArmorTiming) — 정의에 들어간 값으로
	const FAuroraSkillDefinition& ArmorTimes = Skills[EAuroraSkill::IceArmor];
	ArmorPoseUntil = GetWorld()->GetTimeSeconds() + ArmorTimes.ActionTime + ArmorTimes.RecoveryTime + FullBodyBlendOut + 0.1f;
	GetWorld()->GetTimerManager().SetTimer(ArmorPoseTimer, this, &UAuroraSkillComponent::ArmorPoseTick, 1.0f / 60.0f, true);
}

void UAuroraSkillComponent::ArmorPoseTick()
{
	USkeletalMeshComponent* Mesh = Character.IsValid() ? Character->GetMesh() : nullptr;
	if (!Mesh || !GetWorld() || GetWorld()->GetTimeSeconds() >= ArmorPoseUntil || (bCasting && ActiveSkill != EAuroraSkill::IceArmor))
	{
		EndArmorPoseLock();
		return;
	}
	// 메시 공간 골반의 수평 어긋남을 캡슐 공간으로 돌려(메시는 -90도 돌아 있다) 그만큼 반대로 민다.
	const FVector Pelvis = Mesh->GetBoneLocation(ArmorPelvisBone, EBoneSpaces::ComponentSpace);
	const FVector Drift(Pelvis.X - ArmorPelvisRest.X, Pelvis.Y - ArmorPelvisRest.Y, 0.0f);
	Mesh->SetRelativeLocation(ArmorMeshBase - Mesh->GetRelativeRotation().RotateVector(Drift * Mesh->GetRelativeScale3D()));
}

void UAuroraSkillComponent::EndArmorPoseLock()
{
	if (GetWorld())
	{
		GetWorld()->GetTimerManager().ClearTimer(ArmorPoseTimer);
	}
	if (bArmorPoseLocked && Character.IsValid() && Character->GetMesh())
	{
		Character->GetMesh()->SetRelativeLocation(ArmorMeshBase);
	}
	bArmorPoseLocked = false;
}

void UAuroraSkillComponent::StopFullBody()
{
	USkeletalMeshComponent* Mesh = Character.IsValid() ? Character->GetMesh() : nullptr;
	UAnimInstance* Anim = Mesh ? Mesh->GetAnimInstance() : nullptr;
	// 끝나는 자세에서 보행 자세로 FullBodyBlendOut 동안 섞는다(그동안 이미 움직일 수 있다).
	if (Anim && ActiveMontage)
	{
		Anim->Montage_Stop(FullBodyBlendOut, ActiveMontage);
	}
	ActiveMontage = nullptr;
}

int32 UAuroraSkillComponent::ExecuteMeleeHit(float Range, float HalfAngle, float Damage, int32 ComboStep)
{
	if (!bEnabled || !Character.IsValid() || !GetWorld())
	{
		return 0;
	}
	const FVector Origin = Character->GetActorLocation();
	const FVector Forward = Character->GetActorForwardVector();
	const float MinDot = FMath::Cos(FMath::DegreesToRadians(HalfAngle));
	if (MeleeSnowflakes && CVarAuroraMeleeSnow.GetValueOnGameThread() != 0)
	{
		UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), MeleeSnowflakes, Origin + Forward * Range * 0.5f, Forward.Rotation());
	}
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_Pawn);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	FCollisionQueryParams Query(SCENE_QUERY_STAT(AuroraMelee), false, Character.Get());
	TArray<FOverlapResult> Overlaps;
	GetWorld()->OverlapMultiByObjectType(Overlaps, Origin, FQuat::Identity, Objects, FCollisionShape::MakeSphere(Range), Query);
	TSet<AActor*> HitActors;
	for (const FOverlapResult& Overlap : Overlaps)
	{
		AActor* Target = Overlap.GetActor();
		if (!IsCombatTarget(Target, Character.Get()) || !Target->CanBeDamaged() || HitActors.Contains(Target))
		{
			continue;
		}
		const FVector Offset = Target->GetActorLocation() - Origin;
		if (Offset.SizeSquared2D() > FMath::Square(Range) || FMath::Abs(Offset.Z) > 120.0f ||
			FVector::DotProduct(Forward, Offset.GetSafeNormal2D()) < MinDot)
		{
			continue;
		}
		FHitResult Hit;
		// 벽 너머의 대상을 베지 않도록 시야를 확인한다.
		if (GetWorld()->LineTraceSingleByChannel(Hit, Origin, Target->GetActorLocation(), ECC_Visibility, Query)
			&& Hit.GetActor() != Target)
		{
			continue;
		}
		Hit = FHitResult(Target, Overlap.GetComponent(), Target->GetActorLocation() - Offset.GetSafeNormal2D() * 40.0f, -Forward);
		HitActors.Add(Target);
		UGameplayStatics::ApplyPointDamage(Target, Damage, Forward, Hit, Character->GetController(), Character.Get(), nullptr);
		if (MeleeImpact)
		{
			UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), MeleeImpact, Hit.ImpactPoint, (-Forward).Rotation());
		}
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_BASIC step=%d hits=%d"), ComboStep, HitActors.Num());
	return HitActors.Num();
}

UParticleSystemComponent* UAuroraSkillComponent::SpawnOwnedEffect(UParticleSystem* Effect, const FVector& Location, const FRotator& Rotation)
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

void UAuroraSkillComponent::SpawnBurstLater(UParticleSystem* Effect, const FVector& Location, float Scale, float Delay,
	const FRotator& Rotation)
{
	if (!Effect || !GetWorld())
	{
		return;
	}
	if (Delay <= 0.0f)
	{
		UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), Effect, Location, Rotation, FVector(Scale));
		return;
	}
	TWeakObjectPtr<UParticleSystem> WeakEffect = Effect;
	GetWorld()->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this,
		[this, WeakEffect, Location, Scale, Rotation]()
		{
			if (UParticleSystem* Template = WeakEffect.Get(); Template && GetWorld())
			{
				UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), Template, Location, Rotation, FVector(Scale));
			}
		}), Delay, false);
}

void UAuroraSkillComponent::DestroyEffectLater(UParticleSystemComponent* Effect, float Seconds)
{
	if (!IsValid(Effect) || !GetWorld())
	{
		return;
	}
	TWeakObjectPtr<UParticleSystemComponent> Weak = Effect;
	GetWorld()->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, [this, Weak]()
	{
		if (UParticleSystemComponent* Component = Weak.Get())
		{
			OwnedEffects.Remove(Component);
			Component->DestroyComponent();
		}
	}), Seconds, false);
}

UDecalComponent* UAuroraSkillComponent::SpawnFloorDecal(UMaterialInterface* Material, const FVector& Center, float Radius,
	float Seconds, float FadeIn, float FadeOut, float Width)
{
	if (!Material || !GetWorld())
	{
		return nullptr;
	}
	// 위에서 아래로 비추는 바닥 데칼(X = 비추는 깊이, Y = 그림 세로, Z = 그림 가로). 재질이 DecalLifetimeOpacity를 곱해
	// 나타남·사라짐이 부드럽다.
	UDecalComponent* Decal = UGameplayStatics::SpawnDecalAtLocation(GetWorld(), Material,
		FVector(FloorDecalDepth, Radius, Width > 0.0f ? Width : Radius), Center, FRotator(-90.0f, 0.0f, 0.0f), Seconds);
	if (Decal)
	{
		Decal->SetFadeIn(0.0f, FadeIn);
		// 소유자(세계 설정 액터)는 지우지 않는다.
		Decal->SetFadeOut(FMath::Max(Seconds - FadeOut, 0.0f), FadeOut, false);
	}
	return Decal;
}

void UAuroraSkillComponent::ReleaseOwnedEffect(UParticleSystemComponent* Effect)
{
	if (!IsValid(Effect))
	{
		return;
	}
	OwnedEffects.Remove(Effect);
	// 반복 입자는 새로 뿜는 것만 멈추고, 남은 입자가 사라지면 스스로 정리한다(E 둘레 결정처럼 멈춰 세운 입자도 제 속도로).
	Effect->CustomTimeDilation = 1.0f;
	Effect->bAutoDestroy = true;
	Effect->DeactivateSystem();
}

void UAuroraSkillComponent::GatherTargets(const FVector& Center, float Radius, TArray<AActor*>& Out) const
{
	if (!GetWorld())
	{
		return;
	}
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_Pawn);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	FCollisionQueryParams Query(SCENE_QUERY_STAT(AuroraArea), false, GetOwner());
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

int32 UAuroraSkillComponent::ApplyAreaDamage(const FVector& Center, float Radius, float Damage, FName Status, float StatusSeconds,
	TArray<AActor*>* OutTargets)
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
			if (Status == TEXT("STUN"))
			{
				RecordFrozen(Target, StatusSeconds);
			}
		}
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_AREA center=%s radius=%.0f damage=%.0f hits=%d"),
		*Center.ToCompactString(), Radius, Damage, Targets.Num());
	if (OutTargets)
	{
		*OutTargets = Targets;
	}
	return Targets.Num();
}

void UAuroraSkillComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	CancelSkill();
	SetHaste(false);
	EndHitStop();
	EndArmorPoseLock();
	EndRDraft();
	EndQAdd();
	if (GetWorld())
	{
		GetWorld()->GetTimerManager().ClearTimer(ActionTimer);
		GetWorld()->GetTimerManager().ClearTimer(RecoveryTimer);
		GetWorld()->GetTimerManager().ClearTimer(ShoveRestoreTimer);
		GetWorld()->GetTimerManager().ClearTimer(ShoveSlideTimer);
		GetWorld()->GetTimerManager().ClearTimer(DecoyTimer);
		GetWorld()->GetTimerManager().ClearTimer(CryoTimer);
		GetWorld()->GetTimerManager().ClearTimer(FieldTimer);
		GetWorld()->GetTimerManager().ClearTimer(ArmorTimer);
		GetWorld()->GetTimerManager().ClearTimer(HasteTimer);
		GetWorld()->GetTimerManager().ClearTimer(SpikeTimer);
		GetWorld()->GetTimerManager().ClearTimer(LanceTimer);
		GetWorld()->GetTimerManager().ClearTimer(FlakeTimer);
		GetWorld()->GetTimerManager().ClearTimer(ShardTimer);
		GetWorld()->GetTimerManager().ClearTimer(RuptureSpikeTimer);
		GetWorld()->GetTimerManager().ClearTimer(BladeTimer);
		GetWorld()->GetTimerManager().ClearTimer(SpearTimer);
		GetWorld()->GetTimerManager().ClearTimer(NovaTimer);
		for (FTimerHandle& Handle : ReleaseTimers)
		{
			GetWorld()->GetTimerManager().ClearTimer(Handle);
		}
	}
	ReleaseTimers.Reset();
	// 날던 분신(F 분신 돌격)은 캐릭터 부품이라 같이 지운다
	for (const FAuroraLance& Lance : Lances)
	{
		if (USkeletalMeshComponent* Clone = Lance.Clone.Get())
		{
			Clone->DestroyComponent();
		}
		EndLanceBird(Lance, false);
	}
	if (!ShovedTargets.IsEmpty())
	{
		RestoreShoved();
	}
	ClearVortex();
	// 캐릭터를 바꾸는 등으로 먼저 사라져도 얼음 석상으로 바꿔 둔 대상을 원래 재질로 돌려 놓는다.
	while (!Encased.IsEmpty())
	{
		AActor* Target = Encased.Last().Target.Get();
		if (!ReleaseEncased(Target, true))
		{
			Encased.Pop();
		}
	}
	for (UParticleSystemComponent* Effect : OwnedEffects)
	{
		if (IsValid(Effect))
		{
			Effect->DestroyComponent();
		}
	}
	OwnedEffects.Reset();
	for (UStaticMeshComponent* Mesh : OwnedMeshes)
	{
		if (IsValid(Mesh))
		{
			Mesh->DestroyComponent();
		}
	}
	OwnedMeshes.Reset();
	bEnabled = false;
	Super::EndPlay(EndPlayReason);
}
