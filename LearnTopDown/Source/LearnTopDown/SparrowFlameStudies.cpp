#include "SparrowFlameStudies.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/Material.h"
#include "Particles/ParticleSystemComponent.h"
#include "SparrowArrow.h"
#include "SparrowAscension.h"
#include "TopDownCombatCharacter.h"

namespace
{
	TAutoConsoleVariable<int32> CVarDFlameStudy(TEXT("Sparrow.FlameStudy.D"), 0,
		TEXT("D visual studies: 0 installed, 1 feather lance, 2 burning screw wake, 3 shard pressure shot."));
	TAutoConsoleVariable<int32> CVarVFlameStudy(TEXT("Sparrow.FlameStudy.V"), 3,
		TEXT("V presentation: 3 adopted shoulder/arm flame crests; 0 legacy wings, 1 mantle, 2 detached corona."));
	TAutoConsoleVariable<int32> CVarVDesign(TEXT("Sparrow.DesignIngame.V"), 7,
		TEXT("V entry preview: 0 installed, 1 soft gold column, 2 descending silk, 3 solar corona, 4 uninterrupted ray then rough column, 5 dawn revelation, 6 grounded V4 with staged release, 7 axis-centred gold pressure and natural reveal."));
}

int32 ASparrowFlameStudies::GetDPreview() { return FMath::Clamp(CVarDFlameStudy.GetValueOnGameThread(), 0, 3); }
int32 ASparrowFlameStudies::GetVPreview() { return FMath::Clamp(CVarVFlameStudy.GetValueOnGameThread(), 0, 3); }
int32 ASparrowFlameStudies::GetVDesignPreview() { return FMath::Clamp(CVarVDesign.GetValueOnGameThread(), 0, 7); }

ASparrowFlameStudies::ASparrowFlameStudies()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickGroup = TG_PostPhysics;
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
	SetActorEnableCollision(false);
	SetCanBeDamaged(false);
	Tags.Append({TEXT("SparrowSkillFX"), TEXT("SparrowFlameStudy")});
}

bool ASparrowFlameStudies::AddSurface(const TCHAR* MaterialName, int32 Index, bool bCylinder)
{
	UStaticMesh* Plane = LoadObject<UStaticMesh>(nullptr, bCylinder ? TEXT("/Engine/BasicShapes/Cylinder.Cylinder") : TEXT("/Engine/BasicShapes/Plane.Plane"));
	UMaterialInterface* Source = LoadObject<UMaterialInterface>(nullptr, *FString::Printf(
		TEXT("/Game/TopDown/Characters/Sparrow/Previews/FlameStudies20261026/M_%s.M_%s"), MaterialName, MaterialName));
	if (!Plane || !Source) { return false; }
	UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(Source, this);
	if (!Material) { return false; }
	Material->SetScalarParameterValue(TEXT("Index"), static_cast<float>(Index));
	Material->SetScalarParameterValue(TEXT("ShotAge"), 100.0f);
	Material->SetScalarParameterValue(TEXT("Strength"), 0.0f);
	UStaticMeshComponent* Part = NewObject<UStaticMeshComponent>(this, NAME_None, RF_Transient);
	Part->SetupAttachment(RootComponent);
	Part->SetMobility(EComponentMobility::Movable);
	Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Part->SetGenerateOverlapEvents(false);
	Part->SetCanEverAffectNavigation(false);
	Part->SetCastShadow(false);
	Part->SetReceivesDecals(false);
	Part->SetStaticMesh(Plane);
	Part->SetMaterial(0, Material);
	Part->SetVisibility(false);
	Part->ComponentTags.Add(TEXT("SparrowFlameStudySurface"));
	AddInstanceComponent(Part);
	Part->RegisterComponent();
	Surfaces.Add(Part);
	Materials.Add(Material);
	return true;
}

bool ASparrowFlameStudies::AddDesignSurface(const TCHAR* MeshName, const TCHAR* MaterialName, int32 Index)
{
	const TCHAR* Folder = TEXT("/Game/TopDown/Characters/Sparrow/Previews/QVDesign20261027");
	UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *FString::Printf(TEXT("%s/%s.%s"), Folder, MeshName, MeshName));
	UMaterialInterface* Source = LoadObject<UMaterialInterface>(nullptr, *FString::Printf(TEXT("%s/M_%s.M_%s"), Folder, MaterialName, MaterialName));
	if (!Mesh || !Source) { return false; }
	UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(Source, this);
	Material->SetScalarParameterValue(TEXT("Index"), Index);
	Material->SetScalarParameterValue(TEXT("Style"), VDesign);
	if (VDesign == 6) { Material->SetScalarParameterValue(TEXT("Style"), 4.0f); }
	Material->SetScalarParameterValue(TEXT("Envelope"), 0.0f);
	UStaticMeshComponent* Part = NewObject<UStaticMeshComponent>(this, NAME_None, RF_Transient);
	Part->SetupAttachment(RootComponent);
	Part->SetMobility(EComponentMobility::Movable);
	Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Part->SetGenerateOverlapEvents(false);
	Part->SetCanEverAffectNavigation(false);
	Part->SetCastShadow(false);
	Part->SetReceivesDecals(false);
	Part->SetStaticMesh(Mesh);
	Part->SetMaterial(0, Material);
	Part->SetVisibility(false);
	Part->ComponentTags.Append({TEXT("SparrowVDesignSurface"), FName(MaterialName)});
	AddInstanceComponent(Part);
	Part->RegisterComponent();
	Surfaces.Add(Part);
	Materials.Add(Material);
	return true;
}

bool ASparrowFlameStudies::InitializeD(ATopDownCombatCharacter* Character, const FVector& Aim, float ChargeSeconds)
{
	Design = GetDPreview();
	if (!IsValid(Character) || !Character->GetMesh() || Design == 0 || GetOwner() != Character) { return false; }
	Caster = Character;
	Direction = (Aim - Character->GetActorLocation()).GetSafeNormal2D();
	if (Direction.IsNearlyZero()) { return false; }
	Charge = FMath::Max(.1f, ChargeSeconds);
	Origin = Head = Character->GetMesh()->GetSocketLocation(TEXT("BowEmitterSocket"));
	Tags.Add(TEXT("SparrowDFlameStudy"));
	for (int32 Index = 0; Index < 23; ++Index)
	{
		const TCHAR* Material = Index == 22 ? TEXT("FlameShotBurst") : Design == 1 ? TEXT("FlameFeather") :
			Design == 2 ? (Index < 3 ? TEXT("FlameSpiral") : TEXT("FlameWake")) : TEXT("FlameShard");
		if (!AddSurface(Material, Index)) { return false; }
	}
	SetLifeSpan(Charge + 1.4f);
	return true;
}

