#include "SparrowGatherShot.h"
#include "SparrowHarmonyFX.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "SparrowArrow.h"
#include "SparrowSkillComponent.h"
#include "TopDownCombatCharacter.h"

namespace
{
	TAutoConsoleVariable<int32> CVarSparrowFDesignStyle(TEXT("Sparrow.FDesign.Style"), 7,
		TEXT("F design: 0 legacy, 1 crystal assembly, 2 pressure vortex, 3 feather convergence, 4 crystal vortex, 5 fine crystals, 6 charged crystal shot, 7 adopted aligned light splinters, 8 spiral light needles."));
	constexpr int32 DesignShardCount = 12;
	constexpr int32 CrystalFragmentsPerArrow = 8;
	constexpr int32 CrystalFoldsPerArrow = 3;
	constexpr float CrystalArrowLength = 240.0f;
	constexpr float CrystalDisplayLead = 110.0f;
	constexpr float CrystalPressureRadius = 56.641f;
	constexpr float CrystalMeshLength = 158.395f;
	constexpr float CrystalMeshTip = 61.464f;
	int32 DesignPieces(int32 Style) { return Style == 7 ? 18 : Style == 8 ? 36 : Style == 6 ? 24 : Style == 5 ? 40 : Style == 1 || Style == 4 ? 16 : Style == 3 ? 18 : 0; }
	int32 DesignRibbons(int32 Style) { return Style == 7 ? 3 : Style == 8 ? 5 : Style == 6 ? 4 : 2; }

	FVector CrystalLaneOffset(int32 Lane, bool bAscended, const FVector& Right)
	{
		if (!bAscended) { return FVector::ZeroVector; }
		if (Lane == 0) { return FVector::UpVector * 32.0f; }
		return Right * (Lane == 1 ? -28.0f : 28.0f) - FVector::UpVector * 16.0f;
	}
}

ASparrowGatherShot::ASparrowGatherShot()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickGroup = TG_PostPhysics;
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
	SetActorEnableCollision(false);
	SetCanBeDamaged(false);
	Tags.Append({TEXT("SparrowSkillFX"), TEXT("SparrowGatherShot")});
}

