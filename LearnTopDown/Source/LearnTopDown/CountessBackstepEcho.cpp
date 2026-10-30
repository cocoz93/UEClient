#include "CountessBackstepEcho.h"

#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "CountessSkillComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "TimerManager.h"

ACountessBackstepEcho::ACountessBackstepEcho()
{
	PrimaryActorTick.bCanEverTick = true;
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("DeparturePoint")));
	Departure = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("AnchoredCountess"));
	Departure->SetupAttachment(RootComponent);
	Departure->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Departure->SetGenerateOverlapEvents(false);
	Departure->SetCanEverAffectNavigation(false);
	Departure->SetCastShadow(false);
	Departure->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	Departure->ComponentTags.Add(TEXT("CountessBackstepDeparture"));
	Tags.Add(TEXT("CountessBackstepEcho"));
	SetActorEnableCollision(false);
	SetCanBeDamaged(false);
	InitialLifeSpan = 1.10f;
	for (int32 Index = 0; Index < 3; ++Index)
	{
		UPoseableMeshComponent* Pose = CreateDefaultSubobject<UPoseableMeshComponent>(
			*FString::Printf(TEXT("MotionAfterimage%d"), Index));
		Pose->SetupAttachment(RootComponent);
		Pose->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Pose->SetGenerateOverlapEvents(false);
		Pose->SetCanEverAffectNavigation(false);
		Pose->SetCastShadow(false);
		Pose->SetVisibility(false);
		Pose->ComponentTags.Add(TEXT("CountessBackstepAfterimage"));
		MotionEchoes.Add(Pose);
		MotionAges.Add(-1.0f);
	}
}