bool ASparrowFlameStudies::InitializeV(ATopDownCombatCharacter* Character, ASparrowAscensionWings* NativeForm)
{
	Design = GetVPreview();
	VDesign = GetVDesignPreview();
	if (VDesign > 0) { Design = 3; }
	if (!IsValid(Character) || !Character->GetMesh() || !IsValid(NativeForm) || Design == 0 || GetOwner() != Character) { return false; }
	Caster = Character;
	Form = NativeForm;
	bForm = true;
	Origin = Character->GetMesh()->GetComponentLocation() + FVector::UpVector * 12.0f;
	if (VDesign >= 6)
	{
		UpdateVGroundAnchor();
		UE_LOG(LogTemp, Log, TEXT("Sparrow V6 ground mesh=%s anchor=%s normal=%s"),
			*Character->GetMesh()->GetComponentLocation().ToString(), *Origin.ToString(), *EntryGroundNormal.ToString());
	}
	Tags.Add(TEXT("SparrowVFlameStudy"));
	AddTickPrerequisiteActor(NativeForm);
	const int32 MainCount = Design == 1 ? 7 : Design == 2 ? 5 : 6;
	for (int32 Index = 0; Index < MainCount + 10; ++Index)
	{
		const TCHAR* Material = Index >= MainCount ? TEXT("FlameEmber") :
			Design == 1 ? TEXT("FlameMantle") : Design == 2 ? TEXT("FlameCorona") : TEXT("FlameCrest");
		if (!AddSurface(Material, Index)) { return false; }
	}
	if (Design == 3)
	{
		EntryStart = Surfaces.Num();
		if (VDesign > 0)
		{
			Tags.Add(FName(*FString::Printf(TEXT("SparrowVDesign%d"), VDesign)));
			for (int32 Index = 0; Index < 12; ++Index)
			{
				if (VDesign == 7)
				{
					const TCHAR* Meshes[] = {TEXT("SM_QVLightRibbon"), TEXT("SM_QVLightRibbon"),
						TEXT("SM_QVLightRibbon"), TEXT("SM_QVLightRibbon"), TEXT("SM_QVCelestialDisc"),
						TEXT("SM_QVContactBillow"), TEXT("SM_QVContactSpray"), TEXT("SM_QVGroundFray"),
						TEXT("SM_QVLightRibbon"), TEXT("SM_QVLightRibbon"), TEXT("SM_QVLightRibbon"), TEXT("SM_QVLightRibbon")};
					const TCHAR* Parts[] = {TEXT("PlumeCore"), TEXT("PlumeCore"), TEXT("PlumeVeil"), TEXT("PlumeVeil"),
						TEXT("PlumeContact"), TEXT("PlumeBurst"), TEXT("PlumeSparks"), TEXT("VReveal"),
						TEXT("PlumeTip"), TEXT("PlumeVeil"), TEXT("PlumeVeil"), TEXT("PlumeVeil")};
					if (!AddDesignSurface(Meshes[Index], Parts[Index], Index)) { return false; }
					continue;
				}
				if (VDesign == 5)
				{
					const TCHAR* Meshes[] = {TEXT("SM_QVStraightVolume"), TEXT("SM_QVStraightVolume"),
						TEXT("SM_QVDawnCurtains"), TEXT("SM_QVDawnCurtains"), TEXT("SM_QVDawnShock"), TEXT("SM_QVCelestialDisc"),
						TEXT("SM_QVContactSpray"), TEXT("SM_QVDawnShock"), TEXT("SM_QVCelestialDisc"), TEXT("SM_QVContactSpray"),
						TEXT("SM_QVContactBillow"), TEXT("SM_QVGroundFray")};
					const TCHAR* Parts[] = {TEXT("VPrimeRay"), TEXT("DawnVCore"), TEXT("DawnVCurtains"), TEXT("DawnVCurtains"),
						TEXT("DawnShock"), TEXT("DawnPool"), TEXT("DawnSparks"), TEXT("DawnShock"), TEXT("DawnPool"),
						TEXT("DawnSparks"), TEXT("CelestialPlume"), TEXT("VReveal")};
					if (!AddDesignSurface(Meshes[Index], Parts[Index], Index)) { return false; }
					continue;
				}
				if (VDesign == 4 || VDesign == 6)
				{
					const TCHAR* MeshName = Index == 9 ? TEXT("SM_QVCelestialDisc") : Index == 10 ? TEXT("SM_QVContactBillow") :
						Index == 11 ? TEXT("SM_QVGroundFray") : TEXT("SM_QVStraightVolume");
					const bool bAnchored = VDesign == 6;
					const TCHAR* Material = Index == 0 ? (bAnchored ? TEXT("V4GroundedRay") : TEXT("VPrimeRay")) :
						Index < 9 ? (bAnchored ? TEXT("V4GroundedColumn") : TEXT("VCelestialColumn")) :
						Index == 9 ? (bAnchored ? TEXT("VAnchoredContact") : TEXT("CelestialPool")) :
						Index == 10 ? TEXT("CelestialPlume") : TEXT("VReveal");
					if (!AddDesignSurface(MeshName, Material, Index)) { return false; }
					continue;
				}
				const TCHAR* MeshName = Index == 9 || Index == 11 ? TEXT("SM_QVGroundFray") : Index == 10 ?
					TEXT("SM_QVFlameCrown") : TEXT("SM_QVFluxFold");
				const TCHAR* Material = Index == 0 ? TEXT("VPrelude") : Index < 9 ? TEXT("VColumn") : Index == 9 ?
					TEXT("Contact") : Index == 10 ? TEXT("Burst") : Index == 11 ? TEXT("VReveal") : TEXT("VWingFlow");
				if (!AddDesignSurface(MeshName, Material, Index)) { return false; }
			}
		}
		else
		{
		const TCHAR* EntryMaterials[] = {TEXT("VEntryColumn"), TEXT("VEntryImpact"), TEXT("VEntryScatter"),
			TEXT("VRevealFlash"), TEXT("VEntryShaft"), TEXT("VEntryPrelude")};
		for (int32 Index = 0; Index < UE_ARRAY_COUNT(EntryMaterials); ++Index)
		{
			if (!AddSurface(EntryMaterials[Index], EntryStart + Index, Index == 0)) { return false; }
			Surfaces.Last()->ComponentTags.Add(TEXT("SparrowVEntrySurface"));
		}
		}
	}
	// 채택한 V3는 Serath 원본 날개 모션을 가리지 않고 주변 화염 질감만 보탠다.
	if (Design != 3) { HideForStudy(NativeForm->GetWingMesh()); }
	return true;
}

bool ASparrowFlameStudies::InitializeDCharge(ATopDownCombatCharacter* Character, const FVector& Aim, float ChargeSeconds)
{
	if (!IsValid(Character) || !Character->GetMesh() || GetOwner() != Character) { return false; }
	Caster = Character;
	Direction = (Aim - Character->GetActorLocation()).GetSafeNormal2D();
	if (Direction.IsNearlyZero()) { return false; }
	Origin = Character->GetMesh()->GetSocketLocation(TEXT("BowEmitterSocket"));
	Charge = FMath::Max(.05f, ChargeSeconds);
	Design = 4;
	Tags.Add(TEXT("SparrowDChargeFX"));
	for (int32 Index = 0; Index < 10; ++Index)
	{
		const TCHAR* Material = Index < 8 ? TEXT("DChargeVane") : Index == 8 ? TEXT("DChargeCore") : TEXT("DChargeRelease");
		if (!AddSurface(Material, Index)) { return false; }
		Surfaces.Last()->ComponentTags.Add(TEXT("SparrowDChargeSurface"));
	}
	SetLifeSpan(Charge + .40f);
	return true;
}

ASparrowFlameStudies* ASparrowFlameStudies::FindActiveForm(ATopDownCombatCharacter* Character)
{
	if (!IsValid(Character) || !Character->GetWorld()) { return nullptr; }
	for (TActorIterator<ASparrowFlameStudies> It(Character->GetWorld()); It; ++It)
	{
		if (It->bForm && It->Design == 3 && It->Caster.Get() == Character && It->Form.IsValid() &&
			!It->Form->IsActorBeingDestroyed() && !It->IsActorBeingDestroyed()) { return *It; }
	}
	return nullptr;
}

bool ASparrowFlameStudies::BeginFormFold(const FVector& Aim, float ChargeSeconds)
{
	if (!bForm || Design != 3 || !Caster.IsValid()) { return false; }
	FoldDirection = (Aim - Caster->GetActorLocation()).GetSafeNormal2D();
	if (FoldDirection.IsNearlyZero()) { return false; }
	FoldStartedAt = Age;
	FoldReleasedAt = -1.0f;
	FoldDuration = FMath::Max(.05f, ChargeSeconds);
	return true;
}

void ASparrowFlameStudies::ReleaseFormFold()
{
	if (FoldStartedAt >= 0.0f && FoldReleasedAt < 0.0f) { FoldReleasedAt = Age; }
}