bool ASparrowGatherShot::Initialize(ATopDownCombatCharacter* Character, const FVector& Aim, bool bCrystal, float ChargeSeconds)
{
	if (!IsValid(Character) || !Character->GetMesh() || GetOwner() != Character) { return false; }
	Caster = Character;
	const USparrowSkillComponent* Skills = Character->FindComponentByClass<USparrowSkillComponent>();
	bAscended = Skills && Skills->GetAscensionRemaining() > 0.0f;
	if (bAscended) { Tags.Add(TEXT("SparrowAscendedGather")); }
	Direction = (Aim - Character->GetActorLocation()).GetSafeNormal2D();
	if (Direction.IsNearlyZero()) { return false; }
	bCrystals = bCrystal;
	Charge = FMath::Max(.1f, ChargeSeconds);
	Tags.Add(bCrystals ? TEXT("SparrowCrystalShot") : TEXT("SparrowConvergingShot"));
	FDesignStyle = bCrystals ? FMath::Clamp(CVarSparrowFDesignStyle.GetValueOnGameThread(), 0, 8) : 0;
	if (FDesignStyle > 0)
	{
		const bool Ready = InitializeDesignSurfaces();
		if (Ready) { HarmonyFX = ASparrowHarmonyFX::Create(Character, TEXT("F"), Character->GetActorLocation(), Direction, Charge, this); }
		return Ready;
	}
	UStaticMesh* Plane = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
	UStaticMesh* PressureMesh = bCrystals ? LoadObject<UStaticMesh>(nullptr, TEXT("/Game/ParagonSparrow/FX/Meshes/Heroes/Sparrow/Abilities/SM_ShockwaveFlame.SM_ShockwaveFlame")) : nullptr;
	UStaticMesh* CrystalMesh = bCrystals ? LoadObject<UStaticMesh>(nullptr, TEXT("/Game/ParagonSparrow/FX/Meshes/Heroes/Sparrow/Abilities/SM_Sparrow_Arrow.SM_Sparrow_Arrow")) : nullptr;
	if (bCrystals && (!PressureMesh || !CrystalMesh)) { return false; }
	const int32 Lanes = bCrystals && bAscended ? 3 : 1;
	const int32 BodyCount = bCrystals ? CrystalFragmentsPerArrow * Lanes : (bAscended ? 14 : 10);
	const int32 Flakes = bCrystals ? 0 : (bAscended ? 20 : 14);
	const int32 MainCount = BodyCount + Flakes;
	for (int32 Index = 0; Index < MainCount + (bCrystals ? Lanes * 2 : 2); ++Index)
	{
		const TCHAR* Path = bCrystals ? (Index < MainCount ? (Index % CrystalFragmentsPerArrow < CrystalFoldsPerArrow ?
			TEXT("/Game/TopDown/Characters/Sparrow/Materials/Arsenal20261026/M_GatherCrystalFold.M_GatherCrystalFold") :
			TEXT("/Game/TopDown/Characters/Sparrow/Materials/Arsenal20261026/M_GatherCrystalFragment.M_GatherCrystalFragment")) :
			Index < MainCount + Lanes ?
			TEXT("/Game/TopDown/Characters/Sparrow/Materials/Arsenal20261026/M_GatherCrystalArrow.M_GatherCrystalArrow") :
			TEXT("/Game/TopDown/Characters/Sparrow/Materials/Arsenal20261026/M_GatherCrystalRelease.M_GatherCrystalRelease")) :
			Index >= MainCount ?
			TEXT("/Game/TopDown/Characters/Sparrow/Materials/Arsenal20261026/M_GatherRelease.M_GatherRelease") :
			Index >= BodyCount ? TEXT("/Game/TopDown/Characters/Sparrow/Materials/SharpArt20261026/M_SharpT11Body.M_SharpT11Body") :
			TEXT("/Game/TopDown/Characters/Sparrow/Materials/Arsenal20261026/M_GatherRibbon.M_GatherRibbon");
		UStaticMesh* SurfaceMesh = Plane;
		if (bCrystals)
		{
			const bool bBody = Index < MainCount;
			const int32 Piece = Index % CrystalFragmentsPerArrow;
			if ((bBody && Piece < CrystalFoldsPerArrow) || (Index >= MainCount && Index < MainCount + Lanes))
			{
				SurfaceMesh = PressureMesh;
			}
			else if (bBody && Piece == CrystalFoldsPerArrow)
			{
				SurfaceMesh = CrystalMesh;
				Path = TEXT("/Game/TopDown/Characters/Sparrow/Materials/Arsenal20261026/M_GatherCrystalSolid.M_GatherCrystalSolid");
			}
		}
		FString MaterialPath(Path);
		if (bAscended && (bCrystals || Index < BodyCount || Index >= BodyCount + Flakes))
		{
			MaterialPath.ReplaceInline(TEXT("/Arsenal20261026/"), TEXT("/AscendedArsenal20261026/"));
			MaterialPath.ReplaceInline(TEXT("/SharpArt20261026/"), TEXT("/AscendedArsenal20261026/"));
		}
		UMaterialInterface* Source = LoadObject<UMaterialInterface>(nullptr, *MaterialPath);
		if (!SurfaceMesh || !Source) { return false; }
		UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(Source, this);
		Material->SetScalarParameterValue(TEXT("Index"), Index);
		Material->SetScalarParameterValue(TEXT("Crystal"), bCrystals ? 1.0f : 0.0f);
		Material->SetScalarParameterValue(TEXT("ShotAge"), 100.0f);
		UStaticMeshComponent* Part = NewObject<UStaticMeshComponent>(this, NAME_None, RF_Transient);
		Part->SetMobility(EComponentMobility::Movable);
		Part->SetupAttachment(RootComponent);
		Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Part->SetGenerateOverlapEvents(false);
		Part->SetCanEverAffectNavigation(false);
		Part->SetCastShadow(false);
		Part->SetReceivesDecals(false);
		Part->SetStaticMesh(SurfaceMesh);
		Part->SetMaterial(0, Material);
		Part->SetVisibility(false);
		Part->ComponentTags.Add(TEXT("SparrowGatherSurface"));
		if (bCrystals)
		{
			if (SurfaceMesh == PressureMesh) { Part->ComponentTags.Add(TEXT("SparrowCrystalPressureMesh")); }
			if (SurfaceMesh == CrystalMesh) { Part->ComponentTags.Add(TEXT("SparrowCrystalSolidCore")); }
			Part->ComponentTags.Add(Index < MainCount ?
				(Index % CrystalFragmentsPerArrow < CrystalFoldsPerArrow ? TEXT("SparrowCrystalFold") : TEXT("SparrowCrystalFragment")) :
				Index < MainCount + Lanes ? TEXT("SparrowCrystalAssembly") : TEXT("SparrowCrystalRelease"));
		}
		AddInstanceComponent(Part);
		Part->RegisterComponent();
		Surfaces.Add(Part);
		Materials.Add(Material);
	}
	SetLifeSpan(Charge + .5f);
	return true;
}

