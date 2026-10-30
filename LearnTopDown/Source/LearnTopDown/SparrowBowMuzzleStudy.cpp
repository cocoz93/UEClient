#include "SparrowBowMuzzleStudy.h"
#include "SparrowHarmonyFX.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/SplineMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "TopDownCombatCharacter.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	TAutoConsoleVariable<int32> CVarBowMuzzleStyle(TEXT("Sparrow.BowMuzzle.Style"), 7,
		TEXT("D bow studies: 0 installed, 1 flame feather coating, 2 limb currents, 3 drawn light strings, 4 currents converging into light strings, 5 frozen release tail, 6 fitted feathers, 7 whole weapon-sized ornate bow without forward release tails."));
	TAutoConsoleVariable<int32> CVarBowMuzzleAudit(TEXT("Sparrow.BowMuzzle.Audit"), 0,
		TEXT("Log D6 live spline binding and projected surface area at three preparation samples."));
	const FName LimbBones[2][5] = {
		{TEXT("bow_base"), TEXT("bow_shaft_top_01"), TEXT("bow_shaft_top_02"), TEXT("bow_shaft_top_03"), TEXT("bow_string_top")},
		{TEXT("bow_base"), TEXT("bow_shaft_bott_01"), TEXT("bow_shaft_bott_02"), TEXT("bow_shaft_bott_03"), TEXT("bow_string_bott")}};
	float Ease(float A, float B, float Value) { return FMath::SmoothStep(A, B, Value); }
}

int32 ASparrowBowMuzzleStudy::GetPreviewStyle()
{
	return FMath::Clamp(CVarBowMuzzleStyle.GetValueOnGameThread(), 0, 7);
}

ASparrowBowMuzzleStudy::ASparrowBowMuzzleStudy()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false;
	PrimaryActorTick.TickGroup = TG_PostPhysics;
	SetCanBeDamaged(false);
	SetActorEnableCollision(false);
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Plane(TEXT("/Engine/BasicShapes/Plane.Plane"));
	const TCHAR* Names[] = {TEXT("LimbCoating"), TEXT("LimbCurrents"), TEXT("LightStrings"), TEXT("FlameBarbs"), TEXT("BowEmbers")};
	for (int32 Index = 0; Index < BankCount; ++Index)
	{
		UInstancedStaticMeshComponent* Mesh = CreateDefaultSubobject<UInstancedStaticMeshComponent>(Names[Index]);
		Mesh->SetupAttachment(GetRootComponent());
		Mesh->SetMobility(EComponentMobility::Movable);
		Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Mesh->SetGenerateOverlapEvents(false);
		Mesh->SetCanEverAffectNavigation(false);
		Mesh->SetCastShadow(false);
		Mesh->SetReceivesDecals(false);
		Mesh->SetStaticMesh(Plane.Object);
		Mesh->NumCustomDataFloats = 4;
		Mesh->ComponentTags.Append({TEXT("SparrowSkillFX"), TEXT("SparrowBowMuzzleSurface")});
		Banks.Add(Mesh);
		Transforms[Index].Reserve(160);
		InstanceData[Index].Reserve(160);
	}
	Tags.Append({TEXT("SparrowSkillFXProxy"), TEXT("SparrowBowMuzzleStudy")});
}

