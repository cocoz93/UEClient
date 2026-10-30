#include "SparrowShotWave.h"

#include "Camera/CameraModifier_CameraShake.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/StaticMeshComponent.h"
#include "Distributions/DistributionFloatConstant.h"
#include "Distributions/DistributionFloatUniform.h"
#include "Distributions/DistributionVectorUniform.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/Character.h"
#include "GameFramework/PlayerController.h"
#include "Components/SkeletalMeshComponent.h"
#include "SparrowSkillComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Kismet/GameplayStatics.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "Particles/ParticleEmitter.h"
#include "Particles/ParticleLODLevel.h"
#include "Particles/ParticleModuleRequired.h"
#include "Particles/Color/ParticleModuleColor.h"
#include "Particles/Lifetime/ParticleModuleLifetime.h"
#include "Particles/Size/ParticleModuleSize.h"
#include "Particles/Spawn/ParticleModuleSpawn.h"
#include "Particles/Velocity/ParticleModuleVelocity.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	TAutoConsoleVariable<int32> CVarRenaissanceW(TEXT("Sparrow.Renaissance.W"), 0,
		TEXT("W release study: 0 original, 1 split pressure lips and axial light rails."), ECVF_Cheat);
	void SetPressureScalar(UObject* Outer, FRawDistributionFloat& Value, float Constant)
	{
		UDistributionFloatConstant* Distribution = NewObject<UDistributionFloatConstant>(Outer, NAME_None, RF_Transient);
		Distribution->Constant = Constant;
		Distribution->bCanBeBaked = false;
		Distribution->bIsDirty = false;
		Value = FRawDistributionFloat();
		Value.Distribution = Distribution;
	}

	void SetPressureVector(UObject* Outer, FRawDistributionVector& Value, const FVector& Min, const FVector& Max)
	{
		UDistributionVectorUniform* Distribution = NewObject<UDistributionVectorUniform>(Outer, NAME_None, RF_Transient);
		Distribution->Min = Min;
		Distribution->Max = Max;
		Distribution->bCanBeBaked = false;
		Distribution->bIsDirty = false;
		Value = FRawDistributionVector();
		Value.Distribution = Distribution;
	}

	UParticleSystem* GetReleasePressure()
	{
		static TWeakObjectPtr<UParticleSystem> Cached;
		if (Cached.IsValid()) { return Cached.Get(); }
		UParticleSystem* Source = LoadObject<UParticleSystem>(nullptr,
			TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Primary/FX/P_SparrowPrimaryMuzzleFlash.P_SparrowPrimaryMuzzleFlash"));
		if (!Source) { return nullptr; }
		UParticleSystem* Runtime = DuplicateObject<UParticleSystem>(Source, GetTransientPackage(),
			MakeUniqueObjectName(GetTransientPackage(), UParticleSystem::StaticClass(), TEXT("P_SparrowReleasePressureRuntime")));
		Runtime->SetFlags(RF_Transient);
		Runtime->ClearFlags(RF_Public | RF_Standalone);
		// 원본 CPU 플라즈마 flipbook과 0.1초 airglow를 재사용한다. 새 고리나 넓은 단색 면을 겹치지 않는다.
		Runtime->Emitters.RemoveAll([](UParticleEmitter* Emitter)
		{
			return !Emitter || (Emitter->GetEmitterName() != TEXT("Wisps") && Emitter->GetEmitterName() != TEXT("AirglowFlash"));
		});
		if (Runtime->Emitters.Num() != 2) { return nullptr; }
		for (UParticleEmitter* Emitter : Runtime->Emitters)
		{
			if (!Emitter->IsIn(Runtime)) { return nullptr; }
			const bool bWisps = Emitter->GetEmitterName() == TEXT("Wisps");
			for (UParticleLODLevel* LOD : Emitter->LODLevels)
			{
				if (!LOD || !LOD->RequiredModule || !LOD->SpawnModule) { continue; }
				LOD->RequiredModule->EmitterDuration = 0.04f;
				LOD->RequiredModule->EmitterLoops = 1;
				LOD->RequiredModule->bKillOnDeactivate = false;
				SetPressureScalar(LOD->SpawnModule, LOD->SpawnModule->Rate, 0.0f);
				LOD->SpawnModule->BurstList.Reset();
				FParticleBurst Burst;
				Burst.Count = bWisps ? 12 : 1;
				Burst.CountLow = -1;
				Burst.Time = 0.0f;
				LOD->SpawnModule->BurstList.Add(Burst);
				if (!bWisps) { continue; }
				for (UParticleModule* Module : LOD->Modules)
				{
					if (!Module || !Module->IsIn(Runtime)) { return nullptr; }
					if (UParticleModuleLifetime* Life = Cast<UParticleModuleLifetime>(Module))
					{
						UDistributionFloatUniform* Distribution = NewObject<UDistributionFloatUniform>(Life, NAME_None, RF_Transient);
						Distribution->Min = 0.08f;
						Distribution->Max = 0.16f;
						Distribution->bCanBeBaked = false;
						Distribution->bIsDirty = false;
						Life->Lifetime = FRawDistributionFloat();
						Life->Lifetime.Distribution = Distribution;
					}
					else if (UParticleModuleSize* Size = Cast<UParticleModuleSize>(Module))
					{
						SetPressureVector(Size, Size->StartSize, FVector(60.0f), FVector(85.0f));
					}
					else if (UParticleModuleVelocity* Velocity = Cast<UParticleModuleVelocity>(Module))
					{
						SetPressureVector(Velocity, Velocity->StartVelocity, FVector(350.0f, -80.0f, -40.0f), FVector(650.0f, 80.0f, 40.0f));
						Velocity->bInWorldSpace = false;
					}
					else if (UParticleModuleColor* Color = Cast<UParticleModuleColor>(Module))
					{
						SetPressureVector(Color, Color->StartColor, FVector(3.5f, 2.8f, 0.55f), FVector(3.5f, 2.8f, 0.55f));
						SetPressureScalar(Color, Color->StartAlpha, 0.5f);
					}
				}
			}
			Emitter->UpdateModuleLists();
		}
		Cached = Runtime;
		return Runtime;
	}
}

