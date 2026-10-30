#include "PlayerCombatComponent.h"

#include "TopDownCombatCharacter.h"
#include "CharacterSkillComponent.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "Engine/SkeletalMesh.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/RootMotionSource.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"
#include "Kismet/GameplayStatics.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"

namespace
{
	constexpr float PlayerHitRecovery = 0.12f;
	constexpr float PlayerHitProtection = 0.75f;
	constexpr float HitReactionBlendIn = 0.04f;
	constexpr float HitReactionBlendOut = 0.16f;
	constexpr float LightHitBlendIn = 0.02f;
	constexpr float LightHitBlendOut = 0.10f;
	constexpr float LightHitWeight = 1.0f;
	constexpr float LightHitPlayRate = 2.0f;
	constexpr float DamageTrailHold = 0.25f;
	constexpr float DamageTrailFade = 0.45f;
	constexpr float HardControlRecoveryProtection = 0.75f;

	EPlayerHitDirection ResolveHitDirection(const AActor& Character, const AActor* Source)
	{
		if (!IsValid(Source) || Source == &Character) { return EPlayerHitDirection::Front; }
		const FVector TowardSource = (Source->GetActorLocation() - Character.GetActorLocation()).GetSafeNormal2D();
		if (TowardSource.IsNearlyZero() || TowardSource.ContainsNaN()) { return EPlayerHitDirection::Front; }
		const float Forward = FVector::DotProduct(Character.GetActorForwardVector(), TowardSource);
		const float Right = FVector::DotProduct(Character.GetActorRightVector(), TowardSource);
		if (FMath::Abs(Forward) >= FMath::Abs(Right))
		{
			return Forward >= 0.0f ? EPlayerHitDirection::Front : EPlayerHitDirection::Back;
		}
		return Right >= 0.0f ? EPlayerHitDirection::Right : EPlayerHitDirection::Left;
	}
}

UPlayerCombatComponent::UPlayerCombatComponent()
{
	PrimaryComponentTick.bCanEverTick = false;
	const auto LoadAnimation = [](const TCHAR* Path)
	{
		ConstructorHelpers::FObjectFinder<UAnimSequence> Animation(Path);
		return Animation.Object;
	};
	const auto AddAnimations = [this, &LoadAnimation](const TCHAR* Hero, const TCHAR* Hit,
		const TCHAR* Back, const TCHAR* Left, const TCHAR* Right, const TCHAR* StunStart,
		const TCHAR* StunLoop, const TCHAR* Knockback, const TCHAR* Death, const TCHAR* Slot)
	{
		const FString Base = FString::Printf(TEXT("/Game/Paragon%s/Characters/Heroes/%s/Animations/"), Hero, Hero);
		const auto Load = [&LoadAnimation, &Base](const TCHAR* Name) { return LoadAnimation(*(Base + Name)); };
		FPlayerCombatAnimations& Animations = CharacterAnimations.AddDefaulted_GetRef();
		Animations.HitReaction = Load(Hit);
		Animations.HitBack = Load(Back);
		Animations.HitLeft = Load(Left);
		Animations.HitRight = Load(Right);
		Animations.StunStart = Load(StunStart);
		Animations.StunLoop = Load(StunLoop);
		Animations.Knockback = Load(Knockback);
		Animations.Death = Load(Death);
		Animations.HitReactionSlot = Slot;
	};
	AddAnimations(TEXT("Countess"), TEXT("Hitreact_Fwd"), TEXT("Hitreact_Bwd"), TEXT("Hitreact_Left"), TEXT("Hitreact_Right"),
		TEXT("Stun_Start"), TEXT("Stun_Loop"), TEXT("Knock_Fwd"), TEXT("Death"), TEXT("CountessFullBody"));
	CharacterAnimations.Last().bNonInterruptingDamageFeedback = true;
	ConstructorHelpers::FObjectFinder<UParticleSystem> DamageEffect(
		TEXT("/Game/TopDown/Combat/FX/BloodStudy20261030/P_FleshHitB2.P_FleshHitB2"));
	FleshHitEffect = DamageEffect.Object;
	AddAnimations(TEXT("Sparrow"), TEXT("HitReact_Fwd"), TEXT("HitReact_Bwd"), TEXT("HitReact_Left"), TEXT("HitReact_Right"),
		TEXT("Stunned_Start"), TEXT("Stunned_Loop"), TEXT("Knock_Fwd"), TEXT("Death_Fwd"), TEXT("SparrowFullBody"));
	AddAnimations(TEXT("Gideon"), TEXT("HitReact_Front"), TEXT("HitReact_Back"), TEXT("HitReact_Left"), TEXT("HitReact_Right"),
		TEXT("Stun_Start"), TEXT("Stun_Loop"), TEXT("Knock_Fwd"), TEXT("Death_Fwd"), TEXT("UpperBody"));
	AddAnimations(TEXT("Aurora"), TEXT("HitReact_Front"), TEXT("HitReact_Back"), TEXT("HitReact_Left"), TEXT("HitReact_Right"),
		TEXT("Stun_Start"), TEXT("Stun_Loop"), TEXT("Knockback_Fwd"), TEXT("Death"), TEXT("AuroraFullBody"));
}

