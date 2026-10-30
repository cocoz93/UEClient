#include "SparrowEDesignVisual.h"
#include "SparrowHarmonyFX.h"

#include "SparrowArrow.h"
#include "SparrowSkillComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Character.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	void ConfigureEPart(UStaticMeshComponent* Part)
	{
		Part->SetMobility(EComponentMobility::Movable);
		Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Part->SetGenerateOverlapEvents(false);
		Part->SetCanEverAffectNavigation(false);
		Part->SetCastShadow(false);
		Part->SetReceivesDecals(false);
		Part->ComponentTags.AddUnique(TEXT("SparrowSkillFX"));
	}
	UMaterialInterface* ESurface(const TCHAR* Name)
	{
		if (FCString::Strcmp(Name, TEXT("M_CarvedGold")) == 0)
		{ return LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/TopDown/Characters/Sparrow/FX/Harmony20261028/M_BowRelief.M_BowRelief")); }
		const FString Path = FString::Printf(TEXT("/Game/TopDown/Characters/Sparrow/Materials/EDesign20261027/%s.%s"), Name, Name);
		return LoadObject<UMaterialInterface>(nullptr, *Path);
	}
	UStaticMesh* EMesh(const TCHAR* Name)
	{
		if (FCString::Strcmp(Name, TEXT("SM_ReferenceBow")) == 0)
		{ return LoadObject<UStaticMesh>(nullptr, TEXT("/Game/TopDown/Characters/Sparrow/FX/Harmony20261028/SM_ReferenceBow.SM_ReferenceBow")); }
		const FString Path = FString::Printf(TEXT("/Game/TopDown/Characters/Sparrow/FX/EDesign20261027/%s.%s"), Name, Name);
		return LoadObject<UStaticMesh>(nullptr, *Path);
	}
	void UploadELines(UInstancedStaticMeshComponent* Part, const TArray<FTransform>& Lines)
	{
		if (Part->GetInstanceCount() == Lines.Num())
		{
			if (!Lines.IsEmpty()) { Part->BatchUpdateInstancesTransforms(0, Lines, true, true, true); }
		}
		else
		{
			Part->ClearInstances();
			if (!Lines.IsEmpty()) { Part->AddInstances(Lines, false, true); }
		}
	}
	float ESeed(int32 Index) { return FMath::Frac(FMath::Abs(FMath::Sin(Index * 97.31f + 13.72f) * 43758.54f)); }
}

ASparrowEDesignVisual::ASparrowEDesignVisual()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false;
	SetActorEnableCollision(false);
	SetCanBeDamaged(false);
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
	Strands = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("DesignStrands"));
	Strands->SetupAttachment(GetRootComponent());
	ConfigureEPart(Strands);
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Plane(TEXT("/Engine/BasicShapes/Plane.Plane"));
	Strands->SetStaticMesh(Plane.Object);
	Tags.Add(TEXT("SparrowEDesignVisual"));
}

