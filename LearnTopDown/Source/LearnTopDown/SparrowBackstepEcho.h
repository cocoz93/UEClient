#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "GameFramework/Actor.h"
#include "SparrowBackstepEcho.generated.h"

class ACharacter;
class USparrowSkillComponent;
class USkeletalMeshComponent;
class UAnimMontage;
class UAnimSequence;
class UMaterialInstanceDynamic;
class UParticleSystemComponent;
class UPoseableMeshComponent;

// 백스텝의 출발점에 남아 이미 준비하던 W를 한 번만 인수한다. D 추종 분신과 수명이 독립적이다.
UCLASS()
class LEARNTOPDOWN_API ASparrowBackstepEcho : public AActor
{
	GENERATED_BODY()
public:
	ASparrowBackstepEcho();
	static constexpr float MoveDuration = 0.16f;
	bool Initialize(ACharacter* InCharacter, USparrowSkillComponent* InSkills, UAnimMontage* Dodge,
		UAnimMontage* CapturedMontage, float CapturedPosition, float ReleaseDelay,
		bool bTransferShot, const FVector& Aim, const FVector& Destination);
	bool IsMoving() const { return bMoving; }
	FVector GetArrowOrigin() const;
	FVector GetCapturedAim() const { return CapturedAim; }
	void TrackEffect(UParticleSystemComponent* Effect);
	UFUNCTION(BlueprintPure, Category = "Skills")
	int32 GetTransferredShotCount() const { return TransferredShots; }
	virtual void Tick(float DeltaSeconds) override;
protected:
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
private:
	void FinishMovement();
	void ReleaseCapturedShot();
	void UpdateMotionEchoes(float DeltaSeconds, float Progress);
	UPROPERTY()
	TObjectPtr<USkeletalMeshComponent> Archer;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> EchoMaterial;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UPoseableMeshComponent>> MotionEchoes;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> MotionMaterials;
	TArray<float> MotionAges;
	UPROPERTY(Transient)
	TObjectPtr<UAnimMontage> MovementMontage;
	UPROPERTY(Transient)
	TObjectPtr<UAnimMontage> EchoMontage;
	TWeakObjectPtr<ACharacter> CharacterOwner;
	TWeakObjectPtr<USparrowSkillComponent> Skills;
	TWeakObjectPtr<UAnimInstance> MovingAnim;
	TArray<TWeakObjectPtr<UParticleSystemComponent>> Effects;
	FTimerHandle ReleaseTimer;
	FVector MoveStart = FVector::ZeroVector;
	FVector MoveEnd = FVector::ZeroVector;
	FVector CapturedAim = FVector::ZeroVector;
	TEnumAsByte<ERootMotionMode::Type> PreviousRootMotion = ERootMotionMode::RootMotionFromMontagesOnly;
	bool bPreviousOrientRotation = true;
	bool bMoving = false;
	bool bShotPending = false;
	int32 TransferredShots = 0;
	float Age = 0.0f;
};
