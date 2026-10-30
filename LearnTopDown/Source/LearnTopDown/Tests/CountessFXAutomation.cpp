#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS

#include "CharacterPipelineQA.h"

#include "../CountessSkillComponent.h"
#include "../KwangCharacter.h"
#include "Components/AudioComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Animation/AnimSequence.h"
#include "Dom/JsonObject.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInterface.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "Particles/ParticleEmitter.h"
#include "Particles/ParticleLODLevel.h"
#include "Particles/Location/ParticleModuleLocationBoneSocket.h"
#include "Particles/Material/ParticleModuleMeshMaterial.h"
#include "Serialization/JsonSerializer.h"
#include "Sound/SoundBase.h"

// 화면에 입자가 실제로 생성되는지, 원본 뼈 입력과 상세 LOD가 적용되는지 별도로 검증한다.
static FAutoConsoleCommandWithWorldAndArgs SnapshotCountessFX(
	TEXT("CountessFXQA.State"), TEXT("PIE only: filename token"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (!World || World->WorldType != EWorldType::PIE || Args.Num() != 1 ||
			Args[0].Contains(TEXT("/")) || Args[0].Contains(TEXT("\\")))
		{
			return;
		}
		AKwangCharacter* Character = Cast<AKwangCharacter>(UGameplayStatics::GetPlayerCharacter(World, 0));
		if (!Character)
		{
			return;
		}
		TSharedRef<FJsonObject> Json = MakeShared<FJsonObject>();
		Json->SetNumberField(TEXT("time"), World->GetTimeSeconds());
		Json->SetBoolField(TEXT("detailed_presentation"), UCountessSkillComponent::UsesDetailedPresentation());
		Json->SetBoolField(TEXT("skill_audio_enabled"), UCountessSkillComponent::UsesSkillAudio());
		Json->SetBoolField(TEXT("skill_voice_enabled"), UCountessSkillComponent::UsesSkillVoice());
		Json->SetBoolField(TEXT("q_sword_audio_enabled"), UCountessSkillComponent::UsesQSwordAudio());
		Json->SetBoolField(TEXT("q_rush_audio_enabled"), UCountessSkillComponent::UsesQRushAudio());
		TArray<TSharedPtr<FJsonValue>> Effects;
		for (TObjectIterator<UParticleSystemComponent> Iterator; Iterator; ++Iterator)
		{
			UParticleSystemComponent* Particle = *Iterator;
			if (!IsValid(Particle) || !Particle->IsRegistered() || Particle->GetWorld() != World ||
				!Particle->ComponentHasTag(TEXT("CountessSkillFX")))
			{
				continue;
			}
			TSharedRef<FJsonObject> Effect = MakeShared<FJsonObject>();
			Effect->SetStringField(TEXT("template"), Particle->Template ? Particle->Template->GetName() : TEXT(""));
			Effect->SetBoolField(TEXT("active"), Particle->IsActive());
			Effect->SetNumberField(TEXT("particles"), Particle->GetNumActiveParticles());
			Effect->SetNumberField(TEXT("lod"), Particle->GetCurrentLODIndex());
			Effect->SetBoolField(TEXT("direct_lod"), Particle->bOverrideLODMethod && Particle->LODMethod == PARTICLESYSTEMLODMETHOD_DirectSet);
			AActor* Source = nullptr;
			Particle->GetActorParameter(TEXT("BoneSocketActor"), Source);
			Effect->SetStringField(TEXT("bone_source"), IsValid(Source) ? Source->GetName() : TEXT(""));
			Effect->SetBoolField(TEXT("bone_source_has_mesh"), IsValid(Source) && Source->FindComponentByClass<USkeletalMeshComponent>());
			Effect->SetStringField(TEXT("attach_socket"), Particle->GetAttachSocketName().ToString());
			Effect->SetStringField(TEXT("attach_parent"), Particle->GetAttachParent() ? Particle->GetAttachParent()->GetClass()->GetName() : TEXT(""));
			Effects.Add(MakeShared<FJsonValueObject>(Effect));
		}
		Json->SetArrayField(TEXT("effects"), Effects);
		TArray<TSharedPtr<FJsonValue>> Clones;
		int32 Proxies = 0;
		for (TActorIterator<AActor> Iterator(World); Iterator; ++Iterator)
		{
			if (Iterator->ActorHasTag(TEXT("CountessSkillFXProxy")))
			{
				++Proxies;
			}
			if (!Iterator->ActorHasTag(TEXT("CountessSkillShadowClone")))
			{
				continue;
			}
			TSharedRef<FJsonObject> Clone = MakeShared<FJsonObject>();
			Clone->SetStringField(TEXT("name"), Iterator->GetName());
			Clone->SetBoolField(TEXT("collision"), Iterator->GetActorEnableCollision());
			Clone->SetBoolField(TEXT("damageable"), Iterator->CanBeDamaged());
			USkeletalMeshComponent* Mesh = Iterator->FindComponentByClass<USkeletalMeshComponent>();
			Clone->SetStringField(TEXT("material"), Mesh && Mesh->GetMaterial(0) ? Mesh->GetMaterial(0)->GetName() : TEXT(""));
			Clone->SetStringField(TEXT("location"), Iterator->GetActorLocation().ToString());
			Clones.Add(MakeShared<FJsonValueObject>(Clone));
		}
		Json->SetArrayField(TEXT("clones"), Clones);
		Json->SetNumberField(TEXT("proxy_count"), Proxies);
		TArray<TSharedPtr<FJsonValue>> Sounds;
		for (int32 Index = 0; Index < 4; ++Index)
		{
			const FCountessSkillDefinition* Definition = Character->GetCountessSkills()->GetDefinition(static_cast<ECountessSkill>(Index));
			Sounds.Add(MakeShared<FJsonValueString>(Definition && Definition->CastSound ? Definition->CastSound->GetName() : TEXT("")));
		}
		Json->SetArrayField(TEXT("cast_sound_assets"), Sounds);
		TArray<TSharedPtr<FJsonValue>> AudioStates;
		for (TObjectIterator<UAudioComponent> Iterator; Iterator; ++Iterator)
		{
			if (IsValid(*Iterator) && Iterator->GetWorld() == World &&
				(Iterator->GetAttachParent() == Character->GetMesh() || Iterator->ComponentHasTag(TEXT("CountessSkillSFX"))))
			{
				TSharedRef<FJsonObject> Audio = MakeShared<FJsonObject>();
				Audio->SetBoolField(TEXT("playing"), Iterator->IsPlaying());
				Audio->SetStringField(TEXT("sound"), Iterator->Sound ? Iterator->Sound->GetName() : TEXT(""));
				Audio->SetBoolField(TEXT("follows_character"), Iterator->GetAttachParent() == Character->GetMesh());
				AudioStates.Add(MakeShared<FJsonValueObject>(Audio));
			}
		}
		Json->SetArrayField(TEXT("audio"), AudioStates);
		FString Text;
		FJsonSerializer::Serialize(Json, TJsonWriterFactory<>::Create(&Text));
		FFileHelper::SaveStringToFile(Text, *(CharacterPipelineQA::GetOutputDirectory(TEXT("QA/CountessSkillFXRestoration")) / (Args[0] + TEXT(".json"))),
			FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
	}));

