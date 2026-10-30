#include "CountessSkillComponent.h"
#include "CountessRebirthFX.h"

#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "CountessDemonForm.h"
#include "CountessInfernoVisual.h"
#include "CountessRuinVisual.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "GameFramework/Controller.h"
#include "Kismet/GameplayStatics.h"
#include "KwangTrainingDummy.h"
#include "NavigationSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "TimerManager.h"
#include "TopDownCombatCharacter.h"

namespace CountessReforge
{
	struct FDefinition
	{
		int32 Slot;
		const TCHAR* Animation;
		float Action;
		float Recovery;
		float Cooldown;
	};
	const FDefinition Definitions[] = {
		{1, TEXT("Ability_RMB"), .22f, .65f, 8.0f},
		{2, TEXT("Ability_E"), .32f, .80f, 8.0f},
		{3, TEXT("Ability_Ultimate"), .50f, 1.00f, 14.0f},
		{8, TEXT("Ability_RMB"), .22f, .75f, 9.0f},
		{9, TEXT("Cast"), .18f, .85f, 30.0f},
		{10, TEXT("Primary_Attack_B_Normal"), .18f, .62f, 7.0f},
		{16, TEXT("Cast"), .40f, 3.80f, 18.0f}
	};
	const FDefinition* Find(int32 Slot)
	{
		for (const FDefinition& Definition : Definitions)
		{
			if (Definition.Slot == Slot) { return &Definition; }
		}
		return nullptr;
	}
}

float UCountessSkillComponent::GetDemonFormRemaining() const
{
	return DemonForm.IsValid() ? DemonForm->GetFormRemaining() : 0.0f;
}

bool UCountessSkillComponent::IsReforgePathClear(const FVector& Start, const FVector& End) const
{
	if (!GetWorld() || !Character.IsValid()) { return false; }
	FCollisionQueryParams Query(SCENE_QUERY_STAT(CountessReforgeSight), false, Character.Get());
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_WorldStatic);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	TArray<FHitResult> Hits;
	GetWorld()->LineTraceMultiByObjectType(Hits, Start, End, Objects, Query);
	for (const FHitResult& Hit : Hits)
	{
		const AActor* Actor = Hit.GetActor();
		if (Actor && (Actor->IsA<APawn>() || Actor->IsA<AKwangTrainingDummy>())) { continue; }
		if (Hit.GetComponent() && Hit.GetComponent()->GetCollisionResponseToChannel(ECC_Visibility) == ECR_Block) { return false; }
	}
	return true;
}

bool UCountessSkillComponent::FindReforgeGround(const FVector& AimLocation, float Range, FVector& Ground) const
{
	if (!Character.IsValid() || !GetWorld() || AimLocation.ContainsNaN()) { return false; }
	const FVector Feet = GetFeetLocation();
	const FVector Delta = AimLocation - Feet;
	const FVector Requested = Feet + Delta.GetSafeNormal2D() * FMath::Min(static_cast<float>(Delta.Size2D()), Range);
	FCollisionQueryParams Query(SCENE_QUERY_STAT(CountessReforgeGround), false, Character.Get());
	FCollisionObjectQueryParams Objects(ECC_WorldStatic);
	FHitResult Hit;
	if (!GetWorld()->LineTraceSingleByObjectType(Hit, Requested + FVector(0, 0, 180),
		Requested - FVector(0, 0, 240), Objects, Query) || Hit.ImpactNormal.Z < .65f) { return false; }
	Ground = Hit.ImpactPoint + FVector(0, 0, 3);
	return IsReforgePathClear(Feet + FVector(0, 0, 80), Ground + FVector(0, 0, 80));
}

