#include "GideonCharacter.h"

#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "GideonSkillComponent.h"
#include "UObject/ConstructorHelpers.h"

AGideonCharacter::AGideonCharacter(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer.SetDefaultSubobjectClass<UGideonSkillComponent>(SkillComponentName))
{
	GetCapsuleComponent()->InitCapsuleSize(42.0f, 96.0f);
	// 커서의 지면 선택이 캐릭터 자신에게 가로막히지 않도록 기존 필드 캐릭터와 맞춘다.
	GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility, ECR_Ignore);
	GetMesh()->SetCollisionResponseToChannel(ECC_Visibility, ECR_Ignore);
	GetMesh()->SetRelativeLocation(FVector(0.0f, 0.0f, -96.0f));
	GetMesh()->SetRelativeRotation(FRotator(0.0f, -90.0f, 0.0f));

	// 스킨 메시도 모두 기본 Gideon_Skeleton을 쓰므로 원본 애니 BP를 그대로 붙인다.
	static ConstructorHelpers::FObjectFinder<USkeletalMesh> Body(
		TEXT("/Game/ParagonGideon/Characters/Heroes/Gideon/Meshes/Gideon.Gideon"));
	static ConstructorHelpers::FClassFinder<UAnimInstance> Locomotion(
		TEXT("/Game/ParagonGideon/Characters/Heroes/Gideon/Gideon_AnimBlueprint"));
	GetMesh()->SetSkeletalMeshAsset(Body.Object);
	GetMesh()->SetAnimationMode(EAnimationMode::AnimationBlueprint);
	GetMesh()->SetAnimInstanceClass(Locomotion.Class);

	// 원본 평타 3타. 몽타주의 명명 노티파이(연계 시점)는 부모가 저장된 시점으로 읽는다.
	// 10-19 1타만 되풀이하던 것을 되돌리고 대신 BasicAttackPlayRate로 느리게 휘두른다(「평타 그냥 롤백, 대신 공속을 좀 낮춰」).
	static ConstructorHelpers::FObjectFinder<UAnimMontage> AttackA(
		TEXT("/Game/ParagonGideon/Characters/Heroes/Gideon/Animations/Primary_Attack_A_Medium_Montage.Primary_Attack_A_Medium_Montage"));
	static ConstructorHelpers::FObjectFinder<UAnimMontage> AttackB(
		TEXT("/Game/ParagonGideon/Characters/Heroes/Gideon/Animations/Primary_Attack_B_Medium_Montage.Primary_Attack_B_Medium_Montage"));
	static ConstructorHelpers::FObjectFinder<UAnimMontage> AttackC(
		TEXT("/Game/ParagonGideon/Characters/Heroes/Gideon/Animations/Primary_Attack_C_Medium_Montage.Primary_Attack_C_Medium_Montage"));
	for (UAnimMontage* Montage : {AttackA.Object, AttackB.Object, AttackC.Object})
	{
		FBasicAttackComboStep Step;
		Step.Montage = Montage;
		// 세 몽타주 모두 길이 1.233초, SaveAttack 0.377~0.399초. 누르고 있으면 그 시점에 다음 타로 넘어가며
		// 앞 타의 타격 타이머를 지우므로 발사는 그보다 앞이어야 한다.
		// 손을 내뻗는 동작은 세 타 모두 0.13~0.17초에 끝나므로(gideon_hand_timing_dump.py) 손이 다 뻗은 0.173초에 쏜다.
		// 재생 속도를 낮추면 발사·연계 시점도 같은 배율로 늦춰진다(1 / BasicAttackPlayRate배).
		Step.HitTimeFraction = 0.14f;
		Step.PlayRate = BasicAttackPlayRate;
		ComboAttacks.Add(Step);
	}
	// 발사 뒤 남은 동작(1·2타 약 0.76초, 3타 약 1.07초 + 재시작 0.3초)을 0.2초에서 끊는다(「평타 후딜레이 줄여줘 너무 길어」 10-20).
	// 누르고 있거나 다음 클릭이 예약돼 있으면 1·2타는 원래 연계 시점에 다음 타로 넘어가 공속은 그대로다.
	RecoveryAfterHit = 0.2f;

	// 이동 수치는 스패로우 프로필과 같다.
	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->MaxWalkSpeed = 600.0f;
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

UGideonSkillComponent* AGideonCharacter::GetGideonSkills() const
{
	return Cast<UGideonSkillComponent>(GetSkills());
}

FRotator AGideonCharacter::GetBaseAimRotation() const
{
	return FRotator(0.0f, GetActorRotation().Yaw, 0.0f);
}

void AGideonCharacter::BeginPlay()
{
	Super::BeginPlay();
	// 평타 발사 시점(HitTimeFraction)을 연계 시점보다 앞에 두는 근거로 원본 노티파이 시점을 남긴다.
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
		UE_LOG(LogTemp, Display, TEXT("GIDEON_COMBO step=%d montage=%s length=%.3f rate=%.2f notifies=%s"), Index,
			*Montage->GetName(), Montage->GetPlayLength(), Montage->RateScale, *Notifies);
	}
}

void AGideonCharacter::ExecuteBasicAttackHit()
{
	// 근접 부채꼴 판정 대신 현재 콤보 단계의 손에서 투사체를 쏜다.
	if (UGideonSkillComponent* Skills = GetGideonSkills())
	{
		Skills->FireBasicAttack(GetActiveAttackAimLocation(), GetComboAttackNumber() - 1);
	}
}
