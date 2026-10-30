#include "SparrowAscension.h"

#include "Animation/AnimInstance.h"
#include "Animation/AnimSequence.h"
#include "Components/SceneComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/OverlapResult.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "Materials/Material.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "Particles/ParticleEmitter.h"
#include "Particles/ParticleLODLevel.h"
#include "Particles/ParticleModuleRequired.h"
#include "SparrowSkillComponent.h"
#include "SparrowCharacter.h"
#include "KwangTrainingDummy.h"
#include "SparrowShotWave.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"
#include "Distributions/DistributionFloatConstant.h"
#include "Distributions/DistributionVectorConstant.h"
#include "Particles/Color/ParticleModuleColor.h"

namespace
{
	constexpr float WingUnfoldRate = 0.8f * 1.75f;
	constexpr float WingEntrySpeed = 1.75f;
	constexpr float WingScale = 0.8f;
	constexpr float WingVisualExitSeconds = .55f;
	constexpr float WingEntryRevealSeconds = 1.16f;
	constexpr float WingAttackReturnSeconds = .42f;
	constexpr float WingAttackReleasePose = 8.0f / 30.0f;
	constexpr float WingAttackReturnPose = 1.0f;
	constexpr float SentryLifetime = 8.0f;
	constexpr float SentryDamageScale = 0.30f;

	UParticleSystem* FilterWingEntryEffect(const TCHAR* Path, FName RuntimeName, const TArray<FName>& Names)
	{
		UParticleSystem* Source = LoadObject<UParticleSystem>(nullptr, Path);
		if (!Source) { return nullptr; }
		UParticleSystem* Runtime = DuplicateObject<UParticleSystem>(Source, GetTransientPackage(),
			MakeUniqueObjectName(GetTransientPackage(), UParticleSystem::StaticClass(), RuntimeName));
		if (!Runtime) { return nullptr; }
		Runtime->SetFlags(RF_Transient);
		Runtime->ClearFlags(RF_Public | RF_Standalone);
		Runtime->Emitters.RemoveAll([&Names](UParticleEmitter* Emitter)
		{
			return !Emitter || !Names.Contains(Emitter->GetEmitterName());
		});
		if (Runtime->Emitters.IsEmpty()) { return nullptr; }
		for (UParticleEmitter* Emitter : Runtime->Emitters)
		{
			if (!Emitter->IsIn(Runtime)) { return nullptr; }
			for (UParticleLODLevel* LOD : Emitter->LODLevels)
			{
				if (!LOD || !LOD->RequiredModule || !LOD->RequiredModule->IsIn(Runtime)) { return nullptr; }
				LOD->RequiredModule->bKillOnDeactivate = false;
			}
			Emitter->UpdateModuleLists();
		}
		return Runtime;
	}

	UParticleSystem* GetWingEntryShards()
	{
		static TWeakObjectPtr<UParticleSystem> Cached;
		if (!Cached.IsValid())
		{
			Cached = FilterWingEntryEffect(
				TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Ultimate/FX/P_Sparrow_Burst.P_Sparrow_Burst"),
				TEXT("P_SparrowWingEntryShards"), {TEXT("Flames2")});
		}
		return Cached.Get();
	}

	UParticleSystem* GetWingEntrySparks()
	{
		static TWeakObjectPtr<UParticleSystem> Cached;
		if (!Cached.IsValid())
		{
			Cached = FilterWingEntryEffect(
				TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Ultimate/FX/P_Sparrow_UltHit.P_Sparrow_UltHit"),
				TEXT("P_SparrowWingEntrySparks"), {TEXT("Sparks"), TEXT("SparkTrailHeads")});
		}
		return Cached.Get();
	}

	UParticleSystem* GetWingEntryIgnition()
	{
		static TWeakObjectPtr<UParticleSystem> Cached;
		if (!Cached.IsValid())
		{
			Cached = FilterWingEntryEffect(
				TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Ultimate/FX/P_Sparrow_UltHit.P_Sparrow_UltHit"),
				TEXT("P_SparrowWingEntryIgnition"), {TEXT("Main Flames"), TEXT("Sparks")});
		}
		return Cached.Get();
	}

	UParticleSystem* FilterAuthoredEffect(const TCHAR* Path, FName RuntimeName, const TArray<int32>& EmitterIndices)
	{
		UParticleSystem* Source = LoadObject<UParticleSystem>(nullptr, Path);
		if (!Source) { return nullptr; }
		UParticleSystem* Runtime = DuplicateObject<UParticleSystem>(Source, GetTransientPackage(),
			MakeUniqueObjectName(GetTransientPackage(), UParticleSystem::StaticClass(), RuntimeName));
		if (!Runtime) { return nullptr; }
		Runtime->SetFlags(RF_Transient);
		Runtime->ClearFlags(RF_Public | RF_Standalone);
		for (int32 Index = Runtime->Emitters.Num() - 1; Index >= 0; --Index)
		{
			if (!EmitterIndices.Contains(Index)) { Runtime->Emitters.RemoveAt(Index); }
		}
		if (Runtime->Emitters.Num() != EmitterIndices.Num()) { return nullptr; }
		for (UParticleEmitter* Emitter : Runtime->Emitters)
		{
			if (!Emitter || !Emitter->IsIn(Runtime)) { return nullptr; }
			for (UParticleLODLevel* LOD : Emitter->LODLevels)
			{
				if (!LOD || !LOD->RequiredModule || !LOD->RequiredModule->IsIn(Runtime)) { return nullptr; }
				LOD->RequiredModule->bKillOnDeactivate = false;
			}
			// 복제본의 transient spawn/update 목록만 다시 구성한다. 원본과 패키지는 저장하지 않는다.
			Emitter->UpdateModuleLists();
		}
		return Runtime;
	}

	UParticleSystem* GetFormAccentTemplate()
	{
		static TWeakObjectPtr<UParticleSystem> Cached;
		if (!Cached.IsValid())
		{
			// 확인한 원본 #0 plasma와 #7 flame shard만 쓴다. 대형 충격파/광원/활 메시를 제외한다.
			Cached = FilterAuthoredEffect(
				TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Ultimate/FX/P_Sparrow_Burst.P_Sparrow_Burst"),
				TEXT("P_SparrowAscensionPlasma_Runtime"), {0, 7});
		}
		return Cached.Get();
	}

	UParticleSystem* GetCondensedCoreTemplate()
	{
		static TWeakObjectPtr<UParticleSystem> Cached;
		if (!Cached.IsValid())
		{
			// BowFlames와 뼈를 요구하는 FresnelDecals 대신 .75초짜리 local-space Airglow 질감만 사용한다.
			Cached = FilterAuthoredEffect(
				TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Ultimate/FX/P_SparrowBuff.P_SparrowBuff"),
				TEXT("P_SparrowCondensedAirglow_Runtime"), {3});
			if (Cached.IsValid())
			{
				for (UParticleEmitter* Emitter : Cached->Emitters)
				{
					for (UParticleLODLevel* LOD : Emitter->LODLevels)
					{
						if (!LOD) { continue; }
						// 느려진 A의 전체 비행 동안 유지하고, 소유 화살의 종료와 함께 정리한다.
						LOD->RequiredModule->EmitterLoops = 0;
						for (UParticleModule* Module : LOD->Modules)
						{
							if (UParticleModuleColor* Color = Cast<UParticleModuleColor>(Module))
							{
								UDistributionVectorConstant* Tint = NewObject<UDistributionVectorConstant>(Color, NAME_None, RF_Transient);
								Tint->Constant = FVector(3.0f, 2.0f, 0.65f);
								Tint->bCanBeBaked = false;
								Color->StartColor = FRawDistributionVector();
								Color->StartColor.Distribution = Tint;
								UDistributionFloatConstant* Alpha = NewObject<UDistributionFloatConstant>(Color, NAME_None, RF_Transient);
								Alpha->Constant = 0.55f;
								Alpha->bCanBeBaked = false;
								Color->StartAlpha = FRawDistributionFloat();
								Color->StartAlpha.Distribution = Alpha;
							}
						}
					}
					Emitter->UpdateModuleLists();
				}
			}
		}
		return Cached.Get();
	}

