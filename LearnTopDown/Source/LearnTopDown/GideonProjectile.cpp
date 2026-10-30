#include "GideonProjectile.h"
#include "SparrowSanctuary.h"

#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GideonSkillComponent.h"
#include "Kismet/GameplayStatics.h"
#include "KwangTrainingDummy.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "TimerManager.h"

AGideonProjectile::AGideonProjectile()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false;
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
}

void AGideonProjectile::Launch(EGideonProjectileKind InKind, const FVector& Direction, float Speed, float Range,
	float Damage, UParticleSystem* Trail, UParticleSystem* HitCharacter, UParticleSystem* HitWorld, UParticleSystem* NoHit)
{
	Kind = InKind;
	FlightDirection = Direction.GetSafeNormal();
	FlightSpeed = FMath::Max(Speed, 1.0f);
	RemainingRange = FMath::Max(Range, 0.0f);
	FlightDamage = Damage;
	// Burden은 너무 안 맞는다는 요청(10-18)으로 적 판정만 넓힌다.
	TargetRadius = Kind == EGideonProjectileKind::Burden ? 75.0f : CollisionRadius;
	HitCharacterEffect = HitCharacter;
	HitWorldEffect = HitWorld;
	NoHitEffect = NoHit;
	SetActorRotation(FlightDirection.Rotation());
	if (Trail)
	{
		TrailParticle = UGameplayStatics::SpawnEmitterAttached(Trail, GetRootComponent(), NAME_None,
			FVector::ZeroVector, FRotator::ZeroRotator, EAttachLocation::KeepRelativeOffset, false);
	}
	SetLifeSpan(RemainingRange / FlightSpeed + 0.5f);
	SetActorTickEnabled(!FlightDirection.IsNearlyZero());
}

void AGideonProjectile::HideTrailFor(float Seconds)
{
	if (!TrailParticle || Seconds <= 0.0f)
	{
		return;
	}
	TrailParticle->SetVisibility(false);
	FTimerHandle Handle;
	GetWorldTimerManager().SetTimer(Handle, FTimerDelegate::CreateWeakLambda(this, [this]()
	{
		if (TrailParticle)
		{
			TrailParticle->SetVisibility(true);
		}
	}), Seconds, false);
}

void AGideonProjectile::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	if (bStopped || !IsValid(GetOwner()))
	{
		Destroy();
		return;
	}
	const FVector Start = GetActorLocation();
	const float Distance = FMath::Min(FlightSpeed * FMath::Max(DeltaTime, 0.0f), RemainingRange);
	const FVector End = Start + FlightDirection * Distance;
	FCollisionQueryParams Query(SCENE_QUERY_STAT(GideonProjectile), false, GetOwner());
	Query.AddIgnoredActor(this);
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_Pawn);
	Objects.AddObjectTypesToQuery(ECC_WorldStatic);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	TArray<FHitResult> Hits;
	GetWorld()->SweepMultiByObjectType(Hits, Start, End, FQuat::Identity, Objects,
		FCollisionShape::MakeSphere(CollisionRadius), Query);
	if (TargetRadius > CollisionRadius)
	{
		// 넓은 구로는 적만 더 찾는다. 같은 구간을 훑으므로 Time끼리 앞뒤를 비교할 수 있다.
		FCollisionObjectQueryParams Targets;
		Targets.AddObjectTypesToQuery(ECC_Pawn);
		Targets.AddObjectTypesToQuery(ECC_WorldDynamic);
		TArray<FHitResult> Wide;
		GetWorld()->SweepMultiByObjectType(Wide, Start, End, FQuat::Identity, Targets,
			FCollisionShape::MakeSphere(TargetRadius), Query);
		for (const FHitResult& Hit : Wide)
		{
			if (IsValid(Hit.GetActor()) && (Hit.GetActor()->IsA<APawn>() || Hit.GetActor()->IsA<AKwangTrainingDummy>()))
			{
				Hits.Add(Hit);
			}
		}
	}
	Hits.Sort([](const FHitResult& Left, const FHitResult& Right) { return Left.Time < Right.Time; });
	float GuardTime = 1.0f;
	FVector GuardContact = FVector::ZeroVector;
	TWeakObjectPtr<ASparrowSanctuary> Guard = ASparrowSanctuary::FindInterception(this, Start, End, GuardTime, GuardContact);
	const auto StopAtGuard = [&]()
	{
		if (!Guard.IsValid() || !Guard->TryIntercept(this, GuardContact)) { return false; }
		RemainingRange = FMath::Max(0.0f, RemainingRange - Distance * GuardTime);
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
		if (GuardTime < Hit.Time - KINDA_SMALL_NUMBER && StopAtGuard()) { return; }
		if (Target->IsA<APawn>() || Target->IsA<AKwangTrainingDummy>())
		{
			if (Target->CanBeDamaged() && FlightDamage > 0.0f)
			{
				UGameplayStatics::ApplyPointDamage(Target, FlightDamage, FlightDirection, Hit,
					GetInstigatorController(), this, nullptr);
			}
			Stop(Hit.ImpactPoint, Target, HitCharacterEffect);
			return;
		}
		if (Hit.bBlockingHit)
		{
			Stop(Hit.ImpactPoint, nullptr, HitWorldEffect);
			return;
		}
	}
	if (StopAtGuard()) { return; }
	RemainingRange = FMath::Max(0.0f, RemainingRange - Distance);
	SetActorLocation(End);
	if (RemainingRange <= 0.0f)
	{
		Stop(End, nullptr, NoHitEffect);
	}
}

void AGideonProjectile::Stop(const FVector& Location, AActor* Target, UParticleSystem* Effect)
{
	bStopped = true;
	SetActorTickEnabled(false);
	UE_LOG(LogTemp, Display, TEXT("GIDEON_PROJECTILE kind=%d stop=%s target=%s effect=%s"), static_cast<int32>(Kind),
		*Location.ToCompactString(), *GetNameSafe(Target), *GetNameSafe(Effect));
	if (Effect)
	{
		UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), Effect, Location, FlightDirection.Rotation());
	}
	if (UGideonSkillComponent* Skills = GetOwner() ? GetOwner()->FindComponentByClass<UGideonSkillComponent>() : nullptr)
	{
		Skills->HandleProjectileStopped(Kind, Location, Target);
	}
	Destroy();
}

void AGideonProjectile::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	SetActorTickEnabled(false);
	if (TrailParticle)
	{
		TrailParticle->DeactivateSystem();
		TrailParticle->DestroyComponent();
	}
	Super::EndPlay(EndPlayReason);
}
