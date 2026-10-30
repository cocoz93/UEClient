#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS

#include "../CountessDamageAnimInstance.h"
#include "Animation/AnimBlueprint.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "AnimGraphNode_ApplyAdditive.h"
#include "AnimGraphNode_LayeredBoneBlend.h"
#include "AnimGraphNode_Root.h"
#include "AnimGraphNode_SaveCachedPose.h"
#include "AnimGraphNode_SequenceEvaluator.h"
#include "AnimGraphNode_UseCachedPose.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphSchema.h"
#include "Editor.h"
#include "HAL/IConsoleManager.h"
#include "K2Node_VariableGet.h"
#include "Kismet2/BlueprintEditorUtils.h"

namespace CountessDamageAnimationQA
{
	template<typename T>
	T* Node(UEdGraph* Graph, const TCHAR* Name, int32 X, int32 Y)
	{
		T* Result = NewObject<T>(Graph, MakeUniqueObjectName(Graph, T::StaticClass(), FName(Name)));
		Graph->AddNode(Result, false, false);
		Result->CreateNewGuid();
		Result->PostPlacedNewNode();
		Result->NodePosX = X; Result->NodePosY = Y;
		return Result;
	}

	bool Link(UEdGraphNode* From, const TCHAR* Output, UEdGraphNode* To, const TCHAR* Input)
	{
		UEdGraphPin* A = From->FindPin(Output, EGPD_Output);
		UEdGraphPin* B = To->FindPin(Input, EGPD_Input);
		return A && B && A->GetOwningNode()->GetSchema()->TryCreateConnection(A, B);
	}