	UParticleSystem* GetGearImpactTemplate()
	{
		static TWeakObjectPtr<UParticleSystem> Cached;
		if (!Cached.IsValid())
		{
			// 원본의 불꽃 결/불티/잔여만 보존하고 순간 광원과 큰 흰 flare는 제외한다.
			Cached = FilterAuthoredEffect(
				TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Ultimate/FX/P_Sparrow_UltHit.P_Sparrow_UltHit"),
				TEXT("P_SparrowFeatherImpact_Runtime"), {2, 4, 5});
		}
		return Cached.Get();
	}

	void ConfigureVisual(UPrimitiveComponent* Part)
	{
		Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Part->SetGenerateOverlapEvents(false);
		Part->SetCanEverAffectNavigation(false);
		Part->SetCastShadow(false);
		Part->SetReceivesDecals(false);
		Part->SetVisibility(false);
	}

	void SpawnAuthoredAccent(AActor* Owner, UParticleSystem* Template, const FVector& Location,
		const FRotator& Rotation, const FVector& Scale, float EmissionSeconds, float Lifetime)
	{
		if (!IsValid(Owner) || !Owner->GetWorld() || !Template) { return; }
		const FTransform Transform(Rotation, Location, Scale);
		ASparrowAscensionAccent* Accent = Owner->GetWorld()->SpawnActorDeferred<ASparrowAscensionAccent>(
			ASparrowAscensionAccent::StaticClass(), Transform, Owner, Cast<APawn>(Owner), ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
		if (!Accent) { return; }
		Accent->Initialize(Template, EmissionSeconds, Lifetime);
		Accent->FinishSpawning(Transform);
	}

	void SpawnFormAccent(AActor* Owner, const FVector& Location, float Scale, bool bEntering)
	{
		UParticleSystem* Template = GetFormAccentTemplate();
		SpawnAuthoredAccent(Owner, Template, Location, FRotator(90.0f, Owner ? Owner->GetActorRotation().Yaw : 0.0f, 0.0f),
			FVector(Scale, Scale, Scale * 1.5f), bEntering ? 0.12f : 0.06f, bEntering ? 0.65f : 0.45f);
	}
}

ASparrowAscensionAccent::ASparrowAscensionAccent()
{
	PrimaryActorTick.bCanEverTick = true;
	SetActorEnableCollision(false);
	SetCanBeDamaged(false);
	Particle = CreateDefaultSubobject<UParticleSystemComponent>(TEXT("AuthoredAccent"));
	SetRootComponent(Particle);
	Particle->bAutoActivate = false;
	Particle->bAutoDestroy = false;
	Particle->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Particle->SetGenerateOverlapEvents(false);
	Particle->SetCanEverAffectNavigation(false);
	Particle->SetCastShadow(false);
	Particle->bOverrideLODMethod = true;
	Particle->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
	Particle->ComponentTags.Add(TEXT("SparrowSkillFX"));
	Tags.Add(TEXT("SparrowAscensionAccent"));
	Tags.Add(TEXT("SparrowSkillFX"));
}

void ASparrowAscensionAccent::Initialize(UParticleSystem* Template, float EmissionSeconds, float Lifetime)
{
	Particle->SetTemplate(Template);
	EmissionDuration = FMath::Clamp(EmissionSeconds, 0.02f, 0.25f);
	Particle->CustomTimeDilation = Lifetime < 0.5f ? 2.1f : 1.5f;
	SetLifeSpan(FMath::Clamp(Lifetime, EmissionDuration, 1.0f));
}

void ASparrowAscensionAccent::BeginPlay()
{
	Super::BeginPlay();
	if (!IsValid(GetOwner()) || !Particle->Template) { Destroy(); return; }
	Particle->SetLODLevel(0);
	Particle->ActivateSystem(true);
	Particle->SetLODLevel(0);
}

void ASparrowAscensionAccent::InitializeStudyPulse(UParticleSystem* Template, float Lifetime, float PlaybackSpeed)
{
	// Preserve the selected study's exact playback/lifetime without changing
	// existing accent callers or saving a modified Paragon particle template.
	Particle->SetTemplate(Template);
	EmissionDuration = FMath::Clamp(Lifetime, .02f, 1.0f);
	Particle->CustomTimeDilation = FMath::Max(PlaybackSpeed, .01f);
	SetLifeSpan(EmissionDuration);
}

void ASparrowAscensionAccent::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!IsValid(GetOwner())) { Destroy(); return; }
	Age += FMath::Max(DeltaSeconds, 0.0f);
	if (!bEmissionStopped && Age >= EmissionDuration)
	{
		bEmissionStopped = true;
		Particle->DeactivateSystem();
	}
}

ASparrowGearArrow::ASparrowGearArrow()
{
	CollisionRadius = 70.0f;
	Tags.Add(TEXT("SparrowGearArrow"));
	Rotor = CreateDefaultSubobject<USceneComponent>(TEXT("SawRotor"));
	Rotor->SetupAttachment(SceneRoot);
	Rotor->SetRelativeLocation(FVector(40.0f, 0.0f, 0.0f));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Plane(TEXT("/Engine/BasicShapes/Plane.Plane"));
	// 중심을 비운 깃털 고리 두 겹이 기존 비행 축 주위를 회전한다. 충돌은 화살 본체만 처리한다.
	for (int32 Index = 0; Index < 2; ++Index)
	{
		UStaticMeshComponent* Ring = CreateDefaultSubobject<UStaticMeshComponent>(*FString::Printf(TEXT("FeatherRing%d"), Index));
		ConfigureVisual(Ring);
		Ring->SetupAttachment(Rotor);
		Ring->SetStaticMesh(Plane.Object);
		Ring->SetRelativeLocation(FVector(Index == 0 ? 0.0f : -24.0f, 0.0f, 0.0f));
		Ring->SetRelativeRotation(FRotator(90.0f, 0.0f, 0.0f));
		const float Diameter = Index == 0 ? 1.6f : 1.08f;
		Ring->SetRelativeScale3D(FVector(Diameter, Diameter, 1.0f));
		FeatherRings.Add(Ring);
	}
	ArrowMesh->SetRelativeScale3D(FVector(1.35f, 1.35f, 1.1475f));
	ArrowMesh->SetVisibility(false);
	CondensedCore = CreateDefaultSubobject<UParticleSystemComponent>(TEXT("CondensedCore"));
	CondensedCore->SetupAttachment(SceneRoot);
	CondensedCore->bAutoActivate = false;
	CondensedCore->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	CondensedCore->SetGenerateOverlapEvents(false);
	CondensedCore->SetCanEverAffectNavigation(false);
	CondensedCore->SetCastShadow(false);
	CondensedCore->SetRelativeLocation(FVector(35.0f, 0.0f, 0.0f));
	CondensedCore->SetRelativeScale3D(FVector(0.24f));
	CondensedCore->bOverrideLODMethod = true;
	CondensedCore->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
	CondensedCore->ComponentTags.Add(TEXT("SparrowSkillFX"));
}