void UPlayerCombatComponent::BeginPlay()
{
	Super::BeginPlay();
	if (APlayerController* Player = Cast<APlayerController>(GetOwner()))
	{
		PlayerController = Player;
		Player->OnPossessedPawnChanged.AddDynamic(this, &UPlayerCombatComponent::OnPlayerPawnChanged);
		OnPlayerPawnChanged(nullptr, Player->GetPawn());
	}
}

void UPlayerCombatComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	bShuttingDown = true;
	EndHitReaction();
	GetWorld()->GetTimerManager().ClearTimer(HitProtectionTimer);
	if (APawn* Pawn = PlayerPawn.Get())
	{
		Pawn->OnTakeAnyDamage.RemoveDynamic(this, &UPlayerCombatComponent::OnPlayerDamaged);
	}
	if (APlayerController* Player = PlayerController.Get())
	{
		Player->OnPossessedPawnChanged.RemoveDynamic(this, &UPlayerCombatComponent::OnPlayerPawnChanged);
	}
	ReleasePlayerInput();
	Super::EndPlay(EndPlayReason);
}

void UPlayerCombatComponent::NotifyStateChanged()
{
	if (!bShuttingDown) { OnStateChanged.Broadcast(); }
}

void UPlayerCombatComponent::OnPlayerPawnChanged(APawn* OldPawn, APawn* NewPawn)
{
	EndHitReaction();
	LastDamageReactionTime = -1000.0;
	// Health belongs to this player, so replacing a character cannot heal the player.
	if (APawn* Previous = PlayerPawn.Get())
	{
		Previous->OnTakeAnyDamage.RemoveDynamic(this, &UPlayerCombatComponent::OnPlayerDamaged);
	}
	PlayerPawn = Cast<ATopDownCombatCharacter>(NewPawn);
	if (PlayerPawn.IsValid())
	{
		NewPawn->OnTakeAnyDamage.AddUniqueDynamic(this, &UPlayerCombatComponent::OnPlayerDamaged);
		if (!bHasPlayerStart)
		{
			PlayerStartFeet = NewPawn->GetActorLocation() - FVector(0, 0, NewPawn->GetSimpleCollisionHalfHeight());
			PlayerStartRotation = NewPawn->GetActorRotation();
			bHasPlayerStart = true;
		}
		if (!bRespawning && !IsAlive()) { PresentDeath(); }
	}
}

bool UPlayerCombatComponent::IsInvulnerable() const
{
	return GetWorld() && Health > 0.0f && GetWorld()->GetTimeSeconds() < InvulnerableUntil;
}

bool UPlayerCombatComponent::UsesNonInterruptingDamageFeedback() const
{
	const FPlayerCombatAnimations* Animations = FindAnimations();
	return Animations && Animations->bNonInterruptingDamageFeedback;
}

float UPlayerCombatComponent::GetDamageFeedbackAge() const
{
	return GetWorld() ? FMath::Max(0.0f, static_cast<float>(GetWorld()->GetTimeSeconds() - LastDamageTime)) : 1000.0f;
}

