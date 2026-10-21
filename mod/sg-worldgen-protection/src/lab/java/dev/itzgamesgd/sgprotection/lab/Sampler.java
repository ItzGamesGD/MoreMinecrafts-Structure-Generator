package dev.itzgamesgd.sgprotection.lab;

import dev.itzgamesgd.sgprotection.Guard;
import dev.itzgamesgd.sgprotection.SgProtectionMod;
import dev.itzgamesgd.sgprotection.ProtectionConfig;
import com.sun.management.GarbageCollectorMXBean;
import com.sun.management.ThreadMXBean;
import java.io.IOException;
import java.lang.management.ManagementFactory;
import java.lang.management.MemoryPoolMXBean;
import java.lang.management.MemoryType;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.Locale;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;

/**
 * Experiment-only JVM sampler (N7-A4 Phase 4). When SG01_SAMPLE_FILE is set, a daemon thread appends one JSON line every SG01_SAMPLE_MS
 * (default 5000): uptime, heap in use now, heap in use after the last GC (sum of the heap pools' collection usage), non-heap, cumulative
 * allocation (all live threads), GC count/time and the last pause, loaded chunks, and the sizes of the guard's retained state.
 * It only reads; it never changes worldgen.
 */
public final class Sampler {
    private static volatile boolean running;

    private Sampler() {
    }

    public static void start(MinecraftServer server) {
        String file = System.getenv("SG01_SAMPLE_FILE");
        if (file == null || file.isBlank() || running) return;
        long period = Long.parseLong(System.getenv().getOrDefault("SG01_SAMPLE_MS", "5000"));
        running = true;
        Thread thread = new Thread(() -> loop(server, Path.of(file), period), "sg01-sampler");
        thread.setDaemon(true);
        thread.start();
    }

    public static void stop() {
        running = false;
    }

    private static void loop(MinecraftServer server, Path file, long period) {
        ThreadMXBean threads = (ThreadMXBean) ManagementFactory.getThreadMXBean();
        while (running) {
            try {
                Files.writeString(file, line(server, threads) + "\n", StandardOpenOption.CREATE, StandardOpenOption.APPEND);
                Thread.sleep(period);
            } catch (InterruptedException e) {
                return;
            } catch (IOException | RuntimeException e) {
                SgProtectionMod.LOGGER.warn("SG_PROTECTION sampler: {}", e.toString());
            }
        }
    }

    /** Resident set size of this process in kB (Linux /proc), 0 where unavailable. */
    private static long rssKb() {
        try {
            for (String l : Files.readAllLines(Path.of("/proc/self/status"))) {
                if (l.startsWith("VmRSS:")) return Long.parseLong(l.replaceAll("[^0-9]", ""));
            }
        } catch (IOException | RuntimeException e) {
            return 0;
        }
        return 0;
    }

    private static String line(MinecraftServer server, ThreadMXBean threads) {
        long afterGc = 0;
        for (MemoryPoolMXBean pool : ManagementFactory.getMemoryPoolMXBeans()) {
            if (pool.getType() == MemoryType.HEAP && pool.getCollectionUsage() != null) afterGc += pool.getCollectionUsage().getUsed();
        }
        Runtime rt = Runtime.getRuntime();
        long allocated = 0;
        for (long id : threads.getAllThreadIds()) {
            long a = threads.getThreadAllocatedBytes(id);
            if (a > 0) allocated += a;
        }
        long gcCount = 0;
        long gcMs = 0;
        long lastPauseMs = 0;
        for (java.lang.management.GarbageCollectorMXBean gc : ManagementFactory.getGarbageCollectorMXBeans()) {
            gcCount += Math.max(0, gc.getCollectionCount());
            gcMs += Math.max(0, gc.getCollectionTime());
            if (gc instanceof GarbageCollectorMXBean sun && sun.getLastGcInfo() != null) lastPauseMs = Math.max(lastPauseMs, sun.getLastGcInfo().getDuration());
        }
        int loadedChunks = 0;
        for (ServerLevel level : server.getAllLevels()) loadedChunks += level.getChunkSource().getLoadedChunksCount();
        return String.format(Locale.ROOT,
                "{\"uptime_ms\":%d,\"heap_used\":%d,\"heap_after_gc\":%d,\"heap_max\":%d,\"non_heap_used\":%d,\"allocated_bytes\":%d,\"gc_count\":%d,\"gc_ms\":%d,"
                        + "\"last_gc_pause_ms\":%d,\"loaded_chunks\":%d,\"chunks_decorated\":%d,\"rss_kb\":%d,\"process_cpu_ms\":%d,\"live_threads\":%d,\"guard_attempts\":%d,\"guard_events_retained\":%d,\"perf_samples_retained\":%d,\"protected_structures\":%d}",
                ManagementFactory.getRuntimeMXBean().getUptime(), rt.totalMemory() - rt.freeMemory(), afterGc, rt.maxMemory(),
                ManagementFactory.getMemoryMXBean().getNonHeapMemoryUsage().getUsed(), allocated, gcCount, gcMs, lastPauseMs, loadedChunks, Probe.DECORATED.get(), rssKb(),
                ((com.sun.management.OperatingSystemMXBean) ManagementFactory.getOperatingSystemMXBean()).getProcessCpuTime() / 1_000_000L, ManagementFactory.getThreadMXBean().getThreadCount(),
                Guard.GEODE.attempts.get() + Guard.MONSTER_ROOM.attempts.get(), Guard.GEODE.eventCount() + Guard.MONSTER_ROOM.eventCount(),
                Perf.retainedSamples(), ProtectionConfig.protectedCountOrZero());
    }
}
