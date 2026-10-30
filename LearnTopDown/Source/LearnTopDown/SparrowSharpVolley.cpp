#include "SparrowSharpVolley.h"

#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "Particles/ParticleEmitter.h"
#include "SparrowArrow.h"
#include "SparrowArsenalStudyFX.h"
#include "SparrowSkillComponent.h"
#include "TopDownCombatCharacter.h"

namespace
{
	constexpr float CastSeconds = 0.68f;
	constexpr float FirstShot = 0.38f;
	constexpr int32 ApertureCount = 5;
	constexpr float ShotRange = 450.0f;
	constexpr float ShotSpeed = 6000.0f;
	TAutoConsoleVariable<int32> CVarSharpPreview(TEXT("Sparrow.Sharp.Preview"), 0,
		TEXT("S effect study: 0 current, 1 mixed circles, 2 twin large circles, 3 large anchor circle, 4 offset circle cluster."), ECVF_Cheat);
	TAutoConsoleVariable<int32> CVarSharpDetailPreview(TEXT("Sparrow.Sharp.DetailPreview"), 0,
		TEXT("S preview: 0 installed, 1 layered light, 2 gold dust, 3 light fibers, 4 sharp eruption, 5 flowing release."), ECVF_Cheat);
	TAutoConsoleVariable<int32> CVarSharpArtPreview(TEXT("Sparrow.Sharp.ArtPreview"), 0,
		TEXT("S art studies: 0 installed, 1 A crescents, 2 B woven light, 3 C veils, 4 D vortex, 5 E crystals, 6 F ignition. Read at cast start."), ECVF_Cheat);
	TAutoConsoleVariable<int32> CVarSharpReference(TEXT("Sparrow.Sharp.Reference"), 3,
		TEXT("S reference restoration: 0 installed, 1 radiance v10, 2 refined radiance, 3 charged radiance. Read at cast start."), ECVF_Cheat);

	UParticleSystem* PressureTemplate()
	{
		static TWeakObjectPtr<UParticleSystem> Cached;
		if (Cached.IsValid()) { return Cached.Get(); }
		UParticleSystem* Source = LoadObject<UParticleSystem>(nullptr,
			TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Primary/FX/P_SparrowPrimaryMuzzleFlash.P_SparrowPrimaryMuzzleFlash"));
		if (!Source) { return nullptr; }
		UParticleSystem* Copy = DuplicateObject<UParticleSystem>(Source, GetTransientPackage(),
			MakeUniqueObjectName(GetTransientPackage(), UParticleSystem::StaticClass(), TEXT("P_SparrowSharpPressure")));
		Copy->SetFlags(RF_Transient);
		Copy->ClearFlags(RF_Public | RF_Standalone);
		// 넓은 안개·고리·섬광층 없이 작은 원본 발광과 불티만 남긴다.
		Copy->Emitters.RemoveAll([](UParticleEmitter* Emitter)
		{
			return !Emitter || (Emitter->GetEmitterName() != TEXT("MuzzleGlow") && Emitter->GetEmitterName() != TEXT("Sparks"));
		});
		if (Copy->Emitters.IsEmpty()) { return nullptr; }
		for (UParticleEmitter* Emitter : Copy->Emitters)
		{
			if (!Emitter->IsIn(Copy)) { return nullptr; }
			Emitter->UpdateModuleLists();
		}
		Cached = Copy;
		return Copy;
	}
}

ASparrowSharpVolley::ASparrowSharpVolley()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickGroup = TG_PostPhysics;
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
	SetActorEnableCollision(false);
	SetCanBeDamaged(false);
	Tags.Append({TEXT("SparrowSharpVolley"), TEXT("SparrowSkillFX")});
}

