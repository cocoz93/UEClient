#include "CountessDarkTide.h"

#include "Components/SceneComponent.h"
#include "Components/AudioComponent.h"
#include "CountessSkillComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "KwangTrainingDummy.h"
#include "Particles/ParticleSystemComponent.h"
#include "Sound/SoundBase.h"
#include "UObject/ConstructorHelpers.h"

ACountessDarkTide::ACountessDarkTide()
{
	PrimaryActorTick.bCanEverTick = true;
	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
	SetRootComponent(SceneRoot);
	Particle = CreateDefaultSubobject<UParticleSystemComponent>(TEXT("DarkTideEffect"));
	Particle->SetupAttachment(SceneRoot);
	Particle->bAutoActivate = false;
	Particle->SetRelativeLocation(FVector(0.0f, 0.0f, -70.0f));
	Particle->ComponentTags.Add(TEXT("CountessSkillFX"));
	ConstructorHelpers::FObjectFinder<USoundBase> Sound(TEXT("/Game/TopDown/Characters/Countess/Audio/SW_CountessSkill_Impact.SW_CountessSkill_Impact"));
	ImpactSound = Sound.Object;
}

void ACountessDarkTide::Initialize(const FVector& Direction, float InDamage, float InRange,
	UParticleSystem* Effect, UParticleSystem* InImpactEffect)
{
	TravelDirection = Direction.GetSafeNormal2D();
	Damage = InDamage;
	RemainingRange = InRange;
	ImpactEffect = InImpactEffect;
	SegmentEffect = Effect;
	bDetailedFX = UCountessSkillComponent::UsesDetailedPresentation();
	SetActorRotation(TravelDirection.Rotation());
	Particle->SetTemplate(Effect);
	Particle->bOverrideLODMethod = true;
	Particle->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
	Particle->SetLODLevel(0);
	float OwnerRadius, OwnerHalfHeight;
	GetOwner()->GetSimpleCollisionCylinder(OwnerRadius, OwnerHalfHeight);
	GroundOffset = -OwnerHalfHeight + 2.0f;
	Particle->SetRelativeLocation(FVector(0, 0, GroundOffset));
	if (bDetailedFX)
	{
		SpawnVisualSegment(GetActorLocation());
	}
	else
	{
		Particle->ActivateSystem();
		Particle->SetLODLevel(0);
	}
	SetLifeSpan(InRange / Speed + 1.0f);
}

void ACountessDarkTide::SpawnVisualSegment(const FVector& Location)
{
	FRotator Rotation = TravelDirection.Rotation();
	// 원본 SegmentFX는 +Y 방향으로 입자를 방출한다. 판정의 +X 진행 방향과 정렬한다.
	Rotation.Yaw -= 90.0f;
	// 원본 구름은 Z축으로도 width만큼 퍼진다. 중심을 바닥에서 올려 하반부가 지면에 가려지지 않게 한다.
	UParticleSystemComponent* Segment = UCountessSkillComponent::SpawnEffect(GetWorld(), SegmentEffect,
		Location + FVector(0, 0, GroundOffset + Radius), Rotation, 1.0f, GetOwner(), 2.5f);
	if (Segment)
	{
		Segment->SetFloatParameter(TEXT("width"), Radius);
	}
}

