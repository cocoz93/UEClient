#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "CharacterSkillComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "CountessSkillComponent.generated.h"

class ATopDownCombatCharacter;
class UAnimSequence;
class UAnimMontage;
class UParticleSystem;
class UParticleSystemComponent;
class UMaterialInterface;
class UStaticMesh;
class USoundBase;
class USkeletalMeshComponent;
class UAudioComponent;
class ACountessSkillLensEffect;
class ACountessExtraVisual;
class ACountessBackstepEcho;
class ACountessDemonForm;
enum class ECountessExtraVisual : uint8;

UENUM(BlueprintType)
enum class ECountessSkill : uint8
{
	ShadowSlip,
	BladeSiphon,
	DarkTide,
	Feast
};

USTRUCT(BlueprintType)
struct FCountessSkillDefinition
{
	GENERATED_BODY()

	UPROPERTY(EditDefaultsOnly)
	FName Name;
	UPROPERTY(EditDefaultsOnly)
	TObjectPtr<UAnimSequence> Animation;
	UPROPERTY(EditDefaultsOnly)
	TObjectPtr<UParticleSystem> CastEffect;
	UPROPERTY(EditDefaultsOnly)
	TObjectPtr<UParticleSystem> ImpactEffect;
	UPROPERTY(EditDefaultsOnly)
	TObjectPtr<USoundBase> CastSound;
	UPROPERTY(EditDefaultsOnly, meta = (ClampMin = "0.0"))
	float Damage = 0.0f;
	UPROPERTY(EditDefaultsOnly, meta = (ClampMin = "0.0", Units = "s"))
	float Cooldown = 8.0f;
	UPROPERTY(EditDefaultsOnly, meta = (ClampMin = "1.0", Units = "cm"))
	float Range = 500.0f;
	UPROPERTY(EditDefaultsOnly, meta = (ClampMin = "0.01", Units = "s"))
	float ActionTime = 0.2f;
	UPROPERTY(EditDefaultsOnly, meta = (ClampMin = "0.01", Units = "s"))
	float RecoveryTime = 0.65f;
};

