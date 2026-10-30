// A 얼음 갑옷 시안(10-21 「A는 바닥에 조그마한 얼음 오브젝트 깔리는 거 말고 다른 이펙트 뭐 없을까? 시안 만들어 줘 · 육각형 대신에 어떤 무늬
// 그리면 좋을까? 아님 그냥 아무것도 그리지 말까? 이것도 시안 여러 개」). 보호막 크기·시간·피해 줄임은 그대로, 켜질 때 발밑 이펙트와
// 보호막 무늬만 고른다.
#include "AuroraSkillComponent.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Particles/ParticleSystemComponent.h"
#include "TopDownCombatCharacter.h"

namespace
{
	// 10-25 「2로 가되 원 크기를 좀 더 줄여 줘 · A는 금 갈라짐으로 가자」 — 둘 다 2
	TAutoConsoleVariable<int32> CVarAuroraArmorCast(
		TEXT("Aurora.FX.ACast"), 2,
		TEXT("Ice armor cast effect at her feet: 0 six small ice crystals rising and crumbling, 1 none, 2 a frost shockwave ring spreading out (default), 3 a frost whirlwind wrapping round her body, 4 frost spreading over the floor under her, 5 a puff of cold breath bursting from her body."));
	TAutoConsoleVariable<int32> CVarAuroraArmorPattern(
		TEXT("Aurora.FX.APattern"), 2,
		TEXT("Ice armor shell pattern: 0 honeycomb ice plates, 1 none - only the broken rim glow, 2 jagged frost cracks (default), 3 feathery hoarfrost fronds, 4 thin snowflakes, 5 tall ice shards rising up the sides."));

	// 2~5: aurora_shell_patterns.py가 그린 무늬를 지금 보호막과 같은 재질·옅기로(aurora_frost_materials_build.py shelldrafts)
	const TCHAR* const ShellPatterns[] = {
		TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_IceArmor_Crack.M_Aurora_IceArmor_Crack"),
		TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_IceArmor_Fern.M_Aurora_IceArmor_Fern"),
		TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_IceArmor_Flake.M_Aurora_IceArmor_Flake"),
		TEXT("/Game/TopDown/Characters/Aurora/FX/M_Aurora_IceArmor_Shard.M_Aurora_IceArmor_Shard")};

	// 발밑 이펙트 크기: 2 충격파 고리(반경 · 퍼지는 시간) · 3 회오리(E 회오리 1.2배 → 몸만 감싸게) · 4 서리 번짐(반경 · 남는 시간 · 나타남 ·
	// 사라짐) · 5 냉기 숨결(몸 가운데에서)
	// 고리 반경은 처음 260 → 10-25 「원 크기를 좀 더 줄여 줘」로 180 → 이어서 「원 좀 더 좁게」로 130 → 「원 더 작게」로 90
	constexpr float ArmorNovaRadius = 90.0f;
	constexpr float ArmorNovaSeconds = 0.35f;
	constexpr float ArmorSwirlScale = 0.35f;
	constexpr float ArmorSwirlSeconds = 0.75f;
	constexpr float ArmorFrostRadius = 170.0f;
	constexpr float ArmorFrostSeconds = 1.2f;
	constexpr float ArmorFrostFadeIn = 0.12f;
	constexpr float ArmorFrostFadeOut = 0.6f;
	constexpr float ArmorPuffScale = 0.7f;
}

void UAuroraSkillComponent::SpawnArmorCast(const FVector& Feet)
{
	const int32 Cast = CVarAuroraArmorCast.GetValueOnGameThread();
	switch (Cast)
	{
	case 1:
		break;
	case 2:
		SpawnFrostNova(Feet, ArmorNovaRadius, 1, ArmorNovaSeconds, NovaRingMaterial.LoadSynchronous());
		break;
	case 3:
		// E 회오리(시전 이펙트)를 작게 — 몸을 휘감고 지운다(끄기만 하면 조각이 수명대로 떠 있는다)
		if (UParticleSystemComponent* Swirl = SpawnOwnedEffect(Skills[EAuroraSkill::Hoarfrost].CastEffect, Feet + FVector(0.0f, 0.0f, 30.0f)))
		{
			Swirl->SetWorldScale3D(FVector(ArmorSwirlScale));
			DestroyEffectLater(Swirl, ArmorSwirlSeconds);
		}
		break;
	case 4:
		SpawnFloorDecal(FrostTrailMaterial.LoadSynchronous(), Feet, ArmorFrostRadius, ArmorFrostSeconds, ArmorFrostFadeIn, ArmorFrostFadeOut);
		break;
	case 5:
		SpawnBurstLater(IceFrostPuff, Character.IsValid() ? Character->GetActorLocation() : Feet, ArmorPuffScale, 0.0f);
		break;
	default:
		// 0: 칼이 땅에 꽂힌 자리에서 작은 얼음 결정이 솟았다 부서지며 보호막이 얼어붙는다(10-18부터).
		for (int32 Index = 0; Index < ArmorCrystalCount; ++Index)
		{
			const float Angle = 2.0f * PI * Index / ArmorCrystalCount;
			const FVector Outward(FMath::Cos(Angle), FMath::Sin(Angle), 0.0f);
			if (UParticleSystemComponent* Crystal = SpawnOwnedEffect(FreezeSegment, Feet + Outward * ArmorCrystalRadius, Outward.Rotation()))
			{
				Crystal->SetWorldScale3D(FVector(ArmorCrystalScale));
				ReleaseLater(Crystal, ArmorCrystalSeconds, FreezeSegmentCrumble);
			}
		}
		break;
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_ARMOR cast=%d pattern=%d"), Cast, CVarAuroraArmorPattern.GetValueOnGameThread());
}

UMaterialInterface* UAuroraSkillComponent::GetArmorShellMaterial(UStaticMeshComponent* Shell)
{
	const int32 Pattern = CVarAuroraArmorPattern.GetValueOnGameThread();
	if (Pattern >= 2 && Pattern < 2 + static_cast<int32>(UE_ARRAY_COUNT(ShellPatterns)))
	{
		if (UMaterialInterface* Material = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(ShellPatterns[Pattern - 2])).LoadSynchronous())
		{
			return Material;
		}
	}
	UMaterialInterface* Honeycomb = ShellMaterial.LoadSynchronous();
	if (Pattern == 1 && Honeycomb)
	{
		// 무늬 없음: 같은 재질에서 칸(판·테두리·옅은 테두리)만 끈다 — 끊긴 가장자리 빛만 남는다
		UMaterialInstanceDynamic* Bare = UMaterialInstanceDynamic::Create(Honeycomb, Shell);
		for (const TCHAR* Name : {TEXT("PlateOpacity"), TEXT("BorderOpacity"), TEXT("GhostOpacity")})
		{
			Bare->SetScalarParameterValue(Name, 0.0f);
		}
		return Bare;
	}
	return Honeycomb;
}
