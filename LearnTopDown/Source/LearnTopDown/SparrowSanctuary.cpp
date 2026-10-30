#include "SparrowSanctuary.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "Kismet/GameplayStatics.h"
#include "KwangTrainingDummy.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Navigation/PathFollowingComponent.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "Particles/ParticleEmitter.h"
#include "Particles/ParticleLODLevel.h"
#include "Particles/ParticleModuleRequired.h"
#include "SparrowSkillComponent.h"
#include "SparrowArrow.h"

namespace
{
	constexpr float BindArrival = 0.25f;
	constexpr float BindSeconds = 2.0f;
	constexpr float GuardEntry = 0.18f;
	constexpr float GuardSeconds = 2.2f;
	constexpr float GuardWidth = 160.0f;
	constexpr float GuardHeight = 125.0f;
	constexpr float CounterDamage = 12.0f;
	const TCHAR* Fine = TEXT("/Game/TopDown/Characters/Sparrow/Previews/WRefined20261022/M_WOptionA1.M_WOptionA1");
	const TCHAR* Glyph = TEXT("/Game/TopDown/Characters/Sparrow/Previews/WRefined20261022/M_WOptionA2.M_WOptionA2");
	const TCHAR* Line = TEXT("/Game/TopDown/Characters/Gideon/FX/M_NoxGlowStrip.M_NoxGlowStrip");
	struct FRootLease
	{
		int32 Users = 0;
		bool bTickEnabled = false;
		TWeakObjectPtr<UPathFollowingComponent> Path;
		FAIRequestID Request;
		bool bPaused = false;
	};
	TMap<TWeakObjectPtr<UCharacterMovementComponent>, FRootLease> RootLeases;
	TMap<TWeakObjectPtr<AKwangTrainingDummy>, int32> DummyLeases;
	TArray<TWeakObjectPtr<ASparrowSanctuary>> ActiveGuards;

	UParticleSystem* GetSanctuarySparks()
	{
		static TWeakObjectPtr<UParticleSystem> Cached;
		if (Cached.IsValid()) { return Cached.Get(); }
		UParticleSystem* Source = LoadObject<UParticleSystem>(nullptr,
			TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Ultimate/FX/P_Sparrow_UltHit.P_Sparrow_UltHit"));
		if (!Source) { return nullptr; }
		UParticleSystem* Copy = DuplicateObject<UParticleSystem>(Source, GetTransientPackage(),
			MakeUniqueObjectName(GetTransientPackage(), UParticleSystem::StaticClass(), TEXT("P_SparrowSanctuarySparks")));
		Copy->SetFlags(RF_Transient);
		Copy->ClearFlags(RF_Public | RF_Standalone);
		Copy->Emitters.RemoveAll([](UParticleEmitter* Emitter)
		{
			return !Emitter || (Emitter->GetEmitterName() != TEXT("Sparks") &&
				Emitter->GetEmitterName() != TEXT("SparkTrailHeads") && Emitter->GetEmitterName() != TEXT("Wisps"));
		});
		if (Copy->Emitters.IsEmpty()) { return nullptr; }
		for (UParticleEmitter* Emitter : Copy->Emitters)
		{
			if (!Emitter->IsIn(Copy)) { return nullptr; }
			for (UParticleLODLevel* LOD : Emitter->LODLevels)
			{
				if (!LOD || !LOD->RequiredModule || !LOD->RequiredModule->IsIn(Copy)) { return nullptr; }
				LOD->RequiredModule->bKillOnDeactivate = false;
			}
			Emitter->UpdateModuleLists();
		}
		Cached = Copy;
		return Copy;
	}
}

ASparrowSanctuary::ASparrowSanctuary()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickGroup = TG_PrePhysics;
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
	SetActorEnableCollision(false);
	SetCanBeDamaged(false);
	Tags.Add(TEXT("SparrowSanctuary"));
	Tags.Add(TEXT("SparrowSkillFX"));
}

