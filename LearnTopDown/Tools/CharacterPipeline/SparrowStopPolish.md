# 궁수 정지 자세와 방향 보강

2026-10-16 수련장 진단에서 이동→대기 전환의 블렌드가 0초이고, 실제 정지 한 프레임에 골반·머리·발과 망토 표본 입자가 함께 크게 바뀌었다. 루트 본과 캐릭터 위치는 같은 시점에 유지됐다. 30fps의 110cm 역방향 이동에서는 약 11.69도의 미완료 회전도 정지 후 남았다.

`sparrow_stop_fix_assets.py`는 기존 private `ABP_Sparrow_TopDown`을 `ABP_Sparrow_SmoothStop`으로 복사해, 실제 연결을 검사한 Idle→Run과 Run→Idle 전환만 각각 0.08초와 0.18초의 기존 Hermite 곡선으로 연결한다. 원본 private ABP와 Paragon 패키지는 저장하지 않는다. 원본 파일이 사용자 에디터에서 잠겨 있어도 새 복사본은 독립적으로 작성할 수 있다.

전환 시간만 고친 첫 비교에서는 정지 후 골반이 약 58cm 회수됐다. 기존 `idle_relaxed`의 183~336프레임은 몸을 뒤·옆으로 뺀 긴 제스처의 일부였고, Sprint 기반 이동과 중심 차이가 컸다. 원본 후보를 RAW·루트 잠금 조건별로 측정한 뒤, 전체 루프가 잘 맞고 활을 내리는 `Travel_Mode_Idle_BowDown`을 새 `A_Sparrow_TravelIdle`로 복사했다. 보강 AnimBP의 평상시 대기 노드만 이 사본으로 연결한다. 기존 대기 사본과 이동 BlendSpace는 보존한다. 이동과 대기의 평균 XY 차이는 골반 61.58→34.35cm, 머리 72.20→37.88cm로 줄지만, 이것만으로 실제 정지 화면을 통과했다고 판단하지 않는다.

`ASparrowCharacter::BeginPlay`는 현재 AnimClass가 정확히 기존 기본 private ABP일 때만 보강본으로 교체한다. 다른 커스텀 AnimClass는 보존한다. 카메라·속도·가속·감속·스킬 판정과 망토 물성은 유지한다.

도착 후 회전은 정상 경로 완료 시에만 `OnCharacterMovementUpdated`를 임시 연결한다. 기본 CharacterMovement 회전이 끝난 뒤 남은 각도가 30도 이내일 때, 기존 720도/초 한도에서 최대 0.18초 동안 마무리한다. 새 이동·경로 중단·전투·공중 전환·컨트롤러 변경·소유자 종료 시 예약을 해제한다. 상시 캐릭터 Tick은 추가하지 않는다.

`SparrowStopQA.State <token>`은 에디터 PIE에서만 예약 활성 여부·목표 각도·기한·현재 각도·AnimClass를 읽는다. 중단 검사는 예약이 실제 남은 프레임에서 새 입력을 넣고, 이후 0.25초의 각 프레임을 관찰한다. 게임 타깃에는 이 접근용 friend와 작성·진단 콘솔이 포함되지 않는다.

컨트롤러의 `PossessedBy` 알림은 `SetPawn`보다 먼저 올 수 있으므로 `NotifyControllerChanged`에서는 Controller 존재로 경로 콜백을 연결하고, 실제 처리 때 Controller의 현재 Pawn을 검사한다.

정지 보간만으로 미끄러짐이 생기는지는 최대 한 프레임 변화와 함께 정지 후 몸의 총 이동량도 비교해야 한다. 천을 더 강하게 감쇠시키기 전에 같은 자연정지·역방향·근거리 유지 입력 경로에서 잔여 망토 움직임을 다시 관찰한다.

향후 직업의 평상시 자세를 선택할 때도 손 높이·루프 경계에 더해 이동/대기의 골반·머리·발 중심과 실제 감속 구간을 확인한다. 긴 대기 제스처의 발췌와 Sprint의 단순 결합, 전환 시간 증가만으로 자연스러운 정지를 보장하지 않는다. 원본 여행 Corrective는 원본 AnimBP에 직접 연결된 근거가 없어 이번 보강에도 추가하지 않았다.

진단·보완 도구는 `sparrow_stop_diagnostic_{run,review}.py`와 `sparrow_stop_fix_compare.py`다. 후자는 위치·카메라·실제 정지 대비 캡처 시점 차이를 기록하며 사용자 미적 승인을 자동 판정하지 않는다. 보완 산출물은 `Saved/QA/CharacterPipeline/dual-character-polish-20261016`에 보관한다.

원본 자세 구간을 새로 설치하는 작업에서는 그 설치 결과를 기준으로 보강 복사본도 다시 작성·검증해야 한다. 단독 pose installer의 저장 완료만으로 현재 보강본의 실제 재생을 확인했다고 판단하지 않는다.
