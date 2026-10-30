"""Keep functional success, reviewed presentation and original-game fidelity distinct."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_contract(profile: dict) -> dict:
    contract = profile.get('presentation_contract', {})
    if contract.get('mode') not in ('approved_project_baseline', 'user_requested_variant', 'original_game_reproduction'):
        raise ValueError('Declare the purpose of the chosen presentation')
    fidelity = contract.get('original_game_behavior')
    if fidelity not in ('unverified', 'verified'):
        raise ValueError('Declare original-game behavior verification separately')
    if contract['mode'] == 'original_game_reproduction' and fidelity != 'verified':
        raise ValueError('Original-game reproduction cannot complete without original-game reference verification')
    if fidelity == 'verified':
        reference = contract.get('original_game_reference', {})
        if not isinstance(reference, dict) or not reference.get('path') or len(reference.get('sha256', '')) != 64:
            raise ValueError('Original-game behavior needs an explicit reference file and fingerprint')
    states = contract.get('states', {})
    for state in ('idle', 'movement', 'attack', 'skills', 'recovery'):
        row = states.get(state, {})
        if not row.get('references') or not row.get('reason'):
            raise ValueError('Missing pose selection references/reason: ' + state)
    gate = contract.get('quality_gate')
    if profile.get('character_id') in ('sparrow', 'countess') and not gate:
        raise ValueError('Playable character profile requires temporal quality acceptance')
    if gate is not None:
        if not gate.get('expected_cloth_count') or not gate.get('cloth_limits') or not gate.get('minimum_seconds') or not gate.get('reason'):
            raise ValueError('Declare measured cloth limits and complete temporal scenario durations')
    return contract


def presentation_status(project: Path, profile_path: Path, review_path: Path | None = None) -> dict:
    profile = json.loads(profile_path.read_text(encoding='utf-8'))
    contract = validate_contract(profile)
    status = {'status': 'pending_visual_review', 'approved': False,
              'mode': contract['mode'], 'original_game_behavior': contract['original_game_behavior']}
    if contract['original_game_behavior'] == 'verified':
        reference = contract['original_game_reference']
        path = Path(reference['path']).resolve()
        if not path.is_file() or sha256(path) != reference['sha256']:
            status.update(status='invalid_original_reference', error='Original-game reference missing or changed')
            return status
    if review_path is None:
        return status
    try:
        review = json.loads(review_path.read_text(encoding='utf-8'))
        if review.get('profile_sha256') != sha256(profile_path) or review.get('character_id') != profile['character_id']:
            raise ValueError('Review belongs to a different/stale profile')
        if not review.get('approved') or not review.get('reviewer'):
            raise ValueError('No recorded visual review approval')
        if contract['original_game_behavior'] == 'verified' and review.get('original_reference_sha256') != contract['original_game_reference']['sha256']:
            raise ValueError('Visual review has not compared the declared original-game reference')
        required = {'idle', 'movement', 'attack', 'skills', 'recovery'}
        covered = set()
        for row in review.get('screenshots', []):
            path = Path(row['path']).resolve()
            if not path.is_relative_to(project / 'Saved/QA') or sha256(path) != row['sha256']:
                raise ValueError('Screenshot missing, changed or outside this project QA')
            covered.update(row['states'])
        if not required <= covered:
            raise ValueError('Visual review does not cover every declared state')
        protected = review.get('presentation_asset_hashes', {})
        if not protected:
            raise ValueError('Review has no asset fingerprint')
        for relative, expected in protected.items():
            path = (project / relative).resolve()
            if not path.is_relative_to(project) or sha256(path) != expected:
                raise ValueError('Reviewed presentation asset changed: ' + relative)
        if contract.get('quality_gate'):
            from visual_quality import check_quality
            results = []
            for evidence in review.get('quality_reports', []):
                path = Path(evidence['path']).resolve()
                if not path.is_relative_to(project / 'Saved/QA') or sha256(path) != evidence['sha256']:
                    raise ValueError('Temporal quality report missing or changed')
                quality = json.loads(path.read_text(encoding='utf-8'))
                if quality.get('profile_sha256') != sha256(profile_path):
                    raise ValueError('Temporal evidence uses a stale profile')
                fingerprints = quality.get('execution_fingerprints', {})
                if not fingerprints:
                    raise ValueError('Temporal evidence has no runtime source fingerprint')
                for relative, expected in fingerprints.items():
                    source = (project / relative).resolve()
                    if not source.is_relative_to(project) or sha256(source) != expected:
                        raise ValueError('Temporal evidence uses changed runtime code: ' + relative)
                for capture in quality.get('screenshots', []):
                    image_path = Path(capture['image']).resolve()
                    if not image_path.is_relative_to(project / 'Saved/QA') or sha256(image_path) != capture['sha256']:
                        raise ValueError('Temporal screenshot missing or changed')
                results.append(check_quality(profile, quality))
            if {row['fps'] for row in results} != {30, 60}:
                raise ValueError('Visual acceptance requires temporal quality evidence at 30 and 60 FPS')
            observations = review.get('observations', {})
            for criterion in ('cloth_stability', 'no_unintended_surfaces', 'skill_timelines', 'recovery'):
                if not observations.get(criterion, {}).get('passed') or not observations[criterion].get('note'):
                    raise ValueError('Missing explicit visual observation: ' + criterion)
            status['temporal_quality'] = results
        status.update(status='reviewed', approved=True, review=str(review_path),
                      reviewed_screenshot_count=len(review['screenshots']))
    except (ValueError, KeyError, OSError) as error:
        status.update(status='invalid_visual_review', error=str(error))
    return status


def completion_status(functional_passed: bool, presentation: dict) -> str:
    if not functional_passed:
        return 'functional_failure'
    return 'complete' if presentation['approved'] else 'pending_visual_review'