UParticleSystem* SparrowPresentation::GetReleaseShards()
{
	static TWeakObjectPtr<UParticleSystem> Cached;
	if (Cached.IsValid()) { return Cached.Get(); }
	UParticleSystem* Source = LoadObject<UParticleSystem>(nullptr,
		TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Primary/FX/P_Sparrow_Primary_Ballistic_HitPlayer.P_Sparrow_Primary_Ballistic_HitPlayer"));
	if (!Source) { return nullptr; }
	UParticleSystem* Runtime = DuplicateObject<UParticleSystem>(Source, GetTransientPackage(),
		MakeUniqueObjectName(GetTransientPackage(), UParticleSystem::StaticClass(), TEXT("P_SparrowReleaseShards")));
	Runtime->SetFlags(RF_Transient);
	Runtime->ClearFlags(RF_Public | RF_Standalone);
	Runtime->Emitters.RemoveAll([](UParticleEmitter* Emitter)
	{
		return !Emitter || (Emitter->GetEmitterName() != TEXT("Sparks") && Emitter->GetEmitterName() != TEXT("Wisps"));
	});
	if (Runtime->Emitters.IsEmpty()) { return nullptr; }
	UMaterialInterface* WispMaterial = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowReleaseWisps.M_SparrowReleaseWisps"));
	// 착탄의 원본 결을 짧은 전방 파편으로 재구성한다. 큰 섬광/광원/피해 이벤트는 복제하지 않는다.
	for (UParticleEmitter* Emitter : Runtime->Emitters)
	{
		if (!Emitter->IsIn(Runtime)) { return nullptr; }
		const bool bSparks = Emitter->GetEmitterName() == TEXT("Sparks");
		for (UParticleLODLevel* LOD : Emitter->LODLevels)
		{
			if (!LOD || !LOD->RequiredModule || !LOD->SpawnModule) { continue; }
			if (!bSparks && WispMaterial) { LOD->RequiredModule->Material = WispMaterial; }
			LOD->RequiredModule->EmitterDuration = 0.025f;
			LOD->RequiredModule->EmitterLoops = 1;
			LOD->RequiredModule->bKillOnDeactivate = false;
			SetPressureScalar(LOD->SpawnModule, LOD->SpawnModule->Rate, 0.0f);
			LOD->SpawnModule->BurstList.Reset();
			FParticleBurst Burst;
			Burst.Count = bSparks ? 24 : 4;
			Burst.CountLow = -1;
			Burst.Time = 0.0f;
			LOD->SpawnModule->BurstList.Add(Burst);
			for (UParticleModule* Module : LOD->Modules)
			{
				if (!Module || !Module->IsIn(Runtime)) { return nullptr; }
				if (UParticleModuleLifetime* Life = Cast<UParticleModuleLifetime>(Module))
				{
					UDistributionFloatUniform* Dist = NewObject<UDistributionFloatUniform>(Life, NAME_None, RF_Transient);
					Dist->Min = 0.12f;
					Dist->Max = 0.24f;
					Dist->bCanBeBaked = false;
					Life->Lifetime = FRawDistributionFloat();
					Life->Lifetime.Distribution = Dist;
				}
				else if (UParticleModuleSize* Size = Cast<UParticleModuleSize>(Module))
				{
					SetPressureVector(Size, Size->StartSize, FVector(bSparks ? 7.0f : 35.0f),
						FVector(bSparks ? 12.0f : 50.0f));
				}
				else if (UParticleModuleVelocity* Velocity = Cast<UParticleModuleVelocity>(Module))
				{
					SetPressureVector(Velocity, Velocity->StartVelocity, FVector(380.0f, -220.0f, -140.0f), FVector(1050.0f, 220.0f, 140.0f));
					Velocity->bInWorldSpace = false;
				}
				else if (UParticleModuleColor* Color = Cast<UParticleModuleColor>(Module))
				{
					const FVector Gold = bSparks ? FVector(5.0f, 3.8f, 1.2f) : FVector(3.0f, 2.3f, 0.65f);
					SetPressureVector(Color, Color->StartColor, Gold, Gold);
					SetPressureScalar(Color, Color->StartAlpha, bSparks ? 0.85f : 0.45f);
				}
			}
		}
		Emitter->UpdateModuleLists();
	}
	Cached = Runtime;
	return Runtime;
}

UParticleSystem* SparrowPresentation::GetMultishotFinishShards()
{
	static TWeakObjectPtr<UParticleSystem> Cached;
	if (Cached.IsValid()) { return Cached.Get(); }
	UParticleSystem* Source = GetReleaseShards();
	if (!Source) { return nullptr; }
	UParticleSystem* Runtime = DuplicateObject<UParticleSystem>(Source, GetTransientPackage(),
		MakeUniqueObjectName(GetTransientPackage(), UParticleSystem::StaticClass(), TEXT("P_SparrowMultishotFinishShards")));
	Runtime->SetFlags(RF_Transient);
	Runtime->ClearFlags(RF_Public | RF_Standalone);
	// 마지막 파동은 구름처럼 뭉치는 Wisps 대신 가는 불티가 진행 방향으로 빠르게 꺼지게 한다.
	Runtime->Emitters.RemoveAll([](UParticleEmitter* Emitter)
	{
		return !Emitter || Emitter->GetEmitterName() != TEXT("Sparks");
	});
	if (Runtime->Emitters.Num() != 1) { return nullptr; }
	UParticleEmitter* Emitter = Runtime->Emitters[0];
	if (!Emitter->IsIn(Runtime)) { return nullptr; }
	for (UParticleLODLevel* LOD : Emitter->LODLevels)
	{
		if (!LOD || !LOD->RequiredModule || !LOD->SpawnModule) { continue; }
		LOD->RequiredModule->EmitterDuration = 0.02f;
		LOD->SpawnModule->BurstList.Reset();
		FParticleBurst Burst;
		Burst.Count = 14;
		Burst.CountLow = -1;
		Burst.Time = 0.0f;
		LOD->SpawnModule->BurstList.Add(Burst);
		for (UParticleModule* Module : LOD->Modules)
		{
			if (!Module || !Module->IsIn(Runtime)) { return nullptr; }
			if (UParticleModuleLifetime* Life = Cast<UParticleModuleLifetime>(Module))
			{
				UDistributionFloatUniform* Distribution = NewObject<UDistributionFloatUniform>(Life, NAME_None, RF_Transient);
				Distribution->Min = 0.07f;
				Distribution->Max = 0.13f;
				Distribution->bCanBeBaked = false;
				Distribution->bIsDirty = false;
				Life->Lifetime = FRawDistributionFloat();
				Life->Lifetime.Distribution = Distribution;
			}
			else if (UParticleModuleSize* Size = Cast<UParticleModuleSize>(Module))
			{
				SetPressureVector(Size, Size->StartSize, FVector(4.0f), FVector(7.0f));
			}
			else if (UParticleModuleVelocity* Velocity = Cast<UParticleModuleVelocity>(Module))
			{
				SetPressureVector(Velocity, Velocity->StartVelocity, FVector(550.0f, -90.0f, -60.0f), FVector(950.0f, 90.0f, 60.0f));
			}
			else if (UParticleModuleColor* Color = Cast<UParticleModuleColor>(Module))
			{
				SetPressureScalar(Color, Color->StartAlpha, 0.70f);
			}
		}
	}
	Emitter->UpdateModuleLists();
	Cached = Runtime;
	return Runtime;
}

namespace
{
	UParticleSystem* GetTransferredHitFlare()
	{
		static TWeakObjectPtr<UParticleSystem> Cached;
		if (Cached.IsValid()) { return Cached.Get(); }
		UParticleSystem* Source = LoadObject<UParticleSystem>(nullptr,
			TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Ultimate/FX/P_Sparrow_UltHit.P_Sparrow_UltHit"));
		if (!Source) { return nullptr; }
		UParticleSystem* Runtime = DuplicateObject<UParticleSystem>(Source, GetTransientPackage(),
			MakeUniqueObjectName(GetTransientPackage(), UParticleSystem::StaticClass(), TEXT("P_SparrowTransferredRFlare")));
		Runtime->SetFlags(RF_Transient);
		Runtime->ClearFlags(RF_Public | RF_Standalone);
		Runtime->Emitters.RemoveAll([](UParticleEmitter* Emitter)
		{
			return !Emitter || Emitter->GetEmitterName() != TEXT("Flare");
		});
		if (Runtime->Emitters.Num() != 1) { return nullptr; }
		UParticleEmitter* Emitter = Runtime->Emitters[0];
		if (!Emitter->IsIn(Runtime)) { return nullptr; }
		for (UParticleLODLevel* LOD : Emitter->LODLevels)
		{
			if (!LOD || !LOD->RequiredModule || !LOD->SpawnModule) { continue; }
			LOD->RequiredModule->EmitterDuration = 0.02f;
			LOD->RequiredModule->EmitterLoops = 1;
			LOD->RequiredModule->bUseLocalSpace = false;
			SetPressureScalar(LOD->SpawnModule, LOD->SpawnModule->Rate, 0.0f);
			LOD->SpawnModule->BurstList.Reset();
			FParticleBurst Burst;
			Burst.Count = 1;
			Burst.CountLow = -1;
			Burst.Time = 0.0f;
			LOD->SpawnModule->BurstList.Add(Burst);
			// 원래 Flare의 재질/회전/크기 수명 곡선을 보존한다. 다른 emitter 위치 의존만 제거한다.
			LOD->Modules.RemoveAll([](UParticleModule* Module)
			{
				return Module && Module->GetClass()->GetFName() == TEXT("ParticleModuleLocationEmitter");
			});
			for (UParticleModule* Module : LOD->Modules)
			{
				if (!Module || !Module->IsIn(Runtime)) { return nullptr; }
				if (UParticleModuleLifetime* Life = Cast<UParticleModuleLifetime>(Module))
				{
					UDistributionFloatUniform* Distribution = NewObject<UDistributionFloatUniform>(Life, NAME_None, RF_Transient);
					Distribution->Min = 0.035f;
					Distribution->Max = 0.065f;
					Distribution->bCanBeBaked = false;
					Distribution->bIsDirty = false;
					Life->Lifetime = FRawDistributionFloat();
					Life->Lifetime.Distribution = Distribution;
				}
				else if (UParticleModuleSize* Size = Cast<UParticleModuleSize>(Module))
				{
					SetPressureVector(Size, Size->StartSize, FVector(42.0f), FVector(58.0f));
				}
				else if (UParticleModuleColor* Color = Cast<UParticleModuleColor>(Module))
				{
					const FVector Gold(2.8f, 2.2f, 0.85f);
					SetPressureVector(Color, Color->StartColor, Gold, Gold);
					SetPressureScalar(Color, Color->StartAlpha, 0.62f);
				}
			}
		}
		Emitter->UpdateModuleLists();
		Cached = Runtime;
		return Runtime;
	}
}

void SparrowPresentation::SpawnTransferredHitFlash(AActor* Owner, const FVector& Location, const FVector& Direction, bool bWorld)
{
	if (!IsValid(Owner) || Owner->IsActorBeingDestroyed() || !Owner->GetWorld() ||
		Location.ContainsNaN() || Direction.ContainsNaN()) { return; }
	FActorSpawnParameters Spawn;
	Spawn.Owner = Owner;
	Spawn.ObjectFlags |= RF_Transient;
	Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	if (ASparrowTransferredHitFlash* Flash = Owner->GetWorld()->SpawnActor<ASparrowTransferredHitFlash>(
		Location, Direction.Rotation(), Spawn))
	{
		Flash->Tags.Add(bWorld ? TEXT("SparrowTransferredWorldFlash") : TEXT("SparrowTransferredTargetFlash"));
	}
}

void SparrowPresentation::SpawnGearFlightCrackle(AActor* ArrowOwner, const FVector& Location, const FVector& Direction)
{
	if (!IsValid(ArrowOwner) || ArrowOwner->IsActorBeingDestroyed() || !ArrowOwner->GetWorld()) { return; }
	UParticleSystem* Template = GetTransferredHitFlare();
	if (!Template) { return; }
	// 명중의 같은 짧은 Flare를 비행에는 작은 한 점으로 쓴다. 소유 화살 종료 시 함께 제거된다.
	UParticleSystemComponent* Particle = NewObject<UParticleSystemComponent>(ArrowOwner);
	Particle->bAutoActivate = false;
	Particle->bAutoDestroy = true;
	Particle->SetTemplate(Template);
	Particle->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Particle->SetCanEverAffectNavigation(false);
	Particle->SetCastShadow(false);
	Particle->bOverrideLODMethod = true;
	Particle->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
	Particle->ComponentTags.Append({TEXT("SparrowSkillFX"), TEXT("SparrowGearFlightCrackle")});
	ArrowOwner->AddInstanceComponent(Particle);
	Particle->RegisterComponent();
	Particle->SetWorldLocationAndRotation(Location, Direction.Rotation());
	Particle->SetWorldScale3D(FVector(0.20f));
	Particle->SetLODLevel(0);
	Particle->ActivateSystem(true);
	Particle->SetLODLevel(0);
	FTimerHandle Cleanup;
	ArrowOwner->GetWorldTimerManager().SetTimer(Cleanup, FTimerDelegate::CreateWeakLambda(Particle, [Particle]()
	{
		Particle->DestroyComponent();
	}), 0.10f, false);
}

ASparrowMultishotBowTint::ASparrowMultishotBowTint()
{
	PrimaryActorTick.bCanEverTick = true;
	SetCanBeDamaged(false);
	SetActorEnableCollision(false);
	Tags.Add(TEXT("SparrowMultishotBowTint"));
}

void ASparrowMultishotBowTint::BeginPlay()
{
	Super::BeginPlay();
	ACharacter* Character = Cast<ACharacter>(GetOwner());
	if (!Character || !Character->GetMesh()) { Destroy(); return; }
	BowMesh = Character->GetMesh();
	// Rogue 실조회에서 M17_Bow는6번 활 단독 슬롯이다. 번호 대신 이름으로 검증해 몸 재질은 건드리지 않는다.
	BowMaterialSlot = BowMesh->GetMaterialIndex(TEXT("M17_Bow"));
	UMaterialInterface* Gold = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowAscensionGold.M_SparrowAscensionGold"));
	if (BowMaterialSlot == INDEX_NONE || !Gold) { Destroy(); return; }
	OriginalBowMaterial = BowMesh->GetMaterial(BowMaterialSlot);
	GoldBowMaterial = UMaterialInstanceDynamic::Create(Gold, this);
	BowMesh->SetMaterial(BowMaterialSlot, GoldBowMaterial);
}

void ASparrowMultishotBowTint::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!IsValid(GetOwner()) || !BowMesh.IsValid() || !GoldBowMaterial) { Destroy(); return; }
	UMaterialInterface* Current = BowMesh->GetMaterial(BowMaterialSlot);
	if (Current != GoldBowMaterial)
	{
		// R 중 S가 만료되면 S가 복원한 재질을 새 복구 기준으로 삼는다.
		OriginalBowMaterial = Current;
		BowMesh->SetMaterial(BowMaterialSlot, GoldBowMaterial);
	}
}