bool ASparrowSharpVolley::Initialize(ATopDownCombatCharacter* Character, const FVector& Aim)
{
	if (!IsValid(Character) || GetOwner() != Character || !Character->GetMesh() || !GetWorld() || Aim.ContainsNaN()) { return false; }
	Caster = Character;
	Skills = Character->FindComponentByClass<USparrowSkillComponent>();
	Animation = Character->GetMesh()->GetAnimInstance();
	Direction = (Aim - Character->GetActorLocation()).GetSafeNormal2D();
	if (!Skills.IsValid() || !Animation.IsValid() || Direction.IsNearlyZero()) { return false; }
	bAscended = Skills->GetAscensionRemaining() > 0.0f;
	if (bAscended) { Tags.Add(TEXT("SparrowAscendedSharp")); }
	UAnimSequence* Fire = LoadObject<UAnimSequence>(nullptr,
		TEXT("/Game/ParagonSparrow/Characters/Heroes/Sparrow/Animations/Primary_Fire_Fast.Primary_Fire_Fast"));
	const USkeletalMesh* Body = Character->GetMesh()->GetSkeletalMeshAsset();
	if (!Fire || !Body || Fire->GetSkeleton() != Body->GetSkeleton() || Fire->GetPlayLength() < 0.60f - KINDA_SMALL_NUMBER) { return false; }
	Montage = UAnimMontage::CreateSlotAnimationAsDynamicMontage(Fire, TEXT("SparrowUpperBody"), .04f, .08f, 1.0f, 1);
	if (!Montage) { return false; }
	Montage->SetFlags(RF_Transient);
	FAnimTrack& Track = Montage->SlotAnimTracks[0].AnimTrack;
	Track.AnimSegments.Reset();
	const auto Add = [&Track, Fire](float From, float To, float Start, float Duration, int32 Loops)
	{
		FAnimSegment Segment;
		Segment.SetAnimReference(Fire);
		Segment.StartPos = Start;
		Segment.AnimStartTime = From;
		Segment.AnimEndTime = To;
		Segment.AnimPlayRate = (To - From) / (Duration * FMath::Max(FMath::Abs(Fire->RateScale), .001f));
		Segment.LoopingCount = Loops;
		Track.AnimSegments.Add(Segment);
	};
	// 당김을 모은 뒤 한 번만 반동한다. 화살 묶음을 팔의 반복 재장전으로 표현하지 않는다.
	Add(.33f, .45f, 0.0f, FirstShot, 1);
	Add(0.0f, .45f, FirstShot, .16f, 1);
	Add(.45f, .60f, FirstShot + .16f, CastSeconds - FirstShot - .16f, 1);
	Montage->SetCompositeLength(CastSeconds);
	PreviewStyle = FMath::Clamp(CVarSharpPreview.GetValueOnGameThread(), 0, 4);
	DetailPreviewStyle = FMath::Clamp(CVarSharpDetailPreview.GetValueOnGameThread(), 0, 11);
	const int32 ArtStyle = FMath::Clamp(CVarSharpArtPreview.GetValueOnGameThread(), 0, 6);
	if (ArtStyle > 0) { DetailPreviewStyle = ArtStyle + 5; }
	// 채택된 A 겹광륜을 기본 S에 사용한다. 다른 시안은 명시 선택 때만 읽는다.
	else if (DetailPreviewStyle == 0 && PreviewStyle == 0) { DetailPreviewStyle = 6; }
	if (DetailPreviewStyle > 0) { PreviewStyle = 0; }
	ReferenceStyle = FMath::Clamp(CVarSharpReference.GetValueOnGameThread(), 0, 3);
	if (ReferenceStyle > 0)
	{
		// 복원 모드는 채택 광륜·후속 시안보다 우선한다. 게임 판정과 최신 이동 회복은 유지한다.
		PreviewStyle = 0;
		DetailPreviewStyle = 0;
		Tags.Add(TEXT("SparrowSharpReference"));
		if (ReferenceStyle == 2) { Tags.Add(TEXT("SparrowSharpReferenceRefined")); }
		if (ReferenceStyle == 3) { Tags.Add(TEXT("SparrowSharpReferencePlume")); }
	}
	UStaticMesh* Plane = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
	UMaterialInterface* Surface = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowSharpMuzzle.M_SparrowSharpMuzzle"));
	UMaterialInterface* Streak = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowSharpStreak.M_SparrowSharpStreak"));
	UMaterialInterface* Release = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowSharpRelease.M_SparrowSharpRelease"));
	if (PreviewStyle > 0)
	{
		Surface = LoadObject<UMaterialInterface>(nullptr, *FString::Printf(
			TEXT("/Game/TopDown/Characters/Sparrow/Materials/SharpConcepts/M_SharpC%dMuzzle.M_SharpC%dMuzzle"), PreviewStyle, PreviewStyle));
		Release = LoadObject<UMaterialInterface>(nullptr, *FString::Printf(
			TEXT("/Game/TopDown/Characters/Sparrow/Materials/SharpConcepts/M_SharpC%dRelease.M_SharpC%dRelease"), PreviewStyle, PreviewStyle));
	}
	if (DetailPreviewStyle > 0)
	{
		const auto DetailMaterial = [this](const TCHAR* Part)
		{
			const TCHAR* Folder = bAscended && (DetailPreviewStyle == 6 || DetailPreviewStyle == 10) ?
				TEXT("AscendedArsenal20261026") : DetailPreviewStyle >= 6 ? TEXT("SharpArt20261026") : TEXT("SharpDetails20261026");
			return LoadObject<UMaterialInterface>(nullptr, *FString::Printf(
				TEXT("/Game/TopDown/Characters/Sparrow/Materials/%s/M_SharpT%d%s.M_SharpT%d%s"),
				Folder, DetailPreviewStyle, Part, DetailPreviewStyle, Part));
		};
		Surface = DetailMaterial(TEXT("Muzzle"));
		Release = DetailMaterial(TEXT("Release"));
		Streak = DetailMaterial(TEXT("Streak"));
	}
	if (ReferenceStyle > 0)
	{
		const auto ReferenceMaterial = [this](const TCHAR* Part)
		{
			return LoadObject<UMaterialInterface>(nullptr, *FString::Printf(
				TEXT("/Game/TopDown/Characters/Sparrow/Materials/SharpReference20261027/%s/M_SharpReference%s.M_SharpReference%s"),
				ReferenceStyle == 3 ? TEXT("Plume") : ReferenceStyle == 2 ? TEXT("Refined") : TEXT("Base"), Part, Part));
		};
		Surface = ReferenceMaterial(TEXT("Muzzle"));
		Streak = ReferenceMaterial(TEXT("Streak"));
		Release = ReferenceMaterial(TEXT("Release"));
	}
	if (!Plane || !Surface || !Streak || !Release || !PressureTemplate()) { return false; }
	PressureMaterial = UMaterialInstanceDynamic::Create(Surface, this);
	PressureMaterial->SetScalarParameterValue(TEXT("Age"), 0.0f);
	PressureMaterial->SetScalarParameterValue(TEXT("ShotAge"), 100.0f);
	ReleaseMaterial = UMaterialInstanceDynamic::Create(Release, this);
	ReleaseMaterial->SetScalarParameterValue(TEXT("ShotAge"), 100.0f);
	const auto AddMesh = [this](UStaticMesh* Mesh, UMaterialInterface* Material, FName Tag)
	{
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
		Part->ComponentTags.Add(Tag);
		AddInstanceComponent(Part);
		Part->RegisterComponent();
		return Part;
	};
	for (int32 Index = 0; Index < ApertureCount; ++Index)
	{
		UMaterialInstanceDynamic* RingMaterial = Index > 0 ?
			UMaterialInstanceDynamic::Create(Surface, this) : PressureMaterial.Get();
		RingMaterial->SetScalarParameterValue(TEXT("Index"), static_cast<float>(Index));
		PressureSurfaceMaterials.Add(RingMaterial);
		PressureSurfaces.Add(AddMesh(Plane, RingMaterial, TEXT("SparrowSharpMuzzleApertures")));
		ChargeArrows.Add(AddMesh(Plane, Streak, TEXT("SparrowSharpChargeArrow")));
		ChargeArrows.Add(AddMesh(Plane, Streak, TEXT("SparrowSharpChargeArrow")));
	}
	ReleaseSurface = AddMesh(Plane, ReleaseMaterial, TEXT("SparrowSharpReleaseWave"));
	if (DetailPreviewStyle == 5)
	{
		UMaterialInterface* FlowSource = LoadObject<UMaterialInterface>(nullptr,
			TEXT("/Game/TopDown/Characters/Sparrow/Materials/SharpDetails20261026/M_SharpT5Flow.M_SharpT5Flow"));
		if (!FlowSource) { return false; }
		VisualPathLengths.Init(0.0f, ApertureCount);
		for (int32 Index = 0; Index < ApertureCount; ++Index)
		{
			UMaterialInstanceDynamic* Flow = UMaterialInstanceDynamic::Create(FlowSource, this);
			Flow->SetScalarParameterValue(TEXT("Index"), static_cast<float>(Index));
			FlowMaterials.Add(Flow);
			FlowSurfaces.Add(AddMesh(Plane, Flow, TEXT("SparrowSharpFlow")));
		}
	}
	if (DetailPreviewStyle >= 6 && !InitializeArtPresentation(Plane)) { return false; }
	const int32 StudyCandidate = ReferenceStyle > 0 ? 0 : ASparrowArsenalStudyFX::GetCandidate(5);
	if (StudyCandidate > 0)
	{
		FActorSpawnParameters Spawn;
		Spawn.Owner = Character;
		Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		ASparrowArsenalStudyFX* Study = GetWorld()->SpawnActor<ASparrowArsenalStudyFX>(
			ASparrowArsenalStudyFX::StaticClass(), FTransform::Identity, Spawn);
		if (Study && Study->Initialize(Character, 5, StudyCandidate, Skills->GetArrowOrigin(), Direction, FirstShot))
		{
			ArsenalStudy = Study;
			ArsenalStudyCandidate = StudyCandidate;
			Tags.Add(FName(*FString::Printf(TEXT("SparrowStudyS%d"), StudyCandidate)));
		}
		else if (Study) { Study->Destroy(); }
	}
	StartedAt = GetWorld()->GetTimeSeconds();
	bInitialized = true;
	SetLifeSpan(.80f);
	return true;
}

