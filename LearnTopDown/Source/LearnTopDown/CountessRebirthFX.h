#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "CountessRebirthFX.generated.h"

class UInstancedStaticMeshComponent;
class UMaterialInstanceDynamic;
class UParticleSystemComponent;
class UParticleSystem;

// 타격과 이동은 스킬 컴포넌트가 소유한다. 이 배우는 실제 발동 신호 뒤의 조형만 담당한다.
UCLASS()
class LEARNTOPDOWN_API ACountessRebirthFX : public AActor
{
	GENERATED_BODY()
public:
	ACountessRebirthFX();
	static bool Enabled();
	static ACountessRebirthFX* Create(AActor* Owner, FName Kind, const FVector& Origin,
		const FVector& Direction, AActor* Follow = nullptr);
	virtual void Tick(float DeltaSeconds) override;
protected:
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
	bool Initialize(FName Kind, const FVector& Origin, const FVector& Direction, AActor* Follow);
	void Cut(const FVector& Center, const FRotator& Rotation, const FVector& Size, float Alpha, float Seed = 0.f);
	void Fang(const FVector& Base, const FRotator& Rotation, const FVector& Size, float Alpha);
	void Pulse(const FVector& Where, float Scale);
	bool InitializeW();
	void DrawW();
	void DrawStrike();
	void DrawField();
	void DrawForm();
	void Upload();
	UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> Cuts;
	UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> Fangs;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> CutMaterial;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> FangMaterial;
	UPROPERTY(Transient) TArray<TObjectPtr<UParticleSystemComponent>> Pulses;
	UPROPERTY(Transient) TObjectPtr<UParticleSystem> WSlashSource;
	TWeakObjectPtr<AActor> Source;
	FName Role;
	FVector Origin, Forward, Right;
	TArray<FTransform> CutTransforms, FangTransforms;
	TArray<FVector4f> CutData, FangData;
	float Age = 0.f, Life = 1.f;
	int32 LastBeat = -1;
	bool bFollow = false;
};
