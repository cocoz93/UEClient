#include "TrialTowerMonster.h"
#include "TrialTowerEncounter.h"
#include "TrialTowerAnimInstance.h"

#include "AIController.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Navigation/PathFollowingComponent.h"
#include "TimerManager.h"

namespace
{
	constexpr float AttackRange = 220.0f;
	constexpr float AttackHeightTolerance = 120.0f;
	constexpr float AttackWindup = 0.55f;
	constexpr float AttackDuration = 1.2f;
	constexpr float AttackCooldown = 0.35f;
	constexpr float AttackDamage = 10.0f;
	constexpr float AttackBlendIn = 0.12f;
	constexpr float AttackBlendOut = 0.20f;
}

ATrialTowerMonster::ATrialTowerMonster()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickInterval = 0.1f;
	AIControllerClass = AAIController::StaticClass();
	AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
	bUseControllerRotationYaw = false;
	SetCanBeDamaged(true);
	Tags.Add(TEXT("TrialTowerMonster"));

	GetCapsuleComponent()->InitCapsuleSize(38.0f, 90.0f);
	GetCapsuleComponent()->SetCollisionProfileName(TEXT("Pawn"));
	GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
	GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);
	GetMesh()->SetRelativeLocation(FVector(0.0f, 0.0f, -90.0f));
	GetMesh()->SetRelativeRotation(FRotator(0.0f, -90.0f, 0.0f));
	GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);

	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->bOrientRotationToMovement = true;
	Movement->RotationRate = FRotator(0.0f, 540.0f, 0.0f);
	Movement->MaxWalkSpeed = 230.0f;
	Movement->bUseRVOAvoidance = true;
	Movement->AvoidanceConsiderationRadius = 240.0f;
}

void ATrialTowerMonster::InitializeEncounter(ATrialTowerEncounter* InEncounter)
{
	// Possession changes a pawn's Actor owner to its controller. Keep the
	// map-local combat context separately from that engine-owned relationship.
	Encounter = InEncounter;
}

void ATrialTowerMonster::InitializeForFloor(float InMaxHealth, float InMoveSpeed)
{
	if (bDefeated)
	{
		return;
	}
	MaxHealth = FMath::IsFinite(InMaxHealth) ? FMath::Max(1.0f, InMaxHealth) : 100.0f;
	Health = MaxHealth;
	GetCharacterMovement()->MaxWalkSpeed = FMath::IsFinite(InMoveSpeed) ? FMath::Max(1.0f, InMoveSpeed) : 230.0f;
	bInitializedForFloor = true;
}

void ATrialTowerMonster::BeginPlay()
{
	Super::BeginPlay();
	if (!bInitializedForFloor)
	{
		MaxHealth = FMath::IsFinite(MaxHealth) ? FMath::Max(1.0f, MaxHealth) : 100.0f;
		Health = MaxHealth;
	}
	UpdateLocomotionAnimation();
	// MoveToActor observes a moving target; the timer only restarts idle paths or
	// retargets when the player's 1-4 selection replaces the possessed pawn.
	GetWorldTimerManager().SetTimer(PursuitTimer, this, &ATrialTowerMonster::RefreshPursuit,
		0.4f, true, FMath::FRandRange(0.1f, 0.35f));
}

void ATrialTowerMonster::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	GetWorldTimerManager().ClearTimer(PursuitTimer);
	GetWorldTimerManager().ClearTimer(AttackHitTimer);
	GetWorldTimerManager().ClearTimer(AttackEndTimer);
	Super::EndPlay(EndPlayReason);
}

void ATrialTowerMonster::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (IsAlive() && !bAttacking)
	{
		UpdateLocomotionAnimation();
	}
}

void ATrialTowerMonster::RefreshPursuit()
{
	if (!CanFight())
	{
		StopCombat();
		return;
	}
	if (bAttacking)
	{
		return;
	}
	if (!GetController())
	{
		SpawnDefaultController();
	}
	AAIController* AI = Cast<AAIController>(GetController());
	APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!AI)
	{
		return;
	}
	if (!IsValid(Player) || Player == this)
	{
		AI->StopMovement();
		ChaseTarget.Reset();
		return;
	}
	if (IsWithinAttackRange(Player) && GetWorld()->GetTimeSeconds() >= NextAttackTime)
	{
		StartAttack(Player);
		return;
	}
	const float StopDistance = ChaseAcceptanceRadius + GetSimpleCollisionRadius() + Player->GetSimpleCollisionRadius() + 20.0f;
	const bool bNeedsNewPath = AI->GetMoveStatus() != EPathFollowingStatus::Moving &&
		FVector::DistSquared2D(GetActorLocation(), Player->GetActorLocation()) > FMath::Square(StopDistance);
	if (ChaseTarget.Get() != Player || bNeedsNewPath)
	{
		ChaseTarget = Player;
		AI->MoveToActor(Player, ChaseAcceptanceRadius, true, true, false, nullptr, true);
	}
}

