#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS

#include "CharacterPipelineQA.h"
#include "../SparrowCharacter.h"
#include "Components/SkeletalMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UnrealType.h"

// 읽기 전용 진단: 동일한 천 입자를 연속 추적하고 정지 전환의 모양을 관찰한다.
static FAutoConsoleCommandWithWorldAndArgs SnapshotSparrowMotionCloth(
	TEXT("SparrowMotionQA.Cloth"), TEXT("PIE only: filename token, read-only cloth particle snapshot"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (!World || World->WorldType != EWorldType::PIE || Args.Num() != 1 ||
			Args[0].Contains(TEXT("/")) || Args[0].Contains(TEXT("\\")) || Args[0].Contains(TEXT("..")))
		{
			return;
		}
		ASparrowCharacter* Character = Cast<ASparrowCharacter>(UGameplayStatics::GetPlayerCharacter(World, 0));
		USkeletalMeshComponent* Mesh = Character ? Character->GetMesh() : nullptr;
		if (!Mesh)
		{
			return;
		}
		TSharedRef<FJsonObject> Json = MakeShared<FJsonObject>();
		Json->SetNumberField(TEXT("time"), World->GetTimeSeconds());
		Json->SetNumberField(TEXT("pending_teleport_mode"), static_cast<int32>(Mesh->ClothTeleportMode));
		Json->SetStringField(TEXT("teleport_mode_observation"), TEXT("Pending component mode at snapshot time, not a history of resets consumed by the cloth solver."));
		if (const FBoolProperty* Reset = FindFProperty<FBoolProperty>(Mesh->GetClass(), TEXT("bResetAfterTeleport")))
		{
			Json->SetBoolField(TEXT("reset_after_teleport"), Reset->GetPropertyValue_InContainer(Mesh));
		}
		Mesh->WaitForExistingParallelClothSimulation_GameThread();
		TArray<TSharedPtr<FJsonValue>> Cloths;
		for (const auto& Pair : Mesh->GetCurrentClothingData_AnyThread())
		{
			const int32 Count = Pair.Value.Positions.Num();
			if (Count == 0)
			{
				continue;
			}
			TSharedRef<FJsonObject> Cloth = MakeShared<FJsonObject>();
			Cloth->SetNumberField(TEXT("index"), Pair.Key);
			Cloth->SetNumberField(TEXT("vertices"), Count);
			TArray<TSharedPtr<FJsonValue>> Points;
			TArray<TSharedPtr<FJsonValue>> Indices;
			const int32 Samples = FMath::Min(32, Count);
			for (int32 Sample = 0; Sample < Samples; ++Sample)
			{
				const int32 Index = Samples > 1 ? Sample * (Count - 1) / (Samples - 1) : 0;
				const FVector Position = Pair.Value.ComponentRelativeTransform.TransformPosition(FVector(Pair.Value.Positions[Index]));
				TArray<TSharedPtr<FJsonValue>> Coordinates;
				Coordinates.Add(MakeShared<FJsonValueNumber>(Position.X));
				Coordinates.Add(MakeShared<FJsonValueNumber>(Position.Y));
				Coordinates.Add(MakeShared<FJsonValueNumber>(Position.Z));
				Points.Add(MakeShared<FJsonValueArray>(Coordinates));
				Indices.Add(MakeShared<FJsonValueNumber>(Index));
			}
			Cloth->SetArrayField(TEXT("points"), Points);
			Cloth->SetArrayField(TEXT("particle_indices"), Indices);
			Cloths.Add(MakeShared<FJsonValueObject>(Cloth));
		}
		Json->SetArrayField(TEXT("cloth"), Cloths);
		FString Text;
		FJsonSerializer::Serialize(Json, TJsonWriterFactory<>::Create(&Text));
		FFileHelper::SaveStringToFile(Text,
			*(CharacterPipelineQA::GetOutputDirectory(TEXT("QA/SparrowMotion")) / (Args[0] + TEXT(".json"))),
			FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
	}));

#endif
