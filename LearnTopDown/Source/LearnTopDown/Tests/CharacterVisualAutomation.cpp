#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Components/SkeletalMeshComponent.h"
#include "CharacterPipelineQA.h"
#include "Engine/GameViewportClient.h"
#include "UnrealClient.h"
#include "Slate/SceneViewport.h"
#include "ImageUtils.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "ClothingSimulationInteractor.h"
#include "ClothingSimulationInstance.h"
#include "ChaosCloth/ChaosClothingSimulationInteractor.h"
#include "GameFramework/Character.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "../CountessSkillComponent.h"
#include "../SparrowSkillComponent.h"
#include "../SparrowArrow.h"
#include "../TopDownCombatCharacter.h"
#include "EngineUtils.h"
#include "Engine/SkeletalMesh.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Particles/ParticleSystemComponent.h"
#include "TimerManager.h"
#include "UObject/StrongObjectPtr.h"

// 선택 전의 E FX 비교 전용. 실제 속사의 판정/속도/에셋 설정은 바꾸지 않는다.
static FAutoConsoleCommandWithWorldAndArgs PreviewArcherRapidEffects(
    TEXT("CharacterVisualQA.ArcherEPreview"), TEXT("PIE only: variant 1..3 and target actor name"),
    FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
    {
        ACharacter* Character = World && World->WorldType == EWorldType::PIE ? UGameplayStatics::GetPlayerCharacter(World, 0) : nullptr;
        USparrowSkillComponent* Skills = Character ? Character->FindComponentByClass<USparrowSkillComponent>() : nullptr;
        if (!Skills || Args.Num() != 2) { return; }
        const int32 Variant = FCString::Atoi(*Args[0]);
        AActor* Target = nullptr;
        for (TActorIterator<AActor> It(World); It; ++It)
        {
            if (It->GetName() == Args[1]) { Target = *It; break; }
        }
        if (Variant < 1 || Variant > 3 || !Target || !Skills->TryUseSkill(ESparrowSkill::Relentless, Target->GetActorLocation(), Target)) { return; }
        const double Started = World->GetTimeSeconds();
        FTimerHandle PreviewTimer;
        World->GetTimerManager().SetTimer(PreviewTimer, FTimerDelegate::CreateWeakLambda(Character, [Character, Skills, World, Variant, Started]()
        {
            if (!Skills->IsCasting() || Skills->GetActiveSkillNumber() != 3 || World->GetTimeSeconds() - Started > 1.3) { return; }
            for (TActorIterator<ASparrowArrow> It(World); It; ++It)
            {
                ASparrowArrow* Arrow = *It;
                if (Arrow->GetOwner() != Character || Arrow->ActorHasTag(TEXT("RapidFXPreview"))) { continue; }
                Arrow->Tags.Add(TEXT("RapidFXPreview"));
                UParticleSystem* Trail = LoadObject<UParticleSystem>(nullptr, Variant == 2 ?
                    TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/DrawABead/FX/P_Sparrow_RMB.P_Sparrow_RMB") :
                    TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Ultimate/FX/P_Sparrow_UltArrow.P_Sparrow_UltArrow"));
                TInlineComponentArray<UParticleSystemComponent*> Particles(Arrow);
                for (UParticleSystemComponent* Particle : Particles)
                {
                    Particle->SetTemplate(Trail);
                    Particle->SetWorldScale3D(FVector(Variant == 2 ? 0.6f : 0.9f));
                    Particle->ActivateSystem(true);
                }
                UParticleSystem* Flash = LoadObject<UParticleSystem>(nullptr, Variant == 3 ?
                    TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Ultimate/FX/P_Sparrow_Burst.P_Sparrow_Burst") :
                    TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/DrawABead/FX/P_ReleaseArrow.P_ReleaseArrow"));
                if (Variant != 1)
                {
                    UParticleSystemComponent* Particle = UGameplayStatics::SpawnEmitterAtLocation(World, Flash,
                        Skills->GetArrowOrigin(), Arrow->GetActorRotation(), FVector(Variant == 2 ? 0.5f : 0.4f), true);
                    if (Particle)
                    {
                        Particle->ComponentTags.Add(TEXT("SparrowSkillFX"));
                        FTimerHandle Cleanup;
                        World->GetTimerManager().SetTimer(Cleanup, FTimerDelegate::CreateWeakLambda(Particle, [Particle]() { Particle->DestroyComponent(); }), 0.25f, false);
                    }
                }
            }
        }), 0.02f, true);
        FTimerHandle Cleanup;
        World->GetTimerManager().SetTimer(Cleanup, FTimerDelegate::CreateWeakLambda(World,
            [World, PreviewTimer]() mutable { World->GetTimerManager().ClearTimer(PreviewTimer); }), 1.4f, false);
    }));

// PIE의 살아 있는 인터랙터에만 비교 설정을 적용하며 원본 천 에셋은 저장하지 않는다.
static FAutoConsoleCommandWithWorldAndArgs TuneClothForVisualQA(
    TEXT("CharacterVisualQA.ClothTune"), TEXT("PIE only: 1=inertia, 2=anim drive"),
    FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
    {
        ACharacter* Character = World && World->WorldType == EWorldType::PIE ? UGameplayStatics::GetPlayerCharacter(World, 0) : nullptr;
        if (!Character || Args.Num() != 1) { return; }
        USkeletalMeshComponent* Mesh = Character->GetMesh();
        Mesh->SetTeleportRotationThreshold(45.0f);
        int32 Updated = 0;
        for (const FClothingSimulationInstance& Instance : Mesh->GetClothingSimulationInstances())
        {
            UClothingSimulationInteractor* Simulation = Instance.GetClothingSimulationInteractor();
            if (!Simulation) { continue; }
            for (const auto& Pair : Simulation->ClothingInteractors)
            {
                UChaosClothingInteractor* Cloth = Cast<UChaosClothingInteractor>(Pair.Value);
                UE_LOG(LogTemp, Display, TEXT("VisualQA cloth %s: %s"), *Pair.Key.ToString(), *GetNameSafe(Pair.Value));
                if (!Cloth) { continue; }
                Cloth->SetVelocityScale(FVector(0.25f), 0.1f, 0.0f);
                Cloth->SetDamping(0.15f, 0.25f);
                if (Args[0] == TEXT("2"))
                {
                    Cloth->SetVelocityScale(FVector::ZeroVector, 0.0f, 0.0f);
                    Cloth->SetAnimDrive(FVector2D(0.35f), FVector2D(0.6f));
                }
                ++Updated;
            }
        }
        UE_LOG(LogTemp, Display, TEXT("VisualQA cloth updated: %d"), Updated);
    }));