void ASparrowGearArrow::BeginPlay()
{
	Super::BeginPlay();
	const USparrowSkillComponent* OwnerSkills = GetOwner() ? GetOwner()->FindComponentByClass<USparrowSkillComponent>() : nullptr;
	bAscendedGear = OwnerSkills && OwnerSkills->GetAscensionRemaining() > 0.0f;
	if (bAscendedGear) { Tags.Add(TEXT("SparrowAscendedGear")); }
	UMaterialInterface* Gold = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowAscensionGold.M_SparrowAscensionGold"));
	UMaterialInterface* Feather = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowGearFeather.M_SparrowGearFeather"));
	if (!Gold || !Feather) { Destroy(); return; }
	for (int32 Index = 0; Index < FeatherRings.Num(); ++Index)
	{
		UStaticMeshComponent* Ring = FeatherRings[Index];
		UMaterialInstanceDynamic* Material = Ring->CreateDynamicMaterialInstance(0, Feather);
		if (!Material) { Destroy(); return; }
		Material->SetScalarParameterValue(TEXT("Envelope"),
			bAscendedGear ? (Index == 0 ? 1.25f : 0.62f) : (Index == 0 ? 1.05f : 0.46f));
		FeatherMaterials.Add(Material);
		Ring->SetVisibility(true);
	}
	for (int32 Slot = 0; Slot < FMath::Max(1, ArrowMesh->GetNumMaterials()); ++Slot) { ArrowMesh->SetMaterial(Slot, Gold); }
	ArrowMesh->SetVisibility(true);
	// 느린 투사체의 뒤를 긴 궁극기 꼬리가 덮지 않게 실제 궤적만 짧고 좁게 압축한다.
	TrailParticle->SetRelativeScale3D(FVector(0.408f, 0.58f, 0.58f));
	if (UParticleSystem* Template = GetCondensedCoreTemplate())
	{
		CondensedCore->SetTemplate(Template);
		CondensedCore->SetLODLevel(0);
		CondensedCore->ActivateSystem(true);
		CondensedCore->SetLODLevel(0);
	}
	InitializeSawVortex();
}

void ASparrowGearArrow::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (IsActorBeingDestroyed()) { return; }
	SpinDegrees = FMath::Fmod(SpinDegrees + 540.0f * FMath::Max(DeltaSeconds, 0.0f), 360.0f);
	Rotor->SetRelativeRotation(FRotator(0.0f, 0.0f, SpinDegrees));
	ImpactPulseAge += FMath::Max(DeltaSeconds, 0.0f);
	const float Pulse = FMath::Square(FMath::Clamp(1.0f - ImpactPulseAge / 0.14f, 0.0f, 1.0f));
	UpdateSawVortex(DeltaSeconds, Pulse);
	for (int32 Index = 0; Index < FeatherMaterials.Num(); ++Index)
	{
		const float BaseEnvelope = bAscendedGear ? (Index == 0 ? 1.25f : 0.62f) : (Index == 0 ? 1.05f : 0.46f);
		FeatherMaterials[Index]->SetScalarParameterValue(TEXT("Envelope"),
			BaseEnvelope + Pulse * (Index == 0 ? 0.55f : 0.16f));
	}
	FlightCrackleAge += FMath::Max(DeltaSeconds, 0.0f);
	const float CrackleInterval = bAscendedGear ? 0.10f : 0.16f;
	if (!Tags.Contains(TEXT("SparrowSunArrow")) && !Tags.Contains(TEXT("SparrowSolarRotor")) &&
		!Tags.Contains(TEXT("SparrowAnnularCraftArrow")) && !Tags.Contains(TEXT("SparrowLegacySpiralA4")) && FlightCrackleAge >= CrackleInterval)
	{
		FlightCrackleAge = FMath::Fmod(FlightCrackleAge, CrackleInterval);
		bCrackleRight = !bCrackleRight;
		const FVector Point = GetActorLocation() - GetFlightDirection() * 12.0f +
			GetActorRightVector() * (bCrackleRight ? 23.0f : -23.0f) + GetActorUpVector() * 8.0f;
		SparrowPresentation::SpawnGearFlightCrackle(this, Point, GetFlightDirection());
	}
}

void ASparrowGearArrow::OnArrowImpactVisual(const FHitResult& Hit, bool bWorld)
{
	ImpactPulseAge = 0.0f;
	if (Tags.Contains(TEXT("SparrowLegacySpiralA4")))
	{
		SpawnLegacySpiralImpact(Hit, bWorld);
		UParticleSystem* Template = GetGearImpactTemplate();
		SpawnAuthoredAccent(GetOwner(), Template, Hit.ImpactPoint, GetFlightDirection().Rotation(),
			FVector(bWorld ? .50f : .75f), .06f, .72f);
		return;
	}
	SparrowPresentation::SpawnTransferredHitFlash(GetOwner(), Hit.ImpactPoint, GetFlightDirection(), bWorld);
	// 좋아한 세 번의 파열은 유지하고, 접촉면 가장자리 두 점만 더해 밝은 핵 밖에서도 충돌이 읽히게 한다.
	if (!bWorld)
	{
		for (float Side : {-1.0f, 1.0f})
		{
			SparrowPresentation::SpawnGearFlightCrackle(this,
				Hit.ImpactPoint + GetActorRightVector() * Side * 30.0f + GetActorUpVector() * 10.0f, GetFlightDirection());
		}
	}
	UParticleSystem* Template = GetGearImpactTemplate();
	// 화살이 관통하거나 사라져도 짧은 파열은 마무리하되, 본체 종료 때 함께 정리한다.
	SpawnAuthoredAccent(GetOwner(), Template, Hit.ImpactPoint, GetFlightDirection().Rotation(),
		FVector(bWorld ? 0.50f : 0.75f), 0.06f, 0.72f);
}

void ASparrowGearArrow::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	UE_LOG(LogTemp, Display, TEXT("SPARROW_ASCENSION gear_end travelled=%.1f hits=%d location=%s reason=%d"),
		GetDistanceTravelled(), GetHitCount(), *GetActorLocation().ToCompactString(), static_cast<int32>(EndPlayReason));
	Super::EndPlay(EndPlayReason);
}

UParticleSystem* ASparrowAscensionWings::GetEntryRiseTemplate()
{
	static TWeakObjectPtr<UParticleSystem> Cached;
	if (!Cached.IsValid())
	{
		Cached = FilterWingEntryEffect(
			TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Ultimate/FX/P_Sparrow_UltHit.P_Sparrow_UltHit"),
			TEXT("P_SparrowWingEntryRise"), {TEXT("Main Flames"), TEXT("Wisps")});
	}
	return Cached.Get();
}

ASparrowAscensionWings::ASparrowAscensionWings()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickGroup = TG_PostPhysics;
	SetActorEnableCollision(false);
	SetCanBeDamaged(false);
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	Wings = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("SerathWings"));
	ConfigureVisual(Wings);
	Wings->SetupAttachment(RootComponent);
	Wings->bDisableClothSimulation = true;
	Wings->bAllowClothActors = false;
	Wings->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	Wings->SetAllowAnimCurveEvaluation(false);
	Tags.Add(TEXT("SparrowAscensionWings"));
	Tags.Add(TEXT("SparrowSkillFX"));
}

