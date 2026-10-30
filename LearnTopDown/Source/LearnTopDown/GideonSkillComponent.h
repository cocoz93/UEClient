#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "CharacterSkillComponent.h"
#include "GideonProjectile.h"
#include "GideonSkillComponent.generated.h"

class ATopDownCombatCharacter;
class UAnimMontage;
class UAnimSequence;
class UDecalComponent;
class UInstancedStaticMeshComponent;
class UMaterialInterface;
class UParticleSystem;
class UParticleSystemComponent;
class UStaticMesh;
class UStaticMeshComponent;
class USplineMeshComponent;

// HUD 칸 번호 그대로다. Q W E R = 0..3, A S D = 8..10, V = 16, Space = 17 (CharacterSkillHUD의 18칸 배열).
UENUM(BlueprintType)
enum class EGideonSkill : uint8
{
	PortalBlast = 0,
	CosmicRift = 1,
	// 원작에 없는 스킬 셋(사용자 요청 10-18): Dekker 팩 효과(Line·Cage·SkyBeam)로 만든 것.
	StarLine = 2,
	StarCage = 3,
	Burden = 8,
	// 원작에 없는 스킬(사용자 요청 10-17): 작은 포털 셋에서 평타를 조준점 한 곳으로 모아 쏜다.
	PortalVolley = 9,
	// 원작에 없는 스킬(사용자 요청 10-18): 이름은 처음 만든 Sky Lance 그대로, 지금은 유성 낙하(Star Fall).
	SkyLance = 10,
	// 광선 붙잡기(사용자 요청 10-18).
	VoidRay = 11,
	// 궁극기는 V, 이동기는 Space(사용자 요청 10-18).
	BlackHole = 16,
	TornSpace = 17
};

USTRUCT()
struct FGideonSkillDefinition
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere)
	FName Name;
	UPROPERTY(EditAnywhere)
	TObjectPtr<UAnimSequence> Animation;
	UPROPERTY(EditAnywhere)
	TObjectPtr<UParticleSystem> CastEffect;
	UPROPERTY(EditAnywhere, meta = (ClampMin = "0.0"))
	float Damage = 0.0f;
	UPROPERTY(EditAnywhere, meta = (ClampMin = "0.0", Units = "s"))
	float Cooldown = 0.0f;
	UPROPERTY(EditAnywhere, meta = (ClampMin = "0.0", Units = "cm"))
	float Range = 0.0f;
	// 시전 시작부터 효과가 나가는 시점과, 그 뒤 다시 움직일 수 있을 때까지의 시간
	UPROPERTY(EditAnywhere, meta = (ClampMin = "0.0", Units = "s"))
	float ActionTime = 0.0f;
	UPROPERTY(EditAnywhere, meta = (ClampMin = "0.0", Units = "s"))
	float RecoveryTime = 0.0f;
	// 시전이 끝나도 남은 동작(팔 내리기 등)을 끊지 않고 끝까지 재생한다. 상체 칸 재생이라 걸으면서도 이어진다.
	UPROPERTY(EditAnywhere)
	bool bFinishAnimation = false;
};