void ASparrowGatherShot::PrepareArrowPresentation(ASparrowArrow* Arrow) const
{
	if (!IsValid(Arrow) || !bCrystals || FDesignStyle == 0) { return; }
	if (HarmonyFX.IsValid()) { Arrow->Tags.AddUnique(TEXT("SparrowHarmonyArrow")); }
	// CVar는 준비 시작에만 읽는다. 실제 화살에는 그 시전의 디자인만 전달한다.
	Arrow->Tags.AddUnique(FName(*FString::Printf(TEXT("SparrowFDesign%d"), FDesignStyle >= 7 ? 6 : FDesignStyle)));
}

bool ASparrowGatherShot::InitializeDesignSurfaces()
{
	Tags.Add(FName(*FString::Printf(TEXT("SparrowFDesign%d"), FDesignStyle)));
	const TCHAR* Folder = TEXT("/Game/TopDown/Characters/Sparrow/FX/FDesign20261027");
	const int32 Bodies = DesignPieces(FDesignStyle) + DesignRibbons(FDesignStyle);
	const int32 Lanes = bAscended ? 3 : 1;
	for (int32 Index = 0; Index < Bodies + Lanes; ++Index)
	{
		const bool bCore = Index >= Bodies;
		const bool bShard = Index < DesignPieces(FDesignStyle);
		const TCHAR* MeshName = bCore ? TEXT("SM_FDesignNeedle") : bShard ?
			(FDesignStyle >= 7 ? TEXT("SM_FDesignNeedle") : FDesignStyle == 6 ? TEXT("SM_FDesignCrystal") : FDesignStyle == 3 ? TEXT("SM_FDesignFeather") : TEXT("SM_FDesignFacet")) : TEXT("SM_FDesignHelix");
		const TCHAR* MaterialName = bCore ? TEXT("M_FDesignCore") : bShard ?
			(FDesignStyle >= 7 ? TEXT("M_FDesignCore") : FDesignStyle == 3 ? TEXT("M_FDesignFeather") : TEXT("M_FDesignFacet")) :
			FDesignStyle == 7 || FDesignStyle == 1 || FDesignStyle == 3 || (FDesignStyle == 6 && Index >= DesignPieces(FDesignStyle) + 2) ? TEXT("M_FDesignFilament") : TEXT("M_FDesignRibbon");
		UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *FString::Printf(TEXT("%s/%s.%s"), Folder, MeshName, MeshName));
		UMaterialInterface* Source = LoadObject<UMaterialInterface>(nullptr, *FString::Printf(TEXT("%s/%s.%s"), Folder, MaterialName, MaterialName));
		if (!Mesh || !Source) { return false; }
		UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(Source, this);
		Material->SetScalarParameterValue(TEXT("Index"), Index);
		Material->SetScalarParameterValue(TEXT("Ascended"), bAscended ? 1.0f : 0.0f);
		Material->SetScalarParameterValue(TEXT("Refinement"), FDesignStyle == 6 ? 1.0f : 0.0f);
		UStaticMeshComponent* Part = NewObject<UStaticMeshComponent>(this, NAME_None, RF_Transient);
		Part->SetMobility(EComponentMobility::Movable);
		Part->SetupAttachment(RootComponent);
		Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Part->SetGenerateOverlapEvents(false);
		Part->SetCanEverAffectNavigation(false);
		Part->SetCastShadow(false);
		Part->SetReceivesDecals(false);
		Part->SetStaticMesh(Mesh);
		Part->SetMaterial(0, Material);
		Part->SetVisibility(false);
		Part->ComponentTags.Add(TEXT("SparrowFDesignSurface"));
		Part->ComponentTags.Add(bCore ? TEXT("SparrowFDesignCore") : bShard ? TEXT("SparrowFDesignFacet") : TEXT("SparrowFDesignHelix"));
		AddInstanceComponent(Part);
		Part->RegisterComponent();
		Surfaces.Add(Part);
		Materials.Add(Material);
	}
	SetLifeSpan(Charge + .5f);
	return true;
}

bool ASparrowGatherShot::InitializeDesignImpact(ATopDownCombatCharacter* Character, int32 Style, const FVector& Point, const FVector& ShotDirection)
{
	if (!IsValid(Character) || Style < 1 || Style > 6) { return false; }
	Caster = Character;
	FDesignStyle = Style;
	Direction = ShotDirection.GetSafeNormal();
	Origin = Point;
	bCrystals = true;
	bDesignImpact = true;
	const USparrowSkillComponent* Skills = Character->FindComponentByClass<USparrowSkillComponent>();
	bAscended = Skills && Skills->GetAscensionRemaining() > 0.0f;
	if (!InitializeDesignSurfaces()) { return false; }
	Tags.Add(TEXT("SparrowFDesignImpact"));
	SetLifeSpan(.42f);
	return true;
}

