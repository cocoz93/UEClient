#include "SparrowAscendedShotFX.h"
#include "SparrowHarmonyFX.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "Particles/ParticleEmitter.h"
#include "Particles/ParticleLODLevel.h"
#include "Particles/ParticleModuleRequired.h"
#include "Particles/Light/ParticleModuleLightBase.h"
#include "Particles/Material/ParticleModuleMeshMaterial.h"
#include "Particles/TypeData/ParticleModuleTypeDataMesh.h"
#include "SparrowSkillComponent.h"
#include "TopDownCombatCharacter.h"

namespace
{
	constexpr int32 RainShaftCount = 24;
	constexpr int32 DesignRainShaftCount = 16;
	constexpr int32 MaxMeteorWakeDots = 512;
	constexpr float MeteorWakeSpacing = 12.0f;
	constexpr float MeteorWakeLife = .18f;
	TAutoConsoleVariable<int32> CVarQDesign(TEXT("Sparrow.DesignIngame.Q"), 8,
		TEXT("Q preview: 0 installed, 1 gold lances, 2 flowing sunbeams, 3 prismatic needles, 4 celestial apertures, 5 descending sanctum, 6 dawnfall, 7 gold meteor rain, 8 descending golden pillars (ascended only)."));

	UMaterialInterface* FindMeteorGold(UMaterialInterface* Original)
	{
		if (!Original) { return nullptr; }
		if (Original->GetPathName().StartsWith(TEXT("/Game/TopDown/Characters/Sparrow/Previews/QVDesign20261027/Q7SourceGold/"))) { return Original; }
		// The author manifest records these copies and verifies unchanged source hashes.
		static const TPair<const TCHAR*, const TCHAR*> Names[] = {
			{TEXT("M_Projectile_Ball"), TEXT("M_Projectile_Ball_ccab045a_Gold")},
			{TEXT("M_GlowPoint_DistShrink_MASTER"), TEXT("M_GlowPoint_DistShrink_MASTER_5d05bb99_Gold")},
			{TEXT("M_Wispy_Smoke_Trail_Projectile"), TEXT("M_Wispy_Smoke_Trail_Projectile_521379da_Gold")},
			{TEXT("M_Wisp_SplineThicken_Small"), TEXT("M_Wisp_SplineThicken_Small_db5ed33e_Gold")},
			{TEXT("M_Lensflare_TB_Soft_LDR2HDR"), TEXT("M_Lensflare_TB_Soft_LDR2HDR_d2c5f404_Gold")},
			{TEXT("M_Explosion_Smoke_Spears"), TEXT("M_Explosion_Smoke_Spears_f71b3238_Gold")},
			{TEXT("M_Hotdog_Spark_VLerp_MASTER"), TEXT("M_Hotdog_Spark_VLerp_MASTER_f8ec1941_Gold")},
			{TEXT("M_Soft_Spark_Glow"), TEXT("M_Soft_Spark_Glow_76bfc109_Gold")},
			{TEXT("M_Radial_Blur_Refraction"), TEXT("M_Radial_Blur_Refraction_412a93ce_Gold")},
			{TEXT("M_Inky_Smoke_Burst"), TEXT("M_Inky_Smoke_Burst_c6c7255b_Gold")},
			{TEXT("M_DarkFlare_DistShrink"), TEXT("M_DarkFlare_DistShrink_44ae8fca_Gold")},
			{TEXT("M_Spark_VelocityLerp_TeamColor"), TEXT("M_Spark_VelocityLerp_TeamColor_cf59792a_Gold")},
			{TEXT("M_Spark_VelocityLerp_Pellets_Inst"), TEXT("M_Spark_VelocityLerp_Pellets_Inst_c4607b5d_Gold")},
			{TEXT("M_Explosion_RockChunks"), TEXT("M_Explosion_RockChunks_9e46e8fc_Gold")}};
		for (const auto& Entry : Names)
		{
			if (Original->GetFName() == FName(Entry.Key))
			{
				return LoadObject<UMaterialInterface>(nullptr, *FString::Printf(
					TEXT("/Game/TopDown/Characters/Sparrow/Previews/QVDesign20261027/Q7SourceGold/%s.%s"), Entry.Value, Entry.Value));
			}
		}
		UE_LOG(LogTemp, Error, TEXT("SPARROW_Q7 missing gold material mapping: %s"), *Original->GetPathName());
		return nullptr;
	}

	UParticleSystem* MakeMeteorTemplate(bool bContact)
	{
		static TWeakObjectPtr<UParticleSystem> CachedTrail, CachedContact;
		TWeakObjectPtr<UParticleSystem>& Cached = bContact ? CachedContact : CachedTrail;
		if (Cached.IsValid()) { return Cached.Get(); }
		const TCHAR* Path = bContact ?
			TEXT("/Game/ParagonGideon/FX/Particles/Gideon/Abilities/Primary/FX/P_Gideon_Primary_HitWorld.P_Gideon_Primary_HitWorld") :
			TEXT("/Game/ParagonGideon/FX/Particles/Gideon/Abilities/Primary/FX/P_Gideon_Primary_Projectile.P_Gideon_Primary_Projectile");
		UParticleSystem* Source = LoadObject<UParticleSystem>(nullptr, Path);
		if (!Source) { return nullptr; }
		UParticleSystem* Copy = DuplicateObject<UParticleSystem>(Source, GetTransientPackage(),
			MakeUniqueObjectName(GetTransientPackage(), UParticleSystem::StaticClass(), bContact ? TEXT("SparrowQ7Contact") : TEXT("SparrowQ7Trail")));
		Copy->SetFlags(RF_Transient);
		Copy->ClearFlags(RF_Public | RF_Standalone);
		int32 RemovedSplineEmitters = 0;
		if (!bContact)
		{
			// The source's one spline mesh forms a large detached triangle at Q's
			// slow final descent. Keep the ball and adjacent wisps; replace only
			// this mesh tail with the actual travelled-distance wake below.
			RemovedSplineEmitters = Copy->Emitters.RemoveAll([](UParticleEmitter* Emitter)
			{
				if (!Emitter) { return true; }
				for (UParticleLODLevel* LOD : Emitter->LODLevels)
				{
					const UParticleModuleTypeDataMesh* MeshType = LOD ? Cast<UParticleModuleTypeDataMesh>(LOD->TypeDataModule) : nullptr;
					if (MeshType && MeshType->Mesh && MeshType->Mesh->GetFName() == TEXT("SM_Spline_X_Aligned")) { return true; }
				}
				return false;
			});
		}
		// Preserve the source's coherent head/tail/smoke-spears. Broad lens cards,
		// dark ground sheets and rock chunks would undo the gold-light direction.
		if (bContact)
		{
			Copy->Emitters.RemoveAll([](UParticleEmitter* Emitter)
			{
				if (!Emitter) { return true; }
				for (UParticleLODLevel* LOD : Emitter->LODLevels)
				{
					const UMaterialInterface* Material = LOD && LOD->RequiredModule ? LOD->RequiredModule->Material.Get() : nullptr;
					if (!Material) { continue; }
					const FString Name = Material->GetName();
					if (Name.Contains(TEXT("Lensflare")) || Name.Contains(TEXT("DarkFlare")) ||
						Name.Contains(TEXT("Radial_Blur")) || Name.Contains(TEXT("RockChunks")) || Name.Contains(TEXT("Inky_Smoke"))) { return true; }
				}
				return false;
			});
		}
		int32 Mapped = 0, Lights = 0;
		for (UParticleEmitter* Emitter : Copy->Emitters)
		{
			if (!Emitter || !Emitter->IsIn(Copy)) { return nullptr; }
			for (UParticleLODLevel* LOD : Emitter->LODLevels)
			{
				if (!LOD || !LOD->RequiredModule || !LOD->IsIn(Copy)) { continue; }
				if (UMaterialInterface* Original = LOD->RequiredModule->Material)
				{
					UMaterialInterface* Gold = FindMeteorGold(Original);
					if (!Gold) { return nullptr; }
					LOD->RequiredModule->Material = Gold;
					++Mapped;
				}
				LOD->RequiredModule->bKillOnDeactivate = false;
				Lights += LOD->Modules.RemoveAll([](UParticleModule* Module)
				{
					return Module && Module->IsA<UParticleModuleLightBase>();
				});
				for (UParticleModule* Module : LOD->Modules)
				{
					if (UParticleModuleMeshMaterial* MeshMaterials = Cast<UParticleModuleMeshMaterial>(Module))
					{
						for (TObjectPtr<UMaterialInterface>& Material : MeshMaterials->MeshMaterials)
						{
							if (!Material) { continue; }
							UMaterialInterface* Gold = FindMeteorGold(Material);
							if (!Gold) { return nullptr; }
							Material = Gold;
							++Mapped;
						}
					}
				}
				if (UParticleModuleTypeDataMesh* MeshType = Cast<UParticleModuleTypeDataMesh>(LOD->TypeDataModule))
				{
					MeshType->bOverrideMaterial = true;
				}
			}
			// Rebuild cached renderer materials from the copied, recolored modules.
			Emitter->MeshMaterials.Reset();
			Emitter->UpdateModuleLists();
		}
		Copy->BuildEmitters();
		Cached = Copy;
		UE_LOG(LogTemp, Display, TEXT("SPARROW_Q7 template contact=%d emitters=%d mapped=%d removed_lights=%d removed_spline=%d source_unchanged=1"),
			bContact, Copy->Emitters.Num(), Mapped, Lights, RemovedSplineEmitters);
		return Copy;
	}

}

