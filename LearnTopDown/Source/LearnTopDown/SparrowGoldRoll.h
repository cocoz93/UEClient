#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "GameFramework/Actor.h"
#include "SparrowGoldRoll.generated.h"

class ACharacter;
class UAnimSequence;
class USkeletalMeshComponent;
class UPoseableMeshComponent;
class UMaterialInstanceDynamic;

// Space 구르기의 시각 대역이다. 이동과 자세·잔상·착지를 같은 배속으로 연결한다.
UCLASS()
class LEARNTOPDOWN_API ASparrowGoldRoll : public AActor
{
	GENERATED_BODY()
public:
	ASparrowGoldRoll();
	bool Initialize(ACharacter* InCharacter, const FVector& Destination, const FVector& Direction, bool bInTeleport = false);
	bool IsMoving() const { return bMoving; }
	UFUNCTION(BlueprintPure, Category = "Skills")
	UAnimSequence* GetRollAnimation() const;
	UFUNCTION(BlueprintPure, Category = "Skills")
	float GetRollDuration() const { return bTeleport ? TeleportDuration : PresentationDuration / PlaybackRate; }
	UFUNCTION(BlueprintPure, Category = "Skills")
	bool IsTeleporting() const { return bTeleport; }
	UFUNCTION(BlueprintPure, Category = "Skills")
	float GetControlLockDuration() const { return bTeleport ? TeleportControlReturn : RollTravelEnd / PlaybackRate; }
	virtual void Tick(float DeltaSeconds) override;
protected:
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
private:
	static constexpr float PresentationDuration = 1.05f;
	static constexpr float PlaybackRate = 2.625f;
	static constexpr float TeleportDuration = 0.14f;
	static constexpr float RollTravelEnd = 0.70f;
	static constexpr float TeleportControlReturn = 0.065f;
	void UpdateTeleportPresentation();
	void UpdatePresentation();
	void UpdateAfterimages();
	void FinishMovement();
	UPROPERTY()
	TObjectPtr<USkeletalMeshComponent> RollSilhouette;
	UPROPERTY()
	TObjectPtr<USkeletalMeshComponent> TransitionSilhouette;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> RollMaterial;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> TransitionMaterial;
	UPROPERTY()
	TArray<TObjectPtr<UPoseableMeshComponent>> Afterimages;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> AfterimageMaterials;
	TArray<float> AfterimageBirths;
	TWeakObjectPtr<ACharacter> CharacterOwner;
	TWeakObjectPtr<UAnimInstance> OwnerAnim;
	TArray<TWeakObjectPtr<AActor>> HiddenForms;
	TArray<bool> PreviousFormHidden;
	FVector MoveStart = FVector::ZeroVector;
	FVector MoveEnd = FVector::ZeroVector;
	FRotator Facing = FRotator::ZeroRotator;
	TEnumAsByte<ERootMotionMode::Type> PreviousRootMotion = ERootMotionMode::RootMotionFromMontagesOnly;
	bool bPreviousOrientRotation = true;
	bool bPreviousMeshVisible = true;
	bool bMoving = false;
	bool bTeleport = false;
	bool bTeleportCommitted = false;
	float Age = 0.0f;
};
