#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS

#include "CharacterPipelineQA.h"
#include "Animation/AnimBlueprint.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "AnimGraphNode_Root.h"
#include "AnimGraphNode_Slot.h"
#include "AnimGraphNode_SaveCachedPose.h"
#include "AnimGraphNode_UseCachedPose.h"
#include "AnimGraphNode_LayeredBoneBlend.h"
#include "AnimGraphNode_BlendListByBool.h"
#include "AnimGraphNode_SequencePlayer.h"
#include "AnimGraphNode_SequenceEvaluator.h"
#include "Dom/JsonObject.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphPin.h"
#include "EdGraph/EdGraphSchema.h"
#include "EdGraphSchema_K2.h"
#include "Editor.h"
#include "HAL/IConsoleManager.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "K2Node_CallFunction.h"
#include "K2Node_VariableGet.h"
#include "K2Node_VariableSet.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonSerializer.h"
#include "../SparrowCharacter.h"
#include "UObject/UnrealType.h"

namespace SparrowBasicAttackQA
{
	using FObject = TSharedRef<FJsonObject>;
	using FValues = TArray<TSharedPtr<FJsonValue>>;

	static bool Linked(const UEdGraphPin* Source, const UEdGraphPin* Target)
	{
		return Source && Target && Source->LinkedTo.Num() == 1 && Source->LinkedTo.Contains(Target);
	}

	static bool Connect(UEdGraphPin* Source, UEdGraphPin* Target)
	{
		return Source && Target && (Source->LinkedTo.Contains(Target) ||
			Source->GetOwningNode()->GetSchema()->TryCreateConnection(Source, Target));
	}

	template<typename T>
	static T* CreatePoseNode(UEdGraph* Graph, const TCHAR* Name)
	{
		T* Node = NewObject<T>(Graph, FName(Name));
		Graph->AddNode(Node, false, false);
		Node->CreateNewGuid();
		Node->PostPlacedNewNode();
		return Node;
	}

	static FValues NotifyReport(const UAnimMontage* Montage)
	{
		FValues Values;
		for (const FAnimNotifyEvent& Notify : Montage->Notifies)
		{
			const FObject Item = MakeShared<FJsonObject>();
			Item->SetStringField(TEXT("name"), Notify.NotifyName.ToString());
			Item->SetNumberField(TEXT("time"), Notify.GetTime());
			Item->SetNumberField(TEXT("trigger_time"), Notify.GetTriggerTime());
			Item->SetNumberField(TEXT("duration"), Notify.GetDuration());
			Item->SetNumberField(TEXT("end_time"), Notify.EndLink.GetTime());
			Item->SetStringField(TEXT("guid"), Notify.Guid.ToString());
			Values.Add(MakeShared<FJsonValueObject>(Item));
		}
		return Values;
	}