void ASparrowMultishotBowTint::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (BowMesh.IsValid() && BowMaterialSlot != INDEX_NONE && BowMesh->GetMaterial(BowMaterialSlot) == GoldBowMaterial)
	{
		BowMesh->SetMaterial(BowMaterialSlot, OriginalBowMaterial);
	}
	Super::EndPlay(EndPlayReason);
}

ASparrowTransferredHitFlash::ASparrowTransferredHitFlash()
{
	PrimaryActorTick.bCanEverTick = false;
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("ImpactPoint")));
	SetCanBeDamaged(false);
	Tags.Add(TEXT("SparrowTransferredHitFlash"));
	InitialLifeSpan = 0.35f;
}

void ASparrowTransferredHitFlash::BeginPlay()
{
	Super::BeginPlay();
	if (!IsValid(GetOwner()) || GetOwner()->IsActorBeingDestroyed()) { Destroy(); return; }
	FlashTemplate = GetTransferredHitFlare();
	if (!FlashTemplate) { Destroy(); return; }
	GetOwner()->OnDestroyed.AddDynamic(this, &ASparrowTransferredHitFlash::HandleOwnerDestroyed);
	SpawnPulse();
	GetWorldTimerManager().SetTimer(SecondPulseTimer, this, &ASparrowTransferredHitFlash::SpawnPulse, 0.055f, false);
	GetWorldTimerManager().SetTimer(ThirdPulseTimer, this, &ASparrowTransferredHitFlash::SpawnPulse, 0.11f, false);
}

