#include "CountessSkillComponent.h"

#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "CountessExtraTide.h"
#include "CountessExtraVisual.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "GameFramework/Controller.h"
#include "GameFramework/Pawn.h"
#include "KwangTrainingDummy.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "NavigationSystem.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "TimerManager.h"
#include "TopDownCombatCharacter.h"
#include "UObject/ConstructorHelpers.h"

namespace CountessExtras
{
	constexpr float SealBurstTime = 0.75f;
	constexpr float RushSeconds = 0.20f;
	constexpr float RushRadius = 110.0f;
	constexpr float AmbushBurstTime = 0.80f;
	constexpr float AmbushRadius = 240.0f;
	constexpr float AmbushAttackBegin = 0.60f;
	constexpr float AmbushClipHitTime = 0.20f;
}

void UCountessSkillComponent::InitializeExtraDefinitions()
{
	const TCHAR* Names[] = {TEXT("BloodSeal"), TEXT("VeilRush"), TEXT("NightTide"), TEXT("ShadowAmbush")};
	const TCHAR* Animations[] = {TEXT("Cast"), TEXT("Ability_Q_Jog_Fwd"), TEXT("Ability_E"), TEXT("Cast")};
	const float Damage[] = {30.0f, 30.0f, 40.0f, 40.0f};
	const float Cooldowns[] = {9.0f, 7.0f, 8.0f, 12.0f};
	const float Ranges[] = {700.0f, 450.0f, 900.0f, 600.0f};
	const float Actions[] = {0.22f, 0.12f, 0.36f, 0.18f};
	const float Recoveries[] = {0.95f, 0.65f, 0.85f, 1.10f};
	ExtraSkills.SetNum(4);
	for (int32 Index = 0; Index < 4; ++Index)
	{
		FCountessSkillDefinition& Skill = ExtraSkills[Index];
		Skill.Name = Names[Index];
		const FString Path = FString::Printf(TEXT("/Game/ParagonCountess/Characters/Heroes/Countess/Animations/%s.%s"),
			Animations[Index], Animations[Index]);
		ConstructorHelpers::FObjectFinder<UAnimSequence> Animation(*Path);
		Skill.Animation = Animation.Object;
		Skill.Damage = Damage[Index];
		Skill.Cooldown = Cooldowns[Index];
		Skill.Range = Ranges[Index];
		Skill.ActionTime = Actions[Index];
		Skill.RecoveryTime = Recoveries[Index];
	}
	ConstructorHelpers::FObjectFinder<UParticleSystem> SealBurst(
		TEXT("/Game/ParagonCountess/FX/Particles/Abilities/BladeSiphon/FX/P_Countess_SiphonOneShot.P_Countess_SiphonOneShot"));
	ExtraSealBurst = SealBurst.Object;
	ConstructorHelpers::FObjectFinder<UAnimSequence> AmbushAttack(
		TEXT("/Game/ParagonCountess/Characters/Heroes/Countess/Animations/Primary_Attack_B_Normal.Primary_Attack_B_Normal"));
	ExtraAmbushAttackAnimation = AmbushAttack.Object;
	ExtraSkills[0].CastEffect = FeastApplicationEffect;
	ExtraSkills[0].ImpactEffect = Skills[0].ImpactEffect;
	ExtraSkills[1].CastEffect = Skills[0].CastEffect;
	ExtraSkills[1].ImpactEffect = Skills[0].ImpactEffect;
	ExtraSkills[2].CastEffect = Skills[2].CastEffect;
	ExtraSkills[2].ImpactEffect = Skills[2].ImpactEffect;
	ExtraSkills[3].CastEffect = GetVisualEffect(EVisualEffect::CloneBurst);
	ExtraSkills[3].ImpactEffect = Skills[1].ImpactEffect;
}

void UCountessSkillComponent::CreateExtraMontages()
{
	bExtrasReady = false;
	ExtraMontages.Reset();
	// 기존 BP에 저장된 QWER 배열은 보존하고 신규 네 정의만 C++ 기본값으로 설치한다.
	ExtraSkills = GetDefault<UCountessSkillComponent>()->ExtraSkills;
	const USkeletalMesh* Mesh = Character.IsValid() ? Character->GetMesh()->GetSkeletalMeshAsset() : nullptr;
	if (!Mesh || ExtraSkills.Num() != 4) { return; }
	for (const FCountessSkillDefinition& Skill : ExtraSkills)
	{
		if (!Skill.Animation || Skill.Animation->GetSkeleton() != Mesh->GetSkeleton()) { ExtraMontages.Reset(); return; }
		UAnimMontage* Montage = UAnimMontage::CreateSlotAnimationAsDynamicMontage(
			Skill.Animation, TEXT("CountessFullBody"), 0.07f, 0.12f, 1.0f, 1);
		if (!Montage) { ExtraMontages.Reset(); return; }
		ExtraMontages.Add(Montage);
	}
	bExtrasReady = true;
}