bool UCountessSkillComponent::TryUseReforgeSkill(int32 Slot, const FVector& AimLocation)
{
	const CountessReforge::FDefinition* Definition = CountessReforge::Find(Slot);
	if (!Definition || !bEnabled || !Character.IsValid() || !GetWorld() ||
		Character->GetCharacterMovement()->MovementMode != MOVE_Walking) { return RejectInput(TEXT("Unavailable")); }
	if (IsCasting()) { return RejectInput(TEXT("Casting")); }
	if (GetSlotCooldownRemaining(Slot) > 0.0f) { return RejectInput(TEXT("Cooldown")); }
	USkeletalMeshComponent* Mesh = Character->GetMesh();
	UAnimInstance* Anim = Mesh ? Mesh->GetAnimInstance() : nullptr;
	if (!Anim || !Mesh->GetSkeletalMeshAsset()) { return RejectInput(TEXT("Animation unavailable")); }
	FVector Ground = GetFeetLocation();
	if (Slot == 2 && !FindReforgeGround(AimLocation, 750.0f, Ground)) { return RejectInput(TEXT("No clear ground")); }
	ReforgeMontages.SetNum(18);
	if (!ReforgeMontages[Slot])
	{
		const FString Path = FString::Printf(TEXT("/Game/ParagonCountess/Characters/Heroes/Countess/Animations/%s.%s"),
			Definition->Animation, Definition->Animation);
		UAnimSequence* Sequence = LoadObject<UAnimSequence>(nullptr, *Path);
		if (!Sequence || Sequence->GetSkeleton() != Mesh->GetSkeletalMeshAsset()->GetSkeleton())
		{
			return RejectInput(TEXT("Animation unavailable"));
		}
		ReforgeMontages[Slot] = UAnimMontage::CreateSlotAnimationAsDynamicMontage(Sequence,
			TEXT("CountessFullBody"), .10f, .16f, 1.0f, 1);
	}
	if (!ReforgeMontages[Slot]) { return RejectInput(TEXT("Animation unavailable")); }
	Character->InterruptIntroAnimation();
	Character->CancelBasicAttackForSkill();
	if (Character->GetController()) { Character->GetController()->StopMovement(); }
	UCharacterMovementComponent* Movement = Character->GetCharacterMovement();
	Movement->StopMovementImmediately();
	ReforgeSavedRootMotion = Anim->RootMotionMode;
	bReforgeSavedOrient = Movement->bOrientRotationToMovement;
	ReforgeMeshLocation = Mesh->GetRelativeLocation();
	Anim->SetRootMotionMode(ERootMotionMode::IgnoreRootMotion);
	Movement->bOrientRotationToMovement = false;
	ReforgeDirection = (AimLocation - Character->GetActorLocation()).GetSafeNormal2D();
	if (ReforgeDirection.IsNearlyZero()) { ReforgeDirection = Character->GetActorForwardVector(); }
	if (Slot != 9 && Slot != 16) { Character->SetActorRotation(ReforgeDirection.Rotation()); }
	ReforgeOrigin = GetFeetLocation();
	ReforgeAim = Ground;
	ReforgeSlot = Slot;
	ReforgeMontage = ReforgeMontages[Slot];
	ReforgeAnim = Anim;
	ReforgeStartedAt = GetWorld()->GetTimeSeconds();
	ReforgeCommitTime = Definition->Action;
	ReforgeDuration = Definition->Recovery;
	bReforgeCasting = true;
	bReforgeCommitted = false;
	ReforgePlayRate = ReforgeMontage->GetPlayLength() / (Slot == 16 ? 1.15f : ReforgeDuration + .10f);
	if (Anim->Montage_Play(ReforgeMontage, ReforgePlayRate) <= 0.0f)
	{
		FinishReforgeCast();
		return RejectInput(TEXT("Animation unavailable"));
	}
	ReforgeCooldowns[Slot] = ReforgeStartedAt + Definition->Cooldown;
	SetComponentTickEnabled(true);
	Feedback.Reset();
	UE_LOG(LogTemp, Display, TEXT("COUNTESS_REFORGE begin slot=%d action=%.2f duration=%.2f"), Slot, ReforgeCommitTime, ReforgeDuration);
	return true;
}

void UCountessSkillComponent::CommitReforgeSkill()
{
	if (!bReforgeCasting || bReforgeCommitted || !Character.IsValid() || !GetWorld()) { return; }
	bReforgeCommitted = true;
	ReleaseReforgeSkill(ReforgeSlot, ReforgeOrigin, ReforgeAim, ReforgeDirection);
}

