// D 고드름 비(10-25 「고드름 비 가자. 하늘에서 날카로운 얼음송곳들이 일정하게 대각선으로 떨어지는 거 어때」). 그 전 시안(원 안에서 송곳이
// 솟는 범위 얼음송곳)은 「너무 아쉬운데, 제로베이스부터」로 지웠다 — 엔진 원뿔이 짧고 굵어 싸 보였다.
// 첫 판(팩 고드름 메시 다섯 — 판·가시 공·뭉툭한 조각)은 「아냐. 참고 영상(메이플 블리자드류)으로, 송곳처럼 엄청 길고 뾰족한 느낌」으로
// 다시 짰다: 영상의 세 장면 = ① 하늘에 얼음 물결 고리가 뜨고 ② 거기서 아주 길고 가는 얼음창이 비스듬히 내리꽂히고 ③ 꽂힌 자리에서 큰 얼음
// 결정이 솟으며 하얗게 터진다. 창은 엔진 원뿔(끝이 정확히 뾰족함)을 아주 길고 가늘게 늘여 빛나는 얼음 재질(분신과 같은 M_Aurora_CloneIce),
// 고리는 착지 충격파 판(SpawnFrostNova)을 하늘 높이에, 솟는 결정은 E 둘레와 같은 팩 이펙트(P_Aurora_Freeze_Segment).
// 칼을 땅에 꽂는 동작·멈칫은 그대로.
// 이어서 「다 보완해 줘」(내 평가 셋): ① 하늘 고리가 굵고 하얀 표시 원 6~7개로 겹쳐 보임 → 매끈한 고리 둘(물결)을 옅게·작게 ·
// ② 창이 모두 같은 하얀 막대라 빛줄기·바늘 같음 → 창마다 길이·굵기를 달리하고 꼬리(F 창과 같은 Leap_Trail)를 붙임 ·
// ③ 꽂힐 때가 제일 조용함 → 결정 크게 + 푸른 섬광 + 처음 맞힌 한 번만 짧게 멈칫.
#include "AuroraSkillComponent.h"

#include "Components/DecalComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "KwangTrainingDummy.h"
#include "Particles/ParticleSystemComponent.h"
#include "TimerManager.h"
#include "TopDownCombatCharacter.h"

