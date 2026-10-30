#include "SparrowBackstepEcho.h"

#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/PoseableMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Particles/ParticleSystemComponent.h"
#include "SparrowSkillComponent.h"
#include "TimerManager.h"

ASparrowBackstepEcho::ASparrowBackstepEcho()
{
	PrimaryActorTick.bCanEverTick = true;
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("DeparturePoint")));
	Archer = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("AnchoredArcher"));
	Archer->SetupAttachment(RootComponent);
	Archer->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Archer->SetGenerateOverlapEvents(false);
	Archer->SetCanEverAffectNavigation(false);
	Archer->SetCastShadow(false);
	Archer->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	Tags.Add(TEXT("SparrowBackstepEcho"));
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
		Pose->ComponentTags.Add(TEXT("SparrowBackstepAfterimage"));
		MotionEchoes.Add(Pose);
		MotionAges.Add(-1.0f);
	}
}

bool ASparrowBackstepEcho::Initialize(ACharacter* InCharacter, USparrowSkillComponent* InSkills,
	UAnimMontage* Dodge, UAnimMontage* CapturedMontage, float CapturedPosition, float ReleaseDelay,
	bool bTransferShot, const FVector& Aim, const FVector& Destination)
{
	USkeletalMeshComponent* Source = InCharacter ? InCharacter->GetMesh() : nullptr;
	UAnimInstance* SourceAnim = Source ? Source->GetAnimInstance() : nullptr;
	UCharacterMovementComponent* Movement = InCharacter ? InCharacter->GetCharacterMovement() : nullptr;
	if (!Source || !SourceAnim || !Movement || !InSkills || !Dodge) { return false; }
	CharacterOwner = InCharacter;
	Skills = InSkills;
	CapturedAim = Aim;
	MoveStart = InCharacter->GetActorLocation();
	MoveEnd = Destination;
	MovementMontage = Dodge;
	EchoMontage = CapturedMontage;
	Archer->SetSkeletalMeshAsset(Source->GetSkeletalMeshAsset());
	Archer->SetRelativeTransform(Source->GetRelativeTransform());
	// 액터는 출발점에 고정하고 메시만 본체의 상대 위치와 회전을 유지한다.
	Archer->SetWorldTransform(Source->GetComponentTransform());
	Archer->bDisableClothSimulation = true;
	Archer->SetForcedLOD(1);
	UMaterialInterface* Material = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowAscensionEcho.M_SparrowAscensionEcho"));
	if (!Material) { return false; }
	EchoMaterial = UMaterialInstanceDynamic::Create(Material, this);
	EchoMaterial->SetVectorParameterValue(TEXT("BodyTint"), FLinearColor(0.75f, 0.52f, 0.12f));
	EchoMaterial->SetScalarParameterValue(TEXT("Visibility"), 1.0f);
	for (int32 Index = 0; Index < Archer->GetNumMaterials(); ++Index)
	{
		Archer->SetMaterial(Index, EchoMaterial);
		Archer->ShowMaterialSection(Index, Index, Index != 3 && Index != 7 && Source->IsMaterialSectionShown(Index, 0), 0);
	}
	UMaterialInterface* MotionSource = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowShadowPartner.M_SparrowShadowPartner"));
	if (!MotionSource) { return false; }
	for (UPoseableMeshComponent* Pose : MotionEchoes)
	{
		Pose->SetSkinnedAssetAndUpdate(Source->GetSkinnedAsset());
		Pose->SetUsingAbsoluteLocation(true);
		Pose->SetUsingAbsoluteRotation(true);
		Pose->SetUsingAbsoluteScale(true);
		Pose->SetForcedLOD(1);
		UMaterialInstanceDynamic* Fade = UMaterialInstanceDynamic::Create(MotionSource, this);
		Fade->SetVectorParameterValue(TEXT("BodyTint"), FLinearColor(1.65f, 0.90f, 0.12f));
		Fade->SetScalarParameterValue(TEXT("Visibility"), 0.0f);
		MotionMaterials.Add(Fade);
		for (int32 Index = 0; Index < Pose->GetNumMaterials(); ++Index)
		{
			Pose->SetMaterial(Index, Fade);
			Pose->ShowMaterialSection(Index, Index, Index != 3 && Index != 7 && Source->IsMaterialSectionShown(Index, 0), 0);
		}
	}
	if (CapturedMontage)
	{
		Archer->PlayAnimation(CapturedMontage, false);
		if (UAnimSingleNodeInstance* Node = Archer->GetSingleNodeInstance())
		{
			Node->SetRootMotionMode(ERootMotionMode::IgnoreRootMotion);
			Node->SetPosition(CapturedPosition, false);
		}
	}
	else
	{
		UAnimSequence* Ready = LoadObject<UAnimSequence>(nullptr,
			TEXT("/Game/ParagonSparrow/Characters/Heroes/Sparrow/Animations/RMB_Loop.RMB_Loop"));
		if (!Ready) { return false; }
		Archer->PlayAnimation(Ready, true);
		Archer->SetPosition(0.1f, false);
		Archer->SetPlayRate(0.0f);
	}
	MovingAnim = SourceAnim;
	PreviousRootMotion = SourceAnim->RootMotionMode;
	bPreviousOrientRotation = Movement->bOrientRotationToMovement;
	SourceAnim->SetRootMotionMode(ERootMotionMode::IgnoreRootMotion);
	Movement->bOrientRotationToMovement = false;
	Movement->StopMovementImmediately();
	if (InCharacter->GetController()) { InCharacter->GetController()->StopMovement(); }
	bMoving = true;
	const float DodgeRate = Dodge->GetPlayLength() / (MoveDuration + 0.04f);
	if (SourceAnim->Montage_Play(Dodge, DodgeRate, EMontagePlayReturnType::Duration) <= 0.0f)
	{
		FinishMovement();
		return false;
	}
	bShotPending = bTransferShot;
	if (bShotPending)
	{
		GetWorldTimerManager().SetTimer(ReleaseTimer, this, &ASparrowBackstepEcho::ReleaseCapturedShot,
			FMath::Max(0.001f, ReleaseDelay), false);
	}
	return true;
}

