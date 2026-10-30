// F 얼음 새 시안(Aurora.FX.FBird, 10-21 「얼음 모양 매나 새 같은 게 날아가는 거 어때? F는」 — 헤더 LanceBirdHeight 설명).
// 나는 길·맞힘·맞은 자리 터짐은 창 그대로 두고, 숨긴 창 자리를 새가 따라 난다.
// 이어서(10-21 「매는 훨씬 더 얇은 느낌 · 매 아니어도 여러 시안 — 송곳은 별로였고, 매랑 또 뭐가 있을까」): 3 얇은 매 · 4 얼음 용 · 5 눈꽃 표창 · 6 봉황.
// 넷 다 aurora_bird_art.py가 그린 가는 선 그림(안은 거의 비침)이고 재질은 그림 매와 같은 짜임(aurora_frost_materials_build.py flyerdrafts).
#include "AuroraSkillComponent.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Particles/ParticleSystemComponent.h"

namespace
{
	// 이어서 「F도 매 모양 좀...」 → 새로 그린 매 중 날씬한 쪽 8(얇은 느낌도 살림)이 고르기 전까지 기본.
	// 이어서 10-26 「3D 매 — 디테일은 필요 없고 매라고 느끼기만」 → 9(입체 매, 어깨·손목에서 꺾이는 날갯짓이 원근으로 보여 새처럼 움직임)가 고르기 전까지 기본.
	// 10-25 「F는 그럼 일단 매 한 마리만 일직선으로 날아가서 펑 터지는 그런 느낌으로」 → 3(얇은 매 — 10-21 「훨씬 더 얇은 느낌」). 새는 한 마리만
	// 곧게 날고, 멈추면 충격파 고리(LanceBirdBurstSeconds)가 더해진다.
	TAutoConsoleVariable<int32> CVarAuroraLanceBird(
		TEXT("Aurora.FX.FBird"), 9,
		TEXT("Ice Lance flyer draft (any flyer flies alone, straight, and bursts with a frost ring where it stops): 0 the three ice clones, 1 a glowing ice hawk seen from above, beating its wings (drawn), 2 a faceted ice-crystal hawk flapping its wings, 3 a thin ice hawk (slim wings, line drawing), 4 a thin ice dragon snaking along (head, scaled links, legs, tail), 5 a spinning snowflake blade, 6 a thin ice phoenix trailing long tail streamers, 7 a full ice hawk (broad wings, six fingered primaries, fan tail), 8 the same hawk slimmed, 9 the slim hawk built in 3D as faceted ice, its wings bending at shoulder and wrist (default)."));

	// 10-26 「F는 니 추천이 그나마 낫긴 한데... 이펙트가 뭔가 너무 아쉬운데 보완할 방법 없을까」 — 59차 촬영에서 매가 작고 하얀 스티커처럼
	// 납작했고 0.2초 만에 지나갔으며, 나는 길엔 작은 반짝임 몇 개뿐이었다(멈출 때 터짐은 허수아비에 맞으면 원래도 크다 — 59차 촬영은 빈 바닥
	// 화면 밖에서 터졌다). 비트로 더해 본다(잔상·눈송이·몸 빛은 판 하나 매 1·3·7·8에만).
	// 첫 판의 2 바닥 서리 줄(창 시안 1)은 흰 레이저 줄처럼, 4 큰 터짐(별 금 + 충격파 + 섬광)은 원래 터짐과 차이가 거의 없어 바꿨다.
	// 촬영(70차): 1 잔상은 생선 뼈처럼 줄줄이(느리게와 겹치면 날개 여러 겹 덩어리), 2 눈송이는 거의 안 보임 → 고르기 전까지 12(느리게 + 몸 빛).
	TAutoConsoleVariable<int32> CVarAuroraLanceBirdLook(
		TEXT("Aurora.FX.FLook"), 12,
		TEXT("Ice hawk quality draft bitmask: 1 a fading trail of the hawk's afterimages left every frame, 2 snowflakes stream off the hawk as it flies, 4 the hawk flies at half speed so it is seen crossing, 8 the hawk glows brighter and flies a quarter larger. 12 = 4 + 8 (default), 0 = none."));

