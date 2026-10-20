package dev.itzgamesgd.sg01spike;

import com.sun.management.OperatingSystemMXBean;
import com.sun.management.ThreadMXBean;
import java.lang.management.GarbageCollectorMXBean;
import java.lang.management.ManagementFactory;
import java.util.Arrays;
import java.util.Locale;

/**
 * Experiment-only timing (N7-A3). Records how long a guard decision takes and how long the whole feature call takes, on the worldgen
 * thread, plus bytes allocated by the decision. Timing is recorded in every arm (including the vanilla arm) so the arms are comparable.
 * Samples are kept in time order; the first WARMUP samples are reported separately as the cold part of each run.
 */
public final class Perf {
    static final int CAPACITY = 400_000;
    static final int WARMUP = 2_000;

    static final class Samples {
        final String name;
        private final long[] values = new long[CAPACITY];
        private int count;

        Samples(String name) {
            this.name = name;
        }

        synchronized int count() {
            return count;
        }

        synchronized void add(long value) {
            if (count < CAPACITY) values[count++] = value;
        }

        synchronized String json() {
            return String.format(Locale.ROOT, "{\"all\":{%s},\"cold\":{%s},\"steady\":{%s}}", summary(0, count), summary(0, Math.min(WARMUP, count)),
                    summary(Math.min(WARMUP, count), count));
        }

        private String summary(int from, int to) {
            int n = to - from;
            if (n <= 0) return "\"count\":0";
            long[] sorted = Arrays.copyOfRange(values, from, to);
            Arrays.sort(sorted);
            double mean = Arrays.stream(sorted).average().orElse(0);
            return String.format(Locale.ROOT, "\"count\":%d,\"mean\":%.1f,\"p50\":%d,\"p95\":%d,\"p99\":%d,\"max\":%d", n, mean,
                    pct(sorted, 50), pct(sorted, 95), pct(sorted, 99), sorted[n - 1]);
        }

        private static long pct(long[] sorted, int p) {
            int idx = (int) Math.ceil(p / 100.0 * sorted.length) - 1;
            return sorted[Math.max(0, idx)];
        }
    }

    public static final Samples GEODE_DECISION_NS = new Samples("geode_decision_ns");
    public static final Samples GEODE_PLACE_NS = new Samples("geode_place_ns");
    public static final Samples GEODE_VANILLA_NS = new Samples("geode_vanilla_ns");
    public static final Samples MONSTER_DECISION_NS = new Samples("monster_decision_ns");
    public static final Samples MONSTER_DECISION_BYTES = new Samples("monster_decision_bytes");
    public static final Samples MONSTER_PLACE_NS = new Samples("monster_place_ns");
    public static final Samples MONSTER_VANILLA_NS = new Samples("monster_vanilla_ns");

    private static final ThreadMXBean THREADS = (ThreadMXBean) ManagementFactory.getThreadMXBean();
    private static final ThreadLocal<long[]> MARK = ThreadLocal.withInitial(() -> new long[3]);

    private Perf() {
    }

    /** Number of timing samples currently retained (bounded: CAPACITY per series). */
    public static long retainedSamples() {
        return (long) GEODE_DECISION_NS.count() + GEODE_PLACE_NS.count() + GEODE_VANILLA_NS.count() + MONSTER_DECISION_NS.count()
                + MONSTER_DECISION_BYTES.count() + MONSTER_PLACE_NS.count() + MONSTER_VANILLA_NS.count();
    }

    /** Called at the start of a guarded feature call. Index 2 holds an "active" flag, cleared once the call's time is recorded. */
    public static void mark() {
        if (!Guard.LAB) return; // production: no timing instrumentation
        long[] m = MARK.get();
        m[0] = System.nanoTime();
        m[1] = THREADS.getCurrentThreadAllocatedBytes();
        m[2] = 1;
    }

    /** Records the decision time (and its allocation). */
    public static void decisionDone(Samples ns, Samples bytes) {
        long[] m = MARK.get();
        if (m[2] == 0) return;
        ns.add(System.nanoTime() - m[0]);
        if (bytes != null) bytes.add(THREADS.getCurrentThreadAllocatedBytes() - m[1]);
    }

    /** Records the whole feature call. Only the first call after mark() records; a later RETURN injector sees no active mark. */
    public static void placeDone(Samples all, Samples vanilla) {
        long[] m = MARK.get();
        if (m[2] == 0) return;
        m[2] = 0;
        long elapsed = System.nanoTime() - m[0];
        all.add(elapsed);
        if (vanilla != null) vanilla.add(elapsed);
    }

    /** Process-level totals since JVM start (CPU, GC, heap). Startup is included, so the lab reports it as a whole-run figure. */
    public static String json() {
        long gcCount = 0;
        long gcMillis = 0;
        for (GarbageCollectorMXBean gc : ManagementFactory.getGarbageCollectorMXBeans()) {
            gcCount += Math.max(0, gc.getCollectionCount());
            gcMillis += Math.max(0, gc.getCollectionTime());
        }
        long cpuMillis = ((OperatingSystemMXBean) ManagementFactory.getOperatingSystemMXBean()).getProcessCpuTime() / 1_000_000L;
        Runtime rt = Runtime.getRuntime();
        return String.format(Locale.ROOT, "{\"gc_count\":%d,\"gc_ms\":%d,\"process_cpu_ms\":%d,\"heap_used_bytes\":%d,\"heap_max_bytes\":%d,"
                        + "\"geode_decision_ns\":%s,\"geode_place_ns\":%s,\"geode_vanilla_ns\":%s,\"monster_decision_ns\":%s,\"monster_decision_bytes\":%s,"
                        + "\"monster_place_ns\":%s,\"monster_vanilla_ns\":%s}",
                gcCount, gcMillis, cpuMillis, rt.totalMemory() - rt.freeMemory(), rt.maxMemory(),
                GEODE_DECISION_NS.json(), GEODE_PLACE_NS.json(), GEODE_VANILLA_NS.json(), MONSTER_DECISION_NS.json(), MONSTER_DECISION_BYTES.json(),
                MONSTER_PLACE_NS.json(), MONSTER_VANILLA_NS.json());
    }
}
