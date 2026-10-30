#pragma once

class USkeletalMeshComponent;

// 등록된 캐릭터 메시의 인스턴스만 조정한다. 원본 메시·천 설정 에셋은 변경하지 않는다.
void ConfigureTopDownCloth(USkeletalMeshComponent* Mesh, bool bStabilizeCape);