void UCountessSkillComponent::ReleaseReforgeSkill(int32 Slot, const FVector& ReleaseOrigin, const FVector& Aim, const FVector& Direction)
{
	if (!Character.IsValid() || !GetWorld()) { return; }
	FActorSpawnParameters Spawn;
	Spawn.Owner = Character.Get();
	Spawn.ObjectFlags |= RF_Transient;
	Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	const double Now = GetWorld()->GetTimeSeconds();
	auto Pulse = [this, Now, ReleaseOrigin, Direction](float Delay, const FVector& Center, float Radius, float Damage, float HalfWidth = 0.0f,
		AActor* Follow = nullptr, TSharedPtr<TSet<TWeakObjectPtr<AActor>>> SharedHits = nullptr)
	{
		FReforgePulse Item;
		Item.Due = Now + Delay;
		Item.Center = Center;
		Item.CastOrigin = ReleaseOrigin;
		Item.Direction = Direction;
		Item.Radius = Radius;
		Item.Damage = Damage;
		Item.HalfWidth = HalfWidth;
		Item.FollowField = Follow;
		Item.SharedHits = SharedHits;
		ReforgePulses.Add(MoveTemp(Item));
	};
	if (Slot == 1)
	{
		if (auto* Visual = ACountessRebirthFX::Create(Character.Get(), TEXT("W"), ReleaseOrigin, Direction)) { ReforgeVisuals.Add(Visual); }
		Pulse(.04f, ReleaseOrigin + Direction * 190.f, 220.f, 65.f, 160.f);
	}
	else if (Slot == 16 || Slot == 8)
	{
		ACountessInfernoVisual* Visual = GetWorld()->SpawnActor<ACountessInfernoVisual>(ReleaseOrigin, Direction.Rotation(), Spawn);
		if (Visual)
		{
			const bool bStorm = Slot == 16;
			Visual->Initialize(Character.Get(), bStorm, ReleaseOrigin, Direction, bStorm ? 3.6f : 2.3f);
			ReforgeVisuals.Add(Visual);
			const int32 Count = bStorm ? 12 : 6;
			for (int32 Index = 0; Index < Count; ++Index)
			{
				const float Age = bStorm ? .38f + Index * .23f : .18f + Index * .34f;
				const float Growth = FMath::SmoothStep(0.0f, 1.0f, FMath::Clamp((Age - .25f) / .65f, 0.0f, 1.0f));
				Pulse(Age, ReleaseOrigin, bStorm ? 100.0f + 330.0f * Growth : 165.0f, bStorm ? 7.0f : 10.0f, 0.0f, Visual);
			}
		}
	}
	else if (Slot == 9)
	{
		if (DemonForm.IsValid()) { DemonForm->StopForm(); }
		ACountessDemonForm* Form = GetWorld()->SpawnActor<ACountessDemonForm>(ReleaseOrigin, Character->GetActorRotation(), Spawn);
		if (Form && Form->Initialize(Character.Get(), 24.0f))
		{
			DemonForm = Form;
			Pulse(.12f, ReleaseOrigin, 230.0f, 20.0f);
		}
		else if (Form) { Form->Destroy(); }
	}
	else
	{
		const ECountessRuinKind Kind = Slot == 3 ? ECountessRuinKind::Spikes :
			(Slot == 10 ? ECountessRuinKind::Claws : ECountessRuinKind::Eruption);
		const FVector Origin = Slot == 2 ? Aim : ReleaseOrigin;
		AActor* Presentation = ACountessRebirthFX::Create(Character.Get(), Slot == 3 ? TEXT("R") : Slot == 10 ? TEXT("D") : TEXT("E"), Origin, Direction);
		if (!Presentation)
		{
			ACountessRuinVisual* Visual = GetWorld()->SpawnActor<ACountessRuinVisual>(Origin, Direction.Rotation(), Spawn);
			if (Visual) { Visual->Initialize(Character.Get(), Kind, Origin, Direction, Slot == 3 ? 1.35f : (Slot == 10 ? .85f : 1.2f)); }
			Presentation = Visual;
		}
		if (Presentation) { ReforgeVisuals.Add(Presentation); }
		if (Slot == 3)
		{
			const auto Shared = MakeShared<TSet<TWeakObjectPtr<AActor>>>();
			for (int32 Index = 0; Index < 3; ++Index)
			{
				Pulse(.08f + Index * .12f, Origin + Direction * (140.0f + Index * 220.0f), 185.0f, 90.0f, 0.0f, nullptr, Shared);
			}
		}
		else if (Slot == 10)
		{
			for (int32 Index = 0; Index < 3; ++Index)
			{
				Pulse(.21f + Index * .045f, Origin + Direction * 280.0f, 280.0f, 18.0f, 160.0f);
			}
		}
		else { Pulse(.12f, Origin, 240.0f, 55.0f); }
	}
	SetComponentTickEnabled(true);
	PlaySkillSound(Slot == 3 ? ESkillSound::FeastCharge : ESkillSound::Blade, ReleaseOrigin, .45f);
	UE_LOG(LogTemp, Display, TEXT("COUNTESS_REFORGE commit slot=%d pulses=%d"), Slot, ReforgePulses.Num());
}

