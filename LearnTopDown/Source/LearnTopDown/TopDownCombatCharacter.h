#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "GameFramework/Character.h"
#include "TopDownCombatCharacter.generated.h"

class UAnimMontage;
class UCharacterMovementComponent;
class UCharacterSkillComponent;

USTRUCT(BlueprintType)
struct FBasicAttackComboStep
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, Category = "Combat")
	TObjectPtr<UAnimMontage> Montage;

	UPROPERTY(EditAnywhere, Category = "Combat", meta = (ClampMin = "0.1"))
	float PlayRate = 1.0f;

	UPROPERTY(EditAnywhere, Category = "Combat", meta = (ClampMin = "0.05", ClampMax = "0.95"))
	float HitTimeFraction = 0.35f;
};

UCLASS()
class LEARNTOPDOWN_API ATopDownCombatCharacter : public ACharacter
{
	GENERATED_BODY()

public:
	ATopDownCombatCharacter(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());
	void InterruptIntroAnimation();
	UFUNCTION(BlueprintPure, Category = "Movement")
	static FVector GetLocomotionAnimationVelocity(UCharacterMovementComponent* Movement);
	UFUNCTION(BlueprintCallable, Category = "Combat")
	bool TryBasicAttack(const FVector& AimLocation);
	void SetHeldBasicAttackInput(bool bHeld, const FVector& AimLocation = FVector::ZeroVector);
	bool HasHeldBasicAttackInput() const { return bHeldBasicAttackInput; }
	UFUNCTION(BlueprintPure, Category = "Combat")
	bool IsAttacking() const { return bAttacking; }
	UFUNCTION(BlueprintPure, Category = "Combat")
	int32 GetComboAttackNumber() const { return bAttacking ? ComboAttackIndex + 1 : 0; }
	UFUNCTION(BlueprintPure, Category = "Combat")
	FVector GetActiveAttackAimLocation() const { return ActiveAttackAimLocation; }
	UFUNCTION(BlueprintPure, Category = "Combat")
	bool IsCombatBusy() const;
	UFUNCTION(BlueprintPure, Category = "Skills")
	UCharacterSkillComponent* GetSkills() const { return CountessSkills; }
	void CancelBasicAttackForSkill();

protected:
	// 기존 블루프린트의 기본 서브오브젝트 이름을 유지해 에셋을 다시 저장하지 않는다.
	static const FName SkillComponentName;
	UPROPERTY(EditDefaultsOnly, Category = "Animation")
	FName IntroMontageName = TEXT("LevelStart_Montage");

	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	virtual void ExecuteBasicAttackHit();
	virtual UAnimMontage* GetBasicAttackMontage(UAnimMontage* ConfiguredMontage) const;
	virtual float GetBasicAttackHitDelay(UAnimMontage* Montage, float Duration, float HitFraction) const;
	virtual bool ShouldFinishBasicAttackMontage() const { return false; }

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Skills")
	TObjectPtr<UCharacterSkillComponent> CountessSkills;

	UPROPERTY(EditDefaultsOnly, Category = "Combat")
	TObjectPtr<UAnimMontage> BasicAttackMontage;

	// 비어 있으면 기존 단일 공격을 사용한다. 카운테스는 원본 Normal → A → B 순서다.
	UPROPERTY(EditDefaultsOnly, Category = "Combat")
	TArray<FBasicAttackComboStep> ComboAttacks;

	// 마지막 타 종료 후 새 평타를 제한한다. 이동과 콤보 중간의 입력 예약은 유지한다.
	UPROPERTY(EditDefaultsOnly, Category = "Combat", meta = (ClampMin = "0.0", Units = "s"))
	float ComboRestartCooldown = 0.3f;

	// 0보다 크면 타격 이 시간 뒤에 남은 동작을 끊어 바로 움직일 수 있게 한다. 다음 타로 이어질 입력이 있으면 원래 연계를 기다린다.
	UPROPERTY(EditDefaultsOnly, Category = "Combat", meta = (ClampMin = "0.0", Units = "s"))
	float RecoveryAfterHit = 0.0f;

	// 실제 공격 동작에 맞춰 조절하는 타격 시점. 전체 재생 시간에 대한 비율이다.
	UPROPERTY(EditDefaultsOnly, Category = "Combat", meta = (ClampMin = "0.05", ClampMax = "0.95"))
	float HitTimeFraction = 0.35f;

	UPROPERTY(EditDefaultsOnly, Category = "Combat", meta = (ClampMin = "1.0"))
	float AttackRange = 220.0f;

	UPROPERTY(EditDefaultsOnly, Category = "Combat", meta = (ClampMin = "1.0", ClampMax = "90.0"))
	float AttackHalfAngle = 55.0f;

	UPROPERTY(EditDefaultsOnly, Category = "Combat", meta = (ClampMin = "0.0"))
	float AttackDamage = 20.0f;

private:
	bool StartAttackStep(int32 StepIndex, const FVector& AimLocation);
	void ContinueCombo();
	void ApplyAttackHit();
	void CutAttackRecovery();
	void OnAttackEnded(UAnimMontage* Montage, bool bInterrupted, uint32 Generation);
	void OnAttackBlendingOut(UAnimMontage* Montage, bool bInterrupted, uint32 Generation);
	void FinishAttack();
	void ClearAttackTimers();

	bool bAttacking = false;
	bool bAttackQueued = false;
	bool bHeldBasicAttackInput = false;
	bool bHitApplied = false;
	bool bSavedOrientRotationToMovement = true;
	int32 ComboAttackIndex = 0;
	uint32 AttackGeneration = 0;

	double NextBasicAttackTime = 0.0;
	FVector ActiveAttackAimLocation = FVector::ZeroVector;
	FVector QueuedAimLocation = FVector::ZeroVector;
	FVector HeldBasicAttackAimLocation = FVector::ZeroVector;
	UPROPERTY(Transient)
	TObjectPtr<UAnimMontage> ActiveAttackMontage;
	TWeakObjectPtr<UAnimInstance> AttackAnimInstance;
	TEnumAsByte<ERootMotionMode::Type> SavedRootMotionMode = ERootMotionMode::RootMotionFromMontagesOnly;
	FTimerHandle HitTimer;
	FTimerHandle RecoveryTimer;
	FTimerHandle ComboAdvanceTimer;
	FTimerHandle ComboResetTimer;
	FTimerHandle RecoveryCutTimer;
};