void ASparrowFlameStudies::CancelFormFold()
{
	FoldStartedAt = FoldReleasedAt = -1.0f;
	FoldAmount = 0.0f;
}

void ASparrowFlameStudies::HideForStudy(UPrimitiveComponent* Part)
{
	if (!IsValid(Part)) { return; }
	if (!HiddenParts.Contains(Part))
	{
		HiddenParts.Add(Part);
		OriginalVisibility.Add(Part->IsVisible());
	}
	Part->SetVisibility(false);
}

void ASparrowFlameStudies::Release(ASparrowArrow* Arrow)
{
	if (HasReleased() || bForm) { return; }
	if (!IsValid(Arrow)) { Destroy(); return; }
	Projectile = Arrow;
	Origin = Head = Arrow->GetActorLocation();
	Direction = Arrow->GetFlightDirection();
	ReleasedAt = Age;
	Arrow->OnDestroyed.AddDynamic(this, &ASparrowFlameStudies::OnProjectileDestroyed);
	AddTickPrerequisiteActor(Arrow);
	TArray<UPrimitiveComponent*> Parts;
	Arrow->GetComponents(Parts);
	if (Design != 4) { for (UPrimitiveComponent* Part : Parts) { HideForStudy(Part); } }
}

void ASparrowFlameStudies::OnProjectileDestroyed(AActor* DestroyedActor)
{
	// 화살 Tick은 충돌/사거리 끝 위치를 먼저 저장하고 Destroy한다. 마지막 한 프레임의 경로도 보존한다.
	if (!DestroyedActor) { return; }
	Head = DestroyedActor->GetActorLocation();
	Travelled = FMath::Max(0.0f, FVector::DotProduct(Head - Origin, Direction));
}

FQuat ASparrowFlameStudies::Face(const FVector& Axis, const FVector& Position) const
{
	FVector Normal = FVector::UpVector;
	if (APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(this, 0)) { Normal = Camera->GetCameraLocation() - Position; }
	return FRotationMatrix::MakeFromXZ(Axis, Normal).ToQuat();
}

void ASparrowFlameStudies::SetSurface(int32 Index, const FVector& Position, const FQuat& Rotation, const FVector& Scale, float Opacity)
{
	Surfaces[Index]->SetWorldLocationAndRotation(Position, Rotation);
	Surfaces[Index]->SetWorldScale3D(Scale);
	Surfaces[Index]->SetVisibility(Opacity > .001f);
	Materials[Index]->SetScalarParameterValue(TEXT("Age"), Age);
	Materials[Index]->SetScalarParameterValue(TEXT("Progress"), FMath::Clamp(Age / Charge, 0.0f, 1.0f));
	Materials[Index]->SetScalarParameterValue(TEXT("ShotAge"), HasReleased() ? Age - ReleasedAt : 100.0f);
	Materials[Index]->SetScalarParameterValue(TEXT("Strength"), Opacity);
}

void ASparrowFlameStudies::DrawD()
{
	if (Design == 4) { DrawDCharge(); return; }
	const bool Fired = HasReleased();
	const float Since = Fired ? Age - ReleasedAt : 0.0f;
	if (!Fired) { Origin = Head = Caster->GetMesh()->GetSocketLocation(TEXT("BowEmitterSocket")); }
	if (Projectile.IsValid())
	{
		Head = Projectile->GetActorLocation();
		Travelled = FVector::DotProduct(Head - Origin, Direction);
	}
	const float Compress = FMath::SmoothStep(.12f, .97f, FMath::Clamp(Age / Charge, 0.0f, 1.0f));
	const float Open = FMath::SmoothStep(0.0f, .10f, Age);
	const float TrailFade = Fired ? 1.0f - FMath::SmoothStep(.40f, .80f, Since) : 1.0f;
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Direction).GetSafeNormal();
	for (int32 Index = 0; Index < 22; ++Index)
	{
		FVector Position = Origin;
		FVector Scale(1.0f);
		FQuat Rotation = Face(Direction, Origin);
		float Strength = Open;
		const float Phase = Index * 2.399963f;
		const FVector Radial = Right * FMath::Cos(Phase) + FVector::UpVector * FMath::Sin(Phase);
		if (Design == 1)
		{
			if (Index < 8)
			{
				const float Radius = Fired ? 14.0f : (70.0f + (Index % 3) * 14.0f) * (1.0f - Compress * .83f);
				Position = (Fired ? Head : Origin + Direction * 50.0f) + Radial * Radius - Direction * (Index % 3) * 19.0f;
				Rotation = Face(Direction + Radial * (Fired ? .05f : (1.0f - Compress) * .75f), Position);
				Scale = FVector(Fired ? 2.20f : 1.40f, .48f + (Index % 3) * .12f, 1.0f);
				Strength *= Fired ? (Projectile.IsValid() ? 1.0f : FMath::Clamp(1.0f - Since * 3.0f, 0.0f, 1.0f)) : 1.0f;
			}
			else
			{
				const float Dist = (Index - 7) * 75.0f;
				const float LocalAge = Since - Dist / 6500.0f;
				Position = Origin + Direction * Dist + Right * FMath::Sin(Phase) * (15.0f + FMath::Max(0.0f, LocalAge) * 70.0f);
				Position += FVector::UpVector * (FMath::Cos(Phase) * 15.0f + FMath::Max(0.0f, LocalAge) * 42.0f);
				Rotation = Face(Direction + Right * FMath::Sin(Phase) * .42f + FVector::UpVector * .2f, Position);
				Scale = FVector(.95f, .42f, 1.0f);
				Strength = Fired && Travelled >= Dist ? TrailFade * (1.0f - FMath::SmoothStep(.10f, .63f, LocalAge)) : 0.0f;
			}
		}
		else if (Design == 2)
		{
			if (Index < 3)
			{
				Position = (Fired ? Head : Origin + Direction * 55.0f) - Direction * 45.0f;
				Rotation = Face(Direction, Position) * FQuat(FVector::ForwardVector, Index * PI / 3.0f + Age * 3.0f);
				Scale = FVector(2.6f, 1.55f - (Fired ? 0.0f : Compress * .45f), 1.0f);
				Strength *= Fired ? (Projectile.IsValid() ? 1.0f : FMath::Clamp(1.0f - Since * 3.5f, 0.0f, 1.0f)) : 1.0f;
			}
			else
			{
				const float Dist = (Index - 2) * 55.0f;
				const float LocalAge = Since - Dist / 6500.0f;
				Position = Origin + Direction * Dist + Radial * (20.0f + FMath::Max(0.0f, LocalAge) * 23.0f);
				Rotation = Face(Direction, Position) * FQuat(FVector::ForwardVector, Phase - Age * 2.0f);
				Scale = FVector(1.1f, .80f, 1.0f);
				Strength = Fired && Travelled >= Dist ? TrailFade * .9f : 0.0f;
			}
		}
		else
		{
			const float Radius = (75.0f + (Index % 5) * 14.0f) * (1.0f - Compress * .93f);
			if (!Fired)
			{
				Position = Origin + Direction * (30.0f + (Index % 4) * 12.0f) + Radial * Radius;
				Rotation = Face(Direction * .7f - Radial * (1.0f - Compress), Position);
				Scale = FVector(.50f + (Index % 4) * .10f, .14f + (Index % 3) * .04f, 1.0f);
			}
			else
			{
				if (Index < 2)
				{
					Position = Head - Direction * 55.0f;
					Rotation = Face(Direction, Position) * FQuat(FVector::ForwardVector, Index * PI * .5f);
					Scale = FVector(2.35f, .31f, 1.0f);
					Strength = Projectile.IsValid() ? 1.0f : 0.0f;
				}
				else
				{
					const float Dist = (Index / 4 + 1) * 160.0f;
					Position = Origin + Direction * FMath::Min(Dist, Travelled) + Radial * (16.0f + Since * (90.0f + Index * 2.0f));
					Rotation = Face(Direction + Radial * .18f, Position);
					Scale = FVector(1.30f - Since * .55f, .30f, 1.0f);
					Strength = Travelled >= Dist ? TrailFade * (1.0f - FMath::SmoothStep(.08f, .52f, Since)) : 0.0f;
				}
			}
		}
		SetSurface(Index, Position, Rotation, Scale, Strength);
	}
	SetSurface(22, Origin + Direction * 15.0f, Face(Direction, Origin), FVector(3.4f, Design == 3 ? 3.4f : 2.4f, 1.0f),
		Fired ? (1.0f - FMath::SmoothStep(.08f, .27f, Since)) : Compress * .20f);
}

