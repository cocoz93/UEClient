#include "SparrowHolyBow.h"
#include "SparrowEDesignVisual.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "SparrowSkillComponent.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	TAutoConsoleVariable<int32> CVarSparrowEDesignStyle(TEXT("Sparrow.EDesign.Style"), 8,
		TEXT("E candidates: 0 installed, 1 radiant recurve, 2 close sweep, 3/4/5 converging light/plasma/lightning, 6 articulated solar bow, 7 horizontal illuminated regalia, 8 attached feather bow."));
	float Ease(float A, float B, float Time) { return FMath::SmoothStep(A, B, Time); }
	float Seed(int32 Index)
	{
		const float Value = FMath::Sin(Index * 127.1f + 311.7f) * 43758.5453f;
		return Value - FMath::FloorToFloat(Value);
	}
}

ASparrowHolyBow::ASparrowHolyBow()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false;
	SetCanBeDamaged(false);
	SetActorEnableCollision(false);
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Plane(TEXT("/Engine/BasicShapes/Plane.Plane"));
	const auto Configure = [this](UStaticMeshComponent* Mesh)
	{
		Mesh->SetupAttachment(GetRootComponent());
		Mesh->SetMobility(EComponentMobility::Movable);
		Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Mesh->SetGenerateOverlapEvents(false);
		Mesh->SetCanEverAffectNavigation(false);
		Mesh->SetCastShadow(false);
		Mesh->SetReceivesDecals(false);
		Mesh->SetStaticMesh(Plane.Object);
		Mesh->ComponentTags.Append({TEXT("SparrowSkillFX"), TEXT("SparrowHolyBow")});
	};
	Bow = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("RadiantBow")); Configure(Bow);
	Core = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("WaveCores")); Configure(Core);
	Glow = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("WaveGlows")); Configure(Glow);
	CoreTransforms.Reserve(640);
	GlowTransforms.Reserve(640);
	Tags.Append({TEXT("SparrowSkillFXProxy"), TEXT("SparrowHolyBowVisual")});
}

