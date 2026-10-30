#include "SparrowArsenalStudyFX.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Distributions/DistributionFloatConstant.h"
#include "Distributions/DistributionFloatUniform.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "Particles/ParticleEmitter.h"
#include "Particles/ParticleLODLevel.h"
#include "Particles/ParticleModuleRequired.h"
#include "Particles/Spawn/ParticleModuleSpawn.h"
#include "Particles/Lifetime/ParticleModuleLifetime.h"
#include "Particles/Light/ParticleModuleLight.h"
#include "Particles/Color/ParticleModuleColor.h"
#include "SparrowSkillComponent.h"
#include "TopDownCombatCharacter.h"

namespace
{
	TAutoConsoleVariable<int32> CVarStudyR(TEXT("Sparrow.ArsenalStudy.R"), 0,
		TEXT("R presentation: 0 original, 1-4 archived, 5 light rails, 6 native gold pulse. Read at cast start."), ECVF_Cheat);
	TAutoConsoleVariable<int32> CVarStudyS(TEXT("Sparrow.ArsenalStudy.S"), 0,
		TEXT("S presentation: 10 installed; 11 pressure chambers, 12 crystal rake. Read at cast start."), ECVF_Cheat);

	void SetCraftConstant(FRawDistributionFloat& Raw, UObject* Outer, float Value)
	{
		UDistributionFloatConstant* Constant = NewObject<UDistributionFloatConstant>(Outer, NAME_None, RF_Transient);
		Constant->Constant = Value;
		Constant->bCanBeBaked = false;
		Constant->bIsDirty = false;
		Raw = FRawDistributionFloat();
		Raw.Distribution = Constant;
	}

	UParticleSystem* CraftVolleyTemplate(bool bPreparation)
	{
		static TWeakObjectPtr<UParticleSystem> PreparationCache;
		static TWeakObjectPtr<UParticleSystem> BurstCache;
		TWeakObjectPtr<UParticleSystem>& Cache = bPreparation ? PreparationCache : BurstCache;
		if (Cache.IsValid()) { return Cache.Get(); }
		UParticleSystem* Source = LoadObject<UParticleSystem>(nullptr,
			TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Primary/FX/P_SparrowPrimaryMuzzleFlash.P_SparrowPrimaryMuzzleFlash"));
		if (!Source) { return nullptr; }
		UParticleSystem* Copy = DuplicateObject<UParticleSystem>(Source, GetTransientPackage(),
			MakeUniqueObjectName(GetTransientPackage(), UParticleSystem::StaticClass(),
				bPreparation ? TEXT("SparrowRCraftPreparation") : TEXT("SparrowRCraftBurst")));
		Copy->SetFlags(RF_Transient);
		Copy->ClearFlags(RF_Public | RF_Standalone);
		bool bKeptGlow = false, bKeptWisps = false, bKeptSparks = false;
		// 원본에는 Sparks가 두 개다. 이름뿐 아니라 물리 이미터 한 개씩 선택한다.
		Copy->Emitters.RemoveAll([&](UParticleEmitter* Emitter)
		{
			if (!Emitter || Emitter->LODLevels.IsEmpty() || !Emitter->LODLevels[0] || !Emitter->LODLevels[0]->bEnabled) { return true; }
			const FName Name = Emitter->GetEmitterName();
			if (Name == TEXT("MuzzleGlow") && !bKeptGlow) { bKeptGlow = true; return false; }
			if (!bPreparation && Name == TEXT("Wisps") && !bKeptWisps) { bKeptWisps = true; return false; }
			if (!bPreparation && Name == TEXT("Sparks") && !bKeptSparks) { bKeptSparks = true; return false; }
			return true;
		});
		if (Copy->Emitters.Num() != (bPreparation ? 1 : 3)) { return nullptr; }
		for (UParticleEmitter* Emitter : Copy->Emitters)
		{
			if (!Emitter->IsIn(Copy)) { return nullptr; }
			const FName Name = Emitter->GetEmitterName();
			for (UParticleLODLevel* LOD : Emitter->LODLevels)
			{
				if (!LOD || !LOD->RequiredModule || !LOD->SpawnModule) { continue; }
				LOD->RequiredModule->EmitterLoops = bPreparation ? 0 : 1;
				LOD->RequiredModule->EmitterDuration = bPreparation ? 1.0f : .08f;
				LOD->RequiredModule->EmitterDurationLow = LOD->RequiredModule->EmitterDuration;
				LOD->RequiredModule->bEmitterDurationUseRange = false;
				LOD->RequiredModule->EmitterDelay = 0.0f;
				LOD->RequiredModule->EmitterDelayLow = 0.0f;
				LOD->RequiredModule->bEmitterDelayUseRange = false;
				LOD->RequiredModule->bKillOnDeactivate = false;
				SetCraftConstant(LOD->SpawnModule->Rate, LOD->SpawnModule, bPreparation ? 12.0f : 0.0f);
				SetCraftConstant(LOD->SpawnModule->RateScale, LOD->SpawnModule, 1.0f);
				SetCraftConstant(LOD->SpawnModule->BurstScale, LOD->SpawnModule, 1.0f);
				LOD->SpawnModule->BurstList.Reset();
				FParticleBurst Burst;
				Burst.Count = Name == TEXT("Sparks") ? 7 : Name == TEXT("Wisps") ? 4 : 1;
				Burst.CountLow = Burst.Count;
				Burst.Time = 0.0f;
				LOD->SpawnModule->BurstList.Add(Burst);
				if (!bPreparation && Name == TEXT("Wisps"))
				{
					// 짧은 원본 플라스마 흐름을 두 박자로 겹쳐 포구의 전방 방출을 읽히게 한다.
					FParticleBurst FollowThrough;
					FollowThrough.Count = FollowThrough.CountLow = 2;
					FollowThrough.Time = .03f;
					LOD->SpawnModule->BurstList.Add(FollowThrough);
				}
				LOD->Modules.RemoveAll([](UParticleModule* Module) { return Module && Module->IsA<UParticleModuleLight>(); });
				for (UParticleModule* Module : LOD->Modules)
				{
					if (!Module || !Module->IsIn(Copy)) { return nullptr; }
					if (!bPreparation && Name == TEXT("Wisps"))
					{
						if (UParticleModuleColor* Color = Cast<UParticleModuleColor>(Module))
						{
							// 원본 alpha .10은 Plasma의 .5*RelativeTime 침식으로 흐름이 생기기 전에 소거된다.
							// 복제 Wisps만 보정하고 원본 색/수명별 감쇠 곡선은 보존한다.
							SetCraftConstant(Color->StartAlpha, Color, .85f);
						}
					}
					if (UParticleModuleLifetime* Life = Cast<UParticleModuleLifetime>(Module))
					{
						UDistributionFloatUniform* Duration = NewObject<UDistributionFloatUniform>(Life, NAME_None, RF_Transient);
						Duration->Min = bPreparation ? .12f : Name == TEXT("Wisps") ? .16f : .09f;
						Duration->Max = bPreparation ? .19f : Name == TEXT("Wisps") ? .24f : .17f;
						Duration->bCanBeBaked = false;
						Duration->bIsDirty = false;
						Life->Lifetime = FRawDistributionFloat();
						Life->Lifetime.Distribution = Duration;
					}
				}
			}
			Emitter->UpdateModuleLists();
		}
		Cache = Copy;
		return Copy;
	}
}

ASparrowArsenalStudyFX::ASparrowArsenalStudyFX()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickGroup = TG_PostPhysics;
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
	SetActorEnableCollision(false);
	SetCanBeDamaged(false);
	Tags.Append({TEXT("SparrowSkillFX"), TEXT("SparrowArsenalStudy")});
}

bool ASparrowArsenalStudyFX::AddRenaissanceSurface(const TCHAR* MeshName, const TCHAR* MaterialName, int32 Index)
{
	const FString Folder(TEXT("/Game/TopDown/Characters/Sparrow/Materials/Renaissance20261027/"));
	UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *(Folder + TEXT("SM_Ren") + MeshName));
	UMaterialInterface* Source = LoadObject<UMaterialInterface>(nullptr, *(Folder + TEXT("M_Ren") + MaterialName));
	if (!Mesh || !Source) { return false; }
	UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(Source, this);
	if (!Material) { return false; }
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
	Surface->ComponentTags.Add(TEXT("SparrowRenaissance"));
	AddInstanceComponent(Surface);
	Surface->RegisterComponent();
	Material->SetScalarParameterValue(TEXT("Index"), Index);
	Material->SetScalarParameterValue(TEXT("Ascended"), bAscended ? 1.0f : 0.0f);
	Surfaces.Add(Surface);
	Materials.Add(Material);
	return true;
}

