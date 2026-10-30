#include "CountessDemonForm.h"
#include "CountessRebirthFX.h"

#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "Particles/ParticleEmitter.h"
#include "Particles/ParticleLODLevel.h"
#include "Particles/Light/ParticleModuleLightBase.h"
#include "TopDownCombatCharacter.h"

namespace
{
	constexpr float EntrySeconds = 0.5f;
	const TCHAR* BodyPath = TEXT("/Game/TopDown/Characters/Countess/DemonSilhouette20261024/M_CountessDemonSilhouette.M_CountessDemonSilhouette");
	const TCHAR* ShadowPath = TEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessEShadowDissolve.M_CountessEShadowDissolve");

	UParticleSystem* MakeFormTemplate(UObject* Owner, const TCHAR* Path)
	{
		UParticleSystem* Source = LoadObject<UParticleSystem>(nullptr, Path);
		if (!Source)
		{
			UE_LOG(LogTemp, Warning, TEXT("COUNTESS_DEMON_TEMPLATE failed source=%s reason=missing_source"), Path);
			return nullptr;
		}
		UParticleSystem* Runtime = DuplicateObject<UParticleSystem>(Source, Owner);
		if (!Runtime)
		{
			UE_LOG(LogTemp, Warning, TEXT("COUNTESS_DEMON_TEMPLATE failed source=%s reason=duplicate_failed"), Path);
			return nullptr;
		}
		Runtime->SetFlags(RF_Transient);
		Runtime->ClearFlags(RF_Public | RF_Standalone);
		const bool bContact = Source->GetFName() == TEXT("P_CountessBloodSealBurst");
		const bool bGround = Source->GetFName() == TEXT("P_CountessBloodSealGround");
		if (bContact || bGround)
		{
			// 실제 입자 감사에서 확인한 contact/ground 층만 남긴다. 원본 shader/DP/SubUV는 유지한다.
			Runtime->Emitters.RemoveAll([bContact](UParticleEmitter* Emitter)
			{
				if (!Emitter) { return true; }
				const FName Name = Emitter->GetEmitterName();
				return bContact ? !(Name == TEXT("SmokeUp_Dir") || Name == TEXT("SmokeBack_Dir") ||
					Name == TEXT("Smoke") || Name == TEXT("RedSpark") || Name == TEXT("DirectionalSpark") ||
					Name == TEXT("TinyFlare")) : !(Name == TEXT("Smoke") || Name == TEXT("FireSmoke_L") ||
					Name == TEXT("FireSmoke_R") || Name == TEXT("SmokeColumn") || Name == TEXT("SmokeSpears") ||
					Name == TEXT("Ground Linger Sparks"));
			});
		}
		int32 LODCount = 0;
		int32 LightsRemoved = 0;
		// 재질/입자층은 유지하고 S 소유 복제본의 광원만 제외해 몸의 명암을 보존한다.
		for (UParticleEmitter* Emitter : Runtime->Emitters)
		{
			if (!Emitter || !Emitter->IsIn(Runtime))
			{
				UE_LOG(LogTemp, Warning, TEXT("COUNTESS_DEMON_TEMPLATE failed source=%s reason=emitter_ownership object=%s"), Path, *GetPathNameSafe(Emitter));
				return nullptr;
			}
			for (UParticleLODLevel* LOD : Emitter->LODLevels)
			{
				if (!LOD || !LOD->IsIn(Runtime))
				{
					UE_LOG(LogTemp, Warning, TEXT("COUNTESS_DEMON_TEMPLATE failed source=%s reason=lod_ownership object=%s"), Path, *GetPathNameSafe(LOD));
					return nullptr;
				}
				++LODCount;
				LightsRemoved += LOD->Modules.RemoveAll([](UParticleModule* Module)
				{
					return Module && Module->IsA<UParticleModuleLightBase>();
				});
			}
			Emitter->UpdateModuleLists();
		}
		Runtime->BuildEmitters();
		UE_LOG(LogTemp, Display, TEXT("COUNTESS_DEMON_TEMPLATE ready source=%s emitters=%d source_emitters=%d lods=%d lights_removed=%d compact_contact=%d runtime=%s"),
			Path, Runtime->Emitters.Num(), Source->Emitters.Num(), LODCount, LightsRemoved, bContact || bGround, *Runtime->GetPathName());
		return Runtime;
	}
}

