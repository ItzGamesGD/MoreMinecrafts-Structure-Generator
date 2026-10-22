package dev.itzgamesgd.sgprotection;

/**
 * Per-thread nesting depth of "a protected structure is placing its own pieces" (N10-R). The decision whether a scope is exempt is taken once, at
 * {@link #enter}, and the returned token carries it to {@link #exit}: a reload that swaps the protected set between the two can no longer unbalance
 * the depth. Pure Java (no Minecraft types) so that its lifecycle is unit-tested directly.
 */
public final class ExemptionScope {
    private static final ThreadLocal<int[]> DEPTH = ThreadLocal.withInitial(() -> new int[1]);

    private ExemptionScope() {
    }

    /** Opens a scope; returns the token that must be passed to {@link #exit} (true only if this scope is exempt and incremented the depth). */
    public static boolean enter(boolean exempt) {
        if (exempt) DEPTH.get()[0]++;
        return exempt;
    }

    /** Closes the scope that returned {@code token}; a scope that did not open an exemption changes nothing. Never goes below zero. */
    public static void exit(boolean token) {
        int[] depth = DEPTH.get();
        if (token && depth[0] > 0) depth[0]--;
    }

    /** True while at least one exempt scope is open on the calling thread. */
    public static boolean active() {
        return DEPTH.get()[0] > 0;
    }

    /** Current nesting depth of the calling thread (tests and diagnostics). */
    public static int depth() {
        return DEPTH.get()[0];
    }
}