UParticleSystem* ASparrowAscendedShotFX::GetHarmonyContactTemplate()
{
    static TWeakObjectPtr<UParticleSystem> Cached;
    if (Cached.IsValid()) { return Cached.Get(); }
    UParticleSystem* Source = LoadObject<UParticleSystem>(nullptr,
        TEXT("/Game/ParagonGideon/FX/Particles/Gideon/Abilities/Primary/FX/P_Gideon_Primary_HitWorld.P_Gideon_Primary_HitWorld"));
    if (!Source) { return nullptr; }
    UParticleSystem* Copy = DuplicateObject<UParticleSystem>(Source, GetTransientPackage(),
        MakeUniqueObjectName(GetTransientPackage(), UParticleSystem::StaticClass(), TEXT("SparrowHarmonyContact")));
    Copy->SetFlags(RF_Transient); Copy->ClearFlags(RF_Public | RF_Standalone);
    Copy->Emitters.RemoveAll([](UParticleEmitter* Emitter)
    {
        if (!Emitter) { return true; }
        for (UParticleLODLevel* LOD : Emitter->LODLevels)
        {
            const auto* M = LOD && LOD->RequiredModule ? LOD->RequiredModule->Material.Get() : nullptr;
            if (M && (M->GetName().Contains(TEXT("RockChunks")) || M->GetName().Contains(TEXT("Inky_Smoke")))) { return true; }
        }
        return false;
    });
    for (UParticleEmitter* Emitter : Copy->Emitters)
    {
        for (UParticleLODLevel* LOD : Emitter->LODLevels)
        {
            if (!LOD || !LOD->RequiredModule) { continue; }
            if (auto* Gold = FindMeteorGold(LOD->RequiredModule->Material)) { LOD->RequiredModule->Material = Gold; }
            LOD->Modules.RemoveAll([](UParticleModule* M) { return M && M->IsA<UParticleModuleLightBase>(); });
            for (UParticleModule* Module : LOD->Modules)
            {
                if (auto* Mesh = Cast<UParticleModuleMeshMaterial>(Module))
                { for (auto& Material : Mesh->MeshMaterials) { if (auto* Gold = FindMeteorGold(Material)) { Material = Gold; } } }
            }
            if (auto* Mesh = Cast<UParticleModuleTypeDataMesh>(LOD->TypeDataModule)) { Mesh->bOverrideMaterial = true; }
        }
        Emitter->MeshMaterials.Reset(); Emitter->UpdateModuleLists();
    }
    Copy->BuildEmitters(); Cached = Copy; return Copy;
}

ASparrowAscendedShotFX::ASparrowAscendedShotFX()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickGroup = TG_PostPhysics;
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
	SetActorEnableCollision(false);
	SetCanBeDamaged(false);
	Tags.Append({TEXT("SparrowSkillFX"), TEXT("SparrowAscendedShotFX")});
}

bool ASparrowAscendedShotFX::InitializeOwner(ATopDownCombatCharacter* Character)
{
	if (!IsValid(Character) || Character != GetOwner() || !Character->GetMesh()) { return false; }
	const USparrowSkillComponent* Skills = Character->FindComponentByClass<USparrowSkillComponent>();
	if (!Skills || Skills->GetAscensionRemaining() <= 0.0f) { return false; }
	Caster = Character;
	return true;
}

bool ASparrowAscendedShotFX::CreateSurface(const TCHAR* Part, int32 Index)
{
	UStaticMesh* Plane = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
	const FString Path = FString::Printf(TEXT("/Game/TopDown/Characters/Sparrow/Materials/AscendedArsenal20261026/M_Ascended%s.M_Ascended%s"), Part, Part);
	UMaterialInterface* Source = LoadObject<UMaterialInterface>(nullptr, *Path);
	if (!Plane || !Source) { return false; }
	UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(Source, this);
	if (!Material) { return false; }
	Material->SetScalarParameterValue(TEXT("Index"), Index);
	Material->SetScalarParameterValue(TEXT("Skill"), SkillSlot);
	Material->SetScalarParameterValue(TEXT("PulseAge"), 100.0f);
	UStaticMeshComponent* Surface = NewObject<UStaticMeshComponent>(this, NAME_None, RF_Transient);
	Surface->SetMobility(EComponentMobility::Movable);
	Surface->SetupAttachment(RootComponent);
	Surface->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Surface->SetGenerateOverlapEvents(false);
	Surface->SetCanEverAffectNavigation(false);
	Surface->SetCastShadow(false);
	Surface->SetReceivesDecals(false);
	Surface->SetStaticMesh(Plane);
	Surface->SetMaterial(0, Material);
	Surface->SetVisibility(false);
	Surface->ComponentTags.Append({TEXT("SparrowAscendedSurface"), FName(Part)});
	AddInstanceComponent(Surface);
	Surface->RegisterComponent();
	Surfaces.Add(Surface);
	Materials.Add(Material);
	return true;
}

bool ASparrowAscendedShotFX::CreateDesignSurface(const TCHAR* MeshName, const TCHAR* Part, int32 Index)
{
	const bool bPlasmaContact = FCString::Strcmp(MeshName, TEXT("SM_RenSPlume")) == 0;
	const TCHAR* Folder = bPlasmaContact ? TEXT("/Game/TopDown/Characters/Sparrow/Materials/Renaissance20261027") :
		TEXT("/Game/TopDown/Characters/Sparrow/Previews/QVDesign20261027");
	UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *FString::Printf(TEXT("%s/%s.%s"), Folder, MeshName, MeshName));
	UMaterialInterface* Source = LoadObject<UMaterialInterface>(nullptr, *FString::Printf(TEXT("%s/M_%s.M_%s"), Folder, Part, Part));
	if (!Mesh || !Source) { return false; }
	UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(Source, this);
	Material->SetScalarParameterValue(TEXT("Index"), Index / (RainDesign == 6 ? (bRainAscended ? 6 : 4) : RainDesign >= 4 ? 5 : 4));
	Material->SetScalarParameterValue(TEXT("Style"), RainDesign);
	Material->SetScalarParameterValue(TEXT("Envelope"), 0.0f);
	Material->SetScalarParameterValue(TEXT("Ascended"), bRainAscended ? 1.0f : 0.0f);
	Material->SetScalarParameterValue(TEXT("Progress"), 1.0f);
	UStaticMeshComponent* Surface = NewObject<UStaticMeshComponent>(this, NAME_None, RF_Transient);
	Surface->SetMobility(EComponentMobility::Movable);
	Surface->SetupAttachment(RootComponent);
	Surface->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Surface->SetGenerateOverlapEvents(false);
	Surface->SetCanEverAffectNavigation(false);
	Surface->SetCastShadow(false);
	Surface->SetReceivesDecals(false);
	Surface->SetStaticMesh(Mesh);
	Surface->SetMaterial(0, Material);
	Surface->SetVisibility(false);
	Surface->ComponentTags.Append({TEXT("SparrowQDesignSurface"), FName(Part)});
	AddInstanceComponent(Surface);
	Surface->RegisterComponent();
	Surfaces.Add(Surface);
	Materials.Add(Material);
	return true;
}

