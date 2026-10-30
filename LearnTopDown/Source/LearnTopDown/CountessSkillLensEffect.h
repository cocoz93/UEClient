#pragma once

#include "CoreMinimal.h"
#include "Particles/EmitterCameraLensEffectBase.h"
#include "CountessSkillLensEffect.generated.h"

// 엔진의 카메라 렌즈 위치/FOV 보정을 이용하며, 수명이 끝나면 카메라 등록도 함께 정리한다.
UCLASS()
class LEARNTOPDOWN_API ACountessSkillLensEffect : public AEmitterCameraLensEffectBase
{
	GENERATED_BODY()

public:
	ACountessSkillLensEffect();
	void Initialize(UParticleSystem* Effect, float Lifetime);
};
