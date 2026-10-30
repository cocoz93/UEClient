#include "AuroraCharacter.h"

#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "AuroraSkillComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "UObject/ConstructorHelpers.h"

AAuroraCharacter::AAuroraCharacter(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer.SetDefaultSubobjectClass<UAuroraSkillComponent>(SkillComponentName))
{
	GetCapsuleComponent()->InitCapsuleSize(42.0f, 96.0f);
	// 커서의 지면 선택이 캐릭터 자신에게 가로막히지 않도록 기존 필드 캐릭터와 맞춘다.
	GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility, ECR_Ignore);
	GetMesh()->SetCollisionResponseToChannel(ECC_Visibility, ECR_Ignore);
	GetMesh()->SetRelativeLocation(FVector(0.0f, 0.0f, -96.0f));
	GetMesh()->SetRelativeRotation(FRotator(0.0f, -90.0f, 0.0f));

	static ConstructorHelpers::FObjectFinder<USkeletalMesh> Body(
		TEXT("/Game/ParagonAurora/Characters/Heroes/Aurora/Meshes/Aurora.Aurora"));
	// 원본 애니 BP의 사본. 1번(Countess) 사본처럼 출발·멈춤 동작(JogStart·JogStop)을 건너뛰고 Idle↔Run을 바로 섞어,
	// 짧게 움직일 때 멈춤 동작(약 1초)이 끝까지 나오지 않게 한다(Tools/CharacterPipeline/aurora_topdown_anim_build.py로 생성).
	static ConstructorHelpers::FClassFinder<UAnimInstance> Locomotion(
		TEXT("/Game/TopDown/Characters/Aurora/Animations/ABP_Aurora_TopDown"));
	GetMesh()->SetSkeletalMeshAsset(Body.Object);
	GetMesh()->SetAnimationMode(EAnimationMode::AnimationBlueprint);
	GetMesh()->SetAnimInstanceClass(Locomotion.Class);

	// 원본 평타 3타. 몽타주의 명명 노티파이(연계 시점)는 부모가 저장된 시점으로 읽는다.
	static ConstructorHelpers::FObjectFinder<UAnimMontage> AttackA(
		TEXT("/Game/ParagonAurora/Characters/Heroes/Aurora/Animations/Primary_Attack_A_Montage.Primary_Attack_A_Montage"));
	static ConstructorHelpers::FObjectFinder<UAnimMontage> AttackB(
		TEXT("/Game/ParagonAurora/Characters/Heroes/Aurora/Animations/Primary_Attack_B_Montage.Primary_Attack_B_Montage"));
	static ConstructorHelpers::FObjectFinder<UAnimMontage> AttackC(
		TEXT("/Game/ParagonAurora/Characters/Heroes/Aurora/Animations/Primary_Attack_C_Montage.Primary_Attack_C_Montage"));
	for (UAnimMontage* Montage : {AttackA.Object, AttackB.Object, AttackC.Object})
	{
		FBasicAttackComboStep Step;
		Step.Montage = Montage;
		// 세 몽타주 모두 길이 1.0초. 타격은 연계 시점(SaveAttack)보다 앞이어야 한다(BeginPlay의 AURORA_COMBO 로그).
		Step.HitTimeFraction = 0.25f;
		// 사용자 요청으로 원본보다 빠르게 휘두른다(2026-10-18). 타격·연계 시점도 같은 배율로 당겨진다.
		Step.PlayRate = BaseAttackPlayRate;
		ComboAttacks.Add(Step);
	}
	// 근접 베기 범위. 판정은 스킬 부품이 맡아 맞은 자리에 원본 타격 이펙트를 띄운다.
	AttackRange = 260.0f;
	AttackHalfAngle = 60.0f;
	AttackDamage = 22.0f;

	// 이동 수치는 스패로우·Gideon 프로필과 같다.
	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->MaxWalkSpeed = BaseWalkSpeed;
	Movement->MaxAcceleration = 5000.0f;
	Movement->BrakingDecelerationWalking = 6000.0f;
	Movement->RotationRate = FRotator(0.0f, 720.0f, 0.0f);
	Movement->bRequestedMoveUseAcceleration = true;
	Movement->GetNavMovementProperties()->bUseAccelerationForPaths = true;

	CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
	CameraBoom->SetupAttachment(RootComponent);
	CameraBoom->TargetArmLength = 2000.0f;
	CameraBoom->SetUsingAbsoluteRotation(true);
	// 기존 카운테스 필드의 실제 SpringArm/Camera 설정과 같은 시점을 사용한다.
	CameraBoom->SetRelativeRotation(FRotator(-50.0f, 45.0f, 0.0f));
	CameraBoom->bDoCollisionTest = false;
	CameraBoom->bEnableCameraLag = true;
	CameraBoom->CameraLagSpeed = 3.0f;
	TopDownCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("TopDownCamera"));
	TopDownCamera->SetupAttachment(CameraBoom, USpringArmComponent::SocketName);
	TopDownCamera->bUsePawnControlRotation = false;
	TopDownCamera->SetFieldOfView(55.0f);
	TopDownCamera->OrthoWidth = 512.0f;
	TopDownCamera->OrthoNearClipPlane = 0.0f;
	TopDownCamera->bAutoCalculateOrthoPlanes = false;
}