void UCountessSkillComponent::ApplyReforgePulse(const FReforgePulse& Pulse)
{
	if (!Character.IsValid() || !GetWorld()) { return; }
	FVector Center = Pulse.Center;
	if (const ACountessInfernoVisual* Field = Cast<ACountessInfernoVisual>(Pulse.FollowField.Get())) { Center = Field->GetFieldCenter(); }
	else if (Pulse.FollowField.IsStale()) { return; }
	FCollisionQueryParams Query(SCENE_QUERY_STAT(CountessReforgeHit), false, Character.Get());
	// 이미 설치된 효과도 원래 시전점과 중심 사이의 벽을 넘어 피해를 전달하지 않는다.
	if (!IsReforgePathClear(Pulse.CastOrigin + FVector(0, 0, 90), Center + FVector(0, 0, 90))) { return; }
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_Pawn);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	TArray<FOverlapResult> Overlaps;
	GetWorld()->OverlapMultiByObjectType(Overlaps, Center + FVector(0, 0, 60), FQuat::Identity,
		Objects, FCollisionShape::MakeSphere(Pulse.Radius), Query);
	TSet<TWeakObjectPtr<AActor>> LocalHits;
	const FVector Side = FVector::CrossProduct(FVector::UpVector, Pulse.Direction);
	for (const FOverlapResult& Overlap : Overlaps)
	{
		AActor* Target = Overlap.GetActor();
		if (!IsValidSkillTarget(Target, Character.Get()) || LocalHits.Contains(Target) ||
			(Pulse.SharedHits && Pulse.SharedHits->Contains(Target))) { continue; }
		const FVector Offset = Target->GetActorLocation() - Center;
		if (FMath::Abs(Offset.Z) > 200.0f || Offset.SizeSquared2D() > FMath::Square(Pulse.Radius + Target->GetSimpleCollisionRadius())) { continue; }
		if (Pulse.HalfWidth > 0.0f && FMath::Abs(FVector::DotProduct(Offset, Side)) > Pulse.HalfWidth + Target->GetSimpleCollisionRadius()) { continue; }
		if (!IsReforgePathClear(Center + FVector(0, 0, 90), Target->GetActorLocation())) { continue; }
		LocalHits.Add(Target);
		if (Pulse.SharedHits) { Pulse.SharedHits->Add(Target); }
		const float Damage = Pulse.Damage * (GetDemonFormRemaining() > 0.0f ? 1.2f : 1.0f);
		const FVector Direction = Offset.GetSafeNormal();
		const FHitResult Hit(Target, nullptr, Target->GetActorLocation(), -Direction);
		UGameplayStatics::ApplyPointDamage(Target, Damage, Direction, Hit, Character->GetController(), Character.Get(), nullptr);
		if (UParticleSystemComponent* Impact = SpawnOwnedEffect(GetVisualEffect(EVisualEffect::FeastImpact),
			Target->GetActorLocation(), Direction.Rotation(), .23f, nullptr, .28f))
		{
			// 명중마다 겹치던 원본 궁극기의 검은 점/넓은 카드는 제외하고 국소 파열만 남긴다.
			for (const TCHAR* Emitter : {TEXT("DarkSpark"), TEXT("DarkSparkBack"), TEXT("DirectionalSparkBack"),
				TEXT("DarkeningElement"), TEXT("Refraction"), TEXT("Light"), TEXT("Flare"), TEXT("FlareBack")})
			{
				Impact->SetEmitterEnable(Emitter, false);
			}
		}
	}
}

void UCountessSkillComponent::TickReforgeSkills(float DeltaTime)
{
	if (!GetWorld()) { return; }
	const double Now = GetWorld()->GetTimeSeconds();
	if (bReforgeCasting)
	{
		if (!Character.IsValid() || !ReforgeAnim.IsValid() || Character->GetMesh()->GetAnimInstance() != ReforgeAnim.Get() ||
			Character->GetCharacterMovement()->MovementMode != MOVE_Walking || ReforgeAnim->Montage_GetIsStopped(ReforgeMontage))
		{
			FinishReforgeCast();
		}
		else
		{
			const float Age = static_cast<float>(Now - ReforgeStartedAt);
			if (ReforgeSlot == 16)
			{
				const float Lift = FMath::SmoothStep(0.0f, 1.0f, FMath::Clamp(Age / .65f, 0.0f, 1.0f)) *
					FMath::SmoothStep(0.0f, 1.0f, FMath::Clamp((ReforgeDuration - Age) / .45f, 0.0f, 1.0f));
				Character->GetMesh()->SetRelativeLocation(ReforgeMeshLocation + FVector(0, 0, Lift * (72.0f + 6.0f * FMath::Sin(Age * 4.5f))));
				// 시전 자세를 공중에서 유지하되 캡슐과 내비게이션 위치는 바꾸지 않는다.
				if (Age > .55f && Age < ReforgeDuration - .35f)
				{
					ReforgeAnim->Montage_SetPosition(ReforgeMontage, ReforgeMontage->GetPlayLength() * .48f);
					ReforgeAnim->Montage_SetPlayRate(ReforgeMontage, .025f);
				}
				else if (Age >= ReforgeDuration - .35f) { ReforgeAnim->Montage_SetPlayRate(ReforgeMontage, ReforgePlayRate); }
			}
			if (!bReforgeCommitted && Age >= ReforgeCommitTime) { CommitReforgeSkill(); }
			if (Age >= ReforgeDuration) { FinishReforgeCast(); }
		}
	}
	for (int32 Index = ReforgePulses.Num() - 1; Index >= 0; --Index)
	{
		if (ReforgePulses[Index].Due <= Now)
		{
			ApplyReforgePulse(ReforgePulses[Index]);
			ReforgePulses.RemoveAt(Index);
		}
	}
	ReforgeVisuals.RemoveAll([](const TWeakObjectPtr<AActor>& Item) { return !Item.IsValid(); });
	if (!bCasting && !bReforgeCasting && ReforgePulses.IsEmpty()) { SetComponentTickEnabled(false); }
}

