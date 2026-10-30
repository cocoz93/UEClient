#pragma once

#include "CoreMinimal.h"
#include "CharacterSkillComponent.h"
#include "AuroraSkillComponent.generated.h"

class ATopDownCombatCharacter;
class UAnimMontage;
class UAnimSequence;
class UDecalComponent;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class UMeshComponent;
class UParticleSystem;
class UParticleSystemComponent;
class USkeletalMeshComponent;
class UStaticMesh;
class UStaticMeshComponent;
class UPointLightComponent;
class UPoseableMeshComponent;
class UTexture;

// HUD 칸 번호 그대로다(CharacterSkillHUD의 18칸 배열). W E = 1·2, A S D F = 8..11은 원작에 없는 추가 스킬,
// V = 16 궁극기, Space = 17 이동기. 사용자 요청(2026-10-18)으로 R 궁극기는 V, Q 도약은 Space로 옮기고,
// 빈 Q·R 칸과 다시 짠 A에 새 스킬(서리 검기·냉기 장판·얼음 갑옷)을 넣었다.
// 10-21 「W를 Space 스킬로 교체 — Space(도약)는 W로 옮긴 뒤 대상 지정형으로」: 돌진이 Space(17), 도약이 W(1).
UENUM(BlueprintType)
enum class EAuroraSkill : uint8
{
	FrostSlash = 0,
	FrozenSimulacrum = 1,
	Hoarfrost = 2,
	FrostField = 3,
	IceArmor = 8,
	FrostHaste = 9,
	// 10-26 「궁극기를 일반 스킬로 빼고」 → 옛 궁극기가 D(그 전 D 얼음 파열·고드름 비 자리)로
	Cryoseism = 10,
	IceLance = 11,
	// 새 궁극기 눈보라(같은 날 「궁극기는 마법사 캐릭터처럼 광역기로 — 계속 블리자드처럼 얼음송곳이 쏟아지는 느낌」)
	Blizzard = 16,
	GlacialCharge = 17
};

USTRUCT()
struct FAuroraSkillDefinition
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
	// 동작 재생 배율. 시점(ActionTime·RecoveryTime)은 이 배율을 적용한 실제 시간이다.
	UPROPERTY(EditAnywhere, meta = (ClampMin = "0.1"))
	float PlayRate = 1.0f;
};

// 날고 있는 얼음 창(F) 하나: 칼날 메시·꼬리 빛·나는 방향·간 거리. 한 번에 LanceCount개가 부채꼴로 난다.
struct FAuroraLance
{
	TWeakObjectPtr<UStaticMeshComponent> Mesh;
	TWeakObjectPtr<UParticleSystemComponent> Trail;
	// 분신 돌격(Aurora.FX.FClone): 칼날 대신 바닥을 달리는 얼음 분신(칼날은 숨겨 나는 길·맞힘 판정만 쓴다)
	TWeakObjectPtr<USkeletalMeshComponent> Clone;
	// 얼음 새 시안(Aurora.FX.FBird, 헤더 LanceBirdHeight 설명): 1 그림 매 = 판 하나 · 2 결정 매 = 몸·오른 날개·왼 날개·꼬리.
	// 날기 시작한 때 · 날갯짓 박자 어긋남(셋이 같이 퍼덕이지 않게)
	int32 Bird = 0;
	TArray<TWeakObjectPtr<UStaticMeshComponent>> BirdParts;
	TWeakObjectPtr<UMaterialInstanceDynamic> BirdMaterial;
	double BirdBorn = 0.0;
	float BirdPhase = 0.0f;
	// 매 퀄리티 시안(Aurora.FX.FLook 비트, AuroraSkillComponentFDrafts.cpp 설명) — 던질 때 정한다 · 2의 눈송이 꼬리
	int32 BirdLook = 0;
	TWeakObjectPtr<UParticleSystemComponent> BirdFlakes;
	// 나는 쪽 이펙트 시안(Aurora.FX.FTrail 비트): 빛줄기 판(0 몸 뒤 · 1·2 오른·왼 날개 끝)과 그 재질 · 얼음 반짝이
	TWeakObjectPtr<UStaticMeshComponent> BirdStreaks[3];
	TWeakObjectPtr<UMaterialInstanceDynamic> BirdStreakMaterials[3];
	TWeakObjectPtr<UParticleSystemComponent> BirdSparks;
	// 등장 이펙트 시안(Aurora.FX.FSummon) — 4는 매가 짙어지며 커지는 동안 LanceBirdTick이 재질을 만진다
	int32 BirdSummon = 0;
	FVector Direction = FVector::ForwardVector;
	float Travel = 0.0f;
	// 나는 동안 꼬리 시안(Aurora.FX.FFlight)의 다음 잔상 · 다음 부스러기를 남길 때
	double NextTrail = 0.0;
	double NextShed = 0.0;
};

// F 나는 꼬리 시안 2: 창이 지나간 자리에 남아 가늘어지며 사라지는 잔상 하나(창과 같은 메시·자세): 남긴 때·처음 크기.
// 87차 F 얼음 덩어리 입체 시안(Aurora.FX.FChunk, AuroraSkillComponentPolish.cpp): 등 뒤에 떠 있다가 대상에게 날아가는 얼음 메시 하나 —
// 생긴 때 · 쏜 때(-1 = 아직) · 날아가는 시간 · 떠 있는 자리 · 날아갈 출발·도착 · 흔들림 박자 · 도는 축 · 크기 · 안 쏘이면 치울 때
struct FAuroraChunkMesh
{
	TWeakObjectPtr<UStaticMeshComponent> Mesh;
	// 94차 FChunk 4·5 얼음 검: 숨긴 메시(Mesh — 자리·방향을 나르는 몸)에 붙인 오로라 검 사본(칼만 보이는 캐릭터 메시 자세 사본)
	TWeakObjectPtr<USceneComponent> Sword;
	TWeakObjectPtr<UParticleSystemComponent> Trail;
	double Born = 0.0;
	double FiredAt = -1.0;
	double Deadline = 0.0;
	float Flight = 0.0f;
	FVector Spot = FVector::ZeroVector;
	FVector From = FVector::ZeroVector;
	FVector Goal = FVector::ZeroVector;
	float Phase = 0.0f;
	FVector SpinAxis = FVector::UpVector;
	float Scale = 1.0f;
};

struct FAuroraLanceGhost
{
	TWeakObjectPtr<UStaticMeshComponent> Mesh;
	double Born = 0.0;
	FVector Scale = FVector::OneVector;
	// 사라지는 데 걸리는 시간(0 = LanceGhostSeconds) — 매 잔상(FLook 1)은 더 오래 남는다
	float Seconds = 0.0f;
};

// Q 검기 날에서 날려 나가는 눈송이 하나(판 메시): 출발 자리·처음 속도·흔들리는 쪽·나타나는 때·사는 시간·크기·흔들림·돎.
struct FAuroraFlake
{
	TWeakObjectPtr<UStaticMeshComponent> Mesh;
	FVector Start = FVector::ZeroVector;
	FVector Velocity = FVector::ZeroVector;
	FVector Sway = FVector::ZeroVector;
	double Born = 0.0;
	float Life = 1.0f;
	float Size = 8.0f;
	float SwayRate = 2.0f;
	float SwayPhase = 0.0f;
	float Spin = 0.0f;
	float SpinRate = 0.0f;
};

// Q 검기 날에서 튀어 나가는 얼음 파편 하나(엔진 원뿔 + 얼음 석상 재질): 출발 자리·처음 속도·나타나는 때·사는 시간·
// 바닥 높이·크기(옆 너비·두께·길이 cm)·도는 축과 빠르기. 무겁게 떨어져 바닥에 닿으면 미끄러지다 멈춘다.
struct FAuroraShard
{
	TWeakObjectPtr<UStaticMeshComponent> Mesh;
	FVector Start = FVector::ZeroVector;
	FVector Velocity = FVector::ZeroVector;
	double Born = 0.0;
	float Life = 1.0f;
	float FloorZ = 0.0f;
	FVector Size = FVector(10.0f, 5.0f, 30.0f);
	FQuat Facing = FQuat::Identity;
	FVector SpinAxis = FVector::UpVector;
	float SpinRate = 0.0f;
};

// D 얼음 파열 시안 1·3: 바닥을 뚫고 솟았다가 도로 들어가는 얼음 가시 하나(엔진 원뿔 + 얼음 석상 재질). 뿌리 자리·솟는 축·
// 크기(밑동 너비·높이 cm)·솟는 때·사는 시간.
struct FAuroraRuptureSpike
{
	TWeakObjectPtr<UStaticMeshComponent> Mesh;
	FVector Base = FVector::ZeroVector;
	FQuat Facing = FQuat::Identity;
	float Width = 30.0f;
	float Height = 100.0f;
	double Born = 0.0;
	float Life = 0.8f;
};

// D 고드름 비의 고드름 하나(팩 메시 SM_Aurora_Spike_Single): 하늘에서 Landing으로 대각선(IcicleFall)으로 떨어져 박힌 뒤 StuckUntil에 부서진다.
struct FAuroraIcicle
{
	TWeakObjectPtr<UStaticMeshComponent> Mesh;
	FVector Landing = FVector::ZeroVector;
	double Born = 0.0;
	double StuckUntil = 0.0;
	bool bLanded = false;
	// 창마다 길이·굵기 배율(모두 같은 막대로 보이지 않게)
	float Length = 1.0f;
	float Width = 1.0f;
	TWeakObjectPtr<UParticleSystemComponent> Trail;
};

// D 새 시안(Aurora.FX.DFresh, AuroraSkillComponentDFresh.cpp)의 빛 조각 하나: 엔진 판에 빛 그림(M_Aurora_FxAdd 사본)을 붙여 때에 맞춰
// 옮기고 키우고 흐린다. Born이 앞날이면 그때까지 숨는다.
struct FAuroraDPiece
{
	TWeakObjectPtr<UStaticMeshComponent> Mesh;
	TWeakObjectPtr<UMaterialInstanceDynamic> Material;
	double Born = 0.0;
	float Life = 0.3f;
	// 0 바닥에 눕힘 · 1 카메라를 봄 · 2 그림 위쪽(머리)이 Axis를 따르고 판은 카메라 쪽으로 돌림(머리 자리가 From·To) ·
	// 3 화면에 붙음(카메라 앞 Lift만큼, 판 가로 = 화면 가로 — V 눈보라의 눈 겹·어둡게, From·To는 안 씀)
	uint8 Face = 0;
	FVector Axis = FVector(0.0f, 0.0f, -1.0f);
	// MoveSeconds 동안 From → To(MoveEase 0 그대로 · 1 점점 빠르게 · 2 점점 느리게)
	FVector From = FVector::ZeroVector;
	FVector To = FVector::ZeroVector;
	float MoveSeconds = 0.0f;
	uint8 MoveEase = 0;
	// 크기(가로 · 세로 cm): GrowDelay 뒤 GrowSeconds 동안 SizeFrom → SizeTo(GrowEase는 MoveEase와 같은 뜻)
	FVector2D SizeFrom = FVector2D(100.0f, 100.0f);
	FVector2D SizeTo = FVector2D(100.0f, 100.0f);
	float GrowDelay = 0.0f;
	float GrowSeconds = 0.0f;
	uint8 GrowEase = 2;
	float FadeIn = 0.0f;
	float FadeOut = 0.1f;
	float Strength = 1.0f;
	// 퍼진 빛(R) · 흰 심(G) 밝기 — 음수면 재질 기본값(빛 결정은 흰 심이 세면 하얀 종이처럼 보인다)
	float Glow = -1.0f;
	float CoreGlow = -1.0f;
	// 판 돌림(도, Face 0·1) · 초당 돌림 · 위아래 흔들림(cm · 초당 번 · 시작 위상) · 카메라 쪽으로 당기는 거리(바닥에 반쯤 묻히지 않게)
	float Spin = 0.0f;
	float SpinRate = 0.0f;
	float Bob = 0.0f;
	float BobRate = 0.0f;
	float BobPhase = 0.0f;
	float Lift = 0.0f;
	// OrbitRadius > 0이면 From·To 대신 OrbitCenter 둘레를 돈다(각 = OrbitAngle + OrbitRate × 나이, 라디안)
	FVector OrbitCenter = FVector::ZeroVector;
	float OrbitRadius = 0.0f;
	float OrbitAngle = 0.0f;
	float OrbitRate = 0.0f;
	// bAim이면 Axis 대신 머리가 늘 AimPoint를 본다(Face 2)
	bool bAim = false;
	FVector AimPoint = FVector::ZeroVector;
	// 퍼진 빛 색(A가 0이면 재질 기본값)
	FLinearColor Tint = FLinearColor(0.0f, 0.0f, 0.0f, 0.0f);
	// 반투명 그리는 차례(클수록 위) — 화면을 어둡게 하는 판 아래에 빛 조각, 그 위에 눈 겹
	int32 SortPriority = 0;
	// 바탕 재질 사본에 더 넣을 값(흐르는 눈의 Tiling·SpeedX·SpeedY 같은 것)
	TArray<TPair<FName, float>> Scalars;
};

// D 새 시안의 번쩍이는 빛 하나(Life 동안 Peak에서 제곱으로 꺼짐)
struct FAuroraDLight
{
	TWeakObjectPtr<UPointLightComponent> Light;
	double Born = 0.0;
	float Life = 0.2f;
	float Peak = 0.0f;
};

// Q1 날아가는 검기 하나(엔진 판 + M_Aurora_WaveBlade 사본): 떠난 발밑·나는 쪽·떠난 때. 가는 거리·폭·흐려짐은 WaveTick이 때로 정한다.
// 얼음 검기(QStyle 6)는 초승달 날을 따라 바깥으로 솟은 얼음 조각(Crest — 날 위 각도·길이 배율)을 같이 싣고, 옆으로 기운 쪽(Roll 부호)이
// 칼 방향을 따르며, NextShed마다 얼음 부스러기를 떨군다.
struct FAuroraWave
{
	TWeakObjectPtr<UStaticMeshComponent> Mesh;
	TWeakObjectPtr<UMaterialInstanceDynamic> Material;
	FVector Feet = FVector::ZeroVector;
	FVector Direction = FVector::ForwardVector;
	double Born = 0.0;
	float Roll = 1.0f;
	// 화면 기울기(Aurora.FX.QTilt) — 쏠 때 카메라가 보는 쪽(0이면 나는 쪽 축으로 QWaveRoll만) · 기울 각(도, 부호 포함)
	FVector ViewAxis = FVector::ZeroVector;
	float Tilt = 0.0f;
	TArray<TWeakObjectPtr<UStaticMeshComponent>> Crest;
	TArray<FVector2D> CrestShape;
	double NextShed = 0.0;
	// Q 검기 시안(Aurora.FX.QWave, 10-20 「Q도 시안 — 필요하면 조합해서」): 1 Yin 바람 줄기 메시를 같이 싣고 · 2 Yin 채찍 잔상을
	// 날 꼭대기에 띄워 끌고 · 4 같은 초승달 둘을 뒤에 겹쳐 따라오게(겹 검기)
	TWeakObjectPtr<UStaticMeshComponent> Spline;
	TWeakObjectPtr<UParticleSystemComponent> Afterimage;
	TArray<TWeakObjectPtr<UStaticMeshComponent>> Echoes;
	TArray<TWeakObjectPtr<UMaterialInstanceDynamic>> EchoMaterials;
	// 얼음 검기인지(얼음 조각을 빼는 시안 QBlade 8에서도 폭·부스러기는 얼음 검기대로) · 시안 QBlade 4의 따라가는 푸른 빛
	bool bIce = false;
	TWeakObjectPtr<UPointLightComponent> Light;
	// 시안 Aurora.FX.QFeel 비트 · 골격 시안 Aurora.FX.QShape(0 = 지금) · 골격 2 얼음 덩어리마다 제 자세(Crest와 같은 차례)
	int32 Feel = 0;
	int32 Shape = 0;
	TArray<FQuat> CrestSpin;
	// 이펙트 시안 Aurora.FX.QSkin 비트 · 긴 잔광(가는 날 선 사본을 Echoes로) · 얼음 결정 크기(검기 폭 300일 때 cm, 0 = 원뿔) ·
	// 1 빛무리 판
	int32 Skin = 0;
	bool bAfterglow = false;
	float ChunkSize = 0.0f;
	TWeakObjectPtr<UStaticMeshComponent> Aura;
	TWeakObjectPtr<UMaterialInstanceDynamic> AuraMaterial;
	// 빛무리 판 크기(검기 판 대비, 0 = QSkinAuraScale) — 94차 팩 칼 궤적 겹(QSlash 8·9)은 1
	float AuraScale = 0.0f;
	// 나는 거리·시간·폭(처음 → 끝)·높이(QBlade 16 큰 검기면 커진 값) · 32 잔상 줄기(Echoes를 촘촘히) · 64 파편 강화
	float Reach = 420.0f;
	float Seconds = 0.3f;
	float StartWidth = 150.0f;
	float EndWidth = 300.0f;
	float Height = 65.0f;
	bool bSmear = false;
	bool bHeavy = false;
	// 시안 QBig 4: 다 날아간 자리에서 산산조각 — 마지막 장면의 판 가운데·자세·반폭을 적어 둔다
	bool bShatter = false;
	FVector LastCenter = FVector::ZeroVector;
	FQuat LastRolled = FQuat::Identity;
	float LastHalf = 0.0f;
};

// V 착지 시안 5·7·8(Aurora.FX.VLand): 바깥으로 퍼지는 서리 충격파 고리 하나(엔진 판 + M_Aurora_NovaRing 사본) — 퍼지기 시작하는 때 ·
// 다 퍼진 반경 · 진하기
struct FAuroraNovaRing
{
	TWeakObjectPtr<UStaticMeshComponent> Mesh;
	TWeakObjectPtr<UMaterialInstanceDynamic> Material;
	double Born = 0.0;
	float MaxRadius = 500.0f;
	float Strength = 1.0f;
	// 다 퍼지는 시간(시안 VNova 2는 더 빠르게)
	float Seconds = 0.25f;
};

// V 착지 시안 3(Aurora.FX.VLand): 하늘에서 내리꽂히는 얼음 창 하나 — 떨어지기 시작하는 자리·꽂히는 자리·떨어지기 시작하는 때.
struct FAuroraFallingSpear
{
	TWeakObjectPtr<UStaticMeshComponent> Mesh;
	FVector From = FVector::ZeroVector;
	FVector To = FVector::ZeroVector;
	double Born = 0.0;
	bool bLanded = false;
};

// Q2 공중 칼자국 하나(엔진 판 + M_Aurora_CutMark 사본, 카메라를 봄): 그어진 때 · 깨지는 때(0 = 아직)
struct FAuroraCutMark
{
	TWeakObjectPtr<UStaticMeshComponent> Mesh;
	TWeakObjectPtr<UMaterialInstanceDynamic> Material;
	double Born = 0.0;
	double ShatterAt = 0.0;
};


// R 회오리(Aurora.FX.RField 1)에서 도는 얼음 파편 하나(엔진 원뿔 + 얼음 석상 재질): 도는 각(도) · 안팎 자리(0 안 ~ 1 바깥) ·
// 높이(0 바닥 ~ 1 꼭대기) · 도는 빠르기 배율 · 크기(옆 너비·두께·길이 cm) · 나타난 때 · 스스로 도는 빠르기
struct FAuroraVortexShard
{
	TWeakObjectPtr<UStaticMeshComponent> Mesh;
	float Angle = 0.0f;
	float Reach = 0.5f;
	float Rise = 0.5f;
	float Pace = 1.0f;
	FVector Size = FVector(10.0f, 6.0f, 30.0f);
	double Born = 0.0;
	float SpinRate = 0.0f;
};

