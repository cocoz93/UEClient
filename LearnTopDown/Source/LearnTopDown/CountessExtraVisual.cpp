#include "CountessExtraVisual.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"

ACountessExtraVisual::ACountessExtraVisual()
{
	PrimaryActorTick.bCanEverTick = true;
	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
	SetRootComponent(SceneRoot);
	SetActorEnableCollision(false);
	SetCanBeDamaged(false);
	Tags.Add(TEXT("CountessExtraVisual"));
	InkMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
		TEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessExtraInk_20261021.M_CountessExtraInk_20261021")));
	QualityMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
		TEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessExtraInkQuality2_20261021.M_CountessExtraInkQuality2_20261021")));
}

void ACountessExtraVisual::Initialize(ECountessExtraVisual InKind, const FVector& Direction, float Lifetime, AActor* Follow)
{
	Kind = InKind;
	StartedAt = GetWorld()->GetTimeSeconds();
	LifeSeconds = FMath::Clamp(Lifetime, 0.1f, 2.5f);
	SetLifeSpan(LifeSeconds);
	SetActorRotation(Direction.GetSafeNormal2D().Rotation());
	FollowActor = Follow;
	FollowOffset = IsValid(Follow) ? GetActorLocation() - Follow->GetActorLocation() : FVector::ZeroVector;
	if (Kind == ECountessExtraVisual::Seal || Kind == ECountessExtraVisual::Ambush || Kind == ECountessExtraVisual::AuthoredImpact)
	{
		// 원본 입체 메시 이미터와 수명 곡선 전체를 전용 사본으로 재생한다. 피해 타이머는 갖지 않는다.
		if (Kind == ECountessExtraVisual::Seal)
		{
			GatherEffect = SpawnAuthored(TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessBloodSealGather.P_CountessBloodSealGather"),
				FVector(0, 0, -18), FRotator::ZeroRotator, .55f);
		}
		else if (Kind == ECountessExtraVisual::AuthoredImpact)
		{
			SpawnAuthored(TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessShadowContact.P_CountessShadowContact"),
				FVector::ZeroVector, FRotator::ZeroRotator, .48f);
		}
		UE_LOG(LogTemp, Display, TEXT("COUNTESS_EXTRA_AUTHORED kind=%d phase=prepare effects=%d"), static_cast<int32>(Kind), AuthoredEffects.Num());
		return;
	}
	UMaterialInterface* Material = Kind == ECountessExtraVisual::Rush ? InkMaterial.LoadSynchronous() : QualityMaterial.LoadSynchronous();
	UStaticMesh* Plane = TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(TEXT("/Engine/BasicShapes/Plane.Plane"))).LoadSynchronous();
	if (!Material || !Plane) { Destroy(); return; }
	if (Kind == ECountessExtraVisual::Rush)
	{
		UStaticMesh* Blade = TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(
			TEXT("/Game/ParagonCountess/FX/Meshes/Shapes/SM_Countess_SwordAbstractMesh.SM_Countess_SwordAbstractMesh"))).LoadSynchronous();
		if (!Blade) { Destroy(); return; }
		AddPart(Blade, Material, false);
		AddPart(Plane, Material, true);
		AddPart(Plane, Material, true);
	}
	else if (Kind == ECountessExtraVisual::Tide)
	{
		for (int32 Index = 0; Index < 4; ++Index) { AddPart(Plane, Material, true, 3.0f); }
		for (int32 Index = 0; Index < 3; ++Index) { AddPart(Plane, Material, true, 2.0f); }
		for (int32 Index = 0; Index < 2; ++Index) { AddPart(Plane, Material, true, 4.0f); }
	}
	else
	{
		for (int32 Index = 0; Index < 7; ++Index) { AddPart(Plane, Material, true, 5.0f); }
		for (int32 Index = 0; Index < 2; ++Index) { AddPart(Plane, Material, true, 4.0f); }
	}
	UpdateParts();
	UE_LOG(LogTemp, Display, TEXT("COUNTESS_EXTRA_VISUAL kind=%d parts=%d"), static_cast<int32>(Kind), Parts.Num());
}