bool ASparrowSanctuary::Initialize(ACharacter* Character, int32 Slot, const FVector& Aim, AActor* Target)
{
	if (!IsValid(Character) || !Character->GetMesh() || !GetWorld() || (Slot != 9 && Slot != 11)) { return false; }
	Caster = Character;
	SkillSlot = Slot;
	BoundTarget = Target;
	CastOrigin = Character->GetMesh()->DoesSocketExist(TEXT("arrow_anchor")) ?
		Character->GetMesh()->GetSocketLocation(TEXT("arrow_anchor")) : Character->GetActorLocation();
	CastDirection = (Aim - Character->GetActorLocation()).GetSafeNormal2D();
	if (CastDirection.IsNearlyZero()) { CastDirection = Character->GetActorForwardVector(); }
	const int32 Rings = Slot == 9 ? 4 : 3;
	for (int32 Index = 0; Index < Rings; ++Index)
	{
		if (!CreatePlane(Index < 2 ? Glyph : Fine, false)) { return false; }
	}
	for (int32 Index = 0; Index < (Slot == 9 ? 17 : 8); ++Index)
	{
		if (!CreatePlane(Line, true)) { return false; }
	}
	StartedAt = GetWorld()->GetTimeSeconds();
	SetLifeSpan(Slot == 9 ? BindArrival + BindSeconds + 0.45f : GuardEntry + GuardSeconds + 0.35f);
	return Slot != 9 || BoundTarget.IsValid();
}

UStaticMeshComponent* ASparrowSanctuary::CreatePlane(const TCHAR* Material, bool bLine)
{
	UMaterialInterface* Source = LoadObject<UMaterialInterface>(nullptr, Material);
	UStaticMesh* Plane = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
	if (!Source || !Plane) { return nullptr; }
	UStaticMeshComponent* Mesh = NewObject<UStaticMeshComponent>(this, NAME_None, RF_Transient);
	Mesh->SetMobility(EComponentMobility::Movable);
	Mesh->SetupAttachment(RootComponent);
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Mesh->SetGenerateOverlapEvents(false);
	Mesh->SetCanEverAffectNavigation(false);
	Mesh->SetCastShadow(false);
	Mesh->SetReceivesDecals(false);
	Mesh->SetStaticMesh(Plane);
	AddInstanceComponent(Mesh);
	Mesh->RegisterComponent();
	UMaterialInstanceDynamic* Mid = UMaterialInstanceDynamic::Create(Source, this);
	Mesh->SetMaterial(0, Mid);
	if (bLine)
	{
		Mid->SetVectorParameterValue(TEXT("CoreColor"), FLinearColor(1.0f, 0.90f, 0.60f));
		Mid->SetVectorParameterValue(TEXT("GlowColor"), FLinearColor(1.0f, 0.60f, 0.12f));
		Mid->SetScalarParameterValue(TEXT("CoreSharpness"), 6.0f);
		Mid->SetScalarParameterValue(TEXT("GlowSoftness"), 1.7f);
		Mid->SetScalarParameterValue(TEXT("CoreIntensity"), 0.0f);
		Mid->SetScalarParameterValue(TEXT("GlowIntensity"), 0.0f);
		LineMeshes.Add(Mesh);
		LineMaterials.Add(Mid);
	}
	else
	{
		Mid->SetScalarParameterValue(TEXT("Strength"), 0.0f);
		RingMeshes.Add(Mesh);
		RingMaterials.Add(Mid);
	}
	return Mesh;
}

void ASparrowSanctuary::BeginPlay()
{
	Super::BeginPlay();
	if (!Caster.IsValid()) { Destroy(); return; }
	if (SkillSlot == 11)
	{
		ActiveGuards.AddUnique(this);
	}
}

bool ASparrowSanctuary::IsCasting() const
{
	return GetWorld() && !IsActorBeingDestroyed() && GetWorld()->GetTimeSeconds() - StartedAt < (SkillSlot == 9 ? 0.42f : 0.32f);
}

float ASparrowSanctuary::GetRemainingSeconds() const
{
	if (!GetWorld()) { return 0.0f; }
	return FMath::Max(0.0f, (SkillSlot == 9 ? BindArrival + BindSeconds : GuardEntry + GuardSeconds) -
		static_cast<float>(GetWorld()->GetTimeSeconds() - StartedAt));
}