UAuroraSkillComponent* AAuroraCharacter::GetAuroraSkills() const
{
	return Cast<UAuroraSkillComponent>(GetSkills());
}

FRotator AAuroraCharacter::GetBaseAimRotation() const
{
	return FRotator(0.0f, GetActorRotation().Yaw, 0.0f);
}

void AAuroraCharacter::SetSpeedScale(float AttackScale, float MoveScale)
{
	// 다음 타부터 새 배율로 재생된다(지금 휘두르는 타는 그대로).
	for (FBasicAttackComboStep& Step : ComboAttacks)
	{
		Step.PlayRate = BaseAttackPlayRate * AttackScale;
	}
	GetCharacterMovement()->MaxWalkSpeed = BaseWalkSpeed * MoveScale;
}

float AAuroraCharacter::TakeDamage(float DamageAmount, const FDamageEvent& DamageEvent, AController* EventInstigator, AActor* DamageCauser)
{
	const UAuroraSkillComponent* Skills = GetAuroraSkills();
	const float Scaled = DamageAmount * (Skills ? Skills->GetIncomingDamageScale() : 1.0f);
	UE_LOG(LogTemp, Display, TEXT("AURORA_TAKE in=%.0f out=%.0f"), DamageAmount, Scaled);
	return Super::TakeDamage(Scaled, DamageEvent, EventInstigator, DamageCauser);
}

void AAuroraCharacter::BeginPlay()
{
	Super::BeginPlay();
	// 평타 타격 시점(HitTimeFraction)을 연계 시점보다 앞에 두는 근거로 원본 노티파이 시점을 남긴다.
	for (int32 Index = 0; Index < ComboAttacks.Num(); ++Index)
	{
		const UAnimMontage* Montage = ComboAttacks[Index].Montage;
		if (!Montage)
		{
			continue;
		}
		FString Notifies;
		for (const FAnimNotifyEvent& Notify : Montage->Notifies)
		{
			Notifies += FString::Printf(TEXT("%s@%.3f "), *Notify.NotifyName.ToString(), Notify.GetTriggerTime());
		}
		UE_LOG(LogTemp, Display, TEXT("AURORA_COMBO step=%d montage=%s length=%.3f rate=%.2f notifies=%s"), Index,
			*Montage->GetName(), Montage->GetPlayLength(), Montage->RateScale, *Notifies);
	}
}

void AAuroraCharacter::ExecuteBasicAttackHit()
{
	if (UAuroraSkillComponent* Skills = GetAuroraSkills())
	{
		Skills->ExecuteMeleeHit(AttackRange, AttackHalfAngle, AttackDamage, GetComboAttackNumber() - 1);
	}
}
