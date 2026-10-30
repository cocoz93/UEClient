#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "TrialTowerMonster.generated.h"

class ATrialTowerMonster;
class ATrialTowerEncounter;
class UAnimSequence;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FTrialTowerMonsterDefeated, ATrialTowerMonster*, Monster);

UCLASS()
class LEARNTOPDOWN_API ATrialTowerMonster : public ACharacter
{
	GENERATED_BODY()

public:
	ATrialTowerMonster();
	virtual void Tick(float DeltaSeconds) override;
	virtual float TakeDamage(float DamageAmount, const FDamageEvent& DamageEvent,
		AController* EventInstigator, AActor* DamageCauser) override;

	UFUNCTION(BlueprintCallable, Category = "Trial Tower")
	void InitializeForFloor(float InMaxHealth, float InMoveSpeed);
	void InitializeEncounter(ATrialTowerEncounter* InEncounter);

	UFUNCTION(BlueprintPure, Category = "Trial Tower")
	bool IsAlive() const { return !bDefeated && Health > 0.0f && !IsActorBeingDestroyed(); }

	UFUNCTION(BlueprintPure, Category = "Trial Tower")
	float GetHealth() const { return Health; }

	UFUNCTION(BlueprintPure, Category = "Trial Tower")
	float GetMaxHealth() const { return MaxHealth; }

	UFUNCTION(BlueprintPure, Category = "Trial Tower")
	bool IsAttacking() const { return bAttacking; }

	// Stops this encounter's combat without treating a surviving monster as a kill.
	UFUNCTION(BlueprintCallable, Category = "Trial Tower")
	void StopCombat();

	UPROPERTY(BlueprintAssignable, Category = "Trial Tower")
	FTrialTowerMonsterDefeated OnDefeated;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Trial Tower|Animation")
	TObjectPtr<UAnimSequence> IdleAnimation;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Trial Tower|Animation")
	TObjectPtr<UAnimSequence> RunAnimation;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Trial Tower|Animation")
	TObjectPtr<UAnimSequence> DeathAnimation;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Trial Tower|Animation")
	TObjectPtr<UAnimSequence> AttackAnimation;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	UPROPERTY(EditDefaultsOnly, Category = "Trial Tower", meta = (ClampMin = "1.0"))
	float MaxHealth = 100.0f;

	UPROPERTY(EditDefaultsOnly, Category = "Trial Tower", meta = (ClampMin = "0.0"))
	float ChaseAcceptanceRadius = 65.0f;

private:
	void RefreshPursuit();
	void UpdateLocomotionAnimation();
	bool CanFight() const;
	bool IsWithinAttackRange(const APawn* Target) const;
	void StartAttack(APawn* Target);
	void ApplyAttackHit();
	void FinishAttack();
	void Defeat();

	UPROPERTY(VisibleInstanceOnly, Category = "Trial Tower")
	float Health = 100.0f;

	TWeakObjectPtr<APawn> ChaseTarget;
	TWeakObjectPtr<ATrialTowerEncounter> Encounter;
	TWeakObjectPtr<APawn> AttackTarget;
	TWeakObjectPtr<UAnimSequence> PlayingAnimation;
	FTimerHandle PursuitTimer;
	FTimerHandle AttackHitTimer;
	FTimerHandle AttackEndTimer;
	double NextAttackTime = 0.0;
	bool bDefeated = false;
	bool bRunning = false;
	bool bAttacking = false;
	bool bCombatStopped = false;
	bool bInitializedForFloor = false;
};