void ASparrowArsenalStudyFX::DrawRenaissance(float Since, float Fade)
{
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Forward).GetSafeNormal();
	const FQuat Axis = FRotationMatrix::MakeFromXZ(Forward, FVector::UpVector).ToQuat();
	const float Gather = FMath::SmoothStep(0.0f, Preparation, Age);
	const float Form = bAscended ? 1.12f : 1.0f;
	for (int32 Index = 0; Index < Surfaces.Num(); ++Index)
	{
		FVector Position = Origin;
		FQuat Rotation = Axis;
		FVector Scale(1.0f);
		float Live = Fade;
		if (Slot == 3)
		{
			// R: 두 짧은 광결과 각 파동의 불티만 남겨 빗살 부채 윤곽을 없앤다.
			const float Pulse = Pulses > 0 ? FMath::Exp(-FMath::Max(0.0f, Since) * 28.0f) : 0.0f;
			if (Index < 2)
			{
				const float Side = Index == 0 ? -1.0f : 1.0f;
				Position += Right * Side * 10.0f + FVector::UpVector * Side * 8.0f;
				Position -= Forward * (17.0f * (1.0f - Gather));
				Rotation *= FQuat(FVector::ForwardVector, Side * .65f);
				Scale = FVector((.30f + Pulse * .18f) * Form, .48f + Pulse * .25f, .45f);
				Live *= .13f * Gather + .74f * Pulse;
			}
			else
			{
				const int32 Spark = Index - 2;
				const float Angle = (Spark - 4) * 5.5f;
				const FVector Ray = Forward.RotateAngleAxis(Angle, FVector::UpVector);
				const float Travel = FMath::Clamp(Since, 0.0f, .14f);
				Position += Ray * (15.0f + Travel * (460.0f + Spark * 35.0f));
				Position += FVector::UpVector * ((Spark % 3 - 1) * (8.0f + Travel * 75.0f));
				Rotation = FRotationMatrix::MakeFromXZ(Ray, FVector::UpVector).ToQuat();
				Scale = FVector(.095f + (Spark % 3) * .025f, .24f, .28f);
				Live *= Pulses > 0 ? 1.0f - FMath::SmoothStep(.035f, .12f, Since) : 0.0f;
			}
		}
		else if (Style == 11 && Index < 3)
		{
			// S11: 원형 테두리 대신 원본 입체 광염 질감이 응축되고 전방으로 터진다.
			const float Local = Since - Index * .018f;
			const float Open = FMath::SmoothStep(0.0f, .16f, Age);
			const float Compress = FMath::SmoothStep(.19f, Preparation, Age);
			const float Launch = Pulses > 0 ? FMath::SmoothStep(0.0f, .09f, Local) : 0.0f;
			const float Span = (1.0f - Compress * .40f + Launch * .66f) * Form;
			Position += Forward * (-34.0f + Compress * 29.0f + Launch * 88.0f);
			Position += Right * (Index - 1) * (24.0f - Compress * 12.0f + Launch * 10.0f);
			Position += FVector::UpVector * (Index == 1 ? 14.0f : -5.0f);
			Scale = FVector(.67f + Launch * .62f, .68f * Span, 1.0f);
			Rotation *= FQuat(FVector::ForwardVector, (Index - 1) * .45f);
			Live *= Pulses > 0 ? (1.0f - FMath::SmoothStep(.15f, .29f, Local)) : Open * .78f;
		}
		else if (Style == 12 && Index < 7)
		{
			// S12: 평행한 짧은 결정 빗살이 벌어졌다가 사격축으로 모여 한 번에 끊어진다.
			const int32 Lane = Index - 3;
			const float Compress = FMath::SmoothStep(.17f, Preparation, Age);
			const float Flight = Pulses > 0 ? FMath::Clamp(Since / .12f, 0.0f, 1.0f) : 0.0f;
			Position += Right * Lane * FMath::Lerp(27.0f, 15.0f, Compress);
			Position += Forward * (-84.0f + 50.0f * Compress + Flight * 235.0f);
			Position += FVector::UpVector * ((Index % 2 == 0 ? -1.0f : 1.0f) * 13.0f * (1.0f - Compress));
			Scale = FVector((.65f + .28f * Gather) * Form, .35f * Form, .35f * Form);
			Rotation *= FQuat(FVector::ForwardVector, Index * .81f + Gather * .38f);
			Live *= Pulses > 0 ? 1.0f - FMath::SmoothStep(.06f, .18f, Since) : FMath::SmoothStep(Index * .012f, .14f + Index * .012f, Age);
		}
		else
		{
			const int32 Start = Style == 11 ? 3 : 7;
			const int32 Lane = Index - Start;
			const float Phase = Lane * PI / 3.0f;
			const float Compress = FMath::SmoothStep(.12f, Preparation, Age);
			const float Travel = Pulses > 0 ? FMath::Clamp(Since / .16f, 0.0f, 1.0f) : 0.0f;
			Position += (Right * FMath::Cos(Phase) + FVector::UpVector * FMath::Sin(Phase)) * (70.0f - Compress * 36.0f);
			Position += Forward * (-100.0f + Compress * 68.0f + Travel * 170.0f);
			Rotation *= FQuat(FVector::ForwardVector, Phase);
			Scale = FVector(.66f + Compress * .35f, .34f, .60f);
			Live *= Pulses > 0 ? 1.0f - FMath::SmoothStep(.07f, .23f, Since) : Gather * .66f;
		}
		Place(Index, Position, Rotation, Scale, Live, Since);
	}
}

int32 ASparrowArsenalStudyFX::GetCandidate(int32 SkillSlot)
{
	return SkillSlot == 3 ? FMath::Clamp(CVarStudyR.GetValueOnGameThread(), 0, 6) :
		SkillSlot == 5 ? FMath::Clamp(CVarStudyS.GetValueOnGameThread(), 0, 12) : 0;
}

