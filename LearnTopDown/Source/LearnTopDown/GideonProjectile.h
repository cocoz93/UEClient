#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GideonProjectile.generated.h"

class UParticleSystem;
class UParticleSystemComponent;

UENUM()
enum class EGideonProjectileKind : uint8
{
	Primary,
	PortalBlast,
	Burden
};

// 평타·Portal Blast·Burden이 함께 쓰는 직선 투사체. 명중 뒤의 범위 피해·지속 피해는 발사한 스킬 컴포넌트가 소유한다.
UCLASS()
class LEARNTOPDOWN_API AGideonProjectile : public AActor
{
	GENERATED_BODY()

public:
	AGideonProjectile();
	void Launch(EGideonProjectileKind InKind, const FVector& Direction, float Speed, float Range, float Damage,
		UParticleSystem* Trail, UParticleSystem* HitCharacter, UParticleSystem* HitWorld, UParticleSystem* NoHit);
	// 탄 그림을 잠깐 숨겼다가 보인다(출발점 뒤로 긴 몸통을 달고 생기는 그림이 출발점에서부터 나오는 것처럼 보이게).
	void HideTrailFor(float Seconds);
	FVector GetFlightDirection() const { return FlightDirection; }
	float GetFlightSpeed() const { return bStopped ? 0.0f : FlightSpeed; }
	float GetRemainingRange() const { return RemainingRange; }
	virtual void Tick(float DeltaTime) override;

protected:
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	void Stop(const FVector& Location, AActor* Target, UParticleSystem* Effect);

	UPROPERTY(Transient)
	TObjectPtr<UParticleSystemComponent> TrailParticle;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> HitCharacterEffect;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> HitWorldEffect;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> NoHitEffect;

	EGideonProjectileKind Kind = EGideonProjectileKind::Primary;
	FVector FlightDirection = FVector::ForwardVector;
	float FlightSpeed = 0.0f;
	float RemainingRange = 0.0f;
	float FlightDamage = 0.0f;
	float CollisionRadius = 18.0f;
	// 적에게만 쓰는 판정 반지름. 벽·바닥은 CollisionRadius로 본다(넓히면 낮게 나는 투사체가 바닥에 걸린다).
	float TargetRadius = 18.0f;
	bool bStopped = false;
};
