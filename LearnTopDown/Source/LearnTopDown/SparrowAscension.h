#pragma once

#include "CoreMinimal.h"
#include "SparrowArrow.h"
#include "SparrowAscension.generated.h"

class ACharacter;
class UAnimSequence;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UParticleSystemComponent;
class UParticleSystem;
class USkeletalMeshComponent;
class UStaticMeshComponent;

// 소유자가 사라지면 즉시 정리하고, 원본 파티클의 반복 여부와 별개로 짧은 수명을 강제한다.
UCLASS()
class LEARNTOPDOWN_API ASparrowAscensionAccent : public AActor
{
	GENERATED_BODY()
public:
	ASparrowAscensionAccent();
	void Initialize(UParticleSystem* Template, float EmissionSeconds, float Lifetime);
	void InitializeStudyPulse(UParticleSystem* Template, float Lifetime, float PlaybackSpeed);
	virtual void Tick(float DeltaSeconds) override;
protected:
	virtual void BeginPlay() override;
private:
	UPROPERTY()
	TObjectPtr<UParticleSystemComponent> Particle;
	float Age = 0.0f;
	float EmissionDuration = 0.10f;
	bool bEmissionStopped = false;
};

// A만 사용하는 느린 회전 파동 화살. 이동/구간 충돌/표적당 한 번의 피해는 기존 화살을 재사용한다.
UCLASS()
class LEARNTOPDOWN_API ASparrowGearArrow : public ASparrowArrow
{
	GENERATED_BODY()
public:
	ASparrowGearArrow();
	virtual void Tick(float DeltaSeconds) override;
protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	virtual void OnArrowImpactVisual(const FHitResult& Hit, bool bWorld) override;
private:
	UPROPERTY()
	TObjectPtr<USceneComponent> Rotor;
	UPROPERTY()
	TArray<TObjectPtr<UStaticMeshComponent>> FeatherRings;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> FeatherMaterials;
	UPROPERTY()
	TObjectPtr<UParticleSystemComponent> CondensedCore;
	void InitializeSawVortex();
	void UpdateSawVortex(float DeltaSeconds, float ImpactPulse);
	void SpawnLegacySpiralImpact(const FHitResult& Hit, bool bWorld);
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> VortexSurfaces;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> VortexMaterials;
	float VortexAge = 0.0f;
	float NextSpiralEmission = 0.0f;
	bool bAscendedGear = false;
	float ImpactPulseAge = 1.0f;
	float SpinDegrees = 0.0f;
	float FlightCrackleAge = 0.0f;
	bool bCrackleRight = false;
};

