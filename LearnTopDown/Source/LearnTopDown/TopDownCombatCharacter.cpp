#include "TopDownCombatCharacter.h"

#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Components/SkeletalMeshComponent.h"
#include "CharacterSkillComponent.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"

const FName ATopDownCombatCharacter::SkillComponentName(TEXT("CountessSkills"));

ATopDownCombatCharacter::ATopDownCombatCharacter(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer)
{
	CountessSkills = CreateDefaultSubobject<UCharacterSkillComponent>(SkillComponentName);
	PrimaryActorTick.bCanEverTick = false;
	bUseControllerRotationYaw = false;
	GetCharacterMovement()->bOrientRotationToMovement = true;
	GetCharacterMovement()->RotationRate = FRotator(0.0f, 640.0f, 0.0f);
}

void ATopDownCombatCharacter::InterruptIntroAnimation()
{
	UAnimInstance* AnimInstance = GetMesh() ? GetMesh()->GetAnimInstance() : nullptr;
	UAnimMontage* Montage = AnimInstance ? AnimInstance->GetCurrentActiveMontage() : nullptr;
	if (Montage && Montage->GetFName() == IntroMontageName)
	{
		// 입력에 즉시 반응하도록 등장 몽타주만 페이드 없이 중단한다.
		AnimInstance->Montage_Stop(0.0f, Montage);
	}
}

FVector ATopDownCombatCharacter::GetLocomotionAnimationVelocity(UCharacterMovementComponent* Movement)
{
	if (!Movement)
	{
		return FVector::ZeroVector;
	}
	const ATopDownCombatCharacter* Character = Cast<ATopDownCombatCharacter>(Movement->GetOwner());
	if (Character && Character->IsCombatBusy())
	{
		return FVector::ZeroVector;
	}
	// 실제 정지를 즉시 전달하고, 자세의 부드러운 연결은 AnimBP의 전환 블렌드에 맡긴다.
	return Movement->Velocity;
}

bool ATopDownCombatCharacter::TryBasicAttack(const FVector& AimLocation)
{
	if (!GetMesh() || !GetMesh()->GetAnimInstance() ||
		GetCharacterMovement()->MovementMode != MOVE_Walking || (CountessSkills && CountessSkills->IsCasting()))
	{
		return false;
	}

	if (bAttacking)
	{
		if (ComboAttacks.IsEmpty() || bAttackQueued || !AttackAnimInstance.IsValid() ||
			AttackAnimInstance.Get() != GetMesh()->GetAnimInstance())
		{
			return false;
		}
		// 마지막 타에서는 새 1타를 예약하지 않는다. 쿨타임 뒤의 새 입력으로 시작한다.
		if (ComboRestartCooldown > 0.0f && ComboAttackIndex == ComboAttacks.Num() - 1)
		{
			return false;
		}
		// 원본 SaveAttack처럼 다음 입력 한 번만 보관한다. 연타를 무한히 쌓지 않는다.
		QueuedAimLocation = AimLocation;
		bAttackQueued = true;
		return true;
	}
	if (GetWorld()->GetTimeSeconds() < NextBasicAttackTime)
	{
		return false;
	}
	return StartAttackStep(0, AimLocation);
}

void ATopDownCombatCharacter::SetHeldBasicAttackInput(bool bHeld, const FVector& AimLocation)
{
	// 유지 입력은 수동 클릭 예약과 분리한다. 해제해도 이미 예약한 클릭 콤보는 지우지 않는다.
	bHeldBasicAttackInput = bHeld && !AimLocation.ContainsNaN();
	HeldBasicAttackAimLocation = bHeldBasicAttackInput ? AimLocation : FVector::ZeroVector;
}

bool ATopDownCombatCharacter::IsCombatBusy() const
{
	return bAttacking || (CountessSkills && CountessSkills->IsCasting());
}

void ATopDownCombatCharacter::CancelBasicAttackForSkill()
{
	if (bAttacking)
	{
		UAnimInstance* AnimInstance = AttackAnimInstance.Get();
		UAnimMontage* Montage = ActiveAttackMontage;
		// 먼저 타격 예약을 정리해 스킬 모션에 이전 평타의 피해가 섞이지 않게 한다.
		FinishAttack();
		if (AnimInstance && Montage)
		{
			AnimInstance->Montage_Stop(0.06f, Montage);
		}
	}
}