bool ASparrowAscensionWings::Initialize(ACharacter* Character, float Lifetime)
{
	if (!IsValid(Character) || !Character->GetMesh() || !GetWorld()) { return false; }
	USkeletalMesh* Source = LoadObject<USkeletalMesh>(nullptr,
		TEXT("/Game/ParagonSerath/Characters/Heroes/Serath/Meshes/Serath.Serath"));
	UnfoldAnimation = LoadObject<UAnimSequence>(nullptr,
		TEXT("/Game/ParagonSerath/Characters/Heroes/Serath/Animations/Wings_Unfold.Wings_Unfold"));
	FoldAnimation = LoadObject<UAnimSequence>(nullptr,
		TEXT("/Game/ParagonSerath/Characters/Heroes/Serath/Animations/Wings_Fold.Wings_Fold"));
	AttackAnimation = LoadObject<UAnimSequence>(nullptr,
		TEXT("/Game/ParagonSerath/Characters/Heroes/Serath/Animations/E_Ability_Wing_Flap_Holy.E_Ability_Wing_Flap_Holy"));
	IdleAnimation = LoadObject<UAnimSequence>(nullptr,
		TEXT("/Game/ParagonSerath/Characters/Heroes/Serath/Animations/Idle_Pose_Wings.Idle_Pose_Wings"));
	if (!Source || !UnfoldAnimation || !FoldAnimation || !AttackAnimation || !IdleAnimation) { return false; }
	for (UAnimSequence* Animation : {UnfoldAnimation.Get(), FoldAnimation.Get(), AttackAnimation.Get(), IdleAnimation.Get()})
	{
		if (Source->GetSkeleton() != Animation->GetSkeleton() || Animation->IsValidAdditive()) { return false; }
	}
	SourceMesh = Character->GetMesh();
	AddTickPrerequisiteComponent(SourceMesh.Get());
	UMaterialInterface* BodySource = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowArchonSilhouette.M_SparrowArchonSilhouette"));
	if (!BodySource)
	{
		// 전용 재질을 저작하기 전에도 기존 변신/복구 경로는 유지한다. 분신의 Echo 재질은 변경하지 않는다.
		BodySource = LoadObject<UMaterialInterface>(nullptr,
			TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowAscensionEcho.M_SparrowAscensionEcho"));
		UE_LOG(LogTemp, Warning, TEXT("SPARROW_ASCENSION silhouette material unavailable; using existing body fallback"));
	}
	for (const FName SlotName : {FName(TEXT("M16_CloakStraps")), FName(TEXT("M08_Cloak")), FName(TEXT("M14_CloakHood"))})
	{
		const int32 MaterialId = SourceMesh->GetMaterialIndex(SlotName);
		if (MaterialId == INDEX_NONE) { return false; }
		HiddenClothMaterialIds.Add(MaterialId);
	}
	const int32 Splines = Source->GetMaterials().IndexOfByPredicate([](const FSkeletalMaterial& Material)
	{
		return Material.MaterialSlotName == TEXT("M12_WingSplines");
	});
	const int32 Membrane = Source->GetMaterials().IndexOfByPredicate([](const FSkeletalMaterial& Material)
	{
		return Material.MaterialSlotName == TEXT("M13_WingMembrane");
	});
	if (!BodySource || Splines == INDEX_NONE || Membrane == INDEX_NONE ||
		!SourceMesh->DoesSocketExist(TEXT("spine_03"))) { return false; }
	// 비날개 섹션은 가벼운 override로 렌더링 의존성을 없애고 처음부터 숨긴다. 원본 자산은 건드리지 않는다.
	UMaterialInterface* HiddenMaterial = UMaterial::GetDefaultMaterial(MD_Surface);
	for (int32 Slot = 0; Slot < Source->GetMaterials().Num(); ++Slot) { Wings->SetMaterial(Slot, HiddenMaterial); }
	Wings->SetSkeletalMeshAsset(Source);
	for (int32 Lod = 0; Lod < Wings->GetNumLODs(); ++Lod)
	{
		for (int32 Slot = 0; Slot < Source->GetMaterials().Num(); ++Slot)
		{
			Wings->ShowMaterialSection(Slot, INDEX_NONE, Slot == Splines || Slot == Membrane, Lod);
		}
	}
	Wings->SetForcedLOD(1);
	UMaterialInterface* FlameSource = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowSerathGoldFlame.M_SparrowSerathGoldFlame"));
	UMaterialInterface* SplineFlameSource = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowSerathSplineFlame.M_SparrowSerathSplineFlame"));
	if (!FlameSource || !SplineFlameSource) { return false; }
	for (const int32 Slot : {Splines, Membrane})
	{
		// 두 원본 재질의 형상/WPO는 보존하되, 실제 막과 spline 자체를 같은 불꽃장에서 침식한다.
		UMaterialInterface* SlotSource = Slot == Membrane ? FlameSource : SplineFlameSource;
		UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(SlotSource, this);
		if (!Material) { return false; }
		Material->SetScalarParameterValue(TEXT("Holy=True"), 1.0f);
		Material->SetScalarParameterValue(TEXT("WingAlpha"), 0.0f);
		if (Slot == Splines)
		{
			Material->SetScalarParameterValue(TEXT("HDRTintMult"), 1.0f);
			Material->SetScalarParameterValue(TEXT("GoldBoost"), 2.0f);
			Material->SetVectorParameterValue(TEXT("Holy1"), FLinearColor(0.9f, 0.65f, 0.18f));
			Material->SetVectorParameterValue(TEXT("Holy2"), FLinearColor(0.60f, 0.36f, 0.05f));
			Material->SetVectorParameterValue(TEXT("Holy3"), FLinearColor(0.14f, 0.08f, 0.008f));
		}
		else
		{
			Material->SetVectorParameterValue(TEXT("HolyColor"), FLinearColor(0.8f, 0.5f, 0.1f, 0.0f));
			Material->SetVectorParameterValue(TEXT("HolyColor1"), FLinearColor(0.16f, 0.08f, 0.01f, 0.0f));
			Material->SetVectorParameterValue(TEXT("HolyWeb1"), FLinearColor(0.8f, 0.65f, 0.18f));
			Material->SetVectorParameterValue(TEXT("HolyWeb2"), FLinearColor(0.1f, 0.08f, 0.01f));
			// 원본 막의 흐르는 결을 느리고 넓게 풀어 고정된 금속판처럼 보이지 않게 한다.
			Material->SetScalarParameterValue(TEXT("PanSpeedHoly"), 0.19f);
			Material->SetScalarParameterValue(TEXT("UVDistortHoly"), 0.025f);
		}
		Wings->SetMaterial(Slot, Material);
		WingMaterials.Add(Material);
	}
	SetWingPose(UnfoldAnimation, 0.0f);
	if (!Wings->DoesSocketExist(TEXT("spine_03"))) { return false; }
	AttachToComponent(SourceMesh.Get(), FAttachmentTransformRules::SnapToTargetNotIncludingScale, TEXT("spine_03"));
	AlignWingRoot();
	Wings->SuspendClothingSimulation();
	Wings->SetBoundsScale(1.5f);
	// 사용자가 선택한 기존 Serath 날개 형상과 펼침/유지 포즈를 다시 표시한다.
	Wings->SetVisibility(true);
	for (int32 Bone = 0; Bone < Wings->GetNumBones(); ++Bone)
	{
		const FName Name = Wings->GetBoneName(Bone);
		if (Name.ToString().Contains(TEXT("wing"))) { EntryWingBones.Add(Name); }
	}
	GoldenBodyMaterial = UMaterialInstanceDynamic::Create(BodySource, this);
	if (!GoldenBodyMaterial) { return false; }
	GoldenBodyMaterial->SetVectorParameterValue(TEXT("BodyTint"), FLinearColor(1.0f, 0.72f, 0.22f));
	GoldenBodyMaterial->SetScalarParameterValue(TEXT("Visibility"), 1.0f);
	for (int32 Slot = 0; Slot < SourceMesh->GetNumMaterials(); ++Slot)
	{
		OriginalBodyMaterials.Add(SourceMesh->GetMaterial(Slot));
		SourceMesh->SetMaterial(Slot, GoldenBodyMaterial);
	}
	for (const int32 MaterialId : HiddenClothMaterialIds)
	{
		TArray<bool>& Visibility = ClothVisibility.AddDefaulted_GetRef();
		for (int32 Lod = 0; Lod < SourceMesh->GetNumLODs(); ++Lod)
		{
			Visibility.Add(SourceMesh->IsMaterialSectionShown(MaterialId, Lod));
			SourceMesh->ShowMaterialSection(MaterialId, INDEX_NONE, false, Lod);
		}
	}
	LifeSeconds = FMath::Clamp(Lifetime, 0.5f, 60.0f);
	StartedAt = GetWorld()->GetTimeSeconds();
	// 상태 만료 후 원본 Fold만 짧게 남긴다. 본체 외형/능력 상태는 만료 시점에 바로 복구한다.
	SetLifeSpan(LifeSeconds + WingVisualExitSeconds + .10f);
	UE_LOG(LogTemp, Display, TEXT("SPARROW_ASCENSION wings start hidden_cloth_sections=%d body_materials=%d seconds=%.2f wing_materials=%d,%d"),
		HiddenClothMaterialIds.Num(), OriginalBodyMaterials.Num(), LifeSeconds, Splines, Membrane);
	return true;
}

void ASparrowAscensionWings::BeginPlay()
{
	Super::BeginPlay();
	if (!SourceMesh.IsValid()) { Destroy(); return; }
	// Deferred spawn의 최종 transform 적용 이후에도 원본 몸통 기준점을 정확히 맞춘다.
	AttachToComponent(SourceMesh.Get(), FAttachmentTransformRules::SnapToTargetNotIncludingScale, TEXT("spine_03"));
	// V2의 짧은 진입만 날개 주변에서 전파한다. 유지 중에는 표면 자체의 화염만 남는다.
}

void ASparrowAscensionWings::UseIdleWings()
{
	if (IdleAnimation && IsValid(GetOwner()) && !bVisualExiting)
	{
		SetWingPose(IdleAnimation, 0.0f);
	}
}

FName ASparrowAscensionWings::GetWingAnimationName() const
{
	return CurrentWingAnimation ? CurrentWingAnimation->GetFName() : NAME_None;
}

void ASparrowAscensionWings::SetWingPose(UAnimSequence* Animation, float Position)
{
	if (!Animation || !Wings) { return; }
	const float ClampedPosition = FMath::Clamp(Position, 0.0f, Animation->GetPlayLength());
	if (CurrentWingAnimation == Animation && FMath::IsNearlyEqual(WingAnimationPosition, ClampedPosition)) { return; }
	if (CurrentWingAnimation != Animation)
	{
		CurrentWingAnimation = Animation;
		Wings->PlayAnimation(Animation, false);
		Wings->SetPlayRate(0.0f);
		if (UAnimInstance* Anim = Wings->GetAnimInstance()) { Anim->SetRootMotionMode(ERootMotionMode::IgnoreRootMotion); }
	}
	WingAnimationPosition = ClampedPosition;
	// Only the original skeletal pose is sampled; Serath's gameplay notifies and root movement never run.
	Wings->SetPosition(WingAnimationPosition, false);
	Wings->TickAnimation(0.0f, false);
	Wings->RefreshBoneTransforms();
	AlignWingRoot();
}

void ASparrowAscensionWings::AlignWingRoot()
{
	if (!Wings || !Wings->DoesSocketExist(TEXT("spine_03"))) { return; }
	const FTransform Anchor = Wings->GetSocketTransform(TEXT("spine_03"), RTS_Component);
	FTransform WingTransform = Anchor.Inverse();
	// 형상만 .8배로 줄이되 등 부착점도 함께 보정해 펼침 중 뿌리가 밀리지 않게 한다.
	WingTransform.SetTranslation(WingTransform.GetTranslation() * WingScale);
	WingTransform.SetScale3D(WingTransform.GetScale3D() * WingScale);
	// 펼친 Serath의 좌우 끝 본은 component X=-196..206cm에 놓인다. 길이 축만 10% 줄이고 Y/Z 폭은 유지한다.
	WingTransform.SetScale3D(WingTransform.GetScale3D() * FVector(0.90f, 1.0f, 1.0f));
	// 비균일 스케일 뒤에도 spine_03 부착점이 원래 원점에 남도록 회전·스케일을 적용한 anchor를 다시 상쇄한다.
	WingTransform.SetTranslation(-WingTransform.TransformVector(Anchor.GetTranslation()));
	Wings->SetRelativeTransform(WingTransform);
}

bool ASparrowAscensionWings::BeginWingAttack(float ChargeSeconds)
{
	if (bVisualExiting || GetRemainingSeconds() <= 0.0f || !SourceMesh.IsValid() || !AttackAnimation) { return false; }
	WingAttackStartedAt = GetWorld()->GetTimeSeconds();
	WingAttackReleasedAt = -1.0;
	WingAttackChargeSeconds = FMath::Max(.05f, ChargeSeconds);
	SetWingPose(AttackAnimation, 0.0f);
	return true;
}

void ASparrowAscensionWings::ReleaseWingAttack()
{
	if (bVisualExiting || WingAttackStartedAt < 0.0 || !GetWorld()) { return; }
	WingAttackReleasedAt = GetWorld()->GetTimeSeconds();
	SetWingPose(AttackAnimation, WingAttackReleasePose);
}

void ASparrowAscensionWings::CancelWingAttack()
{
	WingAttackStartedAt = WingAttackReleasedAt = -1.0;
	if (!bVisualExiting) { UseIdleWings(); }
}

void ASparrowAscensionWings::BeginVisualExit()
{
	if (bVisualExiting || !GetWorld()) { return; }
	bVisualExiting = true;
	VisualExitStartedAt = GetWorld()->GetTimeSeconds();
	WingAttackStartedAt = WingAttackReleasedAt = -1.0;
	RestoreBodyAppearance();
	SetWingPose(FoldAnimation, 0.0f);
	SetLifeSpan(WingVisualExitSeconds + .05f);
}

void ASparrowAscensionWings::UpdateWingAnimation(float Age)
{
	const double Now = GetWorld()->GetTimeSeconds();
	if (bVisualExiting)
	{
		const float Alpha = FMath::Clamp(static_cast<float>(Now - VisualExitStartedAt) / WingVisualExitSeconds, 0.0f, 1.0f);
		SetWingPose(FoldAnimation, FoldAnimation->GetPlayLength() * Alpha);
	}
	else if (WingAttackStartedAt >= 0.0)
	{
		if (WingAttackReleasedAt >= 0.0)
		{
			const float Alpha = FMath::Clamp(static_cast<float>(Now - WingAttackReleasedAt) / WingAttackReturnSeconds, 0.0f, 1.0f);
			SetWingPose(AttackAnimation, FMath::Lerp(WingAttackReleasePose, WingAttackReturnPose, Alpha));
			if (Alpha >= 1.0f) { CancelWingAttack(); }
		}
		else
		{
			const float Alpha = FMath::Clamp(static_cast<float>(Now - WingAttackStartedAt) / WingAttackChargeSeconds, 0.0f, 1.0f);
			SetWingPose(AttackAnimation, WingAttackReleasePose * Alpha);
			if (Now - WingAttackStartedAt > WingAttackChargeSeconds + .5f) { CancelWingAttack(); }
		}
	}
	else if (Age * WingUnfoldRate < UnfoldAnimation->GetPlayLength())
	{
		SetWingPose(UnfoldAnimation, Age * WingUnfoldRate);
	}
	else
	{
		UseIdleWings();
	}
}

float ASparrowAscensionWings::GetRemainingSeconds() const
{
	return !bVisualExiting && GetWorld() ? FMath::Max(0.0f, LifeSeconds - static_cast<float>(GetWorld()->GetTimeSeconds() - StartedAt)) : 0.0f;
}

void ASparrowAscensionWings::UpdateWingEnvelope(float Envelope)
{
	if (!SourceMesh.IsValid()) { return; }
	const FVector Origin = SourceMesh->GetSocketLocation(TEXT("spine_03"));
	const FVector Side = GetOwner()->GetActorRightVector();
	const FVector Back = -GetOwner()->GetActorForwardVector();
	for (UMaterialInstanceDynamic* Material : WingMaterials)
	{
		Material->SetScalarParameterValue(TEXT("WingAlpha"), Envelope);
		Material->SetVectorParameterValue(TEXT("WingRootPosition"), FLinearColor(
			static_cast<float>(Origin.X), static_cast<float>(Origin.Y), static_cast<float>(Origin.Z), 0.0f));
		Material->SetVectorParameterValue(TEXT("WingSideAxis"), FLinearColor(
			static_cast<float>(Side.X), static_cast<float>(Side.Y), static_cast<float>(Side.Z), 0.0f));
		Material->SetVectorParameterValue(TEXT("WingBackAxis"), FLinearColor(
			static_cast<float>(Back.X), static_cast<float>(Back.Y), static_cast<float>(Back.Z), 0.0f));
	}
}

FVector ASparrowAscensionWings::GetEntryWingPoint(float Side, float Reach, float Height) const
{
	if (!SourceMesh.IsValid() || !IsValid(GetOwner())) { return GetActorLocation(); }
	const FVector Root = SourceMesh->GetSocketLocation(TEXT("spine_03"));
	const FVector Right = GetOwner()->GetActorRightVector();
	FVector End = Root + Right * (Side * 155.0f * WingScale) - GetOwner()->GetActorForwardVector() * 32.0f + FVector(0.0f, 0.0f, 28.0f);
	float Extent = 24.0f;
	for (const FName Bone : EntryWingBones)
	{
		const FVector Point = Wings->GetSocketLocation(Bone);
		const float Projection = FVector::DotProduct(Point - Root, Right) * Side;
		if (Projection > Extent) { End = Point; Extent = Projection; }
	}
	return Root + (End - Root) * Reach + FVector(0.0f, 0.0f, Height);
}

void ASparrowAscensionWings::AddEntryFlame(UParticleSystem* Template, float Side, float Reach, float EndReach,
	float Height, float EndHeight, const FVector& Scale, const FVector& EndScale, float Duration, float Speed)
{
	if (!Template || !GetWorld() || !IsValid(GetOwner())) { return; }
	UParticleSystemComponent* Particle = NewObject<UParticleSystemComponent>(this, NAME_None, RF_Transient);
	Particle->bAutoActivate = false;
	Particle->bAutoDestroy = false;
	Particle->SetupAttachment(RootComponent);
	Particle->SetTemplate(Template);
	Particle->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Particle->SetGenerateOverlapEvents(false);
	Particle->SetCastShadow(false);
	Particle->SetCanEverAffectNavigation(false);
	Particle->ComponentTags.Add(TEXT("SparrowAscensionEntry"));
	Particle->bOverrideLODMethod = true;
	Particle->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
	Particle->CustomTimeDilation = Speed * WingEntrySpeed;
	AddInstanceComponent(Particle);
	Particle->RegisterComponent();
	const FVector Position = GetEntryWingPoint(Side, Reach, Height);
	const FVector Direction = (GetEntryWingPoint(Side, 1.0f, Height) - SourceMesh->GetSocketLocation(TEXT("spine_03"))).GetSafeNormal();
	Particle->SetWorldLocationAndRotation(Position, FRotationMatrix::MakeFromZ(Direction).Rotator());
	Particle->SetWorldScale3D(Scale);
	// 모든 등록/속성 설정을 마친 뒤 활성화한다. 비자동 PSC의 재등록으로 진입층이 꺼지는 것을 막는다.
	Particle->SetLODLevel(0);
	Particle->ActivateSystem(true);
	Particle->SetLODLevel(0);
	FEntryFlame& Flame = EntryFlames.AddDefaulted_GetRef();
	Flame.Particle = Particle;
	Flame.Born = static_cast<float>(GetWorld()->GetTimeSeconds() - StartedAt) - WingEntryRevealSeconds;
	Flame.Duration = Duration / WingEntrySpeed;
	Flame.Side = Side;
	Flame.Reach = Reach;
	Flame.EndReach = EndReach;
	Flame.Height = Height;
	Flame.EndHeight = EndHeight;
	Flame.Scale = Scale;
	Flame.EndScale = EndScale;
}

void ASparrowAscensionWings::UpdateEntryFlames(float Age)
{
	constexpr float Gain = 2.6f;
	constexpr float Delays[] = {0.38f, 0.50f, 0.66f, 0.82f, 0.98f, 1.04f};
	constexpr float Reaches[] = {0.26f, 0.52f, 0.78f, 1.08f};
	while (NextEntryBeat < UE_ARRAY_COUNT(Delays) && Age >= Delays[NextEntryBeat] / WingEntrySpeed)
	{
		for (const float Side : {-1.0f, 1.0f})
		{
			if (NextEntryBeat == 0)
			{
				AddEntryFlame(GetWingEntryShards(), Side, 0.05f, 1.10f, 20.0f, 20.0f,
					FVector(0.50f, 0.50f, 1.15f) * Gain, FVector(0.24f, 0.24f, 0.60f) * Gain, 0.72f, 1.1f);
			}
			else if (NextEntryBeat <= 4)
			{
				const float Reach = Reaches[NextEntryBeat - 1];
				AddEntryFlame(GetWingEntryIgnition(), Side, Reach, Reach + 0.06f, 2.0f, 5.0f,
					FVector(0.55f, 0.40f, 0.70f) * Gain, FVector(0.18f, 0.16f, 0.24f) * Gain, 0.40f, 1.3f);
			}
			else
			{
				AddEntryFlame(GetWingEntrySparks(), Side, 1.02f, 1.16f, 4.0f, 10.0f,
					FVector(0.65f, 0.42f, 0.42f) * Gain, FVector(0.20f, 0.15f, 0.15f) * Gain, 0.34f, 1.6f);
			}
		}
		++NextEntryBeat;
	}
	for (int32 Index = EntryFlames.Num() - 1; Index >= 0; --Index)
	{
		FEntryFlame& Flame = EntryFlames[Index];
		if (!Flame.Particle.IsValid() || Age - Flame.Born >= Flame.Duration)
		{
			if (Flame.Particle.IsValid()) { Flame.Particle->DestroyComponent(); }
			EntryFlames.RemoveAtSwap(Index);
			continue;
		}
		const float T = FMath::Clamp((Age - Flame.Born) / Flame.Duration, 0.0f, 1.0f);
		const float Blend = 1.0f - FMath::Square(1.0f - T);
		Flame.Particle->SetWorldLocation(GetEntryWingPoint(Flame.Side,
			FMath::Lerp(Flame.Reach, Flame.EndReach, Blend), FMath::Lerp(Flame.Height, Flame.EndHeight, Blend)));
		Flame.Particle->SetWorldScale3D(FMath::Lerp(Flame.Scale, Flame.EndScale, Blend));
	}
}

void ASparrowAscensionWings::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!IsValid(GetOwner()) || !SourceMesh.IsValid()) { Destroy(); return; }
	const float Age = static_cast<float>(GetWorld()->GetTimeSeconds() - StartedAt);
	const float Remaining = GetRemainingSeconds();
	if (!bVisualExiting && Remaining <= 0.0f) { BeginVisualExit(); }
	const float RevealAge = FMath::Max(0.0f, Age - WingEntryRevealSeconds);
	UpdateWingAnimation(RevealAge);
	const float ExitAge = bVisualExiting ? static_cast<float>(GetWorld()->GetTimeSeconds() - VisualExitStartedAt) : 0.0f;
	const float Envelope = bVisualExiting ? 1.0f - FMath::SmoothStep(.32f, WingVisualExitSeconds, ExitAge) :
		FMath::SmoothStep(0.0f, 0.55f / WingEntrySpeed, RevealAge);
	UpdateWingEnvelope(Envelope * MobilityVisibility);
	if (!bVisualExiting && Age >= WingEntryRevealSeconds)
	{
		if (!bEntryRevealPlayed)
		{
			bEntryRevealPlayed = true;
			const FVector RiseOrigin = SourceMesh->GetSocketLocation(TEXT("spine_03")) - FVector(0, 0, 36);
			SpawnAuthoredAccent(GetOwner(), GetEntryRiseTemplate(), RiseOrigin, FRotator::ZeroRotator,
				FVector(1.43f, 1.43f, 3.12f), .10f, .65f);
			SpawnFormAccent(GetOwner(), SourceMesh->GetSocketLocation(TEXT("spine_03")), .70f, true);
		}
		UpdateEntryFlames(RevealAge);
	}
	if (GoldenBodyMaterial && !bBodyAppearanceRestored)
	{
		const float EntryEmphasis = 1.0f + 0.18f * FMath::Square(FMath::Clamp(1.0f - Age / 0.70f, 0.0f, 1.0f));
		GoldenBodyMaterial->SetVectorParameterValue(TEXT("BodyTint"), FLinearColor(1.0f, 0.72f, 0.22f) * EntryEmphasis);
	}
	if (!bExitAccentPlayed && Remaining < 0.20f)
	{
		bExitAccentPlayed = true;
		SpawnFormAccent(GetOwner(), SourceMesh->GetSocketLocation(TEXT("spine_03")), 0.26f, false);
	}
	if (bVisualExiting && ExitAge >= WingVisualExitSeconds) { Destroy(); }
}

