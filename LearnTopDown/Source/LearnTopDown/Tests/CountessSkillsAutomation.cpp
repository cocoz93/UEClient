#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS

#include "CharacterPipelineQA.h"

#include "Animation/AnimBlueprint.h"
#include "Animation/AnimMontage.h"
#include "AnimGraphNode_Root.h"
#include "AnimGraphNode_Slot.h"
#include "../CountessSkillComponent.h"
#include "Dom/JsonObject.h"
#include "EdGraph/EdGraph.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "InputKeyEventArgs.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "../KwangCharacter.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Particles/ParticleSystemComponent.h"
#include "Serialization/JsonSerializer.h"
#include "Slate/SceneViewport.h"

// 최종 출력에만 스킬 슬롯을 추가한다. 기존 상체 슬롯과 보행 그래프는 보존한다.
static FAutoConsoleCommand InstallCountessFullBodySlot(
	TEXT("CountessSkillsQA.InstallFullBodySlot"), TEXT("Editor only: add skill slot after existing locomotion output"),
	FConsoleCommandDelegate::CreateLambda([]()
	{
		UAnimBlueprint* Blueprint = LoadObject<UAnimBlueprint>(nullptr,
			TEXT("/Game/TopDown/Characters/Countess/Animations/ABP_Countess_TopDown.ABP_Countess_TopDown"));
		if (!Blueprint)
		{
			return;
		}
		TArray<UEdGraph*> Graphs;
		Blueprint->GetAllGraphs(Graphs);
		for (UEdGraph* Graph : Graphs)
		{
			if (Graph->GetFName() != TEXT("AnimGraph"))
			{
				continue;
			}
			UAnimGraphNode_Root* Root = nullptr;
			for (UEdGraphNode* Node : Graph->Nodes)
			{
				if (UAnimGraphNode_Slot* Slot = Cast<UAnimGraphNode_Slot>(Node))
				{
					if (Slot->Node.SlotName == TEXT("CountessFullBody"))
					{
						UE_LOG(LogTemp, Display, TEXT("COUNTESS_FULL_BODY_SLOT_ALREADY_PRESENT"));
						return;
					}
				}
				if (UAnimGraphNode_Root* Candidate = Cast<UAnimGraphNode_Root>(Node))
				{
					Root = Candidate;
				}
			}
			UEdGraphPin* Result = Root ? Root->FindPin(TEXT("Result")) : nullptr;
			if (!Result || Result->LinkedTo.Num() != 1)
			{
				UE_LOG(LogTemp, Error, TEXT("Countess animation root does not have a single source"));
				return;
			}
			Blueprint->Modify();
			Graph->Modify();
			Root->Modify();
			UEdGraphPin* Source = Result->LinkedTo[0];
			FGraphNodeCreator<UAnimGraphNode_Slot> Creator(*Graph);
			UAnimGraphNode_Slot* Slot = Creator.CreateNode();
			Slot->Node.SlotName = TEXT("CountessFullBody");
			Slot->NodePosX = Root->NodePosX - 180;
			Slot->NodePosY = Root->NodePosY + 150;
			Creator.Finalize();
			UEdGraphPin* Input = Slot->FindPin(TEXT("Source"));
			UEdGraphPin* Output = Slot->FindPin(TEXT("Pose"));
			if (!Input || !Output)
			{
				UE_LOG(LogTemp, Error, TEXT("Countess full body slot pins unavailable"));
				return;
			}
			Result->BreakAllPinLinks();
			const UEdGraphSchema* Schema = Graph->GetSchema();
			if (!Schema->TryCreateConnection(Source, Input) || !Schema->TryCreateConnection(Output, Result))
			{
				UE_LOG(LogTemp, Error, TEXT("Countess full body slot connection failed"));
				return;
			}
			FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
			UE_LOG(LogTemp, Display, TEXT("COUNTESS_FULL_BODY_SLOT_INSTALLED"));
			return;
		}
	}));