void ASparrowSharpVolley::BeginPlay()
{
	Super::BeginPlay();
	if (!bInitialized || !Caster.IsValid() || !Animation.IsValid() || !Montage) { Destroy(); return; }
	bAnimationStarted = Animation->Montage_Play(Montage, 1.0f, EMontagePlayReturnType::MontageLength, 0.0f, false) > 0.0f;
	if (!bAnimationStarted) { Destroy(); }
}

float ASparrowSharpVolley::GetRemainingSeconds() const
{
	return bInitialized && GetWorld() && !IsActorBeingDestroyed() ?
		FMath::Max(0.0f, CastSeconds - static_cast<float>(GetWorld()->GetTimeSeconds() - StartedAt)) : 0.0f;
}

bool ASparrowSharpVolley::IsCasting() const
{
	return !bMovementReleased && Caster.IsValid() && GetOwner() == Caster.Get() && GetRemainingSeconds() > 0.0f;
}

void ASparrowSharpVolley::ReleaseRecoveryForMovement()
{
	if (!GetWorld() || bMovementReleased || WavesFired == 0 || LastReleaseAge < 0.0f ||
		GetWorld()->GetTimeSeconds() - StartedAt < LastReleaseAge + .035f) { return; }
	bMovementReleased = true;
	if (Animation.IsValid() && Montage) { Animation->Montage_Stop(.035f, Montage); }
}