	// 10-26 「매가 날아가는 쪽에 뭔가 이펙트가 있었으면 좋겠는데 시안 만들어 줄래?」: 비트로 더한다. 빛줄기는 R 난무 칼 빛과 같은 판
	// (M_Aurora_CutMark)을 나는 쪽으로 눕힌 것, 반짝이는 램페이지 얼음 정령 불꽃, 부스러기는 창 꼬리 시안(FFlight 1)과 같은 것.
	// 촬영(72차): 1은 화살대처럼, 4·8은 거의 안 보임. 사용자가 원한 건 나는 길이 아니라 소환되는 때의 이펙트였다(「이런 이펙트가 아니라 매가
	// 소환되는 타이밍에」 — Aurora.FX.FSummon) → 0.
	TAutoConsoleVariable<int32> CVarAuroraLanceBirdTrail(
		TEXT("Aurora.FX.FTrail"), 0,
		TEXT("Ice hawk flight trail draft bitmask: 1 a long streak of light trailing behind its body, 2 thin streaks of light off both wingtips, 4 icy sparks swirling off the hawk, 8 ice crumbs shed behind it. 0 = none (default)."));
	// 10-26 「입체 매로 일단 하되, 매가 소환되는 타이밍에 뭔가 이펙트가 있어야 하지 않겠냐」: 매가 나타나는 자리에 한 번.
	// 촬영(73차): 1 흰 연기 뭉치로 뿌옇고 · 3 오로라를 덮는 큰 돔 · 4 은은함 — 내 추천은 2였고, 사용자가 「4번 좋다, 4번으로 가자」.
	TAutoConsoleVariable<int32> CVarAuroraLanceBirdSummon(
		TEXT("Aurora.FX.FSummon"), 4,
		TEXT("Ice hawk summon draft: 0 it just pops in, 1 Aurora's own ice-decoy summon bloom where it appears, 2 a blue flash with a burst of ice shards and a small frost ring under it, 3 a small white burst from her ultimate, 4 no effect - the hawk glows in from faint and small to full (default)."));
	const TCHAR* const BirdSparkPath =
		TEXT("/Game/ParagonRampage/FX/Particles/Rampage_v001_IceBlue/FX/P_Rampage_Ice_Elemental_Enraged_Sparks.P_Rampage_Ice_Elemental_Enraged_Sparks");

	// 9 입체 매(10-26 「3D 매를 니가 만들 수 있겠어? — 디테일은 필요 없고 유저가 매라고 느끼기만 하면 돼」): aurora_bird_art.py hawk3d —
	// 날씬한 매 날개 + 꽉 찬 매 몸·꼬리를 위에서 본 모양 그대로 세운 각진 얼음판, 날개폭 약 160(그림 매를 줄인 크기와 같음).
	// 몸 · 오른·왼 안쪽 날개(원점 = 어깨) · 오른·왼 바깥쪽 날개(원점 = 손목). 어깨·손목 자리(cm, 오른쪽 기준)는 그 도구가 찍은 값.
	const TCHAR* const Hawk3DParts[] = {
		TEXT("/Game/TopDown/Characters/Aurora/FX/Meshes/SM_Aurora_Hawk3D_Body.SM_Aurora_Hawk3D_Body"),
		TEXT("/Game/TopDown/Characters/Aurora/FX/Meshes/SM_Aurora_Hawk3D_InnerR.SM_Aurora_Hawk3D_InnerR"),
		TEXT("/Game/TopDown/Characters/Aurora/FX/Meshes/SM_Aurora_Hawk3D_InnerL.SM_Aurora_Hawk3D_InnerL"),
		TEXT("/Game/TopDown/Characters/Aurora/FX/Meshes/SM_Aurora_Hawk3D_OuterR.SM_Aurora_Hawk3D_OuterR"),
		TEXT("/Game/TopDown/Characters/Aurora/FX/Meshes/SM_Aurora_Hawk3D_OuterL.SM_Aurora_Hawk3D_OuterL")};
	const FVector2D Hawk3DShoulder(10.4f, 5.6f);
	const FVector2D Hawk3DWrist(5.6f, 42.4f);
	// 날갯짓: 초당 · 가운데 각 · 어깨 폭(도) · 손목 폭(도) · 손목이 늦는 정도(라디안)
	constexpr float Hawk3DFlapRate = 3.0f;
	constexpr float Hawk3DFlapMid = 6.0f;
	constexpr float Hawk3DFlapAmp = 30.0f;
	constexpr float Hawk3DHandAmp = 22.0f;
	constexpr float Hawk3DHandLag = 0.7f;

	const TCHAR* const CrystalHawkParts[] = {
		TEXT("/Game/TopDown/Characters/Aurora/FX/Meshes/SM_Aurora_CrystalHawk_Body.SM_Aurora_CrystalHawk_Body"),
		TEXT("/Game/TopDown/Characters/Aurora/FX/Meshes/SM_Aurora_CrystalHawk_WingR.SM_Aurora_CrystalHawk_WingR"),
		TEXT("/Game/TopDown/Characters/Aurora/FX/Meshes/SM_Aurora_CrystalHawk_WingL.SM_Aurora_CrystalHawk_WingL"),
		TEXT("/Game/TopDown/Characters/Aurora/FX/Meshes/SM_Aurora_CrystalHawk_Tail.SM_Aurora_CrystalHawk_Tail")};

