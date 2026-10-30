#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "KwangPlayerController.generated.h"

class UPathFollowingComponent;
class ATopDownCombatCharacter;
class UPlayerCombatComponent;

UCLASS()
class LEARNTOPDOWN_API AKwangPlayerController : public APlayerController
{
	GENERATED_BODY()

public:
	AKwangPlayerController();
	virtual void PlayerTick(float DeltaTime) override;
	virtual void SetPawn(APawn* InPawn) override;
	virtual void FlushPressedKeys() override;
	virtual bool ShouldFlushKeysWhenViewportFocusChanges() const override { return true; }
	UFUNCTION(BlueprintPure, Category = "Combat")
	UPlayerCombatComponent* GetPlayerCombat() const { return PlayerCombat; }

protected:
	virtual void BeginPlay() override;
	virtual void SetupInputComponent() override;

private:
	void InterruptIntroAnimation();
	void MovePressed();
	void MoveReleased();
	void AttackPressed();
	void AttackReleased();
	void ClearHeldAttackInput();
	bool UpdateHeldAttackAim(FVector& AimLocation);
	void SkillQPressed();
	void SkillWPressed();
	void SkillEPressed();
	void SkillRPressed();
	void SkillAPressed();
	void SkillSPressed();
	void SkillDPressed();
	void SkillFPressed();
	void SkillVPressed();
	void SkillSpacePressed();
	void SelectCountess();
	void SelectSparrow();
	void SelectGideon();
	void SelectAurora();
	void SwitchCharacter(const TCHAR* ClassPath);
	void UseSkill(int32 Slot);
	void MoveToCursor(bool bContinuousInput = false);
	void MoveToLocation(const FVector& Destination, bool bContinuousInput);
	void ClearPendingMoveInput();
	void TraceMovementInput(const TCHAR* Event) const;

	UPROPERTY()
	TObjectPtr<UPathFollowingComponent> PathFollowingComponent;
	UPROPERTY(VisibleAnywhere, Category = "Combat")
	TObjectPtr<UPlayerCombatComponent> PlayerCombat;

	bool bMoveHeld = false;
	bool bAttackHeld = false;
	TWeakObjectPtr<ATopDownCombatCharacter> HeldAttackOwner;
	TWeakObjectPtr<ATopDownCombatCharacter> PendingMoveOwner;
	FVector PendingMoveDestination = FVector::ZeroVector;
	bool bPendingMoveContinuousInput = false;
	float MoveRefreshTime = 0.0f;
};