void ASparrowSharpVolley::ReleaseWave()
{
	if (!Caster.IsValid() || !Skills.IsValid() || GetOwner() != Caster.Get() || Skills->GetOwner() != Caster.Get()) { return; }
	const float Age = static_cast<float>(GetWorld()->GetTimeSeconds() - StartedAt);
	// 발사구의 표시 좌표를 그대로 실탄의 출발점으로 사용한다.
	UpdatePressure(Age);
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Direction).GetSafeNormal();
	const TSharedPtr<TSet<TWeakObjectPtr<AActor>>> Hits = MakeShared<TSet<TWeakObjectPtr<AActor>>>();
	int32 Released = 0;
	FCollisionObjectQueryParams WorldObjects;
	WorldObjects.AddObjectTypesToQuery(ECC_WorldStatic);
	WorldObjects.AddObjectTypesToQuery(ECC_WorldDynamic);
	FCollisionQueryParams WorldQuery(SCENE_QUERY_STAT(SparrowSharpMuzzle), false, Caster.Get());
	WorldQuery.AddIgnoredActor(this);
	for (int32 Index = 0; Index < ApertureCount; ++Index)
	{
		const FVector Origin = PressureSurfaces[Index]->GetComponentLocation();
		ReleaseOrigins.Add(Origin);
		FVector BodyOrigin = Caster->GetActorLocation();
		BodyOrigin.Z = Origin.Z;
		FHitResult Obstacle;
		// 옆으로 벌린 발사구가 얇은 벽 너머에서 시작하는 것을 막는다.
		if (GetWorld()->LineTraceSingleByObjectType(Obstacle, BodyOrigin, Origin, WorldObjects, WorldQuery)) { continue; }
		if (DetailPreviewStyle == 5)
		{
			FHitResult VisualObstacle;
			const bool bBlocked = GetWorld()->LineTraceSingleByObjectType(VisualObstacle, Origin,
				Origin + Direction * ShotRange, WorldObjects, WorldQuery);
			VisualPathLengths[Index] = bBlocked ? FMath::Max(0.0f, VisualObstacle.Distance - 3.0f) : ShotRange;
		}
		for (int32 Lane = -1; Lane <= 1; ++Lane)
		{
			// 발사구 안에서 출발점만 나누며 모든 화살의 진행 방향은 동일하게 유지한다.
			const FVector LaneOrigin = Origin + Right * (Lane * 8.0f);
			BodyOrigin.Z = LaneOrigin.Z;
			if (GetWorld()->LineTraceSingleByObjectType(Obstacle, BodyOrigin, LaneOrigin, WorldObjects, WorldQuery)) { continue; }
			if (ASparrowArrow* Arrow = Skills->SpawnArrow(Direction, 54.0f, ShotRange, ShotSpeed,
				true, false, false, true, &LaneOrigin, false, Hits))
			{
				Arrow->Tags.Add(TEXT("SparrowSharpVolleyArrow"));
				if (ReferenceStyle > 0)
				{
					Arrow->Tags.Add(TEXT("SparrowSharpReference"));
					if (ReferenceStyle == 2) { Arrow->Tags.Add(TEXT("SparrowSharpReferenceRefined")); }
					if (ReferenceStyle == 3) { Arrow->Tags.Add(TEXT("SparrowSharpReferencePlume")); }
				}
				if (ArsenalStudyCandidate >= 9 && ArsenalStudyCandidate <= 12)
				{
					Arrow->Tags.Add(FName(*FString::Printf(TEXT("SparrowSStudy%d"), ArsenalStudyCandidate)));
				}
				Arrow->EnableSharpBurstPresentation(DetailPreviewStyle);
				++Released;
			}
		}
	}
	LastReleaseAge = static_cast<float>(GetWorld()->GetTimeSeconds() - StartedAt);
	++WavesFired;
	if (Released > 0 && ArsenalStudy.IsValid()) { ArsenalStudy->Pulse(Skills->GetArrowOrigin() + Direction * 20.0f, Direction); }
	UParticleSystemComponent* Particle = NewObject<UParticleSystemComponent>(this, NAME_None, RF_Transient);
	Particle->bAutoActivate = false;
	Particle->bAutoDestroy = false;
	Particle->SetTemplate(PressureTemplate());
	Particle->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Particle->SetCanEverAffectNavigation(false);
	Particle->SetCastShadow(false);
	Particle->bOverrideLODMethod = true;
	Particle->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
	Particle->CustomTimeDilation = 2.5f;
	Particle->ComponentTags.Add(TEXT("SparrowSharpMuzzle"));
	AddInstanceComponent(Particle);
	Particle->RegisterComponent();
	Particle->SetWorldLocationAndRotation(Skills->GetArrowOrigin() + Direction * 20.0f, Direction.Rotation());
	Particle->SetWorldScale3D(FVector(.70f));
	Particle->SetLODLevel(0);
	Particle->ActivateSystem(true);
	MuzzleParticles.Add(Particle);
	UE_LOG(LogTemp, Display, TEXT("SPARROW_SHARP wave=%d arrows=%d age=%.3f damage=54 range=450 speed=6000 apertures=5"),
		WavesFired, Released, LastReleaseAge);
}

