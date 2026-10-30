#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "TrialTowerStatusWidget.generated.h"

class ATrialTowerEncounter;
class UButton;
class UProgressBar;
class UTextBlock;

UCLASS()
class LEARNTOPDOWN_API UTrialTowerStatusWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	void InitializeEncounter(ATrialTowerEncounter* InEncounter);
	void Refresh();

protected:
	virtual TSharedRef<SWidget> RebuildWidget() override;
	virtual void NativeConstruct() override;
	virtual void NativeDestruct() override;
	virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;

private:
	void BuildLayout();
	UFUNCTION()
	void HandleRestart();

	TWeakObjectPtr<ATrialTowerEncounter> Encounter;
	UPROPERTY(Transient, BlueprintReadOnly, Category = "Trial Tower", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<UTextBlock> FloorText;
	UPROPERTY(Transient, BlueprintReadOnly, Category = "Trial Tower", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<UTextBlock> StatusText;
	UPROPERTY(Transient, BlueprintReadOnly, Category = "Trial Tower", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<UTextBlock> RemainingText;
	UPROPERTY(Transient, BlueprintReadOnly, Category = "Trial Tower", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<UTextBlock> HealthText;
	UPROPERTY(Transient, BlueprintReadOnly, Category = "Trial Tower", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<UProgressBar> HealthBar;
	UPROPERTY(Transient, BlueprintReadOnly, Category = "Trial Tower", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<UProgressBar> DamageTrailBar;
	UPROPERTY(Transient, BlueprintReadOnly, Category = "Trial Tower", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<UButton> RestartButton;
};
