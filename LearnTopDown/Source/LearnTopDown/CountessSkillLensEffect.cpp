#include "CountessSkillLensEffect.h"

#include "Particles/ParticleSystemComponent.h"

ACountessSkillLensEffect::ACountessSkillLensEffect()
{
	bAllowMultipleInstances = true;
	bDestroyOnSystemFinish = false;
	SetCanBeDamaged(false);
	SetActorEnableCollision(false);
	Tags.Add(TEXT("CountessSkillLensFX"));
	BaseFOV = 90.0f;
	RelativeTransform.SetLocation(FVector(90.0f, 0.0f, 0.0f));
	GetParticleSystemComponent()->bAutoActivate = false;
}

void ACountessSkillLensEffect::Initialize(UParticleSystem* Effect, float Lifetime)
{
	PS_CameraEffect = Effect;
	UParticleSystemComponent* Particle = GetParticleSystemComponent();
	Particle->SetTemplate(Effect);
	Particle->ComponentTags.Add(TEXT("CountessSkillFX"));
	Particle->ComponentTags.Add(TEXT("CountessSkillCameraFX"));
	Particle->bOverrideLODMethod = true;
	Particle->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
	ActivateLensEffect();
	Particle->SetLODLevel(0);
	SetLifeSpan(FMath::Max(0.05f, Lifetime));
}
