#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "PlayerCombatComponent.generated.h"

class APlayerController;
class ATopDownCombatCharacter;
class UAnimInstance;
class UAnimMontage;
class UAnimSequence;
class UParticleSystem;

UENUM(BlueprintType)
enum class EPlayerHitDirection : uint8 { Front, Back, Left, Right };

UENUM(BlueprintType)
enum class EPlayerControlState : uint8 { None, HitReaction, Stunned, Knockback };

USTRUCT(BlueprintType)
struct FPlayerCombatAnimations
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, Category = "Combat")
	TObjectPtr<UAnimSequence> HitReaction;
	UPROPERTY(EditAnywhere, Category = "Combat")
	TObjectPtr<UAnimSequence> HitBack;
	UPROPERTY(EditAnywhere, Category = "Combat")
	TObjectPtr<UAnimSequence> HitLeft;
	UPROPERTY(EditAnywhere, Category = "Combat")
	TObjectPtr<UAnimSequence> HitRight;
	UPROPERTY(EditAnywhere, Category = "Combat")
	TObjectPtr<UAnimSequence> StunStart;
	UPROPERTY(EditAnywhere, Category = "Combat")
	TObjectPtr<UAnimSequence> StunLoop;
	UPROPERTY(EditAnywhere, Category = "Combat")
	TObjectPtr<UAnimSequence> Knockback;
	UPROPERTY(EditAnywhere, Category = "Combat")
	TObjectPtr<UAnimSequence> Death;
	UPROPERTY(EditAnywhere, Category = "Combat")
	FName HitReactionSlot;
	UPROPERTY(EditAnywhere, Category = "Combat")
	bool bNonInterruptingDamageFeedback = false;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE(FPlayerCombatEvent);

// Owned by the player controller so character selection cannot reset health.
// Map-specific encounters subscribe to state/death events; damage has no map dependency.
UCLASS(ClassGroup = (Combat), meta = (BlueprintSpawnableComponent))
class LEARNTOPDOWN_API UPlayerCombatComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UPlayerCombatComponent();
	UFUNCTION(BlueprintPure, Category = "Combat")
	float GetHealth() const { return Health; }
	UFUNCTION(BlueprintPure, Category = "Combat")
	float GetMaxHealth() const { return 100.0f; }
	UFUNCTION(BlueprintPure, Category = "Combat")
	bool UsesNonInterruptingDamageFeedback() const;
	bool CanShowDamageReaction() const
	{
		return bHitReactionsEnabled && UsesNonInterruptingDamageFeedback() && IsAlive() && !IsCrowdControlled();
	}
	UFUNCTION(BlueprintPure, Category = "Combat")
	float GetDamageTrailHealth() const;
	UFUNCTION(BlueprintPure, Category = "Combat")
	float GetDamageFeedbackAge() const;
	// Countess visual contacts can restart while health remains protected.
	UFUNCTION(BlueprintPure, Category = "Combat")
	float GetDamageReactionAge() const;
	UFUNCTION(BlueprintPure, Category = "Combat")
	bool IsAlive() const { return Health > 0.0f; }
	UFUNCTION(BlueprintPure, Category = "Combat")
	bool IsInvulnerable() const;
	UFUNCTION(BlueprintPure, Category = "Combat")
	bool IsHitReacting() const { return ControlState == EPlayerControlState::HitReaction; }
	UFUNCTION(BlueprintPure, Category = "Combat")
	bool IsCrowdControlled() const { return ControlState != EPlayerControlState::None; }
	UFUNCTION(BlueprintPure, Category = "Combat")
	bool IsStunned() const { return ControlState == EPlayerControlState::Stunned; }
	UFUNCTION(BlueprintPure, Category = "Combat")
	bool IsKnockedBack() const { return ControlState == EPlayerControlState::Knockback; }
	UFUNCTION(BlueprintPure, Category = "Combat")
	EPlayerHitDirection GetHitDirection() const { return HitDirection; }
	UFUNCTION(BlueprintPure, Category = "Combat")
	UAnimSequence* GetActiveReactionAnimation() const { return ActiveReactionAnimation; }
	// Explicit hard CC interrupts casts. Repeated hard CC cannot extend its duration.
	// Damage protection is independent, so an attack may apply damage, then CC.
	UFUNCTION(BlueprintCallable, Category = "Combat")
	bool ApplyStun(float Duration = 1.0f);
	// Direction is a world-space push vector. Movement retains capsule collision.
	UFUNCTION(BlueprintCallable, Category = "Combat")
	bool ApplyKnockback(FVector Direction, float Distance = 250.0f, float Duration = 0.35f);
	// Respawns the selected character at this map's initial player position.
	UFUNCTION(BlueprintCallable, Category = "Combat")
	bool RespawnPlayer();

	UPROPERTY(BlueprintAssignable, Category = "Combat")
	FPlayerCombatEvent OnStateChanged;
	UPROPERTY(BlueprintAssignable, Category = "Combat")
	FPlayerCombatEvent OnDied;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	UPROPERTY(EditDefaultsOnly, Category = "Combat")
	TArray<FPlayerCombatAnimations> CharacterAnimations;
	// Practice modes may opt out without changing the shared damage rules.
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Combat")
	bool bDamageEnabled = true;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Combat")
	bool bHitReactionsEnabled = true;