void ACountessExtraVisual::AddPart(UStaticMesh* Mesh, UMaterialInterface* Material, bool bCard, float Shape)
{
	UStaticMeshComponent* Part = NewObject<UStaticMeshComponent>(this);
	Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Part->SetGenerateOverlapEvents(false);
	Part->SetCanEverAffectNavigation(false);
	Part->SetStaticMesh(Mesh);
	Part->SetupAttachment(SceneRoot);
	Part->SetCastShadow(false);
	Part->SetReceivesDecals(false);
	Part->ComponentTags.Add(TEXT("CountessExtraFX"));
	Part->RegisterComponent();
	UMaterialInstanceDynamic* Dynamic = UMaterialInstanceDynamic::Create(Material, this);
	Dynamic->SetScalarParameterValue(TEXT("Card"), bCard ? 1.0f : 0.0f);
	Dynamic->SetScalarParameterValue(TEXT("Shape"), Shape);
	Dynamic->SetScalarParameterValue(TEXT("Seed"), Parts.Num() * 1.371f);
	for (int32 Slot = 0; Slot < FMath::Max(1, Part->GetNumMaterials()); ++Slot) { Part->SetMaterial(Slot, Dynamic); }
	Parts.Add(Part);
	Materials.Add(Dynamic);
	Cards.Add(bCard);
}

void ACountessExtraVisual::SetPart(int32 Index, const FVector& Center, const FVector& Direction,
	float Length, float Width, float Fade, float Pulse, float Opacity, bool bFaceCamera)
{
	if (!Parts.IsValidIndex(Index)) { return; }
	UStaticMeshComponent* Part = Parts[Index];
	const FBox Box = Part->GetStaticMesh()->GetBoundingBox();
	const FVector Size = Box.GetSize();
	int32 LongAxis = 0;
	for (int32 Axis = 1; Axis < 3; ++Axis) { if (Size[Axis] > Size[LongAxis]) { LongAxis = Axis; } }
	int32 WideAxis = (LongAxis + 1) % 3;
	for (int32 Axis = 0; Axis < 3; ++Axis) { if (Axis != LongAxis && Size[Axis] > Size[WideAxis]) { WideAxis = Axis; } }
	FVector SourceLong = FVector::ZeroVector;
	FVector SourceWide = FVector::ZeroVector;
	SourceLong[LongAxis] = 1.0f;
	SourceWide[WideAxis] = 1.0f;
	const FVector Aim = (bFaceCamera ? Direction - ViewDirectionLocal * FVector::DotProduct(Direction, ViewDirectionLocal) : Direction).GetSafeNormal();
	FVector Side = FVector::CrossProduct(bFaceCamera ? ViewDirectionLocal : FVector::UpVector, Aim).GetSafeNormal();
	if (Side.IsNearlyZero()) { Side = FVector::RightVector; }
	const FQuat Rotation = FRotationMatrix::MakeFromXY(Aim, Side).ToQuat() *
		FRotationMatrix::MakeFromXY(SourceLong, SourceWide).ToQuat().Inverse();
	FVector Scale(1.0f);
	for (int32 Axis = 0; Axis < 3; ++Axis)
	{
		Scale[Axis] = (Axis == LongAxis ? Length : (Axis == WideAxis ? Width : 5.0f)) / FMath::Max(0.1f, Size[Axis]);
	}
	Part->SetRelativeTransform(FTransform(Rotation, Center - Rotation.RotateVector(Box.GetCenter() * Scale), Scale));
	Materials[Index]->SetScalarParameterValue(TEXT("Fade"), FMath::Clamp(Fade, 0.0f, 1.0f));
	Materials[Index]->SetScalarParameterValue(TEXT("Pulse"), FMath::Clamp(Pulse, 0.0f, 1.0f));
	Materials[Index]->SetScalarParameterValue(TEXT("Opacity"), FMath::Clamp(Opacity, 0.0f, 1.0f));
}