void ASparrowSanctuary::ApplyBinding()
{
	if (!Caster.IsValid() || !BoundTarget.IsValid()) { Destroy(); return; }
	AActor* Target = BoundTarget.Get();
	const USparrowSkillComponent* Skills = Caster->FindComponentByClass<USparrowSkillComponent>();
	const AKwangTrainingDummy* DummyCheck = Cast<AKwangTrainingDummy>(Target);
	if (!Skills || !Target->CanBeDamaged() || (DummyCheck && !DummyCheck->IsAlive()) ||
		!Skills->HasWorldLineOfSight(CastOrigin, Target->GetActorLocation(), Target) ||
		FVector::DistSquared2D(Caster->GetActorLocation(), Target->GetActorLocation()) > FMath::Square(900.0f)) { Destroy(); return; }
	bCommitted = true;
	if (ACharacter* Character = Cast<ACharacter>(Target))
	{
		BoundMovement = Character->GetCharacterMovement();
		if (BoundMovement.IsValid())
		{
			FRootLease& Lease = RootLeases.FindOrAdd(BoundMovement);
			if (Lease.Users++ == 0)
			{
				Lease.bTickEnabled = BoundMovement->IsComponentTickEnabled();
				const bool bAbortPaths = BoundMovement->GetNavMovementProperties()->bStopMovementAbortPaths;
				Lease.Path = Character->GetController() ? Character->GetController()->FindComponentByClass<UPathFollowingComponent>() : nullptr;
				if (Lease.Path.IsValid() && Lease.Path->GetStatus() == EPathFollowingStatus::Moving)
				{
					Lease.Request = Lease.Path->GetCurrentRequestId();
					Lease.Path->PauseMove(Lease.Request);
					Lease.bPaused = true;
				}
				// StopMovementImmediately는 AI 요청을 Abort한다. 원래 경로/이동 모드는 그대로 두고 tick을 잠근다.
				BoundMovement->StopMovementKeepPathing();
				BoundMovement->GetNavMovementProperties()->bStopMovementAbortPaths = bAbortPaths;
				BoundMovement->ClearAccumulatedForces();
				BoundMovement->ConsumeInputVector();
				BoundMovement->SetComponentTickEnabled(false);
			}
			bBindingLease = true;
		}
	}
	if (AKwangTrainingDummy* Dummy = Cast<AKwangTrainingDummy>(Target))
	{
		StatusDummy = Dummy;
		// 공용 ROOT/STUN 표식과 구분한다. 겹친 결박 중 마지막 소유자만 자신의 표식을 지운다.
		const TWeakObjectPtr<AKwangTrainingDummy> Key(Dummy);
		if (int32* Users = DummyLeases.Find(Key))
		{
			++*Users;
			bDummyStatusOwned = true;
			if (Dummy->GetCombatStatus() == TEXT("GOLD_BIND")) { Dummy->SetCombatStatus(TEXT("GOLD_BIND"), BindSeconds); }
		}
		else if (Dummy->GetCombatStatus().IsNone())
		{
			DummyLeases.Add(Key, 1);
			Dummy->SetCombatStatus(TEXT("GOLD_BIND"), BindSeconds);
			bDummyStatusOwned = true;
		}
	}
	UGameplayStatics::ApplyDamage(Target, 12.0f, Caster->GetController(), this, nullptr);
	Pulse(Target->GetActorLocation(), FVector::UpVector, 0.70f);
}

void ASparrowSanctuary::ReleaseBinding()
{
	if (bReleased) { return; }
	bReleased = true;
	if (bBindingLease)
	{
		if (FRootLease* Lease = RootLeases.Find(BoundMovement))
		{
			if (--Lease->Users <= 0)
			{
				if (BoundMovement.IsValid())
				{
					BoundMovement->ClearAccumulatedForces();
					BoundMovement->ConsumeInputVector();
					BoundMovement->SetComponentTickEnabled(Lease->bTickEnabled);
				}
				if (Lease->bPaused && Lease->Path.IsValid() && Lease->Path->GetStatus() == EPathFollowingStatus::Paused &&
					Lease->Path->GetCurrentRequestId() == Lease->Request) { Lease->Path->ResumeMove(Lease->Request); }
				RootLeases.Remove(BoundMovement);
			}
		}
		bBindingLease = false;
	}
	if (bDummyStatusOwned)
	{
		if (int32* Users = DummyLeases.Find(StatusDummy))
		{
			if (--*Users <= 0)
			{
				DummyLeases.Remove(StatusDummy);
				if (StatusDummy.IsValid() && StatusDummy->GetCombatStatus() == TEXT("GOLD_BIND"))
				{
					StatusDummy->SetCombatStatus(NAME_None, 0.01f);
				}
			}
		}
		bDummyStatusOwned = false;
	}
}

