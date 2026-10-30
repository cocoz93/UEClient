#include "KwangTrainingDummy.h"

#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "DrawDebugHelpers.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"

static TAutoConsoleVariable<int32> CVarCountessHitMarkers(
	TEXT("Countess.Debug.HitMarkers"), 0,
	TEXT("1 draws training-dummy hit spheres; 0 shows the actual combat effects without debug geometry."));

AKwangTrainingDummy::AKwangTrainingDummy()
{
	PrimaryActorTick.bCanEverTick = false;
	Capsule = CreateDefaultSubobject<UCapsuleComponent>(TEXT("Capsule"));
	SetRootComponent(Capsule);
	Capsule->InitCapsuleSize(35.0f, 90.0f);
	Capsule->SetCollisionProfileName(TEXT("BlockAllDynamic"));
	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	Mesh->SetupAttachment(Capsule);
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Mesh->SetRelativeScale3D(FVector(0.6f, 0.6f, 1.8f));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	Mesh->SetStaticMesh(Cube.Object);
	Label = CreateDefaultSubobject<UTextRenderComponent>(TEXT("HealthLabel"));
	Label->SetupAttachment(Capsule);
	Label->SetRelativeLocation(FVector(0.0f, 0.0f, 125.0f));
	Label->SetRelativeRotation(FRotator(0.0f, 225.0f, 0.0f));
	Label->SetHorizontalAlignment(EHTA_Center);
	Label->SetWorldSize(30.0f);
	UpdateLabel();
}

void AKwangTrainingDummy::BeginPlay()
{
	Super::BeginPlay();
	UpdateLabel();
}

float AKwangTrainingDummy::TakeDamage(float DamageAmount, const FDamageEvent& DamageEvent,
	AController* EventInstigator, AActor* DamageCauser)
{
	if (!CanBeDamaged() || DamageAmount <= 0.0f || Health <= 0.0f)
	{
		return 0.0f;
	}
	const float Applied = FMath::Min(DamageAmount, Health);
	Health -= Applied;
	if (Health <= 0.0f)
	{
		// 스킬 시연 중에도 같은 표적을 계속 사용할 수 있도록 쓰러진 허수아비를 복구한다.
		GetWorldTimerManager().SetTimer(RespawnTimer, this, &AKwangTrainingDummy::ResetDummy, 3.0f, false);
	}
	UpdateLabel();
	if (CVarCountessHitMarkers.GetValueOnGameThread() != 0)
	{
		DrawDebugSphere(GetWorld(), GetActorLocation(), 75.0f, 12, FColor::Red, false, 0.25f);
	}
	UE_LOG(LogTemp, Display, TEXT("Kwang hit %s: damage=%.0f health=%.0f"), *GetName(), Applied, Health);
	return Applied;
}

void AKwangTrainingDummy::UpdateLabel()
{
	const FName Status = GetCombatStatus();
	const FString Suffix = Status.IsNone() ? FString() : TEXT("\n") + Status.ToString();
	Label->SetText(FText::FromString(FString::Printf(TEXT("HP %.0f / 100%s"), Health, *Suffix)));
	Label->SetTextRenderColor(Health > 0.0f ? FColor::White : FColor::Red);
}

void AKwangTrainingDummy::ResetDummy()
{
	GetWorldTimerManager().ClearTimer(RespawnTimer);
	Health = 100.0f;
	CombatStatus = NAME_None;
	StatusDeadline = 0.0;
	GetWorldTimerManager().ClearTimer(StatusTimer);
	UpdateLabel();
}

FName AKwangTrainingDummy::GetCombatStatus() const
{
	return GetWorld() && GetWorld()->GetTimeSeconds() < StatusDeadline ? CombatStatus : NAME_None;
}

void AKwangTrainingDummy::SetCombatStatus(FName Status, float Duration)
{
	CombatStatus = Status;
	StatusDeadline = GetWorld()->GetTimeSeconds() + Duration;
	GetWorldTimerManager().SetTimer(StatusTimer, this, &AKwangTrainingDummy::UpdateLabel, Duration, false);
	UpdateLabel();
}