void ASparrowFlameStudies::DrawV()
{
	if (FoldStartedAt >= 0.0f)
	{
		FoldAmount = FoldReleasedAt >= 0.0f ? 1.0f - FMath::SmoothStep(.015f, .24f, Age - FoldReleasedAt) :
			FMath::SmoothStep(.08f, .98f, (Age - FoldStartedAt) / FoldDuration);
		if ((FoldReleasedAt >= 0.0f && Age - FoldReleasedAt >= .24f) || Age - FoldStartedAt > FoldDuration + .50f) { CancelFormFold(); }
	}
	if (Design != 3) { HideForStudy(Form->GetWingMesh()); }
	TArray<UParticleSystemComponent*> NativeParticles;
	Form->GetComponents(NativeParticles);
	for (UParticleSystemComponent* Part : NativeParticles)
	{
		if (Design != 3 && Part->ComponentHasTag(TEXT("SparrowAscensionEntry"))) { HideForStudy(Part); }
	}
	USkeletalMeshComponent* Mesh = Caster->GetMesh();
	const FVector Right = Caster->GetActorRightVector();
	const FVector Forward = Caster->GetActorForwardVector();
	const FVector Spine = Mesh->GetSocketLocation(TEXT("spine_03"));
	const float Envelope = FMath::SmoothStep(Design == 3 ? 1.16f : 0.0f, Design == 3 ? 1.34f : .24f, Age) * FMath::SmoothStep(0.0f, .35f, Form->GetRemainingSeconds());
	const int32 MainCount = Design == 3 ? 6 : Design == 2 ? 5 : 7;
	for (int32 Index = 0; Index < MainCount + 10; ++Index)
	{
		FVector Position = Spine;
		FVector Axis = FVector::UpVector;
		FVector Scale(1.0f);
		float Strength = Envelope;
		const float Phase = Index * 2.399963f;
		if (Index >= MainCount)
		{
			const float T = FMath::Frac(Age * (.35f + (Index % 4) * .06f) + Index * .173f);
			Position += Right * FMath::Sin(Phase + T) * (50.0f + (Index % 3) * 13.0f) - Forward * (20.0f + (Index % 4) * 12.0f);
			Position += FVector::UpVector * (-35.0f + T * 135.0f);
			Scale = FVector(.23f + T * .11f, .18f, 1.0f);
			Strength *= FMath::Sin(T * PI);
		}
		else if (Design == 1)
		{
			// 몸 둘레의 서로 다른 높이의 화염이 위로 흘러 외투처럼 움직인다.
			const float Angle = Index * TWO_PI / 7.0f + FMath::Sin(Age * .6f) * .18f;
			if (Index < 3)
			{
				Position += Right * (Index - 1) * 45.0f - Forward * 30.0f + FVector::UpVector * (48.0f + (Index % 2) * 15.0f);
				Axis = (FVector::UpVector + Right * ((Index - 1) * .15f + FMath::Sin(Age * 1.1f + Index) * .06f)).GetSafeNormal();
				Scale = FVector(Index == 1 ? 3.05f : 2.65f, 1.02f, 1.0f);
				Strength *= 1.15f;
			}
			else
			{
				Position += Right * FMath::Sin(Angle) * 43.0f - Forward * FMath::Cos(Angle) * 36.0f;
				Position += FVector::UpVector * (-24.0f + (Index % 3) * 12.0f);
				Axis = (FVector::UpVector + Right * FMath::Sin(Angle) * .18f).GetSafeNormal();
				Scale = FVector(1.65f + (Index % 3) * .12f, .80f, 1.0f);
				Strength *= .80f;
			}
		}
		else if (Design == 2)
		{
			// 원판 대신 분리된 불꽃 덩어리가 서로 다른 속도로 등 뒤를 공전한다.
			// 세 큰 불꽃과 두 작은 불꽃의 크기/궤도를 분리해 원주가 이어지지 않게 한다.
			const float Starts[] = {.20f, 2.15f, 4.35f, 1.32f, 5.55f};
			const float Angle = Starts[Index] + Age * (.18f + (Index % 3) * .08f);
			const float Radius = 98.0f + (Index % 3) * 24.0f + FMath::Sin(Age * 1.4f + Index) * 12.0f;
			Position -= Forward * 57.0f;
			Position += Right * FMath::Cos(Angle) * Radius + FVector::UpVector * (43.0f + FMath::Sin(Angle) * Radius * .78f);
			Axis = (Right * (-FMath::Sin(Angle) * .70f) + FVector::UpVector * (.58f + FMath::Cos(Angle) * .56f)).GetSafeNormal();
			Scale = Index < 3 ? FVector(1.65f + Index * .12f, .92f, 1.0f) : FVector(.69f, .42f, 1.0f);
			Strength *= Index < 3 ? 1.18f : .78f;
		}
		else
		{
			const TCHAR* Bones[] = {TEXT("upperarm_l"), TEXT("upperarm_r"), TEXT("lowerarm_l"), TEXT("lowerarm_r"), TEXT("hand_l"), TEXT("hand_r")};
			Position = Mesh->DoesSocketExist(Bones[Index]) ? Mesh->GetSocketLocation(Bones[Index]) : Spine;
			const float Side = Index % 2 == 0 ? -1.0f : 1.0f;
			Position += FVector::UpVector * (Index < 2 ? 42.0f : 17.0f) + Right * Side * (Index < 2 ? 32.0f : 17.0f);
			Axis = (FVector::UpVector + Right * Side * (Index < 2 ? .62f : .34f) - Forward * .18f).GetSafeNormal();
			Scale = FVector(Index < 2 ? 1.86f : 1.02f, Index < 2 ? .96f : .58f, 1.0f);
			Strength *= Index < 2 ? .40f : .32f;
			if (FoldAmount > 0.0f)
			{
				const FVector Muzzle = Mesh->GetSocketLocation(TEXT("BowEmitterSocket"));
				const FVector FoldRight = FVector::CrossProduct(FVector::UpVector, FoldDirection).GetSafeNormal();
				const float Pair = static_cast<float>(Index / 2);
				const FVector FoldPosition = Muzzle + FoldDirection * (38.0f + Pair * 34.0f) + FoldRight * Side * (6.0f + Pair * 5.0f) + FVector::UpVector * (12.0f + Pair * 4.0f);
				const FVector FoldAxis = (FoldDirection + FoldRight * Side * .035f + FVector::UpVector * .08f).GetSafeNormal();
				Position = FMath::Lerp(Position, FoldPosition, FoldAmount);
				Axis = FMath::Lerp(Axis, FoldAxis, FoldAmount).GetSafeNormal();
				Scale.X *= FMath::Lerp(1.0f, .90f, FoldAmount);
				Scale.Y *= FMath::Lerp(1.0f, .72f, FoldAmount);
			}
		}
		SetSurface(Index, Position, Face(Axis, Position), Scale, Strength);
	}
	if (EntryStart != INDEX_NONE) { if (VDesign > 0) { DrawVDesign(); } else { DrawVEntry(); } }
}