void ASparrowAscensionWings::RestoreBodyAppearance()
{
	if (bBodyAppearanceRestored) { return; }
	bBodyAppearanceRestored = true;
	if (SourceMesh.IsValid())
	{
		for (int32 Index = 0; Index < ClothVisibility.Num(); ++Index)
		{
			for (int32 Lod = 0; Lod < ClothVisibility[Index].Num() && Lod < SourceMesh->GetNumLODs(); ++Lod)
			{
				SourceMesh->ShowMaterialSection(HiddenClothMaterialIds[Index], INDEX_NONE, ClothVisibility[Index][Lod], Lod);
			}
		}
		for (int32 Slot = 0; Slot < OriginalBodyMaterials.Num(); ++Slot)
		{
			SourceMesh->SetMaterial(Slot, OriginalBodyMaterials[Slot]);
		}
	}
	UE_LOG(LogTemp, Display, TEXT("SPARROW_ASCENSION wings stop restored_cloth_sections=%d restored_body_materials=%d owner=%s"),
		ClothVisibility.Num(), OriginalBodyMaterials.Num(), *GetNameSafe(GetOwner()));
}

void ASparrowAscensionWings::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	for (const FEntryFlame& Flame : EntryFlames)
	{
		if (Flame.Particle.IsValid()) { Flame.Particle->DestroyComponent(); }
	}
	EntryFlames.Reset();
	RestoreBodyAppearance();
	Super::EndPlay(EndPlayReason);
}

