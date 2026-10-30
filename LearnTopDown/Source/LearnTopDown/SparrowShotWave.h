#pragma once

#include "CoreMinimal.h"
#include "Camera/CameraShakeBase.h"
#include "GameFramework/Actor.h"
#include "SparrowShotWave.generated.h"

class UMaterialInstanceDynamic;
class UMaterialInterface;
class UStaticMeshComponent;
class UParticleSystemComponent;
class APlayerCameraManager;
class UParticleSystem;
class USkeletalMeshComponent;

namespace SparrowPresentation
{
	UParticleSystem* GetReleaseShards();
	UParticleSystem* GetMultishotFinishShards();
	void SpawnTransferredHitFlash(AActor* Owner, const FVector& Location, const FVector& Direction, bool bWorld = false);
	void SpawnGearFlightCrackle(AActor* ArrowOwner, const FVector& Location, const FVector& Direction);
}

// R 입력 순간에 활 전용 슬롯만 황금색으로 바꾸고 시전 종료 때 복구한다.
UCLASS()
class LEARNTOPDOWN_API ASparrowMultishotBowTint : public AActor
{
	GENERATED_BODY()
public:
	ASparrowMultishotBowTint();
	virtual void Tick(float DeltaSeconds) override;
protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
private:
	TWeakObjectPtr<USkeletalMeshComponent> BowMesh;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> OriginalBowMaterial;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> GoldBowMaterial;
	int32 BowMaterialSlot = INDEX_NONE;
};

// R에서 제거한 착탄 섬광을 A 명중 지점에서 2/3 크기로 세 번만 재생한다. 피해는 처리하지 않는다.
UCLASS()
class LEARNTOPDOWN_API ASparrowTransferredHitFlash : public AActor
{
	GENERATED_BODY()
public:
	ASparrowTransferredHitFlash();
	UFUNCTION(BlueprintPure, Category = "Skills")
	int32 GetPulseCount() const { return PulseCount; }
protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
private:
	void SpawnPulse();
	UFUNCTION()
	void HandleOwnerDestroyed(AActor* DestroyedOwner);
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> FlashTemplate;
	TArray<TWeakObjectPtr<UParticleSystemComponent>> Particles;
	FTimerHandle SecondPulseTimer;
	FTimerHandle ThirdPulseTimer;
	int32 PulseCount = 0;
};

UCLASS()
class USparrowShotRecoil : public UCameraShakePattern
{
	GENERATED_BODY()
private:
	virtual void GetShakePatternInfoImpl(FCameraShakeInfo& OutInfo) const override;
	virtual void StartShakePatternImpl(const FCameraShakePatternStartParams& Params) override;
	virtual void UpdateShakePatternImpl(const FCameraShakePatternUpdateParams& Params, FCameraShakePatternUpdateResult& OutResult) override;
	virtual bool IsFinishedImpl() const override { return Age >= 0.24f; }
	virtual void StopShakePatternImpl(const FCameraShakePatternStopParams& Params) override { Age = 0.24f; }
	float Age = 0.0f;
};

UCLASS()
class USparrowShotCameraShake : public UCameraShakeBase
{
	GENERATED_BODY()
public:
	USparrowShotCameraShake(const FObjectInitializer& ObjectInitializer);
};

// W 발사에만 사용하는 짧은 공기 파동. 충돌과 피해는 원래 화살이 처리한다.
UCLASS()
class LEARNTOPDOWN_API ASparrowShotWave : public AActor
{
	GENERATED_BODY()
public:
	ASparrowShotWave();
	// Deferred spawn only. Preparation owns no projectile or gameplay timer.
	void SetPreparationMode(float Seconds) { bPreparation = true; PreparationSeconds = FMath::Max(.08f, Seconds); }
	virtual void Tick(float DeltaSeconds) override;
protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
private:
	UPROPERTY()
	TArray<TObjectPtr<UStaticMeshComponent>> Waves;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> Materials;
	UPROPERTY()
	TSoftObjectPtr<UMaterialInterface> AirMaterial;
	UPROPERTY()
	TObjectPtr<UStaticMeshComponent> AxialFlash;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> FlashMaterial;
	TWeakObjectPtr<UParticleSystemComponent> PressureEffect;
	TWeakObjectPtr<UParticleSystemComponent> ShardEffect;
	TWeakObjectPtr<APlayerCameraManager> Camera;
	TWeakObjectPtr<UCameraShakeBase> Shake;
	UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> PressureLips;
	UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> LipMaterials;
	bool bRenaissance = false;
	bool bPreparation = false;
	float PreparationSeconds = .65f;
	float Age = 0.0f;
};

// E의 단일 맥동 고리와 R의 전방 잔광. 피해/화살 발사와 독립된 짧은 연출이다.
UCLASS()
class LEARNTOPDOWN_API ASparrowBowFeedback : public AActor
{
	GENERATED_BODY()
public:
	ASparrowBowFeedback();
	void SetRapidMode() { bRapidMode = true; }
	void Pulse() { PulseAge = 0.0f; }
	virtual void Tick(float DeltaSeconds) override;
protected:
	virtual void BeginPlay() override;
private:
	UPROPERTY()
	TObjectPtr<UStaticMeshComponent> Surface;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> Material;
	UPROPERTY()
	TSoftObjectPtr<UMaterialInterface> RingMaterial;
	UPROPERTY()
	TSoftObjectPtr<UMaterialInterface> FanMaterial;
	bool bRapidMode = false;
	float Age = 0.0f;
	float PulseAge = 0.0f;
};