void UCountessSkillComponent::FinishReforgeCast()
{
	if (!bReforgeCasting) { return; }
	const int32 FinishedSlot = ReforgeSlot;
	bReforgeCasting = false;
	if (ReforgeAnim.IsValid())
	{
		ReforgeAnim->Montage_Stop(.12f, ReforgeMontage);
		ReforgeAnim->SetRootMotionMode(ReforgeSavedRootMotion);
	}
	if (Character.IsValid())
	{
		Character->GetCharacterMovement()->bOrientRotationToMovement = bReforgeSavedOrient;
		if (FinishedSlot == 16) { Character->GetMesh()->SetRelativeLocation(ReforgeMeshLocation); }
	}
	ReforgeMontage = nullptr;
	ReforgeAnim.Reset();
	ReforgeSlot = INDEX_NONE;
	SetComponentTickEnabled(bCasting || !ReforgePulses.IsEmpty());
	UE_LOG(LogTemp, Display, TEXT("COUNTESS_REFORGE recovered slot=%d"), FinishedSlot);
}

void UCountessSkillComponent::CleanupReforgeSkills()
{
	FinishReforgeCast();
	ReforgePulses.Reset();
	if (GetWorld())
	{
		for (FTimerHandle& Timer : ReforgeHandoffTimers) { GetWorld()->GetTimerManager().ClearTimer(Timer); }
	}
	ReforgeHandoffTimers.Reset();
	for (const TWeakObjectPtr<AActor>& Actor : ReforgeVisuals) { if (Actor.IsValid()) { Actor->Destroy(); } }
	ReforgeVisuals.Reset();
	if (DemonForm.IsValid()) { DemonForm->StopForm(); }
	DemonForm.Reset();
}

bool UCountessSkillComponent::TryUseCursorBlink(const FVector& AimLocation)
{
	if (!bEnabled || !Character.IsValid() || !GetWorld() || IsBackstepping() ||
		Character->GetCharacterMovement()->MovementMode != MOVE_Walking) { return RejectInput(TEXT("Blink unavailable")); }
	if (GetSlotCooldownRemaining(11) > 0.0f) { return RejectInput(TEXT("Cooldown")); }
	FVector Landing;
	if (!FindCursorBlinkLanding(AimLocation, Landing)) { return RejectInput(TEXT("No clear landing")); }
	const FVector Origin = Character->GetActorLocation();
	FinishReforgeCast();
	FinishSkill();
	Character->InterruptIntroAnimation();
	Character->CancelBasicAttackForSkill();
	if (Character->GetController()) { Character->GetController()->StopMovement(); }
	Character->GetCharacterMovement()->StopMovementImmediately();
	const FTransform SourceTransform = Character->GetMesh()->GetComponentTransform();
	if (!Character->TeleportTo(Landing, Character->GetActorRotation(), false, false)) { return RejectInput(TEXT("Landing blocked")); }
	SpawnCursorBlinkEchoes(Origin, Landing, SourceTransform);
	if (!ACountessRebirthFX::Enabled())
	{
	SpawnOwnedEffect(GetVisualEffect(EVisualEffect::BlinkFlash), Origin, Character->GetActorRotation(), .40f, nullptr, .30f);
	SpawnOwnedEffect(TeleportArrivalEffect, GetFeetLocation(), Character->GetActorRotation(), .45f, nullptr, .35f);
	}
	NextCursorBlinkTime = GetWorld()->GetTimeSeconds() + 6.0;
	Feedback.Reset();
	UE_LOG(LogTemp, Display, TEXT("COUNTESS_REFORGE blink_f distance=%.2f"), FVector::Dist2D(Origin, Landing));
	return true;
}
