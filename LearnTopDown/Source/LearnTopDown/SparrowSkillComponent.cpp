#include "SparrowSkillComponent.h"
#include "SparrowShotWave.h"
#include "SparrowBackstepEcho.h"
#include "SparrowGoldRoll.h"
#include "SparrowHolyBow.h"
#include "SparrowEDesignVisual.h"
#include "SparrowAscendedShotFX.h"
#include "SparrowAscension.h"
#include "SparrowFlameStudies.h"
#include "SparrowArsenalStudyFX.h"

#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Distributions/DistributionFloatConstant.h"
#include "Distributions/DistributionVectorConstant.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/ProjectileMovementComponent.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "InputCoreTypes.h"
#include "KwangTrainingDummy.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "Particles/ParticleEmitter.h"
#include "Particles/ParticleLODLevel.h"
#include "ParticleEmitterInstances.h"
#include "Particles/ParticleModuleRequired.h"
#include "Particles/TypeData/ParticleModuleTypeDataMesh.h"
#include "Particles/Color/ParticleModuleColor.h"
#include "Particles/Color/ParticleModuleColorScaleOverLife.h"
#include "Particles/Material/ParticleModuleMeshMaterial.h"
#include "Particles/Location/ParticleModuleLocationPrimitiveCylinder.h"
#include "Particles/Spawn/ParticleModuleSpawn.h"
#include "SparrowArrow.h"
#include "TopDownCombatCharacter.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	constexpr float HailDuration = 4.0f;
	constexpr float HailRecovery = 0.36f;
	constexpr float HailIndicatorFadeSeconds = 0.4f;
	constexpr float HailInterval = 0.5f;
	constexpr float HailRadius = 300.0f;
	constexpr float AscendedHailRadius = 750.0f;
	constexpr float HailHeight = 200.0f;
	constexpr float ChargeDuration = 0.5f;
	constexpr float HolyPreparationDuration = 0.32f;
	constexpr float HolyReleaseDuration = 0.16f;
	constexpr float HolyTailDuration = 0.12f;
	constexpr float HolyTotalDuration = HolyPreparationDuration + HolyReleaseDuration + HolyTailDuration;
	constexpr float HailVisualDensity = 2.56f / 3.0f;
	constexpr int32 PiercingShotCount = 4;
	constexpr float PiercingShotInterval = 0.18f;
	constexpr float PiercingReleaseOffset = 0.09f;
	constexpr float PiercingFinisherDelay = 0.42f;
	constexpr float PiercingRecovery = ChargeDuration + PiercingShotCount * PiercingShotInterval + 0.06f;
	constexpr int32 MultishotWaveCount = 10;
	constexpr int32 MultishotArrowsPerWave = 31;
	constexpr float MultishotWaveInterval = 0.13f;
	constexpr float MultishotPreparation = 0.12f;
	constexpr float MultishotTail = 0.22f;
	constexpr float MultishotDuration = MultishotPreparation + MultishotWaveCount * MultishotWaveInterval + MultishotTail;
	constexpr float MultishotHalfAngle = 39.0f;
	constexpr float RelentlessDuration = 5.0f;
	constexpr int32 RelentlessLimit = 10;
	constexpr int32 HailPulseCount = 8;
	constexpr int32 MaxHailZones = 8;
	TAutoConsoleVariable<int32> CVarSparrowHailDiagnostics(
		TEXT("Sparrow.Hail.Diagnostics"), 0,
		TEXT("Read-only: log the actual Q particle template and resolved render materials."));
	constexpr float RelentlessDamagePerStack = 0.0175f;
	TAutoConsoleVariable<int32> CVarSparrowIgnoreCooldowns(
		TEXT("Sparrow.Skills.IgnoreCooldowns"), 1,
		TEXT("Practice mode: 1 ignores Sparrow skill cooldowns; 0 restores configured cooldowns."));
	bool IsLivingTarget(const AActor* Target)
	{
		if (!IsValid(Target) || Target->IsActorBeingDestroyed())
		{
			return false;
		}
		const AKwangTrainingDummy* Dummy = Cast<AKwangTrainingDummy>(Target);
		return !Dummy || Dummy->IsAlive();
	}

	UParticleSystem* CreateRapidBowEffect(UParticleSystem* Source, UObject* Outer)
	{
		if (!Source || !Outer) { return nullptr; }
		UParticleSystem* Copy = DuplicateObject<UParticleSystem>(Source, Outer,
			MakeUniqueObjectName(Outer, UParticleSystem::StaticClass(), TEXT("SparrowRapidBow")));
		if (!Copy) { return nullptr; }
		Copy->SetFlags(RF_Transient);
		Copy->ClearFlags(RF_Public | RF_Standalone);
		// 원본 불꽃 메시와 잔불만 사용한다. 긴 보라 리본과 뼈 전체를 덮는 decal은 제외한다.
		Copy->Emitters.RemoveAll([](const TObjectPtr<UParticleEmitter>& Emitter)
		{
			return !Emitter || (Emitter->GetEmitterName() != TEXT("BowFlames") && Emitter->GetEmitterName() != TEXT("Embers"));
		});
		for (UParticleEmitter* Emitter : Copy->Emitters)
		{
			if (!Emitter->IsIn(Copy)) { return nullptr; }
			Emitter->UpdateModuleLists();
		}
		return Copy->Emitters.IsEmpty() ? nullptr : Copy;
	}
}

