#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "GameFramework/Actor.h"
#include "CountessBackstepEcho.generated.h"

class ACharacter;
class UCountessSkillComponent;
class UAnimMontage;
class USkeletalMeshComponent;
class UPoseableMeshComponent;
class UMaterialInstanceDynamic;

// 출발점의 V 한 번과 실제 후퇴를 분리한다. 분신/잔상에는 별도 피해 판정이 없다.
UCLASS()
class LEARNTOPDOWN_API ACountessBackstepEcho : public AActor
{
	GENERATED_BODY()
public:
	ACountessBackstepEcho();
	static constexpr float MoveDuration = 0.16f;
	bool Initialize(ACharacter* InCharacter, UCountessSkillComponent* InSkills, UAnimMontage* Dodge,
		UAnimMontage* Captured, float CapturedPosition, float CapturedRate, float ReleaseDelay,
		bool bTransferSiphon, bool bDetailedSiphon, const FVector& Destination);
	bool IsMoving() const { return bMoving; }
	bool UsesDetailedSiphon() const { return bCapturedDetailed; }
	float GetSiphonPlayRate() const { return EchoRate; }
	UFUNCTION(BlueprintPure, Category = "Skills")
	int32 GetTransferredActionCount() const { return TransferredActions; }
	virtual void Tick(float DeltaSeconds) override;
protected:
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
private:
	void FinishMovement();
	void ReleaseCapturedSiphon();
	void UpdateMotionEchoes(float DeltaSeconds, float Progress);
	UPROPERTY()
	TObjectPtr<USkeletalMeshComponent> Departure;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UPoseableMeshComponent>> MotionEchoes;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> MotionMaterials;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> DepartureMaterial;
	UPROPERTY(Transient)
	TObjectPtr<UAnimMontage> MovementMontage;
	TArray<float> MotionAges;
	TWeakObjectPtr<ACharacter> CharacterOwner;
	TWeakObjectPtr<UCountessSkillComponent> Skills;
	TWeakObjectPtr<UAnimInstance> MovingAnim;
	FTimerHandle ReleaseTimer;
	FVector MoveStart = FVector::ZeroVector;
	FVector MoveEnd = FVector::ZeroVector;
	TEnumAsByte<ERootMotionMode::Type> PreviousRootMotion = ERootMotionMode::RootMotionFromMontagesOnly;
	float EchoPosition = 0.0f;
	float EchoRate = 0.0f;
	float Age = 0.0f;
	float DepartureLife = 1.10f;
	float DepartureFadeStart = 0.08f;
	bool bPreviousOrientRotation = true;
	bool bMoving = false;
	bool bShotPending = false;
	bool bCapturedDetailed = false;
	int32 TransferredActions = 0;
};