void ASparrowFlameStudies::DrawVEntry()
{
	// 긴 진입광은 시전 지점에 남고, 이동 제어는 원래 스킬 회복 시각에 풀린다.
	if (Age >= 2.01f)
	{
		for (int32 Index = EntryStart; Index < Surfaces.Num(); ++Index) { Surfaces[Index]->SetVisibility(false); }
		return;
	}
	const FVector Base = Origin;
	const float Height = 1050.0f;
	const float Radius = 160.0f;
	// 가는 전조는 0.50초 동안 높이별로 끊어진다. 큰 기둥은 0.66초 착탄, 1.16초 날개 전개다.
	const float Descent = FMath::SmoothStep(.54f, .66f, Age);
	const float TipHeight = Height * (1.0f - Descent);
	const FVector Center = Base + FVector::UpVector * (TipHeight + Height * .5f);
	const float Beam = FMath::SmoothStep(.54f, .555f, Age) * (1.0f - FMath::SmoothStep(1.04f, 1.29f, Age));
	Materials[EntryStart]->SetScalarParameterValue(TEXT("HalfHeight"), Height * .5f);
	SetSurface(EntryStart, Center, FQuat::Identity, FVector(Radius / 50.0f, Radius / 50.0f, Height / 100.0f), Beam);
	const float Hit = FMath::SmoothStep(.65f, .665f, Age) * (1.0f - FMath::SmoothStep(1.12f, 1.61f, Age));
	const float Expansion = 1.0f + FMath::SmoothStep(.66f, 1.10f, Age) * .48f;
	SetSurface(EntryStart + 1, Base, FQuat::Identity, FVector(5.8f, 5.8f, 1.0f) * Expansion, Hit);
	SetSurface(EntryStart + 2, Base + FVector::UpVector * 2.0f, FQuat::Identity, FVector(7.4f, 7.4f, 1.0f), Hit);
	const FVector CharacterCenter = Caster->GetMesh()->GetComponentLocation() + FVector::UpVector * 92.0f;
	const float Reveal = FMath::SmoothStep(1.155f, 1.175f, Age) * (1.0f - FMath::SmoothStep(1.24f, 1.54f, Age));
	SetSurface(EntryStart + 3, CharacterCenter, Face(FVector::UpVector, CharacterCenter), FVector(4.1f, 4.8f, 1.0f), Reveal);
	// 전조 소멸은 재질의 높이별 분절이 담당한다. 전체 페이드로 이 움직임을 덮지 않는다.
	const float Prelude = Age < .50f ? FMath::SmoothStep(.0f, .025f, Age) : 0.0f;
	const float ThinTip = Height * (1.0f - FMath::SmoothStep(.0f, .08f, Age));
	const FVector ThinCenter = Base + FVector::UpVector * (ThinTip + Height * .5f);
	SetSurface(EntryStart + 4, ThinCenter, Face(-FVector::UpVector, ThinCenter), FVector(Height / 100.0f, .60f, 1.0f), Prelude);
	const float PreludeContact = FMath::SmoothStep(.075f, .10f, Age) * (1.0f - FMath::SmoothStep(.34f, .50f, Age));
	SetSurface(EntryStart + 5, Base, FQuat::Identity, FVector(2.5f, 2.5f, 1.0f), PreludeContact);
}

void ASparrowFlameStudies::DrawVDesign()
{
	if (VDesign == 7) { DrawPlumeV(); return; }
	if (VDesign == 5) { DrawRenaissanceV(); return; }
	if (VDesign == 4 || VDesign == 6) { DrawCelestialV(); return; }
	if (Age >= 2.08f)
	{
		for (int32 Index = EntryStart; Index < Surfaces.Num(); ++Index) { Surfaces[Index]->SetVisibility(false); }
		return;
	}
	const FVector Base = Origin;
	const FVector Right = Caster->GetActorRightVector();
	const FVector Forward = Caster->GetActorForwardVector();
	const FVector Spine = Caster->GetMesh()->GetSocketLocation(TEXT("spine_03"));
	const float Height = 1010.0f;
	const float Tip = Height * (1.0f - FMath::SmoothStep(.54f, .66f, Age));
	const float Column = FMath::SmoothStep(.54f, .575f, Age) * (1.0f - FMath::SmoothStep(1.03f, 1.40f, Age));
	for (int32 Local = 0; Local < 12; ++Local)
	{
		const int32 Index = EntryStart + Local;
		FVector Position = Base;
		FVector Scale = FVector::OneVector;
		FQuat Rotation = Face(FVector::UpVector, Base);
		float Strength = 0.0f;
		if (Local == 0)
		{
			Position += FVector::UpVector * (Height * (1.0f - FMath::SmoothStep(0.0f, .08f, Age)));
			Scale = FVector(Height / 100.0f, .55f, .55f);
			Strength = FMath::SmoothStep(0.0f, .02f, Age) * (1.0f - FMath::SmoothStep(.43f, .50f, Age));
		}
		else if (Local < 9)
		{
			const int32 Piece = Local - 1;
			Position += FVector::UpVector * Tip;
			const float Phase = Piece * TWO_PI / 7.0f;
			if (VDesign == 1)
			{
				// 부드러운 중심 광주: 세 장의 휘어진 체적 면에 밝기/깊이를 나눈다.
				Rotation *= FQuat(FVector::ForwardVector, Piece * 1.03f);
				Scale = FVector(Height / 100.0f, Piece == 0 ? 2.45f : 1.95f, Piece == 0 ? 2.45f : 1.95f);
				Position += Forward * (Piece - 1) * 21.0f;
				Strength = Piece < 3 ? Column * (Piece == 0 ? .64f : .38f) : 0.0f;
			}
			else if (VDesign == 2)
			{
				// 서로 다른 반경의 열린 광막. 원통 표면이나 반복된 평면 고리를 쓰지 않는다.
				const FVector Radial = Right * FMath::Cos(Phase) + Forward * FMath::Sin(Phase);
				Position += Radial * (52.0f + (Piece % 3) * 15.0f);
				Position.Z += Piece % 2 == 0 ? 0.0f : 36.0f;
				Rotation = FRotationMatrix::MakeFromXZ(FVector::UpVector, Radial).ToQuat();
				Rotation *= FQuat(FVector::ForwardVector, FMath::Sin(Age * 2.2f + Piece) * .17f);
				const float Width = 1.05f + (Piece % 3) * .18f;
				Scale = FVector(Height / 100.0f, Width, Width);
				Strength = Piece < 7 ? Column * .66f : 0.0f;
			}
			else
			{
				const float CoronaPhase = Piece * TWO_PI / 5.0f;
				const FVector Radial = Right * FMath::Cos(CoronaPhase) + Forward * FMath::Sin(CoronaPhase);
				Position += Radial * (Piece == 7 ? 0.0f : 85.0f);
				Rotation = Piece == 7 ? Rotation : FRotationMatrix::MakeFromXZ(FVector::UpVector, Radial).ToQuat();
				const float Width = Piece == 7 ? 1.90f : 1.10f + (Piece % 2) * .18f;
				Scale = FVector(Height / 100.0f, Width, Width);
				Strength = Column * (Piece == 7 ? .10f : Piece < 5 ? .77f : 0.0f);
			}
		}
		else if (Local == 9 || Local == 10)
		{
			const float Contact = FMath::Max(0.0f, Age - .66f);
			Rotation = FQuat::Identity;
			Position.Z += 4.0f;
			const float Expansion = FMath::SmoothStep(.0f, .20f, Contact);
			Scale = FVector(Local == 9 ? 1.25f + Expansion * .35f : .22f + Expansion * 1.0f);
			Scale.Z *= Local == 9 ? .40f : VDesign == 2 ? .40f : .75f;
			Strength = Age >= .66f ? (1.0f - FMath::SmoothStep(Local == 9 ? .40f : .05f, Local == 9 ? .83f : .33f, Contact)) : 0.0f;
			if (Local == 10 && VDesign == 1) { Strength *= .65f; }
		}
		else if (Local == 11)
		{
			Position = Spine;
			Rotation = Face(FVector::UpVector, Position);
			Scale = FVector(.68f + FMath::SmoothStep(1.16f, 1.25f, Age) * .22f);
			Strength = FMath::SmoothStep(1.155f, 1.175f, Age) * (1.0f - FMath::SmoothStep(1.21f, 1.34f, Age)) * .62f;
		}
		SetSurface(Index, Position, Rotation, Scale, Strength);
		Materials[Index]->SetScalarParameterValue(TEXT("Envelope"), Strength);
		Materials[Index]->SetScalarParameterValue(TEXT("ContactAge"), Age - .66f);
	}
}