// 카운테스 스킬만 소유한다. 기존 평타의 콤보 타이머와 이동 설정은 별도로 유지한다.
UCLASS(ClassGroup = (Combat), meta = (BlueprintSpawnableComponent))
class LEARNTOPDOWN_API UCountessSkillComponent : public UCharacterSkillComponent
{
	GENERATED_BODY()

public:
	UCountessSkillComponent();
	UFUNCTION(BlueprintCallable, Category = "Skills")
	bool TryUseSkill(ECountessSkill Skill, const FVector& AimLocation, AActor* Target);
	virtual bool IsCasting() const override { return bCasting || bReforgeCasting || IsBackstepping(); }
	virtual bool IsEnabled() const override { return bEnabled; }
	virtual int32 GetActiveSkillNumber() const override { return IsBackstepping() ? 18 : (bReforgeCasting ? ReforgeSlot + 1 : (bCasting ? ActiveSkillIndex + 1 : 0)); }
	UFUNCTION(BlueprintPure, Category = "Skills")
	bool IsReforgeCasting() const { return bReforgeCasting; }
	UFUNCTION(BlueprintPure, Category = "Skills")
	float GetDemonFormRemaining() const;
	UFUNCTION(BlueprintPure, Category = "Skills")
	bool IsBackstepping() const;
	UFUNCTION(BlueprintPure, Category = "Skills")
	float GetCooldownRemaining(ECountessSkill Skill) const;
	UFUNCTION(BlueprintPure, Category = "Skills")
	float GetReturnRemaining() const;
	virtual FString GetInputFeedback() const override;
	virtual bool IgnoresCooldowns() const override;
	const FCountessSkillDefinition* GetDefinition(ECountessSkill Skill) const;
	UFUNCTION(BlueprintPure, Category = "Skills")
	float GetSkillPlayRate(ECountessSkill Skill) const;
	UFUNCTION(BlueprintPure, Category = "Skills")
	float GetSkillStartTime(ECountessSkill Skill) const;
	virtual void CancelSkill() override;
	virtual bool TryUseSkillSlot(int32 Slot, const FVector& AimLocation, AActor* Target) override;
	virtual int32 GetSkillCount() const override { return 18; }
	virtual bool PlacesLetterKeysOnLeftHud() const override { return true; }
	virtual FText GetSkillDisplayName(int32 Slot) const override;
	virtual FText GetSkillStatusText(int32 Slot) const override;
	UFUNCTION(BlueprintPure, Category = "Skills")
	bool IsFlurryPrototypeEnabled() const { return bEFlurryPrototype; }
	virtual ECharacterSkillTargeting GetSkillTargeting(int32 Slot) const override;
	virtual bool IsSkillTargetValid(int32 Slot, const AActor* Target, const AActor* Caster) const override;
	virtual float GetSlotCooldownRemaining(int32 Slot) const override;
	virtual float GetSlotRecastRemaining(int32 Slot) const override;
	static bool IsValidSkillTarget(const AActor* Target, const AActor* Caster);
	static bool UsesDetailedPresentation();
	static bool UsesSkillAudio();
	static bool UsesSkillVoice();
	static bool UsesQSwordAudio();
	static bool UsesQRushAudio();
	static UParticleSystemComponent* SpawnEffect(UWorld* World, UParticleSystem* Effect, const FVector& Location,
		const FRotator& Rotation, float Scale = 1.0f, AActor* SourceActor = nullptr,
		float Lifetime = 3.0f, bool bAttachToSource = false);

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	UPROPERTY(EditDefaultsOnly, Category = "Skills")
	TArray<FCountessSkillDefinition> Skills;

private:
	struct FReforgePulse
	{
		double Due = 0.0;
		FVector Center = FVector::ZeroVector;
		FVector CastOrigin = FVector::ZeroVector;
		FVector Direction = FVector::ForwardVector;
		float Radius = 0.0f;
		float Damage = 0.0f;
		float HalfWidth = 0.0f;
		TWeakObjectPtr<AActor> FollowField;
		TSharedPtr<TSet<TWeakObjectPtr<AActor>>> SharedHits;
	};
	bool TryUseReforgeSkill(int32 Slot, const FVector& AimLocation);
	bool TryUseCursorBlink(const FVector& AimLocation);
	void CommitReforgeSkill();
	void ReleaseReforgeSkill(int32 Slot, const FVector& Origin, const FVector& Aim, const FVector& Direction);
	void TickReforgeSkills(float DeltaTime);
	void FinishReforgeCast();
	void CleanupReforgeSkills();
	void ApplyReforgePulse(const FReforgePulse& Pulse);
	bool FindReforgeGround(const FVector& AimLocation, float Range, FVector& Ground) const;
	bool IsReforgePathClear(const FVector& Start, const FVector& End) const;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UAnimMontage>> ReforgeMontages;
	UPROPERTY(Transient)
	TObjectPtr<UAnimMontage> ReforgeMontage;
	TWeakObjectPtr<UAnimInstance> ReforgeAnim;
	TWeakObjectPtr<ACountessDemonForm> DemonForm;
	TArray<TWeakObjectPtr<AActor>> ReforgeVisuals;
	TArray<FReforgePulse> ReforgePulses;
	TArray<FTimerHandle> ReforgeHandoffTimers;
	double ReforgeCooldowns[18] = {};
	double ReforgeStartedAt = 0.0;
	float ReforgeCommitTime = 0.0f;
	float ReforgeDuration = 0.0f;
	float ReforgePlayRate = 1.0f;
	int32 ReforgeSlot = INDEX_NONE;
	bool bReforgeCasting = false;
	bool bReforgeCommitted = false;
	bool bReforgeSavedOrient = true;
	ERootMotionMode::Type ReforgeSavedRootMotion = ERootMotionMode::RootMotionFromMontagesOnly;
	FVector ReforgeMeshLocation = FVector::ZeroVector;
	FVector ReforgeOrigin = FVector::ZeroVector;
	FVector ReforgeAim = FVector::ZeroVector;
	FVector ReforgeDirection = FVector::ForwardVector;
	enum class EVisualEffect : uint8
	{
		BlinkFlash, BlinkSlash, CloneBurst, ReturnDeparture, TideGround,
		FeastEyes, FeastSlash, FeastGround, FeastImpact, MeleeTrail, FeastTarget,
		BlinkAim, SmokeyBlade, FeastBind, FeastTargetRemove, FeastEyeBurst, TideAim,
		BlinkLensStart, BlinkLensReturn, BlinkLensDuration, TideLens,
		Count
	};
	enum class EVisualCue : uint8 { QDualSweep, StartTrails, EndTrails, BladeSpin, BladeEcho, TideGround, FeastCast, FeastSlash };
	enum class ESkillSound : uint8 { Blink, Blade, Tide, FeastCharge, FeastHit, Impact, QSlash, QHit, QRush, QRushSlash, QRushHit, Count };
	void PlaySkillSound(ESkillSound Sound, const FVector& Location, float Volume = 0.7f, bool bFollowCharacter = false);
	ACountessSkillLensEffect* SpawnLensEffect(EVisualEffect Effect, float Lifetime);
	void StartSkillVisuals();
	void ScheduleVisualCue(float Delay, EVisualCue Cue);
	void PlayVisualCue(EVisualCue Cue);
	void SpawnBladeShadowEcho();
	void StartWeaponTrails(USkeletalMeshComponent* TargetMesh = nullptr);
	void StopWeaponTrails();
	void StopCastVisuals();
	AActor* SpawnSkeletalProxy(float Lifetime, bool bShadowClone);
	UParticleSystemComponent* SpawnOwnedEffect(UParticleSystem* Effect, const FVector& Location,
		const FRotator& Rotation, float Scale = 1.0f, AActor* SourceActor = nullptr,
		float Lifetime = 3.0f, bool bAttachToSource = false);
	UParticleSystem* GetVisualEffect(EVisualEffect Effect) const;
	bool RejectInput(const TCHAR* Reason);
	bool HasLineOfSight(AActor* Target) const;
	bool FindLandingPoint(const FVector& FeetLocation, FVector& Result) const;
	bool FindTargetLanding(AActor* Target, FVector& Result) const;
	bool IsBlinkPathClear(const FVector& Destination, AActor* IgnoreTarget = nullptr) const;
	bool FindCursorBlinkLanding(const FVector& AimLocation, FVector& Result) const;
	bool TryBackstep();
	friend class ACountessBackstepEcho;
	void ReleaseAnchoredBladeSiphon(ACountessBackstepEcho* Echo);
	void ReleaseBladeSiphon(const FVector& Origin, bool bDetailed, float PlayRate);
	void SpawnCursorBlinkEchoes(const FVector& Origin, const FVector& Destination, const FTransform& SourceMeshTransform);
	void ClearCursorBlinkVisuals();
	bool TryReturn();
	bool BeginSkill(int32 SkillIndex, const FVector& AimLocation, AActor* Target, bool bReturn);
	void ExecuteAction();
	void InitializeExtraDefinitions();
	void CreateExtraMontages();
	bool TryUseExtraSkill(int32 ExtraIndex, const FVector& AimLocation, AActor* Target);
	bool FindExtraRushLanding(const FVector& AimLocation, FVector& Result) const;
	bool FindExtraAmbushLanding(const FVector& AimLocation, AActor* Target, FVector& Result) const;
	void DamageExtraTarget(AActor* Target, float Damage, UParticleSystem* ImpactEffect);
	ACountessExtraVisual* SpawnExtraVisual(ECountessExtraVisual Kind, const FVector& Location, const FVector& Direction,
		float Lifetime, AActor* Follow = nullptr);
	void SpawnExtraRushEcho(const FVector& Location);
	void ExecuteExtraAction();
	void ExecuteExtraFollowup();
	void UpdateExtraRush();
	void DamageExtraRushSegment(const FVector& Start, const FVector& End);
	void ClearExtraCast();
	void ClearExtraWorldEffects();
	void RetireExtraAmbush();
	UParticleSystemComponent* SpawnExtraEffect(UParticleSystem* Effect, const FVector& Location,
		const FRotator& Rotation, float Scale = 1.0f, AActor* SourceActor = nullptr,
		float Lifetime = 1.0f, bool bAttachToSource = false);
	bool CreateFlurryMontages();
	bool SpawnFlurryShadow();
	void RetireFlurryShadow();
	bool ValidateFlurryTarget() const;
	void PlayFlurryStrike(int32 Index);
	void HitFlurryTarget();
	void SpawnFlurryTargetCuts(AActor* Target);
	UParticleSystemComponent* SpawnFlurryEffect(UParticleSystem* Effect, const FVector& Location,
		const FRotator& Rotation, float Scale, AActor* SourceActor, float Lifetime);
	void StopFlurryEffects();
	void StartFeastStun();
	bool FindFeastLanding(AActor* Target, FVector& Result) const;
	void ApproachFeast();
	void UpdateFeastApproach();
	void RestoreTargetMovement();
	void RestoreSlow();
	void ExpireReturn();
	void FinishSkill();
	void OnMontageEnded(UAnimMontage* Montage, bool bInterrupted, uint32 Generation);
	void OnMontageBlendingOut(UAnimMontage* Montage, bool bInterrupted, uint32 Generation);
	void DamageTarget(AActor* Target, float Damage, UParticleSystem* ImpactEffect);
	void ApplyShadowSlow(AActor* Target);
	void SpawnBlinkImpactAccent(AActor* Target);
	void SpawnBlinkDualSweep(bool bAtImpact);
	FVector GetFeetLocation() const;

