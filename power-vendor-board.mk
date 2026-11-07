# Do not let the archived Qualcomm Power HAL set board policy on mondrian.
ifneq ($(TARGET_DEVICE),mondrian)
TARGET_USES_NON_LEGACY_POWERHAL := true
endif # TARGET_DEVICE != mondrian