bool ACountessBackstepEcho::Initialize(ACharacter* InCharacter, UCountessSkillComponent* InSkills,
	UAnimMontage* Dodge, UAnimMontage* Captured, float CapturedPosition, float CapturedRate,
	float ReleaseDelay, bool bTransferSiphon, bool bDetailedSiphon, const FVector& Destination)
{
	USkeletalMeshComponent* Source = InCharacter ? InCharacter->GetMesh() : nullptr;
	UAnimInstance* Anim = Source ? Source->GetAnimInstance() : nullptr;
	UCharacterMovementComponent* Movement = InCharacter ? InCharacter->GetCharacterMovement() : nullptr;
	UMaterialInterface* Material = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessQualityMotionEcho.M_CountessQualityMotionEcho"));
	if (!Material) { Material = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessEShadowDissolve.M_CountessEShadowDissolve")); }
	UAnimSequence* Idle = Captured ? nullptr : LoadObject<UAnimSequence>(nullptr,
		TEXT("/Game/ParagonCountess/Characters/Heroes/Countess/Animations/Idle_Pose.Idle_Pose"));
	if (!Source || !Anim || !Movement || !InSkills || !Dodge || !Material || (!Captured && !Idle)) { return false; }
	CharacterOwner = InCharacter;
	Skills = InSkills;
	MovingAnim = Anim;
	MovementMontage = Dodge;
	MoveStart = InCharacter->GetActorLocation();
	MoveEnd = Destination;
	EchoPosition = CapturedPosition;
	EchoRate = Captured ? CapturedRate : 0.0f;
	bCapturedDetailed = bDetailedSiphon;
	// 가장 느린 V 배속에서도 원래 예약 시각 뒤에 소멸할 시간을 보장한다.
	const float LifeSeconds = FMath::Max(1.10f, bTransferSiphon ? ReleaseDelay + 0.22f : 1.10f);
	DepartureLife = LifeSeconds;
	DepartureFadeStart = bTransferSiphon ? FMath::Max(.08f, ReleaseDelay - .12f) : .08f;
	SetLifeSpan(LifeSeconds);
	Departure->SetSkeletalMeshAsset(Source->GetSkeletalMeshAsset());
	Departure->SetWorldTransform(Source->GetComponentTransform());
	Departure->bDisableClothSimulation = true;
	Departure->SetForcedLOD(1);
	UMaterialInterface* DepartureSurface = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/Reference20261024/M_CountessDepartureInk.M_CountessDepartureInk"));
	UMaterialInstanceDynamic* Ink = UMaterialInstanceDynamic::Create(DepartureSurface ? DepartureSurface : Material, this);
	DepartureMaterial = Ink;
	Ink->SetScalarParameterValue(TEXT("CloneOpacity"), .74f);
	const FVector Travel = (Destination - MoveStart).GetSafeNormal();
	Ink->SetVectorParameterValue(TEXT("EchoDirection"), FLinearColor(-Travel.X, -Travel.Y, .5f));
	// 이동을 마친 직후부터 표면이 천천히 찢어진다. V 인계 대기는 그대로 두고 시각적인 몸체만 흩어진다.
	Ink->SetScalarParameterValue(TEXT("DissolveStart"), GetWorld()->GetTimeSeconds() + DepartureFadeStart);
	Ink->SetScalarParameterValue(TEXT("DissolveDuration"), FMath::Max(.18f, LifeSeconds - DepartureFadeStart - .03f));
	for (int32 Index = 0; Index < Departure->GetNumMaterials(); ++Index) { Departure->SetMaterial(Index, Ink); }
	Departure->PlayAnimation(Captured ? static_cast<UAnimationAsset*>(Captured) : Idle, false);
	Departure->SetPlayRate(0.0f);
	if (UAnimSingleNodeInstance* Node = Departure->GetSingleNodeInstance())
	{
		Node->SetRootMotionMode(ERootMotionMode::IgnoreRootMotion);
		Node->SetPosition(EchoPosition, false);
	}
	Departure->TickAnimation(0.0f, false);
	Departure->RefreshBoneTransforms();
	for (UPoseableMeshComponent* Pose : MotionEchoes)
	{
		Pose->SetSkinnedAssetAndUpdate(Source->GetSkinnedAsset());
		Pose->SetUsingAbsoluteLocation(true);
		Pose->SetUsingAbsoluteRotation(true);
		Pose->SetUsingAbsoluteScale(true);
		Pose->SetForcedLOD(1);
		UMaterialInstanceDynamic* Fade = UMaterialInstanceDynamic::Create(Material, this);
		Fade->SetScalarParameterValue(TEXT("CloneOpacity"), .46f - MotionMaterials.Num() * .09f);
		Fade->SetVectorParameterValue(TEXT("EchoDirection"), FLinearColor(-Travel.X, -Travel.Y, .35f));
		Fade->SetScalarParameterValue(TEXT("DissolveStart"), GetWorld()->GetTimeSeconds() + 1000.0f);
		Fade->SetScalarParameterValue(TEXT("DissolveDuration"), 0.22f);
		MotionMaterials.Add(Fade);
		for (int32 Index = 0; Index < Pose->GetNumMaterials(); ++Index) { Pose->SetMaterial(Index, Fade); }
	}
	PreviousRootMotion = Anim->RootMotionMode;
	bPreviousOrientRotation = Movement->bOrientRotationToMovement;
	Anim->SetRootMotionMode(ERootMotionMode::IgnoreRootMotion);
	Movement->bOrientRotationToMovement = false;
	Movement->StopMovementImmediately();
	if (InCharacter->GetController()) { InCharacter->GetController()->StopMovement(); }
	bMoving = true;
	const float Rate = Dodge->GetPlayLength() / (MoveDuration + 0.04f);
	if (Anim->Montage_Play(Dodge, Rate, EMontagePlayReturnType::Duration) <= 0.0f)
	{
		FinishMovement();
		return false;
	}
	bShotPending = bTransferSiphon;
	if (bShotPending)
	{
		GetWorldTimerManager().SetTimer(ReleaseTimer, this, &ACountessBackstepEcho::ReleaseCapturedSiphon,
			FMath::Max(0.001f, ReleaseDelay), false);
	}
	return true;
}

void ACountessBackstepEcho::ReleaseCapturedSiphon()
{
	if (!bShotPending) { return; }
	bShotPending = false;
	if (CharacterOwner.IsValid() && !CharacterOwner->IsActorBeingDestroyed() && Skills.IsValid())
	{
		Skills->ReleaseAnchoredBladeSiphon(this);
		++TransferredActions;
	}
}

void ACountessBackstepEcho::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!CharacterOwner.IsValid() || CharacterOwner->IsActorBeingDestroyed() || !Skills.IsValid()) { Destroy(); return; }
	Age += DeltaSeconds;
	float MotionProgress = -1.0f;
	if (bMoving)
	{
		USkeletalMeshComponent* Source = CharacterOwner->GetMesh();
		if (!MovingAnim.IsValid() || !Source || Source->GetAnimInstance() != MovingAnim.Get() ||
			MovingAnim->Montage_GetIsStopped(MovementMontage) ||
			CharacterOwner->GetCharacterMovement()->MovementMode != MOVE_Walking)
		{
			FinishMovement();
		}
		else
		{
			const float Phase = FMath::Clamp(Age / MoveDuration, 0.0f, 1.0f);
			const float Progress = 1.0f - FMath::Pow(1.0f - Phase, 3.0f);
			FHitResult Hit;
			CharacterOwner->SetActorLocation(FMath::Lerp(MoveStart, MoveEnd, Progress), true, &Hit);
			CharacterOwner->GetCharacterMovement()->StopMovementImmediately();
			const float FullDistance = FVector::Dist(MoveStart, MoveEnd);
			MotionProgress = FullDistance > KINDA_SMALL_NUMBER ?
				FVector::Dist(MoveStart, CharacterOwner->GetActorLocation()) / FullDistance : 0.0f;
			if (Hit.bBlockingHit || Phase >= 1.0f) { FinishMovement(); }
		}
	}
	// 수동 포즈 진행은 애니메이션 Notify를 재발동시키지 않는다. 피해는 원래 V 예약 한 번만 소유한다.
	if (UAnimSingleNodeInstance* Node = Departure->GetSingleNodeInstance())
	{
		Node->SetPosition(FMath::Min(EchoPosition + Age * EchoRate, Node->GetLength()), false);
		Departure->TickAnimation(0.0f, false);
		Departure->RefreshBoneTransforms();
	}
	UpdateMotionEchoes(DeltaSeconds, MotionProgress);
	if (DepartureMaterial)
	{
		const float Fade = FMath::SmoothStep(DepartureFadeStart, DepartureLife - .035f, Age);
		DepartureMaterial->SetScalarParameterValue(TEXT("CloneOpacity"), FMath::Lerp(.74f, .10f, Fade));
	}
}