UParticleSystem* ASparrowArsenalStudyFX::GetCraftImpactEffect()
{
	static TWeakObjectPtr<UParticleSystem> Cached;
	if (Cached.IsValid()) { return Cached.Get(); }
	UParticleSystem* Source = LoadObject<UParticleSystem>(nullptr,
		TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Ultimate/FX/P_Sparrow_UltHit.P_Sparrow_UltHit"));
	if (!Source) { return nullptr; }
	UParticleSystem* Copy = DuplicateObject<UParticleSystem>(Source, GetTransientPackage(),
		MakeUniqueObjectName(GetTransientPackage(), UParticleSystem::StaticClass(), TEXT("SparrowRCraftContact")));
	Copy->SetFlags(RF_Transient);
	Copy->ClearFlags(RF_Public | RF_Standalone);
	Copy->Emitters.RemoveAll([](UParticleEmitter* Emitter)
	{
		if (!Emitter) { return true; }
		const FName Name = Emitter->GetEmitterName();
		return Name != TEXT("Main Flames") && Name != TEXT("Wisps") &&
			Name != TEXT("Line Burst") && Name != TEXT("Sparks");
	});
	if (Copy->Emitters.IsEmpty()) { return nullptr; }
	for (UParticleEmitter* Emitter : Copy->Emitters)
	{
		if (!Emitter->IsIn(Copy)) { return nullptr; }
		const FName Name = Emitter->GetEmitterName();
		for (UParticleLODLevel* LOD : Emitter->LODLevels)
		{
			if (!LOD || !LOD->RequiredModule || !LOD->SpawnModule) { continue; }
			LOD->RequiredModule->EmitterLoops = 1;
			LOD->RequiredModule->EmitterDuration = .08f;
			LOD->RequiredModule->EmitterDurationLow = .08f;
			LOD->RequiredModule->bEmitterDurationUseRange = false;
			LOD->RequiredModule->EmitterDelay = 0.0f;
			LOD->RequiredModule->EmitterDelayLow = 0.0f;
			LOD->RequiredModule->bEmitterDelayUseRange = false;
			LOD->RequiredModule->bKillOnDeactivate = false;
			SetCraftConstant(LOD->SpawnModule->Rate, LOD->SpawnModule, 0.0f);
			SetCraftConstant(LOD->SpawnModule->RateScale, LOD->SpawnModule, 1.0f);
			SetCraftConstant(LOD->SpawnModule->BurstScale, LOD->SpawnModule, 1.0f);
			LOD->SpawnModule->BurstList.Reset();
			FParticleBurst Burst;
			Burst.Count = Name == TEXT("Main Flames") ? 1 : Name == TEXT("Wisps") ? 2 : 6;
			Burst.CountLow = Burst.Count;
			Burst.Time = 0.0f;
			LOD->SpawnModule->BurstList.Add(Burst);
			LOD->Modules.RemoveAll([](UParticleModule* Module) { return Module && Module->IsA<UParticleModuleLight>(); });
			for (UParticleModule* Module : LOD->Modules)
			{
				if (!Module || !Module->IsIn(Copy)) { return nullptr; }
				if (UParticleModuleLifetime* Life = Cast<UParticleModuleLifetime>(Module))
				{
					UDistributionFloatUniform* Duration = NewObject<UDistributionFloatUniform>(Life, NAME_None, RF_Transient);
					Duration->Min = .10f;
					Duration->Max = .18f;
					Duration->bCanBeBaked = false;
					Duration->bIsDirty = false;
					Life->Lifetime = FRawDistributionFloat();
					Life->Lifetime.Distribution = Duration;
				}
			}
		}
		Emitter->UpdateModuleLists();
	}
	Cached = Copy;
	return Copy;
}

bool ASparrowArsenalStudyFX::AddSurface(const TCHAR* Part, int32 Index)
{
	UStaticMesh* Plane = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
	const bool bSharedAccent = FCString::Strcmp(Part, TEXT("Streak")) == 0 || FCString::Strcmp(Part, TEXT("Ember")) == 0;
	const TCHAR* Folder = Style >= 9 ? TEXT("ImpactRevision20261027") :
		Style >= 5 && !bSharedAccent ? TEXT("SeraphStudies20261027") :
		Style >= 4 ? TEXT("Impact20261027") : TEXT("Celestial20261026");
	UMaterialInterface* Source = LoadObject<UMaterialInterface>(nullptr, *FString::Printf(
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/%s/M_Study%s.M_Study%s"), Folder, Part, Part));
	if (!Plane || !Source) { return false; }
	UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(Source, this);
	if (!Material) { return false; }
	Material->SetScalarParameterValue(TEXT("Index"), Index);
	Material->SetScalarParameterValue(TEXT("Style"), Style);
	Material->SetScalarParameterValue(TEXT("Ascended"), bAscended ? 1.0f : 0.0f);
	Material->SetScalarParameterValue(TEXT("Sharp"), Slot == 5 ? 1.0f : 0.0f);
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
	Surface->ComponentTags.Add(FName(Part));
	AddInstanceComponent(Surface);
	Surface->RegisterComponent();
	Surfaces.Add(Surface);
	Materials.Add(Material);
	return true;
}

bool ASparrowArsenalStudyFX::Initialize(ATopDownCombatCharacter* Character, int32 SkillSlot, int32 Candidate,
	const FVector& InOrigin, const FVector& Direction, float PreparationSeconds)
{
	if (!IsValid(Character) || Character != GetOwner() || !Character->GetMesh() || !GetWorld() ||
		(SkillSlot != 3 && SkillSlot != 5) || Candidate < 1 || Candidate > (SkillSlot == 5 ? 12 : 6) ||
		InOrigin.ContainsNaN() || Direction.ContainsNaN() || Direction.IsNearlyZero()) { return false; }
	const USparrowSkillComponent* Skills = Character->FindComponentByClass<USparrowSkillComponent>();
	if (!Skills) { return false; }
	Caster = Character;
	Slot = SkillSlot;
	Style = Candidate;
	Origin = InOrigin;
	Forward = Direction.GetSafeNormal2D();
	if (Forward.IsNearlyZero()) { return false; }
	Preparation = FMath::Max(.08f, PreparationSeconds);
	bAscended = Skills->GetAscensionRemaining() > 0.0f;
	if (UsesCraftVolleyPresentation())
	{
		if (!CraftVolleyTemplate(false)) { return false; }
		CraftPreparation = SpawnCraftPulse(true);
		if (!CraftPreparation) { return false; }
		Tags.Add(TEXT("SparrowStudyR6"));
		if (bAscended) { Tags.Add(TEXT("SparrowStudyAscended")); }
		bReady = true;
		SetLifeSpan(4.0f);
		return true;
	}
	if ((Slot == 3 && Style == 5) || (Slot == 5 && Style >= 11))
	{
		const int32 Count = Slot == 3 ? 11 : Style == 11 ? 9 : 13;
		for (int32 Index = 0; Index < Count; ++Index)
		{
			const bool bLens = Slot == 5 && Style == 11 && Index < 3;
			const bool bFacet = Slot == 5 && Style == 12 && Index < 7;
			if (!AddRenaissanceSurface(bLens ? TEXT("SPlume") : bFacet ? TEXT("Facet") : TEXT("Rail"),
				bLens ? TEXT("SPlasma") : bFacet ? TEXT("Facet") : TEXT("Rail"), Index)) { return false; }
		}
		Tags.Add(FName(*FString::Printf(TEXT("SparrowStudy%c%d"), Slot == 3 ? TEXT('R') : TEXT('S'), Style)));
		if (bAscended) { Tags.Add(TEXT("SparrowStudyAscended")); }
		bReady = true;
		SetLifeSpan(Slot == 3 ? 2.0f : .82f);
		return true;
	}
	const int32 SurfaceCount = Style >= 4 ? 24 : 18;
	for (int32 Index = 0; Index < SurfaceCount; ++Index)
	{
		const TCHAR* Part = Index < 3 ? (Style == 2 ? TEXT("Prism") : TEXT("Crescent")) :
			Index < 12 ? TEXT("Filament") : TEXT("Fracture");
		if (Style == 4)
		{
			Part = Slot == 3 ? (Index < 2 ? TEXT("Recoil") : Index == 2 ? TEXT("Pressure") :
				Index == 3 ? TEXT("Eruption") : Index < 13 ? TEXT("Streak") : TEXT("Ember")) :
				(Index < 5 ? TEXT("Pressure") : Index < 7 ? TEXT("Eruption") :
				Index < 12 ? TEXT("Streak") : TEXT("Ember"));
		}
		else if (Style == 5)
		{
			Part = Index < 6 ? TEXT("Tempest") : Index < 9 ? TEXT("Plasma") : Index < 14 ? TEXT("Streak") : TEXT("Ember");
		}
		else if (Style == 6)
		{
			Part = Index < 9 || Index >= 14 ? TEXT("Shard") : TEXT("Streak");
		}
		else if (Style == 7) { Part = TEXT("Feather"); }
		else if (Style == 8)
		{
			Part = Index < 4 || (Index >= 9 && Index < 15) ? TEXT("Fan") : Index < 9 ? TEXT("Streak") : TEXT("Ember");
		}
		else if (Style >= 9)
		{
			Part = Index < 3 ?
				(Style == 9 ? TEXT("RevisionWind") : TEXT("RevisionMantle")) :
				Index < 6 ? TEXT("RevisionCore") : Index < 11 ? TEXT("RevisionJet") :
				Index < 17 ? (Style == 9 ? TEXT("RevisionSurge") : TEXT("RevisionBurst")) : TEXT("RevisionSplinter");
		}
		if (!AddSurface(Part, Index)) { return false; }
	}
	Tags.Add(FName(*FString::Printf(TEXT("SparrowStudy%c%d"), Slot == 3 ? TEXT('R') : TEXT('S'), Style)));
	if (bAscended) { Tags.Add(TEXT("SparrowStudyAscended")); }
	bReady = true;
	SetLifeSpan(Slot == 3 ? 2.0f : .82f);
	return true;
}

void ASparrowArsenalStudyFX::Pulse(const FVector& InOrigin, const FVector& Direction)
{
	if (!bReady || FadeAt >= 0.0f || InOrigin.ContainsNaN() || Direction.ContainsNaN() || Direction.IsNearlyZero()) { return; }
	Origin = InOrigin;
	Forward = Direction.GetSafeNormal2D();
	PulseAt = Age;
	++Pulses;
	if (UsesCraftVolleyPresentation())
	{
		if (CraftPreparation) { CraftPreparation->DestroyComponent(); CraftPreparation = nullptr; }
		if (Pulses <= 10)
		{
			if (UParticleSystemComponent* Burst = SpawnCraftPulse(false))
			{
				CraftBursts.Add(Burst);
				CraftBurstTimes.Add(Age);
			}
		}
		UE_LOG(LogTemp, Display, TEXT("SPARROW_RCRAFT pulse=%d emitters=3 active_bursts=%d"), Pulses, CraftBursts.Num());
	}
}

void ASparrowArsenalStudyFX::FinishCast()
{
	if (FadeAt >= 0.0f) { return; }
	if (Pulses == 0) { Destroy(); return; }
	FadeAt = Age;
	if (CraftPreparation) { CraftPreparation->DestroyComponent(); CraftPreparation = nullptr; }
	SetLifeSpan(UsesCraftVolleyPresentation() ? .29f : .18f);
}

UParticleSystemComponent* ASparrowArsenalStudyFX::SpawnCraftPulse(bool bPreparation)
{
	UParticleSystem* Template = CraftVolleyTemplate(bPreparation);
	if (!Template || !GetWorld() || !Caster.IsValid()) { return nullptr; }
	UParticleSystemComponent* Particle = NewObject<UParticleSystemComponent>(this, NAME_None, RF_Transient);
	Particle->bAutoActivate = false;
	Particle->bAutoDestroy = false;
	Particle->SetupAttachment(RootComponent);
	Particle->SetAbsolute(true, true, true);
	Particle->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Particle->SetGenerateOverlapEvents(false);
	Particle->SetCanEverAffectNavigation(false);
	Particle->SetCastShadow(false);
	Particle->SetTemplate(Template);
	Particle->bOverrideLODMethod = true;
	Particle->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
	Particle->ComponentTags.Append({TEXT("SparrowSkillFX"), bPreparation ? TEXT("SparrowRCraftPreparation") : TEXT("SparrowRCraftBurst")});
	AddInstanceComponent(Particle);
	Particle->RegisterComponent();
	Particle->SetWorldLocationAndRotation(Origin + Forward * (bPreparation ? 8.0f : 24.0f), Forward.Rotation());
	Particle->SetWorldScale3D(FVector(bPreparation ? 1.15f : bAscended ? 1.52f : 1.34f));
	Particle->SetLODLevel(0);
	Particle->ActivateSystem(true);
	Particle->SetLODLevel(0);
	return Particle;
}

void ASparrowArsenalStudyFX::UpdateCraftVolley()
{
	if (CraftPreparation)
	{
		CraftPreparation->SetWorldLocationAndRotation(Origin + Forward * 8.0f, Forward.Rotation());
		CraftPreparation->SetWorldScale3D(FVector(FMath::Lerp(.90f, 1.60f, FMath::SmoothStep(0.0f, Preparation, Age))));
	}
	for (int32 Index = CraftBursts.Num() - 1; Index >= 0; --Index)
	{
		if (Age - CraftBurstTimes[Index] >= .29f || !IsValid(CraftBursts[Index]))
		{
			if (IsValid(CraftBursts[Index])) { CraftBursts[Index]->DestroyComponent(); }
			CraftBursts.RemoveAtSwap(Index);
			CraftBurstTimes.RemoveAtSwap(Index);
		}
	}
}

void ASparrowArsenalStudyFX::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (IsValid(CraftPreparation)) { CraftPreparation->DestroyComponent(); }
	CraftPreparation = nullptr;
	for (UParticleSystemComponent* Particle : CraftBursts)
	{
		if (IsValid(Particle)) { Particle->DestroyComponent(); }
	}
	CraftBursts.Reset();
	CraftBurstTimes.Reset();
	Super::EndPlay(EndPlayReason);
}

void ASparrowArsenalStudyFX::Place(int32 Index, FVector Position, FQuat Rotation, FVector Scale, float Envelope, float Since)
{
	Surfaces[Index]->SetWorldLocationAndRotation(Position, Rotation);
	Surfaces[Index]->SetWorldScale3D(Scale);
	Surfaces[Index]->SetVisibility(Envelope > .006f);
	Materials[Index]->SetScalarParameterValue(TEXT("Age"), Age);
	Materials[Index]->SetScalarParameterValue(TEXT("PulseAge"), Since);
	Materials[Index]->SetScalarParameterValue(TEXT("Progress"), FMath::Clamp(Age / Preparation, 0.0f, 1.0f));
	Materials[Index]->SetScalarParameterValue(TEXT("Envelope"), Envelope);
}

void ASparrowArsenalStudyFX::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!bReady || !Caster.IsValid() || Caster->IsActorBeingDestroyed() || GetOwner() != Caster.Get()) { Destroy(); return; }
	const USparrowSkillComponent* Skills = Caster->FindComponentByClass<USparrowSkillComponent>();
	if (!Skills || (bAscended && Skills->GetAscensionRemaining() <= 0.0f)) { Destroy(); return; }
	Age += FMath::Max(0.0f, DeltaSeconds);
	if (Slot == 3 && FadeAt < 0.0f && (!Skills->IsCasting() || Skills->GetActiveSkillNumber() != 4)) { FinishCast(); }
	if (IsActorBeingDestroyed()) { return; }
	if (Pulses == 0) { Origin = Skills->GetArrowOrigin(); }
	if (UsesCraftVolleyPresentation()) { UpdateCraftVolley(); return; }
	const float Fade = FadeAt < 0.0f ? 1.0f : 1.0f - FMath::SmoothStep(0.0f, .18f, Age - FadeAt);
	if ((Slot == 3 && Style == 5) || (Slot == 5 && Style >= 11)) { DrawRenaissance(Age - PulseAt, Fade); return; }
	if (Style >= 9) { DrawSharpRevision(Age - PulseAt, Fade); return; }
	if (Style >= 5) { DrawSharpDirections(Age - PulseAt, Fade); return; }
	if (Style == 4)
	{
		if (Slot == 3) { DrawVolleyRecrafted(Age - PulseAt, Fade); }
		else { DrawSharpRecrafted(Age - PulseAt, Fade); }
		return;
	}
	if (Slot == 3) { DrawVolley(Age - PulseAt, Fade); }
	else { DrawSharp(Age - PulseAt, Fade); }
}