ACountessDemonForm::ACountessDemonForm()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickGroup = TG_PostPhysics;
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
	SetActorEnableCollision(false);
	SetCanBeDamaged(false);
	Tags.Add(TEXT("CountessDemonForm"));
	Tags.Add(TEXT("CountessSkillFX"));
}

bool ACountessDemonForm::Initialize(ATopDownCombatCharacter* Source, float Duration)
{
	USkeletalMeshComponent* Mesh = IsValid(Source) ? Source->GetMesh() : nullptr;
	if (bInitialized || bStopped || !GetWorld() || !Mesh || !Mesh->GetSkeletalMeshAsset() ||
		!FMath::IsFinite(Duration) || Duration < EntrySeconds) { return false; }
	UMaterialInterface* Body = LoadObject<UMaterialInterface>(nullptr, BodyPath);
	if (!Body) { Body = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessDemonForm.M_CountessDemonForm")); }
	if (!Body) { Body = LoadObject<UMaterialInterface>(nullptr, ShadowPath); }
	UStaticMesh* Wing = LoadObject<UStaticMesh>(nullptr,
		TEXT("/Game/ParagonCountess/FX/Meshes/Shapes/SM_Countess_WingMesh.SM_Countess_WingMesh"));
	if (!Body || !Wing || Mesh->GetNumMaterials() <= 0) { return false; }
	SourceCharacter = Source;
	SourceMesh = Mesh;
	FormSeconds = Duration;
	StartedAt = GetWorld()->GetTimeSeconds();
	SetOwner(Source);
	AttachToComponent(Mesh, FAttachmentTransformRules::SnapToTargetNotIncludingScale);
	for (int32 Index = 0; Index < Mesh->GetNumMaterials(); ++Index)
	{
		OriginalMaterials.Add(Mesh->GetMaterial(Index));
		UMaterialInstanceDynamic* Mid = UMaterialInstanceDynamic::Create(Body, this);
		if (!Mid) { RestoreSource(); return false; }
		Mid->SetScalarParameterValue(TEXT("CloneOpacity"), 0.98f);
		Mid->SetScalarParameterValue(TEXT("DissolveStart"), 1000000.0f);
		Mid->SetScalarParameterValue(TEXT("DissolveDuration"), 0.25f);
		Mid->SetScalarParameterValue(TEXT("FormStrength"), 0.0f);
		Mid->SetScalarParameterValue(TEXT("FormPulse"), 0.0f);
		Mid->SetScalarParameterValue(TEXT("FormMantle"), 0.0f);
		BodyMaterials.Add(Mid);
		Mesh->SetMaterial(Index, Mid);
	}
	for (int32 Index = 0; Index < 2; ++Index)
	{
		UStaticMeshComponent* Part = NewObject<UStaticMeshComponent>(this, NAME_None, RF_Transient);
		Part->SetMobility(EComponentMobility::Movable);
		Part->SetupAttachment(RootComponent);
		Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Part->SetGenerateOverlapEvents(false);
		Part->SetCanEverAffectNavigation(false);
		Part->SetCastShadow(false);
		Part->SetReceivesDecals(false);
		Part->SetStaticMesh(Wing);
		Part->ComponentTags.Add(TEXT("CountessDemonMantle"));
		AddInstanceComponent(Part);
		Part->RegisterComponent();
		UMaterialInstanceDynamic* Mid = UMaterialInstanceDynamic::Create(Body, this);
		Mid->SetScalarParameterValue(TEXT("FormMantle"), 1.0f);
		Mid->SetScalarParameterValue(TEXT("FormOpacity"), 0.0f);
		Mid->SetScalarParameterValue(TEXT("FormStrength"), 1.0f);
		Mid->SetScalarParameterValue(TEXT("FormPulse"), 0.0f);
		for (int32 Slot = 0; Slot < FMath::Max(1, Part->GetNumMaterials()); ++Slot) { Part->SetMaterial(Slot, Mid); }
		MantleParts.Add(Part); MantleMaterials.Add(Mid);
	}
	UStaticMesh* Shroud = LoadObject<UStaticMesh>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/Reference20261024/SM_CountessDemonShroud.SM_CountessDemonShroud"));
	UMaterialInterface* ShroudMaterial = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/DemonSilhouette20261024/M_CountessDemonEntryShell.M_CountessDemonEntryShell"));
	if (Shroud && ShroudMaterial)
	{
		for (int32 Index = 0; Index < 3; ++Index)
		{
			UStaticMeshComponent* Part = NewObject<UStaticMeshComponent>(this, NAME_None, RF_Transient);
			Part->SetMobility(EComponentMobility::Movable);
			Part->SetupAttachment(RootComponent);
			Part->SetStaticMesh(Shroud);
			Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			Part->SetGenerateOverlapEvents(false);
			Part->SetCanEverAffectNavigation(false);
			Part->SetCastShadow(false);
			Part->SetReceivesDecals(false);
			Part->ComponentTags.Add(TEXT("CountessDemonEntryShroud"));
			Part->SetVisibility(false);
			Part->RegisterComponent();
			UMaterialInstanceDynamic* Mid = UMaterialInstanceDynamic::Create(ShroudMaterial, this);
			Mid->SetScalarParameterValue(TEXT("RuinEnergy"), .72f - Index * .17f);
			Part->SetMaterial(0, Mid);
			EntryShrouds.Add(Part);
			EntryShroudMaterials.Add(Mid);
		}
	}
	EntryGather = MakeFormTemplate(this,
		TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessBloodSealGather.P_CountessBloodSealGather"));
	EntryBurst = MakeFormTemplate(this,
		TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessBloodSealBurst.P_CountessBloodSealBurst"));
	EntryGround = MakeFormTemplate(this,
		TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessBloodSealGround.P_CountessBloodSealGround"));
	ShadowBurst = MakeFormTemplate(this,
		TEXT("/Game/ParagonCountess/FX/Particles/Abilities/BlinkStrike/FX/p_Countess_ShadowCloneBurst.p_Countess_ShadowCloneBurst"));
	EyeLoop = LoadObject<UParticleSystem>(nullptr,
		TEXT("/Game/ParagonCountess/FX/Particles/Abilities/Ultimate/FX/p_CountessUlt_EyeFX_Looping.p_CountessUlt_EyeFX_Looping"));
	BladeTrail = LoadObject<UParticleSystem>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessESharpTrail.P_CountessESharpTrail"));
	BladeTrailMaterial = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessESharpBladeTrail.M_CountessESharpBladeTrail"));
	bInitialized = true;
	ACountessRebirthFX::Create(Source, TEXT("S"), Source->GetActorLocation(), Source->GetActorForwardVector(), this);
	SpawnEntryPhase(0);
	UpdateMantle(0.0f, Mesh->IsVisible() && !Mesh->bHiddenInGame && !Source->IsHidden());
	UpdateEntryShroud(0.0f, Mesh->IsVisible() && !Mesh->bHiddenInGame && !Source->IsHidden());
	SetLifeSpan(Duration);
	UE_LOG(LogTemp, Display, TEXT("COUNTESS_DEMON begin seconds=%.2f body=%s slots=%d mantle=%d"),
		Duration, *GetNameSafe(Body), BodyMaterials.Num(), MantleParts.Num());
	return true;
}

FName ACountessDemonForm::FindBodySocket() const
{
	if (SourceMesh.IsValid())
	{
		for (const FName Name : {FName(TEXT("spine_03")), FName(TEXT("spine_02")), FName(TEXT("pelvis"))})
		{
			if (SourceMesh->DoesSocketExist(Name)) { return Name; }
		}
	}
	return NAME_None;
}

UParticleSystemComponent* ACountessDemonForm::SpawnFormEffect(UParticleSystem* Template, FName Socket,
	const FVector& Offset, float Scale, float Lifetime, bool bTrail)
{
	if (!Template || !SourceMesh.IsValid())
	{
		UE_LOG(LogTemp, Warning, TEXT("COUNTESS_DEMON_FX skipped template=%s mesh=%d age=%.3f"),
			*GetNameSafe(Template), SourceMesh.IsValid(), GetVisualAge());
		return nullptr;
	}
	UParticleSystemComponent* Particle = NewObject<UParticleSystemComponent>(this, NAME_None, RF_Transient);
	Particle->bAutoActivate = false;
	Particle->bAutoDestroy = false;
	Particle->SetupAttachment(SourceMesh.Get(), Socket);
	Particle->SetTemplate(Template);
	Particle->SetRelativeLocationAndRotation(Offset, FRotator::ZeroRotator);
	Particle->SetRelativeScale3D(FVector(Scale));
	Particle->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Particle->SetGenerateOverlapEvents(false);
	Particle->SetCanEverAffectNavigation(false);
	Particle->SetCastShadow(false);
	Particle->ComponentTags.Add(TEXT("CountessSkillFX"));
	Particle->ComponentTags.Add(TEXT("CountessDemonFormFX"));
	Particle->SetActorParameter(TEXT("BoneSocketActor"), SourceCharacter.Get());
	Particle->bOverrideLODMethod = true;
	Particle->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
	AddInstanceComponent(Particle);
	Particle->RegisterComponent();
	Particle->SetLODLevel(0);
	Particle->ActivateSystem(true);
	Particle->SetLODLevel(0);
	Effects.Add({Particle, GetVisualAge() + Lifetime, bTrail});
	UE_LOG(LogTemp, Display, TEXT("COUNTESS_DEMON_FX spawn template=%s scale=%.2f seconds=%.2f age=%.3f active=%d"),
		*GetNameSafe(Template), Scale, Lifetime, GetVisualAge(), Particle->IsActive());
	return Particle;
}

void ACountessDemonForm::SpawnEntryPhase(int32 Phase)
{
	if (Phase == 0)
	{
		InhaleEffect = SpawnFormEffect(EntryGather, NAME_None, FVector(0.0f, 0.0f, 72.0f), 0.90f, 0.10f);
	}
	else if (Phase == 1)
	{
		// 본체 높이의 짧은 파열과 바닥 먹물을 분리한다. bone 축 회전으로 폭발이 눕지 않게 한다.
		SpawnFormEffect(ShadowBurst, NAME_None, FVector(0.0f, 0.0f, 78.0f), 0.82f, 0.30f);
		SpawnFormEffect(EntryBurst, NAME_None, FVector(0.0f, 0.0f, 88.0f), 0.68f, 0.34f);
		SpawnFormEffect(EntryGround, NAME_None, FVector(0.0f, 0.0f, 6.0f), 0.48f, 0.30f);
	}
	else
	{
		if (SourceMesh->DoesSocketExist(TEXT("head")))
		{
			SpawnFormEffect(EyeLoop, TEXT("head"), FVector::ZeroVector, 0.23f, FormSeconds - GetVisualAge());
		}
		for (const TCHAR* Side : {TEXT("L"), TEXT("R")})
		{
			const FName Base(*FString::Printf(TEXT("FX_WeaponBase_%s"), Side));
			const FName Tip(*FString::Printf(TEXT("FX_WeaponTip_%s"), Side));
			if (!SourceMesh->DoesSocketExist(Base) || !SourceMesh->DoesSocketExist(Tip)) { continue; }
			if (UParticleSystemComponent* Trail = SpawnFormEffect(BladeTrail, NAME_None,
				FVector::ZeroVector, 1.0f, FormSeconds - GetVisualAge(), true))
			{
				if (BladeTrailMaterial) { Trail->SetMaterial(0, BladeTrailMaterial); }
				Trail->BeginTrails(Base, Tip, ETrailWidthMode_FromCentre, 0.22f);
				Trail->SetLODLevel(0);
			}
		}
	}
}

void ACountessDemonForm::UpdateMantle(float Age, bool bVisible)
{
	if (!SourceMesh.IsValid() || !SourceCharacter.IsValid()) { return; }
	const FVector Forward = SourceCharacter->GetActorForwardVector();
	const FVector Side = SourceCharacter->GetActorRightVector();
	const FName Socket = FindBodySocket();
	const FVector Center = Socket.IsNone() ? SourceCharacter->GetActorLocation() + FVector(0.0f, 0.0f, 35.0f) :
		SourceMesh->GetSocketLocation(Socket);
	const float Reveal = FMath::SmoothStep(0.12f, 0.44f, Age);
	const float Opening = 1.0f + 0.10f * FMath::Exp(-FMath::Square((Age - 0.28f) / 0.18f));
	const float Breathing = 1.0f + 0.035f * FMath::Sin(Age * 3.7f);
	const float Fade = FMath::SmoothStep(0.0f, 0.3f, GetFormRemaining());
	for (int32 Index = 0; Index < MantleParts.Num(); ++Index)
	{
		const float Sign = Index == 0 ? -1.0f : 1.0f;
		const FVector Position = Center - Forward * 18.0f + Side * Sign * 34.0f + FVector(0.0f, 0.0f, 6.0f);
		FRotator Rotation = Forward.Rotation();
		Rotation.Yaw += Sign * (24.0f + 6.0f * Reveal);
		Rotation.Roll = Sign * (14.0f + 4.0f * FMath::Sin(Age * 2.6f));
		const FVector Size = MantleParts[Index]->GetStaticMesh()->GetBoundingBox().GetSize();
		const FVector Scale(28.0f / FMath::Max(1.0f, Size.X), 82.0f * Opening * Breathing / FMath::Max(1.0f, Size.Y),
			112.0f * Opening * Breathing / FMath::Max(1.0f, Size.Z));
		const FVector Pivot = MantleParts[Index]->GetStaticMesh()->GetBoundingBox().GetCenter() * Scale;
		MantleParts[Index]->SetWorldTransform(FTransform(Rotation, Position - Rotation.RotateVector(Pivot), Scale));
		MantleParts[Index]->SetVisibility(bVisible && Reveal * Fade > 0.001f);
		MantleMaterials[Index]->SetScalarParameterValue(TEXT("FormOpacity"), Reveal * Fade);
		MantleMaterials[Index]->SetScalarParameterValue(TEXT("FormPulse"), FMath::Exp(-FMath::Square((Age - 0.32f) / 0.12f)));
	}
}

void ACountessDemonForm::UpdateEntryShroud(float Age, bool bVisible)
{
	if (!SourceCharacter.IsValid()) { return; }
	// 응축하는 검은 몸체가 먼저 본체를 감싸고, 붉은 틈으로 갈라지며 새 외형을 드러낸다.
	// 긴 변신 수명과는 독립적으로 0.9초 뒤 모든 진입 껍질을 제거한다.
	if (Age >= .90f)
	{
		for (UStaticMeshComponent* Part : EntryShrouds) { if (Part) { Part->DestroyComponent(); } }
		EntryShrouds.Reset();
		EntryShroudMaterials.Reset();
		return;
	}
	for (int32 Index = 0; Index < EntryShrouds.Num(); ++Index)
	{
		const float LocalAge = Age - Index * .035f;
		const float Gather = FMath::SmoothStep(0.0f, .17f, LocalAge);
		const float Release = FMath::SmoothStep(.15f, .50f, LocalAge);
		// 정면의 막이 먼저 갈라져 발광 능선이 드러난다. 잔여 외곽만 짧게 소멸한다.
		const float Fade = 1.0f - FMath::SmoothStep(.24f, .60f, LocalAge);
		const float Show = FMath::SmoothStep(0.0f, .055f, LocalAge) * Fade;
		const float Diameter = FMath::Lerp(255.0f, 155.0f, Gather) + Release * (90.0f + Index * 21.0f);
		const float Height = 222.0f + Release * (42.0f + Index * 15.0f);
		const FVector Center = SourceCharacter->GetActorLocation() + FVector(0, 0, 20.0f + Release * 32.0f);
		FRotator Rotation = SourceCharacter->GetActorRotation();
		Rotation.Yaw += Index * 119.0f + LocalAge * (Index == 1 ? -210.0f : 175.0f);
		UStaticMeshComponent* Part = EntryShrouds[Index];
		const FBox Bounds = Part->GetStaticMesh()->GetBoundingBox();
		const FVector SourceSize = Bounds.GetSize().ComponentMax(FVector(1.0f));
		const FVector Scale(Diameter / SourceSize.X, Diameter / SourceSize.Y, Height / SourceSize.Z);
		Part->SetWorldTransform(FTransform(Rotation, Center - Rotation.RotateVector(Bounds.GetCenter() * Scale), Scale));
		Part->SetVisibility(bVisible && Show > .005f);
		const float LayerOpacity = Index == 0 ? .85f : (Index == 1 ? .40f : .26f);
		EntryShroudMaterials[Index]->SetScalarParameterValue(TEXT("CloneOpacity"), Show * LayerOpacity);
		EntryShroudMaterials[Index]->SetScalarParameterValue(TEXT("RuinErode"), Release);
		EntryShroudMaterials[Index]->SetScalarParameterValue(TEXT("RuinPulse"), FMath::Exp(-FMath::Square((LocalAge - .23f) / .12f)));
		EntryShroudMaterials[Index]->SetScalarParameterValue(TEXT("ReferenceAge"), FMath::Max(0.0f, LocalAge));
	}
}

float ACountessDemonForm::GetVisualAge() const
{
	return bInitialized && GetWorld() ? FMath::Max(0.0f, static_cast<float>(GetWorld()->GetTimeSeconds() - StartedAt)) : 0.0f;
}

float ACountessDemonForm::GetFormRemaining() const
{
	return bInitialized && !bStopped ? FMath::Max(0.0f, FormSeconds - GetVisualAge()) : 0.0f;
}

void ACountessDemonForm::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!bInitialized || bStopped || !SourceCharacter.IsValid() || !SourceMesh.IsValid() ||
		SourceCharacter->IsActorBeingDestroyed() || GetFormRemaining() <= 0.0f) { StopForm(); return; }
	const float Age = GetVisualAge();
	const bool bVisible = SourceMesh->IsVisible() && !SourceMesh->bHiddenInGame && !SourceCharacter->IsHidden();
	if (EntryPhase == 0 && Age >= 0.08f) { SpawnEntryPhase(1); EntryPhase = 1; }
	if (EntryPhase == 1 && Age >= EntrySeconds) { SpawnEntryPhase(2); EntryPhase = 2; }
	const float Strength = FMath::SmoothStep(0.0f, EntrySeconds, Age);
	const float Pulse = FMath::Exp(-FMath::Square((Age - 0.32f) / 0.12f));
	for (UMaterialInstanceDynamic* Mid : BodyMaterials)
	{
		Mid->SetScalarParameterValue(TEXT("FormStrength"), Strength);
		Mid->SetScalarParameterValue(TEXT("FormPulse"), Pulse);
	}
	if (InhaleEffect.IsValid())
	{
		const float Inhale = FMath::SmoothStep(0.0f, 0.10f, Age);
		InhaleEffect->SetRelativeScale3D(FVector(FMath::Lerp(0.90f, 0.20f, Inhale)));
	}
	UpdateMantle(Age, bVisible);
	UpdateEntryShroud(Age, bVisible);
	for (int32 Index = Effects.Num() - 1; Index >= 0; --Index)
	{
		UParticleSystemComponent* Particle = Effects[Index].Particle.Get();
		if (!Particle || Age >= Effects[Index].Until)
		{
			if (Particle) { if (Effects[Index].bTrail) { Particle->EndTrails(); } Particle->DestroyComponent(); }
			Effects.RemoveAtSwap(Index);
		}
		else { Particle->SetVisibility(bVisible); }
	}
	constexpr float AuditTimes[] = {0.10f, 0.20f, 0.35f, 0.50f, 1.20f};
	for (int32 Index = 0; Index < UE_ARRAY_COUNT(AuditTimes); ++Index)
	{
		const uint8 Bit = static_cast<uint8>(1u << Index);
		if ((VisualAuditMask & Bit) || Age < AuditTimes[Index]) { continue; }
		VisualAuditMask |= Bit;
		int32 ActiveSystems = 0;
		int32 LiveParticles = 0;
		for (const FEffectLease& Effect : Effects)
		{
			if (Effect.Particle.IsValid())
			{
				ActiveSystems += Effect.Particle->IsActive() ? 1 : 0;
				LiveParticles += Effect.Particle->GetNumActiveParticles();
			}
		}
		UE_LOG(LogTemp, Display, TEXT("COUNTESS_DEMON_SAMPLE age=%.3f active_systems=%d live_particles=%d mantle=%d visible=%d"),
			Age, ActiveSystems, LiveParticles, MantleParts.Num(), bVisible);
	}
}

void ACountessDemonForm::RestoreSource()
{
	if (SourceMesh.IsValid())
	{
		for (int32 Index = 0; Index < BodyMaterials.Num(); ++Index)
		{
			if (OriginalMaterials.IsValidIndex(Index) && SourceMesh->GetMaterial(Index) == BodyMaterials[Index])
			{
				SourceMesh->SetMaterial(Index, OriginalMaterials[Index]);
			}
		}
	}
	BodyMaterials.Reset();
	OriginalMaterials.Reset();
	for (const FEffectLease& Effect : Effects)
	{
		if (Effect.Particle.IsValid())
		{
			if (Effect.bTrail) { Effect.Particle->EndTrails(); }
			Effect.Particle->DestroyComponent();
		}
	}
	Effects.Reset();
	InhaleEffect.Reset();
	for (UStaticMeshComponent* Part : MantleParts) { if (Part) { Part->DestroyComponent(); } }
	MantleParts.Reset();
	MantleMaterials.Reset();
	for (UStaticMeshComponent* Part : EntryShrouds) { if (Part) { Part->DestroyComponent(); } }
	EntryShrouds.Reset();
	EntryShroudMaterials.Reset();
}

void ACountessDemonForm::StopForm()
{
	if (bStopped) { return; }
	bStopped = true;
	RestoreSource();
	Destroy();
}

void ACountessDemonForm::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	bStopped = true;
	RestoreSource();
	Super::EndPlay(EndPlayReason);
}