float UPlayerCombatComponent::GetDamageReactionAge() const
{
	return GetWorld() ? FMath::Max(0.0f, static_cast<float>(GetWorld()->GetTimeSeconds() - LastDamageReactionTime)) : 1000.0f;
}

float UPlayerCombatComponent::GetDamageTrailHealth() const
{
	const float Alpha = FMath::Clamp((GetDamageFeedbackAge() - DamageTrailHold) / DamageTrailFade, 0.0f, 1.0f);
	return FMath::Lerp(DamageTrailHealth, Health, FMath::SmoothStep(0.0f, 1.0f, Alpha));
}

void UPlayerCombatComponent::OnPlayerDamaged(AActor* DamagedActor, float Damage,
	const UDamageType* DamageType, AController* InstigatedBy, AActor* DamageCauser)
{
	if (bShuttingDown || !bDamageEnabled || !IsAlive() || DamagedActor != PlayerPawn.Get() ||
		!FMath::IsFinite(Damage) || Damage <= 0.0f) { return; }
	AActor* Source = IsValid(DamageCauser) && DamageCauser != DamagedActor ? DamageCauser :
		(InstigatedBy ? InstigatedBy->GetPawn() : nullptr);
	// Only Countess opts into this visual response. Protected contacts do not
	// change health, the HUD damage trail, blood FX or the protection deadline.
	if (CanShowDamageReaction())
	{
		if (const ATopDownCombatCharacter* Character = Cast<ATopDownCombatCharacter>(PlayerPawn.Get()))
		{
			LastDamageReactionTime = GetWorld()->GetTimeSeconds();
			HitDirection = ResolveHitDirection(*Character, Source);
		}
	}
	if (IsInvulnerable()) { return; }
	// OnTakeAnyDamage observes the final damage after the character's defenses.
	DamageTrailHealth = FMath::Max(Health, GetDamageTrailHealth());
	LastDamageTime = GetWorld()->GetTimeSeconds();
	Health = FMath::Max(0.0f, Health - Damage);
	if (bHitReactionsEnabled) { PresentDamage(Source); }
	UE_LOG(LogTemp, Display, TEXT("PlayerCombat hit damage=%.1f health=%.1f"), Damage, Health);
	if (!IsAlive())
	{
		PresentDeath();
		NotifyStateChanged();
		OnDied.Broadcast();
		return;
	}
	// Protection starts once per accepted hit. Rejected hits above cannot extend
	// either this deadline or the shorter movement/input recovery.
	InvulnerableUntil = GetWorld()->GetTimeSeconds() + PlayerHitProtection;
	GetWorld()->GetTimerManager().SetTimer(HitProtectionTimer, this, &UPlayerCombatComponent::EndHitProtection, PlayerHitProtection, false);
	if (bHitReactionsEnabled) { StartHitReaction(Source); }
	NotifyStateChanged();
}

void UPlayerCombatComponent::PresentDamage(AActor* DamageSource)
{
	ATopDownCombatCharacter* Character = Cast<ATopDownCombatCharacter>(PlayerPawn.Get());
	if (!Character || !FleshHitEffect) { return; }
	FVector TowardSource = IsValid(DamageSource) ?
		(DamageSource->GetActorLocation() - Character->GetActorLocation()).GetSafeNormal2D() : FVector::ZeroVector;
	if (TowardSource.IsNearlyZero() || TowardSource.ContainsNaN()) { TowardSource = Character->GetActorForwardVector(); }
	// Generic damage has no weapon contact point. Use the current chest pose and
	// trace its physics surface, falling back to the source-facing torso surface.
	USkeletalMeshComponent* Mesh = Character->GetMesh();
	const FVector Torso = Mesh && Mesh->DoesSocketExist(TEXT("spine_03")) ?
		Mesh->GetSocketLocation(TEXT("spine_03")) : Character->GetActorLocation() + FVector(0, 0, 18.0f);
	FVector Location = Torso + TowardSource * 12.0f;
	FHitResult Contact;
	if (Mesh && Mesh->LineTraceComponent(Contact, Torso + TowardSource * 100.0f,
		Torso - TowardSource * 25.0f, FCollisionQueryParams(SCENE_QUERY_STAT(PlayerDamageContact), false)))
	{
		Location = Contact.ImpactPoint + Contact.ImpactNormal * 2.0f;
	}
	UParticleSystemComponent* Particle = UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), FleshHitEffect,
		Location, TowardSource.Rotation(), FVector(0.48f), true, EPSCPoolMethod::None, false);
	if (!Particle) { return; }
	Particle->ComponentTags.Add(TEXT("PlayerDamageFeedback"));
	Particle->bOverrideLODMethod = true;
	Particle->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
	Particle->SetLODLevel(0);
	Particle->ActivateSystem(true);
	Particle->SetLODLevel(0);
	// Keep the original burst, particle motion and fade; cap any looping tail.
	FTimerHandle Cleanup;
	GetWorld()->GetTimerManager().SetTimer(Cleanup, FTimerDelegate::CreateWeakLambda(Particle, [Particle]()
	{
		Particle->DestroyComponent();
	}), 1.2f, false);
}

