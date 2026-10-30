#include "SparrowGoldRoll.h"
#include "SparrowHarmonyFX.h"

#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Components/CapsuleComponent.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "SparrowAscension.h"

ASparrowGoldRoll::ASparrowGoldRoll()
{
	PrimaryActorTick.bCanEverTick = true;
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("RollRoot")));
	RollSilhouette = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("RollSilhouette"));
	RollSilhouette->SetupAttachment(RootComponent);
	RollSilhouette->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	RollSilhouette->SetGenerateOverlapEvents(false);
	RollSilhouette->SetCanEverAffectNavigation(false);
	RollSilhouette->SetCastShadow(false);
	RollSilhouette->SetVisibility(false);
	RollSilhouette->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	RollSilhouette->ComponentTags.Add(TEXT("SparrowGoldRoll"));
	TransitionSilhouette = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("RollBodyTransition"));
	TransitionSilhouette->SetupAttachment(RootComponent);
	TransitionSilhouette->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	TransitionSilhouette->SetGenerateOverlapEvents(false);
	TransitionSilhouette->SetCanEverAffectNavigation(false);
	TransitionSilhouette->SetCastShadow(false);
	TransitionSilhouette->SetVisibility(false);
	TransitionSilhouette->bDisableClothSimulation = true;
	TransitionSilhouette->ComponentTags.Add(TEXT("SparrowGoldRollTransition"));
	for (int32 Index = 0; Index < 5; ++Index)
	{
		UPoseableMeshComponent* Echo = CreateDefaultSubobject<UPoseableMeshComponent>(
			*FString::Printf(TEXT("RollAfterimage%d"), Index));
		Echo->SetupAttachment(RootComponent);
		Echo->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Echo->SetGenerateOverlapEvents(false);
		Echo->SetCanEverAffectNavigation(false);
		Echo->SetCastShadow(false);
		Echo->SetVisibility(false);
		Echo->ComponentTags.Add(TEXT("SparrowGoldRollAfterimage"));
		Afterimages.Add(Echo);
		AfterimageBirths.Add(-1.0f);
	}
	Tags.Add(TEXT("SparrowGoldRollActor"));
	SetCanBeDamaged(false);
}