// E 시안 4: 회오리로 묶은 대상 하나를 얼음 석상 재질로 바꿔 둔 기록. 풀 때 메시마다 칸 수만큼 이어 붙인 원래 재질로 되돌린다
// (Originals를 붙잡아 실행 중 만든 재질 사본도 지워지지 않게 한다). 묶는 동안 다시 맞으면 EndsAt만 늦춘다.
USTRUCT()
struct FAuroraEncased
{
	GENERATED_BODY()

	TWeakObjectPtr<AActor> Target;
	TArray<TWeakObjectPtr<UMeshComponent>> Meshes;
	TArray<int32> SlotCounts;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInterface>> Originals;
	double EndsAt = 0.0;
};

// Aurora 원본 스킬 넷(Frozen Simulacrum·Glacial Charge·Hoarfrost·Cryoseism)과 근접 평타 판정을 소유한다.
// 원본 애니 BP에는 상체 슬롯뿐이라, 스킬 동작은 애니 BP 사본에 넣은 전신 슬롯에서 재생한다(PlayFullBody).
UCLASS(ClassGroup = (Combat), meta = (BlueprintSpawnableComponent))
class LEARNTOPDOWN_API UAuroraSkillComponent : public UCharacterSkillComponent
{
	GENERATED_BODY()

public:
	UAuroraSkillComponent();
	virtual bool TryUseSkillSlot(int32 Slot, const FVector& AimLocation, AActor* Target) override;
	virtual bool IsCasting() const override { return bCasting; }
	virtual bool IsEnabled() const override { return bEnabled; }
	virtual int32 GetActiveSkillNumber() const override { return bCasting ? ActiveSlot + 1 : 0; }
	virtual int32 GetSkillCount() const override { return SlotCount; }
	virtual FText GetSkillDisplayName(int32 Slot) const override;
	virtual ECharacterSkillTargeting GetSkillTargeting(int32 Slot) const override;
	virtual bool IsSkillTargetValid(int32 Slot, const AActor* Target, const AActor* Caster) const override;
	virtual float GetSlotCooldownRemaining(int32 Slot) const override;
	virtual FString GetInputFeedback() const override;
	virtual bool IgnoresCooldowns() const override;
	virtual void CancelSkill() override;
	// 스킬이 QWER·ASDF 글자 키뿐이라 HUD 왼쪽 묶음에 모으고, 오른쪽 윗줄 앞 두 칸에 V·Space를 그린다(Gideon과 같은 배치).
	virtual bool PlacesLetterKeysOnLeftHud() const override { return true; }

	// 얼음 갑옷(A)이 켜져 있으면 받는 피해 배율(1보다 작음). 캐릭터의 TakeDamage가 쓴다.
	float GetIncomingDamageScale() const;

	// 평타 한 타. 앞쪽 부채꼴 안의 대상을 베고 맞은 자리에 타격 이펙트를 띄운다.
	int32 ExecuteMeleeHit(float Range, float HalfAngle, float Damage, int32 ComboStep);

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	UPROPERTY(EditDefaultsOnly, Category = "Skills")
	TMap<EAuroraSkill, FAuroraSkillDefinition> Skills;

private:
	static constexpr int32 SlotCount = 18;

	const FAuroraSkillDefinition* FindSkill(int32 Slot) const;
	bool RejectInput(const TCHAR* Reason);
	bool ClampGroundTarget(const FVector& Aim, float Range, bool bRequireNavigation, FVector& Result) const;
	bool BeginCast(EAuroraSkill Skill, const FVector& Aim);
	// 시전 시작 공통: 평타·이동을 멈추고 겨눈 쪽을 보고 시전 상태로 둔다(BeginCast·BeginFrostCross).
	void PrepareCast(EAuroraSkill Skill, const FVector& Aim);
	void ExecuteAction(uint32 Generation);
	void FinishCast();
	void StartCooldown(EAuroraSkill Skill);
	FVector GetFeetLocation() const;
	UParticleSystemComponent* SpawnOwnedEffect(UParticleSystem* Effect, const FVector& Location, const FRotator& Rotation = FRotator::ZeroRotator);
	void ReleaseOwnedEffect(UParticleSystemComponent* Effect);
	// 위에서 비추는 둥근 바닥 데칼(반경 Radius)을 Seconds 동안 깐다. 나타남·사라짐은 FadeIn·FadeOut초.
	// Width를 주면 그림 가로(옆) 반폭만 따로(세로 = 그림 위아래 반길이는 Radius).
	UDecalComponent* SpawnFloorDecal(UMaterialInterface* Material, const FVector& Center, float Radius, float Seconds, float FadeIn,
		float FadeOut, float Width = -1.0f);
	// 바닥 무늬(M_Aurora_SlashArc 등, B = 드러나는 차례)를 그림 위쪽이 Facing을 보게 깔고 SweepSeconds 동안 B 순서로 드러낸다.
	// FadeOut을 주지 않으면 남는 시간의 절반 동안 사라진다.
	UDecalComponent* SweepFloorDecal(UMaterialInterface* Material, const FVector& Center, const FVector& Facing, float Radius,
		float Seconds, float SweepSeconds, float Width = -1.0f, float FadeOut = -1.0f);
	// 재질 사본의 Reveal을 0에서 1.1까지 SweepSeconds 동안 Steps번에 나눠 올린다(1을 조금 넘겨 끝자락까지 다 보이게).
	void RampReveal(UMaterialInstanceDynamic* Dynamic, float SweepSeconds, int32 Steps = 8);
	// Q 칼 궤적을 따라 바닥 자국(시안 Aurora.FX.QGround)을 차례로 깐다.
	void SpawnSlashGround(const FVector& Feet, const FVector& Direction, float Range);
	// Q 검기 날에서 눈송이 Count개를 날려 보내고(크기 Size cm · 출발 자리 = 베는 거리의 Reach배 · 사는 시간 Life초, 각각 최소~최대),
	// FlakeTick이 매 장면 움직인다.
	void SpawnSlashFlakes(const FVector& Feet, const FVector& Direction, float Range, int32 Count, FVector2D Size, FVector2D Reach,
		FVector2D Life);
	void FlakeTick();
	// Q 시안 3·4(여전사풍): 검기 날에서 얼음 파편 SlashShardCount개를 바깥·칼이 지나가는 쪽으로 세게 튕겨 보내고 ShardTick이 움직인다.
	void SpawnSlashShards(const FVector& Feet, const FVector& Direction, float Range);
	// F 시안 2·3: 칼날이 꽂힌 자리(Where)에서 얼음 파편 LanceShardCount개를 나는 쪽(Direction) 부채꼴로 튕겨 보낸다(바닥 높이 FloorZ).
	void SpawnImpactShards(const FVector& Where, const FVector& Direction, float FloorZ);
	// 얼음이 깨지며 파편 Count개가 사방으로 튄다(발 Feet, 높이 Height 안 곳곳에서 · 바깥·위 빠르기 · 크기 배율). E 석상 · R 회오리.
	void SpawnShatterShards(const FVector& Feet, float Height, int32 Count, float Speed, float UpSpeed, float SizeScale = 1.0f);
	// 파편 하나의 메시를 띄워 ShardTick 목록에 넣는다(Q·F·E 공용).
	// Material = 파편 재질(없으면 얼음 분신 석상 재질)
	void AddShard(FAuroraShard Shard, double Now, UMaterialInterface* Material = nullptr);
	void ShardTick();
	// D 시안 1·3: 줄 위 한 자리(Spot)에서 얼음 가시 RuptureSpikesPerStep개가 솟고 RuptureSpikeTick이 움직인다.
	void SpawnRuptureSpikes(const FVector& Spot, const FVector& Direction);
	void RuptureSpikeTick();
	// From 바로 아래 바닥 높이(못 찾으면 Fallback)
	float FindFloorZ(const FVector& From, float Fallback) const;
	// Seconds 뒤 이펙트를 남은 입자째 바로 지운다(끄기와 달리 떠 있던 조각이 남지 않는다).
	void DestroyEffectLater(UParticleSystemComponent* Effect, float Seconds);
	// 한 번 터지고 끝나는 이펙트를 Delay 뒤 크기 Scale로 띄운다(0이면 바로). 여러 겹·물결 연출용.
	void SpawnBurstLater(UParticleSystem* Effect, const FVector& Location, float Scale, float Delay, const FRotator& Rotation = FRotator::ZeroRotator);
	int32 ApplyAreaDamage(const FVector& Center, float Radius, float Damage, FName Status = NAME_None, float StatusSeconds = 0.0f,
		TArray<AActor*>* OutTargets = nullptr);
	void GatherTargets(const FVector& Center, float Radius, TArray<AActor*>& Out) const;
	// 대상에 붙인 이펙트를 Seconds 뒤 풀고, 그 자리에 끝 이펙트를 띄운다.
	void AttachTimedEffect(UParticleSystem* Effect, AActor* Target, float Seconds, UParticleSystem* EndEffect = nullptr);
	void ReleaseLater(UParticleSystemComponent* Effect, float Seconds, UParticleSystem* EndEffect = nullptr);
	// 충돌 없는 얼음 메시를 세상에 Seconds 동안 세워 두고, 치울 때 그 자리에 끝 이펙트를 띄운다.
	UStaticMeshComponent* SpawnTimedMesh(UStaticMesh* Mesh, const FTransform& Transform, float Seconds, UParticleSystem* EndEffect = nullptr);
	void RemoveTimedMesh(UStaticMeshComponent* Component, UParticleSystem* EndEffect);
	FTimerHandle& AddReleaseTimer();

	void ExecuteHoarfrost();
	bool PlanGlacialCharge(const FVector& Aim, FVector& OutEnd) const;
	void ExecuteGlacialCharge();
	void GlacialChargeTick();
	void EndGlacialCharge(bool bCancelled);
	// 나와 대상(없으면 나만)을 Seconds 동안 거의 멈춘다(역경직). 그동안 돌진·시전 끝 예약도 멈춘다.
	// 돌진이 처음 맞힌 순간(ChargeHitStopSeconds), D 칼끝이 바닥에 닿는 순간(SpikePlantHitStopSeconds).
	void BeginHitStop(AActor* Target, float Seconds);
	void EndHitStop();
	// 돌진 뒤 멈춰 있는 시간: 원작 돌진 자세(WRun 2)는 짧게 버티고, 달리기 시안(0·1)은 미끄러져 멈추는 동작 길이.
	float GetChargeStopSeconds() const;
	void ShoveBack(AActor* Target, const FVector& PathDirection);
	// Seconds가 0이면 허수아비를 그 자리로 옮기고, 아니면 그동안 미끄러뜨린다(ShoveSlideTick)
	void PushTarget(AActor* Target, const FVector& Direction, float Distance, float Seconds = 0.0f);
	void ShoveSlideTick();
	void RestoreShoved();
	void SpawnDecoy();
	void ExplodeDecoy();
	// 87차 마감 재작업(AuroraSkillComponentPolish.cpp, 10-28 「E, D 빼고 다 아쉽다」 → 고르기 페이지 답). 콘솔 값 0이면 그 전 모습.
	// W 남는 얼음 분신을 돌진 직전 자세의 캐릭터 사본으로(Aurora.FX.WPose) — 만들었으면 true
	bool SpawnDecoyPose(const FVector& Feet, float Yaw);
	// Space-2: 길에 얼음 조각 · 도착 자리 결정 파열 + 섬광(Aurora.FX.SpaceLook)
	int32 GetSpaceLook() const;
	void SpaceFragment(const FVector& Spot, const FVector& Direction);
	void SpaceArrival(const FVector& Feet, const FVector& Direction);
	// R-2: 난무 시작에 대상 둘레 감옥 → 난무 끝에 감옥째 크게 터짐(Aurora.FX.RPrison — 93차부터 2 냉기 회오리 · 3 떠서 도는 결정 · 1 고드름)
	void BeginRPrison(const FVector& Center, float BreakAfter, AActor* Target = nullptr);
	void BreakRPrison();
	// 93차 D 「오브젝트 얼음 생기는 거 너무 별론데 아예 빼든가 다른 오브젝트 이펙트」(Aurora.FX.DShard): 착지·얼음 터짐 때 바닥에 흩어지던 빛나는
	// 얼음 조각(SpawnIceBurst) 대신 — 0 그 조각 그대로 · 1 없음 · 2 팩 결정 파열(남는 것 없음). bEcho = 얼린 대상마다 터질 때
	void SpawnCryoShards(const FVector& Center, int32 Count, bool bHeavy, float Reach, bool bEcho);
	// 93차 「분신 주변 얼음 오브젝트는 다른 이펙트 없나」: RPrison 3 = 대상 둘레를 떠서 도는 얼음 결정(PrisonOrbTick이 돌리고, 터질 때 바깥으로 흩어짐)
	void PrisonOrbTick();
	void ClearPrisonOrbs();
	// 94차 R 감옥 시안 4·5에 쓰는 대상(BeginRPrison이 받음)
	TWeakObjectPtr<AActor> PrisonTarget;
	// Q-2 · F-1: 맞은 자리 결정 파열(Aurora.FX.QBurst · FBurst) — 바닥 높이에
	bool UseQBurst() const;
	bool UseFBurst() const;
	// Q 검기 자체(Aurora.FX.QSlash): 0 그 전 그림 재질 · 1 날 선 검기 · 2 결정 검기 · (93차) 3 에너지 초승달 · 4 세 줄기 칼바람 ·
	// 5 서리 폭풍 · 6 얼음 덩어리 초승달(M_Aurora_QSlashForge Style — 6은 덩어리를 골격 2 길로 띄운다)
	int32 GetQSlash() const;
	// 94차 V 팩 효과 시안(Aurora.FX.VLook 2·3, AuroraSkillComponentDFresh.cpp): 그림만 — 피해는 BlizzardSpike·BlizzardFinale 그대로
	void BlizzardPack(const FVector& Center, int32 Look, float Total);
	// 94차 Q 팩 칼 궤적(QSlash 7~9): 리본 메시(bThin = 가는 날, 아니면 넓은 리본) · 팩 칼 궤적 재질 사본(bPrimary = 평타 칼 궤적, 아니면
	// 메시 꼬리) · 그 밝기 · 꼭대기를 따라가는 오로라 평타 눈송이
	UStaticMesh* LoadQRibbon(bool bThin) const;
	UMaterialInterface* LoadQTrailMaterial(bool bPrimary) const;
	float GetQTrailBrightness(bool bPrimary) const;
	UParticleSystem* LoadQTrailSnow() const;
	// 95차 「검기를 아주 얇게」(QSlash 10): 아주 가는 리본
	UStaticMesh* LoadQRibbonHair() const;
	// 95차 F 「애니메이션 다른 거 없을까」(Aurora.FX.FMotion): 시전 동작을 다른 원작 동작 구간으로 — 틀었으면 true
	bool PlayLanceMotion();
	// A 게임 안 시안(Aurora.FX.APolish — 87차 「A-1, A-2는 게임에 적용해서 시안 볼 수 있게」): 0 그 전 · 1 가시 갑주 폭발 · 2 고드름 판 두르기
	int32 GetAPolish() const;
	void SpawnArmorPolish(int32 Look);
	void EndArmorPolish();
	// 93차 A 시전 동작 시안(Aurora.FX.AMotion): 다른 원작 동작의 한 구간을 시전 시간(ArmorRaiseSeconds)에 맞춘 빠르기로 틀고 다 든 자세에서
	// 멈춰 세운다(판정·재사용 대기·시전 시간은 그대로). 틀었으면 true, 0이면 false(그 전 손 뻗기)
	bool PlayArmorMotion();
	// 94차 「A는 좀 천천히」: 동작 시안(AMotion 1~3)이면 시전·버팀 시간을 늘려 둔다(BeginCast가 부름) — 판정·재사용 대기는 그대로
	void ApplyArmorTiming();
	// 94차 「보호막도 시안 여러 개」(Aurora.FX.AShell): 1 금 간 서리 구(그 전) · 2 몸에 얇은 얼음 막(겹쳐 그리는 재질) · 3 팩 분신 서리가 몸에
	int32 GetAShell() const;
	void BeginArmorSkin();
	void EndArmorSkin();
	bool bArmorSkin = false;
	// 94차 S 얼음 왕관(SPolish 3·4): 머리 위에서 천천히 도는 얼음 결정 고리
	void SpawnHasteCrown();
	void ClearHasteCrown();
	void HasteCrownTick();
	TArray<TWeakObjectPtr<UStaticMeshComponent>> HasteCrown;
	TWeakObjectPtr<USceneComponent> HasteCrownPivot;
	FTimerHandle HasteCrownTimer;
	double HasteCrownBorn = 0.0;
	TArray<TWeakObjectPtr<UParticleSystemComponent>> ArmorPlates;
	// S 새 방향(Aurora.FX.SPolish — 87차 「S는 다 아쉬움」 + 바닥 얼음 오브젝트 남발 금지): 0 그 전 · 1 은은한 서리 바닥 + 몸 오라 ·
	// 2 지금 마법진 바닥 + 몸 오라. 둘 다 둘레 얼음(HasteRimIce)은 뺀다. 오라 = 빨라진 동안 몸에 붙는 Rampage 얼음 분노 오라
	int32 GetSPolish() const;
	void SetHasteAura(bool bOn);
	TArray<TWeakObjectPtr<UParticleSystemComponent>> HasteAura;
	void PolishHitBurst(const FVector& Where, float Scale);
	void ExecuteLeap();
	void LeapDropTick();
	void EndLeap(bool bCancelled);
	void ExecuteCryoseism();
	// 착지 둘레 얼음 결정 물결(RStyle 1·3). Dense = 시안 Aurora.FX.VDense(0 지금 고리 셋 · 1~4 빽빽한 시안) — 고리마다 늦춰 띄운다.
	void SpawnCryoCrystals(const FVector& Center, float Range, int32 Dense);
	void BurstFrozen();
	// V 착지 시안 3: 얼린 대상마다 + 둘레 CryoSpearRingCount곳에 얼음 창이 내리꽂히고, 얼음이 터질 때(BurstFrozen) 같이 부서진다.
	void SpawnFallingSpears(const FVector& Center, const TArray<AActor*>& Targets);
	void FallingSpearTick();
	void ShatterFallingSpears();
	// V 착지 시안 5·7·8: 서리 충격파 고리 RingCount개(Seconds에 Radius까지 퍼짐, 재질 Material) + 그 자리 빛 번쩍(NovaTick이 퍼뜨리고
	// 흐린다) · 6·7·8: 빛나는 얼음 파편 Count개가 사방으로 튐(bHeavy = 크고 높이, Reach = 멈추는 거리 배율의 기준 반경)
	// Strength = 고리 진하기 배율(1 = 그대로 — D 고드름 비의 하늘 고리는 옅게)
	void SpawnFrostNova(const FVector& Center, float Radius, int32 RingCount, float Seconds, UMaterialInterface* Material, float Strength = 1.0f);
	void NovaTick();
	void SpawnIceBurst(const FVector& Center, int32 Count, bool bHeavy, float Reach);
	// S 시안(Aurora.FX.SLight): 장판 가운데 위 푸른 빛 — 바닥 데칼의 빛은 둘레(바닥·캐릭터)를 비추지 않는다.
	void SpawnHasteLight(float Intensity);
	// 얼어 있는(STUN) 대상 기록. 서리 검기가 얼어 있는 적에게 2배 피해를 준다.
	void RecordFrozen(AActor* Target, float Seconds);
	bool IsFrozen(const AActor* Target) const;
	void ExecuteFrostSlash();
	// 서리 검기 한 대상에 피해(× DamageScale)·감속·맞은 자리 이펙트(얼어 있으면 2배로 깨뜨림). 검기는 닿는 때에 부른다.
	void StrikeFrostSlash(AActor* Target, const FVector& Direction, float DamageScale = 1.0f);
	// 날아가는 검기가 부채꼴 안 대상마다 닿는 때(거리 ÷ 빠르기)에 맞게 예약한다. Reach·Seconds = 나는 거리·시간(0 이하면 Range·QWaveSeconds),
	// HitStop > 0 = 맞는 순간 그만큼 멈칫(시안 QBig 8의 마지막 검기), Roll = 검기가 기운 쪽(Q 덧붙임 시안의 칼자국)
	void ScheduleWaveHits(const FVector& Feet, const FVector& Direction, float DamageScale, float Reach = 0.0f, float Seconds = 0.0f,
		float HitStop = 0.0f, float Roll = 1.0f);
	// 얼음 검기가 나는 거리·시간(QBlade 비트 Blade에 16이 있으면 큰 검기)
	void GetWaveFlight(int32 Blade, float& OutReach, float& OutSeconds) const;
	// Q1(QStyle 5)·얼음 검기(QStyle 6): 칼에서 떠난 초승달 검기가 앞으로 날아간다. BladeTick이 Q2 칼자국과 같이 움직인다.
	// bIce = 얼음 조각 날·부스러기를 싣고 푸른 얼음빛으로, Roll = 옆으로 기운 쪽(+1 「/」 · -1 「\」).
	// Scale = 폭 배율(시안 QBig 8의 마지막 검기)
	void SpawnFlyingWave(const FVector& Feet, const FVector& Direction, bool bIce = false, float Roll = 1.0f, float Scale = 1.0f);
	// 얼음 검기 세 번(QStyle 6)의 Index번째(0 「/」 Slow_B · 1 「\」 Fast_C · 2 「/」 Fast_B)
	void LaunchIceWave(uint32 Generation, int32 Index);
	void BladeTick();
	// Q2: Q1 뒤 FrostCrossWindow초 안에 Q를 다시 누르면 X자로 두 번 벤다(Cut 0 = 「\」, 1 = 「/」).
	bool BeginFrostCross(const FVector& Aim);
	void FrostCrossCut(uint32 Generation, int32 Cut);
	void ShatterCutMarks();
	void ExecuteFrostField();
	void FrostFieldTick();
	bool IsFieldChannelling() const;
	// 냉기 장판 채널링을 끝까지 가기 전에 멈춘다(마지막 얼림 없음). 시전도 같이 끝낸다.
	void CancelFrostChannel(const TCHAR* Reason);
	// R 회오리(RField 1): 장판 위에 얼음 파편이 도는 기둥을 세우고, 칼질마다 한 단(VortexStageUp) 빨라지고 굵어지며 장판 안 적을
	// 가운데로 끌어당긴다(PullIntoVortex). 끝까지 버티면 위에서 내리꽂혀 터지고(bFull), 끊기면 흩어진다.
	void SpawnVortex();
	void AddVortexShards(int32 Count);
	void VortexStageUp();
	void VortexTick();
	void PullIntoVortex(float DeltaSeconds);
	void CollapseVortex(bool bFull);
	void ClearVortex();
	void ExecuteIceArmor();
	void IceArmorTick();
	void ExecuteFrostHaste();
	void FrostHasteTick();
	void SetHaste(bool bOn);
	// 회오리로 묶은 대상의 얼음이 풀리며 깨지는 마무리(E). bCenterShock = 시전 자리에 작은 파란 충격파도 띄울지(E 4는 안 띄움).
	void ShatterHoarfrost(TArray<TWeakObjectPtr<AActor>> Rooted, FVector Center, bool bCenterShock);
	// E 시안 4: 칼 궤적(Aurora 팩 칼 궤적, 칼 소켓 둘 사이)을 Seconds 동안 그리고 끝낸다.
	void BeginSwordTrail(float Seconds);
	// E 시안 4: 대상을 Seconds 동안 얼음 석상 재질로 바꾸고 발밑에 얼음 덩어리를 세운다.
	void EncaseTarget(AActor* Target, float Seconds);
	// 얼음 석상 재질을 원래대로 되돌린다. bForce가 아니면 다시 맞아 늦춰진 대상은 그대로 둔다(되돌렸으면 true).
	bool ReleaseEncased(AActor* Target, bool bForce);
	void ExecuteIceSpikes();
	void IceSpikeStep();
	void ExecuteIceLance();
	void IceLanceTick();
	// 나는 창 하나 뒤에 꼬리 시안(LanceFlight): 1 얼음 부스러기 · 2 잔상 · 3 둘 다. 때가 된 것만 남긴다.
	void TrailLance(FAuroraLance& Lance, const UStaticMeshComponent* Mesh, double Now);
	USkeletalMeshComponent* SpawnLanceClone(const FVector& Direction, const FVector& Where);
	void StopIceLance(int32 Index, AActor* HitTarget, const FVector& Where);