bool ASparrowAscendedShotFX::InitializeBow(ATopDownCombatCharacter* Character, int32 Slot, const FVector& InOrigin,
	const FVector& Direction, float PrepareSeconds)
{
	if ((Slot != 0 && Slot != 1 && Slot != 3) || !InitializeOwner(Character) ||
		InOrigin.ContainsNaN() || Direction.ContainsNaN() || Direction.IsNearlyZero()) { return false; }
	SkillSlot = Slot;
	Mode = 0;
	Origin = InOrigin;
	Forward = Direction.GetSafeNormal();
	Preparation = FMath::Max(.08f, PrepareSeconds);
	// W의 앞쪽 여섯 깃 장식만 제외한다. 실제 날개와 두 출구 압력광은 별도 경로다.
	for (int32 Index = Slot == 1 ? 6 : 0; Index < 8; ++Index)
	{
		if (!CreateSurface(Index < 6 ? TEXT("BowFlow") : TEXT("BowPulse"), Index)) { return false; }
	}
	Tags.Add(TEXT("SparrowAscendedBow"));
	bReady = true;
	SetLifeSpan(2.0f);
	return true;
}

bool ASparrowAscendedShotFX::InitializeRain(ATopDownCombatCharacter* Character, const FVector& Ground, float Duration, float Radius, bool bDownward, bool bAscended)
{
	if (!IsValid(Character) || GetOwner() != Character || !Character->GetMesh() ||
		(bAscended && !InitializeOwner(Character)) || Ground.ContainsNaN() || Duration <= 0.0f || Radius <= 0.0f) { return false; }
	Caster = Character;
	Mode = 1;
	Origin = Ground;
	RainSeconds = Duration;
	RainRadius = Radius;
	bRainDownward = bDownward;
	bRainAscended = bAscended;
	RainDesign = FMath::Clamp(CVarQDesign.GetValueOnGameThread(), 0, 8);
	if (bAscended && ASparrowHarmonyFX::Enabled())
	{
		if (ASparrowHarmonyFX::Create(Character, TEXT("Q"), Ground, FVector::ForwardVector, .82f, this))
		{
			RainDesign = 9; bReady = true; Tags.Add(TEXT("SparrowAscendedRain"));
			SetLifeSpan(Duration + .12f); return true;
		}
	}
	if (!bAscended && RainDesign != 6) { return false; }
	if (RainDesign == 8)
	{
		if (!InitializePillarRain()) { return false; }
	}
	else if (RainDesign == 7)
	{
		if (!InitializeMeteorRain()) { return false; }
	}
	else if (RainDesign == 6)
	{
		Tags.Add(TEXT("SparrowQDesign6"));
		const TCHAR* AscendedMeshes[] = {TEXT("SM_QVContactSpray"), TEXT("SM_QVDawnCurtains"), TEXT("SM_QVStraightVolume"),
			TEXT("SM_RenSPlume"), TEXT("SM_RenSPlume"), TEXT("SM_RenSPlume")};
		const TCHAR* AscendedParts[] = {TEXT("DawnOverture"), TEXT("DawnCurtains"), TEXT("DawnCore"),
			TEXT("RenSPlasma"), TEXT("RenSPlasma"), TEXT("RenSPlasma")};
		const TCHAR* NormalMeshes[] = {TEXT("SM_QVDawnSpears"), TEXT("SM_RenSPlume"), TEXT("SM_RenSPlume"), TEXT("SM_RenSPlume")};
		const TCHAR* NormalParts[] = {TEXT("DawnSpears"), TEXT("RenSPlasma"), TEXT("RenSPlasma"), TEXT("RenSPlasma")};
		const int32 PartCount = bAscended ? 6 : 4;
		for (int32 Index = 0; Index < 8 * PartCount; ++Index)
		{
			if (!CreateDesignSurface(bAscended ? AscendedMeshes[Index % PartCount] : NormalMeshes[Index % PartCount],
				bAscended ? AscendedParts[Index % PartCount] : NormalParts[Index % PartCount], Index)) { return false; }
		}
	}
	else if (RainDesign >= 4)
	{
		Tags.Add(FName(*FString::Printf(TEXT("SparrowQDesign%d"), RainDesign)));
		const int32 ShaftCount = RainDesign == 4 ? 16 : 8;
		const TCHAR* Meshes[] = {TEXT("SM_QVCelestialDisc"), TEXT("SM_QVStraightVolume"),
			TEXT("SM_QVCelestialDisc"), TEXT("SM_QVContactBillow"), TEXT("SM_QVContactSpray")};
		const TCHAR* Parts[] = {TEXT("CelestialAperture"), TEXT("CelestialColumn"),
			TEXT("CelestialPool"), TEXT("CelestialPlume"), TEXT("CelestialScatter")};
		for (int32 Index = 0; Index < ShaftCount * 5; ++Index)
		{
			if (!CreateDesignSurface(Meshes[Index % 5], Parts[Index % 5], Index)) { return false; }
		}
	}
	else if (RainDesign > 0)
	{
		Tags.Add(FName(*FString::Printf(TEXT("SparrowQDesign%d"), RainDesign)));
		for (int32 Index = 0; Index < DesignRainShaftCount * 4; ++Index)
		{
			const int32 Part = Index % 4;
			const TCHAR* MeshName = Part < 2 ? (RainDesign == 3 ? TEXT("SM_QVPrism") : TEXT("SM_QVFluxFold")) :
				Part == 2 ? TEXT("SM_QVGroundFray") : (RainDesign == 3 ? TEXT("SM_QVShardCrown") : TEXT("SM_QVFlameCrown"));
			const TCHAR* Material = Part == 0 ? TEXT("QBeam") : Part == 1 ? TEXT("QVeil") : Part == 2 ? TEXT("Contact") : TEXT("Burst");
			if (!CreateDesignSurface(MeshName, Material, Index)) { return false; }
		}
	}
	else for (int32 Index = 0; Index < RainShaftCount * 3; ++Index)
	{
		const TCHAR* Part = Index < RainShaftCount ? TEXT("RainStreak") :
			Index < RainShaftCount * 2 ? TEXT("RainContact") : TEXT("RainFlare");
		if (!CreateSurface(Part, Index)) { return false; }
	}
	Tags.Add(TEXT("SparrowAscendedRain"));
	Tags.Add(bRainDownward ? TEXT("SparrowGoldenPillarsDown") : TEXT("SparrowGoldenPillarsUp"));
	bReady = true;
	SetLifeSpan(Duration + .12f);
	return true;
}

bool ASparrowAscendedShotFX::InitializeContact(ATopDownCombatCharacter* Character, int32 Slot,
	const FVector& Point, const FVector& Direction)
{
	if ((Slot != 1 && Slot != 3) || !InitializeOwner(Character) || Point.ContainsNaN() ||
		Direction.ContainsNaN() || Direction.IsNearlyZero()) { return false; }
	Mode = 2;
	SkillSlot = Slot;
	Origin = Point;
	Forward = Direction.GetSafeNormal();
	for (int32 Index = 0; Index < 2; ++Index) { if (!CreateSurface(TEXT("Contact"), Index)) { return false; } }
	Tags.Add(TEXT("SparrowAscendedContact"));
	bReady = true;
	SetLifeSpan(Slot == 1 ? .22f : .16f);
	return true;
}

void ASparrowAscendedShotFX::Pulse(const FVector& InOrigin, const FVector& Direction)
{
	if (!bReady || Mode != 0 || FadeAt >= 0.0f || InOrigin.ContainsNaN() || Direction.ContainsNaN() || Direction.IsNearlyZero()) { return; }
	Origin = InOrigin;
	Forward = Direction.GetSafeNormal();
	PulseAt = Age;
	++Pulses;
	SetLifeSpan(SkillSlot == 3 ? .45f : .32f);
}

void ASparrowAscendedShotFX::FinishCast()
{
	if (Mode != 0 || FadeAt >= 0.0f) { return; }
	if (Pulses == 0) { Destroy(); return; }
	FadeAt = Age;
	SetLifeSpan(.18f);
}