bool ASparrowEDesignVisual::Initialize(const FVector& Direction, int32 InStyle, bool bInImpact, bool bWorld)
{
	if (!IsValid(GetOwner()) || Direction.IsNearlyZero() || InStyle < 1 || InStyle > 8) { Destroy(); return false; }
	Style = InStyle;
	bImpact = bInImpact;
	Forward = Direction.GetSafeNormal();
	Origin = GetActorLocation();
	OwnerStart = GetOwner()->GetActorLocation();
	if (Style >= 7 && !bImpact)
	{
		if (const ACharacter* Character = Cast<ACharacter>(GetOwner()))
		{
			BowMesh = Character->GetMesh();
			if (BowMesh.IsValid()) { AddTickPrerequisiteComponent(BowMesh.Get()); }
		}
		// The horizontal shooting pose and its FX share world up. Camera-facing
		// limbs can tilt below the floor even when their grip is at the hand.
		Forward = Direction.GetSafeNormal2D();
		if (Forward.IsNearlyZero()) { Forward = GetOwner()->GetActorForwardVector().GetSafeNormal2D(); }
	}
	const USparrowSkillComponent* Skills = GetOwner()->FindComponentByClass<USparrowSkillComponent>();
	bAscended = Skills && Skills->GetAscensionRemaining() > 0.0f;
	ImpactScale = (bWorld ? .55f : 1.0f) * (Style >= 3 && Style <= 5 ? .58f : 1.0f);
	UMaterialInterface* Strand = ESurface(Style == 8 ? TEXT("M_E8Strand") : Style == 7 ? TEXT("M_E7Strand") : TEXT("M_EStrand"));
	if (!Strand) { Destroy(); return false; }
	StrandMaterial = UMaterialInstanceDynamic::Create(Strand, this);
	Strands->SetMaterial(0, StrandMaterial);
	Strands->ComponentTags.AddUnique(TEXT("SparrowEDesignStrands"));
	Tags.AddUnique(*FString::Printf(TEXT("SparrowEDesign%d"), Style));
	if (bImpact) { Tags.AddUnique(TEXT("SparrowEDesignContact")); }
	const auto AddPart = [this](const TCHAR* MeshName, const TCHAR* SurfaceName, const TCHAR* Tag, int32 Index)
	{
		UStaticMesh* Mesh = EMesh(MeshName);
		UMaterialInterface* Surface = ESurface(SurfaceName);
		if (!Mesh || !Surface) { return false; }
		UStaticMeshComponent* Part = NewObject<UStaticMeshComponent>(this);
		ConfigureEPart(Part);
		Part->SetupAttachment(GetRootComponent());
		Part->SetStaticMesh(Mesh);
		Part->ComponentTags.AddUnique(Tag);
		UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(Surface, this);
		Material->SetScalarParameterValue(TEXT("Index"), static_cast<float>(Index));
		Material->SetScalarParameterValue(TEXT("Ascended"), bAscended ? 1.0f : 0.0f);
		Part->SetMaterial(0, Material);
		AddInstanceComponent(Part); Part->RegisterComponent();
		Parts.Add(Part); Materials.Add(Material);
		return true;
	};
	if (bImpact && Style == 6)
	{
		for (int32 Layer = 0; Layer < 3; ++Layer)
		{
			if (!AddPart(TEXT("SM_EHeliosContact"), TEXT("M_EHeliosFire"), TEXT("EHeliosContact"), Layer)) { Destroy(); return false; }
		}
	}
	else if (bImpact && Style >= 7)
	{
		for (int32 Layer = 0; Layer < 2; ++Layer)
		{
			if (!AddPart(TEXT("SM_ESweep"), TEXT("M_ESweep"), TEXT("ERegaliaContactFlow"), Layer)) { Destroy(); return false; }
		}
	}
	if (!bImpact)
	{
		if (Style >= 7)
		{
			if (!AddPart(Style == 8 ? TEXT("SM_ReferenceBow") : TEXT("SM_ERegaliaBow"),
				Style == 8 ? TEXT("M_CarvedGold") : TEXT("M_ERegaliaBow"), TEXT("ERegaliaBow"), 0)) { Destroy(); return false; }
			if (Style == 8 && !AddPart(TEXT("SM_EFeatherBow"), TEXT("M_EFeatherBow"), TEXT("ERegaliaSeal"), 0)) { Destroy(); return false; }
			for (int32 Side = 0; Side < 2; ++Side)
			{
				if (!AddPart(TEXT("SM_ESweep"), TEXT("M_ESweep"), TEXT("ERegaliaReleaseFlow"), Side)) { Destroy(); return false; }
			}
		}
		else if (Style == 6)
		{
			for (int32 Side = 0; Side < 2; ++Side)
			{
				if (!AddPart(TEXT("SM_EHeliosLimb"), TEXT("M_EHeliosLimb"), TEXT("EHeliosLimb"), Side) ||
					!AddPart(TEXT("SM_EHeliosFire"), TEXT("M_EHeliosFire"), TEXT("EHeliosFire"), Side) ||
					!AddPart(TEXT("SM_EHeliosInlay"), TEXT("M_EHeliosInlay"), TEXT("EHeliosInlay"), Side)) { Destroy(); return false; }
			}
		}
		else if (Style == 1)
		{
			if (!AddPart(TEXT("SM_ERecurveFrame"), TEXT("M_ERecurveFrame"), TEXT("ERecurveFrame"), 0) ||
				!AddPart(TEXT("SM_ERecurveSails"), TEXT("M_ERecurveSails"), TEXT("ERecurveSails"), 0) ||
				!AddPart(TEXT("SM_ERecurveCrests"), TEXT("M_ERecurveCrests"), TEXT("ERecurveCrests"), 0)) { Destroy(); return false; }
		}
		for (int32 Side = 0; Style != 1 && Style != 6 && Style < 7 && Side < 2; ++Side)
		{
			if (!AddPart(TEXT("SM_ELimb"), TEXT("M_ELimb"), TEXT("EConceptLimb"), Side)) { Destroy(); return false; }
		}
		if (Style == 2)
		{
			for (int32 Layer = 0; Layer < 3; ++Layer)
			{
				if (!AddPart(TEXT("SM_ESweep"), TEXT("M_ESweep"), TEXT("EConceptSweep"), Layer)) { Destroy(); return false; }
			}
		}
	}
	SetLifeSpan(bImpact ? .34f : 2.0f);
	SetActorTickEnabled(true);
	Draw();
	return true;
}

void ASparrowEDesignVisual::NotifyShot() { if (ShotAt < 0.0f) { ShotAt = Age; } }
void ASparrowEDesignVisual::FadeOut() { if (FadeAt < 0.0f) { FadeAt = Age; SetLifeSpan(.28f); } }

void ASparrowEDesignVisual::Line(const FVector& A, const FVector& B, float Width)
{
	const FVector Delta = B - A;
	if (Delta.SizeSquared() < .01f || Width < .04f) { return; }
	Lines.Emplace(FRotationMatrix::MakeFromXZ(Delta.GetSafeNormal(), Normal).Rotator(), (A + B) * .5f,
		FVector(Delta.Size() / 100.0f, Width / 100.0f, 1.0f));
}

