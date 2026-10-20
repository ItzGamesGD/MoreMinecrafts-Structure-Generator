package dev.itzgamesgd.sg01spike;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.chunk.status.ChunkStatus;

/**
 * Experiment-only instrumentation (Phase 4). Counts what happens on the guard's own thread while a guard decision is in progress:
 * region reads, hasChunk answers, blocking cache requests and generation-task scheduling. Counters are only incremented while
 * {@link #inGuard()} is true, so vanilla worldgen outside the guard is not counted. The probe never changes a result.
 */
public final class Probe {
    private static final ThreadLocal<int[]> DEPTH = ThreadLocal.withInitial(() -> new int[1]);

    public static final AtomicLong HAS_CHUNK_TRUE = new AtomicLong();
    public static final AtomicLong HAS_CHUNK_FALSE = new AtomicLong();
    /** WorldGenRegion.getChunk(x,z,status,load) entered from the guard. */
    public static final AtomicLong REGION_GET_CALLS = new AtomicLong();
    /** ... that returned a chunk whose persisted status is at or after the requested status (data was already available). */
    public static final AtomicLong REGION_GET_SERVED = new AtomicLong();
    /** ... that returned a chunk whose status was BELOW the requested status. Must stay 0. */
    public static final AtomicLong REGION_GET_STATUS_BELOW = new AtomicLong();
    /** ... that returned null. */
    public static final AtomicLong REGION_GET_NULL = new AtomicLong();
    /** ServerChunkCache.getChunk (blocking, may generate) entered from the guard. Must stay 0. */
    public static final AtomicLong SERVER_GET_BLOCKING = new AtomicLong();
    /** ServerChunkCache.getChunkFuture entered from the guard. Must stay 0. */
    public static final AtomicLong SERVER_GET_FUTURE = new AtomicLong();
    /** ChunkMap.scheduleGenerationTask from the guard. Must stay 0. */
    public static final AtomicLong CHUNKMAP_SCHEDULE = new AtomicLong();
    /** GenerationChunkHolder.scheduleChunkGenerationTask from the guard. Must stay 0. */
    public static final AtomicLong HOLDER_SCHEDULE = new AtomicLong();
    private static final List<String> SCHEDULED = new ArrayList<>();

    private Probe() {
    }

    public static void enter() {
        DEPTH.get()[0]++;
    }

    public static void exit() {
        DEPTH.get()[0]--;
    }

    public static boolean inGuard() {
        return DEPTH.get()[0] > 0;
    }

    public static void recordHasChunk(boolean result) {
        (result ? HAS_CHUNK_TRUE : HAS_CHUNK_FALSE).incrementAndGet();
    }

    public static void recordRegionGet(ChunkStatus requested, ChunkAccess chunk) {
        if (chunk == null) {
            REGION_GET_NULL.incrementAndGet();
        } else if (chunk.getPersistedStatus() != null && chunk.getPersistedStatus().isOrAfter(requested)) {
            REGION_GET_SERVED.incrementAndGet();
        } else {
            REGION_GET_STATUS_BELOW.incrementAndGet();
        }
    }

    public static synchronized void recordScheduled(String source, ChunkStatus status, ChunkPos pos) {
        if (SCHEDULED.size() < 50) SCHEDULED.add(source + " status=" + status.getName() + " pos=" + pos);
    }

    public static synchronized String json() {
        List<String> events = new ArrayList<>();
        for (String e : SCHEDULED) events.add("\"" + e.replace("\"", "'") + "\"");
        return String.format(
                "{\"has_chunk_true\":%d,\"has_chunk_false\":%d,\"region_get_calls\":%d,\"region_get_served\":%d,\"region_get_status_below\":%d,"
                        + "\"region_get_null\":%d,\"server_get_blocking\":%d,\"server_get_future\":%d,\"chunkmap_schedule\":%d,\"holder_schedule\":%d,\"scheduled_events\":[%s]}",
                HAS_CHUNK_TRUE.get(), HAS_CHUNK_FALSE.get(), REGION_GET_CALLS.get(), REGION_GET_SERVED.get(), REGION_GET_STATUS_BELOW.get(),
                REGION_GET_NULL.get(), SERVER_GET_BLOCKING.get(), SERVER_GET_FUTURE.get(), CHUNKMAP_SCHEDULE.get(), HOLDER_SCHEDULE.get(),
                String.join(",", events));
    }
}
