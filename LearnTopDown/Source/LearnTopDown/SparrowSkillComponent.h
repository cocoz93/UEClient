#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "CharacterSkillComponent.h"
#include "SparrowSkillComponent.generated.h"

class ATopDownCombatCharacter;
class ASparrowArrow;
class ASparrowBowFeedback;
class ASparrowHolyBow;
class ASparrowAscendedShotFX;
class ASparrowMultishotBowTint;
class ASparrowAscensionWings;
class ASparrowMirrorArcher;
class ASparrowBackstepEcho;
class ASparrowGoldRoll;
class ASparrowSanctuary;
class ASparrowSharpVolley;
class ASparrowGatherShot;
class ASparrowBowMuzzleStudy;
class ASparrowFlameStudies;
class UAnimSequence;
class UAnimMontage;
class UParticleSystem;
class UParticleSystemComponent;
class USoundBase;
class UStaticMesh;
class UMaterialInterface;
class UMaterialInstanceDynamic;

UENUM(BlueprintType)
enum class ESparrowSkill : uint8
{
	HailOfArrows = 0,
	PiercingShot = 1,
	Relentless = 2 UMETA(DisplayName = "Rapid Shot"),
	InnerFire = 3
};

USTRUCT(BlueprintType)
struct FSparrowSkillDefinition
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere)
	FName Name;
	UPROPERTY(EditAnywhere)
	TObjectPtr<UAnimSequence> Animation;
	UPROPERTY(EditAnywhere)
	TObjectPtr<UParticleSystem> CastEffect;
	UPROPERTY(EditAnywhere)
	TObjectPtr<UParticleSystem> ImpactEffect;
	UPROPERTY(EditAnywhere)
	TObjectPtr<USoundBase> CastSound;
	UPROPERTY(EditAnywhere, meta = (ClampMin = "0.0"))
	float Damage = 0.0f;
	UPROPERTY(EditAnywhere, meta = (ClampMin = "0.0", Units = "s"))
	float Cooldown = 0.0f;
	UPROPERTY(EditAnywhere, meta = (ClampMin = "0.0", Units = "cm"))
	float Range = 0.0f;
	UPROPERTY(EditAnywhere, meta = (ClampMin = "0.0", Units = "s"))
	float ActionTime = 0.0f;
	UPROPERTY(EditAnywhere, meta = (ClampMin = "0.0", Units = "s"))
	float RecoveryTime = 0.0f;
};