	// 판 하나로 그리는 시안: 재질 · 그림 장(가로 × 세로, 왼쪽 위부터) · 판 폭·길이(cm, 그림 칸 비율 그대로) · 나는 자리(어깨)가 판 가운데보다
	// 앞선 거리(cm) · 장 넘김(초당) · 도는 빠르기(도/초, 위에서 보아 + = 시계 방향).
	// 매 판 240cm는 날개 끝 사이 약 0.94배. 얇은 매는 선이 가늘어진 만큼 조금 크게. 봉황 칸은 512 × 1024(어깨가 칸 높이 0.24 — 앞선 거리
	// = 0.26 × 길이), 꼬리 깃이 어깨 뒤 약 330cm까지. 눈꽃 표창은 팔이 꼬리 쪽으로 휜 바람개비라 시계 반대로 돈다(팔 끝이 뒤처지게).
	struct FFlyerCard
	{
		int32 Kind;
		const TCHAR* Material;
		int32 Columns;
		int32 Rows;
		float Width;
		float Length;
		float Ahead;
		float FrameRate;
		float Spin;
	};
	const FFlyerCard FlyerCards[] = {
		{1, TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_IceHawk.M_Aurora_IceHawk"), 4, 2, 240.0f, 240.0f, 0.0f, 40.0f, 0.0f},
		{3, TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_IceHawkThin.M_Aurora_IceHawkThin"), 4, 2, 260.0f, 260.0f, 0.0f, 40.0f, 0.0f},
		// 10-25 「F도 매 모양 좀...」: 7 꽉 찬 매 · 8 날씬한 매(aurora_bird_art.py bold — 넓은 날개 · 손 판에서 벌어지는 첫째 깃 여섯 · 짧은 몸통 · 부채 꼬리)
		// 판은 처음 260 → 10-26 「매 너무 큰데... 거의 절반 크기로」로 130(몸 빛 시안 FLook 8의 1.25배를 더해 화면에서 약 160, 그 전 325)
		{7, TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_IceHawkBold.M_Aurora_IceHawkBold"), 4, 2, 130.0f, 130.0f, 0.0f, 40.0f, 0.0f},
		{8, TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_IceHawkSlim.M_Aurora_IceHawkSlim"), 4, 2, 130.0f, 130.0f, 0.0f, 40.0f, 0.0f},
		{5, TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_FrostStar.M_Aurora_FrostStar"), 1, 1, 130.0f, 130.0f, 0.0f, 0.0f, -540.0f},
		{6, TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_IcePhoenix.M_Aurora_IcePhoenix"), 4, 2, 260.0f, 520.0f, 135.0f, 24.0f, 0.0f},
	};

	const FFlyerCard* FindFlyerCard(int32 Kind)
	{
		for (const FFlyerCard& Card : FlyerCards)
		{
			if (Card.Kind == Kind)
			{
				return &Card;
			}
		}
		return nullptr;
	}

	// 얼음 용(4): 그림 2 × 2(0 머리 · 1 몸통 마디 · 2 다리 달린 마디 · 3 꼬리 끝). 머리 판(가운데 = 나는 자리, 아래 끝까지 목) 뒤로 마디를
	// DragonSpacing마다 이어 꼬리까지 — 마디마다 머리가 지나간 길 위 자리에 놓여 구불구불 따라온다(바닥 기준 옆으로 DragonSway, 한 물결
	// DragonWave, 떠난 자리에서 DragonSwayRamp까지는 곧게 펴졌다 커짐). 몸통 폭은 목 DragonTubeFrom → 꼬리 DragonTubeTo로 가늘어지고, 마디
	// 판 폭 = 몸통 폭 × 2.128 / 1.1(그림 칸에서 몸통 반폭 0.55, 칸 반폭 1.064) · 길이 = 틈 × DragonLinkOverlap(겹친 끝은 그림이 서로 반대로 옅어진다).
	// 다리는 DragonLegLinks번째 마디. 떠난 자리(창이 던져진 곳)를 아직 못 지난 마디는 숨긴다.
	const TCHAR* const DragonMaterialPath = TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_IceDragon.M_Aurora_IceDragon");
	constexpr float DragonHeadCard = 140.0f;
	constexpr int32 DragonLinks = 13;
	constexpr float DragonSpacing = 30.0f;
	constexpr float DragonLinkOverlap = 1.1f;
	constexpr float DragonTubeFrom = 22.0f;
	constexpr float DragonTubeTo = 10.0f;
	constexpr float DragonCardPerTube = 2.128f / 1.1f;
	constexpr float DragonTailLength = 55.0f;
	constexpr float DragonSway = 34.0f;
	constexpr float DragonWave = 480.0f;
	constexpr float DragonSwayRamp = 150.0f;
	constexpr int32 DragonLegLinks[] = {2, 8};
	// 부서질 때: 머리 + DragonShardEvery 마디마다 파편 DragonShards개
	constexpr int32 DragonShardEvery = 3;
	constexpr int32 DragonShards = 4;

	float DragonTube(int32 Link)
	{
		return FMath::Lerp(DragonTubeFrom, DragonTubeTo, Link / static_cast<float>(DragonLinks));
	}
}

int32 UAuroraSkillComponent::GetFBird() const
{
	return CVarAuroraLanceBird.GetValueOnGameThread();
}

int32 UAuroraSkillComponent::GetFLook() const
{
	return CVarAuroraLanceBirdLook.GetValueOnGameThread();
}

int32 UAuroraSkillComponent::GetFTrail() const
{
	return CVarAuroraLanceBirdTrail.GetValueOnGameThread();
}

int32 UAuroraSkillComponent::GetFSummon() const
{
	return CVarAuroraLanceBirdSummon.GetValueOnGameThread();
}

void UAuroraSkillComponent::SpawnLanceBird(FAuroraLance& Lance, const FVector& Origin, int32 Index)
{
	const int32 Kind = GetFBird();
	if (Kind == 0 || !GetWorld())
	{
		return;
	}
	// 창이 다 날 시간 + 1초(창 칼날과 같은 수명) — 그 전에 멈추면 EndLanceBird가 지운다
	const float Life = Skills[EAuroraSkill::IceLance].Range / (LanceSpeed * LanceSpeedScale) + 1.0f;
	const FVector Where(Origin.X, Origin.Y, LanceFloorZ + LanceBirdHeight);
	Lance.Bird = Kind;
	Lance.BirdLook = GetFLook();
	Lance.BirdBorn = GetWorld()->GetTimeSeconds();
	Lance.BirdPhase = Index / static_cast<float>(LanceCount);
	const auto AddCard = [this, &Lance, &Where, Life](UMaterialInterface* Material) -> UMaterialInstanceDynamic*
	{
		UStaticMeshComponent* Card = SpawnTimedMesh(PlaneMesh, FTransform(Where), Life);
		if (!Card)
		{
			return nullptr;
		}
		UMaterialInstanceDynamic* Dynamic = UMaterialInstanceDynamic::Create(Material, Card);
		Card->SetMaterial(0, Dynamic);
		Card->SetCastShadow(false);
		Card->SetReceivesDecals(false);
		Lance.BirdParts.Add(Card);
		return Dynamic;
	};
	if (const FFlyerCard* Flyer = FindFlyerCard(Kind))
	{
		UMaterialInterface* Material = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(Flyer->Material)).LoadSynchronous();
		Lance.BirdMaterial = Material ? AddCard(Material) : nullptr;
		if (!Lance.BirdMaterial.IsValid())
		{
			EndLanceBird(Lance, false);
			Lance.Bird = 0;
			return;
		}
		if (Lance.BirdLook & 8)
		{
			// 몸 빛: 선·몸통 빛을 세게, 둘레 번짐을 짙게(재질 기본 1.1 · 2.5 · 0.5 — aurora_frost_materials_build.py hawkdrafts)
			Lance.BirdMaterial->SetScalarParameterValue(TEXT("Brightness"), 1.6f);
			Lance.BirdMaterial->SetScalarParameterValue(TEXT("LineGlow"), 4.0f);
			Lance.BirdMaterial->SetScalarParameterValue(TEXT("HaloOpacity"), 0.9f);
		}
		if ((Lance.BirdLook & 2) && MeleeSnowflakes && !Lance.BirdParts.IsEmpty())
		{
			// 눈송이 꼬리: 평타 눈송이를 매 판에 붙여 날며 흘린다(멈추면 EndLanceBird가 끈다)
			if (UParticleSystemComponent* Snow = UGameplayStatics::SpawnEmitterAttached(MeleeSnowflakes, Lance.BirdParts[0].Get(), NAME_None,
				FVector::ZeroVector, FRotator::ZeroRotator, FVector(LanceBirdFlakeScale), EAttachLocation::KeepRelativeOffset, false))
			{
				OwnedEffects.Add(Snow);
				Lance.BirdFlakes = Snow;
			}
		}
	}
	else if (Kind == 4)
	{
		UMaterialInterface* Material = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(DragonMaterialPath)).LoadSynchronous();
		// 머리(장 0) · 마디(1, 다리 마디 2) · 꼬리(3) — 장은 판마다 한 번 정한다
		for (int32 Part = 0; Material && Part < DragonLinks + 2; ++Part)
		{
			int32 Frame = Part == 0 ? 0 : (Part == DragonLinks + 1 ? 3 : 1);
			for (const int32 Leg : DragonLegLinks)
			{
				Frame = Part == Leg + 1 ? 2 : Frame;
			}
			UMaterialInstanceDynamic* Dynamic = AddCard(Material);
			if (!Dynamic)
			{
				break;
			}
			Dynamic->SetScalarParameterValue(TEXT("FrameU"), (Frame % 2) / 2.0f);
			Dynamic->SetScalarParameterValue(TEXT("FrameV"), (Frame / 2) / 2.0f);
			Lance.BirdMaterial = Part == 0 ? Dynamic : Lance.BirdMaterial.Get();
		}
		if (Lance.BirdParts.Num() != DragonLinks + 2)
		{
			EndLanceBird(Lance, false);
			Lance.Bird = 0;
			return;
		}
	}
	else
	{
		// 2 결정 매(몸·날개 둘·꼬리) · 9 입체 매(몸·안쪽 날개 둘·바깥쪽 날개 둘)
		const TArrayView<const TCHAR* const> Paths = Kind == 9 ? TArrayView<const TCHAR* const>(Hawk3DParts) :
			TArrayView<const TCHAR* const>(CrystalHawkParts);
		for (const TCHAR* Path : Paths)
		{
			UStaticMesh* Mesh = TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(Path)).LoadSynchronous();
			if (UStaticMeshComponent* Part = Mesh ? SpawnTimedMesh(Mesh, FTransform(Where), Life) : nullptr)
			{
				Part->SetCastShadow(false);
				Part->SetReceivesDecals(false);
				Lance.BirdParts.Add(Part);
			}
		}
		if (Lance.BirdParts.Num() != Paths.Num())
		{
			EndLanceBird(Lance, false);
			Lance.Bird = 0;
			return;
		}
	}
	// 등장 이펙트 시안(FSummon): 매가 나타나는 자리에 한 번
	Lance.BirdSummon = GetFSummon();
	switch (Lance.BirdSummon)
	{
	case 1:
		SpawnBurstLater(DecoySpawn, Where, LanceBirdSummonDecoyScale, 0.0f, Lance.Direction.Rotation());
		break;
	case 2:
		SpawnBurstLater(LanceFlash, Where, LanceBirdSummonFlashScale, 0.0f);
		SpawnBurstLater(IceShards, Where, LanceBirdSummonShardScale, 0.0f, Lance.Direction.Rotation());
		SpawnFrostNova(FVector(Where.X, Where.Y, LanceFloorZ), LanceBirdSummonRingRadius, 1, LanceBirdSummonRingSeconds,
			NovaRingMaterial.LoadSynchronous(), LanceBirdSummonRingStrength);
		break;
	case 3:
		SpawnBurstLater(CryoInitialBlast, Where, LanceBirdSummonBlastScale, 0.0f);
		break;
	case 4:
		// 짙어지기: 판·메시마다 재질 사본을 만들어 LanceBirdTick이 Fade를 0 → 1로(그림 매는 이미 사본)
		for (const TWeakObjectPtr<UStaticMeshComponent>& Part : Lance.BirdParts)
		{
			if (Part.IsValid() && !Cast<UMaterialInstanceDynamic>(Part->GetMaterial(0)))
			{
				Part->CreateDynamicMaterialInstance(0);
			}
		}
		break;
	default:
		break;
	}
	// 나는 쪽 이펙트 시안(FTrail): 빛줄기 판(자리·길이는 LanceBirdTick) · 얼음 반짝이
	const int32 Trail = GetFTrail();
	UMaterialInterface* Streak = CutMarkMaterial.LoadSynchronous();
	for (int32 Slot = 0; Streak && PlaneMesh && Slot < 3; ++Slot)
	{
		if (!(Trail & (Slot == 0 ? 1 : 2)))
		{
			continue;
		}
		if (UStaticMeshComponent* Mark = SpawnTimedMesh(PlaneMesh, FTransform(Where), Life))
		{
			UMaterialInstanceDynamic* Dynamic = UMaterialInstanceDynamic::Create(Streak, Mark);
			Dynamic->SetScalarParameterValue(TEXT("Reveal"), 1.1f);
			Mark->SetMaterial(0, Dynamic);
			Mark->SetCastShadow(false);
			Mark->SetReceivesDecals(false);
			Lance.BirdStreaks[Slot] = Mark;
			Lance.BirdStreakMaterials[Slot] = Dynamic;
		}
	}
	UParticleSystem* Sparks = (Trail & 4) ? TSoftObjectPtr<UParticleSystem>(FSoftObjectPath(BirdSparkPath)).LoadSynchronous() : nullptr;
	if (Sparks && !Lance.BirdParts.IsEmpty())
	{
		if (UParticleSystemComponent* Glitter = UGameplayStatics::SpawnEmitterAttached(Sparks, Lance.BirdParts[0].Get(), NAME_None,
			FVector::ZeroVector, FRotator::ZeroRotator, EAttachLocation::KeepRelativeOffset, false))
		{
			// 붙인 판·메시의 배율을 물려받지 않게(70차 D 꼬리가 연기 기둥이 된 까닭)
			Glitter->SetUsingAbsoluteScale(true);
			Glitter->SetWorldScale3D(FVector(LanceBirdSparkScale));
			OwnedEffects.Add(Glitter);
			Lance.BirdSparks = Glitter;
		}
	}
	LanceBirdTick(Lance, Origin, Lance.BirdBorn);
}

void UAuroraSkillComponent::LanceBirdTick(FAuroraLance& Lance, const FVector& Where, double Now)
{
	if (Lance.Bird == 0 || Lance.BirdParts.IsEmpty())
	{
		return;
	}
	const float Age = static_cast<float>(Now - Lance.BirdBorn);
	// 나타날 때 0.5배에서 커진다
	// 등장 시안 4는 더 작게·옅게 시작해 LanceBirdRevealSeconds 동안 짙어지며 커진다
	const bool bReveal = Lance.BirdSummon == 4;
	const float Grow = bReveal ? FMath::Lerp(LanceBirdRevealFrom, 1.0f, FMath::Clamp(Age / LanceBirdRevealSeconds, 0.0f, 1.0f)) :
		FMath::Lerp(0.5f, 1.0f, FMath::Clamp(Age / LanceBirdGrowSeconds, 0.0f, 1.0f));
	if (bReveal && Age <= LanceBirdRevealSeconds + 0.05f)
	{
		for (const TWeakObjectPtr<UStaticMeshComponent>& Part : Lance.BirdParts)
		{
			if (UMaterialInstanceDynamic* Dynamic = Part.IsValid() ? Cast<UMaterialInstanceDynamic>(Part->GetMaterial(0)) : nullptr)
			{
				Dynamic->SetScalarParameterValue(TEXT("Fade"), FMath::Clamp(Age / LanceBirdRevealSeconds, 0.0f, 1.0f));
			}
		}
	}
	const FVector Body(Where.X, Where.Y, LanceFloorZ + LanceBirdHeight);
	// 판의 그림 위쪽(-Y) = 머리 = 나는 쪽, 앞면(Z)이 위
	const auto Lay = [](const FVector& Forward)
	{
		return FRotationMatrix::MakeFromYZ(-Forward, FVector::UpVector).ToQuat();
	};
	// 나는 쪽 빛줄기: 몸(또는 날개 끝) 뒤로 지나온 길이만큼(최대 길이까지) 눕힌 판 — 그림 위쪽(-Y)이 나는 쪽
	const FVector Across(-Lance.Direction.Y, Lance.Direction.X, 0.0f);
	for (int32 Slot = 0; Slot < 3; ++Slot)
	{
		UStaticMeshComponent* Mark = Lance.BirdStreaks[Slot].Get();
		if (!Mark)
		{
			continue;
		}
		const bool bTip = Slot != 0;
		const float Length = FMath::Max(FMath::Min(Lance.Travel, bTip ? LanceBirdTipLength : LanceBirdStreakLength), 1.0f);
		const FVector Root = Body + (bTip ? Across * (Slot == 1 ? LanceBirdTipSide : -LanceBirdTipSide) - Lance.Direction * LanceBirdTipBack :
			FVector(0.0f, 0.0f, -4.0f));
		Mark->SetWorldTransform(FTransform(Lay(Lance.Direction), Root - Lance.Direction * (Length * 0.5f),
			FVector((bTip ? LanceBirdTipWidth : LanceBirdStreakWidth) / 100.0f, Length / 100.0f, 1.0f)));
	}
	if (const FFlyerCard* Flyer = FindFlyerCard(Lance.Bird))
	{
		UStaticMeshComponent* Card = Lance.BirdParts[0].Get();
		if (!Card)
		{
			return;
		}
		// 눈꽃 표창은 판 앞면 축으로 돈다(셋이 같은 자세로 돌지 않게 60도 × 박자 어긋남에서 시작)
		const FQuat Turn(FVector::UpVector, FMath::DegreesToRadians(Flyer->Spin * Age + 60.0f * Lance.BirdPhase));
		Card->SetWorldLocationAndRotation(Body - Lance.Direction * Flyer->Ahead, Flyer->Spin != 0.0f ? Turn * Lay(Lance.Direction) : Lay(Lance.Direction));
		const float Size = Grow * ((Lance.BirdLook & 8) ? LanceBirdGlowSize : 1.0f);
		Card->SetWorldScale3D(FVector(Flyer->Width / 100.0f * Size, Flyer->Length / 100.0f * Size, 1.0f));
		const int32 Frames = Flyer->Columns * Flyer->Rows;
		UMaterialInstanceDynamic* Dynamic = Lance.BirdMaterial.Get();
		float FrameU = 0.0f;
		float FrameV = 0.0f;
		if (Dynamic && Frames > 1)
		{
			// 박자 어긋남 = 한 바퀴(Frames장)의 BirdPhase만큼
			const int32 Frame = FMath::FloorToInt32((Age + Lance.BirdPhase * Frames / Flyer->FrameRate) * Flyer->FrameRate) % Frames;
			FrameU = (Frame % Flyer->Columns) / static_cast<float>(Flyer->Columns);
			FrameV = (Frame / Flyer->Columns) / static_cast<float>(Flyer->Rows);
			Dynamic->SetScalarParameterValue(TEXT("FrameU"), FrameU);
			Dynamic->SetScalarParameterValue(TEXT("FrameV"), FrameV);
		}
		if ((Lance.BirdLook & 1) && Dynamic && Now > Lance.BirdBorn)
		{
			// 잔상: 장면마다 지금 자리·날갯짓 장 그대로 어둡게 한 장 남기고, IceLanceTick이 창 잔상처럼 줄여 지운다
			if (UStaticMeshComponent* Ghost = SpawnTimedMesh(PlaneMesh, Card->GetComponentTransform(), LanceBirdGhostSeconds + 0.1f))
			{
				UMaterialInstanceDynamic* Dim = UMaterialInstanceDynamic::Create(Dynamic->Parent, Ghost);
				Dim->SetScalarParameterValue(TEXT("FrameU"), FrameU);
				Dim->SetScalarParameterValue(TEXT("FrameV"), FrameV);
				Dim->SetScalarParameterValue(TEXT("Brightness"), Dynamic->K2_GetScalarParameterValue(TEXT("Brightness")) * LanceBirdGhostBrightness);
				Ghost->SetMaterial(0, Dim);
				Ghost->SetCastShadow(false);
				Ghost->SetReceivesDecals(false);
				LanceGhosts.Add({Ghost, Now, Card->GetComponentScale(), LanceBirdGhostSeconds});
			}
		}
		return;
	}
	if (Lance.Bird == 4)
	{
		// 얼음 용: 머리가 지나간 길(떠난 자리에서 잰 거리 S)을 마디가 그대로 따라온다 — 길은 나는 쪽으로 곧게 가며 옆으로 물결친다
		const FVector Right(-Lance.Direction.Y, Lance.Direction.X, 0.0f);
		const FVector Start = Body - Lance.Direction * Lance.Travel;
		const float Wave = 2.0f * PI / DragonWave;
		const auto Place = [&](UStaticMeshComponent* Part, float S, float Width, float Length)
		{
			if (!Part)
			{
				return;
			}
			if (S < 0.0f)
			{
				Part->SetVisibility(false);
				return;
			}
			const float Ramp = FMath::Clamp(S / DragonSwayRamp, 0.0f, 1.0f);
			const float Side = DragonSway * Ramp * FMath::Sin(Wave * S);
			const float Slope = DragonSway * (Ramp * Wave * FMath::Cos(Wave * S) + (S < DragonSwayRamp ? FMath::Sin(Wave * S) / DragonSwayRamp : 0.0f));
			const FVector Forward = (Lance.Direction + Right * Slope).GetSafeNormal();
			Part->SetVisibility(true);
			Part->SetWorldLocationAndRotation(Start + Lance.Direction * S + Right * Side, Lay(Forward));
			Part->SetWorldScale3D(FVector(Width / 100.0f, Length / 100.0f, 1.0f));
		};
		Place(Lance.BirdParts[0].Get(), Lance.Travel, DragonHeadCard * Grow, DragonHeadCard * Grow);
		// 첫 마디 앞 끝이 머리 판 아래 끝(목)에 조금 겹치게
		const float LinkLength = DragonSpacing * DragonLinkOverlap;
		float S = Lance.Travel - DragonHeadCard * 0.5f - DragonSpacing * 0.45f;
		for (int32 Link = 0; Link < DragonLinks; ++Link, S -= DragonSpacing)
		{
			Place(Lance.BirdParts[1 + Link].Get(), S, DragonTube(Link) * DragonCardPerTube, LinkLength);
		}
		// 꼬리 끝: 마지막 마디 뒤 끝에 조금 겹치게
		const float TailS = S + DragonSpacing - LinkLength * 0.5f - DragonTailLength * 0.5f + 1.5f;
		Place(Lance.BirdParts[DragonLinks + 1].Get(), TailS, DragonTubeTo * DragonCardPerTube, DragonTailLength);
		return;
	}
	if (Lance.Bird == 9)
	{
		// 입체 매: 안쪽 날개를 어깨에서, 바깥쪽을 손목에서 X축으로 돌린다 — 바깥쪽이 조금 늦게 더 크게 꺾여 채찍처럼 퍼덕이고,
		// 내리칠 때 몸이 조금 뜬다
		const float Beat = 2.0f * PI * Age * Hawk3DFlapRate;
		const float Inner = FMath::DegreesToRadians(Hawk3DFlapMid + Hawk3DFlapAmp * FMath::Sin(Beat));
		const float Outer = FMath::DegreesToRadians(Hawk3DHandAmp * FMath::Sin(Beat - Hawk3DHandLag));
		const FTransform Frame(Lance.Direction.ToOrientationQuat(), Body + FVector(0.0f, 0.0f, 4.0f * FMath::Cos(Beat)), FVector(Grow));
		if (UStaticMeshComponent* Torso = Lance.BirdParts[0].Get())
		{
			Torso->SetWorldTransform(Frame);
		}
		for (int32 Side = 0; Side < 2; ++Side)
		{
			const float Sign = Side == 0 ? 1.0f : -1.0f;
			const FTransform Shoulder(FQuat(FVector::ForwardVector, Inner * Sign), FVector(Hawk3DShoulder.X, Hawk3DShoulder.Y * Sign, 0.0f));
			const FTransform InnerWorld = Shoulder * Frame;
			if (UStaticMeshComponent* Wing = Lance.BirdParts[1 + Side].Get())
			{
				Wing->SetWorldTransform(InnerWorld);
			}
			if (UStaticMeshComponent* Hand = Lance.BirdParts[3 + Side].Get())
			{
				Hand->SetWorldTransform(FTransform(FQuat(FVector::ForwardVector, Outer * Sign), FVector(Hawk3DWrist.X, Hawk3DWrist.Y * Sign, 0.0f)) * InnerWorld);
			}
		}
		return;
	}
	// 결정 매: 날개를 어깨에서 X축으로 돌려 퍼덕이고, 내리칠 때 몸이 조금 뜬다
	const float Cycle = 2.0f * PI * (Age * LanceBirdFlapRate + Lance.BirdPhase);
	const float Flap = FMath::DegreesToRadians(LanceBirdFlapMid + LanceBirdFlapAmp * FMath::Sin(Cycle));
	const float Scale = LanceBirdCrystalScale * Grow;
	const FQuat Facing = Lance.Direction.ToOrientationQuat();
	const FVector Lifted = Body + FVector(0.0f, 0.0f, 6.0f * FMath::Cos(Cycle) * Scale);
	const FTransform Frame(Facing, Lifted, FVector(Scale));
	UStaticMeshComponent* Parts[4] = {Lance.BirdParts[0].Get(), Lance.BirdParts[1].Get(), Lance.BirdParts[2].Get(), Lance.BirdParts[3].Get()};
	if (Parts[0])
	{
		Parts[0]->SetWorldTransform(Frame);
	}
	for (int32 Side = 0; Side < 2; ++Side)
	{
		if (UStaticMeshComponent* Wing = Parts[1 + Side])
		{
			const float Sign = Side == 0 ? 1.0f : -1.0f;
			const FTransform Local(FQuat(FVector::ForwardVector, Flap * Sign), FVector(LanceBirdShoulderX, LanceBirdShoulderY * Sign, LanceBirdShoulderZ));
			Wing->SetWorldTransform(Local * Frame);
		}
	}
	if (Parts[3])
	{
		Parts[3]->SetWorldTransform(FTransform(FQuat::Identity, FVector(LanceBirdTailX, 0.0f, 0.0f)) * Frame);
	}
}

void UAuroraSkillComponent::EndLanceBird(const FAuroraLance& Lance, bool bShatter)
{
	ReleaseOwnedEffect(Lance.BirdFlakes.Get());
	ReleaseOwnedEffect(Lance.BirdSparks.Get());
	// 빛줄기는 그 자리에 남아 칼자국처럼 빠르게 사라진다(BladeTick)
	const double Now = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0;
	for (int32 Index = 0; Index < 3; ++Index)
	{
		if (UStaticMeshComponent* Mark = Lance.BirdStreaks[Index].Get())
		{
			CutMarks.Add({Mark, Lance.BirdStreakMaterials[Index], Now - 1.0, Now});
			if (GetWorld() && !GetWorld()->GetTimerManager().IsTimerActive(BladeTimer))
			{
				GetWorld()->GetTimerManager().SetTimer(BladeTimer, this, &UAuroraSkillComponent::BladeTick, 1.0f / 60.0f, true);
			}
		}
	}
	// 부서질 자리: 판 하나 시안은 나는 자리(봉황은 판 가운데보다 앞선 어깨) 한 곳, 용은 머리와 몇 마디마다, 결정 매는 몸
	TArray<FVector> Bursts;
	const FFlyerCard* Flyer = FindFlyerCard(Lance.Bird);
	for (int32 Index = 0; Index < Lance.BirdParts.Num(); ++Index)
	{
		UStaticMeshComponent* Part = Lance.BirdParts[Index].Get();
		if (!Part)
		{
			continue;
		}
		const bool bDragonBurst = Lance.Bird == 4 && Part->IsVisible() && Index % DragonShardEvery == 0;
		if (bShatter && (Bursts.IsEmpty() && Lance.Bird != 4 || bDragonBurst))
		{
			Bursts.Add(Part->GetComponentLocation() + (Flyer ? Lance.Direction * Flyer->Ahead : FVector::ZeroVector));
		}
		RemoveTimedMesh(Part, nullptr);
	}
	for (const FVector& Where : Bursts)
	{
		// 그 자리에서 얼음 조각으로 부서진다(분신과 같은 파편, 뜬 높이에서 아래로)
		SpawnShatterShards(FVector(Where.X, Where.Y, LanceFloorZ + LanceBirdHeight * 0.5f), LanceBirdHeight * 0.6f,
			Lance.Bird == 4 ? DragonShards : LanceBirdShards, Lance.Bird == 4 ? 260.0f : 320.0f, Lance.Bird == 4 ? 160.0f : 200.0f,
			Lance.Bird == 4 ? 0.7f : 1.0f);
	}
}
