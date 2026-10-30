#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SparrowAscendedShotFX.generated.h"

class ATopDownCombatCharacter;
class UStaticMeshComponent;
class UInstancedStaticMeshComponent;
class UMaterialInstanceDynamic;
class UParticleSystem;
class UParticleSystemComponent;

// 변신 Q/W/R의 추가 표면. 실탄, 피해, 쿨타임과 분리된 표현 전용 액터다.
UCLASS()
class LEARNTOPDOWN_API ASparrowAscendedShotFX : public AActor
{
	GENERATED_BODY()
public:
	ASparrowAscendedShotFX();
	static class UParticleSystem* GetHarmonyContactTemplate();
	// 변신 Q의 느린 지면 접촉과 피해 펄스가 같은 시간축을 사용한다.
	static constexpr float RainContactDelay = .82f;
	static constexpr float RainContactInterval = .37f;
	bool InitializeBow(ATopDownCombatCharacter* Character, int32 Slot, const FVector& Origin,
		const FVector& Direction, float PrepareSeconds);
	bool InitializeRain(ATopDownCombatCharacter* Character, const FVector& Ground, float Duration = 4.0f,
		float Radius = 300.0f, bool bDownward = true, bool bAscended = true);
	bool InitializeContact(ATopDownCombatCharacter* Character, int32 Slot, const FVector& Point, const FVector& Direction);
	void Pulse(const FVector& Origin, const FVector& Direction);
	void FinishCast();
	virtual void Tick(float DeltaSeconds) override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
private:
	bool InitializeOwner(ATopDownCombatCharacter* Character);
	bool CreateSurface(const TCHAR* Part, int32 Index);
	bool CreateDesignSurface(const TCHAR* MeshName, const TCHAR* Part, int32 Index);
	void DrawBow();
	void DrawRain();
	void DrawDesignRain();
	void DrawCelestialRain();
	void DrawRenaissanceRain();
	bool InitializePillarRain();
	void DrawPillarRain();
	bool InitializeMeteorRain();
	void DrawMeteorRain();
	UParticleSystemComponent* SpawnRainParticle(UParticleSystem* Template, const FVector& Position,
		const FRotator& Rotation, float Scale);
	void DrawContact();
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Surfaces;
	UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> Materials;
	UPROPERTY(Transient) TObjectPtr<UParticleSystem> MeteorTrailTemplate;
	UPROPERTY(Transient) TObjectPtr<UParticleSystem> MeteorContactTemplate;
	UPROPERTY(Transient) TArray<TObjectPtr<UParticleSystemComponent>> RainParticles;
	UPROPERTY(Transient) TObjectPtr<UInstancedStaticMeshComponent> MeteorWake;
	struct FWakeDot
	{
		FVector Position = FVector::ZeroVector;
		float BornAt = 0.0f;
		float Size = 0.0f;
	};
	TArray<FWakeDot> WakeDots;
	TArray<FTransform> WakeTransforms;
	struct FMeteorVisual
	{
		FVector Ground = FVector::ZeroVector;
		FVector Fall = -FVector::UpVector;
		FVector LastWakePoint = FVector::ZeroVector;
		float BornAt = 0.0f;
		float Height = 800.0f;
		float Scale = 1.0f;
		bool bSpawned = false;
		bool bContact = false;
		TWeakObjectPtr<UParticleSystemComponent> Trail;
		TWeakObjectPtr<UParticleSystemComponent> Contact;
	};
	TArray<FMeteorVisual> MeteorVisuals;
	// Four waves share a fixed visual pool; collision/damage remains in the skill.
	TArray<FVector> PillarGrounds;
	TWeakObjectPtr<ATopDownCombatCharacter> Caster;
	FVector Origin = FVector::ZeroVector;
	FVector Forward = FVector::ForwardVector;
	float Age = 0.0f;
	float PulseAt = -100.0f;
	float FadeAt = -1.0f;
	float Preparation = .3f;
	float RainSeconds = 4.0f;
	float RainRadius = 300.0f;
	int32 SkillSlot = 0;
	int32 Mode = 0;
	int32 Pulses = 0;
	int32 RainDesign = 0;
	bool bReady = false;
	bool bRainDownward = true;
	bool bRainAscended = true;
};
