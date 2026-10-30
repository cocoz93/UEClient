#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS

#include "CharacterPipelineQA.h"
#include "Distributions/DistributionFloatConstant.h"
#include "Distributions/DistributionFloatConstantCurve.h"
#include "Distributions/DistributionFloatUniform.h"
#include "Distributions/DistributionVectorConstant.h"
#include "Distributions/DistributionVectorConstantCurve.h"
#include "Distributions/DistributionVectorUniform.h"
#include "Materials/MaterialInterface.h"
#include "Materials/Material.h"
#include "UObject/UnrealType.h"
#include "Particles/ParticleEmitter.h"
#include "Particles/ParticleLODLevel.h"
#include "Particles/ParticleModuleRequired.h"
#include "Particles/ParticleSystem.h"
#include "Particles/Acceleration/ParticleModuleAccelerationConstant.h"
#include "Particles/Color/ParticleModuleColor.h"
#include "Particles/Color/ParticleModuleColorScaleOverLife.h"
#include "Particles/Lifetime/ParticleModuleLifetime.h"
#include "Particles/Location/ParticleModuleLocationPrimitiveSphere.h"
#include "Particles/Rotation/ParticleModuleRotation.h"
#include "Particles/RotationRate/ParticleModuleRotationRate.h"
#include "Particles/Size/ParticleModuleSize.h"
#include "Particles/Size/ParticleModuleSizeMultiplyLife.h"
#include "Particles/Spawn/ParticleModuleSpawn.h"
#include "Particles/TypeData/ParticleModuleTypeDataGpu.h"
#include "Particles/VectorField/ParticleModuleVectorFieldLocal.h"
#include "Particles/Velocity/ParticleModuleVelocity.h"