private:
	void PresentDamage(AActor* DamageSource);
	void StartHitReaction(AActor* DamageSource);
	bool BeginControl(EPlayerControlState State, float Duration);
	bool CanApplyHardControl() const;
	const FPlayerCombatAnimations* FindAnimations() const;
	void PlayReaction(UAnimSequence* Animation, int32 LoopCount = 1);
	void PlayStunLoop();
	void EndHitReaction();
	void EndHitProtection();
	void PresentDeath();
	void ReleasePlayerInput();
	void NotifyStateChanged();
	UFUNCTION()
	void OnPlayerPawnChanged(APawn* OldPawn, APawn* NewPawn);
	UFUNCTION()
	void OnPlayerDamaged(AActor* DamagedActor, float Damage, const UDamageType* DamageType,
		AController* InstigatedBy, AActor* DamageCauser);

	TWeakObjectPtr<APlayerController> PlayerController;
	TWeakObjectPtr<APawn> PlayerPawn;
	TWeakObjectPtr<ATopDownCombatCharacter> HitReactionCharacter;
	TWeakObjectPtr<UAnimInstance> HitReactionAnimInstance;
	UPROPERTY(Transient)
	TObjectPtr<UAnimMontage> HitReactionMontage;
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> ActiveReactionAnimation;
	UPROPERTY()
	TObjectPtr<UParticleSystem> FleshHitEffect;
	FTimerHandle HitProtectionTimer;
	FTimerHandle HitReactionTimer;
	FTimerHandle StunLoopTimer;
	FVector PlayerStartFeet = FVector::ZeroVector;
	FRotator PlayerStartRotation = FRotator::ZeroRotator;
	float Health = 100.0f;
	float DamageTrailHealth = 100.0f;
	double LastDamageTime = -1000.0;
	double LastDamageReactionTime = -1000.0;
	double InvulnerableUntil = 0.0;
	double HardControlProtectedUntil = 0.0;
	EPlayerControlState ControlState = EPlayerControlState::None;
	EPlayerHitDirection HitDirection = EPlayerHitDirection::Front;
	uint16 KnockbackSourceID = 0;
	uint8 SavedHitMovementMode = 0;
	uint8 SavedHitCustomMovementMode = 0;
	bool bSavedOrientToMovement = false;
	bool bSavedControllerDesiredRotation = false;
	bool bHasPlayerStart = false;
	bool bDisabledPlayerInput = false;
	bool bRespawning = false;
	bool bShuttingDown = false;
};