// 원본 Q/RMB/R과 단발 E를 소유한다. 원본 누적 피해 패시브는 평타와 E에 유지한다.
UCLASS(ClassGroup = (Combat), meta = (BlueprintSpawnableComponent))
class LEARNTOPDOWN_API USparrowSkillComponent : public UCharacterSkillComponent
{
	GENERATED_BODY()

public:
	USparrowSkillComponent();
	UFUNCTION(BlueprintCallable, Category = "Skills")
	bool TryUseSkill(ESparrowSkill Skill, const FVector& AimLocation, AActor* Target);
	virtual bool TryUseSkillSlot(int32 Slot, const FVector& AimLocation, AActor* Target) override;
	virtual bool IsCasting() const override { return bCasting || IsBackstepping() || IsRolling() || IsSanctuaryCasting(); }
	// 유효한 이동 입력이 예약됐을 때만, 발사 이후 회복 자세의 잠금을 해제한다.
	void FinishRecoveryForMovement();
	virtual bool IsEnabled() const override { return bEnabled; }
	virtual int32 GetActiveSkillNumber() const override { return IsRolling() ? 18 : (IsSanctuaryCasting() ? GetSanctuaryActiveSlot() + 1 : (bCasting ? (ActiveSkillIndex == 9 ? 17 : ActiveSkillIndex + 1) : 0)); }
	virtual int32 GetSkillCount() const override { return 18; }
	virtual bool PlacesLetterKeysOnLeftHud() const override { return true; }
	virtual FText GetSkillDisplayName(int32 Slot) const override;
	virtual ECharacterSkillTargeting GetSkillTargeting(int32 Slot) const override;
	virtual bool IsSkillPassive(int32 Slot) const override { return false; }
	virtual FText GetSkillStatusText(int32 Slot) const override;
	virtual float GetSlotCooldownRemaining(int32 Slot) const override;
	virtual FString GetInputFeedback() const override;
	virtual bool IgnoresCooldowns() const override;
	virtual void CancelSkill() override;
	UFUNCTION(BlueprintPure, Category = "Skills")
	float GetCooldownRemaining(ESparrowSkill Skill) const;
	UFUNCTION(BlueprintCallable, Category = "Combat")
	bool FireBasicAttack(const FVector& Direction);
	UFUNCTION(BlueprintCallable, Category = "Combat")
	bool FireBasicAttackAt(const FVector& AimLocation);
	UFUNCTION(BlueprintPure, Category = "Combat")
	FVector GetArrowOrigin() const;
	UFUNCTION(BlueprintPure, Category = "Skills")
	bool IsInnerFireActive() const;
	UFUNCTION(BlueprintPure, Category = "Skills")
	float GetBuffRemaining() const;
	UFUNCTION(BlueprintPure, Category = "Skills")
	int32 GetRelentlessStacks(AActor* Target) const;
	UFUNCTION(BlueprintPure, Category = "Skills")
	int32 GetActiveHailCount() const { return HailZones.Num(); }
	float ModifyArrowDamageAndRecordHit(AActor* Target, float BaseDamage);
	void RecordRelentlessHit(AActor* Target);
	const FSparrowSkillDefinition* GetDefinition(ESparrowSkill Skill) const;
	UAnimMontage* GetInnerFireAttackMontage() const;
	void SpawnExtraArrowHitVisual(const FVector& Location, const FVector& Direction, bool bChain = false, int32 HitOrdinal = 0);
	UFUNCTION(BlueprintPure, Category = "Skills")
	float GetAscensionRemaining() const;
	UFUNCTION(BlueprintPure, Category = "Skills")
	float GetMirrorRemaining() const;
	UFUNCTION(BlueprintPure, Category = "Skills")
	bool IsBackstepping() const;
	UFUNCTION(BlueprintPure, Category = "Skills")
	bool IsRolling() const;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
	UPROPERTY(EditDefaultsOnly, Category = "Skills")
	TArray<FSparrowSkillDefinition> Skills;
	// 기존 BP의 QWER 4칸과 A/V/D 정의를 유지한다. S/F와 Space 구르기는 독립 상태로 소유한다.
	UPROPERTY(EditDefaultsOnly, Category = "Skills")
	TArray<FSparrowSkillDefinition> ExtraSkills;
	UPROPERTY(EditDefaultsOnly, Category = "Animation")
	FName FullBodySlot = TEXT("SparrowFullBody");
	UPROPERTY(EditDefaultsOnly, Category = "Combat", meta = (ClampMin = "0.0"))
	float BasicAttackDamage = 20.0f;
	UPROPERTY(EditDefaultsOnly, Category = "Combat", meta = (ClampMin = "1.0", Units = "cm"))
	float BasicAttackRange = 1800.0f;
	UPROPERTY(EditDefaultsOnly, Category = "Combat", meta = (ClampMin = "1.0", Units = "cm/s"))
	float ArrowSpeed = 3000.0f;

private:
	friend class ASparrowSanctuary;
	friend class ASparrowSharpVolley;
	bool TryUseSanctuarySkill(int32 Slot, const FVector& AimLocation, AActor* Target);
	bool IsSanctuaryCasting() const;
	int32 GetSanctuaryActiveSlot() const;
	float GetSanctuaryCooldownRemaining(int32 Slot) const;
	FText GetSanctuaryName(int32 Slot) const;
	FText GetSanctuaryStatus(int32 Slot) const;
	void CancelSanctuaryCast();
	void CleanupSanctuarySkills();
	TWeakObjectPtr<ASparrowSanctuary> SanctuaryCast;
	TWeakObjectPtr<ASparrowSharpVolley> SharpVolley;
	TWeakObjectPtr<ASparrowSanctuary> CounterBarrier;
	double NextSanctuarySkillTimes[2] = {};
	friend class ASparrowMirrorArcher;
	friend class ASparrowBackstepEcho;
	bool TryBackstep();
	bool TryRoll(const FVector& AimLocation);
	void ReleaseAnchoredPiercingShot(ASparrowBackstepEcho* Echo);
	void ReleasePiercingShot(const FVector& Origin, const FVector& Aim, float DamageScale = 1.0f, bool bFinisher = false);
	TWeakObjectPtr<ASparrowBackstepEcho> BackstepEcho;
	UPROPERTY(Transient)
	TObjectPtr<UAnimMontage> BackstepMontage;
	double NextBackstepTime = 0.0;
	TWeakObjectPtr<ASparrowGoldRoll> GoldRoll;
	double NextRollTime = 0.0;
	void InitializeExtraSkills();
	void CreateExtraMontages();
	const FSparrowSkillDefinition* GetSlotDefinition(int32 Slot) const;
	UAnimMontage* GetSlotMontage(int32 Slot) const;
	bool TryUseExtraSkill(int32 Slot, const FVector& AimLocation, AActor* Target);
	bool FindExtraGround(const FVector& Aim, float Range, FVector& Ground, AActor* Target = nullptr) const;
	void ExecuteExtraAction(uint32 Generation);
	void PrepareExtraPresentation(int32 Slot, float ActionSeconds);
	ASparrowArrow* SpawnAscensionArrow(const FVector& Origin, const FVector& Direction, float Damage, bool bGear, bool bAllowMirrors = true);
	void EchoArrowShot(const FVector& Direction, float Damage, float Range, float Speed,
		bool bPiercing, bool bPassesWorld, bool bUltimate, TSharedPtr<TSet<TWeakObjectPtr<AActor>>> VolleyHits = nullptr);
	void EchoHail(const FVector& Location);
	void EchoAscensionArrow(const FVector& Direction, float Damage);
	bool FindMirrorLocations(const FVector& Facing, FVector& Left, FVector& Right) const;
	void CancelExtraCast();
	void CleanupExtraSkills();
	UPROPERTY(Transient)
	TArray<TObjectPtr<UAnimMontage>> ExtraMontages;
	TWeakObjectPtr<ASparrowAscensionWings> AscensionWings;
	TArray<TWeakObjectPtr<ASparrowMirrorArcher>> PendingMirrorArchers;
	TArray<TWeakObjectPtr<ASparrowMirrorArcher>> ActiveMirrorArchers;
	double ExtraNextSkillTimes[4] = {};
	TWeakObjectPtr<ASparrowGatherShot> GatherShot;
	TWeakObjectPtr<ASparrowBowMuzzleStudy> BowMuzzleStudy;
	TWeakObjectPtr<ASparrowFlameStudies> FlameStudy;