// 변신 중 망토/후드 섹션과 본체 재질을 임시 교체하고 종료 때 각 LOD와 원본 override를 복구한다.
UCLASS()
class LEARNTOPDOWN_API ASparrowAscensionWings : public AActor
{
	GENERATED_BODY()
public:
	ASparrowAscensionWings();
	bool Initialize(ACharacter* Character, float Lifetime);
	static UParticleSystem* GetEntryRiseTemplate();
	float GetRemainingSeconds() const;
	USkeletalMeshComponent* GetWingMesh() const { return Wings; }
	void SetMobilityVisibility(float Alpha) { MobilityVisibility = FMath::Clamp(Alpha, 0.0f, 1.0f); }
	bool BeginWingAttack(float ChargeSeconds);
	void ReleaseWingAttack();
	void CancelWingAttack();
	UFUNCTION(BlueprintCallable, Category = "Skills") void BeginVisualExit();
	UFUNCTION(BlueprintPure, Category = "Skills") bool IsVisualExiting() const { return bVisualExiting; }
	UFUNCTION(BlueprintPure, Category = "Skills") bool IsWingAttackActive() const { return WingAttackStartedAt >= 0.0; }
	UFUNCTION(BlueprintPure, Category = "Skills") FName GetWingAnimationName() const;
	UFUNCTION(BlueprintPure, Category = "Skills") float GetWingAnimationPosition() const { return WingAnimationPosition; }
	virtual void Tick(float DeltaSeconds) override;
protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
private:
	void UseIdleWings();
	void SetWingPose(UAnimSequence* Animation, float Position);
	void UpdateWingAnimation(float Age);
	void AlignWingRoot();
	void RestoreBodyAppearance();
	void UpdateWingEnvelope(float Envelope);
	void UpdateEntryFlames(float Age);
	FVector GetEntryWingPoint(float Side, float Reach, float Height) const;
	void AddEntryFlame(UParticleSystem* Template, float Side, float Reach, float EndReach,
		float Height, float EndHeight, const FVector& Scale, const FVector& EndScale, float Duration, float Speed);
	struct FEntryFlame
	{
		TWeakObjectPtr<UParticleSystemComponent> Particle;
		float Born = 0.0f;
		float Duration = 0.0f;
		float Side = 0.0f;
		float Reach = 0.0f;
		float EndReach = 0.0f;
		float Height = 0.0f;
		float EndHeight = 0.0f;
		FVector Scale = FVector::OneVector;
		FVector EndScale = FVector::OneVector;
	};
	TArray<FEntryFlame> EntryFlames;
	TArray<FName> EntryWingBones;
	int32 NextEntryBeat = 0;
	UPROPERTY()
	TObjectPtr<USkeletalMeshComponent> Wings;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> WingMaterials;
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> IdleAnimation;
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> UnfoldAnimation;
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> FoldAnimation;
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> AttackAnimation;
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> CurrentWingAnimation;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInterface>> OriginalBodyMaterials;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> GoldenBodyMaterial;
	TWeakObjectPtr<USkeletalMeshComponent> SourceMesh;
	TArray<int32> HiddenClothMaterialIds;
	TArray<TArray<bool>> ClothVisibility;
	double StartedAt = 0.0;
	float LifeSeconds = 40.0f;
	float MobilityVisibility = 1.0f;
	double WingAttackStartedAt = -1.0;
	double WingAttackReleasedAt = -1.0;
	double VisualExitStartedAt = -1.0;
	float WingAttackChargeSeconds = .42f;
	float WingAnimationPosition = 0.0f;
	bool bVisualExiting = false;
	bool bBodyAppearanceRestored = false;
	bool bEntryRevealPlayed = false;
	bool bExitAccentPlayed = false;
};

// D의 설치 궁수 두 명은 생성 위치에 고정되어 본체와 같은 평타 주기로 자율 사격한다.
UCLASS()
class LEARNTOPDOWN_API ASparrowMirrorArcher : public AActor
{
	GENERATED_BODY()
public:
	ASparrowMirrorArcher();
	bool Initialize(ACharacter* Character, const FVector& Aim, bool bWhite);
	void BeginVolley();
	bool HasStartedVolley() const { return bVolleyStarted; }
	bool CanEcho() const;
	UFUNCTION(BlueprintPure, Category = "Skills")
	bool IsActive() const { return CanEcho(); }
	UFUNCTION(BlueprintPure, Category = "Skills")
	int32 GetEchoShotCount() const { return EchoesFired; }
	UFUNCTION(BlueprintPure, Category = "Skills")
	float GetRemainingSeconds() const;
	FVector GetArrowOrigin() const;
	virtual void Tick(float DeltaSeconds) override;
protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
private:
	AActor* FindSentryTarget() const;
	void StartSentryAttack();
	void FireSentryArrow();
	UPROPERTY()
	TObjectPtr<USkeletalMeshComponent> Archer;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> EchoMaterial;
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> AttackAnimation;
	TWeakObjectPtr<USkeletalMeshComponent> SourceMesh;
	TWeakObjectPtr<AActor> SentryTarget;
	FVector CastDirection = FVector::ForwardVector;
	FLinearColor EchoBodyTint = FLinearColor(0.7f, 0.39f, 0.06f);
	double StartedAt = 0.0;
	double VolleyStartedAt = 0.0;
	double EchoPulseDeadline = 0.0;
	double NextAttackAt = 0.0;
	double ShotAt = 0.0;
	float AttackPhaseOffset = 0.0f;
	int32 EchoesFired = 0;
	bool bShotPending = false;
	bool bVolleyStarted = false;
	bool bExitAccentPlayed = false;
};