namespace
{
	TAutoConsoleVariable<int32> CVarAuroraIcicleRain(
		TEXT("Aurora.FX.DRain"), 1,
		TEXT("Ice Rupture: 1 icicle rain - frost rings open in the sky and very long, sharp ice spears plunge from them at a slant into a circle where she aims, ice crystals bursting up where they strike (default), 0 the old line of ice rocks forward."));
	// 10-25 「D는 방향은 맞는 것 같은데 퀄리티가 너무 안 좋은데 더 올릴 수는 없나」 — 촬영(59차) 다섯 중 4(다 같이 부서짐)가 참고 영상의
	// 얼음 무더기에 가장 가까워 고르기 전까지 4. 2의 바닥 서리 원은 하얀 판처럼 떠 보였고, 1의 석상 재질은 멀리서 빛나는 얼음과 거의 같았다.
	TAutoConsoleVariable<int32> CVarAuroraIcicleLook(
		TEXT("Aurora.FX.DLook"), 4,
		TEXT("Icicle rain quality draft bitmask: 1 the spears in the frosted ice-statue material instead of plain glowing white, 2 the ground frosts over under the circle and cracks in a star where each spear strikes, 4 the spears stay planted until the last one lands, then all shatter together with a burst in the middle (default). 0 = none."));
	// 10-26 「D는 저 꽂히는 얼음 오브젝트가 너무 별로인 것 같은데 다른 거 없어?」 — 엔진 원뿔이 가늘어 테두리 흰빛만 남아 하얀 막대로 보였다.
	// 1~4는 aurora_spear_art.py가 그린 각진 얼음 결정 창(육각 · 고르지 않은 면 · 뒤 끝이 부러진 듯 평평)과 곁가지 달린 다발
	// (aurora_frost_materials_build.py speardrafts). 팩 고드름 메시는 첫 판에서 판·가시 공·뭉툭한 조각이라 뺐고, 뮤리엘·백작 창은 납작한 판이었다.
	// 촬영(70차) 다섯 중 1이 꽂힌 자리 결정 무더기와 같은 푸른 얼음으로 읽혀 고르기 전까지 1. 2·3(고드름 벽 재질)은 회보라로 탁했고
	// 4는 점무늬로 지저분했다. → 10-26 「니 권장대로」(참고 영상의 창은 가는 흰 빛줄기)로 다시 0.
	TAutoConsoleVariable<int32> CVarAuroraIcicleSpear(
		TEXT("Aurora.FX.DSpear"), 0,
		TEXT("Icicle rain spear draft: 0 the long engine cone in glowing white ice (default), 1 a faceted ice crystal in deep glowing blue ice, 2 the same crystal in Aurora's icicle-wall ice (streaked, catching the light), 3 a crystal with two short crystals branching off its back in the icicle-wall ice, 4 the crystal in the frost-shield ice chunk material."));
	struct FRainSpear
	{
		const TCHAR* Mesh;
		const TCHAR* Material;
		float Thick;
	};
	// 원뿔 굵기 16의 배율 — 결정은 끝까지 가늘어지는 길이가 길어 같은 굵기면 바늘처럼 보인다
	const FRainSpear RainSpears[] = {
		{TEXT("/Game/TopDown/Characters/Aurora/FX/Meshes/SM_Aurora_IceSpear.SM_Aurora_IceSpear"),
			TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_SpearIce.M_Aurora_SpearIce"), 1.6f},
		{TEXT("/Game/TopDown/Characters/Aurora/FX/Meshes/SM_Aurora_IceSpear.SM_Aurora_IceSpear"),
			TEXT("/Game/ParagonAurora/FX/Materials/Aurora/M_Aurora_Spike_Spline.M_Aurora_Spike_Spline"), 1.6f},
		{TEXT("/Game/TopDown/Characters/Aurora/FX/Meshes/SM_Aurora_IceSpearCluster.SM_Aurora_IceSpearCluster"),
			TEXT("/Game/ParagonAurora/FX/Materials/Aurora/M_Aurora_Spike_Spline.M_Aurora_Spike_Spline"), 1.6f},
		{TEXT("/Game/TopDown/Characters/Aurora/FX/Meshes/SM_Aurora_IceSpear.SM_Aurora_IceSpear"),
			TEXT("/Game/ParagonAurora/FX/Materials/Aurora/M_Aurora_Chunk_FresFade_Inst.M_Aurora_Chunk_FresFade_Inst"), 1.6f},
	};
	// 「이펙트를 톤 맞춰서 새로 제작하는 건 불가능한가」 시험: 팩 결정(Freeze_Segment)의 입자 재질을 빛나는 흰 얼음으로 바꿔 끼운다
	// (입자 판 모양·움직임은 팩 그대로, 색만 우리 톤). 0 = 팩 색 그대로(기본)
	TAutoConsoleVariable<int32> CVarAuroraIcicleTint(
		TEXT("Aurora.FX.DTint"), 0,
		TEXT("Icicle rain crystal colour test: 0 the pack's blue crystals (default), 1 the same crystals re-skinned in Aurora's glowing white ice, 2 re-skinned in the deep blue spear ice."));
	constexpr int32 RainTintSlots = 8;
	// 10-26 「저 얼음 오브젝트 말고 다르게 표현할 방법은 없나」(결정은 크기·색을 바꿔도 두 번 다 별로): 1 = 솟는 결정·튀는 조각(물체) 없이
	// 꽂힌 자리 바닥이 가운데부터 얼어붙어 퍼진다(M_Aurora_FrostBurst, aurora_frost_materials_build.py frostburst). 0 = 결정(기본)
	TAutoConsoleVariable<int32> CVarAuroraIcicleMark(
		TEXT("Aurora.FX.DMark"), 0,
		TEXT("Icicle rain strike mark: 0 a pack ice crystal bursts up with flying shards (default), 1 no object - the floor freezes over from the strike point outward in a ragged frost patch."));
	const TCHAR* const RainFrostBurstPath = TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_FrostBurst.M_Aurora_FrostBurst");
	// 1: 서리 자국 반경 · 번지는 시간 · 남는 시간(4면 마지막 창이 박힐 때까지 더) · 사라짐
	constexpr float RainMarkRadius = 90.0f;
	constexpr float RainMarkSweep = 0.18f;
	constexpr float RainMarkSeconds = 1.2f;
	constexpr float RainMarkFadeOut = 0.6f;

	// 결정 창 메시의 반 크기(굵기 10 · 길이 100, 가운데가 원점) — 다발은 곁가지로 상자가 넓어도 본 결정 기준으로 늘인다
	const FVector RainCrystalExtent(5.0f, 5.0f, 50.0f);

	// 4: 마지막 창이 박히고 함께 부서지기까지 · 가운데 터짐 크기
	constexpr float RainFinaleHold = 0.35f;
	constexpr float RainFinaleShock = 1.2f;
	// 2: 바닥 서리 원(반경 배율 · 나타남 · 사라짐) · 창마다 별 모양 금(반경 · 그어지는 시간 · 남는 시간 · 사라짐)
	constexpr float RainFrostScale = 1.15f;
	constexpr float RainFrostFadeIn = 0.15f;
	constexpr float RainFrostFadeOut = 0.6f;
	constexpr float RainCrackRadius = 90.0f;
	constexpr float RainCrackSweep = 0.06f;
	constexpr float RainCrackSeconds = 1.6f;
	constexpr float RainCrackFadeOut = 0.5f;

	// 원 반경 · 겨눌 수 있는 거리(발밑에서) · 창 수 · 사이 시간(창 수 × 사이 = 내리는 시간) · 고리가 뜨고 창이 떨어지기 시작할 때까지 ·
	// 떨어지기 시작하는 거리(비스듬히 위) · 떨어지는 시간 · 수직에서 기운 각(도, 오로라 → 겨눈 쪽으로)
	// 10-26 「D는 니 권장대로 바꿔 봐」(참고 영상 대비 — 영상은 꽂힐 때마다 캐릭터 2~3배 높이의 크고 투명한 흰·하늘색 결정이 솟고 흰 섬광·
	// 안개가 크며 창은 가는 흰 빛줄기, 지금은 키보다 낮은 짙은 파랑 결정 12개가 깔려 뭉개짐): 창 12 → 6(사이 0.08 → 0.12) · 결정 0.9 → 1.8 ·
	// 섬광 0.9 → 2 · 꽂힐 때마다 흰 터짐(RainBlastScale) · 창은 다시 가는 흰 원뿔(DSpear 0, 굵기 16 → 10)
	constexpr float RainRadius = 260.0f;
	constexpr float RainReach = 850.0f;
	constexpr int32 RainCount = 6;
	constexpr float RainInterval = 0.12f;
	constexpr float RainRingLead = 0.12f;
	// 첫 판 1200은 위에서 보는 카메라 화면 위로 고리가 벗어나 안 보였다 → 650
	constexpr float RainDropDistance = 650.0f;
	constexpr float RainFallSeconds = 0.14f;
	constexpr float RainSlantDegrees = 25.0f;
	// 창: 길이 · 밑동 굵기(끝은 원뿔이라 뾰족) · 바닥에 박히는 깊이 · 박혀 있는 시간
	constexpr float RainSpearLength = 420.0f;
	constexpr float RainSpearWidth = 10.0f;
	constexpr float RainEmbed = 60.0f;
	constexpr float RainStuckSeconds = 0.5f;
	// 하늘 고리: 반경 · 퍼지는 시간 · 진하기(첫 판 거친 고리 1배는 굵고 하얀 표시 원처럼 보였다 → 매끈한 고리 둘을 옅게)
	constexpr float RainRingRadius = 100.0f;
	constexpr float RainRingSeconds = 0.4f;
	// 0.45는 화면에서 거의 그대로 하얗게 보여(빛이 넘쳐 번짐) 0.2
	constexpr float RainRingStrength = 0.2f;
	// 창마다 길이·굵기 배율 범위
	constexpr float RainLengthMin = 0.75f;
	constexpr float RainLengthMax = 1.25f;
	constexpr float RainWidthMin = 0.8f;
	constexpr float RainWidthMax = 1.2f;
	// 꽂힌 자리: 솟는 얼음 결정 크기 · 서 있는 시간(그 뒤 부서짐) · 튀는 얼음 조각 크기. 흰 서리 터짐(IceFrostPuff)은 첫 촬영에서 파란
	// 그물 공처럼 보여 뺐다
	constexpr float RainCrystalScale = 1.8f;
	constexpr float RainCrystalSeconds = 0.9f;
	constexpr float RainShardScale = 0.5f;
	// 꽂힌 자리 푸른 섬광 크기 · 흰 터짐(궁극기 첫 폭발) 크기 · 처음 맞힌 창 한 번만 멈칫하는 시간
	constexpr float RainFlashScale = 2.0f;
	constexpr float RainBlastScale = 0.45f;
	constexpr float RainHitStopSeconds = 0.05f;
	// 창 하나 피해(맞을 때마다) · 맞는 반경 · 감속
	constexpr float RainHitDamage = 12.0f;
	constexpr float RainHitRadius = 100.0f;
	constexpr float RainSlowSeconds = 1.0f;
	// 떨어지는 차례: 해바라기 배치(고르게 퍼진 자리)를 RainStride칸씩 건너 고른다 — 한쪽으로 몰리지 않고 원 전체에 고르게 내린다
	constexpr int32 RainStride = 5;

	// AuroraSkillComponent.cpp의 SetStatus와 같다(그쪽은 그 파일 안에서만 보이고, 한 덩어리로 묶어 빌드할 때 겹치지 않게 이름을 달리 씀)
	void SetRainStatus(AActor* Target, FName Status, float Seconds)
	{
		if (AKwangTrainingDummy* Dummy = Cast<AKwangTrainingDummy>(Target))
		{
			Dummy->SetCombatStatus(Status, Seconds);
		}
	}
}

int32 UAuroraSkillComponent::GetDRain() const
{
	return CVarAuroraIcicleRain.GetValueOnGameThread();
}

void UAuroraSkillComponent::ExecuteIcicleRain()
{
	if (!GetWorld() || !Character.IsValid())
	{
		return;
	}
	// 겨눈 자리(RainReach까지 당김) 바닥
	const FVector Feet = GetFeetLocation();
	FVector Offset = (ActiveAim - Feet) * FVector(1.0f, 1.0f, 0.0f);
	if (Offset.Size() > RainReach)
	{
		Offset = Offset.GetSafeNormal() * RainReach;
	}
	FVector Toward = Offset.GetSafeNormal();
	if (Toward.IsNearlyZero())
	{
		Toward = Character->GetActorForwardVector().GetSafeNormal2D();
	}
	const FVector Above(Feet.X + Offset.X, Feet.Y + Offset.Y, Character->GetActorLocation().Z);
	const FVector Center(Above.X, Above.Y, FindFloorZ(Above, Feet.Z));
	// 모두 같은 기울기: 오로라 쪽 하늘에서 겨눈 쪽으로 비스듬히
	const float Slant = FMath::DegreesToRadians(RainSlantDegrees);
	IcicleFall = (Toward * FMath::Sin(Slant) - FVector::UpVector * FMath::Cos(Slant)).GetSafeNormal();
	IcicleHits.Reset();
	// 새 시안(Aurora.FX.DFresh, AuroraSkillComponentDFresh.cpp)이면 같은 자리·기울기로 그쪽이 맡는다
	if (const int32 Fresh = GetDFresh(); Fresh >= 1 && ExecuteDFresh(Fresh, Center, Toward))
	{
		return;
	}
	RainLook = CVarAuroraIcicleLook.GetValueOnGameThread();
	RainCenter = Center;
	// 창 모양 시안 — 못 불러오면 엔진 원뿔
	const int32 Spear = CVarAuroraIcicleSpear.GetValueOnGameThread();
	RainSpearMesh = nullptr;
	RainSpearMaterial = nullptr;
	RainSpearExtent = BladeMesh ? BladeMesh->GetBounds().BoxExtent : FVector(50.0f);
	RainSpearThick = 1.0f;
	if (Spear >= 1 && Spear <= static_cast<int32>(UE_ARRAY_COUNT(RainSpears)))
	{
		const FRainSpear& Choice = RainSpears[Spear - 1];
		UStaticMesh* Mesh = TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(Choice.Mesh)).LoadSynchronous();
		UMaterialInterface* Material = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(Choice.Material)).LoadSynchronous();
		if (Mesh && Material)
		{
			RainSpearMesh = Mesh;
			RainSpearMaterial = Material;
			RainSpearExtent = RainCrystalExtent;
			RainSpearThick = Choice.Thick;
		}
	}
	// 4: 마지막 창이 박힌 뒤 RainFinaleHold에 다 같이 부서진다
	RainEndsAt = GetWorld()->GetTimeSeconds() + RainInterval * (RainCount - 1) + RainRingLead + RainFallSeconds + RainFinaleHold;
	if (RainLook & 2)
	{
		SpawnFloorDecal(FrostTrailMaterial.LoadSynchronous(), Center, RainRadius * RainFrostScale,
			static_cast<float>(RainEndsAt - GetWorld()->GetTimeSeconds()) + RainFrostFadeOut, RainFrostFadeIn, RainFrostFadeOut);
	}
	if (RainLook & 4)
	{
		GetWorld()->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, [this]()
		{
			SpawnBurstLater(IceShock, RainCenter, RainFinaleShock, 0.0f);
			if (CryoExplode)
			{
				UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), CryoExplode, RainCenter, FRotator::ZeroRotator, FVector(0.6f));
			}
		}), static_cast<float>(RainEndsAt - GetWorld()->GetTimeSeconds()), false);
	}
	UMaterialInterface* Ring = NovaRingMaterial.LoadSynchronous();
	const TWeakObjectPtr<UMaterialInterface> WeakRing = Ring;
	for (int32 Index = 0; Index < RainCount; ++Index)
	{
		// 해바라기 배치의 (Index × RainStride) % RainCount번째 자리
		const int32 Seat = (Index * RainStride) % RainCount;
		const float Reach = RainRadius * 0.9f * FMath::Sqrt((Seat + 0.5f) / RainCount);
		const float Angle = Seat * PI * (3.0f - FMath::Sqrt(5.0f));
		const FVector Landing = Center + FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.0f) * Reach;
		const float Delay = RainInterval * Index;
		// ① 창이 나올 하늘 자리에 얼음 물결 고리가 먼저 뜬다
		const FVector Sky = Landing - IcicleFall * RainDropDistance;
		GetWorld()->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, [this, Sky, WeakRing]()
		{
			SpawnFrostNova(Sky, RainRingRadius, 2, RainRingSeconds, WeakRing.Get(), RainRingStrength);
		}), FMath::Max(Delay, 0.01f), false);
		// ② 고리가 뜬 뒤 창이 떨어진다
		GetWorld()->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateUObject(this, &UAuroraSkillComponent::DropIcicle,
			Landing), Delay + RainRingLead, false);
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_RAIN start count=%d at=%s fall=%s spear=%d crystal=%d"), RainCount, *Center.ToCompactString(),
		*IcicleFall.ToCompactString(), Spear, RainSpearMesh.IsValid());
}