bool ASparrowBowMuzzleStudy::Initialize(ATopDownCombatCharacter* Character, const FVector& Aim, float ChargeSeconds)
{
	Design = GetPreviewStyle();
	if (!IsValid(Character) || Design == 0 || !Character->GetMesh()) { return false; }
	USkeletalMeshComponent* Mesh = Character->GetMesh();
	for (const auto& Side : LimbBones)
	{
		for (FName Bone : Side)
		{
			if (!Mesh->DoesSocketExist(Bone))
			{
				UE_LOG(LogTemp, Warning, TEXT("SPARROW_BOW_STUDY missing bone=%s"), *Bone.ToString());
				return false;
			}
		}
	}
	if (!Mesh->DoesSocketExist(TEXT("arrow_nock"))) { return false; }
	const TCHAR* Names[] = {TEXT("Coating"), TEXT("Current"), TEXT("Thread"), TEXT("Feather"), TEXT("Ember")};
	for (int32 Index = 0; Index < BankCount; ++Index)
	{
		const FString Path = FString::Printf(TEXT("/Game/TopDown/Characters/Sparrow/FX/BowMuzzle20261027/M_BowMuzzle%s.M_BowMuzzle%s"), Names[Index], Names[Index]);
		UMaterialInterface* Source = LoadObject<UMaterialInterface>(nullptr, *Path);
		UMaterialInstanceDynamic* Material = Source ? Banks[Index]->CreateDynamicMaterialInstance(0, Source) : nullptr;
		if (!Material) { UE_LOG(LogTemp, Warning, TEXT("SPARROW_BOW_STUDY missing material=%s"), *Path); return false; }
		Materials.Add(Material);
	}
	Caster = Character;
	Body = Mesh;
	SetOwner(Character);
	Forward = (Aim - Character->GetActorLocation()).GetSafeNormal2D();
	if (Forward.IsNearlyZero()) { Forward = Character->GetActorForwardVector(); }
	Charge = FMath::Clamp(ChargeSeconds, .1f, 2.0f);
	if (Design == 6 && !CreateFeatherSkin())
	{
		UE_LOG(LogTemp, Warning, TEXT("SPARROW_BOW_STUDY D6 feather resources unavailable; live renaissance coating remains visible"));
	}
	if (Design == 7 && !CreateOrnateBow()) { return false; }
	AddTickPrerequisiteComponent(Mesh);
	Tags.Add(FName(*FString::Printf(TEXT("SparrowBowMuzzleD%d"), Design)));
	HarmonyFX = ASparrowHarmonyFX::Create(Character, TEXT("D"), Mesh->GetSocketLocation(TEXT("arrow_anchor")), Forward, Charge, this);
	bReady = true;
	SetLifeSpan(Charge + 1.3f);
	SetActorTickEnabled(true);
	Draw();
	return true;
}

bool ASparrowBowMuzzleStudy::CreateOrnateBow()
{
	UStaticMesh* Shape = LoadObject<UStaticMesh>(nullptr,
		TEXT("/Game/TopDown/Characters/Sparrow/FX/Harmony20261028/SM_ReferenceBow.SM_ReferenceBow"));
	UMaterialInterface* Surface = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Sparrow/FX/Harmony20261028/M_BowRelief.M_BowRelief"));
	if (!Shape || !Surface) { return false; }
	OrnateBow = NewObject<UStaticMeshComponent>(this);
	OrnateBow->SetupAttachment(GetRootComponent());
	OrnateBow->SetMobility(EComponentMobility::Movable);
	OrnateBow->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	OrnateBow->SetGenerateOverlapEvents(false);
	OrnateBow->SetCanEverAffectNavigation(false);
	OrnateBow->SetCastShadow(false);
	OrnateBow->SetReceivesDecals(false);
	OrnateBow->SetStaticMesh(Shape);
	OrnateMaterial = UMaterialInstanceDynamic::Create(Surface, this);
	OrnateBow->SetMaterial(0, OrnateMaterial);
	OrnateBow->ComponentTags.Append({TEXT("SparrowSkillFX"), TEXT("SparrowD7WeaponBow")});
	AddInstanceComponent(OrnateBow);
	OrnateBow->RegisterComponent();
	return true;
}