	TWeakObjectPtr<ATopDownCombatCharacter> Character;
	TWeakObjectPtr<UAnimInstance> CastAnimInstance;
	TWeakObjectPtr<ACountessBackstepEcho> BackstepEcho;
	UPROPERTY(Transient)
	TObjectPtr<UAnimMontage> BackstepMontage;
	TWeakObjectPtr<AActor> CastTarget;
	TWeakObjectPtr<UCharacterMovementComponent> StunnedMovement;
	TWeakObjectPtr<UCharacterMovementComponent> SlowedMovement;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UAnimMontage>> SkillMontages;
	UPROPERTY()
	TArray<TObjectPtr<UAnimSequence>> FlurrySources;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UAnimMontage>> FlurryMontages;
	bool bEFlurryPrototype = false;
	int32 FlurryStrikeIndex = 0;
	double FlurryStartedAt = 0.0;
	FTimerHandle FlurryStrikeTimer;
	TWeakObjectPtr<AActor> FlurryShadow;
	TArray<TWeakObjectPtr<UParticleSystemComponent>> FlurryEffects;
	UPROPERTY()
	TSoftObjectPtr<UMaterialInterface> FlurryShadowDissolveMaterial;
	UPROPERTY()
	TSoftObjectPtr<UMaterialInterface> FlurryBladeMaterial;
	UPROPERTY()
	TSoftObjectPtr<UParticleSystem> FlurryBladeEffect;
	UPROPERTY()
	TSoftObjectPtr<UMaterialInterface> FlurryTargetCutMaterial;
	UPROPERTY(Transient)
	TObjectPtr<UAnimMontage> ActiveMontage;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystemComponent> ReturnMarker;
	UPROPERTY()
	TObjectPtr<UParticleSystem> ReturnEffect;
	UPROPERTY()
	TObjectPtr<UParticleSystem> SiphonTrails;
	UPROPERTY()
	TObjectPtr<UParticleSystem> DetailedSiphonRing;
	UPROPERTY()
	TObjectPtr<UParticleSystem> RimSiphonRing;
	UPROPERTY()
	TObjectPtr<UParticleSystem> SpiralSiphonRing;
	UPROPERTY()
	TSoftObjectPtr<UParticleSystem> LightSiphonRing;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> LoadedLightSiphonRing;
	UPROPERTY()
	TObjectPtr<UParticleSystem> DetailedSiphonTrails;
	UPROPERTY()
	TObjectPtr<UParticleSystem> DetailedSiphonImpact;
	UPROPERTY()
	TObjectPtr<UParticleSystem> TideEffect;
	UPROPERTY()
	TObjectPtr<UParticleSystem> DetailedTideEffect;
	UPROPERTY()
	TObjectPtr<UParticleSystem> TeleportArrivalEffect;
	UPROPERTY()
	TObjectPtr<UParticleSystem> FeastApplicationEffect;
	UPROPERTY()
	TArray<TObjectPtr<UParticleSystem>> VisualEffects;
	UPROPERTY()
	TObjectPtr<UMaterialInterface> ShadowCloneMaterial;
	UPROPERTY()
	TObjectPtr<UMaterialInterface> BlinkAccentMaterial;
	UPROPERTY()
	TObjectPtr<UStaticMesh> BlinkAccentMesh;
	UPROPERTY()
	TObjectPtr<UMaterialInterface> DualSweepMaterial;
	UPROPERTY()
	TObjectPtr<UStaticMesh> DualSweepMesh;
	UPROPERTY()
	TObjectPtr<UMaterialInterface> OutwardCutMaterial;
	UPROPERTY()
	TSoftObjectPtr<UMaterialInterface> CompactOutwardCutMaterial;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> LoadedCompactOutwardCutMaterial;
	UPROPERTY()
	TObjectPtr<UStaticMesh> OutwardCutMesh;
	UPROPERTY()
	TObjectPtr<UMaterialInterface> DetailedCloneMaterial;
	UPROPERTY()
	TArray<TObjectPtr<USoundBase>> CombatSounds;
	UPROPERTY()
	TObjectPtr<UAnimSequence> ShadowCloneIdle;
	UPROPERTY(Transient)
	TObjectPtr<AActor> ReturnClone;
	TArray<TWeakObjectPtr<UParticleSystemComponent>> OwnedEffects;
	TArray<TWeakObjectPtr<UParticleSystemComponent>> WeaponTrails;
	TArray<TWeakObjectPtr<UParticleSystemComponent>> CastBoundEffects;
	TArray<TWeakObjectPtr<AActor>> VisualProxies;
	TArray<TWeakObjectPtr<ACountessSkillLensEffect>> LensEffects;
	TWeakObjectPtr<ACountessSkillLensEffect> ReturnLens;
	TWeakObjectPtr<UAudioComponent> CastAudio;
	TArray<TWeakObjectPtr<UAudioComponent>> EffectAudio;
	TArray<FTimerHandle> VisualTimers;