	// 전신 동작: 애니 BP 사본(ABP_Aurora_TopDown)의 마지막 슬롯 AuroraFullBody에 몽타주로 재생한다. 시작·끝이 보행과 섞인다
	// (2026-10-18 전엔 숨긴 자세 메시를 따라가게 해서 끝날 때 자세가 툭 바뀌었다). 슬롯은 aurora_topdown_slot_build.py가 넣는다.
	// BlendIn = 앞 자세에서 넘어오는 시간(R 손 뻗기 반복은 손을 거둬들이는 시간으로 쓴다).
	void PlayFullBody(UAnimSequence* Animation, float PlayRate = 1.0f, float StartTime = 0.0f, int32 LoopCount = 1,
		float BlendIn = FullBodyBlendIn);
	void StopFullBody();
	// A 동작의 골반이 보행 자세와 어긋나 있으면 섞여 들어갈 때 몸이 옆으로 튄다(10-20 오후 Level_Start 1.9~3.0초는 몸이 앞오른쪽
	// 약 90cm에서 두 걸음 걸어 제자리로 들어왔다 — 루트는 그대로). 시작할 때의 골반 수평 자리를 잡아 두고 ArmorPoseTick이 골반이
	// 그 자리에 머물게 메시를 반대로 민다 — 섞여 빠지는 동안까지, 다른 스킬이 시작되면 바로 원래 자리로.
	// 지금 동작(Emote_Ice_Sculpture 첫 0.33초)은 머리가 수평 15cm쯤 움직인다(aurora-70th-sculpt) — 골반은 안 재 봤다. 없으면 아무 일도 안 한다.
	void BeginArmorPoseLock();
	void ArmorPoseTick();
	void EndArmorPoseLock();
	FTimerHandle ArmorPoseTimer;
	FVector ArmorMeshBase = FVector::ZeroVector;
	FVector ArmorPelvisRest = FVector::ZeroVector;
	double ArmorPoseUntil = 0.0;
	bool bArmorPoseLocked = false;
	inline static const FName ArmorPelvisBone{TEXT("pelvis")};

	TWeakObjectPtr<ATopDownCombatCharacter> Character;
	UPROPERTY(Transient)
	TObjectPtr<UAnimMontage> ActiveMontage;
	inline static const FName FullBodySlot{TEXT("AuroraFullBody")};
	static constexpr float FullBodyBlendIn = 0.08f;
	static constexpr float FullBodyBlendOut = 0.25f;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UParticleSystemComponent>> OwnedEffects;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> OwnedMeshes;
	TMap<EAuroraSkill, double> CooldownEnds;

	EAuroraSkill ActiveSkill = EAuroraSkill::FrozenSimulacrum;
	int32 ActiveSlot = INDEX_NONE;
	uint32 CastGeneration = 0;
	bool bCasting = false;
	bool bEnabled = false;
	bool bSavedOrientRotation = true;
	FVector ActiveAim = FVector::ZeroVector;
	FString Feedback;
	double FeedbackDeadline = 0.0;
	FTimerHandle ActionTimer;
	FTimerHandle RecoveryTimer;
	TArray<FTimerHandle> ReleaseTimers;

	struct FShovedTarget
	{
		TWeakObjectPtr<AActor> Actor;
		FVector Origin = FVector::ZeroVector;
	};
	// W에 맞아 뒤로 미끄러지는 허수아비 하나 — 출발·도착 자리, 걸리는 시간, 대상 시간으로 센 흐른 시간
	struct FShoveSlide
	{
		TWeakObjectPtr<AActor> Actor;
		FVector From = FVector::ZeroVector;
		FVector To = FVector::ZeroVector;
		float Seconds = 0.1f;
		float Age = 0.0f;
	};
	TArray<FShoveSlide> ShoveSlides;
	FTimerHandle ShoveSlideTimer;
	FVector ChargeStart = FVector::ZeroVector;
	FVector ChargeEnd = FVector::ZeroVector;
	FVector ChargeLast = FVector::ZeroVector;
	float ChargeSeconds = 0.0f;
	float ChargeWallTravel = 0.0f;
	int32 ChargeWalls = 0;
	// 얼음벽 메시 배치값. BeginPlay에서 메시 크기로 정한다(높이 ChargeWallHeight에 맞춘 배율·조각 간격·긴 축 방향).
	float WallScale = 1.0f;
	float WallStep = 150.0f;
	float WallYawOffset = 0.0f;
	float WallLift = 0.0f;
	uint16 ChargeRootMotionId = 0;
	TSet<TWeakObjectPtr<AActor>> ChargeHits;
	TArray<FShovedTarget> ShovedTargets;
	TWeakObjectPtr<UParticleSystemComponent> ChargeBodyEffect;
	// 앞쪽 얼음을 다시 터뜨릴 때까지 남은 시간(시안 Aurora.FX.WFront 1~3)
	float ChargeFrontClock = 0.0f;
	bool bChargeHitStopped = false;
	TWeakObjectPtr<AActor> HitStopTarget;
	FTimerHandle HitStopTimer;
	FTimerHandle ChargeTimer;
	FTimerHandle ChargeEndTimer;
	FTimerHandle ShoveRestoreTimer;

	// 도약(W, 헤더 LeapAboveHead 설명): 떠난 자리 · 내려설 자리(캡슐 가운데) · 고른 대상 · 나타난 머리 위 자리 · 떨어진 시간(캐릭터 시간) · 도는 중
	FVector LeapStart = FVector::ZeroVector;
	FVector LeapTarget = FVector::ZeroVector;
	TWeakObjectPtr<AActor> LeapTargetActor;
	FVector LeapFrom = FVector::ZeroVector;
	float LeapDropAge = 0.0f;
	bool bLeaping = false;
	TWeakObjectPtr<UParticleSystemComponent> LeapTrailEffect;
	TWeakObjectPtr<UStaticMeshComponent> DecoyMesh;
	// 87차: 석상 대신 남는 캐릭터 사본(SpawnDecoyPose) · R-2 고드름 고리와 그 가운데 · Q 한 번 시전에 결정 파열을 이미 받은 대상
	TWeakObjectPtr<USkeletalMeshComponent> DecoyClone;
	TArray<TWeakObjectPtr<UParticleSystemComponent>> PrisonRing;
	FVector PrisonCenter = FVector::ZeroVector;
	// RPrison 3 떠서 도는 결정 · 생긴 때 · 흩어지기 시작한 때(-1 = 아직) · 돌리는 타이머 · 이번 감옥 모양(터질 때 갈래)
	TArray<TWeakObjectPtr<UStaticMeshComponent>> PrisonOrbs;
	double PrisonOrbBorn = 0.0;
	double PrisonOrbScatter = -1.0;
	FTimerHandle PrisonOrbTimer;
	// 95차 R 4 「연기가 갑자기 생긴다 — 자연스럽게」: 터짐을 느린 속도로 띄워 작게서 키우다 멈춰 세우는 동안 돌리는 타이머 · 시작 때
	FTimerHandle PrisonGrowTimer;
	double PrisonGrowBorn = 0.0;
	void PrisonGrowTick();
	int32 PrisonLook = 0;
	TSet<TWeakObjectPtr<AActor>> QBurstTargets;
	FTimerHandle LeapEndTimer;
	FTimerHandle DecoyTimer;

	TArray<TWeakObjectPtr<AActor>> FrozenTargets;
	FTimerHandle CryoTimer;

	TMap<TWeakObjectPtr<AActor>, double> FrozenUntil;

	FVector FieldCenter = FVector::ZeroVector;
	double FieldStartedAt = 0.0;
	double FieldNextGlowAt = 0.0;
	int32 FieldBurstsDone = 0;
	// R 시안 7: 다음에 손을 다시 뻗는 때 · 뻗은 손끝에서 크게 터뜨릴 때(0 = 없음) · 뻗은 횟수
	double FieldNextThrustAt = 0.0;
	double FieldThrustBurstAt = 0.0;
	int32 FieldThrusts = 0;
	// 시전 때 고른 버티는 자세 시안(Aurora.FX.RChannel) · 시안 8 손을 앞뒤로 오가기 시작한 때(0 = 아직) · 시안 9 다음 칼질 차례
	int32 FieldStyle = 0;
	double FieldPulseStartedAt = 0.0;
	int32 FieldCarveIndex = 0;
	FTimerHandle FieldTimer;

	double ArmorStartedAt = 0.0;
	double ArmorEndsAt = 0.0;
	TWeakObjectPtr<UStaticMeshComponent> ArmorShell;
	FTimerHandle ArmorTimer;

	FVector HasteCenter = FVector::ZeroVector;
	double HasteEndsAt = 0.0;
	bool bHasteApplied = false;
	TWeakObjectPtr<UDecalComponent> HasteFloor;
	// S 시안 6·7: 장판 고리 위에 겹쳐 까는 깨진 테두리
	TWeakObjectPtr<UDecalComponent> HasteRim;
	FTimerHandle HasteTimer;

	FVector SpikeOrigin = FVector::ZeroVector;
	FVector SpikeDirection = FVector::ForwardVector;
	float SpikeLength = 0.0f;
	int32 SpikeIndex = 0;
	// 시전 때 고른 D 시안(Aurora.FX.DStyle)
	int32 SpikeStyle = 0;
	TSet<TWeakObjectPtr<AActor>> SpikeHits;
	FTimerHandle SpikeTimer;
	TArray<FAuroraRuptureSpike> RuptureSpikes;
	FTimerHandle RuptureSpikeTimer;

	TArray<FAuroraFlake> Flakes;
	FTimerHandle FlakeTimer;
	TArray<FAuroraShard> Shards;
	FTimerHandle ShardTimer;

	// Q1 검기·Q2 칼자국(BladeTick) · Q2를 받는 마감(0 = 닫힘) · Q1 도중 Q를 다시 눌러 둠 · 지금 시전이 Q2 · 그때 겨눈 자리
	TArray<FAuroraWave> Waves;
	TArray<FAuroraFallingSpear> FallingSpears;
	FTimerHandle SpearTimer;
	// V 착지 시안 5·7·8: 퍼지는 서리 충격파 고리들 · 착지 자리 빛과 켜진 때
	TArray<FAuroraNovaRing> NovaRings;
	FTimerHandle NovaTimer;
	TWeakObjectPtr<UPointLightComponent> NovaLight;
	double NovaLightBorn = 0.0;
	TWeakObjectPtr<UPointLightComponent> HasteLight;
	TArray<FAuroraCutMark> CutMarks;
	FTimerHandle BladeTimer;
	double CrossWindowEnds = 0.0;
	bool bCrossQueued = false;
	bool bCrossCast = false;
	FVector CrossAim = FVector::ZeroVector;

	// R 회오리: 시전 때 고른 RField · 파편 · 단 · 단이 오른 때 · 내리꽂히기 시작한 때(0 = 아직) · 끝까지 버텼나 · 끌어당긴 거리 합
	int32 FieldVisual = 0;
	TArray<FAuroraVortexShard> VortexShards;
	int32 VortexStage = 0;
	double VortexStageAt = 0.0;
	double VortexCollapseAt = 0.0;
	bool bVortexFull = false;
	double VortexLastTick = 0.0;
	double FieldLastTick = 0.0;
	float VortexPulled = 0.0f;
	FTimerHandle VortexTimer;

	TArray<FAuroraLance> Lances;
	// 한 번 던진 창 셋 중 이미 피해를 준 대상(가까이서 셋이 다 꽂혀도 피해는 한 번)
	TSet<TWeakObjectPtr<AActor>> LanceHitTargets;
	// 던질 때 고른 F 시안(Aurora.FX.FStyle)
	int32 LanceStyle = 0;
	// 이번에 던진 창의 빠르기 배율(매 퀄리티 시안 FLook 4만 1이 아님)
	float LanceSpeedScale = 1.0f;
	// 던질 때 고른 나는 꼬리 시안(Aurora.FX.FFlight) · 던진 자리 바닥 높이(부스러기가 떨어질 곳) · 잔상들
	int32 LanceFlight = 0;
	float LanceFloorZ = 0.0f;
	TArray<FAuroraLanceGhost> LanceGhosts;
	FTimerHandle LanceTimer;