bool ASparrowGoldRoll::Initialize(ACharacter* InCharacter, const FVector& Destination, const FVector& Direction, bool bInTeleport)
{
	USkeletalMeshComponent* Source = InCharacter ? InCharacter->GetMesh() : nullptr;
	UAnimInstance* Anim = Source ? Source->GetAnimInstance() : nullptr;
	UCharacterMovementComponent* Movement = InCharacter ? InCharacter->GetCharacterMovement() : nullptr;
	USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr,
		TEXT("/Game/TopDown/Characters/Sparrow/Mobility/Quaternius/SK_QuaterniusRoll.SK_QuaterniusRoll"));
	UAnimSequence* Roll = LoadObject<UAnimSequence>(nullptr,
		TEXT("/Game/TopDown/Characters/Sparrow/Mobility/Quaternius/AS_QuaterniusRoll.AS_QuaterniusRoll"));
	UMaterialInterface* Gold = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowRollBlend.M_SparrowRollBlend"));
	if (!Source || !Anim || !Movement || !Mesh || !Roll || !Gold ||
		Roll->GetSkeleton() != Mesh->GetSkeleton() || Roll->GetPlayLength() <= KINDA_SMALL_NUMBER) { return false; }
	CharacterOwner = InCharacter;
	bTeleport = bInTeleport;
	OwnerAnim = Anim;
	MoveStart = InCharacter->GetActorLocation();
	MoveEnd = Destination;
	Facing = Direction.Rotation();
	RollSilhouette->SetSkeletalMeshAsset(Mesh);
	RollSilhouette->bDisableClothSimulation = true;
	RollMaterial = UMaterialInstanceDynamic::Create(Gold, this);
	RollMaterial->SetVectorParameterValue(TEXT("BodyTint"), FLinearColor(1.35f, 0.85f, 0.10f));
	for (int32 Index = 0; Index < RollSilhouette->GetNumMaterials(); ++Index)
	{
		RollSilhouette->SetMaterial(Index, RollMaterial);
	}
	TransitionSilhouette->SetSkeletalMeshAsset(Source->GetSkeletalMeshAsset());
	TransitionSilhouette->SetLeaderPoseComponent(Source);
	TransitionSilhouette->SetForcedLOD(1);
	TransitionMaterial = UMaterialInstanceDynamic::Create(Gold, this);
	TransitionMaterial->SetVectorParameterValue(TEXT("BodyTint"), FLinearColor(1.35f, 0.85f, 0.10f));
	for (int32 Index = 0; Index < TransitionSilhouette->GetNumMaterials(); ++Index)
	{
		TransitionSilhouette->SetMaterial(Index, TransitionMaterial);
		const FName SlotName = Source->GetSkeletalMeshAsset()->GetMaterials()[Index].MaterialSlotName;
		// 본체 천의 시뮬레이션 버텍스는 LeaderPose가 복사하지 않는다. 굳은 금빛 망토 판이 겹치지 않게 몸만 연결한다.
		const bool bCloth = SlotName == TEXT("M08_Cloak") || SlotName == TEXT("M16_CloakStraps") ||
			SlotName == TEXT("M14_CloakHood");
		for (int32 Lod = 0; Lod < TransitionSilhouette->GetNumLODs(); ++Lod)
		{
			TransitionSilhouette->ShowMaterialSection(Index, INDEX_NONE, !bCloth && Source->IsMaterialSectionShown(Index, Lod), Lod);
		}
	}
	for (UPoseableMeshComponent* Echo : Afterimages)
	{
		Echo->SetSkinnedAssetAndUpdate(bTeleport ? Source->GetSkeletalMeshAsset() : Mesh);
		Echo->SetUsingAbsoluteLocation(true);
		Echo->SetUsingAbsoluteRotation(true);
		Echo->SetUsingAbsoluteScale(true);
		UMaterialInstanceDynamic* Fade = UMaterialInstanceDynamic::Create(Gold, this);
		Fade->SetVectorParameterValue(TEXT("BodyTint"), FLinearColor(1.8f, 1.05f, 0.17f));
		Fade->SetScalarParameterValue(TEXT("Visibility"), 0.0f);
		AfterimageMaterials.Add(Fade);
		for (int32 Index = 0; Index < Echo->GetNumMaterials(); ++Index) { Echo->SetMaterial(Index, Fade); }
	}
	const float SourceHeight = InCharacter->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() * 1.8f;
	RollSilhouette->SetWorldScale3D(FVector(SourceHeight / FMath::Max(1.0f, Mesh->GetBounds().BoxExtent.Z * 2.0f)));
	RollSilhouette->PlayAnimation(Roll, false);
	RollSilhouette->SetPlayRate(0.0f);
	if (UAnimSingleNodeInstance* Node = RollSilhouette->GetSingleNodeInstance())
	{
		Node->SetRootMotionMode(ERootMotionMode::IgnoreRootMotion);
	}
	PreviousRootMotion = Anim->RootMotionMode;
	bPreviousOrientRotation = Movement->bOrientRotationToMovement;
	bPreviousMeshVisible = Source->IsVisible();
	Anim->SetRootMotionMode(ERootMotionMode::IgnoreRootMotion);
	Movement->bOrientRotationToMovement = false;
	Movement->StopMovementImmediately();
	if (InCharacter->GetController()) { InCharacter->GetController()->StopMovement(); }
	InCharacter->SetActorRotation(Facing);
	if (bTeleport)
	{
		ASparrowHarmonyFX::Create(InCharacter, TEXT("B"), MoveStart - FVector::UpVector * 35.f, Direction);
		// 출발 잔상은 본체의 실제 변신 자세를 고정한다. 이동 경로에 구르기 대역을 만들지 않는다.
		Afterimages[0]->SetWorldTransform(Source->GetComponentTransform());
		Afterimages[0]->CopyPoseFromSkeletalComponent(Source);
		Afterimages[0]->RefreshBoneTransforms();
		for (int32 Index = 0; Index < Source->GetNumMaterials(); ++Index)
		{
			for (int32 Lod = 0; Lod < Source->GetNumLODs(); ++Lod)
			{
				Afterimages[0]->ShowMaterialSection(Index, INDEX_NONE, Source->IsMaterialSectionShown(Index, Lod), Lod);
			}
		}
	}
	for (TActorIterator<ASparrowAscensionWings> It(GetWorld()); It; ++It)
	{
		if (It->GetOwner() == InCharacter)
		{
			HiddenForms.Add(*It);
			PreviousFormHidden.Add(It->IsHidden());
			It->SetMobilityVisibility(1.0f);
		}
	}
	bMoving = true;
	RollSilhouette->SetVisibility(true);
	UpdatePresentation();
	return true;
}