void ACountessExtraVisual::UpdateParts()
{
	if (Kind == ECountessExtraVisual::Seal || Kind == ECountessExtraVisual::Ambush || Kind == ECountessExtraVisual::AuthoredImpact) { return; }
	const double Now = GetWorld()->GetTimeSeconds();
	if (const APlayerController* Controller = GetWorld()->GetFirstPlayerController(); Controller && Controller->PlayerCameraManager)
	{
		ViewDirectionLocal = GetActorQuat().UnrotateVector(Controller->PlayerCameraManager->GetCameraLocation() - GetActorLocation()).GetSafeNormal();
	}
	const FVector ScreenRight = FVector::CrossProduct(FVector::UpVector, ViewDirectionLocal).GetSafeNormal();
	const float Age = static_cast<float>(Now - StartedAt);
	const float BurstAge = TriggeredAt >= 0.0 ? static_cast<float>(Now - TriggeredAt) : -1.0f;
	float Fade = FMath::Clamp((LifeSeconds - Age) / 0.25f, 0.0f, 1.0f);
	if (RetiredAt >= 0.0) { Fade *= FMath::Clamp(1.0f - static_cast<float>(Now - RetiredAt) / 0.38f, 0.0f, 1.0f); }
	const float Pulse = BurstAge >= 0.0f ? FMath::Clamp(1.0f - BurstAge / 0.16f, 0.0f, 1.0f) : 0.0f;
	if (Kind == ECountessExtraVisual::Rush)
	{
		SetPart(0, FVector(108, 0, 12), FVector::ForwardVector, 142.0f, 24.0f, Fade, 0.3f);
		SetPart(1, FVector(16, -35, -81), FVector(1, -.16f, 0), 180.0f, 38.0f, Fade, 0.0f, .65f);
		SetPart(2, FVector(-35, 42, -80), FVector(1, .22f, 0), 148.0f, 30.0f, Fade, 0.0f, .45f);
	}
	else if (Kind == ECountessExtraVisual::Impact)
	{
		const float Progress = FMath::Clamp(Age / .42f, 0.0f, 1.0f);
		for (int32 Index = 0; Index < 7; ++Index)
		{
			const FVector Outward = FVector::ForwardVector.RotateAngleAxis(Index * 137.5f, FVector::UpVector);
			const float Reach = (Index < 4 ? 82.0f : 51.0f) * FMath::Sqrt(Progress);
			const FVector Where = Outward * Reach + FVector(0, 0, 24.0f * FMath::Sin(Progress * PI) - Progress * 28.0f) + ViewDirectionLocal * 20;
			SetPart(Index, Where, Outward + FVector::UpVector * .3f,
				Index < 4 ? 31.0f : 17.0f, Index < 4 ? 18.0f : 10.0f, Fade, 1.0f - Progress, 1.0f, true);
		}
		SetPart(7, FVector(0, 0, -76), FVector(1, .4f, 0), 150.0f, 88.0f, Fade, 1.0f - Progress, .8f);
		SetPart(8, FVector(-18, 13, -75), FVector(1, -.7f, 0), 112.0f, 65.0f, Fade, 1.0f - Progress, .7f);
	}
	else
	{
		SetPart(0, FVector(100, 0, -40), FVector::ForwardVector, 195.0f, 180.0f, Fade, Pulse, .92f);
		SetPart(1, FVector(70, -25, -18), FVector(1, .15f, .75f), 170.0f, 150.0f, Fade, Pulse, .78f);
		SetPart(2, FVector(10, 33, -35), FVector(1, -.12f, .25f), 210.0f, 136.0f, Fade, Pulse, .73f);
		SetPart(3, FVector(-30, -20, -10), FVector(1, .15f, .45f), 170.0f, 115.0f, Fade, Pulse, .62f);
		SetPart(4, FVector(-125, -45, -70), FVector(1, .2f, 0), 220.0f, 92.0f, Fade, Pulse, .8f);
		SetPart(5, FVector(-180, 35, -74), FVector(1, -.3f, 0), 180.0f, 80.0f, Fade, Pulse, .72f);
		SetPart(6, FVector(-225, -15, -72), FVector(1, .18f, 0), 140.0f, 68.0f, Fade, Pulse, .62f);
		SetPart(7, FVector(-90, -70, -83), FVector(1, .4f, 0), 140.0f, 75.0f, Fade, Pulse, .78f);
		SetPart(8, FVector(-170, 50, -82), FVector(1, -.5f, 0), 110.0f, 62.0f, Fade, Pulse, .65f);
	}
}