void ASparrowFlameStudies::UpdateVGroundAnchor()
{
	if (!Caster.IsValid() || !GetWorld()) { return; }
	const UCapsuleComponent* Capsule = Caster->GetCapsuleComponent();
	const FVector Feet = Caster->GetActorLocation() - FVector::UpVector *
		(Capsule ? Capsule->GetScaledCapsuleHalfHeight() : 96.0f);
	FHitResult Hit;
	FCollisionQueryParams Query(SCENE_QUERY_STAT(SparrowVEntryFloor), false, Caster.Get());
	if (Form.IsValid()) { Query.AddIgnoredActor(Form.Get()); }
	const bool bGround = GetWorld()->LineTraceSingleByObjectType(Hit, Feet + FVector::UpVector * 80.0f,
		Feet - FVector::UpVector * 220.0f, FCollisionObjectQueryParams(ECC_WorldStatic), Query) && Hit.ImpactNormal.Z > .5f;
	EntryGroundNormal = bGround ? Hit.ImpactNormal : FVector::UpVector;
	Origin = (bGround ? Hit.ImpactPoint : Feet) + EntryGroundNormal * .5f;
}

void ASparrowFlameStudies::DrawCelestialV()
{
	if (Age >= 2.08f)
	{
		for (int32 Index = EntryStart; Index < Surfaces.Num(); ++Index) { Surfaces[Index]->SetVisibility(false); }
		return;
	}
	const bool bAnchored = VDesign == 6;
	if (bAnchored) { UpdateVGroundAnchor(); }
	const FVector Base = Origin;
	const FVector Spine = Caster->GetMesh()->GetSocketLocation(TEXT("spine_03"));
	constexpr float ContactAt = .34f;
	constexpr float Height = 1120.0f;
	const float ContactAge = Age - ContactAt;
	for (int32 Local = 0; Local < 12; ++Local)
	{
		const int32 Index = EntryStart + Local;
		FVector Position = Base;
		FVector Scale = FVector::OneVector;
		FQuat Rotation = FRotationMatrix::MakeFromXZ(FVector::UpVector, FVector::ForwardVector).ToQuat();
		float Strength = 0.0f;
		if (Local == 0)
		{
			// 노이즈/분절이 없는 곧은 전조. 큰 기둥이 닿기 전까지 한 줄로 유지한다.
			const float Tip = Height * (1.0f - FMath::SmoothStep(0.0f, .06f, Age));
			Position.Z += Tip;
			Scale = FVector(FMath::Max(1.0f, Height - Tip) / 100.0f, .065f, .065f);
			Strength = FMath::SmoothStep(0.0f, .018f, Age) * (1.0f - FMath::SmoothStep(.29f, .36f, Age));
		}
		else if (Local < 9)
		{
			const int32 Piece = Local - 1;
			const float Tip = Height * (1.0f - FMath::SmoothStep(.20f, ContactAt, Age));
			Position.Z += Tip;
			Rotation *= FQuat(FVector::ForwardVector, Piece * .81f);
			const float Width = Piece == 0 ? 3.20f : 3.70f;
			Scale = FVector(FMath::Max(1.0f, Height - Tip) / 100.0f, Width, Width);
			// V6 keeps V4's light body, but the outer veil releases before the core.
			const float FadeFrom = bAnchored ? (Piece == 0 ? 1.18f : .93f) : 1.03f;
			const float FadeUntil = bAnchored ? (Piece == 0 ? 1.67f : 1.46f) : 1.40f;
			Strength = Piece < 2 ? FMath::SmoothStep(.20f, .245f, Age) *
				(1.0f - FMath::SmoothStep(FadeFrom, FadeUntil, Age)) * (Piece == 0 ? .85f : .34f) : 0.0f;
		}
		else if (Local == 9)
		{
			Rotation = bAnchored ? FRotationMatrix::MakeFromZ(EntryGroundNormal).ToQuat() : FQuat::Identity;
			Position.Z += bAnchored ? .5f : 5.0f;
			const float Size = bAnchored ? 1.60f + FMath::SmoothStep(0.0f, .20f, ContactAge) * .10f :
				1.15f + FMath::SmoothStep(0.0f, .20f, ContactAge) * .75f;
			Scale = FVector(Size, Size, 1.0f);
			Strength = FMath::SmoothStep(0.0f, .02f, ContactAge) * (1.0f -
				(bAnchored ? FMath::SmoothStep(1.52f, 1.89f, Age) : FMath::SmoothStep(.34f, .72f, ContactAge)));
		}
		else if (Local == 10)
		{
			Rotation = FQuat::Identity;
			Position.Z += 6.0f;
			const float Expand = FMath::SmoothStep(0.0f, .18f, ContactAge);
			Scale = FVector(.60f + Expand * .82f, .60f + Expand * .82f, .55f + Expand * .55f);
			Strength = FMath::SmoothStep(0.0f, .02f, ContactAge) * (1.0f - FMath::SmoothStep(.12f, .42f, ContactAge));
		}
		else
		{
			Position = Spine;
			Rotation = Face(FVector::UpVector, Position);
			Scale = FVector(.68f + FMath::SmoothStep(1.16f, 1.25f, Age) * .22f);
			Strength = FMath::SmoothStep(1.155f, 1.175f, Age) * (1.0f - FMath::SmoothStep(1.21f, 1.34f, Age)) * .62f;
		}
		SetSurface(Index, Position, Rotation, Scale, Strength);
		Materials[Index]->SetScalarParameterValue(TEXT("Envelope"), Strength);
		Materials[Index]->SetScalarParameterValue(TEXT("ContactAge"), ContactAge);
	}
	const int32 DiagnosticPhase = Age >= 1.50f ? 2 : Age >= 1.0f ? 1 : Age >= .50f ? 0 : INDEX_NONE;
	if (DiagnosticPhase != INDEX_NONE && (EntryDiagnosticPhases & (1 << DiagnosticPhase)) == 0)
	{
		EntryDiagnosticPhases |= 1 << DiagnosticPhase;
		const int32 ColumnIndex = EntryStart + 1;
		UStaticMeshComponent* Column = Surfaces[ColumnIndex];
		UMaterialInstanceDynamic* Material = Materials[ColumnIndex];
		const FBox MeshBounds = Column->GetStaticMesh()->GetBoundingBox();
		const FVector BottomCenter = Column->GetComponentTransform().TransformPosition(FVector(MeshBounds.Min.X, 0.0f, 0.0f));
		const float FeetZ = Caster->GetActorLocation().Z - Caster->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
		UE_LOG(LogTemp, Display, TEXT("SPARROW_V_ENTRY design=%d age=%.3f mid_age=%.3f envelope=%.3f style=%.0f feetZ=%.3f anchorZ=%.3f bottomCenterZ=%.3f worldMinZ=%.3f same_mid=%d base=%s"),
			VDesign, Age, Material->K2_GetScalarParameterValue(TEXT("Age")), Material->K2_GetScalarParameterValue(TEXT("Envelope")),
			Material->K2_GetScalarParameterValue(TEXT("Style")), FeetZ, Origin.Z, BottomCenter.Z,
			Column->CalcBounds(Column->GetComponentTransform()).GetBox().Min.Z, Column->GetMaterial(0) == Material,
			*Material->GetMaterial()->GetPathName());
	}
}

