#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS

#include "CoreMinimal.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Input/Events.h"
#include "InputKeyEventArgs.h"
#include "Kismet/GameplayStatics.h"
#include "Slate/SceneViewport.h"
#include "Widgets/SViewport.h"

// Python에 노출되지 않은 게임 월드 생성 API를 사용하는 PIE 검사 전용 명령이다.
static FAutoConsoleCommandWithWorldAndArgs SpawnComboTestActor(
	TEXT("CountessComboQA.Spawn"), TEXT("PIE only: name class_path x y z"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (!World || World->WorldType != EWorldType::PIE || Args.Num() != 5)
		{
			return;
		}
		UClass* ActorClass = LoadClass<AActor>(nullptr, *Args[1]);
		if (!ActorClass)
		{
			return;
		}
		FActorSpawnParameters Params;
		Params.Name = FName(*Args[0]);
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		Params.ObjectFlags |= RF_Transient;
		AActor* Actor = World->SpawnActor<AActor>(ActorClass,
			FVector(FCString::Atod(*Args[2]), FCString::Atod(*Args[3]), FCString::Atod(*Args[4])),
			FRotator::ZeroRotator, Params);
		ensure(Actor);
	}));

// 실제 포커스 상실 경로와 같은 키 해제를 호출하는 PIE 입력 검사다.
static FAutoConsoleCommandWithWorldAndArgs FlushComboTestInput(
    TEXT("CountessComboQA.FlushInput"), TEXT("PIE only: release held input through the controller focus-loss path"),
    FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
    {
        if (World && World->WorldType == EWorldType::PIE && Args.IsEmpty())
        {
            if (APlayerController* Controller = UGameplayStatics::GetPlayerController(World, 0))
            {
                Controller->FlushPressedKeys();
            }
        }
    }));

// 뷰포트 캐시에만 좌표를 전달한다. OS 커서 이동이나 창 포커스 변경은 하지 않는다.
static FAutoConsoleCommandWithWorldAndArgs InjectComboMouseInput(
	TEXT("CountessComboQA.Mouse"), TEXT("PIE only: Press|Release|Move Left|Right target_x target_y target_z"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (!World || World->WorldType != EWorldType::PIE || Args.Num() != 5)
		{
			return;
		}
		APlayerController* Controller = UGameplayStatics::GetPlayerController(World, 0);
		ULocalPlayer* Player = Controller ? Controller->GetLocalPlayer() : nullptr;
		FSceneViewport* Viewport = Player && Player->ViewportClient ? Player->ViewportClient->GetGameViewport() : nullptr;
		TSharedPtr<SViewport> Widget = Viewport ? Viewport->GetViewportWidget().Pin() : nullptr;
		if (!Widget.IsValid())
		{
			return;
		}
		FVector2D Position;
		if (!Controller->ProjectWorldLocationToScreen(
			FVector(FCString::Atod(*Args[2]), FCString::Atod(*Args[3]), FCString::Atod(*Args[4])), Position))
		{
			return;
		}
		const FGeometry& Geometry = Widget->GetCachedGeometry();
		// 고정 렌더 크기와 Slate 위젯 크기가 달라도 같은 뷰포트 픽셀을 가리키도록 역변환한다.
		const FIntPoint ViewportSize = Viewport->GetSizeXY();
		const FVector2D ToViewportPixelScale = UE::Slate::Viewport::GetViewportLocalToPixelScale(
			Geometry, FVector2D(ViewportSize.X, ViewportSize.Y));
		if (ToViewportPixelScale.X <= 0.0 || ToViewportPixelScale.Y <= 0.0) { return; }
		const FVector2D AbsolutePosition = Geometry.LocalToAbsolute(Position / ToViewportPixelScale);
		const FPointerEvent MoveEvent(0, AbsolutePosition, AbsolutePosition,
			TSet<FKey>(), EKeys::Invalid, 0.0f, FModifierKeysState());
		Viewport->OnMouseMove(Geometry, MoveEvent);
		if (Args[0] == TEXT("Move"))
		{
			return;
		}
		Controller->InputKey(FInputKeyEventArgs(Viewport, FInputDeviceId::CreateFromInternalId(0),
			Args[1] == TEXT("Right") ? EKeys::RightMouseButton : EKeys::LeftMouseButton,
			Args[0] == TEXT("Release") ? IE_Released : IE_Pressed, FPlatformTime::Cycles64()));
	}));

#endif