void ASparrowEDesignVisual::Draw()
{
	if (Style >= 7) { DrawRegalia(); return; }
	const FVector Center = bImpact ? Origin : Origin + GetOwner()->GetActorLocation() - OwnerStart;
	const APlayerController* PC = GetWorld()->GetFirstPlayerController();
	Normal = PC && PC->PlayerCameraManager ? (PC->PlayerCameraManager->GetCameraLocation() - Center).GetSafeNormal() : FVector::UpVector;
	const FRotator Facing = FRotationMatrix::MakeFromXZ(Forward, Normal).Rotator();
	if (Style == 6) { DrawHelios(Center, Facing); return; }
	const FVector Across = FRotationMatrix(Facing).GetUnitAxis(EAxis::Y);
	const float SinceShot = ShotAt < 0.0f ? -1.0f : Age - ShotAt;
	const float Open = FMath::SmoothStep(.01f, .26f, Age);
	const float ReleaseFade = ShotAt < 0.0f ? 1.0f : 1.0f - FMath::SmoothStep(.05f, .25f, SinceShot);
	const float Fade = FadeAt < 0.0f ? 1.0f : 1.0f - FMath::SmoothStep(.04f, .28f, Age - FadeAt);
	const float Pulse = SinceShot < 0.0f ? 0.0f : FMath::Exp(-SinceShot * 28.0f);
	int32 LimbSide = 0, FeatherSide = 0, SweepLayer = 0;
	for (int32 Index = 0; Index < Parts.Num(); ++Index)
	{
		UStaticMeshComponent* Part = Parts[Index];
		UMaterialInstanceDynamic* Material = Materials[Index];
		Material->SetScalarParameterValue(TEXT("Age"), Age);
		Material->SetScalarParameterValue(TEXT("Open"), Open);
		Material->SetScalarParameterValue(TEXT("Pulse"), Pulse);
		Material->SetScalarParameterValue(TEXT("Envelope"), ReleaseFade * Fade);
		if (Style == 1)
		{
			const float Recoil = SinceShot < 0.0f ? 0.0f : FMath::Sin(FMath::Clamp(SinceShot / .12f, 0.0f, 1.0f) * UE_PI) * 14.0f;
			const bool bSail = Part->ComponentTags.Contains(TEXT("ERecurveSails"));
			const float Reveal = FMath::SmoothStep(bSail ? .065f : .01f, bSail ? .29f : .22f, Age);
			Part->SetWorldLocation(Center + Forward * (12.0f - Recoil));
			Part->SetWorldRotation(Facing);
			Part->SetWorldScale3D(FVector(1.0f, FMath::Lerp(.12f, 1.0f, Reveal), FMath::Lerp(.35f, 1.0f, Reveal)));
			Material->SetScalarParameterValue(TEXT("Envelope"), ReleaseFade * Fade * Reveal);
		}
		else if (Part->ComponentTags.Contains(TEXT("EConceptSweep")))
		{
			const float Local = SinceShot - SweepLayer * .018f;
			const bool bActive = SinceShot >= 0.0f && Local >= 0.0f && Local < .22f;
			Part->SetVisibility(bActive);
			static const FVector SweepScales[] = {FVector(1.0f, 1.0f, 1.0f), FVector(.85f, 1.22f, 1.0f), FVector(.76f, .88f, 1.0f)};
			static const float SweepYaw[] = {-5.0f, 10.0f, -21.0f};
			static const float SweepHeight[] = {0.0f, 26.0f, -22.0f};
			const float Turn = SweepYaw[SweepLayer] + FMath::Lerp(0.0f, 17.0f, FMath::Clamp(Local / .12f, 0.0f, 1.0f));
			Part->SetWorldLocation(Center + FVector::UpVector * SweepHeight[SweepLayer]);
			Part->SetWorldRotation(FRotator(0.0f, Forward.Rotation().Yaw + Turn, SweepLayer * 3.0f));
			Part->SetWorldScale3D(SweepScales[SweepLayer]);
			Material->SetScalarParameterValue(TEXT("Open"), .8f + .2f * FMath::SmoothStep(0.0f, .06f, Local));
			Material->SetScalarParameterValue(TEXT("Envelope"), bActive ? (1.0f - FMath::SmoothStep(.04f, .22f, Local)) * Fade : 0.0f);
			++SweepLayer;
		}
		else
		{
			const bool bFeather = Part->ComponentTags.Contains(TEXT("EConceptFeathers"));
			const float Sign = (bFeather ? FeatherSide++ : LimbSide++) == 0 ? 1.0f : -1.0f;
			const float Size = Style == 1 ? 1.18f : .47f;
			const FQuat LocalTilt(FVector::ForwardVector, FMath::DegreesToRadians(bFeather ? Sign * (1.0f - Open) * 15.0f : 0.0f));
			Part->SetWorldLocation(Center + Forward * 10.0f);
			Part->SetWorldRotation(Facing.Quaternion() * LocalTilt);
			Part->SetWorldScale3D(FVector(Size, Sign * Size * FMath::Lerp(.18f, 1.0f, Open), Size));
		}
	}
	Lines.Reset();
	if (!bImpact)
	{
		const float BowSize = Style == 1 ? 1.34f : .47f;
		const float DrawBack = ShotAt < 0.0f ? 48.0f * FMath::SmoothStep(.05f, .33f, Age) : 8.0f * FMath::Exp(-SinceShot * 30.0f);
		const FVector Nock = Center - Forward * DrawBack;
		for (float Sign : {-1.0f, 1.0f})
		{
			const FVector Tip = Style == 1 ? Center + Forward * 20.0f + Across * (Sign > 0.0f ? 196.0f : -179.0f) * Open :
				Center + Forward * (-25.0f * BowSize) + Across * (146.0f * BowSize * Sign * Open);
			Line(Tip, Nock, (Style == 1 ? 1.5f : 1.05f) * ReleaseFade * Fade);
		}
		if (Style == 1 && ShotAt < 0.0f)
		{
			// 전방 파문은 얇은 열린 초승달 세 개. 본체 활보다 작고 중심축을 가리지 않는다.
			for (int32 Wave = 0; Wave < 3; ++Wave)
			{
				const float WaveAge = Age - .12f - Wave * .04f;
				if (WaveAge <= 0.0f) { continue; }
				const float Radius = (44.0f - Wave * 8.0f) * FMath::SmoothStep(0.0f, .08f, WaveAge);
				const FVector WaveCenter = Center + Forward * (65.0f + Wave * 42.0f);
				for (int32 Step = 0; Step < 14; ++Step)
				{
					const auto Point = [&](float T) { const float A = FMath::Lerp(-1.10f, 1.10f, T); return WaveCenter - Forward * FMath::Cos(A) * Radius * .34f + Across * FMath::Sin(A) * Radius; };
					Line(Point(Step / 14.0f), Point((Step + 1) / 14.0f), 1.15f + FMath::Sin(Step * UE_PI / 14.0f) * 1.4f);
				}
			}
		}
		const int32 Seeds = Style == 1 ? 42 : 22;
		for (int32 Index = 0; Index < Seeds; ++Index)
		{
			const float Local = Age - .03f - ESeed(Index) * .18f;
			if (Local < 0.0f || Local > .52f) { continue; }
			const float Sign = Index % 2 ? 1.0f : -1.0f;
			const FVector Base = Center + Across * Sign * (25.0f + ESeed(Index + 9) * 120.0f) * BowSize * Open;
			const FVector Drift = (-Forward * (.4f + ESeed(Index + 4)) + Across * Sign * .4f).GetSafeNormal();
			const FVector Point = Base + Drift * Local * 130.0f;
			Line(Point, Point - Drift * (3.0f + ESeed(Index + 7) * 7.0f), (1.0f - Local / .52f) * 1.8f * Fade);
		}
	}
	else
	{
		const float Life = 1.0f - FMath::SmoothStep(.025f, .30f, Age);
		if (Style == 2)
		{
			for (int32 Slash = 0; Slash < 3; ++Slash)
			{
				const float Local = Age - Slash * .035f;
				if (Local < 0.0f || Local > .22f) { continue; }
				const FVector Offset = Across * (Slash - 1) * 17.0f;
				const float Length = (105.0f - Slash * 12.0f) * ImpactScale;
				Line(Center + Offset - Forward * Length, Center + Offset + Forward * Length, (1.0f - Local / .22f) * 5.8f);
			}
		}
		for (int32 Index = 0; Index < (Style >= 3 ? 20 : 48); ++Index)
		{
			const float A = ESeed(Index + 14) * UE_TWO_PI;
			const FVector Ray = (Forward * FMath::Cos(A) + Across * FMath::Sin(A) * .65f).GetSafeNormal();
			const float Radius = Age * (180.0f + ESeed(Index) * 440.0f) * ImpactScale;
			Line(Center + Ray * Radius, Center + Ray * (Radius + (10.0f + ESeed(Index + 2) * 30.0f) * Life * ImpactScale), Life * (1.2f + ESeed(Index + 7) * 2.0f) * ImpactScale);
		}
	}
	StrandMaterial->SetScalarParameterValue(TEXT("Envelope"), bImpact ? 1.0f : Fade);
	StrandMaterial->SetScalarParameterValue(TEXT("Age"), Age);
	UploadELines(Strands, Lines);
}

