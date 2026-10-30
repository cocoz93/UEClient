#include "SparrowPiercingLance.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "UObject/ConstructorHelpers.h"

ASparrowPiercingLance::ASparrowPiercingLance()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false;
	SetCanBeDamaged(false);
	SetActorEnableCollision(false);
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Plane(TEXT("/Engine/BasicShapes/Plane.Plane"));
	const auto Layer = [this](const TCHAR* Name)
	{
		UInstancedStaticMeshComponent* Mesh = CreateDefaultSubobject<UInstancedStaticMeshComponent>(Name);
		Mesh->SetupAttachment(GetRootComponent());
		Mesh->SetMobility(EComponentMobility::Movable);
		Mesh->SetStaticMesh(Plane.Object);
		Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Mesh->SetGenerateOverlapEvents(false);
		Mesh->SetCanEverAffectNavigation(false);
		Mesh->SetCastShadow(false);
		Mesh->SetReceivesDecals(false);
		return Mesh;
	};
	Core = Layer(TEXT("PlatinumNeedles"));
	Glow = Layer(TEXT("GoldEdges"));
	Tags.Append({TEXT("SparrowSkillFXProxy"), TEXT("SparrowPiercingLanceVisual")});
}

bool ASparrowPiercingLance::CreateMaterials()
{
	UMaterialInterface* Strip = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Gideon/FX/M_NoxGlowStrip.M_NoxGlowStrip"));
	if (!Strip || !IsValid(GetOwner())) { Destroy(); return false; }
	CoreMaterial = Core->CreateDynamicMaterialInstance(0, Strip);
	GlowMaterial = Glow->CreateDynamicMaterialInstance(0, Strip);
	if (!CoreMaterial || !GlowMaterial) { Destroy(); return false; }
	for (UMaterialInstanceDynamic* Material : {CoreMaterial.Get(), GlowMaterial.Get()})
	{
		Material->SetVectorParameterValue(TEXT("CoreColor"), FLinearColor(1.0f, 0.96f, 0.72f));
		Material->SetVectorParameterValue(TEXT("GlowColor"), FLinearColor(1.0f, 0.58f, 0.08f));
		Material->SetScalarParameterValue(TEXT("CoreSharpness"), 5.0f);
		Material->SetScalarParameterValue(TEXT("GlowSoftness"), 2.0f);
	}
	CoreMaterial->SetScalarParameterValue(TEXT("GlowIntensity"), 0.0f);
	GlowMaterial->SetScalarParameterValue(TEXT("CoreIntensity"), 0.0f);
	bReady = true;
	return true;
}

void ASparrowPiercingLance::InitializeFlight(const FVector& Direction)
{
	Origin = Head = GetActorLocation();
	Forward = Direction.GetSafeNormal();
	if (Forward.IsNearlyZero() || !CreateMaterials()) { Destroy(); return; }
	SetLifeSpan(0.85f);
	SetActorTickEnabled(true);
	Draw();
}

void ASparrowPiercingLance::UpdateHead(const FVector& Position)
{
	if (FinishedAt < 0.0f) { Head = Position; }
}

void ASparrowPiercingLance::FinishFlight(const FVector& Position)
{
	if (FinishedAt >= 0.0f) { return; }
	Head = Position;
	FinishedAt = Age;
	SetLifeSpan(0.20f);
	Draw();
}

void ASparrowPiercingLance::InitializeImpact(const FVector& Direction, int32 HitOrdinal, bool bWorld)
{
	bImpact = true;
	bWorldHit = bWorld;
	Ordinal = HitOrdinal;
	Origin = Head = GetActorLocation();
	Forward = Direction.GetSafeNormal();
	if (!CreateMaterials()) { return; }
	Tags.Add(TEXT("SparrowPiercingLanceImpact"));
	SpawnTexture(bWorld);
	SetLifeSpan(bWorld ? 0.23f : 0.34f);
	SetActorTickEnabled(true);
	Draw();
}