	// 원작 위키 근거는 없다(효과 방식만 원작: 공개 소개 글). 수치는 카운테스·스패로우·Gideon 규모 임시값이다.
	static constexpr float HoarfrostRootSeconds = 1.5f;
	// 시전 때 하나 + 내려찍은 뒤 회오리가 한 겹씩 이어 뜬다. 사용자 요청 「30% 줄여」·「더 줄여」로 겹쳐 띄우던 5겹 → 1겹(1.3배).
	// 10-19 「바닥 원과 크기가 안 맞는다, 원은 키우고 스킬은 약간 줄여 중간 크기로」: 사진(aurora-24th-final e_0_0~4)에서 회오리의
	// 진한 부분이 바닥 원 반경의 1.15~1.24배 → 둘이 원의 1.1배에서 만나게 회오리 1.3 → 1.2, 바닥 원 데칼 반경 × HoarfrostRingScale.
	// 묶는 판정 반경(Range 380)은 그대로다.
	static constexpr float HoarfrostSwirlScale = 1.2f;
	static constexpr float HoarfrostRingScale = 1.1f;
	// 회오리 띠가 다 돌고 사라지는 때(촬영 e_060 → e_090 사이). 이때 남은 얼음 조각도 같이 지운다.
	static constexpr float HoarfrostSwirlSeconds = 0.75f;
	// 「한 바퀴 돌고 갑자기 없어진다」(2026-10-18): 절반 속도로 늦췄더니 「너무 부드럽다」 → 원래 속도로 두 바퀴 이어 돌려(0.75 × 2 =
	// 묶는 1.5초) 깨지는 마무리 순간에 지운다. 그때 같이 넣었던 둘레 얼음 바위 터짐은 「넣으라고 한 적 없다」로 뺐다.
	static constexpr int32 HoarfrostSwirlTurns = 2;
	// 10-21 「E 쓰고 나서 V에서 버린 얼음 오브젝트를 주변에 에워싸도록 — 빈틈없이」: 내려찍으면 묶는 반경(Range) 둘레를 V 얼음 결정
	// (Freeze_Segment)이 HoarfrostWallStep마다 바깥으로 기울어 두르고, 묶기가 풀릴 때 같이 부서진다. 결정 하나 폭이 화면에서 약 100cm
	// (V 바깥 고리와 같은 크기 0.85 × CryoEffectScale — 그때 90cm 간격으로 서로 닿았다)라 60cm면 겹쳐 틈이 없다(반경 380에 40개).
	// 10-18에 뺀 원작 둘레 결정은 같은 결정 10개(240cm마다)였다.
	// 이어서 「얼음 오브젝트가 생기고 나서 한 5~10초 정도 유지 — 몬스터가 못 오게 만드는 느낌」: 묶기와 따로 콘솔 값 Aurora.FX.EWallSeconds
	// (기본 8초) 동안 서 있다가 부서진다. 보이기만 하고 길은 막지 않는다.
	static constexpr float HoarfrostWallStep = 60.0f;
	static constexpr float HoarfrostWallScale = 0.85f;
	// 결정 입자는 제 수명이 2~3초라 8초를 세워 두면 3초 전에 저절로 사라졌다(aurora-64th-drafts). 다 솟은 HoarfrostWallHold초 뒤 입자
	// 시간을 HoarfrostWallHoldDilation배로 거의 멈춰 세워 두고, 부술 때(ReleaseOwnedEffect) 제 속도로 돌린다.
	static constexpr float HoarfrostWallHold = 1.0f;
	static constexpr float HoarfrostWallHoldDilation = 0.02f;
	// E 시안 4(10-19 밤 큰 틀 E1 「회전 베기 + 얼음 가둠」): 바닥 원판·회오리 대신 칼 궤적이 도는 칼을 따라 고리를 그리고,
	// 묶인 대상은 몸이 얼음 석상 재질로 바뀌고 발밑에 얼음 덩어리가 솟았다가 풀릴 때 깨진다.
	// 칼 궤적을 그리는 시간·사라지는 시간 · 덩어리 크기(대상 반경 배)·윗면 높이·솟는 시간 · 깨지기 전 금 가는 조각이 튀는 앞당김
	static constexpr float HoarfrostTrailSeconds = 0.5f;
	static constexpr float HoarfrostTrailFadeSeconds = 0.6f;
	static constexpr float EncaseChunkWidthScale = 2.6f;
	static constexpr float EncaseChunkTop = 55.0f;
	static constexpr float EncaseGrowSeconds = 0.12f;
	static constexpr float EncaseCrackLead = 0.25f;
	// 깨질 때 튀는 파편 수·바깥 빠르기·위 빠르기(F 꽂힌 자리 파편과 같은 규모)
	static constexpr int32 EncaseShardCount = 12;
	static constexpr float EncaseShardSpeed = 420.0f;
	static constexpr float EncaseShardUpSpeed = 340.0f;
	UPROPERTY(Transient)
	TArray<FAuroraEncased> Encased;
	// 2000 → 3750(450cm를 약 0.12초, 사용자 「임팩트 있고 절도 있게」 2026-10-18)
	static constexpr float ChargeSpeed = 3750.0f;
	static constexpr float ChargeMinDistance = 150.0f;
	static constexpr float ChargeHitRadius = 130.0f;
	static constexpr float ChargeShoveDistance = 170.0f;
	// 10-21 「옆이 아니라 맞으면 무조건 뒤로 밀리게」: 돌진 쪽으로 적어도 ChargeShoveDistance, 돌진이 막히지 않게 돌진 끝보다 두 몸 반경 +
	// ChargeShoveClearance 앞까지 민다. 남은 돌진 시간(짧아도 ChargeShoveMinSeconds) 동안 처음 빠르고 점점 느리게 미끄러져 몸보다 앞서 간다.
	static constexpr float ChargeShoveClearance = 25.0f;
	static constexpr float ChargeShoveMinSeconds = 0.12f;
	static constexpr float ChargeSlowSeconds = 1.5f;
	static constexpr float ChargeStopSeconds = 0.55f;
	static constexpr float ChargeWallHeight = 140.0f;
	static constexpr float ChargeWallSeconds = 3.0f;
	// W 시안: 앞쪽 얼음 재발사 간격, 빠른 달리기 배율, 원작 돌진 동작(Ability_Q)의 내지르는 구간 시작·배율(GIF 0.28~0.83초 구간)
	static constexpr float ChargeFrontInterval = 0.09f;
	static constexpr float ChargeRunFastRate = 2.0f;
	// 원작 돌진 동작(Ability_Q)은 0.5초에 칼을 앞으로 뻗는다. 10-20 「너무 즉발 — 0.3~0.5초 돌진 동작만 보여 줬다가 돌진」:
	// 처음부터 제 빠르기로 틀어 ChargeWindupSeconds 동안 제자리에서 칼을 들어 올리고 → 출발(0.4) → 도착 무렵(0.52)에 칼이 뻗고,
	// 버티는 0.2초 뒤(0.72) 시전이 끝난다. 그 전(10-18)은 0.2초부터 1.4배로 준비 0.1초 → 출발(0.34) → 도착(0.51).
	static constexpr float ChargeLungeStart = 0.0f;
	static constexpr float ChargeLungeRate = 1.0f;
	static constexpr float ChargeWindupSeconds = 0.4f;
	static constexpr float ChargeHoldSeconds = 0.2f;
	static constexpr float ChargeHitStopSeconds = 0.06f;
	static constexpr float HitStopDilation = 0.05f;
	// 맞은 자리 얼음 파편(Rampage Rock_HitWorld) 크기. 길에 남는 파편(0.35)보다 크게.
	static constexpr float ChargeHitShardScale = 0.55f;
	// 10-21 「Space(도약)를 W로 옮긴 뒤 대상 지정형으로 — 단순 점프가 아니라 대상 머리 위에 나와서 바로 앞에 착지」: 시전 0.15초(ActionTime)에
	// 대상 머리 꼭대기에서 LeapAboveHead 위(발 기준)로 순간이동해 나타나고, LeapSeconds 동안 옆으로는 처음 빠르게 · 아래로는 점점 빠르게
	// (떨어지듯) 대상 바로 앞(떠난 쪽, 두 몸 반경 + LeapLandGap)에 내려선다 — 원작 동작의 착지(0.65초)와 같은 때. 떠난 자리에 얼음 분신은 그대로.
	// 전엔 겨눈 바닥으로 포물선 점프(높이 120)였다.
	static constexpr float LeapAboveHead = 140.0f;
	static constexpr float LeapLandGap = 20.0f;
	static constexpr float LeapSeconds = 0.5f;
	static constexpr float DecoySeconds = 1.5f;
	static constexpr float DecoyRadius = 300.0f;
	static constexpr float DecoySlowSeconds = 2.0f;
	static constexpr float CryoInitialDamage = 20.0f;
	static constexpr float CryoFreezeSeconds = 1.2f;
	static constexpr float CryoBurstRadius = 250.0f;
	static constexpr float CryoSlowSeconds = 2.0f;
	// R 시안 1·3의 얼음 결정 물결: 안쪽부터 바깥으로 몇 겹, 겹 사이 간격
	static constexpr int32 CryoWaveCount = 3;
	static constexpr float CryoWaveInterval = 0.09f;
	// 도약 중 발밑 청록 냉기(Rampage Ice_Enrage_Cast) 크기: 1.5 → 3.75(사용자 「2~3배」 2026-10-18)
	static constexpr float CryoChargeGlowScale = 3.75f;
	// 궁극기(V) 이펙트 전체 크기 배율(10-19 「한 30% 줄여 보자, 100 → 70%」). 시전·냉기 빛·착지 폭발·결정 물결·터질 때 파편에 곱한다.
	// 얼림·피해 반경(Range·CryoBurstRadius)과 대상에 붙는 얼음·감속 표시는 그대로다.
	static constexpr float CryoEffectScale = 0.7f;
	// V 착지 시안(Aurora.FX.VLand, 10-20 「바닥에 오브젝트 깔리는 거 말고 뭐 없을까 — 시안 여러 개」): 1·2 균열이 바깥으로 갈라져
	// 나가는 시간 · 4 서리 바닥이 덮이는 시간 · 채움·고리 진하기 · 3 얼음 창 수(둘레)·둘레 반경 배율·떨어지는 높이·시간·크기(길이·굵기)
	static constexpr float CryoCrackSweepSeconds = 0.25f;
	static constexpr float CryoFrostFadeIn = 0.15f;
	static constexpr float CryoFrostFill = 0.3f;
	static constexpr float CryoFrostRing = 0.6f;
	static constexpr int32 CryoSpearRingCount = 6;
	static constexpr float CryoSpearRingRadius = 0.6f;
	static constexpr float CryoSpearDrop = 700.0f;
	static constexpr float CryoSpearSeconds = 0.16f;
	static constexpr float CryoSpearLength = 200.0f;
	static constexpr float CryoSpearWidth = 16.0f;
	// V 결정 빽빽 시안(Aurora.FX.VDense, 10-20 밤 「지금 나오는 오브젝트들을 빽빽하게 — 일단 이 버전으로 하나, 추가 시안 더」):
	// 지금(0)은 고리 셋(반경 0.31·0.61·0.92 × Range)에 6·11·16개 = 33개, 바깥 고리 결정 사이 약 180cm.
	// 1~3은 고리 다섯을 CryoDenseFirst부터 CryoDenseStep 간격으로 두고 고리마다 둘레 CryoDenseStep마다 하나(98개 — 결정 하나 폭이
	// 화면에서 약 100cm라 서로 닿는다). 크기는 안쪽 0.55 → 바깥 0.85(지금과 같은 폭), 다 퍼지는 데 CryoDenseSpread(지금과 같은 0.18초).
	// 2 = 1 + 자리·크기·방향 흩뜨림 · 3 = 1 + 고리 사이에 작은 결정(크기 CryoDenseSmallScale, 간격 0.75배) · 4 = 고리 넷(6·11·16·21개)
	// + 결정 사이 바닥이 하얗게 언다(VLand 4의 서리 바닥).
	static constexpr int32 CryoDenseRings = 5;
	static constexpr float CryoDenseFirst = 100.0f;
	static constexpr float CryoDenseStep = 90.0f;
	static constexpr float CryoDenseSpread = 0.18f;
	static constexpr float CryoDenseSmallScale = 0.35f;
	// V 착지 시안 5~8(Aurora.FX.VLand, 10-20 밤 「다 별로, 저 얼음 오브젝트가 별로인 것 같다 — 지우고 다른 이펙트 시안」): 5 서리 충격파 고리
	// 둘(빛나는 고리 그림 T_Aurora_NovaRing — Q 큰 검기와 같은 뜯긴 결)이 반경 CryoNovaStart → Range × CryoNovaReach로 CryoNovaSeconds에
	// 퍼지며(처음 빠르게) 다 퍼질 무렵부터 CryoNovaFade에 사라짐, 둘째는 CryoNovaSecondDelay 늦고 CryoNovaSecondStrength만큼 흐림 +
	// 착지 자리 푸른 빛 번쩍(CryoNovaLight칸델라 → 0, CryoNovaLightSeconds) · 6 빛나는 얼음 파편 CryoBurstShardCount개가 사방으로 튀어 바닥을
	// 미끄러져 멈추고 얼음이 터질 때 사라짐 · 7 = 5 + 6 · 8 = 7 + 착지 순간 CryoLandHitStopSeconds 멈칫(W·D와 같은 손맛)
	static constexpr float CryoNovaStart = 40.0f;
	static constexpr float CryoNovaReach = 1.05f;
	static constexpr float CryoNovaSeconds = 0.25f;
	static constexpr float CryoNovaFade = 0.3f;
	static constexpr float CryoNovaSecondDelay = 0.08f;
	static constexpr float CryoNovaSecondStrength = 0.6f;
	static constexpr float CryoNovaLight = 120.0f;
	static constexpr float CryoNovaLightSeconds = 0.5f;
	static constexpr int32 CryoBurstShardCount = 48;
	static constexpr float CryoLandHitStopSeconds = 0.07f;
	// 8 바탕 시안(Aurora.FX.VNova 비트, 10-20 밤 「V는 8을 기반으로 시안 여러 개」 — VLand 5~8에만): 1 고리를 더 거칠게(T_Aurora_NovaRingRough) ·
	// 2 고리 셋을 CryoNovaFastSeconds에 더 빠르게 · 4 파편을 크고 높이(CryoHeavyShardCount개) · 8 얼음이 터질 때(1.2초) 언 대상마다 작은
	// 충격파(반경 CryoBurstRadius)와 파편 CryoEchoShardCount개가 한 번 더
	static constexpr float CryoNovaFastSeconds = 0.17f;
	static constexpr int32 CryoHeavyShardCount = 32;
	static constexpr int32 CryoEchoShardCount = 16;
	// 새 스킬(2026-10-18 사용자 승인 「가자」). 원작에 없고 수치는 임시값이다.
	// 서리 검기(Q): 앞쪽 부채꼴 베기, 얼어 있는 적에게 FrostSlashFrozenMultiplier배.
	static constexpr float FrostSlashHalfAngle = 60.0f;
	static constexpr float FrostSlashFrozenMultiplier = 2.0f;
	static constexpr float FrostSlashSlowSeconds = 1.0f;
	// 칼 궤적 바닥 결정(Freeze_Segment): 개수·베는 거리 대비 자리·크기·결정 사이 간격·부서질 때까지
	static constexpr int32 SlashCrystalCount = 7;
	static constexpr float SlashCrystalReach = 0.55f;
	static constexpr float SlashCrystalScale = 0.3f;
	static constexpr float SlashCrystalInterval = 0.025f;
	static constexpr float SlashCrystalSeconds = 0.6f;
	// 시안 1·2(바닥 데칼) 자국 하나의 반경·남는 시간
	static constexpr float SlashTrailRadius = 75.0f;
	static constexpr float SlashTrailSeconds = 1.0f;
	// Q 시안 1·3(Aurora.FX.QStyle, 10-19): 부채꼴 무늬가 휩쓸며 드러나는 시간·남는 시간
	static constexpr float SlashSweepSeconds = 0.12f;
	static constexpr float SlashWaveSeconds = 0.6f;
	// 데칼 회전 0일 때 그림 위쪽은 세계 yaw 270을 보고 좌우는 뒤집히지 않는다 → 겨눈 yaw + 90, 휩쓸기는 그림 왼쪽(= 캐릭터 왼쪽)부터.
	// 게임 사진(aurora-18th-drafts, 허수아비 자리로 방향을 잰 것)에서 정했다. 처음엔 데칼 미리보기 한 장을 잘못 읽어 +135·반대쪽부터로
	// 넣었다가 초승달이 55도 비틀리고 오른쪽부터 나왔다.
	static constexpr float SweepDecalYawOffset = 90.0f;
	static constexpr float SweepRevealInvert = 0.0f;
	// Q 흩날리는 눈송이(Aurora.FX.QBoost 1, 10-19): 수 · 크기(cm) · 사는 시간 · 날아가는 빠르기(바깥·칼 지나가는 쪽·위) ·
	// 공기 저항(클수록 빨리 느려짐) · 떨어지는 힘 · 옆으로 흔들리는 폭. 첫 판 22개·5~11cm·0.8~1.3초는 게임 화면에서 점으로만 보여 키웠다.
	static constexpr int32 SlashFlakeCount = 30;
	static constexpr float SlashFlakeMinSize = 14.0f;
	static constexpr float SlashFlakeMaxSize = 26.0f;
	static constexpr float SlashFlakeMinLife = 1.0f;
	static constexpr float SlashFlakeMaxLife = 1.6f;
	static constexpr float SlashFlakeOutSpeed = 260.0f;
	static constexpr float SlashFlakeSweepSpeed = 160.0f;
	static constexpr float SlashFlakeUpSpeed = 110.0f;
	static constexpr float SlashFlakeDrag = 2.5f;
	static constexpr float SlashFlakeGravity = 90.0f;
	static constexpr float SlashFlakeFlutter = 18.0f;
	// Q 흩날림 2(Aurora.FX.QBoost 기본, 10-19 오후 「테두리 더 얇게 + 흩날리는 류로」): 날 바로 위에서 떠나는 눈가루(작고 많음) +
	// 1보다 큰 눈송이.
	static constexpr int32 SlashDustCount = 70;
	static constexpr float SlashDustMinSize = 5.0f;
	static constexpr float SlashDustMaxSize = 10.0f;
	static constexpr float SlashDustMinLife = 0.9f;
	static constexpr float SlashDustMaxLife = 1.9f;
	static constexpr int32 SlashBigFlakeCount = 24;
	static constexpr float SlashBigFlakeMinSize = 20.0f;
	static constexpr float SlashBigFlakeMaxSize = 34.0f;
	static constexpr float SlashBigFlakeMinLife = 1.2f;
	static constexpr float SlashBigFlakeMaxLife = 2.0f;
	// Q 여전사풍 시안(Aurora.FX.QBoost 3·4, 10-19 저녁 「너무 공주 같은 느낌, 여전사 같았으면」): 하늘하늘 떠다니는 눈송이 대신
	// 무겁게 튀었다 떨어지는 얼음 파편. 수 · 크기(옆 너비·두께·길이 cm, 최소~최대) · 사는 시간 · 날아가는 빠르기(바깥·칼 지나가는 쪽·위) ·
	// 떨어지는 힘 · 바닥에 닿은 뒤 미끄러지는 정도(클수록 빨리 멈춤)
	static constexpr int32 SlashShardCount = 18;
	static constexpr float SlashShardMinWidth = 7.0f;
	static constexpr float SlashShardMaxWidth = 13.0f;
	static constexpr float SlashShardMinLength = 24.0f;
	static constexpr float SlashShardMaxLength = 44.0f;
	static constexpr float SlashShardMinLife = 0.7f;
	static constexpr float SlashShardMaxLife = 1.1f;
	static constexpr float SlashShardOutSpeed = 520.0f;
	static constexpr float SlashShardSweepSpeed = 380.0f;
	static constexpr float SlashShardUpSpeed = 260.0f;
	static constexpr float SlashShardGravity = 1600.0f;
	static constexpr float SlashShardSlideDrag = 6.0f;
	// Q 시안 3: 칼이 바닥을 베고 지나간 자국(T_Aurora_SlashScar)이 남는 시간·사라지는 시간
	static constexpr float SlashScarSeconds = 1.6f;
	static constexpr float SlashScarFadeOut = 0.6f;
	// Q1 날아가는 검기(QStyle 5, 10-19 밤 큰 틀 「Q1 Q2 둘 다」): 칼끝이 앞을 지나는 때(Slow_B 0.20~0.23초, aurora-40th-qhand)에 떠나
	// 몸 앞 QWaveStart에서 베는 거리(Range)까지 QWaveSeconds에 날고 QWaveOvershoot 더 가며 흐려진다(QWaveFadeFrom부터).
	// 폭(처음 → 끝) · 뜬 높이 · 옆으로 기운 각(왼쪽 아래 → 오른쪽 위로 올려 베는 칼) · 그림 속 초승달 자리(가운데에서 반지름의
	// 0.78, 폭 = 반지름의 1.35배). 대상마다 검기가 닿는 때 맞는다(판정 부채꼴은 그대로).
	static constexpr float QWaveLaunch = 0.22f;
	static constexpr float QWaveStart = 60.0f;
	static constexpr float QWaveSeconds = 0.3f;
	static constexpr float QWaveOvershoot = 60.0f;
	static constexpr float QWaveFadeFrom = 0.75f;
	static constexpr float QWaveStartWidth = 170.0f;
	static constexpr float QWaveEndWidth = 340.0f;
	static constexpr float QWaveHeight = 65.0f;
	// 10-21 「사선으로 가는 건 확실히 사선으로」: 나는 쪽 축으로 18도는 카메라(내려다봄 50도)에서 화면 기울기 약 12도, 옆으로 쏘면 0도였다.
	// 나는 쪽 축으로 더 눕히면 옆으로 쏠 때 둘 중 하나가 카메라 반대로 누워 가는 줄이 된다(골격 시안 1의 둘째 검기) → 카메라가 보는 축으로
	// Aurora.FX.QTilt도만큼 돌린다(화면에서 그 각으로 기울고, 카메라를 보는 넓이는 그대로). 낮은 날 끝이 바닥에 묻히지 않게 띄운다.
	static constexpr float QWaveRoll = 18.0f;
	static constexpr float QWaveArcReach = 0.78f;
	static constexpr float QWaveArcWidth = 1.35f;
	// 얼음 검기 세 번(QStyle 6, 10-19 밤 「차라리 얼음 검기를 날리는 거, 두세 번 정도, 이펙트 신경 좀」): Slow_B 「/」 → Fast_C 「\」 →
	// Fast_B 「/」를 이어(Q2와 같은 이음) 칼마다 검기 하나. 동작을 넘기는 때·칼마다 검기가 떠나는 때(칼끝이 가장 빠른 때, aurora-40th-qhand)·
	// 끝 · 검기마다 피해 배율(Damage 30 기준) · 폭(처음 → 끝) · 날 얼음 조각 수·길이(검기 폭 300 기준 cm)·옆 너비 · 부스러기를 떨구는 틈.
	static constexpr float QVolleySwitchFirst = 0.3f;
	static constexpr float QVolleySwitchSecond = 0.6f;
	static constexpr float QVolleyLaunch[] = {0.22f, 0.48f, 0.79f};
	static constexpr float QVolleyDamage[] = {0.45f, 0.45f, 0.6f};
	static constexpr float QVolleyEnd = 1.05f;
	// 10-21 「Q는 미치겠네 — 그냥 올곧게 일직선으로(바닥이랑 마주보게) 만들어서 두 개만 쏘는 건 어때」(Aurora.FX.QFlat 1): 앞 둘
	// (Slow_B 「/」 → Fast_C 「\」)만 칼마다 검기 하나. 검기는 옆으로 기울이지 않고 바닥과 나란히 눕는다(판 앞면이 위 — 화면 기울기 QTilt도
	// 기운 쪽 부호 0을 곱해 0). 초승달 모양은 그대로. 끝(Fast_C로 넘긴 0.3초 뒤 0.5초 — 셋째 동작으로 안 넘긴다) · 검기마다 피해 배율
	// (셋일 때 합 1.5를 둘로 나눔)
	static constexpr int32 QFlatVolley = 2;
	static constexpr float QFlatVolleyEnd = 0.8f;
	static constexpr float QFlatVolleyDamage = 0.75f;
	static constexpr float QIceWaveStartWidth = 150.0f;
	static constexpr float QIceWaveEndWidth = 300.0f;
	static constexpr int32 QIceCrestCount = 15;
	static constexpr float QIceCrestLength = 95.0f;
	static constexpr float QIceCrestWidth = 26.0f;
	static constexpr float QIceShedSeconds = 0.035f;
	// Q 검기 시안 4(겹 검기): 뒤따르는 초승달 수 · 하나씩 뒤처지는 거리(cm) · 폭 배율 줄어듦 · 흐림 배율
	static constexpr int32 QEchoCount = 2;
	static constexpr float QEchoLag = 45.0f;
	static constexpr float QEchoShrink = 0.08f;
	static constexpr float QEchoFade[2] = {0.55f, 0.3f};
	// Q 검기 시안 1·2: 바람 줄기 메시가 검기 폭의 몇 배 · 채찍 잔상·바람 날개 크기
	static constexpr float QSplineWidthScale = 1.1f;
	static constexpr float QAfterimageScale = 1.6f;
	static constexpr float QKickOffScale = 1.2f;
	// Q 검기 시안(Aurora.FX.QBlade, 10-20 밤 「Q 다 아쉽다, 시안 가자」 — 재 보니 ① 몸통이 짙은 파랑 반투명이라 화면엔 날 선(약 1cm)만
	// 보이고 ② 눈에 띄는 건 빛을 받는 회색 얼음 원뿔 15개(빗살처럼)뿐 ③ 빛이 둘레를 안 비춘다): 4 따라가는 빛 세기(칸델라)·닿는 거리·
	// 바닥 위 높이(빛깔은 S 빛과 같다). 첫 판 50칸델라·40cm는 바로 밑이 약 310럭스라 바닥이 하얗게 날아갔다 → S 빛(60칸델라·
	// 120cm, 밑 약 42럭스)과 비슷한 약 50럭스로.
	static constexpr float QLightCandelas = 18.0f;
	static constexpr float QLightReach = 320.0f;
	static constexpr float QLightHeight = 60.0f;
	// 이어서 「7번이 그나마 낫다 — 원하는 건 검기가 더 크게, 굵게, 빠르게, 더 멀리, 더 거친 느낌, 퀄리티도 더 좋게」(QBlade 16 큰 검기):
	// 나는 거리 420 → QBigReach(맞는 거리도 같이) · 시간 0.3 → QBigSeconds(1,200 → 약 2,290cm/초) · 폭 150~300 → QBigStartWidth~QBigEndWidth ·
	// 높이 65 → QBigHeight(커진 판이 18도 기울면 끝이 바닥에 묻힘). 그림은 몸통 0.24에 붓질처럼 뜯긴 결(T_Aurora_SlashRough, M_Aurora_WaveBladeRough).
	// 10-21 「Q 날아가는 속도 빠르게」: 0.28 → 0.2초(약 2,290 → 3,190cm/초, 1.4배)
	static constexpr float QBigReach = 700.0f;
	static constexpr float QBigSeconds = 0.2f;
	static constexpr float QBigStartWidth = 220.0f;
	static constexpr float QBigEndWidth = 480.0f;
	static constexpr float QBigHeight = 85.0f;
	// 32 잔상 줄기: 같은 검기 QSmearCount장이 QSmearLag씩 뒤처져 조금씩 좁고 흐리게(빨라져 한 장면에 약 38cm 간다)
	static constexpr int32 QSmearCount = 4;
	static constexpr float QSmearLag = 30.0f;
	static constexpr float QSmearShrink = 0.04f;
	static constexpr float QSmearFade[4] = {0.55f, 0.38f, 0.24f, 0.12f};
	// 64 파편 강화: 날 위 원뿔 수 · 떨어지는 부스러기 수(한 번에)·크기 배율 — 부스러기도 빛나는 얼음 재질로
	static constexpr int32 QBigCrestCount = 21;
	static constexpr int32 QBigShedCount = 4;
	static constexpr float QBigShedSize = 1.8f;
	// 23(큰 검기) 바탕 시안(Aurora.FX.QBig 비트, 10-20 밤 「23이 괜찮은데 이걸 기반으로 여러 시안」 — 큰 검기에만): 1 더 거칠게 뜯긴 결
	// (T_Aurora_SlashRougher) · 2 흰 날 + 짙푸른 몸통(QContrast*) · 4 다 날아간 자리에서 산산조각(빛나는 파편 QShatterCount개 + 작은 냉기
	// 충격) · 8 마지막(셋째) 검기를 QFinisherScale배로 + 맞는 순간 QFinisherHitStop 멈칫
	inline static const FLinearColor QContrastIce{0.03f, 0.25f, 1.0f};
	inline static const FLinearColor QContrastWhite{0.92f, 0.98f, 1.0f};
	static constexpr float QContrastBrightness = 1.2f;
	static constexpr float QContrastLineGlow = 3.2f;
	static constexpr int32 QShatterCount = 14;
	static constexpr float QFinisherScale = 1.35f;
	static constexpr float QFinisherHitStop = 0.06f;
	// Q 시안(Aurora.FX.QFeel 비트, 10-21 「시안 중에선 지금 Q가 제일 낫다 — 다른 시안, 한계인가」 — 큰 검기 QBlade 16에만, 지금 모습은 그대로
	// 두고 더한다): 1 칼에서 펼쳐짐 — 처음 QFeelUnfoldSeconds 동안 폭이 QFeelUnfoldFrom배에서 펴지고 떠나는 자리에 번쩍 ·
	// 4 움직이는 그림 — 같은 뜯긴 결을 여덟 장(T_Aurora_SlashFlip, 4×2)으로 그려 생겨남(0·1) → 결이 일렁임(2~4를 초당
	// QFeelFlickerRate장) → 찢겨 흩어짐(5~7, 흐려지는 구간)으로 넘김. 앞 시안 QLook(층 나누기 · 갉혀 부스러짐 · 원뿔 들쭉날쭉 · 늘어진 꼬리)은
	// 「지금이 제일 낫다」로 뺐다. 시안 2 바닥 길은 두 번 다 아니어서 뺐다 — W 돌진 자국 줄은 몸에서 검기까지 이은 레이저 선, Q 눈 덮임을
	// 지나가는 자리마다 깐 판은 옅게 해도 흰 구름 띠로 보였다.
	static constexpr float QFeelUnfoldSeconds = 0.07f;
	static constexpr float QFeelUnfoldFrom = 0.3f;
	static constexpr float QFeelFlashScale = 0.7f;
	static constexpr float QFeelFlickerRate = 20.0f;
	static constexpr int32 QFeelFlipColumns = 4;
	static constexpr int32 QFeelFlipRows = 2;
	// Q 덧붙임 시안(Aurora.FX.QAdd 비트, 10-21 「뭐가 문제지, 검기 날리는 게 문제인가 — 검기를 더 못 하겠다면 다른 추가 이펙트를 붙이는 건
	// 어때」 — 찍은 장면을 보면 검기가 나는 동안에만 무언가 있고 휘두르는 칼·맞는 순간·화면은 비어 있다). 몸통은 AuroraSkillComponentQDrafts.cpp:
	// 1 칼 궤적 — 세 번 휘두르는 동안(QAddTrailSeconds) 칼날 밑동~끝을 따라 흰 칼바람(E 4와 같은 Aurora 평타 궤적) ·
	// 2 맞은 자리 — 대상 몸을 가로질러 검기 기울기대로 칼자국(Q2 칼자국 재질, 화면 가로에서 QAddMarkTilt도)이 그어졌다 QAddMarkHold초 뒤
	// 깨지고, 빛나는 얼음 조각 QAddShardCount개가 검기 나는 쪽으로 튐 · 4 맞은 대상 번쩍·멈칫 — 대상 몸 위에 빛나는 얼음(분신 재질)을
	// QAddFlashSeconds 덧씌우고 대상만 QAddHitStopSeconds 동안 HitStopDilation배로(캐릭터까지 멈추면 세상 시간으로 도는 둘째·셋째 검기
	// 예약이 동작과 어긋나고, 세상 전체를 늦추면 게임 시간으로 찍는 시안 장면에 안 남는다) · 8 화면 흔들림 — 검기가 떠날 때
	// QAddShakeLaunch, 맞을 때 QAddShakeHit(cm)만큼 흔들렸다 QAddShakeSeconds에 가라앉음.
	static constexpr float QAddTrailSeconds = 0.9f;
	static constexpr float QAddMarkLength = 170.0f;
	static constexpr float QAddMarkHalfWidth = 20.0f;
	static constexpr float QAddMarkTilt = 25.0f;
	static constexpr float QAddMarkHold = 0.12f;
	static constexpr int32 QAddShardCount = 8;
	static constexpr float QAddFlashSeconds = 0.08f;
	static constexpr float QAddHitStopSeconds = 0.1f;
	static constexpr float QAddShakeLaunch = 3.0f;
	static constexpr float QAddShakeHit = 9.0f;
	static constexpr float QAddShakeSeconds = 0.18f;
	// Q 검기 골격 시안(Aurora.FX.QShape, 10-21 「뭐가 문제일까 — 검기 이펙트 시안 여러 개」 → 꾸밈새가 아니라 모양이 다른 넷을 「다 만들어서
	// 시안 줘 봐」, 큰 검기 QBlade 16에만 — 나는 길·빠르기·맞는 때는 그대로): 1 세운 검기 — 같은 그림을 나는 쪽 축으로 QShapeUprightRoll도
	// 세우고(「/」「\」 번갈아) 아래 뿔이 바닥을 스치게 띄움, 폭 QShapeUprightScale배 · 2 얼음 덩어리 초승달 — 날 자리에 오로라 얼음
	// 덩어리(SM_Ice_Chunk, 스스로 빛나는 얼음 재질) QShapeChunkCount개를 가운데 크게(검기 폭 300일 때 QShapeChunkSize cm) 박고 그림은
	// QShapeChunkPlaneFade배로 옅게, 원뿔 없음 · 3 가는 칼빛 + 긴 잔광 — 처음 초승달 그림(가는 날 선)을 밝은 얼음빛으로, 같은 그림
	// QShapeTrailCount장이 QShapeTrailLag씩 뒤처지며 QShapeTrailFirst부터 QShapeTrailDecay배씩 흐려짐, 원뿔 없음 · 4 돌며 나는 얼음 고리 —
	// 거친 충격파 고리 그림을 지름 QShapeRingStart → QShapeRingEnd로 눕혀(QShapeRingTilt도 기움) 초당 QShapeRingSpin도 돌리고, 둘레에
	// 뒤로 누운 톱니 원뿔 QShapeRingTeeth개(길이 QShapeRingToothLength · 밑동 QShapeRingToothWidth), 앞 날이 나는 거리에 온다.
	// 첫 촬영(aurora-61st-qshape) 뒤 고침: 1 카메라 반대로 기운 검기가 가는 줄 → 늘 카메라 쪽으로(번갈아 기울지 않음) · 2 덩어리 13개·50cm는
	// 작아 그림에 묻힘 → 17개·75cm, 그림 0.45 → 0.3 · 3 잔상 9장 26cm 틈은 따로 떨어진 빗살 → 20장 8cm · 4 지름 150~230은 작음 →
	// 190~280, 톱니 8개·900도/초는 0.05초 장면마다 45도라 톱니가 멈춰 보임(촬영 장면 틈의 착시) → 6개·540도/초(장면마다 27도 < 톱니 틈의 반 30도).
	// 둘째 촬영 뒤: 2 팩 얼음 재질 덩어리가 흰 눈뭉치 → 빛나는 얼음 재질 · 3 잔상 20장에 번짐까지 겹쳐 흰 반달 판 → 잔상은 날 선만 푸르게(번짐 0.05)
	static constexpr float QShapeUprightRoll = 62.0f;
	static constexpr float QShapeUprightScale = 0.75f;
	static constexpr int32 QShapeChunkCount = 17;
	static constexpr float QShapeChunkSize = 75.0f;
	static constexpr float QShapeChunkPlaneFade = 0.3f;
	static constexpr int32 QShapeTrailCount = 20;
	static constexpr float QShapeTrailLag = 8.0f;
	static constexpr float QShapeTrailShrink = 0.006f;
	static constexpr float QShapeTrailFirst = 0.55f;
	static constexpr float QShapeTrailDecay = 0.86f;
	static constexpr float QShapeRingStart = 190.0f;
	static constexpr float QShapeRingEnd = 280.0f;
	static constexpr float QShapeRingTilt = 12.0f;
	static constexpr float QShapeRingSpin = 540.0f;
	static constexpr int32 QShapeRingTeeth = 6;
	static constexpr float QShapeRingToothLength = 55.0f;
	static constexpr float QShapeRingToothWidth = 22.0f;
	// Q 이펙트 시안(Aurora.FX.QSkin 비트, 10-21 「누운 초승달 형태가 좋은데 이펙트 시안을 더 달라는 뜻」 — 골격은 지금 큰 검기 그대로, 큰 검기에만):
	// 1 푸른 빛무리 — 같은 그림의 퍼진 빛(G)만 짙은 파랑으로 QSkinAuraScale배 판에 깔아 둘레를 감쌈(번짐 QSkinAuraHalo) ·
	// 2 오로라 빛깔 — 새 재질 M_Aurora_WaveBladeSkin의 AuroraMix 1(날 끝에서 끝까지 청록 → 파랑 → 보라) · 4 흐르는 결 — 같은 재질의
	// FlowStrength QSkinFlowStrength · 무늬 QSkinFlowTiling배(몸통이 얼음 잡음으로 흔들리며 뒤로 흐름) — 2·4는 날 빛을 QSkinToneGlow로 낮춤 ·
	// 8 긴 잔광 — 골격 3과 같은 가는 날 선 사본 QShapeTrailCount장이 뒤따름 · 16 얼음 결정 날 — 빗살 원뿔 대신 골격 2의 빛나는 얼음
	// 덩어리 QSkinChunkCount개(QSkinChunkSize cm, 그림은 그대로).
	// 두 번 찍어(aurora-62nd-qskin·qskin2) 뺀 것 둘: 앞 날 밝은 칼날 선(가는 날 그림을 겹치고 더 밝게·6cm 앞에 둬도 큰 검기의 흰 날에 묻힘) ·
	// 공기 일그러짐(굴절 2D 밀기 판 — 빛 안 받음·받음, 세기 0.03~5 모두 바닥 그대로). 2·4는 첫 판에 날 빛 2.5 그대로라 몸통이 흰빛으로
	// 꽉 차 색·결이 묻혔다(빛깔은 끝만 옅게) → 날 빛을 낮추고 재질이 흰빛도 물들임.
	static constexpr float QSkinAuraScale = 1.08f;
	static constexpr float QSkinAuraHalo = 0.8f;
	static constexpr float QSkinToneGlow = 0.8f;
	static constexpr float QSkinFlowStrength = 1.0f;
	static constexpr float QSkinFlowTiling = 3.0f;
	static constexpr int32 QSkinChunkCount = 15;
	static constexpr float QSkinChunkSize = 45.0f;
	// Q2 X자 두 번 베기: Q1이 끝난 뒤 FrostCrossWindow초 안. 첫 칼 = Fast_C(오른쪽 아래 → 왼쪽 위, 0.17~0.2초 가장 빠름) — Q1 끝 자세와
	// 시작 자세가 같아 이어진다. FrostCrossSwitch초에 둘째 칼 Fast_B(왼쪽 아래 → 오른쪽 위, 0.17~0.2초)로 넘어가고 FrostCrossSecondEnd초에
	// 끝난다. 거리·반각 · 피해(첫·둘째) · 둘째 칼에 밀어내는 거리 · 칼자국 길이·옆 반폭·몸 앞 거리·높이·화면 세로에서 기운 각·
	// 그어지는 시간 · 둘째 칼 뒤 깨지기까지 · 깨지며 사라지는 시간
	static constexpr float FrostCrossWindow = 1.5f;
	static constexpr float FrostCrossFirstCut = 0.18f;
	static constexpr float FrostCrossSwitch = 0.3f;
	static constexpr float FrostCrossSecondCut = 0.19f;
	static constexpr float FrostCrossSecondEnd = 0.45f;
	static constexpr float FrostCrossRange = 260.0f;
	static constexpr float FrostCrossHalfAngle = 70.0f;
	static constexpr float FrostCrossFirstDamage = 15.0f;
	static constexpr float FrostCrossSecondDamage = 25.0f;
	static constexpr float FrostCrossPush = 120.0f;
	static constexpr float CutMarkLength = 230.0f;
	static constexpr float CutMarkHalfWidth = 26.0f;
	static constexpr float CutMarkAhead = 115.0f;
	static constexpr float CutMarkHeight = 105.0f;
	static constexpr float CutMarkTilt = 40.0f;
	static constexpr float CutMarkDrawSeconds = 0.06f;
	static constexpr float CutMarkShatterDelay = 0.1f;
	static constexpr float CutMarkFadeSeconds = 0.12f;
	// W 돌진 길 흰 검기 자국(10-19): 길이 양끝 여유·옆 반폭·남는 시간
	static constexpr float DashStreakMargin = 40.0f;
	static constexpr float DashStreakHalfWidth = 70.0f;
	static constexpr float DashStreakSeconds = 0.9f;
	// Q 시안 2: 얼음 결정 두 줄(안쪽·바깥쪽 — 베는 거리 대비 자리·개수·크기), 줄마다 왼쪽에서 오른쪽까지 솟는 시간
	static constexpr float SlashInnerReach = 0.4f;
	static constexpr int32 SlashInnerCount = 7;
	static constexpr float SlashInnerScale = 0.4f;
	static constexpr float SlashOuterReach = 0.72f;
	static constexpr int32 SlashOuterCount = 9;
	static constexpr float SlashOuterScale = 0.55f;
	static constexpr float SlashRowSweepSeconds = 0.15f;
	// E 휘두름 시안(Aurora.FX.EStyle, 10-19): 바닥 무늬(1 원형 검기 · 2 서리 소용돌이)가 남는 시간, 2가 도는 빠르기, 3 청록 냉기 크기
	static constexpr float HoarfrostSpinSeconds = 0.9f;
	static constexpr float HoarfrostSpinDegreesPerSecond = 240.0f;
	static constexpr float HoarfrostGlowScale = 2.2f;
	// 냉기 장판(R, 2026-10-18 채널링): FieldChannelSeconds 동안 FieldBurstInterval마다 얼음 파편이 한 번 튀며 장판 안 전부에
	// FieldTickDamage·감속, 끝까지 버티면 얼림(Damage = 끝 피해). 전엔 4초 동안 0.5초마다 6(합 42)이 혼자 돌았다 → 지금 8 × 5 = 40.
	// 파편 위로 떨어지던 얼음 창(가시 메시)은 사용자 요청으로 뺐다(2026-10-18 밤 「뾰족한 오브젝트는 없애줘」).
	// 10-19 저녁 「지속시간 늘리고, 손 뻗은 애니 반복하고 이펙트 계속 터지는 거」: 버티는 시간 2 → 4초(파편 8 → 16번, 틱 피해는
	// 그대로라 합 40 → 80).
	static constexpr float FieldRadius = 280.0f;
	static constexpr float FieldChannelSeconds = 4.0f;
	static constexpr float FieldBurstInterval = 0.25f;
	static constexpr int32 FieldBurstCount = 16;
	static constexpr float FieldTickDamage = 5.0f;
	static constexpr float FieldTickSlowSeconds = 1.0f;
	static constexpr float FieldFreezeSeconds = 1.5f;
	// 파편 크기, 칼 든 자세(0.03초 한 장면) 반복 횟수
	static constexpr float FieldBurstScale = 0.45f;
	static constexpr int32 FieldChannelLoops = 90;
	// 시안 3: Recall(8초 귀환 채널링)에서 칼이 땅에 꽂히는 1.45초부터 재생하면 무릎 꿇은 채 버틴다
	static constexpr float FieldKneelStart = 1.45f;
	// 시안 4~6(10-19 「R 애니메이션 너무 어색하다, 다르게 조합」 — 3은 A와 같은 동작이고 가리키다 무릎으로 툭 바뀐다):
	// Emote_Slice(0.62초 칼을 듦 → 0.9초 머리 뒤 → 1.18초 앞으로 그음 → 1.74초 칼을 내리며 왼손이 나감 → 2.0~3.0초 손을 앞으로
	// 뻗어 버팀, aurora-35th-r-anims 사진)를 버티는 동작으로 쓴다. 4 = 가리킨(Cast) 뒤 손이 나가는 곳부터 FieldReachRate배로 ·
	// 5 = 가리킨 뒤 칼이 머리 뒤에 있는 곳부터 그어서 손 뻗기 · 6 = 가리키는 Cast 없이 칼을 드는 곳부터 시전 내내 한 동작으로.
	static constexpr float FieldReachStart = 1.74f;
	static constexpr float FieldReachRate = 0.6f;
	static constexpr float FieldSlashStart = 0.9f;
	static constexpr float FieldSliceOpenStart = 0.62f;
	// 시안 7(기본, 10-19 저녁): 6처럼 시전부터 한 동작으로 손을 뻗은 뒤, 버티는 동안 FieldThrustInterval마다 손을 거둬들였다가
	// (FieldThrustBlendIn초) 다시 뻗는다 — Emote_Slice의 손이 나가는 구간(FieldThrustStart → FieldReachPeakTime)을 FieldThrustRate배로.
	// 손이 다 뻗는 순간(처음 한 번 + 다시 뻗을 때마다 FieldThrustPeak초 뒤)마다 장판 안에서 크게 터진다(FieldThrustBurstScale).
	// 처음 손이 다 뻗는 때는 버티기 시작 약 1.05초 뒤, 첫 반복은 FieldThrustFirst초 뒤.
	// 1.7초(팔이 이미 반쯤 나간 자세)부터는 거둬들이는 폭이 작아 0.2초 간격 사진에서 반복이 안 보였다 → 손이 가슴께인 1.6초부터.
	static constexpr float FieldReachPeakTime = 2.02f;
	static constexpr float FieldThrustStart = 1.6f;
	static constexpr float FieldThrustRate = 1.3f;
	static constexpr float FieldThrustBlendIn = 0.12f;
	static constexpr float FieldThrustPeak = (FieldReachPeakTime - FieldThrustStart) / FieldThrustRate;
	static constexpr float FieldThrustFirst = 1.4f;
	static constexpr float FieldThrustInterval = 0.7f;
	static constexpr float FieldThrustBurstScale = 0.8f;
	static constexpr float FieldThrustShockScale = 0.45f;
	// 시안 8(10-19 밤 「R 애니 어색하다 — 다른 거 없나, 아니면 자연스럽게 만져 줄 수 있나」): 7은 다시 뻗을 때마다 1.6초 자세로 되돌려
	// 골반이 옆으로 14cm씩 튀었다(aurora-38th-hand: 1.6 → 1.83초 사이 골반 −10 → −24cm, 1.83초부터는 멈춤). 8은 몸이 멈춘 구간
	// (FieldPulseBack → FieldPulseOut, 왼손 약 30cm)만 앞뒤로 오가게 동작 시각을 직접 옮긴다 — 손을 천천히 거뒀다가(FieldPulseBackSeconds)
	// 빠르게 내밀고(FieldPulseOutSeconds) 다 내민 순간 터진다. 손이 처음 다 뻗을 때(FieldPulseOut)까지는 6·7과 같은 한 동작.
	static constexpr float FieldPulseBack = 1.75f;
	static constexpr float FieldPulseOut = 2.15f;
	static constexpr float FieldPulseBackSeconds = 0.45f;
	static constexpr float FieldPulseOutSeconds = 0.25f;
	// 시안 9: 칼로 얼음을 깎는 감정 표현(Emote_Ice_Sculpture)을 시전부터 끊지 않고 틀고, 칼끝이 가장 빨라지는 때(동작 시각, aurora-38th-hand2
	// 칼 뼈 축 끝 속도)마다 터진다. 버티기 끝(동작 4.35초) 직전 4.3초 칼질은 끝 얼림과 겹쳐 뺐다.
	static constexpr float FieldCarveBursts[] = {1.77f, 2.43f, 2.87f, 3.63f};
	// 9가 기본(10-19 밤 「칼 휘두를 때마다 캐릭터 쪽에 이펙트, 휘두를 때 해당 지점이 터지는 방식」): 칼질마다 발밑 초승달 검기(Q 그림) 반경·
	// 남는 시간, 손에서 뿜는 서리 크기, 겨눈 자리가 터지기까지의 틈과 터지는 크기(얼음 파편·충격파)
	static constexpr float FieldCarveArcRadius = 260.0f;
	static constexpr float FieldCarveArcSeconds = 0.5f;
	static constexpr float FieldCarveSparkleScale = 1.0f;
	static constexpr float FieldCarveBurstDelay = 0.08f;
	static constexpr float FieldCarveBurstScale = 1.0f;
	static constexpr float FieldCarveShockScale = 0.6f;
	// R 회오리(Aurora.FX.RField 1, 10-19 밤 큰 틀 「나 — 얼음 파편 회오리」): 칼질마다(시안 9 FieldCarveBursts) 한 단씩, 최대 VortexMaxStage.
	// 처음·단마다 더하는 파편 수 · 도는 빠르기(도/초, 처음 + 단마다) · 안쪽 반경 · 바깥 반경(처음 + 단마다) · 높이(처음 + 단마다) ·
	// 단이 오를 때 잠깐 부푸는 정도·시간 · 파편 크기 단마다 커짐 · 끌어당기는 빠르기(cm/초, 처음 + 단마다) · 가운데서 멈추는 거리 ·
	// 끝에 내리꽂히는 시간 · 터질 때 파편 수·빠르기. 장판 바닥은 서리 원(FrostTrailMaterial)을 깐다.
	// 첫 촬영(aurora-41st-qr)은 파편이 Q 파편 크기·18개라 흩어진 바늘로만 보였고, 바닥 서리 원(기본 채움 0.42)이 회오리를 덮었다
	// → 파편 크기 VortexShardScale배·수 30 + 단마다 12 · 바닥 원은 채움·고리를 사본 값으로 옅게.
	static constexpr int32 VortexMaxStage = 4;
	static constexpr int32 VortexBaseCount = 30;
	static constexpr int32 VortexAddCount = 12;
	static constexpr float VortexShardScale = 2.0f;
	static constexpr float VortexFloorFill = 0.07f;
	static constexpr float VortexFloorRing = 0.3f;
	static constexpr float VortexSpinBase = 160.0f;
	static constexpr float VortexSpinStage = 95.0f;
	static constexpr float VortexInnerRadius = 35.0f;
	static constexpr float VortexOuterBase = 110.0f;
	static constexpr float VortexOuterStage = 28.0f;
	static constexpr float VortexHeightBase = 130.0f;
	static constexpr float VortexHeightStage = 35.0f;
	static constexpr float VortexPulse = 0.25f;
	static constexpr float VortexPulseSeconds = 0.12f;
	static constexpr float VortexGrowStage = 0.12f;
	static constexpr float VortexPullBase = 25.0f;
	static constexpr float VortexPullStage = 35.0f;
	static constexpr float VortexPullStop = 70.0f;
	static constexpr float VortexCollapseSeconds = 0.18f;
	static constexpr int32 VortexBurstCount = 22;
	static constexpr float VortexBurstSpeed = 560.0f;
	static constexpr float VortexBurstUpSpeed = 380.0f;
	// 얼음 갑옷(A, 2026-10-18 다시 짬): ArmorSeconds 동안 받는 피해 × ArmorDamageScale. 지금은 자신만(파티원·아군 없음).
	// 겉모습은 몸을 감싸는 둥근 얼음 구(엔진 기본 구 지름 100cm를 ArmorShellDiameter로). 10-18 밤 「타원형 말고 둥그런 원형」.
	// 10-19 「지속시간도 2배 정도 더 길게」: 6 → 12초
	static constexpr float ArmorSeconds = 12.0f;
	static constexpr float ArmorDamageScale = 0.6f;
	static constexpr float ArmorShellDiameter = 210.0f;
	// 구 가운데 = 캡슐 가운데(발 위 96) → 발 아래 9cm부터 머리 위(201)까지 덮는다
	static constexpr float ArmorShellLift = 0.0f;
	static constexpr float ArmorShellGrowSeconds = 0.15f;
	static constexpr float ArmorShellFadeSeconds = 0.3f;
	// 동작(10-25 「A는 4번에서 그냥 손만 뻗는 동작만, 자연스럽게」): 얼음 조각 감정 표현(Emote_Ice_Sculpture) 첫 ArmorReachEnd초 —
	// 칼 든 오른손은 허리 아래 그대로, 왼손만 하늘로 뻗는다(aurora-70th-sculpt 손 높이 97 → 0.17초 149 → 0.27초 155 → 0.33초부터 내림).
	// ArmorReachRate배로 틀어 손이 거의 다 올라간 ArmorReachPeak에 보호막, ArmorReachEnd까지 들고 있다가 섞여 내린다(그 뒤는 칼을 휘두름).
	// 그 전(10-20 「간단하고 짧은 동작 중에 괜찮은 거 없나 → A는 니 추천대로」): 칼을 하늘로 곧게 치켜든 자세 하나(Ability_R_Targeting,
	// 0.03초 한 장면)를 30번 되풀이해 섞여 들어가는 0.25초 동안 칼을 올리고 0.3초 버팀.
	// 그 전(10-20 오후 「버프 애니메이션 없을까 → 그렇게 바꿔 봐」): 원작 등장 동작 Level_Start 1.9~3.0초(손을 들어 올려 칼을 한 바퀴
	// 휘두르고 내려 잡음, 칼이 몸 앞을 지나는 2.45초에 보호막 — aurora-48th-anims) — 「아쉽다」.
	// 그보다 전(10-18)은 Recall 앞 1.6초를 1.3배로 재생해 칼을 땅에 꽂는 1.45초에 보호막.
	static constexpr float ArmorReachRate = 0.8f;
	static constexpr float ArmorReachPeak = 0.17f;
	static constexpr float ArmorReachEnd = 0.33f;
	static constexpr float ArmorReachBlendIn = 0.12f;
	static constexpr float ArmorRaiseSeconds = ArmorReachPeak / ArmorReachRate;
	static constexpr float ArmorHoldSeconds = (ArmorReachEnd - ArmorReachPeak) / ArmorReachRate;
	// 켜질 때 발밑에 솟는 작은 얼음 결정 수·크기·반경
	static constexpr int32 ArmorCrystalCount = 6;
	static constexpr float ArmorCrystalScale = 0.3f;
	static constexpr float ArmorCrystalRadius = 60.0f;
	static constexpr float ArmorCrystalSeconds = 0.8f;
	// 서리 가속(S, 2026-10-18 다시 짬): 발밑에 HasteSeconds 동안 원형 장판, 안에 있으면 평타 속도·이동 속도 × HasteScale.
	// 10-19 「크기 더 키우고 지속시간도 더 길게」: 350 → 450cm, 6 → 9초. 10-25 「원 더 크게(2배 정도?)」: 450 → 900cm(빨라지는 범위도 같이).
	static constexpr float HasteRadius = 900.0f;
	static constexpr float HasteSeconds = 9.0f;
	// S 시안(Aurora.FX.SStyle, 10-19 「너무 깔끔하다」): 선이 닳는 정도 · 안에 까는 서리 진하기(「좀 더 투명하게」 0.35 → 0.25,
	// 「투명도 더 올려 줘」 → 0.17, 「더 옅게」 → 0.12, 원 안이 바빠 보여 절반 → 0.06, 「좀 더 투명하게」 → 0.04) ·
	// 3의 반짝임 간격
	// 10-20 S 분석(「왜 이렇게 아쉽지」 — 문양 선이 원판 전체의 뿌연 막에 묻힘): 닳는 정도 0.7 → 0.4(그림이 이미 거칠다),
	// 기본 시안을 서리 안 까는 1로. 깔릴 때 바깥에서 안쪽으로 드러나는 시간
	// 10-25 「흐리멍덩하게 말고 좀 또렷하게」: 닳는 정도 0.4 → 0.15(서리 무늬가 선을 고르게 옅게 만들어 흐려 보였다)
	static constexpr float HasteGrit = 0.15f;
	static constexpr float HasteFrostFill = 0.04f;
	static constexpr float HasteSparkleInterval = 0.4f;
	static constexpr float HasteRevealSeconds = 0.45f;
	// S 시안 빛(Aurora.FX.SLight): 장판 가운데에서 위로 띄우는 높이 · 닿는 거리(장판 반경 배율) · 빛깔
	static constexpr float HasteLightHeight = 120.0f;
	static constexpr float HasteLightReach = 1.3f;
	inline static const FLinearColor HasteLightColour{0.3f, 0.6f, 1.0f};
	// 10-20 밤 S 「라」로 확정(「S는 잘했네. '라' 버전으로 투명도 2~30% 증가」 — 아쉬운 까닭 셋을 다 고친 시안): 바깥 띠·안쪽 무늬가
	// 서로 반대로 도는 빠르기(라디안/초) · 2초마다 오르내리는 빛 폭 · 선·둘레 빛깔(회백색 분필 → 푸른 얼음빛) · 깔리는 순간 빛 배율을
	// HasteFlashStep마다 차례로 내려 0.5초에 가라앉힘. 진하기(선·퍼진 빛·별빛 불투명도)는 시안 값의 HasteOpacityScale배 — 「투명도 증가」를
	// 더 옅게로 읽었다(10-19 「투명도 더 올려 줘」를 옅게로 고친 전례와 같게). 빛 세기는 Aurora.FX.SLight 기본값(60).
	static constexpr float HasteSpinOuter = 0.35f;
	static constexpr float HasteSpinInner = -0.2f;
	static constexpr float HastePulseStrength = 0.35f;
	inline static const FLinearColor HasteIceColour{0.08f, 0.35f, 1.0f};
	inline static const FLinearColor HasteWhiteColour{0.45f, 0.75f, 1.0f};
	static constexpr float HasteFlash[] = {2.5f, 1.8f, 1.2f, 0.7f, 0.3f, 0.0f};
	static constexpr float HasteFlashStep = 0.1f;
	static constexpr float HasteOpacityScale = 0.75f;
	// 선만 10-25 「선 지금 희미한 거 또렷하게」로 0.35 × 0.75 ≈ 0.26 → 0.7(퍼진 빛·별빛은 그대로) → 이어서 「흐리멍덩하게 말고 좀 또렷하게」로
	// 0.9, 선 둘레 퍼진 빛 0.3 × 0.75 ≈ 0.23 → 0.08(선 바깥으로 뿌옇게 번져 경계가 흐려 보였다) — 갉음(SRough)도 끔(아래 SRough 설명)
	static constexpr float HasteLineOpacity = 0.9f;
	static constexpr float HasteHaloOpacity = 0.08f;
	static constexpr float HasteGlintStrength = 0.25f * HasteOpacityScale;
	// S 거친 시안(Aurora.FX.SRough 비트, 10-20 밤 「S 괜찮긴 한데 거친 느낌이 없어, 너무 정갈하고 이쁜 느낌」 — 그림의 「거칠게」가 화면에서
	// 1~1.5화소라 안 보였다): 1 크게 흔들고 갉고 끊은 그림(T_Aurora_SnowCircleRough) · 2 서리 무늬가 선을 굵게 갉음(Grit 0.4 → HasteRoughGrit,
	// 무늬 칸 2.5 → HasteRoughGritTiling — 갉힌 자리가 커짐). 첫 판 1.0 · 1.2는 무늬가 거의 다 지워져 조각만 남았다 → 갉힌 자리가 30%까지만 어두워지게.
	static constexpr float HasteRoughGrit = 0.75f;
	static constexpr float HasteRoughGritTiling = 1.6f;
	// 이어서 「S 2가 그나마 괜찮긴 한데 — 한계야? 시안 더 뽑을 수 있나」(2 바탕, 거친 장판 재질 M_Aurora_SnowFloorRough — 갉음 값이 더 있고
	// 기본값이면 M_Aurora_SnowFloor와 같다): 4 잔 서리 무늬(무늬 칸 HasteFineGritTiling — 굵은 갉음 1.6의 약 4배 잘게)로 한 겹 더 갉아
	// 잔 결을 냄 · 8 갉힌 경계를 칼로 끊듯 — 갉음 = saturate((무늬 − GritCut) × GritGain)의 기울기 2.2 → 8,
	// 반쯤 갉히는 무늬 값(0.15 + 0.5/2.2 ≈ 0.377)은 같게 GritCut 0.377 − 0.5/8 ≈ 0.315, 갉힌 자리는 거의 다 지움(Grit 0.9) ·
	// 16 갉는 무늬 칸 1.6 → HasteBigChunkTiling(갉혀 나간 조각이 커짐 — 8과 같이). 첫 판 16(선 둘레 퍼진 빛을 걷음)은 오히려 깔끔해져
	// 뺐다 — 퍼진 빛이 서리 무늬(PatternTexture) 얼룩을 싣고 있었다.
	static constexpr float HasteFineGrit = 0.6f;
	static constexpr float HasteFineGritTiling = 7.0f;
	static constexpr float HasteHardGrit = 0.9f;
	static constexpr float HasteHardGritCut = 0.315f;
	static constexpr float HasteHardGritGain = 8.0f;
	static constexpr float HasteBigChunkTiling = 1.0f;
	// S 여전사풍 시안 4(10-19 저녁 「Q랑 마찬가지, 여전사 같은 장판기」): 칼을 들어 올린 자리부터 굵은 얼음 균열이 바깥으로 갈라져
	// 나가고(HasteCrackSweepSeconds) 둘레는 깨진 얼음 테두리. 발밑에 얼음 덩어리가 튄다(HasteCrackChunkScale).
	static constexpr float HasteCrackSweepSeconds = 0.3f;
	static constexpr float HasteCrackChunkScale = 0.55f;
	// S 시안 6·7(10-19 밤 「S는 롤백하고, 기존 원에 깨진 듯한 이펙트 추가」): 3의 고리가 앞에서부터 양옆으로 깨져 나가는 시간,
	// 7이 고리 둘레에서 얼음 조각을 튀기는 자리 수·크기
	static constexpr float HasteRimSweepSeconds = 0.35f;
	static constexpr int32 HasteRimChunkCount = 8;
	static constexpr float HasteRimChunkScale = 0.3f;
	static constexpr float HasteScale = 1.3f;
	static constexpr float HasteCheckInterval = 0.2f;
	// 서리 장판 데칼이 나타나는·사라지는 시간, 바닥 데칼이 위아래로 비추는 깊이(반)
	static constexpr float HasteFloorFadeIn = 0.25f;
	static constexpr float HasteFloorFadeOut = 0.4f;
	static constexpr float FloorDecalDepth = 120.0f;
	// 얼음 파열(D, 10-18 전 이름 얼음 가시 줄)·얼음 창(F): 원작에 없는 스킬. 팩 이펙트 조합, 수치는 임시값.
	// 얼음 창 몸통은 엔진 원뿔을 얇게 늘린 칼날(팩에 길쭉한 입체 얼음 메시가 없고 Spike_Single은 두께 0 판, 분신 파편은 휘어 있다).
	static constexpr int32 SpikeCount = 6;
	static constexpr float SpikeStart = 100.0f;
	static constexpr float SpikeSpacing = 125.0f;
	static constexpr float SpikeInterval = 0.06f;
	static constexpr float SpikeHitRadius = 110.0f;
	static constexpr float SpikeSlowSeconds = 1.0f;
	// 줄 길이(시작 거리 포함) · 피해 — 10-26까지 D 정의(Range · Damage)였다. D가 옛 궁극기로 바뀌어 눈보라 시안 0(Aurora.FX.VStorm)에서만 쓴다
	static constexpr float SpikeLineLength = 850.0f;
	static constexpr float SpikeLineDamage = 30.0f;
	// D 동작(10-19 밤 「칼을 땅에 박는 걸로」): Recall에서 칼을 머리 위로 든 때부터 · 재생 배율
	// (10-20 원작 도약 Ability_RMB_Fwd 공중제비 내려찍기로 바꿨다가 「그냥 되돌려줘」로 되돌림) ·
	// 칼끝이 바닥에 닿는 순간 멈칫하는 시간(W 맞힐 때와 같은 방식, 화면 흔들림 없음) · 꽂은 뒤 재생 배율 · 꽂은 뒤 버티는 시간
	// 10-20 「한 끝이 아쉬운데 방법 없나 → 이렇게 해 봐」: 배율 1.5 → 2, 멈칫 새로
	// 이어서 「꽂고 나서 좀 더 기다리는 듯한 느낌」: 꽂은 뒤엔 제 빠르기로 무릎을 꿇으며 0.35 → 0.7초 버팀(얼음 줄이 다 솟을 때까지)
	static constexpr float SpikePlantStart = 0.95f;
	static constexpr float SpikePlantRate = 2.0f;
	static constexpr float SpikePlantHitStopSeconds = 0.07f;
	static constexpr float SpikePlantHoldRate = 1.0f;
	static constexpr float SpikePlantHoldSeconds = 0.7f;
	// D 시안(Aurora.FX.DStyle, 10-19 밤 「방향은 괜찮은데 이펙트가 아쉽다」): 1 = 자리마다 얼음 가시가 바닥을 뚫고 솟았다 도로 들어감
	// (가운데 하나는 높게, 양옆은 낮게 바깥으로 기울게) · 2 = 줄을 따라 바닥이 갈라진 자국(Q 벤 자국처럼 어둡게 파임) · 3 = 둘 다.
	// 가시 수 · 줄에서 옆으로 벌어지는 폭 · 높이(가운데·양옆) · 사는 시간 · 솟는 시간 · 도로 들어가는 시간
	static constexpr int32 RuptureSpikesPerStep = 3;
	static constexpr float RuptureSpikeSpread = 45.0f;
	static constexpr float RuptureSpikeMinHeight = 55.0f;
	static constexpr float RuptureSpikeMaxHeight = 130.0f;
	static constexpr float RuptureSpikeSeconds = 0.75f;
	static constexpr float RuptureSpikeRiseSeconds = 0.08f;
	static constexpr float RuptureSpikeSinkSeconds = 0.25f;
	// 갈라진 자국이 남는 시간·사라지는 시간
	static constexpr float RuptureCrackSeconds = 1.6f;
	static constexpr float RuptureCrackFadeOut = 0.6f;
	static constexpr float LanceSpeed = 2400.0f;
	// 분신 돌격(Aurora.FX.FClone, 10-21 「F는 얼음덩어리 말고 분신 세 개를 돌격시키는 게 좋겠다」): 창 빠르기로 나아가며 W가 실제로
	// 쓰는 돌진 동작(Ability_Q — WRun 2)을 W가 떠나는 때(LanceClonePoseFrom = ChargeWindupSeconds)부터 제 빠르기로 틀고, 칼을 앞으로
	// 뻗고 닿는 자세(LanceClonePoseHold)에서 멈춘 채 미끄러져 간다. 부서질 때 얼음 조각 LanceCloneShards개.
	// 첫 판은 옛 W 달리기(Jog_Fwd_Ability_Q, WRun 0)를 1.8배로 되풀이해 「그냥 달려 나가는 모습 말고 W 진행 중인 동작처럼」(10-21).
	static constexpr float LanceClonePoseFrom = 0.4f;
	static constexpr float LanceClonePoseHold = 0.52f;
	static constexpr int32 LanceCloneShards = 10;
	static constexpr float LanceHitRadius = 40.0f;
	static constexpr float LanceSplashRadius = 200.0f;
	static constexpr float LanceSplashDamage = 20.0f;
	static constexpr float LanceSlowSeconds = 1.5f;
	// 한 번에 던지는 창 수와 이웃 창 사이 각도(10-19 「세 방향으로 쏘는 거」: 가운데 + 좌우 20도)
	static constexpr int32 LanceCount = 3;
	static constexpr float LanceSpreadDegrees = 20.0f;
	// 칼날 크기(cm): 길이 · 옆 너비(위에서 보이는 폭) · 두께. 10-19 「투사체 크기를 절반 정도로」: 170×16×6 → 85×8×3,
	// 10-20 「얼음 조각 더 굵게」: 길이는 두고 너비·두께만 두 배 → 85×16×6, 이어서 「긴 송곳 같은 느낌」: 길게 + 단면을 둥글게
	// (너비 = 두께라 엔진 원뿔이 납작하지 않은 둥근 뿔) → 150×12×12. 꼬리는 85cm 때와 같은 몸 앞 LanceTailAhead에 둔다.
	static constexpr float LanceBladeLength = 150.0f;
	static constexpr float LanceBladeWidth = 12.0f;
	static constexpr float LanceBladeThickness = 12.0f;
	static constexpr float LanceTailAhead = 27.5f;
	// F 시안(Aurora.FX.FStyle, 10-19 밤 「방향은 괜찮은데 이펙트가 아쉽다」): 1 = 칼날마다 아래 바닥에 날아가는 만큼 드러나는 흰 서리 줄
	// (W 돌진 자국 그림을 가늘게) · 2 = 꽂힌 자리 바닥이 별 모양으로 갈라지고 얼음 파편이 나는 쪽으로 튐 · 3 = 둘 다.
	// 서리 줄 옆 반폭·남는 시간 / 갈라진 자국 반경·남는 시간·드러나는 시간·사라지는 시간 / 파편 수·벌어지는 각도·빠르기
	static constexpr float LanceStreakHalfWidth = 26.0f;
	static constexpr float LanceStreakSeconds = 0.7f;
	static constexpr float LanceCrackRadius = 120.0f;
	static constexpr float LanceCrackSeconds = 1.4f;
	static constexpr float LanceCrackSweepSeconds = 0.1f;
	static constexpr float LanceCrackFadeOut = 0.5f;
	static constexpr int32 LanceShardCount = 9;
	static constexpr float LanceShardSpread = 55.0f;
	static constexpr float LanceShardSpeed = 480.0f;
	static constexpr float LanceShardUpSpeed = 320.0f;
	// F 맞은 자리 이펙트 크기 배율(10-20 「맞았을 때 이펙트가 너무 큰데 2/3 수준으로」): 터짐 셋(분신 파편·얼림 폭발·눈사람 터짐) ·
	// 갈라진 자국 반경 · 튀는 파편 크기와 빠르기(퍼지는 거리)에 곱한다.
	static constexpr float LanceImpactScale = 2.0f / 3.0f;
	// F 나는 꼬리 시안(Aurora.FX.FFlight, 10-20 「날아갈 때가 밋밋 — 시안 줘 봐」): 1 얼음 부스러기를 떨구는 간격(Q 얼음 검기와 같음) ·
	// 한 번에 떨구는 수 · 크기 배율(Q 부스러기 기준 — 1배는 이 높이·거리에서 점으로만 보였다) · 2 잔상을 남기는 간격 · 잔상이 가늘어져
	// 사라지는 시간. 첫 시안 3(지나간 자리에 작은 서리 터짐 P_Rampage_Ice_Enrage_End)은 작게 띄우니 검은 그물 공처럼 보여 「둘 다」로 바꿨다.
	// 10-20 「부스러기 + 잔상으로 가되 부스러기를 좀 더 작게」: 3을 기본으로, 크기 2 → 1.4배
	static constexpr float LanceShedSeconds = 0.035f;
	static constexpr int32 LanceShedCount = 3;
	static constexpr float LanceShedSize = 1.4f;
	static constexpr float LanceGhostInterval = 0.025f;
	static constexpr float LanceGhostSeconds = 0.12f;

	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> MeleeImpact;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> MeleeSnowflakes;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> FreezeSegment;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> FreezeSegmentCrumble;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> FreezeRooted;
	// E 시안 4: 칼 궤적 후보(Aurora.FX.ETrail 차례 — Aurora 평타 · Rampage 얼음 평타 · 같은 것 분노 · Kwang 평타) · 발밑 얼음 덩어리 ·
	// 깨지기 직전 튀는 얼음 조각
	UPROPERTY(Transient)
	TArray<TObjectPtr<UParticleSystem>> SwordTrails;
	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> IceChunkMesh;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> SculptureChip;
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> ChargeStopAnimation;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> DashFlare;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> DashBodyFrost;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> WallBase;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> WallTop;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> WallBaseDestroy;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> WallTopDestroy;
	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> IcicleWall;
	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> DecoyStatue;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> DecoySpawn;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> DecoyExplode;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> DecoyCrumble;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> LeapTrail;
	// 87차 재료: Rampage 얼음 결정 파열 · Aurora 분신 조각 · Aurora 고드름 무더기(Recall) · 원작 돌진 겨누기 시작 동작(WPose 3)
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> RockHitBurst;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> DecoyFragmentsFx;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> IcicleWallsFx;
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> DashAimIntroAnimation;
	// F 얼음 바위 시안: Rampage 얼음 바위 던지기 · 나는 바위 꼬리(바위에 붙여야 보인다 — 단독 촬영에선 거의 빈 화면)
	// A 시안: 분신 발밑 가시 덩어리(A-1) · 손 얼음(A-1 손 위)
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> DecoyFrostFx;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> HandIceFx;
	// S 몸 오라: Rampage 얼음 분노 반복 · 몸에서 튀는 얼음 불티(몸 메시에 붙여야 보인다)
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> EnrageLoopFx;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> EnrageSparksFx;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> RockThrowFx;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> RockFlyingFx;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> CryoInitialBlast;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> CryoFrozen;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> CryoExplode;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> CryoSlowed;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> PrisonBurstEffect;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> LanceTrail;
	// 3차 시안(2026-10-18): Rampage 얼음판 충격파·파편·충전 빛
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> IceShock;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> IceShockBig;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> IceShards;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> IceChargeGlow;
	// 10-19 시안용: Rampage 얼음판 하늘색 냉기 연기·얼음 덩어리 파편, Aurora 돌진 준비 섬광(F 던질 때 손 쪽)
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> IceFrostPuff;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> IceChunks;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> LanceFlash;
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> ChargeLungeAnimation;
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> FieldChannelAnimation;
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> FieldAimAnimation;
	// R 버티는 자세 시안 4~6: 칼을 그은 뒤 손을 앞으로 뻗는 감정 표현(Emote_Slice)
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> FieldReachAnimation;
	// R 시안 9: 칼로 얼음을 깎는 감정 표현(Emote_Ice_Sculpture)
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> FieldCarveAnimation;
	// R 시안 3: 칼을 꽂고 무릎 꿇는 귀환 동작(Recall — 10-26까지는 D 정의의 동작을 빌려 썼다)
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> FieldKneelAnimation;
	// 얼음 갑옷 보호막: 엔진 기본 구 + 육각 얼음 재질. 바닥 데칼 재질: 눈송이 모양 서리 장판(S), 둥근 서리 자국(Q 시안 1),
	// 얼음 균열(Q 시안 2).
	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> ShellMesh;
	// 얼음 창 칼날: 엔진 원뿔 + 얼음 분신 석상 재질(BeginPlay에서 석상 메시의 재질을 가져온다)
	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> BladeMesh;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> BladeMaterial;
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> ShellMaterial;
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> HasteFloorMaterial;
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> FrostTrailMaterial;
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> CrackFloorMaterial;
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> SnowCoverMaterial;
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> SlashArcMaterial;
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> FrostSweepMaterial;
	// BeginPlay에서 미리 불러 둔 위 재질들(플레이 동안만 붙잡는다)
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInterface>> PreloadedMaterials;
	// Q 맞은 자리 시안 3: 검기가 지나가는 쪽으로 흩뿌리는 서리 반짝임(얼음 조각상 내지르기 연출)
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> SlashSparkles;
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> SpinRingMaterial;
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> SpinFrostMaterial;
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> DashStreakMaterial;
	// 여전사풍 시안(10-19 저녁): Q 칼이 바닥을 벤 자국 · S 갈라지는 얼음 균열 장판
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> SlashScarMaterial;
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> HasteCrackMaterial;
	// S 시안 5: 눈송이 짜임을 얼음 균열 선으로 그린 장판
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> HasteFlakeCrackMaterial;
	// 10-19 밤 시안: S 고리가 깨진 테두리(6 가늘게 · 7 굵게), D 줄을 따라 갈라진 자국, F 꽂힌 자리 별 모양 금
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> HasteRimCrackMaterial;
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> HasteRimShatterMaterial;
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> RuptureCrackMaterial;
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> LanceImpactCrackMaterial;
	// Q 검기 시안(10-20 사용자가 받은 Yin 팩): 바람 줄기 메시(호 모양 리본) · 채찍 잔상(푸른 물결) · 바람 날개 터짐. 쓸 때 불러온다
	// (팩이 없으면 그 시안만 빠진다).
	UPROPERTY(Transient)
	TSoftObjectPtr<UStaticMesh> YinWindSpline;
	UPROPERTY(Transient)
	TSoftObjectPtr<UParticleSystem> YinAfterimage;
	UPROPERTY(Transient)
	TSoftObjectPtr<UParticleSystem> YinKickOff;
	// Q 흩날리는 눈송이: 엔진 판(100cm, 위가 앞면) + 빛나는 눈송이 재질
	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> PlaneMesh;
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> FlakeMaterial;
	// Q1 날아가는 검기 · Q2 공중 칼자국(엔진 판에 붙이는 빛나는 그림, aurora_frost_materials_build.py 'blades')
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> WaveBladeMaterial;
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> CutMarkMaterial;
	// Q 검기 시안(Aurora.FX.QBlade, 'bladedrafts'): 1 두껍게 빛나는 초승달(그림 T_Aurora_SlashWave) · 2 스스로 빛나는 얼음(날 위 원뿔).
	// 쓸 때 불러온다(애셋이 없으면 그 시안만 빠진다).
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> WaveBladeBrightMaterial;
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> GlowIceMaterial;
	// QBlade 16 큰 검기의 뜯긴 결 초승달(T_Aurora_SlashRough) · V 착지 시안 5의 서리 충격파 고리(T_Aurora_NovaRing)
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> WaveBladeRoughMaterial;
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> NovaRingMaterial;
	// 더 거친 시안(QBig 1 · VNova 1) · S 거친 마법진 그림(SRough 1, 깔린 장판 재질 사본의 FlakeTexture를 바꾼다)
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> WaveBladeRougherMaterial;
	// Q 시안 QFeel 4: 큰 검기 뜯긴 결 여덟 장(T_Aurora_SlashFlip)을 넘기는 재질(FrameU·FrameV = 장 자리)
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> WaveBladeFlipMaterial;
	// Q 이펙트 시안 QSkin 2·4(오로라 빛깔·흐르는 결 값이 있는 큰 검기 재질)
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> WaveBladeSkinMaterial;
	// 얼음 분신 몸(캐릭터 메시용 표시가 있는 빛나는 얼음 — F 분신 돌격 · R 잔상) · R 얼음 난무 바닥 눈꽃 팔
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> CloneIceMaterial;
	// 87차 Q 검기 재질(aurora_frost_materials_build.py qforge) — 도구가 다시 만들 수 있게 소프트 참조
	TSoftObjectPtr<UMaterialInterface> QSlashForgeMaterial;
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> FlakeArmMaterial;
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> NovaRingRoughMaterial;
	UPROPERTY(Transient)
	TSoftObjectPtr<UTexture> SnowCircleRoughTexture;
	// S 마법진에서 가운데 큰 눈꽃만 뺀 그림(Aurora.FX.SInner 0)
	UPROPERTY(Transient)
	TSoftObjectPtr<UTexture> SnowCircleRingTexture;
	// S 거친 장판 재질(SRough 4·8 — 잔 서리 무늬 · 갉힌 경계 기울기 값이 있다)
	UPROPERTY(Transient)
	TSoftObjectPtr<UMaterialInterface> HasteFloorRoughMaterial;
	// Q2 첫 칼(Primary_Attack_Fast_C) · 둘째 칼(Primary_Attack_Fast_B)
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> CrossFirstAnimation;
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> CrossSecondAnimation;