namespace
{
    struct FVisualQACameraState
    {
        float Distance;
        FRotator Rotation;
        bool bLag;
        float FOV;
    };
    TMap<TWeakObjectPtr<ACharacter>, FVisualQACameraState> SavedVisualQACameras;
}

// 에디터 속성 편집은 SCS 컴포넌트를 재생성할 수 있으므로 PIE 런타임 API만 사용한다.
static FAutoConsoleCommandWithWorldAndArgs SetVisualQACamera(
    TEXT("CharacterVisualQA.Camera"), TEXT("PIE only: Close, Rear, Preview or Restore"),
    FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
    {
        ACharacter* Character = World && World->WorldType == EWorldType::PIE ? UGameplayStatics::GetPlayerCharacter(World, 0) : nullptr;
        if (!Character || Args.Num() != 1) { return; }
        USpringArmComponent* Arm = Character->FindComponentByClass<USpringArmComponent>();
        UCameraComponent* Camera = Character->FindComponentByClass<UCameraComponent>();
        if (!Arm || !Camera) { return; }
        if ((Args[0] == TEXT("Close") || Args[0] == TEXT("Rear") || Args[0] == TEXT("Preview")) && !SavedVisualQACameras.Contains(Character))
        {
            SavedVisualQACameras.Add(Character, {Arm->TargetArmLength, Arm->GetRelativeRotation(), Arm->bEnableCameraLag != 0, Camera->FieldOfView});
            const bool bPreview = Args[0] == TEXT("Preview");
            Arm->TargetArmLength = bPreview ? 1000.0f : 600.0f;
            Arm->SetRelativeRotation(bPreview ? FRotator(-35, 45, 0) : FRotator(-15, Args[0] == TEXT("Rear") ? Character->GetActorRotation().Yaw : 35.0f, 0));
            Arm->bEnableCameraLag = false;
            Camera->SetFieldOfView(bPreview ? 50.0f : 45.0f);
        }
        else if (Args[0] == TEXT("Restore"))
        {
            if (const FVisualQACameraState* State = SavedVisualQACameras.Find(Character))
            {
                Arm->TargetArmLength = State->Distance;
                Arm->SetRelativeRotation(State->Rotation);
                Arm->bEnableCameraLag = State->bLag;
                Camera->SetFieldOfView(State->FOV);
                SavedVisualQACameras.Remove(Character);
            }
        }
    }));

