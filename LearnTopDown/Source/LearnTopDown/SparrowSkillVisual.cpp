#include "SparrowSkillVisual.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/CapsuleComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Character.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Misc/PackageName.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "SparrowArrow.h"
#include "UObject/ConstructorHelpers.h"

ASparrowSkillVisual::ASparrowSkillVisual()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false;
	SetCanBeDamaged(false);
	SetActorEnableCollision(false);
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Plane(TEXT("/Engine/BasicShapes/Plane.Plane"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> ArrowAsset(
		TEXT("/Game/ParagonSparrow/FX/Meshes/Heroes/Sparrow/Abilities/SM_Sparrow_Arrow.SM_Sparrow_Arrow"));
	const auto MakeLayer = [this](const TCHAR* Name, UStaticMesh* Mesh)
	{
		UInstancedStaticMeshComponent* Layer = CreateDefaultSubobject<UInstancedStaticMeshComponent>(Name);
		Layer->SetupAttachment(GetRootComponent());
		Layer->SetMobility(EComponentMobility::Movable);
		Layer->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Layer->SetGenerateOverlapEvents(false);
		Layer->SetCanEverAffectNavigation(false);
		Layer->SetCastShadow(false);
		Layer->SetReceivesDecals(false);
		Layer->SetStaticMesh(Mesh);
		return Layer;
	};
	Core = MakeLayer(TEXT("GoldCore"), Plane.Object);
	Glow = MakeLayer(TEXT("AmberGlow"), Plane.Object);
	Sparks = MakeLayer(TEXT("GoldSparks"), Plane.Object);
	PlaneMesh = Plane.Object;
	ArrowMeshes = MakeLayer(TEXT("AuthoredArrows"), ArrowAsset.Object);
	StripSource = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
		TEXT("/Game/TopDown/Characters/Gideon/FX/M_NoxGlowStrip.M_NoxGlowStrip")));
	SparkSource = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
		TEXT("/Game/TopDown/Characters/Gideon/FX/M_NoxSpark.M_NoxSpark")));
	RingSource = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowShotAirAccent.M_SparrowShotAirAccent")));
	WindSource = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowShotWindAxis.M_SparrowShotWindAxis")));
	ExtraGustSource = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowExtraGust.M_SparrowExtraGust")));
	Tags.Append({TEXT("SparrowSkillFXProxy"), TEXT("SparrowExtraPolish")});
}

void ASparrowSkillVisual::Initialize(ESparrowVisualKind InKind, float Lifetime, float InRadius, float InDelay)
{
	Kind = InKind;
	Radius = InRadius;
	Delay = InDelay;
	Anchor = GetActorLocation();
	WakeEnd = Anchor;
	Forward = GetActorForwardVector();
	UMaterialInterface* Strip = StripSource.LoadSynchronous();
	UMaterialInterface* Dot = SparkSource.LoadSynchronous();
	UMaterialInterface* Air = RingSource.LoadSynchronous();
	bUsesExtraGust = Kind != ESparrowVisualKind::Ambush && Kind != ESparrowVisualKind::Skyfall;
	UMaterialInterface* Breeze = bUsesExtraGust ? ExtraGustSource.LoadSynchronous() : WindSource.LoadSynchronous();
	if (!Breeze && bUsesExtraGust)
	{
		UE_LOG(LogTemp, Warning, TEXT("SPARROW_EXTRA_GUST missing owned AS material; using the preserved wind material"));
		Breeze = WindSource.LoadSynchronous();
		bUsesExtraGust = false;
	}
	if (!Strip || !Dot || !Air || !Breeze || !IsValid(GetOwner())) { Destroy(); return; }
	CoreMaterial = Core->CreateDynamicMaterialInstance(0, Strip);
	GlowMaterial = Glow->CreateDynamicMaterialInstance(0, Strip);
	SparkMaterial = Sparks->CreateDynamicMaterialInstance(0, Dot);
	RingMaterial = UMaterialInstanceDynamic::Create(Air, this);
	WindMaterial = UMaterialInstanceDynamic::Create(Breeze, this);
	ArrowMaterial = ArrowMeshes->CreateDynamicMaterialInstance(0, Strip);
	if (!CoreMaterial || !GlowMaterial || !SparkMaterial || !RingMaterial || !WindMaterial || !ArrowMaterial) { Destroy(); return; }
	// M_NoxGlowStrip/M_NoxSpark의 실제 공개 파라미터만 사용한다. 원본 재질은 수정하지 않는다.
	for (UMaterialInstanceDynamic* Material : {CoreMaterial.Get(), GlowMaterial.Get()})
	{
		Material->SetVectorParameterValue(TEXT("CoreColor"), FLinearColor(1.0f, 0.72f, 0.26f));
		Material->SetVectorParameterValue(TEXT("GlowColor"), FLinearColor(1.0f, 0.42f, 0.08f));
		Material->SetScalarParameterValue(TEXT("CoreSharpness"), 14.0f);
		Material->SetScalarParameterValue(TEXT("GlowSoftness"), 1.7f);
	}
	GlowMaterial->SetScalarParameterValue(TEXT("CoreIntensity"), 0.0f);
	SparkMaterial->SetVectorParameterValue(TEXT("Color"), FLinearColor(1.0f, 0.57f, 0.17f));
	SparkMaterial->SetScalarParameterValue(TEXT("Softness"), 2.0f);
	// 실물 화살의 원본 기본 재질은 WorldGrid이므로 신규 표현에서만 금색 ISM 재질을 명시한다.
	ArrowMaterial->SetVectorParameterValue(TEXT("CoreColor"), FLinearColor(1.0f, 0.72f, 0.26f));
	ArrowMaterial->SetVectorParameterValue(TEXT("GlowColor"), FLinearColor(1.0f, 0.42f, 0.08f));
	ArrowMaterial->SetScalarParameterValue(TEXT("CoreSharpness"), 0.35f);
	ArrowMaterial->SetScalarParameterValue(TEXT("GlowSoftness"), 0.5f);
	if (InKind == ESparrowVisualKind::RicochetHit || InKind == ESparrowVisualKind::RetreatHit) { Trigger(); }
	bInitialized = true;
	SetLifeSpan(FMath::Max(Lifetime, 0.05f));
	SetActorTickEnabled(true);
	Draw();
}

