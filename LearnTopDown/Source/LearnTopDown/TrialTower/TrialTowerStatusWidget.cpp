#include "TrialTowerStatusWidget.h"
#include "TrialTowerEncounter.h"
#include "../PlayerCombatComponent.h"

#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Blueprint/WidgetTree.h"
#include "Brushes/SlateRoundedBoxBrush.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/ProgressBar.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Styling/CoreStyle.h"
#include "GameFramework/PlayerController.h"

#define LOCTEXT_NAMESPACE "TrialTowerStatus"

void UTrialTowerStatusWidget::InitializeEncounter(ATrialTowerEncounter* InEncounter)
{
	Encounter = InEncounter;
	Refresh();
}

TSharedRef<SWidget> UTrialTowerStatusWidget::RebuildWidget()
{
	// The root must exist before UUserWidget builds its Slate content.
	BuildLayout();
	return Super::RebuildWidget();
}

void UTrialTowerStatusWidget::BuildLayout()
{
	if (WidgetTree && WidgetTree->RootWidget)
	{
		return;
	}
	if (!WidgetTree)
	{
		WidgetTree = NewObject<UWidgetTree>(this, TEXT("WidgetTree"), RF_Transient);
	}
	UCanvasPanel* Root = WidgetTree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass(), TEXT("TowerStatusRoot"));
	Root->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
	WidgetTree->RootWidget = Root;
	USizeBox* Width = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass(), TEXT("TowerStatusWidth"));
	Width->SetWidthOverride(340.0f);
	Width->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
	UCanvasPanelSlot* Position = Root->AddChildToCanvas(Width);
	Position->SetAnchors(FAnchors(0.5f, 0.0f));
	Position->SetAlignment(FVector2D(0.5f, 0.0f));
	Position->SetPosition(FVector2D(0.0f, 18.0f));
	Position->SetAutoSize(true);

	UBorder* Panel = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), TEXT("TowerStatusPanel"));
	Panel->SetBrushColor(FLinearColor(0.025f, 0.032f, 0.04f, 0.90f));
	Panel->SetPadding(FMargin(16.0f, 10.0f));
	Panel->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
	Width->SetContent(Panel);
	UVerticalBox* Column = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass(), TEXT("TowerStatusColumn"));
	Column->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
	Panel->SetContent(Column);

	auto MakeText = [this](const FName Name, float Size, const FName Typeface, FLinearColor Color)
	{
		UTextBlock* Text = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), Name);
		Text->SetFont(FCoreStyle::GetDefaultFontStyle(Typeface, Size));
		Text->SetColorAndOpacity(FSlateColor(Color));
		Text->SetJustification(ETextJustify::Center);
		Text->SetShadowOffset(FVector2D(0.0f, 1.0f));
		Text->SetShadowColorAndOpacity(FLinearColor(0.0f, 0.0f, 0.0f, 0.7f));
		Text->SetVisibility(ESlateVisibility::HitTestInvisible);
		return Text;
	};
	FloorText = MakeText(TEXT("FloorText"), 18.0f, TEXT("Bold"), FLinearColor(0.92f, 0.94f, 0.96f));
	Column->AddChildToVerticalBox(FloorText)->SetPadding(FMargin(0.0f, 0.0f, 0.0f, 5.0f));
	StatusText = MakeText(TEXT("StatusText"), 14.0f, TEXT("Regular"), FLinearColor(0.72f, 0.78f, 0.83f));
	StatusText->SetAutoWrapText(true);
	Column->AddChildToVerticalBox(StatusText);
	RemainingText = MakeText(TEXT("RemainingText"), 15.0f, TEXT("Bold"), FLinearColor(0.87f, 0.85f, 0.72f));
	Column->AddChildToVerticalBox(RemainingText)->SetPadding(FMargin(0.0f, 5.0f, 0.0f, 0.0f));
	HealthText = MakeText(TEXT("HealthText"), 14.0f, TEXT("Bold"), FLinearColor(0.76f, 0.91f, 0.84f));
	Column->AddChildToVerticalBox(HealthText)->SetPadding(FMargin(0.0f, 9.0f, 0.0f, 4.0f));
	USizeBox* HealthHeight = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass(), TEXT("HealthHeight"));
	HealthHeight->SetHeightOverride(9.0f);
	HealthHeight->SetVisibility(ESlateVisibility::HitTestInvisible);
	Column->AddChildToVerticalBox(HealthHeight);
	HealthBar = WidgetTree->ConstructWidget<UProgressBar>(UProgressBar::StaticClass(), TEXT("HealthBar"));
	HealthBar->SetVisibility(ESlateVisibility::HitTestInvisible);
	FProgressBarStyle HealthStyle = HealthBar->GetWidgetStyle();
	HealthStyle.SetBackgroundImage(FSlateRoundedBoxBrush(FLinearColor(0.07f, 0.09f, 0.10f), 3.0f));
	HealthStyle.SetFillImage(FSlateRoundedBoxBrush(FLinearColor::White, 3.0f));
	HealthStyle.SetEnableFillAnimation(false);
	DamageTrailBar = WidgetTree->ConstructWidget<UProgressBar>(UProgressBar::StaticClass(), TEXT("DamageTrailBar"));
	DamageTrailBar->SetVisibility(ESlateVisibility::HitTestInvisible);
	DamageTrailBar->SetWidgetStyle(HealthStyle);
	DamageTrailBar->SetBarFillStyle(EProgressBarFillStyle::Scale);
	DamageTrailBar->SetBorderPadding(FVector2D::ZeroVector);
	DamageTrailBar->SetFillColorAndOpacity(FLinearColor(0.92f, 0.48f, 0.28f));
	HealthStyle.SetBackgroundImage(FSlateRoundedBoxBrush(FLinearColor::Transparent, 3.0f));
	HealthBar->SetWidgetStyle(HealthStyle);
	HealthBar->SetBarFillStyle(EProgressBarFillStyle::Scale);
	HealthBar->SetBorderPadding(FVector2D::ZeroVector);
	UOverlay* HealthLayers = WidgetTree->ConstructWidget<UOverlay>(UOverlay::StaticClass(), TEXT("HealthLayers"));
	HealthLayers->SetVisibility(ESlateVisibility::HitTestInvisible);
	for (UProgressBar* Layer : {DamageTrailBar.Get(), HealthBar.Get()})
	{
		UOverlaySlot* LayerSlot = HealthLayers->AddChildToOverlay(Layer);
		LayerSlot->SetHorizontalAlignment(HAlign_Fill);
		LayerSlot->SetVerticalAlignment(VAlign_Fill);
	}
	HealthHeight->SetContent(HealthLayers);

	RestartButton = WidgetTree->ConstructWidget<UButton>(UButton::StaticClass(), TEXT("RestartButton"));
	FButtonStyle Style = RestartButton->GetStyle();
	Style.SetNormal(FSlateRoundedBoxBrush(FLinearColor(0.13f, 0.17f, 0.21f), 4.0f));
	Style.SetHovered(FSlateRoundedBoxBrush(FLinearColor(0.21f, 0.28f, 0.34f), 4.0f));
	Style.SetPressed(FSlateRoundedBoxBrush(FLinearColor(0.09f, 0.13f, 0.17f), 4.0f));
	Style.SetNormalPadding(FMargin(12.0f, 6.0f));
	Style.SetPressedPadding(FMargin(12.0f, 7.0f, 12.0f, 5.0f));
	RestartButton->SetStyle(Style);
	RestartButton->SetVisibility(ESlateVisibility::Collapsed);
	UTextBlock* RestartLabel = MakeText(TEXT("RestartLabel"), 15.0f, TEXT("Bold"), FLinearColor(0.94f, 0.96f, 0.98f));
	RestartLabel->SetText(LOCTEXT("Restart", "다시 도전"));
	RestartButton->SetContent(RestartLabel);
	UVerticalBoxSlot* ButtonSlot = Column->AddChildToVerticalBox(RestartButton);
	ButtonSlot->SetPadding(FMargin(50.0f, 9.0f, 50.0f, 0.0f));
	ButtonSlot->SetHorizontalAlignment(HAlign_Fill);
}