ASparrowMirrorArcher::ASparrowMirrorArcher()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickGroup = TG_PostPhysics;
	SetActorEnableCollision(false);
	SetCanBeDamaged(false);
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	Archer = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("MirrorArcherMesh"));
	ConfigureVisual(Archer);
	Archer->SetupAttachment(RootComponent);
	Archer->bDisableClothSimulation = true;
	Archer->bAllowClothActors = false;
	Archer->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	Archer->SetAllowAnimCurveEvaluation(false);
	Tags.Add(TEXT("SparrowMirrorArcher"));
	Tags.Add(TEXT("SparrowSkillFX"));
}

bool ASparrowMirrorArcher::Initialize(ACharacter* Character, const FVector& Aim, bool bWhite)
{
	if (!IsValid(Character) || !Character->GetMesh() || !Character->GetMesh()->GetSkeletalMeshAsset() || !GetWorld()) { return false; }
	UMaterialInterface* Source = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowAscensionEcho.M_SparrowAscensionEcho"));
	AttackAnimation = LoadObject<UAnimSequence>(nullptr,
		TEXT("/Game/ParagonSparrow/Characters/Heroes/Sparrow/Animations/Primary_Fire_Fast.Primary_Fire_Fast"));
	const ASparrowCharacter* Sparrow = Cast<ASparrowCharacter>(Character);
	if (!Source || !AttackAnimation || !Sparrow || Sparrow->GetBasicAttackCycleSeconds() <= 0.0f ||
		AttackAnimation->GetSkeleton() != Character->GetMesh()->GetSkeletalMeshAsset()->GetSkeleton()) { return false; }
	SourceMesh = Character->GetMesh();
	Archer->SetSkeletalMeshAsset(SourceMesh->GetSkeletalMeshAsset());
	Archer->SetRelativeTransform(SourceMesh->GetRelativeTransform());
	Archer->SuspendClothingSimulation();
	Archer->SetForcedLOD(1);
	Archer->PlayAnimation(AttackAnimation, false);
	Archer->SetPlayRate(0.0f);
	Archer->GetAnimInstance()->SetRootMotionMode(ERootMotionMode::IgnoreRootMotion);
	EchoMaterial = UMaterialInstanceDynamic::Create(Source, this);
	if (!EchoMaterial) { return false; }
	EchoBodyTint = FLinearColor(0.95f, 0.60f, 0.12f);
	EchoMaterial->SetVectorParameterValue(TEXT("BodyTint"), EchoBodyTint);
	EchoMaterial->SetScalarParameterValue(TEXT("Visibility"), 0.0f);
	for (int32 Slot = 0; Slot < Archer->GetNumMaterials(); ++Slot) { Archer->SetMaterial(Slot, EchoMaterial); }
	const int32 Hood = Archer->GetMaterialIndex(TEXT("M14_CloakHood"));
	for (int32 Lod = 0; Lod < Archer->GetNumLODs(); ++Lod)
	{
		for (int32 Slot = 0; Slot < Archer->GetNumMaterials(); ++Slot)
		{
			// 설치형은 뛰지 않으므로 망토와 끈을 복구한다. 후드만 벗기고 V의 숨김 상태는 복제하지 않는다.
			Archer->ShowMaterialSection(Slot, INDEX_NONE, Slot != Hood, Lod);
		}
	}
	Archer->SetVisibility(true);
	CastDirection = (Aim - GetActorLocation()).GetSafeNormal2D();
	if (CastDirection.IsNearlyZero()) { CastDirection = Character->GetActorForwardVector(); }
	AttackPhaseOffset = bWhite ? 0.10f : 0.0f;
	StartedAt = GetWorld()->GetTimeSeconds();
	SetLifeSpan(2.0f);
	return true;
}