void ASparrowTransferredHitFlash::SpawnPulse()
{
	if (!IsValid(GetOwner()) || GetOwner()->IsActorBeingDestroyed() || !FlashTemplate) { Destroy(); return; }
	constexpr float TransferredScale = 0.65f * (2.0f / 3.0f);
	UParticleSystemComponent* Particle = UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), FlashTemplate,
		GetActorLocation(), GetActorRotation(), FVector(TransferredScale), true, EPSCPoolMethod::None, false);
	if (!Particle) { return; }
	Particles.Add(Particle);
	Particle->ComponentTags.Append({TEXT("SparrowSkillFX"), TEXT("SparrowTransferredRFlare")});
	Particle->bOverrideLODMethod = true;
	Particle->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
	Particle->SetLODLevel(0);
	Particle->ActivateSystem(true);
	Particle->SetLODLevel(0);
	++PulseCount;
	UE_LOG(LogTemp, Display, TEXT("SPARROW_TRANSFERRED_FLASH owner=%s pulse=%d scale=%.6f"),
		*GetOwner()->GetName(), PulseCount, TransferredScale);
}

void ASparrowTransferredHitFlash::HandleOwnerDestroyed(AActor* DestroyedOwner)
{
	Destroy();
}

void ASparrowTransferredHitFlash::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	GetWorldTimerManager().ClearTimer(SecondPulseTimer);
	GetWorldTimerManager().ClearTimer(ThirdPulseTimer);
	if (IsValid(GetOwner())) { GetOwner()->OnDestroyed.RemoveDynamic(this, &ASparrowTransferredHitFlash::HandleOwnerDestroyed); }
	for (const TWeakObjectPtr<UParticleSystemComponent>& Particle : Particles)
	{
		if (Particle.IsValid()) { Particle->DestroyComponent(); }
	}
	Super::EndPlay(EndPlayReason);
}