// 비교용 허수아비에 시전자와 같은 골격을 붙인다. 판정·HP는 그대로 두고 원본 대상 뼈 FX를 관찰한다.
static FAutoConsoleCommandWithWorldAndArgs AttachCountessFixtureMesh(
	TEXT("CountessFXQA.TargetMesh"), TEXT("PIE only: target actor name"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (!World || World->WorldType != EWorldType::PIE || Args.Num() != 1)
		{
			return;
		}
		ACharacter* Character = UGameplayStatics::GetPlayerCharacter(World, 0);
		for (TActorIterator<AActor> Iterator(World); Iterator; ++Iterator)
		{
			AActor* Target = *Iterator;
			if (Target->GetName() != Args[0] || !Character || Target->FindComponentByClass<USkeletalMeshComponent>())
			{
				continue;
			}
			float Radius, HalfHeight;
			Target->GetSimpleCollisionCylinder(Radius, HalfHeight);
			USkeletalMeshComponent* Mesh = NewObject<USkeletalMeshComponent>(Target);
			Target->AddInstanceComponent(Mesh);
			Mesh->SetupAttachment(Target->GetRootComponent());
			Mesh->SetRelativeLocation(FVector(0, 0, -HalfHeight));
			Mesh->SetRelativeRotation(FRotator(0, 90, 0));
			Mesh->SetSkeletalMeshAsset(Character->GetMesh()->GetSkeletalMeshAsset());
			Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			Mesh->SetCanEverAffectNavigation(false);
			Mesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
			Mesh->RegisterComponent();
			UAnimSequence* Idle = LoadObject<UAnimSequence>(nullptr, TEXT("/Game/ParagonCountess/Characters/Heroes/Countess/Animations/Idle_Relaxed.Idle_Relaxed"));
			Mesh->PlayAnimation(Idle, true);
			TArray<UStaticMeshComponent*> Boxes;
			Target->GetComponents(Boxes);
			for (UStaticMeshComponent* Box : Boxes)
			{
				Box->SetVisibility(false);
			}
			break;
		}
	}));