bool ASparrowSanctuary::CanInterceptProjectile(const AActor* Projectile) const
{
	if (SkillSlot != 11 || !Caster.IsValid() || !GetWorld() || !IsValid(Projectile) ||
		Projectile->IsActorBeingDestroyed() || Projectile->GetWorld() != GetWorld()) { return false; }
	const float Age = static_cast<float>(GetWorld()->GetTimeSeconds() - StartedAt);
	if (Age < GuardEntry || Age >= GuardEntry + GuardSeconds) { return false; }
	const AActor* Shooter = Projectile->GetOwner();
	return IsValid(Shooter) && Shooter != Caster.Get() && Projectile->GetInstigator() != Caster.Get() &&
		!Shooter->IsOwnedBy(Caster.Get()) && (!Caster->GetController() || Projectile->GetInstigatorController() != Caster->GetController());
}

ASparrowSanctuary* ASparrowSanctuary::FindInterception(AActor* Projectile, const FVector& Start, const FVector& End,
	float& Fraction, FVector& Contact)
{
	ASparrowSanctuary* Nearest = nullptr;
	Fraction = 1.0f;
	const FVector Delta = End - Start;
	for (int32 Index = ActiveGuards.Num() - 1; Index >= 0; --Index)
	{
		ASparrowSanctuary* Guard = ActiveGuards[Index].Get();
		if (!Guard) { ActiveGuards.RemoveAtSwap(Index); continue; }
		if (!Guard->CanInterceptProjectile(Projectile) ||
			FVector::DotProduct(Delta.GetSafeNormal(), Guard->CastDirection) >= -0.05f) { continue; }
		const FVector Center = Guard->Caster->GetActorLocation() + Guard->CastDirection * 110.0f + FVector(0.0f, 0.0f, 45.0f);
		const float Distance = FVector::DotProduct(Start - Center, Guard->CastDirection);
		const float Approach = -FVector::DotProduct(Delta, Guard->CastDirection);
		if (Distance < -22.0f || Approach <= 0.0f || Distance - Approach > 22.0f) { continue; }
		// 기존 22cm 전후 두께의 앞면에 들어오는 시각을 실제 Sweep Hit.Time과 비교한다.
		const float Time = FMath::Clamp((Distance - 22.0f) / Approach, 0.0f, 1.0f);
		if (Time > Fraction) { continue; }
		const FVector Point = Start + Delta * Time;
		const FVector Offset = Point - Center;
		const FVector Side = FVector::CrossProduct(FVector::UpVector, Guard->CastDirection);
		const float Lateral = FVector::DotProduct(Offset, Side) / GuardWidth;
		const float Vertical = Offset.Z / GuardHeight;
		if (Lateral * Lateral + Vertical * Vertical > 1.0f) { continue; }
		Nearest = Guard;
		Fraction = Time;
		Contact = Point;
	}
	return Nearest;
}

bool ASparrowSanctuary::TryIntercept(AActor* Projectile, const FVector& Contact)
{
	if (!CanInterceptProjectile(Projectile)) { return false; }
	AActor* Shooter = Projectile->GetOwner();
	bCommitted = true;
	++BlockedProjectiles;
	CounterPulseUntil = static_cast<float>(GetWorld()->GetTimeSeconds() - StartedAt) + 0.22f;
	Pulse(Contact, CastDirection, 0.85f);
	if (USparrowSkillComponent* Skills = Caster->FindComponentByClass<USparrowSkillComponent>())
	{
		const FVector CounterDirection = (Shooter->GetActorLocation() - Contact).GetSafeNormal();
		const FVector Origin = Contact + CastDirection * 28.0f;
		if (ASparrowArrow* Counter = Skills->SpawnArrow(CounterDirection, CounterDamage, 1800.0f, Skills->ArrowSpeed,
			false, false, false, false, &Origin, false))
		{
			Counter->Tags.Add(TEXT("SparrowSanctuaryCounter"));
			++CounterShots;
		}
	}
	// 투사체 자신이 기존 Hit 처리 사이에서 진행 거리/위치를 갱신한 뒤 종료한다.
	return true;
}

