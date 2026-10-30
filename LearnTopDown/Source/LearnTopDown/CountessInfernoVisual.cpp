#include "CountessInfernoVisual.h"
#include "CountessRebirthFX.h"

#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/CapsuleComponent.h"
#include "Components/PostProcessComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "TopDownCombatCharacter.h"

namespace CountessInferno
{
	constexpr float CrossingLife = .66f;
	constexpr float FirstCrossing = .10f;
	constexpr float CrossingInterval = .17f;
	constexpr int32 CrossingCount = 18;
	constexpr float OrbitStrikePeriod = .34f;
	float Ease(float Value)
	{
		const float T = FMath::Clamp(Value, 0.0f, 1.0f);
		return T * T * (3.0f - 2.0f * T);
	}
	float OrbitPhase(float Age, int32 Slot, float Delay = 0.0f)
	{
		return FMath::Fmod(FMath::Max(0.0f, Age + Slot * OrbitStrikePeriod * .5f - Delay), OrbitStrikePeriod) / OrbitStrikePeriod;
	}
}

ACountessInfernoVisual::ACountessInfernoVisual()
{
	PrimaryActorTick.bCanEverTick = true;
	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("InfernoOrigin"));
	SetRootComponent(SceneRoot);
	SetActorEnableCollision(false);
	SetCanBeDamaged(false);
	Tags.Add(TEXT("CountessInfernoVisual"));
}

UParticleSystemComponent* ACountessInfernoVisual::CreateParticle(UParticleSystem* Template,
	USceneComponent* Parent, FName Tag)
{
	if (!Template || !Parent) { return nullptr; }
	UParticleSystemComponent* Particle = NewObject<UParticleSystemComponent>(this);
	Particle->SetupAttachment(Parent);
	Particle->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Particle->SetGenerateOverlapEvents(false);
	Particle->SetCanEverAffectNavigation(false);
	Particle->SetAutoActivate(false);
	Particle->bAutoDestroy = false;
	Particle->bOverrideLODMethod = true;
	Particle->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
	Particle->SetTemplate(Template);
	Particle->ComponentTags.Add(Tag);
	Particle->RegisterComponent();
	// The visual actor refreshes the sampled bones before AnimTrail records this frame's weapon positions.
	Particle->AddTickPrerequisiteActor(this);
	Particle->SetLODLevel(0);
	return Particle;
}

