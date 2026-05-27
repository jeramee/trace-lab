import unittest

from trace_lab.profile_registry import (
    AI_ASSISTED_LAB_NOTEBOOK_PROFILE,
    SIMULATED_LAB_BUNDLE_PROFILE,
    get_profile,
    is_known_profile,
    list_profile_names,
    require_profile,
)


class TraceLabProfileRegistryTests(unittest.TestCase):
    def test_registry_includes_default_and_ai_assisted_profiles(self):
        self.assertEqual(
            list_profile_names(),
            [
                AI_ASSISTED_LAB_NOTEBOOK_PROFILE,
                SIMULATED_LAB_BUNDLE_PROFILE,
            ],
        )

    def test_default_profile_has_no_required_tools_or_ncoder_requirement(self):
        profile = require_profile(SIMULATED_LAB_BUNDLE_PROFILE)

        self.assertEqual(profile["name"], SIMULATED_LAB_BUNDLE_PROFILE)
        self.assertEqual(profile["required_tools"], [])
        self.assertIn("no ncoder requirement", profile["stop_lines"])
        self.assertIn("no real hardware control", profile["stop_lines"])
        self.assertIn("no scientific truth validation", profile["stop_lines"])

    def test_ai_assisted_profile_is_declarative_ncoder_profile_only(self):
        profile = require_profile(AI_ASSISTED_LAB_NOTEBOOK_PROFILE)

        self.assertEqual(profile["name"], AI_ASSISTED_LAB_NOTEBOOK_PROFILE)
        self.assertEqual(profile["required_tools"], ["ncoder"])
        self.assertEqual(
            profile["evidence_meaning"],
            "AI-assisted notebook coding is workflow provenance only",
        )
        self.assertIn("no real ncoder execution in v0.2", profile["stop_lines"])
        self.assertIn("not scientific validation", profile["stop_lines"])
        self.assertIn("not claim promotion", profile["stop_lines"])

    def test_unknown_profile_is_not_known_and_can_raise_narrow_name_error(self):
        self.assertFalse(is_known_profile("real_hardware_lab_controller"))
        self.assertIsNone(get_profile("real_hardware_lab_controller"))

        with self.assertRaises(ValueError) as error:
            require_profile("real_hardware_lab_controller")

        self.assertIn("Unknown TraceLab profile", str(error.exception))

    def test_get_profile_returns_defensive_copy(self):
        profile = require_profile(SIMULATED_LAB_BUNDLE_PROFILE)
        profile["required_tools"].append("mutated")

        fresh_profile = require_profile(SIMULATED_LAB_BUNDLE_PROFILE)

        self.assertEqual(fresh_profile["required_tools"], [])


if __name__ == "__main__":
    unittest.main()
    