bool ATrialTowerMonster::CanFight() const
{
	const ATrialTowerEncounter* Run = Encounter.Get();
	return IsAlive() && !bCombatStopped && Run && Run->CanMonstersAttack();
}

bool ATrialTowerMonster::IsWithinAttackRange(const APawn* Target) const
{
	if (!IsValid(Target)) { return false; }
	const FVector Offset = Target->GetActorLocation() - GetActorLocation();
	return Offset.SizeSquared2D() <= FMath::Square(AttackRange) &&
		FMath::Abs(Offset.Z) <= AttackHeightTolerance;
}

void ATrialTowerMonster::StartAttack(APawn* Target)
{
	if (!CanFight() || bAttacking || !IsWithinAttackRange(Target)) { return; }
	bAttacking = true;
	AttackTarget = Target;
	if (AAIController* AI = Cast<AAIController>(GetController()))
	{
		AI->StopMovement();
	}
	GetCharacterMovement()->StopMovementImmediately();
	GetCharacterMovement()->bOrientRotationToMovement = false;
	GetCharacterMovement()->SetAvoidanceEnabled(false);
	// Commit the facing at windup; the strike never tracks a dodging target.
	const FVector Direction = Target->GetActorLocation() - GetActorLocation();
	SetActorRotation(FRotator(0.0f, Direction.Rotation().Yaw, 0.0f));
	PlayingAnimation.Reset();
	if (AttackAnimation)
	{
		const float PlayRate = FMath::Max(0.01f, AttackAnimation->GetPlayLength() / AttackDuration);
		if (UTrialTowerAnimInstance* Animation = Cast<UTrialTowerAnimInstance>(GetMesh()->GetAnimInstance()))
		{
			// The slot blends back to the continuously evaluated locomotion pose
			// during the final recovery, instead of replacing it on the timer tick.
			Animation->PlaySlotAnimationAsDynamicMontage(AttackAnimation, TEXT("DefaultSlot"),
				AttackBlendIn, AttackBlendOut, PlayRate);
		}
		else
		{
			GetMesh()->PlayAnimation(AttackAnimation, false);
			GetMesh()->SetPlayRate(PlayRate);
		}
	}
	GetWorldTimerManager().SetTimer(AttackHitTimer, this, &ATrialTowerMonster::ApplyAttackHit, AttackWindup, false);
	GetWorldTimerManager().SetTimer(AttackEndTimer, this, &ATrialTowerMonster::FinishAttack, AttackDuration, false);
}

void ATrialTowerMonster::ApplyAttackHit()
{
	APawn* Target = AttackTarget.Get();
	if (!CanFight() || !bAttacking || !IsWithinAttackRange(Target) ||
		UGameplayStatics::GetPlayerPawn(this, 0) != Target) { return; }
	const FVector Direction = (Target->GetActorLocation() - GetActorLocation()).GetSafeNormal2D();
	// A 60-degree half-angle allows a sidestep to evade the committed swing.
	if (FVector::DotProduct(GetActorForwardVector(), Direction) < 0.5f) { return; }
	FHitResult Hit;
	FCollisionQueryParams Query(SCENE_QUERY_STAT(TrialTowerMelee), false, this);
	if (GetWorld()->LineTraceSingleByChannel(Hit, GetActorLocation(), Target->GetActorLocation(),
		ECC_Visibility, Query) && Hit.GetActor() != Target) { return; }
	// Existing character TakeDamage overrides (including Aurora's protection)
	// run before the shared player combat component receives OnTakeAnyDamage.
	UGameplayStatics::ApplyDamage(Target, AttackDamage, GetController(), this, nullptr);
}

void ATrialTowerMonster::FinishAttack()
{
	bAttacking = false;
	AttackTarget.Reset();
	if (!CanFight())
	{
		StopCombat();
		return;
	}
	GetCharacterMovement()->bOrientRotationToMovement = true;
	GetCharacterMovement()->SetAvoidanceEnabled(true);
	NextAttackTime = GetWorld()->GetTimeSeconds() + AttackCooldown;
	UpdateLocomotionAnimation();
	RefreshPursuit();
}