void ACountessInfernoVisual::Initialize(ATopDownCombatCharacter* Source, bool bStorm,
	const FVector& Origin, const FVector& Direction, float Lifetime)
{
	if (bInitialized || !IsValid(Source) || !Source->GetMesh() || !GetWorld()) { Destroy(); return; }
	USkeletalMeshComponent* Original = Source->GetMesh();
	USkeletalMesh* Mesh = Original->GetSkeletalMeshAsset();
	UMaterialInterface* Shadow = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessEShadowDissolve.M_CountessEShadowDissolve"));
	if (UMaterialInterface* QualityShadow = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/Quality20261023/Inferno/M_CountessInfernoShadow.M_CountessInfernoShadow")))
	{
		Shadow = QualityShadow;
	}
	if (UMaterialInterface* StrikeShadow = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/QualityGate20261024/M_CountessStrikeShadow.M_CountessStrikeShadow")))
	{
		Shadow = StrikeShadow;
	}
	UMaterialInterface* Ink = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessExtraInk_20261021.M_CountessExtraInk_20261021"));
	if (UMaterialInterface* QualityInk = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/Quality20261023/Inferno/M_CountessInfernoInk.M_CountessInfernoInk")))
	{
		Ink = QualityInk;
	}
	UStaticMesh* Plane = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
	UParticleSystem* SharpTrail = LoadObject<UParticleSystem>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessESharpTrail.P_CountessESharpTrail"));
	if (UParticleSystem* QualityTrail = LoadObject<UParticleSystem>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/Quality20261023/Inferno/P_CountessInfernoSwordTrail.P_CountessInfernoSwordTrail")))
	{
		SharpTrail = QualityTrail;
	}
	UParticleSystem* Veil = bStorm ? LoadObject<UParticleSystem>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessW_VeilRing.P_CountessW_VeilRing")) : nullptr;
	UParticleSystem* Spiral = bStorm ? LoadObject<UParticleSystem>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessW_SpiralRing.P_CountessW_SpiralRing")) : nullptr;
	if (bStorm)
	{
		if (UParticleSystem* QualityVeil = LoadObject<UParticleSystem>(nullptr,
			TEXT("/Game/TopDown/Characters/Countess/Quality20261023/Inferno/P_CountessInfernoVeil.P_CountessInfernoVeil")))
		{
			Veil = QualityVeil;
		}
		if (UParticleSystem* QualitySpiral = LoadObject<UParticleSystem>(nullptr,
			TEXT("/Game/TopDown/Characters/Countess/Quality20261023/Inferno/P_CountessInfernoSpiral.P_CountessInfernoSpiral")))
		{
			Spiral = QualitySpiral;
		}
	}
	for (const TCHAR* Name : {TEXT("Primary_Attack_Fast_V1"), TEXT("Primary_Attack_A_Fast_V1"), TEXT("Primary_Attack_B_Fast_InMotion")})
	{
		const FString Path = FString::Printf(TEXT("/Game/ParagonCountess/Characters/Heroes/Countess/Animations/%s.%s"), Name, Name);
		UAnimSequence* Attack = LoadObject<UAnimSequence>(nullptr, *Path);
		if (!Mesh || !Attack || Attack->GetSkeleton() != Mesh->GetSkeleton())
		{
			UE_LOG(LogTemp, Warning, TEXT("COUNTESS_INFERNO unavailable_animation=%s matching_skeleton=%d"), *Path, Mesh != nullptr);
			Destroy(); return;
		}
		Attacks.Add(Attack);
	}
	if (!Shadow || !Ink || !Plane || !SharpTrail || (bStorm && (!Veil || !Spiral)))
	{
		UE_LOG(LogTemp, Warning, TEXT("COUNTESS_INFERNO missing_asset shadow=%d ink=%d plane=%d trail=%d veil=%d spiral=%d"),
			Shadow != nullptr, Ink != nullptr, Plane != nullptr, SharpTrail != nullptr, Veil != nullptr, Spiral != nullptr);
		Destroy(); return;
	}
	SourceCharacter = Source;
	bStormField = bStorm;
	FieldOrigin = Origin;
	FieldCenter = Origin;
	FieldForward = Direction.GetSafeNormal2D();
	if (FieldForward.IsNearlyZero()) { FieldForward = Source->GetActorForwardVector().GetSafeNormal2D(); }
	FieldSide = FVector::CrossProduct(FVector::UpVector, FieldForward);
	MeshToCharacter = Original->GetComponentTransform().GetRelativeTransform(Source->GetActorTransform());
	// V may already have raised the real mesh. Copies keep the class's grounded offset instead of inheriting that lift.
	if (const ATopDownCombatCharacter* Defaults = Source->GetClass()->GetDefaultObject<ATopDownCombatCharacter>(); Defaults && Defaults->GetMesh())
	{
		FVector Offset = MeshToCharacter.GetTranslation();
		Offset.Z = Defaults->GetMesh()->GetRelativeLocation().Z;
		MeshToCharacter.SetTranslation(Offset);
	}
	CapsuleHeight = Source->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	LifeSeconds = FMath::Max(.1f, Lifetime);
	SetActorLocation(Origin);
	SetLifeSpan(LifeSeconds);
	Tags.Add(bStorm ? TEXT("CountessInfernoStorm") : TEXT("CountessInfernoOrbit"));
	const int32 ShadowCount = bStorm ? 6 : 2;
	ShadowMotion.SetNum(ShadowCount);
	for (int32 Index = 0; Index < ShadowCount; ++Index)
	{
		USkeletalMeshComponent* Copy = NewObject<USkeletalMeshComponent>(this,
			*FString::Printf(TEXT("CrimsonShadow%d"), Index));
		Copy->SetupAttachment(SceneRoot);
		Copy->SetSkeletalMeshAsset(Mesh);
		Copy->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Copy->SetGenerateOverlapEvents(false);
		Copy->SetCanEverAffectNavigation(false);
		Copy->SetCastShadow(false);
		Copy->bDisableClothSimulation = true;
		Copy->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
		Copy->SetForcedLOD(1);
		Copy->SetBoundsScale(1.4f);
		Copy->ComponentTags.Add(TEXT("CountessInfernoShadow"));
		Copy->RegisterComponent();
		Copy->SetComponentTickEnabled(false);
		Copy->SetVisibility(false);
		UMaterialInstanceDynamic* Dynamic = UMaterialInstanceDynamic::Create(Shadow, this);
		Dynamic->SetScalarParameterValue(TEXT("DissolveStart"), GetWorld()->GetTimeSeconds() + 10000.0f);
		Dynamic->SetScalarParameterValue(TEXT("DissolveDuration"), .18f);
		Dynamic->SetScalarParameterValue(TEXT("InfernoEnergy"), bStorm ? 1.0f : .85f);
		for (int32 Slot = 0; Slot < Copy->GetNumMaterials(); ++Slot) { Copy->SetMaterial(Slot, Dynamic); }
		Shadows.Add(Copy);
		ShadowMaterials.Add(Dynamic);
		for (int32 Side = 0; Side < 2; ++Side)
		{
			UParticleSystemComponent* Trail = CreateParticle(SharpTrail, Copy, TEXT("CountessInfernoSwordTrail"));
			Trails.Add(Trail);
			// AnimTrail samples its attached mesh. Each copy has its own two socket trails.
			Trail->SetRelativeTransform(FTransform::Identity);
			Trail->SetVisibility(false);
		}
	}
	const int32 CardCount = bStorm ? 12 : 4;
	for (int32 Index = 0; Index < CardCount; ++Index)
	{
		UStaticMeshComponent* Card = NewObject<UStaticMeshComponent>(this);
		Card->SetupAttachment(SceneRoot);
		Card->SetStaticMesh(Plane);
		Card->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Card->SetGenerateOverlapEvents(false);
		Card->SetCanEverAffectNavigation(false);
		Card->SetCastShadow(false);
		Card->SetReceivesDecals(false);
		Card->ComponentTags.Add(TEXT("CountessInfernoInk"));
		Card->RegisterComponent();
		UMaterialInstanceDynamic* Dynamic = UMaterialInstanceDynamic::Create(Ink, this);
		Dynamic->SetScalarParameterValue(TEXT("Shape"), Index % 3 == 0 ? 4.0f : 2.0f);
		Dynamic->SetScalarParameterValue(TEXT("Card"), 1.0f);
		Dynamic->SetScalarParameterValue(TEXT("Seed"), Index * 1.713f);
		Dynamic->SetScalarParameterValue(TEXT("Opacity"), 0.0f);
		Card->SetMaterial(0, Dynamic);
		InkCards.Add(Card);
		InkMaterials.Add(Dynamic);
	}
	UStaticMesh* BladeSurface = LoadObject<UStaticMesh>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/QualityGate20261024/SM_CountessSweptCut.SM_CountessSweptCut"));
	UMaterialInterface* BladeSurfaceMaterial = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/QualityGate20261024/M_CountessSweptCut.M_CountessSweptCut"));
	if (BladeSurface && BladeSurfaceMaterial)
	{
		for (int32 Index = 0; Index < ShadowCount * 2; ++Index)
		{
			UStaticMeshComponent* Surface = NewObject<UStaticMeshComponent>(this);
			Surface->SetMobility(EComponentMobility::Movable);
			Surface->SetupAttachment(SceneRoot);
			Surface->SetStaticMesh(BladeSurface);
			Surface->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			Surface->SetGenerateOverlapEvents(false);
			Surface->SetCanEverAffectNavigation(false);
			Surface->SetCastShadow(false);
			Surface->SetReceivesDecals(false);
			Surface->SetVisibility(false);
			Surface->ComponentTags.Add(TEXT("CountessReferenceBlade"));
			Surface->RegisterComponent();
			UMaterialInstanceDynamic* Dynamic = UMaterialInstanceDynamic::Create(BladeSurfaceMaterial, this);
			Dynamic->SetScalarParameterValue(TEXT("CutTail"), Index % 2 == 0 ? 0.0f : 1.0f);
			Dynamic->SetScalarParameterValue(TEXT("CutStrength"), 0.0f);
			Surface->SetMaterial(0, Dynamic);
			BladeSurfaces.Add(Surface);
			BladeMaterials.Add(Dynamic);
		}
	}
	else
	{
		UE_LOG(LogTemp, Warning, TEXT("COUNTESS_INFERNO missing reference blade geometry/material"));
	}
	// Q's baked socket sweep is not the path of these primary attacks. Their own AnimTrail ties the authored cuts to each weapon.
	if (bStorm)
	{
		// Three heights, two alternating authored emitters per height: continuous volume without a hard ring reset.
		for (int32 Index = 0; Index < 6; ++Index)
		{
			UParticleSystemComponent* Layer = CreateParticle(Index / 2 == 1 ? Spiral : Veil,
				SceneRoot, TEXT("CountessInfernoStormLayer"));
			// Thousands of the inherited W sparks read as pixel noise at the storm's enlarged scale.
			Layer->SetEmitterEnable(TEXT("BlackSparks"), false);
			Layer->SetEmitterEnable(TEXT("RedSparks"), false);
			// Keep the heavy outer charcoal at ground level. Upper layers remain porous enough to read the crossings.
			if (Index / 2 > 0)
			{
				Layer->SetEmitterEnable(TEXT("DarkPuffs_FL"), false);
				Layer->SetEmitterEnable(TEXT("SmokePuffs_FL"), false);
			}
			StormLayers.Add(Layer);
			LayerBirths.Add(-1.0f);
		}
		if (Source->IsLocallyControlled())
		{
			UMaterialInterface* LocalContrast = LoadObject<UMaterialInterface>(nullptr,
				TEXT("/Game/TopDown/Characters/Countess/Quality20261023/Inferno/M_CountessInfernoSurroundings.M_CountessInfernoSurroundings"));
			Surroundings = NewObject<UPostProcessComponent>(this);
			Surroundings->SetupAttachment(SceneRoot);
			Surroundings->bUnbound = true;
			Surroundings->Priority = 22.0f;
			Surroundings->BlendWeight = 0.0f;
			Surroundings->Settings.bOverride_AutoExposureBias = false;
			Surroundings->Settings.bOverride_ColorGain = LocalContrast == nullptr;
			Surroundings->Settings.ColorGain = FVector4(.15f, .10f, .12f, 1.0f);
			Surroundings->Settings.bOverride_VignetteIntensity = LocalContrast == nullptr;
			Surroundings->Settings.VignetteIntensity = .78f;
			if (LocalContrast)
			{
				SurroundingsMaterial = UMaterialInstanceDynamic::Create(LocalContrast, this);
				SurroundingsMaterial->SetScalarParameterValue(TEXT("SurroundingsStrength"), 0.0f);
				Surroundings->Settings.WeightedBlendables.Array.Emplace(1.0f, SurroundingsMaterial.Get());
			}
			Surroundings->ComponentTags.Add(TEXT("CountessInfernoSurroundings"));
			Surroundings->RegisterComponent();
		}
	}
	bInitialized = true;
	ACountessRebirthFX::Create(Source, bStorm ? TEXT("V") : TEXT("A"), Origin, Direction, this);
	if (!bStorm)
	{
		StartShadow(0, 0, 0.0f);
		StartShadow(1, 1, 0.0f);
		UpdateOrbit();
	}
	UpdateInk();
	UpdateBlades();
	UE_LOG(LogTemp, Display, TEXT("COUNTESS_INFERNO initialized storm=%d lifetime=%.2f shadow_pool=%d collision=0 damage=0"),
		bStormField, LifeSeconds, Shadows.Num());
}

float ACountessInfernoVisual::GetEnvelope() const
{
	return CountessInferno::Ease(Age / .16f) * CountessInferno::Ease((LifeSeconds - Age) / (bStormField ? .50f : .28f));
}

void ACountessInfernoVisual::SetShadowTrails(int32 Slot, bool bActive, bool bReset)
{
	for (int32 Side = 0; Side < 2; ++Side)
	{
		UParticleSystemComponent* Trail = Trails[Slot * 2 + Side];
		if (!Trail) { continue; }
		if (!bActive) { Trail->EndTrails(); Trail->DeactivateSystem(); continue; }
		const FName Base(Side == 0 ? TEXT("FX_WeaponBase_L") : TEXT("FX_WeaponBase_R"));
		const FName Tip(Side == 0 ? TEXT("FX_WeaponTip_L") : TEXT("FX_WeaponTip_R"));
		if (!Shadows[Slot]->DoesSocketExist(Base) || !Shadows[Slot]->DoesSocketExist(Tip)) { continue; }
		if (bReset) { Trail->DeactivateImmediate(); Trail->KillParticlesForced(); }
		Trail->SetVisibility(true);
		Trail->BeginTrails(Base, Tip, ETrailWidthMode_FromCentre, .88f);
		Trail->SetLODLevel(0);
	}
}

void ACountessInfernoVisual::StartShadow(int32 Slot, int32 Serial, float Birth)
{
	FShadowMotion& Motion = ShadowMotion[Slot];
	Motion.Birth = Birth;
	Motion.Serial = Serial;
	Motion.Animation = INDEX_NONE;
	Motion.bVisible = true;
	const float BirthRadius = 100.0f + 330.0f * CountessInferno::Ease(Birth / .95f);
	const FVector Across = FieldForward.RotateAngleAxis(Serial * 137.5f + 23.0f, FVector::UpVector);
	const FVector Aside = FVector::CrossProduct(FVector::UpVector, Across);
	const float Height = bStormField ? (Serial % 3) * 55.0f + 8.0f : 0.0f;
	// Parallel chords occupy separate inner/outer lanes. Repeated attacks no longer collapse into one central flash.
	const FVector LaneOffset = Aside * BirthRadius * ((Serial % 3) - 1) * .43f;
	Motion.Start = FieldOrigin + LaneOffset + Across * BirthRadius * .76f + FVector(0, 0, Height);
	Motion.End = FieldOrigin + LaneOffset - Across * BirthRadius * .76f + FVector(0, 0, Height + 18.0f);
	ShadowMaterials[Slot]->SetScalarParameterValue(TEXT("DissolveStart"), GetWorld()->GetTimeSeconds() +
		(bStormField ? CountessInferno::CrossingLife - .18f - FMath::Max(0.0f, Age - Birth) : LifeSeconds - Age - .25f));
	ShadowMaterials[Slot]->SetScalarParameterValue(TEXT("DissolveDuration"), bStormField ? .18f : .25f);
	Shadows[Slot]->SetVisibility(true);
	SetShadowPose(Slot, Motion.Start, Motion.End - Motion.Start, Serial % Attacks.Num(), .025f);
	SetShadowTrails(Slot, true, true);
	++ShadowsStarted;
}

void ACountessInfernoVisual::SetShadowPose(int32 Slot, const FVector& Location, const FVector& Facing,
	int32 Animation, float Sample)
{
	USkeletalMeshComponent* Copy = Shadows[Slot];
	FShadowMotion& Motion = ShadowMotion[Slot];
	if (Motion.Animation != Animation)
	{
		Copy->PlayAnimation(Attacks[Animation], false);
		Copy->SetPlayRate(0.0f);
		Copy->SetComponentTickEnabled(false);
		Copy->GetAnimInstance()->SetRootMotionMode(ERootMotionMode::IgnoreRootMotion);
		Motion.Animation = Animation;
	}
	FTransform Anchor(Facing.GetSafeNormal2D().Rotation(), Location + FVector(0, 0, CapsuleHeight));
	Anchor.SetScale3D(FVector(bStormField ? .90f : .88f));
	Copy->SetWorldTransform(MeshToCharacter * Anchor);
	if (UAnimSingleNodeInstance* Node = Copy->GetSingleNodeInstance())
	{
		// Gameplay notifies are never evaluated on the visual copy, even when its attack loops.
		Node->SetPosition(FMath::Clamp(Sample, 0.0f, Attacks[Animation]->GetPlayLength() - .001f), false);
		Copy->TickAnimation(0.0f, false);
		Copy->RefreshBoneTransforms();
	}
}

void ACountessInfernoVisual::UpdateStorm()
{
	using namespace CountessInferno;
	Radius = 100.0f + 330.0f * Ease(Age / .95f);
	while (ShadowsStarted < CrossingCount && Age >= FirstCrossing + ShadowsStarted * CrossingInterval)
	{
		const int32 Serial = ShadowsStarted;
		StartShadow(Serial % Shadows.Num(), Serial, FirstCrossing + Serial * CrossingInterval);
	}
	for (int32 Slot = 0; Slot < Shadows.Num(); ++Slot)
	{
		FShadowMotion& Motion = ShadowMotion[Slot];
		if (!Motion.bVisible) { continue; }
		const float T = FMath::Clamp((Age - Motion.Birth) / CrossingLife, 0.0f, 1.0f);
		if (T >= 1.0f)
		{
			Motion.bVisible = false;
			Shadows[Slot]->SetVisibility(false);
			SetShadowTrails(Slot, false);
			continue;
		}
		const FVector Where = FMath::Lerp(Motion.Start, Motion.End, T) + FVector(0, 0, 30.0f * FMath::Sin(T * PI));
		SetShadowPose(Slot, Where, Motion.End - Motion.Start, Motion.Animation, .07f + .21f * T);
	}
	for (int32 Index = 0; Index < StormLayers.Num(); ++Index)
	{
		const int32 Height = Index / 2;
		UParticleSystemComponent* Layer = StormLayers[Index];
		const float Size = Radius / 240.0f * (Height == 0 ? .56f : Height == 1 ? .46f : .34f);
		Layer->SetRelativeLocation(FVector(0, 0, 14.0f + Height * 82.0f));
		Layer->SetRelativeRotation(FRotator(Height == 1 ? 12.0f : -8.0f, Height * 73.0f + Age * (Height == 1 ? -38.0f : 24.0f), 0));
		Layer->SetRelativeScale3D(FVector(Size, Size, Size * (Height == 0 ? .28f : .65f)));
		const float Start = .08f + Height * .075f + (Index % 2) * .36f;
		const float NextBirth = LayerBirths[Index] < 0.0f ? Start : LayerBirths[Index] + .72f;
		if (Age >= NextBirth && Age < LifeSeconds - .58f)
		{
			LayerBirths[Index] = Age;
			Layer->ActivateSystem(true);
			Layer->SetLODLevel(0);
			Layer->SetEmitterEnable(TEXT("BlackSparks"), false);
			Layer->SetEmitterEnable(TEXT("RedSparks"), false);
			if (Height > 0)
			{
				Layer->SetEmitterEnable(TEXT("DarkPuffs_FL"), false);
				Layer->SetEmitterEnable(TEXT("SmokePuffs_FL"), false);
			}
		}
		if (Age >= LifeSeconds - .50f) { Layer->DeactivateSystem(); }
	}
	UpdateSurroundings();
}

void ACountessInfernoVisual::UpdateOrbit()
{
	const float Progress = FMath::Clamp(Age / LifeSeconds, 0.0f, 1.0f);
	FieldCenter = FieldOrigin + FieldForward * (70.0f + 370.0f * FMath::Sin(PI * Progress));
	for (int32 Slot = 0; Slot < Shadows.Num(); ++Slot)
	{
		const float Sign = Slot == 0 ? -1.0f : 1.0f;
		const float Phase = CountessInferno::OrbitPhase(Age, Slot);
		const float Angle = FMath::DegreesToRadians(Sign * (CountessInferno::Ease(Phase) * 285.0f - 115.0f));
		const FVector Pivot = FieldCenter + FieldSide * Sign * 76.0f + FieldForward * (Sign * 18.0f);
		const FVector Where = Pivot + FieldForward * (FMath::Cos(Angle) * 22.0f) +
			FieldSide * (FMath::Sin(Angle) * 22.0f) + FVector(0, 0, 12.0f + 12.0f * FMath::Sin(Phase * PI));
		const FVector Tangent = (FieldForward * -FMath::Sin(Angle) + FieldSide * FMath::Cos(Angle)) * Sign;
		const float AttackAge = Age + Slot * CountessInferno::OrbitStrikePeriod * .5f;
		const int32 Cycle = FMath::FloorToInt(AttackAge / CountessInferno::OrbitStrikePeriod);
		// Stay inside the real blade sweep, excluding the upright wind-up/recovery frames.
		const int32 Animation = (Cycle + Slot) % 2;
		if (Animation != ShadowMotion[Slot].Animation) { SetShadowTrails(Slot, false); }
		const bool bNewAttack = Animation != ShadowMotion[Slot].Animation;
		SetShadowPose(Slot, Where, Tangent, Animation, .075f + .19f * Phase);
		if (bNewAttack) { SetShadowTrails(Slot, true, true); }
	}
}

void ACountessInfernoVisual::UpdateSurroundings()
{
	if (!Surroundings) { return; }
	const float Strength = .98f * GetEnvelope();
	if (!SurroundingsMaterial) { Surroundings->BlendWeight = Strength; return; }
	// Project every frame, including camera lag and movement. A wide feather has no hard spotlight boundary.
	FLinearColor ScreenField(.5f, .43f, .20f, .24f);
	if (APlayerController* PC = GetWorld()->GetFirstPlayerController(); PC && PC->PlayerCameraManager)
	{
		int32 Width = 0, Height = 0;
		PC->GetViewportSize(Width, Height);
		const FRotationMatrix CameraBasis(PC->PlayerCameraManager->GetCameraRotation());
		const FVector Center = FieldCenter + FVector(0, 0, 105.0f);
		const float FocusRadius = 90.0f + Radius * .52f;
		FVector2D Projected, Right, Up;
		if (Width > 0 && Height > 0 && PC->ProjectWorldLocationToScreen(Center, Projected, true) &&
			PC->ProjectWorldLocationToScreen(Center + CameraBasis.GetUnitAxis(EAxis::Y) * FocusRadius, Right, true) &&
			PC->ProjectWorldLocationToScreen(Center + CameraBasis.GetUnitAxis(EAxis::Z) * FocusRadius, Up, true))
		{
			ScreenField = FLinearColor(Projected.X / Width, Projected.Y / Height,
				FMath::Clamp(FMath::Abs(Right.X - Projected.X) / Width, .035f, .60f),
				FMath::Clamp(FMath::Abs(Up.Y - Projected.Y) / Height, .05f, .70f));
		}
	}
	SurroundingsMaterial->SetVectorParameterValue(TEXT("FieldScreen"), ScreenField);
	SurroundingsMaterial->SetScalarParameterValue(TEXT("FieldRadiusY"), ScreenField.A);
	SurroundingsMaterial->SetScalarParameterValue(TEXT("SurroundingsStrength"), Strength);
	Surroundings->BlendWeight = 1.0f;
}

void ACountessInfernoVisual::UpdateInk()
{
	FVector ToCamera(1, 1, 1);
	if (const APlayerController* PC = GetWorld()->GetFirstPlayerController(); PC && PC->PlayerCameraManager)
	{
		ToCamera = (PC->PlayerCameraManager->GetCameraLocation() - FieldCenter).GetSafeNormal();
	}
	const float Envelope = GetEnvelope();
	for (int32 Index = 0; Index < InkCards.Num(); ++Index)
	{
		FVector Center, Axis;
		float Length, Width, Opacity;
		if (bStormField)
		{
			const int32 Height = Index / 4;
			const float Angle = Index * 1.973f + Age * (Height == 1 ? -2.1f : 1.45f);
			const FVector Out = FieldForward * FMath::Cos(Angle) + FieldSide * FMath::Sin(Angle);
			Center = FieldCenter + Out * Radius * (.22f + .19f * (Index % 4)) +
				FVector(0, 0, 18.0f + Height * 73.0f + 15.0f * FMath::Sin(Angle * 1.7f));
			Axis = FVector::CrossProduct(FVector::UpVector, Out) + FVector(0, 0, .12f * FMath::Sin(Angle));
			Length = Radius * (Index % 3 == 0 ? .40f : .58f);
			Width = Radius * (Index % 3 == 0 ? .09f : .14f);
			Opacity = Height == 0 ? .42f : .30f;
		}
		else
		{
			const int32 Slot = Index / 2;
			const float Phase = CountessInferno::OrbitPhase(Age, Slot, (Index % 2) * .045f);
			const float Sign = Slot == 0 ? -1.0f : 1.0f;
			const float Angle = FMath::DegreesToRadians(Sign * (CountessInferno::Ease(Phase) * 285.0f - 115.0f));
			Center = FieldCenter + FieldForward * (Sign * 18.0f + FMath::Cos(Angle) * 87.0f) +
				FieldSide * (Sign * 76.0f + FMath::Sin(Angle) * 87.0f) + FVector(0, 0, 45.0f + (Index % 2) * 12.0f);
			Axis = -FieldForward * FMath::Sin(Angle) + FieldSide * FMath::Cos(Angle);
			Length = 110.0f - (Index % 2) * 22.0f;
			Width = 34.0f - (Index % 2) * 8.0f;
			Opacity = (.32f - (Index % 2) * .08f) * FMath::Sin(Phase * PI);
		}
		Axis = (Axis - ToCamera * FVector::DotProduct(Axis, ToCamera)).GetSafeNormal();
		FVector Across = FVector::CrossProduct(ToCamera, Axis).GetSafeNormal();
		if (Axis.IsNearlyZero()) { Axis = FieldForward; Across = FieldSide; }
		InkCards[Index]->SetWorldTransform(FTransform(FRotationMatrix::MakeFromXY(Axis, Across).ToQuat(),
			Center, FVector(Length / 100.0f, Width / 100.0f, 1.0f)));
		InkMaterials[Index]->SetScalarParameterValue(TEXT("Fade"), Envelope);
		InkMaterials[Index]->SetScalarParameterValue(TEXT("Opacity"), Opacity * (ACountessRebirthFX::Enabled() ? .28f : 1.f));
		InkMaterials[Index]->SetScalarParameterValue(TEXT("Pulse"), .25f + .15f * FMath::Sin(Age * 7.0f + Index));
	}
}

void ACountessInfernoVisual::UpdateBlades()
{
	const float Envelope = GetEnvelope();
	for (int32 Index = 0; Index < BladeSurfaces.Num(); ++Index)
	{
		const int32 Slot = Index / 2;
		const int32 Layer = Index % 2;
		const FShadowMotion& Motion = ShadowMotion[Slot];
		float Visibility = Envelope;
		FVector Center;
		FRotator Rotation;
		float Diameter;
		if (bStormField)
		{
			const float T = FMath::Clamp((Age - Motion.Birth - Layer * .065f) / CountessInferno::CrossingLife, 0.0f, 1.0f);
			Visibility *= Motion.bVisible ? FMath::SmoothStep(.025f, .15f, T) * (1.0f - FMath::SmoothStep(.62f, .96f, T)) : 0.0f;
			Center = FMath::Lerp(Motion.Start, Motion.End, T) +
				FVector(0, 0, 66.0f + 30.0f * FMath::Sin(T * PI) - Layer * 7.0f);
			Rotation = (Motion.End - Motion.Start).Rotation();
			Rotation.Yaw += -125.0f + CountessInferno::Ease(T) * 285.0f;
			Rotation.Pitch = 12.0f + (Motion.Serial % 3) * 6.0f;
			Rotation.Roll = Motion.Serial % 2 == 0 ? 12.0f : -12.0f;
			Diameter = Layer == 0 ? 310.0f : 290.0f;
			// The first strikes grow with the young storm instead of spawning at the final field's full scale.
			Diameter *= .62f + .38f * CountessInferno::Ease(Age / .80f);
		}
		else
		{
			const float Sign = Slot == 0 ? -1.0f : 1.0f;
			const float Phase = CountessInferno::OrbitPhase(Age, Slot, Layer * .060f);
			Visibility *= FMath::SmoothStep(.015f, .14f, Phase) * (1.0f - FMath::SmoothStep(.65f, .96f, Phase));
			Center = FieldCenter + FieldSide * Sign * 76.0f + FieldForward * Sign * 18.0f +
				FVector(0, 0, 64.0f - Layer * 9.0f);
			Rotation = FieldForward.Rotation();
			Rotation.Yaw += Sign * (CountessInferno::Ease(Phase) * 285.0f - 115.0f);
			Rotation.Pitch = Sign * (18.0f + 5.0f * FMath::Sin(Age * 4.0f));
			Rotation.Roll = Sign * 11.0f;
			Diameter = Layer == 0 ? 300.0f : 268.0f;
		}
		UStaticMeshComponent* Surface = BladeSurfaces[Index];
		const FBox Bounds = Surface->GetStaticMesh()->GetBoundingBox();
		const FVector SourceSize = Bounds.GetSize().ComponentMax(FVector(1.0f));
		const float LateralScale = Diameter / FMath::Max(SourceSize.X, SourceSize.Y);
		const FVector Scale(LateralScale, LateralScale, (Layer == 0 ? 47.0f : 34.0f) / SourceSize.Z);
		Surface->SetWorldTransform(FTransform(Rotation, Center - Rotation.RotateVector(Bounds.GetCenter() * Scale), Scale));
		Surface->SetVisibility(Visibility > .015f);
		BladeMaterials[Index]->SetScalarParameterValue(TEXT("CutStrength"), Visibility);
	}
}

int32 ACountessInfernoVisual::GetVisibleShadowCount() const
{
	int32 Count = 0;
	for (const FShadowMotion& Motion : ShadowMotion) { Count += Motion.bVisible ? 1 : 0; }
	return Count;
}

void ACountessInfernoVisual::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!bInitialized) { return; }
	if (!SourceCharacter.IsValid() || SourceCharacter->IsActorBeingDestroyed()) { Destroy(); return; }
	Age += DeltaSeconds;
	if (Age >= LifeSeconds) { Destroy(); return; }
	if (bStormField) { UpdateStorm(); } else { UpdateOrbit(); }
	UpdateInk();
	UpdateBlades();
}

void ACountessInfernoVisual::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (Surroundings) { Surroundings->BlendWeight = 0.0f; Surroundings->DestroyComponent(); }
	for (UParticleSystemComponent* Trail : Trails)
	{
		if (IsValid(Trail)) { Trail->EndTrails(); Trail->DestroyComponent(); }
	}
	for (UParticleSystemComponent* Layer : StormLayers) { if (IsValid(Layer)) { Layer->DestroyComponent(); } }
	for (USkeletalMeshComponent* Copy : Shadows) { if (IsValid(Copy)) { Copy->DestroyComponent(); } }
	for (UStaticMeshComponent* Card : InkCards) { if (IsValid(Card)) { Card->DestroyComponent(); } }
	for (UStaticMeshComponent* Blade : BladeSurfaces) { if (IsValid(Blade)) { Blade->DestroyComponent(); } }
	Super::EndPlay(EndPlayReason);
}