UAnimMontage* ATopDownCombatCharacter::GetBasicAttackMontage(UAnimMontage* ConfiguredMontage) const
{
	return ConfiguredMontage;
}

float ATopDownCombatCharacter::GetBasicAttackHitDelay(UAnimMontage* Montage, float Duration, float HitFraction) const
{
	return Duration * FMath::Clamp(HitFraction, 0.05f, 0.95f);
}

bool ATopDownCombatCharacter::StartAttackStep(int32 StepIndex, const FVector& AimLocation)
{
	const bool bUsesCombo = !ComboAttacks.IsEmpty();
	if (bUsesCombo && !ComboAttacks.IsValidIndex(StepIndex))
	{
		return false;
	}
	UAnimMontage* ConfiguredMontage = bUsesCombo ? ComboAttacks[StepIndex].Montage.Get() : BasicAttackMontage.Get();
	UAnimMontage* Montage = GetBasicAttackMontage(ConfiguredMontage);
	if (!Montage || !GetMesh())
	{
		return false;
	}
	const float PlayRate = bUsesCombo ? FMath::Max(ComboAttacks[StepIndex].PlayRate, 0.1f) : 1.0f;
	const float EffectivePlayRate = PlayRate * Montage->RateScale;
	if (EffectivePlayRate <= 0.0f)
	{
		return false;
	}
	UAnimInstance* AnimInstance = GetMesh()->GetAnimInstance();
	if (!AnimInstance || GetCharacterMovement()->MovementMode != MOVE_Walking ||
		(bAttacking && AttackAnimInstance.Get() != AnimInstance))
	{
		return false;
	}

	// 이전 타의 종료 콜백이 늦게 도착해도 새 타의 상태를 해제하지 않도록 구분한다.
	++AttackGeneration;
	ClearAttackTimers();
	if (!bAttacking)
	{
		bSavedOrientRotationToMovement = GetCharacterMovement()->bOrientRotationToMovement;
		SavedRootMotionMode = AnimInstance->RootMotionMode;
		AttackAnimInstance = AnimInstance;
		bAttacking = true;
	}
	// 제자리 기본 공격이므로 원본 모션의 루트 이동은 적용하지 않는다.
	AnimInstance->SetRootMotionMode(ERootMotionMode::IgnoreRootMotion);
	GetCharacterMovement()->bOrientRotationToMovement = false;
	bAttackQueued = false;
	bHitApplied = false;
	ComboAttackIndex = StepIndex;
	ActiveAttackMontage = Montage;
	// 현재 타의 목표는 예약한 다음 타와 분리해 높이와 활 발사 위치의 차이를 보존한다.
	ActiveAttackAimLocation = AimLocation;
	const float Duration = AnimInstance->Montage_Play(
		Montage, PlayRate, EMontagePlayReturnType::Duration);
	if (Duration <= 0.0f)
	{
		FinishAttack();
		return false;
	}

	if (Controller)
	{
		Controller->StopMovement();
	}
	GetCharacterMovement()->StopMovementImmediately();

	const FVector Direction = (AimLocation - GetActorLocation()).GetSafeNormal2D();
	if (!Direction.IsNearlyZero())
	{
		SetActorRotation(FRotator(0.0f, Direction.Rotation().Yaw, 0.0f));
	}

	FOnMontageEnded EndDelegate;
	EndDelegate.BindUObject(this, &ATopDownCombatCharacter::OnAttackEnded, AttackGeneration);
	AnimInstance->Montage_SetEndDelegate(EndDelegate, Montage);
	FOnMontageBlendingOutStarted BlendDelegate;
	BlendDelegate.BindUObject(this, &ATopDownCombatCharacter::OnAttackBlendingOut, AttackGeneration);
	AnimInstance->Montage_SetBlendingOutDelegate(BlendDelegate, Montage);
	const float HitFraction = bUsesCombo ? ComboAttacks[StepIndex].HitTimeFraction : HitTimeFraction;
	const float HitDelay = GetBasicAttackHitDelay(Montage, Duration, HitFraction);
	GetWorldTimerManager().SetTimer(HitTimer, this, &ATopDownCombatCharacter::ApplyAttackHit, HitDelay, false);
	if (RecoveryAfterHit > 0.0f && !ShouldFinishBasicAttackMontage())
	{
		GetWorldTimerManager().SetTimer(RecoveryCutTimer, this, &ATopDownCombatCharacter::CutAttackRecovery,
			HitDelay + RecoveryAfterHit, false);
	}
	if (bUsesCombo)
	{
		// 원본 몽타주의 명명 노티파이는 원본 BP 타입에 종속된다. 저장된 시점을 읽어 같은 규칙으로 실행한다.
		for (const FAnimNotifyEvent& Notify : Montage->Notifies)
		{
			// 모션 재생 속도에 맞춰 타격 연계와 초기화 시점도 함께 당긴다.
			const float TriggerTime = Notify.GetTriggerTime() / EffectivePlayRate;
			if (TriggerTime <= 0.0f || TriggerTime >= Duration)
			{
				continue;
			}
			if (Notify.NotifyName == TEXT("SaveAttack"))
			{
				GetWorldTimerManager().SetTimer(ComboAdvanceTimer, this, &ATopDownCombatCharacter::ContinueCombo, TriggerTime, false);
			}
			else if (Notify.NotifyName == TEXT("ResetCombo") && !ShouldFinishBasicAttackMontage())
			{
				GetWorldTimerManager().SetTimer(ComboResetTimer, this, &ATopDownCombatCharacter::FinishAttack, TriggerTime, false);
			}
		}
	}
	// 블루프린트가 애니메이션 인스턴스를 교체해 종료 콜백이 사라져도 입력을 복구한다.
	GetWorldTimerManager().SetTimer(RecoveryTimer, this, &ATopDownCombatCharacter::FinishAttack,
		Duration + 0.1f, false);
	return true;
}