void ASparrowGatherShot::TickDesign(float Progress, float Since)
{
	const bool bReleased = HasReleased();
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Direction).GetSafeNormal();
	const FQuat Axial = FRotationMatrix::MakeFromX(Direction).ToQuat();
	const int32 Pieces = DesignPieces(FDesignStyle);
	const int32 Bodies = Pieces + DesignRibbons(FDesignStyle);
	const float Open = FMath::SmoothStep(0.0f, .20f, Progress);
	const float Pull = FMath::SmoothStep(FDesignStyle >= 6 ? .25f : .51f, FDesignStyle >= 6 ? .78f : .99f, Progress);
	const float Reveal = FMath::SmoothStep(.0f, .10f, Progress);
	for (int32 Index = 0; Index < Surfaces.Num(); ++Index)
	{
		FVector Location = Origin, Scale = FVector::OneVector;
		FQuat Rotation = Axial;
		float Envelope = Reveal;
		if (Index >= Bodies)
		{
			const int32 Lane = Index - Bodies;
			const float Length = FMath::Lerp(55.0f, 270.0f, Pull);
			Location += Direction * (170.0f - Length) + CrystalLaneOffset(Lane, bAscended, Right) * Pull;
			Scale = FVector(Length / 100.0f, .88f, .88f);
			Envelope *= FMath::SmoothStep(FDesignStyle >= 6 ? .40f : .58f, FDesignStyle >= 6 ? .78f : .98f, Progress);
			if (Lane > 0) { Envelope *= Pull; }
			if (bReleased) { Envelope = 0.0f; }
		}
		else if (Index < Pieces)
		{
			// 위치뿐 아니라 실제 결정의 축도 나선 접선에서 화살의 깃 방향으로 접힌다.
			const float Phase = Index * 2.399963f + Progress * (1.0f - Pull) * 2.3f;
			const FVector Radial = Right * FMath::Cos(Phase) + FVector::UpVector * FMath::Sin(Phase);
			const FVector Tangent = -Right * FMath::Sin(Phase) + FVector::UpVector * FMath::Cos(Phase);
			const float Radius = FMath::Lerp((70.0f + (Index % 4) * 22.0f) * Open, 7.0f + (Index % 3) * 3.0f, Pull);
			const float PositionX = FMath::Lerp(70.0f + (Index % 5) * 34.0f, 130.0f - (Index % 5) * 37.0f, Pull);
			const FVector InitialAxis = (Direction * .35f + Tangent * .88f).GetSafeNormal();
			const FVector FinalAxis = (Direction + Radial * .15f).GetSafeNormal();
			const FVector PieceAxis = FMath::Lerp(InitialAxis, FinalAxis, Pull).GetSafeNormal();
			const float FacetScale = FDesignStyle == 6 ? .72f : FDesignStyle == 5 ? .58f : 1.0f;
			const float Length = (44.0f + (Index % 4) * 11.0f) * FMath::Lerp(.45f, 1.0f, Open) * FacetScale;
			Location += Direction * PositionX + Radial * Radius - PieceAxis * Length * .5f;
			Rotation = FRotationMatrix::MakeFromXZ(PieceAxis, Radial + Tangent * .35f).ToQuat();
			Scale = FVector(Length / 100.0f, FDesignStyle == 3 ? 1.25f : FacetScale, FacetScale);
			const float RevealIndex = FDesignStyle == 6 ? Index * 15.0f / 23.0f : FDesignStyle == 5 ? Index * 15.0f / 39.0f : float(Index);
			Envelope *= FMath::SmoothStep(RevealIndex * .008f, .14f + RevealIndex * .008f, Progress);
			if (bReleased) { Envelope = 0.0f; }
		}
		else
		{
			const int32 Ribbon = Index - Pieces;
			const float Phase = Ribbon * 2.399963f + Progress * (FDesignStyle == 2 ? 4.2f : 2.4f);
			const float Length = FMath::Lerp((FDesignStyle == 2 ? 105.0f : 190.0f) * Open, 300.0f, Pull);
			const float Radius = FMath::Lerp(25.0f + Open * (FDesignStyle == 2 ? 125.0f : 92.0f), 12.0f, Pull);
			Location += Direction * (175.0f - Length);
			Rotation = Axial * FQuat(FVector::ForwardVector, Phase);
			Scale = FVector(Length / 100.0f, Radius / 40.0f, Radius / 40.0f);
			Envelope *= (FDesignStyle == 1 ? .17f : FDesignStyle == 3 ? .22f : .75f) * (1.0f - Ribbon * .08f);
			if (bReleased)
			{
				// 화살 본체는 실제 projectile로 인계하고 활 앞에서는 열린 두세 가닥만 짧게 풀린다.
				Location = Origin + Direction * (35.0f - Since * 90.0f);
				Rotation = Axial * FQuat(FVector::ForwardVector, Phase + Since * 5.0f);
				Scale = FVector((110.0f + Since * 240.0f) / 100.0f,
					(24.0f + Since * 220.0f) / 40.0f, (24.0f + Since * 220.0f) / 40.0f);
				Envelope *= (1.0f - FMath::SmoothStep(.02f, .24f, Since)) * .65f;
			}
		}

		if (FDesignStyle >= 7 && Index < Bodies)
		{
			// 준비부만 변주한다. 발사 순간에는 검증된 F6의 실제 화살로 인계한다.
			if (Index < Pieces)
			{
				const float Stagger = (Index % 6) * .018f;
				const float Gather = FMath::SmoothStep(.18f + Stagger, .82f, Progress);
				const float Angle = Index * 2.399963f + (FDesignStyle == 8 ? Progress * 7.0f * (1.0f - Gather) : 0.0f);
				const FVector Radial = Right * FMath::Cos(Angle) + FVector::UpVector * FMath::Sin(Angle);
				const float StartRadius = FDesignStyle == 7 ? 35.0f + (Index % 3) * 19.0f : 86.0f + (Index % 4) * 12.0f;
				const float Radius = FMath::Lerp(StartRadius, 2.0f + (Index % 3), Gather);
				const float StartX = FDesignStyle == 7 ? -95.0f + (Index % 6) * 47.0f : 30.0f + (Index % 7) * 24.0f;
				const float X = FMath::Lerp(StartX, 135.0f - (Index % 6) * 28.0f, Gather);
				const float Length = (FDesignStyle == 7 ? 36.0f + (Index % 4) * 11.0f : 12.0f + (Index % 5) * 4.0f);
				Location = Origin + Direction * (X - Length * .5f) + Radial * Radius;
				const FVector Tangent = -Right * FMath::Sin(Angle) + FVector::UpVector * FMath::Cos(Angle);
				const FVector Axis = FDesignStyle == 7 ? Direction : FMath::Lerp((Direction + Tangent * 1.4f).GetSafeNormal(), Direction, Gather).GetSafeNormal();
				Rotation = FRotationMatrix::MakeFromXZ(Axis, Radial).ToQuat();
				Scale = FVector(Length / 100.0f, FDesignStyle == 7 ? .72f : .42f, FDesignStyle == 7 ? .72f : .42f);
				Envelope = Reveal * FMath::SmoothStep(Stagger, Stagger + .14f, Progress) * (1.0f - FMath::SmoothStep(.77f, .99f, Progress) * .7f);
			}
			else if (!bReleased)
			{
				const int32 Ribbon = Index - Pieces;
				const float Radius = FMath::Lerp(FDesignStyle == 7 ? 44.0f : 90.0f, 10.0f, Pull);
				const float Length = FMath::Lerp(160.0f, 270.0f, Pull);
				Location = Origin + Direction * (165.0f - Length);
				Rotation = Axial * FQuat(FVector::ForwardVector, Ribbon * 2.399963f + Progress * (FDesignStyle == 7 ? 1.5f : 6.0f));
				Scale = FVector(Length / 100.0f, Radius / 40.0f, Radius / 40.0f);
				Envelope = Reveal * (FDesignStyle == 7 ? .24f : .55f) * (1.0f - Pull * .3f);
			}
			if (bReleased && Index < Pieces) { Envelope = 0.0f; }
		}
		Surfaces[Index]->SetWorldLocationAndRotation(Location, Rotation);
		Surfaces[Index]->SetWorldScale3D(Scale);
		Surfaces[Index]->SetVisibility(Envelope > .002f);
		Materials[Index]->SetScalarParameterValue(TEXT("Age"), Age);
		Materials[Index]->SetScalarParameterValue(TEXT("Progress"), Progress);
		Materials[Index]->SetScalarParameterValue(TEXT("Envelope"), Envelope);
	}
}

