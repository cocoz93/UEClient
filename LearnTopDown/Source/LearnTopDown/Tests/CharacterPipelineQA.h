#pragma once

#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "HAL/IConsoleManager.h"
#include "HAL/FileManager.h"
#include "Misc/Paths.h"

namespace CharacterPipelineQA
{
	inline FString GetOutputDirectory(const TCHAR* LegacyDirectory)
	{
		const IConsoleVariable* Variable = IConsoleManager::Get().FindConsoleVariable(TEXT("CharacterPipeline.OutputDirectory"));
		const FString Requested = Variable ? Variable->GetString() : FString();
		const FString Directory = Requested.IsEmpty() ? FPaths::ProjectSavedDir() / LegacyDirectory : Requested;
		IFileManager::Get().MakeDirectory(*Directory, true);
		return Directory;
	}
}
#endif
