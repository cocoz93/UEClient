// D 새 시안(10-26 「내가 준 레퍼런스(메이플 블리자드류 영상) 참고하지 말고 니가 자유롭게 시안 여러 개 — 계속 겉돈다, 근본적인 이펙트
// 퀄리티나 디자인이 마음에 안 든다」). 그 전 판들은 팩 결정·연기·고리를 겹쳐 가며 다듬어 색과 모양이 제각각 뭉개졌다 → 팩 이펙트를 하나도
// 쓰지 않고, 한 벌의 빛 그림(aurora_dfx_textures.py — 빛줄기 · 별빛 · 고리 · 빛 결정 · 결계 원)을 더하기 재질(M_Aurora_FxAdd)로 엔진 판에
// 붙여 때를 맞춰 움직인다(DPieceTick). 겨누는 자리·기울기·시전 동작(칼을 땅에 꽂음)은 고드름 비 그대로(ExecuteIcicleRain이 넘긴다),
// 맞히기는 같은 규칙(맞을 때마다 피해 + 감속, 처음 맞힌 한 번만 멈칫). 피해 수치는 시안마다 임시값.
// 1 빛줄기 연사: 가는 빛줄기 14개가 빠르게 흩뿌려 꽂히고, 꽂힐 때마다 별빛 + 바닥 물결 + 서리 자국, 끝에 원 전체로 큰 물결.
// 2 공중 결정 일제 사격: 빛 결정 9개가 겨눈 자리 위 하늘에 끝부터 하나씩 생겨 떠 있다가, 다 생기면 잇달아 내리꽂힌다. 끝에 원 전체가 언다.
// 3 얼음 결계: 바닥에 결계 원이 그려지고, 둘레를 따라 빛 결정 12개가 바깥에서 안쪽으로 비스듬히 꽂힌 뒤, 고리가 가운데로 빨려 들었다가
//   한가운데가 터진다.
// 이어서 「2, 3 괜찮은 것 같은데 퀄리티를 높이거나 다양한 방식으로 또 시안 여러 개」:
// 4 = 2 다듬음: 꽂힐 자리에 옅은 표시가 미리 뜨고, 쏘는 순간 결정 머리가 번쩍, 꽂히면 빛 결정 조각이 튀고 얼음 가루가 피어오르며,
//   박혀 있던 결정도 조각으로 부서진다.
// 5 = 3 다듬음: 결계가 그려질 때 빛 하나가 원을 따라 달리고, 빨려 들 때 둘레 결정에서 빛 알갱이가 가운데로 모이며, 터질 때 빛기둥이
//   솟고 결계가 한 번 밝게 번쩍, 둘레 결정은 조각으로 부서진다.
// 6 하늘 왕관 수렴: 결정 10개가 원 위 하늘에 고리(왕관)로 생겨 천천히 돌며 모두 한가운데를 겨누다가, 한꺼번에 한 점으로 내리꽂혀 크게 터진다.
// 7 회전 소용돌이: 결정 8개가 원 위에서 빠르게 돌다가 하나씩 떨어져 나와 바깥에서 안쪽으로 소용돌이를 그리며 꽂히고, 마지막이 가운데.
// 8 거대 결정: 하늘에 큰 결정 하나가 빛을 빨아들이며 자라나 한가운데에 꽂히고, 잠시 뒤 부서진 조각들이 둘레로 쏟아져 꽂힌다.
// 10-26 「얼음 결계는 원 바깥선에 얼음이 박히는 아이디어를 살려 S 마법진에 · 궁극기는 일반 스킬로 빼고 마법사 캐릭터처럼 광역기로,
// 계속 블리자드처럼 얼음송곳이 쏟아지는 느낌」 → 같은 빛 조각으로 S 둘레 얼음(HasteRimIce)과 V 눈보라(ExecuteBlizzard)를 맡는다.
// D는 옛 궁극기가 되어 위 시안 1~8과 고드름 비는 눈보라 시안 0(Aurora.FX.VStorm)으로만 닿는다.
#include "AuroraSkillComponent.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/DecalComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Texture.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "KwangTrainingDummy.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Particles/ParticleSystemComponent.h"
#include "TimerManager.h"
#include "TopDownCombatCharacter.h"

namespace
{
	TAutoConsoleVariable<int32> CVarAuroraDFresh(
		TEXT("Aurora.FX.DFresh"), 0,
		TEXT("Fresh D drafts built only from Aurora's own light pictures (no pack effects): 0 the icicle rain as it is (default), 1 a barrage of thin light streaks with star flashes and ground ripples, 2 light shards form one by one in the sky over the circle and then fire down in a volley, 3 a ward circle draws on the floor, shards strike all round its rim pointing inward, then a ring is sucked into the middle and it bursts, 4 draft 2 polished (landing marks, launch flashes, shard fragments, rising frost dust), 5 draft 3 polished (a light runs round the ward, motes drawn in, a light pillar and ward flash at the burst), 6 a crown of shards circles in the sky aiming at the middle and all plunge into one point, 7 shards whirl above the circle and peel off one by one spiralling inward, 8 one huge shard grows in the sky drinking in light, strikes the middle and shatters into fragments that rain round it."));

	// 10-26 「얼음 결계는 원 바깥선에 얼음이 박히는 아이디어를 살려 S 마법진에 넣는 건 어때 — 5번」: 시안 5의 둘레 결정만(원을 달리는 빛 ·
	// 빨려 듦 · 가운데 터짐은 S가 터지는 스킬이 아니라 뺌)
	TAutoConsoleVariable<int32> CVarAuroraHasteIce(
		TEXT("Aurora.FX.SIce"), 1,
		TEXT("Frost Haste rim ice: 1 light shards strike one after another round the circle's outer line, slanting inward, and stay planted until the floor goes (default), 0 none."));
	// 같은 날 V 눈보라 러프 시안 → 「시전만 하고 바로 움직이게 · 범위는 두 배 정도 · 얼음 쏟아지는 건 나쁘지 않은데 누가 봐도 궁극기로 보이게
	// 화려하게 · 눈발도 저렇게 날리는 게 아니라 맵 전체에 눈보라가 쏟아지는 느낌」 → 1(화면 어둡게는 말씀에 없던 것이라 2에서 뺌)
	TAutoConsoleVariable<int32> CVarAuroraStorm(
		TEXT("Aurora.FX.VStorm"), 1,
		TEXT("Blizzard (V): 1 a big seal unfolds where she aims, light shards pour down slanting with the wind all over it for 4 seconds with a big spear every eighth, then a giant shard strikes the middle and the whole circle bursts, while snow storms down over the whole screen and the screen dims (default), 2 = 1 without the dimming, 0 the old D (icicle rain) instead."));

	// 10-26 「2번 캐릭터 F 스킬을 눈색·하얀색·파란색으로 — 매 날리기 빼고 넣어 봐」 → 「전혀 2번 F 느낌이 아니다」로 원본대로 고친 뒤
	// 「그냥 캐릭터 뒤쪽에 얼음 덩어리들이 각자 덩어리를 만들고, 여러 명을 타겟팅해서 공격하는 느낌」 → 1
	// 94차 「V도 너무 아쉬운데 시안 여러 개」 — 마법진·빛 조각·끝 빛기둥(직접 그린 그림) 대신 팩 원본 효과로. 피해(떨어지는 자리·때·크기)는
	// 그대로 두고 그림만 바꾼다(빛 조각은 안 그리고 맞는 것만). 화면 눈보라는 셋 다 그대로
	TAutoConsoleVariable<int32> CVarAuroraVLook(
		TEXT("Aurora.FX.VLook"), 2,
		TEXT("Blizzard (V) look, in the same language as D: 2 a bombardment - Aurora's freezing explosions each with a frost shockwave ring going off one after another all over the circle, then a huge freezing explosion with two rings in the middle (default), 3 frozen ground - a huge freezing burst and two rings sweep the circle, every enemy in it stays sealed in ice while ice crystals burst round them, then the same huge explosion, (95th) 4 a spiral of the same explosions winding out from the middle, 5 three great pulses - a huge freezing burst and two rings to the edge every 1.3 s with crystals bursting round the rim, 6 closing in - a wall of explosions round the edge, then a middle ring, then the middle, 1 the drawn seal with light shards pouring down and a giant shard."));
	TAutoConsoleVariable<int32> CVarAuroraCrystalShot(
		TEXT("Aurora.FX.FShot"), 1,
		TEXT("F: 1 five ice clusters form one by one in a wing-like arc above and behind her while she raises the sword, then fire one after another as ice spears at up to five enemies nearest where she aims (default), 0 the old ice lance hawk."));

	UTexture* LoadFreshTexture(const TCHAR* Name)
	{
		return TSoftObjectPtr<UTexture>(FSoftObjectPath(FString::Printf(TEXT("/Game/TopDown/Characters/Aurora/FX/%s.%s"), Name, Name)))
			.LoadSynchronous();
	}

