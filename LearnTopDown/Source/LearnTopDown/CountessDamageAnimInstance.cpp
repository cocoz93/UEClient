#include "CountessDamageAnimInstance.h"

#include "Animation/AnimSequence.h"
#include "CharacterSkillComponent.h"
#include "Engine/World.h"
#include "GameFramework/Controller.h"
#include "PlayerCombatComponent.h"
#include "TopDownCombatCharacter.h"
#include "UObject/ConstructorHelpers.h"

UCountessDamageAnimInstance::UCountessDamageAnimInstance()
{
	for (const TCHAR* Direction : { TEXT("Fwd"), TEXT("Bwd"), TEXT("Left"), TEXT("Right") })
	{
		const FString Path = FString(TEXT("/Game/ParagonCountess/Characters/Heroes/Countess/Animations/Hitreact_")) + Direction;
		ConstructorHelpers::FObjectFinder<UAnimSequence> Animation(*Path);
		DirectionalDamageReactions.Add(Animation.Object);
	}
	DamageReactionSequence = DirectionalDamageReactions[0];
}

void UCountessDamageAnimInstance::NativeInitializeAnimation()
{
	Super::NativeInitializeAnimation();
	DamageReactionAllowedAfter = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0f;
	DamageReactionTime = DamageReactionWeight = 0.0f;
	ReactionStrength = 1.0f;
}

void UCountessDamageAnimInstance::NativeUpdateAnimation(float DeltaSeconds)
{
	Super::NativeUpdateAnimation(DeltaSeconds);
	const ATopDownCombatCharacter* Character = Cast<ATopDownCombatCharacter>(TryGetPawnOwner());
	const AController* Controller = Character ? Character->GetController() : nullptr;
	const UPlayerCombatComponent* Combat = Controller ? Controller->FindComponentByClass<UPlayerCombatComponent>() : nullptr;
	DamageReactionWeight = 0.0f;
	if (!Combat || !GetWorld()) { return; }
	if (!Combat->CanShowDamageReaction())
	{
		// A short stun must not resume an older ordinary recoil on recovery.
		DamageReactionAllowedAfter = GetWorld()->GetTimeSeconds();
		return;
	}
	const float Age = Combat->GetDamageReactionAge();
	// Character selection/respawn must not inherit a previous pawn's recoil.
	if (Age > GetWorld()->GetTimeSeconds() - DamageReactionAllowedAfter || Age >= 0.75f) { return; }
	const int32 Index = static_cast<int32>(Combat->GetHitDirection());
	if (!DirectionalDamageReactions.IsValidIndex(Index) || !DirectionalDamageReactions[Index]) { return; }
	DamageReactionSequence = DirectionalDamageReactions[Index];
	// Preserve the authored 1x impulse, peak and recovery instead of stopping a
	// fast montage as soon as an unrelated input-lock timer expires.
	DamageReactionTime = FMath::Min(Age, DamageReactionSequence->GetPlayLength());
	const UCharacterSkillComponent* Skills = Character->GetSkills();
	const float Strength = Skills && Skills->IsCasting() ? 0.30f : (Character->IsAttacking() ? 0.55f : 1.0f);
	ReactionStrength = FMath::FInterpTo(ReactionStrength, Strength, DeltaSeconds, 18.0f);
	const float BlendIn = FMath::SmoothStep(0.0f, 0.045f, Age);
	const float BlendOut = 1.0f - FMath::SmoothStep(0.50f, 0.75f, Age);
	DamageReactionWeight = ReactionStrength * BlendIn * BlendOut;
}