void ASparrowSanctuary::PlaceRing(int32 Index, const FVector& Position, const FVector& Normal, float Spin,
	const FVector& Scale, float Strength)
{
	const FQuat Rotation = FRotationMatrix::MakeFromZ(Normal).ToQuat() * FQuat(FVector::UpVector, FMath::DegreesToRadians(Spin));
	RingMeshes[Index]->SetWorldLocationAndRotation(Position, Rotation);
	RingMeshes[Index]->SetWorldScale3D(Scale);
	RingMaterials[Index]->SetScalarParameterValue(TEXT("Strength"), FMath::Max(0.0f, Strength));
}

void ASparrowSanctuary::PlaceLine(int32 Index, const FVector& Start, const FVector& End, float Width, float Strength)
{
	const FVector Center = (Start + End) * 0.5f;
	const FVector Delta = End - Start;
	const APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(GetWorld(), 0);
	const FVector Normal = Camera ? Camera->GetCameraLocation() - Center : FVector::UpVector;
	LineMeshes[Index]->SetWorldLocationAndRotation(Center, FRotationMatrix::MakeFromXZ(Delta, Normal).Rotator());
	LineMeshes[Index]->SetWorldScale3D(FVector(FMath::Max(Delta.Size(), 0.01) * 1.035 / 100.0, Width / 100.0f, 1.0f));
	LineMaterials[Index]->SetScalarParameterValue(TEXT("CoreIntensity"), Strength);
	LineMaterials[Index]->SetScalarParameterValue(TEXT("GlowIntensity"), Strength * 0.16f);
}

void ASparrowSanctuary::UpdateBindingVisual(float Age)
{
	const FVector Target = BoundTarget->GetActorLocation();
	const float Open = FMath::SmoothStep(0.18f, 0.48f, Age);
	const float Fade = 1.0f - FMath::SmoothStep(BindArrival + BindSeconds, BindArrival + BindSeconds + 0.4f, Age);
	const float Contract = 1.0f - FMath::SmoothStep(BindArrival, 0.70f, Age);
	for (int32 Index = 0; Index < RingMeshes.Num(); ++Index)
	{
		const FVector Normal = Index < 2 ? FVector::UpVector : (Index == 2 ? FVector::ForwardVector : FVector::RightVector);
		const float Height = Index < 2 ? (Index == 0 ? -48.0f : 50.0f) : 0.0f;
		const float Size = (Index < 2 ? 2.20f : 3.0f) + Contract * 0.85f;
		PlaceRing(Index, Target + FVector(0.0f, 0.0f, Height), Normal, Age * (Index % 2 ? 38.0f : -45.0f),
			FVector(Size, Index < 2 ? Size : Size * 0.62f, 1.0f), Open * Fade * (Index < 2 ? 0.66f : 0.36f));
	}
	const float Arrival = FMath::Clamp(Age / BindArrival, 0.0f, 1.0f);
	const FVector Tip = FMath::Lerp(CastOrigin, Target, Arrival);
	PlaceLine(0, Tip - (Target - CastOrigin).GetSafeNormal() * 85.0f, Tip, 12.0f, Age < BindArrival ? 3.2f : 0.0f);
	for (int32 Index = 1; Index < LineMeshes.Num(); ++Index)
	{
		const float A = (Index - 1) / 16.0f;
		const float B = Index / 16.0f;
		const auto Point = [Target, Age, Contract](float T)
		{
			const float Angle = T * 4.0f * PI + Age * 1.8f;
			const float Radius = 66.0f + Contract * 28.0f;
			return Target + FVector(FMath::Cos(Angle) * Radius, FMath::Sin(Angle) * Radius, -65.0f + T * 130.0f);
		};
		PlaceLine(Index, Point(A), Point(B), 8.0f, Open * Fade * 1.75f);
	}
	if (bCommitted && !bReleased && Age - LastPulseAt > 0.24f)
	{
		LastPulseAt = Age;
		Pulse(Target + FVector(FMath::Cos(Age * 8.0f) * 62.0f, FMath::Sin(Age * 8.0f) * 62.0f, 12.0f), FVector::UpVector, 0.32f);
	}
}

