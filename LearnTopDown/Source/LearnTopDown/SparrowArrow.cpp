#include "SparrowArrow.h"
#include "SparrowHarmonyFX.h"
#include "SparrowGatherShot.h"
#include "SparrowHolyBow.h"
#include "SparrowArsenalStudyFX.h"
#include "SparrowSharpImpact.h"
#include "SparrowAscendedShotFX.h"
#include "SparrowFeatherTrail.h"
#include "SparrowSanctuary.h"
#include "Camera/PlayerCameraManager.h"

#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Distributions/DistributionFloatConstant.h"
#include "Distributions/DistributionFloatUniform.h"
#include "Distributions/DistributionVectorUniform.h"
#include "Engine/StaticMesh.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "KwangTrainingDummy.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleEmitter.h"
#include "Particles/ParticleLODLevel.h"
#include "Particles/ParticleModuleRequired.h"
#include "Particles/Color/ParticleModuleColor.h"
#include "Particles/Light/ParticleModuleLight.h"
#include "Particles/Lifetime/ParticleModuleLifetime.h"
#include "Particles/Size/ParticleModuleSize.h"
#include "Particles/Spawn/ParticleModuleSpawn.h"
#include "Particles/Velocity/ParticleModuleVelocity.h"
#include "Particles/ParticleSystemComponent.h"
#include "SparrowSkillComponent.h"
#include "TopDownCombatCharacter.h"
#include "SparrowSkillVisual.h"
#include "SparrowPiercingLance.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	int32 FDesignStyleFor(const AActor* Actor)
	{
		if (Actor->ActorHasTag(TEXT("SparrowFDesign6"))) { return 6; }
		if (Actor->ActorHasTag(TEXT("SparrowFDesign1"))) { return 1; }
		if (Actor->ActorHasTag(TEXT("SparrowFDesign2"))) { return 2; }
		if (Actor->ActorHasTag(TEXT("SparrowFDesign3"))) { return 3; }
		if (Actor->ActorHasTag(TEXT("SparrowFDesign4"))) { return 4; }
		if (Actor->ActorHasTag(TEXT("SparrowFDesign5"))) { return 5; }
		return 0;
	}
	int32 FDesignPieces(int32 Style) { return Style == 6 ? 24 : Style == 5 ? 40 : Style == 1 || Style == 4 ? 16 : Style == 3 ? 18 : 0; }
	int32 FDesignRibbons(int32 Style) { return Style == 6 ? 4 : 2; }

	void SetFlowScalar(UObject* Outer, FRawDistributionFloat& Value, float Constant)
	{
		UDistributionFloatConstant* Distribution = NewObject<UDistributionFloatConstant>(Outer, NAME_None, RF_Transient);
		Distribution->Constant = Constant;
		Distribution->bCanBeBaked = false;
		Distribution->bIsDirty = false;
		Value = FRawDistributionFloat();
		Value.Distribution = Distribution;
	}

	void SetFlowRange(UObject* Outer, FRawDistributionVector& Value, const FVector& Min, const FVector& Max)
	{
		UDistributionVectorUniform* Distribution = NewObject<UDistributionVectorUniform>(Outer, NAME_None, RF_Transient);
		Distribution->Min = Min;
		Distribution->Max = Max;
		Distribution->bCanBeBaked = false;
		Distribution->bIsDirty = false;
		Value = FRawDistributionVector();
		Value.Distribution = Distribution;
	}

	UParticleSystem* GetChargedImpact(UParticleSystem* Source)
	{
		static TWeakObjectPtr<UParticleSystem> Cached;
		if (Cached.IsValid()) { return Cached.Get(); }
		if (!Source) { return nullptr; }
		UParticleSystem* Runtime = DuplicateObject<UParticleSystem>(Source, GetTransientPackage(),
			MakeUniqueObjectName(GetTransientPackage(), UParticleSystem::StaticClass(), TEXT("P_SparrowChargedImpactRuntime")));
		Runtime->SetFlags(RF_Transient);
		Runtime->ClearFlags(RF_Public | RF_Standalone);
		// W 전용 복제본: 원본 메시 화염/DP/flipbook은 유지하고 핵-파열-불티의 시간을 분리한다.
		Runtime->Emitters.RemoveAll([](UParticleEmitter* Emitter)
		{
			return !Emitter || Emitter->GetEmitterName() == TEXT("Particle Emitter") ||
				Emitter->GetEmitterName() == TEXT("AddFlare");
		});
		for (UParticleEmitter* Emitter : Runtime->Emitters)
		{
			if (!Emitter->IsIn(Runtime)) { return nullptr; }
			const FName Name = Emitter->GetEmitterName();
			const bool bFlame = Name == TEXT("Main Flames");
			const bool bFlare = Name == TEXT("Flare");
			const bool bWisp = Name == TEXT("Wisps");
			const int32 Count = bFlame ? 6 : bFlare ? 1 : bWisp ? 10 :
				Name == TEXT("Sparks") ? 58 : Name == TEXT("Line Burst") ? 60 : 14;
			for (UParticleLODLevel* LOD : Emitter->LODLevels)
			{
				if (!LOD || !LOD->RequiredModule || !LOD->SpawnModule) { continue; }
				LOD->RequiredModule->EmitterLoops = 1;
				LOD->RequiredModule->EmitterDuration = 0.12f;
				LOD->RequiredModule->EmitterDelay = bFlare ? 0.0f : 0.025f;
				LOD->RequiredModule->bKillOnDeactivate = false;
				SetFlowScalar(LOD->SpawnModule, LOD->SpawnModule->Rate, 0.0f);
				LOD->SpawnModule->BurstList.Reset();
				FParticleBurst Burst;
				Burst.Count = Count;
				Burst.CountLow = -1;
				Burst.Time = 0.0f;
				LOD->SpawnModule->BurstList.Add(Burst);
				if (bFlame)
				{
					Burst.Count = 3;
					Burst.Time = 0.045f;
					LOD->SpawnModule->BurstList.Add(Burst);
				}
				LOD->Modules.RemoveAll([](UParticleModule* Module)
				{
					return Module && Module->IsA<UParticleModuleLight>();
				});
				for (UParticleModule* Module : LOD->Modules)
				{
					if (!Module || !Module->IsIn(Runtime)) { return nullptr; }
					if (UParticleModuleLifetime* Life = Cast<UParticleModuleLifetime>(Module))
					{
						UDistributionFloatUniform* Distribution = NewObject<UDistributionFloatUniform>(Life, NAME_None, RF_Transient);
						Distribution->Min = bFlare ? 0.055f : bFlame ? 0.22f : bWisp ? 0.13f : 0.22f;
						Distribution->Max = bFlare ? 0.075f : bFlame ? 0.34f : bWisp ? 0.22f : 0.40f;
						Distribution->bCanBeBaked = false;
						Distribution->bIsDirty = false;
						Life->Lifetime = FRawDistributionFloat();
						Life->Lifetime.Distribution = Distribution;
					}
					else if (UParticleModuleSize* Size = Cast<UParticleModuleSize>(Module))
					{
						if (bFlame) { SetFlowRange(Size, Size->StartSize, FVector(0.25f), FVector(0.50f)); }
						else if (bFlare) { SetFlowRange(Size, Size->StartSize, FVector(65.0f), FVector(85.0f)); }
						else if (bWisp) { SetFlowRange(Size, Size->StartSize, FVector(24.0f), FVector(38.0f)); }
					}
				}
			}
			Emitter->UpdateModuleLists();
		}
		Cached = Runtime;
		return Runtime;
	}

	UParticleSystem* GetMultishotImpact(UParticleSystem* Source)
	{
		static TWeakObjectPtr<UParticleSystem> Cached;
		if (Cached.IsValid()) { return Cached.Get(); }
		if (!Source) { return nullptr; }
		UParticleSystem* Runtime = DuplicateObject<UParticleSystem>(Source, GetTransientPackage(),
			MakeUniqueObjectName(GetTransientPackage(), UParticleSystem::StaticClass(), TEXT("P_SparrowMultishotImpactRuntime")));
		Runtime->SetFlags(RF_Transient);
		Runtime->ClearFlags(RF_Public | RF_Standalone);
		// 큰 Flare/광원만 제외한다. 원본의 화염 메시, Wisps, 불티와 선형 파열은 함께 유지한다.
		Runtime->Emitters.RemoveAll([](UParticleEmitter* Emitter)
		{
			if (!Emitter) { return true; }
			const FString Name = Emitter->GetEmitterName().ToString();
			// 원본의 이름 없는 첫 emitter는 inventory에서 확인한 LightsOnly 전용층이다.
			return Name.Contains(TEXT("Flare"), ESearchCase::IgnoreCase) ||
				Name.Contains(TEXT("Light"), ESearchCase::IgnoreCase) || Name == TEXT("Particle Emitter");
		});
		if (Runtime->Emitters.IsEmpty()) { return nullptr; }
		for (UParticleEmitter* Emitter : Runtime->Emitters)
		{
			if (!Emitter->IsIn(Runtime)) { return nullptr; }
			for (UParticleLODLevel* LOD : Emitter->LODLevels)
			{
				if (!LOD || !LOD->RequiredModule || !LOD->SpawnModule) { continue; }
				LOD->RequiredModule->EmitterLoops = 1;
				LOD->RequiredModule->bKillOnDeactivate = false;
				LOD->Modules.RemoveAll([](UParticleModule* Module)
				{
					return Module && Module->IsA<UParticleModuleLight>();
				});
				for (UParticleModule* Module : LOD->Modules)
				{
					if (!Module || !Module->IsIn(Runtime)) { return nullptr; }
					if (UParticleModuleLifetime* Life = Cast<UParticleModuleLifetime>(Module))
					{
						UDistributionFloatUniform* Distribution = NewObject<UDistributionFloatUniform>(Life, NAME_None, RF_Transient);
						Distribution->Min = 0.12f;
						Distribution->Max = 0.20f;
						Distribution->bCanBeBaked = false;
						Distribution->bIsDirty = false;
						Life->Lifetime = FRawDistributionFloat();
						Life->Lifetime.Distribution = Distribution;
					}
				}
			}
			Emitter->UpdateModuleLists();
		}
		Cached = Runtime;
		return Runtime;
	}

	UParticleSystem* GetSharpBurstImpact()
	{
		static TWeakObjectPtr<UParticleSystem> Cached;
		if (Cached.IsValid()) { return Cached.Get(); }
		UParticleSystem* Source = LoadObject<UParticleSystem>(nullptr,
			TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Ultimate/FX/P_Sparrow_UltHit.P_Sparrow_UltHit"));
		if (!Source) { return nullptr; }
		UParticleSystem* Copy = DuplicateObject<UParticleSystem>(Source, GetTransientPackage(),
			MakeUniqueObjectName(GetTransientPackage(), UParticleSystem::StaticClass(), TEXT("P_SparrowSharpImpactRuntime")));
		Copy->SetFlags(RF_Transient);
		Copy->ClearFlags(RF_Public | RF_Standalone);
		// S의 실제 명중 한 번에만 짧은 핵·가는 파열·작은 원본 화염 질감을 겹친다.
		Copy->Emitters.RemoveAll([](UParticleEmitter* Emitter)
		{
			if (!Emitter) { return true; }
			const FName Name = Emitter->GetEmitterName();
			return Name != TEXT("Flare") && Name != TEXT("Main Flames") &&
				Name != TEXT("Line Burst") && Name != TEXT("Sparks") && Name != TEXT("SparkTrailHeads");
		});
		for (UParticleEmitter* Emitter : Copy->Emitters)
		{
			if (!Emitter->IsIn(Copy)) { return nullptr; }
			const FName Name = Emitter->GetEmitterName();
			const bool bCore = Name == TEXT("Flare");
			const bool bFlame = Name == TEXT("Main Flames");
			for (UParticleLODLevel* LOD : Emitter->LODLevels)
			{
				if (!LOD || !LOD->RequiredModule || !LOD->SpawnModule) { continue; }
				LOD->RequiredModule->EmitterLoops = 1;
				LOD->RequiredModule->EmitterDuration = .08f;
				LOD->RequiredModule->EmitterDelay = 0.0f;
				LOD->RequiredModule->EmitterDelayLow = 0.0f;
				LOD->RequiredModule->bEmitterDelayUseRange = false;
				SetFlowScalar(LOD->SpawnModule, LOD->SpawnModule->Rate, 0.0f);
				LOD->SpawnModule->BurstList.Reset();
				FParticleBurst Burst;
				Burst.Count = bCore ? 1 : bFlame ? 3 : Name == TEXT("Line Burst") ? 26 : 14;
				Burst.CountLow = -1;
				Burst.Time = 0.0f;
				LOD->SpawnModule->BurstList.Add(Burst);
				LOD->Modules.RemoveAll([](UParticleModule* Module) { return Module && Module->IsA<UParticleModuleLight>(); });
				for (UParticleModule* Module : LOD->Modules)
				{
					if (!Module || !Module->IsIn(Copy)) { return nullptr; }
					if (UParticleModuleLifetime* Life = Cast<UParticleModuleLifetime>(Module))
					{
						SetFlowScalar(Life, Life->Lifetime, bCore ? .075f : bFlame ? .13f : .17f);
					}
					else if (UParticleModuleSize* Size = Cast<UParticleModuleSize>(Module))
					{
						if (bCore) { SetFlowRange(Size, Size->StartSize, FVector(52.0f), FVector(64.0f)); }
						else if (bFlame) { SetFlowRange(Size, Size->StartSize, FVector(.12f), FVector(.24f)); }
					}
				}
			}
			Emitter->UpdateModuleLists();
		}
		Cached = Copy;
		return Copy;
	}

	UParticleSystem* GetTexturedArrowFlow()
	{
		static TWeakObjectPtr<UParticleSystem> Cached;
		if (Cached.IsValid()) { return Cached.Get(); }
		UParticleSystem* Source = LoadObject<UParticleSystem>(nullptr,
			TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Primary/FX/P_SparrowPrimaryMuzzleFlash.P_SparrowPrimaryMuzzleFlash"));
		if (!Source) { return nullptr; }
		UParticleSystem* Runtime = DuplicateObject<UParticleSystem>(Source, GetTransientPackage(),
			MakeUniqueObjectName(GetTransientPackage(), UParticleSystem::StaticClass(), TEXT("P_SparrowArrowFlowRuntime")));
		Runtime->SetFlags(RF_Transient);
		Runtime->ClearFlags(RF_Public | RF_Standalone);
		// 실조회한 CPU flipbook Wisps만 남긴다. 원본 리본/광원/GPU 불티는 화살마다 복제하지 않는다.
		Runtime->Emitters.RemoveAll([](UParticleEmitter* Emitter)
		{
			return !Emitter || Emitter->GetEmitterName() != TEXT("Wisps");
		});
		if (Runtime->Emitters.Num() != 1) { return nullptr; }
		UParticleEmitter* Emitter = Runtime->Emitters[0];
		if (!Emitter->IsIn(Runtime)) { return nullptr; }
		for (UParticleLODLevel* LOD : Emitter->LODLevels)
		{
			if (!LOD || !LOD->RequiredModule || !LOD->SpawnModule) { continue; }
			LOD->RequiredModule->EmitterDuration = 1.0f;
			LOD->RequiredModule->EmitterLoops = 0;
			LOD->RequiredModule->bUseLocalSpace = false;
			SetFlowScalar(LOD->SpawnModule, LOD->SpawnModule->Rate, 45.0f);
			LOD->SpawnModule->BurstList.Reset();
			FParticleBurst Burst;
			Burst.Count = 3;
			Burst.CountLow = -1;
			Burst.Time = 0.0f;
			LOD->SpawnModule->BurstList.Add(Burst);
			for (UParticleModule* Module : LOD->Modules)
			{
				if (!Module || !Module->IsIn(Runtime)) { return nullptr; }
				if (UParticleModuleLifetime* Life = Cast<UParticleModuleLifetime>(Module))
				{
					UDistributionFloatUniform* Distribution = NewObject<UDistributionFloatUniform>(Life, NAME_None, RF_Transient);
					Distribution->Min = 0.16f;
					Distribution->Max = 0.24f;
					Distribution->bCanBeBaked = false;
					Distribution->bIsDirty = false;
					Life->Lifetime = FRawDistributionFloat();
					Life->Lifetime.Distribution = Distribution;
				}
				else if (UParticleModuleSize* Size = Cast<UParticleModuleSize>(Module))
				{
					SetFlowRange(Size, Size->StartSize, FVector(80.0f), FVector(110.0f));
				}
				else if (UParticleModuleVelocity* Velocity = Cast<UParticleModuleVelocity>(Module))
				{
					SetFlowRange(Velocity, Velocity->StartVelocity, FVector(-600.0f, -35.0f, -25.0f), FVector(-250.0f, 35.0f, 25.0f));
					Velocity->bInWorldSpace = false;
				}
				else if (UParticleModuleColor* Color = Cast<UParticleModuleColor>(Module))
				{
					SetFlowRange(Color, Color->StartColor, FVector(3.5f, 2.8f, 0.55f), FVector(3.5f, 2.8f, 0.55f));
					SetFlowScalar(Color, Color->StartAlpha, 0.5f);
				}
			}
		}
		Emitter->UpdateModuleLists();
		Cached = Runtime;
		return Runtime;
	}

	UParticleSystem* GetChargedArrowAura()
	{
		static TWeakObjectPtr<UParticleSystem> Cached;
		if (Cached.IsValid()) { return Cached.Get(); }
		UParticleSystem* Source = LoadObject<UParticleSystem>(nullptr,
			TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Ultimate/FX/P_Sparrow_UltArrow.P_Sparrow_UltArrow"));
		if (!Source) { return nullptr; }
		UParticleSystem* Runtime = DuplicateObject<UParticleSystem>(Source, GetTransientPackage(),
			MakeUniqueObjectName(GetTransientPackage(), UParticleSystem::StaticClass(), TEXT("P_SparrowChargedAuraRuntime")));
		Runtime->SetFlags(RF_Transient);
		Runtime->ClearFlags(RF_Public | RF_Standalone);
		// Preserve the authored aura mesh, material override and dynamic-parameter erosion together.
		Runtime->Emitters.RemoveAll([](UParticleEmitter* Emitter)
		{
			return !Emitter || (Emitter->GetEmitterName() != TEXT("MeshCoronaLarge") &&
				Emitter->GetEmitterName() != TEXT("SparksTrailing"));
		});
		if (Runtime->Emitters.Num() != 2) { return nullptr; }
		for (UParticleEmitter* Emitter : Runtime->Emitters)
		{
			for (UParticleLODLevel* LOD : Emitter->LODLevels)
			{
				if (!LOD) { continue; }
				LOD->Modules.RemoveAll([](UParticleModule* Module) { return Module && Module->IsA<UParticleModuleLight>(); });
				if (Emitter->GetEmitterName() == TEXT("SparksTrailing"))
				{
					for (UParticleModule* Module : LOD->Modules)
					{
						if (UParticleModuleLifetime* Life = Cast<UParticleModuleLifetime>(Module))
						{
							SetFlowScalar(Life, Life->Lifetime, 0.12f);
						}
					}
				}
			}
			Emitter->UpdateModuleLists();
		}
		Cached = Runtime;
		return Runtime;
	}
}

UParticleSystem* SparrowPresentation::GetMultishotBowGlow()
{
	static TWeakObjectPtr<UParticleSystem> Cached;
	if (Cached.IsValid()) { return Cached.Get(); }
	UParticleSystem* Source = LoadObject<UParticleSystem>(nullptr,
		TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Primary/FX/P_SparrowPrimaryMuzzleFlash.P_SparrowPrimaryMuzzleFlash"));
	if (!Source) { return nullptr; }
	UParticleSystem* Runtime = DuplicateObject<UParticleSystem>(Source, GetTransientPackage(),
		MakeUniqueObjectName(GetTransientPackage(), UParticleSystem::StaticClass(), TEXT("P_SparrowMultishotBowGlowRuntime")));
	Runtime->SetFlags(RF_Transient);
	Runtime->ClearFlags(RF_Public | RF_Standalone);
	// 활 앞의 원본 발광과 입자 결만 복원한다. MuzzleFlare/AirglowFlash/고리는 별도 큰 섬광층이다.
	Runtime->Emitters.RemoveAll([](UParticleEmitter* Emitter)
	{
		if (!Emitter) { return true; }
		const FName Name = Emitter->GetEmitterName();
		return Name != TEXT("MuzzleGlow") && Name != TEXT("Airglow") &&
			Name != TEXT("Wisps") && Name != TEXT("Sparks");
	});
	if (Runtime->Emitters.IsEmpty()) { return nullptr; }
	for (UParticleEmitter* Emitter : Runtime->Emitters)
	{
		if (!Emitter->IsIn(Runtime)) { return nullptr; }
		Emitter->UpdateModuleLists();
	}
	Cached = Runtime;
	return Runtime;
}

UParticleSystem* SparrowPresentation::GetPiercingMuzzle()
{
	static TWeakObjectPtr<UParticleSystem> Cached;
	if (Cached.IsValid()) { return Cached.Get(); }
	UParticleSystem* Source = LoadObject<UParticleSystem>(nullptr,
		TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Primary/FX/P_SparrowPrimaryMuzzleFlash.P_SparrowPrimaryMuzzleFlash"));
	if (!Source) { return nullptr; }
	UParticleSystem* Runtime = DuplicateObject<UParticleSystem>(Source, GetTransientPackage(),
		MakeUniqueObjectName(GetTransientPackage(), UParticleSystem::StaticClass(), TEXT("P_SparrowPiercingMuzzleRuntime")));
	Runtime->SetFlags(RF_Transient);
	Runtime->ClearFlags(RF_Public | RF_Standalone);
	// W는 두 muzzle의 Wisps를 겹치지 않고, 원본의 작은 발광과 불티를 한 번만 방출한다.
	Runtime->Emitters.RemoveAll([](UParticleEmitter* Emitter)
	{
		if (!Emitter) { return true; }
		const FName Name = Emitter->GetEmitterName();
		return Name != TEXT("MuzzleGlow") && Name != TEXT("Airglow") &&
			Name != TEXT("Sparks") && Name != TEXT("MuzzleFlare");
	});
	if (Runtime->Emitters.IsEmpty()) { return nullptr; }
	for (UParticleEmitter* Emitter : Runtime->Emitters)
	{
		if (!Emitter->IsIn(Runtime)) { return nullptr; }
		Emitter->UpdateModuleLists();
	}
	Cached = Runtime;
	return Runtime;
}

ASparrowArrow::ASparrowArrow()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false;
	SetCanBeDamaged(false);
	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
	SetRootComponent(SceneRoot);
	ArrowMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("ArrowMesh"));
	ArrowMesh->SetupAttachment(SceneRoot);
	// 원본 메시의 촉은 로컬 -Z다. 물리 진행 축인 액터 +X에 맞춰 서 있는 화살을 전방으로 눕힌다.
	ArrowMesh->SetRelativeRotation(FRotator(90.0f, 0.0f, 0.0f));
	ArrowMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	ArrowMesh->SetCanEverAffectNavigation(false);
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Mesh(
		TEXT("/Game/ParagonSparrow/FX/Meshes/Heroes/Sparrow/Abilities/SM_Sparrow_Arrow.SM_Sparrow_Arrow"));
	ArrowMesh->SetStaticMesh(Mesh.Object);
	TrailParticle = CreateDefaultSubobject<UParticleSystemComponent>(TEXT("ArrowTrail"));
	TrailParticle->SetupAttachment(SceneRoot);
	TrailParticle->bAutoActivate = false;
	TrailParticle->ComponentTags.Add(TEXT("SparrowSkillFX"));
}

void ASparrowArrow::SetMultishotPresentationScale(float Scale)
{
	// R 실탄에서만 호출한다. 물리 충돌 반경과 공용 S/F 표면에는 영향을 주지 않는다.
	const float NewScale = FMath::Clamp(Scale, .1f, 1.0f);
	const float Ratio = NewScale / MultishotPresentationScale;
	MultishotPresentationScale = NewScale;
	ArrowMesh->SetRelativeScale3D(ArrowMesh->GetRelativeScale3D() * Ratio);
	TInlineComponentArray<UStaticMeshComponent*> Meshes(this);
	for (UStaticMeshComponent* Mesh : Meshes)
	{
		if (!Mesh->ComponentHasTag(TEXT("SparrowMultishotTrail"))) { continue; }
		const FVector Previous = Mesh->GetRelativeScale3D();
		Mesh->SetRelativeScale3D(FVector(Previous.X * Ratio, Previous.Y * Ratio, Previous.Z));
	}
	// 화살 길이·두께 확대와 타격 섬광은 분리한다. 이전 R의 작은 타격 크기는 유지한다.
	ImpactScale = .5f;
}

void ASparrowArrow::EnableRenaissanceMultishot()
{
	if (!SharedVolleyHits) { return; }
	UMaterialInterface* Material = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/Renaissance20261027/M_RenRArrow.M_RenRArrow"));
	if (!Material) { return; }
	ArrowMesh->SetVisibility(false);
	Tags.AddUnique(TEXT("SparrowRenaissanceMultishot"));
	TInlineComponentArray<UStaticMeshComponent*> Meshes(this);
	for (UStaticMeshComponent* Mesh : Meshes)
	{
		if (!Mesh->ComponentHasTag(TEXT("SparrowMultishotTrail"))) { continue; }
		Mesh->SetMaterial(0, Material);
		// InitArrow의 앞뒤·길이 분산을 유지해 발사 파동이 일렬의 부채살로 굳지 않게 한다.
		const float PreviousLength = Mesh->GetRelativeScale3D().X * 100.0f;
		const float VisualLag = FMath::Max(0.0f, -Mesh->GetRelativeLocation().X - PreviousLength * .45f);
		const float Length = PreviousLength * 1.35f;
		const float Width = FMath::Lerp(8.5f, 10.5f, FMath::Clamp((PreviousLength - 30.0f) / 25.0f, 0.0f, 1.0f));
		Mesh->SetRelativeLocation(FVector(-VisualLag - Length * .42f, 0.0f, 0.0f));
		Mesh->SetRelativeScale3D(FVector(Length / 100.0f, Width / 100.0f, 1.0f));
	}
}

void ASparrowArrow::EnableCraftMultishot(int32 ArrowIndex, int32 WaveIndex)
{
	if (!SharedVolleyHits) { return; }
	UMaterialInterface* Material = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/SharpReference20261027/M_CraftRArrow.M_CraftRArrow"));
	if (!Material) { return; }
	ArrowMesh->SetVisibility(false);
	Tags.AddUnique(TEXT("SparrowCraftMultishot"));
	ConfigureImpactPresentation(ASparrowArsenalStudyFX::GetCraftImpactEffect(), .42f, .20f);
	TInlineComponentArray<UStaticMeshComponent*> Meshes(this);
	for (UStaticMeshComponent* Mesh : Meshes)
	{
		if (!Mesh->ComponentHasTag(TEXT("SparrowMultishotTrail"))) { continue; }
		const float Length = Mesh->GetRelativeScale3D().X * 100.0f;
		const float Width = 4.2f + 1.4f * float((ArrowIndex * 7 + WaveIndex * 3) % 5) / 4.0f;
		Mesh->SetMaterial(0, Material);
		Mesh->SetRelativeScale3D(FVector(Length / 100.0f, Width / 100.0f, 1.0f));
	}
}

void ASparrowArrow::EnableFeatherTrail()
{
	if (FeatherTrail.IsValid() || !GetWorld() || !IsValid(GetOwner())) { return; }
	FActorSpawnParameters Spawn;
	Spawn.Owner = GetOwner();
	Spawn.ObjectFlags |= RF_Transient;
	Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	ASparrowFeatherTrail* Visual = GetWorld()->SpawnActor<ASparrowFeatherTrail>(GetActorLocation(), GetActorRotation(), Spawn);
	if (Visual && Visual->Initialize(this, ActorHasTag(TEXT("SparrowAscendedArrow")))) { FeatherTrail = Visual; }
	else if (Visual) { Visual->Destroy(); }
}

void ASparrowArrow::SetVisualWidthScale(float Width)
{
	const float Scale = FMath::Clamp(Width, 1.0f, 3.0f);
	// 화살 메시의 길이 축은 로컬 Z, 궤적의 진행 축은 액터 X다.
	ArrowMesh->SetRelativeScale3D(FVector(Scale, Scale, 1.0f));
	TrailParticle->SetRelativeScale3D(FVector(1.0f, Scale, Scale));
}

void ASparrowArrow::EnableChargedAura()
{
	if (bInitialized)
	{
		if (UParticleSystem* Impact = GetChargedImpact(TargetImpactEffect))
		{
			ConfigureImpactPresentation(Impact, 0.75f, 0.58f);
			Tags.AddUnique(TEXT("SparrowChargedArrow"));
		}
	}
	UParticleSystem* Aura = GetChargedArrowAura();
	if (!bInitialized || !Aura) { return; }
	SetVisualWidthScale(1.1f);
	UParticleSystemComponent* Component = NewObject<UParticleSystemComponent>(this, TEXT("ChargedArrowAura"));
	Component->bAutoActivate = false;
	Component->SetupAttachment(SceneRoot);
	Component->SetTemplate(Aura);
	Component->SetRelativeScale3D(FVector(1.5f, 0.46f, 0.46f));
	Component->bOverrideLODMethod = true;
	Component->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
	Component->ComponentTags.Append({TEXT("SparrowSkillFX"), TEXT("SparrowChargedArrowAura")});
	AddInstanceComponent(Component);
	Component->RegisterComponent();
	Component->SetLODLevel(0);
	Component->ActivateSystem(true);
	Component->SetLODLevel(0);
}

TArray<FName> ASparrowArrow::GetTargetImpactEmitterNames() const
{
	TArray<FName> Names;
	if (TargetImpactEffect)
	{
		for (UParticleEmitter* Emitter : TargetImpactEffect->Emitters)
		{
			if (Emitter) { Names.Add(Emitter->GetEmitterName()); }
		}
	}
	return Names;
}

TArray<FName> ASparrowArrow::GetWorldImpactEmitterNames() const
{
	TArray<FName> Names;
	if (ObstacleImpactEffect)
	{
		for (UParticleEmitter* Emitter : ObstacleImpactEffect->Emitters)
		{
			if (Emitter) { Names.Add(Emitter->GetEmitterName()); }
		}
	}
	return Names;
}

bool ASparrowArrow::HasImpactLightModules() const
{
	for (UParticleSystem* Effect : {TargetImpactEffect.Get(), ObstacleImpactEffect.Get()})
	{
		if (!Effect) { continue; }
		for (UParticleEmitter* Emitter : Effect->Emitters)
		{
			if (!Emitter) { continue; }
			for (UParticleLODLevel* LOD : Emitter->LODLevels)
			{
				if (!LOD) { continue; }
				for (UParticleModule* Module : LOD->Modules)
				{
					if (Module && Module->IsA<UParticleModuleLight>()) { return true; }
				}
			}
		}
	}
	return false;
}

void ASparrowArrow::InitArrow(const FVector& Direction, float Damage, float Range, float Speed,
	bool bPiercing, bool bPassesWorld, UParticleSystem* Trail, UParticleSystem* HitEffect,
	UParticleSystem* WorldHitEffect)
{
	if (bInitialized)
	{
		return;
	}
	FlightDirection = Direction.GetSafeNormal();
	if (!IsValid(GetOwner()) || FlightDirection.IsNearlyZero() || Range <= 0.0f || Speed <= 0.0f)
	{
		Destroy();
		return;
	}
	bInitialized = true;
	FlightDamage = FMath::Max(Damage, 0.0f);
	RemainingRange = Range;
	FlightSpeed = Speed;
	bPiercesTargets = bPiercing;
	bIgnoresWorld = bPassesWorld;
	TargetImpactEffect = HitEffect;
	ObstacleImpactEffect = WorldHitEffect;
	SetActorRotation(FlightDirection.Rotation());
	if (SharedVolleyHits)
	{
		TargetImpactEffect = GetMultishotImpact(HitEffect);
		ObstacleImpactEffect = TargetImpactEffect;
		ConfigureImpactPresentation(nullptr, 0.325f, 0.24f);
		// 작은 화살의 앞뒤 위치와 짧은 꼬리를 분산해 촘촘한 화살 군집으로 읽히게 한다.
		TrailParticle->SetTemplate(nullptr);
		Tags.Add(TEXT("SparrowMultishotArrow"));
		float VisualTipScale = 0.5f;
		float VisualLag = 0.0f;
		UStaticMesh* Plane = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
		UMaterialInterface* Streak = LoadObject<UMaterialInterface>(nullptr,
			TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowShotWindAxis.M_SparrowShotWindAxis"));
		if (Plane && Streak)
		{
			FRandomStream Variation(HashCombine(GetTypeHash(FlightDirection),
				GetTypeHash(FMath::FloorToInt(GetWorld()->GetTimeSeconds() * 20.0f))));
			const float TailLength = Variation.FRandRange(30.0f, 55.0f);
			const float TailWidth = Variation.FRandRange(1.5f, 2.0f);
			VisualTipScale = Variation.FRandRange(0.45f, 0.6f);
			VisualLag = Variation.FRandRange(0.0f, 35.0f);
			UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(Streak, this);
			Material->SetScalarParameterValue(TEXT("Envelope"), Variation.FRandRange(0.65f, 0.95f));
			UStaticMeshComponent* TrailPlane = NewObject<UStaticMeshComponent>(this, TEXT("MultishotTrail0"));
			TrailPlane->SetupAttachment(SceneRoot);
			TrailPlane->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			TrailPlane->SetGenerateOverlapEvents(false);
			TrailPlane->SetCanEverAffectNavigation(false);
			TrailPlane->SetStaticMesh(Plane);
			TrailPlane->SetMaterial(0, Material);
			TrailPlane->SetRelativeLocation(FVector(-VisualLag - TailLength * 0.45f, 0.0f, 0.0f));
			TrailPlane->SetRelativeScale3D(FVector(TailLength / 100.0f, TailWidth / 100.0f, 1.0f));
			TrailPlane->SetCastShadow(false);
			TrailPlane->ComponentTags.Add(TEXT("SparrowMultishotTrail"));
			AddInstanceComponent(TrailPlane);
			TrailPlane->RegisterComponent();
		}
		if (UMaterialInterface* Gold = LoadObject<UMaterialInterface>(nullptr,
			TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowAscensionGold.M_SparrowAscensionGold")))
		{
			ArrowMesh->SetMaterial(0, Gold);
			ArrowMesh->SetRelativeScale3D(FVector(VisualTipScale));
			ArrowMesh->SetRelativeLocation(FVector(-VisualLag, 0.0f, 0.0f));
		}
	}
	else if (Trail)
	{
		TrailParticle->SetTemplate(Trail);
		TrailParticle->bOverrideLODMethod = true;
		TrailParticle->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
		TrailParticle->SetLODLevel(0);
		TrailParticle->ActivateSystem(true);
		TrailParticle->SetLODLevel(0);
	}
	SetLifeSpan(Range / Speed + 0.25f);
	SetActorTickEnabled(true);
}

void ASparrowArrow::EnableSharpBurstPresentation(int32 DetailPreviewStyle)
{
	if (!SharedVolleyHits || !SharpBurstTrails.IsEmpty()) { return; }
	UMaterialInterface* Streak = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowSharpStreak.M_SparrowSharpStreak"));
	SharpDetailPreviewStyle = FMath::Clamp(DetailPreviewStyle, 0, 11);
	if (SharpDetailPreviewStyle > 0)
	{
		const TCHAR* Folder = ActorHasTag(TEXT("SparrowAscendedArrow")) && (SharpDetailPreviewStyle == 6 || SharpDetailPreviewStyle == 10) ?
			TEXT("AscendedArsenal20261026") : SharpDetailPreviewStyle >= 6 ? TEXT("SharpArt20261026") : TEXT("SharpDetails20261026");
		Streak = LoadObject<UMaterialInterface>(nullptr, *FString::Printf(
			TEXT("/Game/TopDown/Characters/Sparrow/Materials/%s/M_SharpT%dStreak.M_SharpT%dStreak"),
			Folder, SharpDetailPreviewStyle, SharpDetailPreviewStyle));
	}
	if (ActorHasTag(TEXT("SparrowSStudy11")) || ActorHasTag(TEXT("SparrowSStudy12")))
	{
		Streak = LoadObject<UMaterialInterface>(nullptr,
			TEXT("/Game/TopDown/Characters/Sparrow/Materials/Renaissance20261027/M_RenStreak.M_RenStreak"));
	}
	if (ActorHasTag(TEXT("SparrowSharpReference")))
	{
		const TCHAR* Variant = ActorHasTag(TEXT("SparrowSharpReferencePlume")) ? TEXT("Plume") : ActorHasTag(TEXT("SparrowSharpReferenceRefined")) ? TEXT("Refined") : TEXT("Base");
		Streak = LoadObject<UMaterialInterface>(nullptr, *FString::Printf(
			TEXT("/Game/TopDown/Characters/Sparrow/Materials/SharpReference20261027/%s/M_SharpReferenceStreak.M_SharpReferenceStreak"), Variant));
	}
	if (!Streak) { return; }
	// S는 실물 깃/촉의 불규칙한 윤곽 대신 동일한 대칭 광침을 사용한다. 충돌축은 그대로다.
	ArrowMesh->SetVisibility(false);
	const bool bRevisedStudy = ActorHasTag(TEXT("SparrowSStudy9")) || ActorHasTag(TEXT("SparrowSStudy10")) ||
		ActorHasTag(TEXT("SparrowSStudy11")) || ActorHasTag(TEXT("SparrowSStudy12"));
	ConfigureImpactPresentation(GetSharpBurstImpact(), bRevisedStudy ? .28f : .85f, .22f);
	TInlineComponentArray<UStaticMeshComponent*> Meshes;
	GetComponents(Meshes);
	for (UStaticMeshComponent* Mesh : Meshes)
	{
		if (!Mesh->ComponentHasTag(TEXT("SparrowMultishotTrail"))) { continue; }
		Mesh->SetMaterial(0, Streak);
		Mesh->SetRelativeRotation(FRotator::ZeroRotator);
		SharpBurstTrails.Add(Mesh);
		UStaticMeshComponent* Cross = NewObject<UStaticMeshComponent>(this, TEXT("SharpBurstCross"));
		Cross->SetupAttachment(SceneRoot);
		Cross->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Cross->SetGenerateOverlapEvents(false);
		Cross->SetCanEverAffectNavigation(false);
		Cross->SetCastShadow(false);
		Cross->SetStaticMesh(Mesh->GetStaticMesh());
		Cross->SetMaterial(0, Mesh->GetMaterial(0));
		Cross->SetRelativeRotation(FRotator(0.0f, 0.0f, 90.0f));
		AddInstanceComponent(Cross);
		Cross->RegisterComponent();
		SharpBurstTrails.Add(Cross);
		break;
	}
	UpdateSharpBurstPresentation();
}

void ASparrowArrow::EnableCrystalArrowPresentation()
{
	bCrystalArrowPresentation = true;
	Tags.AddUnique(TEXT("SparrowCrystalArrow"));
	ImpactScale = .32f;
	if (ActorHasTag(TEXT("SparrowHarmonyArrow")))
	{
		ArrowMesh->SetVisibility(false); TrailParticle->DeactivateSystem(); TrailParticle->SetVisibility(false);
		for (UStaticMeshComponent* Part : SharpBurstTrails) { Part->SetVisibility(false); }
		return;
	}
	EnableSharpBurstPresentation(10);
	const int32 FDesignStyle = FDesignStyleFor(this);
	if (FDesignStyle > 0)
	{
		const TCHAR* DesignFolder = TEXT("/Game/TopDown/Characters/Sparrow/FX/FDesign20261027");
		const auto LoadDesignMesh = [DesignFolder](const TCHAR* Name)
		{
			return LoadObject<UStaticMesh>(nullptr, *FString::Printf(TEXT("%s/%s.%s"), DesignFolder, Name, Name));
		};
		const auto LoadDesignMaterial = [DesignFolder](const TCHAR* Name)
		{
			return LoadObject<UMaterialInterface>(nullptr, *FString::Printf(TEXT("%s/%s.%s"), DesignFolder, Name, Name));
		};
		UStaticMesh* Facet = LoadDesignMesh(FDesignStyle == 6 ? TEXT("SM_FDesignCrystal") : FDesignStyle == 3 ? TEXT("SM_FDesignFeather") : TEXT("SM_FDesignFacet"));
		UStaticMesh* Helix = LoadDesignMesh(TEXT("SM_FDesignHelix"));
		UStaticMesh* Needle = LoadDesignMesh(TEXT("SM_FDesignNeedle"));
		UMaterialInterface* FacetMaterial = LoadDesignMaterial(FDesignStyle == 3 ? TEXT("M_FDesignFeather") : TEXT("M_FDesignFacet"));
		UMaterialInterface* RibbonMaterial = LoadDesignMaterial(FDesignStyle == 1 || FDesignStyle == 3 ? TEXT("M_FDesignFilament") : TEXT("M_FDesignRibbon"));
		UMaterialInterface* CoreMaterial = LoadDesignMaterial(TEXT("M_FDesignCore"));
		if (!Facet || !Helix || !Needle || !FacetMaterial || !RibbonMaterial || !CoreMaterial)
		{
			Tags.AddUnique(TEXT("SparrowFDesignMissing"));
			for (UStaticMeshComponent* Trail : SharpBurstTrails) { Trail->SetVisibility(false); }
			ArrowMesh->SetVisibility(true);
			UE_LOG(LogTemp, Error, TEXT("SPARROW_F_DESIGN missing authored mesh/material style=%d"), FDesignStyle);
			return;
		}
		const int32 Pieces = FDesignPieces(FDesignStyle) + FDesignRibbons(FDesignStyle);
		while (SharpBurstTrails.Num() < Pieces)
		{
			UStaticMeshComponent* Part = NewObject<UStaticMeshComponent>(this, NAME_None, RF_Transient);
			Part->SetupAttachment(SceneRoot);
			Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			Part->SetGenerateOverlapEvents(false);
			Part->SetCanEverAffectNavigation(false);
			Part->SetCastShadow(false);
			Part->SetReceivesDecals(false);
			AddInstanceComponent(Part);
			Part->RegisterComponent();
			SharpBurstTrails.Add(Part);
		}
		for (int32 Index = 0; Index < SharpBurstTrails.Num(); ++Index)
		{
			UStaticMeshComponent* Part = SharpBurstTrails[Index];
			const bool bFacet = Index < FDesignPieces(FDesignStyle);
			Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			Part->SetGenerateOverlapEvents(false);
			Part->SetCanEverAffectNavigation(false);
			Part->SetStaticMesh(bFacet ? Facet : Helix);
			UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(bFacet ? FacetMaterial :
				FDesignStyle == 6 && Index >= FDesignPieces(FDesignStyle) + 2 ? LoadDesignMaterial(TEXT("M_FDesignFilament")) : RibbonMaterial, this);
			Material->SetScalarParameterValue(TEXT("Index"), Index);
			Material->SetScalarParameterValue(TEXT("Ascended"), ActorHasTag(TEXT("SparrowAscendedArrow")) ? 1.0f : 0.0f);
			Part->SetMaterial(0, Material);
			Part->ComponentTags.AddUnique(bFacet ? TEXT("SparrowFDesignFacet") : TEXT("SparrowFDesignHelix"));
		}
		ArrowMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		ArrowMesh->SetGenerateOverlapEvents(false);
		ArrowMesh->SetCanEverAffectNavigation(false);
		ArrowMesh->SetStaticMesh(Needle);
		ArrowMesh->SetMaterial(0, CoreMaterial);
		ArrowMesh->SetVisibility(true);
		ArrowMesh->ComponentTags.AddUnique(TEXT("SparrowFDesignCore"));
		UpdateSharpBurstPresentation();
		return;
	}
	const TCHAR* Folder = ActorHasTag(TEXT("SparrowAscendedArrow")) ? TEXT("AscendedArsenal20261026") : TEXT("Arsenal20261026");
	UStaticMesh* Pressure = LoadObject<UStaticMesh>(nullptr,
		TEXT("/Game/ParagonSparrow/FX/Meshes/Heroes/Sparrow/Abilities/SM_ShockwaveFlame.SM_ShockwaveFlame"));
	UMaterialInterface* Crystal = LoadObject<UMaterialInterface>(nullptr, *FString::Printf(
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/%s/M_GatherCrystalArrow.M_GatherCrystalArrow"), Folder));
	if (Pressure && Crystal)
	{
		for (UStaticMeshComponent* Trail : SharpBurstTrails)
		{
			// 기존 표시 컴포넌트도 메시 교체 전에 충돌/내비 비활성 상태를 명시한다.
			Trail->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			Trail->SetGenerateOverlapEvents(false);
			Trail->SetCanEverAffectNavigation(false);
			Trail->SetStaticMesh(Pressure);
			Trail->SetMaterial(0, Crystal);
			Trail->ComponentTags.AddUnique(TEXT("SparrowCrystalPressureMesh"));
		}
	}
	if (UMaterialInterface* Solid = LoadObject<UMaterialInterface>(nullptr, *FString::Printf(
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/%s/M_GatherCrystalSolid.M_GatherCrystalSolid"), Folder)))
	{
		for (int32 Slot = 0; Slot < FMath::Max(1, ArrowMesh->GetNumMaterials()); ++Slot) { ArrowMesh->SetMaterial(Slot, Solid); }
		ArrowMesh->SetVisibility(true);
		ArrowMesh->ComponentTags.AddUnique(TEXT("SparrowCrystalSolidCore"));
	}
	UpdateSharpBurstPresentation();
}

void ASparrowArrow::UpdateSharpBurstPresentation()
{
	if (ActorHasTag(TEXT("SparrowHarmonyArrow"))) { return; }

	if (bCrystalArrowPresentation)
	{
		const bool bForm = ActorHasTag(TEXT("SparrowAscendedArrow"));
		const float FlightAge = DistanceTravelled / FMath::Max(FlightSpeed, 1.0f);
		const float Lead = 110.0f * (1.0f - FMath::SmoothStep(0.0f, .040f, FlightAge));
		const int32 FDesignStyle = FDesignStyleFor(this);
		if (FDesignStyle > 0)
		{
			if (ActorHasTag(TEXT("SparrowFDesignMissing"))) { return; }
			for (int32 Index = 0; Index < SharpBurstTrails.Num(); ++Index)
			{
				UStaticMeshComponent* Part = SharpBurstTrails[Index];
				const bool bFacet = Index < FDesignPieces(FDesignStyle);
				if (bFacet)
				{
					const float Phase = Index * 2.399963f + FlightAge * .9f;
					const FVector Radial(0.0f, FMath::Cos(Phase), FMath::Sin(Phase));
					const FVector Axis = (FVector::ForwardVector + Radial * .22f).GetSafeNormal();
					const float FacetScale = FDesignStyle == 6 ? .72f : FDesignStyle == 5 ? .58f : 1.0f;
					const float Length = (44.0f + (Index % 4) * 11.0f) * FacetScale;
					const float AxialOffset = FDesignStyle >= 5 ? (Index % 7) * 22.0f : (Index % 4) * 38.0f;
					const FVector Center(Lead - 32.0f - AxialOffset, 0.0f, 0.0f);
					Part->SetRelativeLocation(Center + Radial * (6.0f + (Index % 3) * 2.5f) - Axis * Length * .5f);
					Part->SetRelativeRotation(FRotationMatrix::MakeFromXZ(Axis, Radial).ToQuat());
					Part->SetRelativeScale3D(FVector(Length / 100.0f, FDesignStyle == 3 ? 1.25f : FacetScale, FacetScale));
				}
				else
				{
					const int32 Ribbon = Index - FDesignPieces(FDesignStyle);
					const float Length = 300.0f;
					const float Radius = FDesignStyle == 1 ? 12.0f : 19.0f;
					Part->SetRelativeLocation(FVector(Lead - Length, 0.0f, 0.0f));
					Part->SetRelativeRotation(FQuat(FVector::ForwardVector, Ribbon * 2.094395f + FlightAge * 7.0f));
					Part->SetRelativeScale3D(FVector(Length / 100.0f, Radius / 40.0f, Radius / 40.0f));
				}
				if (UMaterialInstanceDynamic* Material = Cast<UMaterialInstanceDynamic>(Part->GetMaterial(0)))
				{
					Material->SetScalarParameterValue(TEXT("Age"), FlightAge + .52f);
					Material->SetScalarParameterValue(TEXT("Progress"), 1.0f);
					Material->SetScalarParameterValue(TEXT("Refinement"), FDesignStyle == 6 ? 1.0f : 0.0f);
					Material->SetScalarParameterValue(TEXT("Envelope"), bForm ? .84f : 1.0f);
				}
			}
			const float Length = 270.0f;
			ArrowMesh->SetRelativeLocation(FVector(Lead - Length, 0.0f, 0.0f));
			ArrowMesh->SetRelativeRotation(FRotator::ZeroRotator);
			ArrowMesh->SetRelativeScale3D(FVector(Length / 100.0f, .88f, .88f));
			return;
		}
		for (int32 Index = 0; Index < SharpBurstTrails.Num(); ++Index)
		{
			UStaticMeshComponent* Trail = SharpBurstTrails[Index];
			const float ShellLength = Index == 0 ? 240.0f : 190.0f;
			const float Radius = (bForm ? 26.0f : 37.0f) * (Index == 0 ? 1.0f : .62f);
			Trail->SetRelativeLocation(FVector(Lead - ShellLength, 0.0f, 0.0f));
			Trail->SetRelativeRotation(FRotator(0.0f, 0.0f, FlightAge * 440.0f + Index * 117.0f));
			Trail->SetRelativeScale3D(FVector(ShellLength, Radius, Radius) / 56.641f);
		}
		const float LengthScale = 240.0f / 158.395f;
		ArrowMesh->SetRelativeLocation(FVector(Lead - 61.464f * LengthScale, 0.0f, 0.0f));
		ArrowMesh->SetRelativeScale3D(FVector(bForm ? 2.35f : 3.0f, bForm ? 2.35f : 3.0f, LengthScale));
		return;
	}
	const float Length = bCrystalArrowPresentation ? 300.0f : FMath::Clamp(DistanceTravelled * .65f + 12.0f, 12.0f, 86.0f);
	const float AssemblyOffset = bCrystalArrowPresentation ? 190.0f *
		(1.0f - FMath::SmoothStep(0.0f, .060f, DistanceTravelled / FMath::Max(FlightSpeed, 1.0f))) : 0.0f;
	for (UStaticMeshComponent* Trail : SharpBurstTrails)
	{
		Trail->SetRelativeLocation(FVector(AssemblyOffset - Length * .49f, 0.0f, 0.0f));
		// 원화 시안에서는 같은 가는 광핵을 유지하며 대칭 화살촉이 읽힐 폭만 확보한다.
		// F는 재질 안에서 광핵 두께를 보존하고 넓어진 바깥 영역만 흐름과 파편에 쓴다.
		const float Width = bCrystalArrowPresentation ? (ActorHasTag(TEXT("SparrowAscendedArrow")) ? 1.20f : 1.60f) :
			SharpDetailPreviewStyle >= 6 ? .24f : .14f;
		Trail->SetRelativeScale3D(FVector(Length / 100.0f, Width, 1.0f));
	}
}

void ASparrowArrow::ConfigureImpactPresentation(UParticleSystem* TargetEffect, float Scale, float Lifetime)
{
	if (TargetEffect) { TargetImpactEffect = TargetEffect; }
	ImpactScale = FMath::Clamp(Scale, 0.1f, 2.0f);
	ImpactLifetime = FMath::Clamp(Lifetime, 0.05f, 2.0f);
}

void ASparrowArrow::EnableRapidFlow()
{
	if (!SharedVolleyHits)
	{
		if (!bInitialized || HolyArrowFlight) { return; }
		UStaticMesh* Plane = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
		UMaterialInterface* Surface = LoadObject<UMaterialInterface>(nullptr,
			TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowHolyArrow.M_SparrowHolyArrow"));
		if (!Plane || !Surface)
		{
			UE_LOG(LogTemp, Warning, TEXT("SPARROW_HOLY_ARROW owned surface unavailable; preserving original rapid flow"));
			TrailParticle->SetRelativeScale3D(FVector(1.0f, 1.5f, 1.5f));
			StartTexturedFlow(1.0f);
			return;
		}
		TrailParticle->DeactivateSystem();
		TrailParticle->SetVisibility(false);
		TrailParticle->SetTemplate(nullptr);
		ArrowMesh->SetVisibility(false);
		HolyArrowFlight = NewObject<UStaticMeshComponent>(this, TEXT("HolyArrowFlight"));
		HolyArrowFlight->SetupAttachment(SceneRoot);
		HolyArrowFlight->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		HolyArrowFlight->SetGenerateOverlapEvents(false);
		HolyArrowFlight->SetCanEverAffectNavigation(false);
		HolyArrowFlight->SetStaticMesh(Plane);
		HolyArrowFlight->SetMaterial(0, Surface);
		HolyArrowFlight->SetRelativeLocation(FVector(-87.0f, 0.0f, 0.0f));
		HolyArrowFlight->SetRelativeScale3D(FVector(1.85f, 0.48f, 1.0f));
		HolyArrowFlight->SetCastShadow(false);
		HolyArrowFlight->SetReceivesDecals(false);
		HolyArrowFlight->ComponentTags.Append({TEXT("SparrowSkillFX"), TEXT("SparrowHolyArrowFlight")});
		AddInstanceComponent(HolyArrowFlight);
		HolyArrowFlight->RegisterComponent();
		UpdateHolyArrowFacing();
		Tags.AddUnique(TEXT("SparrowHolyArrow"));
	}
}

void ASparrowArrow::ConfigureEDesignPresentation(int32 Style)
{
	if (!HolyArrowFlight || (Style != 1 && (Style < 3 || Style > 8))) { return; }
	const FString Name = FString::Printf(TEXT("M_E%dArrow"), Style);
	const FString Path = FString::Printf(TEXT("/Game/TopDown/Characters/Sparrow/Materials/EDesign20261027/%s.%s"), *Name, *Name);
	if (UMaterialInterface* Source = LoadObject<UMaterialInterface>(nullptr, *Path))
	{
		HolyArrowFlight->SetMaterial(0, Source);
		const float Length = Style >= 7 ? 190.0f : Style == 6 ? 255.0f : Style == 1 ? 220.0f : 145.0f;
		HolyArrowFlight->SetRelativeLocation(FVector(-Length * .47f, 0.0f, 0.0f));
		HolyArrowFlight->SetRelativeScale3D(FVector(Length / 100.0f, Style >= 7 ? .52f : Style == 6 ? .74f : Style == 1 ? .55f : Style == 4 ? .72f : Style == 5 ? .58f : .42f, 1.0f));
		Tags.AddUnique(FName(*FString::Printf(TEXT("SparrowEDesign%d"), Style)));
	}
}

void ASparrowArrow::ConfigureConvergingFlight(const FVector& Target, const FVector& Bend, float Seconds)
{
	if (!bInitialized || Target.ContainsNaN() || Bend.ContainsNaN()) { return; }
	CurveStart = GetActorLocation();
	CurveTarget = Target;
	CurveBend = Bend;
	CurveAge = 0.0f;
	CurveDuration = FMath::Max(.08f, Seconds);
	float CurveLength = 0.0f;
	FVector Previous = CurveStart;
	for (int32 Step = 1; Step <= 64; ++Step)
	{
		const float T = Step / 64.0f;
		const FVector Next = FMath::Lerp(CurveStart, CurveTarget, T) + CurveBend * (4.0f * T * (1.0f - T));
		CurveLength += FVector::Distance(Previous, Next);
		Previous = Next;
	}
	// Range selects the endpoint; the curved path needs its own longer travel budget.
	RemainingRange = CurveLength + .5f;
	FlightSpeed = CurveLength / CurveDuration;
	Tags.AddUnique(TEXT("SparrowConvergingFlight"));
}

void ASparrowArrow::UpdateHolyArrowFacing()
{
	if (!HolyArrowFlight || !GetWorld()) { return; }
	const APlayerController* Player = GetWorld()->GetFirstPlayerController();
	const FVector Normal = Player && Player->PlayerCameraManager ?
		(Player->PlayerCameraManager->GetCameraLocation() - GetActorLocation()).GetSafeNormal() : FVector::UpVector;
	HolyArrowFlight->SetWorldRotation(FRotationMatrix::MakeFromXZ(FlightDirection, Normal).Rotator());
}

void ASparrowArrow::EnablePiercingLance(float Radius)
{
	if (!bInitialized || bPiercingLance || !GetWorld() || !IsValid(GetOwner())) { return; }
	bPiercingLance = true;
	bPiercesTargets = true;
	bIgnoresWorld = false;
	bAppliesRelentlessBonus = false;
	bRecordsRelentless = false;
	CollisionRadius = FMath::Clamp(Radius, 1.0f, 100.0f);
	Tags.AddUnique(TEXT("SparrowPiercingLance"));
	ArrowMesh->SetVisibility(false);
	TrailParticle->DeactivateSystem();
	TrailParticle->SetVisibility(false);
	TrailParticle->SetTemplate(nullptr);
	TargetImpactEffect = nullptr;
	ObstacleImpactEffect = nullptr;
	FActorSpawnParameters Spawn;
	Spawn.Owner = GetOwner();
	Spawn.ObjectFlags |= RF_Transient;
	Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	ASparrowPiercingLance* Visual = GetWorld()->SpawnActor<ASparrowPiercingLance>(GetActorLocation(), GetActorRotation(), Spawn);
	if (Visual)
	{
		Visual->InitializeFlight(FlightDirection);
		PiercingLanceVisual = Visual;
	}
}

void ASparrowArrow::OnArrowImpactVisual(const FHitResult& Hit, bool bWorld)
{
	const int32 Design = FDesignStyleFor(this);
	if (Design > 0 && GetWorld() && IsValid(GetOwner()))
	{
		FActorSpawnParameters Spawn;
		Spawn.Owner = GetOwner();
		Spawn.ObjectFlags |= RF_Transient;
		Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		if (ASparrowGatherShot* Impact = GetWorld()->SpawnActor<ASparrowGatherShot>(Hit.ImpactPoint, FRotator::ZeroRotator, Spawn))
		{
			if (!Impact->InitializeDesignImpact(Cast<ATopDownCombatCharacter>(GetOwner()), Design, Hit.ImpactPoint, FlightDirection)) { Impact->Destroy(); }
		}
		return;
	}
	if (!bWorld && ActorHasTag(TEXT("SparrowWFinalImpact")) && GetWorld() && IsValid(GetOwner()))
	{
		FActorSpawnParameters FinalSpawn;
		FinalSpawn.Owner = GetOwner();
		FinalSpawn.ObjectFlags |= RF_Transient;
		FinalSpawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		if (ASparrowSharpImpact* Final = GetWorld()->SpawnActor<ASparrowSharpImpact>(Hit.ImpactPoint, FRotator::ZeroRotator, FinalSpawn))
		{
			Final->Initialize(12, FlightDirection, true);
		}
	}
	if (!bWorld && GetWorld() && IsValid(GetOwner()) &&
		!ActorHasTag(TEXT("SparrowWFinalImpact")) && !ActorHasTag(TEXT("SparrowCraftMultishot")) &&
		ActorHasTag(TEXT("SparrowAscendedW")))
	{
		FActorSpawnParameters Spawn;
		Spawn.Owner = GetOwner();
		Spawn.ObjectFlags |= RF_Transient;
		Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		ASparrowAscendedShotFX* Contact = GetWorld()->SpawnActor<ASparrowAscendedShotFX>(Hit.ImpactPoint, FlightDirection.Rotation(), Spawn);
		if (Contact)
		{
			if (!Contact->InitializeContact(Cast<ATopDownCombatCharacter>(GetOwner()),
				ActorHasTag(TEXT("SparrowAscendedW")) ? 1 : 3, Hit.ImpactPoint, FlightDirection)) { Contact->Destroy(); }
			else { Contact->SetActorScale3D(FVector(ActorHasTag(TEXT("SparrowAscendedW")) ? .75f : .5f)); }
		}
	}
	if (!bWorld && !SharpBurstTrails.IsEmpty() && GetWorld() && IsValid(GetOwner()))
	{
		// 이 콜백은 공유 피격 집합에 등록한 뒤 호출되므로 대상마다 한 번만 생성한다.
		FActorSpawnParameters SharpSpawn;
		SharpSpawn.Owner = GetOwner();
		SharpSpawn.ObjectFlags |= RF_Transient;
		SharpSpawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		ASparrowSharpImpact* Contact = GetWorld()->SpawnActor<ASparrowSharpImpact>(Hit.ImpactPoint, FRotator::ZeroRotator, SharpSpawn);
		const int32 ContactStyle = ActorHasTag(TEXT("SparrowSStudy9")) ? 13 :
			ActorHasTag(TEXT("SparrowSStudy10")) ? 14 : ActorHasTag(TEXT("SparrowSStudy11")) ? 15 :
			ActorHasTag(TEXT("SparrowSStudy12")) ? 16 : SharpDetailPreviewStyle;
		if (Contact)
		{
			if (ActorHasTag(TEXT("SparrowSharpReference")))
			{
				Contact->InitializeReference(FlightDirection, ActorHasTag(TEXT("SparrowSharpReferenceRefined")) || ActorHasTag(TEXT("SparrowSharpReferencePlume")), ActorHasTag(TEXT("SparrowSharpReferencePlume")));
			}
			else { Contact->Initialize(ContactStyle, FlightDirection, ActorHasTag(TEXT("SparrowAscendedArrow")), bCrystalArrowPresentation); }
		}
	}
	if (HolyArrowFlight && GetWorld() && IsValid(GetOwner()))
	{
		FActorSpawnParameters HolySpawn;
		HolySpawn.Owner = GetOwner();
		HolySpawn.ObjectFlags |= RF_Transient;
		HolySpawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		ASparrowHolyBow* Impact = GetWorld()->SpawnActor<ASparrowHolyBow>(Hit.ImpactPoint, FlightDirection.Rotation(), HolySpawn);
		if (Impact)
		{
			const int32 EDesign = ActorHasTag(TEXT("SparrowEDesign8")) ? 8 : ActorHasTag(TEXT("SparrowEDesign7")) ? 7 : ActorHasTag(TEXT("SparrowEDesign6")) ? 6 : ActorHasTag(TEXT("SparrowEDesign1")) ? 1 : ActorHasTag(TEXT("SparrowEDesign5")) ? 5 :
				ActorHasTag(TEXT("SparrowEDesign4")) ? 4 : ActorHasTag(TEXT("SparrowEDesign3")) ? 3 : 0;
			Impact->InitializeImpact(FlightDirection, bWorld, EDesign);
		}
	}
	if (!bPiercingLance || !GetWorld() || !IsValid(GetOwner())) { return; }
	FActorSpawnParameters Spawn;
	Spawn.Owner = GetOwner();
	Spawn.ObjectFlags |= RF_Transient;
	Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	ASparrowPiercingLance* Visual = GetWorld()->SpawnActor<ASparrowPiercingLance>(Hit.ImpactPoint, FlightDirection.Rotation(), Spawn);
	if (Visual) { Visual->InitializeImpact(FlightDirection, DamagedActors.Num(), bWorld); }
}

void ASparrowArrow::StartTexturedFlow(float WidthScale)
{
	if (!bInitialized || RapidFlowParticle) { return; }
	UParticleSystem* Flow = GetTexturedArrowFlow();
	if (!Flow) { return; }
	// 원본 궤적은 비행 축을 계속 연결하고, 별도 flipbook 입자는 짧은 질감과 부피를 더한다.
	RapidFlowParticle = NewObject<UParticleSystemComponent>(this, TEXT("RapidArrowFlow"));
	RapidFlowParticle->bAutoActivate = false;
	RapidFlowParticle->SetupAttachment(SceneRoot);
	RapidFlowParticle->SetTemplate(Flow);
	RapidFlowParticle->SetRelativeLocation(FVector(-25.0f, 0.0f, 0.0f));
	RapidFlowParticle->SetRelativeScale3D(FVector(1.0f, WidthScale, WidthScale));
	RapidFlowParticle->bOverrideLODMethod = true;
	RapidFlowParticle->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
	RapidFlowParticle->ComponentTags.Append({TEXT("SparrowSkillFX"), TEXT("SparrowTexturedArrowFlow")});
	AddInstanceComponent(RapidFlowParticle);
	RapidFlowParticle->RegisterComponent();
	RapidFlowParticle->SetLODLevel(0);
	RapidFlowParticle->ActivateSystem(true);
	RapidFlowParticle->SetLODLevel(0);
}

void ASparrowArrow::SpawnImpact(UParticleSystem* Effect, const FHitResult& Hit, bool bWorldImpact)
{
	if (FDesignStyleFor(this) > 0) { return; }
	if (!Effect || !GetWorld())
	{
		return;
	}
	// 다발 화살이 벽에 모일 때 겹치는 섬광만 줄인다. 적 명중과 다른 화살의 충돌 연출은 유지한다.
	const bool bSmallVolleyWallHit = bWorldImpact && SharedVolleyHits.IsValid();
	const float VisualScale = ImpactScale * (bSmallVolleyWallHit ? 0.22f : 1.0f);
	const float VisualLifetime = bSmallVolleyWallHit ? FMath::Min(ImpactLifetime, 0.18f) : ImpactLifetime;
	UParticleSystemComponent* Particle = UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), Effect,
		Hit.ImpactPoint, FlightDirection.Rotation(), FVector(VisualScale), true, EPSCPoolMethod::None, false);
	if (Particle)
	{
		Particle->ComponentTags.Add(TEXT("SparrowSkillFX"));
		if (SharedVolleyHits) { Particle->ComponentTags.Add(TEXT("SparrowMultishotImpact")); }
		if (!SharpBurstTrails.IsEmpty()) { Particle->ComponentTags.Add(TEXT("SparrowSharpImpact")); }
		if (ActorHasTag(TEXT("SparrowChargedArrow")))
		{
			Particle->ComponentTags.Add(TEXT("SparrowPiercingImpact"));
			Particle->SetVectorParameter(TEXT("TeamColor"), FVector(1.0f, 0.78f, 0.10f));
		}
		Particle->bOverrideLODMethod = true;
		Particle->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
		Particle->SetLODLevel(0);
		Particle->ActivateSystem(true);
		Particle->SetLODLevel(0);
		// 충돌 FX는 화살 소멸 후에도 재생하되 원본에 루프가 있어도 제한 시간 뒤 정리한다.
		FTimerHandle Cleanup;
		GetWorldTimerManager().SetTimer(Cleanup, FTimerDelegate::CreateWeakLambda(Particle, [Particle]()
		{
			Particle->DestroyComponent();
		}), VisualLifetime, false);
	}
}

void ASparrowArrow::ConfigureRicochet(int32 AdditionalTargets, float Radius, float DamageScale)
{
	if (bInitialized) { return; }
	RicochetsRemaining = FMath::Clamp(AdditionalTargets, 0, 2);
	RicochetRadius = FMath::Clamp(Radius, 1.0f, 1000.0f);
	RicochetDamageScale = FMath::Clamp(DamageScale, 0.0f, 1.0f);
	bRicochetMode = RicochetsRemaining > 0;
}

void ASparrowArrow::EnableExtraPresentation()
{
	if (!bInitialized || bExtraPresentation || !GetWorld()) { return; }
	bExtraPresentation = true;
	FActorSpawnParameters Spawn;
	Spawn.Owner = this;
	Spawn.ObjectFlags |= RF_Transient;
	Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	ASparrowSkillVisual* Visual = GetWorld()->SpawnActor<ASparrowSkillVisual>(GetActorLocation(), GetActorRotation(), Spawn);
	if (Visual)
	{
		Visual->SetArrowPresentation(bRicochetMode);
		Visual->Initialize(ESparrowVisualKind::ArrowFlight, RemainingRange / FlightSpeed + 1.5f);
		ExtraFlightVisual = Visual;
	}
}

void ASparrowArrow::SpawnExtraHitVisual(const FHitResult& Hit)
{
	if (!bExtraPresentation || !IsValid(GetOwner())) { return; }
	if (USparrowSkillComponent* Skills = GetOwner()->FindComponentByClass<USparrowSkillComponent>())
	{
		Skills->SpawnExtraArrowHitVisual(Hit.ImpactPoint, FlightDirection, bRicochetMode, DamagedActors.Num());
	}
}

bool ASparrowArrow::TryRicochet(const FHitResult& Hit)
{
	if (!bRicochetMode || RicochetsRemaining <= 0 || !GetWorld() || !IsValid(GetOwner())) { return false; }
	const FVector Origin = IsValid(Hit.GetActor()) ? Hit.GetActor()->GetActorLocation() : FVector(Hit.Location);
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_Pawn);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	FCollisionQueryParams Query(SCENE_QUERY_STAT(SparrowRicochetTargets), false, GetOwner());
	Query.AddIgnoredActor(this);
	TArray<FOverlapResult> Overlaps;
	GetWorld()->OverlapMultiByObjectType(Overlaps, Origin, FQuat::Identity, Objects,
		FCollisionShape::MakeSphere(RicochetRadius), Query);
	FCollisionQueryParams Visibility(SCENE_QUERY_STAT(SparrowRicochetVisibility), false, GetOwner());
	Visibility.AddIgnoredActor(this);
	for (TActorIterator<APawn> It(GetWorld()); It; ++It) { Visibility.AddIgnoredActor(*It); }
	for (TActorIterator<AKwangTrainingDummy> It(GetWorld()); It; ++It) { Visibility.AddIgnoredActor(*It); }
	AActor* Next = nullptr;
	float NearestSquared = FMath::Square(RicochetRadius);
	for (const FOverlapResult& Overlap : Overlaps)
	{
		AActor* Candidate = Overlap.GetActor();
		const AKwangTrainingDummy* Dummy = Cast<AKwangTrainingDummy>(Candidate);
		if (!IsValid(Candidate) || Candidate == GetOwner() || Candidate->IsActorBeingDestroyed() ||
			!Candidate->CanBeDamaged() || DamagedActors.Contains(Candidate) ||
			(!Candidate->IsA<APawn>() && !Dummy) || (Dummy && !Dummy->IsAlive())) { continue; }
		const float DistanceSquared = FVector::DistSquared(Origin, Candidate->GetActorLocation());
		if (DistanceSquared > NearestSquared) { continue; }
		FHitResult Block;
		if (GetWorld()->LineTraceSingleByChannel(Block, Origin, Candidate->GetActorLocation(), ECC_Visibility, Visibility)) { continue; }
		NearestSquared = DistanceSquared;
		Next = Candidate;
	}
	if (!Next) { return false; }
	const FVector Start = Hit.Location;
	FlightDirection = (Next->GetActorLocation() - Start).GetSafeNormal();
	if (FlightDirection.IsNearlyZero()) { return false; }
	FlightDamage *= RicochetDamageScale;
	RemainingRange = RicochetRadius + CollisionRadius * 2.0f;
	--RicochetsRemaining;
	SetActorLocation(Start);
	SetActorRotation(FlightDirection.Rotation());
	SetLifeSpan(RemainingRange / FlightSpeed + 0.25f);
	UE_LOG(LogTemp, Display, TEXT("SPARROW_EXTRA ricochet next=%s damage=%.2f remaining=%d"), *Next->GetName(), FlightDamage, RicochetsRemaining);
	return true;
}

void ASparrowArrow::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	if (!bInitialized || !IsValid(GetOwner()) || RemainingRange <= 0.0f)
	{
		Destroy();
		return;
	}
	const FVector Start = GetActorLocation();
	float Distance = FMath::Min(FlightSpeed * FMath::Max(DeltaTime, 0.0f), RemainingRange);
	FVector End = Start + FlightDirection * Distance;
	bool bCurveAtEndpoint = false;
	if (CurveDuration > 0.0f)
	{
		CurveAge += FMath::Max(DeltaTime, 0.0f);
		const float T = FMath::Clamp(CurveAge / CurveDuration, 0.0f, 1.0f);
		// The actual sweep follows this arc. The light trail samples these same positions.
		const FVector Next = FMath::Lerp(CurveStart, CurveTarget, T) + CurveBend * (4.0f * T * (1.0f - T));
		FlightDirection = (Next - Start).GetSafeNormal();
		Distance = FMath::Min(static_cast<float>(FVector::Distance(Start, Next)), RemainingRange);
		End = Start + FlightDirection * Distance;
		SetActorRotation(FlightDirection.Rotation());
		if (T >= 1.0f)
		{
			bCurveAtEndpoint = true;
			CurveDuration = 0.0f;
			RemainingRange = Distance; // Final sweep still tests the endpoint before retirement.
		}
	}
	FCollisionQueryParams Query(SCENE_QUERY_STAT(SparrowArrow), false, GetOwner());
	Query.AddIgnoredActor(this);
	if (bRicochetMode)
	{
		for (const TWeakObjectPtr<AActor>& Damaged : DamagedActors)
		{
			if (Damaged.IsValid()) { Query.AddIgnoredActor(Damaged.Get()); }
		}
	}
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_Pawn);
	Objects.AddObjectTypesToQuery(ECC_WorldStatic);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	TArray<FHitResult> Hits;
	GetWorld()->SweepMultiByObjectType(Hits, Start, End, FQuat::Identity, Objects,
		FCollisionShape::MakeSphere(CollisionRadius), Query);
	Hits.Sort([](const FHitResult& Left, const FHitResult& Right) { return Left.Time < Right.Time; });
	float TravelFraction = 1.0f;
	bool bStopped = false;
	float GuardTime = 1.0f;
	FVector GuardContact = FVector::ZeroVector;
	TWeakObjectPtr<ASparrowSanctuary> Guard = ASparrowSanctuary::FindInterception(this, Start, End, GuardTime, GuardContact);
	const auto StopAtGuard = [&]()
	{
		if (!Guard.IsValid() || !Guard->TryIntercept(this, GuardContact)) { return false; }
		const float Travelled = Distance * GuardTime;
		DistanceTravelled += Travelled;
		RemainingRange = FMath::Max(0.0f, RemainingRange - Travelled);
		SetActorLocation(GuardContact);
		Destroy();
		return true;
	};
	for (const FHitResult& Hit : Hits)
	{
		AActor* Target = Hit.GetActor();
		if (!IsValid(Target) || Target == GetOwner())
		{
			continue;
		}
		// 앞의 표적/벽은 원래 순서로 처리한다. 관통 또는 굴절로 먼저 끝난 구간에는 방어 반격을 끼워 넣지 않는다.
		if (GuardTime < Hit.Time - KINDA_SMALL_NUMBER && StopAtGuard()) { return; }
		const bool bCombatTarget = Target->IsA<APawn>() || Target->IsA<AKwangTrainingDummy>();
		if (bCombatTarget)
		{
			if (!DamagedActors.Contains(Target) && (!SharedVolleyHits || !SharedVolleyHits->Contains(Target)))
			{
				DamagedActors.Add(Target);
				if (Target->CanBeDamaged())
				{
					if (SharedVolleyHits) { SharedVolleyHits->Add(Target); }
					float AppliedDamage = FlightDamage;
					if (USparrowSkillComponent* Skills = GetOwner()->FindComponentByClass<USparrowSkillComponent>())
					{
						if (bAppliesRelentlessBonus)
						{
							AppliedDamage = Skills->ModifyArrowDamageAndRecordHit(Target, FlightDamage);
						}
						else if (bRecordsRelentless)
						{
							Skills->RecordRelentlessHit(Target);
						}
					}
					UGameplayStatics::ApplyPointDamage(Target, AppliedDamage, FlightDirection,
						Hit, GetInstigatorController(), this, nullptr);
					SpawnImpact(TargetImpactEffect, Hit);
					OnArrowImpactVisual(Hit, false);
					if (bRicochetMode)
					{
						UE_LOG(LogTemp, Display, TEXT("SPARROW_EXTRA ricochet hit=%s damage=%.2f count=%d"), *Target->GetName(), AppliedDamage, DamagedActors.Num());
						if (TryRicochet(Hit))
						{
							SpawnExtraHitVisual(Hit);
							DistanceTravelled += Distance * FMath::Clamp(Hit.Time, 0.0f, 1.0f);
							return;
						}
					}
					SpawnExtraHitVisual(Hit);
				}
			}
			if (!bPiercesTargets)
			{
				TravelFraction = FMath::Clamp(Hit.Time, 0.0f, 1.0f);
				bStopped = true;
				break;
			}
		}
		else if (Hit.bBlockingHit && !bIgnoresWorld)
		{
			SpawnImpact(ObstacleImpactEffect, Hit, true);
			OnArrowImpactVisual(Hit, true);
			SpawnExtraHitVisual(Hit);
			TravelFraction = FMath::Clamp(Hit.Time, 0.0f, 1.0f);
			bStopped = true;
			break;
		}
	}
	if (!bStopped && StopAtGuard()) { return; }
	const float Travelled = Distance * TravelFraction;
	DistanceTravelled += Travelled;
	RemainingRange = FMath::Max(0.0f, RemainingRange - Travelled);
	SetActorLocation(Start + FlightDirection * Travelled);
	if (bCurveAtEndpoint || (CurveDuration > 0.0f && bStopped))
	{
		const FVector Final = GetActorLocation();
		UE_LOG(LogTemp, Display, TEXT("SPARROW_CONVERGE_END arrow=%s target=(%.3f,%.3f,%.3f) final=(%.3f,%.3f,%.3f) distance=%.3f reached=%d stopped=%d"),
			*GetName(), CurveTarget.X, CurveTarget.Y, CurveTarget.Z, Final.X, Final.Y, Final.Z,
			DistanceTravelled, bCurveAtEndpoint && !bStopped, bStopped);
	}
	if (!SharpBurstTrails.IsEmpty()) { UpdateSharpBurstPresentation(); }
	UpdateHolyArrowFacing();
	if (PiercingLanceVisual.IsValid()) { PiercingLanceVisual->UpdateHead(GetActorLocation()); }
	if (bStopped || RemainingRange <= 0.0f)
	{
		Destroy();
	}
}

void ASparrowArrow::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	SetActorTickEnabled(false);
	if (FeatherTrail.IsValid()) { FeatherTrail->StopTracking(GetActorLocation()); }
	FeatherTrail.Reset();
	if (PiercingLanceVisual.IsValid()) { PiercingLanceVisual->FinishFlight(GetActorLocation()); }
	PiercingLanceVisual.Reset();
	if (ExtraFlightVisual.IsValid()) { ExtraFlightVisual->Destroy(); }
	ExtraFlightVisual.Reset();
	if (RapidFlowParticle)
	{
		RapidFlowParticle->DeactivateSystem();
		RapidFlowParticle->DestroyComponent();
	}
	if (TrailParticle)
	{
		TrailParticle->DeactivateSystem();
		TrailParticle->DestroyComponent();
	}
	Super::EndPlay(EndPlayReason);
}