void ASparrowAscendedShotFX::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!bReady || !Caster.IsValid() || Caster->IsActorBeingDestroyed()) { Destroy(); return; }
	const USparrowSkillComponent* Skills = Caster->FindComponentByClass<USparrowSkillComponent>();
	// 이미 방출한 광역기는 시전 때 고정한 범위와 함께 끝까지 유지한다.
	if (!Skills || (Mode != 1 && Skills->GetAscensionRemaining() <= 0.0f)) { Destroy(); return; }
	Age += FMath::Max(DeltaSeconds, 0.0f);
	if (Mode == 1) { DrawRain(); }
	else if (Mode == 2) { DrawContact(); }
	else
	{
		if (FadeAt < 0.0f)
		{
			if (!Skills->IsCasting() || Skills->GetActiveSkillNumber() != SkillSlot + 1) { FinishCast(); }
		}
		if (!IsActorBeingDestroyed()) { DrawBow(); }
	}
}

void ASparrowAscendedShotFX::DrawBow()
{
	if (Pulses == 0)
	{
		USkeletalMeshComponent* Mesh = Caster->GetMesh();
		if (Mesh && Mesh->DoesSocketExist(TEXT("arrow_anchor"))) { Origin = Mesh->GetSocketLocation(TEXT("arrow_anchor")); }
		else if (Mesh && Mesh->DoesSocketExist(TEXT("BowEmitterSocket"))) { Origin = Mesh->GetSocketLocation(TEXT("BowEmitterSocket")); }
	}
	const FVector Axis = SkillSlot == 0 ? FVector::UpVector : Forward;
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Forward).GetSafeNormal();
	FVector CameraNormal = FVector::UpVector;
	if (APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(this, 0)) { CameraNormal = Camera->GetCameraLocation() - Origin; }
	const FQuat Facing = FRotationMatrix::MakeFromXZ(Axis, CameraNormal).ToQuat();
	const float Progress = FMath::Clamp(Age / Preparation, 0.0f, 1.0f);
	const float Since = Age - PulseAt;
	const float Kick = Pulses > 0 ? FMath::Exp(-Since * 18.0f) : 0.0f;
	const float Fade = FadeAt >= 0.0f ? 1.0f - FMath::SmoothStep(0.0f, .18f, Age - FadeAt) : 1.0f;
	for (int32 SurfaceIndex = 0; SurfaceIndex < Surfaces.Num(); ++SurfaceIndex)
	{
		const int32 Index = SurfaceIndex + (SkillSlot == 1 ? 6 : 0);
		FVector Position = Origin;
		FQuat Rotation = Facing;
		FVector Scale(1.0f);
		if (Index >= 6)
		{
			Position += Axis * (Index == 6 ? 18.0f : 38.0f);
			Rotation = Index == 6 ? Facing : FRotationMatrix::MakeFromXZ(Right, Axis).ToQuat();
			Scale = SkillSlot == 3 ? FVector(1.8f, 1.8f, 1.0f) : FVector(2.55f, 2.2f, 1.0f);
		}
		else if (SkillSlot == 0)
		{
			Position += Right * ((Index % 3 - 1) * 26.0f) + FVector::UpVector * (12.0f + (Index / 3) * 25.0f + Kick * 34.0f);
			Scale = FVector(1.65f, .58f, 1.0f);
		}
		else
		{
			const float Side = Index % 2 == 0 ? -1.0f : 1.0f;
			Position += Right * Side * (22.0f + (Index / 2) * 18.0f);
			Position += Forward * (12.0f + Kick * (28.0f + Index * 4.0f));
			Rotation = Facing * FQuat(FVector::UpVector, Side * (.22f + Index / 2 * .17f));
			Scale = FVector(1.02f, .42f, 1.0f);
		}
		Surfaces[SurfaceIndex]->SetWorldLocationAndRotation(Position, Rotation);
		Surfaces[SurfaceIndex]->SetWorldScale3D(Scale);
		Surfaces[SurfaceIndex]->SetVisibility(Age > .005f);
		Materials[SurfaceIndex]->SetScalarParameterValue(TEXT("Age"), Age);
		Materials[SurfaceIndex]->SetScalarParameterValue(TEXT("Progress"), Progress);
		Materials[SurfaceIndex]->SetScalarParameterValue(TEXT("PulseAge"), Since);
		Materials[SurfaceIndex]->SetScalarParameterValue(TEXT("Envelope"), Fade);
	}
}

bool ASparrowAscendedShotFX::InitializeMeteorRain()
{
	if (!bRainAscended || !GetWorld()) { return false; }
	MeteorTrailTemplate = MakeMeteorTemplate(false);
	MeteorContactTemplate = MakeMeteorTemplate(true);
	if (!MeteorTrailTemplate || !MeteorContactTemplate) { return false; }
	UStaticMesh* Plane = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
	UMaterialInterface* Spark = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Gideon/FX/M_NoxSpark.M_NoxSpark"));
	if (!Plane || !Spark) { return false; }
	// Gideon's AddGlowDot uses these same Color/Intensity parameters. The MID
	// belongs to this Q visual; its source material is never recolored or saved.
	MeteorWake = NewObject<UInstancedStaticMeshComponent>(this, NAME_None, RF_Transient);
	MeteorWake->SetupAttachment(RootComponent);
	MeteorWake->SetMobility(EComponentMobility::Movable);
	MeteorWake->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	MeteorWake->SetGenerateOverlapEvents(false);
	MeteorWake->SetCanEverAffectNavigation(false);
	MeteorWake->SetCastShadow(false);
	MeteorWake->SetReceivesDecals(false);
	MeteorWake->SetStaticMesh(Plane);
	UMaterialInstanceDynamic* WakeMaterial = UMaterialInstanceDynamic::Create(Spark, MeteorWake);
	WakeMaterial->SetVectorParameterValue(TEXT("Color"), FLinearColor(1.0f, .52f, .12f));
	WakeMaterial->SetScalarParameterValue(TEXT("Intensity"), 2.3f);
	MeteorWake->SetMaterial(0, WakeMaterial);
	MeteorWake->ComponentTags.Add(TEXT("SparrowQ7ConnectedWake"));
	AddInstanceComponent(MeteorWake);
	MeteorWake->RegisterComponent();
	WakeDots.Reserve(MaxMeteorWakeDots);
	WakeTransforms.Reserve(MaxMeteorWakeDots);
	Tags.Add(TEXT("SparrowQDesign7"));
	FVector ScreenLeft = -FVector::RightVector;
	if (APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(this, 0))
	{
		ScreenLeft = -FRotationMatrix(FRotator(0.0f, Camera->GetCameraRotation().Yaw, 0.0f)).GetUnitAxis(EAxis::Y);
	}
	MeteorVisuals.Reserve(32);
	RainParticles.Reserve(64);
	FCollisionQueryParams Query(SCENE_QUERY_STAT(SparrowQ7ContactFloor), false, Caster.Get());
	for (int32 Wave = 0; Wave < 8; ++Wave)
	{
		for (int32 Lane = 0; Lane < 4; ++Lane)
		{
			const int32 Seed = Wave * 4 + Lane;
			FMeteorVisual& Meteor = MeteorVisuals.AddDefaulted_GetRef();
			const float Angle = Seed * 2.399963f + .3f;
			const float Fraction = (static_cast<float>((Seed * 13) % 32) + .5f) / 32.0f;
			const float Radius = RainRadius * FMath::Sqrt(Fraction) * .88f;
			Meteor.Ground = Origin + FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.0f) * Radius;
			FHitResult Hit;
			if (GetWorld()->LineTraceSingleByObjectType(Hit, Meteor.Ground + FVector::UpVector * 250.0f,
				Meteor.Ground - FVector::UpVector * 500.0f, FCollisionObjectQueryParams(ECC_WorldStatic), Query) && Hit.ImpactNormal.Z > .5f)
			{
				Meteor.Ground = Hit.ImpactPoint;
			}
			Meteor.Ground.Z += 7.0f;
			Meteor.Fall = (ScreenLeft.RotateAngleAxis((Lane - 1.5f) * 7.0f, FVector::UpVector) * .28f - FVector::UpVector).GetSafeNormal();
			Meteor.Height = 760.0f + (Seed % 3) * 65.0f;
			Meteor.BornAt = Wave * RainContactInterval;
			Meteor.Scale = 1.75f + (Seed % 3) * .16f;
		}
	}
	UE_LOG(LogTemp, Display, TEXT("SPARROW_Q7 initialized meteors=%d waves=8 first_contact=%.3f interval=%.3f radius=%.1f wake_spacing=12 wake_life=.18 wake_cap=512 gameplay_visual_only=1"),
		MeteorVisuals.Num(), RainContactDelay, RainContactInterval, RainRadius);
	return true;
}