static FAutoConsoleCommandWithWorldAndArgs InjectCountessSkillKey(
	TEXT("CountessSkillsQA.Key"), TEXT("PIE only: Press|Release Q|W|E|R"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (!World || World->WorldType != EWorldType::PIE || Args.Num() != 2)
		{
			return;
		}
		APlayerController* Controller = UGameplayStatics::GetPlayerController(World, 0);
		ULocalPlayer* Player = Controller ? Controller->GetLocalPlayer() : nullptr;
		FSceneViewport* Viewport = Player && Player->ViewportClient ? Player->ViewportClient->GetGameViewport() : nullptr;
		if (Controller && Viewport)
		{
			Controller->InputKey(FInputKeyEventArgs(Viewport, FInputDeviceId::CreateFromInternalId(0),
				FKey(*Args[1]), Args[0] == TEXT("Release") ? IE_Released : IE_Pressed, FPlatformTime::Cycles64()));
		}
	}));

static FAutoConsoleCommandWithWorldAndArgs SnapshotCountessSkills(
	TEXT("CountessSkillsQA.State"), TEXT("PIE only: filename token"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (!World || World->WorldType != EWorldType::PIE || Args.Num() != 1 || Args[0].Contains(TEXT("/")) || Args[0].Contains(TEXT("\\")))
		{
			return;
		}
		AKwangCharacter* Character = Cast<AKwangCharacter>(UGameplayStatics::GetPlayerCharacter(World, 0));
		UCountessSkillComponent* Skills = Character ? Character->GetCountessSkills() : nullptr;
		if (!Skills)
		{
			return;
		}
		TSharedRef<FJsonObject> Json = MakeShared<FJsonObject>();
		Json->SetNumberField(TEXT("time"), World->GetTimeSeconds());
		Json->SetBoolField(TEXT("enabled"), Skills->IsEnabled());
		Json->SetBoolField(TEXT("casting"), Skills->IsCasting());
		Json->SetBoolField(TEXT("combat_busy"), Character->IsCombatBusy());
		Json->SetNumberField(TEXT("active_skill"), Skills->GetActiveSkillNumber());
		Json->SetNumberField(TEXT("return_remaining"), Skills->GetReturnRemaining());
		Json->SetStringField(TEXT("feedback"), Skills->GetInputFeedback());
		UAnimInstance* Anim = Character->GetMesh()->GetAnimInstance();
		UAnimMontage* Montage = Anim ? Anim->GetCurrentActiveMontage() : nullptr;
		Json->SetStringField(TEXT("montage"), Montage ? Montage->GetName() : TEXT(""));
		Json->SetNumberField(TEXT("montage_position"), Montage ? Anim->Montage_GetPosition(Montage) : 0.0f);
		Json->SetNumberField(TEXT("montage_length"), Montage ? Montage->GetPlayLength() : 0.0f);
		Json->SetNumberField(TEXT("movement_mode"), Character->GetCharacterMovement()->MovementMode);
		Json->SetNumberField(TEXT("montage_play_rate"), Montage ? Anim->Montage_GetPlayRate(Montage) : 0.0f);
		Json->SetStringField(TEXT("montage_slots"), Montage && !Montage->SlotAnimTracks.IsEmpty() ? Montage->SlotAnimTracks[0].SlotName.ToString() : TEXT(""));
		TArray<TSharedPtr<FJsonValue>> Cooldowns;
		for (int32 Index = 0; Index < 4; ++Index)
		{
			Cooldowns.Add(MakeShared<FJsonValueNumber>(Skills->GetCooldownRemaining(static_cast<ECountessSkill>(Index))));
		}
		Json->SetArrayField(TEXT("cooldowns"), Cooldowns);
		int32 EffectCount = 0;
		for (TObjectIterator<UParticleSystemComponent> Iterator; Iterator; ++Iterator)
		{
			if (Iterator->GetWorld() == World && Iterator->ComponentHasTag(TEXT("CountessSkillFX")) && Iterator->IsActive())
			{
				++EffectCount;
			}
		}
		Json->SetNumberField(TEXT("active_effects"), EffectCount);
		FString Text;
		FJsonSerializer::Serialize(Json, TJsonWriterFactory<>::Create(&Text));
		FFileHelper::SaveStringToFile(Text, *(CharacterPipelineQA::GetOutputDirectory(TEXT("QA/CountessSkills")) / (Args[0] + TEXT(".json"))),
			FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
	}));

#endif
