#pragma once

#include "CoreMinimal.h"
#include "TopDownCombatCharacter.h"
#include "SparrowCharacter.generated.h"

class UCameraComponent;
class UMaterialInterface;
class UPathFollowingComponent;
class USparrowSkillComponent;
class USpringArmComponent;
class UAnimSequence;
class UWindDirectionalSourceComponent;
struct FAIRequestID;
struct FPathFollowingResult;

UCLASS()
class LEARNTOPDOWN_API ASparrowCharacter : public ATopDownCombatCharacter
{
	GENERATED_BODY()

public:
	ASparrowCharacter(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());
	UFUNCTION(BlueprintPure, Category = "Skills")
	USparrowSkillComponent* GetSparrowSkills() const;
	UFUNCTION(BlueprintPure, Category = "Combat")
	float GetBasicAttackCycleSeconds() const;
	UFUNCTION(BlueprintPure, Category = "Animation")
	static bool ShouldUseCombatLocomotion(AActor* CharacterOwner);
	UFUNCTION(BlueprintPure, Category = "Animation")
	static bool ShouldHoldBowReady(AActor* CharacterOwner);
	UFUNCTION(BlueprintPure, Category = "Animation")
	static bool ShouldHoldInnerFireReady(AActor* CharacterOwner);
	virtual void Tick(float DeltaSeconds) override;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	virtual void NotifyControllerChanged() override;
	virtual void ExecuteBasicAttackHit() override;
	virtual UAnimMontage* GetBasicAttackMontage(UAnimMontage* ConfiguredMontage) const override;
	virtual float GetBasicAttackHitDelay(UAnimMontage* Montage, float Duration, float HitFraction) const override;
	virtual bool ShouldFinishBasicAttackMontage() const override { return true; }

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Camera")
	TObjectPtr<USpringArmComponent> CameraBoom;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Camera")
	TObjectPtr<UCameraComponent> TopDownCamera;

private:
#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
	friend struct FSparrowStopQA;
#endif

	UPROPERTY()
	TSubclassOf<UAnimInstance> SmoothLocomotionClass;
	UPROPERTY()
	TSubclassOf<UAnimInstance> NaturalBasicAttackClass;
	UPROPERTY()
	TObjectPtr<UAnimMontage> NaturalBasicAttackMontage;
	UPROPERTY()
	TSoftClassPtr<UAnimInstance> HeldAimAnimationClass;
	UPROPERTY()
	TObjectPtr<UAnimSequence> HeldPrimarySequence;
	UPROPERTY()
	TObjectPtr<UAnimSequence> HeldInnerFireSequence;
	UPROPERTY()
	TObjectPtr<UAnimSequence> HeldReadySequence;
	UPROPERTY(Transient)
	TObjectPtr<UAnimMontage> HeldPrimaryMontage;
	UPROPERTY(Transient)
	TObjectPtr<UAnimMontage> HeldInnerFireMontage;
	UPROPERTY()
	TSoftObjectPtr<UMaterialInterface> IvoryHoodMaterial;
	bool bUseNaturalBasicAttack = false;
	bool bUseHeldAimPresentation = false;
	bool bHeldAttackReady = false;
	bool CreateHeldAttackMontages();

	void ClearStopHeading();
	void StartCapeFlutter();
	void UpdateCapeFlutter();
	void StopCapeFlutter();
	void OnNavigationFinished(FAIRequestID RequestId, const FPathFollowingResult& Result);
	UFUNCTION()
	void FinishStopHeading(float DeltaSeconds, FVector OldLocation, FVector OldVelocity);

	TWeakObjectPtr<UPathFollowingComponent> StopHeadingPathFollowing;
	FDelegateHandle NavigationFinishedHandle;
	float StopHeadingYaw = 0.0f;
	float StopHeadingDeadline = 0.0f;
	bool bFinishingStopHeading = false;

	TWeakObjectPtr<UWindDirectionalSourceComponent> CapeFlutterWind;
	FTimerHandle CapeFlutterTimer;
	double CapeFlutterStartTime = 0.0;
	double CapeFlutterLastUpdateTime = 0.0;
	float CapeFlutterMaxSpeed = 0.0f;
	float CapeFlutterMovementBlend = 0.0f;
};
