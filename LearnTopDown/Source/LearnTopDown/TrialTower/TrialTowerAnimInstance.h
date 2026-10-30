#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "TrialTowerAnimInstance.generated.h"

// The tower-owned AnimGraph keeps locomotion under the full-body attack slot.
UCLASS(Transient, Blueprintable)
class LEARNTOPDOWN_API UTrialTowerAnimInstance : public UAnimInstance
{
	GENERATED_BODY()

public:
	UTrialTowerAnimInstance();
	virtual void NativeInitializeAnimation() override;
	virtual void NativeUpdateAnimation(float DeltaSeconds) override;
	void PlayHitReaction(const FVector& TowardSource);
	void ClearHitReaction();

	// The source blend space places its combat jog at 420, independent of the
	// encounter's movement speed. Values above 420 would select a different jog.
	UPROPERTY(BlueprintReadOnly, Category = "Trial Tower|Animation")
	float Speed = 0.0f;

	// Evaluated separately from the attack montage; only the spine branch is
	// blended by the owned AnimBlueprint. Damage never restarts attack timing.
	UPROPERTY(BlueprintReadOnly, Category = "Trial Tower|Animation")
	TObjectPtr<UAnimSequence> HitReactionSequence;

	UPROPERTY(BlueprintReadOnly, Category = "Trial Tower|Animation")
	float HitReactionTime = 0.0f;

	UPROPERTY(BlueprintReadOnly, Category = "Trial Tower|Animation")
	float HitReactionWeight = 0.0f;

private:
	UPROPERTY()
	TArray<TObjectPtr<UAnimSequence>> DirectionalHits;
	float HitReactionElapsed = 1.0f;
};