void ASparrowGatherShot::TickDesignImpact()
{
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Direction).GetSafeNormal();
	const int32 Pieces = DesignPieces(FDesignStyle);
	const int32 Bodies = Pieces + DesignRibbons(FDesignStyle);
	const float Expansion = 1.0f - FMath::Exp(-Age * 13.0f);
	const float Fade = 1.0f - FMath::SmoothStep(.05f, .40f, Age);
	for (int32 Index = 0; Index < Surfaces.Num(); ++Index)
	{
		const bool bPiece = Index < Pieces;
		const float Phase = Index * 2.399963f;
		const FVector Radial = Right * FMath::Cos(Phase) + FVector::UpVector * FMath::Sin(Phase);
		const FVector Axis = (Direction * (Index % 3 == 0 ? 1.0f : -.65f) + Radial).GetSafeNormal();
		const float FacetScale = FDesignStyle == 6 ? .72f : FDesignStyle == 5 ? .58f : 1.0f;
		const float Length = bPiece ? (18.0f + (Index % 4) * 9.0f) * FacetScale : 90.0f + Expansion * 70.0f;
		const FVector Location = Origin + Axis * Expansion * (bPiece ? 90.0f + (Index % 4) * 23.0f : 18.0f) - FVector::UpVector * Age * Age * (bPiece ? 280.0f : 0.0f);
		const FQuat Rotation = bPiece ? FRotationMatrix::MakeFromXZ(Axis, Radial).ToQuat() :
			FRotationMatrix::MakeFromX(-Direction).ToQuat() * FQuat(FVector::ForwardVector, Phase + Age * 4.0f);
		Surfaces[Index]->SetWorldLocationAndRotation(Location, Rotation);
		Surfaces[Index]->SetWorldScale3D(bPiece ? FVector(Length / 100.0f, .8f * FacetScale, .8f * FacetScale) :
			FVector(Length / 100.0f, (20.0f + Expansion * 85.0f) / 40.0f, (20.0f + Expansion * 85.0f) / 40.0f));
		const float Envelope = Index >= Bodies ? 0.0f : Fade * (bPiece ? 1.0f : FDesignStyle == 1 || FDesignStyle == 3 ? .12f : .60f);
		Surfaces[Index]->SetVisibility(Envelope > .002f);
		Materials[Index]->SetScalarParameterValue(TEXT("Age"), Age + .60f);
		Materials[Index]->SetScalarParameterValue(TEXT("Progress"), 1.0f);
		Materials[Index]->SetScalarParameterValue(TEXT("Envelope"), Envelope);
	}
}

