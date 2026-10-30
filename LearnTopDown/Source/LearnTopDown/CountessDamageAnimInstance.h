#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "CountessDamageAnimInstance.generated.h"

class UAnimSequence;

// Visual recoil is independent of montages, input and crowd-control recovery.
UCLASS(Transient, Blueprintable)
class LEARNTOPDOWN_API UCountessDamageAnimInstance : public UAnimInstance
{
	GENERATED_BODY()

public:
	UCountessDamageAnimInstance();
	virtual void NativeInitializeAnimation() override;
	virtual void NativeUpdateAnimation(float DeltaSeconds) override;

	UPROPERTY(Transient, BlueprintReadOnly, Category = "Damage Reaction")
	TObjectPtr<UAnimSequence> DamageReactionSequence;
	UPROPERTY(Transient, BlueprintReadOnly, Category = "Damage Reaction")
	float DamageReactionTime = 0.0f;
	UPROPERTY(Transient, BlueprintReadOnly, Category = "Damage Reaction")
	float DamageReactionWeight = 0.0f;

private:
	UPROPERTY()
	TArray<TObjectPtr<UAnimSequence>> DirectionalDamageReactions;
	float DamageReactionAllowedAfter = 0.0f;
	float ReactionStrength = 1.0f;
};