void USparrowShotRecoil::GetShakePatternInfoImpl(FCameraShakeInfo& OutInfo) const
{
	OutInfo.Duration = FCameraShakeDuration(0.24f);
	OutInfo.BlendOut = 0.06f;
}

void USparrowShotRecoil::StartShakePatternImpl(const FCameraShakePatternStartParams& Params)
{
	Age = 0.0f;
}

void USparrowShotRecoil::UpdateShakePatternImpl(const FCameraShakePatternUpdateParams& Params, FCameraShakePatternUpdateResult& OutResult)
{
	Age += Params.DeltaTime;
	const float Envelope = FMath::Square(FMath::Clamp(1.0f - Age / 0.24f, 0.0f, 1.0f));
	const float Kick = (1.0f - FMath::Exp(-100.0f * Age)) * FMath::Exp(-18.0f * Age);
	OutResult.Location = FVector(-12.0f * Kick, 5.0f * FMath::Sin(95.0f * Age) * Envelope,
		3.0f * FMath::Sin(75.0f * Age) * Envelope);
	OutResult.Rotation = FRotator(-0.8f * Kick, 0.25f * FMath::Sin(85.0f * Age) * Envelope,
		0.12f * FMath::Sin(65.0f * Age) * Envelope);
	OutResult.FOV = 0.35f * Kick;
}

USparrowShotCameraShake::USparrowShotCameraShake(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer)
{
	bSingleInstance = true;
	SetRootShakePattern(CreateDefaultSubobject<USparrowShotRecoil>(TEXT("Recoil")));
}