UParticleSystemComponent* ACountessExtraVisual::SpawnAuthored(const TCHAR* Path, const FVector& Offset,
	const FRotator& Rotation, float Scale)
{
	AuthoredEffects.RemoveAll([](const TObjectPtr<UParticleSystemComponent>& Effect) { return !IsValid(Effect); });
	if (AuthoredEffects.Num() >= 4 || !GetWorld() || RetiredAt >= 0.0) { return nullptr; }
	UParticleSystem* Asset = TSoftObjectPtr<UParticleSystem>(FSoftObjectPath(Path)).LoadSynchronous();
	if (!Asset)
	{
		UE_LOG(LogTemp, Warning, TEXT("COUNTESS_EXTRA_AUTHORED missing_asset=%s"), Path);
		return nullptr;
	}
	UParticleSystemComponent* Effect = NewObject<UParticleSystemComponent>(this);
	Effect->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Effect->SetGenerateOverlapEvents(false);
	Effect->SetCanEverAffectNavigation(false);
	Effect->SetupAttachment(SceneRoot);
	Effect->SetAutoActivate(false);
	Effect->SetTemplate(Asset);
	Effect->bAutoDestroy = true;
	Effect->bOverrideLODMethod = true;
	Effect->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
	// 신규 컴포넌트는 처음부터 액터 상대 좌표다. 원본 bone 발원은 전용 에셋에서 꺼 둔다.
	Effect->SetAbsolute(false, false, false);
	Effect->SetRelativeLocationAndRotation(Offset, Rotation);
	Effect->SetRelativeScale3D(FVector(Scale));
	Effect->ComponentTags.Add(TEXT("CountessExtraFX"));
	Effect->ComponentTags.Add(TEXT("CountessExtraAuthoredFX"));
	Effect->RegisterComponent();
	Effect->SetLODLevel(0);
	Effect->ActivateSystem(true);
	Effect->SetLODLevel(0);
	AuthoredEffects.Add(Effect);
	return Effect;
}

void ACountessExtraVisual::StopAuthored()
{
	for (UParticleSystemComponent* Effect : AuthoredEffects)
	{
		if (IsValid(Effect)) { Effect->DeactivateSystem(); }
	}
}

void ACountessExtraVisual::Trigger()
{
	if (TriggeredAt >= 0.0 || RetiredAt >= 0.0 || !GetWorld()) { return; }
	TriggeredAt = GetWorld()->GetTimeSeconds();
	if (Kind == ECountessExtraVisual::Seal)
	{
		if (GatherEffect.IsValid()) { GatherEffect->DeactivateSystem(); }
		SpawnAuthored(TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessBloodSealBurst.P_CountessBloodSealBurst"),
			FVector(0, 0, -5), FRotator::ZeroRotator, .48f);
		SpawnAuthored(TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessBloodSealGround.P_CountessBloodSealGround"),
			FVector(0, 0, -88), FRotator::ZeroRotator, .28f);
		UE_LOG(LogTemp, Display, TEXT("COUNTESS_EXTRA_AUTHORED seal phase=burst effects=%d seconds=.38"), AuthoredEffects.Num());
	}
	else if (Kind == ECountessExtraVisual::Ambush)
	{
		SpawnAuthored(TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessShadowAmbushSlash.P_CountessShadowAmbushSlash"),
			FVector(0, 0, 82), FRotator::ZeroRotator, .50f);
		UE_LOG(LogTemp, Display, TEXT("COUNTESS_EXTRA_AUTHORED ambush phase=strike effects=%d seconds=.24"), AuthoredEffects.Num());
	}
}

void ACountessExtraVisual::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	for (UParticleSystemComponent* Effect : AuthoredEffects)
	{
		if (IsValid(Effect)) { Effect->DestroyComponent(); }
	}
	AuthoredEffects.Reset();
	GatherEffect.Reset();
	FollowActor.Reset();
	Super::EndPlay(EndPlayReason);
}

void ACountessExtraVisual::Retire()
{
	if (RetiredAt >= 0.0) { return; }
	FollowActor.Reset();
	StopAuthored();
	RetiredAt = GetWorld()->GetTimeSeconds();
	SetLifeSpan(0.4f);
}

void ACountessExtraVisual::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!IsValid(GetOwner())) { Destroy(); return; }
	if (FollowActor.IsValid()) { SetActorLocation(FollowActor->GetActorLocation() + FollowOffset); }
	else if (Kind == ECountessExtraVisual::Seal && RetiredAt < 0.0) { Retire(); }
	UpdateParts();
}