// 실제 스킬 정의나 피해를 바꾸지 않고 현재 PIE 메시에서 정방향 후보 모션과 원본 FX만 비교한다.
static FAutoConsoleCommandWithWorldAndArgs PreviewCountessE(
    TEXT("CharacterVisualQA.CountessEPreview"), TEXT("PIE only: 1|2|3|4 targetActorName; visual only, no damage"),
    FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
    {
        ATopDownCombatCharacter* Character = World && World->WorldType == EWorldType::PIE ? Cast<ATopDownCombatCharacter>(UGameplayStatics::GetPlayerCharacter(World, 0)) : nullptr;
        if (!Character || Args.Num() != 2 || (Args[0] != TEXT("1") && Args[0] != TEXT("2") && Args[0] != TEXT("3") && Args[0] != TEXT("4"))) { return; }
        AActor* Target = nullptr;
        for (TActorIterator<AActor> It(World); It; ++It)
        {
            if (It->GetName() == Args[1]) { Target = *It; break; }
        }
        USkeletalMeshComponent* Mesh = Character->GetMesh();
        UAnimInstance* Anim = Mesh ? Mesh->GetAnimInstance() : nullptr;
        if (!IsValid(Target) || !Anim || !Mesh->GetSkeletalMeshAsset()) { return; }
        const int32 Candidate = FCString::Atoi(*Args[0]);
        const TCHAR* Folder = TEXT("/Game/ParagonCountess/Characters/Heroes/Countess/Animations/");
        TArray<FString> Names;
        if (Candidate == 1 || Candidate == 4) { Names = {TEXT("Primary_Attack_Fast_V1"), TEXT("Primary_Attack_A_Fast_V1"), TEXT("Primary_Attack_B_Fast_InMotion")}; }
        else { Names.Add(Candidate == 2 ? TEXT("Attack_Melee_Air") : TEXT("Cast")); }
        TArray<UAnimSequence*> Sequences;
        for (const FString& Name : Names)
        {
            UAnimSequence* Sequence = LoadObject<UAnimSequence>(nullptr, *(FString(Folder) + Name + TEXT(".") + Name));
            if (!Sequence || Sequence->GetSkeleton() != Mesh->GetSkeletalMeshAsset()->GetSkeleton()) { return; }
            Sequences.Add(Sequence);
        }
        Character->InterruptIntroAnimation();
        Character->CancelBasicAttackForSkill();
        if (Character->GetSkills()) { Character->GetSkills()->CancelSkill(); }
        Anim->Montage_Stop(0.0f);
        UAnimMontage* Montage = UAnimMontage::CreateSlotAnimationAsDynamicMontage(Sequences[0], TEXT("CountessFullBody"), 0.06f, 0.10f, 1.0f, 1);
        if (!Montage) { return; }
        FAnimTrack& Track = Montage->SlotAnimTracks[0].AnimTrack;
        Track.AnimSegments.Reset();
        float SourceDuration = 0.0f;
        for (UAnimSequence* Sequence : Sequences)
        {
            if (Candidate == 4 && Sequence != Sequences[0]) { continue; }
            FAnimSegment Segment;
            Segment.SetAnimReference(Sequence);
            Segment.StartPos = SourceDuration;
            Segment.AnimStartTime = 0.0f;
            Segment.AnimEndTime = Candidate == 4 ? 0.25f : Sequence->GetPlayLength();
            Segment.AnimPlayRate = 1.0f / FMath::Max(FMath::Abs(Sequence->RateScale), 0.001f);
            Segment.LoopingCount = 1;
            Track.AnimSegments.Add(Segment);
            SourceDuration += Segment.AnimEndTime;
        }
        Montage->SetCompositeLength(SourceDuration);
        if (Candidate == 4) { Montage->bEnableAutoBlendOut = false; Montage->BlendOut.SetBlendTime(0.04f); SourceDuration = 0.25f + 0.55f + 0.27f; }
        const float Rate = Candidate == 4 ? 1.15f : (Candidate == 1 ? 1.2f : 1.0f);
        const float Duration = SourceDuration / Rate;
        const ERootMotionMode::Type SavedRootMotion = Anim->RootMotionMode;
        const bool bSavedOrient = Character->GetCharacterMovement()->bOrientRotationToMovement;
        Character->GetCharacterMovement()->StopMovementImmediately();
        Character->GetCharacterMovement()->bOrientRotationToMovement = false;
        Character->SetActorRotation((Target->GetActorLocation() - Character->GetActorLocation()).GetSafeNormal2D().Rotation());
        Anim->SetRootMotionMode(ERootMotionMode::IgnoreRootMotion);
        if (Anim->Montage_Play(Montage, Rate) <= 0.0f)
        {
            Anim->SetRootMotionMode(SavedRootMotion);
            Character->GetCharacterMovement()->bOrientRotationToMovement = bSavedOrient;
            return;
        }
        if (Candidate == 4)
        {
            // 각 구간을 별도 몽타주로 재생해 손과 검이 다음 준비 자세로 짧게 교차 블렌드된다.
            // 자동 블렌드아웃을 끈 끝 포즈에서 다음 몽타주의 0.04초 블렌드인과 겹치며 Idle을 거치지 않는다.
            float SwitchTime = 0.25f / Rate;
            for (int32 ClipIndex = 1; ClipIndex < 3; ++ClipIndex)
            {
                const float ClipEnd = ClipIndex == 1 ? 0.55f : 0.27f;
                UAnimMontage* NextMontage = UAnimMontage::CreateSlotAnimationAsDynamicMontage(Sequences[ClipIndex], TEXT("CountessFullBody"), 0.04f, 0.04f, 1.0f, 1);
                if (!NextMontage) { continue; }
                FAnimSegment& NextSegment = NextMontage->SlotAnimTracks[0].AnimTrack.AnimSegments[0];
                NextSegment.AnimEndTime = ClipEnd;
                NextSegment.AnimPlayRate = 1.0f / FMath::Max(FMath::Abs(Sequences[ClipIndex]->RateScale), 0.001f);
                NextMontage->SetCompositeLength(ClipEnd);
                NextMontage->bEnableAutoBlendOut = false;
                const TSharedRef<TStrongObjectPtr<UAnimMontage>> QueuedMontage = MakeShared<TStrongObjectPtr<UAnimMontage>>(NextMontage);
                const TWeakObjectPtr<UAnimInstance> QueuedAnim = Anim;
                FTimerHandle SwitchTimer;
                World->GetTimerManager().SetTimer(SwitchTimer, FTimerDelegate::CreateWeakLambda(Character, [QueuedMontage, QueuedAnim, Rate]()
                {
                    if (QueuedAnim.IsValid()) { QueuedAnim->Montage_Play(QueuedMontage->Get(), Rate); }
                }), SwitchTime, false);
                SwitchTime += ClipEnd / Rate;
                if (ClipIndex == 2)
                {
                    FTimerHandle FadeTimer;
                    World->GetTimerManager().SetTimer(FadeTimer, FTimerDelegate::CreateWeakLambda(Character, [QueuedMontage, QueuedAnim]()
                    {
                        if (QueuedAnim.IsValid()) { QueuedAnim->Montage_Stop(0.04f, QueuedMontage->Get()); }
                    }), Duration + 0.07f, false);
                }
            }
        }
        TArray<TWeakObjectPtr<UParticleSystemComponent>> Trails;
        if (Candidate != 3)
        {
            UParticleSystem* Effect = LoadObject<UParticleSystem>(nullptr, TEXT("/Game/ParagonCountess/FX/Particles/p_CountessMeleeTrail.p_CountessMeleeTrail"));
            for (const TCHAR* Side : {TEXT("L"), TEXT("R")})
            {
                const FName Base(*FString::Printf(TEXT("FX_WeaponBase_%s"), Side));
                const FName Tip(*FString::Printf(TEXT("FX_WeaponTip_%s"), Side));
                if (!Mesh->DoesSocketExist(Base) || !Mesh->DoesSocketExist(Tip)) { continue; }
                UParticleSystemComponent* Trail = UCountessSkillComponent::SpawnEffect(World, Effect, Mesh->GetComponentLocation(), Mesh->GetComponentRotation(), 1.0f, Character, 2.0f, true);
                if (Trail) { Trail->BeginTrails(Base, Tip, ETrailWidthMode_FromCentre, 1.0f); Trails.Add(Trail); }
            }
        }
        else
        {
            UParticleSystem* Mark = LoadObject<UParticleSystem>(nullptr, TEXT("/Game/ParagonCountess/FX/Particles/Abilities/Ultimate/FX/p_CountessUlt_AimingFX.p_CountessUlt_AimingFX"));
            UCountessSkillComponent::SpawnEffect(World, Mark, Target->GetActorLocation() - FVector(0, 0, Target->GetSimpleCollisionHalfHeight()), Character->GetActorRotation(), 0.75f, Target, 2.0f);
        }
        TArray<float> Hits = Candidate == 4 ? TArray<float>{0.10f, 0.19f, 0.35f, 0.41f, 0.80f, 0.87f} : (Candidate == 1 ? TArray<float>{0.22f, 0.72f, 1.14f} : (Candidate == 2 ? TArray<float>{0.55f} : TArray<float>{0.55f, 0.72f, 0.89f, 1.06f}));
        const TWeakObjectPtr<AActor> WeakTarget = Target;
        for (const float Time : Hits)
        {
            FTimerHandle HitTimer;
            World->GetTimerManager().SetTimer(HitTimer, FTimerDelegate::CreateWeakLambda(Character, [Character, WeakTarget, Time, Candidate]()
            {
                if (!WeakTarget.IsValid()) { return; }
                UParticleSystem* Impact = LoadObject<UParticleSystem>(nullptr, TEXT("/Game/ParagonCountess/FX/Particles/Abilities/BlinkStrike/FX/P_Countess_BlinkStrike_HitFX.P_Countess_BlinkStrike_HitFX"));
                UCountessSkillComponent::SpawnEffect(Character->GetWorld(), Impact, WeakTarget->GetActorLocation(), Character->GetActorRotation(), Candidate == 4 ? 0.50f : 0.75f, WeakTarget.Get(), Candidate == 4 ? 0.14f : 2.0f - Time);
            }), Time, false);
        }
        if (Candidate == 4)
        {
            FTimerHandle TrailEndTimer;
            World->GetTimerManager().SetTimer(TrailEndTimer, FTimerDelegate::CreateWeakLambda(Character, [Trails]()
            {
                for (const TWeakObjectPtr<UParticleSystemComponent>& Trail : Trails)
                {
                    if (Trail.IsValid()) { Trail->EndTrails(); Trail->DeactivateSystem(); }
                }
            }), Duration, false);
        }
        FTimerHandle RestoreTimer;
        const TWeakObjectPtr<UAnimInstance> WeakAnim = Anim;
        World->GetTimerManager().SetTimer(RestoreTimer, FTimerDelegate::CreateWeakLambda(Character, [Character, WeakAnim, SavedRootMotion, bSavedOrient, Trails]()
        {
            for (const TWeakObjectPtr<UParticleSystemComponent>& Trail : Trails)
            {
                if (Trail.IsValid()) { Trail->EndTrails(); Trail->DeactivateSystem(); }
            }
            if (WeakAnim.IsValid()) { WeakAnim->SetRootMotionMode(SavedRootMotion); }
            Character->GetCharacterMovement()->bOrientRotationToMovement = bSavedOrient;
        }), Duration + (Candidate == 4 ? 0.12f : 0.10f), false);
        UE_LOG(LogTemp, Display, TEXT("Countess E visual preview %d: duration=%.3f rate=%.2f target=%s no damage"), Candidate, Duration, Rate, *Target->GetName());
    }));
