#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS

#include "CharacterPipelineQA.h"
#include "../PlayerCombatComponent.h"
#include "Distributions/DistributionFloatConstantCurve.h"
#include "Distributions/DistributionFloatUniform.h"
#include "Distributions/DistributionVectorConstantCurve.h"
#include "Distributions/DistributionVectorUniform.h"
#include "Engine/World.h"
#include "Materials/MaterialInterface.h"
#include "Particles/ParticleEmitter.h"
#include "Particles/ParticleLODLevel.h"
#include "Particles/ParticleModuleRequired.h"
#include "Particles/ParticleSystem.h"
#include "Particles/Color/ParticleModuleColorScaleOverLife.h"
#include "Particles/Acceleration/ParticleModuleAccelerationConstant.h"
#include "Particles/Lifetime/ParticleModuleLifetime.h"
#include "Particles/Size/ParticleModuleSize.h"
#include "Particles/Size/ParticleModuleSizeMultiplyLife.h"
#include "Particles/Spawn/ParticleModuleSpawn.h"
#include "Particles/Velocity/ParticleModuleVelocity.h"
#include "UObject/UObjectIterator.h"
#include "UObject/UnrealType.h"

namespace FleshHitStudy
{

// A는 기본 에셋으로 보존한다. B는 재질과 파티클이 모두 분리된 비교용 사본이다.
static constexpr const TCHAR* CandidatePath =
	TEXT("/Game/TopDown/Combat/FX/BloodStudy20261030/P_FleshHitB.P_FleshHitB");
static constexpr const TCHAR* BoldCandidatePath =
	TEXT("/Game/TopDown/Combat/FX/BloodStudy20261030/P_FleshHitB2.P_FleshHitB2");

static FAutoConsoleCommand Author(
	TEXT("CombatFX.AuthorFleshHitStudy"), TEXT("Editor only: refine isolated blood study B or B2"),
	FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args)
	{
		if (Args.Num() > 1 || (Args.Num() == 1 && Args[0] != TEXT("B") && Args[0] != TEXT("B2"))) { return; }
		const bool bBold = Args.Num() == 1 && Args[0] == TEXT("B2");
		UParticleSystem* Particle = LoadObject<UParticleSystem>(nullptr, bBold ? BoldCandidatePath : CandidatePath);
		if (!Particle || Particle->Emitters.Num() != 3)
		{
			UE_LOG(LogTemp, Error, TEXT("FleshHitStudy: duplicate the three-emitter baseline first"));
			return;
		}
		const FString Suffix = bBold ? TEXT("B2") : TEXT("B");
		const FString Root = TEXT("/Game/TopDown/Combat/FX/BloodStudy20261030/");
		const TMap<FName, FString> MaterialPaths = {
			{TEXT("BlackFlecks"), Root + TEXT("M_FleshHitDroplets") + Suffix + TEXT(".M_FleshHitDroplets") + Suffix},
			{TEXT("FleshFineDroplets"), Root + TEXT("M_FleshHitFineDrops") + Suffix + TEXT(".M_FleshHitFineDrops") + Suffix},
			{TEXT("FleshContactSplash"), Root + TEXT("M_FleshHitImpact") + Suffix + TEXT(".M_FleshHitImpact") + Suffix}};
		// 공유 모듈 또는 불완전한 사본이면 편집 전에 중단한다.
		for (UParticleEmitter* Emitter : Particle->Emitters)
		{
			if (!Emitter || Emitter->LODLevels.Num() != 1 || !Emitter->LODLevels[0]) { return; }
			UParticleLODLevel* Level = Emitter->LODLevels[0];
			const FString* Path = MaterialPaths.Find(Emitter->GetEmitterName());
			if (!Path || !LoadObject<UMaterialInterface>(nullptr, **Path) ||
				!Level->RequiredModule || !Level->RequiredModule->IsIn(Particle) ||
				!Level->SpawnModule || !Level->SpawnModule->IsIn(Particle)) { return; }
			for (UParticleModule* Module : Level->Modules)
			{
				if (Module && !Module->IsIn(Particle))
				{
					UE_LOG(LogTemp, Error, TEXT("FleshHitStudy: shared module %s"), *Module->GetPathName());
					return;
				}
			}
		}
		Particle->Modify();
		for (UParticleEmitter* Emitter : Particle->Emitters)
		{
			UParticleLODLevel* Level = Emitter->LODLevels[0];
			const bool bFine = Emitter->GetEmitterName() == TEXT("FleshFineDroplets");
			const bool bImpact = Emitter->GetEmitterName() == TEXT("FleshContactSplash");
			Level->RequiredModule->Material = LoadObject<UMaterialInterface>(nullptr,
				*MaterialPaths.FindChecked(Emitter->GetEmitterName()));
			if (bFine)
			{
				// 잔여 방울은 소수만 늦게 분리해 중력 궤적이 짧게 읽히도록 한다.
				Level->SpawnModule->BurstList.SetNum(2);
				Level->SpawnModule->BurstList[0].Count = bBold ? 4 : 7;
				Level->SpawnModule->BurstList[0].CountLow = bBold ? 3 : 5;
				Level->SpawnModule->BurstList[0].Time = 0.025f;
				Level->SpawnModule->BurstList[1].Count = 3;
				Level->SpawnModule->BurstList[1].CountLow = 2;
				Level->SpawnModule->BurstList[1].Time = bBold ? 0.085f : 0.075f;
			}
			for (UParticleModule* Module : Level->Modules)
			{
				if (UParticleModuleLifetime* Life = Cast<UParticleModuleLifetime>(Module); Life && (bFine || bBold))
				{
					UDistributionFloatUniform* Value = NewObject<UDistributionFloatUniform>(Life);
					Value->Min = bFine ? (bBold ? 0.48f : 0.34f) : (bImpact ? 0.12f : 0.25f);
					Value->Max = bFine ? (bBold ? 0.66f : 0.52f) : (bImpact ? 0.18f : 0.43f);
					Life->Lifetime.Distribution = Value;
					Life->Lifetime.Initialize();
				}
				else if (UParticleModuleSize* InitialSize = Cast<UParticleModuleSize>(Module); InitialSize && bFine && bBold)
				{
					// B2의 소수 방울은 화면에서 사라지지 않도록 가늘고 긴 크기를 확보한다.
					UDistributionVectorUniform* Value = NewObject<UDistributionVectorUniform>(InitialSize);
					Value->Min = FVector(16, 28, 1);
					Value->Max = FVector(24, 40, 1);
					InitialSize->StartSize.Distribution = Value;
					InitialSize->StartSize.Initialize();
				}
				else if (UParticleModuleVelocity* Velocity = Cast<UParticleModuleVelocity>(Module); Velocity && bFine && bBold)
				{
					UDistributionVectorUniform* Value = NewObject<UDistributionVectorUniform>(Velocity);
					Value->Min = FVector(70, -150, 20);
					Value->Max = FVector(240, 140, 170);
					Velocity->StartVelocity.Distribution = Value;
					Velocity->StartVelocity.Initialize();
				}
				else if (UParticleModuleAccelerationConstant* Gravity = Cast<UParticleModuleAccelerationConstant>(Module); Gravity && bFine && bBold)
				{
					Gravity->Acceleration = FVector(0, 0, -900);
				}
				else if (UParticleModuleSizeMultiplyLife* Size = Cast<UParticleModuleSizeMultiplyLife>(Module))
				{
					UDistributionVectorConstantCurve* Value = NewObject<UDistributionVectorConstantCurve>(Size);
					if (bBold && bFine)
					{
						Value->ConstantCurve.Points.Emplace(0.0f, FVector(0.7f, 1.35f, 1));
						Value->ConstantCurve.Points.Emplace(0.35f, FVector(0.8f, 1.0f, 1));
						Value->ConstantCurve.Points.Emplace(0.75f, FVector(0.7f, 0.9f, 1));
						Value->ConstantCurve.Points.Emplace(1.0f, FVector(0.15f));
					}
					else if (bBold && !bImpact)
					{
						// 분출 직후 길게 늘어났다가 가늘게 끊어지는 윤곽으로 바뀐다.
						Value->ConstantCurve.Points.Emplace(0.0f, FVector(0.9f, 0.85f, 1));
						Value->ConstantCurve.Points.Emplace(0.22f, FVector(0.75f, 1.5f, 1));
						Value->ConstantCurve.Points.Emplace(0.55f, FVector(0.45f, 1.0f, 1));
						Value->ConstantCurve.Points.Emplace(1.0f, FVector(0.08f));
					}
					else if (bFine)
					{
						Value->ConstantCurve.Points.Emplace(0.0f, FVector(0.85f, 1.1f, 1));
						Value->ConstantCurve.Points.Emplace(0.55f, FVector(0.75f, 0.95f, 1));
						Value->ConstantCurve.Points.Emplace(1.0f, FVector(0.2f));
					}
					else
					{
						Value->ConstantCurve.Points.Emplace(0.0f, FVector(0.85f, 0.95f, 1));
						Value->ConstantCurve.Points.Emplace(0.16f, FVector(1.0f, 1.05f, 1));
						Value->ConstantCurve.Points.Emplace(0.5f, FVector(0.7f, 0.85f, 1));
						Value->ConstantCurve.Points.Emplace(1.0f, FVector(0.12f));
					}
					Size->LifeMultiplier.Distribution = Value;
					Size->LifeMultiplier.Initialize();
				}
				else if (UParticleModuleColorScaleOverLife* Fade = Cast<UParticleModuleColorScaleOverLife>(Module))
				{
					UDistributionFloatConstantCurve* Alpha = NewObject<UDistributionFloatConstantCurve>(Fade);
					Alpha->ConstantCurve.Points.Emplace(0.0f, 1.0f);
					Alpha->ConstantCurve.Points.Emplace(bFine ? (bBold ? 0.8f : 0.65f) : (bImpact ? 0.25f : 0.4f), 1.0f);
					Alpha->ConstantCurve.Points.Emplace(1.0f, 0.0f);
					Fade->AlphaScaleOverLife.Distribution = Alpha;
					Fade->AlphaScaleOverLife.Initialize();
				}
			}
		}
		// 주효과의 초기 속도·분출 반경·중력·초기 크기는 A를 그대로 따른다.
		Particle->UpdateAllModuleLists();
		Particle->BuildEmitters();
		Particle->PostEditChange();
		Particle->MarkPackageDirty();
		UE_LOG(LogTemp, Display, TEXT("FleshHitStudy: %s authored; baseline main travel and initial sizes preserved"), *Suffix);
	}));