	UMaterialInterface* LoadFreshMaterial(const TCHAR* Name)
	{
		return TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(FString::Printf(TEXT("/Game/TopDown/Characters/Aurora/FX/%s.%s"), Name,
			Name))).LoadSynchronous();
	}

	// 0 그대로 · 1 점점 빠르게 · 2 점점 느리게
	float FreshEase(float Alpha, uint8 Ease)
	{
		Alpha = FMath::Clamp(Alpha, 0.0f, 1.0f);
		return Ease == 1 ? Alpha * Alpha : Ease == 2 ? 1.0f - FMath::Square(1.0f - Alpha) : Alpha;
	}

	// AuroraSkillComponent.cpp의 SetStatus와 같다(파일마다 이름을 달리 — 한 덩어리로 묶어 빌드할 때 겹치지 않게)
	void SetFreshStatus(AActor* Target, FName Status, float Seconds)
	{
		if (AKwangTrainingDummy* Dummy = Cast<AKwangTrainingDummy>(Target))
		{
			Dummy->SetCombatStatus(Status, Seconds);
		}
	}

	// 서리 자국(M_Aurora_FrostBurst)의 무늬 칸을 반경에 맞춘다 — 재질 기본값은 반경 90 기준이라 원 전체(300)에 깔면 서리 별무늬가 큰 흰 별
	// 스티커처럼 보였다(76차 첫 촬영). 넓을수록 조금 옅게.
	void ScaleFreshFrost(UDecalComponent* Decal, float Radius)
	{
		if (UMaterialInstanceDynamic* Dynamic = Decal ? Cast<UMaterialInstanceDynamic>(Decal->GetDecalMaterial()) : nullptr)
		{
			const float Ratio = Radius / 90.0f;
			Dynamic->SetScalarParameterValue(TEXT("FrostTiling"), 1.2f * Ratio);
			Dynamic->SetScalarParameterValue(TEXT("EdgeTiling"), 1.5f * Ratio);
			Dynamic->SetScalarParameterValue(TEXT("PatchTiling"), 0.6f * Ratio);
			Dynamic->SetScalarParameterValue(TEXT("FillOpacity"), Ratio > 2.0f ? 0.3f : 0.4f);
		}
	}

	// 원 반경 안 해바라기 배치의 (Index × Stride) % Count번째 자리 — 차례대로 골라도 한쪽으로 몰리지 않는다(Stride와 Count는 서로소)
	FVector FreshSeat(const FVector& Center, int32 Index, int32 Count, int32 Stride, float Radius)
	{
		const int32 Seat = (Index * Stride) % Count;
		const float Reach = Radius * 0.92f * FMath::Sqrt((Seat + 0.5f) / Count);
		const float Angle = Seat * PI * (3.0f - FMath::Sqrt(5.0f));
		return Center + FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.0f) * Reach;
	}

	FVector FreshAround(float Angle)
	{
		return FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.0f);
	}

	// 공통: 원 반경(고드름 비와 같음) · 첫 멈칫 · 감속
	constexpr float FreshRadius = 260.0f;
	constexpr float FreshHitStopSeconds = 0.05f;
	constexpr float FreshSlowSeconds = 1.0f;
	// 고리 그림의 심은 판 반쪽의 0.82 — 보이는 고리 반경 r이면 판 크기 = 2r / 0.82
	constexpr float FreshRingCore = 0.82f;
	// 꽂힌 자리 번쩍임(크기 배율 1): 별빛 크기(처음 → 끝) · 커지는 시간 · 사는 시간 · 흐려짐 · 카메라 쪽으로 당김 / 바닥 물결 고리 반경 ·
	// 퍼지는 시간 · 사는 시간 · 흐려짐 · 진하기 / 빛 세기 · 닿는 거리 · 시간
	constexpr float ImpactStarFrom = 50.0f;
	constexpr float ImpactStarTo = 150.0f;
	constexpr float ImpactStarGrow = 0.12f;
	constexpr float ImpactStarLife = 0.24f;
	constexpr float ImpactStarFade = 0.16f;
	constexpr float ImpactStarLift = 80.0f;
	constexpr float ImpactRippleFrom = 12.0f;
	constexpr float ImpactRippleTo = 65.0f;
	constexpr float ImpactRippleGrow = 0.3f;
	constexpr float ImpactRippleLife = 0.34f;
	constexpr float ImpactRippleFade = 0.22f;
	// 첫 촬영은 물결 0.9 · 빛 60 · 280 — 꽂힌 자리마다 흰 원이 겹쳐 방울 무더기가 되고, 빛이 바닥을 뿌옇게 덮었다
	constexpr float ImpactRippleStrength = 0.5f;
	constexpr float ImpactLight = 20.0f;
	constexpr float ImpactLightRadius = 220.0f;
	constexpr float ImpactLightSeconds = 0.22f;

	// 1 빛줄기 연사: 수 · 사이 · 고르는 간격 · 떨어지기 시작하는 거리(비스듬히 위) · 떨어지는 시간 · 꽂힌 뒤 꼬리가 머리로 빨려 드는 시간 ·
	// 길이 · 굵기 · 맞는 반경 · 피해 / 꽂힌 자리 서리 자국(M_Aurora_FrostBurst, 75차 DMark 1과 같은 재질) 반경 · 번짐 / 마지막 뒤 큰 물결까지 ·
	// 큰 물결 반경 · 퍼지는 시간
	constexpr int32 StreakCount = 14;
	constexpr float StreakInterval = 0.05f;
	constexpr int32 StreakStride = 5;
	constexpr float StreakDrop = 700.0f;
	constexpr float StreakFall = 0.09f;
	constexpr float StreakRetract = 0.07f;
	constexpr float StreakLength = 360.0f;
	constexpr float StreakWidth = 16.0f;
	constexpr float StreakHitRadius = 95.0f;
	constexpr float StreakDamage = 6.0f;
	constexpr float StreakFrostRadius = 70.0f;
	constexpr float StreakFrostSweep = 0.12f;
	constexpr float StreakFinaleDelay = 0.2f;
	constexpr float StreakFinaleRadius = 262.0f;
	constexpr float StreakFinaleSeconds = 0.45f;

	// 2·4 공중 결정 일제 사격: 수 · 생기는 사이 · 고르는 간격 · 끝부터 다 자라는 시간 · 다 생긴 뒤 쏘기까지 · 쏘는 사이 · 떠 있는 자리(꽂힐
	// 자리에서 떨어지는 길을 거슬러) · 떨어지는 시간 · 박히는 깊이 · 박혀 있는 시간 · 결정 굵기 · 길이 · 위아래 흔들림 · 맞는 반경 · 피해 /
	// 끝에 원 전체가 어는 서리 반경 · 번짐
	constexpr int32 VolleyCount = 9;
	constexpr float VolleyAppear = 0.045f;
	constexpr int32 VolleyStride = 4;
	constexpr float VolleyGrow = 0.12f;
	constexpr float VolleyHold = 0.15f;
	constexpr float VolleyFireInterval = 0.035f;
	// 첫 촬영 480은 결정 몇 개가 화면 위 끝에 걸렸다
	constexpr float VolleyHover = 380.0f;
	constexpr float VolleyFall = 0.08f;
	constexpr float VolleyEmbed = 30.0f;
	constexpr float VolleyStuck = 0.3f;
	constexpr float VolleyWidth = 34.0f;
	constexpr float VolleyLength = 160.0f;
	constexpr float VolleyBob = 5.0f;
	constexpr float VolleyHitRadius = 100.0f;
	constexpr float VolleyDamage = 8.0f;
	constexpr float VolleyFrostRadius = 300.0f;
	constexpr float VolleyFrostSweep = 0.25f;
	// 4: 꽂힐 자리 표시 고리 반경(처음 → 끝) · 진하기
	constexpr float VolleyMarkFrom = 10.0f;
	constexpr float VolleyMarkTo = 32.0f;
	constexpr float VolleyMarkStrength = 0.35f;

	// 3·5 얼음 결계: 결계 원 반경 · 그려지는 시간 / 둘레 결정 수 · 가운데에서 떨어진 거리 · 첫 결정까지 · 사이 · 수직에서 기운 각(안쪽으로) ·
	// 떨어지기 시작하는 거리 · 떨어지는 시간 · 박히는 깊이 · 굵기 · 길이 · 맞는 반경 · 피해 / 마지막이 꽂힌 뒤 빨려 들기까지 · 빨려 드는 시간 ·
	// 한가운데 터짐 크기 · 피해 · 서리 반경 · 번짐
	constexpr float WardRadius = 300.0f;
	constexpr float WardSweep = 0.25f;
	constexpr int32 WardCount = 12;
	constexpr float WardReach = 235.0f;
	constexpr float WardStart = 0.18f;
	constexpr float WardInterval = 0.04f;
	constexpr float WardSlantDegrees = 35.0f;
	constexpr float WardDrop = 520.0f;
	constexpr float WardFall = 0.08f;
	constexpr float WardEmbed = 25.0f;
	constexpr float WardWidth = 28.0f;
	constexpr float WardLength = 140.0f;
	constexpr float WardHitRadius = 80.0f;
	constexpr float WardDamage = 4.0f;
	constexpr float WardImplodeDelay = 0.12f;
	constexpr float WardImplodeSeconds = 0.2f;
	constexpr float WardBlastScale = 2.2f;
	constexpr float WardBlastDamage = 18.0f;
	constexpr float WardFrostRadius = 280.0f;
	constexpr float WardFrostSweep = 0.15f;
	// 5: 결계 원 바깥 고리 자리(결계 그림의 0.93) · 달리는 빛 크기 · 터질 때 빛기둥 굵기 · 높이
	constexpr float WardRimAt = 0.93f;
	constexpr float WardRunnerSize = 80.0f;
	constexpr float WardPillarWidth = 110.0f;
	constexpr float WardPillarHeight = 520.0f;

	// 6 하늘 왕관 수렴: 수 · 고리 반경 · 높이 · 도는 빠르기(라디안/초) · 생기는 사이 · 자라는 시간 · 다 생긴 뒤 쏘기까지 · 떨어지는 시간 ·
	// 박히는 깊이 · 가운데에서 꽂히는 자리 거리 · 박혀 있는 시간 · 굵기 · 길이 / 터짐 크기 · 맞는 반경 · 피해 · 서리 반경
	constexpr int32 CrownCount = 10;
	// 첫 촬영 220 · 330은 고리 위쪽 결정이 화면 위 끝에 걸렸다
	constexpr float CrownRadius = 190.0f;
	constexpr float CrownHeight = 250.0f;
	constexpr float CrownSpin = 1.2f;
	constexpr float CrownAppear = 0.04f;
	constexpr float CrownGrow = 0.12f;
	constexpr float CrownHold = 0.18f;
	constexpr float CrownFall = 0.12f;
	constexpr float CrownEmbed = 30.0f;
	constexpr float CrownLandReach = 28.0f;
	constexpr float CrownStuck = 0.3f;
	constexpr float CrownWidth = 30.0f;
	constexpr float CrownLength = 150.0f;
	constexpr float CrownBlastScale = 2.4f;
	constexpr float CrownHitRadius = 280.0f;
	constexpr float CrownDamage = 30.0f;
	constexpr float CrownFrostRadius = 280.0f;

	// 7 회전 소용돌이: 수 · 도는 반경 · 높이 · 도는 빠르기 · 생기는 사이 · 자라는 시간 · 떨어져 나오기 시작 · 사이 · 떨어지는 시간 ·
	// 꽂히는 자리 반경(첫 → 마지막) · 박히는 깊이 · 굵기 · 길이 · 맞는 반경 · 피해
	constexpr int32 OrbitCount = 8;
	constexpr float OrbitRingRadius = 210.0f;
	// 첫 촬영 300은 위쪽 결정이 화면 위 끝에 걸렸다
	constexpr float OrbitHeight = 240.0f;
	constexpr float OrbitSpin = 3.0f;
	constexpr float OrbitAppear = 0.04f;
	constexpr float OrbitGrow = 0.1f;
	constexpr float OrbitPeelStart = 0.55f;
	constexpr float OrbitPeelInterval = 0.065f;
	constexpr float OrbitFall = 0.1f;
	constexpr float OrbitLandOuter = 230.0f;
	constexpr float OrbitLandInner = 20.0f;
	constexpr float OrbitEmbed = 30.0f;
	constexpr float OrbitWidth = 30.0f;
	constexpr float OrbitLength = 140.0f;
	constexpr float OrbitHitRadius = 100.0f;
	constexpr float OrbitDamage = 7.0f;

	// 8 거대 결정: 굵기 · 길이 · 떠 있는 자리(떨어지는 길을 거슬러) · 자라는 시간 · 다 자란 뒤 · 떨어지는 시간 · 박히는 깊이 · 박혀 있는 시간 /
	// 맞는 반경 · 피해 · 서리 반경 / 부서진 조각 수 · 굵기 · 길이 · 날아가는 시간 · 꽂히는 자리 반경(안 · 밖) · 맞는 반경 · 피해
	constexpr float BigWidth = 90.0f;
	constexpr float BigLength = 420.0f;
	// 첫 촬영 380은 결정 머리가 화면 위 끝에 붙었다
	constexpr float BigHover = 300.0f;
	constexpr float BigGrow = 0.3f;
	constexpr float BigHold = 0.15f;
	constexpr float BigFall = 0.12f;
	constexpr float BigEmbed = 50.0f;
	constexpr float BigStuck = 0.25f;
	constexpr float BigHitRadius = 200.0f;
	constexpr float BigDamage = 20.0f;
	constexpr float BigFrostRadius = 200.0f;
	constexpr int32 BigShardCount = 10;
	constexpr float BigShardWidth = 18.0f;
	constexpr float BigShardLength = 75.0f;
	constexpr float BigShardFlight = 0.2f;
	constexpr float BigShardInner = 130.0f;
	constexpr float BigShardOuter = 260.0f;
	constexpr float BigShardHitRadius = 70.0f;
	constexpr float BigShardDamage = 3.0f;

	// 떨어지는 결정 뒤 빛줄기(2~8): 굵기 · 길이 · 꽂힌 뒤 사라지는 시간 / 결정이 부서질 때 반짝임 크기
	constexpr float DiveTrailWidth = 20.0f;
	constexpr float DiveTrailLength = 300.0f;
	constexpr float DiveTrailFade = 0.08f;
	constexpr float ShatterGlint = 90.0f;
	// 빛 결정 밝기(퍼진 빛 · 흰 심) — 재질 기본(2.5 · 5)은 흰 심이 넘쳐 하얀 종이 오린 것처럼 보였다
	constexpr float ShardGlow = 3.0f;
	constexpr float ShardCoreGlow = 2.0f;

	// S 둘레 얼음: 수 · 결정 끝이 꽂히는 자리(장판 반경 배율 — 그림 바깥 두 줄 0.98·0.90 바로 안, 비스듬한 몸통이 두 줄을 넘는다) ·
	// 첫 결정까지 · 사이(장판이 드러나는 HasteRevealSeconds 안에 한 바퀴) · 수직에서 안쪽으로 기운 각 · 떨어지기 시작하는 거리 · 떨어지는 시간 ·
	// 박히는 깊이 · 굵기 · 길이(결계 300의 28 × 140보다 크게 — 원이 세 배) · 꽂힌 자리 번쩍임 크기 · 튀는 조각 수
	constexpr int32 HasteIceCount = 24;
	constexpr float HasteIceReach = 0.85f;
	constexpr float HasteIceStart = 0.05f;
	constexpr float HasteIceInterval = 0.02f;
	constexpr float HasteIceSlantDegrees = 35.0f;
	constexpr float HasteIceDrop = 600.0f;
	constexpr float HasteIceFall = 0.08f;
	constexpr float HasteIceEmbed = 25.0f;
	constexpr float HasteIceWidth = 36.0f;
	constexpr float HasteIceLength = 180.0f;
	constexpr float HasteIceImpact = 0.55f;
	constexpr int32 HasteIceChips = 3;

	// V 눈보라: 원 반경(10-26 「범위는 지금보다 훨씬 크게 두 배 정도」 400 → 800, Gideon 블랙홀 450) · 결정이 쏟아지는 시간(블랙홀 3.5초
	// 남짓) · 첫 결정까지(마법진이 펼쳐진 뒤) · 결정 수(초당 60 — 넓이가 네 배라 앞 판 120의 두 배) · 자리 고르는 간격(수와 서로소) ·
	// 몇 번째마다 원 안 적 자리로 · 그 자리에서 흩뜨림 · 바람 기울기(수직에서 — 오로라 쪽 하늘에서 겨눈 쪽으로, 고드름 비 25) · 기울기 흩뜨림 ·
	// 바람 방향 흩뜨림(도) · 떨어지기 시작하는 거리 · 떨어지는 시간 · 박히는 깊이 · 박혀 있는 시간 · 굵기 · 길이(작은 것 ~ 큰 것) · 맞는 반경 ·
	// 꽂힌 자리 번쩍임 크기 · 몇 번째마다 조각이 튀나
	// 앞 판(반경 400): 첫 촬영 64(초당 16) · 떨어지는 0.09초 · 굵기 22~34 · 길이 110~170은 한 장면에 한두 개만 보여 쏟아지는 느낌이 없었고,
	// 적을 셋째마다 겨누니 허수아비 자리에 번쩍임이 겹쳐 흰 덩어리가 됐다 → 120 · 0.15초 · 30~44 · 150~230 · 넷째마다
	constexpr float BlizzardRadius = 800.0f;
	// 94차 V 팩 효과 시안: 2 터짐 수 · 크기(오로라 빙결 터짐 · 람파지 결정) · 3 회오리 크기 · 붙잡는 때 · 붙잡은 빠르기 · 회오리 안 터짐 수 ·
	// 끝 큰 폭발 크기(빙결 폭발 · 빙결 터짐)
	// 첫 촬영(aurora-94th-rest): 빙결 터짐 16번 0.9배는 눈보라 화면에서 작은 연기로만 보였고, 키운 판(20번 1.6배)도 흰 연기 뭉치였다 →
	// D와 같은 빙결 폭발 + 고리로 바꾸고 수를 줄여 하나하나 크게. 3의 회오리는 R에서 「E와 겹친다」로 빠진 것이라 쓰지 않는다
	constexpr int32 VPackBlasts = 12;
	constexpr float VPackStartBlast = 2.0f;
	constexpr float VPackBlastScale = 1.1f;
	constexpr float VPackRockScale = 1.0f;
	constexpr float VPackRingRadius = 280.0f;
	constexpr float VPackRingSeconds = 0.35f;
	constexpr float VPackFreezeBlast = 3.0f;
	constexpr float VPackFreezeRingSeconds = 0.6f;
	constexpr int32 VPackFreezeBursts = 8;
	// 95차 「이전보다 낫긴 한데 여전히 아쉬움, 시안 더」: 4 나선(가운데 → 바깥으로 차례로) 터짐 수 · 바퀴 수 · 5 큰 파동 셋의 때 · 파동마다
	// 둘레 결정 수 · 6 조여 들기(바깥 고리 → 중간 고리 → 가운데) 바깥·중간 터짐 수 · 그 반경 비율
	constexpr int32 VSpiralBlasts = 18;
	constexpr float VSpiralTurns = 1.6f;
	constexpr float VPulseTimes[] = {0.35f, 1.65f, 2.95f};
	constexpr int32 VPulseRim = 6;
	constexpr int32 VCloseOuter = 10;
	constexpr int32 VCloseMiddle = 6;
	constexpr float VCloseOuterReach = 0.92f;
	constexpr float VCloseMiddleReach = 0.5f;
	constexpr float VPackFinaleExplode = 2.5f;
	constexpr float VPackFinaleBlast = 2.2f;
	constexpr float BlizzardSeconds = 4.0f;
	constexpr float BlizzardStart = 0.25f;
	constexpr int32 BlizzardSpikeCount = 240;
	constexpr int32 BlizzardStride = 7;
	constexpr int32 BlizzardAimEvery = 6;
	constexpr float BlizzardAimScatter = 60.0f;
	constexpr float BlizzardSlantDegrees = 28.0f;
	constexpr float BlizzardSlantScatter = 6.0f;
	constexpr float BlizzardYawScatter = 12.0f;
	constexpr float BlizzardDrop = 750.0f;
	constexpr float BlizzardFall = 0.15f;
	constexpr float BlizzardEmbed = 25.0f;
	constexpr float BlizzardStuck = 0.3f;
	// 10-26 「얼음송곳 좀 더 날카롭게, 이펙트 좀 다듬어」: 송곳 그림을 바늘 끝 T_Aurora_FxSpike로 · 굵기 30~44 → 24~34 · 길이 150~230 →
	// 190~280 · 뒤 빛줄기 0.7배. 꽂힌 자리는 별빛 + 물결 고리(안이 차 거품처럼 보임) 대신 바닥에 눕힌 얼음 튐(T_Aurora_FxSplash, 크기 cm) +
	// 작은 별빛 · 박혀 있다 사라질 때 BlizzardSnapEvery번째마다 부러진 조각 둘
	constexpr float BlizzardWidthMin = 24.0f;
	constexpr float BlizzardWidthMax = 34.0f;
	constexpr float BlizzardLengthMin = 190.0f;
	constexpr float BlizzardLengthMax = 280.0f;
	constexpr float BlizzardTrailScale = 0.7f;
	constexpr float BlizzardHitRadius = 90.0f;
	constexpr float BlizzardSplashSize = 120.0f;
	constexpr float BlizzardStar = 0.3f;
	constexpr int32 BlizzardChipEvery = 3;
	constexpr int32 BlizzardSnapEvery = 2;
	// 큰 창(BlizzardBigEvery번째마다 — 빛과 함께 크게 터짐): 굵기 · 길이(64 × 360 → 52 × 460) · 떨어지기 시작하는 거리 · 떨어지는 시간 ·
	// 맞는 반경 · 별빛 크기 · 얼음 튐 크기(퍼지는 고리 220은 거품처럼 보여 뺌) · 튀는 조각 수 · 거리
	constexpr int32 BlizzardBigEvery = 8;
	constexpr float BlizzardBigWidth = 52.0f;
	constexpr float BlizzardBigLength = 460.0f;
	constexpr float BlizzardBigDrop = 1000.0f;
	constexpr float BlizzardBigFall = 0.2f;
	constexpr float BlizzardBigHitRadius = 140.0f;
	constexpr float BlizzardBigImpact = 1.3f;
	constexpr float BlizzardBigSplashSize = 300.0f;
	constexpr int32 BlizzardBigChips = 6;
	constexpr float BlizzardBigChipReach = 120.0f;
	// 첫 촬영 마법진 0.8 · 1.6 · 테두리 0.35는 바깥 띠가 하얗게 떠 원 전체가 빛나는 판으로 보였다
	// 바닥 마법진(T_Aurora_BlizzardSeal — 바깥 고리가 그림 반쪽의 0.96): 펼쳐지는 시간(0.7배 → 1배) · 진하기 · 퍼진 빛 · 흰 심 · 도는 빠르기(도/초) /
	// 테두리 출렁이는 고리 진하기 · 도는 빠르기(마법진과 반대) / 펼쳐질 때 가운데에서 바깥 고리까지 퍼지는 충격파 시간 · 가운데 번쩍임 크기
	constexpr float BlizzardSealCore = 0.96f;
	constexpr float BlizzardSealOpen = 0.35f;
	constexpr float BlizzardSealStrength = 0.55f;
	constexpr float BlizzardSealGlow = 1.3f;
	constexpr float BlizzardSealCoreGlow = 2.5f;
	constexpr float BlizzardSealSpin = 8.0f;
	constexpr float BlizzardRimStrength = 0.15f;
	constexpr float BlizzardRimSpin = -6.0f;
	constexpr float BlizzardOpenWave = 0.35f;
	constexpr float BlizzardOpenFlash = 3.0f;
	// 마지막 거대 결정(쏟아짐이 끝나는 순간 거의 곧게 가운데로): 굵기 · 길이 · 떨어지기 시작하는 거리 · 떨어지는 시간 · 박히는 깊이 · 박혀 있는
	// 시간 · 수직에서 기운 각 · 뒤 빛줄기 길이 / 꽂힐 때 번쩍임 크기 · 원 전체 피해 · 튀는 조각 수 · 거리 · 조각 크기 · 피어오르는 얼음 가루 수 ·
	// 빛기둥 굵기 · 높이 / 꽂힌 뒤 마법진·눈보라가 남는 시간
	// (10-26 「다 같이 부서짐」 — 송곳이 박힌 채 쌓였다가 가운데에서 금이 번지며 한꺼번에 부서짐 — 으로 바꿨다가 「별로 같다, 롤백」으로 되돌림)
	constexpr float BlizzardFinaleWidth = 150.0f;
	constexpr float BlizzardFinaleLength = 820.0f;
	constexpr float BlizzardFinaleDrop = 1300.0f;
	constexpr float BlizzardFinaleFall = 0.22f;
	constexpr float BlizzardFinaleEmbed = 60.0f;
	constexpr float BlizzardFinaleStuck = 0.6f;
	constexpr float BlizzardFinaleSlant = 12.0f;
	constexpr float BlizzardFinaleTrail = 700.0f;
	constexpr float BlizzardFinaleImpact = 4.0f;
	constexpr float BlizzardFinaleDamage = 20.0f;
	constexpr int32 BlizzardFinaleChips = 16;
	constexpr float BlizzardFinaleChipReach = 320.0f;
	constexpr float BlizzardFinaleChipScale = 1.8f;
	constexpr int32 BlizzardFinaleMotes = 40;
	constexpr float BlizzardPillarWidth = 220.0f;
	constexpr float BlizzardPillarHeight = 1000.0f;
	constexpr float BlizzardLinger = 0.8f;
	// 화면 전체 눈보라(10-26 「맵 전체에 눈보라가 쏟아지는 느낌」): 화면에 붙인 흐르는 눈 겹 셋 — 카메라 앞 거리 · 그림 되풀이 · 흐르는 빠르기
	// (그림/초 — 가로 · 세로) · 진하기. 가까운 겹일수록 눈송이가 굵고 빠르다. 판 한 변 = 거리 × BlizzardLayerCover(화면을 넉넉히 덮게) /
	// 들어오고 나가는 시간 / 화면 어둡게(M_Aurora_FxDim) 진하기
	struct FBlizzardLayer
	{
		float Distance;
		float Tiling;
		float SpeedX;
		float SpeedY;
		float Strength;
	};
	// 첫 촬영 가까운 겹 2.2 · 0.8 · 가운데 0.65는 눈송이가 굵은 얼룩으로 화면을 덮었다
	// 이어서 「눈이 너무 밀도가 높고 색이 진하다 — 밀도 낮추고 투명도 올려 줘」: 눈 그림의 눈송이를 절반 아래로(aurora_dfx_textures.py) +
	// 진하기 0.6 · 0.55 · 0.5 → 0.35 · 0.3 · 0.25
	constexpr FBlizzardLayer BlizzardLayers[] = {{350.0f, 2.8f, -0.10f, 0.55f, 0.35f}, {600.0f, 3.6f, -0.07f, 0.38f, 0.3f},
		{900.0f, 5.5f, -0.05f, 0.26f, 0.25f}};
	constexpr float BlizzardLayerCover = 3.2f;
	constexpr float BlizzardStormFadeIn = 0.5f;
	constexpr float BlizzardStormFadeOut = 0.8f;
	// 재질 Opacity 0.4 × 이 값(첫 촬영 1.0은 눈 겹이 더한 밝기에 묻혀 화면 가장자리가 시전 전보다 오히려 밝았다 — 74.5 → 77.9)
	constexpr float BlizzardDimStrength = 1.5f;
	constexpr float BlizzardDimDistance = 250.0f;
	// 반투명 그리는 차례: 어둡게 하는 판 → 빛 조각(0) → 눈 겹
	constexpr int32 BlizzardDimSort = -10;
	constexpr int32 BlizzardSnowSort = 10;
	// F 얼음 덩어리 일제 사격(10-26 「그냥 캐릭터 뒤쪽에 얼음 덩어리들이 각자 덩어리를 만들고, 여러 명을 타겟팅해서 공격하는 느낌」 — 그 전
	// Sparrow CrystalShot 꼴(몸 앞에 보석이 꽃잎처럼 모여 꿰뚫는 창 하나)은 「전혀 2번 F 느낌이 아니다」 뒤 원본대로 고쳤다가 이걸로 바꿈):
	// 덩어리 수 · 덩어리마다 보석 수 · 날개처럼 벌어지는 옆 폭(양끝까지) · 뒤로(가운데 · 양끝에서 더) · 높이(가운데 · 양끝에서 덜) · 하나씩 생기는
	// 사이 · 모이는 시간 · 보석이 모여드는 반지름 · 보석 굵기 · 길이 · 위아래 흔들림(cm · 초당 번) / 가운데 빛 크기 · 진하기 / 쏘는 사이 · 생길 때
	// 번쩍임 크기 / 날아가는 빠르기 · 창 굵기 · 길이 · 뒤 빛줄기 굵기 · 길이 / 대상이 없을 때 겨눈 자리 둘레로 흩뜨림 / 맞은 자리 조각 수 · 얼음 튐
	// 크기 · 감속 시간
	constexpr int32 ChunkCount = 5;
	// 첫 촬영 보석 셋 · 30 × 66 · 모인 반지름 18은 덩어리가 아니라 작은 결정 가지로 보였다
	constexpr int32 ChunkGems = 4;
	constexpr float ChunkSpread = 200.0f;
	constexpr float ChunkBack = 90.0f;
	constexpr float ChunkBackEdge = 40.0f;
	constexpr float ChunkHeight = 220.0f;
	constexpr float ChunkHeightDrop = 70.0f;
	constexpr float ChunkAppear = 0.05f;
	constexpr float ChunkForm = 0.25f;
	constexpr float ChunkGather = 70.0f;
	constexpr float ChunkGemWidth = 40.0f;
	constexpr float ChunkGemLength = 84.0f;
	constexpr float ChunkGemReach = 12.0f;
	constexpr float ChunkBob = 6.0f;
	constexpr float ChunkBobRate = 1.5f;
	constexpr float ChunkOrb = 60.0f;
	constexpr float ChunkOrbStrength = 0.5f;
	constexpr float ChunkFireInterval = 0.07f;
	constexpr float ChunkPop = 90.0f;
	constexpr float ChunkSpeed = 4000.0f;
	constexpr float ChunkSpearWidth = 34.0f;
	constexpr float ChunkSpearLength = 220.0f;
	constexpr float ChunkTrailWidth = 22.0f;
	constexpr float ChunkTrailLength = 520.0f;
	constexpr float ChunkMissScatter = 160.0f;
	constexpr int32 ChunkHitShards = 8;
	constexpr float ChunkSplash = 160.0f;
	constexpr float ChunkSlowSeconds = 1.0f;
	// 쏘는 차례 = 가운데부터 양옆으로 번갈아(덩어리 번호)
	constexpr int32 ChunkOrder[ChunkCount] = {2, 1, 3, 0, 4};
	// 보석 퍼진 빛 · 흰 심(85차 — 2.5 · 2.0은 모이면 하얗게 떠 면이 안 보였다)
	constexpr float ChunkGemGlow = 1.6f;
	constexpr float ChunkGemCore = 1.3f;

	// 덩어리 하나의 자리: 오로라 뒤 머리 위에 날개처럼 벌어진 활 꼴(가운데가 높고, 양끝은 낮고 더 뒤로)
	FVector ChunkSpot(const FVector& Feet, const FVector& Dir, int32 Index)
	{
		const FVector Right = FVector::CrossProduct(FVector::UpVector, Dir).GetSafeNormal();
		const float Side = ChunkCount > 1 ? 2.0f * Index / (ChunkCount - 1) - 1.0f : 0.0f;
		const float Edge = FMath::Abs(Side);
		return Feet + FVector(0.0f, 0.0f, ChunkHeight - ChunkHeightDrop * Edge) - Dir * (ChunkBack + ChunkBackEdge * Edge) + Right * Side * ChunkSpread;
	}

	// 덩어리 번호 → 쏘는 차례(ChunkOrder 안 자리)
	int32 ChunkTurn(int32 Index)
	{
		for (int32 Turn = 0; Turn < ChunkCount; ++Turn)
		{
			if (ChunkOrder[Turn] == Index)
			{
				return Turn;
			}
		}
		return Index;
	}
}