	// Only the project-owned Countess graph changes. The original skeleton,
	// clips, locomotion, combo slots and full-body skill slot stay intact.
	static FAutoConsoleCommand Install(TEXT("CountessDamageQA.InstallHitLayer"),
		TEXT("Editor only: install independent upper-body Countess damage recoil; compile/save remains with caller"),
		FConsoleCommandDelegate::CreateLambda([]()
		{
			if (!GEditor || GEditor->PlayWorld) { return; }
			UAnimBlueprint* BP = LoadObject<UAnimBlueprint>(nullptr,
				TEXT("/Game/TopDown/Characters/Countess/Animations/ABP_Countess_TopDown.ABP_Countess_TopDown"));
			UAnimSequence* Hit = LoadObject<UAnimSequence>(nullptr,
				TEXT("/Game/ParagonCountess/Characters/Heroes/Countess/Animations/Hitreact_Fwd.Hitreact_Fwd"));
			if (!BP || !Hit || BP->TargetSkeleton != Hit->GetSkeleton() ||
				BP->TargetSkeleton->GetReferenceSkeleton().FindBoneIndex(TEXT("spine_01")) == INDEX_NONE ||
				(BP->ParentClass != UAnimInstance::StaticClass() && BP->ParentClass != UCountessDamageAnimInstance::StaticClass()))
			{
				UE_LOG(LogTemp, Error, TEXT("Countess damage layer requires the expected parent and skeleton; no edits made"));
				return;
			}
			TArray<UEdGraph*> Graphs;
			BP->GetAllGraphs(Graphs);
			UEdGraph* Graph = nullptr;
			for (UEdGraph* Candidate : Graphs) { if (Candidate->GetFName() == TEXT("AnimGraph")) { Graph = Candidate; break; } }
			if (!Graph) { return; }
			UAnimGraphNode_Root* Root = nullptr;
			for (UEdGraphNode* Item : Graph->Nodes)
			{
				if (Item->NodeComment == TEXT("Countess damage layer bindings verified")) { return; }
				if (UAnimGraphNode_Root* Value = Cast<UAnimGraphNode_Root>(Item)) { Root = Value; }
			}
			UEdGraphPin* Result = Root ? Root->FindPin(TEXT("Result")) : nullptr;
			if (!Result || Result->LinkedTo.Num() != 1) { return; }
			UEdGraphPin* Source = Result->LinkedTo[0];
			BP->Modify(); Graph->Modify(); Root->Modify();
			BP->ParentClass = UCountessDamageAnimInstance::StaticClass();
			FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP);
			auto* Cache = Node<UAnimGraphNode_SaveCachedPose>(Graph, TEXT("CountessDamageCache"), 0, -200);
			Cache->CacheName = TEXT("CountessDamageBase");
			auto* Base = Node<UAnimGraphNode_UseCachedPose>(Graph, TEXT("CountessDamageBase"), 250, -200);
			auto* AddBase = Node<UAnimGraphNode_UseCachedPose>(Graph, TEXT("CountessDamageAddBase"), 0, 200);
			Base->SaveCachedPoseNode = Cache; AddBase->SaveCachedPoseNode = Cache;
			Base->GetNodeTitle(ENodeTitleType::FullTitle); AddBase->GetNodeTitle(ENodeTitleType::FullTitle);
			auto* Eval = Node<UAnimGraphNode_SequenceEvaluator>(Graph, TEXT("CountessDamageSequence"), -100, 450);
			Eval->Node.SetSequence(Hit); Eval->Node.SetShouldLoop(false); Eval->Node.SetTeleportToExplicitTime(true);
			auto* Add = Node<UAnimGraphNode_ApplyAdditive>(Graph, TEXT("CountessDamageAdditive"), 350, 200);
			Add->Node.Alpha = 1.0f;
			auto* Layer = Node<UAnimGraphNode_LayeredBoneBlend>(Graph, TEXT("CountessDamageUpperBody"), 650, 0);
			Layer->Node.BlendMode = ELayeredBoneBlendMode::BranchFilter;
			Layer->Node.BlendPoses.SetNum(1); Layer->Node.BlendWeights.SetNum(1);
			Layer->Node.BlendWeights[0] = 1.0f;
			Layer->Node.LayerSetup.SetNum(1);
			FBranchFilter& Filter = Layer->Node.LayerSetup[0].BranchFilters.AddDefaulted_GetRef();
			Filter.BoneName = TEXT("spine_01"); Filter.BlendDepth = 1;
			Layer->Node.bMeshSpaceRotationBlend = true;
			Layer->Node.InvalidatePerBoneBlendWeights();
			for (UEdGraphNode* Item : TArray<UEdGraphNode*>{Cache, Base, AddBase, Eval, Add, Layer}) { Item->AllocateDefaultPins(); }
			for (int32 Index = 0; Index < Eval->ShowPinForProperties.Num(); ++Index)
			{
				const FName Property = Eval->ShowPinForProperties[Index].PropertyName;
				if (Property == TEXT("Sequence") || Property == TEXT("ExplicitTime")) { Eval->SetPinVisibility(true, Index); }
			}
			const auto Bind = [Graph](const TCHAR* Variable, UEdGraphNode* Target, const TCHAR* Pin, int32 Y)
			{
				auto* Value = Node<UK2Node_VariableGet>(Graph, *FString::Printf(TEXT("CountessGet%s"), Variable), -500, Y);
				Value->VariableReference.SetSelfMember(Variable); Value->AllocateDefaultPins();
				return Link(Value, Variable, Target, Pin);
			};
			Result->BreakAllPinLinks();
			Root->NodePosX = 950;
			const bool bLinked = Source->GetOwningNode()->GetSchema()->TryCreateConnection(Source, Cache->FindPin(TEXT("Pose"))) &&
				Link(Base, TEXT("Pose"), Layer, TEXT("BasePose")) &&
				Link(AddBase, TEXT("Pose"), Add, TEXT("Base")) &&
				Link(Eval, TEXT("Pose"), Add, TEXT("Additive")) &&
				Link(Add, TEXT("Pose"), Layer, TEXT("BlendPoses_0")) &&
				Link(Layer, TEXT("Pose"), Root, TEXT("Result")) &&
				Bind(TEXT("DamageReactionSequence"), Eval, TEXT("Sequence"), 450) &&
				Bind(TEXT("DamageReactionTime"), Eval, TEXT("ExplicitTime"), 550) &&
				Bind(TEXT("DamageReactionWeight"), Layer, TEXT("BlendWeights_0"), 650);
			if (!bLinked) { UE_LOG(LogTemp, Error, TEXT("Countess damage layer binding failed; do not save")); return; }
			Layer->NodeComment = TEXT("Countess damage layer bindings verified");
			FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP);
			BP->MarkPackageDirty();
			UE_LOG(LogTemp, Display, TEXT("Countess damage layer configured"));
		}));
}
#endif