void ACountessBackstepEcho::UpdateMotionEchoes(float DeltaSeconds, float Progress)
{
	USkeletalMeshComponent* Source = CharacterOwner.IsValid() ? CharacterOwner->GetMesh() : nullptr;
	for (int32 Index = 0; Index < MotionEchoes.Num(); ++Index)
	{
		UPoseableMeshComponent* Pose = MotionEchoes[Index];
		if (MotionAges[Index] < 0.0f && Source && Progress >= (Index + 1) * 0.25f)
		{
			FTransform Snapshot = Source->GetComponentTransform();
			Snapshot.AddToTranslation(FMath::Lerp(MoveStart, MoveEnd, (Index + 1) * 0.25f) - CharacterOwner->GetActorLocation());
			Pose->SetWorldTransform(Snapshot);
			Pose->CopyPoseFromSkeletalComponent(Source);
			Pose->RefreshBoneTransforms();
			Pose->SetVisibility(true);
			MotionMaterials[Index]->SetScalarParameterValue(TEXT("DissolveStart"), GetWorld()->GetTimeSeconds());
			MotionAges[Index] = 0.0f;
		}
		if (MotionAges[Index] >= 0.0f)
		{
			MotionAges[Index] += DeltaSeconds;
			Pose->SetVisibility(MotionAges[Index] < 0.22f);
		}
	}
}

void ACountessBackstepEcho::FinishMovement()
{
	if (!bMoving) { return; }
	bMoving = false;
	if (MovingAnim.IsValid())
	{
		MovingAnim->Montage_Stop(0.025f, MovementMontage);
		MovingAnim->SetRootMotionMode(PreviousRootMotion);
	}
	if (CharacterOwner.IsValid() && CharacterOwner->GetCharacterMovement())
	{
		CharacterOwner->GetCharacterMovement()->bOrientRotationToMovement = bPreviousOrientRotation;
		CharacterOwner->GetCharacterMovement()->StopMovementImmediately();
	}
}

void ACountessBackstepEcho::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	FinishMovement();
	GetWorldTimerManager().ClearTimer(ReleaseTimer);
	Super::EndPlay(EndPlayReason);
}
