#include "CountessExtraTide.h"

#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "CountessSkillComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "KwangTrainingDummy.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"

ACountessExtraTide::ACountessExtraTide()
{
	PrimaryActorTick.bCanEverTick = true;
	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
	SetRootComponent(SceneRoot);
	SetActorEnableCollision(false);
	SetCanBeDamaged(false);
	Tags.Add(TEXT("CountessExtraTide"));
	BodyEffect = TSoftObjectPtr<UParticleSystem>(FSoftObjectPath(
		TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessNightTideBody.P_CountessNightTideBody")));
	BodyWing = TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(
		TEXT("/Game/ParagonCountess/FX/Meshes/Shapes/SM_Countess_WingMesh.SM_Countess_WingMesh")));
	BodyBlade = TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(
		TEXT("/Game/ParagonCountess/FX/Meshes/Shapes/SM_Countess_RollingDark_SwordMesh.SM_Countess_RollingDark_SwordMesh")));
	BodyWingMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
		TEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessNightTideWing.M_CountessNightTideWing")));
	BodyBladeMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
		TEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessNightTideBlade.M_CountessNightTideBlade")));
}

void ACountessExtraTide::Initialize(const FVector& Direction, float InDamage, float InRange,
	UParticleSystem* Effect, UParticleSystem* InImpactEffect)
{
	TravelDirection = Direction.GetSafeNormal2D();
	Damage = InDamage;
	RemainingRange = InRange;
	SegmentEffect = Effect;
	ImpactEffect = InImpactEffect;
	StartedAt = GetWorld()->GetTimeSeconds();
	float OwnerRadius, OwnerHalfHeight;
	if (IsValid(GetOwner()))
	{
		GetOwner()->GetSimpleCollisionCylinder(OwnerRadius, OwnerHalfHeight);
		GroundOffset = -OwnerHalfHeight + 100.0f;
	}
	bTraveling = !TravelDirection.IsNearlyZero() && IsValid(GetOwner());
	SetActorRotation(TravelDirection.Rotation());
	CreateBody();
	FRotator BodyRotation = TravelDirection.Rotation();
	BodyRotation.Pitch = 90;
	if (UParticleSystemComponent* Body = UCountessSkillComponent::SpawnEffect(GetWorld(), BodyEffect.LoadSynchronous(),
		GetActorLocation() + FVector(0, 0, GroundOffset), BodyRotation, .32f, GetOwner(), InRange / 1000.0f + .7f))
	{
		Body->AttachToComponent(SceneRoot, FAttachmentTransformRules::KeepWorldTransform);
		Body->SetAbsolute(false, false, false);
		Body->SetRelativeLocation(FVector(0, 0, GroundOffset));
		Body->SetRelativeRotation(FRotator(90, 0, 0));
		Body->SetRelativeScale3D(FVector(.32f));
		Body->ComponentTags.Add(TEXT("CountessExtraFX"));
		BodyParticle = Body;
		Effects.Add(Body);
	}
	SpawnSegment(GetActorLocation());
	UpdatePresentation();
	SetLifeSpan(InRange / 1000.0f + 1.0f);
}