	ASparrowBowFeedback* SpawnBowFeedback(bool bRapid);
	TWeakObjectPtr<ASparrowBowFeedback> RapidBowFeedback;
	TWeakObjectPtr<ASparrowHolyBow> HolyBow;
	TWeakObjectPtr<ASparrowAscendedShotFX> AscendedBowFX;
	TWeakObjectPtr<class ASparrowArsenalStudyFX> ArsenalStudyFX;
	TWeakObjectPtr<ASparrowMultishotBowTint> MultishotBowTint;
	struct FRelentlessState
	{
		int32 Stacks = 0;
		double Deadline = 0.0;
	};
	struct FHailZone
	{
		uint32 Id = 0;
		FVector Location = FVector::ZeroVector;
		double Deadline = 0.0;
		float DamagePerPulse = 0.0f;
		float Radius = 300.0f;
		int32 PulsesRemaining = 8;
		bool bMirrored = false;
		bool bAscended = false;
		FTimerHandle Timer;
		TArray<TWeakObjectPtr<UParticleSystemComponent>> Effects;
		TWeakObjectPtr<AActor> RangeIndicator;
		TWeakObjectPtr<UMaterialInstanceDynamic> RangeIndicatorMaterial;
	};
	bool RejectInput(const TCHAR* Reason);
	bool ValidateCastState() const;
	bool HasRapidShotMovePress();
	bool FindHailLocation(const FVector& Aim, AActor* AimTarget, FVector& Result) const;
	bool HasWorldLineOfSight(const FVector& From, const FVector& To, AActor* Target = nullptr) const;
	UAnimMontage* CreateChargeMontage(bool bFinisher = false);
	UPROPERTY(Transient)
	TObjectPtr<UAnimMontage> AscendedChargeMontage;
	bool bPiercingAscendedCast = false;
	UAnimMontage* CreateHolyShotMontage();
	UAnimMontage* CreateMultishotMontage();
	UParticleSystem* CreateRuntimeHailEffect();
	bool BeginSkill(int32 Slot, const FVector& Aim);
	void ExecuteAction(uint32 Generation);
	void FireHolyArrow(uint32 Generation);
	void FireMultishotWave(uint32 Generation, int32 WaveIndex);
	void FirePiercingBurst(uint32 Generation, int32 ShotIndex);
	double PiercingStartedAt = 0.0;
	void FinishSkill(float BlendOutSeconds = -1.0f);
	double MovementReadyAt = TNumericLimits<double>::Max();
	void OnMontageEnded(UAnimMontage* Montage, bool bInterrupted, uint32 Generation);
	void OnMontageBlendingOut(UAnimMontage* Montage, bool bInterrupted, uint32 Generation);
	void StartHail(const FVector& Location, float DamageScale = 1.0f, bool bEchoAllowed = true);
	void SpawnHailLaunch(const FVector* OriginOverride = nullptr);
	void PulseHail(uint32 ZoneId);
	void RemoveHail(uint32 ZoneId);
	void ExpireInnerFire();
	void CleanupRelentless();
	ASparrowArrow* SpawnArrow(const FVector& Direction, float Damage, float Range, float Speed,
		bool bPiercing, bool bPassesWorld, bool bApplyRelentlessBonus, bool bUltimate,
		const FVector* OriginOverride = nullptr, bool bEchoAllowed = true,
		TSharedPtr<TSet<TWeakObjectPtr<AActor>>> VolleyHits = nullptr);
	UParticleSystemComponent* SpawnEffect(UParticleSystem* Effect, const FVector& Location,
		const FRotator& Rotation, float Lifetime, bool bAttach = false, float Scale = 1.0f, FName Socket = NAME_None);
	void StopCastEffects();

