# Android 17 / mondrian — Qualcomm Power HAL safety and ADPF source audit

Independent PixelExperience-Reborn Android 17 (AOSP-first) for POCO F5 Pro / Redmi K60 (`mondrian`, SM8475 / taro family).

## Verified old repository
- PE `seventeen` = `fourteen`: commit `6dce78ab54b4d715077a89bd249f47fed2957f3a` (2023-11-25), Git tree `44f939f48bd74121ccaca7909db7e6535eabfb04`.
- The service `android.hardware.power-service-qti` uses `android.hardware.power-V3-ndk` and registers `IPower/default` via Power AIDL **version 3** `power.xml`. The taro `powerhint.xml` is a historical Qualcomm perf-lock configuration including taro/cape/ukee targets; it is *not* verified for mondrian vendor perf ABI or kernel.
- An old `PowerHintSession.cpp` implements `updateTargetWorkDuration`, `reportActualWorkDuration`, `pause`, `resume`, and `close` as **successful no-ops**. Old `Power::createHintSession()` returns these fake sessions and `getHintSessionPreferredRate()` claims 16,666,666 ns. This falsely advertises real Android Dynamic Performance Framework (ADPF) feedback.
- The same historical service can collide with an independent modern Power HAL and an alternative powerhint format on the device. `power-vendor-product.mk` installs its QTI service/implementation and a taro XML table, and `power-vendor-board.mk` sets a legacy board flag.

## Actual source changes in the PE-Reborn review branch
1. `Power.cpp` returns the **AIDL-defined `EX_UNSUPPORTED_OPERATION`** for supported-form hint-session calls and preferred-rate calls instead of fabricating ADPF functionality. Empty TID validation still returns `EX_ILLEGAL_ARGUMENT`. No fake session is returned. Interaction boost and existing non-session power paths are not redesigned in this patch.
2. `Android.mk` stops linking unused fake `PowerHintSession.cpp`. A new outer `TARGET_DEVICE != mondrian` condition prevents registering the old QTI Power HAL module for mondrian, even if an inherited Qualcomm product configuration attempts to include the source.
3. `power-vendor-product.mk` avoids installing the old QTI service/implementation or taro `powerhint.xml` for mondrian. `power-vendor-board.mk` does not set `TARGET_USES_NON_LEGACY_POWERHAL` for mondrian; it remains unchanged for other historical devices.
4. `tests/check_android17_mondrian_power.py` executes the real Makefiles via host GNU Make, checking mondrian exclusion against multiple Qualcomm platforms, non-mondrian opt-in, and the Power AIDL contract. CI runs it without an Android build. Existing historical `power.xml` is **not** relabeled V7 or declared Android17-compatible.

## Modern independent solution for PE-Reborn (NOT implemented in this audit)
- Keep the official Android 17 `hardware/interfaces/power/aidl` specification authoritative. The modern Power HAL / ADPF architecture provides actual per-thread workload feedback, workload duration, and newer optional channels/features. A genuinely functional service requires a real governor/performance backend; implementing only AIDL methods or changing the VINTF version cannot create one.
- Build an independently maintained **single** Power AIDL service compatible with Android17's selected frozen AIDL revision and current vendor VINTF/FCM, potentially using upstream AOSP `libperfmgr` architecture as a technical reference. Do **not** import LineageOS-specific `lineage-libperfmgr` code or device trees. The reference LF52406 `sm8450-common/common.mk` currently selects a lineage libperfmgr Power service, `libqti-perfd-client`, and a **device-specific JSON** `powerhint.json`; these details are hardware-analysis inputs only, not a PE-Reborn product decision.
- Before enabling any service, map Xiaomi SM8475 vendor perf hint APIs, power/perf node ownership, `powerhint.json` semantics, task profiles, cgroup/CPU frequency policy, ADPF support and thermal throttling (avoid forcing persistent boosts). Validate one service owner and no duplicate `IPower/default` VINTF, SELinux, vendor ABI, CTS/VTS, cold boot/resume, games under sustained load, power draw and temperature.
- Current status: **source-only safety patch**, not a modern compiled Power HAL. `default.xml` stays on the official AOSP17 source graph; no power service enabled for PE-Reborn mondrian. No full Android17 Soong build, vendor image, SELinux check or physical mondrian testing done.

Authoritative contracts:
- https://source.android.com/docs/core/architecture/aidl/aidl-hals
- https://android.googlesource.com/platform/hardware/interfaces/+/master/power/aidl/android/hardware/power/IPower.aidl
- https://android.googlesource.com/platform/hardware/interfaces/+/master/power/aidl/vts/VtsHalPowerTargetTest.cpp

LineageOS and other custom ROM code was read **only as reference**. Nothing was copied into the independent base.