void ASparrowBowMuzzleStudy::DrawOrnateBow(float Preparation, float Pulse, float Fade)
{
	if (!OrnateBow || !OrnateMaterial) { return; }
	const FVector Grip = Limb[0][0];
	const FVector PhysicalAcross = UpperTip - LowerTip;
	const FVector Across = (PhysicalAcross - CameraNormal * FVector::DotProduct(PhysicalAcross, CameraNormal)).GetSafeNormal();
	FVector Axis = FVector::CrossProduct(Across, CameraNormal).GetSafeNormal();
	// The authored tips are at negative X. Align that curvature to the real
	// tip midpoint, rather than assuming this weapon bends along the shot axis.
	if (FVector::DotProduct(Axis, Grip - (UpperTip + LowerTip) * .5f) < 0.0f) { Axis *= -1.0f; }
	// One continuous bow silhouette follows the real grip and tip span. Its
	// feather barbs are only a small margin beyond the weapon, never a new giant bow.
	const float Size = BowSpan * 1.15f / 526.0f;
	OrnateBow->SetWorldLocation(Grip + CameraNormal * 1.3f);
	OrnateBow->SetWorldRotation(FRotationMatrix::MakeFromXY(Axis, Across).ToQuat());
	OrnateBow->SetWorldScale3D(FVector(Size * 1.3f, Size, Size));
	OrnateBow->SetVisibility(Fade > .01f);
	OrnateMaterial->SetScalarParameterValue(TEXT("Age"), Age);
	OrnateMaterial->SetScalarParameterValue(TEXT("Open"), Preparation);
	OrnateMaterial->SetScalarParameterValue(TEXT("Pulse"), Pulse);
	OrnateMaterial->SetScalarParameterValue(TEXT("Envelope"), Fade);
}

bool ASparrowBowMuzzleStudy::CreateFeatherSkin()
{
	static const TCHAR* Folder = TEXT("/Game/TopDown/Characters/Sparrow/FX/PlumeBow20261028");
	const FString MaterialPath = FString::Printf(TEXT("%s/M_D6FeatherBow.M_D6FeatherBow"), Folder);
	UMaterialInterface* Source = LoadObject<UMaterialInterface>(nullptr, *MaterialPath);
	if (!Source) { return false; }
	UStaticMesh* Meshes[6] = {};
	for (int32 Index = 0; Index < 6; ++Index)
	{
		const FString Name = FString::Printf(TEXT("SM_D6Feather_%d_%d"), Index / 3, Index % 3);
		const FString Path = FString::Printf(TEXT("%s/%s.%s"), Folder, *Name, *Name);
		Meshes[Index] = LoadObject<UStaticMesh>(nullptr, *Path);
		if (!Meshes[Index]) { return false; }
	}
	FeatherMaterial = UMaterialInstanceDynamic::Create(Source, this);
	for (int32 Index = 0; Index < 6; ++Index)
	{
		USplineMeshComponent* Part = NewObject<USplineMeshComponent>(this);
		Part->SetupAttachment(GetRootComponent());
		Part->SetMobility(EComponentMobility::Movable);
		Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Part->SetGenerateOverlapEvents(false);
		Part->SetCanEverAffectNavigation(false);
		Part->SetCastShadow(false);
		Part->SetReceivesDecals(false);
		Part->SetStaticMesh(Meshes[Index]);
		Part->SetForwardAxis(ESplineMeshAxis::X, false);
		Part->SetBoundaryMin(0.0f, false);
		Part->SetBoundaryMax(100.0f, false);
		Part->SetStartAndEnd(FVector::ZeroVector, FVector(100.0f, 0.0f, 0.0f),
			FVector(100.0f, 0.0f, 0.0f), FVector(100.0f, 0.0f, 0.0f), false);
		Part->SetMaterial(0, FeatherMaterial);
		Part->ComponentTags.Append({TEXT("SparrowSkillFX"), TEXT("SparrowD6FittedFeathers")});
		AddInstanceComponent(Part);
		Part->RegisterComponent();
		FeatherSkin.Add(Part);
	}
	return true;
}