	UPROPERTY()
	TArray<FCountessSkillDefinition> ExtraSkills;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UAnimMontage>> ExtraMontages;
	UPROPERTY()
	TObjectPtr<UParticleSystem> ExtraSealBurst;
	UPROPERTY()
	TObjectPtr<UAnimSequence> ExtraAmbushAttackAnimation;
	TArray<TWeakObjectPtr<UParticleSystemComponent>> ExtraOwnedEffects;
	TArray<TWeakObjectPtr<AActor>> ExtraActors;
	TWeakObjectPtr<UParticleSystemComponent> ExtraSealMarker;
	TWeakObjectPtr<AActor> ExtraAmbushShadow;
	TWeakObjectPtr<ACountessExtraVisual> ExtraSealVisual;
	TWeakObjectPtr<ACountessExtraVisual> ExtraRushVisual;
	TWeakObjectPtr<ACountessExtraVisual> ExtraAmbushVisual;
	int32 ExtraRushEchoes = 0;
	int32 ExtraImpactVisuals = 0;
	double ExtraCastStartedAt = 0.0;
	bool bExtraAmbushStrikeStarted = false;
	TSet<TWeakObjectPtr<AActor>> ExtraRushHits;
	FTimerHandle ExtraFollowupTimer;
	double NextExtraSkillTimes[4] = {};
	double ExtraRushStartedAt = 0.0;
	FVector ExtraLanding = FVector::ZeroVector;
	FVector ExtraRushOrigin = FVector::ZeroVector;
	bool bExtrasReady = false;
	bool bExtraRushActive = false;
	bool bExtraFollowupExecuted = false;