void ASparrowFlameStudies::DrawPlumeV()
{
	if (Age >= 2.10f)
	{
		for (int32 Index = EntryStart; Index < Surfaces.Num(); ++Index) { Surfaces[Index]->SetVisibility(false); }
		return;
	}
	UpdateVGroundAnchor();
	constexpr float Height = 1120.0f;
	constexpr float ContactAt = .36f;
	const float ContactAge = Age - ContactAt;
	const float Tip = Height * (1.0f - FMath::SmoothStep(.21f, ContactAt, Age));
	const FQuat Facing = Face(FVector::UpVector, Origin);
	// Pressure peaks on contact, then relaxes before the native wings reveal at 1.16 s.
	const float Settle = FMath::Lerp(1.0f, .48f, FMath::SmoothStep(.10f, .48f, ContactAge));
	for (int32 Local = 0; Local < 12; ++Local)
	{
		const int32 Index = EntryStart + Local;
		FVector Position = Origin;
		FQuat Rotation = Facing;
		FVector Scale = FVector::OneVector;
		float Strength = 0.0f;
		if (Local == 0)
		{
			const float ThinTip = Height * (1.0f - FMath::SmoothStep(0.0f, .065f, Age));
			Position.Z += ThinTip;
			Scale = FVector(FMath::Max(1.0f, Height - ThinTip) / 100.0f, .10f, 1.0f);
			Strength = FMath::SmoothStep(0.0f, .02f, Age) * (1.0f - FMath::SmoothStep(.28f, .39f, Age));
		}
		else if (Local < 4)
		{
			Position.Z += Tip;
			const bool bCore = Local == 1;
			const float Width = bCore ? .34f : Local == 2 ? 2.75f : 3.35f;
			// The core lies on the character axis; the outer veil has no painted white ridge.
			if (Local == 3) { Rotation = FQuat(FVector::UpVector, .28f) * Facing; }
			const float Release = 1.0f - FMath::SmoothStep(bCore ? .78f : .96f, bCore ? 1.23f : 1.63f, Age);
			const float WidthRelax = FMath::Lerp(1.0f, bCore ? .66f : 1.14f, FMath::SmoothStep(.48f, 1.35f, Age));
			Scale = FVector(FMath::Max(1.0f, Height - Tip) / 100.0f, Width * WidthRelax, 1.0f);
			Strength = FMath::SmoothStep(.21f, .25f, Age) * Release * Settle * (bCore ? .92f : Local == 2 ? 1.65f : .85f);
		}
		else if (Local == 4)
		{
			Rotation = FRotationMatrix::MakeFromZ(EntryGroundNormal).ToQuat();
			Position += EntryGroundNormal * .35f;
			const float Width = .70f + FMath::SmoothStep(0.0f, .18f, ContactAge) * .97f;
			Scale = FVector(Width, Width, 1.0f);
			Strength = FMath::SmoothStep(.055f, .08f, Age) * (Age < ContactAt ? .25f : 1.0f) *
				(1.0f - FMath::SmoothStep(1.35f, 1.98f, Age));
		}
		else if (Local == 5)
		{
			Rotation = FQuat::Identity;
			Position.Z += 1.5f;
			const float Spread = FMath::SmoothStep(0.0f, .17f, ContactAge);
			Scale = FVector(.48f + Spread * .70f, .48f + Spread * .70f,
				.18f + FMath::Sin(FMath::Clamp(ContactAge / .54f, 0.0f, 1.0f) * PI) * 1.25f);
			Strength = FMath::SmoothStep(0.0f, .018f, ContactAge) * (1.0f - FMath::SmoothStep(.27f, .56f, ContactAge));
		}
		else if (Local == 6)
		{
			Rotation = FQuat::Identity;
			Scale = FVector(.45f + FMath::Max(0.0f, ContactAge) * 2.25f);
			Strength = FMath::SmoothStep(0.0f, .015f, ContactAge) * (1.0f - FMath::SmoothStep(.20f, .44f, ContactAge));
		}
		else if (Local == 7)
		{
			Position = Caster->GetMesh()->GetSocketLocation(TEXT("spine_03"));
			Rotation = Face(FVector::UpVector, Position);
			Scale = FVector(.68f + FMath::SmoothStep(1.16f, 1.25f, Age) * .22f);
			Strength = FMath::SmoothStep(1.155f, 1.175f, Age) * (1.0f - FMath::SmoothStep(1.21f, 1.34f, Age)) * .62f;
		}
		else if (Local == 8)
		{
			Position.Z += Tip;
			Scale = FVector(1.45f, 2.10f, 1.0f);
			Strength = FMath::SmoothStep(.23f, .27f, Age) * (1.0f - FMath::SmoothStep(.035f, .18f, ContactAge)) * .85f;
		}
		SetSurface(Index, Position, Rotation, Scale, Strength);
		Materials[Index]->SetScalarParameterValue(TEXT("Envelope"), Strength);
		Materials[Index]->SetScalarParameterValue(TEXT("ContactAge"), ContactAge);
	}
	const int32 Phase = Age >= 1.60f ? 2 : Age >= 1.20f ? 1 : Age >= .40f ? 0 : INDEX_NONE;
	if (Phase != INDEX_NONE && (EntryDiagnosticPhases & (1 << Phase)) == 0)
	{
		EntryDiagnosticPhases |= 1 << Phase;
		UE_LOG(LogTemp, Display, TEXT("SPARROW_V7 age=%.3f core=%.3f veil=%.3f ground=%.3f anchorZ=%.3f axis_baseZ=%.3f"), Age,
			Materials[EntryStart + 1]->K2_GetScalarParameterValue(TEXT("Envelope")),
			Materials[EntryStart + 2]->K2_GetScalarParameterValue(TEXT("Envelope")),
			Materials[EntryStart + 4]->K2_GetScalarParameterValue(TEXT("Envelope")), Origin.Z,
			Surfaces[EntryStart + 1]->GetComponentLocation().Z);
	}
}