// Gideon 원본 스킬 다섯(Portal Blast·Cosmic Rift·Torn Space·Black Hole·Burden)과 평타 투사체를 소유한다.
// 애니는 원본 애니 BP의 UpperBody 슬롯으로 재생해 블루프린트 사본 없이 동작한다.
UCLASS(ClassGroup = (Combat), meta = (BlueprintSpawnableComponent))
class LEARNTOPDOWN_API UGideonSkillComponent : public UCharacterSkillComponent
{
	GENERATED_BODY()

public:
	UGideonSkillComponent();
	virtual bool TryUseSkillSlot(int32 Slot, const FVector& AimLocation, AActor* Target) override;
	virtual bool IsCasting() const override { return bCasting; }
	virtual bool IsEnabled() const override { return bEnabled; }
	virtual int32 GetActiveSkillNumber() const override { return bCasting ? ActiveSlot + 1 : 0; }
	virtual int32 GetSkillCount() const override { return SlotCount; }
	virtual FText GetSkillDisplayName(int32 Slot) const override;
	virtual FText GetSkillStatusText(int32 Slot) const override;
	virtual float GetSlotCooldownRemaining(int32 Slot) const override;
	// S는 대상을 찍어야 쓴다(10-20 「논타겟으로 못 쓰게」 — A 시안 8은 10-21 도우미로 바뀌어 빠짐). 수련장 허수아비도 대상이다.
	virtual ECharacterSkillTargeting GetSkillTargeting(int32 Slot) const override;
	virtual bool IsSkillTargetValid(int32 Slot, const AActor* Target, const AActor* Caster) const override;
	virtual FString GetInputFeedback() const override;
	virtual bool IgnoresCooldowns() const override;
	virtual void CancelSkill() override;
	virtual bool PlacesLetterKeysOnLeftHud() const override { return true; }
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	// 평타 한 타. 콤보 단계마다 다른 손 소켓에서 쏜다.
	bool FireBasicAttack(const FVector& AimLocation, int32 ComboStep);
	void HandleProjectileStopped(EGideonProjectileKind Kind, const FVector& Location, AActor* Target);

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	UPROPERTY(EditDefaultsOnly, Category = "Skills")
	TMap<EGideonSkill, FGideonSkillDefinition> Skills;
	UPROPERTY(EditDefaultsOnly, Category = "Animation")
	FName CastSlot = TEXT("UpperBody");

private:
	static constexpr int32 SlotCount = 18;
	struct FBlackHoleTarget
	{
		TWeakObjectPtr<AActor> Actor;
		FVector Origin = FVector::ZeroVector;
	};
	// Q 운석: 하늘 시작점에서 조준점까지 대각선으로 떨어지는 동안 매 프레임 옮긴다(UpdateBlastMeteors).
	struct FBlastMeteor
	{
		TWeakObjectPtr<UParticleSystemComponent> Effect;
		FVector Start = FVector::ZeroVector;
		FVector End = FVector::ZeroVector;
		double StartTime = 0.0;
		float Duration = 0.0f;
	};
	// D 유성: 하늘에서 비스듬히 날아 바닥·벽·대상 중 먼저 닿는 곳에서 터진다(UpdateStarMeteors).
	struct FStarMeteor
	{
		TWeakObjectPtr<UParticleSystemComponent> Effect;
		FVector Location = FVector::ZeroVector;
		FVector Velocity = FVector::ZeroVector;
		// 떨어질 바닥 높이(목표 지점). 아무것에도 안 닿고 이 아래로 지나가면 여기서 터뜨린다.
		float Ground = 0.0f;
		float Damage = 0.0f;
		float Radius = 0.0f;
		float Scale = 1.0f;
		bool bStun = false;
	};
	// F 녹스 번개 끝·데스레이 불티 하나: 위치·속도·태어난 시각·수명·크기(cm).
	struct FNoxSpark
	{
		FVector Location = FVector::ZeroVector;
		FVector Velocity = FVector::ZeroVector;
		double Born = 0.0;
		float Life = 0.0f;
		float Size = 0.0f;
	};
	// 둥근 빛 점(D 유성 꼬리·F 11·V 빨려 드는 빛): 수명 동안 작아진다. 보통은 Velocity로 날고, Swirl(도/초)이 0이 아니면
	// Center 둘레(Offset)를 돌며 끝으로 갈수록 빨리 가운데로 빨려 든다.
	struct FGlowDot
	{
		FVector Location = FVector::ZeroVector;
		FVector Velocity = FVector::ZeroVector;
		double Born = 0.0;
		float Life = 0.0f;
		float Size = 0.0f;
		FVector Center = FVector::ZeroVector;
		FVector Offset = FVector::ZeroVector;
		float Swirl = 0.0f;
		float Pull = 2.0f;
	};
	struct FBurdenTarget
	{
		TWeakObjectPtr<AActor> Actor;
		TWeakObjectPtr<UParticleSystemComponent> Effect;
		// 3번 손과 대상을 잇는 원작 줄 모형. 매 프레임 두 끝을 다시 잡는다(UpdateBurdenTethers).
		TWeakObjectPtr<USplineMeshComponent> Tether;
		int32 TicksLeft = 0;
		FTimerHandle Timer;
	};