UParticleSystemComponent* ASparrowAscendedShotFX::SpawnRainParticle(UParticleSystem* Template, const FVector& Position,
	const FRotator& Rotation, float Scale)
{
	if (!Template || !GetWorld()) { return nullptr; }
	UParticleSystemComponent* Particle = NewObject<UParticleSystemComponent>(this, NAME_None, RF_Transient);
	Particle->SetAutoActivate(false);
	Particle->bAutoDestroy = false;
	Particle->SetupAttachment(RootComponent);
	Particle->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Particle->SetGenerateOverlapEvents(false);
	Particle->SetCanEverAffectNavigation(false);
	Particle->SetTemplate(Template);
	Particle->SetWorldLocationAndRotation(Position, Rotation);
	Particle->SetWorldScale3D(FVector(Scale));
	Particle->ComponentTags.Add(TEXT("SparrowQ7SourceParticle"));
	AddInstanceComponent(Particle);
	Particle->RegisterComponent();
	Particle->ActivateSystem(true);
	RainParticles.Add(Particle);
	return Particle;
}

void ASparrowAscendedShotFX::DrawMeteorRain()
{
	WakeDots.RemoveAllSwap([this](const FWakeDot& Dot) { return Age - Dot.BornAt >= MeteorWakeLife; }, EAllowShrinking::No);
	for (FMeteorVisual& Meteor : MeteorVisuals)
	{
		const float LocalAge = Age - Meteor.BornAt;
		if (LocalAge < 0.0f) { continue; }
		const float ContactAge = LocalAge - RainContactDelay;
		// The large luminous body approaches first, then presses the final 120 cm
		// slowly into its contact burst. Four contacts share each real Q damage pulse.
		const float Approach = FMath::SmoothStep(0.0f, .49f, LocalAge);
		const float Press = FMath::SmoothStep(.49f, RainContactDelay, LocalAge);
		const float Height = (Meteor.Height - 120.0f) * (1.0f - Approach) + 120.0f * (1.0f - Press);
		const FVector Position = Meteor.Ground - Meteor.Fall * (Height / FMath::Max(.1f, -Meteor.Fall.Z));
		if (!Meteor.bSpawned)
		{
			Meteor.bSpawned = true;
			Meteor.Trail = SpawnRainParticle(MeteorTrailTemplate, Position, Meteor.Fall.Rotation(), Meteor.Scale);
			Meteor.LastWakePoint = Position;
		}
		if (Meteor.Trail.IsValid() && !Meteor.bContact)
		{
			const FVector Travel = Position - Meteor.LastWakePoint;
			const float Distance = Travel.Size();
			const int32 Steps = FMath::Min(FMath::FloorToInt(Distance / MeteorWakeSpacing), 12);
			const FVector Along = Travel.GetSafeNormal();
			for (int32 Step = 1; Step <= Steps && WakeDots.Num() < MaxMeteorWakeDots; ++Step)
			{
				FWakeDot& Dot = WakeDots.AddDefaulted_GetRef();
				Dot.Position = Meteor.LastWakePoint + Along * (Step * MeteorWakeSpacing);
				Dot.BornAt = Age;
				Dot.Size = (30.0f + (Step % 3) * 4.0f) * Meteor.Scale / 1.8f;
			}
			if (Steps >= 12 || WakeDots.Num() >= MaxMeteorWakeDots) { Meteor.LastWakePoint = Position; }
			else { Meteor.LastWakePoint += Along * (Steps * MeteorWakeSpacing); }
			Meteor.Trail->SetWorldLocation(Position);
			Meteor.Trail->SetWorldScale3D(FVector(Meteor.Scale * (1.0f + Press * .12f)));
		}
		if (ContactAge >= 0.0f && !Meteor.bContact)
		{
			Meteor.bContact = true;
			if (Meteor.Trail.IsValid()) { Meteor.Trail->DeactivateSystem(); }
			Meteor.Contact = SpawnRainParticle(MeteorContactTemplate, Meteor.Ground, FRotator::ZeroRotator,
				1.80f + (Meteor.Scale - 1.75f));
			if (Meteor.Contact.IsValid()) { Meteor.Contact->CustomTimeDilation = 1.35f; }
		}
		if (ContactAge > .23f && Meteor.Trail.IsValid())
		{
			Meteor.Trail->DestroyComponent();
			Meteor.Trail.Reset();
		}
		if (ContactAge > .68f && Meteor.Contact.IsValid())
		{
			Meteor.Contact->DeactivateSystem();
			Meteor.Contact->DestroyComponent();
			Meteor.Contact.Reset();
		}
	}
	if (MeteorWake)
	{
		FVector ViewDirection(-1.0f, -1.0f, 1.0f);
		if (APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(this, 0))
		{
			ViewDirection = -Camera->GetCameraRotation().Vector();
		}
		const FQuat Facing = FRotationMatrix::MakeFromZ(ViewDirection).ToQuat();
		WakeTransforms.Reset();
		for (const FWakeDot& Dot : WakeDots)
		{
			const float Shrink = 1.0f - FMath::Clamp((Age - Dot.BornAt) / MeteorWakeLife, 0.0f, 1.0f);
			const float Size = Dot.Size * Shrink / 100.0f;
			WakeTransforms.Emplace(Facing, Dot.Position, FVector(Size, Size, 1.0f));
		}
		MeteorWake->ClearInstances();
		MeteorWake->AddInstances(WakeTransforms, false, true);
	}
}

void ASparrowAscendedShotFX::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	for (UParticleSystemComponent* Particle : RainParticles)
	{
		if (IsValid(Particle)) { Particle->DeactivateSystem(); Particle->DestroyComponent(); }
	}
	RainParticles.Reset();
	MeteorVisuals.Reset();
	WakeDots.Reset();
	WakeTransforms.Reset();
	if (MeteorWake) { MeteorWake->ClearInstances(); }
	Super::EndPlay(EndPlayReason);
}

bool ASparrowAscendedShotFX::InitializePillarRain()
{
	constexpr int32 PillarCount = 40;
	constexpr int32 PoolCount = 20;
	constexpr int32 PartCount = 6;
	const TCHAR* Meshes[] = {TEXT("SM_QVLightRibbon"), TEXT("SM_QVLightRibbon"), TEXT("SM_QVLightRibbon"),
		TEXT("SM_QVContactBillow"), TEXT("SM_QVCelestialDisc"), TEXT("SM_QVContactSpray")};
	const TCHAR* Parts[] = {TEXT("PlumeCore"), TEXT("PlumeVeil"), TEXT("PlumeTip"),
		TEXT("PlumeBurst"), TEXT("PlumeContact"), TEXT("PlumeSparks")};
	for (int32 Index = 0; Index < PoolCount * PartCount; ++Index)
	{
		if (!CreateDesignSurface(Meshes[Index % PartCount], Parts[Index % PartCount], Index)) { return false; }
	}
	PillarGrounds.Reserve(PillarCount);
	FCollisionQueryParams Query(SCENE_QUERY_STAT(SparrowQ8Floor), false, Caster.Get());
	for (int32 Seed = 0; Seed < PillarCount; ++Seed)
	{
		const float Angle = Seed * 2.399963f;
		const float Radius = RainRadius * FMath::Sqrt(((Seed * 17) % PillarCount + .5f) / PillarCount) * .91f;
		FVector Ground = Origin + FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.0f) * Radius;
		FHitResult Hit;
		if (GetWorld()->LineTraceSingleByObjectType(Hit, Ground + FVector::UpVector * 100.0f,
			Ground - FVector::UpVector * 180.0f, FCollisionObjectQueryParams(ECC_WorldStatic), Query) && Hit.ImpactNormal.Z > .5f)
		{
			Ground = Hit.ImpactPoint;
		}
		PillarGrounds.Add(Ground + FVector::UpVector * .8f);
	}
	Tags.Add(TEXT("SparrowQDesign8"));
	UE_LOG(LogTemp, Display, TEXT("SPARROW_Q8 pillars=40 waves=8 pool=20 surfaces=120 contact=%.3f interval=%.3f radius=%.1f normal_unchanged=1"),
		RainContactDelay, RainContactInterval, RainRadius);
	return true;
}

