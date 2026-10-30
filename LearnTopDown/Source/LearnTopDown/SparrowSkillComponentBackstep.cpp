#include "SparrowSkillComponent.h"
#include "SparrowAscendedShotFX.h"

#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "NavigationSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "SparrowBackstepEcho.h"
#include "SparrowGoldRoll.h"
#include "SparrowArrow.h"
#include "SparrowShotWave.h"
#include "TopDownCombatCharacter.h"
#include "TimerManager.h"

bool USparrowSkillComponent::IsBackstepping() const
{
	return BackstepEcho.IsValid() && BackstepEcho->IsMoving();
}

bool USparrowSkillComponent::IsRolling() const
{
	return GoldRoll.IsValid() && GoldRoll->IsMoving();
}

bool USparrowSkillComponent::TryRoll(const FVector& AimLocation)
{
	if (!bEnabled || !Character.IsValid() || !GetWorld() || IsCasting() || AimLocation.ContainsNaN() ||
		!Character->GetCharacterMovement() || Character->GetCharacterMovement()->MovementMode != MOVE_Walking)
	{
		return RejectInput(TEXT("Roll unavailable"));
	}
	if (GetSlotCooldownRemaining(17) > 0.0f) { return RejectInput(TEXT("Cooldown")); }
	UNavigationSystemV1* Navigation = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
	UCapsuleComponent* Capsule = Character->GetCapsuleComponent();
	if (!Navigation || !Capsule) { return RejectInput(TEXT("Roll unavailable")); }
	const FVector Start = Character->GetActorLocation();
	const FVector Direction = (AimLocation - Start).GetSafeNormal2D();
	if (Direction.IsNearlyZero()) { return RejectInput(TEXT("Choose a direction")); }
	FVector Destination = Start + Direction * 480.0f;
	FCollisionQueryParams Query(SCENE_QUERY_STAT(SparrowGoldRoll), false, Character.Get());
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_WorldStatic);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	FHitResult Hit;
	if (GetWorld()->SweepSingleByObjectType(Hit, Start, Destination, FQuat::Identity, Objects,
		FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(), Capsule->GetScaledCapsuleHalfHeight() - 2.0f), Query))
	{
		Destination = Hit.Location + Hit.ImpactNormal * 3.0f;
	}
	FHitResult Floor;
	if (!GetWorld()->LineTraceSingleByObjectType(Floor, Destination + FVector(0, 0, 80),
		Destination - FVector(0, 0, 180), Objects, Query) || Floor.ImpactNormal.Z < 0.65f)
	{
		return RejectInput(TEXT("No safe ground ahead"));
	}
	Destination.Z = Floor.ImpactPoint.Z + Capsule->GetScaledCapsuleHalfHeight() + 0.15f;
	FNavLocation Projected;
	if (!Navigation->ProjectPointToNavigation(Floor.ImpactPoint, Projected, FVector(35, 35, 100),
		&Character->GetNavAgentPropertiesRef()) ||
		FVector::DistSquared2D(Projected.Location, Destination) > FMath::Square(35.0f) ||
		FVector::DistSquared2D(Start, Destination) < FMath::Square(15.0f))
	{
		return RejectInput(TEXT("No safe space ahead"));
	}
	FActorSpawnParameters Spawn;
	Spawn.Owner = Character.Get();
	Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	ASparrowGoldRoll* Roll = GetWorld()->SpawnActor<ASparrowGoldRoll>(Start, Direction.Rotation(), Spawn);
	if (!Roll) { return RejectInput(TEXT("Roll unavailable")); }
	Character->InterruptIntroAnimation();
	Character->CancelBasicAttackForSkill();
	if (!Roll->Initialize(Character.Get(), Destination, Direction, GetAscensionRemaining() > 0.0f))
	{
		Roll->Destroy();
		return RejectInput(TEXT("Roll animation unavailable"));
	}
	GoldRoll = Roll;
	NextRollTime = GetWorld()->GetTimeSeconds() + 6.0;
	Feedback.Reset();
	return true;
}