void ASparrowEDesignVisual::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!IsValid(GetOwner()) || GetOwner()->IsActorBeingDestroyed()) { Destroy(); return; }
	Age += FMath::Max(0.0f, DeltaSeconds); Draw();
}

void ASparrowEDesignVisual::DrawHelios(const FVector& Center, const FRotator& Facing)
{
	const FVector Across = FRotationMatrix(Facing).GetUnitAxis(EAxis::Y);
	const float Open = FMath::SmoothStep(.005f, .25f, Age);
	const float SinceShot = ShotAt < 0.0f ? -1.0f : Age - ShotAt;
	const float Released = SinceShot < 0.0f ? 0.0f : FMath::SmoothStep(0.0f, .055f, SinceShot);
	const float Fade = FadeAt < 0.0f ? 1.0f : 1.0f - FMath::SmoothStep(.03f, .28f, Age - FadeAt);
	const float ReleaseFade = SinceShot < 0.0f ? 1.0f : 1.0f - FMath::SmoothStep(.065f, .255f, SinceShot);
	const float Pulse = SinceShot < 0.0f ? 0.0f : FMath::Exp(-SinceShot * 23.0f);
	Lines.Reset();
	for (int32 Index = 0; Index < Parts.Num(); ++Index)
	{
		UStaticMeshComponent* Part = Parts[Index];
		UMaterialInstanceDynamic* Material = Materials[Index];
		Material->SetScalarParameterValue(TEXT("Age"), Age);
		Material->SetScalarParameterValue(TEXT("Open"), Open);
		Material->SetScalarParameterValue(TEXT("Pulse"), Pulse);
		if (bImpact)
		{
			// Three expanding curved tongues begin at the actual contact, not
			// before the projectile arrives. Delayed fine strokes form the second beat.
			const float Local = Age - Index * .036f;
			const float Bloom = FMath::SmoothStep(0.0f, .065f, Local);
			const float Life = Local < 0.0f ? 0.0f : 1.0f - FMath::SmoothStep(.035f, .24f, Local);
			const FQuat Turn(Forward, FMath::DegreesToRadians(Index * 121.0f + 18.0f));
			Part->SetWorldLocation(Center + Forward * FMath::Max(0.0f, Local) * 85.0f);
			Part->SetWorldRotation(Turn * Facing.Quaternion());
			Part->SetWorldScale3D(FVector(ImpactScale * (.32f + Bloom * .78f)));
			Material->SetScalarParameterValue(TEXT("Open"), 1.0f);
			Material->SetScalarParameterValue(TEXT("Envelope"), Life);
			continue;
		}
		const float Side = Index < 3 ? -1.0f : 1.0f;
		const bool bFire = Part->ComponentTags.Contains(TEXT("EHeliosFire"));
		const float Draw = FMath::SmoothStep(.09f, .34f, Age) * (1.0f - Released);
		const float Swing = Side * ((1.0f - Open) * -43.0f + Draw * 8.0f - Pulse * 6.0f);
		const FQuat Hinge(Normal, FMath::DegreesToRadians(Swing));
		Part->SetWorldLocation(Center + Forward * (11.0f - Draw * 7.0f - Pulse * 10.0f));
		Part->SetWorldRotation(Hinge * Facing.Quaternion());
		Part->SetWorldScale3D(FVector(1.0f, Side, 1.0f) * (bAscended ? 1.08f : 1.0f));
		Material->SetScalarParameterValue(TEXT("Envelope"), Fade * ReleaseFade * (bFire ? FMath::SmoothStep(.05f, .19f, Age) : Open));
	}
	if (!bImpact)
	{
		const float Draw = FMath::SmoothStep(.09f, .34f, Age) * (1.0f - Released);
		const FVector Nock = Center - Forward * (16.0f + Draw * 64.0f);
		for (float Side : {-1.0f, 1.0f})
		{
			const float Swing = Side * ((1.0f - Open) * -43.0f + Draw * 8.0f - Pulse * 6.0f);
			const FQuat Hinge(Normal, FMath::DegreesToRadians(Swing));
			const FVector Tip = Center + Forward * (11.0f - Draw * 7.0f - Pulse * 10.0f)
				+ Hinge.RotateVector((-Forward * 15.0f + Across * Side * 207.0f) * (bAscended ? 1.08f : 1.0f));
			Line(Nock, Tip, 3.2f * Open * ReleaseFade);
			// Layered currents travel along the physical limbs and converge into
			// the nock. The space in front stays open until the single release.
			for (int32 Streak = 0; Streak < 12; ++Streak)
			{
				const float T = FMath::Frac(Age * 1.8f + Streak / 12.0f);
				const float Next = FMath::Min(1.0f, T + .055f);
				const FVector Root = Center - Forward * 12.0f + Across * Side * (65.0f + Streak * 11.0f);
				const FVector A = FMath::Lerp(Root, Nock, T) + Forward * FMath::Sin(T * UE_PI) * 32.0f;
				const FVector B = FMath::Lerp(Root, Nock, Next) + Forward * FMath::Sin(Next * UE_PI) * 32.0f;
				Line(A, B, FMath::Sin(T * UE_PI) * 1.9f * Open * ReleaseFade);
			}
		}
		if (SinceShot < 0.0f)
		{
			const float Charge = FMath::SmoothStep(.08f, .29f, Age);
			const FVector Tip = Center + Forward * 108.0f;
			Line(Nock, Tip, Charge * 3.8f);
			Line(Tip, Tip - Forward * 28.0f + Across * 12.0f, Charge * 2.8f);
			Line(Tip, Tip - Forward * 28.0f - Across * 12.0f, Charge * 2.8f);
		}
		if (SinceShot >= 0.0f && SinceShot < .13f)
		{
			for (int32 Ray = 0; Ray < 18; ++Ray)
			{
				const float Side = (ESeed(Ray) - .5f) * 64.0f;
				const FVector Start = Center + Across * Side + Forward * (SinceShot * 1450.0f + ESeed(Ray + 41) * 60.0f);
				Line(Start, Start + Forward * (50.0f + ESeed(Ray + 3) * 65.0f), (1.0f - SinceShot / .13f) * 2.4f);
			}
		}
	}
	else
	{
		for (int32 Beat = 0; Beat < 2; ++Beat)
		{
			const float Local = Age - Beat * .055f;
			if (Local < 0.0f || Local > .21f) { continue; }
			const float Life = 1.0f - Local / .21f;
			for (int32 Ray = 0; Ray < 32; ++Ray)
			{
				const float Angle = ESeed(Ray + Beat * 67) * UE_TWO_PI;
				const FVector Out = (Forward * FMath::Cos(Angle) + Across * FMath::Sin(Angle)).GetSafeNormal();
				const FVector A = Center + Out * Local * (140.0f + ESeed(Ray + 22) * 440.0f) * ImpactScale;
				Line(A, A + Out * (8.0f + ESeed(Ray + 9) * 24.0f) * Life * ImpactScale, Life * 2.3f * ImpactScale);
			}
		}
	}
	StrandMaterial->SetScalarParameterValue(TEXT("Envelope"), Fade);
	StrandMaterial->SetScalarParameterValue(TEXT("Age"), Age);
	UploadELines(Strands, Lines);
}