int32 UAuroraSkillComponent::GetDFresh() const
{
	return CVarAuroraDFresh.GetValueOnGameThread();
}

bool UAuroraSkillComponent::ExecuteDFresh(int32 Draft, const FVector& Center, const FVector& Toward)
{
	if (!GetWorld() || !LoadFreshTexture(TEXT("T_Aurora_FxShard")) || !LoadFreshMaterial(TEXT("M_Aurora_FxAdd")))
	{
		return false;
	}
	float Seconds = 0.0f;
	switch (Draft)
	{
	case 1: Seconds = DFreshStreaks(Center); break;
	case 2: Seconds = DFreshVolley(Center, Toward, false); break;
	case 3: Seconds = DFreshWard(Center, Toward, false); break;
	case 4: Seconds = DFreshVolley(Center, Toward, true); break;
	case 5: Seconds = DFreshWard(Center, Toward, true); break;
	case 6: Seconds = DFreshCrown(Center, Toward); break;
	case 7: Seconds = DFreshOrbit(Center, Toward); break;
	case 8: Seconds = DFreshBigShard(Center, Toward); break;
	default: return false;
	}
	DFreshLater(Seconds, [this, Draft]()
	{
		UE_LOG(LogTemp, Display, TEXT("AURORA_DFRESH end draft=%d hits=%d"), Draft, IcicleHits.Num());
	});
	UE_LOG(LogTemp, Display, TEXT("AURORA_DFRESH start draft=%d at=%s fall=%s"), Draft, *Center.ToCompactString(), *IcicleFall.ToCompactString());
	return true;
}

float UAuroraSkillComponent::DFreshStreaks(const FVector& Center)
{
	const double Now = GetWorld()->GetTimeSeconds();
	UTexture* Streak = LoadFreshTexture(TEXT("T_Aurora_FxStreak"));
	const TWeakObjectPtr<UMaterialInterface> WeakFrost = LoadFreshMaterial(TEXT("M_Aurora_FrostBurst"));
	const float FinaleAt = StreakInterval * (StreakCount - 1) + StreakFall + StreakFinaleDelay;
	for (int32 Index = 0; Index < StreakCount; ++Index)
	{
		const FVector Landing = FreshSeat(Center, Index, StreakCount, StreakStride, FreshRadius);
		const float At = StreakInterval * Index;
		// 머리가 꽂힐 자리로 곧게 떨어지고, 꽂히면 꼬리가 머리로 빨려 든다
		FAuroraDPiece Bolt;
		Bolt.Born = Now + At;
		Bolt.Life = StreakFall + StreakRetract;
		Bolt.Face = 2;
		Bolt.Axis = IcicleFall;
		Bolt.From = Landing - IcicleFall * StreakDrop;
		Bolt.To = Landing;
		Bolt.MoveSeconds = StreakFall;
		const float Length = StreakLength * FMath::FRandRange(0.8f, 1.2f);
		Bolt.SizeFrom = FVector2D(StreakWidth, Length);
		Bolt.SizeTo = FVector2D(StreakWidth, 0.0f);
		Bolt.GrowDelay = StreakFall;
		Bolt.GrowSeconds = StreakRetract;
		Bolt.GrowEase = 1;
		Bolt.FadeIn = 0.02f;
		Bolt.FadeOut = 0.0f;
		Bolt.Lift = 10.0f;
		AddDPiece(Streak, Bolt);
		const float FrostSeconds = FinaleAt - (At + StreakFall) + 0.6f;
		DFreshLater(At + StreakFall, [this, Landing, WeakFrost, FrostSeconds]()
		{
			DFreshImpact(Landing, 1.0f);
			DFreshStrike(Landing, StreakHitRadius, StreakDamage);
			ScaleFreshFrost(SweepFloorDecal(WeakFrost.Get(), Landing, FRotator(0.0f, FMath::FRandRange(0.0f, 360.0f), 0.0f).Vector(),
				StreakFrostRadius, FrostSeconds, StreakFrostSweep, -1.0f, 0.5f), StreakFrostRadius);
		});
	}
	// 끝: 원 전체로 큰 물결
	DFreshLater(FinaleAt, [this, Center]()
	{
		FAuroraDPiece Wave;
		Wave.Born = GetWorld()->GetTimeSeconds();
		Wave.Life = StreakFinaleSeconds + 0.05f;
		Wave.From = Wave.To = Center + FVector(0.0f, 0.0f, 3.0f);
		Wave.SizeFrom = FVector2D(2.0f * 30.0f / FreshRingCore);
		Wave.SizeTo = FVector2D(2.0f * StreakFinaleRadius / FreshRingCore);
		Wave.GrowSeconds = StreakFinaleSeconds;
		Wave.FadeOut = 0.3f;
		AddDPiece(LoadFreshTexture(TEXT("T_Aurora_FxRing")), Wave);
		AddDLight(Center, ImpactLight * 2.5f, StreakFinaleRadius * 1.6f, 0.35f);
	});
	return FinaleAt + StreakFinaleSeconds;
}

float UAuroraSkillComponent::DFreshVolley(const FVector& Center, const FVector& Toward, bool bPlus)
{
	const double Now = GetWorld()->GetTimeSeconds();
	UTexture* Shard = LoadFreshTexture(TEXT("T_Aurora_FxShard"));
	UTexture* Ring = LoadFreshTexture(TEXT("T_Aurora_FxRing"));
	const TWeakObjectPtr<UMaterialInterface> WeakFrost = LoadFreshMaterial(TEXT("M_Aurora_FrostBurst"));
	const float FireAt = VolleyAppear * (VolleyCount - 1) + VolleyGrow + VolleyHold;
	const float LastHit = FireAt + VolleyFireInterval * (VolleyCount - 1) + VolleyFall;
	for (int32 Index = 0; Index < VolleyCount; ++Index)
	{
		const FVector Landing = FreshSeat(Center, Index, VolleyCount, VolleyStride, FreshRadius);
		const FVector Head = Landing - IcicleFall * VolleyHover;
		const float Appear = VolleyAppear * Index;
		const float Fire = FireAt + VolleyFireInterval * Index;
		// 하늘에 끝부터 자라나 떠 있는다
		FAuroraDPiece Hover;
		Hover.Born = Now + Appear;
		Hover.Life = Fire - Appear;
		Hover.Face = 2;
		Hover.Axis = IcicleFall;
		Hover.From = Hover.To = Head;
		Hover.SizeFrom = FVector2D(VolleyWidth, 0.0f);
		Hover.SizeTo = FVector2D(VolleyWidth, VolleyLength);
		Hover.GrowSeconds = VolleyGrow;
		Hover.FadeIn = 0.05f;
		Hover.FadeOut = 0.0f;
		Hover.Bob = VolleyBob;
		Hover.BobRate = 1.4f;
		Hover.BobPhase = FMath::FRandRange(0.0f, 2.0f * PI);
		Hover.Lift = 10.0f;
		Hover.Glow = ShardGlow;
		Hover.CoreGlow = ShardCoreGlow;
		AddDPiece(Shard, Hover);
		DFreshLater(Appear, [this, Head]() { DFreshGlint(Head, ShatterGlint); });
		if (bPlus)
		{
			// 꽂힐 자리에 옅은 작은 고리가 미리 떠 있다가 꽂힐 때 사라진다 · 쏘는 순간 결정 머리가 번쩍
			FAuroraDPiece Mark;
			Mark.Born = Now + Appear + 0.05f;
			Mark.Life = Fire + VolleyFall - Appear - 0.05f;
			Mark.From = Mark.To = Landing + FVector(0.0f, 0.0f, 3.0f);
			Mark.SizeFrom = FVector2D(2.0f * VolleyMarkFrom / FreshRingCore);
			Mark.SizeTo = FVector2D(2.0f * VolleyMarkTo / FreshRingCore);
			Mark.GrowSeconds = 0.15f;
			Mark.FadeIn = 0.1f;
			Mark.FadeOut = 0.05f;
			Mark.Strength = VolleyMarkStrength;
			AddDPiece(Ring, Mark);
			DFreshLater(Fire, [this, Head]() { DFreshGlint(Head, ShatterGlint * 0.7f); });
		}
		// 잇달아 내리꽂힌다
		DFreshDive(Now + Fire, Head, Landing + IcicleFall * VolleyEmbed, IcicleFall, VolleyFall, VolleyStuck, FVector2D(VolleyWidth, VolleyLength),
			DiveTrailLength * (bPlus ? 1.3f : 1.0f));
		DFreshLater(Fire + VolleyFall, [this, Landing, bPlus]()
		{
			DFreshImpact(Landing, 0.85f);
			DFreshStrike(Landing, VolleyHitRadius, VolleyDamage);
			if (bPlus)
			{
				DFreshShatter(Landing, 5, 90.0f, 0.8f);
				DFreshMotes(Landing, 4, 40.0f);
			}
		});
		const FVector Middle = Landing - IcicleFall * (VolleyLength * 0.5f - VolleyEmbed);
		DFreshLater(Fire + VolleyFall + VolleyStuck - 0.06f, [this, Middle, bPlus]()
		{
			DFreshGlint(Middle, ShatterGlint * 0.8f);
			if (bPlus)
			{
				DFreshShatter(Middle, 4, 70.0f, 0.6f);
			}
		});
	}
	// 끝: 원 전체가 가운데부터 언다
	DFreshLater(LastHit + 0.05f, [this, Center, Toward, WeakFrost, bPlus]()
	{
		ScaleFreshFrost(SweepFloorDecal(WeakFrost.Get(), Center, Toward, VolleyFrostRadius, 1.0f, VolleyFrostSweep, -1.0f, 0.5f),
			VolleyFrostRadius);
		FAuroraDPiece Wave;
		Wave.Born = GetWorld()->GetTimeSeconds();
		Wave.Life = 0.45f;
		Wave.From = Wave.To = Center + FVector(0.0f, 0.0f, 3.0f);
		Wave.SizeFrom = FVector2D(2.0f * 40.0f / FreshRingCore);
		Wave.SizeTo = FVector2D(2.0f * VolleyFrostRadius / FreshRingCore);
		Wave.GrowSeconds = 0.4f;
		Wave.FadeOut = 0.25f;
		AddDPiece(LoadFreshTexture(TEXT("T_Aurora_FxRing")), Wave);
		AddDLight(Center, ImpactLight * 2.5f, VolleyFrostRadius * 1.6f, 0.35f);
		if (bPlus)
		{
			DFreshMotes(Center, 14, VolleyFrostRadius * 0.8f);
		}
	});
	return LastHit + 0.5f;
}

