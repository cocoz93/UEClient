#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SparrowArsenalStudyFX.generated.h"

class ATopDownCombatCharacter;
class UStaticMeshComponent;
class UMaterialInstanceDynamic;
class UParticleSystemComponent;
class UParticleSystem;

// 선택한 R/S 비교 시안에만 생성하는 시각 액터. 실제 발사와 피해는 기존 스킬이 소유한다.
UCLASS()
class LEARNTOPDOWN_API ASparrowArsenalStudyFX : public AActor
{
	GENERATED_BODY()
public:
	ASparrowArsenalStudyFX();
	static int32 GetCandidate(int32 SkillSlot);
	static UParticleSystem* GetCraftImpactEffect();
	bool Initialize(ATopDownCombatCharacter* Character, int32 SkillSlot, int32 Candidate,
		const FVector& Origin, const FVector& Direction, float PreparationSeconds);
	void Pulse(const FVector& Origin, const FVector& Direction);
	void FinishCast();
	UFUNCTION(BlueprintPure, Category = "Skills")
	int32 GetPulses() const { return Pulses; }
	bool UsesRecraftedPresentation() const { return Style >= 4; }
	bool UsesRenaissancePresentation() const { return Style == 5 && Slot == 3; }
	bool UsesCraftVolleyPresentation() const { return Style == 6 && Slot == 3; }
	virtual void Tick(float DeltaSeconds) override;
protected:
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
private:
	UParticleSystemComponent* SpawnCraftPulse(bool bPreparation);
	void UpdateCraftVolley();
	bool AddSurface(const TCHAR* Part, int32 Index);
	void DrawVolley(float Since, float Fade);
	void DrawSharp(float Since, float Fade);
	void DrawVolleyRecrafted(float Since, float Fade);
	void DrawSharpRecrafted(float Since, float Fade);
	void DrawSharpDirections(float Since, float Fade);
	void DrawSharpRevision(float Since, float Fade);
	bool AddRenaissanceSurface(const TCHAR* MeshName, const TCHAR* MaterialName, int32 Index);
	void DrawRenaissance(float Since, float Fade);
	void Place(int32 Index, FVector Position, FQuat Rotation, FVector Scale, float Envelope, float Since);
	TWeakObjectPtr<ATopDownCombatCharacter> Caster;
	UPROPERTY()
	TArray<TObjectPtr<UStaticMeshComponent>> Surfaces;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> Materials;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystemComponent> CraftPreparation;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UParticleSystemComponent>> CraftBursts;
	TArray<float> CraftBurstTimes;
	FVector Origin = FVector::ZeroVector;
	FVector Forward = FVector::ForwardVector;
	float Age = 0.0f;
	float PulseAt = -100.0f;
	float FadeAt = -1.0f;
	float Preparation = .12f;
	int32 Slot = 3;
	int32 Style = 0;
	int32 Pulses = 0;
	bool bAscended = false;
	bool bReady = false;
};