void ASparrowSkillVisual::Trigger()
{
	if (bTriggered) { return; }
	if (Kind == ESparrowVisualKind::RetreatFocus || Kind == ESparrowVisualKind::RicochetFocus)
	{
		// 발사 후 압력 잔광은 발사 자리에 남는다. 후퇴하는 활을 다시 따라가지 않는다.
		const ACharacter* Character = Cast<ACharacter>(GetOwner());
		if (Character && Character->GetMesh()) { Anchor = Character->GetMesh()->GetSocketLocation(TEXT("BowEmitterSocket")); }
	}
	bTriggered = true;
	TriggerAge = Age;
	SetLifeSpan(Kind == ESparrowVisualKind::Ambush ? 0.42f : 0.52f);
}

void ASparrowSkillVisual::SetArrowPresentation(bool bChain, int32 InHitOrdinal)
{
	bChainArrow = bChain;
	HitOrdinal = FMath::Clamp(InHitOrdinal, 0, 3);
	if (bInitialized)
	{
		if (Kind == ESparrowVisualKind::RicochetHit && HitOrdinal == 3) { SetLifeSpan(0.48f); }
		Draw();
	}
}

void ASparrowSkillVisual::FadeOut(float Seconds)
{
	if (FadeAge >= 0.0f) { return; }
	FadeAge = Age;
	FadeSeconds = FMath::Max(Seconds, 0.01f);
	SetLifeSpan(FadeSeconds);
}

void ASparrowSkillVisual::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!IsValid(GetOwner())) { Destroy(); return; }
	Age += FMath::Max(DeltaSeconds, 0.0f);
	UpdateAuthoredEffects();
	if (bInitialized) { Draw(); }
}

UParticleSystemComponent* ASparrowSkillVisual::SpawnAuthoredEffect(const TCHAR* Path, const FVector& Location,
	const FRotator& Rotation, float Scale, float ActiveSeconds, USceneComponent* Parent, FName Socket)
{
	FString ObjectPath(Path);
	if (!ObjectPath.Contains(TEXT("."))) { ObjectPath += TEXT(".") + FPackageName::GetShortName(ObjectPath); }
	UParticleSystem* Source = LoadObject<UParticleSystem>(nullptr, *ObjectPath);
	if (!Source || !GetWorld() || !IsValid(GetOwner())) { return nullptr; }
	UParticleSystemComponent* Effect = NewObject<UParticleSystemComponent>(this);
	Effect->bAutoActivate = false;
	Effect->bAutoDestroy = false;
	Effect->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Effect->SetCanEverAffectNavigation(false);
	Effect->SetTemplate(Source);
	Effect->ComponentTags.Append({TEXT("SparrowSkillFX"), TEXT("SparrowExtraAuthoredFX")});
	Effect->bOverrideLODMethod = true;
	Effect->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
	AddInstanceComponent(Effect);
	Effect->RegisterComponent();
	AActor* BoneSource = Cast<ACharacter>(GetOwner()) ? GetOwner() : GetOwner()->GetOwner();
	Effect->SetActorParameter(TEXT("BoneSocketActor"), BoneSource);
	if (Parent)
	{
		Effect->AttachToComponent(Parent, FAttachmentTransformRules::KeepRelativeTransform, Socket);
		// 월드 절대 좌표를 해제하고 실제 부모/소켓의 상대 변환을 명시한다.
		Effect->SetAbsolute(false, false, false);
		Effect->SetRelativeLocationAndRotation(Location, Rotation);
		Effect->SetRelativeScale3D(FVector(Scale));
	}
	else
	{
		Effect->SetWorldLocationAndRotation(Location, Rotation);
		Effect->SetWorldScale3D(FVector(Scale));
	}
	Effect->SetLODLevel(0);
	Effect->ActivateSystem(true);
	Effect->SetLODLevel(0);
	FAuthoredEffect Layer;
	Layer.Component = Effect;
	Layer.StopAt = Age + FMath::Max(ActiveSeconds, 0.01f);
	AuthoredEffects.Add(MoveTemp(Layer));
	return Effect;
}