ASparrowShotWave::ASparrowShotWave()
{
	PrimaryActorTick.bCanEverTick = true;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Plane(TEXT("/Engine/BasicShapes/Plane.Plane"));
	AirMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowShotSplitRing.M_SparrowShotSplitRing")));
	for (int32 Index = 0; Index < 2; ++Index)
	{
		UStaticMeshComponent* Wave = CreateDefaultSubobject<UStaticMeshComponent>(*FString::Printf(TEXT("AirWave%d"), Index));
		Wave->SetupAttachment(RootComponent);
		Wave->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Wave->SetGenerateOverlapEvents(false);
		Wave->SetCanEverAffectNavigation(false);
		Wave->SetStaticMesh(Plane.Object);
		Wave->SetCastShadow(false);
		Wave->SetRelativeRotation(FRotator(90.0f, 0.0f, 0.0f));
		Wave->SetVisibility(false);
		Waves.Add(Wave);
	}
	AxialFlash = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("AxialFlash"));
	AxialFlash->SetupAttachment(RootComponent);
	AxialFlash->SetStaticMesh(Plane.Object);
	AxialFlash->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	AxialFlash->SetGenerateOverlapEvents(false);
	AxialFlash->SetCanEverAffectNavigation(false);
	AxialFlash->SetCastShadow(false);
	AxialFlash->SetRelativeLocation(FVector(170.0f, 0.0f, 0.0f));
	AxialFlash->SetRelativeScale3D(FVector(3.4f, 0.30f, 1.0f));
	AxialFlash->SetVisibility(false);
	Tags.Add(TEXT("SparrowShotWave"));
	InitialLifeSpan = 0.24f;
}

void ASparrowShotWave::BeginPlay()
{
	Super::BeginPlay();
	bRenaissance = bPreparation || CVarRenaissanceW.GetValueOnGameThread() == 1;
	if (bRenaissance && IsValid(GetOwner()))
	{
		const TCHAR* Folder = TEXT("/Game/TopDown/Characters/Sparrow/Materials/Renaissance20261027/");
		for (int32 Index = 0; Index < 4; ++Index)
		{
			const bool bLip = Index < 2;
			UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *(FString(Folder) + (bLip ? TEXT("SM_RenWPressure") : TEXT("SM_RenRail"))));
			UMaterialInterface* Source = LoadObject<UMaterialInterface>(nullptr, *(FString(Folder) + (bLip ? TEXT("M_RenWPressure") : TEXT("M_RenRail"))));
			if (!Mesh || !Source) { Destroy(); return; }
			UStaticMeshComponent* Part = NewObject<UStaticMeshComponent>(this, NAME_None, RF_Transient);
			Part->SetMobility(EComponentMobility::Movable);
			Part->SetupAttachment(RootComponent);
			Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			Part->SetGenerateOverlapEvents(false);
			Part->SetCanEverAffectNavigation(false);
			Part->SetCastShadow(false);
			Part->SetReceivesDecals(false);
			Part->SetStaticMesh(Mesh);
			Part->SetVisibility(false);
			AddInstanceComponent(Part);
			Part->RegisterComponent();
			UMaterialInstanceDynamic* Dynamic = Part->CreateDynamicMaterialInstance(0, Source);
			Dynamic->SetScalarParameterValue(TEXT("Index"), Index);
			PressureLips.Add(Part);
			LipMaterials.Add(Dynamic);
		}
		Tags.Add(TEXT("SparrowRenaissanceW"));
		if (bPreparation)
		{
			Tags.Add(TEXT("SparrowRenaissanceWPreparation"));
			SetLifeSpan(PreparationSeconds + .015f);
		}
		return;
	}
	UMaterialInterface* Material = AirMaterial.LoadSynchronous();
	if (!Material || !IsValid(GetOwner()))
	{
		Destroy();
		return;
	}
	for (UStaticMeshComponent* Wave : Waves)
	{
		UMaterialInstanceDynamic* Dynamic = Wave->CreateDynamicMaterialInstance(0, Material);
		if (!Dynamic)
		{
			Destroy();
			return;
		}
		Dynamic->SetScalarParameterValue(TEXT("Envelope"), 0.0f);
		Materials.Add(Dynamic);
	}
	if (UMaterialInterface* Flash = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowShotWindAxis.M_SparrowShotWindAxis")))
	{
		FlashMaterial = AxialFlash->CreateDynamicMaterialInstance(0, Flash);
		if (FlashMaterial) { FlashMaterial->SetScalarParameterValue(TEXT("Envelope"), 0.0f); }
	}
	if (UParticleSystem* Pressure = GetReleasePressure())
	{
		UParticleSystemComponent* Particle = UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), Pressure,
			GetActorLocation() + GetActorForwardVector() * 30.0f, GetActorRotation(), FVector(1.0f), true, EPSCPoolMethod::None, false);
		if (Particle)
		{
			PressureEffect = Particle;
			Particle->ComponentTags.Append({TEXT("SparrowSkillFX"), TEXT("SparrowReleasePressure")});
			Particle->bOverrideLODMethod = true;
			Particle->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
			Particle->SetLODLevel(0);
			Particle->ActivateSystem(true);
			Particle->SetLODLevel(0);
			FTimerHandle Cleanup;
			GetWorldTimerManager().SetTimer(Cleanup, FTimerDelegate::CreateWeakLambda(Particle, [Particle]()
			{
				Particle->DestroyComponent();
			}), 0.30f, false);
		}
	}
	if (UParticleSystem* Shards = SparrowPresentation::GetReleaseShards())
	{
		UParticleSystemComponent* Particle = UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), Shards,
			GetActorLocation(), GetActorRotation(), FVector(1.0f), true, EPSCPoolMethod::None, false);
		if (Particle)
		{
			ShardEffect = Particle;
			Particle->ComponentTags.Append({TEXT("SparrowSkillFX"), TEXT("SparrowReleaseShards")});
			Particle->bOverrideLODMethod = true;
			Particle->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
			Particle->SetLODLevel(0);
			Particle->ActivateSystem(true);
			Particle->SetLODLevel(0);
			FTimerHandle Cleanup;
			GetWorldTimerManager().SetTimer(Cleanup, FTimerDelegate::CreateWeakLambda(Particle, [Particle]()
			{
				Particle->DestroyComponent();
			}), 0.30f, false);
		}
	}
	const APawn* Pawn = Cast<APawn>(GetOwner());
	APlayerController* Controller = Pawn ? Cast<APlayerController>(Pawn->GetController()) : nullptr;
	if (Controller && Controller->IsLocalController() && Controller->PlayerCameraManager)
	{
		Camera = Controller->PlayerCameraManager;
		Shake = Camera->StartCameraShake(USparrowShotCameraShake::StaticClass(), .4f);
	}
}