void ASparrowFlameStudies::DrawRenaissanceV()
{
	if (Age >= 2.05f)
	{
		for (int32 Index = EntryStart; Index < Surfaces.Num(); ++Index) { Surfaces[Index]->SetVisibility(false); }
		return;
	}
	constexpr float Height = 1120.0f;
	constexpr float ContactAt = .34f;
	const float ContactAge = Age - ContactAt;
	const FVector Spine = Caster->GetMesh()->GetSocketLocation(TEXT("spine_03"));
	for (int32 Local = 0; Local < 12; ++Local)
	{
		const int32 Index = EntryStart + Local;
		FVector Position = Origin + FVector::UpVector * 3.0f;
		FVector Scale = FVector::OneVector;
		FQuat Rotation = FRotationMatrix::MakeFromXZ(FVector::UpVector, FVector::ForwardVector).ToQuat();
		float Strength = 0.0f;
		if (Local == 0)
		{
			const float Tip = Height * (1.0f - FMath::SmoothStep(0.0f, .06f, Age));
			Position.Z += Tip;
			Scale = FVector(FMath::Max(1.0f, Height - Tip) / 100.0f, .065f, .065f);
			Strength = FMath::SmoothStep(0.0f, .018f, Age) * (1.0f - FMath::SmoothStep(.29f, .37f, Age));
		}
		else if (Local <= 3)
		{
			const float Tip = Height * (1.0f - FMath::SmoothStep(.20f, ContactAt, Age));
			Position.Z += Tip;
			// A brief broad core hits first; the living gold curtains reveal the body
			// before the native wing unfurl, instead of hiding it behind a white rod.
			const float Release = FMath::SmoothStep(.43f, 1.18f, Age);
			const float Width = Local == 1 ? .78f : (Local == 2 ? 3.30f : 3.70f) * (1.0f + Release * .11f);
			Scale = FVector(FMath::Max(1.0f, Height - Tip) / 100.0f, Width, Width);
			Rotation *= FQuat(FVector::ForwardVector, Local == 3 ? 1.3f : .20f);
			Strength = FMath::SmoothStep(.20f, .245f, Age) *
				(1.0f - FMath::SmoothStep(Local == 1 ? .40f : .93f, Local == 1 ? .77f : 1.46f, Age));
			Strength *= Local == 1 ? .92f : Local == 2 ? .76f : .33f;
		}
		else if (Local == 4 || Local == 7)
		{
			Rotation = FRotator(0.0f, Local == 7 ? 37.0f : 0.0f, 0.0f).Quaternion();
			const float Since = ContactAge - (Local == 7 ? .075f : 0.0f);
			const float Expand = FMath::SmoothStep(0.0f, .24f, Since);
			const float Size = .22f + Expand * (Local == 4 ? 2.05f : 1.3f);
			Scale = FVector(Size, Size, .45f + Expand * .63f);
			Strength = FMath::SmoothStep(0.0f, .02f, Since) * (1.0f - FMath::SmoothStep(.13f, .43f, Since)) * (Local == 4 ? .8f : .38f);
		}
		else if (Local == 5 || Local == 8)
		{
			Rotation = FQuat::Identity;
			if (Local == 5)
			{
				const float Expand = FMath::SmoothStep(0.0f, .26f, ContactAge);
				Scale = FVector(1.05f + Expand * 1.85f);
				Scale.Z = 1.0f;
				Strength = FMath::SmoothStep(0.0f, .018f, ContactAge) * (1.0f - FMath::SmoothStep(.38f, .78f, ContactAge));
			}
			else
			{
				Scale = FVector(.50f + FMath::SmoothStep(.06f, .26f, Age) * .22f);
				Strength = FMath::SmoothStep(.055f, .085f, Age) * (1.0f - FMath::SmoothStep(.26f, .37f, Age)) * .48f;
			}
		}
		else if (Local == 6 || Local == 9)
		{
			Rotation = FRotator(0.0f, Local * 31.0f, 0.0f).Quaternion();
			const float Since = ContactAge - (Local == 9 ? .12f : 0.0f);
			const float Fly = FMath::Clamp(Since / .73f, 0.0f, 1.0f);
			Scale = FVector(.25f + Fly * 2.40f, .25f + Fly * 2.40f, .20f + Fly * 1.95f);
			Position.Z += FMath::Sin(Fly * PI) * 30.0f;
			Strength = FMath::SmoothStep(0.0f, .018f, Since) * (1.0f - FMath::SmoothStep(.22f, .73f, Since)) * (Local == 6 ? .82f : .32f);
		}
		else if (Local == 10)
		{
			Rotation = FQuat::Identity;
			const float Expand = FMath::SmoothStep(0.0f, .22f, ContactAge);
			Scale = FVector(.4f + Expand * 1.3f, .4f + Expand * 1.3f, .55f + Expand * .75f);
			Strength = FMath::SmoothStep(0.0f, .025f, ContactAge) * (1.0f - FMath::SmoothStep(.22f, .68f, ContactAge)) * .55f;
		}
		else
		{
			Position = Spine;
			Rotation = Face(FVector::UpVector, Position);
			Scale = FVector(.70f + FMath::SmoothStep(1.16f, 1.29f, Age) * .30f);
			Strength = FMath::SmoothStep(1.155f, 1.175f, Age) * (1.0f - FMath::SmoothStep(1.23f, 1.43f, Age)) * .48f;
		}
		SetSurface(Index, Position, Rotation, Scale, Strength);
		Materials[Index]->SetScalarParameterValue(TEXT("Envelope"), Strength);
		Materials[Index]->SetScalarParameterValue(TEXT("ContactAge"), Local == 8 ? Age - .06f : ContactAge);
	}
}

void ASparrowFlameStudies::DrawDCharge()
{
	const bool Fired = HasReleased();
	const float Since = Fired ? Age - ReleasedAt : 0.0f;
	if (!Fired) { Origin = Caster->GetMesh()->GetSocketLocation(TEXT("BowEmitterSocket")); }
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Direction).GetSafeNormal();
	const float Progress = FMath::Clamp(Age / Charge, 0.0f, 1.0f);
	const float Fold = Fired ? 1.0f : FMath::SmoothStep(.12f, .96f, Progress);
	const float Open = FMath::SmoothStep(.0f, .055f, Age);
	for (int32 Index = 0; Index < 8; ++Index)
	{
		// 활의 양끝에서 출발한 입체 광류가 시위 앞 한 축으로 빨려 들어간다.
		const float Phase = Index * TWO_PI / 8.0f + Age * 3.8f;
		const FVector Radial = Right * FMath::Cos(Phase) + FVector::UpVector * FMath::Sin(Phase);
		const float Radius = FMath::Lerp(94.0f + (Index % 3) * 16.0f, 12.0f, Fold);
		FVector Position = Origin + Direction * (35.0f + Fold * 15.0f) + Radial * Radius;
		const FVector Axis = (Direction * 1.5f - Radial * (1.1f - Fold)).GetSafeNormal();
		float Strength = Open * (.55f + Fold * .25f);
		if (Fired)
		{
			Position += Direction * Since * 1300.0f + Radial * Since * 190.0f;
			Strength *= 1.0f - FMath::SmoothStep(.018f, .16f, Since);
		}
		const float Width = Index % 2 == 0 ? 1.45f : .85f;
		SetSurface(Index, Position, Face(Axis, Position) * FQuat(FVector::ForwardVector, FMath::Sin(Phase) * .32f),
			FVector(2.25f - Fold * .65f, Width, 1.0f), Strength);
	}
	SetSurface(8, Origin + Direction * (26.0f + Since * 650.0f), Face(Direction, Origin), FVector(2.1f, 1.1f, 1.0f),
		Open * (.18f + Fold * .82f) * (Fired ? 1.0f - FMath::SmoothStep(.018f, .15f, Since) : 1.0f));
	SetSurface(9, Origin + Direction * (50.0f + Since * 760.0f), Face(Direction, Origin), FVector(3.2f, 2.15f, 1.0f),
		Fired ? 1.0f - FMath::SmoothStep(.025f, .19f, Since) : 0.0f);
}

void ASparrowFlameStudies::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	if (!Caster.IsValid() || Caster->IsActorBeingDestroyed() || !Caster->GetMesh()) { Destroy(); return; }
	Age += FMath::Max(0.0f, DeltaTime);
	if (bForm)
	{
		if (!Form.IsValid() || Form->IsActorBeingDestroyed() || (VDesign == 0 && GetVPreview() != Design)) { Destroy(); return; }
		DrawV();
	}
	else
	{
		if (HasReleased() && Age - ReleasedAt >= .85f) { Destroy(); return; }
		DrawD();
	}
}

void ASparrowFlameStudies::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (Projectile.IsValid()) { Projectile->OnDestroyed.RemoveDynamic(this, &ASparrowFlameStudies::OnProjectileDestroyed); }
	for (int32 Index = 0; Index < HiddenParts.Num(); ++Index)
	{
		if (HiddenParts[Index].IsValid()) { HiddenParts[Index]->SetVisibility(OriginalVisibility[Index]); }
	}
	HiddenParts.Reset();
	OriginalVisibility.Reset();
	Super::EndPlay(EndPlayReason);
}