	const FGideonSkillDefinition* FindSkill(int32 Slot) const;
	bool RejectInput(const TCHAR* Reason);
	bool ClampGroundTarget(const FVector& Aim, float Range, bool bRequireNavigation, FVector& Result) const;
	bool BeginCast(EGideonSkill Skill, const FVector& Aim);
	void ExecuteAction(uint32 Generation);
	void FinishCast();
	void StartCooldown(EGideonSkill Skill);
	FVector GetSocketLocation(FName Socket) const;
	FVector GetFeetLocation() const;
	UParticleSystemComponent* SpawnOwnedEffect(UParticleSystem* Effect, const FVector& Location, const FRotator& Rotation = FRotator::ZeroRotator);
	void ReleaseOwnedEffect(UParticleSystemComponent* Effect);
	int32 ApplyAreaDamage(const FVector& Center, float Radius, float Damage, FName Status = NAME_None, float StatusSeconds = 0.0f);
	void GatherTargets(const FVector& Center, float Radius, TArray<AActor*>& Out) const;
	AGideonProjectile* LaunchProjectile(EGideonProjectileKind Kind, FName Socket, const FVector& Aim, float Speed, float Range, float Damage,
		UParticleSystem* Trail, UParticleSystem* HitCharacter, UParticleSystem* HitWorld, UParticleSystem* NoHit);
	AGideonProjectile* LaunchProjectileFrom(EGideonProjectileKind Kind, FVector Origin, const FVector& Aim, float Speed, float Range,
		float Damage, UParticleSystem* Trail, UParticleSystem* HitCharacter, UParticleSystem* HitWorld, UParticleSystem* NoHit);