// 원본 PIE 렌더 타깃 크기를 고정해 에디터 창 배치 변화와 무관한 비교 화면을 만든다.
static FAutoConsoleCommandWithWorldAndArgs SetVisualQAViewportSize(
    TEXT("CharacterVisualQA.ViewportSize"), TEXT("PIE only: width height, positive ASCII integers up to 2048 each"),
    FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
    {
        if (!World || World->WorldType != EWorldType::PIE || Args.Num() != 2) { return; }
        int32 Requested[2] = {0, 0};
        for (int32 Index = 0; Index < 2; ++Index)
        {
            const FString& Argument = Args[Index];
            if (Argument.IsEmpty() || Argument.Len() > 4) { return; }
            for (const TCHAR Digit : Argument)
            {
                if (Digit < TEXT('0') || Digit > TEXT('9')) { return; }
            }
            Requested[Index] = FCString::Atoi(*Argument);
            if (Requested[Index] <= 0 || Requested[Index] > 2048) { return; }
        }
        UGameViewportClient* Client = World->GetGameViewport();
        FSceneViewport* Viewport = Client ? Client->GetGameViewport() : nullptr;
        if (!Viewport) { return; }
        Viewport->SetFixedViewportSize(Requested[0], Requested[1]);
        const FIntPoint Actual = Viewport->GetSizeXY();
        UE_LOG(LogTemp, Display, TEXT("CharacterVisualQA.ViewportSize requested=(%d,%d) actual=(%d,%d) match=%d"),
            Requested[0], Requested[1], Actual.X, Actual.Y, Actual == FIntPoint(Requested[0], Requested[1]));
    }));
