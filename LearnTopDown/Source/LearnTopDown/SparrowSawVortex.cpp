#include "SparrowAscension.h"
#include "SparrowHarmonyFX.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Particles/ParticleSystemComponent.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleEmitter.h"
#include "Particles/ParticleLODLevel.h"
#include "Particles/ParticleModuleRequired.h"
#include "Particles/Spawn/ParticleModuleSpawn.h"
#include "Particles/Location/ParticleModuleLocationPrimitiveCylinder.h"
#include "Distributions/DistributionFloatConstant.h"
#include "ParticleEmitterInstances.h"
#include "ParticleHelper.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "TimerManager.h"

namespace
{
	TAutoConsoleVariable<int32> CVarSparrowSunArrowStyle(TEXT("Sparrow.SunArrow.Style"), 6,
		TEXT("A visual candidate: 0 restored saw, 1/2 reserved sun concepts, 3 annular vortex, 4 solar rotor, 5 energy mantle, 6 selected 20261022 A4 spiral shard tail."));
	TAutoConsoleVariable<int32> CVarSparrowSawVortex(TEXT("Sparrow.Gear.Vortex"), 1,
		TEXT("A gear rim presentation: 0 keeps the original feather texture, 1 uses vortex-textured teeth on the existing rings."));
	TAutoConsoleVariable<int32> CVarSparrowSolarConvectionAudit(TEXT("Sparrow.SunArrow.Audit"), 0,
		TEXT("Read one owned solar particle snapshot at .75 s; no asset writes."));

	UParticleSystem* LegacySpiralTemplate(int32 Kind)
	{
		static TWeakObjectPtr<UParticleSystem> Cache[3];
		if (Cache[Kind].IsValid()) { return Cache[Kind].Get(); }
		const TCHAR* Path = Kind == 0 ?
			TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Ultimate/FX/P_Sparrow_Burst.P_Sparrow_Burst") :
			TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Ultimate/FX/P_Sparrow_UltHit.P_Sparrow_UltHit");
		UParticleSystem* Source = LoadObject<UParticleSystem>(nullptr, Path);
		if (!Source) { return nullptr; }
		UParticleSystem* Runtime = DuplicateObject<UParticleSystem>(Source, GetTransientPackage(),
			MakeUniqueObjectName(GetTransientPackage(), UParticleSystem::StaticClass(), TEXT("P_SparrowLegacySpiral")));
		if (!Runtime) { return nullptr; }
		Runtime->SetFlags(RF_Transient); Runtime->ClearFlags(RF_Public | RF_Standalone);
		Runtime->Emitters.RemoveAll([Kind](UParticleEmitter* Emitter)
		{
			if (!Emitter) { return true; }
			const FName Name = Emitter->GetEmitterName();
			return Kind == 0 ? Name != TEXT("Flames2") :
				Name != TEXT("Sparks") && (Kind != 1 || Name != TEXT("SparkTrailHeads"));
		});
		if (Runtime->Emitters.IsEmpty()) { return nullptr; }
		for (UParticleEmitter* Emitter : Runtime->Emitters)
		{
			if (!Emitter || !Emitter->IsIn(Runtime)) { return nullptr; }
			Emitter->UpdateModuleLists();
		}
		Cache[Kind] = Runtime;
		return Runtime;
	}