void ASparrowSharpVolley::UpdatePressure(float Age)
{
	const float Since = LastReleaseAge < 0.0f ? 100.0f : Age - LastReleaseAge;
	const float Recoil = FMath::Square(FMath::Clamp(1.0f - Since / .09f, 0.0f, 1.0f));
	const FVector Origin = Skills->GetArrowOrigin() + Direction * 20.0f;
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Direction).GetSafeNormal();
	// 다섯 발사구는 카메라를 보지 않고 실제 사격 축에 수직으로 펼쳐진다.
	// 큰 겹친 윤곽을 먼저 펼치고 재질에서 작은 발사구로 압축한다. 실제 출발 위치는 유지한다.
	const float Open = 1.0f - FMath::Pow(1.0f - FMath::Clamp(Age / .23f, 0.0f, 1.0f), 3.0f);
	const float Loose = 1.0f - FMath::SmoothStep(.105f, .265f, Age);
	for (int32 Index = 0; Index < PressureSurfaces.Num(); ++Index)
	{
		const float Phase = HALF_PI + Index * (2.0f * PI / ApertureCount);
		const FVector Offset = Right * FMath::Cos(Phase) + FVector::UpVector * FMath::Sin(Phase);
		FVector Location = ReleaseOrigins.IsValidIndex(Index) ? ReleaseOrigins[Index] - Direction * Recoil * 7.0f :
			Origin + Offset * (45.0f * FMath::Lerp(.35f, 1.0f, Open));
		FVector ShapeScale(1.80f, 1.80f, 1.0f);
		FQuat ShapeRotation = FRotationMatrix::MakeFromXZ(Right, Direction).ToQuat();
		{
			// 불규칙한 것은 원의 크기와 배치다. 각 원의 윤곽·가로세로 비율·방향은 유지한다.
			static const float CircleSizes[4][ApertureCount] = {
				{1.16f,.64f,.94f,.72f,.50f},
				{1.32f,1.12f,.45f,.65f,.56f},
				{1.52f,.42f,.58f,.66f,.80f},
				{.60f,1.10f,.48f,.88f,1.28f}};
			static const FVector2D CircleOffsets[4][ApertureCount] = {
				{{-7,8},{5,-6},{-8,-4},{10,4},{3,10}},
				{{10,-16},{-4,9},{8,7},{-8,3},{0,-5}},
				{{0,-32},{-8,7},{0,-5},{5,-4},{12,0}},
				{{-24,-8},{-16,4},{-2,-7},{20,12},{26,16}}};
			const int32 Design = FMath::Max(0, PreviewStyle - 1);
			const FVector2D CircleOffset = CircleOffsets[Design][Index];
			Location += (Right * CircleOffset.X + FVector::UpVector * CircleOffset.Y) * Loose;
			const float UniformScale = FMath::Lerp(1.0f, CircleSizes[Design][Index], Loose);
			ShapeScale.X *= UniformScale;
			ShapeScale.Y *= UniformScale;
		}
		PressureSurfaces[Index]->SetWorldLocationAndRotation(Location, ShapeRotation);
		PressureSurfaces[Index]->SetWorldScale3D(ShapeScale);
		PressureSurfaces[Index]->SetVisibility(Age < .64f);
		if (FlowSurfaces.IsValidIndex(Index))
		{
			const bool bReleased = LastReleaseAge >= 0.0f;
			const float Length = bReleased ? VisualPathLengths[Index] : 160.0f;
			const FVector Start = bReleased ? ReleaseOrigins[Index] : Location - Direction * Length;
			const FVector Midpoint = Start + Direction * (Length * .5f);
			FVector Normal = FVector::UpVector;
			if (APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(this, 0))
			{
				Normal = Camera->GetCameraLocation() - Midpoint;
			}
			FlowSurfaces[Index]->SetWorldLocationAndRotation(Midpoint, FRotationMatrix::MakeFromXZ(Direction, Normal).ToQuat());
			FlowSurfaces[Index]->SetWorldScale3D(FVector(FMath::Max(Length, 1.0f) / 100.0f, bReleased ? .70f : 1.10f, 1.0f));
			FlowSurfaces[Index]->SetVisibility(Length > 1.0f && (bReleased ? Since < .23f : Age > .035f));
			FlowMaterials[Index]->SetScalarParameterValue(TEXT("Age"), Age);
			FlowMaterials[Index]->SetScalarParameterValue(TEXT("ShotAge"), Since);
			FlowMaterials[Index]->SetScalarParameterValue(TEXT("PathLength"), Length);
		}
		const float Draw = FMath::SmoothStep(.19f, .29f, Age);
		for (int32 Cross = 0; Cross < 2; ++Cross)
		{
			UStaticMeshComponent* Arrow = ChargeArrows[Index * 2 + Cross];
			Arrow->SetWorldLocationAndRotation(Location - Direction * (12.0f + 18.0f * Draw),
				Direction.Rotation().Quaternion() * FRotator(0.0f, 0.0f, Cross * 90.0f).Quaternion());
			Arrow->SetWorldScale3D(FVector(.46f * Draw, .12f * Draw, 1.0f));
			Arrow->SetVisibility(Draw > .01f && WavesFired == 0);
		}
	}
	for (UMaterialInstanceDynamic* Material : PressureSurfaceMaterials)
	{
		Material->SetScalarParameterValue(TEXT("Age"), Age);
		Material->SetScalarParameterValue(TEXT("ShotAge"), Since);
	}
	// 압축된 다섯 고리와 별개의 두 번째 원형 파동. 위치를 고정해 손의 반동을 따라 흔들리지 않는다.
	FVector ReleaseOrigin = Origin;
	if (ReleaseOrigins.Num() == ApertureCount)
	{
		ReleaseOrigin = FVector::ZeroVector;
		for (const FVector& Location : ReleaseOrigins) { ReleaseOrigin += Location; }
		ReleaseOrigin /= ApertureCount;
	}
	ReleaseSurface->SetWorldLocationAndRotation(ReleaseOrigin + Direction * 10.0f,
		FRotationMatrix::MakeFromXZ(Right, Direction).Rotator());
	ReleaseSurface->SetWorldScale3D(FVector(2.30f, 2.30f, 1.0f));
	ReleaseSurface->SetVisibility(Age < FirstShot || (Since >= 0.0f && Since < .25f));
	ReleaseMaterial->SetScalarParameterValue(TEXT("Age"), Age);
	ReleaseMaterial->SetScalarParameterValue(TEXT("ShotAge"), Since);
	if (DetailPreviewStyle >= 6) { UpdateArtPresentation(Age, Since, ReleaseOrigin); }
	if (ArsenalStudy.IsValid() && ArsenalStudy->UsesRecraftedPresentation())
	{
		// 좌표는 그대로 실탄 출발점으로 쓰되, 중복된 옛 광륜은 새 광면 아래에 쌓지 않는다.
		for (UStaticMeshComponent* Surface : PressureSurfaces) { Surface->SetVisibility(false); }
		for (UStaticMeshComponent* Surface : FlowSurfaces) { Surface->SetVisibility(false); }
		for (UStaticMeshComponent* Surface : ChargeArrows) { Surface->SetVisibility(false); }
		for (UStaticMeshComponent* Surface : ArtSurfaces) { Surface->SetVisibility(false); }
		ReleaseSurface->SetVisibility(false);
	}
	if (Since > .065f)
	{
		for (UParticleSystemComponent* Particle : MuzzleParticles)
		{
			if (IsValid(Particle) && Particle->IsActive()) { Particle->DeactivateSystem(); }
		}
	}
}