float UAuroraSkillComponent::DFreshWard(const FVector& Center, const FVector& Toward, bool bPlus)
{
	const double Now = GetWorld()->GetTimeSeconds();
	const FVector Up = FVector::UpVector;
	UTexture* Ring = LoadFreshTexture(TEXT("T_Aurora_FxRing"));
	const TWeakObjectPtr<UMaterialInterface> WeakFrost = LoadFreshMaterial(TEXT("M_Aurora_FrostBurst"));
	const TWeakObjectPtr<UMaterialInterface> WeakWard = LoadFreshMaterial(TEXT("M_Aurora_DWard"));
	const float LastHit = WardStart + WardInterval * (WardCount - 1) + WardFall;
	const float ImplodeAt = LastHit + WardImplodeDelay;
	const float BlastAt = ImplodeAt + WardImplodeSeconds;
	SweepFloorDecal(WeakWard.Get(), Center, Toward, WardRadius, BlastAt + 0.45f, WardSweep, -1.0f, 0.4f);
	const float Slant = FMath::DegreesToRadians(WardSlantDegrees);
	const float FrontAngle = FMath::Atan2(Toward.Y, Toward.X);
	if (bPlus)
	{
		// 결계가 그려지는 동안 빛 하나가 바깥 고리를 따라 한 바퀴 달린다(결계 원 B = 시계 방향, 둘레 결정과 같은 차례)
		FAuroraDPiece Runner;
		Runner.Born = Now;
		Runner.Life = WardSweep;
		Runner.Face = 1;
		Runner.OrbitCenter = Center + Up * 20.0f;
		Runner.OrbitRadius = WardRadius * WardRimAt;
		Runner.OrbitAngle = FrontAngle;
		Runner.OrbitRate = 2.0f * PI / WardSweep;
		Runner.SizeFrom = Runner.SizeTo = FVector2D(WardRunnerSize);
		Runner.FadeOut = 0.05f;
		Runner.SpinRate = 720.0f;
		Runner.Lift = 40.0f;
		AddDPiece(LoadFreshTexture(TEXT("T_Aurora_FxStar")), Runner);
	}
	TArray<FVector> Middles;
	for (int32 Index = 0; Index < WardCount; ++Index)
	{
		// 앞에서부터 결계가 그려지는 쪽으로 차례로(결계 원 B = 시계 방향)
		const FVector Landing = Center + FreshAround(FrontAngle + 2.0f * PI * Index / WardCount) * WardReach;
		const FVector Inward = (Center - Landing).GetSafeNormal2D();
		const FVector Fall = (Inward * FMath::Sin(Slant) - Up * FMath::Cos(Slant)).GetSafeNormal();
		const float At = WardStart + WardInterval * Index;
		DFreshDive(Now + At, Landing - Fall * WardDrop, Landing + Fall * WardEmbed, Fall, WardFall, BlastAt - At - WardFall,
			FVector2D(WardWidth, WardLength), DiveTrailLength);
		DFreshLater(At + WardFall, [this, Landing, bPlus]()
		{
			DFreshImpact(Landing, 0.55f);
			DFreshStrike(Landing, WardHitRadius, WardDamage);
			if (bPlus)
			{
				DFreshShatter(Landing, 3, 60.0f, 0.6f);
			}
		});
		Middles.Add(Landing - Fall * (WardLength * 0.5f - WardEmbed));
	}
	// 고리가 결계 둘레에서 가운데로 빨려 든다
	FAuroraDPiece Implode;
	Implode.Born = Now + ImplodeAt;
	Implode.Life = WardImplodeSeconds;
	Implode.From = Implode.To = Center + Up * 3.0f;
	Implode.SizeFrom = FVector2D(2.0f * WardRadius / FreshRingCore);
	Implode.SizeTo = FVector2D(2.0f * 15.0f / FreshRingCore);
	Implode.GrowSeconds = WardImplodeSeconds;
	Implode.GrowEase = 1;
	Implode.FadeIn = 0.05f;
	Implode.FadeOut = 0.0f;
	AddDPiece(Ring, Implode);
	if (bPlus)
	{
		// 둘레 결정마다 빛 알갱이가 가운데로 빨려 든다
		DFreshLater(ImplodeAt, [this, Middles, Center]() { DFreshConverge(Middles, Center + FVector(0.0f, 0.0f, 40.0f), WardImplodeSeconds); });
	}
	// 한가운데가 터지고 둘레 결정이 함께 부서진다
	DFreshLater(BlastAt, [this, Center, Toward, WeakFrost, WeakWard, Middles, bPlus]()
	{
		DFreshImpact(Center, WardBlastScale);
		DFreshStrike(Center, WardRadius, WardBlastDamage);
		ScaleFreshFrost(SweepFloorDecal(WeakFrost.Get(), Center, Toward, WardFrostRadius, 1.0f, WardFrostSweep, -1.0f, 0.5f),
			WardFrostRadius);
		for (const FVector& Middle : Middles)
		{
			DFreshGlint(Middle, ShatterGlint * 0.7f);
			if (bPlus)
			{
				DFreshShatter(Middle, 3, 70.0f, 0.6f);
			}
		}
		if (bPlus)
		{
			DFreshPillar(Center, WardPillarWidth, WardPillarHeight);
			DFreshMotes(Center, 16, WardRadius * 0.85f);
			// 결계가 한 번 밝게 번쩍(같은 그림을 밝게 한 장 더 깔고 바로 흐린다)
			if (UDecalComponent* Flash = SweepFloorDecal(WeakWard.Get(), Center, Toward, WardRadius, 0.35f, 0.01f, -1.0f, 0.3f))
			{
				if (UMaterialInstanceDynamic* Dynamic = Cast<UMaterialInstanceDynamic>(Flash->GetDecalMaterial()))
				{
					Dynamic->SetScalarParameterValue(TEXT("LineGlow"), 6.0f);
					Dynamic->SetScalarParameterValue(TEXT("HaloOpacity"), 0.7f);
					Dynamic->SetScalarParameterValue(TEXT("Brightness"), 1.5f);
				}
			}
		}
	});
	return BlastAt + 0.4f;
}

float UAuroraSkillComponent::DFreshCrown(const FVector& Center, const FVector& Toward)
{
	const double Now = GetWorld()->GetTimeSeconds();
	const FVector Up = FVector::UpVector;
	UTexture* Shard = LoadFreshTexture(TEXT("T_Aurora_FxShard"));
	UTexture* Ring = LoadFreshTexture(TEXT("T_Aurora_FxRing"));
	const TWeakObjectPtr<UMaterialInterface> WeakFrost = LoadFreshMaterial(TEXT("M_Aurora_FrostBurst"));
	const FVector Hub = Center + Up * CrownHeight;
	const float FrontAngle = FMath::Atan2(Toward.Y, Toward.X);
	const float FireAt = CrownAppear * (CrownCount - 1) + CrownGrow + CrownHold;
	const float BlastAt = FireAt + CrownFall;
	// 바닥 한가운데에 모일 자리가 옅게 맥박친다
	FAuroraDPiece Mark;
	Mark.Born = Now + 0.1f;
	Mark.Life = BlastAt - 0.1f;
	Mark.From = Mark.To = Center + Up * 3.0f;
	Mark.SizeFrom = FVector2D(2.0f * 20.0f / FreshRingCore);
	Mark.SizeTo = FVector2D(2.0f * 90.0f / FreshRingCore);
	Mark.GrowSeconds = BlastAt - 0.1f;
	Mark.GrowEase = 0;
	Mark.FadeIn = 0.2f;
	Mark.FadeOut = 0.05f;
	Mark.Strength = 0.4f;
	AddDPiece(Ring, Mark);
	TArray<FVector> Planted;
	for (int32 Index = 0; Index < CrownCount; ++Index)
	{
		const float Seat = FrontAngle + 2.0f * PI * Index / CrownCount;
		const float Appear = CrownAppear * Index;
		// 고리로 천천히 돌며 머리가 늘 한가운데 바닥을 겨눈다
		FAuroraDPiece Hover;
		Hover.Born = Now + Appear;
		Hover.Life = FireAt - Appear;
		Hover.Face = 2;
		Hover.OrbitCenter = Hub;
		Hover.OrbitRadius = CrownRadius;
		Hover.OrbitAngle = Seat + CrownSpin * Appear;
		Hover.OrbitRate = CrownSpin;
		Hover.bAim = true;
		Hover.AimPoint = Center;
		Hover.SizeFrom = FVector2D(CrownWidth, 0.0f);
		Hover.SizeTo = FVector2D(CrownWidth, CrownLength);
		Hover.GrowSeconds = CrownGrow;
		Hover.FadeIn = 0.05f;
		Hover.FadeOut = 0.0f;
		Hover.Lift = 10.0f;
		Hover.Glow = ShardGlow;
		Hover.CoreGlow = ShardCoreGlow;
		AddDPiece(Shard, Hover);
		const FVector Born = Hub + FreshAround(Seat + CrownSpin * Appear) * CrownRadius;
		DFreshLater(Appear, [this, Born]() { DFreshGlint(Born, ShatterGlint); });
		// 한꺼번에 한 점으로 — 쏘는 때 자리에서 가운데 바로 옆으로
		const float FireSeat = Seat + CrownSpin * FireAt;
		const FVector Head = Hub + FreshAround(FireSeat) * CrownRadius;
		const FVector Landing = Center + FreshAround(FireSeat) * CrownLandReach;
		const FVector Axis = (Landing - Head).GetSafeNormal();
		DFreshDive(Now + FireAt, Head, Landing + Axis * CrownEmbed, Axis, CrownFall, CrownStuck, FVector2D(CrownWidth, CrownLength),
			DiveTrailLength * 1.2f);
		Planted.Add(Landing - Axis * (CrownLength * 0.5f - CrownEmbed));
	}
	DFreshLater(BlastAt, [this, Center, Toward, WeakFrost]()
	{
		DFreshImpact(Center, CrownBlastScale);
		DFreshStrike(Center, CrownHitRadius, CrownDamage);
		DFreshPillar(Center, WardPillarWidth * 1.2f, WardPillarHeight * 1.15f);
		DFreshShatter(Center, 12, 220.0f, 1.2f);
		DFreshMotes(Center, 16, CrownHitRadius * 0.8f);
		ScaleFreshFrost(SweepFloorDecal(WeakFrost.Get(), Center, Toward, CrownFrostRadius, 1.0f, 0.2f, -1.0f, 0.5f), CrownFrostRadius);
	});
	DFreshLater(BlastAt + CrownStuck - 0.06f, [this, Planted]()
	{
		for (const FVector& Middle : Planted)
		{
			DFreshGlint(Middle, ShatterGlint * 0.7f);
			DFreshShatter(Middle, 3, 60.0f, 0.6f);
		}
	});
	return BlastAt + 0.6f;
}

float UAuroraSkillComponent::DFreshOrbit(const FVector& Center, const FVector& Toward)
{
	const double Now = GetWorld()->GetTimeSeconds();
	const FVector Up = FVector::UpVector;
	UTexture* Shard = LoadFreshTexture(TEXT("T_Aurora_FxShard"));
	UTexture* Ring = LoadFreshTexture(TEXT("T_Aurora_FxRing"));
	const TWeakObjectPtr<UMaterialInterface> WeakFrost = LoadFreshMaterial(TEXT("M_Aurora_FrostBurst"));
	const FVector Hub = Center + Up * OrbitHeight;
	const float FrontAngle = FMath::Atan2(Toward.Y, Toward.X);
	const float LastHit = OrbitPeelStart + OrbitPeelInterval * (OrbitCount - 1) + OrbitFall;
	// 도는 동안 바닥 원 둘레가 옅게 빛난다
	FAuroraDPiece Rim;
	Rim.Born = Now + 0.05f;
	Rim.Life = LastHit;
	Rim.From = Rim.To = Center + Up * 3.0f;
	Rim.SizeFrom = Rim.SizeTo = FVector2D(2.0f * FreshRadius / FreshRingCore);
	Rim.FadeIn = 0.2f;
	Rim.FadeOut = 0.2f;
	// 첫 촬영 0.3은 바닥에 그린 표시 원처럼 진했다
	Rim.Strength = 0.12f;
	Rim.SpinRate = FMath::RadiansToDegrees(OrbitSpin);
	AddDPiece(Ring, Rim);
	TArray<FVector> Planted;
	for (int32 Index = 0; Index < OrbitCount; ++Index)
	{
		const float Seat = FrontAngle + 2.0f * PI * Index / OrbitCount;
		const float Appear = OrbitAppear * Index;
		const float Peel = OrbitPeelStart + OrbitPeelInterval * Index;
		// 떨어져 나오는 때의 자리 아래쪽으로, 차례가 늦을수록 안쪽에 꽂힌다(바깥 → 안 소용돌이)
		const float PeelSeat = Seat + OrbitSpin * Peel;
		const float Reach = FMath::Lerp(OrbitLandOuter, OrbitLandInner, static_cast<float>(Index) / (OrbitCount - 1));
		const FVector Landing = Center + FreshAround(PeelSeat + 0.6f) * Reach;
		FAuroraDPiece Hover;
		Hover.Born = Now + Appear;
		Hover.Life = Peel - Appear;
		Hover.Face = 2;
		Hover.OrbitCenter = Hub;
		Hover.OrbitRadius = OrbitRingRadius;
		Hover.OrbitAngle = Seat + OrbitSpin * Appear;
		Hover.OrbitRate = OrbitSpin;
		Hover.bAim = true;
		Hover.AimPoint = Landing;
		Hover.SizeFrom = FVector2D(OrbitWidth, 0.0f);
		Hover.SizeTo = FVector2D(OrbitWidth, OrbitLength);
		Hover.GrowSeconds = OrbitGrow;
		Hover.FadeIn = 0.05f;
		Hover.FadeOut = 0.0f;
		Hover.Lift = 10.0f;
		Hover.Glow = ShardGlow;
		Hover.CoreGlow = ShardCoreGlow;
		AddDPiece(Shard, Hover);
		const FVector Born = Hub + FreshAround(Seat + OrbitSpin * Appear) * OrbitRingRadius;
		DFreshLater(Appear, [this, Born]() { DFreshGlint(Born, ShatterGlint * 0.8f); });
		const FVector Head = Hub + FreshAround(PeelSeat) * OrbitRingRadius;
		const FVector Axis = (Landing - Head).GetSafeNormal();
		DFreshDive(Now + Peel, Head, Landing + Axis * OrbitEmbed, Axis, OrbitFall, LastHit - Peel - OrbitFall + 0.25f,
			FVector2D(OrbitWidth, OrbitLength), DiveTrailLength);
		const bool bLast = Index == OrbitCount - 1;
		DFreshLater(Peel + OrbitFall, [this, Landing, bLast, Center, Toward, WeakFrost]()
		{
			DFreshImpact(Landing, bLast ? 1.8f : 0.8f);
			DFreshStrike(Landing, bLast ? OrbitHitRadius * 1.6f : OrbitHitRadius, OrbitDamage);
			DFreshShatter(Landing, bLast ? 8 : 4, bLast ? 150.0f : 80.0f, bLast ? 1.0f : 0.7f);
			if (bLast)
			{
				DFreshPillar(Landing, WardPillarWidth, WardPillarHeight);
				DFreshMotes(Center, 14, FreshRadius * 0.8f);
				ScaleFreshFrost(SweepFloorDecal(WeakFrost.Get(), Center, Toward, FreshRadius, 1.0f, 0.25f, -1.0f, 0.5f), FreshRadius);
			}
		});
		Planted.Add(Landing - Axis * (OrbitLength * 0.5f - OrbitEmbed));
	}
	DFreshLater(LastHit + 0.19f, [this, Planted]()
	{
		for (const FVector& Middle : Planted)
		{
			DFreshGlint(Middle, ShatterGlint * 0.7f);
			DFreshShatter(Middle, 3, 60.0f, 0.6f);
		}
	});
	return LastHit + 0.6f;
}