bool UCountessSkillComponent::FindExtraRushLanding(const FVector& AimLocation, FVector& Result) const
{
	if (!Character.IsValid() || !GetWorld()) { return false; }
	const FVector Origin = Character->GetActorLocation();
	const FVector Direction = (AimLocation - Origin).GetSafeNormal2D();
	if (Direction.IsNearlyZero()) { return false; }
	float Distance = FMath::Min(450.0f, FVector::Dist2D(Origin, AimLocation));
	const UCapsuleComponent* Capsule = Character->GetCapsuleComponent();
	FCollisionQueryParams Query(SCENE_QUERY_STAT(CountessExtraRushLanding), false, Character.Get());
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_WorldStatic);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	TArray<FHitResult> Hits;
	GetWorld()->SweepMultiByObjectType(Hits, Origin, Origin + Direction * Distance, FQuat::Identity,
		Objects, FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(),
			Capsule->GetScaledCapsuleHalfHeight() - 2.0f), Query);
	for (const FHitResult& Hit : Hits)
	{
		if (Hit.bBlockingHit && Hit.GetActor() && !IsValidSkillTarget(Hit.GetActor(), Character.Get()))
		{
			Distance = FMath::Max(0.0f, FVector::Dist2D(Origin, Hit.Location) - 8.0f);
			break;
		}
	}
	const float HalfHeight = Capsule->GetScaledCapsuleHalfHeight();
	for (; Distance >= 80.0f; Distance -= 35.0f)
	{
		const FVector Feet = Origin + Direction * Distance - FVector(0, 0, HalfHeight);
		if (FindLandingPoint(Feet, Result) && FVector::DistSquared2D(Feet, Result) < FMath::Square(35.0f)) { return true; }
	}
	return false;
}

bool UCountessSkillComponent::FindExtraAmbushLanding(const FVector& AimLocation, AActor* Target, FVector& Result) const
{
	if (!Character.IsValid() || !GetWorld()) { return false; }
	const FVector Origin = Character->GetActorLocation();
	FVector Direction = (AimLocation - Origin).GetSafeNormal2D();
	if (Direction.IsNearlyZero()) { Direction = Character->GetActorForwardVector(); }
	FVector Feet = Origin + Direction * FMath::Min(600.0f, FVector::Dist2D(Origin, AimLocation));
	Feet.Z = GetFeetLocation().Z;
	UNavigationSystemV1* Navigation = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
	FNavLocation NavPoint;
	if (!Navigation || !Navigation->ProjectPointToNavigation(Feet, NavPoint, FVector(140, 140, 180),
		&Character->GetNavAgentPropertiesRef()) || FVector::DistSquared2D(Feet, NavPoint.Location) > FMath::Square(145.0f)) { return false; }
	Result = NavPoint.Location + FVector(0, 0, Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() + 2.0f);
	if (FVector::DistSquared2D(Origin, Result) > FMath::Square(600.0f)) { return false; }
	FCollisionQueryParams Query(SCENE_QUERY_STAT(CountessExtraAmbushSight), false, Character.Get());
	if (IsValid(Target)) { Query.AddIgnoredActor(Target); }
	FHitResult Hit;
	return !GetWorld()->LineTraceSingleByChannel(Hit, Origin, Result, ECC_Visibility, Query);
}