void UPlayerCombatComponent::StartHitReaction(AActor* DamageSource)
{
	ATopDownCombatCharacter* Character = Cast<ATopDownCombatCharacter>(PlayerPawn.Get());
	// Countess ordinary damage never flushes held input, stops path following,
	// or starts the short control timer. Explicit stun/knockback still use it.
	if (UsesNonInterruptingDamageFeedback()) { return; }
	if (!Character || IsCrowdControlled() || GetWorld()->GetTimeSeconds() < HardControlProtectedUntil) { return; }
	// Existing casts, channels and evasive skills keep their animation and timers.
	// They still receive damage; only idle/moving/basic-attacking players flinch.
	const UCharacterSkillComponent* Skills = Character->GetSkills();
	if (Skills && Skills->IsCasting()) { return; }
	HitDirection = ResolveHitDirection(*Character, DamageSource);
	if (!BeginControl(EPlayerControlState::HitReaction, PlayerHitRecovery)) { return; }
	if (const FPlayerCombatAnimations* Animations = FindAnimations())
	{
		UAnimSequence* Animation = Animations->HitReaction;
		switch (HitDirection)
		{
		case EPlayerHitDirection::Back: Animation = Animations->HitBack; break;
		case EPlayerHitDirection::Left: Animation = Animations->HitLeft; break;
		case EPlayerHitDirection::Right: Animation = Animations->HitRight; break;
		default: break;
		}
		PlayReaction(Animation ? Animation : Animations->HitReaction.Get());
	}
}

const FPlayerCombatAnimations* UPlayerCombatComponent::FindAnimations() const
{
	const ATopDownCombatCharacter* Character = Cast<ATopDownCombatCharacter>(PlayerPawn.Get());
	const USkeletalMesh* Mesh = Character ? Character->GetMesh()->GetSkeletalMeshAsset() : nullptr;
	if (!Mesh) { return nullptr; }
	return CharacterAnimations.FindByPredicate([Mesh](const FPlayerCombatAnimations& Animations)
	{
		return Animations.HitReaction && !Animations.HitReactionSlot.IsNone() &&
			Animations.HitReaction->GetSkeleton() == Mesh->GetSkeleton();
	});
}