float UAuroraSkillComponent::DFreshBigShard(const FVector& Center, const FVector& Toward)
{
	const double Now = GetWorld()->GetTimeSeconds();
	UTexture* Shard = LoadFreshTexture(TEXT("T_Aurora_FxShard"));
	const TWeakObjectPtr<UMaterialInterface> WeakFrost = LoadFreshMaterial(TEXT("M_Aurora_FrostBurst"));
	const FVector Head = Center - IcicleFall * BigHover;
	const float FireAt = BigGrow + BigHold;
	const float HitAt = FireAt + BigFall;
	const float BreakAt = HitAt + BigStuck;
	// 하늘에 끝부터 자라나며 둘레 빛 알갱이를 빨아들인다
	FAuroraDPiece Hover;
	Hover.Born = Now;
	Hover.Life = FireAt;
	Hover.Face = 2;
	Hover.Axis = IcicleFall;
	Hover.From = Hover.To = Head;
	Hover.SizeFrom = FVector2D(BigWidth, 0.0f);
	Hover.SizeTo = FVector2D(BigWidth, BigLength);
	Hover.GrowSeconds = BigGrow;
	Hover.FadeIn = 0.08f;
	Hover.FadeOut = 0.0f;
	Hover.Bob = 4.0f;
	Hover.BobRate = 2.0f;
	Hover.Lift = 20.0f;
	Hover.Glow = ShardGlow;
	Hover.CoreGlow = ShardCoreGlow;
	AddDPiece(Shard, Hover);
	const FVector Belly = Head - IcicleFall * (BigLength * 0.5f);
	TArray<FVector> Far;
	for (int32 Index = 0; Index < 12; ++Index)
	{
		Far.Add(Belly + FRotator(FMath::FRandRange(-50.0f, 50.0f), 30.0f * Index, 0.0f).Vector() * FMath::FRandRange(200.0f, 280.0f));
	}
	DFreshConverge(Far, Belly, BigGrow);
	DFreshGlint(Head, ShatterGlint * 1.4f);
	DFreshLater(FireAt, [this, Head]() { DFreshGlint(Head, ShatterGlint * 1.2f); });
	DFreshDive(Now + FireAt, Head, Center + IcicleFall * BigEmbed, IcicleFall, BigFall, BigStuck, FVector2D(BigWidth, BigLength),
		DiveTrailLength * 2.0f);
	DFreshLater(HitAt, [this, Center, Toward, WeakFrost]()
	{
		DFreshImpact(Center, 2.0f);
		DFreshStrike(Center, BigHitRadius, BigDamage);
		DFreshPillar(Center, WardPillarWidth, WardPillarHeight);
		ScaleFreshFrost(SweepFloorDecal(WeakFrost.Get(), Center, Toward, BigFrostRadius, 1.4f, 0.2f, -1.0f, 0.5f), BigFrostRadius);
	});
	// 부서진 조각들이 둘레로 쏟아져 꽂힌다
	const FVector Broken = Center - IcicleFall * (BigLength * 0.5f - BigEmbed);
	DFreshLater(BreakAt - 0.02f, [this, Broken]()
	{
		DFreshGlint(Broken, ShatterGlint * 1.6f);
		DFreshMotes(Broken - FVector(0.0f, 0.0f, 100.0f), 10, 120.0f);
	});
	const float FrontAngle = FMath::Atan2(Toward.Y, Toward.X);
	for (int32 Index = 0; Index < BigShardCount; ++Index)
	{
		const float Angle = FrontAngle + 2.0f * PI * (Index + FMath::FRandRange(-0.25f, 0.25f)) / BigShardCount;
		const FVector Landing = Center + FreshAround(Angle) * FMath::FRandRange(BigShardInner, BigShardOuter);
		const FVector Axis = (Landing - Broken).GetSafeNormal();
		const float Delay = FMath::FRandRange(0.0f, 0.06f);
		DFreshDive(Now + BreakAt + Delay, Broken, Landing + Axis * 15.0f, Axis, BigShardFlight, 0.3f, FVector2D(BigShardWidth, BigShardLength),
			DiveTrailLength * 0.5f);
		DFreshLater(BreakAt + Delay + BigShardFlight, [this, Landing]()
		{
			DFreshImpact(Landing, 0.45f);
			DFreshStrike(Landing, BigShardHitRadius, BigShardDamage);
		});
	}
	return BreakAt + 0.06f + BigShardFlight + 0.5f;
}

void UAuroraSkillComponent::DFreshLater(float Delay, TFunction<void()> Do)
{
	if (UWorld* World = GetWorld())
	{
		World->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, MoveTemp(Do)), FMath::Max(Delay, 0.01f),
			false);
	}
}