	void LegacySpiralPulse(AActor* Owner, int32 Kind, const FVector& Point, const FRotator& Rotation,
		const FVector& Scale, float Lifetime, float Speed)
	{
		if (!IsValid(Owner) || !Owner->GetWorld()) { return; }
		UParticleSystem* Template = LegacySpiralTemplate(Kind);
		if (!Template) { return; }
		const FTransform Transform(Rotation, Point, Scale);
		ASparrowAscensionAccent* Accent = Owner->GetWorld()->SpawnActorDeferred<ASparrowAscensionAccent>(
			ASparrowAscensionAccent::StaticClass(), Transform, Owner, Cast<APawn>(Owner), ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
		if (!Accent) { return; }
		Accent->Tags.Add(TEXT("SparrowLegacySpiralA4Accent"));
		Accent->InitializeStudyPulse(Template, Lifetime, Speed);
		Accent->FinishSpawning(Transform);
	}

	void LegacySpiralShard(AActor* Owner, const FVector& Point, const FVector& Direction, float Scale, float Lifetime, float Speed)
	{
		LegacySpiralPulse(Owner, 0, Point, FRotationMatrix::MakeFromZ(Direction).Rotator(),
			FVector(Scale, Scale, Scale * 1.35f), Lifetime, Speed);
	}

	UParticleSystem* SolarConvectionTemplate(bool bMeshFlames)
	{
		static TWeakObjectPtr<UParticleSystem> CoreCache;
		static TWeakObjectPtr<UParticleSystem> FlameCache;
		TWeakObjectPtr<UParticleSystem>& Cache = bMeshFlames ? FlameCache : CoreCache;
		if (Cache.IsValid()) { return Cache.Get(); }
		UParticleSystem* Source = LoadObject<UParticleSystem>(nullptr,
			TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Ultimate/FX/P_Sparrow_Burst.P_Sparrow_Burst"));
		const int32 SourceIndex = bMeshFlames ? 7 : 0;
		if (!Source || !Source->Emitters.IsValidIndex(SourceIndex)) { return nullptr; }
		UParticleSystem* Runtime = DuplicateObject<UParticleSystem>(Source, GetTransientPackage(),
			MakeUniqueObjectName(GetTransientPackage(), UParticleSystem::StaticClass(), bMeshFlames ? TEXT("SparrowSolarMeshConvection") : TEXT("SparrowSolarPlasmaConvection")));
		if (!Runtime) { return nullptr; }
		Runtime->SetFlags(RF_Transient); Runtime->ClearFlags(RF_Public | RF_Standalone);
		for (int32 Index = Runtime->Emitters.Num() - 1; Index >= 0; --Index)
		{
			if (Index != SourceIndex) { Runtime->Emitters.RemoveAt(Index); }
		}
		UParticleEmitter* Emitter = Runtime->Emitters[0];
		if (!Emitter || !Emitter->IsIn(Runtime)) { return nullptr; }
		// Native source audit: #0 owns the 8x8 animated plasma (200-400 cm,
		// .4-.9 s); #7 owns SM_ShockwaveFlame, mesh overrides and DP erosion.
		// Preserve their material/sub-UV/size-over-life/color/erosion chains.
		// The owned copy repeats small local bursts for the slow A projectile.
		for (UParticleLODLevel* LOD : Emitter->LODLevels)
		{
			if (!LOD || !LOD->RequiredModule || !LOD->SpawnModule ||
				!LOD->RequiredModule->IsIn(Runtime) || !LOD->SpawnModule->IsIn(Runtime)) { return nullptr; }
			LOD->bEnabled = true;
			LOD->RequiredModule->bUseLocalSpace = true;
			LOD->RequiredModule->bKillOnDeactivate = true;
			LOD->RequiredModule->EmitterLoops = 0;
			LOD->RequiredModule->EmitterDuration = bMeshFlames ? .24f : .20f;
			LOD->RequiredModule->EmitterDurationLow = LOD->RequiredModule->EmitterDuration;
			LOD->RequiredModule->bEmitterDurationUseRange = false;
			// A small CPU SubUV emitter gives bounded, owner-local convection.
			// It does not keep the source GPU burst's cached world-space simulation.
			if (!bMeshFlames)
			{
				LOD->TypeDataModule = nullptr;
				// Exact source graph audit: opacity = SubUV.A * ParticleAlpha
				// - .5 * RelativeTime. With .25 starting alpha this erases even
				// the densest texels before one third of particle life. The owned
				// SubUV material preserves atlas shape without that subtraction.
				if (UMaterialInterface* OwnedPlasma = LoadObject<UMaterialInterface>(nullptr,
					TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowReleaseWisps.M_SparrowReleaseWisps")))
				{
					LOD->RequiredModule->Material = OwnedPlasma;
				}
			}
			const auto SetConstant = [](FRawDistributionFloat& Raw, UObject* Owner, float Value)
			{
				UDistributionFloatConstant* Distribution = NewObject<UDistributionFloatConstant>(Owner, NAME_None, RF_Transient);
				Distribution->Constant = Value; Distribution->bCanBeBaked = false;
				Raw = FRawDistributionFloat(); Raw.Distribution = Distribution;
			};
			SetConstant(LOD->SpawnModule->Rate, LOD->SpawnModule, 0.0f);
			SetConstant(LOD->SpawnModule->RateScale, LOD->SpawnModule, 1.0f);
			// The source is an explosion: Cylinder multiplies its unnormalised
			// radial offset by 20-30 (#0) or 80 (#7), ejecting the core in a few
			// frames. Convection must remain in the projectile's central volume.
			// Keep its flipbook/erosion lifetime, but remove that spatial impulse.
			LOD->RequiredModule->EmitterOrigin = FVector::ZeroVector;
			for (UParticleModule* Module : LOD->Modules)
			{
				if (UParticleModuleLocationPrimitiveCylinder* Cylinder = Cast<UParticleModuleLocationPrimitiveCylinder>(Module))
				{
					if (!Cylinder->IsIn(Runtime)) { return nullptr; }
					Cylinder->Velocity = false; Cylinder->RadialVelocity = false;
					Cylinder->SurfaceOnly = false;
					SetConstant(Cylinder->StartRadius, Cylinder, bMeshFlames ? 14.0f : 6.0f);
					SetConstant(Cylinder->StartHeight, Cylinder, bMeshFlames ? 12.0f : 8.0f);
				}
			}
			LOD->SpawnModule->BurstList.Reset();
			FParticleBurst& Burst = LOD->SpawnModule->BurstList.AddDefaulted_GetRef();
			Burst.Count = bMeshFlames ? 3 : 4; Burst.CountLow = -1; Burst.Time = 0.0f;
		}
		Runtime->bUseFixedRelativeBoundingBox = false;
		Emitter->UpdateModuleLists();
		Cache = Runtime;
		return Runtime;
	}

	void AuditSolarConvection(UParticleSystemComponent* Component)
	{
		if (!Component) { return; }
		Component->ForceAsyncWorkCompletion(UParticleSystemComponent::STALL);
		for (FParticleEmitterInstance* Instance : Component->EmitterInstances)
		{
			if (!Instance) { continue; }
			float MaxRadius = 0.0f, MaxSize = 0.0f, MaxAlpha = 0.0f;
			for (int32 Index = 0; Index < Instance->ActiveParticles; ++Index)
			{
				if (const FBaseParticle* Particle = Instance->GetParticle(Index))
				{
					MaxRadius = FMath::Max(MaxRadius, static_cast<float>(Particle->Location.Size()));
					MaxSize = FMath::Max(MaxSize, Particle->Size.GetAbsMax());
					MaxAlpha = FMath::Max(MaxAlpha, Particle->Color.A);
				}
			}
			UE_LOG(LogTemp, Display, TEXT("SPARROW_SOLAR_CONVECTION_STATE component=%s active=%d loops=%d radius=%.2f size=%.2f alpha=%.3f scale=%s material=%s local=%d"),
				*Component->GetName(), Instance->ActiveParticles, Instance->LoopCount, MaxRadius, MaxSize, MaxAlpha,
				*Component->GetComponentScale().ToString(), *GetPathNameSafe(Instance->CurrentMaterial),
				Instance->CurrentLODLevel && Instance->CurrentLODLevel->RequiredModule ? static_cast<int32>(Instance->CurrentLODLevel->RequiredModule->bUseLocalSpace) : -1);
		}
	}
}

void ASparrowGearArrow::InitializeSawVortex()
{
	const int32 SunStyle = FMath::Clamp(CVarSparrowSunArrowStyle.GetValueOnGameThread(), 0, 6);
	if (SunStyle == 6)
	{
		if (ASparrowHarmonyFX::Create(GetOwner(), TEXT("A"), GetActorLocation(), GetFlightDirection(), .2f, this))
		{
			// Two distinct silhouettes travel together; the existing central sweep owns the shared hit once.
			const FVector Offset(0.0f, -ASparrowHarmonyFX::APairHalfSpacing, 0.0f);
			for (USceneComponent* Part : {static_cast<USceneComponent*>(ArrowMesh.Get()),
				static_cast<USceneComponent*>(TrailParticle.Get()), Rotor.Get(), static_cast<USceneComponent*>(CondensedCore.Get())})
			{
				Part->SetRelativeLocation(Part->GetRelativeLocation() + Offset);
			}
			Tags.AddUnique(TEXT("SparrowPairedA"));
		}
		// User-selected history 05: fresh_studies A4. Restore its small native
		// feather rings, visible central arrow, .36 core and original short trail.
		// Newer vortex/claw/orb layers and flight crackle must not leak into it.
		Tags.AddUnique(TEXT("SparrowLegacySpiralA4"));
		ArrowMesh->SetRelativeScale3D(FVector(1.35f));
		ArrowMesh->SetVisibility(true);
		TrailParticle->SetRelativeScale3D(FVector(.48f, .58f, .58f));
		CondensedCore->SetRelativeScale3D(FVector(.36f));
		// History 53 keeps the compact spiral shards and original feather rings.
		const float LaneOffset = Tags.Contains(TEXT("SparrowPairedA")) ? -ASparrowHarmonyFX::APairHalfSpacing : 0.0f;
		for (float Offset : {-20.0f, 20.0f})
		{
			const FVector Point = GetActorLocation() + GetActorRightVector() * (LaneOffset + Offset) + FVector::UpVector * FMath::Abs(Offset) * .3f;
			LegacySpiralShard(GetOwner(), Point, GetFlightDirection(), .23f, .22f, 2.2f);
		}
		UpdateSawVortex(0.0f, 0.0f);
		return;
	}
	// 실제 이동/피해는 화살이 유지하되 A의 비행 외형에는 원형 톱니만 남긴다.
	ArrowMesh->SetVisibility(false);
	TrailParticle->DeactivateSystem();
	TrailParticle->SetVisibility(false);
	TrailParticle->SetTemplate(nullptr);
	if (bAscendedGear)
	{
		// 원 안의 폭풍이 중앙 섬광에 묻히지 않도록 변신의 광핵만 좁힌다.
		CondensedCore->SetRelativeScale3D(FVector(.16f));
	}

	if (SunStyle == 5)
	{
		UMaterialInterface* RingSurface = LoadObject<UMaterialInterface>(nullptr,
			TEXT("/Game/TopDown/Characters/Sparrow/Materials/SunArrow20261027/M_AnnularCraftRing.M_AnnularCraftRing"));
		UMaterialInterface* AxisSurface = LoadObject<UMaterialInterface>(nullptr,
			TEXT("/Game/TopDown/Characters/Sparrow/Materials/SunArrow20261027/M_SparrowAnnularAxis.M_SparrowAnnularAxis"));
		UMaterialInterface* CuffSurface = LoadObject<UMaterialInterface>(nullptr,
			TEXT("/Game/TopDown/Characters/Sparrow/Materials/SunArrow20261027/M_AnnularCraftCuff.M_AnnularCraftCuff"));
		UStaticMesh* CuffMesh = LoadObject<UStaticMesh>(nullptr,
			TEXT("/Game/TopDown/Characters/Sparrow/FX/SunArrow20261027/SM_AnnularCraftCuff.SM_AnnularCraftCuff"));
		if (RingSurface && AxisSurface && CuffSurface && CuffMesh)
		{
			Tags.Append({TEXT("SparrowAnnularArrow"), TEXT("SparrowAnnularCraftArrow")});
			if (bAscendedGear) { Tags.AddUnique(TEXT("SparrowAscendedAnnularArrow")); }
			// Restore the A3 arrow and ring proportions. The open mantle has no
			// central orb or detached cutting claws; damage still belongs to A.
			ArrowMesh->SetRelativeLocation(FVector(10.0f, 0.0f, 0.0f));
			ArrowMesh->SetRelativeScale3D(FVector(1.05f, 1.05f, 1.1475f));
			for (int32 Slot = 0; Slot < FMath::Max(1, ArrowMesh->GetNumMaterials()); ++Slot) { ArrowMesh->SetMaterial(Slot, AxisSurface); }
			ArrowMesh->SetVisibility(true);
			ArrowMesh->ComponentTags.AddUnique(TEXT("SparrowAnnularAxis"));
			CondensedCore->DeactivateSystem(); CondensedCore->SetVisibility(false); CondensedCore->SetTemplate(nullptr);
			for (int32 Index = 0; Index < FeatherRings.Num(); ++Index)
			{
				UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(RingSurface, this);
				Material->SetScalarParameterValue(TEXT("Index"), static_cast<float>(Index));
				Material->SetScalarParameterValue(TEXT("Ascended"), bAscendedGear ? 1.0f : 0.0f);
				FeatherRings[Index]->SetMaterial(0, Material); FeatherRings[Index]->SetVisibility(true);
				FeatherRings[Index]->ComponentTags.AddUnique(TEXT("SparrowAnnularCraftRing"));
				FeatherMaterials[Index] = Material; VortexMaterials.Add(Material);
			}
			UStaticMeshComponent* Cuff = NewObject<UStaticMeshComponent>(this);
			Cuff->SetMobility(EComponentMobility::Movable);
			Cuff->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			Cuff->SetGenerateOverlapEvents(false); Cuff->SetCanEverAffectNavigation(false);
			Cuff->SetCastShadow(false); Cuff->SetReceivesDecals(false);
			Cuff->SetupAttachment(SceneRoot); Cuff->SetStaticMesh(CuffMesh);
			Cuff->ComponentTags.Append({TEXT("SparrowSkillFX"), TEXT("SparrowAnnularCraftCuff")});
			UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(CuffSurface, this);
			Material->SetScalarParameterValue(TEXT("Ascended"), bAscendedGear ? 1.0f : 0.0f);
			Cuff->SetMaterial(0, Material); AddInstanceComponent(Cuff); Cuff->RegisterComponent();
			VortexSurfaces.Add(Cuff); VortexMaterials.Add(Material);
			UpdateSawVortex(0.0f, 0.0f);
			return;
		}
		UE_LOG(LogTemp, Warning, TEXT("SPARROW_ANNULAR_CRAFT missing authored asset; falling back to the A3 central arrow and annulus"));
	}
	if (SunStyle == 4)
	{
		UStaticMesh* Blade = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/TopDown/Characters/Sparrow/FX/SunArrow20261027/SM_SolarCrescent.SM_SolarCrescent"));
		UStaticMesh* Wake = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/TopDown/Characters/Sparrow/FX/SunArrow20261027/SM_SolarWake.SM_SolarWake"));
		UMaterialInterface* BladeSurface = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/TopDown/Characters/Sparrow/Materials/SunArrow20261027/M_SolarCrescent.M_SolarCrescent"));
		UMaterialInterface* WakeSurface = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/TopDown/Characters/Sparrow/Materials/SunArrow20261027/M_SolarWake.M_SolarWake"));
		UMaterialInterface* AxisSurface = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/TopDown/Characters/Sparrow/Materials/SunArrow20261027/M_SparrowAnnularAxis.M_SparrowAnnularAxis"));
		if (Blade && Wake && BladeSurface && WakeSurface && AxisSurface)
		{
			Tags.AddUnique(TEXT("SparrowSolarRotor"));
			for (UStaticMeshComponent* Ring : FeatherRings) { Ring->SetVisibility(false); }
			CondensedCore->DeactivateSystem(); CondensedCore->SetVisibility(false); CondensedCore->SetTemplate(nullptr);
			ArrowMesh->SetRelativeLocation(FVector(24.0f, 0.0f, 0.0f));
			ArrowMesh->SetRelativeScale3D(FVector(.82f, .82f, 1.42f));
			for (int32 Slot = 0; Slot < FMath::Max(1, ArrowMesh->GetNumMaterials()); ++Slot) { ArrowMesh->SetMaterial(Slot, AxisSurface); }
			ArrowMesh->SetVisibility(true);
			for (int32 Index = 0; Index < (bAscendedGear ? 8 : 6); ++Index)
			{
				const bool bWake = Index % 2 == 1;
				UStaticMeshComponent* Part = NewObject<UStaticMeshComponent>(this);
				Part->SetMobility(EComponentMobility::Movable);
				Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
				Part->SetGenerateOverlapEvents(false); Part->SetCanEverAffectNavigation(false);
				Part->SetCastShadow(false); Part->SetReceivesDecals(false);
				Part->SetupAttachment(SceneRoot); Part->SetStaticMesh(bWake ? Wake : Blade);
				Part->ComponentTags.Append({TEXT("SparrowSkillFX"), bWake ? TEXT("SparrowSolarWake") : TEXT("SparrowSolarCrescent")});
				UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(bWake ? WakeSurface : BladeSurface, this);
				Material->SetScalarParameterValue(TEXT("Index"), static_cast<float>(Index / 2));
				Material->SetScalarParameterValue(TEXT("Ascended"), bAscendedGear ? 1.0f : 0.0f);
				Part->SetMaterial(0, Material); AddInstanceComponent(Part); Part->RegisterComponent();
				VortexSurfaces.Add(Part); VortexMaterials.Add(Material);
			}
			UParticleSystem* Plasma = SolarConvectionTemplate(false);
			UParticleSystem* Flame = SolarConvectionTemplate(true);
			if (Plasma && Flame)
			{
				// Replace the rejected smooth generated wakes with real animated
				// plasma and authored mesh-flame erosion. Both components already
				// belong to this arrow and disappear with it; no world timer remains.
				for (UStaticMeshComponent* Part : VortexSurfaces)
				{
					if (Part->ComponentTags.Contains(TEXT("SparrowSolarWake"))) { Part->SetVisibility(false); }
				}
				const auto SetConvection = [](UParticleSystemComponent* Particle, UParticleSystem* Template,
					const FVector& Location, const FVector& Scale, FName Tag)
				{
					Particle->DeactivateSystem(); Particle->SetTemplate(Template);
					Particle->SetRelativeLocation(Location); Particle->SetRelativeRotation(FRotator(90.0f, 0.0f, 0.0f));
					Particle->SetRelativeScale3D(Scale); Particle->SetVisibility(true);
					Particle->bOverrideLODMethod = true; Particle->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
					Particle->ComponentTags.AddUnique(Tag);
					Particle->SetLODLevel(0); Particle->ActivateSystem(true); Particle->SetLODLevel(0);
				};
				// Source sprite size is 200-400 cm with a .25-.5 life multiplier:
				// .66 gives roughly 33-132 cm convection inside the 160 cm rotor.
				// Source mesh diameter 113.3 cm * 3-4 start-size * .23 gives 78-104 cm.
				SetConvection(CondensedCore, Plasma, FVector(22.0f, 0.0f, 0.0f), FVector(bAscendedGear ? .74f : .66f), TEXT("SparrowSolarPlasmaCore"));
				SetConvection(TrailParticle, Flame, FVector(13.0f, 0.0f, 0.0f), FVector(bAscendedGear ? .26f : .23f), TEXT("SparrowSolarMeshFlame"));
				Tags.AddUnique(TEXT("SparrowAuthoredSolarConvection"));
			}
			else
			{
				UE_LOG(LogTemp, Warning, TEXT("SPARROW_SOLAR_CONVECTION source unavailable; retaining owned wake fallback"));
			}
			UStaticMesh* HeartMesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Sphere.Sphere"));
			UMaterialInterface* HeartSurface = LoadObject<UMaterialInterface>(nullptr,
				TEXT("/Game/TopDown/Characters/Sparrow/Materials/Renaissance20261027/M_RenSPlasma.M_RenSPlasma"));
			if (HeartMesh && HeartSurface)
			{
				// One small curved atlas surface gives the contained sun a body.
				// It occupies the rear 72 cm of the 160 cm rotor; the forward
				// arrow tip and three independently rotating teeth stay readable.
				UStaticMeshComponent* Heart = NewObject<UStaticMeshComponent>(this);
				Heart->SetMobility(EComponentMobility::Movable);
				Heart->SetCollisionEnabled(ECollisionEnabled::NoCollision);
				Heart->SetGenerateOverlapEvents(false); Heart->SetCanEverAffectNavigation(false);
				Heart->SetCastShadow(false); Heart->SetReceivesDecals(false);
				Heart->SetupAttachment(SceneRoot); Heart->SetStaticMesh(HeartMesh);
				Heart->ComponentTags.Append({TEXT("SparrowSkillFX"), TEXT("SparrowSolarHeart")});
				UMaterialInstanceDynamic* HeartMaterial = UMaterialInstanceDynamic::Create(HeartSurface, this);
				HeartMaterial->SetScalarParameterValue(TEXT("PulseAge"), 100.0f);
				HeartMaterial->SetScalarParameterValue(TEXT("Progress"), .38f);
				HeartMaterial->SetScalarParameterValue(TEXT("Ascended"), bAscendedGear ? 1.0f : 0.0f);
				Heart->SetMaterial(0, HeartMaterial); AddInstanceComponent(Heart); Heart->RegisterComponent();
				VortexSurfaces.Add(Heart); VortexMaterials.Add(HeartMaterial);
			}
			UpdateSawVortex(0.0f, 0.0f);
			return;
		}
		UE_LOG(LogTemp, Warning, TEXT("SPARROW_SOLAR_ROTOR missing authored asset; keeping installed saw"));
	}
	if (SunStyle == 3 || SunStyle == 5)
	{
		UMaterialInterface* RingSurface = LoadObject<UMaterialInterface>(nullptr,
			TEXT("/Game/TopDown/Characters/Sparrow/Materials/SunArrow20261027/M_SparrowAnnularRing.M_SparrowAnnularRing"));
		UMaterialInterface* AxisSurface = LoadObject<UMaterialInterface>(nullptr,
			TEXT("/Game/TopDown/Characters/Sparrow/Materials/SunArrow20261027/M_SparrowAnnularAxis.M_SparrowAnnularAxis"));
		if (RingSurface && AxisSurface)
		{
			Tags.AddUnique(TEXT("SparrowAnnularArrow"));
			if (bAscendedGear) { Tags.AddUnique(TEXT("SparrowAscendedAnnularArrow")); }
			ArrowMesh->SetRelativeLocation(FVector(10.0f, 0.0f, 0.0f));
			ArrowMesh->SetRelativeScale3D(FVector(1.05f, 1.05f, 1.1475f));
			for (int32 Slot = 0; Slot < FMath::Max(1, ArrowMesh->GetNumMaterials()); ++Slot) { ArrowMesh->SetMaterial(Slot, AxisSurface); }
			ArrowMesh->SetVisibility(true);
			ArrowMesh->ComponentTags.AddUnique(TEXT("SparrowAnnularAxis"));
			CondensedCore->DeactivateSystem(); CondensedCore->SetVisibility(false); CondensedCore->SetTemplate(nullptr);
			for (int32 Index = 0; Index < FeatherRings.Num(); ++Index)
			{
				UStaticMeshComponent* Ring = FeatherRings[Index];
				UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(RingSurface, this);
				Material->SetScalarParameterValue(TEXT("Index"), static_cast<float>(Index));
				Material->SetScalarParameterValue(TEXT("Ascended"), bAscendedGear ? 1.0f : 0.0f);
				Ring->SetMaterial(0, Material); Ring->SetVisibility(true);
				Ring->ComponentTags.AddUnique(TEXT("SparrowAnnularRing"));
				FeatherMaterials[Index] = Material; VortexMaterials.Add(Material);
			}
			UpdateSawVortex(0.0f, 0.0f);
			return;
		}
		UE_LOG(LogTemp, Warning, TEXT("SPARROW_ANNULAR missing authored surface; retaining installed saw"));
	}
	if (SunStyle > 0 && SunStyle < 3)
	{
		UStaticMesh* Sphere = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Sphere.Sphere"));
		UStaticMesh* Prominence = LoadObject<UStaticMesh>(nullptr,
			SunStyle == 2 ? TEXT("/Game/TopDown/Characters/Sparrow/FX/SunArrow20261027/SM_SparrowSunOrbit.SM_SparrowSunOrbit") :
			TEXT("/Game/TopDown/Characters/Sparrow/FX/SunArrow20261027/SM_SparrowSunProminence.SM_SparrowSunProminence"));
		UStaticMesh* Tail = LoadObject<UStaticMesh>(nullptr,
			TEXT("/Game/TopDown/Characters/Sparrow/FX/SunArrow20261027/SM_SparrowSunTail.SM_SparrowSunTail"));
		const auto SunMaterial = [](const TCHAR* Name)
		{
			const FString Path = FString::Printf(TEXT("/Game/TopDown/Characters/Sparrow/Materials/SunArrow20261027/%s.%s"), Name, Name);
			return LoadObject<UMaterialInterface>(nullptr, *Path);
		};
		UMaterialInterface* Core = SunMaterial(TEXT("M_SparrowSunCore"));
		UMaterialInterface* Corona = SunMaterial(SunStyle == 2 ? TEXT("M_SparrowSunOrbit") : TEXT("M_SparrowSunCorona"));
		UMaterialInterface* Wake = SunMaterial(TEXT("M_SparrowSunTail"));
		UMaterialInterface* Axis = SunMaterial(TEXT("M_SparrowSunAxis"));
		// 저작이 끝나지 않은 시안은 기존 외형으로 복귀한다. 실제 화살은 그대로 유지한다.
		if (Sphere && Prominence && Tail && Core && Corona && Wake && Axis)
		{
			Tags.AddUnique(TEXT("SparrowSunArrow"));
			Tags.AddUnique(SunStyle == 2 ? TEXT("SparrowSunArrow2") : TEXT("SparrowSunArrow1"));
			if (bAscendedGear) { Tags.AddUnique(TEXT("SparrowAscendedSunArrow")); }
			for (UStaticMeshComponent* Ring : FeatherRings) { if (Ring) { Ring->SetVisibility(false); } }
			CondensedCore->DeactivateSystem();
			CondensedCore->SetVisibility(false);
			CondensedCore->SetTemplate(nullptr);
			// 원본 화살의 끝은 로컬 -Z다. 기존 90도 회전을 유지하고 태양 앞에 촉을 드러낸다.
			ArrowMesh->SetRelativeLocation(FVector(20.0f, 0.0f, 0.0f));
			ArrowMesh->SetRelativeScale3D(FVector(.48f, .48f, 1.70f));
			for (int32 Slot = 0; Slot < FMath::Max(1, ArrowMesh->GetNumMaterials()); ++Slot) { ArrowMesh->SetMaterial(Slot, Axis); }
			ArrowMesh->SetVisibility(true);
			ArrowMesh->ComponentTags.AddUnique(TEXT("SparrowSunAxis"));
			const auto AddSunPart = [this, SunStyle](UStaticMesh* Mesh, UMaterialInterface* Surface, const TCHAR* Tag, int32 Index)
			{
				UStaticMeshComponent* Part = NewObject<UStaticMeshComponent>(this);
				Part->SetMobility(EComponentMobility::Movable);
				Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
				Part->SetGenerateOverlapEvents(false);
				Part->SetCanEverAffectNavigation(false);
				Part->SetCastShadow(false);
				Part->SetupAttachment(SceneRoot);
				Part->SetStaticMesh(Mesh);
				Part->SetRelativeLocation(FVector(30.0f, 0.0f, 0.0f));
				Part->ComponentTags.AddUnique(TEXT("SparrowSkillFX"));
				Part->ComponentTags.AddUnique(TEXT("SparrowSunVisual"));
				Part->ComponentTags.AddUnique(Tag);
				UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(Surface, this);
				Material->SetScalarParameterValue(TEXT("Index"), static_cast<float>(Index));
				Material->SetScalarParameterValue(TEXT("Style"), static_cast<float>(SunStyle));
				Material->SetScalarParameterValue(TEXT("Age"), 0.0f);
				Material->SetScalarParameterValue(TEXT("Pulse"), 0.0f);
				Material->SetScalarParameterValue(TEXT("Ascended"), bAscendedGear ? 1.0f : 0.0f);
				Part->SetMaterial(0, Material);
				AddInstanceComponent(Part);
				Part->RegisterComponent();
				VortexSurfaces.Add(Part);
				VortexMaterials.Add(Material);
				return Part;
			};
			AddSunPart(Sphere, Core, TEXT("SparrowSunCore"), 0)->SetRelativeScale3D(FVector(.12f));
			const int32 CoronaCount = SunStyle == 2 ? (bAscendedGear ? 4 : 3) : (bAscendedGear ? 7 : 5);
			for (int32 Index = 0; Index < CoronaCount; ++Index)
			{
				AddSunPart(Prominence, Corona, TEXT("SparrowSunCorona"), Index);
			}
			const int32 TailCount = bAscendedGear ? 6 : (SunStyle == 2 ? 5 : 4);
			for (int32 Index = 0; Index < TailCount; ++Index)
			{
				AddSunPart(Tail, Wake, TEXT("SparrowSunTail"), Index);
			}
			UpdateSawVortex(0.0f, 0.0f);
			return;
		}
		UE_LOG(LogTemp, Warning, TEXT("SPARROW_SUN missing authored asset; restored saw remains active"));
	}
	if (CVarSparrowSawVortex.GetValueOnGameThread() == 0) { return; }
	UMaterialInterface* Rim = LoadObject<UMaterialInterface>(nullptr, bAscendedGear ?
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/ArsenalAscended20261026/M_SparrowSawGearRimAscended.M_SparrowSawGearRimAscended") :
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/Arsenal20261026/M_SparrowSawGearRim.M_SparrowSawGearRim"));
	// 외곽 재질이 없어도 기존 톱니와 실제 투사체는 유지한다.
	if (!Rim) { return; }
	for (int32 Index = 0; Index < FeatherRings.Num(); ++Index)
	{
		UStaticMeshComponent* Ring = FeatherRings[Index];
		if (!Ring || !FeatherMaterials.IsValidIndex(Index)) { continue; }
		UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(Rim, this);
		if (!Material) { continue; }
		Material->SetScalarParameterValue(TEXT("Index"), static_cast<float>(Index));
		Material->SetScalarParameterValue(TEXT("Age"), 0.0f);
		Material->SetScalarParameterValue(TEXT("Pulse"), 0.0f);
		Material->SetScalarParameterValue(TEXT("Envelope"), bAscendedGear ? (Index == 0 ? 1.25f : .62f) : (Index == 0 ? 1.05f : .46f));
		// 별도 외피는 만들지 않고 기존 160/108cm 톱니 테두리 자체에 바람의 면과 능선을 입힌다.
		Ring->SetMaterial(0, Material);
		Ring->ComponentTags.AddUnique(TEXT("SparrowSawVortex"));
		Ring->ComponentTags.AddUnique(TEXT("SparrowSawRim"));
		if (bAscendedGear) { Ring->ComponentTags.AddUnique(TEXT("SparrowAscendedSawVortex")); }
		FeatherMaterials[Index] = Material;
		VortexMaterials.Add(Material);
	}
}

void ASparrowGearArrow::UpdateSawVortex(float DeltaSeconds, float ImpactPulse)
{
	VortexAge += FMath::Max(DeltaSeconds, 0.0f);
	if (Tags.Contains(TEXT("SparrowLegacySpiralA4")))
	{
		if (VortexAge >= NextSpiralEmission)
		{
			NextSpiralEmission = VortexAge + .14f;
			const float LaneOffset = Tags.Contains(TEXT("SparrowPairedA")) ? -ASparrowHarmonyFX::APairHalfSpacing : 0.0f;
			// Keep the selected spiral tail in two compact lanes with short-lived shards.
			for (int32 Index = 0; Index < 2; ++Index)
			{
				const float Phase = VortexAge * 9.0f + Index * PI;
				const FVector Point = GetActorLocation() - GetFlightDirection() * (24.0f + Index * 32.0f) +
					GetActorRightVector() * (LaneOffset + FMath::Cos(Phase) * 25.0f) + FVector::UpVector * FMath::Sin(Phase) * 25.0f;
				LegacySpiralShard(GetOwner(), Point, GetFlightDirection(), .24f, .28f, 2.0f);
			}
		}
		return;
	}
	if (Tags.Contains(TEXT("SparrowAnnularCraftArrow")))
	{
		const float Reveal = FMath::SmoothStep(0.0f, .14f, VortexAge);
		for (UStaticMeshComponent* Part : VortexSurfaces)
		{
			if (!Part || !Part->ComponentTags.Contains(TEXT("SparrowAnnularCraftCuff"))) { continue; }
			Part->SetRelativeLocation(FVector(40.0f, 0.0f, 0.0f));
			Part->SetRelativeRotation(FRotator(0.0f, 0.0f, -VortexAge * 160.0f));
			Part->SetRelativeScale3D(FVector(FMath::Lerp(.12f, 1.0f, Reveal), 1.0f, 1.0f));
		}
	}
	if (Tags.Contains(TEXT("SparrowSolarRotor")))
	{
		if (CVarSparrowSolarConvectionAudit.GetValueOnGameThread() != 0 && VortexAge >= .75f &&
			!Tags.Contains(TEXT("SparrowSolarConvectionAudited")))
		{
			Tags.AddUnique(TEXT("SparrowSolarConvectionAudited"));
			AuditSolarConvection(CondensedCore); AuditSolarConvection(TrailParticle);
		}
		const float Reveal = FMath::SmoothStep(0.0f, .12f, VortexAge);
		const float TailGrowth = FMath::Clamp((GetDistanceTravelled() + 12.0f) / 150.0f, .08f, 1.0f);
		for (int32 Index = 0; Index < VortexSurfaces.Num(); ++Index)
		{
			UStaticMeshComponent* Part = VortexSurfaces[Index];
			if (Part->ComponentTags.Contains(TEXT("SparrowSolarHeart")))
			{
				Part->SetRelativeLocation(FVector(14.0f, 0.0f, 0.0f));
				Part->SetRelativeRotation(FRotator(VortexAge * 18.0f, VortexAge * 31.0f, -VortexAge * 48.0f));
				Part->SetRelativeScale3D(FVector(.72f * FMath::Lerp(.32f, 1.0f, Reveal)));
				if (UMaterialInstanceDynamic* HeartMaterial = Cast<UMaterialInstanceDynamic>(Part->GetMaterial(0)))
				{
					HeartMaterial->SetScalarParameterValue(TEXT("Progress"), .38f + .30f * FMath::Sin(VortexAge * 2.4f));
					HeartMaterial->SetScalarParameterValue(TEXT("Envelope"), Reveal);
				}
				continue;
			}
			const int32 RotorIndex = Index / 2;
			const bool bWake = Index % 2 == 1;
			const bool bInner = RotorIndex == 3;
			const float Spin = bInner ? -VortexAge * 425.0f : VortexAge * 315.0f;
			const float Scale = (bInner ? .62f : 1.0f) * FMath::Lerp(.32f, 1.0f, Reveal) * (1.0f + ImpactPulse * .035f);
			Part->SetRelativeLocation(FVector(bInner ? 3.0f : 38.0f, 0.0f, 0.0f));
			Part->SetRelativeRotation(FRotator(bInner ? 17.0f : 0.0f, 0.0f, Spin + RotorIndex * 120.0f));
			Part->SetRelativeScale3D(FVector(bWake ? Scale * TailGrowth : Scale, Scale, Scale));
		}
	}
	if (Tags.Contains(TEXT("SparrowSunArrow")))
	{
		const bool bSolarOrbit = Tags.Contains(TEXT("SparrowSunArrow2"));
		const float Reveal = FMath::SmoothStep(0.0f, .12f, VortexAge);
		const float CoreScale = (bAscendedGear ? .90f : .85f) * FMath::Lerp(.20f, 1.0f, Reveal);
		const float TailGrowth = FMath::Clamp((GetDistanceTravelled() + 18.0f) / 180.0f, .10f, 1.0f);
		// 홍염은 균일한 회전 고리가 아니다. 비대칭 뿌리에서 작게 흔들리고, 후류만 뒤로 자란다.
		static const float CoronaRolls[] = {-28.0f, 43.0f, 126.0f, 204.0f, 283.0f, 86.0f, 247.0f};
		static const float OrbitRolls[] = {0.0f, 117.0f, 246.0f, 62.0f};
		static const float TailRolls[] = {17.0f, 112.0f, 223.0f, 306.0f, 66.0f, 264.0f};
		int32 CoronaIndex = 0;
		int32 TailIndex = 0;
		for (UStaticMeshComponent* Part : VortexSurfaces)
		{
			if (!Part) { continue; }
			if (Part->ComponentTags.Contains(TEXT("SparrowSunCore")))
			{
				Part->SetRelativeScale3D(FVector(CoreScale * (1.0f + ImpactPulse * .025f)));
				Part->SetRelativeRotation(FRotator(0.0f, VortexAge * 8.0f, VortexAge * 13.0f));
			}
			else if (Part->ComponentTags.Contains(TEXT("SparrowSunCorona")))
			{
				const float Index = static_cast<float>(CoronaIndex);
				const float Scale = (bSolarOrbit ? (.89f + .08f * static_cast<float>(CoronaIndex % 2)) : (.84f + .08f * static_cast<float>(CoronaIndex % 3))) * (bAscendedGear ? 1.08f : 1.0f);
				Part->SetRelativeScale3D(FVector(Scale, Scale, Scale) * FMath::Lerp(.60f, 1.0f, Reveal));
				Part->SetRelativeRotation(FRotator(FMath::Sin(Index * 1.8f) * 12.0f,
					FMath::Cos(Index * 1.4f) * 11.0f,
					bSolarOrbit ? OrbitRolls[CoronaIndex] + VortexAge * 156.0f :
					CoronaRolls[CoronaIndex] + FMath::Sin(VortexAge * (1.1f + Index * .11f) + Index) * 7.0f));
				++CoronaIndex;
			}
			else if (Part->ComponentTags.Contains(TEXT("SparrowSunTail")))
			{
				const float Index = static_cast<float>(TailIndex);
				const float Length = .80f + .14f * static_cast<float>(TailIndex % 3);
				const float Width = 1.12f + .15f * static_cast<float>(TailIndex % 2);
				Part->SetRelativeScale3D(FVector(Length * TailGrowth, Width, Width));
				Part->SetRelativeRotation(FRotator(FMath::Sin(VortexAge * 1.5f + Index) * 3.5f, 0.0f,
					TailRolls[TailIndex] + FMath::Sin(VortexAge * 1.3f + Index * 2.2f) * 9.0f));
				++TailIndex;
			}
		}
	}

	for (UMaterialInstanceDynamic* Material : VortexMaterials)
	{
		if (!Material) { continue; }
		Material->SetScalarParameterValue(TEXT("Age"), VortexAge);
		Material->SetScalarParameterValue(TEXT("Pulse"), ImpactPulse);
	}
}

void ASparrowGearArrow::SpawnLegacySpiralImpact(const FHitResult& Hit, bool bWorld)
{
	if (bWorld || !IsValid(GetOwner()) || !GetWorld()) { return; }
	const FVector Point = IsValid(Hit.GetActor()) ? Hit.GetActor()->GetActorLocation() : FVector(Hit.ImpactPoint);
	const FVector Direction = GetFlightDirection();
	const FVector Right = GetActorRightVector();
	LegacySpiralPulse(GetOwner(), 1, Point, Direction.Rotation(), FVector(1.05f), .32f, 1.8f);
	for (int32 Index = 0; Index < 5; ++Index)
	{
		const float Phase = Index * 2.39996f;
		LegacySpiralShard(GetOwner(), Point + Right * FMath::Cos(Phase) * 32.0f + FVector::UpVector * FMath::Sin(Phase) * 27.0f,
			Direction, .28f, .30f, 2.2f);
	}
	const TWeakObjectPtr<AActor> WeakOwner(GetOwner());
	for (int32 Index = 1; Index <= 3; ++Index)
	{
		const FVector SparkPoint = Point + Direction * (Index * 7.0f) + Right * (Index % 2 ? 18.0f : -18.0f);
		FTimerHandle Handle;
		GetWorld()->GetTimerManager().SetTimer(Handle, [WeakOwner, SparkPoint, Direction]()
		{
			if (WeakOwner.IsValid()) { LegacySpiralPulse(WeakOwner.Get(), 2, SparkPoint, Direction.Rotation(), FVector(.58f), .28f, 1.8f); }
		}, Index * .065f, false);
	}
}