int32 ACountessExtraTide::AddForm(UStaticMesh* Mesh, UMaterialInterface* Material)
{
	if (!Mesh || !Material) { return INDEX_NONE; }
	UStaticMeshComponent* Form = NewObject<UStaticMeshComponent>(this);
	Form->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Form->SetGenerateOverlapEvents(false);
	Form->SetCanEverAffectNavigation(false);
	Form->SetStaticMesh(Mesh);
	Form->SetupAttachment(SceneRoot);
	Form->SetCastShadow(false);
	Form->SetReceivesDecals(false);
	Form->ComponentTags.Add(TEXT("CountessExtraFX"));
	Form->RegisterComponent();
	UMaterialInstanceDynamic* MaterialInstance = UMaterialInstanceDynamic::Create(Material, this);
	MaterialInstance->SetVectorParameterValue(TEXT("TideTint"), FLinearColor::White);
	// 원본 파티클은 WipeOn/Off를 수명으로 공급한다. 메시 기본값(0,1)은 전체 투명이다.
	MaterialInstance->SetVectorParameterValue(TEXT("TidePhase"),
		Mesh == BodyWing.Get() ? FLinearColor(1, 0, 1, 1) : FLinearColor(.5f, 1, 1, 1));
	if (Mesh == BodyBlade.Get())
	{
		MaterialInstance->SetVectorParameterValue(TEXT("ReallyHotEdgeColor"), FLinearColor(4, .015f, .04f, 0));
		MaterialInstance->SetVectorParameterValue(TEXT("Color2"), FLinearColor(.5f, .005f, .02f, 0));
		MaterialInstance->SetVectorParameterValue(TEXT("Color3"), FLinearColor(.35f, .0005f, .01f, 0));
	}
	for (int32 Slot = 0; Slot < FMath::Max(1, Form->GetNumMaterials()); ++Slot) { Form->SetMaterial(Slot, MaterialInstance); }
	FormMaterials.Add(MaterialInstance);
	return Forms.Add(Form);
}

void ACountessExtraTide::CreateBody()
{
	UStaticMesh* Wing = BodyWing.LoadSynchronous();
	UStaticMesh* Blade = BodyBlade.LoadSynchronous();
	UMaterialInterface* WingMaterial = BodyWingMaterial.LoadSynchronous();
	UMaterialInterface* BladeMaterial = BodyBladeMaterial.LoadSynchronous();
	if (!Wing || !Blade || !WingMaterial || !BladeMaterial)
	{
		UE_LOG(LogTemp, Warning, TEXT("COUNTESS_EXTRA_TIDE missing dedicated body assets"));
		return;
	}
	AddForm(Wing, WingMaterial);
	AddForm(Wing, WingMaterial);
	AddForm(Blade, BladeMaterial);
}

void ACountessExtraTide::PlaceForm(int32 Index, const FVector& Center, const FRotator& Rotation,
	const FVector& Scale, float Opacity)
{
	if (!Forms.IsValidIndex(Index)) { return; }
	UStaticMeshComponent* Form = Forms[Index];
	const FQuat Orientation = Rotation.Quaternion();
	// 원본 FX 메시의 편심 피벗을 보정해, 모양이 바뀌어도 전진 중심과 타격 위치가 어긋나지 않는다.
	const FVector Pivot = Form->GetStaticMesh()->GetBoundingBox().GetCenter() * Scale;
	Form->SetWorldTransform(FTransform(Orientation, Center - Orientation.RotateVector(Pivot), Scale));
	FormMaterials[Index]->SetScalarParameterValue(TEXT("TideOpacity"), Opacity);
	Form->SetVisibility(Opacity > .001f);
}