void UAuroraSkillComponent::DFreshImpact(const FVector& Where, float Scale, bool bLight)
{
	if (!GetWorld())
	{
		return;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	FAuroraDPiece Flash;
	Flash.Born = Now;
	Flash.Life = ImpactStarLife;
	Flash.Face = 1;
	Flash.From = Flash.To = Where + FVector(0.0f, 0.0f, 25.0f);
	Flash.SizeFrom = FVector2D(ImpactStarFrom * Scale);
	Flash.SizeTo = FVector2D(ImpactStarTo * Scale);
	Flash.GrowSeconds = ImpactStarGrow;
	Flash.FadeOut = ImpactStarFade;
	Flash.Spin = FMath::FRandRange(0.0f, 90.0f);
	Flash.Lift = ImpactStarLift * Scale;
	AddDPiece(LoadFreshTexture(TEXT("T_Aurora_FxStar")), Flash);
	FAuroraDPiece Ripple;
	Ripple.Born = Now;
	Ripple.Life = ImpactRippleLife;
	Ripple.From = Ripple.To = Where + FVector(0.0f, 0.0f, 3.0f);
	Ripple.SizeFrom = FVector2D(2.0f * ImpactRippleFrom * Scale / FreshRingCore);
	Ripple.SizeTo = FVector2D(2.0f * ImpactRippleTo * Scale / FreshRingCore);
	Ripple.GrowSeconds = ImpactRippleGrow;
	Ripple.FadeOut = ImpactRippleFade;
	Ripple.Strength = ImpactRippleStrength;
	Ripple.Spin = FMath::FRandRange(0.0f, 360.0f);
	AddDPiece(LoadFreshTexture(TEXT("T_Aurora_FxRing")), Ripple);
	if (bLight)
	{
		AddDLight(Where, ImpactLight * Scale, ImpactLightRadius * Scale, ImpactLightSeconds);
	}
}

void UAuroraSkillComponent::DFreshStrike(const FVector& Where, float Radius, float Damage)
{
	TArray<AActor*> Targets;
	GatherTargets(Where, Radius, Targets);
	AController* Instigator = Character.IsValid() ? Character->GetController() : nullptr;
	for (AActor* Target : Targets)
	{
		// 처음 맞힌 한 번만 짧게 멈칫(맞을 때마다 멈추면 내내 끊긴다)
		if (IcicleHits.IsEmpty())
		{
			BeginHitStop(Target, FreshHitStopSeconds);
		}
		IcicleHits.Add(Target);
		if (Target->CanBeDamaged())
		{
			FHitResult Hit(Target, nullptr, Target->GetActorLocation(), FVector::DownVector);
			UGameplayStatics::ApplyPointDamage(Target, Damage, FVector::DownVector, Hit, Instigator, GetOwner(), nullptr);
		}
		SetFreshStatus(Target, TEXT("SLOW"), FreshSlowSeconds);
	}
}

void UAuroraSkillComponent::DFreshGlint(const FVector& Where, float Size)
{
	if (!GetWorld())
	{
		return;
	}
	FAuroraDPiece Spark;
	Spark.Born = GetWorld()->GetTimeSeconds();
	Spark.Life = 0.18f;
	Spark.Face = 1;
	Spark.From = Spark.To = Where;
	Spark.SizeFrom = FVector2D(Size * 0.4f);
	Spark.SizeTo = FVector2D(Size);
	Spark.GrowSeconds = 0.1f;
	Spark.FadeOut = 0.12f;
	Spark.Strength = 0.7f;
	Spark.Spin = FMath::FRandRange(0.0f, 90.0f);
	Spark.Lift = 40.0f;
	AddDPiece(LoadFreshTexture(TEXT("T_Aurora_FxStar")), Spark);
}

void UAuroraSkillComponent::DFreshDive(double Born, const FVector& Head, const FVector& Ground, const FVector& Axis, float Fall, float Stuck,
	FVector2D Size, float TrailLength, float StuckFade, UTexture* Picture, float TrailScale)
{
	// 떨어지는 결정(Axis 쪽으로 머리 = 끝) + 뒤 빛줄기
	FAuroraDPiece Body;
	Body.Born = Born;
	Body.Life = Fall + Stuck;
	Body.Face = 2;
	Body.Axis = Axis;
	Body.From = Head;
	Body.To = Ground;
	Body.MoveSeconds = Fall;
	Body.MoveEase = 1;
	Body.SizeFrom = Body.SizeTo = Size;
	Body.FadeIn = 0.03f;
	Body.FadeOut = StuckFade;
	Body.Lift = 10.0f;
	Body.Glow = ShardGlow;
	Body.CoreGlow = ShardCoreGlow;
	AddDPiece(Picture ? Picture : LoadFreshTexture(TEXT("T_Aurora_FxShard")), Body);
	// 빛줄기 굵기는 결정 굵기에 맞춘다(76차 결정 30cm 안팎에 20cm)
	FAuroraDPiece Tail = Body;
	Tail.Life = Fall + DiveTrailFade;
	Tail.SizeFrom = Tail.SizeTo = FVector2D(DiveTrailWidth * Size.X / 30.0f * TrailScale, TrailLength);
	Tail.FadeOut = DiveTrailFade;
	Tail.Strength = 0.8f;
	Tail.Glow = Tail.CoreGlow = -1.0f;
	AddDPiece(LoadFreshTexture(TEXT("T_Aurora_FxStreak")), Tail);
}

void UAuroraSkillComponent::DFreshShatter(const FVector& Where, int32 Count, float Reach, float Scale)
{
	if (!GetWorld())
	{
		return;
	}
	// 빛 결정 조각이 사방(조금 위)으로 튀어 느려지며 흐려진다 — 조각 머리가 나는 쪽
	UTexture* Shard = LoadFreshTexture(TEXT("T_Aurora_FxShard"));
	const double Now = GetWorld()->GetTimeSeconds();
	for (int32 Index = 0; Index < Count; ++Index)
	{
		const float Yaw = 2.0f * PI * (Index + FMath::FRandRange(-0.3f, 0.3f)) / Count;
		const float Rise = FMath::DegreesToRadians(FMath::FRandRange(15.0f, 50.0f));
		const FVector Out = FreshAround(Yaw) * FMath::Cos(Rise) + FVector::UpVector * FMath::Sin(Rise);
		FAuroraDPiece Bit;
		Bit.Born = Now;
		Bit.Life = 0.38f;
		Bit.Face = 2;
		Bit.Axis = Out;
		Bit.From = Where;
		Bit.To = Where + Out * Reach * FMath::FRandRange(0.6f, 1.0f);
		Bit.MoveSeconds = 0.35f;
		Bit.MoveEase = 2;
		const float Size = Scale * FMath::FRandRange(0.7f, 1.3f);
		Bit.SizeFrom = Bit.SizeTo = FVector2D(9.0f * Size, 30.0f * Size);
		Bit.FadeOut = 0.18f;
		Bit.Lift = 10.0f;
		Bit.Glow = ShardGlow;
		Bit.CoreGlow = 1.5f;
		AddDPiece(Shard, Bit);
	}
}

void UAuroraSkillComponent::DFreshMotes(const FVector& Where, int32 Count, float Radius)
{
	if (!GetWorld())
	{
		return;
	}
	// 작은 별빛이 천천히 피어올라 반짝이며 사라진다(얼음 가루)
	UTexture* Star = LoadFreshTexture(TEXT("T_Aurora_FxStar"));
	const double Now = GetWorld()->GetTimeSeconds();
	for (int32 Index = 0; Index < Count; ++Index)
	{
		const FVector Offset = FreshAround(FMath::FRandRange(0.0f, 2.0f * PI)) * Radius * FMath::Sqrt(FMath::FRand());
		FAuroraDPiece Mote;
		Mote.Born = Now + FMath::FRandRange(0.0f, 0.15f);
		Mote.Life = FMath::FRandRange(0.55f, 0.8f);
		Mote.Face = 1;
		Mote.From = Where + Offset + FVector(0.0f, 0.0f, FMath::FRandRange(10.0f, 40.0f));
		Mote.To = Mote.From + FVector(0.0f, 0.0f, FMath::FRandRange(50.0f, 110.0f));
		Mote.MoveSeconds = Mote.Life;
		Mote.MoveEase = 2;
		Mote.SizeFrom = Mote.SizeTo = FVector2D(FMath::FRandRange(12.0f, 22.0f));
		Mote.FadeIn = 0.08f;
		Mote.FadeOut = 0.4f;
		Mote.Strength = 0.7f;
		Mote.Spin = FMath::FRandRange(0.0f, 90.0f);
		Mote.SpinRate = FMath::FRandRange(-180.0f, 180.0f);
		Mote.Lift = 20.0f;
		AddDPiece(Star, Mote);
	}
}

void UAuroraSkillComponent::DFreshPillar(const FVector& Where, float Width, float Height)
{
	if (!GetWorld())
	{
		return;
	}
	// 빛줄기 그림을 머리가 바닥에 닿게 세워(꼬리가 위) 빠르게 솟았다가 흐린다
	FAuroraDPiece Pillar;
	Pillar.Born = GetWorld()->GetTimeSeconds();
	Pillar.Life = 0.4f;
	Pillar.Face = 2;
	Pillar.Axis = -FVector::UpVector;
	Pillar.From = Pillar.To = Where;
	Pillar.SizeFrom = FVector2D(Width, 0.0f);
	Pillar.SizeTo = FVector2D(Width, Height);
	Pillar.GrowSeconds = 0.1f;
	Pillar.FadeOut = 0.3f;
	Pillar.Lift = 30.0f;
	Pillar.Glow = 2.0f;
	Pillar.CoreGlow = 4.0f;
	AddDPiece(LoadFreshTexture(TEXT("T_Aurora_FxStreak")), Pillar);
}

void UAuroraSkillComponent::DFreshConverge(const TArray<FVector>& From, const FVector& To, float Seconds)
{
	if (!GetWorld())
	{
		return;
	}
	UTexture* Star = LoadFreshTexture(TEXT("T_Aurora_FxStar"));
	const double Now = GetWorld()->GetTimeSeconds();
	for (const FVector& Start : From)
	{
		FAuroraDPiece Mote;
		Mote.Born = Now;
		Mote.Life = Seconds;
		Mote.Face = 1;
		Mote.From = Start;
		Mote.To = To;
		Mote.MoveSeconds = Seconds;
		Mote.MoveEase = 1;
		Mote.SizeFrom = FVector2D(34.0f);
		Mote.SizeTo = FVector2D(18.0f);
		Mote.GrowSeconds = Seconds;
		Mote.FadeIn = 0.05f;
		Mote.FadeOut = 0.03f;
		Mote.Strength = 0.85f;
		Mote.Spin = FMath::FRandRange(0.0f, 90.0f);
		Mote.Lift = 30.0f;
		AddDPiece(Star, Mote);
	}
}

void UAuroraSkillComponent::AddDPiece(UTexture* Shape, FAuroraDPiece Piece, UMaterialInterface* Base)
{
	if (!Base)
	{
		Base = LoadFreshMaterial(TEXT("M_Aurora_FxAdd"));
	}
	if (!PlaneMesh || !Base || !Shape || !GetWorld())
	{
		return;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	UStaticMeshComponent* Mesh = SpawnTimedMesh(PlaneMesh, FTransform(FQuat::Identity, Piece.From, FVector(0.001f)),
		static_cast<float>(FMath::Max(Piece.Born - Now, 0.0)) + Piece.Life + 0.1f);
	if (!Mesh)
	{
		return;
	}
	UMaterialInstanceDynamic* Dynamic = UMaterialInstanceDynamic::Create(Base, Mesh);
	Dynamic->SetTextureParameterValue(TEXT("Shape"), Shape);
	Dynamic->SetScalarParameterValue(TEXT("Fade"), 0.0f);
	if (Piece.Glow >= 0.0f)
	{
		Dynamic->SetScalarParameterValue(TEXT("Brightness"), Piece.Glow);
	}
	if (Piece.CoreGlow >= 0.0f)
	{
		Dynamic->SetScalarParameterValue(TEXT("CoreBrightness"), Piece.CoreGlow);
	}
	if (Piece.Tint.A > 0.0f)
	{
		Dynamic->SetVectorParameterValue(TEXT("Colour"), Piece.Tint);
	}
	for (const TPair<FName, float>& Scalar : Piece.Scalars)
	{
		Dynamic->SetScalarParameterValue(Scalar.Key, Scalar.Value);
	}
	Mesh->SetMaterial(0, Dynamic);
	Mesh->SetCastShadow(false);
	Mesh->SetReceivesDecals(false);
	Mesh->SetTranslucentSortPriority(Piece.SortPriority);
	Mesh->SetVisibility(Piece.Born <= Now);
	Piece.Mesh = Mesh;
	Piece.Material = Dynamic;
	DPieces.Add(Piece);
	if (!GetWorld()->GetTimerManager().IsTimerActive(DPieceTimer))
	{
		GetWorld()->GetTimerManager().SetTimer(DPieceTimer, this, &UAuroraSkillComponent::DPieceTick, 1.0f / 60.0f, true);
	}
}

void UAuroraSkillComponent::AddDLight(const FVector& Where, float Peak, float Radius, float Seconds)
{
	if (!Character.IsValid() || !GetWorld())
	{
		return;
	}
	UPointLightComponent* Light = NewObject<UPointLightComponent>(Character.Get());
	Light->SetMobility(EComponentMobility::Movable);
	Light->RegisterComponent();
	Light->SetWorldLocation(Where + FVector(0.0f, 0.0f, 100.0f));
	Light->SetIntensityUnits(ELightUnits::Candelas);
	Light->SetIntensity(Peak);
	Light->SetLightColor(HasteLightColour);
	Light->SetAttenuationRadius(Radius);
	Light->SetCastShadows(false);
	DLights.Add({Light, GetWorld()->GetTimeSeconds(), Seconds, Peak});
	if (!GetWorld()->GetTimerManager().IsTimerActive(DPieceTimer))
	{
		GetWorld()->GetTimerManager().SetTimer(DPieceTimer, this, &UAuroraSkillComponent::DPieceTick, 1.0f / 60.0f, true);
	}
}

void UAuroraSkillComponent::DPieceTick()
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	const double Now = World->GetTimeSeconds();
	// 판 앞면이 게임 카메라를 보게(위에서 비스듬히 내려다보므로 세운 판은 카메라 쪽으로 돌려야 얇아지지 않는다)
	FVector ToCamera = FVector::UpVector;
	FVector CameraAt = FVector::ZeroVector;
	FVector CameraUp = FVector::UpVector;
	if (const APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(World, 0))
	{
		ToCamera = -Camera->GetCameraRotation().Vector();
		CameraAt = Camera->GetCameraLocation();
		CameraUp = FRotationMatrix(Camera->GetCameraRotation()).GetScaledAxis(EAxis::Z);
	}
	const FQuat FaceCamera = FRotationMatrix::MakeFromZ(ToCamera).ToQuat();
	for (int32 Index = DPieces.Num() - 1; Index >= 0; --Index)
	{
		const FAuroraDPiece& Piece = DPieces[Index];
		UStaticMeshComponent* Mesh = Piece.Mesh.Get();
		UMaterialInstanceDynamic* Dynamic = Piece.Material.Get();
		const float Age = static_cast<float>(Now - Piece.Born);
		if (!IsValid(Mesh) || !Dynamic || Age >= Piece.Life)
		{
			RemoveTimedMesh(Mesh, nullptr);
			DPieces.RemoveAtSwap(Index);
			continue;
		}
		if (Age < 0.0f)
		{
			continue;
		}
		Mesh->SetVisibility(true);
		FVector At = Piece.OrbitRadius > 0.0f
			? Piece.OrbitCenter + FreshAround(Piece.OrbitAngle + Piece.OrbitRate * Age) * Piece.OrbitRadius
			: FMath::Lerp(Piece.From, Piece.To, Piece.MoveSeconds > 0.0f ? FreshEase(Age / Piece.MoveSeconds, Piece.MoveEase) : 1.0f);
		if (Piece.Bob > 0.0f)
		{
			At.Z += Piece.Bob * FMath::Sin(2.0f * PI * Piece.BobRate * Age + Piece.BobPhase);
		}
		const float Grow = Piece.GrowSeconds > 0.0f ? FreshEase((Age - Piece.GrowDelay) / Piece.GrowSeconds, Piece.GrowEase)
			: (Age >= Piece.GrowDelay ? 1.0f : 0.0f);
		const FVector2D Size = FMath::Lerp(Piece.SizeFrom, Piece.SizeTo, Grow);
		FQuat Rotation = FQuat::Identity;
		FVector Center = At;
		const float Spin = FMath::DegreesToRadians(Piece.Spin + Piece.SpinRate * Age);
		switch (Piece.Face)
		{
		case 0:
			Rotation = FQuat(FVector::UpVector, Spin);
			break;
		case 1:
			Rotation = FQuat(ToCamera, Spin) * FaceCamera;
			Center += ToCamera * Piece.Lift;
			break;
		case 3:
			// 화면에 붙은 판: 카메라 앞 Lift만큼, 판 Y = 화면 위 — 그림 가로(U)가 화면 오른쪽, 세로(V)가 화면 아래로 온다(판 Y = 화면 오른쪽인 첫 판은
			// 그림이 90° 돌아 눈이 왼쪽으로 흘렀다)
			Rotation = FRotationMatrix::MakeFromZY(ToCamera, CameraUp).ToQuat();
			Center = CameraAt - ToCamera * Piece.Lift;
			break;
		default:
		{
			// 그림 위쪽(판 -Y)이 머리 = Axis 쪽, 앞면은 카메라 쪽으로 — 머리 자리에서 꼬리 쪽으로 길이 절반만큼 물러난 곳이 판 가운데.
			// bAim이면 머리가 늘 AimPoint를 본다(돌면서 한 점을 겨누는 결정)
			FVector Axis = Piece.Axis;
			if (Piece.bAim && !(Piece.AimPoint - At).IsNearlyZero())
			{
				Axis = (Piece.AimPoint - At).GetSafeNormal();
			}
			Rotation = FRotationMatrix::MakeFromYZ(-Axis, ToCamera).ToQuat();
			Center = At - Axis * (Size.Y * 0.5f) + ToCamera * Piece.Lift;
			break;
		}
		}
		Mesh->SetWorldLocationAndRotation(Center, Rotation);
		Mesh->SetWorldScale3D(FVector(FMath::Max(Size.X / 100.0f, 0.001f), FMath::Max(Size.Y / 100.0f, 0.001f), 1.0f));
		const float In = Piece.FadeIn > 0.0f ? FMath::Clamp(Age / Piece.FadeIn, 0.0f, 1.0f) : 1.0f;
		const float Out = Piece.FadeOut > 0.0f ? FMath::Clamp((Piece.Life - Age) / Piece.FadeOut, 0.0f, 1.0f) : 1.0f;
		Dynamic->SetScalarParameterValue(TEXT("Fade"), Piece.Strength * In * Out);
	}
	for (int32 Index = DLights.Num() - 1; Index >= 0; --Index)
	{
		const FAuroraDLight& Flash = DLights[Index];
		UPointLightComponent* Light = Flash.Light.Get();
		const float Left = 1.0f - static_cast<float>(Now - Flash.Born) / Flash.Life;
		if (!IsValid(Light) || Left <= 0.0f)
		{
			if (IsValid(Light))
			{
				Light->DestroyComponent();
			}
			DLights.RemoveAtSwap(Index);
			continue;
		}
		Light->SetIntensity(Flash.Peak * Left * Left);
	}
	if (DPieces.IsEmpty() && DLights.IsEmpty())
	{
		World->GetTimerManager().ClearTimer(DPieceTimer);
	}
}

void UAuroraSkillComponent::HasteRimIce(const FVector& Center, const FVector& Forward)
{
	if (CVarAuroraHasteIce.GetValueOnGameThread() == 0 || !GetWorld() || !LoadFreshTexture(TEXT("T_Aurora_FxShard")) ||
		!LoadFreshMaterial(TEXT("M_Aurora_FxAdd")))
	{
		return;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	const FVector Up = FVector::UpVector;
	const float Slant = FMath::DegreesToRadians(HasteIceSlantDegrees);
	const float FrontAngle = FMath::Atan2(Forward.Y, Forward.X);
	for (int32 Index = 0; Index < HasteIceCount; ++Index)
	{
		// 앞에서부터 시계 방향으로 차례로(D 결계와 같은 차례) 바깥 위에서 안쪽으로 비스듬히 꽂혀, 장판이 사라질 때 같이 흐려진다
		const FVector Landing = Center + FreshAround(FrontAngle + 2.0f * PI * Index / HasteIceCount) * HasteRadius * HasteIceReach;
		const FVector Inward = (Center - Landing).GetSafeNormal2D();
		const FVector Fall = (Inward * FMath::Sin(Slant) - Up * FMath::Cos(Slant)).GetSafeNormal();
		const float At = HasteIceStart + HasteIceInterval * Index;
		DFreshDive(Now + At, Landing - Fall * HasteIceDrop, Landing + Fall * HasteIceEmbed, Fall, HasteIceFall,
			FMath::Max(HasteSeconds - At - HasteIceFall, 0.1f), FVector2D(HasteIceWidth, HasteIceLength), DiveTrailLength, HasteFloorFadeOut);
		DFreshLater(At + HasteIceFall, [this, Landing]()
		{
			DFreshImpact(Landing, HasteIceImpact);
			DFreshShatter(Landing, HasteIceChips, 60.0f, 0.6f);
		});
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_HASTE ice=%d reach=%.0f"), HasteIceCount, HasteRadius * HasteIceReach);
}

void UAuroraSkillComponent::ExecuteBlizzard()
{
	if (!GetWorld() || !Character.IsValid())
	{
		return;
	}
	const int32 Storm = CVarAuroraStorm.GetValueOnGameThread();
	if (Storm == 0)
	{
		ExecuteIceSpikes();
		return;
	}
	UTexture* Seal = LoadFreshTexture(TEXT("T_Aurora_BlizzardSeal"));
	UTexture* Ring = LoadFreshTexture(TEXT("T_Aurora_FxRing"));
	if (!Seal || !Ring || !LoadFreshTexture(TEXT("T_Aurora_FxShard")) || !LoadFreshMaterial(TEXT("M_Aurora_FxAdd")))
	{
		UE_LOG(LogTemp, Warning, TEXT("AURORA_BLIZZARD missing light pictures"));
		return;
	}
	// 겨눈 자리(시전 거리까지 당김) 바닥 — 고드름 비와 같은 방식
	const FVector Feet = GetFeetLocation();
	FVector Offset = (ActiveAim - Feet) * FVector(1.0f, 1.0f, 0.0f);
	const float Reach = Skills[EAuroraSkill::Blizzard].Range;
	if (Offset.Size() > Reach)
	{
		Offset = Offset.GetSafeNormal() * Reach;
	}
	FVector Toward = Offset.GetSafeNormal();
	if (Toward.IsNearlyZero())
	{
		Toward = Character->GetActorForwardVector().GetSafeNormal2D();
	}
	const FVector Above(Feet.X + Offset.X, Feet.Y + Offset.Y, Character->GetActorLocation().Z);
	const FVector Center(Above.X, Above.Y, FindFloorZ(Above, Feet.Z));
	IcicleHits.Reset();
	BlizzardLanded = 0;
	BlizzardAimed = 0;
	BlizzardBig = 0;
	const double Now = GetWorld()->GetTimeSeconds();
	const float Ends = BlizzardStart + BlizzardSeconds;
	const float Total = Ends + BlizzardFinaleFall + BlizzardLinger;
	// 94차 VLook 2·3은 그린 마법진·충격파 대신 팩 효과(BlizzardPack), 1은 그 전 그림
	const int32 Look = CVarAuroraVLook.GetValueOnGameThread();
	if (Look >= 2)
	{
		BlizzardPack(Center, Look, Total);
	}
	else
	{
		// 마법진: 가운데에서 펼쳐지며 천천히 돌고, 펼쳐지는 순간 같은 그림을 밝게 한 장 더(번쩍)
		FAuroraDPiece Circle;
		Circle.Born = Now;
		Circle.Life = Total;
		Circle.From = Circle.To = Center + FVector(0.0f, 0.0f, 4.0f);
		Circle.SizeTo = FVector2D(2.0f * BlizzardRadius / BlizzardSealCore);
		Circle.SizeFrom = Circle.SizeTo * 0.7f;
		Circle.GrowSeconds = BlizzardSealOpen;
		Circle.FadeIn = 0.15f;
		Circle.FadeOut = 0.6f;
		Circle.Strength = BlizzardSealStrength;
		Circle.Glow = BlizzardSealGlow;
		Circle.CoreGlow = BlizzardSealCoreGlow;
		Circle.SpinRate = BlizzardSealSpin;
		AddDPiece(Seal, Circle);
		FAuroraDPiece Flash = Circle;
		Flash.Life = BlizzardSealOpen + 0.35f;
		Flash.FadeIn = 0.05f;
		Flash.FadeOut = 0.35f;
		Flash.Strength = 1.0f;
		Flash.Glow = 4.0f;
		Flash.CoreGlow = 6.0f;
		AddDPiece(Seal, Flash);
		// 테두리에 출렁이는 고리(마법진과 반대로 돎) + 펼쳐질 때 가운데에서 바깥 고리까지 퍼지는 충격파 + 가운데 번쩍임
		FAuroraDPiece Rim;
		Rim.Born = Now;
		Rim.Life = Total;
		Rim.From = Rim.To = Center + FVector(0.0f, 0.0f, 5.0f);
		Rim.SizeFrom = Rim.SizeTo = FVector2D(2.0f * BlizzardRadius / FreshRingCore);
		Rim.FadeIn = 0.25f;
		Rim.FadeOut = 0.6f;
		Rim.Strength = BlizzardRimStrength;
		Rim.SpinRate = BlizzardRimSpin;
		AddDPiece(Ring, Rim);
		FAuroraDPiece Wave;
		Wave.Born = Now;
		Wave.Life = BlizzardOpenWave + 0.12f;
		Wave.From = Wave.To = Center + FVector(0.0f, 0.0f, 6.0f);
		Wave.SizeFrom = FVector2D(2.0f * 40.0f / FreshRingCore);
		Wave.SizeTo = FVector2D(2.0f * BlizzardRadius / FreshRingCore);
		Wave.GrowSeconds = BlizzardOpenWave;
		Wave.FadeOut = 0.15f;
		Wave.Strength = 0.9f;
		AddDPiece(Ring, Wave);
		DFreshImpact(Center, BlizzardOpenFlash);
	}
	for (int32 Spike = 0; Spike < BlizzardSpikeCount; ++Spike)
	{
		// 고르게 쏟아지되 사이를 조금씩 흩뜨린다
		const float At = BlizzardStart + BlizzardSeconds * (Spike + FMath::FRandRange(0.0f, 0.8f)) / BlizzardSpikeCount;
		DFreshLater(At, [this, Center, Toward, Spike]() { BlizzardSpike(Center, Toward, Spike); });
	}
	DFreshLater(Ends, [this, Center, Toward]() { BlizzardFinale(Center, Toward); });
	// 94차 팩 효과 시안(VLook 2·3)은 화면을 어둡게 하지 않는다 — 어두운 막이 팩 터짐을 묻었다(첫 촬영)
	BlizzardStorm(Total, Storm == 1 && Look < 2);
	DFreshLater(Total, [this]()
	{
		UE_LOG(LogTemp, Display, TEXT("AURORA_BLIZZARD end landed=%d aimed=%d big=%d hits=%d"), BlizzardLanded, BlizzardAimed, BlizzardBig,
			IcicleHits.Num());
	});
	UE_LOG(LogTemp, Display, TEXT("AURORA_BLIZZARD start storm=%d at=%s radius=%.0f spikes=%d"), Storm, *Center.ToCompactString(),
		BlizzardRadius, BlizzardSpikeCount);
}

void UAuroraSkillComponent::BlizzardSpike(const FVector& Center, const FVector& Toward, int32 Spike)
{
	if (!GetWorld())
	{
		return;
	}
	// 자리: 원 안 해바라기 배치를 건너뛰며 고르고(한쪽으로 몰리지 않게) 조금 흩뜨린다. BlizzardAimEvery번째마다 원 안 적 하나의 발밑으로.
	FVector Landing = FreshSeat(Center, Spike, BlizzardSpikeCount, BlizzardStride, BlizzardRadius) +
		FreshAround(FMath::FRandRange(0.0f, 2.0f * PI)) * FMath::FRandRange(0.0f, 30.0f);
	if (Spike % BlizzardAimEvery == 0)
	{
		TArray<AActor*> Targets;
		GatherTargets(Center, BlizzardRadius, Targets);
		if (!Targets.IsEmpty())
		{
			const FVector Foot = Targets[FMath::RandHelper(Targets.Num())]->GetActorLocation();
			Landing = FVector(Foot.X, Foot.Y, Center.Z) +
				FreshAround(FMath::FRandRange(0.0f, 2.0f * PI)) * FMath::FRandRange(0.0f, BlizzardAimScatter);
			++BlizzardAimed;
		}
	}
	// 원 밖으로 나가지 않게
	const FVector Offset = (Landing - Center) * FVector(1.0f, 1.0f, 0.0f);
	if (Offset.Size() > BlizzardRadius)
	{
		Landing = Center + Offset.GetSafeNormal() * BlizzardRadius * 0.95f;
	}
	Landing.Z = Center.Z;
	// 바람: 모두 오로라 쪽 하늘에서 겨눈 쪽으로 비스듬히, 방향·기울기만 조금씩 다르게
	const FVector Wind = Toward.RotateAngleAxis(FMath::FRandRange(-BlizzardYawScatter, BlizzardYawScatter), FVector::UpVector);
	const float Slant = FMath::DegreesToRadians(BlizzardSlantDegrees + FMath::FRandRange(-BlizzardSlantScatter, BlizzardSlantScatter));
	const FVector Fall = (Wind * FMath::Sin(Slant) - FVector::UpVector * FMath::Cos(Slant)).GetSafeNormal();
	const bool bBig = Spike % BlizzardBigEvery == BlizzardBigEvery / 2;
	const float Grade = FMath::FRand();
	const FVector2D Size = bBig ? FVector2D(BlizzardBigWidth, BlizzardBigLength)
		: FVector2D(FMath::Lerp(BlizzardWidthMin, BlizzardWidthMax, Grade), FMath::Lerp(BlizzardLengthMin, BlizzardLengthMax, Grade));
	const float Drop = bBig ? BlizzardBigDrop : BlizzardDrop;
	const float Fly = bBig ? BlizzardBigFall : BlizzardFall;
	if (CVarAuroraVLook.GetValueOnGameThread() >= 2)
	{
		// 94차 팩 효과 시안: 빛 조각은 그리지 않고 같은 때·자리에 맞는 것만(그림은 BlizzardPack)
		DFreshLater(Fly, [this, Landing, bBig]()
		{
			++BlizzardLanded;
			BlizzardBig += bBig ? 1 : 0;
			DFreshStrike(Landing, bBig ? BlizzardBigHitRadius : BlizzardHitRadius, Skills[EAuroraSkill::Blizzard].Damage);
		});
		return;
	}
	DFreshDive(GetWorld()->GetTimeSeconds(), Landing - Fall * Drop, Landing + Fall * BlizzardEmbed, Fall, Fly, BlizzardStuck, Size,
		bBig ? DiveTrailLength * 1.6f : DiveTrailLength, 0.12f, LoadFreshTexture(TEXT("T_Aurora_FxSpike")), BlizzardTrailScale);
	const bool bChip = Spike % BlizzardChipEvery == 0;
	if (!bBig && Spike % BlizzardSnapEvery == 1)
	{
		// 박혀 있다 사라질 때 부러져 조각 둘이 튄다(그냥 흐려지기만 하면 녹아 없어지는 것처럼 보인다)
		const FVector Snap = Landing - Fall * Size.Y * 0.4f;
		DFreshLater(Fly + BlizzardStuck - 0.08f, [this, Snap]() { DFreshShatter(Snap, 2, 45.0f, 0.45f); });
	}
	DFreshLater(Fly, [this, Landing, Grade, bChip, bBig]()
	{
		++BlizzardLanded;
		const float Damage = Skills[EAuroraSkill::Blizzard].Damage;
		if (!bBig)
		{
			// 작은 결정은 빛 없이(초당 60개가 빛을 켜면 바닥이 뿌옇게 덮인다)
			BlizzardSplash(Landing, BlizzardSplashSize * FMath::Lerp(0.85f, 1.15f, Grade), BlizzardStar, false);
			DFreshStrike(Landing, BlizzardHitRadius, Damage);
			if (bChip)
			{
				DFreshShatter(Landing, 3, 55.0f, 0.5f);
			}
			return;
		}
		++BlizzardBig;
		BlizzardSplash(Landing, BlizzardBigSplashSize, BlizzardBigImpact, true);
		DFreshStrike(Landing, BlizzardBigHitRadius, Damage);
		DFreshShatter(Landing, BlizzardBigChips, BlizzardBigChipReach, 0.9f);
	});
}

void UAuroraSkillComponent::BlizzardSplash(const FVector& Where, float Size, float StarScale, bool bLight)
{
	if (!GetWorld())
	{
		return;
	}
	// 바닥에 눕힌 얼음 튐이 빠르게 벌어졌다 흐려지고(방향은 아무렇게나) 가운데에 작은 별빛
	const double Now = GetWorld()->GetTimeSeconds();
	FAuroraDPiece Burst;
	Burst.Born = Now;
	Burst.Life = 0.34f;
	Burst.From = Burst.To = Where + FVector(0.0f, 0.0f, 4.0f);
	Burst.SizeFrom = FVector2D(Size * 0.35f);
	Burst.SizeTo = FVector2D(Size);
	Burst.GrowSeconds = 0.08f;
	Burst.FadeOut = 0.24f;
	Burst.Strength = 0.85f;
	Burst.Spin = FMath::FRandRange(0.0f, 360.0f);
	AddDPiece(LoadFreshTexture(TEXT("T_Aurora_FxSplash")), Burst);
	FAuroraDPiece Flash;
	Flash.Born = Now;
	Flash.Life = ImpactStarLife * 0.8f;
	Flash.Face = 1;
	Flash.From = Flash.To = Where + FVector(0.0f, 0.0f, 20.0f);
	Flash.SizeFrom = FVector2D(ImpactStarFrom * StarScale);
	Flash.SizeTo = FVector2D(ImpactStarTo * StarScale);
	Flash.GrowSeconds = ImpactStarGrow * 0.7f;
	Flash.FadeOut = ImpactStarFade;
	Flash.Spin = FMath::FRandRange(0.0f, 90.0f);
	Flash.Lift = ImpactStarLift * StarScale;
	AddDPiece(LoadFreshTexture(TEXT("T_Aurora_FxStar")), Flash);
	if (bLight)
	{
		AddDLight(Where, ImpactLight * StarScale, ImpactLightRadius * StarScale, ImpactLightSeconds);
	}
}

void UAuroraSkillComponent::BlizzardFinale(const FVector& Center, const FVector& Toward)
{
	if (!GetWorld())
	{
		return;
	}
	if (CVarAuroraVLook.GetValueOnGameThread() >= 2)
	{
		// 94차 팩 효과 시안: 거대 결정 대신 같은 때 가운데에서 오로라 빙결 폭발이 크게 · 원 안 전부 피해(그 전과 같음)
		DFreshLater(BlizzardFinaleFall, [this, Center]()
		{
			UMaterialInterface* Rough = NovaRingRoughMaterial.LoadSynchronous();
			SpawnFrostNova(Center, BlizzardRadius * 1.1f, 2, 0.5f, Rough ? Rough : NovaRingMaterial.LoadSynchronous());
			SpawnBurstLater(CryoExplode, Center, VPackFinaleExplode, 0.0f);
			SpawnBurstLater(CryoInitialBlast, Center, VPackFinaleBlast, 0.0f);
			DFreshStrike(Center, BlizzardRadius, BlizzardFinaleDamage);
			UE_LOG(LogTemp, Display, TEXT("AURORA_BLIZZARD finale pack hits=%d"), IcicleHits.Num());
		});
		return;
	}
	// 거대 결정이 거의 곧게(바람 쪽으로 조금) 가운데로
	const float Slant = FMath::DegreesToRadians(BlizzardFinaleSlant);
	const FVector Fall = (Toward * FMath::Sin(Slant) - FVector::UpVector * FMath::Cos(Slant)).GetSafeNormal();
	DFreshDive(GetWorld()->GetTimeSeconds(), Center - Fall * BlizzardFinaleDrop, Center + Fall * BlizzardFinaleEmbed, Fall, BlizzardFinaleFall,
		BlizzardFinaleStuck, FVector2D(BlizzardFinaleWidth, BlizzardFinaleLength), BlizzardFinaleTrail, 0.3f);
	DFreshLater(BlizzardFinaleFall, [this, Center]()
	{
		// 꽂히면 가운데가 크게 번쩍 · 두 겹 충격파가 원 끝까지 · 조각 · 얼음 가루 · 빛기둥 · 마법진이 한 번 밝게 · 원 안 전부 피해
		DFreshImpact(Center, BlizzardFinaleImpact);
		UTexture* Ring = LoadFreshTexture(TEXT("T_Aurora_FxRing"));
		const double Now = GetWorld()->GetTimeSeconds();
		for (int32 Index = 0; Index < 2; ++Index)
		{
			FAuroraDPiece Wave;
			Wave.Born = Now + 0.08 * Index;
			Wave.Life = 0.55f;
			Wave.From = Wave.To = Center + FVector(0.0f, 0.0f, 6.0f);
			Wave.SizeFrom = FVector2D(2.0f * 60.0f / FreshRingCore);
			Wave.SizeTo = FVector2D(2.0f * BlizzardRadius * (Index == 0 ? 1.1f : 0.8f) / FreshRingCore);
			Wave.GrowSeconds = 0.45f;
			Wave.FadeOut = 0.2f;
			Wave.Strength = Index == 0 ? 1.0f : 0.6f;
			Wave.Spin = FMath::FRandRange(0.0f, 360.0f);
			AddDPiece(Ring, Wave);
		}
		DFreshShatter(Center, BlizzardFinaleChips, BlizzardFinaleChipReach, BlizzardFinaleChipScale);
		DFreshMotes(Center, BlizzardFinaleMotes, BlizzardRadius * 0.8f);
		DFreshPillar(Center, BlizzardPillarWidth, BlizzardPillarHeight);
		FAuroraDPiece Glare;
		Glare.Born = Now;
		Glare.Life = 0.6f;
		Glare.From = Glare.To = Center + FVector(0.0f, 0.0f, 4.0f);
		Glare.SizeFrom = Glare.SizeTo = FVector2D(2.0f * BlizzardRadius / BlizzardSealCore);
		Glare.FadeIn = 0.03f;
		Glare.FadeOut = 0.5f;
		Glare.Glow = 4.0f;
		Glare.CoreGlow = 6.0f;
		AddDPiece(LoadFreshTexture(TEXT("T_Aurora_BlizzardSeal")), Glare);
		DFreshStrike(Center, BlizzardRadius, BlizzardFinaleDamage);
		UE_LOG(LogTemp, Display, TEXT("AURORA_BLIZZARD finale hits=%d"), IcicleHits.Num());
	});
}

void UAuroraSkillComponent::BlizzardPack(const FVector& Center, int32 Look, float Total)
{
	if (!GetWorld())
	{
		return;
	}
	// D(옛 궁극기 — 「닫자, 좋음」)와 같은 말씨: 오로라 빙결 터짐·빙결 폭발 + 서리 충격파 고리. 바닥에 남는 것 없음
	UMaterialInterface* Rough = NovaRingRoughMaterial.LoadSynchronous();
	UMaterialInterface* Ring = Rough ? Rough : NovaRingMaterial.LoadSynchronous();
	// 한 자리 터짐 = 빙결 폭발 + 결정 + 고리 하나(2·4·6 공용)
	const auto Blast = [this, Ring](const FVector& Spot, float At, float Size)
	{
		SpawnBurstLater(CryoExplode, Spot, VPackBlastScale * Size, At);
		SpawnBurstLater(RockHitBurst, Spot, VPackRockScale * Size, At + 0.05f);
		DFreshLater(At, [this, Spot, Ring, Size]() { SpawnFrostNova(Spot, VPackRingRadius * Size, 1, VPackRingSeconds, Ring); });
	};
	if (Look == 4)
	{
		// 나선: 가운데에서 바깥으로 소용돌이를 그리며 차례로 터진다(흩뿌린 2와 달리 그린 듯한 순서)
		SpawnBurstLater(CryoInitialBlast, Center, VPackStartBlast, 0.0f);
		for (int32 Index = 0; Index < VSpiralBlasts; ++Index)
		{
			const float Alpha = (Index + 1.0f) / VSpiralBlasts;
			const FVector Spot = Center + FRotator(0.0f, 360.0f * VSpiralTurns * Alpha, 0.0f).Vector() * BlizzardRadius * 0.9f * FMath::Pow(Alpha, 0.7f);
			Blast(Spot, BlizzardStart + BlizzardSeconds * Index / VSpiralBlasts, 0.75f + 0.35f * Alpha);
		}
		UE_LOG(LogTemp, Display, TEXT("AURORA_BLIZZARD pack look=4 spiral=%d"), VSpiralBlasts);
		return;
	}
	if (Look == 5)
	{
		// 큰 파동 셋: 가운데 큰 빙결 터짐과 원 끝까지 고리 둘이 1.3초마다 세 번 — 파동마다 둘레에서 결정이 한 바퀴 터진다
		for (int32 Pulse = 0; Pulse < static_cast<int32>(UE_ARRAY_COUNT(VPulseTimes)); ++Pulse)
		{
			const float At = VPulseTimes[Pulse];
			SpawnBurstLater(CryoInitialBlast, Center, VPackFreezeBlast * (0.7f + 0.15f * Pulse), At);
			DFreshLater(At, [this, Center, Ring]() { SpawnFrostNova(Center, BlizzardRadius, 2, VPackFreezeRingSeconds, Ring); });
			for (int32 Index = 0; Index < VPulseRim; ++Index)
			{
				const FVector Spot = Center + FRotator(0.0f, 360.0f * (Index + 0.5f * Pulse) / VPulseRim, 0.0f).Vector() * BlizzardRadius * 0.7f;
				SpawnBurstLater(RockHitBurst, Spot, VPackRockScale, At + 0.15f);
			}
		}
		UE_LOG(LogTemp, Display, TEXT("AURORA_BLIZZARD pack look=5 pulses=%d"), static_cast<int32>(UE_ARRAY_COUNT(VPulseTimes)));
		return;
	}
	if (Look == 6)
	{
		// 조여 들기: 원 둘레에 폭발 벽 → 중간 고리 → 가운데로 몰아쳐 끝 큰 폭발로 이어진다
		for (int32 Index = 0; Index < VCloseOuter; ++Index)
		{
			const FVector Spot = Center + FRotator(0.0f, 360.0f * Index / VCloseOuter, 0.0f).Vector() * BlizzardRadius * VCloseOuterReach;
			Blast(Spot, BlizzardStart + 1.4f * Index / VCloseOuter, 0.9f);
		}
		for (int32 Index = 0; Index < VCloseMiddle; ++Index)
		{
			const FVector Spot = Center + FRotator(0.0f, 30.0f + 360.0f * Index / VCloseMiddle, 0.0f).Vector() * BlizzardRadius * VCloseMiddleReach;
			Blast(Spot, BlizzardStart + 1.8f + 1.0f * Index / VCloseMiddle, 1.0f);
		}
		Blast(Center, BlizzardStart + 3.2f, 1.3f);
		UE_LOG(LogTemp, Display, TEXT("AURORA_BLIZZARD pack look=6 outer=%d middle=%d"), VCloseOuter, VCloseMiddle);
		return;
	}
	if (Look == 2)
	{
		// 폭격: 원 안 고른 자리(해바라기 배치)에서 쏟아지는 4초 동안 차례로 — 자리마다 빙결 폭발 + 결정 + 고리 하나
		SpawnBurstLater(CryoInitialBlast, Center, VPackStartBlast, 0.0f);
		for (int32 Index = 0; Index < VPackBlasts; ++Index)
		{
			const FVector Spot = FreshSeat(Center, Index, VPackBlasts, 5, BlizzardRadius * 0.8f);
			const float At = BlizzardStart + BlizzardSeconds * (Index + FMath::FRandRange(0.0f, 0.7f)) / VPackBlasts;
			SpawnBurstLater(CryoExplode, Spot, VPackBlastScale, At);
			SpawnBurstLater(RockHitBurst, Spot, VPackRockScale, At + 0.05f);
			DFreshLater(At, [this, Spot, Ring]() { SpawnFrostNova(Spot, VPackRingRadius, 1, VPackRingSeconds, Ring); });
		}
		UE_LOG(LogTemp, Display, TEXT("AURORA_BLIZZARD pack look=2 blasts=%d"), VPackBlasts);
		return;
	}
	// 3 얼어붙는 땅: 시작에 가운데 큰 빙결 터짐 + 원 끝까지 고리 둘, 원 안 적은 전부 끝 폭발까지 얼음에 갇히고(D 빙결과 같은 얼음),
	// 그동안 결정이 차례로 터진다
	SpawnBurstLater(CryoInitialBlast, Center, VPackFreezeBlast, 0.0f);
	SpawnFrostNova(Center, BlizzardRadius, 2, VPackFreezeRingSeconds, Ring);
	TArray<AActor*> Targets;
	GatherTargets(Center, BlizzardRadius, Targets);
	for (AActor* Target : Targets)
	{
		AttachTimedEffect(CryoFrozen, Target, FMath::Max(Total - BlizzardLinger, 0.5f));
	}
	for (int32 Index = 0; Index < VPackFreezeBursts; ++Index)
	{
		const FVector Spot = FreshSeat(Center, Index, VPackFreezeBursts, 5, BlizzardRadius * 0.8f);
		SpawnBurstLater(RockHitBurst, Spot, VPackRockScale, BlizzardStart + BlizzardSeconds * (Index + FMath::FRandRange(0.0f, 0.7f)) / VPackFreezeBursts);
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_BLIZZARD pack look=3 frozen=%d bursts=%d"), Targets.Num(), VPackFreezeBursts);
}

void UAuroraSkillComponent::BlizzardStorm(float Seconds, bool bDim)
{
	UMaterialInterface* Snow = LoadFreshMaterial(TEXT("M_Aurora_FxSnow"));
	UTexture* SnowPicture = LoadFreshTexture(TEXT("T_Aurora_FxSnow"));
	if (!GetWorld() || !Snow || !SnowPicture)
	{
		UE_LOG(LogTemp, Warning, TEXT("AURORA_BLIZZARD missing snow"));
		return;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	for (const FBlizzardLayer& Layer : BlizzardLayers)
	{
		FAuroraDPiece Sheet;
		Sheet.Born = Now;
		Sheet.Life = Seconds;
		Sheet.Face = 3;
		Sheet.Lift = Layer.Distance;
		Sheet.SizeFrom = Sheet.SizeTo = FVector2D(Layer.Distance * BlizzardLayerCover);
		Sheet.FadeIn = BlizzardStormFadeIn;
		Sheet.FadeOut = BlizzardStormFadeOut;
		Sheet.Strength = Layer.Strength;
		Sheet.SortPriority = BlizzardSnowSort;
		Sheet.Scalars.Emplace(TEXT("Tiling"), Layer.Tiling);
		Sheet.Scalars.Emplace(TEXT("SpeedX"), Layer.SpeedX);
		Sheet.Scalars.Emplace(TEXT("SpeedY"), Layer.SpeedY);
		AddDPiece(SnowPicture, Sheet, Snow);
	}
	UMaterialInterface* Dim = bDim ? LoadFreshMaterial(TEXT("M_Aurora_FxDim")) : nullptr;
	if (Dim)
	{
		FAuroraDPiece Shade;
		Shade.Born = Now;
		Shade.Life = Seconds;
		Shade.Face = 3;
		Shade.Lift = BlizzardDimDistance;
		Shade.SizeFrom = Shade.SizeTo = FVector2D(BlizzardDimDistance * BlizzardLayerCover);
		Shade.FadeIn = BlizzardStormFadeIn;
		Shade.FadeOut = BlizzardStormFadeOut;
		Shade.Strength = BlizzardDimStrength;
		Shade.SortPriority = BlizzardDimSort;
		AddDPiece(SnowPicture, Shade, Dim);
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_BLIZZARD storm layers=%d dim=%d"), static_cast<int32>(UE_ARRAY_COUNT(BlizzardLayers)), Dim ? 1 : 0);
}

void UAuroraSkillComponent::BeginChunkVolley()
{
	if (CVarAuroraCrystalShot.GetValueOnGameThread() == 0 || !Character.IsValid() || !GetWorld() || !LoadFreshMaterial(TEXT("M_Aurora_FxAdd")))
	{
		return;
	}
	// 칼을 드는 동안 오로라 뒤 머리 위에 덩어리가 가운데부터 하나씩 생긴다 — 덩어리마다 각진 보석이 둘레에서 모여들어(끝이 바깥) 한 덩어리가
	// 되고, 쏠 차례가 올 때까지 위아래로 조금 흔들리며 떠 있다
	FVector Dir = (ActiveAim - Character->GetActorLocation()).GetSafeNormal2D();
	if (Dir.IsNearlyZero())
	{
		Dir = Character->GetActorForwardVector().GetSafeNormal2D();
	}
	const FVector Feet = GetFeetLocation();
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Dir).GetSafeNormal();
	const float Charge = Skills[EAuroraSkill::IceLance].ActionTime;
	const double Now = GetWorld()->GetTimeSeconds();
	UTexture* Gem = LoadFreshTexture(TEXT("T_Aurora_FxGem"));
	UTexture* Star = LoadFreshTexture(TEXT("T_Aurora_FxStar"));
	// 87차 「F도 얼음 이펙트 자체가 아쉽다」: 보석 그림 대신 입체 얼음 메시(Aurora.FX.FChunk 1·2)
	const bool bMeshChunks = GetFChunk() > 0;
	if (bMeshChunks)
	{
		ClearChunkMeshes();
	}
	for (int32 Index = 0; Index < ChunkCount; ++Index)
	{
		const FVector Spot = ChunkSpot(Feet, Dir, Index);
		const int32 Turn = ChunkTurn(Index);
		const float Appear = ChunkAppear * Turn;
		// 쏘는 순간(ExecuteChunkVolley가 같은 차례로 창을 띄움)까지
		const float Life = Charge + ChunkFireInterval * Turn - Appear;
		const float Phase = FMath::FRandRange(0.0f, 2.0f * PI);
		if (bMeshChunks)
		{
			SpawnChunkMesh(Index, Spot, Appear, Life, Phase);
			DFreshLater(Appear, [this, Spot]() { DFreshGlint(Spot, ChunkPop); });
			continue;
		}
		for (int32 Part = 0; Part < ChunkGems; ++Part)
		{
			const float Angle = PI * 0.5f + 2.0f * PI * Part / ChunkGems + FMath::FRandRange(-0.25f, 0.25f);
			const FVector Radial = Right * FMath::Cos(Angle) + FVector::UpVector * FMath::Sin(Angle);
			FAuroraDPiece Piece;
			Piece.Born = Now + Appear;
			Piece.Life = Life;
			Piece.Face = 2;
			Piece.Axis = Radial;
			Piece.From = Spot + Radial * (ChunkGather + FMath::FRandRange(0.0f, 30.0f));
			Piece.To = Spot + Radial * ChunkGemReach;
			Piece.MoveSeconds = ChunkForm;
			Piece.MoveEase = 2;
			Piece.SizeTo = FVector2D(ChunkGemWidth, ChunkGemLength) * FMath::FRandRange(0.85f, 1.2f);
			Piece.SizeFrom = Piece.SizeTo * 0.3f;
			Piece.GrowSeconds = 0.12f;
			Piece.FadeIn = 0.05f;
			Piece.FadeOut = 0.02f;
			Piece.Glow = ChunkGemGlow;
			Piece.CoreGlow = ChunkGemCore;
			Piece.Bob = ChunkBob;
			Piece.BobRate = ChunkBobRate;
			Piece.BobPhase = Phase;
			AddDPiece(Gem, Piece);
		}
		FAuroraDPiece Orb;
		Orb.Born = Now + Appear;
		Orb.Life = Life;
		Orb.Face = 1;
		Orb.From = Orb.To = Spot;
		Orb.SizeFrom = FVector2D(ChunkOrb * 0.3f);
		Orb.SizeTo = FVector2D(ChunkOrb);
		Orb.GrowSeconds = ChunkForm;
		Orb.FadeIn = 0.05f;
		Orb.FadeOut = 0.02f;
		Orb.Strength = ChunkOrbStrength;
		Orb.SpinRate = 200.0f;
		Orb.Bob = ChunkBob;
		Orb.BobRate = ChunkBobRate;
		Orb.BobPhase = Phase;
		Orb.Lift = 20.0f;
		AddDPiece(Star, Orb);
		// 생기는 순간 작게 번쩍
		DFreshLater(Appear, [this, Spot]() { DFreshGlint(Spot, ChunkPop); });
	}
}

bool UAuroraSkillComponent::ExecuteChunkVolley()
{
	if (CVarAuroraCrystalShot.GetValueOnGameThread() == 0 || !Character.IsValid() || !GetWorld() || !LoadFreshMaterial(TEXT("M_Aurora_FxAdd")))
	{
		return false;
	}
	FVector Dir = (ActiveAim - Character->GetActorLocation()).GetSafeNormal2D();
	if (Dir.IsNearlyZero())
	{
		Dir = Character->GetActorForwardVector().GetSafeNormal2D();
	}
	const FVector Feet = GetFeetLocation();
	const FAuroraSkillDefinition& Definition = Skills[EAuroraSkill::IceLance];
	// 여러 명을 겨눈다: 사거리 안 적을 겨눈 자리에 가까운 차례로, 덩어리가 더 많으면 처음부터 돌아가며. 아무도 없으면 겨눈 자리 둘레에 꽂힌다
	TArray<AActor*> Targets;
	GatherTargets(Feet, Definition.Range, Targets);
	const FVector Aim(ActiveAim.X, ActiveAim.Y, Feet.Z);
	Targets.Sort([Aim](const AActor& A, const AActor& B)
	{
		return FVector::DistSquared2D(A.GetActorLocation(), Aim) < FVector::DistSquared2D(B.GetActorLocation(), Aim);
	});
	FVector Fallback = Aim;
	if (FVector::Dist2D(Fallback, Feet) > Definition.Range)
	{
		Fallback = Feet + (Fallback - Feet).GetSafeNormal2D() * Definition.Range;
	}
	Fallback.Z = FindFloorZ(Fallback + FVector(0.0f, 0.0f, 100.0f), Feet.Z);
	for (int32 Turn = 0; Turn < ChunkCount; ++Turn)
	{
		const int32 Index = ChunkOrder[Turn];
		const FVector Spot = ChunkSpot(Feet, Dir, Index);
		const TWeakObjectPtr<AActor> Target = Targets.IsEmpty() ? nullptr : Targets[Turn % Targets.Num()];
		const FVector Miss = Fallback + FVector(FMath::Cos(2.0f * PI * Turn / ChunkCount), FMath::Sin(2.0f * PI * Turn / ChunkCount), 0.0f) *
			(Turn == 0 ? 0.0f : ChunkMissScatter);
		DFreshLater(ChunkFireInterval * Turn, [this, Index, Spot, Target, Miss, Damage = Definition.Damage]()
		{
			// 덩어리가 창이 되어 그 순간 대상 자리로 곧게(대상이 없으면 바닥으로)
			const bool bAimed = Target.IsValid();
			const FVector Goal = bAimed ? Target->GetActorLocation() : Miss;
			const FVector Axis = (Goal - Spot).GetSafeNormal();
			const float Flight = FVector::Dist(Spot, Goal) / ChunkSpeed;
			const double Now = GetWorld()->GetTimeSeconds();
			DFreshGlint(Spot, ChunkPop * 1.3f);
			// 87차 입체 덩어리(FChunk 1·2)는 그 메시가 그대로 날아간다 — 창·빛줄기 그림은 띄우지 않는다
			if (GetFChunk() > 0)
			{
				FireChunkMesh(Index, Goal, Flight);
			}
			else
			{
				FAuroraDPiece Spear;
				Spear.Born = Now;
				Spear.Life = Flight + 0.04f;
				Spear.Face = 2;
				Spear.Axis = Axis;
				Spear.From = Spot;
				Spear.To = Goal;
				Spear.MoveSeconds = Flight;
				Spear.SizeFrom = Spear.SizeTo = FVector2D(ChunkSpearWidth, ChunkSpearLength);
				Spear.FadeOut = 0.04f;
				Spear.Lift = 10.0f;
				Spear.Glow = ShardGlow;
				Spear.CoreGlow = 3.0f;
				AddDPiece(LoadFreshTexture(TEXT("T_Aurora_FxSpike")), Spear);
				FAuroraDPiece Tail = Spear;
				Tail.Life = Flight + 0.14f;
				Tail.SizeFrom = Tail.SizeTo = FVector2D(ChunkTrailWidth, ChunkTrailLength);
				Tail.FadeOut = 0.14f;
				Tail.Strength = 0.85f;
				Tail.Glow = Tail.CoreGlow = -1.0f;
				AddDPiece(LoadFreshTexture(TEXT("T_Aurora_FxStreak")), Tail);
			}
			DFreshLater(Flight, [this, Target, Goal, Axis, Damage, bAimed]()
			{
				// 꽂힌 자리: 조각 · 반짝 · 바닥 얼음 튐 — 대상이 아직 근처에 있으면 피해 + 감속(처음 맞힌 하나만 멈칫)
				AActor* Victim = Target.Get();
				const FVector Where = Victim ? Victim->GetActorLocation() : Goal;
				DFreshShatter(Where, ChunkHitShards, 110.0f, 0.7f);
				DFreshGlint(Where, ShatterGlint);
				BlizzardSplash(FVector(Where.X, Where.Y, FindFloorZ(Where, Where.Z - 90.0f)), ChunkSplash, 0.6f, true);
				// 87차 F-1 「맞는 순간 큰 결정 파열」(Aurora.FX.FBurst) — 남는 작은 가시는 「바닥 얼음 오브젝트 남발 금지」로 뺐다
				if (UseFBurst())
				{
					PolishHitBurst(FVector(Where.X, Where.Y, FindFloorZ(Where, Where.Z - 90.0f)), 1.1f);
				}
				if (!bAimed || !Victim || FVector::Dist2D(Victim->GetActorLocation(), Goal) > 150.0f)
				{
					return;
				}
				if (ChunkVictims.IsEmpty())
				{
					BeginHitStop(Victim, FreshHitStopSeconds);
				}
				ChunkVictims.Add(Victim);
				++ChunkHits;
				if (Victim->CanBeDamaged())
				{
					FHitResult Hit(Victim, nullptr, Victim->GetActorLocation(), -Axis);
					UGameplayStatics::ApplyPointDamage(Victim, Damage, Axis, Hit, Character.IsValid() ? Character->GetController() : nullptr,
						GetOwner(), nullptr);
				}
				SetFreshStatus(Victim, TEXT("SLOW"), ChunkSlowSeconds);
			});
		});
	}
	ChunkVictims.Reset();
	ChunkHits = 0;
	DFreshLater(ChunkFireInterval * ChunkCount + 0.6f, [this]()
	{
		UE_LOG(LogTemp, Display, TEXT("AURORA_CHUNK end hits=%d targets=%d"), ChunkHits, ChunkVictims.Num());
	});
	UE_LOG(LogTemp, Display, TEXT("AURORA_CHUNK fired=%d targets=%d"), ChunkCount, Targets.Num());
	return true;
}