void ASparrowPiercingLance::SpawnTexture(bool bWorld)
{
	UParticleSystem* Source = LoadObject<UParticleSystem>(nullptr,
		TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Ultimate/FX/P_Sparrow_UltHit.P_Sparrow_UltHit"));
	if (!Source) { return; }
	Texture = NewObject<UParticleSystemComponent>(this, TEXT("PiercingContactTexture"));
	Texture->bAutoActivate = false;
	Texture->bAutoDestroy = false;
	Texture->SetTemplate(Source);
	Texture->SetupAttachment(GetRootComponent());
	Texture->SetRelativeRotation(Forward.Rotation());
	Texture->SetRelativeScale3D(bWorld ? FVector(0.28f) : FVector(0.48f, 0.34f, 0.34f));
	Texture->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Texture->SetCanEverAffectNavigation(false);
	Texture->bOverrideLODMethod = true;
	Texture->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
	Texture->CustomTimeDilation = 1.7f;
	Texture->ComponentTags.Append({TEXT("SparrowSkillFX"), TEXT("SparrowPiercingLanceTexture")});
	AddInstanceComponent(Texture);
	Texture->RegisterComponent();
	Texture->SetLODLevel(0);
	Texture->ActivateSystem(true);
	// 원본 침식과 메시 입자는 유지하고 큰 섬광·안개 층만 끈다.
	for (const FName Name : {FName(TEXT("Particle Emitter")), FName(TEXT("Flare")),
		FName(TEXT("Wisps")), FName(TEXT("AddFlare")), FName(TEXT("Line Burst"))})
	{
		Texture->SetEmitterEnable(Name, false);
	}
	Texture->SetEmitterEnable(TEXT("Main Flames"), !bWorld);
	Texture->SetEmitterEnable(TEXT("SparkTrailHeads"), true);
	Texture->SetEmitterEnable(TEXT("Sparks"), true);
}

void ASparrowPiercingLance::Line(const FVector& From, const FVector& To, float Width)
{
	const FVector Delta = To - From;
	const float Length = Delta.Size();
	if (Length < 0.1f || Width < 0.02f) { return; }
	const FRotator Facing = FRotationMatrix::MakeFromXZ(Delta / Length, CameraNormal).Rotator();
	CoreTransforms.Add(FTransform(Facing, (From + To) * 0.5f, FVector(Length / 100.0f, Width / 100.0f, 1.0f)));
	GlowTransforms.Add(FTransform(Facing, (From + To) * 0.5f, FVector(Length / 100.0f, Width * 3.0f / 100.0f, 1.0f)));
}

void ASparrowPiercingLance::Arc(const FVector& Center, const FVector& AxisA, const FVector& AxisB,
	float Radius, float Begin, float Sweep, int32 Count, float Width)
{
	for (int32 Index = 0; Index < Count; ++Index)
	{
		const float A = Begin + Sweep * static_cast<float>(Index) / Count;
		const float B = Begin + Sweep * static_cast<float>(Index + 1) / Count;
		Line(Center + (AxisA * FMath::Cos(A) + AxisB * FMath::Sin(A)) * Radius,
			Center + (AxisA * FMath::Cos(B) + AxisB * FMath::Sin(B)) * Radius, Width);
	}
}

void ASparrowPiercingLance::Draw()
{
	if (!bReady) { return; }
	const APlayerController* Player = GetWorld() ? GetWorld()->GetFirstPlayerController() : nullptr;
	if (Player && Player->PlayerCameraManager)
	{
		CameraNormal = (Player->PlayerCameraManager->GetCameraLocation() - Origin).GetSafeNormal();
	}
	CoreTransforms.Reset();
	GlowTransforms.Reset();
	float Envelope = 1.0f;
	if (bImpact)
	{
		const float Duration = bWorldHit ? 0.23f : 0.34f;
		Envelope = FMath::Square(FMath::Clamp(1.0f - Age / Duration, 0.0f, 1.0f));
		const float Growth = 0.55f + 0.45f * FMath::Clamp(Age / 0.045f, 0.0f, 1.0f);
		const FVector Horizontal = FVector::CrossProduct(FVector::UpVector, CameraNormal).GetSafeNormal();
		const FVector Vertical = FVector::CrossProduct(CameraNormal, Horizontal).GetSafeNormal();
		const float Radius = (bWorldHit ? 28.0f : 66.0f) * Growth;
		for (int32 Index = 0; Index < 18; ++Index)
		{
			const float Angle = Index * UE_TWO_PI / 18.0f + Ordinal * 0.31f;
			const FVector Axis = Horizontal * FMath::Cos(Angle) + Vertical * FMath::Sin(Angle);
			const float Tip = Radius * (Index % 3 == 0 ? 1.0f : Index % 2 == 0 ? 0.72f : 0.44f);
			Line(Origin + Axis * 3.0f, Origin + Axis * Tip, Index % 3 == 0 ? 3.6f : 2.0f);
		}
		if (!bWorldHit)
		{
			Arc(Origin, Horizontal * 0.46f + Vertical * 0.22f, Vertical,
				49.0f * Growth, -0.35f + Age * 4.0f, 5.1f, 26, 1.7f);
			Line(Origin - Horizontal * 82.0f, Origin + Horizontal * 82.0f, 2.6f);
		}
	}
	else
	{
		Envelope = FinishedAt < 0.0f ? 1.0f : FMath::Square(FMath::Clamp(1.0f - (Age - FinishedAt) / 0.20f, 0.0f, 1.0f));
		Line(Origin, Head, 3.2f);
		Line(Origin + FVector::UpVector * 2.6f, Head + FVector::UpVector * 2.6f, 0.9f);
		const float Muzzle = FMath::Square(FMath::Clamp(1.0f - Age / 0.19f, 0.0f, 1.0f));
		if (Muzzle > 0.01f)
		{
			const FVector Side = FVector::CrossProduct(Forward, FVector::UpVector).GetSafeNormal();
			Arc(Origin + Forward * 14.0f, Forward * -0.45f, FVector::UpVector,
				76.0f * (0.7f + 0.3f * (1.0f - Muzzle)), -1.5f, 3.0f, 28, 2.8f * Muzzle);
			Line(Origin - Side * 16.0f, Origin + Forward * 58.0f, 2.0f * Muzzle);
		}
	}
	CoreMaterial->SetScalarParameterValue(TEXT("CoreIntensity"), Envelope * (bImpact ? 1.4f : 0.88f));
	GlowMaterial->SetScalarParameterValue(TEXT("GlowIntensity"), Envelope * (bImpact ? 0.30f : 0.18f));
	const auto Update = [](UInstancedStaticMeshComponent* Mesh, const TArray<FTransform>& Transforms)
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
	};
	Update(Core, CoreTransforms);
	Update(Glow, GlowTransforms);
}

void ASparrowPiercingLance::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!IsValid(GetOwner())) { Destroy(); return; }
	Age += FMath::Max(0.0f, DeltaSeconds);
	Draw();
}

void ASparrowPiercingLance::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (Texture) { Texture->DestroyComponent(); }
	Super::EndPlay(EndPlayReason);
}