FVector ASparrowBackstepEcho::GetArrowOrigin() const
{
	return Archer->DoesSocketExist(TEXT("arrow_anchor")) ? Archer->GetSocketLocation(TEXT("arrow_anchor")) :
		MoveStart + GetActorForwardVector() * 55.0f + FVector(0.0f, 0.0f, 25.0f);
}

void ASparrowBackstepEcho::TrackEffect(UParticleSystemComponent* Effect)
{
	if (Effect) { Effects.Add(Effect); }
}

void ASparrowBackstepEcho::ReleaseCapturedShot()
{
	if (!bShotPending) { return; }
	bShotPending = false;
	if (Skills.IsValid() && CharacterOwner.IsValid() && !CharacterOwner->IsActorBeingDestroyed())
	{
		Skills->ReleaseAnchoredPiercingShot(this);
		++TransferredShots;
	}
}

void ASparrowBackstepEcho::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!CharacterOwner.IsValid() || CharacterOwner->IsActorBeingDestroyed() || !Skills.IsValid()) { Destroy(); return; }
	Age += DeltaSeconds;
	float MotionProgress = -1.0f;
	if (bMoving)
	{
		if (!MovingAnim.IsValid() || MovingAnim->Montage_GetIsStopped(MovementMontage) ||
			CharacterOwner->GetCharacterMovement()->MovementMode != MOVE_Walking)
		{
			FinishMovement();
		}
		else
		{
			const float Phase = FMath::Clamp(Age / MoveDuration, 0.0f, 1.0f);
			// 출발 즉시 거리를 벌리고 짧게 감속한다. 분신의 W 타이머는 이 배속과 독립적이다.
			const float Progress = 1.0f - FMath::Pow(1.0f - Phase, 3.0f);
			FHitResult Hit;
			CharacterOwner->SetActorLocation(FMath::Lerp(MoveStart, MoveEnd, Progress), true, &Hit);
			CharacterOwner->GetCharacterMovement()->StopMovementImmediately();
			// 쓸고 지나간 실제 안전 구간 안에서만 잔상을 남긴다. 벽 뒤로 잔상을 만들지 않는다.
			const float FullDistance = FVector::Dist(MoveStart, MoveEnd);
			MotionProgress = FullDistance > KINDA_SMALL_NUMBER ?
				FVector::Dist(MoveStart, CharacterOwner->GetActorLocation()) / FullDistance : 0.0f;
			if (Hit.bBlockingHit || Phase >= 1.0f) { FinishMovement(); }
		}
	}
	UpdateMotionEchoes(DeltaSeconds, MotionProgress);
	if (EchoMaterial)
	{
		const float Fade = FMath::Clamp((1.10f - Age) / 0.20f, 0.0f, 1.0f);
		EchoMaterial->SetScalarParameterValue(TEXT("Visibility"), Fade);
	}
}

void ASparrowBackstepEcho::UpdateMotionEchoes(float DeltaSeconds, float Progress)
{
	USkeletalMeshComponent* Source = CharacterOwner.IsValid() ? CharacterOwner->GetMesh() : nullptr;
	for (int32 Index = 0; Index < MotionEchoes.Num(); ++Index)
	{
		UPoseableMeshComponent* Pose = MotionEchoes[Index];
		if (MotionAges[Index] < 0.0f && Source && Progress >= (Index + 1) * 0.25f)
		{
			FTransform Snapshot = Source->GetComponentTransform();
			Snapshot.AddToTranslation(FMath::Lerp(MoveStart, MoveEnd, (Index + 1) * 0.25f) -
				CharacterOwner->GetActorLocation());
			Pose->SetWorldTransform(Snapshot);
			Pose->CopyPoseFromSkeletalComponent(Source);
			Pose->SetVisibility(true);
			MotionAges[Index] = 0.0f;
		}
		if (MotionAges[Index] >= 0.0f && MotionMaterials.IsValidIndex(Index))
		{
			MotionAges[Index] += DeltaSeconds;
			const float Fade = FMath::Square(FMath::Clamp(1.0f - MotionAges[Index] / 0.22f, 0.0f, 1.0f));
			MotionMaterials[Index]->SetScalarParameterValue(TEXT("Visibility"), Fade);
			Pose->SetVisibility(Fade > 0.002f);
		}
	}
}

void ASparrowBackstepEcho::FinishMovement()
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

void ASparrowBackstepEcho::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	FinishMovement();
	GetWorldTimerManager().ClearTimer(ReleaseTimer);
	for (const TWeakObjectPtr<UParticleSystemComponent>& Effect : Effects)
	{
		if (Effect.IsValid()) { Effect->DestroyComponent(); }
	}
	Super::EndPlay(EndPlayReason);
}