void ASparrowSharpVolley::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!bInitialized || !Caster.IsValid() || Caster->IsActorBeingDestroyed() || GetOwner() != Caster.Get() ||
		!Skills.IsValid() || Skills->GetOwner() != Caster.Get() || !Animation.IsValid()) { Destroy(); return; }
	const float Age = static_cast<float>(GetWorld()->GetTimeSeconds() - StartedAt);
	// 외부에서 자기 몽타주가 중단되면 아직 발사하지 않은 파동도 함께 취소한다.
	if (bAnimationStarted && WavesFired == 0 && Age < .56f && !Animation->Montage_IsPlaying(Montage)) { Destroy(); return; }
	if (WavesFired == 0 && Age + KINDA_SMALL_NUMBER >= FirstShot)
	{
		const int32 PreviousWaves = WavesFired;
		ReleaseWave();
		if (WavesFired == PreviousWaves) { Destroy(); return; }
	}
	UpdatePressure(Age);
}

void ASparrowSharpVolley::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (ArsenalStudy.IsValid()) { ArsenalStudy->Destroy(); }
	ArsenalStudy.Reset();
	if (Animation.IsValid() && Montage && Animation->Montage_IsActive(Montage))
	{
		Animation->Montage_Stop(.06f, Montage);
	}
	for (UParticleSystemComponent* Particle : MuzzleParticles)
	{
		if (IsValid(Particle)) { Particle->DeactivateSystem(); Particle->DestroyComponent(); }
	}
	MuzzleParticles.Reset();
	// 이미 날아간 화살은 USparrowSkillComponent::OwnedArrows가 수명/owner 전환을 관리한다.
	Super::EndPlay(EndPlayReason);
}