void ASparrowAscendedShotFX::DrawPillarRain()
{
	// 1.42 s visual life fits inside four .37 s waves: no component allocation in Tick.
	constexpr float Life = 1.42f;
	for (UStaticMeshComponent* Surface : Surfaces) { Surface->SetVisibility(false); }
	APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(this, 0);
	for (int32 Seed = 0; Seed < PillarGrounds.Num(); ++Seed)
	{
		const float LocalAge = Age - (Seed / 5) * RainContactInterval;
		if (LocalAge < 0.0f || LocalAge >= Life) { continue; }
		const float ContactAge = LocalAge - RainContactDelay;
		const FVector Ground = PillarGrounds[Seed];
		const FVector View = Camera ? Camera->GetCameraLocation() - Ground : FVector(1.0f, 0.0f, 1.0f);
		const FQuat Facing = FRotationMatrix::MakeFromXZ(FVector::UpVector, View).ToQuat();
		const float Height = 800.0f + Seed % 4 * 45.0f;
		const float Tip = Height * (1.0f - FMath::SmoothStep(0.0f, RainContactDelay, LocalAge));
		const float ScaleSeed = .88f + Seed % 4 * .08f;
		const float Beam = FMath::SmoothStep(0.0f, .055f, LocalAge) * (1.0f - FMath::SmoothStep(.17f, .54f, ContactAge));
		const int32 First = (Seed % 20) * 6;
		for (int32 Part = 0; Part < 6; ++Part)
		{
			const int32 Index = First + Part;
			FVector Position = Ground;
			FQuat Rotation = Facing;
			FVector Scale = FVector::OneVector;
			float Strength = 0.0f;
			if (Part < 2)
			{
				Position.Z += Tip;
				Scale = FVector(FMath::Max(Height - Tip, 1.0f) / 100.0f,
					(Part == 0 ? .24f : .90f) * ScaleSeed * (1.0f + FMath::SmoothStep(0.0f, .10f, ContactAge) * .12f), 1.0f);
				Strength = Beam * (Part == 0 ? .84f : 1.55f);
			}
			else if (Part == 2)
			{
				Position.Z += Tip;
				Scale = FVector(.75f, .64f, 1.0f) * ScaleSeed;
				Strength = FMath::SmoothStep(.12f, .22f, LocalAge) * (1.0f - FMath::SmoothStep(.035f, .16f, ContactAge));
			}
			else if (Part == 3)
			{
				Position.Z += 2.0f;
				Rotation = FRotator(0.0f, Seed * 67.0f, 0.0f).Quaternion();
				const float Spread = FMath::SmoothStep(0.0f, .15f, ContactAge);
				Scale = FVector(.42f + Spread * .51f, .42f + Spread * .51f,
					.16f + FMath::Sin(FMath::Clamp(ContactAge / .46f, 0.0f, 1.0f) * PI) * 1.05f) * ScaleSeed;
				Strength = FMath::SmoothStep(0.0f, .025f, ContactAge) * (1.0f - FMath::SmoothStep(.22f, .48f, ContactAge)) * 1.10f;
			}
			else if (Part == 4)
			{
				Rotation = FQuat::Identity;
				const float Width = (.65f + FMath::SmoothStep(0.0f, .14f, ContactAge) * .65f) * ScaleSeed;
				Scale = FVector(Width, Width, 1.0f);
				Strength = FMath::SmoothStep(0.0f, .018f, ContactAge) * (1.0f - FMath::SmoothStep(.22f, .59f, ContactAge));
			}
			else
			{
				Rotation = FRotator(0.0f, Seed * 47.0f, 0.0f).Quaternion();
				Scale = FVector(.35f + FMath::Max(0.0f, ContactAge) * 1.55f) * ScaleSeed;
				Strength = FMath::SmoothStep(0.0f, .014f, ContactAge) * (1.0f - FMath::SmoothStep(.18f, .40f, ContactAge));
			}
			Surfaces[Index]->SetWorldLocationAndRotation(Position, Rotation);
			Surfaces[Index]->SetWorldScale3D(Scale);
			Surfaces[Index]->SetVisibility(Strength > .001f);
			Materials[Index]->SetScalarParameterValue(TEXT("Age"), LocalAge);
			Materials[Index]->SetScalarParameterValue(TEXT("ContactAge"), ContactAge);
			Materials[Index]->SetScalarParameterValue(TEXT("Index"), Seed);
			Materials[Index]->SetScalarParameterValue(TEXT("Envelope"), Strength);
		}
	}
}

void ASparrowAscendedShotFX::DrawRain()
{
	if (RainDesign > 0) { DrawDesignRain(); return; }
	FVector CameraNormal = FVector::ForwardVector;
	if (APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(this, 0)) { CameraNormal = Camera->GetCameraLocation() - Origin; }
	const FVector Axis = bRainDownward ? -FVector::UpVector : FVector::UpVector;
	const FQuat Vertical = FRotationMatrix::MakeFromXZ(Axis, CameraNormal).ToQuat();
	const float Fade = FMath::SmoothStep(0.0f, .10f, Age) * (1.0f - FMath::SmoothStep(RainSeconds - .20f, RainSeconds, Age));
	for (int32 Index = 0; Index < Surfaces.Num(); ++Index)
	{
		const int32 Seed = Index % RainShaftCount;
		// 직전의 가는 24광체와 세 층의 질감을 복원하되, 세 줄기씩 여덟 피해 펄스에 맞춘다.
		const float LocalAge = Age - (Seed / 3) * RainContactInterval;
		// 이전 재질의 .92초 접촉 위상을 현재 공용 피해 시각에 맞춘다. 접촉 뒤 감쇠 길이는 그대로다.
		const float VisualAge = LocalAge < RainContactDelay ? LocalAge * (.92f / RainContactDelay) : .92f + LocalAge - RainContactDelay;
		const float Angle = Seed * 2.399963f;
		const float Radius = RainRadius * FMath::Sqrt((Seed + .5f) / RainShaftCount) * .94f;
		FVector Location = Origin + FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.0f) * Radius;
		const bool bStreak = Index < RainShaftCount;
		const bool bFlare = Index >= RainShaftCount * 2;
		const float Height = 780.0f + (Seed % 3) * 75.0f;
		const float Travel = FMath::SmoothStep(0.0f, .92f, VisualAge);
		const float Length = FMath::Lerp(360.0f, Height, Travel);
		const float TipHeight = Height * (1.0f - Travel);
		Location.Z += bStreak ? (bRainDownward ? TipHeight + Length * .5f : Length * .5f) : bFlare ? 130.0f : 7.0f;
		const FQuat Rotation = bStreak ? Vertical : bFlare ?
			FRotationMatrix::MakeFromXZ(FVector::UpVector, CameraNormal).ToQuat() : FQuat::Identity;
		Surfaces[Index]->SetWorldLocationAndRotation(Location, Rotation);
		Surfaces[Index]->SetWorldScale3D(bStreak ? FVector(Length / 100.0f, 1.10f + (Seed % 3) * .12f, 1.0f) :
			bFlare ? FVector(3.20f, 4.20f, 1.0f) : FVector(5.20f, 5.20f, 1.0f));
		Surfaces[Index]->SetVisibility(LocalAge >= 0.0f && (bStreak ? VisualAge < 1.45f : VisualAge >= .92f && VisualAge < 1.48f));
		Materials[Index]->SetScalarParameterValue(TEXT("Age"), Age);
		Materials[Index]->SetScalarParameterValue(TEXT("Progress"), VisualAge);
		Materials[Index]->SetScalarParameterValue(TEXT("Envelope"), Fade);
	}
}