void UTrialTowerStatusWidget::NativeConstruct()
{
	Super::NativeConstruct();
	SetVisibility(ESlateVisibility::SelfHitTestInvisible);
	SetIsFocusable(false);
	if (RestartButton)
	{
		RestartButton->OnClicked.AddUniqueDynamic(this, &UTrialTowerStatusWidget::HandleRestart);
	}
	Refresh();
}

void UTrialTowerStatusWidget::NativeDestruct()
{
	if (RestartButton)
	{
		RestartButton->OnClicked.RemoveDynamic(this, &UTrialTowerStatusWidget::HandleRestart);
	}
	Super::NativeDestruct();
}

void UTrialTowerStatusWidget::NativeTick(const FGeometry& MyGeometry, float InDeltaTime)
{
	Super::NativeTick(MyGeometry, InDeltaTime);
	if (!DamageTrailBar || !HealthBar) { return; }
	const APlayerController* Player = GetOwningPlayer();
	const UPlayerCombatComponent* Combat = Player ? Player->FindComponentByClass<UPlayerCombatComponent>() : nullptr;
	DamageTrailBar->SetPercent(Combat && Combat->UsesNonInterruptingDamageFeedback() ?
		Combat->GetDamageTrailHealth() / Combat->GetMaxHealth() : HealthBar->GetPercent());
}