void ASparrowBowMuzzleStudy::DrawFeatherSkin(float Preparation, float Pulse, float Fade)
{
	if (FeatherSkin.Num() != 6 || !FeatherMaterial) { return; }
	const FVector Grip = Limb[0][0];
	FeatherMaterial->SetScalarParameterValue(TEXT("Age"), Age);
	FeatherMaterial->SetScalarParameterValue(TEXT("Open"), Preparation);
	FeatherMaterial->SetScalarParameterValue(TEXT("Pulse"), Pulse);
	FeatherMaterial->SetScalarParameterValue(TEXT("Envelope"), Fade);
	float MinimumSourceProjection = 1.0f, MinimumVisibleProjection = 1.0f;
	for (int32 Side = 0; Side < 2; ++Side)
	{
		// Engine spline X-forward maps mesh Y to cross(Up, tangent). Choose
		// that side away from the drawn string so each feather lies outside
		// its actual limb. Each feather's root stays on that bound limb.
		// The new separate quills overlap instead of sharing an edge. Each can
		// now open around its own bound rachis without tearing a continuous skin.
		for (int32 Section = 0; Section < 3; ++Section)
		{
			USplineMeshComponent* Part = FeatherSkin[Side * 3 + Section];
			const float A = Section / 3.0f, B = (Section + 1) / 3.0f;
			const auto Derivative = [this, Side](float T)
			{
				const float Lo = FMath::Max(0.0f, T - .002f), Hi = FMath::Min(1.0f, T + .002f);
				return (LimbPoint(Side, Hi) - LimbPoint(Side, Lo)) / (Hi - Lo) / 3.0f;
			};
			const FVector Start = LimbPoint(Side, A) - Grip, End = LimbPoint(Side, B) - Grip;
			const FVector StartTangent = Derivative(A), EndTangent = Derivative(B);
			const FVector Tangent = FMath::CubicInterpDerivative(Start, StartTangent, End, EndTangent, .5f).GetSafeNormal();
			const FVector Middle = LimbPoint(Side, (A + B) * .5f);
			FVector SourceUp = BowNormal;
			if (FVector::DotProduct(FVector::CrossProduct(SourceUp, Tangent), Nock - Middle) > 0.0f) { SourceUp *= -1.0f; }
			const auto ProjectedArea = [&](const FVector& ReferenceUp)
			{
				float Minimum = 1.0f;
				for (float Alpha : {0.0f, .5f, 1.0f})
				{
					const FVector Direction = FMath::CubicInterpDerivative(Start, StartTangent, End, EndTangent, Alpha).GetSafeNormal();
					// Match FSplineMeshSceneProxyDesc's actual YVec surface normal.
					// Raw SplineUpDir includes a tangent component and is not a normal.
					const FVector SurfaceNormal = FVector::CrossProduct(Direction,
						FVector::CrossProduct(ReferenceUp, Direction)).GetSafeNormal();
					Minimum = FMath::Min(Minimum, FMath::Abs(FVector::DotProduct(SurfaceNormal, CameraNormal)));
				}
				return Minimum;
			};
			const float SourceProjection = ProjectedArea(SourceUp);
			float BestProjection = SourceProjection;
			FVector Up = SourceUp;
			FVector ViewNormal = (CameraNormal - Tangent * FVector::DotProduct(CameraNormal, Tangent)).GetSafeNormal();
			if (FVector::DotProduct(ViewNormal, SourceUp) < 0.0f) { ViewNormal *= -1.0f; }
			if (SourceProjection < .58f && !ViewNormal.IsNearlyZero())
			{
				// Include the original frame as the baseline. No selected correction
				// can reduce the worst projected area of the three measured slices.
				for (float Blend : {.25f, .50f, .75f, 1.0f})
				{
					const FVector Candidate = FMath::Lerp(SourceUp, ViewNormal, Blend).GetSafeNormal();
					const float Projection = ProjectedArea(Candidate);
					if (Projection > BestProjection) { BestProjection = Projection; Up = Candidate; }
				}
			}
			MinimumSourceProjection = FMath::Min(MinimumSourceProjection, SourceProjection);
			MinimumVisibleProjection = FMath::Min(MinimumVisibleProjection, BestProjection);
			// Mesh origin is at the grip, but its spine endpoints are measured
			// from the live bones every frame, including the release animation.
			Part->SetWorldTransform(FTransform(FQuat::Identity, Grip + CameraNormal * .65f));
			Part->SetSplineUpDir(Up, false);
			Part->SetStartScale(FVector2D(1.0f, 1.0f), false);
			Part->SetEndScale(FVector2D(1.0f, 1.0f), false);
			Part->SetStartAndEnd(Start, StartTangent, End, EndTangent, false);
			Part->SetVisibility(Fade > .01f);
			Part->UpdateMesh();
		}
	}
	static constexpr float AuditTimes[] = {.16f, .33f, .49f};
	if (CVarBowMuzzleAudit.GetValueOnGameThread() != 0 && FeatherAuditSamples < UE_ARRAY_COUNT(AuditTimes) && Age >= AuditTimes[FeatherAuditSamples])
	{
		UE_LOG(LogTemp, Display, TEXT("SPARROW_D6_FEATHER age=%.3f splines=%d span=%.2f sourceProjectedArea=%.3f visibleProjectedArea=%.3f basis=Frenet3Slices quillTips=12/16/18cm open=%.3f opacity=%.3f material=%s"),
			Age, FeatherSkin.Num(), BowSpan, MinimumSourceProjection, MinimumVisibleProjection, Preparation, Fade,
			*FeatherMaterial->GetPathName());
		++FeatherAuditSamples;
	}
}