void UAuroraSkillComponent::DropIcicle(FVector Landing)
{
	if (!BladeMesh || !GetWorld())
	{
		return;
	}
	FAuroraIcicle Icicle;
	Icicle.Landing = Landing;
	Icicle.Born = GetWorld()->GetTimeSeconds();
	Icicle.StuckUntil = (RainLook & 4) ? RainEndsAt : Icicle.Born + RainFallSeconds + RainStuckSeconds;
	Icicle.Length = FMath::FRandRange(RainLengthMin, RainLengthMax);
	Icicle.Width = FMath::FRandRange(RainWidthMin, RainWidthMax);
	UStaticMesh* SpearMesh = RainSpearMesh.IsValid() ? RainSpearMesh.Get() : BladeMesh.Get();
	UStaticMeshComponent* Component = SpawnTimedMesh(SpearMesh, FTransform(Landing - IcicleFall * RainDropDistance),
		static_cast<float>(Icicle.StuckUntil - Icicle.Born) + 0.5f);
	if (!Component)
	{
		return;
	}
	// 창 모양 시안(DSpear)의 재질 · 아니면 1: 얼음 석상 재질(분신 석상과 같은 — 반투명 얼음 결) · 아니면 빛나는 얼음
	UMaterialInterface* SpearMaterial = RainSpearMesh.IsValid() ? RainSpearMaterial.Get() : nullptr;
	if (UMaterialInterface* Ice = SpearMaterial ? SpearMaterial : (RainLook & 1) ? BladeMaterial.Get() : CloneIceMaterial.LoadSynchronous())
	{
		Component->SetMaterial(0, Ice);
	}
	Component->SetReceivesDecals(false);
	// 떨어지는 동안 꼬리(F 창과 같은 이펙트) — 박히면 IcicleRainTick이 끈다
	if (LanceTrail)
	{
		if (UParticleSystemComponent* Trail = UGameplayStatics::SpawnEmitterAttached(LanceTrail, Component, NAME_None,
			FVector::ZeroVector, FRotator::ZeroRotator, EAttachLocation::KeepRelativeOffset, false))
		{
			// 꼬리는 창 배율을 물려받는다 — 결정 창은 메시가 원뿔보다 작아 배율이 커서(굵기 16배) 꼬리가 흰 연기 기둥이 됐다(70차 촬영).
			// 원뿔일 때와 같은 크기가 되게 되돌린다.
			const FVector Cone = BladeMesh->GetBounds().BoxExtent;
			Trail->SetRelativeScale3D(FVector(RainSpearExtent.X / FMath::Max(Cone.X, 1.0f) / RainSpearThick,
				RainSpearExtent.Y / FMath::Max(Cone.Y, 1.0f) / RainSpearThick, RainSpearExtent.Z / FMath::Max(Cone.Z, 1.0f)));
			OwnedEffects.Add(Trail);
			Icicle.Trail = Trail;
		}
	}
	Icicle.Mesh = Component;
	RainIcicles.Add(Icicle);
	if (!GetWorld()->GetTimerManager().IsTimerActive(IcicleTimer))
	{
		GetWorld()->GetTimerManager().SetTimer(IcicleTimer, this, &UAuroraSkillComponent::IcicleRainTick, 1.0f / 60.0f, true);
	}
	IcicleRainTick();
}