void ASparrowArsenalStudyFX::DrawVolley(float Since, float Fade)
{
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Forward).GetSafeNormal();
	FVector Normal = FVector::UpVector;
	if (APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(this, 0)) { Normal = Camera->GetCameraLocation() - Origin; }
	const FQuat Front = FRotationMatrix::MakeFromXZ(Right, Forward).ToQuat();
	const FQuat Facing = FRotationMatrix::MakeFromXZ(Forward, Normal).ToQuat();
	const float Gather = FMath::SmoothStep(0.0f, Preparation, Age);
	const float Kick = Pulses > 0 ? FMath::Exp(-Since * 23.0f) : 0.0f;
	const float Form = bAscended ? 1.15f : 1.0f;
	for (int32 Index = 0; Index < Surfaces.Num(); ++Index)
	{
		FVector Position = Origin;
		FQuat Rotation = Facing;
		FVector Scale(1.0f);
		float Live = Fade;
		if (Index < 3)
		{
			const float Layer = static_cast<float>(Index);
			Rotation = Front;
			if (Style == 1)
			{
				Position += Forward * (18.0f + Layer * 14.0f + Kick * (7.0f + Layer * 5.0f));
				Scale = FVector(2.55f - Layer * .35f, 3.0f - Layer * .33f, 1.0f) * (Form * (.78f + Gather * .22f - Kick * .07f));
				Rotation *= FQuat(FVector::UpVector, (Layer - 1.0f) * .20f);
			}
			else if (Style == 2)
			{
				Position += Forward * (35.0f + Layer * 62.0f + Kick * 10.0f);
				Scale = FVector(1.75f - Layer * .23f, 2.4f - Layer * .30f, 1.0f) * Form;
				Live *= .48f + .52f * FMath::Pow(FMath::Max(0.0f, FMath::Cos(Since * 23.0f - Layer * 1.4f)), 4.0f);
			}
			else
			{
				Position += Forward * (28.0f + Layer * 12.0f);
				Rotation *= FQuat(FVector::UpVector, (Pulses % 2 == 0 ? 1.0f : -1.0f) * (.55f + Layer * .35f));
				Scale = FVector(3.0f, 1.35f + Layer * .18f, 1.0f) * Form;
				Live *= .30f + .70f * Kick;
			}
		}
		else if (Index < 12)
		{
			const int32 I = Index - 3;
			const float Side = I % 2 == 0 ? -1.0f : 1.0f;
			const float Layer = static_cast<float>(I / 2);
			if (Style == 1)
			{
				Position += Right * Side * (42.0f + Layer * 16.0f) + FVector::UpVector * ((I % 3 - 1) * 22.0f);
				Position += Forward * (15.0f + Kick * 36.0f);
				Rotation *= FQuat(FVector::UpVector, Side * (.22f + Layer * .11f));
				Scale = FVector(1.65f, .64f, 1.0f) * Form;
			}
			else if (Style == 2)
			{
				const float Compression = FMath::Fmod(Age * (1.0f / .13f) + I * .117f, 1.0f);
				Position += Right * Side * (110.0f * (1.0f - Compression)) + Forward * (-45.0f + Compression * 135.0f);
				Position += FVector::UpVector * ((I % 3 - 1) * 24.0f * (1.0f - Compression));
				Rotation *= FQuat(FVector::UpVector, -Side * .45f);
				Scale = FVector(.90f, .38f, 1.0f) * Form;
				Live *= .80f;
			}
			else
			{
				Position += Forward * (38.0f + Layer * 22.0f + Kick * 46.0f) + Right * Side * (24.0f + Layer * 18.0f);
				Position += FVector::UpVector * FMath::Sin(I * 1.3f) * 21.0f;
				Rotation *= FQuat(FVector::UpVector, Side * (.50f - Kick * .32f));
				Scale = FVector(1.55f, .48f, 1.0f) * Form;
				Live *= (I % 2 == Pulses % 2 ? 1.0f : .38f);
			}
		}
		else
		{
			const int32 I = Index - 12;
			const float Side = I % 2 == 0 ? -1.0f : 1.0f;
			Position += Forward * (55.0f + I * 12.0f + FMath::Min(Since, .16f) * 250.0f);
			Position += Right * Side * (22.0f + (I / 2) * 21.0f);
			Position += FVector::UpVector * ((I % 3 - 1) * 18.0f);
			Scale = FVector(.90f, .75f, 1.0f) * Form;
			Live *= Pulses > 0 ? FMath::Exp(-Since * 21.0f) : 0.0f;
		}
		Place(Index, Position, Rotation, Scale, Live, Since);
	}
}