UAnimSequence* ASparrowGoldRoll::GetRollAnimation() const
{
	UAnimSingleNodeInstance* Node = RollSilhouette->GetSingleNodeInstance();
	return Node ? Cast<UAnimSequence>(Node->GetCurrentAsset()) : nullptr;
}

void ASparrowGoldRoll::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!CharacterOwner.IsValid() || CharacterOwner->IsActorBeingDestroyed() || !OwnerAnim.IsValid() ||
		CharacterOwner->GetCharacterMovement()->MovementMode != MOVE_Walking) { Destroy(); return; }
	if (bTeleport)
	{
		Age += DeltaSeconds;
		if (bMoving)
		{
			if (!bTeleportCommitted && Age >= 0.035f)
			{
				// 목적지 검사를 통과해도 시전 사이에 생긴 장애물은 실제 캡슐 sweep으로 다시 제한한다.
				FHitResult Hit;
				CharacterOwner->SetActorLocation(MoveEnd, true, &Hit, ETeleportType::TeleportPhysics);
				bTeleportCommitted = true;
				ASparrowHarmonyFX::Create(CharacterOwner.Get(), TEXT("B"), CharacterOwner->GetActorLocation() - FVector::UpVector * 35.f, Facing.Vector());
			}
			CharacterOwner->GetCharacterMovement()->StopMovementImmediately();
			UpdateTeleportPresentation();
			if (bTeleportCommitted && Age >= TeleportControlReturn) { FinishMovement(); }
		}
		// 출발점 잔광은 조작을 돌려준 뒤에도 자기 자리에서만 사라진다.
		const float EchoAlpha = 0.65f * FMath::Square(FMath::Clamp(1.0f - Age / TeleportDuration, 0.0f, 1.0f));
		AfterimageMaterials[0]->SetScalarParameterValue(TEXT("Visibility"), EchoAlpha);
		Afterimages[0]->SetVisibility(bPreviousMeshVisible && EchoAlpha > 0.002f);
		if (Age >= TeleportDuration) { Destroy(); }
		return;
	}
	Age += DeltaSeconds * PlaybackRate;
	const float Phase = FMath::Clamp(Age / PresentationDuration, 0.0f, 1.0f);
	// 도약과 회전 중에 이동을 끝내고 마지막 구간은 착지·회복에 쓴다. 충돌은 본체 캡슐이 소유한다.
	if (bMoving)
	{
		const float Progress = FMath::SmoothStep(0.0f, 1.0f, (Age - 0.05f) / (RollTravelEnd - 0.05f));
		FHitResult Hit;
		CharacterOwner->SetActorLocation(FMath::Lerp(MoveStart, MoveEnd, Progress), true, &Hit);
		CharacterOwner->GetCharacterMovement()->StopMovementImmediately();
		UpdatePresentation();
		UpdateAfterimages();
		// 착지와 동시에 이동/스킬 입력을 돌려준다. 남은 잔상 수명으로 조작을 막지 않는다.
		if (Hit.bBlockingHit || Age >= RollTravelEnd) { FinishMovement(); }
	}
	else { UpdateAfterimages(); }
	if (Phase >= 1.0f) { Destroy(); }
}