	// ---- R 얼음 난무(10-21 「R은 일단 1로」 — Aurora.FX.RDraft 1이 기본, 0 = 그 전 냉기 장판) · 순간이동 시안 Aurora.FX.RBlink ----
	// 몸통은 AuroraSkillComponentRDrafts.cpp. 러프 시안 2 빙하 낙하 · 3 칼날 폭풍 · 5 거대 얼음검은 지웠고, 4 얼음 분신은 F(분신 셋 돌격)로 옮겼다.
	int32 GetRDraft() const;
	bool BeginRDraft(int32 Draft, const FVector& Aim);
	void BlinkCut(uint32 Generation, int32 Cut);
	void ShatterBlinkFlake(TWeakObjectPtr<AActor> Target, FVector Center);
	void LeaveBlinkAfterimage(bool bFirstSwing);
	void RDraftTick();
	void RestoreBlinkCamera();
	void ShowBlinkArmor(bool bShow);
	void EndRDraft();
	FTimerHandle RDraftTimer;
	// 처음 선 자리 · 벨 가운데 · 바로 앞 자리 · 대상 · 순간이동 시안 비트
	FVector BlinkHome = FVector::ZeroVector;
	FVector BlinkCenter = FVector::ZeroVector;
	FVector BlinkLast = FVector::ZeroVector;
	TWeakObjectPtr<AActor> BlinkTarget;
	int32 BlinkStyle = 0;
	// 지름마다 바닥에 남는 눈꽃 팔(데칼) · 지름 방향
	TArray<TWeakObjectPtr<UDecalComponent>> BlinkArms;
	TArray<FVector> BlinkArmDirections;
	// 시안 1 카메라 제자리: 붙잡은 카메라 붐 · 원래 붙은 자리
	TWeakObjectPtr<USceneComponent> BlinkBoom;
	FVector BlinkBoomRelative = FVector::ZeroVector;
	// 시안 8 미끄러지듯: 떠난 자리 · 갈 자리 · 떠난 때(음수 = 안 움직임)
	FVector GlideFrom = FVector::ZeroVector;
	FVector GlideTo = FVector::ZeroVector;
	double GlideStarted = -1.0;