void ASparrowSkillVisual::UpdateAuthoredEffects()
{
	for (FAuthoredEffect& Layer : AuthoredEffects)
	{
		if (!Layer.bStopped && Age >= Layer.StopAt && Layer.Component.IsValid())
		{
			Layer.Component->DeactivateSystem();
			Layer.bStopped = true;
		}
	}
}

void ASparrowSkillVisual::StopAuthoredEffects()
{
	for (FAuthoredEffect& Layer : AuthoredEffects)
	{
		if (Layer.Component.IsValid()) { Layer.Component->DestroyComponent(); }
	}
	AuthoredEffects.Reset();
}

void ASparrowSkillVisual::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	StopAuthoredEffects();
	Super::EndPlay(EndPlayReason);
}

void ASparrowSkillVisual::Line(const FVector& From, const FVector& To, float Width)
{
	const FVector Segment = To - From;
	const float Length = Segment.Size();
	if (Length < 0.5f) { return; }
	const FRotator Facing = FRotationMatrix::MakeFromXZ(Segment / Length, CameraNormal).Rotator();
	const FVector Middle = (From + To) * 0.5f;
	CoreTransforms.Add(FTransform(Facing, Middle, FVector(Length / 100.0f, Width / 100.0f, 1.0f)));
	GlowTransforms.Add(FTransform(Facing, Middle, FVector(Length / 100.0f, Width * 4.0f / 100.0f, 1.0f)));
}

void ASparrowSkillVisual::Spark(const FVector& Where, float Size)
{
	SparkTransforms.Add(FTransform(FRotationMatrix::MakeFromZ(CameraNormal).Rotator(), Where, FVector(Size / 100.0f)));
}

void ASparrowSkillVisual::Ring(const FVector& Center, float InRadius, const FRotator& Rotation)
{
	const float Scale = InRadius / 36.0f;
	RingTransforms.Add(FTransform(Rotation, Center, FVector(Scale, Scale, 1.0f)));
}

void ASparrowSkillVisual::Wind(const FVector& From, const FVector& To, float Width)
{
	const FVector Segment = To - From;
	const float Length = Segment.Size();
	if (Length < 0.5f) { return; }
	WindTransforms.Add(FTransform(FRotationMatrix::MakeFromXZ(Segment / Length, CameraNormal).Rotator(),
		(From + To) * 0.5f, FVector(Length / 100.0f, Width / 100.0f, 1.0f)));
}

void ASparrowSkillVisual::Gust(const FVector& From, const FVector& To, float Width, float BendDirection)
{
	const int32 Before = WindTransforms.Num();
	Wind(From, To, Width);
	if (WindTransforms.Num() > Before && BendDirection < 0.0f)
	{
		FTransform& Transform = WindTransforms.Last();
		FVector Scale = Transform.GetScale3D();
		Scale.Y = -Scale.Y;
		Transform.SetScale3D(Scale);
	}
}

void ASparrowSkillVisual::Arrow(const FVector& Center, const FVector& Direction, float Length, float Width)
{
	const FVector Heading = Direction.GetSafeNormal();
	const FVector Side = FVector::CrossProduct(Heading, CameraNormal).GetSafeNormal();
	const FVector Tip = Center + Heading * (Length * 0.5f);
	const FVector Tail = Center - Heading * (Length * 0.5f);
	Line(Tail, Tip, Width);
	Line(Tip, Tip - Heading * Length * 0.25f + Side * Length * 0.14f, Width);
	Line(Tip, Tip - Heading * Length * 0.25f - Side * Length * 0.14f, Width);
	Line(Tail + Heading * Length * 0.16f, Tail + Side * Length * 0.10f, Width * 0.7f);
	Line(Tail + Heading * Length * 0.16f, Tail - Side * Length * 0.10f, Width * 0.7f);
	ArrowTransforms.Add(FTransform(FRotationMatrix::MakeFromZ(-Heading).Rotator(), Center, FVector(Length / 110.0f)));
}