static FAutoConsoleCommand Preview(
	TEXT("CombatFX.PreviewFleshHit"), TEXT("Editor PIE only: choose A, B or B2 for the current player"),
	FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args)
	{
		if (Args.Num() != 1 || (Args[0] != TEXT("A") && Args[0] != TEXT("B") && Args[0] != TEXT("B2"))) { return; }
		const TCHAR* Path = Args[0] == TEXT("B2") ? BoldCandidatePath : (Args[0] == TEXT("B") ? CandidatePath :
			TEXT("/Game/TopDown/Combat/FX/P_FleshHit.P_FleshHit"));
		UParticleSystem* Particle = LoadObject<UParticleSystem>(nullptr, Path);
		const FObjectPropertyBase* Property = FindFProperty<FObjectPropertyBase>(
			UPlayerCombatComponent::StaticClass(), TEXT("FleshHitEffect"));
		if (!Particle || !Property) { return; }
		int32 Count = 0;
		for (TObjectIterator<UPlayerCombatComponent> It; It; ++It)
		{
			if (!It->IsTemplate() && It->GetWorld() && It->GetWorld()->WorldType == EWorldType::PIE)
			{
				Property->SetObjectPropertyValue_InContainer(*It, Particle);
				++Count;
			}
		}
		UE_LOG(LogTemp, Display, TEXT("FleshHitStudy: preview %s on %d PIE components"), *Args[0], Count);
	}));

}

#endif