void ASparrowAscendedShotFX::DrawDesignRain()
{
	if (RainDesign == 9) { return; }
	if (RainDesign == 8) { DrawPillarRain(); return; }
	if (RainDesign == 7) { DrawMeteorRain(); return; }
	if (RainDesign == 6) { DrawRenaissanceRain(); return; }
	if (RainDesign >= 4) { DrawCelestialRain(); return; }
	const float EndFade = 1.0f - FMath::SmoothStep(RainSeconds - .20f, RainSeconds, Age);
	for (int32 Index = 0; Index < Surfaces.Num(); ++Index)
	{
		const int32 Seed = Index / 4;
		const int32 Part = Index % 4;
		// 두 낙하점씩 여덟 실제 피해 펄스와 맞춘다. 후보는 피해를 추가하지 않는다.
		const float LocalAge = Age - (Seed / 2) * RainContactInterval;
		const float ContactAge = LocalAge - RainContactDelay;
		const float Angle = Seed * 2.399963f;
		const float Radius = RainRadius * FMath::Sqrt((Seed + .5f) / DesignRainShaftCount) * .91f;
		const FVector Ground = Origin + FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.0f) * Radius;
		const float Height = 760.0f + (Seed % 3) * 65.0f;
		const float Descent = FMath::SmoothStep(0.0f, RainContactDelay, LocalAge);
		const float TipHeight = Height * (1.0f - Descent);
		FVector Position = Ground + FVector::UpVector * 5.0f;
		FVector Scale = FVector::OneVector;
		FQuat Rotation = FRotator(0.0f, Seed * 137.5f, 0.0f).Quaternion();
		float Envelope = 0.0f;
		if (Part < 2)
		{
			FVector CameraNormal = FVector::ForwardVector;
			if (APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(this, 0)) { CameraNormal = Camera->GetCameraLocation() - Ground; }
			Rotation = FRotationMatrix::MakeFromXZ(FVector::UpVector, CameraNormal).ToQuat();
			if (Part == 1) { Rotation *= FQuat(FVector::ForwardVector, RainDesign == 2 ? 1.3f : 1.05f); }
			const float Width = RainDesign == 1 ? (Part == 0 ? 54.0f : 31.0f) : RainDesign == 2 ?
				(Part == 0 ? 126.0f : 79.0f) : (Part == 0 ? 80.0f : 7.0f);
			Position += FVector::UpVector * TipHeight;
			const float Pressure = FMath::SmoothStep(-.12f, .03f, ContactAge);
			Scale = FVector(Height / 100.0f, Width / 100.0f, Width / 100.0f);
			Envelope = FMath::SmoothStep(0.0f, .10f, LocalAge) *
				(1.0f - FMath::SmoothStep(RainDesign == 2 ? .18f : .10f, .35f, ContactAge));
			if (RainDesign == 2)
			{
				// 접촉부의 폭을 접어 넓혀 상부의 투명한 낙하 흐름과 구분한다.
				Scale.Y *= 1.0f + Pressure * .30f;
				Scale.Z *= 1.0f + Pressure * .30f;
			}
			else if (RainDesign == 3 && Part == 0)
			{
				const float Peel = FMath::SmoothStep(.0f, .24f, ContactAge);
				Scale.Y *= 1.0f + Peel * .75f;
				Scale.Z *= 1.0f + Peel * .75f;
				Envelope *= 1.0f - Peel;
			}
			if (Part == 1) { Envelope *= RainDesign == 3 ? .42f : .60f; }
		}
		else if (Part == 2)
		{
			const float Expand = 1.0f + FMath::SmoothStep(.0f, .20f, ContactAge) * .32f;
			Scale = FVector((RainDesign == 2 ? 1.05f : .90f) * Expand);
			Scale.Z = .65f;
			Envelope = FMath::SmoothStep(-.015f, .008f, ContactAge) * (1.0f - FMath::SmoothStep(.12f, .44f, ContactAge));
		}
		else
		{
			const float Expand = FMath::SmoothStep(.0f, .16f, ContactAge);
			Position.Z += FMath::Max(0.0f, ContactAge) * (RainDesign == 3 ? 70.0f : 20.0f);
			Scale = FVector(.18f + Expand * (RainDesign == 3 ? .75f : .85f));
			Scale.Z *= RainDesign == 2 ? .48f : .80f;
			Envelope = FMath::SmoothStep(.0f, .016f, ContactAge) * (1.0f - FMath::SmoothStep(.075f, .29f, ContactAge));
		}
		Envelope *= EndFade;
		Surfaces[Index]->SetWorldLocationAndRotation(Position, Rotation);
		Surfaces[Index]->SetWorldScale3D(Scale);
		Surfaces[Index]->SetVisibility(LocalAge >= 0.0f && Envelope > .002f);
		Materials[Index]->SetScalarParameterValue(TEXT("Age"), FMath::Max(0.0f, LocalAge));
		Materials[Index]->SetScalarParameterValue(TEXT("ContactAge"), ContactAge);
		Materials[Index]->SetScalarParameterValue(TEXT("Envelope"), Envelope);
	}
}

void ASparrowAscendedShotFX::DrawCelestialRain()
{
	const bool bApertures = RainDesign == 4;
	const int32 ShaftCount = bApertures ? 16 : 8;
	const float EndFade = 1.0f - FMath::SmoothStep(RainSeconds - .12f, RainSeconds, Age);
	for (int32 Index = 0; Index < Surfaces.Num(); ++Index)
	{
		const int32 Seed = Index / 5;
		const int32 Part = Index % 5;
		const int32 PulseIndex = bApertures ? Seed / 2 : Seed;
		const float LocalAge = Age - PulseIndex * RainContactInterval;
		const float ContactAge = LocalAge - RainContactDelay;
		const float Angle = Seed * 2.399963f;
		const float Radius = RainRadius * FMath::Sqrt((Seed + .5f) / ShaftCount) * .83f;
		const FVector Ground = Origin + FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.0f) * Radius;
		const float Height = (bApertures ? 440.0f : 560.0f) + (Seed % 3) * 32.0f;
		// 개구부는 공중에 고정하고 그 아래 광주만 길어진다. 접점은 기존 피해 펄스와 같다.
		const float Descent = FMath::SmoothStep(.16f, RainContactDelay, LocalAge);
		const float Tip = Height * (1.0f - Descent);
		FVector Position = Ground + FVector::UpVector * 5.0f;
		FVector Scale = FVector::OneVector;
		FQuat Rotation = FRotator(0.0f, Seed * 137.5f, 0.0f).Quaternion();
		float Envelope = 0.0f;
		if (Part == 0)
		{
			Position.Z += Height;
			const float Open = FMath::SmoothStep(0.0f, .15f, LocalAge);
			const float Size = (bApertures ? 1.48f : 1.12f) * (.62f + Open * .38f);
			Scale = FVector(Size, Size, 1.0f);
			Envelope = Open * (1.0f - FMath::SmoothStep(.15f, .42f, ContactAge)) * (bApertures ? .90f : .46f);
		}
		else if (Part == 1)
		{
			const float Length = FMath::Max(1.0f, Height - Tip);
			Position.Z += Tip;
			Rotation = FRotationMatrix::MakeFromXZ(FVector::UpVector, FVector::ForwardVector).ToQuat();
			const float Width = bApertures ? 178.0f : 292.0f;
			Scale = FVector(Length / 100.0f, Width / 100.0f, Width / 100.0f);
			Envelope = FMath::SmoothStep(.15f, .23f, LocalAge) * (1.0f - FMath::SmoothStep(.20f, .53f, ContactAge));
		}
		else if (Part == 2)
		{
			const float Expansion = FMath::SmoothStep(0.0f, .22f, ContactAge);
			const float Size = (bApertures ? 1.38f : 1.90f) + Expansion * (bApertures ? .72f : .88f);
			Scale = FVector(Size, Size, 1.0f);
			Envelope = FMath::SmoothStep(-.008f, .015f, ContactAge) * (1.0f - FMath::SmoothStep(.24f, .62f, ContactAge));
		}
		else if (Part == 3)
		{
			const float Expansion = FMath::SmoothStep(0.0f, .16f, ContactAge);
			const float Size = (bApertures ? 1.0f : 1.34f) * (.48f + Expansion * .70f);
			Scale = FVector(Size, Size, .60f + Expansion * .60f);
			Envelope = FMath::SmoothStep(0.0f, .025f, ContactAge) * (1.0f - FMath::SmoothStep(.13f, .43f, ContactAge));
		}
		else
		{
			const float Travel = FMath::Clamp(ContactAge / .55f, 0.0f, 1.0f);
			Scale = FVector(.48f + Travel * 1.70f, .48f + Travel * 1.70f, .20f + Travel * 1.35f);
			Envelope = FMath::SmoothStep(0.0f, .018f, ContactAge) * (1.0f - FMath::SmoothStep(.18f, .56f, ContactAge));
		}
		Envelope *= EndFade;
		Surfaces[Index]->SetWorldLocationAndRotation(Position, Rotation);
		Surfaces[Index]->SetWorldScale3D(Scale);
		Surfaces[Index]->SetVisibility(LocalAge >= 0.0f && Envelope > .002f);
		Materials[Index]->SetScalarParameterValue(TEXT("Age"), FMath::Max(0.0f, LocalAge));
		Materials[Index]->SetScalarParameterValue(TEXT("ContactAge"), ContactAge);
		Materials[Index]->SetScalarParameterValue(TEXT("Envelope"), Envelope);
	}
}

