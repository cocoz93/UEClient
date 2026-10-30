#include "CharacterClothPresentation.h"

#include "ChaosCloth/ChaosClothingSimulationInteractor.h"
#include "ClothingSimulationInstance.h"
#include "ClothingSimulationInteractor.h"
#include "Components/SkeletalMeshComponent.h"

void ConfigureTopDownCloth(USkeletalMeshComponent* Mesh, bool bStabilizeCape)
{
    if (!Mesh) { return; }
    // 공격의 즉시 방향 전환은 천에 순간적인 회전 충격으로 전달하지 않는다.
    Mesh->SetTeleportRotationThreshold(45.0f);
    if (!bStabilizeCape) { return; }

    for (const FClothingSimulationInstance& Instance : Mesh->GetClothingSimulationInstances())
    {
        UClothingSimulationInteractor* Simulation = Instance.GetClothingSimulationInteractor();
        if (!Simulation) { continue; }
        for (const auto& Pair : Simulation->ClothingInteractors)
        {
            if (UChaosClothingInteractor* Cloth = Cast<UChaosClothingInteractor>(Pair.Value))
            {
                // 600 cm/s 이동·급회전에서 원심력에 망토가 뒤집히지 않도록 조정한다.
                // 명령은 엔진의 다음 동기화 시점에 적용되며 시뮬레이션과 겹쳐 쓰지 않는다.
                Cloth->SetVelocityScale(FVector(0.25f), 0.1f, 0.0f);
                Cloth->SetDamping(0.15f, 0.25f);
            }
        }
    }
}