void UPlayerCombatComponent::PlayReaction(UAnimSequence* Animation, int32 LoopCount)
{
	const FPlayerCombatAnimations* Animations = FindAnimations();
	ATopDownCombatCharacter* Character = HitReactionCharacter.Get();
	UAnimInstance* Anim = Character ? Character->GetMesh()->GetAnimInstance() : nullptr;
	if (!Animations || !Animation || !Anim || Animation->GetSkeleton() != Animations->HitReaction->GetSkeleton()) { return; }
	HitReactionAnimInstance = Anim;
	// Tune the visible flinch independently of the short input lock.
	// Hard control retains the authored speed and its separate recovery.
	const bool bLightHit = IsHitReacting();
	HitReactionMontage = UAnimMontage::CreateSlotAnimationAsDynamicMontage(Animation, Animations->HitReactionSlot,
		bLightHit ? LightHitBlendIn : HitReactionBlendIn,
		bLightHit ? LightHitBlendOut : HitReactionBlendOut, 1.0f, LoopCount);
	if (HitReactionMontage)
	{
		if (bLightHit)
		{
			HitReactionMontage->BlendIn.SetBlendOption(EAlphaBlendOption::Cubic);
			HitReactionMontage->BlendOut.SetBlendOption(EAlphaBlendOption::Cubic);
		}
		const float PlayRate = bLightHit ? LightHitPlayRate : 1.0f;
		if (Anim->Montage_Play(HitReactionMontage, PlayRate) <= 0.0f) { HitReactionMontage = nullptr; }
		else if (bLightHit)
		{
			// These directional clips are additive: retain the current stance and
			// show the full ordinary impact without extending its input lock.
			if (FAnimMontageInstance* Instance = Anim->GetActiveInstanceForMontage(HitReactionMontage))
			{
				Instance->SetDesiredWeight(LightHitWeight);
			}
		}
	}
	ActiveReactionAnimation = HitReactionMontage ? Animation : nullptr;
}

bool UPlayerCombatComponent::CanApplyHardControl() const
{
	return !bShuttingDown && bHitReactionsEnabled && IsAlive() && PlayerPawn.IsValid() &&
		PlayerController.IsValid() && !IsStunned() && !IsKnockedBack() && GetWorld() &&
		GetWorld()->GetTimeSeconds() >= HardControlProtectedUntil;
}

bool UPlayerCombatComponent::ApplyStun(float Duration)
{
	if (!CanApplyHardControl() || !FMath::IsFinite(Duration) || Duration <= 0.0f) { return false; }
	Duration = FMath::Clamp(Duration, 0.05f, 10.0f);
	if (!BeginControl(EPlayerControlState::Stunned, Duration)) { return false; }
	if (const FPlayerCombatAnimations* Animations = FindAnimations())
	{
		if (Animations->StunStart)
		{
			PlayReaction(Animations->StunStart);
			const float LoopStart = FMath::Max(0.01f, Animations->StunStart->GetPlayLength() - HitReactionBlendOut);
			if (Animations->StunLoop && LoopStart < Duration)
			{
				GetWorld()->GetTimerManager().SetTimer(StunLoopTimer, this,
					&UPlayerCombatComponent::PlayStunLoop, LoopStart, false);
			}
		}
		else { PlayStunLoop(); }
	}
	NotifyStateChanged();
	return true;
}

void UPlayerCombatComponent::PlayStunLoop()
{
	if (!IsStunned()) { return; }
	if (const FPlayerCombatAnimations* Animations = FindAnimations()) { PlayReaction(Animations->StunLoop, 100); }
}

bool UPlayerCombatComponent::ApplyKnockback(FVector Direction, float Distance, float Duration)
{
	if (!CanApplyHardControl() || Direction.ContainsNaN() || !FMath::IsFinite(Distance) ||
		!FMath::IsFinite(Duration) || Distance <= 0.0f || Duration <= 0.0f) { return false; }
	Direction = Direction.GetSafeNormal2D();
	if (Direction.IsNearlyZero()) { return false; }
	Duration = FMath::Clamp(Duration, 0.05f, 2.0f);
	Distance = FMath::Min(Distance, 2000.0f);
	if (!BeginControl(EPlayerControlState::Knockback, Duration)) { return false; }
	UCharacterMovementComponent* Movement = HitReactionCharacter->GetCharacterMovement();
	// CharacterMovement integrates the push with normal floor/wall collision.
	// Only this source is removed on recovery; no teleport or collision bypass.
	TSharedPtr<FRootMotionSource_ConstantForce> Push = MakeShared<FRootMotionSource_ConstantForce>();
	Push->InstanceName = TEXT("PlayerCombatKnockback");
	Push->AccumulateMode = ERootMotionAccumulateMode::Override;
	Push->Priority = 1000;
	Push->Duration = Duration;
	Push->Force = Direction * (Distance / Duration);
	Push->FinishVelocityParams.Mode = ERootMotionFinishVelocityMode::SetVelocity;
	Push->FinishVelocityParams.SetVelocity = FVector::ZeroVector;
	KnockbackSourceID = Movement->ApplyRootMotionSource(Push);
	if (const FPlayerCombatAnimations* Animations = FindAnimations()) { PlayReaction(Animations->Knockback); }
	NotifyStateChanged();
	return true;
}