void ASparrowBowMuzzleStudy::Release()
{
	if (HarmonyFX.IsValid()) { HarmonyFX->NotifyShot(); }
	if (bReady && ReleasedAt < 0.0f && CancelledAt < 0.0f)
	{
		ReleasedAt = Age;
		ReleaseGrip = Limb[0][0];
		ReleaseBowNormal = BowNormal;
		for (int32 Side = 0; Side < 2; ++Side)
		{
			for (int32 Ray = 0; Ray < 3; ++Ray) { ReleaseLimb[Side][Ray] = LimbPoint(Side, .45f + Ray * .23f); }
		}
		SetLifeSpan(Design == 5 ? 1.05f : .72f);
		Draw();
	}
}

void ASparrowBowMuzzleStudy::Cancel()
{
	if (ReleasedAt >= 0.0f || CancelledAt >= 0.0f) { return; }
	CancelledAt = Age;
	SetLifeSpan(.1f);
}

void ASparrowBowMuzzleStudy::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!bReady || !Caster.IsValid() || !Body.IsValid()) { Destroy(); return; }
	Age += DeltaSeconds;
	Draw();
}

FVector ASparrowBowMuzzleStudy::LimbPoint(int32 Side, float T) const
{
	const float Along = FMath::Clamp(T, 0.0f, 1.0f) * 4.0f;
	const int32 Index = FMath::Min(3, FMath::FloorToInt(Along));
	const float U = Along - Index;
	const FVector& A = Limb[Side][Index];
	const FVector& B = Limb[Side][Index + 1];
	const FVector TangentA = Index == 0 ? B - A : (B - Limb[Side][Index - 1]) * .5f;
	const FVector TangentB = Index == 3 ? B - A : (Limb[Side][Index + 2] - A) * .5f;
	return FMath::CubicInterp(A, TangentA, B, TangentB, U);
}

void ASparrowBowMuzzleStudy::Segment(int32 Bank, const FVector& A, const FVector& B, float Width,
	float Start, float Span, float Seed, float Alpha)
{
	const FVector Delta = B - A;
	const float Length = FMath::Max(Delta.Size(), .02f);
	const FVector Axis = Delta.IsNearlyZero(.001) ? Forward : Delta / Length;
	const FQuat Rotation = FRotationMatrix::MakeFromXZ(Axis, CameraNormal).ToQuat();
	Transforms[Bank].Emplace(Rotation, (A + B) * .5f,
		FVector((Length + .12f) / 100.0f, FMath::Max(.02f, Width) / 100.0f, 1.0f));
	InstanceData[Bank].Emplace(Start, Span, Seed, Alpha);
}

