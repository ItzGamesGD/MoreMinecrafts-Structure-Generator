package dev.itzgamesgd.sgprotection;

/**
 * Holds the installed {@link LabHooks}. Package-private on purpose (N10-R): the only code that installs a lab implementation is the production entrypoint, after
 * it has checked the operator opt-in and the lab mod's id; no other mod can call {@code install}.
 */
final class LabHolder {
    static volatile LabHooks current = LabHooks.NONE;

    private LabHolder() {
    }

    /** Installed once, from {@link SgProtectionMod#onInitialize}, before any guard decision. */
    static void install(LabHooks hooks) {
        current = hooks;
    }
}
