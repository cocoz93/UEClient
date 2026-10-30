#include "CountessRuinVisual.h"

#include "Components/SceneComponent.h"
#include "Components/SplineMeshComponent.h"
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
	constexpr float SpikeZones[] = {140.0f, 360.0f, 580.0f};

	UParticleSystem* MakeRuinTemplate(UObject* Owner, const TCHAR* Path)
	{
		UParticleSystem* Source = LoadObject<UParticleSystem>(nullptr, Path);
		if (!Source) { return nullptr; }
		UParticleSystem* Runtime = DuplicateObject<UParticleSystem>(Source, Owner);
		Runtime->SetFlags(RF_Transient);
		Runtime->ClearFlags(RF_Public | RF_Standalone);
		// 실제 렌더 기록의 연기 몸체와 전방 혈색 파열만 고른다. 수백 개의
		// 검은 GPU 점/후방 불꽃/미세 돌과 넓은 암전·굴절 카드는 소유 복제본에서 제외한다.
		static const TSet<FName> GroundLayers = {
			TEXT("Smoke"), TEXT("FireSmoke_L"), TEXT("FireSmoke_R"), TEXT("SmokeColumn"),
			TEXT("SmokeSpears"), TEXT("Ground Linger Sparks")};
		static const TSet<FName> ContactLayers = {
			TEXT("SmokeUp_Dir"), TEXT("SmokeBack_Dir"), TEXT("Smoke"),
			TEXT("RedSpark"), TEXT("DirectionalSpark"), TEXT("TinyFlare")};
		const TSet<FName>& Layers = Source->GetFName() == TEXT("P_CountessBloodSealGround") ? GroundLayers : ContactLayers;
		Runtime->Emitters.RemoveAll([&Layers](UParticleEmitter* Emitter)
		{
			return !Emitter || !Layers.Contains(Emitter->EmitterName);
		});
		// 원본 광원도 제외해 조형의 명암을 보존한다. 공유 패키지는 변경하지 않는다.
		for (UParticleEmitter* Emitter : Runtime->Emitters)
		{
			if (!Emitter || !Emitter->IsIn(Runtime)) { return nullptr; }
			for (UParticleLODLevel* LOD : Emitter->LODLevels)
			{
				if (!LOD || !LOD->IsIn(Runtime)) { return nullptr; }
				LOD->Modules.RemoveAll([](UParticleModule* Module)
				{
					return Module && Module->IsA<UParticleModuleLightBase>();
				});
			}
			Emitter->UpdateModuleLists();
		}
		Runtime->BuildEmitters();
		UE_LOG(LogTemp, Display, TEXT("COUNTESS_RUIN template source=%s source_emitters=%d kept=%d owned=%d"),
			*Source->GetPathName(), Source->Emitters.Num(), Runtime->Emitters.Num(), Runtime->IsIn(Owner));
		return Runtime;
	}
}

ACountessRuinVisual::ACountessRuinVisual()
{
	PrimaryActorTick.bCanEverTick = true;
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("RuinRoot")));
	SetActorEnableCollision(false);
	SetCanBeDamaged(false);
	Tags.Add(TEXT("CountessRuinVisual"));
}