bool USparrowSkillComponent::TryBackstep()
{
	if (!bEnabled || !Character.IsValid() || !GetWorld() || IsBackstepping() || IsRolling() ||
		!Character->GetCharacterMovement() || Character->GetCharacterMovement()->MovementMode != MOVE_Walking)
	{
		return RejectInput(TEXT("Backstep unavailable"));
	}
	if (!IgnoresCooldowns() && GetWorld()->GetTimeSeconds() < NextBackstepTime) { return RejectInput(TEXT("Cooldown")); }
	UNavigationSystemV1* Navigation = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
	UCapsuleComponent* Capsule = Character->GetCapsuleComponent();
	USkeletalMeshComponent* Mesh = Character->GetMesh();
	UAnimInstance* Anim = Mesh ? Mesh->GetAnimInstance() : nullptr;
	if (!Navigation || !Capsule || !Anim || !Mesh->GetSkeletalMeshAsset()) { return RejectInput(TEXT("Backstep unavailable")); }
	const FVector Start = Character->GetActorLocation();
	FVector Destination = Start - Character->GetActorForwardVector() * 220.0f;
	FCollisionQueryParams Query(SCENE_QUERY_STAT(SparrowBackstep), false, Character.Get());
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_WorldStatic);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	FHitResult Hit;
	if (GetWorld()->SweepSingleByObjectType(Hit, Start, Destination, FQuat::Identity, Objects,
		FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(), Capsule->GetScaledCapsuleHalfHeight() - 2.0f), Query))
	{
		Destination = Hit.Location + Hit.ImpactNormal * 3.0f;
	}
	FHitResult Floor;
	if (!GetWorld()->LineTraceSingleByObjectType(Floor, Destination + FVector(0, 0, 80),
		Destination - FVector(0, 0, 180), Objects, Query) || Floor.ImpactNormal.Z < 0.65f)
	{
		return RejectInput(TEXT("No safe ground behind"));
	}
	Destination.Z = Floor.ImpactPoint.Z + Capsule->GetScaledCapsuleHalfHeight() + 0.15f;
	FNavLocation Projected;
	const bool bProjected = Navigation->ProjectPointToNavigation(Floor.ImpactPoint, Projected, FVector(35, 35, 100),
		&Character->GetNavAgentPropertiesRef());
	if (!bProjected || FVector::DistSquared2D(Projected.Location, Destination) > FMath::Square(35.0f) ||
		FVector::DistSquared2D(Start, Destination) < FMath::Square(15.0f))
	{
		UE_LOG(LogTemp, Display, TEXT("SPARROW_BACKSTEP unsafe projected=%d start=%s destination=%s floor=%s nav=%s"),
			bProjected, *Start.ToCompactString(), *Destination.ToCompactString(), *Floor.ImpactPoint.ToCompactString(),
			*Projected.Location.ToCompactString());
		return RejectInput(TEXT("No safe space behind"));
	}
	if (!BackstepMontage)
	{
		UAnimSequence* Sequence = LoadObject<UAnimSequence>(nullptr,
			TEXT("/Game/TopDown/Characters/Sparrow/Previews/Fresh20261022/AS_Sparrow_M9_MobilityStudy.AS_Sparrow_M9_MobilityStudy"));
		if (!Sequence || Sequence->GetSkeleton() != Mesh->GetSkeletalMeshAsset()->GetSkeleton())
		{
			return RejectInput(TEXT("Backstep animation unavailable"));
		}
		BackstepMontage = UAnimMontage::CreateSlotAnimationAsDynamicMontage(Sequence, FullBodySlot, 0.012f, 0.025f, 1.0f, 1);
	}
	if (!BackstepMontage) { return RejectInput(TEXT("Backstep animation unavailable")); }
	const bool bWasPiercing = bCasting && ActiveSkillIndex == 1;
	const bool bTransferShot = bWasPiercing && !bActionExecuted;
	UAnimMontage* Captured = bWasPiercing ? ActiveMontage.Get() : nullptr;
	const float Position = Captured ? Anim->Montage_GetPosition(Captured) : 0.0f;
	const float ReleaseDelay = bTransferShot ? GetWorld()->GetTimerManager().GetTimerRemaining(ActionTimer) : 0.0f;
	const FVector Aim = bWasPiercing ? CastAim : Start + Character->GetActorForwardVector() * 1500.0f;
	if (BackstepEcho.IsValid()) { BackstepEcho->Destroy(); BackstepEcho.Reset(); }
	FActorSpawnParameters Spawn;
	Spawn.Owner = Character.Get();
	Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	ASparrowBackstepEcho* Echo = GetWorld()->SpawnActor<ASparrowBackstepEcho>(Start, Character->GetActorRotation(), Spawn);
	if (!Echo) { return RejectInput(TEXT("Backstep unavailable")); }
	FinishSkill();
	Character->InterruptIntroAnimation();
	Character->CancelBasicAttackForSkill();
	if (!Echo->Initialize(Character.Get(), this, BackstepMontage, Captured, Position, ReleaseDelay,
		bTransferShot, Aim, Destination))
	{
		Echo->Destroy();
		return RejectInput(TEXT("Backstep animation unavailable"));
	}
	BackstepEcho = Echo;
	// 출발점에서만 짧게 터지는 금빛 파편이 고정 분신과 본체의 급후퇴를 구분한다.
	SpawnEffect(SparrowPresentation::GetReleaseShards(), Start + FVector(0, 0, 20),
		Character->GetActorRotation(), 0.14f, false, 0.60f);
	if (bTransferShot)
	{
		Echo->TrackEffect(SpawnEffect(Skills[1].CastEffect, Echo->GetArrowOrigin(), Character->GetActorRotation(),
			FMath::Max(0.03f, ReleaseDelay + 0.05f), false, 0.75f));
		Echo->TrackEffect(SpawnEffect(RuntimeRapidBowEffect, Echo->GetArrowOrigin(), Character->GetActorRotation(),
			FMath::Max(0.03f, ReleaseDelay + 0.05f), false, 0.45f));
	}
	NextBackstepTime = GetWorld()->GetTimeSeconds() + 6.0;
	Feedback.Reset();
	UE_LOG(LogTemp, Display, TEXT("SPARROW_BACKSTEP distance=%.2f transfer_w=%d delay=%.3f"),
		FVector::Dist2D(Start, Destination), bTransferShot, ReleaseDelay);
	return true;
}