void UTrialTowerStatusWidget::Refresh()
{
	ATrialTowerEncounter* Run = Encounter.Get();
	if (!Run || !FloorText || !StatusText || !RemainingText || !HealthText || !HealthBar || !RestartButton)
	{
		return;
	}
	FloorText->SetText(FText::Format(LOCTEXT("Floor", "시험의 탑  {0} / {1}층"),
		FText::AsNumber(Run->GetFloorNumber()), FText::AsNumber(Run->GetFloorCount())));
	StatusText->SetText(Run->GetStatusText());
	const ETrialTowerRunState State = Run->GetRunState();
	const bool bFighting = State == ETrialTowerRunState::Fighting;
	const bool bDefeated = State == ETrialTowerRunState::Defeated;
	const bool bHitFeedback = bFighting && Run->IsPlayerInvulnerable();
	const float Health = Run->GetPlayerHealth();
	const float MaxHealth = Run->GetMaxPlayerHealth();
	const float HealthFraction = MaxHealth > 0.0f ? FMath::Clamp(Health / MaxHealth, 0.0f, 1.0f) : 0.0f;
	HealthBar->SetPercent(HealthFraction);
	const FLinearColor HealthColor = bDefeated || bHitFeedback ? FLinearColor(0.95f, 0.16f, 0.12f) :
		(HealthFraction <= 0.3f ? FLinearColor(0.92f, 0.42f, 0.14f) : FLinearColor(0.25f, 0.72f, 0.51f));
	HealthBar->SetFillColorAndOpacity(HealthColor);
	HealthText->SetColorAndOpacity(FSlateColor(bDefeated || bHitFeedback ? FLinearColor(1.0f, 0.44f, 0.38f) :
		FLinearColor(0.76f, 0.91f, 0.84f)));
	HealthText->SetText(FText::Format(bHitFeedback ? LOCTEXT("HealthHit", "체력  {0} / {1}  ·  피격") :
		LOCTEXT("Health", "체력  {0} / {1}"), FText::AsNumber(FMath::CeilToInt(Health)),
		FText::AsNumber(FMath::CeilToInt(MaxHealth))));
	if (bDefeated)
	{
		StatusText->SetText(LOCTEXT("Defeated", "쓰러졌습니다 · 다시 도전해 보세요"));
	}
	StatusText->SetColorAndOpacity(FSlateColor(bDefeated ? FLinearColor(1.0f, 0.55f, 0.48f) :
		FLinearColor(0.72f, 0.78f, 0.83f)));
	RemainingText->SetText(FText::Format(LOCTEXT("Remaining", "남은 몬스터  {0}"), FText::AsNumber(Run->GetRemainingMonsters())));
	RemainingText->SetVisibility(bFighting ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
	const bool bCanRestart = bDefeated || State == ETrialTowerRunState::Complete || State == ETrialTowerRunState::Error;
	RestartButton->SetVisibility(bCanRestart ? ESlateVisibility::Visible : ESlateVisibility::Collapsed);
	RestartButton->SetIsEnabled(bCanRestart);
}

void UTrialTowerStatusWidget::HandleRestart()
{
	if (ATrialTowerEncounter* Run = Encounter.Get())
	{
		const ETrialTowerRunState State = Run->GetRunState();
		if (State == ETrialTowerRunState::Defeated || State == ETrialTowerRunState::Complete || State == ETrialTowerRunState::Error)
		{
			Run->RestartRun();
			UWidgetBlueprintLibrary::SetFocusToGameViewport();
		}
	}
}

#undef LOCTEXT_NAMESPACE