void ACountessExtraTide::UpdatePresentation()
{
	if (Forms.Num() < 3) { return; }
	const double Now = GetWorld()->GetTimeSeconds();
	const float Age = Now - StartedAt;
	const float Opening = FMath::SmoothStep(0.0f, .09f, Age);
	const float Fade = StoppedAt < 0.0 ? 1.0f : 1.0f - FMath::SmoothStep(0.0f, .38f, static_cast<float>(Now - StoppedAt));
	const float Unfold = Opening * (1.0f + .045f * FMath::Sin(Age * 19.0f));
	const FVector Center = GetActorLocation() + FVector(0, 0, GroundOffset);
	const FVector Side(-TravelDirection.Y, TravelDirection.X, 0);
	FRotator Facing = TravelDirection.Rotation();
	Facing.Roll = -8.0f + 7.0f * FMath::Sin(Age * 8.0f);
	PlaceForm(0, Center, Facing, FVector(.85f, 1.30f * Unfold, 1.12f * Unfold), .88f * Fade);
	FormMaterials[0]->SetVectorParameterValue(TEXT("TidePhase"), FLinearColor(Opening, 1.0f - Fade, 1, 1));
	Facing.Roll = 21.0f - 9.0f * FMath::Sin(Age * 6.0f);
	Facing.Yaw += 16.0f;
	PlaceForm(1, Center - TravelDirection * 94.0f + Side * 18.0f - FVector(0, 0, 15), Facing,
		FVector(.70f, .92f * Unfold, .78f * Unfold), .58f * Fade);
	FormMaterials[1]->SetVectorParameterValue(TEXT("TidePhase"), FLinearColor(Opening, 1.0f - Fade, 1, 1));
	Facing = TravelDirection.Rotation();
	Facing.Roll = 64.0f;
	PlaceForm(2, Center + TravelDirection * 16.0f, Facing,
		FVector(.60f * Unfold, .70f * Unfold, .74f * Unfold), .55f * Fade);
	for (const FInkBurst& Burst : Bursts)
	{
		const float Elapsed = Now - Burst.StartedAt;
		const float Spread = FMath::SmoothStep(0.0f, .13f, Elapsed);
		const float BurstFade = (1.0f - FMath::SmoothStep(.09f, .42f, Elapsed)) * FMath::SmoothStep(0.0f, .025f, Elapsed);
		for (int32 SideIndex = 0; SideIndex < 2; ++SideIndex)
		{
			const float Sign = SideIndex == 0 ? -1.0f : 1.0f;
			FRotator BurstRotation = TravelDirection.Rotation();
			BurstRotation.Yaw += Sign * (26.0f + Spread * 18.0f);
			BurstRotation.Roll = Sign * 30.0f;
			PlaceForm(Burst.FirstForm + SideIndex, Burst.Location + Side * Sign * Spread * 38.0f,
				BurstRotation, FVector(.55f, .75f + Spread * .18f, .76f + Spread * .24f), .78f * BurstFade);
			FormMaterials[Burst.FirstForm + SideIndex]->SetVectorParameterValue(TEXT("TidePhase"),
				FLinearColor(1, FMath::SmoothStep(.13f, .41f, Elapsed), 1, 1));
		}
	}
}

void ACountessExtraTide::SpawnImpact(const FVector& Location)
{
	if (Bursts.Num() >= 3 || Forms.Num() < 3) { return; }
	const int32 First = AddForm(Forms[0]->GetStaticMesh(), FormMaterials[0]->Parent);
	if (First == INDEX_NONE) { return; }
	AddForm(Forms[0]->GetStaticMesh(), FormMaterials[0]->Parent);
	Bursts.Add({Location, GetWorld()->GetTimeSeconds(), First});
}

void ACountessExtraTide::SpawnSegment(const FVector& Location)
{
	FRotator Rotation = TravelDirection.Rotation();
	Rotation.Yaw -= 90.0f;
	Effects.RemoveAll([](const TWeakObjectPtr<UParticleSystemComponent>& Item) { return !Item.IsValid(); });
	if (UParticleSystemComponent* Particle = UCountessSkillComponent::SpawnEffect(GetWorld(), SegmentEffect,
		Location - TravelDirection * 75.0f + FVector(0, 0, GroundOffset - 35.0f), Rotation, .40f, GetOwner(), .5f))
	{
		Particle->SetFloatParameter(TEXT("width"), 75.0f);
		Particle->ComponentTags.Add(TEXT("CountessExtraFX"));
		Effects.Add(Particle);
	}
}

void ACountessExtraTide::StopTravel()
{
	bTraveling = false;
	if (BodyParticle.IsValid()) { BodyParticle->DeactivateSystem(); }
	StoppedAt = GetWorld()->GetTimeSeconds();
	SetLifeSpan(0.7f);
}

