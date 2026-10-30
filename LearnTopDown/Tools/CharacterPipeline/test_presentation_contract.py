"""Regression tests for the evidence gate, independent of animation implementation."""
import json
from pathlib import Path
import tempfile
import unittest
from presentation_contract import completion_status, presentation_status, sha256, validate_contract


class PresentationGateTests(unittest.TestCase):
    def profile(self):
        return {'character_id': 'example', 'presentation_contract': {
            'mode': 'user_requested_variant', 'original_game_behavior': 'unverified',
            'states': {state: {'references': ['/Game/Example'], 'reason': 'Measured source choice'}
                       for state in ('idle', 'movement', 'attack', 'skills', 'recovery')}}}

    def test_playable_profile_cannot_omit_temporal_acceptance(self):
        profile = self.profile()
        profile['character_id'] = 'sparrow'
        with self.assertRaises(ValueError):
            validate_contract(profile)

    def test_functional_pass_alone_cannot_complete(self):
        self.assertEqual(completion_status(True, {'approved': False}), 'pending_visual_review')

    def test_asset_name_cannot_prove_game_behavior(self):
        profile = self.profile()
        profile['presentation_contract'].update(original_game_behavior='verified', original_game_reference='idle_relaxed')
        with self.assertRaises(ValueError):
            validate_contract(profile)

    def test_unverified_reference_cannot_complete_reproduction(self):
        profile = self.profile()
        profile['presentation_contract']['mode'] = 'original_game_reproduction'
        with self.assertRaises(ValueError):
            validate_contract(profile)

    def test_stale_review_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            qa = root / 'Saved/QA'
            qa.mkdir(parents=True)
            profile = root / 'profile.json'
            profile.write_text(json.dumps(self.profile()))
            image, asset = qa / 'capture.png', root / 'pose.uasset'
            image.write_bytes(b'render fixture')
            asset.write_bytes(b'asset fixture')
            review = qa / 'review.json'
            data = {'character_id': 'example', 'profile_sha256': sha256(profile), 'approved': True,
                    'reviewer': 'test', 'screenshots': [{'path': str(image), 'sha256': sha256(image),
                    'states': ['idle', 'movement', 'attack', 'skills', 'recovery']}],
                    'presentation_asset_hashes': {'pose.uasset': sha256(asset)}}
            review.write_text(json.dumps(data))
            self.assertTrue(presentation_status(root, profile, review)['approved'])
            image.write_bytes(b'changed image')
            self.assertFalse(presentation_status(root, profile, review)['approved'])
            image.write_bytes(b'render fixture')
            asset.write_bytes(b'changed asset')
            self.assertFalse(presentation_status(root, profile, review)['approved'])
            asset.write_bytes(b'asset fixture')
            profile.write_text(json.dumps(self.profile(), indent=2))
            self.assertFalse(presentation_status(root, profile, review)['approved'])


if __name__ == '__main__':
    unittest.main()