bool UCountessSkillComponent::TryUseExtraSkill(int32 ExtraIndex, const FVector& AimLocation, AActor* Target)
{
	if (!bEnabled || !bExtrasReady || !Character.IsValid() || !ExtraSkills.IsValidIndex(ExtraIndex) ||
		!ExtraMontages.IsValidIndex(ExtraIndex) || !GetWorld() ||
		Character->GetCharacterMovement()->MovementMode != MOVE_Walking) { return RejectInput(TEXT("Unavailable")); }
	if (bCasting) { return RejectInput(TEXT("Casting")); }
	if (GetSlotCooldownRemaining(ExtraIndex + 8) > 0.0f) { return RejectInput(TEXT("Cooldown")); }
	const FCountessSkillDefinition& Skill = ExtraSkills[ExtraIndex];
	if (ExtraIndex == 0)
	{
		if (!IsValidSkillTarget(Target, Character.Get())) { return RejectInput(TEXT("Aim at an enemy")); }
		const FVector Delta = Target->GetActorLocation() - Character->GetActorLocation();
		if (Delta.SizeSquared2D() > FMath::Square(Skill.Range) || FMath::Abs(Delta.Z) > 180.0f) { return RejectInput(TEXT("Out of range")); }
		if (!HasLineOfSight(Target)) { return RejectInput(TEXT("Blocked")); }
	}
	FVector Landing = Character->GetActorLocation();
	if (ExtraIndex == 1 && !FindExtraRushLanding(AimLocation, Landing)) { return RejectInput(TEXT("No room to rush")); }
	if (ExtraIndex == 3 && (!FlurryShadowDissolveMaterial.LoadSynchronous() ||
		!FindExtraAmbushLanding(AimLocation, Target, Landing))) { return RejectInput(TEXT("Blocked")); }
	UAnimInstance* AnimInstance = Character->GetMesh()->GetAnimInstance();
	if (!AnimInstance) { return RejectInput(TEXT("Unavailable")); }
	Character->InterruptIntroAnimation();
	Character->CancelBasicAttackForSkill();
	CastAnimInstance = AnimInstance;
	SavedRootMotionMode = AnimInstance->RootMotionMode;
	bSavedOrientRotation = Character->GetCharacterMovement()->bOrientRotationToMovement;
	AnimInstance->SetRootMotionMode(ERootMotionMode::IgnoreRootMotion);
	Character->GetCharacterMovement()->bOrientRotationToMovement = false;
	if (Character->GetController()) { Character->GetController()->StopMovement(); }
	Character->GetCharacterMovement()->StopMovementImmediately();
	const FVector Direction = (AimLocation - Character->GetActorLocation()).GetSafeNormal2D();
	if (!Direction.IsNearlyZero()) { Character->SetActorRotation(Direction.Rotation()); }
	bCasting = true;
	bReturning = false;
	bDetailedCast = UsesDetailedPresentation();
	bWShadowPreview = false;
	bActionExecuted = false;
	bExtraFollowupExecuted = false;
	bExtraRushActive = false;
	ExtraRushEchoes = 0;
	ExtraImpactVisuals = 0;
	bExtraAmbushStrikeStarted = false;
	ExtraCastStartedAt = GetWorld()->GetTimeSeconds();
	ActiveSkillIndex = ExtraIndex + 8;
	CastOrigin = Character->GetActorLocation();
	CastAim = AimLocation;
	CastTarget = Target;
	ExtraLanding = Landing;
	ActiveMontage = ExtraMontages[ExtraIndex];
	// 짧은 원본 클립도 지연 타격이 끝날 때까지 재생되게 하며 판정 시각은 별도 초 단위를 쓴다.
	ActivePlayRate = FMath::Min(1.0f, ActiveMontage->GetPlayLength() / (Skill.RecoveryTime + 0.12f));
	ActiveStartTime = 0.0f;
	++CastGeneration;
	if (ActivePlayRate <= 0.0f || AnimInstance->Montage_Play(ActiveMontage, ActivePlayRate) <= 0.0f)
	{
		FinishSkill();
		return RejectInput(TEXT("Unavailable"));
	}
	FOnMontageEnded EndDelegate;
	EndDelegate.BindUObject(this, &UCountessSkillComponent::OnMontageEnded, CastGeneration);
	AnimInstance->Montage_SetEndDelegate(EndDelegate, ActiveMontage);
	FOnMontageBlendingOutStarted BlendDelegate;
	BlendDelegate.BindUObject(this, &UCountessSkillComponent::OnMontageBlendingOut, CastGeneration);
	AnimInstance->Montage_SetBlendingOutDelegate(BlendDelegate, ActiveMontage);
	NextExtraSkillTimes[ExtraIndex] = GetWorld()->GetTimeSeconds() + Skill.Cooldown;
	GetWorld()->GetTimerManager().SetTimer(ActionTimer, this, &UCountessSkillComponent::ExecuteExtraAction, Skill.ActionTime, false);
	GetWorld()->GetTimerManager().SetTimer(RecoveryTimer, this, &UCountessSkillComponent::FinishSkill, Skill.RecoveryTime, false);
	ExtraRushHits.Reset();
	Feedback.Reset();
	SetComponentTickEnabled(true);
	if (ExtraIndex == 0 || ExtraIndex == 3)
	{
		for (const TCHAR* Side : {TEXT("L"), TEXT("R")})
		{
			const FName Socket(*FString::Printf(TEXT("FX_WeaponBase_%s"), Side));
			USkeletalMeshComponent* Mesh = Character->GetMesh();
			if (Mesh->DoesSocketExist(Socket))
			{
				if (UParticleSystemComponent* Ink = SpawnExtraEffect(GetVisualEffect(EVisualEffect::SmokeyBlade),
					Mesh->GetSocketLocation(Socket), Mesh->GetSocketRotation(Socket), .6f, Character.Get(), .45f))
				{
					Ink->AttachToComponent(Mesh, FAttachmentTransformRules::SnapToTargetNotIncludingScale, Socket);
				}
			}
		}
	}
	else if (ExtraIndex == 2)
	{
		SpawnExtraEffect(GetVisualEffect(EVisualEffect::TideGround), GetFeetLocation(),
			Character->GetActorRotation(), .65f, Character.Get(), .5f);
	}
	UE_LOG(LogTemp, Display, TEXT("COUNTESS_EXTRA start slot=%d name=%s"), ActiveSkillIndex, *Skill.Name.ToString());
	return true;
}

UParticleSystemComponent* UCountessSkillComponent::SpawnExtraEffect(UParticleSystem* Effect,
	const FVector& Location, const FRotator& Rotation, float Scale, AActor* SourceActor,
	float Lifetime, bool bAttachToSource)
{
	ExtraOwnedEffects.RemoveAll([](const TWeakObjectPtr<UParticleSystemComponent>& Item) { return !Item.IsValid(); });
	UParticleSystemComponent* Particle = SpawnOwnedEffect(Effect, Location, Rotation, Scale, SourceActor, Lifetime, bAttachToSource);
	if (Particle)
	{
		Particle->ComponentTags.Add(TEXT("CountessExtraFX"));
		ExtraOwnedEffects.Add(Particle);
	}
	return Particle;
}