void ATopDownCombatCharacter::ContinueCombo()
{
	if (!bAttacking || (!bAttackQueued && !bHeldBasicAttackInput) || ComboAttacks.IsEmpty())
	{
		return;
	}
	// 정상 블렌드 아웃 중에도 원본 SaveAttack 시점은 유효하다. 중단 여부는 전용 콜백에서 처리한다.
	if (!AttackAnimInstance.IsValid() || AttackAnimInstance.Get() != GetMesh()->GetAnimInstance())
	{
		FinishAttack();
		return;
	}
	// 수동 클릭을 우선하고, 유지 입력은 원래 SaveAttack 시점에만 현재 조준으로 한 번 소비한다.
	const FVector AimLocation = bAttackQueued ? QueuedAimLocation : HeldBasicAttackAimLocation;
	// 원본 AttackCount처럼 3타 다음 입력은 새 1타로 순환한다.
	// 쿨타임이 있으면 마지막 타는 끝까지 재생하고, 새 입력은 종료 후 제한한다.
	if (ComboRestartCooldown > 0.0f && ComboAttackIndex == ComboAttacks.Num() - 1)
	{
		return;
	}
	if (!StartAttackStep((ComboAttackIndex + 1) % ComboAttacks.Num(), AimLocation))
	{
		FinishAttack();
	}
}

void ATopDownCombatCharacter::ApplyAttackHit()
{
	if (!bAttacking || bHitApplied || !GetMesh()->GetAnimInstance() ||
		AttackAnimInstance.Get() != GetMesh()->GetAnimInstance() ||
		GetMesh()->GetAnimInstance()->Montage_GetIsStopped(ActiveAttackMontage))
	{
		return;
	}
	bHitApplied = true;
	ExecuteBasicAttackHit();
}

void ATopDownCombatCharacter::CutAttackRecovery()
{
	// 다음 타로 이어질 입력이 있으면 원본 SaveAttack 연계를 기다린다. 쿨타임이 있는 마지막 타는 이어지지 않으므로 끊는다.
	const bool bCanChain = !ComboAttacks.IsEmpty() &&
		!(ComboRestartCooldown > 0.0f && ComboAttackIndex == ComboAttacks.Num() - 1);
	if (!bAttacking || (bCanChain && (bAttackQueued || bHeldBasicAttackInput)))
	{
		return;
	}
	UAnimInstance* AnimInstance = AttackAnimInstance.Get();
	UAnimMontage* Montage = ActiveAttackMontage;
	// 상태를 먼저 풀어 끊긴 몽타주의 종료 콜백이 새 입력을 건드리지 않게 하고, 남은 동작은 짧게 섞어 내린다.
	FinishAttack();
	if (AnimInstance && Montage)
	{
		AnimInstance->Montage_Stop(0.15f, Montage);
	}
}