	// ---- Q 덧붙임 시안(Aurora.FX.QAdd, 헤더 QAddTrailSeconds 설명) — 몸통은 AuroraSkillComponentQDrafts.cpp ----
	int32 GetQAdd() const;
	// 골격 시안(Aurora.FX.QShape, 헤더 QShapeUprightRoll 설명) — 그리기는 SpawnFlyingWave·BladeTick
	int32 GetQShape() const;
	// 이펙트 시안(Aurora.FX.QSkin, 헤더 QSkinAuraScale 설명)
	int32 GetQSkin() const;
	// 얼음 검기 세 번(QStyle 6)을 시작할 때 · 검기 하나가 떠날 때 · 검기가 대상에 닿을 때(StrikeFrostSlash 뒤)
	void OnQAddCast();
	void OnQAddLaunch();
	void OnQAddHit(AActor* Target, const FVector& Direction, float Roll);
	void ShakeCamera(float Strength);
	void ShakeTick();
	// 시안 4: 대상 몸에 빛나는 얼음을 덧씌우고 대상만 잠깐 멈춘다(덧씌움·멈춤은 제 예약이 푼다)
	void FlashHitTarget(AActor* Target);
	// 끝날 때(EndPlay) 카메라 자리를 되돌린다
	void EndQAdd();
	FTimerHandle ShakeTimer;
	// 흔드는 카메라 · 원래 붙은 자리 · 흔들기 시작한 때 · 세기(cm)
	TWeakObjectPtr<USceneComponent> ShakeCameraComponent;
	FVector ShakeRelative = FVector::ZeroVector;
	double ShakeStarted = 0.0;
	float ShakeStrength = 0.0f;