ACountessExtraVisual* UCountessSkillComponent::SpawnExtraVisual(ECountessExtraVisual Kind,
	const FVector& Location, const FVector& Direction, float Lifetime, AActor* Follow)
{
	if (!GetWorld() || !Character.IsValid()) { return nullptr; }
	FActorSpawnParameters Params;
	Params.Owner = Character.Get();
	Params.ObjectFlags |= RF_Transient;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	ACountessExtraVisual* Visual = GetWorld()->SpawnActor<ACountessExtraVisual>(ACountessExtraVisual::StaticClass(),
		Location, Direction.Rotation(), Params);
	if (Visual)
	{
		Visual->Initialize(Kind, Direction, Lifetime, Follow);
		ExtraActors.RemoveAll([](const TWeakObjectPtr<AActor>& Item) { return !Item.IsValid(); });
		ExtraActors.Add(Visual);
	}
	return Visual;
}

void UCountessSkillComponent::SpawnExtraRushEcho(const FVector& Location)
{
	if (!GetWorld() || !Character.IsValid()) { return; }
	UMaterialInterface* SourceMaterial = FlurryShadowDissolveMaterial.LoadSynchronous();
	if (!SourceMaterial) { return; }
	FActorSpawnParameters Params;
	Params.Owner = Character.Get();
	Params.ObjectFlags |= RF_Transient;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	AActor* Echo = GetWorld()->SpawnActor<AActor>(AActor::StaticClass(), FTransform::Identity, Params);
	if (!Echo) { return; }
	Echo->SetCanBeDamaged(false);
	Echo->SetActorEnableCollision(false);
	Echo->Tags.Add(TEXT("CountessExtraRushEcho"));
	UPoseableMeshComponent* Mesh = NewObject<UPoseableMeshComponent>(Echo);
	Echo->SetRootComponent(Mesh);
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Mesh->SetGenerateOverlapEvents(false);
	Mesh->SetCanEverAffectNavigation(false);
	Mesh->SetSkinnedAssetAndUpdate(Character->GetMesh()->GetSkinnedAsset());
	Mesh->SetCastShadow(false);
	Mesh->RegisterComponent();
	FTransform Transform = Character->GetMesh()->GetComponentTransform();
	Transform.AddToTranslation(Location - Character->GetActorLocation());
	Mesh->SetWorldTransform(Transform);
	Mesh->CopyPoseFromSkeletalComponent(Character->GetMesh());
	Mesh->RefreshBoneTransforms();
	Mesh->SetComponentTickEnabled(false);
	UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(SourceMaterial, Echo);
	Material->SetScalarParameterValue(TEXT("DissolveStart"), GetWorld()->GetTimeSeconds() + .025f);
	Material->SetScalarParameterValue(TEXT("DissolveDuration"), .34f);
	for (int32 Slot = 0; Slot < Mesh->GetNumMaterials(); ++Slot) { Mesh->SetMaterial(Slot, Material); }
	Echo->SetLifeSpan(.40f);
	ExtraActors.RemoveAll([](const TWeakObjectPtr<AActor>& Item) { return !Item.IsValid(); });
	ExtraActors.Add(Echo);
	UE_LOG(LogTemp, Display, TEXT("COUNTESS_EXTRA rush echo=%d actual_pose=1"), ExtraRushEchoes + 1);
}

void UCountessSkillComponent::DamageExtraTarget(AActor* Target, float Damage, UParticleSystem* ImpactEffect)
{
	if (!Character.IsValid() || !IsValidSkillTarget(Target, Character.Get())) { return; }
	const FVector Direction = (Target->GetActorLocation() - Character->GetActorLocation()).GetSafeNormal();
	const FHitResult Hit(Target, nullptr, Target->GetActorLocation(), -Direction);
	UGameplayStatics::ApplyPointDamage(Target, Damage, Direction, Hit, Character->GetController(), Character.Get(), nullptr);
	const bool bAuthoredContact = ActiveSkillIndex == 8 || ActiveSkillIndex == 11;
	if (!bAuthoredContact) { SpawnExtraEffect(ImpactEffect, Target->GetActorLocation(), Direction.Rotation(), 0.9f, Target, 0.7f); }
	if (Damage >= 30.0f && ExtraImpactVisuals < 3)
	{
		SpawnExtraVisual(bAuthoredContact ? ECountessExtraVisual::AuthoredImpact : ECountessExtraVisual::Impact,
			Target->GetActorLocation(), Direction, .46f, bAuthoredContact ? Target : nullptr);
		++ExtraImpactVisuals;
	}
}