void ASparrowArsenalStudyFX::DrawSharp(float Since, float Fade)
{
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Forward).GetSafeNormal();
	FVector Normal = FVector::UpVector;
	if (APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(this, 0)) { Normal = Camera->GetCameraLocation() - Origin; }
	const FQuat Front = FRotationMatrix::MakeFromXZ(Right, Forward).ToQuat();
	const FQuat Facing = FRotationMatrix::MakeFromXZ(Forward, Normal).ToQuat();
	const float Gather = FMath::SmoothStep(.06f, Preparation, Age);
	const bool bReleased = Pulses > 0;
	const float Burst = bReleased ? FMath::SmoothStep(0.0f, .17f, Since) : 0.0f;
	const float Form = bAscended ? 1.14f : 1.0f;
	for (int32 Index = 0; Index < Surfaces.Num(); ++Index)
	{
		FVector Position = Origin;
		FQuat Rotation = Front;
		FVector Scale(1.0f);
		float Live = Fade * (bReleased ? 1.0f - FMath::SmoothStep(.16f, .29f, Since) : FMath::SmoothStep(.015f, .08f, Age));
		if (Index < 3)
		{
			const float Layer = static_cast<float>(Index);
			if (Style == 1)
			{
				Position += Forward * (15.0f + Layer * 14.0f + Burst * (20.0f + Layer * 22.0f));
				Rotation *= FQuat(FVector::UpVector, (Layer - 1.0f) * (.4f + Burst * .6f));
				Scale = FVector(3.05f - Layer * .37f, 3.05f - Layer * .37f, 1.0f) * Form * (1.0f - Gather * .22f + Burst * .38f);
			}
			else if (Style == 2)
			{
				Position += Right * (Layer - 1.0f) * 46.0f * (1.0f - Gather * .72f);
				Position += FVector::UpVector * (Index == 1 ? 22.0f : -10.0f);
				Position += Forward * (18.0f + Layer * 9.0f + Burst * 70.0f);
				Scale = FVector(2.9f, 2.9f, 1.0f) * Form * (1.0f - Gather * .50f + Burst * .55f);
			}
			else
			{
				const float Stage = FMath::Clamp((Age - Layer * .055f) / .14f, 0.0f, 1.0f);
				Position += Forward * (-24.0f + Layer * 54.0f + Burst * 55.0f);
				Scale = FVector(2.65f - Layer * .25f, 2.65f - Layer * .25f, 1.0f) * Form * (.4f + Stage * .60f);
				Rotation *= FQuat(FVector::UpVector, (Layer - 1.0f) * .35f);
				Live *= Stage;
			}
		}
		else if (Index < 12)
		{
			const int32 I = Index - 3;
			const float Phase = I * 2.399963f;
			float Radius = (Style == 2 ? 88.0f : 64.0f) * (1.0f - Gather * .52f + Burst * .9f);
			Position += Right * FMath::Cos(Phase) * Radius + FVector::UpVector * FMath::Sin(Phase) * Radius;
			Position += Forward * (bReleased ? 50.0f + Burst * (90.0f + I * 13.0f) : -38.0f + Gather * 42.0f);
			Rotation = Facing * FQuat(FVector::UpVector, Style == 1 ? FMath::Cos(Phase) * .60f : 0.0f);
			Scale = FVector(Style == 3 ? 2.15f : 1.4f, .52f, 1.0f) * Form;
		}
		else
		{
			const int32 I = Index - 12;
			const float Phase = I * 2.399963f;
			Position += Forward * (35.0f + Burst * (45.0f + I * 13.0f));
			Position += (Right * FMath::Cos(Phase) + FVector::UpVector * FMath::Sin(Phase)) * (25.0f + Burst * 66.0f);
			Rotation = Facing;
			Scale = FVector(1.4f, 1.2f, 1.0f) * Form;
			Live *= bReleased ? FMath::Exp(-Since * 7.0f) : 0.0f;
		}
		Place(Index, Position, Rotation, Scale, Live, Since);
	}
}