void ASparrowShotWave::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!IsValid(GetOwner()))
	{
		Destroy();
		return;
	}
	Age += DeltaSeconds;
	if (bRenaissance)
	{
		if (bPreparation)
		{
			if (const USparrowSkillComponent* Skills = GetOwner()->FindComponentByClass<USparrowSkillComponent>())
			{
				if (Skills->GetActiveSkillNumber() != 2) { Destroy(); return; }
				SetActorLocation(Skills->GetArrowOrigin());
			}
			const float Progress = FMath::Clamp(Age / PreparationSeconds, 0.0f, 1.0f);
			const float Draw = FMath::SmoothStep(.1f, .92f, Progress);
			const float Live = FMath::SmoothStep(0.0f, .20f, Progress) * (1.0f - FMath::SmoothStep(.90f, 1.0f, Progress));
			for (int32 Index = 0; Index < PressureLips.Num(); ++Index)
			{
				const bool bLip = Index < 2;
				PressureLips[Index]->SetRelativeLocation(FVector(-91.0f + Draw * 80.0f, 0, bLip ? 0.0f : (Index == 2 ? -1.0f : 1.0f) * (22.0f - Draw * 17.0f)));
				PressureLips[Index]->SetRelativeRotation(FRotator(0, 0, bLip ? 35.0f + Index * 90.0f - Draw * 32.0f : Index * 90.0f));
				const float Radius = 1.30f - Draw * .95f;
				PressureLips[Index]->SetRelativeScale3D(bLip ? FVector(.95f - Draw * .50f, Radius, Radius) : FVector(.70f - Draw * .30f, .60f, .60f));
				PressureLips[Index]->SetVisibility(Live > .001f);
				LipMaterials[Index]->SetScalarParameterValue(TEXT("Age"), Age);
				LipMaterials[Index]->SetScalarParameterValue(TEXT("Envelope"), Live * (bLip ? .95f : .55f));
			}
			return;
		}
		for (int32 Index = 0; Index < PressureLips.Num(); ++Index)
		{
			const bool bLip = Index < 2;
			const float LocalAge = Age - (Index == 1 ? .020f : 0.0f);
			const float Progress = FMath::Clamp(LocalAge / .19f, 0.0f, 1.0f);
			const float Open = FMath::SmoothStep(0.0f, .025f, LocalAge);
			const float Fade = 1.0f - FMath::SmoothStep(.065f, .205f, LocalAge);
			PressureLips[Index]->SetRelativeLocation(bLip ? FVector(-29.0f + Progress * 94.0f, 0, 0) : FVector(20.0f, 0, (Index == 2 ? -1.0f : 1.0f) * 12.0f));
			PressureLips[Index]->SetRelativeRotation(FRotator(0, 0, bLip ? 35.0f + Index * 90.0f + Progress * 25.0f : Index * 90.0f));
			const float Radius = (Index == 1 ? .70f : 1.0f) * (.48f + Open * .42f + Progress * .35f);
			PressureLips[Index]->SetRelativeScale3D(bLip ? FVector(.52f + Progress * .78f, Radius, Radius) : FVector(.8f + Open * .65f, .55f, .55f));
			PressureLips[Index]->SetVisibility(LocalAge > 0.0f && Fade > .001f);
			LipMaterials[Index]->SetScalarParameterValue(TEXT("Age"), Age);
			LipMaterials[Index]->SetScalarParameterValue(TEXT("Envelope"), Open * Fade * (Index == 1 ? .62f : 1.0f));
		}
		return;
	}
	for (int32 Index = 0; Index < Materials.Num(); ++Index)
	{
		const float LocalAge = Age - Index * 0.012f;
		const float Progress = FMath::Clamp(LocalAge / 0.14f, 0.0f, 1.0f);
		const bool bVisible = LocalAge > 0.0f && Progress < 1.0f;
		Waves[Index]->SetVisibility(bVisible);
		Waves[Index]->SetRelativeLocation(FVector(-35.0f + Index * 60.0f + LocalAge * 420.0f, 0.0f, 0.0f));
		const float Diameter = (Index == 0 ? 3.15f : 2.05f) - (Index == 0 ? 1.5f : 1.1f) * Progress;
		Waves[Index]->SetRelativeScale3D(FVector(Diameter, Diameter, 1.0f));
		const float FadeIn = FMath::Clamp(LocalAge / 0.012f, 0.0f, 1.0f);
		const float FadeOut = 1.0f - FMath::Clamp((LocalAge - 0.035f) / 0.105f, 0.0f, 1.0f);
		Materials[Index]->SetScalarParameterValue(TEXT("Envelope"),
			bVisible ? FadeIn * FadeOut * (Index == 0 ? 0.85f : 0.46f) : 0.0f);
	}
	if (FlashMaterial)
	{
		AxialFlash->SetVisibility(Age < 0.10f);
		FlashMaterial->SetScalarParameterValue(TEXT("Envelope"),
			0.42f * FMath::Square(FMath::Clamp(1.0f - Age / 0.10f, 0.0f, 1.0f)));
	}
}