void UCountessSkillComponent::ExecuteExtraAction()
{
	if (!bCasting || bActionExecuted || !Character.IsValid() || !GetWorld() || ActiveSkillIndex < 8 || ActiveSkillIndex >= 12) { return; }
	const int32 ExtraIndex = ActiveSkillIndex - 8;
	const FCountessSkillDefinition& Skill = ExtraSkills[ExtraIndex];
	bActionExecuted = true;
	if (ExtraIndex == 0)
	{
		AActor* Target = CastTarget.Get();
		if (!IsValidSkillTarget(Target, Character.Get()) || !HasLineOfSight(Target) ||
			FVector::DistSquared2D(Target->GetActorLocation(), Character->GetActorLocation()) > FMath::Square(Skill.Range)) { FinishSkill(); return; }
		ExtraSealVisual = SpawnExtraVisual(ECountessExtraVisual::Seal, Target->GetActorLocation() + FVector(0, 0, 15),
			Character->GetActorForwardVector(), 1.05f, Target);
		// 대상 추적과 준비 FX는 ExtraSealVisual이 소유한다. 전용 사본은 bone 없는 대상에서도 같은 위치에 나온다.
		DamageExtraTarget(Target, 10.0f, nullptr);
		GetWorld()->GetTimerManager().SetTimer(ExtraFollowupTimer, this, &UCountessSkillComponent::ExecuteExtraFollowup,
			CountessExtras::SealBurstTime - Skill.ActionTime, false);
		UE_LOG(LogTemp, Display, TEXT("COUNTESS_EXTRA seal phase=mark damage=10 target=%s"), *Target->GetName());
	}
	else if (ExtraIndex == 1)
	{
		if (!FindExtraRushLanding(CastAim, ExtraLanding)) { FinishSkill(); return; }
		ExtraRushOrigin = Character->GetActorLocation();
		ExtraRushStartedAt = GetWorld()->GetTimeSeconds();
		bExtraRushActive = true;
		ExtraRushVisual = SpawnExtraVisual(ECountessExtraVisual::Rush, Character->GetActorLocation(),
			Character->GetActorForwardVector(), .65f, Character.Get());
		SpawnExtraEffect(Skill.CastEffect, GetFeetLocation(), Character->GetActorRotation(), 0.65f, Character.Get(), 0.5f);
		StartWeaponTrails();
		for (const TWeakObjectPtr<UParticleSystemComponent>& Trail : WeaponTrails)
		{
			if (Trail.IsValid())
			{
				Trail->ComponentTags.Add(TEXT("CountessExtraFX"));
				ExtraOwnedEffects.Add(Trail);
			}
		}
		DamageExtraRushSegment(ExtraRushOrigin, ExtraRushOrigin);
		UE_LOG(LogTemp, Display, TEXT("COUNTESS_EXTRA rush begin planned=%.1f"), FVector::Dist2D(ExtraRushOrigin, ExtraLanding));
	}
	else if (ExtraIndex == 2)
	{
		FVector Direction = (CastAim - Character->GetActorLocation()).GetSafeNormal2D();
		if (Direction.IsNearlyZero()) { Direction = Character->GetActorForwardVector(); }
		FActorSpawnParameters Params;
		Params.Owner = Character.Get();
		Params.Instigator = Character.Get();
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		ACountessExtraTide* Tide = GetWorld()->SpawnActor<ACountessExtraTide>(ACountessExtraTide::StaticClass(),
			Character->GetActorLocation() + Direction * 60.0f, Direction.Rotation(), Params);
		if (Tide)
		{
			Tide->Initialize(Direction, Skill.Damage, Skill.Range,
				bDetailedCast && DetailedTideEffect ? DetailedTideEffect.Get() : TideEffect.Get(), Skill.ImpactEffect);
			ExtraActors.RemoveAll([](const TWeakObjectPtr<AActor>& Item) { return !Item.IsValid(); });
			ExtraActors.Add(Tide);
		}
		SpawnExtraEffect(Skill.CastEffect, GetFeetLocation(), Character->GetActorRotation(), 0.8f, Character.Get(), 0.6f);
		UE_LOG(LogTemp, Display, TEXT("COUNTESS_EXTRA tide released=%d damage=%.1f range=%.1f"), Tide != nullptr, Skill.Damage, Skill.Range);
	}
	else
	{
		if (!FindExtraAmbushLanding(CastAim, CastTarget.Get(), ExtraLanding)) { FinishSkill(); return; }
		AActor* Shadow = SpawnSkeletalProxy(1.5f, true);
		USkeletalMeshComponent* Mesh = Shadow ? Shadow->FindComponentByClass<USkeletalMeshComponent>() : nullptr;
		UMaterialInterface* DissolveMaterial = FlurryShadowDissolveMaterial.LoadSynchronous();
		if (!Mesh || !DissolveMaterial) { if (Shadow) { Shadow->Destroy(); } FinishSkill(); return; }
		ExtraAmbushShadow = Shadow;
		Shadow->Tags.Add(TEXT("CountessExtraAmbush"));
		ExtraActors.RemoveAll([](const TWeakObjectPtr<AActor>& Item) { return !Item.IsValid(); });
		ExtraActors.Add(Shadow);
		UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(DissolveMaterial, Shadow);
		Material->SetScalarParameterValue(TEXT("DissolveStart"), 1000000.0f);
		Material->SetScalarParameterValue(TEXT("DissolveDuration"), 0.45f);
		for (int32 Slot = 0; Slot < Mesh->GetNumMaterials(); ++Slot) { Mesh->SetMaterial(Slot, Material); }
		const FTransform RelativeMesh = Character->GetMesh()->GetComponentTransform().GetRelativeTransform(Character->GetActorTransform());
		Mesh->SetWorldTransform(RelativeMesh * FTransform(Character->GetActorRotation(), ExtraLanding));
		Mesh->SetBoundsScale(1.4f);
		if (ExtraAmbushAttackAnimation)
		{
			Mesh->PlayAnimation(ExtraAmbushAttackAnimation, false);
			Mesh->SetPosition(0.0f, false);
			Mesh->SetPlayRate(0.0f);
			Mesh->GetAnimInstance()->SetRootMotionMode(ERootMotionMode::IgnoreRootMotion);
			Mesh->TickAnimation(0.0f, false);
			Mesh->RefreshBoneTransforms();
		}
		ExtraAmbushVisual = SpawnExtraVisual(ECountessExtraVisual::Ambush,
			ExtraLanding - FVector(0, 0, Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()),
			Character->GetActorForwardVector(), 1.25f);
		SpawnExtraEffect(Skill.CastEffect, ExtraLanding - FVector(0, 0, Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()),
			Character->GetActorRotation(), 0.65f, Shadow, 0.65f);
		GetWorld()->GetTimerManager().SetTimer(ExtraFollowupTimer, this, &UCountessSkillComponent::ExecuteExtraFollowup,
			CountessExtras::AmbushBurstTime - Skill.ActionTime, false);
		UE_LOG(LogTemp, Display, TEXT("COUNTESS_EXTRA ambush placed x=%.1f y=%.1f radius=240"), ExtraLanding.X, ExtraLanding.Y);
	}
}