void ASparrowArsenalStudyFX::DrawVolleyRecrafted(float Since, float Fade)
{
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Forward).GetSafeNormal();
	FVector Normal = FVector::UpVector;
	if (APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(this, 0)) { Normal = Camera->GetCameraLocation() - Origin; }
	const FQuat Facing = FRotationMatrix::MakeFromXZ(Forward, Normal).ToQuat();
	const FQuat Front = FRotationMatrix::MakeFromXZ(Right, Forward).ToQuat();
	const float Gather = FMath::SmoothStep(.015f, Preparation, Age);
	const float T = Pulses > 0 ? FMath::Max(0.0f, Since) : 0.0f;
	const float Kick = Pulses > 0 ? FMath::Exp(-T * 32.0f) : 0.0f;
	const float Form = bAscended ? 1.12f : 1.0f;
	const float Breath = Pulses > 0 ? 1.0f - FMath::SmoothStep(.060f, .120f, T) : Gather * .80f;
	for (int32 Index = 0; Index < Surfaces.Num(); ++Index)
	{
		FVector Position = Origin;
		FQuat Rotation = Facing;
		FVector Scale(1.0f);
		float Live = Fade;
		if (Index < 2)
		{
			// 발사점에 붙은 두꺼운 광막이 실탄 발사 직후 짧게 밀렸다가 다시 응축된다.
			Position += Forward * 93.0f + FVector::UpVector * (Index == 0 ? -6.0f : 10.0f);
			Rotation *= FQuat(FVector::UpVector, Index == 0 ? -.035f : .035f);
			Scale = FVector(2.20f, 2.40f, 1.0f) * Form;
			Live *= Breath * (Index == 0 ? 1.0f : .55f);
		}
		else if (Index == 2)
		{
			Position += Forward * (10.0f - Kick * 8.0f);
			Rotation = Front;
			Scale = FVector(2.15f, 2.15f, 1.0f) * Form * (.78f + Gather * .22f - Kick * .12f);
			Live *= .38f * Gather + Kick * .50f;
		}
		else if (Index == 3)
		{
			Position += Forward * (18.0f + FMath::Min(T, .075f) * 640.0f);
			Rotation = Front;
			Scale = FVector(1.85f, 1.85f, 1.0f) * Form * (1.0f + FMath::Min(T, .10f) * 5.0f);
			Live *= Pulses > 0 ? FMath::Exp(-T * 36.0f) : 0.0f;
		}
		else if (Index < 13)
		{
			// 전체 사격 부채꼴과 같은 축. 길게 이어진 빔 대신 화살 바로 뒤의 짧은 빛결만 보인다.
			const int32 I = Index - 4;
			const FVector Shot = Forward.RotateAngleAxis(-31.2f + I * 7.8f, FVector::UpVector);
			Position += Shot * (38.0f + FMath::Min(T, .09f) * 2600.0f);
			Position += FVector::UpVector * ((I % 3 - 1) * 5.0f);
			Rotation = FRotationMatrix::MakeFromXZ(Shot, Normal).ToQuat();
			Scale = FVector(1.0f, .48f, 1.0f) * Form;
			Live *= Pulses > 0 ? (1.0f - FMath::SmoothStep(.035f, .090f, T)) * .90f : 0.0f;
		}
		else
		{
			const int32 I = Index - 13;
			const float Phase = I * 2.399963f + (Pulses % 3) * .40f;
			const FVector Radial = Right * FMath::Cos(Phase) + FVector::UpVector * FMath::Sin(Phase);
			const bool bGathering = Pulses == 0 || (Pulses < 10 && T > .085f);
			if (bGathering)
			{
				const float Pull = Pulses == 0 ? Gather : FMath::SmoothStep(.085f, .130f, T);
				Position += Radial * FMath::Lerp(58.0f, 8.0f, Pull) + Forward * (12.0f - Pull * 14.0f);
				Rotation = FRotationMatrix::MakeFromXZ(-Radial, Normal).ToQuat();
				Scale = FVector(.40f + (I % 3) * .08f, .23f, 1.0f) * Form;
				Live *= .35f + Pull * .65f;
			}
			else
			{
				Position += Radial * (20.0f + FMath::Min(T, .12f) * (260.0f + I * 16.0f));
				Position += Forward * (16.0f - FMath::Min(T, .12f) * (170.0f + I * 11.0f));
				Rotation = FRotationMatrix::MakeFromXZ((Radial - Forward * .65f).GetSafeNormal(), Normal).ToQuat();
				Scale = FVector(.48f + (I % 3) * .12f, .28f, 1.0f) * Form;
				Live *= FMath::Exp(-T * 22.0f);
			}
		}
		Place(Index, Position, Rotation, Scale, Live, Since);
	}
}

void ASparrowArsenalStudyFX::DrawSharpRecrafted(float Since, float Fade)
{
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Forward).GetSafeNormal();
	const bool bReleased = Pulses > 0;
	const FVector Base = Origin + (bReleased ? FVector::ZeroVector : Forward * 20.0f);
	FVector Normal = FVector::UpVector;
	if (APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(this, 0)) { Normal = Camera->GetCameraLocation() - Base; }
	const FQuat Front = FRotationMatrix::MakeFromXZ(Right, Forward).ToQuat();
	const FQuat Facing = FRotationMatrix::MakeFromXZ(Forward, Normal).ToQuat();
	const float Open = 1.0f - FMath::Pow(1.0f - FMath::Clamp(Age / .13f, 0.0f, 1.0f), 3.0f);
	const float Compress = FMath::SmoothStep(.20f, Preparation - .012f, Age);
	const float T = bReleased ? FMath::Max(0.0f, Since) : 0.0f;
	const float Form = bAscended ? 1.10f : 1.0f;
	static const float CircleScale[] = {3.15f, 2.18f, 2.80f, 1.72f, 2.38f};
	for (int32 Index = 0; Index < Surfaces.Num(); ++Index)
	{
		FVector Position = Base;
		FQuat Rotation = Front;
		FVector Scale(1.0f);
		float Live = Fade;
		if (Index < 5)
		{
			const float Phase = HALF_PI + Index * (2.0f * PI / 5.0f);
			const FVector Radial = Right * FMath::Cos(Phase) + FVector::UpVector * FMath::Sin(Phase);
			Position += Radial * 45.0f + Forward * (Index * 1.8f - T * 50.0f);
			const float Size = CircleScale[Index] * Form * (.40f + Open * .60f) * (1.0f - Compress * .45f);
			Scale = FVector(Size, Size, 1.0f);
			Live *= Open * (bReleased ? 1.0f - FMath::SmoothStep(.020f, .085f, T) : 1.0f);
		}
		else if (Index < 7)
		{
			// 압축된 원이 사라지는 찰나에 별도의 넓은 광면이 두 번 짧게 치고 빠진다.
			const float Delay = Index == 5 ? 0.0f : .040f;
			const float BurstAge = FMath::Max(0.0f, T - Delay);
			Position += Forward * (22.0f + BurstAge * 280.0f);
			const float Size = (Index == 5 ? 2.40f : 3.10f) * Form * (.64f + FMath::SmoothStep(0.0f, .10f, BurstAge) * .58f);
			Scale = FVector(Size, Size, 1.0f);
			Live *= bReleased && T >= Delay ? (1.0f - FMath::SmoothStep(.045f, .18f, BurstAge)) * (Index == 5 ? 1.0f : .70f) : 0.0f;
			Place(Index, Position, Rotation, Scale, Live, bReleased ? BurstAge : 100.0f);
			continue;
		}
		else if (Index < 12)
		{
			const int32 I = Index - 7;
			const float Phase = HALF_PI + I * (2.0f * PI / 5.0f);
			Position += (Right * FMath::Cos(Phase) + FVector::UpVector * FMath::Sin(Phase)) * 45.0f;
			// 다섯 발사구와 동일한 평행 방향. 실탄보다 길게 남는 연속 빔을 만들지 않는다.
			Position += Forward * (bReleased ? 25.0f + FMath::Min(T, .070f) * 6000.0f : -34.0f);
			Rotation = Facing;
			Scale = FVector(bReleased ? 1.0f : .75f, .58f, 1.0f) * Form;
			Live *= bReleased ? 1.0f - FMath::SmoothStep(.025f, .070f, T) : Compress * .70f;
		}
		else
		{
			const int32 I = Index - 12;
			const float Phase = I * 2.399963f;
			const FVector Radial = Right * FMath::Cos(Phase) + FVector::UpVector * FMath::Sin(Phase);
			Position += Radial * (26.0f + FMath::Min(T, .22f) * (310.0f + (I % 4) * 90.0f));
			Position += Forward * (12.0f + FMath::Min(T, .22f) * (150.0f + I * 20.0f));
			Rotation = FRotationMatrix::MakeFromXZ((Radial + Forward * .50f).GetSafeNormal(), Normal).ToQuat();
			Scale = FVector(.50f + (I % 3) * .16f, .30f, 1.0f) * Form;
			Live *= bReleased ? FMath::Exp(-T * 10.0f) : 0.0f;
		}
		Place(Index, Position, Rotation, Scale, Live, Since);
	}
}