void ASparrowAscendedShotFX::DrawRenaissanceRain()
{
	const int32 PartCount = bRainAscended ? 6 : 4;
	const float Interval = bRainAscended ? RainContactInterval : .50f;
	const float ContactDelay = bRainAscended ? RainContactDelay : 0.0f;
	const float EndFade = 1.0f - FMath::SmoothStep(RainSeconds - .16f, RainSeconds, Age);
	for (int32 Index = 0; Index < Surfaces.Num(); ++Index)
	{
		const int32 Seed = Index / PartCount;
		const int32 Part = Index % PartCount;
		const float ContactAge = Age - Seed * Interval - ContactDelay;
		const float LocalAge = ContactAge + RainContactDelay;
		const float Angle = Seed * 2.399963f + .30f;
		const float Radius = RainRadius * FMath::Sqrt((Seed + .5f) / 8.0f) * .79f;
		const FVector Ground = Origin + FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.0f) * Radius;
		const float Height = bRainAscended ? 590.0f + (Seed % 3) * 27.0f : 460.0f;
		FVector Position = Ground + FVector::UpVector * 4.0f;
		FVector Scale = FVector::OneVector;
		FQuat Rotation = FRotator(0.0f, Seed * 137.5f, 0.0f).Quaternion();
		float Envelope = 0.0f;
		if (bRainAscended && Part == 0)
		{
			// The source is a contracting constellation, not a repeated horizontal ring.
			Position.Z += Height;
			const float Gather = FMath::SmoothStep(.02f, .24f, LocalAge);
			Scale = FVector(1.1f - Gather * .62f, 1.1f - Gather * .62f, .08f);
			Envelope = FMath::SmoothStep(0.0f, .07f, LocalAge) * (1.0f - FMath::SmoothStep(.30f, .62f, LocalAge)) * .55f;
		}
		else if (bRainAscended && (Part == 1 || Part == 2))
		{
			// A long approach visibly slows over the last 140 cm and presses into the ground.
			const float Approach = FMath::SmoothStep(.14f, .49f, LocalAge);
			const float Press = FMath::SmoothStep(.49f, RainContactDelay, LocalAge);
			const float Tip = (Height - 140.0f) * (1.0f - Approach) + 140.0f * (1.0f - Press);
			Position.Z += Tip;
			Rotation = FRotationMatrix::MakeFromXZ(FVector::UpVector, FVector::ForwardVector).ToQuat();
			Rotation *= FQuat(FVector::ForwardVector, Seed * .79f);
			const float Width = Part == 1 ? 1.28f + Press * .22f : .10f;
			Scale = FVector(FMath::Max(1.0f, Height - Tip) / 100.0f, Width, Width);
			Envelope = FMath::SmoothStep(.14f, .22f, LocalAge) * (1.0f - FMath::SmoothStep(.12f, .48f, ContactAge));
			if (Part == 2) { Envelope *= .74f; }
		}
		else if (!bRainAscended && Part == 0)
		{
			// Four small, aligned spears replace the old diffuse rain system. The first
			// contact is immediate, matching the existing normal-Q damage schedule.
			const float Fall = FMath::SmoothStep(-.65f, 0.0f, ContactAge);
			Position.Z += Height * (1.0f - Fall);
			Rotation = FRotationMatrix::MakeFromXZ(FVector::UpVector, FVector::ForwardVector).ToQuat();
			Rotation *= FQuat(FVector::ForwardVector, Seed * .59f);
			// Keep a preceding volley in view while the next falls. The four authored
			// heads need enough separation to remain distinct at the gameplay camera.
			Scale = FVector(2.25f, 1.45f, 1.45f);
			Envelope = FMath::SmoothStep(-.68f, -.56f, ContactAge) * (1.0f - FMath::SmoothStep(.08f, .30f, ContactAge));
		}
		else
		{
			// Three curved source-plasma sheets replace the planar pool, metallic
			// spokes and additive particle overlay. Contact has finite rising volume.
			const int32 Lobe = Part - (bRainAscended ? 3 : 1);
			const float LocalContact = ContactAge - Lobe * .014f;
			const float Inflate = FMath::SmoothStep(.015f, .14f, LocalContact);
			const float Release = FMath::SmoothStep(.14f, .40f, LocalContact);
			const float FormScale = bRainAscended ? 1.08f : .68f;
			const float Yaw = Seed * 137.5f + Lobe * 120.0f;
			Rotation = FRotator(2.0f + Inflate * (24.0f + Lobe * 3.0f), Yaw, (Lobe - 1) * 9.0f).Quaternion();
			Position.Z += 7.0f + Inflate * 18.0f;
			Scale = FVector((.25f + Inflate * .70f + Release * .18f) * FormScale,
				(.42f + Inflate * .51f + Release * .16f) * FormScale,
				(.18f + Inflate * 1.10f + Release * .24f) * FormScale);
			Envelope = FMath::SmoothStep(0.0f, .025f, LocalContact) *
				(1.0f - FMath::SmoothStep(.24f, .46f, LocalContact)) * (bRainAscended ? .90f : .82f);
			Materials[Index]->SetScalarParameterValue(TEXT("Index"), Lobe + (Seed % 3) * .35f);
			Materials[Index]->SetScalarParameterValue(TEXT("PulseAge"), FMath::Max(0.0f, LocalContact));
		}
		Envelope *= EndFade;
		Surfaces[Index]->SetWorldLocationAndRotation(Position, Rotation);
		Surfaces[Index]->SetWorldScale3D(Scale);
		Surfaces[Index]->SetVisibility(Envelope > .002f);
		Materials[Index]->SetScalarParameterValue(TEXT("Age"), FMath::Max(0.0f, LocalAge));
		Materials[Index]->SetScalarParameterValue(TEXT("ContactAge"), ContactAge);
		Materials[Index]->SetScalarParameterValue(TEXT("Envelope"), Envelope);
	}
}

void ASparrowAscendedShotFX::DrawContact()
{
	FVector CameraNormal = FVector::UpVector;
	if (APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(this, 0)) { CameraNormal = Camera->GetCameraLocation() - Origin; }
	const FQuat Facing = FRotationMatrix::MakeFromXZ(Forward, CameraNormal).ToQuat();
	// 호출부의 R 축소 배율을 최종 월드 크기에 한 번만 반영한다.
	const float Size = (SkillSlot == 1 ? 1.8f : 1.05f) * GetActorScale3D().X;
	for (int32 Index = 0; Index < Surfaces.Num(); ++Index)
	{
		Surfaces[Index]->SetWorldLocationAndRotation(Origin, Facing * FQuat(FVector::ForwardVector, Index * PI * .5f));
		Surfaces[Index]->SetWorldScale3D(FVector(Size, Size, 1.0f));
		Surfaces[Index]->SetVisibility(true);
		Materials[Index]->SetScalarParameterValue(TEXT("Age"), Age);
		Materials[Index]->SetScalarParameterValue(TEXT("Envelope"), 1.0f);
	}
}