void ASparrowMirrorArcher::BeginPlay()
{
	Super::BeginPlay();
	if (!SourceMesh.IsValid()) { Destroy(); return; }
	SpawnFormAccent(GetOwner(), Archer->GetSocketLocation(TEXT("spine_03")), 0.34f, true);
}

void ASparrowMirrorArcher::BeginVolley()
{
	if (bVolleyStarted || !IsValid(GetOwner())) { return; }
	bVolleyStarted = true;
	VolleyStartedAt = GetWorld()->GetTimeSeconds();
	NextAttackAt = VolleyStartedAt + AttackPhaseOffset;
	SetLifeSpan(SentryLifetime);
}

bool ASparrowMirrorArcher::CanEcho() const
{
	return bVolleyStarted && !IsActorBeingDestroyed() && SourceMesh.IsValid() && IsValid(GetOwner()) && GetRemainingSeconds() > 0.0f;
}

float ASparrowMirrorArcher::GetRemainingSeconds() const
{
	return bVolleyStarted && GetWorld() ? FMath::Max(0.0f, SentryLifetime - static_cast<float>(GetWorld()->GetTimeSeconds() - VolleyStartedAt)) : 0.0f;
}

FVector ASparrowMirrorArcher::GetArrowOrigin() const
{
	return Archer->DoesSocketExist(TEXT("arrow_anchor")) ? Archer->GetSocketLocation(TEXT("arrow_anchor")) :
		GetActorLocation() + GetActorForwardVector() * 55.0f + FVector(0.0f, 0.0f, 25.0f);
}

