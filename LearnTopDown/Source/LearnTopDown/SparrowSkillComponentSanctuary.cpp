#include "SparrowSkillComponent.h"

#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "SparrowSanctuary.h"
#include "SparrowSharpVolley.h"
#include "TopDownCombatCharacter.h"

void USparrowSkillComponent::FinishRecoveryForMovement()
{
	if (SharpVolley.IsValid()) { SharpVolley->ReleaseRecoveryForMovement(); }
	if (bCasting && bActionExecuted && GetWorld() && GetWorld()->GetTimeSeconds() >= MovementReadyAt)
	{
		// 화살·화살비·변신과 이미 방출한 표면은 각자의 수명으로 계속 진행한다.
		FinishSkill(.035f);
	}
}

bool USparrowSkillComponent::TryUseSanctuarySkill(int32 Slot, const FVector& AimLocation, AActor* Target)
{
	if ((Slot != 9 && Slot != 11) || !bEnabled || !GetWorld() || !Character.IsValid() ||
		!Character->GetCharacterMovement() || Character->GetCharacterMovement()->MovementMode != MOVE_Walking ||
		AimLocation.ContainsNaN()) { return RejectInput(TEXT("Unavailable")); }
	if (IsCasting()) { return RejectInput(TEXT("Casting")); }
	if (GetSanctuaryCooldownRemaining(Slot) > 0.0f) { return RejectInput(TEXT("Cooldown")); }
	const FVector Facing = (AimLocation - Character->GetActorLocation()).GetSafeNormal2D();
	if (Facing.IsNearlyZero()) { return RejectInput(TEXT("Choose a direction")); }
	const FTransform Transform(Facing.IsNearlyZero() ? Character->GetActorRotation() : Facing.Rotation(), Character->GetActorLocation());
	ASparrowSanctuary* Barrier = nullptr;
	ASparrowSharpVolley* Volley = nullptr;
	if (Slot == 9)
	{
		Volley = GetWorld()->SpawnActorDeferred<ASparrowSharpVolley>(ASparrowSharpVolley::StaticClass(),
			Transform, Character.Get(), Character.Get(), ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
		if (!Volley || !Volley->Initialize(Character.Get(), AimLocation))
		{
			if (Volley) { Volley->Destroy(); }
			return RejectInput(TEXT("Sharp Shooter assets unavailable"));
		}
		if (SharpVolley.IsValid()) { SharpVolley->Destroy(); }
		SharpVolley = Volley;
	}
	else
	{
		Barrier = GetWorld()->SpawnActorDeferred<ASparrowSanctuary>(ASparrowSanctuary::StaticClass(),
			Transform, Character.Get(), Character.Get(), ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
		if (!Barrier || !Barrier->Initialize(Character.Get(), Slot, AimLocation, nullptr))
		{
			if (Barrier) { Barrier->Destroy(); }
			return RejectInput(TEXT("Sanctuary assets unavailable"));
		}
		if (CounterBarrier.IsValid()) { CounterBarrier->Destroy(); }
		CounterBarrier = Barrier;
		SanctuaryCast = Barrier;
	}
	Character->CancelBasicAttackForSkill();
	if (Character->GetController()) { Character->GetController()->StopMovement(); }
	Character->GetCharacterMovement()->StopMovementImmediately();
	if (!Facing.IsNearlyZero()) { Character->SetActorRotation(Facing.Rotation()); }
	if (Barrier) { Barrier->FinishSpawning(Transform); }
	if (Volley)
	{
		Volley->FinishSpawning(Transform);
		if (!IsValid(Volley) || Volley->IsActorBeingDestroyed()) { return RejectInput(TEXT("Sharp Shooter animation unavailable")); }
	}
	NextSanctuarySkillTimes[Slot == 9 ? 0 : 1] = GetWorld()->GetTimeSeconds() + (Slot == 9 ? 8.0 : 12.0);
	Feedback = Slot == 9 ? TEXT("Sharp Shooter: close-range burst") : TEXT("Counter Ward: frontal native projectiles");
	FeedbackDeadline = GetWorld()->GetTimeSeconds() + 1.25;
	return true;
}

bool USparrowSkillComponent::IsSanctuaryCasting() const
{
	return (SharpVolley.IsValid() && SharpVolley->IsCasting()) ||
		(SanctuaryCast.IsValid() && SanctuaryCast->IsCasting());
}

int32 USparrowSkillComponent::GetSanctuaryActiveSlot() const
{
	return SharpVolley.IsValid() && SharpVolley->IsCasting() ? 9 :
		(SanctuaryCast.IsValid() && SanctuaryCast->IsCasting() ? SanctuaryCast->GetSlot() : INDEX_NONE);
}

float USparrowSkillComponent::GetSanctuaryCooldownRemaining(int32 Slot) const
{
	if ((Slot != 9 && Slot != 11) || IgnoresCooldowns() || !GetWorld()) { return 0.0f; }
	return static_cast<float>(FMath::Max(0.0, NextSanctuarySkillTimes[Slot == 9 ? 0 : 1] - GetWorld()->GetTimeSeconds()));
}

FText USparrowSkillComponent::GetSanctuaryName(int32 Slot) const
{
	return Slot == 9 ? FText::FromString(TEXT("Sharp Shooter")) :
		(Slot == 11 ? FText::FromString(TEXT("Counter Ward")) : FText::GetEmpty());
}

FText USparrowSkillComponent::GetSanctuaryStatus(int32 Slot) const
{
	if (Slot == 9) { return FText::FromString(TEXT("Close burst | 54 damage | 450cm")); }
	if (Slot != 11) { return FText::GetEmpty(); }
	if (!CounterBarrier.IsValid() || CounterBarrier->GetRemainingSeconds() <= 0.0f) { return FText::GetEmpty(); }
	return FText::FromString(FString::Printf(TEXT("Guard %.1fs / %d counter"),
		CounterBarrier->GetRemainingSeconds(), CounterBarrier->GetCounterShotCount()));
}

void USparrowSkillComponent::CancelSanctuaryCast()
{
	if (SharpVolley.IsValid() && SharpVolley->IsCasting()) { SharpVolley->Destroy(); }
	if (SanctuaryCast.IsValid() && SanctuaryCast->IsCasting()) { SanctuaryCast->Destroy(); }
	SanctuaryCast.Reset();
}

void USparrowSkillComponent::CleanupSanctuarySkills()
{
	if (SanctuaryCast.IsValid()) { SanctuaryCast->Destroy(); }
	if (SharpVolley.IsValid()) { SharpVolley->Destroy(); }
	if (CounterBarrier.IsValid()) { CounterBarrier->Destroy(); }
	SanctuaryCast.Reset();
	SharpVolley.Reset();
	CounterBarrier.Reset();
}