void ASparrowEDesignVisual::DrawRegalia()
{
	FVector Center = Origin;
	if (!bImpact)
	{
		Center += GetOwner()->GetActorLocation() - OwnerStart;
		if (BowMesh.IsValid())
		{
			static const FName Anchor(TEXT("arrow_anchor"));
			static const FName Emitter(TEXT("BowEmitterSocket"));
			if (BowMesh->DoesSocketExist(Anchor)) { Center = BowMesh->GetSocketLocation(Anchor); }
			else if (BowMesh->DoesSocketExist(Emitter)) { Center = BowMesh->GetSocketLocation(Emitter); }
		}
		Center += FVector::UpVector * 6.0f;
	}
	Normal = FVector::UpVector;
	const FVector Horizontal = Forward.GetSafeNormal2D();
	const FVector Axis = Horizontal.IsNearlyZero() ? FVector::ForwardVector : Horizontal;
	const FVector Across = FVector::CrossProduct(Normal, Axis).GetSafeNormal();
	const FRotator Facing = FRotationMatrix::MakeFromXZ(Axis, Normal).Rotator();
	const float SinceShot = ShotAt < 0.0f ? -1.0f : Age - ShotAt;
	const float Open = FMath::SmoothStep(.015f, .255f, Age);
	const float Release = SinceShot < 0.0f ? 0.0f : FMath::SmoothStep(0.0f, .045f, SinceShot);
	const float Pulse = SinceShot < 0.0f ? 0.0f : FMath::Exp(-SinceShot * 24.0f);
	const float Draw = FMath::SmoothStep(.075f, .32f, Age) * (1.0f - Release);
	const float Fade = FadeAt < 0.0f ? 1.0f : 1.0f - FMath::SmoothStep(.0f, .22f, Age - FadeAt);
	const float ReleaseFade = SinceShot < 0.0f ? 1.0f : 1.0f - FMath::SmoothStep(.055f, .235f, SinceShot);
	const float Form = bAscended ? 1.08f : 1.0f;
	const FVector Scale((.96f + Open * .04f - Draw * .035f + Pulse * .05f) * Form,
		(.92f + Open * .08f) * Form, 1.0f);
	const FVector Grip = Center - Axis * (Draw * 6.0f + Pulse * 8.0f);
	Lines.Reset();
	int32 FlowIndex = 0;
	for (int32 Index = 0; Index < Parts.Num(); ++Index)
	{
		const bool bReleaseFlow = Parts[Index]->ComponentTags.Contains(TEXT("ERegaliaReleaseFlow"));
		const bool bContactFlow = Parts[Index]->ComponentTags.Contains(TEXT("ERegaliaContactFlow"));
		if (bReleaseFlow || bContactFlow)
		{
			const float Sign = FlowIndex % 2 == 0 ? 1.0f : -1.0f;
			const float Local = bContactFlow ? Age - FlowIndex * .035f : SinceShot;
			const float Duration = bContactFlow ? .20f : .145f;
			const float Growth = FMath::SmoothStep(0.0f, bContactFlow ? .055f : .045f, Local);
			const float Life = Local < 0.0f ? 0.0f : 1.0f - FMath::SmoothStep(bContactFlow ? .06f : .035f, Duration, Local);
			const float Sizing = bContactFlow ? ImpactScale : Form;
			const FQuat Turn(Axis, FMath::DegreesToRadians(Sign * (bContactFlow ? -52.0f : -22.0f)));
			const FVector Position = bContactFlow ? Center + Normal * 12.0f + Axis * FMath::Max(0.0f, Local) * 110.0f :
				Grip + Axis * (24.0f + FMath::Max(0.0f, Local) * 720.0f);
			Parts[Index]->SetVisibility(Local >= 0.0f && Local < Duration);
			Parts[Index]->SetWorldLocation(Position);
			Parts[Index]->SetWorldRotation(Turn * Facing.Quaternion());
			Parts[Index]->SetWorldScale3D(FVector((bContactFlow ? .16f + Growth * .16f : .17f + Growth * .21f) * Sizing,
				Sign * (bContactFlow ? .20f : .15f) * Sizing * FMath::Lerp(.55f, 1.0f, Growth), .30f * Sizing));
			Materials[Index]->SetScalarParameterValue(TEXT("Age"), FMath::Max(0.0f, Local));
			Materials[Index]->SetScalarParameterValue(TEXT("Open"), 1.0f);
			Materials[Index]->SetScalarParameterValue(TEXT("Envelope"), Life * (bContactFlow ? 1.0f : .84f) * Fade);
			++FlowIndex;
			continue;
		}
		const bool bSeal = Parts[Index]->ComponentTags.Contains(TEXT("ERegaliaSeal"));
		const float SealFade = SinceShot < 0.0f ? 1.0f : 1.0f - FMath::SmoothStep(.015f, .12f, SinceShot);
		Parts[Index]->SetWorldLocation(bSeal ? Grip + Normal * 3.0f - Axis * 7.0f : Grip);
		Parts[Index]->SetWorldRotation(Facing);
		Parts[Index]->SetWorldScale3D(bSeal ? FVector(.48f * Form, .48f * Form, 1.0f) : Scale);
		Materials[Index]->SetScalarParameterValue(TEXT("Age"), Age);
		Materials[Index]->SetScalarParameterValue(TEXT("Open"), Open);
		Materials[Index]->SetScalarParameterValue(TEXT("Pulse"), Pulse);
		Materials[Index]->SetScalarParameterValue(TEXT("Draw"), Draw);
		Materials[Index]->SetScalarParameterValue(TEXT("Envelope"), (bSeal ? SealFade * .82f : ReleaseFade) * Fade);
	}
	if (!bImpact)
	{
		// Image coordinates: grip (.5,.585), attached tips (.091/.909,.189).
		// The single authored silhouette lies in XY; the string meets those
		// same tips instead of introducing a second unrelated procedural bow.
		// E8 corrects the E7 image direction: grip (.5,.735), tips
		// (.073/.927,.035). Both tips are behind the grip; the drawn string
		// sits farther behind them while the one actual arrow flies along +X.
		const bool bFeatherBow = Style == 8;
		const FVector Nock = Grip - Axis * ((bFeatherBow ? 122.0f + Draw * 44.0f : 24.0f + Draw * 64.0f) * Form);
		for (float Sign : {-1.0f, 1.0f})
		{
			const FVector Tip = Grip + Axis * ((bFeatherBow ? -109.9636f : 105.60f) * Scale.X)
				+ Across * (Sign * (bFeatherBow ? 204.96f : 196.32f) * Scale.Y);
			Line(Nock, Tip, 1.9f * Open * ReleaseFade);
			if (ShotAt < 0.0f)
			{
				// Only a few pinpricks trace the carved limbs. The generated
				// surface, including its dark inset detail, remains the hero.
				for (int32 Glint = 0; Glint < 5; ++Glint)
				{
					const float T = FMath::Frac(Age * 1.4f + Glint / 5.0f);
					const float Spine = bFeatherBow ? -109.96f * FMath::Pow(T, 1.8f) :
						T * T * 106.0f + FMath::Sin(T * UE_PI) * 23.0f;
					const FVector P = Grip + Across * (Sign * T * (bFeatherBow ? 204.96f : 196.0f) * Form)
						+ Axis * (Spine * Form) + Normal * 2.0f;
					Line(P - Across * Sign * 2.5f, P + Across * Sign * 2.5f,
						1.6f * FMath::Sin(T * UE_PI) * Open);
				}
			}
		}
		if (bFeatherBow)
		{
			const float SealFade = SinceShot < 0.0f ? 1.0f : 1.0f - FMath::SmoothStep(.015f, .12f, SinceShot);
			const float SealPower = Open * SealFade;
			for (float Sign : {-1.0f, 1.0f})
			{
				const FVector Shoulder = Grip + Across * Sign * 24.0f - Axis * 31.0f;
				Line(Grip, Shoulder, 4.0f * SealPower);
				Line(Shoulder, Grip - Axis * 57.0f, 3.0f * SealPower);
			}
		}
		if (ShotAt < 0.0f && !bFeatherBow)
		{
			const float Charge = FMath::SmoothStep(.10f, .30f, Age);
			const FVector Tip = Grip + Axis * 136.0f * Form;
			Line(Nock, Tip, 2.9f * Charge);
			Line(Tip, Tip - Axis * 25.0f * Form + Across * 8.5f * Form, 2.1f * Charge);
			Line(Tip, Tip - Axis * 25.0f * Form - Across * 8.5f * Form, 2.1f * Charge);
		}
		else if (SinceShot >= 0.0f && SinceShot < .12f)
		{
			const float Life = 1.0f - SinceShot / .12f;
			for (int32 Spark = 0; Spark < 10; ++Spark)
			{
				const float Offset = (ESeed(Spark + 16) - .5f) * 43.0f;
				const FVector P = Grip + Across * Offset + Axis * (34.0f + SinceShot * (900.0f + ESeed(Spark) * 480.0f));
				Line(P, P + Axis * (14.0f + ESeed(Spark + 3) * 28.0f) * Life, 1.7f * Life);
			}
		}
	}
	else
	{
		// Two brief directional contact beats. No circular disk or broad
		// screen-covering flash is introduced at the single real hit.
		for (int32 Beat = 0; Beat < 2; ++Beat)
		{
			const float Local = Age - Beat * .047f;
			if (Local < 0.0f || Local > .18f) { continue; }
			const float Life = 1.0f - Local / .18f;
			const float Stretch = FMath::SmoothStep(0.0f, .028f, Local);
			Line(Center - Axis * (32.0f * Stretch * ImpactScale),
				Center + Axis * ((78.0f - Beat * 19.0f) * Stretch * ImpactScale), Life * 5.0f * ImpactScale);
			for (int32 Spark = 0; Spark < 18; ++Spark)
			{
				const float Sign = Spark % 2 ? 1.0f : -1.0f;
				const FVector Direction = (Axis * (.4f + ESeed(Spark + 3)) + Across * Sign * (.25f + ESeed(Spark + 44))
					+ Normal * (.12f + ESeed(Spark + 29) * .45f)).GetSafeNormal();
				const FVector P = Center + Direction * Local * (130.0f + ESeed(Spark + 71) * 330.0f) * ImpactScale;
				Line(P, P + Direction * (7.0f + ESeed(Spark + 2) * 20.0f) * Life * ImpactScale, Life * 2.0f * ImpactScale);
			}
		}
	}
	StrandMaterial->SetScalarParameterValue(TEXT("Envelope"), Fade);
	StrandMaterial->SetScalarParameterValue(TEXT("Age"), Age);
	UploadELines(Strands, Lines);
}