void ASparrowShotWave::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (ShardEffect.IsValid())
	{
		if (!IsValid(GetOwner()) || GetOwner()->IsActorBeingDestroyed()) { ShardEffect->DestroyComponent(); }
		else { ShardEffect->DeactivateSystem(); }
	}
	if (PressureEffect.IsValid())
	{
		if (!IsValid(GetOwner()) || GetOwner()->IsActorBeingDestroyed() || EndPlayReason != EEndPlayReason::Destroyed)
		{
			PressureEffect->DestroyComponent();
		}
		else { PressureEffect->DeactivateSystem(); }
	}
	if (Camera.IsValid() && Shake.IsValid())
	{
		Camera->StopCameraShake(Shake.Get(), true);
	}
	Super::EndPlay(EndPlayReason);
}

ASparrowBowFeedback::ASparrowBowFeedback()
{
	PrimaryActorTick.bCanEverTick = true;
	Surface = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("FeedbackSurface"));
	SetRootComponent(Surface);
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Plane(TEXT("/Engine/BasicShapes/Plane.Plane"));
	Surface->SetStaticMesh(Plane.Object);
	Surface->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Surface->SetGenerateOverlapEvents(false);
	Surface->SetCanEverAffectNavigation(false);
	Surface->SetCastShadow(false);
	RingMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowShotAirStrong.M_SparrowShotAirStrong")));
	FanMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowVolleyFan.M_SparrowVolleyFan")));
	InitialLifeSpan = 1.4f;
}

void ASparrowBowFeedback::BeginPlay()
{
	Super::BeginPlay();
	UMaterialInterface* Source = bRapidMode ? RingMaterial.LoadSynchronous() : FanMaterial.LoadSynchronous();
	Material = Source ? Surface->CreateDynamicMaterialInstance(0, Source) : nullptr;
	if (!Material || !IsValid(GetOwner())) { Destroy(); return; }
	Tags.Add(bRapidMode ? TEXT("SparrowRapidRing") : TEXT("SparrowVolleyFan"));
	if (!bRapidMode)
	{
		SetLifeSpan(0.32f);
		SetActorLocation(GetActorLocation() + GetActorForwardVector() * 350.0f);
	}
	Material->SetScalarParameterValue(TEXT("Envelope"), 0.0f);
}

void ASparrowBowFeedback::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	ACharacter* Character = Cast<ACharacter>(GetOwner());
	if (!Character || !Material) { Destroy(); return; }
	Age += DeltaSeconds;
	PulseAge += DeltaSeconds;
	if (bRapidMode)
	{
		USparrowSkillComponent* Skills = Character->FindComponentByClass<USparrowSkillComponent>();
		if (!Skills || Skills->GetActiveSkillNumber() != 3) { Destroy(); return; }
		const FRotator Facing(0, Character->GetActorRotation().Yaw, 0);
		SetActorLocationAndRotation(Skills->GetArrowOrigin() + Facing.Vector() * 35.0f, FRotator(90, Facing.Yaw, 0));
		const float Pulse = FMath::Clamp(1.0f - PulseAge / 0.16f, 0.0f, 1.0f);
		Surface->SetWorldScale3D(FVector(1.45f + 0.35f * (1.0f - Pulse), 1.45f + 0.35f * (1.0f - Pulse), 1));
		Material->SetScalarParameterValue(TEXT("Envelope"), (0.2f + 1.35f * Pulse) * FMath::Clamp((1.08f - Age) / 0.20f, 0.0f, 1.0f));
	}
	else
	{
		const float Progress = FMath::Clamp(Age / 0.27f, 0.0f, 1.0f);
		Surface->SetWorldScale3D(FVector(7.0f, 6.3f, 1));
		Material->SetScalarParameterValue(TEXT("Progress"), FMath::Min(1.05f, Age / 0.16f));
		Material->SetScalarParameterValue(TEXT("Envelope"), FMath::Pow(1.0f - Progress, 0.7f));
	}
}