// 지정된 PIE 뷰포트의 완성된 프레임을 동기 저장한다. 전역 HighResShot 요청을 사용하지 않는다.
static FAutoConsoleCommandWithWorldAndArgs CaptureVisualQAViewport(
    TEXT("CharacterVisualQA.Capture"), TEXT("PIE only: safe screenshot filename token"),
    FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
    {
        if (!World || World->WorldType != EWorldType::PIE || Args.Num() != 1 ||
            Args[0].Contains(TEXT("/")) || Args[0].Contains(TEXT("\\")) || Args[0].Contains(TEXT(".."))) { return; }
        UGameViewportClient* Client = World->GetGameViewport();
        FViewport* Viewport = Client ? Client->Viewport : nullptr;
        if (!Viewport) { return; }
        const FIntPoint Size = Viewport->GetSizeXY();
        TArray<FColor> Pixels;
        if (Size.X <= 0 || Size.Y <= 0 || !Viewport->ReadPixels(Pixels) || Pixels.Num() != Size.X * Size.Y) { return; }
        for (FColor& Pixel : Pixels) { Pixel.A = 255; }
        TArray64<uint8> PNG;
        FImageUtils::PNGCompressImageArray(Size.X, Size.Y, MakeArrayView(Pixels), PNG);
        const FString Directory = CharacterPipelineQA::GetOutputDirectory(TEXT("QA/Sparrow")) / TEXT("screenshots");
        IFileManager::Get().MakeDirectory(*Directory, true);
        FFileHelper::SaveArrayToFile(PNG, *(Directory / (Args[0] + TEXT(".png"))));
    }));
#endif