// 원본 전체를 복제한 프로젝트 사본에서 BlackFlecks의 움직임과 수명 곡선을 재사용한다.
// 섬광·연기·광원은 살/천 접촉 표현에 맞지 않으므로 사본의 활성 발광기에서 제외한다.
static FAutoConsoleCommand AuthorFleshHit(
	TEXT("CombatFX.AuthorFleshHit"), TEXT("Editor only: adapt the private flesh hit copy; optional size multiplier"),
	FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args)
	{
		UParticleSystem* Particle = LoadObject<UParticleSystem>(nullptr,
			TEXT("/Game/TopDown/Combat/FX/P_FleshHit.P_FleshHit"));
		UMaterialInterface* Material = LoadObject<UMaterialInterface>(nullptr,
			TEXT("/Game/TopDown/Combat/FX/M_FleshHitDroplets.M_FleshHitDroplets"));
		if (!Particle || !Material)
		{
			UE_LOG(LogTemp, Error, TEXT("FleshHit: private particle/material copies are required"));
			return;
		}
		// 원본 렌즈 재질의 불투명 취급 캐시를 해제해 비산 마스크가 실제 렌더에도 적용되게 한다.
		FBoolProperty* AssumeOpaque = FindFProperty<FBoolProperty>(UMaterial::StaticClass(), TEXT("bCanMaskedBeAssumedOpaque"));
		if (!AssumeOpaque) { return; }
		for (const TCHAR* Path : {
			TEXT("/Game/TopDown/Combat/FX/M_FleshHitDroplets.M_FleshHitDroplets"),
			TEXT("/Game/TopDown/Combat/FX/M_FleshHitFineDrops.M_FleshHitFineDrops"),
			TEXT("/Game/TopDown/Combat/FX/M_FleshHitImpact.M_FleshHitImpact")})
		{
			if (UMaterial* LiquidMaterial = LoadObject<UMaterial>(nullptr, Path))
			{
				LiquidMaterial->Modify();
				AssumeOpaque->SetPropertyValue_InContainer(LiquidMaterial, false);
				LiquidMaterial->PostEditChange();
				LiquidMaterial->MarkPackageDirty();
				UE_LOG(LogTemp, Display, TEXT("FleshHit: %s blend %d"), *LiquidMaterial->GetName(), LiquidMaterial->GetBlendMode());
			}
		}
		UParticleEmitter* Flecks = nullptr;
		for (UParticleEmitter* Emitter : Particle->Emitters)
		{
			if (Emitter && Emitter->GetEmitterName() == TEXT("BlackFlecks"))
			{
				Flecks = Emitter;
				break;
			}
		}
		if (!Flecks || Flecks->LODLevels.IsEmpty() || !Flecks->LODLevels[0])
		{
			UE_LOG(LogTemp, Error, TEXT("FleshHit: expected the original BlackFlecks emitter"));
			return;
		}
		UParticleLODLevel* Level = Flecks->LODLevels[0];
		TArray<UParticleModule*> Modules = {Level->RequiredModule, Level->SpawnModule, Level->TypeDataModule};
		for (UParticleModule* Module : Level->Modules) { Modules.Add(Module); }
		for (UParticleModule* Module : Modules)
		{
			if (Module && !Module->IsIn(Particle))
			{
				UE_LOG(LogTemp, Error, TEXT("FleshHit: refusing to edit shared module %s"), *Module->GetPathName());
				return;
			}
		}
		const float SizeScale = Args.IsEmpty() ? 1.0f : FMath::Clamp(FCString::Atof(*Args[0]), 0.25f, 3.0f);
		// 입자 크기와 분출 반경·속도를 함께 키워 전체 효과의 공간 범위를 맞춘다.
		const float EffectScale = 2.0f;
		Particle->Modify();
		Particle->Emitters = {Flecks};
		Flecks->LODLevels.SetNum(1);
		Level->bEnabled = true;
		Level->RequiredModule->bEnabled = true;
		Level->RequiredModule->Material = Material;
		Level->RequiredModule->EmitterDuration = 0.1f;
		Level->RequiredModule->EmitterLoops = 1;
		Level->RequiredModule->bUseLocalSpace = false;
		// 이동 방향을 따라 같은 각도로 늘어나는 불꽃 정렬 대신 입자별 회전을 사용한다.
		Level->RequiredModule->ScreenAlignment = PSA_Rectangle;
		Level->SpawnModule->bEnabled = true;
		UDistributionFloatConstant* Rate = NewObject<UDistributionFloatConstant>(Level->SpawnModule);
		Rate->Constant = 0.0f;
		Level->SpawnModule->Rate.Distribution = Rate;
		Level->SpawnModule->BurstList.SetNum(2);
		Level->SpawnModule->BurstList[0].Count = 6;
		Level->SpawnModule->BurstList[0].CountLow = 4;
		Level->SpawnModule->BurstList[0].Time = 0.0f;
		// 큰 액체 조각은 분출을 짧게 나눠 접촉 순간의 겹침을 줄인다.
		Level->SpawnModule->BurstList[1].Count = 2;
		Level->SpawnModule->BurstList[1].CountLow = 1;
		Level->SpawnModule->BurstList[1].Time = 0.025f;
		// 작은 혈흔은 개별 탄도로 흩어진다. 원본 마법 효과의 회전장은 제외한다.
		Level->Modules.RemoveAll([](const TObjectPtr<UParticleModule>& Module)
		{
			return Module && Module->IsA<UParticleModuleVectorFieldLocal>();
		});
		for (UParticleModule* Module : Level->Modules)
		{
			if (UParticleModuleLifetime* Life = Cast<UParticleModuleLifetime>(Module))
			{
				UDistributionFloatUniform* Value = NewObject<UDistributionFloatUniform>(Life);
				Value->Min = 0.16f;
				Value->Max = 0.38f;
				Life->Lifetime.Distribution = Value;
			}
			else if (UParticleModuleSize* Size = Cast<UParticleModuleSize>(Module))
			{
				UDistributionVectorUniform* Value = NewObject<UDistributionVectorUniform>(Size);
				Value->Min = FVector(12, 18, 1) * SizeScale * EffectScale;
				Value->Max = FVector(23, 34, 1) * SizeScale * EffectScale;
				Size->StartSize.Distribution = Value;
			}
			else if (UParticleModuleSizeMultiplyLife* SizeLife = Cast<UParticleModuleSizeMultiplyLife>(Module))
			{
				// 원본의 한 축만 가늘어지는 곡선은 혈흔을 평행한 줄처럼 보이게 한다.
				UDistributionVectorConstantCurve* Value = NewObject<UDistributionVectorConstantCurve>(SizeLife);
				Value->ConstantCurve.Points.Emplace(0.0f, FVector(1.0f));
				Value->ConstantCurve.Points.Emplace(0.35f, FVector(0.85f));
				Value->ConstantCurve.Points.Emplace(1.0f, FVector(0.15f));
				SizeLife->LifeMultiplier.Distribution = Value;
			}
			else if (UParticleModuleVelocity* Velocity = Cast<UParticleModuleVelocity>(Module))
			{
				// 로컬 +X는 접촉면 바깥쪽이다. 몸을 통과해 뒤늦게 나타나지 않도록 원본 분사를 뒤집는다.
				UDistributionVectorUniform* Value = NewObject<UDistributionVectorUniform>(Velocity);
				Value->Min = FVector(30, -200, -150) * EffectScale;
				Value->Max = FVector(220, 160, 190) * EffectScale;
				Velocity->StartVelocity.Distribution = Value;
				Value->bIsDirty = true;
				Velocity->StartVelocity.Initialize();
			}
			else if (UParticleModuleLocationPrimitiveSphere* Sphere = Cast<UParticleModuleLocationPrimitiveSphere>(Module))
			{
				UDistributionFloatConstant* Radius = NewObject<UDistributionFloatConstant>(Sphere);
				Radius->Constant = 8.0f * EffectScale;
				Sphere->StartRadius.Distribution = Radius;
				Radius->bIsDirty = true;
				Sphere->StartRadius.Initialize();
				Sphere->Positive_Z = Sphere->Negative_Z = true;
				Sphere->Velocity = false;
				UDistributionVectorConstant* Origin = NewObject<UDistributionVectorConstant>(Sphere);
				Origin->Constant = FVector::ZeroVector;
				Sphere->StartLocation.Distribution = Origin;
			}
			else if (UParticleModuleColor* Color = Cast<UParticleModuleColor>(Module))
			{
				UDistributionVectorUniform* Value = NewObject<UDistributionVectorUniform>(Color);
				Value->Min = FVector(0.24, 0.012, 0.020);
				Value->Max = FVector(0.62, 0.036, 0.045);
				Color->StartColor.Distribution = Value;
			}
			else if (UParticleModuleAccelerationConstant* Acceleration = Cast<UParticleModuleAccelerationConstant>(Module))
			{
				Acceleration->Acceleration = FVector(0, 0, -650) * EffectScale;
			}
		}
		UParticleModuleRotation* Rotation = FindObject<UParticleModuleRotation>(Particle, TEXT("FleshRandomRotation"));
		if (!Rotation) { Rotation = NewObject<UParticleModuleRotation>(Particle, TEXT("FleshRandomRotation"), RF_Transactional); }
		UDistributionFloatUniform* Angle = NewObject<UDistributionFloatUniform>(Rotation);
		Angle->Min = 0.0f;
		Angle->Max = 1.0f;
		Rotation->StartRotation.Distribution = Angle;
		Rotation->LODValidity = 1;
		Level->Modules.AddUnique(Rotation);
		UParticleModuleRotationRate* Spin = FindObject<UParticleModuleRotationRate>(Particle, TEXT("FleshRandomSpin"));
		if (!Spin) { Spin = NewObject<UParticleModuleRotationRate>(Particle, TEXT("FleshRandomSpin"), RF_Transactional); }
		UDistributionFloatUniform* SpinRate = NewObject<UDistributionFloatUniform>(Spin);
		SpinRate->Min = -0.35f;
		SpinRate->Max = 0.35f;
		Spin->StartRotationRate.Distribution = SpinRate;
		Spin->LODValidity = 1;
		Level->Modules.AddUnique(Spin);
		// 복제 당시 GPU 캐시는 버리고 사본의 모듈/분포로 다시 만든다.
		UParticleModuleTypeDataGpu* Gpu = NewObject<UParticleModuleTypeDataGpu>(Particle, NAME_None, RF_Transactional);
		Gpu->LODValidity = 1;
		Level->TypeDataModule = Gpu;
		// 둥근 덩어리 대신 액체 조각·미세 방울·접촉 비산의 역할을 분리한다.
		for (UParticleModule* Module : Level->Modules)
		{
			if (UParticleModuleColorScaleOverLife* Fade = Cast<UParticleModuleColorScaleOverLife>(Module))
			{
				UDistributionVectorConstant* Tint = NewObject<UDistributionVectorConstant>(Fade);
				Tint->Constant = FVector::OneVector;
				Fade->ColorScaleOverLife.Distribution = Tint;
				UDistributionFloatConstantCurve* Alpha = NewObject<UDistributionFloatConstantCurve>(Fade);
				Alpha->ConstantCurve.Points.Emplace(0.0f, 1.0f);
				Alpha->ConstantCurve.Points.Emplace(0.45f, 1.0f);
				Alpha->ConstantCurve.Points.Emplace(1.0f, 0.0f);
				Fade->AlphaScaleOverLife.Distribution = Alpha;
			}
		}
		auto AddSecondary = [&](const TCHAR* Name, const TCHAR* MaterialPath, bool bImpact)
		{
			UMaterialInterface* SecondaryMaterial = LoadObject<UMaterialInterface>(nullptr, MaterialPath);
			if (!SecondaryMaterial) { return; }
			UParticleEmitter* Copy = DuplicateObject<UParticleEmitter>(Flecks, Particle);
			Copy->SetEmitterName(FName(Name));
			UParticleLODLevel* CopyLevel = Copy->LODLevels[0];
			CopyLevel->RequiredModule = DuplicateObject<UParticleModuleRequired>(Level->RequiredModule, Particle);
			CopyLevel->RequiredModule->Material = SecondaryMaterial;
			CopyLevel->SpawnModule = DuplicateObject<UParticleModuleSpawn>(Level->SpawnModule, Particle);
			CopyLevel->SpawnModule->BurstList.SetNum(1);
			CopyLevel->SpawnModule->BurstList[0].Count = bImpact ? 1 : 10;
			CopyLevel->SpawnModule->BurstList[0].CountLow = bImpact ? 1 : 7;
			CopyLevel->SpawnModule->BurstList[0].Time = bImpact ? 0.0f : 0.02f;
			CopyLevel->Modules.Reset();
			for (UParticleModule* Original : Level->Modules)
			{
				UParticleModule* Module = DuplicateObject<UParticleModule>(Original, Particle);
				CopyLevel->Modules.Add(Module);
				if (UParticleModuleSize* Size = Cast<UParticleModuleSize>(Module))
				{
					UDistributionVectorUniform* Value = CastChecked<UDistributionVectorUniform>(Size->StartSize.Distribution);
					Value->Min = (bImpact ? FVector(72, 72, 1) : FVector(7, 10, 1)) * SizeScale;
					Value->Max = (bImpact ? FVector(92, 92, 1) : FVector(14, 20, 1)) * SizeScale;
					Value->bIsDirty = true;
					Size->StartSize.Initialize();
				}
				else if (UParticleModuleLifetime* Life = Cast<UParticleModuleLifetime>(Module))
				{
					UDistributionFloatUniform* Value = CastChecked<UDistributionFloatUniform>(Life->Lifetime.Distribution);
					Value->Min = bImpact ? 0.12f : 0.24f;
					Value->Max = bImpact ? 0.18f : 0.44f;
					Value->bIsDirty = true;
					Life->Lifetime.Initialize();
				}
				else if (bImpact)
				{
					if (UParticleModuleVelocity* Velocity = Cast<UParticleModuleVelocity>(Module))
					{
						UDistributionVectorUniform* Value = CastChecked<UDistributionVectorUniform>(Velocity->StartVelocity.Distribution);
						Value->Min = Value->Max = FVector::ZeroVector;
						Value->bIsDirty = true;
						Velocity->StartVelocity.Initialize();
					}
					else if (UParticleModuleAccelerationConstant* Acceleration = Cast<UParticleModuleAccelerationConstant>(Module))
					{
						Acceleration->Acceleration = FVector::ZeroVector;
					}
					else if (UParticleModuleLocationPrimitiveSphere* Sphere = Cast<UParticleModuleLocationPrimitiveSphere>(Module))
					{
						UDistributionFloatConstant* Radius = CastChecked<UDistributionFloatConstant>(Sphere->StartRadius.Distribution);
						Radius->Constant = 2.0f;
						Radius->bIsDirty = true;
						Sphere->StartRadius.Initialize();
					}
				}
			}
			CopyLevel->TypeDataModule = NewObject<UParticleModuleTypeDataGpu>(Particle, NAME_None, RF_Transactional);
			CopyLevel->TypeDataModule->LODValidity = 1;
			Particle->Emitters.Add(Copy);
		};
		AddSecondary(TEXT("FleshFineDroplets"), TEXT("/Game/TopDown/Combat/FX/M_FleshHitFineDrops.M_FleshHitFineDrops"), false);
		AddSecondary(TEXT("FleshContactSplash"), TEXT("/Game/TopDown/Combat/FX/M_FleshHitImpact.M_FleshHitImpact"), true);
		Particle->LODDistances.SetNum(1);
		Particle->LODDistances[0] = 0.0f;
		Particle->LODSettings.SetNum(1);
		Particle->bUseFixedRelativeBoundingBox = true;
		Particle->FixedRelativeBoundingBox = FBox(FVector(-160) * EffectScale, FVector(160) * EffectScale);
		Particle->UpdateAllModuleLists();
		Particle->BuildEmitters();
		Particle->PostEditChange();
		Particle->MarkPackageDirty();
		UE_LOG(LogTemp, Display, TEXT("FleshHit: authored liquid sheets, fine droplets and contact splash, size %.2f"), SizeScale);
	}));

#endif
