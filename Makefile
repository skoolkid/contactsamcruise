SNAPSHOT = $(shell grep -Po 'SNAPSHOT=\$$CONTACTSAMCRUISE_HOME/\K.*' .ddiffsrc)
T2S = contact_sam_cruise.t2s

MK = $(SKOOLKIT_HOME)/tools/disassembly.mk
ifeq ($(wildcard $(MK)),)
    $(error $(MK): file not found)
endif
include $(MK)
