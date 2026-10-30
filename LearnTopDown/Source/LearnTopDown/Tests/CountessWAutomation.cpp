#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS

#include "CharacterPipelineQA.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleEmitter.h"
#include "Particles/ParticleLODLevel.h"
#include "Particles/ParticleModule.h"
#include "Particles/ParticleModuleRequired.h"
#include "Particles/Location/ParticleModuleLocation.h"
#include "Particles/Location/ParticleModuleLocationPrimitiveCylinder.h"
#include "Distributions/DistributionFloatConstant.h"
#include "Distributions/DistributionFloatUniform.h"
#include "Distributions/DistributionVectorConstant.h"
#include "Particles/Spawn/ParticleModuleSpawn.h"
#include "Particles/TypeData/ParticleModuleTypeDataBase.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UnrealType.h"

// Python에 숨겨진 Cascade 발광기와 모듈 연결을 읽기 전용으로 기록한다.
static FAutoConsoleCommand InventoryCountessW(
	TEXT("CountessFXQA.WInventory"), TEXT("Editor only: inspect the private W ring emitter graph"),
	FConsoleCommandDelegate::CreateLambda([]()
	{
		UParticleSystem* Particle = LoadObject<UParticleSystem>(nullptr,
			TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessW_RimRing.P_CountessW_RimRing"));
		if (!Particle)
		{
			return;
		}
		TSharedRef<FJsonObject> Json = MakeShared<FJsonObject>();
		TArray<TSharedPtr<FJsonValue>> Emitters;
		for (int32 Index = 0; Index < Particle->Emitters.Num(); ++Index)
		{
			UParticleEmitter* Emitter = Particle->Emitters[Index];
			if (!Emitter || Emitter->LODLevels.IsEmpty() || !Emitter->LODLevels[0])
			{
				continue;
			}
			UParticleLODLevel* Level = Emitter->LODLevels[0];
			TSharedRef<FJsonObject> Entry = MakeShared<FJsonObject>();
			Entry->SetNumberField(TEXT("index"), Index);
			Entry->SetStringField(TEXT("name"), Emitter->GetEmitterName().ToString());
			Entry->SetStringField(TEXT("lod_path"), Level->GetPathName());
			Entry->SetBoolField(TEXT("enabled"), Level->bEnabled);
			TArray<UParticleModule*> Modules;
			Modules.Add(Level->RequiredModule);
			Modules.Add(Level->SpawnModule);
			Modules.Add(Level->TypeDataModule);
			for (UParticleModule* Module : Level->Modules)
			{
				Modules.Add(Module);
			}
			TArray<TSharedPtr<FJsonValue>> ModuleRows;
			for (UParticleModule* Module : Modules)
			{
				if (!Module)
				{
					continue;
				}
				TSharedRef<FJsonObject> Row = MakeShared<FJsonObject>();
				Row->SetStringField(TEXT("path"), Module->GetPathName());
				Row->SetStringField(TEXT("class"), Module->GetClass()->GetName());
				TSharedRef<FJsonObject> Properties = MakeShared<FJsonObject>();
				for (TFieldIterator<FProperty> It(Module->GetClass()); It; ++It)
				{
					if (It->HasAnyPropertyFlags(CPF_Edit))
					{
						FString Value;
						It->ExportTextItem_Direct(Value, It->ContainerPtrToValuePtr<void>(Module), nullptr, Module, PPF_None);
						Properties->SetStringField(It->GetName(), Value);
					}
				}
				Row->SetObjectField(TEXT("properties"), Properties);
				ModuleRows.Add(MakeShared<FJsonValueObject>(Row));
			}
			Entry->SetArrayField(TEXT("modules"), ModuleRows);
			Emitters.Add(MakeShared<FJsonValueObject>(Entry));
		}
		Json->SetArrayField(TEXT("emitters"), Emitters);
		FString Text;
		FJsonSerializer::Serialize(Json, TJsonWriterFactory<>::Create(&Text));
		FFileHelper::SaveStringToFile(Text,
			*(CharacterPipelineQA::GetOutputDirectory(TEXT("QA/CountessW")) / TEXT("w-emitter-inventory.json")),
			FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
	}));

// 전용 W 복사본의 두 연기 발광기만 원형 선단에 배치한다. 원본 패키지는 변경하지 않는다.
static FAutoConsoleCommand PlaceCountessWOuterSmoke(
	TEXT("CountessFXQA.WOuterSmoke"), TEXT("Editor only: place private W smoke on the outer circumference"),
	FConsoleCommandDelegate::CreateLambda([]()
	{
		UParticleSystem* Particle = LoadObject<UParticleSystem>(nullptr,
			TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessW_RimRing.P_CountessW_RimRing"));
		if (!Particle)
		{
			return;
		}
		Particle->Modify();
		int32 Adapted = 0;
		for (UParticleEmitter* Emitter : Particle->Emitters)
		{
			if (!Emitter || (Emitter->GetEmitterName() != TEXT("DarkPuffs_FL") &&
				Emitter->GetEmitterName() != TEXT("SmokePuffs_FL")) || Emitter->LODLevels.IsEmpty())
			{
				continue;
			}
			UParticleLODLevel* Level = Emitter->LODLevels[0];
			if (!Level)
			{
				continue;
			}
			Level->Modify();
			const FName ModuleName(*FString::Printf(TEXT("WOuterSmokeLocation_%d"), Adapted));
			UParticleModuleLocationPrimitiveCylinder* Cylinder = FindObject<UParticleModuleLocationPrimitiveCylinder>(Particle, *ModuleName.ToString());
			if (!Cylinder)
			{
				Cylinder = NewObject<UParticleModuleLocationPrimitiveCylinder>(Particle, ModuleName, RF_Transactional);
				Cylinder->InitializeDefaults();
			}
			Cylinder->Modify();
			Cylinder->HeightAxis = PMLPC_HEIGHTAXIS_Z;
			Cylinder->SurfaceOnly = true;
			Cylinder->Velocity = false;
			Cylinder->Positive_X = Cylinder->Positive_Y = Cylinder->Positive_Z = true;
			Cylinder->Negative_X = Cylinder->Negative_Y = Cylinder->Negative_Z = true;
			UDistributionFloatUniform* Radius = NewObject<UDistributionFloatUniform>(Cylinder);
			Radius->Min = 385.0f;
			Radius->Max = 415.0f;
			Cylinder->StartRadius.Distribution = Radius;
			CastChecked<UDistributionFloatConstant>(Cylinder->StartHeight.Distribution)->Constant = 30.0f;
			CastChecked<UDistributionVectorConstant>(Cylinder->StartLocation.Distribution)->Constant = FVector(0, 0, 40);
			Level->Modules.RemoveAll([](const TObjectPtr<UParticleModule>& Module)
			{
				return Module && Module->IsA<UParticleModuleLocation>();
			});
			Level->Modules.AddUnique(Cylinder);
			Level->UpdateModuleLists();
			++Adapted;
		}
		Particle->PostEditChange();
		Particle->MarkPackageDirty();
		TSharedRef<FJsonObject> Json = MakeShared<FJsonObject>();
		Json->SetNumberField(TEXT("adapted_emitters"), Adapted);
		Json->SetNumberField(TEXT("radius_min_cm"), 385);
		Json->SetNumberField(TEXT("radius_max_cm"), 415);
		FString Text;
		FJsonSerializer::Serialize(Json, TJsonWriterFactory<>::Create(&Text));
		FFileHelper::SaveStringToFile(Text,
			*(CharacterPipelineQA::GetOutputDirectory(TEXT("QA/CountessW")) / TEXT("w-outer-smoke-adaptation.json")),
			FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
	}));

#endif