bool UPlayerCombatComponent::BeginControl(EPlayerControlState State, float Duration)
{
	ATopDownCombatCharacter* Character = Cast<ATopDownCombatCharacter>(PlayerPawn.Get());
	APlayerController* Player = PlayerController.Get();
	if (!Character || !Player) { return false; }
	EndHitReaction();
	if (State != EPlayerControlState::HitReaction)
	{
		if (UCharacterSkillComponent* Skills = Character->GetSkills()) { Skills->CancelSkill(); }
	}

	ControlState = State;
	HitReactionCharacter = Character;
	Player->FlushPressedKeys();
	Player->StopMovement();
	if (Player->InputEnabled())
	{
		bDisabledPlayerInput = true;
		Player->DisableInput(Player);
	}
	Character->InterruptIntroAnimation();
	Character->SetHeldBasicAttackInput(false);
	Character->CancelBasicAttackForSkill();
	UCharacterMovementComponent* Movement = Character->GetCharacterMovement();
	SavedHitMovementMode = Movement->MovementMode;
	SavedHitCustomMovementMode = Movement->CustomMovementMode;
	Movement->StopMovementImmediately();
	if (State == EPlayerControlState::Knockback)
	{
		bSavedOrientToMovement = Movement->bOrientRotationToMovement;
		bSavedControllerDesiredRotation = Movement->bUseControllerDesiredRotation;
		Movement->bOrientRotationToMovement = false;
		Movement->bUseControllerDesiredRotation = false;
	}
	else { Movement->DisableMovement(); }
	GetWorld()->GetTimerManager().SetTimer(HitReactionTimer, this, &UPlayerCombatComponent::EndHitReaction,
		Duration, false);
	UE_LOG(LogTemp, Display, TEXT("PlayerCombat control start state=%d duration=%.3f pawn=%s"),
		static_cast<int32>(State), Duration, *GetNameSafe(Character));
	return true;
}

void UPlayerCombatComponent::EndHitReaction()
{
	GetWorld()->GetTimerManager().ClearTimer(HitReactionTimer);
	GetWorld()->GetTimerManager().ClearTimer(StunLoopTimer);
	if (!IsCrowdControlled()) { return; }
	const EPlayerControlState PreviousState = ControlState;
	ControlState = EPlayerControlState::None;
	if (PreviousState != EPlayerControlState::HitReaction)
	{
		HardControlProtectedUntil = GetWorld()->GetTimeSeconds() + HardControlRecoveryProtection;
	}
	if (UAnimInstance* AnimInstance = HitReactionAnimInstance.Get())
	{
		// Stop only our reaction, never a subsequently started skill montage.
		// Input returns now; finish with this reaction's authored blend duration.
		if (HitReactionMontage)
		{
			AnimInstance->Montage_Stop(HitReactionMontage->BlendOut.GetBlendTime(), HitReactionMontage);
		}
	}
	if (ATopDownCombatCharacter* Character = HitReactionCharacter.Get())
	{
		UCharacterMovementComponent* Movement = Character->GetCharacterMovement();
		if (PreviousState == EPlayerControlState::Knockback)
		{
			Movement->RemoveRootMotionSourceByID(KnockbackSourceID);
			Movement->StopMovementImmediately();
			Movement->bOrientRotationToMovement = bSavedOrientToMovement;
			Movement->bUseControllerDesiredRotation = bSavedControllerDesiredRotation;
		}
		if (Movement->MovementMode == MOVE_None)
		{
			Movement->SetMovementMode(static_cast<EMovementMode>(SavedHitMovementMode), SavedHitCustomMovementMode);
		}
	}
	HitReactionMontage = nullptr;
	ActiveReactionAnimation = nullptr;
	KnockbackSourceID = 0;
	HitReactionAnimInstance.Reset();
	HitReactionCharacter.Reset();
	ReleasePlayerInput();
	NotifyStateChanged();
	UE_LOG(LogTemp, Display, TEXT("PlayerCombat stagger end t=%.3f"), GetWorld()->GetTimeSeconds());
}

