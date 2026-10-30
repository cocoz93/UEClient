#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SparrowArrow.generated.h"

class UParticleSystem;
class UParticleSystemComponent;
class USceneComponent;
class UStaticMeshComponent;
class ASparrowSkillVisual;
class ASparrowPiercingLance;
class ASparrowFeatherTrail;

namespace SparrowPresentation
{
	UParticleSystem* GetMultishotBowGlow();
	UParticleSystem* GetPiercingMuzzle();
}

// 발사한 화살은 시전 상태와 독립적으로 진행하며 매 프레임 이동 구간 전체를 검사한다.
UCLASS()
class LEARNTOPDOWN_API ASparrowArrow : public AActor
{
	GENERATED_BODY()

public:
	ASparrowArrow();
	UFUNCTION(BlueprintCallable, Category = "Combat")
	void InitArrow(const FVector& Direction, float Damage, float Range, float Speed,
		bool bPiercing, bool bPassesWorld, UParticleSystem* Trail, UParticleSystem* HitEffect,
		UParticleSystem* WorldHitEffect);
	virtual void Tick(float DeltaTime) override;
	UFUNCTION(BlueprintPure, Category = "Combat")
	float GetDistanceTravelled() const { return DistanceTravelled; }
	UFUNCTION(BlueprintPure, Category = "Combat")
	float GetRemainingRange() const { return RemainingRange; }
	UFUNCTION(BlueprintPure, Category = "Combat")
	float GetFlightSpeed() const { return FlightSpeed; }
	UFUNCTION(BlueprintPure, Category = "Combat")
	FVector GetFlightDirection() const { return FlightDirection; }
	UFUNCTION(BlueprintPure, Category = "Combat")
	int32 GetHitCount() const { return DamagedActors.Num(); }
	UFUNCTION(BlueprintPure, Category = "Combat")
	bool IsPiercing() const { return bPiercesTargets; }
	UFUNCTION(BlueprintPure, Category = "Combat")
	bool PassesWorld() const { return bIgnoresWorld; }
	UFUNCTION(BlueprintCallable, Category = "Combat")
	void SetAppliesRelentlessBonus(bool bEnabled) { bAppliesRelentlessBonus = bEnabled; }
	void SetRecordsRelentless(bool bEnabled) { bRecordsRelentless = bEnabled; }
	UFUNCTION(BlueprintPure, Category = "Combat")
	bool AppliesRelentlessBonus() const { return bAppliesRelentlessBonus; }
	// 연쇄 스킬에서만 설정한다. 기본 화살과 QWER의 충돌·피해 경로는 유지한다.
	void ConfigureRicochet(int32 AdditionalTargets, float Radius, float DamageScale);
	void EnableExtraPresentation();
	// W의 보이는 폭만 조절한다. 이동 속도와 충돌 반경은 유지한다.
	void SetVisualWidthScale(float Width);
	void EnableChargedAura();
	void SetMultishotPresentationScale(float Scale);
	void EnableRenaissanceMultishot();
	void EnableCraftMultishot(int32 ArrowIndex, int32 WaveIndex);
	void EnableFeatherTrail();
	// R의 한 파동은 화살 수와 무관하게 표적마다 한 번만 피해를 준다. 다른 화살에는 집합을 지정하지 않는다.
	void SetSharedVolleyHits(TSharedPtr<TSet<TWeakObjectPtr<AActor>>> Hits) { SharedVolleyHits = MoveTemp(Hits); }
	// E에만 백금 화살촉·대칭 깃날을 적용한다. 다발사격의 작은 화살은 이 표면을 생성하지 않는다.
	void EnableRapidFlow();
	void ConfigureEDesignPresentation(int32 Style);
	void ConfigureConvergingFlight(const FVector& Target, const FVector& Bend, float Seconds);
	// D 전용 관통광축. 공용 화살의 sweep을 재사용하며 표적별 피해는 기존 집합으로 제한한다.
	void EnablePiercingLance(float Radius = 45.0f);
	void ConfigureImpactPresentation(UParticleSystem* TargetEffect, float Scale, float Lifetime);
	// S만 호출한다. 발사구 뒤로 꼬리가 역류하지 않도록 실제 이동 거리에 맞춰 짧은 광침을 늘린다.
	void EnableSharpBurstPresentation(int32 DetailPreviewStyle = 0);
	void EnableCrystalArrowPresentation();
	UFUNCTION(BlueprintPure, Category = "Arrow")
	TArray<FName> GetTargetImpactEmitterNames() const;
	UFUNCTION(BlueprintPure, Category = "Arrow")
	TArray<FName> GetWorldImpactEmitterNames() const;
	UFUNCTION(BlueprintPure, Category = "Arrow")
	bool HasImpactLightModules() const;

protected:
	virtual void OnArrowImpactVisual(const FHitResult& Hit, bool bWorld);
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Arrow")
	TObjectPtr<USceneComponent> SceneRoot;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Arrow")
	TObjectPtr<UStaticMeshComponent> ArrowMesh;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Arrow")
	TObjectPtr<UParticleSystemComponent> TrailParticle;
	UPROPERTY(EditDefaultsOnly, Category = "Arrow", meta = (ClampMin = "1.0"))
	float CollisionRadius = 12.0f;

private:
	void StartTexturedFlow(float WidthScale);
	void UpdateHolyArrowFacing();
	void UpdateSharpBurstPresentation();
	bool bCrystalArrowPresentation = false;
	void SpawnImpact(UParticleSystem* Effect, const FHitResult& Hit, bool bWorldImpact = false);
	bool TryRicochet(const FHitResult& Hit);
	void SpawnExtraHitVisual(const FHitResult& Hit);
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> TargetImpactEffect;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> ObstacleImpactEffect;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystemComponent> RapidFlowParticle;
	UPROPERTY(Transient)
	TObjectPtr<UStaticMeshComponent> HolyArrowFlight;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> SharpBurstTrails;
	int32 SharpDetailPreviewStyle = 0;
	TSet<TWeakObjectPtr<AActor>> DamagedActors;
	TSharedPtr<TSet<TWeakObjectPtr<AActor>>> SharedVolleyHits;
	FVector FlightDirection = FVector::ForwardVector;
	FVector CurveStart = FVector::ZeroVector;
	FVector CurveTarget = FVector::ZeroVector;
	FVector CurveBend = FVector::ZeroVector;
	float CurveAge = 0.0f;
	float CurveDuration = 0.0f;
	float FlightDamage = 0.0f;
	float ImpactScale = 1.0f;
	float MultishotPresentationScale = 1.0f;
	float ImpactLifetime = 2.0f;
	float FlightSpeed = 1.0f;
	float RemainingRange = 0.0f;
	float DistanceTravelled = 0.0f;
	bool bPiercesTargets = false;
	bool bIgnoresWorld = false;
	bool bAppliesRelentlessBonus = true;
	bool bRecordsRelentless = true;
	bool bInitialized = false;
	bool bRicochetMode = false;
	int32 RicochetsRemaining = 0;
	float RicochetRadius = 500.0f;
	float RicochetDamageScale = 0.75f;
	bool bExtraPresentation = false;
	TWeakObjectPtr<ASparrowSkillVisual> ExtraFlightVisual;
	bool bPiercingLance = false;
	TWeakObjectPtr<ASparrowPiercingLance> PiercingLanceVisual;
	TWeakObjectPtr<ASparrowFeatherTrail> FeatherTrail;
};