	void ExecutePortalBlast();
	void UpdateBlastMeteors();
	void ExplodeBlastMeteor(const FVector& Location);
	void ExecuteStarLine();
	void StarLinePortals();
	// R 고리 방패: 몸 앞에 포털을 세우고, 끝에 앞쪽 적을 밀쳐낸다.
	void ExecuteRingWard();
	void ReleaseRingWard();
	void ExecuteSkyLance();
	void LaunchStarMeteor(const FVector& Target, float Damage, float Radius, float Scale, bool bStun);
	void UpdateStarMeteors(float DeltaTime);
	void ExplodeStarMeteor(const FStarMeteor& Meteor, const FVector& Point, AActor* Struck);
	void ExecuteVoidRay();
	// F 번개가 나가는 두 손 사이, 줄 위 첫 대상, 시전 중 다른 동작으로 갈아 끼우기(붙잡는 자세·마무리).
	FVector GetRayHands() const;
	AActor* FindRayTarget(const FVector& From, const FVector& To) const;
	// F 10·11이 고정할 한 대상, F 11(모았다가 번개 한 방).
	AActor* FindFocusTarget(const FVector& Cursor, const FVector& Feet, const FVector& End) const;
	void ExecuteFocusBolt(const FVector& Feet, const FVector& End, const FVector& Cursor, int32 Style);
	// A 자리 새 스킬 러프 시안(Gideon.Skills.ANew 2·3·5·6·7·8).
	void ExecuteNewSkillDraft(int32 Draft);
	FTimerHandle ADraftTimer;
	// A 도우미(시안 8): 부르기(손에서 나와 어깨 위로), 따라다니기·끝나면 사라지기, 평타마다 한 발 광선(Preferred = 스킬이 맞힌 대상),
	// 스킬이 맞힌 대상에게 한 발(간격 제한).
	void SummonHelper();
	void UpdateHelper();
	void HelperShoot(const FVector& Aim, AActor* Preferred = nullptr);
	void HelperAssist(AActor* Target);
	double HelperLastAssist = 0.0;
	FTimerHandle HelperTimer;
	TWeakObjectPtr<UParticleSystemComponent> HelperOrb;
	FVector HelperFrom = FVector::ZeroVector;
	FVector HelperAt = FVector::ZeroVector;
	double HelperStart = 0.0;
	double HelperEnd = 0.0;
	double HelperLastTick = 0.0;
	int32 HelperShots = 0;
	int32 HelperHits = 0;
	// A 시안 7 빛줄기: 층(심·빛무리 띠 / 넓은 번짐 띠 / 양 끝 빛덩이)을 처음 쓸 때 만들고 한 번 긋는다(From == To면 빛덩이만), 지운다.
	// CoreSharpness = 흰 심 날카로움(재질 기본 10, 가는 광선 시안에서 낮춤).
	void DrawSweepBeam(const FVector& From, const FVector& To, float Width, float Flare, float CoreSharpness = 10.0f);
	void ClearSweepBeam();
	// 대상 지정 스킬(S·A 시안 8)인지, 쓸 대상(커서 아래 대상, 없으면 커서 둘레 가장 가까운 것).
	bool RequiresTarget(EGideonSkill Skill) const;
	AActor* PickSkillTarget(AActor* Hovered, const FVector& Cursor) const;
	// 둥근 빛 점(D 유성 꼬리·F 11·V): 하나 남기기(Age = 이미 지난 시간), 소용돌이로 빨려 드는 것 하나, 날리며 줄이고 그리기.
	FGlowDot* AddGlowDot(const FVector& At, const FVector& Velocity, float Life, float Size, float Age = 0.0f);
	void AddSpiralDot(const FVector& Center, const FVector& Offset, float Swirl, float Life, float Size, float Pull = 2.0f);
	void UpdateGlowDots(float DeltaTime);
	void PlayCastMontage(UAnimSequence* Animation, int32 Loops, bool bKeepAsActive);
	// F 녹스 번개 그리기: 층(심·빛무리·곁가지 둘·불티) 준비, 한 번 긋기(PulsePhase = 노랑 굵기 0~1), 불티, 데스레이, 지우기.
	void PrepareNoxLayers(int32 Style);
	void DrawNoxBolt(const FVector& From, const FVector& To, float PulsePhase);
	void AddNoxSparks(const FVector& At, int32 Count);
	void EmitDeathRay(const FVector& From, const FVector& To);
	void UpdateNoxSparks(float DeltaTime);
	void ClearNoxBolt();
	// 시안용 도우미: 일정 시간 뒤 실행, 정해진 시간만 보이는 효과, 선분 근처 범위 피해.
	void After(float Seconds, TFunction<void()> Callback);
	UParticleSystemComponent* SpawnTimedEffect(UParticleSystem* Effect, const FVector& Location, const FRotator& Rotation, float Scale, float Seconds);
	int32 ApplyLineDamage(const FVector& Start, const FVector& End, float Width, float Damage, FName Status = NAME_None, float StatusSeconds = 0.0f);
	void ExecutePortalVolley();
	void FirePortalVolleyShot();
	void ExecuteCosmicRift();
	void CosmicRiftWave(int32 WaveIndex);
	// W 마법진(V 블랙홀도 빌려 쓴다). 한 번에 한 벌만 깔린다. Opacity = 반투명 칸 진하기(가산 칸은 제곱).
	void ShowRiftRunes(const FVector& Center, float Radius, float Opacity);
	void HideRiftRunes();
	// 룬 고리 모형 하나를 바닥에 깐다(투명도 사본 재질). W 마법진과 R 전조 고리가 쓴다.
	UStaticMeshComponent* SpawnRuneMesh(UStaticMesh* Mesh, const FVector& Location, const FRotator& Rotation, float Scale, float Opacity,
		const FLinearColor& Tint);
	void UpdateRiftRuneFade();
	void UpdateRiftRuneSpin(float DeltaTime);
	void UpdateBlackHoleShrink();
	// 줄 갱신·마법진(회전·사라짐)·블랙홀 접힘·운석 낙하 중 하나라도 진행 중일 때만 매 프레임 틱을 켠다.
	void RefreshTickEnabled();
	void ExecuteTornSpace();
	void CloseTornSpacePortal(UParticleSystemComponent* Portal, UParticleSystem* CloseEffect);
	void ExecuteBlackHole();
	void BlackHoleTick();
	void EndBlackHole(bool bCancelled);
	// V 일렁이는 빛 시안(Gideon.Skills.VGlow)을 블랙홀이 열릴 때 띄운다.
	void StartBlackHoleGlow();
	void RestoreBlackHoleTargets();
	void ApplyBurden(AActor* Target);
	void BurdenTick(TWeakObjectPtr<AActor> Target);
	void EndBurden(int32 Index, const TCHAR* Reason);
	USplineMeshComponent* SpawnBurdenTether();
	void UpdateBurdenTethers();
	bool IsBurdenTetherBroken(const AActor* Target) const;