	// ---- F 얼음 새 시안(Aurora.FX.FBird, 헤더 LanceBirdHeight 설명) — 몸통은 AuroraSkillComponentFDrafts.cpp ----
	int32 GetFBird() const;
	// 숨긴 창 자리(Origin)에 새를 띄운다 · 창이 옮겨 갈 때마다 따라가며 퍼덕인다 · 창이 멈추면 지운다(bShatter = 그 자리에서 부서짐)
	void SpawnLanceBird(FAuroraLance& Lance, const FVector& Origin, int32 Index);
	void LanceBirdTick(FAuroraLance& Lance, const FVector& Where, double Now);
	void EndLanceBird(const FAuroraLance& Lance, bool bShatter);
	// 10-21 「갑자기 든 생각인데 얼음 모양 매나 새 같은 게 날아가는 거 어때? F는」: 창 셋(나는 길·맞힘 그대로)을 숨기고 그 자리를 새가
	// 난다 — 0 얼음 분신(지금) · 1 위에서 본 빛나는 얼음 매 그림(T_Aurora_IceHawk 여덟 장 날갯짓, M_Aurora_IceHawk) · 2 각진 얼음 결정 매
	// (aurora_bird_art.py가 만든 몸·날개 둘·꼬리 메시 + M_Aurora_IceHawkCrystal, 날개를 어깨 축으로 돌려 퍼덕임). 멈추면 그 자리에서 부서진다.
	// 이어서 「매는 훨씬 더 얇은 느낌 · 매 아니어도 여러 시안」: 3 얇은 매 · 4 얼음 용 · 5 눈꽃 표창 · 6 봉황(가는 선 그림 — 판 크기·장 넘김·
	// 용 마디는 AuroraSkillComponentFDrafts.cpp 표 FlyerCards · Dragon*).
	// 새가 바닥에서 뜬 높이 · 결정 매 크기 배율 ·
	// 결정 매 날갯짓(초당 번 · 가운데 각 · 위아래 폭, 도) · 날개 어깨·꼬리 밑동 자리(몸 기준 cm) · 나타나며 커지는 시간 · 부서질 때 파편 수
	static constexpr float LanceBirdHeight = 120.0f;
	// 새가 멈춘 자리 충격파 고리가 퍼지는 시간(10-25 「펑 터지는」)
	static constexpr float LanceBirdBurstSeconds = 0.25f;
	static constexpr float LanceBirdCrystalScale = 1.0f;
	static constexpr float LanceBirdFlapRate = 5.0f;
	static constexpr float LanceBirdFlapMid = 10.0f;
	static constexpr float LanceBirdFlapAmp = 40.0f;
	static constexpr float LanceBirdShoulderX = 6.0f;
	static constexpr float LanceBirdShoulderY = 12.0f;
	static constexpr float LanceBirdShoulderZ = 3.0f;
	static constexpr float LanceBirdTailX = -26.0f;
	static constexpr float LanceBirdGrowSeconds = 0.08f;
	static constexpr int32 LanceBirdShards = 12;
	// 매 퀄리티 시안(Aurora.FX.FLook): 1 잔상 — 사라지는 시간 · 밝기 배율(장면마다 한 장 — 0.03초마다였을 땐 띄엄띄엄 사다리처럼 보였다) /
	// 2 눈송이 꼬리 크기 / 4 느리게 — 빠르기 배율 / 8 몸 빛 — 판 크기 배율
	int32 GetFLook() const;
	static constexpr float LanceBirdGhostSeconds = 0.15f;
	static constexpr float LanceBirdGhostBrightness = 0.35f;
	// 눈송이는 매 판에 붙어 판 크기(약 2.6배)를 물려받는다
	static constexpr float LanceBirdFlakeScale = 0.6f;
	static constexpr float LanceBirdSlowRate = 0.5f;
	static constexpr float LanceBirdGlowSize = 1.25f;
	// 나는 쪽 이펙트 시안(Aurora.FX.FTrail): 1 몸 뒤 빛 꼬리 — 길이 · 폭 / 2 날개 끝 빛줄기 — 길이 · 폭 · 몸에서 옆·뒤 / 4 얼음 반짝이 크기 /
	// 8 얼음 부스러기(창 꼬리 시안 FFlight 1과 같은 것)
	int32 GetFTrail() const;
	static constexpr float LanceBirdStreakLength = 320.0f;
	static constexpr float LanceBirdStreakWidth = 46.0f;
	static constexpr float LanceBirdTipLength = 220.0f;
	static constexpr float LanceBirdTipWidth = 14.0f;
	static constexpr float LanceBirdTipSide = 72.0f;
	static constexpr float LanceBirdTipBack = 15.0f;
	static constexpr float LanceBirdSparkScale = 0.8f;
	// 등장 이펙트 시안(Aurora.FX.FSummon): 1 분신 등장 크기 / 2 섬광 · 얼음 조각 크기 · 서리 고리 반경 · 퍼지는 시간 · 진하기 /
	// 3 흰 폭발 크기 / 4 짙어지며 커지는 시간 · 처음 크기
	int32 GetFSummon() const;
	static constexpr float LanceBirdSummonDecoyScale = 0.6f;
	static constexpr float LanceBirdSummonFlashScale = 1.4f;
	static constexpr float LanceBirdSummonShardScale = 0.5f;
	static constexpr float LanceBirdSummonRingRadius = 90.0f;
	static constexpr float LanceBirdSummonRingSeconds = 0.3f;
	static constexpr float LanceBirdSummonRingStrength = 0.6f;
	static constexpr float LanceBirdSummonBlastScale = 0.35f;
	static constexpr float LanceBirdRevealSeconds = 0.3f;
	static constexpr float LanceBirdRevealFrom = 0.2f;