ASparrowEDesignTrail::ASparrowEDesignTrail()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false;
	SetActorEnableCollision(false); SetCanBeDamaged(false);
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
	Strands = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("ActualFlightWake"));
	Strands->SetupAttachment(GetRootComponent()); ConfigureEPart(Strands);
	Strands->NumCustomDataFloats = 2;
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Plane(TEXT("/Engine/BasicShapes/Plane.Plane"));
	Strands->SetStaticMesh(Plane.Object);
	Tags.Add(TEXT("SparrowEDesignActualTrail"));
}

bool ASparrowEDesignTrail::Initialize(ASparrowArrow* Arrow, int32 InStyle)
{
	UMaterialInterface* Surface = ESurface(InStyle == 8 ? TEXT("M_E8Trail") : InStyle == 7 ? TEXT("M_E7Trail") : InStyle == 6 ? TEXT("M_E6Trail") : InStyle == 4 ? TEXT("M_E4Trail") : InStyle == 5 ? TEXT("M_E5Trail") : TEXT("M_EStrand"));
	if (!IsValid(Arrow) || !Surface) { Destroy(); return false; }
	SourceArrow = Arrow; Style = InStyle;
	Material = UMaterialInstanceDynamic::Create(Surface, this); Strands->SetMaterial(0, Material);
	Material->SetScalarParameterValue(TEXT("Trail"), 1.0f);
	Material->SetScalarParameterValue(TEXT("TrailMode"), Style >= 3 ? 1.0f : 0.0f);
	Positions.Add(Arrow->GetActorLocation()); Times.Add(0.0f); Distances.Add(Arrow->GetDistanceTravelled());
	SetLifeSpan(3.0f); SetActorTickEnabled(true);
	return true;
}