void UPlayerCombatComponent::EndHitProtection()
{
	InvulnerableUntil = 0.0;
	NotifyStateChanged();
}

void UPlayerCombatComponent::PresentDeath()
{
	EndHitReaction();
	GetWorld()->GetTimerManager().ClearTimer(HitProtectionTimer);
	InvulnerableUntil = 0.0;
	if (APlayerController* Player = PlayerController.Get())
	{
		Player->FlushPressedKeys();
		Player->StopMovement();
		bDisabledPlayerInput |= Player->InputEnabled();
		Player->DisableInput(Player);
	}
	if (ATopDownCombatCharacter* Character = Cast<ATopDownCombatCharacter>(PlayerPawn.Get()))
	{
		Character->SetHeldBasicAttackInput(false);
		Character->CancelBasicAttackForSkill();
		if (UCharacterSkillComponent* Skills = Character->GetSkills()) { Skills->CancelSkill(); }
		Character->GetCharacterMovement()->StopMovementImmediately();
		Character->GetCharacterMovement()->DisableMovement();
		Character->StopAnimMontage();
		USkeletalMeshComponent* Mesh = Character->GetMesh();
		for (const FPlayerCombatAnimations& Animations : CharacterAnimations)
		{
			UAnimSequence* Animation = Animations.Death;
			if (Animation && Mesh->GetSkeletalMeshAsset() &&
				Animation->GetSkeleton() == Mesh->GetSkeletalMeshAsset()->GetSkeleton())
			{
				Mesh->PlayAnimation(Animation, false);
				Mesh->SetPlayRate(1.0f);
				break;
			}
		}
	}
	UE_LOG(LogTemp, Display, TEXT("PlayerCombat player defeated"));
}

bool UPlayerCombatComponent::RespawnPlayer()
{
	APlayerController* Player = PlayerController.Get();
	APawn* Previous = PlayerPawn.Get();
	if (bShuttingDown || !Player || !Previous || !bHasPlayerStart) { return false; }
	EndHitReaction();
	Player->FlushPressedKeys();
	Player->StopMovement();
	// Recreate the selected pawn so its original EndPlay clears every skill/FX
	// timer and its original defaults restore movement, animations and cooldowns.
	FActorSpawnParameters Parameters;
	Parameters.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	APawn* Next = GetWorld()->SpawnActor<APawn>(Previous->GetClass(),
		PlayerStartFeet + FVector(0, 0, Previous->GetSimpleCollisionHalfHeight()), PlayerStartRotation, Parameters);
	if (!Next) { return false; }
	const bool bPreviousCollision = Previous->GetActorEnableCollision();
	Previous->SetActorEnableCollision(false);
	TGuardValue<bool> RespawningGuard(bRespawning, true);
	Player->Possess(Next);
	if (Player->GetPawn() != Next)
	{
		Next->Destroy();
		Previous->SetActorEnableCollision(bPreviousCollision);
		Player->Possess(Previous);
		return false;
	}
	Previous->Destroy();
	Player->SetViewTarget(Next);
	if (ATopDownCombatCharacter* Character = Cast<ATopDownCombatCharacter>(Next))
	{
		Character->InterruptIntroAnimation();
	}
	GetWorld()->GetTimerManager().ClearTimer(HitProtectionTimer);
	InvulnerableUntil = 0.0;
	Health = GetMaxHealth();
	DamageTrailHealth = Health;
	LastDamageTime = -1000.0;
	HardControlProtectedUntil = 0.0;
	ReleasePlayerInput();
	NotifyStateChanged();
	return true;
}

void UPlayerCombatComponent::ReleasePlayerInput()
{
	if (bDisabledPlayerInput)
	{
		if (APlayerController* Player = PlayerController.Get())
		{
			Player->FlushPressedKeys();
			Player->EnableInput(Player);
		}
		bDisabledPlayerInput = false;
	}
}

