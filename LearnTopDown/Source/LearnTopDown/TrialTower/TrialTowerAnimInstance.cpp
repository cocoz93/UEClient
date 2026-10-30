#include "TrialTowerAnimInstance.h"

#include "Animation/AnimSequence.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	constexpr float HitRise = 0.06f;
	constexpr float HitHoldEnd = 0.18f;
	constexpr float HitDuration = 0.42f;
	constexpr float HitStrength = 0.8f;
}

UTrialTowerAnimInstance::UTrialTowerAnimInstance()
{
	for (const TCHAR* Direction : { TEXT("Front"), TEXT("Back"), TEXT("Left"), TEXT("Right") })
	{
		const FString Path = FString(TEXT("/Game/ParagonMinions/Characters/Minions/Down_Minions/Animations/Melee/HitReact_")) + Direction;
		ConstructorHelpers::FObjectFinder<UAnimSequence> Animation(*Path);
		DirectionalHits.Add(Animation.Object);
	}
	HitReactionSequence = DirectionalHits[0];
}

void UTrialTowerAnimInstance::ClearHitReaction()
{
	HitReactionElapsed = HitDuration;
	HitReactionTime = HitReactionWeight = 0.0f;
}

void UTrialTowerAnimInstance::PlayHitReaction(const FVector& TowardSource)
{
	const APawn* Pawn = TryGetPawnOwner();
	// Additional damage still applies. Let the current visual recoil settle
	// instead of snapping its time back to zero on every tick of a damage field.
	if (!Pawn || HitReactionElapsed < HitDuration) { return; }
	const float Forward = FVector::DotProduct(Pawn->GetActorForwardVector(), TowardSource);
	const float Right = FVector::DotProduct(Pawn->GetActorRightVector(), TowardSource);
	const int32 Index = FMath::Abs(Forward) >= FMath::Abs(Right) ?
		(Forward >= 0.0f ? 0 : 1) : (Right >= 0.0f ? 3 : 2);
	if (!DirectionalHits.IsValidIndex(Index) || !DirectionalHits[Index]) { return; }
	HitReactionSequence = DirectionalHits[Index];
	HitReactionElapsed = HitReactionTime = HitReactionWeight = 0.0f;
}

void UTrialTowerAnimInstance::NativeInitializeAnimation()
{
	Super::NativeInitializeAnimation();
	SetRootMotionMode(ERootMotionMode::IgnoreRootMotion);
	ClearHitReaction();
}

void UTrialTowerAnimInstance::NativeUpdateAnimation(float DeltaSeconds)
{
	Super::NativeUpdateAnimation(DeltaSeconds);
	const ACharacter* Character = Cast<ACharacter>(TryGetPawnOwner());
	float TargetSpeed = 0.0f;
	if (Character && Character->GetCharacterMovement())
	{
		const float WalkSpeed = FMath::Max(1.0f, Character->GetCharacterMovement()->MaxWalkSpeed);
		TargetSpeed = FMath::Clamp(Character->GetVelocity().Size2D() / WalkSpeed, 0.0f, 1.0f) * 420.0f;
	}
	Speed = FMath::FInterpTo(Speed, TargetSpeed, DeltaSeconds, 14.0f);
	HitReactionElapsed = FMath::Min(HitReactionElapsed + DeltaSeconds, HitDuration);
	HitReactionTime = HitReactionSequence ? FMath::Min(HitReactionElapsed, HitReactionSequence->GetPlayLength()) : 0.0f;
	const float Envelope = HitReactionElapsed < HitRise ? HitReactionElapsed / HitRise :
		1.0f - FMath::Clamp((HitReactionElapsed - HitHoldEnd) / (HitDuration - HitHoldEnd), 0.0f, 1.0f);
	HitReactionWeight = HitStrength * FMath::SmoothStep(0.0f, 1.0f, Envelope);
}