	TWeakObjectPtr<ATopDownCombatCharacter> Character;
	TWeakObjectPtr<UAnimInstance> CastAnimInstance;
	UPROPERTY(Transient)
	TObjectPtr<UAnimMontage> ActiveMontage;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UParticleSystemComponent>> OwnedEffects;
	TArray<TWeakObjectPtr<AGideonProjectile>> OwnedProjectiles;
	TMap<EGideonSkill, double> CooldownEnds;
	TArray<FBurdenTarget> BurdenTargets;
	TArray<FBlastMeteor> BlastMeteors;
	TArray<FStarMeteor> StarMeteors;
	TArray<FNoxSpark> NoxSparks;
	TArray<FGlowDot> GlowDots;
	// D 그을음 자국: 마지막 큰 유성이 떨어지면 한꺼번에 사라지게 모아 둔다.
	TArray<TWeakObjectPtr<UDecalComponent>> StarScorches;
	int32 NoxStyle = 1;
	// 줄 조각을 카메라를 향한 판으로 놓는다(시안 6~9). 시안 9는 불티도 카메라를 향한 둥근 빛 판.
	bool bNoxStrips = false;
	bool bNoxSoftSparks = false;
	TArray<FBlackHoleTarget> BlackHoleTargets;
	TArray<FBlackHoleTarget> BlackHolePendingRestore;

	EGideonSkill ActiveSkill = EGideonSkill::PortalBlast;
	int32 ActiveSlot = INDEX_NONE;
	uint32 CastGeneration = 0;
	bool bCasting = false;
	bool bEnabled = false;
	bool bSavedOrientRotation = true;
	TEnumAsByte<ERootMotionMode::Type> SavedRootMotionMode = ERootMotionMode::RootMotionFromMontagesOnly;
	FVector ActiveAim = FVector::ZeroVector;
	FVector RiftCenter = FVector::ZeroVector;
	FVector BlackHoleCenter = FVector::ZeroVector;
	double BlackHoleEnd = 0.0;
	TWeakObjectPtr<UParticleSystemComponent> BlackHoleEffect;
	TWeakObjectPtr<UParticleSystemComponent> BlackHoleSealEffect;
	TWeakObjectPtr<UParticleSystemComponent> BlackHoleGlowEffect;
	TWeakObjectPtr<UParticleSystemComponent> RiftPortalEffect;
	TWeakObjectPtr<UParticleSystemComponent> RiftShowerEffect;
	TWeakObjectPtr<UParticleSystemComponent> EntrancePortal;
	TWeakObjectPtr<UParticleSystemComponent> ExitPortal;
	FString Feedback;
	double FeedbackDeadline = 0.0;
	FTimerHandle ActionTimer;
	FTimerHandle RecoveryTimer;
	FTimerHandle RiftTimer;
	FTimerHandle BlackHoleTimer;
	FTimerHandle BlackHoleRestoreTimer;
	// V: 봉인 마법진이 먼저 펼쳐진 뒤 블랙홀이 열리기까지.
	FTimerHandle BlackHoleIntroTimer;
	FTimerHandle VolleyTimer;
	FTimerHandle SkyTimer;
	// E: 포털을 늘어놓을 시작점·방향.
	FVector LineStart = FVector::ZeroVector;
	FVector LineDirection = FVector::ForwardVector;
	// R: 세워 둔 방패 포털과 정면(밀쳐낼 쪽).
	TWeakObjectPtr<UParticleSystemComponent> WardPortal;
	FVector WardForward = FVector::ForwardVector;
	int32 RiftWave = 0;
	// S 포털 위치(시전 순간에 고정)와 모아 쏠 한 점.
	TArray<FVector> VolleyPortals;
	FVector VolleyFocus = FVector::ZeroVector;
	int32 VolleyShot = 0;
	// 대상 지정 스킬(S·A 시안 8)이 시전 때 고른 대상.
	TWeakObjectPtr<AActor> ActiveTarget;