void ATopDownCombatCharacter::ExecuteBasicAttackHit()
{
	const FVector Origin = GetActorLocation();
	const FVector Forward = GetActorForwardVector();
	const float MinDot = FMath::Cos(FMath::DegreesToRadians(AttackHalfAngle));
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_Pawn);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	FCollisionQueryParams Query(SCENE_QUERY_STAT(KwangBasicAttack), false, this);
	TArray<FOverlapResult> Overlaps;
	GetWorld()->OverlapMultiByObjectType(Overlaps, Origin, FQuat::Identity, Objects,
		FCollisionShape::MakeSphere(AttackRange), Query);
	TSet<AActor*> HitActors;

	for (const FOverlapResult& Overlap : Overlaps)
	{
		AActor* Target = Overlap.GetActor();
		if (!IsValid(Target) || Target == this || !Target->CanBeDamaged() || HitActors.Contains(Target))
		{
			continue;
		}
		const FVector Offset = Target->GetActorLocation() - Origin;
		if (Offset.SizeSquared2D() > FMath::Square(AttackRange) || FMath::Abs(Offset.Z) > 120.0f ||
			FVector::DotProduct(Forward, Offset.GetSafeNormal2D()) < MinDot)
		{
			continue;
		}

		FHitResult Hit;
		// 벽 너머의 대상을 타격하지 않도록 시야를 확인한다.
		if (GetWorld()->LineTraceSingleByChannel(Hit, Origin, Target->GetActorLocation(), ECC_Visibility, Query)
			&& Hit.GetActor() != Target)
		{
			continue;
		}
		if (!Hit.bBlockingHit)
		{
			Hit = FHitResult(Target, Overlap.GetComponent(), Target->GetActorLocation(), -Forward);
		}
		HitActors.Add(Target);
		UGameplayStatics::ApplyPointDamage(Target, AttackDamage, Forward, Hit, Controller, this, nullptr);
	}
}

void ATopDownCombatCharacter::OnAttackEnded(UAnimMontage* Montage, bool bInterrupted, uint32 Generation)
{
	if (Generation == AttackGeneration && Montage == ActiveAttackMontage)
	{
		FinishAttack();
	}
}

void ATopDownCombatCharacter::OnAttackBlendingOut(UAnimMontage* Montage, bool bInterrupted, uint32 Generation)
{
	if (bInterrupted && Generation == AttackGeneration && Montage == ActiveAttackMontage)
	{
		FinishAttack();
	}
}

void ATopDownCombatCharacter::ClearAttackTimers()
{
	GetWorldTimerManager().ClearTimer(HitTimer);
	GetWorldTimerManager().ClearTimer(RecoveryTimer);
	GetWorldTimerManager().ClearTimer(ComboAdvanceTimer);
	GetWorldTimerManager().ClearTimer(ComboResetTimer);
	GetWorldTimerManager().ClearTimer(RecoveryCutTimer);
}

void ATopDownCombatCharacter::FinishAttack()
{
	// 타격을 실행한 마지막 타에만 적용한다. 중복 종료 콜백은 쿨타임을 연장하지 않는다.
	if (bAttacking && bHitApplied && !ComboAttacks.IsEmpty() && ComboAttackIndex == ComboAttacks.Num() - 1)
	{
		NextBasicAttackTime = GetWorld()->GetTimeSeconds() + FMath::Max(ComboRestartCooldown, 0.0f);
	}
	ClearAttackTimers();
	++AttackGeneration;
	bAttackQueued = false;
	ComboAttackIndex = 0;
	ActiveAttackMontage = nullptr;
	ActiveAttackAimLocation = FVector::ZeroVector;
	if (bAttacking)
	{
		if (AttackAnimInstance.IsValid())
		{
			AttackAnimInstance->SetRootMotionMode(SavedRootMotionMode);
		}
		AttackAnimInstance.Reset();
		GetCharacterMovement()->bOrientRotationToMovement = bSavedOrientRotationToMovement;
		bAttacking = false;
	}
}

void ATopDownCombatCharacter::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	SetHeldBasicAttackInput(false);
	if (CountessSkills)
	{
		CountessSkills->CancelSkill();
	}
	FinishAttack();
	Super::EndPlay(EndPlayReason);
}