void UCountessSkillComponent::ExecuteExtraFollowup()
{
	if (!bCasting || bExtraFollowupExecuted || !Character.IsValid() || !GetWorld()) { return; }
	bExtraFollowupExecuted = true;
	if (ActiveSkillIndex == 8)
	{
		if (ExtraSealMarker.IsValid()) { ExtraSealMarker->DestroyComponent(); }
		ExtraSealMarker.Reset();
		AActor* Target = CastTarget.Get();
		if (!IsValidSkillTarget(Target, Character.Get()) || !HasLineOfSight(Target) ||
			FVector::DistSquared2D(Target->GetActorLocation(), Character->GetActorLocation()) > FMath::Square(ExtraSkills[0].Range) ||
			FMath::Abs(Target->GetActorLocation().Z - Character->GetActorLocation().Z) > 180.0f) { return; }
		if (ExtraSealVisual.IsValid()) { ExtraSealVisual->Trigger(); }
		// 원본 입체 준비→파열→잔여 입자 전개는 위 Trigger에서 시작한다.
		DamageExtraTarget(Target, ExtraSkills[0].Damage, ExtraSkills[0].ImpactEffect);
		UE_LOG(LogTemp, Display, TEXT("COUNTESS_EXTRA seal phase=burst damage=%.1f target=%s"), ExtraSkills[0].Damage, *Target->GetName());
	}
	else if (ActiveSkillIndex == 11 && ExtraAmbushShadow.IsValid())
	{
		if (USkeletalMeshComponent* Mesh = ExtraAmbushShadow->FindComponentByClass<USkeletalMeshComponent>(); Mesh && ExtraAmbushAttackAnimation)
		{
			// 원본 양검 소켓 최고 속도는 .20초다. .60초 준비 해제 뒤 .80초 판정과 같은 포즈를 확정한다.
			Mesh->SetPosition(CountessExtras::AmbushClipHitTime, true);
			Mesh->SetPlayRate(1.0f);
			Mesh->TickAnimation(0.0f, false);
			Mesh->RefreshBoneTransforms();
		}
		if (ExtraAmbushVisual.IsValid()) { ExtraAmbushVisual->Trigger(); }
		FCollisionObjectQueryParams Objects;
		Objects.AddObjectTypesToQuery(ECC_Pawn);
		Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
		FCollisionQueryParams Query(SCENE_QUERY_STAT(CountessExtraAmbush), false, Character.Get());
		TArray<FOverlapResult> Overlaps;
		GetWorld()->OverlapMultiByObjectType(Overlaps, ExtraLanding, FQuat::Identity,
			Objects, FCollisionShape::MakeSphere(CountessExtras::AmbushRadius), Query);
		// 폭발 안의 적은 서로를 가리지 않는다. 벽과 일반 장애물의 시야 차단은 유지한다.
		FCollisionQueryParams BlastSightQuery = Query;
		for (const FOverlapResult& Overlap : Overlaps)
		{
			AActor* Actor = Overlap.GetActor();
			if (Actor && (Actor->IsA<APawn>() || Actor->IsA<AKwangTrainingDummy>()))
			{
				BlastSightQuery.AddIgnoredActor(Actor);
			}
		}
		TSet<AActor*> Hits;
		for (const FOverlapResult& Overlap : Overlaps)
		{
			AActor* Target = Overlap.GetActor();
			if (!IsValidSkillTarget(Target, Character.Get()) || Hits.Contains(Target) ||
				FVector::DistSquared2D(Target->GetActorLocation(), ExtraLanding) > FMath::Square(CountessExtras::AmbushRadius) ||
				FMath::Abs(Target->GetActorLocation().Z - ExtraLanding.Z) > 150.0f) { continue; }
			FCollisionQueryParams SightQuery = BlastSightQuery;
			SightQuery.AddIgnoredActor(Target);
			FHitResult Obstacle;
			if (GetWorld()->LineTraceSingleByChannel(Obstacle, ExtraLanding, Target->GetActorLocation(), ECC_Visibility, SightQuery)) { continue; }
			Hits.Add(Target);
			DamageExtraTarget(Target, ExtraSkills[3].Damage, ExtraSkills[3].ImpactEffect);
		}
		SpawnExtraEffect(GetVisualEffect(EVisualEffect::CloneBurst), ExtraLanding - FVector(0, 0, 90),
			Character->GetActorRotation(), 1.15f, ExtraAmbushShadow.Get(), 0.7f);
		UE_LOG(LogTemp, Display, TEXT("COUNTESS_EXTRA ambush burst hits=%d damage=%.1f"), Hits.Num(), ExtraSkills[3].Damage);
		RetireExtraAmbush();
	}
}

