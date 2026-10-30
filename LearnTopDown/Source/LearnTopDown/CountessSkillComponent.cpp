#include "CountessSkillComponent.h"
#include "CountessRebirthFX.h"
#include "CountessBackstepEcho.h"

#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/AudioComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialParameters.h"
#include "CountessDarkTide.h"
#include "CountessSkillLensEffect.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "GameFramework/Controller.h"
#include "GameFramework/Pawn.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "TopDownCombatCharacter.h"
#include "KwangTrainingDummy.h"
#include "NavigationSystem.h"
#include "Materials/MaterialInterface.h"
#include "Misc/Paths.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "Particles/ParticleEmitter.h"
#include "Particles/ParticleLODLevel.h"
#include "Particles/TypeData/ParticleModuleTypeDataMesh.h"
#include "ParticleEmitterInstances.h"
#include "Sound/SoundBase.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"

static constexpr float FeastInstantStartTime = 1.05f;
static constexpr float FeastInstantPlayRate = 1.75f;
static constexpr float CursorBlinkRange = 750.0f;
static constexpr float CursorBlinkCooldown = 6.0f;
static constexpr float FeastApproachSeconds = 0.5f;

static constexpr float FlurryStrikeSeconds = 0.22f / 1.5f;
static constexpr float FlurryClipSeconds = 2.0f * FlurryStrikeSeconds;
static constexpr float FlurryHitOffset = 0.14f;
static constexpr float FlurryRecoverySeconds = 5.0f * FlurryStrikeSeconds + FlurryClipSeconds + 0.14f;
static TAutoConsoleVariable<int32> CVarCountessEFlurry(
	TEXT("Countess.Skills.EFlurry"), 1,
	TEXT("Training-room E prototype at pawn spawn: 1 body/shadow six-cut duet; 0 original Dark Tide."));
static TAutoConsoleVariable<float> CVarCountessEInkGain(
	TEXT("Countess.Skills.EInkGain"), .06f,
	TEXT("Instance-only E slash emissive gain after the original color gradient."));

static TAutoConsoleVariable<int32> CVarCountessIgnoreCooldowns(
	TEXT("Countess.Skills.IgnoreCooldowns"), 1,
	TEXT("Practice mode: 1 ignores Countess skill cooldowns; 0 restores configured cooldowns."));

static TAutoConsoleVariable<int32> CVarCountessDetailedFX(
	TEXT("Countess.Skills.DetailedFX"), 1,
	TEXT("Presentation only: 1 detailed original-effect reconstruction; 0 preserved rough presentation."));

static TAutoConsoleVariable<int32> CVarCountessSkillAudio(
	TEXT("Countess.Skills.Audio"), 0,
	TEXT("Audio only: 0 disables Countess skill voice and combat sounds; 1 enables them."));

static TAutoConsoleVariable<int32> CVarCountessSkillVoice(
	TEXT("Countess.Skills.Voice"), 0,
	TEXT("Voice only: 0 disables Countess skill effort and scream voices; 1 enables them when skill audio is enabled."));

static TAutoConsoleVariable<int32> CVarCountessQSwordAudio(
	TEXT("Countess.Skills.QSwordAudio"), 1,
	TEXT("Q audio only: 1 uses the selected sword pack sounds; 0 preserves the previous synthetic sounds."));

static TAutoConsoleVariable<int32> CVarCountessQRushAudio(
	TEXT("Countess.Skills.QRushAudio"), 1,
	TEXT("Q audio only: 1 layers movement, slash and softened impact; 0 preserves the first sword-pack version."));

static TAutoConsoleVariable<int32> CVarCountessQPresentation(
	TEXT("Countess.Skills.QPresentation"), 3,
	TEXT("Q visuals only: 3 uses short outward cuts; 2 compares measured curves; 1 compares the crescent; 0 preserves the original."));

static TAutoConsoleVariable<int32> CVarCountessQTone(
	TEXT("Countess.Skills.QTone"), 1,
	TEXT("Q color only: 1 matches muted blood-red effects; 0 compares the previous bright core."));

static TAutoConsoleVariable<float> CVarCountessQLengthScale(
	TEXT("Countess.Skills.QLengthScale"), 0.52f,
	TEXT("Outward Q lateral visual length only, clamped to 0.35..1; damage and reach are unchanged."));

static TAutoConsoleVariable<int32> CVarCountessWPresentation(
	TEXT("Countess.Skills.WPresentation"), 3,
	TEXT("W visuals only: 3 connects the textured spiral; 2 compares the outer front; 1 compares the dense vortex; 0 preserves the original."));

static TAutoConsoleVariable<float> CVarCountessWPlayRate(
	TEXT("Countess.Skills.WPlayRate"), 1.95f,
	TEXT("W animation, action/recovery and particle playback multiplier, clamped to 0.5..2."));

static TAutoConsoleVariable<int32> CVarCountessWPreview(
	TEXT("Countess.Skills.WPreview"), 0,
	TEXT("W visual preview only: 1 close smoke and short blade shadows/outer echoes; 0 keeps the current veil."));

bool UCountessSkillComponent::UsesDetailedPresentation()
{
	return CVarCountessDetailedFX.GetValueOnGameThread() != 0;
}

bool UCountessSkillComponent::UsesSkillAudio()
{
	return CVarCountessSkillAudio.GetValueOnGameThread() != 0;
}

bool UCountessSkillComponent::UsesSkillVoice()
{
	return UsesSkillAudio() && CVarCountessSkillVoice.GetValueOnGameThread() != 0;
}

bool UCountessSkillComponent::UsesQSwordAudio()
{
	return CVarCountessQSwordAudio.GetValueOnGameThread() != 0;
}

bool UCountessSkillComponent::UsesQRushAudio()
{
	return UsesQSwordAudio() && CVarCountessQRushAudio.GetValueOnGameThread() != 0;
}