void ASparrowSanctuary::UpdateBarrierVisual(float Age)
{
	const FVector Side = FVector::CrossProduct(FVector::UpVector, CastDirection);
	const float Envelope = FMath::SmoothStep(0.0f, GuardEntry + 0.1f, Age) *
		(1.0f - FMath::SmoothStep(GuardEntry + GuardSeconds, GuardEntry + GuardSeconds + 0.3f, Age));
	const float Emphasis = 1.0f + 0.65f * FMath::Clamp((CounterPulseUntil - Age) / 0.22f, 0.0f, 1.0f);
	for (int32 Index = 0; Index < RingMeshes.Num(); ++Index)
	{
		const float Size = (Index == 0 ? 3.45f : 2.70f) * (0.45f + 0.55f * FMath::SmoothStep(0.0f, GuardEntry, Age));
		PlaceRing(Index, BarrierCenter + CastDirection * (Index * 8.0f), CastDirection + Side * ((Index - 1) * 0.20f),
			Age * (Index % 2 ? -32.0f : 32.0f), FVector(Size, Size * 0.72f, 1.0f),
			Envelope * (Index == 0 ? 0.62f : 0.34f) * Emphasis);
	}
	for (int32 Index = 0; Index < LineMeshes.Num(); ++Index)
	{
		const float Angle = Index * PI / 4.0f + Age * 0.32f;
		const FVector Radius = Side * FMath::Cos(Angle) * 115.0f + FVector::UpVector * FMath::Sin(Angle) * 82.0f;
		PlaceLine(Index, BarrierCenter + Radius * 0.84f, BarrierCenter + Radius, 7.0f, Envelope * Emphasis * 1.45f);
	}
}

void ASparrowSanctuary::Pulse(const FVector& Position, const FVector& Direction, float Scale, bool bRelease)
{
	UParticleSystem* Template = GetSanctuarySparks();
	if (!Template) { return; }
	UParticleSystemComponent* Particle = UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), Template,
		Position, Direction.Rotation(), FVector(Scale), false, EPSCPoolMethod::None, false);
	if (!Particle) { return; }
	Particle->ComponentTags.Add(TEXT("SparrowSanctuaryPulse"));
	Particle->bOverrideLODMethod = true;
	Particle->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
	Particle->CustomTimeDilation = bRelease ? 1.8f : 2.1f;
	Particle->SetLODLevel(0);
	Particle->ActivateSystem(true);
	Particle->SetLODLevel(0);
	Pulses.Add({Particle, static_cast<float>(GetWorld()->GetTimeSeconds() - StartedAt) + (bRelease ? 0.45f : 0.30f)});
}

void ASparrowSanctuary::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!Caster.IsValid() || !IsValid(GetOwner()) || (SkillSlot == 9 && !BoundTarget.IsValid())) { Destroy(); return; }
	const float Age = static_cast<float>(GetWorld()->GetTimeSeconds() - StartedAt);
	if (SkillSlot == 9)
	{
		if (!bCommitted && Age >= BindArrival) { ApplyBinding(); if (IsActorBeingDestroyed()) { return; } }
		if (!bReleased && Age >= BindArrival + BindSeconds)
		{
			ReleaseBinding();
			Pulse(BoundTarget->GetActorLocation(), FVector::UpVector, 0.85f, true);
		}
		UpdateBindingVisual(Age);
	}
	else
	{
		BarrierCenter = Caster->GetActorLocation() + CastDirection * 110.0f + FVector(0.0f, 0.0f, 45.0f);
		if (Age >= GuardEntry) { bCommitted = true; }
		UpdateBarrierVisual(Age);
	}
	for (int32 Index = Pulses.Num() - 1; Index >= 0; --Index)
	{
		if (!Pulses[Index].Particle.IsValid() || Age >= Pulses[Index].Until)
		{
			if (Pulses[Index].Particle.IsValid()) { Pulses[Index].Particle->DestroyComponent(); }
			Pulses.RemoveAtSwap(Index);
		}
	}
}

void ASparrowSanctuary::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	ReleaseBinding();
	ActiveGuards.RemoveAll([this](const TWeakObjectPtr<ASparrowSanctuary>& Guard) { return !Guard.IsValid() || Guard.Get() == this; });
	for (const FPulse& Pulse : Pulses)
	{
		if (Pulse.Particle.IsValid()) { Pulse.Particle->DestroyComponent(); }
	}
	Pulses.Reset();
	Super::EndPlay(EndPlayReason);
}