void ASparrowArsenalStudyFX::DrawSharpDirections(float Since, float Fade)
{
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Forward).GetSafeNormal();
	const bool bReleased = Pulses > 0;
	const FVector Base = Origin + (bReleased ? FVector::ZeroVector : Forward * 20.0f);
	FVector Normal = FVector::UpVector;
	if (APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(this, 0)) { Normal = Camera->GetCameraLocation() - Base; }
	const FQuat Front = FRotationMatrix::MakeFromXZ(Right, Forward).ToQuat();
	const FQuat Facing = FRotationMatrix::MakeFromXZ(Forward, Normal).ToQuat();
	const float Open = FMath::SmoothStep(.015f, .13f, Age);
	const float Compress = FMath::SmoothStep(.18f, Preparation - .010f, Age);
	const float T = bReleased ? FMath::Max(0.0f, Since) : 0.0f;
	const float Form = bAscended ? 1.12f : 1.0f;
	for (int32 Index = 0; Index < Surfaces.Num(); ++Index)
	{
		FVector Position = Base;
		FQuat Rotation = Front;
		FVector Scale(1.0f);
		float Live = Fade;
		const int32 StreakStart = Style == 8 ? 4 : 9;
		if (Style != 7 && Index >= StreakStart && Index < StreakStart + 5)
		{
			const float Phase = HALF_PI + (Index - StreakStart) * (2.0f * PI / 5.0f);
			Position += (Right * FMath::Cos(Phase) + FVector::UpVector * FMath::Sin(Phase)) * 45.0f;
			Position += Forward * (25.0f + FMath::Min(T, .070f) * 6000.0f);
			Rotation = Facing;
			Scale = FVector(1.05f, .58f, 1.0f) * Form;
			Live *= bReleased ? 1.0f - FMath::SmoothStep(.025f, .070f, T) : 0.0f;
		}
		else if (Style == 5)
		{
			if (Index < 6)
			{
				const float Phase = Index * (PI / 3.0f) + Age * 8.0f;
				const FVector Radial = Right * FMath::Cos(Phase) + FVector::UpVector * FMath::Sin(Phase);
				Position += Radial * (95.0f - Compress * 74.0f + T * 220.0f) + Forward * (8.0f + Index * 4.0f + T * 340.0f);
				Rotation *= FQuat(FVector::UpVector, Phase + .65f);
				Scale = FVector(1.95f, 1.28f, 1.0f) * Form * (.50f + Open * .50f) * (1.0f - Compress * .30f + T * 1.5f);
				Live *= Open * (bReleased ? 1.0f - FMath::SmoothStep(.055f, .20f, T) : 1.0f);
			}
			else if (Index < 9)
			{
				Position += Forward * (20.0f + (Index - 6) * 7.0f + T * 250.0f);
				Rotation = Index == 6 ? Front : Facing * FQuat(FVector::UpVector, (Index - 7) * .75f);
				Scale = FVector(2.70f, 2.70f, 1.0f) * Form * (1.0f - Compress * .45f + T * 4.0f);
				Live *= Open * (bReleased ? 1.0f - FMath::SmoothStep(.07f, .26f, T) : .72f);
			}
			else
			{
				const float Phase = (Index - 14) * 2.399963f + Age * 4.0f;
				const FVector Radial = Right * FMath::Cos(Phase) + FVector::UpVector * FMath::Sin(Phase);
				Position += Radial * (bReleased ? 18.0f + T * 520.0f : 115.0f * (1.0f - Compress)) + Forward * (T * 290.0f);
				Rotation = FRotationMatrix::MakeFromXZ((Radial + Forward * .3f).GetSafeNormal(), Normal).ToQuat();
				Scale = FVector(.62f, .27f, 1.0f) * Form;
				Live *= bReleased ? FMath::Exp(-T * 10.0f) : Open * .72f;
			}
		}
		else if (Style == 6)
		{
			const bool bMain = Index < 9;
			const int32 I = bMain ? Index : Index - 14;
			const FVector Offset = Right * ((I - 4.0f) * 23.0f) + FVector::UpVector * ((I % 3 - 1) * 39.0f);
			Position += Offset * (1.0f - Compress * .68f + T * 5.0f) + Forward * (18.0f + (I % 3 - 1) * 28.0f + T * (160.0f + I * 20.0f));
			Rotation *= FQuat(FVector::UpVector, .72f + (I % 3 - 1) * .58f + (I % 2 == 0 ? 1.0f : -1.0f) * T * 5.0f);
			Rotation *= FQuat(FVector::ForwardVector, (I % 3 - 1) * .45f);
			Scale = FVector(bMain ? 1.28f * (1.0f - (I % 3) * .15f) : .55f,
				bMain ? .78f : .48f, 1.0f) * Form * (.70f + Open * .30f);
			Live *= bMain ? Open * (bReleased ? 1.0f - FMath::SmoothStep(.06f, .22f, T) : 1.0f) :
				bReleased ? FMath::Exp(-T * 9.0f) : 0.0f;
		}
		else if (Style == 7)
		{
			if (Index < 15)
			{
				const int32 Group = Index / 3;
				const int32 Lane = Index % 3 - 1;
				const float Phase = HALF_PI + Group * (2.0f * PI / 5.0f);
				const FVector ShotOffset = (Right * FMath::Cos(Phase) + FVector::UpVector * FMath::Sin(Phase)) * 45.0f + Right * (Lane * 8.0f);
				const FVector Crown = Right * ((Group - 2) * 40.0f + Lane * 19.0f) + FVector::UpVector * (65.0f - FMath::Abs(Group - 2) * 18.0f + Lane * 19.0f) - Forward * (Lane == 0 ? 2.0f : 32.0f);
				Position += FMath::Lerp(Crown, ShotOffset, Compress) + Forward * (FMath::Min(T, .075f) * 6000.0f);
				Rotation = Facing * FQuat(FVector::UpVector, (Group - 2) * .22f * (1.0f - Compress));
				Rotation *= FQuat(FVector::ForwardVector, Lane * .38f * (1.0f - Compress));
				const float Size = Lane == 0 ? 1.25f : .73f;
				Scale = FVector(Size, Size * (Lane == 0 ? .70f : .60f), 1.0f) * Form * (1.0f - Compress * .20f);
				Live *= Open * (bReleased ? 1.0f - FMath::SmoothStep(.022f, .075f, T) : Lane == 0 ? .95f : .62f);
			}
			else
			{
				const int32 I = Index - 15;
				const float Phase = I * 2.399963f;
				Position += (Right * FMath::Cos(Phase) + FVector::UpVector * FMath::Sin(Phase)) * (20.0f + T * 310.0f);
				Position += Forward * (T * 125.0f) + FVector::UpVector * (T * 140.0f);
				Rotation = Facing * FQuat(FVector::UpVector, Phase + T * 3.5f);
				Scale = FVector(.55f, .40f, 1.0f) * Form;
				Live *= bReleased ? 1.0f - FMath::SmoothStep(.09f, .30f, T) : 0.0f;
			}
		}
		else
		{
			if (Index < 4)
			{
				const float Side = Index % 2 == 0 ? -1.0f : 1.0f;
				const float Delay = Index * .045f;
				const float PieceAge = bReleased ? FMath::Max(0.0f, T - Delay) : 0.0f;
				const float Unfold = FMath::SmoothStep(Index * .038f, .16f + Index * .030f, Age);
				Position += Right * Side * (42.0f + Unfold * 35.0f - Compress * 52.0f + PieceAge * 180.0f);
				Position += FVector::UpVector * ((Index / 2 == 0 ? 1.0f : -1.0f) * 23.0f) + Forward * (15.0f + Index * 8.0f + PieceAge * 310.0f);
				Rotation *= FQuat(FVector::UpVector, Side * (.48f + Unfold * .40f - Compress * .28f + PieceAge * 4.0f));
				Scale = FVector(2.90f, 2.10f, 1.0f) * Form * (.55f + Unfold * .45f) * (1.0f - Compress * .32f + PieceAge * 2.0f);
				Live *= bReleased ? (T >= Delay ? 1.0f - FMath::SmoothStep(.04f, .14f, PieceAge) : .28f) : Unfold;
				Place(Index, Position, Rotation, Scale, Live, bReleased ? PieceAge : 100.0f);
				continue;
			}
			const int32 I = Index - 9;
			const float Phase = I * 2.399963f;
			const FVector Radial = Right * FMath::Cos(Phase) + FVector::UpVector * FMath::Sin(Phase);
			Position += Radial * (25.0f + T * (Index < 15 ? 390.0f : 510.0f)) + Forward * (22.0f + T * 230.0f);
			Rotation = Facing * FQuat(FVector::UpVector, Phase + T * 4.0f);
			Scale = FVector(Index < 15 ? 1.22f : .80f, Index < 15 ? .90f : .36f, 1.0f) * Form;
			Live *= bReleased ? 1.0f - FMath::SmoothStep(.08f, .26f, T) : 0.0f;
		}
		Place(Index, Position, Rotation, Scale, Live, Since);
	}
}