void ASparrowSkillVisual::Arc(const FVector& Center, const FVector& AxisA, const FVector& AxisB, float InRadius,
	float StartAngle, float SweepAngle, int32 Segments, float Width)
{
	FVector Previous;
	for (int32 Index = 0; Index <= Segments; ++Index)
	{
		const float Angle = FMath::DegreesToRadians(StartAngle + SweepAngle * Index / Segments);
		const FVector Point = Center + (AxisA * FMath::Cos(Angle) + AxisB * FMath::Sin(Angle)) * InRadius;
		if (Index > 0) { Line(Previous, Point, Width); }
		Previous = Point;
	}
}

void ASparrowSkillVisual::UpdateInstances(UInstancedStaticMeshComponent* Mesh, const TArray<FTransform>& Transforms)
{
	if (Mesh->GetInstanceCount() == Transforms.Num())
	{
		if (!Transforms.IsEmpty()) { Mesh->BatchUpdateInstancesTransforms(0, Transforms, true, true, true); }
	}
	else
	{
		Mesh->ClearInstances();
		if (!Transforms.IsEmpty()) { Mesh->AddInstances(Transforms, false, true); }
	}
}

void ASparrowSkillVisual::UpdateMeshPool(TArray<TObjectPtr<UStaticMeshComponent>>& Pool,
	const TArray<FTransform>& Transforms, UMaterialInterface* Material)
{
	while (Pool.Num() < Transforms.Num())
	{
		UStaticMeshComponent* Mesh = NewObject<UStaticMeshComponent>(this);
		Mesh->SetupAttachment(GetRootComponent());
		Mesh->SetMobility(EComponentMobility::Movable);
		Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Mesh->SetGenerateOverlapEvents(false);
		Mesh->SetCanEverAffectNavigation(false);
		Mesh->SetCastShadow(false);
		Mesh->SetReceivesDecals(false);
		Mesh->SetStaticMesh(PlaneMesh);
		Mesh->SetMaterial(0, Material);
		AddInstanceComponent(Mesh);
		Mesh->RegisterComponent();
		Pool.Add(Mesh);
	}
	for (int32 Index = 0; Index < Pool.Num(); ++Index)
	{
		const bool bVisible = Transforms.IsValidIndex(Index);
		Pool[Index]->SetVisibility(bVisible);
		if (bVisible) { Pool[Index]->SetWorldTransform(Transforms[Index]); }
	}
}