	// 원작 위키 근거: Cosmic Rift 반경 350·쿨 6초, Black Hole 3.5초. 나머지는 카운테스·스패로우 규모 임시값이다.
	static constexpr float RiftRadius = 350.0f;
	// 사용자 요청(10-17)으로 지속을 두 배로(3 → 6회, 마법진은 0.2초 ~ 약 2.8초).
	static constexpr int32 RiftWaves = 6;
	static constexpr float RiftWaveInterval = 0.4f;
	static constexpr float PortalBlastSplashRadius = 220.0f;
	// 원래 크기의 범위. 쓰는 곳에서 V 크기 BlackHoleSize(1.15 — 10-20 「1/3 더 키워」 → 「너무 과한가?」 → 권장값)를 곱한다.
	static constexpr float BlackHoleRadius = 450.0f;
	static constexpr float BlackHoleSeconds = 3.5f;
	static constexpr float BlackHoleTickSeconds = 0.5f;
	static constexpr float BlackHolePullSpeed = 160.0f;
	// 끌려간 허수아비를 블랙홀이 닫히는 순간 되돌리면 같이 사라져 보이므로 잠시 뒤에 돌린다.
	static constexpr float BlackHoleRestoreDelay = 1.5f;
	static constexpr float BlackHoleCloseOverlap = 0.3f;
	// 원작(2017-09 위키): 줄 4초 동안 8회 피해, 줄 사거리 1700, 멀어지거나 시야가 끊기면 일찍 끊긴다. 피해량만 임시값이다.
	static constexpr int32 BurdenTicks = 8;
	static constexpr float BurdenTickSeconds = 0.5f;
	static constexpr float BurdenTickDamage = 5.0f;
	static constexpr float BurdenTetherRange = 1700.0f;
	// 대상 몸에 붙는 지속 피해 표시 배율(쿼터뷰에서 작게 보여 키움).
	static constexpr float BurdenDotScale = 1.5f;
	// E 포털은 서 있는 고리라 바닥 높이에 두면 아래 절반이 바닥에 묻힌다. 몸 중심 높이로 띄운다.
	static constexpr float TornSpacePortalHeight = 100.0f;
	static constexpr float BasicAttackDamage = 20.0f;
	static constexpr float BasicAttackRange = 1400.0f;
	static constexpr float BasicAttackSpeed = 2600.0f;
	// 커서가 몸 중심에서 이보다 가까우면 방향이 흔들리므로 캐릭터가 보는 쪽으로 쏜다.
	static constexpr float BasicAttackMinAim = 120.0f;
	// 손→커서 방향이 몸→커서 방향과 이 각도(도)보다 어긋나면(몸 가까이 찍은 바닥) 몸 방향으로 쏜다.
	static constexpr float BasicAttackMaxSkew = 15.0f;

	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> PrimaryProjectile;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> PrimaryMuzzle;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> PrimaryHitCharacter;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> PrimaryHitWorld;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> PrimaryNoHit;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> BlastPortal;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> BlastProjectile;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> BlastHitWorld;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> BlastExplosion;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> RiftPortal;
	// 포털 속 룬 원은 0.3초만 보이고 밝은 바닥에선 묻힌다. 같은 룬 고리 모형을 균열 동안 바닥에 직접 깐다.
	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> RiftRuneOuter;
	// 균열 반경 테두리 겹원. 안쪽 겹원 모형을 키우면 딸린 삼각형 조각까지 커져 밖에 흩어지므로 조각을 잘라 낸 사본을 쓴다.
	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> RiftRuneBorder;
	// 룬 글자 고리 안쪽 가운데의 삼각 마법진(블랙홀용 모형, 바닥에 누운 모형). 사용자 선택 10-17(비교 사진 B안).
	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> RiftRuneCenter;
	// W 룬 원판(점선 고리 자리).
	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> RiftRuneDense;
	// 원본 룬 재질 이름 → Opacity 값을 더한 사본.
	UPROPERTY(Transient)
	TMap<FName, TObjectPtr<UMaterialInterface>> RiftRuneFadeMaterials;
	// D 유성(평타 빛 탄을 키운 것). 터짐은 평타 명중 빛·V 섬광을 같이 쓴다.
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> StarTrail;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> SkyStunned;
	// Q 하늘 포털(줄기 가닥을 숨긴 사본), V 시작 봉인 마법진.
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> SkyPortal;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> SealCircle;
	// F 붙잡는 자세·마무리 동작, 녹스 번개 줄 조각(원통)·불티(공)·빛 재질과 층(인스턴스 메시). V 끝 섬광·보라 돔·푸른 충격 고리.
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> RayHold;
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> RayOutro;
	// A 시안 7 빛줄기: 두 손을 모아 앞으로 뻗는 동작(옛 F 광선 동작)의 들어가기·붙잡기·내리기, 빛줄기 재질과 층.
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> SweepIntro;
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> SweepHold;
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> SweepOutro;
	// A 한 발 광선 동작(평타 1타).
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> RayShotAnim;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> SweepBeamMaterial;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UInstancedStaticMeshComponent>> SweepLayers;
	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> NoxSegmentMesh;
	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> NoxSparkMesh;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> NoxBoltMaterial;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UInstancedStaticMeshComponent>> NoxLayers;
	UPROPERTY(Transient)
	TObjectPtr<UInstancedStaticMeshComponent> GlowDotLayer;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> StarScorchMaterial;
	// D 바닥 자국 시안 2·3: 룬 무늬, 별 무늬(같은 짜임, 무늬만 다름).
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> StarRuneMaterial;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> StarAstroMaterial;
	// F 시안 12~15: Prime Helix 보라 모음, 콰앙 빛 강타, Dekker 정지폭탄 충격파, Dekker 하늘 빔 첫 터짐.
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> FocusGather;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> FocusLightStrike;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> FocusShockwave;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> FocusStarBurst;
	// F 파라곤 시안: 콰앙 번개 광선·전기 불꽃, 띠(판) 모형, 방전·번개 재질 사본.
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> RayBolt;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> RayArc;
	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> NoxStripMesh;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> NoxDischargeMaterial;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> NoxBoltStripMaterial;
	// F 시안 9: 부드러운 빛 띠·둥근 불티 재질.
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> NoxGlowStripMaterial;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> NoxSoftSparkMaterial;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> AnnihilateFlash;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> AnnihilateRing;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> WardPop;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> OriginalBolt;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> BlackHoleGlow;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> RiftRunes;
	// 마법진이 줄어들며 사라질 때 기준이 되는 원래 배율(RiftRunes와 같은 순서)과 사라지기 시작한 시각(-1 = 사라지는 중 아님).
	TArray<float> RiftRuneScales;
	// 층마다 도는 속도(도/초, RiftRunes와 같은 순서). 이웃한 층은 반대로 돈다.
	TArray<float> RiftRuneSpins;
	double RiftRuneFadeStart = -1.0;
	// 줄어들며 사라지는 데 걸리는 시간(W는 짧게, V는 블랙홀이 접히는 시간에 맞춘다).
	float RiftRuneFadeLength = 0.25f;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> RiftShower;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> RiftBlast;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> RiftImpact;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> PortalEntrance;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> PortalExit;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> PortalEntranceClose;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> PortalExitClose;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> TeleportEnter;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> TeleportExit;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> BlackHole;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> BlackHoleCancelled;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> BurdenProjectile;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> BurdenMuzzle;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> BurdenHitCharacter;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> BurdenNoHit;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> BurdenDot;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> BurdenDotEnd;
	// 팩에 줄 입자 이펙트는 없지만 원작 줄 모형(SM_Burden_Spline, 재질 M_Burden_Tether)이 남아 있어 늘여 붙인다.
	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> BurdenTetherMesh;
};
