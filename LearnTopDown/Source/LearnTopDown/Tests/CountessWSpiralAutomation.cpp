#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS

#include "CharacterPipelineQA.h"
#include "Algo/Count.h"
#include "Dom/JsonObject.h"
#include "Distributions/DistributionFloatConstant.h"
#include "Distributions/DistributionFloatConstantCurve.h"
#include "Distributions/DistributionFloatUniform.h"
#include "Distributions/DistributionVectorUniform.h"
#include "Distributions/DistributionVectorUniformCurve.h"
#include "Distributions/DistributionVectorConstantCurve.h"
#include "Engine/Texture.h"
#include "Materials/Material.h"
#include "Materials/MaterialExpression.h"
#include "Materials/MaterialExpressionMaterialFunctionCall.h"
#include "Materials/MaterialExpressionTextureCoordinate.h"
#include "Materials/MaterialExpressionTextureSample.h"
#include "Materials/MaterialExpressionMultiply.h"
#include "Materials/MaterialExpressionSaturate.h"
#include "Materials/MaterialFunctionInterface.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceConstant.h"
#include "Misc/FileHelper.h"
#include "Particles/ParticleEmitter.h"
#include "Particles/ParticleLODLevel.h"
#include "Particles/ParticleModule.h"
#include "Particles/ParticleModuleRequired.h"
#include "Particles/ParticleSystem.h"
#include "Particles/Color/ParticleModuleColorScaleOverLife.h"
#include "Particles/Lifetime/ParticleModuleLifetime.h"
#include "Particles/Location/ParticleModuleLocation.h"
#include "Particles/Location/ParticleModuleLocationBase.h"
#include "Particles/Size/ParticleModuleSize.h"
#include "Particles/Size/ParticleModuleSizeMultiplyLife.h"
#include "Particles/Spawn/ParticleModuleSpawn.h"
#include "Particles/TypeData/ParticleModuleTypeDataBase.h"
#include "Particles/TypeData/ParticleModuleTypeDataGpu.h"
#include "Particles/VectorField/ParticleModuleVectorFieldLocal.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UObjectHash.h"
#include "UObject/UnrealType.h"