	double NextSkillTimes[4] = {};
	double NextCursorBlinkTime = 0.0;
	double NextBackstepTime = 0.0;
	TArray<TWeakObjectPtr<AActor>> CursorBlinkEchoes;
	TArray<TWeakObjectPtr<UParticleSystemComponent>> CursorBlinkEffects;
	double ReturnDeadline = 0.0;
	double FeedbackDeadline = 0.0;
	FString Feedback;
	FVector ReturnLocation = FVector::ZeroVector;
	FRotator ReturnRotation = FRotator::ZeroRotator;
	FVector CastAim = FVector::ZeroVector;
	FVector CastOrigin = FVector::ZeroVector;
	FVector FeastApproachOrigin = FVector::ZeroVector;
	FVector FeastLandingLocation = FVector::ZeroVector;
	double FeastApproachStartedAt = 0.0;
	bool bFeastApproaching = false;
	bool bFeastArrived = false;
	bool bEnabled = false;
	bool bCasting = false;
	bool bActionExecuted = false;
	bool bReturning = false;
	bool bDetailedCast = false;
	bool bWShadowPreview = false;
	bool bSavedOrientRotation = true;
	int32 ActiveSkillIndex = INDEX_NONE;
	uint32 CastGeneration = 0;
	ERootMotionMode::Type SavedRootMotionMode = ERootMotionMode::RootMotionFromMontagesOnly;
	EMovementMode SavedTargetMovementMode = MOVE_Walking;
	uint8 SavedTargetCustomMode = 0;
	float SavedTargetSpeed = 0.0f;
	float AppliedTargetSpeed = 0.0f;
	float ActivePlayRate = 1.0f;
	float ActiveStartTime = 0.0f;
	FTimerHandle ActionTimer;
	FTimerHandle RecoveryTimer;
	FTimerHandle StunStartTimer;
	FTimerHandle FeastArrivalTimer;
	FTimerHandle StunEndTimer;
	FTimerHandle SlowTimer;
	FTimerHandle ReturnTimer;
};