void ASparrowArsenalStudyFX::DrawSharpRevision(float Since, float Fade)
{
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Forward).GetSafeNormal();
	const bool bReleased = Pulses > 0;
	const FVector Base = Origin + (bReleased ? FVector::ZeroVector : Forward * 20.0f);
	FVector Normal = FVector::UpVector;
	if (APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(this, 0)) { Normal = Camera->GetCameraLocation() - Base; }
	const FQuat Front = FRotationMatrix::MakeFromXZ(Right, Forward).ToQuat();
	const FQuat Facing = FRotationMatrix::MakeFromXZ(Forward, Normal).ToQuat();
	const float Unfold = FMath::SmoothStep(.025f, .145f, Age);
	const float Squeeze = FMath::SmoothStep(.22f, Preparation - .008f, Age);
	const float T = bReleased ? FMath::Max(0.0f, Since) : 0.0f;
	const float Form = bAscended ? 1.08f : 1.0f;
	for (int32 Index = 0; Index < Surfaces.Num(); ++Index)
	{
		FVector Position = Base;
		FQuat Rotation = Front;
		FVector Scale(1.0f);
		float Live = Fade;
		float LocalSince = Since;
		if (Index < 3)
		{
			if (Style == 9)
			{
				// 서로 다른 깊이의 넓은 압력막을 감아 압축한다. 방출에는 별도 면을 사용한다.
				const float Phase = Index * 1.74f + Age * (Index == 1 ? -7.5f : 6.5f);
				Position += Forward * (25.0f + Index * 27.0f);
				Rotation = Index == 2 ? Facing : Front;
				Rotation *= FQuat(FVector::UpVector, Phase);
				if (Index < 2) { Rotation *= FQuat(FVector::ForwardVector, (Index == 0 ? .20f : -.32f)); }
				const float Size = (Index == 0 ? 4.65f : Index == 1 ? 3.80f : 3.45f) * (.38f + Unfold * .62f) * (1.0f - Squeeze * .35f);
				Scale = FVector(Size, Size * (Index == 2 ? .80f : 1.0f), 1.0f) * Form;
				Live *= Unfold * (Index == 0 ? .85f : Index == 1 ? .55f : .35f) *
					(bReleased ? 1.0f - FMath::SmoothStep(.004f, .032f, T) : 1.0f);
			}
			else
			{
				const float Side = Index == 0 ? -1.0f : 1.0f;
				Position += Forward * (38.0f + Index * 22.0f);
				Position += FVector::UpVector * Side * (Index == 2 ? 0.0f : 48.0f * (1.0f - Squeeze));
				Rotation = Index == 2 ? Facing : Front;
				Rotation *= FQuat(FVector::UpVector, Index == 2 ? .35f : Side * (.55f + Squeeze * .60f));
				if (Index < 2) { Rotation *= FQuat(FVector::ForwardVector, Side * .25f); }
				Scale = FVector(Index == 2 ? 2.65f : 3.95f, Index == 2 ? 2.15f : 3.15f, 1.0f) * Form;
				Scale *= (.30f + Unfold * .70f) * (1.0f - Squeeze * .38f);
				Live *= Unfold * (Index == 2 ? .30f : .70f) * (bReleased ? 1.0f - FMath::SmoothStep(.0f, .026f, T) : 1.0f);
			}
		}
		else if (Index < 6)
		{
			const int32 Layer = Index - 3;
			Position += Forward * (36.0f + Layer * 14.0f + T * 420.0f);
			Rotation = Layer == 0 ? Front : Facing * FQuat(FVector::UpVector, Layer == 1 ? .65f : -.65f);
			const float Size = (Style == 9 ? 1.60f : 1.75f) * (1.0f - Squeeze * .35f + T * 4.2f);
			Scale = FVector(Size, Size * .85f, 1.0f) * Form;
			Live *= Unfold * (Layer == 0 ? .70f : .28f) * (bReleased ? 1.0f - FMath::SmoothStep(.018f, .075f, T) : .20f + Squeeze * .65f);
		}
		else if (Index < 11)
		{
			// 실탄의 다섯 발사구와 속도를 따르는 짧은 광면. 판정은 생성하지 않는다.
			const float Phase = HALF_PI + (Index - 6) * (2.0f * PI / 5.0f);
			Position += (Right * FMath::Cos(Phase) + FVector::UpVector * FMath::Sin(Phase)) * 45.0f;
			Position += Forward * (FMath::Min(T, .072f) * 6000.0f - 15.0f);
			Rotation = Facing;
			Scale = FVector(1.38f, .66f, 1.0f) * Form;
			Live *= bReleased ? 1.0f - FMath::SmoothStep(.022f, .072f, T) : 0.0f;
		}
		else if (Index < 17)
		{
			const int32 I = Index - 11;
			const bool bExtraLayer = I >= 3;
			const float Delay = Style == 9 ? (I % 3) * .018f : (I % 3) * .025f;
			const float PieceAge = FMath::Max(0.0f, T - Delay);
			if (Style == 9)
			{
				// 압축막을 재확대하지 않고, 앞쪽으로 넘겨지는 짧은 나선 파열막을 생성한다.
				const float Phase = I * 2.094395f - PieceAge * 8.5f;
				Position += Forward * (55.0f + I * 14.0f + PieceAge * 700.0f);
				Rotation = I == 2 ? Facing : Front;
				Rotation *= FQuat(FVector::UpVector, Phase);
				Scale = FVector(3.55f, 3.15f, 1.0f) * Form * (.62f + FMath::SmoothStep(0.0f, .070f, PieceAge) * .54f);
			}
			else
			{
				const float Side = I % 3 == 0 ? -1.0f : 1.0f;
				Position += Forward * (58.0f + I * 13.0f + PieceAge * 480.0f);
				Position += FVector::UpVector * Side * (18.0f + PieceAge * 160.0f);
				Rotation = I % 3 == 2 ? Facing : Front;
				Rotation *= FQuat(FVector::UpVector, I % 3 == 2 ? .18f : Side * (.26f + PieceAge * 1.7f));
				if (I % 3 < 2) { Rotation *= FQuat(FVector::ForwardVector, Side * .28f); }
				Scale = FVector(4.55f, 3.55f, 1.0f) * Form * (.58f + FMath::SmoothStep(0.0f, .040f, PieceAge) * .58f);
			}
			if (bExtraLayer) { Scale *= .72f; Position += Forward * 35.0f; }
			Live *= bReleased && T >= Delay && (!bExtraLayer || bAscended) ?
				(1.0f - FMath::SmoothStep(.045f, .125f, PieceAge)) * (bExtraLayer ? .28f : I == 2 ? .38f : .74f) : 0.0f;
			LocalSince = bReleased && T >= Delay ? PieceAge : 100.0f;
		}
		else
		{
			const int32 I = Index - 17;
			const float Phase = I * 2.399963f + .3f;
			const FVector Radial = Right * FMath::Cos(Phase) + FVector::UpVector * FMath::Sin(Phase);
			Position += Radial * (bReleased ? 35.0f + T * (480.0f + (I % 3) * 90.0f) : 125.0f * (1.0f - Squeeze));
			Position += Forward * (45.0f + T * 480.0f);
			Rotation = FRotationMatrix::MakeFromXZ((Radial + Forward * .45f).GetSafeNormal(), Normal).ToQuat();
			Scale = FVector(.65f, .55f, 1.0f) * Form;
			Live *= bReleased ? 1.0f - FMath::SmoothStep(.055f, .22f, T) : Unfold * (1.0f - Squeeze) * .22f;
		}
		Place(Index, Position, Rotation, Scale, Live, LocalSince);
	}
}