void ACountessExtraTide::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!IsValid(GetOwner())) { Destroy(); return; }
	if (!bTraveling) { UpdatePresentation(); return; }
	const FVector Start = GetActorLocation();
	const float Distance = FMath::Min(1000.0f * DeltaSeconds, RemainingRange);
	FVector End = Start + TravelDirection * Distance;
	FCollisionQueryParams Query(SCENE_QUERY_STAT(CountessExtraTide), false, GetOwner());
	FCollisionObjectQueryParams Obstacles;
	Obstacles.AddObjectTypesToQuery(ECC_WorldStatic);
	Obstacles.AddObjectTypesToQuery(ECC_WorldDynamic);
	TArray<FHitResult> ObstacleHits;
	GetWorld()->SweepMultiByObjectType(ObstacleHits, Start, End, FQuat::Identity,
		Obstacles, FCollisionShape::MakeSphere(60.0f), Query);
	bool bWall = false;
	for (const FHitResult& Hit : ObstacleHits)
	{
		AActor* Actor = Hit.GetActor();
		if (Hit.bBlockingHit && Actor && !Actor->IsA<APawn>() && !Actor->IsA<AKwangTrainingDummy>())
		{
			End = Hit.Location;
			bWall = true;
			break;
		}
	}
	FCollisionObjectQueryParams Targets;
	Targets.AddObjectTypesToQuery(ECC_Pawn);
	Targets.AddObjectTypesToQuery(ECC_WorldDynamic);
	TArray<FHitResult> Hits;
	GetWorld()->SweepMultiByObjectType(Hits, Start, End, FQuat::Identity,
		Targets, FCollisionShape::MakeSphere(100.0f), Query);
	for (const FHitResult& Hit : Hits)
	{
		AActor* Target = Hit.GetActor();
		if (!UCountessSkillComponent::IsValidSkillTarget(Target, GetOwner()) || DamagedActors.Contains(Target) ||
			FMath::Abs(Target->GetActorLocation().Z - Start.Z) > 150.0f) { continue; }
		FCollisionQueryParams SightQuery = Query;
		SightQuery.AddIgnoredActor(Target);
		FHitResult Obstacle;
		if (GetWorld()->LineTraceSingleByChannel(Obstacle, Start, Target->GetActorLocation(), ECC_Visibility, SightQuery)) { continue; }
		DamagedActors.Add(Target);
		UGameplayStatics::ApplyPointDamage(Target, Damage, TravelDirection, Hit, GetInstigatorController(), this, nullptr);
		if (UParticleSystemComponent* Impact = UCountessSkillComponent::SpawnEffect(GetWorld(), ImpactEffect,
			Target->GetActorLocation(), TravelDirection.Rotation(), 0.9f, Target, 0.7f))
		{
			Impact->ComponentTags.Add(TEXT("CountessExtraFX"));
			Effects.Add(Impact);
		}
		SpawnImpact(Target->GetActorLocation());
		UE_LOG(LogTemp, Display, TEXT("COUNTESS_EXTRA_TIDE hit target=%s damage=%.1f"), *Target->GetName(), Damage);
	}
	const float Traveled = FVector::Dist2D(Start, End);
	float SegmentDistance = 190.0f - DistanceSinceSegment;
	for (; SegmentDistance <= Traveled; SegmentDistance += 190.0f)
	{
		SpawnSegment(FMath::Lerp(Start, End, SegmentDistance / FMath::Max(Traveled, 1.0f)));
	}
	DistanceSinceSegment = FMath::Fmod(DistanceSinceSegment + Traveled, 190.0f);
	SetActorLocation(End);
	RemainingRange -= Traveled;
	UpdatePresentation();
	if (bWall || RemainingRange <= 0.1f)
	{
		UE_LOG(LogTemp, Display, TEXT("COUNTESS_EXTRA_TIDE stop wall=%d hits=%d remaining=%.1f"), bWall, DamagedActors.Num(), RemainingRange);
		StopTravel();
	}
}

void ACountessExtraTide::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	for (const TWeakObjectPtr<UParticleSystemComponent>& Effect : Effects)
	{
		if (Effect.IsValid()) { Effect->DestroyComponent(); }
	}
	Super::EndPlay(EndPlayReason);
}
