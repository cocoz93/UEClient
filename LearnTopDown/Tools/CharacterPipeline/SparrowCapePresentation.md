# 궁수 망토 움직임 보강

현재 보강은 Sparrow Rogue 망토에만 적용한다. 기존 관성 제한 `.25/.1/0`과 급회전 보호 `45도`, 정지 애니메이션·방향 마무리·카메라·스킬 색과 판정은 보존한다. 대기 중에도 움직임이 살아 있도록 감쇠 기본값을 `.08/.12`로 낮추고, 수평 바람의 방향과 세기를 천천히 바꾼다. 실제 미감과 안정성은 최종 수련장 캡처·전체 천 입자 추적으로 따로 판단한다.

실제 `Sparrow_Rogue_APEX`는 `bUsePointBasedWindModel=true`인 Legacy 모델이다. `SetWind`의 공력 설정과 Min/Max Gust만 바꾸면 원하는 주기 변화가 이 모델에 전달되지 않는다. 엔진 `GetWindForCloth_GameThread`는 Gust 값을 읽지만 사용하지 않는다. 따라서 원본 모델을 유지하면서 궁수 소유의 `UWindDirectionalSourceComponent` 하나를 메시 앞 5cm에 붙인다. 영향 반경은 20cm이고 소스는 좌우 최대 2cm만 움직인다. 메시와 함께 이동·회전하며 수직 바람은 추가하지 않는다. 반경 안의 다른 메시 쿼리에도 영향을 줄 수 있으나 플레이어 캡슐 반경 42cm보다 작다. 전역 바람이나 맵 파일은 변경하지 않는다.

원래 상수풍 후보 80cm/s와 200cm/s는 안정성은 통과했지만 대기 중 펄럭임 개선이 작아 최종 후보에서 제외했다. 시간 변조는 캐릭터 생성 이후 실제 게임 시간을 사용한다. 기본 최대풍속 180cm/s에서 `110+50*sin(2π*.65*t)+20*sin(2π*1.15*t+.8)`로 40~180cm/s 범위의 수평 풍속을 만들고, 소스 좌우 위치는 `1.3*sin(2π*.48*t)+.7*sin(2π*.83*t+.5)`cm로 제한한다. 이를 통해 한 방향으로 처지는 모양만 바꾸는 효과를 줄인다. 물리 결과의 진폭이나 정확한 주파수를 보장하는 식은 아니다.

`.05초` UObject 바인딩 타이머 하나가 바람을 갱신한다. `bMaxOncePerFrame=true`로 지연 후 몰아서 호출하지 않으며, 실제 경과 시간으로 위상을 구한다. 약한 컴포넌트 참조와 소유자·부착·등록 상태를 확인하고 무효 상태면 정리한다. `EndPlay`에서 타이머를 명시적으로 해제한다. 새 Actor Tick은 없고, 맵·원본 천·스킨 에셋을 저장하지 않는다. 타이머와 바람 프록시 갱신 비용은 추가되며 GPU/CPU 성능 벤치마크를 수행했다는 뜻은 아니다.

엔진 `FClothingSimulationSolver::SetWindVelocity`의 100배 단위 변환과 Legacy `AddExternalForces`의 25배를 모두 보정한다. 좌우 소스 위치를 `x`라고 할 때 감쇠는 `1-(25+x*x)/400`, 소스 속도는 `target/(100*25*falloff)`다. 공개 `GetWindParameters`로 생성 직후 자기 메시·범위 밖 쿼리를 확인한다. 난수 순서를 바꾸는 `GetWindForCloth`를 진단용으로 추가 호출하지 않는다. 환산값과 설정 큐는 다른 바람과 합성된 solver 실측을 뜻하지 않는다.

- `Sparrow.Cloth.Presentation`: 생성 전 0=이전 안정화, 1=변조 보강본(기본).
- `Sparrow.Cloth.WindSpeed`: 기본 최대풍속 180cm/s, 0~200 제한. 생성 시 한 번 읽는다.
- `Sparrow.Cloth.Damping`, `LocalDamping`: 기본 `.08/.12`. 생성 시 한 번 읽는다.
- `SparrowCapePointWind`, `SparrowCapeFlutter start/stop` 로그로 입력·생성·타이머 정리를 확인한다.

비교 도구는 `sparrow_cape_run.py`, `sparrow_cape_compare.py`, `sparrow_cape_review.py`다. 최종 60fps는 같은 모듈·같은 실제 렌더 크기로 이전/보강본을 비교하고, 30fps는 보강본 안정성과 기능을 검증한다. 실제 PIE 뷰포트 크기를 검사 전 고정하며 PNG를 사후 확대·축소하지 않는다. 천 입자의 RMS와 주기 후보는 관측값으로 기록하며 미적 개선을 자동 승인하지 않는다. 증거는 `Saved/QA/CharacterPipeline/q-tone-cape-20261016`에 저장한다.