	// 외부 저장 도구가 만든 전용 사본만 수정한다. 원본 그래프와 skeleton package는 저장하지 않는다.
	static FAutoConsoleCommand Configure(
		TEXT("SparrowAttackQA.Configure"), TEXT("Editor only: configure owned upper-body primary attack copies in memory; never saves packages"),
		FConsoleCommandDelegate::CreateLambda([]()
		{
			const FObject Report = MakeShared<FJsonObject>();
			Report->SetBoolField(TEXT("passed"), false);
			Report->SetBoolField(TEXT("saved_packages"), false);
			Report->SetBoolField(TEXT("source_skeleton_save_forbidden"), true);
			Report->SetBoolField(TEXT("runtime_validation_pending"), true);
			const auto Write = [&Report]()
			{
				FString Text;
				FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Text));
				FFileHelper::SaveStringToFile(Text, *(CharacterPipelineQA::GetOutputDirectory(TEXT("QA/SparrowInventory")) /
					TEXT("sparrow-basic-attack-configuration.json")), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
			};
			const auto Fail = [&Report, &Write](const TCHAR* Error)
			{
				Report->SetStringField(TEXT("error"), Error);
				Write();
				UE_LOG(LogTemp, Error, TEXT("SPARROW_BASIC_ATTACK_CONFIGURATION_FAILED %s"), Error);
			};
			if (!GEditor || GEditor->PlayWorld)
			{
				Fail(TEXT("Owned basic attack configuration requires the editor outside PIE"));
				return;
			}
			UAnimBlueprint* Blueprint = LoadObject<UAnimBlueprint>(nullptr,
				TEXT("/Game/TopDown/Characters/Sparrow/Animations/ABP_Sparrow_BasicNatural.ABP_Sparrow_BasicNatural"));
			UAnimMontage* Montage = LoadObject<UAnimMontage>(nullptr,
				TEXT("/Game/TopDown/Characters/Sparrow/Animations/AM_Sparrow_PrimaryNatural.AM_Sparrow_PrimaryNatural"));
			UAnimSequence* Sequence = LoadObject<UAnimSequence>(nullptr,
				TEXT("/Game/ParagonSparrow/Characters/Heroes/Sparrow/Animations/Primary_Fire_Med.Primary_Fire_Med"));
			if (!Blueprint || !Montage || !Sequence || !Blueprint->TargetSkeleton ||
				Blueprint->GetPathName() != TEXT("/Game/TopDown/Characters/Sparrow/Animations/ABP_Sparrow_BasicNatural.ABP_Sparrow_BasicNatural") ||
				Montage->GetPathName() != TEXT("/Game/TopDown/Characters/Sparrow/Animations/AM_Sparrow_PrimaryNatural.AM_Sparrow_PrimaryNatural") ||
				Blueprint->TargetSkeleton != Montage->GetSkeleton() || Blueprint->TargetSkeleton != Sequence->GetSkeleton() ||
				Blueprint->TargetSkeleton->GetPathName() !=
				TEXT("/Game/ParagonSparrow/Characters/Heroes/Sparrow/Meshes/Sparrow_Skeleton.Sparrow_Skeleton") ||
				Blueprint->TargetSkeleton->GetReferenceSkeleton().FindBoneIndex(TEXT("spine_01")) == INDEX_NONE ||
				!FMath::IsNearlyEqual(Sequence->GetPlayLength(), 1.0f) ||
				!FMath::IsNearlyEqual(Montage->GetPlayLength(), 1.0f) ||
				!FMath::IsNearlyEqual(Montage->RateScale, 1.0f) || Montage->SlotAnimTracks.Num() != 1)
			{
				Fail(TEXT("Declare the known private blueprint/montage copies first; expected one-second Sparrow primary and original skeleton"));
				return;
			}
			FSlotAnimationTrack& Track = Montage->SlotAnimTracks[0];
			if ((Track.SlotName != TEXT("SparrowFullBody") && Track.SlotName != TEXT("SparrowUpperBody")) ||
				(Track.AnimTrack.AnimSegments.Num() != 1 && Track.AnimTrack.AnimSegments.Num() != 2))
			{
				Fail(TEXT("Primary montage is neither the inspected original copy nor this configured variant"));
				return;
			}
			for (const FAnimSegment& Segment : Track.AnimTrack.AnimSegments)
			{
				if (Segment.GetAnimReference() != Sequence)
				{
					Fail(TEXT("Primary montage contains an unexpected source animation"));
					return;
				}
			}
			bool bSaveAttack = false;
			bool bResetCombo = false;
			TArray<float> NotifyTimes;
			TArray<float> NotifyEndTimes;
			TArray<float> NotifyTriggerTimes;
			for (const FAnimNotifyEvent& Notify : Montage->Notifies)
			{
				bSaveAttack |= Notify.NotifyName == TEXT("SaveAttack");
				bResetCombo |= Notify.NotifyName == TEXT("ResetCombo");
				NotifyTimes.Add(Notify.GetTime());
				NotifyEndTimes.Add(Notify.EndLink.GetTime());
				NotifyTriggerTimes.Add(Notify.GetTriggerTime());
			}
			if (!bSaveAttack || !bResetCombo)
			{
				Fail(TEXT("The inspected SaveAttack and ResetCombo notifies must remain present"));
				return;
			}
			TArray<float> SectionTimes;
			for (const FCompositeSection& Section : Montage->CompositeSections)
			{
				SectionTimes.Add(Section.GetTime());
			}
			UAnimGraphNode_Root* Root = FindObject<UAnimGraphNode_Root>(nullptr,
				*(Blueprint->GetPathName() + TEXT(":AnimGraph.AnimGraphNode_Root_0")));
			UEdGraphPin* Result = Root ? Root->FindPin(TEXT("Result")) : nullptr;
			UAnimGraphNode_Slot* FullBody = Result && Result->LinkedTo.Num() == 1 ?
				Cast<UAnimGraphNode_Slot>(Result->LinkedTo[0]->GetOwningNode()) : nullptr;
			UEdGraphPin* FullBodySource = FullBody ? FullBody->FindPin(TEXT("Source")) : nullptr;
			if (!Root || !FullBody || FullBody->GetGraph() != Root->GetGraph() ||
				FullBody->Node.SlotName != TEXT("SparrowFullBody") || !FullBodySource || FullBodySource->LinkedTo.Num() != 1 ||
				!Linked(FullBody->FindPin(TEXT("Pose")), Result))
			{
				Fail(TEXT("The inspected final SparrowFullBody slot must remain immediately before the root"));
				return;
			}
			UEdGraph* Graph = Root->GetGraph();
			UAnimGraphNode_SaveCachedPose* Cache = FindObject<UAnimGraphNode_SaveCachedPose>(Graph, TEXT("SparrowPrimaryBaseCache"));
			UAnimGraphNode_UseCachedPose* SlotBase = FindObject<UAnimGraphNode_UseCachedPose>(Graph, TEXT("SparrowPrimaryBaseForSlot"));
			UAnimGraphNode_UseCachedPose* BodyBase = FindObject<UAnimGraphNode_UseCachedPose>(Graph, TEXT("SparrowPrimaryBaseForBody"));
			UAnimGraphNode_Slot* UpperBody = FindObject<UAnimGraphNode_Slot>(Graph, TEXT("SparrowPrimaryUpperBodySlot"));
			UAnimGraphNode_LayeredBoneBlend* Layer = FindObject<UAnimGraphNode_LayeredBoneBlend>(Graph, TEXT("SparrowPrimaryUpperBodyBlend"));
			const bool bConfiguredGraph = Cache && SlotBase && BodyBase && UpperBody && Layer;
			bool bNamedNodeExists = false;
			for (const TCHAR* Name : { TEXT("SparrowPrimaryBaseCache"), TEXT("SparrowPrimaryBaseForSlot"),
				TEXT("SparrowPrimaryBaseForBody"), TEXT("SparrowPrimaryUpperBodySlot"), TEXT("SparrowPrimaryUpperBodyBlend") })
			{
				bNamedNodeExists |= FindObject<UObject>(Graph, Name) != nullptr;
			}
			UEdGraphPin* Base = FullBodySource->LinkedTo[0];
			if (bNamedNodeExists)
			{
				UEdGraphPin* CacheInput = Cache ? Cache->FindPin(TEXT("Pose")) : nullptr;
				if (!bConfiguredGraph || !CacheInput || CacheInput->LinkedTo.Num() != 1 ||
					SlotBase->SaveCachedPoseNode.Get() != Cache || BodyBase->SaveCachedPoseNode.Get() != Cache ||
					!Linked(Layer->FindPin(TEXT("Pose")), FullBodySource) ||
					!Linked(SlotBase->FindPin(TEXT("Pose")), UpperBody->FindPin(TEXT("Source"))) ||
					!Linked(BodyBase->FindPin(TEXT("Pose")), Layer->FindPin(TEXT("BasePose"))) ||
					!Linked(UpperBody->FindPin(TEXT("Pose")), Layer->FindPin(TEXT("BlendPoses_0"))))
				{
					Fail(TEXT("A partial or externally changed owned upper-body graph requires review"));
					return;
				}
				Base = CacheInput->LinkedTo[0];
			}
			if (Base->GetOwningNode()->GetGraph() != Graph || Base->Direction != EGPD_Output ||
				Base->PinName != TEXT("Pose") || Base->GetOwningNode()->GetFName() != TEXT("AnimGraphNode_ComponentToLocalSpace_1"))
			{
				Fail(TEXT("Unexpected locomotion source for the inspected full-body slot"));
				return;
			}

			Report->SetArrayField(TEXT("notifies_before"), NotifyReport(Montage));
			Blueprint->Modify();
			Graph->Modify();
			FullBody->Modify();
			if (!bConfiguredGraph)
			{
				Cache = CreatePoseNode<UAnimGraphNode_SaveCachedPose>(Graph, TEXT("SparrowPrimaryBaseCache"));
				SlotBase = CreatePoseNode<UAnimGraphNode_UseCachedPose>(Graph, TEXT("SparrowPrimaryBaseForSlot"));
				BodyBase = CreatePoseNode<UAnimGraphNode_UseCachedPose>(Graph, TEXT("SparrowPrimaryBaseForBody"));
				UpperBody = CreatePoseNode<UAnimGraphNode_Slot>(Graph, TEXT("SparrowPrimaryUpperBodySlot"));
				Layer = CreatePoseNode<UAnimGraphNode_LayeredBoneBlend>(Graph, TEXT("SparrowPrimaryUpperBodyBlend"));
			}
			Cache->Modify();
			SlotBase->Modify();
			BodyBase->Modify();
			UpperBody->Modify();
			Layer->Modify();
			Cache->CacheName = TEXT("SparrowPrimaryLocomotion");
			SlotBase->SaveCachedPoseNode = Cache;
			BodyBase->SaveCachedPoseNode = Cache;
			// UseCachedPose의 fallback 이름도 채워 저장 후 재로드 시 동일 cache를 다시 찾을 수 있게 한다.
			SlotBase->GetNodeTitle(ENodeTitleType::FullTitle);
			BodyBase->GetNodeTitle(ENodeTitleType::FullTitle);
			UpperBody->Node.SlotName = TEXT("SparrowUpperBody");
			Layer->Node.BlendMode = ELayeredBoneBlendMode::BranchFilter;
			Layer->Node.BlendPoses.SetNum(1);
			Layer->Node.BlendWeights.SetNum(1);
			Layer->Node.BlendWeights[0] = 1.0f;
			Layer->Node.LayerSetup.SetNum(1);
			Layer->Node.LayerSetup[0].BranchFilters.SetNum(1);
			Layer->Node.LayerSetup[0].BranchFilters[0].BoneName = TEXT("spine_01");
			Layer->Node.LayerSetup[0].BranchFilters[0].BlendDepth = 1;
			Layer->Node.bMeshSpaceRotationBlend = true;
			Layer->Node.InvalidatePerBoneBlendWeights();
			if (!bConfiguredGraph)
			{
				for (UEdGraphNode* Node : { static_cast<UEdGraphNode*>(Cache), static_cast<UEdGraphNode*>(SlotBase),
					static_cast<UEdGraphNode*>(BodyBase), static_cast<UEdGraphNode*>(UpperBody), static_cast<UEdGraphNode*>(Layer) })
				{
					Node->AllocateDefaultPins();
				}
				Cache->NodePosX = FullBody->NodePosX - 1100;
				Cache->NodePosY = FullBody->NodePosY - 300;
				SlotBase->NodePosX = BodyBase->NodePosX = FullBody->NodePosX - 900;
				SlotBase->NodePosY = FullBody->NodePosY + 260;
				BodyBase->NodePosY = FullBody->NodePosY;
				UpperBody->NodePosX = FullBody->NodePosX - 650;
				UpperBody->NodePosY = SlotBase->NodePosY;
				Layer->NodePosX = FullBody->NodePosX - 350;
				Layer->NodePosY = FullBody->NodePosY;
				FullBodySource->BreakAllPinLinks();
			}
			const bool bGraphLinked = Connect(Base, Cache->FindPin(TEXT("Pose"))) &&
				Connect(SlotBase->FindPin(TEXT("Pose")), UpperBody->FindPin(TEXT("Source"))) &&
				Connect(BodyBase->FindPin(TEXT("Pose")), Layer->FindPin(TEXT("BasePose"))) &&
				Connect(UpperBody->FindPin(TEXT("Pose")), Layer->FindPin(TEXT("BlendPoses_0"))) &&
				Connect(Layer->FindPin(TEXT("Pose")), FullBodySource);
			if (!bGraphLinked)
			{
				Fail(TEXT("Could not connect the owned upper-body pose graph; do not save this in-memory result"));
				return;
			}

			Montage->Modify();
			FAnimSegment Draw;
			Draw.SetAnimReference(Sequence);
			Draw.StartPos = 0.0f;
			Draw.AnimStartTime = 0.65f;
			Draw.AnimEndTime = 1.0f;
			Draw.AnimPlayRate = 1.75f;
			FAnimSegment Fire;
			Fire.SetAnimReference(Sequence);
			Fire.StartPos = 0.2f;
			Fire.AnimStartTime = 0.0f;
			Fire.AnimEndTime = 0.8f;
			Fire.AnimPlayRate = 1.0f;
			Track.SlotName = TEXT("SparrowUpperBody");
			Track.AnimTrack.AnimSegments = { Draw, Fire };
			Montage->BlendIn.SetBlendTime(0.12f);
			Montage->BlendOut.SetBlendTime(0.18f);
			// 구간 편집으로 notify 상대 좌표가 바뀌지 않도록 기존 montage 절대 시각에 다시 연결한다.
			for (int32 Index = 0; Index < Montage->Notifies.Num(); ++Index)
			{
				Montage->Notifies[Index].Link(Montage, NotifyTimes[Index], 0);
				Montage->Notifies[Index].EndLink.Link(Montage, NotifyEndTimes[Index], 0);
			}
			for (int32 Index = 0; Index < Montage->CompositeSections.Num(); ++Index)
			{
				Montage->CompositeSections[Index].Link(Montage, SectionTimes[Index], 0);
			}
			Montage->RefreshCacheData();
			Montage->MarkPackageDirty();
			FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
			bool bNotifyTimesPreserved = true;
			for (int32 Index = 0; Index < Montage->Notifies.Num(); ++Index)
			{
				bNotifyTimesPreserved &= FMath::IsNearlyEqual(Montage->Notifies[Index].GetTime(), NotifyTimes[Index]) &&
					FMath::IsNearlyEqual(Montage->Notifies[Index].GetTriggerTime(), NotifyTriggerTimes[Index]) &&
					FMath::IsNearlyEqual(Montage->Notifies[Index].EndLink.GetTime(), NotifyEndTimes[Index]);
			}
			const bool bLengthPreserved = FMath::IsNearlyEqual(Montage->CalculateSequenceLength(), 1.0f) &&
				FMath::IsNearlyEqual(Montage->GetPlayLength(), 1.0f);
			Report->SetStringField(TEXT("animation_blueprint"), Blueprint->GetPathName());
			Report->SetStringField(TEXT("primary_montage"), Montage->GetPathName());
			Report->SetStringField(TEXT("original_sequence"), Sequence->GetPathName());
			Report->SetStringField(TEXT("cached_locomotion_source"), Base->GetOwningNode()->GetPathName());
			Report->SetStringField(TEXT("full_body_slot"), FullBody->Node.SlotName.ToString());
			Report->SetStringField(TEXT("primary_slot"), UpperBody->Node.SlotName.ToString());
			Report->SetStringField(TEXT("branch_filter"), TEXT("spine_01"));
			Report->SetNumberField(TEXT("blend_depth"), 1);
			Report->SetBoolField(TEXT("mesh_space_rotation_blend"), Layer->Node.bMeshSpaceRotationBlend);
			Report->SetBoolField(TEXT("full_body_remains_after_upper_body"), Linked(FullBody->FindPin(TEXT("Pose")), Result));
			Report->SetBoolField(TEXT("existing_locomotion_graph_preserved"), true);
			Report->SetBoolField(TEXT("graph_was_already_configured"), bConfiguredGraph);
			Report->SetBoolField(TEXT("notify_times_preserved"), bNotifyTimesPreserved);
			Report->SetBoolField(TEXT("one_second_duration_preserved"), bLengthPreserved);
			Report->SetNumberField(TEXT("blend_in"), Montage->BlendIn.GetBlendTime());
			Report->SetNumberField(TEXT("blend_out"), Montage->BlendOut.GetBlendTime());
			Report->SetNumberField(TEXT("expected_runtime_primary_hit_time"), 0.25);
			Report->SetBoolField(TEXT("runtime_hit_time_configured_by_this_helper"), false);
			FValues Segments;
			for (const FAnimSegment& Segment : Track.AnimTrack.AnimSegments)
			{
				const FObject Item = MakeShared<FJsonObject>();
				Item->SetNumberField(TEXT("montage_start"), Segment.StartPos);
				Item->SetNumberField(TEXT("source_start"), Segment.AnimStartTime);
				Item->SetNumberField(TEXT("source_end"), Segment.AnimEndTime);
				Item->SetNumberField(TEXT("source_play_rate"), Segment.AnimPlayRate);
				Item->SetNumberField(TEXT("duration"), Segment.GetLength());
				Item->SetStringField(TEXT("sequence"), GetPathNameSafe(Segment.GetAnimReference()));
				Segments.Add(MakeShared<FJsonValueObject>(Item));
			}
			Report->SetArrayField(TEXT("segments"), Segments);
			Report->SetArrayField(TEXT("notifies_after"), NotifyReport(Montage));
			Report->SetBoolField(TEXT("passed"), bGraphLinked && bNotifyTimesPreserved && bLengthPreserved);
			Write();
			UE_LOG(LogTemp, Display, TEXT("SPARROW_BASIC_ATTACK_CONFIGURATION passed=%d; compile and save only declared private copies"),
				bGraphLinked && bNotifyTimesPreserved && bLengthPreserved);
		}));

	template<typename T>
	static T* HeldNode(UEdGraph* Graph, const TCHAR* Name)
	{
		if (T* Existing = FindObject<T>(Graph, Name)) { return Existing; }
		return CreatePoseNode<T>(Graph, Name);
	}

	// 기존 Configure는 그대로 두고 새 private 사본의 상체 base만 확장한다.
	static FAutoConsoleCommand ConfigureHeld(
		TEXT("SparrowAttackQA.ConfigureHeld"), TEXT("Editor only: configure the owned HeldAim AnimBP copy; never saves packages"),
		FConsoleCommandDelegate::CreateLambda([]()
		{
			const FObject Report = MakeShared<FJsonObject>();
			Report->SetBoolField(TEXT("passed"), false);
			Report->SetBoolField(TEXT("saved_packages"), false);
			const auto Write = [&Report]()
			{
				FString Text;
				FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Text));
				FFileHelper::SaveStringToFile(Text, *(CharacterPipelineQA::GetOutputDirectory(TEXT("QA/SparrowInventory")) /
					TEXT("sparrow-held-aim-configuration.json")), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
			};
			const auto Fail = [&Report, &Write](const TCHAR* Error)
			{
				Report->SetStringField(TEXT("error"), Error);
				Write();
				UE_LOG(LogTemp, Error, TEXT("SPARROW_HELD_AIM_CONFIGURATION_FAILED %s"), Error);
			};
			if (!GEditor || GEditor->PlayWorld) { Fail(TEXT("Configure HeldAim outside PIE")); return; }
			UAnimBlueprint* Blueprint = LoadObject<UAnimBlueprint>(nullptr,
				TEXT("/Game/TopDown/Characters/Sparrow/Animations/ABP_Sparrow_HeldAim.ABP_Sparrow_HeldAim"));
			UAnimSequence* Ready = LoadObject<UAnimSequence>(nullptr,
				TEXT("/Game/ParagonSparrow/Characters/Heroes/Sparrow/Animations/idle.idle"));
			UAnimSequence* Lean = LoadObject<UAnimSequence>(nullptr,
				TEXT("/Game/ParagonSparrow/Characters/Heroes/Sparrow/Animations/R_Ability_Fast_Fire.R_Ability_Fast_Fire"));
			if (!Blueprint || !Ready || !Lean || Blueprint->TargetSkeleton != Ready->GetSkeleton() ||
				Blueprint->TargetSkeleton != Lean->GetSkeleton())
			{ Fail(TEXT("Owned HeldAim copy or inspected source skeleton is missing")); return; }
			UEdGraph* Graph = FindObject<UEdGraph>(Blueprint, TEXT("AnimGraph"));
			UAnimGraphNode_Slot* Upper = Graph ? FindObject<UAnimGraphNode_Slot>(Graph, TEXT("SparrowPrimaryUpperBodySlot")) : nullptr;
			UAnimGraphNode_UseCachedPose* Base = Graph ? FindObject<UAnimGraphNode_UseCachedPose>(Graph, TEXT("SparrowPrimaryBaseForSlot")) : nullptr;
			UK2Node_VariableSet* SetCombat = FindObject<UK2Node_VariableSet>(nullptr,
				*(Blueprint->GetPathName() + TEXT(":EventGraph.SparrowPoseSetCombat")));
			UK2Node_CallFunction* Owner = FindObject<UK2Node_CallFunction>(nullptr,
				*(Blueprint->GetPathName() + TEXT(":EventGraph.SparrowPoseOwner")));
			if (!Upper || !Base || !SetCombat || !Owner || Upper->Node.SlotName != TEXT("SparrowUpperBody"))
			{ Fail(TEXT("Expected approved Natural upper-body graph and pose event chain")); return; }
			Blueprint->Modify();
			Graph->Modify();
			bool bPassed = true;
			FEdGraphPinType BoolType;
			BoolType.PinCategory = UEdGraphSchema_K2::PC_Boolean;
			for (const TCHAR* Name : {TEXT("HoldBowReady"), TEXT("HoldInnerFireReady")})
			{
				if (FBlueprintEditorUtils::FindNewVariableIndex(Blueprint, Name) == INDEX_NONE)
				{ bPassed &= FBlueprintEditorUtils::AddMemberVariable(Blueprint, Name, BoolType, TEXT("false")); }
			}
			UEdGraph* Events = SetCombat->GetGraph();
			UK2Node_VariableSet* Setters[2];
			const TCHAR* Variables[] = {TEXT("HoldBowReady"), TEXT("HoldInnerFireReady")};
			const TCHAR* Functions[] = {TEXT("ShouldHoldBowReady"), TEXT("ShouldHoldInnerFireReady")};
			for (int32 Index = 0; Index < 2; ++Index)
			{
				UK2Node_CallFunction* Predicate = HeldNode<UK2Node_CallFunction>(Events, *FString::Printf(TEXT("HeldAimPredicate%d"), Index));
				Predicate->SetFromFunction(ASparrowCharacter::StaticClass()->FindFunctionByName(Functions[Index]));
				if (Predicate->Pins.IsEmpty()) { Predicate->AllocateDefaultPins(); }
				Setters[Index] = HeldNode<UK2Node_VariableSet>(Events, *FString::Printf(TEXT("HeldAimSet%d"), Index));
				Setters[Index]->VariableReference.SetSelfMember(Variables[Index]);
				if (Setters[Index]->Pins.IsEmpty()) { Setters[Index]->AllocateDefaultPins(); }
				bPassed &= Connect(Owner->FindPin(TEXT("ReturnValue")), Predicate->FindPin(TEXT("CharacterOwner"))) &&
					Connect(Predicate->FindPin(TEXT("ReturnValue")), Setters[Index]->FindPin(Variables[Index]));
			}
			UEdGraphPin* Then = SetCombat->FindPin(TEXT("then"));
			if (!Then) { Fail(TEXT("Expected existing pose update execution")); return; }
			const TArray<UEdGraphPin*> Consumers = Then->LinkedTo;
			for (UEdGraphPin* Consumer : Consumers)
			{
				if (Consumer != Setters[0]->FindPin(TEXT("execute")))
				{
					Then->BreakLinkTo(Consumer);
					bPassed &= Connect(Setters[1]->FindPin(TEXT("then")), Consumer);
				}
			}
			bPassed &= Connect(Then, Setters[0]->FindPin(TEXT("execute"))) &&
				Connect(Setters[0]->FindPin(TEXT("then")), Setters[1]->FindPin(TEXT("execute")));
			UAnimGraphNode_SequencePlayer* Idle = HeldNode<UAnimGraphNode_SequencePlayer>(Graph, TEXT("HeldAimReady"));
			Idle->Node.SetSequence(Ready);
			Idle->Node.SetLoopAnimation(true);
			if (Idle->Pins.IsEmpty()) { Idle->AllocateDefaultPins(); }
			UAnimGraphNode_SequenceEvaluator* Tilt = HeldNode<UAnimGraphNode_SequenceEvaluator>(Graph, TEXT("HeldAimLean"));
			Tilt->Node.SetSequence(Lean);
			Tilt->Node.SetExplicitTime(0.0f);
			Tilt->Node.SetShouldLoop(false);
			if (Tilt->Pins.IsEmpty()) { Tilt->AllocateDefaultPins(); }
			UAnimGraphNode_BlendListByBool* Selectors[2];
			for (int32 Index = 0; Index < 2; ++Index)
			{
				Selectors[Index] = HeldNode<UAnimGraphNode_BlendListByBool>(Graph, *FString::Printf(TEXT("HeldAimSelect%d"), Index));
				const FStructProperty* Node = FindFProperty<FStructProperty>(Selectors[Index]->GetClass(), TEXT("Node"));
				FArrayProperty* Times = Node ? FindFProperty<FArrayProperty>(Node->Struct, TEXT("BlendTime")) : nullptr;
				if (!Times) { Fail(TEXT("Expected bool pose blend-time property")); return; }
				FScriptArrayHelper Values(Times, Times->ContainerPtrToValuePtr<void>(&Selectors[Index]->Node));
				if (Values.Num() != 2) { Fail(TEXT("Expected two pose alternatives")); return; }
				for (int32 Child = 0; Child < 2; ++Child) { *reinterpret_cast<float*>(Values.GetRawPtr(Child)) = 0.12f; }
				if (Selectors[Index]->Pins.IsEmpty()) { Selectors[Index]->AllocateDefaultPins(); }
				UK2Node_VariableGet* Value = HeldNode<UK2Node_VariableGet>(Graph, *FString::Printf(TEXT("HeldAimValue%d"), Index));
				Value->VariableReference.SetSelfMember(Variables[Index]);
				if (Value->Pins.IsEmpty()) { Value->AllocateDefaultPins(); }
				bPassed &= Connect(Value->FindPin(Variables[Index]), Selectors[Index]->FindPin(TEXT("bActiveValue")));
			}
			Upper->FindPin(TEXT("Source"))->BreakAllPinLinks();
			bPassed &= Connect(Tilt->FindPin(TEXT("Pose")), Selectors[1]->FindPin(TEXT("BlendPose_0"))) &&
				Connect(Idle->FindPin(TEXT("Pose")), Selectors[1]->FindPin(TEXT("BlendPose_1"))) &&
				Connect(Selectors[1]->FindPin(TEXT("Pose")), Selectors[0]->FindPin(TEXT("BlendPose_0"))) &&
				Connect(Base->FindPin(TEXT("Pose")), Selectors[0]->FindPin(TEXT("BlendPose_1"))) &&
				Connect(Selectors[0]->FindPin(TEXT("Pose")), Upper->FindPin(TEXT("Source")));
			FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
			Blueprint->MarkPackageDirty();
			Report->SetStringField(TEXT("asset"), Blueprint->GetPathName());
			Report->SetStringField(TEXT("scope"), TEXT("Held upper-body base only; original lower-body and final full-body graph preserved"));
			Report->SetBoolField(TEXT("passed"), bPassed);
			Write();
		}));
}

#endif