AActor* ASparrowMirrorArcher::FindSentryTarget() const
{
	const ASparrowCharacter* Sparrow = Cast<ASparrowCharacter>(GetOwner());
	const USparrowSkillComponent* Skills = Sparrow ? Sparrow->GetSparrowSkills() : nullptr;
	if (!Skills || !GetWorld()) { return nullptr; }
	const FVector Origin = GetArrowOrigin();
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_Pawn);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	FCollisionQueryParams Query(SCENE_QUERY_STAT(SparrowSentryTargets), false, GetOwner());
	Query.AddIgnoredActor(this);
	TArray<FOverlapResult> Overlaps;
	GetWorld()->OverlapMultiByObjectType(Overlaps, Origin, FQuat::Identity, Objects,
		FCollisionShape::MakeSphere(Skills->BasicAttackRange), Query);
	AActor* Nearest = nullptr;
	float NearestSquared = FMath::Square(Skills->BasicAttackRange);
	for (const FOverlapResult& Overlap : Overlaps)
	{
		AActor* Candidate = Overlap.GetActor();
		const AKwangTrainingDummy* Dummy = Cast<AKwangTrainingDummy>(Candidate);
		if (!IsValid(Candidate) || Candidate == GetOwner() || Candidate->IsActorBeingDestroyed() ||
			!Candidate->CanBeDamaged() || (!Candidate->IsA<APawn>() && !Dummy) || (Dummy && !Dummy->IsAlive())) { continue; }
		const float DistanceSquared = FVector::DistSquared(Origin, Candidate->GetActorLocation());
		if (DistanceSquared > NearestSquared || !Skills->HasWorldLineOfSight(Origin, Candidate->GetActorLocation(), Candidate)) { continue; }
		Nearest = Candidate;
		NearestSquared = DistanceSquared;
	}
	return Nearest;
}

void ASparrowMirrorArcher::StartSentryAttack()
{
	const ASparrowCharacter* Sparrow = Cast<ASparrowCharacter>(GetOwner());
	const float Cycle = Sparrow ? Sparrow->GetBasicAttackCycleSeconds() : 0.0f;
	if (Cycle <= 0.0f || !AttackAnimation) { Destroy(); return; }
	SentryTarget = FindSentryTarget();
	const FVector Facing = SentryTarget.IsValid() ? (SentryTarget->GetActorLocation() - GetActorLocation()).GetSafeNormal2D() : CastDirection;
	SetActorRotation(Facing.Rotation());
	Archer->PlayAnimation(AttackAnimation, false);
	Archer->SetPlayRate(AttackAnimation->GetPlayLength() / (Cycle * FMath::Max(FMath::Abs(AttackAnimation->RateScale), 0.001f)));
	Archer->GetAnimInstance()->SetRootMotionMode(ERootMotionMode::IgnoreRootMotion);
	const double Now = GetWorld()->GetTimeSeconds();
	ShotAt = Now + Cycle * 0.25;
	NextAttackAt = Now + Cycle;
	bShotPending = true;
}

void ASparrowMirrorArcher::FireSentryArrow()
{
	const ASparrowCharacter* Sparrow = Cast<ASparrowCharacter>(GetOwner());
	USparrowSkillComponent* Skills = Sparrow ? Sparrow->GetSparrowSkills() : nullptr;
	if (!Skills || !CanEcho()) { return; }
	// 준비 중 대상이 죽거나 시야를 벗어났으면 현재 유효한 표적을 다시 고른다.
	AActor* Target = FindSentryTarget();
	SentryTarget = Target;
	const FVector Origin = GetArrowOrigin();
	const FVector Direction = Target ? (Target->GetActorLocation() - Origin).GetSafeNormal() : CastDirection;
	const float Damage = Target ? Skills->BasicAttackDamage * SentryDamageScale : 0.0f;
	if (ASparrowArrow* Arrow = Skills->SpawnArrow(Direction, Damage, Skills->BasicAttackRange, Skills->ArrowSpeed,
		false, false, false, false, &Origin, false))
	{
		Arrow->Tags.Add(TEXT("SparrowSentryArrow"));
		if (UMaterialInterface* Gold = LoadObject<UMaterialInterface>(nullptr,
			TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowAscensionGold.M_SparrowAscensionGold")))
		{
			TArray<UStaticMeshComponent*> Meshes;
			Arrow->GetComponents<UStaticMeshComponent>(Meshes);
			for (UStaticMeshComponent* Mesh : Meshes)
			{
				if (Mesh->GetFName() != TEXT("ArrowMesh")) { continue; }
				Mesh->SetRelativeScale3D(FVector(0.55f, 0.55f, 0.65f));
				for (int32 Slot = 0; Slot < FMath::Max(1, Mesh->GetNumMaterials()); ++Slot) { Mesh->SetMaterial(Slot, Gold); }
			}
		}
		++EchoesFired;
		EchoPulseDeadline = GetWorld()->GetTimeSeconds() + 0.10;
		Skills->SpawnEffect(Skills->PrimaryMuzzle, Origin, Direction.Rotation(), 0.12f, false, 0.45f);
	}
}

void ASparrowMirrorArcher::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!IsValid(GetOwner()) || !SourceMesh.IsValid() || !EchoMaterial) { Destroy(); return; }
	const double Now = GetWorld()->GetTimeSeconds();
	if (CanEcho())
	{
		if (bShotPending && Now >= ShotAt) { bShotPending = false; FireSentryArrow(); }
		if (Now >= NextAttackAt) { StartSentryAttack(); }
	}
	const float FadeIn = FMath::SmoothStep(0.0f, 0.16f, static_cast<float>(Now - StartedAt));
	const float FadeOut = bVolleyStarted ? FMath::SmoothStep(0.0f, 0.35f, GetRemainingSeconds()) : 1.0f;
	EchoMaterial->SetScalarParameterValue(TEXT("Visibility"), FadeIn * FadeOut);
	const float EchoEmphasis = 1.0f + 0.45f * FMath::Clamp(static_cast<float>((EchoPulseDeadline - Now) / 0.10), 0.0f, 1.0f);
	EchoMaterial->SetVectorParameterValue(TEXT("BodyTint"), EchoBodyTint * EchoEmphasis);
	if (bVolleyStarted && !bExitAccentPlayed && GetRemainingSeconds() < 0.22f)
	{
		bExitAccentPlayed = true;
		SpawnFormAccent(GetOwner(), Archer->GetSocketLocation(TEXT("spine_03")), 0.23f, false);
	}
}

void ASparrowMirrorArcher::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	bShotPending = false;
	SentryTarget.Reset();
	UE_LOG(LogTemp, Display, TEXT("SPARROW_ASCENSION mirror end echoed_shots=%d"), EchoesFired);
	Super::EndPlay(EndPlayReason);
}