void ACountessRuinVisual::Initialize(ATopDownCombatCharacter* Source, ECountessRuinKind Kind,
	const FVector& Origin, const FVector& Direction, float Lifetime)
{
	if (bInitialized || !IsValid(Source) || !GetWorld() || Origin.ContainsNaN() || Direction.ContainsNaN())
	{
		Destroy();
		return;
	}
	Character = Source;
	RuinKind = Kind;
	Life = FMath::Clamp(Lifetime, .25f, 2.0f);
	FVector Forward = Direction.GetSafeNormal2D();
	if (Forward.IsNearlyZero()) { Forward = Source->GetActorForwardVector().GetSafeNormal2D(); }
	SetActorLocationAndRotation(Origin, Forward.Rotation());
	SetOwner(Source);
	SetLifeSpan(Life + .10f);
	// 원본 팩의 메시를 읽고 기존 전용 재질의 MID만 만든다. 공유 에셋은 수정하지 않는다.
	// 주 가시는 면마다 깊이가 다른 전용 입체 조형을 쓰고 원본 Fragment는 작은 파편에만 쓴다.
	UStaticMesh* Fragment = LoadObject<UStaticMesh>(nullptr,
		TEXT("/Game/ParagonAurora/FX/Meshes/Debris/SM_Aurora_Fragment.SM_Aurora_Fragment"));
	UStaticMesh* RuinShard = LoadObject<UStaticMesh>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/FX/SM_CountessRuinShard.SM_CountessRuinShard"));
	UStaticMesh* ClawBlade = LoadObject<UStaticMesh>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/FX/SM_CountessRuinClawBlade.SM_CountessRuinClawBlade"));
	UStaticMesh* Crest = LoadObject<UStaticMesh>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/QualityGate20261024/SM_CountessRuptureCrest.SM_CountessRuptureCrest"));
	UStaticMesh* Plane = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
	UStaticMesh* Sphere = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	UStaticMesh* Hand = LoadObject<UStaticMesh>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/Reference20261024/SM_CountessDemonicHand.SM_CountessDemonicHand"));
	UMaterialInterface* Fracture = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/QualityGate20261024/M_CountessFractureField.M_CountessFractureField"));
	UMaterialInterface* Obsidian = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/QualityGate20261024/M_CountessBloodObsidian.M_CountessBloodObsidian"));
	UMaterialInterface* RisingCut = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/QualityGate20261024/M_CountessRisingCut.M_CountessRisingCut"));
	UMaterialInterface* Plume = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/QualityGate20261024/M_CountessRupturePlume.M_CountessRupturePlume"));
	UMaterialInterface* HandMaterial = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/QualityGate20261024/M_CountessDemonPalm.M_CountessDemonPalm"));
	UMaterialInterface* Core = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessRuinShadow.M_CountessRuinShadow"));
	UMaterialInterface* Ink = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessExtraInkQuality2_20261021.M_CountessExtraInkQuality2_20261021"));
	ContactEffect = MakeRuinTemplate(this,
		TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessBloodSealBurst.P_CountessBloodSealBurst"));
	GroundEffect = MakeRuinTemplate(this,
		TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessBloodSealGround.P_CountessBloodSealGround"));
	if (!Fragment || !RuinShard || !ClawBlade || !Crest || !Plane || !Sphere || !Core || !Ink ||
		!ContactEffect || !GroundEffect || !Hand || !Fracture || !Obsidian || !RisingCut || !Plume || !HandMaterial)
	{
		UE_LOG(LogTemp, Warning, TEXT("COUNTESS_RUIN missing visual asset kind=%d"), static_cast<int32>(Kind));
		Destroy();
		return;
	}
	Meshes.Reserve(72);
	Materials.Reserve(72);
	Pieces.Reserve(72);
	Effects.Reserve(6);
	if (Kind == ECountessRuinKind::Spikes)
	{
		for (int32 Zone = 0; Zone < 3; ++Zone)
		{
			const float Delay = Zone * .12f;
			const FVector Center = Ground(FVector(SpikeZones[Zone], 0, 0));
			// 바닥 균열에서 불규칙한 입체 가시가 솟는다. 원형 외벽을 만들지 않는다.
			AddPiece(Plane, Fracture, EMotion::Field, Center + FVector(0, 0, 3), FVector::ForwardVector,
				FVector(395, 355, 1), Delay, Life - Delay);
			static const FVector Offsets[] = {
				FVector(-70, -54, 0), FVector(16, 12, 0), FVector(65, -88, 0), FVector(-22, 107, 0),
				FVector(106, 47, 0), FVector(-116, 33, 0), FVector(35, -132, 0)};
			static const float Lengths[] = {220, 105, 165, 85, 145, 115, 65};
			for (int32 Lane = 0; Lane < UE_ARRAY_COUNT(Offsets); ++Lane)
			{
				const FVector Offset = Offsets[Lane].RotateAngleAxis(Zone * 31.0f, FVector::UpVector);
				const FVector Radial = Offset.GetSafeNormal2D();
				const float Length = Lengths[Lane] * (1.0f + Zone * .035f);
				AddPiece(RuinShard, Obsidian, EMotion::Spike, Ground(Center + Offset),
					Radial * (.26f + (Lane % 3) * .13f) + FVector(0, 0, 1.0f),
					FVector(Length, 42.0f + (Lane % 3) * 9.0f, 36.0f), Delay + (Lane % 3) * .016f, .66f);
				AddPiece(Fragment, Obsidian, EMotion::Shard, Ground(Center + Offset * .68f) + FVector(0, 0, 15),
					Radial * .55f + FVector(0, 0, .55f), FVector(47 + (Lane % 2) * 20, 31, 24), Delay + .035f, .42f);
			}
			for (int32 Side : {-1, 1})
			{
				AddPiece(Fragment, Core, EMotion::Shard, Center + FVector(25, Side * 95, 40),
					FVector(.35f, Side * .85f, 1.0f), FVector(34, 23, 17), Delay + .035f, .55f);
			}
		}
	}
	else if (Kind == ECountessRuinKind::Claws)
	{
		// 손바닥·손가락이 먼저 솟고 같은 방향의 검격으로 이어진다. 손은 시각 전용이다.
		AddPiece(Hand, HandMaterial, EMotion::Hand, FVector(130, 0, 195), FVector::ForwardVector,
			FVector(330, 245, 105), 0, .52f);
		for (int32 Lane = 0; Lane < 3; ++Lane)
		{
			const float Side = (Lane - 1) * 99.0f;
			const float Delay = .16f + Lane * .045f;
			// 충분히 분할된 좁은 입체 날을 휜다. 저분할 쐐기의 큰 삼각 면이 곡선을 가리지 않게 한다.
			AddPiece(ClawBlade, RisingCut, EMotion::Slash, FVector(50, Side, 24), FVector::ForwardVector,
				FVector(520, 27, 13), Delay, .36f);
			const int32 ScarIndex = AddPiece(Plane, Ink, EMotion::Scar, Ground(FVector(310, Side, 0)) + FVector(0, 0, 3),
				FVector(1, .035f, 0), FVector(420, 12, 1), Delay + .025f, .42f);
			Materials[ScarIndex]->SetScalarParameterValue(TEXT("Opacity"), .32f);
			for (int32 Debris = 0; Debris < 2; ++Debris)
			{
				AddPiece(Fragment, Core, EMotion::Shard, FVector(440 + Debris * 35, Side, 40),
					FVector(.7f, (Debris == 0 ? -1.0f : 1.0f) * .4f, .75f), FVector(22, 9, 7), Delay + .09f, .4f);
			}
		}
	}
	else
	{
		// 중앙에서 위로 찢기는 검격과 바닥 파열을 나눈다. R의 가시 장판을 복제하지 않는다.
		AddPiece(Plane, Fracture, EMotion::Field, Ground(FVector::ZeroVector) + FVector(0, 0, 3),
			FVector::ForwardVector, FVector(430, 400, 1), 0, Life);
		AddPiece(Sphere, Core, EMotion::Core, FVector(0, 0, 36), FVector::UpVector,
			FVector(23, 21, 32), .06f, .35f);
		for (int32 Index = 0; Index < 3; ++Index)
		{
			const float Degrees = Index * 119.0f - 26.0f + (Index % 2) * 7.0f;
			const FVector Radial = FVector::ForwardVector.RotateAngleAxis(Degrees, FVector::UpVector);
			const float Delay = .045f + (Index % 3) * .024f;
			const FVector Base = Ground(Radial * 22.0f) + FVector(0, 0, 6);
			AddPiece(ClawBlade, RisingCut, EMotion::RiseCut, Base, Radial,
				FVector(135 + (Index % 3) * 17, 33, 12), Delay, .36f + (Index % 2) * .05f);
			AddPiece(Crest, Plume, EMotion::Plume, Base + Radial * 14.0f + FVector(0, 0, 74 + Index * 7),
				Radial, FVector(132 + Index * 11, 54, 148 + Index * 14), .025f + Index * .022f, .48f);
			AddPiece(Plane, Ink, EMotion::Scar, Ground(Radial * 120) + FVector(0, 0, 3), Radial,
				FVector(190, 14, 1), 0, Life);
			AddPiece(Fragment, Core, EMotion::Shard, Radial * 95 + FVector(0, 0, 40),
				Radial * .8f + FVector::UpVector, FVector(25 + (Index % 2) * 9, 15, 12), Delay + .045f, .6f);
		}
	}
	bInitialized = true;
	UpdatePieces();
	UpdateBursts();
	UE_LOG(LogTemp, Display, TEXT("COUNTESS_RUIN initialized kind=%d parts=%d life=%.3f origin=%s"),
		static_cast<int32>(Kind), Pieces.Num(), Life, *Origin.ToCompactString());
}

FVector ACountessRuinVisual::Ground(const FVector& Local) const
{
	const FVector World = GetActorTransform().TransformPosition(Local);
	FCollisionQueryParams Query(SCENE_QUERY_STAT(CountessRuinGround), false, GetOwner());
	Query.AddIgnoredActor(this);
	FHitResult Hit;
	if (GetWorld()->LineTraceSingleByObjectType(Hit, World + FVector(0, 0, 70), World - FVector(0, 0, 150),
		FCollisionObjectQueryParams(ECC_WorldStatic), Query) && Hit.ImpactNormal.Z > .65f)
	{
		return GetActorTransform().InverseTransformPosition(Hit.ImpactPoint);
	}
	return Local;
}

int32 ACountessRuinVisual::AddPiece(UStaticMesh* Mesh, UMaterialInterface* Material, EMotion Motion,
	const FVector& Base, const FVector& Direction, const FVector& Size, float Delay, float Span, float SourceForward)
{
	UStaticMeshComponent* Part = (Motion == EMotion::Slash || Motion == EMotion::RiseCut) ?
		NewObject<USplineMeshComponent>(this) : NewObject<UStaticMeshComponent>(this);
	// 등록 전부터 충돌과 내비 영향을 끈다. 시각 메시가 이동 경로를 바꾸지 않게 한다.
	Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Part->SetGenerateOverlapEvents(false);
	Part->SetCanEverAffectNavigation(false);
	Part->SetMobility(EComponentMobility::Movable);
	Part->SetupAttachment(GetRootComponent());
	Part->SetStaticMesh(Mesh);
	Part->SetCastShadow(false);
	Part->SetReceivesDecals(false);
	Part->SetVisibility(false);
	Part->ComponentTags.Add(TEXT("CountessRuinPart"));
	if (USplineMeshComponent* Claw = Cast<USplineMeshComponent>(Part))
	{
		Claw->SetForwardAxis(ESplineMeshAxis::X, false);
		Claw->SetSplineUpDir(FVector::UpVector, false);
	}
	Part->RegisterComponent();
	UMaterialInstanceDynamic* MID = UMaterialInstanceDynamic::Create(Material, this);
	MID->SetScalarParameterValue(TEXT("CloneOpacity"), .98f);
	MID->SetScalarParameterValue(TEXT("DissolveStart"), GetWorld()->GetTimeSeconds() + Delay + Span * .64f);
	MID->SetScalarParameterValue(TEXT("DissolveDuration"), FMath::Max(.06f, Span * .36f));
	MID->SetScalarParameterValue(TEXT("RuinEnergy"), Motion == EMotion::Field ? .55f : 1.0f);
	MID->SetScalarParameterValue(TEXT("RuinProfile"), Motion == EMotion::Field ? 0.0f :
		(Motion == EMotion::Slash ? 2.0f : (Motion == EMotion::Core ? 3.0f : 1.0f)));
	MID->SetScalarParameterValue(TEXT("RuinErode"), 0.0f);
	MID->SetScalarParameterValue(TEXT("TideOpacity"), 1.0f);
	MID->SetScalarParameterValue(TEXT("TideErode"), 0.0f);
	MID->SetVectorParameterValue(TEXT("TideTint"), FLinearColor::White);
	MID->SetVectorParameterValue(TEXT("TidePhase"), FLinearColor(.5f, 1, 1, 1));
	MID->SetVectorParameterValue(TEXT("Color2"), FLinearColor(.028f, .001f, .005f));
	MID->SetVectorParameterValue(TEXT("Color3"), FLinearColor(.009f, .002f, .003f));
	MID->SetScalarParameterValue(TEXT("Card"), Motion == EMotion::Scar ? 1.0f : 0.0f);
	MID->SetScalarParameterValue(TEXT("Shape"), 4.0f);
	MID->SetScalarParameterValue(TEXT("Seed"), Pieces.Num() * 1.371f);
	MID->SetScalarParameterValue(TEXT("Fade"), 1.0f);
	MID->SetScalarParameterValue(TEXT("Opacity"), Motion == EMotion::Scar ? .50f : 1.0f);
	for (int32 Slot = 0; Slot < FMath::Max(1, Part->GetNumMaterials()); ++Slot) { Part->SetMaterial(Slot, MID); }
	FPiece Piece;
	Piece.Base = Base;
	Piece.Direction = Direction.GetSafeNormal();
	Piece.Size = Size;
	Piece.Delay = Delay;
	Piece.Span = FMath::Max(.1f, Span);
	Piece.Motion = Motion;
	Piece.Seed = Pieces.Num() * 1.371f;
	const FBox Box = Mesh->GetBoundingBox();
	Piece.SourceCenter = Box.GetCenter();
	Piece.SourceSize = Box.GetSize().ComponentMax(FVector(.1f));
	for (int32 Axis = 1; Axis < 3; ++Axis)
	{
		if (Piece.SourceSize[Axis] > Piece.SourceSize[Piece.LongAxis]) { Piece.LongAxis = Axis; }
	}
	Piece.WideAxis = (Piece.LongAxis + 1) % 3;
	for (int32 Axis = 0; Axis < 3; ++Axis)
	{
		if (Axis != Piece.LongAxis && Piece.SourceSize[Axis] > Piece.SourceSize[Piece.WideAxis]) { Piece.WideAxis = Axis; }
	}
	FVector Long = FVector::ZeroVector, Wide = FVector::ZeroVector;
	Long[Piece.LongAxis] = SourceForward;
	Wide[Piece.WideAxis] = 1.0f;
	FVector Side = FVector::CrossProduct(FVector::UpVector, Piece.Direction).GetSafeNormal();
	if (Side.IsNearlyZero()) { Side = FVector::RightVector; }
	Piece.Basis = FRotationMatrix::MakeFromXY(Piece.Direction, Side).ToQuat() *
		FRotationMatrix::MakeFromXY(Long, Wide).ToQuat().Inverse();
	if (Motion == EMotion::Spike)
	{
		Piece.Basis = FQuat(Piece.Direction, FMath::Fmod(Piece.Seed, 1.0f) * .9f - .45f) * Piece.Basis;
	}
	Meshes.Add(Part);
	Materials.Add(MID);
	return Pieces.Add(Piece);
}

void ACountessRuinVisual::UpdatePieces()
{
	for (int32 Index = 0; Index < Pieces.Num(); ++Index)
	{
		const FPiece& Piece = Pieces[Index];
		UStaticMeshComponent* Part = Meshes[Index];
		UMaterialInstanceDynamic* MID = Materials[Index];
		const float Elapsed = Age - Piece.Delay;
		if (Elapsed < 0.0f || Elapsed >= Piece.Span) { Part->SetVisibility(false); continue; }
		const float Rise = FMath::SmoothStep(0.0f, Piece.Motion == EMotion::Slash ? .055f : .105f, Elapsed);
		const float Fade = 1.0f - FMath::SmoothStep(Piece.Span * .58f, Piece.Span, Elapsed);
		FVector Center = Piece.Base;
		FVector Size = Piece.Size;
		FQuat Rotation = Piece.Basis;
		if (Piece.Motion == EMotion::Spike)
		{
			Size.X *= FMath::Max(.015f, Rise);
			Center += Piece.Direction * Size.X * .5f - FVector(0, 0, 13.0f + (1.0f - Fade) * 35.0f);
		}
		else if (Piece.Motion == EMotion::Slash)
		{
			Size.X *= .35f + .65f * Rise;
			Size.Y *= (.50f + .50f * Rise) * (.6f + .4f * Fade);
		}
		else if (Piece.Motion == EMotion::Shard)
		{
			const float Flight = Elapsed / Piece.Span;
			Center += Piece.Direction * (Flight * 86.0f) + FVector(0, 0, 35.0f * FMath::Sin(Flight * PI) - 62.0f * Flight * Flight);
			Rotation = FQuat(Piece.Direction, Elapsed * (4.0f + FMath::Fmod(Piece.Seed, 3.0f))) * Rotation;
			Size *= .55f + .45f * Rise;
		}
		else if (Piece.Motion == EMotion::Field)
		{
			Size *= .70f + .30f * Rise;
		}
		else if (Piece.Motion == EMotion::Core)
		{
			Size *= (.65f + .35f * Rise) * (.9f + .1f * FMath::Sin(Elapsed * 29.0f));
		}
		else if (Piece.Motion == EMotion::Hand)
		{
			const float Strike = FMath::SmoothStep(.12f, .34f, Elapsed);
			Center += FVector(Strike * 235.0f, 0, -Strike * 135.0f);
			Rotation = FRotator(FMath::Lerp(58.0f, -28.0f, Strike), -6.0f + 14.0f * Strike, 5.0f).Quaternion();
			Size *= .75f + .25f * Rise;
		}
		else if (Piece.Motion == EMotion::RiseCut)
		{
			Size.X *= .22f + .78f * Rise;
			Size.Y *= (.45f + .55f * Rise) * (.55f + .45f * Fade);
			Center.Z += 75.0f * Elapsed;
		}
		else if (Piece.Motion == EMotion::Plume)
		{
			Size.X *= .65f + .35f * Rise;
			Size.Z *= .25f + .75f * Rise;
			Center.Z += FMath::Max(0.0f, Elapsed - .14f) * 65.0f - (Piece.Size.Z - Size.Z) * .5f;
			Rotation = Piece.Direction.Rotation().Quaternion();
		}
		if (USplineMeshComponent* Claw = Cast<USplineMeshComponent>(Part))
		{
			// 분할된 날의 X축을 곡선에 연결하며 전방/후방 양끝은 실제 기하로 가늘게 닫힌다.
			const FVector2D CrossScale(Size.Y / Piece.SourceSize.Y, Size.Z / Piece.SourceSize.Z);
			const FVector2D CrossOffset(-Piece.SourceCenter.Y * CrossScale.X, -Piece.SourceCenter.Z * CrossScale.Y);
			Claw->SetStartScale(CrossScale, false);
			Claw->SetEndScale(CrossScale, false);
			Claw->SetStartOffset(CrossOffset, false);
			Claw->SetEndOffset(CrossOffset, false);
			if (Piece.Motion == EMotion::RiseCut)
			{
				Claw->SetStartAndEnd(FVector(-22, 0, 0), FVector(Size.X * 1.6f, 0, Size.X * .25f),
					FVector(Size.X * .63f, 0, Size.X * 1.30f), FVector(-Size.X * .25f, 0, Size.X * 1.60f), true);
			}
			else
			{
				Claw->SetStartAndEnd(FVector(Size.X, 0, 5), FVector(-Size.X, 55, 420),
					FVector(0, 0, 62), FVector(-Size.X, -55, -180), true);
			}
			Claw->SetRelativeTransform(FTransform(Piece.Direction.Rotation(), Center, FVector::OneVector));
		}
		else
		{
			FVector Scale;
			if (Piece.Motion == EMotion::Field || Piece.Motion == EMotion::Hand || Piece.Motion == EMotion::Plume)
			{
				Scale = Size / Piece.SourceSize;
				if (Piece.Motion == EMotion::Field) { Rotation = Piece.Direction.Rotation().Quaternion(); }
			}
			else
			{
				for (int32 Axis = 0; Axis < 3; ++Axis)
				{
					Scale[Axis] = (Axis == Piece.LongAxis ? Size.X : (Axis == Piece.WideAxis ? Size.Y : Size.Z)) / Piece.SourceSize[Axis];
				}
			}
			Part->SetRelativeTransform(FTransform(Rotation, Center - Rotation.RotateVector(Piece.SourceCenter * Scale), Scale));
		}
		Part->SetVisibility(Rise > .002f && Fade > .002f);
		MID->SetScalarParameterValue(TEXT("CloneOpacity"), .98f * Rise * FMath::Sqrt(Fade));
		MID->SetScalarParameterValue(TEXT("RuinPulse"), 1.0f - FMath::Clamp(Elapsed / .18f, 0.0f, 1.0f));
		MID->SetScalarParameterValue(TEXT("RuinErode"), 1.0f - Fade);
		MID->SetScalarParameterValue(TEXT("ReferenceAge"), Elapsed);
		MID->SetScalarParameterValue(TEXT("TideOpacity"), Fade);
		MID->SetScalarParameterValue(TEXT("TideErode"), 1.0f - Fade);
		MID->SetScalarParameterValue(TEXT("Fade"), Fade * Rise);
		MID->SetScalarParameterValue(TEXT("Pulse"), 1.0f - FMath::Clamp(Elapsed / .18f, 0.0f, 1.0f));
	}
}

void ACountessRuinVisual::Pulse(UParticleSystem* Asset, const FVector& Local, float Scale)
{
	if (!Asset || Effects.Num() >= 6) { return; }
	UParticleSystemComponent* FX = NewObject<UParticleSystemComponent>(this);
	FX->SetAutoActivate(false);
	FX->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	FX->SetGenerateOverlapEvents(false);
	FX->SetCanEverAffectNavigation(false);
	FX->SetupAttachment(GetRootComponent());
	FX->SetTemplate(Asset);
	FX->SetRelativeLocation(Local);
	FX->SetRelativeScale3D(FVector(Scale));
	FX->SetAbsolute(false, false, false);
	FX->bAutoDestroy = true;
	FX->bOverrideLODMethod = true;
	FX->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
	FX->ComponentTags.Add(TEXT("CountessRuinPulse"));
	FX->RegisterComponent();
	FX->SetLODLevel(0);
	FX->ActivateSystem(true);
	FX->SetLODLevel(0);
	Effects.Add(FX);
	UE_LOG(LogTemp, Display, TEXT("COUNTESS_RUIN pulse kind=%d age=%.3f template=%s owned=%d scale=%.2f"),
		static_cast<int32>(RuinKind), Age, *Asset->GetPathName(), Asset->IsIn(this), Scale);
}

void ACountessRuinVisual::UpdateBursts()
{
	if (RuinKind == ECountessRuinKind::Spikes)
	{
		while (BurstStage < 6)
		{
			const int32 Zone = BurstStage / 2;
			const bool bContact = BurstStage % 2 != 0;
			if (Age < Zone * .12f + (bContact ? .08f : 0.0f)) { break; }
			const FVector Base = Ground(FVector(SpikeZones[Zone], 0, 0));
			Pulse(bContact ? ContactEffect : GroundEffect,
				Base + FVector(0, 0, bContact ? 32.0f : 2.0f), bContact ? .55f : .66f);
			++BurstStage;
		}
	}
	else if (RuinKind == ECountessRuinKind::Claws)
	{
		while (BurstStage < 3 && Age >= .21f + BurstStage * .045f)
		{
			Pulse(ContactEffect, FVector(475, (BurstStage - 1) * 99, 48), .36f);
			++BurstStage;
		}
	}
	else if (BurstStage == 0)
	{
		Pulse(GroundEffect, FVector(0, 0, 3), .62f);
		++BurstStage;
	}
	else if (BurstStage == 1 && Age >= .12f)
	{
		Pulse(ContactEffect, FVector(0, 0, 36), .64f);
		++BurstStage;
	}
}

void ACountessRuinVisual::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!bInitialized) { return; }
	if (!Character.IsValid() || Character->IsActorBeingDestroyed()) { Destroy(); return; }
	Age += FMath::Max(DeltaSeconds, 0.0f);
	if (Age >= Life) { Destroy(); return; }
	UpdatePieces();
	UpdateBursts();
}

void ACountessRuinVisual::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	for (UParticleSystemComponent* FX : Effects)
	{
		if (IsValid(FX)) { FX->DeactivateSystem(); FX->DestroyComponent(); }
	}
	Super::EndPlay(EndPlayReason);
}