// 에디터에서 파동 복사본의 물 재질만 교체한다. Python에 노출되지 않은 MeshMaterials를 사용한다.
static FAutoConsoleCommand AdaptCountessTideMaterial(
	TEXT("CountessFXQA.AdaptTide"), TEXT("Editor only: adapt the private detailed tide asset"),
	FConsoleCommandDelegate::CreateLambda([]()
	{
		UParticleSystem* Particle = LoadObject<UParticleSystem>(nullptr,
			TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessDarkTideDetailed.P_CountessDarkTideDetailed"));
		UMaterialInterface* Material = LoadObject<UMaterialInterface>(nullptr,
			TEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessTideRefraction.M_CountessTideRefraction"));
		if (!Particle || !Material)
		{
			return;
		}
		Particle->Modify();
		int32 Replaced = 0;
		int32 Adapted = 0;
		for (UParticleEmitter* Emitter : Particle->Emitters)
		{
			if (!Emitter)
			{
				continue;
			}
			for (UParticleLODLevel* Level : Emitter->LODLevels)
			{
				if (!Level)
				{
					continue;
				}
				for (UParticleModule* Module : Level->Modules)
				{
					UParticleModuleMeshMaterial* MeshMaterial = Cast<UParticleModuleMeshMaterial>(Module);
					if (!MeshMaterial)
					{
						continue;
					}
					for (TObjectPtr<UMaterialInterface>& Entry : MeshMaterial->MeshMaterials)
					{
						if (Entry && Entry->GetPathName() == TEXT("/Game/ParagonCountess/FX/Materials/Water/Hydro/M_Hydro_Water_Particles_Body_Inst.M_Hydro_Water_Particles_Body_Inst"))
						{
							MeshMaterial->Modify();
							Entry = Material;
							++Replaced;
						}
						if (Entry == Material)
						{
							++Adapted;
						}
					}
				}
			}
		}
		Particle->PostEditChange();
		Particle->MarkPackageDirty();
		TSharedRef<FJsonObject> Json = MakeShared<FJsonObject>();
		Json->SetNumberField(TEXT("replaced"), Replaced);
		Json->SetNumberField(TEXT("adapted"), Adapted);
		FString Text;
		FJsonSerializer::Serialize(Json, TJsonWriterFactory<>::Create(&Text));
		FFileHelper::SaveStringToFile(Text, *(FPaths::ProjectSavedDir() / TEXT("QA/CountessSkillFXFull/tide-native-adaptation.json")),
			FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
	}));

// A/F 전용 사본의 bone 발원만 해제한다. Python 비공개 속성을 엔진 타입으로 처리한다.
static FAutoConsoleCommand DisableCountessExtraBoneSources(
	TEXT("CountessFXQA.DisableExtraBoneSources"), TEXT("Editor only: one owned A/F particle copy name"),
	FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args)
	{
		const TArray<FString> Allowed = {TEXT("P_CountessBloodSealGather"), TEXT("P_CountessBloodSealBurst"),
			TEXT("P_CountessBloodSealGround"), TEXT("P_CountessShadowAmbushSlash"), TEXT("P_CountessShadowContact")};
		if (Args.Num() != 1 || !Allowed.Contains(Args[0])) { return; }
		const FString Path = TEXT("/Game/TopDown/Characters/Countess/FX/") + Args[0] + TEXT(".") + Args[0];
		UParticleSystem* Particle = LoadObject<UParticleSystem>(nullptr, *Path);
		if (!Particle) { return; }
		int32 Disabled = 0;
		Particle->Modify();
		for (UParticleEmitter* Emitter : Particle->Emitters)
		{
			if (!Emitter) { continue; }
			for (UParticleLODLevel* Level : Emitter->LODLevels)
			{
				if (!Level) { continue; }
				for (UParticleModule* Module : Level->Modules)
				{
					UParticleModuleLocationBoneSocket* Bone = Cast<UParticleModuleLocationBoneSocket>(Module);
					if (!Bone || Bone->GetOutermost() != Particle->GetOutermost()) { continue; }
					Bone->Modify();
					Bone->bEnabled = false;
					++Disabled;
				}
			}
		}
		Particle->PostEditChange();
		Particle->MarkPackageDirty();
		TSharedRef<FJsonObject> Json = MakeShared<FJsonObject>();
		Json->SetBoolField(TEXT("passed"), true);
		Json->SetStringField(TEXT("asset"), Path);
		Json->SetNumberField(TEXT("disabled"), Disabled);
		FString Text;
		FJsonSerializer::Serialize(Json, TJsonWriterFactory<>::Create(&Text));
		const FString Output = CharacterPipelineQA::GetOutputDirectory(TEXT("QA/CharacterPipeline"));
		FFileHelper::SaveStringToFile(Text, *(Output / (TEXT("countess-af-bones-") + Args[0] + TEXT(".json"))),
			FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
	}));

#endif