void ACountessDarkTide::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	if (!IsValid(GetOwner()))
	{
		Destroy();
		return;
	}
	const FVector Start = GetActorLocation();
	const float Distance = FMath::Min(Speed * DeltaTime, RemainingRange);
	FVector End = Start + TravelDirection * Distance;
	FCollisionQueryParams Query(SCENE_QUERY_STAT(CountessDarkTide), false, GetOwner());
	FCollisionObjectQueryParams Obstacles;
	Obstacles.AddObjectTypesToQuery(ECC_WorldStatic);
	Obstacles.AddObjectTypesToQuery(ECC_WorldDynamic);
	TArray<FHitResult> ObstacleHits;
	GetWorld()->SweepMultiByObjectType(ObstacleHits, Start, End, FQuat::Identity,
		Obstacles, FCollisionShape::MakeSphere(60.0f), Query);
	bool bHitWall = false;
	for (const FHitResult& Hit : ObstacleHits)
	{
		const AActor* Actor = Hit.GetActor();
		// 적은 통과하되 정적 벽과 움직이는 장애물은 모두 앞에서 파동을 끝낸다.
		if (Hit.bBlockingHit && Actor && !Actor->IsA<APawn>() && !Actor->IsA<AKwangTrainingDummy>())
		{
			End = Hit.Location;
			bHitWall = true;
			break;
		}
	}
	FCollisionObjectQueryParams Targets;
	Targets.AddObjectTypesToQuery(ECC_Pawn);
	Targets.AddObjectTypesToQuery(ECC_WorldDynamic);
	TArray<FHitResult> Hits;
	GetWorld()->SweepMultiByObjectType(Hits, Start, End, FQuat::Identity,
		Targets, FCollisionShape::MakeSphere(Radius), Query);
	for (const FHitResult& Hit : Hits)
	{
		AActor* Target = Hit.GetActor();
		if (!UCountessSkillComponent::IsValidSkillTarget(Target, GetOwner()) || DamagedActors.Contains(Target) ||
			FMath::Abs(Target->GetActorLocation().Z - Start.Z) > 150.0f)
		{
			continue;
		}
		// 전체 스윕 끝점의 벽 앞에도 두꺼운 적 캡슐이 겹칠 수 있으므로 대상 중심의 시야를 재확인한다.
		FCollisionQueryParams SightQuery = Query;
		SightQuery.AddIgnoredActor(Target);
		FHitResult Obstacle;
		if (GetWorld()->LineTraceSingleByChannel(Obstacle, Start, Target->GetActorLocation(), ECC_Visibility, SightQuery))
		{
			continue;
		}
		DamagedActors.Add(Target);
		UGameplayStatics::ApplyPointDamage(Target, Damage, TravelDirection, Hit, GetInstigatorController(), this, nullptr);
		UCountessSkillComponent::SpawnEffect(GetWorld(), ImpactEffect, Target->GetActorLocation(), TravelDirection.Rotation());
		if (UCountessSkillComponent::UsesSkillAudio() && bDetailedFX && ImpactSound)
		{
			if (UAudioComponent* Audio = UGameplayStatics::SpawnSoundAtLocation(GetWorld(), ImpactSound, Target->GetActorLocation(), FRotator::ZeroRotator, 0.45f))
			{
				Audio->ComponentTags.Add(TEXT("CountessSkillSFX"));
			}
		}
	}
	if (bDetailedFX)
	{
		// 각 에미터의 방출은 0.2초로 짧다. 판정은 하나로 유지하며 지나간 경로에 원본 구름을 이어 놓는다.
		constexpr float SegmentSpacing = 160.0f;
		const float VisualDistance = FVector::Dist2D(Start, End);
		float NextSegment = SegmentSpacing - DistanceSinceSegment;
		for (; NextSegment <= VisualDistance; NextSegment += SegmentSpacing)
		{
			SpawnVisualSegment(FMath::Lerp(Start, End, NextSegment / FMath::Max(VisualDistance, 1.0f)));
		}
		DistanceSinceSegment = FMath::Fmod(DistanceSinceSegment + VisualDistance, SegmentSpacing);
	}
	SetActorLocation(End);
	RemainingRange -= Distance;
	if (bHitWall || RemainingRange <= 0.0f)
	{
		if (bDetailedFX && bHitWall)
		{
			UCountessSkillComponent::SpawnEffect(GetWorld(), ImpactEffect, End + FVector(0, 0, GroundOffset), TravelDirection.Rotation());
		}
		Particle->DeactivateSystem();
		Destroy();
	}
}