void ASparrowBowMuzzleStudy::Draw()
{
	if (!Body.IsValid()) { return; }
	for (int32 Side = 0; Side < 2; ++Side)
	{
		for (int32 Index = 0; Index < 5; ++Index) { Limb[Side][Index] = Body->GetSocketLocation(LimbBones[Side][Index]); }
	}
	Nock = Body->GetSocketLocation(TEXT("arrow_nock"));
	UpperTip = Limb[0][4]; LowerTip = Limb[1][4];
	BowSpan = FVector::Distance(UpperTip, LowerTip);
	const FVector Grip = Limb[0][0];
	BowNormal = FVector::CrossProduct(UpperTip - LowerTip, Nock - Grip).GetSafeNormal();
	if (BowNormal.IsNearlyZero()) { BowNormal = FVector::CrossProduct(Forward, FVector::UpVector).GetSafeNormal(); }
	const APlayerController* Player = GetWorld()->GetFirstPlayerController();
	if (Player && Player->PlayerCameraManager) { CameraNormal = (Player->PlayerCameraManager->GetCameraLocation() - Grip).GetSafeNormal(); }
	const float SinceShot = ReleasedAt < 0.0f ? -1.0f : Age - ReleasedAt;
	const float Preparation = Ease(.01f, Charge * .72f, Age);
	const float Fade = (SinceShot < 0.0f ? 1.0f : 1.0f - Ease(.16f, Design == 5 ? 1.0f : .70f, SinceShot)) *
		(CancelledAt < 0.0f ? 1.0f : 1.0f - Ease(0.0f, .1f, Age - CancelledAt));
	const float Pulse = SinceShot < 0.0f ? 0.0f : FMath::Exp(-SinceShot * 22.0f);
	for (int32 Bank = 0; Bank < BankCount; ++Bank)
	{
		Transforms[Bank].Reset(); InstanceData[Bank].Reset();
		Materials[Bank]->SetScalarParameterValue(TEXT("Age"), Age);
		const float SupportingLayer = Design == 7 && Bank < 2 ? .08f :
			Design == 6 && FeatherSkin.Num() == 6 && Bank < 2 ? .42f : 1.0f;
		Materials[Bank]->SetScalarParameterValue(TEXT("Envelope"), Ease(0.0f, .09f, Age) * Fade * SupportingLayer);
		Materials[Bank]->SetScalarParameterValue(TEXT("Charge"), Preparation);
		Materials[Bank]->SetScalarParameterValue(TEXT("Pulse"), Pulse);
		Materials[Bank]->SetScalarParameterValue(TEXT("Confluence"), Design >= 4 ? 1.0f : 0.0f);
		Materials[Bank]->SetScalarParameterValue(TEXT("Refinement"), Design >= 5 ? 1.0f : 0.0f);
	}
	const bool bCurrents = Design == 2 || Design >= 4;
	const float StringFocus = Ease(Charge * .20f, Charge * .82f, Age);
	// Each path starts and ends on the animated bow bones. Offsets only decorate
	// the intervening surface, never create a detached bow in front of the hand.
	for (int32 Side = 0; Side < 2; ++Side)
	{
		const int32 Strands = Design >= 4 ? 2 : Design == 2 ? 3 : 1;
		for (int32 Strand = 0; Strand < Strands; ++Strand)
		{
			constexpr int32 Steps = 24;
			const auto Point = [&](float T)
			{
				FVector P = LimbPoint(Side, T);
				if (bCurrents)
				{
					const FVector Tangent = (LimbPoint(Side, FMath::Min(1.0f, T + .02f)) -
						LimbPoint(Side, FMath::Max(0.0f, T - .02f))).GetSafeNormal();
					FVector Outside = FVector::CrossProduct(BowNormal, Tangent).GetSafeNormal();
					if (FVector::DotProduct(Outside, Nock - P) > 0.0f) { Outside *= -1.0f; }
					const float Shape = FMath::Sin(T * PI);
					// Mid-scale gaps survive the gameplay camera; the animated tips stay exact.
					P += Outside * Shape * ((Design >= 4 ? 4.0f : 5.0f) + Strand * 7.0f) *
						(.80f + .20f * FMath::Sin(T * PI * 3.0f + Age * 3.8f + Strand * 1.5f));
					P += BowNormal * Shape * (Strand - (Design >= 4 ? .5f : 1.0f)) * 2.8f;
				}
				return P + CameraNormal * .4f;
			};
			for (int32 Step = 0; Step < Steps; ++Step)
			{
				const float T = float(Step) / Steps;
				const float Width = Design >= 4 ? 9.5f : Design == 1 ? 12.0f : Design == 2 ? 11.0f : 6.0f;
				// The combined study hands visual emphasis from the currents to the
				// drawn strings, avoiding a full-bright stack of the two older studies.
				const float Opacity = Design >= 4 ? .74f - StringFocus * .14f : Design == 3 ? .7f : 1.0f;
				Segment(bCurrents ? 1 : 0, Point(T), Point(T + 1.0f / Steps), Width,
					T, 1.0f / Steps, Side * .41f + Strand * .23f, Opacity);
			}
		}
		if (Design >= 5)
		{
			for (int32 Step = 0; Step < 28; ++Step)
			{
				const float T = float(Step) / 28.0f;
				const float Width = 10.0f + FMath::Sin(T * PI) * 7.0f;
				Segment(0, LimbPoint(Side, T), LimbPoint(Side, T + 1.0f / 28.0f), Width,
					T, 1.0f / 28.0f, Side * .5f, .76f);
			}
			if (Design != 7 && SinceShot >= 0.0f && SinceShot < (Design == 6 ? .22f : .85f))
			{
				const float Tail = 1.0f - Ease(Design == 6 ? .025f : .16f, Design == 6 ? .22f : .85f, SinceShot);
				for (int32 Ray = 0; Ray < 3; ++Ray)
				{
					// 발사 순간의 활 곡면에 잔광을 남겨, 활을 내리는 모션과 분리해 천천히 소멸한다.
					// D6 restores the user's D0 preview: live limb and .22s release.
					const FVector Start = Design == 6 ? LimbPoint(Side, .45f + Ray * .23f) : ReleaseLimb[Side][Ray];
					const FVector End = (Design == 6 ? Grip : ReleaseGrip) + Forward * (35.0f + FMath::Min(SinceShot, .22f) * 340.0f);
					const FVector Bend = (Design == 6 ? BowNormal : ReleaseBowNormal) * (Ray - 1) * 8.0f + Forward * 28.0f;
					for (int32 Step = 0; Step < 20; ++Step)
					{
						const float U = float(Step) / 20.0f, Next = U + .05f;
						const FVector A = FMath::Lerp(Start, End, U) + Bend * FMath::Sin(U * PI);
						const FVector B = FMath::Lerp(Start, End, Next) + Bend * FMath::Sin(Next * PI);
						Segment(1, A, B, 16.0f + FMath::Sin(U * PI) * 13.0f, U, .05f,
							Ray * .17f + Side, Tail * .46f);
					}
				}
			}
		}
		if (Design == 1)
		{
			for (int32 Index = 0; Index < 9; ++Index)
			{
				const float T = .18f + Index * .088f;
				const FVector Base = LimbPoint(Side, T);
				const FVector Tangent = (LimbPoint(Side, FMath::Min(1.0f, T + .035f)) - Base).GetSafeNormal();
				const FVector InPlane = FVector::CrossProduct(BowNormal, Tangent).GetSafeNormal();
				const float Sign = Index % 2 ? 1.0f : -1.0f;
				const float Length = 16.0f + 9.0f * FMath::Sin(T * PI) + 1.5f * FMath::Sin(Age * 9.0f + Index);
				const FVector Tip = Base + Tangent * Length + InPlane * Sign * Length * .46f;
				Segment(3, Base + CameraNormal * .7f, Tip + CameraNormal * .7f, 9.5f, 0, 1, Index * .173f + Side);
			}
		}
		// D3 exposes the existing physical bow, filling its actual drawn triangle
		// with taut filaments instead of a separate floating fan or wing ornament.
		const int32 StringCount = Design == 7 ? 1 : Design >= 4 ? 4 : Design == 3 ? 6 : 1;
		for (int32 Index = 0; Index < StringCount; ++Index)
		{
			const float T = Design == 7 ? 1.0f : Design >= 4 ? .34f + float(Index) / 3.0f * .66f : Design == 3 ? .22f + float(Index) / 5.0f * .78f : 1.0f;
			const FVector Start = LimbPoint(Side, T);
			const float Retract = SinceShot < 0.0f ? 0.0f : Ease(0.0f, .075f, SinceShot);
			const FVector End = FMath::Lerp(Nock, Grip, Retract);
			float Alpha = SinceShot < 0.0f ? (.35f + Preparation * .65f) : 1.0f - Ease(.015f, .14f, SinceShot);
			if (Design >= 4) { Alpha *= .88f * StringFocus; }
			Segment(2, Start, End, Design >= 4 ? 4.0f : Design == 3 ? 4.6f : 1.5f,
				0, 1, Index * .19f + Side * .5f, Alpha);
		}
	}
	for (int32 Index = 0; Index < 20; ++Index)
	{
		const float Cycle = FMath::Frac(Age * (1.0f + Index * .013f) + Index * .618034f);
		const int32 Side = Index % 2;
		const float T = 1.0f - Cycle;
		FVector Position = LimbPoint(Side, T);
		const FVector Tangent = (LimbPoint(Side, FMath::Min(1.0f, T + .02f)) - LimbPoint(Side, FMath::Max(0.0f, T - .02f))).GetSafeNormal();
		const FVector SideVector = FVector::CrossProduct(BowNormal, Tangent).GetSafeNormal();
		Position += SideVector * FMath::Sin(Index * 2.4f + Age * 4.0f) * (bCurrents ? 5.0f : 2.5f);
		Position += CameraNormal;
		const float Alpha = FMath::Sin(Cycle * PI) * (.55f + Pulse * .45f);
		Segment(4, Position - Tangent * .6f, Position + Tangent * (1.8f + Pulse * 3.0f), 1.7f, 0, 1, Index * .13f, Alpha);
	}
	// A short nock-to-grip contraction belongs to the release event; the actual
	// shot remains the single existing ASparrowArrow owned by the D skill.
	const float ReleaseAlpha = SinceShot < 0.0f ? Preparation * .7f : FMath::Exp(-SinceShot * 30.0f);
	const float NockSize = Design >= 4 ? 2.2f : Design == 3 ? 2.8f : 1.35f;
	Segment(4, Nock - Forward * (2.0f * NockSize), Nock + Forward * (4.0f * NockSize),
		(5.0f + Pulse * 3.0f) * NockSize, 0, 1, .5f, ReleaseAlpha);
	Upload();
	if (Design == 6) { DrawFeatherSkin(Preparation, Pulse, Fade); }
	if (Design == 7) { DrawOrnateBow(Preparation, Pulse, Fade); }
}

void ASparrowBowMuzzleStudy::Upload()
{
	for (int32 Bank = 0; Bank < BankCount; ++Bank)
	{
		UInstancedStaticMeshComponent* Mesh = Banks[Bank];
		if (Mesh->GetInstanceCount() != Transforms[Bank].Num())
		{
			Mesh->ClearInstances();
			if (!Transforms[Bank].IsEmpty()) { Mesh->AddInstances(Transforms[Bank], false, true); }
		}
		else if (!Transforms[Bank].IsEmpty()) { Mesh->BatchUpdateInstancesTransforms(0, Transforms[Bank], true, false, true); }
		for (int32 Index = 0; Index < InstanceData[Bank].Num(); ++Index)
		{
			const FVector4f& Data = InstanceData[Bank][Index];
			for (int32 Channel = 0; Channel < 4; ++Channel) { Mesh->SetCustomDataValue(Index, Channel, Data[Channel], false); }
		}
		Mesh->MarkRenderStateDirty();
	}
}

int32 ASparrowBowMuzzleStudy::GetVisibleSegmentCount() const
{
	int32 Count = 0;
	for (const UInstancedStaticMeshComponent* Mesh : Banks) { Count += Mesh->GetInstanceCount(); }
	return Count;
}