void ASparrowGoldRoll::UpdatePresentation()
{
	if (!bMoving || !CharacterOwner.IsValid()) { return; }
	if (bTeleport) { UpdateTeleportPresentation(); return; }
	FVector Location = CharacterOwner->GetActorLocation();
	Location.Z -= CharacterOwner->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	// 대역만 낮은 도약 호를 따른다. 본체 충돌 캡슐은 지면에 남아 벽/내비게이션 판정을 유지한다.
	const float AirPhase = FMath::Clamp((Age - 0.08f) / 0.62f, 0.0f, 1.0f);
	Location.Z += 28.0f * FMath::Sin(PI * AirPhase);
	// 원본 glTF의 전방 +Z는 UE import에서 +Y다. 캡슐 전방 +X에 맞춰 측면 구르기를 막는다.
	RollSilhouette->SetWorldLocationAndRotation(Location, FRotator(0.0f, Facing.Yaw - 90.0f, 0.0f));
	if (UAnimSingleNodeInstance* Node = RollSilhouette->GetSingleNodeInstance())
	{
		// 긴 등 펴기 구간보다 도약→전방 회전→착지의 연결을 분명하게 보인다. 원본 포즈는 유지한다.
		const float Position = Age <= 0.12f ? Age : (Age <= 0.62f ?
			FMath::Lerp(0.12f, 0.78f, (Age - 0.12f) / 0.50f) :
			FMath::Lerp(0.78f, Node->GetLength(), FMath::Clamp((Age - 0.62f) / (RollTravelEnd - 0.62f), 0.0f, 1.0f)));
		Node->SetPosition(Position, false);
		RollSilhouette->TickAnimation(0.0f, false);
		RollSilhouette->RefreshBoneTransforms();
	}
	// 출발/착지에서 본체와 같은 포즈의 금빛 몸을 연결한다. 원래 본체 재질은 교체하지 않는다.
	const float RollIn = FMath::SmoothStep(0.0f, 1.0f, Age / 0.13f);
	const float Landing = FMath::SmoothStep(0.0f, 1.0f, (Age - 0.54f) / 0.16f);
	const float RollAlpha = RollIn * (1.0f - Landing);
	RollMaterial->SetScalarParameterValue(TEXT("Visibility"), RollAlpha);
	RollSilhouette->SetVisibility(RollAlpha > 0.002f);
	const float DepartureGlow = FMath::SmoothStep(0.0f, 1.0f, Age / 0.045f) * (1.0f - RollIn);
	const float LandingGlow = Landing * (1.0f - FMath::SmoothStep(0.0f, 1.0f, (Age - 0.63f) / 0.07f));
	const float BodyAlpha = FMath::Max(DepartureGlow, LandingGlow);
	TransitionMaterial->SetScalarParameterValue(TEXT("Visibility"), BodyAlpha);
	TransitionSilhouette->SetWorldTransform(CharacterOwner->GetMesh()->GetComponentTransform());
	TransitionSilhouette->SetVisibility(bPreviousMeshVisible && BodyAlpha > 0.002f);
	CharacterOwner->GetMesh()->SetVisibility(bPreviousMeshVisible && (Age < 0.055f || Age >= 0.68f), false);
	for (const TWeakObjectPtr<AActor>& Form : HiddenForms)
	{
		if (ASparrowAscensionWings* Wings = Cast<ASparrowAscensionWings>(Form.Get()))
		{
			Wings->SetMobilityVisibility(FMath::Max(1.0f - RollIn, Landing));
		}
	}
}