void ASparrowSkillVisual::Draw()
{
	CoreTransforms.Reset(); GlowTransforms.Reset(); SparkTransforms.Reset();
	RingTransforms.Reset(); WindTransforms.Reset(); ArrowTransforms.Reset();
	FRotator View(-50.0f, 45.0f, 0.0f);
	const ACharacter* Character = Cast<ACharacter>(GetOwner());
	const APawn* ViewerPawn = Character ? Character : Cast<APawn>(GetOwner()->GetOwner());
	const APlayerController* Viewer = ViewerPawn ? Cast<APlayerController>(ViewerPawn->GetController()) : nullptr;
	if (Viewer && Viewer->PlayerCameraManager) { View = Viewer->PlayerCameraManager->GetCameraRotation(); }
	CameraNormal = -View.Vector();
	const float SinceHit = bTriggered ? Age - TriggerAge : 0.0f;
	float Alpha = FadeAge >= 0.0f ? FMath::Clamp(1.0f - (Age - FadeAge) / FadeSeconds, 0.0f, 1.0f) : 1.0f;
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Forward).GetSafeNormal();
	if (Kind == ESparrowVisualKind::RetreatFocus)
	{
		const FVector Bow = bTriggered || !Character || !Character->GetMesh() ? Anchor : Character->GetMesh()->GetSocketLocation(TEXT("BowEmitterSocket"));
		const float Ready = FMath::Clamp(Age / FMath::Max(Delay, 0.01f), 0.0f, 1.0f);
		const float Release = bTriggered ? FMath::Clamp(SinceHit / 0.36f, 0.0f, 1.0f) : 0.0f;
		Alpha *= bTriggered ? FMath::Pow(1.0f - Release, 1.3f) : 0.45f + 0.55f * Ready;
		const FRotator RingFacing = FRotationMatrix::MakeFromZ(Forward).Rotator();
		Ring(Bow + Forward * (25.0f + 85.0f * Release), FMath::Lerp(65.0f, 35.0f, Ready), RingFacing);
		Ring(Bow + Forward * (52.0f + 155.0f * Release), 30.0f * (1.0f - Release * 0.5f), RingFacing);
		// 양쪽 바람을 당겼다가 발사축으로 풀어, 짧은 준비 시간에도 압축과 해제를 구분한다.
		for (int32 Side : {-1, 1})
		{
			FVector Previous;
			FVector Start;
			for (int32 Segment = 0; Segment <= 8; ++Segment)
			{
				const float T = Segment / 8.0f;
				const float Spread = bTriggered ? 38.0f + 55.0f * FMath::Sin(PI * Release) : FMath::Lerp(125.0f, 38.0f, Ready);
				const FVector Point = Bow + Forward * (18.0f + T * (bTriggered ? 260.0f * Release : 65.0f)) +
					Right * (Side * Spread * (1.0f - T)) + FVector::UpVector * (26.0f * FMath::Sin(PI * T));
				if (Segment > 0)
				{
					Line(Previous, Point, 3.5f * (1.0f - T * 0.4f));
				}
				else { Start = Point; }
				Previous = Point;
			}
			Gust(Start, Previous, 64.0f, Side);
		}
		if (bTriggered)
		{
			Gust(Bow - Forward * 35.0f, Bow + Forward * (140.0f + Release * 155.0f), 76.0f * (1.0f - Release));
			Spark(Bow + Forward * 25.0f, 76.0f * FMath::Clamp(1.0f - SinceHit / 0.11f, 0.0f, 1.0f));
		}
	}
	else if (Kind == ESparrowVisualKind::RicochetFocus)
	{
		const FVector Bow = bTriggered || !Character || !Character->GetMesh() ? Anchor : Character->GetMesh()->GetSocketLocation(TEXT("BowEmitterSocket"));
		const float Ready = FMath::SmoothStep(0.0f, 1.0f, Age / FMath::Max(Delay, 0.01f));
		const float Release = bTriggered ? FMath::Clamp(SinceHit / 0.34f, 0.0f, 1.0f) : 0.0f;
		Alpha *= bTriggered ? FMath::Square(1.0f - Release) : 0.5f + 0.5f * Ready;
		for (int32 Index = 0; Index < 3; ++Index)
		{
			const float Angle = FMath::DegreesToRadians(120.0f * Index + 30.0f);
			const FVector Radial = Right * FMath::Cos(Angle) + FVector::UpVector * FMath::Sin(Angle);
			const float Spread = bTriggered ? 32.0f + 75.0f * FMath::Sin(PI * Release) : FMath::Lerp(105.0f, 32.0f, Ready);
			const FVector Center = Bow + Forward * (45.0f + Release * 265.0f) + Radial * Spread;
			const FVector Heading = bTriggered ? (Forward + Radial * Release * 0.65f).GetSafeNormal() :
				FMath::Lerp(-Radial, Forward, Ready * 0.8f).GetSafeNormal();
			const FVector Tip = Center + Heading * 25.0f;
			const FVector FeatherSide = FVector::CrossProduct(Heading, CameraNormal).GetSafeNormal();
			Gust(Center - Heading * 65.0f, Tip, 68.0f);
			Line(Tip, Tip - Heading * 20.0f + FeatherSide * 9.0f, 1.8f);
			Line(Tip, Tip - Heading * 20.0f - FeatherSide * 9.0f, 1.8f);
		}
	}
	else if (Kind == ESparrowVisualKind::RetreatWake && Character)
	{
		if (Age <= 0.33f)
		{
			WakeEnd = Character->GetActorLocation() - FVector(0.0f, 0.0f, Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() - 20.0f);
		}
		const FVector Feet = WakeEnd;
		Alpha *= FMath::Pow(FMath::Clamp(1.0f - FMath::Max(Age - 0.28f, 0.0f) / 0.48f, 0.0f, 1.0f), 1.2f);
		for (int32 Side : {-1, 1})
		{
			for (int32 Segment = 3; Segment <= 9; Segment += 3)
			{
				const float T = Segment / 10.0f;
				const FVector Point = FMath::Lerp(Anchor, Feet, T) + Right * Side * (36.0f + 48.0f * FMath::Sin(PI * T)) +
					FVector::UpVector * (18.0f * FMath::Sin(PI * T));
				Spark(Point, 18.0f * (1.0f - T * 0.5f));
			}
			Gust(Anchor + Right * Side * 45.0f, Feet + Right * Side * 45.0f, 112.0f, Side);
		}
	}
	else if (Kind == ESparrowVisualKind::ArrowFlight)
	{
		const ASparrowArrow* Projectile = Cast<ASparrowArrow>(GetOwner());
		if (Projectile)
		{
			const FVector Tip = Projectile->GetActorLocation();
			if (FlightHistory.IsEmpty() || FVector::DistSquared(FlightHistory.Last(), Tip) > 400.0f)
			{
				FlightHistory.Add(Tip);
				while (FlightHistory.Num() > 2 && FVector::DistSquared(FlightHistory[1], Tip) > FMath::Square(bChainArrow ? 310.0f : 240.0f))
				{
					FlightHistory.RemoveAt(0);
				}
				if (FlightHistory.Num() > 12) { FlightHistory.RemoveAt(0); }
			}
			const FVector Direction = Projectile->GetFlightDirection();
			const FVector Side = FVector::CrossProduct(Direction, CameraNormal).GetSafeNormal();
			const FVector Up = FVector::CrossProduct(CameraNormal, Side).GetSafeNormal();
			const int32 Strands = bChainArrow ? 3 : 2;
			for (int32 Strand = 0; Strand < Strands; ++Strand)
			{
				FVector Previous;
				for (int32 Index = 0; Index < FlightHistory.Num(); ++Index)
				{
					const float Weight = (Index + 1) / static_cast<float>(FlightHistory.Num());
					const float Phase = Age * 16.0f - Weight * 5.0f + Strand * 2.0f * PI / Strands;
					const float Spread = bChainArrow ? 17.0f * (1.0f - Weight * 0.4f) : 7.0f;
					const FVector Point = FlightHistory[Index] + (Side * FMath::Sin(Phase) + Up * FMath::Cos(Phase)) * Spread;
					if (Index > 0)
					{
						Line(Previous, Point, (bChainArrow ? 2.2f : 1.7f) + Weight * 1.2f);
					}
					Previous = Point;
				}
			}
			Gust(Tip - Direction * (bChainArrow ? 260.0f : 190.0f), Tip + Direction * 24.0f, bChainArrow ? 75.0f : 52.0f);
			for (int32 Index = -1; Index <= 1; Index += 2)
			{
				const FVector Offset = Side * Index * (bChainArrow ? 28.0f : 20.0f);
				Line(Tip - Direction * 80.0f + Offset, Tip + Direction * 20.0f, 2.8f);
			}
			Spark(Tip, bChainArrow ? 30.0f : 34.0f);
		}
	}
	else if (Kind == ESparrowVisualKind::RicochetHit)
	{
		const bool bFinal = HitOrdinal == 3;
		const float Progress = FMath::Clamp(SinceHit / (bFinal ? 0.46f : 0.34f), 0.0f, 1.0f);
		Alpha *= FMath::Square(1.0f - Progress);
		const FVector Up = FVector::CrossProduct(CameraNormal, Right).GetSafeNormal();
		const float Strength = HitOrdinal == 2 ? 0.78f : bFinal ? 1.18f : 1.0f;
		for (int32 Index = 0; Index < 3; ++Index)
		{
			const float Angle = FMath::DegreesToRadians(Index * 120.0f + 32.0f * Progress);
			const FVector Radial = Right * FMath::Cos(Angle) + Up * FMath::Sin(Angle);
			const float Fold = FMath::Clamp(Progress * 3.0f, 0.0f, 1.0f);
			const FVector Center = Anchor + Radial * FMath::Lerp(80.0f, bFinal ? 95.0f : 25.0f, Fold) * Strength +
				Forward * (bFinal ? 0.0f : 105.0f * FMath::Square(Progress));
			const FVector Heading = bFinal ? Radial : (-Radial + Forward * Fold * 2.0f).GetSafeNormal();
			const FVector Tip = Center + Heading * 30.0f;
			const FVector FeatherSide = FVector::CrossProduct(Heading, CameraNormal).GetSafeNormal();
			Gust(Center - Heading * 70.0f, Tip, 78.0f * Strength);
			Line(Tip, Tip - Heading * 18.0f + FeatherSide * 8.0f, 2.0f);
			Line(Tip, Tip - Heading * 18.0f - FeatherSide * 8.0f, 2.0f);
		}
		Spark(Anchor, 54.0f * Strength * FMath::Clamp(1.0f - SinceHit / 0.12f, 0.0f, 1.0f));
	}
	else if (Kind == ESparrowVisualKind::RetreatHit)
	{
		const float Progress = FMath::Clamp(SinceHit / 0.45f, 0.0f, 1.0f);
		Alpha *= FMath::Pow(1.0f - Progress, 1.5f);
		const FVector Up = FVector::CrossProduct(CameraNormal, Right).GetSafeNormal();
		for (int32 Side : {-1, 1})
		{
			const FVector Wing = (Right * Side + Up * 0.35f).GetSafeNormal();
			const FVector Outer = Anchor + Wing * (85.0f + 60.0f * Progress);
			Line(Anchor - Forward * 25.0f, Outer, 4.0f * (1.0f - Progress * 0.5f));
			Gust(Anchor - Forward * 55.0f, Outer + Wing * 25.0f, 86.0f, Side);
			Spark(Outer, 35.0f * (1.0f - Progress));
		}
		Spark(Anchor, 84.0f * FMath::Clamp(1.0f - SinceHit / 0.14f, 0.0f, 1.0f));
	}
	else if (Kind == ESparrowVisualKind::Ambush)
	{
		const float Deployment = FMath::SmoothStep(0.0f, 1.0f, Age / FMath::Max(Delay, 0.01f));
		const float Burst = bTriggered ? FMath::Clamp(SinceHit / 0.38f, 0.0f, 1.0f) : 0.0f;
		Alpha *= bTriggered ? FMath::Square(1.0f - Burst) : 0.6f + 0.4f * Deployment;
		const float CageRadius = Radius * (bTriggered ? FMath::Lerp(1.0f, 0.15f, FMath::Min(Burst * 4.0f, 1.0f)) : FMath::Lerp(0.25f, 0.9f, Deployment));
		Ring(Anchor + FVector(0.0f, 0.0f, 5.0f), bTriggered ? FMath::Lerp(Radius * 0.6f, 220.0f, Burst) : Radius);
		for (int32 Index = 0; Index < 6; ++Index)
		{
			const float Angle = FMath::DegreesToRadians(Index * 60.0f + 15.0f);
			const FVector Radial(FMath::Cos(Angle), FMath::Sin(Angle), 0.0f);
			const FVector Position = Anchor + Radial * CageRadius + FVector(0.0f, 0.0f, 55.0f + Deployment * 55.0f);
			const FVector Heading = (FVector::UpVector - Radial * 0.38f).GetSafeNormal();
			Arrow(Position, bTriggered ? -Radial + FVector::UpVector * (1.0f - Burst) : Heading,
				170.0f * Deployment, 2.5f);
			Wind(Position - Heading * 75.0f, Position + Heading * 75.0f, 28.0f);
			const FVector Foot = Anchor + Radial * (Radius * 0.8f) + FVector(0.0f, 0.0f, 9.0f);
			Line(Foot, Anchor + Radial * Radius * 0.35f + FVector(0.0f, 0.0f, 9.0f), 1.6f);
			const float Pulse = 0.5f + 0.5f * FMath::Sin(Age * 4.0f - Index);
			Spark(Foot + FVector(0.0f, 0.0f, 20.0f + Pulse * 12.0f), 16.0f + 12.0f * Pulse);
			if (bTriggered)
			{
				const FVector Shard = Anchor + Radial * (45.0f + Burst * 180.0f) + FVector(0.0f, 0.0f, 35.0f + 75.0f * FMath::Sin(PI * Burst));
				Line(Shard, Shard - Radial * 30.0f, 2.2f);
			}
		}
		if (!bTriggered)
		{
			Arc(Anchor + FVector(0.0f, 0.0f, 37.0f), FVector::ForwardVector, FVector::RightVector,
				Radius * 0.82f, Age * 12.0f, 240.0f, 18, 1.2f);
		}
		else { Spark(Anchor + FVector(0.0f, 0.0f, 30.0f), 90.0f * (1.0f - Burst)); }
	}
	else if (Kind == ESparrowVisualKind::Skyfall)
	{
		const float Fall = FMath::Clamp((Age - FMath::Max(0.0f, Delay - 0.20f)) / 0.20f, 0.0f, 1.0f);
		if (!bTriggered)
		{
			Ring(Anchor + FVector(0.0f, 0.0f, 5.0f), Radius * 0.75f);
			for (int32 Index = -1; Index <= 1; ++Index)
			{
				const FVector Center = Anchor + Right * Index * 43.0f + FVector(0.0f, 0.0f, FMath::Lerp(440.0f, 58.0f, Fall));
				if (Age >= Delay - 0.20f)
				{
					Arrow(Center, -FVector::UpVector, 145.0f, 3.6f);
					Wind(Center + FVector(0.0f, 0.0f, 95.0f), Center - FVector(0.0f, 0.0f, 55.0f), 28.0f);
				}
				Arrow(Anchor + Right * Index * 45.0f + FVector(0.0f, 0.0f, 9.0f), Forward, 30.0f, 1.8f);
			}
		}
		else
		{
			const float Burst = FMath::Clamp(SinceHit / 0.48f, 0.0f, 1.0f);
			Alpha *= FMath::Square(1.0f - Burst);
			Ring(Anchor + FVector(0.0f, 0.0f, 5.0f), FMath::Lerp(Radius * 0.35f, Radius, Burst));
			for (int32 Index = -1; Index <= 1; ++Index)
			{
				const FVector Point = Anchor + Right * Index * 43.0f;
				Arrow(Point + FVector(0.0f, 0.0f, 58.0f), -FVector::UpVector, 145.0f, 3.0f * (1.0f - Burst * 0.7f));
				Wind(Point + FVector(0.0f, 0.0f, 220.0f * (1.0f - Burst)), Point, 26.0f);
			}
			for (int32 Index = 0; Index < 6; ++Index)
			{
				const float Angle = FMath::DegreesToRadians(Index * 60.0f + 30.0f);
				const FVector Radial(FMath::Cos(Angle), FMath::Sin(Angle), 0.0f);
				const float Tip = FMath::Lerp(35.0f, Radius, FMath::Sqrt(Burst));
				Line(Anchor + Radial * 20.0f + FVector(0.0f, 0.0f, 8.0f), Anchor + Radial * Tip + FVector(0.0f, 0.0f, 8.0f), 3.5f);
				Spark(Anchor + Radial * Tip + FVector(0.0f, 0.0f, 18.0f), 24.0f);
			}
			Spark(Anchor + FVector(0.0f, 0.0f, 30.0f), 86.0f * (1.0f - Burst));
		}
	}
	Alpha = FMath::Clamp(Alpha, 0.0f, 1.0f);
	const bool bRicochetAccent = Kind == ESparrowVisualKind::RicochetFocus ||
		(bChainArrow && (Kind == ESparrowVisualKind::ArrowFlight || Kind == ESparrowVisualKind::RicochetHit));
	if (bRicochetAccent)
	{
		// 원본 Sparrow의 금색 심과 연보라 공기층을 분리한다. D/F의 금색 재질값은 유지한다.
		GlowMaterial->SetVectorParameterValue(TEXT("GlowColor"), FLinearColor(0.48f, 0.18f, 0.85f));
		CoreMaterial->SetVectorParameterValue(TEXT("CoreColor"), FLinearColor(1.0f, 0.82f, 0.42f));
	}
	CoreMaterial->SetScalarParameterValue(TEXT("CoreIntensity"), 2.4f * Alpha);
	CoreMaterial->SetScalarParameterValue(TEXT("GlowIntensity"), 0.38f * Alpha);
	GlowMaterial->SetScalarParameterValue(TEXT("GlowIntensity"), (bRicochetAccent ? 0.42f : 0.24f) * Alpha);
	SparkMaterial->SetScalarParameterValue(TEXT("Intensity"), 2.8f * Alpha);
	RingMaterial->SetScalarParameterValue(TEXT("Envelope"), 0.62f * Alpha);
	const float WindStrength = Kind == ESparrowVisualKind::RetreatWake ? 0.34f :
		Kind == ESparrowVisualKind::RetreatFocus || Kind == ESparrowVisualKind::RetreatHit ? 0.30f :
		Kind == ESparrowVisualKind::RicochetFocus || Kind == ESparrowVisualKind::RicochetHit || Kind == ESparrowVisualKind::ArrowFlight ? 0.25f : 0.18f;
	WindMaterial->SetScalarParameterValue(TEXT("Envelope"), WindStrength * Alpha);
	if (bUsesExtraGust)
	{
		WindMaterial->SetScalarParameterValue(TEXT("Bend"), Kind == ESparrowVisualKind::RetreatWake ? 0.26f : 0.12f);
		WindMaterial->SetScalarParameterValue(TEXT("Thickness"), Kind == ESparrowVisualKind::RetreatWake ? 0.12f : 0.09f);
		WindMaterial->SetVectorParameterValue(TEXT("CoreTint"), bRicochetAccent ?
			FLinearColor(7.0f, 4.4f, 1.5f) : FLinearColor(8.0f, 4.8f, 1.6f));
		WindMaterial->SetVectorParameterValue(TEXT("HaloTint"), bRicochetAccent ?
			FLinearColor(1.15f, 0.40f, 1.9f) : FLinearColor(1.6f, 0.65f, 0.2f));
	}
	ArrowMaterial->SetScalarParameterValue(TEXT("CoreIntensity"), 1.4f * Alpha);
	ArrowMaterial->SetScalarParameterValue(TEXT("GlowIntensity"), 0.45f * Alpha);
	// 실물 화살도 같은 곳에서 축소 침식시켜, 발광선이 사라진 뒤 검은 화살만 남지 않게 한다.
	if (Alpha < 0.95f)
	{
		for (FTransform& Transform : ArrowTransforms) { Transform.SetScale3D(Transform.GetScale3D() * Alpha); }
	}
	UpdateInstances(Core, CoreTransforms); UpdateInstances(Glow, GlowTransforms);
	UpdateInstances(Sparks, SparkTransforms);
	UpdateMeshPool(RingMeshes, RingTransforms, RingMaterial);
	UpdateMeshPool(WindMeshes, WindTransforms, WindMaterial);
	UpdateInstances(ArrowMeshes, ArrowTransforms);
}