USparrowSkillComponent::USparrowSkillComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.bStartWithTickEnabled = false;
	const auto FindAnimation = [](const TCHAR* Name)
	{
		const FString Path = FString::Printf(TEXT("/Game/ParagonSparrow/Characters/Heroes/Sparrow/Animations/%s.%s"), Name, Name);
		ConstructorHelpers::FObjectFinder<UAnimSequence> Asset(*Path);
		return Asset.Object;
	};
	const auto FindEffect = [](const TCHAR* Ability, const TCHAR* Name)
	{
		const FString Path = FString::Printf(TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/%s/FX/%s.%s"), Ability, Name, Name);
		ConstructorHelpers::FObjectFinder<UParticleSystem> Asset(*Path);
		return Asset.Object;
	};
	Skills.SetNum(4);
	const TCHAR* Names[] = {TEXT("HailOfArrows"), TEXT("PiercingShot"), TEXT("HolyArrow"), TEXT("InnerFire")};
	const float Damage[] = {40.0f, 35.0f, 60.0f, 60.0f};
	const float Cooldown[] = {8.0f, 6.0f, 8.0f, 20.0f};
	const float Range[] = {1400.0f, 2500.0f, 1800.0f, 1800.0f};
	// 원본 DissolveAmount 커브의 Q 0.237초 / RMB_Fire 0.118413초를 시연 발사 시점에 맞춘다.
	const float Action[] = {0.24f, ChargeDuration + PiercingReleaseOffset, HolyPreparationDuration, 0.12f};
	const float Recovery[] = {HailRecovery, PiercingRecovery, HolyTotalDuration, MultishotDuration};
	// HP 100 허수아비에서 판정과 누적 효과를 확인하는 시연값이며 원작 밸런스 수치는 아니다.
	for (int32 Index = 0; Index < Skills.Num(); ++Index)
	{
		FSparrowSkillDefinition& Skill = Skills[Index];
		Skill.Name = Names[Index];
		Skill.Damage = Damage[Index];
		Skill.Cooldown = Cooldown[Index];
		Skill.Range = Range[Index];
		Skill.ActionTime = Action[Index];
		Skill.RecoveryTime = Recovery[Index];
		Skill.CastSound = nullptr;
	}
	Skills[0].Animation = FindAnimation(TEXT("Q_Ability"));
	Skills[0].CastEffect = FindEffect(TEXT("RainOfArrows"), TEXT("P_RainArrowsTarget"));
	Skills[0].ImpactEffect = FindEffect(TEXT("RainOfArrows"), TEXT("P_RainofArrows"));
	Skills[1].Animation = FindAnimation(TEXT("RMB_Drawback"));
	Skills[1].CastEffect = FindEffect(TEXT("DrawABead"), TEXT("P_Sparrow_RMB"));
	Skills[1].ImpactEffect = FindEffect(TEXT("Ultimate"), TEXT("P_Sparrow_UltHit"));
	// 후기 원작 E의 누적 피해는 유지하고, 입력 슬롯에는 단발 황금 활을 제공한다.
	Skills[2].Animation = FindAnimation(TEXT("Primary_Fire_Fast"));
	Skills[3].Animation = FindAnimation(TEXT("R_Ability_Med_Fire"));
	Skills[3].CastEffect = FindEffect(TEXT("Ultimate"), TEXT("P_SparrowBuff"));
	Skills[3].ImpactEffect = FindEffect(TEXT("Ultimate"), TEXT("P_Sparrow_UltHit"));
	ChargeLoop = FindAnimation(TEXT("RMB_Loop"));
	ChargeFire = FindAnimation(TEXT("RMB_Fire"));
	PrimaryTrail = FindEffect(TEXT("Primary"), TEXT("P_Sparrow_PrimaryAttack"));
	PrimaryHit = FindEffect(TEXT("Primary"), TEXT("P_Sparrow_Primary_Ballistic_HitPlayer"));
	PrimaryWorldHit = FindEffect(TEXT("Primary"), TEXT("P_Sparrow_Primary_Ballistic_HitWorld"));
	PrimaryMuzzle = FindEffect(TEXT("Primary"), TEXT("P_SparrowPrimaryMuzzleFlash"));
	UltimateTrail = FindEffect(TEXT("Ultimate"), TEXT("P_Sparrow_UltArrow"));
	UltimateWorldHit = FindEffect(TEXT("Ultimate"), TEXT("P_Sparrow_UltHitWorld"));
	HailProjectile = FindEffect(TEXT("RainOfArrows"), TEXT("P_RainofArrowsProj"));
	InnerFireEffect = FindEffect(TEXT("Ultimate"), TEXT("P_SparrowBuff"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> RangePlane(TEXT("/Engine/BasicShapes/Plane.Plane"));
	HailRangeMesh = RangePlane.Object;
	HailRangeMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowHailBoundary.M_SparrowHailBoundary")));
	InitializeExtraSkills();
}

void USparrowSkillComponent::BeginPlay()
{
	Super::BeginPlay();
	Character = Cast<ATopDownCombatCharacter>(GetOwner());
	const USkeletalMesh* Mesh = Character.IsValid() && Character->GetMesh() ? Character->GetMesh()->GetSkeletalMeshAsset() : nullptr;
	if (!Mesh || Skills.Num() != 4 || !ChargeLoop || !ChargeFire)
	{
		return;
	}
	// 구형 E 배열을 저장한 BP만 새 능동 정의로 이행한다. Q/W/R의 저장된 설정은 보존한다.
	if (Skills[2].Name == TEXT("Relentless") && !Skills[2].Animation)
	{
		Skills[2] = GetDefault<USparrowSkillComponent>()->Skills[2];
	}
	// 발사 뒤 화살을 다시 꺼내는 원본 후반 대신, 짧게 자세를 풀고 이동으로 복귀한다.
	if (Skills[0].Name == TEXT("HailOfArrows") && FMath::IsNearlyEqual(Skills[0].RecoveryTime, 1.60f))
	{
		Skills[0].RecoveryTime = HailRecovery;
	}
	// BP가 저장한 이전 시연 기본 타이밍만 이행한다. 별도로 조정한 수치는 유지한다.
	if (Skills[1].Name == TEXT("PiercingShot"))
	{
		if (FMath::IsNearlyEqual(Skills[1].ActionTime, 1.12f) || FMath::IsNearlyEqual(Skills[1].ActionTime, .62f))
		{
			Skills[1].ActionTime = ChargeDuration + PiercingReleaseOffset;
		}
		if (FMath::IsNearlyEqual(Skills[1].RecoveryTime, 2.75f) || FMath::IsNearlyEqual(Skills[1].RecoveryTime, 2.25f) ||
			FMath::IsNearlyEqual(Skills[1].RecoveryTime, .72f))
		{
			Skills[1].RecoveryTime = PiercingRecovery;
		}
	}
	if (Skills[2].Name == TEXT("RapidShot") || Skills[2].Name == TEXT("HolyArrow"))
	{
		Skills[2].Name = TEXT("HolyArrow");
		if (FMath::IsNearlyEqual(Skills[2].ActionTime, 0.12f)) { Skills[2].ActionTime = HolyPreparationDuration; }
		if (FMath::IsNearlyEqual(Skills[2].RecoveryTime, 0.84f) || FMath::IsNearlyEqual(Skills[2].RecoveryTime, 1.20f) ||
			FMath::IsNearlyEqual(Skills[2].RecoveryTime, 1.40f))
		{
			Skills[2].RecoveryTime = HolyTotalDuration;
		}
	}
	// 10초 강화 평타를 저장한 BP도 즉시 발사형 R로 이행한다. S가 참조하는 원본 애니메이션은 유지한다.
	if (Skills[3].Name == TEXT("InnerFire"))
	{
		Skills[3].Name = TEXT("GoldenMultishot");
		Skills[3].Damage = 60.0f;
		Skills[3].ActionTime = MultishotPreparation;
		Skills[3].RecoveryTime = MultishotDuration;
	}
	if (Skills[3].Name == TEXT("GoldenMultishot") && FMath::IsNearlyEqual(Skills[3].RecoveryTime, .94f))
	{
		Skills[3].RecoveryTime = MultishotDuration;
	}
	SkillMontages.SetNum(4);
	for (int32 Slot = 0; Slot < Skills.Num(); ++Slot)
	{
		if (IsSkillPassive(Slot))
		{
			continue;
		}
		if (!Skills[Slot].Animation || Skills[Slot].Animation->GetSkeleton() != Mesh->GetSkeleton())
		{
			SkillMontages.Reset();
			return;
		}
		SkillMontages[Slot] = Slot == 1 ? CreateChargeMontage() : Slot == 2 ? CreateHolyShotMontage() :
			Slot == 3 ? CreateMultishotMontage() :
			UAnimMontage::CreateSlotAnimationAsDynamicMontage(Skills[Slot].Animation, FullBodySlot, 0.06f, 0.12f, 1.0f, 1);
		if (!SkillMontages[Slot])
		{
			SkillMontages.Reset();
			return;
		}
	}
	AscendedChargeMontage = CreateChargeMontage(true);
	RuntimeHailEffect = CreateRuntimeHailEffect();
	RuntimeRapidBowEffect = CreateRapidBowEffect(InnerFireEffect, this);
	CreateExtraMontages();
	bEnabled = true;
}

UParticleSystem* USparrowSkillComponent::CreateRuntimeHailEffect()
{
	UParticleSystem* Source = Skills[0].ImpactEffect;
	// 조사한 기본/Rogue 화살비에만 적용한다. 다른 FX 템플릿은 유지한다.
	if (!Source || (Source->GetPathName() !=
		TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/RainOfArrows/FX/P_RainofArrows.P_RainofArrows") &&
		Source->GetPathName() != TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Skins/Rogue/P_RainofArrows.P_RainofArrows")))
	{
		return nullptr;
	}
	UParticleSystem* Runtime = DuplicateObject<UParticleSystem>(Source, this,
		MakeUniqueObjectName(this, UParticleSystem::StaticClass(), TEXT("P_RainofArrows_SparrowRuntime")));
	if (!Runtime)
	{
		return nullptr;
	}
	Runtime->SetFlags(RF_Transient);
	Runtime->ClearFlags(RF_Public | RF_Standalone);
	UMaterialInterface* GoldRain = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/Salvo20261026/M_QArrowRainGold.M_QArrowRainGold"));
	// 원본 Trails의 수명 후반 보라색과 보라 충격파만 복제본에서 교체한다. 원본 에셋과 알파 곡선은 보존한다.
	Runtime->Emitters.RemoveAll([](const TObjectPtr<UParticleEmitter>& Emitter)
	{
		return Emitter && Emitter->GetEmitterName() == TEXT("Shockwave_SmallPurple");
	});
	TSet<UParticleModuleColor*> RetintedStartColors;
	for (UParticleEmitter* Emitter : Runtime->Emitters)
	{
		if (!Emitter) { continue; }
		const FName Name = Emitter->GetEmitterName();
		const bool bKnownPurpleLayer = Name == TEXT("PurpleFallingMist") ||
			Name == TEXT("SparksTrailing") || Name == TEXT("Line Burst");
		if (!bKnownPurpleLayer && Name != TEXT("Hit")) { continue; }
		for (UParticleLODLevel* LOD : Emitter->LODLevels)
		{
			if (!LOD) { continue; }
			for (UParticleModule* Module : LOD->Modules)
			{
				// 실제 Q의 자홍색은 별도 층의 StartColor에도 있다. 밝기와 알파/개수/수명은 유지한다.
				if (UParticleModuleColor* Color = bKnownPurpleLayer ? Cast<UParticleModuleColor>(Module) : nullptr)
				{
					if (RetintedStartColors.Contains(Color)) { continue; }
					const FVector Original = Color->StartColor.GetValue(0.0f);
					// 같은 이름의 황금 스파크와 비활성 Wisps는 변경하지 않는다.
					if (Original.X > Original.Y * 1.5f && Original.Z > Original.Y * 1.5f)
					{
						if (!Color->IsIn(Runtime)) { return nullptr; }
						const FVector Luminance(.2126f, .7152f, .0722f);
						const FVector GoldHue(1.0f, .65f, .10f);
						UDistributionVectorConstant* Gold = NewObject<UDistributionVectorConstant>(Color, NAME_None, RF_Transient);
						Gold->Constant = GoldHue * (FVector::DotProduct(Original, Luminance) / FVector::DotProduct(GoldHue, Luminance));
						Gold->bCanBeBaked = false;
						Gold->bIsDirty = false;
						FRawDistributionVector Tint;
						Tint.Distribution = Gold;
						Color->StartColor = MoveTemp(Tint);
						RetintedStartColors.Add(Color);
						UE_LOG(LogTemp, Display, TEXT("Sparrow runtime hail gold: emitter=%s old=%s new=%s"),
							*Name.ToString(), *Original.ToString(), *Gold->Constant.ToString());
					}
				}
				// 낙하 후 Hit 메시도 같은 원본 화살 재질을 사용하므로 동일한 금색 복제본을 적용한다.
				if (GoldRain && Name == TEXT("Hit"))
				{
					if (UParticleModuleMeshMaterial* MeshMaterial = Cast<UParticleModuleMeshMaterial>(Module))
					{
						if (!MeshMaterial->IsIn(Runtime)) { return nullptr; }
						for (TObjectPtr<UMaterialInterface>& Material : MeshMaterial->MeshMaterials)
						{
							if (Material && Material->GetName() == TEXT("M_ArrowRain")) { Material = GoldRain; }
						}
					}
				}
			}
		}
	}
	for (UParticleEmitter* Emitter : Runtime->Emitters)
	{
		if (!Emitter || Emitter->GetEmitterName() != TEXT("Trails")) { continue; }
		for (UParticleLODLevel* LOD : Emitter->LODLevels)
		{
			if (!LOD) { continue; }
			for (UParticleModule* Module : LOD->Modules)
			{
				if (UParticleModuleColorScaleOverLife* Color = Cast<UParticleModuleColorScaleOverLife>(Module))
				{
					if (!Color->IsIn(Runtime)) { return nullptr; }
					UDistributionVectorConstant* Gold = NewObject<UDistributionVectorConstant>(Color, NAME_None, RF_Transient);
					Gold->Constant = FVector(2.0f, 1.19f, .20f);
					Gold->bCanBeBaked = false;
					Gold->bIsDirty = false;
					FRawDistributionVector Tint;
					Tint.Distribution = Gold;
					Color->ColorScaleOverLife = MoveTemp(Tint);
				}
			}
		}
		Emitter->UpdateModuleLists();
	}
	TSet<UParticleModuleLocationPrimitiveCylinder*> ChangedModules;
	TSet<UParticleModuleSpawn*> ChangedSpawnModules;
	int32 AdjustedEmitters = 0;
	for (UParticleEmitter* Emitter : Runtime->Emitters)
	{
		if (!Emitter || (Emitter->GetEmitterName() != TEXT("Falling") &&
			Emitter->GetEmitterName() != TEXT("FallingLingerArrows")))
		{
			continue;
		}
		if (!Emitter->IsIn(Runtime))
		{
			return nullptr;
		}
		const float Radius = Emitter->GetEmitterName() == TEXT("Falling") ? HailRadius : HailRadius * 0.8f;
		bool bAdjusted = false;
		for (UParticleLODLevel* LOD : Emitter->LODLevels)
		{
			if (!LOD)
			{
				continue;
			}
			// 낙하 화살의 메시 재질에도 원본 보라색이 있으므로 색 출력만 바꾼 전용 복제본을 연결한다.
			if (GoldRain)
			{
				for (UParticleModule* Module : LOD->Modules)
				{
					if (UParticleModuleMeshMaterial* MeshMaterial = Cast<UParticleModuleMeshMaterial>(Module))
					{
						if (!MeshMaterial->IsIn(Runtime)) { return nullptr; }
						for (TObjectPtr<UMaterialInterface>& Material : MeshMaterial->MeshMaterials)
						{
							if (Material && Material->GetName() == TEXT("M_ArrowRain")) { Material = GoldRain; }
						}
					}
				}
			}
			UParticleModuleSpawn* Spawn = LOD->SpawnModule;
			if (Spawn && !ChangedSpawnModules.Contains(Spawn))
			{
				if (!Spawn->IsIn(Runtime))
				{
					return nullptr;
				}
				float MinScale = 0.0f;
				float MaxScale = 0.0f;
				Spawn->RateScale.GetOutRange(MinScale, MaxScale);
				// 원본 Rate 시간 곡선은 유지하고 상수 배율만 늘린다. 미확인 가변 배율은 덮어쓰지 않는다.
				if (!FMath::IsNearlyEqual(MinScale, MaxScale))
				{
					UE_LOG(LogTemp, Warning, TEXT("Sparrow hail density: unexpected varying spawn scale %s"), *Emitter->GetEmitterName().ToString());
					return nullptr;
				}
				UDistributionFloatConstant* Scale = NewObject<UDistributionFloatConstant>(Spawn, NAME_None, RF_Transient);
				Scale->Constant = MaxScale * HailVisualDensity;
				Scale->bCanBeBaked = false;
				Scale->bIsDirty = false;
				FRawDistributionFloat FreshScale;
				FreshScale.Distribution = Scale;
				Spawn->RateScale = MoveTemp(FreshScale);
				for (FParticleBurst& Burst : Spawn->BurstList)
				{
					Burst.Count = FMath::Max(0, FMath::RoundToInt(Burst.Count * HailVisualDensity));
					if (Burst.CountLow >= 0)
					{
						Burst.CountLow = FMath::Max(0, FMath::RoundToInt(Burst.CountLow * HailVisualDensity));
					}
				}
				ChangedSpawnModules.Add(Spawn);
				UE_LOG(LogTemp, Display, TEXT("Sparrow hail density: emitter=%s scale=%.2f->%.2f bursts=%d"),
					*Emitter->GetEmitterName().ToString(), MaxScale, Spawn->RateScale.GetValue(0.0f), Spawn->BurstList.Num());
			}
			for (UParticleModule* Module : LOD->Modules)
			{
				UParticleModuleLocationPrimitiveCylinder* Cylinder = Cast<UParticleModuleLocationPrimitiveCylinder>(Module);
				if (!Cylinder)
				{
					continue;
				}
				// 공유 원본 모듈을 수정하지 않도록 실제 복제본의 소유 관계도 검사한다.
				if (!Cylinder->IsIn(Runtime))
				{
					return nullptr;
				}
				bAdjusted = true;
				if (ChangedModules.Contains(Cylinder))
				{
					continue;
				}
				UDistributionFloatConstant* Constant = NewObject<UDistributionFloatConstant>(Cylinder, NAME_None, RF_Transient);
				Constant->Constant = Radius;
				Constant->bCanBeBaked = false;
				Constant->bIsDirty = false;
				// Initialize()는 에디터 전용이다. 새 raw 분포의 빈 LUT는 Game에서도 Constant를 직접 평가한다.
				FRawDistributionFloat FreshRadius;
				FreshRadius.Distribution = Constant;
				Cylinder->StartRadius = MoveTemp(FreshRadius);
				const float EffectiveRadius = Cylinder->StartRadius.GetValue(0.0f);
				if (!FMath::IsNearlyEqual(EffectiveRadius, Radius))
				{
					return nullptr;
				}
				UE_LOG(LogTemp, Display, TEXT("Sparrow runtime hail: emitter=%s radius=%.2f baked_lookup=%d"),
					*Emitter->GetEmitterName().ToString(), EffectiveRadius, Cylinder->StartRadius.HasLookupTable(false));
				ChangedModules.Add(Cylinder);
			}
		}
		if (bAdjusted)
		{
			++AdjustedEmitters;
		}
	}
	if (AdjustedEmitters != 2)
	{
		UE_LOG(LogTemp, Warning, TEXT("Sparrow runtime hail: expected two original falling emitters, found %d"), AdjustedEmitters);
		return nullptr;
	}
	// DuplicateTransient인 Spawn/Update 목록을 복구한다. System의 UpdateAllModuleLists는 에디터 전용이다.
	for (UParticleEmitter* Emitter : Runtime->Emitters)
	{
		if (Emitter)
		{
			if (!Emitter->IsIn(Runtime))
			{
				return nullptr;
			}
			Emitter->UpdateModuleLists();
		}
	}
	return Runtime;
}

UAnimMontage* USparrowSkillComponent::CreateChargeMontage(bool bFinisher)
{
	UAnimSequence* Draw = Skills[1].Animation;
	if (!Draw || !ChargeLoop || !ChargeFire || Draw->GetSkeleton() != ChargeLoop->GetSkeleton() ||
		Draw->GetSkeleton() != ChargeFire->GetSkeleton() || Draw->GetPlayLength() <= 0.0f ||
		ChargeLoop->GetPlayLength() <= 0.0f || ChargeFire->GetPlayLength() <= 0.0f)
	{
		return nullptr;
	}
	UAnimMontage* Montage = UAnimMontage::CreateSlotAnimationAsDynamicMontage(Draw, FullBodySlot, 0.06f, 0.12f, 1.0f, 1);
	if (!Montage)
	{
		return nullptr;
	}
	Montage->SetFlags(RF_Transient);
	FSlotAnimationTrack& Track = Montage->SlotAnimTracks[0];
	Track.AnimTrack.AnimSegments.Reset();
	const float DrawDuration = FMath::Min(ChargeDuration * 0.45f, Draw->GetPlayLength());
	const float LoopDuration = ChargeDuration - DrawDuration;
	const auto AddSegment = [&Track](UAnimSequence* Sequence, float Start, float Duration)
	{
		FAnimSegment Segment;
		Segment.SetAnimReference(Sequence);
		Segment.StartPos = Start;
		Segment.AnimStartTime = 0.0f;
		Segment.AnimEndTime = Sequence->GetPlayLength();
		Segment.AnimPlayRate = Sequence->GetPlayLength() / (Duration * FMath::Max(FMath::Abs(Sequence->RateScale), 0.001f));
		Segment.LoopingCount = 1;
		Track.AnimTrack.AnimSegments.Add(Segment);
	};
	AddSegment(Draw, 0.0f, DrawDuration);
	AddSegment(ChargeLoop, DrawDuration, LoopDuration);
	// 원본 발사 .118초를 각 .18초 사격의 중간에 맞추고 장전 후반은 반복하지 않는다.
	FAnimSegment FireSegment;
	FireSegment.SetAnimReference(ChargeFire);
	FireSegment.StartPos = ChargeDuration;
	FireSegment.AnimStartTime = 0.0f;
	FireSegment.AnimEndTime = FMath::Min(.24f, ChargeFire->GetPlayLength());
	FireSegment.AnimPlayRate = FireSegment.AnimEndTime /
		(PiercingShotInterval * FMath::Max(FMath::Abs(ChargeFire->RateScale), .001f));
	FireSegment.LoopingCount = PiercingShotCount;
	Track.AnimTrack.AnimSegments.Add(FireSegment);
	const float SalvoEnd = ChargeDuration + PiercingShotCount * PiercingShotInterval;
	if (bFinisher)
	{
		AddSegment(Draw, SalvoEnd, .18f);
		AddSegment(ChargeLoop, SalvoEnd + .18f, .06f);
		FireSegment.StartPos = SalvoEnd + .24f;
		FireSegment.LoopingCount = 1;
		Track.AnimTrack.AnimSegments.Add(FireSegment);
	}
	// 자동 블렌드가 마지막 발사(.12초 전)를 취소하지 않도록 끝 프레임부터 짧게 복귀한다.
	Montage->BlendOutTriggerTime = 0.0f;
	Montage->BlendOut.SetBlendTime(.035f);
	Montage->SetCompositeLength(SalvoEnd + (bFinisher ? PiercingFinisherDelay : 0.0f));
	return Montage;
}

UAnimMontage* USparrowSkillComponent::CreateHolyShotMontage()
{
	UAnimSequence* Fire = Skills[2].Animation;
	const IConsoleVariable* Design = IConsoleManager::Get().FindConsoleVariable(TEXT("Sparrow.EDesign.Style"));
	if (Design && Design->GetInt() >= 7)
	{
		UAnimSequence* Horizontal = LoadObject<UAnimSequence>(nullptr, TEXT("/Game/ParagonSparrow/Characters/Heroes/Sparrow/Animations/R_Ability_Fast_Fire.R_Ability_Fast_Fire"));
		if (Horizontal && Fire && Horizontal->GetSkeleton() == Fire->GetSkeleton()) { Fire = Horizontal; }
	}
	if (!Fire || Fire->GetPlayLength() < 0.6f - KINDA_SMALL_NUMBER)
	{
		return nullptr;
	}
	UAnimMontage* Montage = UAnimMontage::CreateSlotAnimationAsDynamicMontage(Fire,
		TEXT("SparrowUpperBody"), 0.05f, 0.12f, 1.0f, 1);
	if (!Montage)
	{
		return nullptr;
	}
	Montage->SetFlags(RF_Transient);
	FSlotAnimationTrack& Track = Montage->SlotAnimTracks[0];
	Track.AnimTrack.AnimSegments.Reset();
	const auto AddSegment = [&Track, Fire](float SourceStart, float SourceEnd, float Start, float Duration, int32 Loops)
	{
		FAnimSegment Segment;
		Segment.SetAnimReference(Fire);
		Segment.StartPos = Start;
		Segment.AnimStartTime = SourceStart;
		Segment.AnimEndTime = SourceEnd;
		Segment.AnimPlayRate = (SourceEnd - SourceStart) /
			(Duration * FMath::Max(FMath::Abs(Fire->RateScale), 0.001f));
		Segment.LoopingCount = Loops;
		Track.AnimTrack.AnimSegments.Add(Segment);
	};
	// 원본 손 포즈에서 .45초가 시작의 당김 자세로 돌아온다. 정방향 발사 동작을 한 번만 사용한다.
	// DissolveAmount는 원본 .0033~.0757초에 화살을 숨겨 각 사이클의 첫 발사 프레임과 맞는다.
	AddSegment(0.33f, 0.45f, 0.0f, HolyPreparationDuration, 1);
	AddSegment(0.0f, 0.45f, HolyPreparationDuration, HolyReleaseDuration, 1);
	AddSegment(0.45f, FMath::Min(0.6f, Fire->GetPlayLength()),
		HolyPreparationDuration + HolyReleaseDuration, HolyTailDuration, 1);
	Montage->SetCompositeLength(HolyTotalDuration);
	return Montage;
}

UAnimMontage* USparrowSkillComponent::CreateMultishotMontage()
{
	UAnimSequence* Fire = LoadObject<UAnimSequence>(nullptr,
		TEXT("/Game/ParagonSparrow/Characters/Heroes/Sparrow/Animations/R_Ability_Fast_Fire.R_Ability_Fast_Fire"));
	if (!Fire || Fire->GetSkeleton() != Skills[3].Animation->GetSkeleton() ||
		Fire->GetPlayLength() < 0.6f - KINDA_SMALL_NUMBER) { return nullptr; }
	UAnimMontage* Montage = UAnimMontage::CreateSlotAnimationAsDynamicMontage(Fire,
		TEXT("SparrowUpperBody"), 0.05f, 0.10f, 1.0f, 1);
	if (!Montage) { return nullptr; }
	Montage->SetFlags(RF_Transient);
	FAnimTrack& Track = Montage->SlotAnimTracks[0].AnimTrack;
	Track.AnimSegments.Reset();
	const auto Add = [&Track, Fire](float SourceStart, float SourceEnd, float Start, float Duration, int32 Loops)
	{
		FAnimSegment Segment;
		Segment.SetAnimReference(Fire);
		Segment.StartPos = Start;
		Segment.AnimStartTime = SourceStart;
		Segment.AnimEndTime = SourceEnd;
		Segment.AnimPlayRate = (SourceEnd - SourceStart) /
			(Duration * FMath::Max(FMath::Abs(Fire->RateScale), 0.001f));
		Segment.LoopingCount = Loops;
		Track.AnimSegments.Add(Segment);
	};
	// 사격 자세 다섯 번에 열 화살 파동을 겹친다. 발수 증가가 팔의 과도한 왕복으로 이어지지 않게 한다.
	Add(0.33f, 0.45f, 0.0f, MultishotPreparation, 1);
	Add(0.0f, 0.45f, MultishotPreparation, MultishotWaveInterval * MultishotWaveCount / 5.0f, 5);
	Add(0.45f, 0.60f, MultishotPreparation + MultishotWaveCount * MultishotWaveInterval, MultishotTail, 1);
	Montage->SetCompositeLength(MultishotDuration);
	return Montage;
}

const FSparrowSkillDefinition* USparrowSkillComponent::GetDefinition(ESparrowSkill Skill) const
{
	const int32 Slot = static_cast<int32>(Skill);
	return GetSlotDefinition(Slot);
}

bool USparrowSkillComponent::IgnoresCooldowns() const
{
	return CVarSparrowIgnoreCooldowns.GetValueOnGameThread() != 0;
}

float USparrowSkillComponent::GetCooldownRemaining(ESparrowSkill Skill) const
{
	return GetSlotCooldownRemaining(static_cast<int32>(Skill));
}

float USparrowSkillComponent::GetSlotCooldownRemaining(int32 Slot) const
{
	if (Slot == 16) { return !IgnoresCooldowns() && GetWorld() ? FMath::Max(0.0, ExtraNextSkillTimes[1] - GetWorld()->GetTimeSeconds()) : 0.0f; }
	if (Slot == 9) { return GetSanctuaryCooldownRemaining(Slot); }
	if (Slot == 17) { return !IgnoresCooldowns() && GetWorld() ? FMath::Max(0.0, NextRollTime - GetWorld()->GetTimeSeconds()) : 0.0f; }
	if (Slot >= 8 && Slot < 12)
	{
		return !IgnoresCooldowns() && GetWorld() && ExtraSkills.IsValidIndex(Slot - 8) ?
			static_cast<float>(FMath::Max(0.0, ExtraNextSkillTimes[Slot - 8] - GetWorld()->GetTimeSeconds())) : 0.0f;
	}
	return !IgnoresCooldowns() && GetWorld() && Skills.IsValidIndex(Slot) && !IsSkillPassive(Slot) ?
		static_cast<float>(FMath::Max(0.0, NextSkillTimes[Slot] - GetWorld()->GetTimeSeconds())) : 0.0f;
}

FText USparrowSkillComponent::GetSkillDisplayName(int32 Slot) const
{
	if (Slot == 16) { return FText::FromString(TEXT("Ascension")); }
	if (Slot == 9) { return GetSanctuaryName(Slot); }
	if (Slot == 17) { return FText::FromString(GetAscensionRemaining() > 0.0f ? TEXT("Golden Blink") : TEXT("Golden Roll")); }
	if (Slot >= 8 && Slot < 12)
	{
		const TCHAR* ExtraNames[] = {TEXT("Gear Arrow"), TEXT("Ascension"), TEXT("Converging Piercing"), TEXT("Crystal Shot")};
		return FText::FromString(ExtraNames[Slot - 8]);
	}
	const TCHAR* Names[] = {TEXT("Hail of Arrows"), TEXT("Piercing Shot"), TEXT("Holy Arrow"), TEXT("Golden Multishot")};
	return Slot >= 0 && Slot < UE_ARRAY_COUNT(Names) ? FText::FromString(Names[Slot]) : FText::GetEmpty();
}

ECharacterSkillTargeting USparrowSkillComponent::GetSkillTargeting(int32 Slot) const
{
	if (Slot == 0) { return ECharacterSkillTargeting::Ground; }
	return Slot == 16 ? ECharacterSkillTargeting::Self : ECharacterSkillTargeting::Direction;
}

FText USparrowSkillComponent::GetSkillStatusText(int32 Slot) const
{
	if (Slot == 9) { return GetSanctuaryStatus(Slot); }
	if (Slot == 0) { return FText::FromString(TEXT("Ground area | 300cm | 4s")); }
	if (Slot == 8) { return FText::FromString(TEXT("90 damage | slow feather arrow")); }
	if (Slot == 16 && GetAscensionRemaining() > 0.0f)
	{
		return FText::FromString(FString::Printf(TEXT("Golden wings %.1fs"), GetAscensionRemaining()));
	}
	if (Slot == 10) { return FText::FromString(TEXT("65 damage | 1500cm piercing line")); }
	if (Slot == 11) { return FText::FromString(TEXT("80 damage | 1100cm crystal arrow")); }
	if (Slot == 17) { return FText::FromString(GetAscensionRemaining() > 0.0f ?
		TEXT("Blink480cm | 0.065s control | 6s cooldown") : TEXT("Vault480cm | 0.267s control | 6s cooldown")); }
	if (Slot == 2)
	{
		return FText::FromString(FString::Printf(TEXT("1 arrow | 60 damage | Relentless %d / 10"), GetRelentlessStacks(LastRelentlessTarget.Get())));
	}
	if (Slot == 3) { return FText::FromString(TEXT("186 arrows | 6 waves | 60 damage")); }
	return FText::GetEmpty();
}

FString USparrowSkillComponent::GetInputFeedback() const
{
	return GetWorld() && GetWorld()->GetTimeSeconds() < FeedbackDeadline ? Feedback : FString();
}

bool USparrowSkillComponent::RejectInput(const TCHAR* Reason)
{
	Feedback = Reason;
	FeedbackDeadline = GetWorld() ? GetWorld()->GetTimeSeconds() + 1.25 : 0.0;
	return false;
}

bool USparrowSkillComponent::TryUseSkillSlot(int32 Slot, const FVector& AimLocation, AActor* Target)
{
	if (IsRolling()) { return RejectInput(TEXT("Rolling")); }
	if (IsSanctuaryCasting()) { return RejectInput(TEXT("Casting")); }
	if (Slot == 16)
	{
		return IsBackstepping() ? RejectInput(TEXT("Backstepping")) : TryUseExtraSkill(9, AimLocation, Target);
	}
	if (Slot == 9) { return TryUseSanctuarySkill(Slot, AimLocation, Target); }
	if (Slot == 17) { return TryRoll(AimLocation); }
	if (IsBackstepping()) { return RejectInput(TEXT("Backstepping")); }
	if (Slot >= 8 && Slot < 12)
	{
		return TryUseExtraSkill(Slot, AimLocation, Target);
	}
	return Skills.IsValidIndex(Slot) ? TryUseSkill(static_cast<ESparrowSkill>(Slot), AimLocation, Target) : RejectInput(TEXT("Unavailable"));
}

bool USparrowSkillComponent::TryUseSkill(ESparrowSkill Skill, const FVector& AimLocation, AActor* Target)
{
	const int32 Slot = static_cast<int32>(Skill);
	if (!Skills.IsValidIndex(Slot))
	{
		return RejectInput(TEXT("Unavailable"));
	}
	if (!bEnabled || !GetWorld() || !Character.IsValid() || !Character->GetCharacterMovement() ||
		Character->GetCharacterMovement()->MovementMode != MOVE_Walking || AimLocation.ContainsNaN())
	{
		return RejectInput(TEXT("Unavailable"));
	}
	if (IsCasting())
	{
		return RejectInput(TEXT("Casting"));
	}
	if (GetSlotCooldownRemaining(Slot) > 0.0f)
	{
		return RejectInput(TEXT("Cooldown"));
	}
	if (Slot == 3 && IsInnerFireActive())
	{
		return RejectInput(TEXT("Inner Fire is already active"));
	}
	FVector Aim = AimLocation;
	if (Slot == 0)
	{
		if (HailZones.Num() >= MaxHailZones)
		{
			return RejectInput(TEXT("Too many active arrow rains"));
		}
		if (!FindHailLocation(AimLocation, Target, Aim))
		{
			return RejectInput(TEXT("Invalid ground, out of range or blocked"));
		}
	}
	else if ((Slot == 1 || Slot == 2 || Slot == 3) && (Aim - Character->GetActorLocation()).GetSafeNormal2D().IsNearlyZero())
	{
		return RejectInput(TEXT("Choose a direction"));
	}
	return BeginSkill(Slot, Aim);
}

bool USparrowSkillComponent::HasWorldLineOfSight(const FVector& From, const FVector& To, AActor* Target) const
{
	if (!GetWorld() || !Character.IsValid())
	{
		return false;
	}
	FCollisionQueryParams Query(SCENE_QUERY_STAT(SparrowSkillVisibility), false, Character.Get());
	// 다른 캐릭터는 범위 스킬의 지형 가림막이 아니다. 정적·동적 월드 장애물은 그대로 검사한다.
	for (TActorIterator<APawn> It(GetWorld()); It; ++It)
	{
		Query.AddIgnoredActor(*It);
	}
	for (TActorIterator<AKwangTrainingDummy> It(GetWorld()); It; ++It)
	{
		Query.AddIgnoredActor(*It);
	}
	if (IsValid(Target))
	{
		Query.AddIgnoredActor(Target);
	}
	FHitResult Hit;
	return !GetWorld()->LineTraceSingleByChannel(Hit, From, To, ECC_Visibility, Query);
}

bool USparrowSkillComponent::FindHailLocation(const FVector& Aim, AActor* AimTarget, FVector& Result) const
{
	if (!Character.IsValid() || !GetWorld() || Aim.ContainsNaN())
	{
		return false;
	}
	const FVector Feet = Character->GetActorLocation() - FVector(0.0f, 0.0f, Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
	if ((Aim - Feet).SizeSquared2D() > FMath::Square(Skills[0].Range) || FMath::Abs(Aim.Z - Feet.Z) > 400.0f)
	{
		return false;
	}
	FCollisionQueryParams Query(SCENE_QUERY_STAT(SparrowHailGround), false, Character.Get());
	for (TActorIterator<APawn> It(GetWorld()); It; ++It)
	{
		Query.AddIgnoredActor(*It);
	}
	for (TActorIterator<AKwangTrainingDummy> It(GetWorld()); It; ++It)
	{
		Query.AddIgnoredActor(*It);
	}
	if (IsValid(AimTarget))
	{
		Query.AddIgnoredActor(AimTarget);
	}
	FHitResult Ground;
	if (!GetWorld()->LineTraceSingleByChannel(Ground, Aim + FVector(0.0f, 0.0f, 400.0f),
		Aim - FVector(0.0f, 0.0f, 600.0f), ECC_Visibility, Query) || Ground.ImpactNormal.Z < 0.55f)
	{
		return false;
	}
	Result = Ground.ImpactPoint;
	return (Result - Feet).SizeSquared2D() <= FMath::Square(Skills[0].Range) &&
		FMath::Abs(Result.Z - Feet.Z) <= HailHeight &&
		HasWorldLineOfSight(Character->GetActorLocation(), Result + FVector(0.0f, 0.0f, 50.0f));
}

bool USparrowSkillComponent::BeginSkill(int32 Slot, const FVector& Aim)
{
	UAnimInstance* Anim = Character->GetMesh() ? Character->GetMesh()->GetAnimInstance() : nullptr;
	const FSparrowSkillDefinition* Definition = GetSlotDefinition(Slot);
	UAnimMontage* Montage = GetSlotMontage(Slot);
	bPiercingAscendedCast = Slot == 1 && GetAscensionRemaining() > 0.0f;
	if (bPiercingAscendedCast) { Montage = AscendedChargeMontage; }
	if (!Anim || !Definition || !Montage)
	{
		return RejectInput(TEXT("Unavailable"));
	}
	Character->InterruptIntroAnimation();
	Character->CancelBasicAttackForSkill();
	CastAnimInstance = Anim;
	SavedRootMotionMode = Anim->RootMotionMode;
	bSavedOrientRotation = Character->GetCharacterMovement()->bOrientRotationToMovement;
	Anim->SetRootMotionMode(ERootMotionMode::IgnoreRootMotion);
	Character->GetCharacterMovement()->bOrientRotationToMovement = false;
	if (Character->GetController())
	{
		Character->GetController()->StopMovement();
	}
	Character->GetCharacterMovement()->StopMovementImmediately();
	const FVector Direction = (Aim - Character->GetActorLocation()).GetSafeNormal2D();
	if (Slot != 9 && !Direction.IsNearlyZero())
	{
		Character->SetActorRotation(FRotator(0.0f, Direction.Rotation().Yaw, 0.0f));
	}
	CastAim = Aim;
	const APlayerController* Player = Cast<APlayerController>(Character->GetController());
	bRapidMoveWasDown = Player && Player->IsInputKeyDown(EKeys::RightMouseButton);
	bCasting = true;
	bActionExecuted = false;
	MovementReadyAt = TNumericLimits<double>::Max();
	ActiveSkillIndex = Slot;
	ActiveMontage = Montage;
	const uint32 Generation = ++CastGeneration;
	const float Duration = Anim->Montage_Play(ActiveMontage, 1.0f, EMontagePlayReturnType::Duration);
	if (Duration <= 0.0f)
	{
		FinishSkill();
		return RejectInput(TEXT("Unavailable"));
	}
	if (Slot == 3)
	{
		FActorSpawnParameters Spawn;
		Spawn.Owner = Character.Get();
		Spawn.ObjectFlags |= RF_Transient;
		Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		MultishotBowTint = GetWorld()->SpawnActor<ASparrowMultishotBowTint>(
			Character->GetActorLocation(), Character->GetActorRotation(), Spawn);
		const int32 Candidate = ASparrowArsenalStudyFX::GetCandidate(3);
		if (Candidate > 0)
		{
			ASparrowArsenalStudyFX* Study = GetWorld()->SpawnActor<ASparrowArsenalStudyFX>(GetArrowOrigin(), Direction.Rotation(), Spawn);
			if (Study && Study->Initialize(Character.Get(), 3, Candidate, GetArrowOrigin(), Direction, MultishotPreparation))
			{
				ArsenalStudyFX = Study;
				VisualProxies.Add(Study);
			}
			else if (Study) { Study->Destroy(); }
		}
	}
	if (Slot >= 8)
	{
		ExtraNextSkillTimes[Slot - 8] = GetWorld()->GetTimeSeconds() + Definition->Cooldown;
	}
	else
	{
		NextSkillTimes[Slot] = GetWorld()->GetTimeSeconds() + Definition->Cooldown;
	}
	Feedback.Reset();
	FOnMontageEnded EndDelegate;
	EndDelegate.BindUObject(this, &USparrowSkillComponent::OnMontageEnded, Generation);
	Anim->Montage_SetEndDelegate(EndDelegate, ActiveMontage);
	FOnMontageBlendingOutStarted BlendDelegate;
	BlendDelegate.BindUObject(this, &USparrowSkillComponent::OnMontageBlendingOut, Generation);
	Anim->Montage_SetBlendingOutDelegate(BlendDelegate, ActiveMontage);
	const float ActionTime = Slot == 1 ? FMath::Clamp(Definition->ActionTime, ChargeDuration, Duration * 0.85f) :
		FMath::Min(FMath::Max(Definition->ActionTime, 0.01f), Duration * 0.85f);
	const float Recovery = FMath::Max(ActionTime + 0.05f, FMath::Min(
		Definition->RecoveryTime + (bPiercingAscendedCast ? PiercingFinisherDelay : 0.0f), Duration));
	if ((Slot == 0 || Slot == 1) && GetAscensionRemaining() > 0.0f)
	{
		VisualProxies.RemoveAll([](const TWeakObjectPtr<AActor>& Proxy) { return !Proxy.IsValid(); });
		FActorSpawnParameters Spawn;
		Spawn.Owner = Character.Get();
		Spawn.ObjectFlags |= RF_Transient;
		Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		const FVector VisualDirection = Direction.IsNearlyZero() ? Character->GetActorForwardVector() : Direction;
		ASparrowAscendedShotFX* Visual = GetWorld()->SpawnActor<ASparrowAscendedShotFX>(GetArrowOrigin(), VisualDirection.Rotation(), Spawn);
		if (Visual && Visual->InitializeBow(Character.Get(), Slot, GetArrowOrigin(), VisualDirection, ActionTime))
		{
			AscendedBowFX = Visual;
			VisualProxies.Add(Visual);
		}
		else if (Visual) { Visual->Destroy(); }
	}
	GetWorld()->GetTimerManager().SetTimer(ActionTimer, FTimerDelegate::CreateWeakLambda(this, [this, Generation]()
	{
		ExecuteAction(Generation);
	}), ActionTime, false);
	GetWorld()->GetTimerManager().SetTimer(RecoveryTimer, FTimerDelegate::CreateWeakLambda(this, [this, Generation]()
	{
		if (bCasting && Generation == CastGeneration)
		{
			FinishSkill();
		}
	}), Recovery, false);
	if (Slot >= 8 && Slot < 12)
	{
		PrepareExtraPresentation(Slot, ActionTime);
	}
	const IConsoleVariable* WPresentation = IConsoleManager::Get().FindConsoleVariable(TEXT("Sparrow.Renaissance.W"));
	const bool bNewWPreparation = Slot == 1 && WPresentation && WPresentation->GetInt() == 1;
	if (bNewWPreparation)
	{
		const FTransform Transform(FRotator(0, Character->GetActorRotation().Yaw, 0), GetArrowOrigin());
		ASparrowShotWave* Preparation = GetWorld()->SpawnActorDeferred<ASparrowShotWave>(
			ASparrowShotWave::StaticClass(), Transform, Character.Get(), nullptr, ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
		if (Preparation)
		{
			Preparation->SetPreparationMode(ActionTime);
			Preparation->FinishSpawning(Transform);
			VisualProxies.RemoveAll([](const TWeakObjectPtr<AActor>& Proxy) { return !Proxy.IsValid(); });
			VisualProxies.Add(Preparation);
		}
	}
	if (Slot == 0 || (Slot == 1 && !bNewWPreparation))
	{
		// Q는 BoneSocketActor로 활의 여러 뼈를 사용하고, W의 원점 기반 충전 FX는 활 소켓을 따라간다.
		const FName EffectSocket = Slot == 1 ? FName(TEXT("BowEmitterSocket")) : NAME_None;
		if (UParticleSystemComponent* Effect = SpawnEffect(Skills[Slot].CastEffect, GetArrowOrigin(),
			Character->GetActorRotation(), ActionTime + 0.15f, true, 1.0f, EffectSocket))
		{
			CastEffects.Add(Effect);
		}
		if (RuntimeRapidBowEffect)
		{
			if (UParticleSystemComponent* Bow = SpawnEffect(RuntimeRapidBowEffect, GetArrowOrigin(),
				Character->GetActorRotation(), ActionTime + 0.18f, true, Slot == 1 ? 0.45f : 0.65f, TEXT("BowEmitterSocket")))
			{
				CastEffects.Add(Bow);
			}
		}
	}
	else if (Slot == 2)
	{
		// 큰 활의 개방과 전방 파문은 E 전용 액터가 소유하며 실제 발사 예약과 분리한다.
		FActorSpawnParameters Spawn;
		Spawn.Owner = Character.Get();
		Spawn.ObjectFlags |= RF_Transient;
		Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		HolyBow = GetWorld()->SpawnActor<ASparrowHolyBow>(GetArrowOrigin(), Character->GetActorRotation(), Spawn);
		if (HolyBow.IsValid())
		{
			HolyBow->Initialize((CastAim - GetArrowOrigin()).GetSafeNormal());
		}
	}
	SetComponentTickEnabled(true);
	return true;
}

bool USparrowSkillComponent::ValidateCastState() const
{
	return bCasting && Character.IsValid() && CastAnimInstance.IsValid() && Character->GetMesh() &&
		Character->GetMesh()->GetAnimInstance() == CastAnimInstance.Get() && Character->GetCharacterMovement() &&
		Character->GetCharacterMovement()->MovementMode == MOVE_Walking && ActiveMontage &&
		!CastAnimInstance->Montage_GetIsStopped(ActiveMontage);
}

bool USparrowSkillComponent::HasRapidShotMovePress()
{
	const APlayerController* Player = Character.IsValid() ? Cast<APlayerController>(Character->GetController()) : nullptr;
	const bool bDown = Player && Player->IsInputKeyDown(EKeys::RightMouseButton);
	const bool bNewPress = bDown && !bRapidMoveWasDown;
	bRapidMoveWasDown = bDown;
	return bNewPress;
}

void USparrowSkillComponent::ExecuteAction(uint32 Generation)
{
	if (!bCasting || bActionExecuted || Generation != CastGeneration)
	{
		return;
	}
	if (!ValidateCastState() || ((ActiveSkillIndex == 2 || ActiveSkillIndex == 3) && HasRapidShotMovePress()))
	{
		FinishSkill();
		return;
	}
	bActionExecuted = true;
	// W/R은 마지막 발사가 끝난 뒤에만 회복 종료로 잔여 발사를 지우지 않도록 한다.
	if (ActiveSkillIndex != 1 && ActiveSkillIndex != 3) { MovementReadyAt = GetWorld()->GetTimeSeconds() + .035; }
	StopCastEffects();
	if (ActiveSkillIndex >= 8)
	{
		ExecuteExtraAction(Generation);
		return;
	}
	if (ActiveSkillIndex == 0)
	{
		FVector Ground;
		if (!FindHailLocation(CastAim, nullptr, Ground))
		{
			RejectInput(TEXT("Ground became blocked"));
			return;
		}
		StartHail(Ground);
		SpawnHailLaunch();
	}
	else if (ActiveSkillIndex == 1)
	{
		// 지면 선택과 높은 표적 모두 실제 활의 발사 위치에서 조준한다.
		FirePiercingBurst(Generation, 0);
	}
	else if (ActiveSkillIndex == 2)
	{
		FireHolyArrow(Generation);
	}
	else if (ActiveSkillIndex == 3)
	{
		FireMultishotWave(Generation, 0);
	}
}

void USparrowSkillComponent::FirePiercingBurst(uint32 Generation, int32 ShotIndex)
{
	if (!bCasting || ActiveSkillIndex != 1 || Generation != CastGeneration ||
		ShotIndex < 0 || ShotIndex >= PiercingShotCount + (bPiercingAscendedCast ? 1 : 0)) { return; }
	if (!ValidateCastState()) { FinishSkill(); return; }
	if (ShotIndex == 0) { PiercingStartedAt = GetWorld()->GetTimeSeconds(); }
	const bool bFinalShot = ShotIndex + 1 == PiercingShotCount + (bPiercingAscendedCast ? 1 : 0);
	const float DamageScale = bPiercingAscendedCast ? (bFinalShot ? 2.0f : 1.0f) / 6.0f : 1.0f / PiercingShotCount;
	// 변신 W는 추가 한 발만 강화한다. 유지 중인 날개의 포즈나 이펙트는 조작하지 않는다.
	ReleasePiercingShot(GetArrowOrigin(), CastAim, DamageScale, bPiercingAscendedCast && bFinalShot);
	UE_LOG(LogTemp, Display, TEXT("SPARROW_PIERCING_BURST shot=%d damage=%.2f finisher=%d"),
		ShotIndex + 1, Skills[1].Damage * DamageScale, bPiercingAscendedCast && bFinalShot);
	if (bFinalShot)
	{
		MovementReadyAt = GetWorld()->GetTimeSeconds() + .035;
		return;
	}
	// 첫 발사 시각에 고정해 낮은 FPS에서 각 타이머의 프레임 반올림 오차가 누적되지 않게 한다.
	const float NextDelay = FMath::Max(KINDA_SMALL_NUMBER, static_cast<float>(
		PiercingStartedAt + (ShotIndex + 1 == PiercingShotCount ?
			(PiercingShotCount - 1) * PiercingShotInterval + PiercingFinisherDelay : (ShotIndex + 1) * PiercingShotInterval) -
		GetWorld()->GetTimeSeconds()));
	GetWorld()->GetTimerManager().SetTimer(PiercingTimer,
		FTimerDelegate::CreateWeakLambda(this, [this, Generation, ShotIndex]()
	{
		FirePiercingBurst(Generation, ShotIndex + 1);
	}), NextDelay, false);
}

void USparrowSkillComponent::FireMultishotWave(uint32 Generation, int32 WaveIndex)
{
	if (!bCasting || ActiveSkillIndex != 3 || Generation != CastGeneration ||
		WaveIndex < 0 || WaveIndex >= MultishotWaveCount) { return; }
	if (!ValidateCastState() || HasRapidShotMovePress()) { FinishSkill(); return; }
	const FVector Forward = (CastAim - GetArrowOrigin()).GetSafeNormal2D();
	if (Forward.IsNearlyZero()) { FinishSkill(); return; }
	// 작은 화살 31발씩 빠르게 쏟되 파동별 공유 집합이 근거리 중첩 피해를 막는다.
	const TSharedPtr<TSet<TWeakObjectPtr<AActor>>> WaveHits = MakeShared<TSet<TWeakObjectPtr<AActor>>>();
	const bool bCraft = ArsenalStudyFX.IsValid() && ArsenalStudyFX->UsesCraftVolleyPresentation();
	int32 Released = 0;
	for (int32 ArrowIndex = 0; ArrowIndex < MultishotArrowsPerWave; ++ArrowIndex)
	{
		const float Angle = FMath::Lerp(-MultishotHalfAngle, MultishotHalfAngle,
			static_cast<float>(ArrowIndex) / (MultishotArrowsPerWave - 1));
		const FVector Direction = Forward.RotateAngleAxis(Angle, FVector::UpVector);
		if (ASparrowArrow* Arrow = SpawnArrow(Direction, Skills[3].Damage / MultishotWaveCount, Skills[3].Range,
			2600.0f, true, false, false, true, nullptr, true, WaveHits))
		{
			Arrow->SetMultishotPresentationScale(1.0f);
			if (bCraft) { Arrow->EnableCraftMultishot(ArrowIndex, WaveIndex); }
			else if (ArsenalStudyFX.IsValid() && ArsenalStudyFX->UsesRenaissancePresentation()) { Arrow->EnableRenaissanceMultishot(); }
			++Released;
		}
	}
	const bool bFinalWave = WaveIndex == MultishotWaveCount - 1;
	if (Released > 0 && AscendedBowFX.IsValid()) { AscendedBowFX->Pulse(GetArrowOrigin(), Forward); }
	if (Released > 0 && ArsenalStudyFX.IsValid()) { ArsenalStudyFX->Pulse(GetArrowOrigin(), Forward); }
	if (bFinalWave) { MovementReadyAt = GetWorld()->GetTimeSeconds() + .035; }
	if (!bCraft)
	{
		SpawnEffect(SparrowPresentation::GetMultishotBowGlow(), GetArrowOrigin(), Forward.Rotation(), 0.16f, false, 1.15f);
		SpawnEffect(bFinalWave ? SparrowPresentation::GetMultishotFinishShards() : SparrowPresentation::GetReleaseShards(),
			GetArrowOrigin(), Forward.Rotation(), bFinalWave ? 0.18f : 0.29f, false, WaveIndex == 0 || bFinalWave ? 0.85f : 0.50f);
	}
	if (!bCraft && WaveIndex == 0 && RuntimeRapidBowEffect)
	{
		RapidBowEffect = SpawnEffect(RuntimeRapidBowEffect, GetArrowOrigin(), Character->GetActorRotation(),
			MultishotWaveCount * MultishotWaveInterval + 0.16f, true, 1.1f, TEXT("BowEmitterSocket"));
	}
	UE_LOG(LogTemp, Display, TEXT("SPARROW_MULTISHOT wave=%d arrows=%d damage_per_target=%.2f"),
		WaveIndex + 1, Released, Skills[3].Damage / MultishotWaveCount);
	if (WaveIndex + 1 < MultishotWaveCount)
	{
		GetWorld()->GetTimerManager().SetTimer(MultishotTimer,
			FTimerDelegate::CreateWeakLambda(this, [this, Generation, WaveIndex]()
		{
			FireMultishotWave(Generation, WaveIndex + 1);
		}), MultishotWaveInterval, false);
	}
}

void USparrowSkillComponent::FireHolyArrow(uint32 Generation)
{
	if (!bCasting || ActiveSkillIndex != 2 || Generation != CastGeneration)
	{
		return;
	}
	if (!ValidateCastState() || HasRapidShotMovePress())
	{
		FinishSkill();
		return;
	}
	const FVector Origin = GetArrowOrigin();
	const FVector Direction = (CastAim - Origin).GetSafeNormal();
	const int32 Design = HolyBow.IsValid() ? HolyBow->GetDesignStyle() : 0;
	if (Design == 2)
	{
		// 근접 후보는 발사 시점의 부채꼴 한 번만 타격하며 원거리 화살을 만들지 않는다.
		FCollisionObjectQueryParams Objects;
		Objects.AddObjectTypesToQuery(ECC_Pawn);
		Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
		FCollisionQueryParams Query(SCENE_QUERY_STAT(SparrowEBowSweep), false, Character.Get());
		TArray<FOverlapResult> Overlaps;
		GetWorld()->OverlapMultiByObjectType(Overlaps, Character->GetActorLocation(), FQuat::Identity,
			Objects, FCollisionShape::MakeSphere(550.0f), Query);
		TSet<TWeakObjectPtr<AActor>> Damaged;
		for (const FOverlapResult& Overlap : Overlaps)
		{
			AActor* Target = Overlap.GetActor();
			if (!IsLivingTarget(Target) || Target == Character.Get() || !Target->CanBeDamaged() || Damaged.Contains(Target) ||
				(!Target->IsA<APawn>() && !Target->IsA<AKwangTrainingDummy>())) { continue; }
			const FVector Delta = Target->GetActorLocation() - Character->GetActorLocation();
			if (Delta.SizeSquared2D() > FMath::Square(520.0f) || FMath::Abs(Delta.Z) > 180.0f ||
				FVector::DotProduct(Delta.GetSafeNormal2D(), Direction.GetSafeNormal2D()) < .70710678f ||
				!HasWorldLineOfSight(Origin, Target->GetActorLocation(), Target)) { continue; }
			Damaged.Add(Target);
			RecordRelentlessHit(Target);
			UGameplayStatics::ApplyDamage(Target, Skills[2].Damage, Character->GetController(), Character.Get(), nullptr);
			FActorSpawnParameters HitSpawn;
			HitSpawn.Owner = Character.Get();
			HitSpawn.ObjectFlags |= RF_Transient;
			HitSpawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			if (ASparrowHolyBow* HitVisual = GetWorld()->SpawnActor<ASparrowHolyBow>(Target->GetActorLocation() + FVector(0.0f, 0.0f, 55.0f), FRotator::ZeroRotator, HitSpawn))
			{
				HitVisual->InitializeImpact(Direction, false, 2);
			}
		}
		if (HolyBow.IsValid()) { HolyBow->NotifyShot(); }
		return;
	}
	if (Design >= 3 && Design <= 5)
	{
		const FVector Right = FVector::CrossProduct(FVector::UpVector, Direction).GetSafeNormal();
		const FVector Target = Origin + Direction * FMath::Clamp(static_cast<float>(FVector::Distance(Origin, CastAim)), 160.0f, Skills[2].Range);
		int32 Released = 0;
		for (int32 Lane = -2; Lane <= 2; ++Lane)
		{
			if (ASparrowArrow* Arrow = SpawnArrow(Direction, Skills[2].Damage / 5.0f, Skills[2].Range, 6000.0f,
				false, false, false, false, nullptr, false))
			{
				Arrow->SetRecordsRelentless(Lane == 0);
				Arrow->ConfigureEDesignPresentation(Design);
				Arrow->ConfigureConvergingFlight(Target, Right * (Lane * 155.0f) + FVector::UpVector * (FMath::Abs(Lane) * 65.0f), .30f);
				FActorSpawnParameters Spawn;
				Spawn.Owner = Character.Get();
				Spawn.ObjectFlags |= RF_Transient;
				Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
				if (ASparrowEDesignTrail* Trail = GetWorld()->SpawnActor<ASparrowEDesignTrail>(Origin, FRotator::ZeroRotator, Spawn)) { Trail->Initialize(Arrow, Design); }
				++Released;
			}
		}
		if (Released > 0 && HolyBow.IsValid()) { HolyBow->NotifyShot(); }
		return;
	}
	// E는 기본 피해 전체를 단발에 담는다. 실제 명중 한 번만 누적 피해 패시브에 기록한다.
	if (ASparrowArrow* Arrow = SpawnArrow(Direction, Skills[2].Damage, Skills[2].Range, 6000.0f,
		false, false, true, false))
	{
		if (Design == 1 || Design == 6 || Design == 7 || Design == 8) { Arrow->ConfigureEDesignPresentation(Design); }
		if (Design == 6 || Design == 7 || Design == 8)
		{
			FActorSpawnParameters Spawn;
			Spawn.Owner = Character.Get();
			Spawn.ObjectFlags |= RF_Transient;
			Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			if (ASparrowEDesignTrail* Trail = GetWorld()->SpawnActor<ASparrowEDesignTrail>(Origin, FRotator::ZeroRotator, Spawn)) { Trail->Initialize(Arrow, Design); }
		}
		SpawnEffect(PrimaryMuzzle, Origin, Direction.Rotation(), 0.16f, false, 0.45f);
		if (HolyBow.IsValid()) { HolyBow->NotifyShot(); }
	}
}

FVector USparrowSkillComponent::GetArrowOrigin() const
{
	if (!Character.IsValid())
	{
		return FVector::ZeroVector;
	}
	USkeletalMeshComponent* Mesh = Character->GetMesh();
	// 원본 스켈레톤의 arrow_anchor는 bow_base에 붙어 있어 모션의 arrow_nock 이동과 독립적이다.
	if (Mesh && Mesh->DoesSocketExist(TEXT("arrow_anchor")))
	{
		return Mesh->GetSocketLocation(TEXT("arrow_anchor"));
	}
	if (Mesh && Mesh->DoesSocketExist(TEXT("BowEmitterSocket")))
	{
		return Mesh->GetSocketLocation(TEXT("BowEmitterSocket"));
	}
	return Character->GetActorLocation() + Character->GetActorForwardVector() * 55.0f + FVector(0.0f, 0.0f, 25.0f);
}

ASparrowArrow* USparrowSkillComponent::SpawnArrow(const FVector& Direction, float Damage, float Range, float Speed,
	bool bPiercing, bool bPassesWorld, bool bApplyRelentlessBonus, bool bUltimate,
	const FVector* OriginOverride, bool bEchoAllowed, TSharedPtr<TSet<TWeakObjectPtr<AActor>>> VolleyHits)
{
	if (!GetWorld() || !Character.IsValid() || Direction.ContainsNaN() || Direction.IsNearlyZero())
	{
		return nullptr;
	}
	const FTransform Transform(Direction.Rotation(), OriginOverride ? *OriginOverride : GetArrowOrigin());
	ASparrowArrow* Arrow = GetWorld()->SpawnActorDeferred<ASparrowArrow>(ASparrowArrow::StaticClass(), Transform,
		Character.Get(), Character.Get(), ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
	if (!Arrow)
	{
		return nullptr;
	}
	Arrow->SetAppliesRelentlessBonus(bApplyRelentlessBonus);
	Arrow->SetRecordsRelentless(bEchoAllowed);
	Arrow->SetSharedVolleyHits(VolleyHits);
	if (GetAscensionRemaining() > 0.0f)
	{
		Arrow->Tags.Add(TEXT("SparrowAscendedArrow"));
		if (bCasting && (ActiveSkillIndex == 1 || ActiveSkillIndex == 3))
		{
			Arrow->Tags.Add(ActiveSkillIndex == 1 ? TEXT("SparrowAscendedW") : TEXT("SparrowAscendedR"));
		}
	}
	const bool bChargedShot = bPiercing && bPassesWorld && !bUltimate;
	if (bChargedShot) { Arrow->SetVisualWidthScale(1.1f); }
	UParticleSystem* Trail = bUltimate ? UltimateTrail.Get() : (bChargedShot ? Skills[1].CastEffect.Get() : PrimaryTrail.Get());
	UParticleSystem* TargetHit = bUltimate ? Skills[3].ImpactEffect.Get() : (bChargedShot ? Skills[1].ImpactEffect.Get() : PrimaryHit.Get());
	UParticleSystem* WorldHit = bUltimate ? UltimateWorldHit.Get() : PrimaryWorldHit.Get();
	Arrow->InitArrow(Direction, Damage, Range, Speed, bPiercing, bPassesWorld,
		Trail, TargetHit, WorldHit);
	if (bCasting && ActiveSkillIndex == 2 && !bChargedShot && !bUltimate)
	{
		Arrow->SetVisualWidthScale(1.45f);
		Arrow->ConfigureImpactPresentation(Skills[3].ImpactEffect, 0.48f, 0.26f);
		Arrow->EnableRapidFlow();
	}
	Arrow->FinishSpawning(Transform);
	if (bChargedShot) { Arrow->EnableChargedAura(); }
	OwnedArrows.RemoveAll([](const TWeakObjectPtr<ASparrowArrow>& Item) { return !Item.IsValid(); });
	OwnedArrows.Add(Arrow);
	if (bEchoAllowed) { EchoArrowShot(Direction, Damage, Range, Speed, bPiercing, bPassesWorld, bUltimate, VolleyHits); }
	return Arrow;
}

bool USparrowSkillComponent::FireBasicAttackAt(const FVector& AimLocation)
{
	if (AimLocation.ContainsNaN())
	{
		return false;
	}
	const TGuardValue<TOptional<FVector>> AimGuard(MirrorAimLocation, TOptional<FVector>(AimLocation));
	return FireBasicAttack((AimLocation - GetArrowOrigin()).GetSafeNormal());
}

bool USparrowSkillComponent::FireBasicAttack(const FVector& Direction)
{
	if (!bEnabled || IsCasting() || !Character.IsValid() || !Character->GetCharacterMovement() ||
		Character->GetCharacterMovement()->MovementMode != MOVE_Walking || Direction.ContainsNaN())
	{
		return false;
	}
	const FVector Forward = Direction.GetSafeNormal();
	if (Forward.IsNearlyZero())
	{
		return false;
	}
	const bool bUltimate = IsInnerFireActive();
	const float Range = bUltimate ? Skills[3].Range : BasicAttackRange;
	const bool bSpawned = SpawnArrow(Forward, BasicAttackDamage, Range, ArrowSpeed, bUltimate, false, true, bUltimate) != nullptr;
	if (bUltimate)
	{
		// 중앙 20 + 측면 5씩 네 발로, 한 번의 부채꼴 사격 총 기본 피해 40은 유지한다.
		for (const float Angle : {-24.0f, -12.0f, 12.0f, 24.0f})
		{
			SpawnArrow(Forward.RotateAngleAxis(Angle, FVector::UpVector), BasicAttackDamage * 0.25f,
				Range, ArrowSpeed, true, false, true, true);
		}
	}
	if (bSpawned)
	{
		SpawnEffect(PrimaryMuzzle,
			GetArrowOrigin(), Forward.Rotation(), 0.6f);
	}
	return bSpawned;
}

ASparrowBowFeedback* USparrowSkillComponent::SpawnBowFeedback(bool bRapid)
{
	if (!GetWorld() || !Character.IsValid()) { return nullptr; }
	const FTransform Transform(FRotator(0, Character->GetActorRotation().Yaw, 0), GetArrowOrigin());
	ASparrowBowFeedback* FeedbackActor = GetWorld()->SpawnActorDeferred<ASparrowBowFeedback>(
		ASparrowBowFeedback::StaticClass(), Transform, Character.Get(), Character.Get(), ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
	if (!FeedbackActor) { return nullptr; }
	if (bRapid) { FeedbackActor->SetRapidMode(); }
	FeedbackActor->FinishSpawning(Transform);
	VisualProxies.RemoveAll([](const TWeakObjectPtr<AActor>& Proxy) { return !Proxy.IsValid(); });
	VisualProxies.Add(FeedbackActor);
	return FeedbackActor;
}

bool USparrowSkillComponent::IsInnerFireActive() const
{
	return GetBuffRemaining() > 0.0f;
}

UAnimMontage* USparrowSkillComponent::GetInnerFireAttackMontage() const
{
	return IsInnerFireActive() && SkillMontages.IsValidIndex(3) ? SkillMontages[3].Get() : nullptr;
}

float USparrowSkillComponent::GetBuffRemaining() const
{
	return GetWorld() ? static_cast<float>(FMath::Max(0.0, BuffDeadline - GetWorld()->GetTimeSeconds())) : 0.0f;
}

void USparrowSkillComponent::ExpireInnerFire()
{
	BuffDeadline = 0.0;
	if (BuffEffect.IsValid())
	{
		BuffEffect->DestroyComponent();
	}
	BuffEffect.Reset();
}

int32 USparrowSkillComponent::GetRelentlessStacks(AActor* Target) const
{
	if (!GetWorld() || !IsLivingTarget(Target))
	{
		return 0;
	}
	const FRelentlessState* State = RelentlessTargets.Find(TWeakObjectPtr<AActor>(Target));
	return State && GetWorld()->GetTimeSeconds() < State->Deadline ? State->Stacks : 0;
}

float USparrowSkillComponent::ModifyArrowDamageAndRecordHit(AActor* Target, float BaseDamage)
{
	const int32 ExistingStacks = GetRelentlessStacks(Target);
	RecordRelentlessHit(Target);
	return FMath::Max(0.0f, BaseDamage) * (1.0f + ExistingStacks * RelentlessDamagePerStack);
}

void USparrowSkillComponent::RecordRelentlessHit(AActor* Target)
{
	if (!GetWorld() || !Character.IsValid() || !IsLivingTarget(Target) || Target == Character.Get() || !Target->CanBeDamaged())
	{
		return;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	FRelentlessState& State = RelentlessTargets.FindOrAdd(TWeakObjectPtr<AActor>(Target));
	State.Stacks = FMath::Min(Now < State.Deadline ? State.Stacks + 1 : 1, RelentlessLimit);
	State.Deadline = Now + RelentlessDuration;
	LastRelentlessTarget = Target;
	if (!GetWorld()->GetTimerManager().IsTimerActive(RelentlessCleanupTimer))
	{
		GetWorld()->GetTimerManager().SetTimer(RelentlessCleanupTimer, this, &USparrowSkillComponent::CleanupRelentless, 0.5f, true);
	}
}

void USparrowSkillComponent::CleanupRelentless()
{
	const double Now = GetWorld()->GetTimeSeconds();
	for (auto It = RelentlessTargets.CreateIterator(); It; ++It)
	{
		if (!IsLivingTarget(It.Key().Get()) || Now >= It.Value().Deadline)
		{
			It.RemoveCurrent();
		}
	}
	if (RelentlessTargets.IsEmpty())
	{
		GetWorld()->GetTimerManager().ClearTimer(RelentlessCleanupTimer);
		LastRelentlessTarget.Reset();
	}
}

void USparrowSkillComponent::StartHail(const FVector& Location, float DamageScale, bool bEchoAllowed)
{
	if (!GetWorld() || !Character.IsValid() || HailZones.Num() >= MaxHailZones) { return; }
	const bool bAscended = bEchoAllowed && GetAscensionRemaining() > 0.0f;
	const float ZoneRadius = bAscended ? AscendedHailRadius : HailRadius;
	const IConsoleVariable* RainDesign = IConsoleManager::Get().FindConsoleVariable(TEXT("Sparrow.DesignIngame.Q"));
	const bool bNewRain = bEchoAllowed && RainDesign && RainDesign->GetInt() == 6;
	if (bAscended || bNewRain)
	{
		FActorSpawnParameters Spawn;
		Spawn.Owner = Character.Get();
		Spawn.ObjectFlags |= RF_Transient;
		Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		ASparrowAscendedShotFX* Visual = GetWorld()->SpawnActor<ASparrowAscendedShotFX>(Location, FRotator::ZeroRotator, Spawn);
		if (Visual && Visual->InitializeRain(Character.Get(), Location, HailDuration, ZoneRadius, true, bAscended)) { VisualProxies.Add(Visual); }
		else if (Visual) { Visual->Destroy(); }
	}
	FHailZone Zone;
	Zone.Id = ++HailGeneration;
	Zone.Location = Location;
	Zone.Deadline = GetWorld()->GetTimeSeconds() + HailDuration;
	Zone.DamagePerPulse = Skills[0].Damage * FMath::Clamp(DamageScale, 0.0f, 1.0f) / HailPulseCount;
	Zone.Radius = ZoneRadius;
	Zone.bAscended = bAscended;
	Zone.PulsesRemaining = HailPulseCount;
	Zone.bMirrored = !bEchoAllowed;
	// 인스턴스 scale은 입자 크기만 조절한다. 강우 반경 300/240은 transient 복제본의 Cylinder가 소유한다.
	UParticleSystemComponent* Rain = bAscended || bNewRain ? nullptr : SpawnEffect(RuntimeHailEffect ? RuntimeHailEffect.Get() : Skills[0].ImpactEffect.Get(),
		Location, FRotator::ZeroRotator, HailDuration, false, bEchoAllowed ? 0.78f : 0.42f);
	if (Rain)
	{
		Rain->ComponentTags.Add(TEXT("SparrowHailFX"));
	}
	Zone.Effects.Add(Rain);
	if (HailRangeMesh && bEchoAllowed)
	{
		UMaterialInterface* RangeMaterial = HailRangeMaterial.LoadSynchronous();
		FActorSpawnParameters Parameters;
		Parameters.Owner = Character.Get();
		Parameters.ObjectFlags |= RF_Transient;
		Parameters.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		AStaticMeshActor* Indicator = RangeMaterial ? GetWorld()->SpawnActor<AStaticMeshActor>(
			Location + FVector(0.0f, 0.0f, 4.0f), FRotator::ZeroRotator, Parameters) : nullptr;
		if (Indicator)
		{
			Indicator->SetCanBeDamaged(false);
			Indicator->SetActorEnableCollision(false);
			Indicator->Tags.Append({TEXT("SparrowSkillFXProxy"), TEXT("SparrowHailArea"), TEXT("SparrowHailRangeIndicator")});
			UStaticMeshComponent* Mesh = Indicator->GetStaticMeshComponent();
			Mesh->SetMobility(EComponentMobility::Movable);
			Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			Mesh->SetGenerateOverlapEvents(false);
			Mesh->SetCanEverAffectNavigation(false);
			Mesh->SetStaticMesh(HailRangeMesh);
			Mesh->SetCastShadow(false);
			// 기존 황금 원환의 중심선은 UV 반경 .36이다. 게임 판정 반경 300에 중심선을 맞춘다.
			const float Scale = Zone.Radius / (100.0f * 0.36f);
			Mesh->SetWorldScale3D(FVector(Scale, Scale, 1.0f));
			UMaterialInstanceDynamic* Material = Mesh->CreateDynamicMaterialInstance(0, RangeMaterial);
			if (Material)
			{
				Material->SetScalarParameterValue(TEXT("Envelope"), 0.28f);
				Zone.RangeIndicatorMaterial = Material;
			}
			Indicator->SetLifeSpan(HailDuration);
			Zone.RangeIndicator = Indicator;
			VisualProxies.RemoveAll([](const TWeakObjectPtr<AActor>& Proxy) { return !Proxy.IsValid(); });
			VisualProxies.Add(Indicator);
		}
	}
	const uint32 Id = Zone.Id;
	GetWorld()->GetTimerManager().SetTimer(Zone.Timer, FTimerDelegate::CreateWeakLambda(this, [this, Id]()
	{
		PulseHail(Id);
	}), bAscended ? ASparrowAscendedShotFX::RainContactInterval : HailInterval, true,
		bAscended ? ASparrowAscendedShotFX::RainContactDelay : HailInterval);
	HailZones.Add(MoveTemp(Zone));
	if (!bAscended) { PulseHail(Id); }
	if (bEchoAllowed) { EchoHail(Location); }
}

void USparrowSkillComponent::SpawnHailLaunch(const FVector* OriginOverride)
{
	if (!GetWorld() || !Character.IsValid() || !HailProjectile)
	{
		return;
	}
	const FVector Origin = OriginOverride ? *OriginOverride : GetArrowOrigin();
	if (!OriginOverride && AscendedBowFX.IsValid()) { AscendedBowFX->Pulse(Origin, Character->GetActorForwardVector()); }
	SpawnEffect(SparrowPresentation::GetReleaseShards(), Origin, FRotator(75.0f, Character->GetActorRotation().Yaw, 0.0f),
		0.30f, false, OriginOverride ? 0.50f : 1.15f);
	SpawnEffect(PrimaryMuzzle, Origin, FRotator(90.0f, 0.0f, 0.0f), 0.19f, false, OriginOverride ? 0.45f : 0.80f);
	// 카메라용 굴절 메시를 지면 캐릭터 앞에 띄우지 않고 원본 금색 발사체만 사용한다.
	// 원본 RibbonTrail은 이동하는 발사체용이다. 지면 효과와 분리한 순수 표현용 발사체다.
	FActorSpawnParameters Parameters;
	Parameters.Owner = Character.Get();
	Parameters.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	AActor* Proxy = GetWorld()->SpawnActor<AActor>(Origin, FRotator(90.0f, 0.0f, 0.0f), Parameters);
	if (!Proxy)
	{
		return;
	}
	Proxy->SetCanBeDamaged(false);
	UParticleSystemComponent* Particle = NewObject<UParticleSystemComponent>(Proxy);
	Particle->bAutoActivate = false;
	Particle->SetTemplate(HailProjectile);
	Particle->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Particle->ComponentTags.Add(TEXT("SparrowFX"));
	Particle->ComponentTags.Add(TEXT("SparrowSkillFX"));
	Particle->bOverrideLODMethod = true;
	Particle->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
	Proxy->SetRootComponent(Particle);
	Proxy->AddInstanceComponent(Particle);
	Particle->RegisterComponent();
	Particle->SetWorldLocationAndRotation(Origin, FRotator(90.0f, 0.0f, 0.0f));
	Particle->SetLODLevel(0);
	Particle->ActivateSystem(true);
	Particle->SetLODLevel(0);
	UProjectileMovementComponent* Movement = NewObject<UProjectileMovementComponent>(Proxy);
	Proxy->AddInstanceComponent(Movement);
	Movement->SetUpdatedComponent(Particle);
	Movement->ProjectileGravityScale = 0.0f;
	Movement->bRotationFollowsVelocity = true;
	Movement->bInitialVelocityInLocalSpace = false;
	Movement->Velocity = FVector::UpVector * 2400.0f;
	Movement->RegisterComponent();
	Proxy->SetLifeSpan(0.65f);
	OwnedEffects.RemoveAll([](const TWeakObjectPtr<UParticleSystemComponent>& Item) { return !Item.IsValid(); });
	OwnedEffects.Add(Particle);
	VisualProxies.RemoveAll([](const TWeakObjectPtr<AActor>& Item) { return !Item.IsValid(); });
	VisualProxies.Add(Proxy);
}

void USparrowSkillComponent::PulseHail(uint32 ZoneId)
{
	const int32 Index = HailZones.IndexOfByPredicate([ZoneId](const FHailZone& Zone) { return Zone.Id == ZoneId; });
	if (Index == INDEX_NONE || !Character.IsValid() || !GetWorld())
	{
		return;
	}
	FHailZone& Zone = HailZones[Index];
	if (GetWorld()->GetTimeSeconds() >= Zone.Deadline || Zone.PulsesRemaining <= 0)
	{
		RemoveHail(ZoneId);
		return;
	}
	--Zone.PulsesRemaining;
	const FVector Location = Zone.Location;
	const float Damage = Zone.DamagePerPulse;
	if (!Zone.bMirrored && !Zone.bAscended)
	{
		// 착탄을 범위 안의 두 지점에 교대로 배치하고 마지막에는 원본 파열로 한 번 묶는다.
		const bool bFirstPulse = Zone.PulsesRemaining == HailPulseCount - 1;
		const bool bFinalPulse = Zone.PulsesRemaining == 0;
		const float Angle = (HailPulseCount - Zone.PulsesRemaining) * 137.5f;
		const FVector Impact = bFirstPulse ? Location : Location +
			FVector(150.0f, 0.0f, 0.0f).RotateAngleAxis(Angle, FVector::UpVector);
		SpawnEffect(PrimaryWorldHit, Impact + FVector(0.0f, 0.0f, 8.0f), FRotator::ZeroRotator,
			0.48f, false, bFirstPulse ? 0.85f : 0.58f);
		const FVector Secondary = Location + FVector(205.0f, 0.0f, 0.0f).RotateAngleAxis(Angle + 155.0f, FVector::UpVector);
		SpawnEffect(PrimaryWorldHit, Secondary + FVector(0.0f, 0.0f, 8.0f), FRotator::ZeroRotator,
			0.38f, false, 0.46f);
		if (bFinalPulse)
		{
			SpawnEffect(UltimateWorldHit, Location + FVector(0.0f, 0.0f, 20.0f), FRotator::ZeroRotator,
				0.65f, false, 0.85f);
		}
	}
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_Pawn);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	FCollisionQueryParams Query(SCENE_QUERY_STAT(SparrowHailDamage), false, Character.Get());
	TArray<FOverlapResult> Overlaps;
	GetWorld()->OverlapMultiByObjectType(Overlaps, Location + FVector(0.0f, 0.0f, 80.0f), FQuat::Identity,
		Objects, FCollisionShape::MakeSphere(Zone.Radius), Query);
	TSet<TWeakObjectPtr<AActor>> HitActors;
	for (const FOverlapResult& Overlap : Overlaps)
	{
		AActor* Target = Overlap.GetActor();
		const TWeakObjectPtr<AActor> WeakTarget(Target);
		if (!IsLivingTarget(Target) || Target == Character.Get() || !Target->CanBeDamaged() ||
			(!Target->IsA<APawn>() && !Target->IsA<AKwangTrainingDummy>()) || HitActors.Contains(WeakTarget))
		{
			continue;
		}
		const FVector TargetLocation = Target->GetActorLocation();
		const FVector Delta = TargetLocation - Location;
		if (Delta.SizeSquared2D() > FMath::Square(Zone.Radius) || FMath::Abs(Delta.Z) > HailHeight ||
			!HasWorldLineOfSight(Location + FVector(0.0f, 0.0f, 70.0f), TargetLocation, Target))
		{
			continue;
		}
		HitActors.Add(WeakTarget);
		if (!Zone.bMirrored) { RecordRelentlessHit(Target); }
		UGameplayStatics::ApplyDamage(Target, Damage, Character->GetController(), Character.Get(), nullptr);
	}
}

void USparrowSkillComponent::RemoveHail(uint32 ZoneId)
{
	const int32 Index = HailZones.IndexOfByPredicate([ZoneId](const FHailZone& Zone) { return Zone.Id == ZoneId; });
	if (Index == INDEX_NONE)
	{
		return;
	}
	GetWorld()->GetTimerManager().ClearTimer(HailZones[Index].Timer);
	if (HailZones[Index].RangeIndicator.IsValid())
	{
		HailZones[Index].RangeIndicator->Destroy();
	}
	for (const TWeakObjectPtr<UParticleSystemComponent>& Effect : HailZones[Index].Effects)
	{
		if (Effect.IsValid())
		{
			Effect->DestroyComponent();
		}
	}
	HailZones.RemoveAtSwap(Index);
	SetComponentTickEnabled(bCasting || !HailZones.IsEmpty());
}

UParticleSystemComponent* USparrowSkillComponent::SpawnEffect(UParticleSystem* Effect, const FVector& Location,
	const FRotator& Rotation, float Lifetime, bool bAttach, float Scale, FName Socket)
{
	if (!GetWorld() || !Effect)
	{
		return nullptr;
	}
	USkeletalMeshComponent* Mesh = Character.IsValid() ? Character->GetMesh() : nullptr;
	const bool bUseSocket = bAttach && Mesh && Socket != NAME_None && Mesh->DoesSocketExist(Socket);
	const FVector EffectLocation = bUseSocket ? Mesh->GetSocketLocation(Socket) : Location;
	const FRotator EffectRotation = bUseSocket ? Mesh->GetSocketRotation(Socket) : Rotation;
	UParticleSystemComponent* Particle = UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), Effect,
		EffectLocation, EffectRotation, FVector(Scale), true, EPSCPoolMethod::None, false);
	if (Particle)
	{
		Particle->ComponentTags.Add(TEXT("SparrowFX"));
		Particle->ComponentTags.Add(TEXT("SparrowSkillFX"));
		Particle->bOverrideLODMethod = true;
		Particle->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
		Particle->SetLODLevel(0);
		if (Character.IsValid())
		{
			Particle->SetActorParameter(TEXT("BoneSocketActor"), Character.Get());
			if (bAttach && Mesh)
			{
				// AtLocation의 absolute 위치/회전을 해제해 부착 FX가 캐릭터를 따라가게 한다. 월드 크기는 유지한다.
				Particle->SetAbsolute(false, false, true);
				Particle->AttachToComponent(Mesh, bUseSocket ?
					FAttachmentTransformRules::SnapToTargetNotIncludingScale : FAttachmentTransformRules::KeepWorldTransform,
					bUseSocket ? Socket : NAME_None);
			}
		}
		Particle->ActivateSystem(true);
		Particle->SetLODLevel(0);
		if (CVarSparrowHailDiagnostics.GetValueOnGameThread() != 0 &&
			(Effect == RuntimeHailEffect || Effect == Skills[0].ImpactEffect))
		{
			UE_LOG(LogTemp, Display, TEXT("SparrowQDiagnostic PSC=%s template=%s runtime=%s runtime_match=%d emitters=%d"),
				*Particle->GetPathName(), *GetPathNameSafe(Particle->Template.Get()), *GetPathNameSafe(RuntimeHailEffect.Get()),
				Particle->Template == RuntimeHailEffect, Particle->EmitterInstances.Num());
			for (FParticleEmitterInstance* Instance : Particle->EmitterInstances)
			{
				if (!Instance || !Instance->SpriteTemplate || !Instance->CurrentLODLevel) { continue; }
				UParticleEmitter* Emitter = Instance->SpriteTemplate;
				UParticleLODLevel* LOD = Instance->CurrentLODLevel;
				UParticleModuleTypeDataMesh* MeshType = Cast<UParticleModuleTypeDataMesh>(LOD->TypeDataModule);
				UE_LOG(LogTemp, Display, TEXT("SparrowQDiagnostic emitter=%s enabled=%d lod=%d required=%s type=%s override=%d mesh=%s cached_materials=%d"),
					*Emitter->GetEmitterName().ToString(), LOD->bEnabled, Instance->CurrentLODLevelIndex,
					*GetPathNameSafe(LOD->RequiredModule ? LOD->RequiredModule->Material.Get() : nullptr),
					*GetNameSafe(LOD->TypeDataModule), MeshType ? MeshType->bOverrideMaterial : false,
					*GetPathNameSafe(MeshType ? MeshType->Mesh.Get() : nullptr), Emitter->MeshMaterials.Num());
				for (UParticleModule* Module : LOD->Modules)
				{
					if (UParticleModuleMeshMaterial* MaterialModule = Cast<UParticleModuleMeshMaterial>(Module))
					{
						for (int32 Index = 0; Index < MaterialModule->MeshMaterials.Num(); ++Index)
						{
							UE_LOG(LogTemp, Display, TEXT("SparrowQDiagnostic emitter=%s module_enabled=%d slot=%d material=%s"),
								*Emitter->GetEmitterName().ToString(), MaterialModule->bEnabled, Index,
								*GetPathNameSafe(MaterialModule->MeshMaterials[Index].Get()));
						}
					}
				}
				if (MeshType)
				{
					TArray<UMaterialInterface*, TInlineAllocator<2>> RenderMaterials;
					static_cast<FParticleMeshEmitterInstance*>(Instance)->GetMeshMaterials(RenderMaterials, LOD, false);
					for (int32 Index = 0; Index < RenderMaterials.Num(); ++Index)
					{
						UE_LOG(LogTemp, Display, TEXT("SparrowQDiagnostic emitter=%s render_slot=%d resolved_material=%s"),
							*Emitter->GetEmitterName().ToString(), Index, *GetPathNameSafe(RenderMaterials[Index]));
					}
				}
			}
		}
		FTimerHandle Cleanup;
		GetWorld()->GetTimerManager().SetTimer(Cleanup, FTimerDelegate::CreateWeakLambda(Particle, [Particle]()
		{
			Particle->DestroyComponent();
		}), FMath::Max(0.05f, Lifetime), false);
		OwnedEffects.RemoveAll([](const TWeakObjectPtr<UParticleSystemComponent>& Item) { return !Item.IsValid(); });
		OwnedEffects.Add(Particle);
	}
	return Particle;
}

void USparrowSkillComponent::StopCastEffects()
{
	for (const TWeakObjectPtr<UParticleSystemComponent>& Effect : CastEffects)
	{
		if (Effect.IsValid())
		{
			Effect->DestroyComponent();
		}
	}
	CastEffects.Reset();
}

void USparrowSkillComponent::OnMontageEnded(UAnimMontage* Montage, bool bInterrupted, uint32 Generation)
{
	if (bCasting && Generation == CastGeneration && Montage == ActiveMontage)
	{
		FinishSkill();
	}
}

void USparrowSkillComponent::OnMontageBlendingOut(UAnimMontage* Montage, bool bInterrupted, uint32 Generation)
{
	if (bInterrupted && bCasting && Generation == CastGeneration && Montage == ActiveMontage)
	{
		FinishSkill();
	}
}

void USparrowSkillComponent::FinishSkill(float BlendOutSeconds)
{
	if (ArsenalStudyFX.IsValid()) { ArsenalStudyFX->FinishCast(); }
	ArsenalStudyFX.Reset();
	if (AscendedBowFX.IsValid()) { AscendedBowFX->FinishCast(); }
	AscendedBowFX.Reset();
	if (HolyBow.IsValid()) { HolyBow->FadeOut(); }
	HolyBow.Reset();
	if (MultishotBowTint.IsValid()) { MultishotBowTint->Destroy(); }
	MultishotBowTint.Reset();
	CancelExtraCast();
	if (RapidBowEffect.IsValid()) { RapidBowEffect->DestroyComponent(); }
	RapidBowEffect.Reset();
	if (RapidBowFeedback.IsValid()) { RapidBowFeedback->Destroy(); }
	RapidBowFeedback.Reset();
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
		GetWorld()->GetTimerManager().ClearTimer(MultishotTimer);
		GetWorld()->GetTimerManager().ClearTimer(PiercingTimer);
	}
	StopCastEffects();
	if (CastAnimInstance.IsValid())
	{
		CastAnimInstance->Montage_Stop(BlendOutSeconds >= 0.0f ? BlendOutSeconds :
			(ActiveSkillIndex == 1 ? 0.06f : (ActiveSkillIndex == 9 ? 0.24f : 0.12f)), ActiveMontage);
		CastAnimInstance->SetRootMotionMode(SavedRootMotionMode);
	}
	if (Character.IsValid() && Character->GetCharacterMovement())
	{
		Character->GetCharacterMovement()->bOrientRotationToMovement = bSavedOrientRotation;
	}
	CastAnimInstance.Reset();
	ActiveMontage = nullptr;
	ActiveSkillIndex = INDEX_NONE;
	SetComponentTickEnabled(!HailZones.IsEmpty());
}

void USparrowSkillComponent::CancelSkill()
{
	// 이미 방출한 화살·화살비와 활성화한 버프는 시전 잠금과 수명이 독립적이다.
	CancelSanctuaryCast();
	FinishSkill();
	if (BackstepEcho.IsValid()) { BackstepEcho->Destroy(); }
	BackstepEcho.Reset();
	if (GoldRoll.IsValid()) { GoldRoll->Destroy(); }
	GoldRoll.Reset();
}

void USparrowSkillComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	if (GetWorld())
	{
		const double Now = GetWorld()->GetTimeSeconds();
		for (const FHailZone& Zone : HailZones)
		{
			if (Zone.RangeIndicatorMaterial.IsValid())
			{
				// 판정 반경과 종료 시각은 유지하고, 마지막 0.4초만 같은 크기로 흐리게 사라진다.
				const float Remaining = static_cast<float>(Zone.Deadline - Now);
				const float Fade = FMath::SmoothStep(0.0f, 1.0f, Remaining / HailIndicatorFadeSeconds);
				Zone.RangeIndicatorMaterial->SetScalarParameterValue(TEXT("Envelope"), 0.28f * Fade);
			}
		}
	}
	if (bCasting && (!ValidateCastState() || ((ActiveSkillIndex == 2 || ActiveSkillIndex == 3) && HasRapidShotMovePress())))
	{
		FinishSkill();
	}
}

void USparrowSkillComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	CleanupSanctuarySkills();
	if (GoldRoll.IsValid()) { GoldRoll->Destroy(); }
	GoldRoll.Reset();
	if (BackstepEcho.IsValid()) { BackstepEcho->Destroy(); }
	BackstepEcho.Reset();
	FinishSkill();
	CleanupExtraSkills();
	ExpireInnerFire();
	if (GetWorld())
	{
		GetWorld()->GetTimerManager().ClearTimer(ActionTimer);
		GetWorld()->GetTimerManager().ClearTimer(RecoveryTimer);
		GetWorld()->GetTimerManager().ClearTimer(MultishotTimer);
		GetWorld()->GetTimerManager().ClearTimer(PiercingTimer);
		GetWorld()->GetTimerManager().ClearTimer(BuffTimer);
		GetWorld()->GetTimerManager().ClearTimer(RelentlessCleanupTimer);
		for (FHailZone& Zone : HailZones)
		{
			GetWorld()->GetTimerManager().ClearTimer(Zone.Timer);
		}
	}
	for (const TWeakObjectPtr<ASparrowArrow>& Arrow : OwnedArrows)
	{
		if (Arrow.IsValid())
		{
			Arrow->Destroy();
		}
	}
	for (const TWeakObjectPtr<AActor>& Proxy : VisualProxies)
	{
		if (Proxy.IsValid())
		{
			Proxy->Destroy();
		}
	}
	for (const TWeakObjectPtr<UParticleSystemComponent>& Effect : OwnedEffects)
	{
		if (Effect.IsValid())
		{
			Effect->DestroyComponent();
		}
	}
	HailZones.Reset();
	SetComponentTickEnabled(false);
	RelentlessTargets.Reset();
	OwnedArrows.Reset();
	VisualProxies.Reset();
	OwnedEffects.Reset();
	LastRelentlessTarget.Reset();
	bEnabled = false;
	Super::EndPlay(EndPlayReason);
}