void UCountessSkillComponent::DamageExtraRushSegment(const FVector& Start, const FVector& End)
{
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_Pawn);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	FCollisionQueryParams Query(SCENE_QUERY_STAT(CountessExtraRushHit), false, Character.Get());
	TArray<FHitResult> Hits;
	GetWorld()->SweepMultiByObjectType(Hits, Start, End, FQuat::Identity,
		Objects, FCollisionShape::MakeSphere(CountessExtras::RushRadius), Query);
	for (const FHitResult& Hit : Hits)
	{
		AActor* Target = Hit.GetActor();
		if (!IsValidSkillTarget(Target, Character.Get()) || ExtraRushHits.Contains(Target) || !HasLineOfSight(Target) ||
			FMath::Abs(Target->GetActorLocation().Z - End.Z) > 150.0f) { continue; }
		ExtraRushHits.Add(Target);
		DamageExtraTarget(Target, ExtraSkills[1].Damage, ExtraSkills[1].ImpactEffect);
		UE_LOG(LogTemp, Display, TEXT("COUNTESS_EXTRA rush hit target=%s damage=%.1f"), *Target->GetName(), ExtraSkills[1].Damage);
	}
}

void UCountessSkillComponent::UpdateExtraRush()
{
	if (!Character.IsValid() || !GetWorld()) { return; }
	if (ActiveSkillIndex == 8 && !IsValidSkillTarget(CastTarget.Get(), Character.Get())) { FinishSkill(); return; }
	if (ActiveSkillIndex == 11 && bActionExecuted && !bExtraFollowupExecuted && !ExtraAmbushShadow.IsValid()) { FinishSkill(); return; }
	if (ActiveSkillIndex == 11 && ExtraAmbushShadow.IsValid() && !bExtraAmbushStrikeStarted &&
		GetWorld()->GetTimeSeconds() - ExtraCastStartedAt >= CountessExtras::AmbushAttackBegin)
	{
		bExtraAmbushStrikeStarted = true;
		if (USkeletalMeshComponent* Mesh = ExtraAmbushShadow->FindComponentByClass<USkeletalMeshComponent>(); Mesh && ExtraAmbushAttackAnimation)
		{
			Mesh->SetPosition(FMath::Min(CountessExtras::AmbushClipHitTime,
				static_cast<float>(GetWorld()->GetTimeSeconds() - ExtraCastStartedAt - CountessExtras::AmbushAttackBegin)), true);
			Mesh->SetPlayRate(1.0f);
			UParticleSystem* TrailAsset = FlurryBladeEffect.LoadSynchronous();
			UMaterialInterface* TrailMaterial = FlurryBladeMaterial.LoadSynchronous();
			for (const TCHAR* Side : {TEXT("L"), TEXT("R")})
			{
				const FName Base(*FString::Printf(TEXT("FX_WeaponBase_%s"), Side));
				const FName Tip(*FString::Printf(TEXT("FX_WeaponTip_%s"), Side));
				if (!Mesh->DoesSocketExist(Base) || !Mesh->DoesSocketExist(Tip)) { continue; }
				UParticleSystemComponent* Trail = SpawnExtraEffect(TrailAsset,
					Mesh->GetComponentLocation(), Mesh->GetComponentRotation(), 1.0f, Mesh->GetOwner(), .42f, true);
				if (Trail)
				{
					if (TrailMaterial) { Trail->SetMaterial(0, TrailMaterial); }
					Trail->BeginTrails(Base, Tip, ETrailWidthMode_FromCentre, .55f);
					Trail->SetLODLevel(0);
					Trail->ComponentTags.Add(TEXT("CountessSkillWeaponTrail"));
					WeaponTrails.Add(Trail);
				}
			}
			UE_LOG(LogTemp, Display, TEXT("COUNTESS_EXTRA ambush strike_begin clip_hit=.20 cast_hit=.80"));
		}
	}
	// F는 타격 전후의 짧은 창만 소켓 궤적을 남긴다. 원본 QWER의 trail 수명은 바꾸지 않는다.
	if (ActiveSkillIndex == 11 && bExtraFollowupExecuted && !WeaponTrails.IsEmpty() &&
		GetWorld()->GetTimeSeconds() - ExtraCastStartedAt >= .91f)
	{
		StopWeaponTrails();
	}
	if (!bExtraRushActive || !Character.IsValid() || !GetWorld()) { return; }
	const float Progress = FMath::Clamp(static_cast<float>((GetWorld()->GetTimeSeconds() - ExtraRushStartedAt) / CountessExtras::RushSeconds), 0.0f, 1.0f);
	const FVector Start = Character->GetActorLocation();
	const FVector Desired = FMath::Lerp(ExtraRushOrigin, ExtraLanding, Progress);
	FHitResult Hit;
	Character->SetActorLocation(Desired, true, &Hit);
	DamageExtraRushSegment(Start, Character->GetActorLocation());
	const float PreviousDistance = FVector::Dist2D(ExtraRushOrigin, Start);
	const float CurrentDistance = FVector::Dist2D(ExtraRushOrigin, Character->GetActorLocation());
	while (ExtraRushEchoes < 3 && CurrentDistance >= 35.0f + ExtraRushEchoes * 70.0f)
	{
		const float Along = FMath::Clamp((35.0f + ExtraRushEchoes * 70.0f - PreviousDistance) /
			FMath::Max(.01f, CurrentDistance - PreviousDistance), 0.0f, 1.0f);
		SpawnExtraRushEcho(FMath::Lerp(Start, Character->GetActorLocation(), Along));
		++ExtraRushEchoes;
	}
	if (Progress >= 1.0f || Hit.bBlockingHit)
	{
		bExtraRushActive = false;
		if (ExtraRushVisual.IsValid()) { ExtraRushVisual->Retire(); }
		Character->GetCharacterMovement()->StopMovementImmediately();
		StopWeaponTrails();
		SpawnExtraEffect(TeleportArrivalEffect, GetFeetLocation(), Character->GetActorRotation(), 0.55f, Character.Get(), 0.5f);
		UE_LOG(LogTemp, Display, TEXT("COUNTESS_EXTRA rush end moved=%.1f blocked=%d hits=%d"),
			FVector::Dist2D(ExtraRushOrigin, Character->GetActorLocation()), Hit.bBlockingHit, ExtraRushHits.Num());
	}
}