	TWeakObjectPtr<ATopDownCombatCharacter> Character;
	TWeakObjectPtr<UAnimInstance> CastAnimInstance;
	TWeakObjectPtr<AActor> LastRelentlessTarget;
	TArray<TWeakObjectPtr<ASparrowArrow>> OwnedArrows;
	TArray<TWeakObjectPtr<AActor>> VisualProxies;
	TArray<TWeakObjectPtr<UParticleSystemComponent>> OwnedEffects;
	TArray<TWeakObjectPtr<UParticleSystemComponent>> CastEffects;
	TWeakObjectPtr<UParticleSystemComponent> BuffEffect;
	TWeakObjectPtr<UParticleSystemComponent> RapidBowEffect;
	TMap<TWeakObjectPtr<AActor>, FRelentlessState> RelentlessTargets;
	TArray<FHailZone> HailZones;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UAnimMontage>> SkillMontages;
	UPROPERTY(Transient)
	TObjectPtr<UAnimMontage> ActiveMontage;
	UPROPERTY()
	TObjectPtr<UAnimSequence> ChargeLoop;
	UPROPERTY()
	TObjectPtr<UAnimSequence> ChargeFire;
	UPROPERTY()
	TObjectPtr<UParticleSystem> PrimaryTrail;
	UPROPERTY()
	TObjectPtr<UParticleSystem> PrimaryHit;
	UPROPERTY()
	TObjectPtr<UParticleSystem> PrimaryWorldHit;
	UPROPERTY()
	TObjectPtr<UParticleSystem> PrimaryMuzzle;
	UPROPERTY()
	TObjectPtr<UParticleSystem> UltimateTrail;
	UPROPERTY()
	TObjectPtr<UParticleSystem> UltimateWorldHit;
	UPROPERTY()
	TObjectPtr<UParticleSystem> HailProjectile;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> RuntimeHailEffect;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> RuntimeRapidBowEffect;
	UPROPERTY()
	TObjectPtr<UStaticMesh> HailRangeMesh;
	UPROPERTY()
	TSoftObjectPtr<UMaterialInterface> HailRangeMaterial;
	UPROPERTY()
	TObjectPtr<UParticleSystem> InnerFireEffect;
	FVector CastAim = FVector::ZeroVector;
	TOptional<FVector> MirrorAimLocation;
	double NextSkillTimes[4] = {};
	double BuffDeadline = 0.0;
	double FeedbackDeadline = 0.0;
	FString Feedback;
	bool bEnabled = false;
	bool bCasting = false;
	bool bActionExecuted = false;
	bool bSavedOrientRotation = true;
	bool bRapidMoveWasDown = false;
	int32 ActiveSkillIndex = INDEX_NONE;
	uint32 CastGeneration = 0;
	uint32 HailGeneration = 0;
	ERootMotionMode::Type SavedRootMotionMode = ERootMotionMode::RootMotionFromMontagesOnly;
	FTimerHandle ActionTimer;
	FTimerHandle RecoveryTimer;
	FTimerHandle MultishotTimer;
	FTimerHandle PiercingTimer;
	FTimerHandle BuffTimer;
	FTimerHandle RelentlessCleanupTimer;
};