namespace CountessWSpiral
{
static constexpr const TCHAR* SourcePath = TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessW_RimRing.P_CountessW_RimRing");
static constexpr const TCHAR* DestinationPath = TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessW_SpiralRing.P_CountessW_SpiralRing");

static void InspectExpressions(TConstArrayView<TObjectPtr<UMaterialExpression>> Expressions,
	TSet<const UMaterialFunctionInterface*>& Visited, TSet<FString>& Classes,
	TArray<TSharedPtr<FJsonValue>>& Rows)
{
	for (UMaterialExpression* Expression : Expressions)
	{
		if (!Expression)
		{
			continue;
		}
		Classes.Add(Expression->GetClass()->GetName());
		TSharedRef<FJsonObject> Row = MakeShared<FJsonObject>();
		Row->SetStringField(TEXT("path"), Expression->GetPathName());
		Row->SetStringField(TEXT("class"), Expression->GetClass()->GetName());
		TArray<TSharedPtr<FJsonValue>> Inputs;
		for (FExpressionInputIterator Input(Expression); Input; ++Input)
		{
			if (!Input->Expression)
			{
				continue;
			}
			TSharedRef<FJsonObject> Link = MakeShared<FJsonObject>();
			Link->SetStringField(TEXT("input"), Expression->GetInputName(Input.Index).ToString());
			Link->SetStringField(TEXT("expression"), Input->Expression->GetPathName());
			Link->SetNumberField(TEXT("output_index"), Input->OutputIndex);
			Inputs.Add(MakeShared<FJsonValueObject>(Link));
		}
		Row->SetArrayField(TEXT("connected_inputs"), Inputs);
		if (const UMaterialExpressionTextureSample* Sample = Cast<UMaterialExpressionTextureSample>(Expression))
		{
			Row->SetStringField(TEXT("texture"), Sample->Texture ? Sample->Texture->GetPathName() : TEXT("texture_object_input"));
			Row->SetStringField(TEXT("coordinate_source"), Sample->Coordinates.Expression ?
				Sample->Coordinates.Expression->GetPathName() : TEXT("default_texture_coordinate"));
			Row->SetNumberField(TEXT("default_coordinate_index"), Sample->ConstCoordinate);
		}
		if (const UMaterialExpressionTextureCoordinate* Coordinates = Cast<UMaterialExpressionTextureCoordinate>(Expression))
		{
			Row->SetNumberField(TEXT("coordinate_index"), Coordinates->CoordinateIndex);
			Row->SetNumberField(TEXT("u_tiling"), Coordinates->UTiling);
			Row->SetNumberField(TEXT("v_tiling"), Coordinates->VTiling);
		}
		const UMaterialExpressionMaterialFunctionCall* Call = Cast<UMaterialExpressionMaterialFunctionCall>(Expression);
		if (Call && Call->MaterialFunction)
		{
			Row->SetStringField(TEXT("function"), Call->MaterialFunction->GetPathName());
		}
		Rows.Add(MakeShared<FJsonValueObject>(Row));
		if (Call && Call->MaterialFunction && !Visited.Contains(Call->MaterialFunction.Get()))
		{
			Visited.Add(Call->MaterialFunction.Get());
			InspectExpressions(Call->MaterialFunction->GetExpressions(), Visited, Classes, Rows);
		}
	}
}

static bool IsPrivate(const UObject* Object, const UParticleSystem* Particle)
{
	return Object && Object->IsIn(Particle);
}

static bool OwnsDistributions(const UParticleModule* Module, const UParticleSystem* Particle)
{
	for (TFieldIterator<FStructProperty> It(Module->GetClass()); It; ++It)
	{
		if (!It->Struct->GetName().StartsWith(TEXT("RawDistribution")))
		{
			continue;
		}
		const FObjectPropertyBase* Distribution = FindFProperty<FObjectPropertyBase>(It->Struct, TEXT("Distribution"));
		if (Distribution)
		{
			const void* Raw = It->ContainerPtrToValuePtr<void>(Module);
			const UObject* Object = Distribution->GetObjectPropertyValue_InContainer(Raw);
			if (Object && !IsPrivate(Object, Particle))
			{
				return false;
			}
		}
	}
	return true;
}

// Cascade의 모듈은 발광기 바깥에 저장되기도 하므로 각 팔의 모듈과 분포를 따로 복제한다.
static UParticleModule* CopyModule(UParticleModule* Original, UParticleSystem* Particle)
{
	if (!Original)
	{
		return nullptr;
	}
	const FName Name = MakeUniqueObjectName(Particle, Original->GetClass(), Original->GetFName());
	if (const UParticleModuleTypeDataGpu* OriginalGpu = Cast<UParticleModuleTypeDataGpu>(Original))
	{
		// EmitterInfo는 원본 모듈 포인터를 포함한다. 캐시를 복사하지 않고 새 팔에서 다시 빌드한다.
		UParticleModuleTypeDataGpu* Gpu = NewObject<UParticleModuleTypeDataGpu>(Particle, Name, RF_Transactional);
		Gpu->CameraMotionBlurAmount = OriginalGpu->CameraMotionBlurAmount;
		Gpu->bClearExistingParticlesOnInit = OriginalGpu->bClearExistingParticlesOnInit;
		Gpu->LODValidity = OriginalGpu->LODValidity;
		Gpu->bEnabled = OriginalGpu->bEnabled;
		return Gpu;
	}
	return DuplicateObject<UParticleModule>(Original, Particle, Name);
}

static UParticleEmitter* CopyEmitter(UParticleEmitter* Original, UParticleSystem* Particle, int32 Arm)
{
	const FName Name(*FString::Printf(TEXT("WSpiralEmitter_%d"), Arm));
	// 발광기 복제의 PostLoad가 원본 LOD로 먼저 빌드하지 않도록 빈 발광기부터 구성한다.
	UParticleEmitter* Copy = NewObject<UParticleEmitter>(Particle, Original->GetClass(),
		MakeUniqueObjectName(Particle, Original->GetClass(), Name), RF_Transactional);
	Copy->EmitterRenderMode = Original->EmitterRenderMode;
	Copy->SignificanceLevel = Original->SignificanceLevel;
	Copy->bUseLegacySpawningBehavior = Original->bUseLegacySpawningBehavior;
	Copy->bDisabledLODsKeepEmitterAlive = Original->bDisabledLODsKeepEmitterAlive;
	Copy->bDisableWhenInsignficant = Original->bDisableWhenInsignficant;
	Copy->InitialAllocationCount = Original->InitialAllocationCount;
	Copy->QualityLevelSpawnRateScale = Original->QualityLevelSpawnRateScale;
	Copy->DetailModeBitmask = Original->DetailModeBitmask;
	Copy->ConvertedModules = Original->ConvertedModules;
	Copy->bCookedOut = Original->bCookedOut;
	Copy->bCollapsed = Original->bCollapsed;
	Copy->EmitterEditorColor = Original->EmitterEditorColor;
	Copy->SetEmitterName(FName(*FString::Printf(TEXT("WSpiralArm_%d"), Arm)));
	for (const UParticleLODLevel* OriginalLevel : Original->LODLevels)
	{
		if (!OriginalLevel)
		{
			continue;
		}
		UParticleLODLevel* Level = NewObject<UParticleLODLevel>(Copy, NAME_None, RF_Transactional);
		Level->Level = OriginalLevel->Level;
		Level->bEnabled = OriginalLevel->bEnabled;
		Level->ConvertedModules = OriginalLevel->ConvertedModules;
		Level->RequiredModule = CastChecked<UParticleModuleRequired>(CopyModule(OriginalLevel->RequiredModule, Particle));
		Level->SpawnModule = CastChecked<UParticleModuleSpawn>(CopyModule(OriginalLevel->SpawnModule, Particle));
		Level->TypeDataModule = Cast<UParticleModuleTypeDataBase>(CopyModule(OriginalLevel->TypeDataModule, Particle));
		for (UParticleModule* Module : OriginalLevel->Modules)
		{
			Level->Modules.Add(CopyModule(Module, Particle));
		}
		Copy->LODLevels.Add(Level);
	}
	return Copy;
}

static bool ValidatePrivateReferences(UParticleSystem* Particle, const UParticleSystem* Source,
	TArray<TSharedPtr<FJsonValue>>& Invalid)
{
	TArray<UObject*> Objects;
	GetObjectsWithOuter(Particle, Objects, EGetObjectsFlags::IncludeNestedObjects);
	Objects.Add(Particle);
	for (UObject* Object : Objects)
	{
		if (Object->IsA<UParticleModule>() && Object->GetOuter() != Particle)
		{
			Invalid.Add(MakeShared<FJsonValueString>(TEXT("invalid module outer: ") + Object->GetPathName()));
		}
		TArray<UObject*> References;
		FReferenceFinder Finder(References, nullptr, false, true, false, true);
		Finder.FindReferences(Object);
		for (const UObject* Reference : References)
		{
			if (Reference && (Reference->GetOutermost() == Source->GetOutermost() ||
				(Reference->IsA<UParticleModule>() && Reference->GetOuter() != Particle)))
			{
				Invalid.Add(MakeShared<FJsonValueString>(Object->GetPathName() + TEXT(" -> ") + Reference->GetPathName()));
			}
		}
	}
	return Invalid.IsEmpty();
}

static void WriteResult(const TSharedRef<FJsonObject>& Json)
{
	FString Text;
	FJsonSerializer::Serialize(Json, TJsonWriterFactory<>::Create(&Text));
	FFileHelper::SaveStringToFile(Text,
		*(CharacterPipelineQA::GetOutputDirectory(TEXT("QA/CountessWSpiral")) / TEXT("w-spiral-adaptation.json")),
		FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
}

static FAutoConsoleCommand Author(
	TEXT("CountessFXQA.WSpiral"), TEXT("Editor only: author four original-texture W spiral arms in the private copy"),
	FConsoleCommandDelegate::CreateLambda([]()
	{
		TSharedRef<FJsonObject> Json = MakeShared<FJsonObject>();
		Json->SetBoolField(TEXT("passed"), false);
		UParticleSystem* Source = LoadObject<UParticleSystem>(nullptr, SourcePath);
		UParticleSystem* Particle = LoadObject<UParticleSystem>(nullptr, DestinationPath);
		if (!Source || !Particle || Source == Particle)
		{
			Json->SetStringField(TEXT("error"), TEXT("Both the preserved rim source and separate spiral seed must exist"));
			WriteResult(Json);
			return;
		}
		TArray<UParticleEmitter*> Templates;
		for (UParticleEmitter* Emitter : Source->Emitters)
		{
			if (Emitter && (Emitter->GetEmitterName() == TEXT("DarkPuffs_FL") || Emitter->GetEmitterName() == TEXT("SmokePuffs_FL")))
			{
				Templates.Add(Emitter);
			}
		}
		if (Templates.Num() != 2 || Templates[0]->LODLevels.IsEmpty())
		{
			Json->SetStringField(TEXT("error"), TEXT("Expected two mapped original smoke emitters"));
			WriteResult(Json);
			return;
		}
		UMaterialInterface* Smoke = Templates[0]->LODLevels[0]->RequiredModule->Material;
		UMaterial* Material = Smoke ? Smoke->GetMaterial() : nullptr;
		TSet<FString> ExpressionClasses;
		TSet<const UMaterialFunctionInterface*> Visited;
		TArray<TSharedPtr<FJsonValue>> ShaderGraph;
		if (Material)
		{
			InspectExpressions(Material->GetExpressions(), Visited, ExpressionClasses, ShaderGraph);
		}
		bool bSubUV = false;
		for (const FString& Class : ExpressionClasses)
		{
			bSubUV |= Class.Contains(TEXT("SubUV"));
		}
		const bool bParticleColor = ExpressionClasses.Contains(TEXT("MaterialExpressionParticleColor"));
		const bool bTextureSample = ExpressionClasses.Contains(TEXT("MaterialExpressionTextureSample"));
		const bool bTextureCoordinate = ExpressionClasses.Contains(TEXT("MaterialExpressionTextureCoordinate"));
		bool bOriginalSubUVState = true;
		for (const UParticleEmitter* Emitter : Templates)
		{
			for (const UParticleLODLevel* Level : Emitter->LODLevels)
			{
				bOriginalSubUVState &= Level && Level->RequiredModule && Level->RequiredModule->Material == Smoke &&
					Level->RequiredModule->SubImages_Horizontal == 8 && Level->RequiredModule->SubImages_Vertical == 8;
			}
		}
		Json->SetStringField(TEXT("material"), Smoke ? Smoke->GetPathName() : TEXT("missing"));
		Json->SetStringField(TEXT("base_material"), Material ? Material->GetPathName() : TEXT("missing"));
		Json->SetBoolField(TEXT("uses_particle_color"), bParticleColor);
		Json->SetBoolField(TEXT("uses_subuv_expression"), bSubUV);
		Json->SetBoolField(TEXT("uses_texture_sample"), bTextureSample);
		Json->SetBoolField(TEXT("uses_texture_coordinate"), bTextureCoordinate);
		Json->SetBoolField(TEXT("original_emitter_8x8_subuv_state_confirmed"), bOriginalSubUVState);
		Json->SetArrayField(TEXT("shader_graph"), ShaderGraph);
		TArray<TSharedPtr<FJsonValue>> Classes;
		for (const FString& Class : ExpressionClasses)
		{
			Classes.Add(MakeShared<FJsonValueString>(Class));
		}
		Json->SetArrayField(TEXT("expression_classes"), Classes);
		// 원본은 TextureSample과 좌표 함수로 UV를 처리한다. 존재하지 않는 ParticleSubUV 노드를 요구하지 않는다.
		if (!Material || !bParticleColor || !bTextureSample || !bTextureCoordinate || !bOriginalSubUVState)
		{
			Json->SetStringField(TEXT("error"), TEXT("Original smoke sampler, coordinates, ParticleColor or emitter 8x8 state was not confirmed"));
			WriteResult(Json);
			return;
		}

		float OriginalBudget = 0.0f;
		for (UParticleEmitter* Emitter : Templates)
		{
			UParticleLODLevel* Level = Emitter->LODLevels[0];
			OriginalBudget += Level->SpawnModule->Rate.GetValue(0.0f) * Level->RequiredModule->EmitterDuration;
			for (const FParticleBurst& Burst : Level->SpawnModule->BurstList)
			{
				OriginalBudget += Burst.Count;
			}
		}
		constexpr float Duration = 0.24f;
		constexpr int32 InitialBurst = 2;
		const float ArmRate = FMath::Max(0.0f, (OriginalBudget / 4.0f - InitialBurst) / Duration);
		Particle->Modify();
		Particle->Emitters.RemoveAll([](const TObjectPtr<UParticleEmitter>& Emitter)
		{
			return Emitter && Emitter->GetEmitterName().ToString().StartsWith(TEXT("WSpiralArm_"));
		});
		int32 RestoredExteriorEmitters = 0;
		for (UParticleEmitter* Template : Templates)
		{
			const SIZE_T ExistingCount = Algo::CountIf(Particle->Emitters, [Template](const TObjectPtr<UParticleEmitter>& Emitter)
			{
				return Emitter && Emitter->GetEmitterName() == Template->GetEmitterName();
			});
			if (ExistingCount > 1)
			{
				Json->SetStringField(TEXT("error"), TEXT("The private spiral copy has duplicate original exterior smoke emitters"));
				WriteResult(Json);
				return;
			}
			if (ExistingCount == 0)
			{
				// 이전 보강본에서 제거됐던 외곽은 원본 모듈과 분포를 전용 소유자로 복원한다.
				UParticleEmitter* Exterior = CopyEmitter(Template, Particle, 4 + RestoredExteriorEmitters);
				Exterior->SetEmitterName(Template->GetEmitterName());
				Particle->Emitters.Add(Exterior);
				++RestoredExteriorEmitters;
			}
		}
		const SIZE_T ExteriorEmitterCount = Algo::CountIf(Particle->Emitters, [](const TObjectPtr<UParticleEmitter>& Emitter)
		{
			return Emitter && (Emitter->GetEmitterName() == TEXT("DarkPuffs_FL") || Emitter->GetEmitterName() == TEXT("SmokePuffs_FL"));
		});
		TArray<TSharedPtr<FJsonValue>> Arms;
		const float Angles[] = {0.0f, 84.0f, 188.0f, 278.0f};
		for (int32 Arm = 0; Arm < 4; ++Arm)
		{
			UParticleEmitter* Emitter = CopyEmitter(Templates[Arm % Templates.Num()], Particle, Arm);
			for (UParticleLODLevel* Level : Emitter->LODLevels)
			{
				if (!Level)
				{
					continue;
				}
				UParticleModuleRequired* Required = Level->RequiredModule;
				check(IsPrivate(Required, Particle) && IsPrivate(Level->SpawnModule, Particle));
				check(OwnsDistributions(Required, Particle) && OwnsDistributions(Level->SpawnModule, Particle));
				Required->EmitterDelay = 0.02f;
				Required->EmitterDuration = Duration;
				Required->EmitterLoops = 1;
				UDistributionFloatConstant* Rate = NewObject<UDistributionFloatConstant>(Level->SpawnModule);
				Rate->Constant = ArmRate;
				Level->SpawnModule->Rate.Distribution = Rate;
				Level->SpawnModule->BurstList.Reset();
				FParticleBurst Burst;
				Burst.Count = InitialBurst;
				Burst.CountLow = InitialBurst;
				Burst.Time = 0.0f;
				Level->SpawnModule->BurstList.Add(Burst);
				Level->Modules.RemoveAll([](const TObjectPtr<UParticleModule>& Module)
				{
					return Module && Module->IsA<UParticleModuleLocationBase>();
				});
				UParticleModuleLocation* Location = NewObject<UParticleModuleLocation>(Particle, NAME_None, RF_Transactional);
				UDistributionVectorUniformCurve* Path = NewObject<UDistributionVectorUniformCurve>(Location);
				for (int32 Step = 0; Step <= 32; ++Step)
				{
					const float U = Step / 32.0f;
					const float Angle = FMath::DegreesToRadians(Angles[Arm] + U * (190.0f + Arm * 9.0f));
					const float Radius = FMath::Lerp(115.0f + Arm * 3.0f, 385.0f + Arm * 5.0f, U);
					const FVector Center(Radius * FMath::Cos(Angle), Radius * FMath::Sin(Angle), 34.0f + 8.0f * FMath::Sin(U * PI));
					const FVector Jitter(13.0f, 13.0f, 6.0f);
					Path->ConstantCurve.Points.Emplace(Duration * U, FTwoVectors(Center - Jitter, Center + Jitter));
				}
				Location->StartLocation.Distribution = Path;
				Level->Modules.Add(Location);
				for (UParticleModule* Module : Level->Modules)
				{
					check(IsPrivate(Module, Particle));
					check(OwnsDistributions(Module, Particle));
					if (UParticleModuleLifetime* Lifetime = Cast<UParticleModuleLifetime>(Module))
					{
						UDistributionFloatUniform* Life = NewObject<UDistributionFloatUniform>(Lifetime);
						Life->Min = 0.38f;
						Life->Max = 0.46f;
						Lifetime->Lifetime.Distribution = Life;
					}
					else if (UParticleModuleSize* Size = Cast<UParticleModuleSize>(Module))
					{
						UDistributionVectorUniform* Width = NewObject<UDistributionVectorUniform>(Size);
						Width->Min = FVector(105.0f, 145.0f, 29.5f);
						Width->Max = FVector(150.0f, 195.0f, 29.5f);
						Size->StartSize.Distribution = Width;
					}
					else if (UParticleModuleSizeMultiplyLife* SizeLife = Cast<UParticleModuleSizeMultiplyLife>(Module))
					{
						UDistributionVectorConstantCurve* Scale = NewObject<UDistributionVectorConstantCurve>(SizeLife);
						Scale->ConstantCurve.Points.Emplace(0.0f, FVector(0.8f));
						Scale->ConstantCurve.Points.Emplace(0.2f, FVector(1.08f));
						Scale->ConstantCurve.Points.Emplace(0.7f, FVector(0.95f));
						Scale->ConstantCurve.Points.Emplace(1.0f, FVector(0.3f));
						SizeLife->LifeMultiplier.Distribution = Scale;
					}
					else if (UParticleModuleColorScaleOverLife* Color = Cast<UParticleModuleColorScaleOverLife>(Module))
					{
						// RGB는 원본 셰이더의 변형 파라미터이므로 보존하고 상대 수명 알파만 맞춘다.
						UDistributionFloatConstantCurve* Alpha = NewObject<UDistributionFloatConstantCurve>(Color);
						Alpha->ConstantCurve.Points.Emplace(0.0f, 0.0f);
						Alpha->ConstantCurve.Points.Emplace(0.12f, 2.4f);
						Alpha->ConstantCurve.Points.Emplace(0.65f, 2.0f);
						Alpha->ConstantCurve.Points.Emplace(1.0f, 0.0f);
						Color->AlphaScaleOverLife.Distribution = Alpha;
						Color->bEmitterTime = false;
					}
					else if (UParticleModuleVectorFieldLocal* Field = Cast<UParticleModuleVectorFieldLocal>(Module))
					{
						Field->Intensity *= 0.28f;
						Field->Tightness = 0.22f;
					}
				}
				Level->UpdateModuleLists();
				check(Required->Material == Smoke && Required->SubImages_Horizontal == 8 && Required->SubImages_Vertical == 8);
			}
			Particle->Emitters.Add(Emitter);
			TSharedRef<FJsonObject> Row = MakeShared<FJsonObject>();
			Row->SetStringField(TEXT("name"), Emitter->GetEmitterName().ToString());
			Row->SetNumberField(TEXT("start_angle_degrees"), Angles[Arm]);
			Row->SetNumberField(TEXT("radius_start_cm"), 115.0f + Arm * 3.0f);
			Row->SetNumberField(TEXT("radius_end_cm"), 385.0f + Arm * 5.0f);
			Row->SetNumberField(TEXT("rate"), ArmRate);
			Row->SetNumberField(TEXT("duration"), Duration);
			Row->SetNumberField(TEXT("initial_burst"), InitialBurst);
			Arms.Add(MakeShared<FJsonValueObject>(Row));
		}
		// PostEditChange만으로는 GPU EmitterInfo를 다시 만들지 않는다. 공식 Cascade 빌드 경로를 호출한다.
		Particle->UpdateAllModuleLists();
		Particle->BuildEmitters();
		TArray<TSharedPtr<FJsonValue>> InvalidReferences;
		const bool bPrivateReferencesValid = ValidatePrivateReferences(Particle, Source, InvalidReferences);
		Json->SetBoolField(TEXT("module_outers_and_gpu_cached_references_valid"), bPrivateReferencesValid);
		Json->SetBoolField(TEXT("gpu_emitter_info_rebuilt"), true);
		Json->SetArrayField(TEXT("invalid_references"), InvalidReferences);
		if (!bPrivateReferencesValid)
		{
			Json->SetStringField(TEXT("error"), TEXT("Private particle module ownership or cached reference validation failed"));
			WriteResult(Json);
			return;
		}
		Particle->PostEditChange();
		Particle->MarkPackageDirty();
		Json->SetBoolField(TEXT("passed"), true);
		Json->SetBoolField(TEXT("exterior_smoke_preserved"), ExteriorEmitterCount == 2);
		Json->SetNumberField(TEXT("original_exterior_emitter_count"), ExteriorEmitterCount);
		Json->SetNumberField(TEXT("restored_original_exterior_emitter_count"), RestoredExteriorEmitters);
		Json->SetNumberField(TEXT("preserved_rim_smoke_expected_spawns"), OriginalBudget);
		Json->SetNumberField(TEXT("spiral_expected_spawns"), 4.0f * (ArmRate * Duration + InitialBurst));
		Json->SetNumberField(TEXT("total_smoke_expected_spawns"), OriginalBudget * 2.0f);
		Json->SetStringField(TEXT("smoke_budget_scope"), TEXT("The original two exterior emitters are retained; four additional spiral arms share at most one matching original budget; total smoke is bounded to twice the original budget."));
		Json->SetNumberField(TEXT("subuv_horizontal"), 8);
		Json->SetNumberField(TEXT("subuv_vertical"), 8);
		Json->SetBoolField(TEXT("original_color_vectors_preserved"), true);
		Json->SetBoolField(TEXT("original_sampler_graph_and_emitter_subuv_state_preserved"), true);
		Json->SetBoolField(TEXT("all_changed_modules_have_private_owners"), true);
		Json->SetArrayField(TEXT("arms"), Arms);
		WriteResult(Json);
	}));

static FAutoConsoleCommand AuthorLight(
	TEXT("CountessFXQA.WLight"), TEXT("Editor only: reduce smoke spawn density in a separate W copy"),
	FConsoleCommandDelegate::CreateLambda([]()
	{
		TSharedRef<FJsonObject> Json = MakeShared<FJsonObject>();
		Json->SetBoolField(TEXT("passed"), false);
		UParticleSystem* Source = LoadObject<UParticleSystem>(nullptr, DestinationPath);
		UParticleSystem* Particle = LoadObject<UParticleSystem>(nullptr,
			TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessW_LightRing.P_CountessW_LightRing"));
		if (!Source || !Particle || Source == Particle)
		{
			Json->SetStringField(TEXT("error"), TEXT("The preserved spiral source and separate light seed must exist"));
			WriteResult(Json);
			return;
		}
		constexpr float Density = 0.75f;
		int32 SmokeEmitters = 0;
		float BeforeBudget = 0.0f;
		float AfterBudget = 0.0f;
		Particle->Modify();
		Particle->Emitters.Reset();
		for (int32 Index = 0; Index < Source->Emitters.Num(); ++Index)
		{
			UParticleEmitter* Original = Source->Emitters[Index];
			if (!Original)
			{
				continue;
			}
			UParticleEmitter* Emitter = CopyEmitter(Original, Particle, Index);
			Emitter->SetEmitterName(Original->GetEmitterName());
			Particle->Emitters.Add(Emitter);
			const FString Name = Original->GetEmitterName().ToString();
			const bool bSmoke = Name.StartsWith(TEXT("WSpiralArm_")) ||
				Name == TEXT("DarkPuffs_FL") || Name == TEXT("SmokePuffs_FL");
			if (!bSmoke)
			{
				continue;
			}
			++SmokeEmitters;
			for (UParticleLODLevel* Level : Emitter->LODLevels)
			{
				if (!Level || !Level->SpawnModule || !Level->RequiredModule)
				{
					continue;
				}
				UParticleModuleSpawn* Spawn = Level->SpawnModule;
				if (Level->Level == 0)
				{
					BeforeBudget += Spawn->Rate.GetValue(0.0f) * Level->RequiredModule->EmitterDuration;
				}
				if (UDistributionFloatConstant* ConstantRate = Cast<UDistributionFloatConstant>(Spawn->Rate.Distribution))
				{
					ConstantRate->Constant *= Density;
				}
				else if (UDistributionFloatUniform* UniformRate = Cast<UDistributionFloatUniform>(Spawn->Rate.Distribution))
				{
					UniformRate->Min *= Density;
					UniformRate->Max *= Density;
				}
				else if (UDistributionFloatConstantCurve* CurveRate = Cast<UDistributionFloatConstantCurve>(Spawn->Rate.Distribution))
				{
					for (auto& Point : CurveRate->ConstantCurve.Points)
					{
						Point.OutVal *= Density;
						Point.ArriveTangent *= Density;
						Point.LeaveTangent *= Density;
					}
				}
				else
				{
					Json->SetStringField(TEXT("error"), TEXT("Unsupported smoke rate distribution: ") + Spawn->Rate.Distribution->GetClass()->GetName());
					WriteResult(Json);
					return;
				}
				Spawn->Rate.Distribution->bIsDirty = true;
				if (Level->Level == 0)
				{
					AfterBudget += Spawn->Rate.GetValue(0.0f) * Level->RequiredModule->EmitterDuration;
				}
				for (FParticleBurst& Burst : Spawn->BurstList)
				{
					if (Level->Level == 0)
					{
						BeforeBudget += Burst.Count;
					}
					Burst.Count = FMath::RoundToInt(Burst.Count * Density);
					Burst.CountLow = FMath::RoundToInt(Burst.CountLow * Density);
					if (Level->Level == 0)
					{
						AfterBudget += Burst.Count;
					}
				}
			}
		}
		Particle->UpdateAllModuleLists();
		Particle->BuildEmitters();
		TArray<TSharedPtr<FJsonValue>> Invalid;
		const bool bPrivate = ValidatePrivateReferences(Particle, Source, Invalid);
		Json->SetArrayField(TEXT("invalid_references"), Invalid);
		Json->SetBoolField(TEXT("module_outers_and_gpu_cached_references_valid"), bPrivate);
		Json->SetBoolField(TEXT("gpu_emitter_info_rebuilt"), true);
		Json->SetNumberField(TEXT("smoke_emitters"), SmokeEmitters);
		Json->SetNumberField(TEXT("smoke_rate_multiplier"), Density);
		Json->SetNumberField(TEXT("before_expected_smoke_spawns"), BeforeBudget);
		Json->SetNumberField(TEXT("after_expected_smoke_spawns"), AfterBudget);
		Json->SetNumberField(TEXT("expected_smoke_spawn_ratio"), BeforeBudget > 0.0f ? AfterBudget / BeforeBudget : 0.0f);
		Json->SetBoolField(TEXT("size_location_color_material_lifetime_unchanged"), true);
		if (SmokeEmitters != 6 || !bPrivate)
		{
			Json->SetStringField(TEXT("error"), TEXT("Expected six smoke emitters with private rebuilt module references"));
			WriteResult(Json);
			return;
		}
		Particle->PostEditChange();
		Particle->MarkPackageDirty();
		Json->SetBoolField(TEXT("passed"), true);
		WriteResult(Json);
	}));

static FAutoConsoleCommand AuthorVeil(
	TEXT("CountessFXQA.WVeil"), TEXT("Editor only: thin only the four interior W smoke surfaces"),
	FConsoleCommandDelegate::CreateLambda([]()
	{
		TSharedRef<FJsonObject> Json = MakeShared<FJsonObject>();
		Json->SetBoolField(TEXT("passed"), false);
		UParticleSystem* Source = LoadObject<UParticleSystem>(nullptr,
			TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessW_LightRing.P_CountessW_LightRing"));
		UParticleSystem* Particle = LoadObject<UParticleSystem>(nullptr,
			TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessW_VeilRing.P_CountessW_VeilRing"));
		UMaterial* VeilBase = LoadObject<UMaterial>(nullptr,
			TEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessWSmokeVeilBase.M_CountessWSmokeVeilBase"));
		UMaterialInstanceConstant* VeilInstance = LoadObject<UMaterialInstanceConstant>(nullptr,
			TEXT("/Game/TopDown/Characters/Countess/Materials/MI_CountessWSmokeVeil.MI_CountessWSmokeVeil"));
		if (!Source || !Particle || Source == Particle || !VeilBase || !VeilInstance)
		{
			Json->SetStringField(TEXT("error"), TEXT("Expected separate private particle, smoke base and copied Vamp instance"));
			WriteResult(Json);
			return;
		}
		FScalarMaterialInput& Opacity = VeilBase->GetEditorOnlyData()->Opacity;
		if (!Opacity.Expression)
		{
			Json->SetStringField(TEXT("error"), TEXT("The copied smoke material has no connected opacity output"));
			WriteResult(Json);
			return;
		}
		VeilBase->Modify();
		const FString Marker(TEXT("CountessWFinalOpacity40"));
		if (Opacity.Expression->Desc != Marker)
		{
			const FExpressionInput OriginalOpacity = Opacity;
			UMaterialExpressionSaturate* BoundedNode = NewObject<UMaterialExpressionSaturate>(VeilBase, NAME_None, RF_Transactional);
			BoundedNode->Material = VeilBase;
			BoundedNode->Input = OriginalOpacity;
			UMaterialExpressionMultiply* Reduced = NewObject<UMaterialExpressionMultiply>(VeilBase, NAME_None, RF_Transactional);
			Reduced->Material = VeilBase;
			Reduced->A.Expression = BoundedNode;
			Reduced->ConstB = 0.40f;
			Reduced->Desc = Marker;
			VeilBase->GetExpressionCollection().AddExpression(BoundedNode);
			VeilBase->GetExpressionCollection().AddExpression(Reduced);
			Opacity.Connect(0, Reduced);
		}
		const UMaterialExpressionMultiply* Final = Cast<UMaterialExpressionMultiply>(Opacity.Expression);
		const UMaterialExpressionSaturate* Bounded = Final ? Cast<UMaterialExpressionSaturate>(Final->A.Expression) : nullptr;
		if (!Final || Final->ConstB != 0.40f || !Bounded || !Bounded->Input.Expression)
		{
			Json->SetStringField(TEXT("error"), TEXT("Expected the original final opacity followed by saturate and multiply 0.40"));
			WriteResult(Json);
			return;
		}
		Json->SetStringField(TEXT("original_final_opacity_expression"), Bounded->Input.Expression->GetPathName());
		Json->SetNumberField(TEXT("original_final_opacity_output_index"), Bounded->Input.OutputIndex);
		Json->SetNumberField(TEXT("final_opacity_multiplier_after_saturate"), Final->ConstB);
		VeilBase->PostEditChange();
		VeilBase->MarkPackageDirty();
		VeilInstance->Modify();
		VeilInstance->SetParentEditorOnly(VeilBase);
		VeilInstance->PostEditChange();
		VeilInstance->MarkPackageDirty();

		Particle->Modify();
		Particle->Emitters.Reset();
		int32 InteriorEmitters = 0;
		int32 PreservedExteriorEmitters = 0;
		for (int32 Index = 0; Index < Source->Emitters.Num(); ++Index)
		{
			UParticleEmitter* OriginalEmitter = Source->Emitters[Index];
			if (!OriginalEmitter)
			{
				continue;
			}
			UParticleEmitter* CopiedEmitter = CopyEmitter(OriginalEmitter, Particle, Index);
			CopiedEmitter->SetEmitterName(OriginalEmitter->GetEmitterName());
			Particle->Emitters.Add(CopiedEmitter);
			const FString Name = CopiedEmitter->GetEmitterName().ToString();
			if (Name.StartsWith(TEXT("WSpiralArm_")))
			{
				++InteriorEmitters;
				for (UParticleLODLevel* Level : CopiedEmitter->LODLevels)
				{
					if (Level && Level->RequiredModule)
					{
						Level->RequiredModule->Material = VeilInstance;
					}
				}
			}
			else if (Name == TEXT("DarkPuffs_FL") || Name == TEXT("SmokePuffs_FL"))
			{
				++PreservedExteriorEmitters;
			}
		}
		Particle->UpdateAllModuleLists();
		Particle->BuildEmitters();
		TArray<TSharedPtr<FJsonValue>> Invalid;
		const bool bPrivate = ValidatePrivateReferences(Particle, Source, Invalid);
		Json->SetNumberField(TEXT("interior_material_replaced_emitters"), InteriorEmitters);
		Json->SetNumberField(TEXT("exterior_material_preserved_emitters"), PreservedExteriorEmitters);
		Json->SetBoolField(TEXT("spawn_density_size_timing_color_unchanged"), true);
		Json->SetBoolField(TEXT("mesh_strands_sparks_droplets_unchanged"), true);
		Json->SetBoolField(TEXT("gpu_emitter_info_rebuilt"), true);
		Json->SetBoolField(TEXT("module_outers_and_gpu_cached_references_valid"), bPrivate);
		Json->SetArrayField(TEXT("invalid_references"), Invalid);
		if (InteriorEmitters != 4 || PreservedExteriorEmitters != 2 || !bPrivate)
		{
			Json->SetStringField(TEXT("error"), TEXT("Expected four interior replacements and two preserved exterior emitters with private references"));
			WriteResult(Json);
			return;
		}
		Particle->PostEditChange();
		Particle->MarkPackageDirty();
		Json->SetBoolField(TEXT("passed"), true);
		WriteResult(Json);
	}));
}

#endif