void UCountessSkillComponent::RetireExtraAmbush()
{
	if (ExtraAmbushShadow.IsValid())
	{
		AActor* Shadow = ExtraAmbushShadow.Get();
		Shadow->Tags.Remove(TEXT("CountessExtraAmbush"));
		Shadow->Tags.Add(TEXT("CountessExtraAmbushDissolving"));
		if (USkeletalMeshComponent* Mesh = Shadow->FindComponentByClass<USkeletalMeshComponent>())
		{
			if (UMaterialInstanceDynamic* Material = Cast<UMaterialInstanceDynamic>(Mesh->GetMaterial(0)); Material && GetWorld())
			{
				Material->SetScalarParameterValue(TEXT("DissolveStart"), GetWorld()->GetTimeSeconds());
			}
		}
		Shadow->SetLifeSpan(0.5f);
	}
	ExtraAmbushShadow.Reset();
}

void UCountessSkillComponent::ClearExtraCast()
{
	if (GetWorld()) { GetWorld()->GetTimerManager().ClearTimer(ExtraFollowupTimer); }
	if (ExtraSealMarker.IsValid()) { ExtraSealMarker->DestroyComponent(); }
	ExtraSealMarker.Reset();
	if (ExtraSealVisual.IsValid() && !bExtraFollowupExecuted) { ExtraSealVisual->Retire(); }
	if (ExtraAmbushVisual.IsValid() && !bExtraFollowupExecuted) { ExtraAmbushVisual->Retire(); }
	if (ExtraRushVisual.IsValid()) { ExtraRushVisual->Retire(); }
	ExtraSealVisual.Reset();
	ExtraAmbushVisual.Reset();
	ExtraRushVisual.Reset();
	RetireExtraAmbush();
	if (bExtraRushActive && Character.IsValid()) { Character->GetCharacterMovement()->StopMovementImmediately(); }
	bExtraRushActive = false;
	ExtraRushHits.Reset();
	if (ActiveSkillIndex >= 8)
	{
		UE_LOG(LogTemp, Display, TEXT("COUNTESS_EXTRA finish slot=%d acted=%d followup=%d"), ActiveSkillIndex, bActionExecuted, bExtraFollowupExecuted);
	}
}

void UCountessSkillComponent::ClearExtraWorldEffects()
{
	for (const TWeakObjectPtr<UParticleSystemComponent>& Effect : ExtraOwnedEffects)
	{
		if (Effect.IsValid()) { Effect->DestroyComponent(); }
	}
	ExtraOwnedEffects.Reset();
	for (const TWeakObjectPtr<AActor>& Actor : ExtraActors)
	{
		if (Actor.IsValid()) { Actor->Destroy(); }
	}
	ExtraActors.Reset();
}