void ATrialTowerMonster::StopCombat()
{
	bCombatStopped = true;
	// A defeated player's lingering projectiles/fields cannot alter the stopped
	// encounter. Restart creates fresh monsters instead of resuming these actors.
	SetCanBeDamaged(false);
	bAttacking = false;
	AttackTarget.Reset();
	ChaseTarget.Reset();
	GetWorldTimerManager().ClearTimer(PursuitTimer);
	GetWorldTimerManager().ClearTimer(AttackHitTimer);
	GetWorldTimerManager().ClearTimer(AttackEndTimer);
	if (AAIController* AI = Cast<AAIController>(GetController()))
	{
		AI->StopMovement();
	}
	GetCharacterMovement()->StopMovementImmediately();
	GetCharacterMovement()->SetAvoidanceEnabled(false);
	if (IsAlive())
	{
		if (UTrialTowerAnimInstance* Animation = Cast<UTrialTowerAnimInstance>(GetMesh()->GetAnimInstance()))
		{
			Animation->ClearHitReaction();
			Animation->Montage_Stop(AttackBlendOut);
		}
		PlayingAnimation.Reset();
		UpdateLocomotionAnimation();
	}
}

void ATrialTowerMonster::UpdateLocomotionAnimation()
{
	// The tower AnimBlueprint evaluates and blends locomotion every animation
	// frame; never replace that instance with a single-node idle after an attack.
	if (Cast<UTrialTowerAnimInstance>(GetMesh()->GetAnimInstance())) { return; }
	const float Speed = GetVelocity().Size2D();
	bRunning = Speed > (bRunning ? 8.0f : 20.0f);
	UAnimSequence* NextAnimation = bRunning && RunAnimation ? RunAnimation.Get() : IdleAnimation.Get();
	if (NextAnimation && PlayingAnimation.Get() != NextAnimation)
	{
		GetMesh()->PlayAnimation(NextAnimation, true);
		PlayingAnimation = NextAnimation;
	}
	GetMesh()->SetPlayRate(bRunning ? FMath::Clamp(Speed / 230.0f, 0.65f, 1.4f) : 1.0f);
}

float ATrialTowerMonster::TakeDamage(float DamageAmount, const FDamageEvent& DamageEvent,
	AController* EventInstigator, AActor* DamageCauser)
{
	if (!IsAlive() || !CanBeDamaged() || !FMath::IsFinite(DamageAmount) || DamageAmount <= 0.0f)
	{
		return 0.0f;
	}
	const float AppliedDamage = FMath::Min(DamageAmount, Health);
	Health -= AppliedDamage;
	Super::TakeDamage(AppliedDamage, DamageEvent, EventInstigator, DamageCauser);
	if (Health <= 0.0f)
	{
		Defeat();
	}
	else if (UTrialTowerAnimInstance* Animation = Cast<UTrialTowerAnimInstance>(GetMesh()->GetAnimInstance()))
	{
		const AActor* Source = IsValid(DamageCauser) ? DamageCauser :
			(EventInstigator ? EventInstigator->GetPawn() : nullptr);
		const FVector TowardSource = Source ?
			(Source->GetActorLocation() - GetActorLocation()).GetSafeNormal2D() : GetActorForwardVector();
		Animation->PlayHitReaction(TowardSource);
	}
	return AppliedDamage;
}

void ATrialTowerMonster::Defeat()
{
	if (bDefeated || IsActorBeingDestroyed())
	{
		return;
	}
	bDefeated = true;
	Health = 0.0f;
	SetCanBeDamaged(false);
	StopCombat();
	GetCharacterMovement()->DisableMovement();
	GetCharacterMovement()->SetAvoidanceEnabled(false);
	SetActorEnableCollision(false);
	SetActorTickEnabled(false);
	DetachFromControllerPendingDestroy();
	ChaseTarget.Reset();
	if (DeathAnimation)
	{
		GetMesh()->PlayAnimation(DeathAnimation, false);
		GetMesh()->SetPlayRate(1.0f);
	}
	else
	{
		GetMesh()->Stop();
	}
	SetLifeSpan(DeathAnimation ? FMath::Clamp(DeathAnimation->GetPlayLength() + 0.25f, 1.0f, 4.0f) : 1.0f);
	// State is terminal before notifying the encounter, so duplicate damage and
	// destruction callbacks cannot count this defeat a second time.
	OnDefeated.Broadcast(this);
}
