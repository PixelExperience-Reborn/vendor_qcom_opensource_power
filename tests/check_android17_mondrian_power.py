#!/usr/bin/env python3
"""Source and GNU Make regression gate for archived Qualcomm Power AIDL.

Tests the exact checked-in Makefiles. A passing result does NOT imply a built
Android 17 HAL, verified ADPF governor or working mondrian vendor ABI.
"""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class ArchivedPowerGuardTests(unittest.TestCase):
    def make_output(self, device, makefile, platform="taro", extras=None):
        with tempfile.TemporaryDirectory(prefix="pe-a17-power-") as folder:
            base = Path(folder)
            marker = base / "module.mk"
            marker.write_text("$(info PE_POWER_MODULE=$(LOCAL_MODULE))\n", encoding="utf-8")
            harness = base / "harness.mk"
            harness.write_text(
                "include " + str(ROOT / makefile) + "\n"
                ".PHONY: all\nall:\n"
                "\t@echo POWER_PACKAGES=$(PRODUCT_PACKAGES)\n"
                "\t@echo POWER_COPY=$(PRODUCT_COPY_FILES)\n"
                "\t@echo LEGACY_BOARD_POWER=$(TARGET_USES_NON_LEGACY_POWERHAL)\n",
                encoding="utf-8",
            )
            args = [
                "make", "--no-print-directory", "-f", str(harness), "all",
                "TARGET_DEVICE=" + device,
                "TARGET_BOARD_PLATFORM=" + platform,
                "TARGET_COPY_OUT_VENDOR=vendor",
                "CLEAR_VARS=/dev/null",
                "BUILD_EXECUTABLE=" + str(marker),
                "is-vendor-board-platform=true",
                "is-board-platform-in-list=false",
            ]
            if extras:
                args.extend(extras)
            run = subprocess.run(args, cwd=ROOT, text=True,
                                 capture_output=True, check=False)
            self.assertEqual(run.returncode, 0, run.stderr)
            return run.stdout

    def test_no_archived_qti_power_module_for_mondrian(self):
        for target in ("taro", "pineapple"):
            with self.subTest(platform=target):
                output = self.make_output("mondrian", "Android.mk", target)
                self.assertNotIn("PE_POWER_MODULE=android.hardware.power-service-qti", output)

    def test_legacy_module_stays_opt_in_for_other_devices(self):
        result = self.make_output("historical_reference", "Android.mk")
        self.assertIn("PE_POWER_MODULE=android.hardware.power-service-qti", result)

    def test_mondrian_neither_installs_qti_service_nor_taro_xml(self):
        result = self.make_output("mondrian", "power-vendor-product.mk")
        self.assertNotIn("android.hardware.power-service-qti", result)
        self.assertNotIn("android.hardware.power-impl", result)
        self.assertNotIn("powerhint.xml", result)
        self.assertIn("POWER_PACKAGES=\n", result)

    def test_other_device_keeps_previous_product_selection(self):
        result = self.make_output("historical_reference", "power-vendor-product.mk")
        self.assertIn("android.hardware.power-service-qti", result)
        self.assertIn("android.hardware.power-impl", result)
        self.assertIn("config/taro/powerhint.xml:vendor/etc/powerhint.xml", result)

    def test_legacy_board_flag_not_set_for_mondrian(self):
        self.assertIn("LEGACY_BOARD_POWER=\n",
                      self.make_output("mondrian", "power-vendor-board.mk"))
        self.assertIn("LEGACY_BOARD_POWER=true\n",
                      self.make_output("historical_reference", "power-vendor-board.mk"))

    def test_dont_advertise_nonfunctional_adpf_sessions(self):
        source = (ROOT / "Power.cpp").read_text(encoding="utf-8")
        creation = source.split("Power::createHintSession(", 1)[1].split(
            "Power::getHintSessionPreferredRate(", 1)[0]
        preferred = source.split("Power::getHintSessionPreferredRate(", 1)[1]
        for body in (creation, preferred):
            self.assertIn("EX_UNSUPPORTED_OPERATION", body)
            self.assertNotIn("setPowerHintSession(", body)
            self.assertNotIn("getSessionPreferredRate(", body)
            self.assertNotIn("ndk::ScopedAStatus::ok()", body)
        self.assertIn("*_aidl_return = nullptr;", creation)
        build = (ROOT / "Android.mk").read_text(encoding="utf-8")
        self.assertNotIn("    PowerHintSession.cpp", build)
        self.assertNotIn('#include "PowerHintSession.h"', source)

    def test_never_pretend_archive_aidl_v3_is_modern_adpf(self):
        makefile = (ROOT / "Android.mk").read_text(encoding="utf-8")
        vintf = ET.parse(ROOT / "power.xml").getroot()
        hal = vintf.find("./hal")
        self.assertIsNotNone(hal)
        self.assertEqual(hal.findtext("name"), "android.hardware.power")
        self.assertEqual(hal.findtext("version"), "3")
        self.assertEqual(hal.findtext("fqname"), "IPower/default")
        self.assertIn("android.hardware.power-V3-ndk", makefile)
        self.assertNotIn("android.hardware.power-V7-ndk", makefile)


if __name__ == "__main__":
    unittest.main(verbosity=2)