void ASparrowGatherShot::Release(ASparrowArrow* Arrow)
{
	TArray<ASparrowArrow*> Arrows;
	Arrows.Add(Arrow);
	ReleaseVolley(Arrows);
}

void ASparrowGatherShot::ReleaseVolley(const TArray<ASparrowArrow*>& Arrows)
{
	// 발사 실패나 취소에서는 성공한 발사처럼 보이는 섬광을 만들지 않는다.
	if (HasReleased()) { return; }
	ASparrowArrow* FirstArrow = nullptr;
	for (ASparrowArrow* Arrow : Arrows)
	{
		if (HarmonyFX.IsValid()) { HarmonyFX->TrackArrow(Arrow); }
		ReleasedArrows.Add(Arrow);
		ReleaseOrigins.Add(IsValid(Arrow) ? Arrow->GetActorLocation() : FVector::ZeroVector);
		if (!FirstArrow && IsValid(Arrow)) { FirstArrow = Arrow; }
	}
	if (!FirstArrow) { Destroy(); return; }
	Origin = FirstArrow->GetActorLocation();
	ReleasedAt = Age;
}

void ASparrowGatherShot::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	if (!Caster.IsValid() || Caster->IsActorBeingDestroyed() || !Caster->GetMesh()) { Destroy(); return; }
	Age += DeltaTime;
	if (bDesignImpact) { TickDesignImpact(); return; }
	const bool bReleased = HasReleased();
	const float Since = bReleased ? Age - ReleasedAt : 100.0f;
	if (bReleased && Since >= .30f) { Destroy(); return; }
	if (!bReleased)
	{
		const USparrowSkillComponent* Skills = Caster->FindComponentByClass<USparrowSkillComponent>();
		Origin = bCrystals && Skills ? Skills->GetArrowOrigin() : Caster->GetMesh()->GetSocketLocation(TEXT("BowEmitterSocket"));
	}
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Direction).GetSafeNormal();
	FVector Normal = FVector::UpVector;
	if (APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(this, 0)) { Normal = Camera->GetCameraLocation() - Origin; }
	const FQuat Facing = FRotationMatrix::MakeFromXZ(Direction, Normal).ToQuat();
	const float Progress = FMath::Clamp(Age / Charge, 0.0f, 1.0f);
	if (HarmonyFX.IsValid())
	{
		for (UStaticMeshComponent* Surface : Surfaces) { Surface->SetVisibility(false); }
		return;
	}
	if (FDesignStyle > 0) { TickDesign(Progress, Since); return; }
	const float Converge = FMath::SmoothStep(.10f, .95f, Progress);
	const float Open = FMath::SmoothStep(0.0f, .13f, Progress);
	const int32 Lanes = bCrystals && bAscended ? 3 : 1;
	const int32 BodyCount = bCrystals ? CrystalFragmentsPerArrow * Lanes : (bAscended ? 14 : 10);
	const int32 MainCount = BodyCount + (bCrystals ? 0 : (bAscended ? 20 : 14));
	for (int32 Index = 0; Index < Surfaces.Num(); ++Index)
	{
		const float Phase = Index * 2.399963f;
		FVector Location = Origin;
		FVector Scale(1.0f);
		FQuat Rotation = Facing;
		float Envelope = 1.0f;
		bool bLaneAlive = true;
		if (bCrystals)
		{
			const bool bFragment = Index < MainCount;
			const bool bAssembly = Index >= MainCount && Index < MainCount + Lanes;
			const int32 Lane = bFragment ? Index / CrystalFragmentsPerArrow : (Index - MainCount) % Lanes;
			const FQuat AxialFacing = FRotationMatrix::MakeFromX(Direction).ToQuat();
			FVector Tip = Origin + CrystalLaneOffset(Lane, bAscended, Right) + Direction * CrystalDisplayLead;
			if (bReleased)
			{
				bLaneAlive = ReleasedArrows.IsValidIndex(Lane) && ReleasedArrows[Lane].IsValid() &&
					!ReleasedArrows[Lane]->IsActorBeingDestroyed();
				if (bLaneAlive)
				{
					Tip = ReleasedArrows[Lane]->GetActorLocation() +
						Direction * (CrystalDisplayLead * (1.0f - FMath::SmoothStep(0.0f, .040f, Since)));
				}
			}
			if (bFragment)
			{
				// 변신도 준비 광면은 한 세트만 펼치고 마지막 압축에서 실제 사격축으로 분리한다.
				const int32 Piece = Index % CrystalFragmentsPerArrow;
				const float Grow = FMath::SmoothStep(.02f, .34f, Progress);
				const float Pull = FMath::SmoothStep(.46f, .91f, Progress);
				if (Piece < CrystalFoldsPerArrow)
				{
					// 원본 반구형 메시의 실제 깊이를 따라 기류가 활 가까이서 생겨 전방으로 말려든다.
					const float ShellLength = FMath::Lerp(52.0f + Grow * (98.0f - Piece * 22.0f), 104.0f, Pull);
					const float Radius = FMath::Lerp(8.0f + Grow * (76.0f - Piece * 18.0f), 5.0f + Piece * 2.0f, Pull);
					const float Nose = FMath::Lerp(30.0f, CrystalDisplayLead, FMath::SmoothStep(.14f, .78f, Progress));
					Location = Origin + Direction * (Nose - ShellLength);
					const float Turn = Piece * 2.094f + Progress * (Piece == 1 ? -.95f : 1.15f);
					Rotation = AxialFacing * FQuat(FVector::ForwardVector, Turn);
					Scale = FVector(ShellLength, Radius, Radius) / CrystalPressureRadius;
					Envelope = FMath::SmoothStep(.02f, .18f, Progress) * (1.0f - FMath::SmoothStep(.84f, 1.0f, Progress)) * (Piece == 0 ? 1.0f : .68f);
					if (bReleased && ReleaseOrigins.IsValidIndex(Lane))
					{
						// 실제 화살이 떠난 뒤 광면의 양옆이 벗겨져 압력과 후류를 남긴다.
						Location = ReleaseOrigins[Lane] - CrystalLaneOffset(Lane, bAscended, Right) - Direction * 35.0f;
						Scale = FVector(120.0f + Since * 420.0f, 14.0f + Since * 380.0f, 14.0f + Since * 380.0f) / CrystalPressureRadius;
						Envelope = Piece == 0 ? (1.0f - FMath::SmoothStep(.015f, .12f, Since)) * .78f : 0.0f;
						bLaneAlive = true;
					}
					if (Lane > 0) { Envelope = 0.0f; }
				}
				else if (Piece == CrystalFoldsPerArrow)
				{
					const float Draw = FMath::SmoothStep(.18f, .90f, Progress);
					const float Length = FMath::Lerp(90.0f, CrystalArrowLength, Draw);
					const float AxialScale = Length / CrystalMeshLength;
					const float Width = bAscended ? 2.35f : 3.0f;
					Location = Tip - Direction * (CrystalMeshTip * AxialScale);
					Rotation = AxialFacing * FRotator(90.0f, 0.0f, 0.0f).Quaternion();
					Scale = FVector(Width, Width, AxialScale);
					Envelope = FMath::SmoothStep(bAscended ? .58f : .18f, bAscended ? .90f : .62f, Progress);
					if (bReleased) { Envelope = 0.0f; }
				}
				else
				{
					const float Side = Piece % 2 == 0 ? -1.0f : 1.0f;
					const FVector Start = Origin - Direction * (55.0f + (Piece % 3) * 18.0f) +
						Right * (Side * (24.0f + Grow * 22.0f)) + FVector::UpVector * (Piece < 6 ? 25.0f : -22.0f);
					const FVector End = Origin + Direction * (20.0f + Pull * 20.0f);
					Location = (Start + End) * .5f;
					Rotation = FRotationMatrix::MakeFromXZ((End - Start).GetSafeNormal(), Normal).ToQuat();
					Scale = FVector(FVector::Distance(Start, End) / 100.0f, .38f, 1.0f);
					Envelope = Open * (1.0f - FMath::SmoothStep(.64f, .90f, Progress)) * .70f;
					if (bReleased || Lane > 0) { Envelope = 0.0f; }
				}
			}
			else if (bAssembly)
			{
				Location = Tip - Direction * CrystalArrowLength;
				Rotation = AxialFacing * FQuat(FVector::ForwardVector, Progress * .85f + Lane * 2.094f);
				const float Width = bAscended ? 26.0f : 37.0f;
				Scale = FVector(CrystalArrowLength, Width, Width) / CrystalPressureRadius;
				Envelope = FMath::SmoothStep(.56f, .90f, Progress);
				if (bReleased) { Envelope = 0.0f; }
			}
			else
			{
				// 넓은 방사형 파편 대신 발사축을 따라 짧은 압력이 빠진다.
				Location = bReleased && ReleaseOrigins.IsValidIndex(Lane) ?
					ReleaseOrigins[Lane] - CrystalLaneOffset(Lane, bAscended, Right) : Tip;
				Location += Direction * 35.0f;
				Scale = FVector(2.8f, 1.5f, 1.0f);
				Envelope = bReleased ? .70f : 0.0f;
				if (Lane > 0) { Envelope = 0.0f; }
				if (bReleased) { bLaneAlive = true; }
			}
		}
		else if (Index >= MainCount)
		{
			Location += Direction * (Index == MainCount ? 15.0f : 40.0f);
			Rotation = Index == MainCount ? Facing : FRotationMatrix::MakeFromXZ(Right, Direction).ToQuat();
			Scale = FVector(3.4f, 3.0f, 1.0f);
		}
		else if (Index < BodyCount)
		{
			const FVector Radial = Right * FMath::Cos(Phase) + FVector::UpVector * FMath::Sin(Phase);
			const FVector Start = Origin - Direction * (90.0f + (Index % 4) * 20.0f) + Radial * (100.0f + (Index % 3) * 30.0f);
			const FVector End = Origin + Direction * 18.0f;
			const float Pull = bReleased ? .96f : Converge * .67f;
			const FVector Tail = FMath::Lerp(Start, End, Pull);
			const FVector Axis = (End - Tail).GetSafeNormal();
			Location = (Tail + End) * .5f;
			Rotation = FRotationMatrix::MakeFromXZ(Axis, Normal).ToQuat();
			Scale = FVector(FMath::Max(12.0f, FVector::Distance(Tail, End)) / 100.0f, .50f + (Index % 3) * .13f, 1.0f);
		}
		else
		{
			const float Radius = (95.0f + (Index % 5) * 15.0f) * (1.0f - Converge * .9f);
			Location += Right * FMath::Cos(Phase) * Radius + FVector::UpVector * FMath::Sin(Phase) * Radius * .7f;
			Location += Direction * (-45.0f + (Index % 4) * 23.0f);
			if (bReleased) { Location += Right * FMath::Cos(Phase) * Since * 370.0f + Direction * Since * 520.0f; }
			Scale = FVector(.29f + (Index % 3) * .06f);
		}
		Surfaces[Index]->SetWorldLocationAndRotation(Location, Rotation);
		Surfaces[Index]->SetWorldScale3D(Scale);
		Surfaces[Index]->SetVisibility(Age > .005f && bLaneAlive && Envelope > .001f &&
			(Index >= MainCount || !bReleased || Since < .18f));
		Materials[Index]->SetScalarParameterValue(TEXT("Envelope"), Envelope);
		Materials[Index]->SetScalarParameterValue(TEXT("Age"), Progress * .38f);
		Materials[Index]->SetScalarParameterValue(TEXT("Progress"), Progress);
		Materials[Index]->SetScalarParameterValue(TEXT("ShotAge"), bCrystals && bReleased ? Since * 1.5f : Since);
	}
}