	// ---- A 시안(10-21 「A는 바닥에 조그마한 얼음 오브젝트 깔리는 거 말고 다른 이펙트 · 육각형 대신 어떤 무늬, 아님 아무것도 그리지 말까」)
	// — 몸통은 AuroraSkillComponentADrafts.cpp ----
	// 보호막이 켜질 때 발밑 이펙트(Aurora.FX.ACast) · 보호막 재질(Aurora.FX.APattern — 무늬 없음은 Shell을 바깥으로 한 재질 사본)
	void SpawnArmorCast(const FVector& Feet);
	UMaterialInterface* GetArmorShellMaterial(UStaticMeshComponent* Shell);

	// ---- D 고드름 비(10-25 「고드름 비 가자 — 하늘에서 날카로운 얼음송곳들이 일정하게 대각선으로 떨어지는 거」, Aurora.FX.DRain —
	// 0이면 그 전 앞으로 한 줄) — 몸통은 AuroraSkillComponentDRain.cpp ----
	int32 GetDRain() const;
	void ExecuteIcicleRain();
	void DropIcicle(FVector Landing);
	void IcicleRainTick();
	TArray<FAuroraIcicle> RainIcicles;
	FTimerHandle IcicleTimer;
	FVector IcicleFall = FVector(0.0f, 0.0f, -1.0f);
	TSet<TWeakObjectPtr<AActor>> IcicleHits;
	// 퀄리티 시안(Aurora.FX.DLook 비트, AuroraSkillComponentDRain.cpp 설명) · 4일 때 모든 창이 함께 부서지는 때 · 원 가운데
	int32 RainLook = 0;
	double RainEndsAt = 0.0;
	FVector RainCenter = FVector::ZeroVector;
	// 창 모양 시안(Aurora.FX.DSpear, AuroraSkillComponentDRain.cpp 설명) — 시전 때 정한 메시·재질(없으면 엔진 원뿔)과 그 메시의 반 크기,
	// 굵기 배율(각진 결정은 원뿔보다 굵어야 결이 보인다)
	TWeakObjectPtr<UStaticMesh> RainSpearMesh;
	TWeakObjectPtr<UMaterialInterface> RainSpearMaterial;
	FVector RainSpearExtent = FVector(50.0f);
	float RainSpearThick = 1.0f;

	// ---- D 새 시안(10-26 「내가 준 레퍼런스 참고하지 말고 니가 자유롭게 시안 여러 개」, Aurora.FX.DFresh 1~8 — 0이면 위 고드름 비)
	// — 몸통은 AuroraSkillComponentDFresh.cpp ----
	int32 GetDFresh() const;
	// 없는 시안 번호면 false(고드름 비로)
	bool ExecuteDFresh(int32 Draft, const FVector& Center, const FVector& Toward);
	// 시안마다 몸통 — 돌려주는 값 = 끝날 때까지 초(끝 기록용). Volley·Ward의 bPlus = 다듬은 판(4·5)
	float DFreshStreaks(const FVector& Center);
	float DFreshVolley(const FVector& Center, const FVector& Toward, bool bPlus);
	float DFreshWard(const FVector& Center, const FVector& Toward, bool bPlus);
	float DFreshCrown(const FVector& Center, const FVector& Toward);
	float DFreshOrbit(const FVector& Center, const FVector& Toward);
	float DFreshBigShard(const FVector& Center, const FVector& Toward);
	// 빛 조각 하나를 띄운다(Shape = 빛 그림, Base = 바탕 재질 — 없으면 M_Aurora_FxAdd). Piece의 Mesh·Material은 여기서 채운다.
	void AddDPiece(UTexture* Shape, FAuroraDPiece Piece, UMaterialInterface* Base = nullptr);
	void AddDLight(const FVector& Where, float Peak, float Radius, float Seconds);
	void DPieceTick();
	// Delay초 뒤 한 번
	void DFreshLater(float Delay, TFunction<void()> Do);
	// 꽂힌 자리 번쩍임(별빛 + 바닥 물결 고리 + 빛, Scale = 크기 배율, bLight가 아니면 빛 없이) · 맞히기(반경 안 대상마다 피해 + 감속,
	// 처음 한 번만 멈칫)
	void DFreshImpact(const FVector& Where, float Scale, bool bLight = true);
	void DFreshStrike(const FVector& Where, float Radius, float Damage);
	// 작은 반짝임 · 떨어지는 빛 결정(머리 Head → Ground, 박혀 Stuck초) + 뒤 빛줄기 · 빛 결정 조각이 사방으로 튐 · 얼음 가루가 피어오름 ·
	// 바닥에서 솟는 빛기둥 · 여러 자리에서 한 점으로 빨려 드는 빛 알갱이
	void DFreshGlint(const FVector& Where, float Size);
	// Picture = 결정 그림(없으면 T_Aurora_FxShard) · TrailScale = 뒤 빛줄기 굵기 배율
	void DFreshDive(double Born, const FVector& Head, const FVector& Ground, const FVector& Axis, float Fall, float Stuck, FVector2D Size,
		float TrailLength, float StuckFade = 0.12f, UTexture* Picture = nullptr, float TrailScale = 1.0f);
	void DFreshShatter(const FVector& Where, int32 Count, float Reach, float Scale);
	void DFreshMotes(const FVector& Where, int32 Count, float Radius);
	void DFreshPillar(const FVector& Where, float Width, float Height);
	void DFreshConverge(const TArray<FVector>& From, const FVector& To, float Seconds);
	TArray<FAuroraDPiece> DPieces;
	TArray<FAuroraDLight> DLights;
	FTimerHandle DPieceTimer;

	// ---- 위 빛 조각을 쓰는 본 스킬(10-26) — 몸통은 AuroraSkillComponentDFresh.cpp ----
	// S 둘레 얼음(Aurora.FX.SIce): 서리 가속 마법진 바깥 줄을 따라 빛 결정이 차례로 비스듬히 꽂혀 장판과 같이 남는다(D 시안 5 결계 둘레)
	void HasteRimIce(const FVector& Center, const FVector& Forward);
	// V 눈보라: 겨눈 자리에 마법진이 펼쳐지고 BlizzardSeconds 동안 빛 결정이 쏟아진 뒤 거대 결정이 가운데에 꽂혀 터진다. 그동안 화면
	// 전체에 눈보라(Aurora.FX.VStorm 0이면 그 전 D — ExecuteIceSpikes). Spike = 몇 번째 결정(자리 고르기 · 적 겨누기 · 큰 창 차례)
	void ExecuteBlizzard();
	void BlizzardSpike(const FVector& Center, const FVector& Toward, int32 Spike);
	// 송곳이 꽂힌 자리: 바닥에 눕힌 얼음 튐(Size cm) + 작은 별빛(StarScale) + bLight면 빛
	void BlizzardSplash(const FVector& Where, float Size, float StarScale, bool bLight);
	void BlizzardFinale(const FVector& Center, const FVector& Toward);
	// 화면에 붙은 눈 겹(흐르는 눈 그림)과 화면을 어둡게 하는 판(bDim)을 Seconds 동안
	void BlizzardStorm(float Seconds, bool bDim);
	// F 얼음 덩어리 일제 사격(Aurora.FX.FShot 1 — 0이면 그 전 매 날리기): 칼을 드는 동안 오로라 뒤 머리 위에 얼음 덩어리가 하나씩 생기고
	// (BeginChunkVolley), 칼을 뻗는 순간 차례로 창이 되어 여러 적에게 날아간다(ExecuteChunkVolley — 그 전 F면 false)
	void BeginChunkVolley();
	bool ExecuteChunkVolley();
	// 87차 F 덩어리 자체(Aurora.FX.FChunk — AuroraSkillComponentPolish.cpp): 0 그 전 보석 그림 · 1 얼음 바위 · 2 결정 창 · (93차) 3 얼음송곳. 덩어리 번호 = ChunkSpot의 Index
	int32 GetFChunk() const;
	void SpawnChunkMesh(int32 Index, const FVector& Spot, float Appear, float Life, float Phase);
	void FireChunkMesh(int32 Index, const FVector& Goal, float Flight);
	void ChunkMeshTick();
	void ClearChunkMeshes();
	TArray<FAuroraChunkMesh> ChunkMeshes;
	FTimerHandle ChunkMeshTimer;
	// 끝 기록용 — 맞힌 수 · 맞은 대상(처음 맞힌 하나만 멈칫)
	int32 ChunkHits = 0;
	TSet<TWeakObjectPtr<AActor>> ChunkVictims;
	// 끝 기록용 — 꽂힌 결정 수 · 그중 적을 겨눈 수 · 큰 창 수(시전마다 0부터)
	int32 BlizzardLanded = 0;
	int32 BlizzardAimed = 0;
	int32 BlizzardBig = 0;
};