void USparrowSkillComponent::ReleaseAnchoredPiercingShot(ASparrowBackstepEcho* Echo)
{
	if (Echo && BackstepEcho.Get() == Echo && Character.IsValid())
	{
		ReleasePiercingShot(Echo->GetArrowOrigin(), Echo->GetCapturedAim());
	}
}

void USparrowSkillComponent::ReleasePiercingShot(const FVector& Origin, const FVector& Aim, float DamageScale, bool bFinisher)
{
	const FVector Direction = (Aim - Origin).GetSafeNormal();
	if (Direction.IsNearlyZero() || !Character.IsValid() || !GetWorld()) { return; }
	TGuardValue<TOptional<FVector>> AimGuard(MirrorAimLocation, TOptional<FVector>(Aim));
	if (ASparrowArrow* Arrow = SpawnArrow(Direction, Skills[1].Damage * DamageScale, FMath::Min(Skills[1].Range, 2500.0f), 4000.0f,
		true, true, false, false, &Origin))
	{
		if (bFinisher)
		{
			Arrow->Tags.Add(TEXT("SparrowWFinalImpact"));
			Arrow->ConfigureImpactPresentation(nullptr, .30f, .35f);
		}
		if (AscendedBowFX.IsValid()) { AscendedBowFX->Pulse(Origin, Direction); }
		FActorSpawnParameters Spawn;
		Spawn.Owner = Character.Get();
		Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		// 파동은 캐릭터의 수평 전방으로 펼친다. 화살의 높이 조준은 위 Direction으로 별도 유지한다.
		if (ASparrowShotWave* Wave = GetWorld()->SpawnActor<ASparrowShotWave>(Origin, FRotator(0, Direction.Rotation().Yaw, 0), Spawn))
		{
			VisualProxies.RemoveAll([](const TWeakObjectPtr<AActor>& Proxy) { return !Proxy.IsValid(); });
			VisualProxies.Add(Wave);
		}
	}
	SpawnEffect(SparrowPresentation::GetPiercingMuzzle(), Origin, Direction.Rotation(), 0.14f, false, 0.85f);
	for (const float Side : {-1.0f, 1.0f})
	{
		const FVector Opening = Direction.RotateAngleAxis(Side * 17.0f, FVector::UpVector);
		if (UParticleSystemComponent* Feather = SpawnEffect(SparrowPresentation::GetReleaseShards(), Origin,
			Opening.Rotation(), 0.19f, false, 0.65f))
		{
			Feather->SetWorldScale3D(FVector(1.05f, 0.50f, 0.50f));
			Feather->ComponentTags.Add(TEXT("SparrowPiercingReleaseFeathers"));
		}
	}
}