UCountessSkillComponent::UCountessSkillComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.bStartWithTickEnabled = false;
	const TCHAR* Animations[] = {TEXT("Ability_Q"), TEXT("Ability_RMB"), TEXT("Ability_E"), TEXT("Ability_Ultimate")};
	const TCHAR* Names[] = {TEXT("ShadowSlip"), TEXT("BladeSiphon"), TEXT("DarkTide"), TEXT("Feast")};
	const TCHAR* SoundNames[] = {TEXT("Q"), TEXT("RMB"), TEXT("E"), TEXT("Ultimate")};
	const TCHAR* EffectFolders[] = {TEXT("BlinkStrike"), TEXT("BladeSiphon"), TEXT("RollingDark"), TEXT("Ultimate")};
	const TCHAR* CastEffects[] = {TEXT("P_Countess_TeleportBegin"), TEXT("P_Countess_BladeSiphon_RingFX"),
		TEXT("P_Countess_RD_CastBurst"), TEXT("p_CountessUlt_CastFX")};
	const TCHAR* ImpactEffects[] = {TEXT("P_Countess_BlinkStrike_HitFX"), TEXT("p_Countess_BladeSiphon_HitFX"),
		TEXT("p_RollingDark_ImpactFX"), TEXT("P_CountessUlt_Stab")};
	// 기존 평타 피해 20과 HP 100 허수아비에 맞춘 클라이언트 시연 수치다. 원본 모션과 FX는 유지한다.
	const float Damage[] = {35.0f, 40.0f, 45.0f, 80.0f};
	const float Cooldown[] = {8.0f, 6.0f, 8.0f, 20.0f};
	const float Range[] = {850.0f, 240.0f, 900.0f, 500.0f};
	const float ActionTime[] = {0.2f, 0.55f, 0.36f, 1.8f};
	const float Recovery[] = {0.65f, 0.95f, 0.8f, 2.25f};
	Skills.SetNum(4);
	for (int32 Index = 0; Index < 4; ++Index)
	{
		FCountessSkillDefinition& Skill = Skills[Index];
		Skill.Name = Names[Index];
		const FString AnimationPath = FString::Printf(TEXT("/Game/ParagonCountess/Characters/Heroes/Countess/Animations/%s.%s"),
			Animations[Index], Animations[Index]);
		ConstructorHelpers::FObjectFinder<UAnimSequence> Animation(*AnimationPath);
		Skill.Animation = Animation.Object;
		const FString CastPath = FString::Printf(TEXT("/Game/ParagonCountess/FX/Particles/Abilities/%s/FX/%s.%s"), EffectFolders[Index], CastEffects[Index], CastEffects[Index]);
		ConstructorHelpers::FObjectFinder<UParticleSystem> CastEffect(*CastPath);
		Skill.CastEffect = CastEffect.Object;
		const FString ImpactPath = FString::Printf(TEXT("/Game/ParagonCountess/FX/Particles/Abilities/%s/FX/%s.%s"), EffectFolders[Index], ImpactEffects[Index], ImpactEffects[Index]);
		ConstructorHelpers::FObjectFinder<UParticleSystem> ImpactEffect(*ImpactPath);
		Skill.ImpactEffect = ImpactEffect.Object;
		const FString SoundPath = FString::Printf(TEXT("/Game/ParagonCountess/Characters/Heroes/Countess/Sounds/SoundCues/Countess_Effort_Ability_%s.Countess_Effort_Ability_%s"), SoundNames[Index], SoundNames[Index]);
		ConstructorHelpers::FObjectFinder<USoundBase> CastSound(*SoundPath);
		Skill.CastSound = CastSound.Object;
		Skill.Damage = Damage[Index];
		Skill.Cooldown = Cooldown[Index];
		Skill.Range = Range[Index];
		Skill.ActionTime = ActionTime[Index];
		Skill.RecoveryTime = Recovery[Index];
	}
	Skills[2].ImpactEffect = Skills[0].ImpactEffect;
	ConstructorHelpers::FObjectFinder<UParticleSystem> Return(TEXT("/Game/ParagonCountess/FX/Particles/Abilities/BlinkStrike/FX/p_Countess_ShadowCloneSupplementalFX.p_Countess_ShadowCloneSupplementalFX"));
	ReturnEffect = Return.Object;
	ConstructorHelpers::FObjectFinder<UParticleSystem> Trails(TEXT("/Game/ParagonCountess/FX/Particles/Abilities/BladeSiphon/FX/P_Countess_BladeSiphon_Trails.P_Countess_BladeSiphon_Trails"));
	SiphonTrails = Trails.Object;
	ConstructorHelpers::FObjectFinder<UParticleSystem> DenseRing(
		TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessW_DenseRing.P_CountessW_DenseRing"));
	DetailedSiphonRing = DenseRing.Object;
	ConstructorHelpers::FObjectFinder<UParticleSystem> RimRing(
		TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessW_RimRing.P_CountessW_RimRing"));
	RimSiphonRing = RimRing.Object;
	ConstructorHelpers::FObjectFinder<UParticleSystem> SpiralRing(
		TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessW_SpiralRing.P_CountessW_SpiralRing"));
	SpiralSiphonRing = SpiralRing.Object;
	LightSiphonRing = TSoftObjectPtr<UParticleSystem>(FSoftObjectPath(
		TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessW_VeilRing.P_CountessW_VeilRing")));
	ConstructorHelpers::FObjectFinder<UParticleSystem> DenseTrails(
		TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessW_DenseTrails.P_CountessW_DenseTrails"));
	DetailedSiphonTrails = DenseTrails.Object;
	ConstructorHelpers::FObjectFinder<UParticleSystem> DenseHit(
		TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessW_DenseHit.P_CountessW_DenseHit"));
	DetailedSiphonImpact = DenseHit.Object;
	ConstructorHelpers::FObjectFinder<UParticleSystem> Tide(TEXT("/Game/ParagonCountess/FX/Particles/Abilities/RollingDark/FX/p_RollingDark_SegmentFX.p_RollingDark_SegmentFX"));
	TideEffect = Tide.Object;
	ConstructorHelpers::FObjectFinder<UParticleSystem> DetailedTide(TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessDarkTideDetailed.P_CountessDarkTideDetailed"));
	DetailedTideEffect = DetailedTide.Object;
	ConstructorHelpers::FObjectFinder<UParticleSystem> Arrival(TEXT("/Game/ParagonCountess/FX/Particles/Abilities/BlinkStrike/FX/P_Countess_TeleportArrive.P_Countess_TeleportArrive"));
	TeleportArrivalEffect = Arrival.Object;
	ConstructorHelpers::FObjectFinder<UParticleSystem> Application(TEXT("/Game/ParagonCountess/FX/Particles/Abilities/Ultimate/FX/p_CountessUlt_ApplicationFX.p_CountessUlt_ApplicationFX"));
	FeastApplicationEffect = Application.Object;
	const TCHAR* ExtraEffects[] = {
		TEXT("Abilities/BlinkStrike/FX/p_Countess_BlinkStrikeFlash"),
		TEXT("Abilities/BlinkStrike/FX/p_Countess_XSlash"),
		TEXT("Abilities/BlinkStrike/FX/p_Countess_ShadowCloneBurst"),
		TEXT("Abilities/BlinkStrike/FX/p_Countess_ReturnBlinkStart"),
		TEXT("Abilities/RollingDark/FX/P_Countess_RD_CastToGround"),
		TEXT("Abilities/Ultimate/FX/p_CountessUlt_EyeFX_Looping"),
		TEXT("Abilities/Ultimate/FX/p_CountessUlt_SlashFX"),
		TEXT("Abilities/Ultimate/FX/p_CountessUlt_GroundImpactFX"),
		TEXT("Abilities/Ultimate/FX/p_CountessUltImpact"),
		TEXT("p_CountessMeleeTrail"),
		TEXT("Abilities/Ultimate/FX/p_CountessUlt_AimingSwords"),
		TEXT("Abilities/BlinkStrike/FX/p_Countess_BlinkStrike_Aiming"),
		TEXT("Abilities/Primary/FX/p_SmokeyBlade"),
		TEXT("Abilities/Ultimate/FX/p_CountessUlt_AimingFX"),
		TEXT("Abilities/Ultimate/FX/p_CountessUlt_AimingSwordsRemove"),
		TEXT("Abilities/Ultimate/FX/p_CountessUlt_EyeFX_Burst"),
		TEXT("Abilities/RollingDark/FX/p_RollingDark_Aiming"),
		TEXT("Abilities/BlinkStrike/FX/P_Countess_BlinkStartCameraLensFX"),
		TEXT("Abilities/BlinkStrike/FX/P_Countess_BlinkReturnOutCameraLensFX"),
		TEXT("Abilities/BlinkStrike/FX/P_Countess_BlinkDurationCameraLensFX"),
		TEXT("Abilities/RollingDark/FX/P_RollingDark_CameraEffect")};
	static_assert(UE_ARRAY_COUNT(ExtraEffects) == static_cast<uint8>(EVisualEffect::Count));
	for (const TCHAR* RelativePath : ExtraEffects)
	{
		const FString Name = FPaths::GetCleanFilename(RelativePath);
		const FString Path = FString::Printf(TEXT("/Game/ParagonCountess/FX/Particles/%s.%s"), RelativePath, *Name);
		ConstructorHelpers::FObjectFinder<UParticleSystem> Effect(*Path);
		VisualEffects.Add(Effect.Object);
	}
	ConstructorHelpers::FObjectFinder<UMaterialInterface> BlinkAccentMaterialAsset(
		TEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessQCrescent.M_CountessQCrescent"));
	BlinkAccentMaterial = BlinkAccentMaterialAsset.Object;
	ConstructorHelpers::FObjectFinder<UStaticMesh> BlinkAccentMeshAsset(TEXT("/Engine/BasicShapes/Plane.Plane"));
	BlinkAccentMesh = BlinkAccentMeshAsset.Object;
	ConstructorHelpers::FObjectFinder<UMaterialInterface> DualSweepMaterialAsset(
		TEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessQDualSweep.M_CountessQDualSweep"));
	DualSweepMaterial = DualSweepMaterialAsset.Object;
	ConstructorHelpers::FObjectFinder<UStaticMesh> DualSweepMeshAsset(
		TEXT("/Game/TopDown/Characters/Countess/FX/SM_CountessQDualSweep.SM_CountessQDualSweep"));
	DualSweepMesh = DualSweepMeshAsset.Object;
	ConstructorHelpers::FObjectFinder<UMaterialInterface> OutwardCutMaterialAsset(
		TEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessQOutwardMuted.M_CountessQOutwardMuted"));
	OutwardCutMaterial = OutwardCutMaterialAsset.Object;
	CompactOutwardCutMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
		TEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessQOutwardWispy.M_CountessQOutwardWispy")));
	ConstructorHelpers::FObjectFinder<UStaticMesh> OutwardCutMeshAsset(
		TEXT("/Game/TopDown/Characters/Countess/FX/SM_CountessQOutwardCut.SM_CountessQOutwardCut"));
	OutwardCutMesh = OutwardCutMeshAsset.Object;
	ConstructorHelpers::FObjectFinder<UMaterialInterface> CloneMaterial(TEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessSkillShadowClone.M_CountessSkillShadowClone"));
	ShadowCloneMaterial = CloneMaterial.Object;
	ConstructorHelpers::FObjectFinder<UMaterialInterface> DetailedClone(TEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessSkillShadowCloneDetailed.M_CountessSkillShadowCloneDetailed"));
	DetailedCloneMaterial = DetailedClone.Object;
	FlurryShadowDissolveMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
		TEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessEShadowDissolve.M_CountessEShadowDissolve")));
	FlurryBladeMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
		TEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessESharpBladeTrail.M_CountessESharpBladeTrail")));
	FlurryBladeEffect = TSoftObjectPtr<UParticleSystem>(FSoftObjectPath(
		TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessESharpTrail.P_CountessESharpTrail")));
	FlurryTargetCutMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
		TEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessETargetCut.M_CountessETargetCut")));
	const TCHAR* CombatNames[] = {TEXT("Blink"), TEXT("Blade"), TEXT("Tide"), TEXT("FeastCharge"), TEXT("FeastHit"), TEXT("Impact"), TEXT("QSlash"), TEXT("QHit"), TEXT("QRush"), TEXT("QRushSlash"), TEXT("QRushHit")};
	static_assert(UE_ARRAY_COUNT(CombatNames) == static_cast<uint8>(ESkillSound::Count));
	for (const TCHAR* SoundName : CombatNames)
	{
		const FString Path = FString::Printf(TEXT("/Game/TopDown/Characters/Countess/Audio/SW_CountessSkill_%s.SW_CountessSkill_%s"), SoundName, SoundName);
		ConstructorHelpers::FObjectFinder<USoundBase> CombatSound(*Path);
		CombatSounds.Add(CombatSound.Object);
	}
	ConstructorHelpers::FObjectFinder<UAnimSequence> CloneIdle(TEXT("/Game/ParagonCountess/Characters/Heroes/Countess/Animations/Idle_Relaxed.Idle_Relaxed"));
	ShadowCloneIdle = CloneIdle.Object;
	for (const TCHAR* Name : {TEXT("Primary_Attack_Fast_V1"), TEXT("Primary_Attack_A_Fast_V1"), TEXT("Primary_Attack_B_Fast_InMotion")})
	{
		const FString Path = FString::Printf(TEXT("/Game/ParagonCountess/Characters/Heroes/Countess/Animations/%s.%s"), Name, Name);
		ConstructorHelpers::FObjectFinder<UAnimSequence> Source(*Path);
		FlurrySources.Add(Source.Object);
	}
	InitializeExtraDefinitions();
}

void UCountessSkillComponent::BeginPlay()
{
	Super::BeginPlay();
	Character = Cast<ATopDownCombatCharacter>(GetOwner());
	const USkeletalMesh* Mesh = Character.IsValid() && Character->GetMesh() ? Character->GetMesh()->GetSkeletalMeshAsset() : nullptr;
	if (!Mesh || Skills.Num() != 4)
	{
		return;
	}
	// E는 보관된 원래 DarkTide 정의로 복원한다. 이전 시제품의 BP 직렬화 값도 남기지 않는다.
	Skills[2] = GetDefault<UCountessSkillComponent>()->Skills[2];
	for (int32 Index = 0; Index < Skills.Num(); ++Index)
	{
		const FCountessSkillDefinition& Skill = Skills[Index];
		// 같은 C++ 캐릭터를 쓰는 기존 Kwang에는 카운테스 모션을 적용하지 않는다.
		if (!Skill.Animation || Skill.Animation->GetSkeleton() != Mesh->GetSkeleton())
		{
			return;
		}
		UAnimMontage* Montage = UAnimMontage::CreateSlotAnimationAsDynamicMontage(
			Skill.Animation, TEXT("CountessFullBody"), 0.08f, 0.14f, 1.0f, 1);
		if (!Montage)
		{
			SkillMontages.Reset();
			return;
		}
		SkillMontages.Add(Montage);
	}
	bEnabled = true;
}

bool UCountessSkillComponent::CreateFlurryMontages()
{
	if (FlurrySources.Num() != 3) { return false; }
	const float Starts[] = {0.0f, 0.0f, 0.0f};
	const float Ends[] = {0.30f, 0.30f, 0.27f};
	const int32 Sources[] = {0, 0, 1, 1, 2, 2};
	for (int32 Index = 0; Index < 6; ++Index)
	{
		const int32 SourceIndex = Sources[Index];
		UAnimSequence* Source = FlurrySources[SourceIndex];
		if (!Source || Source->GetPlayLength() < Ends[SourceIndex] || Source->GetSkeleton() != Skills[2].Animation->GetSkeleton()) { return false; }
		UAnimMontage* Montage = UAnimMontage::CreateSlotAnimationAsDynamicMontage(Source,
			TEXT("CountessFullBody"), Index == 0 ? 0.06f : 0.055f, 0.08f, 1.0f, 1);
		if (!Montage) { return false; }
		FAnimSegment& Segment = Montage->SlotAnimTracks[0].AnimTrack.AnimSegments[0];
		Segment.AnimStartTime = Starts[SourceIndex];
		Segment.AnimEndTime = Ends[SourceIndex];
		Segment.AnimPlayRate = (Ends[SourceIndex] - Starts[SourceIndex]) /
			(FlurryClipSeconds * FMath::Max(FMath::Abs(Source->RateScale), 0.001f));
		Montage->SetCompositeLength(FlurryClipSeconds);
		Montage->bEnableAutoBlendOut = false;
		FlurryMontages.Add(Montage);
	}
	return true;
}

bool UCountessSkillComponent::SpawnFlurryShadow()
{
	UMaterialInterface* DissolveMaterial = FlurryShadowDissolveMaterial.LoadSynchronous();
	if (!DissolveMaterial) { return false; }
	const FVector Forward = (CastTarget->GetActorLocation() - Character->GetActorLocation()).GetSafeNormal2D();
	float TargetRadius, TargetHalfHeight;
	CastTarget->GetSimpleCollisionCylinder(TargetRadius, TargetHalfHeight);
	const float Offset = FMath::Max(125.0f, Character->GetSimpleCollisionRadius() + TargetRadius + 30.0f);
	FVector Landing;
	// 분신도 기존 착지 검사를 사용해 벽 안이나 바닥 아래에 나타나지 않게 한다.
	const FVector Feet = CastTarget->GetActorLocation() - FVector(0.0f, 0.0f, TargetHalfHeight) + Forward * Offset;
	if (!FindLandingPoint(Feet, Landing)) { return false; }
	// 내비 투영으로 표적 옆이나 벽 너머로 밀린 위치도 반대편 배치로 인정하지 않는다.
	FCollisionQueryParams Query(SCENE_QUERY_STAT(CountessFlurryShadowSight), false, Character.Get());
	Query.AddIgnoredActor(CastTarget.Get());
	FHitResult Hit;
	if (FVector::DistSquared2D(Feet, Landing) > FMath::Square(35.0f) ||
		GetWorld()->LineTraceSingleByChannel(Hit, CastTarget->GetActorLocation(), Landing, ECC_Visibility, Query)) { return false; }
	AActor* Shadow = SpawnSkeletalProxy(FlurryRecoverySeconds + 0.2f, true);
	if (!Shadow) { return false; }
	FlurryShadow = Shadow;
	Shadow->Tags.Add(TEXT("CountessEFlurryShadow"));
	USkeletalMeshComponent* Mesh = Shadow->FindComponentByClass<USkeletalMeshComponent>();
	UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(DissolveMaterial, Shadow);
	Material->SetScalarParameterValue(TEXT("DissolveStart"), 1000000.0f);
	Material->SetScalarParameterValue(TEXT("DissolveDuration"), 0.45f);
	for (int32 Slot = 0; Slot < Mesh->GetNumMaterials(); ++Slot) { Mesh->SetMaterial(Slot, Material); }
	Mesh->SetBoundsScale(1.4f);
	const FTransform RelativeMesh = Character->GetMesh()->GetComponentTransform().GetRelativeTransform(Character->GetActorTransform());
	const FRotator Facing = (CastTarget->GetActorLocation() - Landing).GetSafeNormal2D().Rotation();
	Mesh->SetWorldTransform(RelativeMesh * FTransform(Facing, Landing));
	Mesh->PlayAnimation(FlurryMontages[1], false);
	Mesh->SetPlayRate(0.0f);
	Mesh->GetAnimInstance()->SetRootMotionMode(ERootMotionMode::IgnoreRootMotion);
	Mesh->TickAnimation(0.0f, false);
	Mesh->RefreshBoneTransforms();
	return true;
}

void UCountessSkillComponent::RetireFlurryShadow()
{
	if (FlurryShadow.IsValid())
	{
		AActor* Shadow = FlurryShadow.Get();
		Shadow->Tags.Remove(TEXT("CountessEFlurryShadow"));
		Shadow->Tags.Add(TEXT("CountessEShadowDissolving"));
		USkeletalMeshComponent* Mesh = Shadow->FindComponentByClass<USkeletalMeshComponent>();
		Mesh->SetPlayRate(0.0f);
		if (UMaterialInstanceDynamic* Material = Cast<UMaterialInstanceDynamic>(Mesh->GetMaterial(0)))
		{
			Material->SetScalarParameterValue(TEXT("DissolveStart"), GetWorld()->GetTimeSeconds());
		}
		// 공격 타이머와 잠금은 바로 끝낸다. 별도 판정 없는 외형만 짧게 흩어진다.
		Shadow->SetLifeSpan(0.5f);
	}
	FlurryShadow.Reset();
}

bool UCountessSkillComponent::ValidateFlurryTarget() const
{
	return Character.IsValid() && IsValidSkillTarget(CastTarget.Get(), Character.Get()) &&
		FVector::DistSquared2D(Character->GetActorLocation(), CastTarget->GetActorLocation()) <= FMath::Square(Skills[2].Range) &&
		FMath::Abs(Character->GetActorLocation().Z - CastTarget->GetActorLocation().Z) <= 180.0f && HasLineOfSight(CastTarget.Get());
}

void UCountessSkillComponent::PlayFlurryStrike(int32 Index)
{
	if (!bCasting || ActiveSkillIndex != 2 || !bEFlurryPrototype || !FlurryMontages.IsValidIndex(Index) ||
		!CastAnimInstance.IsValid() || !FlurryShadow.IsValid() || !ValidateFlurryTarget()) { FinishSkill(); return; }
	FlurryStrikeIndex = Index;
	Character->SetActorRotation((CastTarget->GetActorLocation() - Character->GetActorLocation()).GetSafeNormal2D().Rotation());
	if ((Index % 2) == 1)
	{
		USkeletalMeshComponent* Mesh = FlurryShadow->FindComponentByClass<USkeletalMeshComponent>();
		const FRotator Facing = (CastTarget->GetActorLocation() - Mesh->GetComponentLocation()).GetSafeNormal2D().Rotation();
		Mesh->SetWorldRotation((Facing.Quaternion() * Character->GetMesh()->GetRelativeRotation().Quaternion()).Rotator());
		Mesh->PlayAnimation(FlurryMontages[Index], false);
		Mesh->SetPlayRate(1.0f);
	}
	else if (Index > 0)
	{
		// 먼저 활성 포인터를 바꿔 이전 클립 종료 콜백이 새 베기를 중단하지 않게 한다.
		ActiveMontage = FlurryMontages[Index];
		if (CastAnimInstance->Montage_Play(ActiveMontage, 1.0f) <= 0.0f) { FinishSkill(); return; }
		FOnMontageEnded End; End.BindUObject(this, &UCountessSkillComponent::OnMontageEnded, CastGeneration);
		CastAnimInstance->Montage_SetEndDelegate(End, ActiveMontage);
		FOnMontageBlendingOutStarted Blend; Blend.BindUObject(this, &UCountessSkillComponent::OnMontageBlendingOut, CastGeneration);
		CastAnimInstance->Montage_SetBlendingOutDelegate(Blend, ActiveMontage);
	}
	// 현재 공격하는 한쪽의 실제 양검 소켓만 기록해, 교대 클립 사이의 넓은 연결 궤적을 막는다.
	StopWeaponTrails();
	StartWeaponTrails((Index % 2) ? FlurryShadow->FindComponentByClass<USkeletalMeshComponent>() : Character->GetMesh());
	PlaySkillSound(ESkillSound::QSlash, CastTarget->GetActorLocation(), Index >= 4 ? 0.5f : 0.3f);
	GetWorld()->GetTimerManager().SetTimer(ActionTimer, this, &UCountessSkillComponent::HitFlurryTarget,
		FMath::Max(0.01f, static_cast<float>(FlurryStartedAt + Index * FlurryStrikeSeconds + FlurryHitOffset - GetWorld()->GetTimeSeconds())), false);
	if (Index < 5)
	{
		GetWorld()->GetTimerManager().SetTimer(FlurryStrikeTimer,
			FTimerDelegate::CreateWeakLambda(this, [this, Index]() { PlayFlurryStrike(Index + 1); }),
			FMath::Max(0.01f, static_cast<float>(FlurryStartedAt + (Index + 1) * FlurryStrikeSeconds - GetWorld()->GetTimeSeconds())), false);
	}
}

void UCountessSkillComponent::HitFlurryTarget()
{
	if (!bCasting || ActiveSkillIndex != 2 || !bEFlurryPrototype || !FlurryShadow.IsValid() || !ValidateFlurryTarget()) { FinishSkill(); return; }
	bActionExecuted = true;
	AActor* Target = CastTarget.Get();
	DamageTarget(Target, Skills[2].Damage / 6.0f, nullptr);
	PlaySkillSound(ESkillSound::QHit, Target->GetActorLocation(), FlurryStrikeIndex == 5 ? 0.65f : 0.35f);
	SpawnFlurryTargetCuts(Target);
	if (AKwangTrainingDummy* Dummy = Cast<AKwangTrainingDummy>(Target))
	{
		Dummy->SetCombatStatus(*FString::Printf(TEXT("%s %d/6"), (FlurryStrikeIndex % 2) ? TEXT("SHADOW") : TEXT("BLADE"), FlurryStrikeIndex + 1), 0.18f);
	}
	if (!IsValidSkillTarget(Target, Character.Get())) { FinishSkill(); }
}

UParticleSystemComponent* UCountessSkillComponent::SpawnFlurryEffect(UParticleSystem* Effect,
	const FVector& Location, const FRotator& Rotation, float Scale, AActor* SourceActor, float Lifetime)
{
	FlurryEffects.RemoveAll([](const TWeakObjectPtr<UParticleSystemComponent>& Item) { return !Item.IsValid(); });
	if (FlurryEffects.Num() >= 16)
	{
		if (FlurryEffects[0].IsValid()) { FlurryEffects[0]->DestroyComponent(); }
		FlurryEffects.RemoveAt(0);
	}
	UParticleSystemComponent* Particle = SpawnOwnedEffect(Effect, Location, Rotation, Scale, SourceActor, Lifetime);
	if (Particle)
	{
		Particle->ComponentTags.Add(TEXT("CountessEAuthoredFX"));
		FlurryEffects.Add(Particle);
	}
	return Particle;
}

void UCountessSkillComponent::StopFlurryEffects()
{
	for (const TWeakObjectPtr<UParticleSystemComponent>& Particle : FlurryEffects)
	{
		if (Particle.IsValid()) { Particle->DestroyComponent(); }
	}
	FlurryEffects.Reset();
}

void UCountessSkillComponent::SpawnFlurryTargetCuts(AActor* Target)
{
	if (!IsValid(Target) || !Character.IsValid() || !FlurryShadow.IsValid()) { return; }
	AActor* Attacker = (FlurryStrikeIndex % 2) ? FlurryShadow.Get() : Character.Get();
	USkeletalMeshComponent* Mesh = Attacker->FindComponentByClass<USkeletalMeshComponent>();
	const FVector Center = Target->GetActorLocation() + FVector(0, 0, 8);
	const FVector Origin = Mesh ? Mesh->GetComponentLocation() : Attacker->GetActorLocation();
	FRotator Facing = (Center - Origin).GetSafeNormal2D().Rotation();
	const float Rolls[] = {-24.0f, 28.0f, 16.0f, -18.0f, -32.0f, 35.0f};
	const float Pitches[] = {-18.0f, 20.0f, 12.0f, -16.0f, -22.0f, 24.0f};
	Facing.Roll = Rolls[FlurryStrikeIndex];
	Facing.Pitch = Pitches[FlurryStrikeIndex];
	const FVector StrokeCenter = Center + (Origin - Center).GetSafeNormal2D() * 30.0f;
	const bool bFinisher = FlurryStrikeIndex == 5;
	// 원본 XSlash는 SM_Blink_XSlashMesh/B 두 입체 메시와 원본 잉크 재질을 함께 사용한다.
	// 카메라 평면을 키우는 대신 실제 공격 방향에서 짧게 교차하고, 마지막 타격만 한 번 파열한다.
	// 원본 particle lifetime=.40초다. .22초 컴포넌트 파괴로 전개를 자르지 않는다.
	if (UParticleSystemComponent* Slash = SpawnFlurryEffect(GetVisualEffect(EVisualEffect::BlinkSlash), StrokeCenter, Facing,
		bFinisher ? 1.22f : 1.05f, Attacker, .44f))
	{
		UMaterialInterface* Source = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
			TEXT("/Game/ParagonCountess/FX/Materials/Splines/M_Countess_Spline_XSlash_Inst.M_Countess_Spline_XSlash_Inst"))).LoadSynchronous();
		if (Source)
		{
			UMaterialInstanceDynamic* Ink = UMaterialInstanceDynamic::Create(Source, Slash);
			TArray<FMaterialParameterInfo> Parameters;
			TArray<FGuid> ParameterIds;
			Source->GetAllVectorParameterInfo(Parameters, ParameterIds);
			int32 AppliedColors = 0;
			for (const FMaterialParameterInfo& Parameter : Parameters)
			{
				const FString Name = Parameter.Name.ToString();
				FLinearColor Original = FLinearColor::Black;
				const bool bRead = Source->GetVectorParameterValue(Parameter, Original);
				if (FlurryStrikeIndex == 0)
				{
					UE_LOG(LogTemp, Display, TEXT("COUNTESS_E_AUTHORED vector_param=%s association=%d index=%d read=%d rgba=(%.4f,%.4f,%.4f,%.4f) source=%s"),
						*Name, static_cast<int32>(Parameter.Association), Parameter.Index, bRead,
						Original.R, Original.G, Original.B, Original.A, *Source->GetPathName());
				}
				if (!bRead || !Name.Contains(TEXT("Color"), ESearchCase::IgnoreCase)) { continue; }
				// 실제 노출 정보의 이름·association·index로 읽고 쓴다. 설명 문자열을 파라미터 이름으로 추정하지 않는다.
				const float Peak = FMath::Max(0.0f, FMath::Max3(Original.R, Original.G, Original.B));
				const float Red = 2.2f * Peak / (Peak + 7.0f) *
					FMath::Clamp(CVarCountessEInkGain.GetValueOnGameThread(), .005f, 1.0f);
				const FLinearColor Requested(Red, Red * .0068f, Red * .025f, Original.A);
				Ink->SetVectorParameterValueByInfo(Parameter, Requested);
				FLinearColor Resolved = FLinearColor::Black;
				const bool bApplied = Ink->GetVectorParameterValue(Parameter, Resolved) && Resolved.Equals(Requested, .0001f);
				if (bApplied) { ++AppliedColors; }
				else { UE_LOG(LogTemp, Warning, TEXT("COUNTESS_E_AUTHORED color_apply_failed=%s"), *Name); }
				if (FlurryStrikeIndex == 0)
				{
					UE_LOG(LogTemp, Display, TEXT("COUNTESS_E_AUTHORED source_color=%s rgba=(%.4f,%.4f,%.4f,%.4f) red=%.4f applied=%d"),
						*Name, Original.R, Original.G, Original.B, Original.A, Red, bApplied);
				}
			}
			if (AppliedColors == 0)
			{
				UE_LOG(LogTemp, Warning, TEXT("COUNTESS_E_AUTHORED no_valid_color_parameters source=%s vectors=%d"), *Source->GetPathName(), Parameters.Num());
			}
			// 원본 시스템의 두 메시 이미터에만 적용한다. 템플릿과 원본 MI는 바꾸지 않는다.
			Slash->SetMaterial(0, Ink);
			Slash->SetMaterial(1, Ink);
			if (FlurryStrikeIndex == 0)
			{
				for (int32 EmitterIndex = 0; EmitterIndex < Slash->EmitterInstances.Num(); ++EmitterIndex)
				{
					FParticleEmitterInstance* Instance = Slash->EmitterInstances[EmitterIndex];
					UParticleLODLevel* LOD = Instance && Instance->SpriteTemplate ? Instance->SpriteTemplate->GetCurrentLODLevel(Instance) : nullptr;
					if (!LOD || !Cast<UParticleModuleTypeDataMesh>(LOD->TypeDataModule)) { continue; }
					TArray<UMaterialInterface*, TInlineAllocator<2>> MeshMaterials;
					static_cast<FParticleMeshEmitterInstance*>(Instance)->GetMeshMaterials(MeshMaterials, LOD);
					for (UMaterialInterface* MeshMaterial : MeshMaterials)
					{
						UE_LOG(LogTemp, Display, TEXT("COUNTESS_E_AUTHORED resolved_mesh_material emitter=%d material=%s expected_mid=%d"),
							EmitterIndex, *GetPathNameSafe(MeshMaterial), MeshMaterial == Ink);
					}
				}
			}
		}
		else
		{
			UE_LOG(LogTemp, Warning, TEXT("COUNTESS_E_AUTHORED source_material_load_failed"));
		}
	}
	SpawnFlurryEffect(Skills[0].ImpactEffect, Center, Facing, bFinisher ? .30f : .20f,
		Attacker, bFinisher ? .18f : .14f);
	if (bFinisher)
	{
		SpawnFlurryEffect(GetVisualEffect(EVisualEffect::FeastImpact), Center, Facing, .34f, Attacker, .28f);
		float Radius, HalfHeight;
		Target->GetSimpleCollisionCylinder(Radius, HalfHeight);
		SpawnFlurryEffect(GetVisualEffect(EVisualEffect::FeastGround), Target->GetActorLocation() - FVector(0, 0, HalfHeight - 5.0f),
			FRotator(0, Facing.Yaw, 0), .32f, Attacker, .28f);
	}
	UE_LOG(LogTemp, Display, TEXT("COUNTESS_E_AUTHORED hit=%d side=%s mesh_slash=1 finisher=%d"),
		FlurryStrikeIndex + 1, (FlurryStrikeIndex % 2) ? TEXT("shadow") : TEXT("body"), bFinisher);
}

const FCountessSkillDefinition* UCountessSkillComponent::GetDefinition(ECountessSkill Skill) const
{
	const int32 Index = static_cast<int32>(Skill);
	return Skills.IsValidIndex(Index) ? &Skills[Index] : nullptr;
}

float UCountessSkillComponent::GetSkillPlayRate(ECountessSkill Skill) const
{
	if (Skill == ECountessSkill::Feast) { return FeastInstantPlayRate; }
	return Skill == ECountessSkill::BladeSiphon ?
		FMath::Clamp(CVarCountessWPlayRate.GetValueOnGameThread(), 0.5f, 2.0f) :
		1.0f;
}

float UCountessSkillComponent::GetSkillStartTime(ECountessSkill Skill) const
{
	return Skill == ECountessSkill::Feast ? FeastInstantStartTime : 0.0f;
}

float UCountessSkillComponent::GetCooldownRemaining(ECountessSkill Skill) const
{
	if (IgnoresCooldowns())
	{
		return 0.0f;
	}
	const int32 Index = static_cast<int32>(Skill);
	if (Index >= 1 && Index <= 3)
	{
		return GetSlotCooldownRemaining(Index == 1 ? 16 : Index);
	}
	return Index >= 0 && Index < 4 && GetWorld() ?
		static_cast<float>(FMath::Max(0.0, NextSkillTimes[Index] - GetWorld()->GetTimeSeconds())) : 0.0f;
}

bool UCountessSkillComponent::IgnoresCooldowns() const
{
	return CVarCountessIgnoreCooldowns.GetValueOnGameThread() != 0;
}

float UCountessSkillComponent::GetReturnRemaining() const
{
	return GetWorld() ? static_cast<float>(FMath::Max(0.0, ReturnDeadline - GetWorld()->GetTimeSeconds())) : 0.0f;
}

FString UCountessSkillComponent::GetInputFeedback() const
{
	return GetWorld() && GetWorld()->GetTimeSeconds() < FeedbackDeadline ? Feedback : FString();
}

bool UCountessSkillComponent::RejectInput(const TCHAR* Reason)
{
	Feedback = Reason;
	FeedbackDeadline = GetWorld() ? GetWorld()->GetTimeSeconds() + 1.0 : 0.0;
	return false;
}

bool UCountessSkillComponent::IsValidSkillTarget(const AActor* Target, const AActor* Caster)
{
	if (!IsValid(Target) || Target == Caster || !Target->CanBeDamaged())
	{
		return false;
	}
	if (const AKwangTrainingDummy* Dummy = Cast<AKwangTrainingDummy>(Target))
	{
		return Dummy->IsAlive();
	}
	return Target->IsA<APawn>();
}

bool UCountessSkillComponent::HasLineOfSight(AActor* Target) const
{
	if (!Character.IsValid() || !IsValid(Target))
	{
		return false;
	}
	FCollisionQueryParams Query(SCENE_QUERY_STAT(CountessSkillSight), false, Character.Get());
	Query.AddIgnoredActor(Target);
	FHitResult Hit;
	return !GetWorld()->LineTraceSingleByChannel(Hit, Character->GetActorLocation(),
		Target->GetActorLocation(), ECC_Visibility, Query);
}

FVector UCountessSkillComponent::GetFeetLocation() const
{
	return Character->GetActorLocation() - FVector(0.0f, 0.0f, Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
}

bool UCountessSkillComponent::FindLandingPoint(const FVector& FeetLocation, FVector& Result) const
{
	if (!Character.IsValid())
	{
		return false;
	}
	UNavigationSystemV1* Navigation = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
	FNavLocation NavPoint;
	if (!Navigation || !Navigation->ProjectPointToNavigation(FeetLocation, NavPoint,
		FVector(45.0f, 45.0f, 160.0f), &Character->GetNavAgentPropertiesRef()))
	{
		return false;
	}
	const UCapsuleComponent* Capsule = Character->GetCapsuleComponent();
	Result = NavPoint.Location + FVector(0.0f, 0.0f, Capsule->GetScaledCapsuleHalfHeight() + 2.0f);
	FCollisionQueryParams Query(SCENE_QUERY_STAT(CountessSkillLanding), false, Character.Get());
	return !GetWorld()->OverlapBlockingTestByChannel(Result, FQuat::Identity, ECC_Pawn,
		FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(), Capsule->GetScaledCapsuleHalfHeight() - 1.0f), Query);
}

bool UCountessSkillComponent::FindTargetLanding(AActor* Target, FVector& Result) const
{
	if (!Character.IsValid() || !IsValid(Target))
	{
		return false;
	}
	const float Offset = Character->GetSimpleCollisionRadius() + Target->GetSimpleCollisionRadius() + 30.0f;
	FVector Direction = (Character->GetActorLocation() - Target->GetActorLocation()).GetSafeNormal2D();
	if (Direction.IsNearlyZero())
	{
		Direction = -Character->GetActorForwardVector();
	}
	FVector Feet = Target->GetActorLocation();
	float TargetRadius, TargetHalfHeight;
	Target->GetSimpleCollisionCylinder(TargetRadius, TargetHalfHeight);
	Feet.Z -= TargetHalfHeight;
	for (int32 Attempt = 0; Attempt < 8; ++Attempt)
	{
		const float Angle = (Attempt % 2 == 0 ? 1.0f : -1.0f) * ((Attempt + 1) / 2) * 45.0f;
		if (FindLandingPoint(Feet + Direction.RotateAngleAxis(Angle, FVector::UpVector) * Offset, Result))
		{
			return true;
		}
	}
	return false;
}

bool UCountessSkillComponent::TryUseSkill(ECountessSkill Skill, const FVector& AimLocation, AActor* Target)
{
	const int32 Index = static_cast<int32>(Skill);
	if (Index > 0) { return TryUseReforgeSkill(Index, AimLocation); }
	if (!bEnabled || !Character.IsValid() || !Skills.IsValidIndex(Index) ||
		Character->GetCharacterMovement()->MovementMode != MOVE_Walking)
	{
		return RejectInput(TEXT("Unavailable"));
	}
	if (IsCasting())
	{
		return RejectInput(TEXT("Casting"));
	}
	if (Skill == ECountessSkill::ShadowSlip && GetReturnRemaining() > 0.0f)
	{
		return TryReturn();
	}
	if (GetCooldownRemaining(Skill) > 0.0f)
	{
		return RejectInput(TEXT("Cooldown"));
	}
	if (Skill == ECountessSkill::ShadowSlip || Skill == ECountessSkill::Feast || (bEFlurryPrototype && Index == 2))
	{
		if (!IsValidSkillTarget(Target, Character.Get()))
		{
			return RejectInput(TEXT("Aim at an enemy"));
		}
		const FVector Delta = Target->GetActorLocation() - Character->GetActorLocation();
		if (Delta.SizeSquared2D() > FMath::Square(Skills[Index].Range) || FMath::Abs(Delta.Z) > 180.0f)
		{
			return RejectInput(TEXT("Out of range"));
		}
		if (bEFlurryPrototype && Index == 2)
		{
			if (!HasLineOfSight(Target)) { return RejectInput(TEXT("Blocked")); }
			return BeginSkill(Index, AimLocation, Target, false);
		}
		FVector Landing;
		if (!HasLineOfSight(Target) || !FindTargetLanding(Target, Landing))
		{
			return RejectInput(TEXT("Blocked"));
		}
	}
	return BeginSkill(Index, AimLocation, Target, false);
}

bool UCountessSkillComponent::TryReturn()
{
	FVector Landing;
	const FVector Feet = ReturnLocation - FVector(0.0f, 0.0f, Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
	if (!FindLandingPoint(Feet, Landing))
	{
		return RejectInput(TEXT("Return blocked"));
	}
	return BeginSkill(0, Landing, nullptr, true);
}

bool UCountessSkillComponent::BeginSkill(int32 SkillIndex, const FVector& AimLocation, AActor* Target, bool bReturn)
{
	UAnimInstance* AnimInstance = Character->GetMesh()->GetAnimInstance();
	if (!AnimInstance || !SkillMontages.IsValidIndex(SkillIndex))
	{
		return RejectInput(TEXT("Unavailable"));
	}
	FVector InstantFeastLanding = FVector::ZeroVector;
	if (SkillIndex == 3 && !FindFeastLanding(Target, InstantFeastLanding)) { return RejectInput(TEXT("Blocked")); }
	Character->InterruptIntroAnimation();
	Character->CancelBasicAttackForSkill();
	CastAnimInstance = AnimInstance;
	SavedRootMotionMode = AnimInstance->RootMotionMode;
	bSavedOrientRotation = Character->GetCharacterMovement()->bOrientRotationToMovement;
	AnimInstance->SetRootMotionMode(ERootMotionMode::IgnoreRootMotion);
	Character->GetCharacterMovement()->bOrientRotationToMovement = false;
	if (Character->GetController())
	{
		Character->GetController()->StopMovement();
	}
	Character->GetCharacterMovement()->StopMovementImmediately();
	const FVector Direction = (AimLocation - Character->GetActorLocation()).GetSafeNormal2D();
	if (!Direction.IsNearlyZero())
	{
		Character->SetActorRotation(Direction.Rotation());
	}
	bCasting = true;
	bReturning = bReturn;
	bDetailedCast = UsesDetailedPresentation();
	bWShadowPreview = SkillIndex == 1 && bDetailedCast && CVarCountessWPreview.GetValueOnGameThread() != 0;
	bActionExecuted = false;
	ActiveSkillIndex = SkillIndex;
	CastOrigin = Character->GetActorLocation();
	CastAim = AimLocation;
	CastTarget = Target;
	ActivePlayRate = GetSkillPlayRate(static_cast<ECountessSkill>(SkillIndex));
	ActiveStartTime = GetSkillStartTime(static_cast<ECountessSkill>(SkillIndex));
	ActiveMontage = SkillMontages[SkillIndex];
	++CastGeneration;
	const bool bFlurryCast = bEFlurryPrototype && SkillIndex == 2;
	const float MontageDuration = AnimInstance->Montage_Play(ActiveMontage, ActivePlayRate, EMontagePlayReturnType::Duration, ActiveStartTime) -
		ActiveStartTime / ActivePlayRate;
	const float Duration = bFlurryCast ? FlurryRecoverySeconds : MontageDuration;
	if (MontageDuration <= 0.0f)
	{
		FinishSkill();
		return RejectInput(TEXT("Unavailable"));
	}
	if (bFlurryCast && !SpawnFlurryShadow())
	{
		FinishSkill();
		return RejectInput(TEXT("Shadow blocked"));
	}
	if (SkillIndex == 3)
	{
		const FRotator Facing = (Target->GetActorLocation() - InstantFeastLanding).GetSafeNormal2D().Rotation();
		const bool bAlreadyThere = Character->GetActorLocation().Equals(InstantFeastLanding, .1f);
		if (!bAlreadyThere && !Character->TeleportTo(InstantFeastLanding, Facing, false, false))
		{
			FinishSkill();
			return RejectInput(TEXT("Blocked"));
		}
		Character->SetActorRotation(Facing);
		bFeastApproaching = false;
		bFeastArrived = true;
		FeastApproachStartedAt = GetWorld()->GetTimeSeconds();
		const FVector FloorOffset(0, 0, Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
		CastBoundEffects.Add(SpawnOwnedEffect(GetVisualEffect(EVisualEffect::BlinkFlash), CastOrigin - FloorOffset,
			Facing, .45f, nullptr, .24f));
		CastBoundEffects.Add(SpawnOwnedEffect(GetVisualEffect(EVisualEffect::BlinkFlash), GetFeetLocation(),
			Facing, .60f, nullptr, .30f));
		UE_LOG(LogTemp, Display, TEXT("COUNTESS_FAST_R teleported=1 distance=%.1f start=%.2f rate=%.2f hit_after=%.3f recovery_after=%.3f"),
			FVector::Dist2D(CastOrigin, Character->GetActorLocation()), ActiveStartTime, ActivePlayRate,
			(Skills[3].ActionTime - ActiveStartTime) / ActivePlayRate, (Skills[3].RecoveryTime - ActiveStartTime) / ActivePlayRate);
	}
	if (!bReturn)
	{
		NextSkillTimes[SkillIndex] = GetWorld()->GetTimeSeconds() + Skills[SkillIndex].Cooldown;
	}
	Feedback.Reset();
	FOnMontageEnded EndDelegate;
	EndDelegate.BindUObject(this, &UCountessSkillComponent::OnMontageEnded, CastGeneration);
	AnimInstance->Montage_SetEndDelegate(EndDelegate, ActiveMontage);
	FOnMontageBlendingOutStarted BlendDelegate;
	BlendDelegate.BindUObject(this, &UCountessSkillComponent::OnMontageBlendingOut, CastGeneration);
	AnimInstance->Montage_SetBlendingOutDelegate(BlendDelegate, ActiveMontage);
	if (bFlurryCast)
	{
		FlurryStartedAt = GetWorld()->GetTimeSeconds();
		PlayFlurryStrike(0);
	}
	else
	{
		GetWorld()->GetTimerManager().SetTimer(ActionTimer, this, &UCountessSkillComponent::ExecuteAction,
			FMath::Min(FMath::Max(0.01f, (Skills[SkillIndex].ActionTime - ActiveStartTime) / ActivePlayRate), Duration * 0.9f), false);
	}
	GetWorld()->GetTimerManager().SetTimer(RecoveryTimer, this, &UCountessSkillComponent::FinishSkill,
		FMath::Min(FMath::Max(0.01f, (Skills[SkillIndex].RecoveryTime - ActiveStartTime) / ActivePlayRate), Duration), false);
	if (SkillIndex == 3)
	{
		// 순간 접근 뒤 스턴·명중·복귀를 모두 같은 원본 몽타주 시작점/배속으로 환산한다.
		GetWorld()->GetTimerManager().SetTimer(StunStartTimer, this, &UCountessSkillComponent::StartFeastStun,
			FMath::Max(0.01f, (Skills[SkillIndex].ActionTime - 0.75f - ActiveStartTime) / ActivePlayRate), false);
	}
	StartSkillVisuals();
	SetComponentTickEnabled(true);
	UE_LOG(LogTemp, Display, TEXT("Countess skill start: %s return=%d"), *Skills[SkillIndex].Name.ToString(), bReturn);
	return true;
}

UParticleSystemComponent* UCountessSkillComponent::SpawnEffect(UWorld* World, UParticleSystem* Effect,
	const FVector& Location, const FRotator& Rotation, float Scale, AActor* SourceActor,
	float Lifetime, bool bAttachToSource)
{
	if (!World || !Effect)
	{
		return nullptr;
	}
	UParticleSystemComponent* Particle = UGameplayStatics::SpawnEmitterAtLocation(World, Effect,
		Location, Rotation, FVector(Scale), true, EPSCPoolMethod::None, false);
	if (Particle)
	{
		Particle->ComponentTags.Add(TEXT("CountessSkillFX"));
		// 원본 3인칭용 거리 LOD가 쿼터뷰 카메라에서 시전·베기 에미터를 끄지 않도록 인스턴스만 고정한다.
		Particle->bOverrideLODMethod = true;
		Particle->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
		Particle->SetLODLevel(0);
		if (IsValid(SourceActor))
		{
			Particle->SetActorParameter(TEXT("BoneSocketActor"), SourceActor);
			if (bAttachToSource)
			{
				if (USkeletalMeshComponent* Mesh = SourceActor->FindComponentByClass<USkeletalMeshComponent>())
				{
					Particle->AttachToComponent(Mesh, FAttachmentTransformRules::KeepWorldTransform);
				}
			}
		}
		Particle->ActivateSystem(true);
		// 최초 활성화는 원본 템플릿의 거리 LOD를 다시 선택하므로 활성화 후에도 상세 단계로 확정한다.
		Particle->SetLODLevel(0);
		// 원본 FX에 루프 에미터가 있어도 시전 잔상이 월드에 무한히 남지 않는다.
		FTimerHandle Cleanup;
		World->GetTimerManager().SetTimer(Cleanup, FTimerDelegate::CreateWeakLambda(Particle, [Particle]()
		{
			Particle->DestroyComponent();
		}), FMath::Max(0.05f, Lifetime), false);
	}
	return Particle;
}

UParticleSystem* UCountessSkillComponent::GetVisualEffect(EVisualEffect Effect) const
{
	const int32 Index = static_cast<int32>(Effect);
	return VisualEffects.IsValidIndex(Index) ? VisualEffects[Index] : nullptr;
}

UParticleSystemComponent* UCountessSkillComponent::SpawnOwnedEffect(UParticleSystem* Effect,
	const FVector& Location, const FRotator& Rotation, float Scale, AActor* SourceActor,
	float Lifetime, bool bAttachToSource)
{
	UParticleSystemComponent* Particle = SpawnEffect(GetWorld(), Effect, Location, Rotation,
		Scale, SourceActor, Lifetime, bAttachToSource);
	OwnedEffects.RemoveAll([](const TWeakObjectPtr<UParticleSystemComponent>& Item) { return !Item.IsValid(); });
	if (Particle)
	{
		OwnedEffects.Add(Particle);
	}
	return Particle;
}

void UCountessSkillComponent::ScheduleVisualCue(float Delay, EVisualCue Cue)
{
	const uint32 Generation = CastGeneration;
	FTimerHandle Handle;
	GetWorld()->GetTimerManager().SetTimer(Handle, FTimerDelegate::CreateWeakLambda(this, [this, Generation, Cue]()
	{
		if (bCasting && Generation == CastGeneration && Character.IsValid())
		{
			PlayVisualCue(Cue);
		}
	}), FMath::Max(0.01f, (Delay - ActiveStartTime) / ActivePlayRate), false);
	VisualTimers.Add(Handle);
}

void UCountessSkillComponent::StartSkillVisuals()
{
	if (bEFlurryPrototype && ActiveSkillIndex == 2)
	{
		if (FlurryShadow.IsValid())
		{
			if (USkeletalMeshComponent* Mesh = FlurryShadow->FindComponentByClass<USkeletalMeshComponent>())
			{
				const FVector Feet = Mesh->GetComponentLocation();
				SpawnFlurryEffect(GetVisualEffect(EVisualEffect::CloneBurst), Feet, Character->GetActorRotation(), .80f, FlurryShadow.Get(), .42f);
			}
		}
		UE_LOG(LogTemp, Display, TEXT("COUNTESS_E_AUTHORED begin body=3 shadow=3 original_fx=1"));
		return;
	}
	if (CastAudio.IsValid())
	{
		CastAudio->Stop();
	}
	if (UsesSkillVoice() && Skills[ActiveSkillIndex].CastSound && !bReturning)
	{
		CastAudio = UGameplayStatics::SpawnSoundAttached(Skills[ActiveSkillIndex].CastSound,
			Character->GetMesh(), NAME_None, FVector::ZeroVector, EAttachLocation::KeepRelativeOffset, true, 0.6f);
	}
	if (bDetailedCast && ActiveSkillIndex == 0)
	{
		if (UsesQRushAudio())
		{
			PlaySkillSound(ESkillSound::QRush, Character->GetActorLocation(), bReturning ? 0.6f : 0.8f, true);
		}
		SpawnLensEffect(bReturning ? EVisualEffect::BlinkLensReturn : EVisualEffect::BlinkLensStart, 0.5f);
		if (!bReturning)
		{
			CastBoundEffects.Add(SpawnOwnedEffect(GetVisualEffect(EVisualEffect::BlinkAim), GetFeetLocation(),
				Character->GetActorRotation(), 1.0f, Character.Get(), 0.5f, true));
		}
	}
	if (bDetailedCast && ActiveSkillIndex == 2)
	{
		FRotator EffectRotation = Character->GetActorRotation();
		EffectRotation.Yaw -= 90.0f;
		CastBoundEffects.Add(SpawnOwnedEffect(GetVisualEffect(EVisualEffect::TideAim), GetFeetLocation(),
			EffectRotation, 1.0f, Character.Get(), 0.45f));
	}
	if (ActiveSkillIndex == 0 && !bReturning)
	{
		if (bDetailedCast && CVarCountessQPresentation.GetValueOnGameThread() >= 2)
		{
			ScheduleVisualCue(0.10f, EVisualCue::QDualSweep);
		}
		ScheduleVisualCue(0.22f, EVisualCue::StartTrails);
		ScheduleVisualCue(0.48f, EVisualCue::EndTrails);
	}
	else if (ActiveSkillIndex == 1)
	{
		ScheduleVisualCue(0.12f, EVisualCue::StartTrails);
		ScheduleVisualCue(0.30f, EVisualCue::BladeSpin);
		if (bWShadowPreview)
		{
			ScheduleVisualCue(0.48f, EVisualCue::BladeEcho);
			ScheduleVisualCue(0.64f, EVisualCue::BladeEcho);
		}
		ScheduleVisualCue(0.72f, EVisualCue::EndTrails);
	}
	else if (ActiveSkillIndex == 2)
	{
		ScheduleVisualCue(0.18f, EVisualCue::TideGround);
	}
	else if (ActiveSkillIndex == 3)
	{
		if (bDetailedCast)
		{
			PlaySkillSound(ESkillSound::FeastCharge, Character->GetActorLocation(), 0.6f);
			ScheduleVisualCue(Skills[3].ActionTime, EVisualCue::FeastSlash);
		}
		// 준비 구간을 생략하는 궁극기에서도 아래 큐는 ActiveStartTime 기준으로 즉시 시작한다.
		ScheduleVisualCue(0.85f, EVisualCue::FeastCast);
		USkeletalMeshComponent* Mesh = Character->GetMesh();
		UParticleSystemComponent* Eyes = SpawnOwnedEffect(GetVisualEffect(EVisualEffect::FeastEyes),
			Mesh->GetSocketLocation(TEXT("Eyes_Position")), Mesh->GetSocketRotation(TEXT("Eyes_Position")),
			1.0f, Character.Get(), 1.9f / ActivePlayRate);
		if (Eyes && Mesh->DoesSocketExist(TEXT("Eyes_Position")))
		{
			Eyes->AttachToComponent(Mesh, FAttachmentTransformRules::SnapToTargetNotIncludingScale, TEXT("Eyes_Position"));
		}
		CastBoundEffects.Add(Eyes);
		if (IsValid(CastTarget.Get()))
		{
			float Radius, HalfHeight;
			CastTarget->GetSimpleCollisionCylinder(Radius, HalfHeight);
			CastBoundEffects.Add(SpawnOwnedEffect(GetVisualEffect(EVisualEffect::FeastTarget),
				CastTarget->GetActorLocation() - FVector(0, 0, HalfHeight), Character->GetActorRotation(),
				1.0f, CastTarget.Get(), 1.8f / ActivePlayRate, true));
		}
		ScheduleVisualCue(0.95f, EVisualCue::StartTrails);
		ScheduleVisualCue(2.05f, EVisualCue::EndTrails);
	}
}

void UCountessSkillComponent::PlayVisualCue(EVisualCue Cue)
{
	if (Cue == EVisualCue::QDualSweep)
	{
		SpawnBlinkDualSweep(false);
	}
	else if (Cue == EVisualCue::StartTrails)
	{
		StartWeaponTrails();
	}
	else if (Cue == EVisualCue::EndTrails)
	{
		StopWeaponTrails();
	}
	else if (Cue == EVisualCue::BladeSpin)
	{
		if (bDetailedCast)
		{
			PlaySkillSound(ESkillSound::Blade, Character->GetActorLocation());
		}
		if (bWShadowPreview)
		{
			// 미리보기에서는 연기를 몸 가까이에 두고 실제 검 궤적과 짧은 잔상을 앞세운다.
			if (UParticleSystemComponent* NearSmoke = SpawnOwnedEffect(Skills[1].CastEffect,
				GetFeetLocation(), Character->GetActorRotation(), 0.50f, Character.Get(), 0.36f / ActivePlayRate))
			{
				NearSmoke->CustomTimeDilation = ActivePlayRate;
				NearSmoke->ComponentTags.Add(TEXT("CountessWPreviewNearSmoke"));
				CastBoundEffects.Add(NearSmoke);
			}
			SpawnBladeShadowEcho();
			return;
		}
		const bool bDenseW = bDetailedCast && CVarCountessWPresentation.GetValueOnGameThread() != 0;
		UParticleSystem* RingEffect = bDenseW && DetailedSiphonRing ? DetailedSiphonRing.Get() : Skills[1].CastEffect.Get();
		if (bDenseW && CVarCountessWPresentation.GetValueOnGameThread() >= 2 && RimSiphonRing)
		{
			RingEffect = RimSiphonRing.Get();
		}
		if (bDenseW && CVarCountessWPresentation.GetValueOnGameThread() >= 3 && SpiralSiphonRing)
		{
			RingEffect = SpiralSiphonRing.Get();
			if (!LoadedLightSiphonRing)
			{
				LoadedLightSiphonRing = LightSiphonRing.LoadSynchronous();
			}
			if (LoadedLightSiphonRing)
			{
				RingEffect = LoadedLightSiphonRing.Get();
			}
		}
		UParticleSystemComponent* Ring = SpawnOwnedEffect(RingEffect, GetFeetLocation(), Character->GetActorRotation(), 1.0f);
		UParticleSystemComponent* Trails = SpawnOwnedEffect(bDenseW && DetailedSiphonTrails ?
			DetailedSiphonTrails.Get() : SiphonTrails.Get(), GetFeetLocation(), Character->GetActorRotation());
		for (UParticleSystemComponent* Particle : {Ring, Trails})
		{
			if (Particle)
			{
				Particle->CustomTimeDilation = (bDenseW ? 0.85f : 1.0f) * ActivePlayRate;
				if (bDenseW)
				{
					// 원본 소용돌이의 재질과 움직임을 보존하고 입자 밀도와 잔상의 겹침만 강화한다.
					Particle->ComponentTags.Add(TEXT("CountessWTexturedVortex"));
					CastBoundEffects.Add(Particle);
				}
			}
		}
	}
	else if (Cue == EVisualCue::BladeEcho)
	{
		SpawnBladeShadowEcho();
	}
	else if (Cue == EVisualCue::TideGround)
	{
		SpawnOwnedEffect(GetVisualEffect(EVisualEffect::TideGround), GetFeetLocation(), Character->GetActorRotation());
	}
	else if (Cue == EVisualCue::FeastCast)
	{
		CastBoundEffects.Add(SpawnOwnedEffect(Skills[3].CastEffect, GetFeetLocation(),
			Character->GetActorRotation(), 1.0f, Character.Get(), 1.1f, true));
		if (bDetailedCast)
		{
			USkeletalMeshComponent* Mesh = Character->GetMesh();
			if (UParticleSystemComponent* Eyes = SpawnOwnedEffect(GetVisualEffect(EVisualEffect::FeastEyeBurst),
				Mesh->GetSocketLocation(TEXT("Eyes_Position")), Mesh->GetSocketRotation(TEXT("Eyes_Position")),
				1.0f, Character.Get(), 0.7f))
			{
				Eyes->AttachToComponent(Mesh, FAttachmentTransformRules::SnapToTargetNotIncludingScale, TEXT("Eyes_Position"));
			}
		}
	}
	else if (Cue == EVisualCue::FeastSlash)
	{
		SpawnOwnedEffect(GetVisualEffect(EVisualEffect::FeastSlash), GetFeetLocation(), Character->GetActorRotation());
		PlaySkillSound(ESkillSound::Blade, Character->GetActorLocation(), 0.55f);
	}
}

void UCountessSkillComponent::SpawnBladeShadowEcho()
{
	if (!bCasting || !bWShadowPreview || ActiveSkillIndex != 1 || !Character.IsValid())
	{
		return;
	}
	// 외곽은 지속된 원이 아니라 시전 동작에 맞춘 세 번의 짧은 원본 잔상이다.
	if (UParticleSystemComponent* Echo = SpawnOwnedEffect(SiphonTrails,
		GetFeetLocation(), Character->GetActorRotation(), 0.90f, Character.Get(), 0.15f / ActivePlayRate))
	{
		Echo->CustomTimeDilation = ActivePlayRate;
		Echo->ComponentTags.Add(TEXT("CountessWPreviewOuterEcho"));
		CastBoundEffects.Add(Echo);
	}
	USkeletalMeshComponent* Mesh = Character->GetMesh();
	for (const TCHAR* Side : {TEXT("L"), TEXT("R")})
	{
		const FName Base(*FString::Printf(TEXT("FX_WeaponBase_%s"), Side));
		if (!Mesh->DoesSocketExist(Base))
		{
			continue;
		}
		if (UParticleSystemComponent* Shadow = SpawnOwnedEffect(GetVisualEffect(EVisualEffect::SmokeyBlade),
			Mesh->GetSocketLocation(Base), Mesh->GetSocketRotation(Base), 0.80f, Character.Get(), 0.18f / ActivePlayRate))
		{
			Shadow->CustomTimeDilation = ActivePlayRate;
			Shadow->AttachToComponent(Mesh, FAttachmentTransformRules::SnapToTargetNotIncludingScale, Base);
			Shadow->ComponentTags.Add(TEXT("CountessWPreviewBladeShadow"));
			CastBoundEffects.Add(Shadow);
		}
	}
}

void UCountessSkillComponent::PlaySkillSound(ESkillSound Sound, const FVector& Location, float Volume, bool bFollowCharacter)
{
	const int32 Index = static_cast<int32>(Sound);
	if (UsesSkillAudio() && bDetailedCast && CombatSounds.IsValidIndex(Index) && CombatSounds[Index])
	{
		EffectAudio.RemoveAll([](const TWeakObjectPtr<UAudioComponent>& Item) { return !Item.IsValid(); });
		UAudioComponent* Audio = bFollowCharacter && Character.IsValid() ?
			UGameplayStatics::SpawnSoundAttached(CombatSounds[Index], Character->GetMesh(), NAME_None,
				FVector::ZeroVector, EAttachLocation::KeepRelativeOffset, true, Volume) :
			UGameplayStatics::SpawnSoundAtLocation(GetWorld(), CombatSounds[Index], Location, FRotator::ZeroRotator, Volume);
		if (Audio)
		{
			Audio->ComponentTags.Add(TEXT("CountessSkillSFX"));
			if (bFollowCharacter)
			{
				Audio->ComponentTags.Add(TEXT("CountessSkillMovementSFX"));
			}
			EffectAudio.Add(Audio);
		}
	}
}

ACountessSkillLensEffect* UCountessSkillComponent::SpawnLensEffect(EVisualEffect Effect, float Lifetime)
{
	APlayerController* Controller = Character.IsValid() ? Cast<APlayerController>(Character->GetController()) : nullptr;
	if (!Controller || !Controller->IsLocalController() || !Controller->PlayerCameraManager || !GetVisualEffect(Effect))
	{
		return nullptr;
	}
	const TScriptInterface<ICameraLensEffectInterface> Lens = Controller->PlayerCameraManager->AddGenericCameraLensEffect(ACountessSkillLensEffect::StaticClass());
	ACountessSkillLensEffect* Actor = Cast<ACountessSkillLensEffect>(Lens.GetObject());
	if (Actor)
	{
		Actor->Initialize(GetVisualEffect(Effect), Lifetime);
		LensEffects.RemoveAll([](const TWeakObjectPtr<ACountessSkillLensEffect>& Item) { return !Item.IsValid(); });
		LensEffects.Add(Actor);
	}
	return Actor;
}

void UCountessSkillComponent::StartWeaponTrails(USkeletalMeshComponent* TargetMesh)
{
	USkeletalMeshComponent* Mesh = TargetMesh ? TargetMesh : Character->GetMesh();
	const bool bFlurry = bEFlurryPrototype && ActiveSkillIndex == 2;
	const bool bPreciseBlink = ActiveSkillIndex == 0;
	UMaterialInterface* BladeMaterial = (bFlurry || bPreciseBlink) ? FlurryBladeMaterial.LoadSynchronous() : nullptr;
	UParticleSystem* BladeEffect = (bFlurry || bPreciseBlink) ? FlurryBladeEffect.LoadSynchronous() : nullptr;
	for (const TCHAR* Side : {TEXT("L"), TEXT("R")})
	{
		const FName Base(*FString::Printf(TEXT("FX_WeaponBase_%s"), Side));
		const FName Tip(*FString::Printf(TEXT("FX_WeaponTip_%s"), Side));
		if (!Mesh->DoesSocketExist(Base) || !Mesh->DoesSocketExist(Tip))
		{
			continue;
		}
		UParticleSystemComponent* Trail = SpawnOwnedEffect(BladeEffect ? BladeEffect : GetVisualEffect(EVisualEffect::MeleeTrail),
			Mesh->GetComponentLocation(), Mesh->GetComponentRotation(), 1.0f, Mesh->GetOwner(), bFlurry ? .34f : 2.5f, true);
		if (Trail)
		{
			Trail->ComponentTags.Add(TEXT("CountessSkillWeaponTrail"));
			if (bPreciseBlink)
			{
				Trail->SetAbsolute(false, false, false);
				Trail->SetRelativeLocationAndRotation(FVector::ZeroVector, FRotator::ZeroRotator);
				Trail->SetRelativeScale3D(FVector::OneVector);
			}
			if (bFlurry)
			{
				Trail->SetAbsolute(false, false, false);
				Trail->SetRelativeLocationAndRotation(FVector::ZeroVector, FRotator::ZeroRotator);
				Trail->SetRelativeScale3D(FVector::OneVector);
				Trail->ComponentTags.Add(TEXT("CountessEAuthoredFX"));
				FlurryEffects.RemoveAll([](const TWeakObjectPtr<UParticleSystemComponent>& Item) { return !Item.IsValid(); });
				FlurryEffects.Add(Trail);
			}
			if (BladeMaterial) { Trail->SetMaterial(0, BladeMaterial); }
			Trail->BeginTrails(Base, Tip, ETrailWidthMode_FromCentre, bFlurry ? 0.55f : (bPreciseBlink ? .48f : 1.0f));
			if (bFlurry) { Trail->ComponentTags.Add(TEXT("CountessFlurryWideTrail")); }
			if (ActiveSkillIndex == 1)
			{
				Trail->CustomTimeDilation = ActivePlayRate;
			}
			if (bDetailedCast)
			{
				// BeginTrails도 ActivateSystem을 호출하므로 원본의 자동 LOD 선택을 다시 보정한다.
				Trail->SetLODLevel(0);
				if ((ActiveSkillIndex == 1 && !bWShadowPreview) || ActiveSkillIndex == 3 || bFlurry)
				{
					UParticleSystemComponent* Smoke = SpawnOwnedEffect(GetVisualEffect(EVisualEffect::SmokeyBlade),
						Mesh->GetSocketLocation(Base), Mesh->GetSocketRotation(Base), bFlurry ? .80f : 1.0f, Mesh->GetOwner(), bFlurry ? .26f : 1.4f);
					if (Smoke)
					{
						if (ActiveSkillIndex == 1)
						{
							Smoke->CustomTimeDilation = ActivePlayRate;
						}
						Smoke->AttachToComponent(Mesh, FAttachmentTransformRules::SnapToTargetNotIncludingScale, Base);
						if (bFlurry)
						{
							Smoke->SetAbsolute(false, false, false);
							Smoke->SetRelativeLocationAndRotation(FVector::ZeroVector, FRotator::ZeroRotator);
							Smoke->ComponentTags.Add(TEXT("CountessFlurryBladeSmoke"));
							Smoke->ComponentTags.Add(TEXT("CountessEAuthoredFX"));
							FlurryEffects.Add(Smoke);
						}
						CastBoundEffects.Add(Smoke);
					}
				}
			}
			WeaponTrails.Add(Trail);
		}
	}
}

void UCountessSkillComponent::StopWeaponTrails()
{
	for (const TWeakObjectPtr<UParticleSystemComponent>& Trail : WeaponTrails)
	{
		if (Trail.IsValid())
		{
			Trail->EndTrails();
			Trail->DeactivateSystem();
		}
	}
	WeaponTrails.Reset();
}

void UCountessSkillComponent::StopCastVisuals()
{
	StopFlurryEffects();
	for (const TWeakObjectPtr<UAudioComponent>& Audio : EffectAudio)
	{
		if (Audio.IsValid() && Audio->ComponentHasTag(TEXT("CountessSkillMovementSFX")))
		{
			Audio->Stop();
		}
	}
	for (FTimerHandle Handle : VisualTimers)
	{
		GetWorld()->GetTimerManager().ClearTimer(Handle);
	}
	VisualTimers.Reset();
	StopWeaponTrails();
	for (const TWeakObjectPtr<UParticleSystemComponent>& Particle : CastBoundEffects)
	{
		if (Particle.IsValid())
		{
			Particle->DeactivateSystem();
		}
	}
	CastBoundEffects.Reset();
}

AActor* UCountessSkillComponent::SpawnSkeletalProxy(float Lifetime, bool bShadowClone)
{
	FActorSpawnParameters Params;
	Params.Owner = Character.Get();
	Params.ObjectFlags |= RF_Transient;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	AActor* Proxy = GetWorld()->SpawnActor<AActor>(AActor::StaticClass(), Character->GetActorTransform(), Params);
	if (!Proxy)
	{
		return nullptr;
	}
	Proxy->SetCanBeDamaged(false);
	Proxy->SetActorEnableCollision(false);
	Proxy->Tags.Add(bShadowClone ? TEXT("CountessSkillShadowClone") : TEXT("CountessSkillFXProxy"));
	USkeletalMeshComponent* Mesh = NewObject<USkeletalMeshComponent>(Proxy);
	Proxy->SetRootComponent(Mesh);
	Mesh->SetSkeletalMeshAsset(Character->GetMesh()->GetSkeletalMeshAsset());
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Mesh->SetCastShadow(false);
	Mesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	Mesh->RegisterComponent();
	Mesh->SetWorldTransform(Character->GetMesh()->GetComponentTransform());
	Mesh->PlayAnimation(bShadowClone && !bDetailedCast ? ShadowCloneIdle.Get() : Skills[0].Animation.Get(), false);
	Mesh->SetPosition(bShadowClone && !bDetailedCast ? 0.0f : 0.2f, false);
	Mesh->SetPlayRate(0.0f);
	Mesh->TickAnimation(0.0f, false);
	Mesh->RefreshBoneTransforms();
	Mesh->SetVisibility(bShadowClone);
	if (bShadowClone && ShadowCloneMaterial)
	{
		UMaterialInterface* SelectedClone = bDetailedCast && DetailedCloneMaterial ? DetailedCloneMaterial.Get() : ShadowCloneMaterial.Get();
		if (ActiveSkillIndex == 0 && bDetailedCast)
		{
			if (UMaterialInterface* EchoSurface = LoadObject<UMaterialInterface>(nullptr,
				TEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessQualityMotionEcho.M_CountessQualityMotionEcho")))
			{
				UMaterialInstanceDynamic* Echo = UMaterialInstanceDynamic::Create(EchoSurface, Proxy);
				Echo->SetScalarParameterValue(TEXT("CloneOpacity"), .85f);
				Echo->SetScalarParameterValue(TEXT("DissolveStart"), GetWorld()->GetTimeSeconds() + Lifetime - .4f);
				Echo->SetScalarParameterValue(TEXT("DissolveDuration"), .25f);
				SelectedClone = Echo;
			}
		}
		for (int32 Index = 0; Index < Mesh->GetNumMaterials(); ++Index)
		{
			Mesh->SetMaterial(Index, SelectedClone);
		}
	}
	Proxy->SetLifeSpan(Lifetime);
	VisualProxies.RemoveAll([](const TWeakObjectPtr<AActor>& Item) { return !Item.IsValid(); });
	VisualProxies.Add(Proxy);
	return Proxy;
}

void UCountessSkillComponent::DamageTarget(AActor* Target, float Damage, UParticleSystem* ImpactEffect)
{
	if (!IsValidSkillTarget(Target, Character.Get()))
	{
		return;
	}
	const FVector Direction = (Target->GetActorLocation() - Character->GetActorLocation()).GetSafeNormal();
	const FHitResult Hit(Target, nullptr, Target->GetActorLocation(), -Direction);
	UGameplayStatics::ApplyPointDamage(Target, Damage, Direction, Hit, Character->GetController(), Character.Get(), nullptr);
	const bool bEnhancedQ = ActiveSkillIndex == 0 && bDetailedCast && CVarCountessQPresentation.GetValueOnGameThread() != 0;
	const bool bDenseW = ActiveSkillIndex == 1 && bDetailedCast &&
		CVarCountessWPresentation.GetValueOnGameThread() != 0;
	UParticleSystem* SelectedImpact = bDenseW && DetailedSiphonImpact ? DetailedSiphonImpact.Get() : ImpactEffect;
	if (UParticleSystemComponent* Impact = SpawnOwnedEffect(SelectedImpact, Target->GetActorLocation(),
		Direction.Rotation(), bEnhancedQ ? .80f : (bDenseW ? 1.2f : 1.0f), Target))
	{
		// 피격 표현만 조금 더 남긴다. 피해와 캐릭터의 공격/이동 시간은 유지한다.
		const float ImpactPlayRate = ActiveSkillIndex == 1 ? ActivePlayRate : 1.0f;
		Impact->CustomTimeDilation = (bEnhancedQ ? 1.20f : (bDenseW ? 0.9f : 1.0f)) * ImpactPlayRate;

	}
	if (bEnhancedQ)
	{
		if (CVarCountessQPresentation.GetValueOnGameThread() >= 2)
		{
			SpawnBlinkDualSweep(true);
		}
		else
		{
			SpawnBlinkImpactAccent(Target);
		}
	}
	if (ActiveSkillIndex == 0 && UsesQSwordAudio())
	{
		const bool bRushAudio = UsesQRushAudio();
		PlaySkillSound(bRushAudio ? ESkillSound::QRushHit : ESkillSound::QHit,
			Target->GetActorLocation(), bRushAudio ? 0.25f : 0.55f);
	}
	else if (ActiveSkillIndex != 3)
	{
		PlaySkillSound(ESkillSound::Impact, Target->GetActorLocation(), 0.4f);
	}
}

void UCountessSkillComponent::SpawnBlinkImpactAccent(AActor* Target)
{
	if (!IsValid(Target) || !Character.IsValid() || !BlinkAccentMaterial || !BlinkAccentMesh)
	{
		return;
	}
	const APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(GetWorld(), 0);
	if (!Camera)
	{
		return;
	}
	const FVector Center = Target->GetActorLocation();
	FVector Direction = (Center - CastOrigin).GetSafeNormal2D();
	if (Direction.IsNearlyZero())
	{
		Direction = Character->GetActorForwardVector();
	}
	FActorSpawnParameters Parameters;
	Parameters.Owner = Character.Get();
	Parameters.ObjectFlags |= RF_Transient;
	Parameters.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	AActor* Accent = GetWorld()->SpawnActor<AActor>(Center, FRotator::ZeroRotator, Parameters);
	if (!Accent)
	{
		return;
	}
	Accent->Tags.Add(TEXT("CountessSkillFXProxy"));
	Accent->Tags.Add(TEXT("CountessQImpactAccent"));
	Accent->SetCanBeDamaged(false);
	Accent->SetActorEnableCollision(false);
	USceneComponent* Root = NewObject<USceneComponent>(Accent);
	Accent->SetRootComponent(Root);
	Root->RegisterComponent();
	Accent->SetActorLocation(Center);
	const float SpawnTime = GetWorld()->GetTimeSeconds();
	const auto AddBlade = [&](const FVector& Location, const FRotator& Rotation,
		const FVector& Scale, float Mode, float Duration)
	{
		UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(BlinkAccentMaterial, Accent);
		Material->SetScalarParameterValue(TEXT("SpawnTime"), SpawnTime);
		Material->SetScalarParameterValue(TEXT("Duration"), Duration);
		Material->SetScalarParameterValue(TEXT("Mode"), Mode);
		UStaticMeshComponent* Blade = NewObject<UStaticMeshComponent>(Accent);
		Blade->SetupAttachment(Root);
		Blade->SetStaticMesh(BlinkAccentMesh);
		Blade->SetMaterial(0, Material);
		Blade->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Blade->SetCanEverAffectNavigation(false);
		Blade->SetCastShadow(false);
		Blade->RegisterComponent();
		Blade->SetWorldLocationAndRotation(Location, Rotation);
		Blade->SetWorldScale3D(Scale);
	};
	// 끝이 가늘어지는 초승달을 표적 중심에 짧게 펼친다. 충돌과 피해 판정은 만들지 않는다.
	// 쿼터뷰에서는 작은 교차 빛 대신 넓은 초승달과 실제 출발점의 궤적으로 베기를 읽게 한다.
	AddBlade(Center + FVector(0.0f, 0.0f, 50.0f), FRotator(18.0f, Direction.Rotation().Yaw, -12.0f),
		FVector(6.8f, 6.8f, 1.0f), 0.0f, 0.44f);
	const FVector RushCenter = (CastOrigin + Center) * 0.5f + FVector(0.0f, 0.0f, -55.0f);
	const float RushLength = FVector::Dist2D(CastOrigin, Center);
	AddBlade(RushCenter, Direction.Rotation(), FVector(FMath::Max(RushLength / 100.0f, 1.0f), 2.2f, 1.0f),
		1.0f, 0.28f);
	const FVector Facing = (Camera->GetCameraLocation() - Center).GetSafeNormal();
	AddBlade(Center + Facing * 45.0f, FRotationMatrix::MakeFromZ(Facing).Rotator(), FVector(3.6f, 3.6f, 1.0f),
		2.0f, 0.16f);
	Accent->SetLifeSpan(0.48f);
	VisualProxies.RemoveAll([](const TWeakObjectPtr<AActor>& Item) { return !Item.IsValid(); });
	VisualProxies.Add(Accent);
}

void UCountessSkillComponent::SpawnBlinkDualSweep(bool bAtImpact)
{
	if (ACountessRebirthFX::Enabled() && Character.IsValid())
	{
		if (bAtImpact && CastTarget.IsValid())
		{
			if (auto* FX = ACountessRebirthFX::Create(Character.Get(), TEXT("Q"), CastTarget->GetActorLocation() - FVector(0, 0, 65.f), Character->GetActorForwardVector())) { VisualProxies.Add(FX); }
		}
		return;
	}
	const bool bOutwardCut = CVarCountessQPresentation.GetValueOnGameThread() >= 3;
	UMaterialInterface* SelectedMaterial = bOutwardCut ? OutwardCutMaterial.Get() : DualSweepMaterial.Get();
	if (bOutwardCut)
	{
		if (!LoadedCompactOutwardCutMaterial)
		{
			LoadedCompactOutwardCutMaterial = CompactOutwardCutMaterial.LoadSynchronous();
		}
		if (LoadedCompactOutwardCutMaterial)
		{
			SelectedMaterial = LoadedCompactOutwardCutMaterial.Get();
		}
	}
	UStaticMesh* SelectedMesh = bOutwardCut ? OutwardCutMesh.Get() : DualSweepMesh.Get();
	if (!Character.IsValid() || !SelectedMaterial || !SelectedMesh || !BlinkAccentMesh)
	{
		return;
	}
	USkeletalMeshComponent* Mesh = Character->GetMesh();
	AActor* Sweep = nullptr;
	for (const TWeakObjectPtr<AActor>& Proxy : VisualProxies)
	{
		if (Proxy.IsValid() && Proxy->ActorHasTag(TEXT("CountessQDualSweep")))
		{
			Sweep = Proxy.Get();
			break;
		}
	}
	const float Now = GetWorld()->GetTimeSeconds();
	const auto AddVisual = [&](AActor* Owner, UStaticMesh* Shape, const FVector& Location,
		const FRotator& Rotation, const FVector& Scale, float Mode, float SpawnTime, float Duration)
	{
		UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(SelectedMaterial, Owner);
		Material->SetScalarParameterValue(TEXT("Mode"), Mode);
		Material->SetScalarParameterValue(TEXT("SpawnTime"), SpawnTime);
		Material->SetScalarParameterValue(TEXT("Duration"), Duration);
		if (bOutwardCut)
		{
			Material->SetScalarParameterValue(TEXT("ToneMix"), static_cast<float>(FMath::Clamp(CVarCountessQTone.GetValueOnGameThread(), 0, 1)));
		}
		UStaticMeshComponent* Visual = NewObject<UStaticMeshComponent>(Owner);
		Visual->SetupAttachment(Owner->GetRootComponent());
		Visual->SetStaticMesh(Shape);
		Visual->SetMaterial(0, Material);
		Visual->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Visual->SetCanEverAffectNavigation(false);
		Visual->SetCastShadow(false);
		Visual->RegisterComponent();
		Visual->SetWorldLocationAndRotation(Location, Rotation);
		Visual->SetWorldScale3D(Scale);
	};
	if (!Sweep)
	{
		FActorSpawnParameters Parameters;
		Parameters.Owner = Character.Get();
		Parameters.ObjectFlags |= RF_Transient;
		Parameters.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		Sweep = GetWorld()->SpawnActor<AActor>(Mesh->GetComponentLocation(), Mesh->GetComponentRotation(), Parameters);
		if (!Sweep)
		{
			return;
		}
		Sweep->Tags.Append({TEXT("CountessSkillFXProxy"), TEXT("CountessQImpactAccent"), TEXT("CountessQDualSweep")});
		Sweep->SetCanBeDamaged(false);
		Sweep->SetActorEnableCollision(false);
		USceneComponent* Root = NewObject<USceneComponent>(Sweep);
		Sweep->SetRootComponent(Root);
		Root->RegisterComponent();
		Sweep->AttachToComponent(Mesh, FAttachmentTransformRules::SnapToTargetNotIncludingScale);
		// 원본 Ability_Q의 양칼 소켓 궤적이다. 카메라나 표적을 향하는 임의 평면으로 회전하지 않는다.
		// 새 표현은 소켓의 시작점과 좌우 방향만 사용한 짧은 직선 베기다.
		AddVisual(Sweep, SelectedMesh, Mesh->GetComponentLocation(), Mesh->GetComponentRotation(),
			Mesh->GetComponentScale() * FVector(bOutwardCut ? FMath::Clamp(CVarCountessQLengthScale.GetValueOnGameThread(), 0.35f, 1.0f) : 1.0f, 1.0f, 1.0f),
			0.0f, Now - (bAtImpact ? 0.20f : 0.10f), 0.58f);
		Sweep->SetLifeSpan(0.56f);
		VisualProxies.RemoveAll([](const TWeakObjectPtr<AActor>& Item) { return !Item.IsValid(); });
		VisualProxies.Add(Sweep);
	}
	if (!bAtImpact || !IsValid(CastTarget.Get()))
	{
		return;
	}
	// 베기 중에는 실제 메시 방향을 따르고, 도착 후 잔상은 월드에 고정한다.
	Sweep->DetachFromActor(FDetachmentTransformRules::KeepWorldTransform);
	Sweep->SetLifeSpan(0.40f);
	const FVector Center = CastTarget->GetActorLocation();
	const FVector Direction = (Center - CastOrigin).GetSafeNormal2D();
	const FVector RushCenter = (CastOrigin + Center) * 0.5f + FVector(0.0f, 0.0f, -55.0f);
	const float RushLength = FVector::Dist2D(CastOrigin, Center);
	AddVisual(Sweep, BlinkAccentMesh, RushCenter, Direction.Rotation(),
		FVector(FMath::Max(RushLength / 100.0f, 1.0f), 2.2f, 1.0f), 1.0f, Now, 0.28f);
	if (const APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(GetWorld(), 0))
	{
		const FVector Facing = (Camera->GetCameraLocation() - Center).GetSafeNormal();
		AddVisual(Sweep, BlinkAccentMesh, Center + Facing * 45.0f,
			FRotationMatrix::MakeFromZ(Facing).Rotator(), FVector(3.6f, 3.6f, 1.0f), 2.0f, Now, 0.16f);
	}
}

bool UCountessSkillComponent::FindFeastLanding(AActor* Target, FVector& Result) const
{
	if (!Character.IsValid() || !IsValidSkillTarget(Target, Character.Get()) || !HasLineOfSight(Target) ||
		FVector::DistSquared2D(Character->GetActorLocation(), Target->GetActorLocation()) > FMath::Square(Skills[3].Range) ||
		!FindTargetLanding(Target, Result))
	{
		return false;
	}
	// 내비게이션 높이 차이로 OnTeleported가 낙하 상태를 선택해 궁극기를 끊지 않도록 실제 바닥에 맞춘다.
	FFindFloorResult Floor;
	Character->GetCharacterMovement()->FindFloor(Result, Floor, false);
	if (!Floor.IsWalkableFloor())
	{
		return false;
	}
	const float FloorGap = (UCharacterMovementComponent::MIN_FLOOR_DIST + UCharacterMovementComponent::MAX_FLOOR_DIST) * 0.5f;
	Result.Z += FloorGap - (Floor.bLineTrace ? Floor.LineDist : Floor.FloorDist);
	return IsBlinkPathClear(Result, Target);
}

void UCountessSkillComponent::ApproachFeast()
{
	if (!bCasting || ActiveSkillIndex != 3 || !Character.IsValid())
	{
		return;
	}
	if (FindFeastLanding(CastTarget.Get(), FeastLandingLocation))
	{
		FeastApproachOrigin = Character->GetActorLocation();
		FeastApproachStartedAt = GetWorld()->GetTimeSeconds();
		bFeastApproaching = true;
		UpdateFeastApproach();
		return;
	}
	NextSkillTimes[3] = 0.0;
	RejectInput(TEXT("Blocked"));
	FinishSkill();
}

void UCountessSkillComponent::UpdateFeastApproach()
{
	if (!bFeastApproaching || !bCasting || ActiveSkillIndex != 3 || !Character.IsValid())
	{
		return;
	}
	const float Alpha = FMath::Clamp(static_cast<float>((GetWorld()->GetTimeSeconds() - FeastApproachStartedAt) /
		FeastApproachSeconds), 0.0f, 1.0f);
	const FVector Position = FMath::Lerp(FeastApproachOrigin, FeastLandingLocation, Alpha);
	FHitResult Hit;
	// 도약 높이는 원본 모션으로 표현하고, 실제 캡슐은 바닥 경로를 sweep하여 벽 관통을 막는다.
	Character->SetActorLocation(Position, true, &Hit);
	if (Hit.bBlockingHit && !Character->GetActorLocation().Equals(Position, 2.0f))
	{
		NextSkillTimes[3] = 0.0;
		RejectInput(TEXT("Blocked"));
		FinishSkill();
		return;
	}
	if (IsValidSkillTarget(CastTarget.Get(), Character.Get()))
	{
		Character->SetActorRotation((CastTarget->GetActorLocation() - Character->GetActorLocation()).GetSafeNormal2D().Rotation());
	}
	if (Alpha >= 1.0f)
	{
		bFeastApproaching = false;
		bFeastArrived = true;
	}
}

void UCountessSkillComponent::ExecuteAction()
{
	if (!bCasting || bActionExecuted || !Character.IsValid())
	{
		return;
	}
	bActionExecuted = true;
	const FCountessSkillDefinition& Skill = Skills[ActiveSkillIndex];
	AActor* Target = CastTarget.Get();
	if (ActiveSkillIndex == 0 || ActiveSkillIndex == 3)
	{
		FVector Destination;
		bool bCanLand = false;
		if (bReturning)
		{
			const FVector Feet = ReturnLocation - FVector(0.0f, 0.0f, Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
			bCanLand = GetReturnRemaining() > 0.0f && FindLandingPoint(Feet, Destination);
		}
		else if (ActiveSkillIndex == 3)
		{
			UpdateFeastApproach();
			if (!bCasting)
			{
				return;
			}
			FVector ValidLanding;
			bCanLand = bFeastArrived && FindFeastLanding(Target, ValidLanding) &&
				FVector::DistSquared2D(Character->GetActorLocation(), Target->GetActorLocation()) <=
				FMath::Square(Character->GetSimpleCollisionRadius() + Target->GetSimpleCollisionRadius() + 70.0f);
			Destination = Character->GetActorLocation();
		}
		else
		{
			bCanLand = IsValidSkillTarget(Target, Character.Get()) && HasLineOfSight(Target) &&
				FVector::DistSquared2D(Character->GetActorLocation(), Target->GetActorLocation()) <= FMath::Square(Skill.Range) &&
				FindTargetLanding(Target, Destination);
		}

		const FVector Source = Character->GetActorLocation();
		const FRotator SourceRotation = Character->GetActorRotation();
		const FRotator Facing = bReturning ? ReturnRotation :
			(bCanLand ? (Target->GetActorLocation() - Destination).GetSafeNormal2D().Rotation() : SourceRotation);
		AActor* DepartureProxy = nullptr;
		if (bCanLand && ActiveSkillIndex == 0)
		{
			if (!bReturning)
			{
				ExpireReturn();
				ReturnClone = SpawnSkeletalProxy(3.2f, true);
				DepartureProxy = ReturnClone;
			}
			else
			{
				DepartureProxy = SpawnSkeletalProxy(0.8f, false);
			}
		}
		// 이미 도착한 위치에서는 MoveComponent의 무이동 반환값을 착지 실패로 취급하지 않는다.
		const bool bAlreadyAtLanding = bCanLand && ActiveSkillIndex == 3 && Character->GetActorLocation().Equals(Destination, 0.1f);
		if (!bCanLand || (!bAlreadyAtLanding && !Character->TeleportTo(Destination, Facing, false, false)))
		{
			if (!bReturning)
			{
				NextSkillTimes[ActiveSkillIndex] = 0.0;
				if (ActiveSkillIndex == 0)
				{
					ExpireReturn();
				}
			}
			RejectInput(TEXT("Blocked"));
			FinishSkill();
			return;
		}
		if (bAlreadyAtLanding)
		{
			Character->SetActorRotation(Facing);
		}
		if (ActiveSkillIndex == 0)
		{
			if (UsesQSwordAudio())
			{
				if (UsesQRushAudio())
				{
					PlaySkillSound(ESkillSound::QRushSlash, Character->GetActorLocation(), bReturning ? 0.25f : 0.45f);
				}
				else
				{
					PlaySkillSound(ESkillSound::QSlash, Character->GetActorLocation(), bReturning ? 0.35f : 0.55f);
				}
			}
			else
			{
				PlaySkillSound(ESkillSound::Blink, Character->GetActorLocation());
			}
			SpawnOwnedEffect(bReturning ? GetVisualEffect(EVisualEffect::ReturnDeparture) : Skill.CastEffect.Get(),
				Source - FVector(0, 0, Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()),
				SourceRotation, 1.0f, DepartureProxy, 0.8f);
			SpawnOwnedEffect(TeleportArrivalEffect, GetFeetLocation(), Character->GetActorRotation(),
				1.0f, Character.Get(), 1.0f, true);
			const bool bEnhancedQ = !bReturning && bDetailedCast && CVarCountessQPresentation.GetValueOnGameThread() != 0;
			SpawnOwnedEffect(GetVisualEffect(EVisualEffect::BlinkFlash), GetFeetLocation(),
				Character->GetActorRotation(), bEnhancedQ ? .62f : .75f);
			if (!bReturning && !bEnhancedQ)
			{
				SpawnOwnedEffect(GetVisualEffect(EVisualEffect::BlinkSlash), GetFeetLocation(), Character->GetActorRotation());
			}
		}
		else
		{
			float Radius, HalfHeight;
			Target->GetSimpleCollisionCylinder(Radius, HalfHeight);
			if (!bDetailedCast)
			{
				SpawnOwnedEffect(GetVisualEffect(EVisualEffect::FeastSlash), GetFeetLocation(), Character->GetActorRotation());
			}
			else
			{
				PlaySkillSound(ESkillSound::FeastHit, Target->GetActorLocation(), 0.9f);
				SpawnOwnedEffect(GetVisualEffect(EVisualEffect::FeastTargetRemove), Target->GetActorLocation() - FVector(0, 0, HalfHeight),
					Character->GetActorRotation(), 1.0f, Target, 1.0f, true);
			}
			SpawnOwnedEffect(GetVisualEffect(EVisualEffect::FeastGround), Target->GetActorLocation() - FVector(0, 0, HalfHeight), Character->GetActorRotation());
			SpawnOwnedEffect(GetVisualEffect(EVisualEffect::FeastImpact), Target->GetActorLocation(), Character->GetActorRotation(), 1.0f, Target);
		}
		if (bReturning)
		{
			ExpireReturn();
		}
		else
		{
			DamageTarget(Target, Skill.Damage, Skill.ImpactEffect);
			if (ActiveSkillIndex == 3)
			{
				UE_LOG(LogTemp, Display, TEXT("COUNTESS_FAST_R hit damage=%.1f elapsed=%.3f"), Skill.Damage,
					GetWorld()->GetTimeSeconds() - FeastApproachStartedAt);
			}
			if (ActiveSkillIndex == 0)
			{
				ReturnLocation = Source;
				ReturnRotation = SourceRotation;
				ReturnDeadline = GetWorld()->GetTimeSeconds() + 3.0;
				ReturnMarker = SpawnOwnedEffect(ReturnEffect,
					Source - FVector(0, 0, Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()),
					SourceRotation, 1.0f, ReturnClone, 3.0f, true);
				if (bDetailedCast)
				{
					ReturnLens = SpawnLensEffect(EVisualEffect::BlinkLensDuration, 3.0f);
				}
				GetWorld()->GetTimerManager().SetTimer(ReturnTimer, this, &UCountessSkillComponent::ExpireReturn, 3.0f, false);
				ApplyShadowSlow(Target);
			}
		}
	}
	else if (ActiveSkillIndex == 1)
	{
		ReleaseBladeSiphon(Character->GetActorLocation(), bDetailedCast, ActivePlayRate);
	}
	else if (ActiveSkillIndex == 2)
	{
		PlaySkillSound(ESkillSound::Tide, Character->GetActorLocation());
		if (bDetailedCast)
		{
			SpawnLensEffect(EVisualEffect::TideLens, 0.6f);
		}
		SpawnOwnedEffect(Skill.CastEffect, GetFeetLocation(), Character->GetActorRotation());
		FVector Direction = (CastAim - Character->GetActorLocation()).GetSafeNormal2D();
		if (Direction.IsNearlyZero())
		{
			Direction = Character->GetActorForwardVector();
		}
		FActorSpawnParameters Params;
		Params.Owner = Character.Get();
		Params.Instigator = Character.Get();
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		ACountessDarkTide* Tide = GetWorld()->SpawnActor<ACountessDarkTide>(ACountessDarkTide::StaticClass(),
			Character->GetActorLocation() + Direction * 75.0f, Direction.Rotation(), Params);
		if (Tide)
		{
			Tide->Initialize(Direction, Skill.Damage, Skill.Range,
				bDetailedCast && DetailedTideEffect ? DetailedTideEffect.Get() : TideEffect.Get(), Skill.ImpactEffect);
		}
	}
}

void UCountessSkillComponent::StartFeastStun()
{
	AActor* Target = CastTarget.Get();
	if (!bCasting || ActiveSkillIndex != 3 || !IsValidSkillTarget(Target, Character.Get()) || !HasLineOfSight(Target))
	{
		return;
	}
	if (FVector::DistSquared2D(CastOrigin, Target->GetActorLocation()) > FMath::Square(Skills[3].Range))
	{
		NextSkillTimes[3] = 0.0;
		RejectInput(TEXT("Out of range"));
		FinishSkill();
		return;
	}
	if (APawn* Victim = Cast<APawn>(Target))
	{
		Victim->SetActorRotation((Character->GetActorLocation() - Target->GetActorLocation()).GetSafeNormal2D().Rotation());
	}
	if (ACharacter* Victim = Cast<ACharacter>(Target))
	{
		StunnedMovement = Victim->GetCharacterMovement();
		SavedTargetMovementMode = StunnedMovement->MovementMode;
		SavedTargetCustomMode = StunnedMovement->CustomMovementMode;
		if (Victim->GetController())
		{
			Victim->GetController()->StopMovement();
		}
		StunnedMovement->StopMovementImmediately();
		StunnedMovement->DisableMovement();
	}
	if (AKwangTrainingDummy* Dummy = Cast<AKwangTrainingDummy>(Target))
	{
		Dummy->SetCombatStatus(TEXT("STUN"), 0.75f / ActivePlayRate);
	}
	CastBoundEffects.Add(SpawnOwnedEffect(FeastApplicationEffect, Target->GetActorLocation(),
		Character->GetActorRotation(), 1.0f, Target, 0.8f / ActivePlayRate, true));
	if (bDetailedCast && Target->FindComponentByClass<USkeletalMeshComponent>())
	{
		CastBoundEffects.Add(SpawnOwnedEffect(GetVisualEffect(EVisualEffect::FeastBind), Target->GetActorLocation(),
			Character->GetActorRotation(), 1.0f, Target, 0.85f / ActivePlayRate, true));
	}
	GetWorld()->GetTimerManager().SetTimer(StunEndTimer, this, &UCountessSkillComponent::RestoreTargetMovement, 0.75f / ActivePlayRate, false);
}

void UCountessSkillComponent::RestoreTargetMovement()
{
	if (AKwangTrainingDummy* Dummy = Cast<AKwangTrainingDummy>(CastTarget.Get()))
	{
		if (Dummy->GetCombatStatus() == TEXT("STUN"))
		{
			Dummy->SetCombatStatus(NAME_None, 0.01f);
		}
	}
	if (StunnedMovement.IsValid() && StunnedMovement->MovementMode == MOVE_None)
	{
		StunnedMovement->SetMovementMode(SavedTargetMovementMode, SavedTargetCustomMode);
	}
	StunnedMovement.Reset();
}

void UCountessSkillComponent::ApplyShadowSlow(AActor* Target)
{
	RestoreSlow();
	if (ACharacter* Victim = Cast<ACharacter>(Target))
	{
		SlowedMovement = Victim->GetCharacterMovement();
		SavedTargetSpeed = SlowedMovement->MaxWalkSpeed;
		AppliedTargetSpeed = SavedTargetSpeed * 0.58f;
		SlowedMovement->MaxWalkSpeed = AppliedTargetSpeed;
	}
	if (AKwangTrainingDummy* Dummy = Cast<AKwangTrainingDummy>(Target))
	{
		Dummy->SetCombatStatus(TEXT("SLOW"), 1.5f);
	}
	GetWorld()->GetTimerManager().SetTimer(SlowTimer, this, &UCountessSkillComponent::RestoreSlow, 1.5f, false);
}

void UCountessSkillComponent::RestoreSlow()
{
	// 다른 시스템이 속도를 변경한 경우 그 값을 이전 수치로 덮어쓰지 않는다.
	if (SlowedMovement.IsValid() && FMath::IsNearlyEqual(SlowedMovement->MaxWalkSpeed, AppliedTargetSpeed))
	{
		SlowedMovement->MaxWalkSpeed = SavedTargetSpeed;
	}
	SlowedMovement.Reset();
}

void UCountessSkillComponent::ExpireReturn()
{
	if (ReturnLens.IsValid())
	{
		ReturnLens->Destroy();
		ReturnLens.Reset();
	}
	if (IsValid(ReturnClone))
	{
		if (Character.IsValid() && !Character->IsActorBeingDestroyed())
		{
			SpawnOwnedEffect(GetVisualEffect(EVisualEffect::CloneBurst), ReturnClone->GetActorLocation(), ReturnRotation);
		}
		ReturnClone->Destroy();
		ReturnClone = nullptr;
	}
	ReturnDeadline = 0.0;
	GetWorld()->GetTimerManager().ClearTimer(ReturnTimer);
	if (ReturnMarker)
	{
		ReturnMarker->DestroyComponent();
		ReturnMarker = nullptr;
	}
}

void UCountessSkillComponent::OnMontageEnded(UAnimMontage* Montage, bool bInterrupted, uint32 Generation)
{
	if (bCasting && Generation == CastGeneration && Montage == ActiveMontage)
	{
		FinishSkill();
	}
}

void UCountessSkillComponent::OnMontageBlendingOut(UAnimMontage* Montage, bool bInterrupted, uint32 Generation)
{
	if (bInterrupted && bCasting && Generation == CastGeneration && Montage == ActiveMontage)
	{
		FinishSkill();
	}
}

void UCountessSkillComponent::FinishSkill()
{
	if (!bCasting)
	{
		return;
	}
	if (ActiveSkillIndex == 0 && !bActionExecuted)
	{
		for (const TWeakObjectPtr<AActor>& Proxy : VisualProxies)
		{
			if (Proxy.IsValid() && Proxy->ActorHasTag(TEXT("CountessQDualSweep")))
			{
				Proxy->Destroy();
			}
		}
	}
	ClearExtraCast();
	StopCastVisuals();
	RetireFlurryShadow();
	bFeastApproaching = false;
	bFeastArrived = false;
	bCasting = false;
	++CastGeneration;
	SetComponentTickEnabled(bReforgeCasting || !ReforgePulses.IsEmpty());
	GetWorld()->GetTimerManager().ClearTimer(ActionTimer);
	GetWorld()->GetTimerManager().ClearTimer(FlurryStrikeTimer);
	GetWorld()->GetTimerManager().ClearTimer(RecoveryTimer);
	GetWorld()->GetTimerManager().ClearTimer(StunStartTimer);
	GetWorld()->GetTimerManager().ClearTimer(FeastArrivalTimer);
	GetWorld()->GetTimerManager().ClearTimer(StunEndTimer);
	RestoreTargetMovement();
	if (CastAnimInstance.IsValid())
	{
		CastAnimInstance->Montage_Stop(0.14f, ActiveMontage);
		CastAnimInstance->SetRootMotionMode(SavedRootMotionMode);
	}
	if (Character.IsValid())
	{
		Character->GetCharacterMovement()->bOrientRotationToMovement = bSavedOrientRotation;
	}
	ActiveMontage = nullptr;
	ActiveSkillIndex = INDEX_NONE;
	CastTarget.Reset();
	CastAnimInstance.Reset();
}

void UCountessSkillComponent::CancelSkill()
{
	FinishReforgeCast();
	if (BackstepEcho.IsValid()) { BackstepEcho->Destroy(); }
	BackstepEcho.Reset();
	ClearCursorBlinkVisuals();
	FinishSkill();
	ClearExtraWorldEffects();
	for (const TWeakObjectPtr<AActor>& Proxy : VisualProxies)
	{
		if (Proxy.IsValid() && Proxy->ActorHasTag(TEXT("CountessQImpactAccent")))
		{
			Proxy->Destroy();
		}
	}
	if (CastAudio.IsValid())
	{
		CastAudio->Stop();
	}
}

void UCountessSkillComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	TickReforgeSkills(DeltaTime);
	if (bCasting && bEFlurryPrototype && ActiveSkillIndex == 2 && (!FlurryShadow.IsValid() || !ValidateFlurryTarget()))
	{
		FinishSkill();
		return;
	}
	if (bCasting && !bActionExecuted && !bReturning && (ActiveSkillIndex == 0 || ActiveSkillIndex == 3) &&
		!IsValidSkillTarget(CastTarget.Get(), Character.Get()))
	{
		NextSkillTimes[ActiveSkillIndex] = 0.0;
		FinishSkill();
		return;
	}
	// 애니메이션 교체·낙하·외부 몽타주 중단에서도 입력 잠금과 대상 기절을 복구한다.
	if (bCasting && (!Character.IsValid() || !CastAnimInstance.IsValid() ||
		Character->GetMesh()->GetAnimInstance() != CastAnimInstance.Get() ||
		Character->GetCharacterMovement()->MovementMode != MOVE_Walking ||
		CastAnimInstance->Montage_GetIsStopped(ActiveMontage)))
	{
		FinishSkill();
		return;
	}
	if (bCasting && ActiveSkillIndex == 3)
	{
		UpdateFeastApproach();
	}
	if (bCasting && ActiveSkillIndex >= 8)
	{
		UpdateExtraRush();
	}
}

void UCountessSkillComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	CleanupReforgeSkills();
	if (BackstepEcho.IsValid()) { BackstepEcho->Destroy(); }
	BackstepEcho.Reset();
	ClearCursorBlinkVisuals();
	FinishSkill();
	ClearExtraWorldEffects();
	RestoreSlow();
	ExpireReturn();
	if (CastAudio.IsValid())
	{
		CastAudio->Stop();
	}
	for (const TWeakObjectPtr<UParticleSystemComponent>& Particle : OwnedEffects)
	{
		if (Particle.IsValid())
		{
			Particle->DestroyComponent();
		}
	}
	for (const TWeakObjectPtr<AActor>& Proxy : VisualProxies)
	{
		if (Proxy.IsValid())
		{
			Proxy->Destroy();
		}
	}
	for (const TWeakObjectPtr<ACountessSkillLensEffect>& Lens : LensEffects)
	{
		if (Lens.IsValid())
		{
			Lens->Destroy();
		}
	}
	for (const TWeakObjectPtr<UAudioComponent>& Audio : EffectAudio)
	{
		if (Audio.IsValid())
		{
			Audio->Stop();
		}
	}
	GetWorld()->GetTimerManager().ClearTimer(SlowTimer);
	Super::EndPlay(EndPlayReason);
}

bool UCountessSkillComponent::IsBlinkPathClear(const FVector& Destination, AActor* IgnoreTarget) const
{
	if (!Character.IsValid() || !GetWorld() || Destination.ContainsNaN()) { return false; }
	const UCapsuleComponent* Capsule = Character->GetCapsuleComponent();
	FCollisionQueryParams Query(SCENE_QUERY_STAT(CountessInstantBlinkPath), false, Character.Get());
	if (IsValid(IgnoreTarget)) { Query.AddIgnoredActor(IgnoreTarget); }
	const FCollisionShape Shape = FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(),
		FMath::Max(Capsule->GetScaledCapsuleRadius(), Capsule->GetScaledCapsuleHalfHeight() - 1.0f));
	// 착지점만 비어 있어도 벽을 건너뛰지 않는다. 물리 캡슐이 지나갈 전체 구간을 검사한다.
	if (GetWorld()->OverlapBlockingTestByChannel(Destination, FQuat::Identity, ECC_Pawn, Shape, Query)) { return false; }
	if (Character->GetActorLocation().Equals(Destination, .1f)) { return true; }
	FHitResult Hit;
	return !GetWorld()->SweepSingleByChannel(Hit, Character->GetActorLocation(), Destination,
		FQuat::Identity, ECC_Pawn, Shape, Query);
}

bool UCountessSkillComponent::FindCursorBlinkLanding(const FVector& AimLocation, FVector& Result) const
{
	if (!Character.IsValid() || AimLocation.ContainsNaN()) { return false; }
	const FVector Origin = Character->GetActorLocation();
	const FVector Delta = AimLocation - Origin;
	const float Distance = FMath::Min(static_cast<float>(Delta.Size2D()), CursorBlinkRange);
	if (Distance < 25.0f) { return false; }
	const FVector Requested = Origin + Delta.GetSafeNormal2D() * Distance;
	if (!FindLandingPoint(FVector(Requested.X, Requested.Y, AimLocation.Z), Result)) { return false; }
	if (FVector::DistSquared2D(Origin, Result) > FMath::Square(CursorBlinkRange + .5f) ||
		FMath::Abs(Result.Z - Origin.Z) > 180.0f) { return false; }
	FFindFloorResult Floor;
	Character->GetCharacterMovement()->FindFloor(Result, Floor, false);
	if (!Floor.IsWalkableFloor()) { return false; }
	const float FloorGap = (UCharacterMovementComponent::MIN_FLOOR_DIST + UCharacterMovementComponent::MAX_FLOOR_DIST) * .5f;
	Result.Z += FloorGap - (Floor.bLineTrace ? Floor.LineDist : Floor.FloorDist);
	return IsBlinkPathClear(Result);
}

void UCountessSkillComponent::SpawnCursorBlinkEchoes(const FVector& Origin, const FVector& Destination,
	const FTransform& SourceMeshTransform)
{
	if (Character.IsValid())
	{
		ACountessRebirthFX::Create(Character.Get(), TEXT("F"), Origin, Character->GetActorForwardVector());
		ACountessRebirthFX::Create(Character.Get(), TEXT("F"), Destination, Character->GetActorForwardVector());
	}
	UMaterialInterface* Source = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessQualityMotionEcho.M_CountessQualityMotionEcho"));
	if (!Source) { Source = FlurryShadowDissolveMaterial.LoadSynchronous(); }
	if (!Source)
	{
		UE_LOG(LogTemp, Warning, TEXT("COUNTESS_CURSOR_BLINK missing_echo_material"));
		return;
	}
	CursorBlinkEchoes.RemoveAll([](const TWeakObjectPtr<AActor>& Item) { return !Item.IsValid(); });
	for (int32 Index = 0; Index < 3; ++Index)
	{
		while (CursorBlinkEchoes.Num() >= 9)
		{
			if (CursorBlinkEchoes[0].IsValid()) { CursorBlinkEchoes[0]->Destroy(); }
			CursorBlinkEchoes.RemoveAt(0);
		}
		FActorSpawnParameters Params;
		Params.Owner = Character.Get();
		Params.ObjectFlags |= RF_Transient;
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		AActor* Echo = GetWorld()->SpawnActor<AActor>(AActor::StaticClass(), FTransform::Identity, Params);
		if (!Echo) { continue; }
		Echo->SetActorEnableCollision(false);
		Echo->SetCanBeDamaged(false);
		Echo->Tags.Append({TEXT("CountessSkillFXProxy"), TEXT("CountessCursorBlinkResidue")});
		UPoseableMeshComponent* Mesh = NewObject<UPoseableMeshComponent>(Echo);
		Echo->SetRootComponent(Mesh);
		Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Mesh->SetGenerateOverlapEvents(false);
		Mesh->SetCanEverAffectNavigation(false);
		Mesh->SetSkinnedAssetAndUpdate(Character->GetMesh()->GetSkinnedAsset());
		Mesh->SetCastShadow(false);
		Mesh->ComponentTags.Add(TEXT("CountessCursorBlinkResidue"));
		Mesh->RegisterComponent();
		FTransform Transform = SourceMeshTransform;
		Transform.AddToTranslation((Destination - Origin) * ((Index + 1) * .25f));
		Mesh->SetWorldTransform(Transform);
		Mesh->CopyPoseFromSkeletalComponent(Character->GetMesh());
		Mesh->RefreshBoneTransforms();
		Mesh->SetComponentTickEnabled(false);
		UMaterialInstanceDynamic* Ink = UMaterialInstanceDynamic::Create(Source, Echo);
		Ink->SetScalarParameterValue(TEXT("CloneOpacity"), .30f + Index * .15f);
		const FVector Travel = (Destination - Origin).GetSafeNormal();
		Ink->SetVectorParameterValue(TEXT("EchoDirection"), FLinearColor(-Travel.X, -Travel.Y, .35f));
		Ink->SetScalarParameterValue(TEXT("DissolveStart"), GetWorld()->GetTimeSeconds() + Index * .015f);
		Ink->SetScalarParameterValue(TEXT("DissolveDuration"), .20f + Index * .025f);
		for (int32 Slot = 0; Slot < Mesh->GetNumMaterials(); ++Slot) { Mesh->SetMaterial(Slot, Ink); }
		Echo->SetLifeSpan(.34f);
		CursorBlinkEchoes.Add(Echo);
		VisualProxies.RemoveAll([](const TWeakObjectPtr<AActor>& Item) { return !Item.IsValid(); });
		VisualProxies.Add(Echo);
	}
}

bool UCountessSkillComponent::IsBackstepping() const
{
	return BackstepEcho.IsValid() && BackstepEcho->IsMoving();
}

bool UCountessSkillComponent::TryBackstep()
{
	if (!bEnabled || !Character.IsValid() || !GetWorld() || IsBackstepping() ||
		!Character->GetCharacterMovement() || Character->GetCharacterMovement()->MovementMode != MOVE_Walking)
	{
		return RejectInput(TEXT("Backstep unavailable"));
	}
	if (GetSlotCooldownRemaining(17) > 0.0f) { return RejectInput(TEXT("Cooldown")); }
	UCapsuleComponent* Capsule = Character->GetCapsuleComponent();
	USkeletalMeshComponent* Mesh = Character->GetMesh();
	UAnimInstance* Anim = Mesh ? Mesh->GetAnimInstance() : nullptr;
	UNavigationSystemV1* Navigation = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
	if (!Capsule || !Mesh || !Mesh->GetSkeletalMeshAsset() || !Anim || !Navigation)
	{
		return RejectInput(TEXT("Backstep unavailable"));
	}
	const FVector Start = Character->GetActorLocation();
	FVector Destination = Start - Character->GetActorForwardVector() * 220.0f;
	FCollisionQueryParams Query(SCENE_QUERY_STAT(CountessBackstep), false, Character.Get());
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
	if (!bProjected ||
		FVector::DistSquared2D(Projected.Location, Destination) > FMath::Square(35.0f) ||
		FVector::DistSquared2D(Start, Destination) < FMath::Square(15.0f))
	{
		UE_LOG(LogTemp, Display, TEXT("COUNTESS_BACKSTEP reject_safe_space projected=%d nav_busy=%d start=%s forward=%s destination=%s floor=%s nav=%s sweep=%s initial_overlap=%d"),
			bProjected, Navigation->IsNavigationBuildInProgress(), *Start.ToString(), *Character->GetActorForwardVector().ToString(),
			*Destination.ToString(), *Floor.ImpactPoint.ToString(), *Projected.Location.ToString(), *GetNameSafe(Hit.GetActor()), Hit.bStartPenetrating);
		return RejectInput(TEXT("No safe space behind"));
	}
	if (!BackstepMontage)
	{
		UAnimSequence* Sequence = LoadObject<UAnimSequence>(nullptr,
			TEXT("/Game/ParagonCountess/Characters/Heroes/Countess/Animations/Jog_Bwd_Start.Jog_Bwd_Start"));
		if (!Sequence || Sequence->GetSkeleton() != Mesh->GetSkeletalMeshAsset()->GetSkeleton())
		{
			return RejectInput(TEXT("Backstep animation unavailable"));
		}
		BackstepMontage = UAnimMontage::CreateSlotAnimationAsDynamicMontage(Sequence,
			TEXT("CountessFullBody"), 0.012f, 0.025f, 1.0f, 1);
	}
	if (!BackstepMontage || !FlurryShadowDissolveMaterial.LoadSynchronous())
	{
		return RejectInput(TEXT("Backstep presentation unavailable"));
	}
	const bool bWasSiphon = bCasting && ActiveSkillIndex == 1;
	const float PendingDelay = bWasSiphon && !bActionExecuted ?
		GetWorld()->GetTimerManager().GetTimerRemaining(ActionTimer) : -1.0f;
	const bool bTransfer = PendingDelay >= 0.0f;
	UAnimMontage* Captured = bWasSiphon ? ActiveMontage.Get() : (bReforgeCasting ? ReforgeMontage.Get() : nullptr);
	const float Position = Captured ? Anim->Montage_GetPosition(Captured) : 0.0f;
	const float Rate = bWasSiphon ? ActivePlayRate : (bReforgeCasting ? ReforgePlayRate : 0.0f);
	const bool bDetailed = bWasSiphon && bDetailedCast;
	const float Delay = bTransfer ? PendingDelay : 0.0f;
	const bool bTransferInferno = bReforgeCasting && ReforgeSlot == 16 && !bReforgeCommitted;
	const float InfernoDelay = bTransferInferno ? FMath::Max(.001f,
		ReforgeCommitTime - static_cast<float>(GetWorld()->GetTimeSeconds() - ReforgeStartedAt)) : 0.0f;
	const FVector InfernoOrigin = ReforgeOrigin;
	const FVector InfernoAim = ReforgeAim;
	const FVector InfernoDirection = ReforgeDirection;
	if (BackstepEcho.IsValid()) { BackstepEcho->Destroy(); BackstepEcho.Reset(); }
	FActorSpawnParameters Spawn;
	Spawn.Owner = Character.Get();
	Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	ACountessBackstepEcho* Echo = GetWorld()->SpawnActor<ACountessBackstepEcho>(Start, Character->GetActorRotation(), Spawn);
	if (!Echo) { return RejectInput(TEXT("Backstep unavailable")); }
	FinishReforgeCast();
	FinishSkill();
	Character->InterruptIntroAnimation();
	Character->CancelBasicAttackForSkill();
	if (!Echo->Initialize(Character.Get(), this, BackstepMontage, Captured, Position, Rate, Delay,
		bTransfer, bDetailed, Destination))
	{
		Echo->Destroy();
		return RejectInput(TEXT("Backstep animation unavailable"));
	}
	BackstepEcho = Echo;
	ACountessRebirthFX::Create(Character.Get(), TEXT("B"), Start, Character->GetActorForwardVector(), Echo);
	if (bTransferInferno)
	{
		ReforgeHandoffTimers.RemoveAll([this](const FTimerHandle& Timer) { return !GetWorld()->GetTimerManager().TimerExists(Timer); });
		FTimerHandle Timer;
		GetWorld()->GetTimerManager().SetTimer(Timer, FTimerDelegate::CreateWeakLambda(this,
			[this, InfernoOrigin, InfernoAim, InfernoDirection]()
			{
				ReleaseReforgeSkill(16, InfernoOrigin, InfernoAim, InfernoDirection);
			}), InfernoDelay, false);
		ReforgeHandoffTimers.Add(Timer);
	}
	NextBackstepTime = GetWorld()->GetTimeSeconds() + CursorBlinkCooldown;
	Feedback.Reset();
	SpawnOwnedEffect(GetVisualEffect(EVisualEffect::CloneBurst), GetFeetLocation(), Character->GetActorRotation(), .32f, nullptr, .20f);
	UE_LOG(LogTemp, Display, TEXT("COUNTESS_BACKSTEP distance=%.2f transfer_v=%d delay=%.3f"),
		FVector::Dist2D(Start, Destination), bTransfer, Delay);
	return true;
}

void UCountessSkillComponent::ReleaseAnchoredBladeSiphon(ACountessBackstepEcho* Echo)
{
	if (Echo && BackstepEcho.Get() == Echo && Character.IsValid())
	{
		ReleaseBladeSiphon(Echo->GetActorLocation(), Echo->UsesDetailedSiphon(), Echo->GetSiphonPlayRate());
	}
}

void UCountessSkillComponent::ReleaseBladeSiphon(const FVector& Origin, bool bDetailed, float PlayRate)
{
	if (!Character.IsValid() || !GetWorld() || !Skills.IsValidIndex(1)) { return; }
	const FCountessSkillDefinition& Skill = Skills[1];
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_Pawn);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	FCollisionQueryParams Query(SCENE_QUERY_STAT(CountessBladeSiphon), false, Character.Get());
	TArray<FOverlapResult> Overlaps;
	GetWorld()->OverlapMultiByObjectType(Overlaps, Origin, FQuat::Identity,
		Objects, FCollisionShape::MakeSphere(Skill.Range), Query);
	TSet<AActor*> HitActors;
	for (const FOverlapResult& Overlap : Overlaps)
	{
		AActor* Victim = Overlap.GetActor();
		if (!IsValidSkillTarget(Victim, Character.Get()) || HitActors.Contains(Victim) ||
			FVector::DistSquared2D(Victim->GetActorLocation(), Origin) > FMath::Square(Skill.Range) ||
			FMath::Abs(Victim->GetActorLocation().Z - Origin.Z) > 150.0f) { continue; }
		FCollisionQueryParams Sight(SCENE_QUERY_STAT(CountessSkillSight), false, Character.Get());
		Sight.AddIgnoredActor(Victim);
		FHitResult Block;
		if (GetWorld()->LineTraceSingleByChannel(Block, Origin, Victim->GetActorLocation(), ECC_Visibility, Sight)) { continue; }
		HitActors.Add(Victim);
		const FVector Direction = (Victim->GetActorLocation() - Origin).GetSafeNormal();
		const FHitResult TargetHit(Victim, nullptr, Victim->GetActorLocation(), -Direction);
		UGameplayStatics::ApplyPointDamage(Victim, Skill.Damage, Direction, TargetHit,
			Character->GetController(), Character.Get(), nullptr);
		const bool bDense = bDetailed && CVarCountessWPresentation.GetValueOnGameThread() != 0;
		UParticleSystem* ImpactEffect = bDense && DetailedSiphonImpact ? DetailedSiphonImpact.Get() : Skill.ImpactEffect.Get();
		if (UParticleSystemComponent* Impact = SpawnOwnedEffect(ImpactEffect, Victim->GetActorLocation(),
			Direction.Rotation(), bDense ? 1.2f : 1.0f, Victim))
		{
			Impact->CustomTimeDilation = (bDense ? 0.9f : 1.0f) * PlayRate;
		}
		PlaySkillSound(ESkillSound::Impact, Victim->GetActorLocation(), 0.4f);
	}
}

void UCountessSkillComponent::ClearCursorBlinkVisuals()
{
	for (const TWeakObjectPtr<AActor>& Echo : CursorBlinkEchoes)
	{
		if (Echo.IsValid()) { Echo->Destroy(); }
	}
	for (const TWeakObjectPtr<UParticleSystemComponent>& Effect : CursorBlinkEffects)
	{
		if (Effect.IsValid()) { Effect->DestroyComponent(); }
	}
	CursorBlinkEchoes.Reset();
	CursorBlinkEffects.Reset();
}

bool UCountessSkillComponent::TryUseSkillSlot(int32 Slot, const FVector& AimLocation, AActor* Target)
{
	if (Slot == 17) { return TryBackstep(); }
	if (IsBackstepping()) { return RejectInput(TEXT("Backstepping")); }
	if (Slot == 11) { return TryUseCursorBlink(AimLocation); }
	if (Slot == 1 || Slot == 2 || Slot == 3 || (Slot >= 8 && Slot <= 10) || Slot == 16)
	{
		return TryUseReforgeSkill(Slot, AimLocation);
	}
	return Slot == 0 && TryUseSkill(ECountessSkill::ShadowSlip, AimLocation, Target);
}

FText UCountessSkillComponent::GetSkillDisplayName(int32 Slot) const
{
	if (Slot == 17) { return FText::FromString(TEXT("Crimson Backstep")); }
	if (Slot == 16) { return FText::FromString(TEXT("Crimson Inferno")); }
	if (Slot == 1) { return FText::FromString(TEXT("Crimson Scissors")); }
	if (Slot == 2) { return FText::FromString(TEXT("Abyss Eruption")); }
	if (Slot == 3) { return FText::FromString(TEXT("Impaling Ruin")); }
	const TCHAR* ExtraNames[] = {TEXT("Revolving Shades"), TEXT("Demon Form"), TEXT("Rending Claws"), TEXT("Crimson Blink")};
	if (Slot >= 8 && Slot < 12) { return FText::FromString(ExtraNames[Slot - 8]); }
	return Slot == 0 ? FText::FromString(TEXT("Shadow Slip")) : FText::GetEmpty();
}

ECharacterSkillTargeting UCountessSkillComponent::GetSkillTargeting(int32 Slot) const
{
	if (Slot == 17) { return ECharacterSkillTargeting::Direction; }
	if (Slot == 9 || Slot == 16) { return ECharacterSkillTargeting::Self; }
	if (Slot == 2 || Slot == 11) { return ECharacterSkillTargeting::Ground; }
	return Slot == 0 ? ECharacterSkillTargeting::Actor : ECharacterSkillTargeting::Direction;
}

bool UCountessSkillComponent::IsSkillTargetValid(int32 Slot, const AActor* Target, const AActor* Caster) const
{
	return IsValidSkillTarget(Target, Caster);
}

float UCountessSkillComponent::GetSlotCooldownRemaining(int32 Slot) const
{
	if (Slot == 17)
	{
		return IgnoresCooldowns() || !GetWorld() ? 0.0f :
			static_cast<float>(FMath::Max(0.0, NextBackstepTime - GetWorld()->GetTimeSeconds()));
	}
	if (Slot == 11)
	{
		return IgnoresCooldowns() || !GetWorld() ? 0.0f :
			static_cast<float>(FMath::Max(0.0, NextCursorBlinkTime - GetWorld()->GetTimeSeconds()));
	}
	if (Slot == 1 || Slot == 2 || Slot == 3 || (Slot >= 8 && Slot <= 10) || Slot == 16)
	{
		return IgnoresCooldowns() || !GetWorld() ? 0.0f :
			static_cast<float>(FMath::Max(0.0, ReforgeCooldowns[Slot] - GetWorld()->GetTimeSeconds()));
	}
	return Skills.IsValidIndex(Slot) ? GetCooldownRemaining(static_cast<ECountessSkill>(Slot)) : 0.0f;
}

float UCountessSkillComponent::GetSlotRecastRemaining(int32 Slot) const
{
	return Slot == 0 ? GetReturnRemaining() : 0.0f;
}

FText UCountessSkillComponent::GetSkillStatusText(int32 Slot) const
{
	if (Slot == 17) { return FText::FromString(TEXT("220 cm")); }
	if (Slot == 11) { return FText::FromString(TEXT("750 cm")); }
	if (Slot == 16) { return FText::FromString(TEXT("3.8 s | 12 cuts")); }
	if (Slot == 9) { return FText::FromString(FString::Printf(TEXT("24 s | W/E/R/A/D/V +20%% | %.1f"), GetDemonFormRemaining())); }
	if (Slot == 2) { return FText::FromString(TEXT("240 cm | ground")); }
	return FText::GetEmpty();
}
