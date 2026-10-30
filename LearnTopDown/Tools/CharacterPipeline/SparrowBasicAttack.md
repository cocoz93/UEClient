# 궁수 평타 자세와 발사 연결

기본 사격은 `ABP_Sparrow_BasicNatural`과 `AM_Sparrow_PrimaryNatural` 전용 사본을 사용한다. 기존 SmoothStop AnimBP, 기본 몽타주, 원본 Sparrow 팩과 스켈레톤은 저장하지 않는다.

기존 전신 사격은 평상시 BowDown 자세에서 골반과 발을 무장 자세로 재배치한다. 최근 실제 수련장 기록에서는 제자리 평타 중 골반 XY 약 18cm, 오른발 XY 약 14cm 이동이 관찰됐다. 기존 발사 시점 0.05초는 몽타주 진입 블렌드 0.1초보다 빠르다.

평타는 캐시한 이동/대기 포즈 위에 `SparrowUpperBody` 슬롯을 `spine_01`부터 합성한다. 기존 `SparrowFullBody` 슬롯은 이 합성 뒤에 남겨 Q/W/R이 기존 전신 모션을 사용하도록 한다. 일반 평타 중에는 하체를 무장 대기로 전환하지 않는다. 시전과 R 버프의 기존 무장 자세는 유지한다.

1초짜리 원본 `Primary_Fire_Med`의 재장전/당김 구간 0.65~1.0초를 0.2초로 재생한 뒤, 원본 0~0.8초 발사 동작을 이어 재생한다. 전체 길이 1초와 기존 SaveAttack/ResetCombo 시각, 피해는 보존한다. 일반 평타 발사는 준비 0.2초 + 원본 발사 0.05초에 해당하는 0.25초다. R 강화 사격은 원래 발사 시점을 사용한다.

`ATopDownCombatCharacter::GetBasicAttackHitDelay`의 기본 구현은 종전 계산식 그대로다. Sparrow만 실제 선택된 전용 일반 몽타주에 한해 0.25 비율로 재정의한다. 별도 지정된 커스텀 AnimBP/몽타주는 자동 교체하지 않는다.

`Sparrow.Attack.Natural`은 다음 스폰에 적용한다. 1은 보강본, 0은 같은 빌드의 기존 전신 사격 비교다. 실제 기본값은 1이다. 에디터 전용 `SparrowAttackQA.Configure`는 선언된 두 전용 사본만 메모리에서 구성하며, 저장은 `sparrow_basic_attack_assets.py`가 수행한다.

`Sparrow.Attack.Speed`는 다음 스폰의 기본 공격 속도 배율이다. 10-22 기본값은 1.8, 범위 0.5~2.0이며 알려진 Sparrow 기본 공격에만 적용한다. 기본 사격은 약 0.556초, 발사는 약 0.139초다. 사용자의 후속 요청으로 재공격 대기 기준치를 최대0.08초로 줄인 뒤 공속으로 나누므로 현재 대기는 약0.044초다. 실제 60fps 연사 간격은0.600~0.617초, 프레임 단위 대기는0.050초였다.

전용 평타 몽타주는 스폰 시 transient 사본을 만들고 BlendIn0.12초/BlendOut0.18초도 공속으로 나눈다. HeldPrimary는 이 사본을 계승하고 HeldInnerFire의 전환도 같은 공속 배율로 줄인다. 한 발의 모션은 끝까지 재생하며 원본 캐릭터 BP와 몽타주는 다시 저장하지 않는다. 이번 입력·취소·이동 복귀 검사는 기존 `new_skills_probe.py`의 `sparrow_flow` 분기와 `sparrow_flow_concepts.py`가 수행했다. 결과는 `Saved/QA/CharacterPipeline/sparrow-flow-concepts-20261022/verify2`에 있다.

검증 도구는 `sparrow_basic_attack_run.py`, `sparrow_basic_attack_compare.py`다. 수련장 30/60fps에서 기존/수정본의 실제 컨트롤러 입력, 제자리 발·골반 이동, 단발·반복·준비 중 취소, R 강화 발사 시점, Q/W/E/R과 암살자 W를 검사한다. 기본 카메라와 진단용 근접 카메라를 구분하고 PNG와 프레임별 원본 기록을 보관한다. 이 기록은 OS 물리 입력이나 연속 영상, 원작 동작 재현을 의미하지 않는다.