void ASparrowHolyBow::Initialize(const FVector& Direction, int32 InDesignStyle)
{
	Forward = Direction.GetSafeNormal();
	DesignStyle = FMath::Clamp(InDesignStyle < 0 ? CVarSparrowEDesignStyle.GetValueOnGameThread() : InDesignStyle, 0, 8);
	if (DesignStyle > 0 && IsValid(GetOwner()) && !Forward.IsNearlyZero())
	{
		FActorSpawnParameters Spawn;
		Spawn.Owner = GetOwner(); Spawn.ObjectFlags |= RF_Transient;
		Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		ASparrowEDesignVisual* Visual = GetWorld()->SpawnActor<ASparrowEDesignVisual>(GetActorLocation(), Forward.Rotation(), Spawn);
		if (Visual && Visual->Initialize(Forward, DesignStyle, bImpact, ImpactScale < .9f))
		{
			DesignVisual = Visual;
			Bow->SetVisibility(false); Core->SetVisibility(false); Glow->SetVisibility(false);
			Tags.AddUnique(*FString::Printf(TEXT("SparrowEDesign%d"), DesignStyle));
			bReady = true; SetLifeSpan(2.0f); SetActorTickEnabled(true);
			return;
		}
		DesignStyle = 0;
		UE_LOG(LogTemp, Warning, TEXT("SPARROW_E_DESIGN missing authored visual; keeping installed E"));
	}
	const USparrowSkillComponent* Skills = IsValid(GetOwner()) ? GetOwner()->FindComponentByClass<USparrowSkillComponent>() : nullptr;
	bAscended = Skills && Skills->GetAscensionRemaining() > 0.0f;
	if (bAscended) { Tags.Add(TEXT("SparrowAscendedHolyBow")); }
	UMaterialInterface* BowSurface = LoadObject<UMaterialInterface>(nullptr,
		bAscended ? TEXT("/Game/TopDown/Characters/Sparrow/Materials/AscendedArsenal20261026/M_HolyBow.M_HolyBow") :
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowHolyBowFeather.M_SparrowHolyBowFeather"));
	UMaterialInterface* Strip = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Gideon/FX/M_NoxGlowStrip.M_NoxGlowStrip"));
	if (!BowSurface || !Strip || !IsValid(GetOwner()) || Forward.IsNearlyZero()) { Destroy(); return; }
	BowMaterial = Bow->CreateDynamicMaterialInstance(0, BowSurface);
	CoreMaterial = Core->CreateDynamicMaterialInstance(0, Strip);
	GlowMaterial = Glow->CreateDynamicMaterialInstance(0, Strip);
	if (!BowMaterial || !CoreMaterial || !GlowMaterial) { Destroy(); return; }
	for (UMaterialInstanceDynamic* Material : {CoreMaterial.Get(), GlowMaterial.Get()})
	{
		Material->SetVectorParameterValue(TEXT("CoreColor"), FLinearColor(1.0f, 0.94f, 0.69f));
		Material->SetVectorParameterValue(TEXT("GlowColor"), FLinearColor(1.0f, 0.57f, 0.09f));
		Material->SetScalarParameterValue(TEXT("CoreSharpness"), 4.0f);
		Material->SetScalarParameterValue(TEXT("GlowSoftness"), 2.4f);
	}
	CoreMaterial->SetScalarParameterValue(TEXT("GlowIntensity"), 0.0f);
	GlowMaterial->SetScalarParameterValue(TEXT("CoreIntensity"), 0.0f);
	Origin = GetActorLocation() + Forward * 18.0f;
	OwnerStart = GetOwner()->GetActorLocation();
	bReady = true;
	SetLifeSpan(2.0f);
	SetActorTickEnabled(true);
	Draw();
}

void ASparrowHolyBow::NotifyShot()
{
	if (!bReady || FinishedAt >= 0.0f) { return; }
	++ShotsObserved;
	LastShotAge = Age;
	if (DesignVisual.IsValid()) { DesignVisual->NotifyShot(); }
}

void ASparrowHolyBow::InitializeImpact(const FVector& Direction, bool bWorld, int32 InDesignStyle)
{
	bImpact = true;
	ImpactScale = bWorld ? 0.55f : 1.0f;
	Initialize(Direction, InDesignStyle);
	Origin = GetActorLocation();
	Bow->SetVisibility(false);
	Tags.AddUnique(TEXT("SparrowHolyArrowImpact"));
	SetLifeSpan(0.32f);
}

void ASparrowHolyBow::FadeOut()
{
	if (DesignVisual.IsValid()) { DesignVisual->FadeOut(); }
	if (FinishedAt < 0.0f) { FinishedAt = Age; SetLifeSpan(0.18f); }
}

void ASparrowHolyBow::Line(const FVector& A, const FVector& B, float Width)
{
	const FVector Delta = B - A;
	const float Length = Delta.Size();
	if (Length < 0.05f || Width < 0.03f) { return; }
	const FRotator Rotation = FRotationMatrix::MakeFromXZ(Delta / Length, CameraNormal).Rotator();
	CoreTransforms.Emplace(Rotation, (A + B) * 0.5f, FVector((Length + Width * 0.4f) / 100.0f, Width / 100.0f, 1.0f));
	GlowTransforms.Emplace(Rotation, (A + B) * 0.5f, FVector((Length + Width) / 100.0f, Width * 3.1f / 100.0f, 1.0f));
}

void ASparrowHolyBow::Draw()
{
	if (!bReady) { return; }
	if (DesignStyle > 0) { return; }
	if (bImpact) { DrawImpact(); return; }
	const FVector Center = Origin + (GetOwner()->GetActorLocation() - OwnerStart);
	const APlayerController* Player = GetWorld()->GetFirstPlayerController();
	if (Player && Player->PlayerCameraManager)
	{
		CameraNormal = (Player->PlayerCameraManager->GetCameraLocation() - Center).GetSafeNormal();
	}
	const FRotator Facing = FRotationMatrix::MakeFromXZ(Forward, CameraNormal).Rotator();
	Bow->SetWorldLocation(Center);
	Bow->SetWorldRotation(Facing);
	Bow->SetWorldScale3D(FVector(3.3f, 5.4f, 1.0f) * (bAscended ? 1.08f : 1.0f));
	const float SinceShot = LastShotAge < 0.0f ? 10.0f : Age - LastShotAge;
	const float ReleaseFade = LastShotAge < 0.0f ? 1.0f : 1.0f - Ease(0.08f, 0.28f, SinceShot);
	const float Envelope = (FinishedAt < 0.0f ? 1.0f : 1.0f - Ease(0.0f, 0.18f, Age - FinishedAt)) * ReleaseFade;
	const float Pulse = FMath::Exp(-SinceShot * 24.0f);
	BowMaterial->SetScalarParameterValue(TEXT("Age"), Age);
	BowMaterial->SetScalarParameterValue(TEXT("Open"), Ease(0.01f, 0.23f, Age));
	BowMaterial->SetScalarParameterValue(TEXT("Draw"), LastShotAge < 0.0f ? Ease(0.06f, 0.31f, Age) : 0.16f * FMath::Exp(-SinceShot * 18.0f));
	BowMaterial->SetScalarParameterValue(TEXT("Pulse"), Pulse);
	BowMaterial->SetScalarParameterValue(TEXT("Envelope"), Envelope);
	CoreTransforms.Reset(); GlowTransforms.Reset();
	const FVector BowUp = FRotationMatrix(Facing).GetUnitAxis(EAxis::Y);
	// Open, forward-pointing crests compress toward the shot. No circular gate obscures the bow.
	for (int32 Layer = 0; Layer < 3; ++Layer)
	{
		const float LocalAge = Age - 0.12f - Layer * 0.045f;
		if (LocalAge <= 0.0f) { continue; }
		// The preparation crests vanish at release rather than reading as extra arrows in flight.
		const float CrestFade = LastShotAge < 0.0f ? 1.0f : 1.0f - Ease(0.0f, 0.07f, SinceShot);
		const float Form = Ease(0.0f, 0.09f, LocalAge) * CrestFade;
		if (Form < 0.001f) { continue; }
		const float Release = LastShotAge < 0.0f ? 0.0f : Ease(0.0f, 0.11f, SinceShot);
		const float Width = (57.0f - Layer * 12.0f) * Form * (1.0f - Release * 0.78f);
		const FVector Crest = Center + Forward * (70.0f + Layer * 44.0f + Release * 105.0f);
		for (float Sign : {-1.0f, 1.0f})
		{
			const FVector Root = Crest - Forward * 19.0f + BowUp * Sign * Width;
			const FVector Tip = Crest + Forward * 36.0f;
			const FVector ControlA = Root + Forward * 34.0f + BowUp * Sign * Width * 0.10f;
			const FVector ControlB = Tip - Forward * 14.0f + BowUp * Sign * Width * 0.14f;
			const auto Curve = [&](float T)
			{
				const float U = 1.0f - T;
				return Root * U * U * U + ControlA * 3.0f * U * U * T
					+ ControlB * 3.0f * U * T * T + Tip * T * T * T;
			};
			for (int32 Segment = 0; Segment < 12; ++Segment)
			{
				const float T = Segment / 12.0f;
				const float Next = (Segment + 1) / 12.0f;
				const float Packet = FMath::Exp(-FMath::Square((T - FMath::Frac(LocalAge * 3.2f)) * 5.0f));
				Line(Curve(T), Curve(Next), Form * (0.55f + FMath::Sin(T * UE_PI) * 1.6f + Packet * 1.1f + Pulse));
				if (Segment < 7)
				{
					const FVector Offset = -Forward * 6.0f + BowUp * Sign * 4.0f;
					Line(Curve(T) + Offset, Curve(Next) + Offset, Form * 0.65f);
				}
			}
			const FVector Jewel = Curve(0.28f);
			Line(Jewel - Forward * 3.0f, Jewel + Forward * 3.0f, Form * 3.4f);
		}
		for (int32 Index = 0; Index < 12; ++Index)
		{
			const float Travel = FMath::Frac(LocalAge * 2.0f + Seed(Index + Layer * 71));
			const float Sign = Index % 2 == 0 ? -1.0f : 1.0f;
			const FVector Position = Crest + Forward * (-25.0f + Travel * 66.0f)
				+ BowUp * Sign * Width * (1.0f - Travel) * (0.6f + Seed(Index) * 0.7f);
			Line(Position, Position - Forward * (3.0f + Travel * 8.0f), Form * FMath::Sin(Travel * UE_PI) * 1.2f);
		}
	}
	// Opening sparks follow the enlarged bow limbs and their attached feather tips.
	if (LastShotAge >= 0.0f && SinceShot < 0.09f)
	{
		const float Release = 1.0f - Ease(0.0f, 0.09f, SinceShot);
		for (int32 Index = 0; Index < (bAscended ? 24 : 16); ++Index)
		{
			const FVector Start = Center + Forward * (25.0f + Seed(Index + 52) * 75.0f + SinceShot * 900.0f)
				+ BowUp * (Seed(Index + 109) - 0.5f) * 26.0f;
			Line(Start, Start + Forward * (28.0f + Seed(Index + 12) * 54.0f), Release * (1.4f + Seed(Index + 19) * 1.4f));
		}
	}
	for (int32 Index = 0; Index < (bAscended ? 144 : 96); ++Index)
	{
		const float Born = 0.04f + Seed(Index + 17) * 0.20f;
		const float LocalAge = Age - Born;
		if (LocalAge <= 0.0f || LocalAge > 0.45f) { continue; }
		const float Sign = Index % 2 == 0 ? -1.0f : 1.0f;
		const float Height = 35.0f + Seed(Index + 79) * 175.0f;
		const FVector Direction = (BowUp * Sign + Forward * (Seed(Index + 41) - 0.4f)).GetSafeNormal();
		const FVector Position = Center + BowUp * Height * Sign + Direction * LocalAge * 70.0f;
		Line(Position, Position - Direction * 4.0f, FMath::Square(1.0f - LocalAge / 0.45f) * 1.6f);
	}
	CoreMaterial->SetScalarParameterValue(TEXT("CoreIntensity"), Envelope * (2.4f + Pulse * 0.5f));
	GlowMaterial->SetScalarParameterValue(TEXT("GlowIntensity"), Envelope * (0.85f + Pulse * 0.15f));
	UploadGeometry();
}

void ASparrowHolyBow::DrawImpact()
{
	const APlayerController* Player = GetWorld()->GetFirstPlayerController();
	if (Player && Player->PlayerCameraManager)
	{
		CameraNormal = (Player->PlayerCameraManager->GetCameraLocation() - Origin).GetSafeNormal();
	}
	const FVector Across = FVector::CrossProduct(CameraNormal, Forward).GetSafeNormal();
	const FVector Along = FVector::CrossProduct(Across, CameraNormal).GetSafeNormal();
	CoreTransforms.Reset(); GlowTransforms.Reset();
	// 두 번의 짧은 시각 방출은 한 번의 실제 접촉에서만 생성하며 추가 피해를 만들지 않는다.
	for (int32 Burst = 0; Burst < 2; ++Burst)
	{
		const float Time = Age - Burst * 0.055f;
		if (Time < 0.0f || Time > 0.24f) { continue; }
		const float Fade = 1.0f - Ease(0.02f, 0.24f, Time);
		const float Scale = ImpactScale * (Burst == 0 ? 1.0f : 0.68f);
		const FVector Center = Origin + Along * Burst * 14.0f * Scale;
		const float Flash = FMath::Exp(-Time * 42.0f);
		Line(Center - Along * 105.0f * Scale, Center + Along * 63.0f * Scale, Flash * 13.0f * Scale);
		Line(Center - Across * 35.0f * Scale, Center + Across * 35.0f * Scale, Flash * 7.0f * Scale);
		for (int32 Index = 0; Index < 36; ++Index)
		{
			const float Angle = Index * UE_TWO_PI / 36.0f + Burst * 0.7f;
			const FVector Ray = (Along * FMath::Cos(Angle) + Across * FMath::Sin(Angle)).GetSafeNormal();
			const float Radius = (8.0f + Time * (180.0f + Seed(Index + 91) * 320.0f)) * Scale;
			const float Length = (5.0f + Seed(Index + 29) * 21.0f) * Fade * Scale;
			Line(Center + Ray * Radius, Center + Ray * (Radius + Length), Fade * (1.1f + Seed(Index + 7) * 1.8f) * Scale);
			if (Index % 6 < 4)
			{
				const float RingRadius = (12.0f + Time * 250.0f) * Scale;
				const FVector Next = Along * FMath::Cos(Angle + 0.15f) + Across * FMath::Sin(Angle + 0.15f);
				Line(Center + Ray * RingRadius, Center + Next * RingRadius, Fade * 1.6f * Scale);
			}
		}
	}
	CoreMaterial->SetScalarParameterValue(TEXT("CoreIntensity"), 4.2f);
	GlowMaterial->SetScalarParameterValue(TEXT("GlowIntensity"), 1.0f);
	UploadGeometry();
}

void ASparrowHolyBow::UploadGeometry()
{
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
	Update(Core, CoreTransforms); Update(Glow, GlowTransforms);
}

void ASparrowHolyBow::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!IsValid(GetOwner()) || GetOwner()->IsActorBeingDestroyed()) { Destroy(); return; }
	Age += DeltaSeconds;
	Draw();
}

void ASparrowHolyBow::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (DesignVisual.IsValid()) { DesignVisual->Destroy(); }
	DesignVisual.Reset();
	Super::EndPlay(EndPlayReason);
}