void ASparrowEDesignTrail::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!IsValid(GetOwner()) || GetOwner()->IsActorBeingDestroyed()) { Destroy(); return; }
	Age += FMath::Max(0.0f, DeltaSeconds);
	if (SourceArrow.IsValid() && !SourceArrow->IsActorBeingDestroyed())
	{
		Positions.Add(SourceArrow->GetActorLocation()); Times.Add(Age); Distances.Add(SourceArrow->GetDistanceTravelled());
	}
	else if (EndAt < 0.0f) { EndAt = Age; }
	if (EndAt >= 0.0f && Age - EndAt >= .16f) { Destroy(); return; }
	const float WakeDuration = Style >= 7 ? .09f : .24f;
	while (Times.Num() > 2 && Age - Times[1] > WakeDuration)
	{
		Positions.RemoveAt(0, 1, EAllowShrinking::No); Times.RemoveAt(0, 1, EAllowShrinking::No); Distances.RemoveAt(0, 1, EAllowShrinking::No);
	}
	const APlayerController* PC = GetWorld()->GetFirstPlayerController();
	const FVector Camera = PC && PC->PlayerCameraManager ? PC->PlayerCameraManager->GetCameraLocation() : GetActorLocation() + FVector::UpVector * 1000.0f;
	Lines.Reset(); SegmentData.Reset();
	for (int32 Index = 1; Index < Positions.Num(); ++Index)
	{
		const FVector Delta = Positions[Index] - Positions[Index - 1];
		if (Delta.SizeSquared() < .01f) { continue; }
		const FVector Center = (Positions[Index] + Positions[Index - 1]) * .5f;
		const FVector Normal = (Camera - Center).GetSafeNormal();
		const FVector Across = FVector::CrossProduct(Normal, Delta.GetSafeNormal()).GetSafeNormal();
		const float Fade = 1.0f - FMath::Clamp((Age - Times[Index]) / WakeDuration, 0.0f, 1.0f);
		for (int32 Strand = Style >= 3 ? 0 : -1; Strand <= (Style >= 3 ? 0 : 1); ++Strand)
		{
			const float Offset = Strand * (5.4f + FMath::Sin(Times[Index] * 31.0f + Strand) * 1.7f);
			const float Width = Style >= 7 ? 24.0f : Style == 6 ? 64.0f : Style == 4 ? 58.0f : Style == 5 ? 34.0f : Strand == 0 ? (Style == 1 ? 11.0f : 8.5f) : 3.5f;
			Lines.Emplace(FRotationMatrix::MakeFromXZ(Delta.GetSafeNormal(), Normal).Rotator(), Center + Across * Offset,
				FVector(Delta.Size() / 100.0f, Width * Fade / 100.0f, 1.0f));
			SegmentData.Emplace(Distances[Index - 1], Delta.Size());
		}
	}
	Material->SetScalarParameterValue(TEXT("Envelope"), EndAt < 0.0f ? 1.0f : 1.0f - (Age - EndAt) / .16f);
	Material->SetScalarParameterValue(TEXT("Age"), Age);
	UploadELines(Strands, Lines);
	for (int32 Index = 0; Index < SegmentData.Num(); ++Index)
	{
		Strands->SetCustomDataValue(Index, 0, SegmentData[Index].X, false);
		Strands->SetCustomDataValue(Index, 1, SegmentData[Index].Y, Index == SegmentData.Num() - 1);
	}
}