void UAuroraSkillComponent::IcicleRainTick()
{
	UWorld* World = GetWorld();
	if (!World || !BladeMesh)
	{
		return;
	}
	// 엔진 원뿔(가운데가 원점, 끝 +Z)을 길이 RainSpearLength · 굵기 RainSpearWidth로 — 끝이 떨어지는 쪽을 본다(결정 창도 같은 짜임)
	const FVector Extent = RainSpearExtent;
	const FQuat Facing = FRotationMatrix::MakeFromZ(IcicleFall).ToQuat();
	const double Now = World->GetTimeSeconds();
	for (int32 Index = RainIcicles.Num() - 1; Index >= 0; --Index)
	{
		FAuroraIcicle& Icicle = RainIcicles[Index];
		UStaticMeshComponent* Component = Icicle.Mesh.Get();
		if (!Component || Now >= Icicle.StuckUntil)
		{
			if (Component)
			{
				// 박혀 있던 창이 부서진다
				SpawnShatterShards(Component->Bounds.Origin, 60.0f, 5, 240.0f, 180.0f, 0.7f);
				ReleaseOwnedEffect(Icicle.Trail.Get());
				RemoveTimedMesh(Component, nullptr);
			}
			RainIcicles.RemoveAt(Index);
			continue;
		}
		const float Width = RainSpearWidth * RainSpearThick * Icicle.Width;
		const float Length = RainSpearLength * Icicle.Length;
		const FVector Scale(Width / FMath::Max(2.0f * Extent.X, 1.0f), Width / FMath::Max(2.0f * Extent.Y, 1.0f),
			Length / FMath::Max(2.0f * Extent.Z, 1.0f));
		const FVector TipOffset = IcicleFall * (Length * 0.5f);
		// 끝이 Landing 아래 RainEmbed까지 곧게 떨어진다
		const FVector Ground = Icicle.Landing + IcicleFall * RainEmbed;
		const float Alpha = FMath::Clamp(static_cast<float>(Now - Icicle.Born) / RainFallSeconds, 0.0f, 1.0f);
		const FVector TipAt = FMath::Lerp(Ground - IcicleFall * RainDropDistance, Ground, Alpha);
		Component->SetWorldTransform(FTransform(Facing, TipAt - TipOffset, Scale));
		if (Alpha >= 1.0f && !Icicle.bLanded)
		{
			Icicle.bLanded = true;
			ReleaseOwnedEffect(Icicle.Trail.Get());
			SpawnBurstLater(LanceFlash, Icicle.Landing + FVector(0.0f, 0.0f, 30.0f), RainFlashScale, 0.0f);
			SpawnBurstLater(CryoInitialBlast, Icicle.Landing, RainBlastScale, 0.0f);
			// ③ 꽂힌 자리에서 얼음 결정이 솟고(E 둘레와 같은 이펙트) 얼음 조각이 튄다 · DMark 1이면 대신 바닥이 얼어붙는다
			const bool bFrostMark = CVarAuroraIcicleMark.GetValueOnGameThread() == 1;
			if (bFrostMark)
			{
				SweepFloorDecal(TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(RainFrostBurstPath)).LoadSynchronous(), Icicle.Landing,
					FRotator(0.0f, FMath::FRandRange(0.0f, 360.0f), 0.0f).Vector(), RainMarkRadius,
					RainMarkSeconds + ((RainLook & 4) ? FMath::Max(static_cast<float>(RainEndsAt - Now), 0.0f) : 0.0f), RainMarkSweep, -1.0f,
					RainMarkFadeOut);
			}
			else if (UParticleSystemComponent* Crystal = SpawnOwnedEffect(FreezeSegment, Icicle.Landing,
				FRotator(0.0f, FMath::FRandRange(0.0f, 360.0f), 0.0f)))
			{
				Crystal->SetWorldScale3D(FVector(RainCrystalScale));
				// 색 시험(DTint): 입자 재질 칸을 모두 바꿔 끼운다
				const int32 Tint = CVarAuroraIcicleTint.GetValueOnGameThread();
				UMaterialInterface* Skin = Tint == 1 ? CloneIceMaterial.LoadSynchronous() : Tint == 2 ?
					TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(RainSpears[0].Material)).LoadSynchronous() : nullptr;
				for (int32 Slot = 0; Skin && Slot < RainTintSlots; ++Slot)
				{
					Crystal->SetMaterial(Slot, Skin);
				}
				ReleaseLater(Crystal, (RainLook & 4) ? FMath::Max(static_cast<float>(RainEndsAt - Now), 0.05f) : RainCrystalSeconds, FreezeSegmentCrumble);
			}
			if (!bFrostMark)
			{
				SpawnBurstLater(IceShards, Icicle.Landing, RainShardScale, 0.0f, IcicleFall.Rotation());
			}
			if (RainLook & 2)
			{
				if (UDecalComponent* Crack = SweepFloorDecal(LanceImpactCrackMaterial.LoadSynchronous(), Icicle.Landing, IcicleFall.GetSafeNormal2D(),
					RainCrackRadius, RainCrackSeconds, RainCrackSweep, -1.0f, RainCrackFadeOut))
				{
					Crack->SetSortOrder(1);
				}
			}
			TArray<AActor*> Targets;
			GatherTargets(Icicle.Landing, RainHitRadius, Targets);
			AController* Instigator = Character.IsValid() ? Character->GetController() : nullptr;
			for (AActor* Target : Targets)
			{
				// 처음 맞힌 한 번만 짧게 멈칫(창마다 멈추면 1초 내내 끊긴다)
				if (IcicleHits.IsEmpty())
				{
					BeginHitStop(Target, RainHitStopSeconds);
				}
				IcicleHits.Add(Target);
				if (Target->CanBeDamaged())
				{
					FHitResult Hit(Target, nullptr, Target->GetActorLocation(), IcicleFall);
					UGameplayStatics::ApplyPointDamage(Target, RainHitDamage, IcicleFall, Hit, Instigator, GetOwner(), nullptr);
				}
				SetRainStatus(Target, TEXT("SLOW"), RainSlowSeconds);
			}
		}
	}
	if (RainIcicles.IsEmpty())
	{
		World->GetTimerManager().ClearTimer(IcicleTimer);
		UE_LOG(LogTemp, Display, TEXT("AURORA_RAIN end targets=%d"), IcicleHits.Num());
	}
}