void ASparrowGoldRoll::UpdateTeleportPresentation()
{
	if (!bMoving || !CharacterOwner.IsValid()) { return; }
	const float Departure = 1.0f - FMath::SmoothStep(0.0f, 0.035f, Age);
	const float Arrival = bTeleportCommitted ? FMath::SmoothStep(0.035f, TeleportControlReturn, Age) : 0.0f;
	const float Settle = 1.0f - FMath::SmoothStep(0.050f, TeleportControlReturn, Age);
	const float BodyAlpha = FMath::Max(Departure, Arrival * Settle);
	RollSilhouette->SetVisibility(false);
	TransitionSilhouette->SetWorldTransform(CharacterOwner->GetMesh()->GetComponentTransform());
	TransitionMaterial->SetScalarParameterValue(TEXT("Visibility"), BodyAlpha);
	TransitionSilhouette->SetVisibility(bPreviousMeshVisible && BodyAlpha > 0.002f);
	CharacterOwner->GetMesh()->SetVisibility(bPreviousMeshVisible && (Age < 0.02f || Age >= TeleportControlReturn), false);
	const float EchoAlpha = 0.65f * FMath::Square(FMath::Clamp(1.0f - Age / TeleportDuration, 0.0f, 1.0f));
	AfterimageMaterials[0]->SetScalarParameterValue(TEXT("Visibility"), EchoAlpha);
	Afterimages[0]->SetVisibility(bPreviousMeshVisible && EchoAlpha > 0.002f);
	for (const TWeakObjectPtr<AActor>& Form : HiddenForms)
	{
		if (ASparrowAscensionWings* Wings = Cast<ASparrowAscensionWings>(Form.Get()))
		{
			Wings->SetMobilityVisibility(FMath::Max(Departure, Arrival));
		}
	}
}

void ASparrowGoldRoll::UpdateAfterimages()
{
	for (int32 Index = 0; Index < Afterimages.Num(); ++Index)
	{
		UPoseableMeshComponent* Echo = Afterimages[Index];
		if (bMoving && AfterimageBirths[Index] < 0.0f && Age >= 0.13f + Index * 0.10f)
		{
			Echo->SetWorldTransform(RollSilhouette->GetComponentTransform());
			Echo->CopyPoseFromSkeletalComponent(RollSilhouette);
			Echo->RefreshBoneTransforms();
			AfterimageBirths[Index] = Age;
		}
		if (AfterimageBirths[Index] < 0.0f) { continue; }
		const float Fade = 0.44f * FMath::Square(FMath::Clamp(1.0f - (Age - AfterimageBirths[Index]) / 0.32f, 0.0f, 1.0f));
		AfterimageMaterials[Index]->SetScalarParameterValue(TEXT("Visibility"), Fade);
		Echo->SetVisibility(Fade > 0.002f);
	}
}

void ASparrowGoldRoll::FinishMovement()
{
	if (!bMoving) { return; }
	bMoving = false;
	RollSilhouette->SetVisibility(false);
	TransitionSilhouette->SetVisibility(false);
	if (OwnerAnim.IsValid()) { OwnerAnim->SetRootMotionMode(PreviousRootMotion); }
	if (CharacterOwner.IsValid())
	{
		CharacterOwner->GetMesh()->SetVisibility(bPreviousMeshVisible, false);
		if (UCharacterMovementComponent* Movement = CharacterOwner->GetCharacterMovement())
		{
			Movement->bOrientRotationToMovement = bPreviousOrientRotation;
			Movement->StopMovementImmediately();
		}
	}
	for (int32 Index = 0; Index < HiddenForms.Num(); ++Index)
	{
		if (ASparrowAscensionWings* Wings = Cast<ASparrowAscensionWings>(HiddenForms[Index].Get()))
		{
			Wings->SetMobilityVisibility(1.0f);
			Wings->SetActorHiddenInGame(PreviousFormHidden[Index]);
		}
	}
	HiddenForms.Reset();
	PreviousFormHidden.Reset();
}

void ASparrowGoldRoll::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	FinishMovement();
	Super::EndPlay(EndPlayReason);
}
